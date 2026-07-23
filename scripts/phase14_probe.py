"""Phase-14 probe legs (0b-1 tile probe; 0b-3 Tier-2 report lands T18).

``tile-sizing``: the ONE measured production-geometry tile probe at
reduced days. PINNED config (plan Task 15): frame = 15°×15° core
lon [292, 307]°E lat [30, 45]°N + 2° overlap + 1.0° halo (contains the
signed box); ONE 60-day window 2017-01-15 → 2017-03-15; mean solve +
member 0 only; five CMEMS mapping missions (alg, h2ag, j2g, j2n, s3a —
j3 stays the holdout convention); PROBE-labeled outputs; Tier 0/1.

The Tier-1 launch check runs FIRST (measured MemAvailable, fork-g pin 4).
The sizing model is NOT retuned in-code — measured-vs-model ratios are
recorded (the Phase-12 re-grounding precedent). NO source edits during
the timed run (standing memory).
"""

from __future__ import annotations

import json
import math
import resource
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import numpy as np
import typer

app = typer.Typer(add_completion=False)

EVIDENCE = Path("data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json")
PROBE_DIR = Path("data/2021a_ssh_mapping_ose/ours/phase14_probe")

# The pinned probe frame + window (plan Task 15).
PROBE_CORE = (292.0, 307.0, 30.0, 45.0)
PROBE_T0 = np.datetime64("2017-01-15")
PROBE_MISSIONS = ("alg", "h2ag", "j2g", "j2n", "s3a")
_DAYS_1993_TO_2017 = 8766.0


def _plane(lon: float, lat: float) -> tuple[float, float]:
    """The shared km plane (miost_basis convention, box-anchored)."""
    from sverdrup.methods.miost_sizing import (  # noqa: PLC0415
        BOX_LAT,
        BOX_LON,
        KM_PER_DEG,
        MID_LAT,
    )

    x = (lon - BOX_LON[0]) * KM_PER_DEG * math.cos(math.radians(MID_LAT))
    y = (lat - BOX_LAT[0]) * KM_PER_DEG
    return x, y


