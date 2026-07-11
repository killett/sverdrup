"""Tests for Phase-8 fold machinery + pool-then-max lexicographic selection.

Covers spec plan-obligation 1 (T/S folds, guard rings), plan-obligation 2
(rho_hat / n_eff, small-block merge), and the pooled-worst-region + lane-0
eligible lexicographic selection.

Every test names the concrete bug it would catch.
"""

from __future__ import annotations

import numpy as np
import pytest

import sverdrup.application.calibration.folds as folds
from sverdrup.application.calibration.constants import (
    COVERAGE_TARGET,
    MIN_N_EFF,
    S_FOLD_COUNT,
    T_FOLDS,
)

# ---------------------------------------------------------------------------
# T-folds
# ---------------------------------------------------------------------------


def test_t_folds_yields_six_rotations_each_verifies_its_pair() -> None:
    """t_folds yields exactly the 6 pinned rotations; each rotation's verify
    mask is precisely the two T_FOLDS months, and the fit mask is the
    complement.

    Bug caught: fold order scrambled, verify/fit swapped, or a rotation
    holding out the wrong month pair.
    """
    # One point per month, in month order.
    months = np.array([f"{m:02d}" for m in range(1, 13)])
    rotations = list(folds.t_folds(months))

    assert len(rotations) == len(T_FOLDS) == 6

    for (fit_mask, verify_mask), pair in zip(rotations, T_FOLDS, strict=True):
        want_verify = np.isin(months, np.array(pair))
        np.testing.assert_array_equal(verify_mask, want_verify)
        np.testing.assert_array_equal(fit_mask, ~want_verify)
        # verify holds exactly the two months of this pair
        assert set(months[verify_mask]) == set(pair)


def test_t_folds_rotation_coverage_each_month_verified_once() -> None:
    """Across the 6 T-folds every month is held out in exactly one rotation.

    Bug caught: a month never verified, or verified in two rotations (broken
    rotation coverage).
    """
    months = np.array([f"{m:02d}" for m in range(1, 13)])
    verified_count = np.zeros(len(months), dtype=int)
    for _fit, verify in folds.t_folds(months):
        verified_count += verify.astype(int)
    np.testing.assert_array_equal(verified_count, np.ones(len(months), dtype=int))


# ---------------------------------------------------------------------------
# S-fold layout
# ---------------------------------------------------------------------------


def test_s_fold_layout_sizes_partition_disjoint() -> None:
    """s_fold_layout returns 4 frozensets of block ids with sizes (7,6,6,6),
    union = all 25 blocks, pairwise disjoint.

    Bug caught: wrong split sizes, dropped/duplicated blocks, off-by-one on
    the 25-block universe.
    """
    layout = folds.s_fold_layout(salt=0)
    assert len(layout) == S_FOLD_COUNT == 4
    assert all(isinstance(f, frozenset) for f in layout)

    sizes = sorted(len(f) for f in layout)
    assert sizes == [6, 6, 6, 7]

    union: set[int] = set()
    for f in layout:
        assert union.isdisjoint(f)
        union |= f
    assert union == set(range(25))


def test_s_fold_layout_deterministic_by_salt() -> None:
    """Same salt reproduces the layout exactly; salt+1 gives a different
    layout (seeded permutation, not order-dependent).

    Bug caught: unseeded RNG, salt not threaded into the seed, or the seed
    args mis-ordered so salt has no effect.
    """
    a = folds.s_fold_layout(salt=0)
    b = folds.s_fold_layout(salt=0)
    c = folds.s_fold_layout(salt=1)
    assert a == b
    assert a != c


# ---------------------------------------------------------------------------
# S-folds: guard ring
# ---------------------------------------------------------------------------


def _single_block_layout(held_block: int) -> tuple[frozenset[int], ...]:
    """Layout with one fold == {held_block}, rest lumped into fold 1."""
    others = frozenset(set(range(25)) - {held_block})
    return (frozenset({held_block}), others)


