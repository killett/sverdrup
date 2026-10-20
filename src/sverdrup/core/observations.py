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
        """In-place add R's contribution for these observations to obs-obs kernel ``k``.

        Implementations may add off-diagonal structure (e.g. a full
        correlated block), not just the diagonal.
        """

    def as_matrix(self, n: int) -> np.ndarray:
        """Materialise the (n, n) R (used for correlated models / tests)."""


def _check_count(n_var: int, n: int) -> None:
    """Refuse an R sized for a different number of observations.

    Args:
        n_var: How many variances the model carries.
        n: How many observations the caller has.

    Raises:
        ValueError: If they differ.
    """
    if n_var != n:
        raise ValueError(f"error model has {n_var} variances for {n} observations")


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

        Raises:
            ValueError: If ``n`` is not the number of variances.
        """
        _check_count(np.size(self.variance), n)
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

        Raises:
            ValueError: If ``n`` is not the number of variances.
        """
        _check_count(np.size(self.variance), n)
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


def diagonal_variances(model: ObservationErrorModel, n: int) -> np.ndarray:
    """Per-observation variances of a DIAGONAL R, refusing anything else.

    Every path that reads R as a vector — OI's ``noise_diag``, GMRF/FEM's
    ``R^-1``, the subset rebuilders, the perturbation adapter — is
    diagonal-only. Each used to take ``np.diag(as_matrix(n))`` (or
    ``.diagonal()``), which silently dropped a correlated model's
    off-diagonal (hygiene P1-#6) and densified an ``(n, n)`` matrix to do
    it. A :class:`DiagonalErrorModel` is read directly; any other model is
    accepted only if its R has no off-diagonal entry.

    Args:
        model: The observation-error model.
        n: Number of observations it must describe.

    Returns:
        A fresh ``(n,)`` copy of the variances (dtype preserved).

    Raises:
        NotImplementedError: If R has an off-diagonal entry (a correlated
            model such as :class:`BandedErrorModel`) — this path would drop
            its correlations.
        ValueError: If the model does not describe ``n`` observations.
    """
    if isinstance(model, DiagonalErrorModel):
        var = np.array(model.variance)
        _check_count(var.size, n)
        return var
    mat = np.asarray(model.as_matrix(n))
    if mat.shape != (n, n):
        raise ValueError(f"error model has a {mat.shape} R for {n} observations")
    if np.any(mat[~np.eye(n, dtype=bool)] != 0.0):
        raise NotImplementedError(
            f"{type(model).__name__} is a correlated R; this path is "
            "diagonal-only and would silently drop its correlations"
        )
    return np.array(np.diag(mat))


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
