"""Phase-14 Stage-1 per-tile run driver (Stage-1 Task 1 — CI-testable core).

ONE command runs one roster tile: frame from the registry, source-mapped
load (the Stage-0 pin-4 source map — per-tile source is REGISTRY
provenance, never a CLI option), frozen signed config, evidence row under
``phase14.stage1.tiles.<tile>`` quoting the seal sha.

THIS module ships the CI-testable core plus the Task-2 measured-first
``probe`` command (quiet_gyre, ONE 60-day window, m=1, PROBE-labeled,
record-then-stop 1.3x bracket) and the owner PIN-26(c) ``seam-probe``
command (seam_n, ONE production window, m=1, cap 2000 — a convergence
measurement on the frames T4 solves, taken BEFORE T4 is spent, because
``seam_read`` REFUSES on residual > rtol). The remaining real load/solve/score legs
are separately gated Stage-1 tasks (3 anchor gate / 4 seam pair /
5 diverse tiles) and land behind :func:`_solve_leg`.

Standing refusals wired here:

- **Diverse-frame convention (plan pin 2, RULED 2026-07-25):**
  production-representative — see :data:`DIVERSE_FRAME_CONVENTION`. The
  refusal MECHANISM stays: while the constant is ``None`` (unruled) the
  four diverse frames REFUSE. (Pin 12, the equatorial box, was ruled the
  same day: box KEPT — the ``run`` refusal is gone.)
- **Tier-1 ladder (fork-g pin 4):** :func:`preflight` sizes the tile and
  checks ``tier1_eligible`` BEFORE any load — never launch over headroom.
- **Seal tripwire (Task 10):** :func:`record_evidence_row` verifies the
  current seal before anything is written.
"""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer

if TYPE_CHECKING:
    from collections.abc import Iterable
    from types import ModuleType

    import numpy as np
    from numpy.typing import ArrayLike, NDArray

    from sverdrup.adapters.altimetry.contract import BBox
    from sverdrup.application.spatial_tiles import TileFrame
    from sverdrup.core.grid import GridSpec
    from sverdrup.validation.seam_metrics import SeamRead

app = typer.Typer(add_completion=False)

EVIDENCE = Path("data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json")
STAGE1_DIR = Path("data/2021a_ssh_mapping_ose/ours/phase14_stage1")
RESOLUTION_DEG = 0.2

# Task 2 — the measured-first sizing probe (plan Task 2, gated on the pin-2
# ruling which landed 2026-07-25). Window start/length follow the Stage-0
# probe convention: 2017-01-15 in days-since-2017-01-01, one 60-day window.
PROBE_TILE = "quiet_gyre"
PROBE_M = 1
PROBE_W_START = 14.0
PROBE_W_DAYS = 60.0
PROBE_STOP_THRESHOLD = 1.3
# Production PCG iteration cap — MUST equal miost_solver.PCG_MAXITER
# (test-pinned; stated locally so the CLI default needs no heavy import at
# module scope). Owner PIN 23(a)+(c): the T2 probe ran BOTH legs into this
# cap over rtol, so its wall was bounded above by 500 x per-iteration cost
# — the bracket could only ever report "model conservative". The probe now
# takes --maxiter, records the cap in-row, and flags CAPPED measurements.
PROBE_MAXITER_DEFAULT = 500
# The PIN-23(a) converged re-run node. The ORIGINAL T2 row at
# phase14.stage1.probe stays as history — never rewritten.
PROBE_CONVERGED_NODE = "probe_converged"
# The frozen five-mission mapping config (j3 stays the holdout convention);
# CMEMS-MY directory codes (h2g -> h2ag on this source).
PROBE_MISSIONS = ("alg", "h2ag", "j2g", "j2n", "s3a")
# The same five missions on the dc2021a challenge source (its own codes).
DC_MAPPING_FIVE = ("alg", "h2g", "j2g", "j2n", "s3a")

# ---------------------------------------------------------------------------
# Owner PIN 26(b) — the Stage-1 PRODUCTION PCG cap, SET FROM MEASUREMENT.
#
# Derivation (all numbers measured, none assumed):
#   * The converged 19-degree probe (phase14.stage1.probe_converged, run at
#     maxiter 2000) needed 524 iterations on the mean leg and 554 on the
#     MEMBER-BATCH leg. 554 is the measured worst leg.
#   * Owner rule: the production cap is >= 2x the measured requirement, so
#     the floor is 1108. Chosen: 1200 (the next round number above it).
#   * The library default PCG_MAXITER = 500 is DELIBERATELY left alone: the
#     signed-identity paths re-solve at the SIGNED cap and their behavior
#     is not re-proven here. The driver passing an explicit cap is the safe
#     form (pin 26(b)).
#
# Wall consequence, stated in the same breath (per-iteration cost from the
# same converged probe: 603.1 s / 1078 iterations = 0.56 s/iter at the 19-
# degree solve geometry, m=1):
#   * IF a leg ever ran all the way to this cap it would cost
#     1200 x 0.56 s = 672 s ~ 11.2 min; a window is two legs (mean +
#     member-batch), so ~22.4 min/window, and a full T5 (4 tiles x 9
#     windows) that capped EVERYWHERE would cost ~13.4 h.
#   * At the MEASURED iteration counts the same T5 costs ~6.0 h (36 windows
#     x 1078 iters x 0.56 s) — the cap buys ~2x headroom, it does not spend
#     it. A cap is a ceiling on the bad case, not a bill.
#   * Both wall figures are FLOORS: 0.56 s/iter was measured at m=1, and the
#     production member-batch leg solves m=100 right-hand sides per blocked
#     iteration.
#
# PIN 26(d): the MEMBER-BATCH leg is the worst-converging leg in every
# measurement taken (probe 554 vs 524; anchor 396-459 vs 342-422) and T10's
# sigma field kind is built on it — margins are set by that leg.
STAGE1_PCG_MAXITER = 1200

# Owner PIN 26(c) — the SEAM-FRAME convergence probe. The seam frames are
# SMALLER than the anchor (51x37 = 1887 solve-grid nodes vs 51x52 = 2652)
# and very likely converge cheaply, but ``seam_read`` REFUSES on residual >
# rtol, so an unmeasured cap costs the whole T4 spend AFTER the fact. ONE
# seam frame, m=1, ONE window, cap raised to 2000 so the probe can report a
# requirement instead of a cap. PROBE-labeled, no scores.
SEAM_PROBE_TILE = "seam_n"
SEAM_PROBE_M = 1
SEAM_PROBE_MAXITER = 2000
SEAM_PROBE_NODE = "seam_convergence_probe"
# The first PRODUCTION window (WindowPlan default k=0) — the probe measures
# a window T4 actually solves, never a probe-only placement.
SEAM_PROBE_W_INDEX = 0
# Launch gate (the anchor gate's convention): MemAvailable >= 2 x predicted
# peak, measured at call time — never a constant.
SEAM_RAM_GATE_FACTOR = 2.0
# CMEMS-MY obs times are days since 1993-01-01; the solver frame is days
# since 2017-01-01 (the Stage-0 probe's rebase constant).
_DAYS_1993_TO_2017 = 8766.0

# Probe-pinned smallest wavelength for the Task-22 sizing arithmetic
# (plan Task 15 probe leg; no canonical constant exists for it). The
# direction count is NOT restated here — preflight imports the frozen
# config's canonical N_DIR from miost_basis.
_SIZING_LAM_MIN_KM = 80.0

# The Stage-1 tile roster (owner-endorsed; boxes are NOT re-litigated here).
TILES: dict[str, dict[str, Any]] = {
    "anchor": {
        "frame": "anchor",  # resolved to anchor_frame()
        "source": "dc2021a",
        "job": "identity gate (degenerate single tile)",
    },
    "seam_n": {
        "core": (295.0, 305.0, 38.0, 43.0),
        "source": "dc2021a",
        "missing_neighbors": frozenset({"W", "E", "N"}),
        "job": "seam ORACLE north half (seam at 38.0N)",
    },
    "seam_s": {
        "core": (295.0, 305.0, 33.0, 38.0),
        "source": "dc2021a",
        "missing_neighbors": frozenset({"W", "E", "S"}),
        "job": "seam ORACLE south half (seam at 38.0N)",
    },
    "equatorial": {
        "core": (200.0, 215.0, -4.0, 11.0),
        "source": "cmems_my",
        # Pin 12 — owner-ruled 2026-07-25: box KEPT. "in-band coverage is
        # the primary job; shifting north moves the equator/TIW band toward
        # the core edge where blend effects are worst".
        "job": "in-band core crossing the 10N component edge (fork-b pin 4)",
    },
    "southern": {
        "core": (215.0, 230.0, -62.0, -47.0),
        "source": "cmems_my",
        "job": (
            "high-latitude honesty instrument (~54.5S center; "
            "obs southern edge = solve_bbox.lat_min - halo; "
            "+/-66 headroom set by the pin-2 convention)"
        ),
    },
    "quiet_gyre": {
        "core": (255.0, 270.0, -30.0, -15.0),
        "source": "cmems_my",
        "job": "low-signal regime (SE Pacific subtropics)",
    },
    "kuroshio": {
        "core": (132.0, 147.0, 28.0, 43.0),
        "source": "cmems_my",
        "job": "coastal/island-dense WBJ - exercises land mask",
    },
}

# Plan pin 2 — OWNER-RULED 2026-07-25: PRODUCTION-REPRESENTATIVE. The four
# diverse tiles (equatorial/southern/quiet_gyre/kuroshio) build with the
# 2-degree overlap extension on ALL sides (missing_neighbors empty — every
# side has a notional neighbor). Ruling rationale, recorded verbatim:
# "owner-ruled 2026-07-25: the probe re-grounds sizing for Stage 2/2G,
# which flies this geometry; accepted cost 1.59x nodes; SO +/-66 headroom
# tightens to halo <= 2.0 deg (Gate-1 kernel decision inherits)".
# The refusal mechanism stays: while None, building their frames REFUSES.
DIVERSE_FRAME_CONVENTION: str | None = "production-representative"

# Review pin 7 — VERBATIM on every cmems_my row: the golden-tile bridge
# delta carries its own provenance and disclaims transfer to other tiles.
BRIDGE_CAVEAT = (
    "cross-lineage reading; golden-tile bridge delta MEASURED ON THE ANCHOR "
    "BOX (mu -0.012457 their_eval-scale, map RMS 4.10 cm); its magnitude at "
    "THIS tile is unmeasured; interpretation WAITS on the owner attribution "
    "readout"
)

# ---------------------------------------------------------------------------
# Owner pin 90 (ruling doc PART 20, 2026-08-01) — T5 ACCEPTANCE CRITERION 8,
# DISCHARGED BY THE PIN-12 RULING.
#
# The criterion asks the programmatic path (record_evidence_row for tile
# "equatorial") to REFUSE while box_election_pending. It was written while the
# election was open. The election closed 2026-07-25 (box KEPT, -4..11N), no
# such state exists in this module, and NO NEW STATE IS TO BE CREATED — pin 42
# refuses a gate that cannot fire, and a permanently-False flag is that exact
# object.
#
# Recorded the way the anchor gate records SPEC §10 check 3 (ERA_NOOP_* in
# phase14_anchor_gate.py): a criterion whose specified mechanism became
# unrunnable is recorded HONESTLY, with what was run in its place NAMED —
# never as "met", never as "dropped" (pin 90d).
#
# The citations are load-bearing, not decorative: test_criterion8_discharge_
# cites_live_tests fails if a cited test is renamed or deleted, so the
# discharge cannot rot into a claim pointing at nothing (pin 90a).
CRITERION_8_DISCHARGE: dict[str, Any] = {
    "criterion": (
        "T5 acceptance criterion 8 (pin-12 gate breadth): the equatorial "
        "election gate must also cover the programmatic path "
        '(record_evidence_row for tile "equatorial" refuses while '
        "box_election_pending), not only the CLI run entry — test-pinned"
    ),
    "status": "DISCHARGED_BY_RULING",
    "ruling": "docs/superpowers/2026-07-27-owner-ruling-crn-sigma-rule0.md",
    "pin": "90 (PART 20); the pin-12 election closed 2026-07-25",
    "dead_half": (
        "the REFUSAL. There is no box_election_pending state and none is to "
        "be created: pin 42 bars a gate that cannot fire. The criterion's "
        "refusal clause outlived its own premise when the owner ruled the "
        "box KEPT"
    ),
    "live_half": (
        "the BREADTH. Criterion 8's actual concern was CLI-only coverage, "
        "and that is still live: record_evidence_row for tile 'equatorial' "
        "must be exercised on the REAL path once the production solve leg "
        "exists, rather than at the NotImplementedError stub (pin 90c)"
    ),
    "live_half_deferred_to": "_solve_leg (T5b)",
    "evidence_tests": (
        "test_run_equatorial_reaches_gated_stub_after_pin12_ruling",
        "test_equatorial_frame_is_the_pin12_ruled_box",
    ),
    "why_two_tests": (
        "the first proves the pin-12 gate is GONE; the second proves the box "
        "that SURVIVED is the one the owner ruled. Different facts, both "
        "load-bearing — the whole point of keeping -4..11N was in-band "
        "coverage, and a later frame edit would pass the first test silently "
        "(pin 90b)"
    ),
    "never_recorded_as": ("met", "dropped"),
}


def registry_frame(tile: str) -> TileFrame:
    """The registry tile's frame — anchor CONSUMED, seams pinned, diverse gated.

    The anchor entry resolves to the EXISTING :func:`anchor_frame` (review
    pin 1: consumed, never reconstructed — a rebuilt ``TileFrame(core, 2.0,
    halo)`` would widen the signed 51x52 substrate to 71x72 nodes). Seam
    tiles build 2-degree-overlap frames open ONLY toward the 38N seam.

    Args:
        tile: Registry tile name.

    Returns:
        The tile's :class:`TileFrame`.

    Raises:
        KeyError: Unknown tile name.
        RuntimeError: Diverse tile while the frame convention election
            (plan pin 2) is pending.
    """
    from sverdrup.adapters.altimetry.contract import BBox  # noqa: PLC0415
    from sverdrup.application.spatial_tiles import (  # noqa: PLC0415
        OVERLAP_DEG,
        TileFrame,
        anchor_frame,
        operative_halo_deg,
    )

    spec = TILES.get(tile)
    if spec is None:
        raise KeyError(f"unknown tile {tile!r}; known: {sorted(TILES)}")
    if spec.get("frame") == "anchor":
        return anchor_frame()
    missing = spec.get("missing_neighbors")
    if missing is None:
        if DIVERSE_FRAME_CONVENTION is None:
            raise RuntimeError(
                f"tile {tile!r}: the diverse-tile missing_neighbors "
                "convention is an OWNER ELECTION PENDING (plan pin 2) — "
                "building this frame REFUSES until the owner rules "
                '"isolated" vs "production-representative"'
            )
        if DIVERSE_FRAME_CONVENTION != "production-representative":
            raise RuntimeError(
                f"unrecognized DIVERSE_FRAME_CONVENTION "
                f"{DIVERSE_FRAME_CONVENTION!r} — the 2026-07-25 ruling is "
                '"production-representative"'
            )
        # Ruled pin 2: all sides have notional neighbors — the solve bbox
        # extends by the overlap on every side.
        missing = frozenset()
    return TileFrame(
        core=BBox(*spec["core"]),
        overlap_deg=OVERLAP_DEG,
        halo_deg=operative_halo_deg(),
        missing_neighbors=missing,
    )


def preflight(tile: str, m: int) -> dict[str, float]:
    """Size the tile solve and run the Tier-1 predicate BEFORE any load.

    Task-22 arithmetic at the tile's geometry (fork-g pin 4: the ladder
    check comes FIRST — never launch over measured headroom). NO data is
    touched: the per-window obs count is estimated from the box basis by
    solve-area ratio; the measured probe (Stage-1 Task 2) re-grounds it.

    Args:
        tile: Registry tile name.
        m: Ensemble members retained.

    Returns:
        The ``size_tile`` model dict (peak, nnz, wall estimate, ...).

    Raises:
        RuntimeError: Predicted peak fails the Tier-1 ladder predicate.
    """
    from sverdrup.application import ladder  # noqa: PLC0415
    from sverdrup.application.spatial_tiles import frame_grid  # noqa: PLC0415
    from sverdrup.methods.miost import PHASE13_WINNER_PARAMS  # noqa: PLC0415
    from sverdrup.methods.miost_basis import N_DIR  # noqa: PLC0415
    from sverdrup.methods.miost_sizing import (  # noqa: PLC0415
        BOX_LAT,
        BOX_LON,
        BOX_W0_OBS_BASIS,
        KM_PER_DEG,
        size_tile,
    )
    from sverdrup.methods.miost_windows import WindowPlan  # noqa: PLC0415

    frame = registry_frame(tile)
    grid = frame_grid(frame, RESOLUTION_DEG)
    solve = frame.solve_bbox
    mid_lat = 0.5 * (solve.lat_min + solve.lat_max)
    d_x_km = (
        (solve.lon_max - solve.lon_min) * KM_PER_DEG * math.cos(math.radians(mid_lat))
    )
    d_y_km = (solve.lat_max - solve.lat_min) * KM_PER_DEG
    box_area_deg2 = (BOX_LON[1] - BOX_LON[0]) * (BOX_LAT[1] - BOX_LAT[0])
    tile_area_deg2 = (solve.lon_max - solve.lon_min) * (solve.lat_max - solve.lat_min)
    # Deg^2-area scaling UNDERSTATES high-latitude obs density: meridian
    # convergence packs ground tracks by ~1/cos(lat) (~35-70% more obs per
    # deg^2 at the southern tile than this estimate assumes). Acceptable
    # only because Task 2's measured-first probe re-grounds the estimate
    # BEFORE any high-latitude preflight goes live.
    n_obs_est = int(BOX_W0_OBS_BASIS * tile_area_deg2 / box_area_deg2)
    plan = WindowPlan()
    model = size_tile(
        d_x_km=d_x_km,
        d_y_km=d_y_km,
        n_grid_nodes=int(grid.x.size * grid.y.size),
        window_days=plan.w_days,
        n_windows=len(plan.windows),
        m_members=m,
        n_obs=n_obs_est,
        alpha=float(PHASE13_WINNER_PARAMS["spacing_alpha"]),
        n_dir=N_DIR,
        lam_min=_SIZING_LAM_MIN_KM,
    )
    if not ladder.tier1_eligible(model["peak_model_mib"]):
        raise RuntimeError(
            f"tile {tile!r}: predicted peak {model['peak_model_mib']:.0f} "
            "MiB fails the Tier-1 measured-RAM ladder predicate (fork-g "
            "pin 4) — the run WAITS; never launch over headroom"
        )
    return model


