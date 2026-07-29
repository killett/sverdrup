"""Provenance mirror of the gitignored evidence store (owner pin 56).

Pins ``sverdrup.validation.evidence_mirror``. Pin 56(a) states the problem
exactly: write-once enforced by a file only its author can see is a
convention, and nothing can demonstrate it was not rewritten. The mirror
puts the provenance-bearing subset under version control so the claim is
externally witnessed instead of trusted.

The tests below are about the two properties that make it a WITNESS
rather than a copy: a canonical digest that changes iff the content
changes, and a change detector that separates additions (fine) from
modifications of already-recorded nodes (a STOP).

Expected values are hand-constructed — key-order pairs, a single edited
float, a reversed list — never taken from the implementation.
"""

from __future__ import annotations

from typing import Any

import pytest

from sverdrup.validation.evidence_mirror import (
    detect_changes,
    detect_index_regressions,
    digest_node,
    select_nodes,
)

# ---- digest_node ---------------------------------------------------------


def test_digest_is_stable_across_dict_key_order() -> None:
    """The same mapping digests identically however it was built.

    Catches a digest taken over a non-canonical serialization: Python
    preserves insertion order, so a re-sync that happened to build the
    dict differently would report every node as tampered with, and the
    append-only gate would cry wolf until someone disabled it.
    """
    a = {"alpha": 1, "beta": {"x": [1, 2], "y": "s"}}
    b = {"beta": {"y": "s", "x": [1, 2]}, "alpha": 1}

    assert digest_node(a) == digest_node(b)


def test_digest_changes_when_a_nested_value_changes() -> None:
    """A single edited float changes the digest.

    Catches a digest computed over structure or keys alone — the failure
    that would let a recorded verdict or measurement be rewritten in
    place while the mirror still reported a match.

    The edit is one ULP-scale but REPRESENTABLE change to the recorded
    `pair`/sigma ratio. It has to be representable: ``1.1044354829041465``
    and ``1.1044354829041466`` are the SAME binary64, so a digest cannot
    and should not distinguish them — the mirror witnesses the stored
    value, not the decimal someone typed.
    """
    before = {"rows": [{"route": "pair", "ratio": 1.1044354829041465}]}
    after = {"rows": [{"route": "pair", "ratio": 1.1044354829041469}]}

    assert before != after  # the edit is a real change in binary64
    assert digest_node(before) != digest_node(after)


def test_digest_changes_when_a_list_is_reordered() -> None:
    """List ORDER is content, unlike dict key order.

    Catches canonicalization that sorts lists: the settling measurement
    stores 200 ratios per split size in partition order, and a mirror
    that digested them order-insensitively could not witness a reordered
    or permuted array.
    """
    forward = {"ratios": [0.991, 0.997, 1.004]}
    reversed_ = {"ratios": [1.004, 0.997, 0.991]}

    assert digest_node(forward) != digest_node(reversed_)


# ---- select_nodes --------------------------------------------------------


def test_select_nodes_pulls_dotted_paths() -> None:
    """Dotted paths address nested nodes and keep their values intact.

    Catches a traversal that returns the parent, the wrong branch, or a
    shallow copy of the top level — any of which would mirror something
    other than what was named.
    """
    store = {
        "phase14": {"stage1": {"gate5": {"mu": 0.5}, "probe": {"skip": True}}},
        "c2_touch_tally": ["touch 1"],
    }

    picked = select_nodes(store, ["phase14.stage1.gate5", "c2_touch_tally"])

    assert picked == {
        "phase14.stage1.gate5": {"mu": 0.5},
        "c2_touch_tally": ["touch 1"],
    }


def test_select_nodes_refuses_a_missing_path() -> None:
    """A path that does not resolve is an error, naming the path.

    Catches the worst failure mode this component has: silently skipping
    a node, which produces a mirror that looks healthy while the record
    it was supposed to witness is simply absent.
    """
    store: dict[str, Any] = {"phase14": {"stage1": {"gate5": {}}}}

    with pytest.raises(KeyError, match="phase14.stage1.seam_rows"):
        select_nodes(store, ["phase14.stage1.seam_rows"])


# ---- detect_changes ------------------------------------------------------


def test_detect_changes_names_only_the_modified_nodes() -> None:
    """Exactly the nodes whose content changed, and nothing else.

    Catches an implementation that always returns an empty list, which
    would make the append-only gate vacuous — the mirror would accept a
    rewritten verdict without comment, which is the whole failure pin 56
    exists to close.
    """
    existing = {"a": {"v": 1}, "b": {"v": 2}, "c": {"v": 3}}
    incoming = {"a": {"v": 1}, "b": {"v": 99}, "c": {"v": 3}}

    assert detect_changes(existing, incoming) == ["b"]


def test_detect_changes_treats_a_new_node_as_an_addition() -> None:
    """Appending a node is not a modification.

    Catches conflating "absent from the mirror" with "changed", which
    would make every genuinely new record — the next measurement, the
    next correction — trip the gate and force a supersede that nothing
    was superseded by.
    """
    existing = {"a": {"v": 1}}
    incoming = {"a": {"v": 1}, "brand_new": {"v": 2}}

    assert detect_changes(existing, incoming) == []


# ---- amendment index (owner pin 64) --------------------------------------


def test_index_addition_to_an_existing_node_is_allowed() -> None:
    """A second amendment appends beside the first.

    Catches an index so rigid that recording a later amendment to an
    already-amended node is impossible — the store would then go stale in
    exactly the way pin 64 is written to prevent.
    """
    existing = {"n": [{"amended_by": "a", "what": "first"}]}
    incoming = {
        "n": [
            {"amended_by": "a", "what": "first"},
            {"amended_by": "b", "what": "second"},
        ]
    }

    assert detect_index_regressions(existing, incoming) == []


def test_index_entry_removal_is_a_regression() -> None:
    """Dropping a recorded pointer is a regression, naming the node.

    Catches the failure that hollows the index out: a forward pointer
    silently removed leaves a witnessed node looking current while the
    record that amends it is unreachable from it.
    """
    existing = {"n": [{"amended_by": "a", "what": "first"}]}
    incoming: dict[str, Any] = {"n": []}

    assert detect_index_regressions(existing, incoming) == ["n"]


def test_index_entry_alteration_is_a_regression() -> None:
    """Rewriting an entry under an unchanged key is a regression.

    Catches history being edited in place — the index is append-only for
    the same reason the nodes are, and an entry whose text can change
    witnesses nothing.
    """
    existing = {"n": [{"amended_by": "a", "what": "first"}]}
    incoming = {"n": [{"amended_by": "a", "what": "rewritten"}]}

    assert detect_index_regressions(existing, incoming) == ["n"]


def test_index_new_node_key_is_allowed() -> None:
    """The first amendment of a node is an addition, not a regression.

    Catches conflating "not previously in the index" with tampering,
    which would block every first forward pointer ever recorded.
    """
    existing = {"n": [{"amended_by": "a", "what": "first"}]}
    incoming = {
        "n": [{"amended_by": "a", "what": "first"}],
        "brand_new": [{"amended_by": "c", "what": "x"}],
    }

    assert detect_index_regressions(existing, incoming) == []
