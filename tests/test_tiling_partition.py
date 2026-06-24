"""Scale-aware halos + lon/lat partition with co-registered overlap nodes."""

from __future__ import annotations

import numpy as np

from sverdrup.application.tiling import LonLatPartition, ScaleAwareHalo
from sverdrup.core.geometry import Window
from sverdrup.core.grid import GridSpec
from sverdrup.core.parameters import LatitudeVaryingProvider


def _target():
    return GridSpec.lonlat(np.arange(-30.0, 30.01, 1.0), np.arange(-10.0, 60.01, 1.0))


def test_halo_is_km_and_widest_at_equator():
    # Behavior: halo_km = max(k*corr_len(lat), stencil); equator wider than high-lat.
    # Bug caught: a single global halo or a degree pad (invariant 5).
    target = _target()
    prov = LatitudeVaryingProvider(800.0, 100.0, {})
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
    prov = LatitudeVaryingProvider(800.0, 100.0, {})
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
    prov = LatitudeVaryingProvider(800.0, 100.0, {})
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
