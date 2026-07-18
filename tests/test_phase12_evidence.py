"""Phase-12 evidence schema + runner isolation pins.

Bugs caught: writer clobbering sibling evidence blocks (the P0-1 legacy
failure mode — a whole-dict overwrite would erase the signed
phase8.c2_acceptance); provenance drift between writer and touch-asserter
(shared-module-by-construction); the runner silently binding the PHASE-8
results file; a seed root that jq-float-rounds (int equality only).
"""

from __future__ import annotations

import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from sverdrup.validation.phase12_evidence import (
    DEV_SMOKE_PREFIX,
    MIOST6_KEYS,
    MIOST6_PREFIX,
    PROVENANCE_HASH_FIELDS,
    assert_provenance_matches,
    provenance_block,
    sha256_file,
    write_pack_entry,
)

RUNNER = Path("scripts/phase12_miost6_run.py")


def test_schema_key_layout_exact() -> None:
    assert MIOST6_PREFIX == "phase12.miost6"
    assert DEV_SMOKE_PREFIX == "phase12_dev_smoke"
    assert MIOST6_KEYS == (
        "geometry",
        "telemetry",
        "budget",
        "report_rows",
        "deltas",
        "tier3",
        "provenance",
        "c2_acceptance",
    )


def test_provenance_hash_fields_exact() -> None:
    """The tripwire recomputes EXACTLY these six — writer and asserter agree."""
    assert PROVENANCE_HASH_FIELDS == (
        "mean_maps_sha256",
        "var_maps_sha256",
        "member_store_sha256",
        "cal_key",
        "scope_cfg_sha256",
        "geometry_artifact_sha256",
    )


def test_write_pack_entry_preserves_siblings(tmp_path: Path) -> None:
    """Named anti-clobber test (spec §5 / fork-d pin).

    Writing phase12.miost6.telemetry into a store already holding
    phase12.miost6.geometry AND a foreign phase8.c2_acceptance leaves both
    intact: the write is a read-modify-write of ONE leaf key.
    """
    store = tmp_path / "results.json"
    store.write_text(
        json.dumps(
            {
                "phase8": {"c2_acceptance": {"signed": True, "mu": 0.8572611954190728}},
                "phase12": {"miost6": {"geometry": {"sha256": "abc"}}},
            }
        )
    )
    write_pack_entry(store, "phase12.miost6.telemetry", {"wall_s": 1.5})

    after = json.loads(store.read_text())
    assert after["phase8"]["c2_acceptance"] == {
        "signed": True,
        "mu": 0.8572611954190728,
    }
    assert after["phase12"]["miost6"]["geometry"] == {"sha256": "abc"}
    assert after["phase12"]["miost6"]["telemetry"] == {"wall_s": 1.5}


def test_write_pack_entry_creates_store(tmp_path: Path) -> None:
    store = tmp_path / "new.json"
    write_pack_entry(store, "phase12.miost6.budget", {"n_obs_smoke": 3})
    assert json.loads(store.read_text()) == {
        "phase12": {"miost6": {"budget": {"n_obs_smoke": 3}}}
    }


def _blocks(tmp_path: Path) -> tuple[dict[str, str], dict[str, str]]:
    files = {}
    for name in ("mean.nc", "var.nc", "members.npz", "scope.json", "geom.json"):
        p = tmp_path / name
        p.write_text(name)
        files[name] = p

    def _block() -> dict[str, str]:
        return provenance_block(
            mean_maps=files["mean.nc"],
            var_maps=files["var.nc"],
            member_store=files["members.npz"],
            cal_key="poly:phase8",
            scope_cfg=files["scope.json"],
            geometry_artifact=files["geom.json"],
        )

    return _block(), _block()


def test_provenance_roundtrip_matches(tmp_path: Path) -> None:
    recorded, recomputed = _blocks(tmp_path)
    assert set(recorded) == set(PROVENANCE_HASH_FIELDS)
    assert recorded["mean_maps_sha256"] == sha256_file(tmp_path / "mean.nc")
    assert_provenance_matches(recorded, recomputed)  # no raise


