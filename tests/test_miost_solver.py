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


def test_csc_input_matches_csr() -> None:
    """The huge-G path hands the solver CSC; solution and preconditioner identical."""
    g, r, q = _small_system()
    b = RNG.standard_normal(g.shape[1])
    s_csr = MiostSolver(g, r_diag=r, q_diag=q, pcg_rtol=1e-12)
    s_csc = MiostSolver(g.tocsc(), r_diag=r, q_diag=q, pcg_rtol=1e-12)
    np.testing.assert_allclose(s_csc._m_inv, s_csr._m_inv, rtol=1e-14)
    x_csr, _ = s_csr.solve(b)
    x_csc, _ = s_csc.solve(b)
    np.testing.assert_allclose(x_csc, x_csr, rtol=1e-10)


def test_zero_obs_total() -> None:
    """n_obs=0 -> A = Q^-1, solve returns q*b exactly (degenerate-obs totality §4.3)."""
    g = sparse.csr_matrix((0, 10))
    q = np.full(10, 2.0)
    s = MiostSolver(g, r_diag=np.zeros(0), q_diag=q)
    b = RNG.standard_normal(10)
    x, _ = s.solve(b)
    np.testing.assert_allclose(x, q * b, rtol=1e-10)


def _capped_converges(
    g: sparse.csr_matrix, r: np.ndarray, q: np.ndarray, b: np.ndarray, cap: int
) -> bool:
    s = MiostSolver(g, r_diag=r, q_diag=q, pcg_rtol=1e-10, pcg_maxiter=cap)
    return bool(s.solve(b)[1].final_rel_residual[0] <= 1e-10)


def test_reported_iterations_are_the_iterations_it_took() -> None:
    """``iterations`` is the iteration at which the residual met rtol.

    Bug caught (hygiene P2-#15): ``iters[active] = it`` ran AFTER the
    convergence test, so a column converging at iteration k kept the k-1
    written on the previous pass — every converged column under-reported
    by one. Expected value without the report: with ONE right-hand side
    the solve stops at the first converging iteration, so k is the
    smallest ``pcg_maxiter`` at which a capped solve converges (binary
    search; monotone because no iterate before k meets rtol).
    """
    g, r, q = _small_system()
    b = np.random.default_rng(21).standard_normal(g.shape[1])
    lo, hi = 1, 2000
    assert _capped_converges(g, r, q, b, hi)
    while lo < hi:
        mid = (lo + hi) // 2
        if _capped_converges(g, r, q, b, mid):
            hi = mid
        else:
            lo = mid + 1
    k = lo
    assert k > 1  # a one-iteration system could not show an off-by-one
    _, report = MiostSolver(g, r_diag=r, q_diag=q, pcg_rtol=1e-10).solve(b)
    assert int(report.iterations[0]) == k


def test_a_capped_unconverged_solve_reports_the_cap() -> None:
    """Bug caught: a fix that shifts EVERY count by one, so a solve that
    hit its cap reports cap+1 iterations it never ran."""
    g, r, q = _small_system()
    b = np.random.default_rng(21).standard_normal(g.shape[1])
    s = MiostSolver(g, r_diag=r, q_diag=q, pcg_rtol=1e-10, pcg_maxiter=3)
    _, report = s.solve(b)
    assert report.final_rel_residual[0] > 1e-10
    assert int(report.iterations[0]) == 3
