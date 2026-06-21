"""OSSE NATL60 source: nadir obs (whole) + daily CJM165 reference clipped to the eval window."""

from __future__ import annotations

from regatta.adapters.odc.download import ODCCache
from regatta.adapters.odc.fixtures import FixtureSource

WINDOW = ("2012-10-22", "2012-12-02")  # 42-day eval window
OBS_URL = (
    "https://tds.../2020a_SSH_mapping_NATL60/dc_obs/...tar.gz"  # documented endpoint
)
REF_DAILY_URL = "https://tds.../NATL60-CJM165/...daily...nc"


class Natl60Source(FixtureSource):
    """Phase-1 OSSE source. Until cached data is present, behaves as a FixtureSource."""

    def __init__(
        self, obs_path: str, ref_path: str, cache: ODCCache | None = None
    ) -> None:
        """Open the OSSE obs + daily reference (delegating to the fixture interface).

        Args:
            obs_path: Path to the nadir observation dataset.
            ref_path: Path to the clipped daily reference dataset.
            cache: Optional ODC cache (created on demand if omitted).
        """
        super().__init__(obs_path, ref_path)
        self.cache = cache or ODCCache()
