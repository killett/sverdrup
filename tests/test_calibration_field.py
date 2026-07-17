"""Tests for the CalibrationField hierarchy (Phase 8, Task 2).

All four lanes: ScalarCalibration, PiecewiseCalibration, PolyCalibration,
CovariateCalibration.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from sverdrup.application.calibration.constants import CLIP_PAD, S_STAR
from sverdrup.distributions.calibration import (
    CalibratedDistribution,
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

    Bug caught: a wrong log->sqrt link (e.g. exp(log s) instead of
    exp(0.5*log s)) or a stray offset term. The spatial coeffs are zero, so
    (u, v) normalization is NOT exercised here (the clamp/quadrant tests
    cover it with nonzero coeffs).
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
    """a + b*log(proxy) with proxy=1.0 gives log s = a everywhere (log(1)=0).

    b=1.5 is deliberately nonzero, so any spurious contribution from the
    proxy term (wrong log base, proxy used un-logged) shifts the result.
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


def test_all_kinds_hashable() -> None:
    """hash(f) must work for every kind (Task-3 per-grid cache keys on it).

    Bug caught: a mutable dict field makes the generated __hash__ raise
    TypeError, breaking any dict/set keyed on the calibration instance.
    """
    cals: list[CalibrationField] = [
        ScalarCalibration(s=S_STAR),
        PolyCalibration(
            coeffs=(LOG_S_STAR, 0.1, -0.1, 0.05, -0.05),
            clip=_CLIP,
            fit_id="hash-poly",
        ),
        _make_piecewise(fit_id="hash-pw"),
        CovariateCalibration(
            proxy_cells=_make_proxy_cells(fill=3.0),
            a=LOG_S_STAR,
            b=0.2,
            clip=_CLIP,
            fit_id="hash-cov",
        ),
    ]
    for cal in cals:
        assert isinstance(hash(cal), int), f"unhashable: {type(cal).__name__}"


def test_piecewise_region_values_immutable() -> None:
    """Region values must not be mutable in place after construction.

    Bug caught: dict-backed storage lets `pw.log_s_by_region["SW"] = 9.9`
    silently invalidate the __post_init__ clip-bounds guarantee.
    """
    pw = _make_piecewise()
    with pytest.raises(TypeError):
        pw.log_s_by_region["SW"] = 9.9  # type: ignore[index]


def test_piecewise_key_changes_with_mask_cell() -> None:
    """Flipping one mask cell must change PiecewiseCalibration.key().

    Bug caught: mask omitted from key -> cache collision between two
    calibrations differing only in jet-core extent.
    """
    k0 = _make_piecewise().key()
    mask_list = [[False] * 5 for _ in range(5)]
    mask_list[2][3] = True
    flipped: tuple[tuple[bool, ...], ...] = tuple(tuple(r) for r in mask_list)
    assert _make_piecewise(mask=flipped).key() != k0


def test_covariate_key_changes_with_proxy_cell() -> None:
    """Perturbing one proxy_cells entry must change CovariateCalibration.key().

    Bug caught: proxy grid omitted from key -> cache collision between two
    covariate calibrations fit to different proxy fields.
    """
    proxy_list = [[2.0] * 5 for _ in range(5)]
    base = CovariateCalibration(
        proxy_cells=tuple(tuple(r) for r in proxy_list),
        a=LOG_S_STAR,
        b=0.5,
        clip=_CLIP,
        fit_id="pk",
    )
    proxy_list[3][1] = 2.001
    perturbed = CovariateCalibration(
        proxy_cells=tuple(tuple(r) for r in proxy_list),
        a=LOG_S_STAR,
        b=0.5,
        clip=_CLIP,
        fit_id="pk",
    )
    assert base.key() != perturbed.key()


def test_covariate_nonpositive_proxy_raises() -> None:
    """A non-positive proxy cell must raise ValueError at construction.

    Bug caught: silent NaN/-inf from log(proxy) at query time — the proxy
    is a std and must be strictly positive; fail loudly at build instead.
    """
    for bad in (0.0, -1.0):
        proxy_list = [[2.0] * 5 for _ in range(5)]
        proxy_list[4][4] = bad
        with pytest.raises(ValueError, match="[Pp]roxy|positive"):
            CovariateCalibration(
                proxy_cells=tuple(tuple(r) for r in proxy_list),
                a=LOG_S_STAR,
                b=0.5,
                clip=_CLIP,
                fit_id="bad-proxy",
            )


