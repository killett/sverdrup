"""T19 seal assembly runner — build once, re-derive forever (0a-6).

The seal recipe as an executable (T19 review finding 4): ``build`` writes
seal v1 (WRITE-ONCE) + the evidence pointer; ``check`` re-assembles the
content from the LIVE artifacts and compares the sha against the sealed
file and the evidence pointer — a drifted input FAILS, it never silently
passes. Inputs: epoch-table bytes (Task 5), locked split + screening
config (Task 8, config derived from the operative constants), instrument
configs (Tasks 9/11), c2 era windows (table-derived: rows whose locked
instruments meet {c2, c2n}).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from sverdrup.adapters.insitu.screening import screening_config_record
from sverdrup.core.seeding import derive_seed
from sverdrup.validation.phase14_instruments import serialize_instrument_configs
from sverdrup.validation.phase14_seal import (
    EVIDENCE,
    SEAL_V1,
    assemble_content,
    build_seal,
    seal_sha,
    supersede_seal,
    verify_seal,
)

app = typer.Typer(add_completion=False)

EPOCH_TABLE_PATH = Path("data/cmems_my/epoch_table_draft.json")
LOCKED_SPLIT = Path("data/insitu/locked_split.json")

_EpochTableOpt = Annotated[Path, typer.Option("--epoch-table")]
_LockedSplitOpt = Annotated[Path, typer.Option("--locked-split")]
_SealPathOpt = Annotated[Path, typer.Option("--seal-path")]
_EvidencePathOpt = Annotated[Path, typer.Option("--evidence-path")]


def _assemble(epoch_table: Path, locked_split: Path) -> dict[str, object]:
    table_bytes = epoch_table.read_bytes()
    rows = json.loads(table_bytes)
    c2_windows = sorted(
        r["epoch_id"] for r in rows if {"c2", "c2n"} & set(r["locked_instruments"])
    )
    return assemble_content(
        epoch_table_bytes=table_bytes,
        locked_split=json.loads(locked_split.read_text()),
        split_seed=int(derive_seed("insitu", "phase14-seal", "locked-split", 0)),
        screening_config=screening_config_record(),
        instrument_config_bytes=serialize_instrument_configs(),
        c2_era_windows=c2_windows,
    )


@app.command()
def build(
    epoch_table: _EpochTableOpt = EPOCH_TABLE_PATH,
    locked_split: _LockedSplitOpt = LOCKED_SPLIT,
    seal_path: _SealPathOpt = SEAL_V1,
    evidence_path: _EvidencePathOpt = EVIDENCE,
) -> None:
    """Build seal v1 (WRITE-ONCE) + record the evidence pointer."""
    content = _assemble(epoch_table, locked_split)
    sha = build_seal(content, path=seal_path)  # refuses an existing seal
    results = json.loads(evidence_path.read_text())
    node = results["phase14"]["stage0"].setdefault("seal", {})
    if node:
        raise typer.BadParameter(
            "phase14.stage0.seal already recorded — the pointer is write-once"
        )
    node.update(
        {
            "path": str(seal_path),
            "sha": sha,
            "version": 1,
            "date": datetime.now(UTC).date().isoformat(),
        }
    )
    from sverdrup.application.calibration.harness import (  # noqa: PLC0415
        atomic_write_json,
    )

    atomic_write_json(evidence_path, results)
    typer.echo(f"seal built: {seal_path} sha {sha}")


# The supersession envelope: fields `supersede_seal` adds to an AMENDED
# content that no live artifact produces. `check` re-derives the
# substantive fields and admits these three verbatim from the sealed file
# — it must not go blind to artifact drift to accommodate them.
_ENVELOPE_KEYS = ("supersedes", "signoff", "date")


@app.command()
def check(
    epoch_table: _EpochTableOpt = EPOCH_TABLE_PATH,
    locked_split: _LockedSplitOpt = LOCKED_SPLIT,
    seal_path: _SealPathOpt = SEAL_V1,
    evidence_path: _EvidencePathOpt = EVIDENCE,
) -> None:
    """Re-derive the sha from the LIVE artifacts; FAIL on any drift."""
    recorded = json.loads(evidence_path.read_text())["phase14"]["stage0"]["seal"]
    content = _assemble(epoch_table, locked_split)
    sealed_path = Path(recorded["path"])
    if sealed_path.exists():
        sealed = json.loads(sealed_path.read_text()).get("content", {})
        content.update({k: sealed[k] for k in _ENVELOPE_KEYS if k in sealed})
    derived = seal_sha(content)
    failures = []
    if derived != recorded["sha"]:
        failures.append(
            f"live-artifact re-assembly sha {derived} != recorded {recorded['sha']}"
        )
    try:
        verify_seal(Path(recorded["path"]), recorded["sha"])
    except Exception as e:  # noqa: BLE001 - report, then exit nonzero
        failures.append(f"seal file verification: {e}")
    if failures:
        for f in failures:
            typer.echo(f"FAIL: {f}")
        raise typer.Exit(code=1)
    typer.echo(f"PASS: seal {recorded['path']} sha {recorded['sha']} re-derived")


@app.command()
def supersede(
    signoff: Annotated[
        str,
        typer.Option(
            "--signoff",
            help="The owner decision that authorizes the amendment (required)",
        ),
    ],
    epoch_table: _EpochTableOpt = EPOCH_TABLE_PATH,
    locked_split: _LockedSplitOpt = LOCKED_SPLIT,
    evidence_path: _EvidencePathOpt = EVIDENCE,
) -> None:
    """Amend the seal: a NEW version file + the pointer, chain recorded.

    The sanctioned amendment path (fork-f pin 2). The CURRENT seal must
    verify against its recorded pointer first, the new content is
    re-assembled from the LIVE artifacts, and the pointer moves while
    recording what it superseded — Gate 0's evidence quotes v1 by sha, and
    that quotation must stay resolvable.
    """
    results = json.loads(evidence_path.read_text())
    node = results["phase14"]["stage0"].get("seal")
    if not node:
        raise typer.BadParameter(
            "no phase14.stage0.seal recorded — there is nothing to supersede "
            "(build the seal first)"
        )
    old_path = Path(node["path"])
    verify_seal(old_path, node["sha"])  # refuse to amend an unverified seal
    content = _assemble(epoch_table, locked_split)
    if seal_sha(content) == node["sha"]:
        raise typer.BadParameter(
            "the live artifacts re-assemble to the RECORDED sha — the sealed "
            "content is unchanged, so there is nothing to amend (a v2 identical "
            "in substance to v1 makes 'which version verdicted this row' "
            "unanswerable)"
        )
    new_path, sha = supersede_seal(old_path, content, signoff)
    results["phase14"]["stage0"]["seal"] = {
        "path": str(new_path),
        "sha": sha,
        "version": int(node["version"]) + 1,
        "date": datetime.now(UTC).date().isoformat(),
        "signoff": signoff,
        "supersedes": dict(node),
    }
    from sverdrup.application.calibration.harness import (  # noqa: PLC0415
        atomic_write_json,
    )

    atomic_write_json(evidence_path, results)
    typer.echo(f"seal superseded: {new_path} sha {sha} (supersedes {node['sha']})")


if __name__ == "__main__":
    app()
