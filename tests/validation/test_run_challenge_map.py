"""run_challenge_map is method-agnostic; OI path matches the legacy run_year."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import xarray as xr

from sverdrup.core.grid import GridSpec
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
from sverdrup.core.parameters import ConstantProvider
from sverdrup.validation.run import run_challenge_map, run_year


def _tiny_obs() -> ObsWindow:
    rng = np.random.default_rng(0)
    n = 60
    lon = 300.0 + rng.random(n)
    lat = 38.0 + rng.random(n)
    t = rng.uniform(-2, 2, n)
    val = rng.standard_normal(n) * 0.1
    return ObsWindow.from_arrays(lon, lat, t, val, DiagonalErrorModel(np.full(n, 0.01)))


def _grid() -> GridSpec:
    return GridSpec.lonlat(np.arange(300.0, 301.01, 0.5), np.arange(38.0, 39.01, 0.5))


def test_oi_path_matches_run_year(tmp_path: Path) -> None:
    # Bug it catches: the generalized runner drifting from the validated OI path.
    obs, grid = _tiny_obs(), _grid()
    p = ConstantProvider({"length_scale": 100.0, "time_scale": 7.0, "variance": 1.0})
    a = run_year(obs, p, grid, 14.0, [0.0], tmp_path / "a.nc")
    b = run_challenge_map("oi", obs, p, grid, 14.0, [0.0], tmp_path / "b.nc")
    assert np.allclose(xr.open_dataset(a).ssh.values, xr.open_dataset(b).ssh.values)


def test_gmrf_path_writes_valid_map(tmp_path: Path) -> None:
    # Bug it catches: a non-OI method that can't drive the per-day challenge runner.
    obs, grid = _tiny_obs(), _grid()
    p = ConstantProvider({"range": 100.0, "variance": 1.0, "temporal_taper_scale": 7.0})
    out = run_challenge_map("gmrf", obs, p, grid, 14.0, [0.0], tmp_path / "g.nc")
    ds = xr.open_dataset(out)
    assert "ssh" in ds and ds.ssh.shape[0] == 1
