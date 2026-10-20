"""Hygiene: stage-1 entry points resolve their store paths at CALL time.

The stage-1 test sandbox (pin 110a) monkeypatches the module globals
EVIDENCE / STAGE1_DIR / LANE0_DIR — but 17 functions and CLI commands took
``evidence_path: Path = EVIDENCE`` (or ``dest: Path = LANE0_DIR``) as a
default, bound when the script was IMPORTED. Patching the global did not
reach them: one forgotten kwarg in a test read — or WROTE — the live store.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from tests.helpers import load_script

_mod = load_script("phase14_stage1_run")
_LIVE = {_mod.EVIDENCE, _mod.STAGE1_DIR, _mod.LANE0_DIR}


def test_no_function_binds_a_store_path_at_import() -> None:
    """Bug caught: an import-bound default the sandbox cannot redirect."""
    offenders = sorted(
        f"{name}({param.name})"
        for name, fn in inspect.getmembers(_mod, inspect.isfunction)
        if fn.__module__ == _mod.__name__
        for param in inspect.signature(fn).parameters.values()
        if isinstance(param.default, Path) and param.default in _LIVE
    )
    assert offenders == []


def test_a_no_argument_read_follows_the_patched_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The behaviour the sandbox relies on: with EVIDENCE patched to a path
    that does not exist, a call with no evidence_path must fail ON THAT
    PATH — not silently read the live store."""
    ghost = tmp_path / "no_such_store.json"
    monkeypatch.setattr(_mod, "EVIDENCE", ghost)
    with pytest.raises(Exception) as info:  # noqa: PT011 - any failure, but on the ghost
        _mod.poleward_obs_edges()
    assert str(ghost) in str(info.value)
