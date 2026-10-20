"""Hygiene: diag_stage1_hypothesis_tests STOPs before writing its artifact.

Owner pin 205(d): when a ruling-quoted figure does not reproduce, the
script stops "rather than recording a disagreement" — its own message says
"Nothing is recorded". It wrote the tracked JSON artifact first, so the
disagreement WAS recorded (in git's working tree) before the STOP fired.
The data loaders and payload builder are stubbed: what is under test is the
ORDER of the write and the STOP in ``main``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests.helpers import load_script


def _payload(reproduced: bool) -> dict[str, Any]:
    return {
        "all_ruling_quotes_reproduced": reproduced,
        "ruling_quote_verification": [
            {
                "tile": "kuroshio",
                "band_km": [100, 200],
                "on_canonical_grid": True,
                "quoted": {},
                "computed": {},
                "per_field_agrees": {},
                "agrees": reproduced,
            }
        ],
    }


def _stubbed(monkeypatch: pytest.MonkeyPatch, reproduced: bool) -> Any:  # noqa: ANN401
    mod = load_script("diag_stage1_hypothesis_tests")
    monkeypatch.setattr(mod, "track_spectrum", lambda _t: None)
    monkeypatch.setattr(mod, "skill_spectrum", lambda _t: None)
    monkeypatch.setattr(mod, "build_payload", lambda *_a: _payload(reproduced))
    return mod


def test_a_non_reproducing_quote_stops_with_nothing_written(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bug caught (hygiene, diag_stage1_hypothesis_tests.py:552): the
    artifact was written BEFORE the 205(d) STOP."""
    mod = _stubbed(monkeypatch, reproduced=False)
    out = tmp_path / "band_tables.json"
    with pytest.raises(SystemExit, match="STOP"):
        mod.main(out=out, record=False)
    assert not out.exists()


def test_a_reproducing_run_still_writes_its_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bug caught: a fix that moves the write out of the happy path too."""
    mod = _stubbed(monkeypatch, reproduced=True)
    out = tmp_path / "band_tables.json"
    mod.main(out=out, record=False)
    assert out.exists()
