"""★★ probe: how does tree-kriging cross-seam covariance scale with tile count?

Two distinct scalings of the SAME cross-seam rel-err metric, kept separate because
they answer different questions (the confound that motivated the bigger fixture):

  edge_relerr = ||emp[seam] - dense_global[seam]|| / ||dense_global[seam]|| for the
  DEFAULT tree-kriging driver; marginal-contract strict-min is the localized collapse
  metric (aggregates launder localized seam defects — standing Stage-B rule).

SWEEP 1 — FIXED DOMAIN, shrink tiles. Subdivides the fixed 8°×8° natl60_tiny fixture
  into more, smaller tiles. Conflates tile-count with core/range shrinking toward
  degenerate (near-empty cores at 6×6). Kept for the record; NOT the frontier question.

SWEEP 2 — CONSTANT CORE, grow domain (THE frontier question). Generates a large
  synthetic obs fixture and windows a growing centered box so per-tile core span
  (domain / n_tiles) is HELD FIXED while tile-count grows. This is the true
  "tiles → global" scaling: does aggregate cross-seam error PLATEAU (tiled coherent
  sampler feasible at scale) or GROW UNBOUNDED (tiling breaks down)?

Posterior covariance is obs-VALUE-independent (Q_post = Q_prior + HᵀR⁻¹H), so the
synthetic fixture needs only natl60-like obs GEOMETRY/density, not real SLA. OSSE
``_prepare`` never touches the ref grid, so the fixture is obs-only (ref_path=None).

Run with the fixed prior; checkout the pre-fix matern_precision and re-run to compare.
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

M = 2000

# Constant-core sweep geometry.
CORE_DEG = 4.0  # per-tile core span held fixed (2×2 over 8° == the SWEEP-1 baseline)
CENTER_LON, CENTER_LAT = -60.0, 38.0  # mid-latitude NATL band, matches natl60_tiny
OBS_DENSITY = 0.4  # obs per deg² — natl60_tiny is 40 obs / (10°×10°)
BIG_OBS_PATH = os.path.join(tempfile.gettempdir(), "natl60_big_obs.nc")


def _write_big_obs(path: str, span: float) -> None:
    """Write a large synthetic natl60-like obs fixture covering a ``span``×``span`` box.

    Obs are scattered uniformly at ``OBS_DENSITY`` per deg² and centered on
    (CENTER_LON, CENTER_LAT); values are arbitrary (rng.normal) because the cross-seam
    covariance metric is obs-value-independent. Windowing a sub-box out of this fixture
    preserves the density, so every tiling in the constant-core sweep sees the same
    obs-per-core.

    Args:
        path: Output NetCDF path.
        span: Side length in degrees of the box to populate (use the LARGEST sweep domain).
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


