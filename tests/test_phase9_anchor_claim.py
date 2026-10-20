"""Hygiene P2-#17: the G_pre anchor's regression guard says what it checks.

``phase9_g_pre_anchor`` step 2 compares the two field artifacts as PARSED
JSON (leaf equality) but its comment and refusal claimed a "byte-identical"
check. The check is kept (it is the anchor writer's recorded semantics);
the claim is corrected.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.helpers import load_script


def test_the_regression_refusal_names_the_comparison_it_makes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bug caught: a refusal claiming BYTE identity for a parsed-JSON
    comparison — a reader would trust it to catch formatting/ordering drift
    it cannot see. Paths point at temp files; nothing real is read/written."""
    mod = load_script("phase9_g_pre_anchor")
    results = tmp_path / "results.json"
    results.write_text(json.dumps({"phase9": {"miost": {"fit_run": {}}}}))
    (tmp_path / "phase8_field.json").write_text(json.dumps({"a": 1}))
    field = tmp_path / "phase9_field_miost.json"
    field.write_text(json.dumps({"a": 2}))
    monkeypatch.setattr(mod, "_RESULTS", results)
    monkeypatch.setattr(mod, "_FIELD_ARTIFACT", field)
    monkeypatch.setattr(mod, "_DATA_ROOT", tmp_path)
    with pytest.raises(RuntimeError) as info:
        mod.main()
    assert "byte-identical" not in str(info.value)
    assert "parsed-JSON" in str(info.value)
