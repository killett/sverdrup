"""The absence check over the RENDERED Gate-1 pack (review pin 17, owner pin 208a).

The transfer-reading section of the pack is ASSEMBLED from recorded row
fields by ``phase14_stage1_run.py render-transfer-readings`` — the assembler
has no free-text parameter — and is wrapped in two markers. While the
attribution readout has not ruled, that section carries numbers, caveats
and the ruled structure, and NO cross-lineage interpretation. This script
scans exactly that section for the words that would mean one slipped in,
and its output is captured into the pack's close evidence.

Scope is the section, not the file: the owner's own rulings are quoted
elsewhere in the pack in their own words (pin 196(c) says "consistent with
a reference offset ... consistent, not established"), and those quotations
sit outside the markers by design.

Usage::

    pixi run python scripts/phase14_pack_absence_check.py docs/superpowers/<pack>.md

Exit codes: 0 PASS, 1 FAIL (a banned word inside the section), 2 the
section could not be found (markers missing) — which must never read as
a pass over nothing.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated

import typer

BEGIN_MARKER = "<!-- TRANSFER-READINGS: BEGIN -->"
END_MARKER = "<!-- TRANSFER-READINGS: END -->"
BANNED: tuple[str, ...] = ("suggests", "consistent with", "attributable", "implies")

app = typer.Typer(add_completion=False, help=__doc__)


def extract_section(text: str) -> str | None:
    """The text between the two markers, or None when either is missing.

    Args:
        text: The rendered pack.

    Returns:
        The section body, or None.
    """
    start = text.find(BEGIN_MARKER)
    end = text.find(END_MARKER)
    if start < 0 or end < 0 or end < start:
        return None
    return text[start + len(BEGIN_MARKER) : end]


def count_banned(section: str) -> dict[str, int]:
    """Case-insensitive, word-bounded counts of each banned word.

    Args:
        section: The section body.

    Returns:
        ``{word: count}`` for every word in :data:`BANNED`.
    """
    return {
        word: len(re.findall(rf"\b{re.escape(word)}\b", section, flags=re.IGNORECASE))
        for word in BANNED
    }


@app.command()
def main(
    pack: Annotated[Path, typer.Argument(help="The rendered pack file to check")],
) -> None:
    """Scan the assembled transfer-reading section of ``pack`` for banned words.

    Args:
        pack: The rendered pack file.

    Raises:
        typer.Exit: 1 on any banned word inside the section; 2 when the
            section's markers are not both present.
    """
    section = extract_section(pack.read_text())
    if section is None:
        typer.echo(
            f"REFUSED: {pack} — the transfer-readings markers are not both present; "
            "nothing was checked, and nothing-checked is not a pass"
        )
        raise typer.Exit(2)
    counts = count_banned(section)
    typer.echo(f"absence check over {pack}")
    typer.echo(
        f"  section: {len(section.splitlines())} lines between "
        f"{BEGIN_MARKER!r} and {END_MARKER!r}"
    )
    for word, n in counts.items():
        typer.echo(f"  {word!r:20s} {n}")
    if any(counts.values()):
        hits = ", ".join(f"{w} x{n}" for w, n in counts.items() if n)
        typer.echo(f"FAIL: banned inside the assembled section — {hits}")
        raise typer.Exit(1)
    typer.echo("PASS: none of the banned words appears inside the assembled section")


if __name__ == "__main__":
    app()
