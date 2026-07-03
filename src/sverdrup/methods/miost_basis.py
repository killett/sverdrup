"""MIOST wavelet dictionary: BasisSpec, enumeration, evaluation, operators (spec §2)."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import sparse  # type: ignore[import-untyped]

from sverdrup.methods.miost_sizing import D_X_KM, D_Y_KM, KM_PER_DEG, scale_set

LADDER: tuple[float, ...] = tuple(scale_set(80.0, lam_max=905.0))  # D1: 8 rungs
N_DIR = 8  # D1: mod-180 degrees
LAM_REF = 300.0  # D8 anchor (gauge-inert)
R_REF = 0.03**2  # D8 anchor (gauge-inert)
W_DAYS, V_DAYS, STRIDE_DAYS = 60.0, 15.0, 45.0  # D3 run-constants
LT_MAX, BETA = 12.0, 0.5  # D3: placement designed at ceiling; dt = BETA*l_t
HALO_DEG = 1.0  # D7
BOX_LON = (295.0, 305.0)
BOX_LAT = (33.0, 43.0)
MID_LAT = 38.0
SUPPORT = 1.5  # L = 1.5*lam


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

    def elements_for_window(self, start_day: float) -> Elements:
        """Enumerate elements whose GLOBAL temporal slot falls in [start, start+W].

        Args:
            start_day: Window start [days since epoch 2017-01-01].

        Returns:
            The window's elements with window-independent identity tuples.
        """
        ids, xs, ys, ts, kxs, kys, phs, hws = [], [], [], [], [], [], [], []
        dt = self.dt_days
        j_lo = math.ceil(start_day / dt)
        j_hi = math.floor((start_day + W_DAYS) / dt)
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


def build_g(
    spec: BasisSpec,
    els: Elements,
    lon: np.ndarray,
    lat: np.ndarray,
    t_days: np.ndarray,
) -> sparse.csr_matrix:
    """Assemble CSR G analytically: rows=obs, cols=elements. Never via a gridded H.

    Args:
        spec: Basis specification.
        els: Enumerated window elements.
        lon: Observation longitudes [deg east].
        lat: Observation latitudes [deg north].
        t_days: Observation times [days since epoch].

    Returns:
        CSR matrix (n_obs, n_elements).
    """
    x, y = lonlat_to_km(np.asarray(lon, float), np.asarray(lat, float))
    t = np.asarray(t_days, float)
    rows, cols, vals = [], [], []
    # NOTE: O(n_elements * n_obs) masking — bucket per scale (cells of size
    # alpha*lam) if the alpha=1.0 60-d window assembly exceeds ~60 s.
    for p in range(els.x_km.size):
        hw = els.half_width_km[p]
        m = (
            (np.abs(x - els.x_km[p]) < hw)
            & (np.abs(y - els.y_km[p]) < hw)
            & (np.abs(t - els.t_days[p]) < spec.l_t_days)
        )
        idx = np.nonzero(m)[0]
        if idx.size == 0:
            continue
        dx = (x[idx] - els.x_km[p]) / hw
        dy = (y[idx] - els.y_km[p]) / hw
        dtt = (t[idx] - els.t_days[p]) / spec.l_t_days
        v = (
            np.cos(
                els.kx[p] * (x[idx] - els.x_km[p])
                + els.ky[p] * (y[idx] - els.y_km[p])
                + els.phase[p]
            )
            * np.cos(0.5 * np.pi * dx)
            * np.cos(0.5 * np.pi * dy)
            * np.cos(0.5 * np.pi * dtt)
        )
        rows.append(idx)
        cols.append(np.full(idx.size, p))
        vals.append(v)
    if not rows:
        return sparse.csr_matrix((x.size, els.x_km.size))
    return sparse.csr_matrix(
        (np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
        shape=(x.size, els.x_km.size),
    )


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
    x, y = lonlat_to_km(grid_lon, grid_lat)
    rows, cols, vals = [], [], []
    for p in range(els.x_km.size):
        hw = els.half_width_km[p]
        m = (np.abs(x - els.x_km[p]) < hw) & (np.abs(y - els.y_km[p]) < hw)
        idx = np.nonzero(m)[0]
        if idx.size == 0:
            continue
        v = (
            np.cos(
                els.kx[p] * (x[idx] - els.x_km[p])
                + els.ky[p] * (y[idx] - els.y_km[p])
                + els.phase[p]
            )
            * np.cos(0.5 * np.pi * (x[idx] - els.x_km[p]) / hw)
            * np.cos(0.5 * np.pi * (y[idx] - els.y_km[p]) / hw)
        )
        rows.append(idx)
        cols.append(np.full(idx.size, p))
        vals.append(v)
    if not rows:
        return sparse.csr_matrix((x.size, els.x_km.size))
    return sparse.csr_matrix(
        (np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
        shape=(x.size, els.x_km.size),
    )


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
