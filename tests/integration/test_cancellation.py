import numpy as np

from sverdrup.core.grid import GridSpec
from sverdrup.core.provenance import UncertaintyProvenance
from sverdrup.core.types import UncertaintyCapability
from sverdrup.derived.firstdifference import FirstDifference
from sverdrup.distributions.ensemble import EnsemblePredictiveDistribution
from sverdrup.distributions.gaussian import GaussianPredictiveDistribution
from tests.unit._doubles import ToyExpOperator


def test_exact_path_beats_sample_path_on_difference_variance():
    # Bug caught: sample-derived covariance for a cancellation-sensitive linear functional.
    grid = GridSpec.lonlat(np.linspace(0, 0.4, 5), np.linspace(40, 40.4, 5))
    op = ToyExpOperator(
        sigma2=1.0, length=5.0
    )  # long correlation -> near-equal neighbours
    prov = UncertaintyProvenance(
        native_capability=UncertaintyCapability.SAMPLES, transformations=[]
    )
    gauss = GaussianPredictiveDistribution(
        grid, np.zeros((5, 5)), op, prov, time_days=0.0
    )

    exact = FirstDifference(axis="x").apply(gauss).marginal_variance()

    m = 400
    samples = gauss.sample(m, seed=0)
    ens = EnsemblePredictiveDistribution(grid, samples, prov, time_days=0.0)
    sample_based = FirstDifference(axis="x").apply(ens).marginal_variance()

    # closed-form reference using the operator directly
    pts = grid.points(0.0).reshape(5, 5, 3)
    ref = np.zeros((5, 4))
    for i in range(5):
        for j in range(4):
            a = pts[i, j][None, :]
            b = pts[i, j + 1][None, :]
            ref[i, j] = op.cov(a, a)[0, 0] + op.cov(b, b)[0, 0] - 2 * op.cov(a, b)[0, 0]
    scale = (np.cos(np.deg2rad(40)) * 111195.0 * 0.1) ** 2  # (metres per node step)^2
    ref = ref / scale

    err_exact = np.abs(exact - ref).mean()
    err_sample = np.abs(sample_based - ref).mean()
    assert err_exact < err_sample
