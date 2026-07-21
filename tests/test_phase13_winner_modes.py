"""Tests for the phase-13 winner-run modes (plan Task 11 wiring).

Guard-level tests (the heavy solve paths are exercised by the runs
themselves); each names the bug it catches.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.helpers import load_script

runner = load_script("phase13_lane_run")


def _evidence(tmp_path: Path, payload: dict[str, Any]) -> Path:
    p = tmp_path / "results.json"
    p.write_text(json.dumps(payload))
    return p


_D_TRIAL = {
    "delta_alg": 0.1,
    "delta_h2g": 0.0,
    "delta_j2g": 0.0,
    "delta_j2n": 0.0,
    "log10_rho": 1.3,
    "log_lam_bias": None,
    "log_lam_tilt": None,
}


def test_winner_ctap_refuses_modes_absent_lane(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The §8 c-block diagnostics exist only where Λ does: a tap run at a
    # modes-absent winner (lane D) must refuse, not write empty taps.
    # Bug caught: a phantom (empty) tap artifact for lane D entering the
    # §8 tables as "no saturation, no autocorrelation — all clean".
    ev = {
        "phase13": {
            "miost": {"lanes": {"D": {"winner": {"lane": "D", "trial": _D_TRIAL}}}}
        }
    }
    monkeypatch.setattr(runner, "_RESULTS", _evidence(tmp_path, ev))
    with pytest.raises(SystemExit, match="modes"):
        runner.main_winner_ctap("D")


def test_winner_ctap_refuses_missing_winner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Bug caught: a tap run against nothing silently solving at defaults.
    ev: dict[str, Any] = {"phase13": {"miost": {"lanes": {}}}}
    monkeypatch.setattr(runner, "_RESULTS", _evidence(tmp_path, ev))
    with pytest.raises(SystemExit, match="winner"):
        runner.main_winner_ctap("C")


def test_winner_ensemble_refuses_without_winner_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The m=100 acceptance ensemble executes ONLY on branch=winner (plan
    # branch semantics): a missing or negative verdict refuses.
    # Bug caught: acceptance substrate built on a negative read (spending
    # ~6 h and creating shippable-looking artifacts the branch forbids).
    ev = {
        "phase13": {
            "miost": {
                "lanes": {
                    "verdict": {
                        "branch_recorded": "NEGATIVE: Task 10 close executes",
                        "winner_lane_rule": {"chain_lane": None},
                    }
                }
            }
        }
    }
    monkeypatch.setattr(runner, "_RESULTS", _evidence(tmp_path, ev))
    with pytest.raises(SystemExit, match="branch"):
        runner.main_winner_ensemble()


def test_ensemble_root_is_the_recorded_exact_int_convention() -> None:
    # §11: the phase-13 winner ensemble root derives from the unit of
    # work ("miost", "phase13-winner", "members", 0) — recorded as an
    # exact int (jq float-rounds; the string form rides beside).
    # Bug caught: silently reusing the miost5/miost6 stage-b-winner root
    # (CRN streams would collide with the signed products') or a
    # non-deterministic root.
    from sverdrup.core.seeding import derive_seed

    expected = derive_seed("miost", "phase13-winner", "members", 0)
    assert runner._ensemble_root() == expected
    assert isinstance(runner._ensemble_root(), int)
    assert runner._ensemble_root() != derive_seed(
        "miost", "stage-b-winner", "members", 0
    )
