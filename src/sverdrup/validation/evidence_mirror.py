"""Provenance mirror of the gitignored evidence store (owner pin 56).

The Stage-1 evidence store is gitignored, so every write-once surface it
carries — gate-5 constants, the seal chain, the locked-instrument tally,
correction and withdrawal records, the settling measurement — has existed
on one machine and has never been externally visible. Owner pin 56 states
the defect precisely:

> The issue is WITNESS, not backup. Write-once enforced by a file only
> its author can see is a convention; nothing can demonstrate it was not
> rewritten. That is the one guarantee this program cannot hold on trust.

This module holds the arithmetic behind the mirror. Two properties make
it a witness rather than a copy:

1. **A canonical digest** that changes if and only if the content
   changes — stable across dict key order, sensitive to values and to
   LIST ORDER (the settling ratios are stored in partition order).
2. **Change detection that separates additions from modifications.**
   Appending a new record is ordinary. Rewriting one already mirrored is
   a STOP, because that is exactly the event write-once forbids and the
   event a private file cannot rule out.

The mirror's tamper-evidence ultimately rests on git: once pushed, the
digests are timestamped in history that the author cannot silently
rewrite. This module only makes drift detectable; the push makes it
witnessed.

**NOT VERDICT-BEARING.** Nothing here adjudicates anything — it records.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

__all__ = [
    "detect_changes",
    "detect_index_regressions",
    "digest_node",
    "select_nodes",
]


def digest_node(node: Any) -> str:  # noqa: ANN401 - mirrors arbitrary JSON
    """SHA-256 over a canonical JSON serialization of one node.

    Canonical means: dict keys sorted (so the digest does not depend on
    how the mapping was built), compact separators, and ``ensure_ascii``
    off so the bytes are the document's own text. Lists are NOT sorted —
    their order is content.

    Args:
        node: Any JSON-serializable value.

    Returns:
        Hex SHA-256 of the canonical encoding.

    Raises:
        TypeError: If the node is not JSON-serializable — a silent
            fallback would digest a repr and witness nothing.
    """
    encoded = json.dumps(
        node, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def select_nodes(store: dict[str, Any], paths: list[str]) -> dict[str, Any]:
    """Pull the named dotted paths out of the evidence store.

    Args:
        store: The parsed evidence store.
        paths: Dotted paths, e.g. ``phase14.stage1.gate5``.

    Returns:
        ``path -> value``, keyed by the dotted path itself so the mirror
        reads as a flat list of named records.

    Raises:
        KeyError: If a path does not resolve. This is deliberately fatal:
            silently skipping a node yields a mirror that looks healthy
            while the record it was meant to witness is simply absent.
    """
    picked: dict[str, Any] = {}
    for path in paths:
        cursor: Any = store
        for part in path.split("."):
            if not isinstance(cursor, dict) or part not in cursor:
                raise KeyError(f"evidence path does not resolve: {path}")
            cursor = cursor[part]
        picked[path] = cursor
    return picked


def detect_changes(existing: dict[str, Any], incoming: dict[str, Any]) -> list[str]:
    """Names of already-mirrored nodes whose content has CHANGED.

    A node present in ``incoming`` but absent from ``existing`` is an
    ADDITION, not a change, and is not reported: appending the next
    measurement or the next correction is ordinary work. A node whose
    content differs from what was already witnessed is the event
    write-once forbids.

    Args:
        existing: Previously mirrored ``name -> value``.
        incoming: Freshly extracted ``name -> value``.

    Returns:
        Sorted names of nodes that exist in both and differ.
    """
    return sorted(
        name
        for name, value in incoming.items()
        if name in existing and digest_node(existing[name]) != digest_node(value)
    )


def detect_index_regressions(
    existing: dict[str, list[Any]], incoming: dict[str, list[Any]]
) -> list[str]:
    """Nodes whose amendment-index entries were REMOVED or ALTERED.

    Owner pin 64: a witnessed node whose claim is later amended must stay
    reachable FROM that node, or the store accumulates entries that are
    individually accurate and collectively stale. The index carries those
    forward pointers — and is itself append-only, for the same reason the
    nodes are.

    Appending a further amendment to a node is ordinary. Dropping a
    recorded pointer, or rewriting one in place, is a regression: it would
    leave a witnessed node looking current while the record that amends it
    became unreachable.

    Args:
        existing: Previously recorded ``node -> [entry, ...]``.
        incoming: Freshly authored ``node -> [entry, ...]``.

    Returns:
        Sorted node names whose recorded entries are not a PREFIX of the
        incoming ones.
    """
    regressed: list[str] = []
    for node, prior in existing.items():
        now = incoming.get(node, [])
        if len(now) < len(prior) or any(
            digest_node(a) != digest_node(b)
            for a, b in zip(prior, now[: len(prior)], strict=False)
        ):
            regressed.append(node)
    return sorted(regressed)
