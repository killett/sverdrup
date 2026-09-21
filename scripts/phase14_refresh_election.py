"""The Gate-1 refresh election — the OUTCOME, recorded (owner pins 255-259).

Owner pin 255 ruled the six-mission production refresh **ELECTED**, scope
Stage-2G assembly runs onward, **BUNDLED** with Stage 2G's acceptance chain.
Pin 259(b) puts that outcome in the evidence store at the pre-registered node
``phase14.stage1.refresh_election`` — the C-11 line the contract has owed
since pin 136, which T9 could only PRESENT with its decision cell empty.

**The quotes are EXTRACTED from the landed ruling, never hand-pasted.** Pins
255-258 are read out of PART 59 of the ruling document at build time, so the
witnessed node cannot drift from the ruling it cites, and a tree where the
ruling is *not* landed raises instead of writing a blank quote (pins 41/48).

**The c2 tally is READ FROM THE STORE**, not asserted here. Pin 255(c) says
BUNDLED spends no touch and leaves the tally untouched; a claim like that is
worth only as much as the number it is checked against, so the number comes
from ``phase13.miost.c2_acceptance.c2_touch_tally``.

⛔ Pin 258 is IN the record, in the record's own words: the election makes no
claim about the transfer result. A node that let a successor read the sixth
mission as the remedy for the weak-signal finding would be the one way this
recording could do harm.

Commands:
    (default)   print the election record
    --record    also write it to the evidence store
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Annotated, Any

import typer

app = typer.Typer(add_completion=False)

EVIDENCE = Path("data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json")
RULING = Path("docs/superpowers/2026-07-27-owner-ruling-crn-sigma-rule0.md")
NODE = "refresh_election"

PART = "PART 59"
OUTCOME_PINS: tuple[str, ...] = ("255", "256", "257", "258")

# The tally node pin 255(c) makes a claim about. Named as a path so the claim
# is checkable against the store rather than against this file.
TALLY_PATH = "phase13.miost.c2_acceptance.c2_touch_tally"

# The Phase-13 deferral, verbatim (owner T14 item 2, Phase-13 close). The
# election fires its FIRST branch: Stage 2G is the next six-mission-relevant
# improvement that can share the chain.
BUNDLING_RULE = (
    "it runs with its OWN chain + touch when the next six-mission-relevant "
    "improvement can share the chain, or at the global-domain transition — "
    "whichever first. Neither silent fold-in nor flat decline."
)


def pins_verbatim(ruling_path: Path = RULING) -> dict[str, str]:
    """Extract pins 255-258 from the landed ruling's PART 59 blockquote.

    Args:
        ruling_path: Path to the owner ruling document.

    Returns:
        ``{pin: text}`` for each outcome pin, whitespace-normalised.

    Raises:
        RuntimeError: If PART 59 is absent from the document, or if any
            outcome pin is missing from it. A missing quote is a tree where
            the ruling is not landed, and recording from it would cite a
            ruling that is not at HEAD (pins 41/48).
    """
    text = ruling_path.read_text()
    if f"## {PART}" not in text:
        raise RuntimeError(
            f"{PART} is not in {ruling_path}: the ruling is NOT LANDED, so "
            "nothing may cite it (pins 41/48)"
        )
    section = text.split(f"## {PART}", 1)[1].split("\n## ", 1)[0]

    quoted = [
        line[1:].lstrip() for line in section.splitlines() if line.startswith(">")
    ]
    body = re.sub(r"\s+", " ", " ".join(quoted).replace("**", "")).strip()

    bounds = {
        pin: match.start()
        for pin in OUTCOME_PINS + ("259",)
        for match in [re.search(rf"(?:^|(?<=\s)){pin}\. ", body)]
        if match is not None
    }
    missing = [pin for pin in OUTCOME_PINS if pin not in bounds]
    if missing:
        raise RuntimeError(
            f"{PART} in {ruling_path} does not carry pin(s) {', '.join(missing)}: "
            "the landed quote is partial, which is not a ruling"
        )

    ordered = sorted(bounds.items(), key=lambda kv: kv[1])
    spans: dict[str, str] = {}
    for index, (pin, start) in enumerate(ordered):
        end = ordered[index + 1][1] if index + 1 < len(ordered) else len(body)
        spans[pin] = body[start:end].strip()
    return {pin: spans[pin] for pin in OUTCOME_PINS}


def c2_touch_tally(evidence_path: Path = EVIDENCE) -> dict[str, int]:
    """Read the c2 touch tally pin 255(c) leaves untouched.

    Args:
        evidence_path: Path to the evidence store.

    Returns:
        The tally as the store holds it, e.g. ``{"miost5": 3, "miost6": 1}``.
    """
    node: Any = json.loads(evidence_path.read_text())
    for key in TALLY_PATH.split("."):
        node = node[key]
    return {str(k): int(v) for k, v in node.items()}


def election_record(
    evidence_path: Path = EVIDENCE, ruling_path: Path = RULING
) -> dict[str, Any]:
    """Build the Gate-1 refresh-election record (owner pins 255-258).

    Args:
        evidence_path: Path to the evidence store (the c2 tally's source).
        ruling_path: Path to the landed ruling (the quotes' source).

    Returns:
        The outcome, its scope, the chain/touch disposition, what it
        reunifies, both Stage-2 obligations, the pin-258 firewall, and the
        four outcome pins verbatim.
    """
    return {
        "outcome": "ELECTED",
        "outcome_authority": (
            "owner pin 255, 2026-09-21 — ruling PART 59 of "
            "docs/superpowers/2026-07-27-owner-ruling-crn-sigma-rule0.md"
        ),
        "contract_line": "C-11 — the Gate-1 shipped-config election OUTCOME with its scope",
        "what_was_elected": (
            "the six-mission production refresh with structured R: Phase 12's "
            "frozen-transfer chain re-run on the Phase-13 R-winner, j3 "
            "assimilated"
        ),
        "scope": "Stage-2G assembly runs onward, as the spec named it (1-8)",
        "presented_rule_is_not_the_decision": (
            "T9 pack item (7) posted the presumptive rule with the decision "
            "cell EMPTY and STOPPED, because Gate 1 is the owner's (pin 136b). "
            "THIS NODE IS THE DECISION. A successor must not read the "
            "presentation as the answer — that reading is the defect pin 136 "
            "created task 23 to prevent."
        ),
        "chain_and_touch": {
            "mode": "BUNDLED",
            "bundled_with": "Stage 2G's acceptance chain, sharing its touch",
            "bundling_rule_verbatim": BUNDLING_RULE,
            "bundling_rule_source": (
                "owner T14 item 2 at the Phase-13 close; named again in the "
                "Phase-14 program design §1 as fired by THIS program"
            ),
            "branch_that_fired": (
                "the FIRST branch of the rule quoted above — Stage 2G is the "
                "shareable chain, and it is reached before the global-domain "
                "transition"
            ),
            "touch_spent_now": False,
            "c2_touch_tally_observed": c2_touch_tally(evidence_path),
            "c2_touch_tally_source": TALLY_PATH,
            "tally_untouched_by_this_ruling": True,
        },
        "what_it_reunifies": {
            "statement": (
                "SHIPPED is already six-mission without structured R; the "
                "structured-R winner is five-mission. The election joins them."
            ),
            "shipped_is_already_six_mission": True,
            "shipped_factory": "shipped_miost6",
            "shipped_flip": "b4878a0",
            "structured_r_winner_is_five_mission": True,
            "is_a_mission_count_change": False,
        },
        "delta_j3": {
            "rule": "δ_j3 := δ_j2n",
            "basis": "instrument-class match, Poseidon-series",
            "status": "PROVISIONAL",
            "fitted": False,
            "why_not_fitted": (
                "the five-mission contrasts never fit j3 — it was the "
                "VALIDATION HOLDOUT — so the presumptive rule supplies an "
                "INHERITED value"
            ),
            "governed_by": "Stage 2's per-era δ assignment (spec E7)",
            "if_stage2_fits_it": (
                "the fit replaces the inheritance and the election stands unchanged"
            ),
            "is_a_condition_of_the_election": False,
            "obligation": "owner pin 256 — a named Stage-2 obligation in the C1->2 contract",
        },
        "e10_holdout_consequence": {
            "statement": (
                "2G does not run on the elected config until e10's "
                "replacement holdout is chosen and sealed"
            ),
            "why": (
                "every Stage-1 transfer reading is j3-validated, and j3 is the "
                "2017 epoch's (e10) holdout in the sealed census. Assimilating "
                "j3 from 2G onward consumes that holdout."
            ),
            "is_a_precondition_on_2g": True,
            "resolved": False,
            "selection_criteria": "fork C's recorded criteria, in order",
            "obligation": "owner pin 257 — carried in the C1->2 contract as a precondition",
        },
        "makes_no_claim_about_the_transfer_result": (
            "⛔ THE ELECTION MAKES NO CLAIM ABOUT THE TRANSFER RESULT (owner "
            "pin 258). A sixth mission raises observation density, and nothing "
            "recorded says whether that helps, hurts or leaves unchanged the "
            "two tiles whose λx is absent. That mechanism is firewalled and "
            "open. The election is about reuniting the shipped product with "
            "its calibration. It must not be cited as a remedy for the "
            "weak-signal finding, and no record may imply it is."
        ),
        "stage2_obligations": [
            "pin 256 — δ_j3 := δ_j2n is PROVISIONAL; Stage 2's per-era δ "
            "assignment (E7) governs it",
            "pin 257 — e10's replacement holdout is chosen and sealed BEFORE "
            "2G runs on the elected config",
        ],
        "ruling_verbatim": pins_verbatim(ruling_path),
        "citations": [
            "owner pin 255 — ELECTED, scope 2G onward, BUNDLED, no touch spent",
            "owner pin 256 — δ_j3 is PROVISIONAL, superseded by Stage 2",
            "owner pin 257 — the e10 holdout consequence, a precondition on 2G",
            "owner pin 258 — the transfer-result firewall",
            "owner pin 259(b) — this node is an APPEND to a pre-registered node",
            "owner pin 136 — C-11's producer is task 23, post-gate",
        ],
    }


@app.command()
def main(
    record: Annotated[
        bool, typer.Option(help="Also write phase14.stage1.refresh_election")
    ] = False,
) -> None:
    """Print the election record; ``--record`` also writes evidence.

    Args:
        record: Write the block to the evidence store.
    """
    block = election_record()
    typer.echo(f"refresh election: {block['outcome']}  scope={block['scope']}")
    ct = block["chain_and_touch"]
    typer.echo(
        f"  chain: {ct['mode']} with {ct['bundled_with']}; "
        f"touch spent now = {ct['touch_spent_now']}; "
        f"c2 tally {ct['c2_touch_tally_observed']} (unchanged)"
    )
    typer.echo(f"  δ_j3: {block['delta_j3']['status']} — {block['delta_j3']['rule']}")
    typer.echo(f"  e10: {block['e10_holdout_consequence']['statement']}")
    typer.echo(f"  pins quoted verbatim: {', '.join(block['ruling_verbatim'])}")

    if record:
        from sverdrup.application.calibration.harness import (  # noqa: PLC0415
            atomic_write_json,
        )
        from sverdrup.validation import phase14_seal  # noqa: PLC0415

        phase14_seal.verify_current_seal()
        doc = json.loads(EVIDENCE.read_text())
        stage1 = doc.setdefault("phase14", {}).setdefault("stage1", {})
        if NODE in stage1:
            raise RuntimeError(
                f"phase14.stage1.{NODE} already exists — pin 259(b) rules this "
                "an APPEND to a PRE-REGISTERED node, not a supersession. "
                "Overwriting a written node is the mirror's business, via "
                "--supersede with a reason."
            )
        stage1[NODE] = block
        atomic_write_json(EVIDENCE, doc)
        typer.echo(f"\nrecorded: phase14.stage1.{NODE}")


if __name__ == "__main__":
    app()
