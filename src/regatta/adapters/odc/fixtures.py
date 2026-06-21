"""Offline fixture data-source for deterministic CI (wraps the same interface as ODC)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import dask.array as da
import numpy as np
import xarray as xr

from regatta.core.observations import DiagonalErrorModel, ObsWindow
from regatta.core.types import Field

if TYPE_CHECKING:
    from regatta.core.grid import GridSpec

Range = tuple[float, float]


class FixtureSource:
    """A NetCDF-backed data source matching the ODC ``DataSource``/truth interface."""

    def __init__(
        self, obs_path: str, ref_path: str | None = None, noise: float = 0.01
    ) -> None:
        """Open the observation (and optional reference) datasets.

        Args:
            obs_path: Path to the along-track observation NetCDF.
            ref_path: Optional path to the gridded reference NetCDF (OSSE truth).
            noise: Per-observation error variance for the diagonal error model.
        """
        self._obs = xr.open_dataset(obs_path)
        self._ref = xr.open_dataset(ref_path) if ref_path else None
        self._noise = noise

    def window(
        self, *, lon_range: Range, lat_range: Range, time_range: Range
    ) -> ObsWindow:
        """Return a lazily-backed ``ObsWindow`` over the requested space-time box.

        Args:
            lon_range: Inclusive longitude bounds in degrees.
            lat_range: Inclusive latitude bounds in degrees.
            time_range: Inclusive time bounds in days.

        Returns:
            An ``ObsWindow`` whose values stay dask-lazy until materialised.
        """
        ds = self._obs
        m = (
            (ds.longitude >= lon_range[0])
            & (ds.longitude <= lon_range[1])
            & (ds.latitude >= lat_range[0])
            & (ds.latitude <= lat_range[1])
            & (ds.time >= time_range[0])
            & (ds.time <= time_range[1])
        )
        sub = ds.where(m, drop=True)
        n = int(sub.sizes["t"])
        return ObsWindow.from_arrays(
            sub.longitude.values,
            sub.latitude.values,
            sub.time.values,
            da.from_array(sub.sla.values, chunks=max(1, n // 2)),  # type: ignore[no-untyped-call]
            DiagonalErrorModel(np.full(n, self._noise)),
            mission=sub.mission.values,
        )

    def truth(self, time_days: float, grid: GridSpec) -> Field | None:
        """Return the reference field interpolated to grid nodes, or ``None`` for OSE.

        Args:
            time_days: The output time in days.
            grid: The output grid.

        Returns:
            The ``(ny, nx)`` reference field, or ``None`` when no reference is set.
        """
        if self._ref is None:
            return None
        snap = self._ref.ssh.interp(time=time_days)
        lon, lat = grid._lonlat_nodes()
        vals = snap.interp(
            longitude=("z", lon.ravel()), latitude=("z", lat.ravel())
        ).values
        return np.asarray(vals).reshape(grid.shape)
