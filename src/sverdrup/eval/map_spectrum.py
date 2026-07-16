"""Shared map-plane spectral prep (spec §3).

NOT eval/spectral.py (the lambda_x algorithm) — that module is untouched
(Phase-5 invariant 10).

Ring convention: azimuthally-INTEGRATED E(k) (ring-sum, not ring-mean).
Exponent relation (the off-by-one trap, recorded once, here): an isotropic
2-D power DENSITY ~ |k|^(-q) gives ring-integrated E(k) ~ k^(-q+1), the SAME
exponent as a 1-D along-track spectrum of that field.

Half-plane convention: kx >= 0, with the kx == 0 column's ky < 0 half dropped
(alpha == alpha + 180 axial identification; no mode counted twice). On grids
with an EVEN x-dimension the kx-Nyquist column is its own conjugate mirror, so
the same ky-half drop applies there; fully self-conjugate modes (DC and
Nyquist corners) carry Hermitian weight 1, every other kept mode weight 2 —
this is what makes the half-plane Parseval-exact on any grid shape. The real
52x51 grid has odd nx, where the pinned wording is literal.

phi0-plane frame shared with application/orbit_geometry.py:
x = lon * cos(phi0) [deg -> km via 111.32], y = lat [deg -> km].
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

KM_PER_DEG = 111.32


@dataclass(frozen=True)
class PlaneGrid:
    """Regular phi0-plane grid in km.

    Attributes:
        x_km: 1-D zonal coordinates (km), evenly spaced.
        y_km: 1-D meridional coordinates (km), evenly spaced.
        phi0: Reference latitude of the plane (degrees).
    """

    x_km: np.ndarray
    y_km: np.ndarray
    phi0: float

    @classmethod
    def from_deg(
        cls, lon: np.ndarray, lat: np.ndarray, phi0: float | None = None
    ) -> PlaneGrid:
        """Build the grid from lon/lat degree axes.

        Args:
            lon: 1-D longitudes (degrees).
            lat: 1-D latitudes (degrees).
            phi0: Reference latitude; defaults to ``mean(lat)``.

        Returns:
            The projected :class:`PlaneGrid`.
        """
        lon = np.asarray(lon, dtype=float)
        lat = np.asarray(lat, dtype=float)
        p0 = float(np.mean(lat)) if phi0 is None else float(phi0)
        x = (lon - lon[0]) * KM_PER_DEG * np.cos(np.deg2rad(p0))
        y = (lat - lat[0]) * KM_PER_DEG
        return cls(x_km=x, y_km=y, phi0=p0)

    @classmethod
    def from_km(cls, dx_km: float, dy_km: float, ny: int, nx: int) -> PlaneGrid:
        """Build a synthetic grid directly from spacings and shape.

        Args:
            dx_km: Zonal spacing (km).
            dy_km: Meridional spacing (km).
            ny: Number of rows.
            nx: Number of columns.

        Returns:
            The :class:`PlaneGrid` (phi0 recorded as NaN — synthetic).
        """
        return cls(
            x_km=np.arange(nx, dtype=float) * dx_km,
            y_km=np.arange(ny, dtype=float) * dy_km,
            phi0=float("nan"),
        )

    @property
    def shape(self) -> tuple[int, int]:
        """Grid shape ``(ny, nx)``."""
        return self.y_km.size, self.x_km.size

    @property
    def dx_km(self) -> float:
        """Zonal spacing (km)."""
        return float(self.x_km[1] - self.x_km[0])

    @property
    def dy_km(self) -> float:
        """Meridional spacing (km)."""
        return float(self.y_km[1] - self.y_km[0])

    @property
    def lx_km(self) -> float:
        """Periodic zonal extent the FFT sees: ``nx * dx_km`` (km)."""
        return self.x_km.size * self.dx_km


def detrend(field: np.ndarray) -> np.ndarray:
    """Subtract the least-squares plane fit on ``[1, x, y]``.

    Args:
        field: 2-D ``(ny, nx)`` field.

    Returns:
        The field minus its best-fit plane.
    """
    field = np.asarray(field, dtype=float)
    ny, nx = field.shape
    x = np.arange(nx, dtype=float)[None, :] * np.ones((ny, 1))
    y = np.arange(ny, dtype=float)[:, None] * np.ones((1, nx))
    basis = np.column_stack(
        [np.ones(field.size), x.ravel() / max(nx - 1, 1), y.ravel() / max(ny - 1, 1)]
    )
    coef, *_ = np.linalg.lstsq(basis, field.ravel(), rcond=None)
    return np.asarray(field - (basis @ coef).reshape(ny, nx))


def radial_hann(grid: PlaneGrid) -> np.ndarray:
    """Radial Hann window on the inscribed disk.

    ``0.5 * (1 + cos(pi * r / R))`` for ``r <= R`` (R = half the smaller
    physical extent, disk centred on the domain), else 0.

    Args:
        grid: The plane grid.

    Returns:
        2-D ``(ny, nx)`` window.
    """
    x = grid.x_km - grid.x_km.mean()
    y = grid.y_km - grid.y_km.mean()
    r = np.hypot(x[None, :], y[:, None])
    radius = min(x.max() - x.min(), y.max() - y.min()) / 2.0
    win = np.asarray(0.5 * (1.0 + np.cos(np.pi * r / radius)))
    win[r > radius] = 0.0
    return win


def _half_plane_selection(ny: int, nx: int) -> tuple[np.ndarray, np.ndarray]:
    """Kept-mode boolean mask and Hermitian weights over the full FFT grid.

    Returns:
        ``(keep, weight)`` where ``keep`` selects one representative per
        conjugate pair and ``weight`` is 2 for paired modes, 1 for
        self-conjugate modes.
    """
    jx = np.arange(nx)
    jy = np.arange(ny)
    JX, JY = np.meshgrid(jx, jy)
    # signed integer frequencies with Nyquist counted as positive
    sx = np.where(jx <= nx // 2, jx, jx - nx)[None, :] * np.ones((ny, 1), dtype=int)
    sy = np.where(jy <= ny // 2, jy, jy - ny)[:, None] * np.ones((1, nx), dtype=int)
    x_self = (JX == 0) | ((nx % 2 == 0) & (JX == nx // 2))  # own-mirror columns
    y_self = (JY == 0) | ((ny % 2 == 0) & (JY == ny // 2))
    keep = (~x_self & (sx > 0)) | (x_self & ((sy > 0) | y_self))
    weight = np.where(x_self & y_self, 1.0, 2.0)
    return keep, weight


def power2d(
    field: np.ndarray, window: np.ndarray, grid: PlaneGrid
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Half-plane 2-D power of the windowed field.

    The returned power carries the Hermitian pair weights, so ``P.sum()``
    equals the spatial-domain energy ``sum((field * window)**2)`` exactly
    (Parseval), and is normalized by ``N = ny * nx`` accordingly.

    Args:
        field: 2-D ``(ny, nx)`` field (detrended by the caller).
        window: 2-D taper (e.g. :func:`radial_hann`).
        grid: The plane grid (supplies dx/dy for the wavenumber axes).

    Returns:
        ``(P, KX, KY)`` — 1-D arrays over the kept half-plane modes; KX/KY in
        cycles per km.
    """
    field = np.asarray(field, dtype=float)
    ny, nx = field.shape
    spec = np.fft.fft2(field * window)
    keep, weight = _half_plane_selection(ny, nx)
    power_full = weight * np.abs(spec) ** 2 / (ny * nx)
    kx = np.fft.fftfreq(nx, d=grid.dx_km)
    ky = np.fft.fftfreq(ny, d=grid.dy_km)
    KX_full, KY_full = np.meshgrid(kx, ky)
    return power_full[keep], KX_full[keep], KY_full[keep]


