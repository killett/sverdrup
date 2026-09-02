"""Coefficient-space Stage-B ensemble distribution for MIOST (plan Task 15, D6).

Members live as coefficient anomalies about the UNPERTURBED eta^a per window;
every query evaluates the blended basis on demand at arbitrary points — no
node snapping. The mean field is the Stage-A mean, untouched by construction.

Phase-9 note: calibration lives ONLY on the CalibratedDistribution wrapper
(distributions/calibration.py). This raw class stores anomalies RAW, applies
NO √s(x) factor, carries NO calibration field, and appends NO calibration
transform to provenance (PIN D — single append, on the wrapper).
``Miost.sample_members`` / ``Miost.solve`` return the wrapper; the raw
instance is reachable as its ``.underlying``.
"""

from __future__ import annotations

import os
from collections import OrderedDict
from collections.abc import Mapping
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
    from collections.abc import Callable, Iterator, Sequence

    from sverdrup.core.observations import ObsWindow
    from sverdrup.core.parameters import ParameterProvider
    from sverdrup.methods.miost import Miost

KIND = "miost-coeff-ensemble"
# Phase-13 (spec §11): ensembles produced under a STRUCTURED rspec persist
# under a versioned tag — a scalar-era consumer refuses them by the existing
# kind-refusal pattern instead of silently mistaking their provenance.
KIND_AUG = "miost-coeff-ensemble-aug1"
_KNOWN_KINDS = frozenset({KIND, KIND_AUG})


def variance_consistency_rtol(m: int) -> float:
    """5·SE relative tolerance for the member-variance consistency statistic.

    χ² arithmetic: the sample variance of m N(0, v) draws has
    Var = 2 v² / (m − 1), so SE/v = √(2/(m−1)) and the pre-registered
    band is 5·√(2/(m−1)) — 0.158 at the in-test m = 2000, 0.711 at the
    m = 100 acceptance runs (spec §19.4, recorded).

    Args:
        m: Member count.

    Returns:
        The relative tolerance (dimensionless).
    """
    return float(5.0 * np.sqrt(2.0 / (m - 1)))


def ensemble_provenance(m: int) -> UncertaintyProvenance:
    """Provenance for m perturbed-observation members (spec 6.2).

    Sample variance has m - 1 degrees of freedom, so at m = 1 (the
    single-member probe/cross-env solves) the Monte-Carlo error is
    UNDEFINED — recorded as ``None``, never a finite fake.

    Args:
        m: Member count (>= 1).

    Returns:
        Native SAMPLES with one INPUT_PERTURBATION transform carrying m and
        the Monte-Carlo error sqrt(2 / (m - 1)) (``None`` at m = 1).

    Raises:
        ValueError: If ``m < 1`` (no members is not an ensemble).
    """
    if m < 1:
        raise ValueError(f"m must be >= 1, got {m}")
    mc_error = float(np.sqrt(2.0 / (m - 1))) if m > 1 else None
    return UncertaintyProvenance(
        native_capability=UncertaintyCapability.SAMPLES,
        transformations=[
            UncertaintyTransform(
                kind=TransformKind.INPUT_PERTURBATION,
                params={"m": m, "mc_error": mc_error},
            )
        ],
    )


