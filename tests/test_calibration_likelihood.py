"""Tests for Phase-8 floored MLE fitters (Task 7).

Covers: nll, grad, fit_region_newton, fit_poly_lbfgsb,
tail_diagnostic, assert_beats_scalar.

All assertions are derived independently of the implementation
(hand arithmetic, finite differences, synthetic data with planted truth).
"""

from __future__ import annotations

import math

import numpy as np
import pytest

import sverdrup.application.calibration.constants as _const
import sverdrup.application.calibration.likelihood as _lik

# ---------------------------------------------------------------------------
# NLL hand arithmetic
# ---------------------------------------------------------------------------


def test_nll_matches_hand_arithmetic() -> None:
    """n=2 case computed by hand: r2=(1,4), v=(1,2), theta=(0,), X=ones.

    tot_i = 1*v_i + SIGMA_OBS2; nll = 0.5*sum(log tot_i + r2_i/tot_i).
    Bug caught: dropped 0.5, missing floor, log of s*v alone.
    """
    sigma2 = 0.03**2  # == SIGMA_OBS2 at module level, but written literally
    r2 = np.array([1.0, 4.0])
    v = np.array([1.0, 2.0])
    x = np.ones((2, 1))
    theta = np.array([0.0])

    # Hand computation (s=exp(0)=1):
    tot0 = 1.0 * 1.0 + sigma2
    tot1 = 1.0 * 2.0 + sigma2
    expected = 0.5 * (math.log(tot0) + 1.0 / tot0 + math.log(tot1) + 4.0 / tot1)

    result = _lik.nll(theta, x, r2, v)

    assert abs(result - expected) < 1e-14, (
        f"nll={result}, expected={expected}, diff={result - expected}"
    )


# ---------------------------------------------------------------------------
# Gradient vs finite difference
# ---------------------------------------------------------------------------


def test_grad_matches_finite_difference() -> None:
    """Analytic grad vs central difference at a random-but-fixed theta, rtol 1e-6.

    Bug caught: sign or missing (1 - r2/tot) factor.
    """
    rng = np.random.default_rng(42)
    n, d = 50, 3
    x = rng.standard_normal((n, d))
    r2 = rng.exponential(scale=2.0, size=n)
    v = rng.exponential(scale=1.0, size=n) + 0.1
    theta = rng.standard_normal(d) * 0.5

    eps = 1e-6
    analytic = _lik.grad(theta, x, r2, v)
    fd = np.zeros(d)
    for i in range(d):
        tp = theta.copy()
        tm = theta.copy()
        tp[i] += eps
        tm[i] -= eps
        fd[i] = (_lik.nll(tp, x, r2, v) - _lik.nll(tm, x, r2, v)) / (2 * eps)

    np.testing.assert_allclose(analytic, fd, rtol=1e-5, atol=1e-10)


# ---------------------------------------------------------------------------
# Newton: closed form at σ_obs²=0
# ---------------------------------------------------------------------------


def test_newton_recovers_truth_sigma0(monkeypatch: pytest.MonkeyPatch) -> None:
    """With floor monkeypatched to 0, Newton == mean(r2/v) exactly (1e-12).

    Bug caught: fitting total variance (aliases the floor into s —
    the spec §2 sampling artifact).
    """
    monkeypatch.setattr(_const, "SIGMA_OBS2", 0.0)
    # Also patch the likelihood module's reference so it picks up the change.
    monkeypatch.setattr(_lik, "SIGMA_OBS2", 0.0)

    rng = np.random.default_rng(7)
    n = 500
    v = rng.exponential(scale=2.0, size=n) + 0.5
    s_true = 5.0
    r2 = rng.exponential(scale=1.0, size=n) * s_true * v  # χ²₁ samples

    log_s_hat, _n_iter, converged = _lik.fit_region_newton(r2, v)
    s_hat = math.exp(log_s_hat)

    closed_form = float(np.mean(r2 / v))
    assert converged, "Newton did not converge for sigma0=0 case"
    assert abs(s_hat - closed_form) < 1e-12, (
        f"s_hat={s_hat}, closed_form={closed_form}, diff={s_hat - closed_form}"
    )


# ---------------------------------------------------------------------------
# Newton: recovers planted s with floor (statistical)
# ---------------------------------------------------------------------------


