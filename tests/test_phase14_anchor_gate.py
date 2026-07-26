"""Anchor identity gate unit tests (phase-14 Stage-1 Task 3) — CI-local.

Covers the CI-testable machinery ONLY: the six-key block assembly
(fail-any-fail, with DEFERRED neither pass nor fail), the locked-tally
guard, the surface-identity exact-equality semantics, the era-no-op
deferral, the accounting buckets, the pin-30 root-conditionality claims,
pin-23 capped-leg detection, the gate-5 write-once pin, and the check-2/4
citation builders. The heavy anchor solve legs are data-gated skips with
named reasons.

Every test names the concrete bug it would catch (test-design discipline);
expected values come from the plan/spec/ruling wording, never from
executing the implementation.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from sverdrup.distributions.calibration import ClipSpec, PolyCalibration
from tests.helpers import load_script

_mod = load_script("phase14_anchor_gate")

# The recorded check keys after the owner's 2026-07-26 check-3 SPLIT,
# restated from the ruling (NOT read off the module — a drift between the
# ruling and the module must fail here, not be mirrored).
_CHECK_KEYS = (
    "tiling_identity",
    "loader_identity",
    "cross_env",
    "score_identity",
    "surface_identity",
    "era_noop",
)
# The keys that carry a verdict at Stage 1 (era_noop is DEFERRED — it is
# neither a pass nor a fail here).
_VERDICT_KEYS = tuple(k for k in _CHECK_KEYS if k != "era_noop")

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


def _deferred_stub(**over: Any) -> dict[str, Any]:
    """A minimally well-formed deferred sub-block (T11 deferral discipline)."""
    block: dict[str, Any] = {
        "status": "deferred",
        "pass": None,
        "deferred_to": "the stage that introduces era-keyed code",
        "reappears_in": "that stage's own coverage walk",
    }
    block.update(over)
    return block


def _passing_checks() -> dict[str, dict[str, Any]]:
    """The green Stage-1 shape: 1/5 run, 2/4 cite, surface passes, era defers."""
    return {
        "tiling_identity": {"status": "pass", "pass": True},
        "loader_identity": {"status": "cited", "pass": True},
        "cross_env": {"status": "cited", "pass": True},
        "score_identity": {"status": "pass", "pass": True},
        "surface_identity": {"status": "pass", "pass": True},
        "era_noop": _deferred_stub(),
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
# Gate-block assembly: six keys, fail-any-fail, deferred is neither
# ---------------------------------------------------------------------------


def test_gate_block_requires_all_six_checks() -> None:
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
    # unconditional pass) lets one RED check ride into a GREEN gate. Covers
    # the post-split key set, era_noop included: a check flipped to fail
    # must still fail the gate.
    for key in _CHECK_KEYS:
        checks = _passing_checks()
        checks[key] = {"status": "fail", "pass": False}
        block = _block(checks)
        assert block["pass"] is False, f"failing {key} must fail the gate"
        assert _mod.gate_exit_code(block) != 0


def test_gate_block_green_with_era_noop_deferred() -> None:
    # Bug caught: a DEFERRED sub-block (pass=None) is aggregated with
    # bool(None) and the gate can NEVER go green — or the cited statuses
    # (2/4) are treated as failures. Green = the run checks green AND the
    # deferred one explicitly deferred.
    block = _block(_passing_checks())
    assert block["pass"] is True
    assert _mod.gate_exit_code(block) == 0
    assert tuple(block["checks"]) == _CHECK_KEYS
    assert block["label"] == "ANCHOR-IDENTITY-GATE"
    assert block["checks"]["era_noop"]["status"] == "deferred"
    assert block["checks"]["era_noop"]["pass"] is None


def test_deferred_check_is_never_counted_as_a_pass() -> None:
    # Bug caught: "deferred" aggregated as green (e.g. status != "fail"
    # counted as a pass) — a gate where NOTHING ran would report GREEN and
    # the deferral would read as "check passed" downstream.
    checks = {k: _deferred_stub() for k in _CHECK_KEYS}
    block = _block(checks)
    assert block["pass"] is False
    assert _mod.gate_exit_code(block) != 0


def test_deferred_check_must_name_where_it_reappears() -> None:
    # Bug caught: a bare {"status": "deferred"} is accepted, so a check can
    # be dropped from the walk forever — the T11 deferral discipline
    # requires naming the stage it defers to and the walk it reappears in.
    for missing in ("deferred_to", "reappears_in"):
        checks = _passing_checks()
        bad = _deferred_stub()
        del bad[missing]
        checks["era_noop"] = bad
        with pytest.raises(ValueError, match=missing):
            _block(checks)


def test_era_noop_cannot_be_recorded_as_a_pass() -> None:
    # Bug caught (the ruling's whole point): the surface-identity proxy is
    # re-attached to the era_noop key as a PASS, and "check 3 passed" ships
    # three documents downstream on evidence that was never run.
    for bad in ({"status": "pass", "pass": True}, {"status": "cited", "pass": True}):
        checks = _passing_checks()
        checks["era_noop"] = bad
        with pytest.raises(ValueError, match="era_noop"):
            _block(checks)


def test_gate_block_rejects_inconsistent_status() -> None:
    # Bug caught: a sub-block claims status "fail" while pass=True (or an
    # unknown status) and the aggregate reads only one of the two fields.
    checks = _passing_checks()
    checks["surface_identity"] = {"status": "fail", "pass": True}
    with pytest.raises(ValueError, match="surface_identity"):
        _block(checks)


def test_gate_block_rejects_non_deferred_null_verdict() -> None:
    # Bug caught: pass=None smuggled into a RUN check, where the aggregate
    # would neither pass nor fail it — a verdict-less check riding along.
    checks = _passing_checks()
    checks["score_identity"] = {"status": "pass", "pass": None}
    with pytest.raises(ValueError, match="score_identity"):
        _block(checks)


# ---------------------------------------------------------------------------
# The accounting block: the gate is NOT "five green"
# ---------------------------------------------------------------------------


def test_accounting_states_the_three_buckets() -> None:
    # Bug caught: the block records a bare pass=True and a reader in Stage 2
    # counts the checks as "five green" — the ruling requires the recorded
    # accounting to name what actually ran, what was cited, and what was
    # proxy-passed with the specified check deferred.
    acc = _block(_passing_checks())["accounting"]
    assert acc["run_and_passed"] == ["tiling_identity", "score_identity"]
    assert acc["cited_and_pre_ratified_at_gate0"] == ["loader_identity", "cross_env"]
    assert acc["proxy_passed_specified_check_deferred"] == [
        "surface_identity (pass) / era_noop (deferred)"
    ]
    assert "2026-07-26" in acc["ruling"]
    assert "five green" in acc["ruling"] or "five green" in acc["statement"]
    assert "TWO checks run and passed" in acc["statement"]
    assert "TWO cited and pre-ratified at Gate 0" in acc["statement"]
    assert "ONE proxy-passed with the specified check deferred" in acc["statement"]
    assert "'five green' does not" in acc["statement"]


def test_accounting_buckets_cover_every_recorded_check() -> None:
    # Bug caught: a check is added (or renamed) and the accounting silently
    # stops describing the block it sits in — the three buckets must
    # partition exactly the recorded key set.
    acc = _block(_passing_checks())["accounting"]
    named = set(acc["run_and_passed"]) | set(acc["cited_and_pre_ratified_at_gate0"])
    for entry in acc["proxy_passed_specified_check_deferred"]:
        named |= {part.split(" ")[0] for part in entry.split(" / ")}
    assert named == set(_CHECK_KEYS)


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
# The check-3 SPLIT: surface identity passes on its own terms (EXACT
# equality, never a tolerance); the era no-op is DEFERRED
# ---------------------------------------------------------------------------

_LON = np.linspace(295.0, 305.0, 5)
_LAT = np.linspace(33.0, 43.0, 5)


def test_surface_identity_exact_identity_passes() -> None:
    # Bug caught: the check compares against the wrong artifact node (or
    # never evaluates the surface) so the true identity reads as a fail.
    cal = _cal()
    block = _mod.check_surface_identity(cal, _signed_field_for(cal), _LON, _LAT)
    assert block["pass"] is True
    assert block["status"] == "pass"
    assert block["cal_key_equal"] is True
    assert block["surface_exact_equal"] is True
    assert block["n_points"] == _LON.size * _LAT.size


def test_surface_identity_claims_only_its_own_terms() -> None:
    # Bug caught: the surface check is recorded under the era-no-op claim
    # again — it must name itself and say what it actually proves (no drift
    # in the SHIPPED CALIBRATION SURFACE), never "era no-op" / "check 3".
    cal = _cal()
    block = _mod.check_surface_identity(cal, _signed_field_for(cal), _LON, _LAT)
    claim = f"{block['name']} {block['what_it_proves']}".lower()
    assert "shipped calibration surface" in claim
    assert re.search(r"\bera\b|era-", claim) is None, claim
    assert "no-op" not in claim
    assert "check 3" not in claim
    assert block["equality"] == "exact (==), by construction — never a tolerance"


def test_surface_identity_rejects_last_ulp_coeff_perturbation() -> None:
    # Bug caught: someone softens the == to allclose; a 1e-13 coefficient
    # drift would pass any reasonable tolerance but violates the spec's
    # "EXACTLY, BY CONSTRUCTION — an identity, not a tolerance".
    cal = _cal()
    coeffs = list(_SIGNED_FIELD["calibration"]["coeffs"])
    coeffs[0] += 1e-13
    drifted = _cal(coeffs=coeffs)
    block = _mod.check_surface_identity(drifted, _signed_field_for(cal), _LON, _LAT)
    assert block["pass"] is False
    assert block["status"] == "fail"


def test_surface_identity_rejects_descriptor_mismatch_with_equal_values() -> None:
    # Bug caught: the check compares surface VALUES only — a fit_id
    # (provenance) drift with numerically identical values would pass and
    # the gate would cite the wrong fit lineage as the signed s(x).
    cal = _cal()
    relabeled = _cal(fit_id="L-BFGS-B;gtol=1e-07")
    block = _mod.check_surface_identity(relabeled, _signed_field_for(cal), _LON, _LAT)
    assert block["pass"] is False
    assert block["cal_key_equal"] is False
    # values ARE equal — only the descriptor differs (isolates the bug)
    assert block["surface_exact_equal"] is True


def _superseded() -> dict[str, Any]:
    cal = _cal()
    surface = _mod.check_surface_identity(cal, _signed_field_for(cal), _LON, _LAT)
    return _mod.superseded_check3_recording(
        surface, artifact={"path": "phase13_field_miost.json", "sha256": "ab"}
    )


def test_era_noop_block_is_deferred_and_verdict_less() -> None:
    # Bug caught: the deferral is recorded with pass=False (reads as a
    # FAILED check downstream) or pass=True (the proxy masquerading again).
    # SPEC §10 check 3 is UNRUNNABLE at Stage 1 — neither pass nor fail.
    block = _mod.build_era_noop_deferred(superseded=_superseded())
    assert block["status"] == "deferred"
    assert block["pass"] is None
    assert "SPEC §10 check 3" in block["name"]
    assert "spec §10 check 3" in block["spec_citation"]


def test_era_noop_deferral_names_the_stage_and_the_walk() -> None:
    # Bug caught: the deferral names no destination, so nothing forces the
    # check to reappear — a deferred check silently becomes a dropped one.
    block = _mod.build_era_noop_deferred(superseded=_superseded())
    assert "era-keyed" in block["deferred_to"]
    assert "Stage 2" in block["deferred_to"]
    assert "fork E" in block["deferred_to"]
    assert "coverage walk" in block["reappears_in"]
    assert "T11" in block["reappears_in"]
    assert "UNRUNNABLE at Stage 1" in block["why"]
    assert "three documents downstream" in block["why"]


def test_era_noop_preserves_the_superseded_recording_verbatim() -> None:
    # Bug caught: the split DELETES the prior (proxy-pass) recording, so the
    # amended evidence loses what was previously claimed and the ruling
    # becomes unauditable.
    prior = _superseded()
    block = _mod.build_era_noop_deferred(superseded=prior)
    assert block["superseded_recording"] == prior
    assert prior["status"] == "pass"
    assert prior["pass"] is True
    assert prior["cal_key_equal"] is True
    assert prior["artifact"]["sha256"] == "ab"
    assert "RECORDED READING" in prior["reading"]


# ---------------------------------------------------------------------------
# Pin 30: what the four routes are conditional ON
# ---------------------------------------------------------------------------

_ACCEPTANCE_ROOT = 7742201642112487637


def test_root_conditionality_claims_are_route_specific() -> None:
    # Bug caught: the member route is recorded as proving root-INDEPENDENCE
    # (it proves reproduction UNDER shipped_miost5().member_root only), or
    # the variance route is called root-independent when it is computed from
    # the same member draws and inherits their conditionality.
    rc = _mod.root_conditionality(_ACCEPTANCE_ROOT)
    assert rc["ruling"] == "owner pin 30, 2026-07-26"
    assert rc["member_route"] == (
        "CONDITIONAL on shipped_miost5().member_root (7742201642112487637) — "
        "the route proves REPRODUCTION UNDER THAT ROOT (the reference members "
        "were drawn with it), never root-independence"
    )
    assert rc["mean_and_gamma_routes"] == "root-independent"
    assert rc["variance_route"] == (
        "computed from the same member draws — inherits the member route's "
        "root conditionality"
    )
    assert "4836134738817689931" in rc["plan_text_was_wrong"]


def test_root_conditionality_carries_the_root_actually_used() -> None:
    # Bug caught: the recorded conditionality hardcodes the acceptance root
    # while the run used another one — the claim would name a root the
    # members were not drawn with.
    rc = _mod.root_conditionality(123456789)
    assert "123456789" in rc["member_route"]
    assert str(_ACCEPTANCE_ROOT) not in rc["member_route"]


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
    assert tuple(block["checks"]) == _CHECK_KEYS
    assert block["pass"] is True
    assert block["pin23"]["tripped"] is False
    gate5 = d["phase14"]["stage1"]["gate5"]
    for key in ("mu", "sigma", "lambda_x"):
        assert isinstance(gate5[key], float)


@pytest.mark.skipif(
    not _EVIDENCE.exists(),
    reason=f"evidence store absent: {_EVIDENCE}",
)
def test_recorded_split_matches_what_a_rerun_would_build() -> None:
    # Bug caught: a re-run REVERTS the owner's amended shape — it re-records
    # a passing era_noop, drops the accounting or the pin-30 conditionality,
    # or emits different key names than the ruled block the owner walked.
    d = json.loads(_EVIDENCE.read_text())
    block = d["phase14"]["stage1"]["anchor_gate"]
    recorded = block["checks"]
    assert recorded["era_noop"]["status"] == "deferred"
    assert recorded["era_noop"]["pass"] is None
    assert recorded["surface_identity"]["status"] == "pass"

    cal = _cal()
    built_surface = _mod.check_surface_identity(cal, _signed_field_for(cal), _LON, _LAT)
    built_era = _mod.build_era_noop_deferred(superseded=_superseded())
    assert set(built_surface) == set(recorded["surface_identity"])
    assert set(built_era) == set(recorded["era_noop"])
    assert set(built_era["superseded_recording"]) == set(
        recorded["era_noop"]["superseded_recording"]
    )
    # Wording, not just shape: the deferral prose the owner ruled.
    for key in ("name", "deferred_to", "why", "reappears_in", "spec_citation"):
        assert built_era[key] == recorded["era_noop"][key], key
    for key in ("name", "equality", "what_it_proves"):
        assert built_surface[key] == recorded["surface_identity"][key], key

    assert _block(_passing_checks())["accounting"] == block["accounting"]
    assert (
        _mod.root_conditionality(block["root_int"])
        == recorded["tiling_identity"]["root_conditionality"]
    )
