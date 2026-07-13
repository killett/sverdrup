"""Task-18 / spec 6.2 Stage-B diagnostic: seam dispersion + variance equivalence.

Measures the CRN residual on MEMBER DISPERSION: (a) per-output-day member std
fields from the production windowed plan, with the HEADLINE ratio
(blend-day worst / interior-day median) — worst-case-localized, never averaged
away; (b) the D4 harness extended to variance: windowed-vs-single-window member
std at the D4 diagnostic point (alpha=1.5, rho=10, q_slope=2, L_t=10), SAME
m and SAME CRN root on both sides (identity-keyed CRN makes the comparison
sharp); (c) a verdict line for the Task-19 gate.

Protocol: obs are TRAIN-ONLY (make_splits locked c2 / validation j3, then
train subset) — c2 is never touched. Member fields are evaluated via the
SPARSE S-path (build_s_spatial + time_contract) — NEVER BasisSpec.evaluate on
the production grid (dense gamma ~8 GB/window, the OOM-#3 trap). Exactly ONE
batched member solve per window: 9 windowed + 1 single = 10 solves total.

Usage:
    pixi run python scripts/diag_miost_seam_dispersion.py            # full year
    DIAG_DAYS=0-30 DIAG_M=4 pixi run python ...                      # smoke
    DIAG_MAXITER=2000 DIAG_RTOL=1e-8 DIAG_FLOOR=0 ...                # overrides
Launch the full year DETACHED (nohup + pid file); a watcher must treat
ZOMBIE as dead (ps -o stat = Z; kill -0 succeeds on zombies).
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import cast

import numpy as np

from sverdrup.application.splits import make_splits
from sverdrup.application.tuning.stage_a import _subset
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
from sverdrup.core.parameters import ConstantProvider
from sverdrup.distributions.miost_ensemble import (  # noqa: F401  (re-exported for the pinned tests)
    exclusive_days,
    merged_members,
    std_fields,
)
from sverdrup.methods.miost import CONVERGENCE_LOG, Miost
from sverdrup.methods.miost_basis import (
    BOX_LAT,
    BOX_LON,
    HALO_DEG,
)
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
DOC = Path("docs/validation/miost_seam_dispersion.md")
_T0 = time.time()


def _log(msg: str) -> None:
    """Print a timestamped, flushed heartbeat line."""
    s = int(time.time() - _T0)
    print(f"[+{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}] {msg}", flush=True)


def _rss() -> str:
    """Current and peak RSS from /proc (the Task-22 peak-model datapoint)."""
    vals = {}
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith(("VmRSS", "VmHWM")):
            k, v = line.split(":")
            vals[k] = float(v.split()[0]) / 1e6
    return f"RSS {vals.get('VmRSS', 0):.2f} GB / peak {vals.get('VmHWM', 0):.2f} GB"


def _days() -> list[float]:
    """Output days from DIAG_DAYS='lo-hi' (default full year 0-364)."""
    lo, hi = (os.environ.get("DIAG_DAYS") or "0-364").split("-")
    return [float(d) for d in range(int(lo), int(hi) + 1)]


def dispersion_summary(day_max: np.ndarray, blend: np.ndarray) -> dict[str, float]:
    """Worst-case-localized seam-dispersion headline.

    Args:
        day_max: Per-day spatial MAX of the member std field.
        blend: Per-day blend-zone flag.

    Returns:
        worst_blend (max over blend days), interior_median (median over
        interior days), and their ratio — the headline. The worst blend day
        is never averaged away.
    """
    worst_blend = float(day_max[blend].max())
    interior_median = float(np.median(day_max[~blend]))
    return {
        "worst_blend": worst_blend,
        "interior_median": interior_median,
        "ratio": worst_blend / interior_median,
    }


def _train_obs() -> ObsWindow:
    """Six missions, box+halo, TRAIN-ONLY (locked c2 / validation j3 held out)."""
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
    halo = ObsWindow.from_arrays(
        c[idx, 0],
        c[idx, 1],
        c[idx, 2],
        obs.values()[idx],
        err,
        None if obs.mission is None else obs.mission[idx],
    )
    split = make_splits(
        halo, by="mission", locked_missions=["c2"], validation_missions=["j3"]
    )
    return _subset(halo, split.train_idx)


def _summ(v: np.ndarray) -> tuple[float, float, float]:
    """(median, p95, max) of a per-day series."""
    return float(np.median(v)), float(np.percentile(v, 95)), float(v.max())


def main() -> None:
    """Run both sides, compute (a)+(b), write the doc with the (c) verdict."""
    days = _days()
    m = int(os.environ.get("DIAG_M", "50"))
    root = int(os.environ.get("DIAG_ROOT", "1"))
    rtol = float(os.environ.get("DIAG_RTOL", "1e-6"))
    maxiter = int(os.environ.get("DIAG_MAXITER", "500"))
    _, grid, _ = baseline_config()
    obs = _train_obs()
    _log(
        f"train-only obs: {len(obs)}; days {days[0]:.0f}..{days[-1]:.0f}; "
        f"m={m} root={root}; solver rtol={rtol:g} maxiter={maxiter}; {_rss()}"
    )

    plan_w = WindowPlan()
    plan_s = WindowPlan(starts=(-30.0,), w_days=425.0)
    windowed = Miost(pcg_rtol=rtol, pcg_maxiter=maxiter)
    single = Miost(plan=plan_s, pcg_rtol=rtol, pcg_maxiter=maxiter)

    def _on_window(wid: str, day: float) -> None:
        _log(f"  members solved: {wid} (exclusive day {day:.0f}); {_rss()}")

    CONVERGENCE_LOG.clear()
    _log("windowed member solves (9 windows) ...")
    spec_w, _, anoms_w, starts_w = merged_members(
        windowed, obs, grid, PARAMS, m, root, on_window=_on_window
    )
    _log("single-window member solve (1 window) ...")
    spec_s, _, anoms_s, starts_s = merged_members(
        single, obs, grid, PARAMS, m, root, on_window=_on_window
    )
    solves = [dict(e) for e in CONVERGENCE_LOG]
    _log(f"all member batches solved; {_rss()}")

    t0 = time.time()
    f_w = std_fields(spec_w, starts_w, anoms_w, grid, plan_w, days)
    f_s = std_fields(spec_s, starts_s, anoms_s, grid, plan_s, days)
    _log(f"std fields evaluated (S-path) in {time.time() - t0:.0f}s; {_rss()}")

    blend = np.array([len(plan_w.covering(d)) == 2 for d in days])
    day_max_w = f_w.max(axis=1)
    disp = dispersion_summary(day_max_w, blend)

    delta = np.abs(f_w - f_s).max(axis=1)  # per-day max|Delta std|
    d_b, d_i = delta[blend], delta[~blend]
    db_med, db_p95, db_max = _summ(d_b) if d_b.size else (0.0, 0.0, 0.0)
    di_med, di_p95, di_max = _summ(d_i) if d_i.size else (0.0, 0.0, 0.0)
    std_scale = float(np.median(f_s.max(axis=1)))
    worst_eq_day = float(np.asarray(days)[delta.argmax()])

    # SOLVER-FLOOR PROBE (Task-11 lesson: under-converged deltas are noise, not
    # signal): re-solve the worst blend day's covering windows deeper on the
    # WINDOWED side and measure how much its std field moves.
    floor = float("nan")
    if os.environ.get("DIAG_FLOOR", "1") != "0" and blend.any():
        try:
            d_star = float(np.asarray(days)[blend][day_max_w[blend].argmax()])
            _log(
                f"floor probe: windowed day {d_star:.0f} at maxiter {maxiter + 1000} ..."
            )
            deep = (
                Miost(pcg_rtol=rtol, pcg_maxiter=maxiter + 1000)
                .sample_members(obs, grid, PARAMS, d_star, m, root)
                .underlying
            )  # raw coefficient internals (Phase-9 §3 wrapper return)
            f_deep = std_fields(
                deep._spec, deep._window_starts, deep._anoms, grid, plan_w, [d_star]
            )[0]
            f_ref = f_w[days.index(d_star)]
            floor = float(np.abs(f_deep - f_ref).max())
            _log(f"floor probe: max|std shift| = {floor:.5f} m; {_rss()}")
        except Exception as exc:  # never lose the 10 solves to a probe failure
            _log(f"floor probe FAILED ({exc!r}) — doc written with floor=nan")

    seam_flag = disp["ratio"] < 0.9 or disp["ratio"] > 1.1
    eq_flag = db_max > 0.10 * std_scale
    verdict = (
        f"TASK-19 GATE VERDICT: seam-dispersion ratio (blend worst / interior "
        f"median, spatial-max) = {disp['ratio']:.3f} "
        f"({'FLAGGED — outside [0.9, 1.1]' if seam_flag else 'no seam artifact at the 10% heuristic'}); "
        f"variance equivalence: worst-day max|Delta std| = {db_max:.4f} m blend / "
        f"{di_max:.4f} m interior vs std scale {std_scale:.4f} m "
        f"({'FLAGGED — exceeds 10% of scale' if eq_flag else 'within 10% of scale'}); "
        f"windowed solver-floor probe {floor:.5f} m — deltas "
        f"{'clear the floor' if db_max > 3 * floor else 'do NOT clearly exceed the floor (solver-noise caveat)'}."
    )

    member_rows = [e for e in solves if e.get("kind") == "member-batch"]
    lines = [
        "# MIOST Stage-B seam-dispersion + variance-equivalence diagnostic (Task 18)",
        "",
        f"- Params: D4 diagnostic point alpha=1.5, rho=10 (log10_rho=1), q_slope=2, "
        f"L_t=10; grid 0.2 deg {grid.shape}; obs TRAIN-ONLY box+halo "
        f"({len(obs):,} points; c2 locked, j3 validation — neither assimilated).",
        f"- Members: m={m}, CRN root={root} — SAME root on BOTH sides "
        "(identity-keyed CRN; the comparison isolates windowing).",
        f"- Solver: budgeted rtol {rtol:g} / maxiter {maxiter} on BOTH sides; "
        "achieved residuals below (budgeted-solve honesty).",
        f"- Days: {days[0]:.0f}..{days[-1]:.0f} ({len(days)}); blend {int(blend.sum())}, "
        f"interior {int((~blend).sum())}. Exactly one batched member solve per window "
        "(9 windowed + 1 single); member fields via the sparse S-path.",
        "",
        "## (a) Seam dispersion — per-day spatial MAX of member std [m]",
        "",
        "| class | median | p95 | max |",
        "|---|---|---|---|",
        f"| blend days | {_summ(day_max_w[blend])[0]:.4f} | {_summ(day_max_w[blend])[1]:.4f} | **{disp['worst_blend']:.4f}** |"
        if blend.any()
        else "| blend days | - | - | - |",
        f"| interior days | {_summ(day_max_w[~blend])[0]:.4f} | {_summ(day_max_w[~blend])[1]:.4f} | {_summ(day_max_w[~blend])[2]:.4f} |",
        "",
        f"**HEADLINE ratio (blend worst / interior median) = {disp['ratio']:.3f}** "
        f"({disp['worst_blend']:.4f} / {disp['interior_median']:.4f}).",
        "",
        "## (b) Variance equivalence — per-day max|Delta member-std| windowed vs single [m]",
        "",
        "| class | median | p95 | max |",
        "|---|---|---|---|",
        f"| blend days | {db_med:.4f} | {db_p95:.4f} | **{db_max:.4f}** |",
        f"| interior days | {di_med:.4f} | {di_p95:.4f} | {di_max:.4f} |",
        "",
        f"Scale context: median per-day spatial-max single-window member std = "
        f"{std_scale:.4f} m. Worst day: {worst_eq_day:.0f}.",
        f"Windowed solver-floor probe (worst blend day, maxiter +1000): "
        f"max|std shift| = {floor:.5f} m.",
        "",
        "## Member-batch achieved residuals (budgeted solve)",
        "",
        "| window | iterations | final rel residual |",
        "|---|---|---|",
    ]
    lines += [
        f"| {e['window']} | {e['iterations']} | "
        f"{float(cast('float', e['final_rel_residual'])):.2e} |"
        for e in member_rows
    ]
    lines += ["", "## Verdict", "", verdict, "", f"Run footprint: {_rss()}.", ""]
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text("\n".join(lines))
    _log(f"doc written -> {DOC}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
