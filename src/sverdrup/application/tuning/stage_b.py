"""Stage-B wiring: the identical loop, GMRF parameter_space (single-tile, unconstrained)."""

from __future__ import annotations

from pathlib import Path

from sverdrup.application.tuning.stage_a import StageAReport, _run_stage
from sverdrup.application.tuning.strategy import SearchStrategy
from sverdrup.methods.gmrf import MaternGMRF


def run_stage_b(
    *,
    scope: Path,
    n_trials: int = 16,
    seed: int = 1,
    strategy: SearchStrategy | None = None,
    rounds: int = 1,
) -> StageAReport:
    """Run Stage A's loop unchanged with GMRF's parameter_space and GMRF acceptance.

    ``strategy`` is the drop-in search; ``None`` keeps the ``SobolSearch`` baseline,
    while ``BayesianOptimization(seed, n_trials)`` runs the GMRF sweep under TPE
    (Task 14) with the loop/objective/acceptance untouched.
    """
    return _run_stage(
        method_name="gmrf",
        space=MaternGMRF().parameter_space(),
        scope=scope,
        n_trials=n_trials,
        seed=seed,
        strategy=strategy,
        rounds=rounds,
    )
