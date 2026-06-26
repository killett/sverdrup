"""solve_unit: run one windowed solve and extract everything needing the EXACT operator."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from typing import Any, cast

import numpy as np

from sverdrup.application.uow import UnitOfWork
from sverdrup.core.grid import GridSpec
from sverdrup.core.product import PerTimeProduct, Product
from sverdrup.core.provenance import ProductProvenance
from sverdrup.derived.firstdifference import FirstDifference
from sverdrup.distributions.persisted import (
    PersistedDistribution,
    PersistedFields,
    PrecisionDistribution,
    PrecisionFields,
)
from sverdrup.distributions.reduction import select_reduction
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
        strat = select_reduction(dist)
        unit = strat.reduce(
            dist,
            uow.grid.points(t),
            uow.eval_locations,
            rank=uow.rank,
            seed=uow.seed,
        )
        base_fields = unit.base_fields
        base: Any
        # First-class dispatch by representation: GMRF persists sparse precision, never a
        # low-rank factor, so it must wrap in a PrecisionDistribution (not PersistedDistribution).
        if isinstance(base_fields, PrecisionFields):
            base = PrecisionDistribution(uow.grid, base_fields, dist.provenance, t)
        else:
            base = PersistedDistribution(uow.grid, base_fields, dist.provenance, t)
        derived = {
            name: _reduce_derived(_DERIVED[name](), dist, uow)
            for name in uow.derived_names
        }
        prov = ProductProvenance(
            method=uow.method_name,
            params_key=uow.params.params_key(),
            seed=uow.seed,
            split_id=uow.split_id,
            code_version=_git_version(),
            input_manifest={"window": uow.window_id},
            uncertainty=dist.provenance,
        )
        per_time.append(PerTimeProduct(t, base, derived, unit.eval_points, prov))
        # dist (and its operator/L) goes out of scope here — nothing exact leaks downstream.
    return Product(
        per_time=per_time,
        run_manifest={"window": uow.window_id, "method": uow.method_name},
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
