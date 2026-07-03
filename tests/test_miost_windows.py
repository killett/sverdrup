"""Tests for the MIOST WindowPlan + temporal blend (D3/fold A, owner-corrected placement)."""

from __future__ import annotations

import numpy as np
import pytest

from sverdrup.methods.miost_windows import (
    L_T_MAX,
    OBS_END_DAY,
    OBS_START_DAY,
    WindowPlan,
)

PLAN = WindowPlan()  # run-constants from miost_basis


def test_placement_right_aligned_last_window() -> None:
    """8 stride windows s_k = -18+45k plus the right-aligned [322, 382]."""
    starts = [w.start_day for w in PLAN.windows]
    assert starts == [-18.0 + 45.0 * k for k in range(8)] + [322.0]


def test_every_output_day_union_supported_at_lt_ceiling() -> None:
    """Spec 4.1 constraint (i) at L_t_max=12, ALL output days 0..364: the UNION of
    covering windows holds slots [d-12, d+12] entirely (support inside DATA).
    Bug: right-edge window demanding obs beyond the data end (the reviewed
    402-crash) — day 364 needs support to 376, impossible from a [342, 402]
    window whose own obs span assert cannot be satisfied.

    PLAN DEVIATION (spec governs): the plan asked for a SINGLE covering window
    with the full +-12 span, unconditionally — geometrically impossible at
    stride 45 (single-window full-support ranges [s+12, s+48] leave 9-day gaps
    inside every blend zone). Spec constraint (iii) requires the single-window
    form only for FULL-WEIGHT days (tested below)."""
    for d in range(0, 365):
        wins = PLAN.covering(float(d))
        assert 1 <= len(wins) <= 2
        assert min(w.start_day for w in wins) <= d - 12
        assert max(w.end_day for w in wins) >= d + 12


def test_full_weight_days_have_complete_two_sided_support() -> None:
    """Spec 4.1 constraint (iii), UNCONDITIONAL over ALL full-weight output days
    (no first/last-window escape hatch): the single covering window holds
    [d-12, d+12] entirely."""
    checked = 0
    for d in range(0, 365):
        wins = PLAN.covering(float(d))
        if len(wins) == 1:
            (w,) = wins
            assert w.start_day <= d - 12, f"day {d}: left support truncated"
            assert w.end_day >= d + 12, f"day {d}: right support truncated"
            checked += 1
    assert checked > 200  # most days are full-weight; guard against a vacuous loop


def test_blend_zone_truncation_anticorrelated_with_weight() -> None:
    """Spec 4.1 constraint (iii): inside a blend zone each contributor's support
    truncation grows only as its weight falls, hitting weight 0 exactly at its
    boundary (where truncation peaks)."""
    for d_left, d_right in [(27.0, 42.0), (322.0, 357.0)]:  # interior + 35-d pair
        days = np.linspace(d_left, d_right, 31)
        left, right = PLAN.covering(0.5 * (d_left + d_right))
        w_l = np.array([PLAN.weight(left, float(d)) for d in days])
        w_r = np.array([PLAN.weight(right, float(d)) for d in days])
        trunc_l = np.maximum(0.0, days + L_T_MAX - left.end_day)
        trunc_r = np.maximum(0.0, right.start_day - (days - L_T_MAX))
        # weight is 0 exactly where the contributor's truncation is maximal
        assert w_l[-1] == pytest.approx(0.0) and trunc_l[-1] == pytest.approx(L_T_MAX)
        assert w_r[0] == pytest.approx(0.0) and trunc_r[0] == pytest.approx(L_T_MAX)
        # anti-correlation: truncation never grows while weight grows
        assert np.all(np.diff(w_l) <= 0) and np.all(np.diff(trunc_l) >= 0)
        assert np.all(np.diff(w_r) >= 0) and np.all(np.diff(trunc_r) <= 0)


def test_edge_slack_both_sides() -> None:
    """Support fits inside data with 1-day slack, symmetric left/right."""
    assert PLAN.windows[0].start_day - L_T_MAX >= OBS_START_DAY + 1 - 1e-9
    assert PLAN.windows[-1].end_day + L_T_MAX <= OBS_END_DAY - 1 + 1e-9


def test_blend_partition_of_unity() -> None:
    """MUST fail with a fixed /V_DAYS denominator (35-d overlap sums to 35/15):
    the sample range sweeps straight through [322, 357]."""
    for d in np.linspace(-18, 364, 500):
        wins = PLAN.covering(float(d))
        total = sum(PLAN.weight(w, float(d)) for w in wins)
        assert total == pytest.approx(1.0)


def test_blend_linear_in_overlap() -> None:
    """Interior pair: day 30 in w0/w1 overlap [27, 42]: w0 weight (42-30)/15 = 0.8.
    Right pair: day 350 in w7/w8 overlap [322, 357]: w7 weight (357-350)/35 = 0.2."""
    w0, w1 = PLAN.covering(30.0)
    assert PLAN.weight(w0, 30.0) == pytest.approx(0.8)
    assert PLAN.weight(w1, 30.0) == pytest.approx(0.2)
    w7, w8 = PLAN.covering(350.0)
    assert PLAN.weight(w7, 350.0) == pytest.approx(0.2)
    assert PLAN.weight(w8, 350.0) == pytest.approx(1.0 - 0.2)


def test_window_ids_stable_and_distinct() -> None:
    """Ids derive from start_day — 9 distinct cache keys."""
    ids = [w.id for w in PLAN.windows]
    assert len(set(ids)) == 9


def test_single_window_plan_custom_w_days() -> None:
    """Task-11 harness: WindowPlan(starts=(-30,), w_days=425) = one 425-d window.

    Bug caught: end_day/id hardwired to the 60-d run-constant, making the
    windowed-vs-single-window equivalence diagnostic silently solve 60 days.
    """
    plan = WindowPlan(starts=(-30.0,), w_days=425.0)
    (w,) = plan.windows
    assert w.end_day == 395.0
    assert "425" in w.id  # distinct cache key vs any 60-d window
    for d in (0.0, 180.0, 364.0):
        assert plan.covering(d) == [w]
        assert plan.weight(w, d) == 1.0
