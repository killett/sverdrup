"""Stub: geostrophic velocity derived quantity (committed signature; body deferred — spec 6)."""

from __future__ import annotations

from typing import NoReturn

from regatta.core.types import Linearity


class GeostrophicVelocity:
    """Geostrophic velocity from SSHA gradients (committed signature; body deferred)."""

    linearity = Linearity.LINEAR

    def apply(self, dist: object) -> NoReturn:
        """Not implemented in Phase 1."""
        raise NotImplementedError("Geostrophic-velocity body is deferred (spec 6).")
