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
    from sverdrup.distributions.calibration import (
        CalibratedDistribution,
        CalibrationField,
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
from sverdrup.methods.miost_crn import coef_noise, err_noise, obs_noise
from sverdrup.methods.miost_error_basis import (
    build_b,
    err_identity,
    lam_diag,
    mission_hash_ints,
    segment_passes,
)
from sverdrup.methods.miost_rspec import RSpec
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
    err_ident: np.ndarray | None = None,
) -> np.ndarray:
    """Build the m member right-hand sides for one window (spec 6.2, §5).

    Column i is ``G_aug^T R^-1 (y + eps'_i) + Q_aug^-1 [eta~_i; c~_i]``
    with identity-keyed CRN perturbations; without ``err_ident`` this is
    the scalar-era ``G^T R^-1 (y + eps'_i) + Q^-1 eta~_i`` unchanged.
    Shared by :meth:`Miost.sample_members` and the Stage-B exactness
    oracle — one construction, tested against dense ``A^-1``.

    Args:
        g: CSR observation operator (augmented [G B] when modes active).
        r: (n_obs,) diagonal R (per-mission under a structured rspec).
        y: (n_obs,) observed values (empty allowed).
        q: (n_col,) diagonal Q (``Q_aug = concat(Q, Λ)`` when augmented).
        obs_identity: (n_obs, 4) CRN identity rows (see _obs_identity).
        els_identity: (n_el, 6) element identity rows (the FIELD block).
        m: Member count.
        root: CRN seed root.
        err_ident: Optional (n_mode, 3) mode identity rows (``err_identity``)
            — present iff ``q`` carries the Λ tail; c̃ draws ride the
            "err" axis (spec §5).

    Returns:
        (n_col, m) RHS matrix.
    """
    n_field = els_identity.shape[0]
    base = rhs_from_obs(g, r, y) if y.size else np.zeros(q.size)
    b = np.empty((q.size, m))
    for i in range(m):
        eta_t = coef_noise(i, els_identity, q[:n_field], root)
        if err_ident is not None:
            c_t = err_noise(i, err_ident, q[n_field:], root)
            prior = np.concatenate([eta_t, c_t])
        else:
            prior = eta_t
        b[:, i] = base + prior / q
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
        rspec: RSpec | None = None,
        member_solve_checkpoint_dir: Path | None = None,
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
            rspec: Phase-13 structured observation-error spec. None (the
                default) = the scalar-era configuration, byte-identical
                behavior AND params_key. A structured spec switches
                ``_solve_window`` to per-mission R (and, when modes are
                active, the augmented [G B] assembly with the field-block
                slice at return).
            member_solve_checkpoint_dir: Optional directory for per-window
                crash-durable PCG checkpoints of the member batch (the
                solve resumes bit-identically after a kill; see
                ``MiostSolver.solve``). None = no checkpointing.

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
        from sverdrup.distributions.calibration import ScalarCalibration

        self.n_dir = n_dir
        self.cache = cache
        self.pcg_rtol = pcg_rtol
        self.pcg_maxiter = pcg_maxiter
        self.members = members
        self.member_root = member_root
        self.inflation_s = inflation_s
        self.rspec = rspec if rspec is not None else RSpec()
        self.member_solve_checkpoint_dir = member_solve_checkpoint_dir
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
        """Return the tunable boxes (plan-fixed + phase-13 structured-R dims).

        The structured-R bounds are WIDE method-level boxes (plan Task 2);
        the pre-registered SWEEP boxes are sealed in ``phase13_boxes.py``.

        CONSUMPTION SEAM (recorded at Task-2 review): the structured-R dims
        are consumed through the ``rspec`` constructor argument — the
        phase-13 lane runner builds an :class:`RSpec` per trial. ``solve``
        does NOT read them from the ParameterProvider, so a tuner that
        enumerates these bounds into trial params (the legacy Stage-A
        sweep) would sweep dead dimensions; that tuner must not be pointed
        at the structured dims.
        """
        return ParameterSpace(
            bounds={
                "spacing_alpha": (0.5, 1.5),
                "log10_rho": (-2.0, 3.0),
                "q_slope": (0.0, 4.0),
                "l_t_days": (5.0, 12.0),
                "delta_alg": (-3.0, 3.0),
                "delta_h2g": (-3.0, 3.0),
                "delta_j2g": (-3.0, 3.0),
                "delta_j2n": (-3.0, 3.0),
                "log_lam_bias": (-8.0, -1.0),
                "log_lam_tilt": (-8.0, -1.0),
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
        # rspec fragment is "" for the scalar config — scalar-era keys stay
        # byte-identical (cache lineage, spec §2 rider 5 / §11).
        return (
            f"{spec.key()};rho={rho!r};q_slope={q_slope!r};"
            f"pcg_rtol={self.pcg_rtol!r};pcg_maxiter={self.pcg_maxiter};"
            f"cal={self._calibration.key()}{self.rspec.key()}"
        )

    def solve(
        self,
        obs: ObsWindow,
        grid: GridSpec,
        params: ParameterProvider,
        time_days: float,
    ) -> MiostPointDistribution | CalibratedDistribution:
        """Solve the <=2 covering windows (cached), blend, return the day map.

        In ensemble mode (``members > 0``) the day's perturbed-observation
        ensemble is returned as a CalibratedDistribution wrapping the raw
        MiostEnsembleDistribution; its mean IS the Stage-A mean (D6 — bit-
        identical arrays).

        Args:
            obs: The FULL observation window (method re-subsets per window).
            grid: Output grid.
            params: Parameter provider (spacing_alpha, log10_rho, q_slope, l_t_days).
            time_days: Output day [days since epoch].

        Returns:
            The POINT predictive distribution at ``time_days``, or a
            CalibratedDistribution wrapping the raw SAMPLES ensemble in
            ensemble mode.
        """
        if self.members > 0:
            assert self.member_root is not None  # noqa: S101 (checked in __init__)
            # Phase-9 §3: calibration rides the shared CalibratedDistribution
            # wrapper (distributions/calibration.py) — relocated from the
            # class-internal seam with NO semantic change; identity-proven at
            # rtol 1e-12 / mean-bit. sample_members builds the wrapper (with
            # ``self._calibration`` — the scalar inflation_s shim or a Phase-8
            # CalibrationField); returning it directly keeps the append single.
            return self.sample_members(
                obs, grid, params, time_days, m=self.members, root=self.member_root
            )
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
    ) -> CalibratedDistribution:
        """Generate m perturbed-observation members (spec 6.2; plan Task 15).

        Per covering window: build the m member RHS
        ``G^T R^-1 (y + eps'_i) + Q^-1 eta~_i`` with identity-keyed CRN
        perturbations and run ONE batched solve. The unperturbed eta^a path
        (:meth:`solve` / ``_solve_window``) is untouched; the ensemble mean
        IS the Stage-A mean (D6).

        Phase-9 §3: the raw coefficient ensemble is returned WRAPPED in a
        CalibratedDistribution carrying ``self._calibration`` (default
        ScalarCalibration(1.0) — an identity wrap that appends no provenance
        transform). The raw instance is reachable as ``.underlying``.

        Args:
            obs: The FULL observation window (method re-subsets per window).
            grid: Output grid.
            params: Parameter provider (the tuned winner's params).
            time_days: Output day [days since epoch].
            m: Member count.
            root: CRN seed root (derive_seed of the unit of work).

        Returns:
            A CalibratedDistribution wrapping the coefficient-space SAMPLES
            distribution.
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
            n_elem = els.identity.shape[0]
            g = build_g(spec, els, lon, lat, t)
            q = DiagonalQ(rho=rho, q_slope=q_slope).variances_for(els)
            # Structured R (spec §5): ε' stays WHITE per-obs with the
            # per-mission variances; active modes augment [G B] and the c̃
            # prior draws ride the "err" axis on time-based identities.
            if self.rspec.is_scalar:
                r = np.full(y.size, R_REF)
                mission_mh: np.ndarray | None = None
            else:
                if mission is None:
                    raise ValueError(
                        "structured rspec requires per-obs mission labels "
                        "(identity-keyed σ²_m lookup, never positional)"
                    )
                mission_mh = mission_hash_ints(mission)
                r = self.rspec.sigma2_for(mission_mh)
            if self.rspec.modes_active:
                assert mission_mh is not None  # noqa: S101 (guarded above)
                pt = segment_passes(lon, lat, t, mission_mh)
                g_use = sparse.hstack([g, build_b(pt)], format="csr")
                q_use = np.concatenate(
                    [q, lam_diag(pt.n_pass, self.rspec.lam_bias, self.rspec.lam_tilt)]
                )
                err_id: np.ndarray | None = err_identity(pt)
            else:
                g_use, q_use, err_id = g, q, None
            obs_ident = _obs_identity(lon, lat, t, mission)
            b = member_rhs_matrix(
                g_use, r, y, q_use, obs_ident, els.identity, m, root, err_ident=err_id
            )
            solver = MiostSolver(
                g_use,
                r_diag=r,
                q_diag=q_use,
                pcg_rtol=self.pcg_rtol,
                pcg_maxiter=self.pcg_maxiter,
            )
            ck_dir = self.member_solve_checkpoint_dir
            members, mreport = solver.solve(  # ONE batched solve per window
                b,
                checkpoint=(ck_dir / f"pcg_{w.id}.npz" if ck_dir else None),
            )
            del g, g_use, solver
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
            # retention slicing (spec §12): the c-block is TRANSIENT — the
            # retained anomaly store holds FIELD-BLOCK rows only, so its
            # size is unchanged by augmentation (eta_a is already sliced).
            anoms[w.id] = np.asarray(members)[:n_elem] - np.asarray(eta_a)[:, None]
            starts[w.id] = w.start_day
        from sverdrup.distributions.calibration import CalibratedDistribution
        from sverdrup.distributions.miost_ensemble import KIND, KIND_AUG

        raw = MiostEnsembleDistribution(
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
            state_kind=KIND if self.rspec.is_scalar else KIND_AUG,
        )
        return CalibratedDistribution(
            raw, self._calibration, UncertaintyCapability.SAMPLES
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
        """Solve one window's reduced normal equations (cached; G freed after).

        Phase-13 structured R (spec §2): a per-mission ``rspec`` swaps the
        scalar R for the identity-keyed σ²_m lookup; active modes augment
        the assembly to [G B] with Q_aug = concat(Q, Λ). The returned (and
        cached) eta is ALWAYS the field-block slice — the c-block is
        solver-internal and contributes nothing downstream (rider 1).
        """
        key = (w.id, pk, fp)
        if self.cache and key in self._eta_cache:
            return self._eta_cache[key]
        mask = _window_mask(obs, w, spec.l_t_days)
        coords = obs.coords()
        lon, lat, t = coords[mask, 0], coords[mask, 1], coords[mask, 2]
        y = obs.values()[mask]
        els = spec.elements_for_window(w.start_day, w.w_days)
        n_elem = els.identity.shape[0]
        g = build_g(spec, els, lon, lat, t)
        q = DiagonalQ(rho=rho, q_slope=q_slope).variances_for(els)
        if self.rspec.is_scalar:
            r = np.full(y.size, R_REF)
            mission_mh: np.ndarray | None = None
        else:
            if obs.mission is None:
                raise ValueError(
                    "structured rspec requires per-obs mission labels "
                    "(identity-keyed σ²_m lookup, never positional)"
                )
            mission_mh = mission_hash_ints(obs.mission[mask])
            r = self.rspec.sigma2_for(mission_mh)
        if self.rspec.modes_active:
            assert mission_mh is not None  # noqa: S101 (guarded above)
            pt = segment_passes(lon, lat, t, mission_mh)
            g_use = sparse.hstack([g, build_b(pt)], format="csr")
            q_use = np.concatenate(
                [q, lam_diag(pt.n_pass, self.rspec.lam_bias, self.rspec.lam_tilt)]
            )
        else:
            # structural COLUMN ABSENCE (rider 3) — never a Λ=0 diagonal
            g_use, q_use = g, q
        solver = MiostSolver(
            g_use,
            r_diag=r,
            q_diag=q_use,
            pcg_rtol=self.pcg_rtol,
            pcg_maxiter=self.pcg_maxiter,
        )
        eta, report = solver.solve(
            rhs_from_obs(g_use, r, y) if y.size else np.zeros(q_use.size)
        )
        eta = np.asarray(eta)[:n_elem]  # field block ONLY (rider 1)
        del g, g_use, solver  # G freed after the window solve (hardening 2)
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
# Scalar s* — superseded by the Phase-8 field 2026-07-12, kept for the signed
# Stage-B record (the coverage-0.7481 / chi2_red(s*)=1 sign-off is anchored to it).
STAGE_B_INFLATION_S = 10.062847634082484  # s* frozen from corrected-framing validation

# --- Phase-8 accepted field (gate, owner sign-off 2026-07-12) ---
# The winning CLIPPED low-order polynomial (5 dof) from the held-out selection.
# Constants inlined from the signed evidence (data/2021a_ssh_mapping_ose/ours/
# phase8_field.json + the phase8 block of stage_miost_gate_results.json); the
# assembled PolyCalibration.key() is byte-identical to that artifact's cal_key.
# log s = a0 + a1·v + a2·v² + a3·u + a4·u·v,  u=(lon−300)/5, v=(lat−38)/5.
PHASE8_POLY_COEFFS: tuple[float, float, float, float, float] = (
    2.628363705995422,
    0.6473150127828258,
    -2.2371390187292186,
    -0.1485348137468948,
    0.5330366783275191,
)
# Evidence-anchored log-s clip (lane-A range ± log 1.25).
PHASE8_CLIP_LO = 1.1731020392124571
PHASE8_CLIP_HI = 2.9290288130316813
PHASE8_FIT_ID = "L-BFGS-B;gtol=1e-08"


def shipped_miost5() -> Miost:
    """The five-mission calibration-lineage REFERENCE product (miost5 generation).

    SHIPPED["miost"] until the Phase-12 flip (owner sign-off 2026-07-18);
    retained as a named factory forever: every five-mission signed artifact
    (stage-B maps, phase8 field selection, the 0.8573/156.43 acceptance) pins
    THIS configuration. SAMPLES-native at the accepted Phase-8 config.

    Sigma semantics (owner-ordered at the Phase-8 gate close, 2026-07-12): the
    shipped sigma is CALIBRATED PREDICTIVE uncertainty against along-track
    residuals via a SPATIALLY-VARYING field s(x) — a **clipped low-order
    polynomial** (dof 5) in normalised box coordinates, superseding the retired
    global scalar. The field is
    ``cal:poly;coeffs=(2.628363705995422, 0.6473150127828258,
    -2.2371390187292186, -0.1485348137468948, 0.5330366783275191);
    clip=(1.1731020392124571,2.9290288130316813);fit=L-BFGS-B;gtol=1e-08``
    (``cal_key``, byte-identical to phase8_field.json). It includes
    representation error and unresolved scales and is NOT the raw posterior
    spread; the correlation STRUCTURE is the raw posterior's — cross-point
    uncertainties scale by ``√(s(x)·s(y))`` and the underlying correlations are
    preserved EXACTLY (the √s(x) anomaly rescale is diagonal in the field).

    Floor-exclusion delta: the map product carries ``σ²(x) = s(x)·v`` (posterior
    variance × field); the along-track VALIDATION variance additionally adds the
    observation floor, ``s(x)·v + SIGMA_OBS2`` (0.03² m²). The gridded σ² does
    NOT include that floor — the map reports predictive-field variance, the
    coverage/chi2 numbers below are the floored track-side statistic.

    Per-region c2 coverage evidence (touch 2, full-year n=44,844; ∈ 0.6827±0.10
    → aggregate **0.7350**): SW 0.775 / SE 0.753 / NW 0.707 / NE 0.705 /
    jet_core 0.674 — no severe local mis-calibration.

    Edge behavior: coordinates outside the box are clamped to the box hull
    (constant continuation), then log-s is clipped to the evidence-anchored
    bounds ``[1.1731020392124571, 2.9290288130316813]``. The clip floor is
    active on 37.2% of box+halo nodes (max excursion 2.11 log-s) — working as
    designed; the held-out selection judged the CLIPPED field. [†] The off-track
    √s gradient reported for diagnostics is the RAW-poly gradient, because the
    clipped plateaus have zero gradient.

    Jet-core residual (recorded, not resolved): c2 jet_core 0.674 at chi2 1.29,
    improved from the scalar era's 0.643 / 1.43 but still below the coverage
    target — the field narrows the motivating defect without closing it.

    August limitation (recorded): monthly j3 coverage 0.691 (scalar) → 0.655
    (field), still in band; the seasonal axis is out of scope per fork (c) — no
    seasonal calibration term ships.

    Mean maps are bit-UNCHANGED by the calibration flip: proven on the touch-2
    c2 evaluation, where the (µ, σ, λx) triplet reproduces the signed Stage-A
    values bit-identically (the field rides the query-time √s(x) layer only, D6).

    Mechanism (Phase 9): the field rides the shared CalibratedDistribution
    wrapper (distributions/calibration.py) — relocated from the class-internal
    seam with NO semantic change; identity-proven at rtol 1e-12 / mean-bit.

    Honest tally note: this product's acceptance spent TWO c2 touches — touch 1
    was a partial-window DEFECT-RUN (disclosed, preserved under
    ``phase8.c2_defect_run_20260712``, never used as evidence); touch 2 is the
    accepted full-year evaluation.

    Tuning note: parameter SEARCHES must use a POINT-configured ``Miost()``
    (members=0) — members are generated at tuned winners only (spec 6.1),
    never per-trial.

    Returns:
        The ensemble-mode method with m, seed root, and the Phase-8 field.
    """
    from sverdrup.distributions.calibration import ClipSpec, PolyCalibration

    return Miost(
        members=STAGE_B_MEMBERS,
        member_root=STAGE_B_ROOT,
        calibration=PolyCalibration(
            coeffs=PHASE8_POLY_COEFFS,
            clip=ClipSpec(lo_log_s=PHASE8_CLIP_LO, hi_log_s=PHASE8_CLIP_HI),
            fit_id=PHASE8_FIT_ID,
        ),
    )


def shipped_miost6() -> Miost:
    """The SHIPPED six-mission flagship (miost6 generation, Phase-12 flip).

    Identical FROZEN solver/calibration configuration to
    :func:`shipped_miost5` — winner params, m=100, STAGE_B_ROOT, the Phase-8
    s(x) field — run with j3 ASSIMILATED (six missions, leaderboard
    convention). A separate function purely for provenance: the phase-12
    record (`phase12.miost6.*` in the evidence store) anchors THIS name.

    Acceptance (the ONE phase-12 c2 touch, owner-authorized fresh
    2026-07-18): µ 0.8677794298228094, σ 0.08229205674809689,
    λx 151.22280673169575 km; aggregate c2 coverage 0.7307332084559808
    (χ²_red 0.9906981743442226, CRPS 0.0427).

    Sigma semantics — TRANSFERRED-AND-VERIFIED: s(x) fit on the
    five-mission configuration (j3 held out), transferred frozen; the
    pre-registered expectation was mild over-coverage; MEASURED
    Δcoverage = −0.0043 vs the 0.7350 referent ≈ 0.6·SE (n_eff ≈ n/10.27,
    SE ≈ 0.0067) — the transfer is NEUTRAL within noise; χ²_red 0.991;
    the regional structure reproduces region-by-region (max |Δ| 0.011:
    SW 0.7752/0.775, SE 0.7468/0.753, NW 0.6962/0.707, NE 0.7043/0.705,
    jet_core 0.6777/0.674). The constellation-dependence caveat for LARGE
    constellation changes (the 1993-era case) stands unchanged — this
    measured one small step, not that one.

    Recorded limitations (fork-c lineage, unchanged by transfer): August
    coverage 0.6364 / χ²_red 1.466 — the persisting seasonal trough, in
    band; jet_core 0.6777 remains the weakest region, slightly improved.

    Honest tally: this product line has spent THREE c2 touches —
    {miost5: 2 (defect-run + accepted), miost6: 1 (this acceptance)}.

    Returns:
        The ensemble-mode method at the frozen config (six-mission use is a
        property of the obs handed to solve, not of this factory).
    """
    return shipped_miost5()