# ---------------------------------------------------------------------------
# Numpy-repr pollution: coercion of np.float64 inputs to builtin float
# ---------------------------------------------------------------------------
# Bug: constructing any calibration class from numpy scalar inputs causes
# key() to emit "np.float64(...)" repr strings.  After to_json()/from_json(),
# all numerics are plain Python float, so calibration_from_json(f.to_json()).key()
# != f.key() — the identity round-trip breaks.  __post_init__ must coerce
# every numeric field to builtin float so key() is self-consistent regardless
# of whether the caller passed np.float64 or float.


def test_scalar_numpy_input_key_no_np_float64() -> None:
    """ScalarCalibration built from np.float64 must not emit 'np.float64' in key().

    Bug caught: key() uses {self.s!r} → repr(np.float64(x)) = 'np.float64(x)'
    so persisted cal_key does not round-trip via calibration_from_json.
    """
    s_np = np.float64(S_STAR)
    cal = ScalarCalibration(s=s_np)
    assert "np.float64" not in cal.key(), f"numpy repr leaked into key(): {cal.key()}"
    rt = calibration_from_json(cal.to_json())
    assert rt.key() == cal.key(), (
        f"key self-consistency broken:\n  original: {cal.key()}\n  roundtrip: {rt.key()}"
    )
    assert isinstance(hash(cal), int)


def test_poly_numpy_input_key_no_np_float64() -> None:
    """PolyCalibration built from a numpy array must not emit 'np.float64' in key().

    Bug caught: tuple(theta) where theta is np.ndarray produces a tuple of
    np.float64; {self.coeffs!r} → "(np.float64(x), ...)" in key().
    """
    theta = np.array([LOG_S_STAR, 0.3, -0.1, 0.05, -0.02])
    clip = ClipSpec(
        lo_log_s=np.float64(CLIP_LO),
        hi_log_s=np.float64(CLIP_HI),
    )
    cal = PolyCalibration(coeffs=tuple(theta), clip=clip, fit_id="np-test")
    key = cal.key()
    assert "np.float64" not in key, f"numpy repr leaked into key(): {key}"
    rt = calibration_from_json(cal.to_json())
    assert rt.key() == key, (
        f"key self-consistency broken:\n  original: {key}\n  roundtrip: {rt.key()}"
    )
    assert isinstance(hash(cal), int)


def test_piecewise_numpy_input_key_no_np_float64() -> None:
    """PiecewiseCalibration built from numpy scalars must not emit 'np.float64'.

    Bug caught: region values or lon_mid/lat_mid stored as np.float64 leak
    into the key via !r formatting.
    """
    regions = {k: np.float64(v) for k, v in _ALL_STAR_PIECEWISE.items()}
    clip = ClipSpec(
        lo_log_s=np.float64(CLIP_LO),
        hi_log_s=np.float64(CLIP_HI),
    )
    cal = PiecewiseCalibration(
        lon_mid=np.float64(300.0),
        lat_mid=np.float64(38.0),
        mask=_NO_JET_MASK,
        log_s_by_region=regions,
        clip=clip,
        fit_id="np-pw",
    )
    key = cal.key()
    assert "np.float64" not in key, f"numpy repr leaked into key(): {key}"
    rt = calibration_from_json(cal.to_json())
    assert rt.key() == key, (
        f"key self-consistency broken:\n  original: {key}\n  roundtrip: {rt.key()}"
    )
    assert isinstance(hash(cal), int)


def test_covariate_numpy_input_key_no_np_float64() -> None:
    """CovariateCalibration built from numpy scalars must not emit 'np.float64'.

    Bug caught: a, b stored as np.float64 leak into key via {self.a!r};
    proxy_cells entries stored as np.float64 also appear in key via !r.
    """
    proxy_np = tuple(
        tuple(np.float64(r * 5 + c + 1.0) for c in range(5)) for r in range(5)
    )
    clip = ClipSpec(
        lo_log_s=np.float64(CLIP_LO),
        hi_log_s=np.float64(CLIP_HI),
    )
    cal = CovariateCalibration(
        proxy_cells=proxy_np,
        a=np.float64(LOG_S_STAR),
        b=np.float64(0.25),
        clip=clip,
        fit_id="np-cov",
    )
    key = cal.key()
    assert "np.float64" not in key, f"numpy repr leaked into key(): {key}"
    rt = calibration_from_json(cal.to_json())
    assert rt.key() == key, (
        f"key self-consistency broken:\n  original: {key}\n  roundtrip: {rt.key()}"
    )
    assert isinstance(hash(cal), int)


