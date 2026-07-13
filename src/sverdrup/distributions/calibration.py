"""Shared CalibrationField hierarchy — shared home, Phase-9 §2.

Moved verbatim from miost_ensemble.py — pre-registered code, do not edit
in transit.

Contains the four calibration field classes, helpers, box constants, and the
JSON dispatcher used by the MIOST ensemble distribution and all callers.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np

# ---------------------------------------------------------------------------
# Phase-8 CalibrationField hierarchy (Task 2)
# ---------------------------------------------------------------------------
#
# Box constants (lon ∈ [295, 305], lat ∈ [33, 43]).
# 2°-cell grid: lon edges 295, 297, …, 305; lat edges 33, 35, …, 43 → 5×5 cells.

BOX_LON: tuple[float, float] = (295.0, 305.0)
BOX_LAT: tuple[float, float] = (33.0, 43.0)

_LON_EDGES: np.ndarray = np.arange(295.0, 305.0 + 2.0, 2.0)
_LAT_EDGES: np.ndarray = np.arange(33.0, 43.0 + 2.0, 2.0)


def _clamp_hull(lon: np.ndarray, lat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Clamp coordinates to the box hull (spec §9 constant continuation).

    Args:
        lon: Longitude array [deg east].
        lat: Latitude array [deg north].

    Returns:
        (lon_clamped, lat_clamped) arrays clipped to [295, 305] × [33, 43].
    """
    return (
        np.clip(np.asarray(lon, float), *BOX_LON),
        np.clip(np.asarray(lat, float), *BOX_LAT),
    )


