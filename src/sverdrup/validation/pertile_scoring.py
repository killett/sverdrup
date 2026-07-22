"""Per-tile validation scorer (phase-14 0d-3).

The box scoring path generalized to a ``TileFrame``: track extraction is
CORE-ONLY (the blend overlap is never double-scored — each track point is
scored by exactly the tile that owns it), the µ/σ/λx machinery is the
EXISTING vendored challenge sequence (imported, unchanged), and every call
goes through the provenance guard with the map's own assimilated list.

λx note: the spectral helper runs the box convention unchanged (identity
with the signed path — the gate-5 requirement). The tile-extent band value
WILL be carried in the Task-11 instrument config; parameterizing the helper
happens with its first non-anchor consumer (Stage 1), never before the
anchor identity is pinned.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import xarray as xr

from sverdrup.application.spatial_tiles import TileFrame
from sverdrup.eval.spectral import effective_resolution_lambda_x
from sverdrup.validation.provenance_guard import assert_scored_not_assimilated
from sverdrup.validation.vendor import prepare_vendored_imports

# The published-leaderboard eval conventions (their_eval, v1.0 notebook).
_BIN_LON_STEP = 1.0
_BIN_LAT_STEP = 1.0
_BIN_TIME_STEP = "1D"
_TIME_MIN, _TIME_MAX = "2017-01-01", "2017-12-31"


@dataclass(frozen=True)
class TileScore:
    """One tile's validation score triple + support count."""

    mu: float
    sigma: float
    lambda_x: float
    n_scored_points: int


def extract_core_track(
    frame: TileFrame,
    track_path: Path,
    time_min: str = _TIME_MIN,
    time_max: str = _TIME_MAX,
) -> xr.Dataset:
    """The validation track restricted to ``frame.core`` — CORE ONLY.

    Track points in the blend overlap belong to the neighboring tile that
    owns them; scoring them here would double-score the overlap. Bounds are
    inclusive (the vendored ``read_l3_dataset`` convention, matching BBox).

    Args:
        frame: The tile frame (its ``core`` is the extraction region).
        track_path: The along-track L3 NetCDF.
        time_min: Inclusive ISO start date.
        time_max: Inclusive ISO end date (the vendored slice convention).

    Returns:
        The clipped xarray dataset (vendored schema).
    """
    prepare_vendored_imports()
    from src.mod_inout import read_l3_dataset  # noqa: PLC0415

    ds: xr.Dataset = read_l3_dataset(
        str(track_path),
        lon_min=frame.core.lon_min,
        lon_max=frame.core.lon_max,
        lat_min=frame.core.lat_min,
        lat_max=frame.core.lat_max,
        time_min=time_min,
        time_max=time_max,
    )
    return ds


def score_tile(
    frame: TileFrame,
    map_path: Path,
    track_path: Path,
    time_min: str = _TIME_MIN,
    time_max: str = _TIME_MAX,
) -> TileScore:
    """Score a gridded map against the validation track WITHIN a tile core.

    The provenance guard runs FIRST with the map's own assimilated list
    (per-tile provenance rows); then the vendored interpolation, RMSE
    binning, and the shared spectral helper run unchanged on the core-only
    track.

    Args:
        frame: The tile frame; extraction and scoring are core-only.
        map_path: The tile's gridded map (challenge L4 schema, provenance
            attributes from ``write_map``).
        track_path: The validation along-track L3 NetCDF.
        time_min: Inclusive ISO start date.
        time_max: Inclusive ISO end date.

    Returns:
        The tile's ``(µ, σ, λx)`` + the count of points that survived the
        vendored interpolation (post NaN/inset filtering — the number the
        scores are actually computed over).

    Raises:
        TrainScoreLeakError: If the track's mission is in the map's
            assimilated list (or provenance cannot prove separation).
    """
    assert_scored_not_assimilated(map_path, track_path)
    ds_track = extract_core_track(frame, track_path, time_min, time_max)
    prepare_vendored_imports()
    from src.mod_interp import interp_on_alongtrack  # noqa: PLC0415
    from src.mod_stats import compute_stats  # noqa: PLC0415

    time_a, lat_a, lon_a, ssh_a, ssh_map_interp = interp_on_alongtrack(
        str(map_path),
        ds_track,
        lon_min=frame.core.lon_min,
        lon_max=frame.core.lon_max,
        lat_min=frame.core.lat_min,
        lat_max=frame.core.lat_max,
        time_min=time_min,
        time_max=time_max,
        is_circle=False,
    )
    if np.asarray(ssh_a).size == 0:
        raise ValueError(
            f"no validation track points survive in tile core {frame.core} "
            f"for {track_path} — an empty tile must be handled by the "
            "caller, never scored to a masked/NaN triple"
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
    lambda_x = effective_resolution_lambda_x(
        time_a, lat_a, lon_a, ssh_a, ssh_map_interp
    )
    return TileScore(
        mu=float(mu),
        sigma=float(sigma),
        lambda_x=float(lambda_x),
        n_scored_points=int(np.asarray(ssh_a).size),
    )
