"""Tests for ``miost_error_basis`` (plan Task 1 — pass table + B block).

Each test names the concrete bug it catches. Expected values hand-computed
from small synthetic fixtures — never derived by running the implementation.
"""

from __future__ import annotations

import hashlib

import numpy as np
import pytest

from sverdrup.methods.miost_error_basis import (
    PassTable,
    build_b,
    err_identity,
    lam_diag,
    mission_hash_ints,
    segment_passes,
)


def _hash_of(name: str) -> int:
    """The standing blake2b-4 mission hash (mirrors miost._obs_identity)."""
    return int.from_bytes(hashlib.blake2b(name.encode(), digest_size=4).digest(), "big")


def _mh(names: list[str]) -> np.ndarray:
    return mission_hash_ints(np.asarray(names))


def test_mission_hash_matches_obs_identity_convention() -> None:
    # Bug caught: a hash scheme diverging from miost._obs_identity's
    # blake2b-4 convention — the "err" CRN axis (Task 4) must key on the
    # SAME mission integers the obs axis uses.
    got = mission_hash_ints(np.asarray(["s3a", "alg"]))
    assert got.dtype == np.int64
    assert got.tolist() == [_hash_of("s3a"), _hash_of("alg")]


def test_segment_splits_on_gap_rule() -> None:
    # Gaps 30 s (same pass) and 2 h (new pass): 2 passes, obs 0-2 in the
    # first, obs 3-4 in the second (hand).
    # Bug caught: gap threshold compared in the wrong unit (seconds vs
    # day-valued diffs) merging everything or splitting every neighbor.
    t_s = np.asarray([0.0, 30.0, 60.0, 7200.0, 7230.0])
    pt = segment_passes(
        lon=np.full(5, 300.0),
        lat=np.asarray([30.0, 30.1, 30.2, 30.0, 30.1]),
        t_days=t_s / 86400.0,
        mission_hash=_mh(["a"] * 5),
    )
    assert pt.pass_mission.size == 2
    assert pt.obs_pass_idx.tolist() == [0, 0, 0, 1, 1]


def test_s_is_arc_length_not_time() -> None:
    # Three obs at the same lon, lats 30.0 / 30.09 / 30.36: cumulative arc
    # fractions 0, 0.25, 1.0 (hand: 0.09 / 0.36 of the lat span; same-lon
    # great-circle length is proportional to dlat). s = 2*frac - 1 ->
    # [-1, -0.5, +1]. Times are EQUALLY spaced, so a time-normalized s
    # would put the middle obs at 0.0, not -0.5.
    # Bug caught: s computed from time coordinates instead of arc length.
    pt = segment_passes(
        lon=np.full(3, 300.0),
        lat=np.asarray([30.0, 30.09, 30.36]),
        t_days=np.asarray([0.0, 1.0, 2.0]) / 86400.0,
        mission_hash=_mh(["a"] * 3),
    )
    assert pt.s == pytest.approx([-1.0, -0.5, 1.0], abs=1e-9)


def test_single_obs_pass_s_zero() -> None:
    # An isolated obs is its own pass with s = 0.0 EXACTLY (spec §3).
    # Bug caught: 0/0 arc normalization producing NaN.
    t_s = np.asarray([0.0, 10800.0, 10830.0])
    pt = segment_passes(
        lon=np.full(3, 300.0),
        lat=np.asarray([30.0, 31.0, 31.1]),
        t_days=t_s / 86400.0,
        mission_hash=_mh(["a"] * 3),
    )
    assert pt.pass_mission.size == 2
    first = pt.s[pt.obs_pass_idx == 0]
    assert first.tolist() == [0.0]
    assert pt.s.dtype == np.float64


