"""Epoch-table tests (phase-14 Task 5, 0a-2) — holdout criteria mechanical.

Synthetic census reproducing the known shape; every expected holdout is
hand-derived from the recorded criteria order, never from the code.
"""

from __future__ import annotations

import numpy as np

from sverdrup.application.epoch_table import (
    INSTRUMENT_CLASS,
    build_epoch_table,
    serialize_epoch_table,
)
from sverdrup.application.epochs import build_census, partition_epochs


def _dates(start: str, end: str) -> list[str]:
    days = np.arange(np.datetime64(start), np.datetime64(end) + np.timedelta64(1, "D"))
    return [str(d) for d in days]


def _catalog() -> dict[str, dict[str, list[str]]]:
    return {
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


def _table():
    part = partition_epochs(build_census(_catalog()))
    return build_epoch_table(part.epochs, build_census(_catalog()))


def test_2017_anchor_row_pinned() -> None:
    """The epoch containing 2017: holdout j3, role reference (fit+validate)
    — the signed workhorse, by construction (spec fork-c)."""
    table = _table()
    row = next(r for r in table.rows if r.start <= np.datetime64("2017-07-01") < r.end)
    assert row.holdout == "j3"
    assert row.criterion == "signed-workhorse-by-construction"
    assert row.role == "fit+validate"
    assert row.fit_or_transferred == "fit"
    assert "c2" in row.locked_instruments  # c2 flies here
    assert "gauges" in row.locked_instruments


def test_1993_shape_row() -> None:
    """The earliest epoch: ERS-line holdout, validate-only, mask flag,
    sibling-less — every column hand-derived.

    {tp, e1}: criterion 1 removes tp (climate line, alternative exists)
    -> e1; e1 has no ers-line sibling assimilated -> sibling_less; e1 is
    ERS-line -> ±66 mask; net constellation 2 < 4 -> validate-only,
    transferred; c2 does not fly -> gauges only.
    """
    table = _table()
    row = table.rows[0]
    assert row.holdout == "e1"
    assert row.role == "validate-only"
    assert row.fit_or_transferred == "transferred"
    assert row.mask_66 is True
    assert row.sibling_less is True
    assert row.locked_instruments == ("gauges",)


def test_sibling_preference_and_stability() -> None:
    """A mid-2000s epoch: sibling-holding candidates beat sibling-less.

    The epoch containing {e2, en, j1, tp}: criterion 1 drops the climate
    line (j1, tp) -> pool {e2, en}; both hold ers-line siblings; the
    geometry mix is all-repeat so distortion ties -> lexicographic
    stability picks 'e2'. Rebuild yields the identical table (stable).
    """
    table = _table()
    row = next(r for r in table.rows if {"e2", "en", "j1"} <= set(r.missions))
    assert row.holdout == "e2"
    assert row.sibling_less is False
    assert serialize_epoch_table(_table()) == serialize_epoch_table(table)


def test_never_climate_line_where_alternative_exists() -> None:
    """No row holds out a Poseidon-line mission except the anchor pin."""
    for row in _table().rows:
        if row.criterion == "signed-workhorse-by-construction":
            continue
        assert INSTRUMENT_CLASS[row.holdout] != "poseidon", row


def test_handicap_fraction_recorded() -> None:
    """fit_substrate_fraction = (net - 1)/net of the epoch's NET count."""
    for row in _table().rows:
        net = len(set(row.missions) - {"c2", "c2n"})
        assert row.fit_substrate_fraction == (net - 1) / net


def test_serialization_deterministic_bytes() -> None:
    """The seal consumes these bytes: two builds byte-identical."""
    a = serialize_epoch_table(_table())
    b = serialize_epoch_table(_table())
    assert a == b and isinstance(a, bytes)
