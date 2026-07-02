"""FEM P1 SPDE method: precision assembly + basis read-off + solve (Phase 6).

FEM is a near-pure discretization swap: ``fem_precision`` and ``FEMBasisProjection`` are the only
mesh-carrying units; everything downstream (operator, CHOLMOD factor + Takahashi selective inverse,
reduction, coherent driver, blend) is inherited unchanged. Stationary scalar kappa only (per-node
kappa deferred — it scales entries, not the sparsity pattern).
"""

from __future__ import annotations

import numpy as np
from scipy import sparse  # type: ignore[import-untyped]

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
