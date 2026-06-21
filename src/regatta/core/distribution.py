"""Headline predictive-distribution and covariance-operator protocols (spec 5.3)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from regatta.core.types import CovFidelity, Field, Points, Seed

if TYPE_CHECKING:
    import numpy as np

    from regatta.core.grid import GridSpec
    from regatta.core.provenance import UncertaintyProvenance


@runtime_checkable
class CovarianceOperator(Protocol):
    """Zero-mean covariance machinery; queried on demand, never materialised densely."""

    fidelity: CovFidelity

    def cov(self, a: Points, b: Points) -> np.ndarray:
        """Return the ``(len(a), len(b))`` cross-covariance between point sets."""
        ...

    def marginal_var(self, a: Points) -> np.ndarray:
        """Return the ``(len(a),)`` marginal variances at points ``a``."""
        ...

    def posterior_sample(self, s: Points, seed: Seed, m: int) -> np.ndarray:
        """Return ``(m, len(s))`` zero-mean posterior draws at points ``s``."""
        ...


@runtime_checkable
class PredictiveDistribution(Protocol):
    """A first-class predictive distribution over the SSHA field."""

    grid: GridSpec
    provenance: UncertaintyProvenance

    def marginal_variance(self) -> Field:
        """Return the marginal-variance field, shape ``(ny, nx)``."""
        ...

    def covariance(self, a: Points, b: Points) -> np.ndarray:
        """Return the ``(len(a), len(b))`` covariance between query points."""
        ...

    def sample(self, m: int, seed: Seed) -> np.ndarray:
        """Return ``m`` field draws, shape ``(m, ny, nx)``."""
        ...

    def regrid(self, target: GridSpec) -> PredictiveDistribution:
        """Return this distribution re-expressed on ``target`` (operator-on-covariance)."""
        ...
