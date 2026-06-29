"""Stage B runs the identical loop with GMRF; acceptance produces a score."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

FIX = Path("tests/validation/fixtures")


@pytest.mark.skipif(
    os.environ.get("SVERDRUP_STAGE_A_E2E") != "1"
    or not (FIX / "stage_a_scope.json").exists(),
    reason=(
        "Stage-B end-to-end is opt-in (multi-minute, needs the 1.2GB challenge data): "
        "set SVERDRUP_STAGE_A_E2E=1 and ensure data/2021a_ssh_mapping_ose/ is present."
    ),
)
def test_stage_b_runs_and_accepts() -> None:
    from sverdrup.application.tuning.stage_b import run_stage_b

    report = run_stage_b(scope=FIX / "stage_a_scope.json", n_trials=8, seed=1)
    mu, sigma, lambda_x = report.acceptance
    assert mu > 0 and lambda_x > 0
