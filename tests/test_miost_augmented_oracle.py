"""Extended duality oracle: augmented [G B] == dense OI under structured R_eff.

Proves the spec-§2 marginalization identity EXECUTABLY, for mean AND
field-marginal posterior variance (spec §5 rider 1: the variance side is
where a c-block slicing error hides). The dense side is written from the
spec equations (B_qq - B_qd (B_dd + R_eff)^-1 B_qd^T with R_eff =
diag(sigma2_m) + B Lam B^T), never from the implementation.

If a test here fails, the bug is in the augmented assembly/RSpec — fix
there; never loosen the oracle.
"""

from __future__ import annotations

import math

import numpy as np

from sverdrup.core.grid import GridSpec
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
from sverdrup.core.parameters import ConstantProvider
from sverdrup.methods.miost import Miost
from sverdrup.methods.miost_basis import (
    R_REF,
    BasisSpec,
    DiagonalQ,
    build_g,
    lonlat_to_km,
)
from sverdrup.methods.miost_error_basis import (
    build_b,
    lam_diag,
    mission_hash_ints,
    segment_passes,
)
from sverdrup.methods.miost_rspec import RSpec
from sverdrup.methods.miost_solver import MiostSolver, rhs_from_obs
from sverdrup.methods.miost_windows import WindowPlan

SPEC = BasisSpec(alpha=1.5, l_t_days=10.0, ladder=(320.0, 452.548))  # 2 rungs
# The spec Miost._spec_from builds (default full ladder) — the end-to-end
# tests' dense sides MUST use this one, not the tiny 2-rung SPEC.
FULL_SPEC = BasisSpec(alpha=1.5, l_t_days=10.0)
_DELTAS = {"alg": 0.3, "h2g": -0.1, "j2g": 0.0, "j2n": 0.0}
_LOG_LAM = (-3.5, -4.0)  # log10 m^2: sigma_bias ~ 18 mm, sigma_tilt ~ 10 mm
RSPEC_C = RSpec(deltas=_DELTAS, log_lam_bias=_LOG_LAM[0], log_lam_tilt=_LOG_LAM[1])
RSPEC_D = RSpec(deltas=_DELTAS)


def _fixture(n_per_pass: int = 15) -> dict[str, np.ndarray]:
    """Two missions x two synthetic passes each (~60 obs), window [0, 60].

    Passes are second-scale clusters separated by hours (>> the 60 s gap
    rule); each sweeps a lat chord so tilt modes are constrained.
    """
    rng = np.random.default_rng(23)
    lon_l, lat_l, t_l, mission_l = [], [], [], []
    # (mission, pass start day) — all interior to the [10, 50] day band.
    # j2n and s3a passes included so the DERIVED balance contrast
    # (delta_s3a = -sum = -0.2 here) is exercised through the oracle.
    for mission, day0 in (
        ("alg", 20.0),
        ("alg", 30.0),
        ("h2g", 25.0),
        ("h2g", 35.0),
        ("j2n", 22.0),
        ("s3a", 32.0),
    ):
        frac = np.linspace(0.0, 1.0, n_per_pass)
        t_l.append(day0 + frac * (40.0 / 86400.0))  # a 40 s pass
        lat_l.append(34.5 + frac * 7.0)  # south-to-north chord
        lon_l.append(np.full(n_per_pass, 297.0) + rng.uniform(0, 4) + frac * 2.0)
        mission_l.append(np.full(n_per_pass, mission, dtype=object))
    # span sentinels: _window_mask demands obs spanning [start-L_t, end+L_t]
    # = [-10, 70]; two single-obs passes (s = 0) at the support edges.
    for day_edge in (-10.0, 70.0):
        t_l.append(np.asarray([day_edge]))
        lat_l.append(np.asarray([38.0]))
        lon_l.append(np.asarray([300.0]))
        mission_l.append(np.asarray(["alg"], dtype=object))
    lon = np.concatenate(lon_l)
    lat = np.concatenate(lat_l)
    t = np.concatenate(t_l)
    mission_all = np.concatenate(mission_l).astype(str)
    y = rng.standard_normal(lon.size) * 0.1
    return {"lon": lon, "lat": lat, "t": t, "mission": mission_all, "y": y}


