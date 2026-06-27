"""Stage-B spanning-tree oracles: tree/dropped/direction/invariance, baselines measured in-test.

Fast, well-conditioned 2x2 fixture (real solved tiles). The near-singular natl60 regime is the
Task-9 gate; here we pin the CONTRACTS and the relationships, with every threshold derived from the
in-test-measured chain baseline (never a hardcoded constant).
"""

from __future__ import annotations

from typing import Any, cast

import numpy as np
import pytest

pytest.importorskip("sksparse")  # noqa: E402

from sverdrup.core.seeding import derive_seed  # noqa: E402
from sverdrup.distributions.coherent import (  # noqa: E402
    GmrfTreeKrigingSolve,
    NoiseSpec,
)
from tests.unit._tree_gate import make_2x2, make_chain  # noqa: E402

_NOISE = NoiseSpec(method="gmrf", params_key="p", lattice_step=0.5)
_SLACK = (
    0.15  # tree edges must be <= chain_baseline*(1+slack); baseline measured in-test
)
_C = 2.5  # dropped-edge relative bound, with the chain-baseline floor below
_M = 1500


def _chain_baseline() -> float:
    """The plain chain's max edge joint-cov rel-err — the accepted halo-truncation residual."""
    cf = make_chain()
    emp = cf.cov(cf.chain_samples(m=_M))
    _, _, tree_edges, _ = cf.tree()
    return max(cf.edge_relerr(emp, i, j) for i, j in tree_edges)


def test_fixture_integrity():
    # Behavior: real solved tiles carry populated posterior precision + resolve shared nodes.
    # Bug caught: a future refactor reintroducing a hand-stubbed (None-precision) fixture.
    make_2x2().assert_fixture_integrity()


def test_root_tile_is_exact_unconditional_posterior():
    # Behavior: the spanning-tree ROOT is unconditional, so its corrected-draw marginal variance
    #   == diag((Q_root)^-1) exactly — the sweep does not perturb the root. (The kriging-preserves-
    #   law property for CONDITIONED tiles holds only for exact-marginal fixtures and is already
    #   pinned on the chain in test_gmrf_kriging_oracle; on real solved tiles a child kriged toward
    #   its parent's DIFFERENT posterior is legitimately not (Q_child)^-1.)
    # Bug caught: the root being perturbed, or a global blow-up of the unconditional draw.
    fix = make_2x2()
    _parent, order, _te, _dr = fix.tree()
    root = order[0]
    drv = GmrfTreeKrigingSolve()
    draws = np.stack(
        [drv._sweep_tree(fix.parts, 2.0, m, _NOISE)[root] for m in range(3000)]
    )
    emp = np.cov(draws.T)
    exact = np.linalg.inv(
        cast(Any, fix.parts[root].distribution).fields.precision.toarray()
    )
    np.testing.assert_allclose(np.diag(emp), np.diag(exact), rtol=0.12)


def test_two_white_streams_independent():
    # Behavior (C2'): two tiles' unconditional draws use distinct seeds and are ~uncorrelated.
    # Bug caught: a shared seed correlating a child's unconditional draw with its parent target.
    s0 = derive_seed(_NOISE.method, _NOISE.params_key, "gmrf-tile:0", 7)
    s1 = derive_seed(_NOISE.method, _NOISE.params_key, "gmrf-tile:1", 7)
    assert s0 != s1
    a = np.array(
        [
            float(
                np.random.default_rng(
                    derive_seed(_NOISE.method, _NOISE.params_key, "gmrf-tile:0", m)
                ).standard_normal()
            )
            for m in range(2000)
        ]
    )
    b = np.array(
        [
            float(
                np.random.default_rng(
                    derive_seed(_NOISE.method, _NOISE.params_key, "gmrf-tile:1", m)
                ).standard_normal()
            )
            for m in range(2000)
        ]
    )
    assert abs(np.corrcoef(a, b)[0, 1]) < 0.1