@app.command("tile-sizing")
def tile_sizing(
    dry_run: Annotated[
        bool, typer.Option(help="Predict + Tier-1 check only, no solve")
    ] = False,
) -> None:
    """The pinned Tier-0/1 tile probe: predict, check RAM, solve, record."""
    import sverdrup.methods.miost as miost_mod  # noqa: PLC0415
    from sverdrup.adapters.altimetry import BBox  # noqa: PLC0415
    from sverdrup.adapters.altimetry.cmems_my import CmemsMySource  # noqa: PLC0415
    from sverdrup.application.ladder import tier1_eligible  # noqa: PLC0415
    from sverdrup.application.spatial_tiles import (  # noqa: PLC0415
        TileFrame,
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
    from sverdrup.methods.miost_sizing import size_tile  # noqa: PLC0415
    from sverdrup.methods.miost_windows import WindowPlan  # noqa: PLC0415
    from sverdrup.validation.params import OBS_NOISE_VARIANCE  # noqa: PLC0415

    lon_min, lon_max, lat_min, lat_max = PROBE_CORE
    frame = TileFrame(
        core=BBox(lon_min, lon_max, lat_min, lat_max),
        overlap_deg=2.0,
        halo_deg=1.0,
    )
    grid = frame_grid(frame, resolution_deg=0.2)
    n_nodes = int(grid.x.size * grid.y.size)

    # obs: five-mission CMEMS subset over the window + temporal support
    src = CmemsMySource()
    obs_93 = src.load(
        frame.obs_bbox(resolution_deg=0.2),
        np.datetime64("2016-12-20"),
        np.datetime64("2017-04-10"),
        missions=PROBE_MISSIONS,
    )
    c = obs_93.coords()
    obs = ObsWindow.from_arrays(
        c[:, 0],
        c[:, 1],
        c[:, 2] - _DAYS_1993_TO_2017,  # -> days since 2017-01-01 (solver frame)
        obs_93.values(),
        DiagonalErrorModel(np.full(len(obs_93), OBS_NOISE_VARIANCE)),
        mission=obs_93.mission,
    )
    framed = frame_obs(obs, frame, resolution_deg=0.2)

    params = dict(PHASE13_WINNER_PARAMS)
    alpha = float(params["spacing_alpha"])
    solve = frame.solve_bbox
    x0, y0 = _plane(solve.lon_min, solve.lat_min)
    x1, y1 = _plane(solve.lon_max, solve.lat_max)
    w_start = float((PROBE_T0 - np.datetime64("2017-01-01")) / np.timedelta64(1, "D"))
    t_mask = (framed.coords()[:, 2] >= w_start - 12.0) & (
        framed.coords()[:, 2] <= w_start + 72.0
    )
    n_obs_est = int(t_mask.sum())

    model = size_tile(
        d_x_km=x1 - x0,
        d_y_km=y1 - y0,
        n_grid_nodes=n_nodes,
        window_days=60.0,
        n_windows=1,
        m_members=1,
        n_obs=n_obs_est,
        alpha=alpha,
        n_dir=8,
        lam_min=80.0,
    )
    typer.echo(f"model: {json.dumps({k: round(v, 1) for k, v in model.items()})}")

    # Tier-1 launch check FIRST (fork-g pin 4)
    if not tier1_eligible(model["peak_model_mib"]):
        typer.echo(
            "REFUSED: predicted peak exceeds the Tier-1 measured-RAM "
            "predicate — the probe WAITS (never launch over headroom)"
        )
        raise typer.Exit(code=1)
    typer.echo("tier-1 launch check: ELIGIBLE (measured MemAvailable)")
    if dry_run:
        return

    method = Miost(basis_domain=(x0, y0, x1 - x0, y1 - y0))
    method._plan = WindowPlan(starts=(w_start,))
    provider = ConstantProvider(params)
    root = derive_seed("miost", "phase14-probe", "tile", 0)
    log_start = len(miost_mod.CONVERGENCE_LOG)
    t_wall = time.monotonic()
    spec, etas_a, anoms, starts = merged_members(
        method, framed, grid, provider, 1, root
    )
    days = [w_start + 30.0]
    means = mean_fields(spec, starts, etas_a, grid, method._plan, days)
    wall_s = time.monotonic() - t_wall
    peak_mib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    pcg_rows = list(miost_mod.CONVERGENCE_LOG[log_start:])

    PROBE_DIR.mkdir(parents=True, exist_ok=True)
    np.savez(
        PROBE_DIR / "tile_probe_mean.npz",
        mean=means,
        label="PROBE",
        provenance=json.dumps({"frame": PROBE_CORE, "missions": PROBE_MISSIONS}),
    )
    record: dict[str, Any] = {
        "label": "PROBE",
        "frame_core": list(PROBE_CORE),
        "missions": list(PROBE_MISSIONS),
        "window": [w_start, w_start + 60.0],
        "n_obs": int(len(framed)),
        "n_obs_window": n_obs_est,
        "n_grid_nodes": n_nodes,
        "wall_s": wall_s,
        "peak_rss_mib": peak_mib,
        "pcg": pcg_rows,
        "model": model,
        "measured_vs_model": {
            "wall_ratio": wall_s / model["wall_est_s"],
            "peak_ratio": peak_mib / model["peak_model_mib"],
        },
        "date": datetime.now(UTC).date().isoformat(),
        "note": "model NOT retuned in-code; ratios recorded (Phase-12 precedent)",
    }
    if EVIDENCE.exists():
        from sverdrup.application.calibration.harness import (  # noqa: PLC0415
            atomic_write_json,
        )

        results = json.loads(EVIDENCE.read_text())
        results.setdefault("phase14", {}).setdefault("stage0", {})["probe_tile"] = (
            record
        )
        atomic_write_json(EVIDENCE, results)
    typer.echo(json.dumps(record["measured_vs_model"], indent=1))
    typer.echo(f"PROBE tile solve done: wall {wall_s:.1f} s, peak {peak_mib:.0f} MiB")


if __name__ == "__main__":
    app()
