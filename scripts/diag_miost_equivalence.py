"""Task-11 / D4 REQUIRED diagnostic: windowed-vs-single-window MIOST equivalence.

Solves 2017 BOTH ways at alpha=1.5 on the real dc_obs — the production windowed
plan (W=60 / V=15 / stride 45 + right-aligned last window) vs ONE 425-day window
[-30, 395] — with identical params (rho=10, q_slope=2, L_t=10), and reports the
windowing error Delta = mean_windowed - mean_single per output day.

Worst-case-localized reporting (standing rule): blend-day and interior-day
distributions are separated and the HEADLINE is the worst blend-day max|Delta| —
never a year-RMS that launders localized seam defects.

Output: docs/validation/miost_equivalence_diagnostic.md + stdout table.
Owner decides the pavement +-L_t extension fallback from the doc (plan Task 11).

Usage:
    pixi run python scripts/diag_miost_equivalence.py           # full year
    DIAG_DAYS=0-30 pixi run python scripts/diag_miost_equivalence.py   # smoke
    DIAG_MAXITER=4000 DIAG_RTOL=1e-8 ...   # convergence-sensitivity variant
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import numpy as np

from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
from sverdrup.core.parameters import ConstantProvider
from sverdrup.methods.miost import Miost
from sverdrup.methods.miost_basis import BOX_LAT, BOX_LON, HALO_DEG
from sverdrup.methods.miost_windows import WindowPlan
from sverdrup.validation.input_adapter import load_mapping_obs
from sverdrup.validation.params import baseline_config

OBS_PATHS = [
    Path("data/2021a_ssh_mapping_ose/dc_obs")
    / f"dt_gulfstream_{m}_phy_l3_20161201-20180131_285-315_23-53.nc"
    for m in ("alg", "h2g", "j2g", "j2n", "j3", "s3a")
]
PARAMS = ConstantProvider(
    {"spacing_alpha": 1.5, "log10_rho": 1.0, "q_slope": 2.0, "l_t_days": 10.0}
)
DOC = Path("docs/validation/miost_equivalence_diagnostic.md")
_T0 = time.time()


def _log(msg: str) -> None:
    """Print a timestamped, flushed heartbeat line."""
    s = int(time.time() - _T0)
    print(f"[+{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}] {msg}", flush=True)


def _days() -> list[int]:
    """Output days from DIAG_DAYS='lo-hi' (default full year 0-364)."""
    lo, hi = (os.environ.get("DIAG_DAYS") or "0-364").split("-")
    return list(range(int(lo), int(hi) + 1))


def _halo_obs() -> ObsWindow:
    """Load the six mapping missions, subset to the box + halo (production framing)."""
    provider, _, _ = baseline_config()
    obs = load_mapping_obs(OBS_PATHS, provider)
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


def main() -> None:
    """Solve both ways, print the comparison, write the doc."""
    days = _days()
    _, grid, _ = baseline_config()
    obs = _halo_obs()
    _log(f"obs loaded: {len(obs)} in box+halo; days {days[0]}..{days[-1]}")

    maxiter = int(os.environ.get("DIAG_MAXITER", "500"))
    rtol = float(os.environ.get("DIAG_RTOL", "1e-6"))
    _log(f"solver: pcg_rtol={rtol} pcg_maxiter={maxiter}")
    windowed = Miost(pcg_rtol=rtol, pcg_maxiter=maxiter)
    single = Miost(
        plan=WindowPlan(starts=(-30.0,), w_days=425.0),
        pcg_rtol=rtol,
        pcg_maxiter=maxiter,
    )
    ref_plan = WindowPlan()

    rows: list[dict[str, float | int | bool]] = []
    for d in days:
        t0 = time.time()
        mw = np.asarray(windowed.solve(obs, grid, PARAMS, time_days=float(d)).mean)
        ms = np.asarray(single.solve(obs, grid, PARAMS, time_days=float(d)).mean)
        delta = mw - ms
        rows.append(
            {
                "day": d,
                "blend": len(ref_plan.covering(float(d))) == 2,
                "max_abs": float(np.abs(delta).max()),
                "rms": float(np.sqrt((delta**2).mean())),
                "field_std": float(ms.std()),
            }
        )
        if time.time() - t0 > 5 or d % 30 == 0:
            _log(
                f"day {d:3d} ({'blend' if rows[-1]['blend'] else 'interior'}): "
                f"max|D|={rows[-1]['max_abs']:.4f} rms={rows[-1]['rms']:.4f} "
                f"({time.time() - t0:.0f}s)"
            )

    # SOLVER-NOISE FLOOR: same windowed path at maxiter+2000 on the worst day —
    # the windowing verdict is only valid where |Delta| clearly exceeds this.
    worst_day = float(max(rows, key=lambda r: float(r["max_abs"]))["day"])
    deeper = Miost(pcg_rtol=rtol, pcg_maxiter=maxiter + 2000)
    mw_ref = np.asarray(windowed.solve(obs, grid, PARAMS, time_days=worst_day).mean)
    mw_deep = np.asarray(deeper.solve(obs, grid, PARAMS, time_days=worst_day).mean)
    noise_floor = float(np.abs(mw_ref - mw_deep).max())
    _log(f"solver-noise floor (day {worst_day:.0f}, +2000 iters): {noise_floor:.4f} m")

    blend = [r for r in rows if r["blend"]]
    interior = [r for r in rows if not r["blend"]]

    def _summ(
        rs: list[dict[str, float | int | bool]], key: str
    ) -> tuple[float, float, float]:
        v = np.array([r[key] for r in rs], dtype=float)
        return float(np.median(v)), float(np.percentile(v, 95)), float(v.max())

    b_med, b_p95, b_max = _summ(blend, "max_abs") if blend else (0.0, 0.0, 0.0)
    i_med, i_p95, i_max = _summ(interior, "max_abs") if interior else (0.0, 0.0, 0.0)
    field_std = float(np.median([r["field_std"] for r in rows]))
    worst = max(rows, key=lambda r: r["max_abs"])

    # Fallback heuristic surfaced for the owner (the DECISION is the owner's):
    # invoke the pavement +-L_t extension if the worst blend-day max|Delta| is
    # large vs the field scale OR clearly dominated by blend days — and only
    # where the deltas exceed the measured solver-noise floor.
    fallback = b_max > 0.05 or (i_max > 0 and b_max > 3.0 * i_max)
    verdict = (
        f"FALLBACK NEEDED: {'yes' if fallback else 'no'} — worst blend-day "
        f"max|Delta| = {b_max:.4f} m ({100 * b_max / max(field_std, 1e-12):.1f}% of the "
        f"median field std {field_std:.3f} m); interior worst = {i_max:.4f} m; "
        f"ratio blend/interior = {b_max / max(i_max, 1e-12):.2f}; "
        f"solver-noise floor {noise_floor:.4f} m "
        f"({'DELTAS ABOVE floor — attributable' if max(b_max, i_max) > 3 * noise_floor else 'deltas NOT clearly above floor — solver-noise-dominated, verdict INVALID'})"
    )

    top = sorted(rows, key=lambda r: -float(r["max_abs"]))[:10]
    lines = [
        "# MIOST windowed-vs-single-window equivalence diagnostic (Task 11 / D4)",
        "",
        f"- Params: alpha=1.5, rho=10 (log10_rho=1), q_slope=2, L_t=10; grid 0.2 deg "
        f"{grid.shape}; obs = 6 mapping missions, box+halo ({len(obs):,} points).",
        "- Windowed: production WindowPlan (9 windows, W=60/V=15/stride 45, "
        "right-aligned last). Single: one 425-day window [-30, 395].",
        f"- Days solved: {days[0]}..{days[-1]} ({len(days)}); blend days: {len(blend)}, "
        f"interior days: {len(interior)}.",
        f"- PCG rtol {rtol:g} / maxiter {maxiter} on BOTH paths (identical solver "
        "settings; per-window residuals in the run log).",
        "",
        "## Per-day max|Delta| [m] (worst-case-localized; the headline metric)",
        "",
        "| class | median | p95 | max |",
        "|---|---|---|---|",
        f"| blend days | {b_med:.4f} | {b_p95:.4f} | **{b_max:.4f}** |",
        f"| interior days | {i_med:.4f} | {i_p95:.4f} | {i_max:.4f} |",
        "",
        f"Median single-window field std (scale context): {field_std:.3f} m.",
        f"Solver-noise floor (windowed path, maxiter {maxiter} vs +2000, worst day): "
        f"max|delta| = {noise_floor:.4f} m — Delta attribution requires clearing this.",
        f"Worst day overall: day {worst['day']} "
        f"({'blend' if worst['blend'] else 'interior'}), max|Delta| = "
        f"{worst['max_abs']:.4f} m, RMS = {worst['rms']:.4f} m.",
        "",
        "## Ten worst days",
        "",
        "| day | class | max|Delta| | RMS Delta | field std |",
        "|---|---|---|---|---|",
    ]
    lines += [
        f"| {r['day']} | {'blend' if r['blend'] else 'interior'} | "
        f"{r['max_abs']:.4f} | {r['rms']:.4f} | {r['field_std']:.3f} |"
        for r in top
    ]
    lines += [
        "",
        "## Verdict",
        "",
        verdict,
        "",
        "**Owner checkpoint:** the pavement +-L_t temporal-slot extension (D4 "
        "fallback) is NOT implemented; decide invoke / not-needed from the numbers "
        "above before Task 13.",
        "",
    ]
    doc = DOC
    if maxiter != 500 or rtol != 1e-6:
        doc = DOC.with_name(DOC.stem + "_sensitivity.md")
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text("\n".join(lines))
    _log(f"doc written -> {doc}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
