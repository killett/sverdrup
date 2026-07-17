"""Budget-arithmetic tests for ``scripts/phase10_probe.py``.

Bug caught: budget arithmetic drifting from the recorded formula
(spec §4: trials_per_lane = floor(wall_budget_h*3600 / (t_trial_s * n_lanes))).
Pure-function tests only — the probe execution path is script-run, never
imported here beyond module load (no data touched at import).
"""

from __future__ import annotations

import pytest

from tests.helpers import load_script

# Load the probe as a module directly from scripts/ (repo convention: scripts/
# is not a package; mirrors tests/test_phase8_gate_run.py).
probe = load_script("phase10_probe")


def test_trials_per_lane_floor_exact() -> None:
    # 6 h budget, 20-min trial, 3 lanes -> floor(21600 / (1200*3)) = 6 (hand).
    # Bug caught: h->s conversion drift (3600 factor lost -> 0).
    assert probe.trials_per_lane(t_trial_s=1200.0, wall_budget_h=6.0, n_lanes=3) == 6


def test_trials_per_lane_floor_fractional() -> None:
    # floor(21600 / (1300*3)) = floor(5.538...) = 5 (hand).
    # Bug caught: round/ceil instead of floor would over-book the wall budget (6).
    assert probe.trials_per_lane(t_trial_s=1300.0, wall_budget_h=6.0, n_lanes=3) == 5


def test_trials_per_lane_never_negative() -> None:
    # A trial costlier than the whole budget -> 0 trials, not negative/raise.
    assert probe.trials_per_lane(t_trial_s=1e9, wall_budget_h=1.0, n_lanes=3) == 0


def test_trials_per_lane_rejects_nonpositive_trial_cost() -> None:
    # Bug caught: silent ZeroDivisionError / inf trials on a bad measurement.
    with pytest.raises(ValueError, match="t_trial_s"):
        probe.trials_per_lane(t_trial_s=0.0, wall_budget_h=6.0, n_lanes=3)
