# tests/test_fem_mesh.py
"""Mesh construction, boundary-ring inclusion, and the sliver quality guard."""

from __future__ import annotations

import numpy as np
import pytest

from sverdrup.methods.fem_mesh import Mesh, assert_mesh_quality, build_mesh


def _square_points() -> np.ndarray:
    # a 4x4 lattice of points -> a well-conditioned triangulation
    xs, ys = np.meshgrid(np.linspace(0.0, 3.0, 4), np.linspace(0.0, 3.0, 4))
    return np.column_stack([xs.ravel(), ys.ravel()])


def test_build_mesh_produces_pointset_like_mesh() -> None:
    # Behavior: build_mesh triangulates and exposes (n,3) points() for the blend's _support_points.
    # Bug it catches: a Mesh that does not carry the (lon,lat,time) contract the blend consumes.
    mesh = build_mesh(_square_points(), time_days=2.0)
    assert isinstance(mesh, Mesh)
    assert mesh.points_xy.shape == (16, 2)
    assert mesh.triangles.shape[1] == 3 and mesh.triangles.shape[0] > 0
    p = mesh.points()
    assert p.shape == (16, 3)
    assert np.allclose(p[:, 2], 2.0)  # time column carried


def test_boundary_ring_adds_nodes() -> None:
    # Behavior: an extended boundary ring drives boundary extension by adding ring nodes.
    # Bug it catches: build_mesh silently dropping the ring so no boundary extension happens.
    ring = np.array([[-1.0, -1.0], [4.0, -1.0], [4.0, 4.0], [-1.0, 4.0]])
    mesh = build_mesh(_square_points(), boundary_ring=ring)
    assert mesh.points_xy.shape[0] == 16 + 4


def test_sliver_guard_raises_on_degenerate_triangle() -> None:
    # Behavior: assert_mesh_quality is a loud red on a near-collinear (sliver) triangle.
    # Bug it catches: a meshing artifact inflating G / denting Q conditioning passing silently.
    # An INTERIOR point sitting ~1e-3 off the base forces an unavoidable sliver: Delaunay must
    # connect it to every hull vertex (a hull-edge diagonal-flip cannot escape it, unlike a
    # near-collinear hull triple, which Delaunay re-triangulates into well-shaped triangles).
    slivers = np.array([[0.0, 0.0], [2.0, 0.0], [1.0, 2.0], [1.0, 1e-3]])
    mesh = build_mesh(slivers)
    with pytest.raises(AssertionError, match="sliver|degenerate"):
        assert_mesh_quality(mesh, min_angle=5.0)


def test_sliver_guard_passes_on_good_mesh() -> None:
    # Behavior: a well-shaped mesh clears the guard.
    # Bug it catches: an over-strict guard that reddens valid triangulations.
    assert_mesh_quality(build_mesh(_square_points()), min_angle=5.0)  # no raise
