"""Tests for the shared eval wiring path (plan Task 6, spec §7).

Covers the context builder (field_kind single source, geometry filtering,
ONE mask derivation — owner pin 1b), default_registry, and the report-row
builder (full schema, visible skip rows, propagating guards).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import numpy as np
import pytest

from sverdrup.application.eval_context import (
    build_eval_context,
    build_report_rows,
    default_registry,
)
from sverdrup.core.evaluation import ContextKey, EvalContext, Registry
from sverdrup.eval import ALL_EVALUATORS
from sverdrup.eval.accuracy import Accuracy

_SCHEMA_KEYS = {
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


def _real_axes() -> tuple[np.ndarray, np.ndarray]:
    return np.arange(295, 305.01, 0.2), np.arange(33, 43.21, 0.2)


def _maps(seed: int, n_days: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    lon, lat = _real_axes()
    return rng.standard_normal((n_days, lat.size, lon.size))


def _fam(heading: float) -> dict[str, Any]:
    return {
        "heading_north_deg": heading,
        "n_passes": 24,
        "n_crossings": 24,
        "orbit_class": "repeat",
        "s_lon_km": 300.0,
        "d_perp_km": 280.0,
        "spacing_quantiles_km": None,
    }


def _write_geometry_artifact(path: Path) -> None:
    artifact = {
        "derivation_version": 1,
        "key": "test",
        "phi0": 38.1,
        "missions": {
            "alg": {"asc": _fam(12.0), "desc": _fam(168.0)},
            "s3a": {"asc": _fam(30.0), "desc": None},
            "j2g": {"asc": _fam(66.0), "desc": None},
        },
        "provenance": {"obs_sha256": {}},
    }
    path.write_text(json.dumps(artifact))


def _mean_result() -> dict[str, Any]:
    lon, lat = _real_axes()
    return {"fields": _maps(0, 2), "grid_lon": lon, "grid_lat": lat}


def test_default_registry_matches_all_evaluators() -> None:
    """Bug caught: a new evaluator added to ALL_EVALUATORS but not wired into
    the default registry (or vice versa) — the two must stay in lockstep."""
    assert {type(e).__name__ for e in default_registry()._evaluators} == {
        type(f()).__name__ for f in ALL_EVALUATORS if f().name != "effective_resolution"
    }
    # EffectiveResolution excluded THIS PHASE: its inputs (eval_locations/
    # eval_times) are not part of the standard result payload the builder
    # assembles; recorded decision (obligation 3) — integrity coverage comes
    # from ALL_EVALUATORS, not default_registry.


def test_skip_row_is_visible_not_silent() -> None:
    """Bug caught: an evaluator returning {} silently vanishing from the
    report — the pinned convention is a VISIBLE skip row."""
    rows = build_report_rows(
        Registry([Accuracy()]),
        {"eval_mean": np.array([1.0]), "field_kind": "mean"},
        EvalContext({}),
    )
    (row,) = rows
    assert row["flags"] == ["no_usable_context"]
    assert row["context_keys_used"] == []
    assert row["metrics"] == {}


def test_builder_sets_field_kind_and_filters_missions(tmp_path: Path) -> None:
    """Bug caught: field_kind left unset (sigma-guard toothless) or geometry
    NOT filtered by the product's assimilated_missions attr (a mission the
    product never assimilated would leak probe wedges into its scoring)."""
    art = tmp_path / "geom.json"
    _write_geometry_artifact(art)
    built = build_eval_context(
        _mean_result(),
        field_kind="mean",
        geometry_artifact=art,
        assimilated_missions="alg s3a",  # j2g present in artifact, NOT here
    )
    assert built.result["field_kind"] == "mean"
    bag = cast("dict[str, Any]", built.context.items[ContextKey.ORBIT_GEOMETRY])
    assert set(bag) == {"alg", "s3a"}
    # masks: alg asc+desc, s3a asc = 3 families
    assert len(built.result["track_wedge_masks"]) == 3
    assert built.wedge_masks_sha is not None


def test_builder_without_geometry_leaves_context_lean() -> None:
    """Bug caught: fabricating an ORBIT_GEOMETRY entry (or masks) when no
    artifact exists — absence must mean absence."""
    built = build_eval_context(_mean_result(), field_kind="mean")
    assert ContextKey.ORBIT_GEOMETRY not in built.context.items
    assert "track_wedge_masks" not in built.result
    assert built.wedge_masks_sha is None


def test_mask_derivation_shared_across_both_consumer_rows(tmp_path: Path) -> None:
    """OWNER PIN 1b — bug caught: two independent mask derivations drifting
    apart. The builder derives ONCE; both consumer rows must record the SAME
    wedge_masks_sha (spec §3's 'one exclusion implementation, two consumers'
    made checkable)."""
    art = tmp_path / "geom.json"
    _write_geometry_artifact(art)
    built = build_eval_context(
        _mean_result(),
        field_kind="mean",
        geometry_artifact=art,
        assimilated_missions="alg s3a j2g",
    )
    rows = build_report_rows(default_registry(), built.result, built.context)
    by_name = {r["evaluator"]: r for r in rows}
    gt_sha = by_name["groundtrack"]["params"]["wedge_masks_sha"]
    fid_sha = by_name["spectral_fidelity"]["params"]["wedge_masks_sha"]
    assert gt_sha == fid_sha == built.wedge_masks_sha
    assert len(gt_sha) == 64  # sha256 hex
    # and the fidelity row says the exclusion actually happened (pin 1a)
    assert "wedge_exclusion:true" in by_name["spectral_fidelity"]["flags"]


def test_row_schema_complete_and_context_keys_used_are_reads(tmp_path: Path) -> None:
    """Bug caught: a missing schema field (evidence readers break) or
    context_keys_used fabricated from availability instead of actual reads."""
    art = tmp_path / "geom.json"
    _write_geometry_artifact(art)
    result = _mean_result()
    n = 32
    rng = np.random.default_rng(1)
    result["eval_mean"] = rng.standard_normal(n)
    result["eval_var"] = np.full(n, 0.1)
    built = build_eval_context(
        result,
        field_kind="mean",
        geometry_artifact=art,
        assimilated_missions="alg",
        withheld={"values": rng.standard_normal(n)},
    )
    rows = build_report_rows(default_registry(), built.result, built.context)
    assert {r["evaluator"] for r in rows} == {
        "accuracy",
        "calibration",
        "skill",
        "groundtrack",
        "spectral_fidelity",
    }
    for row in rows:
        assert set(row) == _SCHEMA_KEYS, row["evaluator"]
        assert set(row["context_keys_used"]) <= set(row["context_keys_available"])
    by_name = {r["evaluator"]: r for r in rows}
    # accuracy read WITHHELD_OBS (not TRUTH — absent; not fabricated)
    assert by_name["accuracy"]["context_keys_used"] == ["WITHHELD_OBS"]
    assert by_name["groundtrack"]["context_keys_used"] == ["ORBIT_GEOMETRY"]
    # n_modes companions surfaced for the spectral consumers
    assert by_name["spectral_fidelity"]["n_modes"] != {}


def test_guard_raise_propagates(tmp_path: Path) -> None:
    """Bug caught: the row builder swallowing evaluator guards — a sigma map
    reaching a mean-only evaluator must CRASH the run, not emit a row."""
    art = tmp_path / "geom.json"
    _write_geometry_artifact(art)
    built = build_eval_context(
        _mean_result(),
        field_kind="sigma",
        geometry_artifact=art,
        assimilated_missions="alg",
    )
    with pytest.raises(ValueError, match="mean"):
        build_report_rows(default_registry(), built.result, built.context)
