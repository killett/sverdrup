"""The Projection seam: grid dataclasses conform; weights/field_shape are load-bearing."""

from __future__ import annotations

import numpy as np
from scipy import sparse  # type: ignore[import-untyped]

from sverdrup.core.grid import GridSpec
from sverdrup.core.projection import Projection
from sverdrup.methods.gmrf_grid import (
    BilinearProjection,
    GridIdentityProjection,
    bilinear_weights,
)


def _grid() -> GridSpec:
    return GridSpec.lonlat(np.linspace(0.0, 9.0, 10), np.linspace(0.0, 9.0, 10))


def test_grid_projections_are_projections():
    # Behavior: both grid dataclasses structurally satisfy the Projection protocol.
    # Bug caught: a projection missing weights/field_shape/node_points would be
    #   silently un-consumable by the operator, reverting to the hardcoded read-off.
    g = _grid()
    assert isinstance(GridIdentityProjection(g), Projection)
    assert isinstance(BilinearProjection(g, g.points(0.0)), Projection)


def test_identity_weights_match_bilinear_and_shape():
    # Behavior: GridIdentity.weights routes through bilinear_weights; field_shape is (ny,nx).
    # Bug caught: a weights() that diverges from bilinear_weights would make the
    #   refactored operator disagree with the Phase-3 hardcoded path.
    g = _grid()
    proj = GridIdentityProjection(g)
    pts = np.array([[2.5, 3.5, 0.0], [4.0, 4.0, 0.0]])
    assert (proj.weights(pts) - bilinear_weights(g, pts)).nnz == 0
    assert proj.field_shape() == g.shape
    assert proj.node_points(0.0).shape[0] == g.shape[0] * g.shape[1]


def test_bilinear_projection_field_shape_is_query_count():
    # Behavior: an off-grid projection's field_shape is the number of query points.
    g = _grid()
    pts = np.array([[1.1, 2.2, 0.0], [3.3, 4.4, 0.0], [5.5, 6.6, 0.0]])
    assert BilinearProjection(g, pts).field_shape() == (3,)


def test_assert_adjacency_delegates_to_grid_check():
    # Behavior: the grid projection's adjacency precondition is the 5-point pattern check.
    # Bug caught: an operator that skipped this would let a too-narrow Q stencil silently
    #   break eval-variance / first-difference cancellation.
    import pytest

    g = _grid()
    bad = sparse.identity(g.shape[0] * g.shape[1], format="csc")  # no neighbour edges
    with pytest.raises(AssertionError):
        GridIdentityProjection(g).assert_adjacency(bad)
