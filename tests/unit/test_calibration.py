import numpy as np

from sverdrup.eval.calibration import (
    assert_relaxes_to_prior,
    coverage,
    crps_gaussian,
    reduced_chi2,
)


def test_reduced_chi2_and_coverage_well_specified():
    # Bug caught: mis-scaled variance (UQ not honest).
    rng = np.random.default_rng(0)
    truth = rng.normal(size=20000)
    mean = np.zeros(20000)
    var = np.ones(20000)
    assert abs(reduced_chi2(mean, var, truth) - 1.0) < 0.15
    assert abs(coverage(mean, var, truth, k=1.0) - 0.6827) < 0.05


def test_crps_matches_closed_form():
    # Closed form CRPS(N(0,1), y) = z(2Phi(z)-1)+2phi(z)-1/sqrt(pi); at y=0.5 -> 0.331404.
    # (At y=0 it is 0.233695 — the plan's 0.23379 constant was the y=0 value.)
    val = crps_gaussian(np.array([0.0]), np.array([1.0]), np.array([0.5]))[0]
    assert abs(val - 0.331404) < 1e-4


def test_polar_void_assertion():
    # Bug caught: small reported error in a data void (broken UQ).
    prior = 1.0
    assert assert_relaxes_to_prior(var_in_void=0.95, prior_var=prior) is True
    assert assert_relaxes_to_prior(var_in_void=0.05, prior_var=prior) is False
