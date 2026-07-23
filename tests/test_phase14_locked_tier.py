"""Locked-tier touch ceremony tests (phase-14 Task 10, 0a-4).

The eight refusal legs (the phase-13 pre-touch pattern) + the accept path,
against an injected seal verifier (the real one lands at Task 19; the
interface is pinned here).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from sverdrup.adapters.insitu.gauges import LOCKED_ENV
from sverdrup.validation.locked_tier import (
    TOUCH_ENV,
    SealVerificationError,
    TouchRefusedError,
    open_touch,
    read_tally,
)


def _evidence(tmp_path: Path, tally: dict[str, Any] | None = None) -> Path:
    p = tmp_path / "evidence.json"
    p.write_text(json.dumps({"phase14": {"locked_tally": tally or {}}}))
    return p


def _ok_seal() -> None:
    return None


def _bad_seal() -> None:
    raise SealVerificationError("seal sha mismatch (injected)")


def test_refuses_without_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """(1) No ceremony env -> refuse before anything else."""
    monkeypatch.delenv(TOUCH_ENV, raising=False)
    with pytest.raises(TouchRefusedError, match=TOUCH_ENV):
        with open_touch("prodA", ["e00"], _evidence(tmp_path), _ok_seal):
            pass


@pytest.mark.parametrize("value", ["true", "yes", "", "0"])
def test_refuses_non_exact_string(
    value: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """(2) Only the exact string "1" opens the ceremony."""
    monkeypatch.setenv(TOUCH_ENV, value)
    with pytest.raises(TouchRefusedError):
        with open_touch("prodA", ["e00"], _evidence(tmp_path), _ok_seal):
            pass


def test_refuses_on_seal_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """(3) Seal verification fails -> refuse BEFORE any locked data opens."""
    monkeypatch.setenv(TOUCH_ENV, "1")
    with pytest.raises(SealVerificationError, match="mismatch"):
        with open_touch("prodA", ["e00"], _evidence(tmp_path), _bad_seal):
            pass
    assert read_tally(_evidence(tmp_path)) == {}  # nothing counted


def test_refuses_on_missing_seal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """(4) The default verifier refuses while no seal exists (pre-Task-19)."""
    monkeypatch.setenv(TOUCH_ENV, "1")
    with pytest.raises(SealVerificationError, match="[Ss]eal"):
        with open_touch("prodA", ["e00"], _evidence(tmp_path)):
            pass


def test_refuses_tally_exceeded_without_defect_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """(5) A second touch on the same (product, era) refuses (one-touch)."""
    monkeypatch.setenv(TOUCH_ENV, "1")
    ev = _evidence(tmp_path, {"prodA": {"e00": 1}})
    with pytest.raises(TouchRefusedError, match="tally"):
        with open_touch("prodA", ["e00"], ev, _ok_seal):
            pass


def test_defect_key_path_accepted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """(6) The owner's dated defect key authorizes the corrected re-touch
    (the misfire protocol, owner 2026-07-20, applied verbatim)."""
    monkeypatch.setenv(TOUCH_ENV, "1")
    ev = _evidence(tmp_path, {"prodA": {"e00": 1}})
    with open_touch(
        "prodA", ["e00"], ev, _ok_seal, corrected_by="2026-07-20-defect-xyz"
    ):
        pass
    tally = read_tally(ev)
    assert tally["prodA"]["e00"] == 2
    assert tally["prodA"]["e00_corrected_by"] == "2026-07-20-defect-xyz"


def test_refuses_double_open(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """(7) A nested/concurrent open refuses (single-ceremony discipline)."""
    monkeypatch.setenv(TOUCH_ENV, "1")
    ev = _evidence(tmp_path)
    with open_touch("prodA", ["e00"], ev, _ok_seal):
        with pytest.raises(TouchRefusedError, match="open"):
            with open_touch("prodB", ["e01"], ev, _ok_seal):
                pass


def test_dev_pool_unaffected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """(8) Outside the ceremony the locked env is UNSET — dev loads never
    see it; inside, the ceremony sets it for its child scope ONLY."""
    monkeypatch.setenv(TOUCH_ENV, "1")
    monkeypatch.delenv(LOCKED_ENV, raising=False)
    ev = _evidence(tmp_path)
    with open_touch("prodA", ["e00"], ev, _ok_seal):
        assert os.environ.get(LOCKED_ENV) == "1"  # ceremony child scope
    assert os.environ.get(LOCKED_ENV) is None  # restored after


def test_clean_touch_increments_tally(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The accept path counts EXACTLY one touch per (product, era)."""
    monkeypatch.setenv(TOUCH_ENV, "1")
    ev = _evidence(tmp_path)
    with open_touch("prodA", ["e00", "e01"], ev, _ok_seal):
        pass
    assert read_tally(ev) == {"prodA": {"e00": 1, "e01": 1}}


def test_gate_approval_sentence_in_docstring() -> None:
    """The standing rule rides in the module docstring."""
    import sverdrup.validation.locked_tier as mod

    assert "gate approval is NOT touch authorization" in (mod.__doc__ or "")
