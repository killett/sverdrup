"""Per-tile scorer unit tests (phase-14 Task 14, 0d-3) — synthetic fixtures.

Covers the two Stage-0 unit legs: core-only track extraction (overlap obs
excluded, boundary inclusion pinned) and the provenance guard firing with
the per-tile assimilated list. The gate-5 score identity lives in
``tests/test_phase14_gate5_score_identity.py`` (skip-guarded until the
Stage-1 anchor artifacts exist).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from sverdrup.adapters.altimetry import BBox
from sverdrup.application.spatial_tiles import TileFrame
from sverdrup.validation.pertile_scoring import extract_core_track, score_tile
from sverdrup.validation.provenance_guard import TrainScoreLeakError

_FRAME = TileFrame(
    core=BBox(lon_min=300.0, lon_max=305.0, lat_min=35.0, lat_max=40.0),
    overlap_deg=2.0,
    halo_deg=1.0,
)


def _track_file(path: Path, lon: np.ndarray, lat: np.ndarray) -> Path:
    """A minimal challenge-schema track file at the given positions."""
    n = lon.size
    t0 = np.datetime64("2017-06-01T00:00:00")
    time = t0 + np.arange(n) * np.timedelta64(30, "s")
    ds = xr.Dataset(
        {
            "longitude": ("time", lon.astype(np.float64)),
            "latitude": ("time", lat.astype(np.float64)),
            "sla_unfiltered": ("time", np.linspace(-0.1, 0.1, n)),
            "mdt": ("time", np.full(n, 0.5)),
            "lwe": ("time", np.zeros(n)),
        },
        coords={"time": time},
    )
    ds.to_netcdf(path)
    return path


def test_core_only_extraction_boundary_pinned(tmp_path: Path) -> None:
    """Extraction keeps EXACTLY the core-inclusive points.

    Points in the blend overlap (e.g. lon 305.1, inside solve_bbox 307)
    are excluded — they belong to the neighboring tile — and the boundary
    point at exactly lon 305.0 is INCLUDED (inclusive convention, matching
    BBox/read_l3_dataset). An off-by-one or solve-bbox extraction passes
    different point sets and fails the count.
    """
    lon = np.array([299.9, 300.0, 302.5, 305.0, 305.1, 306.9])
    lat = np.array([37.0, 37.0, 37.0, 37.0, 37.0, 37.0])
    track = _track_file(tmp_path / "dt_gulfstream_j3_phy_l3_fixture.nc", lon, lat)
    ds = extract_core_track(_FRAME, track)
    got = np.sort(np.asarray(ds["longitude"]))
    np.testing.assert_array_equal(got, [300.0, 302.5, 305.0])


def test_extraction_clips_latitude_too(tmp_path: Path) -> None:
    """Latitude clipping is core-only as well (lat/lon not swapped)."""
    lon = np.full(4, 302.0)
    lat = np.array([34.9, 35.0, 40.0, 40.1])
    track = _track_file(tmp_path / "dt_gulfstream_j3_phy_l3_fixture.nc", lon, lat)
    ds = extract_core_track(_FRAME, track)
    np.testing.assert_array_equal(np.sort(np.asarray(ds["latitude"])), [35.0, 40.0])


def test_extraction_respects_time_window(tmp_path: Path) -> None:
    """Points outside [time_min, time_max] are dropped (vendored slice)."""
    lon = np.full(3, 302.0)
    lat = np.full(3, 37.0)
    track = _track_file(tmp_path / "dt_gulfstream_j3_phy_l3_fixture.nc", lon, lat)
    ds = extract_core_track(_FRAME, track, time_min="2018-01-01", time_max="2018-12-31")
    assert np.asarray(ds["longitude"]).size == 0


def test_provenance_guard_fires_before_scoring(tmp_path: Path) -> None:
    """A map that assimilated the track's mission refuses to score.

    The fixture map carries ``assimilated_missions`` INCLUDING j3 and the
    track filename identifies j3 — the guard must raise, proving the
    per-tile scorer cannot silently score an assimilated mission.
    """
    from sverdrup.validation.output_adapter import write_map

    lon = np.arange(300.0, 305.01, 0.5)
    lat = np.arange(35.0, 40.01, 0.5)
    times = np.array([np.datetime64("2017-06-01")])
    stack = np.zeros((1, lat.size, lon.size))
    map_path = tmp_path / "tile_map.nc"
    write_map(times, lat, lon, stack, map_path, assimilated_missions=("alg", "j3"))
    track = _track_file(
        tmp_path / "dt_gulfstream_j3_phy_l3_fixture.nc",
        np.full(3, 302.0),
        np.full(3, 37.0),
    )
    with pytest.raises(TrainScoreLeakError):
        score_tile(_FRAME, map_path, track)
