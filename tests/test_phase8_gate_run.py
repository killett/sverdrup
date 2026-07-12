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

import pytest

from sverdrup.application.calibration.constants import COVERAGE_TARGET, COVERAGE_TOL
from sverdrup.distributions.miost_ensemble import ScalarCalibration

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


def _results(
    *,
    negative: bool = False,
    with_c2: bool = False,
    with_ref: bool = True,
) -> dict[str, Any]:
    """Build a synthetic gate-results dict with controllable gating fields."""
    r: dict[str, Any] = {
        "phase8": {"fit_run": {"selection": {"negative_result": negative}}}
    }
    if with_c2:
        r["phase8"]["c2_acceptance"] = {"verdict": "SIGN-OFF"}
    if with_ref:
        r["stage_b"] = {
            "c2_acceptance": {
                "stage_a_reference": [
                    0.8572611954190728,
                    0.07998859332412292,
                    156.42996684578844,
                ]
            }
        }
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
# check_not_already_touched — one-touch discipline
# ---------------------------------------------------------------------------


def test_preexisting_c2_acceptance_refuses() -> None:
    """phase8.c2_acceptance already present -> refuse a second touch.

    Bug caught: a re-run that silently re-touches c2, violating the
    one-touch owner discipline (a second evaluation must demand owner
    adjudication, not proceed).
    """
    with pytest.raises(gate.GateRefusal) as exc:
        gate.check_not_already_touched(_results(with_c2=True))
    assert "already exists" in str(exc.value)


def test_no_prior_c2_acceptance_passes() -> None:
    """No phase8.c2_acceptance -> no raise (first, authorized touch).

    Bug caught: a guard that refuses even the first legitimate touch.
    """
    gate.check_not_already_touched(_results(with_c2=False))


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
# _run_refusal_checks — ordering: all refusals fire BEFORE any data load
# ---------------------------------------------------------------------------


def test_refusal_ordering_no_data_loaded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With the flag set but a pre-existing c2_acceptance, refusal fires with
    the map/track paths pointed at NONEXISTENT files — proving no data load.

    Bug caught: a runner that loads c2 (or the maps) before checking the
    one-touch guard, which would spend the touch on a re-run.
    """
    monkeypatch.setenv("SVERDRUP_MIOST_C2", "1")
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
    # The nonexistent maps were never opened — the refusal returned first.
    assert not (tmp_path / "does_not_exist_mean.nc").exists()


def test_refusal_ordering_all_pass_returns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When every gate passes, _run_refusal_checks returns the parsed inputs.

    Bug caught: a check that raises on a fully valid pre-touch state, which
    would make the authorized touch impossible to run.
    """
    monkeypatch.setenv("SVERDRUP_MIOST_C2", "1")
    field = _consistent_field()
    monkeypatch.setattr(gate, "FIELD_IN", _write_field(tmp_path / "f.json", field))
    results_path = tmp_path / "results.json"
    results_path.write_text(json.dumps(_results()))
    monkeypatch.setattr(gate, "RESULTS", results_path)

    results, got_field, ref = gate._run_refusal_checks()
    assert got_field["cal_key"] == field["cal_key"]
    assert ref == [0.8572611954190728, 0.07998859332412292, 156.42996684578844]
    assert "c2_acceptance" not in results["phase8"]
