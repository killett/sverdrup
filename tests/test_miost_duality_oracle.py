"""Tier-1 duality oracle: reduced normal equations == obs-space OI with B = Gamma Q Gamma^T.

If this test fails, the bug is in Tasks 2-4 code (basis/operators/solver) — fix
there; never loosen the oracle.
"""

from __future__ import annotations

import numpy as np

from sverdrup.methods.miost_basis import BasisSpec, DiagonalQ, build_g, lonlat_to_km
from sverdrup.methods.miost_solver import MiostSolver, rhs_from_obs

RNG = np.random.default_rng(11)


def test_duality_oracle_u2021_eq2_vs_eq15() -> None:
    """Reduced path (Eq. 15) reproduces dense obs-space OI (Eq. 2) at rtol 1e-8."""
    spec = BasisSpec(alpha=1.5, l_t_days=10.0, ladder=(320.0, 452.548))  # 2 rungs, tiny
    els = spec.elements_for_window(0.0)
    n = 50
    lon = RNG.uniform(296, 304, n)
    lat = RNG.uniform(34, 42, n)
    t = RNG.uniform(10, 50, n)
    y = RNG.standard_normal(n) * 0.1
    r = np.full(n, 0.01)
    q = DiagonalQ(rho=20.0, q_slope=2.0).variances_for(els)

    g = build_g(spec, els, lon, lat, t)  # obs-side Gamma (= H Gamma, H analytic)
    # query points: a coarse grid at day 30
    qlon, qlat = np.meshgrid(np.linspace(296, 304, 9), np.linspace(34, 42, 9))
    qx, qy = lonlat_to_km(qlon.ravel(), qlat.ravel())
    gamma_q = spec.evaluate(els, qx, qy, np.full(qx.size, 30.0))  # (n_query, n_elem)

    # Eq. 2: x^a = B_qd (B_dd + R)^-1 y  with  B = Gamma Q Gamma^T
    gd = g.toarray()
    b_dd = gd * q @ gd.T
    b_qd = gamma_q * q @ gd.T
    dense_map = b_qd @ np.linalg.solve(b_dd + np.diag(r), y)

    # Eq. 15: eta^a = (G^T R^-1 G + Q^-1)^-1 G^T R^-1 y ; map = Gamma eta^a
    eta, _ = MiostSolver(g, r_diag=r, q_diag=q, pcg_rtol=1e-13).solve(
        rhs_from_obs(g, r, y)
    )
    np.testing.assert_allclose(gamma_q @ eta, dense_map, rtol=1e-8, atol=1e-12)
