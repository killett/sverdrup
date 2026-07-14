"""Scale-aware halos + lon/lat partition with co-registered overlap nodes.

Provider note (Phase-10 Task 2): ``LatitudeVaryingProvider`` was superseded
in place (named-form fields, box-hull-clamped — spec §2), so it can no longer
supply the global cos(lat) correlation-length profile these tests exercise
the halo machinery with. ``_CosLatProvider`` below is a local test stub with
the retired profile: these tests verify ``ScaleAwareHalo``/``LonLatPartition``
behavior against ANY lat-varying provider (invariant 5), not the provider
class itself.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sverdrup.application.tiling import LonLatPartition, ScaleAwareHalo
from sverdrup.core.geometry import Window
from sverdrup.core.grid import GridSpec


@dataclass(frozen=True)
class _CosLatProvider:
    """Test stub: correlation_length as a cos(lat) blend (equator wide, pole narrow)."""

    equator_km: float
    pole_km: float

    def resolve(self, name: str, grid: GridSpec) -> np.ndarray:
        """Resolve ``correlation_length`` as a field over ``grid``'s latitudes."""
        assert name == "correlation_length"
        _, lat = grid._lonlat_nodes()
        c = np.cos(np.deg2rad(lat))  # 1 at equator -> 0 at pole
        return np.asarray(self.pole_km + (self.equator_km - self.pole_km) * c)

    def params_key(self) -> str:
        """Return a canonical key for the stub profile."""
        return f"cos-test(eq={self.equator_km!r},pole={self.pole_km!r})"


def _target():
    return GridSpec.lonlat(np.arange(-30.0, 30.01, 1.0), np.arange(-10.0, 60.01, 1.0))


def test_halo_is_km_and_widest_at_equator():
    # Behavior: halo_km = max(k*corr_len(lat), stencil); equator wider than high-lat.
    # Bug caught: a single global halo or a degree pad (invariant 5).
    target = _target()
    prov = _CosLatProvider(800.0, 100.0)
    pol = ScaleAwareHalo(k=2.0)
    eq = pol.halo_for(
        Window((-5, 5), (-5, 5), (0, 21)), target, prov, stencil_radius_km=10.0
    )
    hi = pol.halo_for(
        Window((-5, 5), (50, 60), (0, 21)), target, prov, stencil_radius_km=10.0
    )
    assert eq.radius_km > hi.radius_km
    assert eq.radius_km == 2.0 * 800.0  # k * equator corr length dominates the stencil


def test_partition_cores_tile_target_with_overlaps_and_shared_nodes():
    # Behavior: cores cover the target; extended windows overlap; tile grids are windows of target.
    # Bug caught: non-shared overlap nodes would force Persisted.regrid inside Stage A.
    target = _target()
    prov = _CosLatProvider(800.0, 100.0)
    tiles = LonLatPartition(
        n_lon=3,
        n_lat=2,
        halo=ScaleAwareHalo(k=0.5),
        correlation_length=prov,
        stencil_radius_km=10.0,
    ).tiles(target)
    assert len(tiles) == 6
    for t in tiles:
        # extended contains core
        assert t.extended_window.lon_range[0] <= t.core_window.lon_range[0]
        assert t.extended_window.lon_range[1] >= t.core_window.lon_range[1]
        # tile grid nodes are a subset of the target nodes (co-registration)
        assert np.all(np.isin(t.grid.x, target.x))
        assert np.all(np.isin(t.grid.y, target.y))


def test_equatorial_tiles_get_wider_halos_than_high_lat():
    # Behavior: the partition is non-uniform — equatorward tiles have wider extended windows.
    # Bug caught: a uniform halo ignores the latitude-varying correlation length.
    target = _target()
    prov = _CosLatProvider(800.0, 100.0)
    tiles = LonLatPartition(
        n_lon=1,
        n_lat=2,
        halo=ScaleAwareHalo(k=0.5),
        correlation_length=prov,
        stencil_radius_km=10.0,
    ).tiles(target)
    # n_lat=2 over lat [-10, 60] -> a lower (equatorward) band and an upper band
    by_low = min(tiles, key=lambda t: abs(t.core_window.lat_range[0]))
    by_high = max(tiles, key=lambda t: abs(t.core_window.lat_range[0]))
    low_pad = by_low.extended_window.lat_range[1] - by_low.core_window.lat_range[1]
    high_pad = by_high.extended_window.lat_range[1] - by_high.core_window.lat_range[1]
    assert low_pad > high_pad
