"""Tests for the 2017 single-tile OI run driver."""

import numpy as np
import xarray as xr

from sverdrup.validation.run import run_year


def test_run_year_produces_daily_maps(
    tmp_path, mapping_fixture_obs, baseline_provider, small_grid
):
    """run_year emits one schema-valid map per output day from windowed obs.

    Catches a broken temporal-window assembly (empty maps / wrong day count) and
    a non-schema output their eval would reject.
    """
    dest = tmp_path / "ours.nc"
    out = run_year(
        mapping_obs=mapping_fixture_obs,
        params=baseline_provider,
        grid=small_grid,
        temporal_half_window_days=10.0,
        output_days=[0.0, 1.0, 2.0],
        dest=dest,
    )
    ds = xr.open_dataset(out)
    assert ds.sizes["time"] == 3
    assert ds["ssh"].dims == ("time", "lat", "lon")
    assert ds.sizes["lat"] == np.unique(small_grid._lonlat_nodes()[1]).size
    assert np.isfinite(ds["ssh"].values).any()


def test_run_year_time_axis_matches_output_days(
    tmp_path, mapping_fixture_obs, baseline_provider, small_grid
):
    """The written time axis equals the requested output days (epoch 2017-01-01).

    Catches an off-by-epoch / wrong-day-stamp bug that would misalign every map
    with the eval's per-day matching.
    """
    dest = tmp_path / "ours.nc"
    out = run_year(
        mapping_obs=mapping_fixture_obs,
        params=baseline_provider,
        grid=small_grid,
        temporal_half_window_days=10.0,
        output_days=[0.0, 5.0],
        dest=dest,
    )
    days = xr.open_dataset(out)["time"].values.astype("datetime64[D]")
    assert list(days) == [np.datetime64("2017-01-01"), np.datetime64("2017-01-06")]


def test_run_year_window_excludes_distant_obs(
    tmp_path, mapping_fixture_obs, baseline_provider, small_grid
):
    """A near-zero window starves the solve, giving a near-prior (near-zero) map.

    Catches a windowing bug that ignores temporal_half_window_days and always
    uses all obs (the wide-window map must differ from the starved one).
    """
    common = dict(
        mapping_obs=mapping_fixture_obs,
        params=baseline_provider,
        grid=small_grid,
        output_days=[0.0],
    )
    starved = xr.open_dataset(
        run_year(temporal_half_window_days=0.01, dest=tmp_path / "s.nc", **common)
    )["ssh"].values
    fed = xr.open_dataset(
        run_year(temporal_half_window_days=14.0, dest=tmp_path / "f.nc", **common)
    )["ssh"].values
    assert np.nanmax(np.abs(fed)) > np.nanmax(np.abs(starved))


def test_run_year_adds_mdt_grid(
    tmp_path, mapping_fixture_obs, baseline_provider, small_grid
):
    """A constant MDT grid offsets every map by that constant (SLA -> SSH).

    Catches a reference-frame bug where MDT is dropped (the exact defect that
    collapsed the first full-year run's mu).
    """
    lon, lat = small_grid._lonlat_nodes()
    ny, nx = np.unique(lat).size, np.unique(lon).size
    offset = np.full((ny, nx), 0.5)
    common = dict(
        mapping_obs=mapping_fixture_obs,
        params=baseline_provider,
        grid=small_grid,
        temporal_half_window_days=10.0,
        output_days=[0.0],
    )
    base = xr.open_dataset(run_year(dest=tmp_path / "b.nc", **common))["ssh"].values
    shifted = xr.open_dataset(
        run_year(dest=tmp_path / "s.nc", mdt_grid=offset, **common)
    )["ssh"].values
    assert np.allclose(shifted - base, 0.5, atol=1e-9)
