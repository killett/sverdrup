"""Derived-quantity closure + propagation dispatch (invariant 10; spec 5.4)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from sverdrup.core.types import CovFidelity, Linearity

if TYPE_CHECKING:
    from sverdrup.core.distribution import PredictiveDistribution


@dataclass(frozen=True)
class Route:
    """The chosen propagation path plus the covariance fidelity stamped on it."""

    path: str  # "covariance" | "sample"
    fidelity: CovFidelity


def select_route(linearity: Linearity, fidelity: CovFidelity) -> Route:
    """Pick the propagation path by linearity x covariance fidelity.

    Linear functionals take the covariance path (exact preferred); the result is
    stamped with the fidelity actually used. Nonlinear functionals take the sample path.

    Args:
        linearity: Whether the derived functional is linear or nonlinear.
        fidelity: The covariance fidelity available from the base distribution.

    Returns:
        The selected ``Route`` with its stamped fidelity.
    """
    if linearity is Linearity.NONLINEAR:
        return Route("sample", fidelity)
    return Route("covariance", fidelity)


@runtime_checkable
class DerivedQuantity(Protocol):
    """A functional of the SSHA field with a declared linearity."""

    linearity: Linearity

    def apply(self, dist: PredictiveDistribution) -> PredictiveDistribution:
        """Apply the functional, returning a derived predictive distribution."""
        ...
