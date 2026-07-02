"""Multi-round tuning feeds accumulated history forward — the mechanism BO relies on."""

from __future__ import annotations

import inspect

from sverdrup.application.tuning.feasibility import CoherenceFeasibility, TileGeometry
from sverdrup.application.tuning.loop import tune
from sverdrup.application.tuning.objective import ConstrainedObjective
from sverdrup.application.tuning.stage_a import run_stage_a
from sverdrup.application.tuning.stage_b import run_stage_b
from sverdrup.core.parameters import ParameterSpace
from sverdrup.core.types import UncertaintyCapability as UC
from sverdrup.methods.gmrf import MaternGMRF


class _HistoryRecordingStrategy:
    """Fake SearchStrategy: records history size at each propose call, returns a fixed point."""

    def __init__(self, n: int) -> None:
        self.n = n
        self.history_lengths: list[int] = []

    def propose(self, space: ParameterSpace, history: object) -> list[dict[str, float]]:
        self.history_lengths.append(len(history.records))  # type: ignore[attr-defined]
        mid = {k: (lo + hi) / 2 for k, (lo, hi) in space.bounds.items()}
        return [dict(mid) for _ in range(self.n)]


class _AdmissibleScorer:
    def score(self, method_name, params, split, seed, window):  # noqa: ANN001, ANN201
        return {"lambda_x": 120.0, "mu_score": 0.86, "coverage_1sigma": 0.68}


class _FakeSplit:
    id = "s"


class _FakeWindow:
    id = "w"


def _space() -> ParameterSpace:
    return MaternGMRF().parameter_space()


def test_multi_round_feeds_accumulated_history() -> None:
    # Behavior: rounds=R runs propose R times, each seeing the prior rounds' recorded trials.
    # Bug it catches: a regression that breaks the range(rounds) loop or stops passing the
    # growing history into propose -> BO silently reverts to random density (rounds=1 behavior).
    strat = _HistoryRecordingStrategy(n=2)
    tune(
        method_name="gmrf",
        space=_space(),
        strategy=strat,
        predicate=CoherenceFeasibility(),
        objective=ConstrainedObjective(),
        scorer=_AdmissibleScorer(),
        split=_FakeSplit(),
        seed=1,
        window=_FakeWindow(),
        tile_geometry=TileGeometry(1e9, 1.0, "single"),
        required_capabilities=frozenset({UC.POINT}),
        rounds=3,
        on_empty="return_history",
    )
    assert strat.history_lengths == [
        0,
        2,
        4,
    ]  # 3 rounds; history grows by n=2 each round


def test_stage_runners_expose_rounds_default_one() -> None:
    # Contract: the stage runners accept `rounds` and default it to 1 (production unchanged).
    # Bug it catches: dropping the parameter so BO can never be driven multi-round.
    for fn in (run_stage_a, run_stage_b):
        p = inspect.signature(fn).parameters
        assert "rounds" in p, fn.__name__
        assert p["rounds"].default == 1, fn.__name__
