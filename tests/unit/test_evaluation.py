from sverdrup.core.evaluation import (
    ContextKey,
    EvalContext,
    MetricScope,
    Objective,
    Registry,
)


class _TruthOnly:
    name = "accuracy_vs_truth"
    required_context = frozenset({ContextKey.TRUTH})
    metric_scope = MetricScope.POINTWISE

    def evaluate(self, result: object, context: EvalContext) -> dict[str, float]:
        return {"rmse": 0.0}


class _Intrinsic:
    name = "groundtrack"
    required_context = frozenset({ContextKey.ORBIT_GEOMETRY})
    metric_scope = MetricScope.POINTWISE

    def evaluate(self, result: object, context: EvalContext) -> dict[str, float]:
        return {"track_power": 0.0}


def test_registry_filters_by_available_context():
    # Bug caught: assuming a reference always exists (invariant 9).
    reg = Registry([_TruthOnly(), _Intrinsic()])
    osse = reg.applicable({ContextKey.TRUTH, ContextKey.ORBIT_GEOMETRY})
    ose = reg.applicable({ContextKey.WITHHELD_OBS, ContextKey.ORBIT_GEOMETRY})
    assert {e.name for e in osse} == {"accuracy_vs_truth", "groundtrack"}
    assert {e.name for e in ose} == {"groundtrack"}


def test_objective_is_vector_valued():
    obj = Objective(scores={"rmse": 0.1, "crps": 0.2})
    assert set(obj.scores) == {"rmse", "crps"}
