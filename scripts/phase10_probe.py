"""Phase-10 Task-0/Task-5 runtime probe: one full-year OI re-solve, measured.

Measures wall seconds + peak RSS for a full-year (365-day) train-only OI
mean+var re-solve and writes the measurement to the gate-evidence JSON under
``phase10.oi.probe.<config>``.  The probe maps are KEPT — they are the band
machinery's probe-pair reference sides (spec §5, demoted shakedown pair):

- ``--config signed``   -> the phase-9 signed baseline config regenerated ->
  ``phase10_probe_signed_{mean,var}.nc`` (probe-pair side A).
- ``--config paciorek`` -> the pinned Paciorek probe config (Task 5; raises
  until the Task-4 kernel lands) -> probe-pair side B.

Budget arithmetic (spec §4) lives here as the pure function
:func:`trials_per_lane`, unit-tested in ``tests/test_phase10_probe.py``.

Scope discipline (mirrors generate_oi_maps.py):
    SVERDRUP_PHASE10_SCOPE=dev  -> 12-day smoke; separate ``*_dev.nc`` outputs;
                                   NEVER writes gate evidence.
    (default / full)            -> 365 days; writes ``phase10.oi.probe.<config>``.

c2 is NEVER touched here: obs loading uses the mapping-mission file list only
(no c2 path), and the standing split locks c2 out of the train subset.

Usage:
    SVERDRUP_PHASE10_SCOPE=dev pixi run python scripts/phase10_probe.py --config signed
    nohup pixi run python scripts/phase10_probe.py --config signed > probe.log 2>&1 &
"""

from __future__ import annotations

import argparse
import json
import os
import resource
import time
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths / scope
# ---------------------------------------------------------------------------

_DATA_ROOT = Path("data/2021a_ssh_mapping_ose")
_OBS_DIR = _DATA_ROOT / "dc_obs"
_OUT_ROOT = _DATA_ROOT / "ours"
_RESULTS = _OUT_ROOT / "stage_miost_gate_results.json"

_MAPPING_OBS_PATHS: list[Path] = [
    _OBS_DIR / "dt_gulfstream_alg_phy_l3_20161201-20180131_285-315_23-53.nc",
    _OBS_DIR / "dt_gulfstream_h2g_phy_l3_20161201-20180131_285-315_23-53.nc",
    _OBS_DIR / "dt_gulfstream_j2g_phy_l3_20161201-20180131_285-315_23-53.nc",
    _OBS_DIR / "dt_gulfstream_j2n_phy_l3_20161201-20180131_285-315_23-53.nc",
    _OBS_DIR / "dt_gulfstream_j3_phy_l3_20161201-20180131_285-315_23-53.nc",
    _OBS_DIR / "dt_gulfstream_s3a_phy_l3_20161201-20180131_285-315_23-53.nc",
]
# c2 must NEVER appear above — the probe (like every phase-10 task before
# Task 13) has no c2 capability; the input_adapter guard is the safety net.

_SCOPE = os.environ.get("SVERDRUP_PHASE10_SCOPE", "full")
if _SCOPE not in {"dev", "full"}:
    raise SystemExit(f"SVERDRUP_PHASE10_SCOPE must be 'dev' or 'full', got {_SCOPE!r}")

# Dev smoke: days 60-71 (the stage_a fixture window); full year: 0-364.
_DEV_DAYS: list[float] = [float(d) for d in range(60, 72)]
_FULL_DAYS: list[float] = [float(d) for d in range(0, 365)]


