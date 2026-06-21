from sverdrup.core.derived import Route, select_route
from sverdrup.core.types import CovFidelity, Linearity


def test_linear_exact_uses_exact_covariance_path():
    # Bug caught: routing a cancellation-sensitive linear functional through samples.
    assert select_route(Linearity.LINEAR, CovFidelity.EXACT) == Route(
        "covariance", CovFidelity.EXACT
    )


def test_linear_lowrank_stamps_fidelity():
    assert select_route(Linearity.LINEAR, CovFidelity.LOW_RANK) == Route(
        "covariance", CovFidelity.LOW_RANK
    )
    assert select_route(Linearity.LINEAR, CovFidelity.SAMPLE) == Route(
        "covariance", CovFidelity.SAMPLE
    )


def test_nonlinear_uses_sample_path():
    assert select_route(Linearity.NONLINEAR, CovFidelity.EXACT) == Route(
        "sample", CovFidelity.EXACT
    )
