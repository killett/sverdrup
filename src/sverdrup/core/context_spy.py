"""Read-recording context items mapping (Phase-11).

Shared by the declared⇒consumed integrity test and the report-row builder
(``context_keys_used``). Tracks KEYED reads only (``__getitem__`` / ``.get``)
— membership probes and whole-dict iteration are deliberately untracked;
see tests/test_evaluator_context_integrity.py for the recorded narrowing.
"""

from __future__ import annotations

from sverdrup.core.evaluation import ContextKey


class SpyItems(dict[ContextKey, object]):
    """Items mapping that records reads (``__getitem__`` and ``.get``)."""

    def __init__(self, data: dict[ContextKey, object]) -> None:
        """Copy ``data`` and start with an empty read set.

        Args:
            data: The real context items.
        """
        super().__init__(data)
        self.reads: set[ContextKey] = set()

    def __getitem__(self, key: ContextKey) -> object:
        """Record and forward a keyed read."""
        self.reads.add(key)
        return super().__getitem__(key)

    def get(self, key: ContextKey, default: object = None) -> object:
        """Record and forward a defaulted read."""
        self.reads.add(key)
        return super().get(key, default)
