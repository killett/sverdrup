"""ReductionStrategy: dispatch by live-operator representation; OI path unchanged."""

from __future__ import annotations

from typing import cast

import numpy as np

from sverdrup.core.grid import GridSpec
from sverdrup.distributions.persisted import PersistedFields, reduce_with_basis
from sverdrup.distributions.reduction import (
    EmpiricalReduction,
    LowRankReduction,
    select_reduction,
)


class _FakeOp:
    representation = "lowrank+diag"
    fidelity = None

    def __init__(self, n):
        rng = np.random.default_rng(0)
        b = rng.standard_normal((n, 4))
        self._p = b @ b.T + np.eye(n) * 0.1

    def cov(self, a, b):
        return self._p[: a.shape[0]][:, : b.shape[0]]

    def marginal_var(self, a):
        return np.diag(self._p)[: a.shape[0]]

    def posterior_mean(self, pts):
        return np.zeros(pts.shape[0])


class _FakeGaussian:
    def __init__(self, grid, op):
        self.grid = grid
        self.mean = np.zeros(grid.shape)
        self.cov_op = op
        self.time_days = 0.0


class _FakeEnsemble:
    def __init__(self, grid, samples):
        self.grid = grid
        self.samples = samples
        self.time_days = 0.0


def _grid():
    return GridSpec.lonlat(np.linspace(0, 4, 5), np.linspace(0, 4, 5))


def test_select_reduction_dispatches_on_representation():
    # Behavior: selection keys on the live operator's representation, not method identity.
    # Bug caught: dispatching on hasattr(cov_op) alone would route a future sparse-precision
    #   operator (which also wraps in a Gaussian dist) to the low-rank reducer.
    g = _grid()
    assert isinstance(select_reduction(_FakeGaussian(g, _FakeOp(25))), LowRankReduction)
    samples = np.random.default_rng(1).standard_normal((8, 5, 5))
    assert isinstance(select_reduction(_FakeEnsemble(g, samples)), EmpiricalReduction)


def test_lowrank_reduction_matches_reduce_with_basis():
    # Behavior: the strategy's base reduction equals the free-function reduction exactly.
    # Bug caught: any drift in factor/residual/marginal_variance vs the Phase-2 path.
    g = _grid()
    dist = _FakeGaussian(g, _FakeOp(25))
    pts = g.points(0.0)
    unit = LowRankReduction().reduce(dist, pts, None, rank=6, seed=3)
    ref, _ = reduce_with_basis(dist.mean, dist.cov_op, pts, rank=6, seed=3)
    base = cast(PersistedFields, unit.base_fields)
    np.testing.assert_array_equal(base.factor, ref.factor)
    np.testing.assert_array_equal(base.residual, ref.residual)
    assert base.sampler_spec == "lowrank+diag"


def test_lowrank_reduction_builds_eval_rows_in_basis():
    # Behavior: eval rows come from eval_rows_in_grid_basis (shared SVD basis), exact var.
    # Bug caught: re-factoring eval rows independently breaks cross-tile eval blending.
    g = _grid()
    dist = _FakeGaussian(g, _FakeOp(25))
    pts = g.points(0.0)
    evals = np.array([[1.3, 1.7, 0.0], [2.1, 0.4, 0.0]])
    unit = LowRankReduction().reduce(dist, pts, evals, rank=6, seed=3)
    assert unit.eval_points is not None
    assert unit.eval_points.factor is not None
    assert unit.eval_points.factor.shape == (2, 6)
    np.testing.assert_allclose(
        unit.eval_points.variance, dist.cov_op.marginal_var(evals)
    )
