"""Write-once guard for evidence-store nodes (hygiene item 44).

The shared evidence store is single-copy and gitignored. About twenty
runners REPLACED their node on a rerun with no guard: a seam-pair rerun
erased the pin-45(b) withholding marks, a default settling run destroyed
owner-added blocks no code produces, a tier-2 probe rerun replaced the
measurement a pending owner decision derives from. The evidence mirror
detects such a rewrite only AFTERWARDS, and never for a node it does not
mirror.

A runner that has produced its record calls :func:`refuse_if_recorded`
BEFORE any work: re-measuring a recorded node is an owner decision, carried
out by moving the node aside deliberately (and superseding it in the
mirror), never by a rerun.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

__all__ = ["NodeAlreadyRecordedError", "refuse_if_recorded"]


class NodeAlreadyRecordedError(RuntimeError):
    """A runner was about to replace a node the store already holds."""


def _resolves(store: Any, dotted: str) -> bool:  # noqa: ANN401 - parsed JSON
    cursor = store
    for part in dotted.split("."):
        if not isinstance(cursor, dict) or part not in cursor:
            return False
        cursor = cursor[part]
    return True


def refuse_if_recorded(evidence_path: Path, *dotted: str) -> None:
    """Refuse if any of the dotted paths is already recorded in the store.

    Args:
        evidence_path: The evidence store (absent = nothing recorded yet).
        *dotted: Dotted node paths, e.g. ``phase14.stage1.seam_rows``.

    Raises:
        NodeAlreadyRecordedError: Naming every path already present.
    """
    if not evidence_path.exists():
        return
    store = json.loads(evidence_path.read_text())
    present = [path for path in dotted if _resolves(store, path)]
    if present:
        raise NodeAlreadyRecordedError(
            f"REFUSED: {evidence_path} already records {present} — a rerun "
            "would REPLACE the witnessed record (hygiene item 44). Re-measuring "
            "is an owner decision: move the node aside deliberately (and "
            "supersede it in the evidence mirror) before re-running."
        )
