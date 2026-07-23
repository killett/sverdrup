"""CMEMS DUACS multi-year along-track source (phase-14 0c-2).

Product pinned: ``SEALEVEL_GLO_PHY_L3_MY_008_062``, per-mission along-track
SLA, native daily-global NetCDF. **Vintage ``_202411`` (DT2024 lineage),
RATIFIED by the owner DT-vintage ruling 2026-07-22** (spec postscript 2 —
fork-a pin-5 "DT2021" superseded-with-pointer: DT2021 was removed upstream
by the Nov-2024 reprocessing). Version migration = a NEW ``source_id``,
never a mutation (fork-a pin 5): any future DT change re-fires the
golden-tile machinery.

**Documented native layout (the interface contract):** a local root with
one subdirectory per mission code holding
``dt_global_<code>_phy_l3_1hz_<YYYYMMDD>_<prodtag>.nc`` daily files with
``time`` coordinate and per-sample ``latitude`` / ``longitude`` /
``sla_unfiltered`` [m] variables (the DUACS L3 schema the challenge files
share). Values load RAW (fork-a pin 4 — no transform at load).

**Locked tier:** the c2 family (``c2``, ``c2n``) is structurally absent
from the served mission set — CryoSat-2 is a LOCKED evaluation instrument
(gauges + c2 2010→); its data path goes through the Task-10 touch
ceremony, never the mapping load.

Challenge→CMEMS mission-code mapping (recorded interpretation, consumed by
the golden tile): identical codes except challenge ``h2g`` (HY-2A
geodetic) → CMEMS ``h2ag``.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Sequence
from pathlib import Path

import numpy as np
import xarray as xr

from sverdrup.adapters.altimetry.contract import BBox, SourceDescriptor
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
from sverdrup.validation.params import OBS_NOISE_VARIANCE

PRODUCT_ID = "SEALEVEL_GLO_PHY_L3_MY_008_062"
DT_TAG = "202411"
DATASET_VERSION = f"{PRODUCT_ID}_{DT_TAG}"

CMEMS_DATA_DIR = Path("data/cmems_my")
EPOCH = np.datetime64("1993-01-01")

# The locked evaluation family: never served through the mapping load.
LOCKED_MISSIONS = frozenset({"c2", "c2n"})

# Challenge box codes -> CMEMS dataset codes (golden-tile consumer).
CHALLENGE_TO_CMEMS = {
    "alg": "alg",
    "h2g": "h2ag",
    "j2g": "j2g",
    "j2n": "j2n",
    "s3a": "s3a",
    "j3": "j3",
}

_FILE_RE = re.compile(r"dt_global_(\w+)_phy_l3_1hz_(\d{8})_\d+\.nc$")


def catalog_from_listing(
    dataset_ids: Sequence[str], list_keys: Callable[[str], list[str]]
) -> dict[str, dict[str, object]]:
    """Per-mission (first_date, last_date, n_files) from key listings.

    Metadata only — no data download; the census leg's core arithmetic,
    injectable for tests.

    Args:
        dataset_ids: The product's dataset ids (one per mission).
        list_keys: Returns the object keys under one dataset prefix.

    Returns:
        ``{mission_code: {first_date, last_date, n_files, dataset_id}}``.
    """
    out: dict[str, dict[str, object]] = {}
    for ds_id in dataset_ids:
        keys = list_keys(ds_id)
        dates = []
        code = None
        for k in keys:
            m = _FILE_RE.search(k)
            if m:
                code = m.group(1)
                d = m.group(2)
                dates.append(f"{d[:4]}-{d[4:6]}-{d[6:]}")
        if code is None:
            continue
        out[code] = {
            "first_date": min(dates),
            "last_date": max(dates),
            "n_files": len(dates),
            "dataset_id": ds_id,
            # the full sorted day list — the Task-4 census artifact's
            # gap-splitting input (metadata only, ~11 B/day)
            "dates": sorted(dates),
        }
    return out


class CmemsMySource:
    """The public multi-year source over a locally downloaded scoped subset."""

    def __init__(self, data_dir: Path = CMEMS_DATA_DIR) -> None:
        """Bind to the downloaded subset root.

        Args:
            data_dir: Root with per-mission subdirectories + the download
                manifest (``manifest.json``, per-file shas at download).
        """
        self._dir = Path(data_dir)

    def missions(self) -> tuple[str, ...]:
        """Downloaded mission codes, sorted — locked c2 family excluded."""
        return tuple(
            sorted(
                p.name
                for p in self._dir.iterdir()
                if p.is_dir() and p.name not in LOCKED_MISSIONS
            )
        )

    def time_epoch(self) -> np.datetime64:
        """Epoch the ObsWindow times count days from (product start era)."""
        return EPOCH

    def descriptor(self) -> SourceDescriptor:
        """Content-addressed identity from the download-time manifest."""
        manifest_path = self._dir / "manifest.json"
        entries = (
            json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
        )
        return SourceDescriptor(
            source_id="cmems_my",
            dataset_version=DATASET_VERSION,
            content_manifest=tuple(sorted(entries.items())),
        )

    def _files(self, mission: str, t0_days: float, t1_days: float) -> list[Path]:
        """The mission's daily files whose file-date can intersect [t0, t1)."""
        hits = []
        for p in sorted((self._dir / mission).glob("*.nc")):
            m = _FILE_RE.search(p.name)
            if not m:
                continue
            d = m.group(2)
            day = float(
                (np.datetime64(f"{d[:4]}-{d[4:6]}-{d[6:]}") - EPOCH)
                / np.timedelta64(1, "D")
            )
            if day + 1.0 > t0_days and day < t1_days:
                hits.append(p)
        return hits

    def load(
        self,
        bbox: BBox,
        t0: np.datetime64,
        t1: np.datetime64,
        missions: Sequence[str] | None = None,
    ) -> ObsWindow:
        """Load SLA obs — a pure restriction of the downloaded stream.

        Non-finite ``sla_unfiltered`` samples are dropped (the documented
        finite filter); everything else is a pure restriction.

        Args:
            bbox: Inclusive spatial box (DUACS lon convention 0..360).
            t0: Absolute start (inclusive).
            t1: Absolute end (exclusive).
            missions: Optional subset; unknown or locked (c2-family) codes
                raise.

        Returns:
            Mission-tagged ObsWindow, times in days since 1993-01-01.

        Raises:
            ValueError: On an unknown or locked mission code.
        """
        known = self.missions()
        wanted = known if missions is None else tuple(str(m) for m in missions)
        bad = [m for m in wanted if m not in known]
        if bad:
            locked = [m for m in bad if m in LOCKED_MISSIONS]
            if locked:
                raise ValueError(
                    f"mission(s) {locked} are in the LOCKED evaluation tier "
                    "(CryoSat-2 family) and never load through the mapping "
                    "call — the Task-10 touch ceremony is the only path"
                )
            raise ValueError(
                f"unknown mission code(s) {bad}; downloaded subset serves {known}"
            )
        t0_days = float((t0 - EPOCH) / np.timedelta64(1, "D"))
        t1_days = float((t1 - EPOCH) / np.timedelta64(1, "D"))
        lons, lats, times, vals, miss = [], [], [], [], []
        for mission in known:  # canonical order, then filter
            if mission not in wanted:
                continue
            for path in self._files(mission, t0_days, t1_days):
                with xr.open_dataset(path) as ds:
                    t = (np.asarray(ds["time"].values) - EPOCH) / np.timedelta64(1, "D")
                    lon = np.asarray(ds["longitude"].values, dtype=float)
                    lat = np.asarray(ds["latitude"].values, dtype=float)
                    sla = np.asarray(ds["sla_unfiltered"].values, dtype=float)
                keep = (
                    (t >= t0_days)
                    & (t < t1_days)
                    & bbox.contains(lon, lat)
                    & np.isfinite(sla)
                )
                lons.append(lon[keep])
                lats.append(lat[keep])
                times.append(np.asarray(t, dtype=float)[keep])
                vals.append(sla[keep])
                miss.append(np.full(int(keep.sum()), mission))
        values = np.concatenate(vals) if vals else np.empty(0)
        return ObsWindow.from_arrays(
            np.concatenate(lons) if lons else np.empty(0),
            np.concatenate(lats) if lats else np.empty(0),
            np.concatenate(times) if times else np.empty(0),
            values,
            DiagonalErrorModel(np.full(values.size, OBS_NOISE_VARIANCE)),
            mission=(np.concatenate(miss) if miss else np.empty(0, dtype="U6")),
        )
