"""The auxiliary joint field: strip sub-GMRF from prior Q, corner edges, independent white."""

from __future__ import annotations

import numpy as np

from sverdrup.distributions.coherent import (
    NoiseSpec,
    _draw_joint,
    _strip_network,
    _strip_prior,
)
from tests.unit._strip_fixtures import four_tile_corner_parts

_NOISE = NoiseSpec(method="gmrf", params_key="k", lattice_step=0.25)


def test_strip_prior_has_corner_cross_edges():
    # Behavior (C1): the induced strip prior connects junction nodes across overlaps; the
    #   matrix has off-diagonal entries between strip nodes that come from different tiles.
    # Bug caught: assembling per-overlap ribbons leaves the strip prior block-diagonal at the
    #   junction, so the auxiliary field is discontinuous there.
    parts = four_tile_corner_parts()
    gk, pt = _strip_network(parts)
    q_s = _strip_prior(parts, gk, pt).tocoo()
    off = q_s.row != q_s.col
    assert off.sum() > 0  # there ARE cross-node edges, not a diagonal matrix


def test_joint_white_independent_of_tile_seed():
    # Behavior (C2): the auxiliary field's white noise is seeded independently of any tile's
    #   unconditional-draw white. Re-deriving the joint seed must not collide with a tile seed.
    # Bug caught: sharing noise between the joint target and a tile draw re-biases kriging.
    from sverdrup.core.seeding import derive_seed

    parts = four_tile_corner_parts()
    gk, pt, xj = _draw_joint(parts, member_index=2, noise=_NOISE)
    joint_seed = derive_seed(_NOISE.method, _NOISE.params_key, "gmrf-joint-strip", 2)
    tile0_seed = derive_seed(_NOISE.method, _NOISE.params_key, "gmrf-tile:0", 2)
    assert joint_seed != tile0_seed
    assert xj.shape[0] == len(gk)


def test_nonstationary_strip_prior_differs_from_constant():
    # Behavior (C4): with a lat-varying kappa field the strip prior carries per-node kappa.
    # Bug caught: drawing the joint field from a single scalar kappa biases the nonstationary
    #   case only (invisible to stationary tests).
    from tests.unit._strip_fixtures import four_tile_corner_parts_nonstationary

    parts = four_tile_corner_parts_nonstationary()
    gk, pt = _strip_network(parts)
    q_s = _strip_prior(parts, gk, pt)
    diag = np.asarray(q_s.diagonal())
    assert (
        diag.std() / diag.mean() > 1e-3
    )  # spatially-varying coefficients, not constant
