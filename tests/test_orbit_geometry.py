"""Tests for the Phase-11 orbit-geometry provider (plan Task 1).

Expected values are fixed by CONSTRUCTION of the synthetic passes (known
heading, known crossing longitudes), never by running the code under test.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from sverdrup.application.orbit_geometry import (
    build_geometry_artifact,
    classify_orbit,
    derive_family,
    derive_mission_geometry,
    split_passes,
)

PHI0 = 38.1
KM_PER_DEG = 111.32


def _synth_passes(
    heading_north_deg: float,
    s_lon_deg: float,
    n_tracks: int,
    revisits: int,
    jitter_deg: float = 0.005,
    seed: int = 7,
) -> list[tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Ascending-family passes: each pass = (lon, lat, time) arrays crossing phi0."""
    rng = np.random.default_rng(seed)
    lats = np.linspace(33.0, 43.2, 40)
    passes = []
    tan_h = np.tan(np.deg2rad(heading_north_deg))
    base_lons = 295.0 + s_lon_deg * np.arange(n_tracks)
    for rev in range(revisits):
        for lon0 in base_lons:
            # lon increases with lat at rate tan(heading) (heading from north)
            lon = (
                lon0
                + (lats - PHI0) * tan_h / np.cos(np.deg2rad(PHI0))
                + rng.normal(0, jitter_deg)
            )
            t0 = rev * 10.0 + lon0  # distinct pass times; > 60 s gaps
            times = t0 + np.linspace(0, 0.005, lats.size)
            passes.append((lon, lats.copy(), times))
    return passes


def test_repeat_mission_recovered() -> None:
    """Bug caught: wrong axial circular mean, missing cos(phi0) in deg->km,
    or broken single-linkage clustering would each push these out of band."""
    fams = derive_family(_synth_passes(12.0, 2.8, 4, 12), phi0=PHI0, ascending=True)
    assert fams.orbit_class == "repeat"
    assert abs(fams.heading_north_deg - 12.0) < 1.0
    expected_s_lon = 2.8 * 111.32 * np.cos(np.deg2rad(PHI0))  # ~245.3 km by hand
    assert fams.s_lon_km is not None
    assert abs(fams.s_lon_km - expected_s_lon) < 0.05 * expected_s_lon
    assert fams.d_perp_km is not None
    # hand value: 245.3 * cos(12 deg) ~= 239.9 km; identity is the pinned formula
    assert abs(fams.d_perp_km - expected_s_lon * np.cos(np.deg2rad(12.0))) < 5.0
    assert np.isclose(
        fams.d_perp_km,
        fams.s_lon_km * abs(np.cos(np.deg2rad(fams.heading_north_deg))),
    )
    assert fams.n_passes == 48
    assert fams.spacing_quantiles_km is None
    # classifier evidence recorded per family (Task-12 rider): 4 tracks
    # revisited 12x; jitter drops 7 of the lon0=295 crossings out of the
    # domain box, so 41 in-domain crossings -> ratio 4/41
    assert fams.n_clusters == 4
    assert fams.classifier_ratio == pytest.approx(fams.n_clusters / fams.n_crossings)
    assert fams.classifier_ratio == pytest.approx(4 / 41)
    assert fams.cluster_size_median == 12.0


def test_drifting_mission_classified() -> None:
    """Bug caught: inverted ratio rule (repeat/drifting swapped) or a missing
    drifting-quantile path would fail the class or the summary fields."""
    rng = np.random.default_rng(3)
    passes = []
    for lon0 in 295.0 + rng.uniform(0, 10, 48):
        lats = np.linspace(33.0, 43.2, 40)
        lon = lon0 + (lats - PHI0) * np.tan(np.deg2rad(6.0))
        passes.append((lon, lats, lon0 + np.linspace(0, 0.005, 40)))
    fams = derive_family(passes, phi0=PHI0, ascending=True)
    assert fams.orbit_class == "drifting"
    assert fams.d_perp_km is None
    assert fams.s_lon_km is None
    assert fams.spacing_quantiles_km is not None
    q10, q50, q90 = fams.spacing_quantiles_km
    assert 0.0 < q10 <= q50 <= q90


def test_orbit_class_boundary_both_sides() -> None:
    """Bug caught: wrong comparison direction, or ratio over passes instead of
    crossings. Threshold = REPEAT_RATIO_MAX = 0.25 (owner-RATIFIED at the
    Task-12 ruling, 2026-07-16; measured envelope: repeat side <= 0.0952,
    drifting side >= 0.4320). Sides sit OUTSIDE the tabling gap
    (RATIO_GAP_LO, RATIO_GAP_HI) = (0.14, 0.431):
    2 clusters / 24 crossings = 0.083 -> repeat;
    6 clusters / 9 crossings = 0.667 -> drifting."""
    below = np.array([295.0] * 12 + [297.0] * 12)  # 2 clusters / 24 = 0.083
    cls, centers = classify_orbit(below)
    assert cls == "repeat"
    assert centers.size == 2
    above = np.array(
        [295.0, 295.0, 295.0, 297.0, 297.0, 299.0, 301.0, 303.0, 304.0]
    )  # 6 clusters / 9 = 0.667
    cls, centers = classify_orbit(above)
    assert cls == "drifting"
    assert centers.size == 6


def test_gap_ratio_tables_owner_decision() -> None:
    """OWNER RIDER (Task-12 ruling, 2026-07-16) — bug caught: silently
    classifying a family whose ratio lands strictly inside the measured gap
    between the classified sides. 2 clusters / 8 crossings = 0.25 is inside
    (0.14, 0.431) and MUST refuse."""
    in_gap = np.array([295.0] * 4 + [297.0] * 4)  # 2 clusters / 8 = 0.25
    with pytest.raises(ValueError, match="owner decision"):
        classify_orbit(in_gap)


