from dataclasses import replace

import numpy as np
import pytest

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


# --- captured-energy diagnostic (hygiene P2 #14) ------------------------------
# Design (phase-1 spec): "a captured-energy diagnostic (fraction of trace(P)
# captured by BB^T) so LOW_RANK quality is monitorable per product". The
# marginal variance is always exact through the residual, so a constant 1.0
# would make the diagnostic unmonitorable — every expected value below is
# that fraction, computed by hand.


def test_captured_energy_fraction_hand_values():
    # Bug caught: a missing clip, the wrong normaliser, or a zero / NaN total
    #   dividing instead of reporting nothing captured.
    from sverdrup.distributions.persisted import captured_energy_fraction

    f = np.array([[3.0], [4.0]])  # sum of squares 25
    assert captured_energy_fraction(f, 50.0) == 0.5
    assert captured_energy_fraction(f, 25.0) == 1.0
    assert captured_energy_fraction(f, 20.0) == 1.0  # randomized overshoot clips
    assert captured_energy_fraction(f, 0.0) == 0.0
    assert captured_energy_fraction(f, float("nan")) == 0.0
    assert captured_energy_fraction(np.zeros((2, 0)), 7.0) == 0.0


def test_points_fields_report_the_factor_share():
    # Bug caught: PersistedPoints.fields claiming captured_energy=1.0 while half
    #   the trace sits in the residual.
    from sverdrup.core.grid import PointSet
    from sverdrup.distributions.persisted import PersistedPoints

    pp = PersistedPoints(
        PointSet(np.zeros((3, 3)), _grid().crs),
        mean=np.zeros(3),
        factor=np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]),  # energy 4
        residual=np.array([1.0, 1.0, 2.0]),  # energy 4
        provenance=_prov(),
        time_days=0.0,
    )
    assert pp.fields.captured_energy == 0.5


def _rank1_plus_identity(n_side: int) -> PersistedDistribution:
    """Cov = b b^T + I with b = ones: trace 2n, top eigenvalue n + 1."""
    from sverdrup.distributions.persisted import PersistedFields

    n = n_side * n_side
    fields = PersistedFields(
        mean=np.zeros((n_side, n_side)),
        marginal_variance=np.full((n_side, n_side), 2.0),
        factor=np.ones((n, 1)),
        residual=np.ones(n),
        rank=1,
        seed=3,
        captured_energy=0.5,
    )
    return PersistedDistribution(_grid(n_side), fields, _prov(), time_days=0.0)


def test_regrid_reports_rank_truncation():
    # Behavior: a rank-1 regrid of b b^T + I (n = 25) keeps the top component
    #   only; by hand its population share of trace is (n + 1) / 2n = 26/50 =
    #   0.52, and the reported value is the factor share of the RETURNED
    #   representation's own trace.
    # Bug caught: regrid hard-coding captured_energy=1.0 for a truncated factor.
    out = _rank1_plus_identity(5).regrid(_grid(5)).fields
    assert out.rank == 1
    share = float(np.sum(out.factor**2) / np.sum(out.marginal_variance))
    assert out.captured_energy == pytest.approx(share, rel=1e-12)
    assert 0.4 < out.captured_energy < 0.7


def test_regrid_at_full_rank_captures_everything():
    # Boundary: n = 4 nodes and rank >= 4 — the factor carries the whole
    #   ensemble trace, residual ~0, so the honest share is 1 (not under-reported).
    src = _rank1_plus_identity(2)
    full = PersistedDistribution(
        src.grid,
        replace(src.fields, factor=np.eye(4), residual=np.ones(4), rank=4),
        src.provenance,
        time_days=0.0,
    )
    out = full.regrid(_grid(2)).fields
    assert out.rank == 4
    assert out.captured_energy == pytest.approx(1.0, abs=1e-9)


def test_reduce_derived_rank0_captures_nothing():
    # Bug caught: solve._reduce_derived claiming captured_energy=1.0 for an
    #   EMPTY factor (rank 0: every unit of variance is in the residual).
    from types import SimpleNamespace
    from typing import Any, cast

    from sverdrup.application.solve import _reduce_derived

    var = np.full((2, 3), 0.5)
    op = SimpleNamespace(
        apply=lambda dist: SimpleNamespace(marginal_variance=lambda: var)
    )
    uow = SimpleNamespace(seed=5, grid=GridSpec.lonlat(np.arange(4.0), np.arange(2.0)))
    dist = SimpleNamespace(provenance=_prov(), time_days=0.0)
    # _reduce_derived reads only .seed and .grid off the unit of work
    out = _reduce_derived(op, dist, cast(Any, uow)).fields
    assert out.rank == 0
    assert out.captured_energy == 0.0
