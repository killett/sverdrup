"""Space-time covariance kernels behind a small interface (nonstationary-ready)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np

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


def _m32(r: np.ndarray) -> np.ndarray:
    """Matern-3/2 correlation as a function of scaled distance ``r``."""
    s = np.sqrt(3.0) * r
    return np.asarray((1.0 + s) * np.exp(-s))