def classify_pcg_legs(
    pcg: Iterable[dict[str, Any]], *, rtol: float, maxiter: int
) -> tuple[list[dict[str, Any]], bool]:
    """Stamp rtol/maxiter onto COPIES of the legs; say whether the row capped.

    The ONE convergence classifier for this driver (owner PIN 26(a)): the
    probe path, the seam-probe path and the production tile path all route
    through it, so a capped leg is classified identically wherever it is
    measured. A leg is CAPPED when it exited AT (or above) the iteration
    cap with its final relative residual STRICTLY above rtol — a leg that
    reaches the cap but meets rtol converged, it was not capped.

    Stamping is done on copies because the real callers pass the live
    ``miost.CONVERGENCE_LOG`` entries; mutating those would corrupt the
    shared diagnostic log for every later solve in the process.

    Args:
        pcg: Per-leg convergence rows (``iterations`` and
            ``final_rel_residual`` required per leg).
        rtol: The solver rtol ACTUALLY used.
        maxiter: The solver iteration cap ACTUALLY used.

    Returns:
        ``(stamped_rows, capped)``. An empty leg list is ``([], False)``:
        it makes no cap claim (callers that require legs check for them —
        see :func:`seam_probe`).
    """
    rows = [{**leg, "rtol": rtol, "maxiter": maxiter} for leg in pcg]
    capped = any(
        int(leg["iterations"]) >= maxiter and float(leg["final_rel_residual"]) > rtol
        for leg in rows
    )
    return rows, capped


def build_evidence_row(
    *,
    seal_sha: str,
    tile: str,
    frame: dict[str, Any],
    window_plan: dict[str, Any],
    m: int,
    superobs_cfg: dict[str, Any] | None,
    n_obs: int,
    wall_s: float,
    peak_rss_mib: float,
    pcg: Iterable[dict[str, Any]],
    pcg_rtol: float,
    pcg_maxiter: int,
    scores: dict[str, Any],
    date: str,
) -> dict[str, Any]:
    """Assemble one Stage-1 evidence row — a PURE function, schema pinned.

    Source, bridge caveat and reference row are DERIVED from the registry:
    ``bridge_caveat`` is the verbatim review-pin-7 string on cmems_my
    tiles (None on dc2021a); ``reference_row`` marks every non-anchor
    tile's scores REFERENCE-ONLY (raw-sigma + scalar-s* transfer). No
    free-prose field exists. Fresh containers every call — callers may
    mutate their row without corrupting the next one.

    Owner PIN 26(a): the PRODUCTION row carries the same convergence shape
    the probe row carries — every pcg leg stamped with the rtol/cap it
    actually ran under, a ``convergence`` verdict, and
    ``scores.capped_measurement`` mirroring it so a capped measurement is
    labeled where its numbers are read. Both paths route through
    :func:`classify_pcg_legs` — one classifier, never two.

    Args:
        seal_sha: The verified evaluation-seal sha the row quotes.
        tile: Registry tile name.
        frame: Frame provenance block (core/overlap/halo/missing sides).
        window_plan: Window-plan provenance block.
        m: Ensemble members retained.
        superobs_cfg: The applied super-obs cfg (cmems side) or None.
        n_obs: Framed observation count.
        wall_s: Measured wall time [s].
        peak_rss_mib: Measured peak RSS [MiB].
        pcg: Per-window PCG convergence rows (``iterations`` and
            ``final_rel_residual`` required per leg).
        pcg_rtol: The solver rtol ACTUALLY used (stamped per leg).
        pcg_maxiter: The solver iteration cap ACTUALLY used (stamped per
            leg — never a restated constant).
        scores: The per-tile scores block.
        date: ISO date string (passed in — purity).

    Returns:
        The evidence row (exactly the pinned key set).

    Raises:
        KeyError: Unknown tile name.
    """
    spec = TILES.get(tile)
    if spec is None:
        raise KeyError(f"unknown tile {tile!r}; known: {sorted(TILES)}")
    source = str(spec["source"])
    pcg_rows, capped = classify_pcg_legs(pcg, rtol=pcg_rtol, maxiter=pcg_maxiter)
    reference_row = (
        None
        if tile == "anchor"
        else {
            "kind": "raw-sigma + scalar-s* transfer",
            "label": "REFERENCE-ONLY, NOT CALIBRATED",
        }
    )
    return {
        "seal_sha": seal_sha,
        "tile": tile,
        "source": source,
        "frame": frame,
        "window_plan": window_plan,
        "m": m,
        "superobs_cfg": superobs_cfg,
        "n_obs": n_obs,
        "wall_s": wall_s,
        "peak_rss_mib": peak_rss_mib,
        "pcg": pcg_rows,
        "convergence": "CAPPED" if capped else "CONVERGED",
        "scores": {**scores, "capped_measurement": capped},
        "reference_row": reference_row,
        "bridge_caveat": BRIDGE_CAVEAT if source == "cmems_my" else None,
        "label": "STAGE1-EVIDENCE",
        "date": date,
    }


def record_evidence_row(row: dict[str, Any], evidence_path: Path = EVIDENCE) -> None:
    """Record one row under ``phase14.stage1.tiles.<tile>`` — seal-gated.

    Verifies the CURRENT evaluation seal FIRST (the Task-10 ceremony
    tripwire): while no verified seal exists, nothing is written and the
    :class:`~sverdrup.validation.phase14_seal.SealError` propagates. The
    write is atomic and merges into the standing store (never clobbers).

    Args:
        row: An evidence row from :func:`build_evidence_row`.
        evidence_path: The evidence store (tmp path in tests).

    Raises:
        sverdrup.validation.phase14_seal.SealError: No verified seal.
    """
    from sverdrup.application.calibration.harness import (  # noqa: PLC0415
        atomic_write_json,
    )
    from sverdrup.validation import phase14_seal  # noqa: PLC0415

    phase14_seal.verify_current_seal()
    results: dict[str, Any] = (
        json.loads(evidence_path.read_text()) if evidence_path.exists() else {}
    )
    node = results.setdefault("phase14", {}).setdefault("stage1", {})
    node.setdefault("tiles", {})[str(row["tile"])] = row
    atomic_write_json(evidence_path, results)


def build_probe_row(
    *,
    frame: dict[str, Any],
    window: list[float],
    superobs_cfg: dict[str, Any] | None,
    n_obs: int,
    n_grid_nodes: int,
    wall_s: float,
    peak_rss_mib: float,
    pcg: list[dict[str, Any]],
    pcg_rtol: float,
    pcg_maxiter: int,
    model: dict[str, float],
    date: str,
) -> dict[str, Any]:
    """Assemble the Task-2 probe evidence row — PURE, schema pinned.

    The probe is a SIZING measurement, never an evaluation: there is NO
    scores block (a probe row with a µ would be an evaluation-bearing
    artifact) and ``m`` is pinned to 1. ``measured_vs_model`` carries the
    measured/model ratios; ``stop_bracket`` trips when EITHER ratio
    STRICTLY exceeds the 1.3x honest-bracket convention.

    Owner PIN 23(c): every pcg leg is stamped (on a COPY — the caller's
    dicts are the live miost ``CONVERGENCE_LOG`` entries) with the solver's
    ``rtol``/``maxiter``, and the row carries a ``convergence`` verdict —
    ``"CAPPED"`` when ANY leg exited AT the cap with residual still above
    rtol (its wall is bounded above by cap x per-iteration cost, so its
    ratios can only under-report). ``measured_vs_model.capped_measurement``
    mirrors the verdict so a capped ratio is labeled where it appears.
    The stamping and the verdict come from :func:`classify_pcg_legs` — the
    SAME classifier the production tile rows use (owner PIN 26(a)).

    Args:
        frame: Frame provenance block (core/overlap/halo/solve bbox).
        window: ``[start, end]`` in solver days (since 2017-01-01).
        superobs_cfg: The applied super-obs cfg (cmems side).
        n_obs: In-window (support-widened) observation count — the same
            count fed to the sizing model.
        n_grid_nodes: Solve grid node count.
        wall_s: Measured wall time [s].
        peak_rss_mib: Measured peak RSS [MiB].
        pcg: Per-window PCG convergence rows (``iterations`` and
            ``final_rel_residual`` required per leg).
        pcg_rtol: The solver rtol ACTUALLY used (stamped per leg).
        pcg_maxiter: The solver iteration cap ACTUALLY used (stamped per
            leg — never a restated constant).
        model: The ``size_tile`` output at the probe's own geometry.
        date: ISO date string (passed in — purity).

    Returns:
        The probe row (exactly the pinned key set).
    """
    wall_ratio = wall_s / model["wall_est_s"]
    peak_ratio = peak_rss_mib / model["peak_model_mib"]
    pcg_rows, capped = classify_pcg_legs(pcg, rtol=pcg_rtol, maxiter=pcg_maxiter)
    return {
        "label": "PROBE",
        "tile": PROBE_TILE,
        "source": str(TILES[PROBE_TILE]["source"]),
        "frame": frame,
        "window": window,
        "m": PROBE_M,
        "superobs_cfg": superobs_cfg,
        "n_obs": n_obs,
        "n_grid_nodes": n_grid_nodes,
        "wall_s": wall_s,
        "peak_rss_mib": peak_rss_mib,
        "pcg": pcg_rows,
        "convergence": "CAPPED" if capped else "CONVERGED",
        "model": model,
        "measured_vs_model": {
            "wall_ratio": wall_ratio,
            "peak_ratio": peak_ratio,
            "capped_measurement": capped,
        },
        "stop_bracket": {
            "threshold": PROBE_STOP_THRESHOLD,
            "tripped": (
                wall_ratio > PROBE_STOP_THRESHOLD or peak_ratio > PROBE_STOP_THRESHOLD
            ),
        },
        "date": date,
    }


def record_probe_row(
    row: dict[str, Any], evidence_path: Path = EVIDENCE, node: str = "probe"
) -> None:
    """Record the probe row under ``phase14.stage1.<node>`` — seal-gated.

    Same ceremony as :func:`record_evidence_row`: the CURRENT seal is
    verified FIRST (Task-10 tripwire — nothing is written while no
    verified seal exists), then an atomic merge into the standing store.
    The PIN-23(a) converged re-run records at
    :data:`PROBE_CONVERGED_NODE` so the original T2 row at ``probe``
    stays as history.

    Args:
        row: The probe row from :func:`build_probe_row`.
        evidence_path: The evidence store (tmp path in tests).
        node: The stage1 store key (``"probe"`` for the historical T2
            leg; ``"probe_converged"`` for the PIN-23(a) re-run).

    Raises:
        sverdrup.validation.phase14_seal.SealError: No verified seal.
    """
    from sverdrup.application.calibration.harness import (  # noqa: PLC0415
        atomic_write_json,
    )
    from sverdrup.validation import phase14_seal  # noqa: PLC0415

    phase14_seal.verify_current_seal()
    results: dict[str, Any] = (
        json.loads(evidence_path.read_text()) if evidence_path.exists() else {}
    )
    results.setdefault("phase14", {}).setdefault("stage1", {})[node] = row
    atomic_write_json(evidence_path, results)


def _probe_solve(
    maxiter: int = PROBE_MAXITER_DEFAULT,
    tile: str = PROBE_TILE,
    m: int = PROBE_M,
) -> dict[str, Any]:
    """The Task-2 measured leg: load, one-window solve, PROBE map, measure.

    Follows the Stage-0 tile-sizing probe pattern (`phase14_probe.py`):
    CMEMS load clipped to the frame's obs bbox, challenge-coarsen
    super-obs, ObsWindow rebuild into the solver frame, ``Miost`` with the
    solve bbox as km-plane basis domain, single-window plan, m=1 merged
    members, one mid-window mean day. The sizing model is computed at the
    probe's OWN geometry (one window, m=1, measured in-window obs count)
    so the recorded ratios compare like with like. Constants are NOT
    retuned here (the Phase-12 precedent — ratios recorded only).

    Args:
        maxiter: PCG iteration cap passed to the solver (owner PIN 23(a):
            the re-run raises it until the solve CONVERGES to rtol). The
            recorded ``pcg_rtol``/``pcg_maxiter`` are read back off the
            method so the row records what was actually used.
        tile: Registry tile to probe. DEFAULTS to the T2 subject, so the
            Task-2 row is byte-for-byte the same call it always was.
        m: Members to solve. DEFAULTS to the T2 value. Owner pin 89 runs
            this at m=100 on ``kuroshio`` to MEASURE the axis the Tier-2
            ceiling decision actually turns on — the T2 defaults are
            untouched by that.

    Returns:
        Measurement kwargs for :func:`build_probe_row` (all but ``date``).
    """
    import resource  # noqa: PLC0415
    import time  # noqa: PLC0415

    import numpy as np  # noqa: PLC0415

    import sverdrup.methods.miost as miost_mod  # noqa: PLC0415
    from sverdrup.adapters.altimetry import apply_superobs  # noqa: PLC0415
    from sverdrup.adapters.altimetry.cmems_my import CmemsMySource  # noqa: PLC0415
    from sverdrup.application.spatial_tiles import (  # noqa: PLC0415
        frame_grid,
        frame_obs,
    )
    from sverdrup.core.observations import (  # noqa: PLC0415
        DiagonalErrorModel,
        ObsWindow,
    )
    from sverdrup.core.parameters import ConstantProvider  # noqa: PLC0415
    from sverdrup.core.seeding import derive_seed  # noqa: PLC0415
    from sverdrup.distributions.miost_ensemble import (  # noqa: PLC0415
        mean_fields,
        merged_members,
    )
    from sverdrup.methods.miost import PHASE13_WINNER_PARAMS, Miost  # noqa: PLC0415
    from sverdrup.methods.miost_basis import N_DIR, lonlat_to_km  # noqa: PLC0415
    from sverdrup.methods.miost_sizing import size_tile  # noqa: PLC0415
    from sverdrup.methods.miost_windows import WindowPlan  # noqa: PLC0415
    from sverdrup.validation.params import (  # noqa: PLC0415
        COARSEN_TIME,
        OBS_NOISE_VARIANCE,
    )

    frame = registry_frame(tile)
    grid = frame_grid(frame, RESOLUTION_DEG)
    n_nodes = int(grid.x.size * grid.y.size)

    src = CmemsMySource()
    obs_93 = src.load(
        frame.obs_bbox(resolution_deg=RESOLUTION_DEG),
        np.datetime64("2016-12-20"),
        np.datetime64("2017-04-10"),
        missions=PROBE_MISSIONS,
    )
    superobs_cfg: dict[str, Any] = {"kind": "challenge-coarsen", "n": COARSEN_TIME}
    obs_93 = apply_superobs(obs_93, cfg=superobs_cfg)
    c = obs_93.coords()
    obs = ObsWindow.from_arrays(
        c[:, 0],
        c[:, 1],
        c[:, 2] - _DAYS_1993_TO_2017,  # -> days since 2017-01-01 (solver frame)
        obs_93.values(),
        DiagonalErrorModel(np.full(len(obs_93), OBS_NOISE_VARIANCE)),
        mission=obs_93.mission,
    )
    framed = frame_obs(obs, frame, resolution_deg=RESOLUTION_DEG)

    solve = frame.solve_bbox
    xs, ys = lonlat_to_km(
        np.array([solve.lon_min, solve.lon_max]),
        np.array([solve.lat_min, solve.lat_max]),
    )
    x0, y0 = float(xs[0]), float(ys[0])
    x1, y1 = float(xs[1]), float(ys[1])
    t = framed.coords()[:, 2]
    # One window's support span (the Stage-0 probe's mask convention).
    in_window = (t >= PROBE_W_START - 12.0) & (t <= PROBE_W_START + 72.0)
    n_obs_window = int(in_window.sum())

    model = size_tile(
        d_x_km=float(x1 - x0),
        d_y_km=float(y1 - y0),
        n_grid_nodes=n_nodes,
        window_days=PROBE_W_DAYS,
        n_windows=1,
        m_members=m,
        n_obs=n_obs_window,
        alpha=float(PHASE13_WINNER_PARAMS["spacing_alpha"]),
        n_dir=N_DIR,
        lam_min=_SIZING_LAM_MIN_KM,
    )

    method = Miost(
        basis_domain=(float(x0), float(y0), float(x1 - x0), float(y1 - y0)),
        pcg_maxiter=maxiter,
    )
    method._plan = WindowPlan(starts=(PROBE_W_START,))  # noqa: SLF001
    provider = ConstantProvider(dict(PHASE13_WINNER_PARAMS))
    root = derive_seed("miost", "phase14-stage1-probe", tile, 0)
    log_start = len(miost_mod.CONVERGENCE_LOG)
    t_wall = time.monotonic()
    spec, etas_a, _anoms, starts = merged_members(
        method, framed, grid, provider, m, root
    )
    days = [PROBE_W_START + PROBE_W_DAYS / 2.0]
    means = mean_fields(spec, starts, etas_a, grid, method._plan, days)  # noqa: SLF001
    wall_s = time.monotonic() - t_wall
    peak_mib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    pcg_rows = list(miost_mod.CONVERGENCE_LOG[log_start:])

    STAGE1_DIR.mkdir(parents=True, exist_ok=True)
    frame_block: dict[str, Any] = {
        "core": list(TILES[tile]["core"]),
        "overlap_deg": frame.overlap_deg,
        "halo_deg": frame.halo_deg,
        "missing_neighbors": sorted(frame.missing_neighbors),
        "solve_bbox": [solve.lon_min, solve.lon_max, solve.lat_min, solve.lat_max],
        "convention": DIVERSE_FRAME_CONVENTION,
        "resolution_deg": RESOLUTION_DEG,
    }
    window = [PROBE_W_START, PROBE_W_START + PROBE_W_DAYS]
    # The T2 artifact (default cap) keeps its historical name; a raised-cap
    # re-run writes beside it — the PIN-23(a) ruling keeps T2 as history.
    if tile != PROBE_TILE or m != PROBE_M:
        npz_name = f"probe_{tile}_m{m}_mean.npz"
    elif maxiter == PROBE_MAXITER_DEFAULT:
        npz_name = "probe_quiet_gyre_mean.npz"
    else:
        npz_name = f"probe_quiet_gyre_mean_maxiter{maxiter}.npz"
    np.savez(
        STAGE1_DIR / npz_name,
        mean=means,
        label="PROBE",
        provenance=json.dumps(
            {
                "tile": tile,
                "frame": frame_block,
                "missions": list(PROBE_MISSIONS),
                "window": window,
                "m": m,
                "days": days,
                "pcg_rtol": float(method.pcg_rtol),
                "pcg_maxiter": int(method.pcg_maxiter),
            }
        ),
    )
    return {
        "tile": tile,
        "m": m,
        "frame": frame_block,
        "window": window,
        "superobs_cfg": superobs_cfg,
        "n_obs": n_obs_window,
        "n_grid_nodes": n_nodes,
        "wall_s": wall_s,
        "peak_rss_mib": peak_mib,
        "pcg": pcg_rows,
        "pcg_rtol": float(method.pcg_rtol),
        "pcg_maxiter": int(method.pcg_maxiter),
        "model": model,
    }


