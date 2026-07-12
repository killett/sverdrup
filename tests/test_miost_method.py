"""Tests for the window-cache Miost Method (spec §4.2 hardenings; seams e, f)."""

from __future__ import annotations

import numpy as np
import pytest

from sverdrup.core.grid import GridSpec
from sverdrup.core.method import Method
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
from sverdrup.core.parameters import ConstantProvider
from sverdrup.methods.miost import Miost, MiostPointDistribution
from sverdrup.methods.registry import METHODS

PARAMS = ConstantProvider(
    {"spacing_alpha": 1.5, "log10_rho": 1.3, "q_slope": 2.0, "l_t_days": 10.0}
)
GRID = GridSpec.lonlat(np.linspace(296.0, 304.0, 9), np.linspace(34.0, 42.0, 9))


def _obs(
    n: int = 300, t_lo: float = -30.0, t_hi: float = 100.0, seed: int = 5
) -> ObsWindow:
    rng = np.random.default_rng(seed)
    t = np.concatenate([[t_lo, t_hi], rng.uniform(t_lo, t_hi, n - 2)])
    return ObsWindow.from_arrays(
        lon=rng.uniform(296, 304, n),
        lat=rng.uniform(34, 42, n),
        time=t,
        values=rng.standard_normal(n) * 0.1,
        error_model=DiagonalErrorModel(np.full(n, 0.03**2)),
    )


OBS = _obs()


def test_protocol_compliant_and_registered() -> None:
    """Registered miost is the SHIPPED SAMPLES product (capability flip).

    Catches: the flip regressing to the POINT class default (bars_for would
    silently drop the coverage bar), or the accepted (m, root, s*) drifting
    from the signed Stage-B gate record.
    """
    from sverdrup.core.types import UncertaintyCapability
    from sverdrup.methods.miost import (
        PHASE8_CLIP_HI,
        PHASE8_CLIP_LO,
        PHASE8_FIT_ID,
        PHASE8_POLY_COEFFS,
        STAGE_B_MEMBERS,
        STAGE_B_ROOT,
    )

    m = Miost()
    assert isinstance(m, Method)
    assert m.native_capability is UncertaintyCapability.POINT  # class default
    shipped = METHODS["miost"]()
    assert isinstance(shipped, Miost)
    assert shipped.native_capability is UncertaintyCapability.SAMPLES
    assert shipped.members == STAGE_B_MEMBERS == 100
    assert shipped.member_root == STAGE_B_ROOT
    # Phase-8 capability flip (Task 12): the shipped product now carries the
    # winning clipped-poly field, superseding the Stage-B scalar s*.
    from sverdrup.distributions.miost_ensemble import ClipSpec, PolyCalibration

    assert shipped._calibration == PolyCalibration(
        coeffs=PHASE8_POLY_COEFFS,
        clip=ClipSpec(lo_log_s=PHASE8_CLIP_LO, hi_log_s=PHASE8_CLIP_HI),
        fit_id=PHASE8_FIT_ID,
    )


def test_flip_observed_bars_include_coverage() -> None:
    """bars_for(registered miost capability) now includes coverage (spec 7.4 AC).

    Catches: the capability-derived bars machinery not seeing the flip —
    the Stage-B calibration bar would silently vanish from acceptance.
    """
    from sverdrup.application.tuning.objective import bars_for

    shipped = METHODS["miost"]()
    assert isinstance(shipped, Miost)
    metrics = [b.metric for b in bars_for(shipped.native_capability)]
    assert "coverage_1sigma" in metrics and "mu_score" in metrics


def test_solve_returns_point_distribution() -> None:
    d = Miost().solve(OBS, GRID, PARAMS, time_days=30.0)
    assert isinstance(d, MiostPointDistribution)
    assert np.isfinite(np.asarray(d.mean)).all()


def test_cache_repeat_day_equals_fresh() -> None:
    m1, m2 = Miost(), Miost()
    d_a = m1.solve(OBS, GRID, PARAMS, time_days=30.0)
    _ = m1.solve(OBS, GRID, PARAMS, time_days=35.0)  # same window pair, cache warm
    d_b = m1.solve(OBS, GRID, PARAMS, time_days=30.0)  # repeat day
    d_fresh = m2.solve(OBS, GRID, PARAMS, time_days=30.0)
    np.testing.assert_array_equal(np.asarray(d_a.mean), np.asarray(d_b.mean))
    np.testing.assert_array_equal(np.asarray(d_a.mean), np.asarray(d_fresh.mean))


