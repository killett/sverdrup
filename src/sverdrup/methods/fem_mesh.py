"""FEM triangulation: Mesh value object + Delaunay builder + sliver quality guard (Phase 6).

The Mesh is the FEM ``Projection.node_space``. It is PointSet-like — ``.points()`` returns
``(n_nodes, 3)`` ``(lon, lat, time)`` so the blend's ``_support_points`` / ``_nearest`` work
unchanged. ``assert_mesh_quality`` is the sliver guard, the FEM analogue of ``_assert_separates``:
a loud red on a degenerate triangulation so a meshing artifact never masquerades as a method failure.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.spatial import Delaunay  # type: ignore[import-untyped]

from sverdrup.core.types import Points


@dataclass(frozen=True)
class Mesh:
    """A 2-D P1 triangulation: node coordinates + triangle vertex indices.

    Attributes:
        points_xy: ``(n_nodes, 2)`` node coordinates ``(lon, lat)``.
        triangles: ``(n_tri, 3)`` integer vertex indices into ``points_xy``.
        time_days: The output time carried in the ``(n,3)`` ``points()`` third column.
    """

    points_xy: np.ndarray
    triangles: np.ndarray
    time_days: float = 0.0

    def points(self) -> Points:
        """Return ``(n_nodes, 3)`` ``(lon, lat, time)`` — the PointSet contract the blend consumes."""
        n = self.points_xy.shape[0]
        return np.column_stack([self.points_xy, np.full(n, self.time_days)]).astype(
            float
        )

    @property
    def n_nodes(self) -> int:
        """Return the number of mesh nodes."""
        return int(self.points_xy.shape[0])


def build_mesh(
    points: np.ndarray,
    boundary_ring: np.ndarray | None = None,
    refine_points: np.ndarray | None = None,
    time_days: float = 0.0,
) -> Mesh:
    """Delaunay-triangulate an arbitrary 2-D point set (+ optional boundary ring / refinement).

    Args:
        points: ``(n, >=2)`` input node coordinates (only the first 2 columns are used).
        boundary_ring: Optional ``(m, >=2)`` extended-boundary nodes that drive boundary extension.
        refine_points: Optional ``(r, >=2)`` locally-densified nodes for data-adaptive refinement.
        time_days: Output time carried by the resulting ``Mesh``.

    Returns:
        A ``Mesh`` over the stacked input/ring/refine node set.
    """
    stack = [np.asarray(points, float)[:, :2]]
    if boundary_ring is not None:
        stack.append(np.asarray(boundary_ring, float)[:, :2])
    if refine_points is not None:
        stack.append(np.asarray(refine_points, float)[:, :2])
    all_pts = np.vstack(stack)
    tri = Delaunay(all_pts)
    return Mesh(all_pts, tri.simplices.astype(int), time_days)


def assert_mesh_quality(mesh: Mesh, min_angle: float = 5.0) -> None:
    """Raise if any triangle's minimum interior angle is below ``min_angle`` degrees (sliver guard).

    Args:
        mesh: The triangulation to check.
        min_angle: The minimum acceptable interior angle in degrees.

    Raises:
        AssertionError: On a zero-area (degenerate) or sub-threshold (sliver) triangle.
    """
    p = mesh.points_xy
    worst = 180.0
    for t in mesh.triangles:
        tri = p[t]
        for a in range(3):
            v1 = tri[(a + 1) % 3] - tri[a]
            v2 = tri[(a + 2) % 3] - tri[a]
            denom = float(np.linalg.norm(v1) * np.linalg.norm(v2))
            if denom == 0.0:
                raise AssertionError("degenerate triangle: zero-length edge")
            ang = np.degrees(np.arccos(np.clip(np.dot(v1, v2) / denom, -1.0, 1.0)))
            worst = min(worst, float(ang))
    if worst < min_angle:
        raise AssertionError(
            f"sliver triangle: min angle {worst:.2f} deg < {min_angle} deg"
        )
