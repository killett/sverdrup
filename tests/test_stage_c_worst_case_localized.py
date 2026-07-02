"""Coherence gated worst-case-localized (strict max), never aggregate — the anti-false-green rule."""

from __future__ import annotations

import numpy as np

from sverdrup.application.tuning.coherence_gate import (
    corr_err_feasible,
    worst_case_corr_err,
)


def test_strict_max_not_median() -> None:
    # Bug it catches: a median laundering one catastrophic seam pair (design §2: median 0.015,
    # worst 1.105 at 2x2 — the sparse catastrophic tail).
    errs = np.array([0.01, 0.02, 0.02, 1.105])
    assert worst_case_corr_err(errs) == 1.105  # strict max
    assert np.median(errs) < 0.5  # the median would have passed it
    assert (
        corr_err_feasible(errs, tol=0.5) is False
    )  # gated on the worst, not the median


def test_empty_is_feasible_sentinel() -> None:
    assert worst_case_corr_err(np.array([])) == 0.0
    assert corr_err_feasible(np.array([]), tol=0.5) is True