def test_s_folds_guard_ring_excludes_from_both_masks() -> None:
    """A point within GUARD_RING_DEG of the held-out block's boundary is in
    NEITHER fit nor score; deep-inside-held-out is score only; well inside a
    fit block and clear of the ring is fit only.

    Bug caught: guard ring not applied, applied to only one side, or leaking
    ring points into a mask.
    """
    # Held-out block 12 = row 2, col 2: lon [299,301], lat [37,39].
    held = 12
    layout = _single_block_layout(held)

    lon = np.array(
        [
            300.0,  # deep inside held block -> score
            299.4,  # inside held but within 0.5 of left edge (299) -> ring
            296.0,  # far fit block (col 0), clear of ring -> fit
            301.4,  # in neighbouring fit block but within 0.5 of edge 301 -> ring
        ]
    )
    lat = np.array(
        [
            38.0,  # deep inside
            38.0,
            34.0,  # far fit
            38.0,
        ]
    )
    labels = np.array(["A", "A", "A", "A"])  # unused here

    fit_mask, score_mask = folds.s_folds(lon, lat, labels, layout)[0]

    # index 0: deep inside held -> score only
    assert score_mask[0] and not fit_mask[0]
    # index 1: within ring of held edge -> neither
    assert not score_mask[1] and not fit_mask[1]
    # index 2: far fit block, clear of ring -> fit only
    assert fit_mask[2] and not score_mask[2]
    # index 3: within ring on the fit side of the edge -> neither
    assert not score_mask[3] and not fit_mask[3]


def test_s_folds_score_and_fit_are_disjoint() -> None:
    """For every fold the fit and score masks never both select the same
    point.

    Bug caught: a point counted as both training and evaluation (leakage).
    """
    rng = np.random.default_rng(0)
    lon = rng.uniform(295.0, 305.0, 500)
    lat = rng.uniform(33.0, 43.0, 500)
    labels = np.array(["A"] * 500)
    layout = folds.s_fold_layout(salt=0)
    for fit_mask, score_mask in folds.s_folds(lon, lat, labels, layout):
        assert not np.any(fit_mask & score_mask)


# ---------------------------------------------------------------------------
# Partition constraint checker
# ---------------------------------------------------------------------------


def test_layout_respects_partition_true_when_healthy() -> None:
    """A layout that keeps >=50% of every partition label on the fit side of
    every fold returns True.

    Bug caught: checker too strict / inverted so a healthy layout is rejected.
    """
    # Spread points across all blocks, all label 'A' -> each fold holds out
    # at most 7/25 blocks, so >50% stays on fit.
    lon, lat, labels = _grid_points_all_blocks()
    layout = folds.s_fold_layout(salt=0)
    assert folds.layout_respects_partition(lon, lat, labels, layout) is True


def test_layout_respects_partition_false_on_violation() -> None:
    """A partition label whose points all live in one held-out fold (0% on the
    fit side for that fold) returns False.

    Bug caught: checker ignores per-fold accounting or the 50% threshold.
    """
    # Label 'B' lives entirely in block 0. Build a layout whose fold 0 == {0}.
    layout = _single_block_layout(0)
    # Two points in block 0 labelled 'B', rest 'A' spread over other blocks.
    lon = np.array([295.5, 295.6, 300.0, 302.0])
    lat = np.array([33.5, 33.6, 38.0, 40.0])
    labels = np.array(["B", "B", "A", "A"])
    assert folds.layout_respects_partition(lon, lat, labels, layout) is False


# ---------------------------------------------------------------------------
# rho_hat / n_eff
# ---------------------------------------------------------------------------


def test_n_eff_ar1_matches_theory() -> None:
    """For an AR(1) series with rho=0.6, n_eff estimated from rho_hat is
    within 10% of the theoretical n*(1-rho)/(1+rho); the summed lags stop at
    the first rho_k < RHO_CUTOFF and never exceed RHO_MAX_LAG.

    Bug caught: wrong autocorrelation normalisation, sum not truncated, or
    n_eff formula transposed.
    """
    rng = np.random.default_rng(42)
    rho = 0.6
    n = 10_000
    z = np.empty(n)
    z[0] = rng.standard_normal()
    for i in range(1, n):
        z[i] = rho * z[i - 1] + np.sqrt(1 - rho**2) * rng.standard_normal()

    day = np.arange(n)  # native order
    pass_id = np.zeros(n, dtype=int)  # single pass

    rhos, factor = folds.rho_hat(z, day, pass_id)
    assert len(rhos) <= 20  # RHO_MAX_LAG cap
    assert rhos[0] >= 0.05  # first retained lag is above cutoff
    # truncation: all retained lags are above the cutoff
    assert np.all(rhos >= 0.05)

    n_eff_val = folds.n_eff(n, rhos)
    theory = n * (1 - rho) / (1 + rho)
    assert abs(n_eff_val - theory) / theory < 0.10, (
        f"n_eff={n_eff_val}, theory={theory}"
    )
    # factor consistency: n_eff == n / factor
    assert abs(n_eff_val - n / factor) < 1e-9