def test_clipspec_numpy_input_no_np_float64() -> None:
    """ClipSpec built from np.float64 must coerce to builtin float.

    Bug caught: ClipSpec(lo_log_s=np.float64(...)) stores numpy scalar so
    PolyCalibration.key() emits 'np.float64(...)' for the clip bounds.
    """
    clip = ClipSpec(
        lo_log_s=np.float64(CLIP_LO),
        hi_log_s=np.float64(CLIP_HI),
    )
    assert isinstance(clip.lo_log_s, float), (
        f"lo_log_s is {type(clip.lo_log_s).__name__}, expected float"
    )
    assert isinstance(clip.hi_log_s, float), (
        f"hi_log_s is {type(clip.hi_log_s).__name__}, expected float"
    )
    # Confirm no numpy repr in downstream key
    cal = PolyCalibration(
        coeffs=(LOG_S_STAR, 0.0, 0.0, 0.0, 0.0),
        clip=clip,
        fit_id="cs-np",
    )
    assert "np.float64" not in cal.key()


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


# ---------------------------------------------------------------------------
# Task 3: eval-time √s(x) seam in MiostEnsembleDistribution
# ---------------------------------------------------------------------------
#
# One general query-time √s(x) application at the two row-scaling sites
# (_anoms_at for arbitrary points; the anomaly term of the grid paths). The
# mean paths must stay BIT-UNTOUCHED (the D6 property the whole phase leans
# on); correlations are preserved exactly; variance scales pointwise by s(x).

from sverdrup.core.grid import GridSpec  # noqa: E402
from sverdrup.core.observations import (  # noqa: E402
    DiagonalErrorModel,
    ObsWindow,
)
from sverdrup.core.parameters import ConstantProvider  # noqa: E402
from sverdrup.distributions.miost_ensemble import (  # noqa: E402
    MiostEnsembleDistribution,
)
from sverdrup.methods.miost import Miost  # noqa: E402
from sverdrup.methods.miost_windows import WindowPlan  # noqa: E402

# WIDE clip: bounds far enough apart that no positive field ever engages the
# clamp — isolates the seam wiring from the clip machinery.
WIDE = ClipSpec(lo_log_s=-100.0, hi_log_s=100.0)

_SEAM_M = 6
_SEAM_DAY = 50.0  # inside the [45, 60] blend zone of the two-window plan
_SEAM_ROOT = 12345
_SEAM_PARAMS = ConstantProvider(
    {"spacing_alpha": 1.5, "log10_rho": 1.3, "q_slope": 2.0, "l_t_days": 10.0}
)
_SEAM_GRID = GridSpec.lonlat(np.linspace(296.0, 304.0, 7), np.linspace(34.0, 42.0, 7))


def _seam_obs(n: int = 80) -> ObsWindow:
    rng = np.random.default_rng(7)
    t = rng.uniform(-12.0, 117.0, n)  # spans both windows' +-L_t support
    err = DiagonalErrorModel(np.full(n, 0.01))
    mission = np.asarray(["alg", "s3a", "h2g", "j2n"])[rng.integers(0, 4, n)]
    return ObsWindow.from_arrays(
        rng.uniform(296, 304, n),
        rng.uniform(34, 42, n),
        t,
        rng.standard_normal(n) * 0.1,
        err,
        mission,
    )


def _seam_method() -> Miost:
    return Miost(plan=WindowPlan(starts=(0.0, 45.0)))


@pytest.fixture(scope="module")
def dist() -> CalibratedDistribution:
    return _seam_method().sample_members(
        _seam_obs(), _SEAM_GRID, _SEAM_PARAMS, _SEAM_DAY, m=_SEAM_M, root=_SEAM_ROOT
    )


