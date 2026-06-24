"""Phase-2 core value objects: math-free geometry the tiling layer populates."""

from __future__ import annotations

import dataclasses

import numpy as np
import pyproj
import pytest

from sverdrup.core.geometry import HaloExtent, Tile, Window
from sverdrup.core.grid import GridSpec, PointSet


def test_window_is_frozen_space_time_box():
    # Behavior: Window is an immutable space-time box.
    # Bug caught: a mutable Window lets orchestration mutate tile geometry mid-run.
    w = Window(lon_range=(-40.0, -30.0), lat_range=(30.0, 40.0), time_range=(0.0, 21.0))
    assert w.lon_range == (-40.0, -30.0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        w.lon_range = (0.0, 1.0)  # type: ignore[misc]


def test_halo_extent_is_km_not_degrees():
    # Behavior: halo distance is projection-neutral km, never a degree pad.
    # Bug caught: storing lon/lat degree pads breaks constant-km halos (a degree of
    # longitude shrinks as cos(lat)) and the projection-mixed partition.
    h = HaloExtent(radius_km=300.0)
    assert h.radius_km == 300.0
    assert not any("deg" in f.name for f in dataclasses.fields(h))


def test_tile_carries_core_extended_windows_and_grid():
    # Behavior: a Tile names its authoritative core, its solve region, and its grid.
    # Bug caught: conflating core and extended window makes every node authoritative,
    # so overlaps are double-counted instead of crossfaded.
    g = GridSpec.lonlat(np.array([-40.0, -39.0]), np.array([30.0, 31.0]))
    core = Window((-40.0, -39.0), (30.0, 31.0), (0.0, 21.0))
    ext = Window((-41.0, -38.0), (29.0, 32.0), (0.0, 21.0))
    t = Tile(core_window=core, extended_window=ext, grid=g)
    assert t.core_window is core and t.extended_window is ext
    assert t.grid.shape == (2, 2)


def test_pointset_holds_points_and_crs():
    # Behavior: PointSet is the unified-support sibling of GridSpec for the blend.
    # Bug caught: a blend that only accepts GridSpec cannot blend withheld eval points.
    pts = np.array([[-35.0, 35.0, 5.0], [-34.0, 36.0, 5.0]])
    ps = PointSet(points=pts, crs=pyproj.CRS.from_epsg(4326))
    assert ps.points().shape == (2, 3)
    assert ps.crs.to_epsg() == 4326
