"""Pluggable blocked withholding: two exemplars, buffer-discard, no random holdout."""

from __future__ import annotations

import numpy as np
import pytest

from sverdrup.application.splits import make_splits
from sverdrup.application.withholding import (
    Assignment,
    LeaveOneMissionOut,
    PerMissionTemporalFraction,
)
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow


def _obs(n=100):
    rng = np.random.default_rng(0)
    mission = np.where(np.arange(n) % 2 == 0, "alg", "c2")
    t = np.tile(np.linspace(0, 20, n // 2), 2)
    return ObsWindow.from_arrays(
        rng.uniform(-5, 5, n),
        rng.uniform(-5, 5, n),
        t,
        rng.standard_normal(n),
        DiagonalErrorModel(np.full(n, 0.01)),
        mission=mission,
    )


def test_leave_one_mission_out_withholds_whole_mission():
    # Behavior: an entire mission goes to validation; none of it trains.
    # Bug caught: leaking a withheld mission's points into train.
    obs = _obs()
    a = LeaveOneMissionOut(validation_missions=["c2"]).split(obs)
    val = a.assignment == Assignment.VALIDATION
    assert set(obs.mission[val]) == {"c2"}
    assert "c2" not in set(obs.mission[a.assignment == Assignment.TRAIN])


def test_per_mission_temporal_fraction_has_disjoint_buffer():
    # Behavior: per mission, first 75% train, next 5% buffer-discard, last 20% validation;
    #   buffer severs train/validation autocorrelation and is disjoint from both.
    # Bug caught: train and validation adjacent in time -> autocorrelation leak.
    obs = _obs()
    a = PerMissionTemporalFraction(train=0.75, buffer=0.05, validation=0.20).split(obs)
    tr = set(np.where(a.assignment == Assignment.TRAIN)[0])
    bf = set(np.where(a.assignment == Assignment.BUFFER_DISCARD)[0])
    vl = set(np.where(a.assignment == Assignment.VALIDATION)[0])
    assert bf and not (bf & tr) and not (bf & vl)
    assert len(bf) > 0


def test_random_point_holdout_still_rejected():
    # Behavior: random point holdout is forbidden by construction (invariant 12).
    # Bug caught: silently allowing an autocorrelation-leaking split.
    with pytest.raises(ValueError, match="[Rr]andom point holdout"):
        make_splits(_obs(), by="random_point")


def test_split_carries_buffer_discard_idx_default_empty():
    # Behavior: Split gains buffer_discard_idx, defaulting empty for Phase-1 back-compat.
    # Bug caught: a required field would break every existing make_splits caller.
    split = make_splits(_obs(), by="mission", locked_missions=["c2"])
    assert split.buffer_discard_idx.shape == (0,)
