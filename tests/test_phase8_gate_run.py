"""Refusal-path logic tests for ``scripts/phase8_gate_run.py``.

These tests exercise ONLY the pure refusal checks (env, field presence,
cal_key self-consistency, negative_result, one-touch discipline) and the
pre-registered coverage/triplet readings.  They use synthetic tmp fixtures —
NO real gate data is read and c2 is NEVER loaded.  Each refusal must fire
BEFORE any data load, so pointing the path constants at nonexistent maps is
enough to prove no touch occurs.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from sverdrup.application.calibration.constants import COVERAGE_TARGET, COVERAGE_TOL
from sverdrup.distributions.calibration import ScalarCalibration

# Load the runner as a module directly from scripts/ (not on the package path).
_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "phase8_gate_run.py"
_spec = importlib.util.spec_from_file_location("phase8_gate_run", _SCRIPT)
assert _spec is not None and _spec.loader is not None
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)


# ---------------------------------------------------------------------------
# Synthetic fixtures (no real data)
# ---------------------------------------------------------------------------


def _consistent_field(s: float = 10.0) -> dict[str, Any]:
    """A self-consistent winner-field dict (cal_key == recomputed key)."""
    cal = ScalarCalibration(s)
    return {"calibration": cal.to_json(), "cal_key": cal.key()}


def _write_field(path: Path, field: dict[str, Any]) -> Path:
    """Write a field dict to disk and return the path."""
    path.write_text(json.dumps(field))
    return path


N_FULL_YEAR = 44844  # Task-19 recorded full-year c2 count (the tripwire target).


def _results(
    *,
    negative: bool = False,
    with_c2: bool = False,
    with_defect: bool = False,
    with_ref: bool = True,
    with_n_full: bool = True,
) -> dict[str, Any]:
    """Build a synthetic gate-results dict with controllable gating fields.

    Args:
        negative: Set phase8.fit_run.selection.negative_result.
        with_c2: Add a phase8.c2_acceptance block (defect-run stand-in).
        with_defect: Add a phase8.c2_defect_run_20260712 block.
        with_ref: Include stage_b.c2_acceptance.stage_a_reference triplet.
        with_n_full: Include the full-year n_points tripwire target.
    """
    r: dict[str, Any] = {
        "phase8": {"fit_run": {"selection": {"negative_result": negative}}}
    }
    if with_c2:
        r["phase8"]["c2_acceptance"] = {"verdict": "SIGN-OFF", "n_points": 2353}
    if with_defect:
        r["phase8"]["c2_defect_run_20260712"] = {"verdict": "SIGN-OFF"}
    sb: dict[str, Any] = {}
    if with_ref:
        sb["stage_a_reference"] = [
            0.8572611954190728,
            0.07998859332412292,
            156.42996684578844,
        ]
    if with_n_full:
        sb["calibration_at_frozen_s_star"] = {"n_points": N_FULL_YEAR}
    if sb:
        r["stage_b"] = {"c2_acceptance": sb}
    return r


# ---------------------------------------------------------------------------
# check_authorized — the env gate
# ---------------------------------------------------------------------------


def test_missing_env_refuses() -> None:
    """No SVERDRUP_MIOST_C2 -> refuse (nonzero exit), load nothing.

    Bug caught: a runner that treats the Task-10 PROCEED as standing
    authorization and touches c2 without the fresh per-touch flag.
    """
    with pytest.raises(gate.GateRefusal) as exc:
        gate.check_authorized(env={})
    assert exc.value.code is not None and exc.value.code != 0
    assert "SVERDRUP_MIOST_C2" in str(exc.value)


@pytest.mark.parametrize("val", ["0", "true", "yes", "", "2", " 1", "1 "])
def test_wrong_env_value_refuses(val: str) -> None:
    """Only the exact string "1" authorizes; any other value refuses.

    Bug caught: a truthy check (``if os.environ.get(FLAG):``) that would
    accept "0" or a stray whitespace-padded "1".
    """
    with pytest.raises(gate.GateRefusal):
        gate.check_authorized(env={"SVERDRUP_MIOST_C2": val})


def test_exact_env_value_passes() -> None:
    """SVERDRUP_MIOST_C2=1 authorizes (no raise).

    Bug caught: an over-strict gate that never lets the authorized touch run.
    """
    gate.check_authorized(env={"SVERDRUP_MIOST_C2": "1"})


# ---------------------------------------------------------------------------
# check_field_self_consistent — presence + cal_key round-trip
# ---------------------------------------------------------------------------


def test_missing_field_refuses(tmp_path: Path) -> None:
    """Absent phase8_field.json -> refuse.

    Bug caught: a runner that proceeds to score with no field to load.
    """
    with pytest.raises(gate.GateRefusal) as exc:
        gate.check_field_self_consistent(tmp_path / "nope.json")
    assert "absent" in str(exc.value)


def test_cal_key_mismatch_refuses(tmp_path: Path) -> None:
    """cal_key not matching the recomputed key -> refuse.

    Bug caught: silently accepting a field whose recorded cal_key does not
    match ``calibration_from_json(to_json).key()`` — i.e. a tampered or
    stale artifact, which would score a DIFFERENT field than certified.
    """
    field = _consistent_field()
    field["cal_key"] = "cal:scalar;s=99.0"  # deliberately wrong
    p = _write_field(tmp_path / "field.json", field)
    with pytest.raises(gate.GateRefusal) as exc:
        gate.check_field_self_consistent(p)
    assert "self-consistent" in str(exc.value)


def test_malformed_field_refuses(tmp_path: Path) -> None:
    """A field JSON missing the calibration block -> refuse (no crash).

    Bug caught: an unguarded ``field["calibration"]`` KeyError that would
    surface as an opaque traceback instead of a clear refusal.
    """
    p = _write_field(tmp_path / "field.json", {"cal_key": "x"})
    with pytest.raises(gate.GateRefusal):
        gate.check_field_self_consistent(p)


def test_consistent_field_passes(tmp_path: Path) -> None:
    """A self-consistent field returns the parsed dict.

    Bug caught: a check that rejects a valid, self-consistent artifact.
    """
    field = _consistent_field()
    p = _write_field(tmp_path / "field.json", field)
    got = gate.check_field_self_consistent(p)
    assert got["cal_key"] == field["cal_key"]


# ---------------------------------------------------------------------------
# check_not_negative_result
# ---------------------------------------------------------------------------


def test_negative_result_refuses() -> None:
    """selection.negative_result true -> refuse.

    Bug caught: accepting a phase with NO winner field onto c2, which would
    spend the single touch scoring a non-existent selection.
    """
    with pytest.raises(gate.GateRefusal) as exc:
        gate.check_not_negative_result(_results(negative=True))
    assert "negative_result" in str(exc.value)


def test_non_negative_result_passes() -> None:
    """selection.negative_result false -> no raise.

    Bug caught: a check that blocks the legitimate positive-result path.
    """
    gate.check_not_negative_result(_results(negative=False))


# ---------------------------------------------------------------------------
# resolve_scope — one window/track source (owner rider 1)
# ---------------------------------------------------------------------------


def test_scope_default_is_full() -> None:
    """No SVERDRUP_PHASE8_SCOPE -> resolves to 'full' (the c2-authorized scope).

    Bug caught: a default that silently falls back to the dev fixture bounds —
    the exact partial-window class the DEFECT-RUN suffered.
    """
    assert gate.resolve_scope(env={}) == "full"


def test_scope_full_explicit_is_full() -> None:
    """SVERDRUP_PHASE8_SCOPE=full -> 'full'.

    Bug caught: an over-strict resolver that rejects the explicit full scope.
    """
    assert gate.resolve_scope(env={"SVERDRUP_PHASE8_SCOPE": "full"}) == "full"


def test_scope_dev_refuses() -> None:
    """SVERDRUP_PHASE8_SCOPE=dev -> refuse (no c2 authorization semantics).

    Bug caught: a dev mode that runs a partial-window c2 evaluation instead of
    refusing — dev must never spend or corrupt the single c2 touch.
    """
    with pytest.raises(gate.GateRefusal) as exc:
        gate.resolve_scope(env={"SVERDRUP_PHASE8_SCOPE": "dev"})
    assert "no c2 authorization semantics" in str(exc.value)


def test_scope_invalid_value_refuses() -> None:
    """An unknown scope value -> refuse (mirrors phase8_fit_run validation).

    Bug caught: silently treating a typo'd scope as full (or dev).
    """
    with pytest.raises(gate.GateRefusal) as exc:
        gate.resolve_scope(env={"SVERDRUP_PHASE8_SCOPE": "smoke"})
    assert "must be 'dev' or 'full'" in str(exc.value)


# ---------------------------------------------------------------------------
# full_year_n_points — the tripwire target read from the results JSON
# ---------------------------------------------------------------------------


def test_full_year_n_points_reads_recorded_count() -> None:
    """The tripwire target is READ from stage_b, not hard-coded.

    Bug caught: a hard-coded 44844 that would silently pass even if the signed
    record changed — the constant must trace to the recorded Task-19 count.
    """
    assert gate.full_year_n_points(_results()) == N_FULL_YEAR


def test_full_year_n_points_missing_refuses() -> None:
    """Absent full-year count -> refuse (cannot establish the tripwire target).

    Bug caught: defaulting the target to 0 or None, which would make the
    n-count tripwire a no-op.
    """
    with pytest.raises(gate.GateRefusal):
        gate.full_year_n_points(_results(with_n_full=False))


# ---------------------------------------------------------------------------
# check_touch_protocol — the UPGRADED corrected-touch refusal matrix (rider 3)
# ---------------------------------------------------------------------------
#
#   C = SVERDRUP_PHASE8_CORRECTED_TOUCH=1
#   A = phase8.c2_acceptance present
#   D = phase8.c2_defect_run_20260712 present
#
#   C      A    D    outcome
#   unset  yes  -    REFUSE (unchanged one-touch)
#   unset  no   -    REFUSE (no bare re-invocation)
#   set    yes  no   PROCEED (migrate then evaluate — the current real state)
#   set    no   yes  PROCEED (resume)
#   set    yes  yes  REFUSE (third invocation)
#   set    no   no   REFUSE (flag invalid — nothing to correct)


def test_matrix_unset_flag_acceptance_present_refuses() -> None:
    """C unset + A -> refuse (unchanged one-touch discipline).

    Bug caught: dropping the original one-touch guard while adding the corrected
    path — a bare re-run would silently re-touch c2.
    """
    with pytest.raises(gate.GateRefusal) as exc:
        gate.check_touch_protocol(_results(with_c2=True), env={})
    assert "already exists" in str(exc.value)


def test_matrix_unset_flag_no_acceptance_refuses() -> None:
    """C unset + no A -> refuse (corrected touch is the only sanctioned path).

    Bug caught: a first-touch without the corrected flag proceeding — the flag
    is now mandatory for any c2 invocation (touch 2 protocol).
    """
    with pytest.raises(gate.GateRefusal) as exc:
        gate.check_touch_protocol(_results(with_c2=False), env={})
    assert "CORRECTED_TOUCH" in str(exc.value)


def test_matrix_corrected_acceptance_no_defect_proceeds() -> None:
    """C + A + no D -> PROCEED (migrate-then-evaluate; the current real state).

    Bug caught: refusing the exact state the corrected touch must run from
    (defect-run c2_acceptance present, defect key not yet created).
    """
    gate.check_touch_protocol(
        _results(with_c2=True, with_defect=False),
        env={"SVERDRUP_PHASE8_CORRECTED_TOUCH": "1"},
    )


def test_matrix_corrected_defect_no_acceptance_proceeds() -> None:
    """C + D + no A -> PROCEED (resume path; migration already applied).

    Bug caught: refusing a legitimate resume after the rename already happened.
    """
    gate.check_touch_protocol(
        _results(with_c2=False, with_defect=True),
        env={"SVERDRUP_PHASE8_CORRECTED_TOUCH": "1"},
    )


def test_matrix_corrected_acceptance_and_defect_refuses() -> None:
    """C + A + D -> refuse (third invocation; corrected already done).

    Bug caught: a third run overwriting the corrected c2_acceptance after both
    the defect key and a fresh acceptance already exist.
    """
    with pytest.raises(gate.GateRefusal) as exc:
        gate.check_touch_protocol(
            _results(with_c2=True, with_defect=True),
            env={"SVERDRUP_PHASE8_CORRECTED_TOUCH": "1"},
        )
    assert "third invocation" in str(exc.value)


def test_matrix_corrected_neither_key_refuses() -> None:
    """C + no A + no D -> refuse (flag invalid without a recorded defect).

    Bug caught: honoring the corrected flag when there is nothing to correct —
    the flag must not authorize a fresh first-touch.
    """
    with pytest.raises(gate.GateRefusal) as exc:
        gate.check_touch_protocol(
            _results(with_c2=False, with_defect=False),
            env={"SVERDRUP_PHASE8_CORRECTED_TOUCH": "1"},
        )
    assert "nothing to correct" in str(exc.value)


# ---------------------------------------------------------------------------
# migrate_defect_run — rename c2_acceptance -> defect key (rider 3)
# ---------------------------------------------------------------------------


def test_migration_renames_and_annotates() -> None:
    """The defect-run c2_acceptance is renamed to the defect key + annotated.

    Bug caught: overwriting/losing the defect-run block instead of preserving it
    as disclosed context; or forgetting the recorded defect note.
    """
    r = _results(with_c2=True, with_defect=False)
    original = dict(r["phase8"]["c2_acceptance"])
    changed = gate.migrate_defect_run(r)
    assert changed is True
    assert "c2_acceptance" not in r["phase8"]
    moved = r["phase8"]["c2_defect_run_20260712"]
    # The original content is preserved verbatim under the new key ...
    for k, v in original.items():
        assert moved[k] == v
    # ... plus the disclosure annotations.
    assert moved["defect_recorded"] == "2026-07-12"
    assert "partial-window" in moved["defect"]
    assert "context, never evidence" in moved["defect"]


def test_migration_frees_acceptance_slot_for_fresh_eval() -> None:
    """After migration a fresh c2_acceptance can be written without collision.

    Bug caught: leaving the old c2_acceptance in place so the fresh evaluation
    would silently merge into / collide with the defect run.
    """
    r = _results(with_c2=True, with_defect=False)
    gate.migrate_defect_run(r)
    r["phase8"]["c2_acceptance"] = {"verdict": "SIGN-OFF", "fresh": True}
    assert r["phase8"]["c2_acceptance"]["fresh"] is True
    assert r["phase8"]["c2_defect_run_20260712"]["verdict"] == "SIGN-OFF"


def test_migration_is_noop_on_resume() -> None:
    """With the defect key already present, migration is a no-op.

    Bug caught: a second migration clobbering an existing defect key or moving a
    fresh acceptance into it.
    """
    r = _results(with_c2=False, with_defect=True)
    assert gate.migrate_defect_run(r) is False
    assert "c2_defect_run_20260712" in r["phase8"]


def test_migration_is_noop_when_no_acceptance() -> None:
    """With no c2_acceptance to move, migration is a no-op.

    Bug caught: fabricating an empty defect block from nothing.
    """
    r = _results(with_c2=False, with_defect=False)
    assert gate.migrate_defect_run(r) is False
    assert "c2_defect_run_20260712" not in r["phase8"]


# ---------------------------------------------------------------------------
# stage_a_reference_triplet — reads the FULL-precision signed floats
# ---------------------------------------------------------------------------


def test_stage_a_reference_full_precision() -> None:
    """The reference triplet is read verbatim, at full stored precision.

    Bug caught: comparing against rounded literals (0.8572612, ...) instead
    of the exact stored floats — which would make the bit-identity verdict
    pass on values that are NOT bit-identical.
    """
    ref = gate.stage_a_reference_triplet(_results())
    assert ref == [0.8572611954190728, 0.07998859332412292, 156.42996684578844]


def test_missing_reference_refuses() -> None:
    """Absent stage-A reference triplet -> refuse (cannot apply the reading).

    Bug caught: defaulting to a synthesized/empty reference, which would
    turn the bit-identity check into a no-op.
    """
    with pytest.raises(gate.GateRefusal):
        gate.stage_a_reference_triplet(_results(with_ref=False))


# ---------------------------------------------------------------------------
# coverage_verdict — the pre-registered coverage reading
# ---------------------------------------------------------------------------


def test_coverage_in_band_signs_off() -> None:
    """Coverage within target±tol -> SIGN-OFF.

    Bug caught: an inverted band comparison that would HOLD an in-band run.
    """
    assert gate.coverage_verdict(COVERAGE_TARGET) == "SIGN-OFF"
    assert gate.coverage_verdict(COVERAGE_TARGET + COVERAGE_TOL) == "SIGN-OFF"
    assert gate.coverage_verdict(COVERAGE_TARGET - COVERAGE_TOL) == "SIGN-OFF"


def test_coverage_outside_band_holds() -> None:
    """Coverage outside target±tol -> HOLD.

    Bug caught: a too-wide band (or a >= vs > slip) that would sign off an
    out-of-band coverage the owner must adjudicate.
    """
    assert gate.coverage_verdict(COVERAGE_TARGET + COVERAGE_TOL + 1e-6) == "HOLD"
    assert gate.coverage_verdict(COVERAGE_TARGET - COVERAGE_TOL - 1e-6) == "HOLD"
    assert gate.coverage_verdict(0.30) == "HOLD"


# ---------------------------------------------------------------------------
# window_tripwire — the pre-registered full-year precondition (owner rider 2)
# ---------------------------------------------------------------------------


def _full_year_times(n: int) -> np.ndarray:
    """n times spread evenly across 2017 (Jan 1 .. Dec 31), datetime64[ns]."""
    days = np.linspace(0, 364, n).round().astype("int64")
    return np.datetime64("2017-01-01") + days * np.timedelta64(1, "D")


def test_tripwire_full_year_passes() -> None:
    """Full count + full-year span -> pass record (no raise).

    Bug caught: a tripwire so strict it rejects the legitimate full-year set.
    """
    times = _full_year_times(N_FULL_YEAR)
    rec = gate.window_tripwire(N_FULL_YEAR, times, N_FULL_YEAR)
    assert rec["passed"] is True
    assert rec["n_points_match"] is True
    assert rec["spans_challenge_year"] is True
    assert rec["in_challenge_bounds"] is True


def test_tripwire_n_mismatch_raises_and_records() -> None:
    """n_points != expected -> WindowTripwire (nonzero) with the count recorded.

    Bug caught: the exact DEFECT-RUN failure — 2,353 points scored as if full;
    the count mismatch must be a loud defect-STOP, not a silent acceptance.
    """
    # Even with a full-year span, the wrong count must trip.
    times = _full_year_times(2353)
    with pytest.raises(gate.WindowTripwire) as exc:
        gate.window_tripwire(2353, times, N_FULL_YEAR)
    assert exc.value.code is not None and exc.value.code != 0
    msg = str(exc.value)
    assert "2353" in msg and str(N_FULL_YEAR) in msg


def test_tripwire_date_range_mismatch_raises() -> None:
    """A 21-day dev window (right count, wrong span) -> WindowTripwire.

    Bug caught: checking only the count and not the date span — a full-count set
    concentrated in a 21-day window would sneak through.
    """
    base = np.datetime64("2017-02-25")
    times = base + (np.arange(N_FULL_YEAR) % 21) * np.timedelta64(1, "D")
    with pytest.raises(gate.WindowTripwire) as exc:
        gate.window_tripwire(N_FULL_YEAR, times, N_FULL_YEAR)
    assert "spans_year=False" in str(exc.value)


def test_tripwire_out_of_challenge_bounds_raises() -> None:
    """Times outside [2017-01-01, 2018-01-01) -> WindowTripwire.

    Bug caught: accepting a set that leaks into 2016 or 2018 — the loaded window
    must sit inside the challenge bounds.
    """
    times = np.datetime64("2016-06-01") + np.linspace(
        0, 400, N_FULL_YEAR
    ).round().astype("int64") * np.timedelta64(1, "D")
    with pytest.raises(gate.WindowTripwire) as exc:
        gate.window_tripwire(N_FULL_YEAR, times, N_FULL_YEAR)
    assert "in_bounds=False" in str(exc.value)


# ---------------------------------------------------------------------------
# _run_refusal_checks — ordering: all refusals fire BEFORE any data load
# ---------------------------------------------------------------------------


def test_refusal_ordering_no_data_loaded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A bare re-invocation (no corrected flag) with c2_acceptance present
    refuses with the map/track paths pointed at NONEXISTENT files — proving no
    data load.

    Bug caught: a runner that loads c2 (or the maps) before checking the
    one-touch guard, which would spend the touch on a re-run.
    """
    monkeypatch.setenv("SVERDRUP_MIOST_C2", "1")
    monkeypatch.delenv("SVERDRUP_PHASE8_CORRECTED_TOUCH", raising=False)
    monkeypatch.delenv("SVERDRUP_PHASE8_SCOPE", raising=False)
    monkeypatch.setattr(
        gate, "FIELD_IN", _write_field(tmp_path / "field.json", _consistent_field())
    )
    monkeypatch.setattr(gate, "MEAN_NC", tmp_path / "does_not_exist_mean.nc")
    monkeypatch.setattr(gate, "VAR_NC", tmp_path / "does_not_exist_var.nc")
    results_path = tmp_path / "results.json"
    results_path.write_text(json.dumps(_results(with_c2=True)))
    monkeypatch.setattr(gate, "RESULTS", results_path)

    with pytest.raises(gate.GateRefusal) as exc:
        gate._run_refusal_checks()
    assert "already exists" in str(exc.value)


