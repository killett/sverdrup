"""Orbit geometry derived FROM the obs files (spec §2; fork-a pins 1-5).

phi0-plane frame (pinned once, shared with eval/map_spectrum.py):
x = lon * cos(phi0) [deg -> km via 111.32], y = lat [deg -> km].
Headings are AXIAL (alpha == alpha + 180), measured from NORTH, in [0, 180).
d_perp_km = s_lon_km * |cos(heading_north)| (formula recorded in the artifact).

The withheld Cryosat-2 (c2) file is NEVER opened: mission ids are checked
through ``input_adapter._mission_code`` (the standing withheld-leak guard)
before any ``xr.open_dataset`` call, and ``build_geometry_artifact`` refuses
the id up front.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import xarray as xr

from sverdrup.application.calibration.harness import atomic_write_json
from sverdrup.eval.phase11_constants import (
    CLUSTER_TOL_DEG,
    DERIVATION_VERSION,
    RATIO_GAP_HI,
    RATIO_GAP_LO,
    REPEAT_RATIO_MAX,
)
from sverdrup.validation.input_adapter import _days_since_epoch, _mission_code

KM_PER_DEG = 111.32
_GAP_SEC = 60.0  # inter-pass threshold; mirrors harness._PASS_GAP_SEC
_LON_LO, _LON_HI = 295.0, 305.0  # map-box longitudes; crossings kept in-domain
_D_PERP_FORMULA = "d_perp_km = s_lon_km * abs(cos(radians(heading_north_deg)))"

Pass = tuple[np.ndarray, np.ndarray, np.ndarray]


@dataclass(frozen=True)
class FamilyGeometry:
    """Per-family (asc/desc) track geometry derived from one mission's passes.

    Attributes:
        heading_north_deg: Axial track heading from north, in [0, 180).
        n_passes: Number of passes in the family.
        n_crossings: Passes crossing phi0 IN-DOMAIN (spacing uses only these).
        orbit_class: ``"repeat"`` or ``"drifting"`` (classifier: obligation 2).
        s_lon_km: Repeat only — median adjacent cluster-center gap at phi0.
        d_perp_km: Repeat only — ``s_lon_km * |cos(heading_north)|``.
        spacing_quantiles_km: Drifting only — (q10, q50, q90) adjacent gaps.
        classifier_ratio: ``n_clusters / n_crossings`` — the classifier's
            decision variable, recorded per the Task-12 rider (2026-07-16).
        n_clusters: Single-linkage cluster count at the pinned tolerance.
        cluster_size_median: Median crossings per cluster — the corroborating
            second evidence axis (true repeat ~revisit count; chance chains ~2).
    """

    heading_north_deg: float
    n_passes: int
    n_crossings: int
    orbit_class: str
    s_lon_km: float | None
    d_perp_km: float | None
    spacing_quantiles_km: tuple[float, float, float] | None
    classifier_ratio: float
    n_clusters: int
    cluster_size_median: float


def split_passes(
    lon: np.ndarray,
    lat: np.ndarray,
    time: np.ndarray,
    gap_sec: float = _GAP_SEC,
) -> list[tuple[np.ndarray, np.ndarray, np.ndarray, bool]]:
    """Segment one mission's arrays into passes on time gaps > ``gap_sec``.

    Reuses the harness ``_PASS_GAP_SEC`` convention (time in DAYS since epoch;
    the threshold converts to days here). Each segment is labelled ascending
    or descending on the median sign of dlat/dt within the segment.

    Args:
        lon: Per-observation longitudes (degrees).
        lat: Per-observation latitudes (degrees).
        time: Per-observation times in days since epoch.
        gap_sec: Inter-pass gap threshold in seconds.

    Returns:
        List of ``(lon, lat, time, ascending)`` per-pass tuples in time order.
    """
    lon = np.asarray(lon, dtype=float)
    lat = np.asarray(lat, dtype=float)
    t = np.asarray(time, dtype=float)
    order = np.argsort(t, kind="stable")
    lon, lat, t = lon[order], lat[order], t[order]
    gap = np.diff(t) > gap_sec / 86400.0
    seg_id = np.concatenate([[0], np.cumsum(gap)])
    passes: list[tuple[np.ndarray, np.ndarray, np.ndarray, bool]] = []
    for seg in np.unique(seg_id):
        mask = seg_id == seg
        if int(mask.sum()) < 2:
            continue  # a single point has no direction
        ascending = bool(np.median(np.sign(np.diff(lat[mask]))) > 0)
        passes.append((lon[mask], lat[mask], t[mask], ascending))
    return passes


def _fit_heading(passes: list[Pass], phi0: float) -> float:
    """Axial from-north heading via per-pass TLS + doubled-angle circular mean.

    Per-pass total-least-squares direction in the phi0 km plane, then the
    doubled-angle (axial) circular mean over passes (batch-1 pin 4):
    ``mean_angle = 0.5 * atan2(mean(sin 2a_i), mean(cos 2a_i))``; the
    east-referenced fit angle converts to from-NORTH axial [0, 180).

    Args:
        passes: Per-pass ``(lon, lat, time)`` arrays.
        phi0: Reference latitude of the plane (degrees).

    Returns:
        Heading from north in degrees, in [0, 180).
    """
    cph = np.cos(np.deg2rad(phi0))
    doubled = []
    for lon, lat, *_ in passes:
        x = np.asarray(lon, dtype=float) * KM_PER_DEG * cph
        y = np.asarray(lat, dtype=float) * KM_PER_DEG
        xc, yc = x - x.mean(), y - y.mean()
        cov = np.cov(np.vstack([xc, yc]))
        _evals, evecs = np.linalg.eigh(cov)
        v = evecs[:, -1]  # principal (TLS) direction, east-referenced
        doubled.append(2.0 * np.arctan2(v[1], v[0]))
    mean2 = np.arctan2(np.mean(np.sin(doubled)), np.mean(np.cos(doubled)))
    a_east_deg = np.rad2deg(0.5 * mean2)
    return float((90.0 - a_east_deg) % 180.0)


def _phi0_crossings(
    passes: list[Pass],
    phi0: float,
    lon_lo: float = _LON_LO,
    lon_hi: float = _LON_HI,
) -> np.ndarray:
    """Linear-interpolated crossing longitude of each pass at ``lat == phi0``.

    Keeps only crossings inside ``[lon_lo, lon_hi]`` (obligation 4: in-domain
    only — out-of-box tracks must not pollute the spacing statistics).

    Args:
        passes: Per-pass ``(lon, lat, time)`` arrays.
        phi0: Crossing latitude (degrees).
        lon_lo: Domain lower longitude bound (degrees).
        lon_hi: Domain upper longitude bound (degrees).

    Returns:
        Array of in-domain crossing longitudes, one per crossing pass.
    """
    crossings = []
    for lon, lat, *_ in passes:
        lat = np.asarray(lat, dtype=float)
        if not (lat.min() <= phi0 <= lat.max()):
            continue
        order = np.argsort(lat)
        xlon = float(np.interp(phi0, lat[order], np.asarray(lon, dtype=float)[order]))
        if lon_lo <= xlon <= lon_hi:
            crossings.append(xlon)
    return np.asarray(crossings, dtype=float)


def classify_orbit(
    crossing_lons: np.ndarray, tol_deg: float = CLUSTER_TOL_DEG
) -> tuple[str, np.ndarray]:
    """Classify the family's orbit from its phi0-crossing longitudes.

    Sorts crossings, single-linkage clusters with gap > ``tol_deg``, and
    applies the pinned rule: ``"repeat"`` iff
    ``n_clusters / n_crossings <= REPEAT_RATIO_MAX``.

    Gap-tabling rider (owner Task-12 ruling, 2026-07-16): a ratio strictly
    inside the measured gap between the classified sides
    ``(RATIO_GAP_LO, RATIO_GAP_HI)`` refuses — it TABLES an owner decision,
    never a silent classification.

    Args:
        crossing_lons: In-domain crossing longitudes (degrees).
        tol_deg: Single-linkage cluster tolerance (degrees).

    Returns:
        ``(orbit_class, cluster_centers)`` with centers in degrees, sorted.

    Raises:
        ValueError: If there are no crossings to classify, or if the ratio
            lands inside the tabling gap (owner decision required).
    """
    xs = np.sort(np.asarray(crossing_lons, dtype=float))
    if xs.size == 0:
        raise ValueError("no phi0 crossings in domain — cannot classify orbit")
    centers, _sizes = _clusters(xs, tol_deg)
    ratio = centers.size / xs.size
    if RATIO_GAP_LO < ratio < RATIO_GAP_HI:
        raise ValueError(
            f"orbit-class ratio {ratio:.4f} lands inside the measured gap "
            f"({RATIO_GAP_LO}, {RATIO_GAP_HI}) — TABLES an owner decision; "
            "never silently classified (Task-12 rider, 2026-07-16)"
        )
    orbit_class = "repeat" if ratio <= REPEAT_RATIO_MAX else "drifting"
    return orbit_class, centers


def _clusters(xs_sorted: np.ndarray, tol_deg: float) -> tuple[np.ndarray, list[int]]:
    """Single-linkage clusters of sorted crossings: (centers, sizes)."""
    breaks = np.nonzero(np.diff(xs_sorted) > tol_deg)[0]
    bounds = np.concatenate([[0], breaks + 1, [xs_sorted.size]])
    centers = np.array(
        [xs_sorted[a:b].mean() for a, b in zip(bounds[:-1], bounds[1:], strict=True)]
    )
    sizes = [int(b - a) for a, b in zip(bounds[:-1], bounds[1:], strict=True)]
    return centers, sizes


def derive_family(passes: list[Pass], phi0: float, ascending: bool) -> FamilyGeometry:
    """Derive one family's geometry from its passes.

    Spacing (repeat): gaps between adjacent CLUSTER CENTERS, median ->
    ``s_lon_km`` (deg -> km via ``KM_PER_DEG * cos(phi0)``). Drifting:
    (q10, q50, q90) of adjacent gaps of all sorted crossings.

    Args:
        passes: Per-pass ``(lon, lat, time)`` arrays for one asc/desc family.
        phi0: Reference latitude of the plane (degrees).
        ascending: Family label (recorded upstream; not used in the numbers).

    Returns:
        The family's :class:`FamilyGeometry`.
    """
    heading = _fit_heading(passes, phi0)
    crossings = _phi0_crossings(passes, phi0)
    orbit_class, centers = classify_orbit(crossings)
    _centers, sizes = _clusters(np.sort(crossings), CLUSTER_TOL_DEG)
    deg_to_km = KM_PER_DEG * abs(np.cos(np.deg2rad(phi0)))
    s_lon_km: float | None = None
    d_perp_km: float | None = None
    quantiles: tuple[float, float, float] | None = None
    if orbit_class == "repeat":
        center_gaps = np.diff(np.sort(centers))
        if center_gaps.size:
            s_lon_km = float(np.median(center_gaps)) * deg_to_km
            d_perp_km = s_lon_km * abs(np.cos(np.deg2rad(heading)))
    else:
        gaps_km = np.diff(np.sort(crossings)) * deg_to_km
        q10, q50, q90 = np.quantile(gaps_km, [0.1, 0.5, 0.9])
        quantiles = (float(q10), float(q50), float(q90))
    return FamilyGeometry(
        heading_north_deg=heading,
        n_passes=len(passes),
        n_crossings=int(crossings.size),
        orbit_class=orbit_class,
        s_lon_km=s_lon_km,
        d_perp_km=d_perp_km,
        spacing_quantiles_km=quantiles,
        classifier_ratio=float(centers.size / crossings.size),
        n_clusters=int(centers.size),
        cluster_size_median=float(np.median(sizes)),
    )


def derive_mission_geometry(
    obs_path: Path | str, phi0: float
) -> dict[str, FamilyGeometry | None]:
    """Derive ``{"asc": ..., "desc": ...}`` for one mission file.

    Refuses mission id ``"c2"`` (and any unknown mission) through the standing
    withheld-leak guard BEFORE the file is opened.

    Args:
        obs_path: L3 along-track NetCDF path (mission id in the filename).
        phi0: Reference latitude of the plane (degrees).

    Returns:
        Family geometries keyed ``"asc"``/``"desc"``; ``None`` for an absent
        family.

    Raises:
        ValueError: If the filename is not a recognised mapping mission (the
            withheld Cryosat-2 ``c2`` file above all).
    """
    obs_path = Path(obs_path)
    _mission_code(obs_path)  # raises on c2/unknown; the file stays unopened
    ds = xr.open_dataset(obs_path)
    lon = np.asarray(ds["longitude"], dtype=float)
    lat = np.asarray(ds["latitude"], dtype=float)
    t = _days_since_epoch(np.asarray(ds["time"]))
    finite = np.isfinite(lon) & np.isfinite(lat)
    passes = split_passes(lon[finite], lat[finite], t[finite])
    out: dict[str, FamilyGeometry | None] = {}
    for name, want_asc in (("asc", True), ("desc", False)):
        fam = [(lo, la, ti) for lo, la, ti, asc in passes if asc == want_asc]
        out[name] = derive_family(fam, phi0, want_asc) if fam else None
    return out


def _sha256_file(path: Path) -> str:
    """Return the sha256 hex digest of a file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _find_obs(obs_dir: Path, mission: str) -> Path:
    """Locate one mission's L3 file in ``obs_dir`` by the standing pattern."""
    hits = sorted(obs_dir.glob(f"dt_gulfstream_{mission}_phy_l3_*.nc"))
    if len(hits) != 1:
        raise FileNotFoundError(
            f"expected exactly one obs file for mission {mission!r} in "
            f"{obs_dir}, found {len(hits)}"
        )
    return hits[0]


