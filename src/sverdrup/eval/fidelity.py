"""Descriptive-only wavenumber-slope sanity evaluator (spec §5; plan Task 4)."""

from __future__ import annotations

from typing import Any, cast

import numpy as np

from sverdrup.core.evaluation import ContextKey, EvalContext, MetricScope
from sverdrup.eval.map_spectrum import (
    PlaneGrid,
    detrend,
    power2d,
    radial_hann,
    ring_spectrum,
)
from sverdrup.eval.phase11_constants import (
    BAND_HI_CAP_KM,
    BAND_LO_FLOOR_KM,
    MIN_BIN_INDEX,
)


def _wls_slope(
    log_k: np.ndarray, log_e: np.ndarray, weights: np.ndarray
) -> tuple[float, float]:
    """Weighted least-squares slope of ``log_e`` on ``log_k``.

    Args:
        log_k: Abscissa (log10 wavenumber).
        log_e: Ordinate (log10 ring-integrated power).
        weights: Per-point weights (mode counts).

    Returns:
        ``(slope, slope_se)`` with the SE from the weighted residual variance.
    """
    x = np.column_stack([np.ones_like(log_k), log_k])
    w = np.asarray(weights, dtype=float)
    xtwx = x.T @ (w[:, None] * x)
    xtwy = x.T @ (w * log_e)
    beta = np.linalg.solve(xtwx, xtwy)
    resid = log_e - x @ beta
    dof = max(log_k.size - 2, 1)
    s2 = float((w * resid**2).sum() / w.sum() * log_k.size / dof)
    cov = np.linalg.inv(xtwx) * s2
    return float(beta[1]), float(np.sqrt(cov[1, 1]))


def _obs_slope_1d(
    bag: dict[str, np.ndarray], lo_km: float, hi_km: float, phi0: float
) -> float | None:
    """Median per-pass along-track 1-D log-log slope within the band.

    Passes come from the standing gap-split convention
    (:func:`sverdrup.application.orbit_geometry.split_passes`); each pass is
    resampled onto a uniform along-track km grid, linearly detrended, Hann
    windowed, and periodogrammed.

    Args:
        bag: WITHHELD_OBS carrying ``time``/``lat``/``lon``/``values`` arrays.
        lo_km: Band lower wavelength edge (km).
        hi_km: Band upper wavelength edge (km).
        phi0: Reference latitude for the km plane (degrees).

    The fit is POOLED: every pass contributes its in-band (log f, log PSD)
    periodogram points to ONE log-log fit — a per-pass fit over the narrow
    pinned band (a factor ~2.2 in frequency) has enormous variance, while the
    pooled estimator's per-point chi-square scatter is a constant log offset
    that cannot tilt the slope.

    Returns:
        Pooled slope, or ``None`` when fewer than 8 in-band points exist.
    """
    # Deliberately local: application imports eval, so a module-top import of
    # sverdrup.application.orbit_geometry here would create an import cycle.
    from sverdrup.application.orbit_geometry import KM_PER_DEG, split_passes

    lon = np.asarray(bag["lon"], dtype=float)
    lat = np.asarray(bag["lat"], dtype=float)
    time = np.asarray(bag["time"], dtype=float)
    values = np.asarray(bag["values"], dtype=float)
    order = np.argsort(time, kind="stable")
    lon, lat, time, values = lon[order], lat[order], time[order], values[order]
    cph = np.cos(np.deg2rad(phi0))
    log_f: list[np.ndarray] = []
    log_p: list[np.ndarray] = []
    for p_lon, p_lat, p_time, _asc in split_passes(lon, lat, time):
        idx = np.searchsorted(time, p_time[0])
        vals = values[idx : idx + p_lon.size]
        if vals.size < 32:
            continue
        dx = np.diff(p_lon) * KM_PER_DEG * cph
        dy = np.diff(p_lat) * KM_PER_DEG
        s = np.concatenate([[0.0], np.cumsum(np.hypot(dx, dy))])
        ds = float(np.median(np.diff(s)))
        if ds <= 0:
            continue
        s_uniform = np.arange(0.0, s[-1], ds)
        if s_uniform.size < 32:
            continue
        v = np.interp(s_uniform, s, vals)
        coef = np.polyfit(s_uniform, v, 1)
        v = v - np.polyval(coef, s_uniform)
        v = v * np.hanning(v.size)
        psd = np.abs(np.fft.rfft(v)) ** 2
        freq = np.fft.rfftfreq(v.size, d=ds)
        band = (freq >= 1.0 / hi_km) & (freq <= 1.0 / lo_km) & (psd > 0)
        if int(band.sum()) < 2:
            continue
        log_f.append(np.log10(freq[band]))
        log_p.append(np.log10(psd[band]))
    if not log_f:
        return None
    lf = np.concatenate(log_f)
    lp = np.concatenate(log_p)
    if lf.size < 8:
        return None
    return float(np.polyfit(lf, lp, 1)[0])


