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


def test_unresolved_scale_error_carries_its_coherence_evidence() -> None:
    """The DEFINED signal arrives with the numbers that justify it (pin 160a).

    Bug caught: an absence recorded bare. Owner pin 160(a) is explicit --
    "an absence is never bare; the evidence is what stops it hiding a
    defect later". A caller that catches this error and records
    "lambda_x absent" with nothing attached produces a row indis-
    tinguishable from one where the map was fine and the scorer broke.
    The evidence rides on the exception so no catcher has to recompute a
    PSD to record honestly, and none can record without it.
    """
    from sverdrup.eval.spectral import UnresolvedScaleError, _coherence_guard

    # Equatorial's real shape: coherence never reaches 0.5 anywhere.
    coherence = np.array([-4.169, -0.533, -0.002, 0.0003, 0.003])
    evidence = {
        "coherence_min": -4.169,
        "coherence_max": 0.003,
        "psd_diff_over_ref_median": 1.0005,
        "wavelength_km": {"min": 12.8, "max": 996.3},
        "n_wavenumbers": 79,
    }
    with pytest.raises(UnresolvedScaleError) as exc:
        _coherence_guard(coherence, evidence=evidence)

    assert exc.value.evidence is not None
    assert exc.value.evidence["coherence_max"] == 0.003
    assert exc.value.evidence["psd_diff_over_ref_median"] == 1.0005
    assert exc.value.evidence["wavelength_km"]["max"] == 996.3


def test_coherence_guard_still_refuses_without_evidence() -> None:
    """Evidence is optional to the guard; the refusal is not.

    Bug caught: making the evidence mandatory and thereby turning a
    degenerate-map refusal into a TypeError at the call sites that do not
    supply it (lane_compare, loop, stage_a all catch the defined signal
    and record NaN -- they must keep working unchanged).
    """
    from sverdrup.eval.spectral import UnresolvedScaleError, _coherence_guard

    with pytest.raises(UnresolvedScaleError) as exc:
        _coherence_guard(np.array([0.1, 0.2, 0.3]))
    assert exc.value.evidence is None
