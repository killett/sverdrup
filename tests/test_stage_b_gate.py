"""Stage-B gate: GMRF tuned via BO lands a sensible, non-regressing challenge score.

Opt-in (multi-hour, needs the 1.2GB challenge data): set ``SVERDRUP_STAGE_B_GATE=1``.
This is the USER GATE that owns the GMRF ``(µ, σ, λx)`` acceptance NUMBER (AC split
2026-06-29). It runs the GMRF sweep twice on the SAME scope/seed — once with the Sobol
baseline, once with ``BayesianOptimization`` — and asserts BO lands a finite acceptance
that does not badly regress the Sobol λx. Capture BOTH rows for the gate evidence.

Per PROGRESS.md the 12-day dev fixture is all-degenerate for GMRF (random Sobol too
weak); landing a real admissible GMRF winner is expected to need the full-2017 window
in ``stage_a_scope.json``. The ``n_trials`` here is a placeholder the gate run overrides.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

FIX = Path("tests/validation/fixtures")

_OPT_IN = (
    os.environ.get("SVERDRUP_STAGE_B_GATE") == "1"
    and (FIX / "stage_a_scope.json").exists()
)


@pytest.mark.skipif(
    not _OPT_IN,
    reason=(
        "Stage-B gate is opt-in (multi-hour GMRF run, needs data/2021a_ssh_mapping_ose/): "
        "set SVERDRUP_STAGE_B_GATE=1 to run the real GMRF-via-BO acceptance."
    ),
)
def test_gmrf_bo_lands_sensible_score() -> None:
    # Behavior: the GMRF sweep, driven by MULTI-ROUND BayesianOptimization through the
    # unchanged loop/objective/acceptance at equal total budget, produces a finite challenge
    # acceptance (µ, σ, λx) that does not regress the Sobol-baseline λx by more than 1.25x.
    # Bug it catches: a BO drop-in that silently degrades the search (out-of-bounds, collapse
    # to one point, or losing multi-round guidance) so the GMRF winner resolves a far coarser
    # scale than the Sobol baseline — or returns a non-finite acceptance.
    from sverdrup.application.tuning.bayesopt import BayesianOptimization
    from sverdrup.application.tuning.stage_a import StageANoAdmissible
    from sverdrup.application.tuning.stage_b import run_stage_b

    n = int(os.environ.get("SVERDRUP_STAGE_B_N", "8"))
    rounds = int(os.environ.get("SVERDRUP_STAGE_B_ROUNDS", "4"))
    scope = FIX / "stage_a_scope.json"
    try:
        # Sobol baseline: 1 round of n (Sobol ignores history; rounds>1 would duplicate).
        sobol = run_stage_b(scope=scope, n_trials=n, seed=1)
        # BO: R guided rounds of n // R -> same total budget n, surrogate re-fit each round.
        bo = run_stage_b(
            scope=scope,
            n_trials=n,
            seed=1,
            strategy=BayesianOptimization(seed=1, n=max(1, n // rounds)),
            rounds=rounds,
        )
    except StageANoAdmissible as exc:
        pytest.skip(
            f"no admissible GMRF trial on this scope ({exc}); the 12-day dev fixture is too "
            "small for GMRF — set stage_a_scope.json to the full-2017 window to run the gate."
        )
    # Finite, positive acceptance (µ and λx) — the GMRF winner produced a real map.
    assert bo.acceptance[0] > 0.0
    assert bo.acceptance[2] > 0.0
    # BO must not badly regress λx vs the Sobol baseline (record the margin).
    assert bo.acceptance[2] <= sobol.acceptance[2] * 1.25
