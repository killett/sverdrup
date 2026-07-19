"""Unit tests for ``scripts/phase13_probe.py`` (plan Task 0 — leg A units).

Pure-function tests only: the input guard (zero-c2 discipline) and the
pass-count aggregation helper. The probe execution path is script-run,
never exercised here (no data touched at import).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from tests.helpers import load_script

probe = load_script("phase13_probe")

_OBS = Path("data/2021a_ssh_mapping_ose/dc_obs")
_FIVE = [
    _OBS / f"dt_gulfstream_{m}_phy_l3_20161201-20180131_285-315_23-53.nc"
    for m in ("alg", "h2g", "j2g", "j2n", "s3a")
]


def test_input_guard_rejects_j3() -> None:
    # Bug caught: a guard checking only c2 lets the j3 VALIDATION mission
    # leak into the five-mission probe input (plan Task 0 zero-c2 AC).
    j3 = _OBS / "dt_gulfstream_j3_phy_l3_20161201-20180131_285-315_23-53.nc"
    with pytest.raises(ValueError, match="j3"):
        probe.guard_five_mission_inputs([*_FIVE, j3])


def test_input_guard_rejects_c2() -> None:
    # Bug caught: the withheld Cryosat-2 track consumed by the probe.
    c2 = _OBS / "dt_gulfstream_c2_phy_l3_20161201-20180131_285-315_23-53.nc"
    with pytest.raises(ValueError, match="c2"):
        probe.guard_five_mission_inputs([*_FIVE, c2])


def test_input_guard_accepts_the_five_mapping_missions() -> None:
    # Bug caught: an over-broad substring match (e.g. matching "j3" anywhere
    # in the path) refusing the legitimate five-mission list.
    assert probe.guard_five_mission_inputs(list(_FIVE)) == list(_FIVE)


def _frame(
    mission: list[str], t_s: list[float], lon: list[float], lat: list[float]
) -> dict[str, np.ndarray]:
    """Build a synthetic obs frame (times given in SECONDS for readability)."""
    return {
        "mission": np.asarray(mission),
        "t_days": np.asarray(t_s, dtype=float) / 86400.0,
        "lon": np.asarray(lon, dtype=float),
        "lat": np.asarray(lat, dtype=float),
    }


# One synthetic window covering the whole fixture day; aggregation takes
# explicit (id, start_day, end_day) windows, so tests never touch WindowPlan.
_W0 = ("w0", 0.0, 1.0)


def test_pass_counts_exact_on_gap_rule() -> None:
    # Mission "a": obs at 0, 30, 60 s (gaps 30 s <= 60 s -> ONE pass), then
    # 7200 s (2 h gap -> SECOND pass with its 7230 s neighbor).
    # Mission "b": one 2-obs pass. Hand counts: a -> 2 passes, b -> 1.
    # Bug caught: gap threshold applied in the wrong unit (seconds compared
    # against day-valued diffs merges everything into one pass; days
    # compared against second-valued diffs splits every neighbor).
    f = _frame(
        mission=["a", "a", "a", "a", "a", "b", "b"],
        t_s=[0.0, 30.0, 60.0, 7200.0, 7230.0, 100.0, 130.0],
        lon=[300.0] * 7,
        lat=[30.0, 30.1, 30.2, 30.0, 30.1, 40.0, 40.1],
    )
    stats = probe.aggregate_pass_stats(f, [_W0], gap_sec=60.0)
    assert stats["w0"]["a"]["n_passes"] == 2
    assert stats["w0"]["b"]["n_passes"] == 1


def test_single_obs_pass_is_counted() -> None:
    # One isolated obs 3 h from its neighbors IS a pass (Task-1 identity
    # rule keeps single-obs passes; s = 0). Hand count: 2 passes.
    # Bug caught: reusing orbit_geometry.split_passes' "< 2 obs -> skip"
    # convention undercounts the per-window mode dimension.
    f = _frame(
        mission=["a", "a", "a"],
        t_s=[0.0, 30.0, 10800.0],
        lon=[300.0] * 3,
        lat=[30.0, 30.1, 31.0],
    )
    stats = probe.aggregate_pass_stats(f, [_W0], gap_sec=60.0)
    assert stats["w0"]["a"]["n_passes"] == 2
    # Passes carry 2 and 1 obs -> median 1.5; the single-obs pass has zero
    # arc length, so chord min is exactly 0.0 (hand).
    assert stats["w0"]["a"]["median_pass_n_obs"] == 1.5
    assert stats["w0"]["a"]["chord_km"]["min"] == 0.0


def test_median_pass_length_counts_obs_per_pass() -> None:
    # Passes of 2 and 4 obs -> median pass length 3.0 (hand).
    # Bug caught: median over obs times (or over passes' durations) instead
    # of per-pass obs counts.
    f = _frame(
        mission=["a"] * 6,
        t_s=[0.0, 30.0, 7200.0, 7230.0, 7260.0, 7290.0],
        lon=[300.0] * 6,
        lat=[30.0, 30.1, 30.0, 30.1, 30.2, 30.3],
    )
    stats = probe.aggregate_pass_stats(f, [_W0], gap_sec=60.0)
    assert stats["w0"]["a"]["median_pass_n_obs"] == 3.0


def test_chord_length_uses_great_circle_not_raw_degrees() -> None:
    # Two-obs pass at lat 60, lon 10 -> 11: great-circle ~ 111.19*cos(60 deg)
    # ~ 55.6 km (hand: R*cos(lat)*dlon_rad = 6371*0.5*0.017453 = 55.597).
    # Bug caught: chord computed as raw degree distance * 111.32 (no
    # cos(lat)) reports ~111.3 km — double the true length at this latitude.
    f = _frame(
        mission=["a", "a"],
        t_s=[0.0, 30.0],
        lon=[10.0, 11.0],
        lat=[60.0, 60.0],
    )
    stats = probe.aggregate_pass_stats(f, [_W0], gap_sec=60.0)
    assert stats["w0"]["a"]["chord_km"]["median"] == pytest.approx(55.6, abs=0.4)


def test_trials_per_lane_floor_exact() -> None:
    # 12 h wall, 1200 s trial, 3 lanes -> floor(43200/3600) = 12 (hand).
    # Bug caught: the h->s conversion drifting (3600 lost -> 0 trials).
    assert probe.trials_per_lane(t_trial_s=1200.0, wall_budget_h=12.0, n_lanes=3) == 12


def test_trials_per_lane_floor_fractional() -> None:
    # floor(43200 / (1300*2)) = floor(16.615) = 16 (hand).
    # Bug caught: round/ceil instead of floor over-booking the wall.
    assert probe.trials_per_lane(t_trial_s=1300.0, wall_budget_h=12.0, n_lanes=2) == 16


def test_trials_per_lane_rejects_nonpositive_cost() -> None:
    # Bug caught: silent ZeroDivisionError/inf trials on a bad measurement.
    with pytest.raises(ValueError, match="t_trial_s"):
        probe.trials_per_lane(t_trial_s=0.0, wall_budget_h=12.0, n_lanes=2)


def test_budget_three_lanes_when_conditional_covered() -> None:
    # t=1200 s: n3 = floor(43200/3600) = 12 >= 8 -> the modes-only 4th
    # lane RUNS and all three sweeping lanes get n = 12 (hand).
    # Bug caught: conditional rule inverted (modes-only run only when
    # budget is SHORT), or the committed lanes keeping the 2-lane n.
    d = probe.budget_determination(t_trial_s=1200.0, wall_budget_h=12.0)
    assert d["modes_only_runs"] is True
    assert d["n_per_lane"] == 12
    assert d["screening_contingency_active"] is False
    assert d["lanes"] == ["D", "C", "modes-only"]


def test_budget_conditional_boundary_exactly_at_floor() -> None:
    # t=1800 s: n3 = floor(43200/5400) = 8 == floor -> runs (>= is the
    # pinned rule, spec §7 "n >= the floor").
    # Bug caught: a strict > at the boundary silently dropping the lane.
    d = probe.budget_determination(t_trial_s=1800.0, wall_budget_h=12.0)
    assert d["modes_only_runs"] is True
    assert d["n_per_lane"] == 8


def test_budget_two_lanes_when_conditional_uncovered() -> None:
    # t=2400 s: n3 = floor(43200/7200) = 6 < 8 but n2 = floor(43200/4800)
    # = 9 >= 8 -> committed lanes at 9, modes-only NOT run (hand).
    # Bug caught: the conditional lane stealing budget the committed
    # lanes need (n dropping to 6 for everyone).
    d = probe.budget_determination(t_trial_s=2400.0, wall_budget_h=12.0)
    assert d["modes_only_runs"] is False
    assert d["n_per_lane"] == 9
    assert d["screening_contingency_active"] is False
    assert d["lanes"] == ["D", "C"]


def test_budget_screening_contingency_below_floor() -> None:
    # t=6000 s: n2 = floor(43200/12000) = 3 < 8 -> the sealed 91-day
    # screening contingency arms (n=30/lane screening, k=3 re-scores).
    # Bug caught: under-floor budgets silently sweeping with tiny n
    # instead of arming the pre-registered contingency.
    d = probe.budget_determination(t_trial_s=6000.0, wall_budget_h=12.0)
    assert d["screening_contingency_active"] is True
    assert d["modes_only_runs"] is False
    assert d["n_screening_per_lane"] == 30
    assert d["k_full_rescores"] == 3


def test_overlap_obs_counted_in_both_windows() -> None:
    # Windows [0, 1] and [0.5, 1.5] overlap; a pass at day 0.75 belongs to
    # BOTH windows' per-window load statistics (windows solve independently).
    # Bug caught: exclusive/half-open assignment silently dropping overlap
    # passes from one window's mode-count estimate.
    f = _frame(
        mission=["a", "a"],
        t_s=[64800.0, 64830.0],  # day 0.75
        lon=[300.0, 300.0],
        lat=[30.0, 30.1],
    )
    windows = [("w0", 0.0, 1.0), ("w1", 0.5, 1.5)]
    stats = probe.aggregate_pass_stats(f, windows, gap_sec=60.0)
    assert stats["w0"]["a"]["n_passes"] == 1
    assert stats["w1"]["a"]["n_passes"] == 1
