import os

import numpy as np
import pytest

from regatta.adapters.executor_dask import ExecutorConfig
from regatta.adapters.odc.fixtures import FixtureSource
from regatta.application.pipeline import PipelineInputs, _grid, run_pipeline

ODC_OI_BASELINE_RMSE = (
    0.0907  # recorded NATL60 2020a OI leaderboard RMSE (metres); see runbook
)
_NO_DATA = os.environ.get("REGATTA_ODC_DATA") is None


def test_fixture_smoke_rmse_finite_and_sane(tmp_path):
    # Bug caught: a pipeline that 'runs' but produces a degenerate/incorrect map.
    src = FixtureSource(
        "tests/fixtures/natl60_tiny.nc", ref_path="tests/fixtures/natl60_ref_tiny.nc"
    )
    inp = PipelineInputs(
        mode="OSSE",
        method_name="oi",
        source=src,
        out_url=f"file://{tmp_path}/s.zarr",
        lon_range=(-64, -56),
        lat_range=(34, 42),
        time_range=(0, 5),
        output_times=[2.0],
        params={"length_scale": 300.0, "time_scale": 10.0, "variance": 0.05},
        grid_resolution_deg=1.0,
        executor=ExecutorConfig(2, 1),
        rank=20,
    )
    _, scores = run_pipeline(inp)
    assert np.isfinite(scores["rmse"])
    # Loose sanity: OI must not do much worse than a trivial all-zero prediction.
    truth = src.truth(2.0, _grid(inp))
    assert truth is not None
    zero_rmse = float(np.sqrt(np.mean(truth**2)))
    assert scores["rmse"] <= 1.25 * zero_rmse


@pytest.mark.oracle
@pytest.mark.skipif(
    _NO_DATA,
    reason="set REGATTA_ODC_DATA to the cached NATL60 window to run the oracle",
)
def test_oi_matches_odc_baseline_within_10pct():
    from tests.oracle.conftest import cached_natl60_source, full_window_config

    src = cached_natl60_source()
    _, scores = run_pipeline(full_window_config(src))
    assert scores["rmse"] <= 1.10 * ODC_OI_BASELINE_RMSE
