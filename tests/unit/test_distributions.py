import numpy as np

from sverdrup.core.grid import GridSpec
from sverdrup.core.provenance import UncertaintyProvenance
from sverdrup.core.types import UncertaintyCapability
from sverdrup.distributions.ensemble import EnsemblePredictiveDistribution
from sverdrup.distributions.gaussian import GaussianPredictiveDistribution
from tests.unit._doubles import ToyExpOperator


def _grid():
    return GridSpec.lonlat(np.linspace(0, 3, 4), np.linspace(0, 3, 4))


def _prov(cap):
    return UncertaintyProvenance(native_capability=cap, transformations=[])


def test_gaussian_sample_centered_on_mean():
    grid = _grid()
    mean = np.arange(16.0).reshape(4, 4)
    d = GaussianPredictiveDistribution(
        grid,
        mean,
        ToyExpOperator(),
        _prov(UncertaintyCapability.SAMPLES),
        time_days=0.0,
    )
    s = d.sample(2000, seed=1)
    assert np.allclose(s.mean(axis=0), mean, atol=0.15)


def test_gaussian_marginal_variance_from_operator():
    grid = _grid()
    d = GaussianPredictiveDistribution(
        grid,
        np.zeros((4, 4)),
        ToyExpOperator(sigma2=0.7),
        _prov(UncertaintyCapability.SAMPLES),
        time_days=0.0,
    )
    assert np.allclose(d.marginal_variance(), 0.7)


def test_ensemble_recovers_operator_covariance():
    # Bug caught: ensemble covariance that does not converge to the truth (sanity for SAMPLE path).
    grid = _grid()
    op = ToyExpOperator()
    pts = grid.points(0.0)
    truth = op.cov(pts, pts)
    base = np.zeros((4, 4))
    samples = base.ravel()[None, :] + op.posterior_sample(pts, seed=3, m=6000)
    ens = EnsemblePredictiveDistribution(
        grid,
        samples.reshape(-1, 4, 4),
        _prov(UncertaintyCapability.SAMPLES),
        time_days=0.0,
    )
    est = ens.covariance(pts, pts)
    assert np.allclose(est, truth, atol=0.08)


def test_regrid_evaluates_operator_on_target():
    grid = _grid()
    op = ToyExpOperator(sigma2=0.5)
    d = GaussianPredictiveDistribution(
        grid, np.zeros((4, 4)), op, _prov(UncertaintyCapability.SAMPLES), time_days=0.0
    )
    target = GridSpec.lonlat(np.linspace(0, 3, 7), np.linspace(0, 3, 7))
    rg = d.regrid(target)
    assert rg.marginal_variance().shape == (7, 7)
    assert np.allclose(rg.marginal_variance(), 0.5)
