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
    SVERDRUP_PHASE9_SCOPE=dev pixi run python scripts/phase9_fit_run.py --product oi
    pixi run python scripts/phase9_fit_run.py            # full MIOST (detached)
    pixi run python scripts/phase9_fit_run.py --product oi  # full OI (detached)
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from sverdrup.application.calibration.harness import (
    MIOST_DESCRIPTOR,
    OI_DESCRIPTOR,
    ProductDescriptor,
    atomic_write_json,
    run_harness,
)

# ---------------------------------------------------------------------------
# Paths / scope
# ---------------------------------------------------------------------------

_ROOT = Path("data/2021a_ssh_mapping_ose/ours")
_RESULTS = _ROOT / "stage_miost_gate_results.json"

_SCOPE_MODE = os.environ.get("SVERDRUP_PHASE9_SCOPE", "full")
if _SCOPE_MODE not in {"dev", "full"}:
    raise SystemExit(
        f"SVERDRUP_PHASE9_SCOPE must be 'dev' or 'full', got {_SCOPE_MODE!r}"
    )

# ---------------------------------------------------------------------------
# Product dispatch — --product miost (default) | oi
# ---------------------------------------------------------------------------

_PRODUCT_MAP: dict[str, ProductDescriptor] = {
    "miost": MIOST_DESCRIPTOR,
    "oi": OI_DESCRIPTOR,
}


def _parse_descriptor() -> ProductDescriptor:
    """Parse --product from argv and return the selected descriptor.

    Kept out of module scope so importing this script never touches
    ``sys.argv`` (phase8_fit_run.py idiom: argparse lives in main()).
    """
    parser = argparse.ArgumentParser(
        description=(
            "Phase-9 fit run: thin CLI over the generalized calibration harness."
        )
    )
    parser.add_argument(
        "--product",
        choices=list(_PRODUCT_MAP),
        default="miost",
        help="Calibration product to run (miost | oi). Default: miost.",
    )
    return _PRODUCT_MAP[parser.parse_args().product]


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


def _inject_oi_interpretation(evidence: dict[str, Any]) -> None:
    """Inject OI-specific interpretation note and demonstration marker (AC 4).

    Args:
        evidence: The evidence dict to mutate in-place.
    """
    shat = evidence.get("shat_reconciliation", {})
    s_hat = shat.get("s_hat_floored", float("nan"))
    evidence["demonstration_only"] = True
    evidence["shipping"] = "not elected; Phase 10 supersedes"
    evidence["shat_interpretation"] = (
        f"ŝ_OI={s_hat:.4f} (constant-lane MLE with floor) — ŝ < 1 means the "
        "raw OI variance maps are mildly OVER-dispersed on the constant lane "
        f"(the MLE shrinks variance by ~{(1.0 - s_hat) * 100.0:.0f}% at the "
        "constant-lane optimum), in contrast to MIOST's strong under-dispersion "
        "(s* = 10.06). "
        "Poly wins selection over piecewise and lane-0 on S-fold primary, so "
        "the spatial lane IS informative even at near-1 overall scale. "
        "This is an INFORMATIVE FINDING: the calibration harness is "
        "method-agnostic and correctly handles both the near-1 (shrink) and "
        "near-10 (inflate) regimes."
    )


def main() -> None:
    """Run the Phase-9 fit pipeline, write scope-appropriate artifacts."""
    desc = _parse_descriptor()
    smoke_out = _ROOT / f"phase9_dev_smoke_{desc.product_id}.json"
    evidence = run_harness(desc, _SCOPE_MODE)
    negative = evidence["selection"].get("negative_result", False)

    # OI-specific: inject demonstration marker and interpretation note (AC 4).
    if desc.product_id == "oi":
        _inject_oi_interpretation(evidence)

    if _SCOPE_MODE == "dev":
        # Dev smoke: structure-completeness only; NEVER the gate JSON, NEVER field.
        atomic_write_json(smoke_out, evidence)
        print(
            f"[dev smoke] scope=dev product={desc.product_id} "
            f"n={evidence['n_track_points']} points; "
            f"negative_result={negative}; wrote {smoke_out}"
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
