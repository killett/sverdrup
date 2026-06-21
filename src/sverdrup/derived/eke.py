"""Stub: eddy kinetic energy derived quantity (committed signature; body deferred — spec 6)."""

from __future__ import annotations

from typing import NoReturn

from sverdrup.core.types import Linearity


class EddyKineticEnergy:
    """Eddy kinetic energy (nonlinear in velocity; committed signature; body deferred)."""

    linearity = Linearity.NONLINEAR

    def apply(self, dist: object) -> NoReturn:
        """Not implemented in Phase 1."""
        raise NotImplementedError("Eddy-kinetic-energy body is deferred (spec 6).")
