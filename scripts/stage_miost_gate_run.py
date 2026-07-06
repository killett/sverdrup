"""Durable Stage-A MIOST gate runner: Sobol then BO(rounds=4), c2 once, evidence JSON.

Mirrors scripts/stage_b_gate_run.py: per-strategy rows persist the INSTANT they
complete; heartbeat per trial; StageANoAdmissible is RECORDED as a diagnostic row
and the process exits cleanly (the d7376b8 pattern — smoke must never ERROR).

Scope is env-selected (the committed 12-day dev fixture is never mutated):
    SVERDRUP_MIOST_SCOPE=dev   -> the 12-day dev fixture as-is (smoke confirm)
    SVERDRUP_MIOST_SCOPE=full  -> full-2017 derived in-memory (default; multi-hour)
    SVERDRUP_MIOST_N=<int>     -> n_trials per strategy (default 16)

Run (detached):
    nohup pixi run python scripts/stage_miost_gate_run.py \
        > data/2021a_ssh_mapping_ose/ours/stage_miost_gate.log 2>&1 &

Results: data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json
"""

from __future__ import annotations

import ast
import json
import os
import re
import sys
import tempfile
import time
import traceback
from pathlib import Path
from typing import Any

import numpy as np

from sverdrup.application.tuning.bayesopt import BayesianOptimization
from sverdrup.application.tuning.feasibility import (
    CoherenceFeasibility,
    CompositeFeasibility,
    StoredGFeasibility,
)
from sverdrup.application.tuning.scorer import ValidationTrackScorer
from sverdrup.application.tuning.stage_a import StageANoAdmissible, StageAReport
from sverdrup.application.tuning.stage_miost import run_stage_miost
from sverdrup.application.tuning.strategy import SearchStrategy
from sverdrup.core.observations import ObsWindow
from sverdrup.core.parameters import ConstantProvider
from sverdrup.methods.miost import CONVERGENCE_LOG, Miost, _params_key_hash
from sverdrup.methods.miost_basis import BOX_LAT, BOX_LON, HALO_DEG
from sverdrup.methods.miost_solver import PCG_MAXITER, PCG_RTOL
from sverdrup.methods.miost_windows import L_T_MAX, WindowPlan
from sverdrup.validation.input_adapter import load_mapping_obs
from sverdrup.validation.params import baseline_config

DEV_FIX = Path("tests/validation/fixtures/stage_a_scope.json")
OUT_DIR = Path("data/2021a_ssh_mapping_ose/ours")
RESULTS = OUT_DIR / "stage_miost_gate_results.json"
LOG_FILE = OUT_DIR / "stage_miost_gate.log"
REPLAY_FILE = OUT_DIR / "stage_miost_gate_replay_cache.json"
SCOPE_MODE = os.environ.get("SVERDRUP_MIOST_SCOPE", "full")  # "dev" | "full"
N_TRIALS = int(os.environ.get("SVERDRUP_MIOST_N", "16"))
BO_ROUNDS = 4
SEED = 1

_T0 = time.time()


def _stamp() -> str:
    """Return elapsed wall-clock as HH:MM:SS since process start."""
    s = int(time.time() - _T0)
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"


def _log(msg: str) -> None:
    """Print a timestamped, flushed heartbeat line."""
    print(f"[+{_stamp()}] {msg}", flush=True)


# --- replay cache: relaunch-after-crash recovery of already-measured trials ----------
# Launch-state amendment (owner-approved 2026-07-05): after the OOM at BO
# trial 27, a relaunch re-proposes the IDENTICAL points (deterministic seed +
# persisted Sobol history), so trials measured by the dead run replay from
# (params -> scores) parsed out of its log + results JSON instead of
# re-solving ~20 min each. Kill-switch: SVERDRUP_MIOST_REPLAY=0.

_TRIAL_START = re.compile(r"trial (\d+): (\{.*\}) -> solving ")
_TRIAL_SCORE = re.compile(r"trial (\d+): (\{.*\}) \(\d+s\)\s*$")


def _replay_key(params: dict[str, float]) -> str:
    """Order-independent exact key; float repr round-trips the log losslessly."""
    return json.dumps({k: repr(float(v)) for k, v in params.items()}, sort_keys=True)


