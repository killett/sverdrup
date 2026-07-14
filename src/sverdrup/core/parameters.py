"""Field-capable parameter provider seam (invariant 6).

Phase-1 spec §5.2; the latitude forms follow Phase-10 spec §2.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np

from sverdrup.core.grid import GridSpec
from sverdrup.core.types import ScalarOrField

_V_CENTER, _V_SCALE = 38.0, 5.0  # v = (lat - 38) / 5 -> box edges at v = ±1
_LAT_HULL = (33.0, 43.0)  # constant continuation outside (PolyCalibration convention)


@dataclass(frozen=True)
class LatitudeField:
    """Named low-dof latitude form (invariant-12 vehicle; spec §2).

    A small typed value carrying the named form + coefficients, evaluable at
    latitudes. Consumers dispatch ON TYPE: a resolve returning a
    ``LatitudeField`` routes the nonstationary kernel path; it must never be
    silently coerced to a scalar (``__float__`` raises).

    Attributes:
        form: ``"exp-quad"`` (``exp(c0 + c1*v + c2*v**2)``) or
            ``"exp-linear-mult"`` (``exp(l1*v)``, a unitless multiplier).
        coeffs: The form's coefficients, ``(c0, c1, c2)`` or ``(l1,)``.
    """

    form: str
    coeffs: tuple[float, ...]

    def at(self, lat: np.ndarray) -> np.ndarray:
        """Evaluate the field at latitudes (degrees north).

        Latitudes are clamped to the box hull [33, 43] first — constant
        continuation off-box, the PolyCalibration convention.

        Args:
            lat: Latitudes in degrees north (any shape).

        Returns:
            The field values, same shape as ``lat``.

        Raises:
            ValueError: For an unknown ``form``.
        """
        v = (np.clip(np.asarray(lat, float), *_LAT_HULL) - _V_CENTER) / _V_SCALE
        if self.form == "exp-quad":
            c0, c1, c2 = self.coeffs
            return np.asarray(np.exp(c0 + c1 * v + c2 * v**2))
        if self.form == "exp-linear-mult":
            (l1,) = self.coeffs
            return np.asarray(np.exp(l1 * v))
        raise ValueError(f"unknown form {self.form!r}")

    def key(self) -> str:
        """Return the canonical serialization (form + coefficients, repr-stable)."""
        return f"{self.form}({','.join(repr(c) for c in self.coeffs)})"

    def __float__(self) -> float:
        """Refuse scalar coercion — a field is not a number.

        Declared so ``float(provider.resolve(...))`` call sites stay type-clean
        for scalar providers, while an accidental field-to-float coercion (the
        bug the dispatch contract exists to prevent) fails LOUDLY at runtime.

        Raises:
            TypeError: Always.
        """
        raise TypeError(
            f"LatitudeField({self.key()}) cannot be coerced to float — "
            "dispatch on type (spec §2 resolve/dispatch contract)"
        )


@runtime_checkable
class ParameterProvider(Protocol):
    """Resolves a named parameter to a scalar, spatial field, or latitude form."""

    def resolve(self, name: str, grid: GridSpec) -> ScalarOrField | LatitudeField:
        """Resolve ``name`` to a scalar, field over ``grid``, or ``LatitudeField``."""
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
    """Resolves core names to floats and varied names to ``LatitudeField``s.

    Superseded IN PLACE for Phase 10 (invariant-12 option B; spec §2, no
    shim). Archaeology: the Phase-1 incarnation resolved
    ``correlation_length`` via a cos(lat) blend — a name OI's solve never
    requests, so the invariant-12 deferral was never runtime-load-bearing;
    Phase 10 makes the vehicle real with named low-dof forms.

    ``grid`` is unused by this provider — latitudes come from the field
    CONSUMER (the nonstationary kernel evaluates ``LatitudeField.at`` at its
    own points), so unit tests may pass ``None``.

    Attributes:
        core: Names resolved as constant scalars (e.g. ``time_scale``).
        varied: Names resolved as typed latitude forms (e.g. ``variance``).
    """

    core: dict[str, float]
    varied: dict[str, LatitudeField]

    def resolve(
        self, name: str, grid: GridSpec | None
    ) -> ScalarOrField | LatitudeField:
        """Resolve ``name`` to a float (core) or ``LatitudeField`` (varied).

        Args:
            name: Parameter name.
            grid: Unused (latitudes come from the field consumer).

        Returns:
            ``varied[name]`` if present, else ``core[name]``.
        """
        if name in self.varied:
            return self.varied[name]
        return self.core[name]

    def params_key(self) -> str:
        """Return an order-independent canonical key (forms + coefficients).

        The tuned config is reconstructible from provenance alone (spec §2):
        varied entries serialize via ``LatitudeField.key()`` (named form +
        repr'd coefficients).
        """
        core = ";".join(f"{k}={self.core[k]!r}" for k in sorted(self.core))
        varied = ";".join(f"{k}={self.varied[k].key()}" for k in sorted(self.varied))
        return f"latvary[{core}|{varied}]"


@dataclass(frozen=True)
class ResolvedParams:
    """Concrete parameter values resolved for one solve (provenance records this)."""

    values: dict[str, ScalarOrField]
    key: str


@dataclass(frozen=True)
class ParameterSpace:
    """Declarative tunable space — consumed later by the (deferred) tuner."""

    bounds: dict[str, tuple[float, float]]
