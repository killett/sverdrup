"""Cross-tile coherent sampler via white-noise conditioning (design section 5)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

import numpy as np

from sverdrup.core.seeding import derive_seed
from sverdrup.core.types import Field, Points


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
