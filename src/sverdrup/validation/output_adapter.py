"""Our gridded OI map -> NetCDF in the challenge map schema (read_l4_dataset).

Schema captured from the shipped maps (e.g. ``OSE_ssh_mapping_DUACS.nc``), which
their eval ingests via ``src.mod_inout.read_l4_dataset`` (needs variable ``ssh``
on coords ``lon``/``lat``/``time``):

- dims order ``(time, lat, lon)``; coords ``lat``/``lon`` (float64,
  degrees_north/east), ``time`` (int ``days since 2017-01-01``, proleptic
  gregorian); data var ``ssh`` (float64, no units, matching the shipped maps).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import xarray as xr

SSH_VAR = "ssh"
TIME_UNITS = "days since 2017-01-01 00:00:00"
TIME_CALENDAR = "proleptic_gregorian"


def write_map(
    times: np.ndarray,
    lats: np.ndarray,
    lons: np.ndarray,
    ssh: np.ndarray,
    dest: Path,
) -> Path:
    """Write a (time, lat, lon) SSH map to ``dest`` in the challenge schema.

    Args:
        times: 1-D ``datetime64`` time coordinate.
        lats: 1-D latitude coordinate (degrees north).
        lons: 1-D longitude coordinate (degrees east).
        ssh: ``(time, lat, lon)`` SSH field.
        dest: Output NetCDF path.

    Returns:
        ``dest``.
    """
    ds = xr.Dataset(
        {SSH_VAR: (("time", "lat", "lon"), np.asarray(ssh, dtype=np.float64))},
        coords={
            "lat": ("lat", np.asarray(lats, dtype=np.float64)),
            "lon": ("lon", np.asarray(lons, dtype=np.float64)),
            "time": ("time", np.asarray(times, dtype="datetime64[ns]")),
        },
    )
    ds["lat"].attrs.update(long_name="Latitudes", units="degrees_north")
    ds["lon"].attrs.update(long_name="Longitudes", units="degrees_east")
    encoding = {
        "time": {
            "units": TIME_UNITS,
            "calendar": TIME_CALENDAR,
            "dtype": "int32",
        },
        SSH_VAR: {"dtype": "float64"},
    }
    dest.parent.mkdir(parents=True, exist_ok=True)
    ds.to_netcdf(dest, encoding=encoding)
    return dest
