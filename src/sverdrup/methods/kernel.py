"""Space-time covariance kernels behind a small interface (nonstationary-ready)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np

from sverdrup.core.parameters import LatitudeField
from sverdrup.core.types import Points

_DEG2KM = 111.195  # approx km per degree on a sphere of R=6371 km


@runtime_checkable
class Kernel(Protocol):
    """A covariance kernel evaluated between two space-time point sets."""

    def evaluate(self, a: Points, b: Points) -> np.ndarray:
        """Return the ``(len(a), len(b))`` covariance between point sets."""
        ...


@dataclass(frozen=True)
class Matern32SpaceTime:
    """Separable Matern-3/2 in (great-circle space, time).

    Spatial distance is approximated in km from lon/lat degrees; temporal distance
    uses the time column directly. ``length_scale`` in km, ``time_scale`` in days.
    """

    variance: float
    length_scale: float
    time_scale: float

    def evaluate(self, a: Points, b: Points) -> np.ndarray:
        """Return the separable space-time covariance between ``a`` and ``b``."""
        ds = self._spatial_km(a, b) / self.length_scale
        dt = np.abs(a[:, None, 2] - b[None, :, 2]) / self.time_scale
        return np.asarray(self.variance * _m32(ds) * _m32(dt))

    @staticmethod
    def _spatial_km(a: Points, b: Points) -> np.ndarray:
        """Return the ``(len(a), len(b))`` planar-approx great-circle distance in km."""
        dlon = (a[:, None, 0] - b[None, :, 0]) * np.cos(
            np.deg2rad(0.5 * (a[:, None, 1] + b[None, :, 1]))
        )
        dlat = a[:, None, 1] - b[None, :, 1]
        return np.asarray(np.sqrt(dlon**2 + dlat**2) * _DEG2KM)


@dataclass(frozen=True)
class GaussianSpaceTimeDegrees:
    """Separable Gaussian (squared-exponential) covariance in degree-space.

    Reproduces the 2021a challenge BASELINE OI (``src/mod_oi.py::oi_core``):

        B(a, b) = variance · exp( −(Δlon/Lx)² − (Δlat/Ly)² − (Δt/Lt)² )

    Spatial differences are **raw degrees** (no cos-lat correction, no km
    conversion), so the kernel is anisotropic in physical space. ``lx_deg`` and
    ``ly_deg`` are in degrees; ``time_scale`` in days.
    """

    variance: float
    lx_deg: float
    ly_deg: float
    time_scale: float

    def evaluate(self, a: Points, b: Points) -> np.ndarray:
        """Return the separable Gaussian covariance between ``a`` and ``b``."""
        dlon = (a[:, None, 0] - b[None, :, 0]) / self.lx_deg
        dlat = (a[:, None, 1] - b[None, :, 1]) / self.ly_deg
        dt = (a[:, None, 2] - b[None, :, 2]) / self.time_scale
        return np.asarray(self.variance * np.exp(-(dlon**2) - dlat**2 - dt**2))


@dataclass(frozen=True)
class PaciorekGaussianDegrees:
    """Nonstationary Gaussian degree-space kernel (Paciorek–Schervish; spec §3).

    Per pair, with the shared-lx/ly length scale ``L(x) = lx_deg_base ·
    m(lat_x)`` and ``L̄² = (L(x)² + L(y)²)/2``:

        B(x, y) = σ(x)·σ(y) · [L(x)·L(y)/L̄²]
                  · exp( −(Δlon² + Δlat²)/L̄² − (Δt/Lt)² )

    The prefactor is the isotropic-2D Paciorek–Schervish normalization
    (|Σx|^¼|Σy|^¼ / |(Σx+Σy)/2|^½ for Σ = L²I) — what keeps the kernel PD;
    a naive L(x) substitution into the stationary form is NOT PD. σ² is the
    variance field (exp link ⇒ σ ≥ 0); the σ(x)·σ(y) outer scaling is the
    √(s(x)s(y)) algebra of Phases 8/9 applied to the PRIOR. The temporal
    factor stays stationary (spec fork b: no lat-varying Lt).

    Constant limits: a scalar ``variance_field`` and/or ``l_mult_field=None``
    (or zero-coefficient fields) reduce EXACTLY to the stationary
    ``GaussianSpaceTimeDegrees`` arithmetic at ``L0 = lx_deg_base = 1``
    (the constant-reduction identity test pins this against the SHIPPED
    ``baseline_kernel()``).

    Attributes:
        variance_field: σ²(lat) — a ``LatitudeField`` (or a plain float for
            the constant limit).
        lx_deg_base: The base length scale L0 in degrees (shared lx = ly).
        l_mult_field: The unitless length multiplier m(lat) (``None`` ⇒ 1).
        time_scale: Lt in days (stationary temporal factor).
    """

    variance_field: LatitudeField | float
    lx_deg_base: float
    l_mult_field: LatitudeField | None
    time_scale: float

    def _sigma(self, lat: np.ndarray) -> np.ndarray:
        """Return σ(lat) = sqrt of the variance field at ``lat``."""
        if isinstance(self.variance_field, LatitudeField):
            return np.asarray(np.sqrt(self.variance_field.at(lat)))
        return np.full(lat.shape, np.sqrt(self.variance_field))

    def _mult(self, lat: np.ndarray) -> np.ndarray:
        """Return the length multiplier m(lat) (1 when no field is set)."""
        if self.l_mult_field is None:
            return np.ones(lat.shape)
        return self.l_mult_field.at(lat)

    def evaluate(self, a: Points, b: Points) -> np.ndarray:
        """Return the ``(len(a), len(b))`` nonstationary covariance."""
        lx = self.lx_deg_base * self._mult(a[:, 1])[:, None]
        ly = self.lx_deg_base * self._mult(b[:, 1])[None, :]
        l2 = 0.5 * (lx**2 + ly**2)
        prefactor = lx * ly / l2
        dlon = a[:, None, 0] - b[None, :, 0]
        dlat = a[:, None, 1] - b[None, :, 1]
        dt = (a[:, None, 2] - b[None, :, 2]) / self.time_scale
        sig = self._sigma(a[:, 1])[:, None] * self._sigma(b[:, 1])[None, :]
        return np.asarray(sig * prefactor * np.exp(-(dlon**2 + dlat**2) / l2 - dt**2))

    def prior_var_at(self, pts: Points) -> np.ndarray:
        """Return the pointwise prior variance — the variance field itself.

        At x == y the prefactor is exactly 1 and Δt = 0, so the prior
        variance is σ²(lat) with NO sqrt round-trip (exact; the brute-force
        ``np.diag(evaluate(a, a))`` cross-check tolerates only the
        ``sqrt(v)²`` ulp).

        Args:
            pts: ``(n, 3)`` lon/lat/time points.

        Returns:
            ``variance_field(lat)`` as an ``(n,)`` array.
        """
        lat = np.asarray(pts[:, 1], float)
        if isinstance(self.variance_field, LatitudeField):
            return self.variance_field.at(lat)
        return np.full(lat.shape, float(self.variance_field))


def _m32(r: np.ndarray) -> np.ndarray:
    """Matern-3/2 correlation as a function of scaled distance ``r``."""
    s = np.sqrt(3.0) * r
    return np.asarray((1.0 + s) * np.exp(-s))