def test_correlation_preserved_under_nonconstant_field(
    dist: CalibratedDistribution,
) -> None:
    """Corr' == Corr exactly under a non-constant positive field.

    Bug caught: scaling applied after centering, or one covariance side only.
    """
    field = PolyCalibration(coeffs=(0.5, 0.8, 0.0, 0.3, 0.0), clip=WIDE, fit_id="t")
    a = np.array([[296.0, 34.0, 5.0], [303.0, 42.0, 5.0], [300.0, 38.0, 5.0]])
    c0 = dist.covariance(a, a)
    c1 = dist.with_calibration(field).covariance(a, a)
    d0, d1 = np.sqrt(np.diag(c0)), np.sqrt(np.diag(c1))
    np.testing.assert_allclose(c1 / np.outer(d1, d1), c0 / np.outer(d0, d0), rtol=1e-12)


def test_magnitude_marginal_variance_scales_pointwise(
    dist: CalibratedDistribution,
) -> None:
    """var'(x) == s(x) · var(x) node-by-node on the grid, analytic.

    Bug caught: any positive-but-wrong power of s (s, s², √s) — the
    correlation test is blind to this by design (spec §2 note).
    """
    field = PolyCalibration(coeffs=(0.2, 0.6, -0.3, 0.1, 0.0), clip=WIDE, fit_id="t")
    v0 = dist.marginal_variance()
    v1 = dist.with_calibration(field).marginal_variance()
    lon2d, lat2d = np.meshgrid(dist.grid.x, dist.grid.y)
    s = np.exp(field.log_s_at(lon2d.ravel(), lat2d.ravel())).reshape(v0.shape)
    np.testing.assert_allclose(v1, s * v0, rtol=1e-12)


def test_rescaled_composition_multiplicative(
    dist: CalibratedDistribution,
) -> None:
    """rescaled(4).rescaled(9) variance == 36 × base variance (rtol 1e-12)."""
    composed = dist.rescaled(4.0).rescaled(9.0)
    np.testing.assert_allclose(
        composed.marginal_variance(),
        36.0 * dist.marginal_variance(),
        rtol=1e-12,
    )
    # A single rescaled(36) is the same variance — the multiplicative law.
    np.testing.assert_allclose(
        composed.marginal_variance(),
        dist.rescaled(36.0).marginal_variance(),
        rtol=1e-12,
    )


def test_rescaled_raises_on_field_calibrated(
    dist: CalibratedDistribution,
) -> None:
    """rescaled(s) on a field-calibrated product raises ValueError.

    Bug caught: silent scalar-on-field corruption (owner narrowing).
    """
    field = PolyCalibration(coeffs=(0.2, 0.6, -0.3, 0.1, 0.0), clip=WIDE, fit_id="t")
    calibrated = dist.with_calibration(field)
    with pytest.raises(ValueError, match="field-calibrated"):
        calibrated.rescaled(2.0)


def test_no_stale_sqrt_s_cache(dist: CalibratedDistribution) -> None:
    """with_calibration returns a fresh instance; the original's grid
    queries are unchanged after the derived instance is queried.

    Bug caught: per-grid √s cache shared across calibrations.
    """
    field = PolyCalibration(coeffs=(0.2, 0.6, -0.3, 0.1, 0.0), clip=WIDE, fit_id="t")
    v_before = dist.marginal_variance().copy()
    derived = dist.with_calibration(field)
    _ = derived.marginal_variance()  # populates the derived instance's cache
    v_after = dist.marginal_variance()
    np.testing.assert_array_equal(v_after, v_before)
    # And the derived instance is a genuinely fresh object.
    assert derived is not dist


def test_field_inert_beyond_box_halo(dist: CalibratedDistribution) -> None:
    """Beyond box+halo, calibrated marginal stats equal uncalibrated to
    machine precision (anomalies ~0 there; spec §9 inertness pin).

    Constructed with one in-box node (so the sparse S-path has support and
    builds) plus far nodes well outside the observation footprint, where the
    blended member anomalies are EXACTLY zero — so √s·0 == 0 for any field.
    """
    mixed_grid = GridSpec.lonlat(
        np.array([300.0, 340.0, 350.0]), np.array([38.0, 80.0, 85.0])
    )
    mixed = _seam_method().sample_members(
        _seam_obs(), mixed_grid, _SEAM_PARAMS, _SEAM_DAY, m=_SEAM_M, root=_SEAM_ROOT
    )
    field = PolyCalibration(coeffs=(0.5, 0.8, 0.0, 0.3, 0.0), clip=WIDE, fit_id="t")
    v0 = mixed.marginal_variance()
    v1 = mixed.with_calibration(field).marginal_variance()
    far = v0.ravel() < 1e-20  # the out-of-footprint nodes (anomalies ~0)
    assert far.sum() >= 4, "fixture must contain several out-of-footprint nodes"
    np.testing.assert_array_equal(v1.ravel()[far], v0.ravel()[far])