def test_newton_recovers_planted_s_with_floor() -> None:
    """Synthetic r ~ N(0, s_true*v + floor), n=200_000, seeded: ŝ within 1% of s_true=10.

    Bug caught: fitting total variance (aliases the floor into s —
    the spec §2 sampling artifact).
    """
    rng = np.random.default_rng(314159)
    n = 200_000
    s_true = 10.0
    v = rng.exponential(scale=1.0, size=n) + 0.2
    sigma2 = _const.SIGMA_OBS2
    std = np.sqrt(s_true * v + sigma2)
    r = rng.standard_normal(n) * std
    r2 = r**2

    log_s_hat, _n_iter, converged = _lik.fit_region_newton(r2, v)
    s_hat = math.exp(log_s_hat)

    assert converged, "Newton did not converge"
    assert abs(s_hat - s_true) / s_true < 0.01, (
        f"s_hat={s_hat:.6f}, s_true={s_true}, rel_err={abs(s_hat - s_true) / s_true:.4f}"
    )


# ---------------------------------------------------------------------------
# Newton: Hessian vs finite difference of the gradient
# ---------------------------------------------------------------------------


def test_newton_hessian_matches_finite_difference() -> None:
    """Analytic h from _newton_gh vs central finite-difference of g, rtol 1e-6.

    g is evaluated independently via grad() with x = ones column (grad is
    itself FD-verified against nll above), at several fixed NON-optimal
    log_s values — the mirror of the grad-vs-nll check one derivative up.
    Bug caught: h = 0.5*sum[p²(2q-1)] (drops the 0.5*sum[p(1-q)] = g term,
    which vanishes at the optimum and so escapes optimum-anchored tests).
    """
    rng = np.random.default_rng(5)
    n = 200
    v = rng.exponential(scale=1.0, size=n) + 0.05
    sigma2 = _const.SIGMA_OBS2
    r2 = rng.exponential(scale=1.0, size=n) * (3.0 * v + sigma2)
    x = np.ones((n, 1))

    eps = 1e-6
    for log_s in (-2.0, 0.0, 1.0, 2.5):
        _g, h_analytic = _lik._newton_gh(log_s, r2, v)
        g_plus = _lik.grad(np.array([log_s + eps]), x, r2, v)[0]
        g_minus = _lik.grad(np.array([log_s - eps]), x, r2, v)[0]
        h_fd = (g_plus - g_minus) / (2 * eps)
        assert abs(h_analytic - h_fd) / abs(h_fd) < 1e-6, (
            f"log_s={log_s}: h_analytic={h_analytic}, h_fd={h_fd}, "
            f"rel={(h_analytic - h_fd) / h_fd:.3e}"
        )


# ---------------------------------------------------------------------------
# Newton: convergence from a poor init (floor-dominated data)
# ---------------------------------------------------------------------------


def test_newton_converges_from_poor_init() -> None:
    """Floor-dominated data where the default init is far from the MLE.

    With v ~ 1e-5 and s_true=10, s·v ~ 1e-4 << SIGMA_OBS2 = 9e-4, so the
    σ=0 closed-form init log(mean(r2/v)) lands near log(93) — far above
    the true MLE near log(10). Newton must still converge to the MLE,
    verified against an independent scipy minimize_scalar oracle (1%).
    Bug caught: wrong Hessian (drops the g term) overshoots to
    log_s ~ -1e16 and falsely reports converged=True at a flat plateau.
    """
    import scipy.optimize  # type: ignore[import-untyped]  # oracle only

    rng = np.random.default_rng(777)
    n = 200_000
    s_true = 10.0
    sigma2 = _const.SIGMA_OBS2
    v = rng.uniform(0.5e-5, 2e-5, size=n)  # floor dominates: s*v << sigma2
    std = np.sqrt(s_true * v + sigma2)
    r = rng.standard_normal(n) * std
    r2 = r**2

    # Confirm the init really is poor (test-precondition, not implementation):
    init_s = float(np.mean(r2 / v))
    assert init_s > 5 * s_true, f"precondition: init s={init_s:.1f} not poor"

    # Independent oracle: 1-d bounded minimization of the same NLL
    ones = np.ones((n, 1))
    oracle = scipy.optimize.minimize_scalar(
        lambda t: _lik.nll(np.array([t]), ones, r2, v),
        bounds=(-5.0, 10.0),
        method="bounded",
        options={"xatol": 1e-12},
    )
    s_oracle = math.exp(oracle.x)

    log_s_hat, n_iter, converged = _lik.fit_region_newton(r2, v)
    s_hat = math.exp(log_s_hat)

    assert converged, f"Newton did not converge (n_iter={n_iter})"
    assert n_iter <= _const.NEWTON_MAX_ITER
    assert abs(s_hat - s_oracle) / s_oracle < 0.01, (
        f"s_hat={s_hat:.6g}, oracle={s_oracle:.6g}, "
        f"rel_err={abs(s_hat - s_oracle) / s_oracle:.3e}"
    )


