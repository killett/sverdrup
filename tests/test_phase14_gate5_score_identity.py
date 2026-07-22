"""SPEC §10 gate 5 — score-level anchor identity (CODE lands Stage 0, RUNS Stage 1).

``score_tile(anchor_frame(), signed_maps, j3_track)`` must reproduce the
signed scoring path EXACTLY: identical to the vendored box sequence
(``their_eval.score``) at rtol 1e-12 on all three of (µ, σ, λx).

Recorded deviation (for the gate-0 pack): the signed record carries NO
full-precision (µ, σ, λx) triple in the COMPUTE_STATS lineage for the j3
track — the phase-13 ``lane0_reference.mu_score`` (0.8641999994291494) is
the ``leaderboard_nrmse`` estimator at track granularity, a DIFFERENT
quantity from the vendored area-binned ``compute_stats`` µ this scorer
emits (see ``eval/skill_score.py``; adversarial review 2026-07-22 caught
the near-miss of pinning it here). So gate 5 asserts the machinery
identity now, and the compute_stats-lineage value constants are pinned AT
the Stage-1 anchor run (recorded into ``phase14.stage1.gate5`` evidence
when this test first runs unskipped). Owner ratifies at Gate 0.

SKIP-GUARDED: the anchor-run artifacts exist only in Stage 1.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from sverdrup.application.spatial_tiles import anchor_frame

# The Stage-1 anchor run (frozen signed config through the tile substrate)
# writes its mean maps here; until then this gate SKIPS with the path named.
ANCHOR_SIGNED_MAPS = Path(
    "data/2021a_ssh_mapping_ose/ours/phase14_stage1/anchor_signed_maps.nc"
)
_J3_TRACK = Path(
    "data/2021a_ssh_mapping_ose/dc_obs/"
    "dt_gulfstream_j3_phy_l3_20161201-20180131_285-315_23-53.nc"
)

pytestmark = pytest.mark.skipif(
    not ANCHOR_SIGNED_MAPS.exists(),
    reason=(
        f"gate-5 runs in Stage 1: anchor-run artifact {ANCHOR_SIGNED_MAPS} not present"
    ),
)


def test_gate5_anchor_score_identity() -> None:
    """The per-tile scorer on the anchor frame == the signed box scoring."""
    from sverdrup.validation import their_eval
    from sverdrup.validation.pertile_scoring import score_tile

    ours = score_tile(anchor_frame(), ANCHOR_SIGNED_MAPS, _J3_TRACK)
    mu, sigma, lambda_x = their_eval.score(ANCHOR_SIGNED_MAPS, _J3_TRACK)
    assert np.isclose(ours.mu, mu, rtol=1e-12, atol=0.0)
    assert np.isclose(ours.sigma, sigma, rtol=1e-12, atol=0.0)
    assert np.isclose(ours.lambda_x, lambda_x, rtol=1e-12, atol=0.0)