def test_cache_off_identical() -> None:
    d_on = Miost().solve(OBS, GRID, PARAMS, time_days=30.0)
    d_off = Miost(cache=False).solve(OBS, GRID, PARAMS, time_days=30.0)
    np.testing.assert_array_equal(np.asarray(d_on.mean), np.asarray(d_off.mean))


def test_span_assert_raises_loud() -> None:
    """Obs missing the window's temporal margin -> ValueError naming the span."""
    short = _obs(t_lo=20.0, t_hi=40.0)  # cannot support window [-18, 42] +- L_t
    with pytest.raises(ValueError, match="span"):
        Miost().solve(short, GRID, PARAMS, time_days=30.0)


def test_obs_fingerprint_busts_cache() -> None:
    """A different full-span obs set must not hit the old cache entry."""
    m = Miost()
    d1 = m.solve(OBS, GRID, PARAMS, time_days=30.0)
    d2 = m.solve(_obs(seed=6), GRID, PARAMS, time_days=30.0)
    assert not np.array_equal(np.asarray(d2.mean), np.asarray(d1.mean))


def test_zero_obs_window_finite() -> None:
    empty = ObsWindow.from_arrays(
        lon=np.zeros(0),
        lat=np.zeros(0),
        time=np.zeros(0),
        values=np.zeros(0),
        error_model=DiagonalErrorModel(np.zeros(0)),
    )
    d = Miost().solve(empty, GRID, PARAMS, time_days=30.0)
    assert np.isfinite(np.asarray(d.mean)).all()


def test_params_key_serializes_contract() -> None:
    key = Miost()._params_key(PARAMS, GRID)
    for token in ("alpha", "rho", "q_slope", "l_t", "pcg_rtol", "ladder"):
        assert token in key


def test_convergence_telemetry_appended_per_fresh_solve() -> None:
    """Budgeted-solve honesty: every fresh window solve appends achieved residuals
    to miost.CONVERGENCE_LOG; cache hits do not re-append."""
    from sverdrup.methods import miost as miost_mod

    miost_mod.CONVERGENCE_LOG.clear()
    m = Miost()
    m.solve(OBS, GRID, PARAMS, time_days=30.0)  # windows w0 + w1: 2 fresh solves
    assert len(miost_mod.CONVERGENCE_LOG) == 2
    entry = miost_mod.CONVERGENCE_LOG[0]
    assert {"window", "iterations", "final_rel_residual", "params_key_hash"} <= set(
        entry
    )
    assert float(entry["final_rel_residual"]) > 0  # type: ignore[arg-type]
    m.solve(OBS, GRID, PARAMS, time_days=30.0)  # cache hit: nothing appended
    assert len(miost_mod.CONVERGENCE_LOG) == 2


def test_pcg_overrides_enter_params_key() -> None:
    """Solver settings are part of what eta depends on — overrides must bust the cache."""
    m = Miost(pcg_rtol=1e-8, pcg_maxiter=2000)
    key = m._params_key(PARAMS, GRID)
    assert "pcg_rtol=1e-08" in key and "pcg_maxiter=2000" in key
    default_key = Miost()._params_key(PARAMS, GRID)
    assert key != default_key


def test_parameter_space_boxes() -> None:
    space = Miost().parameter_space()
    assert space.bounds == {
        "spacing_alpha": (0.5, 1.5),
        "log10_rho": (-2.0, 3.0),
        "q_slope": (0.0, 4.0),
        "l_t_days": (5.0, 12.0),
    }


def test_s_cache_bounded_and_g_freed() -> None:
    """<=2 S matrices live; the eta cache holds vectors, never G matrices."""
    m = Miost()
    wide = _obs(t_lo=-30.0, t_hi=145.0)  # spans w0..w2 support intervals
    for day in (10.0, 55.0, 100.0):  # marches across 3 windows
        m.solve(wide, GRID, PARAMS, time_days=day)
    assert len(m._s_cache) <= 2
    for eta in m._eta_cache.values():
        assert isinstance(eta, np.ndarray) and eta.ndim == 1
