"""The three hexagonal boundaries (spec 5.8, 5.9)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from regatta.core.observations import ObsWindow
    from regatta.core.product import Product

Range = tuple[float, float]


@runtime_checkable
class DataSource(Protocol):
    """Source of windowed observations over a space-time box."""

    def window(
        self, *, lon_range: Range, lat_range: Range, time_range: Range
    ) -> ObsWindow:
        """Return observations inside the given lon/lat/time ranges."""
        ...


@runtime_checkable
class ResultSink(Protocol):
    """Persistence boundary for produced Product bundles."""

    def write(self, product: Product, path: str) -> None:
        """Persist ``product`` to ``path``."""
        ...


@runtime_checkable
class Executor(Protocol):
    """Compute boundary that runs a unit of work and returns its Product."""

    def submit(self, unit_of_work: object) -> Product:
        """Run ``unit_of_work`` and return its Product."""
        ...
