"""Scoped, reproducible CMEMS multi-year downloads (phase-14 Task 3, 0c-2).

The dc-download reproducer pattern: httpx + stamina retry on transient
faults only, sha256 manifest written beside the data, re-run =
verify-and-skip. NEVER an implicit full-globe pull: every leg is scoped by
missions × time (native files are DAILY-GLOBAL — spatial subsetting
happens at load; the ``bbox`` scope argument is recorded for the future
ARCO-subset path and does not widen any pull).

Storage WAIT semantics: a pull whose estimate would exceed the remaining
Stage-0 CMEMS budget (ladder row ``cmems_downloads``, 50 GiB, owner
pre-registered) REFUSES before any byte moves.

SINGLE-WRITER: manifest and ledger use read-modify-write — run legs
sequentially.

Usage:
    pixi run python scripts/download_cmems_my.py census
    pixi run python scripts/download_cmems_my.py subset \
        --missions alg,h2ag,j2g,j2n,s3a,j3 \
        --t0 2016-12-01 --t1 2018-02-01
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import httpx
import stamina
import typer

from sverdrup.adapters.altimetry.cmems_my import (
    CMEMS_DATA_DIR,
    DT_TAG,
    PRODUCT_ID,
    catalog_from_listing,
)
from sverdrup.adapters.odc.download import _is_retryable
from sverdrup.application.ladder import STAGE0_SPEND_TABLE

app = typer.Typer(add_completion=False)

MANIFEST = CMEMS_DATA_DIR / "manifest.json"
CENSUS_RAW = CMEMS_DATA_DIR / "census_raw.json"
EVIDENCE = Path("data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json")

STAC_ROOT = f"https://stac.marine.copernicus.eu/metadata/{PRODUCT_ID}"
_S3_HOST = "https://s3.waw3-1.cloudferro.com"
_AVG_FILE_GIB = 0.5 / 1024.0  # measured ~0.5 MB per daily-global file

_KEY_RE = re.compile(r"<Key>([^<]+)</Key>")
_TOKEN_RE = re.compile(r"<NextContinuationToken>([^<]+)</NextContinuationToken>")
_TRUNC_RE = re.compile(r"<IsTruncated>(\w+)</IsTruncated>")


def check_budget(est_gib: float, already_gib: float) -> None:
    """Refuse a pull whose estimate exceeds the remaining CMEMS budget.

    Args:
        est_gib: Estimated size of the pull.
        already_gib: GiB already ledgered against the CMEMS row.

    Raises:
        RuntimeError: WAIT — the owner must extend the budget first.
    """
    row = next(r for r in STAGE0_SPEND_TABLE if r.task_class == "cmems_downloads")
    if already_gib + est_gib > row.storage_gib:
        raise RuntimeError(
            f"storage WAIT: estimate {est_gib:.2f} GiB + ledgered "
            f"{already_gib:.2f} GiB exceeds the pre-registered CMEMS budget "
            f"{row.storage_gib} GiB — the task WAITS for the owner "
            "(executor-set spend never happens)"
        )


def _ledgered_cmems_gib() -> float:
    if not EVIDENCE.exists():
        return 0.0
    node = (
        json.loads(EVIDENCE.read_text())
        .get("phase14", {})
        .get("stage0", {})
        .get("storage_ledger", [])
    )
    return float(sum(r["gib"] for r in node if str(r["name"]).startswith("cmems")))


def _ledger_append(name: str, gib: float) -> None:
    if not EVIDENCE.exists():
        typer.echo(f"ledger skip: evidence store {EVIDENCE} absent")
        return
    from sverdrup.application.calibration.harness import (  # noqa: PLC0415
        atomic_write_json,
    )

    results = json.loads(EVIDENCE.read_text())
    node = results.setdefault("phase14", {}).setdefault("stage0", {})
    node.setdefault("storage_ledger", []).append(
        {
            "name": name,
            "gib": round(gib, 6),
            "date": datetime.now(UTC).date().isoformat(),
        }
    )
    atomic_write_json(EVIDENCE, results)


@stamina.retry(on=_is_retryable, attempts=4)
def _get_text(url: str) -> str:
    r = httpx.get(url, timeout=60.0, follow_redirects=True)
    r.raise_for_status()
    return r.text


@stamina.retry(on=_is_retryable, attempts=4)
def _get_json(url: str) -> dict[str, Any]:
    r = httpx.get(url, timeout=60.0, follow_redirects=True)
    r.raise_for_status()
    return dict(r.json())  # narrow at call sites


@stamina.retry(on=_is_retryable, attempts=4)
def _fetch_file(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with httpx.stream("GET", url, timeout=120.0, follow_redirects=True) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_bytes(1 << 20):
                f.write(chunk)
    tmp.replace(dest)


def _dataset_native_hrefs() -> dict[str, str]:
    """dataset_id -> native S3 href, from the public STAC catalog."""
    product = _get_json(f"{STAC_ROOT}/product.stac.json")
    out = {}
    for link in product.get("links", []):
        if link.get("rel") != "item":
            continue
        ds_rel = str(link["href"])
        ds_id = ds_rel.split("/")[0]
        ds = _get_json(f"{STAC_ROOT}/{ds_rel}")
        href = ds.get("assets", {}).get("native", {}).get("href")
        if href:
            out[ds_id] = str(href)
    return out


def _list_native_keys(href: str) -> list[str]:
    """Anonymous paged S3 listing of every object key under a native href."""
    bucket_host, _, prefix = href.removeprefix(f"{_S3_HOST}/").partition("/")
    keys: list[str] = []
    token: str | None = None
    while True:
        url = f"{_S3_HOST}/{bucket_host}?list-type=2&prefix={prefix}/&max-keys=1000"
        if token:
            from urllib.parse import quote  # noqa: PLC0415

            url += f"&continuation-token={quote(token)}"
        body = _get_text(url)
        keys.extend(_KEY_RE.findall(body))
        trunc = _TRUNC_RE.search(body)
        if not trunc or trunc.group(1) != "true":
            break
        tok = _TOKEN_RE.search(body)
        if not tok:
            break
        token = tok.group(1)
    return keys


@app.command()
def census() -> None:
    """The census leg: per-mission span + file counts, METADATA ONLY."""
    hrefs = _dataset_native_hrefs()
    typer.echo(f"{len(hrefs)} datasets in the STAC catalog")
    hrefs_by_id = dict(sorted(hrefs.items()))

    def list_keys(ds_id: str) -> list[str]:
        keys = _list_native_keys(hrefs_by_id[ds_id])
        typer.echo(f"  {ds_id}: {len(keys)} objects")
        return keys

    cat = catalog_from_listing(list(hrefs_by_id), list_keys)
    payload = {
        "schema_version": 2,  # v2: per-mission 'dates' lists (Task-4 input)
        "product_id": PRODUCT_ID,
        "dt_tag": DT_TAG,
        "generated": datetime.now(UTC).date().isoformat(),
        "missions": {k: cat[k] for k in sorted(cat)},
    }
    CENSUS_RAW.parent.mkdir(parents=True, exist_ok=True)
    canonical = json.dumps(payload, indent=1, sort_keys=True) + "\n"
    CENSUS_RAW.write_text(canonical)
    sha = hashlib.sha256(canonical.encode()).hexdigest()
    (CENSUS_RAW.with_suffix(".json.sha256")).write_text(sha + "\n")
    typer.echo(f"census: {len(cat)} missions -> {CENSUS_RAW} sha {sha[:12]}…")
    if EVIDENCE.exists():
        from sverdrup.application.calibration.harness import (  # noqa: PLC0415
            atomic_write_json,
        )

        results = json.loads(EVIDENCE.read_text())
        node = results.setdefault("phase14", {}).setdefault("stage0", {})
        node["cmems_census_raw_sha"] = sha
        atomic_write_json(EVIDENCE, results)


@app.command()
def subset(
    missions: Annotated[str, typer.Option(help="Comma-separated CMEMS codes")],
    t0: Annotated[str, typer.Option(help="ISO start date (inclusive)")],
    t1: Annotated[str, typer.Option(help="ISO end date (exclusive)")],
    bbox: Annotated[
        str,
        typer.Option(
            help=(
                "Recorded scope only: native files are daily-global; "
                "spatial subsetting happens at load"
            )
        ),
    ] = "global",
) -> None:
    """A scoped missions × time pull (budget-checked, verify-and-skip)."""
    wanted = [m.strip() for m in missions.split(",") if m.strip()]
    from sverdrup.adapters.altimetry.cmems_my import LOCKED_MISSIONS  # noqa: PLC0415

    locked = [m for m in wanted if m in LOCKED_MISSIONS]
    if locked:
        raise typer.BadParameter(
            f"mission(s) {locked} are in the LOCKED evaluation tier — "
            "locked data is acquired only through the touch-ceremony path"
        )
    hrefs = _dataset_native_hrefs()
    by_code = {}
    for ds_id, href in hrefs.items():
        code = ds_id.split("_my_")[1].split("-l3")[0]
        by_code[code] = (ds_id, href)
    unknown = [m for m in wanted if m not in by_code]
    if unknown:
        raise typer.BadParameter(f"unknown mission code(s) {unknown}")
    d0 = t0.replace("-", "")
    d1 = t1.replace("-", "")
    plan: list[tuple[str, str, str]] = []  # (mission, key, url)
    for m in wanted:
        ds_id, href = by_code[m]
        for key in _list_native_keys(href):
            match = re.search(r"_1hz_(\d{8})_", key)
            if match and d0 <= match.group(1) < d1:
                bucket_host = href.removeprefix(f"{_S3_HOST}/").split("/")[0]
                plan.append((m, key, f"{_S3_HOST}/{bucket_host}/{key}"))
    est_gib = len(plan) * _AVG_FILE_GIB
    already = _ledgered_cmems_gib()
    check_budget(est_gib, already)
    typer.echo(
        f"pull plan: {len(plan)} files ~{est_gib:.2f} GiB "
        f"(ledgered {already:.2f}); budget OK"
    )
    man = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    pulled = 0
    pulled_bytes = 0
    for mission, key, url in plan:
        name = key.rsplit("/", 1)[-1]
        dest = CMEMS_DATA_DIR / mission / name
        rel = f"{mission}/{name}"
        if dest.exists() and rel in man:
            continue
        _fetch_file(url, dest)
        h = hashlib.sha256(dest.read_bytes()).hexdigest()
        man[rel] = h
        pulled += 1
        pulled_bytes += dest.stat().st_size
        if pulled % 200 == 0:
            MANIFEST.write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
            typer.echo(f"  …{pulled}/{len(plan)}")
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
    if pulled:
        _ledger_append(
            f"cmems-subset-{'-'.join(wanted)}-{t0}-{t1}", pulled_bytes / 2**30
        )
    typer.echo(
        f"subset done: {pulled} new files ({pulled_bytes / 2**30:.3f} GiB), "
        f"{len(plan) - pulled} verified-skipped"
    )


if __name__ == "__main__":
    app()
