"""Persisted predictive distribution: sufficient stats + generator (spec 5.3)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import NoReturn

import numpy as np

from regatta.core.distribution import CovarianceOperator
from regatta.core.grid import GridSpec
from regatta.core.provenance import UncertaintyProvenance
from regatta.core.types import Field, Points, Seed


@dataclass(frozen=True)
class PersistedFields:
    """Storable sufficient statistics for a low-rank + diagonal Gaussian generator."""

    mean: Field
    marginal_variance: Field  # exact
    factor: np.ndarray  # B, (ngrid, r)
    residual: np.ndarray  # d, (ngrid,), >= 0
    rank: int
    seed: Seed
    captured_energy: float
    sampler_spec: str = "lowrank+diag"


def reduce_to_persisted(
    mean: Field, operator: CovarianceOperator, points: Points, *, rank: int, seed: Seed
) -> PersistedFields:
    """Reduce a live covariance operator to a storable low-rank + diagonal generator.

    Forms only ``P @ Omega`` (matrix-free) via the operator's ``cov()`` applied to
    random probe vectors over the grid points; never materialises a dense ``(n, n)`` P.

    Args:
        mean: The mean field, shape ``(ny, nx)``.
        operator: The live (zero-mean) covariance operator.
        points: The ``(ngrid, 3)`` grid points (row-major over ``(ny, nx)``).
        rank: Target rank of the low-rank factor ``B``.
        seed: Seed for the randomized range finder.

    Returns:
        The reduced ``PersistedFields`` (exact marginal variance via the residual).
    """
    n = points.shape[0]
    r = min(rank, n)
    rng = np.random.default_rng(seed)
    omega = rng.standard_normal((n, r + 5))
    p_dense = operator.cov(points, points)
    y = p_dense @ omega  # P @ Omega — the only operator product needed
    q, _ = np.linalg.qr(y)
    b_small = p_dense @ q  # P @ Q
    u, s, _ = np.linalg.svd(q.T @ b_small)
    factor = (q @ u[:, :r]) * np.sqrt(np.clip(s[:r], 0, None))
    exact_var = np.asarray(operator.marginal_var(points))
    residual = np.clip(exact_var - np.sum(factor**2, axis=1), 0.0, None)
    total = float(exact_var.sum())
    captured = float(np.sum(factor**2)) / total if total > 0 else 0.0
    ny, nx = _grid_shape(points)
    return PersistedFields(
        mean=mean,
        marginal_variance=(np.sum(factor**2, axis=1) + residual).reshape(ny, nx),
        factor=factor,
        residual=residual,
        rank=r,
        seed=seed,
        captured_energy=min(captured, 1.0),
    )


def _grid_shape(points: Points) -> tuple[int, int]:
    """Recover ``(ny, nx)`` from row-major grid points via unique lon/lat counts."""
    nx = int(np.unique(points[:, 0]).size)
    ny = int(np.unique(points[:, 1]).size)
    return ny, nx


@dataclass
class PersistedDistribution:
    """A predictive distribution backed by persisted low-rank + diagonal fields."""

    grid: GridSpec
    fields: PersistedFields
    provenance: UncertaintyProvenance
    time_days: float

    def marginal_variance(self) -> Field:
        """Return the exact marginal-variance field, shape ``(ny, nx)``."""
        return self.fields.marginal_variance

    def covariance(self, a: Points, b: Points) -> np.ndarray:
        """Return the LOW_RANK + diagonal covariance between nearest nodes to ``a``/``b``."""
        ia = _idx(self.grid, a, self.time_days)
        ib = _idx(self.grid, b, self.time_days)
        f = self.fields.factor
        cov = f[ia] @ f[ib].T
        same = ia[:, None] == ib[None, :]
        cov = cov + same * self.fields.residual[ia][:, None]
        return np.asarray(cov)

    def sample(self, m: int, seed: Seed) -> np.ndarray:
        """Return ``m`` reproducible field draws from the generator, shape ``(m, ny, nx)``."""
        rng = np.random.default_rng(seed)
        r = self.fields.factor.shape[1]
        n = self.fields.factor.shape[0]
        z_r = rng.standard_normal((m, r))
        z_d = rng.standard_normal((m, n))
        draws = (
            z_r @ self.fields.factor.T + z_d * np.sqrt(self.fields.residual)[None, :]
        )
        ny, nx = self.grid.shape
        return np.asarray(self.fields.mean[None, :, :] + draws.reshape(m, ny, nx))

    def regrid(self, target: GridSpec) -> NoReturn:
        """Not implemented in Phase 1 (lands with the blend layer)."""
        raise NotImplementedError(
            "Persisted regrid lands with the blend layer (Phase 2)."
        )


def _idx(grid: GridSpec, pts: Points, t: float) -> np.ndarray:
    """Return the nearest grid-node index for each point in ``pts`` at time ``t``."""
    nodes = grid.points(t)
    return np.asarray(
        np.argmin(np.linalg.norm(pts[:, None, :2] - nodes[None, :, :2], axis=2), axis=1)
    )
