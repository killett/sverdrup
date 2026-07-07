"""Report-only localized calibration at the FROZEN s* (owner protocol item 3).

Validation-side only, from the existing Stage-B maps — c2 is never touched
here. Coverage (and chi2 context) at the frozen s* split by (a) blend vs
interior days, (b) spatial quadrants of the box, (c) month. NOT a bar: the
gate bars stay as pre-registered; severe local mis-calibration is recorded
as a scalar-s limitation (spatially-varying s = future work, out of scope).

Usage:
    pixi run python scripts/diag_stage_b_localized_calibration.py
Writes stage_b["localized_calibration"] into the gate results JSON.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from sverdrup.methods.miost_windows import WindowPlan

RESULTS = Path("data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json")
MEAN_NC = Path("data/2021a_ssh_mapping_ose/ours/stage_b_mean_maps.nc")
VAR_NC = Path("data/2021a_ssh_mapping_ose/ours/stage_b_var_maps.nc")
SCOPE = Path("tests/validation/fixtures/stage_a_scope.json")
EPOCH = np.datetime64("2017-01-01")
LON_MID, LAT_MID = 300.0, 38.0


def localized_coverage(
    day: np.ndarray,
    lon: np.ndarray,
    lat: np.ndarray,
    resid: np.ndarray,
    var: np.ndarray,
    s: float,
) -> dict[str, dict[str, float]]:
    """Coverage/chi2 at frozen ``s`` per locality class (report-only).

    Args:
        day: Track-point days since 2017-01-01.
        lon: Longitudes [deg east].
        lat: Latitudes [deg north].
        resid: truth - mean at the track points.
        var: UN-inflated predicted variances at the track points.
        s: The FROZEN inflation factor (never refit here).

    Returns:
        class name -> {n, coverage_1sigma, reduced_chi2}; classes are
        blend/interior (production WindowPlan), quadrant_{SW,SE,NW,NE}
        (split at 300E / 38N), and month_MM.
    """
    plan = WindowPlan()
    blend = np.array([len(plan.covering(float(d))) == 2 for d in day])
    month = np.array(
        [(EPOCH + np.timedelta64(int(d), "D")).astype("datetime64[M]") for d in day]
    )
    classes: dict[str, np.ndarray] = {
        "blend": blend,
        "interior": ~blend,
        "quadrant_SW": (lon < LON_MID) & (lat < LAT_MID),
        "quadrant_SE": (lon >= LON_MID) & (lat < LAT_MID),
        "quadrant_NW": (lon < LON_MID) & (lat >= LAT_MID),
        "quadrant_NE": (lon >= LON_MID) & (lat >= LAT_MID),
    }
    for mm in np.unique(month):
        classes[f"month_{str(mm)[5:7]}"] = month == mm
    out: dict[str, dict[str, float]] = {}
    sd = np.sqrt(s * var)
    for name, mask in classes.items():
        if not mask.any():
            continue
        r, band, v = resid[mask], sd[mask], s * var[mask]
        out[name] = {
            "n": int(mask.sum()),
            "coverage_1sigma": float(np.mean(np.abs(r) <= band)),
            "reduced_chi2": float(np.mean(r**2 / v)),
        }
    return out


def main() -> None:
    """Interp the existing maps on the validation track, split, and record."""
    import sverdrup.validation.their_eval as te
    from sverdrup.validation.provenance_guard import assert_scored_not_assimilated

    cfg = json.loads(SCOPE.read_text())
    results = json.loads(RESULTS.read_text())
    s = float(results["stage_b"]["s_star"])  # FROZEN — never refit
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
    day = (np.asarray(t_a) - EPOCH) / np.timedelta64(1, "D")
    ok = np.isfinite(ssh) & np.isfinite(mu) & np.isfinite(var) & (var > 0)

    table = localized_coverage(
        day[ok], lon_a[ok], lat_a[ok], (ssh - mu)[ok], var[ok], s
    )
    results["stage_b"]["localized_calibration"] = {
        "semantics": (
            "REPORT-ONLY (owner protocol item 3, 2026-07-07): coverage at the "
            "FROZEN s* split by locality; NOT a bar. Severe local "
            "mis-calibration = recorded scalar-s limitation, future work."
        ),
        "s_frozen": s,
        "classes": table,
    }
    RESULTS.write_text(json.dumps(results, indent=2))
    print(f"frozen s* = {s:.4f}; {int(ok.sum()):,} points")
    print(f"{'class':14s} {'n':>7s} {'coverage':>9s} {'chi2':>7s}")
    for name, row in table.items():
        print(
            f"{name:14s} {row['n']:7d} {row['coverage_1sigma']:9.4f} "
            f"{row['reduced_chi2']:7.3f}"
        )


if __name__ == "__main__":
    main()
