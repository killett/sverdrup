"""Per-tile coherence diagnostic for the Stage-1 diverse legs.

Read-only. Reproduces :func:`score_tile`'s path up to the coherence array on
the PERSISTED maps — no solve, no write, no evidence touched.

Why it exists: leg 3 (equatorial) died in scoring on
``UnresolvedScaleError: map resolves no scale`` after all nine windows had
solved. That error is a DEFINED signal (``_coherence_guard`` raises it in
place of a cryptic vendored ``interp1d`` out-of-range error), and it fires on
BOTH degenerate sides — a map that never reaches 0.5 coherence, and one that
never falls to it. Which side decides whether the tile produced a real
result or hit a defect, and no log line answers that. This does.

Usage::

    pixi run python scripts/diag_stage1_coherence.py
"""

from __future__ import annotations

import importlib.util
import pathlib
import tempfile
from types import ModuleType
from typing import Any

import numpy as np
import xarray as xr

TILES = ("kuroshio", "southern", "equatorial", "quiet_gyre")


def _stage1_module() -> ModuleType:
    """Load the Stage-1 runner as a module (it is a script, not a package)."""
    spec = importlib.util.spec_from_file_location(
        "phase14_stage1_run", pathlib.Path(__file__).with_name("phase14_stage1_run.py")
    )
    if spec is None or spec.loader is None:  # pragma: no cover - import plumbing
        raise RuntimeError("cannot load phase14_stage1_run.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def tile_coherence(tile: str) -> dict[str, Any] | None:
    """Coherence and residual statistics for one tile's persisted map.

    Args:
        tile: Tile name.

    Returns:
        A row of statistics, or None when the tile's artifacts are absent.
    """
    from sverdrup.eval.spectral import (  # noqa: PLC0415
        _DELTA_T,
        _DELTA_X,
        _LENGTH_SCALE,
        _ensure_vendor_importable,
    )
    from sverdrup.validation.pertile_scoring import (  # noqa: PLC0415
        extract_core_track,
    )
    from sverdrup.validation.vendor import (  # noqa: PLC0415
        prepare_vendored_imports,
    )

    mod = _stage1_module()
    mean_map = mod.tile_mean_map(tile)
    track = mod.STAGE1_DIR / f"dt_{tile}_j3_phy_l3_2017_stage1.nc"
    if not (mean_map.exists() and track.exists()):
        return None

    frame, _grid, _framed, _cfg = mod._tile_framed_obs(tile)  # noqa: SLF001
    ds_track = extract_core_track(
        frame, track, mod.VALIDATION_TIME_MIN, mod.VALIDATION_TIME_MAX
    )
    prepare_vendored_imports()
    _ensure_vendor_importable()
    from src.mod_interp import interp_on_alongtrack  # noqa: PLC0415
    from src.mod_spectral import compute_spectral_scores  # noqa: PLC0415

    time_a, lat_a, lon_a, ssh_a, ssh_map = interp_on_alongtrack(
        str(mean_map),
        ds_track,
        lon_min=frame.core.lon_min,
        lon_max=frame.core.lon_max,
        lat_min=frame.core.lat_min,
        lat_max=frame.core.lat_max,
        time_min=mod.VALIDATION_TIME_MIN,
        time_max=mod.VALIDATION_TIME_MAX,
        is_circle=False,
    )
    track_ssh = np.asarray(ssh_a, dtype="float64")
    map_ssh = np.asarray(ssh_map, dtype="float64")

    with tempfile.TemporaryDirectory() as td:
        psd_file = pathlib.Path(td) / "psd.nc"
        compute_spectral_scores(
            np.asarray(time_a),
            np.asarray(lat_a),
            np.asarray(lon_a),
            track_ssh,
            map_ssh,
            _LENGTH_SCALE,
            _DELTA_X,
            _DELTA_T,
            str(psd_file),
        )
        with xr.open_dataset(str(psd_file)) as ds:
            coherence = (1.0 - ds.psd_diff / ds.psd_ref).to_numpy()
            ratio = float(np.nanmedian(ds.psd_diff.to_numpy() / ds.psd_ref.to_numpy()))

    coh_min = float(np.nanmin(coherence))
    coh_max = float(np.nanmax(coherence))
    track_std = float(np.nanstd(track_ssh))
    residual_std = float(np.nanstd(track_ssh - map_ssh))
    return {
        "tile": tile,
        "lat_min": float(np.nanmin(lat_a)),
        "lat_max": float(np.nanmax(lat_a)),
        "track_std": track_std,
        "map_std": float(np.nanstd(map_ssh)),
        "bias": float(np.nanmean(map_ssh) - np.nanmean(track_ssh)),
        "residual_std": residual_std,
        "residual_over_track": residual_std / track_std if track_std else float("nan"),
        "coherence_min": coh_min,
        "coherence_max": coh_max,
        "psd_diff_over_ref_median": ratio,
        # The guard's own condition, restated so the reader sees WHY.
        "lambda_x": "resolved" if coh_min <= 0.5 <= coh_max else "UNRESOLVED",
    }


def main() -> None:
    """Print the per-tile coherence table."""
    header = (
        f"{'tile':<12}{'lat span':>16}{'trk std':>9}{'map std':>9}{'bias':>8}"
        f"{'res std':>9}{'res/trk':>9}{'coh max':>9}{'diff/ref':>10}  lambda_x"
    )
    print(header)
    for tile in TILES:
        row = tile_coherence(tile)
        if row is None:
            print(f"{tile:<12}  (artifacts absent — leg not run)")
            continue
        span = f"{row['lat_min']:+.1f}..{row['lat_max']:+.1f}"
        print(
            f"{row['tile']:<12}{span:>16}{row['track_std']:>9.4f}"
            f"{row['map_std']:>9.4f}{row['bias']:>8.3f}{row['residual_std']:>9.4f}"
            f"{row['residual_over_track']:>9.2f}{row['coherence_max']:>9.3f}"
            f"{row['psd_diff_over_ref_median']:>10.4f}  {row['lambda_x']}"
        )


if __name__ == "__main__":
    main()
