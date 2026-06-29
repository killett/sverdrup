"""Shared normalized-RMSE skill score (the leaderboard µ FORM; higher is better).

NOTE: the published challenge µ is the vendored, AREA-BINNED ``compute_stats`` value
(the locked-test harness). This helper is the same nrmse FORM at track granularity,
used for the per-trial admissibility floor on the blocked validation split. The
Stage-A gate (Task 11) empirically confirms the internal ``mu_score`` tracks the
vendored acceptance µ; if scales diverge there, the floor is recalibrated at the gate.
"""

from __future__ import annotations

import numpy as np


def leaderboard_nrmse(observed: np.ndarray, predicted: np.ndarray) -> float:
    """Return ``max(0, 1 - rms(observed-predicted)/rms(observed))`` (higher is better)."""
    observed = np.asarray(observed, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    rms_signal = float(np.sqrt(np.mean(observed**2)))
    if rms_signal == 0.0:
        return 0.0
    rms_resid = float(np.sqrt(np.mean((observed - predicted) ** 2)))
    return float(max(0.0, 1.0 - rms_resid / rms_signal))
