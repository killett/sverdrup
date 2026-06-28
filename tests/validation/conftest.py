"""Shared fixtures for the validation test suite."""

from pathlib import Path

import pytest

from sverdrup.validation.params import baseline_config

_FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def mapping_fixture_paths() -> list[Path]:
    """Paths to the committed mapping-mission L3 subset(s) (no Cryosat-2)."""
    return [_FIXTURES / "l3_alg_subset.nc"]


@pytest.fixture
def cryosat2_fixture_path() -> Path:
    """Path to the committed Cryosat-2 (withheld) L3 subset."""
    return _FIXTURES / "l3_c2_subset.nc"


@pytest.fixture
def baseline_provider():
    """The baseline_oi parameter provider."""
    provider, _grid, _half = baseline_config()
    return provider


@pytest.fixture
def baseline_grid():
    """The baseline_oi output grid."""
    _provider, grid, _half = baseline_config()
    return grid


@pytest.fixture
def map_schema_ref() -> Path:
    """Path to the tiny real challenge-map schema reference (DUACS subset)."""
    return _FIXTURES / "map_schema_ref.nc"


@pytest.fixture
def mapping_fixture_obs(mapping_fixture_paths, baseline_provider):
    """An ObsWindow loaded from the committed mapping fixture(s)."""
    from sverdrup.validation.input_adapter import load_mapping_obs

    return load_mapping_obs(mapping_fixture_paths, baseline_provider)


@pytest.fixture
def small_grid():
    """A small GridSpec covering the fixture region (300-303 / 36-39 at 0.2 deg)."""
    import numpy as np

    from sverdrup.core.grid import GridSpec

    return GridSpec.lonlat(
        lons=np.arange(300.0, 303.0 + 0.2, 0.2),
        lats=np.arange(36.0, 39.0 + 0.2, 0.2),
    )