def build_geometry_artifact(
    obs_dir: Path | str,
    missions: list[str],
    phi0: float,
    out_path: Path | str,
) -> str:
    """Derive all missions into one deterministic JSON artifact.

    Key: sha256 over (sorted obs-file sha256s, DERIVATION_VERSION, box, phi0).
    Provenance block inside: file shas, missions, n_passes/n_crossings per
    family. Loads instead of re-deriving when the stored key matches. Written
    via ``atomic_write_json`` — bytes are deterministic (no timestamps).

    Args:
        obs_dir: Directory holding the L3 along-track files.
        missions: Mission ids to derive (must not contain ``"c2"``).
        phi0: Reference latitude of the plane (degrees).
        out_path: Artifact JSON path.

    Returns:
        sha256 hex digest of the artifact file bytes.

    Raises:
        ValueError: If ``"c2"`` is requested (zero-c2 invariant).
        FileNotFoundError: If a mission's obs file is absent or ambiguous.
    """
    missions = sorted(missions)
    if "c2" in missions:
        raise ValueError(
            "mission 'c2' is the withheld Cryosat-2 track — the c2 file is "
            "never opened (zero-c2 invariant)"
        )
    obs_dir = Path(obs_dir)
    out_path = Path(out_path)
    paths = {m: _find_obs(obs_dir, m) for m in missions}
    obs_shas = {m: _sha256_file(p) for m, p in paths.items()}
    key_material = json.dumps(
        {
            "obs_sha256": obs_shas,
            "derivation_version": DERIVATION_VERSION,
            "box_lon": [_LON_LO, _LON_HI],
            "phi0": phi0,
        },
        sort_keys=True,
    )
    key = hashlib.sha256(key_material.encode()).hexdigest()
    if out_path.exists():
        try:
            existing = json.loads(out_path.read_text())
        except json.JSONDecodeError:
            existing = {}
        if existing.get("key") == key:
            return _sha256_file(out_path)
    mission_blocks: dict[str, dict[str, dict[str, object] | None]] = {}
    for m in missions:
        fams = derive_mission_geometry(paths[m], phi0)
        mission_blocks[m] = {
            fam_name: (asdict(fam) if fam is not None else None)
            for fam_name, fam in fams.items()
        }
    artifact = {
        "derivation_version": DERIVATION_VERSION,
        "key": key,
        "phi0": phi0,
        "box_lon": [_LON_LO, _LON_HI],
        "d_perp_formula": _D_PERP_FORMULA,
        "missions": mission_blocks,
        "provenance": {
            "obs_sha256": obs_shas,
            "missions": missions,
            "n_passes": {
                m: {
                    fam_name: (fam["n_passes"] if fam is not None else 0)
                    for fam_name, fam in blocks.items()
                }
                for m, blocks in mission_blocks.items()
            },
            "n_crossings": {
                m: {
                    fam_name: (fam["n_crossings"] if fam is not None else 0)
                    for fam_name, fam in blocks.items()
                }
                for m, blocks in mission_blocks.items()
            },
        },
    }
    atomic_write_json(out_path, artifact)
    return _sha256_file(out_path)
