"""Field-capable parameter provider seam (invariant 6; spec section 5.2)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np

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
class LatitudeVaryingProvider:
    """Resolves ``correlation_length`` as a cos(lat) blend; other params are constants.

    Attributes:
        equator_km: The correlation length at the equator (widest).
        pole_km: The correlation length at the pole (narrowest).
        constants: Other named parameters resolved as scalars, untouched by latitude.
    """

    equator_km: float
    pole_km: float
    constants: dict[str, float]

    def resolve(self, name: str, grid: GridSpec) -> ScalarOrField:
        """Resolve ``name``; ``correlation_length`` becomes a latitude field.

        Args:
            name: Parameter name.
            grid: The grid over which a latitude-varying field is evaluated.

        Returns:
            A ``(ny, nx)`` field for ``correlation_length``, else the constant scalar.
        """
        if name == "correlation_length":
            _, lat = grid._lonlat_nodes()
            c = np.cos(np.deg2rad(lat))  # 1 at equator -> 0 at pole
            return np.asarray(self.pole_km + (self.equator_km - self.pole_km) * c)
        return self.constants[name]

    def params_key(self) -> str:
        """Return a stable canonical key including the latitude profile."""
        consts = ";".join(f"{k}={self.constants[k]!r}" for k in sorted(self.constants))
        return f"latvary(eq={self.equator_km!r},pole={self.pole_km!r});{consts}"


@dataclass(frozen=True)
class ResolvedParams:
    """Concrete parameter values resolved for one solve (provenance records this)."""

    values: dict[str, ScalarOrField]
    key: str


@dataclass(frozen=True)
class ParameterSpace:
    """Declarative tunable space — consumed later by the (deferred) tuner."""

    bounds: dict[str, tuple[float, float]]
