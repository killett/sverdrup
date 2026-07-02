"""The capability-conditional, tile-count-keyed coherence feasibility predicate."""

from __future__ import annotations

from sverdrup.application.tuning.feasibility import (
    CoherenceFeasibility,
    RelaxedCoherenceFeasibility,
    TileGeometry,
)
from sverdrup.core.types import UncertaintyCapability

SAMPLES = frozenset({UncertaintyCapability.SAMPLES})
COVARIANCE = frozenset({UncertaintyCapability.COVARIANCE})
MARGINAL = frozenset({UncertaintyCapability.MARGINAL_VARIANCE})
POINT = frozenset({UncertaintyCapability.POINT})


def _geom(n_tiles: int) -> TileGeometry:
    return TileGeometry(
        core_size_deg=4.0, range_km=300.0, tiling_id="g", n_tiles=n_tiles
    )


def test_samples_infeasible_at_multi_tile() -> None:
    # Bug it catches: a predicate that lets a multi-tile joint product through
    # (the measured empty region — joint worst-case > tol at every N>=2).
    p = CoherenceFeasibility()
    assert p.feasible({}, _geom(2), SAMPLES) is False
    assert p.feasible({}, _geom(9), COVARIANCE) is False
    assert (
        p.feasible({}, _geom(1), SAMPLES) is True
    )  # untiled single-tile is joint-valid


def test_marginal_ships_conditional_on_tol() -> None:
    # Bug it catches: burying the ~15% marginal-error acceptance in a constant so a
    # stricter tolerance silently still "ships".
    assert (
        CoherenceFeasibility().feasible({}, _geom(9), MARGINAL) is True
    )  # 0.15 <= 0.20
    strict = CoherenceFeasibility(marg_tol=0.10)
    assert strict.feasible({}, _geom(9), MARGINAL) is False  # 0.15 > 0.10
    # flat in N: same verdict at any tile count
    assert strict.feasible({}, _geom(2), MARGINAL) is False


def test_point_unconstrained() -> None:
    p = CoherenceFeasibility()
    assert p.feasible({}, _geom(9), POINT) is True
    assert p.feasible({}, _geom(999), frozenset()) is True


def test_relaxed_widens_joint_region() -> None:
    # TEST 6 (redesign interface): a relaxed predicate widens n_star_joint, tuner unchanged.
    default = CoherenceFeasibility()
    relaxed = RelaxedCoherenceFeasibility(n_star_joint=64)
    assert default.feasible({}, _geom(9), SAMPLES) is False
    assert relaxed.feasible({}, _geom(9), SAMPLES) is True
