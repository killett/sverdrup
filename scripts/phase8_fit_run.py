"""Phase-8 fit run: thin shim over the generalized calibration harness.

SHIM (Phase 9, Task 4): The fit-pipeline logic has been extracted to
``src/sverdrup/application/calibration/harness.py`` and parameterised by
:class:`~sverdrup.application.calibration.harness.ProductDescriptor`.
This file is now a thin shim that delegates to the harness with the FROZEN
MIOST descriptor, preserving CLI provenance-of-record intact.

Shim vs retire decision: the shim is preferred over retiring because:
  1. The Phase-8 gate test (``tests/test_phase8_gate_run.py``) tests
     ``phase8_gate_run.py``, not this script — so neither approach breaks it.
  2. Keeping the script alive with the same CLI interface preserves the
     shell provenance trail and protects against accidental re-invocation of
     the old pipeline on future sessions.
  3. The shim writes to Phase-8 paths (``phase8_field.json``,
     ``phase8.fit_run`` key in the gate JSON), not Phase-9 paths, so
     any re-run is isolated to the Phase-8 evidence block.

Provenance note: The FROZEN Phase-8 tuple ``("miost", "phase8", "s-folds")``
in MIOST_DESCRIPTOR reproduces the Phase-8 seed EXACTLY — the harness's
``draw_s_layout`` calls ``derive_seed(*fold_seed_tuple, salt)`` with the same
3-tuple that ``folds.s_fold_layout`` uses via ``S_FOLD_SEED_ARGS``.

Original pipeline (spec §7):
    load_track() -> measure_rho() -> run_family(t_folds) -> run_family(s_folds)
    -> select() -> refit_or_negative() -> evidence() -> write + STOP banner

Scope discipline (unchanged from original):
    SVERDRUP_PHASE8_SCOPE=dev  -> 12-day dev fixture window; writes ONLY
                                  phase8_dev_smoke.json (NEVER the gate JSON).
    (default / full)           -> full j3 year; writes the gate JSON phase8 block.

c2 is UNTOUCHED: the harness never imports their_eval or c2 paths.

Usage:
    SVERDRUP_PHASE8_SCOPE=dev pixi run python scripts/phase8_fit_run.py
    pixi run python scripts/phase8_fit_run.py            # full (detached)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import numpy as np

# Re-export the path constants so that monkeypatching in tests still works
# and the provenance trail is intact.
ROOT = Path("data/2021a_ssh_mapping_ose/ours")
RESULTS = ROOT / "stage_miost_gate_results.json"
MEAN_NC = ROOT / "stage_b_mean_maps.nc"
VAR_NC = ROOT / "stage_b_var_maps.nc"
JET_MASK = ROOT / "phase8_jet_core_mask.json"
FIELD_OUT = ROOT / "phase8_field.json"
SMOKE_OUT = ROOT / "phase8_dev_smoke.json"
SCOPE_FIX = Path("tests/validation/fixtures/stage_a_scope.json")

SCOPE_MODE = os.environ.get("SVERDRUP_PHASE8_SCOPE", "full")  # "dev" | "full"
if SCOPE_MODE not in {"dev", "full"}:
    raise SystemExit(
        f"SVERDRUP_PHASE8_SCOPE must be 'dev' or 'full', got {SCOPE_MODE!r}"
    )

# Import the harness — all pipeline logic now lives here.
from sverdrup.application.calibration.harness import (  # noqa: E402
    MIOST_DESCRIPTOR,
    Track,
    build_evidence,
)
from sverdrup.application.calibration.harness import (  # noqa: E402
    atomic_write_json as _atomic_write_json,
)
from sverdrup.application.calibration.harness import (  # noqa: E402
    load_track as _load_track,
)

# Keep backward-compatible module-level name.
EPOCH = np.datetime64("2017-01-01")


def _proxy() -> np.ndarray:
    """Return the (5,5) signal-variance proxy from the shipped MIOST mean maps."""
    import xarray as xr

    from sverdrup.application.calibration import regions as R

    with xr.open_dataset(MEAN_NC) as ds:
        return R.proxy_cells(ds)


def load_track() -> Track:
    """Load the j3 track using the MIOST descriptor and current SCOPE_MODE."""
    return _load_track(MIOST_DESCRIPTOR, SCOPE_MODE)


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
    b = evidence["bars"]
    print(
        f"bar1 agg={b['bar1_aggregate_coverage']:.4f} in_band={b['bar1_aggregate_in_band']}"
    )
    print(f"bar2 every_region_in_band={b['bar2_every_region_in_band']}")
    print(
        f"bar3 worst={b['bar3_worst_region']} deficit={b['bar3_worst_deficit']:.4f} "
        f"improved={b['bar3_strictly_improved_vs_scalar_record']}"
    )
    print(
        f"salt={evidence['folds']['s_salt_final']} "
        f"tail_flag={evidence['tail_diagnostic']['flagged']}"
    )
    print("=" * 72)


def main() -> None:
    """Run the fit pipeline via the harness shim, write Phase-8 artifacts."""
    trk = load_track()
    proxy = _proxy()
    evidence = build_evidence(MIOST_DESCRIPTOR, trk, proxy, SCOPE_MODE)

    negative = evidence["selection"].get("negative_result", False)

    if SCOPE_MODE == "dev":
        # Dev smoke: structure-completeness only; NEVER the gate JSON, NEVER field.
        _atomic_write_json(SMOKE_OUT, evidence)
        print(
            f"[dev smoke] scope=dev n={trk.n} points; "
            f"negative_result={negative}; wrote {SMOKE_OUT}"
        )
        _print_banner(evidence, negative)
        return

    # Full scope: write the gate JSON phase8 block (preserve existing content).
    results = json.loads(RESULTS.read_text())
    results.setdefault("phase8", {})  # preserves covariate_alignment
    results["phase8"]["fit_run"] = evidence
    _atomic_write_json(RESULTS, results)

    if not negative:
        cal_json = evidence["winner_field"]["to_json"]
        _atomic_write_json(
            FIELD_OUT,
            {
                "calibration": cal_json,
                "cal_key": evidence["winner_field"]["cal_key"],
            },
        )
        print(f"[full] wrote field artifact {FIELD_OUT}")
    else:
        print("[full] NEGATIVE RESULT — no field artifact written.")
    print(f"[full] wrote phase8.fit_run into {RESULTS}")
    _print_banner(evidence, negative)


if __name__ == "__main__":
    main()
