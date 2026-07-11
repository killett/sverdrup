"""Coefficient-space Stage-B ensemble distribution for MIOST (plan Task 15, D6).

Members live as coefficient anomalies about the UNPERTURBED eta^a per window;
every query evaluates the blended basis on demand at arbitrary points — no
node snapping. The mean field is the Stage-A mean, untouched by construction.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
from scipy import sparse  # type: ignore[import-untyped]

from sverdrup.core.grid import GridSpec
from sverdrup.core.provenance import (
    TransformKind,
    UncertaintyProvenance,
    UncertaintyTransform,
)
from sverdrup.core.types import Field, Points, Seed, UncertaintyCapability
from sverdrup.distributions.ensemble import EnsemblePredictiveDistribution
from sverdrup.methods.miost_basis import (
    W_DAYS,
    BasisSpec,
    Elements,
    build_s_spatial,
    lonlat_to_km,
    time_contract,
)
from sverdrup.methods.miost_windows import Window, WindowPlan

if TYPE_CHECKING:
    from collections.abc import Callable

    from sverdrup.core.observations import ObsWindow
    from sverdrup.core.parameters import ParameterProvider
    from sverdrup.methods.miost import Miost

KIND = "miost-coeff-ensemble"


def ensemble_provenance(m: int) -> UncertaintyProvenance:
    """Provenance for m perturbed-observation members (spec 6.2).

    Args:
        m: Member count.

    Returns:
        Native SAMPLES with one INPUT_PERTURBATION transform carrying m and
        the Monte-Carlo error sqrt(2 / (m - 1)).
    """
    return UncertaintyProvenance(
        native_capability=UncertaintyCapability.SAMPLES,
        transformations=[
            UncertaintyTransform(
                kind=TransformKind.INPUT_PERTURBATION,
                params={"m": m, "mc_error": float(np.sqrt(2.0 / (m - 1)))},
            )
        ],
    )


@dataclass
class MiostEnsembleDistribution:
    """SAMPLES predictive: Stage-A mean + m coefficient-anomaly members."""

    grid: GridSpec
    mean: Field
    provenance: UncertaintyProvenance
    time_days: float
    m: int
    _spec: BasisSpec
    _etas_a: dict[str, np.ndarray]  # window_id -> unperturbed eta^a (f64)
    _anoms: dict[str, np.ndarray]  # window_id -> (n_el, m) member anomalies
    _window_starts: dict[str, float]
    _w_days: float = W_DAYS

    def _eval(self, pts: Points, cols: dict[str, np.ndarray]) -> np.ndarray:
        """Blend-weighted basis evaluation of per-window column stacks.

        Args:
            pts: (n, 3) points as (lon deg, lat deg, time days).
            cols: window_id -> (n_el, k) coefficient columns.

        Returns:
            (n, k) values (zero where no window covers the point's day).
        """
        pts = np.asarray(pts, float)
        x, y = lonlat_to_km(pts[:, 0], pts[:, 1])
        t = pts[:, 2]
        plan = WindowPlan(
            starts=tuple(sorted(self._window_starts.values())), w_days=self._w_days
        )
        k = next(iter(cols.values())).shape[1]
        out = np.zeros((pts.shape[0], k))
        for wid, c in cols.items():
            w = Window(self._window_starts[wid], self._w_days)
            in_w = (t >= w.start_day) & (t <= w.end_day)
            if not in_w.any():
                continue
            els = self._spec.elements_for_window(w.start_day, self._w_days)
            gamma = self._spec.evaluate(els, x[in_w], y[in_w], t[in_w])
            wgt = np.array([plan.weight(w, float(td)) for td in t[in_w]])
            out[in_w] += wgt[:, None] * (gamma @ c)
        return out

    def mean_at(self, pts: Points) -> np.ndarray:
        """Stage-A mean (Gamma eta^a) at arbitrary points."""
        return self._eval(pts, {w: e[:, None] for w, e in self._etas_a.items()})[:, 0]

    def _anoms_at(self, pts: Points) -> np.ndarray:
        """(n_pts, m) member-anomaly fields at arbitrary points."""
        return self._eval(pts, self._anoms)

    def member_at(self, i: int, pts: Points) -> np.ndarray:
        """Member i's field (mean + anomaly) at arbitrary points."""
        return np.asarray(self.mean_at(pts) + self._anoms_at(pts)[:, i])

    def _grid_eval(self, cols: dict[str, np.ndarray], time_days: float) -> np.ndarray:
        """(n_nodes, k) blended evaluation on the grid via the SPARSE S-path.

        Grid-shaped queries must never build the dense gamma
        (``BasisSpec.evaluate`` is ~8 GB/window on the production grid — the
        OOM-#3 trap); arbitrary-POINT queries (:meth:`mean_at`,
        :meth:`covariance`) stay dense because track point sets are small.

        Args:
            cols: window_id -> (n_el, k) coefficient columns.
            time_days: Output day.

        Returns:
            (n_nodes, k) blended values on the grid.
        """
        plan = WindowPlan(
            starts=tuple(sorted(self._window_starts.values())), w_days=self._w_days
        )
        lon2d, lat2d = np.meshgrid(self.grid.x, self.grid.y)
        k = next(iter(cols.values())).shape[1]
        out = np.zeros((lon2d.size, k))
        for wid, c in cols.items():
            w = Window(self._window_starts[wid], self._w_days)
            if not (w.start_day <= time_days <= w.end_day):
                continue
            els = self._spec.elements_for_window(w.start_day, self._w_days)
            s = build_s_spatial(self._spec, els, lon2d.ravel(), lat2d.ravel())
            out += plan.weight(w, time_days) * (
                s @ time_contract(self._spec, els, c, time_days)
            )
        return out

    def marginal_variance(self) -> Field:
        """Per-node member variance about the MEMBER MEAN, (m - 1) denominator."""
        a = self._grid_eval(self._anoms, self.time_days)
        return np.asarray(np.var(a, axis=1, ddof=1).reshape(self.grid.shape))

    def covariance(self, a: Points, b: Points) -> np.ndarray:
        """Member-mean-centered sample covariance between point sets (no snap)."""
        aa = self._anoms_at(a)
        ab = self._anoms_at(b)
        ca = aa - aa.mean(axis=1, keepdims=True)
        cb = ab - ab.mean(axis=1, keepdims=True)
        return np.asarray((ca @ cb.T) / (self.m - 1))

    def sample(self, k: int, seed: Seed) -> np.ndarray:
        """Seeded without-replacement member subselection, shape (k, ny, nx).

        Raises:
            ValueError: If k exceeds the member count m (never fabricates).
        """
        if k > self.m:
            raise ValueError(f"sample(k={k}) exceeds member count m={self.m}")
        idx = np.random.default_rng(seed).choice(self.m, size=k, replace=False)
        return np.asarray(self.to_grid_ensemble(self.time_days).samples[idx])

    def to_grid_ensemble(self, time_days: float) -> EnsemblePredictiveDistribution:
        """Down-convert to the existing grid-sample representation at one day."""
        mean_g = self._grid_eval(
            {w: e[:, None] for w, e in self._etas_a.items()}, time_days
        )[:, 0]
        fields = mean_g[:, None] + self._grid_eval(self._anoms, time_days)
        samples = fields.T.reshape(self.m, *self.grid.shape)
        return EnsemblePredictiveDistribution(
            grid=self.grid,
            samples=samples,
            provenance=self.provenance,
            time_days=time_days,
        )

    def rescaled(self, s: float) -> MiostEnsembleDistribution:
        """Exact s-inflation: anomalies x sqrt(s); the mean is UNTOUCHED (D6).

        Args:
            s: Variance inflation factor (s* = chi2_red(1) closed form).

        Returns:
            A new distribution with variance exactly s x the original and a
            DIAGONAL_INFLATION transform recording s; the mean field is the
            same array (bit-identical).
        """
        prov = UncertaintyProvenance(
            native_capability=self.provenance.native_capability,
            transformations=[
                *self.provenance.transformations,
                UncertaintyTransform(
                    kind=TransformKind.DIAGONAL_INFLATION, params={"s": float(s)}
                ),
            ],
        )
        root_s = float(np.sqrt(s))
        return MiostEnsembleDistribution(
            grid=self.grid,
            mean=self.mean,
            provenance=prov,
            time_days=self.time_days,
            m=self.m,
            _spec=self._spec,
            _etas_a=self._etas_a,
            _anoms={w: a * root_s for w, a in self._anoms.items()},
            _window_starts=self._window_starts,
            _w_days=self._w_days,
        )

    def save_state(self, path: Path, anomalies_f32: bool = False) -> None:
        """Persist the representation-tagged coefficient ensemble.

        Args:
            path: Destination .npz path.
            anomalies_f32: Store member anomalies as float32 (eta^a stays
                float64 regardless — the mean is never compressed).
        """
        arrays: dict[str, object] = {
            "kind": KIND,
            "alpha": self._spec.alpha,
            "l_t_days": self._spec.l_t_days,
            "n_dir": self._spec.n_dir,
            "ladder": np.asarray(self._spec.ladder),
            "time_days": self.time_days,
            "w_days": self._w_days,
            "m": self.m,
            "mean": np.asarray(self.mean),
            "grid_lon": self.grid.x,
            "grid_lat": self.grid.y,
            "window_ids": np.asarray(list(self._etas_a.keys())),
        }
        for wid in self._etas_a:
            arrays[f"eta_{wid}"] = self._etas_a[wid]
            anom = self._anoms[wid]
            arrays[f"anom_{wid}"] = anom.astype(np.float32) if anomalies_f32 else anom
            arrays[f"start_{wid}"] = self._window_starts[wid]
        np.savez(path, **arrays)  # type: ignore[arg-type]

    @classmethod
    def load_state(cls, path: Path) -> MiostEnsembleDistribution:
        """Reconstruct a persisted ensemble; refuses non-ensemble files.

        Raises:
            ValueError: If the file's kind tag is not ``miost-coeff-ensemble``.
        """
        with np.load(path) as z:
            if "kind" not in z or str(z["kind"]) != KIND:
                raise ValueError(
                    f"not a {KIND!r} state file: kind="
                    f"{str(z['kind']) if 'kind' in z else 'MISSING'!r}"
                )
            spec = BasisSpec(
                alpha=float(z["alpha"]),
                l_t_days=float(z["l_t_days"]),
                n_dir=int(z["n_dir"]),
                ladder=tuple(float(s) for s in z["ladder"]),
            )
            wids = [str(w) for w in z["window_ids"]]
            m = int(z["m"])
            self = cls(
                grid=GridSpec.lonlat(z["grid_lon"], z["grid_lat"]),
                mean=np.asarray(z["mean"]),
                provenance=ensemble_provenance(m),
                time_days=float(z["time_days"]),
                m=m,
                _spec=spec,
                _etas_a={w: np.asarray(z[f"eta_{w}"]) for w in wids},
                _anoms={w: np.asarray(z[f"anom_{w}"], dtype=float) for w in wids},
                _window_starts={w: float(z[f"start_{w}"]) for w in wids},
                _w_days=float(z["w_days"]),
            )
        return self


def exclusive_days(plan: WindowPlan) -> dict[str, float]:
    """For each window, a day covered by ONLY that window (exclusive-range mid).

    ``Miost.sample_members`` solves the covering windows of the day it is
    given; one exclusive day per window yields exactly one batched member
    solve per window across :func:`merged_members` — the Task-18 efficiency
    contract (never re-solve members per output day).

    Args:
        plan: The window plan.

    Returns:
        window_id -> exclusive day.

    Raises:
        ValueError: If some window is never the sole cover of any day (a
            silent skip would merge an ensemble with a variance hole).
    """
    out: dict[str, float] = {}
    for w in plan.windows:
        alone = [
            float(d)
            for d in np.arange(w.start_day, w.end_day + 0.5, 1.0)
            if [c.id for c in plan.covering(float(d))] == [w.id]
        ]
        if not alone:
            raise ValueError(f"window {w.id} has no exclusive day in plan")
        out[w.id] = alone[len(alone) // 2]
    return out


def merged_members(
    method: Miost,
    obs: ObsWindow,
    grid: GridSpec,
    params: ParameterProvider,
    m: int,
    root: Seed,
    on_window: Callable[[str, float], None] | None = None,
) -> tuple[BasisSpec, dict[str, np.ndarray], dict[str, np.ndarray], dict[str, float]]:
    """All windows' member anomalies via one sample_members call per window.

    Identity-keyed CRN (same root every call) makes the merged ensemble
    identical per window to what any single blend-day call would produce.

    Args:
        method: The Miost method (its plan defines the windows).
        obs: Full observation window (TRAIN-ONLY at the call site).
        grid: Output grid.
        params: Parameter provider.
        m: Member count.
        root: CRN seed root — the SAME root for every window.
        on_window: Optional progress callback ``(window_id, day)`` fired
            after each window's batched solve.

    Returns:
        (spec, etas_a, anoms, window_starts) merged over all windows.

    Raises:
        ValueError: If the plan has no windows.
    """
    spec: BasisSpec | None = None
    etas_a: dict[str, np.ndarray] = {}
    anoms: dict[str, np.ndarray] = {}
    starts: dict[str, float] = {}
    for wid, day in exclusive_days(method._plan).items():
        dist = method.sample_members(obs, grid, params, day, m, root)
        spec = dist._spec
        etas_a.update(dist._etas_a)
        anoms.update(dist._anoms)
        starts.update(dist._window_starts)
        if on_window is not None:
            on_window(wid, day)
    if spec is None:
        raise ValueError("plan has no windows — nothing to merge")
    return spec, etas_a, anoms, starts


def _window_smats(
    spec: BasisSpec,
    starts: dict[str, float],
    grid: GridSpec,
    plan: WindowPlan,
) -> tuple[int, dict[str, tuple[Elements, sparse.csr_matrix]]]:
    """Per-window (Elements, spatial-S) on the grid nodes (SPARSE path)."""
    lon2d, lat2d = np.meshgrid(grid.x, grid.y)
    smats = {}
    for wid, s0 in starts.items():
        els = spec.elements_for_window(s0, plan.w_days)
        smats[wid] = (els, build_s_spatial(spec, els, lon2d.ravel(), lat2d.ravel()))
    return lon2d.size, smats


def mean_fields(
    spec: BasisSpec,
    starts: dict[str, float],
    etas_a: dict[str, np.ndarray],
    grid: GridSpec,
    plan: WindowPlan,
    days: list[float],
) -> np.ndarray:
    """Per-day blended mean fields via the SPARSE S-path (never dense evaluate).

    Args:
        spec: Basis specification of the merged ensemble.
        starts: window_id -> start day.
        etas_a: window_id -> (n_el,) unperturbed coefficients.
        grid: Output grid.
        plan: The window plan (blend weights).
        days: Output days.

    Returns:
        (len(days), n_nodes) mean fields (SLA space; add MDT downstream).
    """
    n_nodes, smats = _window_smats(spec, starts, grid, plan)
    out = np.zeros((len(days), n_nodes))
    for i, day in enumerate(days):
        for w in plan.covering(day):
            els, s = smats[w.id]
            out[i] += plan.weight(w, day) * (
                s @ time_contract(spec, els, etas_a[w.id], day)
            )
    return out


def std_fields(
    spec: BasisSpec,
    starts: dict[str, float],
    anoms: dict[str, np.ndarray],
    grid: GridSpec,
    plan: WindowPlan,
    days: list[float],
) -> np.ndarray:
    """Per-day member std fields via the SPARSE S-path (never dense evaluate).

    The blended member-anomaly field at a day is
    ``sum_w weight_w(day) * S_w @ time_contract(anoms_w, day)``; std is taken
    about the member sample mean with the (m - 1) denominator, matching
    :meth:`MiostEnsembleDistribution.marginal_variance`.

    Args:
        spec: Basis specification of the merged ensemble.
        starts: window_id -> start day.
        anoms: window_id -> (n_el, m) coefficient anomalies.
        grid: Output grid.
        plan: The window plan (blend weights).
        days: Output days.

    Returns:
        (len(days), n_nodes) member std fields.
    """
    n_nodes, smats = _window_smats(spec, starts, grid, plan)
    m = next(iter(anoms.values())).shape[1]
    out = np.empty((len(days), n_nodes))
    for i, day in enumerate(days):
        acc = np.zeros((n_nodes, m))
        for w in plan.covering(day):
            els, s = smats[w.id]
            acc += plan.weight(w, day) * (
                s @ time_contract(spec, els, anoms[w.id], day)
            )
        out[i] = acc.std(axis=1, ddof=1)
    return out


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

    Implements the searchsorted-right, clip-to-0..4 convention from
    scripts/diag_phase8_covariate_alignment.py.

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


@dataclass(frozen=True)
class ScalarCalibration:
    """Constant s — the shipped-scalar limit of the field layer.

    Clip-free by spec: the global scalar needs no spatial clamp.

    Attributes:
        s: Scale factor value (positive float).
    """

    s: float

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
        log_s_by_region: Mapping from region name to log(s) value.
            Keys must include SW, SE, NW, NE, JET.
        clip: Pre-registered log-s clip bounds.
        fit_id: Identifier of the fitting run.
    """

    lon_mid: float
    lat_mid: float
    mask: tuple[tuple[bool, ...], ...]
    log_s_by_region: dict[str, float]
    clip: ClipSpec
    fit_id: str

    def __post_init__(self) -> None:
        """Validate that all region values lie within clip bounds.

        Raises:
            ValueError: If any region log-s value falls outside [lo, hi].
        """
        lo, hi = self.clip.lo_log_s, self.clip.hi_log_s
        bad = {k: v for k, v in self.log_s_by_region.items() if not (lo <= v <= hi)}
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
        result = np.empty(row.shape, dtype=float)
        for i in range(row.size):
            r, c = int(row.flat[i]), int(col.flat[i])
            if self.mask[r][c]:
                result.flat[i] = self.log_s_by_region["JET"]
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
                result.flat[i] = self.log_s_by_region[region]
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
        # Sort region keys for determinism
        regions = sorted(self.log_s_by_region.items())
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
