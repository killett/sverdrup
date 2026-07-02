# tests/test_fem_precision.py
"""AGNOSTICISM TIER #1 (headline): the inherited selective inverse is EXACT on FEM's irregular pattern.

Scope caveat (spec 0.2/7): this is strong falsifying evidence on the paths this adversarial fixture
exercises (selective-inverse diagonal + mesh-edge cov), proportional to fixture adversarial-ness — not
an unconditional proof of grid-agnosticism.
"""

from __future__ import annotations

import numpy as np
from scipy import sparse  # type: ignore[import-untyped]

from sverdrup.methods.fem import fem_precision
from sverdrup.methods.fem_mesh import Mesh, build_mesh
from sverdrup.methods.gmrf_linalg import GMRFFactor


def _adversarial_mesh(seed: int = 7) -> Mesh:
    # MAXIMALLY ADVERSARIAL (spec 3 #1): variable valence, non-uniform spacing, a near-threshold
    # sliver, a jagged boundary ring, small enough for a dense Q^-1 ground truth.
    rng = np.random.default_rng(seed)
    cluster = rng.normal(0.3, 0.05, size=(18, 2))  # dense cluster -> high valence
    scatter = rng.uniform(0.0, 1.0, size=(22, 2))  # sparse scatter -> low valence
    theta = np.linspace(0.0, 2 * np.pi, 13, endpoint=False)
    r = 0.9 + 0.25 * rng.uniform(size=theta.size)  # irregular radius -> jagged boundary
    ring = np.c_[0.5 + r * np.cos(theta), 0.5 + r * np.sin(theta)]
    slivers = np.array(
        [[0.501, 0.5], [0.503, 0.5005], [0.505, 0.501]]
    )  # near-collinear sliver
    return build_mesh(np.vstack([cluster, scatter, ring, slivers]))


def _q_post(mesh: Mesh) -> sparse.csc_matrix:
    q_prior = fem_precision(mesh, kappa=3.0, tau=0.05)
    n = mesh.n_nodes
    rng = np.random.default_rng(1)
    obs = rng.choice(n, size=8, replace=False)
    a = sparse.csc_matrix(
        (np.ones(obs.size), (np.arange(obs.size), obs)), shape=(obs.size, n)
    )
    return (q_prior + (a.T @ a) / 0.01).tocsc()


def test_selective_inverse_diag_exact_on_adversarial_mesh() -> None:
    # Behavior: the INHERITED Takahashi selective-inverse diagonal equals dense diag(Q^-1) on FEM's
    # irregular P1 pattern -> no hidden lattice assumption in the reduction path.
    # Bug it catches: any latent grid/lattice assumption in factorization or the selective inverse
    # (would produce plausible-but-wrong marginal variance on a non-grid pattern).
    mesh = _adversarial_mesh()
    assert mesh.points_xy.shape[0] >= 40  # dense-invertible but non-trivial
    q = _q_post(mesh)
    factor = GMRFFactor(q)
    sinv_diag = factor.selective_inverse_diag()
    dense = np.linalg.inv(q.toarray())
    rel = np.abs(sinv_diag - np.diag(dense)) / np.abs(np.diag(dense))
    assert rel.max() < 1e-9, (
        f"selective-inverse diag not exact: max rel {rel.max():.2e}"
    )


def test_every_mesh_edge_in_pattern_and_exact() -> None:
    # Behavior: every 1-hop mesh edge's Sigma_ij is IN the selective-inverse pattern (0 absent) and
    # exact vs dense -> the alpha=2 assembly (k^2 C + G) C^-1 (k^2 C + G) carries the 2-hop neighborhood.
    # Bug it catches: an assembly that drops mesh edges from Q's pattern so cov/firstdifference reads 0
    # (NOT implied by Takahashi-exactness alone; this is the assembly-pattern sub-claim, spec 0.1).
    mesh = _adversarial_mesh()
    q = _q_post(mesh)
    factor = GMRFFactor(q)
    sinv = factor.selective_inverse()
    dense = np.linalg.inv(q.toarray())
    edges = {
        tuple(sorted((int(t[a]), int(t[(a + 1) % 3]))))
        for t in mesh.triangles
        for a in range(3)
    }
    absent, checked = 0, 0
    for i, j in edges:
        checked += 1
        val = sinv[i, j]
        if val == 0.0 and sinv[j, i] == 0.0:
            absent += 1
            continue
        assert abs(val - dense[i, j]) / (abs(dense[i, j]) + 1e-30) < 1e-8
    assert absent == 0, (
        f"{absent}/{checked} mesh edges absent from the selective-inverse pattern"
    )
