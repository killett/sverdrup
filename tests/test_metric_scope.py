"""MetricScope keeps cross-seam metrics out of the tuner objective by construction."""

from __future__ import annotations

from sverdrup.core.evaluation import (
    ContextKey,
    EvalContext,
    Evaluator,
    MetricScope,
    Registry,
)
from sverdrup.eval.accuracy import Accuracy
from sverdrup.eval.calibration import Calibration
from sverdrup.eval.groundtrack import GroundTrack


class _FakeCrossSeam:
    name = "coherence"
    required_context: frozenset[ContextKey] = frozenset()
    metric_scope = MetricScope.CROSS_SEAM

    def evaluate(self, result: object, context: EvalContext) -> dict[str, float]:
        return {"coherence": 0.5}


def test_pointwise_filters_out_cross_seam() -> None:
    # Behavior: Registry.pointwise() drops CROSS_SEAM evaluators.
    # Bug it catches: a coherence (JOINT) metric leaking into the objective vector.
    reg = Registry([Accuracy(), Calibration(), GroundTrack(), _FakeCrossSeam()])
    pw = reg.pointwise()
    names = {e.name for e in pw.applicable({k for k in _all_keys()})}
    assert "coherence" not in names
    assert {"accuracy", "calibration", "groundtrack"} <= names


def test_existing_evaluators_are_pointwise() -> None:
    for ev in (Accuracy(), Calibration(), GroundTrack()):
        assert ev.metric_scope is MetricScope.POINTWISE


def test_evaluator_satisfies_protocol_with_metric_scope() -> None:
    assert isinstance(Accuracy(), Evaluator)


def _all_keys() -> set[ContextKey]:
    return set(ContextKey)
