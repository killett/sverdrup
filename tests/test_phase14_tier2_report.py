"""Tier-2 report assembly tests (phase-14 Task 18, 0b-3) — fixture inputs."""

from __future__ import annotations

import pytest

from tests.helpers import load_script

_mod = load_script("phase14_probe")


def _cross() -> dict[str, dict[str, float]]:
    return {
        "mean": {"max_abs": 2e-7, "rms": 5e-8},
        "member0_anom": {"max_abs": 4e-7, "rms": 1e-7},
    }


def _mt() -> list[dict[str, dict[str, float]]]:
    return [
        {
            "mean": {"max_abs": 1e-7, "rms": 2e-8},
            "member0_anom": {"max_abs": 9e-7, "rms": 3e-7},
        },
        {
            "mean": {"max_abs": 3e-7, "rms": 6e-8},
            "member0_anom": {"max_abs": 2e-7, "rms": 8e-8},
        },
        {
            "mean": {"max_abs": 2e-7, "rms": 4e-8},
            "member0_anom": {"max_abs": 5e-7, "rms": 2e-7},
        },
    ]


def test_two_tolerances_separate_and_envelope() -> None:
    """tolerance_gate and tolerance_threading land SEPARATE (fork-g pin 2);
    the spot-check envelope = per-key max — hand-computed.

    threading spread(mean) = 3e-7 - 1e-7 = 2e-7; gate(mean) = 2e-7 ->
    envelope 2e-7. spread(member0) = 9e-7 - 2e-7 = 7e-7 > gate 4e-7 ->
    envelope 7e-7. A blended single number fails these pins.
    """
    r = _mod.assemble_tier2_report(True, _cross(), _mt(), 8.5, 3600.0, 0.4)
    assert r["crn_cross_host"] == "EQUAL"
    assert r["stop_for_owner"] is False
    assert r["tolerance_gate"]["mean"]["max_abs"] == 2e-7
    assert r["tolerance_threading"]["mean"] == pytest.approx(2e-7)
    assert r["tolerance_threading"]["member0_anom"] == pytest.approx(7e-7)
    assert r["spotcheck_envelope"]["mean"] == pytest.approx(2e-7)
    assert r["spotcheck_envelope"]["member0_anom"] == pytest.approx(7e-7)
    assert "max(" in r["envelope_formula"]
    assert r["cost_basis"] == {
        "cost_usd": 8.5,
        "wall_s": 3600.0,
        "egress_gib": 0.4,
    }


def test_crn_mismatch_is_a_stop() -> None:
    """A CRN cross-host mismatch marks STOP for the owner — it breaks the
    identity assumption; never a tolerance question."""
    r = _mod.assemble_tier2_report(False, _cross(), _mt(), 1.0, 10.0, 0.0)
    assert r["crn_cross_host"] == "STOP-MISMATCH"
    assert r["stop_for_owner"] is True
