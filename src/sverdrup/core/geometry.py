"""Frozen, math-free geometry value objects for tiling (design section 2)."""

from __future__ import annotations

from dataclasses import dataclass

from sverdrup.core.grid import GridSpec

Range = tuple[float, float]


@dataclass(frozen=True)
class Window:
    """A space-time box: lon/lat/time ranges. Time rides here, not on GridSpec.

    Attributes:
        lon_range: Inclusive ``(min, max)`` longitude bounds in degrees.
        lat_range: Inclusive ``(min, max)`` latitude bounds in degrees.
        time_range: Inclusive ``(min, max)`` time bounds in days.
    """

    lon_range: Range
    lat_range: Range
    time_range: Range


@dataclass(frozen=True)
class HaloExtent:
    """Projection-neutral halo distance in kilometres (= k * correlation_length(lat)).

    Attributes:
        radius_km: The halo radius in kilometres (never a degree pad).
    """

    radius_km: float


@dataclass(frozen=True)
class Tile:
    """A tile: its authoritative core, its (core+halo) solve region, and its grid.

    Attributes:
        core_window: The authoritative interior this tile owns in the partition.
        extended_window: The core-plus-halo region the tile actually solves over.
        grid: The tile's spatial ``GridSpec`` (a window of the target grid).
    """

    core_window: Window
    extended_window: Window
    grid: GridSpec
