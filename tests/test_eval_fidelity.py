"""Tests for SpectralFidelity + the optional_context protocol extension (Task 4).

Band-edge expectations are hand-derived from the pinned rule (spec §5) and the
real-grid numbers measured in the plan: lo = max(100, 3*22.26) = 100 km (floor
binds), hi = min(300, 876/4) = 219 km (mainlobe-clearance rule binds; Lx is
the BOX EXTENT (nx-1)*dx = 876 km, not the FFT periodic length 893.5 km —
using the latter is the bug the 219.3 +- 1.0 assertion catches).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from sverdrup.core.evaluation import ContextKey, EvalContext, MetricScope, Registry
from sverdrup.eval.fidelity import SpectralFidelity
from sverdrup.eval.map_spectrum import PlaneGrid

PHI0 = 38.1


def _real_axes() -> tuple[np.ndarray, np.ndarray]:
    return np.arange(295, 305.01, 0.2), np.arange(33, 43.21, 0.2)


def _real_grid() -> PlaneGrid:
    lon, lat = _real_axes()
    return PlaneGrid.from_deg(lon, lat, phi0=PHI0)


def _gauss_field(seed: int, n_days: int, q: float = 3.0) -> np.ndarray:
    """Gaussian isotropic field with 2-D power density ~ |k|^-q."""
    rng = np.random.default_rng(seed)
    lon, lat = _real_axes()
    ny, nx = lat.size, lon.size
    kx = np.fft.fftfreq(nx)[None, :]
    ky = np.fft.fftfreq(ny)[:, None]
    kk = np.hypot(kx, ky)
    kk[0, 0] = np.inf
    amp = kk ** (-q / 2)
    days = []
    for _ in range(n_days):
        z = rng.standard_normal((ny, nx)) + 1j * rng.standard_normal((ny, nx))
        field = np.real(np.fft.ifft2(amp * z))
        days.append(field / field.std())
    return np.stack(days)


def _result(maps: np.ndarray, kind: str = "mean") -> dict[str, Any]:
    lon, lat = _real_axes()
    return {"fields": maps, "grid_lon": lon, "grid_lat": lat, "field_kind": kind}


class _OptionalWanter:
    name = "optional_wanter"
    required_context: frozenset[ContextKey] = frozenset()
    optional_context = frozenset({ContextKey.TRUTH})
    metric_scope = MetricScope.POINTWISE

    def evaluate(self, result: object, context: EvalContext) -> dict[str, float]:
        return {"x": 0.0}


def test_unmet_optionals_never_gate_applicability() -> None:
    """Bug caught: Registry.applicable gating on optional_context — the
    protocol extension must not change applicability semantics."""
    reg = Registry([_OptionalWanter()])
    assert [e.name for e in reg.applicable(set())] == ["optional_wanter"]
    assert [e.name for e in reg.applicable({ContextKey.WITHHELD_OBS})] == [
        "optional_wanter"
    ]


def test_band_edges_follow_rule_on_real_grid() -> None:
    """Bug caught: FFT periodic length instead of box extent (223.4 vs 219.0),
    or a dropped floor/cap in the pinned band rule."""
    lo, hi = SpectralFidelity().band_km(_real_grid())
    assert lo == 100.0
    assert abs(hi - 219.3) < 1.0


def test_band_floor_and_cap_bind_on_other_grids() -> None:
    """Bug caught: max/min swapped in either edge rule."""
    ev = SpectralFidelity()
    coarse = PlaneGrid.from_km(dx_km=17.5, dy_km=40.0, ny=30, nx=51)
    lo, _hi = ev.band_km(coarse)
    assert lo == pytest.approx(120.0)  # 3 * dy binds over the 100 floor
    wide = PlaneGrid.from_km(dx_km=40.0, dy_km=22.26, ny=52, nx=51)
    _lo, hi = ev.band_km(wide)
    assert hi == pytest.approx(300.0)  # cap binds: extent/4 = 500 > 300


def test_slope_recovered_on_synthetic_power_law() -> None:
    """Bug caught: broken WLS weighting, wrong ring selection, or a band in
    the wrong units — the known |k|^-3 field must fit to -2 in the band."""
    out = SpectralFidelity().evaluate(_result(_gauss_field(3, 20)), EvalContext({}))
    assert abs(out["spec_slope"] - (-2.0)) < 0.2
    assert out["spec_slope_wls_se"] > 0.0
    assert out["spec_n_modes_min"] >= 1.0


def test_day_statistics_present_and_coherent() -> None:
    """Bug caught: per-day slopes silently dropped (median/IQR absent or
    degenerate) — the day spread is the instrument's stability readout."""
    out = SpectralFidelity().evaluate(_result(_gauss_field(4, 8)), EvalContext({}))
    assert "spec_slope_day_median" in out
    assert out["spec_slope_day_iqr"] >= 0.0
    assert abs(out["spec_slope_day_median"] - out["spec_slope"]) < 1.0


