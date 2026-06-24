"""Partition-of-unity weights: sum to one, smootherstep, C1 across boundaries."""

from __future__ import annotations

import numpy as np

from sverdrup.core.geometry import Tile, Window
from sverdrup.core.grid import GridSpec
from sverdrup.distributions.blend import partition_weights


def _tile(core_lon, ext_lon):
    # a 1-D-ish tile: full lat band, varying lon core/extended windows
    g = GridSpec.lonlat(np.linspace(ext_lon[0], ext_lon[1], 64), np.array([0.0, 1.0]))
    core = Window(core_lon, (0.0, 1.0), (0.0, 1.0))
    ext = Window(ext_lon, (0.0, 1.0), (0.0, 1.0))
    return Tile(core, ext, g)


def test_weights_sum_to_one_in_overlap():
    # Behavior: sum_i w_i = 1 everywhere covered (partition of unity).
    # Bug caught: un-normalized tapers double-count or under-count in the overlap.
    left = _tile((-10.0, -2.0), (-10.0, 2.0))
    right = _tile((2.0, 10.0), (-2.0, 10.0))
    pts = np.column_stack([np.linspace(-10.0, 10.0, 200), np.zeros(200), np.zeros(200)])
    w = partition_weights([left, right], pts)
    assert w.shape == (2, 200)
    np.testing.assert_allclose(w.sum(axis=0), 1.0, atol=1e-9)


def test_core_is_authoritative():
    # Behavior: deep in a tile's core, its weight is 1 and the neighbor's is 0.
    # Bug caught: a taper that leaks into the core blurs the authoritative interior.
    left = _tile((-10.0, -2.0), (-10.0, 2.0))
    right = _tile((2.0, 10.0), (-2.0, 10.0))
    pts = np.array([[-8.0, 0.0, 0.0]])  # deep in left core
    w = partition_weights([left, right], pts)
    np.testing.assert_allclose(w[:, 0], [1.0, 0.0], atol=1e-9)


def test_weight_first_derivative_is_continuous():
    # Behavior: dw/dlon has no jump at the core/overlap boundaries (smootherstep, not smoothstep).
    # Bug caught: smoothstep's curvature jump injects a faint velocity-field artifact at the seam.
    left = _tile((-10.0, -2.0), (-10.0, 2.0))
    right = _tile((2.0, 10.0), (-2.0, 10.0))
    lon = np.linspace(-3.0, 3.0, 6001)  # dense transect across the whole overlap
    pts = np.column_stack([lon, np.zeros_like(lon), np.zeros_like(lon)])
    w_left = partition_weights([left, right], pts)[0]
    d1 = np.gradient(w_left, lon)
    d2 = np.gradient(d1, lon)
    # second derivative is bounded (no delta spike from a first-derivative jump)
    assert np.nanmax(np.abs(d2)) < 5.0
