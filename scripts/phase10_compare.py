"""Phase-10 stage-2 PRIMARY comparison (plan Task 8; spec §5).

Reads the three recorded lane winners and writes the claim-bearing
verdict block at ``phase10.oi.lanes.verdict``:

- refusal clock FIRST (the sealed band protocol must predate every
  consulted winner record — enforced inside ``primary_verdict``);
- PRIMARY row = VL winner vs lane-0 winner, bands computed AT READ TIME
  on the actual pair from the persisted residual arrays (single seeded
  execution; values + write-times land here, in the consuming record);
- SECONDARY row V-vs-lane0 is COPIED from the stage-1 record (the
  single-execution rule forbids a second seeded computation on a pair
  already consulted; the copy carries a provenance pointer);
- the conditional L-only lane decision is recorded either way with the
  sealed budget number as the reason;
- the Task-8 branch (POSITIVE -> Tasks 10-15; NEGATIVE -> Task 9,
  10-15 superseded) is recorded verbatim.

The held-out challenge track is never read here: this script consumes
only recorded winner blocks and persisted validation-track residuals.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import numpy as np

from sverdrup.application.tuning.lane_compare import (
    load_protocol,
    primary_verdict,
)

_RESULTS = Path("data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _read_evidence() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(_RESULTS.read_text()))


def _write_evidence(key_path: str, value: object) -> None:
    """Atomic nested-key write (phase9_fit_run pattern; single writer)."""
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


def _loader(rec: dict[str, Any]) -> dict[str, np.ndarray]:
    """Load a winner record's persisted validation-track arrays.

    Args:
        rec: A lane winner record carrying ``residuals_npz``.

    Returns:
        The persisted track arrays keyed as saved.
    """
    with np.load(rec["residuals_npz"], allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


def main() -> None:
    """Assemble and write ``phase10.oi.lanes.verdict``."""
    ev = _read_evidence()
    oi_ev = ev.get("phase10", {}).get("oi", {})

    proto_ptr = oi_ev.get("band_protocol")
    budget = oi_ev.get("probe", {}).get("budget")
    if not proto_ptr or not budget:
        raise SystemExit("run phase10_prereg.py first (budget/protocol missing)")
    protocol = load_protocol(Path(proto_ptr["path"]), expected_sha=proto_ptr["sha256"])

    lanes = oi_ev.get("lanes", {})
    winners: dict[str, dict[str, Any]] = {}
    for lane in ("lane0", "V", "VL"):
        w = lanes.get(lane, {}).get("winner")
        if not w:
            raise SystemExit(f"lane {lane} has no recorded winner — run it first")
        winners[lane] = w

    # PRIMARY (claim-bearing): VL vs lane-0. Refusal clock runs FIRST
    # inside primary_verdict; this is the pair's single seeded execution.
    primary = primary_verdict(winners["VL"], winners["lane0"], protocol, _loader)
    primary["role"] = "PRIMARY (claim-bearing, spec §5)"

    # SECONDARY: copy of the stage-1 row (single-execution rule).
    secondary = lanes.get("stage1_secondary_v_vs_lane0")
    if not secondary:
        raise SystemExit("stage-1 secondary row missing — stage 1 incomplete")
    secondary = dict(secondary)
    secondary["provenance"] = (
        "copied verbatim from phase10.oi.lanes.stage1_secondary_v_vs_lane0 "
        "(single-execution rule: the pair was consulted at stage-1 close; "
        "no second seeded computation)"
    )

    # Conditional L-only lane: sealed budget arithmetic decides.
    n_four = int(budget["n_sobol_per_lane_four_lanes"])
    floor = int(budget["minimum_floor"])
    l_only = {
        "run": n_four >= floor,
        "reason": (
            f"sealed budget: n_sobol_per_lane at four lanes = {n_four} "
            f"{'>=' if n_four >= floor else '<'} minimum_floor {floor} "
            f"(probe t_trial_s {budget['t_trial_s']:.1f}, wall "
            f"{budget['wall_budget_h']} h)"
        ),
    }

    branch = (
        "POSITIVE: Tasks 10-15 proceed"
        if primary["positive"]
        else "NEGATIVE: Task 9 executes; Tasks 10-15 close as superseded "
        "(Phase-8 Task-13 branch-semantics precedent)"
    )

    verdict = {
        "created_utc": _now(),
        "rule": "PRIMARY = VL winner vs lane-0 winner, lexicographic "
        "mu->lambda_x (spec §5); wording pin: non-positive reads "
        "'improvements within band', never 'worse'",
        "primary": primary,
        "secondary_v_vs_lane0": secondary,
        "l_only": l_only,
        "branch_recorded": branch,
        "protocol_sha": primary["protocol_sha"],
    }
    _write_evidence("phase10.oi.lanes.verdict", verdict)
    print(
        f"[verdict] PRIMARY VL-vs-lane0: {primary['branch']} "
        f"positive={primary['positive']} dmu={primary['delta_mu']:+.5f} "
        f"band={primary['band_mu']:.5f} dlx={primary['delta_lambda_x']:+.2f} "
        f"band_lx={primary['band_lambda_x']:.2f} "
        f"lambda_informative={primary['lambda_informative']}",
        flush=True,
    )
    print(f"[verdict] {branch}", flush=True)
    print(f"[verdict] L-only: run={l_only['run']} ({l_only['reason']})", flush=True)


if __name__ == "__main__":
    main()
