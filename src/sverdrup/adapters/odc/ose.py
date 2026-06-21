"""OSE source: real along-track inputs; withheld CryoSat-2 as the independent eval signal."""

from __future__ import annotations

import numpy as np

from sverdrup.adapters.odc.fixtures import FixtureSource


class OseSource(FixtureSource):
    """Phase-1 OSE source. Truth is absent; CryoSat-2 is withheld for evaluation."""

    def __init__(self, obs_path: str) -> None:
        """Open the OSE along-track inputs (no reference truth).

        Args:
            obs_path: Path to the along-track observation dataset.
        """
        super().__init__(obs_path, ref_path=None)

    def withheld(self) -> tuple[np.ndarray, np.ndarray]:
        """Return the withheld CryoSat-2 along-track as ``(locations, values)``.

        Returns:
            A ``((k, 3), (k,))`` tuple of ``(lon, lat, time)`` locations and SLA values.
        """
        c2 = self._obs.where(self._obs.mission == "c2", drop=True)
        locs = np.column_stack(
            [c2.longitude.values, c2.latitude.values, c2.time.values]
        )
        return locs, np.asarray(c2.sla.values)
