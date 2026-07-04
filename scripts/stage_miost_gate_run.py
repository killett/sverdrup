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

import json
import os
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
from sverdrup.methods.miost_basis import BOX_LAT, BOX_LON, HALO_DEG
from sverdrup.methods.miost_windows import L_T_MAX, WindowPlan
from sverdrup.validation.input_adapter import load_mapping_obs
from sverdrup.validation.params import baseline_config

DEV_FIX = Path("tests/validation/fixtures/stage_a_scope.json")
OUT_DIR = Path("data/2021a_ssh_mapping_ose/ours")
RESULTS = OUT_DIR / "stage_miost_gate_results.json"
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


def _n_obs_max_window(scope: Path) -> int:
    """Halo-inclusive max obs count over the 9 production windows (StoredG pricing)."""
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
    t = c[in_halo, 2]
    counts = [
        int(((t >= w.start_day - L_T_MAX) & (t <= w.end_day + L_T_MAX)).sum())
        for w in WindowPlan().windows
    ]
    return max(counts)


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
    row = {
        "acceptance_mu_sigma_lambda_x": list(rep.acceptance),
        "winner_params": rep.winner.trial.params,
        "winner_scores": rep.winner.scores,
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
    else:
        _log("no admissible winner in either strategy — see per-strategy rows")
    _log("=== ALL DONE ===")


if __name__ == "__main__":
    main()
