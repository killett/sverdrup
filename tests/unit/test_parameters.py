import numpy as np

from regatta.core.grid import GridSpec
from regatta.core.parameters import ConstantProvider, ParameterSpace


def test_constant_provider_resolves_scalar():
    grid = GridSpec.lonlat(np.array([0.0, 1.0]), np.array([0.0, 1.0]))
    p = ConstantProvider({"length_scale": 100.0, "time_scale": 10.0, "variance": 0.05})
    assert p.resolve("length_scale", grid) == 100.0


def test_params_key_is_stable_and_order_independent():
    # Bug caught: unstable key → seed/provenance churn across runs.
    a = ConstantProvider({"length_scale": 100.0, "variance": 0.05}).params_key()
    b = ConstantProvider({"variance": 0.05, "length_scale": 100.0}).params_key()
    assert a == b


def test_parameter_space_declares_bounds():
    space = ParameterSpace({"length_scale": (10.0, 500.0)})
    assert space.bounds["length_scale"] == (10.0, 500.0)