def _replay_from_log(log_path: Path) -> dict[str, dict[str, float]]:
    """Pair 'trial N: {params} -> solving' with 'trial N: {scores} (Ns)' lines.

    A trial whose start line has no matching score line (the process died
    mid-solve) is excluded.
    """
    starts: dict[str, dict[str, float]] = {}
    cache: dict[str, dict[str, float]] = {}
    for line in log_path.read_text().splitlines():
        m = _TRIAL_START.search(line)
        if m:
            starts[m.group(1)] = ast.literal_eval(m.group(2))
            continue
        m = _TRIAL_SCORE.search(line)
        if m and m.group(1) in starts:
            cache[_replay_key(starts.pop(m.group(1)))] = ast.literal_eval(m.group(2))
    return cache


def _build_replay_cache(
    log_path: Path, results_path: Path
) -> dict[str, dict[str, float]]:
    """Merge scored history rows from the results JSON with log-parsed trials."""
    cache: dict[str, dict[str, float]] = {}
    if results_path.exists():
        results = json.loads(results_path.read_text())
        for row in results.values():
            if not isinstance(row, dict):
                continue
            for rec in row.get("history") or []:
                if rec.get("scores"):
                    cache[_replay_key(rec["params"])] = rec["scores"]
    if log_path.exists():
        cache.update(_replay_from_log(log_path))
    return cache


REPLAY_CACHE: dict[str, dict[str, float]] = (
    json.loads(REPLAY_FILE.read_text()) if REPLAY_FILE.exists() else {}
)


# --- per-trial heartbeat: wrap the scorer so each solve announces itself -------------
_orig_score = ValidationTrackScorer.score


def _counting_score(
    self: ValidationTrackScorer,
    method_name: str,
    params: dict[str, float],
    split: object,
    seed: int,
    window: object,
) -> dict[str, float]:
    """Wrapped scorer.score that logs a heartbeat + the trial's scores (or its error)."""
    n = getattr(self, "_trial_n", 0) + 1
    self._trial_n = n  # type: ignore[attr-defined]
    if os.environ.get("SVERDRUP_MIOST_REPLAY", "1") != "0":
        cached = REPLAY_CACHE.get(_replay_key(params))
        if cached is not None:
            _log(f"  trial {n}: REPLAY {params} -> {cached}")
            return dict(cached)
    _log(f"  trial {n}: {params} -> solving {len(self.output_days)} day-maps ...")
    t = time.time()
    try:
        scores = _orig_score(self, method_name, params, split, seed, window)
    except Exception as exc:  # noqa: BLE001 - heartbeat only; re-raise for the loop
        _log(f"  trial {n}: {type(exc).__name__} after {int(time.time() - t)}s")
        raise
    _log(f"  trial {n}: {scores} ({int(time.time() - t)}s)")
    return scores


ValidationTrackScorer.score = _counting_score  # type: ignore[method-assign]


def _scope() -> Path:
    """Return the scope path (dev = 12-day fixture as-is; full = full-2017)."""
    if SCOPE_MODE == "dev":
        return DEV_FIX
    cfg = json.loads(DEV_FIX.read_text())
    days = list(range(365))
    cfg["validation_days"] = days
    cfg["acceptance_days"] = days
    cfg["time_min"] = "2017-01-01"
    cfg["time_max"] = "2018-01-01"
    cfg["acceptance_map_out"] = str(OUT_DIR / "stage_miost_acceptance.nc")
    fd = tempfile.NamedTemporaryFile("w", suffix="_miost_full_year.json", delete=False)
    json.dump(cfg, fd)
    fd.close()
    return Path(fd.name)


