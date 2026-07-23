"""Golden-tile machinery unit tests (phase-14 Task 7, 0c-5) — CI-local."""

from __future__ import annotations

import numpy as np
import pytest
from typer.testing import CliRunner

from tests.helpers import load_script

_mod = load_script("phase14_golden_tile")
runner = CliRunner()


def test_delta_arithmetic_hand_values() -> None:
    """RMS/max/worst-day on a synthetic pair, hand-computed."""
    a = np.zeros((2, 2, 2))
    b = np.zeros((2, 2, 2))
    b[1] = 0.02  # day 1 differs by 2 cm everywhere
    d = _mod.compute_deltas(a, b)
    assert d["max_abs_m"] == pytest.approx(0.02)
    assert d["worst_day_rms_m"] == pytest.approx(0.02)
    assert d["rms_m"] == pytest.approx(0.02 / np.sqrt(2))  # half the days differ


def test_tabled_flag_thresholds() -> None:
    """The pre-registered thresholds flag OVER, never under (records both)."""
    small = {"rms_m": 0.001, "max_abs_m": 0.01, "worst_day_rms_m": 0.002}
    assert _mod.tabled_flag(small, mu_delta=0.001) is False
    assert _mod.tabled_flag(small, mu_delta=0.0021) is True  # mu leg
    big = dict(small, rms_m=0.011)
    assert _mod.tabled_flag(big, mu_delta=0.0) is True  # map leg


def test_refuses_identical_source_ids() -> None:
    """a == b is a no-op comparison: refuse loudly."""
    res = runner.invoke(_mod.app, ["--source-a", "dc2021a", "--source-b", "dc2021a"])
    assert res.exit_code != 0
    assert "differ" in res.output


def test_refuses_unregistered_frame_or_period() -> None:
    """Only the pre-registered signed-box x 2017 comparison exists."""
    res = runner.invoke(
        _mod.app,
        ["--source-a", "dc2021a", "--source-b", "cmems_my", "--period", "2016"],
    )
    assert res.exit_code != 0
    assert "pre-registered" in res.output
