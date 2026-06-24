"""Tiling orchestration: scale-aware halos + projection-aware partitions (design section 3)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np

from sverdrup.application.uow import UnitOfWork
from sverdrup.core.geometry import HaloExtent, Tile, Window
from sverdrup.core.grid import GridSpec
from sverdrup.core.observations import ObsWindow
from sverdrup.core.parameters import ParameterProvider
from sverdrup.core.product import Product
from sverdrup.core.seeding import derive_seed
from sverdrup.distributions.blend import BlendedDistribution, BlendInput, BlendOperator

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


@runtime_checkable
class Executor(Protocol):
    """The existing scatter-gather port: submit one unit, get its Persisted Product."""

    def submit(self, uow: UnitOfWork) -> Product:
        """Run one unit of work and return its Persisted ``Product``."""
        ...


class TilingCoordinator:
    """Partition -> one UnitOfWork per tile via the existing Executor -> gather -> blend."""

    def __init__(self, blend: BlendOperator | None = None) -> None:
        """Store the blend operator (defaults to the standard partition-of-unity blend).

        Args:
            blend: The blend operator to combine gathered tile products.
        """
        self.blend_op = blend or BlendOperator()

    def run(
        self,
        target: GridSpec,
        partition: TilePartition,
        method: str,
        params: ParameterProvider,
        split: object,
        seed: int,
        output_times: Sequence[float],
        executor: Executor,
        *,
        obs_for_tile: Callable[[Tile], ObsWindow] | None = None,
        k: float = 3.0,
    ) -> list[BlendedDistribution]:
        """Run the tiled solve and return one ``BlendedDistribution`` per output time.

        Emits exactly one ``UnitOfWork`` per tile through the existing ``Executor`` port
        (no re-granularization), gathers the per-tile ``Persisted`` bases, then blends them
        over the full target grid per output time.

        Args:
            target: The full target grid the tiles cover.
            partition: The partition producing overlapping tiles.
            method: The method name for each unit.
            params: The parameter provider (its ``params_key`` stamps each unit's seed).
            split: The split object (its ``id`` is recorded; ``None`` -> "train").
            seed: The run-level seed folded into each tile's derived seed.
            output_times: The output times to solve and blend.
            executor: The scatter-gather port submitting each unit.
            obs_for_tile: Optional callable windowing the obs over a tile (None -> no obs).
            k: The halo multiple recorded in blend provenance.

        Returns:
            A list of ``BlendedDistribution``, one per output time, over ``target``.
        """
        products = self.gather(
            target,
            partition,
            method,
            params,
            split,
            seed,
            output_times,
            executor,
            obs_for_tile=obs_for_tile,
        )
        return self.blend_grid(
            products,
            target,
            output_times,
            k=k,
            method=method,
            params_key=params.params_key(),
        )

    def gather(
        self,
        target: GridSpec,
        partition: TilePartition,
        method: str,
        params: ParameterProvider,
        split: object,
        seed: int,
        output_times: Sequence[float],
        executor: Executor,
        *,
        obs_for_tile: Callable[[Tile], ObsWindow] | None = None,
        eval_for_tile: Callable[[Tile], np.ndarray | None] | None = None,
        derived_names: Sequence[str] | None = None,
    ) -> list[tuple[Tile, Product]]:
        """Emit one ``UnitOfWork`` per tile and gather the per-tile ``Product``s.

        Args:
            target: The full target grid.
            partition: The partition producing overlapping tiles.
            method: The method name for each unit.
            params: The parameter provider.
            split: The split object (its ``id`` is recorded; ``None`` -> "train").
            seed: The run-level seed folded into each tile's derived seed.
            output_times: The output times to solve.
            executor: The scatter-gather port.
            obs_for_tile: Optional callable windowing the obs over a tile.
            eval_for_tile: Optional callable returning a tile's eval locations (or None).
            derived_names: Optional derived-quantity names requested on each unit.

        Returns:
            A list of ``(tile, product)`` pairs, one per tile (one submit each).
        """
        tiles = list(partition.tiles(target))
        products: list[tuple[Tile, Product]] = []
        for n, tile in enumerate(tiles):
            wid = f"tile{n}"
            uow = UnitOfWork(
                window_id=wid,
                method_name=method,
                params=params,
                split_id=getattr(split, "id", "train"),
                seed=derive_seed(method, params.params_key(), f"{wid}:{seed}", 0),
                output_times=list(output_times),
                obs=(obs_for_tile(tile) if obs_for_tile is not None else None),
                grid=tile.grid,
                eval_locations=(
                    eval_for_tile(tile) if eval_for_tile is not None else None
                ),
                derived_names=list(derived_names) if derived_names else [],
            )
            products.append((tile, executor.submit(uow)))
        return products

    def blend_grid(
        self,
        products: list[tuple[Tile, Product]],
        target: GridSpec,
        output_times: Sequence[float],
        *,
        k: float = 3.0,
        method: str = "oi",
        params_key: str = "",
    ) -> list[BlendedDistribution]:
        """Blend the gathered per-tile bases over the target grid, one per output time.

        Args:
            products: The ``(tile, product)`` pairs from :meth:`gather`.
            target: The full target grid to blend onto.
            output_times: The output times (indexes the per-time series).
            k: The halo multiple recorded in blend provenance.
            method: The method identity for the driving-noise spec.
            params_key: The resolved-parameter identity for the driving-noise spec.

        Returns:
            One ``BlendedDistribution`` per output time over ``target``.
        """
        blended_by_time: list[BlendedDistribution] = []
        for ti, _t in enumerate(output_times):
            parts = [
                BlendInput(prod.per_time[ti].base, tile) for tile, prod in products
            ]
            blended_by_time.append(
                self.blend_op.blend(
                    parts, support=target, k=k, method=method, params_key=params_key
                )
            )
        return blended_by_time
