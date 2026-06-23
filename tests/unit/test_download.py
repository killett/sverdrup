"""Tests for the ODC download retry policy."""

from __future__ import annotations

import httpx
import pytest

from sverdrup.adapters.odc.download import _is_retryable


def _status_error(code: int) -> httpx.HTTPStatusError:
    """Build a real ``HTTPStatusError`` carrying ``code`` for the predicate.

    Args:
        code: The HTTP status code the response should report.

    Returns:
        An ``HTTPStatusError`` whose ``response.status_code`` is ``code``.
    """
    request = httpx.Request("GET", "https://example.invalid/data.nc")
    response = httpx.Response(code, request=request)
    return httpx.HTTPStatusError(f"HTTP {code}", request=request, response=response)


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        # Transport faults are transient -> retry. Two distinct subclasses
        # prove the predicate matches the TransportError base, not one leaf.
        (httpx.ConnectError("connection refused"), True),
        (httpx.ReadTimeout("read timed out"), True),
        # 5xx is a transient server fault. 500 is the inclusive boundary.
        (_status_error(500), True),
        (_status_error(503), True),
        # 4xx is a permanent client error -> retrying cannot help.
        (_status_error(404), False),
        (_status_error(400), False),
        # Non-HTTP failures must surface, never be retried.
        (OSError("disk full"), False),
        (ValueError("logic bug"), False),
    ],
)
def test_is_retryable_classifies_only_transient_faults(
    exc: Exception, expected: bool
) -> None:
    """Only transport errors and 5xx statuses are retryable; all else is not."""
    assert _is_retryable(exc) is expected
