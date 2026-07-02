"""Offline guard for ``@external`` download tests: skip (not fail) when the remote is unreachable.

The ``external`` marker's contract is "skipped offline" (pyproject.toml). The download tests
re-fetch from a live mirror, so offline they must SKIP rather than hang to an ``httpx.ConnectTimeout``.
A short-timeout HEAD distinguishes offline (transport-level failure) from a reachable host returning
any HTTP status — the latter still proves connectivity and lets the real download run and be verified.
"""

from __future__ import annotations

import httpx
import pytest


def skip_if_unreachable(url: str, timeout: float = 5.0) -> None:
    """``pytest.skip`` when a quick connect to ``url`` fails at the transport level (offline)."""
    try:
        httpx.head(url, timeout=timeout, follow_redirects=True)
    except httpx.TransportError as exc:  # connect/read/DNS/timeout — treat as offline
        pytest.skip(f"offline: {url} unreachable ({type(exc).__name__})")