def _dense_sides(
    fx: dict[str, np.ndarray], with_modes: bool, spec: BasisSpec = SPEC
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Independent dense OI mean + variance at query points under R_eff.

    R_eff = diag(sigma2_m) + B Lam B^T (modes) or diag(sigma2_m) (lane-D).
    sigma2_m is hand-built here from the delta dict — NOT via RSpec. All
    algebra is OBS-space (n_obs x n_obs), so any ladder size is cheap.
    """
    els = spec.elements_for_window(0.0)
    q = DiagonalQ(rho=20.0, q_slope=2.0).variances_for(els)
    g = build_g(spec, els, fx["lon"], fx["lat"], fx["t"]).toarray()
    # hand-computed from _DELTAS incl. the derived balance:
    # delta_s3a = -(0.3 - 0.1 + 0.0 + 0.0) = -0.2
    hand_sigma2 = {
        "alg": R_REF * math.exp(0.3),
        "h2g": R_REF * math.exp(-0.1),
        "j2n": R_REF * math.exp(0.0),
        "s3a": R_REF * math.exp(-0.2),
    }
    r_eff = np.diag(np.asarray([hand_sigma2[m] for m in fx["mission"]]))
    if with_modes:
        pt = segment_passes(
            fx["lon"], fx["lat"], fx["t"], mission_hash_ints(fx["mission"])
        )
        bd = build_b(pt).toarray()
        lam = lam_diag(pt.n_pass, 10.0 ** _LOG_LAM[0], 10.0 ** _LOG_LAM[1])
        r_eff = r_eff + bd * lam @ bd.T
    qlon, qlat = np.meshgrid(np.linspace(296, 304, 7), np.linspace(34, 42, 7))
    qx, qy = lonlat_to_km(qlon.ravel(), qlat.ravel())
    gamma_q = spec.evaluate(els, qx, qy, np.full(qx.size, 30.0))
    b_dd = g * q @ g.T
    b_qd = gamma_q * q @ g.T
    b_qq = gamma_q * q @ gamma_q.T
    solve = np.linalg.solve(b_dd + r_eff, np.column_stack([fx["y"][:, None], b_qd.T]))
    mean = b_qd @ solve[:, 0]
    var = np.diag(b_qq - b_qd @ solve[:, 1:])
    return mean, var, gamma_q


def test_extended_duality_oracle_mean_and_variance_with_modes() -> None:
    # Bug caught (mean): hstack order / q_aug concat order swapped, wrong
    # per-mission r assignment. Bug caught (variance): a field-marginal
    # variance route that includes c-columns — it passes every mean test
    # and fails ONLY here (spec §5 rider 1).
    fx = _fixture()
    dense_mean, dense_var, gamma_q = _dense_sides(fx, with_modes=True)

    els = SPEC.elements_for_window(0.0)
    n_elem = els.identity.shape[0]
    q = DiagonalQ(rho=20.0, q_slope=2.0).variances_for(els)
    g = build_g(SPEC, els, fx["lon"], fx["lat"], fx["t"])
    pt = segment_passes(fx["lon"], fx["lat"], fx["t"], mission_hash_ints(fx["mission"]))
    from scipy import sparse  # type: ignore[import-untyped]  # noqa: PLC0415

    g_aug = sparse.hstack([g, build_b(pt)], format="csr")
    q_aug = np.concatenate(
        [q, lam_diag(pt.n_pass, 10.0 ** _LOG_LAM[0], 10.0 ** _LOG_LAM[1])]
    )
    r = RSPEC_C.sigma2_for(mission_hash_ints(fx["mission"]))

    eta_full, _ = MiostSolver(
        g_aug, r_diag=r, q_diag=q_aug, pcg_rtol=1e-13, pcg_maxiter=20000
    ).solve(rhs_from_obs(g_aug, r, fx["y"]))
    np.testing.assert_allclose(
        gamma_q @ np.asarray(eta_full)[:n_elem], dense_mean, rtol=1e-8, atol=1e-12
    )

    # variance: dense A_aug^-1, eta-eta slice, mapped through Gamma_q
    ga = g_aug.toarray()
    a_aug = ga.T / r @ ga + np.diag(1.0 / q_aug)
    a_inv_ee = np.linalg.inv(a_aug)[:n_elem, :n_elem]
    var_aug = np.diag(gamma_q @ a_inv_ee @ gamma_q.T)
    np.testing.assert_allclose(var_aug, dense_var, rtol=1e-8, atol=1e-14)


def test_solve_window_end_to_end_matches_dense_oracle() -> None:
    # The ACTUAL Miost._solve_window augmented assembly (through
    # Miost.solve + mean_at) against the independent dense mean.
    # Bug caught: _solve_window building B from the wrong obs subset,
    # forgetting the eta slice (shape blowup in mean_at), or feeding the
    # scalar R into an augmented config.
    fx = _fixture()
    dense_mean, _, _ = _dense_sides(fx, with_modes=True, spec=FULL_SPEC)
    obs = ObsWindow.from_arrays(
        lon=fx["lon"],
        lat=fx["lat"],
        time=fx["t"],
        values=fx["y"],
        error_model=DiagonalErrorModel(np.full(fx["y"].size, R_REF)),
        mission=fx["mission"],
    )
    grid = GridSpec.lonlat(np.linspace(296, 304, 7), np.linspace(34, 42, 7))
    m = Miost(
        plan=WindowPlan(starts=(0.0,)),
        pcg_rtol=1e-13,
        pcg_maxiter=20000,
        rspec=RSPEC_C,
    )
    params = ConstantProvider(
        {
            "spacing_alpha": 1.5,
            "log10_rho": math.log10(20.0),
            "q_slope": 2.0,
            "l_t_days": 10.0,
        }
    )
    dist = m.solve(obs, grid, params, 30.0)
    np.testing.assert_allclose(
        np.asarray(dist.mean).ravel(), dense_mean, rtol=1e-8, atol=1e-12
    )


def test_lane_d_deltas_only_matches_dense_diagonal_r() -> None:
    # Lane-D restriction: per-mission diag R, modes COLUMN-ABSENT (spec §2
    # rider 3 — structural absence, never Lambda=0).
    # Bug caught: B columns built despite log_lam None (Lambda=0 would
    # divide by zero in Q_aug^-1 — structural absence is the only correct
    # reading), or per-mission r not reaching _solve_window.
    fx = _fixture()
    dense_mean, _, _ = _dense_sides(fx, with_modes=False, spec=FULL_SPEC)
    obs = ObsWindow.from_arrays(
        lon=fx["lon"],
        lat=fx["lat"],
        time=fx["t"],
        values=fx["y"],
        error_model=DiagonalErrorModel(np.full(fx["y"].size, R_REF)),
        mission=fx["mission"],
    )
    grid = GridSpec.lonlat(np.linspace(296, 304, 7), np.linspace(34, 42, 7))
    m = Miost(
        plan=WindowPlan(starts=(0.0,)),
        pcg_rtol=1e-13,
        pcg_maxiter=20000,
        rspec=RSPEC_D,
    )
    params = ConstantProvider(
        {
            "spacing_alpha": 1.5,
            "log10_rho": math.log10(20.0),
            "q_slope": 2.0,
            "l_t_days": 10.0,
        }
    )
    dist = m.solve(obs, grid, params, 30.0)
    np.testing.assert_allclose(
        np.asarray(dist.mean).ravel(), dense_mean, rtol=1e-8, atol=1e-12
    )


def test_lambda_to_zero_continuity_vs_column_absent() -> None:
    """Lambda = 1e-12 m^2 solution == column-absent solution at rtol 1e-9.

    Tolerance derivation (spec §19.1, fixed here): the mode prior weight
    relative to the obs-error floor is 1e-12 / R_REF = 1e-12 / 9e-4 ~
    1.1e-9 — the mode contribution to the mean is O(that) RELATIVE TO THE
    FIELD SCALE (an absolute bound of ~1e-9 on this O(1) field); with
    pcg_rtol tightened to 1e-13 the solver residual is dominated by it.
    Hence rtol 1e-9 for O(1) map values plus atol 1e-10 (one decade under
    the field-scale bound) at zero-crossings, where a per-point relative
    reading of the bound is meaningless.
    Bug caught: a numerical seam between the Lambda box floor and the
    structural column-absent restriction (anchor embedding, spec §4).
    """
    fx = _fixture()
    obs = ObsWindow.from_arrays(
        lon=fx["lon"],
        lat=fx["lat"],
        time=fx["t"],
        values=fx["y"],
        error_model=DiagonalErrorModel(np.full(fx["y"].size, R_REF)),
        mission=fx["mission"],
    )
    grid = GridSpec.lonlat(np.linspace(296, 304, 7), np.linspace(34, 42, 7))
    params = ConstantProvider(
        {
            "spacing_alpha": 1.5,
            "log10_rho": math.log10(20.0),
            "q_slope": 2.0,
            "l_t_days": 10.0,
        }
    )
    plan = WindowPlan(starts=(0.0,))
    tiny = Miost(
        plan=plan,
        pcg_rtol=1e-13,
        pcg_maxiter=20000,
        rspec=RSpec(deltas=_DELTAS, log_lam_bias=-12.0, log_lam_tilt=-12.0),
    )
    absent = Miost(plan=plan, pcg_rtol=1e-13, pcg_maxiter=20000, rspec=RSPEC_D)
    m_tiny = np.asarray(tiny.solve(obs, grid, params, 30.0).mean)
    m_abs = np.asarray(absent.solve(obs, grid, params, 30.0).mean)
    np.testing.assert_allclose(m_tiny, m_abs, rtol=1e-9, atol=1e-10)


def test_gauge_common_delta_shift_equals_rho_shift_for_mean() -> None:
    """Joint (cR, cQ) scaling leaves the posterior mean EXACTLY flat.

    A common shift of all delta_m scales R by c = e^shift; Q = rho*R_REF*
    (lam/lam_ref)^q scales by c under rho -> c*rho — the spec-§4 identity.
    The relative-residual PCG preserves it under inexact arithmetic too
    (scaled RHS => proportionally scaled residuals => same iterates).
    Bug caught: an absolute-tolerance term or preconditioner asymmetry
    breaking the flat direction — per-mission R would then be spuriously
    identifiable in its absolute level.

    Asserted on the MEAN at query points (the §4 claim is about mean maps
    — tiny individual coefficients in near-null directions carry FP-level
    wiggle that the map contraction cancels).
    """
    fx = _fixture()
    els = SPEC.elements_for_window(0.0)
    q = DiagonalQ(rho=20.0, q_slope=2.0).variances_for(els)
    g = build_g(SPEC, els, fx["lon"], fx["lat"], fx["t"])
    r = np.full(fx["y"].size, R_REF)
    c = math.exp(0.37)
    qlon, qlat = np.meshgrid(np.linspace(296, 304, 7), np.linspace(34, 42, 7))
    qx, qy = lonlat_to_km(qlon.ravel(), qlat.ravel())
    gamma_q = SPEC.evaluate(els, qx, qy, np.full(qx.size, 30.0))
    eta_base, _ = MiostSolver(
        g, r_diag=r, q_diag=q, pcg_rtol=1e-13, pcg_maxiter=20000
    ).solve(rhs_from_obs(g, r, fx["y"]))
    eta_scaled, _ = MiostSolver(
        g, r_diag=c * r, q_diag=c * q, pcg_rtol=1e-13, pcg_maxiter=20000
    ).solve(rhs_from_obs(g, c * r, fx["y"]))
    # tolerance = the solver-precision bound: converged rel residual ~1e-13
    # amplifies to ~2e-12 absolute on an O(1) map; flatness is EXACT in
    # exact arithmetic (the identity, not the solver, is under test).
    np.testing.assert_allclose(
        gamma_q @ eta_scaled, gamma_q @ eta_base, rtol=1e-10, atol=1e-11
    )