def _cell_index(lon: np.ndarray, lat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (row, col) 2°-cell indices, clipped to [0, 4]×[0, 4].

    Local twin of the canonical ``application.calibration.regions.cell_index``
    (kept here so the distribution layer does not import the application
    layer). Any change to the 2°-grid convention must touch BOTH — they are
    output-identical by construction (searchsorted-right, clip 0..4).

    Args:
        lon: Longitudes [deg east] — already clamped to hull.
        lat: Latitudes [deg north] — already clamped to hull.

    Returns:
        (row, col) integer arrays each in [0, 4].
    """
    col = np.clip(np.searchsorted(_LON_EDGES, lon, side="right") - 1, 0, 4)
    row = np.clip(np.searchsorted(_LAT_EDGES, lat, side="right") - 1, 0, 4)
    return row.astype(int), col.astype(int)


@dataclass(frozen=True)
class ClipSpec:
    """Pre-registered log-s clip bounds (spec §9; evidence-anchored).

    Attributes:
        lo_log_s: Lower bound on log(s).
        hi_log_s: Upper bound on log(s).
    """

    lo_log_s: float
    hi_log_s: float

    def __post_init__(self) -> None:
        """Coerce bounds to builtin float.

        Bug guarded: ClipSpec built from np.float64 inputs (e.g. numpy
        min/max computations in refit_winner) stores numpy scalars so
        downstream key() calls emit 'np.float64(...)' repr strings,
        breaking cal_key self-consistency after JSON round-trip.
        """
        object.__setattr__(self, "lo_log_s", float(self.lo_log_s))
        object.__setattr__(self, "hi_log_s", float(self.hi_log_s))


@dataclass(frozen=True)
class ScalarCalibration:
    """Constant s — the shipped-scalar limit of the field layer.

    Clip-free by spec: the global scalar needs no spatial clamp.

    Attributes:
        s: Scale factor value (positive float).
    """

    s: float

    def __post_init__(self) -> None:
        """Coerce s to builtin float.

        Bug guarded: ScalarCalibration(s=np.float64(...)) stores a numpy
        scalar so key() emits 'np.float64(...)' via {self.s!r}, breaking
        cal_key self-consistency after JSON round-trip.
        """
        object.__setattr__(self, "s", float(self.s))

    def log_s_at(self, lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
        """Return log(s) as a broadcast-shaped constant array.

        Args:
            lon: Longitude array [deg east].
            lat: Latitude array [deg north].

        Returns:
            Array of shape broadcast(lon, lat).shape filled with log(s).
        """
        return np.full(np.broadcast(lon, lat).shape, math.log(self.s))

    def sqrt_s_at(self, lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
        """Return sqrt(s) as a broadcast-shaped constant array.

        Args:
            lon: Longitude array [deg east].
            lat: Latitude array [deg north].

        Returns:
            Array of shape broadcast(lon, lat).shape filled with sqrt(s).
        """
        return np.full(np.broadcast(lon, lat).shape, math.sqrt(self.s))

    def key(self) -> str:
        """Return a deterministic string key for this calibration.

        Returns:
            String encoding kind and s value.
        """
        return f"cal:scalar;s={self.s!r}"

    def to_json(self) -> dict[str, Any]:
        """Serialise to a JSON-compatible dict with a kind discriminator.

        Returns:
            Dict with keys ``kind`` and ``s``.
        """
        return {"kind": "scalar", "s": float(self.s)}

    @classmethod
    def from_json(cls, d: dict[str, Any]) -> ScalarCalibration:
        """Reconstruct from a serialised dict.

        Args:
            d: Dict produced by :meth:`to_json`.

        Returns:
            Reconstructed ScalarCalibration.
        """
        return cls(s=float(d["s"]))


@dataclass(frozen=True)
class PolyCalibration:
    """log s = a0 + a1·v + a2·v² + a3·u + a4·u·v.

    Normalised coordinates: u = (lon − 300) / 5, v = (lat − 38) / 5,
    both in [−1, 1] over the box.  Coordinates outside the box are
    clamped to the hull before evaluation (constant continuation).

    Attributes:
        coeffs: (a0, a1, a2, a3, a4) polynomial coefficients.
        clip: Pre-registered log-s clip bounds.
        fit_id: Identifier of the fitting run that produced these coefficients.
    """

    coeffs: tuple[float, float, float, float, float]
    clip: ClipSpec
    fit_id: str

    def __post_init__(self) -> None:
        """Coerce coeffs to a tuple of builtin floats.

        Bug guarded: PolyCalibration(coeffs=tuple(numpy_array), ...) stores
        a tuple of np.float64 so key() emits 'np.float64(...)' via
        {self.coeffs!r}, breaking cal_key self-consistency after JSON
        round-trip.
        """
        object.__setattr__(self, "coeffs", tuple(float(c) for c in self.coeffs))

    def log_s_at(self, lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
        """Return clipped log(s) at the given locations.

        Args:
            lon: Longitude array [deg east].
            lat: Latitude array [deg north].

        Returns:
            log(s) array, clipped to [clip.lo_log_s, clip.hi_log_s].
        """
        lo, la = _clamp_hull(lon, lat)
        u = (lo - 300.0) / 5.0
        v = (la - 38.0) / 5.0
        a0, a1, a2, a3, a4 = self.coeffs
        raw = a0 + a1 * v + a2 * v * v + a3 * u + a4 * u * v
        return np.clip(raw, self.clip.lo_log_s, self.clip.hi_log_s)

    def sqrt_s_at(self, lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
        """Return sqrt(s) at the given locations.

        Args:
            lon: Longitude array [deg east].
            lat: Latitude array [deg north].

        Returns:
            sqrt(s) = exp(0.5 * log_s_at(lon, lat)).
        """
        return np.exp(0.5 * self.log_s_at(lon, lat))

    def key(self) -> str:
        """Return a deterministic string key for this calibration.

        Returns:
            String encoding kind, coefficients, clip bounds, and fit_id.
        """
        return (
            f"cal:poly;coeffs={self.coeffs!r};"
            f"clip=({self.clip.lo_log_s!r},{self.clip.hi_log_s!r});"
            f"fit={self.fit_id}"
        )

    def to_json(self) -> dict[str, Any]:
        """Serialise to a JSON-compatible dict with a kind discriminator.

        Returns:
            Dict with keys ``kind``, ``coeffs``, ``clip``, ``fit_id``.
        """
        return {
            "kind": "poly",
            "coeffs": list(self.coeffs),
            "clip": {
                "lo_log_s": self.clip.lo_log_s,
                "hi_log_s": self.clip.hi_log_s,
            },
            "fit_id": self.fit_id,
        }

    @classmethod
    def from_json(cls, d: dict[str, Any]) -> PolyCalibration:
        """Reconstruct from a serialised dict.

        Args:
            d: Dict produced by :meth:`to_json`.

        Returns:
            Reconstructed PolyCalibration.
        """
        c = d["clip"]
        return cls(
            coeffs=tuple(float(x) for x in d["coeffs"]),  # type: ignore[arg-type]
            clip=ClipSpec(
                lo_log_s=float(c["lo_log_s"]),
                hi_log_s=float(c["hi_log_s"]),
            ),
            fit_id=str(d["fit_id"]),
        )


@dataclass(frozen=True)
class PiecewiseCalibration:
    """Piecewise-constant log s on the 5×5 2°-cell grid, five named regions.

    Regions: SW, SE, NW, NE, JET.  JET overrides the quadrant assignment for
    cells listed in ``mask``.  Values must lie within the clip bounds at
    construction time (spec §9 assertion — evidence-side values must not be
    silently clipped away).

    Attributes:
        lon_mid: Longitude midpoint separating E (≥) from W (<) quadrants.
        lat_mid: Latitude midpoint separating N (≥) from S (<) quadrants.
        mask: (5, 5) boolean tuple-of-tuples; True marks a JET cell.
        log_s_by_region: Region name -> log(s).  A plain dict may be passed
            at construction for convenience; it is normalized in
            ``__post_init__`` to a sorted tuple of (region, value) pairs so
            the instance is deeply immutable and hashable (Task-3's per-grid
            √s cache keys on the calibration).  Keys must include
            SW, SE, NW, NE, JET.
        clip: Pre-registered log-s clip bounds.
        fit_id: Identifier of the fitting run.
    """

    lon_mid: float
    lat_mid: float
    mask: tuple[tuple[bool, ...], ...]
    log_s_by_region: tuple[tuple[str, float], ...] | Mapping[str, float]
    clip: ClipSpec
    fit_id: str

    def __post_init__(self) -> None:
        """Normalize region values to a sorted tuple and validate clip bounds.

        Also coerces lon_mid and lat_mid to builtin float.

        Bug guarded: PiecewiseCalibration built with numpy scalar lon_mid/
        lat_mid stores np.float64 so key() emits 'np.float64(...)' via
        {self.lon_mid!r}/{self.lat_mid!r}, breaking cal_key self-consistency
        after JSON round-trip.

        Raises:
            ValueError: If any region log-s value falls outside [lo, hi].
        """
        object.__setattr__(self, "lon_mid", float(self.lon_mid))
        object.__setattr__(self, "lat_mid", float(self.lat_mid))
        items = (
            self.log_s_by_region.items()
            if isinstance(self.log_s_by_region, Mapping)
            else self.log_s_by_region
        )
        normalized = tuple(sorted((str(k), float(v)) for k, v in items))
        object.__setattr__(self, "log_s_by_region", normalized)
        lo, hi = self.clip.lo_log_s, self.clip.hi_log_s
        bad = {k: v for k, v in normalized if not (lo <= v <= hi)}
        if bad:
            raise ValueError(
                f"Region log_s values outside clip [{lo!r}, {hi!r}]: {bad!r}"
            )

    def _region_at(
        self, row: np.ndarray, col: np.ndarray, lon_c: np.ndarray, lat_c: np.ndarray
    ) -> np.ndarray:
        """Return log(s) for each (row, col) cell.

        Args:
            row: Row indices in [0, 4].
            col: Column indices in [0, 4].
            lon_c: Clamped longitudes (used for E/W split).
            lat_c: Clamped latitudes (used for N/S split).

        Returns:
            log(s) array, one value per input point.
        """
        by_region = dict(self.log_s_by_region)
        result = np.empty(row.shape, dtype=float)
        for i in range(row.size):
            r, c = int(row.flat[i]), int(col.flat[i])
            if self.mask[r][c]:
                result.flat[i] = by_region["JET"]
            else:
                east = lon_c.flat[i] >= self.lon_mid
                north = lat_c.flat[i] >= self.lat_mid
                if north and east:
                    region = "NE"
                elif north:
                    region = "NW"
                elif east:
                    region = "SE"
                else:
                    region = "SW"
                result.flat[i] = by_region[region]
        return result

    def log_s_at(self, lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
        """Return log(s) at the given locations.

        Coordinates outside the hull are clamped before cell lookup.

        Args:
            lon: Longitude array [deg east].
            lat: Latitude array [deg north].

        Returns:
            log(s) array; values are within clip by construction
            (validated at init).
        """
        lon_a = np.asarray(lon, float)
        lat_a = np.asarray(lat, float)
        lon_c, lat_c = _clamp_hull(lon_a, lat_a)
        shape = lon_c.shape
        row, col = _cell_index(lon_c.ravel(), lat_c.ravel())
        vals = self._region_at(row, col, lon_c.ravel(), lat_c.ravel())
        return vals.reshape(shape)

    def sqrt_s_at(self, lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
        """Return sqrt(s) at the given locations.

        Args:
            lon: Longitude array [deg east].
            lat: Latitude array [deg north].

        Returns:
            sqrt(s) = exp(0.5 * log_s_at(lon, lat)).
        """
        return np.exp(0.5 * self.log_s_at(lon, lat))

    def key(self) -> str:
        """Return a deterministic string key for this calibration.

        Returns:
            String encoding kind, region values, clip, mask, and fit_id.
        """
        # log_s_by_region is already a sorted tuple (normalized at init)
        regions = list(self.log_s_by_region)
        mask_str = repr(self.mask)
        return (
            f"cal:piecewise;mid=({self.lon_mid!r},{self.lat_mid!r});"
            f"regions={regions!r};mask={mask_str};"
            f"clip=({self.clip.lo_log_s!r},{self.clip.hi_log_s!r});"
            f"fit={self.fit_id}"
        )

    def to_json(self) -> dict[str, Any]:
        """Serialise to a JSON-compatible dict.

        Returns:
            Dict with keys ``kind``, ``lon_mid``, ``lat_mid``, ``mask``,
            ``log_s_by_region``, ``clip``, ``fit_id``.
        """
        return {
            "kind": "piecewise",
            "lon_mid": self.lon_mid,
            "lat_mid": self.lat_mid,
            # mask: nested list of bools (JSON-compatible)
            "mask": [list(row) for row in self.mask],
            "log_s_by_region": dict(self.log_s_by_region),
            "clip": {
                "lo_log_s": self.clip.lo_log_s,
                "hi_log_s": self.clip.hi_log_s,
            },
            "fit_id": self.fit_id,
        }

    @classmethod
    def from_json(cls, d: dict[str, Any]) -> PiecewiseCalibration:
        """Reconstruct from a serialised dict.

        Args:
            d: Dict produced by :meth:`to_json`.

        Returns:
            Reconstructed PiecewiseCalibration.
        """
        c = d["clip"]
        mask: tuple[tuple[bool, ...], ...] = tuple(
            tuple(bool(v) for v in row) for row in d["mask"]
        )
        return cls(
            lon_mid=float(d["lon_mid"]),
            lat_mid=float(d["lat_mid"]),
            mask=mask,
            log_s_by_region={k: float(v) for k, v in d["log_s_by_region"].items()},
            clip=ClipSpec(
                lo_log_s=float(c["lo_log_s"]),
                hi_log_s=float(c["hi_log_s"]),
            ),
            fit_id=str(d["fit_id"]),
        )


@dataclass(frozen=True)
class CovariateCalibration:
    """log s = a + b · log(proxy(cell(x))), clamped + clipped.

    The proxy is stored as raw per-cell values (not pre-logged).  At query
    time the cell is looked up on the 5×5 2°-cell grid, then
    log(proxy) is computed and used in the linear model.

    Attributes:
        proxy_cells: (5, 5) tuple-of-tuples of raw proxy values (positive
            floats — stored as raw proxy, logged at query time).
        a: Intercept of the log-s linear model.
        b: Slope on log(proxy).
        clip: Pre-registered log-s clip bounds.
        fit_id: Identifier of the fitting run.
    """

    proxy_cells: tuple[tuple[float, ...], ...]
    a: float
    b: float
    clip: ClipSpec
    fit_id: str

    def __post_init__(self) -> None:
        """Coerce a, b, and proxy_cells to builtin floats; validate positivity.

        Bug guarded: CovariateCalibration built with np.float64 inputs stores
        numpy scalars so key() emits 'np.float64(...)' via {self.a!r},
        {self.b!r}, and {self.proxy_cells!r}, breaking cal_key self-consistency
        after JSON round-trip.

        The proxy is a per-cell std of the mean maps — it must be > 0 or
        log(proxy) at query time silently produces NaN/-inf.

        Raises:
            ValueError: If any proxy cell is <= 0.
        """
        object.__setattr__(self, "a", float(self.a))
        object.__setattr__(self, "b", float(self.b))
        object.__setattr__(
            self,
            "proxy_cells",
            tuple(tuple(float(v) for v in row) for row in self.proxy_cells),
        )
        bad = [
            (r, c, v)
            for r, row in enumerate(self.proxy_cells)
            for c, v in enumerate(row)
            if not v > 0.0
        ]
        if bad:
            raise ValueError(
                f"Proxy cells must be strictly positive (std source); "
                f"offending (row, col, value): {bad!r}"
            )

    def log_s_at(self, lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
        """Return clipped log(s) at the given locations.

        Coordinates outside the hull are clamped; then the cell is looked
        up and the proxy value retrieved; log(proxy) is computed, and
        the linear model is applied.

        Args:
            lon: Longitude array [deg east].
            lat: Latitude array [deg north].

        Returns:
            log(s) array, clipped to [clip.lo_log_s, clip.hi_log_s].
        """
        lon_a = np.asarray(lon, float)
        lat_a = np.asarray(lat, float)
        lon_c, lat_c = _clamp_hull(lon_a, lat_a)
        shape = lon_c.shape
        row, col = _cell_index(lon_c.ravel(), lat_c.ravel())
        proxy_vals = np.array(
            [self.proxy_cells[int(r)][int(c)] for r, c in zip(row, col, strict=True)],
            dtype=float,
        )
        raw = self.a + self.b * np.log(proxy_vals)
        clipped: np.ndarray = np.clip(raw, self.clip.lo_log_s, self.clip.hi_log_s)
        return clipped.reshape(shape)

    def sqrt_s_at(self, lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
        """Return sqrt(s) at the given locations.

        Args:
            lon: Longitude array [deg east].
            lat: Latitude array [deg north].

        Returns:
            sqrt(s) = exp(0.5 * log_s_at(lon, lat)).
        """
        return np.exp(0.5 * self.log_s_at(lon, lat))

    def key(self) -> str:
        """Return a deterministic string key for this calibration.

        Returns:
            String encoding kind, proxy cells, a, b, clip, and fit_id.
        """
        return (
            f"cal:covariate;proxy={self.proxy_cells!r};"
            f"a={self.a!r};b={self.b!r};"
            f"clip=({self.clip.lo_log_s!r},{self.clip.hi_log_s!r});"
            f"fit={self.fit_id}"
        )

    def to_json(self) -> dict[str, Any]:
        """Serialise to a JSON-compatible dict.

        Returns:
            Dict with keys ``kind``, ``proxy_cells``, ``a``, ``b``,
            ``clip``, ``fit_id``.
        """
        return {
            "kind": "covariate",
            # proxy_cells: nested list of floats (JSON-compatible)
            "proxy_cells": [list(row) for row in self.proxy_cells],
            "a": self.a,
            "b": self.b,
            "clip": {
                "lo_log_s": self.clip.lo_log_s,
                "hi_log_s": self.clip.hi_log_s,
            },
            "fit_id": self.fit_id,
        }

    @classmethod
    def from_json(cls, d: dict[str, Any]) -> CovariateCalibration:
        """Reconstruct from a serialised dict.

        Args:
            d: Dict produced by :meth:`to_json`.

        Returns:
            Reconstructed CovariateCalibration.
        """
        c = d["clip"]
        proxy: tuple[tuple[float, ...], ...] = tuple(
            tuple(float(v) for v in row) for row in d["proxy_cells"]
        )
        return cls(
            proxy_cells=proxy,
            a=float(d["a"]),
            b=float(d["b"]),
            clip=ClipSpec(
                lo_log_s=float(c["lo_log_s"]),
                hi_log_s=float(c["hi_log_s"]),
            ),
            fit_id=str(d["fit_id"]),
        )


# Union alias for all four calibration field kinds.
CalibrationField = (
    ScalarCalibration | PiecewiseCalibration | PolyCalibration | CovariateCalibration
)


def calibration_from_json(d: dict[str, Any]) -> CalibrationField:
    """Dispatch deserialisation by the ``kind`` discriminator.

    Args:
        d: Dict produced by any CalibrationField's ``to_json()`` method.

    Returns:
        The reconstructed CalibrationField instance.

    Raises:
        ValueError: If ``kind`` is not recognised.
    """
    kind = d.get("kind")
    if kind == "scalar":
        return ScalarCalibration.from_json(d)
    if kind == "poly":
        return PolyCalibration.from_json(d)
    if kind == "piecewise":
        return PiecewiseCalibration.from_json(d)
    if kind == "covariate":
        return CovariateCalibration.from_json(d)
    raise ValueError(f"Unknown CalibrationField kind: {kind!r}")


def _cal_kind(cal: CalibrationField) -> str:
    """Return the ``kind`` discriminator string for a calibration field.

    Args:
        cal: Any CalibrationField instance.

    Returns:
        The same discriminator ``to_json`` emits (``scalar``/``poly``/
        ``piecewise``/``covariate``).
    """
    return str(cal.to_json()["kind"])


def _cal_dof(cal: CalibrationField) -> int:
    """Return the number of free parameters of a calibration field.

    Used as the ``dof`` recorded on the FIELD_INFLATION provenance transform.

    Args:
        cal: Any CalibrationField instance.

    Returns:
        Free-parameter count: scalar 1, poly 5, piecewise = number of regions,
        covariate 2.

    Raises:
        TypeError: If ``cal`` is not a recognised CalibrationField kind.
    """
    if isinstance(cal, ScalarCalibration):
        return 1
    if isinstance(cal, PolyCalibration):
        return len(cal.coeffs)
    if isinstance(cal, PiecewiseCalibration):
        return len(cal.log_s_by_region)
    if isinstance(cal, CovariateCalibration):
        return 2
    raise TypeError(f"Unknown CalibrationField kind for dof: {type(cal)!r}")
