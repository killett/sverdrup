from sverdrup.adapters.executor_dask import ExecutorConfig
from sverdrup.adapters.odc.fixtures import FixtureSource
from sverdrup.application.pipeline import PipelineInputs, run_pipeline
from sverdrup.core.evaluation import ContextKey
from sverdrup.eval.calibration import assert_relaxes_to_prior


def _grid_cfg():
    return dict(
        lon_range=(-64, -56),
        lat_range=(34, 42),
        grid_resolution_deg=1.0,
        time_range=(0, 5),
        output_times=[2.0],
        params={"length_scale": 300.0, "time_scale": 10.0, "variance": 0.05},
        executor=ExecutorConfig(n_processes=2, threads_per_process=1),
        rank=20,
    )


def test_osse_slice_produces_truth_rmse_and_calibration(tmp_path):
    src = FixtureSource(
        "tests/fixtures/natl60_tiny.nc", ref_path="tests/fixtures/natl60_ref_tiny.nc"
    )
    inp = PipelineInputs(
        mode="OSSE",
        method_name="oi",
        source=src,
        out_url=f"file://{tmp_path}/osse.zarr",
        **_grid_cfg(),
    )
    product, scores = run_pipeline(inp)
    assert product.times() == [2.0]
    assert "rmse" in scores and "reduced_chi2" in scores and "coverage_1sigma" in scores


def test_ose_slice_uses_withheld_cryosat_not_truth(tmp_path):
    src = FixtureSource("tests/fixtures/ose_tiny.nc")  # mission c2 present -> withheld
    inp = PipelineInputs(
        mode="OSE",
        method_name="oi",
        source=src,
        out_url=f"file://{tmp_path}/ose.zarr",
        **_grid_cfg(),
    )
    product, scores = run_pipeline(inp)
    # truth-based evaluator did not fire on a grid truth; rmse is vs withheld obs.
    assert "rmse" in scores
    assert scores["context_keys"] == {
        ContextKey.WITHHELD_OBS.name,
        ContextKey.ORBIT_GEOMETRY.name,
    }


def test_polar_void_assertion_in_slice():
    # The calibration void check is expressible even on the non-polar tile.
    assert assert_relaxes_to_prior(0.9, 1.0) is True
    assert assert_relaxes_to_prior(0.02, 1.0) is False
