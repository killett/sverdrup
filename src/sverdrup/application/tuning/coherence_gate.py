"""Worst-case-localized coherence reduction (invariant 6): strict MAX adjacent-seam corr-err.

The joint cross-seam coherence deficit is measured per grid-adjacent seam node pair as a
correlation-unit error (|emp_cov - ref_cov| / sqrt(sigma_a sigma_b); design §2). This reduces
those per-pair errors worst-case-localized — the strict maximum, never a median/mean, because the
deficit is a SPARSE catastrophic tail an aggregate launders (the Phase-4 anti-false-green lesson).
This is gate EVIDENCE (the feasibility predicate keys on the baked n_star_joint), never a score.
"""

from __future__ import annotations

import numpy as np


def worst_case_corr_err(per_pair_errs: np.ndarray | list[float]) -> float:
    """Return the strict MAX adjacent-seam correlation error (0.0 if there are no seams)."""
    a = np.asarray(per_pair_errs, dtype=float)
    return float(a.max()) if a.size else 0.0


def corr_err_feasible(per_pair_errs: np.ndarray | list[float], tol: float) -> bool:
    """Return True iff the worst-case adjacent-seam corr-err is within ``tol``."""
    return worst_case_corr_err(per_pair_errs) <= tol
