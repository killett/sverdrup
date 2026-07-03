"""Tests for MIOST CSR G/S builders, DiagonalQ/R, representer (seams b, c; Tier 2)."""

from __future__ import annotations

import numpy as np
import pytest

from sverdrup.methods.miost_basis import (
    BasisSpec,
    DiagonalQ,
    build_g,
    lonlat_to_km,
)

SPEC = BasisSpec(alpha=1.5, l_t_days=10.0)  # coarse alpha keeps the test small
RNG = np.random.default_rng(7)


def _small_obs(n: int = 40) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    lon = RNG.uniform(297, 303, n)
    lat = RNG.uniform(35, 41, n)
    t = RNG.uniform(5, 55, n)
    return lon, lat, t


def test_g_matches_dense_evaluate() -> None:
    """CSR assembly == dense analytic evaluation (bug: wrong sparsity window/offset)."""
    els = SPEC.elements_for_window(0.0)
    lon, lat, t = _small_obs()
    g = build_g(SPEC, els, lon, lat, t)
    x, y = lonlat_to_km(lon, lat)
    dense = SPEC.evaluate(els, x, y, t)
    np.testing.assert_allclose(g.toarray(), dense, atol=1e-14)


def test_s_matches_dense_evaluate_via_taper() -> None:
    """S (spatial-only) times the day taper == full dense evaluation at that day.

    Bug caught: wrong column layout / temporal factor leaking into S.
    """
    from sverdrup.methods.miost_basis import build_s, temporal_taper

    els = SPEC.elements_for_window(0.0)
    lon = np.linspace(296.0, 304.0, 7)
    lat = np.linspace(34.5, 41.5, 7)
    s = build_s(SPEC, els, lon, lat)
    x, y = lonlat_to_km(lon, lat)
    for day in (12.0, 30.0):
        dense = SPEC.evaluate(els, x, y, np.full(lon.size, day))
        np.testing.assert_allclose(
            s.toarray() * temporal_taper(SPEC, els, day)[None, :], dense, atol=1e-14
        )


def test_adjoint_identity() -> None:
    """Seam (b): <G eta, r> == <eta, G^T r> to machine precision."""
    els = SPEC.elements_for_window(0.0)
    lon, lat, t = _small_obs()
    g = build_g(SPEC, els, lon, lat, t)
    eta = RNG.standard_normal(g.shape[1])
    r = RNG.standard_normal(g.shape[0])
    assert (g @ eta) @ r == pytest.approx(eta @ (g.T @ r), rel=1e-12)


def test_q_lam_ref_gauge_inert() -> None:
    """Seam (c)/D8: changing lam_ref with Q_scale retuned analytically -> identical q.

    q_p = rho*R_REF*(lam/ref)^s ; ref 300->400 is offset by rho' = rho*(400/300)^s.
    """
    q1 = DiagonalQ(rho=10.0, q_slope=2.0, lam_ref=300.0).variances(SPEC)
    q2 = DiagonalQ(
        rho=10.0 * (400.0 / 300.0) ** 2.0, q_slope=2.0, lam_ref=400.0
    ).variances(SPEC)
    np.testing.assert_allclose(q1, q2, rtol=1e-12)


def test_q_variances_for_custom_ladder() -> None:
    """variances_for prices q at the element's ACTUAL wavelength, not the default LADDER.

    Bug caught: indexing the module LADDER by scale_idx — a custom 2-rung ladder
    (320, 452.548) would get q priced at 80/113 km.
    """
    spec = BasisSpec(alpha=1.5, l_t_days=10.0, ladder=(320.0, 452.548))
    els = spec.elements_for_window(0.0)
    q = DiagonalQ(rho=10.0, q_slope=2.0).variances_for(els)
    lam = np.where(els.identity[:, 0] == 0, 320.0, 452.548)
    expected = 10.0 * (0.03**2) * (lam / 300.0) ** 2.0
    np.testing.assert_allclose(q, expected, rtol=1e-12)


def test_representer_negative_lobe() -> None:
    """Tier 2 (U2022 Fig. 4): the equivalent covariance row crosses zero."""
    els = SPEC.elements_for_window(0.0)
    q = DiagonalQ(rho=10.0, q_slope=2.0).variances_for(els)
    xs = np.linspace(0.0, 850.0, 200)
    row = SPEC.evaluate(els, xs, np.full(200, 550.0), np.full(200, 30.0))
    center = SPEC.evaluate(els, np.array([425.0]), np.array([550.0]), np.array([30.0]))
    rep = (center * q) @ row.T  # (1, 200)
    assert rep[0].max() > 0 and rep[0].min() < 0
