"""Tests for the Gaussian degree-space anisotropic kernel (challenge BASELINE OI)."""

import numpy as np

from sverdrup.methods.kernel import GaussianSpaceTimeDegrees


def _pt(lon, lat, t):
    return np.array([[lon, lat, t]], dtype=float)


def test_self_covariance_equals_variance():
    """B(a, a) must equal the signal variance (correlation peak).

    Catches a normalization bug that would scale every mapped value.
    """
    k = GaussianSpaceTimeDegrees(variance=1.0, lx_deg=1.0, ly_deg=1.0, time_scale=7.0)
    assert k.evaluate(_pt(300.0, 38.0, 0.0), _pt(300.0, 38.0, 0.0))[0, 0] == 1.0


def test_each_axis_decays_at_its_own_scale():
    """One scale-length offset on each axis gives variance * exp(-1).

    Catches axis swaps or scale mixups (Lx vs Ly vs Lt) — each axis is exercised
    independently at exactly its decorrelation scale.
    """
    k = GaussianSpaceTimeDegrees(variance=2.0, lx_deg=1.0, ly_deg=3.0, time_scale=7.0)
    base = _pt(300.0, 38.0, 0.0)
    e1 = 2.0 * np.exp(-1.0)
    assert np.isclose(k.evaluate(base, _pt(301.0, 38.0, 0.0))[0, 0], e1)  # +Lx lon
    assert np.isclose(k.evaluate(base, _pt(300.0, 41.0, 0.0))[0, 0], e1)  # +Ly lat
    assert np.isclose(k.evaluate(base, _pt(300.0, 38.0, 7.0))[0, 0], e1)  # +Lt time


def test_degree_space_no_cos_lat_correction():
    """The spatial metric is raw degrees (no cos-lat), matching oi_core.

    Catches an accidental great-circle/km conversion (as in the Matern kernel):
    a fixed lon offset must give the SAME covariance at 60N as at 0N.
    """
    k = GaussianSpaceTimeDegrees(variance=1.0, lx_deg=1.0, ly_deg=1.0, time_scale=7.0)
    low = k.evaluate(_pt(300.0, 0.0, 0.0), _pt(300.5, 0.0, 0.0))[0, 0]
    high = k.evaluate(_pt(300.0, 60.0, 0.0), _pt(300.5, 60.0, 0.0))[0, 0]
    assert np.isclose(low, high)


def test_matches_oi_core_formula_on_a_pair():
    """Exactly matches their oi_core exp(...) expression for an off-diagonal pair.

    Catches any deviation from the challenge's separable-Gaussian definition.
    """
    k = GaussianSpaceTimeDegrees(variance=1.0, lx_deg=1.0, ly_deg=1.0, time_scale=7.0)
    a = _pt(300.0, 38.0, 0.0)
    b = _pt(300.7, 38.4, 2.0)
    expected = np.exp(-(0.7**2) - (0.4**2) - ((2.0 / 7.0) ** 2))
    assert np.isclose(k.evaluate(a, b)[0, 0], expected)
