"""GMRF method: EXACT sparse-precision operator, temporal-taper conditioning, off-grid W."""

from __future__ import annotations

from typing import Any, cast

import numpy as np
import pytest

pytest.importorskip("sksparse")  # noqa: E402

from sverdrup.core.grid import GridSpec  # noqa: E402
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow  # noqa: E402
from sverdrup.core.parameters import ConstantProvider  # noqa: E402
from sverdrup.core.types import CovFidelity  # noqa: E402
from sverdrup.methods.gmrf import MaternGMRF  # noqa: E402
from sverdrup.methods.registry import METHODS  # noqa: E402


def _grid():
    return GridSpec.lonlat(np.linspace(0.0, 6.0, 7), np.linspace(0.0, 6.0, 7))


def _params(taper=5.0):
    return ConstantProvider(
        {"range": 300.0, "variance": 0.05, "temporal_taper_scale": taper}
    )


def _obs(value=1.0, t=2.0):
    return ObsWindow.from_arrays(
        np.array([3.0]),
        np.array([3.0]),
        np.array([t]),
        np.array([value]),
        DiagonalErrorModel(np.array([1e-3])),
    )


def test_registered_and_capability():
    # Behavior: GMRF plugs into the registry like OI; EXACT, sparse-precision.
    assert "gmrf" in METHODS
    dist = MaternGMRF().solve(_obs(), _grid(), _params(), 2.0)
    assert dist.cov_op.fidelity is CovFidelity.EXACT
    assert cast(Any, dist.cov_op).representation == "sparse-precision"


def test_marginal_var_is_exact_selective_inverse():
    # Behavior: gridded marginal variance == diag(Q_post^-1), exactly.
    # Bug caught: a sampled/approx variance would make calibration dishonest.
    dist = MaternGMRF().solve(_obs(), _grid(), _params(), 2.0)
    pts = _grid().points(2.0)
    var = dist.cov_op.marginal_var(pts)
    q = cast(Any, dist.cov_op).q_post.toarray()
    np.testing.assert_allclose(var, np.diag(np.linalg.inv(q)), rtol=1e-8)


def test_posterior_mean_pulled_toward_obs():
    # Behavior: conditioning on one high obs raises the nearest-node mean above zero.
    # Bug caught: dropping A^T R^-1 y leaves the prior-mean (zero) field.
    dist = MaternGMRF().solve(_obs(value=1.0), _grid(), _params(), 2.0)
    j = i = 3
    assert dist.mean[j, i] > 0.05


def test_offgrid_var_uses_W_selective_inverse_not_interpolation():
    # Behavior: off-grid eval var == diag(W Sigma W^T) from stencil entries, == dense.
    # Bug caught: interpolating the marginal-variance map (invariant 7 violation).
    dist = MaternGMRF().solve(_obs(), _grid(), _params(), 2.0)
    ep = np.array([[3.5, 3.5, 2.0]])
    var = dist.cov_op.marginal_var(ep)
    from sverdrup.methods.gmrf_grid import bilinear_weights

    w = bilinear_weights(_grid(), ep).toarray()
    dense = w @ np.linalg.inv(cast(Any, dist.cov_op).q_post.toarray()) @ w.T
    np.testing.assert_allclose(var, np.diag(dense), rtol=1e-6)


def test_temporal_taper_inflates_far_obs():
    # Behavior: an obs far in time conditions the field less than a near one.
    # Bug caught: ignoring the time offset over-conditions from far-in-time obs.
    near = MaternGMRF().solve(_obs(t=2.0), _grid(), _params(taper=2.0), 2.0)
    far = MaternGMRF().solve(_obs(t=10.0), _grid(), _params(taper=2.0), 2.0)
    assert near.mean[3, 3] > far.mean[3, 3]


def test_diag_fastpath_equals_slowpath_on_native_nodes():
    # Behavior (C3): the cached _diag equals diag(W Σ W^T) computed through the
    #   projection's weights() on the native node points — the fast path is the slow path.
    # Bug caught: the projection layer drifting from the cached diagonal, producing a
    #   plausible-but-wrong marginal variance that no other test would notice.
    op = cast(Any, MaternGMRF().solve(_obs(), _grid(), _params(), 2.0).cov_op)
    nodes = op.projection.node_points(op.time_days)
    w = op.projection.weights(nodes)
    slow = np.asarray((w @ op._sinv @ w.T).diagonal())
    np.testing.assert_allclose(op._diag, slow, rtol=1e-9, atol=1e-12)


def test_operator_carries_prior_precision():
    # Behavior (Stage B prep): the operator persists q_prior for the strip-prior draw.
    # Bug caught: a dropped prior precision leaves Stage B unable to assemble the strip sub-GMRF.
    op = cast(Any, MaternGMRF().solve(_obs(), _grid(), _params(), 2.0).cov_op)
    assert op.q_prior is not None
    assert op.q_prior.shape == op.q_post.shape
