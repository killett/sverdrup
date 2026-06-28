"""Drive 2017 single-tile OI over a sliding temporal window -> daily map NetCDF."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from sverdrup.core.grid import GridSpec
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
from sverdrup.core.parameters import ParameterProvider
from sverdrup.methods.kernel import Kernel
from sverdrup.methods.oi import OptimalInterpolation
from sverdrup.validation.output_adapter import write_map
from sverdrup.validation.params import baseline_kernel

EPOCH = np.datetime64("2017-01-01")


def _window(obs: ObsWindow, day: float, half: float) -> ObsWindow:
    """Subset ``obs`` to those within ``±half`` days of ``day``."""
    c = obs.coords()
    keep = np.abs(c[:, 2] - day) <= half
    var = np.asarray(obs.error_model.as_matrix(len(obs)).diagonal())[keep]
    mission = None if obs.mission is None else np.asarray(obs.mission)[keep]
    return ObsWindow.from_arrays(
        c[keep, 0],
        c[keep, 1],
        c[keep, 2],
        obs.values()[keep],
        DiagonalErrorModel(var),
        mission=mission,
    )


def run_year(
    mapping_obs: ObsWindow,
    params: ParameterProvider,
    grid: GridSpec,
    temporal_half_window_days: float,
    output_days: list[float],
    dest: Path,
    kernel: Kernel | None = None,
) -> Path:
    """Run OI for each output day and write the stacked daily maps.

    For each output day the obs are restricted to a ``±temporal_half_window_days``
    window (so spin-up obs feed early-2017 days), the OI posterior mean is taken
    on ``grid``, and the stack is written in the challenge map schema.

    Args:
        mapping_obs: All mapping-mission obs (spin-up included).
        params: The baseline OI parameter provider (used only if ``kernel`` is
            None and the Matern default is built).
        grid: The output grid over the box.
        temporal_half_window_days: Half-width of the obs influence window.
        output_days: Output day numbers (0.0 == 2017-01-01).
        dest: Output NetCDF path.
        kernel: Covariance kernel; defaults to the faithful BASELINE
            ``GaussianSpaceTimeDegrees`` (gate-1 option (a)).

    Returns:
        ``dest``.
    """
    if kernel is None:
        kernel = baseline_kernel()
    oi = OptimalInterpolation()
    maps = []
    for day in output_days:
        win = _window(mapping_obs, day, temporal_half_window_days)
        dist = oi.solve(win, grid, params, time_days=day, kernel=kernel)
        maps.append(np.asarray(dist.mean))
    ssh = np.stack(maps, axis=0)
    lon, lat = grid._lonlat_nodes()
    days_int = np.rint(np.asarray(output_days, dtype=float)).astype("int64")
    times = EPOCH + days_int * np.timedelta64(1, "D")
    return write_map(times, np.unique(lat), np.unique(lon), ssh, dest)
