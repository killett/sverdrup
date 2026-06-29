"""ConstrainedObjective: hard bars (incl. calibration), λx primary, loud on empty."""

from __future__ import annotations

import pytest

from sverdrup.application.tuning.objective import (
    BASELINE_BAR_MU,
    ConstrainedObjective,
    NoAdmissibleTrial,
)
from sverdrup.application.tuning.trial import Trial, TrialRecord


def _rec(lx: float, mu: float, cov: float) -> TrialRecord:
    return TrialRecord(
        Trial("oi", {"length_scale": lx}, "s", 1, "w"),
        scores={"lambda_x": lx, "mu_score": mu, "coverage_1sigma": cov},
        feasible=True,
    )


def test_ranks_by_lambda_x_among_admissible() -> None:
    obj = ConstrainedObjective()
    recs = [_rec(150.0, 0.86, 0.68), _rec(140.0, 0.87, 0.69)]
    ranked = obj.rank(recs)
    assert ranked[0].scores is not None
    assert ranked[0].scores["lambda_x"] == 140.0  # finer resolution wins


def test_baseline_floor_is_hard() -> None:
    # Bug it catches: admitting a below-baseline trial because its λx is great.
    obj = ConstrainedObjective()
    with pytest.raises(NoAdmissibleTrial):
        obj.rank([_rec(120.0, 0.80, 0.68)])  # mu 0.80 < 0.85 floor
    assert BASELINE_BAR_MU == 0.85


def test_calibration_is_hard_never_traded() -> None:
    # A miscalibrated trial with the finest λx is still dropped.
    obj = ConstrainedObjective()
    with pytest.raises(NoAdmissibleTrial):
        obj.rank([_rec(100.0, 0.90, 0.40)])  # coverage 0.40 far from 0.683


def test_empty_admissible_raises_loud() -> None:
    obj = ConstrainedObjective()
    with pytest.raises(NoAdmissibleTrial, match="loosen the bar or widen the search"):
        obj.rank([])
