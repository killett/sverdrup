"""Reference-agnostic evaluator registry (invariant 9; spec 5.6)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Protocol, runtime_checkable


class ContextKey(Enum):
    """A capability/reference available in an evaluation context."""

    TRUTH = auto()
    WITHHELD_OBS = auto()
    ORBIT_GEOMETRY = auto()
    PHYSICAL_CONSTANTS = auto()


@dataclass
class EvalContext:
    """The references/capabilities available to evaluators for one run."""

    items: dict[ContextKey, object]

    def keys(self) -> set[ContextKey]:
        """Return the set of available context keys."""
        return set(self.items)


@runtime_checkable
class Evaluator(Protocol):
    """A scoring function that requires a declared subset of context keys."""

    name: str
    required_context: frozenset[ContextKey]

    def evaluate(self, result: object, context: EvalContext) -> dict[str, float]:
        """Return named scores for ``result`` given ``context``."""
        ...


@dataclass
class Objective:
    """Vector-valued tuning objective (no baked-in scalarization)."""

    scores: dict[str, float]


class Registry:
    """Holds evaluators and filters them by available context (reference-agnostic)."""

    def __init__(self, evaluators: list[Evaluator]) -> None:
        """Store the evaluator list.

        Args:
            evaluators: The evaluators to register.
        """
        self._evaluators = list(evaluators)

    def applicable(self, context_keys: set[ContextKey]) -> list[Evaluator]:
        """Return evaluators whose required context is a subset of ``context_keys``.

        Args:
            context_keys: The available context keys.

        Returns:
            The applicable evaluators.
        """
        return [e for e in self._evaluators if e.required_context <= set(context_keys)]

    def run(self, result: object, context: EvalContext) -> dict[str, float]:
        """Run every applicable evaluator and merge their scores.

        Args:
            result: The result object under evaluation.
            context: The available references/capabilities.

        Returns:
            The merged score dictionary.
        """
        out: dict[str, float] = {}
        for ev in self.applicable(context.keys()):
            out.update(ev.evaluate(result, context))
        return out
