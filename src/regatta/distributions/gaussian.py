"""Method-agnostic Gaussian predictive distribution (mean + injected covariance operator)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from regatta.core.distribution import CovarianceOperator
from regatta.core.grid import GridSpec
from regatta.core.provenance import UncertaintyProvenance
from regatta.core.types import Field, Points, Seed


@dataclass
class GaussianPredictiveDistribution:
    """A Gaussian field predictive: a mean field plus a zero-mean covariance operator."""

    grid: GridSpec
    mean: Field
    cov_op: CovarianceOperator
    provenance: UncertaintyProvenance
    time_days: float

    def marginal_variance(self) -> Field:
        """Return the marginal-variance field from the operator, shape ``(ny, nx)``."""
        var = self.cov_op.marginal_var(self.grid.points(self.time_days))
        return np.asarray(var).reshape(self.grid.shape)

    def covariance(self, a: Points, b: Points) -> np.ndarray:
        """Return the ``(len(a), len(b))`` covariance by delegating to the operator."""
        return self.cov_op.cov(a, b)

    def sample(self, m: int, seed: Seed) -> np.ndarray:
        """Return ``m`` field draws (zero-mean operator draws + mean), shape ``(m, ny, nx)``."""
        pts = self.grid.points(self.time_days)
        draws = self.cov_op.posterior_sample(pts, seed, m)  # (m, ngrid) zero-mean
        ny, nx = self.grid.shape
        return np.asarray(self.mean[None, :, :] + draws.reshape(m, ny, nx))

    def regrid(self, target: GridSpec) -> GaussianPredictiveDistribution:
        """Re-express on ``target`` by re-evaluating the operator at target nodes.

        Operator-on-covariance (invariant 7): the covariance machinery is the
        operator, so variance on the target grid is exact, not interpolated.

        Args:
            target: The destination grid.

        Returns:
            A Gaussian distribution on ``target``.
        """
        tgt_pts = target.points(self.time_days)
        src_pts = self.grid.points(self.time_days)
        mean_interp = _nearest(self.mean.ravel(), src_pts, tgt_pts).reshape(
            target.shape
        )
        return GaussianPredictiveDistribution(
            target, mean_interp, self.cov_op, self.provenance, self.time_days
        )


def _nearest(values: np.ndarray, src: Points, tgt: Points) -> np.ndarray:
    """Nearest-neighbour resample of ``values`` from ``src`` nodes onto ``tgt`` nodes."""
    idx = np.argmin(np.linalg.norm(tgt[:, None, :2] - src[None, :, :2], axis=2), axis=1)
    return np.asarray(values[idx])
