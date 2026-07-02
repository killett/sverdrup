# tests/test_fem_boundary_payoff.py
"""C7 (secondary): the boundary-extension MECHANISM reduces near-edge variance vs the shipped grid.

Honest baseline (spec 4.2): the grid GMRF prior uses a 5-point finite-difference Laplacian with
NEUMANN (zero-flux) edges (_laplacian, gmrf_grid.py:48) — edge nodes lack outward neighbour support,
inflating their variance. FEM's boundary ring supplies that support. This demonstrates that mechanism
on a controlled fixture; it is NOT a value claim about real coasts (real data deferred, ODC dead).
"""

from __future__ import annotations

import numpy as np

from sverdrup.core.grid import GridSpec
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
from sverdrup.core.parameters import ConstantProvider
from sverdrup.methods.fem import FEMMatern
from sverdrup.methods.fem_mesh import build_mesh
from sverdrup.methods.gmrf import MaternGMRF


def _obs(seed: int = 0) -> ObsWindow:
    rng = np.random.default_rng(seed)
    lon = rng.uniform(0.5, 3.5, size=12)
    lat = rng.uniform(0.5, 3.5, size=12)
    return ObsWindow.from_arrays(
        lon,
        lat,
        np.full(12, 1.0),
        rng.normal(0.0, 0.1, size=12),
        DiagonalErrorModel(np.full(12, 1e-3)),
    )


def test_boundary_ring_reduces_near_edge_variance() -> None:
    # Behavior: a boundary-extended FEM mesh has lower marginal variance at domain-edge nodes than the
    # Neumann-edge grid at the same edge locations (the boundary-extension mechanism).
    # Bug it catches: the boundary ring not actually supplying edge support -> no mechanism.
    params = ConstantProvider(
        {"range": 200.0, "variance": 0.05, "temporal_taper_scale": 5.0}
    )
    obs = _obs()

    grid = GridSpec.lonlat(np.arange(0.0, 4.0), np.arange(0.0, 4.0))
    gdist = MaternGMRF().solve(obs, grid, params, 1.0)
    gnodes = grid.points(1.0)
    gvar = gdist.cov_op.marginal_var(gnodes)

    # FEM mesh on the SAME core node set, extended by a boundary ring one cell out.
    core = grid.points(1.0)[:, :2]
    ring = np.array(
        [[x, y] for x in (-1.0, 4.0) for y in np.linspace(-1.0, 4.0, 6)]
        + [[x, y] for y in (-1.0, 4.0) for x in np.linspace(-1.0, 4.0, 6)]
    )
    mesh = build_mesh(core, boundary_ring=ring, time_days=1.0)
    fdist = FEMMatern(mesh=mesh).solve(obs, grid, params, 1.0)
    fvar = fdist.cov_op.marginal_var(mesh.points())

    # near-boundary = domain-edge core nodes (x or y at 0 or 3)
    edge = (
        np.isclose(gnodes[:, 0], 0.0)
        | np.isclose(gnodes[:, 0], 3.0)
        | np.isclose(gnodes[:, 1], 0.0)
        | np.isclose(gnodes[:, 1], 3.0)
    )
    # map each edge core node to its FEM node (coincident, since core points are shared)
    fem_xy = mesh.points_xy
    fem_edge_var = []
    for gp in gnodes[edge]:
        idx = int(np.argmin(np.linalg.norm(fem_xy - gp[:2], axis=1)))
        fem_edge_var.append(fvar[idx])
    assert np.median(fem_edge_var) < np.median(gvar[edge]), (
        "boundary ring did not reduce near-edge variance vs the Neumann-edge grid baseline"
    )
