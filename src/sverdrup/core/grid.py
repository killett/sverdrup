"""CRS-aware, purely spatial grid specification (invariants 1, 3; spec section 5.5)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pyproj

from sverdrup.core.types import Field, Points

R_EARTH = 6_371_000.0


@dataclass(frozen=True)
class GridSpec:
    """A 2-D grid of node coordinates with a CRS. Time is NOT carried here.

    Attributes:
        x: 1-D node coordinates along the first axis (lon degrees, or projected metres).
        y: 1-D node coordinates along the second axis (lat degrees, or projected metres).
        crs: The coordinate reference system.
    """

    x: np.ndarray
    y: np.ndarray
    crs: pyproj.CRS

    @classmethod
    def lonlat(cls, lons: np.ndarray, lats: np.ndarray) -> GridSpec:
        """Build a geographic lon/lat grid (default regional tile).

        Args:
            lons: 1-D longitudes in degrees.
            lats: 1-D latitudes in degrees.

        Returns:
            A geographic ``GridSpec`` in EPSG:4326.
        """
        return cls(
            np.asarray(lons, float), np.asarray(lats, float), pyproj.CRS.from_epsg(4326)
        )

    @classmethod
    def polar_stereographic(
        cls, x: np.ndarray, y: np.ndarray, *, lat_ts: float, lon0: float
    ) -> GridSpec:
        """Build a polar-stereographic grid (projected metres).

        Args:
            x: 1-D projected x coordinates in metres.
            y: 1-D projected y coordinates in metres.
            lat_ts: Latitude of true scale in degrees.
            lon0: Central longitude in degrees.

        Returns:
            A projected ``GridSpec`` in a polar-stereographic CRS.
        """
        crs = pyproj.CRS.from_proj4(
            f"+proj=stere +lat_0=90 +lat_ts={lat_ts} +lon_0={lon0} +R={R_EARTH}"
        )
        return cls(np.asarray(x, float), np.asarray(y, float), crs)

    @property
    def shape(self) -> tuple[int, int]:
        """Return the grid shape ``(ny, nx)``."""
        return (self.y.size, self.x.size)

    def _lonlat_nodes(self) -> tuple[np.ndarray, np.ndarray]:
        """Return ``(lon2d, lat2d)`` of node centres, shape ``(ny, nx)``."""
        xx, yy = np.meshgrid(self.x, self.y)  # (ny, nx)
        if self.crs.is_geographic:
            return xx, yy
        transformer = pyproj.Transformer.from_crs(
            self.crs, pyproj.CRS.from_epsg(4326), always_xy=True
        )
        lon, lat = transformer.transform(xx, yy)
        return lon, lat

    def points(self, time_days: float) -> Points:
        """Flattened ``(ny*nx, 3)`` space-time points ``(lon, lat, time)`` at one output time.

        Args:
            time_days: The output time in days, broadcast to every node.

        Returns:
            A ``(ny*nx, 3)`` array of ``(lon_deg, lat_deg, time_days)`` rows.
        """
        lon, lat = self._lonlat_nodes()
        n = lon.size
        out = np.empty((n, 3), float)
        out[:, 0] = lon.ravel()
        out[:, 1] = lat.ravel()
        out[:, 2] = time_days
        return out

    def cell_area(self) -> Field:
        """True spherical cell area (m^2), shape ``(ny, nx)``.

        Geographic grids use the spherical-cap band area * longitude fraction
        (shrinks as cos(lat)); projected grids use the planar cell area scaled
        by the local CRS distortion via node spacing in metres.

        Returns:
            A ``(ny, nx)`` array of positive cell areas in square metres.
        """
        if self.crs.is_geographic:
            lat = np.deg2rad(self.y)
            dlat = _edge_widths(lat)
            dlon = np.deg2rad(_edge_widths(self.x))
            band = R_EARTH**2 * np.cos(lat) * dlat  # per unit radian lon, shape (ny,)
            area = np.outer(band, dlon)  # (ny, nx)
            return area
        dx = _edge_widths(self.x)
        dy = _edge_widths(self.y)
        return np.outer(dy, dx)

    def window(
        self, *, lon_range: tuple[float, float], lat_range: tuple[float, float]
    ) -> GridSpec:
        """Return the sub-grid whose nodes fall inside the lon/lat box (same CRS/type).

        Args:
            lon_range: Inclusive ``(min, max)`` longitude bounds in degrees.
            lat_range: Inclusive ``(min, max)`` latitude bounds in degrees.

        Returns:
            A ``GridSpec`` of the same CRS containing the subset of nodes inside the box.
        """
        lon, lat = self._lonlat_nodes()
        col_mask = (lon[0, :] >= lon_range[0]) & (lon[0, :] <= lon_range[1])
        row_mask = (lat[:, 0] >= lat_range[0]) & (lat[:, 0] <= lat_range[1])
        return GridSpec(self.x[col_mask], self.y[row_mask], self.crs)


def _edge_widths(centers: np.ndarray) -> np.ndarray:
    """Per-node spacing from midpoints between neighbouring node centres.

    Args:
        centers: 1-D monotonic node-centre coordinates.

    Returns:
        A 1-D array of positive per-node widths, same length as ``centers``.
    """
    edges = np.empty(centers.size + 1)
    edges[1:-1] = 0.5 * (centers[:-1] + centers[1:])
    edges[0] = centers[0] - 0.5 * (centers[1] - centers[0])
    edges[-1] = centers[-1] + 0.5 * (centers[-1] - centers[-2])
    return np.abs(np.diff(edges))
