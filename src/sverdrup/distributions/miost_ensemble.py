"""Coefficient-space Stage-B ensemble distribution for MIOST (plan Task 15, D6).

Members live as coefficient anomalies about the UNPERTURBED eta^a per window;
every query evaluates the blended basis on demand at arbitrary points — no
node snapping. The mean field is the Stage-A mean, untouched by construction.

Phase-9 note: calibration scaling has moved to the CalibratedDistribution
wrapper (distributions/calibration.py). The raw class stores anomalies
RAW and applies NO √s(x) factor; the wrapper applies it once at the method
layer. :meth:`with_calibration` and :meth:`rescaled` are thin forwarders
to the wrapper for backward-compat with existing call sites.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from scipy import sparse  # type: ignore[import-untyped]

from sverdrup.core.grid import GridSpec
from sverdrup.core.provenance import (
    TransformKind,
    UncertaintyProvenance,
    UncertaintyTransform,
)
from sverdrup.core.types import Field, Points, Seed, UncertaintyCapability
from sverdrup.distributions.calibration import (
    CalibrationField,
    ScalarCalibration,
    _cal_kind,
    calibration_from_json,
)
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
    from sverdrup.distributions.calibration import CalibratedDistribution
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
    """SAMPLES predictive: Stage-A mean + m coefficient-anomaly members.

    Anomalies are stored RAW (no √s(x) factor). Calibration scaling is
    applied by the :class:`~sverdrup.distributions.calibration.CalibratedDistribution`
    wrapper at the method layer (Phase-9 §3). The ``calibration`` attribute
    is retained for persistence compatibility only — it is NOT applied
    internally; use :meth:`with_calibration` to obtain a calibrated product.
    """

    grid: GridSpec
    mean: Field
    provenance: UncertaintyProvenance
    time_days: float
    m: int
    _spec: BasisSpec
    _etas_a: dict[str, np.ndarray]  # window_id -> unperturbed eta^a (f64)
    _anoms: dict[str, np.ndarray]  # window_id -> (n_el, m) RAW member anomalies
    _window_starts: dict[str, float]
    _w_days: float = W_DAYS
    # Stored for persistence round-trips; NOT applied internally (Phase-9 §3).
    calibration: CalibrationField = field(
        default_factory=lambda: ScalarCalibration(1.0)
    )

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
        """(n_pts, m) RAW member-anomaly fields at arbitrary points.

        Anomalies are returned WITHOUT calibration scaling. Scaling is applied
        by the CalibratedDistribution wrapper at the method layer (Phase-9 §3).
        The mean path (:meth:`mean_at`) never routes through here.
        """
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
        """Per-node RAW member variance about the MEMBER MEAN, (m - 1) denominator.

        Anomalies are RAW (no calibration scaling). The CalibratedDistribution
        wrapper applies s(x) on top when the product is queried through the
        method layer (Phase-9 §3). The mean path is not involved.
        """
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
        """Down-convert to the existing grid-sample representation at one day.

        Returns RAW (uncalibrated) samples. The CalibratedDistribution wrapper
        rescales the returned stack when the product is queried through the
        method layer (Phase-9 §3 + PIN A ``to_grid_ensemble`` forwarded route).
        """
        mean_g = self._grid_eval(
            {w: e[:, None] for w, e in self._etas_a.items()}, time_days
        )[:, 0]
        anoms_g = self._grid_eval(self._anoms, time_days)
        fields = mean_g[:, None] + anoms_g
        samples = fields.T.reshape(self.m, *self.grid.shape)
        return EnsemblePredictiveDistribution(
            grid=self.grid,
            samples=samples,
            provenance=self.provenance,
            time_days=time_days,
        )

    def with_calibration(self, cal: CalibrationField) -> CalibratedDistribution:
        """Return a CalibratedDistribution wrapping this raw ensemble with ``cal``.

        Thin forwarder to the Phase-9 CalibratedDistribution wrapper (Phase-9
        §3). Anomalies remain RAW; the wrapper applies √s(x) at query time.
        This method is retained for call-site compatibility (test_phase8_identity
        _regression.py, test_calibration_field.py). The raw class's calibration
        attribute is set to ``cal`` on the returned wrapper's underlying for
        persistence round-trips.

        Args:
            cal: The calibration field to apply.

        Returns:
            A CalibratedDistribution wrapping this instance with ``cal``.
        """
        from sverdrup.distributions.calibration import CalibratedDistribution

        updated = replace(self, calibration=cal)
        return CalibratedDistribution(updated, cal, UncertaintyCapability.SAMPLES)

    def rescaled(self, s: float) -> CalibratedDistribution:
        """Exact s-inflation via the CalibratedDistribution wrapper; composes ×√(st).

        Thin forwarder to the Phase-9 wrapper. On a scalar-calibrated instance
        this composes multiplicatively with the current scalar; on a
        NON-scalar (field-calibrated) instance it RAISES (owner narrowing).
        The mean is UNTOUCHED (D6). See
        :meth:`~sverdrup.distributions.calibration.CalibratedDistribution.rescaled`
        for the full contract.

        Args:
            s: Variance inflation factor.

        Returns:
            A CalibratedDistribution with variance exactly s × the original.

        Raises:
            ValueError: If this instance is field-calibrated (non-scalar).
        """
        from sverdrup.distributions.calibration import CalibratedDistribution

        if isinstance(self.calibration, ScalarCalibration):
            composed = ScalarCalibration(self.calibration.s * s)
            updated = replace(self, calibration=composed)
            wrapped = CalibratedDistribution(
                updated, composed, UncertaintyCapability.SAMPLES
            )
            # Record the INCREMENTAL factor (Phase-8 semantics: each step is
            # its own inflate, not the cumulative product).
            from sverdrup.distributions.calibration import _prov_with

            wrapped.provenance = _prov_with(self.provenance, composed, scalar_s=s)
            return wrapped
        raise ValueError(
            "rescaled(scalar) on a field-calibrated product is ambiguous — "
            "compose explicitly via with_calibration"
        )

    def save_state(self, path: Path, anomalies_f32: bool = False) -> None:
        """Persist the representation-tagged coefficient ensemble.

        Anomalies are always stored RAW (one convention — spec §8); the
        calibration field is serialised alongside as ``cal_kind`` /
        ``cal_params`` (a JSON string) / ``cal_key`` so the query-time √s(x)
        layer round-trips exactly. Files WITHOUT these keys reload as
        ScalarCalibration(1.0) (the FACTORY supplies s* for legacy raw-anoms
        files).

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
            "cal_kind": _cal_kind(self.calibration),
            "cal_params": json.dumps(self.calibration.to_json()),
            "cal_key": self.calibration.key(),
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
            # Files WITHOUT cal keys reload as ScalarCalibration(1.0) — the
            # persisted anomalies are RAW and the factory supplies s* (spec §8).
            calibration: CalibrationField = (
                calibration_from_json(json.loads(str(z["cal_params"])))
                if "cal_params" in z
                else ScalarCalibration(1.0)
            )
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
                calibration=calibration,
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
