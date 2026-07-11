"""Phase-8 step-0 covariate alignment diagnostic (spec §1(a), §7 step 0).

Existing artifacts only; runs BEFORE any fit lane. Pre-registered promotion
rule: |Pearson r(per-cell log chi2_red at frozen s*, per-cell log proxy)| >= 0.6
promotes the signal-variance covariate to a third fit lane.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import xarray as xr
from scipy.stats import pearsonr  # type: ignore[import-untyped]

from sverdrup.application.calibration.constants import (
    CELL_DEG,
    COVERAGE_TARGET,
    PROMOTION_R,
    S_STAR,
)

RESULTS = Path("data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json")
MEAN_NC = Path("data/2021a_ssh_mapping_ose/ours/stage_b_mean_maps.nc")
VAR_NC = Path("data/2021a_ssh_mapping_ose/ours/stage_b_var_maps.nc")
SCOPE = Path("tests/validation/fixtures/stage_a_scope.json")
LON_EDGES = np.arange(295.0, 305.0 + CELL_DEG, CELL_DEG)
LAT_EDGES = np.arange(33.0, 43.0 + CELL_DEG, CELL_DEG)
MIN_CELL_POINTS = 200


def cell_index(lon: np.ndarray, lat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (row, col) 2°-cell indices, clipped to the 5x5 grid.

    Args:
        lon: Longitudes [deg east].
        lat: Latitudes [deg north].

    Returns:
        Tuple of (row, col) integer arrays, each clipped to [0, 4].
    """
    col = np.clip(np.searchsorted(LON_EDGES, lon, side="right") - 1, 0, 4)
    row = np.clip(np.searchsorted(LAT_EDGES, lat, side="right") - 1, 0, 4)
    return row, col


def proxy_cells(mean_ds: xr.Dataset) -> np.ndarray:
    """Return (5,5) per-cell mean of the per-node temporal std of the mean maps.

    Args:
        mean_ds: Dataset loaded from stage_b_mean_maps.nc, with ``ssh``
            variable of shape (time, lat, lon).

    Returns:
        Array of shape (5, 5) with per-cell mean temporal std [m].
    """
    std_map = mean_ds["ssh"].std(dim="time")  # (lat, lon) — spatial artifact
    out = np.full((5, 5), np.nan)
    lon2d, lat2d = np.meshgrid(std_map["lon"].values, std_map["lat"].values)
    row, col = cell_index(lon2d.ravel(), lat2d.ravel())
    vals = std_map.values.ravel()
    for r in range(5):
        for c in range(5):
            m = (row == r) & (col == c)
            out[r, c] = float(np.nanmean(vals[m]))
    return out


