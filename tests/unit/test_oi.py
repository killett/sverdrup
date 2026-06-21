import numpy as np

from regatta.core.grid import GridSpec
from regatta.core.observations import DiagonalErrorModel, ObsWindow
from regatta.core.parameters import ConstantProvider
from regatta.core.types import CovFidelity, UncertaintyCapability
from regatta.methods.kernel import Matern32SpaceTime
from regatta.methods.oi import GPCovarianceOperator, OptimalInterpolation


def _closed_form(kern, op_pts, obs_pts, y, noise):
    kdd = kern.evaluate(obs_pts, obs_pts) + noise * np.eye(len(obs_pts))
    kgd = kern.evaluate(op_pts, obs_pts)
    kgg = kern.evaluate(op_pts, op_pts)
    inv = np.linalg.inv(kdd)
    return kgd @ inv @ y, kgg - kgd @ inv @ kgd.T


def test_gp_matches_closed_form_1d():
    # Bug caught: a sign/solve error in K_AB - V_A^T V_B.
    kern = Matern32SpaceTime(variance=1.0, length_scale=200.0, time_scale=10.0)
    obs_pts = np.array([[0, 0, 0], [0, 1, 0], [0, 2, 0]], float)
    y = np.array([0.2, -0.1, 0.3])
    op_pts = np.array([[0, 0.5, 0], [0, 1.5, 0]], float)
    noise = 0.01
    op = GPCovarianceOperator(kern, obs_pts, y, noise_diag=np.full(3, noise))
    mu_cf, cov_cf = _closed_form(kern, op_pts, obs_pts, y, noise)
    assert np.allclose(op.posterior_mean(op_pts), mu_cf, atol=1e-8)
    assert np.allclose(op.cov(op_pts, op_pts), cov_cf, atol=1e-8)


def test_variance_relaxes_to_prior_in_void():
    # Bug caught: broken UQ that reports small error where there is no data.
    kern = Matern32SpaceTime(variance=1.0, length_scale=50.0, time_scale=5.0)
    obs_pts = np.array([[0, 0, 0]], float)
    op = GPCovarianceOperator(
        kern, obs_pts, np.array([0.0]), noise_diag=np.full(1, 0.01)
    )
    near = op.marginal_var(np.array([[0, 0.01, 0]], float))[0]
    far = op.marginal_var(np.array([[0, 50.0, 0]], float))[0]
    assert near < 0.2
    assert far > 0.9  # relaxes toward prior variance 1.0


def test_solve_returns_native_gaussian():
    kern_params = ConstantProvider(
        {"length_scale": 200.0, "time_scale": 10.0, "variance": 1.0}
    )
    grid = GridSpec.lonlat(np.linspace(0, 2, 3), np.linspace(0, 2, 3))
    obs = ObsWindow.from_arrays(
        np.array([0.0, 1.0]),
        np.array([0.5, 1.5]),
        np.zeros(2),
        np.array([0.1, -0.2]),
        DiagonalErrorModel(np.full(2, 0.01)),
    )
    method = OptimalInterpolation()
    dist = method.solve(obs, grid, kern_params, time_days=0.0)
    assert method.native_capability is UncertaintyCapability.SAMPLES
    assert dist.cov_op.fidelity is CovFidelity.EXACT
    assert dist.provenance.is_synthesized is False
