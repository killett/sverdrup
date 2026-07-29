"""Tree stamp for the gate sequence (owner pin 83).

Pre-commit REWRITES files. Under the standing order
``suite -> pre-commit -> commit`` the gate evidence therefore came from a
pre-format tree structurally and every time — not occasionally, and not
through inattention. Pin 83 reorders it to

    format -> stamp -> suite -> verify -> commit

and requires the check be mechanical rather than remembered: record the
tree hash when the suite starts and assert it is unchanged at commit,
naming the changed paths on a mismatch.

This module is the arithmetic. ``scripts/phase14_gate_suite.py`` is the
sequence.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path

__all__ = ["changed_paths", "file_digests"]


def file_digests(root: Path, paths: Iterable[str]) -> dict[str, str]:
    """SHA-256 per file, keyed by path relative to ``root``.

    Content only: no mtime, no size shortcut, no path salt. A formatter
    that rewrites a file to the SAME length still moves its digest, which
    is the case that matters — rebalanced whitespace and swapped quote
    styles both preserve byte count.

    Args:
        root: Directory the paths are relative to.
        paths: Relative file paths. Missing files are skipped, so a file
            that vanishes shows up as a removal in :func:`changed_paths`
            rather than as an exception here.

    Returns:
        ``relative path -> hex SHA-256``.
    """
    out: dict[str, str] = {}
    for rel in paths:
        f = root / rel
        if not f.is_file():
            continue
        h = hashlib.sha256()
        with f.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        out[rel] = h.hexdigest()
    return out


def changed_paths(before: dict[str, str], after: dict[str, str]) -> list[str]:
    """Paths that were modified, added or removed between two stamps.

    Additions and removals count. A rewriting hook can CREATE a file
    mid-run, and a file that vanished between the suite and the commit
    disqualifies the evidence exactly as much as one that was edited.

    Args:
        before: Stamp taken when the suite started.
        after: Stamp taken at commit time.

    Returns:
        Sorted paths that differ.
    """
    return sorted(
        {p for p in before.keys() | after.keys() if before.get(p) != after.get(p)}
    )
