"""Provenance-enforced train/score separation (Task 21 hardening).

Maps written by this repo carry the assimilated-mission list as a NetCDF
global attribute; every track-scoring path calls
:func:`assert_scored_not_assimilated` before scoring. Ordered after the
Task-13 winner-point leak (a map that assimilated j3 was scored on j3):
with the guard in place that class of leak raises instead of scoring.
"""

from __future__ import annotations

import re
from pathlib import Path

import xarray as xr

ASSIMILATED_ATTR = "assimilated_missions"
# The mission is the token immediately before ``_phy_l3`` in the L3 naming
# scheme. Written this way rather than against ``dt_gulfstream_`` so the
# phase-14 per-tile validation tracks (``dt_<tile>_<mission>_phy_l3_...``,
# tiles far outside the challenge box) resolve their mission too — the
# alternative was naming a Pacific track "gulfstream" to satisfy the parser,
# i.e. claiming provenance it does not have. A name that does not follow the
# scheme still yields None, and the guard still fails LOUD on it.
_TRACK_MISSION_RE = re.compile(r"_([a-z0-9]+)_phy_l3")


class TrainScoreLeakError(RuntimeError):
    """A track-scoring path could not prove train/score separation."""


def mission_from_track_path(track_path: Path) -> str | None:
    """Extract the mission id from a challenge along-track filename.

    Args:
        track_path: The along-track L3 file (L3 naming scheme — the
            challenge's ``dt_gulfstream_<mission>_phy_l3_...`` or a
            per-tile ``dt_<tile>_<mission>_phy_l3_...``). The file need
            not exist.

    Returns:
        The mission id, or None if the name does not match the scheme.
    """
    m = _TRACK_MISSION_RE.search(Path(track_path).name)
    return m.group(1) if m else None


def read_assimilated(map_path: Path) -> tuple[str, ...] | None:
    """Read the assimilated-mission provenance from a map file.

    Args:
        map_path: A gridded map NetCDF.

    Returns:
        The sorted mission tuple, or None when the file carries no
        provenance (external/legacy maps).
    """
    with xr.open_dataset(map_path) as ds:
        raw = ds.attrs.get(ASSIMILATED_ATTR)
    if raw is None:
        return None
    return tuple(str(raw).split())


def assert_scored_not_assimilated(map_path: Path, track_path: Path) -> None:
    """Assert the scored mission was not assimilated into the map.

    Enforcement is provenance-conditional: maps WITHOUT the attribute
    (external/legacy products we cannot re-tag) pass unchecked; maps WITH it
    must prove separation — an unidentifiable track is a loud failure, never
    a silent skip.

    Args:
        map_path: The gridded map about to be scored.
        track_path: The along-track file it is scored against.

    Raises:
        TrainScoreLeakError: If the scored mission is in the map's
            assimilated list, or the map carries provenance but the track's
            mission cannot be identified.
    """
    assimilated = read_assimilated(map_path)
    if assimilated is None:
        return
    mission = mission_from_track_path(track_path)
    if mission is None:
        raise TrainScoreLeakError(
            f"map {map_path} carries assimilated-mission provenance but the "
            f"scored track {Path(track_path).name!r} has no recognizable "
            "mission id — cannot prove train/score separation"
        )
    if mission in assimilated:
        raise TrainScoreLeakError(
            f"train/score leak: mission {mission!r} was assimilated into map "
            f"{map_path} (assimilated: {' '.join(assimilated)}) and must not "
            "be scored against it"
        )
