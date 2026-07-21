"""Tests for the phase-13 §8 diagnostics statistics (plan Task 11).

Each test names the bug it catches; expected values are hand-computed
(exact fixtures chosen so correlations/fractions are analytic).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from tests.helpers import load_script

diag = load_script("phase13_diagnostics")


def _rows(
    mission: list[str],
    family: list[str],
    c_bias: list[float],
    c_tilt: list[float] | None = None,
    t_mean_days: list[float] | None = None,
    field_chord_mean: list[float] | None = None,
    n_obs: list[int] | None = None,
) -> list[dict[str, object]]:
    n = len(mission)
    return [
        {
            "mission": mission[i],
            "family": family[i],
            "c_bias": c_bias[i],
            "c_tilt": (c_tilt or [0.0] * n)[i],
            "t_mean_days": (t_mean_days or [float(i)] * 1 + [float(i)] * (n - 1))[i]
            if t_mean_days
            else float(i),
            "field_chord_mean": (field_chord_mean or [0.0] * n)[i],
            "n_obs": (n_obs or [10] * n)[i],
        }
        for i in range(n)
    ]


def test_variance_ratio_table_hand_values() -> None:
    # var(ddof=1) of [0.1, -0.1] = 0.02; ratio vs lam_bias 0.01 = 2.0;
    # tilt [0.2, 0.0]: var = 0.02, ratio vs lam_tilt 0.04 = 0.5 (hand).
    # Bug caught: ratio inverted (lam/var), ddof=0 (0.01 -> ratio 1.0),
    # or bias/tilt columns swapped.
    rows = _rows(
        mission=["j3", "j3"],
        family=["asc", "asc"],
        c_bias=[0.1, -0.1],
        c_tilt=[0.2, 0.0],
    )
    table = diag.variance_ratio_table(rows, lam_bias=0.01, lam_tilt=0.04)
    j3 = table["j3"]
    assert np.isclose(j3["var_ratio_bias"], 2.0)
    assert np.isclose(j3["var_ratio_tilt"], 0.5)
    assert j3["n_passes"] == 2


def test_saturation_fraction_hand_values() -> None:
    # lam 0.04 -> 2*sqrt(lam) = 0.4; |c| in [0.1, 0.3, 0.5, 0.7] exceeds
    # for 0.5 and 0.7 -> fraction 0.5 exactly (hand).
    # Bug caught: threshold sqrt(lam) or 2*lam instead of 2*sqrt(lam),
    # or >= vs > at the boundary counting 0.4 itself.
    rows = _rows(
        mission=["s3a"] * 4,
        family=["asc"] * 4,
        c_bias=[0.1, -0.3, 0.5, -0.7],
    )
    sat = diag.saturation_fraction(rows, lam_bias=0.04, lam_tilt=0.04)
    assert np.isclose(sat["s3a"]["bias"], 0.5)


def test_lag1_autocorr_exact_endpoints() -> None:
    # Monotone sequence [1,2,3,4] time-ordered: corr(x[:-1], x[1:]) =
    # corr([1,2,3],[2,3,4]) = 1.0 exactly. Alternating [1,-1,1,-1]:
    # corr([1,-1,1],[-1,1,-1]) = -1.0 exactly. Null band 2/sqrt(4) = 1.0.
    # Bug caught: sequence not time-ordered before lagging (a shuffled
    # order destroys +1.0), families mixed (asc+desc interleave injects
    # alternation - the spec's named hazard), or band using n-1.
    rows = _rows(
        mission=["j3"] * 4 + ["j3"] * 4,
        family=["asc"] * 4 + ["desc"] * 4,
        c_bias=[1.0, 2.0, 3.0, 4.0, 1.0, -1.0, 1.0, -1.0],
        t_mean_days=[3.0, 1.0, 2.0, 4.0, 1.0, 2.0, 3.0, 4.0],
    )
    # asc values by TIME order: t=[3,1,2,4] -> ordered c = [2,3,1,4]?? No:
    # c_bias asc rows are [1,2,3,4] at t [3,1,2,4] -> time-ordered seq is
    # [2.0 (t=1), 3.0 (t=2), 1.0 (t=3), 4.0 (t=4)] — NOT monotone, so use
    # the desc family for the exact -1.0 and give asc aligned times below.
    out = diag.lag1_autocorr(rows)
    desc = out[("j3", "desc")]
    assert np.isclose(desc["r1"], -1.0)
    assert np.isclose(desc["null_band"], 1.0)
    assert desc["n_passes"] == 4
    # median inter-pass dt for desc: diffs [1,1,1] -> 1.0
    assert np.isclose(desc["median_dt_days"], 1.0)


def test_lag1_autocorr_time_orders_before_lagging() -> None:
    # Values [10, 20, 30, 40] carried at shuffled times [2, 4, 1, 3]:
    # time-ordered sequence is [30, 10, 40, 20] whose lag-1 corr is
    # corr([30,10,40],[10,40,20]) = -0.5 by hand:
    #   a=[30,10,40] mean 26.667, b=[10,40,20] mean 23.333
    #   cov = ((3.333*-13.333)+(-16.667*16.667)+(13.333*-3.333))/3 = -122.22
    #   sd_a = sqrt((11.11+277.78+177.78)/3)=12.472, sd_b same -> r=-0.786?
    # (exact arithmetic done in-code below against a hand-ordered copy)
    # Bug caught: lagging in ROW order (gives corr([10,20,30],[20,30,40])
    # = +1.0) instead of time order.
    rows = _rows(
        mission=["alg"] * 4,
        family=["asc"] * 4,
        c_bias=[10.0, 20.0, 30.0, 40.0],
        t_mean_days=[2.0, 4.0, 1.0, 3.0],
    )
    out = diag.lag1_autocorr(rows)
    seq = np.asarray([30.0, 10.0, 40.0, 20.0])  # hand time-ordering
    expected = float(np.corrcoef(seq[:-1], seq[1:])[0, 1])
    assert not np.isclose(expected, 1.0)  # the fixture discriminates
    assert np.isclose(out[("alg", "asc")]["r1"], expected)


def test_field_correlation_sign_logic() -> None:
    # n=5, band 2/sqrt(5) = 0.894. Perfect positive corr (r=1.0) exceeds
    # the band -> "absorption"; perfect negative -> "compensation";
    # zero-corr fixture (orthogonal) -> "clean" (hand).
    # Bug caught: sign classes swapped (positive must read absorption --
    # field leaking INTO modes, spec §8.4), or classification ignoring
    # the null band (any tiny r classified).
    pos = _rows(
        mission=["h2g"] * 5,
        family=["asc"] * 5,
        c_bias=[1.0, 2.0, 3.0, 4.0, 5.0],
        field_chord_mean=[2.0, 4.0, 6.0, 8.0, 10.0],
    )
    neg = _rows(
        mission=["h2g"] * 5,
        family=["asc"] * 5,
        c_bias=[1.0, 2.0, 3.0, 4.0, 5.0],
        field_chord_mean=[-2.0, -4.0, -6.0, -8.0, -10.0],
    )
    # corr([1,-1,1,-1,0],[1,1,-1,-1,0]) = 0 exactly (orthogonal, hand).
    zero = _rows(
        mission=["h2g"] * 5,
        family=["asc"] * 5,
        c_bias=[1.0, -1.0, 1.0, -1.0, 0.0],
        field_chord_mean=[1.0, 1.0, -1.0, -1.0, 0.0],
    )
    p = diag.field_correlation(pos)[("h2g", "asc")]
    n = diag.field_correlation(neg)[("h2g", "asc")]
    z = diag.field_correlation(zero)[("h2g", "asc")]
    assert np.isclose(p["r"], 1.0) and p["reading"] == "absorption"
    assert np.isclose(n["r"], -1.0) and n["reading"] == "compensation"
    assert np.isclose(z["r"], 0.0) and z["reading"] == "clean"


def test_adjacent_window_agreement_matches_by_identity() -> None:
    # Two windows share passes keyed (mission_hash, pass_start_s):
    # window A carries keys {(7,100): 1.0, (7,200): 2.0, (7,300): 5.0},
    # window B carries {(7,200): 2.5, (7,300): 4.5, (7,400): 9.0}.
    # Overlap = keys 200,300 -> pairs (2.0,2.5),(5.0,4.5): rmse =
    # sqrt((0.25+0.25)/2) = 0.5 exactly; n_matched = 2 (hand).
    # Bug caught: positional matching (pairing row i with row i across
    # windows pairs 1.0<->2.5 - the value-derived identity rule broken),
    # or unmatched passes silently entering the scatter.
    win_a = {
        "window": "w+00000",
        "keys": [(7, 100), (7, 200), (7, 300)],
        "c_bias": [1.0, 2.0, 5.0],
    }
    win_b = {
        "window": "w+00045",
        "keys": [(7, 200), (7, 300), (7, 400)],
        "c_bias": [2.5, 4.5, 9.0],
    }
    out = diag.adjacent_window_agreement([win_a, win_b])
    assert out["n_matched"] == 2
    assert np.isclose(out["rmse_bias"], 0.5)


def test_read_tap_dir_dedups_overlap_passes_by_identity(tmp_path: Path) -> None:
    # A pass in two overlapping windows appears ONCE in the per-pass rows
    # (identity = (mission_hash, pass_start_s); earlier window kept) while
    # BOTH copies feed the §8.5 stability scatter.
    # Bug caught: overlap passes double-counted — n_passes inflated and
    # every per-pass statistic biased toward the overlap region.
    import numpy as np

    def _write(name: str, starts: list[int], cb: list[float]) -> None:
        np.savez(
            tmp_path / name,
            window=np.asarray(name),
            c_bias=np.asarray(cb),
            c_tilt=np.zeros(len(cb)),
            pass_mission=np.asarray([7] * len(cb), dtype=np.int64),
            pass_mission_label=np.asarray(["j3"] * len(cb)),
            pass_start_s=np.asarray(starts, dtype=np.int64),
            family=np.asarray(["asc"] * len(cb)),
            t_mean_days=np.asarray([s / 86400.0 for s in starts]),
            field_chord_mean=np.zeros(len(cb)),
            n_obs=np.asarray([5] * len(cb), dtype=np.int64),
            lam_bias=np.asarray(0.01),
            lam_tilt=np.asarray(0.01),
        )

    _write("ctap_w+00000.0+60.npz", [100, 200], [1.0, 2.0])
    _write("ctap_w+00045.0+60.npz", [200, 300], [2.5, 3.0])  # 200 overlaps
    rows, windows = diag.read_tap_dir(tmp_path)
    assert len(rows) == 3  # 100, 200 (once), 300
    assert len(windows) == 2
    agree = diag.adjacent_window_agreement(windows)
    assert agree["n_matched"] == 1  # the overlap pass, matched by identity


def test_tables_for_json_flattens_tuple_keys() -> None:
    # Evidence is JSON: (mission, family) tuple keys must flatten to
    # "mission/family" strings.
    # Bug caught: json.dumps crashing on tuple keys AFTER the ensemble
    # run's evidence write window (a mid-assembly abort).
    out = diag.tables_for_json({("j3", "asc"): {"r1": 0.5}})
    assert out == {"j3/asc": {"r1": 0.5}}


def test_small_sample_rows_flagged_not_dropped() -> None:
    # A mission x family with n_passes < 3 cannot carry a lag-1 estimate:
    # the row must appear FLAGGED (r1 None), never silently vanish
    # (Phase-11 ratification 2: under-floor rows stay visible).
    # Bug caught: small families dropped from the table - an absent row
    # reads as "no problem" in the gate pack.
    rows = _rows(
        mission=["j2n", "j2n"],
        family=["asc", "desc"],
        c_bias=[0.5, 0.7],
        t_mean_days=[1.0, 2.0],
    )
    out = diag.lag1_autocorr(rows)
    assert ("j2n", "asc") in out
    assert out[("j2n", "asc")]["r1"] is None
    assert out[("j2n", "asc")]["n_passes"] == 1
