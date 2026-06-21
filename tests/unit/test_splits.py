import numpy as np
import pytest

from regatta.application.splits import make_splits
from regatta.core.observations import DiagonalErrorModel, ObsWindow


def _obs(n=30):
    rng = np.random.default_rng(0)
    mission = np.array(["s6", "c2", "j3"])[rng.integers(0, 3, n)]
    return ObsWindow.from_arrays(
        rng.uniform(0, 10, n),
        rng.uniform(40, 50, n),
        rng.uniform(0, 40, n),
        rng.normal(size=n),
        DiagonalErrorModel(np.full(n, 0.01)),
        mission=mission,
    )


def test_mission_holdout_is_grouped():
    # Bug caught: random point holdout leaking through spatial autocorrelation.
    obs = _obs()
    split = make_splits(
        obs, by="mission", locked_missions=["j3"], validation_missions=["c2"]
    )
    assert set(obs.mission[split.train_idx]) == {"s6"}
    assert set(obs.mission[split.locked_test_idx]) == {"j3"}


def test_partition_is_disjoint_and_total():
    obs = _obs()
    s = make_splits(
        obs, by="mission", locked_missions=["j3"], validation_missions=["c2"]
    )
    all_idx = np.concatenate([s.train_idx, s.validation_idx, s.locked_test_idx])
    assert np.array_equal(np.sort(all_idx), np.arange(len(obs)))


def test_random_point_holdout_rejected():
    with pytest.raises(ValueError):
        make_splits(_obs(), by="random_point")