def _halo_obs(scope: Path) -> ObsWindow:
    """Six mapping missions subset to box + halo (production framing)."""
    from sverdrup.core.observations import DiagonalErrorModel

    cfg = json.loads(scope.read_text())
    provider, _, _ = baseline_config()
    obs = load_mapping_obs([Path(p) for p in cfg["mapping_obs_paths"]], provider)
    c = obs.coords()
    in_halo = (
        (c[:, 0] >= BOX_LON[0] - HALO_DEG)
        & (c[:, 0] <= BOX_LON[1] + HALO_DEG)
        & (c[:, 1] >= BOX_LAT[0] - HALO_DEG)
        & (c[:, 1] <= BOX_LAT[1] + HALO_DEG)
    )
    idx = np.nonzero(in_halo)[0]
    err = DiagonalErrorModel(np.asarray(obs.error_model.variance)[idx])  # type: ignore[attr-defined]
    return ObsWindow.from_arrays(
        c[idx, 0],
        c[idx, 1],
        c[idx, 2],
        obs.values()[idx],
        err,
        None if obs.mission is None else obs.mission[idx],
    )


def _n_obs_max_window(scope: Path) -> int:
    """Halo-inclusive max obs count over the 9 production windows (StoredG pricing)."""
    t = _halo_obs(scope).coords()[:, 2]
    counts = [
        int(((t >= w.start_day - L_T_MAX) & (t <= w.end_day + L_T_MAX)).sum())
        for w in WindowPlan().windows
    ]
    return max(counts)


