"""Drive 2017 single-tile OI over a sliding temporal window -> daily map NetCDF."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import numpy as np

from sverdrup.core.grid import GridSpec
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
from sverdrup.core.parameters import LatitudeField, ParameterProvider
from sverdrup.methods.kernel import (
    GaussianSpaceTimeDegrees,
    Kernel,
    Matern32SpaceTime,
)
from sverdrup.methods.registry import METHODS, SHIPPED
from sverdrup.validation.output_adapter import write_map
from sverdrup.validation.params import baseline_kernel

EPOCH = np.datetime64("2017-01-01")


def _oi_kernel_from_params(
    params: ParameterProvider, grid: GridSpec
) -> Matern32SpaceTime:
    """Build the explicit Matérn kernel ``OI.solve(kernel=None)`` would build from params.

    Used by the Phase-5 tuner path so the SAME tuned params drive both the per-trial
    map and acceptance — instead of ``run_challenge_map``'s default Gaussian
    ``baseline_kernel`` (which ignores the params). The OI parameter names live HERE in
    validation/, never in ``application/tuning/`` (method-agnosticism, Task-12 test 3).
    """
    return Matern32SpaceTime(
        variance=float(params.resolve("variance", grid)),
        length_scale=float(params.resolve("length_scale", grid)),
        time_scale=float(params.resolve("time_scale", grid)),
    )


def gaussian_kernel_from_params(
    params: ParameterProvider, grid: GridSpec | None
) -> Kernel:
    """Build the Gaussian degree-space kernel from params, dispatching on type.

    The Phase-10 seam (spec §2): resolves ``variance``, ``lx_deg`` (shared
    ``ly``, the signed 1:1 anisotropy), and ``time_scale``. All-scalar
    resolution constructs the STATIONARY ``GaussianSpaceTimeDegrees`` (same
    instance semantics as ``baseline_kernel()`` at the signed values — the
    byte-identical baseline gate); any ``LatitudeField`` routes the
    nonstationary Paciorek path. Like ``_oi_kernel_from_params``, OI's
    parameter names live HERE in validation/, never in application/tuning/.

    Args:
        params: Provider resolving ``variance``, ``lx_deg``, ``time_scale``.
        grid: Passed through to ``resolve`` (unused by scalar and latitude
            providers; ``None`` is fine in unit tests).

    Returns:
        The stationary Gaussian kernel, or (Task 4) the Paciorek kernel.

    Raises:
        NotImplementedError: For a field-valued resolution until Task 4 lands
            ``PaciorekGaussianDegrees``.
    """
    g = cast(GridSpec, grid)  # resolve ignores grid for these providers
    variance = params.resolve("variance", g)
    lx_deg = params.resolve("lx_deg", g)
    time_scale = params.resolve("time_scale", g)
    if any(isinstance(v, LatitudeField) for v in (variance, lx_deg, time_scale)):
        raise NotImplementedError(
            "nonstationary Gaussian path lands Task 4 (PaciorekGaussianDegrees)"
        )
    return GaussianSpaceTimeDegrees(
        variance=float(variance),
        lx_deg=float(lx_deg),
        ly_deg=float(lx_deg),  # shared lx=ly per spec §2
        time_scale=float(time_scale),
    )


def _resolve_oi_kernel(
    params: ParameterProvider,
    grid: GridSpec,
    oi_kernel_from_params: bool,
    oi_gaussian_kernel_from_params: bool,
) -> Kernel:
    """Pick the OI kernel source when no explicit kernel is given.

    Args:
        params: The method's parameter provider.
        grid: The output grid.
        oi_kernel_from_params: Matérn-from-params (the Phase-5 tuner path).
        oi_gaussian_kernel_from_params: Gaussian-degrees factory (Phase-10).

    Returns:
        The kernel per the requested flag, else the faithful baseline.

    Raises:
        ValueError: If both flags are set (ambiguous kernel source).
    """
    if oi_kernel_from_params and oi_gaussian_kernel_from_params:
        raise ValueError(
            "ambiguous OI kernel source: at most one of oi_kernel_from_params / "
            "oi_gaussian_kernel_from_params may be True (both False -> the "
            "faithful baseline_kernel)"
        )
    if oi_gaussian_kernel_from_params:
        return gaussian_kernel_from_params(params, grid)
    if oi_kernel_from_params:
        return _oi_kernel_from_params(params, grid)
    return baseline_kernel()


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


def _assimilated(obs: ObsWindow) -> tuple[str, ...] | None:
    """Mission set of the obs feeding a map, for typed file provenance."""
    if obs.mission is None:
        return None
    return tuple(sorted({str(m) for m in np.asarray(obs.mission)}))


def halo_obs(obs: ObsWindow, grid: GridSpec, halo_deg: float = 1.0) -> ObsWindow:
    """THE production obs framing: region derived from GRID NODES ± halo.

    The single source for spatial obs framing (owner order, 2026-07-07,
    after the third convention divergence this phase): the region is the
    grid's actual node extent plus ``halo_deg`` — NOT the nominal box. The
    production 0.2° grid overshoots the 33–43°N box to 43.2°N (a recorded
    quirk); a box-derived cut silently drops the 43.2–44.2°N obs sliver and
    breaks bit-reproducibility against acceptance maps.

    Args:
        obs: Observations to frame.
        grid: The output grid whose node extent defines the region.
        halo_deg: Halo beyond the node extent [degrees] (D7 default 1.0).

    Returns:
        The obs restricted to the node extent ± halo (order preserved).
    """
    lon_nodes, lat_nodes = grid._lonlat_nodes()
    c = obs.coords()
    keep = (
        (c[:, 0] >= lon_nodes.min() - halo_deg)
        & (c[:, 0] <= lon_nodes.max() + halo_deg)
        & (c[:, 1] >= lat_nodes.min() - halo_deg)
        & (c[:, 1] <= lat_nodes.max() + halo_deg)
    )
    return _subset(obs, keep)


def run_challenge_map(
    method_name: str,
    mapping_obs: ObsWindow,
    params: ParameterProvider,
    grid: GridSpec,
    temporal_half_window_days: float,
    output_days: list[float],
    dest: Path,
    kernel: Kernel | None = None,
    halo_deg: float = 1.0,
    mdt_grid: np.ndarray | None = None,
    oi_kernel_from_params: bool = False,
    oi_gaussian_kernel_from_params: bool = False,
    shipped: bool = False,
) -> Path:
    """Run the per-day single-tile solve for any method and write the stacked maps.

    For each output day the obs are restricted to a ``±temporal_half_window_days``
    window (so spin-up obs feed early-2017 days), the method's posterior mean is taken
    on ``grid``, and the stack is written in the challenge map schema. OI keeps the
    faithful BASELINE kernel seam; other methods (GMRF) solve with their own prior
    (``kernel`` is ignored). Same windowing / MDT reference-frame handling either way.

    Args:
        method_name: Key into ``methods.registry.METHODS`` (e.g. ``"oi"``, ``"gmrf"``).
        mapping_obs: All mapping-mission obs (spin-up included).
        params: The method's parameter provider.
        grid: The output grid over the box.
        temporal_half_window_days: Half-width of the obs influence window.
        output_days: Output day numbers (0.0 == 2017-01-01).
        dest: Output NetCDF path.
        kernel: Covariance kernel for OI; defaults to the faithful BASELINE
            ``GaussianSpaceTimeDegrees`` (gate-1 option (a)). Ignored for non-OI methods.
        halo_deg: Spatial halo (degrees) beyond the grid bbox to keep obs for;
            matches their ``read_obs`` filter (grid ± Lx, Lx = 1.0). Keeps the
            per-day solve tractable without changing the result (the Gaussian is
            ~0 well within the halo).
        mdt_grid: Optional ``(ny, nx)`` gridded MDT added to each day's SLA to
            form ``ssh = sla + mdt`` (the challenge reference frame). When None,
            the raw SLA map is written (SLA space).
        oi_kernel_from_params: When True and ``method_name == "oi"`` and no explicit
            ``kernel`` is given, build the Matérn kernel from ``params`` (the Phase-5
            tuner path) instead of the default Gaussian ``baseline_kernel``.
        oi_gaussian_kernel_from_params: When True and OI (no explicit kernel),
            build the Gaussian degree-space kernel from ``params`` via the
            type-dispatching factory (the Phase-10 path). Mutually exclusive
            with ``oi_kernel_from_params``.
        shipped: Resolve ``method_name`` via the ``SHIPPED`` product table
            instead of ``METHODS`` (registry role-split escape; used ONLY by
            shipped-product map regeneration — never by tuning paths).

    Returns:
        ``dest``.
    """
    method = cast(Any, (SHIPPED if shipped else METHODS)[method_name]())
    is_oi = method_name == "oi"
    if is_oi and kernel is None:
        kernel = _resolve_oi_kernel(
            params, grid, oi_kernel_from_params, oi_gaussian_kernel_from_params
        )
    region_obs = halo_obs(mapping_obs, grid, halo_deg)
    maps = []
    for day in output_days:
        win = _window(region_obs, day, temporal_half_window_days)
        if is_oi:
            dist = method.solve(win, grid, params, time_days=day, kernel=kernel)
        else:
            dist = method.solve(win, grid, params, time_days=day)
        sla = np.asarray(dist.mean)
        maps.append(sla if mdt_grid is None else sla + mdt_grid)
    ssh = np.stack(maps, axis=0)
    lon, lat = grid._lonlat_nodes()
    days_int = np.rint(np.asarray(output_days, dtype=float)).astype("int64")
    times = EPOCH + days_int * np.timedelta64(1, "D")
    return write_map(
        times,
        np.unique(lat),
        np.unique(lon),
        ssh,
        dest,
        assimilated_missions=_assimilated(mapping_obs),
    )


def run_mean_var_maps(
    method_name: str,
    mapping_obs: ObsWindow,
    params: ParameterProvider,
    grid: GridSpec,
    temporal_half_window_days: float,
    output_days: list[float],
    mean_dest: Path,
    var_dest: Path,
    kernel: Kernel | None = None,
    halo_deg: float = 1.0,
    mdt_grid: np.ndarray | None = None,
    oi_kernel_from_params: bool = False,
    oi_gaussian_kernel_from_params: bool = False,
) -> tuple[Path, Path]:
    """Produce daily mean AND marginal-variance maps from one solve pass per day.

    Same windowing / MDT handling as :func:`run_challenge_map`, but writes two
    challenge-schema NetCDFs: the SSH mean (``mean_dest``) and the marginal variance
    (``var_dest``, in SLA-variance space — MDT is a deterministic shift and does not
    change the variance). Used by the Phase-5 validation scorer, which interpolates
    BOTH onto the validation along-track (mean → residuals/λx, variance → coverage).

    Args:
        method_name: Key into ``methods.registry.METHODS``.
        mapping_obs: All mapping-mission obs (spin-up included).
        params: The method's parameter provider.
        grid: The output grid over the box.
        temporal_half_window_days: Half-width of the obs influence window.
        output_days: Output day numbers (0.0 == 2017-01-01).
        mean_dest: Output NetCDF path for the SSH mean map.
        var_dest: Output NetCDF path for the marginal-variance map.
        kernel: Explicit OI covariance kernel (see ``run_challenge_map``).
        halo_deg: Spatial halo (degrees) beyond the grid bbox to keep obs for.
        mdt_grid: Optional gridded MDT added to the mean (not the variance).
        oi_kernel_from_params: When True and OI, build the Matérn kernel from
            ``params`` rather than the default Gaussian ``baseline_kernel``.
        oi_gaussian_kernel_from_params: When True and OI, build the Gaussian
            degree-space kernel from ``params`` via the type-dispatching
            factory (Phase-10). Mutually exclusive with
            ``oi_kernel_from_params``.

    Returns:
        ``(mean_dest, var_dest)``.
    """
    method = cast(Any, METHODS[method_name]())
    is_oi = method_name == "oi"
    if is_oi and kernel is None:
        kernel = _resolve_oi_kernel(
            params, grid, oi_kernel_from_params, oi_gaussian_kernel_from_params
        )
    region_obs = halo_obs(mapping_obs, grid, halo_deg)
    means, variances = [], []
    for day in output_days:
        win = _window(region_obs, day, temporal_half_window_days)
        if is_oi:
            dist = method.solve(win, grid, params, time_days=day, kernel=kernel)
        else:
            dist = method.solve(win, grid, params, time_days=day)
        sla = np.asarray(dist.mean)
        means.append(sla if mdt_grid is None else sla + mdt_grid)
        variances.append(np.asarray(dist.marginal_variance()))
    mean_ssh = np.stack(means, axis=0)
    var_ssh = np.stack(variances, axis=0)
    lon, lat = grid._lonlat_nodes()
    days_int = np.rint(np.asarray(output_days, dtype=float)).astype("int64")
    times = EPOCH + days_int * np.timedelta64(1, "D")
    assimilated = _assimilated(mapping_obs)
    write_map(
        times,
        np.unique(lat),
        np.unique(lon),
        mean_ssh,
        mean_dest,
        assimilated_missions=assimilated,
    )
    write_map(
        times,
        np.unique(lat),
        np.unique(lon),
        var_ssh,
        var_dest,
        assimilated_missions=assimilated,
    )
    return mean_dest, var_dest


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
    """OI single-tile challenge runner (delegates to ``run_challenge_map``)."""
    return run_challenge_map(
        "oi",
        mapping_obs,
        params,
        grid,
        temporal_half_window_days,
        output_days,
        dest,
        kernel=kernel,
        halo_deg=halo_deg,
        mdt_grid=mdt_grid,
    )
