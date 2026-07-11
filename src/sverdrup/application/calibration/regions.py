"""Phase-8 pre-registered region machinery (spec §6).

Provides:
  - cell_index: 2°-cell grid assignment (moved from diag_phase8_covariate_alignment.py)
  - quadrant_of: point → {SW, SE, NW, NE} using the shipped >= convention
  - evaluation_masks: 6 evaluation classes (4 quadrants + jet_core + aggregate)
  - fit_partition: true partition into 5 labels (quadrants-minus-jet + JET)
  - largest_4connected_component: deterministic largest-component filter
  - proxy_cells: per-cell mean of per-node temporal std of the Stage-B mean maps

Grid: lon edges 295,297,...,305; lat edges 33,35,...,43 → 5×5 = 25 cells.
Quadrant split: lon_mid=300, lat_mid=38; lon>=300 → East; lat>=38 → North.
This mirrors diag_stage_b_localized_calibration.py lines 62-65 exactly.
"""

from __future__ import annotations

import numpy as np
import scipy.ndimage  # type: ignore[import-untyped]
import xarray as xr

from sverdrup.application.calibration.constants import CELL_DEG

# ---------------------------------------------------------------------------
# Grid constants
# ---------------------------------------------------------------------------

LON_MIN = 295.0
LON_MAX = 305.0
LAT_MIN = 33.0
LAT_MAX = 43.0
LON_MID = 300.0
LAT_MID = 38.0

_LON_EDGES: np.ndarray = np.arange(LON_MIN, LON_MAX + CELL_DEG, CELL_DEG)
_LAT_EDGES: np.ndarray = np.arange(LAT_MIN, LAT_MAX + CELL_DEG, CELL_DEG)

