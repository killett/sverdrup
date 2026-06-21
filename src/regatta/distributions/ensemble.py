"""Ensemble predictive distribution: the M-sample-map canonical compute-time rep."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from regatta.core.grid import GridSpec
from regatta.core.provenance import UncertaintyProvenance
from regatta.core.types import CovFidelity, Field, Points, Seed


@dataclass
class EnsemblePredictiveDistribution:
    """A predictive distribution carried as an ``(m, ny, nx)`` sample map (fidelity SAMPLE)."""

    grid: GridSpec
    samples: np.ndarray  # (m, ny, nx)
    provenance: UncertaintyProvenance
    time_days: float
    fidelity: CovFidelity = CovFidelity.SAMPLE

    def _flat(self) -> np.ndarray:
        """Return the samples flattened to ``(m, ngrid)``."""
        m = self.samples.shape[0]
        return self.samples.reshape(m, -1)

    def marginal_variance(self) -> Field:
        """Return the per-node sample variance, shape ``(ny, nx)``."""
        return np.asarray(self._flat().var(axis=0, ddof=1).reshape(self.grid.shape))

    def covariance(self, a: Points, b: Points) -> np.ndarray:
        """Return the sample covariance between nearest nodes to ``a`` and ``b``."""
        flat = self._flat()
        ia = _node_index(self.grid, a)
        ib = _node_index(self.grid, b)
        cov = np.cov(flat, rowvar=False)
        return np.asarray(cov[np.ix_(ia, ib)])

    def sample(self, m: int, seed: Seed) -> np.ndarray:
        """Return ``m`` draws by resampling members with replacement, shape ``(m, ny, nx)``."""
        rng = np.random.default_rng(seed)
        idx = rng.integers(0, self.samples.shape[0], size=m)
        return np.asarray(self.samples[idx])

    def regrid(self, target: GridSpec) -> EnsemblePredictiveDistribution:
        """Not implemented in Phase 1 (lands with the blend layer)."""
        raise NotImplementedError(
            "Ensemble regrid lands with the blend layer (Phase 2)."
        )


def _node_index(grid: GridSpec, pts: Points) -> np.ndarray:
    """Return the nearest grid-node index for each point in ``pts``."""
    nodes = grid.points(pts[0, 2] if len(pts) else 0.0)
    return np.asarray(
        np.argmin(np.linalg.norm(pts[:, None, :2] - nodes[None, :, :2], axis=2), axis=1)
    )