def wedge_mask(
    KX: np.ndarray,
    KY: np.ndarray,
    angle_east_deg: float,
    dtheta_deg: float,
    k_lo: float,
    k_hi: float,
) -> np.ndarray:
    """Axial wedge: fold ``atan2(KY, KX)`` into [0, 180); circular distance.

    Args:
        KX: Kept-mode zonal wavenumbers (cyc/km).
        KY: Kept-mode meridional wavenumbers (cyc/km).
        angle_east_deg: Probe direction from east (any representative; axial).
        dtheta_deg: Angular half-width (degrees).
        k_lo: Radial lower edge (cyc/km, inclusive).
        k_hi: Radial upper edge (cyc/km, inclusive).

    Returns:
        Boolean mask over the kept modes.
    """
    r = np.hypot(KX, KY)
    angle = np.rad2deg(np.arctan2(KY, KX)) % 180.0
    target = angle_east_deg % 180.0
    d = np.abs(angle - target)
    d = np.minimum(d, 180.0 - d)
    return np.asarray((r >= k_lo) & (r <= k_hi) & (d <= dtheta_deg))


def annulus_mask(
    KX: np.ndarray, KY: np.ndarray, k_lo: float, k_hi: float
) -> np.ndarray:
    """Radial annulus over the kept modes, edges inclusive.

    Args:
        KX: Kept-mode zonal wavenumbers (cyc/km).
        KY: Kept-mode meridional wavenumbers (cyc/km).
        k_lo: Lower |k| edge (cyc/km).
        k_hi: Upper |k| edge (cyc/km).

    Returns:
        Boolean mask over the kept modes.
    """
    r = np.hypot(KX, KY)
    return np.asarray((r >= k_lo) & (r <= k_hi))


