"""Sealed per-tile instrument configs (phase-14 0a-5).

ONE deterministic, serializable config object the Task-19 seal ingests:

- **GroundTrack per tile×era** — geometry-artifact keyed,
  constellation-aware (the 0.410→0.331 lineage as the standing
  instrument).
- **SpectralFidelity per tile** — band = tile extent (the box convention
  generalized; the λx helper parameterization lands with its first
  non-anchor consumer, Stage 1).
- **Seam rubric thresholds** — mirroring
  ``docs/validation/phase14_seam_rubric.md`` (a unit test pins doc↔code
  equality on the numbers).
- **In-situ nulls** — the Task-9 sealed :class:`InSituNullConfig` values.

Serialization is canonical JSON bytes — byte-deterministic, the seal
substrate.
"""

from __future__ import annotations

import json
from typing import Any

from sverdrup.eval.insitu import InSituNullConfig

# Seam verdict thresholds (pre-registered; the rubric doc is the prose
# source, these constants the code source — doc↔code equality is test-pinned).
SEAM_CLEAN_MAX = 1.0
SEAM_ELEVATED_MAX = 2.5

SCHEMA_VERSION = 1


def instrument_configs() -> dict[str, Any]:
    """The sealed instrument config set (deterministic, plain data).

    Returns:
        A JSON-serializable mapping with one entry per instrument family;
        every value is a plain scalar/str so canonical serialization is
        byte-deterministic.
    """
    nulls = InSituNullConfig()
    return {
        "schema_version": SCHEMA_VERSION,
        "groundtrack": {
            "per_tile": True,
            "per_era": True,
            "geometry_artifact_keyed": True,
            "constellation_aware": True,
        },
        "spectral_fidelity": {
            "per_tile": True,
            "band": "tile-extent",
            "convention": "box-generalized",
        },
        "seam": {
            "metric": "cross-seam dispersion ratio vs interior reference",
            "clean_max": SEAM_CLEAN_MAX,
            "elevated_max": SEAM_ELEVATED_MAX,
            "oracle": "seam-pair blend vs seamless signed truth",
            "rubric_doc": "docs/validation/phase14_seam_rubric.md",
        },
        "insitu_nulls": {
            "climo_smooth_days": nulls.climo_smooth_days,
            "persist_lag_days": nulls.persist_lag_days,
        },
    }


def serialize_instrument_configs(cfg: dict[str, Any] | None = None) -> bytes:
    """Canonical JSON bytes of the config set (the seal substrate).

    Args:
        cfg: Optional explicit config (defaults to
            :func:`instrument_configs`).

    Returns:
        Sorted-key, compact-separator UTF-8 JSON — byte-deterministic.
    """
    payload = instrument_configs() if cfg is None else cfg
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
