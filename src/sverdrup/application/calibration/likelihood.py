"""Phase-8 floored MLE fitters, tail diagnostic, and safeguard (spec §4).

Model: r ~ N(0, s(x)·v + σ_obs²), where
  - s(x) = exp(x @ theta) is the calibration field (positive by construction)
  - v is the un-inflated ensemble variance interpolated on the track
  - σ_obs² = SIGMA_OBS2 is the observation-noise floor (pinned constant)
  - x is a design vector / matrix row

This module is pure numerics (numpy + scipy only).  No I/O, no xarray.

Constants are imported from `sverdrup.application.calibration.constants` and
also re-exported at module scope so that tests can monkeypatch them here
(e.g.  ``monkeypatch.setattr(_lik, "SIGMA_OBS2", 0.0)``).  All fitters read
the module-level names at call time — not at import time — so patching takes
effect immediately.

Chi-squared median constant::

    CHI2_1_MEDIAN = scipy.stats.chi2.ppf(0.5, df=1)
                  = 0.454936423119572

Pinned from scipy 1.x; source recorded in the constant definition below.

Newton Hessian (lane A, x = ones column, scalar theta).  With
p = s·v/tot and q = r2/tot::

    h = d²NLL/d(log s)² = 0.5 * sum[ p·(1-p)·(1-q) + p²·q ]

Derived by differentiating g = d(NLL)/d(log s) = 0.5·sum[p·(1-q)] with
respect to log s, using d(s)/d(log s) = s and d(tot)/d(log s) = s·v, so
that dp/d(log s) = p·(1-p) and dq/d(log s) = -p·q::

    dg/d(log s) = 0.5 * sum[ (dp/d log s)·(1-q) - p·(dq/d log s) ]
                = 0.5 * sum[ p·(1-p)·(1-q) + p²·q ]

Equivalently h = g + 0.5·sum[p²·(2q-1)]: the g term vanishes exactly at
the optimum, so an optimum-anchored test cannot detect its omission —
h is therefore verified against a finite difference of g at non-optimal
points.  The floor keeps h positive for well-conditioned data; we
additionally clamp h to 1e-12 from below to guard degenerate cases.
"""

from __future__ import annotations

import math
from typing import NamedTuple

import numpy as np
import scipy.optimize  # type: ignore[import-untyped]

from sverdrup.application.calibration.constants import (
    LBFGSB_GTOL as LBFGSB_GTOL,
)
from sverdrup.application.calibration.constants import (
    NEWTON_MAX_ITER as NEWTON_MAX_ITER,
)
from sverdrup.application.calibration.constants import (
    NEWTON_TOL as NEWTON_TOL,
)
from sverdrup.application.calibration.constants import (
    S_STAR as S_STAR,
)
from sverdrup.application.calibration.constants import (
    SIGMA_OBS2 as SIGMA_OBS2,
)

# Pinned χ²₁ median = scipy.stats.chi2.ppf(0.5, df=1).
# Source: repr(scipy.stats.chi2.ppf(0.5, 1)) evaluated 2026-07-11 on scipy
# installed in this environment.  The guard test test_chi2_median_pin_matches_scipy
# asserts exact equality so any scipy-version drift becomes a loud test failure.
CHI2_1_MEDIAN: float = 0.454936423119572

# Tail-diagnostic flag threshold
_TAIL_FLAG_RATIO: float = 1.5


# ---------------------------------------------------------------------------
# Core NLL and gradient (pinned formulas, spec §4)
# ---------------------------------------------------------------------------


def nll(
    theta: np.ndarray,
    x: np.ndarray,
    r2: np.ndarray,
    v: np.ndarray,
) -> float:
    """Floored Gaussian NLL for log s = x @ theta (spec §4).

    Args:
        theta: Parameter vector, shape (d,).
        x: Design matrix, shape (n, d).
        r2: Squared residuals r², shape (n,).
        v: Un-inflated ensemble variances, shape (n,).

    Returns:
        Scalar NLL value = 0.5 * sum(log(tot_i) + r2_i / tot_i).
    """
    s = np.exp(x @ theta)
    tot = s * v + SIGMA_OBS2
    return float(0.5 * np.sum(np.log(tot) + r2 / tot))


