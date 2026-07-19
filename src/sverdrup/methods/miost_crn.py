"""Identity-keyed common random numbers for Stage-B members (spec 6.2).

Perturbations are pure functions of ``(seed root, member, identity)`` —
never of window membership, enumeration order, or array position. Two
overlapping windows therefore perturb a shared observation/element
IDENTICALLY, keeping member fields coherent across window seams with no
cross-window communication.
"""

from __future__ import annotations

import hashlib

import numpy as np
from scipy.special import ndtri  # type: ignore[import-untyped]

from sverdrup.core.types import Seed


def _keyed_uniform(key: bytes, rows: np.ndarray) -> np.ndarray:
    """Deterministic U(0,1) per row from a keyed hash of the row's bytes.

    Args:
        key: Stream key (root + member + axis), 16 bytes.
        rows: (n, k) array; each row is one identity, hashed as raw bytes.

    Returns:
        (n,) uniforms via blake2b(row, key) -> uint64 -> (u + 0.5) / 2**64
        (strictly inside (0, 1), so ndtri never sees 0 or 1).
    """
    contig = np.ascontiguousarray(rows)
    out = np.empty(contig.shape[0])
    for i in range(contig.shape[0]):  # blake2b ~1 us/row; vectorize if hot
        h = hashlib.blake2b(contig[i].tobytes(), key=key, digest_size=8).digest()
        out[i] = (int.from_bytes(h, "big") + 0.5) / 2.0**64
    return out


def _member_key(root: Seed, member: int, axis: str) -> bytes:
    """16-byte stream key separating (root, member) and the obs/elem axes."""
    return hashlib.blake2b(f"{root}|{member}|{axis}".encode(), digest_size=16).digest()


def obs_noise(
    member: int, identity: np.ndarray, r_var: np.ndarray, root: Seed
) -> np.ndarray:
    """Observation perturbation eps' ~ N(0, R), keyed by obs identity.

    Args:
        member: Ensemble member index.
        identity: (n, 4) float64 rows (lon, lat, time, mission-hash) — the
            window-independent identity of each observation.
        r_var: (n,) observation-error variances (diagonal R).
        root: Seed root from :func:`sverdrup.core.seeding.derive_seed`.

    Returns:
        (n,) draws; identical for the same (root, member, identity row)
        regardless of which window subsets the observation.
    """
    u = _keyed_uniform(_member_key(root, member, "obs"), identity)
    return np.asarray(np.sqrt(r_var) * ndtri(u))


def coef_noise(
    member: int, identity: np.ndarray, q_var: np.ndarray, root: Seed
) -> np.ndarray:
    """Coefficient perturbation eta~ ~ N(0, Q), keyed by element identity.

    Args:
        member: Ensemble member index.
        identity: (n, 6) int64 element identity rows
            (scale_idx, dir_idx, phase_idx, ix, iy, global_slot).
        q_var: (n,) prior variances (diagonal Q).
        root: Seed root from :func:`sverdrup.core.seeding.derive_seed`.

    Returns:
        (n,) draws; identical for the same (root, member, identity row)
        across overlapping windows.
    """
    u = _keyed_uniform(_member_key(root, member, "elem"), identity)
    return np.asarray(np.sqrt(q_var) * ndtri(u))


def err_noise(
    member: int, identity: np.ndarray, lam_var: np.ndarray, root: Seed
) -> np.ndarray:
    """Error-mode perturbation c̃ ~ N(0, Λ), keyed by mode identity (spec §5).

    The phase-13 "err" axis: stream-key separation from the obs/elem axes
    makes collisions impossible by construction; identity rows are the
    TIME-BASED ``err_identity`` rows (mission_hash, pass_start_s,
    mode_idx), so overlapping windows draw identical c̃ for a shared pass
    — the cross-window CRN property extended to the new draws.

    Args:
        member: Ensemble member index.
        identity: (n, 3) int64 mode identity rows (``err_identity``).
        lam_var: (n,) mode prior variances (the tiled Λ diagonal).
        root: Seed root from :func:`sverdrup.core.seeding.derive_seed`.

    Returns:
        (n,) draws; identical for the same (root, member, identity row)
        regardless of window membership or array position.
    """
    u = _keyed_uniform(_member_key(root, member, "err"), identity)
    return np.asarray(np.sqrt(lam_var) * ndtri(u))
