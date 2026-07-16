"""Constrained (not scalarized) multi-objective ranking (Phase-5, spec 5/§8)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

from sverdrup.application.policy import Criterion, LexicographicPolicy, Verdict
from sverdrup.application.tuning.trial import TrialRecord
from sverdrup.core.types import UncertaintyCapability

BASELINE_BAR_MU = (
    0.85  # hard admissibility floor (published 2021a BASELINE µ; OI 0.853 clears it)
)
DUACS_TARGET_MU = 0.88  # aspirational acceptance target, never a hard gate
_COVERAGE_TARGET = 0.6827
_COVERAGE_TOL = 0.10


class NoAdmissibleTrial(RuntimeError):
    """Raised when no feasible trial passes every hard bar (a config signal, not a result)."""


@dataclass(frozen=True)
class HardBar:
    """One hard admissibility constraint on a named score."""

    metric: str
    op: str  # ">=", "<=", or "within"
    threshold: float
    tol: float = 0.0

    def passes(self, scores: dict[str, float]) -> bool:
        """Return True iff ``scores[metric]`` satisfies this bar (missing metric fails)."""
        if self.metric not in scores:
            return False
        v = scores[self.metric]
        if self.op == ">=":
            return v >= self.threshold
        if self.op == "<=":
            return v <= self.threshold
        if self.op == "within":
            return abs(v - self.threshold) <= self.tol
        raise ValueError(f"unknown op {self.op!r}")


def _default_bars() -> tuple[HardBar, ...]:
    return (
        HardBar("mu_score", ">=", BASELINE_BAR_MU),
        HardBar("coverage_1sigma", "within", _COVERAGE_TARGET, _COVERAGE_TOL),
    )


def bars_for(capability: UncertaintyCapability) -> tuple[HardBar, ...]:
    """Capability-derived hard bars (spec §5.3): coverage iff capability can emit variance.

    Args:
        capability: The method's native uncertainty capability.

    Returns:
        The hard-bar tuple; POINT gets the µ bar only.
    """
    bars: tuple[HardBar, ...] = (HardBar("mu_score", ">=", BASELINE_BAR_MU),)
    if capability.value >= UncertaintyCapability.MARGINAL_VARIANCE.value:
        bars += (HardBar("coverage_1sigma", "within", _COVERAGE_TARGET, _COVERAGE_TOL),)
    return bars


@dataclass(frozen=True)
class ConstrainedObjective:
    """Maximize resolution (minimize λx) subject to hard bars. No weighted-sum."""

    primary: str = "lambda_x"
    bars: tuple[HardBar, ...] = field(default_factory=_default_bars)

    def admissible(self, scores: dict[str, float]) -> bool:
        """Return True iff every hard bar passes."""
        return all(b.passes(scores) for b in self.bars)

    def rank(self, records: list[TrialRecord]) -> list[TrialRecord]:
        """Return admissible feasible records sorted ascending by the primary objective.

        The sort delegates to the Phase-11 Policy seam with a single unbanded
        lower-is-better criterion — byte-identical order to the legacy
        ``sorted(ok, key=lambda r: r.scores[primary])`` (gate-iii identity
        property test in tests/test_tuning_objective.py). Bar filter and
        :class:`NoAdmissibleTrial` stay HERE — the seam only compares.
        """
        ok = [
            r
            for r in records
            if r.feasible and r.scores is not None and self.admissible(r.scores)
        ]
        if not ok:
            raise NoAdmissibleTrial(
                "no admissible trial — loosen the bar or widen the search"
            )
        primary = self.primary

        def _lower_primary(a: TrialRecord, b: TrialRecord) -> Verdict:
            va = cast("dict[str, float]", a.scores)[primary]
            vb = cast("dict[str, float]", b.scores)[primary]
            if va < vb:
                return Verdict.A_WINS
            if vb < va:
                return Verdict.B_WINS
            return Verdict.TIE

        policy: LexicographicPolicy[TrialRecord] = LexicographicPolicy(
            (Criterion(primary, _lower_primary),)
        )
        return policy.sort(ok)
