"""Shared effective-resolution (λx) computation: one algorithm, two call sites.

Both ``validation.their_eval`` (CryoSat-2 locked test) and ``eval.resolution``
(blocked validation split) call ``effective_resolution_lambda_x`` so the per-trial
λx and the acceptance λx are the SAME algorithm (Phase-5 invariant 10). Segment
preparation lives here, so the only thing that varies between the two call sites is
the track itself.

This module owns its own headless vendor-import prep (``sys.path`` + the Agg
matplotlib backend + the unused ``hvplot`` stub that ``src.mod_plot`` imports at
module top). It deliberately does NOT import ``validation.their_eval`` — that would
be circular (``their_eval`` imports this helper) and would couple the per-trial
path to the locked-test harness. The pyinterp compat shim is unnecessary here: the
spectral path (``compute_spectral_scores`` + ``find_wavelength_05_crossing``) never
touches pyinterp.
"""

from __future__ import annotations

import sys
import tempfile
import types
from pathlib import Path

import numpy as np

# Spectral parameters — the vendored leaderboard definition (their_eval.py).
_VENDOR = Path(__file__).resolve().parents[3] / "vendor" / "2021a_SSH_mapping_OSE"
_DELTA_T = 0.9434  # s — CryoSat-2 along-track sampling interval
_VELOCITY = 6.77  # km/s — satellite ground-track speed
_DELTA_X = _VELOCITY * _DELTA_T  # km — along-track spatial sampling
_LENGTH_SCALE = 1000.0  # km — spectral segment length


class ShortTrackError(ValueError):
    """Raised when an along-track segment is too short for the spectral computation."""


def _ensure_vendor_importable() -> None:
    """Make the vendored spectral modules importable in a headless env.

    Idempotent: puts the submodule root on ``sys.path``, forces the non-interactive
    matplotlib backend, and stubs the unused ``hvplot`` import that ``src.mod_plot``
    performs at module top (it is only used by interactive plotters, never by
    ``find_wavelength_05_crossing``). Mirrors the subset of
    ``their_eval._prepare_imports`` the spectral path needs, without importing it.
    """
    if str(_VENDOR) not in sys.path:
        sys.path.insert(0, str(_VENDOR))
    import matplotlib

    matplotlib.use("Agg", force=True)
    if "hvplot" not in sys.modules:
        stub = types.ModuleType("hvplot")
        xr_stub = types.ModuleType("hvplot.xarray")
        stub.xarray = xr_stub  # type: ignore[attr-defined]
        sys.modules["hvplot"] = stub
        sys.modules["hvplot.xarray"] = xr_stub


def effective_resolution_lambda_x(
    time: np.ndarray,
    lat: np.ndarray,
    lon: np.ndarray,
    ssh_track: np.ndarray,
    ssh_map_interp: np.ndarray,
) -> float:
    """Return the effective resolution λx (km) from raw along-track arrays.

    Args:
        time: Along-track sample times (any monotone numeric/datetime array the
            vendored spectral code accepts).
        lat: Along-track latitudes.
        lon: Along-track longitudes.
        ssh_track: Observed along-track SSH/SLA values (the reference signal).
        ssh_map_interp: The mapped field interpolated onto the same track points.

    Returns:
        λx in km (the 0.5 spectral-coherence crossing wavelength).

    Raises:
        ShortTrackError: If the track cannot support one ``_LENGTH_SCALE`` segment.
    """
    n = int(np.asarray(ssh_track).size)
    samples_per_segment = int(_LENGTH_SCALE / _DELTA_X)
    if n < samples_per_segment:
        raise ShortTrackError(
            f"track has {n} samples; need >= {samples_per_segment} for a "
            f"{_LENGTH_SCALE} km spectral segment (Δx={_DELTA_X:.3f} km). "
            "Widen/rotate the validation split."
        )
    _ensure_vendor_importable()
    from src.mod_plot import find_wavelength_05_crossing
    from src.mod_spectral import compute_spectral_scores

    with tempfile.TemporaryDirectory() as td:
        psd_file = Path(td) / "psd.nc"
        compute_spectral_scores(
            np.asarray(time),
            np.asarray(lat),
            np.asarray(lon),
            np.asarray(ssh_track, dtype="float64"),
            np.asarray(ssh_map_interp, dtype="float64"),
            _LENGTH_SCALE,
            _DELTA_X,
            _DELTA_T,
            str(psd_file),
        )
        return float(find_wavelength_05_crossing(str(psd_file)))