def test_pass_identity_time_based_not_positional() -> None:
    # The SAME obs presented in reversed input order must yield the same
    # pass identities and the same per-obs (start_s, s) association.
    # Bug caught: positional pass ids (enumeration order of the input)
    # instead of time-based identity (spec §5 rider 2).
    t_s = np.asarray([0.0, 30.0, 7200.0, 7230.0])
    lon = np.asarray([300.0, 300.1, 301.0, 301.1])
    lat = np.asarray([30.0, 30.1, 32.0, 32.1])
    mh = _mh(["a"] * 4)
    fwd = segment_passes(lon, lat, t_s / 86400.0, mh)
    rev = segment_passes(
        lon[::-1].copy(), lat[::-1].copy(), (t_s[::-1] / 86400.0).copy(), mh
    )
    assert fwd.pass_start_s.tolist() == rev.pass_start_s.tolist()
    assert fwd.pass_mission.tolist() == rev.pass_mission.tolist()
    # per-obs association follows the VALUES, not the input slots
    assert fwd.s.tolist() == rev.s[::-1].tolist()
    assert fwd.pass_start_s[fwd.obs_pass_idx].tolist() == (
        rev.pass_start_s[rev.obs_pass_idx][::-1].tolist()
    )


def test_pass_start_s_integer_seconds_since_epoch() -> None:
    # First obs at t = 1.5 days -> pass_start_s == 129600 exactly, int64.
    # Bug caught: identity kept in float days (collides after rounding
    # drift) or seconds computed with a wrong epoch/scale.
    pt = segment_passes(
        lon=np.asarray([300.0, 300.1]),
        lat=np.asarray([30.0, 30.1]),
        t_days=np.asarray([1.5, 1.5 + 30.0 / 86400.0]),
        mission_hash=_mh(["a"] * 2),
    )
    assert pt.pass_start_s.dtype == np.int64
    assert pt.pass_start_s.tolist() == [129600]


def test_pass_start_s_rounds_negative_times_to_nearest_second() -> None:
    # Obs data start at day -31, so negative times are real. First obs at
    # exactly -864001 s stored as float days: the float product
    # t*86400 lands within 1e-6 s of -864001 and must round to -864001.
    # Bug caught: int() truncation toward zero (or floor) turning a
    # -864000.9999999 float artifact into -864000 — a 1 s identity drift
    # that breaks cross-window CRN keying for the same pass.
    t0 = -864001.0 / 86400.0
    pt = segment_passes(
        lon=np.asarray([300.0, 300.1]),
        lat=np.asarray([30.0, 30.1]),
        t_days=np.asarray([t0, t0 + 30.0 / 86400.0]),
        mission_hash=_mh(["a"] * 2),
    )
    assert pt.pass_start_s.tolist() == [-864001]


