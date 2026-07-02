# tests/test_fem_agnosticism_path.py
"""AGNOSTICISM TIER #2: the whole solve->reduce->project path takes no grid shortcut on FEM.

Scope caveat (spec 0.2/7): falsifying evidence on the exercised path only.
"""

from __future__ import annotations

from typing import cast

import numpy as np
import pytest

from sverdrup.core.grid import GridSpec
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
from sverdrup.core.parameters import ConstantProvider
from sverdrup.distributions.reduction import GMRFPrecisionReduction
from sverdrup.methods import gmrf_grid
from sverdrup.methods.fem import FEMMatern
from sverdrup.methods.fem_mesh import Mesh, build_mesh
from sverdrup.methods.gmrf import GMRFCovarianceOperator
from sverdrup.methods.registry import METHODS


def _irregular_mesh() -> Mesh:
    rng = np.random.default_rng(3)
    pts = np.vstack(
        [rng.uniform(0.0, 4.0, size=(40, 2)), rng.normal(2.0, 0.3, size=(15, 2))]
    )
    return build_mesh(pts, time_days=2.0)


def _obs() -> ObsWindow:
    rng = np.random.default_rng(0)
    lon = rng.uniform(0.5, 3.5, size=10)
    lat = rng.uniform(0.5, 3.5, size=10)
    return ObsWindow.from_arrays(
        lon,
        lat,
        np.full(10, 2.0),
        rng.normal(0.0, 0.1, size=10),
        DiagonalErrorModel(np.full(10, 1e-3)),
    )


def test_fem_registered() -> None:
    # Behavior: "fem" is a registered method. Bug it catches: forgetting the registry wiring.
    assert "fem" in METHODS


def test_whole_path_takes_no_grid_shortcut(monkeypatch: pytest.MonkeyPatch) -> None:
    # Behavior: a full FEM solve->reduce->project never calls bilinear_weights (the grid read-off);
    # the FEM path holds field_shape (n_nodes,). Bug it catches: any grid shortcut on the FEM path.
    def _boom(*a: object, **k: object) -> None:
        raise AssertionError(
            "bilinear_weights called on the FEM path — grid shortcut detected"
        )

    monkeypatch.setattr(gmrf_grid, "bilinear_weights", _boom)
    mesh = _irregular_mesh()
    grid = GridSpec.lonlat(np.arange(0.0, 4.0), np.arange(0.0, 4.0))
    params = ConstantProvider(
        {"range": 150.0, "variance": 0.05, "temporal_taper_scale": 5.0}
    )
    dist = FEMMatern(mesh=mesh).solve(_obs(), grid, params, 2.0)
    cov_op = cast(GMRFCovarianceOperator, dist.cov_op)
    assert cov_op.projection.field_shape() == (mesh.n_nodes,)
    eval_pts = np.array([[1.5, 1.5, 2.0], [2.5, 2.5, 2.0]])
    unit = GMRFPrecisionReduction().reduce(
        dist, mesh.points(), eval_pts, rank=0, seed=1
    )
    assert unit.base_fields.marginal_variance.shape == (mesh.n_nodes,)


def test_end_to_end_marginal_var_exact_vs_dense() -> None:
    # Behavior: reported marginal variance through the INHERITED reduction equals dense diag(Q_post^-1).
    # Bug it catches: the operator/reduction wrapping introducing a grid-shaped error on the mesh path.
    mesh = _irregular_mesh()
    grid = GridSpec.lonlat(np.arange(0.0, 4.0), np.arange(0.0, 4.0))
    params = ConstantProvider(
        {"range": 150.0, "variance": 0.05, "temporal_taper_scale": 5.0}
    )
    dist = FEMMatern(mesh=mesh).solve(_obs(), grid, params, 2.0)
    unit = GMRFPrecisionReduction().reduce(dist, mesh.points(), None, rank=0, seed=1)
    cov_op = cast(GMRFCovarianceOperator, dist.cov_op)
    dense = np.diag(np.linalg.inv(cov_op.q_post.toarray()))
    rel = np.abs(unit.base_fields.marginal_variance - dense) / np.abs(dense)
    assert rel.max() < 1e-9
