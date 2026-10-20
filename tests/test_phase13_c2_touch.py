"""Refusal tests for the phase-13 c2 touch (plan Task 13; green BEFORE
the touch). Each test names the bug it catches; the ceremony matrix is
the phase-8 owner-rider-3 template on phase13 keys.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.helpers import load_script

touch = load_script("phase13_c2_touch")


def test_no_env_refuses_before_any_data() -> None:
    # Exact-string-"1" authorization: any other value refuses with no
    # data loaded (delegated to the phase-12 check, invoked FIRST).
    # Bug caught: the touch proceeding on an unset/mistyped env.
    p12 = touch._p12()
    with pytest.raises(SystemExit, match="SVERDRUP_MIOST_C2"):
        p12.check_authorized(env={})
    with pytest.raises(SystemExit, match="SVERDRUP_MIOST_C2"):
        p12.check_authorized(env={"SVERDRUP_MIOST_C2": "true"})


def test_protocol_spent_refuses_second_invocation() -> None:
    # First touch spent -> a second plain invocation refuses.
    # Bug caught: silent re-execution of the claim-bearing touch.
    ev: dict[str, Any] = {"phase13": {"miost": {"c2_acceptance": {"x": 1}}}}
    with pytest.raises(SystemExit, match="spent"):
        touch.check_touch_protocol(ev, env={})


def test_protocol_third_invocation_refuses() -> None:
    # Corrected flag with BOTH acceptance and a defect key -> the third
    # invocation refuses (owner-gated beyond that).
    # Bug caught: the corrected path looping (unbounded re-touches).
    ev: dict[str, Any] = {
        "phase13": {
            "miost": {
                "c2_acceptance": {"x": 1},
                "c2_defect_run_20260721": {"y": 2},
            }
        }
    }
    with pytest.raises(SystemExit, match="third"):
        touch.check_touch_protocol(ev, env={"SVERDRUP_MIOST_C2_CORRECTED": "1"})


def test_protocol_corrected_without_defect_refuses() -> None:
    # Corrected flag with nothing to correct -> refuse.
    # Bug caught: the corrected flag used as a bypass on a clean state.
    ev: dict[str, Any] = {"phase13": {"miost": {}}}
    with pytest.raises(SystemExit, match="invalid"):
        touch.check_touch_protocol(ev, env={"SVERDRUP_MIOST_C2_CORRECTED": "1"})


def test_protocol_first_touch_proceeds() -> None:
    # Clean state, no corrected flag -> PROCEED (returns None).
    # Bug caught: an over-eager matrix refusing the ONE authorized touch.
    ev: dict[str, Any] = {"phase13": {"miost": {"members": {"m": 100}}}}
    assert touch.check_touch_protocol(ev, env={}) is None


_TRIPWIRE_FIELDS = (
    "mean_maps_sha256",
    "var_maps_sha256",
    "member_store_sha256",
    "field_artifact_sha256",
    "cal_key",
)


def _tripwire_substrate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Any]:
    """Small temp artifacts in place of the real (1.4 GB) set; the correct
    recorded block computed INDEPENDENTLY (hashlib), not by the module."""
    import hashlib

    recorded: dict[str, Any] = {}
    for attr, field, body in (
        ("_MEAN", "mean_maps_sha256", b"mean"),
        ("_VAR", "var_maps_sha256", b"var"),
        ("_STORE", "member_store_sha256", b"store"),
        ("_FIELD", "field_artifact_sha256", b"field"),
    ):
        f = tmp_path / f"{attr.strip('_').lower()}.bin"
        f.write_bytes(body)
        monkeypatch.setattr(touch, attr, f)
        recorded[field] = hashlib.sha256(body).hexdigest()

    class _Cal:
        def key(self) -> str:
            return "cal:test"

    monkeypatch.setattr(touch, "_refit_cal", lambda: _Cal())
    recorded["cal_key"] = "cal:test"
    return recorded


def test_provenance_tripwire_passes_the_reviewed_substrate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Bug caught: a tripwire that refuses regardless (the old test's all-zero
    # block passed on ANY refusal — on a clean clone, the missing-artifact one).
    recorded = _tripwire_substrate(tmp_path, monkeypatch)
    assert touch.provenance_tripwire(recorded) is None


@pytest.mark.parametrize("field", _TRIPWIRE_FIELDS)
def test_provenance_tripwire_checks_EVERY_field(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    # The tripwire recomputes every content hash BEFORE the c2 file
    # opens; a mutated substrate refuses (owner rider: content-hash
    # asserted at touch entry against the gate-reviewed artifacts).
    # Bug caught: a tripwire that checks only SOME fields — one wrong field,
    # the rest correct, must refuse naming that field. (Hygiene: the old
    # all-zero block could not tell, and it hashed the real 1.4 GB store.)
    recorded = _tripwire_substrate(tmp_path, monkeypatch)
    recorded[field] = "0" * 64
    with pytest.raises(
        SystemExit, match=rf"PROVENANCE-TRIPWIRE defect-STOP \({field}\)"
    ):
        touch.provenance_tripwire(recorded)


def test_migrate_defect_run_moves_acceptance_under_dated_key() -> None:
    # The corrected path preserves the defective read under a dated key
    # (misfire protocol) — never deletes it.
    # Bug caught: a corrected run silently discarding the defective
    # evidence instead of preserving it.
    ev: dict[str, Any] = {"phase13": {"miost": {"c2_acceptance": {"mu": 0.9}}}}
    assert touch.migrate_defect_run(ev, "20260721") is True
    m = ev["phase13"]["miost"]
    assert "c2_acceptance" not in m
    assert m["c2_defect_run_20260721"] == {"mu": 0.9}
    assert touch.migrate_defect_run(ev, "20260721") is False


def test_refit_cal_key_roundtrip_against_recorded_evidence() -> None:
    # The touch's s(x) is reconstructed from the recorded refit evidence;
    # the reconstructed key must equal the recorded cal_key byte-for-byte.
    # Bug caught: a serialization drift between the harness's winner
    # field and the reconstruction (the touch would score under a
    # different calibration than the gate reviewed).
    results = json.loads(
        Path(
            "data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json"
        ).read_text()
    )
    wf = results["phase13"]["miost"]["refit"]["winner_field"]
    cal = touch._refit_cal()
    assert cal.key() == wf["cal_key"]