def test_build_b_exact_dense_on_hand_fixture() -> None:
    # Two passes: pass 0 obs {0,1,2} with s = [-1, -0.5, 1] (the arc
    # fixture), pass 1 a single obs {3} with s = [0]. Hand-built dense B
    # (n_obs=4, 2*n_pass=4), column order [bias0, tilt0, bias1, tilt1]:
    #   [[1, -1.0, 0, 0],
    #    [1, -0.5, 0, 0],
    #    [1,  1.0, 0, 0],
    #    [0,  0.0, 1, 0]]
    # Bug caught: bias/tilt interleave swapped, or tilt column carrying
    # ones and bias carrying s.
    t_s = np.asarray([0.0, 1.0, 2.0, 10800.0])
    pt = segment_passes(
        lon=np.full(4, 300.0),
        lat=np.asarray([30.0, 30.09, 30.36, 31.0]),
        t_days=t_s / 86400.0,
        mission_hash=_mh(["a"] * 4),
    )
    b = build_b(pt).toarray()
    expected = np.asarray(
        [
            [1.0, -1.0, 0.0, 0.0],
            [1.0, -0.5, 0.0, 0.0],
            [1.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
        ]
    )
    np.testing.assert_allclose(b, expected, atol=1e-9)


def test_build_b_window_independent_for_shared_pass() -> None:
    # One pass (obs 2-4) fully inside BOTH of two overlapping synthetic
    # windows; each window also carries obs the other lacks. The pass's
    # bias/tilt column values on the shared obs must be IDENTICAL.
    # Bug caught: s normalized over the whole window's arc (window-scoped
    # normalization) instead of within the pass.
    lon = np.full(7, 300.0)
    lat = np.asarray([20.0, 20.1, 30.0, 30.09, 30.36, 40.0, 40.1])
    t_s = np.asarray([0.0, 30.0, 7200.0, 7201.0, 7202.0, 14400.0, 14430.0])
    mh = _mh(["a"] * 7)
    w1 = slice(0, 5)  # obs {0..4}: earlier pass + the shared pass
    w2 = slice(2, 7)  # obs {2..6}: the shared pass + a later pass
    pt1 = segment_passes(lon[w1], lat[w1], t_s[w1] / 86400.0, mh[w1])
    pt2 = segment_passes(lon[w2], lat[w2], t_s[w2] / 86400.0, mh[w2])
    b1 = build_b(pt1).toarray()
    b2 = build_b(pt2).toarray()
    # locate the shared pass by its TIME-BASED identity (start 7200 s)
    p1 = int(np.nonzero(pt1.pass_start_s == 7200)[0][0])
    p2 = int(np.nonzero(pt2.pass_start_s == 7200)[0][0])
    # shared obs are rows 2..4 in window 1 and rows 0..2 in window 2
    np.testing.assert_allclose(
        b1[2:5, 2 * p1 : 2 * p1 + 2], b2[0:3, 2 * p2 : 2 * p2 + 2], atol=1e-12
    )


def test_lam_diag_tiles_bias_tilt_per_pass() -> None:
    # n_pass=3, lam_bias=2.0, lam_tilt=5.0 -> [2,5,2,5,2,5] (hand), matching
    # build_b's per-pass [bias, tilt] column interleave.
    # Bug caught: block layout [b,b,b,t,t,t] silently mismatching columns.
    got = lam_diag(3, 2.0, 5.0)
    assert got.tolist() == [2.0, 5.0, 2.0, 5.0, 2.0, 5.0]
    assert got.dtype == np.float64


def test_err_identity_rows_exact_and_collision_free() -> None:
    # Two missions, SAME start second: rows must differ by mission hash.
    # Expected rows (hand), pass order = (start_s, mission_hash) sorted:
    # for each pass, (mission_hash, pass_start_s, mode_idx) with mode 0/1.
    # Bug caught: identity built from the pass INDEX (collides across
    # windows) or dropping the mission component (collides across missions).
    lon = np.asarray([300.0, 300.1, 300.0, 300.1])
    lat = np.asarray([30.0, 30.1, 31.0, 31.1])
    t_days = np.asarray([0.0, 30.0 / 86400.0, 0.0, 30.0 / 86400.0])
    pt = segment_passes(lon, lat, t_days, _mh(["a", "a", "b", "b"]))
    ident = err_identity(pt)
    assert ident.shape == (4, 3)
    assert ident.dtype == np.int64
    ha, hb = _hash_of("a"), _hash_of("b")
    lo, hi = sorted([ha, hb])
    expected = [[lo, 0, 0], [lo, 0, 1], [hi, 0, 0], [hi, 0, 1]]
    assert ident.tolist() == expected
    # collision-free across all rows
    assert len({tuple(r) for r in ident.tolist()}) == 4


def test_passtable_s_bounds() -> None:
    # Every s lies in [-1, 1] on a generic multi-pass fixture; endpoints hit
    # exactly for multi-obs passes.
    # Bug caught: normalization producing values outside the pinned range
    # (e.g. arc not shifted by arc_min).
    rng = np.random.default_rng(7)
    n = 40
    t_s = np.sort(rng.uniform(0, 4.0, n)) * 3600.0
    pt = segment_passes(
        lon=rng.uniform(295.0, 305.0, n),
        lat=rng.uniform(24.0, 52.0, n),
        t_days=t_s / 86400.0,
        mission_hash=_mh(["a"] * n),
    )
    assert isinstance(pt, PassTable)
    assert float(pt.s.min()) >= -1.0
    assert float(pt.s.max()) <= 1.0
