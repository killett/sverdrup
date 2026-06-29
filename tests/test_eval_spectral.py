"""The shared λx helper: one algorithm, raw-residual boundary, loud on short tracks."""

from __future__ import annotations

import numpy as np
import pytest

from sverdrup.eval.spectral import ShortTrackError, effective_resolution_lambda_x


def _synthetic_track(
    n: int = 6000, dx_km: float = 6.39, seg: int = 600
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    # A long synthetic along-track signal + a smoothed "map" of it.
    # Time MUST be datetime64 at the Δt cadence, AND must contain >4s gaps so the
    # vendored compute_spectral_scores can cut the record into passes (it segments
    # on np.diff(time) > 4s and assumes >=1 gap, like a real year of CryoSat-2).
    # We insert a 1-day gap every `seg` samples; each pass (>= npt~156) yields PSD.
    rng = np.random.default_rng(0)
    s = np.cumsum(rng.standard_normal(n)) * 0.01
    # crude low-pass "map" (resolves long scales, loses short ones)
    k = np.ones(50) / 50.0
    m = np.convolve(s, k, mode="same")
    t0 = np.datetime64("2017-01-01T00:00:00")
    step = np.timedelta64(943400, "us")  # 0.9434 s along-track spacing
    gap = np.timedelta64(1, "D")  # >4s gap between passes
    idx = np.arange(n)
    t = t0 + idx * step + (idx // seg) * gap
    lat = 38.0 + np.zeros(n)
    lon = 300.0 + np.cumsum(np.full(n, dx_km / 111.0))
    return t, lat, lon, s, m


def test_lambda_x_is_finite_and_positive() -> None:
    # Behavior: a real long track yields a finite positive resolution.
    t, lat, lon, s, m = _synthetic_track()
    lx = effective_resolution_lambda_x(t, lat, lon, s, m)
    assert np.isfinite(lx) and lx > 0


def test_short_track_raises_loudly() -> None:
    # Behavior: a track too short for one spectral segment is a config error, not a value.
    # Bug it catches: a noisy λx silently emitted and chased by the search.
    t, lat, lon, s, m = _synthetic_track(n=20)
    with pytest.raises(ShortTrackError):
        effective_resolution_lambda_x(t, lat, lon, s, m)
