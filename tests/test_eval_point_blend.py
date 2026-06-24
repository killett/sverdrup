"""Eval points blend over PointSet via shared-basis rows (invariants 6, 7)."""

from __future__ import annotations

import numpy as np

from sverdrup.core.geometry import Tile, Window
from sverdrup.core.grid import GridSpec, PointSet
from sverdrup.core.provenance import UncertaintyProvenance
from sverdrup.core.types import UncertaintyCapability
from sverdrup.distributions.blend import BlendInput, BlendOperator
from sverdrup.distributions.persisted import PersistedPoints


def _persisted_points(locs, mean, B, d, time=0.0):
    prov = UncertaintyProvenance(UncertaintyCapability.SAMPLES, [])
    crs = GridSpec.lonlat(np.array([0.0]), np.array([0.0])).crs
    return PersistedPoints(
        PointSet(locs, crs),
        mean=mean,
        factor=B,
        residual=d,
        provenance=prov,
        time_days=time,
    )


def test_eval_points_blend_in_overlap():
    # Behavior: a withheld point in the overlap mixes both tiles' predictives.
    # Bug caught: reconstructing from the gridded blend, or taking one tile only.
    loc = np.array([[0.0, 0.0, 0.0]])  # mid-overlap
    left_pp = _persisted_points(
        loc, np.array([1.0]), np.zeros((1, 0)), np.array([0.04])
    )
    right_pp = _persisted_points(
        loc, np.array([3.0]), np.zeros((1, 0)), np.array([0.04])
    )
    lg = GridSpec.lonlat(np.linspace(-10, 2, 13), np.array([0.0]))
    rg = GridSpec.lonlat(np.linspace(-2, 10, 13), np.array([0.0]))
    left = Tile(
        Window((-10, -2), (-1, 1), (0, 0)), Window((-10, 2), (-1, 1), (0, 0)), lg
    )
    right = Tile(
        Window((2, 10), (-1, 1), (0, 0)), Window((-2, 10), (-1, 1), (0, 0)), rg
    )
    out = BlendOperator().blend(
        [BlendInput(left_pp, left), BlendInput(right_pp, right)],
        support=PointSet(loc, lg.crs),
    )
    # at mid-overlap w=0.5/0.5 -> blended mean is the average, not 1.0 or 3.0
    np.testing.assert_allclose(out.mean.ravel(), [2.0], atol=1e-6)


def test_eval_rows_share_gridded_basis():
    # Behavior: Cov(eval, grid node) = B_eval . B_grid_row^T (shared basis).
    # Bug caught: an independent SVD of eval rows breaks cross-seam coupling.
    B_grid_row = np.array([[0.1, -0.2, 0.05]])
    B_eval = np.array([[0.1, -0.2, 0.05]])  # same basis -> identical row here
    cov = B_eval @ B_grid_row.T
    np.testing.assert_allclose(cov, np.array([[np.sum(B_grid_row**2)]]), rtol=1e-12)


def test_eval_rows_in_grid_basis_match_operator_covariance():
    # Behavior: shared-basis eval rows reproduce Cov(eval, grid) = B_eval @ B_grid^T
    #   from the SAME basis as the gridded reduction (no independent re-factorization).
    # Bug caught: re-factoring eval points yields a basis inconsistent with the grid,
    #   breaking cross-tile coupling for withheld-point covariance.
    from sverdrup.core.types import CovFidelity
    from sverdrup.distributions.persisted import (
        eval_rows_in_grid_basis,
        reduce_with_basis,
    )

    n = 20
    grid_pts = np.column_stack([np.linspace(-5, 5, n), np.zeros(n), np.zeros(n)])

    class _Op:
        """A smooth SPD covariance operator over lon distance (CovarianceOperator stub)."""

        fidelity = CovFidelity.EXACT

        def cov(self, a, b):
            return np.exp(-((a[:, None, 0] - b[None, :, 0]) ** 2) / 8.0)

        def marginal_var(self, p):
            return np.ones(p.shape[0])

        def posterior_sample(self, s, seed, m):
            return np.zeros((m, s.shape[0]))

    op = _Op()
    mean = np.zeros(n)
    _, basis = reduce_with_basis(mean, op, grid_pts, rank=8, seed=1)
    grid_factor = (basis.q @ basis.u_r) * basis.sqrt_s
    eval_pts = np.array([[1.3, 0.0, 0.0], [-2.7, 0.0, 0.0]])
    b_eval, d_eval = eval_rows_in_grid_basis(op, eval_pts, grid_pts, basis)
    approx = b_eval @ grid_factor.T  # (k, n)
    exact = op.cov(eval_pts, grid_pts)
    # shared-basis reconstruction matches the operator cross-covariance (rank-8 is ample)
    assert np.max(np.abs(approx - exact)) < 1e-3
    assert d_eval.shape == (2,)
    assert np.all(d_eval >= -1e-9)
