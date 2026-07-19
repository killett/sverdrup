"""Tests for the phase-13 pre-registration bundle (plan Task 6).

Tamper refusal, the lane-0 µ assertion, and the box arithmetic — each
test names the bug it catches.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sverdrup.application.tuning.lane_compare import (
    PreRegistrationError,
    load_protocol,
    seal_protocol,
)
from sverdrup.validation import phase13_boxes as boxes
from tests.helpers import load_script

prereg = load_script("phase13_prereg")


def test_tampered_artifact_refuses(tmp_path: Path) -> None:
    # Bug caught: a band computed against a modified protocol — the whole
    # pre-registration discipline hinges on the sha binding refusing this.
    p = tmp_path / "artifact.json"
    sha = seal_protocol(p, created_utc="2026-07-19T00:00:00+00:00")
    doc = json.loads(p.read_text())
    doc["n_resamples"] = 5  # the tamper
    p.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
    with pytest.raises(PreRegistrationError, match="sha"):
        load_protocol(p, expected_sha=sha)


def test_lane0_mu_mismatch_refuses() -> None:
    # Bug caught: regenerated lane-0 residual arrays that do NOT reproduce
    # the recorded validation µ silently anchoring every pair band — the
    # reference side would be a different product than the signed record.
    with pytest.raises(SystemExit, match="mu"):
        prereg.assert_lane0_mu(0.8641, prereg.RECORDED_LANE0_MU)
    # exact reproduction passes
    prereg.assert_lane0_mu(prereg.RECORDED_LANE0_MU, prereg.RECORDED_LANE0_MU)


def test_recorded_mu_constant_matches_signed_record() -> None:
    # Bug caught: the frozen literal drifting from the signed record
    # (the phase-12 assert-against-record precedent, applied to µ).
    rec = json.loads(
        Path(
            "data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json"
        ).read_text()
    )
    assert prereg.RECORDED_LANE0_MU == rec["winner"]["scores"]["mu_score"]


def test_delta_s3a_derived_range_arithmetic() -> None:
    # Hand: -sum of four contrasts each in [-0.7, 0.7] -> [-2.8, 2.8].
    # Bug caught: the derived range recorded from a single contrast (+-0.7)
    # — the gate-1 source-table row would understate the balance excursion.
    lo, hi = boxes.DELTA_BOX
    assert boxes.DELTA_S3A_DERIVED_RANGE == (4 * lo, 4 * hi)


def test_box_constants_pinned() -> None:
    # Bug caught: sweep boxes drifting from the pre-registered values
    # between the seal and the sweep (the artifact restates these; this
    # pins the module side).
    assert boxes.DELTA_BOX == (-0.7, 0.7)
    assert boxes.LOG10_LAM_BOX == (-6.0, -2.5)
    assert boxes.SOBOL_DIMS[:4] == (
        "delta_alg",
        "delta_h2g",
        "delta_j2g",
        "delta_j2n",
    )
    assert boxes.SOBOL_DIMS[4] == "log10_rho"
    assert boxes.N_LAMBDA_USED_MIN_FRAC == 0.5
    assert boxes.BAND_LAMBDA_X_MAX_KM == 25.0
    assert boxes.NEGATIVE_WORDING == "improvements within band"
