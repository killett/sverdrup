"""Tests for the baseline_oi parameter extraction."""

import numpy as np
import pytest

from sverdrup.core.grid import GridSpec
from sverdrup.validation.params import (
    GRID_RES_DEG,
    OBS_NOISE_VARIANCE,
    baseline_config,
)


def test_baseline_config_resolves_oi_params_and_box():
    """The extracted config resolves all OI params and covers the OI grid box.

    Catches a mis-wired parameter name (OI reads variance/length_scale/time_scale)
    or a grid that does not cover the real baseline_oi box lon 295-305 / lat 33-43
    (e.g. the 285-315/23-53 data-extraction box mistake). The notebook's
    ``arange(lo, hi+step, step)`` overshoots the upper edge by up to one cell, so
    the max bound allows one extra step.
    """
    provider, grid, temporal_half_window_days = baseline_config()
    assert isinstance(grid, GridSpec)
    for name in ("variance", "length_scale", "time_scale"):
        assert isinstance(float(provider.resolve(name, grid)), float)
    lon, lat = grid._lonlat_nodes()
    assert lon.min() == pytest.approx(295.0)
    assert lat.min() == pytest.approx(33.0)
    assert 305.0 - 1e-6 <= lon.max() <= 305.0 + GRID_RES_DEG + 1e-6
    assert 43.0 - 1e-6 <= lat.max() <= 43.0 + GRID_RES_DEG + 1e-6
    assert temporal_half_window_days > 0


def test_baseline_config_exact_scalars():
    """The transcribed scalars match baseline_oi.ipynb cell 7 exactly.

    Catches a silent mis-transcription of variance / time_scale / noise / window
    that would change the OI behaviour without any error.
    """
    provider, grid, half_window = baseline_config()
    assert float(provider.resolve("variance", grid)) == 1.0  # signal variance
    assert float(provider.resolve("time_scale", grid)) == 7.0  # Lt days
    assert half_window == 14.0  # 2 * Lt obs influence window
    assert OBS_NOISE_VARIANCE == pytest.approx(0.0025)  # noise (0.05) squared


def test_baseline_grid_resolution_is_quarter_fifth_degree():
    """The grid step is 0.2 deg (dx=dy), per cell 7.

    Catches a wrong grid resolution that would change the map size + the score.
    """
    _provider, grid, _half = baseline_config()
    lon, lat = grid._lonlat_nodes()
    assert np.isclose(np.diff(np.unique(lon)).mean(), 0.2)
    assert np.isclose(np.diff(np.unique(lat)).mean(), 0.2)
