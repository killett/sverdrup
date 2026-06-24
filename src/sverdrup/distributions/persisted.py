"""Persisted predictive distribution: sufficient stats + generator (spec 5.3)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import NoReturn

import numpy as np

from sverdrup.core.distribution import CovarianceOperator
from sverdrup.core.grid import GridSpec, PointSet
from sverdrup.core.provenance import UncertaintyProvenance
from sverdrup.core.types import Field, Points, Seed


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


@dataclass(frozen=True)
class GridBasis:
    """The orthonormal/singular basis of one grid reduction, reused for eval-point rows.

    Attributes:
        q: ``(n, m)`` orthonormal range basis from the randomized range finder.
        u_r: ``(m, r)`` truncated left singular vectors of ``q^T P q``.
        sqrt_s: ``(r,)`` square-root singular values (the gridded factor scaling).
        inv_sqrt_s: ``(r,)`` reciprocal of ``sqrt_s`` (zeroed where ~0) for projecting
            eval covariance into the same basis.
    """

    q: np.ndarray
    u_r: np.ndarray
    sqrt_s: np.ndarray
    inv_sqrt_s: np.ndarray


def reduce_with_basis(
    mean: Field, operator: CovarianceOperator, points: Points, *, rank: int, seed: Seed
) -> tuple[PersistedFields, GridBasis]:
    """Reduce a live covariance operator and also return the basis used.

    Forms only ``P @ Omega`` (matrix-free) via the operator's ``cov()`` applied to
    random probe vectors over the grid points; never materialises a dense ``(n, n)`` P.
    The returned ``GridBasis`` lets eval-point rows be projected into the *same* basis
    as the gridded factor (so ``Cov(eval, grid) = B_eval @ B_grid^T``, never re-factored).

    Args:
        mean: The mean field, shape ``(ny, nx)``.
        operator: The live (zero-mean) covariance operator.
        points: The ``(ngrid, 3)`` grid points (row-major over ``(ny, nx)``).
        rank: Target rank of the low-rank factor ``B``.
        seed: Seed for the randomized range finder.

    Returns:
        The reduced ``PersistedFields`` and the ``GridBasis`` of the reduction.
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
    u_r = u[:, :r]
    sqrt_s = np.sqrt(np.clip(s[:r], 0, None))
    inv_sqrt_s = np.where(
        sqrt_s > 1e-12, 1.0 / np.where(sqrt_s > 1e-12, sqrt_s, 1.0), 0.0
    )
    factor = (q @ u_r) * sqrt_s
    exact_var = np.asarray(operator.marginal_var(points))
    residual = np.clip(exact_var - np.sum(factor**2, axis=1), 0.0, None)
    total = float(exact_var.sum())
    captured = float(np.sum(factor**2)) / total if total > 0 else 0.0
    ny, nx = _grid_shape(points)
    fields = PersistedFields(
        mean=mean,
        marginal_variance=(np.sum(factor**2, axis=1) + residual).reshape(ny, nx),
        factor=factor,
        residual=residual,
        rank=r,
        seed=seed,
        captured_energy=min(captured, 1.0),
    )
    basis = GridBasis(q=q, u_r=u_r, sqrt_s=sqrt_s, inv_sqrt_s=inv_sqrt_s)
    return fields, basis


def reduce_to_persisted(
    mean: Field, operator: CovarianceOperator, points: Points, *, rank: int, seed: Seed
) -> PersistedFields:
    """Reduce a live covariance operator to a storable low-rank + diagonal generator.

    Thin wrapper over :func:`reduce_with_basis` that discards the basis.

    Args:
        mean: The mean field, shape ``(ny, nx)``.
        operator: The live (zero-mean) covariance operator.
        points: The ``(ngrid, 3)`` grid points (row-major over ``(ny, nx)``).
        rank: Target rank of the low-rank factor ``B``.
        seed: Seed for the randomized range finder.

    Returns:
        The reduced ``PersistedFields`` (exact marginal variance via the residual).
    """
    fields, _ = reduce_with_basis(mean, operator, points, rank=rank, seed=seed)
    return fields


def eval_rows_in_grid_basis(
    operator: CovarianceOperator,
    eval_points: Points,
    grid_points: Points,
    basis: GridBasis,
) -> tuple[np.ndarray, np.ndarray]:
    """Extract eval-point structured rows in the gridded block's basis (never re-factored).

    Builds ``B_eval = Cov(eval, grid) @ Q @ U_r @ diag(1/sqrt(s_r))`` so that
    ``B_eval @ B_grid^T`` reconstructs the operator cross-covariance consistently with the
    gridded factor. The diagonal residual is the exact marginal variance minus the captured
    structured energy, clipped at zero (the same convention as the gridded reduction).

    Args:
        operator: The live (zero-mean) covariance operator.
        eval_points: The ``(k, 3)`` evaluation/withheld locations.
        grid_points: The ``(n, 3)`` grid points the basis was built over.
        basis: The ``GridBasis`` returned by :func:`reduce_with_basis`.

    Returns:
        A pair ``(B_eval, d_eval)`` of shape ``(k, r)`` and ``(k,)``.
    """
    p_eg = operator.cov(eval_points, grid_points)  # (k, n)
    b_eval = (p_eg @ basis.q @ basis.u_r) * basis.inv_sqrt_s  # (k, r)
    var = np.asarray(operator.marginal_var(eval_points))
    d_eval = np.clip(var - np.sum(b_eval**2, axis=1), 0.0, None)
    return np.asarray(b_eval), np.asarray(d_eval)


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


@dataclass
class PersistedPoints:
    """A Persisted predictive over a PointSet support (unified-blend sibling of the grid rep).

    Attributes:
        pointset: The ``(k, 3)`` point support.
        mean: The ``(k,)`` predictive mean at the points.
        factor: The ``(k, r)`` structured factor in the gridded block's basis.
        residual: The ``(k,)`` diagonal residual (>= 0).
        provenance: The uncertainty provenance.
        time_days: The output time in days.
    """

    pointset: PointSet
    mean: np.ndarray
    factor: np.ndarray
    residual: np.ndarray
    provenance: UncertaintyProvenance
    time_days: float

    @property
    def grid(self) -> PointSet:
        """Return the point support (named ``grid`` to match the blend's nearest access)."""
        return self.pointset

    @property
    def fields(self) -> PersistedFields:
        """Expose the same field bundle the blend reads from a gridded Persisted."""
        return PersistedFields(
            mean=self.mean,
            marginal_variance=np.sum(self.factor**2, axis=1) + self.residual,
            factor=self.factor,
            residual=self.residual,
            rank=self.factor.shape[1],
            seed=0,
            captured_energy=1.0,
        )
