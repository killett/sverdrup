"""Stage-B seam-dispersion diagnostic helpers (plan Task 18).

The script's load-bearing logic — exclusive-day window merge and the SPARSE
S-path per-day member-std evaluation — is pinned here against the dense-gamma
reference (`MiostEnsembleDistribution`), which Task 16 proved exact.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from sverdrup.core.grid import GridSpec
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
from sverdrup.core.parameters import ConstantProvider
from sverdrup.distributions.miost_ensemble import (
    MiostEnsembleDistribution,
    ensemble_provenance,
)
from sverdrup.methods.miost import Miost
from sverdrup.methods.miost_windows import WindowPlan

_SCRIPT = (
    Path(__file__).resolve().parents[1] / "scripts" / "diag_miost_seam_dispersion.py"
)

M = 6
ROOT = 12345
PARAMS = ConstantProvider(
    {"spacing_alpha": 1.5, "log10_rho": 1.3, "q_slope": 2.0, "l_t_days": 10.0}
)
GRID = GridSpec.lonlat(np.linspace(296.0, 304.0, 6), np.linspace(34.0, 42.0, 6))
TWO_WIN = (0.0, 45.0)  # blend zone [45, 60]


def _obs(n: int = 80) -> ObsWindow:
    rng = np.random.default_rng(7)
    t = rng.uniform(-12.0, 117.0, n)  # spans both windows' +-L_t support
    err = DiagonalErrorModel(np.full(n, 0.01))
    mission = np.asarray(["alg", "s3a", "h2g", "j2n"])[rng.integers(0, 4, n)]
    return ObsWindow.from_arrays(
        rng.uniform(296, 304, n),
        rng.uniform(34, 42, n),
        t,
        rng.standard_normal(n) * 0.1,
        err,
        mission,
    )


@pytest.fixture(scope="module")
def diag_mod() -> Any:
    spec = importlib.util.spec_from_file_location("diag_miost_seam_dispersion", _SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["diag_miost_seam_dispersion"] = mod
    spec.loader.exec_module(mod)
    yield mod
    del sys.modules["diag_miost_seam_dispersion"]


@pytest.fixture(scope="module")
def merged(
    diag_mod: Any,
) -> tuple[Any, dict[str, Any], dict[str, Any], dict[str, float]]:
    """(spec, etas_a, anoms, starts) merged over the two-window plan."""
    method = Miost(plan=WindowPlan(starts=TWO_WIN))
    return diag_mod.merged_members(method, _obs(), GRID, PARAMS, m=M, root=ROOT)


def test_exclusive_days_cover_every_production_window(diag_mod: Any) -> None:
    """Every production window gets a day covered ONLY by it.

    Bug caught: naive midpoint arithmetic picks day ~352 for the right-aligned
    last window [322, 382] — inside its 35-d overlap with w7 [297, 357] — so
    the merge would solve w7 twice and w8's members would carry w7 blending.
    Hand: w8's exclusive range is (357, 382], so its day must be >= 358.
    """
    plan = WindowPlan()
    ex = diag_mod.exclusive_days(plan)
    assert set(ex) == {w.id for w in plan.windows}
    assert len(set(ex.values())) == 9
    for w in plan.windows:
        assert [c.id for c in plan.covering(ex[w.id])] == [w.id]
    assert ex[plan.windows[-1].id] >= 358.0


def test_exclusive_days_raises_when_window_never_alone(diag_mod: Any) -> None:
    """A window with no exclusive day must raise, never be silently dropped.

    Bug caught: silent skip merges an ensemble MISSING that window's
    anomalies — a variance hole exactly where dispersion is being measured.
    Hand: with starts (0, 5, 10) and W=60, window [5, 65] is always covered
    together with [0, 60] (days < 60) or [10, 70] (days > 60).
    """
    plan = WindowPlan(starts=(0.0, 5.0, 10.0))
    never_alone = plan.windows[1].id
    with pytest.raises(ValueError, match=never_alone.replace("+", r"\+")):
        diag_mod.exclusive_days(plan)


def test_merged_ensemble_matches_direct_sample_members(
    merged: tuple[Any, dict[str, Any], dict[str, Any], dict[str, float]],
) -> None:
    """Merged per-window anomalies == one direct sample_members call (bitwise).

    Bug caught: a per-window CRN root (root+k) instead of the shared root, or
    storing raw members instead of anomalies — identity-keyed CRN guarantees
    the production blend-day call reproduces both windows exactly.
    """
    _, etas_a, anoms, starts = merged
    direct = (
        Miost(plan=WindowPlan(starts=TWO_WIN))
        .sample_members(_obs(), GRID, PARAMS, 50.0, m=M, root=ROOT)
        .underlying
    )  # day 50 = blend: covers BOTH windows; raw internals via .underlying (Phase-9 §3)
    assert set(anoms) == set(direct._anoms)
    assert set(etas_a) == set(direct._etas_a)
    for wid in direct._anoms:
        np.testing.assert_array_equal(anoms[wid], direct._anoms[wid])
        np.testing.assert_array_equal(etas_a[wid], direct._etas_a[wid])
        assert starts[wid] == direct._window_starts[wid]


def test_std_fields_match_dense_reference(
    diag_mod: Any,
    merged: tuple[Any, dict[str, Any], dict[str, Any], dict[str, float]],
) -> None:
    """S-path per-day member std == dense-gamma marginal_variance sqrt.

    Bug caught: dropped blend weight in the accumulation (blend day 50), a
    time_contract day/taper misalignment (interior day 20), or an m-vs-(m-1)
    ddof mismatch. The dense reference is the Task-16-pinned production path.
    """
    spec, etas_a, anoms, starts = merged
    plan = WindowPlan(starts=TWO_WIN)
    days = [20.0, 50.0]  # interior, blend
    fields = diag_mod.std_fields(spec, starts, anoms, GRID, plan, days)
    assert fields.shape == (2, GRID.shape[0] * GRID.shape[1])
    for i, day in enumerate(days):
        dense = MiostEnsembleDistribution(
            grid=GRID,
            mean=np.zeros(GRID.shape),
            provenance=ensemble_provenance(M),
            time_days=day,
            m=M,
            _spec=spec,
            _etas_a=etas_a,
            _anoms=anoms,
            _window_starts=starts,
            _w_days=plan.w_days,
        )
        ref = np.sqrt(np.asarray(dense.marginal_variance())).ravel()
        np.testing.assert_allclose(fields[i], ref, rtol=1e-10, atol=1e-14)


def test_mean_fields_match_dense_reference(
    diag_mod: Any,
    merged: tuple[Any, dict[str, Any], dict[str, Any], dict[str, float]],
) -> None:
    """S-path per-day blended MEAN == dense-gamma mean_at on the grid.

    Bug caught: a blend-weight or taper error in the mean path of the
    S-path evaluator (tune_miost_inflation's full-year mean maps) that the
    std tests cannot see — anomalies are mean-centered per window.
    """
    from sverdrup.distributions.miost_ensemble import mean_fields

    spec, etas_a, anoms, starts = merged
    plan = WindowPlan(starts=TWO_WIN)
    days = [20.0, 50.0]  # interior, blend
    fields = mean_fields(spec, starts, etas_a, GRID, plan, days)
    assert fields.shape == (2, GRID.shape[0] * GRID.shape[1])
    lon2d, lat2d = np.meshgrid(GRID.x, GRID.y)
    for i, day in enumerate(days):
        dense = MiostEnsembleDistribution(
            grid=GRID,
            mean=np.zeros(GRID.shape),
            provenance=ensemble_provenance(M),
            time_days=day,
            m=M,
            _spec=spec,
            _etas_a=etas_a,
            _anoms=anoms,
            _window_starts=starts,
            _w_days=plan.w_days,
        )
        pts = np.column_stack([lon2d.ravel(), lat2d.ravel(), np.full(lon2d.size, day)])
        np.testing.assert_allclose(
            fields[i], dense.mean_at(pts), rtol=1e-10, atol=1e-14
        )


def test_dispersion_summary_worst_case_localized(diag_mod: Any) -> None:
    """Headline ratio = worst blend day / interior MEDIAN — exactly 3.0 here.

    Bug caught: averaging over blend days (mean of 0.1, 0.1, 0.3 gives ~1.7x)
    or taking the blend median (1.0x) launders the single-seam spike that is
    the entire point of the diagnostic.
    """
    day_max = np.array([0.1] * 10 + [0.1, 0.1, 0.3])
    blend = np.array([False] * 10 + [True] * 3)
    s = diag_mod.dispersion_summary(day_max, blend)
    assert s["worst_blend"] == pytest.approx(0.3)
    assert s["interior_median"] == pytest.approx(0.1)
    assert s["ratio"] == pytest.approx(3.0)
