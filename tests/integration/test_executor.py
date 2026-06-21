import numpy as np

from regatta.adapters.executor_dask import DaskExecutor, ExecutorConfig
from regatta.application.solve import solve_unit
from regatta.application.uow import UnitOfWork
from regatta.core.grid import GridSpec
from regatta.core.observations import DiagonalErrorModel, ObsWindow
from regatta.core.parameters import ConstantProvider


def _uow():
    grid = GridSpec.lonlat(np.linspace(0, 2, 4), np.linspace(40, 42, 4))
    obs = ObsWindow.from_arrays(
        np.array([0.5, 1.5]),
        np.array([40.5, 41.5]),
        np.zeros(2),
        np.array([0.1, -0.2]),
        DiagonalErrorModel(np.full(2, 0.01)),
    )
    params = ConstantProvider(
        {"length_scale": 200.0, "time_scale": 10.0, "variance": 1.0}
    )
    return UnitOfWork(
        "tile0", "oi", params, "train", 7, [0.0], obs, grid, None, ["firstdifference"]
    )


def test_blas_env_set_in_worker():
    # Bug caught: thread oversubscription across the 64 cores (no per-worker BLAS cap).
    cfg = ExecutorConfig(n_processes=2, threads_per_process=3)
    with DaskExecutor(cfg) as ex:
        env = ex.worker_env_sample()
        assert env["OMP_NUM_THREADS"] == "3"
        assert env["OPENBLAS_NUM_THREADS"] == "3"
        assert env["MKL_NUM_THREADS"] == "3"


def test_submit_matches_in_process():
    uow = _uow()
    ref = solve_unit(uow)
    cfg = ExecutorConfig(n_processes=2, threads_per_process=1)
    with DaskExecutor(cfg) as ex:
        got = ex.submit(uow)
    assert np.allclose(
        got.per_time[0].base.marginal_variance(),
        ref.per_time[0].base.marginal_variance(),
        atol=1e-10,
    )