@app.command()
def tier2_probe(
    tile: Annotated[str, typer.Option(help="Diverse tile to probe")] = "kuroshio",
    m: Annotated[int, typer.Option(help="Members to solve")] = 100,
    maxiter: Annotated[int, typer.Option(help="PCG cap")] = PROBE_MAXITER_DEFAULT,
) -> None:
    """Owner pin 89: MEASURE the axis the Tier-2 ceiling decision turns on.

    Task 22 was to arrive with a 4x bracket (23.8-94.2 h/tile) whose spread
    is an unmeasured scaling exponent, not an observation. This runs ONE
    window of ONE diverse tile at the production ``m`` through T2's
    existing machinery and reports per-window wall, PEAK RAM and iteration
    counts with the CONVERGED/CAPPED flag.

    **PROBE, not evaluation-bearing execution** (pin 89e): the row carries
    the PROBE label, no ``STAGE1-EVIDENCE`` artifact is attached, and the
    locked-instrument tally is untouched. It runs on the ruling.

    RAM is the binding axis and has only ever been MODELLED here — the
    >=9,431 MiB figure is a model output, and pin 57 already found the
    model's phase-max does not track ``m`` until ~512 members. So the
    Tier-1 predicate is deliberately NOT used as a launch gate: gating the
    measurement on the model would beg the question the probe exists to
    answer. A live-headroom guard is applied instead.

    Args:
        tile: Registry tile (pin 89b: kuroshio, the plan's own ordering —
            riskiest path, fail fast).
        m: Members to solve.
        maxiter: PCG iteration cap.

    Raises:
        RuntimeError: If live headroom is too small to attempt safely.
    """
    from sverdrup.application.calibration.harness import (  # noqa: PLC0415
        atomic_write_json,
    )
    from sverdrup.methods.miost_windows import WindowPlan  # noqa: PLC0415

    model = tile_size_model(tile, m=m, n_windows=1)
    avail = _mem_available_mib()
    typer.echo(
        f"tile={tile} m={m}  model peak {model['peak_model_mib']:.0f} MiB  "
        f"live MemAvailable {avail:.0f} MiB"
    )
    if avail < 3000.0:
        raise RuntimeError(
            f"live headroom {avail:.0f} MiB is too small to attempt this "
            "probe safely — wait for the co-tenant cycle"
        )

    measured = _probe_solve(maxiter=maxiter, tile=tile, m=m)
    pcg_rows, capped = classify_pcg_legs(
        measured["pcg"],
        rtol=measured["pcg_rtol"],
        maxiter=measured["pcg_maxiter"],
    )
    wall = measured["wall_s"]
    peak = measured["peak_rss_mib"]
    n_windows = len(WindowPlan().windows)
    row: dict[str, Any] = {
        "label": "PROBE",
        "ruling": "docs/superpowers/2026-07-27-owner-ruling-crn-sigma-rule0.md",
        "pin": "89 — task 22 arrives with a measurement, not a 4x bracket",
        "not_evidence_bearing": (
            "PROBE label; no STAGE1-EVIDENCE artifact attached; locked "
            "instrument tally untouched (pin 89e)"
        ),
        "tile": tile,
        "m": m,
        "source": str(TILES[tile]["source"]),
        "frame": measured["frame"],
        "window": measured["window"],
        "superobs_cfg": measured["superobs_cfg"],
        "n_obs": measured["n_obs"],
        "n_grid_nodes": measured["n_grid_nodes"],
        "measured_one_window": {
            "wall_s": wall,
            "wall_h": wall / 3600.0,
            "peak_rss_mib": peak,
            "convergence": "CAPPED" if capped else "CONVERGED",
            "pcg": pcg_rows,
        },
        "model_at_probe_geometry": model,
        "measured_vs_model": {
            "peak_ratio": peak / model["peak_model_mib"],
            "note": (
                "peak_ratio is the number the ceiling decision turns on; "
                "the model has never been validated at this m on this tile"
            ),
        },
        "rederived_bracket_pin_89d": {
            "n_windows_production": n_windows,
            "per_tile_wall_h_if_linear_in_windows": wall / 3600.0 * n_windows,
            "four_tile_wall_h_if_linear_in_windows": wall / 3600.0 * n_windows * 4,
            "prior_bracket_per_tile_h": [23.8, 94.2],
            "prior_bracket_four_tiles_h": [95.0, 377.0],
            "tier2_probe_ceiling_h": 6.0,
            "caveat": (
                "one window measured; windows are not identical in cost and "
                "this host's throughput is non-stationary at x1.70 within a "
                "single run (pin 28). The residual span is stated, not "
                "hidden — see residual_span_note"
            ),
            "residual_span_note": (
                "scaling ACROSS windows is now the only unmeasured factor in "
                "the per-tile figure; the nodes-exponent question that "
                "produced the 4x spread is answered by this measurement"
            ),
        },
        "date": datetime.now(UTC).date().isoformat(),
    }
    results = json.loads(EVIDENCE.read_text())
    results["phase14"]["stage1"][f"tier2_probe_{tile}_m{m}"] = row
    atomic_write_json(EVIDENCE, results)
    typer.echo(
        f"MEASURED one window: wall {wall / 3600.0:.2f} h, peak RSS "
        f"{peak:.0f} MiB, {row['measured_one_window']['convergence']}"
    )
    typer.echo(
        f"re-derived per-tile (x{n_windows} windows): "
        f"{wall / 3600.0 * n_windows:.1f} h; four tiles: "
        f"{wall / 3600.0 * n_windows * 4:.1f} h "
        f"(prior bracket 95-377 h, ceiling 6.0 h)"
    )
    typer.echo(f"recorded: phase14.stage1.tier2_probe_{tile}_m{m}")


@app.command()
def probe(
    maxiter: Annotated[
        int,
        typer.Option(
            help=(
                "PCG iteration cap (default = the production "
                "miost_solver.PCG_MAXITER). A non-default cap is the "
                "PIN-23(a) converged re-run and records under "
                "phase14.stage1.probe_converged — the T2 row at "
                "phase14.stage1.probe stays as history."
            )
        ),
    ] = PROBE_MAXITER_DEFAULT,
) -> None:
    """The Task-2 measured-first sizing re-check — BEFORE any full run.

    quiet_gyre tile (CMEMS source — the first real CMEMS-side solve at the
    production-representative 19° solve geometry), ONE 60-day window, m=1,
    single mid-window day map, PROBE-labeled artifacts. Record-then-stop:
    a tripped 1.3x bracket exits nonzero AFTER the row is recorded (never
    a silent stop). Rows carry rtol/maxiter per pcg leg and a
    CONVERGED/CAPPED verdict (owner PIN 23(c)); a CAPPED measurement is
    called out because its ratios can only under-report.

    Args:
        maxiter: PCG iteration cap passed through to the solver.

    Raises:
        RuntimeError: Tier-1 ladder refusal (via :func:`preflight`).
        typer.Exit: Nonzero when the STOP bracket trips.
    """
    preflight_model = preflight(PROBE_TILE, PROBE_M)
    typer.echo(
        "preflight model: "
        + json.dumps({k: round(v, 1) for k, v in preflight_model.items()})
    )
    measured = _probe_solve(maxiter=maxiter)
    row = build_probe_row(date=datetime.now(UTC).date().isoformat(), **measured)
    node = "probe" if maxiter == PROBE_MAXITER_DEFAULT else PROBE_CONVERGED_NODE
    record_probe_row(row, evidence_path=EVIDENCE, node=node)
    typer.echo("measured_vs_model: " + json.dumps(row["measured_vs_model"]))
    typer.echo(f"convergence: {row['convergence']} (node phase14.stage1.{node})")
    if row["convergence"] == "CAPPED":
        typer.echo(
            "WARNING: CAPPED measurement — a PCG leg exited AT maxiter with "
            "residual above rtol; the wall is bounded above by the cap, so "
            "these ratios can only under-report (PIN 23(c): a capped ratio "
            "is labeled wherever it appears)"
        )
    if row["stop_bracket"]["tripped"]:
        typer.echo(
            "STOP: measured-vs-model bracket TRIPPED (ratio > 1.3) — the row "
            "IS recorded; the owner decides before any full runs (a mis-sized "
            "model at 6 tiles is a spend decision)"
        )
        raise typer.Exit(code=1)
    typer.echo(
        f"PROBE {PROBE_TILE} done: wall {row['wall_s']:.1f} s, "
        f"peak {row['peak_rss_mib']:.0f} MiB"
    )


# ---------------------------------------------------------------------------
# Owner PIN 26(c) — the seam-frame convergence probe (measure the frames T4
# will actually solve, BEFORE spending T4)
# ---------------------------------------------------------------------------


def _mem_available_mib() -> float:
    """MemAvailable read AT CALL TIME (the co-tenant box's headroom moves)."""
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return float(line.split()[1]) / 1024.0
    raise RuntimeError("MemAvailable not found in /proc/meminfo")  # pragma: no cover


def seam_ram_gate(*, peak_model_mib: float, mem_available_mib: float) -> dict[str, Any]:
    """The launch gate: MemAvailable >= 2 x predicted peak (the anchor rule).

    Args:
        peak_model_mib: ``size_tile``'s predicted peak RSS [MiB].
        mem_available_mib: Measured MemAvailable [MiB].

    Returns:
        The recorded gate block (``passed`` False = never launch).
    """
    threshold = SEAM_RAM_GATE_FACTOR * peak_model_mib
    return {
        "mem_available_mib": mem_available_mib,
        "threshold_mib": threshold,
        "passed": mem_available_mib >= threshold,
    }


# ---------------------------------------------------------------------------
# E-16 §1-§2 (ruling doc PART 19), ratified owner PIN 92 — the TIER-2
# PRODUCTION LAUNCH GATE for T5's diverse-tile legs.
#
# Task 22 cleared the Tier-2 crossing, so the Tier-1 ladder predicate is NOT
# the gate for these legs. It stays exactly as it is for every other caller:
# `preflight` still refuses on it, because seam_pair and the anchor gate were
# never Tier-2-cleared and the clearance is T5-scoped. tier2_probe set this
# precedent (it bypassed the predicate with a live-headroom guard and said
# why); this is that shape, promoted to the production path.
#
# Both numbers are MEASURED, not modelled:
#   * peak — pin 89 measured 4365 MiB peak RSS at m=100 on kuroshio against a
#     model 5154: the model OVER-predicts by 18%. E-16 §2 gates on "twice the
#     MEASURED peak, not the model's 5154".
#   * wall — pin 89 measured 3.440 h for ONE window; x9 windows = 31.0 h per
#     tile, x1.3 residual span -> ~40 h. PER LEG. The stage figure (123.8 h
#     for four tiles) is NOT a ceiling: E-16 §1 says "a leg exceeding 40 h
#     STOPS and reports" rather than running on, so a runaway first leg is
#     known after ~31 h instead of after 5 days.
TIER2_MEASURED_PEAK_MIB = 4365.0
TIER2_MAX_LEG_WALL_H = 40.0
TIER2_WALL_SCOPE = (
    "PER LEG (one tile), NOT per stage — the four-tile 123.8 h figure is an "
    "expectation, never a ceiling (E-16 §1)"
)


def tier2_launch_gate(*, mem_available_mib: float) -> dict[str, Any]:
    """E-16 §2's per-leg launch gate: MemAvailable >= 2 x the MEASURED peak.

    Deliberately does NOT consult ``ladder.tier1_eligible``: task 22
    cleared the Tier-2 crossing for these legs, and gating them on the
    Tier-1 predicate would make the clearance inert. The predicate is
    untouched for every other caller.

    Args:
        mem_available_mib: Measured MemAvailable [MiB], read at call time.

    Returns:
        The recorded gate block (``passed`` False = never launch; wait for
        the top of the co-tenant headroom cycle).
    """
    threshold = SEAM_RAM_GATE_FACTOR * TIER2_MEASURED_PEAK_MIB
    return {
        "mem_available_mib": mem_available_mib,
        "threshold_mib": threshold,
        "measured_peak_mib": TIER2_MEASURED_PEAK_MIB,
        "basis": (
            "2 x the MEASURED 4365 MiB peak (pin 89), NOT the model's 5154 — "
            "the model over-predicts by 18%"
        ),
        "passed": mem_available_mib >= threshold,
    }


def tier2_wall_ceiling(*, elapsed_h: float) -> dict[str, Any]:
    """E-16 §1's PER-LEG wall ceiling: over ~40 h the leg STOPS and reports.

    Args:
        elapsed_h: The leg's elapsed wall clock [h].

    Returns:
        The recorded ceiling block (``stop`` True = stop and report; the
        leg does NOT run on).
    """
    return {
        "elapsed_h": elapsed_h,
        "ceiling_h": TIER2_MAX_LEG_WALL_H,
        "scope": TIER2_WALL_SCOPE,
        "basis": "31.0 h measured (3.440 h x 9 windows, pin 89) x 1.3 residual",
        "stop": elapsed_h > TIER2_MAX_LEG_WALL_H,
    }


def seam_probe_size_model(n_obs: int) -> dict[str, float]:
    """Task-22 sizing arithmetic at the SEAM geometry, m=1, ONE window.

    Args:
        n_obs: In-window observation count (estimated before the load,
            measured after it).

    Returns:
        The ``size_tile`` model dict at the probe's own geometry.
    """
    from sverdrup.application.spatial_tiles import frame_grid  # noqa: PLC0415
    from sverdrup.methods.miost import PHASE13_WINNER_PARAMS  # noqa: PLC0415
    from sverdrup.methods.miost_basis import N_DIR  # noqa: PLC0415
    from sverdrup.methods.miost_sizing import KM_PER_DEG, size_tile  # noqa: PLC0415
    from sverdrup.methods.miost_windows import WindowPlan  # noqa: PLC0415

    frame = registry_frame(SEAM_PROBE_TILE)
    grid = frame_grid(frame, RESOLUTION_DEG)
    solve = frame.solve_bbox
    mid_lat = 0.5 * (solve.lat_min + solve.lat_max)
    d_x_km = (
        (solve.lon_max - solve.lon_min) * KM_PER_DEG * math.cos(math.radians(mid_lat))
    )
    d_y_km = (solve.lat_max - solve.lat_min) * KM_PER_DEG
    return size_tile(
        d_x_km=d_x_km,
        d_y_km=d_y_km,
        n_grid_nodes=int(grid.x.size * grid.y.size),
        window_days=WindowPlan().w_days,
        n_windows=1,
        m_members=SEAM_PROBE_M,
        n_obs=n_obs,
        alpha=float(PHASE13_WINNER_PARAMS["spacing_alpha"]),
        n_dir=N_DIR,
        lam_min=_SIZING_LAM_MIN_KM,
    )


def _seam_obs_estimate() -> int:
    """Pre-load in-window obs estimate: the signed box basis by area ratio."""
    from sverdrup.methods.miost_sizing import (  # noqa: PLC0415
        BOX_LAT,
        BOX_LON,
        BOX_W0_OBS_BASIS,
    )

    solve = registry_frame(SEAM_PROBE_TILE).solve_bbox
    box_area = (BOX_LON[1] - BOX_LON[0]) * (BOX_LAT[1] - BOX_LAT[0])
    tile_area = (solve.lon_max - solve.lon_min) * (solve.lat_max - solve.lat_min)
    return int(BOX_W0_OBS_BASIS * tile_area / box_area)


def build_seam_probe_row(
    *,
    tile: str,
    frame: dict[str, Any],
    window: list[float],
    superobs_cfg: dict[str, Any] | None,
    n_obs: int,
    n_grid_nodes: int,
    wall_s: float,
    peak_rss_mib: float,
    pcg: Iterable[dict[str, Any]],
    pcg_rtol: float,
    pcg_maxiter: int,
    config: dict[str, Any],
    model: dict[str, float],
    ram_gate: dict[str, Any],
    date: str,
) -> dict[str, Any]:
    """Assemble the PIN-26(c) seam convergence-probe row — PURE, schema pinned.

    A CONVERGENCE measurement, never an evaluation: NO scores block, NO
    seal_sha, ``m`` pinned to 1. The verdict comes from the SAME
    :func:`classify_pcg_legs` the probe and production rows use.

    Args:
        tile: The seam tile probed (registry name).
        frame: Frame provenance block (core/overlap/halo/solve bbox).
        window: ``[start, end]`` in solver days.
        superobs_cfg: Applied super-obs cfg (None on the dc2021a path).
        n_obs: Measured in-window (support-widened) observation count.
        n_grid_nodes: Solve grid node count.
        wall_s: Measured wall time [s].
        peak_rss_mib: Measured peak RSS [MiB].
        pcg: Per-leg PCG convergence rows (mean + member-batch).
        pcg_rtol: The solver rtol ACTUALLY used.
        pcg_maxiter: The solver iteration cap ACTUALLY used.
        config: Solver-configuration provenance (missions, rspec).
        model: The ``size_tile`` output at the probe's own geometry.
        ram_gate: The launch-gate record from :func:`seam_ram_gate`.
        date: ISO date string (passed in — purity).

    Returns:
        The seam-probe row (exactly the pinned key set).

    Raises:
        KeyError: Unknown tile name.
    """
    spec = TILES.get(tile)
    if spec is None:
        raise KeyError(f"unknown tile {tile!r}; known: {sorted(TILES)}")
    pcg_rows, capped = classify_pcg_legs(pcg, rtol=pcg_rtol, maxiter=pcg_maxiter)
    return {
        "label": "PROBE",
        "tile": tile,
        "source": str(spec["source"]),
        "frame": frame,
        "window": window,
        "m": SEAM_PROBE_M,
        "superobs_cfg": superobs_cfg,
        "n_obs": n_obs,
        "n_grid_nodes": n_grid_nodes,
        "wall_s": wall_s,
        "peak_rss_mib": peak_rss_mib,
        "pcg": pcg_rows,
        "convergence": "CAPPED" if capped else "CONVERGED",
        "config": config,
        "model": model,
        "ram_gate": ram_gate,
        "date": date,
    }


