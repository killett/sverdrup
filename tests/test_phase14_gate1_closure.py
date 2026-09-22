"""Gate-1 closure record tests (owner pin 264b) — CI-local.

Pin 264(b) names exactly what must be pinned: **14 contract lines; every
cited node present in the mirror with a digest; registered_but_not_yet_written
empty; read (i) trips on a fixture with a non-empty locked_tally.**

⛔ The failure mode these guard is **a closure record that looks complete and
is not**. Stage 2 reads this record INSTEAD of re-deriving Stage 1, so a
dropped contract line, a citation to a node nobody witnessed, or a read that
cannot fail would all be invisible at exactly the moment they matter. The
last one is the sharpest: a read that always passes is not evidence, it is
decoration — so read (i) is exercised against a store that should trip it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.helpers import load_script

_mod = load_script("phase14_gate1_closure")


def _mirror() -> dict[str, Any]:
    return json.loads(_mod.MIRROR.read_text())


def test_there_are_exactly_fourteen_contract_lines_c01_to_c14() -> None:
    """C-01…C-14, no gaps and no duplicates.

    Bug caught: a contract line quietly dropped from the closure record.
    The C1→2 sentence is segmented into exactly 14 normative parts, so a
    record with 13 hands Stage 2 a contract with a hole in it and nothing
    else in the pipeline would notice.
    """
    ids = [line["id"] for line in _mod.CONTRACT_LINES]
    assert ids == [f"C-{n:02d}" for n in range(1, 15)]
    assert len(set(ids)) == 14


def test_every_cited_node_is_in_the_mirror_with_a_full_digest() -> None:
    """Each line cites witnessed evidence, not prose.

    Bug caught: the record citing a node that is not in the mirror — a
    citation that looks like provenance and carries none. `contract_rows`
    resolves every carrier against the mirror, so this fails loudly rather
    than rendering an empty cell.
    """
    rows = _mod.contract_rows()
    assert len(rows) == 14
    nodes = _mirror()["nodes"]
    for row in rows:
        assert row["citations"], row["id"]
        for cite in row["citations"]:
            assert cite["node"] in nodes, (row["id"], cite["node"])
            full = nodes[cite["node"]]["digest_sha256"]
            assert len(full) == 64
            assert full.startswith(cite["digest"])
            assert cite["value"], (row["id"], cite["field"])


def test_a_missing_carrier_raises_instead_of_rendering_prose(tmp_path: Path) -> None:
    """A carrier that has gone missing is a STOP, not a blank cell.

    Bug caught — pin 264(b)'s named failure: a line whose evidence moved
    still rendering as discharged. Both halves are exercised: a node that
    has left the mirror, and a node still present whose cited FIELD is
    gone. Silent degradation here would be worse than a crash.
    """
    mirror = _mirror()
    gone = tmp_path / "no-node.json"
    del mirror["nodes"]["phase14.stage1.refresh_election"]
    gone.write_text(json.dumps(mirror))
    with pytest.raises(_mod.ClosureReadError, match="refresh_election"):
        _mod.contract_rows(mirror_path=gone)

    mirror2 = _mirror()
    mirror2["nodes"]["phase14.stage1.refresh_election"]["value"].pop("outcome")
    moved = tmp_path / "no-field.json"
    moved.write_text(json.dumps(mirror2))
    with pytest.raises(_mod.ClosureReadError, match="outcome"):
        _mod.contract_rows(mirror_path=moved)


def test_no_node_is_registered_but_still_unwritten() -> None:
    """The mirror has no PENDING registration at closure.

    Bug caught: closing the gate with a pre-registered node still empty —
    which is precisely the state `refresh_election` sat in from pin 136
    until pin 259(b). A gate cannot close over a witness that was promised
    and never written.
    """
    pending = _mirror()["registered_but_not_yet_written"]
    assert pending["paths"] == [], pending["paths"]


def test_read_i_trips_on_a_non_empty_ceremony_ledger(tmp_path: Path) -> None:
    """Read (i) is failable — the whole point of 262(a).

    Bug caught: a read that passes no matter what the store says. If read
    (i) could not trip, §3 of the record would assert "zero locked opens"
    on evidence that never looked. The fixture writes one ceremony entry
    at the ceremony's OWN key and the read must report `trips`.
    """
    from sverdrup.validation.locked_tier import _TALLY_KEYS

    store = tmp_path / "ev.json"
    doc: dict[str, Any] = {}
    node: Any = doc
    for key in _TALLY_KEYS[:-1]:
        node = node.setdefault(key, {})
    node[_TALLY_KEYS[-1]] = {"prod": {"2017": 1}}
    store.write_text(json.dumps(doc))

    read = _mod.read_locked_tally(store_path=store)
    assert read["trips"] is True
    assert "2017" in read["value"]

    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps({"phase14": {}}))
    assert _mod.read_locked_tally(store_path=empty)["trips"] is False


def test_read_ii_trips_when_the_c2_tally_moves(tmp_path: Path) -> None:
    """Read (ii) is failable too.

    Bug caught: a c2 touch spent during Stage 1 and the record still
    reporting "tally untouched". Pin 255(c) claims no touch was spent;
    this is the read that could contradict it.
    """
    store = tmp_path / "ev.json"
    store.write_text(
        json.dumps(
            {"phase13": {"miost": {"c2_acceptance": {"c2_touch_tally": {"miost6": 2}}}}}
        )
    )
    assert _mod.read_c2_tally(store_path=store)["trips"] is True


def test_all_four_reads_pass_at_closure_and_each_names_its_trip_condition() -> None:
    """The reads as taken at closure, on the real store and mirror.

    Bug caught: the record announcing closure while a read trips. Pin
    262(b) makes a tripped read fatal to the closure itself, so this is
    the assertion the whole ruling turns on — and each read must also
    carry the condition that would have tripped it, or the record states
    a value without stating what it rules out.
    """
    reads = _mod.closure_reads()
    assert [r["id"] for r in reads] == ["(i)", "(ii)", "(iii)", "(iv)"]
    for read in reads:
        assert read["trips"] is False, read
        assert read["trip_condition"].strip()
        assert read["value"].strip()


def test_the_record_on_disk_is_what_the_producer_builds() -> None:
    """The derived blocks are never hand-pasted (264b).

    Bug caught: someone editing the closure record's tables by hand, so
    the record and the mirror disagree while the record still looks
    authoritative. Splicing the freshly built blocks into the file on
    disk must be a no-op, byte for byte.
    """
    current = _mod.RECORD.read_text()
    assert _mod.splice(current, _mod.derived_blocks()) == current


def test_a_record_without_the_markers_refuses_to_be_written(tmp_path: Path) -> None:
    """A record missing its DERIVED markers raises.

    Bug caught: the producer silently writing nothing (or appending) when
    the markers are renamed or lost in an edit, leaving stale derived
    tables in place with no signal at all.
    """
    with pytest.raises(_mod.ClosureReadError, match="markers"):
        _mod.splice("# a record with no markers\n", _mod.derived_blocks())
