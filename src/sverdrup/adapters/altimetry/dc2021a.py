"""dc2021a challenge-source adapter (phase-14 0c-6).

Wraps the existing 2021a OSE Gulf Stream challenge input path as a REAL
``AlongTrackSource`` (owner pin 2, plan review 2026-07-22): the per-mission
reading logic is ``validation.input_adapter.load_mapping_obs`` — imported,
not copied — so the SPEC §10 gate-2 loader identity is byte-comparable
against the legacy path by construction. Uniform content-manifested
descriptor; never a test-only bypass.

The withheld Cryosat-2 (``c2``) mission is structurally absent: not in
``missions()``, not in the manifest, and any attempt to load it raises —
the existing exclusion (``_mission_code`` withheld-leak guard) preserved at
the contract layer.

Version migration = a NEW ``source_id``, never a mutation (fork-a pin 5).
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path

import numpy as np

from sverdrup.adapters.altimetry.contract import BBox, SourceDescriptor
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
from sverdrup.core.parameters import ConstantProvider
from sverdrup.validation.input_adapter import load_mapping_obs
from sverdrup.validation.params import EPOCH, OBS_NOISE_VARIANCE

DC_OBS_DIR = Path("data/2021a_ssh_mapping_ose/dc_obs")

# The six challenge missions the source serves: the five signed mapping
# missions + the j3 validation track. c2 is DELIBERATELY absent.
_MISSIONS = ("alg", "h2g", "j2g", "j2n", "j3", "s3a")


@lru_cache(maxsize=8)
def _file_sha(path_str: str, size: int, mtime_ns: int, inode: int) -> str:
    """sha256 of a file's bytes (cache keyed on path+size+mtime+inode)."""
    h = hashlib.sha256()
    with open(path_str, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Dc2021aSource:
    """The existing challenge input path wrapped as an AlongTrackSource."""

    def __init__(self, obs_dir: Path = DC_OBS_DIR) -> None:
        """Bind to a challenge obs directory (default: the standing layout).

        Args:
            obs_dir: Directory holding the ``dt_gulfstream_<code>_phy_l3_*.nc``
                challenge files.
        """
        self._dir = obs_dir

    def missions(self) -> tuple[str, ...]:
        """Mission codes this source serves (c2 deliberately absent)."""
        return _MISSIONS

    def time_epoch(self) -> np.datetime64:
        """Epoch the ObsWindow times count days from (the legacy EPOCH)."""
        return np.datetime64(EPOCH)

    def _path(self, mission: str) -> Path:
        """The single challenge file for ``mission``.

        Raises:
            FileNotFoundError: If zero or multiple files match.
        """
        hits = sorted(self._dir.glob(f"dt_gulfstream_{mission}_phy_l3_*.nc"))
        if len(hits) != 1:
            raise FileNotFoundError(
                f"expected exactly one {mission!r} challenge file under "
                f"{self._dir}, found {len(hits)}"
            )
        return hits[0]

    def descriptor(self) -> SourceDescriptor:
        """Content-addressed identity: per-file sha256 of the six files."""
        manifest = []
        for mission in _MISSIONS:
            p = self._path(mission)
            st = p.stat()
            manifest.append(
                (p.name, _file_sha(str(p), st.st_size, st.st_mtime_ns, st.st_ino))
            )
        return SourceDescriptor(
            source_id="dc2021a",
            dataset_version="2021a_ssh_mapping_ose-l3",
            content_manifest=tuple(manifest),
        )

    def load(
        self,
        bbox: BBox,
        t0: np.datetime64,
        t1: np.datetime64,
        missions: Sequence[str] | None = None,
    ) -> ObsWindow:
        """Load challenge obs — a pure restriction of the legacy reading path.

        Args:
            bbox: Inclusive spatial box.
            t0: Absolute start (inclusive).
            t1: Absolute end (exclusive).
            missions: Optional mission subset; c2 or unknown codes raise.

        Returns:
            Mission-tagged ObsWindow, times in days since 2017-01-01, arrays
            byte-identical to the legacy ``load_mapping_obs`` path on the
            same restriction (gate 2).

        Raises:
            ValueError: On an unknown mission code — including ``c2``, whose
                exclusion from the mapping set is structural.
        """
        wanted = _MISSIONS if missions is None else tuple(str(m) for m in missions)
        unknown = [m for m in wanted if m not in _MISSIONS]
        if unknown:
            raise ValueError(
                f"unknown mission code(s) {unknown}; this source serves "
                f"{_MISSIONS} (c2 is the withheld mission and never loads "
                "through the mapping call)"
            )
        epoch = self.time_epoch()
        t0_days = float((t0 - epoch) / np.timedelta64(1, "D"))
        t1_days = float((t1 - epoch) / np.timedelta64(1, "D"))
        provider = ConstantProvider({})
        lons, lats, times, vals, miss = [], [], [], [], []
        for mission in _MISSIONS:  # canonical order, then filter
            if mission not in wanted:
                continue
            w = load_mapping_obs([self._path(mission)], provider)
            c = w.coords()
            keep = (
                (c[:, 2] >= t0_days)
                & (c[:, 2] < t1_days)
                & bbox.contains(c[:, 0], c[:, 1])
            )
            mission_arr = w.mission
            if mission_arr is None:  # pragma: no cover - load_mapping_obs tags
                raise RuntimeError("legacy loader returned untagged obs")
            lons.append(c[keep, 0])
            lats.append(c[keep, 1])
            times.append(c[keep, 2])
            vals.append(w.values()[keep])
            miss.append(mission_arr[keep])
        values = np.concatenate(vals) if vals else np.empty(0)
        return ObsWindow.from_arrays(
            np.concatenate(lons) if lons else np.empty(0),
            np.concatenate(lats) if lats else np.empty(0),
            np.concatenate(times) if times else np.empty(0),
            values,
            DiagonalErrorModel(np.full(values.size, OBS_NOISE_VARIANCE)),
            mission=(np.concatenate(miss) if miss else np.empty(0, dtype="U3")),
        )