def grad(
    theta: np.ndarray,
    x: np.ndarray,
    r2: np.ndarray,
    v: np.ndarray,
) -> np.ndarray:
    """Gradient of the floored Gaussian NLL w.r.t. theta (spec §4).

    d(NLL)/d(theta_j) = 0.5 * sum_i [ w_i * x_{ij} ]
    where w_i = (s_i·v_i / tot_i) · (1 - r2_i / tot_i).

    Args:
        theta: Parameter vector, shape (d,).
        x: Design matrix, shape (n, d).
        r2: Squared residuals r², shape (n,).
        v: Un-inflated ensemble variances, shape (n,).

    Returns:
        Gradient array, shape (d,).
    """
    s = np.exp(x @ theta)
    tot = s * v + SIGMA_OBS2
    w = 0.5 * (s * v / tot) * (1.0 - r2 / tot)
    return np.asarray(x.T @ w)


# ---------------------------------------------------------------------------
# Lane-A: per-region 1-D Newton in log s
# ---------------------------------------------------------------------------


class NewtonResult(NamedTuple):
    """Result of a Newton MLE fit in log s.

    Attributes:
        log_s_hat: Estimated log-scale parameter.
        n_iter: Number of Newton iterations taken.
        converged: True iff |step| < NEWTON_TOL before NEWTON_MAX_ITER.
    """

    log_s_hat: float
    n_iter: int
    converged: bool


def _newton_gh(
    log_s: float,
    r2: np.ndarray,
    v: np.ndarray,
) -> tuple[float, float]:
    """Gradient and Hessian of the 1-D floored NLL at log s (lane-A specialization).

    With p = s·v/tot and q = r2/tot (tot = s·v + SIGMA_OBS2):
      g = 0.5 * sum[ p·(1-q) ]
      h = 0.5 * sum[ p·(1-p)·(1-q) + p²·q ]
    See module docstring for the derivation of h.

    Args:
        log_s: Log-scale parameter at which to evaluate.
        r2: Squared track residuals, shape (n,).
        v: Un-inflated ensemble variances at track points, shape (n,).

    Returns:
        Tuple (g, h) of the first and second derivative of the NLL
        with respect to log s.
    """
    s = math.exp(log_s)
    tot = s * v + SIGMA_OBS2
    p = s * v / tot
    q = r2 / tot
    g = 0.5 * float(np.sum(p * (1.0 - q)))
    h = 0.5 * float(np.sum(p * (1.0 - p) * (1.0 - q) + p**2 * q))
    return g, h


def fit_region_newton(r2: np.ndarray, v: np.ndarray) -> NewtonResult:
    """1-D Newton optimisation of the floored Gaussian NLL in log s (lane A).

    Initialisation is the σ_obs²=0 closed form: log(mean(r²/v)).
    When SIGMA_OBS2=0 (e.g. monkeypatched), this equals the exact MLE so
    Newton converges in one step and returns exp(log_s_hat) == mean(r2/v)
    to machine precision.

    Newton step: log_s -= g / h with (g, h) from _newton_gh:
      g = 0.5 * sum[ p·(1-q) ]
      h = 0.5 * sum[ p·(1-p)·(1-q) + p²·q ]
    where p = s·v/tot, q = r2/tot.  h is clamped to 1e-12 from below to
    guard degenerate cases.  See module docstring for the derivation.

    Args:
        r2: Squared track residuals, shape (n,).
        v: Un-inflated ensemble variances at track points, shape (n,).

    Returns:
        NewtonResult(log_s_hat, n_iter, converged).

    Raises:
        ValueError: If ``r2`` is empty.
    """
    r2 = np.asarray(r2, dtype=float)
    v = np.asarray(v, dtype=float)

    if r2.size == 0:
        raise ValueError("empty residual array")

    # Closed-form initialisation (exact MLE when sigma2=0, documented in docstring)
    log_s = math.log(float(np.mean(r2 / v)))

    converged = False
    n_iter = 0
    max_iter: int = NEWTON_MAX_ITER
    tol: float = NEWTON_TOL

    for i in range(max_iter):
        n_iter = i + 1
        g, h = _newton_gh(log_s, r2, v)
        h = max(h, 1e-12)

        step = g / h
        log_s -= step

        if abs(step) < tol:
            converged = True
            break

    return NewtonResult(log_s_hat=log_s, n_iter=n_iter, converged=converged)


