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


def test_runner_c2_touch_stub_refuses() -> None:
    """Until Task 8, --c2-touch must refuse loudly; no c2 open exists in the runner."""
    from tests.helpers import load_script

    runner = load_script("phase12_miost6_run")
    with pytest.raises(SystemExit, match="not implemented until T8"):
        runner.c2_touch_main()
