"""Accuracy evaluator (vs truth in OSSE, vs withheld obs in OSE); spec 5.6."""

from __future__ import annotations

from typing import Any, cast

import numpy as np

from regatta.core.evaluation import ContextKey, EvalContext


class Accuracy:
    """RMSE vs truth (OSSE) or withheld obs (OSE); gated at runtime on available context."""

    name = "accuracy"
    # Fires if either TRUTH or WITHHELD_OBS is present (checked at runtime).
    required_context: frozenset[ContextKey] = frozenset()

    def evaluate(self, result: object, context: EvalContext) -> dict[str, float]:
        """Return ``{"rmse": ...}`` using exact eval-point means (OSE) or truth (OSSE)."""
        r = cast(Any, result)
        keys = context.keys()
        if ContextKey.WITHHELD_OBS in keys:
            truth = cast(Any, context.items[ContextKey.WITHHELD_OBS])["values"]
            pred = r["eval_mean"]
        elif ContextKey.TRUTH in keys:
            truth = cast(Any, context.items[ContextKey.TRUTH])["field"].ravel()
            pred = r["grid_mean"].ravel()
        else:
            return {}
        return {"rmse": float(np.sqrt(np.mean((pred - truth) ** 2)))}
