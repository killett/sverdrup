"""ODC THREDDS cache: fetch whole files and OPeNDAP-subset, into ./data/cache/."""

from __future__ import annotations

import hashlib
from pathlib import Path

import httpx
import stamina
import xarray as xr

CACHE = Path("data/cache")


def _is_retryable(exc: Exception) -> bool:
    """Decide whether a download failure is worth retrying.

    Retries only transient faults: transport errors (connect/read timeouts,
    dropped connections) and 5xx server responses. Permanent failures — 4xx
    client errors, disk errors, programming bugs — are surfaced immediately.

    Args:
        exc: The exception raised during a download attempt.

    Returns:
        ``True`` if the failure is transient and should be retried.
    """
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return False


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

    @stamina.retry(on=_is_retryable, attempts=4)
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
