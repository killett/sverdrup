"""Regular-grid Matérn SPDE topology: precision stencil, bilinear projection (spec §5.1).

Precision-node space (the GMRF lattice) and output-grid space are kept conceptually
distinct even though they coincide here. Every field/covariance is read off the precision
through a ``Projection``: the gridded block is ``W = identity-on-nodes``; off-grid eval is
``W = bilinear``. A later FEM phase supplies a different projection + mesh assembly only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import numpy as np
from scipy import sparse  # type: ignore[import-untyped]

from sverdrup.core.grid import GridSpec
from sverdrup.core.types import Points

_DEG2KM = 111.195
_NU = 1.0  # alpha = 2 in 2-D -> nu = alpha - d/2 = 1


def kappa_from_range(range_km: float | np.ndarray) -> float | np.ndarray:
    """Return κ for an empirical correlation range (km): ``range = sqrt(8ν)/κ`` (ν=1).

    Polymorphic: a scalar returns a ``float`` (stationary path); a ``(ny, nx)`` range field
    returns the elementwise κ field (nonstationary path; spatially-varying ``Q`` coefficients).
    """
    k = np.sqrt(8.0 * _NU) / np.asarray(range_km, dtype=float)
    return float(k) if k.ndim == 0 else np.asarray(k)


def range_from_kappa(kappa: float | np.ndarray) -> float | np.ndarray:
    """Return the empirical correlation range (km) for κ (inverse of :func:`kappa_from_range`)."""
    r = np.sqrt(8.0 * _NU) / np.asarray(kappa, dtype=float)
    return float(r) if r.ndim == 0 else np.asarray(r)


def _node_spacing_km(grid: GridSpec) -> tuple[np.ndarray, np.ndarray]:
    """Per-node (dx, dy) spacing in km over the grid (geographic uses cos-lat for dx)."""
    lon, lat = grid._lonlat_nodes()
    dy = np.full(grid.shape, np.gradient(grid.y).mean() * _DEG2KM)
    dx = np.gradient(grid.x).mean() * _DEG2KM * np.cos(np.deg2rad(lat))
    return dx, dy


def _laplacian(grid: GridSpec) -> sparse.csc_matrix:
    """5-point finite-difference Laplacian (Neumann edges) on the grid nodes, in km^-2."""
    ny, nx = grid.shape
    n = ny * nx
    dx, dy = _node_spacing_km(grid)
    dx2 = (dx.ravel()) ** 2
    dy2 = (dy.ravel()) ** 2
    rows, cols, vals = [], [], []

    def idx(j: int, i: int) -> int:
        return j * nx + i

    for j in range(ny):
        for i in range(nx):
            c = idx(j, i)
            diag = 0.0
            for dj, di, h2 in ((0, 1, dx2), (0, -1, dx2), (1, 0, dy2), (-1, 0, dy2)):
                jj, ii = j + dj, i + di
                if 0 <= jj < ny and 0 <= ii < nx:
                    w = 1.0 / h2[c]
                    rows.append(c)
                    cols.append(idx(jj, ii))
                    vals.append(w)
                    diag -= w
            rows.append(c)
            cols.append(c)
            vals.append(diag)
    return sparse.csc_matrix((vals, (rows, cols)), shape=(n, n))


def matern_precision(
    grid: GridSpec, kappa: float | np.ndarray, tau: float
) -> sparse.csc_matrix:
    """Assemble the Matérn SPDE precision ``Q = (1/tau)·(κ²I − Δ)²`` (α=2, ν=1).

    Args:
        grid: The regular grid the lattice lives on.
        kappa: Scalar κ, or a ``(ny, nx)`` κ field (nonstationary; spatially-varying coeffs).
        tau: Marginal-variance scaling (larger τ -> smaller precision -> larger variance).

    Returns:
        A symmetric SPD ``(n, n)`` CSC precision over the ``n = ny*nx`` nodes.
    """
    n = grid.shape[0] * grid.shape[1]
    lap = _laplacian(grid)
    if np.isscalar(kappa):
        k2 = sparse.identity(n, format="csc") * float(cast(float, kappa)) ** 2
    else:
        k2 = sparse.diags(np.asarray(kappa).ravel() ** 2, format="csc")
    a = k2 - lap  # (κ²I − Δ)
    q = (a.T @ a) / float(tau)
    return sparse.csc_matrix(0.5 * (q + q.T))  # symmetrize against round-off


def bilinear_weights(grid: GridSpec, pts: Points) -> sparse.csr_matrix:
    """Return the sparse ``(k, n)`` bilinear interpolation operator grid-nodes -> ``pts``.

    Rows sum to 1; a point on a node is a unit selector (<=4 nonzeros otherwise). This is
    the ONE primitive feeding both ``A`` (grid->obs conditioning) and ``W`` (grid->eval).
    """
    lon, lat = grid._lonlat_nodes()
    xs, ys = lon[0, :], lat[:, 0]
    nx, ny = xs.size, ys.size
    k = pts.shape[0]
    rows, cols, vals = [], [], []
    for r in range(k):
        ix = int(np.clip(np.searchsorted(xs, pts[r, 0]) - 1, 0, nx - 2))
        iy = int(np.clip(np.searchsorted(ys, pts[r, 1]) - 1, 0, ny - 2))
        tx = (
            0.0
            if xs[ix + 1] == xs[ix]
            else (pts[r, 0] - xs[ix]) / (xs[ix + 1] - xs[ix])
        )
        ty = (
            0.0
            if ys[iy + 1] == ys[iy]
            else (pts[r, 1] - ys[iy]) / (ys[iy + 1] - ys[iy])
        )
        tx = float(np.clip(tx, 0.0, 1.0))
        ty = float(np.clip(ty, 0.0, 1.0))
        for dj, wy in ((0, 1 - ty), (1, ty)):
            for di, wx in ((0, 1 - tx), (1, tx)):
                wgt = wx * wy
                if wgt > 0:
                    rows.append(r)
                    cols.append((iy + dj) * nx + (ix + di))
                    vals.append(wgt)
    w = sparse.csr_matrix((vals, (rows, cols)), shape=(k, nx * ny))
    # renormalize rows (guards clipped/edge points) so each row sums to 1
    rs = np.asarray(w.sum(axis=1)).ravel()
    rs[rs == 0] = 1.0
    return sparse.diags(1.0 / rs) @ w


@dataclass(frozen=True)
class GridIdentityProjection:
    """The gridded node projection: ``W = bilinear`` (identity on nodes); ``(ny,nx)`` fields."""

    grid: GridSpec

    @property
    def node_space(self) -> GridSpec:
        """Return the node layout (the grid)."""
        return self.grid

    @property
    def matrix(self) -> sparse.csr_matrix:
        """Return the ``(n, n)`` identity projection over the grid nodes (legacy hook)."""
        n = self.grid.shape[0] * self.grid.shape[1]
        return sparse.identity(n, format="csr")

    def weights(self, pts: Points) -> sparse.csr_matrix:
        """Return the bilinear ``W`` to ``pts`` (a unit selector on nodes ⇒ identity there)."""
        return bilinear_weights(self.grid, pts)

    def field_shape(self) -> tuple[int, ...]:
        """Return ``(ny, nx)``."""
        return self.grid.shape

    def node_points(self, time_days: float) -> Points:
        """Return the grid node coordinates at ``time_days``."""
        return self.grid.points(time_days)

    def assert_adjacency(self, q: sparse.spmatrix) -> None:
        """Delegate to the 5-point-pattern precondition for the grid."""
        from sverdrup.methods.gmrf_linalg import assert_adjacency_in_pattern

        assert_adjacency_in_pattern(q.tocsc(), self.grid.shape)


@dataclass(frozen=True)
class BilinearProjection:
    """The off-grid read-off: bilinear ``W`` from grid nodes to fixed query points."""

    grid: GridSpec
    pts: Points

    @property
    def node_space(self) -> GridSpec:
        """Return the node layout (the grid)."""
        return self.grid

    @property
    def matrix(self) -> sparse.csr_matrix:
        """Return the ``(k, n)`` bilinear projection to ``pts`` (legacy hook)."""
        return bilinear_weights(self.grid, self.pts)

    def weights(self, pts: Points) -> sparse.csr_matrix:
        """Return the bilinear ``W`` to ``pts`` (ignores the stored ``self.pts``)."""
        return bilinear_weights(self.grid, pts)

    def field_shape(self) -> tuple[int, ...]:
        """Return ``(k,)`` — the number of fixed query points."""
        return (self.pts.shape[0],)

    def node_points(self, time_days: float) -> Points:
        """Return the grid node coordinates at ``time_days``."""
        return self.grid.points(time_days)

    def assert_adjacency(self, q: sparse.spmatrix) -> None:
        """Delegate to the 5-point-pattern precondition for the grid."""
        from sverdrup.methods.gmrf_linalg import assert_adjacency_in_pattern

        assert_adjacency_in_pattern(q.tocsc(), self.grid.shape)
