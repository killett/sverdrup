"""StoredGFeasibility + CompositeFeasibility + exclusion-reason recording (spec §5.1)."""

from __future__ import annotations

from sverdrup.application.tuning.feasibility import (
    CompositeFeasibility,
    StoredGFeasibility,
    TileGeometry,
)
from sverdrup.application.tuning.loop import tune
from sverdrup.application.tuning.objective import ConstrainedObjective
from sverdrup.core.parameters import ParameterSpace
from sverdrup.methods.miost_sizing import nnz_g

GEOM = TileGeometry(10.0, 0.0, "miost-single", n_tiles=1)


def test_predicted_bytes_is_sizing_arithmetic() -> None:
    """Single arithmetic: predicted bytes come from miost_sizing, no local formula."""
    p = StoredGFeasibility(n_obs_max=57_000, budget_bytes=8e9)
    expected = nnz_g(57_000, alpha=0.75, n_dir=8, lam_min=80.0, lam_max=905.0) * 12
    assert p.predicted_bytes({"spacing_alpha": 0.75}) == expected


def test_l_t_free() -> None:
    """No L_t term: nnz is L_t-invariant (D3)."""
    p = StoredGFeasibility(n_obs_max=57_000)
    a = p.predicted_bytes({"spacing_alpha": 1.0, "l_t_days": 5.0})
    b = p.predicted_bytes({"spacing_alpha": 1.0, "l_t_days": 12.0})
    assert a == b


def test_budget_boundary_and_reason() -> None:
    """Halo-priced fine corner alpha=0.5 exceeds 8 GB (D7); explain names the terms."""
    p = StoredGFeasibility(n_obs_max=57_000, budget_bytes=8e9)
    fine = {"spacing_alpha": 0.5}
    coarse = {"spacing_alpha": 1.5}
    assert not p.feasible(fine, GEOM, frozenset())
    assert p.feasible(coarse, GEOM, frozenset())
    reason = p.explain(fine)
    assert reason is not None and "stored-G" in reason and "8.0e+09" in reason
    assert p.explain(coarse) is None


def test_n_concurrent_scales_accounting() -> None:
    """n_concurrent * bytes <= budget (execution contract, spec §4.2)."""
    one = StoredGFeasibility(n_obs_max=57_000, budget_bytes=8e9, n_concurrent=1)
    two = StoredGFeasibility(n_obs_max=57_000, budget_bytes=8e9, n_concurrent=2)
    mid = {"spacing_alpha": 0.75}
    assert one.feasible(mid, GEOM, frozenset())
    assert not two.feasible(mid, GEOM, frozenset())


def test_composite_all_of_first_reason() -> None:
    """Composite = logical AND; the FIRST failing member's explain() is the reason."""
    tight = StoredGFeasibility(n_obs_max=10**6, budget_bytes=1.0)
    loose = StoredGFeasibility(n_obs_max=100, budget_bytes=1e15)
    comp = CompositeFeasibility((loose, tight))
    params = {"spacing_alpha": 1.0}
    assert not comp.feasible(params, GEOM, frozenset())
    reason = comp.explain(params)
    assert reason is not None and "stored-G" in reason
    assert CompositeFeasibility((loose,)).feasible(params, GEOM, frozenset())


class _OneShotStrategy:
    def propose(self, space: ParameterSpace, history: object) -> list[dict[str, float]]:
        return [{"spacing_alpha": 1.0}]


def test_loop_records_exclusion_reason() -> None:
    """tune() records explain() for infeasible trials; predicates without explain -> None."""
    comp = CompositeFeasibility(
        (StoredGFeasibility(n_obs_max=10**6, budget_bytes=1.0),)
    )
    result = tune(
        method_name="miost",
        space=ParameterSpace(bounds={"spacing_alpha": (0.5, 1.5)}),
        strategy=_OneShotStrategy(),
        predicate=comp,
        objective=ConstrainedObjective(),
        scorer=None,  # type: ignore[arg-type]  # gate excludes before any solve
        split=None,
        seed=1,
        window=None,
        tile_geometry=GEOM,
        required_capabilities=frozenset(),
        on_empty="return_history",
    )
    rec = result.history.records[0]
    assert not rec.feasible
    assert rec.exclusion_reason is not None and "stored-G" in rec.exclusion_reason


class _NoExplainPredicate:
    def feasible(
        self, params: dict[str, float], tile_geometry: object, caps: object
    ) -> bool:
        return False


def test_loop_back_compat_no_explain() -> None:
    result = tune(
        method_name="miost",
        space=ParameterSpace(bounds={"spacing_alpha": (0.5, 1.5)}),
        strategy=_OneShotStrategy(),
        predicate=_NoExplainPredicate(),
        objective=ConstrainedObjective(),
        scorer=None,  # type: ignore[arg-type]
        split=None,
        seed=1,
        window=None,
        tile_geometry=GEOM,
        required_capabilities=frozenset(),
        on_empty="return_history",
    )
    rec = result.history.records[0]
    assert not rec.feasible and rec.exclusion_reason is None
