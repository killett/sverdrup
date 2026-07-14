"""PaciorekGaussianDegrees — PD, constant-reduction, prior-diag (Task 4; spec §3).

Bug named per test: naive L(x) substitution into the stationary form is NOT
PD (test_pd_at_pinned_geometry); a prefactor/exponent convention mismatch vs
the shipped kernel silently changes every solve (constant-reduction
identity); the pointwise prior variance drifting from the variance field —
wrong at the clip boundary or via the sqrt round-trip (prior-diag tests);
the multiplier not actually entering the covariance (nonstationarity test);
the stationary fast path mistakenly claiming constant prior variance for a
lat-varying kernel (_stationary routing).
"""

from __future__ import annotations

import numpy as np

from sverdrup.core.parameters import LatitudeField
from sverdrup.methods.kernel import PaciorekGaussianDegrees
from sverdrup.methods.oi import _stationary
from sverdrup.validation.params import baseline_kernel


def _paciorek(
    c: tuple[float, float, float], l1: float, lx_base: float = 1.0, lt: float = 7.0
) -> PaciorekGaussianDegrees:
    return PaciorekGaussianDegrees(
        variance_field=LatitudeField("exp-quad", c),
        lx_deg_base=lx_base,
        l_mult_field=LatitudeField("exp-linear-mult", (l1,)),
        time_scale=lt,
    )


def _pinned_geometry() -> np.ndarray:
    """Spec §3 PD geometry: 20 south-edge + 20 north-edge + 40 mid-box points.

    Max-L-contrast bands (lat 33.0-33.4 and 42.6-43.0) + a dense cluster
    around (300, 38) ± 0.3°; times cycle {0, 3, 7} days. Deterministic.
    """
    south = np.column_stack(
        [
            np.linspace(295.5, 304.5, 20),
            np.linspace(33.0, 33.4, 20),
            np.tile([0.0, 3.0, 7.0], 7)[:20],
        ]
    )
    north = np.column_stack(
        [
            np.linspace(295.5, 304.5, 20),
            np.linspace(42.6, 43.0, 20),
            np.tile([3.0, 7.0, 0.0], 7)[:20],
        ]
    )
    gx, gy = np.meshgrid(np.linspace(299.7, 300.3, 8), np.linspace(37.7, 38.3, 5))
    mid = np.column_stack([gx.ravel(), gy.ravel(), np.tile([0.0, 3.0, 7.0], 14)[:40]])
    return np.vstack([south, north, mid])


def _pts() -> np.ndarray:
    rng = np.random.default_rng(7)
    lon = 295 + 10 * rng.random(40)
    lat = 33 + 10 * rng.random(40)
    t = 30 * rng.random(40)
    return np.column_stack([lon, lat, t])


def test_pd_at_pinned_geometry() -> None:
    # Strongly varying fields at the spec's max-contrast geometry: the
    # Paciorek prefactor is what keeps this PD; a naive L(x)-substitution
    # kernel goes indefinite here.
    k = _paciorek(c=(0.5, 1.0, -1.0), l1=-0.5)
    pts = _pinned_geometry()
    K = k.evaluate(pts, pts)
    w = np.linalg.eigvalsh(0.5 * (K + K.T))
    assert w.min() >= -1e-10 * np.linalg.norm(K, 2)


def test_pd_at_dense_lat_sweep_discriminates_row_substitution() -> None:
    # Dense 80-point latitude line across the whole box, l1 at the box edge:
    # HERE the asymmetric row-substitution bug (exp(-d²/L(x)²)) is measurably
    # indefinite (min eig ≈ -1e-3, verified), while the Paciorek form stays
    # PD. The spec-pinned geometry above does NOT discriminate (its bands
    # are ~9° apart, cross-band covariance ~0) — this sweep is the teeth.
    mult = LatitudeField("exp-linear-mult", (-0.5,))
    lat = np.linspace(33.0, 43.0, 80)
    pts = np.column_stack([np.full_like(lat, 300.0), lat, np.zeros_like(lat)])
    k = PaciorekGaussianDegrees(1.0, 1.0, mult, 7.0)
    K = k.evaluate(pts, pts)
    w = np.linalg.eigvalsh(0.5 * (K + K.T))
    assert w.min() >= -1e-10 * np.linalg.norm(K, 2)


