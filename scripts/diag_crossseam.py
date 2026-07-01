"""★★ probe: how does tree-kriging cross-seam JOINT covariance scale with tile count?

The Stage-C feasibility question: does the DEFAULT tree-kriging coherent sampler hold
valid JOINT cross-seam covariance as tiles → global? Two metrics on the same seams:

  BLOCK rel-err (fragile) = ‖emp[block] - ref[block]‖ / ‖ref[block]‖ over shared-node
    blocks. Denominator → 0 for far / thin-overlap node sets (true cov ~0), so M-sample
    noise inflates it — the suspected "worst-seam max grows past 2" artifact.

  CORR-err (robust) = per grid-ADJACENT shared node pair, |emp_cov - ref_cov| / √(σ_a σ_b):
    a correlation-unit error (never near-zero denominator), the physical seam where
    cross-tile gradients integrate. This is the metric Stage-C feasibility keys on.

SELECTION CONTROL (the point of this M=8000 re-run): raw worst-case (max) over all
adjacent node pairs grows with tile count PARTLY because more pairs are sampled
(worst-of-6 vs worst-of-600), a selection confound — not necessarily because seams
degrade. So we pool CORR-err at the node-pair level and report, alongside the raw max,
a **worst-of-K** statistic: the mean over R seeded subsamples of the max of a FIXED count
K of node pairs (K = the smallest tiling's pool). worst-of-K is comparable across tilings
— if it still grows, seams genuinely degrade with scale; if it is flat, the raw-max growth
was pure selection. High M drives the per-pair sampling floor well below the tolerance.

SWEEP — CONSTANT CORE, grow domain (the tiles→global frontier). Windows a growing
centered box out of a large synthetic obs fixture so per-tile core span (domain / n_tiles)
is HELD FIXED while tile-count grows. Posterior covariance is obs-VALUE-independent
(Q_post = Q_prior + HᵀR⁻¹H), so the fixture needs only natl60-like obs geometry/density;
OSSE ``_prepare`` never touches the ref grid, so it is obs-only (ref_path=None).
"""

from __future__ import annotations

import os
import sys
import tempfile

import numpy as np
import xarray as xr
from scipy.linalg import eigvalsh  # type: ignore[import-untyped]

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.unit._tree_gate import make_natl60  # noqa: E402

M = 8000  # high sample count so the per-pair corr-err sampling floor << tolerance
R_SUBSAMPLE = 400  # seeded subsamples for the selection-controlled worst-of-K

# Constant-core sweep geometry.
CORE_DEG = 4.0  # per-tile core span held fixed
CENTER_LON, CENTER_LAT = -60.0, 38.0  # mid-latitude NATL band, matches natl60_tiny
OBS_DENSITY = 0.4  # obs per deg² — natl60_tiny is 40 obs / (10°×10°)
BIG_OBS_PATH = os.path.join(tempfile.gettempdir(), "natl60_big_obs.nc")


def _write_big_obs(path: str, span: float) -> None:
    """Write a large synthetic natl60-like obs fixture covering a ``span``×``span`` box.

    Obs are scattered uniformly at ``OBS_DENSITY`` per deg² and centered on
    (CENTER_LON, CENTER_LAT); values are arbitrary (rng.normal) because the cross-seam
    covariance metric is obs-value-independent. Windowing a sub-box out of this fixture
    preserves the density, so every tiling sees the same obs-per-core.

    Args:
        path: Output NetCDF path.
        span: Side length in degrees of the box to populate (the largest sweep domain).
    """
    rng = np.random.default_rng(0)
    half = span / 2.0
    n = int(round(OBS_DENSITY * span * span))
    ds = xr.Dataset(
        {
            "sla": ("t", rng.normal(0, 0.1, n)),
            "longitude": ("t", rng.uniform(CENTER_LON - half, CENTER_LON + half, n)),
            "latitude": ("t", rng.uniform(CENTER_LAT - half, CENTER_LAT + half, n)),
            "time": ("t", np.linspace(0, 5, n)),
            "mission": ("t", rng.choice(["s6", "j3", "alg"], n)),
        }
    )
    ds.to_netcdf(path)


def _worst_of_k(pool: np.ndarray, k: int, r: int) -> float:
    """Mean over ``r`` seeded subsamples of the max of ``k`` draws from ``pool``.

    Selection-controlled worst-case: holds the compared-pair count fixed at ``k`` across
    tilings so a growing value means seams degraded, not that more pairs were sampled.
    """
    if pool.size == 0 or k <= 0:
        return float("nan")
    rng = np.random.default_rng(12345)
    k = min(k, pool.size)
    maxes = [float(rng.choice(pool, size=k, replace=False).max()) for _ in range(r)]
    return float(np.mean(maxes))


