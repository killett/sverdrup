"""P0-2 blocking precondition: stage-B evidence clobber path refuses by default.

Hygiene register P0-2 (docs/hygiene-priorities.md): any future plan invoking
tune_miost_inflation or writing stage_b_* canonical names fixes this first.
Phase-14 Task 0 hardens the write into a refusal unless
SVERDRUP_ALLOW_STAGEB_EVIDENCE="1" (exact string).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.helpers import load_script

_write_evidence_guarded = load_script("tune_miost_inflation")._write_evidence_guarded

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "tune_miost_inflation.py"
ENV = "SVERDRUP_ALLOW_STAGEB_EVIDENCE"


def _delegate_factory(target: Path) -> tuple[list[tuple[object, ...]], object]:
    """A recording delegate that clobbers ``target`` when invoked."""
    calls: list[tuple[object, ...]] = []

    def delegate(*args: object, **kwargs: object) -> str:
        calls.append(args)
        target.write_bytes(b"CLOBBERED")
        return "wrote"

    return calls, delegate


def test_refuses_without_env_before_any_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without the env var the guard raises BEFORE the delegate runs."""
    monkeypatch.delenv(ENV, raising=False)
    evidence = tmp_path / "stage_b_mean_maps.nc"
    evidence.write_bytes(b"SIGNED-EVIDENCE")
    calls, delegate = _delegate_factory(evidence)

    with pytest.raises(RuntimeError, match=r"P0-2") as excinfo:
        _write_evidence_guarded(delegate, evidence)

    assert "docs/hygiene-priorities.md" in str(excinfo.value)
    assert calls == []
    assert evidence.read_bytes() == b"SIGNED-EVIDENCE"


@pytest.mark.parametrize("value", ["true", "yes", "", "0", "1 "])
def test_refuses_on_non_exact_string(
    value: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only the exact string "1" opens the path — truthy strings refuse."""
    monkeypatch.setenv(ENV, value)
    evidence = tmp_path / "stage_b_var_maps.nc"
    evidence.write_bytes(b"SIGNED-EVIDENCE")
    calls, delegate = _delegate_factory(evidence)

    with pytest.raises(RuntimeError, match=r"P0-2"):
        _write_evidence_guarded(delegate, evidence)
    assert calls == []
    assert evidence.read_bytes() == b"SIGNED-EVIDENCE"


def test_writes_with_env_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """With the exact-string opt-in the delegate runs with the original args."""
    monkeypatch.setenv(ENV, "1")
    evidence = tmp_path / "stage_b_mean_maps.nc"
    evidence.write_bytes(b"SIGNED-EVIDENCE")
    calls, delegate = _delegate_factory(evidence)

    result = _write_evidence_guarded(delegate, evidence, tag="x")

    assert result == "wrote"
    assert calls == [(evidence,)]
    assert evidence.read_bytes() == b"CLOBBERED"


def test_main_has_no_unguarded_write_map_call() -> None:
    """The script never calls write_map directly — only through the guard."""
    source = SCRIPT.read_text()
    direct = [
        line
        for line in source.splitlines()
        if re.search(r"(?<![\w.])write_map\(", line)
        and "_write_evidence_guarded" not in line
    ]
    assert direct == [], f"unguarded write_map call(s): {direct}"
