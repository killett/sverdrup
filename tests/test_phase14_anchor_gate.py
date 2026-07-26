"""Anchor identity gate unit tests (phase-14 Stage-1 Task 3) — CI-local.

Covers the CI-testable machinery ONLY: five-check block assembly
(fail-any-fail), the locked-tally guard, check-3 exact-equality semantics,
pin-23 capped-leg detection, the gate-5 write-once pin, and the check-2/4
citation builders. The heavy anchor solve legs are data-gated skips with
named reasons.

Every test names the concrete bug it would catch (test-design discipline);
expected values come from the plan/spec wording, never from executing the
implementation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from sverdrup.distributions.calibration import ClipSpec, PolyCalibration
from tests.helpers import load_script

_mod = load_script("phase14_anchor_gate")

# The five §10 check keys, restated from the plan (NOT read off the module —
# a drift between plan and module must fail here, not be mirrored).
_FIVE = (
    "tiling_identity",
    "loader_identity",
    "era_noop",
    "cross_env",
    "score_identity",
)

_SIGNED_FIELD: dict[str, Any] = {
    "calibration": {
        "kind": "poly",
        "coeffs": [2.0, 0.5, -2.25, -0.13, 0.56],
        "clip": {"lo_log_s": 0.62, "hi_log_s": 2.4},
        "fit_id": "L-BFGS-B;gtol=1e-08",
    },
}


def _cal(**over: Any) -> PolyCalibration:
    """A fake calibration surface mirroring the signed-field fixture."""
    c = dict(_SIGNED_FIELD["calibration"])
    c.update(over)
    return PolyCalibration(
        coeffs=tuple(c["coeffs"]),
        clip=ClipSpec(
            lo_log_s=float(c["clip"]["lo_log_s"]),
            hi_log_s=float(c["clip"]["hi_log_s"]),
        ),
        fit_id=str(c["fit_id"]),
    )


def _signed_field_for(cal: PolyCalibration) -> dict[str, Any]:
    """The signed-artifact dict whose cal_key matches ``cal``."""
    return {"calibration": cal.to_json(), "cal_key": cal.key()}


def _passing_checks() -> dict[str, dict[str, Any]]:
    """Five green sub-blocks (statuses per the plan: 1/3/5 run, 2/4 cite)."""
    return {
        "tiling_identity": {"status": "pass", "pass": True},
        "loader_identity": {"status": "cited", "pass": True},
        "era_noop": {"status": "pass", "pass": True},
        "cross_env": {"status": "cited", "pass": True},
        "score_identity": {"status": "pass", "pass": True},
    }


def _block(checks: dict[str, dict[str, Any]], **kw: Any) -> dict[str, Any]:
    """Assemble a gate block with quiet defaults for the non-check inputs."""
    defaults: dict[str, Any] = {
        "pcg_rows": [],
        "pcg_rtol": 1e-6,
        "pcg_maxiter": 500,
        "tally_guard": {"byte_identical": True},
        "artifacts": {},
        "meta": {"seal_sha": "s", "date": "2026-07-25"},
    }
    defaults.update(kw)
    return _mod.build_gate_block(checks=checks, **defaults)


# ---------------------------------------------------------------------------
# Gate-block assembly: five keys, fail-any-fail
# ---------------------------------------------------------------------------


def test_gate_block_requires_all_five_checks() -> None:
    # Bug caught: a refactor drops one §10 check (e.g. cross_env) and the
    # gate assembles four sub-blocks and reports GREEN anyway.
    checks = _passing_checks()
    del checks["cross_env"]
    with pytest.raises(ValueError, match="cross_env"):
        _block(checks)


def test_gate_block_rejects_unknown_check_key() -> None:
    # Bug caught: a typoed check key ("cross_envv") rides in beside a
    # MISSING real one and the count-based validation waves it through.
    checks = _passing_checks()
    checks["cross_envv"] = checks.pop("cross_env")
    with pytest.raises(ValueError, match="cross_envv"):
        _block(checks)


def test_gate_block_fail_any_fail() -> None:
    # Bug caught: any()-style aggregation (or a cited status counted as an
    # unconditional pass) lets one RED check ride into a GREEN gate.
    for key in _FIVE:
        checks = _passing_checks()
        checks[key] = {"status": "fail", "pass": False}
        block = _block(checks)
        assert block["pass"] is False, f"failing {key} must fail the gate"
        assert _mod.gate_exit_code(block) != 0


def test_gate_block_all_green() -> None:
    # Bug caught: cited statuses (checks 2/4) wrongly treated as failures —
    # the gate could NEVER go green and downstream would stall forever.
    block = _block(_passing_checks())
    assert block["pass"] is True
    assert _mod.gate_exit_code(block) == 0
    assert set(block["checks"]) == set(_FIVE)
    assert block["label"] == "ANCHOR-IDENTITY-GATE"


def test_gate_block_rejects_inconsistent_status() -> None:
    # Bug caught: a sub-block claims status "fail" while pass=True (or an
    # unknown status) and the aggregate reads only one of the two fields.
    checks = _passing_checks()
    checks["era_noop"] = {"status": "fail", "pass": True}
    with pytest.raises(ValueError, match="era_noop"):
        _block(checks)


# ---------------------------------------------------------------------------
# Locked-tally guard
# ---------------------------------------------------------------------------


def _tally_store(tmp_path: Path) -> Path:
    p = tmp_path / "ev.json"
    p.write_text(
        json.dumps(
            {
                "c2_touch_tally": {"miost5": 3, "miost6": 1},
                "phase14": {"locked_n": {"prod": {"era": 1}}, "stage1": {}},
            }
        )
    )
    return p


def test_tally_guard_detects_locked_n_mutation(tmp_path: Path) -> None:
    # Bug caught: the guard snapshots the wrong subtree and a locked-tier
    # n increment during the gate run slips through the zero-touch assert.
    p = _tally_store(tmp_path)
    before = _mod.snapshot_locked_tally(p)
    d = json.loads(p.read_text())
    d["phase14"]["locked_n"]["prod"]["era"] = 2
    p.write_text(json.dumps(d))
    with pytest.raises(RuntimeError, match="tally"):
        _mod.assert_tally_unchanged(before, p)


def test_tally_guard_detects_c2_tally_mutation(tmp_path: Path) -> None:
    # Bug caught: the guard covers only the phase-14 ledger and misses the
    # legacy top-level c2_touch_tally.
    p = _tally_store(tmp_path)
    before = _mod.snapshot_locked_tally(p)
    d = json.loads(p.read_text())
    d["c2_touch_tally"]["miost5"] = 4
    p.write_text(json.dumps(d))
    with pytest.raises(RuntimeError, match="tally"):
        _mod.assert_tally_unchanged(before, p)


def test_tally_guard_ignores_unrelated_evidence_writes(tmp_path: Path) -> None:
    # Bug caught: the guard hashes the whole file, so the gate's OWN
    # legitimate evidence write trips it and the gate can never record.
    p = _tally_store(tmp_path)
    before = _mod.snapshot_locked_tally(p)
    d = json.loads(p.read_text())
    d["phase14"]["stage1"]["anchor_gate"] = {"pass": True}
    p.write_text(json.dumps(d))
    _mod.assert_tally_unchanged(before, p)  # must NOT raise


# ---------------------------------------------------------------------------
# Check 3: era-machinery no-op — EXACT equality, never a tolerance
# ---------------------------------------------------------------------------

_LON = np.linspace(295.0, 305.0, 5)
_LAT = np.linspace(33.0, 43.0, 5)


def test_check3_exact_identity_passes() -> None:
    # Bug caught: the check compares against the wrong artifact node (or
    # never evaluates the surface) so the true identity reads as a fail.
    cal = _cal()
    block = _mod.check3_era_noop(cal, _signed_field_for(cal), _LON, _LAT)
    assert block["pass"] is True
    assert block["status"] == "pass"
    assert block["cal_key_equal"] is True
    assert block["surface_exact_equal"] is True
    assert block["n_points"] == _LON.size * _LAT.size


def test_check3_rejects_last_ulp_coeff_perturbation() -> None:
    # Bug caught: someone softens the == to allclose; a 1e-13 coefficient
    # drift would pass any reasonable tolerance but violates the spec's
    # "EXACTLY, BY CONSTRUCTION — an identity, not a tolerance".
    cal = _cal()
    coeffs = list(_SIGNED_FIELD["calibration"]["coeffs"])
    coeffs[0] += 1e-13
    drifted = _cal(coeffs=coeffs)
    block = _mod.check3_era_noop(drifted, _signed_field_for(cal), _LON, _LAT)
    assert block["pass"] is False
    assert block["status"] == "fail"


def test_check3_rejects_descriptor_mismatch_with_equal_values() -> None:
    # Bug caught: the check compares surface VALUES only — a fit_id
    # (provenance) drift with numerically identical values would pass and
    # the gate would cite the wrong fit lineage as the signed s(x).
    cal = _cal()
    relabeled = _cal(fit_id="L-BFGS-B;gtol=1e-07")
    block = _mod.check3_era_noop(relabeled, _signed_field_for(cal), _LON, _LAT)
    assert block["pass"] is False
    assert block["cal_key_equal"] is False
    # values ARE equal — only the descriptor differs (isolates the bug)
    assert block["surface_exact_equal"] is True


# ---------------------------------------------------------------------------
# Pin 23: capped-leg detection on pcg rows
# ---------------------------------------------------------------------------


def test_pin23_capped_leg_detection() -> None:
    # Bug caught: flagging on iterations alone (a converged-at-cap leg
    # STOPS the stage spuriously) or on residual alone / not at all (a
    # genuinely capped leg sails through the owner STOP).
    rows = [
        {"window": "w-00018.0+60", "iterations": 500, "final_rel_residual": 2e-6},
        {"window": "w+00027.0+60", "iterations": 500, "final_rel_residual": 9e-7},
        {"window": "w+00072.0+60", "iterations": 137, "final_rel_residual": 9e-7},
    ]
    capped = _mod.capped_pcg_legs(rows, rtol=1e-6, maxiter=500)
    assert [r["window"] for r in capped] == ["w-00018.0+60"]


def test_pin23_trips_gate_and_is_recorded_in_block() -> None:
    # Bug caught: a capped leg stops the script BEFORE the block records
    # it (silent stop) or exits 0 — pin 23 demands record-then-nonzero,
    # an IMMEDIATE owner STOP distinct from a plain check failure.
    rows = [
        {"window": "w-00018.0+60", "iterations": 500, "final_rel_residual": 5e-4},
    ]
    block = _block(_passing_checks(), pcg_rows=rows)
    assert block["pin23"]["tripped"] is True
    assert block["pin23"]["capped_legs"] == rows
    assert block["pass"] is False
    assert _mod.gate_exit_code(block) == _mod.EXIT_PIN23


def test_pin23_exit_code_distinct_from_plain_failure() -> None:
    # Bug caught: pin-23 STOP collapsed into the generic failure exit —
    # the owner cannot tell the separate IMMEDIATE-STOP condition apart.
    failing = _passing_checks()
    failing["tiling_identity"] = {"status": "fail", "pass": False}
    plain = _block(failing)
    assert _mod.gate_exit_code(plain) not in (0, _mod.EXIT_PIN23)


# ---------------------------------------------------------------------------
# Gate-5 constants: write-once
# ---------------------------------------------------------------------------


def test_gate5_write_once_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Bug caught: a re-run silently overwrites the pinned gate-5 (µ, σ, λx)
    # constants — the whole point of PIN NOW is that they never move.
    from sverdrup.validation import phase14_seal

    monkeypatch.setattr(phase14_seal, "verify_current_seal", lambda: None)
    p = tmp_path / "ev.json"
    p.write_text(json.dumps({"phase14": {"stage1": {}}}))
    constants = {"mu": 0.1, "sigma": 0.2, "lambda_x": 150.0}
    _mod.record_gate5(constants, evidence_path=p)
    recorded = json.loads(p.read_text())["phase14"]["stage1"]["gate5"]
    assert recorded["mu"] == 0.1
    with pytest.raises(RuntimeError, match="write-once"):
        _mod.record_gate5({"mu": 0.9}, evidence_path=p)
    # the first pin survives the refused second write
    after = json.loads(p.read_text())["phase14"]["stage1"]["gate5"]
    assert after["mu"] == 0.1


# ---------------------------------------------------------------------------
# Check 2 / check 4 citation builders
# ---------------------------------------------------------------------------


def test_check2_requires_recorded_pass() -> None:
    # Bug caught: the citation cites the Stage-0 node without READING its
    # verdict — a failed loader-identity gate would be cited as green.
    gate2 = {"pass": False, "manifest_sha": "x", "date": "2026-07-22"}
    golden = {"dc2021a_vs_cmems_my": {"tabled_for_owner": True}}
    with pytest.raises(RuntimeError, match="gate2_loader_identity"):
        _mod.build_check2(gate2, golden)


def test_check2_requires_tabled_golden_row() -> None:
    # Bug caught: the lineage-sensitivity half (golden tile TABLED row) is
    # silently dropped from the citation and check 2 cites only half its
    # evidence.
    gate2 = {"pass": True, "manifest_sha": "x", "date": "2026-07-22"}
    golden = {"dc2021a_vs_cmems_my": {"tabled_for_owner": False}}
    with pytest.raises(RuntimeError, match="golden"):
        _mod.build_check2(gate2, golden)


def test_check2_cites_both_nodes() -> None:
    gate2 = {"pass": True, "manifest_sha": "abc", "date": "2026-07-22"}
    golden = {"dc2021a_vs_cmems_my": {"tabled_for_owner": True, "mu_delta": -0.01}}
    block = _mod.build_check2(gate2, golden)
    assert block["status"] == "cited"
    assert block["pass"] is True
    assert block["citations"]["gate2_loader_identity"]["manifest_sha"] == "abc"
    assert block["citations"]["golden_tile"]["tabled_for_owner"] is True


def test_check4_pending_slot_is_explicit_never_silent() -> None:
    # Bug caught: the cross-host slot is omitted (or defaulted to a bare
    # pass) — the Gate-0 ruling requires GREEN WITH THE SLOT EXPLICITLY
    # pending, never silently.
    manifests = [{"path": "a.json", "sha256": "aa"}, {"path": "b.json", "sha256": "bb"}]
    block = _mod.build_check4(
        crn_manifests=manifests, crn_equal=True, cross_host="pending-T18"
    )
    assert block["status"] == "cited"
    assert block["pass"] is True
    assert block["cross_host"] == "pending-T18"
    with pytest.raises(ValueError, match="cross_host"):
        _mod.build_check4(crn_manifests=manifests, crn_equal=True, cross_host="")


def test_check4_crn_mismatch_fails() -> None:
    # Bug caught: the builder cites the T17 EQUAL verdict without carrying
    # the recomputed equality — divergent manifests would still cite green.
    manifests = [{"path": "a.json", "sha256": "aa"}, {"path": "b.json", "sha256": "bb"}]
    block = _mod.build_check4(
        crn_manifests=manifests, crn_equal=False, cross_host="pending-T18"
    )
    assert block["pass"] is False
    assert block["status"] == "fail"


# ---------------------------------------------------------------------------
# Heavy legs — data-gated, named skips
# ---------------------------------------------------------------------------

_ANCHOR_MAPS = Path(
    "data/2021a_ssh_mapping_ose/ours/phase14_stage1/anchor_signed_maps.nc"
)
_EVIDENCE = Path("data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json")


@pytest.mark.skipif(
    not _ANCHOR_MAPS.exists(),
    reason=f"anchor gate real leg not run yet: {_ANCHOR_MAPS} absent",
)
def test_anchor_gate_block_recorded_after_real_leg() -> None:
    # Bug caught (once the real leg lands): the run recorded a block with a
    # missing check, a failing sub-block, or without the gate-5 pin — CI
    # would otherwise never re-read the recorded evidence.
    d = json.loads(_EVIDENCE.read_text())
    block = d["phase14"]["stage1"]["anchor_gate"]
    assert set(block["checks"]) == set(_FIVE)
    assert block["pass"] is True
    assert block["pin23"]["tripped"] is False
    gate5 = d["phase14"]["stage1"]["gate5"]
    for key in ("mu", "sigma", "lambda_x"):
        assert isinstance(gate5[key], float)
