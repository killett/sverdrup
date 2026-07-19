"""Phase-13 probe (plan Tasks 0/5): measured baselines for the budget arithmetic.

Leg A (``--leg scalar``, Task 0): one full-year FIVE-MISSION point solve at the
signed miost5 config (params verbatim from the signed record, asserted against
the frozen literal) — wall seconds, peak RSS, per-window PCG iteration counts
(signed-run baseline ~302 at cap 500: recorded beside, never asserted) — plus
REAL per-window pass counts from the geometry-artifact segmentation rule,
written to ``phase13.probe.scalar`` + ``phase13.probe.passes``.

Leg B (``--leg augmented``, Task 5): raises until the Task-2/4 augmented path
lands.

Scope discipline (phase10_probe pattern):
    SVERDRUP_PHASE13_SCOPE=dev  -> 12-day smoke; NEVER writes gate evidence.
    (default / full)            -> 365 days; writes ``phase13.probe.*``.

c2 is NEVER touched and j3 is NEVER assimilated here: the probe consumes the
five mapping missions only, enforced by :func:`guard_five_mission_inputs`
BEFORE any file opens (unit-tested; the input_adapter guard is the safety net).

Usage:
    SVERDRUP_PHASE13_SCOPE=dev pixi run python scripts/phase13_probe.py --leg scalar
    nohup pixi run python scripts/phase13_probe.py --leg scalar > probe.log 2>&1 &
"""

from __future__ import annotations

import argparse
import json
import os
import resource
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from sverdrup.core.observations import ObsWindow
    from sverdrup.methods.miost_windows import WindowPlan

# The segmentation gap rule is the GEOMETRY ARTIFACT'S, imported not copied
# (plan Task 0 AC: same constant the Phase-11 v3 artifact pins).
from sverdrup.application.orbit_geometry import _GAP_SEC as PASS_GAP_SEC

_DATA_ROOT = Path("data/2021a_ssh_mapping_ose")
_OBS_DIR = _DATA_ROOT / "dc_obs"
_OUT_ROOT = _DATA_ROOT / "ours"
_RESULTS = _OUT_ROOT / "stage_miost_gate_results.json"
_PHASE12_RESULTS = _OUT_ROOT / "phase12_miost6_results.json"
_GEOMETRY_ARTIFACT = _OUT_ROOT / "phase11_orbit_geometry.json"

# The five MAPPING missions (miost5 lineage). j3 = validation, c2 = withheld:
# neither may EVER appear in the probe's input list (guard below, unit-tested).
_FIVE_MISSIONS = ("alg", "h2g", "j2g", "j2n", "s3a")
_FIVE_MISSION_PATHS: list[Path] = [
    _OBS_DIR / f"dt_gulfstream_{m}_phy_l3_20161201-20180131_285-315_23-53.nc"
    for m in _FIVE_MISSIONS
]

# The signed Stage-A winner, verbatim (phase12_miost6_run precedent: the
# literal is asserted against the signed record at launch — drift refuses).
SIGNED_PARAMS = {
    "spacing_alpha": 1.0656719505786896,
    "log10_rho": -1.5990709075704217,
    "q_slope": 1.4518111273646355,
    "l_t_days": 6.00630128569901,
}

# Spec §12 analytic estimate replaced by measurement here (delta recorded,
# no bar) and the signed run's PCG-iteration figure (recorded beside only).
ANALYTIC_PASSES_PER_WINDOW = 240
SIGNED_PCG_ITERS_BASELINE = 302

# The PINNED augmented probe config (Task 5) — NO tuning meaning:
# delta = 0.2*[+1,+1,-1,-1] over (alg, h2g, j2g, j2n): a mid-scale
# contrast pattern whose derived s3a balance is exactly 0.0; Lambda at
# the MID of the pre-registered sweep box log10 in [-6, -2.5] (Task-6
# bundle) -> -4.25 for both modes (sigma_mode ~ 7.5 mm, cm-order).
_PROBE_DELTAS = {"alg": 0.2, "h2g": 0.2, "j2g": -0.2, "j2n": -0.2}
_PROBE_LOG_LAM = -4.25

# Budget constants (spec §7): trials floor, sealed screening contingency.
N_FULL_FLOOR = 8
SCREENING_N_PER_LANE = 30
SCREENING_K_FULL = 3
WALL_BUDGET_H_DEFAULT = 12.0  # pre-registered OWNER-AMENDABLE default
# (standing rule 3b: pre-registered default or the task WAITS — never
# executor-set; Task-6 bundle co-seals this value.)