def test_n_eff_raises_on_nonpositive_factor() -> None:
    """n_eff raises ValueError when 1 + 2*sum(rhos) <= 0 (arbitrary negative
    rhos violate the rho_hat-truncation precondition of factor >= 1).

    Bug caught: silently returning a negative or infinite effective sample
    size instead of rejecting the invalid input.
    """
    with pytest.raises(ValueError, match="factor"):
        folds.n_eff(500, np.array([-0.75]))  # factor == -0.5 (negative)
    with pytest.raises(ValueError, match="factor"):
        folds.n_eff(500, np.array([-0.25, -0.25]))  # factor == 0


def test_n_eff_formula_white_noise_is_n() -> None:
    """White noise (rho ~ 0) yields n_eff ~ n because no lag survives the
    RHO_CUTOFF and the correction sum is empty.

    Bug caught: correction applied even with no retained lags, or empty-array
    sum mis-handled.
    """
    assert folds.n_eff(500, np.array([])) == 500.0
    assert folds.n_eff(500.0, np.array([0.1, 0.05])) == pytest.approx(
        500.0 / (1 + 2 * 0.15)
    )


# ---------------------------------------------------------------------------
# merge_small_blocks
# ---------------------------------------------------------------------------


def test_merge_no_merge_when_all_above_threshold() -> None:
    """When every block's n_eff >= MIN_N_EFF the layout is unchanged and the
    mapping is the identity.

    Bug caught: spurious merges when nothing is under-powered.
    """
    layout = folds.s_fold_layout(salt=0)
    n_eff_per_block = {b: MIN_N_EFF + 1.0 for b in range(25)}
    merged, mapping = folds.merge_small_blocks(layout, n_eff_per_block)
    assert merged == layout
    assert mapping == {b: b for b in range(25)}


def test_merge_tiny_block_to_nearest_same_fold_lowest_index_tiebreak() -> None:
    """A block below MIN_N_EFF merges into the nearest-centroid block of the
    SAME fold; an exact centroid-distance tie resolves to the lowest block
    index.

    Bug caught: merging across folds, choosing the farthest block, or a
    non-deterministic tie-break.
    """
    # Fold with blocks {6, 8, 12}. Block 6 (row1,col1, center 298,36) is tiny.
    # Neighbours in same fold: 8 (row1,col3, center 302,36) dist 4;
    # 12 (row2,col2, center 300,38) dist sqrt(4+4)=2.83 -> nearest is 12.
    fold = frozenset({6, 8, 12})
    other = frozenset(set(range(25)) - {6, 8, 12})
    layout = (fold, other)
    n_eff_per_block = {b: MIN_N_EFF + 10.0 for b in range(25)}
    n_eff_per_block[6] = 10.0  # tiny

    merged, mapping = folds.merge_small_blocks(layout, n_eff_per_block)
    assert mapping[6] == 12
    # The merged layout relabels block 6 to its target 12: block 6 no longer
    # appears as a standalone id, and its fold still carries the target 12.
    fold_with_12 = next(f for f in merged if 12 in f)
    assert 6 not in fold_with_12
    assert 12 in fold_with_12 and 8 in fold_with_12
    # Untouched blocks in the other fold keep their identity.
    assert all(6 not in f for f in merged)

    # Tie-break: block 6 equidistant to 8 and 4 -> pick lowest index.
    # 6 center (298,36); 8 center (302,36) dist 4; 4 (row0,col4, center 304,34)
    # is far. Use symmetric neighbours 2 (302,34?) — construct explicit tie:
    # blocks 5 (row1,col0, center 296,36) dist 2 and 7 (row1,col2, center
    # 300,36) dist 2 are both distance 2 from 6 -> lowest index 5 wins.
    fold2 = frozenset({5, 6, 7})
    other2 = frozenset(set(range(25)) - {5, 6, 7})
    layout2 = (fold2, other2)
    n2 = {b: MIN_N_EFF + 10.0 for b in range(25)}
    n2[6] = 5.0
    _merged2, mapping2 = folds.merge_small_blocks(layout2, n2)
    assert mapping2[6] == 5


# ---------------------------------------------------------------------------
# pooled_worst_region
# ---------------------------------------------------------------------------