def _seam_probe_solve(maxiter: int) -> dict[str, Any]:
    """The PIN-26(c) measured leg: dc2021a load, ONE window, m=1, measure.

    Mirrors the anchor gate's production dc2021a substrate (five mapping
    missions, phase-13 winner params, structured RSpec) at the seam frame
    and the FIRST production window, so the iteration counts transfer to
    what T4 will actually run. No maps are scored and none are written as
    products: this leg exists to report iterations + final residual.

    Args:
        maxiter: PCG iteration cap (raised so the probe reports a
            REQUIREMENT rather than a cap).

    Returns:
        Measurement kwargs for :func:`build_seam_probe_row` (all but
        ``date`` and ``ram_gate``).
    """
    import resource  # noqa: PLC0415
    import time  # noqa: PLC0415

    import numpy as np  # noqa: PLC0415

    import sverdrup.methods.miost as miost_mod  # noqa: PLC0415
    from sverdrup.adapters.altimetry.contract import BBox  # noqa: PLC0415
    from sverdrup.adapters.altimetry.dc2021a import Dc2021aSource  # noqa: PLC0415
    from sverdrup.application.spatial_tiles import (  # noqa: PLC0415
        frame_grid,
        frame_obs,
    )
    from sverdrup.core.parameters import ConstantProvider  # noqa: PLC0415
    from sverdrup.core.seeding import derive_seed  # noqa: PLC0415
    from sverdrup.distributions.miost_ensemble import (  # noqa: PLC0415
        mean_fields,
        merged_members,
    )
    from sverdrup.methods.miost import (  # noqa: PLC0415
        PHASE13_DELTAS,
        PHASE13_WINNER_PARAMS,
        Miost,
    )
    from sverdrup.methods.miost_basis import lonlat_to_km  # noqa: PLC0415
    from sverdrup.methods.miost_rspec import RSpec  # noqa: PLC0415
    from sverdrup.methods.miost_windows import WindowPlan  # noqa: PLC0415

    def _echo(msg: str) -> None:
        print(f"[seam-probe] {msg}", flush=True)

    frame = registry_frame(SEAM_PROBE_TILE)
    grid = frame_grid(frame, RESOLUTION_DEG)
    n_nodes = int(grid.x.size * grid.y.size)
    _echo(f"frame {SEAM_PROBE_TILE}: {grid.x.size}x{grid.y.size} = {n_nodes} nodes")

    obs = Dc2021aSource().load(
        BBox(0.0, 360.0, -90.0, 90.0),
        np.datetime64("2016-11-01"),
        np.datetime64("2018-03-01"),
        missions=DC_MAPPING_FIVE,
    )
    framed = frame_obs(obs, frame, RESOLUTION_DEG)
    del obs
    _echo(f"framed obs: {len(framed.values())}")

    window = WindowPlan().windows[SEAM_PROBE_W_INDEX]
    t = framed.coords()[:, 2]
    in_window = (t >= window.start_day - 12.0) & (t <= window.end_day + 12.0)
    n_obs_window = int(in_window.sum())
    model = seam_probe_size_model(n_obs_window)
    _echo(f"window {window.id}: n_obs {n_obs_window}, model " + json.dumps(model))

    solve = frame.solve_bbox
    xs, ys = lonlat_to_km(
        np.array([solve.lon_min, solve.lon_max]),
        np.array([solve.lat_min, solve.lat_max]),
    )
    x0, y0 = float(xs[0]), float(ys[0])
    method = Miost(
        basis_domain=(x0, y0, float(xs[1]) - x0, float(ys[1]) - y0),
        pcg_maxiter=maxiter,
        rspec=RSpec(deltas=dict(PHASE13_DELTAS)),
    )
    method._plan = WindowPlan(starts=(window.start_day,))  # noqa: SLF001
    provider = ConstantProvider(dict(PHASE13_WINNER_PARAMS))
    root = derive_seed("miost", "phase14-stage1-seam-probe", SEAM_PROBE_TILE, 0)
    log_start = len(miost_mod.CONVERGENCE_LOG)
    t_wall = time.monotonic()
    spec, etas_a, _anoms, starts = merged_members(
        method, framed, grid, provider, SEAM_PROBE_M, root
    )
    mean_fields(
        spec,
        starts,
        etas_a,
        grid,
        method._plan,  # noqa: SLF001
        [window.start_day + window.w_days / 2.0],
    )
    wall_s = time.monotonic() - t_wall
    peak_mib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    pcg_rows = [dict(r) for r in miost_mod.CONVERGENCE_LOG[log_start:]]
    _echo(f"wall {wall_s:.1f} s, peak {peak_mib:.0f} MiB, legs " + json.dumps(pcg_rows))

    return {
        "tile": SEAM_PROBE_TILE,
        "frame": {
            "core": list(TILES[SEAM_PROBE_TILE]["core"]),
            "overlap_deg": frame.overlap_deg,
            "halo_deg": frame.halo_deg,
            "missing_neighbors": sorted(frame.missing_neighbors),
            "solve_bbox": [solve.lon_min, solve.lon_max, solve.lat_min, solve.lat_max],
            "resolution_deg": RESOLUTION_DEG,
        },
        "window": [window.start_day, window.end_day],
        "superobs_cfg": None,
        "n_obs": n_obs_window,
        "n_grid_nodes": n_nodes,
        "wall_s": wall_s,
        "peak_rss_mib": peak_mib,
        "pcg": pcg_rows,
        "pcg_rtol": float(method.pcg_rtol),
        "pcg_maxiter": int(method.pcg_maxiter),
        "config": {
            "missions": list(DC_MAPPING_FIVE),
            "rspec": "phase13-deltas (the winner/anchor-gate dc2021a config)",
        },
        "model": model,
    }


@app.command()
def seam_probe(
    maxiter: Annotated[
        int,
        typer.Option(
            help=(
                "PCG iteration cap for the seam probe (default 2000 — high "
                "enough that the probe reports a REQUIREMENT, not a cap)."
            )
        ),
    ] = SEAM_PROBE_MAXITER,
) -> None:
    """The PIN-26(c) seam-frame convergence probe — BEFORE any T4 spend.

    ONE seam frame (``seam_n``, dc2021a), m=1, ONE production window, cap
    raised to 2000. Records iterations + final residual for BOTH legs
    (mean and member-batch) under ``phase14.stage1.seam_convergence_probe``
    — PROBE-labeled, no scores. RAM-gated on MemAvailable >= 2x the
    predicted peak, and a CAPPED leg is recorded and then exits nonzero:
    ``seam_read`` REFUSES on residual > rtol, so an unmeasured cap would
    cost the whole T4 spend after the fact.

    Args:
        maxiter: PCG iteration cap passed through to the solver.

    Raises:
        typer.Exit: Nonzero on a failed RAM gate (nothing runs), on a
            missing solve leg, and on a CAPPED measurement (recorded
            first — an immediate owner surface).
    """
    model_pre = seam_probe_size_model(_seam_obs_estimate())
    gate = seam_ram_gate(
        peak_model_mib=float(model_pre["peak_model_mib"]),
        mem_available_mib=_mem_available_mib(),
    )
    typer.echo("ram_gate: " + json.dumps(gate))
    if not gate["passed"]:
        typer.echo(
            f"REFUSED: MemAvailable {gate['mem_available_mib']:.0f} MiB < "
            f"{SEAM_RAM_GATE_FACTOR:.0f} x predicted peak "
            f"{model_pre['peak_model_mib']:.0f} MiB — the probe WAITS; "
            "never launch over headroom (fork-g pin 4)"
        )
        raise typer.Exit(code=1)
    measured = _seam_probe_solve(maxiter)
    row = build_seam_probe_row(
        date=datetime.now(UTC).date().isoformat(), ram_gate=gate, **measured
    )
    record_probe_row(row, evidence_path=EVIDENCE, node=SEAM_PROBE_NODE)
    typer.echo(
        f"convergence: {row['convergence']} "
        f"(node phase14.stage1.{SEAM_PROBE_NODE}); legs "
        + json.dumps(
            [
                {
                    "kind": leg.get("kind", "mean"),
                    "iterations": leg["iterations"],
                    "final_rel_residual": leg["final_rel_residual"],
                }
                for leg in row["pcg"]
            ]
        )
    )
    if len(row["pcg"]) < 2:
        typer.echo(
            "STOP: fewer than the two expected PCG legs (mean + "
            "member-batch) were recorded — a row that cannot show both "
            "legs is not a convergence measurement"
        )
        raise typer.Exit(code=1)
    if row["convergence"] == "CAPPED":
        typer.echo(
            f"STOP: a seam leg CAPPED at maxiter {maxiter} over rtol — this "
            "is an IMMEDIATE owner surface (the row IS recorded). T4 must "
            "not launch: seam_read REFUSES on residual > rtol, so every "
            "seam solve would be spent and then rejected."
        )
        raise typer.Exit(code=1)
    typer.echo(
        f"SEAM PROBE {SEAM_PROBE_TILE} done: wall {row['wall_s']:.1f} s, "
        f"peak {row['peak_rss_mib']:.0f} MiB"
    )


# ---------------------------------------------------------------------------
# Task 4 — the seam pair: PRIMARY PAIR READ + the secondary ORACLE READ
#
# TWO reads, not one. They answer DIFFERENT questions and are recorded
# side by side:
#
#   * PRIMARY (the rubric's pre-registered verdict route): R_seam on
#     ``delta(x) = field_A(x) - field_B(x)`` at overlap points, EACH
#     TILE'S OWN SOLVE, BEFORE blending — the blend hides exactly what
#     this measures.
#   * ORACLE (secondary, keeps its own question — "does the blend
#     work?"): the BLENDED field against the seamless-anchor truth
#     (Task 3's maps, consumed — the anchor is never re-solved here).
#
# Both ride the ONE evaluation domain: the 2·overlap strip centred on
# the shared core boundary (owner ruling). Both ride BOTH field kinds
# (mean + σ) through the unchanged T10 machinery.
# ---------------------------------------------------------------------------

SEAM_PAIR_TILES = ("seam_n", "seam_s")
SEAM_PAIR_NAME = "seam_n|seam_s"
SEAM_PAIR_M = 100
# Era is DEGENERATE at Stage 1 (2017 only) and resolution is single —
# that is a ROW COUNT, not a schema excuse: both keys ride every row so
# Stage 2 is a row addition, not a migration.
SEAM_ERA = "2017"
SEAM_N_DAYS = 365
# The seam at 38.0N is a line of constant LATITUDE, so the axis
# perpendicular to it is latitude — always -2 in the (time, lat, lon)
# map convention this driver writes and reads.
SEAM_PERP_AXIS = -2
# The rubric's interior trim: "every node >= overlap-width from any core
# boundary", applied at the tiling's overlap constant to EVERY interior
# (the two tiles' and the seamless anchor's). Uniform on purpose: the
# pair and oracle denominators must differ ONLY in WHICH solve's
# interior they pool, never in how "interior" is defined. (The anchor
# frame's own overlap is 0.0 — trimming at its own width would pool the
# outermost solve-domain rows, where the basis is least constrained,
# into the flagship denominator.)
INTERIOR_TRIM_DEG = 2.0
SEAM_STRIP_NAME = "the 2·overlap strip"
# The solver's shipped relative tolerance (Miost default). Stated here so
# the floor probe's "deeper" claim is checkable without a heavy import;
# the recorded rows always carry the rtol the solve ACTUALLY ran under.
SEAM_PRODUCTION_RTOL = 1.0e-6
SEAM_PAIR_NODE = "seam_pair"
SEAM_ROWS_NODE = "seam_rows"
ROUTE_PAIR = "pair"
ROUTE_ORACLE = "oracle"
FIELD_KIND_MEAN = "mean"
FIELD_KIND_SIGMA = "sigma"

# Artifact names (persisted BEFORE the compare phase — the anchor-gate
# lesson: a compare-phase death must never cost the solves).
SEAM_MEAN_MAPS = {t: STAGE1_DIR / f"{t}_signed_maps.nc" for t in SEAM_PAIR_TILES}
SEAM_STD_MAPS = {t: STAGE1_DIR / f"{t}_member_std_maps.nc" for t in SEAM_PAIR_TILES}
SEAM_MEMBER_STORE = {t: STAGE1_DIR / f"{t}_member_store.npz" for t in SEAM_PAIR_TILES}
SEAM_FLOOR_STORE = STAGE1_DIR / "seam_floor_probe.npz"
# The seamless truth — Task 3's OUTPUT, read-only (never re-solved).
ANCHOR_MEAN_MAPS = STAGE1_DIR / "anchor_signed_maps.nc"
ANCHOR_STD_MAPS = STAGE1_DIR / "anchor_member_std_maps.nc"
ANCHOR_MEMBER_STORE = STAGE1_DIR / "anchor_gate_member_store.npz"

# ---- Rule 0.a: the solver floor probe (rubric) + owner PIN 23 -------------
FLOOR_FACTOR = 3.0
# Deeper on BOTH axes. The rubric's construction says "maxiter +1000";
# on its own that is inert HERE, because the production seam solve
# CONVERGES at ~407 iterations against a 1200 cap — more headroom would
# return the identical answer and F would come out exactly 0, licensing
# every verdict vacuously. So the probe also tightens rtol by three
# decades; the +1000 is what buys the iterations that tightening costs.
#
# RUBRIC v2 / OWNER PIN 34: F is defined by the ACCURACY the probe
# REACHES, not by the iteration budget it is handed. The decade count is
# the pre-registered quantity (sealed in instrument_configs), the target
# rtol is DERIVED from it, and maxiter is merely sized to reach the
# target. A probe that does not attain the target is a STOP — never a
# fallback to a looser F.
# (Stated as a literal to keep this module's import light — a test pins it
# equal to the sealed `SEAM_FLOOR_DECADES`, so drift fails.)
FLOOR_DECADES = 3
FLOOR_RTOL = SEAM_PRODUCTION_RTOL * 10.0**-FLOOR_DECADES
FLOOR_MAXITER = STAGE1_PCG_MAXITER + 1000
FLOOR_W_INDEX = 0
FLOOR_M = SEAM_PAIR_M
FLOOR_M_JUSTIFICATION = (
    "m=100, NOT pin 20(a)'s m=1 — stated here because the pin requires "
    "it: the σ field kind has no floor at m=1 (member-std is taken about "
    "the sample mean with the (m-1) denominator, undefined for a single "
    "member), and the sealed rubric carries a floor per VERDICT-BEARING "
    "ROUTE, of which σ is one. Solving the probe at the production m "
    "against the production run's OWN window-0 coefficients (same root, "
    "same window, same m — ONLY the tolerance differs) is also the "
    "cheapest way to obtain the σ floor: it adds one deeper window solve "
    "per tile and re-uses the production solve as the reference. Pin "
    "20(a)'s physics claim is untouched: m adds RHS columns to the same "
    "operator and cannot change the convergence floor."
)
UNMEASURED_SOLVER_FLOOR = "UNMEASURED (solver floor)"
UNMEASURED_PENDING_OWNER = "UNMEASURED (pending owner — floor-probe WAIT)"

# ---- TWO D_int DENOMINATORS — DIFFERENT BY DESIGN, PINNED ADJACENT -------
# WHY THEY DIFFER (do NOT "fix" this inconsistency): the two reads answer
# different questions, so they normalize against different fields. The
# PAIR read asks "do the two tile solves agree where they overlap?" and
# the rubric (R-06/R-07) anchors that against the TILES' own field
# variability — pooled core interiors of BOTH tiles. The ORACLE read asks
# "does the blended product match the seamless truth?" and the rubric
# (R-19) anchors that against the SEAMLESS solve's own variability, the
# only field the oracle claims to reproduce. A future reader who unifies
# them silently breaks the flagship comparison: the oracle ratio would
# start being scaled by the very tiles it is supposed to audit.
PAIR_D_INT_SOURCE = (
    "pooled core interiors of both seam tiles (rubric R-06/R-07) — the "
    "PAIR read's denominator"
)
ORACLE_D_INT_SOURCE = (
    "the seamless anchor solve's core interior (rubric R-19) — the "
    "ORACLE read's denominator"
)

# ---- review pin 13: the geometry caveat, verbatim, on every row ----------
SEAM_GEOMETRY = (
    "10x5 halves inside the anchor footprint — NOT D1 production geometry (15x15)"
)
SEAM_NON_TRANSFER_NOTE = (
    "this verdict is not a production-geometry seam reading: it is taken "
    "on 10x5 halves inside the anchor footprint, and the "
    "feasibility-frontier watch item (worst-seam grew with TILE COUNT, "
    "PROGRESS 2026-07-01) sits on the far side of that gap — discipline "
    "7 applied to a positive result"
)
ORACLE_NOTE = "no published precedent — gap-register (T11)"


