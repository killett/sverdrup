"""Tests for the output adapter (challenge map NetCDF schema, field-for-field)."""

import numpy as np
import xarray as xr

from sverdrup.validation.output_adapter import write_map


def test_output_matches_challenge_map_schema(tmp_path, map_schema_ref):
    """Our NetCDF matches the challenge map schema field-for-field.

    Catches a silent number-shifter: wrong dim order, coord names, SSH var name,
    coord units, or time encoding that their eval (read_l4_dataset) would
    misread or reject.
    """
    ref = xr.open_dataset(map_schema_ref, decode_times=False)
    dest = tmp_path / "ours.nc"
    write_map(
        times=np.array(["2017-01-01"], dtype="datetime64[ns]"),
        lats=ref["lat"].values,
        lons=ref["lon"].values,
        ssh=np.zeros((1, ref.sizes["lat"], ref.sizes["lon"])),
        dest=dest,
    )
    ours = xr.open_dataset(dest, decode_times=False)

    # Dataset.dims is alphabetically sorted; the real dim ORDER lives on ssh.dims.
    assert list(ours.dims) == list(ref.dims)
    assert list(ours.coords) == list(ref.coords)
    assert "ssh" in ours.data_vars
    assert ours["ssh"].dims == ref["ssh"].dims == ("time", "lat", "lon")
    assert ours["ssh"].dtype == np.float64
    assert ours["lat"].attrs.get("units") == "degrees_north"
    assert ours["lon"].attrs.get("units") == "degrees_east"
    assert ours["time"].attrs.get("units", "").startswith("days since 2017-01-01")
    assert ours["time"].attrs.get("calendar") == "proleptic_gregorian"


def test_output_time_decodes_to_the_written_dates(tmp_path):
    """The encoded time axis round-trips to the dates we passed in.

    Catches a time-epoch/encoding bug that would shift every map in time and
    silently wreck the eval's day-matching.
    """
    dest = tmp_path / "ours.nc"
    days = np.array(["2017-01-01", "2017-01-02", "2017-07-15"], dtype="datetime64[ns]")
    write_map(
        times=days,
        lats=np.array([33.0, 33.2]),
        lons=np.array([295.0, 295.2]),
        ssh=np.zeros((3, 2, 2)),
        dest=dest,
    )
    decoded = xr.open_dataset(dest)["time"].values.astype("datetime64[D]")
    assert list(decoded) == list(days.astype("datetime64[D]"))
