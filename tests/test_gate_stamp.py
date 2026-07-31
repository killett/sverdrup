"""Tree-stamp gate for the suite/commit sequence (owner pin 83).

Pre-commit REWRITES files, so the standing order suite -> pre-commit ->
commit produced gate evidence from a pre-format tree, structurally and
every time. Pin 83 reorders it to format -> stamp -> suite -> verify ->
commit, and requires the check be mechanical:

> record the tree hash at suite start and assert it is unchanged at
> commit. A mismatch names the changed paths and refuses, the way the
> mirror gates do.

These tests are about the two properties that make the stamp a gate
rather than a note: a digest that moves iff the bytes move, and a diff
that names what changed including files that appeared or vanished.
"""

from __future__ import annotations

from pathlib import Path

from sverdrup.validation.gate_stamp import (
    changed_paths,
    file_digests,
    stamp_blockers,
)


def _write(root: Path, name: str, body: str) -> None:
    """Write one file under the root.

    Args:
        root: Directory to write into.
        name: Relative file name.
        body: Text content.
    """
    p = root / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)


def test_digest_moves_when_bytes_move(tmp_path: Path) -> None:
    """A changed file changes its digest.

    Catches a stamp computed over file NAMES or mtimes — it would sail
    through the exact event pin 83 exists to catch, a formatter rewriting
    a file after the suite has run.
    """
    _write(tmp_path, "a.py", "x = 1\n")
    before = file_digests(tmp_path, ["a.py"])
    _write(tmp_path, "a.py", "x = 2\n")
    after = file_digests(tmp_path, ["a.py"])

    assert before["a.py"] != after["a.py"]


def test_digest_is_stable_for_identical_content(tmp_path: Path) -> None:
    """Unchanged bytes digest identically on a later call.

    Catches a nondeterministic stamp (mtime, path ordering, a random
    salt), which would refuse every commit and be disabled within a day —
    the failure mode that kills gates.
    """
    _write(tmp_path, "a.py", "x = 1\n")

    assert file_digests(tmp_path, ["a.py"]) == file_digests(tmp_path, ["a.py"])


def test_same_length_rewrite_is_detected(tmp_path: Path) -> None:
    """Equal-length content changes are caught, not just size changes.

    Catches a size-based shortcut. This is not hypothetical: a formatter
    swapping quote style or rebalancing whitespace can leave the byte
    count identical.
    """
    _write(tmp_path, "a.py", "x = 'ab'\n")
    before = file_digests(tmp_path, ["a.py"])
    _write(tmp_path, "a.py", 'x = "ab"\n')

    assert file_digests(tmp_path, ["a.py"]) != before


def test_changed_paths_names_exactly_the_modified_files(tmp_path: Path) -> None:
    """The diff names what moved, and is empty when nothing did.

    Catches an always-empty result, which would make the gate vacuous —
    it would report PASS across precisely the rewrite it was added to
    refuse.
    """
    before = {"a.py": "d1", "b.py": "d2", "c.py": "d3"}
    after = {"a.py": "d1", "b.py": "CHANGED", "c.py": "d3"}

    assert changed_paths(before, after) == ["b.py"]
    assert changed_paths(before, before) == []


def test_added_and_removed_files_are_reported(tmp_path: Path) -> None:
    """Appearing and vanishing files count as changes.

    Catches a diff over common keys only. A rewriting hook can CREATE a
    file mid-run — and a file that vanished between the suite and the
    commit is exactly as disqualifying as one that was edited.
    """
    before = {"a.py": "d1", "gone.py": "d2"}
    after = {"a.py": "d1", "new.py": "d3"}

    assert changed_paths(before, after) == ["gone.py", "new.py"]


# ---- stamp_blockers: a green verify must mean a suite FINISHED -------------


def test_verify_refuses_when_no_suite_completion_is_recorded() -> None:
    """A stamp with no recorded completion cannot license a commit.

    This is the hole that was hit live: `verify` returned green while the
    suite was still at 5%, because the stamp only ever recorded when the
    suite STARTED. Catches a gate that looks authoritative next to a run
    that never finished.
    """
    stamp = {"digests": {}, "stamped_utc": "2026-07-30T00:00:00+00:00"}

    blockers = stamp_blockers(stamp)

    assert len(blockers) == 1
    assert "no completed suite" in blockers[0]


def test_verify_refuses_a_recorded_suite_failure() -> None:
    """A stamp recording a FAILED suite refuses too.

    Catches committing on a red run whose tree merely happens to be
    unchanged — tree-unchanged and suite-passed are different claims and
    the gate must require both.
    """
    stamp = {"digests": {}, "suite": {"completed": True, "exit_code": 1}}

    blockers = stamp_blockers(stamp)

    assert len(blockers) == 1
    assert "exit 1" in blockers[0]


def test_verify_accepts_a_clean_completion() -> None:
    """A recorded clean completion produces no blockers.

    Catches a rule so strict nothing can satisfy it — the failure mode
    that gets gates disabled rather than fixed.
    """
    stamp = {"digests": {}, "suite": {"completed": True, "exit_code": 0}}

    assert stamp_blockers(stamp) == []
