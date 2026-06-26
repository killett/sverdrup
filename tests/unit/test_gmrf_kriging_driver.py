"""GMRF kriging-conditioning coherence driver (Task 9b): forward-sweep, values-not-seeds.

These pin the mechanism: overlapping distinct-Q tiles must AGREE exactly on shared nodes
(coherence), single tiles must reduce to the bare native draw, and a too-thin overlap must
trip the Q-separator precondition (the boundary of validity, proven by 9c's negative control).
"""

from __future__ import annotations

from typing import cast

import numpy as np
import pytest

pytest.importorskip("sksparse")  # noqa: E402

from sverdrup.core.geometry import Tile, Window  # noqa: E402
from sverdrup.core.grid import GridSpec  # noqa: E402
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow  # noqa: E402
from sverdrup.core.parameters import ConstantProvider  # noqa: E402
from sverdrup.distributions.blend import BlendInput, partition_weights  # noqa: E402
from sverdrup.distributions.coherent import (  # noqa: E402
    GmrfKrigingSolve,
    NoiseSpec,
    diagonal_noise,
)
from sverdrup.distributions.persisted import (  # noqa: E402
    PrecisionDistribution,
    PrecisionFields,
)
from sverdrup.distributions.reduction import GMRFPrecisionReduction  # noqa: E402
from sverdrup.methods.gmrf import MaternGMRF  # noqa: E402

_P = ConstantProvider({"range": 300.0, "variance": 0.05, "temporal_taper_scale": 5.0})
_NOISE = NoiseSpec(method="gmrf", params_key="p", lattice_step=0.5)


def _pd(lon, lat, obsval):
    grid = GridSpec.lonlat(lon, lat)
    obs = ObsWindow.from_arrays(
        np.array([float(lon.mean())]),
        np.array([float(lat.mean())]),
        np.array([2.0]),
        np.array([obsval]),
        DiagonalErrorModel(np.array([1e-3])),
    )
    dist = MaternGMRF().solve(obs, grid, _P, 2.0)
    unit = GMRFPrecisionReduction().reduce(dist, grid.points(2.0), None, rank=0, seed=3)
    return PrecisionDistribution(
        grid, cast(PrecisionFields, unit.base_fields), dist.provenance, 2.0
    )


def _two_distinct_tiles(r_ext=(4.0, 10.0)):
    lat = np.arange(0.0, 5.0)
    pd_l = _pd(np.arange(0.0, 7.0), lat, 1.0)  # lon 0..6
    pd_r = _pd(np.arange(4.0, 11.0), lat, 2.0)  # lon 4..10, distinct obs -> distinct Q
    tile_l = Tile(
        Window((0, 5), (0, 4), (0, 0)), Window((0, 6), (0, 4), (0, 0)), pd_l.grid
    )
    tile_r = Tile(
        Window((5, 10), (0, 4), (0, 0)), Window(r_ext, (0, 4), (0, 0)), pd_r.grid
    )
    return [BlendInput(pd_l, tile_l), BlendInput(pd_r, tile_r)]


def test_single_tile_reduces_to_native_draw():
    # Behavior: with no shared boundary, the kriging sweep returns the bare native posterior
    #   draw mean + L^-T w — conditioning is a no-op when targets are empty.
    # Bug caught: a sweep that perturbs the interior even with nothing to condition on.
    grid = GridSpec.lonlat(np.linspace(0.0, 6.0, 7), np.linspace(0.0, 6.0, 7))
    pd = _pd(grid.x, grid.y, 1.0)
    tile = Tile(Window((0, 6), (0, 6), (0, 0)), Window((0, 6), (0, 6), (0, 0)), grid)
    pts = grid.points(2.0)
    w = partition_weights([tile], pts)
    got = GmrfKrigingSolve().crossfaded_member(
        [BlendInput(pd, tile)], pts, w, 4, _NOISE
    )
    white = diagonal_noise(pts, 4, _NOISE)
    expected = pd.fields.mean.ravel() + pd._factor_obj().sample(white)
    np.testing.assert_allclose(got, expected, rtol=1e-9)


def test_overlapping_tiles_agree_exactly_on_shared_nodes():
    # Behavior: after the forward sweep, the two distinct-Q tiles' corrected node fields are
    #   IDENTICAL on their shared (overlap) nodes — exact conditioning on handed-forward values.
    # Bug caught: the native shared-w defect (overlap corr ~0) this whole rework replaces.
    parts = _two_distinct_tiles()
    driver = GmrfKrigingSolve()
    corrected = driver._sweep(parts, 2.0, member_index=7, noise=_NOISE)
    cl, cr = corrected
    ptl = parts[0].distribution.grid.points(2.0)
    ptr = parts[1].distribution.grid.points(2.0)
    kl = {(round(p[0], 6), round(p[1], 6)): i for i, p in enumerate(ptl)}
    kr = {(round(p[0], 6), round(p[1], 6)): i for i, p in enumerate(ptr)}
    shared = sorted(set(kl) & set(kr))
    assert len(shared) >= 10  # the 3-column x 5-row overlap strip really is shared
    vl = np.array([cl[kl[k]] for k in shared])
    vr = np.array([cr[kr[k]] for k in shared])
    np.testing.assert_allclose(vl, vr, rtol=1e-9, atol=1e-12)


def test_kriging_correction_preserves_marginal_under_correct_premise():
    # Behavior: the kriging correction the driver applies preserves the tile's EXACT posterior
    #   marginal variance WHEN the conditioned-on values are drawn from that same law (the
    #   kriging theorem's premise). Cross-seam validity vs a GLOBAL reference is 9c's oracle;
    #   this isolates the correction algebra the sweep relies on.
    # Bug caught: a correction that matches the boundary while distorting the interior law.
    pd = _pd(np.arange(0.0, 7.0), np.arange(0.0, 5.0), 1.0)
    fac = pd._factor_obj()
    mean = pd.fields.mean.ravel()
    n = mean.size
    s_idx = np.array([0, 1, 7, 8])  # a 2x2 boundary strip
    cols = pd.posterior_cov_columns(s_idx)
    sigma_ss = cols[s_idx, :]
    rng = np.random.default_rng(0)
    draws = np.empty((4000, n))
    for m in range(4000):
        x_u = mean + fac.sample(rng.standard_normal(n))
        x_ref = mean + fac.sample(rng.standard_normal(n))  # target ~ same law
        draws[m] = x_u + cols @ np.linalg.solve(sigma_ss, x_ref[s_idx] - x_u[s_idx])
    np.testing.assert_allclose(
        draws.var(axis=0), pd.marginal_variance().ravel(), rtol=0.1
    )


def test_separator_precondition_raises_on_thin_overlap():
    # Behavior: a 1-column overlap (< stencil reach 2) trips the Q-separator assertion — the
    #   handed-forward boundary fails to cut the graph, so the joint law would be wrong.
    # Bug caught: silently accepting a too-thin halo and emitting an invalid joint sample.
    parts = _two_distinct_tiles(r_ext=(6.0, 10.0))  # overlap shrinks to lon=6 only
    pts = parts[0].distribution.grid.points(
        2.0
    )  # any support; raise happens in the sweep
    w = partition_weights([p.tile for p in parts], pts)
    with pytest.raises(AssertionError, match="separat"):
        GmrfKrigingSolve().crossfaded_member(parts, pts, w, 1, _NOISE)
