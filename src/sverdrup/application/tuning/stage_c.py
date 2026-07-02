"""Stage-C wiring: the global multi-tile coherent mode where the joint barrier binds.

The feasibility predicate keys on tile count (design 2026-07-01): at the default
n_star_joint=1 any n_tiles>=2 SAMPLES/COVARIANCE trial is excluded before solve. The loop's
gate-before-solve guarantee makes the barrier hard (test 4).
"""

from __future__ import annotations

from sverdrup.application.tuning.feasibility import FeasibilityPredicate, TileGeometry
from sverdrup.application.tuning.loop import TrialScorer, TuningResult, tune
from sverdrup.application.tuning.objective import ConstrainedObjective
from sverdrup.application.tuning.strategy import SearchStrategy
from sverdrup.core.types import UncertaintyCapability
from sverdrup.methods.gmrf import MaternGMRF

_JOINT = frozenset({UncertaintyCapability.SAMPLES})


def tile_geometry_for(n_tiles: int, params: dict[str, float]) -> TileGeometry:
    """Derive the coherence-relevant geometry from the tile count + trial range."""
    return TileGeometry(
        core_size_deg=0.0,
        range_km=float(params.get("range", 0.0)),
        tiling_id=f"global-{n_tiles}tiles",
        n_tiles=n_tiles,
    )


def run_stage_c_loop(
    *,
    n_tiles: int,
    strategy: SearchStrategy,
    predicate: FeasibilityPredicate,
    objective: ConstrainedObjective,
    scorer: TrialScorer,
    seed: int,
    on_empty: str = "raise",
) -> TuningResult:
    """Run the GMRF global-coherent loop; the predicate gates on the fixed tile count.

    A single ``TileGeometry(n_tiles=n_tiles)`` per run — the joint barrier keys on tile count,
    not per-trial range, so no per-trial predicate wrapper is needed (unlike the retired
    core/range design).
    """
    return tune(
        method_name="gmrf",
        space=MaternGMRF().parameter_space(),
        strategy=strategy,
        predicate=predicate,
        objective=objective,
        scorer=scorer,
        split=type("S", (), {"id": "global"})(),
        seed=seed,
        window=type("W", (), {"id": "global"})(),
        tile_geometry=tile_geometry_for(n_tiles, {"range": 1.0}),
        required_capabilities=_JOINT,
        rounds=1,
        on_empty=on_empty,
    )
