"""MIOST method: POINT distribution + window-cache Method (spec §4; Stage A)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from sverdrup.core.distribution import CapabilityNotAvailableError
from sverdrup.core.grid import GridSpec
from sverdrup.core.provenance import UncertaintyProvenance
from sverdrup.core.types import Field, Points, Seed, UncertaintyCapability
from sverdrup.methods.miost_basis import BasisSpec, lonlat_to_km
from sverdrup.methods.miost_windows import Window, WindowPlan


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
