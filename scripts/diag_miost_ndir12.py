"""12-direction sensitivity diagnostic (D2): winner re-score with n_dir=12.

Validation-track ONLY (never c2). Conditions verbatim from D2: run only if
StoredGFeasibility(n_dir=12) admits the winner's alpha at the halo-inclusive
obs count — otherwise skip WITH the predicate's reason recorded.

Usage:
    pixi run python scripts/diag_miost_ndir12.py [RESULTS.json]
    (default RESULTS = data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json)

Output: docs/validation/miost_ndir12_sensitivity.md
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

from sverdrup.application.splits import make_splits
from sverdrup.application.tuning.feasibility import StoredGFeasibility
from sverdrup.application.tuning.stage_a import _build_scorer, _subset, _Win
from sverdrup.methods.miost import Miost
from sverdrup.methods.registry import METHODS
from sverdrup.validation.input_adapter import load_mapping_obs, load_mdt_grid
from sverdrup.validation.params import baseline_config

RESULTS_DEFAULT = Path("data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json")
SCOPE = Path("tests/validation/fixtures/stage_a_scope.json")
DOC = Path("docs/validation/miost_ndir12_sensitivity.md")


def _full_year_cfg() -> dict[str, Any]:
    """Stage-A scope paths with the full-2017 day range (mirrors the gate runner)."""
    cfg: dict[str, Any] = json.loads(SCOPE.read_text())
    cfg["validation_days"] = list(range(365))
    cfg["time_min"] = "2017-01-01"
    cfg["time_max"] = "2018-01-01"
    return cfg


def main() -> None:
    """Re-score the winner at n_dir=12 (feasibility-gated); write the report."""
    results_path = Path(sys.argv[1]) if len(sys.argv) > 1 else RESULTS_DEFAULT
    results = json.loads(results_path.read_text())
    winner = results["winner"]["params"]
    winner_scores = results["winner"]["scores"]
    n_obs_max = int(results["n_obs_max_window"])

    pred = StoredGFeasibility(n_obs_max=n_obs_max, n_dir=12)
    reason = pred.explain(winner)
    lines = [
        "# MIOST 12-direction sensitivity (D2 diagnostic; validation track only)",
        "",
        f"- Winner params: `{winner}`; halo-inclusive max-window obs: {n_obs_max:,}.",
        "",
    ]
    if reason is not None:
        lines += [
            "## SKIPPED — StoredGFeasibility(n_dir=12) excludes the winner's alpha",
            "",
            f"Reason: {reason}",
            "",
        ]
    else:
        cfg = _full_year_cfg()
        provider, grid, half = baseline_config()
        obs = load_mapping_obs([Path(p) for p in cfg["mapping_obs_paths"]], provider)
        mdt = (
            load_mdt_grid([Path(p) for p in cfg["mdt_paths"]], grid)
            if cfg.get("mdt_paths")
            else None
        )
        split = make_splits(
            obs,
            by="mission",
            locked_missions=["c2"],
            validation_missions=[str(cfg["validation_mission"])],
        )
        scorer = _build_scorer(cfg, _subset(obs, split.train_idx), grid, half, mdt)
        METHODS["miost"] = lambda: Miost(n_dir=12)  # type: ignore[assignment]
        try:
            t0 = time.time()
            scores12 = scorer.score(
                "miost", dict(winner), split, 1, _Win("gulfstream-ndir12")
            )
            elapsed = int(time.time() - t0)
        finally:
            METHODS["miost"] = Miost
        lines += [
            "## Side-by-side (validation track)",
            "",
            "| metric | winner (8-dir) | 12-dir |",
            "|---|---|---|",
            f"| mu_score | {winner_scores.get('mu_score', float('nan')):.4f} | "
            f"{scores12.get('mu_score', float('nan')):.4f} |",
            f"| lambda_x [km] | {winner_scores.get('lambda_x', float('nan')):.1f} | "
            f"{scores12.get('lambda_x', float('nan')):.1f} |",
            "",
            f"(12-dir re-score wall time: {elapsed}s; n_dir recorded in params_key.)",
            "",
        ]
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
