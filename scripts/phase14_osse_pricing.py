"""T8 — the OSSE run decision, PRICED (v3; owner pins 232-249).

Pricing work only: **no legs, no solves, no spend.** The decision cell stays
EMPTY — the OSSE run decision is the owner's at Gate 1.

⛔ **v3 IS SIMPLER THAN v1, NOT MORE COMPLEX** (owner pin 245). Two rounds of
two-reviewer review overturned v1 and v2, both on the **unit of account**.
The decisive point: *every defensible model puts the sweep in 295-470 h, and
that band was always sufficient for a go/no-go.* So the headline is the
**band across models**, with **no exponent in it**. The fit is a recorded
**diagnostic**, not the pricing basis.

⛔ **THE DIRECTION CLAIM IS WITHDRAWN ENTIRELY** (owner pin 244). v2 asserted
that post-lift is dearer than pre-lift "under any cost monotone in
observations". **That is false.** Cost is ``sum f(m_i)``; post-lift has fewer
and larger classes, so the ordering needs **f CONVEX**, not monotone, and it
reverses below p ~ 0.638. **No ordering is re-derived** — convexity needs the
conditioning term, which needs a measurement that does not exist. §9 carries
no ordering at all.

⛔ **THE "CONTROLLED EXPERIMENT" PREMISE IS STRUCK** (245f). With n=4 and one
point per tile, observation count is **perfectly collinear with tile
identity**: the regression cannot separate "how many observations" from
"which tile".

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

PRICED_TILES: tuple[str, ...] = ("kuroshio", "equatorial", "quiet_gyre", "southern")
LOCKED_MISSIONS = frozenset({"c2", "c2n"})

# `PROBE_MISSIONS` at scripts/phase14_stage1_run.py:88 — test-pinned against
# the runner, because the leg rows carry no mission list.
LEG_MISSIONS: tuple[str, ...] = ("alg", "h2ag", "j2g", "j2n", "s3a")

# ⛔ THE PLATFORM CONVENTION IS AN OPEN INPUT (owner pin 245b). `j2g` and
# `j2n` are time-disjoint ORBIT PHASES of ONE Jason-2, so the legs ran FOUR
# platforms under five labels. v2 never disclosed the convention it chose.
LEG_PLATFORMS = 4
LABEL_VS_PLATFORM_NOTE = (
    "j2g and j2n are time-disjoint orbit phases of ONE Jason-2, so the legs "
    "ran 4 PLATFORMS under 5 LABELS. The same over-count appears in epochs 0 "
    "(e1+e1g), 8 (al+alg), 9 (j2+j2n) and 14 (j3g+j3n). Which convention a "
    "price uses moves it ~1.28x and v2 disclosed neither."
)

# ⚖ Owner pin 99(b) / E-16: the per-leg WAIT ceiling. v2 defined this and
# NEVER REFERENCED IT (owner pin 245c) — pin 99(b)'s rule as dead code.
TIER_CEILING_H = 40.0

# The Tier-2 launch gate (owner pin 155): MemAvailable >= 2 x measured peak.
LAUNCH_GATE_MIB = 9902.33

CMEMS_BUDGET_GIB = 50.0  # ladder.STAGE0_SPEND_TABLE, task_class cmems_downloads
DISK_AVAILABLE_GIB_AT_MEASUREMENT = 311

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
}

SOLVE_BBOX_DEG = 19.0

VALUE_CASE = (
    "constellation varied over FIXED model truth is the only ground-truth "
    "test of the era-transfer claim (fork-e level 1 validates against fitted "
    "s; OSSE against truth)"
)


def _stage1(evidence_path: Path) -> dict[str, Any]:
    doc: dict[str, Any] = json.loads(evidence_path.read_text())
    stage1: dict[str, Any] = doc["phase14"]["stage1"]
    return stage1


def _walls(evidence_path: Path) -> dict[str, float]:
    tiles = _stage1(evidence_path)["tiles"]
    return {t: tiles[t]["wall_s"] / 3600.0 for t in PRICED_TILES}


def epoch_classes(seal_path: Path = SEAL) -> dict[str, Any]:
    """Derive N_epoch-classes from the SEALED epoch table (pin 234a).

    Args:
        seal_path: Path to the sealed evaluation file.

    Returns:
        Counts, mission counts, and the no-deduplication finding.
    """
    table = json.loads(seal_path.read_text())["content"]["epoch_table"]
    sets = [frozenset(e["missions"]) for e in table]
    counts = [len(e["missions"]) for e in table]
    return {
        "n_epochs": len(table),
        "n_classes": len(set(sets)),
        "n_classes_without_locked": len({s - LOCKED_MISSIONS for s in sets}),
        "mission_counts": counts,
        "classes_above_leg_size": sum(1 for m in counts if m > len(LEG_MISSIONS)),
        "deduplication_available": len(set(sets)) < len(table),
        "source": "phase14_evaluation_seal_v1.json content.epoch_table",
        "no_deduplication_note": (
            "EVERY epoch's constellation is UNIQUE — 15 epochs, 15 distinct "
            "mission sets, still 15 after removing the locked c2/c2n. THE "
            "PRICE HAS NO CHEAP REDUCTION AVAILABLE (owner pin 234b)."
        ),
    }


def wall_diagnostic(evidence_path: Path = EVIDENCE) -> dict[str, Any]:
    """The per-iteration decomposition — a DIAGNOSTIC, not the pricing basis.

    ⚖ **Owner pin 245(e).** ``wall / (n_obs x sum_iterations)`` is constant to
    about ±4.5% across the four legs, which says the wall is essentially
    *linear in observations x iterations*. **About 60% of the apparent
    superlinearity in a raw wall-vs-n_obs fit is the ITERATION term wearing
    an observation exponent** — and the iteration term runs **OPPOSITE** to
    the observation term for sparse constellations, which are
    worse-conditioned.

    Args:
        evidence_path: Path to the evidence store.

    Returns:
        Per-leg observations, iterations, wall and the per-iteration cost,
        plus the raw fit recorded as a diagnostic with its collinearity
        caveat.
    """
    tiles = _stage1(evidence_path)["tiles"]
    rows = []
    for t in PRICED_TILES:
        r = tiles[t]
        iters = sum(w["iterations"] for w in r["pcg"])
        wall_h = r["wall_s"] / 3600.0
        rows.append(
            {
                "tile": t,
                "n_obs": r["n_obs"],
                "sum_pcg_iterations": iters,
                "wall_h": wall_h,
                "microseconds_per_obs_iteration": r["wall_s"]
                / (r["n_obs"] * iters)
                * 1e6,
            }
        )
    us = [r["microseconds_per_obs_iteration"] for r in rows]

    xs = [math.log(r["n_obs"]) for r in rows]
    ys = [math.log(r["wall_h"]) for r in rows]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    exponent = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / sum(
        (x - mx) ** 2 for x in xs
    )

    # Standard error and the 95% CI on the 4-leg slope (t, df = n-2).
    intercept = my - exponent * mx
    ss_res = sum(
        (y - (intercept + exponent * x)) ** 2 for x, y in zip(xs, ys, strict=True)
    )
    sxx = sum((x - mx) ** 2 for x in xs)
    se = math.sqrt((ss_res / (len(xs) - 2)) / sxx)
    t_crit = 4.302652729911275  # t(0.975, df=2)

    # ⚠ The anchor gate IS a measured m=100 9-window CONVERGED solve BELOW the
    # leg span (n_obs 54,345). v2's declaration claimed the small classes sat
    # "below anything measured"; that was wrong in both directions.
    ag = _stage1(evidence_path)["anchor_gate"]
    five = [(r["n_obs"], r["wall_h"]) for r in rows] + [
        (ag["n_obs"], ag["wall_s"] / 3600.0)
    ]
    fx = [math.log(n) for n, _ in five]
    fy = [math.log(w) for _, w in five]
    fmx, fmy = sum(fx) / len(fx), sum(fy) / len(fy)
    refit = sum((a - fmx) * (b - fmy) for a, b in zip(fx, fy, strict=True)) / sum(
        (a - fmx) ** 2 for a in fx
    )

    return {
        "legs": rows,
        "microseconds_per_obs_iteration_span": [min(us), max(us)],
        "fit_ci_95": [exponent - t_crit * se, exponent + t_crit * se],
        "refit_with_anchor_gate": refit,
        "anchor_gate_was_not_below_anything_measured": (
            "phase14.stage1.anchor_gate is a MEASURED m=100, 9-window, "
            "CONVERGED solve at n_obs 54,345 — BELOW the four legs' span. v2 "
            "declared the small classes 'below anything measured'; that was "
            "false. Including it drops the exponent to "
            f"{refit:.4f}. It is a smaller domain and a dc2021a source, so "
            "excluding it from the headline is defensible — but the reason "
            "for excluding it (a domain change) is the SAME confound that "
            "disqualifies the four-leg fit as a clean observation contrast. "
            "It cannot be had both ways, so the fit is a diagnostic only."
        ),
        "spread_pct": (max(us) - min(us)) / 2 / (sum(us) / len(us)) * 100,
        "reading": (
            "wall is essentially LINEAR in (observations x iterations): the "
            "per-iteration cost is constant to about +/-4.5% across four legs "
            "spanning 1.26x in observations."
        ),
        "raw_wall_vs_nobs_exponent": exponent,
        "is_a_diagnostic_not_a_basis": (
            "RECORDED AS A DIAGNOSTIC (owner pin 245a). It is NOT the pricing "
            "basis: about 60% of it is the iteration term, and the iteration "
            "term runs OPPOSITE to the observation term for sparse "
            "constellations (owner pin 245e)."
        ),
        "collinearity_caveat": (
            "⛔ THE 'CONTROLLED EXPERIMENT' PREMISE IS STRUCK (owner pin "
            "245f). With n=4 and ONE POINT PER TILE, observation count is "
            "PERFECTLY COLLINEAR with tile identity — the regression measures "
            "WHICH TILE, not HOW MANY OBSERVATIONS. There is no measurement "
            "in this repository where n_obs varies at a FIXED domain, which "
            "is the only contrast an OSSE produces."
        ),
        "domain_confound_searched_and_absent": (
            "n_coef (the basis dimension) varies with latitude through "
            "miost_sizing.n_coefficients' d_x_km/d_y_km, so a domain confound "
            "is PLAUSIBLE. It is NOT QUANTIFIED here: only kuroshio's n_coef "
            "is recorded anywhere (297600 at "
            "tier2_probe_kuroshio_m100.model_at_probe_geometry), and the "
            "other three tiles' values are SEARCHED AND ABSENT from the store "
            "and the logs (pin 60a's form). A reviewer reported per-tile "
            "values; they could not be reproduced, so they are not restated "
            "here (owner pin 247)."
        ),
    }


def model_survey(
    evidence_path: Path = EVIDENCE, seal_path: Path = SEAL
) -> dict[str, Any]:
    """Price the sweep under every defensible model and report the BAND.

    ⚖ **Owner pin 245(a).** No exponent appears in the headline. The models
    disagree by less than the tile axis does, which is why the band was
    always sufficient for a go/no-go.

    Args:
        evidence_path: Path to the evidence store.
        seal_path: Path to the sealed evaluation file.

    Returns:
        One row per model, and the band across all of them.
    """
    walls = _walls(evidence_path)
    counts = epoch_classes(seal_path)["mission_counts"]
    base = len(LEG_MISSIONS)
    diag = wall_diagnostic(evidence_path)
    p_fit = diag["raw_wall_vs_nobs_exponent"]

    models = [
        ("flat — one class = one leg (v1)", 0.0),
        ("linear in missions", 1.0),
        ("5-point refit (legs + anchor_gate)", diag["refit_with_anchor_gate"]),
        ("raw wall-vs-n_obs fit (diagnostic)", p_fit),
        ("upper 95% CI on the 4-leg fit", diag["fit_ci_95"][1]),
    ]
    rows = []
    for name, p in models:
        eq = float(len(counts)) if p == 0.0 else sum((m / base) ** p for m in counts)
        rows.append(
            {
                "model": name,
                "exponent": p,
                "leg_equivalents": eq,
                "h_at_lowest_tile": eq * min(walls.values()),
                "h_at_highest_tile": eq * max(walls.values()),
            }
        )
    lo = min(r["h_at_lowest_tile"] for r in rows)
    hi = max(r["h_at_highest_tile"] for r in rows)

    return {
        "rows": rows,
        "band_low_h": lo,
        "band_high_h": hi,
        "band_statement": (
            f"EVERY DEFENSIBLE MODEL PUTS THE FULL SWEEP IN "
            f"{lo:.0f}-{hi:.0f} h. That band is sufficient for a go/no-go, "
            "and it always was."
        ),
        "why_no_exponent_in_the_headline": (
            "The models disagree by less than the TILE axis does (1.40x). "
            "Two rounds of review were spent on the smallest term in the "
            "price (owner pin 245a)."
        ),
    }


def per_class_walls(
    evidence_path: Path = EVIDENCE, seal_path: Path = SEAL
) -> dict[str, Any]:
    """Per-class wall against the 40 h per-leg WAIT ceiling (owner pin 245c).

    ⛔ **THE DECISION-RELEVANT FACT v2 OMITTED.** v2 reported only sums.
    Pin 99(b)'s rule is a PER-LEG rule, and under the pricing models some
    classes breach it — which is a WAIT, not a line item in a total.

    Args:
        evidence_path: Path to the evidence store.
        seal_path: Path to the sealed evaluation file.

    Returns:
        Per distinct constellation size: wall at the cheapest and dearest
        tile, and the WAIT/RUN verdict at each.
    """
    walls = _walls(evidence_path)
    lo_t = min(walls, key=lambda t: walls[t])
    hi_t = max(walls, key=lambda t: walls[t])
    counts = epoch_classes(seal_path)["mission_counts"]
    base = len(LEG_MISSIONS)
    p = wall_diagnostic(evidence_path)["raw_wall_vs_nobs_exponent"]

    rows = []
    for m in sorted(set(counts)):
        scale = (m / base) ** p
        lo_h, hi_h = walls[lo_t] * scale, walls[hi_t] * scale
        rows.append(
            {
                "n_missions": m,
                "n_classes_at_this_size": counts.count(m),
                f"wall_h_at_{lo_t}": lo_h,
                f"wall_h_at_{hi_t}": hi_h,
                f"verdict_at_{lo_t}": "WAIT" if lo_h > TIER_CEILING_H else "RUN",
                f"verdict_at_{hi_t}": "WAIT" if hi_h > TIER_CEILING_H else "RUN",
            }
        )
    breach_hi = sum(
        r["n_classes_at_this_size"] for r in rows if r[f"verdict_at_{hi_t}"] == "WAIT"
    )
    breach_lo = sum(
        r["n_classes_at_this_size"] for r in rows if r[f"verdict_at_{lo_t}"] == "WAIT"
    )
    return {
        "ceiling_h": TIER_CEILING_H,
        "ceiling_authority": "owner pin 99(b) + E-16 — the PER-LEG WAIT ceiling",
        "rows": rows,
        "classes_breaching_at_cheapest_tile": breach_lo,
        "classes_breaching_at_dearest_tile": breach_hi,
        "finding": (
            f"BETWEEN {breach_lo} AND {breach_hi} OF THE 15 CLASSES BREACH THE "
            f"{TIER_CEILING_H:g} h PER-LEG CEILING depending on the tile. A "
            "breach is a WAIT under pin 99(b), not a line in a total — and v2 "
            "reported only totals (owner pin 245c)."
        ),
        "note_on_the_scale": (
            "the per-class scaling uses the DIAGNOSTIC exponent because the "
            "ceiling question needs SOME per-class figure; it inherits that "
            "diagnostic's collinearity caveat and is not a measurement"
        ),
    }


def ram_axis(evidence_path: Path = EVIDENCE) -> dict[str, Any]:
    """RAM as a NAMED, EXPLICITLY UNMODELLED axis (owner pin 245d).

    ⛔ This project has pinned this exact asymmetry before: *the RAM
    projection that was NEVER WRITTEN DOWN* — leg 1 came in at wall 0.63x and
    **RAM 1.69x** against its model. v2 gave RAM one clause in a list. It is
    the axis that has actually stopped work here.

    Args:
        evidence_path: Path to the evidence store.

    Returns:
        The measured peaks, the launch gate, the recorded incidents, and an
        explicit UNMODELLED declaration.
    """
    tiles = _stage1(evidence_path)["tiles"]
    peaks = {t: tiles[t]["peak_rss_mib"] for t in PRICED_TILES}
    return {
        "modelled": False,
        "declaration": (
            "⛔ RAM IS UNMODELLED AT CONSTELLATION SIZES OTHER THAN THE LEGS' "
            "FIVE. This is a NAMED AXIS carrying an explicit refusal to "
            "estimate, not an omission (owner pin 245d)."
        ),
        "measured_peaks_mib": peaks,
        "peak_basis_missions": len(LEG_MISSIONS),
        "launch_gate_mib": LAUNCH_GATE_MIB,
        "launch_gate_rule": "MemAvailable >= 2 x the MEASURED peak (owner pin 155)",
        "why_it_is_not_estimated": (
            "no measurement exists at any constellation size but five, and "
            "the one recorded RAM projection in this project MISSED BY 1.69x "
            "while its wall projection was 0.63x — the asymmetry pin 139(a) "
            "predicted. Estimating here would repeat that."
        ),
        "recorded_incidents": [
            "the equatorial leg was REFUSED by the launch gate at 9891.58 MiB "
            "against a 9902.33 MiB gate — a margin of 11 MiB — and relaunched "
            "at 9907.33 MiB, clearing by 5 MiB",
            "leg 2 bottomed at 1382 MiB mid-run with swap exhausted and "
            "survived by owner intervention, which is not a property the "
            "remaining legs can rely on",
        ],
        "what_would_settle_it": (
            "predicted peak RSS at 9 missions against the 9902.33 MiB gate — "
            "a go/no-go, not a magnitude"
        ),
    }


def truth_field_cost(evidence_path: Path = EVIDENCE) -> dict[str, Any]:
    """Derive the truth-field volume from the recorded STAC metadata.

    Truth is bought **once per tile**, not once per class: an OSSE varies the
    CONSTELLATION over FIXED truth. It **does** scale with tiles.

    Args:
        evidence_path: Path to the evidence store.

    Returns:
        Volumes, the scaling finding, and a DERIVED feasibility verdict.
    """
    plan = _stage1(evidence_path)["tiles"]["quiet_gyre"]["window_plan"]
    starts = plan["starts"]
    span_days = max(s + plan["w_days"] for s in starts) - min(starts)
    strides = sorted({b - a for a, b in zip(starts, starts[1:], strict=False)})

    step = TRUTH_QUERY["grid"]["step_deg"]
    item = TRUTH_QUERY["zos_item_size_bytes"]
    n_side = round(SOLVE_BBOX_DEG / step) + 1  # node-INCLUSIVE
    per_day_b = n_side * n_side * item
    one_tile_b = int(span_days * per_day_b)
    grid = TRUTH_QUERY["grid"]
    global_day_b = grid["latitude_len"] * grid["longitude_len"] * item

    all_tiles_gib = one_tile_b * len(PRICED_TILES) / 1024**3
    return {
        "measured": True,
        "query": TRUTH_QUERY,
        "variable": "zos (sea surface height) — the OSSE truth field",
        "scope_assumption": "zos only; no MDT, mask or ancillary — a nadir-SLA scope choice",
        "grid_nodes_per_side": n_side,
        "window_plan_span_days": span_days,
        "window_plan_shape": (
            f"9 windows x {plan['w_days']:.0f} d, OVERLAPPING and on a "
            f"NON-UNIFORM stride {strides} d — {9 * plan['w_days']:.0f} "
            f"window-days over a {span_days:.0f}-d union. The UNION is the "
            "download basis because each day is bought once."
        ),
        "mib_per_tile_per_span": one_tile_b / 1024**2,
        "mib_all_four_tiles": one_tile_b * len(PRICED_TILES) / 1024**2,
        "global_zos_full_record_tib": global_day_b * grid["time_len"] / 1024**4,
        "does_not_scale_with_classes": (
            "THE TRUTH FIELD IS BOUGHT ONCE PER TILE, NOT ONCE PER CLASS — an "
            "OSSE varies the CONSTELLATION over FIXED truth. It DOES scale "
            "with the number of tiles."
        ),
        "epoch_span_reading_is_unstated": (
            "⚠ OPEN: the 15 classes are DATE-RANGED in the sealed table "
            "(1992-2026) while this volume assumes ONE common 400-day truth "
            "span. Common-span means historical ground tracks must be "
            "SYNTHESISED (uncosted engineering); per-era means 15x the "
            "download (2.34 GiB for four tiles, still feasible) and the truth "
            "is no longer 'FIXED', which is the value case's own word. The "
            "run design must name which reading it takes."
        ),
        "bbox_caveat": (
            "this is the SOLVE box; simulating observations needs the OBS "
            "footprint (+1.0 deg halo = 21 deg), 1.22x larger"
        ),
        "encoding_caveat": (
            "this is the UNCOMPRESSED array size — a BOUND on wire volume, "
            "not a wire measurement"
        ),
        "feasibility": {
            "cmems_storage_budget_gib": CMEMS_BUDGET_GIB,
            "budget_row": "ladder.STAGE0_SPEND_TABLE task_class=cmems_downloads (BOX_PRODUCTION)",
            "all_four_tiles_gib": all_tiles_gib,
            "fraction_of_budget": all_tiles_gib / CMEMS_BUDGET_GIB,
            "verdict": "FEASIBLE" if all_tiles_gib <= CMEMS_BUDGET_GIB else "REFUSED",
            "derived_not_asserted": "computed from the volume against the budget",
        },
    }


def probe_cross_check(evidence_path: Path = EVIDENCE) -> dict[str, Any]:
    """Pin 89's probe, derived from the store — a cross-check, not a price.

    Args:
        evidence_path: Path to the evidence store.

    Returns:
        The projection, the measurement, and the over-prediction factor.
    """
    s1 = _stage1(evidence_path)
    wall = s1["tier2_probe_kuroshio_m100"]["derived_pin_89d"]["wall"]
    measured = s1["tiles"]["kuroshio"]["wall_s"] / 3600.0
    return {
        "role": "CROSS-CHECK ONLY — NOT A PRICE (owner pin 236b)",
        "source": "phase14.stage1.tier2_probe_kuroshio_m100.derived_pin_89d.wall",
        "projected_tile_h": wall["per_tile_h"],
        "measured_same_tile_h": measured,
        "overprediction_factor": wall["per_tile_h"] / measured,
        "note_on_1_28": (
            "⛔ the node's implied_exponent 1.28 is an exponent on GRID NODES "
            "(its anchors are labelled nodes^1.25 / nodes^1.5). v2 cited it "
            "as 'independent corroboration' of an OBSERVATION exponent. It is "
            "not: they are exponents of different variables, and the four "
            "legs hold nodes FIXED. THE CORROBORATION CLAIM IS WITHDRAWN "
            "(owner pin 246)."
        ),
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
    """Scope subsets with their limits — and NO ORDERING (owner pin 244a).

    ⛔ **THE DIRECTION CLAIM IS WITHDRAWN AND NOT RE-DERIVED.** v2 asserted
    that post-lift is dearer "under any cost monotone in observations". Cost
    is ``sum f(m_i)``; post-lift has FEWER and LARGER classes, so the
    ordering requires **f CONVEX**, and it REVERSES below p ~ 0.638.
    Convexity needs the conditioning term, which needs a measurement that
    does not exist.

    Args:
        evidence_path: Path to the evidence store.
        seal_path: Path to the sealed evaluation file.

    Returns:
        The subsets with class and mission counts and their limits, the
        withdrawal record, and no ordering claim.
    """
    table = json.loads(seal_path.read_text())["content"]["epoch_table"]
    picks: list[tuple[str, list[dict[str, Any]]]] = [
        ("full_sweep", table),
        ("fit+validate", [e for e in table if e.get("role") == "fit+validate"]),
        ("pre_lift_mask66", [e for e in table if e.get("mask_66")]),
        ("post_lift_mask66", [e for e in table if not e.get("mask_66")]),
        ("validate_only", [e for e in table if e.get("role") == "validate-only"]),
    ]
    rows = [
        {
            "subset": name,
            "n_classes": len({frozenset(e["missions"]) for e in es}),
            "total_missions": sum(len(e["missions"]) for e in es),
            "mission_counts": sorted(len(e["missions"]) for e in es),
            "elected": False,
            "cannot_establish": SUBSET_LIMITS[name],
        }
        for name, es in picks
    ]
    return {
        "rows": rows,
        "ordering": None,
        "ordering_is_WITHDRAWN": {
            "withdrawn_claim": (
                "post_lift_mask66 is DEARER than pre_lift_mask66, and this "
                "holds under ANY cost monotone in observation count"
            ),
            "why_it_is_false": (
                "cost is SUM f(m_i). post-lift has FEWER and LARGER classes "
                "(6 classes / 44 missions) than pre-lift (9 / 35), so the "
                "ordering requires f CONVEX, not merely MONOTONE. It REVERSES "
                "below p ~ 0.638: at p=0.5 pre-lift costs 17.70 and post-lift "
                "16.22 leg-equivalents."
            ),
            "the_arithmetic_error_beneath_it": (
                "the ratios that ratified it were (sum m_post / sum m_pre)**p "
                "— the exponent applied to the AGGREGATE. sum(m_i**p) is not "
                "(sum m_i)**p unless p == 1. ⭐ p=1 IS THE ONLY POINT WHERE "
                "THE TWO FORMULAS COINCIDE, and that lone agreeing figure was "
                "read as verification. THAT IS THE FINDING, not the slip "
                "(owner pin 244c)."
            ),
            "not_re_derived": (
                "⛔ NO ordering is re-derived (owner pin 244a). Convexity "
                "needs the conditioning term, which needs a measurement that "
                "does not exist. This is pin 239(c)'s discipline applied to "
                "the owner's claim as it was to the executor's: record that "
                "it is UNSETTLED; do not replace it with its opposite."
            ),
            "what_would_settle_it": (
                "one solve, one tile, one window, at a 3-mission subset of "
                "PROBE_MISSIONS, recording n_obs and PCG iterations — roughly "
                "1-2 h of compute"
            ),
        },
    }


def open_axes(
    evidence_path: Path = EVIDENCE, seal_path: Path = SEAL
) -> list[dict[str, Any]]:
    """Every axis an OSSE price depends on, NONE collapsed (owner pin 245b).

    Args:
        evidence_path: Path to the evidence store.
        seal_path: Path to the sealed evaluation file.

    Returns:
        One entry per open axis, each marked not-a-default.
    """
    walls = _walls(evidence_path)
    counts = epoch_classes(seal_path)["mission_counts"]
    return [
        {
            "axis": "which tile",
            "not_a_default": True,
            "spread": f"{max(walls.values()) / min(walls.values()):.2f}x",
            "detail": f"measured legs run {min(walls.values()):.2f}-{max(walls.values()):.2f} h",
        },
        {
            "axis": "constellation size",
            "not_a_default": True,
            "spread": f"~{(max(counts) / min(counts)) ** 1.41:.1f}x",
            "detail": f"classes run {min(counts)}-{max(counts)} missions; the legs ran {len(LEG_MISSIONS)}",
        },
        {
            "axis": "platform convention (labels vs platforms)",
            "not_a_default": True,
            "spread": "~1.28x",
            "detail": LABEL_VS_PLATFORM_NOTE,
        },
        {
            "axis": "RAM",
            "not_a_default": True,
            "spread": "UNMODELLED",
            "detail": (
                "no measurement at any constellation size but five; the one "
                "recorded RAM projection in this project missed by 1.69x"
            ),
        },
    ]


def price(evidence_path: Path = EVIDENCE, seal_path: Path = SEAL) -> dict[str, Any]:
    """Build the full OSSE pricing block (v3).

    Args:
        evidence_path: Path to the evidence store.
        seal_path: Path to the sealed evaluation file.

    Returns:
        The pricing block, decision cell EMPTY.
    """
    survey = model_survey(evidence_path, seal_path)
    classes = epoch_classes(seal_path)
    return {
        "decision": None,
        "decision_cell": "EMPTY",
        "decision_is_the_owners": (
            "PRICED, OWNER TO DECIDE — NOT 'not priced'. Every figure below "
            "is a measurement, a declared diagnostic, or an explicit refusal "
            "to estimate. What is absent is the owner's election (pin 235e)."
        ),
        "report_only": True,
        "version": "v3",
        "rebuilt_under_pin_245": (
            "v1 and v2 were both OVERTURNED on the UNIT OF ACCOUNT. v3 is "
            "SIMPLER than v1: the headline is the BAND ACROSS MODELS with no "
            "exponent in it, because every defensible model lands inside it "
            "and that was always sufficient for a go/no-go."
        ),
        "value_case_verbatim": VALUE_CASE,
        "headline_band_h": [survey["band_low_h"], survey["band_high_h"]],
        "model_survey": survey,
        "epoch_classes": classes,
        "open_axes": open_axes(evidence_path, seal_path),
        "per_class_walls": per_class_walls(evidence_path, seal_path),
        "ram_axis": ram_axis(evidence_path),
        "wall_diagnostic": wall_diagnostic(evidence_path),
        "probe_cross_check": probe_cross_check(evidence_path),
        "scope_subsets": scope_subsets(evidence_path, seal_path),
        "truth_field": truth_field_cost(evidence_path),
        "lower_bound": {
            "statement": "THE FIGURES HERE ARE A LOWER BOUND ON THE OSSE PRICE.",
            "what_is_covered": (
                "constellation-varied re-solves + the truth download, both at "
                "declared model assumptions"
            ),
            "what_is_not_costed": [
                "truth-provider wiring: the TRUTH interface is DORMANT since "
                "4b and re-arming it is unmeasured engineering time — the "
                "LARGEST open item, and it carries no number at all",
                "per-class observation simulation from the truth field",
                "scoring and analysis of 15 outputs",
                "REPLICATION: 15 classes x 1 tile x 1 truth realisation gives "
                "no way to separate 'this constellation is worse' from 'these "
                "track positions over this tile were unlucky'",
                "non-convergence retries; the legs ran 375-626 PCG iterations "
                "per window at 5 missions",
                "calendar time and box occupancy: serial single-host hours",
                "truth-field independence: GLORYS12V1 is a data-assimilative "
                "reanalysis that ingests along-track SLA from the very "
                "constellations being simulated — the fraternal-twin problem, "
                "first-order for an OSSE whose value case is 'against truth'",
            ],
        },
        "recommendation_options": [
            {
                "option": "run at Stage-2 entry (when era-transfer is the live question)",
                "cost": "same compute; truth download trivial either way",
                "can_establish": (
                    "the era-transfer claim against truth where it becomes load-bearing"
                ),
                "cannot_establish": "anything for Gate 1 — it closes no Stage-1 item",
            },
            {
                "option": "run now",
                "cost": (
                    f"{survey['band_low_h']:.0f}-{survey['band_high_h']:.0f} h "
                    "across all defensible models, + the truth download"
                ),
                "can_establish": "the same thing, earlier",
                "cannot_establish": (
                    "any Gate-1 item — the OSSE is not a Gate-1 deliverable, "
                    "and Gate 1 already carries two ruled WAITs"
                ),
            },
        ],
        "citations": [
            "owner pin 99(c) — price from CONVERGED numbers, basis in-row",
            "owner pin 232 — standalone doc + witnessed node; posted pack untouched",
            "owner pin 234 — N_epoch-classes derived; no deduplication",
            "owner pin 237 — the STAC metadata query, authorised and recorded",
            "owner pin 244 — the direction claim WITHDRAWN, not re-derived",
            "owner pin 245 — v3 simpler than v1: the band, every axis open",
            "owner pin 247 — agent output is data, not fact",
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
    typer.echo(block["model_survey"]["band_statement"])
    for r in block["model_survey"]["rows"]:
        typer.echo(
            f"  {r['model']:<38} {r['h_at_lowest_tile']:6.1f}-"
            f"{r['h_at_highest_tile']:6.1f} h"
        )
    pcw = block["per_class_walls"]
    typer.echo(f"\n  {pcw['finding']}")
    d = block["wall_diagnostic"]
    lo, hi = d["microseconds_per_obs_iteration_span"]
    typer.echo(
        f"  diagnostic: {lo:.1f}-{hi:.1f} us per obs-iteration "
        f"(+/-{d['spread_pct']:.1f}%) — wall ~ linear in obs x iterations"
    )
    typer.echo(f"  subset ordering: {block['scope_subsets']['ordering']} (WITHDRAWN)")
    typer.echo(f"  RAM: modelled={block['ram_axis']['modelled']}")
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
