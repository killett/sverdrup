"""The write-once guard for evidence-store nodes (hygiene item 44).

About twenty runners REPLACED their node on a rerun with no guard — the
evidence mirror could only detect it afterwards, and never for a node it
does not mirror. Expected values are hand-built stores.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sverdrup.validation.write_once import (
    NodeAlreadyRecordedError,
    refuse_if_recorded,
)


def _store(tmp_path: Path) -> Path:
    path = tmp_path / "store.json"
    path.write_text(
        json.dumps({"phase14": {"stage1": {"seam_rows": [], "probe": {"x": 1}}}})
    )
    return path


def test_an_existing_node_is_refused_naming_node_and_store(tmp_path: Path) -> None:
    """Bug caught: a guard that misses a recorded node (even an EMPTY list —
    an empty value is still a witnessed record)."""
    store = _store(tmp_path)
    with pytest.raises(NodeAlreadyRecordedError) as exc:
        refuse_if_recorded(store, "phase14.stage1.seam_rows")
    assert "phase14.stage1.seam_rows" in str(exc.value)
    assert str(store) in str(exc.value)


@pytest.mark.parametrize(
    "dotted",
    ["phase14.stage1.seam_pair", "phase14.stage0.golden_tile", "nothing.here"],
)
def test_an_unrecorded_node_passes(tmp_path: Path, dotted: str) -> None:
    """Bug caught: over-broad matching (a sibling, or a present PARENT, read
    as the node itself) that would block every first run."""
    refuse_if_recorded(_store(tmp_path), dotted)


def test_an_absent_store_passes(tmp_path: Path) -> None:
    """Bug caught: a guard that crashes on a fresh box instead of allowing."""
    refuse_if_recorded(tmp_path / "absent.json", "phase14.stage1.probe")


def test_several_paths_name_exactly_those_recorded(tmp_path: Path) -> None:
    """Bug caught: reporting the first path asked about rather than the one
    actually present — the operator would move the wrong node aside."""
    with pytest.raises(NodeAlreadyRecordedError) as exc:
        refuse_if_recorded(
            _store(tmp_path), "phase14.stage1.seam_pair", "phase14.stage1.probe"
        )
    assert "phase14.stage1.probe" in str(exc.value)
    assert "seam_pair" not in str(exc.value)
