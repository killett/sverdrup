"""Sparse-precision persisted form: first-class beside low-rank, never reduced to a factor."""

from __future__ import annotations

from typing import cast

import numpy as np
import pytest

pytest.importorskip("sksparse")  # noqa: E402

from sverdrup.core.grid import GridSpec  # noqa: E402
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow  # noqa: E402
from sverdrup.core.parameters import ConstantProvider  # noqa: E402
from sverdrup.distributions.persisted import (  # noqa: E402
    PrecisionDistribution,
    PrecisionFields,
)
from sverdrup.distributions.reduction import (  # noqa: E402
    GMRFPrecisionReduction,
    select_reduction,
)
from sverdrup.methods.gmrf import MaternGMRF  # noqa: E402


def _grid():
    return GridSpec.lonlat(np.linspace(0.0, 6.0, 7), np.linspace(0.0, 6.0, 7))


def _dist():
    obs = ObsWindow.from_arrays(
        np.array([3.0]),
        np.array([3.0]),
        np.array([2.0]),
        np.array([1.0]),
        DiagonalErrorModel(np.array([1e-3])),
    )
    p = ConstantProvider(
        {"range": 300.0, "variance": 0.05, "temporal_taper_scale": 5.0}
    )
    return MaternGMRF().solve(obs, _grid(), p, 2.0)


def test_select_reduction_routes_gmrf_to_precision():
    # Behavior: a sparse-precision operator selects the precision reducer, not low-rank.
    # Bug caught: GMRF silently reduced to a low-rank factor (the failure this whole phase guards).
    assert isinstance(select_reduction(_dist()), GMRFPrecisionReduction)


def test_reduction_is_genuine_first_class_no_factor():
    # Behavior: GMRF persists Q + permutation + exact var; no low-rank factor anywhere.
    # Bug caught: a hidden randomized-SVD of the GMRF would defeat the validation's point.
    dist = _dist()
    pts = _grid().points(2.0)
    unit = GMRFPrecisionReduction().reduce(dist, pts, None, rank=20, seed=1)
    assert isinstance(unit.base_fields, PrecisionFields)
    assert not hasattr(unit.base_fields, "factor")
    assert unit.base_fields.sampler_spec == "sparse-precision"


def test_precision_distribution_marginal_var_exact():
    # Behavior: the stored marginal variance equals the operator's exact selective-inverse diag.
    dist = _dist()
    pts = _grid().points(2.0)
    unit = GMRFPrecisionReduction().reduce(dist, pts, None, rank=20, seed=1)
    pd = PrecisionDistribution(
        _grid(), cast(PrecisionFields, unit.base_fields), dist.provenance, 2.0
    )
    np.testing.assert_allclose(
        pd.marginal_variance().ravel(), dist.cov_op.marginal_var(pts), rtol=1e-10
    )


def test_precision_distribution_posterior_cov_columns_delegate():
    # Behavior: the distribution exposes the factor's full Q^-1 columns for kriging conditioning.
    # Bug caught: the kriging driver would have no representation-level handle on cross-cov,
    #   forcing it to reach past the persisted rep into a raw factor.
    dist = _dist()
    pts = _grid().points(2.0)
    unit = GMRFPrecisionReduction().reduce(dist, pts, None, rank=20, seed=1)
    pd = PrecisionDistribution(
        _grid(), cast(PrecisionFields, unit.base_fields), dist.provenance, 2.0
    )
    shared = np.array([4, 17, 40])
    cols = pd.posterior_cov_columns(shared)
    q = pd.fields.precision
    dense = np.linalg.inv(q.toarray())  # type: ignore[attr-defined]
    np.testing.assert_allclose(cols, dense[:, shared], rtol=1e-9)


def test_precision_distribution_eval_points_have_no_factor():
    # Behavior: off-grid eval predictions carry (mean, var), factor is None for GMRF.
    # Bug caught: forcing GMRF eval rows into the low-rank basis (representation leak).
    dist = _dist()
    pts = _grid().points(2.0)
    evals = np.array([[3.5, 3.5, 2.0]])
    unit = GMRFPrecisionReduction().reduce(dist, pts, evals, rank=20, seed=1)
    assert unit.eval_points is not None
    assert unit.eval_points.factor is None
    np.testing.assert_allclose(
        unit.eval_points.variance, dist.cov_op.marginal_var(evals), rtol=1e-6
    )
