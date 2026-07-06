"""Stage-B exactness oracle + under-convergence contract (plan Task 16, spec 6.5).

Proves the PRODUCTION member construction (member_rhs_matrix — the same
function sample_members uses) samples the exact coefficient posterior
A^-1 = (G^T R^-1 G + Q^-1)^-1 on a small multiscale geometry, against a
DENSE inverse computed independently of the PCG/CRN path.

PLAN DEVIATION (recorded in PROGRESS): the plan's matrix-wide Frobenius
bound 3*sqrt(2/(m-1)) is a SCALAR-variance yardstick; the rel Frobenius
error of an (n x n) sample covariance from m draws scales as sqrt(n/m)
(~0.96 here at n=3696, m=4000), so that acceptance is unsatisfiable for
any realistic basis. The exactness claim is instead tested on WHITENED
anomalies Z = L^-1 (members - mean), A^-1 = L L^T: exact sampling gives
Z ~ N(0, I), so trace(C_Z)/n -> 1 within sqrt(2/(m n)) — a far TIGHTER
scale test than the plan bound — off-diagonals -> 1/m, and every
whitened variance stays within its own 5-sigma band.
"""

from __future__ import annotations

import numpy as np
import pytest

from sverdrup.methods.miost import _obs_identity, member_rhs_matrix
from sverdrup.methods.miost_basis import BasisSpec, DiagonalQ, build_g
from sverdrup.methods.miost_solver import MiostSolver, rhs_from_obs

M = 4000
ROOT = 987654321
# Two COARSE rungs keep dense A^-1 tractable (n_el = 3696) while preserving
# the cross-rung overlap that makes the system genuinely multiscale.
SPEC = BasisSpec(alpha=1.5, l_t_days=12.0, ladder=(640.0, 905.1))


class _Case:
    def __init__(self) -> None:
        rng = np.random.default_rng(23)
        els = SPEC.elements_for_window(0.0)
        n_obs = 40
        lon = rng.uniform(296, 304, n_obs)
        lat = rng.uniform(34, 42, n_obs)
        t = rng.uniform(5, 55, n_obs)
        self.y = rng.standard_normal(n_obs) * 0.1
        self.r = np.full(n_obs, 0.01)
        self.q = DiagonalQ(rho=20.0, q_slope=2.0).variances_for(els)
        self.g = build_g(SPEC, els, lon, lat, t)
        self.obs_ident = _obs_identity(lon, lat, t, None)
        self.els_ident = els.identity
        self.n = len(self.q)
        # Independent dense reference: A^-1 by direct linear algebra.
        gd = np.asarray(self.g.todense())
        a = gd.T @ (gd / self.r[:, None]) + np.diag(1.0 / self.q)
        self.a_inv = np.linalg.inv(a)
        # Whitener: A^-1 = L L^T -> exact members give L^-1 anomalies ~ N(0, I).
        self.chol = np.linalg.cholesky(self.a_inv)
        solver = MiostSolver(
            self.g, r_diag=self.r, q_diag=self.q, pcg_rtol=1e-8, pcg_maxiter=4000
        )
        self.eta_a, rep = solver.solve(rhs_from_obs(self.g, self.r, self.y))
        # Guard: solver error must be negligible vs the sampling statistics.
        assert float(rep.final_rel_residual.max()) < 1e-8
        self.b = member_rhs_matrix(
            self.g, self.r, self.y, self.q, self.obs_ident, self.els_ident, M, ROOT
        )
        members, repm = solver.solve(self.b)
        assert float(repm.final_rel_residual.max()) < 1e-8
        self.members = np.asarray(members)

    def whitened(self, members: np.ndarray) -> np.ndarray:
        """L^-1 (members - member mean): exact sampling -> N(0, I) columns."""
        anoms = members - members.mean(axis=1, keepdims=True)
        from scipy.linalg import solve_triangular  # type: ignore[import-untyped]

        return np.asarray(solve_triangular(self.chol, anoms, lower=True))


@pytest.fixture(scope="module")
def case() -> _Case:
    return _Case()


def test_whitened_covariance_is_identity(case: _Case) -> None:
    """Whitened member covariance == I within exact sampling statistics.

    Catches: a missing Q^-1 eta~ term (whitened prior-dominated directions
    collapse, trace/n falls far below 1 — the exact under-dispersion sigma
    cares about), eps scaled by R instead of sqrt(R) (trace blows up), and
    an m denominator (trace off by (m-1)/m > 5 sigma at this m*n).
    """
    z = case.whitened(case.members)
    c_z = (z @ z.T) / (M - 1)
    n = case.n
    diag = np.diag(c_z)
    trace_stat = float(diag.mean())
    trace_tol = 5.0 * np.sqrt(2.0 / (M * n))  # pooled 5-sigma, ~0.0016
    print(f"whitened trace/n: {trace_stat:.5f} (tol +-{trace_tol:.5f})")
    assert abs(trace_stat - 1.0) < trace_tol
    # Every whitened variance individually within its own 5-sigma band.
    worst = float(np.abs(diag - 1.0).max())
    per_entry = 5.0 * np.sqrt(2.0 / M)
    print(f"worst whitened variance dev: {worst:.4f} (tol {per_entry:.4f})")
    assert worst < per_entry
    # Off-diagonals: mean square == 1/m under independence (20% band).
    off = c_z[~np.eye(n, dtype=bool)]
    ms = float((off**2).mean())
    print(f"offdiag mean square: {ms:.2e} (expect ~{1 / M:.2e})")
    assert 0.8 / M < ms < 1.2 / M


def test_member_mean_recovers_eta_a(case: _Case) -> None:
    """Member mean -> eta^a within Monte-Carlo error.

    Catches: biased uniform mapping in the CRN (nonzero-mean draws) or a
    missing base RHS term (mean would sit at 0, not eta^a).
    """
    mc = 3.0 * np.sqrt(np.trace(case.a_inv) / M)
    diff = float(np.linalg.norm(case.members.mean(axis=1) - np.asarray(case.eta_a)))
    print(f"mean recovery: |diff| {diff:.4f} vs MC bound {mc:.4f}")
    assert diff < mc
    assert diff > 0.0  # members genuinely stochastic, not copies of eta^a


def test_under_convergence_corrupts_covariance(case: _Case) -> None:
    """Deliberately loose PCG (rtol=0.5) breaks the whitened-identity scale
    by >3x the tight solve's deviation — the spec-6.5 contract: member
    generation MUST NOT inherit a budget cap silently.

    Catches: assuming the Stage-A budgeted solve is statistically harmless
    for members; this documents, with numbers, that it is not.
    """

    def trace_dev(members: np.ndarray) -> float:
        z = case.whitened(members)
        return abs(float(np.einsum("ij,ij->i", z, z).mean()) / (M - 1) - 1.0)

    loose = MiostSolver(
        case.g, r_diag=case.r, q_diag=case.q, pcg_rtol=0.5, pcg_maxiter=4000
    )
    members_loose, _ = loose.solve(case.b)
    dev_tight = trace_dev(case.members)
    dev_loose = trace_dev(np.asarray(members_loose))
    print(
        f"under-convergence: tight |trace/n - 1| {dev_tight:.5f}, "
        f"loose (rtol=0.5) {dev_loose:.5f}"
    )
    assert dev_loose > 3.0 * dev_tight