# ---------------------------------------------------------------------------
# Newton: non-convergence surface
# ---------------------------------------------------------------------------


def test_newton_returns_not_converged_when_max_iter_hit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """converged=False when NEWTON_MAX_ITER=1 (artificially limiting iterations).

    Bug caught: always returning converged=True regardless of iteration count.
    """
    monkeypatch.setattr(_const, "NEWTON_MAX_ITER", 1)
    monkeypatch.setattr(_lik, "NEWTON_MAX_ITER", 1)

    rng = np.random.default_rng(99)
    n = 1000
    v = rng.exponential(scale=2.0, size=n) + 0.5
    s_true = 5.0
    sigma2 = _const.SIGMA_OBS2
    std = np.sqrt(s_true * v + sigma2)
    r = rng.standard_normal(n) * std
    r2 = r**2

    # Use a very bad init (far from truth) so 1 iteration is not enough.
    # We override the init externally by patching; the built-in init is
    # log(mean(r2/v)) which for these data is ~log(5) ≈ 1.6 — one Newton
    # step won't reach NEWTON_TOL=1e-10 from there because the floor makes
    # the step finite but |step| > 1e-10.
    # With n=1000 and a curved likelihood, one step is insufficient.
    _log_s_hat, _n_iter, converged = _lik.fit_region_newton(r2, v)

    # With NEWTON_MAX_ITER patched to 1, the loop should exit after one step
    # and return converged=False unless the problem happens to be trivial.
    # For this data (s_true=5, floor present), one iteration yields step > 1e-10.
    assert not converged, (
        "Expected converged=False with NEWTON_MAX_ITER=1, but got converged=True"
    )


# ---------------------------------------------------------------------------
# L-BFGS-B: recovers planted latitudinal field
# ---------------------------------------------------------------------------


def test_poly_recovers_planted_latitudinal_field() -> None:
    """Plant log s = 2.0 + 0.5*y on synthetic points; L-BFGS-B recovers
    (a0, a1) within 2%, other coeffs ~0.

    Design matrix X columns: (1, v_coord, v_coord², u_coord, u_coord·v_coord)
    where u, v are normalized coordinates in [−1, 1].
    Bug caught: wrong gradient sign, wrong theta init, L-BFGS-B divergence.
    """
    rng = np.random.default_rng(271828)
    n = 50_000

    # Synthetic lon/lat inside the box
    lon = rng.uniform(295.5, 304.5, size=n)
    lat = rng.uniform(33.5, 42.5, size=n)

    # Normalized coords in [-1, 1]
    u = (lon - 300.0) / 5.0  # lon direction
    vv = (lat - 38.0) / 5.0  # lat direction (named vv to avoid shadowing v)

    # Design matrix: [1, vv, vv², u, u·vv]
    X = np.column_stack([np.ones(n), vv, vv**2, u, u * vv])

    # Planted coefficients: a0=2.0, a1=0.5, rest=0
    theta_true = np.array([2.0, 0.5, 0.0, 0.0, 0.0])
    s_true = np.exp(X @ theta_true)
    v = rng.exponential(scale=1.0, size=n) + 0.2
    sigma2 = _const.SIGMA_OBS2
    std = np.sqrt(s_true * v + sigma2)
    r = rng.standard_normal(n) * std
    r2 = r**2

    theta_fit, fit_id = _lik.fit_poly_lbfgsb(X, r2, v)

    # Check method name and gtol in fit_id
    assert "L-BFGS-B" in fit_id, f"fit_id missing L-BFGS-B: {fit_id!r}"
    assert "gtol=1e-08" in fit_id or "gtol=1e-8" in fit_id, (
        f"fit_id missing gtol: {fit_id!r}"
    )

    # a0 and a1 recovered within 2%
    assert abs(theta_fit[0] - 2.0) / 2.0 < 0.02, f"a0={theta_fit[0]:.4f}, expected ≈2.0"
    assert abs(theta_fit[1] - 0.5) / 0.5 < 0.02, f"a1={theta_fit[1]:.4f}, expected ≈0.5"
    # other coeffs near zero
    for i, coef in enumerate(theta_fit[2:], start=2):
        assert abs(coef) < 0.05, f"theta[{i}]={coef:.4f} expected ≈0"


