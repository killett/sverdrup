"""Census artifact + epoch partition tests (phase-14 Task 4, 0a-1).

Synthetic catalogs reproduce the known constellation shape (1993
two-satellite; a mid-2000s 4-mission span; 2017 six-mission); every
boundary off-by-one is pinned by hand-derived expectations.
"""

from __future__ import annotations

import numpy as np
import pytest

from sverdrup.application.epochs import (
    MIN_EPOCH_DAYS,
    MISSION_GAP_SPLIT_D,
    build_census,
    partition_epochs,
    reference_candidates,
    window_epoch,
)


def _dates(start: str, end: str) -> list[str]:
    days = np.arange(np.datetime64(start), np.datetime64(end) + np.timedelta64(1, "D"))
    return [str(d) for d in days]


def test_constants_pinned() -> None:
    """The recorded constants (spec 0a-1)."""
    assert MISSION_GAP_SPLIT_D == 90
    assert MIN_EPOCH_DAYS == 365


def test_census_active_intervals_split_on_gap() -> None:
    """An intra-mission gap > 90 d splits the ACTIVE interval; ≤ 90 d not.

    Hand fixture: tp flies 1993-01-01..1994-06-30, silent 200 d, resumes
    1995-01-16..1996-12-31 -> TWO intervals. j1 has an 89-day gap -> ONE.
    """
    catalog = {
        "tp": {
            "dates": _dates("1993-01-01", "1994-06-30")
            + _dates("1995-01-16", "1996-12-31")
        },
        "j1": {
            "dates": _dates("1993-01-01", "1993-06-30")
            + _dates("1993-09-27", "1994-12-31")
        },  # gap = 89 d
    }
    census = build_census(catalog)
    assert census.schema_version == 1
    tp = census.intervals["tp"]
    assert [(str(a), str(b)) for a, b in tp] == [
        ("1993-01-01", "1994-06-30"),
        ("1995-01-16", "1996-12-31"),
    ]
    assert len(census.intervals["j1"]) == 1


def test_census_content_sha_deterministic() -> None:
    """Two builds from the same catalog are byte-equal (content sha)."""
    catalog = {"tp": {"dates": _dates("1993-01-01", "1995-01-01")}}
    a = build_census(catalog)
    b = build_census(catalog)
    assert a.content_sha() == b.content_sha()
    c = build_census({"tp": {"dates": _dates("1993-01-01", "1995-01-02")}})
    assert c.content_sha() != a.content_sha()


def _shape_catalog() -> dict[str, dict[str, list[str]]]:
    """The known constellation shape, synthetic."""
    return {
        # the climate reference line, continuous
        "tp": {"dates": _dates("1993-01-01", "2002-12-31")},
        "j1": {"dates": _dates("2002-01-01", "2008-12-31")},
        "e1": {"dates": _dates("1993-01-01", "1996-05-31")},
        "e2": {"dates": _dates("1995-06-01", "2003-06-30")},
        "en": {"dates": _dates("2002-06-01", "2012-04-08")},
        "g2": {"dates": _dates("2004-06-01", "2008-12-31")},
        "al": {"dates": _dates("2013-03-14", "2017-12-31")},
        "j2": {"dates": _dates("2008-07-04", "2017-12-31")},
        "j3": {"dates": _dates("2016-02-17", "2017-12-31")},
        "s3a": {"dates": _dates("2016-03-01", "2017-12-31")},
        "c2": {"dates": _dates("2010-07-16", "2017-12-31")},
        "h2a": {"dates": _dates("2011-10-01", "2017-12-31")},
    }


