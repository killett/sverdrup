"""Sparse Cholesky + Takahashi selective inverse vs the dense Q^-1 oracle."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("sksparse")  # noqa: E402

from sverdrup.core.grid import GridSpec  # noqa: E402
from sverdrup.methods.gmrf_grid import matern_precision  # noqa: E402
from sverdrup.methods.gmrf_linalg import GMRFFactor  # noqa: E402


def _q(nside=6):
    g = GridSpec.lonlat(np.arange(nside, dtype=float), np.arange(nside, dtype=float))
    return g, matern_precision(g, kappa=0.4, tau=1.0)


def test_permutation_is_deterministic():
    # Behavior: the fill-reducing permutation is reproducible across factorizations.
    # Bug caught: a nondeterministic ordering breaks reproducibility-from-provenance.
    _, q = _q()
    assert np.array_equal(GMRFFactor(q).permutation, GMRFFactor(q).permutation)


def test_solve_matches_dense():
    # Behavior: factor.solve(b) == Q^-1 b.
    # Bug caught: mishandling the permutation in the solve path.
    _, q = _q()
    b = np.arange(q.shape[0], dtype=float)
    np.testing.assert_allclose(
        GMRFFactor(q).solve(b), np.linalg.solve(q.toarray(), b), rtol=1e-9
    )


def test_takahashi_diag_matches_dense_inverse():
    # Behavior: selective inverse diagonal == diag(Q^-1) exactly (EXACT marginal variance).
    # Bug caught: ANY error in the Takahashi recursion -> calibration silently dishonest.
    #   A red here is a math bug to fix, never a tolerance to loosen.
    _, q = _q()
    diag = GMRFFactor(q).selective_inverse_diag()
    np.testing.assert_allclose(diag, np.diag(np.linalg.inv(q.toarray())), rtol=1e-9)


def test_takahashi_adjacent_entries_match_dense():
    # Behavior: selective inverse entries between 5-point-adjacent nodes == dense Q^-1.
    # Bug caught: W (4-node) eval var and firstdifference adjacent-cov read wrong entries.
    g, q = _q()
    fac = GMRFFactor(q)
    sinv = fac.selective_inverse()  # sparse, on the L+L^T pattern
    dense = np.linalg.inv(q.toarray())
    nx = g.shape[1]
    pairs = [(0, 1), (0, nx), (7, 8), (7, 7 + nx)]
    for a, b in pairs:
        assert sinv[a, b] == pytest.approx(dense[a, b], rel=1e-9)


def test_sample_is_zero_mean_with_right_covariance():
    # Behavior: L^-T w draws have covariance ~ Q^-1 (checked on the diagonal).
    # Bug caught: sampling with L instead of L^-T inverts the covariance scale.
    _, q = _q()
    fac = GMRFFactor(q)
    rng = np.random.default_rng(0)
    draws = np.stack([fac.sample(rng.standard_normal(q.shape[0])) for _ in range(4000)])
    emp = draws.var(axis=0)
    np.testing.assert_allclose(emp, np.diag(np.linalg.inv(q.toarray())), rtol=0.15)


def test_posterior_cov_columns_match_dense_full_columns():
    # Behavior: posterior_cov_columns(S) == the FULL columns (Q^-1)[:, S], not the
    #   selective-inverse pattern. These off-pattern entries are what kriging conditions on.
    # Bug caught: returning the Takahashi/selective-inverse block (sparse, pattern-only) would
    #   zero out the long-range cross-cov entries the kriging correction needs -> wrong joint law.
    _, q = _q()
    fac = GMRFFactor(q)
    shared = np.array([2, 5, 11])
    cols = fac.posterior_cov_columns(shared)
    dense = np.linalg.inv(q.toarray())
    assert cols.shape == (q.shape[0], shared.size)
    np.testing.assert_allclose(cols, dense[:, shared], rtol=1e-9)


def test_posterior_cov_columns_off_pattern_entries_are_nonzero():
    # Behavior: the returned columns carry genuine long-range entries OUTSIDE the L+L^T pattern.
    # Bug caught: a selective-inverse-based shortcut that silently drops off-pattern coupling
    #   (the exact defect that made the marginal-only checks pass on the broken sampler).
    g, q = _q()
    fac = GMRFFactor(q)
    far = np.array(
        [0]
    )  # corner node; row 0 vs the opposite corner is off the sparse pattern
    cols = fac.posterior_cov_columns(far)
    opposite = q.shape[0] - 1
    sinv = fac.selective_inverse()
    assert sinv[opposite, 0] == 0.0  # off the selective-inverse pattern
    assert abs(cols[opposite, 0]) > 0.0  # but present in the true full column


def test_adjacency_precondition_holds_for_alpha2():
    # Behavior: every 5-point-adjacent pair lies inside the selective-inverse pattern.
    # Bug caught: a future wider kappa-stencil would silently break eval var / cancellation.
    from sverdrup.methods.gmrf_linalg import assert_adjacency_in_pattern

    g, q = _q()
    assert_adjacency_in_pattern(q, g.shape)  # must not raise
