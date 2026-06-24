"""Partition-of-unity crossfade blend over a GridSpec or PointSet (design section 4)."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from sverdrup.core.geometry import Tile


def _smootherstep(t: np.ndarray) -> np.ndarray:
    """Quintic 6t^5-15t^4+10t^3, clamped to [0,1]; value & 1st deriv vanish at 0 and 1."""
    t = np.clip(t, 0.0, 1.0)
    return np.asarray(t**3 * (t * (t * 6.0 - 15.0) + 10.0))


def _axis_taper(
    coord: np.ndarray, core: tuple[float, float], ext: tuple[float, float]
) -> np.ndarray:
    """Per-axis raw taper: 1 inside core, smootherstep down to 0 at the extended edge."""
    lo_c, hi_c = core
    lo_e, hi_e = ext
    left_pen = np.where(coord < lo_c, (lo_c - coord) / max(lo_c - lo_e, 1e-12), 0.0)
    right_pen = np.where(coord > hi_c, (coord - hi_c) / max(hi_e - hi_c, 1e-12), 0.0)
    pen = np.clip(left_pen + right_pen, 0.0, 1.0)  # 0 in core, 1 at extended edge
    inside = (coord >= lo_e) & (coord <= hi_e)
    return np.asarray(np.where(inside, 1.0 - _smootherstep(pen), 0.0))


def _raw_weight(tile: Tile, points: np.ndarray) -> np.ndarray:
    """Separable raw taper over lon & lat (product keeps it C1; min would kink at corners)."""
    lon, lat = points[:, 0], points[:, 1]
    tx = _axis_taper(lon, tile.core_window.lon_range, tile.extended_window.lon_range)
    ty = _axis_taper(lat, tile.core_window.lat_range, tile.extended_window.lat_range)
    return np.asarray(tx * ty)


def partition_weights(tiles: Sequence[Tile], points: np.ndarray) -> np.ndarray:
    """Return normalized partition-of-unity weights, shape ``(n_tiles, n_points)``.

    Args:
        tiles: The tiles whose core/halo geometry defines the crossfade.
        points: ``(n, 3)`` support points ``(lon, lat, time)``.

    Returns:
        Weights summing to 1 over tiles wherever at least one tile covers the point.
    """
    raw = np.stack([_raw_weight(t, points) for t in tiles])  # (n_tiles, n)
    total = raw.sum(axis=0)
    safe = np.where(total > 0, total, 1.0)
    return np.asarray(raw / safe)
