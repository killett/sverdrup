import numpy as np

from regatta.application.solve import solve_unit
from regatta.application.uow import UnitOfWork
from regatta.core.grid import GridSpec
from regatta.core.observations import DiagonalErrorModel, ObsWindow
from regatta.core.parameters import ConstantProvider
from regatta.distributions.persisted import PersistedDistribution


def _inputs():
    grid = GridSpec.lonlat(np.linspace(0, 2, 4), np.linspace(40, 42, 4))
    obs = ObsWindow.from_arrays(
        np.array([0.5, 1.5]),
        np.array([40.5, 41.5]),
        np.zeros(2),
        np.array([0.1, -0.2]),
        DiagonalErrorModel(np.full(2, 0.01)),
    )
    eval_locs = np.array([[0.7, 40.7, 0.0], [1.2, 41.2, 0.0]])
    return grid, obs, eval_locs


def test_solve_unit_returns_persisted_bundle_with_exact_eval_points():
    grid, obs, eval_locs = _inputs()
    params = ConstantProvider(
        {"length_scale": 200.0, "time_scale": 10.0, "variance": 1.0}
    )
    uow = UnitOfWork(
        window_id="tile0",
        method_name="oi",
        params=params,
        split_id="train",
        seed=123,
        output_times=[0.0],
        obs=obs,
        grid=grid,
        eval_locations=eval_locs,
        derived_names=["firstdifference"],
    )
    product = solve_unit(uow)
    assert product.times() == [0.0]
    pt = product.per_time[0]
    assert isinstance(pt.base, PersistedDistribution)
    assert "firstdifference" in pt.derived

    # eval-point predictive must be the EXACT operator query, not grid interpolation.
    from regatta.methods.kernel import Matern32SpaceTime
    from regatta.methods.oi import GPCovarianceOperator

    kern = Matern32SpaceTime(1.0, 200.0, 10.0)
    op = GPCovarianceOperator(kern, obs.coords(), obs.values(), np.full(2, 0.01))
    assert pt.eval_points is not None
    assert np.allclose(pt.eval_points.mean, op.posterior_mean(eval_locs), atol=1e-8)
    assert np.allclose(pt.eval_points.variance, op.marginal_var(eval_locs), atol=1e-8)


def test_no_dense_obs_matrix_escapes():
    grid, obs, eval_locs = _inputs()
    params = ConstantProvider(
        {"length_scale": 200.0, "time_scale": 10.0, "variance": 1.0}
    )
    uow = UnitOfWork(
        "tile0",
        "oi",
        params,
        "train",
        1,
        [0.0],
        obs,
        grid,
        eval_locs,
        ["firstdifference"],
    )
    pt = solve_unit(uow).per_time[0]
    # Persisted factor is (ngrid, r), never (nobs, nobs)
    assert pt.base.fields.factor.shape[0] == grid.shape[0] * grid.shape[1]
