"""Cross-tile coherent sampler via white-noise conditioning (design section 5)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol, cast, runtime_checkable

import numpy as np

from sverdrup.core.geometry import Window
from sverdrup.core.grid import GridSpec, PointSet
from sverdrup.core.seeding import derive_seed
from sverdrup.core.types import Field, Points


def _support_points(support: GridSpec | PointSet, time_days: float) -> Points:
    """Return ``(n, 3)`` points for either support kind."""
    if isinstance(support, PointSet):
        return support.points()
    return support.points(time_days)


def _nearest(grid: GridSpec | PointSet, pts: Points, t: float) -> np.ndarray:
    """Return the nearest support-node index for each point in ``pts`` at time ``t``."""
    nodes = grid.points() if isinstance(grid, PointSet) else grid.points(t)
    return np.asarray(
        np.argmin(np.linalg.norm(pts[:, None, :2] - nodes[None, :, :2], axis=2), axis=1)
    )


@dataclass(frozen=True)
class NoiseSpec:
    """The tile-independent global driving-noise spec (lattice + method identity).

    Attributes:
        method: Method name, used in the seed derivation.
        params_key: Canonical resolved-parameter string, used in the seed derivation.
        lattice_step: Degrees per global cell along lon & lat (tile-independent grid).
    """

    method: str
    params_key: str
    lattice_step: float


def _cell_ids(points: Points, step: float) -> np.ndarray:
    """Map points to deterministic global lattice cell ids (tile-independent)."""
    cx = np.floor(points[:, 0] / step).astype(np.int64)
    cy = np.floor(points[:, 1] / step).astype(np.int64)
    ct = np.floor(points[:, 2]).astype(np.int64)
    # a stable, collision-resistant-enough composite id for seeding
    return np.asarray((cx * 73856093) ^ (cy * 19349663) ^ (ct * 83492791))


def diagonal_noise(
    points: Points, member_index: int, noise_spec: NoiseSpec
) -> np.ndarray:
    """Return one N(0,1) draw per point, keyed by global cell id x member (coherent).

    Args:
        points: ``(n, 3)`` space-time points ``(lon, lat, time)``.
        member_index: The ensemble member index.
        noise_spec: The tile-independent global driving-noise spec.

    Returns:
        A length-``n`` array of standard-normal draws; the same global cell and member
        always yield the same value regardless of which tile requested it.
    """
    ids = _cell_ids(points, noise_spec.lattice_step)
    out = np.empty(points.shape[0], float)
    for i, cid in enumerate(ids):
        seed = derive_seed(
            noise_spec.method, noise_spec.params_key, f"cell:{cid}", member_index
        )
        out[i] = np.random.default_rng(seed).standard_normal()
    return out


@runtime_checkable
class StructuredNoiseSource(Protocol):
    """Drives the structured (low-rank) part; swap point for Option-1/Option-2."""

    def draw(
        self,
        member_index: int,
        parts: Sequence[Any],
        support: object,
        noise_spec: NoiseSpec,
    ) -> list[np.ndarray]:
        """Return one ``z_r`` latent vector per tile."""
        ...


@dataclass
class MemberSeededZr:
    """Option 1 (default): z_r seeded by member only — tile-independent latent."""

    def draw_one(
        self, member_index: int, rank: int, noise_spec: NoiseSpec
    ) -> np.ndarray:
        """Return the member's latent ``z_r`` prefix of length ``rank``.

        Args:
            member_index: The ensemble member index (seed depends on this only).
            rank: The length of the latent vector to draw.
            noise_spec: The global driving-noise spec (method/params identity).

        Returns:
            A length-``rank`` standard-normal latent vector, tile-independent.
        """
        seed = derive_seed(
            noise_spec.method, noise_spec.params_key, "structured", member_index
        )
        return np.asarray(np.random.default_rng(seed).standard_normal(rank))

    def draw(
        self,
        member_index: int,
        parts: Sequence[Any],
        support: object,
        noise_spec: NoiseSpec,
    ) -> list[np.ndarray]:
        """Return one member-seeded ``z_r`` per tile (each truncated to its rank)."""
        return [
            self.draw_one(member_index, p.distribution.fields.rank, noise_spec)
            for p in parts
        ]


def coherent_structured_field(
    factors: list[np.ndarray],
    weights: np.ndarray,
    member_index: int,
    noise_spec: NoiseSpec,
) -> np.ndarray:
    """Return a cross-tile-coherent structured field over the support (shared-basis driver).

    The shared-overlap-basis structured driver (design §5c, Option-2 realized). Each tile's
    factor is projected into one common orthonormal basis ``Q`` (QR of the stacked factors),
    symmetrically square-rooted there (``Aᵢ = (CᵢCᵢᵀ)^½``, ``Cᵢ = QᵀFᵢ``) to remove the
    SVD rotational ambiguity, and the weighted sum ``G = Σ wᵢ Q Aᵢ`` is driven by ONE shared
    member-seeded latent ``g``. Tiles therefore agree at shared points (no basis-orientation
    cancellation, no cross-seam derivative inflation) and the field's structured covariance
    is the weighted blend of the per-tile structured covariances — no per-point renormalization.

    Args:
        factors: Per-tile ``(n, rᵢ)`` factors at the support (rows zeroed where the tile
            does not cover the point).
        weights: ``(T, n)`` partition-of-unity weights.
        member_index: The ensemble member index (seeds the shared latent only).
        noise_spec: The global driving-noise spec (method/params identity for the seed).

    Returns:
        A length-``n`` coherent structured field (zeros if the stacked rank is 0).
    """
    n = weights.shape[1]
    cat = np.hstack(factors) if factors else np.zeros((n, 0))
    if cat.shape[1] == 0:
        return np.zeros(n)
    q, _ = np.linalg.qr(cat)  # (n, p) common orthonormal basis
    p = q.shape[1]
    g_sum = np.zeros((n, p))
    for i, f_i in enumerate(factors):
        if f_i.shape[1] == 0:
            continue
        c_i = q.T @ f_i  # (p, rᵢ)
        k_i = c_i @ c_i.T  # (p, p) structured covariance in Q-space
        evals, evecs = np.linalg.eigh(k_i)
        a_i = (evecs * np.sqrt(np.clip(evals, 0.0, None))) @ evecs.T  # symmetric sqrt
        g_sum += weights[i][:, None] * (q @ a_i)  # (n, p), aligned + weight-crossfaded
    seed = derive_seed(
        noise_spec.method, noise_spec.params_key, "structured-shared", member_index
    )
    g = np.random.default_rng(seed).standard_normal(p)
    return np.asarray(g_sum @ g)


class CoherentSampler:
    """Realizes coherent sample fields from Persisted reps + global driving noise."""

    def __init__(self, structured: StructuredNoiseSource | None = None) -> None:
        """Store the structured-noise source (defaults to member-only z_r).

        Args:
            structured: The structured (low-rank) noise driver; defaults to
                ``MemberSeededZr`` (Option 1).
        """
        self.structured: StructuredNoiseSource = structured or MemberSeededZr()

    def realize_one(
        self,
        *,
        mean: Field,
        factor: np.ndarray,
        residual: np.ndarray,
        points: Points,
        member_index: int,
        noise_spec: NoiseSpec,
    ) -> np.ndarray:
        """Realize one tile's coherent field: mean + B z_r + sqrt(d) z_diag.

        Args:
            mean: The tile mean at ``points`` (length n).
            factor: The low-rank factor ``B`` at ``points``, shape ``(n, r)``.
            residual: The diagonal residual ``d`` at ``points`` (length n, >= 0).
            points: The ``(n, 3)`` space-time points to realize at.
            member_index: The ensemble member index.
            noise_spec: The global driving-noise spec.

        Returns:
            The realized field, length n.
        """
        r = factor.shape[1]
        z_r = MemberSeededZr().draw_one(member_index, r, noise_spec)
        z_d = diagonal_noise(points, member_index, noise_spec)
        return np.asarray(mean + factor @ z_r + np.sqrt(residual) * z_d)


@runtime_checkable
class CoherentMemberDriver(Protocol):
    """Relocated coherence seam: one cross-tile-coherent, weight-crossfaded realization."""

    def crossfaded_member(
        self,
        parts: Sequence[Any],
        pts: Points,
        weights: np.ndarray,
        member_index: int,
        noise: NoiseSpec,
    ) -> np.ndarray:
        """Realize one coherent member over ``pts`` from the constituents + global noise."""
        ...


class LowRankSharedBasis:
    """OI driver: mean crossfade + shared-overlap-basis structured field + coherent diagonal."""

    def crossfaded_member(
        self,
        parts: Sequence[Any],
        pts: Points,
        weights: np.ndarray,
        member_index: int,
        noise: NoiseSpec,
    ) -> np.ndarray:
        """Realize one coherent member: mean blend + shared-basis struct + coherent diagonal."""
        n = pts.shape[0]
        means = np.zeros((len(parts), n))
        sqd = np.zeros((len(parts), n))
        cols: list[np.ndarray] = []
        for i, p in enumerate(parts):
            d = p.distribution
            idx = _nearest(d.grid, pts, d.time_days)
            means[i] = d.fields.mean.ravel()[idx]
            cols.append(d.fields.factor[idx] * (weights[i] > 0)[:, None])
            sqd[i] = np.sqrt(d.fields.residual[idx])
        mean_blend = (weights * means).sum(axis=0)
        diag_amp = (weights * sqd).sum(axis=0)
        struct = coherent_structured_field(cols, weights, member_index, noise)
        diag = diag_amp * diagonal_noise(pts, member_index, noise)
        return np.asarray(mean_blend + struct + diag)


# α=2 (κ²−Δ)² precision couples nodes within grid-distance 2; the handed-forward overlap
# must be at least this thick (in the sweep direction) to Q-separate the interiors.
STENCIL_REACH = 2


def _node_keys(points: Points, decimals: int = 6) -> list[tuple[float, float]]:
    """Round (lon, lat) to stable tuple keys so coincident nodes across tiles match."""
    r = np.round(points[:, :2], decimals)
    return [(float(a), float(b)) for a, b in r]


def _in_window(pt: np.ndarray, win: Window, eps: float = 1e-6) -> bool:
    """Return whether ``pt`` (lon, lat) lies inside a geometry ``Window`` (inclusive)."""
    lo_lon, hi_lon = win.lon_range
    lo_lat, hi_lat = win.lat_range
    return bool(
        lo_lon - eps <= pt[0] <= hi_lon + eps and lo_lat - eps <= pt[1] <= hi_lat + eps
    )


class GmrfKrigingSolve:
    """GMRF driver: conditioning-by-kriging toward ONE global realization (spec §5.3.1).

    Per member, a single forward sweep over the tile chain (ordered by core lon) draws each
    tile's unconditional exact posterior sample ``x_u = mean + L^-T w`` and krige-corrects it
    toward the **values** already fixed on its overlap with the already-processed neighbour:

        x_c = x_u + Σ_{:,S} (Σ_{S,S})^-1 (x_S − x_u|_S)

    with ``Σ_{:,S}`` the full ``Q^-1`` columns for the shared nodes (back-solves on the tile
    factor, exact). The corrected overlap with the NEXT tile is handed forward as fixed values
    (NOT a shared seed — same seed through a different ``L^-T`` decorrelates), so tile k inherits
    tile k-1's values which were conditioned on tile k-2: transitive by construction.

    Validity is exact for a **tree-structured tile chain** (Phase-3 ``n_lon×1``) when each
    handed-forward overlap Q-separates the processed/unprocessed interiors. That precondition
    is ASSERTED (overlap ≥ ``STENCIL_REACH`` columns in the sweep direction), not assumed; a
    2-D / FEM tiling needs the pre-drawn-joint or junction-tree variant (out of Phase-3 scope).
    """

    def _sweep(
        self,
        parts: Sequence[Any],
        time_days: float,
        member_index: int,
        noise: NoiseSpec,
    ) -> list[np.ndarray]:
        """Return each tile's kriging-corrected node-space field (parts order)."""
        order = sorted(
            range(len(parts)),
            key=lambda i: sum(parts[i].tile.core_window.lon_range) / 2.0,
        )
        corrected: list[np.ndarray | None] = [None] * len(parts)
        targets: dict[tuple[float, float], float] = {}
        for pos, i in enumerate(order):
            d = parts[i].distribution
            gpts = _support_points(d.grid, time_days)
            keys = _node_keys(gpts)
            # Independent white per tile (keyed by sweep position x member): the kriging
            # theorem needs each tile's unconditional draw INDEPENDENT of the handed-forward
            # targets. The old shared-lattice diagonal_noise correlated the draws across
            # overlapping tiles, biasing the correction (spec §5.3.1: white choice is free,
            # conditioning enforces coherence).
            seed = derive_seed(
                noise.method, noise.params_key, f"gmrf-tile:{pos}", member_index
            )
            white = np.random.default_rng(seed).standard_normal(len(gpts))
            x_u = d.fields.mean.ravel() + d._factor_obj().sample(white)
            s_idx = np.array([n for n, k in enumerate(keys) if k in targets], dtype=int)
            if s_idx.size:
                x_s = np.array([targets[keys[n]] for n in s_idx])
                cols = d.posterior_cov_columns(s_idx)  # (n_i, |S|)
                sigma_ss = cols[s_idx, :]  # (|S|, |S|)
                x_c = x_u + cols @ np.linalg.solve(sigma_ss, x_s - x_u[s_idx])
            else:
                x_c = x_u
            corrected[i] = x_c
            targets = {}
            if pos + 1 < len(order):
                nxt_win = parts[order[pos + 1]].tile.extended_window
                ov = [n for n, p in enumerate(gpts) if _in_window(p, nxt_win)]
                _assert_separates(gpts, ov)
                for n in ov:
                    targets[keys[n]] = float(x_c[n])
        return [np.asarray(c) for c in corrected]

    def crossfaded_member(
        self,
        parts: Sequence[Any],
        pts: Points,
        weights: np.ndarray,
        member_index: int,
        noise: NoiseSpec,
    ) -> np.ndarray:
        """Realize one coherent member: forward-sweep kriging + weight-crossfade onto ``pts``."""
        t = cast(Any, parts[0].distribution).time_days
        corrected = self._sweep(parts, t, member_index, noise)
        n = pts.shape[0]
        out = np.zeros(n)
        for i, p in enumerate(parts):
            d = p.distribution
            idx = _nearest(d.grid, pts, d.time_days)
            cover = weights[i] > 0
            field_i = np.zeros(n)
            field_i[cover] = corrected[i][idx[cover]]
            out += weights[i] * field_i
        return np.asarray(out)


