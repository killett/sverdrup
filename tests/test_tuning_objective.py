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


def test_rank_order_identical_to_legacy_sorted_expression() -> None:
    # GATE (iii) — Phase-11 Policy-seam migration identity property.
    # Written against the PRE-migration implementation (green baseline) and
    # KEPT: rank() must stay identical, object-per-position, to the frozen
    # legacy expression `sorted(ok, key=lambda r: r.scores[primary])`, ties
    # included (stability). Bug it catches: any ordering drift through the
    # seam (comparator sign, stability loss, filter change).
    import numpy as np

    obj = ConstrainedObjective()
    rng = np.random.default_rng(31415)
    raised = 0
    for _trial in range(200):
        n = int(rng.integers(1, 40))
        recs = []
        for _i in range(n):
            lx = float(rng.integers(100, 111))  # coarse grid -> plenty of ties
            mu = float(rng.choice([0.80, 0.86, 0.90]))
            cov = float(rng.choice([0.40, 0.68]))
            recs.append(
                TrialRecord(
                    Trial("oi", {"length_scale": lx}, "s", 1, "w"),
                    scores={
                        "lambda_x": lx,
                        "mu_score": mu,
                        "coverage_1sigma": cov,
                    },
                    feasible=bool(rng.random() > 0.1),
                )
            )
        ok = [
            r
            for r in recs
            if r.feasible and r.scores is not None and obj.admissible(r.scores)
        ]
        if not ok:
            with pytest.raises(NoAdmissibleTrial):
                obj.rank(recs)
            raised += 1
            continue
        expected = sorted(ok, key=lambda r: r.scores["lambda_x"])  # type: ignore[index]
        got = obj.rank(recs)
        assert len(got) == len(expected)
        for g, e in zip(got, expected, strict=True):
            assert g is e  # object identity per position, ties included
    assert raised < 60  # the sweep genuinely exercises the sorted path
