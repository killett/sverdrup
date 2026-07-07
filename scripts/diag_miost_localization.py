"""Task-11 D4 localization probes (owner-ordered, 2026-07-04) on the equivalence pair.

Four probes on the windowed-vs-single-window pair, feeding the PRE-REGISTERED
close rules (owner message, Task-11 gate):

1. Score BOTH full-year maps on the BLOCKED VALIDATION track (mu; lambda_x if
   it resolves). Never c2. Records Delta-mu = the measured windowing skill-cost.
2. Delta vs DISTANCE-TO-NEAREST-WINDOW-BOUNDARY profile (replaces the binary
   blend/interior split).
3. Scale attribution (exact per-rung day maps, no band-pass leakage) + spatial
   pattern (edge-band vs interior) on the worst + a far-from-boundary day.
4. J-identity sanity: J_single(eta_single) <= J_single(stitched windowed) —
   violation means the reference is not the joint minimizer (diagnostic defect).

Solves run at the Stage-A budgeted-solve config (rtol 1e-6 target, maxiter 500
cap) — map-space depth-insensitivity is MEASURED (worst-day 2.0036 vs 2.0220 m).

Output: docs/validation/miost_equivalence_localization.md
"""

from __future__ import annotations

import math
import time
from pathlib import Path

import numpy as np

from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
from sverdrup.core.parameters import ConstantProvider
from sverdrup.eval.skill_score import leaderboard_nrmse
from sverdrup.eval.spectral import (
    ShortTrackError,
    UnresolvedScaleError,
    effective_resolution_lambda_x,
)
from sverdrup.methods.miost import Miost, _window_obs
from sverdrup.methods.miost_basis import (
    BOX_LAT,
    BOX_LON,
    HALO_DEG,
    R_REF,
    BasisSpec,
    DiagonalQ,
    _layouts,
    build_g,
)
from sverdrup.methods.miost_windows import WindowPlan
from sverdrup.validation.input_adapter import load_mapping_obs, load_mdt_grid
from sverdrup.validation.output_adapter import write_map
from sverdrup.validation.params import baseline_config

SCOPE = Path("tests/validation/fixtures/stage_a_scope.json")
OUT_DIR = Path("data/2021a_ssh_mapping_ose/ours")
DOC = Path("docs/validation/miost_equivalence_localization.md")
PARAMS = ConstantProvider(
    {"spacing_alpha": 1.5, "log10_rho": 1.0, "q_slope": 2.0, "l_t_days": 10.0}
)
VAL_TRACK = Path(
    "data/2021a_ssh_mapping_ose/dc_obs/"
    "dt_gulfstream_j3_phy_l3_20161201-20180131_285-315_23-53.nc"
)
_T0 = time.time()


def _log(msg: str) -> None:
    """Timestamped, flushed heartbeat."""
    s = int(time.time() - _T0)
    print(f"[+{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}] {msg}", flush=True)


def _halo_obs() -> ObsWindow:
    """Six mapping missions, box + halo (identical to the equivalence run)."""
    import json

    cfg = json.loads(SCOPE.read_text())
    provider, _, _ = baseline_config()
    obs = load_mapping_obs([Path(p) for p in cfg["mapping_obs_paths"]], provider)
    c = obs.coords()
    keep = (
        (c[:, 0] >= BOX_LON[0] - HALO_DEG)
        & (c[:, 0] <= BOX_LON[1] + HALO_DEG)
        & (c[:, 1] >= BOX_LAT[0] - HALO_DEG)
        & (c[:, 1] <= BOX_LAT[1] + HALO_DEG)
    )
    idx = np.nonzero(keep)[0]
    err = DiagonalErrorModel(np.asarray(obs.error_model.variance)[idx])  # type: ignore[attr-defined]
    return ObsWindow.from_arrays(
        c[idx, 0],
        c[idx, 1],
        c[idx, 2],
        obs.values()[idx],
        err,
        None if obs.mission is None else obs.mission[idx],
    )


def _boundary_distance(day: float, plan: WindowPlan) -> float:
    """Days to the nearest window start/end over the real WindowPlan."""
    return min(min(abs(day - w.start_day), abs(day - w.end_day)) for w in plan.windows)


