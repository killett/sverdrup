"""Helpers binding the oracle test to the cached NATL60 window (only used when data present)."""

from __future__ import annotations

import os

from regatta.adapters.executor_dask import ExecutorConfig
from regatta.adapters.odc.natl60 import Natl60Source
from regatta.application.pipeline import PipelineInputs


def cached_natl60_source() -> Natl60Source:
    """Build a Natl60Source from the cached data pointed to by REGATTA_ODC_DATA."""
    root = os.environ["REGATTA_ODC_DATA"]
    return Natl60Source(f"{root}/natl60_obs.nc", f"{root}/natl60_ref_daily.nc")


def full_window_config(src: Natl60Source) -> PipelineInputs:
    """Return the full 42-day NATL60 window pipeline config for the oracle run."""
    return PipelineInputs(
        mode="OSSE",
        method_name="oi",
        source=src,
        out_url="file:///tmp/regatta_oracle.zarr",
        lon_range=(-65, -55),
        lat_range=(33, 43),
        time_range=(0, 42),
        output_times=[20.0],
        params={"length_scale": 150.0, "time_scale": 7.0, "variance": 0.05},
        grid_resolution_deg=0.25,
        executor=ExecutorConfig(n_processes=8, threads_per_process=4),
        rank=80,
    )
