"""Phase-13 per-lane sweep execution (plan Tasks 7/8; spec §7).

Runs ONE lane's paired Sobol trials + pre-registered anchors as FULL-YEAR
point solves (the sealed budget resolved to full scoring — no screening),
persists every trial's j3 validation-track residual arrays (band source),
checkpoints each record AS SCORED (crash-durable), and selects the lane
winner via the read-time selection layer (refusal clock inside).

Launch rule: REFUSES without the sealed Task-6 bundle (band protocol +
budget evidence); the Task-8 wall estimate is evaluated against the
owner-amendable 12 h default BEFORE launch (standing rule 3b).

Scope discipline:
    SVERDRUP_PHASE13_SCOPE=dev  -> 12-day window, 2 trials; evidence under
                                   phase13.miost.lanes_dev.* (NEVER gate
                                   evidence).
    (default / full)            -> sealed budget numbers; evidence under
                                   phase13.miost.lanes.<lane>.

c2 is NEVER touched: train-only assimilation (c2 locked out by the
standing split), j3-only scoring, assert_scored_not_assimilated on every
map.

Usage:
    SVERDRUP_PHASE13_SCOPE=dev pixi run python scripts/phase13_lane_run.py --lane D
    nohup pixi run python scripts/phase13_lane_run.py --lane D > laneD.log 2>&1 &
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import numpy as np

from sverdrup.application.tuning.lane_compare import load_protocol, select_lane_winner
from sverdrup.application.tuning.objective import BASELINE_BAR_MU
from sverdrup.eval.skill_score import leaderboard_nrmse
from sverdrup.eval.spectral import (
    ShortTrackError,
    UnresolvedScaleError,
    effective_resolution_lambda_x,
)
from sverdrup.validation.phase13_lanes import (
    LANES,
    Trial,
    anchors_for,
    lane_bars,
    params_for_trial,
    rspec_for_trial,
    sobol_trials,
)

_OUT_ROOT = Path("data/2021a_ssh_mapping_ose/ours")
_RESULTS = _OUT_ROOT / "stage_miost_gate_results.json"
_VAL_TRACK = Path(
    "data/2021a_ssh_mapping_ose/dc_obs/"
    "dt_gulfstream_j3_phy_l3_20161201-20180131_285-315_23-53.nc"
)
# c2 never appears here; the standing split locks it out of assimilation.

_SCOPE = os.environ.get("SVERDRUP_PHASE13_SCOPE", "full")
if _SCOPE not in {"dev", "full"}:
    raise SystemExit(f"SVERDRUP_PHASE13_SCOPE must be 'dev' or 'full', got {_SCOPE!r}")

_DEV_DAYS = [float(d) for d in range(60, 72)]
_FULL_DAYS = [float(d) for d in range(0, 365)]
_MU_BAR = BASELINE_BAR_MU  # λx computed only above the µ floor


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _evidence_root(lane: str) -> str:
    base = "phase13.miost.lanes" if _SCOPE == "full" else "phase13.miost.lanes_dev"
    return f"{base}.{lane}"


def _write_evidence(key_path: str, value: object) -> None:
    """Atomic nested-key write. SINGLE-WRITER: lanes run SEQUENTIALLY."""
    from sverdrup.application.calibration.harness import (  # noqa: PLC0415
        atomic_write_json,
    )

    results = json.loads(_RESULTS.read_text())
    keys = key_path.split(".")
    node: dict[str, Any] = results
    for k in keys[:-1]:
        node = node.setdefault(k, {})
    node[keys[-1]] = value
    atomic_write_json(_RESULTS, results)


def _read_evidence() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(_RESULTS.read_text()))


def _load_ctx() -> dict[str, Any]:
    """Load obs (train split), grid, MDT — the phase-10 lane pattern.

    Six-file load + mission split (c2 locked, j3 validation) and the
    SIX-FILE MDT list — the signed scorer's convention (the five-file MDT
    variant shifts µ at 4e-6 and would break lane-0 reproduction).
    """
    from sverdrup.application.splits import make_splits  # noqa: PLC0415
    from sverdrup.validation.input_adapter import (  # noqa: PLC0415
        load_mapping_obs,
        load_mdt_grid,
    )
    from sverdrup.validation.params import baseline_config  # noqa: PLC0415
    from sverdrup.validation.run import _subset, halo_obs  # noqa: PLC0415

    obs_dir = Path("data/2021a_ssh_mapping_ose/dc_obs")
    mapping = [
        obs_dir / f"dt_gulfstream_{m}_phy_l3_20161201-20180131_285-315_23-53.nc"
        for m in ("alg", "h2g", "j2g", "j2n", "j3", "s3a")
    ]
    provider, grid, half = baseline_config()
    obs_all = load_mapping_obs(mapping, provider)
    split = make_splits(
        obs_all, by="mission", locked_missions=["c2"], validation_missions=["j3"]
    )
    train = halo_obs(_subset(obs_all, split.train_idx), grid)
    mdt = load_mdt_grid(mapping, grid)
    return {"train": train, "grid": grid, "half": half, "mdt": np.asarray(mdt)}


def _interp_track(mean_p: Path) -> dict[str, np.ndarray]:
    """Interp a mean map onto the j3 track (harness box; finite subset)."""
    from sverdrup.validation.provenance_guard import (  # noqa: PLC0415
        assert_scored_not_assimilated,
    )
    from sverdrup.validation.vendor import prepare_vendored_imports  # noqa: PLC0415

    assert_scored_not_assimilated(mean_p, _VAL_TRACK)
    prepare_vendored_imports()
    from src.mod_inout import read_l3_dataset  # noqa: PLC0415
    from src.mod_interp import interp_on_alongtrack  # noqa: PLC0415

    box = dict(
        lon_min=295.0,
        lon_max=305.0,
        lat_min=33.0,
        lat_max=43.0,
        time_min="2017-01-01",
        time_max="2018-01-01",
    )
    ds_at = read_l3_dataset(str(_VAL_TRACK), **box)
    t_a, lat_a, lon_a, ssh, mu = interp_on_alongtrack(
        str(mean_p), ds_at, is_circle=False, **box
    )
    ssh, mu = np.asarray(ssh, float), np.asarray(mu, float)
    ok = np.isfinite(ssh) & np.isfinite(mu)
    return {
        "time": np.asarray(t_a)[ok],
        "lat": np.asarray(lat_a, float)[ok],
        "lon": np.asarray(lon_a, float)[ok],
        "ssh": ssh[ok],
        "mean_interp": mu[ok],
    }


def _scores_from_track(trk: dict[str, np.ndarray]) -> dict[str, float]:
    """Score a persisted track: µ, λx above the bar (POINT trials)."""
    mu = float(leaderboard_nrmse(trk["ssh"], trk["mean_interp"]))
    scores: dict[str, float] = {"mu_score": mu}
    if mu >= _MU_BAR:
        try:
            scores["lambda_x"] = float(
                effective_resolution_lambda_x(
                    trk["time"], trk["lat"], trk["lon"], trk["ssh"], trk["mean_interp"]
                )
            )
        except (ShortTrackError, UnresolvedScaleError) as exc:
            scores["lambda_x_error"] = float("nan")
            print(f"  [warn] lambda_x failed: {type(exc).__name__}", flush=True)
    return scores


def _score_trial(
    trial: Trial, ctx: dict[str, Any], npz_path: Path, days: list[float]
) -> tuple[dict[str, float], dict[str, Any]]:
    """Full-span point solve for one trial; persists the residual npz.

    Returns:
        (scores, PCG telemetry — the §2 rider-4 conditioning watch row).
    """
    import tempfile  # noqa: PLC0415

    from sverdrup.core.parameters import ConstantProvider  # noqa: PLC0415
    from sverdrup.methods.miost import CONVERGENCE_LOG, Miost  # noqa: PLC0415
    from sverdrup.validation.output_adapter import write_map  # noqa: PLC0415

    # FRESH method per trial: every window solves exactly once (then the
    # day loop reuses the cache), so the telemetry below captures ALL of
    # this trial's window solves — nothing is served from a prior trial's
    # cache (params_key differs per trial anyway).
    method = Miost(rspec=rspec_for_trial(trial))
    params = ConstantProvider(params_for_trial(trial))
    grid = ctx["grid"]
    CONVERGENCE_LOG.clear()
    maps = [np.asarray(method.solve(ctx["train"], grid, params, d).mean) for d in days]
    entries = [dict(e) for e in CONVERGENCE_LOG if "kind" not in e]
    telemetry = {
        "n_window_solves": len(entries),
        "pcg_iterations": [int(cast(int, e["iterations"])) for e in entries],
        "pcg_max_final_rel_residual": max(
            (float(cast(float, e["final_rel_residual"])) for e in entries),
            default=0.0,
        ),
    }
    epoch = np.datetime64("2017-01-01")
    times = epoch + np.asarray(days, dtype="int64") * np.timedelta64(1, "D")
    stack = np.stack(maps) + ctx["mdt"][None]
    with tempfile.TemporaryDirectory() as td:
        mean_p = Path(td) / "mean.nc"
        write_map(times, grid.y, grid.x, stack, mean_p)
        trk = _interp_track(mean_p)
    np.savez(npz_path, **cast(Any, trk))
    return _scores_from_track(trk), telemetry


def make_record(
    *,
    lane: str,
    index: int,
    anchor: bool,
    trial: Trial,
    scores: dict[str, float],
    telemetry: dict[str, Any],
    created_utc: str,
    residuals_npz: str,
) -> dict[str, Any]:
    """Build one evidence record (per-bar outcomes itemized)."""
    bars = {b.metric: bool(b.passes(scores)) for b in lane_bars()}
    return {
        "created_utc": created_utc,
        "lane": lane,
        "index": index,
        "anchor": anchor,
        "scope": "full" if _SCOPE == "full" else "dev",
        "trial": trial,
        "scores": scores,
        "bars": bars,
        "admissible": all(bars.values()),
        "pcg_telemetry": telemetry,
        "residuals_npz": residuals_npz,
    }


def main_for_lane(lane: str) -> None:
    """Run one lane end-to-end: trials + anchors -> records -> winner.

    Raises:
        SystemExit: On a missing bundle (launch rule), a lane the sealed
            budget excludes, or no admissible trial.
    """
    ev = _read_evidence()
    p13 = ev.get("phase13", {})
    budget = p13.get("probe", {}).get("budget")
    proto_ptr = p13.get("band_protocol")
    if not budget or not proto_ptr:
        raise SystemExit(
            "run scripts/phase13_prereg.py first (budget/protocol missing — "
            "the launch rule refuses an unsealed state)"
        )
    protocol = load_protocol(Path(proto_ptr["path"]), expected_sha=proto_ptr["sha256"])

    if _SCOPE == "dev":
        days = _DEV_DAYS
        n_trials = 2
    else:
        if budget["screening_contingency_active"]:
            raise SystemExit(
                "screening contingency ACTIVE in the sealed budget: this "
                "runner implements the full-score path only — refuse to "
                "improvise"
            )
        if lane not in {*budget["lanes"], "lane0"}:
            raise SystemExit(
                f"lane {lane!r} is not in the sealed budget's lane set "
                f"{budget['lanes']} — record 'not run' instead of sweeping"
            )
        days = _FULL_DAYS
        n_trials = int(budget["n_per_lane"])

    lanes_key = "lanes" if _SCOPE == "full" else "lanes_dev"
    winners_prior: dict[str, Trial] = {}
    for other in LANES:
        w = p13.get("miost", {}).get(lanes_key, {}).get(other, {}).get("winner")
        if w:
            winners_prior[other] = dict(w["trial"])
    anchors = anchors_for(lane, winners_prior)
    trials = sobol_trials(lane, n_trials)
    all_points: list[tuple[Trial, bool]] = [(t, False) for t in trials] + [
        (a, True) for a in anchors
    ]
    print(
        f"[lane {lane}] scope={_SCOPE} n_trials={n_trials} anchors={len(anchors)} "
        f"days={len(days)}",
        flush=True,
    )

    ctx = _load_ctx()
    sink = f"{_evidence_root(lane)}.records"
    existing = (
        p13.get("miost", {}).get(lanes_key, {}).get(lane, {}).get("records") or []
    )
    records: list[dict[str, Any]] = list(existing)
    # Resume-identity guard (Task-7 review): stale checkpoints from a run
    # with a DIFFERENT point list (e.g. an owner-amended wall changing n)
    # must never alias onto new indices — verify each resumed record's
    # trial dict against the current list or refuse.
    for idx, rec in enumerate(records):
        if idx >= len(all_points) or rec["trial"] != all_points[idx][0]:
            raise SystemExit(
                f"stale checkpoint records for lane {lane!r} (trial list "
                f"changed at index {idx}) — clear {sink} before rerunning"
            )
    t0 = time.monotonic()
    for idx, (trial, is_anchor) in enumerate(all_points):
        if idx < len(records):
            continue  # crash-durable resume: already scored + checkpointed
        tag = "dev_" if _SCOPE == "dev" else ""
        npz = _OUT_ROOT / f"phase13_residuals_{tag}{lane}_{idx}.npz"
        t1 = time.monotonic()
        scores, telemetry = _score_trial(trial, ctx, npz, days)
        records.append(
            make_record(
                lane=lane,
                index=idx,
                anchor=is_anchor,
                trial=trial,
                scores=scores,
                telemetry=telemetry,
                created_utc=_now(),
                residuals_npz=str(npz),
            )
        )
        _write_evidence(sink, records)  # checkpoint AS SCORED
        print(
            f"[lane {lane}] {idx + 1}/{len(all_points)} "
            f"mu={scores.get('mu_score', float('nan')):.4f} "
            f"lx={scores.get('lambda_x', float('nan')):.1f} "
            f"iters_max={max(telemetry['pcg_iterations'], default=0)} "
            f"({time.monotonic() - t1:.0f}s)",
            flush=True,
        )
    print(f"[lane {lane}] scoring done in {time.monotonic() - t0:.0f}s", flush=True)

    candidates = [r for r in records if r["admissible"]]
    smoke_fallback = False
    if not candidates and _SCOPE == "dev":
        # DEV-ONLY plumbing fallback (phase-10 pattern): arbitrary dev
        # points may legitimately fail the LIVE µ bar; the smoke still
        # exercises selection. Labeled loudly; never full-scope semantics.
        smoke_fallback = True
        candidates = [
            dict(r, admissible=True, smoke_admissible_override=True) for r in records
        ]
        print(
            f"[lane {lane}] DEV SMOKE FALLBACK: selecting over inadmissible", flush=True
        )
    if not candidates:
        _write_evidence(f"{_evidence_root(lane)}.winner", None)
        raise SystemExit(f"[lane {lane}] NO admissible trial — STOP")

    def _loader(rec: dict[str, Any]) -> dict[str, np.ndarray]:
        with np.load(rec["residuals_npz"], allow_pickle=False) as z:
            return {k: z[k] for k in z.files}

    winner = select_lane_winner(candidates, protocol, _loader)
    if smoke_fallback:
        winner["smoke_admissible_override"] = True
    _write_evidence(f"{_evidence_root(lane)}.winner", winner)
    print(
        f"[lane {lane}] WINNER index={winner['index']} "
        f"mu={winner['scores']['mu_score']:.4f} "
        f"lambda_x={winner['scores'].get('lambda_x', float('nan')):.1f}",
        flush=True,
    )
    print(f"[lane {lane}] DONE", flush=True)


def main() -> None:
    """CLI entry: one lane per invocation (sequential by protocol)."""
    parser = argparse.ArgumentParser(description="Phase-13 lane run (spec §7).")
    parser.add_argument("--lane", choices=sorted(set(LANES) - {"lane0"}), required=True)
    args = parser.parse_args()
    main_for_lane(args.lane)


if __name__ == "__main__":
    main()
