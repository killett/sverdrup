"""Hygiene: the Stage-1 solve lock — an unreadable lock is stale, and two
acquirers cannot both hold it (phase14_stage1_run.stage1_solve_lock).

- An unreadable lock was recorded as pid -1, and ``os.kill(-1, 0)``
  signals a process GROUP and succeeds whenever ANY process is
  signalable — so "an unreadable lock is a stale lock" (the code's own
  comment) read as HELD, forever.
- Acquisition was check-then-``write_text``: a lock created between the
  check and the write was silently overwritten, and both acquirers held.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from tests.helpers import load_script

_mod = load_script("phase14_stage1_run")


def test_an_unreadable_lock_is_taken_over_as_stale(tmp_path: Path) -> None:
    """Bug caught: the corrupt lock left by a crash mid-write blocking every
    future leg as "pid -1 already holds the Stage-1 solve lock"."""
    lock = tmp_path / "solve.lock"
    lock.write_text("{half-written")
    with _mod.stage1_solve_lock("leg:kuroshio", path=lock) as held:
        assert held["took_over_stale"] == {"pid": -1, "label": "unreadable"}
        assert held["pid"] == os.getpid()


@pytest.mark.parametrize("pid", [-1, 0])
def test_a_non_positive_pid_is_never_a_live_holder(tmp_path: Path, pid: int) -> None:
    """Bug caught: kill(pid<=0, 0) reports a process GROUP as alive."""
    assert _mod._lock_holder_alive(pid) is False
    lock = tmp_path / "solve.lock"
    lock.write_text(json.dumps({"pid": pid, "label": "leg:ghost", "started": "then"}))
    with _mod.stage1_solve_lock("leg:kuroshio", path=lock) as held:
        assert held["took_over_stale"]["pid"] == pid


def test_a_lock_created_during_acquisition_is_not_overwritten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bug caught: the check-then-write race. A competitor's lock (a LIVE
    pid — our parent) lands after the existence check, while our holder
    block is being built; the acquisition must refuse, and the competitor's
    record must survive. Deterministic: ``datetime.now`` (called between
    the check and the write) plants it."""
    lock = tmp_path / "solve.lock"
    rival = {"pid": os.getppid(), "label": "leg:racer", "started": "now"}

    class _Racer(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> _Racer:  # noqa: ANN401
            if not lock.exists():
                lock.write_text(json.dumps(rival))
            return super().now(tz)

    monkeypatch.setattr(_mod, "datetime", _Racer)
    with pytest.raises(RuntimeError, match="solve lock"):
        with _mod.stage1_solve_lock("leg:kuroshio", path=lock):
            pass
    assert json.loads(lock.read_text()) == rival
