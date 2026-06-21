"""Stub: transport derived quantity (committed signature; body deferred — spec 6)."""

from __future__ import annotations

from typing import NoReturn

from regatta.core.types import Linearity


class Transport:
    """Volume/mass transport across a section (committed signature; body deferred)."""

    linearity = Linearity.LINEAR

    def apply(self, dist: object) -> NoReturn:
        """Not implemented in Phase 1."""
        raise NotImplementedError("Transport body is deferred (spec 6).")