@dataclass
class MiostEnsembleDistribution:
    """SAMPLES predictive: Stage-A mean + m coefficient-anomaly members.

    Anomalies are stored RAW (no √s(x) factor). Calibration scaling is
    applied by the :class:`~sverdrup.distributions.calibration.CalibratedDistribution`
    wrapper at the method layer (Phase-9 §3). This class carries NO
    calibration surface — calibrate by wrapping:
    ``CalibratedDistribution(raw, cal, capability)`` (or via the wrapper's
    replace/compose methods).
    """

    grid: GridSpec
    mean: Field
    provenance: UncertaintyProvenance
    time_days: float
    m: int
    _spec: BasisSpec
    _etas_a: dict[str, np.ndarray]  # window_id -> unperturbed eta^a (f64)
    # Read-only here; with a window store this is a WindowBackedAnoms
    # reader rather than a dict (owner pin 133).
    _anoms: Mapping[str, np.ndarray]  # window_id -> (n_el, m) RAW member anomalies
    _window_starts: dict[str, float]
    _w_days: float = W_DAYS
    # persisted kind tag: KIND for scalar-era configs, KIND_AUG for
    # ensembles produced under a structured rspec (spec §11 versioning)
    state_kind: str = KIND

    def _plan(self) -> WindowPlan:
        """Return the WindowPlan over this distribution's sorted window starts."""
        return WindowPlan(
            starts=tuple(sorted(self._window_starts.values())), w_days=self._w_days
        )

    def _eval(self, pts: Points, cols: Mapping[str, np.ndarray]) -> np.ndarray:
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
        plan = self._plan()
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

    def _grid_eval(
        self, cols: Mapping[str, np.ndarray], time_days: float
    ) -> np.ndarray:
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
        plan = self._plan()
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

    def save_state(self, path: Path, anomalies_f32: bool = False) -> None:
        """Persist the representation-tagged coefficient ensemble.

        Anomalies are always stored RAW (one convention — spec §8). This raw
        class writes NO calibration keys — the CalibratedDistribution
        wrapper's ``save_state`` adds ``cal_kind`` / ``cal_params`` /
        ``cal_key`` on top (Phase-9 §3; legacy files without those keys load
        as ScalarCalibration(1.0) through the wrapper's ``load_state``).

        Args:
            path: Destination .npz path.
            anomalies_f32: Store member anomalies as float32 (eta^a stays
                float64 regardless — the mean is never compressed).
        """
        arrays: dict[str, object] = {
            "kind": self.state_kind,
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
            ValueError: If the file's kind tag is not one of the known
                ensemble kinds (scalar-era or the phase-13 augmented tag).
        """
        with np.load(path) as z:
            if "kind" not in z or str(z["kind"]) not in _KNOWN_KINDS:
                raise ValueError(
                    f"not a known ensemble state file ({sorted(_KNOWN_KINDS)}): "
                    f"kind={str(z['kind']) if 'kind' in z else 'MISSING'!r}"
                )
            loaded_kind = str(z["kind"])
            spec = BasisSpec(
                alpha=float(z["alpha"]),
                l_t_days=float(z["l_t_days"]),
                n_dir=int(z["n_dir"]),
                ladder=tuple(float(s) for s in z["ladder"]),
            )
            wids = [str(w) for w in z["window_ids"]]
            m = int(z["m"])
            # cal_* keys, if present (wrapper-written files), are IGNORED here:
            # the CalibratedDistribution wrapper's load_state reads them (§3).
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
                state_kind=loaded_kind,
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


def _window_store_file(store: Path, wid: str) -> Path:
    """Path of one window's persisted members inside ``store``."""
    return store / f"window_{wid}.npz"


def _save_window(
    store: Path,
    wid: str,
    *,
    eta: np.ndarray,
    anom: np.ndarray,
    start: float,
    m: int,
    root: Seed,
) -> None:
    """Persist ONE window's members atomically (owner pins 121a, 122).

    Temp-and-rename, so a crash inside the write leaves the previous state
    intact rather than a half-written window a later leg would read as
    complete. ``m`` and ``root`` ride along so a store from a different
    configuration is refused rather than adopted.
    """
    store.mkdir(parents=True, exist_ok=True)
    dest = _window_store_file(store, wid)
    tmp = dest.with_name(dest.name + ".tmp")
    np.savez(
        tmp,
        eta=eta,
        anom=anom,
        start=float(start),
        wid=wid,
        m=int(m),
        root=str(root),
    )
    written = tmp if tmp.exists() else tmp.with_name(tmp.name + ".npz")
    os.replace(written, dest)


def _load_window(
    path: Path, *, wid: str, m: int, root: Seed
) -> tuple[np.ndarray, np.ndarray, float]:
    """Load ONE persisted window, refusing anything that is not it.

    Raises:
        RuntimeError: The file is unreadable (a crash inside its own
            write), or it belongs to a different configuration. Neither is
            recoverable by guessing, and adopting either silently is how a
            leg assembles one configuration's window under another's name.
    """
    try:
        ctx = np.load(path, allow_pickle=False)
    except Exception as exc:  # noqa: BLE001 - any load failure is corruption
        raise RuntimeError(
            f"persisted window {path} is unreadable ({exc!r}) — it is corrupt, "
            "most likely a crash inside its own write. Delete it and the "
            "window will be re-solved"
        ) from exc
    with ctx as z:
        if str(z["wid"]) != wid or int(z["m"]) != int(m) or str(z["root"]) != str(root):
            raise RuntimeError(
                f"persisted window {path} belongs to a different configuration "
                f"(stored wid={str(z['wid'])!r} m={int(z['m'])} root={str(z['root'])!r}; "
                f"requested wid={wid!r} m={int(m)} root={str(root)!r}) — refusing to "
                "assemble it"
            )
        return np.asarray(z["eta"]), np.asarray(z["anom"]), float(z["start"])


def _load_window_fields(
    path: Path, *, wid: str, m: int, root: Seed, fields: tuple[str, ...]
) -> tuple[np.ndarray | float, ...]:
    """Load NAMED members of one persisted window, refusing anything else.

    ``np.load`` on an npz reads members on demand, so asking for ``eta``
    and ``start`` never materialises the ``(n_el, m)`` anomaly block —
    which is the whole point of pin 133: the leg keeps the cheap fields
    and leaves the expensive one on disk until a consumer asks.

    Args:
        path: The persisted window file.
        wid: Window id this file must belong to.
        m: Member count this file must have been written under.
        root: CRN root this file must have been written under.
        fields: Member names to read, in the order they are returned.

    Returns:
        The requested members, in ``fields`` order.

    Raises:
        RuntimeError: The file is unreadable, or it belongs to a different
            configuration — the same two refusals :func:`_load_window`
            makes, made in the same place so a lazy read can never be the
            laxer path.
    """
    try:
        ctx = np.load(path, allow_pickle=False)
    except Exception as exc:  # noqa: BLE001 - any load failure is corruption
        raise RuntimeError(
            f"persisted window {path} is unreadable ({exc!r}) — it is corrupt, "
            "most likely a crash inside its own write. Delete it and the "
            "window will be re-solved"
        ) from exc
    with ctx as z:
        if str(z["wid"]) != wid or int(z["m"]) != int(m) or str(z["root"]) != str(root):
            raise RuntimeError(
                f"persisted window {path} belongs to a different configuration "
                f"(stored wid={str(z['wid'])!r} m={int(z['m'])} root={str(z['root'])!r}; "
                f"requested wid={wid!r} m={int(m)} root={str(root)!r}) — refusing to "
                "assemble it"
            )
        out: list[np.ndarray | float] = []
        for name in fields:
            out.append(float(z[name]) if name == "start" else np.asarray(z[name]))
        return tuple(out)


class WindowBackedAnoms(Mapping[str, np.ndarray]):
    """Member anomalies read from the window store, ``max_resident`` at a time.

    Owner pin 133. A completed window's ``(n_el, m)`` anomaly block is on
    disk the moment ``_save_window`` returns; holding it as well made peak
    RSS O(n_windows). At leg-1 kuroshio shape that block is 373.8 MiB, and
    nine of them is the 391 MiB-per-window growth the leg measured.

    Consumers walk days in order and each day blends at most two windows
    (``WindowPlan.covering``), so a two-entry LRU loads each window once
    per pass rather than thrashing. The mapping is READ-ONLY and its
    contents are byte-identical to the eager path — the acceptance pin
    133(e) names, checked by the same digests as pin 121.
    """

    def __init__(
        self,
        store: Path,
        window_ids: Sequence[str],
        *,
        m: int,
        root: Seed,
        max_resident: int = 2,
    ) -> None:
        """Bind the mapping to a store without reading anything.

        Args:
            store: Directory holding ``window_<wid>.npz``.
            window_ids: The windows this leg assembled.
            m: Member count every file must carry.
            root: CRN root every file must carry.
            max_resident: How many blocks may stay live at once.
        """
        if max_resident < 1:
            raise ValueError("max_resident must be at least 1")
        self._store = store
        self._ids = tuple(window_ids)
        self._m = int(m)
        self._root = root
        self._max_resident = int(max_resident)
        self._cache: OrderedDict[str, np.ndarray] = OrderedDict()

    def __getitem__(self, wid: str) -> np.ndarray:
        """One window's anomaly block, loading it if it is not resident."""
        if wid not in self._ids:
            raise KeyError(wid)
        if wid in self._cache:
            self._cache.move_to_end(wid)
            return self._cache[wid]
        (anom,) = _load_window_fields(
            _window_store_file(self._store, wid),
            wid=wid,
            m=self._m,
            root=self._root,
            fields=("anom",),
        )
        block = np.asarray(anom)
        self._cache[wid] = block
        while len(self._cache) > self._max_resident:
            self._cache.popitem(last=False)
        return block

    def __iter__(self) -> Iterator[str]:
        """Window ids, in the order the leg assembled them."""
        return iter(self._ids)

    def __len__(self) -> int:
        """How many windows this leg assembled."""
        return len(self._ids)

    def resident_window_ids(self) -> tuple[str, ...]:
        """Which blocks are live right now — the pin-133 property, observable."""
        return tuple(self._cache)


def merged_members(
    method: Miost,
    obs: ObsWindow,
    grid: GridSpec,
    params: ParameterProvider,
    m: int,
    root: Seed,
    on_window: Callable[[str, float], None] | None = None,
    window_store: Path | None = None,
) -> tuple[
    BasisSpec, dict[str, np.ndarray], Mapping[str, np.ndarray], dict[str, float]
]:
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
        window_store: Optional directory for PER-WINDOW persistence (owner
            pin 121). Each window's members are written as it completes and
            an already-persisted window is LOADED instead of re-solved, so a
            crash costs one window rather than every completed one. The
            solve is unchanged; this is persistence and reassembly only
            (121c), and the assembled result is bit-identical to the
            monolithic path (121b, test-pinned at two windows per pin 127).

    Returns:
        (spec, etas_a, anoms, window_starts) merged over all windows.
        With ``window_store`` set, ``anoms`` is a
        :class:`WindowBackedAnoms` reader over the store rather than a
        dict (owner pin 133): the blocks are already persisted, so holding
        them too made peak RSS O(n_windows). Content is unchanged and
        bit-identical, which is the acceptance pin 133(e) names.

    Raises:
        ValueError: If the plan has no windows.
    """
    spec: BasisSpec | None = None
    etas_a: dict[str, np.ndarray] = {}
    anoms: dict[str, np.ndarray] = {}
    starts: dict[str, float] = {}
    for wid, day in exclusive_days(method._plan).items():
        stored = None if window_store is None else _window_store_file(window_store, wid)
        if stored is not None and stored.exists():
            # Pin 133: read the CHEAP fields only. The (n_el, m) block stays
            # on disk until a consumer asks for it — at leg-1 kuroshio shape
            # that is 373.8 MiB per window not held.
            eta, start = _load_window_fields(
                stored, wid=wid, m=m, root=root, fields=("eta", "start")
            )
            etas_a[wid] = np.asarray(eta)
            starts[wid] = float(start)
            if on_window is not None:
                on_window(wid, day)
            continue
        # sample_members returns the CalibratedDistribution wrapper (Phase-9
        # §3); the merge needs the RAW coefficient internals -> .underlying.
        dist = method.sample_members(obs, grid, params, day, m, root).underlying
        spec = dist._spec
        etas_a.update(dist._etas_a)
        starts.update(dist._window_starts)
        if window_store is not None:
            _save_window(
                window_store,
                wid,
                eta=dist._etas_a[wid],
                anom=dist._anoms[wid],
                start=dist._window_starts[wid],
                m=m,
                root=root,
            )
            # Pin 133. The block is on disk now; the only thing keeping it
            # live is this scope, and `dist` is rebound next iteration.
            # Dropping it here is what makes peak RSS O(1) in windows.
            del dist
        else:
            anoms.update(dist._anoms)
        if on_window is not None:
            on_window(wid, day)
    if spec is None:
        if not etas_a:
            raise ValueError("plan has no windows — nothing to merge")
        # Every window came from the store, so no solve produced a spec.
        # This is the resume path the seam and anchor legs already use:
        # the spec is a pure function of the params and the grid.
        spec = method._spec_from(params, grid)
    if window_store is not None:
        # Pin 133: the store IS the retention. Hand back a reader over it,
        # never a dict — a dict is the defect by definition.
        return (
            spec,
            etas_a,
            WindowBackedAnoms(window_store, list(etas_a), m=m, root=root),
            starts,
        )
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
    etas_a: Mapping[str, np.ndarray],
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
    anoms: Mapping[str, np.ndarray],
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
