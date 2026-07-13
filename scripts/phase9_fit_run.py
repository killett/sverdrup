"""Phase-9 fit run: thin CLI over the generalized calibration harness.

Dispatches to :func:`sverdrup.application.calibration.harness.run_harness`
with the requested descriptor and scope.  All pipeline logic lives in the
harness module; this script is pure CLI glue.

Scope discipline (mirrors phase8_fit_run.py):
    SVERDRUP_PHASE9_SCOPE=dev  -> 12-day dev fixture window; writes ONLY
                                  phase9_dev_smoke.json (NEVER gate evidence).
    (default / full)           -> full j3 year; writes per-product gate evidence
                                  into stage_miost_gate_results.json under the
                                  descriptor's evidence_key, and writes the
                                  field artifact.

c2 is UNTOUCHED: the harness never imports their_eval or c2 paths.

Usage:
    SVERDRUP_PHASE9_SCOPE=dev pixi run python scripts/phase9_fit_run.py
    pixi run python scripts/phase9_fit_run.py            # full (detached)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from sverdrup.application.calibration.harness import (
    MIOST_DESCRIPTOR,
    ProductDescriptor,
    atomic_write_json,
    run_harness,
)

# ---------------------------------------------------------------------------
# Paths / scope
# ---------------------------------------------------------------------------

_ROOT = Path("data/2021a_ssh_mapping_ose/ours")
_RESULTS = _ROOT / "stage_miost_gate_results.json"
_SMOKE_OUT = _ROOT / "phase9_dev_smoke.json"

_SCOPE_MODE = os.environ.get("SVERDRUP_PHASE9_SCOPE", "full")
if _SCOPE_MODE not in {"dev", "full"}:
    raise SystemExit(
        f"SVERDRUP_PHASE9_SCOPE must be 'dev' or 'full', got {_SCOPE_MODE!r}"
    )

# Default descriptor — MIOST (the Phase-8 calibration product).
_DESCRIPTOR: ProductDescriptor = MIOST_DESCRIPTOR


def _print_banner(evidence: dict[str, Any], negative: bool) -> None:
    """Print the STOP banner + selection/bars summary."""
    sel = evidence["selection"]
    print("=" * 72)
    if negative:
        print("STOP — NEGATIVE RESULT (spec §3 path)")
        print(sel.get("stop_banner", ""))
        print("=" * 72)
        return
    print("STOP — owner reviews j3-side evidence (spec §7 step 4)")
    print(f"winner: {sel['winner']}")
    print(f"lane-0 S/T stat: {sel['lane0_s_stat']:.4f} / {sel['lane0_t_stat']:.4f}")
    for nm, e in sel["eligibility"].items():
        print(
            f"  {nm:10s} S={e['s_stat']:.4f} T={e['t_stat']:.4f} "
            f"eligible={e['eligible']}"
        )
    if "bars" in evidence:
        b = evidence["bars"]
        print(
            f"bar1 agg={b['bar1_aggregate_coverage']:.4f} "
            f"in_band={b['bar1_aggregate_in_band']}"
        )
        print(f"bar2 every_region_in_band={b['bar2_every_region_in_band']}")
        print(
            f"bar3 worst={b['bar3_worst_region']} "
            f"deficit={b['bar3_worst_deficit']:.4f} "
            f"improved={b['bar3_strictly_improved_vs_scalar_record']}"
        )
        print(
            f"salt={evidence['folds']['s_salt_final']} "
            f"tail_flag={evidence['tail_diagnostic']['flagged']}"
        )
    print("=" * 72)


def main() -> None:
    """Run the Phase-9 fit pipeline, write scope-appropriate artifacts."""
    desc = _DESCRIPTOR
    evidence = run_harness(desc, _SCOPE_MODE)
    negative = evidence["selection"].get("negative_result", False)

    if _SCOPE_MODE == "dev":
        # Dev smoke: structure-completeness only; NEVER the gate JSON, NEVER field.
        atomic_write_json(_SMOKE_OUT, evidence)
        print(
            f"[dev smoke] scope=dev product={desc.product_id} "
            f"n={evidence['n_track_points']} points; "
            f"negative_result={negative}; wrote {_SMOKE_OUT}"
        )
        _print_banner(evidence, negative)
        return

    # Full scope: write the gate JSON under the descriptor's evidence_key.
    # Resolve nested key path, e.g. "phase9.miost.fit_run" -> results["phase9"]["miost"]["fit_run"].
    results = json.loads(_RESULTS.read_text())
    keys = desc.evidence_key.split(".")
    node: dict[str, Any] = results
    for k in keys[:-1]:
        node = node.setdefault(k, {})
    node[keys[-1]] = evidence
    atomic_write_json(_RESULTS, results)

    if not negative:
        cal_json = evidence["winner_field"]["to_json"]
        atomic_write_json(
            desc.field_artifact,
            {
                "calibration": cal_json,
                "cal_key": evidence["winner_field"]["cal_key"],
            },
        )
        print(f"[full] wrote field artifact {desc.field_artifact}")
    else:
        print("[full] NEGATIVE RESULT — no field artifact written.")
    print(f"[full] wrote {desc.evidence_key} into {_RESULTS}")
    _print_banner(evidence, negative)


if __name__ == "__main__":
    main()
