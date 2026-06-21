"""Generate tiny NetCDF fixtures for offline CI (run once; outputs committed)."""

from __future__ import annotations

import numpy as np
import xarray as xr

rng = np.random.default_rng(0)


def _obs_fixture(path: str, missions: list[str]) -> None:
    """Write a tiny along-track observation fixture to ``path``."""
    n = 40
    ds = xr.Dataset(
        {
            "sla": ("t", rng.normal(0, 0.1, n)),
            "longitude": ("t", rng.uniform(-65, -55, n)),
            "latitude": ("t", rng.uniform(33, 43, n)),
            "time": ("t", np.linspace(0, 5, n)),
            "mission": ("t", rng.choice(missions, n)),
        }
    )
    ds.to_netcdf(path)


def _ref_fixture(path: str) -> None:
    """Write a tiny gridded daily reference fixture to ``path``."""
    lon = np.linspace(-65, -55, 12)
    lat = np.linspace(33, 43, 12)
    t = np.arange(0, 6.0)
    ssh = rng.normal(0, 0.1, (t.size, lat.size, lon.size))
    xr.Dataset(
        {"ssh": (("time", "latitude", "longitude"), ssh)},
        coords={"time": t, "latitude": lat, "longitude": lon},
    ).to_netcdf(path)


if __name__ == "__main__":
    _obs_fixture("tests/fixtures/natl60_tiny.nc", ["s6", "j3", "alg"])
    _ref_fixture("tests/fixtures/natl60_ref_tiny.nc")
    _obs_fixture("tests/fixtures/ose_tiny.nc", ["s6", "j3", "c2"])
