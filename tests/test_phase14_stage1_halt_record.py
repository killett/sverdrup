"""Hygiene: the Stage-1 headroom halt record is written atomically.

``record_headroom_halt`` used ``dest.write_text``: a process killed mid-write
leaves a torn record, and ``_prior_halts_block`` silently reads a torn record
as "never halted" — the resumed leg's row then drops the warning that its
wall_s spans a pause (a silently wrong pricing input).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from tests.helpers import load_script

_mod = load_script("phase14_stage1_run")


def test_a_kill_during_the_halt_write_leaves_the_previous_record_intact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bug caught: a non-atomic write. Both write paths are made to die
    mid-flight — a direct ``write_text`` writes half its text and is killed;
    a temp-and-rename is killed at the rename — and the record on disk must
    be the PREVIOUS one, whole."""
    dest = tmp_path / "kuroshio_headroom_halt.json"
    prior = {"kind": "HEADROOM_HALT", "windows_completed": 3}
    dest.write_text(json.dumps(prior))

    def _torn_write(self: Path, data: str, *_a: Any, **_k: Any) -> int:  # noqa: ANN401
        with open(self, "w") as fh:
            fh.write(data[: len(data) // 2])
        raise KeyboardInterrupt

    def _killed_rename(*_a: Any, **_k: Any) -> None:  # noqa: ANN401
        raise KeyboardInterrupt

    monkeypatch.setattr(Path, "write_text", _torn_write)
    monkeypatch.setattr(os, "replace", _killed_rename)
    with pytest.raises(KeyboardInterrupt):
        _mod.record_headroom_halt(
            dest, tile="kuroshio", watchdog={}, windows_done=6, window_id="w6"
        )
    monkeypatch.undo()
    assert json.loads(dest.read_text()) == prior
    assert sorted(p.name for p in tmp_path.iterdir()) == [dest.name]  # no temp litter
