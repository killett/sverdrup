"""Along-track observation model with a first-class error operator (spec section 5.1)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, cast, runtime_checkable

import numpy as np

from sverdrup.core.types import Points


@runtime_checkable
class ObservationErrorModel(Protocol):
    """Observation-error covariance R. Not merely a scalar noise sigma."""

    def add_to_diagonal(self, k: np.ndarray) -> None:
        """In-place add R's diagonal contribution to obs-obs kernel ``k``."""

    def as_matrix(self, n: int) -> np.ndarray:
        """Materialise the (n, n) R (used for correlated models / tests)."""


@dataclass(frozen=True)
class DiagonalErrorModel:
    """White (uncorrelated) per-observation variances — the nadir default."""

    variance: np.ndarray

    def add_to_diagonal(self, k: np.ndarray) -> None:
        """In-place add the per-obs variances to the diagonal of ``k``.

        Args:
            k: The obs-obs kernel matrix, modified in place.
        """
        k[np.diag_indices_from(k)] += self.variance

    def as_matrix(self, n: int) -> np.ndarray:
        """Return the dense ``(n, n)`` diagonal R.

        Args:
            n: Number of observations (must match ``variance`` length).

        Returns:
            The diagonal ``(n, n)`` observation-error covariance.
        """
        return np.diag(self.variance)


@dataclass(frozen=True)
class BandedErrorModel:
    """Correlated error model (exponential band) — the swath-ready hook."""

    variance: np.ndarray
    corr_length: float
    coords1d: np.ndarray

    def as_matrix(self, n: int) -> np.ndarray:
        """Return the dense ``(n, n)`` exponentially-correlated R.

        Args:
            n: Number of observations (must match the model arrays).

        Returns:
            A symmetric ``(n, n)`` covariance with exponential off-diagonal decay.
        """
        d = np.abs(self.coords1d[:, None] - self.coords1d[None, :])
        corr = np.exp(-d / self.corr_length)
        s = np.sqrt(self.variance)
        return np.asarray((s[:, None] * s[None, :]) * corr, dtype=float)

    def add_to_diagonal(self, k: np.ndarray) -> None:
        """In-place add the full correlated block to ``k``.

        Banded R contributes its full block; callers add ``as_matrix`` for
        correlated models.

        Args:
            k: The obs-obs kernel matrix, modified in place.
        """
        k += self.as_matrix(k.shape[0])


@dataclass(frozen=True)
class Observation:
    """A single nadir observation."""

    mission: str
    lon: float
    lat: float
    time_days: float
    sla: float


@dataclass(frozen=True)
class ObsWindow:
    """Windowed, lazily-accessed observations over a space-time window."""

    _lon: np.ndarray
    _lat: np.ndarray
    _time: np.ndarray
    _values: object  # numpy or dask array; kept lazy until values() is called
    error_model: ObservationErrorModel
    mission: np.ndarray | None = None

    @classmethod
    def from_arrays(
        cls,
        lon: np.ndarray,
        lat: np.ndarray,
        time: np.ndarray,
        values: object,
        error_model: ObservationErrorModel,
        mission: np.ndarray | None = None,
    ) -> ObsWindow:
        """Build an ``ObsWindow`` from coordinate/value arrays without forcing compute.

        Args:
            lon: 1-D longitudes in degrees.
            lat: 1-D latitudes in degrees.
            time: 1-D times in days.
            values: 1-D SLA values (numpy or dask array); kept lazy.
            error_model: The observation-error covariance operator.
            mission: Optional per-obs mission labels.

        Returns:
            A new ``ObsWindow``.
        """
        return cls(
            np.asarray(lon, float),
            np.asarray(lat, float),
            np.asarray(time, float),
            values,
            error_model,
            mission,
        )

    def coords(self) -> Points:
        """Return the ``(n, 3)`` space-time coordinates ``(lon, lat, time)``."""
        out = np.empty((self._lon.size, 3), float)
        out[:, 0], out[:, 1], out[:, 2] = self._lon, self._lat, self._time
        return out

    def values(self) -> np.ndarray:
        """Materialise and return the ``(n,)`` SLA values (computes dask on demand)."""
        v = self._values
        if hasattr(v, "compute"):
            return np.asarray(cast(Any, v).compute(), dtype=float)
        return np.asarray(v, dtype=float)

    def __len__(self) -> int:
        """Return the number of observations in the window."""
        return int(self._lon.size)
