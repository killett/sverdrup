"""The spanning-tree hand-forward driver: registry, finiteness, single-tile == native draw."""

from __future__ import annotations

from typing import cast

import numpy as np
import pytest

pytest.importorskip("sksparse")  # noqa: E402

from sverdrup.core.geometry import Tile, Window  # noqa: E402
from sverdrup.core.grid import GridSpec  # noqa: E402
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow  # noqa: E402
from sverdrup.core.parameters import ConstantProvider  # noqa: E402
from sverdrup.core.seeding import derive_seed  # noqa: E402
from sverdrup.distributions.blend import BlendInput, partition_weights  # noqa: E402
from sverdrup.distributions.coherent import (  # noqa: E402
    GmrfTreeKrigingSolve,
    NoiseSpec,
    select_driver,
)
from sverdrup.distributions.persisted import (  # noqa: E402
    PrecisionDistribution,
    PrecisionFields,
)
from sverdrup.distributions.reduction import GMRFPrecisionReduction  # noqa: E402
from sverdrup.methods.gmrf import MaternGMRF  # noqa: E402
from tests.unit._strip_fixtures import four_tile_corner_parts  # noqa: E402

_NOISE = NoiseSpec(method="gmrf", params_key="p", lattice_step=0.5)
_P = ConstantProvider({"range": 300.0, "variance": 0.05, "temporal_taper_scale": 5.0})


def _single_tile():
    grid = GridSpec.lonlat(np.linspace(0.0, 6.0, 7), np.linspace(0.0, 6.0, 7))
    obs = ObsWindow.from_arrays(
        np.array([3.0]),
        np.array([3.0]),
        np.array([2.0]),
        np.array([1.0]),
        DiagonalErrorModel(np.array([1e-3])),
    )
    dist = MaternGMRF().solve(obs, grid, _P, 2.0)
    unit = GMRFPrecisionReduction().reduce(dist, grid.points(2.0), None, rank=0, seed=3)
    pd = PrecisionDistribution(
        grid, cast(PrecisionFields, unit.base_fields), dist.provenance, 2.0
    )
    tile = Tile(Window((0, 6), (0, 6), (0, 0)), Window((0, 6), (0, 6), (0, 0)), grid)
    return pd, BlendInput(pd, tile), grid


def test_registry_points_to_tree_driver():
    # Behavior: the sparse-precision coherence driver is the spanning-tree hand-forward one.
    assert isinstance(select_driver("sparse-precision"), GmrfTreeKrigingSolve)


def test_crossfaded_member_is_finite_and_full_length():
    # Behavior: a 2x2 partition produces one coherent field over the output points, no NaN.
    # Bug caught: a singular kriging solve or a disconnected tree NaN-ing the seam.
    parts = four_tile_corner_parts()
    grid = parts[0].distribution.grid
    pts = grid.points(2.0)
    w = np.ones((len(parts), pts.shape[0])) / len(parts)
    out = GmrfTreeKrigingSolve().crossfaded_member(
        parts, pts, w, member_index=1, noise=_NOISE
    )
    assert out.shape == (pts.shape[0],)
    assert np.all(np.isfinite(out))


def test_single_tile_is_native_draw():
    # Behavior: with no parent, the spanning-tree sweep returns the bare native posterior draw
    #   mean + L^-T w keyed by gmrf-tile:0 — conditioning is a no-op for the root.
    # Bug caught: the root being perturbed, or the seed key drifting from the chain's.
    pd, part, grid = _single_tile()
    pts = grid.points(2.0)
    w = partition_weights([part.tile], pts)
    got = GmrfTreeKrigingSolve().crossfaded_member([part], pts, w, 4, _NOISE)
    seed = derive_seed(_NOISE.method, _NOISE.params_key, "gmrf-tile:0", 4)
    white = np.random.default_rng(seed).standard_normal(pts.shape[0])
    expected = pd.fields.mean.ravel() + pd._factor_obj().sample(white)
    np.testing.assert_allclose(got, expected, rtol=1e-9)
