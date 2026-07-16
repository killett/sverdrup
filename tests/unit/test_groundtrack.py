"""Tests for the rebuilt GroundTrack evaluator (plan Task 3; fork-d pin 1).

The old ``track_power`` pins die here by design — this file fully replaces
them. Fixtures are constructed so expected outcomes follow from the planted
signal (known heading/wavelength), never from running the evaluator.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from sverdrup.core.evaluation import ContextKey, EvalContext, MetricScope
from sverdrup.eval.groundtrack import GroundTrack
from sverdrup.eval.map_spectrum import PlaneGrid

PHI0 = 38.1


def _real_axes() -> tuple[np.ndarray, np.ndarray]:
    return np.arange(295, 305.01, 0.2), np.arange(33, 43.21, 0.2)


def _geometry_bag() -> dict[str, Any]:
    return {
        "synth": {
            "asc": {
                "heading_north_deg": 12.0,
                "orbit_class": "repeat",
                "d_perp_km": 248.0,
                "s_lon_km": 315.0,
                "n_crossings": 30,
            },
            "desc": None,
        }
    }


def _oriented_sinusoid(
    lon: np.ndarray, lat: np.ndarray, heading_north_deg: float, wavelength_km: float
) -> np.ndarray:
    """Stripes ALONG the track direction, spaced ``wavelength_km`` apart —
    wavevector perpendicular to the track, magnitude 1/wavelength."""
    g = PlaneGrid.from_deg(lon, lat, phi0=PHI0)
    h = np.deg2rad(heading_north_deg)
    ux, uy = np.cos(h), -np.sin(h)  # perpendicular-to-track unit (east, north)
    x = g.x_km[None, :]
    y = g.y_km[:, None]
    return np.sin(2.0 * np.pi * (ux * x + uy * y) / wavelength_km)


def _rednoise(lon: np.ndarray, lat: np.ndarray, seed: int, n_days: int) -> np.ndarray:
    """Gaussian isotropic red field (power ~ k^-1.5): complex-normal spectral
    amplitudes, NOT unit-modulus phases — fixed-amplitude fields have no
    day-to-day power variation and hide small-sample behavior."""
    rng = np.random.default_rng(seed)
    ny, nx = lat.size, lon.size
    kx = np.fft.fftfreq(nx)[None, :]
    ky = np.fft.fftfreq(ny)[:, None]
    kk = np.hypot(kx, ky)
    kk[0, 0] = np.inf
    amp = kk ** (-0.75)  # power ~ k^-1.5
    days = []
    for _ in range(n_days):
        z = rng.standard_normal((ny, nx)) + 1j * rng.standard_normal((ny, nx))
        field = np.real(np.fft.ifft2(amp * z))
        days.append(field / field.std())
    return np.stack(days)


def _result(
    maps: np.ndarray, lon: np.ndarray, lat: np.ndarray, kind: str = "mean"
) -> dict[str, Any]:
    return {"fields": maps, "grid_lon": lon, "grid_lat": lat, "field_kind": kind}


def _ctx(bag: dict[str, Any]) -> EvalContext:
    return EvalContext({ContextKey.ORBIT_GEOMETRY: bag})


def test_planted_track_signature_detected() -> None:
    """Bug caught: probing ALONG the track instead of perpendicular, or a
    wrong band radius (not 1/d_perp), misses the planted stripe entirely."""
    lon, lat = _real_axes()
    stripe = _oriented_sinusoid(lon, lat, heading_north_deg=12.0, wavelength_km=248.0)
    maps = stripe[None] + _rednoise(lon, lat, seed=5, n_days=8) * 0.3
    out = GroundTrack().evaluate(_result(maps, lon, lat), _ctx(_geometry_bag()))
    assert out["track_excess_log10_synth_asc"] > 1.0
    assert out["track_excess_log10_max_repeat"] == out["track_excess_log10_synth_asc"]


def test_isotropic_field_scores_near_zero() -> None:
    """Bug caught: missing per-mode normalization biases the statistic away
    from 0 (band and baseline share the same |k| range by design, so an
    isotropic field must score ~0 regardless of spectral slope).

    Fixture note: 12 days of a Gaussian k^-1.5 field; the missing-
    normalization bug class scores ~0.7 here (log10 of the 53/11 mode-count
    ratio), so 0.15 separates cleanly (15-seed sweep max |stat| = 0.156,
    this seed 0.035)."""
    lon, lat = _real_axes()
    maps = _rednoise(lon, lat, seed=9, n_days=12)
    out = GroundTrack().evaluate(_result(maps, lon, lat), _ctx(_geometry_bag()))
    assert abs(out["track_excess_log10_synth_asc"]) < 0.15


def test_n_modes_metrics_reported() -> None:
    """Bug caught: dropped mode-count companions break the report-row audit."""
    lon, lat = _real_axes()
    maps = _rednoise(lon, lat, seed=1, n_days=2)
    out = GroundTrack().evaluate(_result(maps, lon, lat), _ctx(_geometry_bag()))
    key = "track_excess_log10_synth_asc"
    assert out[key + "_n_modes_band"] >= 1.0
    assert out[key + "_n_modes_baseline"] >= 8.0


def test_sigma_field_refused_loudly() -> None:
    """Bug caught: scoring a sigma map 'detects' the EXPECTED sampling-geometry
    pattern (Phase-8 theorem) — must refuse, not report."""
    lon, lat = _real_axes()
    maps = _rednoise(lon, lat, seed=2, n_days=2)
    with pytest.raises(ValueError, match="mean"):
        GroundTrack().evaluate(
            _result(maps, lon, lat, kind="sigma"), _ctx(_geometry_bag())
        )


def test_nan_in_box_refused() -> None:
    """Bug caught: NaN silently propagating through the FFT zeroes the score."""
    lon, lat = _real_axes()
    maps = _rednoise(lon, lat, seed=3, n_days=2)
    maps[0, 5, 5] = np.nan
    with pytest.raises(ValueError, match="NaN"):
        GroundTrack().evaluate(_result(maps, lon, lat), _ctx(_geometry_bag()))


def test_drifting_family_uses_quantile_range_and_flags_estimand() -> None:
    """Bug caught: a missing drifting path (KeyError on d_perp_km=None) or a
    silent estimand switch without the visible flag."""
    lon, lat = _real_axes()
    bag = {
        "drift": {
            "asc": {
                "heading_north_deg": 40.0,
                "orbit_class": "drifting",
                "d_perp_km": None,
                "s_lon_km": None,
                "n_crossings": 48,
                "spacing_quantiles_km": (150.0, 220.0, 320.0),
            },
            "desc": None,
        }
    }
    maps = _rednoise(lon, lat, seed=4, n_days=4)
    out = GroundTrack().evaluate(_result(maps, lon, lat), _ctx(bag))
    key = "track_excess_log10_drift_asc"
    assert np.isfinite(out[key])
    assert out[key + "_estimand_drifting_band"] == 1.0
    assert out["track_excess_log10_max_drifting"] == out[key]
    assert "track_excess_log10_max_repeat" not in out  # never cross-class


def _crowded_bag(n_missions: int) -> dict[str, Any]:
    """Many families whose exclusion wedges starve the baseline annulus."""
    bag: dict[str, Any] = {}
    for i in range(n_missions):
        bag[f"m{i}"] = {
            "asc": {
                "heading_north_deg": 15.0 + 30.0 * i,
                "orbit_class": "repeat",
                "d_perp_km": 248.0,
                "s_lon_km": 300.0,
                "n_crossings": 20,
            },
            "desc": None,
        }
    return bag


def test_widening_fires_when_baseline_starved() -> None:
    """Bug caught: a missing widening loop leaves the baseline under the
    pre-registered floor when exclusion wedges crowd the annulus."""
    lon, lat = np.arange(295, 298.01, 0.2), np.arange(33, 36.01, 0.2)
    bag = _crowded_bag(4)  # 4 x 30 deg of exclusions on a small grid
    maps = _rednoise(lon, lat, seed=6, n_days=2)
    out = GroundTrack().evaluate(_result(maps, lon, lat), _ctx(bag))
    key = "track_excess_log10_m0_asc"
    assert out[key + "_n_widenings"] >= 1.0
    assert out[key + "_n_modes_baseline"] >= 8.0
    assert key + "_under_floor" not in out


def test_under_floor_flagged_metric_still_reported() -> None:
    """Bug caught: suppressing the metric (or crashing) when the floor cannot
    be met — the pinned rule is flag-and-report, not hide."""
    lon, lat = np.arange(295, 296.61, 0.2), np.arange(33, 34.61, 0.2)
    bag = _crowded_bag(5)  # 150 of 180 degrees excluded on a tiny grid
    maps = _rednoise(lon, lat, seed=7, n_days=2)
    out = GroundTrack().evaluate(_result(maps, lon, lat), _ctx(bag))
    key = "track_excess_log10_m0_asc"
    assert out[key + "_under_floor"] == 1.0
    assert out[key + "_n_widenings"] == 3.0
    assert key in out  # metric reported despite the flag


def test_precomputed_wedge_masks_match_self_derived() -> None:
    """Bug caught: the builder-shared exclusion-mask path (owner pin 1b)
    diverging from the evaluator's own derivation of the same wedges."""
    from sverdrup.eval.groundtrack import all_probe_wedge_masks

    lon, lat = _real_axes()
    maps = _rednoise(lon, lat, seed=8, n_days=3)
    bag = _geometry_bag()
    ctx = _ctx(bag)
    out_self = GroundTrack().evaluate(_result(maps, lon, lat), ctx)
    grid = PlaneGrid.from_deg(lon, lat)
    masks = all_probe_wedge_masks(bag, grid)
    res = _result(maps, lon, lat)
    res["track_wedge_masks"] = masks
    out_shared = GroundTrack().evaluate(res, ctx)
    assert out_self == out_shared


def test_metadata_and_docstring_pins() -> None:
    """Bug caught: a drifted declaration (integrity contract) or a dropped
    verbatim caveat the spec requires in the class docstring."""
    ev = GroundTrack()
    assert ev.required_context == frozenset({ContextKey.ORBIT_GEOMETRY})
    assert ev.optional_context == frozenset()
    assert ev.metric_scope is MetricScope.POINTWISE
    assert ev.name == "groundtrack"
    flat_doc = " ".join((GroundTrack.__doc__ or "").split())
    assert (
        "NECESSARY-NOT-SUFFICIENT — a strong track signature proves a problem; "
        "a clean map does not prove correctness." in flat_doc
    )
