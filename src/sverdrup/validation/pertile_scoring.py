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
from typing import Any

import numpy as np
import xarray as xr

from sverdrup.application.spatial_tiles import TileFrame
from sverdrup.eval.spectral import (
    UnresolvedScaleError,
    effective_resolution_lambda_x,
)
from sverdrup.validation.provenance_guard import assert_scored_not_assimilated
from sverdrup.validation.vendor import prepare_vendored_imports

# The published-leaderboard eval conventions (their_eval, v1.0 notebook).
_BIN_LON_STEP = 1.0
_BIN_LAT_STEP = 1.0
_BIN_TIME_STEP = "1D"
_TIME_MIN, _TIME_MAX = "2017-01-01", "2017-12-31"


@dataclass(frozen=True)
class TileScore:
    """One tile's validation score triple + support count.

    Owner pin 161: ``lambda_x`` is None when the map resolves no scale.
    That is a RECORDED ABSENCE, not a failure to score — and it never
    travels alone: ``lambda_x_absence`` carries the coherence evidence
    that justifies it (pin 160a), so a caught signal can never be read
    as a clean result.
    """

    mu: float
    sigma: float
    lambda_x: float | None
    n_scored_points: int
    lambda_x_absence: dict[str, Any] | None = None


def score_from_arrays(
    *,
    mu: float,
    sigma: float,
    n_scored_points: int,
    time_a: np.ndarray,
    lat_a: np.ndarray,
    lon_a: np.ndarray,
    ssh_a: np.ndarray,
    ssh_map_interp: np.ndarray,
) -> TileScore:
    """Assemble a :class:`TileScore`, recording an unresolved λx (pin 161).

    Three call sites already catch :class:`UnresolvedScaleError` and the
    tuner names it as what a degenerate map raises; ``score_tile`` was the
    outlier, and leg 3 died on it after nine windows had solved. This is
    the single place the signal becomes a record.

    ``ShortTrackError`` is deliberately NOT caught: too few samples to form
    one spectral segment is a question about the SPLIT, not about the map,
    and swallowing it would hide a track problem as a map property.

    Args:
        mu: their_eval mu at this tile core.
        sigma: their_eval sigma (the vendored RMS statistic).
        n_scored_points: Track points the triple was computed over.
        time_a: Along-track sample times.
        lat_a: Along-track latitudes.
        lon_a: Along-track longitudes.
        ssh_a: Observed along-track SSH (the reference signal).
        ssh_map_interp: The mapped field on the same track points.

    Returns:
        The tile score, with ``lambda_x`` None and ``lambda_x_absence``
        populated when the map resolves no scale.
    """
    try:
        lambda_x: float | None = effective_resolution_lambda_x(
            time_a, lat_a, lon_a, ssh_a, ssh_map_interp
        )
        absence: dict[str, Any] | None = None
    except UnresolvedScaleError as unresolved:
        lambda_x = None
        absence = {
            "reason": "UnresolvedScaleError",
            "message": str(unresolved),
            "evidence": unresolved.evidence,
            "meaning": (
                "the spectral coherence never crosses 0.5, so λx is UNDEFINED "
                "for this map — a RECORDED ABSENCE (owner pins 160a/161), not "
                "a scoring failure and not a value of zero"
            ),
            "pin": "161 — score_tile records the absence rather than crashing",
        }
    return TileScore(
        mu=float(mu),
        sigma=float(sigma),
        lambda_x=lambda_x,
        n_scored_points=int(n_scored_points),
        lambda_x_absence=absence,
    )


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
    return score_from_arrays(
        mu=float(mu),
        sigma=float(sigma),
        n_scored_points=int(np.asarray(ssh_a).size),
        time_a=time_a,
        lat_a=lat_a,
        lon_a=lon_a,
        ssh_a=ssh_a,
        ssh_map_interp=ssh_map_interp,
    )
