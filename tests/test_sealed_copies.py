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
# Rubric v2 amendment (owner ruling 2026-07-27, pins 32 + 34). The Gate-0
# snapshot still quotes v1 by sha — that is history, and it must stay
# resolvable, which is why BOTH versions are tracked.
SEALED_SEAL_V2 = Path("sealed/phase14_evaluation_seal_v2.json")
CANONICAL_V2 = Path("data/2021a_ssh_mapping_ose/ours/phase14_evaluation_seal_v2.json")


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


@pytest.mark.skipif(
    not SEALED_SEAL_V2.exists(),
    reason=(
        "no v2 seal tracked: T13's amendment is PREPARED but WITHDRAWN pending "
        "the owner ruling (see PROGRESS.md). This test activates the moment the "
        "corrected v2 is sealed — the artifact's presence IS the condition."
    ),
)
def test_tracked_seal_v2_self_verifies_and_chains_to_v1() -> None:
    """v2 verifies from its own bytes AND names the v1 sha it supersedes.

    Bug caught: an amended seal committed without its chain — the Gate-0
    snapshot quotes v1 by sha, and with no `supersedes` link a reader
    cannot tell whether v2 replaced v1 or was minted independently
    (which is how a rubric amendment turns into an unauditable rewrite).
    Also catches a hand-edited v2 copy: one flipped content byte breaks
    the recompute.
    """
    v1 = json.loads(SEALED_SEAL.read_text())
    v2 = json.loads(SEALED_SEAL_V2.read_text())
    assert seal_sha(v2["content"]) == v2["seal_sha"]
    assert v2["content"]["supersedes"] == v1["seal_sha"]
    assert v2["seal_sha"] != v1["seal_sha"]
    # the amendment is an owner decision, recorded IN the sealed content
    assert "2026-07-27" in v2["content"]["signoff"]
    assert v2["content"]["instruments"]["seam"]["rubric_version"] == 2


@pytest.mark.skipif(
    not CANONICAL_V2.exists(),
    reason=f"live store not on this host: {CANONICAL_V2}",
)
def test_tracked_seal_v2_byte_identical_to_canonical() -> None:
    """Tracked v2 copy == the canonical data/ v2 seal, byte for byte.

    Bug caught: the amendment landing in the live store only, leaving the
    public auditability mirror one version behind.
    """
    assert SEALED_SEAL_V2.read_bytes() == CANONICAL_V2.read_bytes()