def per_cell_stats(
    lon: np.ndarray,
    lat: np.ndarray,
    resid: np.ndarray,
    var: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute per-cell chi2_red (UN-floored) and 1σ coverage at frozen s*.

    chi2_red = mean(resid**2 / (S_STAR * var)) — no SIGMA_OBS2 floor anywhere.
    coverage = mean(|resid| <= sqrt(S_STAR * var)).

    Args:
        lon: Track longitudes [deg east].
        lat: Track latitudes [deg north].
        resid: ssh_obs - ssh_mean at each track point [m].
        var: UN-inflated predicted variance at each track point [m^2].

    Returns:
        Tuple of (chi2_red_cells, coverage_cells, n_cells_arr), each (5,5).
        Cells with fewer than MIN_CELL_POINTS track points are NaN.
    """
    row, col = cell_index(lon, lat)
    chi2_cells = np.full((5, 5), np.nan)
    cov_cells = np.full((5, 5), np.nan)
    n_cells_arr = np.zeros((5, 5), dtype=int)
    inflated_var = S_STAR * var
    sd = np.sqrt(inflated_var)
    chi2_pts = resid**2 / inflated_var  # UN-floored
    cov_pts = (np.abs(resid) <= sd).astype(float)
    for r in range(5):
        for c in range(5):
            m = (row == r) & (col == c)
            n = int(m.sum())
            n_cells_arr[r, c] = n
            if n >= MIN_CELL_POINTS:
                chi2_cells[r, c] = float(np.mean(chi2_pts[m]))
                cov_cells[r, c] = float(np.mean(cov_pts[m]))
    return chi2_cells, cov_cells, n_cells_arr


def main() -> None:
    """Interpolate the existing maps onto the j3 validation track and record.

    Loads stage_b_mean_maps.nc and stage_b_var_maps.nc, interpolates onto
    the j3 validation track exactly as diag_stage_b_localized_calibration.py
    does, computes per-cell chi2_red (UN-floored at frozen s*) and 1σ coverage,
    then measures the two Pearson statistics over cells meeting the ≥200-point
    threshold. Writes the phase8.covariate_alignment block into the gate
    results JSON and prints the decision line.
    """
    import sverdrup.validation.their_eval as te
    from sverdrup.validation.provenance_guard import assert_scored_not_assimilated

    cfg = json.loads(SCOPE.read_text())
    results = json.loads(RESULTS.read_text())
    track = Path(cfg["val_track_path"])
    assert_scored_not_assimilated(MEAN_NC, track)

    te._prepare_imports()
    from src.mod_inout import read_l3_dataset
    from src.mod_interp import interp_on_alongtrack

    box = dict(
        lon_min=295.0,
        lon_max=305.0,
        lat_min=33.0,
        lat_max=43.0,
        time_min="2017-01-01",
        time_max="2018-01-01",
    )
    ds_at = read_l3_dataset(str(track), **box)
    t_a, lat_a, lon_a, ssh, mu = interp_on_alongtrack(
        str(MEAN_NC), ds_at, is_circle=False, **box
    )
    _, _, _, _, var = interp_on_alongtrack(str(VAR_NC), ds_at, is_circle=False, **box)
    ssh, mu, var = (np.asarray(a, float) for a in (ssh, mu, var))
    lat_a, lon_a = np.asarray(lat_a, float), np.asarray(lon_a, float)
    ok = np.isfinite(ssh) & np.isfinite(mu) & np.isfinite(var) & (var > 0)
    resid = (ssh - mu)[ok]
    lon_ok, lat_ok, var_ok = lon_a[ok], lat_a[ok], var[ok]

    # Per-cell chi2_red (UN-floored) and 1σ coverage at frozen S_STAR.
    chi2_cells, cov_cells, _ = per_cell_stats(lon_ok, lat_ok, resid, var_ok)

    # Proxy: per-cell mean of the per-node temporal std of mean maps.
    mean_ds = xr.open_dataset(MEAN_NC)
    proxy = proxy_cells(mean_ds)
    mean_ds.close()

    # Restrict to cells where both chi2 and proxy are finite.
    valid = (
        np.isfinite(chi2_cells) & np.isfinite(proxy) & (chi2_cells > 0) & (proxy > 0)
    )
    n_valid = int(valid.sum())
    log_chi2 = np.log(chi2_cells[valid])
    log_proxy = np.log(proxy[valid])
    log_deficit = np.log(np.abs(cov_cells[valid] - COVERAGE_TARGET) + 1e-9)

    r_primary, _ = pearsonr(log_chi2, log_proxy)
    r_deficit, _ = pearsonr(log_deficit, log_proxy)

    promoted = bool(abs(r_primary) >= PROMOTION_R)

    block = {
        "r_primary": float(r_primary),
        "r_deficit": float(r_deficit),
        "n_cells": n_valid,
        "promoted": promoted,
        "semantics": (
            "Phase-8 step-0 pre-registered promotion rule (spec §7 step 0, "
            "2026-07-10): PRIMARY = Pearson r(per-cell log chi2_red at frozen "
            f"s*={S_STAR}, per-cell log proxy); |r| >= {PROMOTION_R} promotes "
            "the signal-variance covariate to a third fit lane. "
            "chi2_red is UN-floored (no SIGMA_OBS2). "
            "Deficit variant = r(log|coverage - 0.6827|, log proxy), reported "
            "alongside but not used for promotion."
        ),
    }

    # Nest under "phase8" -> "covariate_alignment", preserving all other content.
    results.setdefault("phase8", {})["covariate_alignment"] = block
    RESULTS.write_text(json.dumps(results, indent=2))

    decision = "PROMOTED" if promoted else "NOT promoted"
    print(
        f"r_primary={r_primary:.4f}  r_deficit={r_deficit:.4f}  "
        f"n_cells={n_valid}  → {decision} (|r|>={PROMOTION_R})"
    )


if __name__ == "__main__":
    main()
