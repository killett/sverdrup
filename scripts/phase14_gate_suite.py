"""The gate sequence, in the order that makes its evidence true (pin 83).

    format -> stamp -> suite -> verify -> commit

The old order was ``suite -> pre-commit -> commit``. Because pre-commit
REWRITES files, the gate evidence came from a pre-format tree
structurally and every time. Pin 83(c) states why it earned a pin: the
principle was already understood — a 70-minute suite was killed on it
correctly earlier the same day — and the workflow defeated it four steps
later anyway. So the check is mechanical here, not remembered.

Commands:
    run      format, stamp the tree, run the suite, re-verify the stamp
    verify   assert the tree still matches the stamp (run before commit)
"""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer

from sverdrup.validation.gate_stamp import (
    changed_paths,
    file_digests,
    stamp_blockers,
)

app = typer.Typer(add_completion=False)

ROOT = Path()
STAMP = Path("logs/gate_stamp.json")
# Only files a rewriting hook or an edit could touch. Data and logs are
# excluded deliberately: a suite that writes a log must not invalidate
# its own evidence.
TRACKED_GLOBS = ("src/**/*.py", "scripts/**/*.py", "tests/**/*.py", "pyproject.toml")


def _tracked() -> list[str]:
    """Relative paths of every file the stamp covers.

    Returns:
        Sorted relative paths.
    """
    seen: set[str] = set()
    for pattern in TRACKED_GLOBS:
        for p in ROOT.glob(pattern):
            if p.is_file() and "__pycache__" not in p.parts:
                seen.add(str(p))
    return sorted(seen)


def _run(cmd: list[str]) -> int:
    """Run a command, streaming its output.

    Args:
        cmd: Argument vector.

    Returns:
        The process exit code.
    """
    typer.echo(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, check=False).returncode  # noqa: S603


@app.command()
def run(
    suite: Annotated[str, typer.Option(help="Suite command")] = "pixi run pytest -q",
    skip_suite: Annotated[bool, typer.Option(help="Stamp only, do not run")] = False,
) -> None:
    """Format and typecheck FIRST, then stamp, run the suite, re-verify.

    Raises:
        RuntimeError: If formatting or mypy fails, or if the tree changed while
            the suite was running — which would mean the evidence
            describes a tree that no longer exists.
    """
    if _run(["pixi", "run", "ruff", "format", "."]) != 0:
        raise RuntimeError("ruff format failed — fix before stamping")
    if _run(["pixi", "run", "ruff", "check", "--fix", "."]) != 0:
        typer.echo("NOTE: ruff check reported findings; they are yours to resolve")
    # mypy runs BEFORE the stamp for the same reason the formatter does: it is
    # part of pre-commit, so a failure found at commit time lands AFTER the
    # suite and invalidates it. Catching it here costs seconds; catching it at
    # commit costs the whole run.
    if _run(["pixi", "run", "mypy", "."]) != 0:
        raise RuntimeError(
            "mypy failed — fix before stamping. Running it here rather than at "
            "commit time is deliberate: a mypy failure discovered after the "
            "suite would force the suite to be re-run, which is exactly the "
            "defect pin 83 closed for formatters."
        )

    before = file_digests(ROOT, _tracked())
    STAMP.parent.mkdir(parents=True, exist_ok=True)
    stamp: dict[str, Any] = {
        "stamped_utc": datetime.now(UTC).isoformat(),
        "n_files": len(before),
        "digests": before,
    }
    STAMP.write_text(json.dumps(stamp, indent=2) + "\n")
    typer.echo(f"stamped {len(before)} files -> {STAMP}")

    if skip_suite:
        return
    code = _run(suite.split())
    after = file_digests(ROOT, _tracked())
    drift = changed_paths(before, after)
    if drift:
        raise RuntimeError(
            f"TREE CHANGED WHILE THE SUITE RAN: {drift}. The suite result "
            "describes a tree that no longer exists — re-run, do not commit."
        )
    # The completion record is what makes a later `verify` mean anything:
    # without it, a green tree attests nothing about whether tests ran.
    stamp["suite"] = {
        "completed": True,
        "exit_code": code,
        "command": suite,
        "finished_utc": datetime.now(UTC).isoformat(),
    }
    STAMP.write_text(json.dumps(stamp, indent=2) + "\n")
    typer.echo(f"suite exit {code}; tree unchanged across the run")
    if code != 0:
        raise RuntimeError(f"suite failed (exit {code})")


@app.command()
def verify() -> None:
    """Assert the tree still matches the stamp. Run immediately before commit.

    Raises:
        RuntimeError: If no stamp exists, if the stamp records no COMPLETED
            suite (or a failed one), or if any covered file changed since
            the suite started. The message NAMES the paths, the way the
            mirror gates do. The completion check exists because a green
            tree alone once returned PASS beside a suite still at 5%.
    """
    if not STAMP.exists():
        raise RuntimeError(f"no stamp at {STAMP} — run `run` before committing")
    stamp = json.loads(STAMP.read_text())
    blockers = stamp_blockers(stamp)
    if blockers:
        raise RuntimeError("STAMP DOES NOT LICENSE A COMMIT — " + " ".join(blockers))
    before = stamp["digests"]
    drift = changed_paths(before, file_digests(ROOT, _tracked()))
    if drift:
        raise RuntimeError(
            f"STAMP MISMATCH — these files changed after the suite ran: {drift}. "
            "The gate evidence is from a different tree. Re-run the suite; do "
            "not commit on it."
        )
    typer.echo(
        f"stamp verified: {len(before)} files unchanged since the suite ran, "
        f"and the stamp records a suite that COMPLETED with exit "
        f"{stamp['suite']['exit_code']}"
    )


if __name__ == "__main__":
    app()
