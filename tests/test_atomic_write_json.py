"""``harness.atomic_write_json`` — every evidence writer routes through it.

Hygiene P1-#3: on an ``os.replace`` failure the handler re-closed an fd the
``try`` had already closed, so ``OSError(EBADF)`` masked the real error and
the ``.tmp`` file leaked (the unlink was skipped). The single ``os.write``
was also unchecked: a short write installed a truncated JSON file
ATOMICALLY — the one failure "atomic" exists to prevent.

Expected values are hand-constructed; no assertion reads the implementation.
"""

from __future__ import annotations

import errno
import json
import os
from pathlib import Path

import numpy as np
import pytest

from sverdrup.application.calibration.harness import atomic_write_json

_DATA = {"phase14": {"gate5": {"mu": 0.75, "n": 3}}, "rows": [1, 2, 3]}


def _temps(directory: Path) -> list[str]:
    return sorted(p.name for p in directory.iterdir() if p.name.endswith(".tmp"))


def test_round_trip_replaces_the_target_and_leaves_no_temp(tmp_path: Path) -> None:
    """Bug caught: a temp file left behind on success, or numpy values that
    no longer serialise (the evidence rows carry numpy scalars and arrays)."""
    target = tmp_path / "store.json"
    target.write_text('{"old": true}')
    atomic_write_json(target, {"x": np.float64(1.5), "a": np.array([1, 2])})
    assert json.loads(target.read_text()) == {"x": 1.5, "a": [1, 2]}
    assert _temps(tmp_path) == []


def test_a_failed_replace_reraises_the_original_error_and_cleans_up(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bug caught: the double close — EBADF raised from the handler masks
    the real failure, and the temp file leaks because its unlink is skipped."""
    target = tmp_path / "store.json"
    target.write_text('{"old": true}')
    before = target.read_bytes()

    def _cross_device(src: object, dst: object) -> None:
        raise OSError(errno.EXDEV, "Invalid cross-device link")

    monkeypatch.setattr(os, "replace", _cross_device)
    with pytest.raises(OSError) as exc:
        atomic_write_json(target, _DATA)
    assert exc.value.errno == errno.EXDEV
    assert target.read_bytes() == before
    assert _temps(tmp_path) == []


def test_a_short_os_write_never_installs_a_truncated_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bug caught: one unchecked ``os.write`` — a partial write (legal for
    write(2)) was renamed over the store, truncating it atomically."""
    target = tmp_path / "store.json"
    real_write = os.write

    def _half_write(fd: int, data: bytes) -> int:
        return real_write(fd, data[: max(1, len(data) // 2)])

    monkeypatch.setattr(os, "write", _half_write)
    atomic_write_json(target, _DATA)
    assert json.loads(target.read_text()) == _DATA
