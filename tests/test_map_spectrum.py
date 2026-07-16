"""Tests for the Phase-11 shared map-plane spectral prep (plan Task 2).

Reference values come from spatial-domain identities (Parseval), analytic
power laws, and independent full-plane brute-force enumeration — never from
running the module's own vectorized path.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from sverdrup.eval.map_spectrum import (
    PlaneGrid,
    annulus_mask,
    detrend,
    mainlobe_halfwidth_bins,
    power2d,
    radial_hann,
    ring_spectrum,
    wedge_mask,
)
from sverdrup.eval.phase11_constants import MAINLOBE_HALFWIDTH_BINS


def _real_grid() -> PlaneGrid:
    return PlaneGrid.from_deg(
        lon=np.arange(295, 305.01, 0.2), lat=np.arange(33, 43.21, 0.2), phi0=38.1
    )


def test_detrend_removes_exact_plane() -> None:
    """Bug caught: mean-only subtraction leaves the linear ramp intact."""
    g = PlaneGrid.from_km(dx_km=17.5, dy_km=22.26, ny=20, nx=24)
    x = g.x_km[None, :]
    y = g.y_km[:, None]
    field = 3.0 + 0.5 * x - 2.0 * y
    out = detrend(field)
    assert np.max(np.abs(out)) < 1e-9


@pytest.mark.parametrize("ny,nx", [(33, 32), (52, 51), (16, 16)])
def test_parseval_half_plane(ny: int, nx: int) -> None:
    """Bug caught: wrong Hermitian weights or silently dropped Nyquist modes
    lose energy; reference is the spatial-domain energy, not the FFT path."""
    rng = np.random.default_rng(42 + ny)
    g = PlaneGrid.from_km(dx_km=17.5, dy_km=22.26, ny=ny, nx=nx)
    field = detrend(rng.standard_normal((ny, nx)))
    win = radial_hann(g)
    P, _KX, _KY = power2d(field, win, g)
    energy_spatial = float(np.sum((field * win) ** 2))
    assert math.isclose(float(P.sum()), energy_spatial, rel_tol=1e-6)


def test_ring_spectrum_slope_recovers_isotropic_power_law() -> None:
    """Bug caught: ring-MEAN instead of ring-SUM yields slope ~-3, failing the
    pinned -q+1 = -2 relation; wrong ring bin width also shifts the fit.

    DEVIATION from the plan's sketch fixture (bins 3-10, one realization),
    recorded: ring 3 sits inside the radial-Hann mainlobe smear (half-width
    2.25 bins) and a single windowed realization scatters +-0.4 in slope —
    the sketch contradicts the spec's own mainlobe-clearance rule
    (MIN_BIN_INDEX = 4). Measured with a correct implementation: bins 3-10
    single-realization slope is -2.44. The fit here follows the clearance
    rule (rings >= 4) on 20-realization ensemble-averaged power; seeds 0-5
    all land within +-0.15 of -2.
    """
    rng = np.random.default_rng(11)
    ny, nx = 128, 128
    kx = np.fft.fftfreq(nx)[None, :]
    ky = np.fft.fftfreq(ny)[:, None]
    kk = np.hypot(kx, ky)
    kk[0, 0] = np.inf
    amp = kk ** (-3 / 2)  # power ~ k^-3
    g = PlaneGrid.from_km(dx_km=17.5, dy_km=22.26, ny=ny, nx=nx)
    win = radial_hann(g)
    p_acc = np.zeros(0)
    kx_kept = ky_kept = np.zeros(0)
    n_real = 20
    for _ in range(n_real):
        phase = np.exp(2j * np.pi * rng.random((ny, nx)))
        field = np.real(np.fft.ifft2(amp * phase))
        P, kx_kept, ky_kept = power2d(detrend(field), win, g)
        p_acc = P if p_acc.size == 0 else p_acc + P
    k, e_sum, _n = ring_spectrum(
        p_acc / n_real, kx_kept, ky_kept, dk=1.0 / g.lx_km, exclude=[]
    )
    slope = np.polyfit(np.log10(k[3:12]), np.log10(e_sum[3:12]), 1)[0]
    assert abs(slope - (-2.0)) < 0.15  # E(k) ~ k^(-q+1), the spec §3 relation


def _brute_canonical_modes(ny: int, nx: int) -> set[tuple[int, int]]:
    """Independent conjugate-pairing enumeration over the FULL plane."""
    reps = set()
    for i in range(ny):
        for j in range(nx):
            partner = ((-i) % ny, (-j) % nx)
            reps.add(min((i, j), partner))
    return reps


def test_half_plane_mode_set_matches_brute_force_pairing() -> None:
    """Bug caught: any double count or dropped mode across the half-plane —
    16x16 has 256 full modes, 4 self-conjugate, so exactly (256+4)/2 = 130
    independent modes (hand arithmetic)."""
    g = PlaneGrid.from_km(dx_km=1.0, dy_km=1.0, ny=16, nx=16)
    field = np.random.default_rng(0).standard_normal((16, 16))
    P, KX, KY = power2d(field, np.ones((16, 16)), g)
    assert P.shape == KX.shape == KY.shape
    assert KX.size == 130
    assert len(_brute_canonical_modes(16, 16)) == 130


def test_wedge_and_annulus_counts_exact_vs_brute_force() -> None:
    """Bug caught: axial-fold boundary errors or wrong radius edges in the
    vectorized masks; reference count loops over the full plane with scalar
    math and counts each conjugate pair once."""
    ny = nx = 16
    g = PlaneGrid.from_km(dx_km=1.0, dy_km=1.0, ny=ny, nx=nx)
    field = np.random.default_rng(1).standard_normal((ny, nx))
    _P, KX, KY = power2d(field, np.ones((ny, nx)), g)
    angle, dtheta, k_lo, k_hi = 30.0, 15.0, 0.12, 0.38

    def in_wedge(kxv: float, kyv: float) -> bool:
        r = math.hypot(kxv, kyv)
        if not (k_lo <= r <= k_hi):
            return False
        a = math.degrees(math.atan2(kyv, kxv)) % 180.0
        d = abs(a - angle)
        return min(d, 180.0 - d) <= dtheta

    def in_annulus(kxv: float, kyv: float) -> bool:
        return k_lo <= math.hypot(kxv, kyv) <= k_hi

    fx = np.fft.fftfreq(nx, d=1.0)
    fy = np.fft.fftfreq(ny, d=1.0)
    wedge_count = annulus_count = 0
    for i, j in _brute_canonical_modes(ny, nx):
        if in_wedge(float(fx[j]), float(fy[i])):
            wedge_count += 1
        if in_annulus(float(fx[j]), float(fy[i])):
            annulus_count += 1
    assert int(wedge_mask(KX, KY, angle, dtheta, k_lo, k_hi).sum()) == wedge_count
    assert int(annulus_mask(KX, KY, k_lo, k_hi).sum()) == annulus_count
    assert wedge_count > 0 and annulus_count > wedge_count


def test_wedge_mask_is_axial() -> None:
    """Bug caught: a missing 180-degree fold makes theta and theta+180 differ."""
    g = PlaneGrid.from_km(dx_km=1.0, dy_km=1.0, ny=16, nx=16)
    field = np.random.default_rng(2).standard_normal((16, 16))
    _P, KX, KY = power2d(field, np.ones((16, 16)), g)
    m1 = wedge_mask(KX, KY, 30.0, 15.0, 0.1, 0.4)
    m2 = wedge_mask(KX, KY, 210.0, 15.0, 0.1, 0.4)
    np.testing.assert_array_equal(m1, m2)


def test_mainlobe_halfwidth_matches_recorded() -> None:
    """Bug caught: wrong window shape (e.g. separable instead of radial Hann)
    or wrong padding/bin normalization moves the measured half-width off the
    pre-registered 2.25 zonal-fundamental bins (obligation 5)."""
    g = _real_grid()
    measured = mainlobe_halfwidth_bins(radial_hann(g), g, pad=8)
    assert abs(measured - MAINLOBE_HALFWIDTH_BINS) < 0.1
