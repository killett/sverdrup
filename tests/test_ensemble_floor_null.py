"""Null distribution of the σ-route ensemble-floor ratio (owner pin 36b).

Pins ``sverdrup.validation.ensemble_floor_null``, the harness that DERIVES
the Rule-0.b attributability factor instead of picking one. The quantity
characterised is

    T = RMS(sigma_delta) / F_ens ,  F_ens = sigma/sqrt(m-1)

under the null of NO seam: two independent m-member σ estimates of the
same field. Because ``s = F_ens * sqrt(chi2_{m-1})`` exactly for Gaussian
members, ``T`` is the weighted RMS of ``sqrt(chi2_a) - sqrt(chi2_b)`` over
the effectively-independent nodes — scale-free, so the derivation depends
only on ``m``, ``N_eff`` and the σ-level weights.

All expected values are hand-derived (half-normal moments, the exact c4
correction factor, iid/perfectly-correlated limiting cases), never taken
from the implementation.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from sverdrup.validation.ensemble_floor_null import (
    clean_reachable,
    effective_node_count,
    min_m_for_clean,
    node_term_moments,
    null_t_quantile,
    null_t_samples,
)


def _c4(m: int) -> float:
    """E[s]/sigma for an m-sample Gaussian std — independent Gamma form."""
    return math.sqrt(2.0 / (m - 1)) * math.exp(
        math.lgamma(m / 2.0) - math.lgamma((m - 1) / 2.0)
    )


# ---------------------------------------------------------------------------
# null_t_samples — the null distribution of T
# ---------------------------------------------------------------------------


def test_null_t_second_moment_at_m_two_is_the_half_normal_hand_value() -> None:
    """At m=2, E[T^2] = 2(1 - 2/pi) = 0.72676 exactly.

    Hand derivation, no implementation involved: at m=2 the chi2 has ONE
    degree of freedom, so sqrt(chi2) = |z| for a standard normal z, with
    E[|z|^2] = 1 and E[|z|] = sqrt(2/pi). Hence
    E[(|z_a| - |z_b|)^2] = 2 Var(|z|) = 2(1 - 2/pi).

    Bug caught: comparing VARIANCES instead of standard deviations (i.e.
    using chi2 rather than sqrt(chi2)), or using m degrees of freedom
    instead of m-1. The first changes this number to 2.0, the second to
    2(1 - (2/pi)*...) at the wrong dof — and either way the derived
    attributability factor is set from the wrong null.
    """
    t = null_t_samples(m=2, n_eff=4000, k=4000, seed=20260727)
    assert float(np.mean(t**2)) == pytest.approx(2.0 * (1.0 - 2.0 / math.pi), rel=0.02)


def test_null_t_mean_matches_the_exact_c4_expression_at_m_100() -> None:
    """E[T] = sqrt(2(1 - c4^2)(m-1)) = 0.99873 at m=100, NOT 1.0.

    The expected value is computed in the test from the Gamma-function
    form of c4 (see ``_c4``), which is an independent derivation: the
    implementation draws chi2 variates and never evaluates c4.

    This is the "asymptotic approximation" the ruling asks to be given
    explicit margin: the sigma/sqrt(m-1) floor is 0.13% ABOVE the exact
    expected RMS at m=100, so T concentrates just below 1.

    Bug caught: an off-by-one in the degrees of freedom. At dof=m the mean
    lands near 1.0037 instead of 0.99873 — a 0.5% error, which is
    comparable to the entire null spread and would bias the derived
    factor by more than the spread it is supposed to cover.
    """
    m = 100
    expected = math.sqrt(2.0 * (1.0 - _c4(m) ** 2) * (m - 1))
    assert expected == pytest.approx(0.99873, abs=5e-5)  # anchors the hand value
    t = null_t_samples(m=m, n_eff=20000, k=2000, seed=11)
    assert float(np.mean(t)) == pytest.approx(expected, rel=2e-3)


def test_null_t_spread_scales_as_one_over_sqrt_two_n_eff() -> None:
    """sd(T) * sqrt(2 N_eff) is invariant across N_eff — the concentration law.

    Independent reasoning: T^2 is a mean of N_eff iid terms, so its
    relative sd falls as 1/sqrt(N_eff); the square root halves that,
    giving sd(T)/E[T] = c/sqrt(2 N_eff) for a constant c that depends only
    on the per-node kurtosis. Tested across a 16x range of N_eff.

    Bug caught: N_eff ignored or applied to the wrong axis (e.g. summing
    over replications instead of nodes). The factor is a QUANTILE of this
    distribution, so getting the concentration wrong is exactly how a
    factor ends up 3x too large.
    """
    scaled = []
    for n_eff in (100, 400, 1600):
        t = null_t_samples(m=100, n_eff=n_eff, k=6000, seed=100 + n_eff)
        scaled.append(float(np.std(t, ddof=1)) * math.sqrt(2.0 * n_eff))
    assert scaled[1] == pytest.approx(scaled[0], rel=0.08)
    assert scaled[2] == pytest.approx(scaled[0], rel=0.08)


def test_null_t_weights_shift_the_distribution_off_the_unweighted_case() -> None:
    """Heterogeneous σ levels change the null: weights are not decorative.

    A pool where one node carries 90% of the σ² weight behaves like a
    MUCH smaller effective sample: its spread must be far wider than the
    equal-weight case at the same node count. Hand-reasoned direction and
    a strict inequality, not a fitted number.

    Bug caught: weights accepted and silently ignored (the recorded σ
    field is not flat — the diagnosis measured a 14.4% spread across the
    strip), which would understate the null spread and tighten the factor.
    """
    w = np.concatenate([[0.9], np.full(99, 0.1 / 99)])
    flat = null_t_samples(m=100, n_eff=100, k=4000, seed=7)
    lumpy = null_t_samples(m=100, n_eff=100, k=4000, seed=7, weights=w)
    assert float(np.std(lumpy, ddof=1)) > 3.0 * float(np.std(flat, ddof=1))


def test_null_t_refuses_below_two_members() -> None:
    """m < 2 has no member-std and therefore no null to characterise.

    Bug caught: dof = m - 1 = 0 producing a degenerate chi2 (all zeros)
    and a "null distribution" concentrated at 0, which would derive a
    factor of ~0 and license every σ verdict.
    """
    with pytest.raises(ValueError, match="m >= 2"):
        null_t_samples(m=1, n_eff=10, k=10, seed=1)


# ---------------------------------------------------------------------------
# effective_node_count — the spatial/temporal correlation that sets N_eff
# ---------------------------------------------------------------------------


def test_effective_node_count_of_an_iid_field_is_the_node_count() -> None:
    """An uncorrelated field has N_eff ~ N (every node independent).

    Hand-reasoned limiting case: with rho(lag) = 0 for every non-zero lag,
    sum over lags of rho^2 is 1, so N_eff = N.

    Bug caught: a normalization error in the autocorrelation sum — any
    constant factor shows up here immediately, and it would rescale the
    derived factor's spread term directly.
    """
    rng = np.random.default_rng(3)
    field = rng.normal(size=(40, 21, 51))
    n = field.size
    assert effective_node_count(field) == pytest.approx(n, rel=0.15)


def test_effective_node_count_collapses_for_a_time_constant_field() -> None:
    """A field frozen in time has N_eff ~ N / n_time, not N.

    Hand-reasoned limiting case: 40 identical time slices of an iid
    spatial field carry the information of ONE slice, so N_eff must fall
    to N/40 (= the spatial node count).

    Bug caught — and this is the load-bearing one for this instrument:
    ignoring the TIME axis. The σ error field is a function of the member
    draws, which are SHARED across all 365 output days, so time is the
    dominant correlation direction. Counting 365 days as independent
    would overstate N_eff by ~365x, understate the null spread by ~19x,
    and derive a factor far tighter than the measurement supports.
    """
    rng = np.random.default_rng(4)
    slice_ = rng.normal(size=(1, 21, 51))
    field = np.repeat(slice_, 40, axis=0)
    assert effective_node_count(field) == pytest.approx(21 * 51, rel=0.2)


def test_effective_node_count_drops_with_spatial_smoothing() -> None:
    """Smoothing a field in space strictly reduces N_eff.

    A 3x3 box-smoothed iid field has ~9 nodes per independent patch, so
    N_eff must fall well below N and stay above N/20 — a bracket, not a
    fitted value.

    Bug caught: an N_eff estimator that only looks along one axis (e.g.
    time) and treats spatially smooth fields as fully independent.
    """
    rng = np.random.default_rng(5)
    field = rng.normal(size=(30, 30, 30))
    smooth = np.copy(field)
    for axis in (1, 2):
        smooth = (
            np.roll(smooth, 1, axis=axis) + smooth + np.roll(smooth, -1, axis=axis)
        ) / 3.0
    n_eff = effective_node_count(smooth)
    assert n_eff < 0.5 * field.size
    assert n_eff > field.size / 20.0


def test_effective_node_count_ignores_nan_land_nodes() -> None:
    """NaN (land) nodes are excluded rather than poisoning the estimate.

    Bug caught: NaN propagation returning nan for N_eff, which would make
    the whole derivation refuse on any tile with a coastline — the
    Kuroshio tile, for one.
    """
    rng = np.random.default_rng(6)
    field = rng.normal(size=(20, 21, 51))
    field[:, 0, 0] = np.nan
    assert math.isfinite(effective_node_count(field))


# ---------------------------------------------------------------------------
# reachability (owner pin 36c) — the standing property of the instrument
# ---------------------------------------------------------------------------


def test_clean_is_unreachable_at_the_recorded_geometry_with_factor_three() -> None:
    """The pin-36 defect, pinned: factor 3 leaves NO reachable CLEAN cell.

    Recorded numbers: F_ens = 0.0037082780 m, D_int_sigma = 0.0032654982 m,
    clean_max = 1.0. Attributability at 3x needs
    RMS(sigma_delta) > 0.0111248 m, i.e. R_seam_sigma > 3.407 — above
    elevated_max 2.5, so every attributable σ verdict is STRUCTURAL_STOP
    and the only other outcome is UNMEASURED.

    Bug caught: a future threshold or floor edit that reintroduces an
    unpassable gate. This test is pin 33 made mechanical for the σ route.
    """
    assert not clean_reachable(
        factor=3.0, f_ens=0.0037082779872093232, clean_max=1.0, d_int_sigma=0.003265498
    )
    assert clean_reachable(
        factor=0.8, f_ens=0.0037082779872093232, clean_max=1.0, d_int_sigma=0.003265498
    )


def test_min_m_for_clean_hand_value_at_factor_one() -> None:
    """The member count CLEAN needs: m-1 > (factor * sigma / D_int)^2.

    Hand arithmetic from the recorded σ level 0.0368969005 m and
    D_int_sigma 0.0032654982 m: sigma/D_int = 11.2990, so at factor 1.0
    CLEAN requires m - 1 > 127.67, i.e. m >= 129.

    Bug caught: using m instead of m-1 (off-by-one in the required
    ensemble size, which is a directly costed quantity — every member is
    a solve), or dropping the factor from the condition.
    """
    got = min_m_for_clean(
        factor=1.0,
        sigma_level=0.036896900105722996,
        clean_max=1.0,
        d_int_sigma=0.0032654982,
    )
    assert got == 129


def test_min_m_for_clean_at_factor_three_reproduces_the_ruling_estimate() -> None:
    """At factor 3 the required m is 1151, the ~1150 the ruling quotes.

    Same hand arithmetic scaled by 3: m - 1 > (3 * 11.29903)^2 = 1149.01,
    so m >= 1151. Independent of the implementation's search.

    Bug caught: a monotonicity error in the requirement (a larger factor
    must demand a LARGER m, never smaller).
    """
    assert (
        min_m_for_clean(
            factor=3.0,
            sigma_level=0.036896900105722996,
            clean_max=1.0,
            d_int_sigma=0.0032654982,
        )
        == 1151
    )


# ---------------------------------------------------------------------------
# node_term_moments / null_t_quantile — the affordable, validated predictor
# ---------------------------------------------------------------------------


def test_node_term_moments_at_m_two_match_half_normal_hand_values() -> None:
    """Per-node moments of u = (sqrt(chi2_a) - sqrt(chi2_b))^2 at m=2.

    Hand derivation: at dof 1, sqrt(chi2) = |z|, so d = |z_a| - |z_b| has
    E[d^2] = 2(1 - 2/pi) = 0.726763. For the second moment,
    E[d^4] = 2 mu4 + 6 mu2^2 with mu2 = 1 - 2/pi = 0.363380 and, using
    E|z| = sqrt(2/pi), E[z^2] = 1, E|z|^3 = 2 sqrt(2/pi), E[z^4] = 3,
    mu4 = E[r^4] - 4 mu E[r^3] + 6 mu^2 E[r^2] - 3 mu^4
        = 3 - 2(2/pi) - 3(2/pi)^2 = 0.510906,
    giving E[d^4] = 1.814080 and Var(u) = 1.814080 - 0.726763^2 = 1.285896.

    Bug caught: a wrong central-moment expansion or a dof off-by-one — both
    change Var(u), which sets the null spread and therefore the derived
    factor directly.
    """
    two_over_pi = 2.0 / math.pi
    mu2 = 1.0 - two_over_pi
    mu4 = 3.0 - 2.0 * two_over_pi - 3.0 * two_over_pi**2
    mom = node_term_moments(m=2, n_pool=4_000_000, seed=3)
    assert mom["mean"] == pytest.approx(2.0 * mu2, rel=5e-3)
    assert mom["var"] == pytest.approx(
        2.0 * mu4 + 6.0 * mu2**2 - (2.0 * mu2) ** 2, rel=2e-2
    )
    assert mom["skew"] > 0.0  # u is a squared quantity: right-skewed


def test_null_t_quantile_agrees_with_direct_simulation() -> None:
    """The predictor reproduces the DIRECTLY simulated q99.9 at n_eff=2000.

    This is the validation the ruling asks for: the cheap predictor
    (per-node moments + Cornish-Fisher over n_eff) is checked against the
    expensive path (drawing every node of every replication). Agreement to
    0.5% is required at a quantile 3.1 sd into the tail.

    Bug caught: a predictor that silently omits the skewness term or gets
    the 1/sqrt(n_eff) scaling wrong — either would shift the derived factor
    by more than the entire null spread, which is the whole quantity being
    measured.
    """
    n_eff = 2000
    mom = node_term_moments(m=100, n_pool=8_000_000, seed=17)
    predicted = null_t_quantile(moments=mom, n_eff=n_eff, confidence=0.999)
    direct = float(
        np.quantile(null_t_samples(m=100, n_eff=n_eff, k=60_000, seed=19), 0.999)
    )
    assert predicted == pytest.approx(direct, rel=5e-3)


def test_null_t_quantile_weights_reduce_the_effective_count() -> None:
    """Weighted pools quantile HIGHER than equal weights at the same n_eff.

    Concentrating the σ² weight on fewer nodes reduces the effective sample
    (1/sum w^2 < n_eff), so the null tail must move OUT. Hand-reasoned
    direction plus the exact effective count the predictor reports.

    Bug caught: weights accepted but not propagated into the concentration
    term — the recorded σ field is not flat, and ignoring that tightens the
    factor on a false premise.
    """
    mom = node_term_moments(m=100, n_pool=4_000_000, seed=23)
    flat_q = null_t_quantile(moments=mom, n_eff=1000, confidence=0.999)
    w = np.concatenate([np.full(100, 0.008), np.full(900, 0.0002222)])
    lumpy_q = null_t_quantile(moments=mom, n_eff=1000, confidence=0.999, weights=w)
    assert lumpy_q > flat_q
    # 1/sum(w^2) is the exact effective count the weights imply
    w_n = w / w.sum()
    assert 1.0 / float(np.sum(w_n**2)) < 1000.0


def test_null_t_quantile_tightens_as_n_eff_grows() -> None:
    """More independent nodes -> a tighter null tail (monotone in n_eff).

    Bug caught: an inverted or absent n_eff dependence, which would make
    the factor insensitive to the correlation structure the ruling
    specifically asked to be included.
    """
    mom = node_term_moments(m=100, n_pool=4_000_000, seed=29)
    q_small = null_t_quantile(moments=mom, n_eff=500, confidence=0.999)
    q_large = null_t_quantile(moments=mom, n_eff=50_000, confidence=0.999)
    assert q_small > q_large > 1.0
