"""MIOST method: POINT distribution + window-cache Method (spec §4; Stage A)."""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from scipy import sparse  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from sverdrup.distributions.miost_ensemble import (
        CalibrationField,
        MiostEnsembleDistribution,
    )

from sverdrup.core.distribution import CapabilityNotAvailableError
from sverdrup.core.grid import GridSpec
from sverdrup.core.observations import ObsWindow
from sverdrup.core.parameters import ParameterProvider, ParameterSpace
from sverdrup.core.provenance import UncertaintyProvenance
from sverdrup.core.types import Field, Points, Seed, UncertaintyCapability
from sverdrup.methods.miost_basis import (
    N_DIR,
    R_REF,
    W_DAYS,
    BasisSpec,
    DiagonalQ,
    Elements,
    build_g,
    build_s_spatial,
    lonlat_to_km,
    time_contract,
)
from sverdrup.methods.miost_solver import (
    PCG_MAXITER,
    PCG_RTOL,
    MiostSolver,
    rhs_from_obs,
)
from sverdrup.methods.miost_windows import (
    OBS_END_DAY,
    OBS_START_DAY,
    Window,
    WindowPlan,
)


@dataclass
class MiostPointDistribution:
    """POINT predictive: mean field + analytic-eval queries; variance family raises (seam e)."""

    grid: GridSpec
    mean: Field
    provenance: UncertaintyProvenance
    time_days: float
    _spec: BasisSpec
    _etas: dict[str, np.ndarray]  # window_id -> eta
    _window_starts: dict[str, float]
    _w_days: float = W_DAYS  # non-default ONLY in the Task-11 single-window harness

    @classmethod
    def from_etas(
        cls,
        grid: GridSpec,
        time_days: float,
        spec: BasisSpec,
        etas: dict[str, np.ndarray],
        window_starts: dict[str, float],
        w_days: float = W_DAYS,
    ) -> MiostPointDistribution:
        """Build the distribution from solved window coefficients.

        Args:
            grid: Output grid.
            time_days: Output day [days since epoch].
            spec: Basis specification the coefficients belong to.
            etas: window_id -> solved coefficient vector.
            window_starts: window_id -> window start day.
            w_days: Window length the coefficients were solved at.

        Returns:
            The POINT distribution with the mean evaluated on ``grid``.
        """
        prov = UncertaintyProvenance(
            native_capability=UncertaintyCapability.POINT, transformations=[]
        )
        self = cls(
            grid=grid,
            mean=np.empty(grid.shape),
            provenance=prov,
            time_days=time_days,
            _spec=spec,
            _etas={k: np.asarray(v) for k, v in etas.items()},
            _window_starts=dict(window_starts),
            _w_days=w_days,
        )
        lon2d, lat2d = np.meshgrid(grid.x, grid.y)
        pts = np.column_stack(
            [lon2d.ravel(), lat2d.ravel(), np.full(lon2d.size, time_days)]
        )
        self.mean = self.mean_at(pts).reshape(grid.shape)
        return self

    def marginal_variance(self) -> Field:
        """POINT capability: raises — no marginal variance exists."""
        raise CapabilityNotAvailableError(
            "miost Stage A is POINT: no marginal variance"
        )

    def covariance(self, a: Points, b: Points) -> np.ndarray:
        """POINT capability: raises — no covariance exists."""
        raise CapabilityNotAvailableError("miost Stage A is POINT: no covariance")

    def sample(self, m: int, seed: Seed) -> np.ndarray:
        """POINT capability: raises — no samples exist."""
        raise CapabilityNotAvailableError("miost Stage A is POINT: no samples")

    def regrid(self, target: GridSpec) -> MiostPointDistribution:
        """Re-express the mean on ``target`` by analytic evaluation.

        Args:
            target: The target grid.

        Returns:
            A new POINT distribution on ``target``.
        """
        return MiostPointDistribution.from_etas(
            grid=target,
            time_days=self.time_days,
            spec=self._spec,
            etas=self._etas,
            window_starts=self._window_starts,
            w_days=self._w_days,
        )

    def mean_at(self, pts: Points) -> np.ndarray:
        """Blend-weighted analytic evaluation at arbitrary (lon, lat, t) points (seam d).

        Args:
            pts: ``(n, 3)`` points as (lon deg, lat deg, time days).

        Returns:
            Mean values at the points.
        """
        pts = np.asarray(pts, float)
        x, y = lonlat_to_km(pts[:, 0], pts[:, 1])
        t = pts[:, 2]
        plan = WindowPlan(
            starts=tuple(sorted(self._window_starts.values())), w_days=self._w_days
        )
        out = np.zeros(pts.shape[0])
        for wid, eta in self._etas.items():
            w = Window(self._window_starts[wid], self._w_days)
            in_w = (t >= w.start_day) & (t <= w.end_day)
            if not in_w.any():
                continue
            els = self._spec.elements_for_window(w.start_day, self._w_days)
            gamma = self._spec.evaluate(els, x[in_w], y[in_w], t[in_w])
            wgt = np.array([plan.weight(w, float(td)) for td in t[in_w]])
            out[in_w] += wgt * (gamma @ eta)
        return out

    def save_state(self, path: Path) -> None:
        """Persist coefficients + basis parameters + grid (seam e), flat npz layout.

        Args:
            path: Destination ``.npz`` path.
        """
        arrays: dict[str, object] = {
            "basis_key": self._spec.key(),
            "alpha": self._spec.alpha,
            "l_t_days": self._spec.l_t_days,
            "n_dir": self._spec.n_dir,
            "ladder": np.asarray(self._spec.ladder),
            "time_days": self.time_days,
            "w_days": self._w_days,
            "mean": np.asarray(self.mean),
            "grid_lon": self.grid.x,
            "grid_lat": self.grid.y,
            "window_ids": np.asarray(list(self._etas.keys())),
        }
        arrays.update({f"eta_{wid}": eta for wid, eta in self._etas.items()})
        arrays.update({f"start_{wid}": s for wid, s in self._window_starts.items()})
        np.savez(path, **arrays)  # type: ignore[arg-type]

    @classmethod
    def load_state(cls, path: Path) -> MiostPointDistribution:
        """Reconstruct a persisted distribution; the mean is re-derived bit-identically.

        Args:
            path: Source ``.npz`` path.

        Returns:
            The reconstructed POINT distribution.
        """
        with np.load(path) as z:
            spec = BasisSpec(
                alpha=float(z["alpha"]),
                l_t_days=float(z["l_t_days"]),
                n_dir=int(z["n_dir"]),
                ladder=tuple(float(s) for s in z["ladder"]),
            )
            wids = [str(w) for w in z["window_ids"]]
            etas = {wid: np.asarray(z[f"eta_{wid}"]) for wid in wids}
            starts = {wid: float(z[f"start_{wid}"]) for wid in wids}
            grid = GridSpec.lonlat(z["grid_lon"], z["grid_lat"])
            out = cls.from_etas(
                grid=grid,
                time_days=float(z["time_days"]),
                spec=spec,
                etas=etas,
                window_starts=starts,
                w_days=float(z["w_days"]) if "w_days" in z else W_DAYS,
            )
            # bit-identity guaranteed by storing the mean too
            out.mean = np.asarray(z["mean"])
        return out