def trials_per_lane(t_trial_s: float, wall_budget_h: float, n_lanes: int) -> int:
    """Trials per lane from measured trial cost (spec §4 budget arithmetic).

    Args:
        t_trial_s: Measured wall seconds per trial (one full-scope score).
        wall_budget_h: Owner-supplied wall budget in hours.
        n_lanes: Number of tuning lanes sharing the budget.

    Returns:
        ``floor(wall_budget_h*3600 / (t_trial_s * n_lanes))``, never negative.

    Raises:
        ValueError: If ``t_trial_s`` is not positive (bad measurement).
    """
    if t_trial_s <= 0:
        raise ValueError("t_trial_s must be positive")
    return max(0, int(wall_budget_h * 3600.0 // (t_trial_s * n_lanes)))


def _peak_rss_mib() -> float:
    """Return this process's peak RSS in MiB.

    Returns:
        Peak resident set size in MiB (Linux ``ru_maxrss`` is KiB).
    """
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def _host_fingerprint() -> dict[str, Any]:
    """Return the probe host's capacity fingerprint (cpu count, MemAvailable).

    Returns:
        Dict with ``cpu_count`` and ``mem_available_gib`` (from /proc/meminfo;
        NaN if unreadable — non-Linux fallback, never fatal).
    """
    mem_gib = float("nan")
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                mem_gib = float(line.split()[1]) / (1024.0**2)  # KiB -> GiB
                break
    except OSError:
        pass
    return {"cpu_count": os.cpu_count(), "mem_available_gib": mem_gib}


def _write_evidence(key_path: str, block: dict[str, Any]) -> None:
    """Atomically merge ``block`` into the gate JSON under dotted ``key_path``.

    The nested-key writer pattern from phase9_fit_run.py: resolve
    ``a.b.c`` -> results["a"]["b"]["c"] = block, then atomic write.
    Read-modify-write is NOT locked — probe runs are sequential by protocol
    (signed at Task 0, paciorek at Task 5; never parallel), single writer.

    Args:
        key_path: Dotted evidence key, e.g. ``phase10.oi.probe.signed``.
        block: The evidence block to store at that key.
    """
    from sverdrup.application.calibration.harness import (  # noqa: PLC0415
        atomic_write_json,
    )

    results = json.loads(_RESULTS.read_text())
    keys = key_path.split(".")
    node: dict[str, Any] = results
    for k in keys[:-1]:
        node = node.setdefault(k, {})
    node[keys[-1]] = block
    atomic_write_json(_RESULTS, results)


def _run_signed_probe(output_days: list[float], suffix: str) -> dict[str, Any]:
    """Run the signed-config mean+var re-solve and return the measurement block.

    Args:
        output_days: Output day numbers (dev: 12 days; full: 365).
        suffix: Output filename suffix ("" for full scope, "_dev" for dev).

    Returns:
        The ``phase10.oi.probe.signed`` evidence block (wall, RSS, framing,
        host fingerprint, map paths).
    """
    # Local imports keep module import light for the unit tests (pure function
    # only) — the heavy validation stack loads only when a probe actually runs.
    from sverdrup.application.splits import make_splits  # noqa: PLC0415
    from sverdrup.validation.input_adapter import (  # noqa: PLC0415
        load_mapping_obs,
        load_mdt_grid,
    )
    from sverdrup.validation.params import (  # noqa: PLC0415
        baseline_config,
        baseline_kernel,
    )
    from sverdrup.validation.run import _subset, run_mean_var_maps  # noqa: PLC0415

    provider, grid, half = baseline_config()
    kernel = baseline_kernel()

    print("  loading mapping obs (train-only split; c2 locked out) ...", flush=True)
    obs_all = load_mapping_obs(_MAPPING_OBS_PATHS, provider)
    split = make_splits(
        obs_all, by="mission", locked_missions=["c2"], validation_missions=["j3"]
    )
    train_obs = _subset(obs_all, split.train_idx)
    print(f"  train obs: {len(train_obs)} / {len(obs_all)}", flush=True)
    mdt_grid = load_mdt_grid(_MAPPING_OBS_PATHS, grid)

    mean_dest = _OUT_ROOT / f"phase10_probe_signed_mean{suffix}.nc"
    var_dest = _OUT_ROOT / f"phase10_probe_signed_var{suffix}.nc"
    print(f"  solving {len(output_days)} days -> {mean_dest} + {var_dest}", flush=True)
    t0 = time.monotonic()
    run_mean_var_maps(
        "oi",
        train_obs,
        provider,
        grid,
        half,
        output_days,
        mean_dest,
        var_dest,
        kernel=kernel,
        halo_deg=1.0,
        mdt_grid=mdt_grid,
    )
    wall_s = time.monotonic() - t0
    return {
        "config": "signed",
        "wall_s": wall_s,
        "peak_rss_mib": _peak_rss_mib(),
        "n_days": len(output_days),
        "framing": (
            "grid-node halo 1.0 deg; train-only obs (c2 locked, j3 validation); "
            "signed baseline config (Gaussian degree-space kernel)"
        ),
        "host": _host_fingerprint(),
        "mean_map": str(mean_dest),
        "var_map": str(var_dest),
    }


def _budget_template() -> dict[str, Any]:
    """Return the budget TEMPLATE block (named slots; numbers land in Task 5).

    Returns:
        The ``phase10.oi.probe.budget_template`` block: the recorded formula
        plus named empty slots the Task-5 pre-registration fills.
    """
    return {
        "formula": "n_sobol_per_lane = floor(wall_budget_h*3600 / (t_trial_s * n_lanes))",
        "t_trial_s": None,
        "wall_budget_h": None,
        "wall_budget_provenance": None,
        "n_lanes": None,
        "n_sobol_per_lane": None,
        "minimum_floor": 8,
        "note": (
            "TEMPLATE written at Task 0; Task 5 finalizes the arithmetic from "
            "the measured Paciorek-path trial cost and the owner-supplied wall "
            "budget (spec §4). n < minimum_floor -> screening contingency ACTIVE."
        ),
    }


def main() -> None:
    """Run the requested probe config and record the measurement.

    Raises:
        SystemExit: For ``--config paciorek`` before Task 4 lands the kernel.
    """
    parser = argparse.ArgumentParser(description="Phase-10 runtime probe (spec §4).")
    parser.add_argument("--config", choices=["signed", "paciorek"], required=True)
    args = parser.parse_args()

    if args.config == "paciorek":
        raise SystemExit("paciorek path lands Task 4")

    output_days = _DEV_DAYS if _SCOPE == "dev" else _FULL_DAYS
    suffix = "_dev" if _SCOPE == "dev" else ""
    print(f"[phase10_probe] config=signed scope={_SCOPE!r}", flush=True)
    block = _run_signed_probe(output_days, suffix)
    print(
        f"[probe] signed wall={block['wall_s']:.1f} "
        f"peak_rss={block['peak_rss_mib']:.0f} MiB",
        flush=True,
    )
    if _SCOPE == "dev":
        print("[dev smoke] gate evidence NOT written (dev scope).", flush=True)
        return
    _write_evidence("phase10.oi.probe.signed", block)
    # Clobber guard: never reset a budget already finalized by Task 5.
    existing = (
        json.loads(_RESULTS.read_text())
        .get("phase10", {})
        .get("oi", {})
        .get("probe", {})
        .get("budget_template", {})
    )
    if existing.get("n_sobol_per_lane") is None:
        _write_evidence("phase10.oi.probe.budget_template", _budget_template())
    print(f"[probe] wrote phase10.oi.probe.signed + budget_template to {_RESULTS}")


if __name__ == "__main__":
    main()
