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


def test_superobs_cfg_for_sides() -> None:
    """CMEMS side carries the pin-4 coarsen cfg; dc2021a side None.

    Bug caught: the evidence record omitting the applied super-obs
    transform (fork-a pin 4: parameterized AND recorded in provenance).
    """
    from sverdrup.validation.params import COARSEN_TIME

    assert _mod.superobs_cfg_for("cmems_my") == {
        "kind": "challenge-coarsen",
        "n": COARSEN_TIME,
    }
    assert _mod.superobs_cfg_for("dc2021a") is None
    with pytest.raises(ValueError, match="unknown source"):
        _mod.superobs_cfg_for("nope")


def test_record_and_apply_share_the_cfg_source() -> None:
    """The record keys and the apply site both route through superobs_cfg_for.

    Source pin: catches the drift bug where the applied transform and the
    recorded provenance disagree, or the record keys are dropped.
    """
    import inspect

    run_src = inspect.getsource(_mod.run)
    assert '"superobs_cfg_a": superobs_cfg_for(source_a)' in run_src
    assert '"superobs_cfg_b": superobs_cfg_for(source_b)' in run_src
    side_src = inspect.getsource(_mod._load_side)
    assert "superobs_cfg_for(source_id)" in side_src
    assert "apply_superobs(obs, cfg=cfg)" in side_src
