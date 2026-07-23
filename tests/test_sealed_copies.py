"""Tracked sealed/ copies stay self-consistent (Gate-0 ruling item 5).

The seal's value IS its public auditability: the tracked copy must verify
from its own bytes, agree with the snapshot's recorded pointer, and (on
hosts that carry the live store) stay byte-identical to the canonical
file under data/.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sverdrup.validation.phase14_seal import seal_sha

SEALED_SEAL = Path("sealed/phase14_evaluation_seal_v1.json")
SNAPSHOT = Path("sealed/phase14_gate0_evidence_snapshot.json")
CANONICAL = Path("data/2021a_ssh_mapping_ose/ours/phase14_evaluation_seal_v1.json")


def test_tracked_seal_self_verifies() -> None:
    """Embedded seal_sha equals the canonical-content recompute.

    Bug caught: a tampered or hand-edited tracked copy — one flipped
    byte in content changes the recompute and this fails.
    """
    doc = json.loads(SEALED_SEAL.read_text())
    assert seal_sha(doc["content"]) == doc["seal_sha"]


def test_snapshot_pointer_matches_tracked_seal() -> None:
    """The snapshot's phase14.stage0.seal sha is the tracked seal's sha.

    Bug caught: seal and evidence snapshot updated independently
    (a superseded seal committed without its snapshot, or vice versa).
    """
    doc = json.loads(SEALED_SEAL.read_text())
    snap = json.loads(SNAPSHOT.read_text())
    assert snap["phase14"]["stage0"]["seal"]["sha"] == doc["seal_sha"]


@pytest.mark.skipif(
    not CANONICAL.exists(),
    reason=f"live store not on this host: {CANONICAL}",
)
def test_tracked_seal_byte_identical_to_canonical() -> None:
    """Tracked copy == the canonical data/ seal, byte for byte."""
    assert SEALED_SEAL.read_bytes() == CANONICAL.read_bytes()
