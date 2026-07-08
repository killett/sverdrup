"""PeakFeasibility — the Task-22 re-grounded resource predicate.

Prices the MODELED PEAK RSS (component-sum, validated 2026-07-07 against
the instrumented windowed member-gen run: model/measured 1.11x windowed,
1.08x single-window) against a budget derived from MEASURED available RAM
— replacing the stored-G-only 8e9 constant whose ignored transients and
workspace were the OOM-#1/#2 class.
"""

from __future__ import annotations

import pytest

from sverdrup.application.tuning.feasibility import (
    CompositeFeasibility,
    PeakFeasibility,
    TileGeometry,
)
from sverdrup.methods.miost_sizing import peak_model

GEOM = TileGeometry(10.0, 0.0, "miost-single", n_tiles=1)


def _total(alpha: float, m: int = 1) -> float:
    return peak_model(
        alpha=alpha,
        n_dir=8,
        window_days=60.0,
        lam_min=80.0,
        n_obs=16_066,
        m=m,
        lam_max=905.0,
    ).total


def test_boundary_excludes_fine_alpha_admits_coarse() -> None:
    """The predicate thresholds the validated peak model, not stored-G.

    Budget placed BETWEEN the alpha=1.5 and alpha=0.5 modeled peaks: coarse
    admitted, fine excluded with a named reason. Bug caught: predicate
    pricing stored-G only (both alphas would flip together at a very
    different budget) or an inverted comparison.
    """
    lo, hi = _total(1.5), _total(0.5)
    assert lo < hi  # sanity: finer spacing costs more
    p = PeakFeasibility(n_obs_max=16_066, budget_bytes=(lo + hi) / 2)
    assert p.feasible({"spacing_alpha": 1.5}, GEOM, frozenset())
    assert not p.feasible({"spacing_alpha": 0.5}, GEOM, frozenset())
    reason = p.explain({"spacing_alpha": 0.5})
    assert reason is not None and "peak" in reason and "budget" in reason
    assert p.explain({"spacing_alpha": 1.5}) is None


def test_budget_from_measured_available_ram(monkeypatch: pytest.MonkeyPatch) -> None:
    """budget=None derives from MEASURED MemAvailable x safety at construction.

    Bug caught: the kB-vs-bytes /proc/meminfo confusion (a 1024x budget
    error) or the safety factor dropped — either re-creates the OOM class
    the owner ordered this predicate to close.
    """
    from sverdrup.application.tuning import feasibility as feas

    monkeypatch.setattr(feas, "_mem_available_bytes", lambda: 10e9)
    p = PeakFeasibility(n_obs_max=16_066)
    assert p.budget_bytes == pytest.approx(0.8 * 10e9)


def test_member_batches_reprice_the_same_alpha() -> None:
    """A large member batch must exclude a config the m=1 predicate admits.

    The OOM-#2 class: m-scaled RHS + PCG workspace grow the SOLVE phase
    past the assembly phase (at alpha=1.0 the crossover is ~m=250, so
    m=1000 is decisively solve-dominated). Budget set between the m=1 and
    m=1000 peaks: mean-only admits, member-generation refuses. Bug caught:
    m not threaded into the peak model.
    """
    assert _total(1.0, m=1000) > _total(1.0, m=1)  # solve phase dominates
    budget = (_total(1.0, m=1) + _total(1.0, m=1000)) / 2
    mean_only = PeakFeasibility(n_obs_max=16_066, budget_bytes=budget)
    members = PeakFeasibility(n_obs_max=16_066, m=1000, budget_bytes=budget)
    params = {"spacing_alpha": 1.0}
    assert mean_only.feasible(params, GEOM, frozenset())
    assert not members.feasible(params, GEOM, frozenset())


def test_composes_with_first_failing_reason() -> None:
    """CompositeFeasibility surfaces PeakFeasibility's reason (invariant 5)."""
    p = PeakFeasibility(n_obs_max=16_066, budget_bytes=1.0)  # nothing fits
    comp = CompositeFeasibility((p,))
    reason = comp.explain({"spacing_alpha": 1.5})
    assert reason is not None and "peak" in reason
