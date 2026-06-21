"""Adapters lifting poorer methods to the full predictive-distribution interface (spec 5.3)."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from sverdrup.core.grid import GridSpec
from sverdrup.core.observations import ObsWindow
from sverdrup.core.provenance import (
    KnownBias,
    TransformKind,
    UncertaintyProvenance,
    UncertaintyTransform,
)
from sverdrup.core.seeding import derive_seed
from sverdrup.core.types import CovFidelity, Field, Points, Seed, UncertaintyCapability
from sverdrup.distributions.ensemble import EnsemblePredictiveDistribution
from sverdrup.distributions.gaussian import GaussianPredictiveDistribution

PointFn = Callable[[ObsWindow, GridSpec, float], Field]


def perturb_and_ensemble(
    point_fn: PointFn,
    obs: ObsWindow,
    grid: GridSpec,
    *,
    m: int,
    seed: Seed,
    time_days: float,
) -> EnsemblePredictiveDistribution:
    """Lift a deterministic POINT method by perturbing observations and re-solving.

    Each member perturbs the observations by their per-obs error std and re-runs
    ``point_fn``. Member seeds derive deterministically from ``seed`` and the member
    index, so the ensemble is reproducible across calls (independent of object ids).

    Args:
        point_fn: A deterministic ``(obs, grid, time_days) -> field`` reconstruction.
        obs: The observation window to perturb.
        grid: The output grid.
        m: Number of ensemble members.
        seed: Base seed driving the perturbations.
        time_days: The output time in days.

    Returns:
        An ``EnsemblePredictiveDistribution`` with synthesized POINT provenance.
    """
    coords = obs.coords()
    lon, lat, time = coords[:, 0], coords[:, 1], coords[:, 2]
    base_vals = obs.values()
    std = np.sqrt(np.diag(obs.error_model.as_matrix(len(obs))))
    members = np.empty((m, *grid.shape))
    for i in range(m):
        rng = np.random.default_rng(derive_seed("perturb", str(seed), "ensemble", i))
        perturbed = ObsWindow.from_arrays(
            lon,
            lat,
            time,
            base_vals + rng.standard_normal(base_vals.shape) * std,
            obs.error_model,
        )
        members[i] = point_fn(perturbed, grid, time_days)
    prov = UncertaintyProvenance(
        native_capability=UncertaintyCapability.POINT,
        transformations=[
            UncertaintyTransform(
                kind=TransformKind.INPUT_PERTURBATION,
                known_bias=KnownBias.UNDER_DISPERSED_IN_VOIDS,
                params={"m": m},
            )
        ],
    )
    return EnsemblePredictiveDistribution(grid, members, prov, time_days)


class _DiagonalOperator:
    """A zero-cross-covariance operator carrying only per-node marginal variance."""

    fidelity = CovFidelity.LOW_RANK

    def __init__(self, variance_flat: np.ndarray) -> None:
        """Store the flattened per-node variance.

        Args:
            variance_flat: The ``(ngrid,)`` marginal variances.
        """
        self._v = variance_flat

    def cov(self, a: Points, b: Points) -> np.ndarray:
        """Return zero cross-covariance (diagonal-only operator)."""
        return np.zeros((a.shape[0], b.shape[0]))

    def marginal_var(self, a: Points) -> np.ndarray:
        """Return the per-node marginal variance for the first ``len(a)`` nodes."""
        return np.asarray(self._v[: a.shape[0]])

    def posterior_sample(self, s: Points, seed: Seed, m: int) -> np.ndarray:
        """Return ``m`` independent zero-mean diagonal draws, shape ``(m, len(s))``."""
        rng = np.random.default_rng(seed)
        return np.asarray(
            rng.standard_normal((m, s.shape[0])) * np.sqrt(self._v[: s.shape[0]])
        )


def diagonal_gaussian(
    mean: Field, variance_field: Field, grid: GridSpec, *, time_days: float
) -> GaussianPredictiveDistribution:
    """Lift a MARGINAL_VARIANCE method to a Gaussian with a diagonal covariance operator.

    Args:
        mean: The mean field, shape ``(ny, nx)``.
        variance_field: The per-node marginal variance, shape ``(ny, nx)``.
        grid: The output grid.
        time_days: The output time in days.

    Returns:
        A Gaussian distribution with a diagonal operator and an inflation transform.
    """
    prov = UncertaintyProvenance(
        native_capability=UncertaintyCapability.MARGINAL_VARIANCE,
        transformations=[UncertaintyTransform(kind=TransformKind.DIAGONAL_INFLATION)],
    )
    return GaussianPredictiveDistribution(
        grid, mean, _DiagonalOperator(variance_field.ravel()), prov, time_days
    )
