"""Phase-14 Stage-1 per-tile run driver (Stage-1 Task 1 — CI-testable core).

ONE command runs one roster tile: frame from the registry, source-mapped
load (the Stage-0 pin-4 source map — per-tile source is REGISTRY
provenance, never a CLI option), frozen signed config, evidence row under
``phase14.stage1.tiles.<tile>`` quoting the seal sha.

THIS module ships the CI-testable core plus the Task-2 measured-first
``probe`` command (quiet_gyre, ONE 60-day window, m=1, PROBE-labeled,
record-then-stop 1.3x bracket). The remaining real load/solve/score legs
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
    from sverdrup.application.spatial_tiles import TileFrame

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
# The frozen five-mission mapping config (j3 stays the holdout convention);
# CMEMS-MY directory codes (h2g -> h2ag on this source).
PROBE_MISSIONS = ("alg", "h2ag", "j2g", "j2n", "s3a")
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


def build_probe_row(
    *,
    frame: dict[str, Any],
    window: list[float],
    superobs_cfg: dict[str, Any] | None,
    n_obs: int,
    n_grid_nodes: int,
    wall_s: float,
    peak_rss_mib: float,
    pcg: object,
    model: dict[str, float],
    date: str,
) -> dict[str, Any]:
    """Assemble the Task-2 probe evidence row — PURE, schema pinned.

    The probe is a SIZING measurement, never an evaluation: there is NO
    scores block (a probe row with a µ would be an evaluation-bearing
    artifact) and ``m`` is pinned to 1. ``measured_vs_model`` carries the
    measured/model ratios; ``stop_bracket`` trips when EITHER ratio
    STRICTLY exceeds the 1.3x honest-bracket convention.

    Args:
        frame: Frame provenance block (core/overlap/halo/solve bbox).
        window: ``[start, end]`` in solver days (since 2017-01-01).
        superobs_cfg: The applied super-obs cfg (cmems side).
        n_obs: In-window (support-widened) observation count — the same
            count fed to the sizing model.
        n_grid_nodes: Solve grid node count.
        wall_s: Measured wall time [s].
        peak_rss_mib: Measured peak RSS [MiB].
        pcg: Per-window PCG convergence rows.
        model: The ``size_tile`` output at the probe's own geometry.
        date: ISO date string (passed in — purity).

    Returns:
        The probe row (exactly the pinned key set).
    """
    wall_ratio = wall_s / model["wall_est_s"]
    peak_ratio = peak_rss_mib / model["peak_model_mib"]
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
        "pcg": pcg,
        "model": model,
        "measured_vs_model": {"wall_ratio": wall_ratio, "peak_ratio": peak_ratio},
        "stop_bracket": {
            "threshold": PROBE_STOP_THRESHOLD,
            "tripped": (
                wall_ratio > PROBE_STOP_THRESHOLD or peak_ratio > PROBE_STOP_THRESHOLD
            ),
        },
        "date": date,
    }


def record_probe_row(row: dict[str, Any], evidence_path: Path = EVIDENCE) -> None:
    """Record the probe row under ``phase14.stage1.probe`` — seal-gated.

    Same ceremony as :func:`record_evidence_row`: the CURRENT seal is
    verified FIRST (Task-10 tripwire — nothing is written while no
    verified seal exists), then an atomic merge into the standing store.

    Args:
        row: The probe row from :func:`build_probe_row`.
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
    results.setdefault("phase14", {}).setdefault("stage1", {})["probe"] = row
    atomic_write_json(evidence_path, results)


