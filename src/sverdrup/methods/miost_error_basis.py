"""Pass table + per-pass {bias, tilt} error-mode B block (phase-13, spec §3).

One responsibility: the B block and its identities. Passes are segmented per
mission on the GEOMETRY ARTIFACT'S time-gap rule (``_GAP_SEC``, imported not
copied — the same constant the Phase-11 v3 artifact pins), the along-track
coordinate ``s`` is arc-length normalized to [-1, 1] within each pass, and
pass identity is TIME-BASED (integer seconds since epoch 2017-01-01 of the
pass's first obs — spec §5 rider 2), never positional: the same pass built
from any window's obs subset carries the same identity and column values.

KNOWN EDGE (recorded at Task-1 review): a pass straddling a window's obs
SUPPORT edge (``start - L_t`` / ``end + L_t``) is clipped, and the clipped
fragment's first obs — hence its time-based identity — differs from the
full pass's. Support edges lie >= L_t away from every blended output day,
so such fragments carry taper-suppressed weight and their mode draws never
co-blend across windows: the shared-obs window-independence guarantee holds
everywhere the blend consumes. No global segmentation pass is warranted.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np
from scipy import sparse  # type: ignore[import-untyped]

# The segmentation gap rule is the geometry artifact's (imported, spec §3).
from sverdrup.application.orbit_geometry import _GAP_SEC

PASS_GAP_SEC: float = _GAP_SEC

_EARTH_RADIUS_KM = 6371.0
_SECONDS_PER_DAY = 86400.0


@dataclass(frozen=True)
class PassTable:
    """Window-independent pass segmentation of one obs subset.

    Attributes:
        pass_mission: (n_pass,) int64 mission hashes (blake2b-4 convention,
            the same integers ``miost._obs_identity`` embeds).
        pass_start_s: (n_pass,) int64 — integer seconds since epoch
            2017-01-01 of each pass's first obs (time-based identity).
        obs_pass_idx: (n_obs,) int32 — pass index (into the arrays above)
            of every input obs.
        s: (n_obs,) float64 in [-1, 1] — arc-length-normalized along-track
            coordinate within the obs's pass; single-obs pass -> 0.0.
    """

    pass_mission: np.ndarray
    pass_start_s: np.ndarray
    obs_pass_idx: np.ndarray
    s: np.ndarray

    @property
    def n_pass(self) -> int:
        """Number of passes."""
        return int(self.pass_mission.size)

    @property
    def n_obs(self) -> int:
        """Number of observations."""
        return int(self.obs_pass_idx.size)


def mission_hash_ints(mission: np.ndarray) -> np.ndarray:
    """Blake2b-4 mission hashes as int64 (the ``_obs_identity`` convention).

    Args:
        mission: Mission id strings.

    Returns:
        (n,) int64 hashes — the SAME integers ``miost._obs_identity`` stores
        (there as floats), so the "err" CRN axis keys on consistent values.
    """
    return np.array(
        [
            int.from_bytes(
                hashlib.blake2b(str(s).encode(), digest_size=4).digest(), "big"
            )
            for s in np.asarray(mission)
        ],
        dtype=np.int64,
    )


def _cumulative_arc_km(lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    """Cumulative great-circle arc length [km] along consecutive points."""
    if lon.size < 2:
        return np.zeros(lon.size)
    lam = np.deg2rad(np.asarray(lon, dtype=float))
    phi = np.deg2rad(np.asarray(lat, dtype=float))
    dlam, dphi = np.diff(lam), np.diff(phi)
    a = (
        np.sin(dphi / 2.0) ** 2
        + np.cos(phi[:-1]) * np.cos(phi[1:]) * np.sin(dlam / 2.0) ** 2
    )
    steps = _EARTH_RADIUS_KM * 2.0 * np.arcsin(np.sqrt(a))
    return np.concatenate([[0.0], np.cumsum(steps)])


def segment_passes(
    lon: np.ndarray,
    lat: np.ndarray,
    t_days: np.ndarray,
    mission_hash: np.ndarray,
    gap_sec: float = PASS_GAP_SEC,
) -> PassTable:
    """Segment obs into passes; window-independent, input-order-independent.

    Per mission, time-sorted obs split where the inter-obs gap exceeds
    ``gap_sec``. Within each pass, ``s = 2*(arc - arc_min)/(arc_max -
    arc_min) - 1`` with arc = cumulative great-circle distance in time
    order; a single-obs (or zero-span) pass gets ``s = 0``. Passes are
    ordered by ``(pass_start_s, pass_mission)`` — a value-derived order,
    stable under any permutation of the input arrays.

    Args:
        lon: (n_obs,) longitudes [deg].
        lat: (n_obs,) latitudes [deg].
        t_days: (n_obs,) times [days since epoch 2017-01-01].
        mission_hash: (n_obs,) int64 mission hashes (:func:`mission_hash_ints`).
        gap_sec: Inter-pass gap threshold in seconds (the artifact's rule).

    Returns:
        The :class:`PassTable` for this obs subset.
    """
    lon = np.asarray(lon, dtype=float)
    lat = np.asarray(lat, dtype=float)
    t = np.asarray(t_days, dtype=float)
    mh = np.asarray(mission_hash, dtype=np.int64)
    n = t.size
    gap_days = gap_sec / _SECONDS_PER_DAY

    pass_rows: list[tuple[int, int, np.ndarray, np.ndarray]] = []
    for m in np.unique(mh):
        idx = np.nonzero(mh == m)[0]
        order = idx[np.argsort(t[idx], kind="stable")]
        seg_id = np.concatenate([[0], np.cumsum(np.diff(t[order]) > gap_days)])
        for seg in np.unique(seg_id):
            rows = order[seg_id == seg]
            arc = _cumulative_arc_km(lon[rows], lat[rows])
            span = arc[-1] - arc[0] if arc.size else 0.0
            s = np.zeros(rows.size) if span == 0.0 else 2.0 * (arc / span) - 1.0
            start_s = int(np.rint(t[rows[0]] * _SECONDS_PER_DAY))
            pass_rows.append((start_s, int(m), rows, s))

    pass_rows.sort(key=lambda r: (r[0], r[1]))
    obs_pass_idx = np.empty(n, dtype=np.int32)
    s_all = np.empty(n, dtype=float)
    for p, (_start, _m, rows, s) in enumerate(pass_rows):
        obs_pass_idx[rows] = p
        s_all[rows] = s
    return PassTable(
        pass_mission=np.asarray([m for _s, m, *_ in pass_rows], dtype=np.int64),
        pass_start_s=np.asarray([st for st, *_ in pass_rows], dtype=np.int64),
        obs_pass_idx=obs_pass_idx,
        s=s_all,
    )


def build_b(pt: PassTable) -> sparse.csr_matrix:
    """The error-mode operator B: (n_obs, 2*n_pass) CSR (spec §3).

    Column ``2p`` is the pass-p BIAS mode (ones on the pass's obs rows);
    column ``2p+1`` is the TILT mode (the obs's ``s`` value). Column values
    for a pass are identical regardless of which window's obs subset built
    the table (s normalizes within the pass, never over the window).

    Args:
        pt: The pass table for this window's obs.

    Returns:
        CSR matrix (n_obs, 2*n_pass) with two entries per obs row.
    """
    rows = np.repeat(np.arange(pt.n_obs, dtype=np.int64), 2)
    p = pt.obs_pass_idx.astype(np.int64)
    cols = np.column_stack([2 * p, 2 * p + 1]).ravel()
    vals = np.column_stack([np.ones(pt.n_obs), pt.s]).ravel()
    return sparse.csr_matrix((vals, (rows, cols)), shape=(pt.n_obs, 2 * pt.n_pass))


def lam_diag(n_pass: int, lam_bias: float, lam_tilt: float) -> np.ndarray:
    """Tiled mode-prior diagonal Λ: ``[lam_bias, lam_tilt] * n_pass``.

    Matches :func:`build_b`'s per-pass [bias, tilt] column interleave.

    Args:
        n_pass: Number of passes.
        lam_bias: Bias-mode prior variance [m^2].
        lam_tilt: Tilt-mode prior variance [m^2].

    Returns:
        (2*n_pass,) float64 diagonal.
    """
    return np.tile(np.asarray([lam_bias, lam_tilt], dtype=float), n_pass)


def err_identity(pt: PassTable) -> np.ndarray:
    """CRN identity rows for the "err" axis: (2*n_pass, 3) int64 (spec §5).

    Row ``2p + k`` is ``(mission_hash, pass_start_s, mode_idx=k)`` for pass
    p, mode k in {0=bias, 1=tilt} — deterministic and collision-free across
    missions, passes, and windows (time-based identity, never positional).

    Args:
        pt: The pass table.

    Returns:
        (2*n_pass, 3) int64 identity rows in build_b column order.
    """
    mode = np.tile(np.asarray([0, 1], dtype=np.int64), pt.n_pass)
    return np.ascontiguousarray(
        np.column_stack(
            [
                np.repeat(pt.pass_mission, 2),
                np.repeat(pt.pass_start_s, 2),
                mode,
            ]
        ).astype(np.int64)
    )
