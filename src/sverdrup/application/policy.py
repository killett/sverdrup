"""Lexicographic selection Policy seam (plan Task 8; spec §8).

Comparison-only pairwise-criterion chain — the rule-of-three extraction of
the selection logic triplicated across ``tuning/objective.rank``,
``calibration/folds.select`` and ``tuning/lane_compare``. The seam computes
NO bands and carries NO conditional semantics: criteria are closures over
band VALUES computed (or loaded) by the call site; degradation = the site
DROPPING a criterion from the chain.

Two consumption modes:

- ``sort()`` — total ordering; UNBANDED criteria only. A banded criterion
  (±band ties) forms a SEMIORDER: ties are intransitive (a~b, b~c yet a
  beats c), so no total order exists and ``sort()`` refuses loudly.
- ``winner()`` — the sequential pinned-order reduction over candidates
  (folds' keep-running-winner loop shape), always audited; well-defined for
  banded criteria, with candidate order = list order as the pinned
  semantics.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import Enum, auto
from functools import cmp_to_key
from typing import Any


class Verdict(Enum):
    """Pairwise outcome of one criterion on (a, b)."""

    A_WINS = auto()
    B_WINS = auto()
    TIE = auto()


@dataclass(frozen=True)
class Criterion[T]:
    """One pinned-order comparison stage.

    Attributes:
        name: Stage name recorded in the audit trail.
        compare: ``(a, b) -> Verdict`` closure (over band values when banded).
        banded: True when ties span a band (semiorder — refuses ``sort()``).
        detail: Optional ``(a, b) -> dict`` of audit values (values/Δ/band).
    """

    name: str
    compare: Callable[[T, T], Verdict]  # in winner(): a=challenger, b=incumbent
    banded: bool = False
    detail: Callable[[T, T], dict[str, Any]] | None = None  # same (a, b) order


@dataclass(frozen=True)
class StageAudit:
    """One consulted stage of one pairwise comparison.

    ``detail`` is treated as immutable once trailed — call sites must not
    mutate it (it lands verbatim in evidence records).
    """

    criterion: str
    verdict: str
    detail: dict[str, Any]


class LexicographicPolicy[T]:
    """Sequential criterion chain: first non-TIE stage decides."""

    def __init__(self, criteria: Sequence[Criterion[T]]) -> None:
        """Store the pinned-order criteria.

        Args:
            criteria: Comparison stages, consulted in order.
        """
        self.criteria = tuple(criteria)

    def compare(self, a: T, b: T) -> tuple[Verdict, list[StageAudit]]:
        """Compare one pair through the chain, recording consulted stages.

        Args:
            a: Left candidate.
            b: Right candidate.

        Returns:
            ``(verdict, trail)`` — the trail holds EXACTLY the consulted
            stages (short-circuits at the first decisive verdict).
        """
        trail: list[StageAudit] = []
        for criterion in self.criteria:
            verdict = criterion.compare(a, b)
            trail.append(
                StageAudit(
                    criterion=criterion.name,
                    verdict=verdict.name,
                    detail=criterion.detail(a, b) if criterion.detail else {},
                )
            )
            if verdict is not Verdict.TIE:
                return verdict, trail
        return Verdict.TIE, trail

    def sort(self, candidates: list[T]) -> list[T]:
        """Stable total sort; UNBANDED criteria only.

        Args:
            candidates: Records to order (best first).

        Returns:
            New list, byte-identical order to the legacy
            ``sorted(key=...)`` expression for a single unbanded criterion
            (ties keep input order — ``sorted`` stability).

        Raises:
            ValueError: If any criterion is banded (semiorder — see module
                docstring; use :meth:`winner`).
        """
        if any(c.banded for c in self.criteria):
            raise ValueError(
                "banded criteria form a semiorder — sort() is refused; use winner()"
            )

        def _cmp(a: T, b: T) -> int:
            verdict, _trail = self.compare(a, b)
            if verdict is Verdict.A_WINS:
                return -1
            if verdict is Verdict.B_WINS:
                return 1
            return 0

        return sorted(candidates, key=cmp_to_key(_cmp))

    def winner(self, candidates: Sequence[T]) -> tuple[T, list[list[StageAudit]]]:
        """Sequential reduction in list order (keep-running-winner).

        Args:
            candidates: Non-empty candidate sequence; index 0 is the initial
                incumbent (terminal all-TIE keeps it — folds semantics).

        Returns:
            ``(winner, audits)`` with one trail per challenger, in order.
        """
        incumbent = candidates[0]
        audits: list[list[StageAudit]] = []
        for challenger in candidates[1:]:
            verdict, trail = self.compare(challenger, incumbent)
            audits.append(trail)
            if verdict is Verdict.A_WINS:
                incumbent = challenger
        return incumbent, audits
