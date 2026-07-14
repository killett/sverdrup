"""Phase-10 Task-5 pre-registration: ONE artifact, sealed BEFORE any trial.

Seals the band PROTOCOL (procedure only — NO operative band values; owner
plan-review correction 1), finalizes the budget arithmetic from the measured
probe costs, pins the screening contingency constants (day list + k), and
records the DEMOTED probe-pair shakedown (machinery + dissimilar-pair noise
scale; never operative). Everything lands in one commit (batch-2 fold 3).

Prerequisites: both probe measurements present in the gate JSON
(``phase10.oi.probe.signed`` from Task 0, ``phase10.oi.probe.paciorek`` from
this task's probe run) and the four probe map files on disk.

Outputs:
- ``phase10_band_artifact.json`` — the sealed protocol (+ contingency block
  + demoted probe_pair_reference).
- Evidence keys: ``phase10.oi.band_protocol`` (path + sha256 + created_utc),
  ``phase10.oi.probe.budget`` (finalized arithmetic + provenance).

c2 is NEVER touched: the shakedown scores the j3 validation track only.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

_OUT_ROOT = Path("data/2021a_ssh_mapping_ose/ours")
_RESULTS = _OUT_ROOT / "stage_miost_gate_results.json"
_PROTOCOL_PATH = _OUT_ROOT / "phase10_band_artifact.json"
_VAL_TRACK = Path(
    "data/2021a_ssh_mapping_ose/dc_obs/"
    "dt_gulfstream_j3_phy_l3_20161201-20180131_285-315_23-53.nc"
)

# Budget inputs (spec §4). wall_budget_h is recorded WITH provenance: the
# plan's "owner-supplied at execution" slot is filled executor-side in the
# owner's absence — the evidence block names who set it; the owner can veto
# at gate 1 before anything claim-bearing depends on it.
_WALL_BUDGET_H = 12.0
_WALL_BUDGET_PROVENANCE = (
    "executor-set 2026-07-13 (owner absent at execution; overnight-scale on "
    "the probe host); recorded per the plan's who-set-it requirement"
)
_N_LANES = 3  # lane0, V, VL (L-only is conditional at four lanes, Task 8)
_MIN_FLOOR = 8  # n_sobol_per_lane below this -> screening contingency ACTIVE

# Screening contingency constants (spec §4): every 4th day of 2017 starting
# day 1 -> 91 days, stratified across the year; k full-year re-scores.
_SCREENING_DAYS: list[int] = list(range(1, 365, 4))
_SCREENING_K = 3


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _probe_track(mean_map: Path) -> dict[str, np.ndarray]:
    """Interp a probe mean map onto the j3 validation track (harness box).

    Args:
        mean_map: The probe mean-map NetCDF.

    Returns:
        Track arrays ``{time, lat, lon, ssh, mean_interp}`` (finite subset).
    """
    from sverdrup.validation.provenance_guard import (  # noqa: PLC0415
        assert_scored_not_assimilated,
    )
    from sverdrup.validation.vendor import prepare_vendored_imports  # noqa: PLC0415

    assert_scored_not_assimilated(mean_map, _VAL_TRACK)
    prepare_vendored_imports()
    from src.mod_inout import read_l3_dataset  # noqa: PLC0415
    from src.mod_interp import interp_on_alongtrack  # noqa: PLC0415

    box = dict(
        lon_min=295.0,
        lon_max=305.0,
        lat_min=33.0,
        lat_max=43.0,
        time_min="2017-01-01",
        time_max="2018-01-01",
    )
    ds_at = read_l3_dataset(str(_VAL_TRACK), **box)
    t_a, lat_a, lon_a, ssh, mu = interp_on_alongtrack(
        str(mean_map), ds_at, is_circle=False, **box
    )
    ssh, mu = np.asarray(ssh, float), np.asarray(mu, float)
    ok = np.isfinite(ssh) & np.isfinite(mu)
    return {
        "time": np.asarray(t_a)[ok],
        "lat": np.asarray(lat_a, float)[ok],
        "lon": np.asarray(lon_a, float)[ok],
        "ssh": ssh[ok],
        "mean_interp": mu[ok],
    }


def main() -> None:
    """Seal the pre-registration artifact and write the evidence blocks.

    Raises:
        SystemExit: If either probe measurement or map file is missing.
    """
    # Deferred import keeps this script import-light (probe module loads the
    # heavy validation stack lazily too).
    import importlib.util  # noqa: PLC0415

    from sverdrup.application.tuning.lane_compare import (  # noqa: PLC0415
        BandProtocol,
        compute_bands,
        load_protocol,
        seal_protocol,
    )

    spec = importlib.util.spec_from_file_location(
        "phase10_probe", Path(__file__).parent / "phase10_probe.py"
    )
    if spec is None or spec.loader is None:
        raise SystemExit("cannot load scripts/phase10_probe.py")
    probe_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe_mod)

    results = json.loads(_RESULTS.read_text())
    probe = results.get("phase10", {}).get("oi", {}).get("probe", {})
    for key in ("signed", "paciorek"):
        if "mean_map" not in probe.get(key, {}):
            raise SystemExit(
                f"phase10.oi.probe.{key} missing or malformed — run the probe first"
            )
    mean_signed = Path(probe["signed"]["mean_map"])
    mean_pac = Path(probe["paciorek"]["mean_map"])
    for p in (mean_signed, mean_pac):
        if not p.exists():
            raise SystemExit(f"probe map missing: {p}")

    # ------------------------------------------------------------------
    # Budget arithmetic (spec §4) from the MEASURED Paciorek trial cost.
    # ------------------------------------------------------------------
    t_trial = float(probe["paciorek"]["wall_s"])
    n_full = probe_mod.trials_per_lane(
        t_trial_s=t_trial, wall_budget_h=_WALL_BUDGET_H, n_lanes=_N_LANES
    )
    n_full_four_lanes = probe_mod.trials_per_lane(
        t_trial_s=t_trial, wall_budget_h=_WALL_BUDGET_H, n_lanes=4
    )
    contingency_active = n_full < _MIN_FLOOR
    t_screening = t_trial * (len(_SCREENING_DAYS) / 365.0)
    n_screening = probe_mod.trials_per_lane(
        t_trial_s=t_screening, wall_budget_h=_WALL_BUDGET_H, n_lanes=_N_LANES
    )

    budget: dict[str, Any] = {
        "formula": (
            "n_sobol_per_lane = floor(wall_budget_h*3600 / (t_trial_s * n_lanes))"
        ),
        "t_trial_s": t_trial,
        "t_trial_source": "phase10.oi.probe.paciorek wall_s (full-year re-solve)",
        "wall_budget_h": _WALL_BUDGET_H,
        "wall_budget_provenance": _WALL_BUDGET_PROVENANCE,
        "n_lanes": _N_LANES,
        "n_sobol_per_lane": n_full,
        "n_sobol_per_lane_four_lanes": n_full_four_lanes,
        "minimum_floor": _MIN_FLOOR,
        "contingency_active": contingency_active,
        "screening": {
            "t_trial_s": t_screening,
            "n_sobol_per_lane": n_screening,
            "note": (
                "screening trials score every 4th day of 2017 (91 days); the "
                "top-k per lane are re-scored full-year (k below)"
            ),
        },
    }

    # ------------------------------------------------------------------
    # Probe-pair shakedown (DEMOTED — machinery + noise scale, never
    # operative): computed ONCE with a provisional (unsealed) protocol.
    # ------------------------------------------------------------------
    provisional = BandProtocol(
        created_utc="unsealed-shakedown",
        resample_seed=271828,
        block_unit="contiguous day/pass segments",
        n_resamples=2000,
        n_lambda_resamples=200,
        machinery="application/calibration folds rho/n_eff segmentation",
        lambda_informative_rule="band_lambda_x <= 25 km, evaluated per computed pair",
        single_execution_rule=(
            "one seeded computation per consulted pair; values recorded in the "
            "consuming record with write-times"
        ),
        protocol_sha="unsealed-shakedown",
    )
    print("[prereg] interpolating probe pair onto the validation track ...", flush=True)
    track_a = _probe_track(mean_signed)
    track_b = _probe_track(mean_pac)
    print(f"[prereg] shakedown on {track_a['ssh'].size} track points ...", flush=True)
    t0 = time.monotonic()
    shakedown = compute_bands(track_a, track_b, provisional)
    shakedown_wall = time.monotonic() - t0
    print(
        f"[prereg] shakedown: dmu={shakedown.delta_mu:+.5f} "
        f"band_mu={shakedown.band_mu:.5f} dlx={shakedown.delta_lambda_x:+.2f} "
        f"band_lx={shakedown.band_lambda_x:.2f} km "
        f"(n_seg={shakedown.n_segments}, wall={shakedown_wall:.0f}s)",
        flush=True,
    )

    probe_pair_reference = {
        "source_pair": {"a": _sha256(mean_signed), "b": _sha256(mean_pac)},
        "band_mu": shakedown.band_mu,
        "band_lambda_x": shakedown.band_lambda_x,
        "delta_mu": shakedown.delta_mu,
        "delta_lambda_x": shakedown.delta_lambda_x,
        "n_segments": shakedown.n_segments,
        "n_lambda_used": shakedown.n_lambda_used,
        "shakedown_wall_s": shakedown_wall,
        "note": "machinery shakedown + dissimilar-pair noise scale; NEVER operative",
    }

    # ------------------------------------------------------------------
    # Seal: protocol + contingency constants in ONE artifact.
    # ------------------------------------------------------------------
    created = datetime.now(UTC).isoformat()
    sha = seal_protocol(
        _PROTOCOL_PATH,
        created_utc=created,
        probe_pair_reference=probe_pair_reference,
        extra={
            "screening_days": _SCREENING_DAYS,
            "screening_k": _SCREENING_K,
            "contingency_active": contingency_active,
        },
    )
    sealed = load_protocol(_PROTOCOL_PATH, expected_sha=sha)  # round-trip check
    print(f"[prereg] sealed {_PROTOCOL_PATH} sha256={sha}", flush=True)

    # ------------------------------------------------------------------
    # Evidence blocks (nested-key writer pattern; each write is atomic).
    # ORDER MATTERS: budget first, band_protocol POINTER last — a crash
    # between the two leaves no protocol pointer, so nothing downstream can
    # consume bands against a half-registered state; rerun heals.
    # ------------------------------------------------------------------
    probe_mod._write_evidence("phase10.oi.probe.budget", budget)
    probe_mod._write_evidence(
        "phase10.oi.band_protocol",
        {
            "path": str(_PROTOCOL_PATH),
            "sha256": sha,
            "created_utc": sealed.created_utc,
            "constants": dataclasses.asdict(sealed),
        },
    )
    print(
        f"[prereg] budget: t_trial={t_trial:.0f}s wall={_WALL_BUDGET_H}h "
        f"n_full={n_full} (4-lane {n_full_four_lanes}) "
        f"contingency_active={contingency_active} n_screening={n_screening}",
        flush=True,
    )
    print(f"[prereg] wrote phase10.oi.probe.budget + band_protocol to {_RESULTS}")


if __name__ == "__main__":
    main()