def seam_strip_bbox() -> BBox:
    """The ONE evaluation domain: the 2·overlap strip (owner ruling).

    DERIVED from the two registry frames — the shared core boundary and
    the tiling overlap — never typed, so a frame edit cannot silently
    desync the domain from the geometry it is supposed to describe.

    Returns:
        The strip bbox (shared lon span x boundary +/- overlap).

    Raises:
        RuntimeError: If the pair does not share a core boundary or the
            two frames disagree on the overlap width.
    """
    from sverdrup.adapters.altimetry.contract import BBox  # noqa: PLC0415

    north = registry_frame("seam_n")
    south = registry_frame("seam_s")
    if north.core.lat_min != south.core.lat_max:
        raise RuntimeError(
            f"seam pair does not share a core boundary: seam_n core starts "
            f"at {north.core.lat_min} but seam_s core ends at "
            f"{south.core.lat_max}"
        )
    if north.overlap_deg != south.overlap_deg:
        raise RuntimeError(
            f"seam pair overlap mismatch: {north.overlap_deg} vs "
            f"{south.overlap_deg} — the strip width is 2 x overlap and "
            "cannot be defined from two different overlaps"
        )
    boundary = float(north.core.lat_min)
    half = float(north.overlap_deg)
    return BBox(
        max(north.core.lon_min, south.core.lon_min),
        min(north.core.lon_max, south.core.lon_max),
        boundary - half,
        boundary + half,
    )


def strip_mask(grid: GridSpec, bbox: BBox) -> tuple[NDArray[np.bool_], ...]:
    """Node masks (lat, lon) selecting a bbox on a frame grid.

    Args:
        grid: The tile's solve grid.
        bbox: The region to select.

    Returns:
        ``(lat_mask, lon_mask)`` boolean masks into ``grid.y`` / ``grid.x``.
    """
    import numpy as np  # noqa: PLC0415

    tol = 1.0e-6  # grid nodes carry fp accumulation (43.2000000000001)
    lat = (np.asarray(grid.y) >= bbox.lat_min - tol) & (
        np.asarray(grid.y) <= bbox.lat_max + tol
    )
    lon = (np.asarray(grid.x) >= bbox.lon_min - tol) & (
        np.asarray(grid.x) <= bbox.lon_max + tol
    )
    return np.asarray(lat), np.asarray(lon)


def core_interior_mask(
    frame: TileFrame, grid: GridSpec, trim_deg: float = INTERIOR_TRIM_DEG
) -> tuple[NDArray[np.bool_], ...]:
    """The rubric's core interior: every node >= trim from any core boundary.

    Args:
        frame: The tile frame.
        grid: The tile's solve grid.
        trim_deg: Trim width (see :data:`INTERIOR_TRIM_DEG`).

    Returns:
        ``(lat_mask, lon_mask)`` selecting the core interior.

    Raises:
        ValueError: If the trim leaves no interior node (a frame too small
            to carry the rubric's denominator must refuse, never silently
            pool the seam itself).
    """
    from sverdrup.adapters.altimetry.contract import BBox  # noqa: PLC0415

    core = frame.core
    inner = BBox(
        core.lon_min + trim_deg,
        core.lon_max - trim_deg,
        core.lat_min + trim_deg,
        core.lat_max - trim_deg,
    )
    lat, lon = strip_mask(grid, inner)
    if not lat.any() or not lon.any():
        raise ValueError(
            f"core interior empty after trimming {trim_deg} deg from core "
            f"{core} — D_int cannot be pooled on this frame"
        )
    return lat, lon


def pair_read(
    *,
    mean_a: ArrayLike,
    mean_b: ArrayLike,
    sigma_a: ArrayLike,
    sigma_b: ArrayLike,
    interior_mean_a: ArrayLike,
    interior_mean_b: ArrayLike,
    interior_sigma_a: ArrayLike,
    interior_sigma_b: ArrayLike,
    residual_a: float,
    rtol_a: float,
    residual_b: float,
    rtol_b: float,
    axis: int = SEAM_PERP_AXIS,
) -> SeamRead:
    """The PRIMARY read: each tile's OWN solve on the strip, before blending.

    D_INT PIN (PAIR) — the pooled core interiors of BOTH tiles
    (:data:`PAIR_D_INT_SOURCE`, rubric R-06/R-07). Read the
    why-they-differ comment beside :data:`ORACLE_D_INT_SOURCE` before
    changing either.

    Args:
        mean_a: Tile A mean map on the 2·overlap strip.
        mean_b: Tile B mean map on the same strip nodes.
        sigma_a: Tile A member-std map on the strip.
        sigma_b: Tile B member-std map on the strip.
        interior_mean_a: Tile A core-interior mean field.
        interior_mean_b: Tile B core-interior mean field.
        interior_sigma_a: Tile A core-interior member-std field.
        interior_sigma_b: Tile B core-interior member-std field.
        residual_a: Tile A worst PCG final relative residual.
        rtol_a: Tile A solver rtol.
        residual_b: Tile B worst PCG final relative residual.
        rtol_b: Tile B solver rtol.
        axis: Axis perpendicular to the seam.

    Returns:
        The assembled :class:`SeamRead` (both field kinds).
    """
    from sverdrup.validation.seam_metrics import seam_read  # noqa: PLC0415

    return seam_read(
        mean_a,
        mean_b,
        interior_mean_a,
        interior_mean_b,
        axis,
        sigma_seam_a=sigma_a,
        sigma_seam_b=sigma_b,
        sigma_interior_a=interior_sigma_a,
        sigma_interior_b=interior_sigma_b,
        final_rel_residual_a=residual_a,
        rtol_a=rtol_a,
        final_rel_residual_b=residual_b,
        rtol_b=rtol_b,
    )


def oracle_read(
    *,
    blended_mean: ArrayLike,
    seamless_mean: ArrayLike,
    blended_sigma: ArrayLike,
    seamless_sigma: ArrayLike,
    seamless_interior_mean: ArrayLike,
    seamless_interior_sigma: ArrayLike,
    residual_blend: float,
    rtol_blend: float,
    residual_seamless: float,
    rtol_seamless: float,
    axis: int = SEAM_PERP_AXIS,
) -> SeamRead:
    """The SECONDARY read: the blended field vs the seamless-anchor truth.

    D_INT PIN (ORACLE) — the SEAMLESS solve's interior ALONE
    (:data:`ORACLE_D_INT_SOURCE`, rubric R-19), which is why the seamless
    interior is passed on BOTH sides of the T10 pooling call: pooling a
    set with itself is the identity on RMS, so ``D_int`` comes out
    exactly the seamless solve's own interior dispersion, through the
    unmodified metric module. The tiles' interiors are deliberately NOT
    in this denominator — see the why-they-differ comment beside
    :data:`PAIR_D_INT_SOURCE`.

    Args:
        blended_mean: Partition-of-unity blend of the pair on the strip.
        seamless_mean: Seamless-anchor mean truth on the same strip nodes.
        blended_sigma: Blended member-std field on the strip.
        seamless_sigma: Seamless-anchor member-std truth on the strip.
        seamless_interior_mean: Seamless core-interior mean field.
        seamless_interior_sigma: Seamless core-interior member-std field.
        residual_blend: Worst PCG residual across the blended pair.
        rtol_blend: The pair's solver rtol.
        residual_seamless: The seamless solve's worst PCG residual.
        rtol_seamless: The seamless solve's solver rtol.
        axis: Axis perpendicular to the seam.

    Returns:
        The assembled :class:`SeamRead` (both field kinds).
    """
    from sverdrup.validation.seam_metrics import seam_read  # noqa: PLC0415

    return seam_read(
        blended_mean,
        seamless_mean,
        seamless_interior_mean,
        seamless_interior_mean,
        axis,
        sigma_seam_a=blended_sigma,
        sigma_seam_b=seamless_sigma,
        sigma_interior_a=seamless_interior_sigma,
        sigma_interior_b=seamless_interior_sigma,
        final_rel_residual_a=residual_blend,
        rtol_a=rtol_blend,
        final_rel_residual_b=residual_seamless,
        rtol_b=rtol_seamless,
    )


_FLOOR_PROBE_REQUIRED = (
    "rtol",
    "maxiter",
    "iterations",
    "final_rel_residual",
    "converged",
)


def floor_attributability(
    *, rms_delta: float, floor_f: float, probe: dict[str, Any]
) -> dict[str, Any]:
    """Rubric Rule 0.a + owner PINs 23/34: above the solver floor?

    The verdict is attributable ONLY if ``RMS(delta) > 3 x F``. At or
    below that the number is still recorded and the row is marked
    UNMEASURED (solver floor) — never CLEAN.

    PIN 23: ``F`` is a floor only if the deeper solve CONVERGED. A gap
    between two TRUNCATION points is not a floor and ``3 x F`` has no
    meaning, so a non-converged probe is a STOP for the owner, never an
    UNMEASURED verdict.

    PIN 34 (rubric v2): ``F`` is defined by the ACCURACY TARGET — the
    probe must reach ``FLOOR_DECADES`` decades below the production rtol.
    The target and the ACHIEVED residual are both recorded, and a probe
    whose achieved residual misses the target is a STOP: never a fallback
    to a looser F.

    Args:
        rms_delta: The measured co-located disagreement RMS.
        floor_f: The measured floor F (max|field shift| on the strip).
        probe: The deeper solve's recorded convergence evidence (rtol,
            maxiter, iterations, final_rel_residual, converged).

    Returns:
        The attributability block recorded on the row.

    Raises:
        ValueError: If the probe omits any of pin 23's five fields.
        RuntimeError: If the deeper solve did not converge, or if it did
            not attain the pre-registered accuracy target (pin 34).
    """
    for key in _FLOOR_PROBE_REQUIRED:
        if key not in probe:
            raise ValueError(
                f"floor probe must record {key!r} (owner PIN 23: the row "
                "records rtol, maxiter, iterations, final residual and the "
                "CONVERGED flag — a bare F is unverifiable)"
            )
    if not probe["converged"]:
        raise RuntimeError(
            "STOP for the owner (PIN 23): the deeper-tolerance solve did "
            f"NOT converge (rtol {probe['rtol']!r}, maxiter "
            f"{probe['maxiter']!r}, final residual "
            f"{probe['final_rel_residual']!r}) — F between two truncation "
            "points is not a floor and 3xF has no meaning; this is a STOP, "
            "NOT an UNMEASURED verdict"
        )
    achieved = float(probe["final_rel_residual"])
    if not achieved <= FLOOR_RTOL:  # NaN-safe
        raise RuntimeError(
            "STOP for the owner (PIN 34): the floor probe did not attain its "
            f"accuracy target — achieved relative residual {achieved:g} against "
            f"the pre-registered target {FLOOR_RTOL:g} ({FLOOR_DECADES} decades "
            f"below the production rtol {SEAM_PRODUCTION_RTOL:g}). F is defined "
            "by accuracy reached, so non-attainment is a STOP, NEVER a fallback "
            "to a looser F"
        )
    threshold = FLOOR_FACTOR * float(floor_f)
    return {
        "f_m": float(floor_f),
        "factor": FLOOR_FACTOR,
        "threshold_m": threshold,
        "attributable": bool(rms_delta > threshold),
        # PIN 34: the accuracy target beside what was actually achieved —
        # the pairing is what makes the floor checkable from the row.
        "production_rtol": SEAM_PRODUCTION_RTOL,
        "decades_below_production_rtol": FLOOR_DECADES,
        "target_rtol": FLOOR_RTOL,
        "achieved_rel_residual": achieved,
        "probe": dict(probe),
    }


def floor_wait_block(*, reason: str) -> dict[str, Any]:
    """A WAIT floor block: the probe was refused, the verdict is withheld.

    Pin 20(b): when the ladder refuses the extra leg, a WAIT row is
    RECORDED and the pair is marked UNMEASURED-pending-owner — never
    silently skipped, and never reported as if it had been floored.

    Args:
        reason: Why the probe did not run.

    Returns:
        The WAIT block.
    """
    return {
        "status": "WAIT",
        "reason": reason,
        "f_m": None,
        "factor": FLOOR_FACTOR,
        "threshold_m": None,
        "attributable": False,
        "probe": None,
    }


NOT_ESTABLISHED = "NOT_ESTABLISHED (ensemble MC artifact — see diagnosis)"
NOT_ESTABLISHED_FIREWALL = (
    "the committed, dual-reviewed and CONFIRMED diagnosis establishes this "
    "sigma reading as ensemble Monte-Carlo noise arising from the per-tile CRN "
    "basis origin, NOT as a seam artifact. The row is therefore withheld under "
    "the standing not-established firewall: no rubric verdict supports any "
    "reading of it, in either direction, and the diagnosis-derived bound must "
    "not be presented adjacent to it as though it were one (owner pin 37b). "
    "No sealed instrument was amended to record this — the rubric amendment is "
    "DEFERRED to one sealed version after T14/T15 (owner pin 45)"
)
#: Verdict strings that are WITHHOLDINGS, not readings. A row already
#: carrying one of these cannot be marked not-established: there is no
#: reading to withhold, and relabelling it would assert something the
#: diagnosis does not say.
_WITHHELD_PREFIXES = ("UNMEASURED", "NOT_ESTABLISHED")


def mark_not_established(
    *, row: dict[str, Any], diagnosis_ref: str, date: str
) -> dict[str, Any]:
    """Withhold ONE recorded σ row under the not-established firewall.

    Owner pin 45(b): the σ rows do not need a seal. The diagnosis already
    establishes both σ cells as artifacts of the shared basis origin, so
    they are marked under the firewall that already exists — no sealed
    instrument is touched, and the MEASUREMENT is untouched (only the
    verdict is withheld, with the prior value preserved).

    **Owner pin 47 — the guard keys on the VERDICT, not on its own
    witness.** The predecessor guard refused when the annotation block was
    present, so deleting that block (what a manual reset does) let a second
    marking overwrite ``prior_verdict`` with the already-marked value. The
    verdict cannot be deleted without destroying the row, so it is the
    honest witness.

    Args:
        row: The recorded σ row.
        diagnosis_ref: Evidence path of the establishing diagnosis.
        date: ISO date string (passed in — purity).

    Returns:
        The withheld row.

    Raises:
        ValueError: If the row is not a σ row, if it already carries a
            marking, or if its verdict is already a withholding rather than
            a pre-registered rubric cell.
    """
    if row["field_kind"] != FIELD_KIND_SIGMA:
        raise ValueError(
            f"only sigma rows are withheld by this diagnosis; got field_kind "
            f"{row['field_kind']!r} — the two mean-route CLEAN verdicts stand"
        )
    verdict = str(row["verdict"])
    if verdict.startswith(_WITHHELD_PREFIXES):
        raise ValueError(
            f"row verdict is already a withholding ({verdict!r}), not a "
            "reading: there is nothing to withhold, and this refusal also "
            "closes the deletion attack (owner pin 47) — the guard keys on "
            "the verdict, which cannot be deleted, not on the annotation "
            "block, which can"
        )
    if row.get("not_established") is not None:
        raise ValueError("row is already marked not-established")
    withheld = dict(row)
    withheld["verdict"] = NOT_ESTABLISHED
    withheld["attributable"] = False
    withheld["not_established"] = {
        "prior_verdict": verdict,
        "prior_attributable": row["attributable"],
        "diagnosis": diagnosis_ref,
        "firewall": NOT_ESTABLISHED_FIREWALL,
        "ruling": "docs/superpowers/2026-07-27-owner-ruling-crn-sigma-rule0.md",
        "pin": "45(b)",
        "measurement_unchanged": (
            "rms_delta, d_int, r_seam and the pre-registered rubric_cell stand "
            "exactly as recorded under seal v1"
        ),
        "date": date,
    }
    return withheld


def seam_verdict_from_floors(*, rubric_cell: str, floor: dict[str, Any]) -> str:
    """Apply Rule 0's solver floor to a rubric cell — the ONE precedence.

    A floor-probe WAIT withholds first; then the SOLVER floor (Rule 0.a).
    The ensemble floor (Rule 0.b) is NOT here: the owner DEFERRED the whole
    rubric amendment to one sealed version authored after T14/T15, against
    the CRN-paired configuration that will then exist, so no code verdicts
    on an unsealed rule.

    Args:
        rubric_cell: The sealed-threshold cell for the ratio.
        floor: Solver-floor attributability block, or a WAIT block.

    Returns:
        The verdict string.
    """
    if floor.get("status") == "WAIT":
        return UNMEASURED_PENDING_OWNER
    if not floor["attributable"]:
        return UNMEASURED_SOLVER_FLOOR
    return rubric_cell


def build_seam_row(
    *,
    route: str,
    field_kind: str,
    rms_delta: float,
    d_int: float,
    r_seam: float,
    rubric_cell: str,
    floor: dict[str, Any],
    seal_sha: str,
    date: str,
) -> dict[str, Any]:
    """Assemble one rubric seam row — a PURE function, schema pinned.

    The row carries the rubric's shape ``{pair, era, field_kind,
    rms_delta, d_int, r_seam, verdict}`` plus the resolution, the
    denominator it used, its own floor blocks, and the review-pin-13
    geometry caveat. There is deliberately NO free-prose field.

    Args:
        route: ``"pair"`` (primary) or ``"oracle"`` (secondary).
        field_kind: ``"mean"`` or ``"sigma"``.
        rms_delta: Co-located disagreement RMS for this field kind.
        d_int: The route's interior reference dispersion.
        r_seam: ``rms_delta / d_int``.
        rubric_cell: The sealed-threshold cell for ``r_seam`` (computed
            by the metric module at call time — never re-derived here).
        floor: A solver-floor attributability block or a WAIT block.
        seal_sha: The verified evaluation-seal sha the row quotes.
        date: ISO date string (passed in — purity).

    Returns:
        The seam row (exactly the pinned key set).

    Raises:
        ValueError: Unknown route.
    """
    if route == ROUTE_PAIR:
        d_int_source = PAIR_D_INT_SOURCE
        oracle_note = None
    elif route == ROUTE_ORACLE:
        d_int_source = ORACLE_D_INT_SOURCE
        oracle_note = ORACLE_NOTE
    else:
        raise ValueError(
            f"unknown seam read route {route!r}; known: {[ROUTE_PAIR, ROUTE_ORACLE]}"
        )
    verdict = seam_verdict_from_floors(rubric_cell=rubric_cell, floor=floor)
    strip = seam_strip_bbox()
    return {
        "route": route,
        "pair": SEAM_PAIR_NAME,
        "era": SEAM_ERA,
        "field_kind": field_kind,
        "resolution_deg": RESOLUTION_DEG,
        "domain": {
            "name": SEAM_STRIP_NAME,
            "bbox": [strip.lon_min, strip.lon_max, strip.lat_min, strip.lat_max],
            "boundary_lat": 0.5 * (strip.lat_min + strip.lat_max),
            "overlap_deg": 0.5 * (strip.lat_max - strip.lat_min),
        },
        "rms_delta": rms_delta,
        "d_int": d_int,
        "d_int_source": d_int_source,
        "r_seam": r_seam,
        "rubric_cell": rubric_cell,
        "verdict": verdict,
        "attributable": bool(floor.get("attributable", False)),
        "floor": floor,
        "geometry": SEAM_GEOMETRY,
        "non_transfer_note": SEAM_NON_TRANSFER_NOTE,
        "oracle_note": oracle_note,
        "seal_sha": seal_sha,
        "label": "STAGE1-EVIDENCE",
        "date": date,
    }


