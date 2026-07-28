"""Member-partition settling measurement (owner pin 43).

Pins ``sverdrup.validation.ensemble_settling``, the harness behind the
settling measurement the owner ordered instead of sealing a two-sample
factor: ~200 DISJOINT random member partitions per tile, replayed from
the persisted member stores (no solves), at two split sizes, giving the
realized null distribution of

    T = RMS(sigma_A - sigma_B) / F_ens ,  F_ens = sigma_pooled/sqrt(size-1)

**NOT VERDICT-BEARING (owner pin 49).** Nothing here licenses a σ verdict
until T17 seals Rule 0.b; this module measures, it does not adjudicate.

All expected values are hand-derived (set algebra for the partitions,
two-point standard deviations for the σ levels), never taken from the
implementation.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from sverdrup.validation.ensemble_settling import (
    disjoint_partitions,
    expected_t,
    member_sigma,
    settling_ratios,
)

# ---- disjoint_partitions -------------------------------------------------


def test_partition_halves_are_disjoint_and_exactly_sized() -> None:
    """Each partition is two DISJOINT equal subsets of the member index set.

    Catches the failure that makes the whole measurement meaningless:
    drawing the two halves independently (or with replacement) so they
    share members, which correlates the two σ estimates and understates
    the null spread the owner asked to measure.
    """
    parts = disjoint_partitions(m_total=100, size=25, n_partitions=50, seed=7)

    assert parts.shape == (50, 2, 25)
    for a, b in parts:
        assert len(set(a.tolist())) == 25
        assert len(set(b.tolist())) == 25
        assert set(a.tolist()).isdisjoint(set(b.tolist()))
        assert set(a.tolist()) | set(b.tolist()) <= set(range(100))


def test_partitions_are_seed_reproducible_and_seed_sensitive() -> None:
    """The draw is a function of the seed alone.

    Catches an unseeded generator — the measured factor is a number the
    owner will seal against later, so a record nobody can reproduce is a
    record nobody can check.
    """
    a = disjoint_partitions(m_total=100, size=50, n_partitions=8, seed=11)
    b = disjoint_partitions(m_total=100, size=50, n_partitions=8, seed=11)
    c = disjoint_partitions(m_total=100, size=50, n_partitions=8, seed=12)

    assert np.array_equal(a, b)
    assert not np.array_equal(a, c)


def test_partitions_are_distinct_and_exhaustion_is_an_error() -> None:
    """No partition repeats, and asking for more than exist is refused.

    With ``m_total=6, size=3`` there are ``C(6,3)/2 = 10`` distinct
    partitions (a split and its mirror are the same partition). Catches
    duplicate draws, which would inflate the apparent sample size of the
    null distribution, and a retry loop that spins forever once the space
    is exhausted.
    """
    parts = disjoint_partitions(m_total=6, size=3, n_partitions=10, seed=3)

    keys = {frozenset((frozenset(a.tolist()), frozenset(b.tolist()))) for a, b in parts}
    assert len(keys) == 10

    with pytest.raises(ValueError, match="distinct"):
        disjoint_partitions(m_total=6, size=3, n_partitions=11, seed=3)


@pytest.mark.parametrize(
    ("m_total", "size", "match"),
    [
        (100, 51, "disjoint"),
        (10, 6, "disjoint"),
        (100, 1, "at least 2"),
        (100, 0, "at least 2"),
    ],
)
def test_partition_size_bounds_are_refused(m_total: int, size: int, match: str) -> None:
    """Sizes that cannot yield two disjoint σ estimates are refused.

    Catches silently overlapping halves when ``2*size > m_total``, and a
    size-1 subset whose ``ddof=1`` standard deviation is undefined —
    either would produce a NaN or a deflated T with no error.
    """
    with pytest.raises(ValueError, match=match):
        disjoint_partitions(m_total=m_total, size=size, n_partitions=2, seed=1)


def test_full_split_covers_every_member() -> None:
    """At ``2*size == m_total`` the two halves exhaust the ensemble.

    Catches a draw restricted to the low index range (e.g. sampling from
    ``range(size*2)`` or reusing the first half), which would measure the
    spread of a sub-ensemble rather than of the recorded 100.
    """
    parts = disjoint_partitions(m_total=100, size=50, n_partitions=4, seed=5)

    for a, b in parts:
        assert set(a.tolist()) | set(b.tolist()) == set(range(100))


# ---- member_sigma --------------------------------------------------------


def test_member_sigma_uses_the_sample_denominator() -> None:
    """σ over the SELECTED members with the ``(m-1)`` denominator.

    Members lie on the LAST axis — the layout the lineage evaluator
    reduces, where the member axis is the fastest-varying one.

    Hand value: the two-member subset ``(0, 2)`` has sample standard
    deviation ``|2-0|/sqrt(2) = sqrt(2)``. Catches ``ddof=0`` (the
    population form), which would return 1.0 and inflate every T by
    ``sqrt(2)`` at this size — and by ``sqrt(m/(m-1))`` in general, the
    exact factor the floor is built from.
    """
    fields = np.array([[0.0, 2.0, 4.0, 6.0]])

    assert member_sigma(fields, [0, 1]) == pytest.approx(math.sqrt(2.0))
    # (0,2,4,6): mean 3, sum sq dev 9+1+1+9 = 20, /3 -> sqrt(20/3).
    assert member_sigma(fields, [0, 1, 2, 3]) == pytest.approx(math.sqrt(20.0 / 3.0))


def test_member_sigma_reduces_the_last_axis_not_the_first() -> None:
    """The member axis is the LAST one, and the node axes survive.

    Catches a reduction over axis 0, which on the production capture is a
    huge-stride accumulation whose summation ORDER differs from the
    evaluator's — the difference that made the capture fail its own
    exact-zero identity check against the persisted map.
    """
    # 3 nodes x 2 members; every node has the same pair, so σ is uniform.
    fields = np.array([[0.0, 2.0], [0.0, 2.0], [0.0, 2.0]])

    sigma = member_sigma(fields, [0, 1])

    assert sigma.shape == (3,)
    assert sigma == pytest.approx([math.sqrt(2.0)] * 3)


def test_member_sigma_refuses_a_single_member() -> None:
    """A one-member subset has no sample σ and must raise, not return NaN.

    Catches a silent NaN that would propagate into the recorded null
    distribution and be read as a missing row rather than a broken one.
    """
    fields = np.array([[0.0, 2.0]])

    with pytest.raises(ValueError, match="at least 2"):
        member_sigma(fields, [0])


def test_member_sigma_propagates_land_nan_per_node() -> None:
    """A non-finite member value makes THAT node non-finite, nothing else.

    Catches ``nanstd``, which would compute σ at a land-adjacent node
    from a different member count than the floor's ``m`` assumes — a
    per-node change in the noise floor that no downstream RMS could see.
    """
    fields = np.array([[1.0, 3.0, 5.0], [0.0, np.nan, 4.0]])

    sigma = member_sigma(fields, [0, 1, 2])

    assert np.isnan(sigma[1])
    assert sigma[0] == pytest.approx(2.0)  # (1,3,5): sum sq dev 8, /2 -> 2


# ---- settling_ratios -----------------------------------------------------


def test_settling_ratio_pools_the_two_sigma_levels_quadratically() -> None:
    """T uses the POOLED (quadratic-mean) σ level of pin 38, not the mean.

    Construction, all hand-derived: two members ``(0, 3*sqrt(2))`` give
    ``sigma_A = 3`` at every node; ``(0, sqrt(2))`` give ``sigma_B = 1``.
    So ``RMS(sigma_A - sigma_B) = 2``, the pooled level is
    ``sqrt((9+1)/2) = sqrt(5)``, ``size = 2`` so ``F_ens = sqrt(5)``, and
    ``T = 2/sqrt(5) = 0.8944271909999159``.

    Catches the superseded ARITHMETIC-mean pooling (level 2, T = 1.0
    exactly), ``sqrt(m)`` in place of ``sqrt(m-1)`` (T = 0.632), and a
    floor built from one field's level alone (T = 0.667 or 2.0).
    """
    root2 = math.sqrt(2.0)
    # 3 nodes x 4 members; members 0,1 give σ=3, members 2,3 give σ=1.
    fields = np.array([[0.0, 3.0 * root2, 0.0, root2]] * 3)
    partitions = np.array([[[0, 1], [2, 3]]])

    ratios = settling_ratios(fields, partitions)

    assert ratios == pytest.approx([2.0 / math.sqrt(5.0)])


def test_settling_ratios_returns_the_whole_distribution() -> None:
    """One T per partition, in partition order — the distribution, not a summary.

    Catches an implementation that aggregates internally (returning a
    mean or a quantile), which would discard exactly what pin 43 ordered
    measured: the spread across partitions.
    """
    rng = np.random.default_rng(4)
    fields = rng.normal(size=(12, 20))  # 12 nodes, 20 members
    partitions = disjoint_partitions(m_total=20, size=5, n_partitions=6, seed=9)

    ratios = settling_ratios(fields, partitions)

    assert ratios.shape == (6,)
    assert np.all(np.isfinite(ratios))
    assert len(np.unique(ratios)) == 6


@pytest.mark.parametrize("bad", [-1, 20])
def test_settling_ratios_refuse_out_of_range_members(bad: int) -> None:
    """Member indices outside ``[0, m)`` are an error, not a wraparound.

    Catches numpy's negative-index semantics silently selecting a member
    from the other end of the ensemble — the two halves would then share
    a member and the partition would no longer be disjoint.
    """
    rng = np.random.default_rng(2)
    fields = rng.normal(size=(4, 20))  # 4 nodes, 20 members
    partitions = np.array([[[0, 1, 2, 3, bad], [10, 11, 12, 13, 14]]])

    with pytest.raises(ValueError, match="member index"):
        settling_ratios(fields, partitions)


# ---- expected_t (owner pin 54) -------------------------------------------

# Published c4 values from the standard control-chart constants table
# (n, c4) — an INDEPENDENT source, not this package's own Gamma call.
PUBLISHED_C4 = {2: 0.7979, 5: 0.9400, 10: 0.9727, 25: 0.9896}


@pytest.mark.parametrize(("m", "c4"), sorted(PUBLISHED_C4.items()))
def test_expected_t_matches_published_c4_constants(m: int, c4: float) -> None:
    """``E[T] = sqrt(2(m-1)(1-c4^2))`` against tabulated ``c4``.

    The ``c4`` values come from the published control-chart constants
    table, so the expected value is derived without touching the
    implementation's own Gamma-ratio evaluation.

    The table carries only 4 decimals, and ``1 - c4^2`` AMPLIFIES that
    rounding by ``c4^2/(1-c4^2)`` — a factor of ~47 at m=25. The
    tolerance is therefore propagated from the table's own +/-5e-5
    precision rather than picked, so the test stays as tight as the
    reference actually is and no tighter.

    Catches an inverted Gamma ratio and an off-by-one in ``m-1`` — either
    would still produce a plausible number just below 1, which is exactly
    the kind of error a sealed threshold would carry silently.
    """
    expected = math.sqrt(2.0 * (m - 1) * (1.0 - c4**2))
    amplification = c4**2 / (1.0 - c4**2)
    tol = amplification * (5e-5 / c4)

    assert expected_t(m) == pytest.approx(expected, rel=tol)


@pytest.mark.parametrize("m", [5, 25, 50])
def test_expected_t_matches_a_direct_simulation_of_the_null(m: int) -> None:
    """The closed form against a simulation that uses no Gamma function.

    Draws iid Gaussian members directly, forms two independent
    ``m``-member sigma estimates per node, and reads the mean of
    ``T = RMS(s_a - s_b)/(sigma/sqrt(m-1))`` off the sample. Nothing in
    this path shares code or algebra with the implementation, so it is a
    genuine independent check of the whole expression — not just of the
    Gamma ratio inside it.

    Catches the same sign/off-by-one errors as the table test, and in
    addition any error in the ``sqrt(2)`` from differencing two
    estimates, which cancels out of a c4-only comparison.
    """
    rng = np.random.default_rng(20260727 + m)
    n_nodes = 200_000
    a = rng.normal(size=(n_nodes, m)).std(axis=1, ddof=1)
    b = rng.normal(size=(n_nodes, m)).std(axis=1, ddof=1)
    floor = 1.0 / math.sqrt(m - 1)  # true sigma is 1 by construction
    simulated = math.sqrt(float(np.mean((a - b) ** 2))) / floor

    # Measured Monte-Carlo scatter of this estimator is ~8e-4 relative at
    # n = 1e6 (four seeds), so ~1.8e-3 at 2e5; 6e-3 is a ~3-sigma band.
    # It still separates the closed form from every bug above: an m-1/m
    # slip moves m=5 by 12%, a missing sqrt(2) by 29%.
    assert expected_t(m) == pytest.approx(simulated, rel=6e-3)


def test_expected_t_approaches_one_strictly_from_below() -> None:
    """The correction is a DEFICIT that shrinks as ``m`` grows.

    Catches a sign error in ``1 - c4^2``: an ``E[T]`` above 1 would bias
    every future attributability threshold in the permissive direction,
    and the drift measured between the two split sizes would have come
    out with the wrong sign.
    """
    values = [expected_t(m) for m in (2, 5, 10, 25, 50, 100, 500)]

    assert all(v < 1.0 for v in values)
    assert values == sorted(values)
    assert values[-1] == pytest.approx(1.0, abs=1e-3)


@pytest.mark.parametrize(
    ("m", "measured_mean"),
    [(25, 0.99397), (50, 0.99755)],
)
def test_expected_t_reproduces_the_measured_settling_means(
    m: int, measured_mean: float
) -> None:
    """Pin 54's standing condition: pinned at the ``m`` ACTUALLY USED.

    These are the pooled means of 400 realized partitions per split size
    from the pin-43 settling measurement
    (``phase14.stage1.ensemble_settling_measurement``), measured on the
    real strip and never seen by this closed form.

    Catches any later change to the form that stops reproducing the
    recorded measurement — the form is going to be SEALED in T17 and
    applied at m values the measurement never ran, so agreement at the
    two m values it did run is the only anchor there is.
    """
    assert expected_t(m) == pytest.approx(measured_mean, abs=1e-3)


def test_expected_t_refuses_a_degenerate_size() -> None:
    """``m < 2`` has no sample σ, so there is no ``T`` to expect.

    Catches a silent NaN or a ZeroDivisionError surfacing later as a
    broken threshold rather than as a refused input.
    """
    with pytest.raises(ValueError, match="at least 2"):
        expected_t(1)
