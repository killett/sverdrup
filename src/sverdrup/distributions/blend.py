"""Partition-of-unity crossfade blend over a GridSpec or PointSet (design section 4)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, cast

import numpy as np

from sverdrup.core.distribution import PredictiveDistribution
from sverdrup.core.geometry import Tile
from sverdrup.core.grid import GridSpec, PointSet
from sverdrup.core.provenance import UncertaintyProvenance, blend_transform
from sverdrup.core.types import CovFidelity, Field, Points, Seed
from sverdrup.distributions.coherent import (
    CoherentSampler,
    NoiseSpec,
    _nearest,
    _support_points,
    select_driver,
)


def _smootherstep(t: np.ndarray) -> np.ndarray:
    """Quintic 6t^5-15t^4+10t^3, clamped to [0,1]; value & 1st deriv vanish at 0 and 1."""
    t = np.clip(t, 0.0, 1.0)
    return np.asarray(t**3 * (t * (t * 6.0 - 15.0) + 10.0))


def _axis_taper(
    coord: np.ndarray, core: tuple[float, float], ext: tuple[float, float]
) -> np.ndarray:
    """Per-axis raw taper: 1 inside core, smootherstep down to 0 at the extended edge."""
    lo_c, hi_c = core
    lo_e, hi_e = ext
    left_pen = np.where(coord < lo_c, (lo_c - coord) / max(lo_c - lo_e, 1e-12), 0.0)
    right_pen = np.where(coord > hi_c, (coord - hi_c) / max(hi_e - hi_c, 1e-12), 0.0)
    pen = np.clip(left_pen + right_pen, 0.0, 1.0)  # 0 in core, 1 at extended edge
    inside = (coord >= lo_e) & (coord <= hi_e)
    return np.asarray(np.where(inside, 1.0 - _smootherstep(pen), 0.0))


def _raw_weight(tile: Tile, points: np.ndarray) -> np.ndarray:
    """Separable raw taper over lon & lat (product keeps it C1; min would kink at corners)."""
    lon, lat = points[:, 0], points[:, 1]
    tx = _axis_taper(lon, tile.core_window.lon_range, tile.extended_window.lon_range)
    ty = _axis_taper(lat, tile.core_window.lat_range, tile.extended_window.lat_range)
    return np.asarray(tx * ty)


def partition_weights(tiles: Sequence[Tile], points: np.ndarray) -> np.ndarray:
    """Return normalized partition-of-unity weights, shape ``(n_tiles, n_points)``.

    Args:
        tiles: The tiles whose core/halo geometry defines the crossfade.
        points: ``(n, 3)`` support points ``(lon, lat, time)``.

    Returns:
        Weights summing to 1 over tiles wherever at least one tile covers the point.
    """
    raw = np.stack([_raw_weight(t, points) for t in tiles])  # (n_tiles, n)
    total = raw.sum(axis=0)
    safe = np.where(total > 0, total, 1.0)
    return np.asarray(raw / safe)


@dataclass
class BlendInput:
    """One constituent: a predictive distribution (grid or PointSet) plus its tile geometry."""

    distribution: PredictiveDistribution
    tile: Tile


def _constituent_moments(
    parts: list[BlendInput], pts: Points
) -> tuple[np.ndarray, np.ndarray]:
    """Nearest-node mean and sigma of every constituent at ``pts`` -> (n_tiles, n)."""
    means, sigmas = [], []
    for p in parts:
        d = cast(Any, p.distribution)  # duck-typed .fields/.time_days across reps
        idx = _nearest(d.grid, pts, d.time_days)
        means.append(d.fields.mean.ravel()[idx])
        sigmas.append(np.sqrt(d.fields.marginal_variance.ravel()[idx]))
    return np.stack(means), np.stack(sigmas)


@dataclass
class BlendedDistribution:
    """A PredictiveDistribution on the union support: weight crossfade of constituents."""

    support: GridSpec | PointSet
    mean: Field
    _variance: Field
    provenance: UncertaintyProvenance
    fidelity: CovFidelity
    time_days: float
    _parts: list[BlendInput] = field(default_factory=list)
    _noise: NoiseSpec | None = None
    _sampler: CoherentSampler = field(default_factory=CoherentSampler)
    _cov_batch: np.ndarray | None = None

    @property
    def grid(self) -> GridSpec:
        """Return the GridSpec support (PredictiveDistribution contract; grid support only)."""
        return cast(GridSpec, self.support)

    @grid.setter
    def grid(self, value: GridSpec) -> None:
        """Set the support (keeps ``grid`` a settable variable per the Protocol)."""
        self.support = value

    def marginal_variance(self) -> Field:
        """Return the coherence-correct (corr=1) marginal-variance field."""
        return self._variance

    def _coherent_member(self, member_index: int, pts: Points) -> np.ndarray:
        """Realize one cross-tile-coherent member via the driver selected by sampler_spec.

        The driver is keyed on the persisted ``sampler_spec`` (post-persistence), so the
        low-rank OI rep, the sparse-precision GMRF rep, and the perturb-ensemble rep each
        bring their own coherence math without the blend knowing the method identity.
        """
        noise = self._noise
        if noise is None:
            raise RuntimeError("general path needs a NoiseSpec (set by BlendOperator)")
        parts = self._parts
        w = partition_weights([p.tile for p in parts], pts)  # (T, n)
        spec = cast(Any, parts[0].distribution).fields.sampler_spec
        driver = select_driver(spec)
        return driver.crossfaded_member(parts, pts, w, member_index, noise)

    def _grid_sample_batch(self, m: int = 256) -> np.ndarray:
        """Return a cached ``(m, n_grid)`` coherent-member matrix over the grid points.

        Computed once and reused so derived operators that read ``covariance`` node by
        node share a single realization instead of regenerating members per query.
        """
        if self._cov_batch is None or self._cov_batch.shape[0] != m:
            pts = _support_points(self.support, self.time_days)
            self._cov_batch = np.stack(
                [self._coherent_member(int(i), pts) for i in range(m)]
            )
        return self._cov_batch

    def covariance(self, a: Points, b: Points) -> np.ndarray:
        """Return the crossfaded sample covariance between ``a`` and ``b`` (general path).

        Query points are matched to nearest grid nodes and read from one cached
        coherent-member batch, so repeated node-by-node reads stay cheap.
        """
        m = 256
        s = self._grid_sample_batch(m)  # (m, n_grid)
        ia = _nearest(self.support, a, self.time_days)
        ib = _nearest(self.support, b, self.time_days)
        sa = s[:, ia]
        sb = s[:, ib]
        sa = sa - sa.mean(axis=0)
        sb = sb - sb.mean(axis=0)
        return np.asarray(sa.T @ sb / (m - 1))

    def sample(self, m: int, seed: Seed) -> np.ndarray:
        """Return ``m`` coherent crossfaded draws.

        Shape is ``(m, ny, nx)`` over a ``GridSpec`` support or ``(m, k)`` over a
        ``PointSet`` support.
        """
        pts = _support_points(self.support, self.time_days)
        rng = np.random.default_rng(seed)
        members = rng.integers(0, 2**31 - 1, size=m)
        draws = np.stack([self._coherent_member(int(i), pts) for i in members])
        if isinstance(self.support, PointSet):
            return np.asarray(draws.reshape(m, pts.shape[0]))
        ny, nx = self.grid.shape
        return np.asarray(draws.reshape(m, ny, nx))

    def regrid(self, target: GridSpec) -> BlendedDistribution:
        """Stage-B cross-projection regrid (Task 16)."""
        raise NotImplementedError("regrid lands with Stage B (Task 16).")


class BlendOperator:
    """Partition-of-unity crossfade over a GridSpec or PointSet (one support math)."""

    def blend(
        self,
        parts: Sequence[BlendInput],
        support: GridSpec | PointSet,
        *,
        k: float = 3.0,
        residual_bound: float = 0.0,
        structured_residual: bool = True,
        lattice_step: float = 0.25,
        method: str = "oi",
        params_key: str = "",
    ) -> BlendedDistribution:
        """Blend constituent Persisted distributions into one on ``support``.

        The mean and marginal variance follow the cheap moment crossfade
        (mean = sum w_i mean_i; sigma = sum w_i sigma_i, corr=1 so the mid-overlap
        variance does not dip). ``sample()``/``covariance()`` use the coherent-sample
        crossfade driven by the stored ``NoiseSpec``.

        Args:
            parts: The constituent ``BlendInput``s (one per overlapping tile).
            support: The union support to blend onto (``GridSpec`` or ``PointSet``).
            k: The halo multiple, recorded in provenance.
            residual_bound: Conservative finite-halo residual bound, recorded in provenance.
            structured_residual: Whether the member-only ``z_r`` driver is in use.
            lattice_step: Degrees per global driving-noise cell (coherence lattice).
            method: Method identity for the driving-noise seed derivation.
            params_key: Resolved-parameter identity for the driving-noise seed derivation.

        Returns:
            A ``BlendedDistribution`` with crossfaded mean and coherence-correct variance.
        """
        parts = list(parts)
        t = cast(Any, parts[0].distribution).time_days
        pts = _support_points(support, t)
        w = partition_weights([p.tile for p in parts], pts)  # (n_tiles, n)
        means, sigmas = _constituent_moments(parts, pts)
        mean = (w * means).sum(axis=0)
        sigma = (w * sigmas).sum(axis=0)  # coherence (corr=1) crossfade -> no dip
        base = parts[0].distribution.provenance
        transforms = [
            *base.transformations,
            blend_transform(k, residual_bound, structured_residual=structured_residual),
        ]
        spec0 = cast(Any, parts[0].distribution).fields.sampler_spec
        if spec0 == "perturb-ensemble":
            from sverdrup.core.provenance import degradation_transform

            transforms.append(degradation_transform())
        prov = UncertaintyProvenance(
            native_capability=base.native_capability,
            transformations=transforms,
        )
        shape = support.shape if isinstance(support, GridSpec) else (pts.shape[0],)
        noise = NoiseSpec(
            method=method, params_key=params_key, lattice_step=lattice_step
        )
        return BlendedDistribution(
            support=support,
            mean=mean.reshape(shape),
            _variance=(sigma**2).reshape(shape),
            provenance=prov,
            fidelity=CovFidelity.BLENDED,
            time_days=t,
            _parts=parts,
            _noise=noise,
            _sampler=CoherentSampler(),
        )