def seam_rows_from_read(
    *,
    route: str,
    read: SeamRead,
    floor_mean: dict[str, Any],
    floor_sigma: dict[str, Any],
    seal_sha: str,
    date: str,
) -> list[dict[str, Any]]:
    """Both field-kind rows of one read — mean first, σ second.

    Args:
        route: ``"pair"`` or ``"oracle"``.
        read: The assembled :class:`SeamRead`.
        floor_mean: The mean route's floor block.
        floor_sigma: The σ route's floor block (its OWN floor — the two
            field kinds are different quantities in different units).
        seal_sha: The verified seal sha.
        date: ISO date string.

    Returns:
        Two rows, one per field kind.
    """
    return [
        build_seam_row(
            route=route,
            field_kind=FIELD_KIND_MEAN,
            rms_delta=read.rms_delta,
            d_int=read.d_int,
            r_seam=read.r_seam,
            rubric_cell=read.verdict,
            floor=floor_mean,
            seal_sha=seal_sha,
            date=date,
        ),
        build_seam_row(
            route=route,
            field_kind=FIELD_KIND_SIGMA,
            rms_delta=read.rms_sigma_delta,
            d_int=read.d_int_sigma,
            r_seam=read.r_seam_sigma,
            rubric_cell=read.verdict_sigma,
            floor=floor_sigma,
            seal_sha=seal_sha,
            date=date,
        ),
    ]


def record_seam_rows(
    rows: list[dict[str, Any]], evidence_path: Path = EVIDENCE
) -> None:
    """Record the rubric rows under ``phase14.stage1.seam_rows`` — seal-gated.

    Args:
        rows: Rows from :func:`seam_rows_from_read`.
        evidence_path: The evidence store (tmp path in tests).

    Raises:
        sverdrup.validation.phase14_seal.SealError: No verified seal.
    """
    from sverdrup.application.calibration.harness import (  # noqa: PLC0415
        atomic_write_json,
    )
    from sverdrup.validation import phase14_seal  # noqa: PLC0415

    phase14_seal.verify_current_seal()
    results: dict[str, Any] = (
        json.loads(evidence_path.read_text()) if evidence_path.exists() else {}
    )
    node = results.setdefault("phase14", {}).setdefault("stage1", {})
    node[SEAM_ROWS_NODE] = rows
    atomic_write_json(evidence_path, results)


def record_seam_block(block: dict[str, Any], evidence_path: Path = EVIDENCE) -> None:
    """Record the run block under ``phase14.stage1.seam_pair`` — seal-gated.

    Args:
        block: The seam-pair run provenance block.
        evidence_path: The evidence store (tmp path in tests).

    Raises:
        sverdrup.validation.phase14_seal.SealError: No verified seal.
    """
    from sverdrup.application.calibration.harness import (  # noqa: PLC0415
        atomic_write_json,
    )
    from sverdrup.validation import phase14_seal  # noqa: PLC0415

    phase14_seal.verify_current_seal()
    results: dict[str, Any] = (
        json.loads(evidence_path.read_text()) if evidence_path.exists() else {}
    )
    node = results.setdefault("phase14", {}).setdefault("stage1", {})
    node[SEAM_PAIR_NODE] = block
    atomic_write_json(evidence_path, results)


def _obs_estimate(tile: str) -> int:
    """Pre-load in-window obs estimate for a tile: box basis by area ratio."""
    from sverdrup.methods.miost_sizing import (  # noqa: PLC0415
        BOX_LAT,
        BOX_LON,
        BOX_W0_OBS_BASIS,
    )

    solve = registry_frame(tile).solve_bbox
    box_area = (BOX_LON[1] - BOX_LON[0]) * (BOX_LAT[1] - BOX_LAT[0])
    tile_area = (solve.lon_max - solve.lon_min) * (solve.lat_max - solve.lat_min)
    return int(BOX_W0_OBS_BASIS * tile_area / box_area)


def tile_size_model(tile: str, *, m: int, n_windows: int) -> dict[str, float]:
    """Task-22 sizing arithmetic at any registry tile's geometry.

    Args:
        tile: Registry tile name.
        m: Ensemble members.
        n_windows: Windows solved.

    Returns:
        The ``size_tile`` model dict.
    """
    from sverdrup.application.spatial_tiles import frame_grid  # noqa: PLC0415
    from sverdrup.methods.miost import PHASE13_WINNER_PARAMS  # noqa: PLC0415
    from sverdrup.methods.miost_basis import N_DIR  # noqa: PLC0415
    from sverdrup.methods.miost_sizing import KM_PER_DEG, size_tile  # noqa: PLC0415
    from sverdrup.methods.miost_windows import WindowPlan  # noqa: PLC0415

    frame = registry_frame(tile)
    grid = frame_grid(frame, RESOLUTION_DEG)
    solve = frame.solve_bbox
    mid_lat = 0.5 * (solve.lat_min + solve.lat_max)
    return size_tile(
        d_x_km=(solve.lon_max - solve.lon_min)
        * KM_PER_DEG
        * math.cos(math.radians(mid_lat)),
        d_y_km=(solve.lat_max - solve.lat_min) * KM_PER_DEG,
        n_grid_nodes=int(grid.x.size * grid.y.size),
        window_days=WindowPlan().w_days,
        n_windows=n_windows,
        m_members=m,
        n_obs=_obs_estimate(tile),
        alpha=float(PHASE13_WINNER_PARAMS["spacing_alpha"]),
        n_dir=N_DIR,
        lam_min=_SIZING_LAM_MIN_KM,
    )


def floor_probe_plan(*, m: int = FLOOR_M) -> dict[str, Any]:
    """The Tier-1 arithmetic for the floor legs — STATED BEFORE THEY RUN.

    Pin 20(b): the extra leg is sized (``size_tile`` at each probed
    geometry, ONE window) and laddered before it is spent; a ladder
    refusal becomes a WAIT row, never a silent skip.

    Args:
        m: Members solved by the probe (see
            :data:`FLOOR_M_JUSTIFICATION`).

    Returns:
        The recorded plan block.
    """
    from sverdrup.application import ladder  # noqa: PLC0415

    probed = (*SEAM_PAIR_TILES, "anchor")
    models = {t: tile_size_model(t, m=m, n_windows=1) for t in probed}
    peak = max(float(mo["peak_model_mib"]) for mo in models.values())
    return {
        "construction": (
            "Task-18 lineage (scripts/diag_miost_seam_dispersion.py), "
            "imported — never reimplemented"
        ),
        "m": m,
        "m_justification": FLOOR_M_JUSTIFICATION,
        "window_index": FLOOR_W_INDEX,
        "n_windows": 1,
        "rtol": FLOOR_RTOL,
        "maxiter": FLOOR_MAXITER,
        "production_rtol": SEAM_PRODUCTION_RTOL,
        "production_maxiter": STAGE1_PCG_MAXITER,
        "probed_tiles": list(probed),
        "models": models,
        "peak_model_mib": peak,
        "tier1_eligible": bool(ladder.tier1_eligible(peak)),
        "wall_note": (
            "wall scales ~linearly in iterations at fixed geometry and m; "
            "RAM is unchanged by the deeper tolerance (the operator and "
            "the RHS block are identical — only the stopping test moves)"
        ),
    }


def _diag_lineage() -> ModuleType:
    """The Task-18 seam-dispersion diagnostic, imported (never reimplemented).

    Plan pin 20(c): the floor machinery REUSES this script's
    Task-18-lineage construction BY IMPORT — the standing reuse formula.

    Returns:
        The executed ``scripts/diag_miost_seam_dispersion`` module.
    """
    import importlib.util  # noqa: PLC0415
    import sys  # noqa: PLC0415

    name = "diag_miost_seam_dispersion"
    cached = sys.modules.get(name)
    if cached is not None:
        return cached
    path = Path(__file__).with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover - loader exists
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _lineage_std_fields() -> Any:  # noqa: ANN401 - the lineage's own callable
    """The Task-18 lineage's member-std evaluator (sparse S-path)."""
    return _diag_lineage().std_fields


def _lineage_mean_fields() -> Any:  # noqa: ANN401 - the lineage's own callable
    """The Task-18 lineage's mean-field evaluator (sparse S-path)."""
    from sverdrup.distributions.miost_ensemble import mean_fields  # noqa: PLC0415

    return getattr(_diag_lineage(), "mean_fields", mean_fields)


def _lineage_exclusive_days() -> Any:  # noqa: ANN401 - the lineage's own callable
    """The Task-18 lineage's exclusive-day helper (one solve per window)."""
    return _diag_lineage().exclusive_days


def _anchor_gate_module() -> ModuleType:
    """The Task-3 anchor gate, imported read-only (constants + tally guard)."""
    import importlib.util  # noqa: PLC0415
    import sys  # noqa: PLC0415

    name = "phase14_anchor_gate"
    cached = sys.modules.get(name)
    if cached is not None:
        return cached
    path = Path(__file__).with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover - loader exists
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _seam_echo(msg: str) -> None:
    """Flushed heartbeat line (the detached-log/stall-watcher convention)."""
    print(f"[seam-pair] {datetime.now(UTC).isoformat()} {msg}", flush=True)


def _seam_framed_obs(tile: str) -> tuple[TileFrame, GridSpec, Any]:  # noqa: ANN401
    """Frame, grid and framed dc2021a obs for one seam tile."""
    import numpy as np  # noqa: PLC0415

    from sverdrup.adapters.altimetry.contract import BBox  # noqa: PLC0415
    from sverdrup.adapters.altimetry.dc2021a import Dc2021aSource  # noqa: PLC0415
    from sverdrup.application.spatial_tiles import (  # noqa: PLC0415
        frame_grid,
        frame_obs,
    )

    frame = registry_frame(tile)
    grid = frame_grid(frame, RESOLUTION_DEG)
    obs = Dc2021aSource().load(
        BBox(0.0, 360.0, -90.0, 90.0),
        np.datetime64("2016-11-01"),
        np.datetime64("2018-03-01"),
        missions=DC_MAPPING_FIVE,
    )
    framed = frame_obs(obs, frame, RESOLUTION_DEG)
    del obs
    return frame, grid, framed


def _seam_miost(
    frame: TileFrame,
    *,
    starts: tuple[float, ...] | None,
    maxiter: int,
    rtol: float | None = None,
    ckpt_dir: Path | None = None,
) -> Any:  # noqa: ANN401 - the Miost method object
    """The frozen signed config at a seam frame (basis domain = solve bbox)."""
    import numpy as np  # noqa: PLC0415

    from sverdrup.methods.miost import (  # noqa: PLC0415
        PHASE13_DELTAS,
        Miost,
    )
    from sverdrup.methods.miost_basis import lonlat_to_km  # noqa: PLC0415
    from sverdrup.methods.miost_rspec import RSpec  # noqa: PLC0415
    from sverdrup.methods.miost_windows import WindowPlan  # noqa: PLC0415

    solve = frame.solve_bbox
    xs, ys = lonlat_to_km(
        np.array([solve.lon_min, solve.lon_max]),
        np.array([solve.lat_min, solve.lat_max]),
    )
    x0, y0 = float(xs[0]), float(ys[0])
    plan = WindowPlan() if starts is None else WindowPlan(starts=starts)
    kwargs: dict[str, Any] = {
        "plan": plan,
        "basis_domain": (x0, y0, float(xs[1]) - x0, float(ys[1]) - y0),
        "pcg_maxiter": maxiter,
        "rspec": RSpec(deltas=dict(PHASE13_DELTAS)),
    }
    if rtol is not None:
        kwargs["pcg_rtol"] = rtol
    if ckpt_dir is not None:
        kwargs["member_solve_checkpoint_dir"] = ckpt_dir
    return Miost(**kwargs)


def _store_payload(
    etas_a: dict[str, Any],
    anoms: dict[str, Any],
    starts: dict[str, float],
    pcg_rows: list[dict[str, Any]],
    wall_s: float,
    label: str,
) -> dict[str, Any]:
    """Npz payload for a leg's own member store (crash-resume substrate)."""
    import numpy as np  # noqa: PLC0415

    payload: dict[str, Any] = {
        "window_ids": np.array(sorted(anoms)),
        "pcg_rows": json.dumps(pcg_rows),
        "solve_wall_s": wall_s,
        "label": label,
    }
    for w in anoms:
        payload[f"eta_{w}"] = etas_a[w]
        payload[f"anom_{w}"] = anoms[w]
        payload[f"start_{w}"] = starts[w]
    return payload


def _load_window_coefficients(store: Path, window_id: str) -> dict[str, Any]:
    """One window's coefficients from a persisted member store (lazy npz read)."""
    import numpy as np  # noqa: PLC0415

    with np.load(store, allow_pickle=False) as z:
        return {
            "eta": np.asarray(z[f"eta_{window_id}"]),
            "anom": np.asarray(z[f"anom_{window_id}"]),
            "start": float(z[f"start_{window_id}"]),
        }


def _seam_tile_leg(tile: str, *, m: int, maxiter: int, root: int) -> dict[str, Any]:
    """Solve one seam tile (m members, full production plan) and PERSIST it.

    Crash-durable at two levels — member-batch PCG checkpoints inside the
    window solve, and this leg's own member store afterwards, so a
    compare-phase death never costs the solves (the anchor-gate lesson).
    The mean and MEMBER-STD maps are written BEFORE any compare runs.

    Args:
        tile: ``seam_n`` or ``seam_s``.
        m: Ensemble members.
        maxiter: PCG iteration cap.
        root: CRN root (the anchor run's convention — the ORACLE compares
            like against like).

    Returns:
        The tile's solve provenance block.
    """
    import resource  # noqa: PLC0415
    import time  # noqa: PLC0415

    import numpy as np  # noqa: PLC0415

    import sverdrup.methods.miost as miost_mod  # noqa: PLC0415
    from sverdrup.core.parameters import ConstantProvider  # noqa: PLC0415
    from sverdrup.distributions.miost_ensemble import (  # noqa: PLC0415
        merged_members,
    )
    from sverdrup.methods.miost import PHASE13_WINNER_PARAMS  # noqa: PLC0415
    from sverdrup.methods.miost_windows import WindowPlan  # noqa: PLC0415
    from sverdrup.validation.input_adapter import load_mdt_grid  # noqa: PLC0415
    from sverdrup.validation.output_adapter import write_map  # noqa: PLC0415

    gate = _anchor_gate_module()
    t_leg = time.monotonic()
    frame, grid, framed = _seam_framed_obs(tile)
    n_obs = int(len(framed.values()))
    _seam_echo(f"{tile}: framed obs {n_obs}, grid {grid.x.size}x{grid.y.size}")

    plan = WindowPlan()
    provider = ConstantProvider(dict(PHASE13_WINNER_PARAMS))
    ckpt = STAGE1_DIR / f"{tile}_pcg_ckpt"
    ckpt.mkdir(parents=True, exist_ok=True)
    method = _seam_miost(frame, starts=None, maxiter=maxiter, ckpt_dir=ckpt)

    store = SEAM_MEMBER_STORE[tile]
    resumed = store.exists()
    if resumed:
        _seam_echo(f"{tile}: RESUME from own member store {store}")
        with np.load(store, allow_pickle=False) as z:
            wids = [str(w) for w in np.asarray(z["window_ids"])]
            etas_a = {w: np.asarray(z[f"eta_{w}"]) for w in wids}
            anoms = {w: np.asarray(z[f"anom_{w}"]) for w in wids}
            starts = {w: float(z[f"start_{w}"]) for w in wids}
            pcg_rows = json.loads(str(z["pcg_rows"][()]))
            solve_wall_s = float(z["solve_wall_s"])
        spec = method._spec_from(provider, grid)  # noqa: SLF001
    else:
        t_solve = time.monotonic()
        log_start = len(miost_mod.CONVERGENCE_LOG)
        spec, etas_a, anoms, starts = merged_members(
            method,
            framed,
            grid,
            provider,
            m,
            root,
            on_window=lambda wid, day: _seam_echo(
                f"{tile}: window {wid} solved (day {day:.0f}); "
                f"{time.monotonic() - t_leg:.0f}s"
            ),
        )
        pcg_rows = [dict(r) for r in miost_mod.CONVERGENCE_LOG[log_start:]]
        solve_wall_s = time.monotonic() - t_solve
        STAGE1_DIR.mkdir(parents=True, exist_ok=True)
        np.savez(
            store,
            **_store_payload(
                etas_a,
                anoms,
                starts,
                pcg_rows,
                solve_wall_s,
                f"SEAM-PAIR leg member store ({tile}); crash-resume "
                "substrate, never a reference",
            ),
        )
        _seam_echo(f"{tile}: member store persisted -> {store}")

    stamped, capped = classify_pcg_legs(
        pcg_rows, rtol=float(method.pcg_rtol), maxiter=int(method.pcg_maxiter)
    )
    days = [float(d) for d in range(SEAM_N_DAYS)]
    if not SEAM_MEAN_MAPS[tile].exists() or not SEAM_STD_MAPS[tile].exists():
        means = _lineage_mean_fields()(spec, starts, etas_a, grid, plan, days)
        stds = _lineage_std_fields()(spec, starts, anoms, grid, plan, days)
        mdt = np.asarray(load_mdt_grid([Path(p) for p in gate.MAPPING_SIX], grid))
        mean_stack = np.stack([mn.reshape(grid.shape) for mn in means]) + mdt[None]
        std_stack = np.stack([sd.reshape(grid.shape) for sd in stds])
        assimilated = tuple(sorted({str(s) for s in np.asarray(framed.mission)}))
        epoch = np.datetime64("2017-01-01")
        times = epoch + np.asarray(days, dtype="int64") * np.timedelta64(1, "D")
        write_map(
            times,
            grid.y,
            grid.x,
            mean_stack,
            SEAM_MEAN_MAPS[tile],
            assimilated_missions=assimilated,
        )
        write_map(
            times,
            grid.y,
            grid.x,
            std_stack,
            SEAM_STD_MAPS[tile],
            assimilated_missions=assimilated,
        )
        for p in (SEAM_MEAN_MAPS[tile], SEAM_STD_MAPS[tile]):
            gate._attach_label(p, "STAGE1-EVIDENCE")  # noqa: SLF001
        del means, stds, mean_stack, std_stack
        _seam_echo(f"{tile}: maps written (mean + member-std)")
    solve = frame.solve_bbox
    return {
        "tile": tile,
        "source": str(TILES[tile]["source"]),
        "n_obs": n_obs,
        "m": m,
        "root_int": root,
        "resumed_from_own_store": resumed,
        "frame": {
            "core": list(TILES[tile]["core"]),
            "overlap_deg": frame.overlap_deg,
            "halo_deg": frame.halo_deg,
            "missing_neighbors": sorted(frame.missing_neighbors),
            "solve_bbox": [solve.lon_min, solve.lon_max, solve.lat_min, solve.lat_max],
            "resolution_deg": RESOLUTION_DEG,
        },
        "window_plan": {
            "starts": list(plan.starts),
            "w_days": plan.w_days,
            "n_windows": len(plan.windows),
        },
        "pcg": stamped,
        "pcg_rtol": float(method.pcg_rtol),
        "pcg_maxiter": int(method.pcg_maxiter),
        "convergence": "CAPPED" if capped else "CONVERGED",
        "worst_residual": max(float(leg["final_rel_residual"]) for leg in stamped),
        "solve_wall_s": solve_wall_s,
        "leg_wall_s": time.monotonic() - t_leg,
        "peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0,
        "maps": {
            "mean": str(SEAM_MEAN_MAPS[tile]),
            "member_std": str(SEAM_STD_MAPS[tile]),
        },
        "member_store": str(store),
    }


