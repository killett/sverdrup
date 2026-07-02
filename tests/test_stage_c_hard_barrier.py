"""Stage C: the joint coherence barrier binds; multi-tile joint trials are never solved."""

from __future__ import annotations

from sverdrup.application.tuning.feasibility import CoherenceFeasibility
from sverdrup.application.tuning.objective import ConstrainedObjective
from sverdrup.application.tuning.stage_c import run_stage_c_loop, tile_geometry_for
from sverdrup.application.tuning.strategy import RandomSearch


class _SpyScorer:
    def __init__(self) -> None:
        self.calls = 0

    def score(self, method_name, params, split, seed, window):
        self.calls += 1
        return {"lambda_x": 120.0, "mu_score": 0.86, "coverage_1sigma": 0.68}


def test_multi_tile_joint_trials_never_scored() -> None:
    # TEST 4 (global): n_tiles>=2 with SAMPLES -> excluded before any solve (empty region).
    scorer = _SpyScorer()
    result = run_stage_c_loop(
        n_tiles=9,
        strategy=RandomSearch(seed=1, n=24),
        predicate=CoherenceFeasibility(),
        objective=ConstrainedObjective(),
        scorer=scorer,
        seed=1,
        on_empty="return_history",
    )
    assert scorer.calls == 0  # decisive: no solve for any infeasible trial
    excluded = [rec for rec in result.history.records if not rec.feasible]
    assert excluded and all(rec.scores is None for rec in excluded)


def test_single_tile_is_scored() -> None:
    # n_tiles=1 -> joint-valid -> the scorer runs.
    scorer = _SpyScorer()
    run_stage_c_loop(
        n_tiles=1,
        strategy=RandomSearch(seed=1, n=4),
        predicate=CoherenceFeasibility(),
        objective=ConstrainedObjective(),
        scorer=scorer,
        seed=1,
        on_empty="return_history",
    )
    assert scorer.calls > 0


def test_tile_geometry_carries_n_tiles() -> None:
    geom = tile_geometry_for(n_tiles=9, params={"range": 80.0})
    assert geom.n_tiles == 9 and geom.range_km == 80.0
