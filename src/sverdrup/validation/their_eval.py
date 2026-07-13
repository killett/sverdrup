"""Drive the challenge's own scoring functions (ground truth) on a map + track.

This is a thin wrapper over the vendored ``2021a_SSH_mapping_OSE`` code
(``vendor/2021a_SSH_mapping_OSE``, pinned to the v1.0 leaderboard commit). It
reproduces the exact sequence of ``notebooks/example_eval_baseline.ipynb``:

1. ``src.mod_inout.read_l3_dataset`` — load the withheld Cryosat-2 track.
2. ``src.mod_interp.interp_on_alongtrack`` — interpolate the gridded map onto
   the track (SSH reference = ``sla_unfiltered + mdt - lwe``).
3. ``src.mod_stats.compute_stats`` — area-binned RMSE timeseries -> (mu, sigma).
4. ``src.mod_spectral.compute_spectral_scores`` -> PSD NetCDF.
5. ``src.mod_plot.find_wavelength_05_crossing`` -> lambda_x (effective resolution).

The eval-region box, time window, binning and spectral parameters below are
transcribed verbatim from that notebook; they *are* the published-leaderboard
eval definition, so ``score`` takes only the two file paths.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from sverdrup.eval.spectral import effective_resolution_lambda_x
from sverdrup.validation.provenance_guard import assert_scored_not_assimilated
from sverdrup.validation.vendor import prepare_vendored_imports

# --- eval definition (notebooks/example_eval_baseline.ipynb, v1.0) ---
_LON_MIN, _LON_MAX = 295.0, 305.0
_LAT_MIN, _LAT_MAX = 33.0, 43.0
_TIME_MIN, _TIME_MAX = "2017-01-01", "2017-12-31"
_BIN_LON_STEP = 1.0
_BIN_LAT_STEP = 1.0
_BIN_TIME_STEP = "1D"
_DELTA_T = 0.9434  # s — Cryosat-2 along-track sampling interval
_VELOCITY = 6.77  # km/s — satellite ground-track speed
_DELTA_X = _VELOCITY * _DELTA_T  # km — along-track spatial sampling
_LENGTH_SCALE = 1000.0  # km — spectral segment length


def _prepare_imports() -> None:
    """Make the vendored challenge package importable in a headless env.

    Thin delegate to :func:`sverdrup.validation.vendor.prepare_vendored_imports`
    — the full path/plumbing logic lives there so that callers (including the
    calibration harness) can reach it without importing this module.
    """
    prepare_vendored_imports()


def score(map_path: Path, track_path: Path) -> tuple[float, float, float]:
    """Score a gridded SSH map against the withheld track using THEIR code.

    Args:
        map_path: Path to a gridded map NetCDF in the challenge L4 schema
            (coords ``lon``/``lat``/``time``, variable ``ssh``).
        track_path: Path to the withheld Cryosat-2 along-track L3 NetCDF.

    Returns:
        ``(mu_rmse, sigma_rmse, lambda_x_km)`` as computed by the challenge's
        own RMSE-based and spectral scoring functions.

    Raises:
        TrainScoreLeakError: If the map's typed provenance shows the track's
            mission was assimilated (Task-21 train/score guard).
    """
    assert_scored_not_assimilated(map_path, track_path)
    _prepare_imports()
    from src.mod_inout import read_l3_dataset
    from src.mod_interp import interp_on_alongtrack
    from src.mod_stats import compute_stats

    ds_alongtrack = read_l3_dataset(
        str(track_path),
        lon_min=_LON_MIN,
        lon_max=_LON_MAX,
        lat_min=_LAT_MIN,
        lat_max=_LAT_MAX,
        time_min=_TIME_MIN,
        time_max=_TIME_MAX,
    )
    time_a, lat_a, lon_a, ssh_a, ssh_map_interp = interp_on_alongtrack(
        str(map_path),
        ds_alongtrack,
        lon_min=_LON_MIN,
        lon_max=_LON_MAX,
        lat_min=_LAT_MIN,
        lat_max=_LAT_MAX,
        time_min=_TIME_MIN,
        time_max=_TIME_MAX,
        is_circle=False,
    )

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        mu, sigma = compute_stats(
            time_a,
            lat_a,
            lon_a,
            ssh_a,
            ssh_map_interp,
            _BIN_LON_STEP,
            _BIN_LAT_STEP,
            _BIN_TIME_STEP,
            str(tmp / "stat.nc"),
            str(tmp / "stat_timeseries.nc"),
        )
    # λx goes through the shared helper (Phase-5 invariant 10): the per-trial and
    # acceptance paths are the SAME algorithm. The helper manages its own temp dir
    # and segment preparation; we pass raw along-track arrays only.
    lambda_x = effective_resolution_lambda_x(
        time_a, lat_a, lon_a, ssh_a, ssh_map_interp
    )

    return float(mu), float(sigma), lambda_x
