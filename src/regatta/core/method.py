"""Method contract (spec 5.2)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from regatta.core.types import UncertaintyCapability

if TYPE_CHECKING:
    from regatta.core.distribution import PredictiveDistribution
    from regatta.core.grid import GridSpec
    from regatta.core.observations import ObsWindow
    from regatta.core.parameters import ParameterProvider, ParameterSpace


@runtime_checkable
class Method(Protocol):
    """A reconstruction method producing a predictive distribution from observations."""

    native_capability: UncertaintyCapability

    def solve(
        self,
        obs: ObsWindow,
        grid: GridSpec,
        params: ParameterProvider,
        time_days: float,
    ) -> PredictiveDistribution:
        """Solve for the predictive distribution at one output time."""
        ...

    def parameter_space(self) -> ParameterSpace:
        """Return the declarative tunable parameter space."""
        ...
