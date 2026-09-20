"""T7 revisit WAIT rows — the refusal, recorded as evidence (owner pin 230).

Owner pin 224 ruled T7 a **WAIT**: the per-lane guard passes every solve and
the AGGREGATE is refused. Pin 230 puts that refusal in the evidence store
rather than only in the ruling document, as four rows at
``phase14.stage1.revisit.<tile>``.

**The rows are DERIVED, never hand-pasted.** Every number is recomputed here
from two measured sources — the T5 legs at ``phase14.stage1.tiles.<tile>``
and the sealed phase-10 budget at ``phase10.oi.probe.budget`` — so a reader
can re-run this script and get the same rows. Nothing is projected: the
aggregate is a multiplication of two measured quantities (ruling PART 52).

⛔ **A ROW SHOWING ONLY `RUN` VERDICTS WOULD READ AS AN UNEXPLAINED
NON-RUN** (pin 230b). Every row therefore states, in its own body, why it is
a WAIT *despite* every lane passing. That asymmetry is the finding, not a
footnote on it.

Commands:
    (default)   print the rows
    --record    also write them to the evidence store
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer

from sverdrup.validation.phase10_lanes import LANES as _p10_LANES

app = typer.Typer(add_completion=False)

EVIDENCE = Path("data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json")
REVISIT_NODE = "revisit"

# The four diverse tiles. The anchor is the identity subject and the seam
# pair is the seam subject; a lane at either measures nothing new.
REVISIT_TILES: tuple[str, ...] = ("kuroshio", "southern", "equatorial", "quiet_gyre")

# Anchors per lane, from `phase10_lanes.anchors_for`: the lane-0 winner is
# evaluated inside V and VL; the V winner inside VL with l1 = 0.
LANE_ANCHORS: dict[str, int] = {"V": 1, "VL": 2}

TIER_CEILING_H = 40.0

# ⛔ Pin 225(b), VERBATIM. It travels IN THE ROW: a reader who pulls the
# cheap option out of the store must get its weakness with it, or they will
# elect a 12.3-day run believing it can deliver a negative result.
ANCHORS_ONLY_LIMIT = (
    "ITS CLAIM IS STRICTLY WEAKER AND THAT LIMIT TRAVELS WITH IT: "
    "anchors-only can say \"the lane's designated configuration does not "
    'beat lane-0 in this regime." It CANNOT say "no configuration in the '
    'lane does." A negative result needs the second, and the sobol search '
    "is what buys it."
)

# Pin 199: kuroshio's peak predates the pin-133 fix and is NOT comparable to
# the post-fix basis. A row citing it bare re-raises a closed question.
PRE_133_TILES = frozenset({"kuroshio"})
PRE_133_CAVEAT = (
    "PRE-133 measurement — NOT comparable to the post-fix peak basis "
    "(owner pin 199). Wall is comparable; peak is not."
)


def _why_wait(tile: str) -> str:
    """Return the row's own statement of the WAIT/RUN asymmetry.

    Args:
        tile: The tile the row describes.

    Returns:
        The explanation required by pin 230(b).
    """
    return (
        f"EVERY LANE AT {tile} PASSES THE PER-LANE GUARD AND THE TOTAL IS "
        "REFUSED ANYWAY. Each solve is priced at this tile's measured leg, "
        f"which sits under the {TIER_CEILING_H:g} h per-leg ceiling, so "
        "owner pin 99(b) marks NOT ONE LANE a WAIT. The refusal is owner "
        "pin 224 and it is about the AGGREGATE, which pin 222(c) reserves "
        "to the owner: '99(b) governs whether a lane that CAN run must be "
        "recorded as a WAIT; it does not authorise the aggregate.' The "
        "per-lane guard was not wrong and was not overridden — it has no "
        "opinion on the total, by design. A phase-10 LANE IS NOT ONE LEG: "
        "it is n_sobol_per_lane Sobol trials plus anchors, and at Stage-1 "
        "tile scale each trial is a full leg. That is what makes an "
        "affordable lane an unaffordable revisit."
    )


def measured_leg(tile: str, store: dict[str, Any]) -> dict[str, Any]:
    """Pull one tile's MEASURED leg cost out of the evidence store.

    Args:
        tile: Tile name.
        store: The parsed evidence store.

    Returns:
        ``wall_h``, ``peak_rss_mib``, the source path, and — where pin 199
        applies — the caveat that the peak is not comparable.

    Raises:
        KeyError: If the tile has no recorded leg. Deliberately fatal: a
            missing leg would otherwise yield a row whose predicted cost is
            built on nothing, and an aggregate summed from nothing.
    """
    try:
        row = store["phase14"]["stage1"]["tiles"][tile]
        wall_s = row["wall_s"]
        peak = row["peak_rss_mib"]
    except (KeyError, TypeError) as exc:
        raise KeyError(
            f"no measured leg at phase14.stage1.tiles.{tile} — a revisit row "
            "cannot be priced without one"
        ) from exc

    leg: dict[str, Any] = {
        "wall_h": wall_s / 3600.0,
        "peak_rss_mib": peak,
        "source": f"phase14.stage1.tiles.{tile}",
    }
    if tile in PRE_133_TILES:
        leg["peak_caveat"] = PRE_133_CAVEAT
    return leg


def build_revisit_wait_row(
    tile: str, store: dict[str, Any], *, n_sobol: int, screening_n: int
) -> dict[str, Any]:
    """Build one tile's revisit WAIT row.

    Args:
        tile: Tile name.
        store: The parsed evidence store.
        n_sobol: ``n_sobol_per_lane`` from the sealed phase-10 budget.
        screening_n: The screening path's trials per lane.

    Returns:
        The row, carrying the verdict and its authority, the lane set with
        lane-0's exclusion reason, the per-lane sizing with each solve's
        tier verdict, the refused aggregate, the WAIT/RUN asymmetry, and
        pin 225(b)'s limit on the anchors-only option.
    """
    leg = measured_leg(tile, store)
    wall_h = leg["wall_h"]

    per_lane: list[dict[str, Any]] = []
    for lane, anchors in LANE_ANCHORS.items():
        solves = n_sobol + anchors
        per_lane.append(
            {
                "lane": lane,
                "released_dims": sorted(_p10_LANES[lane]),
                "n_sobol": n_sobol,
                "anchors": anchors,
                "solves": solves,
                "per_solve_wall_h": wall_h,
                "per_solve_peak_rss_mib": leg["peak_rss_mib"],
                # The ceiling is PER LEG, and each Sobol trial is a leg.
                "tier_verdict_per_solve": (
                    "WAIT" if wall_h > TIER_CEILING_H else "RUN"
                ),
                "tier_ceiling_h": TIER_CEILING_H,
                "lane_total_h": solves * wall_h,
            }
        )

    tile_solves = sum(entry["solves"] for entry in per_lane)
    screening_solves = sum(screening_n + a for a in LANE_ANCHORS.values())
    anchors_only_solves = sum(LANE_ANCHORS.values())

    return {
        "tile": tile,
        "verdict": "WAIT",
        "verdict_authority": (
            "owner pin 224, 2026-09-19 — ruling PART 52 of "
            "docs/superpowers/2026-07-27-owner-ruling-crn-sigma-rule0.md"
        ),
        "report_only": True,
        "measured_leg": leg,
        "lane_set": {
            "source": "sverdrup.validation.phase10_lanes.LANES",
            "lanes": {name: sorted(dims) for name, dims in _p10_LANES.items()},
            "lane0_excluded_reason": (
                "the T5 leg IS lane-0 at the frozen config (owner pin 226); "
                "re-solving it would measure the solver, not the lane"
            ),
        },
        "per_lane": per_lane,
        "tile_totals": {
            "solves": tile_solves,
            "wall_h": tile_solves * wall_h,
            "basis": "this tile's own measured leg, never a shared basis",
        },
        "aggregate_refused": {
            "scope": "four diverse tiles, lanes V and VL",
            "full_scope": {
                "n_sobol_per_lane": n_sobol,
                "solves": tile_solves * len(REVISIT_TILES),
                "note": "wall totals are the sum of the four tiles' own legs",
            },
            "screening": {
                "n_sobol_per_lane": screening_n,
                "solves": screening_solves * len(REVISIT_TILES),
                "contingency_active": True,
            },
            "budget_source": "phase10.oi.probe.budget",
            "refused_by": "owner pin 224(a)",
        },
        "why_wait_despite_all_lanes_run": _why_wait(tile),
        "anchors_only_option": {
            "elected": False,
            "authority": "owner pin 225 — priced, presented, NOT elected",
            "solves_per_tile": anchors_only_solves,
            "solves_total": anchors_only_solves * len(REVISIT_TILES),
            "tile_wall_h": anchors_only_solves * wall_h,
            "role": "STAGE 2's entry point, so Stage 2 inherits a priced "
            "option rather than a refusal",
            "limit": ANCHORS_ONLY_LIMIT,
            "not_elected_reason": (
                "12 days for a report-only result whose strong form is "
                "unreachable, on a memory-constrained box, where the "
                "box-scale negative is already never cited as transferring "
                "(discipline 7). The cost does not buy a Gate-1 item."
            ),
        },
        "screening_lever": {
            "priced": False,
            "reason": (
                "phase-10 screens every 4th day (91/365) at 478.25 s/trial "
                "versus 1918.26 s full-year, ~4x cheaper AT PHASE-10 SCALE. "
                "The Stage-1 leg is a 9-window solve, not a 365-day score, "
                "so scaling by 91/365 has NO VALID BASIS here (owner pin "
                "226). If it is ever wanted, it is a MEASUREMENT."
            ),
        },
        "citations": [
            "owner pin 224 — T7 WAIT, aggregate refused",
            "owner pin 225 — anchors-only priced, not elected",
            "owner pin 226 — lane-0 exclusion and the unpriced screening lever",
            "owner pin 222(c) — 99(b) governs the lane, never the aggregate",
            "owner pin 99(b) — a lane under the live ceiling is not a WAIT",
            "ruling PART 52 — pins 221-229 and the sizing table",
        ],
    }


def build_rows(evidence_path: Path = EVIDENCE) -> dict[str, dict[str, Any]]:
    """Build all four revisit WAIT rows from the store.

    Args:
        evidence_path: Path to the evidence store.

    Returns:
        ``{tile: row}`` for the four diverse tiles.
    """
    store = json.loads(evidence_path.read_text())
    budget = store["phase10"]["oi"]["probe"]["budget"]
    n_sobol = int(budget["n_sobol_per_lane"])
    screening_n = int(budget["screening"]["n_sobol_per_lane"])
    return {
        tile: build_revisit_wait_row(
            tile, store, n_sobol=n_sobol, screening_n=screening_n
        )
        for tile in REVISIT_TILES
    }


@app.command()
def main(
    record: Annotated[
        bool, typer.Option(help="Also write phase14.stage1.revisit.<tile>")
    ] = False,
) -> None:
    """Print the four revisit WAIT rows; ``--record`` also writes evidence.

    Args:
        record: Write the rows to the evidence store.
    """
    rows = build_rows(evidence_path=EVIDENCE)
    for tile, row in rows.items():
        total = row["tile_totals"]
        verdicts = {entry["tier_verdict_per_solve"] for entry in row["per_lane"]}
        typer.echo(
            f"{tile:11s} verdict={row['verdict']}  "
            f"per-solve tier verdicts={sorted(verdicts)}  "
            f"{total['solves']} solves  {total['wall_h']:.1f} h"
        )

    if record:
        from sverdrup.application.calibration.harness import (  # noqa: PLC0415
            atomic_write_json,
        )
        from sverdrup.validation import phase14_seal  # noqa: PLC0415

        phase14_seal.verify_current_seal()
        doc = json.loads(EVIDENCE.read_text())
        stage1 = doc.setdefault("phase14", {}).setdefault("stage1", {})
        node = stage1.setdefault(REVISIT_NODE, {})
        for tile, row in rows.items():
            node[tile] = row
        atomic_write_json(EVIDENCE, doc)
        for tile in rows:
            typer.echo(f"recorded: phase14.stage1.{REVISIT_NODE}.{tile}")


if __name__ == "__main__":
    app()