def _score_map_on_validation(map_path: Path, cfg: dict[str, Any]) -> dict[str, float]:
    """Blocked-j3-track skill of one map file (mu + lambda_x when it resolves)."""
    import sverdrup.validation.their_eval as te
    from sverdrup.eval.skill_score import leaderboard_nrmse
    from sverdrup.eval.spectral import (
        ShortTrackError,
        UnresolvedScaleError,
        effective_resolution_lambda_x,
    )

    te._prepare_imports()
    from src.mod_inout import read_l3_dataset
    from src.mod_interp import interp_on_alongtrack

    box = dict(
        lon_min=295.0,
        lon_max=305.0,
        lat_min=33.0,
        lat_max=43.0,
        time_min=cfg["time_min"],
        time_max=cfg["time_max"],
    )
    ds_at = read_l3_dataset(str(cfg["val_track_path"]), **box)
    time_a, lat_a, lon_a, ssh_a, interp = interp_on_alongtrack(
        str(map_path), ds_at, is_circle=False, **box
    )
    out = {
        "mu_score": float(
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
        _log(f"winner-point lambda_x unresolved: {type(exc).__name__}")
    return out


def _winner_point_windowing_cost(
    scope: Path, winner_params: dict[str, float], winner_scores: dict[str, float]
) -> dict[str, Any]:
    """Task-11 close condition 2: re-measure the windowing cost at the WINNER's params.

    Validation-only, feasibility-conditional, no switching: one full-year
    single-window solve at the winner's params IF stored-G fits the budget at
    the winner's alpha; (Delta-mu, Delta-lambda_x) vs the winner's own
    validation scores. c2 is never touched here.
    """
    from sverdrup.application.splits import make_splits
    from sverdrup.application.tuning.stage_a import _subset
    from sverdrup.methods.miost_windows import WindowPlan as _WP
    from sverdrup.validation.input_adapter import load_mdt_grid
    from sverdrup.validation.output_adapter import write_map

    cfg = json.loads(scope.read_text())
    # TRAIN-ONLY obs (validation mission excluded) — the windowed side of the
    # comparison scored maps built without j3; assimilating j3 here and then
    # scoring ON j3 leaks absolutes and inflates the single-window mu
    # (protocol violation caught at the 2026-07-06 sign-off; the first run's
    # delta_mu=-0.0652 was cross-protocol).
    full = _halo_obs(scope)
    split = make_splits(
        full,
        by="mission",
        locked_missions=["c2"],
        validation_missions=[str(cfg["validation_mission"])],
    )
    obs = _subset(full, split.train_idx)
    n_single = len(obs)
    pred = StoredGFeasibility(n_obs_max=n_single, budget_bytes=8e9)
    reason = pred.explain(dict(winner_params))
    if reason is not None:
        return {
            "status": (
                "cost not measurable at winner's alpha "
                f"(single-window stored-G exceeds budget): {reason}"
            )
        }
    provider, grid, _ = baseline_config()
    mdt = load_mdt_grid([Path(p) for p in cfg["mdt_paths"]], grid)
    single = Miost(plan=_WP(starts=(-30.0,), w_days=425.0))
    days = list(cfg["validation_days"])
    maps = [
        np.asarray(
            single.solve(
                obs, grid, ConstantProvider(dict(winner_params)), float(d)
            ).mean
        )
        + mdt
        for d in days
    ]
    epoch = np.datetime64("2017-01-01")
    times = epoch + np.asarray(days, dtype="int64") * np.timedelta64(1, "D")
    lon2d, lat2d = np.meshgrid(grid.x, grid.y)
    dest = OUT_DIR / "winner_single_window.nc"
    write_map(times, np.unique(lat2d), np.unique(lon2d), np.stack(maps), dest)
    single_scores = _score_map_on_validation(dest, cfg)
    return {
        "caveat": "POINT-MEASURED at the winner's params; not a universal windowing cost",
        "windowed_validation": winner_scores,
        "single_window_validation": single_scores,
        "delta_mu": float(winner_scores.get("mu_score", float("nan")))
        - single_scores["mu_score"],
        "delta_lambda_x": float(winner_scores.get("lambda_x", float("nan")))
        - single_scores.get("lambda_x", float("nan")),
    }


def _history_rows(rep: StageAReport) -> list[dict[str, Any]]:
    """Serializable trial rows — infeasible reasons visible (Task-10 AC)."""
    if rep.history is None:
        return []
    return [
        {
            "params": r.trial.params,
            "feasible": r.feasible,
            "exclusion_reason": r.exclusion_reason,
            "scores": r.scores,
        }
        for r in rep.history.records
    ]


def _run(
    label: str,
    scope: Path,
    strategy: SearchStrategy | None,
    predicate: CompositeFeasibility,
    rounds: int,
) -> dict[str, Any]:
    """Run one strategy; return a serializable row (winner + acceptance, or the outcome)."""
    _log(f"=== {label}: start (n={N_TRIALS}, rounds={rounds}) ===")
    t = time.time()
    log_start = len(CONVERGENCE_LOG)
    try:
        rep = run_stage_miost(
            scope=scope,
            predicate=predicate,
            n_trials=N_TRIALS,
            seed=SEED,
            strategy=strategy,
            rounds=rounds,
        )
    except StageANoAdmissible as exc:
        # RECORDED, not raised: the d7376b8 pattern — a no-admissible smoke/sweep
        # is a diagnostic outcome, never a crash.
        _log(f"=== {label}: StageANoAdmissible — {exc} ===")
        return {
            "no_admissible": str(exc),
            "elapsed_s": int(time.time() - t),
        }
    except Exception as exc:  # noqa: BLE001 - persist the failure, don't lose the run
        _log(f"=== {label}: FAILED {type(exc).__name__}: {exc} ===")
        return {
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(),
            "elapsed_s": int(time.time() - t),
        }
    # Budgeted-solve honesty: the achieved residuals of every window solved at
    # the WINNER's params (its search trial + the acceptance map production).
    _, grid, _ = baseline_config()
    winner_hash = _params_key_hash(
        Miost()._params_key(ConstantProvider(rep.winner.trial.params), grid)
    )
    achieved = [
        {k: v for k, v in e.items() if k != "params_key_hash"}
        for e in CONVERGENCE_LOG[log_start:]
        if e["params_key_hash"] == winner_hash
    ]
    row = {
        "acceptance_mu_sigma_lambda_x": list(rep.acceptance),
        "winner_params": rep.winner.trial.params,
        "winner_scores": rep.winner.scores,
        "winner_achieved_residuals": achieved,
        "their_eval_calls_during_search": rep.their_eval_calls_during_search,
        "precheck_scores": rep.precheck_scores,
        "history": _history_rows(rep),
        "elapsed_s": int(time.time() - t),
    }
    _log(f"=== {label}: DONE acceptance={rep.acceptance} ({row['elapsed_s']}s) ===")
    return row


def main() -> None:
    """Run Sobol then BO over the scope, persisting each row immediately."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    scope = _scope()
    n_obs_max = _n_obs_max_window(scope)
    predicate = CompositeFeasibility(
        (
            StoredGFeasibility(n_obs_max=n_obs_max, budget_bytes=8e9),
            CoherenceFeasibility(),
        )
    )
    _log(
        f"scope={SCOPE_MODE} ({scope}); n_trials={N_TRIALS}; "
        f"n_obs_max_window={n_obs_max:,}; results -> {RESULTS}"
    )
    results: dict[str, Any] = {
        "scope": SCOPE_MODE,
        "n_trials": N_TRIALS,
        "seed": SEED,
        "n_obs_max_window": n_obs_max,
        "calibration": "N/A-for-POINT (capability-conditional; spec 7.4 Stage A)",
        "replay_cache": {
            "n_entries": len(REPLAY_CACHE),
            "source": str(REPLAY_FILE),
            "semantics": (
                "launch-state amendment (owner-approved 2026-07-05): relaunch "
                "after the trial-27 OOM replays already-measured trials from "
                "the dead run's log/results (deterministic seed re-proposes "
                "identical points). SVERDRUP_MIOST_REPLAY=0 disables."
            ),
        },
        "solver_budget": {
            "semantics": (
                "BUDGETED SOLVE (owner decision, Task-11 gate 2026-07-04, "
                "Stage-A-scoped): iterations capped; per-window ACHIEVED "
                "residuals recorded under winner_achieved_residuals. Stage B "
                "re-decides via the spec-6.5 under-convergence test — member "
                "generation must NOT inherit this cap silently."
            ),
            "pcg_rtol_target": PCG_RTOL,
            "pcg_maxiter_cap": PCG_MAXITER,
            "depth_insensitivity_evidence": {
                "worst_day_max_delta_m_at_cap_500": 2.0036,
                "worst_day_max_delta_m_converged_6000": 2.0220,
                "blend_median_max_delta_m_at_cap_500": 0.5740,
                "blend_median_max_delta_m_converged_6000": 0.5542,
                "source": "docs/validation/miost_equivalence_diagnostic.md",
            },
        },
    }
    RESULTS.write_text(json.dumps(results, indent=2))

    results["sobol"] = _run("Sobol", scope, None, predicate, rounds=1)
    RESULTS.write_text(json.dumps(results, indent=2))

    results["bo"] = _run(
        "BayesianOptimization",
        scope,
        BayesianOptimization(seed=SEED, n=N_TRIALS),
        predicate,
        rounds=BO_ROUNDS,
    )
    RESULTS.write_text(json.dumps(results, indent=2))

    # Headline winner for downstream tools (12-dir diagnostic): best admissible
    # acceptance-µ strategy, BO preferred on ties.
    best_label = None
    best_mu = -np.inf
    for label in ("bo", "sobol"):
        row = results[label]
        if "acceptance_mu_sigma_lambda_x" in row:
            mu = row["acceptance_mu_sigma_lambda_x"][0]
            if mu > best_mu:
                best_mu, best_label = mu, label
    if best_label is not None:
        row = results[best_label]
        results["winner"] = {
            "strategy": best_label,
            "params": row["winner_params"],
            "scores": row["winner_scores"],
            "acceptance_mu_sigma_lambda_x": row["acceptance_mu_sigma_lambda_x"],
            "mu_ge_0p85": bool(row["acceptance_mu_sigma_lambda_x"][0] >= 0.85),
        }
        RESULTS.write_text(json.dumps(results, indent=2))
        _log(f"winner: {results['winner']}")
        # Task-11 close condition 2: winner-point windowing-cost re-measurement
        # (validation-only, feasibility-conditional; c2 untouched here).
        _log("winner-point windowing-cost re-measurement ...")
        results["winner_point_windowing_cost"] = _winner_point_windowing_cost(
            scope, row["winner_params"], row["winner_scores"]
        )
        RESULTS.write_text(json.dumps(results, indent=2))
        _log(f"windowing cost: {results['winner_point_windowing_cost']}")
    else:
        _log("no admissible winner in either strategy — see per-strategy rows")
    _log("=== ALL DONE ===")


if __name__ == "__main__":
    if "--build-replay-cache" in sys.argv:
        built = _build_replay_cache(LOG_FILE, RESULTS)
        REPLAY_FILE.write_text(json.dumps(built, indent=2))
        print(f"replay cache: {len(built)} entries -> {REPLAY_FILE}")
    else:
        main()
