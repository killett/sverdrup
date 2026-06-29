"""SearchStrategy proposes within-bounds, deterministic, method-agnostic params."""

from __future__ import annotations

from sverdrup.application.tuning.strategy import (
    RandomSearch,
    SearchStrategy,
    SobolSearch,
)
from sverdrup.application.tuning.trial import TrialHistory
from sverdrup.core.parameters import ParameterSpace
from sverdrup.methods.gmrf import MaternGMRF
from sverdrup.methods.oi import OptimalInterpolation


def _within(space: ParameterSpace, proposals: list[dict[str, float]]) -> bool:
    for p in proposals:
        assert set(p) == set(space.bounds)
        for k, (lo, hi) in space.bounds.items():
            if not (lo <= p[k] <= hi):
                return False
    return True


def test_protocol_runtime_checkable() -> None:
    assert isinstance(SobolSearch(seed=1), SearchStrategy)


def test_within_bounds_both_methods() -> None:
    h = TrialHistory(seed=1)
    for method in (OptimalInterpolation(), MaternGMRF()):
        space = method.parameter_space()
        assert _within(space, SobolSearch(seed=1, n=8).propose(space, h))
        assert _within(space, RandomSearch(seed=1, n=8).propose(space, h))


def test_determinism() -> None:
    space = OptimalInterpolation().parameter_space()
    h = TrialHistory(seed=1)
    assert SobolSearch(seed=3, n=8).propose(space, h) == SobolSearch(
        seed=3, n=8
    ).propose(space, h)
