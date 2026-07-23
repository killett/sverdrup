"""Constellation census + deterministic epoch partition (phase-14 0a-1).

The whole program keys on this artifact: per-mission ACTIVE intervals from
loader metadata (day resolution, schema-versioned, content-addressed), the
epoch partition at constellation-change dates with the minimum-epoch merge
rule, the WINDOW-CENTER epoch assignment (fork-d D6), and reference-epoch
candidates counted NET of locked missions (fork-e pin 3).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

import numpy as np

# A day-sequence difference EXCEEDING this splits the ACTIVE interval
# (diff > 90 days, i.e. 90+ silent days); shorter outages stay inside.
MISSION_GAP_SPLIT_D = 90

# Epochs shorter than this merge into a neighbor (constellation-change
# chatter cannot support per-epoch calibration).
MIN_EPOCH_DAYS = 365


@dataclass(frozen=True)
class CensusArtifact:
    """Per-mission ACTIVE intervals, content-addressed."""

    schema_version: int
    intervals: dict[str, tuple[tuple[np.datetime64, np.datetime64], ...]]

    def content_sha(self) -> str:
        """sha256 over the canonical serialization (two builds byte-equal)."""
        payload = json.dumps(
            {
                "schema_version": self.schema_version,
                "intervals": {
                    m: [[str(a), str(b)] for a, b in iv]
                    for m, iv in sorted(self.intervals.items())
                },
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode()).hexdigest()


@dataclass(frozen=True)
class Epoch:
    """One program epoch: half-open [start, end), active-mission set."""

    epoch_id: str
    start: np.datetime64
    end: np.datetime64
    missions: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class EpochPartition:
    """The partition + the pre-merge boundary trail."""

    epochs: tuple[Epoch, ...]
    raw_boundaries: tuple[np.datetime64, ...]


def build_census(catalog: dict[str, dict[str, list[str]]]) -> CensusArtifact:
    """Per-mission ACTIVE intervals from loader metadata.

    Args:
        catalog: ``{mission: {"dates": [ISO day, ...]}}`` — the observed
            file days (the census leg's ``dates`` field).

    Returns:
        Intervals split wherever an intra-mission gap exceeds
        ``MISSION_GAP_SPLIT_D`` days; day resolution; deterministic.
    """
    intervals: dict[str, tuple[tuple[np.datetime64, np.datetime64], ...]] = {}
    for mission, meta in sorted(catalog.items()):
        if "dates" not in meta:
            raise ValueError(
                f"catalog entry {mission!r} lacks the 'dates' field — the "
                "census snapshot predates schema v2; re-run the census leg"
            )
        days = np.array(sorted(set(meta["dates"])), dtype="datetime64[D]")
        if days.size == 0:
            continue
        gaps = np.diff(days) / np.timedelta64(1, "D")
        split_at = np.where(gaps > MISSION_GAP_SPLIT_D)[0]
        spans = []
        start_idx = 0
        for idx in split_at:
            spans.append((days[start_idx], days[idx]))
            start_idx = idx + 1
        spans.append((days[start_idx], days[-1]))
        intervals[mission] = tuple(spans)
    return CensusArtifact(schema_version=1, intervals=intervals)


def _active_missions(
    census: CensusArtifact, start: np.datetime64, end: np.datetime64
) -> frozenset[str]:
    """Missions with any ACTIVE overlap with [start, end)."""
    out = set()
    for mission, spans in census.intervals.items():
        for a, b in spans:
            if a < end and b >= start:
                out.add(mission)
    return frozenset(out)


def partition_epochs(census: CensusArtifact) -> EpochPartition:
    """Epochs at constellation-change dates, minimum-length merged.

    Boundaries = the union of active-interval endpoints (an interval END
    contributes the day AFTER it — the constellation changes the next
    day). Epochs shorter than ``MIN_EPOCH_DAYS`` merge into the neighbor
    with the higher mission-set Jaccard similarity (tie → the earlier
    neighbor); the pre-merge boundaries survive as ``raw_boundaries``.

    Args:
        census: The census artifact.

    Returns:
        The partition, epochs named ``e{index:02d}_{start ISO}`` in time
        order.
    """
    bounds: set[np.datetime64] = set()
    for spans in census.intervals.values():
        for a, b in spans:
            bounds.add(a)
            bounds.add(b + np.timedelta64(1, "D"))  # change takes effect next day
    raw = tuple(sorted(bounds))
    if len(raw) < 2:
        raise ValueError("census yields no epoch boundaries")

    segs = [
        (raw[i], raw[i + 1], _active_missions(census, raw[i], raw[i + 1]))
        for i in range(len(raw) - 1)
    ]

    def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
        if not a and not b:
            return 1.0
        return len(a & b) / len(a | b)

    def _days(seg: tuple[np.datetime64, np.datetime64, frozenset[str]]) -> float:
        return float((seg[1] - seg[0]) / np.timedelta64(1, "D"))

    merged = list(segs)
    while True:
        short_idx = next(
            (i for i, seg in enumerate(merged) if _days(seg) < MIN_EPOCH_DAYS),
            None,
        )
        if short_idx is None or len(merged) == 1:
            break
        seg = merged[short_idx]
        left = merged[short_idx - 1] if short_idx > 0 else None
        right = merged[short_idx + 1] if short_idx < len(merged) - 1 else None
        # tie -> earlier neighbor: strict > required to prefer the right
        if left is None:
            target = short_idx + 1
        elif right is None:
            target = short_idx - 1
        elif _jaccard(seg[2], right[2]) > _jaccard(seg[2], left[2]):
            target = short_idx + 1
        else:
            target = short_idx - 1
        other = merged[target]
        lo = min(seg[0], other[0])
        hi = max(seg[1], other[1])
        fused = (lo, hi, _active_missions(census, lo, hi))
        i, j = sorted((short_idx, target))
        merged[i : j + 1] = [fused]

    epochs = tuple(
        Epoch(
            epoch_id=f"e{i:02d}_{seg[0]}",
            start=seg[0],
            end=seg[1],
            missions=seg[2],
        )
        for i, seg in enumerate(merged)
    )
    return EpochPartition(epochs=epochs, raw_boundaries=raw)


def window_epoch(window_center_date: np.datetime64, epochs: tuple[Epoch, ...]) -> str:
    """The WINDOW-CENTER rule (fork-d D6): the epoch containing the center.

    Accepted approximation (recorded): a window straddling an epoch
    boundary is assigned WHOLLY to its center's epoch — windows are short
    (60 d) against epochs (≥ 365 d), so the mixed-support edge affects a
    bounded sliver and the assignment stays deterministic.

    Args:
        window_center_date: The solve window's center day.
        epochs: The partition's epochs (half-open [start, end)).

    Returns:
        The containing epoch's id.

    Raises:
        ValueError: If the date falls outside every epoch.
    """
    for e in epochs:
        if e.start <= window_center_date < e.end:
            return e.epoch_id
    raise ValueError(
        f"{window_center_date} lies outside every epoch "
        f"[{epochs[0].start}, {epochs[-1].end})"
    )


def reference_candidates(
    epochs: tuple[Epoch, ...], locked_exclusions: frozenset[str]
) -> list[str]:
    """Reference-epoch candidates, constellation counted NET of locked.

    Args:
        epochs: The partition's epochs.
        locked_exclusions: Locked mission codes (never fit substrate).

    Returns:
        Epoch ids whose net mission count is ≥ 4, in time order.
    """
    return [e.epoch_id for e in epochs if len(e.missions - locked_exclusions) >= 4]