def test_mean_untouched_by_field(dist: CalibratedDistribution) -> None:
    """mean_at under any field is the SAME ARRAY VALUES as uncalibrated
    (bitwise equal) — the D6 property the whole phase leans on.
    """
    field = PolyCalibration(coeffs=(0.5, 0.8, 0.0, 0.3, 0.0), clip=WIDE, fit_id="t")
    pts = np.array([[298.0, 36.0, _SEAM_DAY], [301.0, 40.0, _SEAM_DAY]])
    m0 = dist.mean_at(pts)
    m1 = dist.with_calibration(field).mean_at(pts)
    np.testing.assert_array_equal(m0, m1)
    # The analytic mean path over grid nodes is likewise bit-untouched
    # (the member SAMPLE mean is not — see NOTE below).
    field_grid = PolyCalibration(
        coeffs=(0.2, 0.6, -0.3, 0.1, 0.0), clip=WIDE, fit_id="t"
    )
    # NOTE: sample mean of members shifts under a field (variance scales), so
    # compare the analytic mean field, not the member mean. Use mean_at on grid
    # nodes to assert bit-identity of the mean path.
    lon2d, lat2d = np.meshgrid(dist.grid.x, dist.grid.y)
    day = np.full(lon2d.size, _SEAM_DAY)
    gpts = np.column_stack([lon2d.ravel(), lat2d.ravel(), day])
    gm0 = dist.mean_at(gpts)
    gm1 = dist.with_calibration(field_grid).mean_at(gpts)
    np.testing.assert_array_equal(gm0, gm1)


# ---------------------------------------------------------------------------
# Task 4: field persistence + FIELD_INFLATION provenance + factory boundary
# ---------------------------------------------------------------------------

from pathlib import Path  # noqa: E402

from sverdrup.core.provenance import TransformKind  # noqa: E402
from sverdrup.distributions.miost_ensemble import KIND  # noqa: E402

_GRID_LONS = np.array([296.0, 300.0, 304.0])
_GRID_LATS = np.array([34.0, 38.0, 42.0])


def _all_field_kinds() -> list[CalibrationField]:
    """One instance of every kind, with distinctive non-default params."""
    return [
        ScalarCalibration(s=S_STAR),
        PolyCalibration(
            coeffs=(LOG_S_STAR, 0.3, -0.2, 0.1, 0.05), clip=_CLIP, fit_id="p4"
        ),
        _make_piecewise(fit_id="pw4"),
        CovariateCalibration(
            proxy_cells=tuple(
                tuple(1.0 + 0.1 * (r + c) for c in range(5)) for r in range(5)
            ),
            a=LOG_S_STAR,
            b=0.5,
            clip=_CLIP,
            fit_id="cv4",
        ),
    ]


@pytest.mark.parametrize("cal", _all_field_kinds(), ids=lambda c: type(c).__name__)
def test_persistence_roundtrip_all_field_kinds(
    cal: CalibrationField, dist: CalibratedDistribution, tmp_path: Path
) -> None:
    """save→load reconstructs the calibration bit-exactly (sqrt_s + key).

    Bug caught: save_state dropping the calibration (round-trip resets to
    ScalarCalibration(1.0)) — the Task-3 persistence gap — or reconstructing a
    different field kind/params.
    """
    calibrated = dist.with_calibration(cal)
    p = tmp_path / "cal.npz"
    calibrated.save_state(p)
    # Phase-9 §3: cal keys live on the wrapper — reload through it (the raw
    # class loads arrays only; the wrapper's load_state reads the cal keys).
    back = CalibratedDistribution.load_state(p, MiostEnsembleDistribution.load_state(p))
    lon2d, lat2d = np.meshgrid(_GRID_LONS, _GRID_LATS)
    np.testing.assert_array_equal(
        back.calibration.sqrt_s_at(lon2d.ravel(), lat2d.ravel()),
        cal.sqrt_s_at(lon2d.ravel(), lat2d.ravel()),
    )
    assert back.calibration.key() == cal.key()


