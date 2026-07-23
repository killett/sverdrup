"""The single epoch registry (phase-14 0a-2, fork-c/e/f).

epoch → missions → holdout(validation) → locked instruments →
fit-vs-transferred, with the sparse-era handicap columns. Holdout criteria
applied IN ORDER, mechanically (fork-c, recorded):

1. never the climate-reference line (TOPEX→J1→J2→J3 family) where an
   alternative exists;
2. prefer a holdout with an instrument-class sibling still assimilated
   (the δ_j3 := δ_j2n precedent);
3. prefer minimal geometry-class-mix (repeat/drifting) distortion;
4. one holdout per epoch, stable (lexicographic tie-break).

The ANCHOR exception (spec fork-c, "2017/five-mission first by
construction"): the epoch containing ``ANCHOR_DATE`` holds out ``j3`` —
the signed workhorse — with criterion ``signed-workhorse-by-construction``.

Locked tier: gauges (universal spine) in every epoch; c2 wherever CryoSat-2
flies (2010→). Sealed later by Task 19; this module only DRAFTS.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np

from sverdrup.application.epochs import CensusArtifact, Epoch

ANCHOR_DATE = np.datetime64("2017-07-01")

# Recorded instrument-class map (fork-c criterion 2). SWOT nadir carries a
# Poseidon-3C altimeter; GFO (g2) is its own sibling-less line.
INSTRUMENT_CLASS: dict[str, str] = {
    "tp": "poseidon",
    "tpn": "poseidon",
    "j1": "poseidon",
    "j1n": "poseidon",
    "j1g": "poseidon",
    "j2": "poseidon",
    "j2n": "poseidon",
    "j2g": "poseidon",
    "j3": "poseidon",
    "j3n": "poseidon",
    "j3g": "poseidon",
    "s6a": "poseidon",
    "s6a-lr": "poseidon",
    "swon": "poseidon",
    "swonc": "poseidon",
    "e1": "ers-line",
    "e1g": "ers-line",
    "e2": "ers-line",
    "en": "ers-line",
    "enn": "ers-line",
    "al": "ers-line",
    "alg": "ers-line",
    "h2a": "hy2",
    "h2ag": "hy2",
    "h2b": "hy2",
    "s3a": "sentinel3",
    "s3b": "sentinel3",
    "c2": "cryosat",
    "c2n": "cryosat",
    "g2": "gfo",
}

# Recorded orbit-geometry class (fork-c criterion 3; the Phase-11 repeat/
# drifting classification): geodetic/drifting phases + CryoSat drift.
DRIFTING: frozenset[str] = frozenset(
    {"e1g", "j1g", "j2g", "alg", "h2ag", "c2", "c2n", "enn", "g2"}
)

LOCKED_ALTIMETERS: frozenset[str] = frozenset({"c2", "c2n"})


@dataclass(frozen=True)
class EpochRow:
    """One registry row (all columns the seal consumes)."""

    epoch_id: str
    start: np.datetime64
    end: np.datetime64
    missions: tuple[str, ...]
    holdout: str
    criterion: str
    role: str  # "fit+validate" | "validate-only"
    fit_or_transferred: str  # "fit" | "transferred"
    locked_instruments: tuple[str, ...]
    fit_substrate_fraction: float
    mask_66: bool
    sibling_less: bool


@dataclass(frozen=True)
class EpochTable:
    """The registry draft (sealed by Task 19)."""

    rows: tuple[EpochRow, ...]


def _select_holdout(missions: frozenset[str]) -> tuple[str, str]:
    """The mechanical criteria chain over one epoch's NET candidates."""
    candidates = sorted(missions - LOCKED_ALTIMETERS)
    if not candidates:
        raise ValueError(f"epoch has no holdout candidate: {sorted(missions)}")
    # 1. never the climate line where an alternative exists
    non_ref = [c for c in candidates if INSTRUMENT_CLASS.get(c) != "poseidon"]
    pool = non_ref or candidates
    criterion = "non-climate-line" if non_ref else "climate-line-only-choice"

    # 2. prefer a candidate with an instrument-class sibling still assimilated
    def has_sibling(c: str) -> bool:
        cls = INSTRUMENT_CLASS.get(c)
        return any(
            m != c and INSTRUMENT_CLASS.get(m) == cls
            for m in missions - LOCKED_ALTIMETERS
        )

    with_sib = [c for c in pool if has_sibling(c)]
    if with_sib:
        pool = with_sib
        criterion += "+sibling-assimilated"
    # 3. minimal geometry-class-mix distortion on removal
    assim = sorted(missions - LOCKED_ALTIMETERS)
    n = len(assim)
    ratio_all = sum(1 for m in assim if m in DRIFTING) / n

    def distortion(c: str) -> float:
        rest = [m for m in assim if m != c]
        if not rest:
            return 0.0
        return abs(sum(1 for m in rest if m in DRIFTING) / len(rest) - ratio_all)

    best = min(distortion(c) for c in pool)
    pool = [c for c in pool if distortion(c) == best]
    criterion += "+min-geometry-distortion"
    # 4. stable: lexicographic
    return pool[0], criterion


def build_epoch_table(epochs: tuple[Epoch, ...], census: CensusArtifact) -> EpochTable:
    """The registry draft from the partition + census.

    Args:
        epochs: The epoch partition.
        census: The census artifact (drives the c2-flies column).

    Returns:
        One row per epoch; reference epochs (net ≥ 4) are
        ``fit+validate``/``fit``, sparse epochs ``validate-only``/
        ``transferred``. ``fit_substrate_fraction`` = (net − 1)/net — the
        assimilable fraction left after the holdout is withheld.
    """
    rows = []
    for e in epochs:
        net = e.missions - LOCKED_ALTIMETERS
        if ANCHOR_DATE >= e.start and ANCHOR_DATE < e.end and "j3" in e.missions:
            holdout, criterion = "j3", "signed-workhorse-by-construction"
        else:
            holdout, criterion = _select_holdout(e.missions)
        reference = len(net) >= 4
        locked = ["gauges"]
        if e.missions & LOCKED_ALTIMETERS:
            locked.extend(sorted(e.missions & LOCKED_ALTIMETERS))
        cls = INSTRUMENT_CLASS.get(holdout, "unknown")
        sibling_less = not any(
            m != holdout and INSTRUMENT_CLASS.get(m) == cls for m in net
        )
        rows.append(
            EpochRow(
                epoch_id=e.epoch_id,
                start=e.start,
                end=e.end,
                missions=tuple(sorted(e.missions)),
                holdout=holdout,
                criterion=criterion,
                role="fit+validate" if reference else "validate-only",
                fit_or_transferred="fit" if reference else "transferred",
                locked_instruments=tuple(locked),
                fit_substrate_fraction=(len(net) - 1) / len(net),
                mask_66=(cls == "ers-line"),
                sibling_less=sibling_less,
            )
        )
    return EpochTable(rows=tuple(rows))


def serialize_epoch_table(table: EpochTable) -> bytes:
    """Canonical JSON bytes (the seal substrate; byte-deterministic)."""
    payload = [
        {
            "epoch_id": r.epoch_id,
            "start": str(r.start),
            "end": str(r.end),
            "missions": list(r.missions),
            "holdout": r.holdout,
            "criterion": r.criterion,
            "role": r.role,
            "fit_or_transferred": r.fit_or_transferred,
            "locked_instruments": list(r.locked_instruments),
            "fit_substrate_fraction": r.fit_substrate_fraction,
            "mask_66": r.mask_66,
            "sibling_less": r.sibling_less,
        }
        for r in table.rows
    ]
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
