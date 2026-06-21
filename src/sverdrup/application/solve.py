"""solve_unit: run one windowed solve and extract everything needing the EXACT operator."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from typing import Any, cast

import numpy as np

from sverdrup.application.uow import UnitOfWork
from sverdrup.core.grid import GridSpec
from sverdrup.core.product import EvalPointPredictions, PerTimeProduct, Product
from sverdrup.core.provenance import ProductProvenance
from sverdrup.derived.firstdifference import FirstDifference
from sverdrup.distributions.persisted import (
    PersistedDistribution,
    PersistedFields,
    reduce_to_persisted,
)
from sverdrup.methods.registry import METHODS

_DERIVED: dict[str, Callable[[], FirstDifference]] = {
    "firstdifference": lambda: FirstDifference(axis="x"),
}


def solve_unit(uow: UnitOfWork) -> Product:
    """Run the windowed solve and reduce everything needing the EXACT operator on-worker.

    For each output time: solve (operator live), reduce the base to Persisted fields,
    extract declared derived products and exact eval-point predictions, then let the
    live operator (and its Cholesky factor) go out of scope before returning.

    Args:
        uow: The unit of work to execute.

    Returns:
        A Persisted ``Product`` bundle (no live operator escapes).
    """
    method = cast(Any, METHODS[uow.method_name]())
    per_time: list[PerTimeProduct] = []
    for t in uow.output_times:
        dist = method.solve(uow.obs, uow.grid, uow.params, t)  # operator live here
        base_fields = _reduce(dist, uow)
        base = PersistedDistribution(uow.grid, base_fields, dist.provenance, t)
        derived = {
            name: _reduce_derived(_DERIVED[name](), dist, uow)
            for name in uow.derived_names
        }
        eval_pts = _eval_points(dist, uow)
        prov = ProductProvenance(
            method=uow.method_name,
            params_key=uow.params.params_key(),
            seed=uow.seed,
            split_id=uow.split_id,
            code_version=_git_version(),
            input_manifest={"window": uow.window_id},
            uncertainty=dist.provenance,
        )
        per_time.append(PerTimeProduct(t, base, derived, eval_pts, prov))
        # dist (and its operator/L) goes out of scope here — nothing exact leaks downstream.
    return Product(
        per_time=per_time,
        run_manifest={"window": uow.window_id, "method": uow.method_name},
    )


def _reduce(dist: object, uow: UnitOfWork) -> PersistedFields:
    """Reduce a live distribution to Persisted fields (matrix-free for Gaussian)."""
    d = cast(Any, dist)
    if hasattr(dist, "cov_op"):  # Gaussian: matrix-free reduction of the exact operator
        return reduce_to_persisted(
            d.mean,
            d.cov_op,
            uow.grid.points(d.time_days),
            rank=uow.rank,
            seed=uow.seed,
        )
    # Ensemble (Method 0): reduce empirically.
    flat = d.samples.reshape(d.samples.shape[0], -1)
    var = flat.var(axis=0, ddof=1)
    return PersistedFields(
        mean=d.samples.mean(axis=0),
        marginal_variance=var.reshape(uow.grid.shape),
        factor=np.zeros((flat.shape[1], 0)),
        residual=var,
        rank=0,
        seed=uow.seed,
        captured_energy=0.0,
    )


def _reduce_derived(
    operator: object, dist: object, uow: UnitOfWork
) -> PersistedDistribution:
    """Apply a derived operator (exact path, operator live) and persist its variance field."""
    d = cast(Any, dist)
    out = cast(Any, operator).apply(
        dist
    )  # exact covariance path while operator is live
    var = out.marginal_variance()
    fields = PersistedFields(
        mean=var * 0.0,
        marginal_variance=var,
        factor=np.zeros((var.size, 0)),
        residual=var.ravel(),
        rank=0,
        seed=uow.seed,
        captured_energy=1.0,
    )
    diff_grid = _shrunk_grid(uow.grid)
    return PersistedDistribution(diff_grid, fields, d.provenance, d.time_days)


def _eval_points(dist: object, uow: UnitOfWork) -> EvalPointPredictions | None:
    """Compute exact (operator) eval-point predictions, or sample-based for ensembles."""
    if uow.eval_locations is None:
        return None
    locs = uow.eval_locations
    d = cast(Any, dist)
    if hasattr(dist, "cov_op"):
        mean = d.cov_op.posterior_mean(locs)
        var = d.cov_op.marginal_var(locs)
        return EvalPointPredictions(locs, mean, var, samples=None)
    # Ensemble: sample-based eval-point predictive.
    s = _ensemble_at(dist, locs)
    return EvalPointPredictions(locs, s.mean(axis=0), s.var(axis=0, ddof=1), samples=s)


def _ensemble_at(dist: object, locs: np.ndarray) -> np.ndarray:
    """Return the ensemble member values at the nearest nodes to ``locs``."""
    d = cast(Any, dist)
    nodes = d.grid.points(d.time_days)
    idx = np.argmin(
        np.linalg.norm(locs[:, None, :2] - nodes[None, :, :2], axis=2), axis=1
    )
    return np.asarray(d.samples.reshape(d.samples.shape[0], -1)[:, idx])


def _shrunk_grid(grid: GridSpec) -> GridSpec:
    """Return the grid with one fewer column (the first-difference x-axis shape)."""
    return GridSpec(grid.x[:-1], grid.y, grid.crs)


def _git_version() -> str:
    """Return the short git HEAD hash, or ``"unknown"`` if unavailable."""
    cmd = ["git", "rev-parse", "--short", "HEAD"]
    try:
        return subprocess.check_output(cmd, text=True).strip()  # noqa: S603
    except Exception:
        return "unknown"
