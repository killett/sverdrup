"""The phase-14 evaluation-set SEAL (0a-6): build / verify / supersede.

ONE sha-sealed artifact — the program's founding evaluation object:
epoch table (Task 5 bytes), locked gauge IDs + split seed + screening
config (Task 8), instrument configs incl. sealed nulls + seam thresholds
(Tasks 9/11), c2 era windows, and the descriptor schema version it binds
to (Task 1). Immutable: MUTATION of an existing seal file is impossible
through this API — amendment = a NEW version file carrying a supersession
pointer (fork-f pin 2); ``verify_seal`` on a superseded version still
passes (history stays auditable).
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

SEAL_DIR = Path("data/2021a_ssh_mapping_ose/ours")
SEAL_V1 = SEAL_DIR / "phase14_evaluation_seal_v1.json"
EVIDENCE = SEAL_DIR / "stage_miost_gate_results.json"

# The Task-1 SourceDescriptor schema this seal binds to.
DESCRIPTOR_SCHEMA_VERSION = 1

_VERSION_RE = re.compile(r"_v(\d+)\.json$")


class SealError(RuntimeError):
    """Seal build/verify/supersede refusal."""


def _canonical(content: dict[str, Any]) -> bytes:
    return json.dumps(content, sort_keys=True, separators=(",", ":")).encode()


def seal_sha(content: dict[str, Any]) -> str:
    """sha256 of the canonical content bytes."""
    return hashlib.sha256(_canonical(content)).hexdigest()


def assemble_content(
    epoch_table_bytes: bytes,
    locked_split: dict[str, list[str]],
    split_seed: int,
    screening_config: dict[str, Any],
    instrument_config_bytes: bytes,
    c2_era_windows: list[str],
) -> dict[str, Any]:
    """The deterministic seal content (pure assembly, no I/O).

    Args:
        epoch_table_bytes: ``serialize_epoch_table`` output (Task 5).
        locked_split: ``{"locked": [...], "dev": [...]}`` (Task 8).
        split_seed: The recorded split seed.
        screening_config: The recorded screening constants.
        instrument_config_bytes: ``serialize_instrument_configs`` output.
        c2_era_windows: Epoch ids where c2 is a locked instrument.

    Returns:
        The content mapping (canonicalized at sha/serialization time).
    """
    return {
        "schema_version": 1,
        "descriptor_schema_version": DESCRIPTOR_SCHEMA_VERSION,
        "epoch_table": json.loads(epoch_table_bytes),
        "locked_gauges": sorted(locked_split["locked"]),
        "dev_gauges": sorted(locked_split["dev"]),
        "split_seed": split_seed,
        "screening": screening_config,
        "instruments": json.loads(instrument_config_bytes),
        "c2_era_windows": sorted(c2_era_windows),
    }


def build_seal(content: dict[str, Any], path: Path = SEAL_V1) -> str:
    """Write the seal file (WRITE-ONCE) and return its sha.

    Args:
        content: The assembled content.
        path: The versioned seal path.

    Returns:
        The seal sha (also embedded in the file).

    Raises:
        SealError: If the path already exists — a seal is never rewritten;
            amendment goes through :func:`supersede_seal`.
    """
    if path.exists():
        raise SealError(
            f"seal {path} already exists — seals are write-once; amendment "
            "= supersede_seal with owner signoff (fork-f pin 2)"
        )
    sha = seal_sha(content)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"content": content, "seal_sha": sha}, indent=1, sort_keys=True)
        + "\n"
    )
    return sha


def verify_seal(path: Path, expected_sha: str) -> None:
    """Byte-recompute verification — a single flipped byte refuses.

    Args:
        path: The seal file.
        expected_sha: The sha the caller holds (evidence/pack).

    Raises:
        SealError: Missing file, embedded/recomputed/expected mismatch.
    """
    if not path.exists():
        raise SealError(f"seal file {path} does not exist")
    payload = json.loads(path.read_text())
    recomputed = seal_sha(payload["content"])
    if recomputed != payload.get("seal_sha"):
        raise SealError(
            f"seal {path} TAMPERED: embedded sha {payload.get('seal_sha')!r} "
            f"!= recomputed {recomputed}"
        )
    if recomputed != expected_sha:
        raise SealError(
            f"seal {path} sha {recomputed} != expected {expected_sha} — "
            "wrong version or stale reference"
        )


def supersede_seal(
    old_path: Path, new_content: dict[str, Any], owner_signoff: str
) -> tuple[Path, str]:
    """Amendment: a NEW version file with a supersession pointer.

    Args:
        old_path: The current seal (must verify against itself).
        new_content: The amended content.
        owner_signoff: The owner's recorded signoff line (required).

    Returns:
        ``(new_path, new_sha)`` — ``…_v{n+1}.json``.

    Raises:
        SealError: Unparseable version, missing signoff, or existing target.
    """
    if not owner_signoff.strip():
        raise SealError("supersession requires an owner signoff line")
    m = _VERSION_RE.search(old_path.name)
    if not m:
        raise SealError(f"cannot parse seal version from {old_path.name!r}")
    old_payload = json.loads(old_path.read_text())
    old_sha = seal_sha(old_payload["content"])
    n = int(m.group(1))
    new_path = old_path.with_name(_VERSION_RE.sub(f"_v{n + 1}.json", old_path.name))
    from datetime import UTC, datetime  # noqa: PLC0415

    content = dict(new_content)
    content["supersedes"] = old_sha
    content["signoff"] = owner_signoff
    content["date"] = datetime.now(UTC).date().isoformat()
    sha = build_seal(content, new_path)
    return new_path, sha


def verify_current_seal(evidence_path: Path | None = None) -> None:
    """The Task-10 ceremony tripwire: verify the CURRENT seal via evidence.

    Reads the recorded ``phase14.stage0.seal`` pointer (path + sha) from
    the evidence JSON and byte-verifies it. Refuses while no seal is
    recorded — a locked open before the sealed set exists is definitionally
    unceremonied.

    Args:
        evidence_path: Evidence store to read the pointer from; defaults to
            the standing :data:`EVIDENCE`. Callers that operate on an
            isolated store MUST pass it — verifying a scratch store against
            the production pointer proves nothing about either.

    Raises:
        SealError: No recorded seal, or verification failure.
    """
    store = EVIDENCE if evidence_path is None else evidence_path
    if not store.exists():
        raise SealError("no evidence store — no seal recorded")
    node = (
        json.loads(store.read_text()).get("phase14", {}).get("stage0", {}).get("seal")
    )
    if not node:
        raise SealError(
            "no phase-14 seal recorded in evidence (Task 19 not run) — "
            "locked data cannot open before the sealed set is signed"
        )
    verify_seal(Path(node["path"]), node["sha"])
