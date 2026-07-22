"""Synthetic along-track CI adapter (phase-14 0c-3).

Two fake missions with analytic deterministic ground tracks:

- ``synA``: 10-day exact-repeat orbit — coords on day ``d`` equal coords on
  day ``d + 10`` (times and values differ; the geometry repeats).
- ``synB``: drifting orbit — the daily longitude offset never repeats on
  the program horizon.

Values are an analytic SSH field (sum of two slowly-advected Gaussians), so
downstream machinery sees structured, reproducible data with no external
files. Per-mission phase constants are drawn once from
``derive_seed("altimetry", "synthetic-v1", mission, 0)`` — deterministic
across instantiations and hosts.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence

import numpy as np

from sverdrup.adapters.altimetry.contract import BBox, SourceDescriptor
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
from sverdrup.core.seeding import derive_seed

_EPOCH = np.datetime64("2017-01-01")
_N_PER_DAY = 500
_OBS_NOISE_VARIANCE = 1e-3
_MISSIONS = ("synA", "synB")
# Ground-track shape: passes per day and latitude turning point.
_PASSES_PER_DAY = 7
_LAT_MAX = 66.0
# synA repeats its daily offset every 10 days; synB drifts 0.7 deg/day.
_REPEAT_DAYS = 10
_DRIFT_DEG_PER_DAY = 0.7


def _phases() -> dict[str, tuple[float, float]]:
    """Per-mission (lon, lat) phase constants from the seeded generator."""
    out: dict[str, tuple[float, float]] = {}
    for mission in _MISSIONS:
        rng = np.random.default_rng(
            derive_seed("altimetry", "synthetic-v1", mission, 0)
        )
        out[mission] = (float(rng.uniform(0.0, 360.0)), float(rng.uniform(0.0, 1.0)))
    return out


def _ssh(lon: np.ndarray, lat: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Analytic SSH: two Gaussians advected slowly eastward/westward."""

    def gauss(amp: float, lon_c: np.ndarray, lat_c: float, sig: float) -> np.ndarray:
        dlon = ((lon - lon_c + 180.0) % 360.0) - 180.0
        dlat = lat - lat_c
        return np.asarray(amp * np.exp(-(dlon**2 + dlat**2) / (2.0 * sig**2)))

    g1 = gauss(0.5, 300.0 + 0.05 * t, 40.0, 5.0)
    g2 = gauss(-0.3, 310.0 - 0.03 * t, 35.0, 8.0)
    return np.asarray(g1 + g2, dtype=np.float64)


class SyntheticSource:
    """Two fake missions with analytic deterministic ground tracks."""

    def __init__(self) -> None:
        """Draw the per-mission phase constants (seeded, deterministic)."""
        self._phase = _phases()

    def missions(self) -> tuple[str, ...]:
        """Mission codes this source serves."""
        return _MISSIONS

    def time_epoch(self) -> np.datetime64:
        """Epoch the ObsWindow times count days from."""
        return _EPOCH

    def descriptor(self) -> SourceDescriptor:
        """Content-addressed identity of the generator.

        No files exist: the single manifest entry is the sha of the
        generator's parameter string, so any generator change moves the sha.
        """
        params = "|".join(
            [
                f"epoch={_EPOCH}",
                f"n_per_day={_N_PER_DAY}",
                f"passes_per_day={_PASSES_PER_DAY}",
                f"lat_max={_LAT_MAX}",
                f"repeat_days={_REPEAT_DAYS}",
                f"drift_deg_per_day={_DRIFT_DEG_PER_DAY}",
                f"noise_var={_OBS_NOISE_VARIANCE}",
                f"phases={sorted(self._phase.items())}",
            ]
        )
        sha = hashlib.sha256(params.encode()).hexdigest()
        return SourceDescriptor(
            source_id="synthetic",
            dataset_version="synthetic-v1",
            content_manifest=(("generator/params", sha),),
        )

    def _day_track(
        self, mission: str, day: int
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Analytic (lon, lat, t_days) for one mission-day, 500 obs."""
        lon_phase, lat_phase = self._phase[mission]
        s = np.arange(_N_PER_DAY, dtype=np.float64) / _N_PER_DAY
        if mission == "synA":
            day_offset = (day % _REPEAT_DAYS) * (360.0 / _REPEAT_DAYS)
        else:
            day_offset = day * _DRIFT_DEG_PER_DAY
        lat = _LAT_MAX * np.sin(2.0 * np.pi * (_PASSES_PER_DAY * s + lat_phase))
        lon = (360.0 * _PASSES_PER_DAY * s / 2.0 + day_offset + lon_phase) % 360.0
        t = day + s
        return lon, lat, t

    def load(
        self,
        bbox: BBox,
        t0: np.datetime64,
        t1: np.datetime64,
        missions: Sequence[str] | None = None,
    ) -> ObsWindow:
        """Load synthetic obs — a pure restriction of the analytic stream.

        Args:
            bbox: Inclusive spatial box.
            t0: Absolute start (inclusive).
            t1: Absolute end (exclusive).
            missions: Optional mission subset; unknown codes raise.

        Returns:
            Mission-tagged ObsWindow, times in days since 2017-01-01.

        Raises:
            ValueError: On an unknown mission code.
        """
        wanted = _MISSIONS if missions is None else tuple(str(m) for m in missions)
        unknown = [m for m in wanted if m not in _MISSIONS]
        if unknown:
            raise ValueError(
                f"unknown mission code(s) {unknown}; this source serves {_MISSIONS}"
            )
        t0_days = float((t0 - _EPOCH) / np.timedelta64(1, "D"))
        t1_days = float((t1 - _EPOCH) / np.timedelta64(1, "D"))
        d_first = int(np.floor(t0_days))
        d_last = int(np.ceil(t1_days))
        lons, lats, times, miss = [], [], [], []
        for day in range(d_first, d_last):
            for mission in _MISSIONS:  # canonical order, then filter
                if mission not in wanted:
                    continue
                lon, lat, t = self._day_track(mission, day)
                keep = (t >= t0_days) & (t < t1_days) & bbox.contains(lon, lat)
                lons.append(lon[keep])
                lats.append(lat[keep])
                times.append(t[keep])
                miss.append(np.full(int(keep.sum()), mission))
        lon_all = np.concatenate(lons) if lons else np.empty(0)
        lat_all = np.concatenate(lats) if lats else np.empty(0)
        t_all = np.concatenate(times) if times else np.empty(0)
        m_all = np.concatenate(miss) if miss else np.empty(0, dtype="U4")
        values = _ssh(lon_all, lat_all, t_all)
        return ObsWindow.from_arrays(
            lon_all,
            lat_all,
            t_all,
            values,
            DiagonalErrorModel(np.full(values.size, _OBS_NOISE_VARIANCE)),
            mission=m_all,
        )
