"""Owner pin 138 — the task-citation check reads the TRACKER, not headings.

T11's verify step spot-checked citations against `### Task N:` headings in
the plan prose. T13 and T22 exist only in the co-located `.tasks.json`
(both created by owner ruling after the prose was written), so a third of
the recent tasks read as phantoms to the method that was supposed to
validate them.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.helpers import load_script

_mod = load_script("check_task_citations")


def _tracker(
    tmp_path: Path, ids: list[int], *, headings: list[int] | None = None
) -> Path:
    """A plan + tracker pair where the two need not agree."""
    plan = tmp_path / "plan.md"
    plan.write_text(
        "\n".join(
            f"### Task {i}: something"
            for i in (headings if headings is not None else ids)
        )
        + "\n"
    )
    tracker = tmp_path / "plan.md.tasks.json"
    tracker.write_text(
        json.dumps(
            {
                "planPath": str(plan),
                "tasks": [
                    {"id": i, "subject": f"Task {i}", "status": "pending"} for i in ids
                ],
            }
        )
    )
    return tracker


def test_tracker_only_tasks_are_NOT_phantoms(tmp_path: Path) -> None:
    """A citation of a tracker-only task passes.

    Bug caught: pin 138 itself — the heading-only method reporting T13 and
    T22 as unknown, which is a verification tool telling the next reader
    that two live tasks do not exist.
    """
    tracker = _tracker(tmp_path, ids=[0, 9, 13, 22], headings=[0, 9])
    doc = tmp_path / "coverage.md"
    doc.write_text(
        "T13 landed the withholding; T22 was the Tier-2 gate; T9 assembles.\n"
    )

    result = _mod.check(doc, tracker)

    assert result.unknown == ()
    assert result.ok
    assert set(result.cited) == {0, 9, 13, 22} - {0}
    assert set(result.tracker_only) == {13, 22}, (
        "tracker-only ids are reported as INFO so the plan/tracker drift stays visible"
    )


def test_a_citation_with_no_task_FAILS_by_name(tmp_path: Path) -> None:
    """An invented task number is named, not silently accepted.

    Bug caught: a check that only ever passes — the coverage tables cite
    tasks as their evidence, so an unresolvable citation must be loud.
    """
    tracker = _tracker(tmp_path, ids=[0, 1])
    doc = tmp_path / "coverage.md"
    doc.write_text("T0 and T1 are real; T99 is not.\n")

    result = _mod.check(doc, tracker)

    assert result.unknown == (99,)
    assert not result.ok


def test_sub_labelled_citations_resolve_to_their_task(tmp_path: Path) -> None:
    """T5c cites task 5, not a task called 5c.

    Bug caught: a word-boundary regex that skips every sub-label — the
    Stage-1 docs are full of T5b/T5c/T5d/T5e, so missing them means the
    check silently validates a fraction of the citations it appears to.
    """
    tracker = _tracker(tmp_path, ids=[5])
    doc = tmp_path / "coverage.md"
    doc.write_text("T5c wired GroundTrack; T5d added the per-tile extras.\n")

    result = _mod.check(doc, tracker)

    assert result.cited == (5,)
    assert result.ok


def test_missing_tracker_refuses_rather_than_passing(tmp_path: Path) -> None:
    """No tracker is a refusal, never an empty pass.

    Bug caught: the pin-110(b) shape — a check that quietly succeeds when
    the thing it checks against is absent.
    """
    doc = tmp_path / "coverage.md"
    doc.write_text("T5\n")
    with pytest.raises(FileNotFoundError):
        _mod.check(doc, tmp_path / "nope.tasks.json")
