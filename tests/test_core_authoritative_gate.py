"""Stage-B core-authoritative sampler — ownership, marginal fix, and the case-(b) boundary gate.

The overwrite driver fixes the marginal seam collapse but, because cores are drawn independently,
reports cross-seam correlation as ZERO by construction — correct only at short range (true seam
corr ~0), wrong at operational range. These tests pin that boundary (PROGRESS "SECOND ANTAGONIST" /
"DEFLATION IS DEAD"): overwrite is a NON-DEFAULT reference; the default stays the tree driver pending
Phase 5; and the cross-seam COVARIANCE invariant (invisible to marginal + direction) is the acceptance
test the Phase-5 decomposition fix must flip.
"""

from __future__ import annotations

from functools import cache
from typing import Any

import numpy as np
import pytest

pytest.importorskip("sksparse")

from sverdrup.application.tuning.feasibility import (  # noqa: E402
    CoherenceFeasibility,
    TileGeometry,
)
from sverdrup.core.types import UncertaintyCapability  # noqa: E402
from sverdrup.distributions.blend import partition_weights  # noqa: E402
from sverdrup.distributions.coherent import (  # noqa: E402
    GmrfCoreAuthoritativeSolve,
    GmrfTreeKrigingSolve,
    NoiseSpec,
    _core_owner_of_points,
    select_driver,
)
from tests.unit._tree_gate import make_grid_diagonal, make_natl60  # noqa: E402

_NOISE = NoiseSpec(method="gmrf", params_key="p", lattice_step=0.5)


def _samples(fix: Any, m: int = 400) -> np.ndarray:
    drv = GmrfCoreAuthoritativeSolve()
    w = partition_weights([p.tile for p in fix.parts], fix.pts)
    return np.stack(
        [drv.crossfaded_member(fix.parts, fix.pts, w, k, _NOISE) for k in range(m)]
    )


def test_core_ownership_matches_weights():
    fix = make_natl60(2, 2)
    pts = fix.pts
    owner = _core_owner_of_points(fix.parts, pts, 2.0)
    assert (owner >= 0).all(), "every output node must have a core owner"
    w = partition_weights([p.tile for p in fix.parts], pts)  # (T, n)
    assert np.array_equal(owner, np.argmax(w, axis=0)), (
        "core-ownership tie-break must match partition_weights' argmax at every node"
    )


def test_marginal_contract_honored_and_overwrite_is_non_default():
    # The default sparse-precision sampler is NOT overwrite: registering a construction
    #   structurally guaranteed-wrong in the operational band would be a runtime tripwire, not a
    #   sampler. The default stays the tree driver; the choice is deferred to Phase 5.
    assert isinstance(select_driver("sparse-precision"), GmrfTreeKrigingSolve)
    assert not isinstance(select_driver("sparse-precision"), GmrfCoreAuthoritativeSolve)
    # Overwrite (constructed directly) DOES fix the marginal seam collapse — a real property of the
    #   reference construction (the tree driver gave 1.76e-7 here).
    fix = make_natl60(2, 2)
    ratios = fix.marginal_contract_ratios(_samples(fix))
    smin = float(ratios.min())
    print(f"\n[core-authoritative] marginal sample/contract strict-min = {smin:.3f}")
    assert smin >= 0.5, (
        f"overwrite marginal collapse not fixed: strict-min {smin:.3e} < 0.5 "
        "(tree driver was 1.76e-7)"
    )


def _adjacent_pairs(pts: np.ndarray) -> list[tuple[int, int]]:
    """Grid-adjacent (a, b) pairs: a 1-degree step in lon XOR lat."""
    idx = {
        (round(float(pts[i, 0]), 6), round(float(pts[i, 1]), 6)): i
        for i in range(pts.shape[0])
    }
    out: list[tuple[int, int]] = []
    for i in range(pts.shape[0]):
        lo, la = float(pts[i, 0]), float(pts[i, 1])
        for dlo, dla in ((1.0, 0.0), (0.0, 1.0)):
            j = idx.get((round(lo + dlo, 6), round(la + dla, 6)))
            if j is not None:
                out.append((i, j))
    return out


