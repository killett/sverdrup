"""Phase-13 Task-6 pre-registration: ONE bundle, sealed BEFORE any sweep.

Seals the phase-13 band PROTOCOL (procedure only — no operative values;
Phase-10 family via ``lane_compare.seal_protocol``) with BOTH degradation
criteria explicit, co-seals the screening day list + k and the 12 h
owner-amendable wall default, restates the sweep boxes + designations +
negative wording from ``phase13_boxes``, and REGENERATES the lane-0
per-point validation residual arrays at the signed config — asserted
against the recorded validation µ before anything is sealed.

Prerequisites: ``phase13.probe.{scalar,augmented,budget}`` present (Tasks
0/5) — the budget determination is restated into the artifact verbatim.

Outputs:
- ``phase13_band_artifact.json`` — the sealed protocol (+ co-sealed blocks).
- ``phase13_residuals_lane0.npz`` — lane-0 per-point track arrays.
- Evidence keys: ``phase13.band_protocol``, ``phase13.lane0_reference``.

c2 is NEVER touched: the regeneration scores the j3 validation track only
(the standing provenance guard runs before interpolation).
"""

from __future__ import annotations

import dataclasses
import hashlib
import importlib.util
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from sverdrup.validation import phase13_boxes as boxes

_OUT_ROOT = Path("data/2021a_ssh_mapping_ose/ours")
_RESULTS = _OUT_ROOT / "stage_miost_gate_results.json"
_PROTOCOL_PATH = _OUT_ROOT / "phase13_band_artifact.json"
_LANE0_NPZ = _OUT_ROOT / "phase13_residuals_lane0.npz"
_LANE0_MEAN_NC = _OUT_ROOT / "phase13_lane0_mean.nc"
_VAL_TRACK = Path(
    "data/2021a_ssh_mapping_ose/dc_obs/"
    "dt_gulfstream_j3_phy_l3_20161201-20180131_285-315_23-53.nc"
)

# The signed record's validation µ, frozen at full precision (asserted
# against the record by test; the regenerated lane-0 must reproduce it).
RECORDED_LANE0_MU = 0.8641999994291494

# Screening contingency constants (spec §7, Phase-10 family): every 4th
# day of 2017 -> 91 days, stratified; k full-year re-scores.
SCREENING_DAYS: list[int] = list(range(1, 365, 4))
SCREENING_K = 3


def assert_lane0_mu(mu_computed: float, mu_recorded: float) -> None:
    """Refuse a lane-0 regeneration that fails to reproduce the record.

    Exact float equality: the regeneration runs the SAME deterministic
    pipeline (solve -> interp -> leaderboard_nrmse) that produced the
    signed number, so anything but bit-reproduction means a different
    product is about to anchor every pair band.

    Args:
        mu_computed: µ from the regenerated arrays.
        mu_recorded: The signed record's ``winner.scores.mu_score``.

    Raises:
        SystemExit: On any mismatch.
    """
    if mu_computed != mu_recorded:
        raise SystemExit(
            f"REFUSED: regenerated lane-0 mu {mu_computed!r} != recorded "
            f"{mu_recorded!r} — the reference side does not reproduce the "
            "signed product; nothing is sealed"
        )