# Budgeted-solve telemetry (owner decision, Task-11 gate 2026-07-04): every fresh
# window solve appends its ACHIEVED residual here so acceptance configs can state
# (target, cap, achieved) — the honest record of a capped solve. Consumers
# (gate runners) snapshot/filter by params_key_hash; tests may clear it.
CONVERGENCE_LOG: list[dict[str, object]] = []


def _params_key_hash(pk: str) -> str:
    """Short stable hash of a params_key for telemetry correlation."""
    return hashlib.blake2b(pk.encode(), digest_size=8).hexdigest()


def _obs_fingerprint(obs: ObsWindow) -> str:
    """Content hash of the obs (spec §4.2.1: wrong-becomes-slow, never wrong-becomes-wrong)."""
    h = hashlib.blake2b(digest_size=16)
    h.update(obs.coords().tobytes())
    h.update(obs.values().tobytes())
    return h.hexdigest()


def _window_mask(obs: ObsWindow, w: Window, l_t_days: float) -> np.ndarray:
    """Boolean mask of obs in [start - L_t, end + L_t]; loud span assert.

    Args:
        obs: The FULL observation window (wide temporal_half_window_days).
        w: The solve window.
        l_t_days: Temporal support half-width.

    Returns:
        Boolean mask over the obs.

    Raises:
        ValueError: If nonempty obs do not span the window's support interval
            (clipped to the obs data span) — pass the full obs.
    """
    t = obs.coords()[:, 2]
    lo_full = w.start_day - l_t_days
    hi_full = w.end_day + l_t_days
    # Span demand clipped to the data span WITH the placement's 1-day edge slack
    # (real coarsened obs start/end a fraction inside the nominal file days).
    lo = max(lo_full, OBS_START_DAY + 1.0)
    hi = min(hi_full, OBS_END_DAY - 1.0)
    if len(obs) and (t.min() > lo + 1e-9 or t.max() < hi - 1e-9):
        raise ValueError(
            f"obs do not span window {w.id} support [{lo}, {hi}] "
            f"(got [{t.min()}, {t.max()}]) — pass the full obs "
            "(wide temporal_half_window_days)"
        )
    return np.asarray((t >= lo_full) & (t <= hi_full))