def _obs_bag(
    seed: int = 0, q1d: float = 2.0, n_passes: int = 30, n_pts: int = 512
) -> dict[str, np.ndarray]:
    """Straight zonal passes at fixed latitudes; values carry a known 1-D
    power law (power ~ f^-q1d) along track. Longer passes give ~10 band bins
    each so the pooled fit has real spectral span (the pinned band covers
    only a factor ~2.2 in frequency)."""
    rng = np.random.default_rng(seed)
    lon = np.linspace(290.0, 310.0, n_pts)
    times, lats, lons, vals = [], [], [], []
    f = np.fft.rfftfreq(n_pts)
    amp = np.zeros_like(f)
    amp[1:] = f[1:] ** (-q1d / 2)
    for p in range(n_passes):
        z = rng.standard_normal(f.size) + 1j * rng.standard_normal(f.size)
        v = np.fft.irfft(amp * z, n=n_pts)
        lats.append(np.full(n_pts, 36.0 + 0.05 * p))
        lons.append(lon)
        vals.append(v / v.std())
        t0 = p * 0.5  # days; > 60 s gaps between passes
        times.append(t0 + np.linspace(0, 0.005, n_pts))
    return {
        "time": np.concatenate(times),
        "lat": np.concatenate(lats),
        "lon": np.concatenate(lons),
        "values": np.concatenate(vals),
    }


def test_obs_row_iff_withheld_present() -> None:
    """Bug caught: unconditional obs access (KeyError with no WITHHELD_OBS) or
    the obs row leaking in without the context."""
    ev = SpectralFidelity()
    res = _result(_gauss_field(5, 4))
    out_with = ev.evaluate(res, EvalContext({ContextKey.WITHHELD_OBS: _obs_bag()}))
    out_without = ev.evaluate(res, EvalContext({}))
    assert "spec_slope_obs_1d" in out_with
    assert "spec_slope_obs_1d" not in out_without


def test_obs_1d_slope_recovers_known_power_law() -> None:
    """Bug caught: broken along-track resampling/periodogram — a known 1-D
    f^-2 track spectrum must fit near -2 in the band."""
    ev = SpectralFidelity()
    out = ev.evaluate(
        _result(_gauss_field(6, 2)),
        EvalContext({ContextKey.WITHHELD_OBS: _obs_bag(seed=1, q1d=2.0, n_passes=100)}),
    )
    # Tolerance note: Hann + linear detrend bias the pooled fit ~-0.3 steep at
    # this pass count (measured -2.33); the bug classes this test exists for
    # (wrong km units, broken resampling, band in wrong space) land whole
    # integers away.
    assert abs(out["spec_slope_obs_1d"] - (-2.0)) < 0.5


def test_wedge_exclusion_flag_both_branches() -> None:
    """OWNER PIN 1a — bug caught: silent estimand degradation. Without the
    builder's masks the slope is still computed but the row must say
    wedge_exclusion=0; with masks, 1."""
    from sverdrup.eval.groundtrack import all_probe_wedge_masks

    ev = SpectralFidelity()
    res = _result(_gauss_field(7, 4))
    out_absent = ev.evaluate(res, EvalContext({}))
    assert out_absent["wedge_exclusion"] == 0.0
    assert np.isfinite(out_absent["spec_slope"])

    bag = {
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
    res2 = dict(res)
    res2["track_wedge_masks"] = all_probe_wedge_masks(bag, _real_grid())
    out_present = ev.evaluate(res2, EvalContext({}))
    assert out_present["wedge_exclusion"] == 1.0
    assert np.isfinite(out_present["spec_slope"])


def test_sigma_and_nan_guards_match_groundtrack() -> None:
    """Bug caught: fidelity accepting sigma maps or NaN (shared guard rule)."""
    ev = SpectralFidelity()
    maps = _gauss_field(8, 2)
    with pytest.raises(ValueError, match="mean"):
        ev.evaluate(_result(maps, kind="sigma"), EvalContext({}))
    maps[0, 3, 3] = np.nan
    with pytest.raises(ValueError, match="NaN"):
        ev.evaluate(_result(maps), EvalContext({}))


def test_metadata_pins() -> None:
    """Bug caught: dishonest declaration (fidelity must NOT require or read
    ORBIT_GEOMETRY — masks arrive via the result, spec §5 decision)."""
    ev = SpectralFidelity()
    assert ev.name == "spectral_fidelity"
    assert ev.required_context == frozenset()
    assert ev.optional_context == frozenset({ContextKey.WITHHELD_OBS})
    assert ev.metric_scope is MetricScope.POINTWISE
