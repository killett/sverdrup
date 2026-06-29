"""Effective-resolution (λx) evaluator on the blocked validation track (Phase-5).

POINTWISE / objective-eligible. Computes λx via the shared ``eval.spectral`` helper
on the validation split's along-track residuals. The VARYING per-point times arrive
on a dedicated ``eval_times`` channel (float days since the named ``EPOCH``, the
pipeline-native time convention); this evaluator reconstructs datetime64 from them so
that both this internal path and the locked-test path feed the shared helper an
identical datetime64 time representation (invariant 10 — the track is the only thing
that varies between the two call sites). It NEVER reaches into the locked-test
scoring harness — only the track handed to it in ``result``/``context``.
"""

from __future__ import annotations

from typing import Any, cast

import numpy as np

from sverdrup.core.evaluation import ContextKey, EvalContext, MetricScope
from sverdrup.eval.spectral import effective_resolution_lambda_x
from sverdrup.validation.input_adapter import EPOCH

_US_PER_DAY = 86_400_000_000


def _days_to_datetime64(days: np.ndarray) -> np.ndarray:
    """Reconstruct datetime64[us] from float days since EPOCH.

    Exactly inverts ``input_adapter._days_since_epoch`` to microsecond precision
    (lossless over the challenge year), so the reconstructed times match the
    locked-test path's native datetime64 and λx segmentation (gap-based) is identical.
    """
    us = np.round(np.asarray(days, dtype=float) * _US_PER_DAY).astype("int64")
    out = EPOCH.astype("datetime64[us]") + us.astype("timedelta64[us]")
    return np.asarray(out)


class EffectiveResolution:
    """λx (effective resolution) on the blocked validation track."""

    name = "effective_resolution"
    required_context = frozenset({ContextKey.WITHHELD_OBS, ContextKey.ORBIT_GEOMETRY})
    metric_scope = MetricScope.POINTWISE

    def evaluate(self, result: object, context: EvalContext) -> dict[str, float]:
        """Return ``{"lambda_x": …}`` from the along-track validation residuals."""
        r = cast(Any, result)
        locs = np.asarray(r["eval_locations"])  # (k, 3) = (lon, lat, unused time col)
        times = _days_to_datetime64(r["eval_times"])  # varying per-point times
        observed = np.asarray(
            cast(Any, context.items[ContextKey.WITHHELD_OBS])["values"]
        )
        mapped = np.asarray(r["eval_mean"])
        lx = effective_resolution_lambda_x(
            times, locs[:, 1], locs[:, 0], observed, mapped
        )
        return {"lambda_x": lx}
