import numpy as np

from regatta.core.grid import GridSpec
from regatta.core.observations import DiagonalErrorModel, ObsWindow
from regatta.core.types import UncertaintyCapability
from regatta.distributions.adapters import perturb_and_ensemble
from regatta.methods.trivial import TrivialInterpolation


def _obs():
    return ObsWindow.from_arrays(
        np.array([0.0, 3.0]),
        np.array([0.0, 3.0]),
        np.zeros(2),
        np.array([5.0, -5.0]),
        DiagonalErrorModel(np.full(2, 0.01)),
    )


def test_capability_is_point():
    assert TrivialInterpolation().native_capability is UncertaintyCapability.POINT


def test_estimate_follows_nearest_obs():
    # Bug caught: interpolation ignoring observation locations.
    grid = GridSpec.lonlat(np.linspace(0, 3, 4), np.linspace(0, 3, 4))
    field = TrivialInterpolation().point_estimate(_obs(), grid, time_days=0.0)
    assert field.shape == (4, 4)
    assert field[0, 0] > field[-1, -1]  # near (0,0)=+5 vs near (3,3)=-5


def test_lifted_is_synthesized():
    grid = GridSpec.lonlat(np.linspace(0, 3, 4), np.linspace(0, 3, 4))
    m = TrivialInterpolation()
    dist = perturb_and_ensemble(
        m.point_estimate, _obs(), grid, m=20, seed=1, time_days=0.0
    )
    assert dist.provenance.is_synthesized is True
