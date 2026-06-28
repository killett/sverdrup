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


def _diag_variance(obs: ObsWindow) -> np.ndarray:
    """Return the per-obs error variances without densifying the error matrix."""
    em = obs.error_model
    if isinstance(em, DiagonalErrorModel):
        return np.asarray(em.variance, dtype=float)
    # Non-diagonal models are small by construction; fall back to the dense diag.
    return np.asarray(em.as_matrix(len(obs)).diagonal(), dtype=float)


def _subset(obs: ObsWindow, mask: np.ndarray) -> ObsWindow:
    """Return the obs selected by a boolean ``mask`` (diagonal error preserved)."""
    c = obs.coords()
    var = _diag_variance(obs)[mask]
    mission = None if obs.mission is None else np.asarray(obs.mission)[mask]
    return ObsWindow.from_arrays(
        c[mask, 0],
        c[mask, 1],
        c[mask, 2],
        obs.values()[mask],
        DiagonalErrorModel(var),
        mission=mission,
    )


def _window(obs: ObsWindow, day: float, half: float) -> ObsWindow:
    """Subset ``obs`` to those within ``±half`` days of ``day``."""
    return _subset(obs, np.abs(obs.coords()[:, 2] - day) <= half)


def run_year(
    mapping_obs: ObsWindow,
    params: ParameterProvider,
    grid: GridSpec,
    temporal_half_window_days: float,
    output_days: list[float],
    dest: Path,
    kernel: Kernel | None = None,
    halo_deg: float = 1.0,
    mdt_grid: np.ndarray | None = None,
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
        halo_deg: Spatial halo (degrees) beyond the grid bbox to keep obs for;
            matches their ``read_obs`` filter (grid ± Lx, Lx = 1.0). Keeps the
            per-day solve tractable without changing the result (the Gaussian is
            ~0 well within the halo).
        mdt_grid: Optional ``(ny, nx)`` gridded MDT added to each day's OI SLA to
            form ``ssh = sla + mdt`` (the challenge reference frame). When None,
            the raw SLA map is written (SLA space).

    Returns:
        ``dest``.
    """
    if kernel is None:
        kernel = baseline_kernel()
    lon_nodes, lat_nodes = grid._lonlat_nodes()
    c = mapping_obs.coords()
    in_region = (
        (c[:, 0] >= lon_nodes.min() - halo_deg)
        & (c[:, 0] <= lon_nodes.max() + halo_deg)
        & (c[:, 1] >= lat_nodes.min() - halo_deg)
        & (c[:, 1] <= lat_nodes.max() + halo_deg)
    )
    region_obs = _subset(mapping_obs, in_region)
    oi = OptimalInterpolation()
    maps = []
    for day in output_days:
        win = _window(region_obs, day, temporal_half_window_days)
        dist = oi.solve(win, grid, params, time_days=day, kernel=kernel)
        sla = np.asarray(dist.mean)
        maps.append(sla if mdt_grid is None else sla + mdt_grid)
    ssh = np.stack(maps, axis=0)
    lon, lat = grid._lonlat_nodes()
    days_int = np.rint(np.asarray(output_days, dtype=float)).astype("int64")
    times = EPOCH + days_int * np.timedelta64(1, "D")
    return write_map(times, np.unique(lat), np.unique(lon), ssh, dest)
