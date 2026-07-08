"""Pluggable feasibility predicate: the coherence barrier (Phase-5; Stage-C redesign 2026-07-01).

Capability-conditional (invariant 4) + tile-count-keyed. Replaces the refuted core/range >= 25
bound (a GMRF-prior-bug artifact, fixed in 6cce45b). Measured boundary + provenance:
docs/superpowers/specs/2026-07-01-stagec-redesign-design.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
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
class StoredGFeasibility:
    """Excludes trials whose predicted stored-G exceeds the RAM budget (spec §5.1).

    Cost model = methods.miost_sizing (the probe's single arithmetic). HALO-INCLUSIVE
    ``n_obs_max`` (max over windows). No L_t term: nnz is L_t-invariant (D3).
    Accounting: n_concurrent * bytes <= budget (execution contract, spec §4.2).
    """

    n_obs_max: int
    budget_bytes: float = 8e9
    n_concurrent: int = 1
    n_dir: int = 8
    lam_min: float = 80.0
    lam_max: float = 905.0

    def predicted_bytes(self, params: dict[str, float]) -> int:
        """Predict the stored-G footprint for one trial's spacing.

        Args:
            params: Trial params; only ``spacing_alpha`` enters the cost model.

        Returns:
            Predicted CSR bytes (float64 data + int32 index = 12 B/nnz).
        """
        from sverdrup.methods.miost_sizing import nnz_g

        return (
            nnz_g(
                self.n_obs_max,
                alpha=params["spacing_alpha"],
                n_dir=self.n_dir,
                lam_min=self.lam_min,
                lam_max=self.lam_max,
            )
            * 12
        )

    def explain(self, params: dict[str, float]) -> str | None:
        """Return the exclusion reason, or None when the trial fits the budget."""
        b = self.n_concurrent * self.predicted_bytes(params)
        if b <= self.budget_bytes:
            return None
        return (
            f"stored-G {b:.1e} B > budget {self.budget_bytes:.1e} B "
            f"(alpha={params['spacing_alpha']})"
        )

    def feasible(
        self,
        params: dict[str, float],
        tile_geometry: TileGeometry,
        required_capabilities: frozenset[UncertaintyCapability],
    ) -> bool:
        """Return True iff the predicted stored-G fits the budget."""
        return self.explain(params) is None


@dataclass(frozen=True)
class CompositeFeasibility:
    """All-of composition (invariant 5); first failing member's explain() is the reason."""

    members: tuple[FeasibilityPredicate, ...]

    def explain(self, params: dict[str, float]) -> str | None:
        """Return the first failing member's reason (or None when all pass).

        Members without their own ``explain`` contribute a class-name reason.
        """
        for m in self.members:
            expl = getattr(m, "explain", None)
            if expl is not None:
                reason = expl(params)
                if reason is not None:
                    return f"{type(m).__name__}: {reason}"
        return None

    def feasible(
        self,
        params: dict[str, float],
        tile_geometry: TileGeometry,
        required_capabilities: frozenset[UncertaintyCapability],
    ) -> bool:
        """Logical AND over all members (each keeps its own semantics)."""
        return all(
            m.feasible(params, tile_geometry, required_capabilities)
            for m in self.members
        )


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


def _mem_available_bytes() -> float:
    """MEASURED available RAM from /proc/meminfo (kB field -> bytes)."""
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable"):
            return float(line.split()[1]) * 1024.0
    raise RuntimeError("MemAvailable not found in /proc/meminfo")


@dataclass(frozen=True)
class PeakFeasibility:
    """Excludes trials whose MODELED PEAK RSS exceeds the measured-RAM budget.

    Task-22 re-grounding (owner-ordered): the component-sum peak model
    (``miost_sizing.peak_model`` — CSR G, assembly triplets, preconditioner
    copy, RHS batch, m-scaled PCG workspace; phase-MAX, no bare multiplier)
    replaces stored-G-only pricing, whose fixed 8e9 constant ignored
    transients and workspace (the OOM class). Model validated 2026-07-07
    against the instrumented windowed member-gen run: model/measured =
    1.11x (windowed leg) and 1.08x (single-window leg) — conservative,
    in the pre-registered [1x, 2x] band.

    ``budget_bytes=None`` derives the budget from MEASURED ``MemAvailable``
    at CONSTRUCTION time x ``safety`` — recorded on the instance so the
    exclusion reasons state the actual number used.
    """

    n_obs_max: int
    m: int = 1
    budget_bytes: float | None = None
    safety: float = 0.8
    n_dir: int = 8
    lam_min: float = 80.0
    lam_max: float = 905.0
    window_days: float = 60.0
    n_grid_nodes: int = 0

    def __post_init__(self) -> None:
        """Freeze the measured budget at construction when none is given."""
        if self.budget_bytes is None:
            object.__setattr__(
                self, "budget_bytes", self.safety * _mem_available_bytes()
            )

    def predicted_peak_bytes(self, params: dict[str, float]) -> float:
        """Modeled peak RSS for one trial's spacing at this predicate's m."""
        from sverdrup.methods.miost_sizing import peak_model

        return peak_model(
            alpha=params["spacing_alpha"],
            n_dir=self.n_dir,
            window_days=self.window_days,
            lam_min=self.lam_min,
            n_obs=self.n_obs_max,
            m=self.m,
            lam_max=self.lam_max,
            n_grid_nodes=self.n_grid_nodes,
        ).total

    def explain(self, params: dict[str, float]) -> str | None:
        """Return the exclusion reason, or None when the trial fits."""
        peak = self.predicted_peak_bytes(params)
        budget = float(self.budget_bytes)  # type: ignore[arg-type]
        if peak <= budget:
            return None
        return (
            f"modeled peak RSS {peak:.2e} B > budget {budget:.2e} B "
            f"(alpha={params['spacing_alpha']}, m={self.m}; component-sum "
            "peak model, Task 22)"
        )

    def feasible(
        self,
        params: dict[str, float],
        tile_geometry: TileGeometry,
        required_capabilities: frozenset[UncertaintyCapability],
    ) -> bool:
        """Return True iff the modeled peak fits the measured-RAM budget."""
        return self.explain(params) is None
