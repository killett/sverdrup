"""Area-weighted aggregation with true spherical cell_area (invariant 11)."""

from __future__ import annotations

import numpy as np

from sverdrup.core.grid import GridSpec
from sverdrup.eval.aggregate import area_weighted_mean, area_weighted_rmse


def test_area_weighting_differs_from_unweighted():
    # Behavior: high-lat cells weigh less (cos lat) -> weighted != unweighted.
    # Bug caught: an unweighted global mean over-counts shrunken polar cells.
    grid = GridSpec.lonlat(np.array([0.0, 1.0, 2.0]), np.array([0.0, 30.0, 60.0]))
    # big values at high lat
    field = np.array([[1.0, 1.0, 1.0], [2.0, 2.0, 2.0], [9.0, 9.0, 9.0]])
    w = area_weighted_mean(field, grid)
    assert abs(w - field.mean()) > 1e-3
    area = grid.cell_area()
    np.testing.assert_allclose(w, (area * field).sum() / area.sum(), rtol=1e-12)


def test_area_weighted_rmse():
    # Behavior: RMS uses area weights too.
    # Bug caught: mixing weighted mean with unweighted error stats.
    grid = GridSpec.lonlat(np.array([0.0, 1.0]), np.array([0.0, 60.0]))
    err = np.array([[1.0, 1.0], [3.0, 3.0]])
    area = grid.cell_area()
    expect = np.sqrt((area * err**2).sum() / area.sum())
    np.testing.assert_allclose(area_weighted_rmse(err, grid), expect, rtol=1e-12)


def test_area_weighted_mean_below_unweighted_when_low_lat_smaller():
    # Behavior: weighting pulls the mean toward the (larger) equatorward cells.
    # Bug caught: weights applied with the wrong (pole-heavy) orientation.
    grid = GridSpec.lonlat(np.array([0.0, 1.0]), np.array([0.0, 70.0]))
    field = np.array([[1.0, 1.0], [9.0, 9.0]])  # small at equator, big at high lat
    assert area_weighted_mean(field, grid) < field.mean()
