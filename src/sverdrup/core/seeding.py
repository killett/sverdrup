"""Deterministic per-unit-of-work seed derivation (spec section 5.9)."""

from __future__ import annotations

import hashlib

from sverdrup.core.types import Seed


def derive_seed(
    method: str, params_key: str, window_id: str, member_index: int
) -> Seed:
    """Derive a reproducible seed from the unit-of-work identity.

    Args:
        method: Method name (e.g. "oi").
        params_key: Canonical string of resolved parameters.
        window_id: Stable identifier of the space-time window.
        member_index: Ensemble member index (0 for the base solve).

    Returns:
        A non-negative 63-bit integer suitable for numpy's default_rng.
    """
    payload = "\x1f".join([method, params_key, window_id, str(member_index)]).encode()
    digest = hashlib.blake2b(payload, digest_size=8).digest()
    return int.from_bytes(digest, "big") >> 1