_EARTH_RADIUS_KM = 6371.0

_SCOPE = os.environ.get("SVERDRUP_PHASE13_SCOPE", "full")
if _SCOPE not in {"dev", "full"}:
    raise SystemExit(f"SVERDRUP_PHASE13_SCOPE must be 'dev' or 'full', got {_SCOPE!r}")

_DEV_DAYS: list[float] = [float(d) for d in range(60, 72)]
_FULL_DAYS: list[float] = [float(d) for d in range(0, 365)]

_T0 = time.time()


def _log(msg: str) -> None:
    """Print a timestamped, flushed heartbeat line."""
    s = int(time.time() - _T0)
    print(f"[+{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}] {msg}", flush=True)


def trials_per_lane(t_trial_s: float, wall_budget_h: float, n_lanes: int) -> int:
    """Full-score trials per lane (spec §7 template, Phase-10 family).

    Args:
        t_trial_s: Measured wall seconds per trial (one full-year score).
        wall_budget_h: Wall budget in hours (12 h owner-amendable default).
        n_lanes: Number of SWEEPING lanes sharing the budget.

    Returns:
        ``floor(wall_budget_h*3600 / (t_trial_s * n_lanes))``, never negative.

    Raises:
        ValueError: If ``t_trial_s`` is not positive (bad measurement).
    """
    if t_trial_s <= 0:
        raise ValueError("t_trial_s must be positive")
    return max(0, int(wall_budget_h * 3600.0 // (t_trial_s * n_lanes)))


def budget_determination(
    t_trial_s: float, wall_budget_h: float = WALL_BUDGET_H_DEFAULT
) -> dict[str, Any]:
    """The §7 lane-budget determination, including the modes-only conditional.

    Rules (spec §7, pre-registered): lane-0 is QUOTED (costless); lane-D
    and lane-C are the committed sweeping lanes. The modes-only 4th lane
    runs iff the budget covers THREE sweeping lanes at n >= the floor
    (n3 >= 8) — in that case all three sweep at n3. Otherwise the two
    committed lanes sweep at n2 when n2 >= 8; below the floor the sealed
    91-day screening contingency arms (n=30/lane screening, k=3 full
    re-scores).

    Args:
        t_trial_s: Measured augmented trial cost (leg B wall seconds).
        wall_budget_h: Wall budget in hours.

    Returns:
        The determination block (recorded verbatim in the evidence).
    """
    n2 = trials_per_lane(t_trial_s, wall_budget_h, 2)
    n3 = trials_per_lane(t_trial_s, wall_budget_h, 3)
    modes_only = n3 >= N_FULL_FLOOR
    screening = (not modes_only) and n2 < N_FULL_FLOOR
    if modes_only:
        lanes, n_per_lane = ["D", "C", "modes-only"], n3
    else:
        lanes, n_per_lane = ["D", "C"], n2
    out: dict[str, Any] = {
        "formula": "n = floor(wall_budget_h*3600 / (t_trial_s * n_lanes))",
        "t_trial_s": t_trial_s,
        "wall_budget_h": wall_budget_h,
        "wall_budget_provenance": (
            "12 h pre-registered owner-amendable default (standing rule 3b; "
            "co-sealed in the Task-6 bundle)"
        ),
        "n_two_lanes": n2,
        "n_three_lanes": n3,
        "minimum_floor": N_FULL_FLOOR,
        "lanes": lanes,
        "n_per_lane": n_per_lane,
        "modes_only_runs": modes_only,
        "semantics_note": (
            "EQUAL-SHARING reading of spec §7 (recorded at Task-5 review): "
            "when the modes-only lane runs, all three sweeping lanes share "
            "the wall equally (n3 each). The alternative reading (committed "
            "lanes keep n2, modes-only gets the remainder) yields 2 lanes "
            "at n2 with modes-only unfunded at this t_trial; the sealed "
            "Task-6 bundle carries this choice for owner review at gate 1."
        ),
        "modes_only_reason": (
            f"n3 = {n3} >= floor {N_FULL_FLOOR}: 4th lane covered"
            if modes_only
            else f"n3 = {n3} < floor {N_FULL_FLOOR}: not run (recorded, spec §7)"
        ),
        "screening_contingency_active": screening,
    }
    if screening:
        out["n_screening_per_lane"] = SCREENING_N_PER_LANE
        out["k_full_rescores"] = SCREENING_K_FULL
    return out


def guard_five_mission_inputs(paths: list[Path]) -> list[Path]:
    """Refuse any input list carrying the j3 (validation) or c2 (withheld) file.

    The mission code is parsed from the standing filename pattern
    ``dt_gulfstream_<code>_phy_l3_...`` — a code-level check, never a raw
    substring match over the whole path (unit-tested both ways).

    Args:
        paths: Candidate obs file paths for the probe.

    Returns:
        The same list, unchanged, when clean.

    Raises:
        ValueError: If any path's mission code is ``j3`` or ``c2``.
    """
    for p in paths:
        name = Path(p).name
        parts = name.split("_")
        code = parts[2] if len(parts) > 2 else ""
        if code in {"j3", "c2"}:
            raise ValueError(
                f"mission {code!r} must not appear in the phase-13 probe input "
                f"list ({name}): j3 is the validation mission, c2 is withheld "
                "(zero-c2 discipline, plan Task 0)"
            )
    return paths


def _great_circle_km(lon: np.ndarray, lat: np.ndarray) -> float:
    """Total great-circle arc length [km] along consecutive points (haversine)."""
    if lon.size < 2:
        return 0.0
    lam = np.deg2rad(np.asarray(lon, dtype=float))
    phi = np.deg2rad(np.asarray(lat, dtype=float))
    dlam, dphi = np.diff(lam), np.diff(phi)
    a = (
        np.sin(dphi / 2.0) ** 2
        + np.cos(phi[:-1]) * np.cos(phi[1:]) * np.sin(dlam / 2.0) ** 2
    )
    return float(_EARTH_RADIUS_KM * np.sum(2.0 * np.arcsin(np.sqrt(a))))


def aggregate_pass_stats(
    frame: dict[str, np.ndarray],
    windows: list[tuple[str, float, float]],
    gap_sec: float = PASS_GAP_SEC,
) -> dict[str, dict[str, dict[str, Any]]]:
    """Per-window x mission pass statistics under the geometry-artifact gap rule.

    Segmentation: per mission, time-sorted obs split where the inter-obs gap
    exceeds ``gap_sec`` (the artifact's ``_GAP_SEC``, imported). Single-obs
    passes are KEPT — the Task-1 identity rule keeps them (s = 0); the
    artifact's ``split_passes`` drops them only because a direction is
    undefined for heading fits, which is irrelevant to mode counting.
    Windows overlap by design; an obs inside two windows contributes to both
    (each window solves independently, so each carries its own B columns).

    Args:
        frame: Arrays ``mission``, ``t_days``, ``lon``, ``lat`` (per-obs).
        windows: ``(window_id, start_day, end_day)`` triples, inclusive.
        gap_sec: Inter-pass gap threshold in seconds.

    Returns:
        ``{window_id: {mission: {n_passes, median_pass_n_obs, chord_km}}}``
        with ``chord_km`` carrying min/median/max per-pass arc length.
    """
    mission = np.asarray(frame["mission"])
    t = np.asarray(frame["t_days"], dtype=float)
    lon = np.asarray(frame["lon"], dtype=float)
    lat = np.asarray(frame["lat"], dtype=float)
    gap_days = gap_sec / 86400.0
    out: dict[str, dict[str, dict[str, Any]]] = {}
    for wid, start, end in windows:
        in_w = (t >= start) & (t <= end)
        per_mission: dict[str, dict[str, Any]] = {}
        for m in sorted({str(x) for x in mission[in_w]}):
            mask = in_w & (mission == m)
            order = np.argsort(t[mask], kind="stable")
            tm = t[mask][order]
            lom = lon[mask][order]
            lam = lat[mask][order]
            seg_id = np.concatenate([[0], np.cumsum(np.diff(tm) > gap_days)])
            n_obs_per_pass: list[int] = []
            chords: list[float] = []
            for seg in np.unique(seg_id):
                sel = seg_id == seg
                n_obs_per_pass.append(int(sel.sum()))
                chords.append(_great_circle_km(lom[sel], lam[sel]))
            per_mission[m] = {
                "n_passes": len(n_obs_per_pass),
                "median_pass_n_obs": float(np.median(n_obs_per_pass)),
                "chord_km": {
                    "min": float(np.min(chords)),
                    "median": float(np.median(chords)),
                    "max": float(np.max(chords)),
                },
            }
        out[wid] = per_mission
    return out


def _peak_rss_mib() -> float:
    """Peak RSS of this process [MiB] (Linux ``ru_maxrss`` is KiB)."""
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def _host_fingerprint() -> dict[str, Any]:
    """Host capacity: cpu count + MemAvailable GiB (NaN if unreadable)."""
    mem_gib = float("nan")
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                mem_gib = float(line.split()[1]) / (1024.0**2)
                break
    except OSError:
        pass
    return {"cpu_count": os.cpu_count(), "mem_available_gib": mem_gib}


def _sha256_file(path: Path) -> str:
    """sha256 hex digest of a file's bytes."""
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_evidence(key_path: str, block: dict[str, Any]) -> None:
    """Atomically merge ``block`` into the gate JSON under dotted ``key_path``.

    Single sequential writer by protocol (leg A at Task 0, leg B at Task 5) —
    the phase10_probe nested-key pattern.

    Args:
        key_path: Dotted evidence key, e.g. ``phase13.probe.scalar``.
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


def _assert_signed_params() -> dict[str, float]:
    """Assert the frozen literal equals the signed record's params, exactly.

    Returns:
        The verified signed params.

    Raises:
        SystemExit: On any exact-float mismatch (frozen record violated).
    """
    rec = json.loads(_RESULTS.read_text())
    for src_name, params in (
        ("winner.params", rec["winner"]["params"]),
        ("stage_b.winner_params", rec["stage_b"]["winner_params"]),
    ):
        if params != SIGNED_PARAMS:
            raise SystemExit(
                f"REFUSED: signed-record {src_name} != frozen literal "
                f"({params!r} vs {SIGNED_PARAMS!r})"
            )
    return dict(SIGNED_PARAMS)


def _task22_ledger_quote() -> dict[str, Any]:
    """Quote the Task-22 conservatism ledger verbatim from the phase-12 record.

    The retained-store term is named BY NAME per the Phase-12 close ruling;
    the model is NOT retuned here (plan Task 0 AC).

    Returns:
        The ledger quote block (ratio + note + measured peak + the term).
    """
    p12 = json.loads(_PHASE12_RESULTS.read_text())
    m6 = p12["phase12"]["miost6"]
    ledger = m6["budget"]["amended"]["task22_conservatism_ledger"]
    return {
        "model_over_measured_ratio": ledger["model_over_measured_ratio"],
        "note": ledger["note"],
        "phase12_measured_peak_rss_mib": m6["telemetry"]["peak_rss_mib"],
        "retained_store_term": (
            "RETAINED MEMBER STORE (~1.42 GB at phase-12 scale) — the term the "
            "Task-22 accumulator misses BY NAME (owner pack ruling 2026-07-18); "
            "re-grounding queue entry carries it; model NOT retuned here"
        ),
    }


def _pass_stats_block(obs: ObsWindow, plan: WindowPlan) -> dict[str, Any]:
    """Real per-window pass statistics from the halo-framed five-mission obs.

    Args:
        obs: The halo-framed ObsWindow the solver consumes.
        plan: The production WindowPlan (9 windows).

    Returns:
        The ``phase13.probe.passes`` evidence block.
    """
    coords = obs.coords()
    frame = {
        "mission": np.asarray(obs.mission),
        "lon": coords[:, 0],
        "lat": coords[:, 1],
        "t_days": coords[:, 2],
    }
    windows = [(w.id, w.start_day, w.end_day) for w in plan.windows]
    stats = aggregate_pass_stats(frame, windows, gap_sec=PASS_GAP_SEC)
    totals = {
        wid: sum(m["n_passes"] for m in per.values()) for wid, per in stats.items()
    }
    measured_mean = float(np.mean(list(totals.values())))
    return {
        "segmentation": {
            "rule": "time-gap > gap_sec per mission (geometry-artifact rule)",
            "gap_sec": PASS_GAP_SEC,
            "single_obs_passes": "kept (Task-1 identity rule; s = 0)",
            "geometry_artifact": str(_GEOMETRY_ARTIFACT),
            "geometry_artifact_sha256": _sha256_file(_GEOMETRY_ARTIFACT),
            "geometry_artifact_key": json.loads(_GEOMETRY_ARTIFACT.read_text())["key"],
        },
        "per_window": stats,
        "total_passes_per_window": totals,
        "analytic_vs_measured": {
            "analytic_passes_per_window": ANALYTIC_PASSES_PER_WINDOW,
            "measured_mean_passes_per_window": measured_mean,
            "delta": measured_mean - ANALYTIC_PASSES_PER_WINDOW,
            "note": "measurement REPLACES the spec-§12 estimate; no bar",
        },
    }


def _point_solve_run(
    method: Any,  # noqa: ANN401 - Miost, imported lazily by callers
    obs: ObsWindow,
    grid: Any,  # noqa: ANN401 - GridSpec, lazy
    params: dict[str, float],
    output_days: list[float],
) -> tuple[float, list[dict[str, Any]], float]:
    """Timed full-span point solve; returns (wall_s, PCG entries, checksum)."""
    from sverdrup.core.parameters import ConstantProvider  # noqa: PLC0415
    from sverdrup.methods.miost import CONVERGENCE_LOG  # noqa: PLC0415

    CONVERGENCE_LOG.clear()
    t0 = time.monotonic()
    checksum = 0.0
    for d in output_days:
        dist = method.solve(obs, grid, ConstantProvider(params), float(d))
        checksum += float(np.asarray(dist.mean).sum())
        if int(d) % 60 == 0:
            _log(f"  day {d:.0f} solved; elapsed {time.monotonic() - t0:.0f} s")
    wall_s = time.monotonic() - t0
    entries = [
        {k: v for k, v in e.items() if k != "params_key_hash"}
        for e in CONVERGENCE_LOG
        if "kind" not in e
    ]
    return wall_s, entries, checksum


def _load_probe_obs() -> tuple[ObsWindow, Any, dict[str, float]]:
    """Load the guarded five-mission obs + grid + signed params."""
    from sverdrup.validation.input_adapter import load_mapping_obs  # noqa: PLC0415
    from sverdrup.validation.params import baseline_config  # noqa: PLC0415
    from sverdrup.validation.run import halo_obs  # noqa: PLC0415

    params = _assert_signed_params()
    paths = guard_five_mission_inputs(list(_FIVE_MISSION_PATHS))
    provider, grid, _ = baseline_config()
    _log("loading five-mission mapping obs (j3/c2 guarded out) ...")
    obs = halo_obs(load_mapping_obs(paths, provider), grid)
    missions = sorted({str(m) for m in np.asarray(obs.mission)})
    if missions != sorted(_FIVE_MISSIONS):
        raise SystemExit(f"REFUSED: loaded missions {missions} != {_FIVE_MISSIONS}")
    _log(f"obs {len(obs)} across {missions}")
    return obs, grid, params


def _run_leg_augmented(output_days: list[float]) -> dict[str, Any]:
    """Leg B: the full-year point solve at the pinned augmented config.

    Args:
        output_days: Output day numbers (dev: 12 days; full: 365).

    Returns:
        The ``phase13.probe.augmented`` evidence block (budget arithmetic
        is derived from it and written separately).
    """
    from sverdrup.methods.miost import Miost  # noqa: PLC0415
    from sverdrup.methods.miost_rspec import RSpec  # noqa: PLC0415

    obs, grid, params = _load_probe_obs()
    rspec = RSpec(
        deltas=dict(_PROBE_DELTAS),
        log_lam_bias=_PROBE_LOG_LAM,
        log_lam_tilt=_PROBE_LOG_LAM,
    )
    method = Miost(rspec=rspec)
    wall_s, point_entries, checksum = _point_solve_run(
        method, obs, grid, params, output_days
    )
    return {
        "config": "augmented probe (pinned; no tuning meaning)",
        "params": params,
        "rspec": {
            "deltas": rspec.all_deltas,
            "log_lam_bias": _PROBE_LOG_LAM,
            "log_lam_tilt": _PROBE_LOG_LAM,
            "rationale": (
                "delta 0.2*[+1,+1,-1,-1] mid-scale contrast pattern "
                "(derived s3a = 0.0); Lambda at the mid of the sweep box "
                "log10 [-6, -2.5]"
            ),
        },
        "wall_s": round(wall_s, 1),
        "peak_rss_mib": round(_peak_rss_mib(), 1),
        "peak_note": (
            "point solve — the RETAINED MEMBER STORE term (the Task-22 "
            "accumulator miss, BY NAME) applies to ensemble runs only; "
            "quoted in the ledger below, model NOT retuned"
        ),
        "n_days": len(output_days),
        "n_obs": len(obs),
        "per_window_pcg": point_entries,
        "pcg_baseline_note": (
            f"conditioning watch (spec §2 rider 4): iterations beside leg A's "
            f"and the signed ~{SIGNED_PCG_ITERS_BASELINE} figure"
        ),
        "mean_map_checksum": checksum,
        "host": _host_fingerprint(),
        "task22_ledger": _task22_ledger_quote(),
    }


def _run_leg_scalar(output_days: list[float]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Leg A: the full-year five-mission point solve + pass statistics.

    Args:
        output_days: Output day numbers (dev: 12 days; full: 365).

    Returns:
        ``(phase13.probe.scalar, phase13.probe.passes)`` evidence blocks.
    """
    from sverdrup.methods.miost import Miost  # noqa: PLC0415

    obs, grid, params = _load_probe_obs()
    method = Miost()
    plan = method._plan
    passes_block = _pass_stats_block(obs, plan)
    _log(
        "pass stats: mean "
        f"{passes_block['analytic_vs_measured']['measured_mean_passes_per_window']:.1f}"
        f" passes/window (analytic {ANALYTIC_PASSES_PER_WINDOW})"
    )

    wall_s, point_entries, checksum = _point_solve_run(
        method, obs, grid, params, output_days
    )
    scalar_block = {
        "config": "scalar signed miost5",
        "params": params,
        "wall_s": round(wall_s, 1),
        "peak_rss_mib": round(_peak_rss_mib(), 1),
        "n_days": len(output_days),
        "n_obs": len(obs),
        "n_windows": len(plan.windows),
        "per_window_pcg": point_entries,
        "pcg_baseline_note": (
            f"signed-run figure ~{SIGNED_PCG_ITERS_BASELINE} iterations at cap "
            "500 — recorded beside, never asserted (plan Task 0)"
        ),
        "mean_map_checksum": checksum,
        "host": _host_fingerprint(),
        "task22_ledger": _task22_ledger_quote(),
    }
    return scalar_block, passes_block


def main() -> None:
    """Run the requested probe leg and record the measurement."""
    parser = argparse.ArgumentParser(description="Phase-13 probe (plan Tasks 0/5).")
    parser.add_argument("--leg", choices=["scalar", "augmented"], required=True)
    args = parser.parse_args()

    output_days = _DEV_DAYS if _SCOPE == "dev" else _FULL_DAYS
    _log(f"[phase13_probe] leg={args.leg} scope={_SCOPE!r}")

    if args.leg == "scalar":
        scalar_block, passes_block = _run_leg_scalar(output_days)
        _log(
            f"[probe] scalar wall={scalar_block['wall_s']:.1f} s "
            f"peak_rss={scalar_block['peak_rss_mib']:.0f} MiB"
        )
        if _SCOPE == "dev":
            _log("[dev smoke] gate evidence NOT written (dev scope).")
            return
        _write_evidence("phase13.probe.scalar", scalar_block)
        _write_evidence("phase13.probe.passes", passes_block)
        _log("[probe] wrote phase13.probe.scalar + phase13.probe.passes")
        return

    # leg B: augmented cost + the §7 budget determination
    aug_block = _run_leg_augmented(output_days)
    _log(
        f"[probe] augmented wall={aug_block['wall_s']:.1f} s "
        f"peak_rss={aug_block['peak_rss_mib']:.0f} MiB"
    )
    if _SCOPE == "dev":
        _log("[dev smoke] gate evidence NOT written (dev scope).")
        return
    scalar_rec = (
        json.loads(_RESULTS.read_text())
        .get("phase13", {})
        .get("probe", {})
        .get("scalar")
    )
    if scalar_rec is None:
        raise SystemExit(
            "REFUSED: phase13.probe.scalar absent — run leg A first "
            "(the delta and the budget consume it)"
        )
    aug_block["delta_vs_scalar"] = {
        "wall_s_scalar": scalar_rec["wall_s"],
        "wall_s_augmented": aug_block["wall_s"],
        "wall_delta_s": round(aug_block["wall_s"] - scalar_rec["wall_s"], 1),
        "wall_ratio": round(aug_block["wall_s"] / scalar_rec["wall_s"], 4),
        "note": "expected ~negligible at +0.24% cols (spec §7); measured anyway",
    }
    # t_trial: the augmented full-year point solve IS one sweep trial's
    # solve cost; validation scoring overhead rides on top (small, noted).
    budget = budget_determination(t_trial_s=aug_block["wall_s"])
    budget["t_trial_note"] = (
        "t_trial_s = leg-B wall (full-year augmented point solve); "
        "per-trial validation scoring overhead not included (small; the "
        "launch rule re-checks against measured trial wall at Task 8)"
    )
    _write_evidence("phase13.probe.augmented", aug_block)
    _write_evidence("phase13.probe.budget", budget)
    _log("[probe] wrote phase13.probe.augmented + phase13.probe.budget")


if __name__ == "__main__":
    main()
