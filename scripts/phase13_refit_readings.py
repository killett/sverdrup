"""Phase-13 Task-11: s*/s(x) refit + §9 instrument readings.

Two legs, run AFTER the winner ensemble lands its maps + member store:

``--refit``
    The Phase-9 harness on the winner posterior maps under the FROZEN
    MIOST anchor-family frame (mask, scope config, fold seed tuple all
    byte-identical to ``MIOST_DESCRIPTOR`` — only the maps, evidence key,
    and field artifact differ). SIGMA_OBS2 untouched (spec §10.2: the
    calibration floor is the j3 validation track's noise, orthogonal to
    assimilated-mission R; contrasts-only identification could not update
    it anyway). Evidence: the full harness dict at ``phase13.miost.refit``
    plus the §9b rows (ŝ delta vs the signed miost5 ŝ, G_pre→G_post under
    the anchored G_pre with an exact-match refusal, s(x) shape summary).

``--readings``
    §9a/§9c/§9d report rows: GroundTrack + SpectralFidelity on the winner
    mean maps through the Phase-11 retro wiring (existing v3 geometry
    artifact, sha recorded), the direction row vs the 0.410 five-mission
    baseline (0.376 six-mission beside, non-governing), and mean-map
    deltas vs the signed miost5 stage-B maps. Evidence:
    ``phase13.miost.readings``. REPORT-ONLY (µ/λx remain the verdict).

Zero c2 throughout (validation track only).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import time
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import numpy as np

from sverdrup.application.calibration.harness import (
    MIOST_DESCRIPTOR,
    atomic_write_json,
    run_harness,
)

_OURS = Path("data/2021a_ssh_mapping_ose/ours")
_RESULTS = _OURS / "stage_miost_gate_results.json"
_GEOMETRY = _OURS / "phase11_orbit_geometry.json"

#: The sealed MIOST anchor-family G_pre (phase9.g_pre_anchor; exact).
_EXPECTED_G_PRE = 0.13510401012055406
#: The signed miost5 s_hat_floored (phase9.miost.fit_run reconciliation).
_MIOST5_SHAT = 8.737979722446696

PHASE13_DESCRIPTOR = replace(
    MIOST_DESCRIPTOR,
    product_id="miost_phase13",
    mean_maps=_OURS / "phase13_winner_mean.nc",
    var_maps=_OURS / "phase13_winner_var.nc",
    evidence_key="phase13.miost.refit",
    field_artifact=_OURS / "phase13_field_miost.json",
)


def _read_results() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(_RESULTS.read_text()))


def _write_evidence(key_path: str, value: object) -> None:
    results = _read_results()
    node: dict[str, Any] = results
    keys = key_path.split(".")
    for k in keys[:-1]:
        node = node.setdefault(k, {})
    node[keys[-1]] = value
    atomic_write_json(_RESULTS, results)


def _verify_gpre(anchor_block: dict[str, Any]) -> float:
    """Return the anchored G_pre or refuse on any drift (STOP pattern).

    Args:
        anchor_block: The ``phase9.g_pre_anchor``-bearing dict.

    Raises:
        SystemExit: On a mismatch with the sealed expected value.
    """
    g_pre = float(anchor_block["g_pre"]["g_pre"])
    if g_pre != _EXPECTED_G_PRE:
        raise SystemExit(
            f"G_pre STOP: anchored {g_pre!r} != expected {_EXPECTED_G_PRE!r} "
            "— the MIOST anchor family has drifted; owner adjudication"
        )
    return g_pre


def _direction_row(groundtrack_max_repeat: float) -> dict[str, Any]:
    """§9a direction row vs the five-mission 0.410 baseline.

    Args:
        groundtrack_max_repeat: The winner's max repeat-family
            track_excess_log10.

    Returns:
        The evidence row (direction + baselines + verbatim caveat).
    """
    return {
        "winner_max_repeat_track_excess_log10": groundtrack_max_repeat,
        "baseline_five_mission": 0.410,
        "six_mission_beside_non_governing": 0.376,
        "direction_vs_baseline": ("DOWN" if groundtrack_max_repeat < 0.410 else "UP"),
        "expectation": (
            "directional expectation DOWN from 0.410 if track-correlated "
            "error is real and absorbed (spec §9a)"
        ),
        "caveat": (
            "necessary-not-sufficient: a strong track signature proves a "
            "problem; a clean map does not prove correctness — a drop is "
            "supporting evidence, not proof"
        ),
    }


def run_refit() -> None:
    """The §9b refit leg (frozen anchor-family frame)."""
    for p in (PHASE13_DESCRIPTOR.mean_maps, PHASE13_DESCRIPTOR.var_maps):
        if not p.exists():
            raise SystemExit(f"missing {p} — run --winner-ensemble first")
    results = _read_results()
    g_pre = _verify_gpre({"g_pre": results["phase9"]["g_pre_anchor"]})

    t0 = time.monotonic()
    evidence = run_harness(PHASE13_DESCRIPTOR, "full")
    sel = evidence["selection"]
    g_post = float(sel["lane0_s_stat"]) - float(
        sel["eligibility"][sel["winner"]]["s_stat"]
    )
    shat = float(evidence["shat_reconciliation"]["s_hat_floored"])
    evidence["flattening_rows"] = {
        "s_hat": shat,
        "s_hat_miost5_signed": _MIOST5_SHAT,
        "s_hat_delta": shat - _MIOST5_SHAT,
        "expectation": (
            "representation error partially reattributed to obs error "
            "should LOWER the refit s_hat and may flatten s(x) (spec §9b)"
        ),
        "g_pre": g_pre,
        "g_post": g_post,
        "g_shrinkage": g_pre - g_post,
        "winner_lane": sel["winner"],
        "sigma_obs2_untouched": True,
        "wall_s": round(time.monotonic() - t0, 1),
    }
    _write_evidence("phase13.miost.refit", evidence)
    print(
        f"[refit] s_hat={shat:.6f} (miost5 {_MIOST5_SHAT:.6f}, "
        f"delta {shat - _MIOST5_SHAT:+.6f}); G {g_pre:.8f} -> {g_post:.8f} "
        f"(shrinkage {g_pre - g_post:+.8f}); winner={sel['winner']}",
        flush=True,
    )


def run_readings() -> None:
    """The §9a/c/d readings leg (report-only)."""
    import hashlib  # noqa: PLC0415

    import xarray as xr  # noqa: PLC0415

    mean_maps = PHASE13_DESCRIPTOR.mean_maps
    if not mean_maps.exists():
        raise SystemExit(f"missing {mean_maps} — run --winner-ensemble first")
    if not _GEOMETRY.exists():
        raise SystemExit(f"missing {_GEOMETRY} (phase-11 v3 geometry artifact)")

    spec = importlib.util.spec_from_file_location(
        "phase11_retro_run", Path("scripts/phase11_retro_run.py")
    )
    if spec is None or spec.loader is None:
        raise SystemExit("cannot load scripts/phase11_retro_run.py")
    retro = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(retro)

    block = retro.build_product_block(mean_maps, _GEOMETRY)
    gt = block["groundtrack"]
    # retro row schema (phase11.retro.miost.groundtrack): flat metrics
    # dict with the per-class maxima as *_max_repeat / *_max_drifting.
    max_repeat = float(gt["metrics"]["track_excess_log10_max_repeat"])

    # §9c precursor: mean-map deltas vs the signed miost5 stage-B maps.
    with (
        xr.open_dataset(mean_maps) as ds_new,
        xr.open_dataset(MIOST_DESCRIPTOR.mean_maps) as ds_ref,
    ):
        a = np.asarray(ds_new["ssh"].values, float)
        b = np.asarray(ds_ref["ssh"].values, float)
        n = min(a.shape[0], b.shape[0])
        d = a[:n] - b[:n]
        deltas = {
            "n_days_compared": int(n),
            "max_abs_delta_m": float(np.nanmax(np.abs(d))),
            "rms_delta_m": float(np.sqrt(np.nanmean(d**2))),
            "reference": str(MIOST_DESCRIPTOR.mean_maps),
        }

    reading = {
        "geometry_artifact": str(_GEOMETRY),
        "geometry_sha256": hashlib.sha256(_GEOMETRY.read_bytes()).hexdigest(),
        "groundtrack": gt,
        "direction_row": _direction_row(max_repeat),
        "spectral_fidelity": block["spectral_fidelity"],
        "spectral_note": (
            "descriptive only — sub-lambda_x rolloff caveat stands; no "
            "verdict semantics (spec §9d)"
        ),
        "mean_map_deltas_vs_miost5": deltas,
        "n_days": block["n_days"],
    }
    _write_evidence("phase13.miost.readings", reading)
    print(
        f"[readings] groundtrack max repeat={max_repeat:.3f} "
        f"({reading['direction_row']['direction_vs_baseline']} vs 0.410); "
        f"mean-map max|delta|={deltas['max_abs_delta_m']:.4f} m",
        flush=True,
    )


def main() -> None:
    """CLI: one leg per invocation (sequential single-writer)."""
    parser = argparse.ArgumentParser(description="Phase-13 refit + readings.")
    parser.add_argument("--refit", action="store_true")
    parser.add_argument("--readings", action="store_true")
    args = parser.parse_args()
    if args.refit == args.readings:
        parser.error("exactly one of --refit / --readings")
    if args.refit:
        run_refit()
    else:
        run_readings()


if __name__ == "__main__":
    main()
