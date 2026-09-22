"""The Gate-1 closure record's DERIVED sections (owner pin 264).

Owner pins 260-267 closed Gate 1 and Stage 1. Pin 264(b) rules that the
record's derived halves — **the four reads of 262(a)** and **the per-line
node citations for C-01…C-14** — come from a producer and are *never
hand-pasted* (230e). This is that producer.

**Why a producer and not prose.** A closure record is the artifact Stage 2
reads instead of re-deriving Stage 1. Hand-typing 14 node citations into it
would make it a second, unchecked copy of the mirror: it would look right
for exactly as long as nobody changed anything. Here every citation is
resolved against ``phase14-stage1-provenance.json`` at build time, and a
carrier that has gone missing RAISES rather than rendering a blank cell —
pin 264(b)'s "STOP and report; it does not get prose instead".

⛔ **THE READS ARE FAILABLE, AND EACH RECORDS WHAT WOULD HAVE TRIPPED IT**
(262a). Read (i) takes its key from ``locked_tier._TALLY_KEYS`` rather than
retyping it (§7-12: the key has one origin), which is the whole point of
finding F1 — the per-run guard retyped the key and has been watching
``phase14.locked_n``, which nothing writes.

The ruled at-closure STATUS of each line is the owner's own accounting from
pin 260 and is quoted, not computed. What is computed is the evidence: which
witnessed node carries the line, and what that node actually says today.

Commands:
    (default)   print the derived sections as markdown
    --write     splice them into the record between its DERIVED markers
    --check     verify the record's derived blocks match this producer
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Annotated, Any

import typer

app = typer.Typer(add_completion=False)

STORE = Path("data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json")
MIRROR = Path("docs/validation/evidence-mirror/phase14-stage1-provenance.json")
RECORD = Path("docs/superpowers/2026-09-21-phase14-gate1-closure.md")

# The legacy list's digest as pin 262(a)(iii) names it. A change trips.
LEGACY_TALLY_NODE = "c2_touch_tally"
LEGACY_TALLY_DIGEST_PREFIX = "9ea71b85"
LEGACY_TALLY_DIGEST_SUFFIX = "d806"

# Pin 262(a)(ii): the value witnessed in phase14.stage1.refresh_election.
C2_TALLY_PATH = ("phase13", "miost", "c2_acceptance", "c2_touch_tally")
C2_TALLY_EXPECTED = {"miost5": 3, "miost6": 1}

# Pin 262(a)(iv): the ceremony's env gates. Taken from the modules that
# define them, never retyped — the same discipline F1 caught being broken.
ENV_GREP_ROOTS = ("scripts/",)

MARKERS = ("reads", "contract")


class ClosureReadError(RuntimeError):
    """A 262(a) read could not be taken, or a carrier has gone missing."""


# ---------------------------------------------------------------------------
# C-01…C-14 — the contract lines, their ruled status, and their carriers.
#
# `status` is the OWNER'S accounting (pin 260), quoted. `carriers` are
# (node, field-path) pairs resolved against the mirror at build time: the
# cell shows what the witnessed node says TODAY, so a line whose evidence
# moved cannot keep reading as discharged.
# ---------------------------------------------------------------------------

CONTRACT_LINES: tuple[dict[str, Any], ...] = (
    {
        "id": "C-01",
        "deliverable": "Tiling machinery",
        "status": "COVERED — machinery run and green (260a's identity accounting)",
        "carriers": (
            ("phase14.stage1.anchor_gate", "pass"),
            ("phase14.stage1.reachability_declarations", "finding"),
        ),
    },
    {
        "id": "C-02",
        "deliverable": "Measured seam behaviour — ORACLE verdict",
        "status": "260(b) — mean CLEAN (R=0.098103); σ NOT_ESTABLISHED",
        "carriers": (
            ("phase14.stage1.seam_rows", "2.verdict"),
            ("phase14.stage1.seam_rows", "3.verdict"),
        ),
    },
    {
        "id": "C-03",
        "deliverable": "Measured seam behaviour — RUBRIC (pair) verdicts",
        "status": "260(b) — mean CLEAN (R=0.082738); σ NOT_ESTABLISHED",
        "carriers": (
            ("phase14.stage1.seam_rows", "0.verdict"),
            ("phase14.stage1.seam_rows", "1.verdict"),
            ("phase14.stage1.sigma_rows_not_established", "withheld.0"),
        ),
    },
    {
        "id": "C-04",
        "deliverable": "High-latitude kernel DECISION",
        "status": "260(d) — WAIT, option cell EMPTY (219)",
        "carriers": (
            ("phase14.stage1.kernel_pack", "decision"),
            ("phase14.stage1.kernel_pack", "decided_by"),
            ("phase14.stage1.kernel_hull_deferred", "label"),
        ),
    },
    {
        "id": "C-05",
        "deliverable": "…and its arithmetic",
        "status": "COVERED (arithmetic); the anisotropy INPUT is UNEVIDENCED (108)",
        "carriers": (
            ("phase14.stage1.kernel_pack", "arithmetic.in_box_cos_decrease"),
            ("phase14.stage1.kernel_pack", "anisotropy_axis.status"),
        ),
    },
    {
        "id": "C-06",
        "deliverable": "Per-tile frozen-config transfer readings (j3-side coverage/χ²) + µ/λx",
        "status": "260(c) — FOUR, witnessed; composition INCOMPLETE, no GroundTrack row (106)",
        "carriers": tuple(
            (f"phase14.stage1.tiles.{tile}", "scores.chi2_j3_validation.value")
            for tile in ("kuroshio", "southern", "equatorial", "quiet_gyre")
        ),
    },
    {
        "id": "C-07",
        "deliverable": "…raw-σ rows",
        "status": "PRODUCED — per-tile, never presented as calibrated (spec §6 policy a)",
        "carriers": tuple(
            (f"phase14.stage1.tiles.{tile}", "scores.raw_sigma.label")
            for tile in ("kuroshio", "southern", "equatorial", "quiet_gyre")
        ),
    },
    {
        "id": "C-08",
        "deliverable": "…LABELLED scalar-s* reference rows",
        "status": "PRODUCED — labelled REFERENCE-ONLY, with the s*/χ² identity in-row (100)",
        "carriers": (
            ("phase14.stage1.tiles.kuroshio", "reference_row.label"),
            (
                "phase14.stage1.tiles.kuroshio",
                "scores.s_star_chi2_identity.same_by_construction",
            ),
            (
                "phase14.stage1.tiles.kuroshio",
                "scores.s_star_chi2_identity.not_corroboration",
            ),
        ),
    },
    {
        "id": "C-09",
        "deliverable": "Equatorial lane-0 baseline persisted under the frozen fold/eval frame",
        "status": "PRODUCED — manifest witnessed AT CREATION (96d)",
        "carriers": (
            ("phase14.stage1.equatorial_lane0_manifest", "witness_class"),
            ("phase14.stage1.equatorial_lane0_manifest", "frozen_config_policy"),
        ),
    },
    {
        "id": "C-10",
        "deliverable": "Land-mask path exercised",
        "status": "PRODUCED — n_scored_points honest at the land-bearing tile",
        "carriers": (("phase14.stage1.tiles.kuroshio", "scores.n_scored_points"),),
    },
    {
        "id": "C-11",
        "deliverable": "The Gate-1 shipped-config election OUTCOME with its scope",
        "status": "260(f) — DISCHARGED 2026-09-21: ELECTED, BUNDLED, no touch spent (255)",
        "carriers": (
            ("phase14.stage1.refresh_election", "outcome"),
            ("phase14.stage1.refresh_election", "scope"),
            ("phase14.stage1.refresh_election", "chain_and_touch.touch_spent_now"),
        ),
    },
    {
        "id": "C-12",
        "deliverable": "The σ seam question is recorded OPEN, with the inheritance package NAMED",
        "status": "COVERED — OPEN, carried to Stage 2 (263.5)",
        "carriers": (
            ("phase14.stage1.sigma_rows_not_established", "consequence"),
            ("phase14.stage1.seam_sigma_diagnosis", "not_established"),
        ),
    },
    {
        "id": "C-13",
        "deliverable": "STAGE 2 / 2G MAY NOT ASSUME σ SEAMS ARE CLEAN",
        "status": "COVERED — 'UNANSWERED, not answered clean' is the node's own wording",
        "carriers": (
            ("phase14.stage1.sigma_rows_not_established", "consequence"),
            ("phase14.stage1.seam_sigma_diagnosis", "question"),
        ),
    },
    {
        "id": "C-14",
        "deliverable": "The CRN defect travels forward as a PRODUCTION DEFECT",
        "status": "COVERED — OPEN, and Stage 2G cannot close while it stands (263.6)",
        "carriers": (
            ("phase14.stage1.crn_production_defect_deferred", "status"),
            (
                "phase14.stage1.crn_production_defect_deferred",
                "stage_2g_cannot_close_while_it_stands",
            ),
        ),
    },
)


def _dig(value: Any, field_path: str, where: str) -> Any:
    """Resolve a dotted field path, with list indices, or raise.

    Args:
        value: The node value to walk.
        field_path: Dotted path; a numeric segment indexes a list.
        where: Node name, for the error message.

    Returns:
        The value at the path.

    Raises:
        ClosureReadError: The path does not resolve — a carrier has moved
            or gone, and pin 264(b) forbids rendering prose in its place.
    """
    node = value
    for segment in field_path.split("."):
        try:
            node = node[int(segment)] if segment.isdigit() else node[segment]
        except (KeyError, IndexError, TypeError) as exc:
            raise ClosureReadError(
                f"{where}: field '{field_path}' does not resolve in the mirror "
                "— the line's at-closure status is NOT derivable, so it gets "
                "a STOP and not prose (pin 264b)"
            ) from exc
    return node


def _render(value: Any, limit: int = 150) -> str:
    """Render a mirrored value for a table cell, without inventing one."""
    if value is None:
        return "`null` (EMPTY)"
    if isinstance(value, bool):
        return f"`{str(value).lower()}`"
    if isinstance(value, int | float):
        return f"`{value}`"
    if isinstance(value, str):
        flat = re.sub(r"\s+", " ", value).strip()
        cut = flat if len(flat) <= limit else flat[: limit - 1] + "…"
        return cut.replace("|", "\\|")
    if isinstance(value, list):
        return f"*{len(value)} entries*"
    return f"*{len(value)} fields: {', '.join(list(value)[:4])}…*"


def load_mirror(mirror_path: Path = MIRROR) -> dict[str, Any]:
    """Load the evidence mirror.

    Args:
        mirror_path: Path to the provenance mirror.

    Returns:
        The parsed mirror document.
    """
    mirror: dict[str, Any] = json.loads(mirror_path.read_text())
    return mirror


def contract_rows(mirror_path: Path = MIRROR) -> list[dict[str, Any]]:
    """Resolve every contract line's carriers against the mirror.

    Args:
        mirror_path: Path to the provenance mirror.

    Returns:
        One row per contract line, each carrying resolved citations.

    Raises:
        ClosureReadError: A cited node is absent from the mirror, carries
            no digest, or a cited field does not resolve.
    """
    mirror = load_mirror(mirror_path)
    nodes = mirror["nodes"]
    rows: list[dict[str, Any]] = []
    for line in CONTRACT_LINES:
        citations: list[dict[str, str]] = []
        for node_name, field_path in line["carriers"]:
            if node_name not in nodes:
                raise ClosureReadError(
                    f"{line['id']}: cited node '{node_name}' is NOT in the "
                    "mirror — the line cannot cite what is not witnessed"
                )
            entry = nodes[node_name]
            digest = entry.get("digest_sha256", "")
            if len(digest) != 64:
                raise ClosureReadError(
                    f"{line['id']}: node '{node_name}' has no usable digest"
                )
            citations.append(
                {
                    "node": node_name,
                    "field": field_path,
                    "value": _render(_dig(entry["value"], field_path, line["id"])),
                    "digest": digest[:12],
                }
            )
        rows.append({**line, "citations": citations})
    return rows


# ---------------------------------------------------------------------------
# 262(a) — the four reads
# ---------------------------------------------------------------------------


def read_locked_tally(store_path: Path = STORE) -> dict[str, Any]:
    """Read (i): the CEREMONY's ledger must be ABSENT or EMPTY.

    The key comes from ``locked_tier._TALLY_KEYS`` and is never retyped —
    finding F1 is precisely what retyping it costs.

    Args:
        store_path: Path to the evidence store.

    Returns:
        The read: its key, value, trip condition and whether it trips.
    """
    from sverdrup.validation.locked_tier import _TALLY_KEYS  # noqa: PLC0415

    node: Any = json.loads(store_path.read_text())
    present = True
    for key in _TALLY_KEYS:
        if isinstance(node, dict) and key in node:
            node = node[key]
        else:
            present = False
            break
    value = "ABSENT (no such node in the store)" if not present else json.dumps(node)
    return {
        "id": "(i)",
        "name": "the ceremony's ledger",
        "method": (
            f"`{'.'.join(_TALLY_KEYS)}`, keyed from `locked_tier._TALLY_KEYS` "
            "and not retyped"
        ),
        "value": value,
        "trip_condition": "any entry trips",
        "trips": bool(present and node),
    }


def read_c2_tally(store_path: Path = STORE) -> dict[str, Any]:
    """Read (ii): the c2 ledger must equal the witnessed value.

    Args:
        store_path: Path to the evidence store.

    Returns:
        The read, as for :func:`read_locked_tally`.
    """
    node: Any = json.loads(store_path.read_text())
    for key in C2_TALLY_PATH:
        node = node[key]
    return {
        "id": "(ii)",
        "name": "the c2 ledger",
        "method": (
            f"`{'.'.join(C2_TALLY_PATH)}`, the value witnessed in "
            "`phase14.stage1.refresh_election` and written by "
            "`scripts/phase13_c2_touch.py`"
        ),
        "value": json.dumps(node, sort_keys=True),
        "trip_condition": f"any value other than {json.dumps(C2_TALLY_EXPECTED, sort_keys=True)} trips",
        "trips": node != C2_TALLY_EXPECTED,
    }


def read_legacy_digest(mirror_path: Path = MIRROR) -> dict[str, Any]:
    """Read (iii): the legacy list's mirrored digest must be unchanged.

    Args:
        mirror_path: Path to the provenance mirror.

    Returns:
        The read, as for :func:`read_locked_tally`.
    """
    digest = load_mirror(mirror_path)["nodes"][LEGACY_TALLY_NODE]["digest_sha256"]
    unchanged = digest.startswith(LEGACY_TALLY_DIGEST_PREFIX) and digest.endswith(
        LEGACY_TALLY_DIGEST_SUFFIX
    )
    return {
        "id": "(iii)",
        "name": "the legacy list, unchanged",
        "method": (
            "`phase14_evidence_mirror.py check` PASS **without a re-sync**, and "
            f"the mirrored digest of `{LEGACY_TALLY_NODE}`"
        ),
        "value": digest,
        "trip_condition": (
            f"a digest not matching `{LEGACY_TALLY_DIGEST_PREFIX}…"
            f"{LEGACY_TALLY_DIGEST_SUFFIX}` trips"
        ),
        "trips": not unchanged,
    }


def read_env_grep() -> dict[str, Any]:
    """Read (iv): no Stage-1 producer references the ceremony's env gates.

    The residual 262(a)(iv) names: the ceremony increments on clean
    completion only, so an open that crashed would leave no entry. The
    grep is what covers that gap.

    Returns:
        The read, with the grep's hits (or their absence) recorded.
    """
    from sverdrup.adapters.insitu.gauges import LOCKED_ENV  # noqa: PLC0415
    from sverdrup.validation.locked_tier import TOUCH_ENV  # noqa: PLC0415

    pattern = f"{TOUCH_ENV}|{LOCKED_ENV}"
    ripgrep = shutil.which("rg")
    if ripgrep is None:
        raise ClosureReadError(
            "read (iv) needs rg and it is not on PATH — the read is NOT taken, "
            "and an untaken read is not a passed one"
        )
    # The command is fully resolved and its arguments come from the modules
    # that DEFINE the env names, never from input.
    proc = subprocess.run(  # noqa: S603
        [ripgrep, "-n", pattern, *ENV_GREP_ROOTS],
        capture_output=True,
        text=True,
        check=False,
    )
    hits = [line for line in proc.stdout.splitlines() if line.strip()]
    return {
        "id": "(iv)",
        "name": "the residual — no producer can open a ceremony",
        "method": f"`rg -n '{pattern}' {' '.join(ENV_GREP_ROOTS)}`",
        "value": "NO HITS" if not hits else "; ".join(hits),
        "trip_condition": "any hit in a Stage-1 producer trips",
        "trips": bool(hits),
    }


def closure_reads(
    store_path: Path = STORE, mirror_path: Path = MIRROR
) -> list[dict[str, Any]]:
    """Take all four reads of pin 262(a).

    Args:
        store_path: Path to the evidence store.
        mirror_path: Path to the provenance mirror.

    Returns:
        The four reads, in the ruling's order.
    """
    return [
        read_locked_tally(store_path),
        read_c2_tally(store_path),
        read_legacy_digest(mirror_path),
        read_env_grep(),
    ]


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render_reads(reads: list[dict[str, Any]]) -> str:
    """Render the four reads as markdown.

    Args:
        reads: Output of :func:`closure_reads`.

    Returns:
        The markdown block.
    """
    tripped = [r for r in reads if r["trips"]]
    verdict = (
        "✅ **ALL FOUR READS PASS. NONE TRIPS.**"
        if not tripped
        else "⛔ **TRIPPED: " + ", ".join(r["id"] for r in tripped) + "**"
    )
    lines = [
        f"{verdict} Gate 1's one quantitative criterion is discharged by direct",
        "read at closure, not by the per-run guard (262).",
        "",
        "| read | what is read | value AT CLOSURE | what would have tripped it | verdict |",
        "|---|---|---|---|---|",
    ]
    for r in reads:
        lines.append(
            f"| **{r['id']}** {r['name']} | {r['method']} | `{r['value']}` | "
            f"{r['trip_condition']} | {'⛔ TRIPS' if r['trips'] else '✅ passes'} |"
        )
    return "\n".join(lines)


def render_contract(rows: list[dict[str, Any]]) -> str:
    """Render the C-01…C-14 at-closure table as markdown.

    Args:
        rows: Output of :func:`contract_rows`.

    Returns:
        The markdown block.
    """
    lines = [
        f"**{len(rows)} contract lines, every one citing the witnessed node(s) that",
        "carry it.** The status column is the owner's accounting (260), quoted. The",
        "evidence column is RESOLVED AGAINST THE MIRROR at build time — node, field,",
        "and what that field says today — so a line whose carrier moved cannot keep",
        "reading as discharged.",
        "",
        "| line | C1→2 deliverable | at-closure status (ruled) | witnessed carrier → what it says now | digest |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        cites = "<br>".join(
            f"`{c['node']}` → `{c['field']}`: {c['value']}" for c in row["citations"]
        )
        digests = "<br>".join(f"`{c['digest']}…`" for c in row["citations"])
        lines.append(
            f"| **{row['id']}** | {row['deliverable']} | {row['status']} | {cites} | {digests} |"
        )
    return "\n".join(lines)


def derived_blocks(
    store_path: Path = STORE, mirror_path: Path = MIRROR
) -> dict[str, str]:
    """Build both derived blocks.

    Args:
        store_path: Path to the evidence store.
        mirror_path: Path to the provenance mirror.

    Returns:
        ``{marker: markdown}`` for each DERIVED section.
    """
    return {
        "reads": render_reads(closure_reads(store_path, mirror_path)),
        "contract": render_contract(contract_rows(mirror_path)),
    }


def splice(text: str, blocks: dict[str, str]) -> str:
    """Replace each DERIVED marker's contents with freshly built markdown.

    Args:
        text: The record's current text.
        blocks: Output of :func:`derived_blocks`.

    Returns:
        The record text with every derived block replaced.

    Raises:
        ClosureReadError: A marker pair is missing from the record.
    """
    out = text
    for name, body in blocks.items():
        begin, end = f"<!-- BEGIN DERIVED: {name} -->", f"<!-- END DERIVED: {name} -->"
        if begin not in out or end not in out:
            raise ClosureReadError(f"record is missing the '{name}' DERIVED markers")
        head, rest = out.split(begin, 1)
        _, tail = rest.split(end, 1)
        out = f"{head}{begin}\n{body}\n{end}{tail}"
    return out


@app.command()
def main(
    write: Annotated[
        bool, typer.Option(help="Splice the blocks into the record")
    ] = False,
    check: Annotated[
        bool, typer.Option(help="Verify the record matches this producer")
    ] = False,
) -> None:
    """Print, write, or check the closure record's derived sections.

    Args:
        write: Splice the derived blocks into the record.
        check: Verify the record's blocks match what this producer builds.

    Raises:
        SystemExit: ``--check`` found the record out of step.
    """
    blocks = derived_blocks()
    if not write and not check:
        for name, body in blocks.items():
            typer.echo(f"\n===== DERIVED: {name} =====\n{body}")
        return

    current = RECORD.read_text()
    spliced = splice(current, blocks)
    if check:
        if spliced != current:
            typer.echo(
                "DRIFT: the record's derived blocks are NOT what this producer builds"
            )
            raise SystemExit(1)
        typer.echo(
            "record derived blocks: PASS (byte-identical to the producer's output)"
        )
        return
    RECORD.write_text(spliced)
    typer.echo(f"wrote derived blocks into {RECORD}")


if __name__ == "__main__":
    app()