def _floor_probe_tile(
    tile: str, *, m: int, store: Path, method_prod_maxiter: int
) -> dict[str, Any]:
    """Deeper-tolerance re-solve of ONE window; returns the strip shift fields.

    The reference is that tile's OWN production window-0 coefficients —
    same root, same window, same m, ONLY the tolerance differs — so the
    measured shift is a solver-convergence property and nothing else.
    The evaluation rides the Task-18 lineage's sparse S-path helpers by
    import (:func:`_diag_lineage`), never a local reimplementation.

    Args:
        tile: Registry tile name (a seam tile or ``anchor``).
        m: Members (see :data:`FLOOR_M_JUSTIFICATION`).
        store: The production member store to read the reference from.
        method_prod_maxiter: The cap the production solve ran under
            (recorded; the deeper solve raises it by 1000).

    Returns:
        Shift fields on the strip plus the deeper solve's convergence row.
    """
    import time  # noqa: PLC0415

    import numpy as np  # noqa: PLC0415

    import sverdrup.methods.miost as miost_mod  # noqa: PLC0415
    from sverdrup.core.parameters import ConstantProvider  # noqa: PLC0415
    from sverdrup.distributions.miost_ensemble import (  # noqa: PLC0415
        merged_members,
    )
    from sverdrup.methods.miost import PHASE13_WINNER_PARAMS  # noqa: PLC0415
    from sverdrup.methods.miost_windows import WindowPlan  # noqa: PLC0415

    t0 = time.monotonic()
    window = WindowPlan().windows[FLOOR_W_INDEX]
    day = float(_lineage_exclusive_days()(WindowPlan())[window.id])
    if tile == "anchor":
        gate = _anchor_gate_module()
        frame, grid, framed = gate._load_generalized_obs()  # noqa: SLF001
    else:
        frame, grid, framed = _seam_framed_obs(tile)
    provider = ConstantProvider(dict(PHASE13_WINNER_PARAMS))
    deep = _seam_miost(
        frame,
        starts=(window.start_day,),
        maxiter=FLOOR_MAXITER,
        rtol=FLOOR_RTOL,
    )
    _seam_echo(
        f"floor probe {tile}: window {window.id}, m={m}, rtol {FLOOR_RTOL:g}, "
        f"maxiter {FLOOR_MAXITER} (production cap {method_prod_maxiter})"
    )
    log_start = len(miost_mod.CONVERGENCE_LOG)
    root = int(_shipped_member_root())
    spec, etas_deep, anoms_deep, starts_deep = merged_members(
        deep, framed, grid, provider, m, root
    )
    legs = [dict(r) for r in miost_mod.CONVERGENCE_LOG[log_start:]]
    stamped, capped = classify_pcg_legs(
        legs, rtol=float(deep.pcg_rtol), maxiter=int(deep.pcg_maxiter)
    )
    ref = _load_window_coefficients(store, window.id)
    plan_one = WindowPlan(starts=(window.start_day,))
    starts_ref = {window.id: ref["start"]}

    def _fields(eta: Any, anom: Any, starts: dict[str, float]) -> tuple[Any, Any]:  # noqa: ANN401
        mean = _lineage_mean_fields()(
            spec, starts, {window.id: eta}, grid, plan_one, [day]
        )[0]
        std = _lineage_std_fields()(
            spec, starts, {window.id: anom}, grid, plan_one, [day]
        )[0]
        return mean.reshape(grid.shape), std.reshape(grid.shape)

    mean_deep, std_deep = _fields(
        etas_deep[window.id], anoms_deep[window.id], starts_deep
    )
    del etas_deep, anoms_deep
    mean_ref, std_ref = _fields(ref["eta"], ref["anom"], starts_ref)
    lat_m, lon_m = strip_mask(grid, seam_strip_bbox())
    sel = np.ix_(lat_m, lon_m)
    shift_mean = np.asarray(mean_deep[sel] - mean_ref[sel])
    shift_sigma = np.asarray(std_deep[sel] - std_ref[sel])
    worst = max(stamped, key=lambda leg: float(leg["final_rel_residual"]))
    _seam_echo(
        f"floor probe {tile}: {'CAPPED' if capped else 'CONVERGED'} in "
        f"{worst['iterations']} iters @ {worst['final_rel_residual']:.3e}; "
        f"max|mean shift| {np.abs(shift_mean).max():.3e} m, "
        f"max|sigma shift| {np.abs(shift_sigma).max():.3e} m "
        f"({time.monotonic() - t0:.0f}s)"
    )
    return {
        "tile": tile,
        "shift_mean": shift_mean,
        "shift_sigma": shift_sigma,
        "probe": {
            "rtol": float(deep.pcg_rtol),
            "maxiter": int(deep.pcg_maxiter),
            "iterations": int(worst["iterations"]),
            "final_rel_residual": float(worst["final_rel_residual"]),
            "converged": not capped,
            "m": m,
            "window": window.id,
            "production_maxiter": method_prod_maxiter,
            "legs": stamped,
            "wall_s": time.monotonic() - t0,
        },
    }


def _shipped_member_root() -> int:
    """The signed acceptance CRN root (the anchor run's roots convention)."""
    from sverdrup.methods.miost import shipped_miost5  # noqa: PLC0415

    root = shipped_miost5().member_root
    if root is None:  # pragma: no cover - the shipped config pins it
        raise RuntimeError("shipped_miost5().member_root is None — no CRN root")
    return int(root)


def _seam_pair_real_leg(
    *,
    m: int,
    maxiter: int,
    floor_plan: dict[str, Any],
    evidence_path: Path,
) -> dict[str, Any]:
    """Solve the pair, probe the floors, take BOTH reads, assemble the rows.

    Order is deliberate: both tiles are solved and their mean + member-std
    maps PERSISTED before anything is compared; a capped solve stops
    immediately (``seam_read`` refuses on residual > rtol, so a verdict
    could not be produced anyway); the floor probes run next; the compare
    phase reads the persisted maps, so it can be re-run without re-solving.

    Args:
        m: Ensemble members per tile.
        maxiter: Production PCG cap.
        floor_plan: The pre-stated floor-probe plan (Tier-1 arithmetic).
        evidence_path: The evidence store (tally guard + seal sha).

    Returns:
        ``{"rows": [...], "block": {...}, "stop": None | "PIN23"}``.
    """
    import gc  # noqa: PLC0415
    import resource  # noqa: PLC0415
    import threading  # noqa: PLC0415
    import time  # noqa: PLC0415

    import numpy as np  # noqa: PLC0415

    gate = _anchor_gate_module()
    t_wall = time.monotonic()
    store = json.loads(evidence_path.read_text())
    seal_sha = str(store["phase14"]["stage0"]["seal"]["sha"])
    tally_before = gate.snapshot_locked_tally(evidence_path)
    anchor_block = store["phase14"]["stage1"]["anchor_gate"]
    if not anchor_block.get("pass"):
        raise RuntimeError(
            "REFUSED: the anchor identity gate is not green — T4 consumes "
            "its maps as the seamless truth and does not run before it"
        )
    root = _shipped_member_root()
    date = datetime.now(UTC).date().isoformat()

    stop_beat = threading.Event()

    def _beat() -> None:
        while not stop_beat.wait(300.0):
            _seam_echo(
                f"heartbeat peak_rss="
                f"{resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0:.0f}"
                f"MiB mem_avail={_mem_available_mib():.0f}MiB"
            )

    threading.Thread(target=_beat, daemon=True).start()
    try:
        tiles = {}
        for tile in SEAM_PAIR_TILES:
            tiles[tile] = _seam_tile_leg(tile, m=m, maxiter=maxiter, root=root)
            gc.collect()
        block: dict[str, Any] = {
            "label": "SEAM-PAIR",
            "seal_sha": seal_sha,
            "pair": SEAM_PAIR_NAME,
            "era": SEAM_ERA,
            "m": m,
            "root_int": root,
            "roots_convention": (
                "shipped_miost5().member_root — the anchor run's root, on "
                "BOTH tiles: identity-keyed CRN so the ORACLE compares like "
                "against like"
            ),
            "tiles": tiles,
            "floor_plan": floor_plan,
            "geometry": SEAM_GEOMETRY,
            "non_transfer_note": SEAM_NON_TRANSFER_NOTE,
            "seamless_truth": {
                "mean": str(ANCHOR_MEAN_MAPS),
                "member_std": str(ANCHOR_STD_MAPS),
                "source": "phase14.stage1.anchor_gate (Task 3) — CONSUMED",
            },
            "tally_guard": {"before": tally_before},
            "date": date,
        }
        capped = [t for t, p in tiles.items() if p["convergence"] == "CAPPED"]
        if capped:
            block["convergence"] = "CAPPED"
            block["capped_tiles"] = capped
            return {"rows": [], "block": block, "stop": "PIN23"}
        block["convergence"] = "CONVERGED"

        floors, floor_block = _seam_floor_phase(
            floor_plan=floor_plan,
            m=int(floor_plan["m"]),
            maxiter=maxiter,
            anchor_maxiter=int(anchor_block["pcg"]["maxiter"]),
        )
        block["floor_probe"] = floor_block
        if floor_block.get("status") == "NOT_CONVERGED":
            return {"rows": [], "block": block, "stop": "FLOOR_NOT_CONVERGED"}
        gc.collect()
        rows = _seam_compare_phase(
            tiles=tiles,
            floors=floors,
            anchor_block=anchor_block,
            seal_sha=seal_sha,
            date=date,
        )
        block["wall_s"] = time.monotonic() - t_wall
        block["peak_rss_mib"] = (
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
        )
        block["mem_available_mib"] = _mem_available_mib()
        block["rows_recorded_at"] = f"phase14.stage1.{SEAM_ROWS_NODE}"
        block["n_strip_nodes"] = int(np.prod(floors["strip_shape"]))
        return {"rows": rows, "block": block, "stop": None}
    finally:
        stop_beat.set()


