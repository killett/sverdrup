"""In-situ gauge evaluator — the founding taxonomy completed (phase-14 0a-3b).

``InSituGauges`` joins the registry as a reference-based family member:
``required_context`` = the in-situ provider key, ``Registry.applicable``
picks it up iff the provider is present (the Phase-11 pattern; the
declared⇒consumed integrity suite covers it via ``ALL_EVALUATORS``).

Comparison operator: map SSHA bilinearly interpolated to the gauge location
(wet-node handling: weights renormalize over finite nodes, the blend
renormalization pattern) vs the gauge daily anomaly, both demeaned over the
common days (datum offsets cancel; the B2023 Eq.-1 stack is the reference
correction convention, recorded per gauge upstream).

Metrics are correlation and RMSE REDUCTION vs null. **Nulls come from the
SEALED instrument config only (fork-f pin 4):** ``InSituNullConfig`` is
constructed once (defaults are the sealed values, ingested by the Task-19
seal) — no scoring-time null choice exists in the API. Report-only: no bar
semantics anywhere (fork-f pin 6).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import numpy as np

from sverdrup.core.evaluation import ContextKey, EvalContext, MetricScope


@dataclass(frozen=True)
class InSituNullConfig:
    """The sealed null-model configuration (Task-19 seal substrate).

    Attributes:
        climo_smooth_days: Circular boxcar width [days] applied to the
            day-of-year climatology (the sealed 15).
        persist_lag_days: Persistence lag [days] (the sealed 1).
    """

    climo_smooth_days: int = 15
    persist_lag_days: int = 1


def null_climo(
    days: np.ndarray, values: np.ndarray, cfg: InSituNullConfig
) -> np.ndarray:
    """Day-of-year climatology null from the gauge's OWN record.

    The per-doy mean (doy 366 folded into 365) smoothed by a CIRCULAR
    boxcar of ``cfg.climo_smooth_days``; predictions read the smoothed
    climatology at each day's doy.

    Args:
        days: The gauge's days (datetime64[D]).
        values: The gauge's daily values.
        cfg: The sealed null config.

    Returns:
        The climatology prediction per input day.
    """
    doy = (days - days.astype("datetime64[Y]")).astype(int) + 1
    doy = np.minimum(doy, 365)
    climo = np.full(365, np.nan)
    for d in range(1, 366):
        sel = doy == d
        if sel.any():
            climo[d - 1] = values[sel].mean()
    half = cfg.climo_smooth_days // 2
    smoothed = np.full(365, np.nan)
    for d in range(365):
        window = climo[(np.arange(d - half, d + half + 1)) % 365]
        if np.isfinite(window).any():
            smoothed[d] = np.nanmean(window)
    return np.asarray(smoothed[doy - 1])


def null_persist(
    days: np.ndarray, values: np.ndarray, cfg: InSituNullConfig
) -> np.ndarray:
    """Lag-1-day persistence null: predict day t with the value at t - lag.

    Args:
        days: The gauge's days (datetime64[D]).
        values: The gauge's daily values.
        cfg: The sealed null config.

    Returns:
        The persistence prediction per day; NaN where the lagged day is
        absent from the record.
    """
    lag = np.timedelta64(cfg.persist_lag_days, "D")
    lookup = {
        d.astype("datetime64[D]").astype(int): v
        for d, v in zip(days, values, strict=True)
    }
    out = np.full(values.shape, np.nan)
    for i, d in enumerate(days):
        key = (d - lag).astype("datetime64[D]").astype(int)
        if key in lookup:
            out[i] = lookup[key]
    return out


def bilinear_wet(
    field: np.ndarray,
    lon_axis: np.ndarray,
    lat_axis: np.ndarray,
    lon: float,
    lat: float,
) -> float:
    """Bilinear interpolation with wet-node renormalization.

    NaN (land) corners drop out and the remaining weights renormalize —
    the actual-weight-sum lesson applied pointwise. All-dry cells return
    NaN (the gauge is skipped by the caller).

    Args:
        field: ``(ny, nx)`` map field (NaN = dry).
        lon_axis: Ascending 1-D grid longitudes.
        lat_axis: Ascending 1-D grid latitudes.
        lon: Gauge longitude (same convention as the axis).
        lat: Gauge latitude.

    Returns:
        The interpolated value, or NaN when no wet corner exists.
    """
    ix = int(np.clip(np.searchsorted(lon_axis, lon) - 1, 0, lon_axis.size - 2))
    iy = int(np.clip(np.searchsorted(lat_axis, lat) - 1, 0, lat_axis.size - 2))
    fx = (lon - lon_axis[ix]) / (lon_axis[ix + 1] - lon_axis[ix])
    fy = (lat - lat_axis[iy]) / (lat_axis[iy + 1] - lat_axis[iy])
    corners = np.array(
        [
            field[iy, ix],
            field[iy, ix + 1],
            field[iy + 1, ix],
            field[iy + 1, ix + 1],
        ]
    )
    weights = np.array(
        [
            (1 - fx) * (1 - fy),
            fx * (1 - fy),
            (1 - fx) * fy,
            fx * fy,
        ]
    )
    if not (lon_axis[0] <= lon <= lon_axis[-1] and lat_axis[0] <= lat <= lat_axis[-1]):
        return float("nan")  # outside the grid: never silently extrapolate
    wet = np.isfinite(corners)
    if not wet.any() or weights[wet].sum() == 0.0:
        return float("nan")
    return float((weights[wet] * corners[wet]).sum() / weights[wet].sum())


def _gauge_series(
    result: dict[str, Any], gauge: dict[str, Any]
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(common days, map series, gauge series) at the gauge location."""
    map_days = np.asarray(result["map_days"], dtype="datetime64[D]")
    g_days = np.asarray(gauge["days"], dtype="datetime64[D]")
    common, mi, gi = np.intersect1d(map_days, g_days, return_indices=True)
    lon_axis = np.asarray(result["map_lon"], dtype=float)
    lat_axis = np.asarray(result["map_lat"], dtype=float)
    ssha = np.asarray(result["map_ssha"], dtype=float)
    series = np.array(
        [
            bilinear_wet(ssha[i], lon_axis, lat_axis, gauge["lon"], gauge["lat"])
            for i in mi
        ]
    )
    return common, series, np.asarray(gauge["anomaly_m"], dtype=float)[gi]


