"""Tests for the phase-13 refit + §9 readings glue (plan Task 11).

Guard-level (the heavy harness/scoring paths run detached); each test
names the bug it catches.
"""

from __future__ import annotations

import pytest

from sverdrup.application.calibration.harness import MIOST_DESCRIPTOR
from tests.helpers import load_script

rr = load_script("phase13_refit_readings")


def test_refit_descriptor_carries_the_frozen_frame() -> None:
    # §9b: the refit runs "via the Phase-9 harness under its frozen-frame
    # discipline (MIOST G_pre anchor family)" — mask, fold tuple, and
    # scope config must be BYTE-IDENTICAL to the MIOST descriptor; only
    # the maps, evidence key, and field artifact differ.
    # Bug caught: a refit in a different frame (new mask/folds) — G_post
    # would not be comparable to the anchored G_pre and the ŝ delta row
    # would silently compare across frames.
    d = rr.PHASE13_DESCRIPTOR
    assert d.mask_artifact == MIOST_DESCRIPTOR.mask_artifact
    assert d.scope_config == MIOST_DESCRIPTOR.scope_config
    assert d.fold_seed_tuple == ("miost", "phase8", "s-folds")
    assert d.covariate_promoted == MIOST_DESCRIPTOR.covariate_promoted
    assert d.evidence_key == "phase13.miost.refit"
    assert d.product_id == "miost_phase13"
    assert "phase13" in str(d.mean_maps) and "phase13" in str(d.field_artifact)
    assert d.mean_maps != MIOST_DESCRIPTOR.mean_maps


def test_gpre_anchor_mismatch_refuses() -> None:
    # The MIOST anchor family G_pre is sealed evidence: a recomputed or
    # drifted value refuses the reading (phase-10 --anchor STOP pattern).
    # Bug caught: silently reading G_pre from a mutated anchor block —
    # the shrinkage row would be computed against a wrong baseline.
    good = {"g_pre": {"g_pre": rr._EXPECTED_G_PRE}}
    assert rr._verify_gpre(good) == rr._EXPECTED_G_PRE
    with pytest.raises(SystemExit, match="G_pre"):
        rr._verify_gpre({"g_pre": {"g_pre": rr._EXPECTED_G_PRE + 1e-9}})


def test_groundtrack_direction_row_reads_against_0410() -> None:
    # §9a owner watch row: direction vs the five-mission baseline 0.410
    # (DOWN expected if track-correlated error is real and absorbed);
    # six-mission 0.376 quoted beside, non-governing.
    # Bug caught: inverted direction reading, or the baseline replaced by
    # the non-governing six-mission number.
    down = rr._direction_row(0.35)
    up = rr._direction_row(0.45)
    assert down["direction_vs_baseline"] == "DOWN"
    assert up["direction_vs_baseline"] == "UP"
    assert down["baseline_five_mission"] == 0.410
    assert down["six_mission_beside_non_governing"] == 0.376
    assert "necessary-not-sufficient" in down["caveat"]
