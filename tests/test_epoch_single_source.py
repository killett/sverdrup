"""The pipeline's day-0 epoch is ``validation.params.EPOCH`` alone (hygiene #12)."""

from __future__ import annotations

import inspect

import numpy as np
import pytest

from sverdrup.application.calibration import harness
from sverdrup.application.tuning import lane_compare
from sverdrup.validation import params


def test_day_float_counts_from_the_canonical_epoch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``lane_compare._day_float`` reads the canonical epoch at call time.

    Moving the canonical epoch back one day moves every converted day up by
    one. Bug caught: the function keeping its own ``2017-01-01`` literal, so
    a changed epoch (or a sentinel, as here) is silently ignored and lane
    days disagree with the obs loader's.
    """
    monkeypatch.setattr(params, "EPOCH", np.datetime64("2016-12-31"))
    t = np.array(["2017-01-02T00:00:00"], dtype="datetime64[s]")
    assert lane_compare._day_float(t).tolist() == [2.0]


def test_day_float_is_fractional_days_since_epoch() -> None:
    """Noon on 2017-01-02 is day 1.5 (hand value; epoch 2017-01-01)."""
    t = np.array(["2017-01-02T12:00:00"], dtype="datetime64[s]")
    assert lane_compare._day_float(t).tolist() == [1.5]


@pytest.mark.parametrize("module", [harness, lane_compare])
def test_no_module_re_pastes_the_epoch_literal(module: object) -> None:
    """Bug caught: a fourth ``np.datetime64("2017-01-01")`` quietly returning."""
    assert 'np.datetime64("2017-01-01")' not in inspect.getsource(module)  # type: ignore[arg-type]
