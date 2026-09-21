"""T8 — the OSSE run decision: a ruled WAIT (owner pins 250-252).

⛔ **THIS IS NO LONGER A PRICING PRODUCER.** Three pricing rounds were built
and all three were OVERTURNED by two-reviewer adversarial review under pin
212(b), each on the **unit of account**. Owner pin 250 ruled T8 a **WAIT**:
*validity is prior to price, and pricing stops here.*

⭐ **THE REASON IS NOT THAT THE PRICE WAS HARD.** It is that the experiment
being priced **may not answer its own value case**: there is no replication,
the truth field GLORYS12 **assimilates the very constellations under test**,
and neither epoch-span reading preserves "constellation varied over **FIXED**
model truth" — the value case's own word.

⚖ **SAME SHAPE AS T6 AND T7** (250c): a measured WAIT with its exits named,
not an empty row. **Gate 1 carries THREE ruled WAITs.**

What this module now does: record the WAIT, the three overturns and what each
found, the pin-251 exit, and — separately — the facts that SURVIVED every
round, each still derived from the store and the seal rather than typed.

Commands:
    (default)   print the WAIT record
    --record    also write phase14.stage1.osse_pricing
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer

app = typer.Typer(add_completion=False)

EVIDENCE = Path("data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json")
SEAL = Path("data/2021a_ssh_mapping_ose/ours/phase14_evaluation_seal_v1.json")
NODE = "osse_pricing"

PRICED_TILES: tuple[str, ...] = ("kuroshio", "equatorial", "quiet_gyre", "southern")
LOCKED_MISSIONS = frozenset({"c2", "c2n"})
LEG_MISSIONS: tuple[str, ...] = ("alg", "h2ag", "j2g", "j2n", "s3a")
LEG_PLATFORMS = 4

VALUE_CASE = (
    "constellation varied over FIXED model truth is the only ground-truth "
    "test of the era-transfer claim (fork-e level 1 validates against fitted "
    "s; OSSE against truth)"
)

# The three overturns, in order, each naming the defect rather than the fix.
OVERTURNS: tuple[dict[str, str], ...] = (
    {
        "version": "v1",
        "defect": "priced one epoch class = one tile solve",
        "why_wrong": (
            "what varies between epoch classes is the CONSTELLATION, and "
            "solve wall moves with observation count — so the unit of "
            "account was not the varying quantity"
        ),
        "found_by": "the frame reviewer; all five authored surfaces were CONFIRMED",
    },
    {
        "version": "v2",
        "defect": (
            "fitted wall on OBSERVATIONS and applied the exponent to MISSION "
            "COUNTS, then asserted a subset ordering as exponent-free"
        ),
        "why_wrong": (
            "the legs vary 1.26x in observations at a FIXED five-mission "
            "constellation, so observation count is a function of "
            "(constellation, tile), not of constellation alone. The ordering "
            "claim needed f CONVEX, not monotone, and reverses below p~0.638"
        ),
        "found_by": "the frame reviewer, and the owner's own ratifying arithmetic",
    },
    {
        "version": "v3",
        "defect": (
            "removed the exponent from the headline but LEFT IT IN THE ONLY "
            "SECTION THAT PRODUCES A VERDICT — the per-class walls and their "
            "40 h WAIT verdicts"
        ),
        "why_wrong": (
            "that is v2's defect exactly, in the one place a number changes a "
            "decision, and the document's own banner named it as v2's error "
            "without saying the section still did it. The breach count runs "
            "0 to 5 ACROSS THE DOCUMENT'S OWN BAND and is driven by MODEL, "
            "not by tile as the document claimed"
        ),
        "found_by": "the frame reviewer",
    },
)

# ⛔ Pin 251 — the exit. Named so Stage 2 inherits a direction, not a refusal.
EXIT: dict[str, Any] = {
    "headline": "THE TRUTH FIELD MUST BE A NATURE RUN, NOT A REANALYSIS",
    "why": (
        "GLORYS12 ASSIMILATES ALTIMETRY, so it has already seen the "
        "observations an OSSE would test — the fraternal-twin problem, and it "
        "is first-order for an experiment whose whole value case is 'against "
        "truth'. LLC4320-class truth is FREE-RUNNING and has not."
    ),
    "the_237_query_measured_the_wrong_kind_of_truth": (
        "the authorised metadata query returned GLORYS12 because the CMEMS "
        "host carries it. The 40.01 MiB per tile it established is therefore "
        "the size of the WRONG KIND OF TRUTH. The measurement was correct; "
        "the object was not."
    ),
    "llc4320_span_forces_the_common_span_design": (
        "LLC4320's span is ~14 months, so a per-era design is not available "
        "and the COMMON-SPAN design is forced"
    ),
    "the_open_design_question": (
        "⛔ WHETHER FLYING EACH ERA'S ORBIT GEOMETRY OVER ONE FIXED NATURE-RUN "
        "PERIOD PRESERVES 'CONSTELLATION VARIED OVER FIXED TRUTH' IS THE OPEN "
        "DESIGN QUESTION. It is OWNED BY STAGE 2 and is NOT resolved here."
    ),
    "replication_is_required_and_unpriced": (
        "15 classes x 1 tile x 1 realisation cannot separate 'this "
        "constellation is worse' from 'these track positions over this tile "
        "were unlucky'. Replication is REQUIRED and is UNPRICED."
    ),
    "owner": "Stage 2",
}


def _stage1(evidence_path: Path) -> dict[str, Any]:
    doc: dict[str, Any] = json.loads(evidence_path.read_text())
    stage1: dict[str, Any] = doc["phase14"]["stage1"]
    return stage1


def surviving_facts(
    evidence_path: Path = EVIDENCE, seal_path: Path = SEAL
) -> dict[str, Any]:
    """The facts that survived all three rounds, still derived (pin 252).

    Every one of these was attacked across three adversarial reviews and
    held. They are recorded so Stage 2 inherits them rather than re-deriving
    them, and they are computed here rather than typed so they cannot drift.

    Args:
        evidence_path: Path to the evidence store.
        seal_path: Path to the sealed evaluation file.

    Returns:
        The class census, the per-iteration decomposition, the convexity
        crossover, the platform convention, and the 99(c) attestation.
    """
    table = json.loads(seal_path.read_text())["content"]["epoch_table"]
    sets = [frozenset(e["missions"]) for e in table]
    counts = [len(e["missions"]) for e in table]

    tiles = _stage1(evidence_path)["tiles"]
    legs = []
    for t in PRICED_TILES:
        r = tiles[t]
        iters = sum(w["iterations"] for w in r["pcg"])
        legs.append(
            {
                "tile": t,
                "n_obs": r["n_obs"],
                "sum_pcg_iterations": iters,
                "wall_h": r["wall_s"] / 3600.0,
                "microseconds_per_obs_iteration": r["wall_s"]
                / (r["n_obs"] * iters)
                * 1e6,
            }
        )
    us = [leg["microseconds_per_obs_iteration"] for leg in legs]
    all_iters = [w["iterations"] for t in PRICED_TILES for w in tiles[t]["pcg"]]

    # The convexity crossover: where sum(m^p) for the two mask_66 subsets meet.
    pre = [len(e["missions"]) for e in table if e.get("mask_66")]
    post = [len(e["missions"]) for e in table if not e.get("mask_66")]

    def gap(p: float) -> float:
        post_cost: float = sum(float(m) ** p for m in post)
        pre_cost: float = sum(float(m) ** p for m in pre)
        return post_cost - pre_cost

    lo, hi = 0.1, 1.5
    for _ in range(200):
        mid = (lo + hi) / 2
        if gap(lo) * gap(mid) <= 0:
            hi = mid
        else:
            lo = mid
    crossover = (lo + hi) / 2

    return {
        "epoch_classes": {
            "n_epochs": len(table),
            "n_classes": len(set(sets)),
            "n_classes_without_locked": len({s - LOCKED_MISSIONS for s in sets}),
            "mission_counts": counts,
            "deduplication_available": len(set(sets)) < len(table),
            "note": (
                "15 epochs, 15 distinct mission sets, still 15 after removing "
                "the locked c2/c2n. THE PRICE HAS NO CHEAP REDUCTION "
                "AVAILABLE — a real property of the census (pin 234b)"
            ),
        },
        "per_iteration_decomposition": {
            "legs": legs,
            "microseconds_span": [min(us), max(us)],
            "spread_pct": (max(us) - min(us)) / 2 / (sum(us) / len(us)) * 100,
            "pcg_iterations_span": [min(all_iters), max(all_iters)],
            "reading": (
                "the per-iteration cost is constant to about +/-4.5%, so the "
                "wall is essentially LINEAR in (observations x iterations). "
                "The conditioning term is therefore first-order and it runs "
                "OPPOSITE to the observation term for sparse constellations — "
                "which is where 8 of the 15 classes sit"
            ),
        },
        "convexity_crossover_p": crossover,
        "convexity_note": (
            "the withdrawn subset ordering needed f CONVEX, not monotone: "
            "post-lift has FEWER and LARGER classes (6 classes / "
            f"{sum(post)} missions) than pre-lift (9 / {sum(pre)}), so the "
            f"ordering REVERSES below p ~ {crossover:.3f} (owner pin 244)"
        ),
        "platform_convention": {
            "leg_labels": len(LEG_MISSIONS),
            "leg_platforms": LEG_PLATFORMS,
            "note": (
                "j2g and j2n are time-disjoint ORBIT PHASES of ONE Jason-2, so "
                "the legs ran 4 PLATFORMS under 5 LABELS. The same over-count "
                "appears in epochs 0, 8, 9 and 14. Which convention a price "
                "uses moves it ~1.28x, and no pricing round disclosed one"
            ),
        },
        "pin_99c_attestation": (
            "no figure in any round traced to the CAPPED T2 probe "
            "(phase14.stage1.probe), confirmed by three independent reviews"
        ),
        "truth_volume_measured_but_for_the_wrong_object": (
            "the pin-237 metadata query is sound and its arithmetic exact "
            "(229 node-inclusive, 40.01 MiB per tile, 160.04 MiB for four) — "
            "but it measured GLORYS12, a REANALYSIS, and pin 251 rules the "
            "truth must be a free-running NATURE RUN. See EXIT."
        ),
    }


def wait_record(
    evidence_path: Path = EVIDENCE, seal_path: Path = SEAL
) -> dict[str, Any]:
    """Build T8's WAIT record (owner pins 250-252).

    Args:
        evidence_path: Path to the evidence store.
        seal_path: Path to the sealed evaluation file.

    Returns:
        The WAIT, its authority, the three overturns, the pin-251 exit, and
        the surviving facts.
    """
    return {
        "verdict": "WAIT",
        "verdict_authority": (
            "owner pin 250, 2026-09-20 — ruling PART 58 of "
            "docs/superpowers/2026-07-27-owner-ruling-crn-sigma-rule0.md"
        ),
        "decision": None,
        "decision_cell": "EMPTY",
        "report_only": True,
        "pricing_is_withdrawn": (
            "⛔ T8 IS NOT PRICED AND WILL NOT BE PRICED AT STAGE 1. "
            "VALIDITY IS PRIOR TO PRICE (owner pin 250): three pricing rounds "
            "were overturned on the unit of account, and the experiment "
            "itself may not answer its value case. A price for an experiment "
            "that may establish nothing is not a useful number."
        ),
        "why_wait_and_not_a_price": (
            "NO REPLICATION (15 classes x 1 tile x 1 realisation); a truth "
            "field that ASSIMILATES the constellations under test; and an "
            "epoch-span question that may not preserve 'FIXED truth' under "
            "EITHER reading. Until those are answered, any price is of an "
            "experiment that may establish nothing (owner pin 250b)."
        ),
        "same_shape_as_t6_and_t7": (
            "a MEASURED WAIT WITH ITS EXITS NAMED, not an empty row (250c). "
            "Gate 1 now carries THREE ruled WAITs: kernel 219, revisit 224, "
            "OSSE 250."
        ),
        "value_case_verbatim": VALUE_CASE,
        "value_case_is_what_is_at_risk": (
            "neither epoch-span reading preserves 'constellation varied over "
            "FIXED model truth'. Common-span requires SYNTHESISING historical "
            "ground tracks, so the constellations are no longer the "
            "historical ones; per-era makes the truth no longer FIXED, which "
            "is the value case's own word."
        ),
        "overturns": list(OVERTURNS),
        "overturn_count": len(OVERTURNS),
        "exit": EXIT,
        "surviving_facts": surviving_facts(evidence_path, seal_path),
        "the_v3_document": {
            "path": "docs/superpowers/2026-09-20-phase14-t8-osse-pricing.md",
            "status": "WITHDRAWN as a pricing deliverable; PRESERVED as the record of why",
            "why_preserved": (
                "it carries the three overturns and the reviewer findings in "
                "full. Deleting it would leave the WAIT without its reasoning "
                "(owner pin 252)."
            ),
        },
        "citations": [
            "owner pin 250 — T8 is a WAIT; validity is prior to price",
            "owner pin 251 — the exit: a free-running NATURE RUN, not a reanalysis",
            "owner pin 252 — close T8 as a WAIT, witnessed",
            "owner pin 212(b) — the two-reviewer review that overturned all three rounds",
            "owner pin 241 — the second reviewer attacks the frame",
        ],
    }


@app.command()
def main(
    record: Annotated[
        bool, typer.Option(help="Also write phase14.stage1.osse_pricing")
    ] = False,
) -> None:
    """Print T8's WAIT record; ``--record`` also writes evidence.

    Args:
        record: Write the block to the evidence store.
    """
    block = wait_record()
    typer.echo(f"T8 verdict: {block['verdict']} ({block['overturn_count']} overturns)")
    for o in block["overturns"]:
        typer.echo(f"  {o['version']}: {o['defect']}")
    typer.echo(f"\n  EXIT: {block['exit']['headline']}")
    sf = block["surviving_facts"]
    lo, hi = sf["per_iteration_decomposition"]["microseconds_span"]
    typer.echo(
        f"  surviving: {sf['epoch_classes']['n_classes']} classes, no dedup; "
        f"{lo:.1f}-{hi:.1f} us/obs-iter; crossover p={sf['convexity_crossover_p']:.3f}"
    )
    typer.echo(f"  DECISION CELL: {block['decision_cell']}")

    if record:
        from sverdrup.application.calibration.harness import (  # noqa: PLC0415
            atomic_write_json,
        )
        from sverdrup.validation import phase14_seal  # noqa: PLC0415

        phase14_seal.verify_current_seal()
        doc = json.loads(EVIDENCE.read_text())
        doc.setdefault("phase14", {}).setdefault("stage1", {})[NODE] = block
        atomic_write_json(EVIDENCE, doc)
        typer.echo(f"\nrecorded: phase14.stage1.{NODE}")


if __name__ == "__main__":
    app()
