import numpy as np

from sverdrup.core.evaluation import ContextKey, EvalContext
from sverdrup.eval.accuracy import Accuracy


def test_rmse_uses_exact_eval_point_mean():
    ev = Accuracy()
    ctx = EvalContext({ContextKey.WITHHELD_OBS: {"values": np.array([1.0, 2.0])}})
    result = {"eval_mean": np.array([1.1, 1.9])}
    scores = ev.evaluate(result, ctx)
    assert abs(scores["rmse"] - np.sqrt((0.01 + 0.01) / 2)) < 1e-9


def test_optional_context_declared_and_neither_branch_returns_empty():
    # Behavior: Accuracy declares TRUTH/WITHHELD_OBS as OPTIONAL (required
    # stays empty) and returns {} when neither is present.
    # Bug it catches: raising (or scoring garbage) without references —
    # the pinned {} precedent feeds Task-6's visible-skip-row path.
    ev = Accuracy()
    assert ev.optional_context == frozenset({ContextKey.TRUTH, ContextKey.WITHHELD_OBS})
    assert ev.required_context == frozenset()
    assert ev.evaluate({"eval_mean": np.array([1.0])}, EvalContext({})) == {}
