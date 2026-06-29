"""Stage A: tuned OI through the loop; locked test touched exactly once."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from sverdrup.application.tuning.stage_a import run_stage_a

FIX = Path("tests/validation/fixtures")


@pytest.mark.skipif(
    os.environ.get("SVERDRUP_STAGE_A_E2E") != "1"
    or not (FIX / "stage_a_scope.json").exists(),
    reason=(
        "Stage-A end-to-end is opt-in (multi-minute, needs the 1.2GB challenge data): "
        "set SVERDRUP_STAGE_A_E2E=1 and ensure data/2021a_ssh_mapping_ose/ is present."
    ),
)
def test_stage_a_loop_and_single_acceptance(monkeypatch: pytest.MonkeyPatch) -> None:
    import sverdrup.validation.their_eval as te

    counts = {"n": 0}
    real = te.score

    def spy(*a: object, **k: object) -> object:
        counts["n"] += 1
        return real(*a, **k)  # type: ignore[arg-type]

    monkeypatch.setattr(te, "score", spy)
    # stage_a imports `score` by name, so patch the bound reference there too.
    import sverdrup.application.tuning.stage_a as sa

    monkeypatch.setattr(sa, "their_score", spy)

    report = run_stage_a(scope=FIX / "stage_a_scope.json", n_trials=8, seed=1)

    # TEST 2: locked test touched exactly once (only at acceptance).
    assert report.their_eval_calls_during_search == 0
    assert counts["n"] == 1

    # TEST 1: a winner cleared the hard bars; acceptance reported (µ, σ, λx).
    assert report.winner.scores is not None
    assert report.winner.scores["mu_score"] >= 0.85
    assert abs(report.winner.scores["coverage_1sigma"] - 0.6827) <= 0.10
    mu, sigma, lambda_x = report.acceptance
    assert mu > 0 and lambda_x > 0
