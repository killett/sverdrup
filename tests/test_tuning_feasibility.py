"""CoherenceFeasibility: capability-conditional hard barrier; pluggable relaxation."""

from __future__ import annotations

from sverdrup.application.tuning.feasibility import (
    CoherenceFeasibility,
    FeasibilityPredicate,
    RelaxedCoherenceFeasibility,
    TileGeometry,
)
from sverdrup.core.types import UncertaintyCapability as UC

_POINT = frozenset({UC.POINT})
_JOINT = frozenset({UC.SAMPLES})


def test_unconstrained_when_no_joint_capability() -> None:
    # Single-tile / per-gridpoint modes: always feasible (no seams).
    geom = TileGeometry(
        core_size_deg=4.0, range_km=400.0, tiling_id="single"
    )  # ratio ~1.1
    assert CoherenceFeasibility().feasible({}, geom, _POINT) is True


def test_binds_on_core_over_range_when_joint() -> None:
    # Bug it catches: the boundary not binding in the global-coherent mode.
    pred = CoherenceFeasibility()
    infeasible = TileGeometry(12.0, 400.0, "g")  # 12*111/400 ≈ 3.3 < 25
    feasible = TileGeometry(12.0, 40.0, "g")  # 12*111/40  ≈ 33  > 25
    assert pred.feasible({}, infeasible, _JOINT) is False
    assert pred.feasible({}, feasible, _JOINT) is True


def test_relaxed_widens_region_same_signature() -> None:
    # TEST 6: a relaxed predicate accepts what the default rejects, signature unchanged.
    geom = TileGeometry(12.0, 400.0, "g")
    assert CoherenceFeasibility().feasible({}, geom, _JOINT) is False
    assert RelaxedCoherenceFeasibility(min_ratio=1.0).feasible({}, geom, _JOINT) is True
    assert isinstance(RelaxedCoherenceFeasibility(), FeasibilityPredicate)
