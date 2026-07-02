# tests/test_fem_projection.py
"""FEMBasisProjection: P1 basis read-off conforming to the Projection seam."""

from __future__ import annotations

import numpy as np
import pytest
from scipy import sparse  # type: ignore[import-untyped]

from sverdrup.core.projection import Projection
from sverdrup.methods.fem import FEMBasisProjection, fem_precision
from sverdrup.methods.fem_mesh import Mesh, build_mesh


def _mesh() -> Mesh:
    xs, ys = np.meshgrid(np.linspace(0.0, 3.0, 5), np.linspace(0.0, 3.0, 5))
    return build_mesh(np.column_stack([xs.ravel(), ys.ravel()]), time_days=1.0)


def test_conforms_to_projection_protocol() -> None:
    # Behavior: FEMBasisProjection is a structural Projection (the seam the operator routes through).
    # Bug it catches: a missing/renamed hook that would break the discretization-agnostic operator.
    assert isinstance(FEMBasisProjection(_mesh()), Projection)


def test_weights_partition_of_unity_and_node_selector() -> None:
    # Behavior: P1 basis rows sum to 1; a query on a node is a unit selector on that node.
    # Bug it catches: barycentric weights that don't interpolate (biased A/W read-off).
    mesh = _mesh()
    proj = FEMBasisProjection(mesh)
    interior = np.array([[1.3, 1.7, 1.0], [2.1, 0.4, 1.0]])
    w = proj.weights(interior)
    assert w.shape == (2, mesh.n_nodes)
    assert np.allclose(np.asarray(w.sum(axis=1)).ravel(), 1.0)
    node = mesh.points()[3:4]  # exactly on node 3
    wn = proj.weights(node)
    assert wn[0, 3] > 0.999 and abs(wn.sum() - 1.0) < 1e-9


def test_field_shape_and_node_points() -> None:
    # Behavior: mesh field is flat (n_nodes,); node_points echoes the mesh coords with a time column.
    # Bug it catches: a (ny,nx) leak on the FEM path.
    mesh = _mesh()
    proj = FEMBasisProjection(mesh)
    assert proj.field_shape() == (mesh.n_nodes,)
    np_pts = proj.node_points(1.0)
    assert np_pts.shape == (mesh.n_nodes, 3)
    assert np.allclose(np_pts[:, :2], mesh.points_xy)


def test_assert_adjacency_mesh_edge_guard() -> None:
    # Behavior: the FEM adjacency guard passes on the real Q (edges in pattern) and raises when an
    # edge is missing -> the mesh analogue of the grid 5-point precondition, NOT the grid guard.
    # Bug it catches: routing FEM through assert_adjacency_in_pattern(shape=(ny,nx)) (grid-shaped).
    mesh = _mesh()
    proj = FEMBasisProjection(mesh)
    q = fem_precision(mesh, kappa=3.0, tau=0.05)
    proj.assert_adjacency(q)  # no raise: alpha=2 carries every mesh edge
    # a precision missing an edge -> loud red
    empty = sparse.identity(mesh.n_nodes, format="csc")
    with pytest.raises(AssertionError, match="edge|pattern"):
        proj.assert_adjacency(empty)
