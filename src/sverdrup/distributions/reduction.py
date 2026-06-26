"""Per-operator persistence strategy (spec §4c, §5.4).

Dispatch is on the LIVE operator's representation (pre-persistence) — never on method
identity. The coherence driver later dispatches on the persisted ``sampler_spec``
(post-persistence); that two-point split is deliberate (see the plan).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, cast, runtime_checkable

import numpy as np

from sverdrup.core.product import EvalPointPredictions
from sverdrup.distributions.persisted import (
    PersistedFields,
    PrecisionFields,
    eval_rows_in_grid_basis,
    reduce_with_basis,
)


@dataclass(frozen=True)
class ReducedUnit:
    """Everything extracted before the live operator goes out of scope."""

    base_fields: PersistedFields | PrecisionFields
    eval_points: EvalPointPredictions | None


@runtime_checkable
class ReductionStrategy(Protocol):
    """Reduce a live distribution to a storable representation + eval-point predictives."""

    def reduce(
        self,
        dist: object,
        grid_points: np.ndarray,
        eval_points: np.ndarray | None,
        *,
        rank: int,
        seed: int,
    ) -> ReducedUnit:
        """Return the persisted base fields and (optional) eval-point predictions."""
        ...


class LowRankReduction:
    """OI low-rank+diagonal reduction: randomized-SVD factor + exact residual."""

    def reduce(
        self,
        dist: object,
        grid_points: np.ndarray,
        eval_points: np.ndarray | None,
        *,
        rank: int,
        seed: int,
    ) -> ReducedUnit:
        """Reduce the gridded block and project eval rows into the shared SVD basis."""
        d = cast(Any, dist)
        base, basis = reduce_with_basis(
            d.mean, d.cov_op, grid_points, rank=rank, seed=seed
        )
        if eval_points is None:
            return ReducedUnit(base, None)
        mean = d.cov_op.posterior_mean(eval_points)
        var = d.cov_op.marginal_var(eval_points)
        factor, residual = eval_rows_in_grid_basis(
            d.cov_op, eval_points, grid_points, basis
        )
        return ReducedUnit(
            base,
            EvalPointPredictions(
                eval_points, mean, var, samples=None, factor=factor, residual=residual
            ),
        )


class EmpiricalReduction:
    """Ensemble (Method 0) empirical reduction: sample mean/variance, no factor."""

    sampler_spec = (
        "lowrank+diag"  # Phase-2 default; retagged "perturb-ensemble" in Task 10
    )

    def reduce(
        self,
        dist: object,
        grid_points: np.ndarray,
        eval_points: np.ndarray | None,
        *,
        rank: int,
        seed: int,
    ) -> ReducedUnit:
        """Reduce an ensemble to sample mean/variance and nearest-node eval predictives."""
        d = cast(Any, dist)
        flat = d.samples.reshape(d.samples.shape[0], -1)
        var = flat.var(axis=0, ddof=1)
        base = PersistedFields(
            mean=d.samples.mean(axis=0),
            marginal_variance=var.reshape(d.grid.shape),
            factor=np.zeros((flat.shape[1], 0)),
            residual=var,
            rank=0,
            seed=seed,
            captured_energy=0.0,
            sampler_spec=self.sampler_spec,
        )
        if eval_points is None:
            return ReducedUnit(base, None)
        nodes = d.grid.points(d.time_days)
        idx = np.argmin(
            np.linalg.norm(eval_points[:, None, :2] - nodes[None, :, :2], axis=2),
            axis=1,
        )
        s = flat[:, idx]
        return ReducedUnit(
            base,
            EvalPointPredictions(
                eval_points, s.mean(axis=0), s.var(axis=0, ddof=1), samples=s
            ),
        )


class GMRFPrecisionReduction:
    """GMRF reduction: persist Q + permutation + exact var directly; NO low-rank factor."""

    def reduce(
        self,
        dist: object,
        grid_points: np.ndarray,
        eval_points: np.ndarray | None,
        *,
        rank: int,
        seed: int,
    ) -> ReducedUnit:
        """Persist the sparse precision + permutation + exact var (no factor materialized)."""
        from sverdrup.distributions.persisted import PrecisionFields
        from sverdrup.methods.gmrf_grid import bilinear_weights

        d = cast(Any, dist)
        op = d.cov_op
        base = PrecisionFields(
            mean=d.mean,
            precision=op.q_post,
            permutation=op._factor.permutation,
            marginal_variance=op.marginal_var(grid_points).reshape(d.grid.shape),
            seed=seed,
        )
        if eval_points is None:
            return ReducedUnit(base, None)
        mean = np.asarray(bilinear_weights(d.grid, eval_points) @ d.mean.ravel())
        var = op.marginal_var(eval_points)
        return ReducedUnit(
            base, EvalPointPredictions(eval_points, mean, var, samples=None)
        )


_REDUCTIONS: dict[str, type] = {
    "lowrank+diag": LowRankReduction,
    "sparse-precision": GMRFPrecisionReduction,
}


def select_reduction(dist: object) -> ReductionStrategy:
    """Pick the reduction by the live operator's representation (ensemble if no operator)."""
    op = getattr(dist, "cov_op", None)
    if op is None:
        return EmpiricalReduction()
    rep = getattr(op, "representation", "lowrank+diag")
    return cast(ReductionStrategy, _REDUCTIONS[rep]())
