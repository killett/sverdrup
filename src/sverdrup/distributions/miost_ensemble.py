"""Coefficient-space Stage-B ensemble distribution for MIOST (plan Task 15, D6).

Members live as coefficient anomalies about the UNPERTURBED eta^a per window;
every query evaluates the blended basis on demand at arbitrary points — no
node snapping. The mean field is the Stage-A mean, untouched by construction.
"""

from __future__ import annotations

from dataclasses import dataclass
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
