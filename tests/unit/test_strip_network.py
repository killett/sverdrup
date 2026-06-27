"""The strip-network: union strip nodes + induced connectivity; corner is multiply-covered."""

from __future__ import annotations

import numpy as np
import pytest

from sverdrup.distributions.coherent import _strip_network
from tests.unit._strip_fixtures import disjoint_pair_parts, four_tile_corner_parts


def test_corner_node_is_covered_by_at_least_three_tiles():
    # Behavior (C1/C6): in a 2x2 partition the interior corner node belongs to >=3 tiles,
    #   so the induced strip graph must connect across the junction, not treat strips as
    #   independent ribbons.
    # Bug caught: assembling the strip prior per-overlap drops the corner's cross-strip edges.
    parts = four_tile_corner_parts()
    global_keys, per_tile = _strip_network(parts)
    coverage = np.array(
        [sum(pt.get(g, -1) >= 0 for pt in per_tile) for g in range(len(global_keys))]
    )
    assert coverage.max() >= 3  # the interior corner


def test_disjoint_tiles_raise_loudly():
    # Behavior (C6): adjacent tiles that share no node must fail loudly, never silently
    #   produce an empty conditioning set.
    parts = disjoint_pair_parts()
    with pytest.raises(AssertionError, match="share no strip node"):
        _strip_network(parts)
