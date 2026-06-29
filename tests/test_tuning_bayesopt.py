"""BayesianOptimization is a seeded, in-bounds, drop-in SearchStrategy."""

from __future__ import annotations

from sverdrup.application.tuning.bayesopt import BayesianOptimization
from sverdrup.application.tuning.feasibility import CoherenceFeasibility, TileGeometry
from sverdrup.application.tuning.loop import tune
from sverdrup.application.tuning.objective import ConstrainedObjective
from sverdrup.application.tuning.strategy import SearchStrategy
from sverdrup.application.tuning.trial import Trial, TrialHistory, TrialRecord
from sverdrup.core.parameters import ParameterSpace
from sverdrup.core.types import UncertaintyCapability as UC
from sverdrup.methods.gmrf import MaternGMRF


def _history(space: ParameterSpace) -> TrialHistory:
    """Two feasible-scored records at the bound midpoints (warm-start fodder)."""
    h = TrialHistory(seed=1)
    for lx in (160.0, 150.0):
        p = {k: (lo + hi) / 2 for k, (lo, hi) in space.bounds.items()}
        h.records.append(
            TrialRecord(
                Trial("gmrf", p, "s", 1, "w"),
                {"lambda_x": lx, "mu_score": 0.86, "coverage_1sigma": 0.68},
                True,
            )
        )
    return h


def test_is_strategy_and_in_bounds() -> None:
    # Behavior: conforms to the SearchStrategy Protocol; every proposal is an
    # in-bounds dict over exactly the space's keys.
    # Bug caught: optuna FloatDistribution wired with wrong/swapped bounds would
    # emit values outside [lo, hi] -> the loop would tune illegal params.
    space = MaternGMRF().parameter_space()
    assert isinstance(BayesianOptimization(seed=1), SearchStrategy)
    props = BayesianOptimization(seed=1, n=4).propose(space, _history(space))
    assert len(props) == 4
    for p in props:
        assert set(p) == set(space.bounds)
        for k, (lo, hi) in space.bounds.items():
            assert lo <= p[k] <= hi


def test_determinism() -> None:
    # Behavior: same seed + same history -> byte-identical proposals.
    # Bug caught: an unseeded (or clock-seeded) TPESampler would make sweeps
    # irreproducible, breaking the tuner-wide determinism invariant.
    space = MaternGMRF().parameter_space()
    a = BayesianOptimization(seed=7, n=4).propose(space, _history(space))
    b = BayesianOptimization(seed=7, n=4).propose(space, _history(space))
    assert a == b


class _SpyScorer:
    """Fake scorer (solve boundary only): records submits, scores by param sum."""

    def __init__(self) -> None:
        self.submits: list[dict[str, float]] = []

    def score(
        self,
        method_name: str,
        params: dict[str, float],
        split: object,
        seed: int,
        window: object,
    ) -> dict[str, float]:
        """Return admissible POINTWISE scores; λx varies so the objective can rank."""
        self.submits.append(params)
        return {
            "lambda_x": 200.0 - sum(params.values()) * 1e-3,
            "mu_score": 0.86,
            "coverage_1sigma": 0.68,
        }


class _FakeSplit:
    id = "split0"


class _FakeWindow:
    id = "tile0"


def test_dropin_into_tune() -> None:
    # Behavior (AC #3): tune() accepts BayesianOptimization with no signature
    # change; proposals flow through the loop, get scored, and a winner emerges
    # with in-bounds params.
    # Bug caught: if propose() returned the wrong type (dict not list[dict], or
    # values the loop/objective can't consume), tune() would crash or never
    # score -> the drop-in contract is broken.
    space = MaternGMRF().parameter_space()
    scorer = _SpyScorer()
    result = tune(
        method_name="gmrf",
        space=space,
        strategy=BayesianOptimization(seed=3, n=4),
        predicate=CoherenceFeasibility(),
        objective=ConstrainedObjective(),
        scorer=scorer,
        split=_FakeSplit(),
        seed=3,
        window=_FakeWindow(),
        tile_geometry=TileGeometry(10.0, 100.0, "single"),
        required_capabilities=frozenset({UC.POINT}),  # single-tile -> all feasible
        rounds=1,
    )
    assert len(scorer.submits) == 4  # all four proposals were solved/scored
    assert result.winner is not None
    assert set(result.winner.trial.params) == set(space.bounds)
    for k, (lo, hi) in space.bounds.items():
        assert lo <= result.winner.trial.params[k] <= hi