def ring_spectrum(
    P: np.ndarray,
    KX: np.ndarray,
    KY: np.ndarray,
    dk: float,
    exclude: list[np.ndarray] | tuple[np.ndarray, ...] = (),
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Ring-integrated E(k): per-ring SUM of power (never the mean).

    Ring b collects kept modes with ``round(|k| / dk) == b``; its centre is
    ``b * dk``. Ring width ``dk`` is the zonal fundamental ``1 / Lx`` by the
    spec §3 convention (callers pass it explicitly).

    Args:
        P: Kept-mode power (from :func:`power2d`).
        KX: Kept-mode zonal wavenumbers (cyc/km).
        KY: Kept-mode meridional wavenumbers (cyc/km).
        dk: Ring bin width (cyc/km).
        exclude: Boolean masks (kept-mode shape) removed before integration
            (the track-wedge exclusion set).

    Returns:
        ``(k_centers, e_sum, n_modes)`` for rings b >= 1 up to the largest
        populated ring; rings with zero modes carry ``e_sum = 0, n_modes = 0``.
    """
    r = np.hypot(KX, KY)
    keep = np.ones(P.shape, dtype=bool)
    for mask in exclude:
        keep &= ~mask
    b = np.rint(r / dk).astype(int)
    b_max = int(b[keep].max()) if keep.any() else 0
    k_centers = np.arange(1, b_max + 1, dtype=float) * dk
    e_sum = np.zeros(b_max, dtype=float)
    n_modes = np.zeros(b_max, dtype=int)
    for ring in range(1, b_max + 1):
        sel = keep & (b == ring)
        e_sum[ring - 1] = float(P[sel].sum())
        n_modes[ring - 1] = int(sel.sum())
    return k_centers, e_sum, n_modes


def mainlobe_halfwidth_bins(window: np.ndarray, grid: PlaneGrid, pad: int = 8) -> float:
    """First-null half-width of the window transform, in zonal-fundamental bins.

    Measured by a ``pad``x zero-padded FFT of the window; the magnitude is
    scanned outward along the kx axis (ky = 0) to its first local minimum, and
    that wavenumber is expressed in units of ``1 / Lx``. Assumes the window
    transform decays monotonically from DC to its first null (true of the
    radial Hann); a taper violating that would terminate the scan early.

    Args:
        window: 2-D taper (e.g. :func:`radial_hann`).
        grid: The plane grid the window lives on.
        pad: Zero-padding factor (resolution = ``1 / pad`` bin).

    Returns:
        Half-width in zonal-fundamental bins (multiples of ``1 / Lx``).
    """
    ny, nx = window.shape
    padded = np.zeros((pad * ny, pad * nx))
    padded[:ny, :nx] = window
    mag = np.abs(np.fft.fft2(padded))[0, : pad * nx // 2]
    i = 1
    while i + 1 < mag.size and mag[i + 1] < mag[i]:
        i += 1
    return i / pad
