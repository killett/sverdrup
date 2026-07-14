"""Phase-10 flattening readings under the FROZEN pre-B OI frame (spec §7).

Two modes:
    --anchor            recompute **G_pre_oi** canonically from
                        phase9.oi.fit_run -> phase10.g_pre_oi_anchor
                        (STOP-asserted against the spec expectation at 1e-12)
                        with the pre-B companions from phase9_field_oi.json.
    --stage {1,2}       G_post reading of a product's maps under the FROZEN
                        pre-B OI frame (phase-9 OI mask, sha-asserted; fold
                        tuple ("oi","phase9","s-folds"); s_salt 4 expected,
                        redraws [0,1,2,3] — differences recorded) ->
                        phase10.oi.flattening_stage<N>.

The frozen-frame run is COMPARISON ONLY: it never writes a field artifact
(the field_artifact path in its descriptor points at a scratch file that is
deleted afterwards); the NEW-frame acceptance fit (Task 10) is a separate
descriptor with a separate evidence key — two runs, never conflated.

The anchor guard (spec §0.3): phase9.g_pre_anchor is MIOST's — this script
reads phase9.oi.fit_run and writes phase10.g_pre_oi_anchor only.

c2 is NEVER touched (the harness never imports their_eval or c2 paths).
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any, cast

_OUT_ROOT = Path("data/2021a_ssh_mapping_ose/ours")
_RESULTS = _OUT_ROOT / "stage_miost_gate_results.json"
_P9_OI_MASK = _OUT_ROOT / "phase9_jet_core_mask_oi.json"
_P9_OI_FIELD = _OUT_ROOT / "phase9_field_oi.json"
_SCOPE_FIX = Path("tests/validation/fixtures/stage_a_scope.json")

# Frozen pre-B frame pins (spec §7).
_EXPECTED_G_PRE = 0.27086964275496783
_EXPECTED_MASK_SHA = "0deefcb961a3092279ca5de30852d65fffcbade304b19de0cb9e6a5d35ef0058"
_FROZEN_TUPLE = ("oi", "phase9", "s-folds")
_EXPECTED_SALT = 4
_EXPECTED_REDRAWS = [0, 1, 2, 3]


def _load_script(name: str) -> Any:  # noqa: ANN401 — dynamic script module
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).parent / f"{name}.py"
    )
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load scripts/{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_evidence(key_path: str, value: dict[str, object] | None) -> None:
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


def _mask_sha() -> str:
    return hashlib.sha256(_P9_OI_MASK.read_bytes()).hexdigest()


def run_anchor() -> None:
    """Recompute G_pre_oi canonically and write phase10.g_pre_oi_anchor.

    Raises:
        SystemExit: If the recomputation deviates from the spec expectation
            by more than 1e-12 (STOP — the pre-B record moved under us).
    """
    p9 = _load_script("phase9_g_pre_anchor")  # reuse the anchored companions math
    results = json.loads(_RESULTS.read_text())
    fit_run = results["phase9"]["oi"]["fit_run"]
    sel = fit_run["selection"]
    winner = sel["winner"]
    g_pre = float(sel["lane0_s_stat"]) - float(sel["eligibility"][winner]["s_stat"])
    if abs(g_pre - _EXPECTED_G_PRE) > 1e-12:
        raise SystemExit(
            f"G_pre_oi STOP: recomputed {g_pre!r} != expected {_EXPECTED_G_PRE!r} "
            "(tolerance 1e-12) — the phase-9 OI record moved; do not proceed"
        )

    field = json.loads(_P9_OI_FIELD.read_text())
    cal_json = field["calibration"]
    clip_frac = float(p9._compute_clip_engagement(cal_json))
    std_log_s, log_s_range = p9._compute_area_weighted_stats(cal_json)

    mask_sha = _mask_sha()
    if mask_sha != _EXPECTED_MASK_SHA:
        raise SystemExit(
            f"phase-9 OI mask sha {mask_sha} != frozen-frame pin "
            f"{_EXPECTED_MASK_SHA} — STOP"
        )
    block = {
        "g_pre_oi": g_pre,
        "definition": p9._SPEC_DEFINITION,
        "frame": {
            "mask": _P9_OI_MASK.name,
            "sha256": mask_sha,
            "fold_seed_tuple": list(_FROZEN_TUPLE),
            "salt": int(fit_run["folds"]["s_salt_final"]),
            "s_salt_redraws": [int(s) for s in fit_run["folds"]["s_salt_redraws"]],
        },
        "companions": {
            "area_weighted_std_log_s": float(std_log_s),
            "log_s_range": float(log_s_range),
            "clip_engagement_fraction": clip_frac,
            "nll_gap_demoted": {
                "value": None,
                "note": "pre-B OI NLL gap not recomputed; demoted per spec §7",
            },
        },
        "source": "recomputed canonically from phase9.oi.fit_run (spec §7 anchor)",
    }
    _write_evidence("phase10.g_pre_oi_anchor", block)
    print(
        f"[anchor] G_pre_oi = {g_pre!r} (expected match OK); companions "
        f"std_log_s={std_log_s:.4f} range={log_s_range:.4f} clip={clip_frac:.4f}",
        flush=True,
    )


def run_reading(stage: int, mean_maps: Path, var_maps: Path) -> None:
    """Run the frozen-frame G_post reading for a product's maps.

    Args:
        stage: 1 (V winner) or 2 (VL winner) — selects the evidence key.
        mean_maps: The product's full-year mean maps.
        var_maps: The product's full-year variance maps.

    Raises:
        SystemExit: If the frozen-frame pins (mask sha) do not hold, or the
            anchor has not been written yet.
    """
    from sverdrup.application.calibration.harness import (  # noqa: PLC0415
        ProductDescriptor,
        run_harness,
    )

    results = json.loads(_RESULTS.read_text())
    if "g_pre_oi_anchor" not in results.get("phase10", {}):
        raise SystemExit("run --anchor first (phase10.g_pre_oi_anchor missing)")
    mask_sha = _mask_sha()
    if mask_sha != _EXPECTED_MASK_SHA:
        raise SystemExit(
            f"FROZEN-FRAME REFUSAL: mask sha {mask_sha} != pinned "
            f"{_EXPECTED_MASK_SHA} — this runner only reads under the pre-B frame"
        )
    for p in (mean_maps, var_maps):
        if not p.exists():
            raise SystemExit(f"product maps missing: {p}")

    scratch_field = _OUT_ROOT / f"phase10_frozenframe_scratch_stage{stage}.json"
    desc = ProductDescriptor(
        product_id="oi",  # regions/promotion keyed like the phase-9 OI run
        mean_maps=mean_maps,
        var_maps=var_maps,
        scope_config=_SCOPE_FIX,
        mask_artifact=_P9_OI_MASK,
        evidence_key=f"phase10.oi.flattening_stage{stage}",
        field_artifact=scratch_field,
        fold_seed_tuple=_FROZEN_TUPLE,
        covariate_promoted=False,  # the phase-9 OI frame ran without covariate
    )
    evidence = run_harness(desc, "full")
    sel = evidence["selection"]
    winner = sel["winner"] if not sel.get("negative_result") else None
    g_post = (
        float(sel["lane0_s_stat"]) - float(sel["eligibility"][winner]["s_stat"])
        if winner
        else 0.0
    )
    salt = int(evidence["folds"]["s_salt_final"])
    redraws = [int(s) for s in evidence["folds"].get("s_salt_redraws", [])]
    frame_diffs: dict[str, Any] = {}
    if salt != _EXPECTED_SALT:
        frame_diffs["s_salt_final"] = {"expected": _EXPECTED_SALT, "got": salt}
    if redraws != _EXPECTED_REDRAWS:
        frame_diffs["s_salt_redraws"] = {
            "expected": _EXPECTED_REDRAWS,
            "got": redraws,
        }

    g_pre = float(results["phase10"]["g_pre_oi_anchor"]["g_pre_oi"])
    block = {
        "g_post": g_post,
        "g_pre_oi": g_pre,
        "g_shrinkage": g_pre - g_post,
        "winner": winner,
        "negative_result": bool(sel.get("negative_result", False)),
        "lane0_s_stat": float(sel["lane0_s_stat"]),
        "frame": {
            "mask": _P9_OI_MASK.name,
            "sha256": mask_sha,
            "fold_seed_tuple": list(_FROZEN_TUPLE),
            "s_salt_final": salt,
            "s_salt_redraws": redraws,
            "frame_differences": frame_diffs,  # empty == frame reproduced
        },
        "product_maps": {"mean": str(mean_maps), "var": str(var_maps)},
        "harness_evidence": evidence,
        "note": (
            "COMPARISON ONLY under the frozen pre-B OI frame; no field "
            "artifact written (scratch deleted); the acceptance fit is the "
            "separate NEW-frame descriptor (two runs, never conflated)"
        ),
    }
    _write_evidence(f"phase10.oi.flattening_stage{stage}", block)
    scratch_field.unlink(missing_ok=True)
    print(
        f"[stage{stage}] G_post={g_post:.6f} G_pre={g_pre:.6f} "
        f"shrinkage={g_pre - g_post:+.6f} winner={winner} "
        f"frame_diffs={frame_diffs or 'none'}",
        flush=True,
    )


def resolve_winner_maps(lane: str, stage: int) -> tuple[Path, Path]:
    """Re-solve a lane winner's config to persistent full-year maps.

    Args:
        lane: The lane whose recorded winner config is re-solved.
        stage: Stage number (names the output files).

    Returns:
        (mean_maps, var_maps) paths.

    Raises:
        SystemExit: If the lane winner is missing from the evidence.
    """
    lane_run = _load_script("phase10_lane_run")
    results = json.loads(_RESULTS.read_text())
    winner = (
        results.get("phase10", {})
        .get("oi", {})
        .get("lanes", {})
        .get(lane, {})
        .get("winner")
    )
    if not winner:
        raise SystemExit(f"phase10.oi.lanes.{lane}.winner missing — run the lane first")
    trial = {k: float(v) for k, v in winner["trial"].items()}

    from sverdrup.validation.run import run_mean_var_maps  # noqa: PLC0415

    ctx = lane_run._load_ctx()
    mean_p = _OUT_ROOT / f"phase10_stage{stage}_{lane}winner_mean.nc"
    var_p = _OUT_ROOT / f"phase10_stage{stage}_{lane}winner_var.nc"
    print(f"[stage{stage}] re-solving {lane} winner {trial} -> {mean_p}", flush=True)
    run_mean_var_maps(
        "oi",
        ctx["train"],
        lane_run.provider_for_trial(trial),
        ctx["grid"],
        ctx["half"],
        [float(d) for d in range(365)],
        mean_p,
        var_p,
        mdt_grid=ctx["mdt"],
        oi_gaussian_kernel_from_params=True,
    )
    return mean_p, var_p


def main() -> None:
    """CLI dispatch."""
    parser = argparse.ArgumentParser(description="Phase-10 flattening readings.")
    parser.add_argument("--anchor", action="store_true")
    parser.add_argument("--stage", type=int, choices=[1, 2])
    parser.add_argument("--mean-maps", type=Path)
    parser.add_argument("--var-maps", type=Path)
    parser.add_argument(
        "--from-winner",
        choices=["V", "VL"],
        help="re-solve this lane's recorded winner and read it (with --stage)",
    )
    args = parser.parse_args()
    if args.anchor:
        run_anchor()
        return
    if args.stage:
        if args.from_winner:
            mean_p, var_p = resolve_winner_maps(args.from_winner, args.stage)
        elif args.mean_maps and args.var_maps:
            mean_p, var_p = cast(Path, args.mean_maps), cast(Path, args.var_maps)
        else:
            raise SystemExit("--stage requires --from-winner or --mean-maps/--var-maps")
        run_reading(args.stage, mean_p, var_p)
        return
    raise SystemExit("nothing to do: pass --anchor or --stage")


if __name__ == "__main__":
    main()
