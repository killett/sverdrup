"""ODC THREDDS cache: fetch whole files and OPeNDAP-subset, into ./data/cache/."""

from __future__ import annotations

import hashlib
from pathlib import Path

import httpx
import xarray as xr
from tenacity import retry, stop_after_attempt, wait_exponential

CACHE = Path("data/cache")


class ODCCache:
    """A local content cache for ODC THREDDS files under ``./data/cache/``."""

    def __init__(self, root: Path = CACHE) -> None:
        """Create the cache root if needed.

        Args:
            root: The cache directory.
        """
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, url: str) -> Path:
        """Return the deterministic cache path for ``url``."""
        h = hashlib.blake2b(url.encode(), digest_size=8).hexdigest()
        return self.root / f"{h}_{url.rsplit('/', 1)[-1]}"

    @retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, max=30))
    def fetch_file(self, url: str) -> Path:
        """Download ``url`` to the cache (skipped if already present).

        Args:
            url: The file URL.

        Returns:
            The local cache path.
        """
        dest = self.path_for(url)
        if dest.exists():
            return dest
        with httpx.stream("GET", url, timeout=120, follow_redirects=True) as r:
            r.raise_for_status()
            tmp = dest.with_suffix(".part")
            with tmp.open("wb") as f:
                for chunk in r.iter_bytes(1 << 20):
                    f.write(chunk)
            tmp.replace(dest)
        return dest

    def open_dodsC(self, opendap_url: str) -> xr.Dataset:
        """Open an OPeNDAP dataset lazily (no full download)."""
        return xr.open_dataset(opendap_url)
