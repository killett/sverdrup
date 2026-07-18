"""Phase-12 evidence schema: key layout + provenance hash fields (spec §5).

Shared BY CONSTRUCTION between the pack writer (``--run``) and the touch-time
asserter (``--c2-touch``): both import THIS module, so the field names the
writer records are the field names the tripwire recomputes — they cannot
drift apart.

Writer discipline (fork-d pin): every write is a read-modify-write of ONE
leaf key via ``atomic_write_json`` — siblings (including foreign phase8/
phase11 blocks in a shared store) always survive.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

MIOST6_PREFIX = "phase12.miost6"
DEV_SMOKE_PREFIX = "phase12_dev_smoke"
MIOST6_KEYS = (
    "geometry",
    "telemetry",
    "budget",
    "report_rows",
    "deltas",
    "tier3",
    "provenance",
    "c2_acceptance",
)

PROVENANCE_HASH_FIELDS = (
    "mean_maps_sha256",
    "var_maps_sha256",
    "member_store_sha256",
    "cal_key",
    "scope_cfg_sha256",
    "geometry_artifact_sha256",
)


def sha256_file(path: Path | str) -> str:
    """sha256 hex digest of a file's bytes.

    Args:
        path: The file to hash.

    Returns:
        The hex digest.
    """
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def provenance_block(
    mean_maps: Path | str,
    var_maps: Path | str,
    member_store: Path | str,
    cal_key: str,
    scope_cfg: Path | str,
    geometry_artifact: Path | str,
) -> dict[str, str]:
    """Build the closed-input-set provenance block (all six hash fields).

    Args:
        mean_maps: The six-mission mean maps NetCDF.
        var_maps: The six-mission variance maps NetCDF.
        member_store: The member-store npz (the touch reads members from it).
        cal_key: The byte-stable calibration key of the shipped s(x) field.
        scope_cfg: The phase12 scope JSON the run loaded.
        geometry_artifact: The six-mission orbit-geometry artifact JSON.

    Returns:
        Dict with exactly the ``PROVENANCE_HASH_FIELDS`` keys.
    """
    return {
        "mean_maps_sha256": sha256_file(mean_maps),
        "var_maps_sha256": sha256_file(var_maps),
        "member_store_sha256": sha256_file(member_store),
        "cal_key": cal_key,
        "scope_cfg_sha256": sha256_file(scope_cfg),
        "geometry_artifact_sha256": sha256_file(geometry_artifact),
    }


def assert_provenance_matches(
    recorded: dict[str, Any], recomputed: dict[str, Any]
) -> None:
    """Refuse on ANY provenance field mismatch (determinism tripwire).

    Args:
        recorded: The provenance block persisted by the evidence run.
        recomputed: A block freshly computed from the on-disk artifacts.

    Raises:
        ValueError: Naming every mismatched or missing field. The caller
            must not have opened the c2 file yet — and must never re-solve.
    """
    problems = []
    for field in PROVENANCE_HASH_FIELDS:
        if field not in recorded:
            problems.append(f"{field}: MISSING from recorded block")
        elif field not in recomputed:
            problems.append(f"{field}: MISSING from recomputed block")
        elif recorded[field] != recomputed[field]:
            problems.append(
                f"{field}: recorded {recorded[field]!r} != recomputed "
                f"{recomputed[field]!r}"
            )
    if problems:
        raise ValueError(
            "provenance tripwire REFUSED (closed input set violated; never "
            "a re-solve — attribute first): " + "; ".join(problems)
        )


def write_pack_entry(results: Path, key_path: str, value: object) -> None:
    """Atomic read-modify-write of ONE leaf key; every sibling survives.

    Args:
        results: The evidence JSON path (created if absent).
        key_path: Dot-separated key, e.g. ``"phase12.miost6.telemetry"``.
        value: JSON-serializable value for the leaf.
    """
    from sverdrup.application.calibration.harness import atomic_write_json

    evidence: dict[str, Any] = (
        json.loads(results.read_text()) if results.exists() else {}
    )
    keys = key_path.split(".")
    node: dict[str, Any] = evidence
    for k in keys[:-1]:
        node = node.setdefault(k, {})
    node[keys[-1]] = value
    atomic_write_json(results, evidence)
