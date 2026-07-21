"""Tests for the phase-13 c-block diagnostic tap (plan Task 11; spec §8.5).

The tap extracts per-pass posterior-mean mode coefficients (ĉ) into a
window-tagged npz during a POINT solve at a modes-active winner config.
Winner-only, never a product output (§2 rider 1 stands).

Each test names the bug it catches; the fixture reuses the augmented-
oracle geometry (two missions x synthetic passes, one made DESCENDING).
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from sverdrup.core.grid import GridSpec
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
from sverdrup.core.parameters import ConstantProvider
from sverdrup.methods.miost import Miost, MiostPointDistribution
from sverdrup.methods.miost_basis import R_REF, build_g
from sverdrup.methods.miost_error_basis import (
    mission_hash_ints,
    segment_passes,
)
from sverdrup.methods.miost_rspec import RSpec
from sverdrup.methods.miost_windows import WindowPlan

_DELTAS = {"alg": 0.3, "h2g": -0.1, "j2g": 0.0, "j2n": 0.0}
_PARAMS = ConstantProvider(
    {
        "spacing_alpha": 1.5,
        "log10_rho": math.log10(20.0),
        "q_slope": 2.0,
        "l_t_days": 10.0,
    }
)
_GRID = GridSpec.lonlat(np.linspace(296, 304, 7), np.linspace(34, 42, 7))


def _fixture() -> dict[str, np.ndarray]:
    """Oracle-fixture geometry with the h2g@35 pass made DESCENDING."""
    rng = np.random.default_rng(23)
    lon_l, lat_l, t_l, mission_l = [], [], [], []
    for mission, day0, desc in (
        ("alg", 20.0, False),
        ("alg", 30.0, False),
        ("h2g", 25.0, False),
        ("h2g", 35.0, True),  # the one descending pass
        ("j2n", 22.0, False),
        ("s3a", 32.0, False),
    ):
        frac = np.linspace(0.0, 1.0, 15)
        t_l.append(day0 + frac * (40.0 / 86400.0))
        chord = 34.5 + frac * 7.0
        lat_l.append(chord[::-1] if desc else chord)
        lon_l.append(np.full(15, 297.0) + rng.uniform(0, 4) + frac * 2.0)
        mission_l.append(np.full(15, mission, dtype=object))
    for day_edge in (-10.0, 70.0):  # span sentinels (single-obs passes)
        t_l.append(np.asarray([day_edge]))
        lat_l.append(np.asarray([38.0]))
        lon_l.append(np.asarray([300.0]))
        mission_l.append(np.asarray(["alg"], dtype=object))
    lon = np.concatenate(lon_l)
    lat = np.concatenate(lat_l)
    t = np.concatenate(t_l)
    mission_arr = np.concatenate(mission_l).astype(str)
    # Give every pass a REAL per-pass offset so bias modes carry signal.
    y = rng.standard_normal(lon.size) * 0.02
    pt = segment_passes(lon, lat, t, mission_hash_ints(mission_arr))
    offsets = rng.standard_normal(pt.n_pass) * 0.15
    y = y + offsets[pt.obs_pass_idx]
    return {"lon": lon, "lat": lat, "t": t, "mission": mission_arr, "y": y}


def _obs(fx: dict[str, np.ndarray]) -> ObsWindow:
    return ObsWindow.from_arrays(
        lon=fx["lon"],
        lat=fx["lat"],
        time=fx["t"],
        values=fx["y"],
        error_model=DiagonalErrorModel(np.full(fx["y"].size, R_REF)),
        mission=fx["mission"],
    )


def _miost(tap: Path | None, rspec: RSpec) -> Miost:
    return Miost(
        plan=WindowPlan(starts=(0.0,)),
        pcg_rtol=1e-11,
        pcg_maxiter=20000,
        rspec=rspec,
        c_tap_dir=tap,
    )


_RSPEC_C = RSpec(deltas=_DELTAS, log_lam_bias=-2.0, log_lam_tilt=-8.0)


def test_tap_writes_window_tagged_artifact_with_pass_rows(
    tmp_path: Path,
) -> None:
    # One covering window -> one npz tagged by the window id, one row per
    # pass (8: six chord passes + two sentinels), schema complete.
    # Bug caught: tap keyed per-solve (overwriting windows), or rows per
    # obs instead of per pass.
    fx = _fixture()
    m = _miost(tmp_path, _RSPEC_C)
    m.solve(_obs(fx), _GRID, _PARAMS, 30.0)
    files = sorted(tmp_path.glob("ctap_*.npz"))
    assert len(files) == 1
    with np.load(files[0], allow_pickle=False) as z:
        assert z["c_bias"].size == 8
        assert z["c_tilt"].size == 8
        assert z["pass_mission"].size == 8
        assert z["pass_start_s"].size == 8
        assert z["family"].size == 8
        assert z["t_mean_days"].size == 8
        assert z["field_chord_mean"].size == 8
        assert z["n_obs"].size == 8
        assert float(z["lam_bias"]) == 10.0**-2.0
        assert float(z["lam_tilt"]) == 10.0**-8.0


def test_tap_family_from_lat_trend(tmp_path: Path) -> None:
    # The h2g@35 pass is descending (lat reversed); every other chord
    # pass ascends; single-obs sentinels default "asc" (no trend).
    # Bug caught: family from sign of c or from mission instead of the
    # per-pass lat trend, or asc/desc swapped (spec §8.3 separates
    # families precisely because mixing injects alternation).
    fx = _fixture()
    m = _miost(tmp_path, _RSPEC_C)
    m.solve(_obs(fx), _GRID, _PARAMS, 30.0)
    with np.load(next(iter(tmp_path.glob("ctap_*.npz"))), allow_pickle=False) as z:
        fam = [str(s) for s in z["family"]]
        t_mean = z["t_mean_days"]
        # exactly one desc row, and it is the pass near day 35
        assert fam.count("desc") == 1
        assert abs(float(t_mean[fam.index("desc")]) - 35.0) < 0.1


def test_tap_bias_tilt_deinterleaved_not_swapped(tmp_path: Path) -> None:
    # lam_bias 1e-2 (free) vs lam_tilt 1e-8 (pinned): with real per-pass
    # offsets in y, |c_bias| must dominate |c_tilt| by orders of
    # magnitude on the multi-obs passes.
    # Bug caught: the [bias, tilt] per-pass column interleave read as
    # [all-bias | all-tilt] (block layout) — the swap mixes the two modes
    # and the magnitude ordering collapses.
    fx = _fixture()
    m = _miost(tmp_path, _RSPEC_C)
    m.solve(_obs(fx), _GRID, _PARAMS, 30.0)
    with np.load(next(iter(tmp_path.glob("ctap_*.npz"))), allow_pickle=False) as z:
        multi = z["n_obs"] > 1
        med_bias = float(np.median(np.abs(z["c_bias"][multi])))
        med_tilt = float(np.median(np.abs(z["c_tilt"][multi])))
    assert med_bias > 100.0 * med_tilt


def test_tap_chord_mean_matches_fitted_field(tmp_path: Path) -> None:
    # field_chord_mean must equal the per-pass mean of (G_field @ eta)
    # recomputed here from the returned distribution's own eta and an
    # independently rebuilt G on the window's obs subset.
    # Bug caught: chord mean computed from the AUGMENTED prediction
    # (field + modes) — the row-4 detector would correlate c with itself.
    fx = _fixture()
    m = _miost(tmp_path, _RSPEC_C)
    dist = m.solve(_obs(fx), _GRID, _PARAMS, 30.0)
    assert isinstance(dist, MiostPointDistribution)
    spec = dist._spec  # noqa: SLF001 (test reaches into the fixture result)
    eta = dist._etas["w+00000.0+60"]  # noqa: SLF001
    with np.load(next(iter(tmp_path.glob("ctap_*.npz"))), allow_pickle=False) as z:
        # window [0,60] with L_t 10 covers every obs incl. sentinels
        els = spec.elements_for_window(0.0, 60.0)
        g = build_g(spec, els, fx["lon"], fx["lat"], fx["t"])
        fitted = np.asarray(g @ eta)
        pt = segment_passes(
            fx["lon"], fx["lat"], fx["t"], mission_hash_ints(fx["mission"])
        )
        for p in range(pt.n_pass):
            sel = pt.obs_pass_idx == p
            np.testing.assert_allclose(
                float(z["field_chord_mean"][p]),
                float(fitted[sel].mean()),
                rtol=1e-10,
            )


def test_tap_absent_for_modes_absent_config(tmp_path: Path) -> None:
    # Lane-D configs have NO c-block (structural column absence): the tap
    # writes nothing even when a tap dir is set.
    # Bug caught: a zero-filled phantom c artifact for a config whose
    # parameterization has no modes (rows would enter the §8 tables).
    fx = _fixture()
    m = _miost(tmp_path, RSpec(deltas=_DELTAS))
    m.solve(_obs(fx), _GRID, _PARAMS, 30.0)
    assert list(tmp_path.glob("ctap_*.npz")) == []


def test_tap_does_not_perturb_the_solve(tmp_path: Path) -> None:
    # The tap is observational: means with tap ON vs OFF are bit-equal.
    # Bug caught: the tap mutating eta / g mid-solve (any numeric
    # contamination voids the winner identity).
    fx = _fixture()
    with_tap = _miost(tmp_path, _RSPEC_C).solve(_obs(fx), _GRID, _PARAMS, 30.0)
    without = _miost(None, _RSPEC_C).solve(_obs(fx), _GRID, _PARAMS, 30.0)
    assert np.array_equal(np.asarray(with_tap.mean), np.asarray(without.mean))