# 4-connectivity structure (cross, not full 3×3)
_CROSS = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=int)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def cell_index(lon: np.ndarray, lat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (row, col) 2°-cell indices, clipped to the 5×5 grid.

    Uses searchsorted with side='right' so that a point exactly on an interior
    edge is assigned to the higher-index cell. Points at the upper domain
    boundary (lon=305, lat=43) are clipped into the last valid cell (index 4).

    Args:
        lon: Longitudes [deg east].
        lat: Latitudes [deg north].

    Returns:
        Tuple of (row, col) integer arrays, each clipped to [0, 4].
    """
    lon_arr = np.asarray(lon)
    lat_arr = np.asarray(lat)
    col = np.clip(np.searchsorted(_LON_EDGES, lon_arr, side="right") - 1, 0, 4)
    row = np.clip(np.searchsorted(_LAT_EDGES, lat_arr, side="right") - 1, 0, 4)
    return row, col


def quadrant_of(lon: float, lat: float) -> str:
    """Return the quadrant label for a single (lon, lat) point.

    Convention (mirrors diag_stage_b_localized_calibration.py lines 62-65):
      - lon >= LON_MID (300) → East; lon < LON_MID → West
      - lat >= LAT_MID (38)  → North; lat < LAT_MID → South

    Args:
        lon: Longitude [deg east].
        lat: Latitude [deg north].

    Returns:
        One of 'SW', 'SE', 'NW', 'NE'.
    """
    ns = "N" if lat >= LAT_MID else "S"
    ew = "E" if lon >= LON_MID else "W"
    return ns + ew


def evaluation_masks(
    lon: np.ndarray,
    lat: np.ndarray,
    jet_mask: np.ndarray,
) -> dict[str, np.ndarray]:
    """Return the 6 pre-registered evaluation class masks.

    Evaluation classes are NOT disjoint: jet_core overlaps the four quadrant
    masks. Each quadrant contains ALL points in that geographic region,
    regardless of jet_core membership. The aggregate is the union of the
    four quadrant masks. Points are assumed in-domain (no clip, unlike
    cell_index).

    Args:
        lon: Point longitudes [deg east], shape (N,).
        lat: Point latitudes [deg north], shape (N,).
        jet_mask: Boolean array shape (N,) marking jet-core points.

    Returns:
        Dict with keys: 'SW', 'SE', 'NW', 'NE', 'jet_core', 'aggregate'.
        Each value is a boolean array of shape (N,).
    """
    lon_arr = np.asarray(lon, dtype=float)
    lat_arr = np.asarray(lat, dtype=float)
    jet = np.asarray(jet_mask, dtype=bool)

    east = lon_arr >= LON_MID
    north = lat_arr >= LAT_MID

    sw = (~east) & (~north)
    se = east & (~north)
    nw = (~east) & north
    ne = east & north

    return {
        "SW": sw,
        "SE": se,
        "NW": nw,
        "NE": ne,
        "jet_core": jet,
        "aggregate": sw | se | nw | ne,
    }


def fit_partition(
    lon: np.ndarray,
    lat: np.ndarray,
    jet_mask: np.ndarray,
) -> np.ndarray:
    """Return a true partition label array over the 5 fit lanes.

    Fit lanes: SW, SE, NW, NE (each minus jet-core cells) and JET. Every
    point gets exactly one label. Jet-core points are labeled JET regardless
    of their geographic quadrant. Points are assumed in-domain (no clip,
    unlike cell_index).

    Args:
        lon: Point longitudes [deg east], shape (N,).
        lat: Point latitudes [deg north], shape (N,).
        jet_mask: Boolean array shape (N,) marking jet-core points.

    Returns:
        String array of shape (N,) with values in {'SW','SE','NW','NE','JET'}.

    Raises:
        RuntimeError: If the partition invariant is violated (should never
            happen with well-formed inputs).
    """
    lon_arr = np.asarray(lon, dtype=float)
    lat_arr = np.asarray(lat, dtype=float)
    jet = np.asarray(jet_mask, dtype=bool)

    east = lon_arr >= LON_MID
    north = lat_arr >= LAT_MID
    non_jet = ~jet

    labels = np.empty(len(lon_arr), dtype=object)
    labels[jet] = "JET"
    labels[non_jet & (~east) & (~north)] = "SW"
    labels[non_jet & east & (~north)] = "SE"
    labels[non_jet & (~east) & north] = "NW"
    labels[non_jet & east & north] = "NE"

    # Partition invariant: every point must have a label
    if np.any(labels == None):  # noqa: E711
        raise RuntimeError("fit_partition: unlabeled points found")

    return labels.astype(str)


def largest_4connected_component(mask: np.ndarray) -> np.ndarray:
    """Return the largest 4-connected component of a 2-D boolean mask.

    Uses scipy.ndimage.label with a cross-shaped structure (4-connectivity
    only; diagonal adjacency does NOT connect). For equal-size components,
    the lowest label index (first found) is returned — deterministic tie-break.

    Args:
        mask: Boolean array of shape (5, 5).

    Returns:
        Boolean array of shape (5, 5) with only the largest component True.
    """
    labeled, n_labels = scipy.ndimage.label(mask, structure=_CROSS)
    if n_labels == 0:
        return np.zeros_like(mask, dtype=bool)

    # Count cells per label (labels are 1..n_labels)
    sizes = np.bincount(labeled.ravel())[1:]  # index 0 = background
    # Deterministic tie-break: np.argmax returns the lowest index on ties
    best_label = int(np.argmax(sizes)) + 1  # +1 because labels are 1-based
    result: np.ndarray = labeled == best_label
    return result


def proxy_cells(mean_ds: xr.Dataset) -> np.ndarray:
    """Return (5,5) per-cell mean of the per-node temporal std of the mean maps.

    Shared proxy rule for the Phase-8 covariate alignment diagnostic and the
    jet-core mask build — both must use this single definition so they stay
    bit-identical.

    Args:
        mean_ds: Dataset loaded from stage_b_mean_maps.nc, with ``ssh``
            variable of shape (time, lat, lon).

    Returns:
        Array of shape (5, 5) with per-cell mean temporal std [m].
    """
    std_map = mean_ds["ssh"].std(dim="time")  # (lat, lon) — spatial artifact
    out = np.full((5, 5), np.nan)
    lon2d, lat2d = np.meshgrid(std_map["lon"].values, std_map["lat"].values)
    row, col = cell_index(lon2d.ravel(), lat2d.ravel())
    vals = std_map.values.ravel()
    for r in range(5):
        for c in range(5):
            m = (row == r) & (col == c)
            out[r, c] = float(np.nanmean(vals[m]))
    return out