def _score_on_validation(map_path: Path) -> dict[str, float]:
    """Blocked-j3-track skill of one map file: mu (+ lambda_x when it resolves)."""
    import sverdrup.validation.their_eval as te
    from sverdrup.validation.provenance_guard import assert_scored_not_assimilated

    assert_scored_not_assimilated(map_path, VAL_TRACK)  # Task-21 guard

    te._prepare_imports()
    from src.mod_inout import read_l3_dataset
    from src.mod_interp import interp_on_alongtrack

    box = dict(
        lon_min=295.0,
        lon_max=305.0,
        lat_min=33.0,
        lat_max=43.0,
        time_min="2017-01-01",
        time_max="2018-01-01",
    )
    ds_at = read_l3_dataset(str(VAL_TRACK), **box)
    time_a, lat_a, lon_a, ssh_a, interp = interp_on_alongtrack(
        str(map_path), ds_at, is_circle=False, **box
    )
    out = {
        "mu": float(
            leaderboard_nrmse(np.asarray(ssh_a, float), np.asarray(interp, float))
        )
    }
    try:
        out["lambda_x"] = float(
            effective_resolution_lambda_x(
                np.asarray(time_a),
                np.asarray(lat_a),
                np.asarray(lon_a),
                np.asarray(ssh_a, float),
                np.asarray(interp, float),
            )
        )
    except (UnresolvedScaleError, ShortTrackError) as exc:
        out["lambda_x"] = float("nan")
        _log(f"lambda_x unresolved for {map_path.name}: {type(exc).__name__}")
    return out


def _rung_map(
    spec: BasisSpec, els: object, s_sp: object, eta: np.ndarray, day: float, rung: int
) -> np.ndarray:
    """Exact single-rung day map: zero every other rung's spatial columns."""
    from sverdrup.methods.miost_basis import time_contract

    v = time_contract(spec, els, eta, day)  # type: ignore[arg-type]
    j_lo = int(els.identity[:, 5].min())  # type: ignore[attr-defined]
    j_hi = int(els.identity[:, 5].max())  # type: ignore[attr-defined]
    keep = np.zeros(v.size, dtype=bool)
    base = 0
    for s_idx, lay in enumerate(_layouts(spec, j_lo, j_hi)):
        n_sp = lay.nx * lay.ny * spec.n_dir * 2
        if s_idx == rung:
            keep[base : base + n_sp] = True
        base += n_sp
    return np.asarray(s_sp @ np.where(keep, v, 0.0))


