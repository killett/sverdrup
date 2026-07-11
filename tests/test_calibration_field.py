"""Tests for the CalibrationField hierarchy (Phase 8, Task 2).

All four lanes: ScalarCalibration, PiecewiseCalibration, PolyCalibration,
CovariateCalibration.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from sverdrup.application.calibration.constants import CLIP_PAD, S_STAR
from sverdrup.distributions.miost_ensemble import (
    CalibrationField,
    ClipSpec,
    CovariateCalibration,
    PiecewiseCalibration,
    PolyCalibration,
    ScalarCalibration,
    calibration_from_json,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

LOG_S_STAR = math.log(S_STAR)
CLIP_LO = LOG_S_STAR - math.log(CLIP_PAD)
CLIP_HI = LOG_S_STAR + math.log(CLIP_PAD)
_CLIP = ClipSpec(lo_log_s=CLIP_LO, hi_log_s=CLIP_HI)

# Grid sampling points (lon, lat) that span and exceed the box
_LONS = np.array([295.0, 297.0, 300.0, 303.0, 305.0, 293.0, 307.0])
_LATS = np.array([33.0, 36.0, 38.0, 40.0, 43.0, 31.0, 45.0])

# A simple 5×5 piecewise log-s grid (all equal to LOG_S_STAR → scalar limit)
_ALL_STAR_PIECEWISE = {
    "SW": LOG_S_STAR,
    "SE": LOG_S_STAR,
    "NW": LOG_S_STAR,
    "NE": LOG_S_STAR,
    "JET": LOG_S_STAR,
}
# Jet-core mask: all False (no jet cells)
_NO_JET_MASK: tuple[tuple[bool, ...], ...] = tuple(
    tuple(False for _ in range(5)) for _ in range(5)
)


def _make_piecewise(
    log_s_by_region: dict[str, float] | None = None,
    mask: tuple[tuple[bool, ...], ...] | None = None,
    clip: ClipSpec | None = None,
    fit_id: str = "test",
) -> PiecewiseCalibration:
    return PiecewiseCalibration(
        lon_mid=300.0,
        lat_mid=38.0,
        mask=mask if mask is not None else _NO_JET_MASK,
        log_s_by_region=log_s_by_region
        if log_s_by_region is not None
        else _ALL_STAR_PIECEWISE,
        clip=clip if clip is not None else _CLIP,
        fit_id=fit_id,
    )


# ---------------------------------------------------------------------------
# ScalarCalibration
# ---------------------------------------------------------------------------


def test_scalar_log_s_at_returns_constant_array() -> None:
    """log_s_at must return a broadcast-shaped array of log(s).

    Bug caught: returning a Python float instead of ndarray, or wrong value.
    """
    cal = ScalarCalibration(s=S_STAR)
    lon = np.array([295.0, 300.0, 305.0])
    lat = np.array([33.0, 38.0, 43.0])
    result = cal.log_s_at(lon, lat)
    assert result.shape == (3,)
    np.testing.assert_allclose(result, math.log(S_STAR), rtol=1e-15)


def test_scalar_sqrt_s_at_returns_sqrt() -> None:
    """sqrt_s_at must return sqrt(s) everywhere, clip-free.

    Bug caught: clip applied to ScalarCalibration (spec says clip-free).
    """
    cal = ScalarCalibration(s=S_STAR)
    lon = np.array([295.0, 300.0])
    lat = np.array([33.0, 38.0])
    np.testing.assert_allclose(cal.sqrt_s_at(lon, lat), math.sqrt(S_STAR), rtol=1e-15)


def test_scalar_key_contains_s() -> None:
    """key() must embed s value so distinct scalars produce distinct keys.

    Bug caught: key() returning a constant string regardless of s.
    """
    k1 = ScalarCalibration(s=1.0).key()
    k2 = ScalarCalibration(s=2.0).key()
    assert k1 != k2
    assert "scalar" in k1
    assert repr(S_STAR) in ScalarCalibration(s=S_STAR).key()


def test_scalar_json_roundtrip() -> None:
    """from_json(to_json(f)) reproduces sqrt_s_at bit-identically on a grid.

    Bug caught: float serialised as int, or s lost in JSON.
    """
    cal = ScalarCalibration(s=S_STAR)
    rt = calibration_from_json(cal.to_json())
    assert isinstance(rt, ScalarCalibration)
    np.testing.assert_array_equal(
        cal.sqrt_s_at(_LONS, _LATS), rt.sqrt_s_at(_LONS, _LATS)
    )


# ---------------------------------------------------------------------------
# PolyCalibration
# ---------------------------------------------------------------------------


def test_poly_scalar_reduction_exact() -> None:
    """Coeffs (log s*, 0,...) must equal ScalarCalibration(s*) everywhere.

    Bug caught: wrong normalization of (u, v) or a stray offset term.
    """
    poly = PolyCalibration(
        coeffs=(math.log(S_STAR), 0.0, 0.0, 0.0, 0.0),
        clip=ClipSpec(lo_log_s=math.log(S_STAR) - 1, hi_log_s=math.log(S_STAR) + 1),
        fit_id="test",
    )
    lon = np.array([295.0, 300.0, 305.0, 299.3])
    lat = np.array([33.0, 38.0, 43.0, 41.7])
    np.testing.assert_allclose(poly.sqrt_s_at(lon, lat), np.sqrt(S_STAR), rtol=1e-15)
    # rtol=1e-15, not 0: exp(0.5*log(s)) vs sqrt(s) is a transcendental
    # roundtrip — ulp-fragile at exact equality (owner review fix, 2026-07-10).
    # The load-bearing pin stays the distribution-level s*-identity at
    # rtol 1e-12 (Task 5).


def test_clamp_constant_continuation_outside_hull() -> None:
    """s at (294, 32) must equal s at the clamped corner (295, 33).

    Bug caught: raw extrapolation of the quadratic outside the box.
    """
    poly = PolyCalibration(
        coeffs=(LOG_S_STAR, 0.5, 0.3, -0.2, 0.1),
        clip=ClipSpec(lo_log_s=LOG_S_STAR - 2, hi_log_s=LOG_S_STAR + 2),
        fit_id="test",
    )
    inside = poly.sqrt_s_at(np.array([295.0]), np.array([33.0]))
    outside = poly.sqrt_s_at(np.array([290.0]), np.array([28.0]))
    np.testing.assert_array_equal(inside, outside)


def test_clip_engages_and_is_recorded() -> None:
    """A poly whose raw value exceeds hi must return exactly hi.

    Bug caught: clip applied to s instead of log s, or not at all.
    """
    hi = LOG_S_STAR + 0.1
    lo = LOG_S_STAR - 0.5
    # coeffs push log s well above hi at the box center
    poly = PolyCalibration(
        coeffs=(LOG_S_STAR + 2.0, 0.0, 0.0, 0.0, 0.0),
        clip=ClipSpec(lo_log_s=lo, hi_log_s=hi),
        fit_id="test",
    )
    result = poly.log_s_at(np.array([300.0]), np.array([38.0]))
    np.testing.assert_allclose(result, np.array([hi]), rtol=1e-15)


def test_poly_key_changes_with_every_param() -> None:
    """Perturbing any coeff, clip bound, or fit_id changes key().

    Bug caught: cache collisions between distinct calibrations.
    """
    base = PolyCalibration(
        coeffs=(LOG_S_STAR, 0.1, 0.2, 0.3, 0.4),
        clip=ClipSpec(lo_log_s=LOG_S_STAR - 1, hi_log_s=LOG_S_STAR + 1),
        fit_id="run1",
    )
    k0 = base.key()

    # Perturb each coeff
    for i in range(5):
        perturbed = list(base.coeffs)
        perturbed[i] += 0.001
        cal = PolyCalibration(
            coeffs=tuple(perturbed),  # type: ignore[arg-type]
            clip=base.clip,
            fit_id=base.fit_id,
        )
        assert cal.key() != k0, f"key unchanged after perturbing coeff[{i}]"

    # Perturb lo clip
    cal_lo = PolyCalibration(
        coeffs=base.coeffs,
        clip=ClipSpec(lo_log_s=base.clip.lo_log_s + 0.001, hi_log_s=base.clip.hi_log_s),
        fit_id=base.fit_id,
    )
    assert cal_lo.key() != k0, "key unchanged after perturbing lo_log_s"

    # Perturb hi clip
    cal_hi = PolyCalibration(
        coeffs=base.coeffs,
        clip=ClipSpec(lo_log_s=base.clip.lo_log_s, hi_log_s=base.clip.hi_log_s + 0.001),
        fit_id=base.fit_id,
    )
    assert cal_hi.key() != k0, "key unchanged after perturbing hi_log_s"

    # Perturb fit_id
    cal_id = PolyCalibration(
        coeffs=base.coeffs,
        clip=base.clip,
        fit_id="run2",
    )
    assert cal_id.key() != k0, "key unchanged after changing fit_id"


def test_poly_json_roundtrip_bitexact() -> None:
    """from_json(to_json(f)) reproduces sqrt_s_at bit-identically on a grid.

    Bug caught: coeff tuple mangled to list, or float precision lost.
    """
    poly = PolyCalibration(
        coeffs=(LOG_S_STAR, 0.123, -0.456, 0.789, -0.321),
        clip=_CLIP,
        fit_id="rt-test",
    )
    rt = calibration_from_json(poly.to_json())
    assert isinstance(rt, PolyCalibration)
    np.testing.assert_array_equal(
        poly.sqrt_s_at(_LONS, _LATS), rt.sqrt_s_at(_LONS, _LATS)
    )


# ---------------------------------------------------------------------------
# PiecewiseCalibration
# ---------------------------------------------------------------------------


def test_piecewise_scalar_reduction() -> None:
    """All-regions-log-s* must equal ScalarCalibration(s*) everywhere in box.

    Bug caught: wrong region lookup or log/exp error.
    """
    pw = _make_piecewise(log_s_by_region=_ALL_STAR_PIECEWISE)
    lon = np.array([296.0, 300.0, 304.0])
    lat = np.array([34.0, 38.0, 42.0])
    np.testing.assert_allclose(pw.sqrt_s_at(lon, lat), math.sqrt(S_STAR), rtol=1e-15)


def test_piecewise_quadrant_lookup() -> None:
    """NE quadrant points must return NE log-s, SW points SW log-s.

    Bug caught: E/W or N/S sense inverted in region assignment.
    """
    ne_val = LOG_S_STAR + 0.3
    sw_val = LOG_S_STAR - 0.3
    log_s_by_region: dict[str, float] = {
        "SW": sw_val,
        "SE": LOG_S_STAR,
        "NW": LOG_S_STAR,
        "NE": ne_val,
        "JET": LOG_S_STAR,
    }
    clip = ClipSpec(lo_log_s=LOG_S_STAR - 1, hi_log_s=LOG_S_STAR + 1)
    pw = PiecewiseCalibration(
        lon_mid=300.0,
        lat_mid=38.0,
        mask=_NO_JET_MASK,
        log_s_by_region=log_s_by_region,
        clip=clip,
        fit_id="quad",
    )
    # NE: lon > 300, lat > 38
    np.testing.assert_allclose(
        pw.log_s_at(np.array([302.0]), np.array([40.0])),
        np.array([ne_val]),
        rtol=1e-15,
    )
    # SW: lon < 300, lat < 38
    np.testing.assert_allclose(
        pw.log_s_at(np.array([297.0]), np.array([35.0])),
        np.array([sw_val]),
        rtol=1e-15,
    )


def test_piecewise_jet_cell_takes_jet_region() -> None:
    """A cell in the jet mask must return JET log-s, not the quadrant value.

    Bug caught: jet-mask check missing; quadrant value returned for jet cells.
    """
    jet_val = LOG_S_STAR + 0.5
    # Set NE to a different value from jet
    ne_val = LOG_S_STAR - 0.2
    log_s_by_region: dict[str, float] = {
        "SW": LOG_S_STAR,
        "SE": LOG_S_STAR,
        "NW": LOG_S_STAR,
        "NE": ne_val,
        "JET": jet_val,
    }
    # Mark cell (row=4, col=4) as jet — that's the NE corner cell
    mask_list = [[False] * 5 for _ in range(5)]
    mask_list[4][4] = True
    mask: tuple[tuple[bool, ...], ...] = tuple(tuple(row) for row in mask_list)
    clip = ClipSpec(lo_log_s=LOG_S_STAR - 1, hi_log_s=LOG_S_STAR + 1)
    pw = PiecewiseCalibration(
        lon_mid=300.0,
        lat_mid=38.0,
        mask=mask,
        log_s_by_region=log_s_by_region,
        clip=clip,
        fit_id="jet",
    )
    # lon=304 → col=4 (between 303-305), lat=41 → row=4 (between 41-43)
    # That cell is marked jet
    result = pw.log_s_at(np.array([304.0]), np.array([41.0]))
    np.testing.assert_allclose(result, np.array([jet_val]), rtol=1e-15)


def test_piecewise_lookup_and_out_of_range_raises() -> None:
    """Region values outside [lo, hi] must raise at construction.

    Bug caught: silently clipping evidence-side values (spec §9 assert).
    """
    clip = ClipSpec(lo_log_s=LOG_S_STAR - 0.5, hi_log_s=LOG_S_STAR + 0.5)
    bad_regions = {
        "SW": LOG_S_STAR,
        "SE": LOG_S_STAR,
        "NW": LOG_S_STAR,
        "NE": LOG_S_STAR,
        "JET": LOG_S_STAR + 1.0,  # exceeds hi → must raise
    }
    with pytest.raises(ValueError, match="[Rr]egion|log_s|clip|outside"):
        PiecewiseCalibration(
            lon_mid=300.0,
            lat_mid=38.0,
            mask=_NO_JET_MASK,
            log_s_by_region=bad_regions,
            clip=clip,
            fit_id="bad",
        )


def test_piecewise_clamp_outside_hull() -> None:
    """Points outside the box hull must be clamped (constant continuation).

    Bug caught: raw out-of-box cell index falls off the grid.
    """
    pw = _make_piecewise()
    # Point outside the box should give same result as the clamped corner
    inside = pw.sqrt_s_at(np.array([295.0]), np.array([33.0]))
    outside = pw.sqrt_s_at(np.array([290.0]), np.array([28.0]))
    np.testing.assert_array_equal(inside, outside)


def test_piecewise_key_changes_with_every_param() -> None:
    """Perturbing any field changes key().

    Bug caught: cache collisions between distinct piecewise calibrations.
    """
    pw = _make_piecewise(fit_id="base")
    k0 = pw.key()
    assert _make_piecewise(fit_id="other").key() != k0
    new_regions = dict(_ALL_STAR_PIECEWISE)
    new_regions["NE"] = LOG_S_STAR + 0.001
    clip_hi = ClipSpec(lo_log_s=_CLIP.lo_log_s, hi_log_s=_CLIP.hi_log_s + 0.5)
    assert _make_piecewise(log_s_by_region=new_regions, clip=clip_hi).key() != k0


def test_piecewise_json_roundtrip_bitexact() -> None:
    """from_json(to_json(f)) reproduces sqrt_s_at bit-identically on a grid.

    Bug caught: mask serialized as nested booleans lost or misread.
    """
    pw = _make_piecewise()
    rt = calibration_from_json(pw.to_json())
    assert isinstance(rt, PiecewiseCalibration)
    np.testing.assert_array_equal(
        pw.sqrt_s_at(_LONS, _LATS), rt.sqrt_s_at(_LONS, _LATS)
    )


# ---------------------------------------------------------------------------
# CovariateCalibration
# ---------------------------------------------------------------------------


def _make_proxy_cells(
    fill: float = math.exp(LOG_S_STAR),
) -> tuple[tuple[float, ...], ...]:
    """Return a (5,5) proxy_cells tuple filled with ``fill``."""
    return tuple(tuple(fill for _ in range(5)) for _ in range(5))


def test_covariate_b_zero_constant_log_s() -> None:
    """b=0 → log s = a everywhere (constant, independent of proxy).

    Bug caught: proxy lookup called when b=0, crashing on log(0).
    """
    a = LOG_S_STAR
    proxy_val = 5.0  # arbitrary nonzero
    cal = CovariateCalibration(
        proxy_cells=_make_proxy_cells(fill=proxy_val),
        a=a,
        b=0.0,
        clip=ClipSpec(lo_log_s=a - 1, hi_log_s=a + 1),
        fit_id="b0",
    )
    lon = np.array([297.0, 300.0, 303.0])
    lat = np.array([35.0, 38.0, 41.0])
    np.testing.assert_allclose(cal.log_s_at(lon, lat), a, rtol=1e-15)


def test_covariate_scalar_reduction_via_log_proxy() -> None:
    """a=log(s*), b=1, proxy=s* → log s = log s* + log s* = 2*log(s*)?

    Specific scalar reduction: a + b*log(proxy) with proxy=exp(0) = 1.0
    gives log s = a everywhere (since log(1)=0).

    Bug caught: wrong sign or factor on the b term.
    """
    a = LOG_S_STAR
    # proxy = 1.0 → log(proxy) = 0 → log s = a regardless of b
    cal = CovariateCalibration(
        proxy_cells=_make_proxy_cells(fill=1.0),
        a=a,
        b=1.5,  # any b
        clip=ClipSpec(lo_log_s=a - 2, hi_log_s=a + 2),
        fit_id="log1",
    )
    lon = np.array([296.0, 301.0])
    lat = np.array([34.0, 39.0])
    np.testing.assert_allclose(cal.log_s_at(lon, lat), a, rtol=1e-15)


def test_covariate_clip_engages() -> None:
    """A covariate whose raw value exceeds hi must return exactly hi.

    Bug caught: clip skipped on covariate lane.
    """
    hi = LOG_S_STAR + 0.2
    lo = LOG_S_STAR - 0.5
    # proxy = e → log proxy = 1; a + b*1 = LOG_S_STAR + 3 >> hi
    cal = CovariateCalibration(
        proxy_cells=_make_proxy_cells(fill=math.e),
        a=LOG_S_STAR,
        b=3.0,
        clip=ClipSpec(lo_log_s=lo, hi_log_s=hi),
        fit_id="clip-cov",
    )
    result = cal.log_s_at(np.array([300.0]), np.array([38.0]))
    np.testing.assert_allclose(result, np.array([hi]), rtol=1e-15)


def test_covariate_clamp_outside_hull() -> None:
    """Points outside the hull clamp to the hull boundary.

    Bug caught: out-of-box coordinates produce negative cell indices.
    """
    cal = CovariateCalibration(
        proxy_cells=_make_proxy_cells(fill=2.0),
        a=LOG_S_STAR,
        b=0.5,
        clip=ClipSpec(lo_log_s=LOG_S_STAR - 2, hi_log_s=LOG_S_STAR + 2),
        fit_id="clamp-cov",
    )
    inside = cal.sqrt_s_at(np.array([295.0]), np.array([33.0]))
    outside = cal.sqrt_s_at(np.array([280.0]), np.array([20.0]))
    np.testing.assert_array_equal(inside, outside)


def test_covariate_key_changes_with_every_param() -> None:
    """Perturbing any param changes key().

    Bug caught: cache collisions between distinct covariate calibrations.
    """
    proxy = _make_proxy_cells(fill=2.0)
    clip = ClipSpec(lo_log_s=LOG_S_STAR - 1, hi_log_s=LOG_S_STAR + 1)
    base = CovariateCalibration(
        proxy_cells=proxy, a=LOG_S_STAR, b=0.5, clip=clip, fit_id="c1"
    )
    k0 = base.key()

    # Different a
    assert (
        CovariateCalibration(
            proxy_cells=proxy, a=LOG_S_STAR + 0.1, b=0.5, clip=clip, fit_id="c1"
        ).key()
        != k0
    )
    # Different b
    assert (
        CovariateCalibration(
            proxy_cells=proxy, a=LOG_S_STAR, b=0.6, clip=clip, fit_id="c1"
        ).key()
        != k0
    )
    # Different fit_id
    assert (
        CovariateCalibration(
            proxy_cells=proxy, a=LOG_S_STAR, b=0.5, clip=clip, fit_id="c2"
        ).key()
        != k0
    )
    # Different clip
    clip2 = ClipSpec(lo_log_s=LOG_S_STAR - 1.5, hi_log_s=LOG_S_STAR + 1)
    assert (
        CovariateCalibration(
            proxy_cells=proxy, a=LOG_S_STAR, b=0.5, clip=clip2, fit_id="c1"
        ).key()
        != k0
    )


def test_covariate_json_roundtrip_bitexact() -> None:
    """from_json(to_json(f)) reproduces sqrt_s_at bit-identically on a grid.

    Bug caught: proxy_cells serialized as float but deserialized as int.
    """
    # Use a proxy grid with varying values
    proxy_list = [[float(r * 5 + c + 1) for c in range(5)] for r in range(5)]
    proxy: tuple[tuple[float, ...], ...] = tuple(tuple(row) for row in proxy_list)
    cal = CovariateCalibration(
        proxy_cells=proxy,
        a=LOG_S_STAR,
        b=0.1,
        clip=ClipSpec(lo_log_s=LOG_S_STAR - 2, hi_log_s=LOG_S_STAR + 2),
        fit_id="cov-rt",
    )
    rt = calibration_from_json(cal.to_json())
    assert isinstance(rt, CovariateCalibration)
    np.testing.assert_array_equal(
        cal.sqrt_s_at(_LONS, _LATS), rt.sqrt_s_at(_LONS, _LATS)
    )


# ---------------------------------------------------------------------------
# Cross-kind: key/roundtrip covers all four kinds
# ---------------------------------------------------------------------------


def test_key_changes_with_every_param() -> None:
    """Perturbing any coeff, clip bound, or fit_id changes key().

    Bug caught: cache collisions between distinct calibrations.
    """
    # Scalar
    assert ScalarCalibration(s=1.0).key() != ScalarCalibration(s=2.0).key()
    # Poly (covered in detail above)
    p1 = PolyCalibration(coeffs=(1.0, 0.0, 0.0, 0.0, 0.0), clip=_CLIP, fit_id="a")
    p2 = PolyCalibration(coeffs=(1.0, 0.0, 0.0, 0.0, 0.0), clip=_CLIP, fit_id="b")
    assert p1.key() != p2.key()
    # Piecewise
    pw1 = _make_piecewise(fit_id="x")
    pw2 = _make_piecewise(fit_id="y")
    assert pw1.key() != pw2.key()
    # Covariate
    proxy = _make_proxy_cells()
    clip = _CLIP
    cv1 = CovariateCalibration(proxy_cells=proxy, a=1.0, b=0.5, clip=clip, fit_id="cv1")
    cv2 = CovariateCalibration(proxy_cells=proxy, a=1.0, b=0.5, clip=clip, fit_id="cv2")
    assert cv1.key() != cv2.key()


def test_json_roundtrip_bitexact() -> None:
    """from_json(to_json(f)) reproduces sqrt_s_at bit-identically on a grid.

    Bug caught: kind discriminator missing, wrong class reconstructed.
    """
    cals: list[CalibrationField] = [
        ScalarCalibration(s=S_STAR),
        PolyCalibration(
            coeffs=(LOG_S_STAR, 0.1, -0.1, 0.05, -0.05),
            clip=_CLIP,
            fit_id="poly-rt",
        ),
        _make_piecewise(fit_id="pw-rt"),
        CovariateCalibration(
            proxy_cells=_make_proxy_cells(fill=3.0),
            a=LOG_S_STAR,
            b=0.2,
            clip=_CLIP,
            fit_id="cov-rt",
        ),
    ]
    for cal in cals:
        rt = calibration_from_json(cal.to_json())
        assert type(rt) is type(cal), (
            f"Wrong type after roundtrip: {type(rt)} != {type(cal)}"
        )
        np.testing.assert_array_equal(
            cal.sqrt_s_at(_LONS, _LATS),
            rt.sqrt_s_at(_LONS, _LATS),
            err_msg=f"sqrt_s_at mismatch after roundtrip for {type(cal).__name__}",
        )