def test_legacy_load_without_cal_keys_is_scalar_one(
    dist: CalibratedDistribution, tmp_path: Path
) -> None:
    """A state file with NO cal_* keys loads as ScalarCalibration(1.0).

    The factory supplies s* (spec §8): the persisted anomalies are RAW, so a
    legacy (pre-Phase-8) file must reload uncalibrated, not crash or invent s.

    Bug caught: load_state KeyError-ing on absent cal keys, or defaulting to a
    non-unit scale that would double-apply s* downstream.
    """
    p = tmp_path / "ens_legacy.npz"
    dist.save_state(p)
    # Strip the cal_* keys to emulate a pre-Phase-8 file.
    with np.load(p) as z:
        arrays = {k: z[k] for k in z.files if not k.startswith("cal_")}
    np.savez(p, **arrays)
    with np.load(p) as z:
        assert not any(k.startswith("cal_") for k in z.files)
    # Phase-9 §3: the legacy rule lives on the wrapper's load_state.
    back = CalibratedDistribution.load_state(p, MiostEnsembleDistribution.load_state(p))
    assert back.calibration == ScalarCalibration(1.0)


@pytest.mark.parametrize(
    ("cal", "expected_dof", "expected_kind"),
    [
        (
            PolyCalibration(
                coeffs=(LOG_S_STAR, 0.3, -0.2, 0.1, 0.05), clip=_CLIP, fit_id="p4"
            ),
            5,
            "poly",
        ),
        (_make_piecewise(fit_id="pw4"), 5, "piecewise"),
        (
            CovariateCalibration(
                proxy_cells=tuple(
                    tuple(1.0 + 0.1 * (r + c) for c in range(5)) for r in range(5)
                ),
                a=LOG_S_STAR,
                b=0.5,
                clip=_CLIP,
                fit_id="cv4",
            ),
            2,
            "covariate",
        ),
    ],
    ids=["poly", "piecewise", "covariate"],
)
def test_field_inflation_provenance_carries_key_kind_dof(
    cal: CalibrationField,
    expected_dof: int,
    expected_kind: str,
    dist: CalibratedDistribution,
) -> None:
    """Non-scalar calibration records a FIELD_INFLATION transform with metadata.

    Bug caught: a field calibration recorded as DIAGONAL_INFLATION (an auditor
    could not tell a spatial field from a scalar), or a wrong/absent dof (poly
    5, piecewise = #regions, covariate 2).
    """
    prov = dist.with_calibration(cal).provenance
    last = prov.transformations[-1]
    assert last.kind is TransformKind.FIELD_INFLATION
    assert last.params["calibration_key"] == cal.key()
    assert last.params["cal_kind"] == expected_kind
    assert last.params["dof"] == expected_dof


def test_scalar_calibration_keeps_diagonal_inflation(
    dist: CalibratedDistribution,
) -> None:
    """Scalar calibration keeps DIAGONAL_INFLATION with params['s'] EXACTLY.

    Bug caught: the FIELD_INFLATION change leaking onto the scalar path,
    breaking every existing gate-s* provenance assertion.
    """
    prov = dist.with_calibration(ScalarCalibration(3.0)).provenance
    last = prov.transformations[-1]
    assert last.kind is TransformKind.DIAGONAL_INFLATION
    assert last.params["s"] == 3.0


def test_rescaled_records_incremental_factor(
    dist: CalibratedDistribution,
) -> None:
    """Composed rescales record the INCREMENTAL factor, not the cumulative s.

    Starting from a scalar-4 base, rescaled(9) must record s=9 (the increment),
    matching pre-Phase-8 semantics — NOT s=36 (the cumulative product).

    Bug caught: provenance recording ``self.calibration.s * s`` (cumulative),
    which would misreport each inflation step to a downstream auditor.
    """
    base4 = dist.with_calibration(ScalarCalibration(4.0))
    composed = base4.rescaled(9.0)
    # Variance is cumulative (36×) — the composition law is unchanged.
    np.testing.assert_allclose(
        composed.marginal_variance(),
        36.0 * dist.marginal_variance(),
        rtol=1e-12,
    )
    # But the LAST recorded transform is the incremental factor, s=9.
    last = composed.provenance.transformations[-1]
    assert last.kind is TransformKind.DIAGONAL_INFLATION
    assert last.params["s"] == 9.0


