import numpy as np

from regatta.core.evaluation import ContextKey, EvalContext
from regatta.eval.accuracy import Accuracy


def test_rmse_uses_exact_eval_point_mean():
    ev = Accuracy()
    assert (
        ContextKey.WITHHELD_OBS in ev.required_context
        or ContextKey.TRUTH in ev.required_context
        or ev.required_context == frozenset()
    )
    ctx = EvalContext({ContextKey.WITHHELD_OBS: {"values": np.array([1.0, 2.0])}})
    result = {"eval_mean": np.array([1.1, 1.9])}
    scores = ev.evaluate(result, ctx)
    assert abs(scores["rmse"] - np.sqrt((0.01 + 0.01) / 2)) < 1e-9
