"""In-situ gauge evaluator tests (phase-14 Task 9, 0a-3b).

Fixtures are synthetic gauge + synthetic map series where the analytic
answer is known; the wrong-null bug (climatology WITHOUT the 15-day boxcar)
is caught by a hand-computed value pin at the year-wrap day.
"""

from __future__ import annotations

import inspect
from typing import Any

import numpy as np
import pytest

from sverdrup.core.evaluation import ContextKey, EvalContext, MetricScope
from sverdrup.eval.insitu import (
    InSituGauges,
    InSituNullConfig,
    bilinear_wet,
    null_climo,
    null_persist,
    per_gauge_rows,
)


def _days(start: str, n: int) -> np.ndarray:
    return np.datetime64(start) + np.arange(n).astype("timedelta64[D]")


# ---------------------------------------------------------------------------
# Null models (sealed config only)
# ---------------------------------------------------------------------------


def test_null_climo_boxcar_value_pin_at_wrap() -> None:
    """The 15-day CIRCULAR boxcar moves the wrap-day value measurably.

    Fixture: two years of values = doy (a sawtooth in day-of-year). The raw
    per-doy climatology at doy 1 is exactly 1.0; the circular 15-day boxcar
    at doy 1 averages doys {359..365, 1..8} = (359+…+365+1+…+8)/15 = 171.33….
    An unsmoothed climatology (the wrong-null bug) returns 1.0 and fails.
    """
    days = _days("2015-01-01", 730)
    doy = (days - days.astype("datetime64[Y]")).astype(int) + 1
    doy = np.minimum(doy, 365)
    values = doy.astype(float)
    cfg = InSituNullConfig()
    pred = null_climo(days, values, cfg)
    wrap_expected = (sum(range(359, 366)) + sum(range(1, 9))) / 15.0
    assert pred[0] == pytest.approx(wrap_expected, rel=1e-12)
    # mid-year: sawtooth is locally linear, boxcar preserves it exactly
    mid = 182  # doy 183 in year 1
    assert pred[mid] == pytest.approx(values[mid], rel=1e-12)


def test_null_persist_lag1() -> None:
    """Persistence predicts yesterday's value; day-gaps yield NaN, day 0 NaN."""
    days = np.array(["2015-01-01", "2015-01-02", "2015-01-04"], dtype="datetime64[D]")
    values = np.array([1.0, 2.0, 3.0])
    pred = null_persist(days, values, InSituNullConfig())
    assert np.isnan(pred[0])
    assert pred[1] == 1.0
    assert np.isnan(pred[2])  # Jan 3 missing: no lag-1 neighbor


def test_no_scoring_time_null_choice_in_api() -> None:
    """Nulls come from the sealed config object only — evaluate() exposes
    no null parameter (fork-f pin 4)."""
    params = inspect.signature(InSituGauges.evaluate).parameters
    assert set(params) == {"self", "result", "context"}


# ---------------------------------------------------------------------------
# Comparison operator
# ---------------------------------------------------------------------------


def test_bilinear_wet_renormalizes_over_finite_nodes() -> None:
    """A NaN (land) corner never poisons the interp: weights renormalize.

    Constant field with one NaN corner must return the constant; the plain
    bilinear formula returns NaN and fails.
    """
    lon = np.array([0.0, 1.0])
    lat = np.array([0.0, 1.0])
    field = np.array([[5.0, 5.0], [np.nan, 5.0]])
    got = bilinear_wet(field, lon, lat, 0.4, 0.6)
    assert got == pytest.approx(5.0, rel=1e-12)


def test_bilinear_wet_exact_on_linear_field() -> None:
    """On an all-wet linear field the interp is exact (hand value)."""
    lon = np.array([0.0, 1.0])
    lat = np.array([0.0, 1.0])
    field = np.array([[0.0, 1.0], [2.0, 3.0]])  # f = lon + 2*lat
    got = bilinear_wet(field, lon, lat, 0.25, 0.5)
    assert got == pytest.approx(0.25 + 2 * 0.5, rel=1e-12)


def test_bilinear_wet_all_dry_returns_nan() -> None:
    """All four corners NaN -> NaN (the gauge is skipped upstream)."""
    lon = np.array([0.0, 1.0])
    lat = np.array([0.0, 1.0])
    field = np.full((2, 2), np.nan)
    assert np.isnan(bilinear_wet(field, lon, lat, 0.5, 0.5))


