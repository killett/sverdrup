"""Offline guard for ``@external`` download tests: skip (not fail) when the remote is unreachable.

The ``external`` marker's contract is "skipped offline" (pyproject.toml). The download tests
re-fetch from a live mirror, so offline they must SKIP rather than hang to an ``httpx.ConnectTimeout``.
A short-timeout HEAD distinguishes offline (transport-level failure) from a reachable host returning
any HTTP status — the latter still proves connectivity and lets the real download run and be verified.

⚠ THE PROBE IS NOT THE WHOLE STORY (owner-filed 2026-09-14). ``skip_if_unreachable`` guards the
HEAD and nothing after it, so a mirror that ANSWERS the probe and then stalls mid-transfer raised
``httpx.ReadTimeout`` out of the download itself and the suite went RED — on exactly the network
condition the marker already promises to skip on, and under pins 83/131 a red suite blocks every
commit whose evidence is cited. Observed twice on 2026-09-14 against the MEOM mirror. Wrap the
transfer in :func:`network_guard` so both halves obey one contract.

The line the guard holds: **transport failures are the network, HTTP statuses and assertion
failures are the subject.** A 404 or a 500 means the host answered, so it is a real failure and
must stay one; a sha256 or size mismatch is what these tests exist to catch and must never be
converted into a skip. A false skip is worse than a red suite because a red suite is visible.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import httpx
import pytest


def skip_if_unreachable(url: str, timeout: float = 5.0) -> None:
    """``pytest.skip`` when a quick connect to ``url`` fails at the transport level (offline)."""
    try:
        httpx.head(url, timeout=timeout, follow_redirects=True)
    except httpx.TransportError as exc:  # connect/read/DNS/timeout — treat as offline
        pytest.skip(f"offline: {url} unreachable ({type(exc).__name__})")


@contextmanager
def network_guard(url: str) -> Iterator[None]:
    """``pytest.skip`` when the TRANSFER fails at the transport level, not just the probe.

    Args:
        url: The remote the wrapped block fetches from — named in the skip
            message so a skipped run says which mirror stalled.

    Yields:
        None. The wrapped block runs unchanged.

    Raises:
        Skipped: The block raised an ``httpx.TransportError`` — a
            connect/read/write timeout or a transport-level read error.
            Same contract as :func:`skip_if_unreachable`, applied to the
            download rather than to the HEAD that precedes it.
    """
    try:
        yield
    except httpx.TransportError as exc:  # mid-transfer: the network, not the subject
        pytest.skip(f"offline: {url} transfer failed ({type(exc).__name__})")
