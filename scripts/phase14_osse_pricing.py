"""T8 — the OSSE run decision, PRICED (owner pins 232/234/236/237/239).

Pricing work only: **no legs, no solves, no spend.** The decision cell stays
EMPTY — the OSSE run decision is the owner's at Gate 1.

⛔ **REBUILT UNDER OWNER PIN 239** after a two-reviewer adversarial review
OVERTURNED the first version. The defect was the **unit of account**: v1
priced *one class = one tile solve*, treating wall as independent of
observation count. The four legs are a controlled experiment — identical
19°×19° solve bbox, identical ``m=100``, identical 9×60 d window plan, with
**only n_obs varying** — and they give ``wall ∝ n_obs**1.41``. The legs ran a
FIVE-mission constellation; the epoch classes run THREE to NINE.

⚖ **PIN 239(b) — STATE THE DIRECTION FIRMLY, DECLARE THE MAGNITUDES.**
*Post-lift is dearer than pre-lift* is a COUNTING FACT (44 missions across 6
classes against 35 across 9) and holds at every exponent above zero, so it is
asserted. The obs-scaled HOURS are a projection from n=4 with the 3-mission
classes outside the measured range, so they carry a pin-139 declaration.
**One point estimate is not swapped for another.**

⚖ **PIN 236 — PRICE FROM THE LEGS.** Pin 89's probe is CONVERGED and
admissible under 99(c), but it is a ONE-WINDOW projection of the thing the
legs then measured, and it over-predicted its own tile by ~1.574×. It is a
cross-check, **not a price** (236b), and its figures are DERIVED from
``phase14.stage1.tier2_probe_kuroshio_m100`` rather than typed.

⛔ **THE CAPPED T2 PROBE IS NEVER USED** (99c / pin 23a).

Commands:
    (default)   print the pricing table
    --record    also write phase14.stage1.osse_pricing
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Annotated, Any

import typer

app = typer.Typer(add_completion=False)

EVIDENCE = Path("data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json")
SEAL = Path("data/2021a_ssh_mapping_ose/ours/phase14_evaluation_seal_v1.json")
NODE = "osse_pricing"

PRICED_TILES: tuple[str, ...] = ("kuroshio", "southern", "equatorial", "quiet_gyre")

# Locked instruments removed when testing for a cheaper deduplication.
LOCKED_MISSIONS = frozenset({"c2", "c2n"})

# The constellation the four legs actually ran — `PROBE_MISSIONS` at
# scripts/phase14_stage1_run.py:88. The leg rows do NOT carry a mission list,
# so this cannot be read from the store; it is test-pinned against the runner
# instead, which is the same gap reviewer A found on the probe constants.
LEG_MISSIONS: tuple[str, ...] = ("alg", "h2ag", "j2g", "j2n", "s3a")

TIER_CEILING_H = 40.0

# ---------------------------------------------------------------------------
# ⛔ PIN 237 — THE TRUTH-FIELD MEASUREMENT. Recorded facts from an AUTHORISED
# metadata-only STAC query (no download, one host, read-only). Recorded as
# constants rather than re-queried at record time: a producer that reaches the
# network to rebuild a witnessed row makes the row depend on an external
# service being up, and on what it says TODAY rather than what it said when
# the measurement was taken.
# ---------------------------------------------------------------------------
TRUTH_QUERY: dict[str, Any] = {
    "host": "stac.marine.copernicus.eu",
    "product": "GLOBAL_MULTIYEAR_PHY_001_030",
    "dataset": "cmems_mod_glo_phy_my_0.083deg_P1D-m_202311",
    "url": (
        "https://stac.marine.copernicus.eu/metadata/GLOBAL_MULTIYEAR_PHY_001_030/"
        "cmems_mod_glo_phy_my_0.083deg_P1D-m_202311/dataset.stac.json"
    ),
    "queried_utc": "2026-09-20T06:58:29Z",
    "http_status": 200,
    "authorisation": "owner pin 237(a) — metadata only, no download, one host",
    "grid": {
        "latitude_len": 2041,
        "longitude_len": 4320,
        "time_len": 12227,
        "step_deg": 0.08333333333333333,
        "temporal_extent": "1993-01-01T00:00:00Z .. 2026-06-23T00:00:00Z",
    },
    "zos_item_size_bytes": 2,
    "zos_dtype": "<i2",
    "no_total_volume_field": (
        "the STAC document carries NO total-size field; the volumes below are "
        "DERIVED from itemSize x grid geometry. That derivation rests on two "
        "typed geometry assumptions (the bbox and node-inclusive counting) "
        "and on the UNCOMPRESSED array size, so it is a bound on the wire "
        "volume rather than a wire measurement (reviewer defect 4)"
    ),
}

SOLVE_BBOX_DEG = 19.0  # 15 deg core + 2 deg overlap on each side

# Pre-registered CMEMS storage budget (ladder.STAGE0_SPEND_TABLE).
CMEMS_BUDGET_GIB = 50.0
DISK_AVAILABLE_GIB_AT_MEASUREMENT = 311

VALUE_CASE = (
    "constellation varied over FIXED model truth is the only ground-truth "
    "test of the era-transfer claim (fork-e level 1 validates against fitted "
    "s; OSSE against truth)"
)


def _stage1(evidence_path: Path) -> dict[str, Any]:
    doc: dict[str, Any] = json.loads(evidence_path.read_text())
    stage1: dict[str, Any] = doc["phase14"]["stage1"]
    return stage1


def epoch_classes(seal_path: Path = SEAL) -> dict[str, Any]:
    """Derive N_epoch-classes from the SEALED epoch table (pin 234a).

    Args:
        seal_path: Path to the sealed evaluation file.

    Returns:
        The epoch count, the distinct-constellation count, the count after
        removing locked instruments, and whether any deduplication exists.
    """
    table = json.loads(seal_path.read_text())["content"]["epoch_table"]
    sets = [frozenset(e["missions"]) for e in table]
    reduced = [s - LOCKED_MISSIONS for s in sets]
    return {
        "n_epochs": len(table),
        "n_classes": len(set(sets)),
        "n_classes_without_locked": len(set(reduced)),
        "locked_removed": sorted(LOCKED_MISSIONS),
        "deduplication_available": len(set(sets)) < len(table),
        "mission_counts": [len(e["missions"]) for e in table],
        "source": "phase14_evaluation_seal_v1.json content.epoch_table",
        "no_deduplication_note": (
            "EVERY epoch's constellation is UNIQUE — 15 epochs, 15 distinct "
            "mission sets, still 15 after removing the locked c2/c2n. THE "
            "PRICE HAS NO CHEAP REDUCTION AVAILABLE. A reader will otherwise "
            "assume one exists (owner pin 234b)."
        ),
    }


def obs_scaling(evidence_path: Path = EVIDENCE) -> dict[str, Any]:
    """Fit solve wall against observation count across the four legs.

    ⛔ **THIS IS THE DEFECT THAT OVERTURNED v1** (owner pin 239). The four
    legs are a controlled experiment: identical solve bbox, ``m``, window
    plan and constellation, with **only n_obs varying**. Wall is NOT
    independent of observation count, and an OSSE varies exactly that.

    ⚖ **The fit is a PROJECTION and is declared as one** (239b, pin 139).
    n=4, and the 3-mission classes sit outside the measured span.

    Args:
        evidence_path: Path to the evidence store.

    Returns:
        The per-leg observations and walls, the fitted exponent with its R²,
        and the pin-139 declaration bounding where it may be applied.
    """
    tiles = _stage1(evidence_path)["tiles"]
    pts = [(tiles[t]["n_obs"], tiles[t]["wall_s"] / 3600.0) for t in PRICED_TILES]

    xs = [math.log(n) for n, _ in pts]
    ys = [math.log(w) for _, w in pts]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    exponent = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / sum(
        (x - mx) ** 2 for x in xs
    )
    intercept = my - exponent * mx
    ss_res = sum(
        (y - (intercept + exponent * x)) ** 2 for x, y in zip(xs, ys, strict=True)
    )
    ss_tot = sum((y - my) ** 2 for y in ys)

    return {
        "legs": [
            {
                "tile": t,
                "n_obs": tiles[t]["n_obs"],
                "wall_h": tiles[t]["wall_s"] / 3600.0,
            }
            for t in PRICED_TILES
        ],
        "controlled": (
            "identical solve bbox (19x19 deg), identical m=100, identical "
            "9x60 d window plan, identical 5-mission constellation — n_obs is "
            "the only varying input"
        ),
        "exponent": exponent,
        "r_squared": 1.0 - ss_res / ss_tot,
        "leg_missions": list(LEG_MISSIONS),
        "n_missions_leg": len(LEG_MISSIONS),
        "independent_corroboration": (
            "phase14.stage1.tier2_probe_kuroshio_m100.derived_pin_89d.wall."
            "implied_exponent = 1.28, whose verdict_on_the_anchors already "
            "recorded 'NOT linear ... optimistic by 1.42x'. v1's flat model "
            "was FLATTER THAN LINEAR, which this project's own pinned "
            "evidence had already rejected once."
        ),
        "projection_declaration": {
            "pin": 139,
            "quantity": "solve wall as a function of observation count",
            "measured_over": {
                "n_legs": 4,
                "n_missions": len(LEG_MISSIONS),
                "n_obs_span": [min(n for n, _ in pts), max(n for n, _ in pts)],
            },
            "application_range": {
                "n_missions": [3, 9],
                "note": "3- and 4-mission classes are BELOW the measured span",
            },
            "within_measured_span": False,
            "what_it_may_be_used_for": (
                "MAGNITUDES ONLY, declared as projected. The DIRECTION of the "
                "subset ordering does NOT rest on this fit — it is a counting "
                "fact (owner pin 239a/b)."
            ),
        },
    }


def truth_field_cost(evidence_path: Path = EVIDENCE) -> dict[str, Any]:
    """Derive the truth-field volume from the recorded STAC metadata.

    ⭐ **The truth field does NOT scale with N_epoch-classes.** An OSSE
    varies the CONSTELLATION over FIXED truth — that is what makes it a
    ground-truth test — so truth is bought **ONCE PER TILE**, not once per
    class. *(The "per tile" qualifier is load-bearing and was dropped from
    v1's headline: four tiles is four buys.)*

    Args:
        evidence_path: Path to the evidence store (for the window plan).

    Returns:
        Per-day, per-span, per-four-tile and global volumes, with the
        scaling finding and a DERIVED feasibility verdict.
    """
    plan = _stage1(evidence_path)["tiles"]["quiet_gyre"]["window_plan"]
    starts = plan["starts"]
    span_days = max(s + plan["w_days"] for s in starts) - min(starts)
    strides = [b - a for a, b in zip(starts, starts[1:], strict=False)]

    step = TRUTH_QUERY["grid"]["step_deg"]
    item = TRUTH_QUERY["zos_item_size_bytes"]
    # Node-INCLUSIVE: the STAC grid is 2041 nodes over 170 deg = 2040
    # intervals + 1. A 19 deg bbox is 229 nodes, not 228 (reviewer defect 4).
    n_side = round(SOLVE_BBOX_DEG / step) + 1
    per_day_b = n_side * n_side * item
    one_tile_b = int(span_days * per_day_b)

    grid = TRUTH_QUERY["grid"]
    global_day_b = grid["latitude_len"] * grid["longitude_len"] * item

    gib = one_tile_b / 1024**3
    all_tiles_gib = gib * len(PRICED_TILES)
    feasible = all_tiles_gib <= CMEMS_BUDGET_GIB

    return {
        "measured": True,
        "searched_and_absent": False,
        "query": TRUTH_QUERY,
        "variable": "zos (sea surface height) — the OSSE truth field",
        "scope_assumption": (
            "zos only. No MDT, mask or ancillary fields are costed — adequate "
            "for a nadir-SLA OSSE, stated as a scope choice, not an omission"
        ),
        "solve_bbox_deg": SOLVE_BBOX_DEG,
        "bbox_caveat": (
            "this is the SOLVE box. Simulating observations needs truth over "
            "the OBS footprint (solve bbox + the 1.0 deg operative halo = 21 "
            "deg), which is (21/19)**2 = 1.22x larger. NOT applied here "
            "because the obs-footprint choice belongs with the run design; "
            "stated so the figure is read as the SOLVE-box volume it is"
        ),
        "grid_nodes_per_side": n_side,
        "grid_nodes_per_tile": n_side * n_side,
        "window_plan_span_days": span_days,
        "window_plan_shape": (
            f"9 windows x {plan['w_days']:.0f} d on a {strides[0]:.0f}-d stride "
            f"— OVERLAPPING by {plan['w_days'] - strides[0]:.0f} d, NOT "
            f"contiguous; {9 * plan['w_days']:.0f} window-days over a "
            f"{span_days:.0f}-d union. The UNION is the download basis "
            "because each day is bought once"
        ),
        "bytes_per_tile_per_day": per_day_b,
        "bytes_per_tile_per_span": one_tile_b,
        "mib_per_tile_per_span": one_tile_b / 1024**2,
        "gib_per_tile_per_span": gib,
        "mib_all_four_tiles": one_tile_b * len(PRICED_TILES) / 1024**2,
        "global_zos_per_day_mib": global_day_b / 1024**2,
        "global_zos_full_record_tib": global_day_b * grid["time_len"] / 1024**4,
        "does_not_scale_with_classes": (
            "THE TRUTH FIELD IS BOUGHT ONCE PER TILE, NOT ONCE PER CLASS. An "
            "OSSE varies the CONSTELLATION over FIXED model truth, so "
            "N_epoch-classes multiplies the RE-SOLVES and not the truth "
            "download. It DOES scale with the number of tiles."
        ),
        "feasibility": {
            "cmems_storage_budget_gib": CMEMS_BUDGET_GIB,
            "all_four_tiles_gib": all_tiles_gib,
            "fraction_of_budget": all_tiles_gib / CMEMS_BUDGET_GIB,
            "disk_available_gib_at_measurement": DISK_AVAILABLE_GIB_AT_MEASUREMENT,
            "verdict": "FEASIBLE" if feasible else "REFUSED",
            "derived_not_asserted": (
                "the verdict is computed from the volume against the budget, "
                "so shrinking the budget flips it"
            ),
            "why": (
                "the spec's 'heavy downloads' is true of the GLOBAL FULL "
                "RECORD (0.20 TiB of zos alone) and NOT of the tile-and-span "
                "subset an OSSE needs"
            ),
        },
    }


def probe_cross_check(evidence_path: Path = EVIDENCE) -> dict[str, Any]:
    """Derive pin 89's probe comparison from the store (reviewer defect 1).

    v1 typed ``3.440`` and ``123.8`` while citing the probe node as their
    source — a provenance claim nothing enforced, and a mutation of 123.8
    survived the whole suite. They are read from the node now.

    Args:
        evidence_path: Path to the evidence store.

    Returns:
        The projection, the measurement it is compared against, the
        over-prediction factor, and a pin-139 declaration.
    """
    s1 = _stage1(evidence_path)
    wall = s1["tier2_probe_kuroshio_m100"]["derived_pin_89d"]["wall"]
    measured = s1["tiles"]["kuroshio"]["wall_s"] / 3600.0
    projected = wall["per_tile_h"]
    four_measured = sum(s1["tiles"][t]["wall_s"] / 3600.0 for t in PRICED_TILES)

    return {
        "role": "CROSS-CHECK ONLY — NOT A PRICE (owner pin 236b)",
        "tile": "kuroshio",
        "source": "phase14.stage1.tier2_probe_kuroshio_m100.derived_pin_89d.wall",
        "h_per_window": wall["one_window_h"],
        "projected_tile_h": projected,
        "measured_same_tile_h": measured,
        "overprediction_factor": projected / measured,
        "four_tile_projected_h": wall["four_tiles_h"],
        "four_tile_measured_h": four_measured,
        "four_tile_overprediction_factor": wall["four_tiles_h"] / four_measured,
        "admissible_under_99c": True,
        "why_not_the_price": (
            "CONVERGED and admissible, but it is a ONE-WINDOW PROJECTION of "
            "the thing the legs then MEASURED, and the measurement supersedes "
            "it. Its value now is as a RECORD OF HOW A ONE-WINDOW PROJECTION "
            "PERFORMED."
        ),
        "projection_declaration": {
            "pin": 139,
            "quantity": "per-tile solve wall",
            "measured_over": {"n_windows": 1, "tile": "kuroshio", "m": 100},
            "application_range": {"n_windows": 9},
            "within_measured_span": False,
            "outcome_when_tested": (
                f"OVER-PREDICTED by {projected / measured:.3f}x against the "
                "direct nine-window measurement of the same tile"
            ),
        },
    }


SUBSET_LIMITS: dict[str, str] = {
    "full_sweep": "",
    "fit+validate": (
        "CANNOT establish transfer into the 5 validate-only epochs, which is "
        "where transfer is actually claimed"
    ),
    "pre_lift_mask66": (
        "CANNOT establish anything about the 6 modern post-lift constellations"
    ),
    "post_lift_mask66": (
        "CANNOT establish era-transfer across the 1992-2009 boundary — the era "
        "gap the claim is weakest at"
    ),
    "validate_only": (
        "CANNOT establish anything fitted; it tests only the transferred epochs"
    ),
}


def scope_subsets(
    evidence_path: Path = EVIDENCE, seal_path: Path = SEAL
) -> dict[str, Any]:
    """Name the scope subsets, with the ORDERING as a counting fact.

    ⛔ **v1's ordering was WRONG and its editorial inverted with it** (owner
    pin 239c). Under the flat model, post-lift looked cheaper than pre-lift
    because it has fewer classes. It has **more total observations** — 44
    missions across 6 classes against 35 across 9 — so it is dearer under any
    cost monotone in observations.

    ⚖ **DIRECTION asserted, MAGNITUDES declared** (239b): the mission totals
    are counts and settle the ordering at every exponent above zero; the
    hours are projected via :func:`obs_scaling`.

    Args:
        evidence_path: Path to the evidence store.
        seal_path: Path to the sealed evaluation file.

    Returns:
        The subsets, the ordering under both models, and the withdrawal of
        v1's editorial.
    """
    table = json.loads(seal_path.read_text())["content"]["epoch_table"]
    tiles = _stage1(evidence_path)["tiles"]
    walls = {t: tiles[t]["wall_s"] / 3600.0 for t in PRICED_TILES}
    lo_t = min(walls, key=lambda t: walls[t])
    hi_t = max(walls, key=lambda t: walls[t])
    p = obs_scaling(evidence_path)["exponent"]
    base_m = len(LEG_MISSIONS)

    picks: list[tuple[str, list[dict[str, Any]]]] = [
        ("full_sweep", table),
        ("fit+validate", [e for e in table if e.get("role") == "fit+validate"]),
        ("pre_lift_mask66", [e for e in table if e.get("mask_66")]),
        ("post_lift_mask66", [e for e in table if not e.get("mask_66")]),
        ("validate_only", [e for e in table if e.get("role") == "validate-only"]),
    ]
    rows: list[dict[str, Any]] = []
    for name, es in picks:
        n = len({frozenset(e["missions"]) for e in es})
        missions = sum(len(e["missions"]) for e in es)
        # Leg-equivalents: each class scaled by (its missions / 5)**p.
        eq = sum((len(e["missions"]) / base_m) ** p for e in es)
        rows.append(
            {
                "subset": name,
                "n_classes": n,
                "total_missions": missions,
                "elected": False,
                "flat_model_leg_equivalents": float(n),
                "obs_scaled_leg_equivalents": eq,
                f"flat_h_at_{lo_t}": n * walls[lo_t],
                f"obs_scaled_h_at_{lo_t}": eq * walls[lo_t],
                f"flat_h_at_{hi_t}": n * walls[hi_t],
                f"obs_scaled_h_at_{hi_t}": eq * walls[hi_t],
                "cannot_establish": SUBSET_LIMITS[name],
            }
        )

    by = {r["subset"]: r for r in rows}
    return {
        "rows": rows,
        "ordering_is_a_counting_fact": {
            "claim": "post_lift_mask66 is DEARER than pre_lift_mask66",
            "pre_lift": {
                "n_classes": by["pre_lift_mask66"]["n_classes"],
                "total_missions": by["pre_lift_mask66"]["total_missions"],
            },
            "post_lift": {
                "n_classes": by["post_lift_mask66"]["n_classes"],
                "total_missions": by["post_lift_mask66"]["total_missions"],
            },
            "why_exponent_free": (
                "post-lift has FEWER classes (6 vs 9) and MORE total missions "
                "(44 vs 35). Under ANY cost monotone in observation count it "
                "is dearer. ONLY the flat 'one class = one leg' model reverses "
                "it, and that model is what the review overturned."
            ),
            "magnitudes_are_projected": (
                "the HOURS carry obs_scaling's pin-139 declaration; the "
                "DIRECTION does not depend on the fit (owner pin 239a/b)"
            ),
        },
        "v1_editorial_WITHDRAWN": {
            "withdrawn_text": (
                "The cheapest subsets are cheap precisely because they drop "
                "the epochs the era-transfer claim is weakest at. Cost and "
                "evidential value move together here."
            ),
            "why": (
                "IT WAS AN ARTEFACT OF THE FLAT MODEL AND INVERTS WITH IT. The "
                "sparse historical constellations — exactly where era-transfer "
                "is weakest — carry the FEWEST observations and are therefore "
                "the CHEAPEST classes to solve."
            ),
            "not_replaced": (
                "⛔ NOT replaced with the opposite editorial (owner pin 239c): "
                "that would be the same mistake with a different sign. The "
                "inversion is recorded as a FINDING; no claim is made about "
                "cost and value moving together or apart."
            ),
        },
    }


def price(evidence_path: Path = EVIDENCE, seal_path: Path = SEAL) -> dict[str, Any]:
    """Build the full OSSE pricing block.

    Args:
        evidence_path: Path to the evidence store.
        seal_path: Path to the sealed evaluation file.

    Returns:
        The pricing block, decision cell EMPTY.
    """
    tiles = _stage1(evidence_path)["tiles"]
    walls = {t: tiles[t]["wall_s"] / 3600.0 for t in PRICED_TILES}
    classes = epoch_classes(seal_path)
    n = classes["n_classes"]
    scaling = obs_scaling(evidence_path)
    subsets = scope_subsets(evidence_path, seal_path)
    full = next(r for r in subsets["rows"] if r["subset"] == "full_sweep")
    eq = full["obs_scaled_leg_equivalents"]

    lo_t = min(walls, key=lambda t: walls[t])
    hi_t = max(walls, key=lambda t: walls[t])

    return {
        "decision": None,
        "decision_cell": "EMPTY",
        "decision_is_the_owners": (
            "PRICED, OWNER TO DECIDE — NOT 'not priced'. Every figure below "
            "is a measurement or a declared projection from one. What is "
            "absent is the owner's election, and only that (owner pin 235e)."
        ),
        "report_only": True,
        "no_run_in_this_plan": "pricing work only — no legs, no solves, no spend",
        "rebuilt_under_pin_239": (
            "v1 was OVERTURNED by a two-reviewer review: it priced one class = "
            "one tile solve, which treats wall as independent of observation "
            "count. See obs_scaling and scope_subsets."
        ),
        "value_case_verbatim": VALUE_CASE,
        "epoch_classes": classes,
        "obs_scaling": scaling,
        "probe_cross_check": probe_cross_check(evidence_path),
        "per_tile_price": {
            t: {
                "measured_leg_wall_h": walls[t],
                "basis": f"phase14.stage1.tiles.{t} — MEASURED, 9/9 CONVERGED",
                "flat_model_full_sweep_h": n * walls[t],
                "obs_scaled_full_sweep_h": eq * walls[t],
            }
            for t in PRICED_TILES
        },
        "full_sweep_range": {
            "n_classes": n,
            "measured_leg_spread_h": [walls[lo_t], walls[hi_t]],
            "low_tile": lo_t,
            "high_tile": hi_t,
            "flat_low_h": n * walls[lo_t],
            "flat_high_h": n * walls[hi_t],
            "obs_scaled_low_h": eq * walls[lo_t],
            "obs_scaled_high_h": eq * walls[hi_t],
            "why_a_range": (
                "A SINGLE NUMBER WOULD HIDE A 1.4x SPREAD THAT IS A PROPERTY "
                "OF THE TILES, NOT OF THE OSSE (owner pin 236c). 'A tile "
                f"solve' is not one number: the four measured legs run "
                f"{walls[lo_t]:.2f}-{walls[hi_t]:.2f} h."
            ),
            "which_tile_is_an_open_input": (
                "WHICH TILE AN OSSE WOULD USE IS NOT DEFAULTED HERE (236d). "
                "The choice belongs with the run decision."
            ),
        },
        "constellation_size_is_an_open_input": {
            "not_a_default": True,
            "statement": (
                "⛔ WHICH CONSTELLATION AN OSSE RE-SOLVE RUNS IS AN OPEN "
                "INPUT, NOT A DEFAULT — and it is the LARGER axis. The epoch "
                "classes run 3 to 9 missions against the legs' 5, a per-class "
                "spread of roughly 4.7x, against the tile axis's 1.40x."
            ),
            "v1_defect": (
                "v1 declared the SMALLER axis open while collapsing the "
                "BIGGER one (owner pin 239d)."
            ),
            "class_mission_counts": classes["mission_counts"],
            "leg_missions": len(LEG_MISSIONS),
        },
        "scope_subsets": subsets,
        "truth_field": truth_field_cost(evidence_path),
        "lower_bound": {
            "statement": (
                "THE FIGURES HERE ARE A LOWER BOUND ON THE OSSE PRICE — "
                "INCLUDING THE COMPUTE FIGURE ITSELF."
            ),
            "compute_is_itself_a_lower_bound": (
                "⛔ WIDENED UNDER OWNER PIN 239(e). v1 attributed the lower "
                "bound to uncosted ENGINEERING alone, so a reader concluded "
                "the compute band was sound. IT IS NOT: the flat model "
                "under-prices every class above 5 missions, and 7 of the 15 "
                "classes are above it."
            ),
            "what_is_covered": (
                "constellation-varied re-solves + the truth download, both at "
                "declared model assumptions"
            ),
            "what_is_not_costed": [
                "truth-provider wiring: the TRUTH interface is DORMANT since "
                "4b and re-arming it is unmeasured engineering time",
                "per-class observation simulation from the truth field",
                "scoring and analysis of 15 outputs",
                "non-convergence retries: the legs ran 424-554 PCG iterations "
                "at 5 missions; the 3-mission classes are sparser, "
                "worse-conditioned and outside anything measured",
                "calendar time and box occupancy: these are serial "
                "single-host hours, with a launch gate of 2x predicted peak "
                "RSS per class",
            ],
            "why_unmissable": (
                "Owner pins 237(d) and 239(e): an OSSE priced at re-solves "
                "alone understates it, and pin 235(b) named that as the most "
                "likely error. The gap is BOUNDED on the download axis and "
                "OPEN on both the engineering and the compute-model axes."
            ),
        },
        "recommendation_options": [
            {
                "option": "run at Stage-2 entry (when era-transfer is the live question)",
                "cost": "same compute; the truth download is trivial either way",
                "can_establish": (
                    "the era-transfer claim against truth at the point where "
                    "it becomes load-bearing"
                ),
                "cannot_establish": (
                    "anything for Gate 1 — it does not close a Stage-1 item"
                ),
            },
            {
                "option": "run now",
                "cost": (
                    f"flat model {n * walls[lo_t]:.1f}-{n * walls[hi_t]:.1f} h; "
                    f"obs-scaled (projected) {eq * walls[lo_t]:.1f}-"
                    f"{eq * walls[hi_t]:.1f} h"
                ),
                "can_establish": "the same thing, earlier",
                "cannot_establish": (
                    "any Stage-1 gate item — the OSSE is not a Gate-1 "
                    "deliverable, and Gate 1 already carries two ruled WAITs"
                ),
            },
        ],
        "citations": [
            "owner pin 99(c) — price from the CONVERGED numbers, basis in-row",
            "owner pin 232 — standalone doc + witnessed node; posted pack untouched",
            "owner pin 234 — N_epoch-classes derived; no deduplication; truth cost in",
            "owner pin 236 — price from the legs; the probe is a declared cross-check",
            "owner pin 237 — the STAC metadata query, authorised and recorded",
            "owner pin 239 — REBUILT: the unit of account was wrong",
            "fork-f pin 5 — the value case, verbatim",
        ],
    }


@app.command()
def main(
    record: Annotated[
        bool, typer.Option(help="Also write phase14.stage1.osse_pricing")
    ] = False,
) -> None:
    """Print the OSSE pricing table; ``--record`` also writes evidence.

    Args:
        record: Write the block to the evidence store.
    """
    block = price()
    sc = block["obs_scaling"]
    typer.echo(
        f"obs scaling: wall ~ n_obs^{sc['exponent']:.4f} "
        f"(R2 {sc['r_squared']:.4f}, n=4) — PROJECTED, declared"
    )
    rng = block["full_sweep_range"]
    typer.echo(
        f"full sweep FLAT       {rng['flat_low_h']:6.1f}-{rng['flat_high_h']:6.1f} h"
    )
    typer.echo(
        f"full sweep OBS-SCALED {rng['obs_scaled_low_h']:6.1f}-"
        f"{rng['obs_scaled_high_h']:6.1f} h  (projected)"
    )
    cf = block["scope_subsets"]["ordering_is_a_counting_fact"]
    typer.echo(
        f"ordering (counting fact): post-lift {cf['post_lift']['total_missions']} "
        f"missions / {cf['post_lift']['n_classes']} classes DEARER than pre-lift "
        f"{cf['pre_lift']['total_missions']} / {cf['pre_lift']['n_classes']}"
    )
    tf = block["truth_field"]
    typer.echo(
        f"truth: {tf['mib_per_tile_per_span']:.2f} MiB per tile ONCE "
        f"({tf['mib_all_four_tiles']:.1f} MiB for four) — {tf['feasibility']['verdict']}"
    )
    typer.echo(f"DECISION CELL: {block['decision_cell']}")

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
