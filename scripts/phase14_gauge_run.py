"""T8 real-data leg: parse every rqds station, screen, split, record (0a-3a).

Runs AFTER the real census re-run (epochs come from the real partition)
and the ``stations-all`` download. Mechanics (all recorded):

- Station series = the merged daily means of a station's rqds hourly
  segment files (``h{id:03d}{a,b,c,...}.nc`` share one ``uhslc_id``);
  gauge_id = ``uh{uhslc_id:03d}``.
- RLR datum continuity = a PSMSL RLR catalog row within
  ``RLR_MATCH_DEG`` of the station position (recorded mechanical rule).
- Corrections recorded per gauge: rqds raw hourly (no DAC applied),
  daily-mean-of-hourly tide suppression; B2023 Eq.-1 is the reference
  convention the Stage-1 consumer reconciles against.
- Proximity DEFERRED to consumption (no Stage-0 program grid — recorded
  interpretation, Gate-0 owner attention item).
- Split written to ``data/insitu/locked_split.json`` (the structural
  refusal's canonical path) + evidence at ``phase14.stage0.gauges``.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import typer

from sverdrup.adapters.insitu.gauges import (
    GAUGES_DIR,
    LOCKED_SPLIT_PATH,
    load_psmsl_catalog,
    parse_uhslc_hourly,
)
from sverdrup.adapters.insitu.screening import (
    RLR_MATCH_DEG,
    Epoch,
    GaugeRecord,
    screen_gauges,
    stratified_split,
    write_locked_split,
)
from sverdrup.core.seeding import derive_seed

app = typer.Typer(add_completion=False)

EVIDENCE = Path("data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json")


def _real_epochs() -> tuple[Epoch, ...]:
    """The REAL program epochs from the schema-v2 census snapshot."""
    from sverdrup.application.epochs import (  # noqa: PLC0415
        build_census,
        partition_epochs,
    )

    census_raw = json.loads(Path("data/cmems_my/census_raw.json").read_text())
    if census_raw.get("schema_version") != 2:
        raise RuntimeError("census snapshot is not schema v2 — re-run the census leg")
    part = partition_epochs(build_census(census_raw["missions"]))
    return tuple(Epoch(e.epoch_id, e.start, e.end) for e in part.epochs)


@app.command()
def run() -> None:
    """Parse -> screen -> split -> record."""
    epochs = _real_epochs()
    typer.echo(f"{len(epochs)} program epochs")
    catalog = load_psmsl_catalog(GAUGES_DIR / "psmsl" / "rlr_monthly.zip")
    cat_lon = np.array([c.lon % 360.0 for c in catalog])
    cat_lat = np.array([c.lat for c in catalog])

    # group segment files by uhslc_id via the station position in each file
    by_station: dict[str, list[Path]] = {}
    for p in sorted((GAUGES_DIR / "uhslc").glob("h*.nc")):
        stem = p.stem  # h057a -> station h057
        by_station.setdefault(stem[:-1] if stem[-1].isalpha() else stem, []).append(p)
    typer.echo(f"{len(by_station)} stations across segment files")

    gauges: list[GaugeRecord] = []
    for station, paths in sorted(by_station.items()):
        days_all: list[np.ndarray] = []
        vals_all: list[np.ndarray] = []
        lon = lat = 0.0
        for p in paths:
            g = parse_uhslc_hourly(p, gauge_id=station)
            days_all.append(g.days)
            vals_all.append(g.sea_level_m)
            lon, lat = g.lon, g.lat
        days = np.concatenate(days_all)
        order = np.argsort(days)
        days, _vals = days[order], np.concatenate(vals_all)[order]
        days, uniq_idx = np.unique(days, return_index=True)
        if days.size == 0:
            continue
        d_lon = np.abs(((cat_lon - lon % 360.0) + 180.0) % 360.0 - 180.0)
        rlr_ok = bool(
            ((d_lon <= RLR_MATCH_DEG) & (np.abs(cat_lat - lat) <= RLR_MATCH_DEG)).any()
        )
        gauges.append(
            GaugeRecord(
                gauge_id=f"uh{station[1:]}",
                lon=lon,
                lat=lat,
                days=days,
                rlr_datum_ok=rlr_ok,
                corrections={
                    "dac": "none-applied (rqds raw hourly)",
                    "tide": "daily-mean-of-hourly",
                },
            )
        )
    typer.echo(f"{len(gauges)} candidate gauges parsed")

    rows, passed = screen_gauges(gauges, epochs, None)
    survivors = [g for g in gauges if g.gauge_id in set(passed)]
    split = stratified_split(survivors)
    # WRITE-ONCE (T19 review finding 2): identical rebuild = no-op;
    # drifted content refuses — the seal pins these ids.
    write_locked_split(LOCKED_SPLIT_PATH, split)
    rows_path = GAUGES_DIR / "screening_rows.json"
    rows_path.write_text(
        json.dumps(
            [
                {
                    "gauge_id": r.gauge_id,
                    "criterion": r.criterion,
                    "passed": r.passed,
                    "detail": r.detail,
                }
                for r in rows
            ],
            indent=1,
        )
        + "\n"
    )
    record = {
        "status": "series-leg-complete",
        "n_candidates": len(gauges),
        "n_screened": len(passed),
        "n_locked": len(split["locked"]),
        "n_dev": len(split["dev"]),
        "split_seed": int(derive_seed("insitu", "phase14-seal", "locked-split", 0)),
        "proximity": "DEFERRED to consumption grid (Gate-0 attention item)",
        "screening_rows": str(rows_path),
        "date": datetime.now(UTC).date().isoformat(),
    }
    if EVIDENCE.exists():
        from sverdrup.application.calibration.harness import (  # noqa: PLC0415
            atomic_write_json,
        )

        results = json.loads(EVIDENCE.read_text())
        node = results.setdefault("phase14", {}).setdefault("stage0", {})
        node.setdefault("gauges", {}).update(record)
        atomic_write_json(EVIDENCE, results)
    typer.echo(json.dumps(record, indent=1))


if __name__ == "__main__":
    app()
