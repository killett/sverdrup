"""Real derived operator: CRS-aware spatial first-difference (exact covariance path; spec 5.4)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, NoReturn, cast

import numpy as np

from regatta.core.distribution import PredictiveDistribution
from regatta.core.grid import GridSpec
from regatta.core.provenance import UncertaintyProvenance
from regatta.core.types import Field, Linearity, Points, Seed

_DEG2M = 111195.0


@dataclass
class _DiffField:
    """A predictive distribution over the first-difference field (LINEAR functional)."""

    grid: GridSpec
    mean: Field
    var: Field
    metric_scale_x: np.ndarray
    provenance: UncertaintyProvenance
    time_days: float

    def marginal_variance(self) -> Field:
        """Return the propagated variance field of the difference."""
        return self.var

    def covariance(self, a: Points, b: Points) -> np.ndarray:
        """Not needed in Phase 1 (difference-field cross-covariance)."""
        raise NotImplementedError(
            "Difference-field cross-covariance not needed in Phase 1."
        )

    def sample(self, m: int, seed: Seed) -> NoReturn:
        """Not needed in Phase 1."""
        raise NotImplementedError

    def regrid(self, target: GridSpec) -> NoReturn:
        """Not needed in Phase 1."""
        raise NotImplementedError


class FirstDifference:
    """Neighbour difference along an axis, scaled by the CRS metric."""

    linearity = Linearity.LINEAR

    def __init__(self, axis: str) -> None:
        """Store the difference axis.

        Args:
            axis: ``"x"`` (along longitude) or ``"y"`` (along latitude).
        """
        self.axis = axis

    def apply(self, dist: PredictiveDistribution) -> _DiffField:
        """Apply the metric-scaled neighbour difference to ``dist``.

        Args:
            dist: The base predictive distribution (Gaussian or Ensemble).

        Returns:
            A ``_DiffField`` carrying the difference mean and exact propagated variance.
        """
        grid = dist.grid
        lon, lat = grid._lonlat_nodes()
        if self.axis == "x":
            step_deg = np.diff(grid.x)
            scale = np.cos(np.deg2rad(lat[:, :-1])) * _DEG2M * step_deg[None, :]
        else:
            step_deg = np.diff(grid.y)
            scale = _DEG2M * step_deg[:, None] * np.ones_like(lat[:-1, :])
        mean = self._diff(_mean_of(dist), scale)
        var = self._diff_var(dist, scale)
        metric_scale_x = scale[0] if self.axis == "x" else scale[:, 0]
        time_days = float(cast(Any, dist).time_days)
        return _DiffField(grid, mean, var, metric_scale_x, dist.provenance, time_days)

    def _diff(self, field: Field, scale: np.ndarray) -> Field:
        """Return the metric-scaled neighbour difference of ``field``."""
        d = np.diff(field, axis=1 if self.axis == "x" else 0)
        return np.asarray(d / scale)

    def _diff_var(self, dist: PredictiveDistribution, scale: np.ndarray) -> Field:
        """Return the exact propagated variance ``Var(a)+Var(b)-2Cov(a,b)`` / scale^2."""
        grid = dist.grid
        time_days = float(cast(Any, dist).time_days)
        pts = grid.points(time_days).reshape(*grid.shape, 3)
        ny, nx = grid.shape
        out = np.zeros((ny, nx - 1)) if self.axis == "x" else np.zeros((ny - 1, nx))
        rows, cols = out.shape
        for i in range(rows):
            for j in range(cols):
                a = pts[i, j][None, :]
                b = (pts[i, j + 1] if self.axis == "x" else pts[i + 1, j])[None, :]
                va = dist.covariance(a, a)[0, 0]
                vb = dist.covariance(b, b)[0, 0]
                cab = dist.covariance(a, b)[0, 0]
                out[i, j] = (va + vb - 2 * cab) / (scale[i, j] ** 2)
        return out


def _mean_of(dist: PredictiveDistribution) -> Field:
    """Return the mean field of ``dist`` (stored mean, or ensemble member mean)."""
    d = cast(Any, dist)
    if hasattr(dist, "mean"):
        return np.asarray(d.mean)
    return np.asarray(d.samples.mean(axis=0))