def test_partition_full_expected_epochs_pinned() -> None:
    """The COMPLETE expected partition of the shape, hand-derived.

    Every boundary is an interval endpoint (+1 day on ends) and every
    merge direction follows the Jaccard rule — e.g. the 151-day
    2002-01-01→2002-06-01 segment ({e2,j1,tp}) merges RIGHT into the
    4-mission span (Jaccard 3/4 vs 2/3 left); the 181-day post-tp
    segment merges LEFT. An inverted tie-break or off-by-one boundary
    changes this table.
    """
    part = partition_epochs(build_census(_shape_catalog()))
    expected = [
        ("e00_1993-01-01", "1993-01-01", "1995-06-01", ["e1", "tp"]),
        ("e01_1995-06-01", "1995-06-01", "1996-06-01", ["e1", "e2", "tp"]),
        ("e02_1996-06-01", "1996-06-01", "2002-01-01", ["e2", "tp"]),
        ("e03_2002-01-01", "2002-01-01", "2003-07-01", ["e2", "en", "j1", "tp"]),
        ("e04_2003-07-01", "2003-07-01", "2009-01-01", ["en", "g2", "j1", "j2"]),
        ("e05_2009-01-01", "2009-01-01", "2010-07-16", ["en", "j2"]),
        ("e06_2010-07-16", "2010-07-16", "2013-03-14", ["c2", "en", "h2a", "j2"]),
        ("e07_2013-03-14", "2013-03-14", "2016-02-17", ["al", "c2", "h2a", "j2"]),
        (
            "e08_2016-02-17",
            "2016-02-17",
            "2018-01-01",
            ["al", "c2", "h2a", "j2", "j3", "s3a"],
        ),
    ]
    got = [
        (e.epoch_id, str(e.start), str(e.end), sorted(e.missions)) for e in part.epochs
    ]
    assert got == expected


def test_partition_boundaries_and_merge_trail() -> None:
    """Boundaries = union of interval endpoints; short epochs MERGED with
    the trail kept (raw_boundaries) — hand-checkable on the shape."""
    part = partition_epochs(build_census(_shape_catalog()))
    # raw boundaries preserved even where epochs merged
    assert len(part.raw_boundaries) >= len(part.epochs) + 1
    # every epoch >= the minimum (the rule's whole point)
    for e in part.epochs:
        assert (e.end - e.start) / np.timedelta64(1, "D") >= MIN_EPOCH_DAYS
    # deterministic naming: index in time order, start date in the id
    for i, e in enumerate(part.epochs):
        assert e.epoch_id == f"e{i:02d}_{e.start}"
    # epochs tile the record contiguously
    for a, b in zip(part.epochs, part.epochs[1:], strict=False):
        assert a.end == b.start


def test_window_epoch_center_rule() -> None:
    """The WINDOW-CENTER rule: the epoch containing the center date wins;
    boundary day belongs to the LATER epoch (half-open intervals)."""
    part = partition_epochs(build_census(_shape_catalog()))
    e0, e1 = part.epochs[0], part.epochs[1]
    assert window_epoch(e0.start, part.epochs) == e0.epoch_id
    assert window_epoch(e1.start, part.epochs) == e1.epoch_id  # boundary -> later
    inside = e0.start + np.timedelta64(10, "D")
    assert window_epoch(inside, part.epochs) == e0.epoch_id
    with pytest.raises(ValueError, match="epoch"):
        window_epoch(np.datetime64("1875-01-01"), part.epochs)


def test_reference_candidates_net_of_locked() -> None:
    """Constellation counted NET of locked missions (fork-e pin 3).

    The 2017-era epoch counts j3+s3a+al (+c2, +h2a where active) but c2
    is locked: candidates need net >= 4. Hand check: 2016-03..2017-12
    epoch has {al, j3, s3a, c2} -> net 3 (c2 out) -> NOT a candidate;
    with j2 active through 2016-10 the earlier epoch qualifies iff its
    net count >= 4.
    """
    part = partition_epochs(build_census(_shape_catalog()))
    cands = reference_candidates(part.epochs, locked_exclusions=frozenset({"c2"}))
    for e in part.epochs:
        net = len(e.missions - {"c2"})
        assert (e.epoch_id in cands) == (net >= 4)
    # anti-vacuity: the shape must produce BOTH candidates and non-candidates
    assert cands and len(cands) < len(part.epochs)


def test_epoch_missions_recorded_per_epoch() -> None:
    """Each epoch records the missions ACTIVE within it (drives Jaccard
    merging and the net-of-locked counts) — 1993 shape is two-satellite."""
    part = partition_epochs(build_census(_shape_catalog()))
    first = part.epochs[0]
    assert first.missions == {"tp", "e1"}
