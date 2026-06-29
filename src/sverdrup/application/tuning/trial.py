"""Tuner value objects: Trial, TrialRecord, TrialHistory (Phase-5)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Trial:
    """One proposed (method, params) evaluated on a window/split with a seed."""

    method_name: str
    params: dict[str, float]
    split_id: str
    seed: int
    window_id: str


@dataclass(frozen=True)
class TrialRecord:
    """A trial plus its marginal scores; ``scores is None`` iff excluded by the gate."""

    trial: Trial
    scores: dict[str, float] | None
    feasible: bool


@dataclass
class TrialHistory:
    """Seeded history of all trials (feasible and excluded)."""

    seed: int
    records: list[TrialRecord] = field(default_factory=list)

    def feasible_scored(self) -> list[TrialRecord]:
        """Return feasible records that carry scores."""
        return [r for r in self.records if r.feasible and r.scores is not None]
