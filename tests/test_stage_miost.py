"""Stage-runner seams for miost: capability-derived objective + report history."""

from __future__ import annotations

from sverdrup.application.tuning.stage_a import StageAReport, _objective_for


def test_objective_for_point_method_omits_coverage() -> None:
    """A POINT method is never judged on a coverage bar it cannot emit.

    Fold B unchanged post-flip — exercised via a POINT-configured miost.
    (Registry role-split, Phase-10 Task 1: "miost" lives in SHIPPED now;
    the shipped product's coverage-bar assertion is
    test_miost_method.py::test_flip_observed_bars_include_coverage.)
    """
    from sverdrup.methods import registry
    from sverdrup.methods.miost import Miost

    registry.METHODS["miost-point-test"] = Miost
    try:
        bars = _objective_for("miost-point-test").bars
        assert [b.metric for b in bars] == ["mu_score"]
    finally:
        registry.METHODS.pop("miost-point-test", None)


def test_objective_for_samples_methods_keep_coverage() -> None:
    """OI/GMRF (SAMPLES) keep the default mu + coverage bars — no behavior change."""
    for name in ("oi", "gmrf"):
        metrics = [b.metric for b in _objective_for(name).bars]
        assert metrics == ["mu_score", "coverage_1sigma"]


def test_stage_report_carries_history_field() -> None:
    """Runner surfaces infeasible reasons from the report's history (default None)."""
    assert StageAReport.__dataclass_fields__["history"].default is None


def test_search_entry_is_point_configured() -> None:
    """The sweep searches "miost-point" (POINT), never the shipped product.

    Catches: a sweep instantiating the shipped SAMPLES miost per trial —
    100-member batches per trial, the exact cost class spec 6.1 forbids.
    """
    import inspect

    from sverdrup.application.tuning import stage_miost
    from sverdrup.core.types import UncertaintyCapability
    from sverdrup.methods.miost import Miost
    from sverdrup.methods.registry import METHODS

    search = METHODS["miost-point"]()
    assert isinstance(search, Miost)
    assert search.native_capability is UncertaintyCapability.POINT
    assert 'method_name="miost-point"' in inspect.getsource(stage_miost.run_stage_miost)
