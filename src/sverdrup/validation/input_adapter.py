"""Challenge L3 along-track NetCDF -> our ObsWindow (Cryosat-2 held out).

Reference frame (audit trail Task 3): the BASELINE OI maps ``sla_unfiltered``,
so the mapping ``ObsWindow`` carries that variable raw (no MDT). The withheld
Cryosat-2 eval track is reconstructed in SSH space (``sla_unfiltered + mdt -
lwe``) to match the challenge eval, and is returned as a separate ``EvalTrack``
that the OI path cannot ingest. Obs are time-coarsened (mean every
``COARSEN_TIME``) as in ``baseline_oi``; spin-up (pre-2017) obs are kept for the
mapping input, while the eval track is restricted to 2017.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import xarray as xr
from scipy.interpolate import griddata  # type: ignore[import-untyped]

from sverdrup.core.grid import GridSpec
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
from sverdrup.core.parameters import ParameterProvider
from sverdrup.validation.params import COARSEN_TIME, OBS_NOISE_VARIANCE

# Cap for gridding the (static) MDT — it is smooth, so a subsample suffices and
# keeps the Delaunay triangulation fast. Deterministic via a fixed seed.
_MDT_SUBSAMPLE = 150_000

# day 0 == 2017-01-01; spin-up obs carry negative day numbers.
EPOCH = np.datetime64("2017-01-01")

# The five mapping missions (Jason-2 ships as geodetic ``j2g`` + interleaved
# ``j2n``). Cryosat-2 (``c2``) is deliberately absent — it is the withheld
# evaluation mission and must never enter the mapping set.
MAPPING_MISSIONS = frozenset({"alg", "j2g", "j2n", "j3", "s3a", "h2g"})


@dataclass(frozen=True)
class EvalTrack:
    """The withheld Cryosat-2 track in SSH space — eval only, never OI-feedable."""

    lon: np.ndarray
    lat: np.ndarray
    time_days: np.ndarray
    ssh: np.ndarray


def _days_since_epoch(times: np.ndarray) -> np.ndarray:
    """Convert datetime64 times to float days since 2017-01-01."""
    return (times - EPOCH) / np.timedelta64(1, "D")


def _mission_code(path: Path) -> str:
    """Map an L3 filename to its mapping-mission code.

    Args:
        path: The L3 NetCDF path (challenge ``dt_gulfstream_<code>_phy_l3_*``).

    Returns:
        The mapping-mission code.

    Raises:
        ValueError: If the file is not a recognised mapping mission (e.g. the
            withheld Cryosat-2 ``c2`` file, or any unknown mission) — this is
            the withheld-leak guard.
    """
    name = path.name.lower()
    for code in MAPPING_MISSIONS:
        if f"_{code}_" in name:
            return code
    raise ValueError(
        f"{path.name!r} is not a recognised mapping mission {sorted(MAPPING_MISSIONS)}; "
        "the withheld Cryosat-2 (c2) track must never enter the mapping set."
    )


def load_mapping_obs(paths: list[Path], params: ParameterProvider) -> ObsWindow:
    """Load the mapping missions into one ObsWindow (SLA, spin-up included).

    Args:
        paths: L3 NetCDF paths for the mapping missions (NO Cryosat-2).
        params: Parameter provider (kept for provenance/symmetry with the run).

    Returns:
        An ``ObsWindow`` of ``sla_unfiltered`` with per-obs noise in a
        ``DiagonalErrorModel``, time-coarsened and labelled by mission.
    """
    lons, lats, times, vals, miss = [], [], [], [], []
    for path in paths:
        code = _mission_code(path)  # raises on c2 / unknown (withheld-leak guard)
        ds = xr.open_dataset(path)
        ds = ds.coarsen(time=COARSEN_TIME, boundary="trim").mean()  # type: ignore[attr-defined]
        sla = np.asarray(ds["sla_unfiltered"], dtype=float)
        finite = np.isfinite(sla)
        lons.append(np.asarray(ds["longitude"], dtype=float)[finite])
        lats.append(np.asarray(ds["latitude"], dtype=float)[finite])
        times.append(_days_since_epoch(np.asarray(ds["time"]))[finite])
        vals.append(sla[finite])
        miss.append(np.full(int(finite.sum()), code))
    values = np.concatenate(vals)
    error = DiagonalErrorModel(np.full(values.size, OBS_NOISE_VARIANCE))
    return ObsWindow.from_arrays(
        np.concatenate(lons),
        np.concatenate(lats),
        np.concatenate(times),
        values,
        error,
        mission=np.concatenate(miss),
    )


def load_mdt_grid(paths: list[Path], grid: GridSpec) -> np.ndarray:
    """Grid the mapping tracks' own MDT onto ``grid`` (reference-frame fix).

    The challenge maps SLA and writes ``ssh = sla + mdt`` (audit trail Task 3).
    We build the gridded MDT from the **mapping** tracks' per-point ``mdt`` (the
    same CNES MDT product the withheld c2 track carries, so the two MDTs cancel
    in the eval to ~1 mm — verified). c2 is never read here.

    Args:
        paths: Mapping-mission L3 paths (NO Cryosat-2).
        grid: The output grid.

    Returns:
        A ``(ny, nx)`` gridded MDT aligned with ``grid``.
    """
    lons, lats, mdts = [], [], []
    for path in paths:
        _mission_code(path)  # withheld-leak guard (rejects c2/unknown)
        ds = xr.open_dataset(path)
        lons.append(np.asarray(ds["longitude"], dtype=float))
        lats.append(np.asarray(ds["latitude"], dtype=float))
        mdts.append(np.asarray(ds["mdt"], dtype=float))
    lon = np.concatenate(lons)
    lat = np.concatenate(lats)
    mdt = np.concatenate(mdts)
    ok = np.isfinite(mdt)
    lon, lat, mdt = lon[ok], lat[ok], mdt[ok]
    if lon.size > _MDT_SUBSAMPLE:
        sel = np.random.default_rng(0).choice(lon.size, _MDT_SUBSAMPLE, replace=False)
        lon, lat, mdt = lon[sel], lat[sel], mdt[sel]

    glon, glat = np.unique(grid._lonlat_nodes()[0]), np.unique(grid._lonlat_nodes()[1])
    gx, gy = np.meshgrid(glon, glat)
    out = griddata((lon, lat), mdt, (gx, gy), method="linear")
    holes = ~np.isfinite(out)
    if holes.any():  # fill outside the convex hull with nearest-neighbour
        out[holes] = griddata((lon, lat), mdt, (gx[holes], gy[holes]), method="nearest")
    return np.asarray(out, dtype=float)


def load_eval_track(path: Path) -> EvalTrack:
    """Load the withheld Cryosat-2 track in SSH space for evaluation only (2017).

    Args:
        path: The Cryosat-2 L3 NetCDF path.

    Returns:
        An ``EvalTrack`` with ``ssh = sla_unfiltered + mdt - lwe`` (the challenge
        eval reference), restricted to 2017 (day >= 0). It is intentionally NOT
        an ``ObsWindow`` so it cannot be fed to the OI mapping path.
    """
    ds = xr.open_dataset(path)
    ssh = (
        np.asarray(ds["sla_unfiltered"], dtype=float)
        + np.asarray(ds["mdt"], dtype=float)
        - np.asarray(ds["lwe"], dtype=float)
    )
    t = _days_since_epoch(np.asarray(ds["time"]))
    keep = (t >= 0.0) & np.isfinite(ssh)  # eval is 2017 only; no spin-up
    return EvalTrack(
        np.asarray(ds["longitude"], dtype=float)[keep],
        np.asarray(ds["latitude"], dtype=float)[keep],
        t[keep],
        ssh[keep],
    )