def test_in_domain_crossings_only() -> None:
    """Bug caught: no [295, 305] filter -> out-of-box crossing pollutes
    n_crossings and the spacing statistics (obligation 4)."""
    lats = np.linspace(33.0, 43.2, 40)
    passes = []
    for lon0 in (296.0, 296.0, 298.0, 298.0, 306.0, 306.0):
        passes.append(
            (np.full(40, lon0), lats.copy(), lon0 + np.linspace(0, 0.005, 40))
        )
    fams = derive_family(passes, phi0=PHI0, ascending=True)
    assert fams.n_passes == 6
    assert fams.n_crossings == 4  # the two 306-deg passes cross outside the box


def test_split_passes_gap_and_direction() -> None:
    """Bug caught: gap threshold in wrong units (days vs seconds) or an
    inverted dlat/dt sign would merge the passes or swap asc/desc."""
    lats_up = np.linspace(33.0, 43.2, 40)
    lon = np.full(80, 300.0)
    lat = np.concatenate([lats_up, lats_up[::-1]])
    # times in DAYS: each pass spans ~7 min; 2-hour gap between them
    t1 = np.linspace(0.0, 0.005, 40)
    t2 = 0.09 + np.linspace(0.0, 0.005, 40)
    time = np.concatenate([t1, t2])
    passes = split_passes(lon, lat, time)
    assert len(passes) == 2
    assert passes[0][3] is True  # ascending
    assert passes[1][3] is False  # descending
    np.testing.assert_array_equal(passes[0][1], lats_up)


def _write_synth_obs(
    path: Path, base_lons: tuple[float, ...], heading_deg: float, jitter_scale: float
) -> None:
    """One ascending-family mission file in the real L3 variable convention."""
    rng = np.random.default_rng(int(jitter_scale * 1000) + 1)
    lats = np.linspace(33.0, 43.2, 40)
    tan_h = np.tan(np.deg2rad(heading_deg))
    lon_parts, lat_parts, time_parts = [], [], []
    t0 = np.datetime64("2017-01-01T00:00:00", "s")
    k = 0
    # 12 revisits keep the classifier ratio (n_tracks / crossings ~ 1/12)
    # clear of the Task-12 tabling gap's lower edge (0.14)
    for _rev in range(12):
        for lon0 in base_lons:
            lon = (
                lon0
                + (lats - PHI0) * tan_h / np.cos(np.deg2rad(PHI0))
                + rng.normal(0, 0.005) * jitter_scale
            )
            start = t0 + np.timedelta64(k * 7200, "s")  # 2-hour inter-pass gaps
            lon_parts.append(lon)
            lat_parts.append(lats)
            time_parts.append(start + np.arange(40) * np.timedelta64(10, "s"))
            k += 1
    time_all = np.concatenate(time_parts)
    ds = xr.Dataset(
        {
            "latitude": ("time", np.concatenate(lat_parts)),
            "longitude": ("time", np.concatenate(lon_parts)),
            "sla_unfiltered": ("time", np.zeros(time_all.size)),
        },
        coords={"time": time_all},
    )
    ds.to_netcdf(path)


def _obs_name(mission: str) -> str:
    return f"dt_gulfstream_{mission}_phy_l3_20161201-20180131_285-315_23-53.nc"


def test_artifact_deterministic_and_key_sensitive(tmp_path: Path) -> None:
    """Bug caught: timestamps/nondeterministic ordering in the artifact break
    byte determinism; a cache key ignoring obs shas would return the stale
    artifact after the input changed."""
    obs_dir = tmp_path / "obs"
    obs_dir.mkdir()
    _write_synth_obs(obs_dir / _obs_name("alg"), (295.5, 298.3, 301.1), 12.0, 1.0)
    _write_synth_obs(obs_dir / _obs_name("s3a"), (296.0, 299.5, 303.0), 30.0, 1.0)
    out = tmp_path / "phase11_orbit_geometry.json"

    sha1 = build_geometry_artifact(obs_dir, ["alg", "s3a"], PHI0, out)
    # Task-12 rider: classifier evidence lives IN the artifact, not only in
    # the constants comment
    art = json.loads(out.read_text())
    fam = art["missions"]["alg"]["asc"]
    assert {"classifier_ratio", "n_clusters", "cluster_size_median"} <= set(fam)
    out.unlink()  # force a full re-derivation, not a cache load
    sha2 = build_geometry_artifact(obs_dir, ["alg", "s3a"], PHI0, out)
    assert sha1 == sha2

    # cache path: same key -> same artifact, no rewrite
    sha2b = build_geometry_artifact(obs_dir, ["alg", "s3a"], PHI0, out)
    assert sha2b == sha1

    # change one obs file -> new key -> new artifact bytes
    _write_synth_obs(obs_dir / _obs_name("alg"), (295.5, 298.3, 301.1), 12.0, 2.0)
    sha3 = build_geometry_artifact(obs_dir, ["alg", "s3a"], PHI0, out)
    assert sha3 != sha1


def test_c2_refused(tmp_path: Path) -> None:
    """Bug caught: a missing zero-c2 guard silently opens the withheld file."""
    obs_dir = tmp_path / "obs"
    obs_dir.mkdir()
    c2_path = obs_dir / _obs_name("c2")
    _write_synth_obs(c2_path, (296.0,), 12.0, 1.0)
    with pytest.raises(ValueError, match="c2"):
        derive_mission_geometry(c2_path, phi0=PHI0)
    with pytest.raises(ValueError, match="c2"):
        build_geometry_artifact(obs_dir, ["c2"], PHI0, tmp_path / "geom.json")
