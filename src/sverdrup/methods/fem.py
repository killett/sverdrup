"""FEM P1 SPDE method: precision assembly + basis read-off + solve (Phase 6).

FEM is a near-pure discretization swap: ``fem_precision`` and ``FEMBasisProjection`` are the only
mesh-carrying units; everything downstream (operator, CHOLMOD factor + Takahashi selective inverse,
reduction, coherent driver, blend) is inherited unchanged. Stationary scalar kappa only (per-node
kappa deferred — it scales entries, not the sparsity pattern).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import sparse  # type: ignore[import-untyped]
from scipy.spatial import Delaunay  # type: ignore[import-untyped]

from sverdrup.core.types import Points
from sverdrup.methods.fem_mesh import Mesh


def fem_precision(mesh: Mesh, kappa: float, tau: float) -> sparse.csc_matrix:
    """Assemble the P1 SPDE alpha=2 precision ``Q = (1/tau)(k^2 C + G) C^-1 (k^2 C + G)``.

    ``C`` is the P1 lumped mass (diagonal, area/3 per node); ``G`` is the P1 stiffness (gradient
    inner products). The congruence ``(k^2 C + G) C^-1 (k^2 C + G)`` is SPD and carries the 2-hop
    neighborhood, so every 1-hop mesh edge is in ``Q``'s pattern.

    Args:
        mesh: The triangulation the precision lives on.
        kappa: Scalar SPDE inverse-range parameter (stationary; per-node deferred).
        tau: Variance scale (``diag(Q^-1)`` grows with ``tau``).

    Returns:
        A symmetric SPD ``(n_nodes, n_nodes)`` CSC precision.

    Note:
        Assembly does NOT gate on ``assert_mesh_quality``: the headline agnosticism claim (spec 3 #1,
        committed in ``scripts/probe_fem_reduction_exactness.py``) is precisely that the inherited
        selective inverse is exact on a maximally-irregular mesh *including near-sliver triangles*
        (verified there at cond ~1.6e8). The sliver guard is a standalone diagnostic (``fem_mesh``),
        invoked by callers that want to reject degenerate meshes — not by assembly.
    """
    p = mesh.points_xy
    n = mesh.n_nodes
    c_diag = np.zeros(n)
    g = sparse.lil_matrix((n, n))
    for t in mesh.triangles:
        tri = p[t]
        area = 0.5 * abs(
            (tri[1, 0] - tri[0, 0]) * (tri[2, 1] - tri[0, 1])
            - (tri[2, 0] - tri[0, 0]) * (tri[1, 1] - tri[0, 1])
        )
        if area <= 0:
            continue
        c_diag[t] += area / 3.0  # P1 lumped mass
        x, y = tri[:, 0], tri[:, 1]
        b = np.array([y[1] - y[2], y[2] - y[0], y[0] - y[1]])
        cc = np.array([x[2] - x[1], x[0] - x[2], x[1] - x[0]])
        ke = (np.outer(b, b) + np.outer(cc, cc)) / (4.0 * area)  # P1 stiffness
        for a in range(3):
            for bb in range(3):
                g[t[a], t[bb]] += ke[a, bb]
    c = sparse.diags(c_diag)
    c_inv = sparse.diags(1.0 / c_diag)
    k = (kappa**2) * c + g.tocsc()  # (k^2 C + G), SPD
    q = (k @ c_inv @ k) / tau  # (k^2 C + G) C^-1 (k^2 C + G) / tau
    return sparse.csc_matrix(0.5 * (q + q.T))  # symmetrize against round-off


@dataclass(frozen=True)
class FEMBasisProjection:
    """P1 basis read-off ``W`` (mesh analogue of ``bilinear_weights``); a ``Projection``.

    ``weights(pts)`` locates each query point's triangle via ``Delaunay.find_simplex`` and evaluates
    the three P1 barycentric basis functions -> a sparse ``(k, n_nodes)`` map. ``A`` (node -> obs) is
    this at obs points. ``assert_adjacency`` is the mesh-edge-in-pattern precondition (NOT the grid
    5-point guard): every triangulation edge must be present in the precision's sparsity pattern.
    """

    mesh: Mesh

    @property
    def node_space(self) -> Mesh:
        """Return the node layout (the mesh)."""
        return self.mesh

    def _delaunay(self) -> Delaunay:
        return Delaunay(self.mesh.points_xy)

    def weights(self, pts: Points) -> sparse.csr_matrix:
        """Return the sparse ``(k, n_nodes)`` P1-basis map from mesh nodes to ``pts``."""
        tri = self._delaunay()
        query = np.asarray(pts, float)[:, :2]
        simplex = tri.find_simplex(query)
        k = query.shape[0]
        rows, cols, vals = [], [], []
        transforms = tri.transform
        for r in range(k):
            s = int(simplex[r])
            if (
                s < 0
            ):  # outside the hull -> nearest node (unit selector), keeps rows summing to 1
                nearest = int(
                    np.argmin(np.linalg.norm(self.mesh.points_xy - query[r], axis=1))
                )
                rows.append(r)
                cols.append(nearest)
                vals.append(1.0)
                continue
            b = transforms[s, :2] @ (query[r] - transforms[s, 2])
            bary = np.array([b[0], b[1], 1.0 - b[0] - b[1]])
            for vtx, wgt in zip(tri.simplices[s], bary, strict=False):
                if wgt != 0.0:
                    rows.append(r)
                    cols.append(int(vtx))
                    vals.append(float(wgt))
        w = sparse.csr_matrix((vals, (rows, cols)), shape=(k, self.mesh.n_nodes))
        rs = np.asarray(w.sum(axis=1)).ravel()
        rs[rs == 0] = 1.0
        return sparse.diags(1.0 / rs) @ w

    def field_shape(self) -> tuple[int, ...]:
        """Return ``(n_nodes,)`` — the FEM field is flat over mesh nodes."""
        return (self.mesh.n_nodes,)

    def node_points(self, time_days: float) -> Points:
        """Return the ``(n_nodes, 3)`` mesh node coordinates at ``time_days``."""
        n = self.mesh.n_nodes
        return np.column_stack([self.mesh.points_xy, np.full(n, time_days)]).astype(
            float
        )

    def assert_adjacency(self, q: sparse.spmatrix) -> None:
        """Raise if any mesh edge ``(i,j)`` is absent from ``q``'s pattern (mesh analogue of 5-point)."""
        qcoo = q.tocoo()
        present = set(zip(qcoo.row.tolist(), qcoo.col.tolist(), strict=False))
        for t in self.mesh.triangles:
            for a in range(3):
                i, j = int(t[a]), int(t[(a + 1) % 3])
                if (i, j) not in present or (j, i) not in present:
                    raise AssertionError(
                        f"mesh edge ({i},{j}) absent from Q pattern — FEM read-off/cov would break"
                    )
