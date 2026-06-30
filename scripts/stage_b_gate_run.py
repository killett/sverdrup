"""Durable Stage-B gate runner: GMRF tuned via Sobol AND BayesianOptimization, full-2017.

Why a runner (not the pytest gate): the full-year GMRF sweep is a ~2-day wall-clock job
with no per-trial checkpoint, so we persist each strategy's acceptance row to a results
JSON the INSTANT it completes (a mid-run death keeps the finished strategy) and heartbeat
once per trial. The committed 12-day dev fixture is left untouched — the full-year scope is
derived in-memory here.

Run (detached):
    nohup pixi run python scripts/stage_b_gate_run.py \
        > data/2021a_ssh_mapping_ose/ours/stage_b_gate.log 2>&1 &

Results: data/2021a_ssh_mapping_ose/ours/stage_b_gate_results.json
"""

from __future__ import annotations

import json
import tempfile
import time
import traceback
from pathlib import Path
from typing import Any

from sverdrup.application.tuning.bayesopt import BayesianOptimization
from sverdrup.application.tuning.scorer import ValidationTrackScorer
from sverdrup.application.tuning.stage_b import run_stage_b
from sverdrup.application.tuning.strategy import SearchStrategy

DEV_FIX = Path("tests/validation/fixtures/stage_a_scope.json")
OUT_DIR = Path("data/2021a_ssh_mapping_ose/ours")
RESULTS = OUT_DIR / "stage_b_gate_results.json"
N_TRIALS = 8
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
    _log(f"  trial {n}: solving {len(self.output_days)} day-maps ...")
    t = time.time()
    try:
        scores = _orig_score(self, method_name, params, split, seed, window)
    except Exception as exc:  # noqa: BLE001 - heartbeat only; re-raise for the loop
        _log(f"  trial {n}: {type(exc).__name__} after {int(time.time() - t)}s")
        raise
    _log(f"  trial {n}: {scores} ({int(time.time() - t)}s)")
    return scores


ValidationTrackScorer.score = _counting_score  # type: ignore[method-assign]


def _full_year_scope() -> Path:
    """Derive a full-2017 scope from the 12-day dev fixture; write to a temp file."""
    cfg = json.loads(DEV_FIX.read_text())
    days = list(range(365))  # 2017-01-01 (day 0) .. 2017-12-31 (day 364)
    cfg["validation_days"] = days
    cfg["acceptance_days"] = days
    cfg["time_min"] = "2017-01-01"
    cfg["time_max"] = "2018-01-01"
    cfg["acceptance_map_out"] = str(OUT_DIR / "stage_b_gate_acceptance.nc")
    fd = tempfile.NamedTemporaryFile(
        "w", suffix="_stage_b_full_year.json", delete=False
    )
    json.dump(cfg, fd)
    fd.close()
    return Path(fd.name)


def _run(label: str, scope: Path, strategy: SearchStrategy | None) -> dict[str, Any]:
    """Run one strategy; return a serializable row (acceptance + winner, or the error)."""
    _log(f"=== {label}: start ===")
    t = time.time()
    try:
        rep = run_stage_b(scope=scope, n_trials=N_TRIALS, seed=SEED, strategy=strategy)
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
        "elapsed_s": int(time.time() - t),
    }
    _log(f"=== {label}: DONE acceptance={rep.acceptance} ({row['elapsed_s']}s) ===")
    return row


def main() -> None:
    """Run Sobol then BO over the full-year scope, persisting each row immediately."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    scope = _full_year_scope()
    _log(f"full-year scope -> {scope}; results -> {RESULTS}")
    results: dict[str, Any] = {"n_trials": N_TRIALS, "seed": SEED}

    results["sobol"] = _run("Sobol", scope, None)
    RESULTS.write_text(json.dumps(results, indent=2))  # persist after Sobol

    results["bo"] = _run(
        "BayesianOptimization", scope, BayesianOptimization(seed=SEED, n=N_TRIALS)
    )
    RESULTS.write_text(json.dumps(results, indent=2))  # persist after BO

    # Gate verdict (only when both produced a finite acceptance).
    sob, bo = results["sobol"], results["bo"]
    if "acceptance_mu_sigma_lambda_x" in sob and "acceptance_mu_sigma_lambda_x" in bo:
        s_lx = sob["acceptance_mu_sigma_lambda_x"][2]
        b_lx = bo["acceptance_mu_sigma_lambda_x"][2]
        results["gate"] = {
            "bo_lambda_x": b_lx,
            "sobol_lambda_x": s_lx,
            "bo_finite_positive": bool(
                bo["acceptance_mu_sigma_lambda_x"][0] > 0 and b_lx > 0
            ),
            "bo_within_1p25x_sobol": bool(b_lx <= s_lx * 1.25),
        }
        RESULTS.write_text(json.dumps(results, indent=2))
        _log(f"gate verdict: {results['gate']}")
    _log("=== ALL DONE ===")


if __name__ == "__main__":
    main()
