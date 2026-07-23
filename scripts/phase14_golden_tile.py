"""Golden-tile cross-source comparison (phase-14 0c-5; the CROSS-DT BRIDGE).

Same tile, same period, same FROZEN signed config through two sources —
map deltas + track-metric deltas, RECORDED; divergence TABLES, never
blocks Stage 1 (owner pin 3 + DT-vintage ruling item 1).

Pre-registration (sharpened): tile = the ANCHOR box, period = 2017,
config = frozen signed (``shipped_miost5`` + PHASE13_WINNER_PARAMS) — the
comparison's meaning is "what would the signed numbers have been on
CMEMS-MY directly". Under the ratified ``_202411`` vintage this measures
the CROSS-DT bridge (repackaging and DT-generation deltas inseparable —
conflation recorded honestly; AVISO DT2021 decomposition is the
owner-electable ledger row).

Mission relabeling (recorded): CMEMS codes map to the challenge codes
(``CHALLENGE_TO_CMEMS`` inverse, h2ag→h2g) BEFORE the solve so the frozen
config's mission-keyed R applies identically on both sides. Both sides
score the SAME challenge j3 track — the delta isolates input lineage.

NO verdict logic: numbers + a ``tabled_for_owner`` flag when any delta
exceeds its pre-registered recording threshold (all deltas recorded
regardless). PROBE-labeled artifacts; never validation-scored beyond the
j3 µ row this instrument is defined by.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import numpy as np
import typer

from sverdrup.core.observations import ObsWindow

if TYPE_CHECKING:
    from sverdrup.adapters.altimetry import BBox
    from sverdrup.core.grid import GridSpec

app = typer.Typer(add_completion=False)

EVIDENCE = Path("data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json")
PROBE_DIR = Path("data/2021a_ssh_mapping_ose/ours/phase14_probe")
_J3_TRACK = Path(
    "data/2021a_ssh_mapping_ose/dc_obs/"
    "dt_gulfstream_j3_phy_l3_20161201-20180131_285-315_23-53.nc"
)
_DAYS_1993_TO_2017 = 8766.0
_MAPPING_FIVE = ("alg", "h2g", "j2g", "j2n", "s3a")  # challenge codes

# Pre-registered recording thresholds (TABLES the row for the owner —
# never a block): ~2x the phase-13 pair band on mu; 1 cm map RMS.
TABLED_MU_DELTA = 0.002
TABLED_MAP_RMS_M = 0.01


def compute_deltas(maps_a: np.ndarray, maps_b: np.ndarray) -> dict[str, float]:
    """Map-delta arithmetic: overall RMS, max-abs, worst-day RMS."""
    d = np.asarray(maps_a, dtype=float) - np.asarray(maps_b, dtype=float)
    per_day_rms = np.sqrt(np.nanmean(d.reshape(d.shape[0], -1) ** 2, axis=1))
    return {
        "rms_m": float(np.sqrt(np.nanmean(d**2))),
        "max_abs_m": float(np.nanmax(np.abs(d))),
        "worst_day_rms_m": float(per_day_rms.max()),
    }


def tabled_flag(map_deltas: dict[str, float], mu_delta: float) -> bool:
    """The pre-registered recording thresholds (record always, flag over)."""
    return abs(mu_delta) > TABLED_MU_DELTA or map_deltas["rms_m"] > TABLED_MAP_RMS_M


def cmems_load_bbox(grid: GridSpec, halo_deg: float = 1.0) -> BBox:
    """The CMEMS load region: grid NODE extent ± halo (the halo_obs rule).

    Loading the globe pulls every daily file's full track (~100M 1-Hz
    samples) and OOM-kills the run (observed exit 137, 2026-07-22);
    conformance-exact clipping to the framing region yields the identical
    framed set. Clip-then-coarsen is the recorded transform semantic —
    the probe's wiring and the signed convention's regional inputs.
    """
    from sverdrup.adapters.altimetry import BBox  # noqa: PLC0415

    lon_nodes, lat_nodes = grid._lonlat_nodes()
    return BBox(
        float(lon_nodes.min()) - halo_deg,
        float(lon_nodes.max()) + halo_deg,
        float(lat_nodes.min()) - halo_deg,
        float(lat_nodes.max()) + halo_deg,
    )


def superobs_cfg_for(source_id: str) -> dict[str, object] | None:
    """The super-obs cfg applied to a side — the SAME object the record keeps.

    CMEMS raw 1-Hz needs the signed convention's time-coarsen (fork-a
    pin 4: parameterized and recorded in provenance); dc2021a is already
    at the signed density, so its cfg is None (identity).
    """
    from sverdrup.validation.params import COARSEN_TIME  # noqa: PLC0415

    if source_id == "cmems_my":
        return {"kind": "challenge-coarsen", "n": COARSEN_TIME}
    if source_id == "dc2021a":
        return None
    raise ValueError(f"unknown source {source_id!r}")


def _load_side(source_id: str) -> tuple[ObsWindow, dict[str, str], dict[str, int]]:
    """(framed ObsWindow in the solver frame, descriptor sha, per-mission n)."""
    from sverdrup.adapters.altimetry import (
        BBox,  # noqa: PLC0415
        apply_superobs,  # noqa: PLC0415
    )
    from sverdrup.adapters.altimetry.cmems_my import (  # noqa: PLC0415
        CHALLENGE_TO_CMEMS,
        CmemsMySource,
    )
    from sverdrup.adapters.altimetry.dc2021a import Dc2021aSource  # noqa: PLC0415
    from sverdrup.core.observations import DiagonalErrorModel  # noqa: PLC0415
    from sverdrup.validation.params import (  # noqa: PLC0415
        OBS_NOISE_VARIANCE,
        baseline_config,
    )
    from sverdrup.validation.run import halo_obs  # noqa: PLC0415

    grid = baseline_config()[1]
    globe = BBox(0.0, 360.0, -90.0, 90.0)
    if source_id == "dc2021a":
        src: Any = Dc2021aSource()
        obs = src.load(
            globe,
            np.datetime64("2016-11-01"),
            np.datetime64("2018-03-01"),
            missions=_MAPPING_FIVE,
        )
    elif source_id == "cmems_my":
        src = CmemsMySource()
        cmems_codes = tuple(CHALLENGE_TO_CMEMS[m] for m in _MAPPING_FIVE)
        raw = src.load(
            cmems_load_bbox(grid, halo_deg=1.0),
            np.datetime64("2016-11-01"),
            np.datetime64("2018-03-01"),
            missions=cmems_codes,
        )
        inv = {v: k for k, v in CHALLENGE_TO_CMEMS.items()}
        mission = raw.mission
        if mission is None:  # pragma: no cover - adapter always tags
            raise RuntimeError("cmems_my returned untagged obs")
        relabeled = np.array([inv[str(m)] for m in mission])
        c = raw.coords()
        obs = ObsWindow.from_arrays(
            c[:, 0],
            c[:, 1],
            c[:, 2] - _DAYS_1993_TO_2017,
            raw.values(),
            DiagonalErrorModel(np.full(len(raw), OBS_NOISE_VARIANCE)),
            mission=relabeled,
        )
    else:
        raise typer.BadParameter(f"unknown source {source_id!r}")
    # the signed convention's time-coarsen on the CMEMS side, identity on
    # dc2021a (fork-a pin 4); daily-file chunking difference = part of
    # the recorded repackaging delta
    cfg = superobs_cfg_for(source_id)
    obs = apply_superobs(obs, cfg=cfg)
    framed = halo_obs(obs, grid, halo_deg=1.0)
    m_arr = framed.mission
    if m_arr is None:  # pragma: no cover - both adapters tag
        raise RuntimeError("untagged obs after framing")
    counts = {m: int((m_arr == m).sum()) for m in _MAPPING_FIVE}
    return framed, {"manifest_sha": src.descriptor().manifest_sha()}, counts


def _solve_and_score(framed: ObsWindow, tag: str) -> tuple[np.ndarray, float, Path]:
    """Frozen-config full-2017 mean maps (PROBE) + the j3 mu score."""
    from sverdrup.core.parameters import ConstantProvider  # noqa: PLC0415
    from sverdrup.core.seeding import derive_seed  # noqa: PLC0415
    from sverdrup.distributions.miost_ensemble import (  # noqa: PLC0415
        mean_fields,
        merged_members,
    )
    from sverdrup.methods.miost import (  # noqa: PLC0415
        PHASE13_WINNER_PARAMS,
        shipped_miost5,
    )
    from sverdrup.methods.miost_windows import WindowPlan  # noqa: PLC0415
    from sverdrup.validation import their_eval  # noqa: PLC0415
    from sverdrup.validation.input_adapter import load_mdt_grid  # noqa: PLC0415
    from sverdrup.validation.output_adapter import write_map  # noqa: PLC0415
    from sverdrup.validation.params import baseline_config  # noqa: PLC0415

    provider = ConstantProvider(dict(PHASE13_WINNER_PARAMS))
    grid = baseline_config()[1]
    method = shipped_miost5()
    root = derive_seed("miost", "phase14-golden-tile", tag, 0)
    spec, etas_a, _anoms, starts = merged_members(
        method, framed, grid, provider, 1, root
    )
    plan = WindowPlan()
    days = [float(d) for d in range(365)]
    means = mean_fields(spec, starts, etas_a, grid, plan, days)
    mdt_paths = sorted(Path("data/2021a_ssh_mapping_ose/dc_obs").glob("*.nc"))
    mdt = load_mdt_grid(
        [p for p in mdt_paths if "_c2_" not in p.name and "_j3_" not in p.name],
        grid,
    )
    stack = means.reshape(len(days), *grid.shape) + mdt[None]
    times = np.datetime64("2017-01-01") + np.asarray(days).astype("timedelta64[D]")
    PROBE_DIR.mkdir(parents=True, exist_ok=True)
    out_nc = PROBE_DIR / f"golden_tile_{tag}_mean_maps.nc"
    write_map(
        times,
        grid.y,
        grid.x,
        stack,
        out_nc,
        assimilated_missions=_MAPPING_FIVE,
    )
    # PROBE marker INSIDE the artifact — a copied file loses its directory
    # context (review S2.4); the npz twin already carries one.
    import netCDF4  # noqa: PLC0415

    with netCDF4.Dataset(out_nc, "a") as ds:
        ds.label = "PROBE"
    mu, _sigma, _lx = their_eval.score(out_nc, _J3_TRACK)
    return means, float(mu), out_nc


@app.command()
def run(
    source_a: Annotated[str, typer.Option()] = "dc2021a",
    source_b: Annotated[str, typer.Option()] = "cmems_my",
    frame: Annotated[str, typer.Option()] = "signed-box",
    period: Annotated[str, typer.Option()] = "2017",
) -> None:
    """The pre-registered comparison: anchor box x 2017 x frozen signed."""
    if source_a == source_b:
        raise typer.BadParameter("source ids must differ (a == b is a no-op)")
    if frame != "signed-box" or period != "2017":
        raise typer.BadParameter(
            "the pre-registered golden tile is signed-box x 2017 (owner pin 3)"
        )
    obs_a, desc_a, counts_a = _load_side(source_a)
    obs_b, desc_b, counts_b = _load_side(source_b)
    typer.echo(f"obs counts A {counts_a}")
    typer.echo(f"obs counts B {counts_b}")
    maps_a, mu_a, _ = _solve_and_score(obs_a, source_a)
    typer.echo(f"{source_a}: mu {mu_a:.10f}")
    maps_b, mu_b, _ = _solve_and_score(obs_b, source_b)
    typer.echo(f"{source_b}: mu {mu_b:.10f}")
    map_deltas = compute_deltas(maps_a, maps_b)
    mu_delta = mu_a - mu_b
    record = {
        "label": "PROBE",
        "frame": frame,
        "period": period,
        "config": "frozen-signed (shipped_miost5 + PHASE13_WINNER_PARAMS)",
        "descriptor_a": desc_a,
        "descriptor_b": desc_b,
        "obs_counts_a": counts_a,
        "obs_counts_b": counts_b,
        "superobs_cfg_a": superobs_cfg_for(source_a),
        "superobs_cfg_b": superobs_cfg_for(source_b),
        "obs_count_deltas": {m: counts_a[m] - counts_b[m] for m in counts_a},
        "mu_a": mu_a,
        "mu_b": mu_b,
        "mu_delta": mu_delta,
        "map_deltas": map_deltas,
        "thresholds": {
            "mu": TABLED_MU_DELTA,
            "map_rms_m": TABLED_MAP_RMS_M,
        },
        "tabled_for_owner": tabled_flag(map_deltas, mu_delta),
        "note": (
            "CROSS-DT BRIDGE (DT-vintage ruling item 1): repackaging and "
            "DT-generation deltas inseparable; AVISO DT2021 decomposition "
            "= owner-electable ledger row"
        ),
        "date": datetime.now(UTC).date().isoformat(),
    }
    if EVIDENCE.exists():
        from sverdrup.application.calibration.harness import (  # noqa: PLC0415
            atomic_write_json,
        )

        results = json.loads(EVIDENCE.read_text())
        node = results.setdefault("phase14", {}).setdefault("stage0", {})
        node.setdefault("golden_tile", {})[f"{source_a}_vs_{source_b}"] = record
        atomic_write_json(EVIDENCE, results)
    typer.echo(
        json.dumps(
            {k: record[k] for k in ("mu_delta", "map_deltas", "tabled_for_owner")},
            indent=1,
        )
    )


if __name__ == "__main__":
    app()