def test_load_state_kind_tag_still_refused(tmp_path: Path) -> None:
    """load_state still refuses a non-ensemble npz even with cal keys present.

    Bug caught: the cal-key additions loosening the kind-tag guard so a
    foreign npz (with a cal_kind but wrong kind) is silently accepted.
    """
    p = tmp_path / "wrong.npz"
    np.savez(p, kind="something-else", cal_kind="scalar")
    with pytest.raises(ValueError, match=KIND):
        MiostEnsembleDistribution.load_state(p)


def test_factory_bytecompat_sigma(tmp_path: Path) -> None:
    """Current factory-path σ/mean/cov match the pre-seam snapshot at rtol 1e-12.

    The fixture was captured through the shipped factory config at commit
    3f88ccb (pre-Task-3), where inflation_s was applied by the old
    ens.rescaled path. The current seam must reproduce those numbers bitwise
    to rtol 1e-12.

    Bug caught: the Task-3 eval-time √s seam shifting the σ the shipped factory
    produces (a silent recalibration of the shipped product).
    """
    from sverdrup.core.observations import DiagonalErrorModel
    from sverdrup.methods.miost import STAGE_B_INFLATION_S

    fixture = (
        Path(__file__).resolve().parent / "fixtures" / "phase8_factory_bytecompat.npz"
    )
    with np.load(fixture) as z:
        probe_pts = z["probe_pts"]
        exp_mean = z["mean"]
        exp_std = z["std"]
        exp_cov = z["cov_block"]
        grid_lon = z["grid_lon"]
        grid_lat = z["grid_lat"]
        m = int(z["m"])
        day = float(z["day"])
        root = int(z["root"])
        s_star = float(z["inflation_s"])

    assert s_star == STAGE_B_INFLATION_S
    grid = GridSpec.lonlat(grid_lon, grid_lat)
    params = ConstantProvider(
        {"spacing_alpha": 1.5, "log10_rho": 1.3, "q_slope": 2.0, "l_t_days": 10.0}
    )
    rng = np.random.default_rng(7)
    n = 80
    t = rng.uniform(-12.0, 117.0, n)
    err = DiagonalErrorModel(np.full(n, 0.01))
    mission = np.asarray(["alg", "s3a", "h2g", "j2n"])[rng.integers(0, 4, n)]
    obs = ObsWindow.from_arrays(
        rng.uniform(296, 304, n),
        rng.uniform(34, 42, n),
        t,
        rng.standard_normal(n) * 0.1,
        err,
        mission,
    )
    method = Miost(
        plan=WindowPlan(starts=(0.0, 45.0)),
        members=m,
        member_root=root,
        inflation_s=s_star,
    )
    dist = method.solve(obs, grid, params, day)
    cov = np.asarray(dist.covariance(probe_pts, probe_pts))
    std = np.sqrt(np.diag(cov))
    np.testing.assert_allclose(
        np.asarray(dist.mean_at(probe_pts)), exp_mean, rtol=1e-12
    )
    np.testing.assert_allclose(std, exp_std, rtol=1e-12)
    np.testing.assert_allclose(cov, exp_cov, rtol=1e-12)


# ---------------------------------------------------------------------------
# Phase-9 Task 1: PIN C — cal_key byte-stability across the module move
# ---------------------------------------------------------------------------


def test_moved_code_reproduces_shipped_cal_key_bytes() -> None:
    """The module move must not change key() output for the SHIPPED field.

    Bug caught: key() accidentally hashing module paths/reprs that change
    with the move (PIN C) — the gate runner asserts this exact key.
    """
    import json
    from pathlib import Path

    from sverdrup.distributions.calibration import calibration_from_json

    art = Path("data/2021a_ssh_mapping_ose/ours/phase8_field.json")
    if not art.exists():
        pytest.skip("shipped field artifact absent")
    d = json.loads(art.read_text())
    assert calibration_from_json(d["calibration"]).key() == d["cal_key"]