@cache
def _measure(r: float, m: int = 300) -> tuple[float, float, float, float]:
    """Three seam invariants for overwrite on the production fixture at range ``r``.

    Returns ``(marginal_strict_min, direction_strict_min, worst_true_seam_corr,
    blend_corr_at_that_pair)``. ``worst`` = the seam pair with the largest |true correlation| (the
    structure overwrite must carry); ``blend_corr`` is what overwrite actually installs (~0 by
    construction). Strict-min / worst-pair throughout (rule i) — never an aggregate.
    """
    fix = make_grid_diagonal(3, 3, r)
    pts = fix.pts
    owner = _core_owner_of_points(fix.parts, pts, 2.0)
    sig = fix.sig_g
    samples = _samples(fix, m)
    emp = np.cov(samples.T)
    sv = samples.var(axis=0)
    contract = fix.sigma_contract() ** 2
    cfloor = 1e-6 * float(np.max(contract))

    seam = [(a, b) for (a, b) in _adjacent_pairs(pts) if owner[a] != owner[b]]
    seam_nodes = sorted({x for p in seam for x in p})
    marg = [sv[g] / contract[g] for g in seam_nodes if contract[g] > cfloor]
    marg_min = float(np.min(marg)) if marg else float("nan")

    dirs = []
    rows = []
    for a, b in seam:
        true_fd = sig[a, a] + sig[b, b] - 2 * sig[a, b]
        blend_fd = emp[a, a] + emp[b, b] - 2 * emp[a, b]
        if true_fd > cfloor:
            dirs.append(blend_fd / true_fd)
        tcorr = float(sig[a, b] / np.sqrt(sig[a, a] * sig[b, b]))
        bcorr = float(emp[a, b] / np.sqrt(emp[a, a] * emp[b, b]))
        rows.append((abs(tcorr), tcorr, bcorr))
    dir_min = float(np.min(dirs)) if dirs else float("nan")
    rows.sort(reverse=True)
    worst_true_corr = rows[0][1]
    blend_at_worst = rows[0][2]
    return marg_min, dir_min, worst_true_corr, blend_at_worst


def test_case_b_boundary_characterization():
    # CHARACTERIZATION (green): pins the measured phase boundary as a function of range on the
    #   production grid+diagonal fixture. At operational range the true cross-seam correlation is
    #   SUBSTANTIAL and overwrite zeroes it (case b); at short range the true correlation is ~0 so
    #   overwrite's zero is correct (case a-real). The marginal and DIRECTION gates both PASS at
    #   long range — only the cross-seam COVARIANCE (worst_true_corr vs blend) sees the destruction.
    # Bug caught: a future change that lets overwrite leak cross-seam correlation away from zero
    #   (it is zero BY CONSTRUCTION) or that makes the long-range true seam corr vanish (fixture no
    #   longer operational-representative) — either invalidates the boundary this gate records.
    lo_marg, lo_dir, lo_true, lo_blend = _measure(400.0)
    sh_marg, sh_dir, sh_true, sh_blend = _measure(50.0)
    print(
        f"\n[case-b boundary] 400km: marg={lo_marg:.3f} dir={lo_dir:.3f} "
        f"true_seam_corr={lo_true:+.3f} blend={lo_blend:+.3f}  |  "
        f"50km: marg={sh_marg:.3f} dir={sh_dir:.3f} "
        f"true_seam_corr={sh_true:+.3f} blend={sh_blend:+.3f}"
    )
    # marginal holds at both ranges (overwrite's one genuine win)
    assert lo_marg >= 0.5 and sh_marg >= 0.5, "overwrite marginal contract must hold"
    # direction PASSES at long range — demonstrating it MISSES the covariance destruction
    assert lo_dir >= 0.9, (
        f"direction strict-min {lo_dir:.3f} < 0.9 at 400km — expected to PASS (zero-corr is "
        "conservative for the gradient); if it fails the masking demonstration changed"
    )
    # DECISIVE: operational regime has substantial true seam corr that overwrite zeroes (case b)
    assert lo_true > 0.4, (
        f"production fixture no longer operational-representative: 400km true seam corr "
        f"{lo_true:.3f} <= 0.4"
    )
    assert abs(lo_blend) < 0.15, (
        f"overwrite must report ~zero cross-seam corr by construction; got {lo_blend:+.3f}"
    )
    # short range: true corr ~0, so overwrite's zero is correct (case a-real)
    assert abs(sh_true) < 0.2, (
        f"short-range true seam corr {sh_true:+.3f} not ~0 — overwrite regime expected here"
    )


@pytest.mark.xfail(
    strict=True,
    reason="owner-deferred coarse-correction; n_star_joint=1 (joint region empty) until then",
)
def test_acceptance_multi_tile_joint_feasible() -> None:
    # The known-unmet target, pinned in code: a multi-tile SAMPLES product should be feasible.
    # It is NOT today (n_star_joint=1) -> strict xfail; the deferred decomposition-redesign that
    # widens n_star_joint flips this to xpass. Replaces the retired core/range>=25 acceptance.
    geom = TileGeometry(core_size_deg=4.0, range_km=300.0, tiling_id="g", n_tiles=9)
    assert CoherenceFeasibility().feasible(
        {}, geom, frozenset({UncertaintyCapability.SAMPLES})
    )