def probe(
    n_lon: int,
    n_lat: int,
    *,
    source: object | None = None,
    lon_range: tuple[float, float] = (-64.0, -56.0),
    lat_range: tuple[float, float] = (34.0, 42.0),
) -> dict[str, float] | None:
    """Print conditioning + marginal strict-min + cross-seam rel-err for one tiling.

    Returns a summary row (tiles, seam-edge count, marginal strict-min, rel-err
    median/max) for the feasibility curve, or ``None`` if the tiling is degenerate
    (empty cores / no seam edges).

    Args:
        n_lon: Tile columns.
        n_lat: Tile rows.
        source: Optional obs source override (constant-core sweep passes the big fixture).
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
        f"\n=== make_natl60({n_lon},{n_lat}): {len(fix.parts)} tiles, grid {fix.grid.shape}, "
        f"core={core_lon:.2f}° ==="
    )
    print(
        f"  global Q_post eigmin={e.min():.3e} eigmax={e.max():.3e} cond={e.max() / e.min():.2e}"
    )
    samples = fix.tree_samples(m=M)
    mc = fix.marginal_contract_ratios(samples)
    mc_min = float(mc.min()) if mc.size else float("nan")
    if mc.size:
        print(
            f"  marginal-contract sample/reported strict-min={mc_min:.3e} "
            f"median={np.median(mc):.3f} (>=~0.5 => NOT collapsed; ~1e-7 => collapse)"
        )
    emp = fix.cov(samples)
    relerrs = []
    corr_errs = []
    for i in range(len(fix.parts)):
        for j in range(i + 1, len(fix.parts)):
            gi = fix._shared_gidx(i, j)
            if gi.size:
                relerrs.append(fix.edge_relerr(emp, i, j))
                ce = fix.edge_seam_corr_err(emp, i, j)
                if ce > 0.0:  # edges with no grid-adjacent seam pair contribute nothing
                    corr_errs.append(ce)
    r = np.array(relerrs)
    c = np.array(corr_errs)
    if not r.size:
        print("  NO seam edges (degenerate tiling) — skipped")
        return None
    print(
        f"  seam edges={r.size}  BLOCK rel-err (fragile): "
        f"median={np.median(r):.3f} max={r.max():.3f}"
    )
    c_med = float(np.median(c)) if c.size else float("nan")
    c_max = float(c.max()) if c.size else float("nan")
    print(
        f"  adjacent-seam CORR-err (robust): "
        f"median={c_med:.3f} max={c_max:.3f} (n={c.size}; ~0 good, ~1 decorrelated)"
    )
    return {
        "n_lon": n_lon,
        "n_lat": n_lat,
        "tiles": float(len(fix.parts)),
        "seam_edges": float(r.size),
        "mc_min": mc_min,
        "relerr_median": float(np.median(r)),
        "relerr_max": float(r.max()),
        "correrr_median": c_med,
        "correrr_max": c_max,
    }


def _print_curve(title: str, rows: list[dict[str, float]]) -> None:
    """Print a feasibility-vs-tile-count table from probe rows."""
    print(f"\n\n==== {title} ====")
    print(
        f"  {'tiling':>8} {'tiles':>6} {'core°':>6} "
        f"{'mc_min':>9} {'block_med':>10} {'block_max':>10} {'CORR_med':>9} {'CORR_max':>9}"
    )
    for row in rows:
        core = 0.0 if not row["core_deg"] else row["core_deg"]
        print(
            f"  {int(row['n_lon'])}x{int(row['n_lat']):<6} "
            f"{int(row['tiles']):>6} {core:>6.2f} "
            f"{row['mc_min']:>9.3e} {row['relerr_median']:>10.3f} {row['relerr_max']:>10.3f} "
            f"{row.get('correrr_median', float('nan')):>9.3f} {row.get('correrr_max', float('nan')):>9.3f}"
        )


def _sweep(constant_core: bool) -> list[dict[str, float]]:
    """Run one tile-count sweep. ``constant_core`` grows the domain with tile count."""
    from sverdrup.adapters.odc.fixtures import FixtureSource

    source = None
    rows: list[dict[str, float]] = []
    if constant_core:
        max_span = CORE_DEG * 6
        _write_big_obs(BIG_OBS_PATH, span=max_span)
        source = FixtureSource(BIG_OBS_PATH, ref_path=None)
    for k in range(2, 7):
        if constant_core:
            half = CORE_DEG * k / 2.0
            lon_range = (CENTER_LON - half, CENTER_LON + half)
            lat_range = (CENTER_LAT - half, CENTER_LAT + half)
        else:
            lon_range, lat_range = (-64.0, -56.0), (34.0, 42.0)
        try:
            row = probe(k, k, source=source, lon_range=lon_range, lat_range=lat_range)
        except Exception as exc:  # noqa: BLE001 — degenerate tiling diagnostic, keep sweeping
            print(f"\n=== make_natl60({k},{k}): FAILED — {type(exc).__name__}: {exc}")
            continue
        if row is not None:
            row["core_deg"] = (lon_range[1] - lon_range[0]) / k
            rows.append(row)
    return rows


if __name__ == "__main__":
    print("SWEEP 1 — FIXED DOMAIN, shrink tiles (confounded: core/range → degenerate):")
    fixed = _sweep(constant_core=False)

    print("\n\nSWEEP 2 — CONSTANT CORE, grow domain (the tiles→global frontier):")
    scaled = _sweep(constant_core=True)

    _print_curve("SWEEP 1: FIXED DOMAIN (core shrinks) — confounded", fixed)
    _print_curve("SWEEP 2: CONSTANT CORE (domain grows) — THE frontier", scaled)
    print("\n  median/max rel-err PLATEAU across SWEEP 2 => tiled coherent sampler")
    print(
        "  feasible at global scale; UNBOUNDED GROWTH => needs Schwarz/coarse-correction."
    )