def _assert_separates(gpts: Points, ov_indices: list[int]) -> None:
    """Raise unless the overlap strip is a Q-separator (≥ ``STENCIL_REACH`` lon columns).

    The forward sweep is exact for the joint law only when the handed-forward overlap cuts the
    Q graph between processed and unprocessed interiors. For the α=2 stencil (reach 2) that
    needs ≥ 2 grid columns in the sweep (lon) direction; the ``k·corr_len`` halo policy
    satisfies it comfortably. A red here means the chain construction / halo is wrong — surface
    it, do not loosen (spec §5.3.1, Task-9 standing rule).
    """
    if not ov_indices:
        raise AssertionError(
            "no overlap between consecutive tiles — cannot separate / hand boundary forward"
        )
    cols = np.unique(np.round(gpts[np.asarray(ov_indices), 0], 6))
    if cols.size < STENCIL_REACH:
        raise AssertionError(
            f"overlap strip {cols.size} column(s) < stencil reach {STENCIL_REACH}: "
            "handed-forward boundary does not Q-separate processed/unprocessed interiors "
            "(joint law would be wrong). Widen the halo (k·corr_len) so overlap ≥ reach."
        )


def _strip_network(
    parts: Sequence[Any],
) -> tuple[list[tuple[float, float]], list[dict[int, int]]]:
    """Return the union strip-node keys and per-tile ``{global_idx -> local node idx}``.

    A strip node of tile ``i`` is a node of tile ``i`` that falls inside ANOTHER tile's
    extended window (an overlap node). The returned ``global_keys`` is the ordered set of
    unique ``(lon,lat)`` keys over all tiles; ``per_tile[i][g]`` is tile ``i``'s local node
    index for global strip node ``g`` (absent if tile ``i`` does not contain it). Corner
    nodes shared by >=3 tiles appear once in ``global_keys`` and in every covering tile's map
    — so the induced connectivity assembled in ``_draw_joint`` spans the junction (C1).

    Raises:
        AssertionError: if a multi-tile ``parts`` produces an empty strip network, or if any
            pair of tiles whose extended windows overlap shares no strip node (C6 —
            silent-empty-conditioning must be a loud red).
    """
    t = cast(Any, parts[0].distribution).time_days
    tile_pts = []
    tile_keys = []
    for p in parts:
        gpts = _support_points(p.distribution.grid, t)
        tile_pts.append(gpts)
        tile_keys.append(_node_keys(gpts))

    # strip nodes: tile-i nodes inside any other tile's extended window
    strip_local: list[set[int]] = [set() for _ in parts]
    for i, _p_i in enumerate(parts):
        for j, p_j in enumerate(parts):
            if i == j:
                continue
            win_j = p_j.tile.extended_window
            for n, pt in enumerate(tile_pts[i]):
                if _in_window(pt, win_j):
                    strip_local[i].add(n)

    global_index: dict[tuple[float, float], int] = {}
    global_keys: list[tuple[float, float]] = []
    per_tile: list[dict[int, int]] = [{} for _ in parts]
    for i in range(len(parts)):
        for n in sorted(strip_local[i]):
            key = tile_keys[i][n]
            g = global_index.get(key)
            if g is None:
                g = len(global_keys)
                global_index[key] = g
                global_keys.append(key)
            per_tile[i][g] = n

    # C6: a multi-tile blend whose tiles never connect would condition on an empty strip.
    if len(parts) > 1 and not global_keys:
        raise AssertionError(
            "tiles share no strip node — conditioning set would be silently empty (C6)"
        )
    # C6: adjacent (extended-window-overlapping) tiles must share at least one strip node
    for i in range(len(parts)):
        for j in range(i + 1, len(parts)):
            wi, wj = parts[i].tile.extended_window, parts[j].tile.extended_window
            overlap = (
                wi.lon_range[0] <= wj.lon_range[1]
                and wj.lon_range[0] <= wi.lon_range[1]
                and wi.lat_range[0] <= wj.lat_range[1]
                and wj.lat_range[0] <= wi.lat_range[1]
            )
            if overlap:
                shared = set(per_tile[i]) & set(per_tile[j])
                if not shared:
                    raise AssertionError(
                        f"tiles {i},{j} overlap but share no strip node — "
                        "conditioning set would be silently empty (C6)"
                    )
    return global_keys, per_tile


