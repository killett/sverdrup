"""Field-capable parameter provider seam (invariant 6; spec section 5.2)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from sverdrup.core.grid import GridSpec
from sverdrup.core.types import ScalarOrField


@runtime_checkable
class ParameterProvider(Protocol):
    """Resolves a named parameter to a scalar or a spatial field over a grid."""

    def resolve(self, name: str, grid: GridSpec) -> ScalarOrField:
        """Resolve ``name`` to a scalar or field over ``grid``."""
        ...

    def params_key(self) -> str:
        """Return a stable canonical string identifying the resolved parameters."""
        ...


@dataclass(frozen=True)
class ConstantProvider:
    """Phase-1 provider: returns constant scalars. The field seam still exists."""

    values: dict[str, float]

    def resolve(self, name: str, grid: GridSpec) -> ScalarOrField:
        """Return the constant value for ``name`` (grid-independent in Phase 1).

        Args:
            name: Parameter name.
            grid: The grid (unused for constants; the seam for spatial fields).

        Returns:
            The constant scalar value.
        """
        return self.values[name]

    def params_key(self) -> str:
        """Return an order-independent canonical key of the resolved parameters."""
        return ";".join(f"{k}={self.values[k]!r}" for k in sorted(self.values))


@dataclass(frozen=True)
class ResolvedParams:
    """Concrete parameter values resolved for one solve (provenance records this)."""

    values: dict[str, ScalarOrField]
    key: str


@dataclass(frozen=True)
class ParameterSpace:
    """Declarative tunable space — consumed later by the (deferred) tuner."""

    bounds: dict[str, tuple[float, float]]