def test_refusal_ordering_dev_scope_refuses_before_load(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SVERDRUP_PHASE8_SCOPE=dev refuses inside _run_refusal_checks (no load).

    Bug caught: the scope refusal wired after the field/track load instead of in
    the pure pre-touch gate — a dev invocation must never reach the maps.
    """
    monkeypatch.setenv("SVERDRUP_MIOST_C2", "1")
    monkeypatch.setenv("SVERDRUP_PHASE8_CORRECTED_TOUCH", "1")
    monkeypatch.setenv("SVERDRUP_PHASE8_SCOPE", "dev")
    monkeypatch.setattr(gate, "FIELD_IN", tmp_path / "does_not_exist_field.json")
    monkeypatch.setattr(gate, "MEAN_NC", tmp_path / "does_not_exist_mean.nc")
    monkeypatch.setattr(gate, "RESULTS", tmp_path / "does_not_exist_results.json")

    with pytest.raises(gate.GateRefusal) as exc:
        gate._run_refusal_checks()
    assert "no c2 authorization semantics" in str(exc.value)


def test_refusal_ordering_all_pass_returns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The migrate-then-evaluate state (corrected flag, defect-run c2_acceptance
    present, defect key absent) passes and returns the parsed inputs.

    Bug caught: a check that raises on the valid corrected-touch pre-state, which
    would make the authorized touch 2 impossible to run.
    """
    monkeypatch.setenv("SVERDRUP_MIOST_C2", "1")
    monkeypatch.setenv("SVERDRUP_PHASE8_CORRECTED_TOUCH", "1")
    monkeypatch.delenv("SVERDRUP_PHASE8_SCOPE", raising=False)
    field = _consistent_field()
    monkeypatch.setattr(gate, "FIELD_IN", _write_field(tmp_path / "f.json", field))
    results_path = tmp_path / "results.json"
    results_path.write_text(json.dumps(_results(with_c2=True, with_defect=False)))
    monkeypatch.setattr(gate, "RESULTS", results_path)

    results, got_field, ref, n_expected = gate._run_refusal_checks()
    assert got_field["cal_key"] == field["cal_key"]
    assert ref == [0.8572611954190728, 0.07998859332412292, 156.42996684578844]
    assert n_expected == N_FULL_YEAR
    # Refusal checks do NOT mutate — migration happens later in main().
    assert "c2_acceptance" in results["phase8"]