def test_hand_computed_cross_band_entry() -> None:
    # One entry, fully by hand (kills a dropped/inverted prefactor and a
    # wrong L̄² denominator, which every PD test above tolerates):
    # x=(300,34,0), y=(300,42,0), l1=-0.5, L0=1, sigma=1:
    #   v(34)=-0.8, v(42)=+0.8 -> Lx=e^{0.4}, Ly=e^{-0.4}
    #   L̄² = (e^{0.8}+e^{-0.8})/2 = cosh(0.8); Lx·Ly = 1
    #   K = [1/cosh(0.8)] · exp(-64/cosh(0.8))
    mult = LatitudeField("exp-linear-mult", (-0.5,))
    k = PaciorekGaussianDegrees(1.0, 1.0, mult, 7.0)
    x = np.array([[300.0, 34.0, 0.0]])
    y = np.array([[300.0, 42.0, 0.0]])
    expected = (1.0 / np.cosh(0.8)) * np.exp(-64.0 / np.cosh(0.8))
    np.testing.assert_allclose(k.evaluate(x, y)[0, 0], expected, rtol=1e-14)


def test_constant_reduction_identity_full_spacetime() -> None:
    # c=(0,0,0), l1=0, L0=1.0, Lt=7.0 -> the SHIPPED baseline_kernel(),
    # full space-time kernel, bit or rtol 1e-15 (spec §3 pin 3).
    k = _paciorek(c=(0.0, 0.0, 0.0), l1=0.0)
    a, b = _pts(), _pts()[:23]
    ref = baseline_kernel().evaluate(a, b)
    got = k.evaluate(a, b)
    assert np.array_equal(got, ref) or np.allclose(got, ref, rtol=1e-15, atol=0)


def test_prior_var_at_equals_variance_field_exactly() -> None:
    # prior_var_at == variance_field.at EXACTLY (prefactor 1, dt 0 at x=y):
    # no sqrt round-trip, no clip-boundary drift. Includes off-hull lats
    # (clamped region) where a wrong clip interaction would show.
    k = _paciorek(c=(0.5, 1.0, -1.0), l1=-0.5)
    lat = np.array([20.0, 33.0, 36.5, 38.0, 41.2, 43.0, 55.0])
    pts = np.column_stack([np.full_like(lat, 300.0), lat, np.zeros_like(lat)])
    expected = LatitudeField("exp-quad", (0.5, 1.0, -1.0)).at(lat)
    assert np.array_equal(k.prior_var_at(pts), expected)


def test_prior_var_matches_brute_force_diag() -> None:
    # Cross-check vs np.diag(evaluate(a, a)) at rtol 1e-14 (the sqrt(v)**2
    # round-trip is the only permitted difference).
    k = _paciorek(c=(0.5, 1.0, -1.0), l1=-0.5)
    pts = _pinned_geometry()[::3]
    np.testing.assert_allclose(
        k.prior_var_at(pts), np.diag(k.evaluate(pts, pts)), rtol=1e-14
    )


def test_length_multiplier_actually_enters_covariance() -> None:
    # Same lon/time, same |dlat| pair placed south vs north: with l1 < 0 the
    # south pair (longer L) must be MORE correlated. Catches the multiplier
    # being resolved but never applied.
    k = _paciorek(c=(0.0, 0.0, 0.0), l1=-0.5)
    south = np.array([[300.0, 33.5, 0.0], [300.0, 34.0, 0.0]])
    north = np.array([[300.0, 42.0, 0.0], [300.0, 42.5, 0.0]])
    c_south = k.evaluate(south[:1], south[1:])[0, 0]
    c_north = k.evaluate(north[:1], north[1:])[0, 0]
    assert c_south > c_north


def test_not_stationary_routes_diag_branch() -> None:
    # _stationary() must be False -> GPCovarianceOperator.marginal_var takes
    # the exact diag branch, never the constant-prior fast path (which would
    # flatten the lat-varying prior variance it exists to represent).
    k = _paciorek(c=(0.5, 1.0, -1.0), l1=-0.5)
    assert not _stationary(k)
