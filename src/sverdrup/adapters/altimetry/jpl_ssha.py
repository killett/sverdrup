"""JPL SSHA adapter — public code, artifact-gated data (phase-14 0c-4).

**Documented directory layout (the interface contract):** a local root
directory with one subdirectory per mission code; each subdirectory holds
along-track NetCDF files (any names ending ``.nc``) with:

- ``time`` — coordinate, datetime64;
- ``latitude`` / ``longitude`` — per-sample positions [degrees, lon any
  convention normalized mod 360];
- ``ssha`` — sea-surface-height anomaly [meters].

Per-file sha256 is computed AT INGEST for the content manifest (fork-a
pin 3 — no processing-tag branch exists). ObsWindow times count days since
``EPOCH`` (1992-10-01, the TOPEX-era anchor — declared, so cross-source
comparisons convert explicitly).

**Data governance (read in code review, enforced by test):** private JPL
data never leaves owner-controlled hosts absent explicit owner
authorization — this adapter is READ-ONLY LOCAL: it opens files under its
root and has no upload/copy/network capability.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import xarray as xr

from sverdrup.adapters.altimetry.contract import BBox, SourceDescriptor
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow

JPL_DIR_ENV = "SVERDRUP_JPL_SSHA_DIR"
EPOCH = np.datetime64("1992-10-01")

# Placeholder per-obs noise variance [m^2] until the source's own error
# metadata is wired (recorded; provenance carries the constant).
JPL_OBS_NOISE_VARIANCE = 1e-3


class JplSshaSource:
    """Along-track JPL SSHA source over a documented local directory tree."""

    def __init__(self, root: Path) -> None:
        """Bind to a local data root (READ-ONLY).

        Args:
            root: Directory with one subdirectory per mission code.
        """
        self._root = Path(root)

    def missions(self) -> tuple[str, ...]:
        """Mission codes = the subdirectory names, sorted."""
        return tuple(sorted(p.name for p in self._root.iterdir() if p.is_dir()))

    def time_epoch(self) -> np.datetime64:
        """Epoch the ObsWindow times count days from."""
        return EPOCH

    def _files(self, mission: str) -> list[Path]:
        return sorted((self._root / mission).glob("*.nc"))

    def descriptor(self) -> SourceDescriptor:
        """Content-addressed identity: per-file sha256 AT INGEST."""
        manifest = []
        for mission in self.missions():
            for p in self._files(mission):
                h = hashlib.sha256()
                with open(p, "rb") as f:
                    for chunk in iter(lambda: f.read(1 << 20), b""):
                        h.update(chunk)
                manifest.append((f"{mission}/{p.name}", h.hexdigest()))
        return SourceDescriptor(
            source_id="jpl_ssha",
            dataset_version="jpl-ssha-local-v1",
            content_manifest=tuple(manifest),
        )

    def load(
        self,
        bbox: BBox,
        t0: np.datetime64,
        t1: np.datetime64,
        missions: Sequence[str] | None = None,
    ) -> ObsWindow:
        """Load SSHA obs — a pure restriction of the on-disk stream.

        Args:
            bbox: Inclusive spatial box (lon compared mod 360).
            t0: Absolute start (inclusive).
            t1: Absolute end (exclusive).
            missions: Optional mission subset; unknown codes raise.

        Returns:
            Mission-tagged ObsWindow, times in days since ``EPOCH``.

        Raises:
            ValueError: On an unknown mission code.
        """
        known = self.missions()
        wanted = known if missions is None else tuple(str(m) for m in missions)
        unknown = [m for m in wanted if m not in known]
        if unknown:
            raise ValueError(
                f"unknown mission code(s) {unknown}; this root serves {known}"
            )
        t0_days = float((t0 - EPOCH) / np.timedelta64(1, "D"))
        t1_days = float((t1 - EPOCH) / np.timedelta64(1, "D"))
        lons, lats, times, vals, miss = [], [], [], [], []
        for mission in known:  # canonical order, then filter
            if mission not in wanted:
                continue
            for path in self._files(mission):
                with xr.open_dataset(path) as ds:
                    t = (np.asarray(ds["time"].values) - EPOCH) / np.timedelta64(1, "D")
                    lon = np.asarray(ds["longitude"].values, dtype=float) % 360.0
                    lat = np.asarray(ds["latitude"].values, dtype=float)
                    ssha = np.asarray(ds["ssha"].values, dtype=float)
                keep = (
                    (t >= t0_days)
                    & (t < t1_days)
                    & bbox.contains(lon, lat)
                    & np.isfinite(ssha)
                )
                lons.append(lon[keep])
                lats.append(lat[keep])
                times.append(np.asarray(t, dtype=float)[keep])
                vals.append(ssha[keep])
                miss.append(np.full(int(keep.sum()), mission))
        values = np.concatenate(vals) if vals else np.empty(0)
        return ObsWindow.from_arrays(
            np.concatenate(lons) if lons else np.empty(0),
            np.concatenate(lats) if lats else np.empty(0),
            np.concatenate(times) if times else np.empty(0),
            values,
            DiagonalErrorModel(np.full(values.size, JPL_OBS_NOISE_VARIANCE)),
            mission=(np.concatenate(miss) if miss else np.empty(0, dtype="U4")),
        )