class PerturbEnsembleDegradation:
    """Degradation driver: per-tile INDEPENDENT members, weight-crossfaded (coherence lost).

    Each tile is forced by a tile-distinct seed (sweep position x member), so members do NOT
    agree across the seam — cross-tile coherence is deliberately not guaranteed. The blend
    records ``DEGRADED_COHERENCE`` (the seam is flagged, not silent) and the crossfaded MEAN
    stays continuous via the partition-of-unity weights. This is the OPPOSITE contract from
    ``GmrfKrigingSolve``: it must not be held to the coherence bar.
    """

    def crossfaded_member(
        self,
        parts: Sequence[Any],
        pts: Points,
        weights: np.ndarray,
        member_index: int,
        noise: NoiseSpec,
    ) -> np.ndarray:
        """Realize one member from per-tile INDEPENDENT draws, weight-crossfaded onto ``pts``."""
        n = pts.shape[0]
        out = np.zeros(n)
        for i, p in enumerate(parts):
            d = p.distribution
            idx = _nearest(d.grid, pts, d.time_days)
            cover = weights[i] > 0
            mean_i = d.fields.mean.ravel()[idx]
            sig_i = np.sqrt(d.fields.marginal_variance.ravel()[idx])
            # tile-distinct seed -> independent member (coherence deliberately not shared)
            seed = derive_seed(
                noise.method, noise.params_key, f"degrade:tile{i}", member_index
            )
            z = np.random.default_rng(seed).standard_normal(n)
            field_i = np.where(cover, mean_i + sig_i * z, 0.0)
            out += weights[i] * field_i
        return np.asarray(out)


_DRIVERS: dict[str, type] = {
    "lowrank+diag": LowRankSharedBasis,
    "sparse-precision": GmrfKrigingSolve,
    "perturb-ensemble": PerturbEnsembleDegradation,
}


def select_driver(sampler_spec: str) -> CoherentMemberDriver:
    """Pick the coherence driver by the persisted representation tag (never by method)."""
    return cast(CoherentMemberDriver, _DRIVERS[sampler_spec]())