def _rmse(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.sqrt(np.mean((a - b) ** 2)))


def per_gauge_rows(
    result: dict[str, Any],
    bag: dict[str, Any],
    cfg: InSituNullConfig,
) -> list[dict[str, Any]]:
    """Per-gauge report rows (the aggregate's visible substrate).

    Args:
        result: The map payload (``map_days``/``map_lon``/``map_lat``/
            ``map_ssha``).
        bag: The INSITU_GAUGES provider bag (``{"gauges": [...]}``).
        cfg: The sealed null config.

    Returns:
        One row per gauge with ≥ 2 usable common days. ONE day population
        per gauge (map, gauge, and BOTH nulls all finite) and ONE demeaning
        convention (every series demeaned over that same population) — the
        three RMSEs are commensurable and no mean offset leaks into any
        residual (adversarial-review convention fix, 2026-07-22).
    """
    rows: list[dict[str, Any]] = []
    for gauge in bag["gauges"]:
        common, map_s, gauge_s = _gauge_series(result, gauge)
        g_all = np.asarray(gauge["anomaly_m"], dtype=float)
        d_all = np.asarray(gauge["days"], dtype="datetime64[D]")
        climo_all = null_climo(d_all, g_all, cfg)
        persist_all = null_persist(d_all, g_all, cfg)
        sel = np.isin(d_all, common)
        climo = climo_all[sel]
        persist = persist_all[sel]
        ok = (
            np.isfinite(map_s)
            & np.isfinite(gauge_s)
            & np.isfinite(climo)
            & np.isfinite(persist)
        )
        if int(ok.sum()) < 2:
            continue
        m = map_s[ok] - map_s[ok].mean()
        g = gauge_s[ok] - gauge_s[ok].mean()
        c = climo[ok] - climo[ok].mean()
        p = persist[ok] - persist[ok].mean()
        rmse_map = _rmse(m, g)
        rmse_climo = _rmse(c, g)
        rmse_persist = _rmse(p, g)
        rows.append(
            {
                "gauge_id": gauge["gauge_id"],
                "n_days": int(ok.sum()),
                "corr": float(np.corrcoef(m, g)[0, 1]),
                "rmse_m": rmse_map,
                "rmse_climo_m": rmse_climo,
                "rmse_persist_m": rmse_persist,
                "reduction_climo": 1.0 - rmse_map / rmse_climo,
                "reduction_persist": 1.0 - rmse_map / rmse_persist,
            }
        )
    return rows


class InSituGauges:
    """Reference-based gauge evaluator (report-only, sealed nulls)."""

    name = "insitu_gauges"
    required_context = frozenset({ContextKey.INSITU_GAUGES})
    optional_context: frozenset[ContextKey] = frozenset()
    metric_scope = MetricScope.POINTWISE

    def __init__(self, null_config: InSituNullConfig | None = None) -> None:
        """Seal the null config at construction (never at scoring time)."""
        self._null_config = InSituNullConfig() if null_config is None else null_config

    def evaluate(self, result: object, context: EvalContext) -> dict[str, float]:
        """Aggregate gauge metrics for one map payload.

        Args:
            result: Mapping with ``map_days``/``map_lon``/``map_lat``/
                ``map_ssha`` ((n_days, ny, nx), NaN = dry).
            context: Carries the INSITU_GAUGES provider bag.

        Returns:
            ``insitu_corr_mean``, ``insitu_rmse_reduction_climo``,
            ``insitu_rmse_reduction_persist``, ``insitu_n_gauges`` —
            report-only, no bar semantics. Empty (a VISIBLE skip row) when
            no gauge overlaps or the payload carries no map keys.
        """
        bag = cast(dict[str, Any], context.items[ContextKey.INSITU_GAUGES])
        r = cast(dict[str, Any], result)
        needed = ("map_days", "map_lon", "map_lat", "map_ssha")
        if any(k not in r for k in needed):
            return {}  # skip visibly, never KeyError a non-gauge payload
        rows = per_gauge_rows(r, bag, self._null_config)
        if not rows:
            return {}
        return {
            "insitu_corr_mean": float(np.mean([r["corr"] for r in rows])),
            "insitu_rmse_reduction_climo": float(
                np.mean([r["reduction_climo"] for r in rows])
            ),
            "insitu_rmse_reduction_persist": float(
                np.mean([r["reduction_persist"] for r in rows])
            ),
            "insitu_n_gauges": float(len(rows)),
        }
