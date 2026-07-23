"""Seal build/verify/supersede tests (phase-14 Task 19, 0a-6)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from sverdrup.validation.phase14_seal import (
    SealError,
    assemble_content,
    build_seal,
    seal_sha,
    supersede_seal,
    verify_seal,
)


def _content() -> dict[str, Any]:
    return assemble_content(
        epoch_table_bytes=json.dumps([{"epoch_id": "e00", "holdout": "e1"}]).encode(),
        locked_split={"locked": ["uh002", "uh001"], "dev": ["uh003"]},
        split_seed=12345,
        screening_config={"l_prox_km": 150.0, "proximity": "deferred"},
        instrument_config_bytes=json.dumps({"seam": {"clean_max": 1.0}}).encode(),
        c2_era_windows=["e07", "e06"],
    )


def test_recompute_byte_identical(tmp_path: Path) -> None:
    """Rebuilding from the same inputs is byte-identical (same sha)."""
    assert seal_sha(_content()) == seal_sha(_content())
    p = tmp_path / "seal_v1.json"
    sha = build_seal(_content(), p)
    verify_seal(p, sha)  # green path
    assert json.loads(p.read_text())["seal_sha"] == sha


def test_content_normalization() -> None:
    """Gauge lists sort canonically — input order cannot move the sha."""
    a = _content()
    b = assemble_content(
        epoch_table_bytes=json.dumps([{"epoch_id": "e00", "holdout": "e1"}]).encode(),
        locked_split={"locked": ["uh001", "uh002"], "dev": ["uh003"]},
        split_seed=12345,
        screening_config={"l_prox_km": 150.0, "proximity": "deferred"},
        instrument_config_bytes=json.dumps({"seam": {"clean_max": 1.0}}).encode(),
        c2_era_windows=["e06", "e07"],
    )
    assert seal_sha(a) == seal_sha(b)


def test_tamper_single_byte_refuses(tmp_path: Path) -> None:
    """One flipped byte in the file -> refusal (the protocol_sha pattern)."""
    p = tmp_path / "seal_v1.json"
    sha = build_seal(_content(), p)
    text = p.read_text().replace("uh001", "uh00X", 1)
    p.write_text(text)
    with pytest.raises(SealError, match="TAMPERED"):
        verify_seal(p, sha)


def test_wrong_expected_sha_refuses(tmp_path: Path) -> None:
    """A stale/wrong caller-held sha refuses even on an intact file."""
    p = tmp_path / "seal_v1.json"
    build_seal(_content(), p)
    with pytest.raises(SealError, match="expected"):
        verify_seal(p, "0" * 64)


def test_write_once(tmp_path: Path) -> None:
    """A second build at the same path refuses — mutation impossible."""
    p = tmp_path / "seal_v1.json"
    build_seal(_content(), p)
    with pytest.raises(SealError, match="write-once"):
        build_seal(_content(), p)


def test_supersession_chain(tmp_path: Path) -> None:
    """v2 carries {supersedes, signoff, date}; v1 STILL verifies."""
    p1 = tmp_path / "seal_v1.json"
    sha1 = build_seal(_content(), p1)
    new = dict(_content())
    new["locked_gauges"] = ["uh001"]
    p2, sha2 = supersede_seal(p1, new, owner_signoff="owner ruling 2026-07-30")
    assert p2.name.endswith("_v2.json")
    payload2 = json.loads(p2.read_text())
    assert payload2["content"]["supersedes"] == sha1
    assert payload2["content"]["signoff"] == "owner ruling 2026-07-30"
    verify_seal(p1, sha1)  # history auditable
    verify_seal(p2, sha2)
    with pytest.raises(SealError, match="signoff"):
        supersede_seal(p2, new, owner_signoff="  ")


def test_ceremony_wired_to_real_verifier(tmp_path: Path) -> None:
    """open_touch with verify_seal-based verifier: mismatch refuses the
    ceremony BEFORE any locked open; a good seal opens it."""
    from sverdrup.validation.locked_tier import open_touch

    p = tmp_path / "seal_v1.json"
    sha = build_seal(_content(), p)
    ev = tmp_path / "evidence.json"
    ev.write_text(json.dumps({"phase14": {"locked_tally": {}}}))
    import os

    os.environ["SVERDRUP_PHASE14_TOUCH"] = "1"
    try:
        with pytest.raises(SealError):
            with open_touch("prod", ["e00"], ev, lambda: verify_seal(p, "0" * 64)):
                pass
        with open_touch("prod", ["e00"], ev, lambda: verify_seal(p, sha)):
            pass
    finally:
        os.environ.pop("SVERDRUP_PHASE14_TOUCH", None)
