"""Record-shape + spectral-guard units for the Task-7 runner machinery.

Bugs caught: the per-bar outcome breakdown drifting from the sealed lane
bars (an evidence record claiming admissible while a bar fails); unscorable
trials recorded as admissible; the empty-PSD degenerate case crashing with
a cryptic zero-size ValueError instead of the defined ShortTrackError
signal (the class that killed the V-lane dev smoke inside a resample).
"""

from __future__ import annotations

import numpy as np
import pytest

from sverdrup.eval.spectral import (
    ShortTrackError,
    UnresolvedScaleError,
    _coherence_guard,
)
from tests.helpers import load_script

lane_run = load_script("phase10_lane_run")

_TRIAL = {"c0": 0.0, "c1": 0.0, "c2": 0.0, "log_L0": 0.0, "l1": 0.0, "Lt": 7.0}
_NOW = "2026-07-14T01:00:00+00:00"


def test_record_itemizes_bars_and_admissible_consistent() -> None:
    # Hand values: mu 0.90 >= 0.85 passes; coverage 0.70 in 0.6827±0.10 passes.
    rec = lane_run.make_record(
        lane="V",
        index=3,
        anchor=False,
        scope="screening",
        trial=_TRIAL,
        scores={"mu_score": 0.90, "coverage_1sigma": 0.70},
        created_utc=_NOW,
    )
    assert rec["bars"] == {"mu_score": True, "coverage_1sigma": True}
    assert rec["admissible"] is True
    assert rec["created_utc"] == _NOW and rec["scope"] == "screening"


def test_record_failing_bar_not_admissible() -> None:
    # coverage 0.85 > 0.7827 top edge -> bar fails -> inadmissible, itemized.
    rec = lane_run.make_record(
        lane="V",
        index=0,
        anchor=True,
        scope="full",
        trial=_TRIAL,
        scores={"mu_score": 0.90, "coverage_1sigma": 0.85},
        created_utc=_NOW,
        residuals_npz="x.npz",
    )
    assert rec["bars"]["mu_score"] is True
    assert rec["bars"]["coverage_1sigma"] is False
    assert rec["admissible"] is False
    assert rec["residuals_npz"] == "x.npz"


def test_record_unscorable_never_admissible() -> None:
    rec = lane_run.make_record(
        lane="lane0",
        index=1,
        anchor=False,
        scope="screening",
        trial=_TRIAL,
        scores=None,
        exclusion_reason="UnresolvedScaleError",
        created_utc=_NOW,
    )
    assert rec["admissible"] is False
    assert rec["bars"] == {"mu_score": False, "coverage_1sigma": False}


def test_coherence_guard_empty_raises_defined_signal() -> None:
    with pytest.raises(ShortTrackError, match="empty PSD"):
        _coherence_guard(np.array([]))


def test_coherence_guard_all_nan_raises_defined_signal() -> None:
    with pytest.raises(ShortTrackError):
        _coherence_guard(np.array([np.nan, np.nan]))


def test_coherence_guard_no_crossing_raises_unresolved() -> None:
    with pytest.raises(UnresolvedScaleError):
        _coherence_guard(np.array([0.1, 0.2, 0.3]))  # never reaches 0.5


def test_coherence_guard_crossing_passes() -> None:
    _coherence_guard(np.array([0.2, 0.6]))  # spans 0.5 -> no raise
