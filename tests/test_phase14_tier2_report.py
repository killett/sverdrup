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

    ``_mt()`` rows are PAIRWISE deltas among the multi-thread runs, so
    threading(mean) = max(1e-7, 3e-7, 2e-7) = 3e-7 > gate 2e-7 -> envelope
    3e-7; threading(member0) = max(9e-7, 2e-7, 5e-7) = 9e-7 > gate 4e-7 ->
    envelope 9e-7. A blended single number fails these pins.
    """
    r = _mod.assemble_tier2_report(True, _cross(), _mt(), 8.5, 3600.0, 0.4)
    assert r["crn_cross_host"] == "EQUAL"
    assert r["stop_for_owner"] is False
    assert r["tolerance_gate"]["mean"]["max_abs"] == 2e-7
    assert r["tolerance_threading"]["mean"] == pytest.approx(3e-7)
    assert r["tolerance_threading"]["member0_anom"] == pytest.approx(9e-7)
    assert r["spotcheck_envelope"]["mean"] == pytest.approx(3e-7)
    assert r["spotcheck_envelope"]["member0_anom"] == pytest.approx(9e-7)
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


def test_threading_tolerance_is_the_max_PAIRWISE_difference_between_runs(
    tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bug caught (hygiene, phase14_probe.py:229): tolerance_threading was
    the spread of each run's max-abs deviation FROM THE LOCAL SOLVE — two
    multi-thread runs deviating by +1e-7 and -1e-7 at the same node have
    equal max-abs (spread 0) while they differ from EACH OTHER by 2e-7, the
    number the docstring promises. Expected values by hand from the
    fixture fields; the evidence path is a temp file."""
    import json
    from pathlib import Path

    import numpy as np

    d = Path(str(tmp_path))
    zeros = np.zeros(3)

    def _npz(name: str, mean: list[float]) -> Path:
        p = d / f"{name}.npz"
        np.savez(p, mean=np.asarray(mean), member0_anom=zeros)
        return p

    local = _npz("local", [0.0, 0.0, 0.0])
    cloud = _npz("cloud", [0.0, 0.0, 0.0])
    mt = [_npz("mt1", [1e-7, 0.0, 0.0]), _npz("mt2", [-1e-7, 0.0, 0.0])]
    crn = d / "crn.json"
    crn.write_text(json.dumps({"axes": ["a"], "root": 1}))
    evidence = d / "evidence.json"
    evidence.write_text("{}")
    monkeypatch.setattr(_mod, "EVIDENCE", evidence)
    _mod.tier2_report(
        crn_a=crn,
        crn_b=crn,
        solve_local=local,
        solve_cloud=cloud,
        mt_runs=",".join(str(p) for p in mt),
        cost_usd=1.0,
        wall_s=1.0,
        egress_gib=0.0,
    )
    report = json.loads(evidence.read_text())["phase14"]["stage0"]["determinism"]
    assert report["tolerance_threading"]["mean"] == pytest.approx(2e-7)
    assert report["tolerance_threading"]["member0_anom"] == 0.0
