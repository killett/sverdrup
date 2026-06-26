"""Joint-covariance validity oracle for the kriging-conditioning GMRF driver (Task 9c).

Marginal checks are the blind spot that passed the broken native-shared-w sampler; this oracle
asserts JOINT structure against a dense global reference (spec §5.3.1, gated point 2):

  1. Per-tile validity — the conditioned tile's full corrected covariance == its exact posterior.
  2. Cross-seam joint coherence — the blended field's joint covariance == the single-tile (global)
     dense reference, including the across-seam cross-blocks (the property measured at −0.51 for
     the old driver).
  3. 3-tile transitivity — the centre tile agrees with BOTH neighbours; the joint matches global.
  4. Separator negative control — a too-thin (1-column) overlap trips the assertion, and (assertion
     bypassed) yields a WRONG joint covariance — proving the separator is the real precondition.

The fixtures are EXACT by construction: each tile carries the global field's exact marginal
precision over its nodes (``inv(Σ_global[tile, tile])``), and the overlap strips are true
Q-separators, so the forward sweep reproduces the global joint sample exactly. A red here is a
math bug, never a tolerance to loosen.
"""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("sksparse")  # noqa: E402

from scipy import sparse  # type: ignore[import-untyped]  # noqa: E402

from sverdrup.core.geometry import Tile, Window  # noqa: E402
from sverdrup.core.grid import GridSpec  # noqa: E402
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow  # noqa: E402
from sverdrup.core.parameters import ConstantProvider  # noqa: E402
from sverdrup.distributions import coherent  # noqa: E402
from sverdrup.distributions.blend import (  # noqa: E402
    BlendInput,
    BlendOperator,
    partition_weights,
)
from sverdrup.distributions.coherent import GmrfKrigingSolve, NoiseSpec  # noqa: E402
from sverdrup.distributions.persisted import (  # noqa: E402
    PrecisionDistribution,
    PrecisionFields,
)
from sverdrup.methods.gmrf import MaternGMRF  # noqa: E402
from sverdrup.methods.gmrf_grid import matern_precision  # noqa: E402

_P = ConstantProvider({"range": 300.0, "variance": 0.05, "temporal_taper_scale": 5.0})
_NOISE = NoiseSpec(method="gmrf", params_key="p", lattice_step=0.5)
_LATS = np.array([0.0, 1.0])


def _prov():
    """Borrow a valid UncertaintyProvenance from one tiny real GMRF solve."""
    g = GridSpec.lonlat(np.arange(3.0), _LATS)
    obs = ObsWindow.from_arrays(
        np.array([1.0]),
        np.array([0.5]),
        np.array([0.0]),
        np.array([1.0]),
        DiagonalErrorModel(np.array([1e-3])),
    )
    return MaternGMRF().solve(obs, g, _P, 0.0).provenance


def _global(nlon, kappa=0.7):
    g = GridSpec.lonlat(np.arange(float(nlon)), _LATS)
    q = matern_precision(g, kappa=kappa, tau=1.0)
    sig = np.linalg.inv(q.toarray())
    return g, q, sig


def _tile_pd(gg, sig, lon_lo, lon_hi, core, ext, prov):
    """A tile carrying the EXACT marginal precision of the global field over its lon window."""
    lon_sub = np.arange(float(lon_lo), float(lon_hi) + 1.0)
    tg = GridSpec.lonlat(lon_sub, _LATS)
    tp = tg.points(0.0)
    gp = gg.points(0.0)
    gidx = np.array(
        [int(np.argmin(np.abs(gp[:, 0] - p[0]) + np.abs(gp[:, 1] - p[1]))) for p in tp]
    )
    sig_ll = sig[np.ix_(gidx, gidx)]
    p_l = np.linalg.inv(sig_ll)
    fields = PrecisionFields(
        mean=np.zeros(tg.shape),
        precision=sparse.csc_matrix(p_l),
        permutation=np.arange(p_l.shape[0]),
        marginal_variance=np.diag(sig_ll).reshape(tg.shape),
        seed=0,
    )
    pd = PrecisionDistribution(tg, fields, prov, 0.0)
    tile = Tile(Window(core, (0, 1), (0, 0)), Window(ext, (0, 1), (0, 0)), tg)
    return BlendInput(pd, tile), gidx


def _two_tile_fixture():
    # global lon 0..7: A{0,1,2}  S{3,4}  B{5,6,7}; S is a 2-col (=reach) separator.
    gg, q, sig = _global(8)
    prov = _prov()
    left, gl = _tile_pd(gg, sig, 0, 4, (0, 2.5), (0, 4), prov)
    right, gr = _tile_pd(gg, sig, 3, 7, (4.5, 7), (3, 7), prov)
    return gg, q, sig, [left, right], [gl, gr]


def _emp_cov(samples):
    c = samples - samples.mean(axis=0)
    return c.T @ c / (samples.shape[0] - 1)


def test_per_tile_corrected_cov_matches_exact_posterior():
    # Behavior(1): the conditioned tile's full corrected covariance == its exact posterior Σ
    #   (whole matrix, not just the diagonal) — kriging preserves the conditional law.
    gg, q, sig, parts, gidx = _two_tile_fixture()
    driver = GmrfKrigingSolve()
    draws = np.stack([driver._sweep(parts, 0.0, m, _NOISE)[1] for m in range(8000)])
    ref = sig[np.ix_(gidx[1], gidx[1])]  # exact marginal Σ of the right tile
    emp = _emp_cov(draws)
    scale = np.mean(np.diag(ref))
    np.testing.assert_allclose(emp, ref, atol=float(0.08 * scale))


