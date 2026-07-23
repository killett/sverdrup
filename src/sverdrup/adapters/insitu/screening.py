"""Gauge screening pipeline + seeded stratified locked/dev split (0a-3a).

**The firewall (SPEC §4-F, verbatim):** data-QUALITY screening may look at
gauge data; SKILL-based selection may not — screening never consults any map.

Criteria run IN the recorded order, each emitting a per-gauge pass/fail row
(visible, never silent): (1) RLR datum continuity; (2) era completeness;
(3) open-ocean siting (excluded-basin polygons + island/offshore preference
flag); (4) proximity to the target grid's ocean points; (5) correction-
consistency (DAC/tide handling recorded per gauge; the B2023 Eq.-1 stack is
the reference convention).

The locked/dev split is drawn AFTER screening, stratified by
basin × era-coverage class, 30% locked per stratum, seeded from
``derive_seed("insitu", "phase14-seal", "locked-split", 0)`` (fork-f pin 3)
— rebuilds are byte-equal.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sverdrup.core.seeding import derive_seed

# Proximity ceiling [km] ≈ the shipped λx neighborhood (151.86 km at the
# phase-13 acceptance): a gauge farther than the product's resolved scale
# from the nearest wet gridpoint cannot be compared to the map.
L_PROX_KM = 150.0

_EARTH_RADIUS_KM = 6371.0

# Excluded basins (recorded lon/lat boxes; lon in [0, 360)). Marginal or
# semi-enclosed seas where open-ocean SSH comparison is invalid.
EXCLUDED_BASINS: tuple[tuple[str, float, float, float, float], ...] = (
    ("baltic", 9.0, 31.0, 53.0, 66.0),
    ("black_sea", 27.0, 42.0, 40.0, 47.5),
    ("mediterranean_w", 354.0, 360.0, 30.0, 46.0),
    ("mediterranean_e", 0.0, 37.0, 30.0, 46.0),
    ("hudson_bay", 265.0, 285.0, 51.0, 64.0),
    ("persian_gulf", 47.0, 57.0, 23.0, 31.0),
    ("red_sea", 32.0, 44.0, 12.0, 30.0),
)

# The recorded 8-box basin partition for split strata (lon in [0, 360)).
BASIN_STRATA: tuple[tuple[str, float, float, float, float], ...] = (
    ("arctic", 0.0, 360.0, 66.0, 90.0),
    ("southern", 0.0, 360.0, -90.0, -50.0),
    ("n_atlantic", 260.0, 360.0, 0.0, 66.0),
    ("s_atlantic", 290.0, 360.0, -50.0, 0.0),
    ("n_pacific", 100.0, 260.0, 0.0, 66.0),
    ("s_pacific", 130.0, 290.0, -50.0, 0.0),
    ("indian", 20.0, 130.0, -50.0, 30.0),
    ("other", 0.0, 360.0, -90.0, 90.0),  # catch-all, matched last
)

LOCKED_FRACTION = 0.3

_CRITERIA_ORDER = (
    "rlr_datum_continuity",
    "era_completeness",
    "open_ocean_siting",
    "proximity",
    "correction_consistency",
)


@dataclass(frozen=True)
class Epoch:
    """One program epoch (id + half-open [start, end) day interval)."""

    epoch_id: str
    start: np.datetime64
    end: np.datetime64


@dataclass(frozen=True)
class GaugeRecord:
    """One screened gauge: position, daily coverage, recorded metadata."""

    gauge_id: str
    lon: float
    lat: float
    days: np.ndarray  # datetime64[D], the days with valid daily means
    rlr_datum_ok: bool
    corrections: dict[str, str]


@dataclass(frozen=True)
class ScreeningRow:
    """One (gauge, criterion) verdict — every pair emits one, visibly."""

    gauge_id: str
    criterion: str
    passed: bool
    detail: str


def _in_box(
    lon: float, lat: float, box: tuple[str, float, float, float, float]
) -> bool:
    _, lon_min, lon_max, lat_min, lat_max = box
    lon_w = lon % 360.0
    return lon_min <= lon_w <= lon_max and lat_min <= lat <= lat_max


def _haversine_km(
    lon1: float, lat1: float, lon2: np.ndarray, lat2: np.ndarray
) -> np.ndarray:
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp = p2 - p1
    dl = np.radians(lon2 - lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return np.asarray(2 * _EARTH_RADIUS_KM * np.arcsin(np.sqrt(a)))


def era_class(days: np.ndarray) -> str:
    """The era-coverage stratum class of a daily series.

    Args:
        days: The gauge's valid days.

    Returns:
        ``pre-2000`` / ``2000-2010`` / ``post-2010`` / ``full-span``
        (spans crossing both the 2000 and 2010 boundaries).
    """
    first, last = days.min(), days.max()
    y2000, y2010 = np.datetime64("2000-01-01"), np.datetime64("2010-01-01")
    if last < y2000:
        return "pre-2000"
    if first >= y2010:
        return "post-2010"
    if first >= y2000 and last < y2010:
        return "2000-2010"
    return "full-span"


def _check_era_completeness(
    g: GaugeRecord, epochs: tuple[Epoch, ...]
) -> tuple[bool, str]:
    """≥ 70% of days in each epoch the gauge claims + ≥ 3 years total."""
    total_years = g.days.size / 365.25
    if total_years < 3.0:
        return False, f"total {total_years:.1f} y < 3 y"
    details = []
    ok = True
    for e in epochs:
        claimed = (g.days >= e.start) & (g.days < e.end)
        if not claimed.any():
            continue  # the gauge does not claim this epoch
        n_epoch_days = int((e.end - e.start) / np.timedelta64(1, "D"))
        frac = float(claimed.sum()) / n_epoch_days
        details.append(f"{e.epoch_id}:{frac:.2f}")
        if frac < 0.70:
            ok = False
    return ok, "; ".join(details) or "claims no epoch"


def screen_gauges(
    gauges: list[GaugeRecord] | tuple[GaugeRecord, ...],
    epochs: tuple[Epoch, ...],
    ocean_points: tuple[np.ndarray, np.ndarray] | None,
) -> tuple[tuple[ScreeningRow, ...], tuple[str, ...]]:
    """Run the recorded criteria IN ORDER over every gauge.

    Args:
        gauges: The candidate gauge records.
        epochs: The program epochs (census-derived; synthetic in tests).
        ocean_points: ``(lon, lat)`` arrays of the target grid's wet points,
            or None — the Stage-0 DEFERRAL (recorded interpretation, a
            Gate-0 owner attention item): no program grid exists in
            Stage 0, so criterion 4 binds AT CONSUMPTION against each
            stage's actual product grid (the evaluator's wet-node interp
            already self-excludes unreachable gauges); the row is emitted
            visibly as deferred, never silently skipped.

    Returns:
        ``(rows, passed_ids)`` — one row per (gauge, criterion) in order,
        and the ids passing ALL criteria (input order preserved).
    """
    rows: list[ScreeningRow] = []
    passed_ids: list[str] = []
    for g in gauges:
        verdicts: dict[str, tuple[bool, str]] = {}
        verdicts["rlr_datum_continuity"] = (
            g.rlr_datum_ok,
            "RLR datum record present" if g.rlr_datum_ok else "no RLR datum",
        )
        verdicts["era_completeness"] = _check_era_completeness(g, epochs)
        basin_hit = next(
            (b[0] for b in EXCLUDED_BASINS if _in_box(g.lon, g.lat, b)), None
        )
        verdicts["open_ocean_siting"] = (
            basin_hit is None,
            (
                f"excluded basin {basin_hit}"
                if basin_hit
                else "open ocean (island/offshore preference recorded)"
            ),
        )
        if ocean_points is None:
            verdicts["proximity"] = (
                True,
                "DEFERRED to consumption grid (Stage-0 recorded "
                "interpretation; Gate-0 owner attention item)",
            )
        else:
            ocean_lon, ocean_lat = ocean_points
            d_km = float(_haversine_km(g.lon, g.lat, ocean_lon, ocean_lat).min())
            verdicts["proximity"] = (
                d_km <= L_PROX_KM,
                f"nearest wet gridpoint {d_km:.0f} km (ceiling {L_PROX_KM:.0f})",
            )
        has_corr = bool(g.corrections.get("dac")) and bool(g.corrections.get("tide"))
        verdicts["correction_consistency"] = (
            has_corr,
            (
                f"recorded {g.corrections} (B2023 Eq.-1 reference convention)"
                if has_corr
                else "DAC/tide handling unrecorded"
            ),
        )
        for crit in _CRITERIA_ORDER:
            ok, detail = verdicts[crit]
            rows.append(ScreeningRow(g.gauge_id, crit, ok, detail))
        if all(verdicts[c][0] for c in _CRITERIA_ORDER):
            passed_ids.append(g.gauge_id)
    return tuple(rows), tuple(passed_ids)


def _basin_of(lon: float, lat: float) -> str:
    return next(b[0] for b in BASIN_STRATA if _in_box(lon, lat, b))


def stratified_split(
    gauges: list[GaugeRecord] | tuple[GaugeRecord, ...],
) -> dict[str, tuple[str, ...]]:
    """The seeded stratified locked/dev split (drawn AFTER screening).

    Strata = basin (the recorded 8-box partition) × era-coverage class;
    ``LOCKED_FRACTION`` (30%) locked per stratum (round-half-up); ONE rng
    seeded from ``derive_seed("insitu", "phase14-seal", "locked-split", 0)``
    consumed over strata in sorted order — rebuilds are byte-equal.

    Args:
        gauges: The screened (surviving) gauge records.

    Returns:
        ``{"locked": (...), "dev": (...)}`` — id tuples, sorted.
    """
    strata: dict[str, list[str]] = {}
    for g in gauges:
        key = f"{_basin_of(g.lon, g.lat)}|{era_class(g.days)}"
        strata.setdefault(key, []).append(g.gauge_id)
    rng = np.random.default_rng(
        derive_seed("insitu", "phase14-seal", "locked-split", 0)
    )
    locked: list[str] = []
    dev: list[str] = []
    for key in sorted(strata):
        ids = sorted(strata[key])
        k = int(np.floor(LOCKED_FRACTION * len(ids) + 0.5))
        picked = rng.permutation(len(ids))[:k]
        chosen = {ids[i] for i in picked}
        locked.extend(sorted(chosen))
        dev.extend(sorted(set(ids) - chosen))
    return {"locked": tuple(sorted(locked)), "dev": tuple(sorted(dev))}
