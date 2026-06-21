import numpy as np

from sverdrup.core.grid import GridSpec
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
from sverdrup.core.provenance import KnownBias, TransformKind
from sverdrup.core.types import UncertaintyCapability
from sverdrup.distributions.adapters import diagonal_gaussian, perturb_and_ensemble


def _obs(n=6):
    return ObsWindow.from_arrays(
        np.linspace(0, 3, n),
        np.linspace(0, 3, n),
        np.zeros(n),
        np.arange(n, dtype=float),
        DiagonalErrorModel(np.full(n, 0.04)),
    )


def test_perturb_ensemble_flags_synthesized_bias():
    # Bug caught: presenting POINT-derived spread as native (invariant 8).
    grid = GridSpec.lonlat(np.linspace(0, 3, 4), np.linspace(0, 3, 4))

    def point_fn(obs, grid, time_days):
        return np.full(grid.shape, obs.values().mean())

    dist = perturb_and_ensemble(point_fn, _obs(), grid, m=40, seed=5, time_days=0.0)
    prov = dist.provenance
    assert prov.native_capability is UncertaintyCapability.POINT
    assert prov.is_synthesized is True
    assert prov.transformations[0].kind is TransformKind.INPUT_PERTURBATION
    assert prov.transformations[0].known_bias is KnownBias.UNDER_DISPERSED_IN_VOIDS


def test_perturb_ensemble_reproducible():
    grid = GridSpec.lonlat(np.linspace(0, 3, 4), np.linspace(0, 3, 4))

    def point_fn(obs, grid, time_days):
        return np.full(grid.shape, obs.values().mean())

    a = perturb_and_ensemble(
        point_fn, _obs(), grid, m=20, seed=9, time_days=0.0
    ).samples
    b = perturb_and_ensemble(
        point_fn, _obs(), grid, m=20, seed=9, time_days=0.0
    ).samples
    assert np.array_equal(a, b)
    assert a.var() > 0  # perturbations actually applied


def test_diagonal_gaussian_marks_inflation():
    grid = GridSpec.lonlat(np.linspace(0, 3, 4), np.linspace(0, 3, 4))
    dist = diagonal_gaussian(
        np.zeros((4, 4)), np.full((4, 4), 0.2), grid, time_days=0.0
    )
    assert np.allclose(dist.marginal_variance(), 0.2)
    assert dist.provenance.transformations[0].kind is TransformKind.DIAGONAL_INFLATION