class SpectralFidelity:
    """Descriptive-only wavenumber-slope sanity (spec §5). No verdict semantics.

    Band rule (pinned): lower edge ``max(100, 3 * dy_km)`` km; upper edge
    ``min(300, Lx / MIN_BIN_INDEX)`` km with Lx the zonal BOX extent — the
    mainlobe-clearance rule (on the real grid: [100, 219] km, clearance
    binds, the 300 cap never does).

    Wedge exclusion masks arrive via ``result["track_wedge_masks"]``
    (builder-computed, Task 6) so fidelity does NOT read ORBIT_GEOMETRY at
    all — the declaration stays honest with required=∅,
    optional={WITHHELD_OBS}. Masks absent is a VISIBLY degraded estimand
    (owner plan-review pin 1a): the slope is still computed and the row
    carries ``wedge_exclusion: 0.0``; present -> ``1.0``.

    Guards match GroundTrack: mean maps only (Phase-8 theorem), NaN refused.
    """

    name = "spectral_fidelity"
    required_context: frozenset[ContextKey] = frozenset()
    optional_context = frozenset({ContextKey.WITHHELD_OBS})
    metric_scope = MetricScope.POINTWISE

    def band_km(self, grid: PlaneGrid) -> tuple[float, float]:
        """Pinned fidelity wavelength band for ``grid``.

        Args:
            grid: The map plane grid.

        Returns:
            ``(lo_km, hi_km)`` band edges in km.
        """
        lo = max(BAND_LO_FLOOR_KM, 3.0 * grid.dy_km)
        hi = min(BAND_HI_CAP_KM, grid.extent_x_km / MIN_BIN_INDEX)
        return float(lo), float(hi)

    def evaluate(self, result: object, context: EvalContext) -> dict[str, float]:
        """Fit the in-band ring-spectrum slope of the mean maps.

        Args:
            result: Mapping with ``fields`` (n_days, ny, nx), ``grid_lon``,
                ``grid_lat``, ``field_kind``, optionally
                ``track_wedge_masks``.
            context: Optionally carries WITHHELD_OBS with track arrays for
                the 1-D companion slope.

        Returns:
            ``spec_slope``, ``spec_slope_wls_se``, ``spec_slope_day_median``,
            ``spec_slope_day_iqr``, ``spec_n_modes_min``, ``wedge_exclusion``
            (0/1), and ``spec_slope_obs_1d`` when obs arrays are available.

        Raises:
            ValueError: On non-mean ``field_kind`` or NaN in the box.
        """
        r = cast(Any, result)
        if r.get("field_kind") != "mean":
            raise ValueError(
                "SpectralFidelity scores mean maps ONLY (Phase-8 theorem, same "
                f"guard as GroundTrack); got field_kind={r.get('field_kind')!r}"
            )
        maps = np.asarray(r["fields"], dtype=float)
        if maps.ndim == 2:
            maps = maps[None]
        if np.isnan(maps).any():
            raise ValueError("NaN in box — SpectralFidelity requires a complete field")
        grid = PlaneGrid.from_deg(np.asarray(r["grid_lon"]), np.asarray(r["grid_lat"]))
        win = radial_hann(grid)
        masks = r.get("track_wedge_masks")
        exclude = list(masks) if masks is not None else []
        dk = 1.0 / grid.lx_km
        lo_km, hi_km = self.band_km(grid)
        day_powers = [power2d(detrend(day), win, grid) for day in maps]
        # ring geometry (k centers, mode counts) is grid-fixed; power varies by day
        k, _e0, n_modes = ring_spectrum(*day_powers[0], dk=dk, exclude=exclude)
        band = (k >= 1.0 / hi_km) & (k <= 1.0 / lo_km) & (n_modes > 0)
        if int(band.sum()) < 2:
            # a grid whose pinned band holds fewer than 2 populated rings
            # cannot support a slope — visible skip row via the {} precedent
            return {}
        k_band, n_band = k[band], n_modes[band]
        log_k = np.log10(k_band)
        day_slopes = []
        e_acc = np.zeros(k_band.size)
        for power, kx, ky in day_powers:
            _k, e_sum, _n = ring_spectrum(power, kx, ky, dk=dk, exclude=exclude)
            e_day = e_sum[band]
            e_acc += e_day
            day_slopes.append(_wls_slope(log_k, np.log10(e_day), n_band)[0])
        e_mean = e_acc / maps.shape[0]
        slope, slope_se = _wls_slope(log_k, np.log10(e_mean), n_band)
        q25, q75 = np.quantile(day_slopes, [0.25, 0.75])
        out = {
            "spec_slope": slope,
            "spec_slope_wls_se": slope_se,
            "spec_slope_day_median": float(np.median(day_slopes)),
            "spec_slope_day_iqr": float(q75 - q25),
            "spec_n_modes_min": float(n_band.min()),
            "wedge_exclusion": 1.0 if exclude else 0.0,
        }
        bag = cast(
            "dict[str, np.ndarray] | None",
            context.items.get(ContextKey.WITHHELD_OBS),
        )
        if bag is not None and all(k in bag for k in ("time", "lat", "lon", "values")):
            obs_slope = _obs_slope_1d(bag, lo_km, hi_km, grid.phi0)
            if obs_slope is not None:
                out["spec_slope_obs_1d"] = obs_slope
        return out
