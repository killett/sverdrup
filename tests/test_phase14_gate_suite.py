"""Hygiene: the gate-suite stamp attests exactly what it covers (pin 197c).

Three scope defects in scripts/phase14_gate_suite.py:

- the stamp covered ``*.py`` + pyproject only, so the shell scripts, the
  git hook, the JSON fixtures and the evidence mirror — all read by tests
  — could change mid-run with the stamp still green;
- ``verify`` never said WHICH command ran, so a ``--suite`` subset
  attested exactly like the full suite;
- ``suite.split()`` broke a quoted argument (a ``--deselect`` node id with
  spaces) into pieces.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sverdrup.validation.gate_stamp import file_digests
from tests.helpers import load_script

_mod = load_script("phase14_gate_suite")
_REPO = Path(__file__).resolve().parents[1]


def test_the_stamp_covers_the_non_python_files_tests_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bug caught: a mid-run edit to any of these left verify green."""
    monkeypatch.chdir(_REPO)
    tracked = set(_mod._tracked())
    for path in (
        "scripts/resume_checks.sh",
        "scripts/stage1_leg_launcher.sh",
        "scripts/git_hooks/post-commit",
        "tests/validation/fixtures/stage_a_scope.json",
        "pixi.toml",
    ):
        assert path in tracked, path
    assert any(p.startswith("docs/validation/evidence-mirror/") for p in tracked)


def test_a_quoted_suite_argument_stays_one_argument() -> None:
    """Bug caught: str.split() turning one --deselect node id into three."""
    argv = _mod._suite_argv('pixi run pytest --deselect "tests/x.py::test a b" -q')
    assert argv == [
        "pixi",
        "run",
        "pytest",
        "--deselect",
        "tests/x.py::test a b",
        "-q",
    ]


def test_verify_states_the_command_its_stamp_attests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Bug caught: a green verify silent about scope — a one-file run read
    exactly like the full suite."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "m.py").write_text("x = 1\n")
    command = "pixi run pytest -q tests/test_one.py"
    stamp = {
        "stamped_utc": "then",
        "n_files": 1,
        "digests": file_digests(Path(), _mod._tracked()),
        "suite": {
            "completed": True,
            "exit_code": 0,
            "command": command,
            "finished_utc": "later",
        },
    }
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "gate_stamp.json").write_text(json.dumps(stamp))
    _mod.verify()
    assert command in capsys.readouterr().out