def test_cross_seam_joint_cov_matches_global_reference():
    # Behavior(2): the blended field's JOINT covariance (incl. across-seam A–B cross-blocks)
    #   == the single-tile global Σ. The old native-shared-w driver missed this at −0.51.
    gg, q, sig, parts, gidx = _two_tile_fixture()
    bd = BlendOperator().blend(
        parts, gg, method="gmrf", params_key="p", lattice_step=0.5
    )
    samples = bd.sample(8000, seed=11).reshape(8000, -1)
    emp = _emp_cov(samples)
    scale = np.mean(np.diag(sig))
    # whole joint matrix, including the A-vs-B cross-seam block that has no shared nodes
    np.testing.assert_allclose(emp, sig, atol=float(0.08 * scale))
    a = gidx[0][0]  # an A-only node (left interior)
    b = gidx[1][-1]  # a B-only node (right interior)
    assert sig[a, b] != 0.0  # the global field genuinely couples across the seam
    assert abs(emp[a, b] - sig[a, b]) < 0.12 * scale


def _three_tile_fixture():
    # global lon 0..11: A{0,1,2} S1{3,4} C{5,6} S2{7,8} B{9,10,11}; both strips 2-col separators.
    gg, q, sig = _global(12)
    prov = _prov()
    left, gl = _tile_pd(gg, sig, 0, 4, (0, 2.5), (0, 4), prov)
    cen, gc = _tile_pd(gg, sig, 3, 8, (4.5, 6.5), (3, 8), prov)
    right, gr = _tile_pd(gg, sig, 7, 11, (8.5, 11), (7, 11), prov)
    return gg, q, sig, [left, cen, right], [gl, gc, gr]


def test_three_tile_transitivity_and_joint():
    # Behavior(3): the centre tile agrees with BOTH neighbours on their respective overlaps
    #   (the seam-of-the-seam), and the 3-tile joint covariance matches the global reference.
    # Bug caught: a pairwise scheme that passes 2-tile but breaks transitively on 3.
    gg, q, sig, parts, gidx = _three_tile_fixture()
    gp = gg.points(0.0)
    driver = GmrfKrigingSolve()
    corrected = driver._sweep(parts, 0.0, member_index=5, noise=_NOISE)
    keymaps = [
        {(round(gp[i, 0], 6), round(gp[i, 1], 6)): k for k, i in enumerate(gi)}
        for gi in gidx
    ]
    for a, b in ((0, 1), (1, 2)):  # L–C and C–R seams
        shared = sorted(set(keymaps[a]) & set(keymaps[b]))
        assert len(shared) >= 4
        va = np.array([corrected[a][keymaps[a][k]] for k in shared])
        vb = np.array([corrected[b][keymaps[b][k]] for k in shared])
        np.testing.assert_allclose(va, vb, rtol=1e-9, atol=1e-12)
    bd = BlendOperator().blend(
        parts, gg, method="gmrf", params_key="p", lattice_step=0.5
    )
    emp = _emp_cov(bd.sample(8000, seed=3).reshape(8000, -1))
    np.testing.assert_allclose(emp, sig, atol=float(0.09 * np.mean(np.diag(sig))))


def test_separator_negative_control():
    # Behavior(4): a 1-column overlap (< stencil reach 2) (a) trips the separator assertion AND
    #   (b) with the assertion bypassed, yields a materially WRONG blended joint covariance vs
    #   the global reference — proving the >= reach overlap policy is a real precondition, not
    #   folklore. With only ONE shared column there is no room for the partition-of-unity
    #   crossfade: the lone seam column loses all weight, its variance collapses, and the joint
    #   departs far beyond MC noise (the >=2-col fixtures above matched global to <0.1*scale per
    #   entry). The structural Q-separator guarantee is gone exactly when overlap < reach.
    # global lon 0..5: tile L lon{0,1,2}, tile R lon{2,3,4,5}; overlap = lon{2} only (1 column).
    gg, q, sig = _global(6)
    prov = _prov()
    left, gl = _tile_pd(gg, sig, 0, 2, (0, 1.5), (0, 2), prov)
    right, gr = _tile_pd(gg, sig, 2, 5, (2.5, 5), (2, 5), prov)
    parts = [left, right]
    pts = gg.points(0.0)
    w = partition_weights([p.tile for p in parts], pts)

    # (a) the precondition fires
    with pytest.raises(AssertionError, match="separat"):
        GmrfKrigingSolve().crossfaded_member(parts, pts, w, 1, _NOISE)

    # (b) bypass it -> the blended joint covariance is provably wrong
    orig = coherent._assert_separates
    coherent._assert_separates = lambda *a, **k: None
    try:
        bd = BlendOperator().blend(
            parts, gg, method="gmrf", params_key="p", lattice_step=0.5
        )
        emp = _emp_cov(bd.sample(8000, seed=7).reshape(8000, -1))
    finally:
        coherent._assert_separates = orig
    gp = gg.points(0.0)
    seam = int(
        np.argmin(np.abs(gp[:, 0] - 2.0) + np.abs(gp[:, 1] - 0.0))
    )  # lon=2 column
    scale = float(np.mean(np.diag(sig)))
    assert (
        abs(emp[seam, seam] - sig[seam, seam]) > 0.5 * scale
    )  # seam variance collapses
    assert (
        np.linalg.norm(emp - sig) > 2.0
    )  # joint departs far beyond MC (~0.5 when valid)
