"""Pluggable feasibility predicate: the hard coherence barrier (Phase-5, spec 5.2)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from sverdrup.core.types import UncertaintyCapability

KM_PER_DEG = 111.195
_JOINT_CAPS = frozenset(
    {UncertaintyCapability.SAMPLES, UncertaintyCapability.COVARIANCE}
)


@dataclass(frozen=True)
class TileGeometry:
    """The tiling geometry the coherence predicate keys on (from partition+params)."""

    core_size_deg: float
    range_km: float
    tiling_id: str


@runtime_checkable
class FeasibilityPredicate(Protocol):
    """Decide whether a trial may be solved+scored at all (hard barrier, invariant 3)."""

    def feasible(
        self,
        params: dict[str, float],
        tile_geometry: TileGeometry,
        required_capabilities: frozenset[UncertaintyCapability],
    ) -> bool:
        """Return True iff the trial is feasible to solve and score."""
        ...


class CoherenceFeasibility:
    """Default predicate keyed on the current tiling: core/range >= 25 when joint."""

    CORE_OVER_RANGE_MIN = 25.0  # measured Phase-4 bound (test_core_authoritative_gate)

    def feasible(
        self,
        params: dict[str, float],
        tile_geometry: TileGeometry,
        required_capabilities: frozenset[UncertaintyCapability],
    ) -> bool:
        """Return True iff single-tile, or (joint) core/range >= the measured bound."""
        if not (required_capabilities & _JOINT_CAPS):
            return True  # single-tile / per-gridpoint: no seams, unconstrained
        ratio = tile_geometry.core_size_deg * KM_PER_DEG / tile_geometry.range_km
        return ratio >= self.CORE_OVER_RANGE_MIN


@dataclass
class RelaxedCoherenceFeasibility:
    """A redesign-supplied predicate that widens the feasible region (invariant 5)."""

    min_ratio: float = 1.0

    def feasible(
        self,
        params: dict[str, float],
        tile_geometry: TileGeometry,
        required_capabilities: frozenset[UncertaintyCapability],
    ) -> bool:
        """Return True iff single-tile, or (joint) core/range >= the relaxed ratio."""
        if not (required_capabilities & _JOINT_CAPS):
            return True
        ratio = tile_geometry.core_size_deg * KM_PER_DEG / tile_geometry.range_km
        return ratio >= self.min_ratio
