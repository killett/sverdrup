"""Cross-tile coherent sampler via white-noise conditioning (design section 5)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol, cast, runtime_checkable

import numpy as np

from sverdrup.core.grid import GridSpec, PointSet
from sverdrup.core.seeding import derive_seed
from sverdrup.core.types import Field, Points


def _support_points(support: GridSpec | PointSet, time_days: float) -> Points:
    """Return ``(n, 3)`` points for either support kind."""
    if isinstance(support, PointSet):
        return support.points()
    return support.points(time_days)


def _nearest(grid: GridSpec | PointSet, pts: Points, t: float) -> np.ndarray:
    """Return the nearest support-node index for each point in ``pts`` at time ``t``."""
    nodes = grid.points() if isinstance(grid, PointSet) else grid.points(t)
    return np.asarray(
        np.argmin(np.linalg.norm(pts[:, None, :2] - nodes[None, :, :2], axis=2), axis=1)
    )


@dataclass(frozen=True)
class NoiseSpec:
    """The tile-independent global driving-noise spec (lattice + method identity).

    Attributes:
        method: Method name, used in the seed derivation.
        params_key: Canonical resolved-parameter string, used in the seed derivation.
        lattice_step: Degrees per global cell along lon & lat (tile-independent grid).
    """

    method: str
    params_key: str
    lattice_step: float


def _cell_ids(points: Points, step: float) -> np.ndarray:
    """Map points to deterministic global lattice cell ids (tile-independent)."""
    cx = np.floor(points[:, 0] / step).astype(np.int64)
    cy = np.floor(points[:, 1] / step).astype(np.int64)
    ct = np.floor(points[:, 2]).astype(np.int64)
    # a stable, collision-resistant-enough composite id for seeding
    return np.asarray((cx * 73856093) ^ (cy * 19349663) ^ (ct * 83492791))


def diagonal_noise(
    points: Points, member_index: int, noise_spec: NoiseSpec
) -> np.ndarray:
    """Return one N(0,1) draw per point, keyed by global cell id x member (coherent).

    Args:
        points: ``(n, 3)`` space-time points ``(lon, lat, time)``.
        member_index: The ensemble member index.
        noise_spec: The tile-independent global driving-noise spec.

    Returns:
        A length-``n`` array of standard-normal draws; the same global cell and member
        always yield the same value regardless of which tile requested it.
    """
    ids = _cell_ids(points, noise_spec.lattice_step)
    out = np.empty(points.shape[0], float)
    for i, cid in enumerate(ids):
        seed = derive_seed(
            noise_spec.method, noise_spec.params_key, f"cell:{cid}", member_index
        )
        out[i] = np.random.default_rng(seed).standard_normal()
    return out


@runtime_checkable
class StructuredNoiseSource(Protocol):
    """Drives the structured (low-rank) part; swap point for Option-1/Option-2."""

    def draw(
        self,
        member_index: int,
        parts: Sequence[Any],
        support: object,
        noise_spec: NoiseSpec,
    ) -> list[np.ndarray]:
        """Return one ``z_r`` latent vector per tile."""
        ...


@dataclass
class MemberSeededZr:
    """Option 1 (default): z_r seeded by member only — tile-independent latent."""

    def draw_one(
        self, member_index: int, rank: int, noise_spec: NoiseSpec
    ) -> np.ndarray:
        """Return the member's latent ``z_r`` prefix of length ``rank``.

        Args:
            member_index: The ensemble member index (seed depends on this only).
            rank: The length of the latent vector to draw.
            noise_spec: The global driving-noise spec (method/params identity).

        Returns:
            A length-``rank`` standard-normal latent vector, tile-independent.
        """
        seed = derive_seed(
            noise_spec.method, noise_spec.params_key, "structured", member_index
        )
        return np.asarray(np.random.default_rng(seed).standard_normal(rank))

    def draw(
        self,
        member_index: int,
        parts: Sequence[Any],
        support: object,
        noise_spec: NoiseSpec,
    ) -> list[np.ndarray]:
        """Return one member-seeded ``z_r`` per tile (each truncated to its rank)."""
        return [
            self.draw_one(member_index, p.distribution.fields.rank, noise_spec)
            for p in parts
        ]


def coherent_structured_field(
    factors: list[np.ndarray],
    weights: np.ndarray,
    member_index: int,
    noise_spec: NoiseSpec,
) -> np.ndarray:
    """Return a cross-tile-coherent structured field over the support (shared-basis driver).

    The shared-overlap-basis structured driver (design §5c, Option-2 realized). Each tile's
    factor is projected into one common orthonormal basis ``Q`` (QR of the stacked factors),
    symmetrically square-rooted there (``Aᵢ = (CᵢCᵢᵀ)^½``, ``Cᵢ = QᵀFᵢ``) to remove the
    SVD rotational ambiguity, and the weighted sum ``G = Σ wᵢ Q Aᵢ`` is driven by ONE shared
    member-seeded latent ``g``. Tiles therefore agree at shared points (no basis-orientation
    cancellation, no cross-seam derivative inflation) and the field's structured covariance
    is the weighted blend of the per-tile structured covariances — no per-point renormalization.

    Args:
        factors: Per-tile ``(n, rᵢ)`` factors at the support (rows zeroed where the tile
            does not cover the point).
        weights: ``(T, n)`` partition-of-unity weights.
        member_index: The ensemble member index (seeds the shared latent only).
        noise_spec: The global driving-noise spec (method/params identity for the seed).

    Returns:
        A length-``n`` coherent structured field (zeros if the stacked rank is 0).
    """
    n = weights.shape[1]
    cat = np.hstack(factors) if factors else np.zeros((n, 0))
    if cat.shape[1] == 0:
        return np.zeros(n)
    q, _ = np.linalg.qr(cat)  # (n, p) common orthonormal basis
    p = q.shape[1]
    g_sum = np.zeros((n, p))
    for i, f_i in enumerate(factors):
        if f_i.shape[1] == 0:
            continue
        c_i = q.T @ f_i  # (p, rᵢ)
        k_i = c_i @ c_i.T  # (p, p) structured covariance in Q-space
        evals, evecs = np.linalg.eigh(k_i)
        a_i = (evecs * np.sqrt(np.clip(evals, 0.0, None))) @ evecs.T  # symmetric sqrt
        g_sum += weights[i][:, None] * (q @ a_i)  # (n, p), aligned + weight-crossfaded
    seed = derive_seed(
        noise_spec.method, noise_spec.params_key, "structured-shared", member_index
    )
    g = np.random.default_rng(seed).standard_normal(p)
    return np.asarray(g_sum @ g)


class CoherentSampler:
    """Realizes coherent sample fields from Persisted reps + global driving noise."""

    def __init__(self, structured: StructuredNoiseSource | None = None) -> None:
        """Store the structured-noise source (defaults to member-only z_r).

        Args:
            structured: The structured (low-rank) noise driver; defaults to
                ``MemberSeededZr`` (Option 1).
        """
        self.structured: StructuredNoiseSource = structured or MemberSeededZr()

    def realize_one(
        self,
        *,
        mean: Field,
        factor: np.ndarray,
        residual: np.ndarray,
        points: Points,
        member_index: int,
        noise_spec: NoiseSpec,
    ) -> np.ndarray:
        """Realize one tile's coherent field: mean + B z_r + sqrt(d) z_diag.

        Args:
            mean: The tile mean at ``points`` (length n).
            factor: The low-rank factor ``B`` at ``points``, shape ``(n, r)``.
            residual: The diagonal residual ``d`` at ``points`` (length n, >= 0).
            points: The ``(n, 3)`` space-time points to realize at.
            member_index: The ensemble member index.
            noise_spec: The global driving-noise spec.

        Returns:
            The realized field, length n.
        """
        r = factor.shape[1]
        z_r = MemberSeededZr().draw_one(member_index, r, noise_spec)
        z_d = diagonal_noise(points, member_index, noise_spec)
        return np.asarray(mean + factor @ z_r + np.sqrt(residual) * z_d)


@runtime_checkable
class CoherentMemberDriver(Protocol):
    """Relocated coherence seam: one cross-tile-coherent, weight-crossfaded realization."""

    def crossfaded_member(
        self,
        parts: Sequence[Any],
        pts: Points,
        weights: np.ndarray,
        member_index: int,
        noise: NoiseSpec,
    ) -> np.ndarray:
        """Realize one coherent member over ``pts`` from the constituents + global noise."""
        ...


class LowRankSharedBasis:
    """OI driver: mean crossfade + shared-overlap-basis structured field + coherent diagonal."""

    def crossfaded_member(
        self,
        parts: Sequence[Any],
        pts: Points,
        weights: np.ndarray,
        member_index: int,
        noise: NoiseSpec,
    ) -> np.ndarray:
        """Realize one coherent member: mean blend + shared-basis struct + coherent diagonal."""
        n = pts.shape[0]
        means = np.zeros((len(parts), n))
        sqd = np.zeros((len(parts), n))
        cols: list[np.ndarray] = []
        for i, p in enumerate(parts):
            d = p.distribution
            idx = _nearest(d.grid, pts, d.time_days)
            means[i] = d.fields.mean.ravel()[idx]
            cols.append(d.fields.factor[idx] * (weights[i] > 0)[:, None])
            sqd[i] = np.sqrt(d.fields.residual[idx])
        mean_blend = (weights * means).sum(axis=0)
        diag_amp = (weights * sqd).sum(axis=0)
        struct = coherent_structured_field(cols, weights, member_index, noise)
        diag = diag_amp * diagonal_noise(pts, member_index, noise)
        return np.asarray(mean_blend + struct + diag)


_DRIVERS: dict[str, type] = {"lowrank+diag": LowRankSharedBasis}


def select_driver(sampler_spec: str) -> CoherentMemberDriver:
    """Pick the coherence driver by the persisted representation tag (never by method)."""
    return cast(CoherentMemberDriver, _DRIVERS[sampler_spec]())
