"""Augmented member sampling tests (plan Task 4 — "err" CRN axis + teeth).

The hazard this file exists to kill (spec §5 rider 3, named): a STRUCTURED
solve fed WHITE-noise perturbations is a wrong ensemble that passes every
mean test — its member variance silently under-disperses by the mode
share. The teeth companion demonstrates that failure is DETECTED by the
variance-consistency statistic; the broken sampler lives only as a
test-local injection, never a code path.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

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
from sverdrup.methods.miost_crn import err_noise, obs_noise
from sverdrup.methods.miost_error_basis import (
    build_b,
    err_identity,
    lam_diag,
    mission_hash_ints,
    segment_passes,
)
from sverdrup.methods.miost_rspec import RSpec
from sverdrup.methods.miost_windows import WindowPlan

SPEC = BasisSpec(alpha=1.5, l_t_days=10.0, ladder=(320.0, 452.548))  # 2 rungs
FULL_SPEC = BasisSpec(alpha=1.5, l_t_days=10.0)  # what Miost._spec_from builds
_DELTAS = {"alg": 0.3, "h2g": -0.1, "j2g": 0.0, "j2n": 0.0}
_RSPEC = RSpec(deltas=_DELTAS, log_lam_bias=-3.0, log_lam_tilt=-3.5)
_GRID = GridSpec.lonlat(np.linspace(296, 304, 5), np.linspace(34, 42, 5))
_PARAMS = ConstantProvider(
    {
        "spacing_alpha": 1.5,
        "log10_rho": math.log10(20.0),
        "q_slope": 2.0,
        "l_t_days": 10.0,
    }
)
_ROOT = 424242


def _obs(n_per_pass: int = 10) -> ObsWindow:
    """Two missions x two passes + span sentinels (window [0, 60])."""
    rng = np.random.default_rng(51)
    lon_l, lat_l, t_l, mission_l = [], [], [], []
    for mission, day0 in (("alg", 20.0), ("alg", 30.0), ("h2g", 25.0), ("h2g", 35.0)):
        frac = np.linspace(0.0, 1.0, n_per_pass)
        t_l.append(day0 + frac * (40.0 / 86400.0))
        lat_l.append(34.5 + frac * 7.0)
        lon_l.append(np.full(n_per_pass, 297.0) + rng.uniform(0, 4) + frac * 2.0)
        mission_l.append(np.full(n_per_pass, mission, dtype=object))
    for day_edge in (-10.0, 70.0):
        t_l.append(np.asarray([day_edge]))
        lat_l.append(np.asarray([38.0]))
        lon_l.append(np.asarray([300.0]))
        mission_l.append(np.asarray(["alg"], dtype=object))
    lon = np.concatenate(lon_l)
    return ObsWindow.from_arrays(
        lon=lon,
        lat=np.concatenate(lat_l),
        time=np.concatenate(t_l),
        values=rng.standard_normal(lon.size) * 0.1,
        error_model=DiagonalErrorModel(np.full(lon.size, R_REF)),
        mission=np.concatenate(mission_l).astype(str),
    )


def _method(m: int = 0) -> Miost:
    return Miost(
        plan=WindowPlan(starts=(0.0,)),
        pcg_rtol=1e-11,
        pcg_maxiter=20000,
        members=m,
        member_root=_ROOT if m else None,
        rspec=_RSPEC,
    )


def test_err_noise_is_identity_keyed_not_positional() -> None:
    # The same identity rows in a DIFFERENT order must return the same
    # values, per-row; and a subset (a window seeing fewer passes) must
    # reproduce the shared rows exactly — the window-independence that
    # keeps member fields coherent through the blend (spec §5 rider 2).
    # Bug caught: draws keyed on array position instead of identity bytes.
    ident = np.ascontiguousarray(
        [[111, 1000, 0], [111, 1000, 1], [222, 1000, 0], [222, 5000, 1]],
        dtype=np.int64,
    )
    lam = np.asarray([1e-3, 1e-4, 1e-3, 1e-4])
    full = err_noise(2, ident, lam, _ROOT)
    perm = np.asarray([3, 0, 2, 1])
    reordered = err_noise(2, ident[perm], lam[perm], _ROOT)
    assert reordered.tolist() == full[perm].tolist()
    subset = err_noise(2, ident[1:3], lam[1:3], _ROOT)
    assert subset.tolist() == full[1:3].tolist()


def test_err_axis_stream_is_separated_from_obs_axis() -> None:
    # Craft an err identity row whose BYTES could collide with an obs
    # identity row; the axis key must still separate the streams.
    # Bug caught: a shared/omitted axis tag — the new err draws would
    # perturb (correlate with) the existing obs stream, breaking the
    # Task-3 CRN no-perturbation claim from the other side.
    row = np.ascontiguousarray([[111, 1000, 0]], dtype=np.int64)
    as_float = np.ascontiguousarray(row.astype(np.float64)[:, :3])
    obs_row = np.column_stack([as_float, np.zeros((1, 1))])
    var = np.asarray([1e-3])
    e = err_noise(0, row, var, _ROOT)
    o = obs_noise(0, obs_row, var, _ROOT)
    assert e[0] != o[0]


def test_member_mean_equals_deterministic_augmented_solve() -> None:
    # D6 re-instantiated at an augmented config (spec §5 rider 4): the
    # ensemble mean IS the deterministic augmented mean, rtol 1e-12.
    # Bug caught: the augmented member RHS built from a different assembly
    # than the point path (e.g. scalar R in one of the two).
    obs = _obs()
    det = _method(0).solve(obs, _GRID, _PARAMS, 30.0)
    ens = _method(4).solve(obs, _GRID, _PARAMS, 30.0)
    np.testing.assert_allclose(
        np.asarray(ens.mean), np.asarray(det.mean), rtol=1e-12, atol=1e-15
    )


def test_retention_slicing_field_block_only() -> None:
    # The retained member store holds FIELD-BLOCK anomaly rows only
    # (spec §12: store size unchanged by augmentation).
    # Bug caught: c rows retained — ~480 extra rows per window per member
    # ballooning the store and leaking solver-internal state.
    obs = _obs()
    ens = _method(3).solve(obs, _GRID, _PARAMS, 30.0)
    raw = ens.underlying  # type: ignore[union-attr]
    n_elem = FULL_SPEC.elements_for_window(0.0).identity.shape[0]
    for wid in raw._anoms:
        assert raw._etas_a[wid].shape == (n_elem,)
        assert raw._anoms[wid].shape == (n_elem, 3)


def test_persisted_kind_versioned_and_refused_by_pattern(tmp_path: Path) -> None:
    # Augmented-config ensembles persist under a NEW kind tag; load_state
    # accepts the known tags and refuses others (spec §11).
    # Bug caught: augmented ensembles persisted under the scalar-era tag —
    # a consumer would silently treat structured-R provenance as scalar.
    from sverdrup.distributions.miost_ensemble import (
        KIND,
        KIND_AUG,
        MiostEnsembleDistribution,
    )

    obs = _obs()
    raw_aug = _method(3).solve(obs, _GRID, _PARAMS, 30.0).underlying  # type: ignore[union-attr]
    assert raw_aug.state_kind == KIND_AUG
    p = tmp_path / "aug.npz"
    raw_aug.save_state(p)
    back = MiostEnsembleDistribution.load_state(p)
    assert back.state_kind == KIND_AUG

    scalar = Miost(plan=WindowPlan(starts=(0.0,)), members=3, member_root=_ROOT).solve(
        obs, _GRID, _PARAMS, 30.0
    )
    assert scalar.underlying.state_kind == KIND  # type: ignore[union-attr]


def _analytic_and_empirical(
    m: int,
    break_err: bool = False,
    rspec: RSpec = _RSPEC,
    on_chord: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    """Empirical member variance vs analytic augmented posterior at points.

    Small case at the TINY 2-rung spec (the dense analytic side needs an
    invertible A_aug): members built through the SHARED construction
    (``member_rhs_matrix`` with the "err" identities — exactly what
    ``sample_members`` calls) and the production ``MiostSolver``. The
    analytic side is the dense (A_aug^-1)_etaeta slice mapped through
    Gamma at query points — the same independent construction the Task-2
    oracle proved against obs-space OI.

    ``break_err=True`` builds the WHITE-FED RHS instead: identical except
    c̃ ≡ 0 — a test-LOCAL loop, never a code path (spec §5 rider 3).
    """
    from sverdrup.methods.miost import _obs_identity, member_rhs_matrix
    from sverdrup.methods.miost_solver import MiostSolver, rhs_from_obs

    obs = _obs()
    coords = obs.coords()
    lon, lat, t = coords[:, 0], coords[:, 1], coords[:, 2]
    y = obs.values()
    els = SPEC.elements_for_window(0.0)
    n_elem = els.identity.shape[0]
    q = DiagonalQ(rho=20.0, q_slope=2.0).variances_for(els)
    g = build_g(SPEC, els, lon, lat, t)
    assert obs.mission is not None
    mh = mission_hash_ints(obs.mission)
    pt = segment_passes(lon, lat, t, mh)
    from scipy import sparse  # type: ignore[import-untyped]  # noqa: PLC0415

    g_aug = sparse.hstack([g, build_b(pt)], format="csr")
    lam = lam_diag(pt.n_pass, rspec.lam_bias, rspec.lam_tilt)
    q_aug = np.concatenate([q, lam])
    r = rspec.sigma2_for(mh)
    err_id = err_identity(pt)
    obs_id = _obs_identity(lon, lat, t, obs.mission)

    if on_chord:
        # query ON the pass chords at the pass days — where the mode share
        # of the posterior variance is large (the teeth fixture geometry)
        qpts: list[tuple[float, float, float]] = []
        for day0 in (20.0, 30.0, 25.0, 35.0):
            idx = np.nonzero(np.abs(t - day0) < 0.1)[0][2:9:2]
            qpts.extend((lon[i], lat[i], day0) for i in idx)
        qarr = np.asarray(qpts)
        qx, qy = lonlat_to_km(qarr[:, 0], qarr[:, 1])
        gamma_q = SPEC.evaluate(els, qx, qy, qarr[:, 2])
    else:
        qlon, qlat = np.meshgrid(np.linspace(297, 303, 4), np.linspace(35, 41, 4))
        qx, qy = lonlat_to_km(qlon.ravel(), qlat.ravel())
        gamma_q = SPEC.evaluate(els, qx, qy, np.full(qx.size, 27.0))

    ga = g_aug.toarray()
    a_aug = ga.T / r @ ga + np.diag(1.0 / q_aug)
    a_inv_ee = np.linalg.inv(a_aug)[:n_elem, :n_elem]
    analytic = np.diag(gamma_q @ a_inv_ee @ gamma_q.T)

    if break_err:
        # WHITE-FED members: same construction with c̃ zeroed, test-local.
        from sverdrup.methods.miost_crn import coef_noise  # noqa: PLC0415

        base = rhs_from_obs(g_aug, r, y)
        b = np.empty((q_aug.size, m))
        for i in range(m):
            eta_t = coef_noise(i, els.identity, q, _ROOT)
            prior = np.concatenate([eta_t, np.zeros(err_id.shape[0])])
            eps = obs_noise(i, obs_id, r, _ROOT)
            b[:, i] = base + prior / q_aug + g_aug.T @ (eps / r)
    else:
        b = member_rhs_matrix(
            g_aug, r, y, q_aug, obs_id, els.identity, m, _ROOT, err_ident=err_id
        )
    solver = MiostSolver(
        g_aug, r_diag=r, q_diag=q_aug, pcg_rtol=1e-11, pcg_maxiter=20000
    )
    eta_full, _ = solver.solve(rhs_from_obs(g_aug, r, y))
    members, _ = solver.solve(b)
    anoms = np.asarray(members)[:n_elem] - np.asarray(eta_full)[:n_elem, None]
    fields = gamma_q @ anoms  # member anomaly fields at the query points
    empirical = fields.var(axis=1, ddof=1)
    return np.asarray(empirical), analytic


def test_member_variance_consistency_augmented() -> None:
    """Empirical member variance == analytic augmented posterior, 5·SE.

    Tolerance derivation (spec §5 / §19.4): the sample variance of m
    N(0, v) draws has Var = 2 v² / (m − 1) (χ² arithmetic), so
    SE = v·√(2/(m−1)) and the 5·SE band at m = 2000 is 0.158·v. At the
    m = 100 acceptance runs the same statistic carries 5·√(2/99) = 0.711·v
    — recorded here as the acceptance-run consistency row's tolerance
    (``variance_consistency_rtol``).

    Bug caught: any augmented-sampler defect that moves the member
    variance beyond MC noise — wrong Λ in the c̃ draws, wrong per-mission
    ε' variances, mis-sliced anomalies.
    """
    from sverdrup.distributions.miost_ensemble import variance_consistency_rtol

    m = 2000
    empirical, analytic = _analytic_and_empirical(m)
    rtol = variance_consistency_rtol(m)
    assert rtol == pytest.approx(5.0 * math.sqrt(2.0 / (m - 1)), rel=1e-12)
    np.testing.assert_allclose(empirical, analytic, rtol=rtol)
    # the acceptance-run row (m=100) tolerance, recorded: 5*sqrt(2/99)
    assert variance_consistency_rtol(100) == pytest.approx(0.71067, abs=2e-5)


def test_teeth_white_fed_ensemble_fails_the_same_statistic() -> None:
    """The c̃-omitted (white-fed) sampler FAILS variance consistency ≫ tol.

    Fixture constructed so the mode share of the posterior variance is
    large: Λ at log10 (−2.6, −2.2) with ~10 obs/pass and query points ON
    the pass chords — measured analytic white-fed deficit share 0.77
    median / 0.85 max of the posterior variance there (probed at fixture
    design; spec §5 "large Λ, few obs per pass"). Omitting c̃ starves the
    members of that share, far beyond the 5·SE band.

    Bug caught (the §5 rider-3 hazard, demonstrated): a structured solve
    fed white-only perturbations passes every mean test and is only
    caught HERE — if this test ever passes with the broken sampler, the
    statistic has lost its teeth.
    """
    from sverdrup.distributions.miost_ensemble import variance_consistency_rtol

    m = 1000
    teeth_rspec = RSpec(deltas=_DELTAS, log_lam_bias=-2.6, log_lam_tilt=-2.2)
    empirical, analytic = _analytic_and_empirical(
        m, break_err=True, rspec=teeth_rspec, on_chord=True
    )
    rtol = variance_consistency_rtol(m)
    rel_dev = (analytic - empirical) / analytic  # signed: a DEFICIT
    # the deficit must exceed the tolerance band by a clear margin at the
    # median query point — not a marginal trip (expected ~0.77 vs 2×0.224)
    assert np.median(rel_dev) > 2.0 * rtol