# ---------------------------------------------------------------------------
# Lane-B: L-BFGS-B on the full design matrix
# ---------------------------------------------------------------------------


def fit_poly_lbfgsb(
    X: np.ndarray,
    r2: np.ndarray,
    v: np.ndarray,
) -> tuple[np.ndarray, str]:
    """L-BFGS-B optimisation of the floored Gaussian NLL on design matrix X (lane B).

    Initialisation: theta_0 = (log(S_STAR), 0, 0, ...) so that the first
    coordinate anchors the constant term near the shipped scalar and higher
    terms start at zero.

    The optimizer name and gtol are serialised in fit_id for provenance:
    e.g. ``"L-BFGS-B;gtol=1e-08"``.

    Args:
        X: Design matrix, shape (n, d).  Column 0 should be the intercept (all
            ones) so that the ``log(S_STAR)`` initialisation is meaningful.
        r2: Squared track residuals, shape (n,).
        v: Un-inflated ensemble variances at track points, shape (n,).

    Returns:
        Tuple of (theta_hat, fit_id) where:
          - theta_hat is the fitted parameter array, shape (d,).
          - fit_id is a provenance string, e.g. "L-BFGS-B;gtol=1e-08".
    """
    gtol: float = LBFGSB_GTOL
    s_star: float = S_STAR

    X = np.asarray(X, dtype=float)
    r2 = np.asarray(r2, dtype=float)
    v = np.asarray(v, dtype=float)

    d = X.shape[1]
    theta0 = np.zeros(d)
    theta0[0] = math.log(s_star)

    result = scipy.optimize.minimize(
        fun=nll,
        x0=theta0,
        args=(X, r2, v),
        method="L-BFGS-B",
        jac=grad,
        options={"gtol": gtol},
    )

    # Serialize as "1e-08" style (no leading coefficient when it is 1.0)
    fit_id = f"L-BFGS-B;gtol={gtol:g}"
    return result.x, fit_id


# ---------------------------------------------------------------------------
# Tail diagnostic
# ---------------------------------------------------------------------------


def tail_diagnostic(
    r2: np.ndarray,
    v: np.ndarray,
    s_hat: float,
) -> tuple[float, bool]:
    """Check whether fitted ŝ over-disperses or under-disperses the tail.

    Computes the median of the normalised squared residuals
    χ²_i = r²_i / (ŝ·v_i + σ_obs²) and compares it to the χ²₁ theoretical
    median CHI2_1_MEDIAN ≈ 0.4549.

    A ratio ≥ 1.5 indicates that the median normalised residual is too large
    (the field is under-estimating variance), and the flag is raised as a
    report-only diagnostic (no exception thrown).

    Args:
        r2: Squared track residuals, shape (n,).
        v: Un-inflated ensemble variances, shape (n,).
        s_hat: Fitted scalar calibration value (positive).

    Returns:
        Tuple (ratio, flagged) where:
          - ratio = median(chi2) / CHI2_1_MEDIAN
          - flagged is True iff ratio >= 1.5
    """
    sigma2: float = SIGMA_OBS2
    r2 = np.asarray(r2, dtype=float)
    v = np.asarray(v, dtype=float)

    tot = s_hat * v + sigma2
    chi2 = r2 / tot
    ratio = float(np.median(chi2)) / CHI2_1_MEDIAN
    flagged = ratio >= _TAIL_FLAG_RATIO
    return ratio, flagged


# ---------------------------------------------------------------------------
# Safeguard
# ---------------------------------------------------------------------------


def assert_beats_scalar(nll_fit: float, nll_s_star: float) -> None:
    """Raise RuntimeError if the fitted NLL exceeds the s*-constant NLL.

    This is the spec §4 loud safeguard: a calibration field that is worse
    than the shipped scalar constant s* should never be promoted.

    Args:
        nll_fit: NLL of the fitted calibration field on the hold-out set.
        nll_s_star: NLL of the s*-constant field on the same hold-out set.

    Raises:
        RuntimeError: If nll_fit > nll_s_star.
    """
    if nll_fit > nll_s_star:
        raise RuntimeError(
            f"Fitted NLL ({nll_fit:.6g}) exceeds s*-constant NLL ({nll_s_star:.6g}); "
            "the calibration field is worse than the shipped scalar. "
            "Refusing to promote."
        )