def probe(
    n_lon: int,
    n_lat: int,
    *,
    source: object | None = None,
    lon_range: tuple[float, float],
    lat_range: tuple[float, float],
) -> dict[str, object] | None:
    """Probe one tiling; return its stats row + the pooled per-pair CORR-err array.

    Args:
        n_lon: Tile columns.
        n_lat: Tile rows.
        source: Obs source (the big constant-core fixture).
        lon_range: Domain longitude extent (grown with n_lon for constant core).
        lat_range: Domain latitude extent (grown with n_lat for constant core).
    """
    fix = make_natl60(
        n_lon, n_lat, source=source, lon_range=lon_range, lat_range=lat_range
    )
    q = np.asarray(fix.gop.q_post.toarray())  # type: ignore[attr-defined]
    e = eigvalsh(q)
    core_lon = (lon_range[1] - lon_range[0]) / n_lon
    print(
        f"\n=== make_natl60({n_lon},{n_lat}): {len(fix.parts)} tiles, "
        f"grid {fix.grid.shape}, core={core_lon:.2f}° ==="
    )
    print(f"  Q_post eigmin={e.min():.3e} cond={e.max() / e.min():.2e}")
    samples = fix.tree_samples(m=M)
    mc = fix.marginal_contract_ratios(samples)
    mc_min = float(mc.min()) if mc.size else float("nan")
    emp = fix.cov(samples)
    block_relerrs = []
    pool: list[
        float
    ] = []  # every grid-adjacent node-pair CORR-err, pooled across edges
    for i in range(len(fix.parts)):
        for j in range(i + 1, len(fix.parts)):
            if fix._shared_gidx(i, j).size:
                block_relerrs.append(fix.edge_relerr(emp, i, j))
                pool.extend(fix.edge_seam_corr_errs(emp, i, j).tolist())
    r = np.array(block_relerrs)
    c = np.array(pool)
    if not r.size or not c.size:
        print("  NO seam / no adjacent node pair (degenerate tiling) — skipped")
        return None
    print(
        f"  marg strict-min={mc_min:.3f}  BLOCK rel-err med={np.median(r):.3f} "
        f"max={r.max():.3f}  |  CORR-err pool n={c.size} med={np.median(c):.3f} "
        f"p95={np.percentile(c, 95):.3f} max={c.max():.3f}"
    )
    return {
        "n_lon": n_lon,
        "n_lat": n_lat,
        "tiles": len(fix.parts),
        "mc_min": mc_min,
        "block_med": float(np.median(r)),
        "block_max": float(r.max()),
        "corr_pool": c,
        "corr_med": float(np.median(c)),
        "corr_p95": float(np.percentile(c, 95)),
        "corr_max": float(c.max()),
        "core_deg": core_lon,
    }


if __name__ == "__main__":
    from sverdrup.adapters.odc.fixtures import FixtureSource

    print(
        f"CONSTANT-CORE tiles→global frontier (M={M}, selection-controlled worst-of-K):"
    )
    _write_big_obs(BIG_OBS_PATH, span=CORE_DEG * 6)
    src = FixtureSource(BIG_OBS_PATH, ref_path=None)

    rows: list[dict[str, object]] = []
    for kk in range(2, 7):
        half = CORE_DEG * kk / 2.0
        try:
            row = probe(
                kk,
                kk,
                source=src,
                lon_range=(CENTER_LON - half, CENTER_LON + half),
                lat_range=(CENTER_LAT - half, CENTER_LAT + half),
            )
        except Exception as exc:  # noqa: BLE001 — degenerate tiling diagnostic, keep sweeping
            print(f"\n=== make_natl60({kk},{kk}): FAILED — {type(exc).__name__}: {exc}")
            continue
        if row is not None:
            rows.append(row)

    # Selection control: fix K = the smallest tiling's pool size across all tilings.
    pools = [np.asarray(row["corr_pool"]) for row in rows]
    k_fixed = min(int(p.size) for p in pools)
    for row, p in zip(rows, pools, strict=True):
        row["corr_wok"] = _worst_of_k(p, k_fixed, R_SUBSAMPLE)

    print(
        f"\n\n==== CONSTANT-CORE FRONTIER — robust CORR-err (worst-of-K, K={k_fixed} fixed) ===="
    )
    print(
        f"  {'tiling':>7} {'tiles':>6} {'marg':>7} {'block_max':>10} "
        f"{'corr_med':>9} {'corr_p95':>9} {'corr_max':>9} {'corr_woK':>9}"
    )
    for row in rows:
        print(
            f"  {row['n_lon']}x{row['n_lat']:<5} {row['tiles']:>6} {row['mc_min']:>7.3f} "
            f"{row['block_max']:>10.3f} {row['corr_med']:>9.3f} {row['corr_p95']:>9.3f} "
            f"{row['corr_max']:>9.3f} {row['corr_wok']:>9.3f}"
        )
    print("\n  corr_woK (selection-controlled) FLAT => raw-max growth was selection;")
    print(
        "  corr_woK GROWS => seams genuinely degrade with tile count (real scale-break)."
    )
    print(
        "  Decisive cell: 2x2 corr_woK vs tol=0.5 — is worst-case broken from the smallest tiling?"
    )
