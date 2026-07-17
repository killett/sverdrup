"""MIOST wavelet dictionary: BasisSpec, enumeration, evaluation, operators (spec §2)."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import sparse  # type: ignore[import-untyped]

from sverdrup.methods.miost_sizing import (
    BOX_LAT as BOX_LAT,  # noqa: PLC0414  (explicit re-export for scripts/)
)
from sverdrup.methods.miost_sizing import (
    BOX_LON as BOX_LON,  # noqa: PLC0414  (explicit re-export for scripts/)
)
from sverdrup.methods.miost_sizing import (
    D_X_KM,
    D_Y_KM,
    KM_PER_DEG,
    MID_LAT,
    scale_set,
)
from sverdrup.methods.miost_sizing import (
    SUPPORT_FACTOR as SUPPORT,  # L = 1.5*lam
)

LADDER: tuple[float, ...] = tuple(scale_set(80.0, lam_max=905.0))  # D1: 8 rungs
N_DIR = 8  # D1: mod-180 degrees
LAM_REF = 300.0  # D8 anchor (gauge-inert)
R_REF = 0.03**2  # D8 anchor (gauge-inert)
W_DAYS, V_DAYS, STRIDE_DAYS = 60.0, 15.0, 45.0  # D3 run-constants
LT_MAX, BETA = 12.0, 0.5  # D3: placement designed at ceiling; dt = BETA*l_t
HALO_DEG = 1.0  # D7


@dataclass(frozen=True)
class Elements:
    """One window's enumerated elements (columns of Gamma restricted to the window)."""

    identity: (
        np.ndarray
    )  # (n, 6) int64: scale_idx, dir_idx, phase_idx, ix, iy, global_slot
    x_km: np.ndarray  # element centers, km from box lon-min at MID_LAT
    y_km: np.ndarray
    t_days: np.ndarray
    kx: np.ndarray  # carrier wavevector components (rad/km)
    ky: np.ndarray
    phase: np.ndarray  # 0 or pi/2
    half_width_km: np.ndarray  # 1.5*lam per element


@dataclass(frozen=True)
class BasisSpec:
    """Run-constants + continuous basis params; the single source of enumeration."""

    alpha: float
    l_t_days: float
    n_dir: int = N_DIR
    ladder: tuple[float, ...] = LADDER

    @property
    def dt_days(self) -> float:
        """Temporal pavement spacing (D3: tied dt = BETA * l_t)."""
        return BETA * self.l_t_days

    def key(self) -> str:
        """Canonical basis contribution to params_key (everything eta depends on)."""
        return (
            f"miost-basis;alpha={self.alpha!r};l_t={self.l_t_days!r};n_dir={self.n_dir};"
            f"ladder={','.join(f'{s:.3f}' for s in self.ladder)};beta={BETA};"
            f"W={W_DAYS};V={V_DAYS};stride={STRIDE_DAYS};halo={HALO_DEG};"
            f"lam_ref={LAM_REF};r_ref={R_REF!r}"
        )

    def elements_for_window(self, start_day: float, w_days: float = W_DAYS) -> Elements:
        """Enumerate elements whose GLOBAL temporal slot falls in [start, start + w_days].

        Args:
            start_day: Window start [days since epoch 2017-01-01].
            w_days: Window length (non-default ONLY for the Task-11 single-window
                equivalence harness).

        Returns:
            The window's elements with window-independent identity tuples.
        """
        ids, xs, ys, ts, kxs, kys, phs, hws = [], [], [], [], [], [], [], []
        dt = self.dt_days
        j_lo = math.ceil(start_day / dt)
        j_hi = math.floor((start_day + w_days) / dt)
        for s_idx, lam in enumerate(self.ladder):
            hw = SUPPORT * lam
            step = self.alpha * lam
            # spatial pavement: box + 1.5*lam margin each side (spec §2.1)
            nx = int(np.ceil((D_X_KM + 2 * hw) / step))
            ny = int(np.ceil((D_Y_KM + 2 * hw) / step))
            x0, y0 = -hw, -hw
            k = 2 * np.pi / lam
            for d_idx in range(self.n_dir):
                th = np.pi * d_idx / self.n_dir  # mod-180 (D1)
                for p_idx, ph in enumerate((0.0, np.pi / 2)):
                    for ix in range(nx):
                        for iy in range(ny):
                            for j in range(j_lo, j_hi + 1):
                                ids.append((s_idx, d_idx, p_idx, ix, iy, j))
                                xs.append(x0 + ix * step)
                                ys.append(y0 + iy * step)
                                ts.append(j * dt)
                                kxs.append(k * np.cos(th))
                                kys.append(k * np.sin(th))
                                phs.append(ph)
                                hws.append(hw)
        return Elements(
            np.asarray(ids, dtype=np.int64),
            np.asarray(xs),
            np.asarray(ys),
            np.asarray(ts),
            np.asarray(kxs),
            np.asarray(kys),
            np.asarray(phs),
            np.asarray(hws),
        )

    def evaluate(
        self, els: Elements, x_km: np.ndarray, y_km: np.ndarray, t_days: np.ndarray
    ) -> np.ndarray:
        """Dense (n_pts, n_elements) evaluation — small inputs only (tests, representers).

        Args:
            els: Enumerated window elements.
            x_km: Query x coordinates [km].
            y_km: Query y coordinates [km].
            t_days: Query times [days since epoch].

        Returns:
            Dense evaluation matrix, one row per query point.
        """
        dx = x_km[:, None] - els.x_km[None, :]
        dy = y_km[:, None] - els.y_km[None, :]
        dt = t_days[:, None] - els.t_days[None, :]
        hx = els.half_width_km[None, :]
        carrier = np.cos(
            els.kx[None, :] * dx + els.ky[None, :] * dy + els.phase[None, :]
        )
        tap = _cos_tap(dx / hx) * _cos_tap(dy / hx) * _cos_tap(dt / self.l_t_days)
        return np.asarray(carrier * tap)


