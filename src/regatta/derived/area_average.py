"""Stub: area-average derived quantity (committed signature; body deferred — spec 6)."""

from __future__ import annotations

from typing import NoReturn

from regatta.core.types import Linearity


class AreaAverage:
    """Area-weighted spatial average (committed signature; body is a global-phase concern)."""

    linearity = Linearity.LINEAR

    def apply(self, dist: object) -> NoReturn:
        """Not implemented in Phase 1."""
        raise NotImplementedError(
            "Area-average body is a global-phase concern (spec 6)."
        )
