"""Calibration metrics + the polar-void sanity assertion (spec 5.5, 5.6)."""

from __future__ import annotations

from typing import Any, cast

import numpy as np
from scipy.stats import norm  # type: ignore[import-untyped]

from regatta.core.evaluation import ContextKey, EvalContext


def reduced_chi2(mean: np.ndarray, var: np.ndarray, truth: np.ndarray) -> float:
    """Return the reduced chi-squared ``mean((truth-mean)^2 / var)`` (1.0 is calibrated)."""
    return float(np.mean((truth - mean) ** 2 / var))


def coverage(
    mean: np.ndarray, var: np.ndarray, truth: np.ndarray, k: float = 1.0
) -> float:
    """Return the empirical fraction of truth within ``k`` standard deviations."""
    sd = np.sqrt(var)
    return float(np.mean(np.abs(truth - mean) <= k * sd))


def crps_gaussian(mean: np.ndarray, var: np.ndarray, obs: np.ndarray) -> np.ndarray:
    """Return the closed-form Gaussian CRPS for each ``obs`` under ``N(mean, var)``."""
    sd = np.sqrt(var)
    z = (obs - mean) / sd
    val = sd * (z * (2 * norm.cdf(z) - 1) + 2 * norm.pdf(z) - 1.0 / np.sqrt(np.pi))
    return np.asarray(val)


def pit(mean: np.ndarray, var: np.ndarray, truth: np.ndarray) -> np.ndarray:
    """Return the probability-integral-transform values (uniform iff calibrated)."""
    return np.asarray(norm.cdf((truth - mean) / np.sqrt(var)))


def assert_relaxes_to_prior(
    var_in_void: float, prior_var: float, frac: float = 0.5
) -> bool:
    """Check a method reports near-prior variance in a data void; small error => broken UQ.

    Args:
        var_in_void: Reported variance at a node with no nearby data.
        prior_var: The prior (climatological) variance.
        frac: Minimum fraction of the prior the void variance must reach.

    Returns:
        True if the void variance relaxes toward the prior.
    """
    return var_in_void >= frac * prior_var


class Calibration:
    """Coverage / reduced-chi2 / CRPS calibration evaluator (requires withheld obs)."""

    name = "calibration"
    required_context = frozenset({ContextKey.WITHHELD_OBS})

    def evaluate(
        self, result: dict[str, np.ndarray], context: EvalContext
    ) -> dict[str, float]:
        """Return calibration scores against the withheld observations."""
        w = cast(Any, context.items[ContextKey.WITHHELD_OBS])
        mean, var, truth = result["eval_mean"], result["eval_var"], w["values"]
        return {
            "reduced_chi2": reduced_chi2(mean, var, truth),
            "coverage_1sigma": coverage(mean, var, truth, 1.0),
            "crps": float(np.mean(crps_gaussian(mean, var, truth))),
        }
