"""Tests for the lexicographic Policy seam (plan Task 8; spec §8).

The gate-(iii) sort-identity property test lives HERE: byte-identical order
vs ``sorted(key=...)`` over 200 seeded-random lists, ties included.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from sverdrup.application.policy import (
    Criterion,
    LexicographicPolicy,
    StageAudit,
    Verdict,
)


@dataclass(frozen=True)
class _Rec:
    name: str
    primary: float
    secondary: float = 0.0


def _lower_primary(a: _Rec, b: _Rec) -> Verdict:
    if a.primary < b.primary:
        return Verdict.A_WINS
    if b.primary < a.primary:
        return Verdict.B_WINS
    return Verdict.TIE


def _banded_primary(a: _Rec, b: _Rec, band: float = 1.0) -> Verdict:
    if a.primary < b.primary - band:
        return Verdict.A_WINS
    if b.primary < a.primary - band:
        return Verdict.B_WINS
    return Verdict.TIE


def test_sort_refuses_any_banded_criterion() -> None:
    """Bug caught: a semiorder (banded ties) fed to a total sort — banded
    comparisons are INTRANSITIVE, so sort() must refuse loudly.

    The intransitivity, constructed: with band 1.0, a=0.0, b=0.9, c=1.8 —
    a~b (gap 0.9 within band), b~c (gap 0.9 within band), but a BEATS c
    (gap 1.8 beyond band). No total order exists; only the sequential
    winner() reduction is well-defined on such criteria."""
    pol = LexicographicPolicy((Criterion("primary", _banded_primary, banded=True),))
    with pytest.raises(ValueError, match="banded"):
        pol.sort([_Rec("a", 0.0), _Rec("b", 0.9), _Rec("c", 1.8)])


def test_winner_handles_intransitive_triple_deterministically() -> None:
    """Bug caught: the winner() reduction depending on anything but the
    pinned list order for the a~b, b~c, a-beats-c triple."""
    a, b, c = _Rec("a", 0.0), _Rec("b", 0.9), _Rec("c", 1.8)
    pol = LexicographicPolicy((Criterion("primary", _banded_primary, banded=True),))
    # order (a, b, c): b ties incumbent a -> a stays; c ties?? c vs a: a beats
    # -> incumbent a survives both challenges
    w1, audits1 = pol.winner([a, b, c])
    assert w1 is a
    assert len(audits1) == 2
    # order (c, b, a): b ~ c -> c stays; a BEATS c -> a wins
    w2, _ = pol.winner([c, b, a])
    assert w2 is a
    # order (b, c, a): c ~ b -> b stays; a ~ b -> b survives — list order is
    # the pinned semantics (legacy folds loop shape), not a global optimum
    w3, _ = pol.winner([b, c, a])
    assert w3 is b


def test_sort_single_unbanded_criterion_identical_to_sorted_key() -> None:
    """GATE (iii) property test — bug caught: any deviation (comparator sign,
    stability loss) from the legacy ``sorted(key=...)`` order; object
    identity per position over 200 seeded-random lists, ties included."""
    pol = LexicographicPolicy((Criterion("primary", _lower_primary),))
    rng = np.random.default_rng(2718)
    for trial in range(200):
        n = int(rng.integers(1, 30))
        # coarse grid of values -> plenty of exact ties to exercise stability
        recs = [_Rec(f"r{trial}_{i}", float(rng.integers(0, 6))) for i in range(n)]
        expected = sorted(recs, key=lambda r: r.primary)
        got = pol.sort(recs)
        assert len(got) == len(expected)
        for g, e in zip(got, expected, strict=True):
            assert g is e  # object identity per position


def test_sort_two_stage_lexicographic() -> None:
    """Bug caught: secondary criterion consulted before the primary ties."""

    def _lower_secondary(a: _Rec, b: _Rec) -> Verdict:
        if a.secondary < b.secondary:
            return Verdict.A_WINS
        if b.secondary < a.secondary:
            return Verdict.B_WINS
        return Verdict.TIE

    pol = LexicographicPolicy(
        (
            Criterion("primary", _lower_primary),
            Criterion("secondary", _lower_secondary),
        )
    )
    recs = [_Rec("x", 1.0, 2.0), _Rec("y", 0.0, 9.0), _Rec("z", 1.0, 1.0)]
    assert [r.name for r in pol.sort(recs)] == ["y", "z", "x"]


def test_winner_audit_schema_and_all_tie_keeps_first() -> None:
    """Bug caught: a dropped/reordered audit trail, or all-TIE electing
    anything but the FIRST candidate (folds keep-running-winner semantics)."""

    def _always_tie(a: _Rec, b: _Rec) -> Verdict:
        return Verdict.TIE

    def _detail(a: _Rec, b: _Rec) -> dict[str, object]:
        return {"a": a.name, "b": b.name}

    pol = LexicographicPolicy(
        (
            Criterion("s", _always_tie, banded=True, detail=_detail),
            Criterion("t", _always_tie, banded=True),
        )
    )
    recs = [_Rec("first", 0.0), _Rec("mid", -1.0), _Rec("last", -2.0)]
    winner, audits = pol.winner(recs)
    assert winner is recs[0]
    assert len(audits) == 2  # one trail per challenger
    for trail in audits:
        assert [s.criterion for s in trail] == ["s", "t"]
        assert all(isinstance(s, StageAudit) for s in trail)
        assert all(s.verdict == "TIE" for s in trail)
    assert audits[0][0].detail == {"a": "mid", "b": "first"}


def test_compare_short_circuits_at_first_decisive_stage() -> None:
    """Bug caught: later criteria leaking into the trail after a decisive
    verdict (the audit must show exactly what was consulted)."""
    calls: list[str] = []

    def _first(a: _Rec, b: _Rec) -> Verdict:
        calls.append("first")
        return Verdict.A_WINS

    def _second(a: _Rec, b: _Rec) -> Verdict:
        calls.append("second")
        return Verdict.TIE

    pol = LexicographicPolicy((Criterion("one", _first), Criterion("two", _second)))
    verdict, trail = pol.compare(_Rec("a", 0.0), _Rec("b", 1.0))
    assert verdict is Verdict.A_WINS
    assert [s.criterion for s in trail] == ["one"]
    assert calls == ["first"]
