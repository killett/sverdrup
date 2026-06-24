"""Tiling orchestration: scale-aware halos + projection-aware partitions (design section 3)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np

from sverdrup.core.geometry import HaloExtent, Tile, Window
from sverdrup.core.grid import GridSpec
from sverdrup.core.parameters import ParameterProvider

_KM_PER_DEG_LAT = 111.195


@runtime_checkable
class HaloPolicy(Protocol):
    """Sizes a tile's halo (km) from the core geometry and the correlation length."""

    def halo_for(
        self,
        core: Window,
        grid: GridSpec,
        correlation_length: ParameterProvider,
        stencil_radius_km: float,
    ) -> HaloExtent:
        """Return the halo extent for ``core``."""
        ...


@dataclass(frozen=True)
class ScaleAwareHalo:
    """``halo_km = max(k * correlation_length, stencil)``, widest over the core band.

    The correlation length is monotone decreasing in ``|lat|``, so the widest value over
    a core band is at its equatorward-most latitude (``0`` clamped into the band's range).

    Attributes:
        k: The multiple of the correlation length used as the halo radius.
    """

    k: float

    def halo_for(
        self,
        core: Window,
        grid: GridSpec,
        correlation_length: ParameterProvider,
        stencil_radius_km: float,
    ) -> HaloExtent:
        """Return ``HaloExtent(max(k * widest_corr_len, stencil_radius_km))``.

        Args:
            core: The core window the halo pads.
            grid: The target grid (CRS context for the provider).
            correlation_length: Provider resolving ``correlation_length`` (km) by latitude.
            stencil_radius_km: The minimum (derived-operator stencil) halo radius in km.

        Returns:
            The projection-neutral ``HaloExtent`` in kilometres.
        """
        lat_lo, lat_hi = core.lat_range
        lat_eq = min(max(0.0, lat_lo), lat_hi)  # equatorward-most latitude in the band
        lon_mid = 0.5 * (core.lon_range[0] + core.lon_range[1])
        band = GridSpec.lonlat(np.array([lon_mid]), np.array([lat_eq]))
        cl = np.asarray(correlation_length.resolve("correlation_length", band))
        return HaloExtent(radius_km=max(self.k * float(np.max(cl)), stencil_radius_km))


@runtime_checkable
class TilePartition(Protocol):
    """Splits a target grid into overlapping tiles."""

    def tiles(self, target: GridSpec) -> Sequence[Tile]:
        """Return the tiles covering ``target``."""
        ...


@dataclass(frozen=True)
class LonLatPartition:
    """Uniform-core lon/lat partition with scale-aware (non-uniform) halos.

    Attributes:
        n_lon: Number of core columns along longitude.
        n_lat: Number of core rows along latitude.
        halo: The halo policy sizing each tile's pad.
        correlation_length: Provider resolving the correlation length by latitude.
        stencil_radius_km: The minimum halo radius (derived-operator stencil) in km.
        time_range: The space-time window's time range carried on each ``Window``.
    """

    n_lon: int
    n_lat: int
    halo: HaloPolicy
    correlation_length: ParameterProvider
    stencil_radius_km: float
    time_range: tuple[float, float] = (0.0, 21.0)

    def tiles(self, target: GridSpec) -> Sequence[Tile]:
        """Split the target into n_lon x n_lat cores; pad each by its scale-aware halo.

        Args:
            target: The full target grid to partition.

        Returns:
            One ``Tile`` per core cell, whose ``grid`` is a window of ``target`` (so overlap
            nodes are shared subsets of the target — co-registered).
        """
        lon_edges = np.linspace(target.x.min(), target.x.max(), self.n_lon + 1)
        lat_edges = np.linspace(target.y.min(), target.y.max(), self.n_lat + 1)
        out: list[Tile] = []
        for i in range(self.n_lon):
            for j in range(self.n_lat):
                core = Window(
                    (lon_edges[i], lon_edges[i + 1]),
                    (lat_edges[j], lat_edges[j + 1]),
                    self.time_range,
                )
                h = self.halo.halo_for(
                    core, target, self.correlation_length, self.stencil_radius_km
                )
                lat_mid = 0.5 * (core.lat_range[0] + core.lat_range[1])
                pad_lat = h.radius_km / _KM_PER_DEG_LAT
                pad_lon = h.radius_km / (
                    _KM_PER_DEG_LAT * max(np.cos(np.deg2rad(lat_mid)), 1e-3)
                )
                ext = Window(
                    (core.lon_range[0] - pad_lon, core.lon_range[1] + pad_lon),
                    (core.lat_range[0] - pad_lat, core.lat_range[1] + pad_lat),
                    self.time_range,
                )
                grid = target.window(lon_range=ext.lon_range, lat_range=ext.lat_range)
                out.append(Tile(core, ext, grid))
        return out