def _cos_tap(d: np.ndarray) -> np.ndarray:
    """cos(pi*d/2) inside |d|<1, exact 0 outside (U2021 Eq. 19)."""
    return np.where(np.abs(d) < 1.0, np.cos(0.5 * np.pi * d), 0.0)


def lonlat_to_km(lon: np.ndarray, lat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Project degrees to the local km frame used for element geometry.

    Args:
        lon: Longitudes [deg east].
        lat: Latitudes [deg north].

    Returns:
        (x_km, y_km) from the box origin at MID_LAT scaling.
    """
    x = (np.asarray(lon) - BOX_LON[0]) * KM_PER_DEG * math.cos(math.radians(MID_LAT))
    y = (np.asarray(lat) - BOX_LAT[0]) * KM_PER_DEG
    return x, y


_G_CHUNK_OBS = 5_000  # obs rows per assembly chunk (bounds triplet temporaries)


@dataclass(frozen=True)
class _ScaleLayout:
    """One scale's pavement geometry, mirroring ``elements_for_window`` exactly."""

    lam: float
    hw: float
    step: float
    nx: int
    ny: int
    j_lo: int
    j_hi: int
    base: int  # first column index of this scale's block

    @property
    def n_t(self) -> int:
        return self.j_hi - self.j_lo + 1


def _layouts(spec: BasisSpec, j_lo: int, j_hi: int) -> list[_ScaleLayout]:
    """Per-scale pavement layouts mirroring the enumeration order.

    Column index of (s, d, p, ix, iy, j) is
    ``base_s + (((d*2 + p)*nx + ix)*ny + iy)*n_t + (j - j_lo)`` — the analytic
    inverse of the enumeration order.
    """
    out: list[_ScaleLayout] = []
    base = 0
    for lam in spec.ladder:
        hw = SUPPORT * lam
        step = spec.alpha * lam
        nx = int(np.ceil((D_X_KM + 2 * hw) / step))
        ny = int(np.ceil((D_Y_KM + 2 * hw) / step))
        out.append(_ScaleLayout(lam, hw, step, nx, ny, j_lo, j_hi, base))
        base += nx * ny * (j_hi - j_lo + 1) * spec.n_dir * 2
    return out


def _axis_candidates(
    pos: np.ndarray, origin: float, step: float, hw: float, n: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per-point candidate pavement indices along one axis (vectorized bucketing).

    Returns ``(idx, delta, ok)`` of shape ``(n_pts, k)``: pavement indices,
    signed offsets ``pos - center``, and the in-support validity mask.
    """
    k = int(np.floor(2.0 * hw / step)) + 1
    lo = np.floor((pos - origin - hw) / step).astype(np.int64) + 1
    idx = lo[:, None] + np.arange(k)[None, :]
    delta = pos[:, None] - (origin + idx * step)
    ok = (idx >= 0) & (idx < n) & (np.abs(delta) < hw)
    return idx, delta, ok


def _chunk_triplets(
    spec: BasisSpec,
    layouts: list[_ScaleLayout],
    x: np.ndarray,
    y: np.ndarray,
    t: np.ndarray,
    values: bool,
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    """(rows, cols, vals|None) for one obs chunk over all scales/dirs/phases.

    ``values=False`` is the cheap counting pass: same candidate logic, no
    trig evaluation, vals returned as None.
    """
    dt = spec.dt_days
    rows_l: list[np.ndarray] = []
    cols_l: list[np.ndarray] = []
    vals_l: list[np.ndarray] = []
    for lay in layouts:
        ix, dx, okx = _axis_candidates(x, -lay.hw, lay.step, lay.hw, lay.nx)
        iy, dy, oky = _axis_candidates(y, -lay.hw, lay.step, lay.hw, lay.ny)
        kt = int(np.floor(2.0 * spec.l_t_days / dt)) + 1
        jt_lo = np.floor((t - spec.l_t_days) / dt).astype(np.int64) + 1
        jt = jt_lo[:, None] + np.arange(kt)[None, :]
        dtt = t[:, None] - jt * dt
        okt = (jt >= lay.j_lo) & (jt <= lay.j_hi) & (np.abs(dtt) < spec.l_t_days)
        valid = okx[:, :, None, None] & oky[:, None, :, None] & okt[:, None, None, :]
        if not valid.any():
            continue
        o_idx, a_ix, a_iy, a_jt = np.nonzero(valid)
        col_spatial = (ix[o_idx, a_ix] * lay.ny + iy[o_idx, a_iy]) * lay.n_t + (
            jt[o_idx, a_jt] - lay.j_lo
        )
        block = lay.nx * lay.ny * lay.n_t
        if values:
            dxv, dyv, dttv = dx[o_idx, a_ix], dy[o_idx, a_iy], dtt[o_idx, a_jt]
            taper = (
                np.cos(0.5 * np.pi * dxv / lay.hw)
                * np.cos(0.5 * np.pi * dyv / lay.hw)
                * np.cos(0.5 * np.pi * dttv / spec.l_t_days)
            )
            k_carrier = 2.0 * np.pi / lay.lam
        for d_idx in range(spec.n_dir):
            th = np.pi * d_idx / spec.n_dir
            if values:
                phase_arg = k_carrier * (np.cos(th) * dxv + np.sin(th) * dyv)
            for p_idx, ph in enumerate((0.0, np.pi / 2)):
                rows_l.append(o_idx)
                cols_l.append(lay.base + (d_idx * 2 + p_idx) * block + col_spatial)
                if values:
                    vals_l.append(np.cos(phase_arg + ph) * taper)
    if not rows_l:
        z = np.empty(0, dtype=np.int64)
        return z, z, (np.empty(0) if values else None)
    return (
        np.concatenate(rows_l),
        np.concatenate(cols_l),
        np.concatenate(vals_l) if values else None,
    )


def build_g(
    spec: BasisSpec,
    els: Elements,
    lon: np.ndarray,
    lat: np.ndarray,
    t_days: np.ndarray,
) -> sparse.csr_matrix:
    """Assemble CSR G analytically: rows=obs, cols=elements. Never via a gridded H.

    Vectorized per-scale bucketing — each obs sees only the O((3/alpha)^2 * 5)
    pavement candidates whose support can contain it, found by integer
    arithmetic (never an O(n_elements x n_obs) mask sweep). Row-chunked
    two-pass fill into preallocated CSR arrays: pass 1 counts (no trig),
    pass 2 evaluates and writes — peak memory stays at the final matrix plus
    one small chunk, never a whole-matrix triplet spike. Values are identical
    to the dense ``spec.evaluate`` at the obs points.

    Args:
        spec: Basis specification (must be the one that enumerated ``els``).
        els: Enumerated window elements (defines shape + slot placement).
        lon: Observation longitudes [deg east].
        lat: Observation latitudes [deg north].
        t_days: Observation times [days since epoch].

    Returns:
        CSR matrix (n_obs, n_elements).
    """
    x, y = lonlat_to_km(np.asarray(lon, float), np.asarray(lat, float))
    t = np.asarray(t_days, float)
    n_obs, n_el = x.size, els.x_km.size
    if n_obs == 0 or n_el == 0:
        return sparse.csr_matrix((n_obs, n_el))
    j_lo = int(els.identity[:, 5].min())
    j_hi = int(els.identity[:, 5].max())
    layouts = _layouts(spec, j_lo, j_hi)
    last = layouts[-1]
    if last.base + last.nx * last.ny * last.n_t * spec.n_dir * 2 != n_el:
        raise ValueError("els does not match this spec's enumeration layout")

    chunks = [
        slice(c, min(c + _G_CHUNK_OBS, n_obs)) for c in range(0, n_obs, _G_CHUNK_OBS)
    ]
    # pass 1: count nnz per chunk (candidate logic only, no trig)
    counts = []
    for sl in chunks:
        r, _, _ = _chunk_triplets(spec, layouts, x[sl], y[sl], t[sl], values=False)
        counts.append(r.size)
    nnz = int(np.sum(counts))
    data = np.empty(nnz)
    indices = np.empty(nnz, dtype=np.int32)
    indptr = np.zeros(n_obs + 1, dtype=np.int64)
    # pass 2: evaluate chunk triplets, sort into CSR rows, write into place
    off = 0
    for sl, cnt in zip(chunks, counts, strict=True):
        if cnt == 0:
            indptr[sl.start + 1 : sl.stop + 1] = off
            continue
        r, c, v = _chunk_triplets(spec, layouts, x[sl], y[sl], t[sl], values=True)
        g_chunk = sparse.csr_matrix((v, (r, c)), shape=(sl.stop - sl.start, n_el))
        g_chunk.sort_indices()
        data[off : off + cnt] = g_chunk.data
        indices[off : off + cnt] = g_chunk.indices
        indptr[sl.start + 1 : sl.stop + 1] = off + g_chunk.indptr[1:]
        off += cnt
    return sparse.csr_matrix((data, indices, indptr), shape=(n_obs, n_el))


def build_s(
    spec: BasisSpec,
    els: Elements,
    grid_lon: np.ndarray,
    grid_lat: np.ndarray,
) -> sparse.csr_matrix:
    """SPATIAL basis matrix at grid nodes (fork-1 hardening 2): carrier * spatial taper only.

    Args:
        spec: Basis specification.
        els: Enumerated window elements.
        grid_lon: Grid-node longitudes [deg east].
        grid_lat: Grid-node latitudes [deg north].

    Returns:
        CSR matrix (n_nodes, n_elements) with NO temporal factor.
    """
    x, y = lonlat_to_km(np.asarray(grid_lon, float), np.asarray(grid_lat, float))
    n_nodes, n_el = x.size, els.x_km.size
    if n_nodes == 0 or n_el == 0:
        return sparse.csr_matrix((n_nodes, n_el))
    j_lo = int(els.identity[:, 5].min())
    j_hi = int(els.identity[:, 5].max())
    layouts = _layouts(spec, j_lo, j_hi)
    rows_l, cols_l, vals_l = [], [], []
    # Spatial values are j-independent: evaluate once per spatial candidate,
    # then tile across that position's n_t temporal-slot columns.
    for lay in layouts:
        ix, dx, okx = _axis_candidates(x, -lay.hw, lay.step, lay.hw, lay.nx)
        iy, dy, oky = _axis_candidates(y, -lay.hw, lay.step, lay.hw, lay.ny)
        valid = okx[:, :, None] & oky[:, None, :]
        if not valid.any():
            continue
        o_idx, a_ix, a_iy = np.nonzero(valid)
        dxv, dyv = dx[o_idx, a_ix], dy[o_idx, a_iy]
        taper = np.cos(0.5 * np.pi * dxv / lay.hw) * np.cos(0.5 * np.pi * dyv / lay.hw)
        col_sp = (ix[o_idx, a_ix] * lay.ny + iy[o_idx, a_iy]) * lay.n_t
        block = lay.nx * lay.ny * lay.n_t
        k_carrier = 2.0 * np.pi / lay.lam
        slots = np.arange(lay.n_t)
        for d_idx in range(spec.n_dir):
            th = np.pi * d_idx / spec.n_dir
            phase_arg = k_carrier * (np.cos(th) * dxv + np.sin(th) * dyv)
            for p_idx, ph in enumerate((0.0, np.pi / 2)):
                v = np.cos(phase_arg + ph) * taper
                base = lay.base + (d_idx * 2 + p_idx) * block
                cols_l.append((base + col_sp[:, None] + slots[None, :]).ravel())
                rows_l.append(np.repeat(o_idx, lay.n_t))
                vals_l.append(np.repeat(v, lay.n_t))
    if not rows_l:
        return sparse.csr_matrix((n_nodes, n_el))
    g = sparse.csr_matrix(
        (np.concatenate(vals_l), (np.concatenate(rows_l), np.concatenate(cols_l))),
        shape=(n_nodes, n_el),
    )
    g.sort_indices()
    return g


def build_s_spatial(
    spec: BasisSpec,
    els: Elements,
    grid_lon: np.ndarray,
    grid_lat: np.ndarray,
) -> sparse.csr_matrix:
    """Spatial-only S: one column per (scale, dir, phase, ix, iy) — NO t-slot axis.

    The day map is ``build_s_spatial(...) @ time_contract(spec, els, eta, day)``:
    tiling the identical spatial values across every t-slot (the naive S) is
    n_t times larger and OOMs on the 425-day single window.

    Args:
        spec: Basis specification (must be the one that enumerated ``els``).
        els: Enumerated window elements.
        grid_lon: Grid-node longitudes [deg east].
        grid_lat: Grid-node latitudes [deg north].

    Returns:
        CSR matrix (n_nodes, n_spatial_columns); spatial columns follow the
        enumeration order with the t axis removed.
    """
    x, y = lonlat_to_km(np.asarray(grid_lon, float), np.asarray(grid_lat, float))
    n_nodes = x.size
    j_lo = int(els.identity[:, 5].min())
    j_hi = int(els.identity[:, 5].max())
    layouts = _layouts(spec, j_lo, j_hi)
    n_sp_total = sum(lay.nx * lay.ny * spec.n_dir * 2 for lay in layouts)
    if n_nodes == 0 or n_sp_total == 0:
        return sparse.csr_matrix((n_nodes, n_sp_total))
    rows_l, cols_l, vals_l = [], [], []
    base_sp = 0
    for lay in layouts:
        ix, dx, okx = _axis_candidates(x, -lay.hw, lay.step, lay.hw, lay.nx)
        iy, dy, oky = _axis_candidates(y, -lay.hw, lay.step, lay.hw, lay.ny)
        valid = okx[:, :, None] & oky[:, None, :]
        block = lay.nx * lay.ny
        if valid.any():
            o_idx, a_ix, a_iy = np.nonzero(valid)
            dxv, dyv = dx[o_idx, a_ix], dy[o_idx, a_iy]
            taper = np.cos(0.5 * np.pi * dxv / lay.hw) * np.cos(
                0.5 * np.pi * dyv / lay.hw
            )
            col_sp = ix[o_idx, a_ix] * lay.ny + iy[o_idx, a_iy]
            k_carrier = 2.0 * np.pi / lay.lam
            for d_idx in range(spec.n_dir):
                th = np.pi * d_idx / spec.n_dir
                phase_arg = k_carrier * (np.cos(th) * dxv + np.sin(th) * dyv)
                for p_idx, ph in enumerate((0.0, np.pi / 2)):
                    rows_l.append(o_idx)
                    cols_l.append(base_sp + (d_idx * 2 + p_idx) * block + col_sp)
                    vals_l.append(np.cos(phase_arg + ph) * taper)
        base_sp += block * spec.n_dir * 2
    s = sparse.csr_matrix(
        (np.concatenate(vals_l), (np.concatenate(rows_l), np.concatenate(cols_l))),
        shape=(n_nodes, n_sp_total),
    )
    s.sort_indices()
    return s


def time_contract(
    spec: BasisSpec, els: Elements, eta: np.ndarray, day: float
) -> np.ndarray:
    """Contract eta over t-slots with the day's temporal taper, per spatial column.

    Within each (scale, dir, phase, ix, iy) block the full columns are contiguous
    in j, so the contraction is a per-scale reshape-dot.

    Args:
        spec: Basis specification.
        els: Enumerated window elements (defines slot placement).
        eta: Full coefficient vector (n_elements,) or batch (n_elements, m).
        day: Output day [days since epoch].

    Returns:
        Spatial-column vector matching ``build_s_spatial``'s columns (same batch
        shape as ``eta`` beyond the first axis).
    """
    j_lo = int(els.identity[:, 5].min())
    j_hi = int(els.identity[:, 5].max())
    layouts = _layouts(spec, j_lo, j_hi)
    dt = spec.dt_days
    tau = np.asarray(_cos_tap((day - np.arange(j_lo, j_hi + 1) * dt) / spec.l_t_days))
    parts = []
    for lay in layouts:
        n_full = lay.nx * lay.ny * lay.n_t * spec.n_dir * 2
        block = eta[lay.base : lay.base + n_full]
        # rows = (dir, phase, ix, iy) in order; last axis = t-slot
        parts.append(block.reshape(-1, lay.n_t, *eta.shape[1:]).swapaxes(1, -1) @ tau)
    return np.concatenate(parts)


def temporal_taper(spec: BasisSpec, els: Elements, day: float) -> np.ndarray:
    """Per-element temporal taper at ``day`` (day map = S @ (eta * taper)).

    Args:
        spec: Basis specification.
        els: Enumerated window elements.
        day: Output day [days since epoch].

    Returns:
        Taper values, one per element.
    """
    return np.asarray(_cos_tap((day - els.t_days) / spec.l_t_days))


@dataclass(frozen=True)
class DiagonalQ:
    """Prior variances q_p = rho * R_REF * (lam_p/lam_ref)^q_slope (spec §2.2, gap-#3 flag)."""

    rho: float
    q_slope: float
    lam_ref: float = LAM_REF
    r_ref: float = R_REF

    def variances_for(self, els: Elements) -> np.ndarray:
        """Per-element prior variances.

        Args:
            els: Enumerated window elements.

        Returns:
            Variances aligned with the element order.
        """
        # The element's ACTUAL wavelength (hw = 1.5*lam), valid for any ladder.
        lam = np.asarray(els.half_width_km) / SUPPORT
        return np.asarray(self.rho * self.r_ref * (lam / self.lam_ref) ** self.q_slope)

    def variances(self, spec: BasisSpec) -> np.ndarray:
        """Per-RUNG variances (gauge test helper).

        Args:
            spec: Basis specification providing the ladder.

        Returns:
            One variance per ladder rung.
        """
        lam = np.asarray(spec.ladder)
        return np.asarray(self.rho * self.r_ref * (lam / self.lam_ref) ** self.q_slope)


@dataclass(frozen=True)
class DiagonalR:
    """Scalar observation-error variance (Stage A: R = R_REF, s == 1)."""

    variance: float = R_REF
