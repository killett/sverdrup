"""Tile-adjacency graph + max-overlap spanning tree (Stage-B redesign)."""

from __future__ import annotations

import itertools

import pytest

from sverdrup.distributions.coherent import (
    _assert_tree_edge_separates,
    _max_overlap_spanning_tree,
    _tile_adjacency,
)
from tests.unit._strip_fixtures import (
    disjoint_pair_parts,
    four_tile_corner_parts,
    narrow_overlap_parts,
)


def _max_total_weight(
    adjacency: dict[tuple[int, int], set[tuple[float, float]]], n: int
) -> int:
    """Brute-force the maximum total spanning-tree weight (small graphs only)."""
    edges = list(adjacency)
    best = -1
    for combo in itertools.combinations(edges, n - 1):
        # connected + acyclic check via union-find
        root = list(range(n))

        def find(a: int, root: list[int] = root) -> int:
            while root[a] != a:
                a = root[a]
            return a

        ok = True
        for i, j in combo:
            ri, rj = find(i), find(j)
            if ri == rj:
                ok = False
                break
            root[ri] = rj
        if ok and len({find(k) for k in range(n)}) == 1:
            best = max(best, sum(len(adjacency[e]) for e in combo))
    return best


def test_spanning_tree_of_2x2_has_n_minus_1_edges_and_dropped():
    # Behavior: a 2x2 corner partition (all four tiles pairwise overlapping) yields a tree of
    #   exactly n-1=3 edges and a non-empty dropped (cycle) set.
    # Bug caught: a tree that drops a tile (disconnection) or keeps a cycle.
    parts = four_tile_corner_parts()
    adj = _tile_adjacency(parts)
    parent, order, tree_edges, dropped = _max_overlap_spanning_tree(adj, len(parts))
    assert len(tree_edges) == len(parts) - 1
    assert len(dropped) >= 1
    assert set(order) == set(range(len(parts)))  # every tile reached
    assert parent[order[0]] is None  # root has no parent


def test_spanning_tree_is_maximum_overlap():
    # Behavior: the chosen tree maximizes total shared-node weight — a higher-overlap edge is
    #   never dropped in favour of a lower-overlap tree edge.
    # Bug caught: a min-weight or arbitrary tree that inflates the dropped-edge residual.
    parts = four_tile_corner_parts()
    adj = _tile_adjacency(parts)
    _, _, tree_edges, _ = _max_overlap_spanning_tree(adj, len(parts))
    chosen = sum(len(adj[e]) for e in tree_edges)
    assert chosen == _max_total_weight(adj, len(parts))


def test_disconnected_adjacency_raises():
    # Behavior (C6): a tile sharing no usable overlap cannot be hand-forward-conditioned -> red.
    parts = disjoint_pair_parts()
    adj = _tile_adjacency(parts)
    with pytest.raises(AssertionError, match="disconnected"):
        _max_overlap_spanning_tree(adj, len(parts))


def test_narrow_overlap_is_not_an_edge():
    # Behavior: a one-column (< stencil reach) overlap is not a usable adjacency edge, so a
    #   two-tile narrow fixture is disconnected and raises.
    # Bug caught: a sub-reach seam silently admitted as a hand-forward edge.
    parts = narrow_overlap_parts()
    adj = _tile_adjacency(parts)
    assert adj == {}  # the 1-column overlap does not span the reach
    with pytest.raises(AssertionError, match="disconnected"):
        _max_overlap_spanning_tree(adj, len(parts))


def test_thin_tree_edge_asserts_loudly():
    # Behavior: forcing a sub-reach overlap as a tree edge is a loud red per edge.
    # Bug caught: the MST being handed a thin edge (only-connection case) without a guard.
    parts = narrow_overlap_parts()
    with pytest.raises(AssertionError, match="stencil reach"):
        _assert_tree_edge_separates(parts, {(0, 1)})
