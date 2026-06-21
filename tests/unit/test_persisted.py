import numpy as np

from sverdrup.core.grid import GridSpec
from sverdrup.core.provenance import UncertaintyProvenance
from sverdrup.core.types import UncertaintyCapability
from sverdrup.distributions.persisted import PersistedDistribution, reduce_to_persisted
from tests.unit._doubles import ToyExpOperator


def _grid(n=5):
    return GridSpec.lonlat(np.linspace(0, 4, n), np.linspace(0, 4, n))


def _prov():
    return UncertaintyProvenance(
        native_capability=UncertaintyCapability.SAMPLES, transformations=[]
    )


def test_marginal_variance_is_exact():
    # Bug caught: dropping the diagonal residual (marginal variance would be under-stated).
    grid = _grid()
    op = ToyExpOperator(sigma2=0.9)
    pts = grid.points(0.0)
    pf = reduce_to_persisted(np.zeros((5, 5)), op, pts, rank=4, seed=2)
    assert np.allclose(pf.marginal_variance.ravel(), op.marginal_var(pts), atol=1e-10)
    assert np.all(pf.residual >= 0.0)


def test_captured_energy_monotone_in_rank():
    grid = _grid(6)
    op = ToyExpOperator()
    pts = grid.points(0.0)
    e_low = reduce_to_persisted(
        np.zeros((6, 6)), op, pts, rank=2, seed=1
    ).captured_energy
    e_high = reduce_to_persisted(
        np.zeros((6, 6)), op, pts, rank=10, seed=1
    ).captured_energy
    assert 0.0 <= e_low <= e_high <= 1.0 + 1e-9


def test_sample_reproducible_and_recovers_variance():
    grid = _grid()
    op = ToyExpOperator(sigma2=0.5)
    pf = reduce_to_persisted(np.zeros((5, 5)), op, grid.points(0.0), rank=12, seed=4)
    dist = PersistedDistribution(grid, pf, _prov(), time_days=0.0)
    s1 = dist.sample(3000, seed=7)
    s2 = dist.sample(3000, seed=7)
    assert np.array_equal(s1, s2)
    assert np.allclose(
        s1.reshape(3000, -1).var(axis=0, ddof=1),
        pf.marginal_variance.ravel(),
        atol=0.08,
    )
