"""MIOST method: POINT distribution + window-cache Method (spec §4; Stage A)."""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy import sparse  # type: ignore[import-untyped]

from sverdrup.core.distribution import CapabilityNotAvailableError
from sverdrup.core.grid import GridSpec
from sverdrup.core.observations import ObsWindow
from sverdrup.core.parameters import ParameterProvider, ParameterSpace
from sverdrup.core.provenance import UncertaintyProvenance
from sverdrup.core.types import Field, Points, Seed, UncertaintyCapability
from sverdrup.methods.miost_basis import (
    N_DIR,
    R_REF,
    BasisSpec,
    DiagonalQ,
    Elements,
    build_g,
    build_s,
    lonlat_to_km,
    temporal_taper,
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

    @classmethod
    def from_etas(
        cls,
        grid: GridSpec,
        time_days: float,
        spec: BasisSpec,
        etas: dict[str, np.ndarray],
        window_starts: dict[str, float],
    ) -> MiostPointDistribution:
        """Build the distribution from solved window coefficients.

        Args:
            grid: Output grid.
            time_days: Output day [days since epoch].
            spec: Basis specification the coefficients belong to.
            etas: window_id -> solved coefficient vector.
            window_starts: window_id -> window start day.

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
        plan = WindowPlan(starts=tuple(sorted(self._window_starts.values())))
        out = np.zeros(pts.shape[0])
        for wid, eta in self._etas.items():
            w = Window(self._window_starts[wid])
            in_w = (t >= w.start_day) & (t <= w.end_day)
            if not in_w.any():
                continue
            els = self._spec.elements_for_window(w.start_day)
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
            )
            # bit-identity guaranteed by storing the mean too
            out.mean = np.asarray(z["mean"])
        return out


def _obs_fingerprint(obs: ObsWindow) -> str:
    """Content hash of the obs (spec §4.2.1: wrong-becomes-slow, never wrong-becomes-wrong)."""
    h = hashlib.blake2b(digest_size=16)
    h.update(obs.coords().tobytes())
    h.update(obs.values().tobytes())
    return h.hexdigest()


def _window_obs(
    obs: ObsWindow, w: Window, l_t_days: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Subset obs to [start - L_t, end + L_t]; loud span assert (spec §4.2.1).

    Args:
        obs: The FULL observation window (wide temporal_half_window_days).
        w: The solve window.
        l_t_days: Temporal support half-width.

    Returns:
        (lon, lat, t, values) of the in-window observations.

    Raises:
        ValueError: If nonempty obs do not span the window's support interval
            (clipped to the obs data span) — pass the full obs.
    """
    coords = obs.coords()
    t = coords[:, 2]
    lo = max(w.start_day - l_t_days, OBS_START_DAY)
    hi = min(w.end_day + l_t_days, OBS_END_DAY)
    if len(obs) and (t.min() > lo + 1e-9 or t.max() < hi - 1e-9):
        raise ValueError(
            f"obs do not span window {w.id} support [{lo}, {hi}] "
            f"(got [{t.min()}, {t.max()}]) — pass the full obs "
            "(wide temporal_half_window_days)"
        )
    m = (t >= lo) & (t <= hi)
    return coords[m, 0], coords[m, 1], t[m], obs.values()[m]


class Miost:
    """MIOST window-cache Method (spec §4.2). native_capability = POINT (Stage A)."""

    native_capability = UncertaintyCapability.POINT

    def __init__(self, n_dir: int = N_DIR, cache: bool = True) -> None:
        """Create the method with empty caches.

        Args:
            n_dir: Plane-wave direction count (D2 diagnostic override; default D1).
            cache: Disable to force fresh solves (cache-correctness tests).
        """
        self.n_dir = n_dir
        self.cache = cache
        self._plan = WindowPlan()
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
            f"pcg_rtol={PCG_RTOL!r};pcg_maxiter={PCG_MAXITER}"
        )

    def solve(
        self,
        obs: ObsWindow,
        grid: GridSpec,
        params: ParameterProvider,
        time_days: float,
    ) -> MiostPointDistribution:
        """Solve the <=2 covering windows (cached), blend, return the day map.

        Args:
            obs: The FULL observation window (method re-subsets per window).
            grid: Output grid.
            params: Parameter provider (spacing_alpha, log10_rho, q_slope, l_t_days).
            time_days: Output day [days since epoch].

        Returns:
            The POINT predictive distribution at ``time_days``.
        """
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
            day_map = s @ (eta * temporal_taper(spec, els, time_days))
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
        els = spec.elements_for_window(w.start_day)
        g = build_g(spec, els, lon, lat, t)
        q = DiagonalQ(rho=rho, q_slope=q_slope).variances_for(els)
        r = np.full(y.size, R_REF)
        solver = MiostSolver(g, r_diag=r, q_diag=q)
        eta, report = solver.solve(
            rhs_from_obs(g, r, y) if y.size else np.zeros(q.size)
        )
        del g, solver  # G freed after the window solve (hardening 2)
        if (
            report.final_rel_residual.size
            and report.final_rel_residual.max() > PCG_RTOL
        ):
            # surfaced, never swallowed (spec §2.4)
            print(
                f"miost window {w.id}: PCG residual "
                f"{report.final_rel_residual.max():.2e} after "
                f"{report.iterations.max()} iters (rtol {PCG_RTOL})"
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
        els = spec.elements_for_window(w.start_day)
        lon2d, lat2d = np.meshgrid(grid.x, grid.y)
        s = build_s(spec, els, lon2d.ravel(), lat2d.ravel())
        if self.cache:
            self._s_cache[key] = (els, s)
            while len(self._s_cache) > 2:
                self._s_cache.popitem(last=False)
        return els, s