def test_provenance_mismatch_refuses_naming_field(tmp_path: Path) -> None:
    """A tampered member store must refuse BEFORE any c2 open — never re-solve."""
    recorded, recomputed = _blocks(tmp_path)
    recomputed["member_store_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="member_store_sha256"):
        assert_provenance_matches(recorded, recomputed)


def test_provenance_missing_field_refuses(tmp_path: Path) -> None:
    recorded, recomputed = _blocks(tmp_path)
    del recorded["cal_key"]
    with pytest.raises(ValueError, match="cal_key"):
        assert_provenance_matches(recorded, recomputed)


def test_runner_path_constants_isolated() -> None:
    """The runner NEVER names the phase-8 results file; its store is phase12's."""
    text = RUNNER.read_text()
    assert "stage_miost_gate_results.json" not in text
    assert "phase12_miost6_results.json" in text


def test_seed_root_literal_exact_int() -> None:
    """spec §1: the member seed root as an EXACT INT (jq float-rounds it)."""
    from sverdrup.core.seeding import derive_seed

    root = derive_seed("miost", "stage-b-winner", "members", 0)
    assert isinstance(root, int)
    assert root == 4836134738817689931


def _runner() -> ModuleType:
    from tests.helpers import load_script

    return load_script("phase12_miost6_run")


# ---------------------------------------------------------------------------
# T8 touch mechanics (pure — no data; owner ceremony verbatim)
# ---------------------------------------------------------------------------


def test_check_authorized_exact_one_only() -> None:
    """Any value but exact-string '1' refuses with no data loaded."""
    r = _runner()
    r.check_authorized({"SVERDRUP_MIOST_C2": "1"})  # no raise
    for bad in (
        {},
        {"SVERDRUP_MIOST_C2": "0"},
        {"SVERDRUP_MIOST_C2": " 1"},
        {"SVERDRUP_MIOST_C2": "true"},
        {"SVERDRUP_MIOST_C2": "1 "},
    ):
        with pytest.raises(SystemExit, match="SVERDRUP_MIOST_C2"):
            r.check_authorized(bad)


def _mk_evidence(acceptance: bool, defect: bool) -> dict[str, Any]:
    m: dict[str, Any] = {}
    if acceptance:
        m["c2_acceptance"] = {"mu": 0.85}
    if defect:
        m["c2_defect_run_20260718"] = {"mu": 0.85, "defect": "x"}
    return {"phase12": {"miost6": m}}


def test_touch_protocol_matrix() -> None:
    """The six-row one-touch/corrected matrix (phase8 owner-rider-3 template)."""
    r = _runner()
    flag = {"SVERDRUP_MIOST_C2_CORRECTED": "1"}

    # unset + acceptance -> refuse (one-touch spent)
    with pytest.raises(SystemExit, match="already"):
        r.check_touch_protocol(_mk_evidence(True, False), {})
    # unset + no acceptance -> PROCEED (this is the FIRST touch)
    r.check_touch_protocol(_mk_evidence(False, False), {})
    # set + acceptance + no defect -> proceed (migrate then re-evaluate)
    r.check_touch_protocol(_mk_evidence(True, False), flag)
    # set + no acceptance + defect -> proceed (resume)
    r.check_touch_protocol(_mk_evidence(False, True), flag)
    # set + acceptance + defect -> refuse (third invocation)
    with pytest.raises(SystemExit, match="third"):
        r.check_touch_protocol(_mk_evidence(True, True), flag)
    # set + neither -> refuse (flag invalid without a defect to correct)
    with pytest.raises(SystemExit, match="invalid"):
        r.check_touch_protocol(_mk_evidence(False, False), flag)


def test_migrate_defect_run_renames_and_is_idempotent() -> None:
    r = _runner()
    ev = _mk_evidence(True, False)
    assert r.migrate_defect_run(ev, "20260718") is True
    m = ev["phase12"]["miost6"]
    assert "c2_acceptance" not in m
    blk = m["c2_defect_run_20260718"]
    assert blk["mu"] == 0.85
    assert "defect" in blk
    assert r.migrate_defect_run(ev, "20260718") is False  # no-op on resume


def test_window_tripwire_refuses_wrong_count_and_partial_span() -> None:
    import numpy as np

    r = _runner()
    full = np.arange("2017-01-01", "2018-01-01", dtype="datetime64[D]").astype(
        "datetime64[ns]"
    )
    rec = r.window_tripwire(44_844, full)  # count pinned; full span
    assert rec["passed"] is True
    with pytest.raises(SystemExit, match="n_points"):
        r.window_tripwire(44_843, full)
    partial = full[:30]  # January only
    with pytest.raises(SystemExit, match="span"):
        r.window_tripwire(44_844, partial)


def test_provenance_tripwire_refuses_tampered_store(tmp_path: Path) -> None:
    """Tampered member store refuses BEFORE any c2 open; never a re-solve."""
    r = _runner()
    files = {}
    for name in ("mean.nc", "var.nc", "members.npz", "scope.json", "geom.json"):
        p = tmp_path / name
        p.write_text(name)
        files[name] = p
    recorded = provenance_block(
        mean_maps=files["mean.nc"],
        var_maps=files["var.nc"],
        member_store=files["members.npz"],
        cal_key="poly:key",
        scope_cfg=files["scope.json"],
        geometry_artifact=files["geom.json"],
    )
    # untampered: passes
    r.provenance_tripwire(
        recorded,
        mean_maps=files["mean.nc"],
        var_maps=files["var.nc"],
        member_store=files["members.npz"],
        cal_key="poly:key",
        scope_cfg=files["scope.json"],
        geometry_artifact=files["geom.json"],
    )
    files["members.npz"].write_text("TAMPERED")
    with pytest.raises(ValueError, match="member_store_sha256"):
        r.provenance_tripwire(
            recorded,
            mean_maps=files["mean.nc"],
            var_maps=files["var.nc"],
            member_store=files["members.npz"],
            cal_key="poly:key",
            scope_cfg=files["scope.json"],
            geometry_artifact=files["geom.json"],
        )
