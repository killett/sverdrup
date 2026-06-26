"""Regular-grid GMRF topology: (kappa^2 - Laplacian)^2 precision, bilinear W, projections."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("sksparse")  # noqa: E402

from scipy import sparse  # type: ignore[import-untyped]  # noqa: E402

from sverdrup.core.grid import GridSpec  # noqa: E402
from sverdrup.methods.gmrf_grid import (  # noqa: E402
    BilinearProjection,
    GridIdentityProjection,
    bilinear_weights,
    kappa_from_range,
    matern_precision,
    range_from_kappa,
)


def _grid():
    return GridSpec.lonlat(np.linspace(0.0, 9.0, 10), np.linspace(0.0, 9.0, 10))


def test_precision_is_symmetric_spd():
    # Behavior: Q = (kappa^2 I - Delta)^2 (+ tau scaling) is symmetric positive definite.
    # Bug caught: an asymmetric stencil assembly (wrong neighbour weighting) -> CHOLMOD fails.
    q = matern_precision(_grid(), kappa=0.3, tau=1.0)
    assert sparse.issparse(q)
    assert (abs(q - q.T)).max() < 1e-10
    # SPD: smallest eigenvalue of a small dense copy > 0
    w = np.linalg.eigvalsh(q.toarray())
    assert w.min() > 0.0


def test_bilinear_weights_partition_and_stencil():
    # Behavior: W rows sum to 1 with <=4 nonzeros; on-node points are unit selectors.
    # Bug caught: a normalization bug biases the eval-point mean; a wide stencil breaks
    #   the Takahashi adjacency precondition.
    g = _grid()
    pts = np.array([[2.5, 3.5, 0.0], [4.0, 4.0, 0.0]])  # off-node, then on-node
    w = bilinear_weights(g, pts)
    assert w.shape == (2, 100)
    np.testing.assert_allclose(np.asarray(w.sum(axis=1)).ravel(), 1.0, rtol=1e-12)
    assert w[0].nnz <= 4
    assert w[1].nnz == 1  # exact node -> selector


def test_projection_identity_and_bilinear():
    # Behavior: gridded block is W=identity-on-nodes; off-grid is the bilinear W.
    # Bug caught: baking the grid block into the operator instead of going through W.
    g = _grid()
    ident = GridIdentityProjection(g).matrix
    assert ident.shape == (100, 100)
    assert (ident - sparse.identity(100)).nnz == 0
    pts = np.array([[2.5, 3.5, 0.0]])
    assert (BilinearProjection(g, pts).matrix - bilinear_weights(g, pts)).nnz == 0


def test_kappa_range_roundtrip():
    # Behavior: range = sqrt(8*nu)/kappa with nu=1 round-trips kappa<->range.
    # Bug caught: an off-by-sqrt(2) in the SPDE range mapping mis-sizes correlation.
    for rng in (50.0, 200.0, 800.0):
        assert range_from_kappa(kappa_from_range(rng)) == pytest.approx(rng, rel=1e-9)
