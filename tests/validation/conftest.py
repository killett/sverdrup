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
