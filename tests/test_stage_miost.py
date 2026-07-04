"""Stage-runner seams for miost: capability-derived objective + report history."""

from __future__ import annotations

from sverdrup.application.tuning.stage_a import StageAReport, _objective_for


def test_objective_for_point_method_omits_coverage() -> None:
    """miost (POINT) must never be judged on a coverage bar it cannot emit."""
    bars = _objective_for("miost").bars
    assert [b.metric for b in bars] == ["mu_score"]


def test_objective_for_samples_methods_keep_coverage() -> None:
    """OI/GMRF (SAMPLES) keep the default mu + coverage bars — no behavior change."""
    for name in ("oi", "gmrf"):
        metrics = [b.metric for b in _objective_for(name).bars]
        assert metrics == ["mu_score", "coverage_1sigma"]


def test_stage_report_carries_history_field() -> None:
    """Runner surfaces infeasible reasons from the report's history (default None)."""
    assert StageAReport.__dataclass_fields__["history"].default is None