def main() -> None:
    """Run the four probes; print + write the localization doc."""
    provider, grid, _ = baseline_config()
    import json

    cfg = json.loads(SCOPE.read_text())
    mdt = load_mdt_grid([Path(p) for p in cfg["mdt_paths"]], grid)
    obs = _halo_obs()
    plan = WindowPlan()
    _log(f"obs {len(obs):,}; solving both paths, 365 days (budgeted 1e-6/500)")

    windowed = Miost()
    single = Miost(plan=WindowPlan(starts=(-30.0,), w_days=425.0))
    days = list(range(365))
    maps_w, maps_s, rows = [], [], []
    for d in days:
        mw = np.asarray(windowed.solve(obs, grid, PARAMS, time_days=float(d)).mean)
        ms = np.asarray(single.solve(obs, grid, PARAMS, time_days=float(d)).mean)
        delta = mw - ms
        rows.append(
            {
                "day": d,
                "dist": _boundary_distance(float(d), plan),
                "max_abs": float(np.abs(delta).max()),
                "rms": float(np.sqrt((delta**2).mean())),
            }
        )
        maps_w.append(mw + mdt)
        maps_s.append(ms + mdt)
        if d % 60 == 0:
            _log(f"day {d}: max|D|={rows[-1]['max_abs']:.3f}")

    epoch = np.datetime64("2017-01-01")
    times = epoch + np.asarray(days, dtype="int64") * np.timedelta64(1, "D")
    lon2d, lat2d = np.meshgrid(grid.x, grid.y)
    p_w = OUT_DIR / "diag_local_windowed.nc"
    p_s = OUT_DIR / "diag_local_single.nc"
    write_map(times, np.unique(lat2d), np.unique(lon2d), np.stack(maps_w), p_w)
    write_map(times, np.unique(lat2d), np.unique(lon2d), np.stack(maps_s), p_s)

    # ---- Probe 1: blocked-validation skill for both maps (never c2) ----
    _log("probe 1: scoring both maps on the blocked j3 validation track")
    sc_w = _score_on_validation(p_w)
    sc_s = _score_on_validation(p_s)
    d_mu = sc_w["mu"] - sc_s["mu"]

    # ---- Probe 2: Delta vs boundary-distance profile ----
    edges = [0, 3, 6, 9, 12, 15, 18, 21, 100]
    prof = []
    dists = np.array([r["dist"] for r in rows])
    maxs = np.array([r["max_abs"] for r in rows])
    rmss = np.array([r["rms"] for r in rows])
    for lo, hi in zip(edges[:-1], edges[1:], strict=True):
        m = (dists >= lo) & (dists < hi)
        if m.any():
            prof.append(
                (
                    f"{lo}-{hi if hi < 100 else 'max'}",
                    int(m.sum()),
                    float(maxs[m].mean()),
                    float(maxs[m].max()),
                    float(rmss[m].mean()),
                )
            )
    corr = float(np.corrcoef(dists, maxs)[0, 1])
    near = float(maxs[dists < 6].mean()) if (dists < 6).any() else float("nan")
    far = float(maxs[dists >= 15].mean()) if (dists >= 15).any() else float("nan")
    profile_flat = abs(corr) < 0.2 and (near / far if far else 1.0) < 1.3

    # ---- Probe 3: scale + spatial attribution ----
    worst = max(rows, key=lambda r: float(r["max_abs"]))
    far_row = max(
        (r for r in rows if float(r["dist"]) >= 15),
        key=lambda r: float(r["max_abs"]),
        default=worst,
    )
    spec = Miost()._spec_from(PARAMS, grid)
    from sverdrup.methods.miost_basis import build_s_spatial

    attribution = []
    top_share = {}
    spatial: dict[str, object] = {}
    for label, row in (("worst", worst), ("far", far_row)):
        day = float(row["day"])
        per_rung = []
        # per-path per-rung maps via each path's own elements/coefficients
        for inst in (windowed, single):
            wins = inst._plan.covering(day)
            rung_maps = np.zeros((len(spec.ladder), lon2d.size))
            for w in wins:
                wgt = inst._plan.weight(w, day)
                els = spec.elements_for_window(w.start_day, w.w_days)
                s_sp = build_s_spatial(spec, els, lon2d.ravel(), lat2d.ravel())
                key = next(k for k in inst._eta_cache if k[0] == w.id)
                eta = inst._eta_cache[key]
                for r_i in range(len(spec.ladder)):
                    rung_maps[r_i] += wgt * _rung_map(spec, els, s_sp, eta, day, r_i)
            per_rung.append(rung_maps)
        d_rung = per_rung[0] - per_rung[1]
        sq = (d_rung**2).sum(axis=1)
        share_top2 = float(sq[-2:].sum() / max(sq.sum(), 1e-30))
        top_share[label] = share_top2
        attribution.append(
            (
                label,
                int(row["day"]),
                [f"{np.abs(d_rung[i]).max():.3f}" for i in range(len(spec.ladder))],
                share_top2,
            )
        )
        if label == "worst":
            # spatial pattern of the full worst-day Delta
            delta_field = maps_w[int(row["day"])] - maps_s[int(row["day"])]
            ny, nx = delta_field.shape
            iy, ix = np.unravel_index(np.abs(delta_field).argmax(), delta_field.shape)
            edge_cells = 5
            edge_band = np.zeros_like(delta_field, dtype=bool)
            edge_band[:edge_cells, :] = edge_band[-edge_cells:, :] = True
            edge_band[:, :edge_cells] = edge_band[:, -edge_cells:] = True
            spatial = {
                "argmax_cell": f"({int(iy)}, {int(ix)}) of ({ny}, {nx})",
                "argmax_dist_to_edge_cells": int(min(iy, ny - 1 - iy, ix, nx - 1 - ix)),
                "edge_band_max": float(np.abs(delta_field[edge_band]).max()),
                "interior_max": float(np.abs(delta_field[~edge_band]).max()),
            }

    # ---- Probe 4: J-identity on the single-window objective ----
    _log("probe 4: J-identity")
    w425 = single._plan.windows[0]
    lon_o, lat_o, t_o, y_o = _window_obs(obs, w425, spec.l_t_days)
    els_s = spec.elements_for_window(w425.start_day, w425.w_days)
    g = build_g(spec, els_s, lon_o, lat_o, t_o)
    q = DiagonalQ(rho=10.0, q_slope=2.0).variances_for(els_s)
    eta_single = single._eta_cache[
        next(k for k in single._eta_cache if k[0] == w425.id)
    ]
    # stitch: per single-window element, blend the windowed etas at the slot time
    dtd = spec.dt_days
    j_lo_s = int(els_s.identity[:, 5].min())
    j_hi_s = int(els_s.identity[:, 5].max())
    lays_s = _layouts(spec, j_lo_s, j_hi_s)
    eta_st = np.zeros(els_s.x_km.size)
    weight_sum = np.zeros(els_s.x_km.size)
    for w in plan.windows:
        els_w = spec.elements_for_window(w.start_day)
        key_w = next((k for k in windowed._eta_cache if k[0] == w.id), None)
        if key_w is None:
            continue  # window never solved (should not happen for 0..364 sweep)
        eta_w = windowed._eta_cache[key_w]
        j_lo_w = int(els_w.identity[:, 5].min())
        j_hi_w = int(els_w.identity[:, 5].max())
        lays_w = _layouts(spec, j_lo_w, j_hi_w)
        for ls, lw in zip(lays_s, lays_w, strict=True):
            n_sp = ls.nx * ls.ny * spec.n_dir * 2
            for j in range(max(j_lo_w, j_lo_s), min(j_hi_w, j_hi_s) + 1):
                t_slot = j * dtd
                if not (w.start_day <= t_slot <= w.end_day):
                    continue
                wgt = plan.weight(w, t_slot) if plan.covering(t_slot) else 0.0
                if wgt == 0.0:
                    continue
                sp = np.arange(n_sp)
                cols_s = ls.base + sp * ls.n_t + (j - j_lo_s)
                cols_w = lw.base + sp * lw.n_t + (j - j_lo_w)
                eta_st[cols_s] += wgt * eta_w[cols_w]
                weight_sum[cols_s] += wgt

    def _j(eta: np.ndarray) -> float:
        misfit = (g @ eta - y_o) / math.sqrt(R_REF)
        return float(misfit @ misfit + (eta**2 / q).sum())

    j_single, j_stitched = _j(np.asarray(eta_single)), _j(eta_st)
    j_ok = j_single <= j_stitched * (1 + 1e-9)

    # ---- close-rule evaluation ----
    attribution_top = all(v > 0.7 for v in top_share.values())
    if abs(d_mu) <= 0.005 and profile_flat and attribution_top and j_ok:
        rule = "CLOSE: fallback NOT INVOKED (skill-equivalent, flat profile, top-rung attribution)"
    elif not j_ok:
        rule = "DEFECT HUNT: J-identity violated — reference not the joint minimizer"
    elif not profile_flat and corr < 0:
        rule = "WINDOW-EDGE MECHANISM: profile decays with distance — implement the D4 pavement extension"
    elif d_mu <= -0.01:
        rule = "STOP: windowing costs >=0.01 mu — back to the owner"
    else:
        rule = "OWNER JUDGMENT: mixed signals — report and hold"

    lam_w = sc_w.get("lambda_x", float("nan"))
    lam_s = sc_s.get("lambda_x", float("nan"))
    lines = [
        "# MIOST equivalence localization (Task-11 D4 probes, owner-ordered)",
        "",
        "Solves at the Stage-A budgeted config (rtol 1e-6 target, maxiter 500 cap);",
        "map-space depth-insensitivity measured in the equivalence doc.",
        "",
        "## Probe 1 — blocked-validation skill (j3 track; never c2)",
        "",
        "| map | mu | lambda_x [km] |",
        "|---|---|---|",
        f"| windowed (product) | {sc_w['mu']:.4f} | {lam_w:.1f} |",
        f"| single-window (reference) | {sc_s['mu']:.4f} | {lam_s:.1f} |",
        "",
        f"**Delta-mu (windowed - single) = {d_mu:+.4f}**",
        "",
        "## Probe 2 — Delta vs distance to nearest window boundary",
        "",
        "| dist bin [d] | n days | mean max|D| | max max|D| | mean RMS |",
        "|---|---|---|---|---|",
    ]
    lines += [
        f"| {b} | {n} | {mm:.3f} | {mx:.3f} | {mr:.3f} |" for b, n, mm, mx, mr in prof
    ]
    lines += [
        "",
        f"corr(dist, max|D|) = {corr:+.3f}; near(<6 d) mean {near:.3f} vs "
        f"far(>=15 d) mean {far:.3f} -> profile "
        f"{'FLAT' if profile_flat else 'NOT flat'}.",
        "",
        "## Probe 3 — scale + spatial attribution",
        "",
        f"Ladder rungs (km): {[f'{s:.0f}' for s in spec.ladder]}",
        "",
        "| day | per-rung max|D_rung| | top-2-rung energy share |",
        "|---|---|---|",
    ]
    lines += [
        f"| {d} ({lbl}) | {vals} | {share:.2f} |" for lbl, d, vals, share in attribution
    ]
    lines += [
        "",
        f"Worst-day spatial: argmax at cell {spatial['argmax_cell']}, "
        f"{spatial['argmax_dist_to_edge_cells']} cells from the nearest edge; "
        f"edge-band(5) max {spatial['edge_band_max']:.3f} vs interior max "
        f"{spatial['interior_max']:.3f}.",
        "",
        "## Probe 4 — J-identity (single-window objective)",
        "",
        f"J(eta_single) = {j_single:.6e}; J(stitched windowed) = {j_stitched:.6e} -> "
        f"{'OK (reference is the better minimizer)' if j_ok else 'VIOLATED'}",
        "",
        "## Pre-registered close-rule outcome",
        "",
        f"**{rule}**",
        "",
    ]
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text("\n".join(lines))
    _log(f"doc written -> {DOC}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
