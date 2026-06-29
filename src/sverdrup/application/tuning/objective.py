"""Constrained (not scalarized) multi-objective ranking (Phase-5, spec 5/§8)."""

from __future__ import annotations

from dataclasses import dataclass, field

from sverdrup.application.tuning.trial import TrialRecord

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


@dataclass(frozen=True)
class ConstrainedObjective:
    """Maximize resolution (minimize λx) subject to hard bars. No weighted-sum."""

    primary: str = "lambda_x"
    bars: tuple[HardBar, ...] = field(default_factory=_default_bars)

    def admissible(self, scores: dict[str, float]) -> bool:
        """Return True iff every hard bar passes."""
        return all(b.passes(scores) for b in self.bars)

    def rank(self, records: list[TrialRecord]) -> list[TrialRecord]:
        """Return admissible feasible records sorted ascending by the primary objective."""
        ok = [
            r
            for r in records
            if r.feasible and r.scores is not None and self.admissible(r.scores)
        ]
        if not ok:
            raise NoAdmissibleTrial(
                "no admissible trial — loosen the bar or widen the search"
            )
        return sorted(ok, key=lambda r: r.scores[self.primary])  # type: ignore[index]
