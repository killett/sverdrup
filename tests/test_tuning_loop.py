"""tune(): hard barrier before solve, POINTWISE-only scoring, no locked-test peek."""

from __future__ import annotations

import pytest

from sverdrup.application.tuning.feasibility import CoherenceFeasibility, TileGeometry
from sverdrup.application.tuning.loop import tune
from sverdrup.application.tuning.objective import ConstrainedObjective
from sverdrup.application.tuning.strategy import SobolSearch
from sverdrup.core.parameters import ParameterSpace
from sverdrup.core.types import UncertaintyCapability as UC
from sverdrup.methods.gmrf import MaternGMRF
from sverdrup.methods.oi import OptimalInterpolation


class _SpyScorer:
    """Fake scorer: records submits, returns scripted POINTWISE scores. No real solve."""

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
        """Record the submit and return scripted admissible POINTWISE scores."""
        self.submits.append(params)
        # finer λx for larger length_scale, all admissible
        return {
            "lambda_x": 200.0 - params["length_scale"] * 0.05,
            "mu_score": 0.86,
            "coverage_1sigma": 0.68,
        }


class _FakeSplit:
    id = "split0"


class _FakeWindow:
    id = "tile0"


def _oi_space() -> ParameterSpace:
    return OptimalInterpolation().parameter_space()


def _gmrf_space() -> ParameterSpace:
    return MaternGMRF().parameter_space()


def test_hard_barrier_no_submit_for_infeasible() -> None:
    # TEST 4: an infeasible (range, tile) trial is never solved/scored.
    scorer = _SpyScorer()
    geom = TileGeometry(12.0, 400.0, "g", n_tiles=2)  # multi-tile joint -> infeasible
    result = tune(
        method_name="gmrf",
        space=_gmrf_space(),
        strategy=SobolSearch(seed=1, n=4),
        predicate=CoherenceFeasibility(),
        objective=ConstrainedObjective(),
        scorer=scorer,
        split=_FakeSplit(),
        seed=1,
        window=_FakeWindow(),
        tile_geometry=geom,
        required_capabilities=frozenset({UC.SAMPLES}),
        rounds=1,
        on_empty="return_history",
    )
    assert scorer.submits == []  # nothing solved
    assert all(r.scores is None and not r.feasible for r in result.history.records)


def test_pointwise_only_and_no_their_eval(monkeypatch: pytest.MonkeyPatch) -> None:
    # TEST 5 + TEST 2 (search half): only POINTWISE scores recorded; their_eval untouched.
    import sverdrup.validation.their_eval as te

    called = {"n": 0}
    monkeypatch.setattr(
        te, "score", lambda *a, **k: called.__setitem__("n", called["n"] + 1)
    )
    scorer = _SpyScorer()
    result = tune(
        method_name="oi",
        space=_oi_space(),
        strategy=SobolSearch(seed=1, n=4),
        predicate=CoherenceFeasibility(),
        objective=ConstrainedObjective(),
        scorer=scorer,
        split=_FakeSplit(),
        seed=1,
        window=_FakeWindow(),
        tile_geometry=TileGeometry(10.0, 100.0, "single"),
        required_capabilities=frozenset({UC.POINT}),  # single-tile -> all feasible
        rounds=1,
    )
    assert called["n"] == 0  # locked test never touched during search
    for r in result.history.feasible_scored():
        assert r.scores is not None
        assert "coherence" not in r.scores  # only POINTWISE keys present


class _DegenerateScorer:
    """Scorer that always raises UnresolvedScaleError (every map is degenerate)."""

    def score(
        self,
        method_name: str,
        params: dict[str, float],
        split: object,
        seed: int,
        window: object,
    ) -> dict[str, float]:
        from sverdrup.eval.spectral import UnresolvedScaleError

        raise UnresolvedScaleError("no crossing")


def test_unresolved_scale_recorded_not_crashed() -> None:
    # Behavior: a degenerate trial is recorded feasible-but-unscorable; sweep continues;
    # an all-degenerate sweep ends in the loud NoAdmissibleTrial (never a crash/empty win).
    # Bug it catches: a single bad config aborting a multi-hour sweep with a cryptic error.
    from sverdrup.application.tuning.objective import NoAdmissibleTrial

    with pytest.raises(NoAdmissibleTrial):
        tune(
            method_name="gmrf",
            space=_gmrf_space(),
            strategy=SobolSearch(seed=1, n=4),
            predicate=CoherenceFeasibility(),
            objective=ConstrainedObjective(),
            scorer=_DegenerateScorer(),
            split=_FakeSplit(),
            seed=1,
            window=_FakeWindow(),
            tile_geometry=TileGeometry(10.0, 100.0, "single"),
            required_capabilities=frozenset({UC.POINT}),
            rounds=1,
        )


def test_unresolved_scale_continues_sweep() -> None:
    # Behavior: degenerate trials are recorded (feasible, scores=None, reason set) and
    # do not stop the loop from finding an admissible trial among the good ones.
    class _MixedScorer:
        def __init__(self) -> None:
            self.n = 0

        def score(
            self,
            method_name: str,
            params: dict[str, float],
            split: object,
            seed: int,
            window: object,
        ) -> dict[str, float]:
            from sverdrup.eval.spectral import UnresolvedScaleError

            self.n += 1
            if self.n == 1:  # first trial degenerate, rest fine
                raise UnresolvedScaleError("no crossing")
            return {"lambda_x": 150.0, "mu_score": 0.86, "coverage_1sigma": 0.68}

    res = tune(
        method_name="gmrf",
        space=_gmrf_space(),
        strategy=SobolSearch(seed=1, n=4),
        predicate=CoherenceFeasibility(),
        objective=ConstrainedObjective(),
        scorer=_MixedScorer(),
        split=_FakeSplit(),
        seed=1,
        window=_FakeWindow(),
        tile_geometry=TileGeometry(10.0, 100.0, "single"),
        required_capabilities=frozenset({UC.POINT}),
        rounds=1,
    )
    assert res.winner is not None
    degenerate = [
        r
        for r in res.history.records
        if r.scores is None
        and r.feasible
        and r.exclusion_reason == "UnresolvedScaleError"
    ]
    assert len(degenerate) == 1


def test_determinism() -> None:
    # TEST 8: same (seed, strategy, predicate, objective) -> identical winner params.
    def _run() -> dict[str, float]:
        res = tune(
            method_name="oi",
            space=_oi_space(),
            strategy=SobolSearch(seed=5, n=8),
            predicate=CoherenceFeasibility(),
            objective=ConstrainedObjective(),
            scorer=_SpyScorer(),
            split=_FakeSplit(),
            seed=5,
            window=_FakeWindow(),
            tile_geometry=TileGeometry(10.0, 100.0, "single"),
            required_capabilities=frozenset({UC.POINT}),
            rounds=1,
        )
        assert res.winner is not None
        return res.winner.trial.params

    assert _run() == _run()
