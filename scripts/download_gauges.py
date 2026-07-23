"""Scoped, reproducible gauge downloads (phase-14 Task 8, 0a-3a).

The dc-download reproducer pattern: httpx + stamina retry on transient
faults only, sha256 manifest written beside the data, re-run =
verify-and-skip. NEVER an implicit bulk pull — every leg is scoped
(catalogs, or one named station series).

Every completed download appends a row to the storage ledger at
``phase14.stage0.storage_ledger`` in the standing evidence JSON.

SINGLE-WRITER: manifest and ledger use read-modify-write — run download
legs sequentially (the standing evidence-store discipline), never in
parallel processes.

Usage:
    pixi run python scripts/download_gauges.py catalogs
    pixi run python scripts/download_gauges.py station --station-id h021
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import stamina
import typer

from sverdrup.adapters.odc.download import _is_retryable

app = typer.Typer(add_completion=False)

DATA_DIR = Path("data/insitu")
MANIFEST = DATA_DIR / "manifest.json"
EVIDENCE = Path("data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json")

PSMSL_RLR_URL = "https://psmsl.org/data/obtaining/rlr.monthly.data/rlr_monthly.zip"
UHSLC_META_URL = "https://uhslc.soest.hawaii.edu/data/meta.geojson"
UHSLC_HOURLY_URL = (
    "https://uhslc.soest.hawaii.edu/data/netcdf/rqds/global/hourly/{name}"
)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@stamina.retry(on=_is_retryable, attempts=4)
def _fetch(url: str, dest: Path) -> Path:
    """Stream ``url`` to ``dest`` (transient-fault retries only)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with httpx.stream("GET", url, timeout=120.0, follow_redirects=True) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_bytes(1 << 20):
                f.write(chunk)
    tmp.replace(dest)
    return dest


def _manifest() -> dict[str, Any]:
    return json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}


def _ledger_append(name: str, path: Path) -> None:
    """Append a storage-ledger row (GiB) to the standing evidence JSON."""
    if not EVIDENCE.exists():
        typer.echo(f"ledger skip: evidence store {EVIDENCE} absent")
        return
    from sverdrup.application.calibration.harness import (  # noqa: PLC0415
        atomic_write_json,
    )

    results = json.loads(EVIDENCE.read_text())
    node = results.setdefault("phase14", {}).setdefault("stage0", {})
    ledger = node.setdefault("storage_ledger", [])
    ledger.append(
        {
            "name": name,
            "gib": round(path.stat().st_size / 2**30, 6),
            "date": datetime.now(UTC).date().isoformat(),
        }
    )
    atomic_write_json(EVIDENCE, results)


def _get(url: str, dest: Path, name: str) -> None:
    """Verify-and-skip download with manifest + ledger recording."""
    man = _manifest()
    rel = str(dest.relative_to(DATA_DIR))
    if dest.exists() and rel in man and _sha256(dest) == man[rel]:
        typer.echo(f"verified, skip: {rel}")
        return
    _fetch(url, dest)
    man[rel] = _sha256(dest)
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
    _ledger_append(name, dest)
    typer.echo(f"downloaded {rel} sha {man[rel][:12]}…")


@app.command()
def catalogs() -> None:
    """The two catalog snapshots: PSMSL RLR zip + UHSLC station metadata."""
    _get(PSMSL_RLR_URL, DATA_DIR / "psmsl" / "rlr_monthly.zip", "psmsl-rlr-catalog")
    _get(UHSLC_META_URL, DATA_DIR / "uhslc" / "meta.geojson", "uhslc-meta")


@app.command("stations-all")
def stations_all() -> None:
    """The full rqds hourly roster (scoped BY the catalog's own file list).

    ~715 station-segment files, ~0.1 MB each — the era-completeness
    criterion needs every candidate's daily series; this is the recorded
    scoped leg (ledgered as one row).
    """
    import re  # noqa: PLC0415

    body = httpx.get(
        UHSLC_HOURLY_URL.format(name=""), timeout=60.0, follow_redirects=True
    ).text
    names = sorted(set(re.findall(r'href="(h\w+\.nc)"', body)))
    typer.echo(f"{len(names)} rqds hourly files in the catalog")
    man = _manifest()
    pulled = 0
    pulled_bytes = 0
    for name in names:
        dest = DATA_DIR / "uhslc" / name
        rel = f"uhslc/{name}"
        if dest.exists() and rel in man:
            continue
        _fetch(UHSLC_HOURLY_URL.format(name=name), dest)
        man[rel] = _sha256(dest)
        pulled += 1
        pulled_bytes += dest.stat().st_size
        if pulled % 100 == 0:
            MANIFEST.write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
            typer.echo(f"  …{pulled}")
    MANIFEST.write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
    if pulled and EVIDENCE.exists():
        from sverdrup.application.calibration.harness import (  # noqa: PLC0415
            atomic_write_json,
        )

        results = json.loads(EVIDENCE.read_text())
        node = results.setdefault("phase14", {}).setdefault("stage0", {})
        node.setdefault("storage_ledger", []).append(
            {
                "name": "uhslc-rqds-hourly-all",
                "gib": round(pulled_bytes / 2**30, 6),
                "date": datetime.now(UTC).date().isoformat(),
            }
        )
        atomic_write_json(EVIDENCE, results)
    typer.echo(
        f"stations-all done: {pulled} new ({pulled_bytes / 2**30:.3f} GiB), "
        f"{len(names) - pulled} verified-skipped"
    )


@app.command()
def station(
    station_id: str = typer.Option(..., help="UHSLC file stem, e.g. h021"),
) -> None:
    """ONE named station's rqds hourly series (scoped, never bulk)."""
    name = f"{station_id}.nc"
    _get(
        UHSLC_HOURLY_URL.format(name=name),
        DATA_DIR / "uhslc" / name,
        f"uhslc-hourly-{station_id}",
    )


if __name__ == "__main__":
    app()
