# tests/test_fem_multitile.py
"""Multi-tile FEM inheritance (secondary, lowest-information): the live tree driver + agnostic envelope.

The coherence envelope is already discretization-agnostic at the predicate level (CoherenceFeasibility
keys on n_tiles + capability, no grid/mesh); this re-confirms the FEM swap doesn't break the inherited
driver and inherits that envelope verbatim.
"""

from __future__ import annotations

from typing import cast

import numpy as np

from sverdrup.application.tuning.feasibility import CoherenceFeasibility, TileGeometry
from sverdrup.core.geometry import Tile, Window
from sverdrup.core.grid import GridSpec
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
from sverdrup.core.parameters import ConstantProvider
from sverdrup.core.types import UncertaintyCapability as UC
from sverdrup.distributions.blend import BlendInput, partition_weights
from sverdrup.distributions.coherent import (
    GmrfTreeKrigingSolve,
    NoiseSpec,
    _tile_adjacency,
)
from sverdrup.distributions.persisted import PrecisionDistribution, PrecisionFields
from sverdrup.distributions.reduction import GMRFPrecisionReduction
from sverdrup.methods.fem import FEMMatern
from sverdrup.methods.fem_mesh import build_mesh

_T = 2.0
_PROV = ConstantProvider(
    {"range": 200.0, "variance": 0.05, "temporal_taper_scale": 5.0}
)


def _obs() -> ObsWindow:
    rng = np.random.default_rng(0)
    lon = rng.uniform(0.0, 10.0, size=12)
    lat = rng.uniform(0.0, 6.0, size=12)
    return ObsWindow.from_arrays(
        lon,
        lat,
        np.full(12, _T),
        rng.normal(0.0, 0.1, size=12),
        DiagonalErrorModel(np.full(12, 1e-3)),
    )


def _fem_part(
    x_lo: float, x_hi: float, core: tuple[float, float], ext: tuple[float, float]
) -> BlendInput:
    # a mesh whose nodes lie on an integer lattice in [x_lo,x_hi] x [0,5] -> adjacent tiles share
    # coincident integer nodes in their overlap (so _node_keys matches them).
    xs, ys = np.meshgrid(np.arange(x_lo, x_hi + 1.0), np.arange(0.0, 6.0))
    mesh = build_mesh(np.column_stack([xs.ravel(), ys.ravel()]), time_days=_T)
    grid = GridSpec.lonlat(np.arange(x_lo, x_hi + 1.0), np.arange(0.0, 6.0))
    dist = FEMMatern(mesh=mesh).solve(_obs(), grid, _PROV, _T)
    unit = GMRFPrecisionReduction().reduce(dist, mesh.points(), None, rank=0, seed=3)
    pd = PrecisionDistribution(
        dist.grid, cast(PrecisionFields, unit.base_fields), dist.provenance, _T
    )
    tile = Tile(
        Window(core, (0.0, 5.0), (0.0, 0.0)),
        Window(ext, (0.0, 5.0), (0.0, 0.0)),
        dist.grid,
    )
    return BlendInput(pd, tile)


def test_fem_tiles_share_nodes_and_blend_through_live_driver() -> None:
    # Behavior: two overlapping FEM tiles share coincident nodes (C6) and the LIVE GmrfTreeKrigingSolve
    # produces a finite coherent field over them (the mesh swap doesn't break the inherited driver).
    # Bug it catches: a mesh-node-index/key mismatch that empties the shared set or NaNs the sweep.
    parts = [
        _fem_part(0.0, 6.0, (0.0, 6.0), (0.0, 7.0)),
        _fem_part(4.0, 10.0, (4.0, 10.0), (3.0, 10.0)),
    ]
    adj = _tile_adjacency(parts)
    assert (0, 1) in adj and len(adj[(0, 1)]) > 0  # C6: coincident-node set non-empty

    out_pts = np.column_stack(
        [np.arange(0.0, 10.0), np.full(10, 2.0), np.full(10, _T)]
    ).astype(float)
    weights = partition_weights([p.tile for p in parts], out_pts)
    noise = NoiseSpec(method="fem", params_key="p", lattice_step=1.0)
    field = GmrfTreeKrigingSolve().crossfaded_member(
        parts, out_pts, weights, member_index=0, noise=noise
    )
    assert field.shape == (10,) and np.all(np.isfinite(field))


def test_fem_inherits_coherence_envelope_verbatim() -> None:
    # Behavior: the feasibility verdict is discretization-agnostic — a mesh TileGeometry gets the same
    # SAMPLES verdict as a grid: feasible at n_tiles=1, infeasible at n_tiles=2 (n_star_joint=1).
    # Bug it catches: FEM smuggling a different coherence envelope than the shipped predicate.
    pred = CoherenceFeasibility()
    params = {"range": 200.0}
    assert pred.feasible(
        params, TileGeometry(4.0, 200.0, "mesh", n_tiles=1), frozenset({UC.SAMPLES})
    )
    assert not pred.feasible(
        params, TileGeometry(4.0, 200.0, "mesh", n_tiles=2), frozenset({UC.SAMPLES})
    )
    # MARGINAL_VARIANCE ships regardless of tile count (worst-case flat, within marg_tol)
    assert pred.feasible(
        params,
        TileGeometry(4.0, 200.0, "mesh", n_tiles=9),
        frozenset({UC.MARGINAL_VARIANCE}),
    )
