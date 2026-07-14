"""Stage-A wiring for miost: the shared stage with POINT bars + resource predicate.

Delegates to the method-agnostic ``_run_stage`` (Task-12 invariant: no
method-specific branch in the loop). The three miost-specific arguments are
ARGUMENTS, not branches: a wide ``temporal_half_window_days`` (the window-cache
Method re-subsets internally), a composite feasibility predicate (stored-G RAM
pricing + the standing coherence predicate), and the single-tile geometry.
"""

from __future__ import annotations

from pathlib import Path

from sverdrup.application.tuning.feasibility import (
    FeasibilityPredicate,
    TileGeometry,
)
from sverdrup.application.tuning.stage_a import StageAReport, _run_stage
from sverdrup.application.tuning.strategy import SearchStrategy
from sverdrup.methods.miost import Miost

MIOST_HALF_WINDOW_DAYS = 425.0  # full obs each call; method re-subsets per window


def run_stage_miost(
    *,
    scope: Path,
    predicate: FeasibilityPredicate,
    n_trials: int = 16,
    seed: int = 1,
    strategy: SearchStrategy | None = None,
    rounds: int = 1,
) -> StageAReport:
    """Run the shared single-tile stage on miost (POINT bars derive automatically).

    Args:
        scope: Stage scope JSON (paths, days, validation mission).
        predicate: Feasibility predicate — pass the CompositeFeasibility of
            ``StoredGFeasibility`` (halo-inclusive obs count) + ``CoherenceFeasibility``.
        n_trials: Trials per round.
        seed: Search seed.
        strategy: Drop-in search strategy (None = seeded Sobol).
        rounds: Propose/score rounds (BO uses n_trials // rounds per round).

    Returns:
        The stage report (winner, single-touch c2 acceptance, history).
    """
    return _run_stage(
        # SEARCH entry (post-flip, Task 22): sweeps price/score the POINT
        # method — the shipped SAMPLES product lives in SHIPPED["miost"]
        # (registry role-split) and must never generate members per trial
        # (spec 6.1).
        method_name="miost-point",
        space=Miost().parameter_space(),
        scope=scope,
        n_trials=n_trials,
        seed=seed,
        strategy=strategy,
        rounds=rounds,
        predicate=predicate,
        temporal_half_window_days=MIOST_HALF_WINDOW_DAYS,
        tile_geometry=TileGeometry(10.0, 0.0, "miost-single", n_tiles=1),
    )
