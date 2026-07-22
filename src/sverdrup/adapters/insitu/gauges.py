"""PSMSL/UHSLC gauge loaders + the LOCKED structural refusal (0a-3a).

Sources (pinned; content-manifested at download by ``scripts/download_gauges.py``,
per-file shas — "version" = the manifest, fork-a pin 3):

- **UHSLC research-quality (rqds) hourly** → daily means — the primary
  series. Documented layout (the interface contract): one NetCDF per
  station, ``time`` coordinate (hourly), ``sea_level`` variable in
  MILLIMETERS (NaN/fill for gaps), scalar ``lat``/``lon`` variables.
- **PSMSL RLR catalog snapshot** (``rlr_monthly.zip``) for
  datum-continuity metadata; parsed from ``filelist.txt``
  (``id; lat; lon; name; coastline; station; flag``).

**Structural refusal (fork-f pin 1, the c2 ceremony pattern):**
``load_gauge`` for an id in the locked split raises ``LockedGaugeError``
BEFORE any file open unless ``SVERDRUP_INSITU_LOCKED`` is the exact string
``"1"``. The Task-10 ceremony function is the only code path that sets that
env for its child scope.
"""

from __future__ import annotations

import json
import os
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import xarray as xr

LOCKED_ENV = "SVERDRUP_INSITU_LOCKED"
GAUGES_DIR = Path("data/insitu")
LOCKED_SPLIT_PATH = GAUGES_DIR / "locked_split.json"

# A daily mean from fewer than this many valid hourly samples is dropped —
# a half-empty day is a biased mean, not a measurement.
MIN_HOURS_PER_DAY = 12


class LockedGaugeError(RuntimeError):
    """A locked-tier gauge was requested outside the touch ceremony."""


@dataclass(frozen=True)
class GaugeDaily:
    """One gauge's daily-mean series."""

    gauge_id: str
    lon: float
    lat: float
    days: np.ndarray  # datetime64[D]
    sea_level_m: np.ndarray


@dataclass(frozen=True)
class PsmslStation:
    """One PSMSL RLR catalog row (datum-continuity metadata)."""

    psmsl_id: int
    lat: float
    lon: float
    name: str
    coastline: int | None  # None: non-numeric code in the snapshot (e.g. XXX)
    station: int | None


def locked_ids(split_path: Path = LOCKED_SPLIT_PATH) -> frozenset[str]:
    """The locked gauge-id set from the split artifact (empty pre-seal).

    Args:
        split_path: The split JSON (``{"locked": [...], "dev": [...]}``).

    Returns:
        The locked ids; empty when no split artifact exists yet.
    """
    if not split_path.exists():
        return frozenset()
    return frozenset(json.loads(split_path.read_text())["locked"])


def parse_uhslc_hourly(path: Path, gauge_id: str) -> GaugeDaily:
    """Parse a UHSLC rqds hourly file into daily means (mm → m).

    Args:
        path: The station NetCDF (documented layout in the module docstring).
        gauge_id: The program gauge id to stamp on the series.

    Returns:
        Daily means over calendar days with ≥ ``MIN_HOURS_PER_DAY`` valid
        hourly samples; thinner days are dropped, never averaged thin.
    """
    with xr.open_dataset(path) as ds:
        time = np.asarray(ds["time"].values)
        level_mm = np.asarray(ds["sea_level"].values, dtype=float).ravel()
        lat = float(np.asarray(ds["lat"]).ravel()[0])
        lon = float(np.asarray(ds["lon"]).ravel()[0])
    day = time.astype("datetime64[D]")
    valid = np.isfinite(level_mm)
    days_out = []
    means_out = []
    for d in np.unique(day):
        sel = (day == d) & valid
        if int(sel.sum()) >= MIN_HOURS_PER_DAY:
            days_out.append(d)
            means_out.append(level_mm[sel].mean() / 1000.0)
    return GaugeDaily(
        gauge_id=gauge_id,
        lon=lon,
        lat=lat,
        days=np.asarray(days_out, dtype="datetime64[D]"),
        sea_level_m=np.asarray(means_out, dtype=float),
    )


def load_gauge(
    gauge_id: str,
    data_dir: Path = GAUGES_DIR,
    split_path: Path | None = None,
) -> GaugeDaily:
    """Load one gauge's daily series — locked ids refuse BEFORE any open.

    Args:
        gauge_id: The program gauge id (file ``<data_dir>/uhslc/<id>.nc``).
        data_dir: The gauge data root.
        split_path: The locked-split artifact. Defaults to the CANONICAL
            ``LOCKED_SPLIT_PATH`` regardless of ``data_dir`` — a custom
            data directory never bypasses the refusal.

    Returns:
        The daily-mean series.

    Raises:
        LockedGaugeError: If ``gauge_id`` is in the locked set and
            ``SVERDRUP_INSITU_LOCKED`` is not the exact string ``"1"`` —
            raised before any file is opened (structural, fork-f pin 1).
    """
    sp = LOCKED_SPLIT_PATH if split_path is None else split_path
    if gauge_id in locked_ids(sp) and os.environ.get(LOCKED_ENV) != "1":
        raise LockedGaugeError(
            f"gauge {gauge_id!r} is in the LOCKED evaluation tier; it loads "
            "only inside the touch ceremony (SVERDRUP_INSITU_LOCKED=1 — "
            "exact string, set by validation.locked_tier.open_touch only)"
        )
    return parse_uhslc_hourly(data_dir / "uhslc" / f"{gauge_id}.nc", gauge_id)


def load_psmsl_catalog(zip_path: Path) -> tuple[PsmslStation, ...]:
    """Parse the PSMSL RLR catalog snapshot's ``filelist.txt``.

    Args:
        zip_path: The ``rlr_monthly.zip`` snapshot.

    Returns:
        The catalog rows, file order preserved.
    """
    with zipfile.ZipFile(zip_path) as zf:
        member = next(n for n in zf.namelist() if n.endswith("filelist.txt"))
        text = zf.read(member).decode()

    def _int_or_none(s: str) -> int | None:
        return int(s) if s.strip().isdigit() else None

    rows = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split(";")]
        rows.append(
            PsmslStation(
                psmsl_id=int(parts[0]),
                lat=float(parts[1]),
                lon=float(parts[2]),
                name=parts[3].rstrip(";").strip(),
                coastline=_int_or_none(parts[4]),
                station=_int_or_none(parts[5]),
            )
        )
    return tuple(rows)
