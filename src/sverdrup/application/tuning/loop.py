"""The autotune orchestration loop: gate -> solve+score -> constrained rank (spec §4)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sverdrup.application.tuning.feasibility import FeasibilityPredicate, TileGeometry
from sverdrup.application.tuning.objective import (
    ConstrainedObjective,
    NoAdmissibleTrial,
)
from sverdrup.application.tuning.strategy import SearchStrategy
from sverdrup.application.tuning.trial import Trial, TrialHistory, TrialRecord
from sverdrup.core.parameters import ParameterSpace
from sverdrup.core.types import UncertaintyCapability
from sverdrup.eval.spectral import ShortTrackError, UnresolvedScaleError


class TrialScorer(Protocol):
    """Solve one trial and return its POINTWISE scores on the validation split.

    Implemented for real in Task 11 (executor + blocked-validation eval). The loop
    depends only on this seam, so the gate/registry discipline is testable without
    a real solve, and ``their_eval`` is structurally unreachable from here.
    """

    def score(
        self,
        method_name: str,
        params: dict[str, float],
        split: object,
        seed: int,
        window: object,
    ) -> dict[str, float]:
        """Return the trial's POINTWISE scores on the validation split."""
        ...


@dataclass
class TuningResult:
    """The winning record (if any) and the full seeded history."""

    winner: TrialRecord | None
    history: TrialHistory


def tune(
    *,
    method_name: str,
    space: ParameterSpace,
    strategy: SearchStrategy,
    predicate: FeasibilityPredicate,
    objective: ConstrainedObjective,
    scorer: TrialScorer,
    split: object,
    seed: int,
    window: object,
    tile_geometry: TileGeometry,
    required_capabilities: frozenset[UncertaintyCapability],
    rounds: int = 1,
    on_empty: str = "raise",
) -> TuningResult:
    """Run the constrained search and return the winner + history.

    Order per trial (spec §4): (1) feasibility gate — excluded BEFORE any solve;
    (2) solve+score on the blocked validation split (POINTWISE only, via the scorer);
    (3) constrained ranking. ``their_eval`` is never imported here.

    Args:
        method_name: The method whose ``parameter_space`` is being searched.
        space: The parameter space to propose within.
        strategy: The (seeded) proposal strategy.
        predicate: The hard feasibility barrier, applied before any solve.
        objective: The constrained objective used to rank feasible+admissible trials.
        scorer: The seam that solves a trial and returns its POINTWISE scores.
        split: The data split (its ``id`` labels the trial).
        seed: The search seed (recorded for determinism).
        window: The evaluation window (its ``id`` labels the trial).
        tile_geometry: The geometry the feasibility predicate keys on.
        required_capabilities: The uncertainty capabilities the mode requires.
        rounds: Number of propose/score rounds.
        on_empty: ``"raise"`` (default) re-raises ``NoAdmissibleTrial``;
            ``"return_history"`` returns ``winner=None`` (used to inspect an
            all-infeasible run in tests/Stage C).

    Returns:
        The winning record (or ``None`` when empty and ``on_empty='return_history'``)
        plus the full seeded history.
    """
    history = TrialHistory(seed=seed)
    split_id = getattr(split, "id", "split0")
    window_id = getattr(window, "id", "tile0")
    for _ in range(rounds):
        for params in strategy.propose(space, history):
            trial = Trial(method_name, params, split_id, seed, window_id)
            if not predicate.feasible(params, tile_geometry, required_capabilities):
                history.records.append(
                    TrialRecord(trial, scores=None, feasible=False)
                )  # HARD BARRIER: no solve, no score
                continue
            try:
                scores = scorer.score(method_name, params, split, seed, window)
            except (UnresolvedScaleError, ShortTrackError) as exc:
                # Feasible-but-unscorable: a degenerate/too-short trial. Recorded with
                # its reason and skipped — the sweep tolerates bad samples. NOTE the
                # catch is NARROW (named domain errors only): real bugs must propagate.
                history.records.append(
                    TrialRecord(
                        trial,
                        scores=None,
                        feasible=True,
                        exclusion_reason=type(exc).__name__,
                    )
                )
                continue
            history.records.append(TrialRecord(trial, scores=scores, feasible=True))
    try:
        ranked = objective.rank(history.feasible_scored())
    except NoAdmissibleTrial:
        if on_empty == "return_history":
            return TuningResult(winner=None, history=history)
        raise
    return TuningResult(winner=ranked[0], history=history)
