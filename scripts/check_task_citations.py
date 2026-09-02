"""Validate a document's task citations against the TRACKER (owner pin 138).

T11's verify step spot-checked its citations against `### Task N:` headings
in the plan prose. Tasks 13 and 22 exist only in the co-located
`.tasks.json` — both were created by owner ruling after the prose was
written — so the heading-only method reports two live tasks as phantoms.
A verification tool blind to a third of the recent tasks misleads whoever
trusts it next, which is the defect this script exists to remove.

The tracker is the source of truth for task existence. The plan headings
are still read, but only to REPORT drift (tracker-only ids), never to
refuse a citation.

Usage:
    pixi run python scripts/check_task_citations.py DOC [--tracker PATH]
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(add_completion=False)

DEFAULT_TRACKER = Path(
    "docs/superpowers/plans/2026-07-23-phase14-stage1-spatial-2017.md.tasks.json"
)

# T5, T5c, T5-something: a sub-label cites its task. The Stage-1 docs are
# full of T5b/T5c/T5d/T5e, and a bare word-boundary regex skips every one
# of them — validating a fraction of the citations it appears to.
_CITATION = re.compile(r"\bT(\d+)[a-z]?\b")


@dataclass(frozen=True)
class CitationCheck:
    """What a document cites, and whether the tracker knows all of it."""

    doc: Path
    cited: tuple[int, ...]
    unknown: tuple[int, ...]
    tracker_only: tuple[int, ...]
    tracker_ids: tuple[int, ...]

    @property
    def ok(self) -> bool:
        """True when every cited task exists in the tracker."""
        return not self.unknown


def _plan_heading_ids(plan: Path) -> set[int]:
    """Task ids that appear as `### Task N:` headings in the plan prose."""
    if not plan.exists():
        return set()
    return {
        int(m.group(1))
        for m in re.finditer(
            r"^### (?:\[[^\]]+\] )?Task (\d+):", plan.read_text(), re.M
        )
    }


def check(doc: Path, tracker: Path = DEFAULT_TRACKER) -> CitationCheck:
    """Resolve every task citation in ``doc`` against ``tracker``.

    Args:
        doc: The document whose `T<n>` citations are checked.
        tracker: The plan's co-located `.tasks.json` — the source of truth
            for which tasks exist.

    Returns:
        The citations found, any that no task carries, and the ids the
        tracker has but the plan prose does not (reported, not refused).

    Raises:
        FileNotFoundError: The document or the tracker is missing. An
            absent tracker REFUSES rather than returning an empty pass —
            the pin-110(b) shape, where a check quietly succeeds because
            the thing it checks against is not there.
    """
    if not doc.exists():
        raise FileNotFoundError(doc)
    if not tracker.exists():
        raise FileNotFoundError(tracker)

    data = json.loads(tracker.read_text())
    tracker_ids = {int(t["id"]) for t in data.get("tasks", [])}
    cited = sorted({int(m.group(1)) for m in _CITATION.finditer(doc.read_text())})
    headings = _plan_heading_ids(
        Path(data.get("planPath", "")) or tracker.with_suffix("")
    )

    return CitationCheck(
        doc=doc,
        cited=tuple(cited),
        unknown=tuple(i for i in cited if i not in tracker_ids),
        tracker_only=tuple(sorted(tracker_ids - headings)) if headings else (),
        tracker_ids=tuple(sorted(tracker_ids)),
    )


@app.command()
def main(
    doc: Annotated[Path, typer.Argument(help="Document whose task citations to check")],
    tracker: Annotated[
        Path, typer.Option(help="The plan's co-located .tasks.json")
    ] = DEFAULT_TRACKER,
) -> None:
    """Check DOC's task citations against the tracker; exit 1 on any unknown."""
    result = check(doc, tracker)
    typer.echo(
        f"{result.doc}: {len(result.cited)} task citations "
        f"({', '.join('T' + str(i) for i in result.cited)})"
    )
    typer.echo(f"tracker carries {len(result.tracker_ids)} tasks")
    if result.tracker_only:
        typer.echo(
            "INFO tracker-only (no `### Task N:` heading in the plan prose — the pin-138 "
            "blind spot, reported not refused): "
            + ", ".join("T" + str(i) for i in result.tracker_only)
        )
    if result.unknown:
        typer.echo(
            "FAIL cited but carried by NO task in the tracker: "
            + ", ".join("T" + str(i) for i in result.unknown)
        )
        raise typer.Exit(1)
    typer.echo("PASS every cited task exists in the tracker")


if __name__ == "__main__":
    app()
