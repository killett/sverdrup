"""Normalized skill-score evaluator emitting mu_score (the µ hard-bar metric)."""

from __future__ import annotations

from typing import Any, cast

from sverdrup.core.evaluation import ContextKey, EvalContext, MetricScope
from sverdrup.eval.skill_score import leaderboard_nrmse


class NormalizedSkillScore:
    """``mu_score`` = normalized RMSE skill score (higher better) vs withheld obs."""

    name = "skill"
    required_context = frozenset({ContextKey.WITHHELD_OBS})
    metric_scope = MetricScope.POINTWISE

    def evaluate(self, result: object, context: EvalContext) -> dict[str, float]:
        """Return ``{"mu_score": …}`` from eval-point means vs withheld values."""
        r = cast(Any, result)
        obs = cast(Any, context.items[ContextKey.WITHHELD_OBS])["values"]
        return {"mu_score": leaderboard_nrmse(obs, r["eval_mean"])}
