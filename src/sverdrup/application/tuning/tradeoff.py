"""Stage-C both-tiers feasibility frontier: the owner's redesign-decision input.

THIN CONSUMER — no measurement here. The heavy cross-seam measurement lives in
scripts/diag_crossseam.py (constant-core sweep, M=8000, selection-controlled worst-of-K; plus the
analytic MARGINAL_VARIANCE-accuracy sweep). Its results are baked below and fed to the injected
predicate, so a relaxed predicate (the redesign interface) widens the feasible region WITHOUT
touching this module (invariant 5). Provenance + tables: design §2.
"""

from __future__ import annotations

from sverdrup.application.tuning.feasibility import FeasibilityPredicate, TileGeometry
from sverdrup.core.types import UncertaintyCapability

_SAMPLES = frozenset({UncertaintyCapability.SAMPLES})
_MARGINAL = frozenset({UncertaintyCapability.MARGINAL_VARIANCE})

# MEASURED (scripts/diag_crossseam.py, constant 4 deg core; design §2). joint_* = adjacent-seam
# corr-err worst-of-K (K=418 fixed) + its estimator std + node-pair median; marg = analytic
# reported-marginal worst-case rel error (FLAT in N).
MEASURED_FRONTIER: list[dict[str, float]] = [
    {
        "n_tiles": 4,
        "joint_worst_of_k": 1.105,
        "joint_wok_std": 0.000,
        "joint_median": 0.015,
        "marg_worst_case": 0.069,
    },
    {
        "n_tiles": 9,
        "joint_worst_of_k": 0.506,
        "joint_wok_std": 0.079,
        "joint_median": 0.023,
        "marg_worst_case": 0.140,
    },
    {
        "n_tiles": 16,
        "joint_worst_of_k": 0.823,
        "joint_wok_std": 0.135,
        "joint_median": 0.031,
        "marg_worst_case": 0.130,
    },
    {
        "n_tiles": 25,
        "joint_worst_of_k": 2.033,
        "joint_wok_std": 0.000,
        "joint_median": 0.052,
        "marg_worst_case": 0.149,
    },
    {
        "n_tiles": 36,
        "joint_worst_of_k": 2.108,
        "joint_wok_std": 0.000,
        "joint_median": 0.070,
        "marg_worst_case": 0.132,
    },
]


def _geom(n_tiles: int) -> TileGeometry:
    return TileGeometry(
        core_size_deg=4.0, range_km=300.0, tiling_id=f"c{n_tiles}", n_tiles=n_tiles
    )


def feasibility_frontier(
    predicate: FeasibilityPredicate,
) -> list[dict[str, float | bool]]:
    """Return per-tile-count rows with both tiers' worst-case + the predicate's verdict.

    ``joint_feasible`` / ``marg_feasible`` are the predicate's decisions for {SAMPLES} /
    {MARGINAL_VARIANCE} at each measured tile count. Injecting a relaxed predicate widens the
    joint region with no change here (invariant 5).
    """
    rows: list[dict[str, float | bool]] = []
    for m in MEASURED_FRONTIER:
        n = int(m["n_tiles"])
        rows.append(
            {
                "n_tiles": n,
                "joint_worst_of_k": m["joint_worst_of_k"],
                "joint_feasible": predicate.feasible({}, _geom(n), _SAMPLES),
                "marg_worst_case": m["marg_worst_case"],
                "marg_feasible": predicate.feasible({}, _geom(n), _MARGINAL),
            }
        )
    return rows
