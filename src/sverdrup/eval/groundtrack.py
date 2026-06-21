"""Intrinsic ground-track-artifact metric: spectral power at the track-spacing wavenumber."""

from __future__ import annotations

from typing import Any, cast

import numpy as np

from sverdrup.core.evaluation import ContextKey, EvalContext


class GroundTrack:
    """Reference-free metric: relative spectral power at the orbit track wavenumber."""

    name = "groundtrack"
    required_context = frozenset({ContextKey.ORBIT_GEOMETRY})

    def __init__(self, track_wavenumber: int = 8) -> None:
        """Store the track wavenumber to probe.

        Args:
            track_wavenumber: The along-row wavenumber where track artifacts concentrate.
        """
        self.k = track_wavenumber

    def evaluate(self, result: object, context: EvalContext) -> dict[str, float]:
        """Return the relative spectral power at the track wavenumber."""
        r = cast(Any, result)
        field = np.asarray(r["field"])
        spec = (
            np.abs(np.fft.rfft(field - field.mean(axis=1, keepdims=True), axis=1)) ** 2
        )
        power = spec.mean(axis=0)
        k = min(self.k, power.size - 1)
        return {"track_power": float(power[k] / (power.sum() + 1e-12))}