def test_tree_dropped_and_conservative_contracts():
    # Behavior: the three coupled contracts on a real 2x2 — (1) tree-edge <= chain baseline,
    #   (2) dropped <= max(C*tree, baseline floor), (3) conservative direction (median seam
    #   firstdifference variance ratio vs the single-tile reference) on dropped edges.
    # Bug caught: a tree sweep worse than the chain on shared edges; an unbounded dropped edge; a
    #   dropped edge that is small in magnitude but UNDER-dispersed (overconfident) at the seam.
    baseline = _chain_baseline()
    fix = make_2x2()
    bs = fix.tree_samples(m=_M)
    rs = fix.ref_samples(m=_M)
    emp = fix.cov(bs)
    _, _, tree_edges, dropped = fix.tree()
    tree_re = [fix.edge_relerr(emp, i, j) for i, j in tree_edges]
    drop_re = [fix.edge_relerr(emp, i, j) for i, j in dropped]
    max_tree = max(tree_re)
    # (1) tree edges no worse than the validated chain baseline
    assert max_tree <= baseline * (1 + _SLACK), (
        f"tree edge {max_tree:.3f} > chain baseline {baseline:.3f}*(1+{_SLACK})"
    )
    # (2) dropped edges bounded relative to tree, with the chain-baseline floor (degenerate guard)
    ceiling = max(_C * max_tree, baseline)
    assert max(drop_re) <= ceiling, (
        f"dropped edge {max(drop_re):.3f} > max({_C}*{max_tree:.3f}, {baseline:.3f})"
    )
    # (3) conservative direction: no dropped seam is systematically under-dispersed
    for i, j in dropped:
        assert fix.edge_dir_ratio(bs, rs, i, j) >= 0.9, (
            f"dropped edge {i}-{j} under-dispersed at the seam"
        )


def _alt_tree(
    tree_edges: set[tuple[int, int]], dropped: list[tuple[int, int]]
) -> set[tuple[int, int]]:
    """A genuinely different spanning tree: swap one tree edge for a reconnecting dropped edge."""
    alt = set(tree_edges)
    swapped_out = next(iter(tree_edges))
    alt.discard(swapped_out)
    comp = {swapped_out[0]}
    changed = True
    while changed:
        changed = False
        for a, b in alt:
            if a in comp and b not in comp:
                comp.add(b)
                changed = True
            elif b in comp and a not in comp:
                comp.add(a)
                changed = True
    reconnect = next(e for e in dropped if (e[0] in comp) != (e[1] in comp))
    alt.add(reconnect)
    return {(min(e), max(e)) for e in alt}


def test_two_tree_invariance():
    # Behavior: correctness is tree-invariant — the shipped blend is within tolerance under the MST
    #   AND a genuinely different spanning tree (one that drops a DIFFERENT cycle edge).
    # Bug caught: correctness depending on tree structure (topology-fragility silently returned).
    fix = make_2x2()
    _parent, _order, tree_edges, dropped = fix.tree()
    mst_tree = {(min(e), max(e)) for e in tree_edges}
    alt_tree = _alt_tree(tree_edges, dropped)
    assert mst_tree.symmetric_difference(alt_tree), "alt tree must differ from the MST"

    n = len(fix.parts)
    nbr: dict[int, list[int]] = {k: [] for k in range(n)}
    for a, b in alt_tree:
        nbr[a].append(b)
        nbr[b].append(a)
    aparent: dict[int, int | None] = {0: None}
    aorder = [0]
    seen = {0}
    queue = [0]
    while queue:
        u = queue.pop(0)
        for v in nbr[u]:
            if v not in seen:
                seen.add(v)
                aparent[v] = u
                aorder.append(v)
                queue.append(v)

    drv = GmrfTreeKrigingSolve()
    w = np.ones((n, fix.pts.shape[0])) / n
    mst_blend = fix.cov(
        np.stack(
            [
                drv.crossfaded_member(fix.parts, fix.pts, w, m, _NOISE)
                for m in range(1200)
            ]
        )
    )
    alt_blend = fix.cov(
        np.stack(
            [
                drv.crossfaded_member_with_tree(
                    fix.parts, fix.pts, w, m, _NOISE, aparent, aorder, alt_tree
                )
                for m in range(1200)
            ]
        )
    )
    rel_mst = np.linalg.norm(mst_blend - fix.sig_g) / np.linalg.norm(fix.sig_g)
    rel_alt = np.linalg.norm(alt_blend - fix.sig_g) / np.linalg.norm(fix.sig_g)
    assert abs(rel_mst - rel_alt) <= 0.15, (
        f"blend depends on tree choice: MST {rel_mst:.3f} vs alt {rel_alt:.3f}"
    )
