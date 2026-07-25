"""Phase-14 Stage-1 per-tile run driver (Stage-1 Task 1 — CI-testable core).

ONE command runs one roster tile: frame from the registry, source-mapped
load (the Stage-0 pin-4 source map — per-tile source is REGISTRY
provenance, never a CLI option), frozen signed config, evidence row under
``phase14.stage1.tiles.<tile>`` quoting the seal sha.

THIS module ships the CI-testable core only: registry + frames, refusals
(unknown tile, pending owner elections, Tier-1 ladder, unverified seal),
and pure evidence-row assembly. The real load/solve/score legs are
separately gated Stage-1 tasks (2 probe / 3 anchor gate / 4 seam pair /
5 diverse tiles) and land behind :func:`_solve_leg`.

Standing refusals wired here:

- **Diverse-frame convention (plan pin 2):** the ``missing_neighbors``
  convention for the four diverse tiles is an OWNER ELECTION PENDING;
  while :data:`DIVERSE_FRAME_CONVENTION` is ``None`` their frames REFUSE.
- **Equatorial box (owner pin 12):** the box election is pending; ``run``
  refuses BEFORE any frame/load work.
- **Tier-1 ladder (fork-g pin 4):** :func:`preflight` sizes the tile and
  checks ``tier1_eligible`` BEFORE any load — never launch over headroom.
- **Seal tripwire (Task 10):** :func:`record_evidence_row` verifies the
  current seal before anything is written.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer

if TYPE_CHECKING:
    from sverdrup.application.spatial_tiles import TileFrame

app = typer.Typer(add_completion=False)

EVIDENCE = Path("data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json")
RESOLUTION_DEG = 0.2

# Probe-pinned sizing inputs (plan Task 15 probe leg): frozen-config
# direction count and smallest wavelength used by the Task-22 arithmetic.
_SIZING_N_DIR = 8
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
        "box_election_pending": True,  # owner pin 12 — run refuses
        "job": "in-band core crossing the 10N component edge",
    },
    "southern": {
        "core": (215.0, 230.0, -62.0, -47.0),
        "source": "cmems_my",
        "job": (
            "high-latitude honesty instrument (~54.5S center; "
            "obs southern edge = solve_bbox.lat_min - halo; "
            "+/-66 headroom set by the frame convention)"
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

# OWNER ELECTION PENDING (plan pin 2): the missing_neighbors convention for
# the four diverse tiles (equatorial/southern/quiet_gyre/kuroshio) is not
# ruled. While None, building their frames REFUSES.
DIVERSE_FRAME_CONVENTION: str | None = (
    None  # ruled: "isolated" | "production-representative"
)

# Review pin 7 — VERBATIM on every cmems_my row: the golden-tile bridge
# delta carries its own provenance and disclaims transfer to other tiles.
BRIDGE_CAVEAT = (
    "cross-lineage reading; golden-tile bridge delta MEASURED ON THE ANCHOR "
    "BOX (mu -0.012457 their_eval-scale, map RMS 4.10 cm); its magnitude at "
    "THIS tile is unmeasured; interpretation WAITS on the owner attribution "
    "readout"
)


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
        raise NotImplementedError(
            "ruled diverse-frame convention wiring lands with the "
            "diverse-tile run legs (Stage-1 Task 5)"
        )
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
        n_dir=_SIZING_N_DIR,
        lam_min=_SIZING_LAM_MIN_KM,
    )
    if not ladder.tier1_eligible(model["peak_model_mib"]):
        raise RuntimeError(
            f"tile {tile!r}: predicted peak {model['peak_model_mib']:.0f} "
            "MiB fails the Tier-1 measured-RAM ladder predicate (fork-g "
            "pin 4) — the run WAITS; never launch over headroom"
        )
    return model


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
    pcg: object,
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
        pcg: Per-window PCG convergence rows.
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
        "pcg": pcg,
        "scores": scores,
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


def _solve_leg(tile: str, m: int, days_stride: int) -> None:
    """The real load/solve/score/record leg — OWNED BY LATER GATED TASKS.

    Args:
        tile: Registry tile name.
        m: Ensemble members.
        days_stride: Output-day stride.

    Raises:
        NotImplementedError: Always — Stage-1 Task 2 (measured-first
            probe), Task 3 (anchor identity gate), Task 4 (seam-pair run),
            and Task 5 (diverse-tile runs) own the real legs.
    """
    raise NotImplementedError(
        f"tile {tile!r} (m={m}, days_stride={days_stride}): the real solve "
        "legs are separately gated — Stage-1 Task 2 (measured-first probe), "
        "Task 3 (anchor identity gate), Task 4 (seam-pair run), Task 5 "
        "(diverse-tile runs). This driver ships the CI-testable core only."
    )


@app.command()
def run(
    tile: Annotated[str, typer.Argument(help="Registry tile name")],
    m: Annotated[int, typer.Option(help="Ensemble members retained")] = 100,
    days_stride: Annotated[int, typer.Option(help="Output-day stride")] = 1,
) -> None:
    """One Stage-1 tile run: registry frame, pinned source, frozen config.

    There is deliberately NO source option: the Stage-0 pin-4 source map
    lives in the registry and is recorded as provenance, never chosen at
    the command line.

    Args:
        tile: Registry tile name.
        m: Ensemble members retained.
        days_stride: Output-day stride.

    Raises:
        typer.BadParameter: Unknown tile.
        RuntimeError: Pending owner election (equatorial box, pin 12) or
            Tier-1 ladder refusal.
    """
    if tile not in TILES:
        raise typer.BadParameter(f"unknown tile {tile!r}; known: {sorted(TILES)}")
    # BEFORE any frame/load work (owner pin 12): the equatorial box
    # election is pending — nothing may be sized, loaded, or recorded.
    if TILES[tile].get("box_election_pending"):
        raise RuntimeError(
            f"tile {tile!r}: box election PENDING (owner pin 12) — the run "
            "REFUSES before any frame/load work until the owner rules the box"
        )
    model = preflight(tile, m)
    typer.echo(json.dumps({k: round(v, 1) for k, v in model.items()}))
    _solve_leg(tile, m, days_stride)


if __name__ == "__main__":
    app()