def _probe_solve() -> dict[str, Any]:
    """The Task-2 measured leg: load, one-window solve, PROBE map, measure.

    Follows the Stage-0 tile-sizing probe pattern (`phase14_probe.py`):
    CMEMS load clipped to the frame's obs bbox, challenge-coarsen
    super-obs, ObsWindow rebuild into the solver frame, ``Miost`` with the
    solve bbox as km-plane basis domain, single-window plan, m=1 merged
    members, one mid-window mean day. The sizing model is computed at the
    probe's OWN geometry (one window, m=1, measured in-window obs count)
    so the recorded ratios compare like with like. Constants are NOT
    retuned here (the Phase-12 precedent — ratios recorded only).

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

    frame = registry_frame(PROBE_TILE)
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
        m_members=PROBE_M,
        n_obs=n_obs_window,
        alpha=float(PHASE13_WINNER_PARAMS["spacing_alpha"]),
        n_dir=N_DIR,
        lam_min=_SIZING_LAM_MIN_KM,
    )

    method = Miost(basis_domain=(float(x0), float(y0), float(x1 - x0), float(y1 - y0)))
    method._plan = WindowPlan(starts=(PROBE_W_START,))  # noqa: SLF001
    provider = ConstantProvider(dict(PHASE13_WINNER_PARAMS))
    root = derive_seed("miost", "phase14-stage1-probe", PROBE_TILE, 0)
    log_start = len(miost_mod.CONVERGENCE_LOG)
    t_wall = time.monotonic()
    spec, etas_a, _anoms, starts = merged_members(
        method, framed, grid, provider, PROBE_M, root
    )
    days = [PROBE_W_START + PROBE_W_DAYS / 2.0]
    means = mean_fields(spec, starts, etas_a, grid, method._plan, days)  # noqa: SLF001
    wall_s = time.monotonic() - t_wall
    peak_mib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    pcg_rows = list(miost_mod.CONVERGENCE_LOG[log_start:])

    STAGE1_DIR.mkdir(parents=True, exist_ok=True)
    frame_block: dict[str, Any] = {
        "core": list(TILES[PROBE_TILE]["core"]),
        "overlap_deg": frame.overlap_deg,
        "halo_deg": frame.halo_deg,
        "missing_neighbors": sorted(frame.missing_neighbors),
        "solve_bbox": [solve.lon_min, solve.lon_max, solve.lat_min, solve.lat_max],
        "convention": DIVERSE_FRAME_CONVENTION,
        "resolution_deg": RESOLUTION_DEG,
    }
    window = [PROBE_W_START, PROBE_W_START + PROBE_W_DAYS]
    np.savez(
        STAGE1_DIR / "probe_quiet_gyre_mean.npz",
        mean=means,
        label="PROBE",
        provenance=json.dumps(
            {
                "tile": PROBE_TILE,
                "frame": frame_block,
                "missions": list(PROBE_MISSIONS),
                "window": window,
                "m": PROBE_M,
                "days": days,
            }
        ),
    )
    return {
        "frame": frame_block,
        "window": window,
        "superobs_cfg": superobs_cfg,
        "n_obs": n_obs_window,
        "n_grid_nodes": n_nodes,
        "wall_s": wall_s,
        "peak_rss_mib": peak_mib,
        "pcg": pcg_rows,
        "model": model,
    }


@app.command()
def probe() -> None:
    """The Task-2 measured-first sizing re-check — BEFORE any full run.

    quiet_gyre tile (CMEMS source — the first real CMEMS-side solve at the
    production-representative 19° solve geometry), ONE 60-day window, m=1,
    single mid-window day map, PROBE-labeled artifacts. Record-then-stop:
    a tripped 1.3x bracket exits nonzero AFTER the row is recorded (never
    a silent stop).

    Raises:
        RuntimeError: Tier-1 ladder refusal (via :func:`preflight`).
        typer.Exit: Nonzero when the STOP bracket trips.
    """
    preflight_model = preflight(PROBE_TILE, PROBE_M)
    typer.echo(
        "preflight model: "
        + json.dumps({k: round(v, 1) for k, v in preflight_model.items()})
    )
    measured = _probe_solve()
    row = build_probe_row(date=datetime.now(UTC).date().isoformat(), **measured)
    record_probe_row(row, evidence_path=EVIDENCE)
    typer.echo("measured_vs_model: " + json.dumps(row["measured_vs_model"]))
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


def _solve_leg(tile: str, m: int, days_stride: int) -> None:
    """The real load/solve/score/record leg — OWNED BY LATER GATED TASKS.

    Args:
        tile: Registry tile name.
        m: Ensemble members.
        days_stride: Output-day stride.

    Raises:
        NotImplementedError: Always — Stage-1 Task 3 (anchor identity
            gate), Task 4 (seam-pair run), and Task 5 (diverse-tile runs)
            own the real legs. (Task 2's measured-first probe LANDED as
            the separate ``probe`` command.)
    """
    raise NotImplementedError(
        f"tile {tile!r} (m={m}, days_stride={days_stride}): the real solve "
        "legs are separately gated — Stage-1 Task 3 (anchor identity gate), "
        "Task 4 (seam-pair run), Task 5 (diverse-tile runs); Task 2's "
        "measured-first probe landed as the `probe` command."
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
        RuntimeError: Tier-1 ladder refusal (via :func:`preflight`).
    """
    if tile not in TILES:
        raise typer.BadParameter(f"unknown tile {tile!r}; known: {sorted(TILES)}")
    model = preflight(tile, m)
    typer.echo(json.dumps({k: round(v, 1) for k, v in model.items()}))
    _solve_leg(tile, m, days_stride)


if __name__ == "__main__":
    app()