# ---------------------------------------------------------------------------
# Evaluator: registry contract + analytic verdicts
# ---------------------------------------------------------------------------


def _fixture(n_days: int = 400) -> tuple[dict[str, Any], dict[str, Any]]:
    """A one-gauge bag + a map whose series EQUALS the gauge anomaly."""
    days = _days("2017-01-01", n_days)
    rng = np.random.default_rng(7)
    anomaly = np.sin(2 * np.pi * np.arange(n_days) / 60.0) * 0.1
    anomaly += 0.01 * rng.standard_normal(n_days)
    lon_axis = np.array([200.0, 201.0])
    lat_axis = np.array([20.0, 21.0])
    ssha = np.zeros((n_days, 2, 2))
    ssha[:] = anomaly[:, None, None]  # spatially constant = exact at gauge
    result = {
        "map_days": days,
        "map_lon": lon_axis,
        "map_lat": lat_axis,
        "map_ssha": ssha,
    }
    bag = {
        "gauges": [
            {
                "gauge_id": "gX",
                "lon": 200.5,
                "lat": 20.5,
                "days": days,
                "anomaly_m": anomaly,
            }
        ]
    }
    return result, bag


def test_registry_contract() -> None:
    """Reference-based membership: required_context = the provider key only."""
    ev = InSituGauges()
    assert ev.name == "insitu_gauges"
    assert ev.required_context == frozenset({ContextKey.INSITU_GAUGES})
    assert ev.metric_scope == MetricScope.POINTWISE


def test_perfect_map_scores_perfectly() -> None:
    """Map == gauge anomaly: corr 1, rmse 0, reductions 1 vs both nulls."""
    result, bag = _fixture()
    metrics = InSituGauges().evaluate(
        result, EvalContext({ContextKey.INSITU_GAUGES: bag})
    )
    assert metrics["insitu_n_gauges"] == 1.0
    assert metrics["insitu_corr_mean"] == pytest.approx(1.0, abs=1e-12)
    assert metrics["insitu_rmse_reduction_climo"] == pytest.approx(1.0, abs=1e-12)
    assert metrics["insitu_rmse_reduction_persist"] == pytest.approx(1.0, abs=1e-12)


def test_persistence_map_gets_zero_persist_reduction() -> None:
    """A map that IS the persistence forecast earns ~0 reduction vs persist.

    Catches a reversed-reduction bug (rmse_null/rmse_map inverts the sign)
    and swapped nulls: reduction-vs-persist must sit at ~0 while
    reduction-vs-climo lands clearly elsewhere (the 60-day sine is not
    doy-locked, so the two nulls are genuinely different models here —
    measured gap ≈ 0.10).
    """
    result, bag = _fixture()
    g = bag["gauges"][0]
    pred = null_persist(g["days"], g["anomaly_m"], InSituNullConfig())
    ok = np.isfinite(pred)
    result = dict(result)
    ssha = np.zeros_like(result["map_ssha"])
    ssha[ok] = pred[ok, None, None]
    ssha[~ok] = 0.0
    result["map_ssha"] = ssha
    metrics = InSituGauges().evaluate(
        result, EvalContext({ContextKey.INSITU_GAUGES: bag})
    )
    assert abs(metrics["insitu_rmse_reduction_persist"]) < 0.05
    gap = abs(
        metrics["insitu_rmse_reduction_climo"]
        - metrics["insitu_rmse_reduction_persist"]
    )
    assert gap > 0.05  # nulls are distinct models; a swap collapses this


def test_per_gauge_rows_shape() -> None:
    """Per-gauge rows carry the row schema for the pack (one row per gauge)."""
    result, bag = _fixture()
    rows = per_gauge_rows(result, bag, InSituNullConfig())
    assert len(rows) == 1
    row = rows[0]
    assert row["gauge_id"] == "gX"
    for key in (
        "n_days",
        "corr",
        "rmse_m",
        "rmse_climo_m",
        "rmse_persist_m",
        "reduction_climo",
        "reduction_persist",
    ):
        assert key in row


def test_report_only_no_bar_semantics() -> None:
    """No metric name carries bar/floor semantics (fork-f pin 6)."""
    result, bag = _fixture()
    metrics = InSituGauges().evaluate(
        result, EvalContext({ContextKey.INSITU_GAUGES: bag})
    )
    assert not any(("bar" in k or "floor" in k) for k in metrics)