def _load_probe_module() -> Any:  # noqa: ANN401 - script module
    spec = importlib.util.spec_from_file_location(
        "phase13_probe", Path(__file__).parent / "phase13_probe.py"
    )
    if spec is None or spec.loader is None:
        raise SystemExit("cannot load scripts/phase13_probe.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _regenerate_lane0(probe_mod: Any) -> dict[str, Any]:  # noqa: ANN401
    """Full-year signed-config solve -> j3-track arrays -> µ assertion.

    Returns:
        The ``phase13.lane0_reference`` evidence block.
    """
    import xarray as xr  # noqa: PLC0415

    from sverdrup.core.parameters import ConstantProvider  # noqa: PLC0415
    from sverdrup.eval.skill_score import leaderboard_nrmse  # noqa: PLC0415
    from sverdrup.methods.miost import Miost  # noqa: PLC0415
    from sverdrup.validation.input_adapter import load_mdt_grid  # noqa: PLC0415
    from sverdrup.validation.output_adapter import write_map  # noqa: PLC0415
    from sverdrup.validation.provenance_guard import (  # noqa: PLC0415
        assert_scored_not_assimilated,
    )
    from sverdrup.validation.vendor import prepare_vendored_imports  # noqa: PLC0415

    obs, grid, params = probe_mod._load_probe_obs()
    method = Miost()
    days = [float(d) for d in range(365)]
    print("[prereg] lane-0 regeneration: full-year signed solve ...", flush=True)
    t0 = time.monotonic()
    maps = [
        np.asarray(method.solve(obs, grid, ConstantProvider(params), d).mean)
        for d in days
    ]
    wall = time.monotonic() - t0
    # MDT from the SIGNED scorer's mdt_paths (the six-file scope list, j3
    # included — MDT is a static reference surface, not assimilation; the
    # five-file variant shifts µ at the 4e-6 level and fails the exact
    # reproduction assert — measured at first regeneration attempt).
    scope_cfg = json.loads(
        Path("tests/validation/fixtures/stage_a_scope.json").read_text()
    )
    mdt = load_mdt_grid([Path(p) for p in scope_cfg["mdt_paths"]], grid)
    epoch = np.datetime64("2017-01-01")
    times = epoch + np.asarray(days, dtype="int64") * np.timedelta64(1, "D")
    stack = np.stack(maps) + np.asarray(mdt)[None]
    write_map(times, grid.y, grid.x, stack, _LANE0_MEAN_NC)
    print(f"[prereg] solve wall {wall:.0f} s; interpolating onto j3 ...", flush=True)

    assert_scored_not_assimilated(_LANE0_MEAN_NC, _VAL_TRACK)
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
    t_a, lat_a, lon_a, ssh, mu_i = interp_on_alongtrack(
        str(_LANE0_MEAN_NC), ds_at, is_circle=False, **box
    )
    ssh, mu_i = np.asarray(ssh, float), np.asarray(mu_i, float)
    ok = np.isfinite(ssh) & np.isfinite(mu_i)
    trk = {
        "time": np.asarray(t_a)[ok],
        "lat": np.asarray(lat_a, float)[ok],
        "lon": np.asarray(lon_a, float)[ok],
        "ssh": ssh[ok],
        "mean_interp": mu_i[ok],
    }
    mu = float(leaderboard_nrmse(trk["ssh"], trk["mean_interp"]))
    print(f"[prereg] lane-0 regenerated mu = {mu!r}", flush=True)
    assert_lane0_mu(mu, RECORDED_LANE0_MU)
    np.savez(_LANE0_NPZ, **trk)
    with xr.open_dataset(_LANE0_MEAN_NC) as _:
        pass  # readability check only
    return {
        "residuals_npz": str(_LANE0_NPZ),
        "residuals_sha256": hashlib.sha256(_LANE0_NPZ.read_bytes()).hexdigest(),
        "mean_map": str(_LANE0_MEAN_NC),
        "mu_score": mu,
        "mu_recorded": RECORDED_LANE0_MU,
        "n_track_points": int(trk["ssh"].size),
        "solve_wall_s": round(wall, 1),
        "note": (
            "per-point j3 validation arrays for pair-band computation "
            "(bands need arrays, not summary numbers — spec §7); µ asserted "
            "EXACT against the signed record before sealing"
        ),
    }


def main() -> None:
    """Regenerate lane-0, seal the bundle, write the evidence blocks."""
    probe_mod = _load_probe_module()
    results = json.loads(_RESULTS.read_text())
    probe = results.get("phase13", {}).get("probe", {})
    for key in ("scalar", "augmented", "budget"):
        if key not in probe:
            raise SystemExit(f"phase13.probe.{key} missing — run the probes first")

    lane0_block = _regenerate_lane0(probe_mod)

    created = datetime.now(UTC).isoformat()
    from sverdrup.application.tuning.lane_compare import (  # noqa: PLC0415
        load_protocol,
        seal_protocol,
    )

    sha = seal_protocol(
        _PROTOCOL_PATH,
        created_utc=created,
        extra={
            "phase": "phase13",
            "degradation_criteria": {
                "n_lambda_used_min_frac": boxes.N_LAMBDA_USED_MIN_FRAC,
                "band_lambda_x_max_km": boxes.BAND_LAMBDA_X_MAX_KM,
                "rule": (
                    "the lambda tie-break fires only if BOTH hold: "
                    "n_lambda_used >= 50% AND band_lambda_x <= 25 km; "
                    "either failing degrades to mu-primary with a note"
                ),
                "deviation_from_phase10": boxes.DEGRADATION_DEVIATION_NOTE,
            },
            "screening_days": SCREENING_DAYS,
            "screening_k": SCREENING_K,
            "wall_budget_h_default": probe_mod.WALL_BUDGET_H_DEFAULT,
            "wall_budget_note": (
                "12 h pre-registered OWNER-AMENDABLE default (standing rule "
                "3b: pre-registered default or the task WAITS)"
            ),
            "budget_determination": results["phase13"]["probe"]["budget"],
            "boxes": {
                "delta_box": list(boxes.DELTA_BOX),
                "swept_deltas": list(boxes.SWEPT_DELTAS),
                "delta_s3a_derived_range": list(boxes.DELTA_S3A_DERIVED_RANGE),
                "log10_lam_box": list(boxes.LOG10_LAM_BOX),
                "log10_rho_box": list(boxes.LOG10_RHO_BOX),
                "source_table": (
                    "phase13_boxes.py module docstring (quoted verbatim at "
                    "gate 1; verify-at-review marks resolve there)"
                ),
            },
            "sobol": {
                "engine": list(boxes.SOBOL_ENGINE_KEY),
                "dims": list(boxes.SOBOL_DIMS),
                "masking": (
                    "per-lane dim MASKING of ONE shared 7-dim sequence; "
                    "NO per-lane engines; anchors are evaluated extra "
                    "points, never Sobol points"
                ),
            },
            "designations": {
                "primary": boxes.PRIMARY_COMPARISON,
                "secondaries": list(boxes.SECONDARY_COMPARISONS),
                "winner_lane_rule": boxes.WINNER_LANE_RULE,
                "modes_only_conditional_rule": boxes.MODES_ONLY_CONDITIONAL_RULE,
            },
            "negative_wording": {
                "verbatim": boxes.NEGATIVE_WORDING,
                "scope_clause": boxes.NEGATIVE_SCOPE_CLAUSE,
                "framing": boxes.NEGATIVE_FRAMING,
            },
            "lane0_reference": lane0_block,
        },
    )
    sealed = load_protocol(_PROTOCOL_PATH, expected_sha=sha)  # round-trip check
    print(f"[prereg] sealed {_PROTOCOL_PATH} sha256={sha}", flush=True)

    # ORDER MATTERS (phase10_prereg pattern): lane0_reference first, the
    # protocol POINTER last — a crash between the two leaves no pointer,
    # nothing downstream consumes a half-registered state; rerun heals.
    probe_mod._write_evidence("phase13.lane0_reference", lane0_block)
    probe_mod._write_evidence(
        "phase13.band_protocol",
        {
            "path": str(_PROTOCOL_PATH),
            "sha256": sha,
            "created_utc": sealed.created_utc,
            "constants": dataclasses.asdict(sealed),
        },
    )
    print(f"[prereg] wrote phase13.lane0_reference + band_protocol to {_RESULTS}")


if __name__ == "__main__":
    main()
