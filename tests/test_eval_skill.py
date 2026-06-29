"""mu_score is a higher-better skill score, distinct from raw rmse, never on c2."""

from __future__ import annotations

import numpy as np

from sverdrup.core.evaluation import ContextKey, EvalContext, MetricScope
from sverdrup.eval.skill import NormalizedSkillScore
from sverdrup.eval.skill_score import leaderboard_nrmse


def test_perfect_and_zero_scores() -> None:
    obs = np.array([1.0, -2.0, 0.5, 3.0])
    assert leaderboard_nrmse(obs, obs) == 1.0
    assert leaderboard_nrmse(obs, np.zeros_like(obs)) == 0.0


def test_evaluator_emits_mu_score_pointwise() -> None:
    # Bug it catches: mu_score named like raw rmse / tagged so it can't enter the objective.
    ev = NormalizedSkillScore()
    assert ev.metric_scope is MetricScope.POINTWISE
    obs = np.array([1.0, -2.0, 0.5, 3.0])
    ctx = EvalContext({ContextKey.WITHHELD_OBS: {"values": obs}})
    out = ev.evaluate({"eval_mean": obs}, ctx)
    assert out["mu_score"] == 1.0
