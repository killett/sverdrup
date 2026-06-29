"""Trial/TrialRecord/TrialHistory: excluded trials carry scores=None (no-solve proof)."""

from __future__ import annotations

from sverdrup.application.tuning.trial import Trial, TrialHistory, TrialRecord


def _trial(i: int) -> Trial:
    return Trial("oi", {"length_scale": float(i)}, "split0", 7, "tile0")


def test_excluded_record_has_none_scores() -> None:
    rec = TrialRecord(_trial(1), scores=None, feasible=False)
    assert rec.scores is None and rec.feasible is False


def test_feasible_scored_filters() -> None:
    h = TrialHistory(seed=7, records=[])
    h.records.append(TrialRecord(_trial(1), scores=None, feasible=False))
    h.records.append(TrialRecord(_trial(2), scores={"lambda_x": 150.0}, feasible=True))
    fs = h.feasible_scored()
    assert len(fs) == 1
    assert fs[0].scores is not None
    assert fs[0].scores["lambda_x"] == 150.0


def test_trial_is_frozen() -> None:
    import dataclasses

    import pytest

    t = _trial(1)
    with pytest.raises(dataclasses.FrozenInstanceError):
        t.seed = 9  # type: ignore[misc]
