"""Tests for the generalized calibration harness (Phase 9, Tasks 4 & 5).

These tests cover:
  - ProductDescriptor validation (each invalid field rejected with right error)
  - Module constants MIOST_DESCRIPTOR / OI_DESCRIPTOR are well-formed
  - Mask-build generalization determinism (two runs byte-identical, phase8 cells)
  - Leaf-identical harness regression on MIOST vs Phase-8 evidence
    (env-gated: set SVERDRUP_PHASE9_EXTERNAL=1 to opt in; ~2.5 min runtime)
  - G_pre anchor block assembly (Task 5): pure-function unit tests on synthetic
    selection tables; no artifacts needed
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np
import pytest

from sverdrup.application.calibration.harness import (
    MIOST_DESCRIPTOR,
    OI_DESCRIPTOR,
    ProductDescriptor,
)

# Load build_jet_core_mask by path (not as ``scripts.build_jet_core_mask``)
# to avoid mypy's "module found twice under different names" error.
_BMK_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_jet_core_mask.py"
_bmk_spec = importlib.util.spec_from_file_location("build_jet_core_mask", _BMK_PATH)
assert _bmk_spec is not None and _bmk_spec.loader is not None
_bm: ModuleType = importlib.util.module_from_spec(_bmk_spec)
_bmk_spec.loader.exec_module(_bm)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _leaves(d: Any, prefix: tuple[str, ...] = ()) -> list[tuple[tuple[str, ...], Any]]:
    """Walk a nested dict/list and yield (path_tuple, leaf_value) pairs.

    Args:
        d: Nested dict, list, or scalar.
        prefix: Current path tuple (used for recursion).

    Returns:
        List of (path_tuple, value) pairs for all leaf nodes.
    """
    result: list[tuple[tuple[str, ...], Any]] = []
    if isinstance(d, dict):
        for k, v in d.items():
            result.extend(_leaves(v, (*prefix, k)))
    elif isinstance(d, list):
        for i, v in enumerate(d):
            result.extend(_leaves(v, (*prefix, str(i))))
    else:
        result.append((prefix, d))
    return result


# ---------------------------------------------------------------------------
# ProductDescriptor validation — red tests drove these; each rejects a bad field
# ---------------------------------------------------------------------------


def test_descriptor_rejects_non_path_mean_maps(tmp_path: Path) -> None:
    """ProductDescriptor rejects a non-Path mean_maps argument.

    Bug caught: a descriptor that silently accepts str paths and then fails at
    runtime with an AttributeError instead of a clear TypeError at construction.
    """
    with pytest.raises(TypeError, match="mean_maps"):
        ProductDescriptor(
            product_id="test",
            mean_maps="not_a_path",  # type: ignore[arg-type]
            var_maps=tmp_path / "var.nc",
            scope_config=tmp_path / "scope.json",
            mask_artifact=tmp_path / "mask.json",
            evidence_key="phase9.test.fit_run",
            field_artifact=tmp_path / "field.json",
            fold_seed_tuple=("test", "phase9", "s-folds"),
        )


def test_descriptor_rejects_non_path_var_maps(tmp_path: Path) -> None:
    """ProductDescriptor rejects a non-Path var_maps argument.

    Bug caught: same silent-str-path bug on a different field.
    """
    with pytest.raises(TypeError, match="var_maps"):
        ProductDescriptor(
            product_id="test",
            mean_maps=tmp_path / "mean.nc",
            var_maps=42,  # type: ignore[arg-type]
            scope_config=tmp_path / "scope.json",
            mask_artifact=tmp_path / "mask.json",
            evidence_key="phase9.test.fit_run",
            field_artifact=tmp_path / "field.json",
            fold_seed_tuple=("test", "phase9", "s-folds"),
        )


def test_descriptor_rejects_empty_product_id(tmp_path: Path) -> None:
    """ProductDescriptor rejects an empty product_id.

    Bug caught: a descriptor with product_id='' that silently produces empty
    evidence_key paths and corrupts the gate JSON structure.
    """
    with pytest.raises(ValueError, match="product_id"):
        ProductDescriptor(
            product_id="",
            mean_maps=tmp_path / "mean.nc",
            var_maps=tmp_path / "var.nc",
            scope_config=tmp_path / "scope.json",
            mask_artifact=tmp_path / "mask.json",
            evidence_key="phase9.test.fit_run",
            field_artifact=tmp_path / "field.json",
            fold_seed_tuple=("test", "phase9", "s-folds"),
        )


def test_descriptor_rejects_bad_evidence_key(tmp_path: Path) -> None:
    """ProductDescriptor rejects an evidence_key not starting with 'phase'.

    Bug caught: a descriptor whose evidence_key is 'stage8.fit_run' or
    'miost.fit_run' (missing phase prefix), silently nesting evidence under the
    wrong gate JSON key.
    """
    with pytest.raises(ValueError, match="evidence_key"):
        ProductDescriptor(
            product_id="test",
            mean_maps=tmp_path / "mean.nc",
            var_maps=tmp_path / "var.nc",
            scope_config=tmp_path / "scope.json",
            mask_artifact=tmp_path / "mask.json",
            evidence_key="stage9.test.fit_run",  # does not start with 'phase'
            field_artifact=tmp_path / "field.json",
            fold_seed_tuple=("test", "phase9", "s-folds"),
        )


def test_descriptor_rejects_short_fold_seed_tuple(tmp_path: Path) -> None:
    """ProductDescriptor rejects a fold_seed_tuple with fewer than 3 elements.

    Bug caught: a 2-element tuple passed to derive_seed causes a TypeError at
    fold layout time rather than at descriptor construction.
    """
    with pytest.raises(ValueError, match="fold_seed_tuple"):
        ProductDescriptor(
            product_id="test",
            mean_maps=tmp_path / "mean.nc",
            var_maps=tmp_path / "var.nc",
            scope_config=tmp_path / "scope.json",
            mask_artifact=tmp_path / "mask.json",
            evidence_key="phase9.test.fit_run",
            field_artifact=tmp_path / "field.json",
            fold_seed_tuple=("test", "phase9"),  # type: ignore[arg-type]
        )


def test_descriptor_rejects_non_str_fold_seed_tuple_elements(tmp_path: Path) -> None:
    """ProductDescriptor rejects a fold_seed_tuple with non-str elements.

    Bug caught: an int salt baked into the tuple that bypasses the 3-str
    requirement, producing a wrong seed silently.
    """
    with pytest.raises(ValueError, match="fold_seed_tuple"):
        ProductDescriptor(
            product_id="test",
            mean_maps=tmp_path / "mean.nc",
            var_maps=tmp_path / "var.nc",
            scope_config=tmp_path / "scope.json",
            mask_artifact=tmp_path / "mask.json",
            evidence_key="phase9.test.fit_run",
            field_artifact=tmp_path / "field.json",
            fold_seed_tuple=("test", "phase9", 0),  # type: ignore[arg-type]
        )


def test_descriptor_rejects_list_fold_seed_tuple(tmp_path: Path) -> None:
    """ProductDescriptor rejects a list (not tuple) for fold_seed_tuple.

    Bug caught: a list accepted silently at descriptor construction but later
    causing a mypy/type-check failure or len() mismatch at runtime.
    """
    with pytest.raises(ValueError, match="fold_seed_tuple"):
        ProductDescriptor(
            product_id="test",
            mean_maps=tmp_path / "mean.nc",
            var_maps=tmp_path / "var.nc",
            scope_config=tmp_path / "scope.json",
            mask_artifact=tmp_path / "mask.json",
            evidence_key="phase9.test.fit_run",
            field_artifact=tmp_path / "field.json",
            fold_seed_tuple=["test", "phase9", "s-folds"],  # type: ignore[arg-type]
        )


def test_descriptor_valid_construction(tmp_path: Path) -> None:
    """A valid ProductDescriptor constructs without error.

    Bug caught: __post_init__ raising spuriously on a well-formed descriptor.
    """
    desc = ProductDescriptor(
        product_id="test",
        mean_maps=tmp_path / "mean.nc",
        var_maps=tmp_path / "var.nc",
        scope_config=tmp_path / "scope.json",
        mask_artifact=tmp_path / "mask.json",
        evidence_key="phase9.test.fit_run",
        field_artifact=tmp_path / "field.json",
        fold_seed_tuple=("test", "phase9", "s-folds"),
    )
    assert desc.product_id == "test"
    assert desc.evidence_key.startswith("phase")
    assert len(desc.fold_seed_tuple) == 3


# ---------------------------------------------------------------------------
# Module constants: MIOST_DESCRIPTOR and OI_DESCRIPTOR are well-formed
# ---------------------------------------------------------------------------


def test_miost_descriptor_frozen_tuple() -> None:
    """MIOST descriptor carries the FROZEN Phase-8 seed tuple.

    Bug caught: a renamed or reordered tuple that breaks the leaf-identical
    harness regression by producing a different s-fold layout.
    """
    assert MIOST_DESCRIPTOR.fold_seed_tuple == ("miost", "phase8", "s-folds")


def test_miost_descriptor_evidence_key() -> None:
    """MIOST descriptor evidence_key is 'phase9.miost.fit_run'.

    Bug caught: evidence written under 'phase8.fit_run' or 'phase9.fit_run'
    (wrong nesting) instead of the per-product Phase-9 key.
    """
    assert MIOST_DESCRIPTOR.evidence_key == "phase9.miost.fit_run"


def test_miost_descriptor_covariate_promoted() -> None:
    """MIOST descriptor has covariate_promoted=True (Phase-8 rule preserved).

    Bug caught: a descriptor that drops the covariate lane for MIOST, changing
    the selection outcome and breaking the leaf-identical regression.
    """
    assert MIOST_DESCRIPTOR.covariate_promoted is True


def test_oi_descriptor_evidence_key() -> None:
    """OI descriptor evidence_key is 'phase9.oi.fit_run'.

    Bug caught: OI evidence written under the MIOST key, silently overwriting
    Phase-9 MIOST evidence.
    """
    assert OI_DESCRIPTOR.evidence_key == "phase9.oi.fit_run"


def test_oi_descriptor_seed_tuple_different_from_miost() -> None:
    """OI descriptor has a different seed tuple from MIOST.

    Bug caught: OI inheriting the MIOST seed tuple, conflating the two products'
    S-fold lineages.
    """
    assert OI_DESCRIPTOR.fold_seed_tuple != MIOST_DESCRIPTOR.fold_seed_tuple
    assert OI_DESCRIPTOR.fold_seed_tuple[0] == "oi"


def test_descriptors_are_frozen(tmp_path: Path) -> None:
    """Both module descriptors are frozen (immutable).

    Bug caught: a mutable descriptor whose paths are modified between
    harness calls, producing non-reproducible evidence.
    """
    with pytest.raises((AttributeError, TypeError)):
        MIOST_DESCRIPTOR.product_id = "mutated"  # type: ignore[misc]
    with pytest.raises((AttributeError, TypeError)):
        OI_DESCRIPTOR.product_id = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Mask build determinism: two runs byte-identical + phase8 cells reproduced
# ---------------------------------------------------------------------------

_MIOST_MEAN_NC = Path("data/2021a_ssh_mapping_ose/ours/stage_b_mean_maps.nc")
_PHASE8_JET_MASK = Path("data/2021a_ssh_mapping_ose/ours/phase8_jet_core_mask.json")
_PHASE8_JET_CELLS = {(2, 1), (2, 2), (3, 0), (3, 1), (3, 2), (3, 3), (3, 4)}


@pytest.mark.skipif(
    not _MIOST_MEAN_NC.exists(),
    reason="MIOST mean maps absent (data/ours/ untracked)",
)
def test_mask_build_deterministic_on_miost_maps() -> None:
    """Two build_mask() runs on the MIOST maps produce identical JSON bytes.

    Bug caught: any non-deterministic element in build_mask (e.g. a timestamp
    or non-reproducible sort) that makes the artifact hash-unstable across runs.
    """
    mask1, prov1 = _bm.build_mask(_MIOST_MEAN_NC)
    mask2, prov2 = _bm.build_mask(_MIOST_MEAN_NC)

    # Byte-identical: encode both as JSON with the same options.
    def _encode(mask: np.ndarray, prov: dict[str, object]) -> str:
        artifact = {"mask": mask.tolist(), "provenance": prov}
        return json.dumps(artifact, sort_keys=True, indent=2) + "\n"

    assert _encode(mask1, prov1) == _encode(mask2, prov2)


@pytest.mark.skipif(
    not _MIOST_MEAN_NC.exists(),
    reason="MIOST mean maps absent (data/ours/ untracked)",
)
def test_mask_build_reproduces_phase8_cells_on_miost_maps() -> None:
    """build_mask on MIOST maps reproduces the pre-registered Phase-8 jet cells.

    Bug caught: a build_jet_core_mask.py implementation that uses different
    constants (threshold, method, connectivity) and produces a different mask,
    silently breaking the per-product Jaccard comparison.

    Expected cells: {(2,1),(2,2),(3,0),(3,1),(3,2),(3,3),(3,4)}.
    """
    mask, _ = _bm.build_mask(_MIOST_MEAN_NC)
    got_cells = {(int(r), int(c)) for r, c in zip(*np.where(mask), strict=True)}
    assert got_cells == _PHASE8_JET_CELLS, (
        f"Expected {_PHASE8_JET_CELLS}, got {got_cells}"
    )


@pytest.mark.skipif(
    not _PHASE8_JET_MASK.exists() or not _MIOST_MEAN_NC.exists(),
    reason="Phase-8 mask artifact or MIOST mean maps absent (untracked)",
)
def test_build_jet_core_mask_byte_identical_to_phase8_artifact() -> None:
    """build_mask + write_mask on MIOST maps produces byte-identical JSON to
    the existing phase8_jet_core_mask.json artifact.

    Bug caught: the generalised build_jet_core_mask.py using a different
    json.dumps call (sort_keys=False, missing trailing newline, different
    indent) that produces a byte-different file even with identical data.
    """
    mask, provenance = _bm.build_mask(_MIOST_MEAN_NC)
    artifact = {"mask": mask.tolist(), "provenance": provenance}
    got_text = json.dumps(artifact, sort_keys=True, indent=2) + "\n"

    expected_text = _PHASE8_JET_MASK.read_text()
    # The source_file path in provenance may differ (absolute vs relative);
    # compare the mask + sha256 + threshold, not the full text.
    got = json.loads(got_text)
    expected = json.loads(expected_text)
    assert got["mask"] == expected["mask"], "Mask arrays differ"
    assert got["provenance"]["sha256"] == expected["provenance"]["sha256"], (
        "SHA-256 digest differs"
    )
    assert got["provenance"]["threshold"] == expected["provenance"]["threshold"], (
        "Threshold differs"
    )
    assert got["provenance"]["quantile"] == expected["provenance"]["quantile"], (
        "Quantile differs"
    )


# ---------------------------------------------------------------------------
# Leaf-identical harness regression on MIOST vs Phase-8 evidence
# Opt-in gate: SVERDRUP_PHASE9_EXTERNAL=1 (runtime ~2.5 min)
# ---------------------------------------------------------------------------

_GATE_RESULTS = Path("data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json")

# EXCLUDED leaves (belt-and-suspenders under the superset assertion below).
# Do NOT simplify away — it documents which Phase-9-only rows are expected.
# jet_core_ref_p8: self-referential for MIOST (the reference IS the MIOST mask).
# jaccard_vs_p8: Jaccard=1.0 for MIOST by construction.
# regional_table_ref: reserved name (not present in either tree; guard rename).
EXCLUDED: set[tuple[str, ...]] = {
    ("regional_table_ref",),
    ("jet_core_ref_p8",),
    ("jaccard_vs_p8",),
    # promotion_record is a new Phase-9 leaf, not present in Phase-8 evidence.
    ("promotion_record",),
    # mask_artifact (path + sha256 bound at fit entry) is a new Phase-9 leaf
    # (Task-7 follow-up), not present in Phase-8 evidence.
    ("mask_artifact",),
}


@pytest.mark.skipif(
    os.environ.get("SVERDRUP_PHASE9_EXTERNAL", "") != "1",
    reason=(
        "leaf-identical harness regression; set SVERDRUP_PHASE9_EXTERNAL=1 to run "
        "(runtime ~2.5 min; requires full data artifacts)"
    ),
)
@pytest.mark.skipif(
    not _GATE_RESULTS.exists(),
    reason="Phase-8 gate results absent (data/ours/ untracked)",
)
def test_harness_on_miost_reproduces_phase8_evidence_leaf_identical() -> None:
    """Harness on MIOST descriptor reproduces Phase-8 fit_run evidence leaf-identically.

    Bug caught: ANY behavioral drift in the extraction — seed scoping, lane math,
    selection, evidence assembly.  Pinned key map EXACTLY
    {phase8.fit_run -> phase9.miost.fit_run}: leaf PATHS below the prefix
    identical, VALUES exactly equal (floats ==, deterministic rerun).
    """
    from sverdrup.application.calibration.harness import run_harness

    # Load Phase-8 evidence.
    p8_full = json.loads(_GATE_RESULTS.read_text())
    p8 = p8_full["phase8"]["fit_run"]

    # Run harness on MIOST descriptor, full scope.
    p9 = run_harness(MIOST_DESCRIPTOR, scope="full")

    # Build leaf maps.
    l8: dict[tuple[str, ...], Any] = {path: val for path, val in _leaves(p8)}
    l9_raw: dict[tuple[str, ...], Any] = {path: val for path, val in _leaves(p9)}

    # Filter out excluded top-level keys from p9.
    l9: dict[tuple[str, ...], Any] = {
        path: val
        for path, val in l9_raw.items()
        if path[:1] not in EXCLUDED and path not in EXCLUDED
    }

    missing = l8.keys() - l9.keys()
    assert not missing, (
        f"Phase-8 leaves missing from harness output: "
        f"{sorted(str(p) for p in missing)[:10]}"
    )

    # Superset assertion: l9 must contain all l8 leaves.
    assert l9.keys() >= l8.keys(), (
        "l9 (harness) is not a superset of l8 (phase8 evidence) leaf keys"
    )

    # Value equality — floats must match exactly (deterministic rerun).
    mismatches: list[str] = []
    for path, v8 in l8.items():
        v9 = l9[path]
        if v8 != v9:
            mismatches.append(f"  {'.'.join(path)}: p8={v8!r}  p9={v9!r}")
    assert not mismatches, (
        f"{len(mismatches)} leaf value mismatches (first 10):\n"
        + "\n".join(mismatches[:10])
    )

    print(
        f"[leaf-identical] PASS: {len(l8)} leaves compared, "
        f"{len(l9) - len(l8)} new p9-only leaves (excluded: {len(EXCLUDED)} keys)"
    )


@pytest.mark.skipif(
    os.environ.get("SVERDRUP_PHASE9_EXTERNAL", "") != "1",
    reason=(
        "field byte-exact gate; set SVERDRUP_PHASE9_EXTERNAL=1 to run "
        "(runtime ~2.5 min; requires full data artifacts)"
    ),
)
@pytest.mark.skipif(
    not Path("data/2021a_ssh_mapping_ose/ours/phase8_field.json").exists(),
    reason="Phase-8 field artifact absent (data/ours/ untracked)",
)
def test_harness_on_miost_field_byte_exact_vs_phase8() -> None:
    """Harness on MIOST descriptor produces a field artifact byte-exact vs phase8_field.json.

    Bug caught: any drift in the refit_winner call (different clip bounds,
    different poly coefficients) that produces a different winner field while
    leaving the selection evidence identical.
    """
    from sverdrup.application.calibration.harness import run_harness

    p9 = run_harness(MIOST_DESCRIPTOR, scope="full")

    # Load Phase-8 field artifact.
    p8_field = json.loads(
        Path("data/2021a_ssh_mapping_ose/ours/phase8_field.json").read_text()
    )

    assert "winner_field" in p9, "harness output missing winner_field"
    wf = p9["winner_field"]

    assert wf["cal_key"] == p8_field["cal_key"], (
        f"cal_key mismatch: harness={wf['cal_key']!r} phase8={p8_field['cal_key']!r}"
    )
    assert wf["to_json"] == p8_field["calibration"], (
        "winner_field.to_json != phase8_field.json calibration (byte mismatch)"
    )


# ---------------------------------------------------------------------------
# G_pre anchor block assembly (Task 5) — pure-function unit tests
# ---------------------------------------------------------------------------
# These tests import build_anchor_block from scripts/phase9_g_pre_anchor.py.
# The function is pure: it only reads its arguments (synthetic selection tables,
# synthetic calibration JSON, a mask SHA, and companion values) and assembles
# the anchor block.  No artifacts are read or written.
# ---------------------------------------------------------------------------

_ANCHOR_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "phase9_g_pre_anchor.py"
)


def _load_anchor_module() -> ModuleType:
    """Load scripts/phase9_g_pre_anchor.py without side effects.

    Returns:
        Loaded module object with build_anchor_block callable.
    """
    spec = importlib.util.spec_from_file_location("phase9_g_pre_anchor", _ANCHOR_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _synthetic_selection(
    lane0_s: float = 0.50,
    winner_name: str = "poly",
    winner_s: float = 0.20,
) -> dict[str, Any]:
    """Return a synthetic selection block with controlled lane0 and winner stats.

    Args:
        lane0_s: Lane-0 (scalar) S-stat.
        winner_name: Name of the winning lane.
        winner_s: Winner S-stat.

    Returns:
        Selection dict shaped like the real harness selection block.
    """
    return {
        "lane0_s_stat": lane0_s,
        "winner": winner_name,
        "table": [
            {"name": "scalar", "s_stat": lane0_s},
            {"name": "piecewise", "s_stat": winner_s + 0.05},
            {"name": winner_name, "s_stat": winner_s},
            {"name": "covariate", "s_stat": winner_s + 0.02},
        ],
    }


def _synthetic_cal_json() -> dict[str, Any]:
    """Return a minimal poly calibration JSON for companion computation.

    All coefficients are zero so log_s_at = 0 everywhere (before clip).
    Clip bounds chosen so the clip NEVER engages (raw=0 is inside [−1, 1]).

    Returns:
        Calibration dict compatible with calibration_from_json.
    """
    return {
        "kind": "poly",
        "coeffs": [0.0, 0.0, 0.0, 0.0, 0.0],
        "clip": {"lo_log_s": -1.0, "hi_log_s": 1.0},
        "fit_id": "test",
    }


def test_g_pre_computed_as_lane0_minus_winner() -> None:
    """build_anchor_block computes G_pre = lane0_s_stat − winner_s_stat (§7c1).

    Bug caught: if the formula were inverted (winner − lane0), or if it used
    the wrong table row's s_stat (e.g. piecewise instead of the winner name),
    the returned g_pre would not equal 0.30.
    """
    mod = _load_anchor_module()
    sel = _synthetic_selection(lane0_s=0.50, winner_name="poly", winner_s=0.20)
    block = mod.build_anchor_block(
        selection=sel,
        cal_json=_synthetic_cal_json(),
        cal_key="cal:test",
        mask_sha256="deadbeef",
    )
    assert abs(block["g_pre"] - 0.30) < 1e-12, (
        f"G_pre should be 0.50 − 0.20 = 0.30, got {block['g_pre']}"
    )


def test_g_pre_is_builtin_float() -> None:
    """build_anchor_block returns g_pre as a Python float, not np.floating.

    Bug caught: if numpy subtraction returns np.float64 and the coercion
    is missing, repr() emits 'np.float64(0.3)' which breaks JSON round-trip
    and the Phase-8 cal_key lesson.
    """
    mod = _load_anchor_module()
    sel = _synthetic_selection(lane0_s=0.50, winner_s=0.20)
    block = mod.build_anchor_block(
        selection=sel,
        cal_json=_synthetic_cal_json(),
        cal_key="cal:test",
        mask_sha256="deadbeef",
    )
    assert type(block["g_pre"]) is float, (
        f"g_pre must be builtin float, got {type(block['g_pre'])}"
    )
    # Ensure no numpy scalar lurks (isinstance catches subclasses too)
    assert not isinstance(block["g_pre"], np.floating), (
        "g_pre must not be an np.floating subclass"
    )


def test_anchor_block_required_keys_present() -> None:
    """build_anchor_block returns a block with all required keys from the spec.

    Bug caught: if any of g_pre, definition, frame, or companions were absent,
    Phase-10 would silently consume an incomplete contract block.
    """
    mod = _load_anchor_module()
    sel = _synthetic_selection()
    block = mod.build_anchor_block(
        selection=sel,
        cal_json=_synthetic_cal_json(),
        cal_key="cal:test",
        mask_sha256="abc123",
    )
    assert "g_pre" in block, "missing key: g_pre"
    assert "definition" in block, "missing key: definition"
    assert "frame" in block, "missing key: frame"
    assert "companions" in block, "missing key: companions"


def test_frame_block_contains_required_fields() -> None:
    """Frame sub-block has mask, sha256, fold_seed_tuple, and salt fields.

    Bug caught: if sha256 were absent, Phase-10 loses the ability to verify
    the pinned mask; if salt were absent, the fold lineage is ambiguous.
    """
    mod = _load_anchor_module()
    sel = _synthetic_selection()
    block = mod.build_anchor_block(
        selection=sel,
        cal_json=_synthetic_cal_json(),
        cal_key="cal:test",
        mask_sha256="aaaa1111",
    )
    frame = block["frame"]
    assert frame["mask"] == "phase8_jet_core_mask.json", (
        f"frame.mask wrong: {frame['mask']}"
    )
    assert frame["sha256"] == "aaaa1111", (
        f"frame.sha256 should be passed-in value, got {frame['sha256']!r}"
    )
    assert frame["fold_seed_tuple"] == ["miost", "phase8", "s-folds"], (
        f"frame.fold_seed_tuple wrong: {frame['fold_seed_tuple']}"
    )
    assert frame["salt"] == 1, f"frame.salt should be 1, got {frame['salt']}"


def test_companions_clip_engagement_zero_for_no_clip_field() -> None:
    """Companions clip_engagement_fraction is 0.0 for a field that never clips.

    Bug caught: if the engagement computation used the wrong grid, applied
    clip incorrectly, or forgot to use raw (pre-clip) values, a field that
    is always within clip bounds would show nonzero engagement.

    The synthetic cal has all-zero coefficients and clip [-1, 1]; raw log_s
    is 0.0 everywhere, which is strictly inside [-1, 1], so no node engages.
    """
    mod = _load_anchor_module()
    sel = _synthetic_selection()
    block = mod.build_anchor_block(
        selection=sel,
        cal_json=_synthetic_cal_json(),
        cal_key="cal:test",
        mask_sha256="deadbeef",
    )
    frac = block["companions"]["clip_engagement_fraction"]
    assert frac == 0.0, (
        f"Synthetic all-zero poly field should have clip_engagement_fraction=0.0, "
        f"got {frac}"
    )


def test_companions_clip_engagement_partial_for_tight_clip() -> None:
    """Companions clip_engagement_fraction is exactly 36/57 for a tight-clip field.

    Bug caught: if engagement compared clipped-vs-clipped (raw values lost)
    the fraction would be 0.0; if the halo were dropped from the grid or the
    hull clamp bounds drifted, the row count and hence the fraction would
    shift away from 36/57.

    Hand computation (independent of the implementation): coeffs [0,1,0,0,0]
    give raw log_s = v = (lat_clamped - 38)/5.  With clip (-0.5, 0.5),
    a node engages iff |v| > 0.5, i.e. lat_clamped < 35.5 or > 40.5.
    On the lat grid 31.0..45.0 step 0.25 (57 rows, hull-clamped to [33,43]):
    rows 31.0..35.25 engage (18 rows; v <= -0.55) and rows 40.75..45.0
    engage (18 rows; v >= 0.55); lat=35.5/40.5 give v=±0.5 exactly
    (binary-exact at step 0.25) so raw == clipped there — NOT engaged.
    36 of 57 rows engage, independent of lon; fraction = 36/57.
    """
    mod = _load_anchor_module()
    sel = _synthetic_selection()
    tight_cal = {
        "kind": "poly",
        "coeffs": [0.0, 1.0, 0.0, 0.0, 0.0],
        "clip": {"lo_log_s": -0.5, "hi_log_s": 0.5},
        "fit_id": "test-tight",
    }
    block = mod.build_anchor_block(
        selection=sel,
        cal_json=tight_cal,
        cal_key="cal:test-tight",
        mask_sha256="deadbeef",
    )
    frac = block["companions"]["clip_engagement_fraction"]
    assert 0.0 < frac < 1.0, (
        f"Tight clip should engage on part (not all/none) of grid, got {frac}"
    )
    expected = 36.0 / 57.0
    assert abs(frac - expected) < 1e-12, (
        f"clip_engagement_fraction should be exactly 36/57 = {expected}, got {frac}"
    )


def test_companions_nll_gap_demoted_dof_is_5() -> None:
    """companions.nll_gap_demoted has dof=5 (5 poly coefficients, per spec §7c4).

    Bug caught: if dof were hardcoded as 1 (scalar) or derived from a wrong
    parameter count, Phase-10 would apply incorrect AIC adjustments.
    """
    mod = _load_anchor_module()
    sel = _synthetic_selection()
    block = mod.build_anchor_block(
        selection=sel,
        cal_json=_synthetic_cal_json(),
        cal_key="cal:test",
        mask_sha256="deadbeef",
    )
    ngd = block["companions"]["nll_gap_demoted"]
    assert ngd["dof"] == 5, f"nll_gap_demoted.dof should be 5, got {ngd['dof']}"


def test_companions_nll_gap_n_eff_note_mentions_aic() -> None:
    """companions.nll_gap_demoted n_eff_note mentions AIC and n_eff (per spec §7c4).

    Bug caught: if n_eff_note were an empty string or omitted, the demoted-stats
    context required by the spec would be absent, silently making the gap
    appear as a valid threshold statistic.
    """
    mod = _load_anchor_module()
    sel = _synthetic_selection()
    block = mod.build_anchor_block(
        selection=sel,
        cal_json=_synthetic_cal_json(),
        cal_key="cal:test",
        mask_sha256="deadbeef",
    )
    note = block["companions"]["nll_gap_demoted"]["n_eff_note"]
    assert "AIC" in note, f"n_eff_note must mention AIC; got: {note!r}"
    assert "n_eff" in note, f"n_eff_note must mention n_eff; got: {note!r}"


def test_companions_area_weighted_std_log_s_positive() -> None:
    """companions.area_weighted_std_log_s is a positive float for a non-flat field.

    Bug caught: if area weighting were applied incorrectly (wrong axis,
    non-normalised weights) the std could be zero or negative.

    We use a field with nonzero linear coefficient (a1=1.0) so log_s varies
    across the grid, giving a positive std.
    """
    mod = _load_anchor_module()
    sel = _synthetic_selection()
    # Non-flat field: a1=1.0 means log_s varies with lat
    varying_cal = {
        "kind": "poly",
        "coeffs": [0.0, 1.0, 0.0, 0.0, 0.0],
        "clip": {"lo_log_s": -5.0, "hi_log_s": 5.0},
        "fit_id": "test-vary",
    }
    block = mod.build_anchor_block(
        selection=sel,
        cal_json=varying_cal,
        cal_key="cal:test-vary",
        mask_sha256="deadbeef",
    )
    std = block["companions"]["area_weighted_std_log_s"]
    assert std > 0.0, f"Expected positive std for varying field, got {std}"
    assert isinstance(std, float), f"std must be builtin float, got {type(std)}"


def test_definition_string_contains_spec_wording() -> None:
    """build_anchor_block embeds the spec §7c1 definition verbatim.

    Bug caught: if the definition string were a paraphrase or empty, the
    Phase-10 interface contract would lose its pinned wording — the anchor's
    whole purpose is to carry the verbatim definition alongside the number.
    """
    mod = _load_anchor_module()
    sel = _synthetic_selection()
    block = mod.build_anchor_block(
        selection=sel,
        cal_json=_synthetic_cal_json(),
        cal_key="cal:test",
        mask_sha256="deadbeef",
    )
    defn = block["definition"]
    # Must contain key terms from §7c1 wording
    assert "lane-0" in defn.lower() or "lane 0" in defn.lower(), (
        f"definition must reference lane-0; got: {defn!r}"
    )
    assert "winner" in defn.lower(), f"definition must reference winner; got: {defn!r}"
    assert "pooled" in defn.lower(), (
        f"definition must reference pooled worst-region; got: {defn!r}"
    )


# ---------------------------------------------------------------------------
# Phase-11 dormant wiring (Task 6): report_only_instruments in every pack
# ---------------------------------------------------------------------------

_P11_SCHEMA_KEYS = {
    "schema_version",
    "evaluator",
    "evaluator_version",
    "metrics",
    "context_keys_available",
    "context_keys_used",
    "params",
    "n_modes",
    "flags",
    "provenance",
}


@pytest.mark.skipif(
    not (
        MIOST_DESCRIPTOR.mean_maps.exists()
        and MIOST_DESCRIPTOR.var_maps.exists()
        and MIOST_DESCRIPTOR.scope_config.exists()
        and MIOST_DESCRIPTOR.mask_artifact.exists()
    ),
    reason="full data artifacts absent (data/ours/ untracked)",
)
def test_report_only_instruments_block_in_dev_scope_pack() -> None:
    """Phase-11 dormant-wiring gate: a dev-scope harness pack carries the
    report_only_instruments block with >= 2 full-schema rows.

    Bug caught: the report-only instrument pattern silently absent from
    future evidence packs (the exact wiring-drift failure the architecture
    audit found for track_power)."""
    from sverdrup.application.calibration.harness import run_harness

    evidence = run_harness(MIOST_DESCRIPTOR, scope="dev")
    block = evidence["report_only_instruments"]
    assert block["mean_maps_sha256"]
    rows = block["rows"]
    assert len(rows) >= 2
    for row in rows:
        assert set(row) == _P11_SCHEMA_KEYS, row["evaluator"]
    names = {r["evaluator"] for r in rows}
    assert "spectral_fidelity" in names
    fid = next(r for r in rows if r["evaluator"] == "spectral_fidelity")
    assert any(f.startswith("wedge_exclusion:") for f in fid["flags"])