def _window_obs(
    obs: ObsWindow, w: Window, l_t_days: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Subset obs to the window support (see _window_mask for the contract).

    Returns:
        (lon, lat, t, values) of the in-window observations.
    """
    m = _window_mask(obs, w, l_t_days)
    coords = obs.coords()
    return coords[m, 0], coords[m, 1], coords[m, 2], obs.values()[m]


def _obs_identity(
    lon: np.ndarray, lat: np.ndarray, t: np.ndarray, mission: np.ndarray | None
) -> np.ndarray:
    """Window-independent per-obs identity rows for CRN keying (spec 6.2).

    Args:
        lon: Longitudes [deg].
        lat: Latitudes [deg].
        t: Times [days].
        mission: Mission strings, or None.

    Returns:
        (n, 4) contiguous float64 rows (lon, lat, time, mission-hash) —
        bit-identical across windows because the sources are the same
        file-loaded values.
    """
    if mission is None:
        mh = np.zeros(lon.size)
    else:
        mh = np.array(
            [
                float(
                    int.from_bytes(
                        hashlib.blake2b(str(s).encode(), digest_size=4).digest(), "big"
                    )
                )
                for s in mission
            ]
        )
    return np.ascontiguousarray(np.column_stack([lon, lat, t, mh]))


def member_rhs_matrix(
    g: sparse.csr_matrix,
    r: np.ndarray,
    y: np.ndarray,
    q: np.ndarray,
    obs_identity: np.ndarray,
    els_identity: np.ndarray,
    m: int,
    root: Seed,
) -> np.ndarray:
    """Build the m member right-hand sides for one window (spec 6.2).

    Column i is ``G^T R^-1 (y + eps'_i) + Q^-1 eta~_i`` with identity-keyed
    CRN perturbations. Shared by :meth:`Miost.sample_members` and the
    Stage-B exactness oracle — one construction, tested against dense
    ``A^-1`` on the oracle geometry.

    Args:
        g: CSR observation operator for the window.
        r: (n_obs,) diagonal R.
        y: (n_obs,) observed values (empty allowed).
        q: (n_el,) diagonal Q.
        obs_identity: (n_obs, 4) CRN identity rows (see _obs_identity).
        els_identity: (n_el, 6) element identity rows.
        m: Member count.
        root: CRN seed root.

    Returns:
        (n_el, m) RHS matrix.
    """
    from sverdrup.methods.miost_crn import coef_noise, obs_noise

    base = rhs_from_obs(g, r, y) if y.size else np.zeros(q.size)
    b = np.empty((q.size, m))
    for i in range(m):
        eta_t = coef_noise(i, els_identity, q, root)
        b[:, i] = base + eta_t / q
        if y.size:
            eps = obs_noise(i, obs_identity, r, root)
            b[:, i] += g.T @ (eps / r)
    return b


class Miost:
    """MIOST window-cache Method (spec §4.2). native_capability = POINT (Stage A)."""

    native_capability = UncertaintyCapability.POINT

    def __init__(
        self,
        n_dir: int = N_DIR,
        cache: bool = True,
        plan: WindowPlan | None = None,
        pcg_rtol: float = PCG_RTOL,
        pcg_maxiter: int = PCG_MAXITER,
        members: int = 0,
        member_root: Seed | None = None,
        inflation_s: float = 1.0,
        calibration: CalibrationField | None = None,
    ) -> None:
        """Create the method with empty caches.

        Args:
            n_dir: Plane-wave direction count (D2 diagnostic override; default D1).
            cache: Disable to force fresh solves (cache-correctness tests).
            plan: Window placement override (Task-11 single-window harness ONLY).
            pcg_rtol: Solver convergence tolerance (diagnostic override).
            pcg_maxiter: Solver iteration cap (diagnostic override).
            members: Ensemble mode — member count per solve (0 = POINT,
                Stage A). When > 0 the method is SAMPLES-native and
                ``solve`` returns the perturbed-observation ensemble.
            member_root: CRN seed root for ensemble mode (REQUIRED when
                ``members > 0`` — a silent default would make members
                irreproducible across sessions).
            inflation_s: Stage-B s* variance inflation (compat shim) — maps to
                ``ScalarCalibration(inflation_s)`` applied by the query-time
                √s(x) calibration layer (mean untouched; 1.0 = none). Mutually
                exclusive with ``calibration``.
            calibration: The Phase-8 CalibrationField carried through to the
                ensemble product (the general s(x) layer). Defaults to
                ``ScalarCalibration(inflation_s)``. Passing BOTH a calibration
                and a non-unit ``inflation_s`` is ambiguous and raises.

        Raises:
            ValueError: If ``members > 0`` without ``member_root``, or if both
                ``calibration`` and a non-unit ``inflation_s`` are supplied.
        """
        if members > 0 and member_root is None:
            raise ValueError("ensemble mode (members > 0) requires member_root")
        if calibration is not None and inflation_s != 1.0:
            raise ValueError(
                "pass either calibration or inflation_s, not both "
                "(inflation_s is the ScalarCalibration compat shim)"
            )
        from sverdrup.distributions.miost_ensemble import ScalarCalibration

        self.n_dir = n_dir
        self.cache = cache
        self.pcg_rtol = pcg_rtol
        self.pcg_maxiter = pcg_maxiter
        self.members = members
        self.member_root = member_root
        self.inflation_s = inflation_s
        self._calibration: CalibrationField = (
            calibration if calibration is not None else ScalarCalibration(inflation_s)
        )
        self.native_capability = (
            UncertaintyCapability.SAMPLES
            if members > 0
            else UncertaintyCapability.POINT
        )
        self._plan = plan if plan is not None else WindowPlan()
        self._eta_cache: dict[tuple[str, str, str], np.ndarray] = {}
        self._s_cache: OrderedDict[
            tuple[str, str], tuple[Elements, sparse.csr_matrix]
        ] = OrderedDict()

    def parameter_space(self) -> ParameterSpace:
        """Return the Stage-A tunable boxes (plan-fixed)."""
        return ParameterSpace(
            bounds={
                "spacing_alpha": (0.5, 1.5),
                "log10_rho": (-2.0, 3.0),
                "q_slope": (0.0, 4.0),
                "l_t_days": (5.0, 12.0),
            }
        )

    def _spec_from(self, params: ParameterProvider, grid: GridSpec) -> BasisSpec:
        """Bind the continuous parameters into a frozen BasisSpec."""
        return BasisSpec(
            alpha=float(params.resolve("spacing_alpha", grid)),
            l_t_days=float(params.resolve("l_t_days", grid)),
            n_dir=self.n_dir,
        )

    def _params_key(self, params: ParameterProvider, grid: GridSpec) -> str:
        """Serialize EVERYTHING eta depends on (spec §4.2.1; seam f)."""
        spec = self._spec_from(params, grid)
        rho = 10.0 ** float(params.resolve("log10_rho", grid))
        q_slope = float(params.resolve("q_slope", grid))
        return (
            f"{spec.key()};rho={rho!r};q_slope={q_slope!r};"
            f"pcg_rtol={self.pcg_rtol!r};pcg_maxiter={self.pcg_maxiter};"
            f"cal={self._calibration.key()}"
        )

    def solve(
        self,
        obs: ObsWindow,
        grid: GridSpec,
        params: ParameterProvider,
        time_days: float,
    ) -> MiostPointDistribution | MiostEnsembleDistribution:
        """Solve the <=2 covering windows (cached), blend, return the day map.

        In ensemble mode (``members > 0``) the day's perturbed-observation
        ensemble is returned instead, s*-inflated by exact anomaly rescale;
        its mean IS the Stage-A mean (D6 — bit-identical arrays).

        Args:
            obs: The FULL observation window (method re-subsets per window).
            grid: Output grid.
            params: Parameter provider (spacing_alpha, log10_rho, q_slope, l_t_days).
            time_days: Output day [days since epoch].

        Returns:
            The POINT predictive distribution at ``time_days``, or the
            SAMPLES ensemble in ensemble mode.
        """
        if self.members > 0:
            assert self.member_root is not None  # noqa: S101 (checked in __init__)
            ens = self.sample_members(
                obs, grid, params, time_days, m=self.members, root=self.member_root
            )
            # One general eval path: the calibration rides the query-time √s(x)
            # layer (no anomaly mutation). ``self._calibration`` is either the
            # scalar inflation_s shim or a Phase-8 CalibrationField.
            return ens.with_calibration(self._calibration)
        spec = self._spec_from(params, grid)
        rho = 10.0 ** float(params.resolve("log10_rho", grid))
        q_slope = float(params.resolve("q_slope", grid))
        pk = self._params_key(params, grid)
        fp = _obs_fingerprint(obs)
        wins = self._plan.covering(time_days)
        mean = np.zeros(grid.shape[0] * grid.shape[1])
        etas: dict[str, np.ndarray] = {}
        starts: dict[str, float] = {}
        for w in wins:
            eta = self._solve_window(w, spec, rho, q_slope, pk, fp, obs)
            els, s = self._s_matrix(w, spec, pk, grid)
            day_map = s @ time_contract(spec, els, eta, time_days)
            mean += self._plan.weight(w, time_days) * day_map
            etas[w.id] = eta
            starts[w.id] = w.start_day
        prov = UncertaintyProvenance(
            native_capability=self.native_capability, transformations=[]
        )
        return MiostPointDistribution(
            grid=grid,
            mean=mean.reshape(grid.shape),
            provenance=prov,
            time_days=time_days,
            _spec=spec,
            _etas=etas,
            _window_starts=starts,
            _w_days=self._plan.w_days,
        )

    def sample_members(
        self,
        obs: ObsWindow,
        grid: GridSpec,
        params: ParameterProvider,
        time_days: float,
        m: int,
        root: Seed,
    ) -> MiostEnsembleDistribution:
        """Generate m perturbed-observation members (spec 6.2; plan Task 15).

        Per covering window: build the m member RHS
        ``G^T R^-1 (y + eps'_i) + Q^-1 eta~_i`` with identity-keyed CRN
        perturbations and run ONE batched solve. The unperturbed eta^a path
        (:meth:`solve` / ``_solve_window``) is untouched; the ensemble mean
        IS the Stage-A mean (D6).

        Args:
            obs: The FULL observation window (method re-subsets per window).
            grid: Output grid.
            params: Parameter provider (the tuned winner's params).
            time_days: Output day [days since epoch].
            m: Member count.
            root: CRN seed root (derive_seed of the unit of work).

        Returns:
            The coefficient-space SAMPLES distribution.
        """
        from sverdrup.distributions.miost_ensemble import (
            MiostEnsembleDistribution,
            ensemble_provenance,
        )

        spec = self._spec_from(params, grid)
        rho = 10.0 ** float(params.resolve("log10_rho", grid))
        q_slope = float(params.resolve("q_slope", grid))
        pk = self._params_key(params, grid)
        fp = _obs_fingerprint(obs)
        wins = self._plan.covering(time_days)
        mean = np.zeros(grid.shape[0] * grid.shape[1])
        etas_a: dict[str, np.ndarray] = {}
        anoms: dict[str, np.ndarray] = {}
        starts: dict[str, float] = {}
        for w in wins:
            eta_a = self._solve_window(w, spec, rho, q_slope, pk, fp, obs)
            mask = _window_mask(obs, w, spec.l_t_days)
            coords = obs.coords()
            lon, lat, t = coords[mask, 0], coords[mask, 1], coords[mask, 2]
            y = obs.values()[mask]
            mission = None if obs.mission is None else obs.mission[mask]
            els = spec.elements_for_window(w.start_day, w.w_days)
            g = build_g(spec, els, lon, lat, t)
            q = DiagonalQ(rho=rho, q_slope=q_slope).variances_for(els)
            r = np.full(y.size, R_REF)
            obs_ident = _obs_identity(lon, lat, t, mission)
            b = member_rhs_matrix(g, r, y, q, obs_ident, els.identity, m, root)
            solver = MiostSolver(
                g,
                r_diag=r,
                q_diag=q,
                pcg_rtol=self.pcg_rtol,
                pcg_maxiter=self.pcg_maxiter,
            )
            members, mreport = solver.solve(b)  # ONE batched solve per window
            del g, solver
            CONVERGENCE_LOG.append(
                {
                    "window": w.id,
                    "kind": "member-batch",
                    "iterations": int(mreport.iterations.max()),
                    "final_rel_residual": float(mreport.final_rel_residual.max()),
                    "params_key_hash": _params_key_hash(pk),
                }
            )
            if mreport.final_rel_residual.max() > self.pcg_rtol:
                # surfaced, never swallowed (spec §2.4)
                print(
                    f"miost window {w.id}: member-batch PCG residual "
                    f"{mreport.final_rel_residual.max():.2e} after "
                    f"{mreport.iterations.max()} iters (rtol {self.pcg_rtol})"
                )
            els_s, s = self._s_matrix(w, spec, pk, grid)
            mean += self._plan.weight(w, time_days) * (
                s @ time_contract(spec, els_s, eta_a, time_days)
            )
            etas_a[w.id] = np.asarray(eta_a)
            anoms[w.id] = np.asarray(members) - np.asarray(eta_a)[:, None]
            starts[w.id] = w.start_day
        return MiostEnsembleDistribution(
            grid=grid,
            mean=mean.reshape(grid.shape),
            provenance=ensemble_provenance(m),
            time_days=time_days,
            m=m,
            _spec=spec,
            _etas_a=etas_a,
            _anoms=anoms,
            _window_starts=starts,
            _w_days=self._plan.w_days,
        )

    def _solve_window(
        self,
        w: Window,
        spec: BasisSpec,
        rho: float,
        q_slope: float,
        pk: str,
        fp: str,
        obs: ObsWindow,
    ) -> np.ndarray:
        """Solve one window's reduced normal equations (cached; G freed after)."""
        key = (w.id, pk, fp)
        if self.cache and key in self._eta_cache:
            return self._eta_cache[key]
        lon, lat, t, y = _window_obs(obs, w, spec.l_t_days)
        els = spec.elements_for_window(w.start_day, w.w_days)
        g = build_g(spec, els, lon, lat, t)
        q = DiagonalQ(rho=rho, q_slope=q_slope).variances_for(els)
        r = np.full(y.size, R_REF)
        solver = MiostSolver(
            g, r_diag=r, q_diag=q, pcg_rtol=self.pcg_rtol, pcg_maxiter=self.pcg_maxiter
        )
        eta, report = solver.solve(
            rhs_from_obs(g, r, y) if y.size else np.zeros(q.size)
        )
        del g, solver  # G freed after the window solve (hardening 2)
        CONVERGENCE_LOG.append(
            {
                "window": w.id,
                "iterations": int(report.iterations.max())
                if report.iterations.size
                else 0,
                "final_rel_residual": float(report.final_rel_residual.max())
                if report.final_rel_residual.size
                else 0.0,
                "params_key_hash": _params_key_hash(pk),
            }
        )
        if (
            report.final_rel_residual.size
            and report.final_rel_residual.max() > self.pcg_rtol
        ):
            # surfaced, never swallowed (spec §2.4)
            print(
                f"miost window {w.id}: PCG residual "
                f"{report.final_rel_residual.max():.2e} after "
                f"{report.iterations.max()} iters (rtol {self.pcg_rtol})"
            )
        eta = np.asarray(eta)
        if self.cache:
            self._eta_cache[key] = eta
        return eta

    def _s_matrix(
        self, w: Window, spec: BasisSpec, pk: str, grid: GridSpec
    ) -> tuple[Elements, sparse.csr_matrix]:
        """Per-window spatial S at the grid (<=2 live entries; hardening 2)."""
        key = (w.id, pk)
        if self.cache and key in self._s_cache:
            self._s_cache.move_to_end(key)
            return self._s_cache[key]
        els = spec.elements_for_window(w.start_day, w.w_days)
        lon2d, lat2d = np.meshgrid(grid.x, grid.y)
        s = build_s_spatial(spec, els, lon2d.ravel(), lat2d.ravel())
        if self.cache:
            self._s_cache[key] = (els, s)
            while len(self._s_cache) > 2:
                self._s_cache.popitem(last=False)
        return els, s


# --- Stage-B accepted configuration (Task-19 gate, owner sign-off 2026-07-07) ---
STAGE_B_MEMBERS = 100
STAGE_B_ROOT = (
    4836134738817689931  # derive_seed("miost", "stage-b-winner", "members", 0)
)
STAGE_B_INFLATION_S = 10.062847634082484  # s* frozen from corrected-framing validation


def shipped_miost() -> Miost:
    """The SHIPPED miost product: SAMPLES-native at the accepted Stage-B config.

    Sigma semantics (owner-ordered at the gate close, 2026-07-07): the
    shipped sigma is CALIBRATED PREDICTIVE uncertainty against along-track
    residuals via ONE global scalar s (``STAGE_B_INFLATION_S``) — it
    includes representation error and unresolved scales, and is NOT the raw
    posterior spread; the correlation STRUCTURE is the raw posterior's (the
    sqrt(s) anomaly rescale preserves it). ``chi2_red(s*) = 1`` on
    validation is a mechanism identity, not evidence — the evidence is
    coverage_1sigma 0.7481 on validation and 0.7481 on the single c2
    acceptance touch (both within 0.6827±0.10) and CRPS ~0.047-0.048 m.

    Known limitation (recorded): one global s mildly under-disperses in the
    jet-core northern quadrants (coverage ~0.69, chi2 ~1.3) and
    over-disperses south (~0.79-0.83) — see the localized-calibration table
    (gate results JSON, ``stage_b.localized_calibration``); a
    spatially-varying s is future work, out of scope.

    Tuning note: parameter SEARCHES must use a POINT-configured ``Miost()``
    (members=0) — members are generated at tuned winners only (spec 6.1),
    never per-trial.

    Returns:
        The ensemble-mode method with m, seed root, and s* as accepted.
    """
    from sverdrup.distributions.miost_ensemble import ScalarCalibration

    return Miost(
        members=STAGE_B_MEMBERS,
        member_root=STAGE_B_ROOT,
        calibration=ScalarCalibration(STAGE_B_INFLATION_S),
    )
