"""★★ probe: does the GMRF prior fix recover cross-seam covariance on make_natl60?

The operational core/range<25 band the Stage-B/C phase boundary declared infeasible.
edge_relerr = ||emp[seam] - dense_global[seam]|| / ||dense_global[seam]|| for the
DEFAULT tree-kriging driver; the marginal-contract strict-min is the localized
collapse metric. Run with the fixed prior, then checkout the pre-fix matern_precision
and re-run to compare.
"""

from __future__ import annotations

import os
import sys

import numpy as np
from scipy.linalg import eigvalsh  # type: ignore[import-untyped]

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.unit._tree_gate import make_natl60  # noqa: E402

M = 2000


def probe(n_lon: int, n_lat: int) -> None:
    """Print conditioning + marginal strict-min + cross-seam rel-err for an n_lon×n_lat tiling."""
    fix = make_natl60(n_lon, n_lat)
    q = np.asarray(fix.gop.q_post.toarray())  # type: ignore[attr-defined]
    e = eigvalsh(q)
    print(
        f"\n=== make_natl60({n_lon},{n_lat}): {len(fix.parts)} tiles, grid {fix.grid.shape} ==="
    )
    print(
        f"  global Q_post eigmin={e.min():.3e} eigmax={e.max():.3e} cond={e.max() / e.min():.2e}"
    )
    samples = fix.tree_samples(m=M)
    mc = fix.marginal_contract_ratios(samples)
    if mc.size:
        print(
            f"  marginal-contract sample/reported strict-min={mc.min():.3e} "
            f"median={np.median(mc):.3f} (>=~0.5 => NOT collapsed; ~1e-7 => collapse)"
        )
    emp = fix.cov(samples)
    relerrs = []
    for i in range(len(fix.parts)):
        for j in range(i + 1, len(fix.parts)):
            gi = fix._shared_gidx(i, j)
            if gi.size:
                relerrs.append(fix.edge_relerr(emp, i, j))
    r = np.array(relerrs)
    print(
        f"  seam edges={r.size}  cross-seam cov rel-err: "
        f"min={r.min():.3f} median={np.median(r):.3f} max={r.max():.3f}"
    )
    print("  (low rel-err => cross-seam covariance RECOVERED vs dense reference)")


if __name__ == "__main__":
    print("TREE-KRIGING driver cross-seam covariance vs dense global reference:")
    probe(2, 2)
    probe(3, 3)
