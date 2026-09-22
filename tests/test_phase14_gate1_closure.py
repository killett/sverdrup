"""Gate-1 closure record tests (owner pins 264b, 269) — CI-local.

Pin 264(b) named what must be pinned: **14 contract lines; every cited node
present in the mirror with a digest; registered_but_not_yet_written empty;
read (i) trips on a fixture with a non-empty locked_tally.**

⛔ **PIN 269 CORRECTED THE THIRD OF THOSE, AND IT IS THE LESSON OF THIS FILE.**
Three tests here re-derived against the LIVE store and mirror, while the record
they guard states values **AT CLOSURE**. The first legitimate Stage-2 act — a
node registered before it is written, 263.10's ledger work, 2G's acceptance
touch — would have turned them red claiming the closure was broken, and the
only green path would have been regenerating a closed record: pin 197(a)'s
retroactive edit with a command attached. *A test that can only be made green
by falsifying the record it guards is worse than no test.*

So the two concerns are now separate:
- the RECORD is **frozen by digest** at the closure commit (269a), which
  catches hand-edits and regeneration alike;
- the LIVE reads are a **tripwire for pin 267** with a named expiry (269b) —
  they assert that nothing has opened SINCE closure;
- the live registered-but-unwritten assertion is **retired** to the record's
  addendum, with the commit it was read at (269c).

The other failure mode is unchanged: a read that always passes is not
evidence, it is decoration — so every read is exercised against a fixture
that must trip it, including the errored-grep case that once rendered a
reassuring "NO HITS" (269d).
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


def test_nothing_has_opened_since_stage1_closure() -> None:
    """TRIPWIRE for pin 267 — not a re-derivation of the closure.

    ⛔ THIS TEST HAS A NAMED EXPIRY. It asserts that the locked ledger and
    the c2 ledger still read what they read when Stage 1 closed, so the
    FIRST thing that opens after closure turns it red. That is its whole
    job: pin 267 says closing opens nothing, and this is what makes that
    checkable rather than stated.

    The authorised way for it to go red is **2G's acceptance touch**. When
    that lands, the owner RETIRES this test by numbered pin — it is not
    updated, not relaxed, and never made green by rewriting the closure
    record (pin 269a freezes that record by digest precisely so nobody
    reaches for `--write` here).

    Bug caught: a locked-instrument open or a c2 touch happening after
    closure with nothing noticing — the exact silence pin 262's reads
    exist to break, extended forward in time.
    """
    # What each read TRIPPING actually means (owner pin 273). Reporting them
    # all as "a ledger moved" is true of (i)/(ii) only, and would send a
    # reader looking for a touch when the finding is a mirror disagreement
    # or a newly-added code path.
    meaning = {
        "(i)": "the CEREMONY's ledger moved: a locked-instrument open since closure",
        "(ii)": "the c2 ledger moved: a c2 touch since closure",
        "(iii)": "the store and the mirror DISAGREE on the legacy list",
        "(iv)": (
            "a script now NAMES the ceremony's env: a touch PATH exists, "
            "which is not by itself a touch. Expected only as 2G's touch is "
            "built; the owner rules on it"
        ),
    }
    reads = _mod.closure_reads()
    assert [r["id"] for r in reads] == ["(i)", "(ii)", "(iii)", "(iv)"]
    tripped = [r["id"] for r in reads if r["trips"]]
    assert not tripped, (
        "CLOSURE TRIPWIRE — "
        + "; ".join(f"{rid} {meaning[rid]}" for rid in tripped)
        + ". The only authorised one is the 2G acceptance "
        "touch. If this is that touch, the owner retires this test by "
        "numbered pin; otherwise it is a violation — STOP."
    )
    for read in reads:
        assert read["trip_condition"].strip()
        assert read["value"].strip()


def test_the_tripwire_runs_the_mirror_check_in_process() -> None:
    """Read (iii)'s failable half, made part of the tripwire (269d).

    Bug caught: read (iii) as first built consulted only the MIRROR's own
    recorded digest — a tracked file that changes only on re-sync — so it
    could not see the store at all. Its real failable half was a hand-run
    `check` that no test invoked. Anything but PASS must fail here.
    """
    mirror = load_script("phase14_evidence_mirror")
    mirror.check()


def test_the_record_is_frozen_by_digest() -> None:
    """The DERIVED blocks are byte-frozen at 31e7569 (pin 269a).

    Bug caught — and this replaces a test that HAD the bug: comparing the
    record against freshly derived output asserts AT-CLOSURE values
    against NOW, so the first legitimate Stage-2 act turns it red and the
    only green path is regenerating a closed record (pin 197a's
    retroactive edit, made mechanical). A digest pinned at the closure
    commit catches hand-edits AND regeneration, and can never be made
    green by rewriting history.
    """
    on_disk = _mod.block_digests(_mod.RECORD.read_text())
    assert on_disk == _mod.FROZEN_BLOCK_SHA256
    assert set(on_disk) == {"reads", "contract"}
    for name, digest in on_disk.items():
        assert len(digest) == 64, name


def test_write_refuses_on_the_frozen_record() -> None:
    """`--write` cannot rewrite a frozen record (269a).

    Bug caught: the producer silently re-splicing live values into a
    closed record. Refusing is what makes the freeze real — a digest test
    that a one-line command can satisfy by changing the record instead of
    the world is not a freeze.
    """
    with pytest.raises(_mod.ClosureReadError, match="FROZEN"):
        _mod.main(write=True)


def test_a_record_without_the_markers_refuses_to_be_written(tmp_path: Path) -> None:
    """A record missing its DERIVED markers raises.

    Bug caught: the producer silently writing nothing (or appending) when
    the markers are renamed or lost in an edit, leaving stale derived
    tables in place with no signal at all.
    """
    with pytest.raises(_mod.ClosureReadError, match="markers"):
        _mod.splice("# a record with no markers\n", _mod.derived_blocks())


def test_read_iii_trips_when_the_store_differs_from_the_mirror(tmp_path: Path) -> None:
    """Read (iii) can see the STORE, not only the mirror's own digest.

    Bug caught (269d): as first built, read (iii) compared the mirror's
    recorded digest to a constant — both sides tracked files that move
    together on re-sync — so a store whose legacy tally had actually
    CHANGED would still read "passes". The store is the thing the pin
    cares about.
    """
    store = json.loads(_mod.STORE.read_text())
    store["c2_touch_tally"] = ["touch 4: a Stage-2 open nobody authorised"]
    moved = tmp_path / "store.json"
    moved.write_text(json.dumps(store))

    read = _mod.read_legacy_digest(store_path=moved)
    assert read["trips"] is True
    assert _mod.read_legacy_digest()["trips"] is False


def test_read_iv_trips_on_a_root_that_references_the_ceremony_env(
    tmp_path: Path,
) -> None:
    """Read (iv) finds a producer that could open a ceremony.

    Bug caught: the grep silently finding nothing because it ran in the
    wrong directory. A fixture root that DOES contain the env name must
    trip, or the read proves nothing about the real root either.
    """
    from sverdrup.validation.locked_tier import TOUCH_ENV

    rogue = tmp_path / "rogue.py"
    rogue.write_text(f'import os\n\nos.environ["{TOUCH_ENV}"] = "1"\n')
    read = _mod.read_env_grep(roots=(str(tmp_path),))
    assert read["trips"] is True
    assert "rogue.py" in read["value"]


def test_read_iv_raises_when_its_root_is_missing(tmp_path: Path) -> None:
    """An errored grep is not a clean grep (269d).

    Bug caught — the sharpest one in this file: rg exits 2 on a missing
    path, and the read as first built treated any non-zero exit as "NO
    HITS". A mistyped or moved root would have rendered the reassuring
    answer forever. Anything but exit 0/1 must raise.
    """
    with pytest.raises(_mod.ClosureReadError, match="rg"):
        _mod.read_env_grep(roots=(str(tmp_path / "does-not-exist"),))
