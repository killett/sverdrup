"""Phase-12 declared-null scope config: schema, refusals, no-default guarantee.

Bugs caught: a loader that treats a MISSING val_track_path as declared-null
(absence must be a schema error, not the production state); a silent
``.get("val_track_path", default)`` anywhere in src/scripts that would
j3-bind a validation-flavored path; a mission set that drifts from the six
assimilated missions (or admits c2); validation-flavored entry points that
proceed instead of refusing with the pinned reason.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from sverdrup.validation.phase12_config import (
    MIOST6_MISSIONS,
    NO_VALIDATION_REFUSAL,
    Phase12ConfigError,
    load_phase12_scope,
    require_validation_track,
)

FIXTURE = Path("tests/validation/fixtures/phase12_miost6_scope.json")


def _raw() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text())


def _write(tmp_path: Path, raw: dict[str, Any]) -> Path:
    p = tmp_path / "scope.json"
    p.write_text(json.dumps(raw))
    return p


def test_fixture_loads_with_declared_roles() -> None:
    """Happy path: the committed fixture validates and carries the six missions."""
    scope = load_phase12_scope(FIXTURE)
    assert len(scope.mapping_obs_paths) == 6
    codes = {
        p.name.split("_phy_")[0].rsplit("_", 1)[-1] for p in scope.mapping_obs_paths
    }
    assert codes == set(MIOST6_MISSIONS)
    assert scope.no_validation_reason == "j3-assimilated"
    assert scope.window_id == "phase12-miost6"
    assert scope.smoke_days == tuple(float(d) for d in range(60, 72))
    assert scope.mean_map_out.name == "phase12_miost6_mean_maps.nc"


def test_missing_val_track_path_key_is_schema_error(tmp_path: Path) -> None:
    """Absence != declared null: a cfg without the key must refuse, naming it."""
    raw = _raw()
    del raw["val_track_path"]
    with pytest.raises(Phase12ConfigError, match="val_track_path"):
        load_phase12_scope(_write(tmp_path, raw))


def test_non_null_val_track_path_refuses_with_pinned_text(tmp_path: Path) -> None:
    raw = _raw()
    raw["val_track_path"] = "data/2021a_ssh_mapping_ose/dc_obs/some_track.nc"
    with pytest.raises(Phase12ConfigError) as exc:
        load_phase12_scope(_write(tmp_path, raw))
    assert str(exc.value) == NO_VALIDATION_REFUSAL


def test_non_null_validation_mission_refuses(tmp_path: Path) -> None:
    raw = _raw()
    raw["validation_mission"] = "j3"
    with pytest.raises(Phase12ConfigError) as exc:
        load_phase12_scope(_write(tmp_path, raw))
    assert str(exc.value) == NO_VALIDATION_REFUSAL


def test_wrong_no_validation_reason_refuses(tmp_path: Path) -> None:
    raw = _raw()
    raw["no_validation_reason"] = "because"
    with pytest.raises(Phase12ConfigError, match="j3-assimilated"):
        load_phase12_scope(_write(tmp_path, raw))


def test_five_mission_set_refuses(tmp_path: Path) -> None:
    """Dropping j3 (the five-mission set) must refuse — this cfg IS the six-mission product."""
    raw = _raw()
    raw["mapping_obs_paths"] = [p for p in raw["mapping_obs_paths"] if "_j3_" not in p]
    with pytest.raises(Phase12ConfigError, match="mapping missions"):
        load_phase12_scope(_write(tmp_path, raw))


def test_c2_in_mapping_paths_refuses(tmp_path: Path) -> None:
    """The withheld-leak guard fires inside _mission_code before set comparison."""
    raw = _raw()
    raw["mapping_obs_paths"][0] = raw["c2_track_path"]
    with pytest.raises(ValueError):
        load_phase12_scope(_write(tmp_path, raw))


def test_require_validation_track_refuses_with_pinned_text() -> None:
    scope = load_phase12_scope(FIXTURE)
    with pytest.raises(Phase12ConfigError) as exc:
        require_validation_track(scope)
    assert str(exc.value) == NO_VALIDATION_REFUSAL


def test_no_default_for_val_track_path() -> None:
    """A .get('val_track_path', default) would silently j3-bind — forbidden."""
    import re

    pat = re.compile(r"\.get\(\s*[\"']val_track_path[\"']\s*,")
    hits = [
        f"{p}"
        for root in ("src", "scripts")
        for p in Path(root).rglob("*.py")
        if pat.search(p.read_text())
    ]
    assert hits == []


def test_harness_load_track_refuses_phase12_cfg(tmp_path: Path) -> None:
    """The s-fit harness handed the phase12 cfg raises before binding any track.

    harness.load_track does ``Path(cfg["val_track_path"])`` — null must blow
    up (TypeError) BEFORE any map or track file is opened; the dummy paths
    below would themselves error loudly if the code got that far.
    """
    from sverdrup.application.calibration.harness import (
        ProductDescriptor,
        load_track,
    )

    desc = ProductDescriptor(
        product_id="miost",
        mean_maps=tmp_path / "absent_mean.nc",
        var_maps=tmp_path / "absent_var.nc",
        scope_config=FIXTURE,
        mask_artifact=tmp_path / "absent_mask.json",
        evidence_key="phase12.miost6.never_written",
        field_artifact=tmp_path / "absent_field.json",
        fold_seed_tuple=("miost", "phase12", "s-folds"),
    )
    with pytest.raises((TypeError, KeyError)):
        load_track(desc, scope="dev")


_GEOMETRY = Path("data/2021a_ssh_mapping_ose/ours/phase12_orbit_geometry_miost6.json")


@pytest.mark.skipif(not _GEOMETRY.exists(), reason="phase12 geometry artifact absent")
def test_geometry_artifact_has_j3_repeat_classification() -> None:
    """The six-mission artifact carries j3's first classification as repeat.

    Bug caught: a derivation that silently dropped j3 (five-mission set), or a
    j3 record whose classifier landed drifting/gap without the Task-4 STOP.
    """
    art = json.loads(_GEOMETRY.read_text())
    assert sorted(art["missions"]) == ["alg", "h2g", "j2g", "j2n", "j3", "s3a"]
    for family in ("asc", "desc"):
        rec = art["missions"]["j3"][family]
        assert rec["orbit_class"] == "repeat"
        assert rec["classifier_ratio"] < 0.14  # below the RATIO_GAP lower edge
        assert rec["cluster_size_median"] > 2  # repeat-side corroborating axis


def test_five_mission_files_byte_untouched() -> None:
    """This phase never edits the five-mission scope fixture or the input adapter."""
    import subprocess

    out = subprocess.run(
        [
            "git",
            "diff",
            "--stat",
            "tests/validation/fixtures/stage_a_scope.json",
            "src/sverdrup/validation/input_adapter.py",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert out.stdout.strip() == ""
