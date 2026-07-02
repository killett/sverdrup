"""Pluggable feasibility predicate: the coherence barrier (Phase-5; Stage-C redesign 2026-07-01).

Capability-conditional (invariant 4) + tile-count-keyed. Replaces the refuted core/range >= 25
bound (a GMRF-prior-bug artifact, fixed in 6cce45b). Measured boundary + provenance:
docs/superpowers/specs/2026-07-01-stagec-redesign-design.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from sverdrup.core.types import UncertaintyCapability

_JOINT_CAPS = frozenset(
    {UncertaintyCapability.SAMPLES, UncertaintyCapability.COVARIANCE}
)


@dataclass(frozen=True)
class TileGeometry:
    """The geometry the coherence predicate keys on.

    ``n_tiles`` is the joint-tier key. ``core_size_deg``/``range_km`` are recorded context for
    the frontier artifact only — the predicate ignores them (measured: tile count, not
    core/range, drives the joint worst-case). ``n_tiles`` is appended + defaulted so the
    pre-redesign positional ``TileGeometry(core, range, id)`` call sites keep working.
    """

    core_size_deg: float
    range_km: float
    tiling_id: str
    n_tiles: int = 1


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


@dataclass(frozen=True)
class CoherenceFeasibility:
    """Default: capability-conditional + tile-count-keyed (design 2026-07-01).

    - SAMPLES/COVARIANCE (joint): feasible iff ``n_tiles <= n_star_joint``. Default
      ``n_star_joint=1`` is the tol=0.5 EMPTY-REGION shorthand — measured worst-of-K adjacent-seam
      corr-err exceeds ``joint_tol`` at every tested N>=2 (non-monotone in N; NOT a monotone law).
    - MARGINAL_VARIANCE: feasible iff ``marg_worst_case <= marg_tol`` — FLAT in N (measured ~15%),
      so ships iff ``marg_tol >= ~0.15``, tile-count-independent.
    - POINT / no joint requirement: always feasible (no seams).

    Predicate is CHEAP (baked constants); the heavy measurement is offline in
    ``scripts/diag_crossseam.py``, preserving the gate-before-solve hard barrier (invariant 3).
    """

    joint_tol: float = 0.5
    n_star_joint: int = 1
    marg_tol: float = 0.20
    marg_worst_case: float = 0.15  # MEASURED, FLAT in tile count (design §2)

    def feasible(
        self,
        params: dict[str, float],
        tile_geometry: TileGeometry,
        required_capabilities: frozenset[UncertaintyCapability],
    ) -> bool:
        """Return the capability-scoped, tile-count-keyed feasibility verdict."""
        if required_capabilities & _JOINT_CAPS:
            return tile_geometry.n_tiles <= self.n_star_joint
        if UncertaintyCapability.MARGINAL_VARIANCE in required_capabilities:
            return self.marg_worst_case <= self.marg_tol
        return True


@dataclass(frozen=True)
class RelaxedCoherenceFeasibility:
    """The redesign's interface (invariant 5): widens the joint region, tuner untouched.

    The owner-deferred coarse-correction supplies this. ``n_star_joint`` here is ILLUSTRATIVE of
    the mechanism (a wider tile-count bound), NOT a measured value — the fix is unbuilt.
    """

    n_star_joint: int = 64
    marg_tol: float = 0.20
    marg_worst_case: float = 0.15

    def feasible(
        self,
        params: dict[str, float],
        tile_geometry: TileGeometry,
        required_capabilities: frozenset[UncertaintyCapability],
    ) -> bool:
        """Same body as the default, reading the widened bounds."""
        if required_capabilities & _JOINT_CAPS:
            return tile_geometry.n_tiles <= self.n_star_joint
        if UncertaintyCapability.MARGINAL_VARIANCE in required_capabilities:
            return self.marg_worst_case <= self.marg_tol
        return True