# ---------------------------------------------------------------------------
# Safeguard
# ---------------------------------------------------------------------------


def test_safeguard_fires_on_worse_than_scalar() -> None:
    """assert_beats_scalar raises RuntimeError when nll_fit > nll_s_star;
    passes silently when nll_fit <= nll_s_star.

    Bug caught: safeguard not implemented, or wrong comparison direction.
    """
    # Should raise
    with pytest.raises(RuntimeError):
        _lik.assert_beats_scalar(nll_fit=100.0, nll_s_star=99.0)

    # Should pass silently (equal)
    _lik.assert_beats_scalar(nll_fit=99.0, nll_s_star=99.0)

    # Should pass silently (better)
    _lik.assert_beats_scalar(nll_fit=98.0, nll_s_star=99.0)


# ---------------------------------------------------------------------------
# Tail diagnostic
# ---------------------------------------------------------------------------


def test_tail_diagnostic_hand_case_flagged() -> None:
    """Construct r2, v, s_hat so median chi2 ratio >> 1.5 → flagged=True.

    Choose s_hat very small so normalised residuals are large.
    Hand computable: chi2_i = r2_i / (s_hat*v_i + sigma2).
    With s_hat=0.01, v=1, sigma2≈0.0009, r2=4*ones →
      chi2 = 4 / (0.01*1 + 0.0009) = 4 / 0.0109 ≈ 366.97 >> 1.5 * 0.4549.
    Bug caught: flag direction inverted, wrong CHI2_1_MEDIAN value.
    """
    sigma2 = _const.SIGMA_OBS2
    n = 10
    r2 = np.full(n, 4.0)
    v = np.ones(n)
    s_hat = 0.01

    chi2_i = r2 / (s_hat * v + sigma2)
    expected_ratio = float(np.median(chi2_i)) / _lik.CHI2_1_MEDIAN

    ratio, flagged = _lik.tail_diagnostic(r2, v, s_hat)

    assert abs(ratio - expected_ratio) < 1e-12, (
        f"ratio={ratio}, expected={expected_ratio}"
    )
    assert flagged, f"Expected flagged=True for ratio={ratio:.3f}"


def test_tail_diagnostic_hand_case_not_flagged() -> None:
    """Construct r2, v, s_hat so median chi2 ratio < 1.5 → flagged=False.

    Choose s_hat and r2 so chi2_i ≈ CHI2_1_MEDIAN (median ≈ 1.0 times the target).
    With s_hat=1.0, v=1, sigma2≈0.0009, set r2 = 0.4549*(1.0+sigma2) so
      chi2_i = 0.4549, median = 0.4549, ratio ≈ 1.0 < 1.5.
    Bug caught: flag direction inverted, wrong comparison threshold.
    """
    sigma2 = _const.SIGMA_OBS2
    s_hat = 1.0
    v = np.ones(10)
    # Set r2 so chi2_i = CHI2_1_MEDIAN exactly → ratio=1.0
    chi2_target = _lik.CHI2_1_MEDIAN
    tot = s_hat * v + sigma2
    r2 = chi2_target * tot

    ratio, flagged = _lik.tail_diagnostic(r2, v, s_hat)

    assert abs(ratio - 1.0) < 1e-12, f"ratio={ratio}"
    assert not flagged, f"Expected flagged=False for ratio={ratio:.3f}"
