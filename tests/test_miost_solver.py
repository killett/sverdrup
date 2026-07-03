"""Tests for the multi-RHS Jacobi-PCG MIOST solver (seam a; Tier 1 iii)."""

from __future__ import annotations

import numpy as np
from scipy import sparse  # type: ignore[import-untyped]

from sverdrup.methods.miost_solver import MiostSolver

RNG = np.random.default_rng(3)


def _small_system(
    n_obs: int = 60, n_coef: int = 25
) -> tuple[sparse.csr_matrix, np.ndarray, np.ndarray]:
    g = sparse.random(n_obs, n_coef, density=0.3, random_state=3, format="csr")
    r = np.full(n_obs, 0.01)
    q = np.full(n_coef, 2.0)
    return g, r, q


def test_pcg_matches_dense() -> None:
    """Tier 1 (iii): PCG solution == dense solve of the same normal equations."""
    g, r, q = _small_system()
    a_dense = (g.T @ sparse.diags(1 / r) @ g).toarray() + np.diag(1 / q)
    b = RNG.standard_normal(g.shape[1])
    s = MiostSolver(g, r_diag=r, q_diag=q, pcg_rtol=1e-12)
    x, report = s.solve(b)
    np.testing.assert_allclose(x, np.linalg.solve(a_dense, b), rtol=1e-8)
    assert report.iterations[0] > 0 and report.final_rel_residual[0] <= 1e-10


def test_solve_is_rhs_agnostic_multi_rhs() -> None:
    """Seam (a): arbitrary B (n_coef, 3) not derived from any y; columns independent."""
    g, r, q = _small_system()
    s = MiostSolver(g, r_diag=r, q_diag=q)
    b = RNG.standard_normal((g.shape[1], 3))
    x, _ = s.solve(b)
    x0, _ = s.solve(b[:, 0])
    np.testing.assert_allclose(x[:, 0], x0, rtol=1e-8)


def test_named_defaults() -> None:
    """pcg_rtol=1e-6, pcg_maxiter=500 are the named defaults."""
    g, r, q = _small_system()
    s = MiostSolver(g, r_diag=r, q_diag=q)
    assert s.pcg_rtol == 1e-6 and s.pcg_maxiter == 500


def test_zero_obs_total() -> None:
    """n_obs=0 -> A = Q^-1, solve returns q*b exactly (degenerate-obs totality §4.3)."""
    g = sparse.csr_matrix((0, 10))
    q = np.full(10, 2.0)
    s = MiostSolver(g, r_diag=np.zeros(0), q_diag=q)
    b = RNG.standard_normal(10)
    x, _ = s.solve(b)
    np.testing.assert_allclose(x, q * b, rtol=1e-10)