def _seam_floor_phase(
    *, floor_plan: dict[str, Any], m: int, maxiter: int, anchor_maxiter: int
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run (or WAIT on) the floor probes and reduce them to the four floors.

    PAIR floor: max|field shift| over the strip across BOTH tiles (the
    rubric's construction, run once per pair roster). ORACLE floor: its
    OWN — the max over the strip of the BLENDED shift and the SEAMLESS
    solve's own shift, because those are the two fields the oracle
    compares. The two floors are never shared: the oracle's includes a
    deeper re-solve of the seamless anchor that the pair's does not.

    Args:
        floor_plan: The pre-stated plan (carries the ladder verdict).
        m: Members for the probe.
        maxiter: The production cap the seam probes are deeper than.
        anchor_maxiter: The SIGNED cap the seamless anchor solve ran
            under (recorded on the Task-3 block — never restated).

    Returns:
        ``(floors, recorded_block)``.
    """
    import numpy as np  # noqa: PLC0415

    from sverdrup.application.spatial_tiles import (  # noqa: PLC0415
        assemble,
        frame_grid,
    )

    if not floor_plan["tier1_eligible"]:
        wait = floor_wait_block(
            reason=(
                "tier1_eligible refused the floor leg at predicted peak "
                f"{floor_plan['peak_model_mib']:.0f} MiB — the pair is "
                "UNMEASURED pending the owner, never silently skipped"
            )
        )
        grid = frame_grid(registry_frame("seam_n"), RESOLUTION_DEG)
        lat_m, lon_m = strip_mask(grid, seam_strip_bbox())
        floors = {
            "pair_mean": wait,
            "pair_sigma": wait,
            "oracle_mean": wait,
            "oracle_sigma": wait,
            "strip_shape": (int(lat_m.sum()), int(lon_m.sum())),
        }
        return floors, {"status": "WAIT", "plan": floor_plan}

    if SEAM_FLOOR_STORE.exists():
        # Crash resume: the probes are the second-most expensive thing this
        # leg buys (one deeper m=100 window solve per probed geometry); a
        # compare-phase death must not cost them either.
        _seam_echo(f"floor probes: RESUME from {SEAM_FLOOR_STORE}")
        with np.load(SEAM_FLOOR_STORE, allow_pickle=False) as z:
            recorded = json.loads(str(z["summary"][()]))
        floors = {
            "f_pair": recorded["f_pair"],
            "f_oracle": recorded["f_oracle"],
            "pair_probe": recorded["pair_probe"],
            "oracle_probe": recorded["oracle_probe"],
            "strip_shape": tuple(recorded["strip_shape"]),
        }
        return floors, recorded

    probes = {
        tile: _floor_probe_tile(
            tile, m=m, store=SEAM_MEMBER_STORE[tile], method_prod_maxiter=maxiter
        )
        for tile in SEAM_PAIR_TILES
    }
    probes["anchor"] = _floor_probe_tile(
        "anchor",
        m=m,
        store=ANCHOR_MEMBER_STORE,
        method_prod_maxiter=anchor_maxiter,
    )

    # The blended shift: the same partition-of-unity machinery the ORACLE's
    # blended field rides, applied to the two tiles' shift fields.
    grid_n = frame_grid(registry_frame("seam_n"), RESOLUTION_DEG)
    lat_m, lon_m = strip_mask(grid_n, seam_strip_bbox())
    lon2d, lat2d = np.meshgrid(grid_n.x[lon_m], grid_n.y[lat_m])
    frames = [registry_frame(t) for t in SEAM_PAIR_TILES]
    blended = {
        kind: assemble(
            frames,
            [probes[t][f"shift_{kind}"].ravel() for t in SEAM_PAIR_TILES],
            lon2d.ravel(),
            lat2d.ravel(),
        )
        for kind in ("mean", "sigma")
    }

    def _worst_probe(tiles: tuple[str, ...], scope: str) -> dict[str, Any]:
        rows = [probes[t]["probe"] for t in tiles]
        worst = max(rows, key=lambda r: float(r["final_rel_residual"]))
        return {
            **worst,
            "converged": all(bool(r["converged"]) for r in rows),
            "scope": scope,
            "tiles": list(tiles),
        }

    pair_probe = _worst_probe(
        SEAM_PAIR_TILES, "PAIR roster (seam_n + seam_s) re-solved deeper"
    )
    oracle_probe = _worst_probe(
        (*SEAM_PAIR_TILES, "anchor"),
        "ORACLE's OWN probe: the blended pair AND the seamless anchor "
        "re-solved deeper (never the pair's floor)",
    )
    if not (pair_probe["converged"] and oracle_probe["converged"]):
        # PIN 23: F between two truncation points is not a floor. RECORD the
        # probe rows (the owner needs exactly these numbers), claim no
        # verdict, and STOP — never an UNMEASURED row.
        return {}, {
            "status": "NOT_CONVERGED",
            "plan": floor_plan,
            "pair_probe": pair_probe,
            "oracle_probe": oracle_probe,
            "per_tile": {t: p["probe"] for t, p in probes.items()},
        }
    f_pair = {
        kind: max(
            float(np.nanmax(np.abs(probes[t][f"shift_{kind}"])))
            for t in SEAM_PAIR_TILES
        )
        for kind in ("mean", "sigma")
    }
    f_oracle = {
        kind: max(
            float(np.nanmax(np.abs(blended[kind]))),
            float(np.nanmax(np.abs(probes["anchor"][f"shift_{kind}"]))),
        )
        for kind in ("mean", "sigma")
    }
    floors = {
        "f_pair": f_pair,
        "f_oracle": f_oracle,
        "pair_probe": pair_probe,
        "oracle_probe": oracle_probe,
        "strip_shape": (int(lat_m.sum()), int(lon_m.sum())),
    }
    recorded = {
        "status": "RUN",
        "plan": floor_plan,
        "f_pair": f_pair,
        "f_oracle": f_oracle,
        "pair_probe": pair_probe,
        "oracle_probe": oracle_probe,
        "strip_shape": [int(lat_m.sum()), int(lon_m.sum())],
        "per_tile": {
            t: {
                "probe": p["probe"],
                "max_abs_shift_mean_m": float(np.nanmax(np.abs(p["shift_mean"]))),
                "max_abs_shift_sigma_m": float(np.nanmax(np.abs(p["shift_sigma"]))),
            }
            for t, p in probes.items()
        },
        "blended_max_abs_shift": {
            k: float(np.nanmax(np.abs(v))) for k, v in blended.items()
        },
    }
    np.savez(
        SEAM_FLOOR_STORE,
        **{
            f"shift_{k}_{t}": p[f"shift_{k}"]
            for t, p in probes.items()
            for k in ("mean", "sigma")
        },
        summary=json.dumps(recorded),
    )
    return floors, recorded


def _strip_fields(path: Path, tile: str) -> Any:  # noqa: ANN401 - ndarray
    """The (time, lat, lon) map on the 2·overlap strip of a tile's grid."""
    import numpy as np  # noqa: PLC0415
    import xarray as xr  # noqa: PLC0415

    from sverdrup.application.spatial_tiles import frame_grid  # noqa: PLC0415

    grid = frame_grid(registry_frame(tile), RESOLUTION_DEG)
    lat_m, lon_m = strip_mask(grid, seam_strip_bbox())
    with xr.open_dataset(path) as ds:
        values = np.asarray(ds["ssh"].values)
    return values[:, lat_m, :][:, :, lon_m]


def _interior_fields(path: Path, tile: str) -> Any:  # noqa: ANN401 - ndarray
    """The (time, lat, lon) map on a tile's rubric core interior."""
    import numpy as np  # noqa: PLC0415
    import xarray as xr  # noqa: PLC0415

    from sverdrup.application.spatial_tiles import frame_grid  # noqa: PLC0415

    frame = registry_frame(tile)
    grid = frame_grid(frame, RESOLUTION_DEG)
    lat_m, lon_m = core_interior_mask(frame, grid)
    with xr.open_dataset(path) as ds:
        values = np.asarray(ds["ssh"].values)
    return values[:, lat_m, :][:, :, lon_m]


def blend_strip(fields: dict[str, Any]) -> Any:  # noqa: ANN401 - ndarray
    """Blend the two seam tiles' per-day strip fields into the product field.

    The ORACLE route's own input: the tiling's partition-of-unity blend
    (``spatial_tiles.assemble``) applied day by day on the 2·overlap
    strip, exactly as the product would assemble it.

    Args:
        fields: ``tile -> (time, lat, lon)`` strip values for both seam
            tiles (same day count and strip shape).

    Returns:
        The blended ``(time, lat, lon)`` strip field.
    """
    import numpy as np  # noqa: PLC0415

    from sverdrup.application.spatial_tiles import (  # noqa: PLC0415
        assemble,
        frame_grid,
    )

    north = SEAM_PAIR_TILES[0]
    grid_n = frame_grid(registry_frame(north), RESOLUTION_DEG)
    lat_m, lon_m = strip_mask(grid_n, seam_strip_bbox())
    lon2d, lat2d = np.meshgrid(grid_n.x[lon_m], grid_n.y[lat_m])
    frames = [registry_frame(t) for t in SEAM_PAIR_TILES]
    shape = lon2d.shape
    return np.stack(
        [
            assemble(
                frames,
                [fields[t][d].ravel() for t in SEAM_PAIR_TILES],
                lon2d.ravel(),
                lat2d.ravel(),
            ).reshape(shape)
            for d in range(fields[north].shape[0])
        ]
    )


def _seam_compare_phase(
    *,
    tiles: dict[str, Any],
    floors: dict[str, Any],
    anchor_block: dict[str, Any],
    seal_sha: str,
    date: str,
) -> list[dict[str, Any]]:
    """Both reads on the persisted maps; four rubric rows out.

    Args:
        tiles: Per-tile solve provenance (residuals, rtol).
        floors: The floor phase's output.
        anchor_block: The Task-3 gate block (the seamless side's solver
            validity comes from ITS recorded pcg rows).
        seal_sha: The verified seal sha.
        date: ISO date string.

    Returns:
        Four rows: {pair, oracle} x {mean, sigma}.
    """
    north, south = SEAM_PAIR_TILES
    mean = {t: _strip_fields(SEAM_MEAN_MAPS[t], t) for t in SEAM_PAIR_TILES}
    sigma = {t: _strip_fields(SEAM_STD_MAPS[t], t) for t in SEAM_PAIR_TILES}
    int_mean = {t: _interior_fields(SEAM_MEAN_MAPS[t], t) for t in SEAM_PAIR_TILES}
    int_sigma = {t: _interior_fields(SEAM_STD_MAPS[t], t) for t in SEAM_PAIR_TILES}
    read_pair = pair_read(
        mean_a=mean[north],
        mean_b=mean[south],
        sigma_a=sigma[north],
        sigma_b=sigma[south],
        interior_mean_a=int_mean[north],
        interior_mean_b=int_mean[south],
        interior_sigma_a=int_sigma[north],
        interior_sigma_b=int_sigma[south],
        residual_a=float(tiles[north]["worst_residual"]),
        rtol_a=float(tiles[north]["pcg_rtol"]),
        residual_b=float(tiles[south]["worst_residual"]),
        rtol_b=float(tiles[south]["pcg_rtol"]),
    )
    _seam_echo(
        f"PAIR read: R_seam {read_pair.r_seam:.4f} ({read_pair.verdict}), "
        f"R_seam_sigma {read_pair.r_seam_sigma:.4f} ({read_pair.verdict_sigma})"
    )

    blended_mean = blend_strip(mean)
    blended_sigma = blend_strip(sigma)
    seamless_mean = _strip_fields(ANCHOR_MEAN_MAPS, "anchor")
    seamless_sigma = _strip_fields(ANCHOR_STD_MAPS, "anchor")
    anchor_pcg = anchor_block["pcg"]
    read_oracle = oracle_read(
        blended_mean=blended_mean,
        seamless_mean=seamless_mean,
        blended_sigma=blended_sigma,
        seamless_sigma=seamless_sigma,
        seamless_interior_mean=_interior_fields(ANCHOR_MEAN_MAPS, "anchor"),
        seamless_interior_sigma=_interior_fields(ANCHOR_STD_MAPS, "anchor"),
        residual_blend=max(float(tiles[t]["worst_residual"]) for t in SEAM_PAIR_TILES),
        rtol_blend=max(float(tiles[t]["pcg_rtol"]) for t in SEAM_PAIR_TILES),
        residual_seamless=max(
            float(r["final_rel_residual"]) for r in anchor_pcg["rows"]
        ),
        rtol_seamless=float(anchor_pcg["rtol"]),
    )
    _seam_echo(
        f"ORACLE read: R_seam {read_oracle.r_seam:.4f} ({read_oracle.verdict}), "
        f"R_seam_sigma {read_oracle.r_seam_sigma:.4f} "
        f"({read_oracle.verdict_sigma})"
    )

    def _floor_for(route: str, kind: str, rms: float) -> dict[str, Any]:
        if "f_pair" not in floors:  # the WAIT path
            wait: dict[str, Any] = floors[f"{route}_{kind}"]
            return wait
        key = "f_pair" if route == ROUTE_PAIR else "f_oracle"
        probe = floors["pair_probe" if route == ROUTE_PAIR else "oracle_probe"]
        return floor_attributability(
            rms_delta=rms, floor_f=floors[key][kind], probe=probe
        )

    return seam_rows_from_read(
        route=ROUTE_PAIR,
        read=read_pair,
        floor_mean=_floor_for(ROUTE_PAIR, "mean", read_pair.rms_delta),
        floor_sigma=_floor_for(ROUTE_PAIR, "sigma", read_pair.rms_sigma_delta),
        seal_sha=seal_sha,
        date=date,
    ) + seam_rows_from_read(
        route=ROUTE_ORACLE,
        read=read_oracle,
        floor_mean=_floor_for(ROUTE_ORACLE, "mean", read_oracle.rms_delta),
        floor_sigma=_floor_for(ROUTE_ORACLE, "sigma", read_oracle.rms_sigma_delta),
        seal_sha=seal_sha,
        date=date,
    )


@app.command()
def seam_pair(
    m: Annotated[int, typer.Option(help="Ensemble members per tile")] = SEAM_PAIR_M,
    maxiter: Annotated[
        int, typer.Option(help="Production PCG cap (owner PIN 26(b))")
    ] = STAGE1_PCG_MAXITER,
) -> None:
    """Task 4: the seam pair, the PRIMARY PAIR READ and the ORACLE READ.

    Runs ``seam_n`` and ``seam_s`` at the frozen signed config (m=100,
    full 9-window production plan, dc2021a, the anchor run's CRN root),
    persists each tile's mean AND member-std maps, probes the solver
    floor (deeper tolerance, pin 23's convergence precondition enforced),
    then takes BOTH reads on the 2·overlap strip and records four rubric
    rows under ``phase14.stage1.seam_rows``.

    Verdicts never block mechanically: a STRUCTURAL_STOP is recorded and
    surfaced to the owner (work on other tiles may continue — they do not
    consume seams).

    Args:
        m: Ensemble members per tile.
        maxiter: Production PCG iteration cap.

    Raises:
        RuntimeError: Tier-1 ladder refusal (via :func:`preflight`).
        typer.Exit: Nonzero on a failed RAM gate, on a capped seam solve
            (pin 23), and on a STRUCTURAL_STOP verdict.
    """
    models = {t: preflight(t, m) for t in SEAM_PAIR_TILES}
    peak = max(float(mo["peak_model_mib"]) for mo in models.values())
    gate = seam_ram_gate(peak_model_mib=peak, mem_available_mib=_mem_available_mib())
    typer.echo("ram_gate: " + json.dumps(gate))
    if not gate["passed"]:
        typer.echo(
            f"REFUSED: MemAvailable {gate['mem_available_mib']:.0f} MiB < "
            f"{SEAM_RAM_GATE_FACTOR:.0f} x predicted peak {peak:.0f} MiB — "
            "the seam pair WAITS; never launch over headroom (fork-g pin 4)"
        )
        raise typer.Exit(code=1)
    plan = floor_probe_plan()
    typer.echo(
        "floor_probe_plan (STATED BEFORE IT RUNS): "
        + json.dumps({k: plan[k] for k in ("m", "rtol", "maxiter", "n_windows")})
        + f" peak_model_mib={plan['peak_model_mib']:.0f} "
        f"tier1_eligible={plan['tier1_eligible']}"
    )
    result = _seam_pair_real_leg(
        m=m, maxiter=maxiter, floor_plan=plan, evidence_path=EVIDENCE
    )
    record_seam_block(result["block"], evidence_path=EVIDENCE)
    if result["rows"]:
        record_seam_rows(result["rows"], evidence_path=EVIDENCE)
    before = result["block"].get("tally_guard", {}).get("before")
    if before:
        _anchor_gate_module().assert_tally_unchanged(before, EVIDENCE)
    for row in result["rows"]:
        typer.echo(
            f"{row['route']}/{row['field_kind']}: rms_delta="
            f"{row['rms_delta']:.6g} d_int={row['d_int']:.6g} "
            f"R={row['r_seam']:.4f} cell={row['rubric_cell']} "
            f"verdict={row['verdict']}"
        )
    if result["stop"] == "PIN23":
        typer.echo(
            "STOP (owner PIN 23): a seam solve exited CAPPED over rtol — the "
            "block IS recorded and NO verdict is claimed; seam_read refuses "
            "on residual > rtol, so no reading exists to report."
        )
        raise typer.Exit(code=2)
    if result["stop"] == "FLOOR_NOT_CONVERGED":
        typer.echo(
            "STOP (owner PIN 23): the deeper-tolerance floor probe did NOT "
            "converge — the probe rows ARE recorded and NO verdict is "
            "claimed. F between two truncation points is not a floor and "
            "3xF has no meaning; this is an owner STOP, never an UNMEASURED "
            "verdict."
        )
        raise typer.Exit(code=2)
    stops = [r for r in result["rows"] if r["verdict"] == "STRUCTURAL_STOP"]
    if stops:
        typer.echo(
            "STRUCTURAL_STOP surfaced to the owner "
            f"({', '.join(f'{r["route"]}/{r["field_kind"]}' for r in stops)}): "
            "the rows ARE recorded; this verdict does NOT block the plan "
            "mechanically — work on other tiles may continue (they do not "
            "consume seams). Gate 1 owns the decision."
        )
        raise typer.Exit(code=3)
    typer.echo("seam pair done: rows at phase14.stage1.seam_rows")


def _solve_leg(tile: str, m: int, days_stride: int, maxiter: int) -> None:
    """The real load/solve/score/record leg — OWNED BY LATER GATED TASKS.

    Args:
        tile: Registry tile name.
        m: Ensemble members.
        days_stride: Output-day stride.
        maxiter: PCG iteration cap handed to the solver and recorded, per
            leg, in the tile evidence row (owner PIN 26(a): the cap a
            production row ran under is part of the row).

    Raises:
        NotImplementedError: Always — Stage-1 Task 3 (anchor identity
            gate), Task 4 (seam-pair run), and Task 5 (diverse-tile runs)
            own the real legs. (Task 2's measured-first probe LANDED as
            the separate ``probe`` command.)
    """
    raise NotImplementedError(
        f"tile {tile!r} (m={m}, days_stride={days_stride}, maxiter={maxiter}): "
        "the real solve legs are separately gated — Stage-1 Task 3 (anchor "
        "identity gate), Task 4 (seam-pair run), Task 5 (diverse-tile runs); "
        "Task 2's measured-first probe landed as the `probe` command."
    )


SIGMA_DIAGNOSIS_NODE = "seam_sigma_diagnosis"
NOT_ESTABLISHED_NODE = "sigma_rows_not_established"


@app.command()
def withhold_sigma_rows(
    evidence_path: Annotated[Path, typer.Option("--evidence-path")] = EVIDENCE,
) -> None:
    """Withhold both σ rows under the not-established firewall (pin 45b).

    NO SEAL IS TOUCHED and no solve runs. The establishing diagnosis is
    already committed, dual-reviewed and CONFIRMED; this records its
    consequence on the rows it is about. The rubric amendment that would
    have produced a verdict-bearing label is DEFERRED to one sealed version
    after T14/T15 (owner pin 45).

    Raises:
        typer.BadParameter: If the rows, the diagnosis or the seal pointer
            are missing, or if the rows are already withheld.
    """
    from sverdrup.validation import phase14_seal  # noqa: PLC0415

    phase14_seal.verify_current_seal(evidence_path)
    results = json.loads(evidence_path.read_text())
    stage1 = results.get("phase14", {}).get("stage1", {})
    rows = stage1.get(SEAM_ROWS_NODE)
    if not rows:
        raise typer.BadParameter(f"no phase14.stage1.{SEAM_ROWS_NODE} to withhold")
    if SIGMA_DIAGNOSIS_NODE not in stage1:
        raise typer.BadParameter(
            f"no phase14.stage1.{SIGMA_DIAGNOSIS_NODE}: the withholding cites "
            "the diagnosis as its establishing evidence and refuses without it"
        )
    if stage1.get(NOT_ESTABLISHED_NODE):
        raise typer.BadParameter(
            f"phase14.stage1.{NOT_ESTABLISHED_NODE} already recorded"
        )
    date = datetime.now(UTC).date().isoformat()
    ref = f"phase14.stage1.{SIGMA_DIAGNOSIS_NODE}"
    out: list[dict[str, Any]] = []
    withheld: list[dict[str, Any]] = []
    for row in rows:
        if row["field_kind"] != FIELD_KIND_SIGMA:
            out.append(row)
            continue
        marked = mark_not_established(row=row, diagnosis_ref=ref, date=date)
        out.append(marked)
        withheld.append(
            {
                "route": marked["route"],
                "prior_verdict": marked["not_established"]["prior_verdict"],
                "verdict": marked["verdict"],
                "r_seam_sigma": marked["r_seam"],
            }
        )
    stage1[SEAM_ROWS_NODE] = out
    stage1[NOT_ESTABLISHED_NODE] = {
        "label": "WITHHELD — NOT A VERDICT",
        "ruling": "docs/superpowers/2026-07-27-owner-ruling-crn-sigma-rule0.md",
        "pin": "45(b)",
        "diagnosis": ref,
        "withheld": withheld,
        "consequence": (
            "Stage 1 has NO attributable sigma-route seam verdict. The sigma "
            "seam question is UNANSWERED, not answered clean; the two "
            "mean-route CLEAN cells are the stage's only standing seam "
            "verdicts, and the C1->2 contract carries the sigma question "
            "forward OPEN (owner pins 37a, 37c)"
        ),
        "seal_untouched": (
            "no sealed instrument was amended: the rubric amendment is "
            "DEFERRED to one sealed version authored after T14 and T15, "
            "against the CRN-paired configuration that will then exist"
        ),
        "no_solves_run": True,
        "date": date,
    }
    from sverdrup.application.calibration.harness import (  # noqa: PLC0415
        atomic_write_json,
    )

    atomic_write_json(evidence_path, results)
    for w in withheld:
        typer.echo(f"{w['route']}/sigma: {w['prior_verdict']} -> {w['verdict']}")


@app.command()
def run(
    tile: Annotated[str, typer.Argument(help="Registry tile name")],
    m: Annotated[int, typer.Option(help="Ensemble members retained")] = 100,
    days_stride: Annotated[int, typer.Option(help="Output-day stride")] = 1,
    maxiter: Annotated[
        int,
        typer.Option(
            help=(
                "PCG iteration cap for this run (default: the measured "
                "Stage-1 cap STAGE1_PCG_MAXITER = 2x the converged "
                "19-degree probe's worst leg). The library default 500 "
                "caps every 19-degree leg un-converged — owner PIN 26(b)."
            )
        ),
    ] = STAGE1_PCG_MAXITER,
) -> None:
    """One Stage-1 tile run: registry frame, pinned source, frozen config.

    There is deliberately NO source option: the Stage-0 pin-4 source map
    lives in the registry and is recorded as provenance, never chosen at
    the command line.

    Args:
        tile: Registry tile name.
        m: Ensemble members retained.
        days_stride: Output-day stride.
        maxiter: PCG iteration cap, threaded to the solve leg and recorded
            per pcg leg in the tile evidence row.

    Raises:
        typer.BadParameter: Unknown tile.
        RuntimeError: Tier-1 ladder refusal (via :func:`preflight`).
    """
    if tile not in TILES:
        raise typer.BadParameter(f"unknown tile {tile!r}; known: {sorted(TILES)}")
    model = preflight(tile, m)
    typer.echo(json.dumps({k: round(v, 1) for k, v in model.items()}))
    _solve_leg(tile, m, days_stride, maxiter)


if __name__ == "__main__":
    app()
