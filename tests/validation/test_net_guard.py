"""The offline guard's two halves: the probe, and the transfer that follows it.

The probe half (``skip_if_unreachable``) was already here. The transfer half
(``network_guard``) is owner-filed work from 2026-09-14: a host that ANSWERS
the probe and then times out mid-download failed the suite instead of
skipping, and under pins 83/131 a red suite blocks every commit whose
evidence is cited. Observed twice on the same day against the MEOM mirror,
``httpx.ReadTimeout`` after the HEAD had already succeeded.
"""

from __future__ import annotations

import httpx
import pytest

from tests.validation._net import network_guard, skip_if_unreachable


def test_a_mid_transfer_timeout_SKIPS_rather_than_failing() -> None:
    """The live one: the probe passes, then the transfer times out.

    Bug caught: `skip_if_unreachable` guards the HEAD and nothing else,
    so a reachable-but-slow mirror raised httpx.ReadTimeout out of the
    download itself and the suite went red on a network condition the
    `external` marker already promises to skip on.
    """
    with pytest.raises(pytest.skip.Exception) as excinfo:
        with network_guard("https://example.invalid/dc2023"):
            raise httpx.ReadTimeout("The read operation timed out")

    message = str(excinfo.value)
    assert "offline" in message
    assert "https://example.invalid/dc2023" in message
    assert "ReadTimeout" in message


def test_the_guard_does_NOT_swallow_a_verification_failure() -> None:
    """Only transport errors become skips. Everything else propagates.

    Bug caught: the guard turning a real sha256 or size mismatch — the
    whole point of the download tests — into a green skip. That failure
    mode is strictly worse than the one the guard fixes, because a red
    suite is visible and a false skip is not.
    """
    with pytest.raises(AssertionError, match="sha256 mismatch"):
        with network_guard("https://example.invalid/dc2023"):
            raise AssertionError("sha256 mismatch")


def test_an_HTTP_STATUS_error_is_NOT_offline() -> None:
    """A server that answers with 404/500 is reachable; that is a failure.

    Bug caught: widening the guard to every httpx exception, so a moved
    or broken artifact on a healthy mirror reads as "offline" and the
    download path silently stops being tested.
    """
    request = httpx.Request("GET", "https://example.invalid/dc2023")
    response = httpx.Response(500, request=request)

    with pytest.raises(httpx.HTTPStatusError):
        with network_guard("https://example.invalid/dc2023"):
            raise httpx.HTTPStatusError(
                "server error", request=request, response=response
            )


def test_the_guard_is_transparent_when_nothing_goes_wrong() -> None:
    """A successful transfer passes through untouched.

    Bug caught: a guard that skips unconditionally (or swallows the
    block's result) would make every external test green-by-skip and
    nobody would notice, because a skip is not a failure.
    """
    ran = []
    with network_guard("https://example.invalid/dc2023"):
        ran.append("downloaded")

    assert ran == ["downloaded"]


def test_the_probe_half_still_skips_on_a_transport_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression pin on the original guard while its module changes.

    Bug caught: refactoring `_net.py` to add the transfer half and
    breaking the probe half — offline would then HANG the download to
    its own timeout instead of skipping, which is what the probe exists
    to prevent.
    """

    def _boom(*_args: object, **_kwargs: object) -> httpx.Response:
        raise httpx.ConnectError("nope")

    monkeypatch.setattr(httpx, "head", _boom)

    with pytest.raises(pytest.skip.Exception) as excinfo:
        skip_if_unreachable("https://example.invalid/dc2023")

    assert "ConnectError" in str(excinfo.value)
