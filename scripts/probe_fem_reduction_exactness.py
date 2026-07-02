"""HEADLINE PROBE (Phase-6 blocker): inherited GMRF selective-inverse exact on FEM's pattern?

Builds a MAXIMALLY ADVERSARIAL Delaunay mesh (irregular valence, non-uniform spacing, near-sliver
triangles, jagged boundary), assembles the P1 SPDE alpha=2 precision Q = (k^2 C + G) C^-1 (k^2 C + G)/tau
(the actual FEM pattern), adds a sparse data term to make Q_post, then compares the INHERITED
GMRFFactor.selective_inverse_diag() (Takahashi on the CHOLMOD L pattern) against a DENSE Q^-1 diagonal.
Also checks an off-diagonal cov entry on a mesh edge (the firstdifference/cov path).

Throwaway diagnostic — NOT committed method code.
"""

from __future__ import annotations

import numpy as np
from scipy import sparse  # type: ignore[import-untyped]
from scipy.spatial import Delaunay  # type: ignore[import-untyped]

from sverdrup.methods.gmrf_linalg import GMRFFactor


def adversarial_mesh(seed: int = 7) -> tuple[np.ndarray, Delaunay]:
    """Points chosen to stress the triangulation: clustered + sparse regions, jagged edge, slivers."""
    rng = np.random.default_rng(seed)
    # non-uniform interior: a dense cluster + a sparse scatter (variable valence + spacing)
    cluster = rng.normal(0.3, 0.05, size=(18, 2))
    scatter = rng.uniform(0.0, 1.0, size=(22, 2))
    # jagged boundary ring (irregular radii) + a couple near-collinear points -> slivers
    theta = np.linspace(0.0, 2 * np.pi, 13, endpoint=False)
    r = 0.9 + 0.25 * rng.uniform(size=theta.size)  # irregular radius = jagged boundary
    ring = np.c_[0.5 + r * np.cos(theta), 0.5 + r * np.sin(theta)]
    slivers = np.array(
        [[0.501, 0.5], [0.503, 0.5005], [0.505, 0.501]]
    )  # near-collinear
    pts = np.vstack([cluster, scatter, ring, slivers])
    return pts, Delaunay(pts)


def p1_assembly(
    pts: np.ndarray, tri: Delaunay, kappa: float, tau: float
) -> sparse.csc_matrix:
    """Hand-rolled P1 lumped-mass C + stiffness G; return SPDE alpha=2 precision Q (CSC)."""
    n = pts.shape[0]
    c_diag = np.zeros(n)
    g = sparse.lil_matrix((n, n))
    for t in tri.simplices:
        p = pts[t]
        # triangle area
        area = 0.5 * abs(
            (p[1, 0] - p[0, 0]) * (p[2, 1] - p[0, 1])
            - (p[2, 0] - p[0, 0]) * (p[1, 1] - p[0, 1])
        )
        if area <= 0:
            continue
        c_diag[t] += area / 3.0  # lumped mass
        # P1 gradients: b_i, c_i coefficients -> grad phi_i = (b_i, c_i)/(2 area)
        x = p[:, 0]
        y = p[:, 1]
        b = np.array([y[1] - y[2], y[2] - y[0], y[0] - y[1]])
        c = np.array([x[2] - x[1], x[0] - x[2], x[1] - x[0]])
        ke = (np.outer(b, b) + np.outer(c, c)) / (4.0 * area)  # local stiffness
        for a in range(3):
            for bb in range(3):
                g[t[a], t[bb]] += ke[a, bb]
    c = sparse.diags(c_diag)
    c_inv = sparse.diags(1.0 / c_diag)
    k = (kappa**2) * c + g.tocsc()  # k^2 C + G  (SPD)
    q = (k @ c_inv @ k) / tau  # (k^2 C + G) C^-1 (k^2 C + G) / tau
    return sparse.csc_matrix(0.5 * (q + q.T))  # symmetrize numerically


def main() -> None:
    """Run the probe: assemble the adversarial-mesh FEM precision, check exactness vs dense."""
    pts, tri = adversarial_mesh()
    n = pts.shape[0]

    # adversarial-ness report
    valence = np.bincount(tri.simplices.ravel(), minlength=n)
    angles = []
    for t in tri.simplices:
        p = pts[t]
        for a in range(3):
            v1 = p[(a + 1) % 3] - p[a]
            v2 = p[(a + 2) % 3] - p[a]
            cang = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-30)
            angles.append(np.degrees(np.arccos(np.clip(cang, -1, 1))))
    print(f"MESH: n_nodes={n}, n_tri={len(tri.simplices)}")
    print(f"  valence range=[{valence.min()},{valence.max()}] (grid-4 would be ~const)")
    print(f"  min triangle angle={min(angles):.2f} deg (sliver stress; <~10 is nasty)")

    q_prior = p1_assembly(pts, tri, kappa=3.0, tau=0.05)
    # sparse data term A^T R^-1 A at a handful of interior nodes -> Q_post (irregular + data)
    rng = np.random.default_rng(1)
    obs_nodes = rng.choice(n, size=8, replace=False)
    a = sparse.csc_matrix(
        (np.ones(obs_nodes.size), (np.arange(obs_nodes.size), obs_nodes)),
        shape=(obs_nodes.size, n),
    )
    q_post = (q_prior + (a.T @ a) / 0.01).tocsc()

    # nnz / fill stats — the pattern the Takahashi must handle
    print(f"  Q_post nnz={q_post.nnz}, density={q_post.nnz / n**2:.3f}")

    # === HEADLINE: inherited selective-inverse diag vs dense ===
    factor = GMRFFactor(q_post)
    sinv_diag = factor.selective_inverse_diag()
    dense_inv = np.linalg.inv(q_post.toarray())
    dense_diag = np.diag(dense_inv)
    rel = np.abs(sinv_diag - dense_diag) / np.abs(dense_diag)
    print("\n=== DIAG(Q^-1) marginal variance ===")
    print(f"  max rel err = {rel.max():.3e}   mean = {rel.mean():.3e}")
    print(f"  EXACT? {'YES' if rel.max() < 1e-9 else 'NO'} (rtol 1e-9)")

    # === off-diagonal cov on a mesh edge (firstdifference/cov path) ===
    sinv = factor.selective_inverse()  # entries on L+L^T pattern only
    # pick a mesh edge (two vertices sharing a triangle)
    edges = set()
    for t in tri.simplices:
        for a2 in range(3):
            i, j = sorted((int(t[a2]), int(t[(a2 + 1) % 3])))
            edges.add((i, j))
    checked, exact_edges, missing = 0, 0, 0
    for i, j in list(edges)[:40]:
        checked += 1
        val = sinv[i, j]
        if val == 0.0 and sinv[j, i] == 0.0:
            missing += 1  # edge NOT in selective-inverse pattern
            continue
        if abs(val - dense_inv[i, j]) / (abs(dense_inv[i, j]) + 1e-30) < 1e-8:
            exact_edges += 1
    print("\n=== off-diagonal cov on mesh edges (cov/firstdifference path) ===")
    print(
        f"  edges checked={checked}, exact={exact_edges}, absent-from-pattern={missing}"
    )


if __name__ == "__main__":
    main()