def test_pooled_worst_region_hand_case() -> None:
    """Two regions with hand-computed pooled coverages produce the correct
    per-region |coverage - target| and the max over regions.

    Bug caught: pooling across folds wrong, abs deviation dropped, or max/min
    confused.
    """
    # Region R1: 60 covered of 100 -> coverage 0.60, |0.60-0.6827| = 0.0827
    # Region R2: 70 covered of 100 -> coverage 0.70, |0.70-0.6827| = 0.0173
    cov_by_region = {"R1": (60, 100), "R2": (70, 100)}
    worst, table = folds.pooled_worst_region(cov_by_region)

    exp_r1 = abs(0.60 - COVERAGE_TARGET)
    exp_r2 = abs(0.70 - COVERAGE_TARGET)
    assert table["R1"] == pytest.approx(exp_r1)
    assert table["R2"] == pytest.approx(exp_r2)
    assert worst == pytest.approx(max(exp_r1, exp_r2))
    assert worst == pytest.approx(exp_r1)


# ---------------------------------------------------------------------------
# select: eligibility + lexicographic cascade
# ---------------------------------------------------------------------------


def _lane(name: str, s_stat: float, t_stat: float) -> dict[str, object]:
    return {"name": name, "s_stat": s_stat, "t_stat": t_stat}


def test_select_worse_than_lane0_on_primary_returns_none() -> None:
    """A candidate worse than lane-0 on the PRIMARY (S-fold) statistic yields
    a negative result (None winner).

    Bug caught: eligibility gate missing, so a lane that never beats the
    scalar baseline is promoted.
    """
    lane0 = _lane("scalar", s_stat=0.10, t_stat=0.10)
    cand = _lane("poly", s_stat=0.12, t_stat=0.05)  # worse on S
    winner, _table = folds.select([lane0, cand])
    assert winner is None


def test_select_better_primary_but_worse_secondary_beyond_band_returns_none() -> None:
    """A candidate better on PRIMARY but worse than lane-0 on SECONDARY by
    more than TIE_BAND is ineligible -> None.

    Bug caught: secondary no-worse-than-lane0 guard not enforced.
    """
    lane0 = _lane("scalar", s_stat=0.10, t_stat=0.10)
    # better on S (0.08 < 0.10*(1-0.01)) but T 0.20 >> 0.10*(1+0.01)
    cand = _lane("poly", s_stat=0.08, t_stat=0.20)
    winner, _table = folds.select([lane0, cand])
    assert winner is None


def test_select_primary_dominates_secondary_lexicographic() -> None:
    """Lane A wins the T-fold (secondary) statistic, lane B wins the S-fold
    (primary) beyond the band; B is selected because S is primary.

    Bug caught: lexicographic order reversed (T ranked above S).
    """
    lane0 = _lane("scalar", s_stat=0.50, t_stat=0.50)
    a = _lane("poly", s_stat=0.30, t_stat=0.05)  # best T
    b = _lane("covariate", s_stat=0.10, t_stat=0.40)  # best S, beyond band
    winner, _table = folds.select([lane0, a, b])
    assert winner is not None
    assert winner["name"] == "covariate"


def test_select_exact_tie_cascades_to_smooth_preference() -> None:
    """When two eligible lanes tie within TIE_BAND on both S and T, the
    smooth-lane preference order poly > covariate > piecewise breaks the tie.

    Bug caught: tie-break preference order wrong or missing, non-deterministic
    winner on exact ties.
    """
    lane0 = _lane("scalar", s_stat=0.50, t_stat=0.50)
    # Both clearly beat lane0 on S, tie each other within band on S and T.
    piece = _lane("piecewise", s_stat=0.10, t_stat=0.10)
    poly = _lane("poly", s_stat=0.10, t_stat=0.10)
    cov = _lane("covariate", s_stat=0.10, t_stat=0.10)
    winner, _table = folds.select([lane0, piece, cov, poly])
    assert winner is not None
    assert winner["name"] == "poly"


def test_select_single_eligible_candidate_wins() -> None:
    """A lone lane that beats lane-0 on primary beyond band and is no worse on
    secondary is selected.

    Bug caught: eligible lane rejected when it is the only candidate.
    """
    lane0 = _lane("scalar", s_stat=0.50, t_stat=0.50)
    cand = _lane("poly", s_stat=0.10, t_stat=0.10)
    winner, _table = folds.select([lane0, cand])
    assert winner is not None
    assert winner["name"] == "poly"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _grid_points_all_blocks() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """One point at the centre of each of the 25 blocks, all label 'A'."""
    lons = []
    lats = []
    for row in range(5):
        for col in range(5):
            lons.append(296.0 + col * 2.0)  # cell centre lon
            lats.append(34.0 + row * 2.0)  # cell centre lat
    lon = np.array(lons)
    lat = np.array(lats)
    labels = np.array(["A"] * len(lon))
    return lon, lat, labels
