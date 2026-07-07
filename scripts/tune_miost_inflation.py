"""Closed-form s* inflation tuning on the validation track (Task 17; D6/spec 6.3).

chi2_red(s) = chi2_red(1) / s  =>  s* = chi2_red(1). The rescale is an EXACT
anomaly x sqrt(s) (MiostEnsembleDistribution.rescaled); the Stage-A mean is
untouched by construction. Valid under the scalar-R condition only — the
script refuses heteroscedastic obs.

Usage (winner params from the Stage-A results JSON; validation track only,
never c2):
    SVERDRUP_MIOST_M=<members> pixi run python scripts/tune_miost_inflation.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

from sverdrup.eval.calibration import coverage, crps_gaussian, reduced_chi2

RESULTS = Path("data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json")
OUT_DIR = Path("data/2021a_ssh_mapping_ose/ours")
SCOPE = Path("tests/validation/fixtures/stage_a_scope.json")


def assert_scalar_r(r_var: np.ndarray) -> None:
    """Refuse the closed form unless the obs error variance is uniform.

    Args:
        r_var: Per-obs error variances.

    Raises:
        ValueError: If R is not scalar (heteroscedastic) — s* = chi2_red(1)
            is only the chi2 minimizer under scalar R.
    """
    if r_var.size and not np.all(r_var == r_var.flat[0]):
        raise ValueError(
            "s* closed form requires scalar R; got non-uniform per-obs "
            f"variances (min {r_var.min():.3e}, max {r_var.max():.3e})"
        )


def s_star_closed_form(mean: np.ndarray, var: np.ndarray, truth: np.ndarray) -> float:
    """s* = chi2_red(1): the s with chi2_red(s) = chi2_red(1)/s = 1.

    Args:
        mean: Predicted means at track points.
        var: UN-inflated predicted variances at track points.
        truth: Track observations.

    Returns:
        The closed-form inflation factor.
    """
    return float(reduced_chi2(mean, var, truth))


def main() -> None:
    """Tune s* at the Stage-A winner on the blocked validation track.

    Members come from ONE batched solve per window (merged_members) and all
    per-day mean/variance fields from the SPARSE S-path — never per-day
    sample_members re-solves, never dense BasisSpec.evaluate on the
    production grid (the OOM-#3 trap; Task-18 helpers).
    """
    import sverdrup.validation.their_eval as te
    from sverdrup.application.splits import make_splits
    from sverdrup.application.tuning.stage_a import _subset
    from sverdrup.core.parameters import ConstantProvider
    from sverdrup.core.seeding import derive_seed
    from sverdrup.distributions.miost_ensemble import (
        mean_fields,
        merged_members,
        std_fields,
    )
    from sverdrup.methods.miost import Miost
    from sverdrup.methods.miost_windows import WindowPlan
    from sverdrup.validation.input_adapter import load_mapping_obs, load_mdt_grid
    from sverdrup.validation.output_adapter import write_map
    from sverdrup.validation.params import baseline_config
    from sverdrup.validation.provenance_guard import assert_scored_not_assimilated

    m = int(os.environ.get("SVERDRUP_MIOST_M", "20"))
    results = json.loads(RESULTS.read_text())
    winner = dict(results["winner"]["params"])
    cfg = json.loads(SCOPE.read_text())
    cfg["validation_days"] = list(range(365))
    cfg["time_min"], cfg["time_max"] = "2017-01-01", "2018-01-01"

    provider, grid, _ = baseline_config()
    obs_full = load_mapping_obs([Path(p) for p in cfg["mapping_obs_paths"]], provider)
    split = make_splits(
        obs_full,
        by="mission",
        locked_missions=["c2"],
        validation_missions=[str(cfg["validation_mission"])],
    )
    obs = _subset(obs_full, split.train_idx)  # TRAIN-ONLY (leak hardening)
    assert_scalar_r(np.asarray(obs.error_model.variance))  # type: ignore[attr-defined]
    mdt = load_mdt_grid([Path(p) for p in cfg["mdt_paths"]], grid)

    method = Miost()
    root = derive_seed("miost", "stage-b-winner", "members", 0)
    days = [float(d) for d in cfg["validation_days"]]
    plan = WindowPlan()
    spec, etas_a, anoms, _starts = merged_members(
        method, obs, grid, ConstantProvider(winner), m, root
    )
    means = mean_fields(spec, _starts, etas_a, grid, plan, days)
    stds = std_fields(spec, _starts, anoms, grid, plan, days)
    mean_stack = means.reshape(len(days), *grid.shape) + mdt[None]
    var_stack = (stds**2).reshape(len(days), *grid.shape)
    epoch = np.datetime64("2017-01-01")
    times = epoch + np.asarray(days, dtype="int64") * np.timedelta64(1, "D")
    lon2d, lat2d = np.meshgrid(grid.x, grid.y)
    mean_nc = OUT_DIR / "stage_b_mean_maps.nc"
    var_nc = OUT_DIR / "stage_b_var_maps.nc"
    assimilated = (
        None
        if obs.mission is None
        else tuple(sorted({str(x) for x in np.asarray(obs.mission)}))
    )
    write_map(
        times,
        np.unique(lat2d),
        np.unique(lon2d),
        mean_stack,
        mean_nc,
        assimilated_missions=assimilated,
    )
    write_map(
        times,
        np.unique(lat2d),
        np.unique(lon2d),
        var_stack,
        var_nc,
        assimilated_missions=assimilated,
    )
    # Task-21 guard: this path scores the validation track on our own maps.
    assert_scored_not_assimilated(mean_nc, Path(cfg["val_track_path"]))

    te._prepare_imports()
    from src.mod_inout import read_l3_dataset
    from src.mod_interp import interp_on_alongtrack

    box = dict(
        lon_min=295.0,
        lon_max=305.0,
        lat_min=33.0,
        lat_max=43.0,
        time_min=cfg["time_min"],
        time_max=cfg["time_max"],
    )
    ds_at = read_l3_dataset(str(cfg["val_track_path"]), **box)
    _, _, _, ssh, mu = interp_on_alongtrack(str(mean_nc), ds_at, is_circle=False, **box)
    _, _, _, _, var = interp_on_alongtrack(str(var_nc), ds_at, is_circle=False, **box)
    ssh, mu, var = (np.asarray(a, float) for a in (ssh, mu, var))
    ok = np.isfinite(ssh) & np.isfinite(mu) & np.isfinite(var) & (var > 0)
    ssh, mu, var = ssh[ok], mu[ok], var[ok]

    s = s_star_closed_form(mu, var, ssh)
    print(f"s* = chi2_red(1) = {s:.4f}  (m={m}, {ssh.size} track points)")
    print(f"chi2_red(s*) = {reduced_chi2(mu, s * var, ssh):.6f} (identity check)")
    print(f"coverage_1sigma(s*) = {coverage(mu, s * var, ssh):.4f} (target 0.6827)")
    print(f"crps(s*) = {float(crps_gaussian(mu, s * var, ssh).mean()):.5f}")


if __name__ == "__main__":
    main()
