import numpy as np
import pytest

from regatta.core.grid import GridSpec

R_EARTH = 6_371_000.0


def make_lonlat(lon0=-65.0, lon1=-55.0, lat0=33.0, lat1=43.0, n=11):
    lons = np.linspace(lon0, lon1, n)
    lats = np.linspace(lat0, lat1, n)
    return GridSpec.lonlat(lons, lats)


def test_cell_area_shrinks_poleward():
    # Bug caught: a flat (dx*dy) area assumption — invariant 1. Higher-lat cells must be smaller.
    grid = GridSpec.lonlat(np.array([0.0, 1.0]), np.array([10.0, 60.0]))
    area = grid.cell_area()
    assert area[1, 0] < area[0, 0]  # lat=60 row smaller than lat=10 row
    assert np.all(area > 0)


def test_global_cell_area_sums_to_sphere():
    # Bug caught: wrong metric constant — global sum must match sphere area within 1%.
    lons = np.linspace(-179.0, 179.0, 180)
    lats = np.linspace(-89.0, 89.0, 90)
    grid = GridSpec.lonlat(lons, lats)
    total = grid.cell_area().sum()
    assert total == pytest.approx(4 * np.pi * R_EARTH**2, rel=0.02)


def test_points_carry_time():
    grid = make_lonlat(n=4)
    pts = grid.points(time_days=12.5)
    assert pts.shape == (16, 3)
    assert np.allclose(pts[:, 2], 12.5)


def test_polar_stereographic_instantiates():
    # Bug caught: projection handled by branching instead of by the type.
    grid = GridSpec.polar_stereographic(
        x=np.linspace(-1e6, 1e6, 5), y=np.linspace(-1e6, 1e6, 5), lat_ts=70.0, lon0=0.0
    )
    area = grid.cell_area()
    assert area.shape == (5, 5)
    assert np.all(area > 0)


def test_window_is_strict_subset_same_type():
    grid = make_lonlat(n=11)
    win = grid.window(lon_range=(-62.0, -58.0), lat_range=(36.0, 40.0))
    assert isinstance(win, GridSpec)
    assert win.shape[0] * win.shape[1] < grid.shape[0] * grid.shape[1]
    assert win.crs == grid.crs
