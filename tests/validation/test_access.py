"""Tests for the challenge data-access adapter (offline: retry + auth rendering)."""

import httpx

from sverdrup.validation.access import is_retryable, render_netrc


def test_is_retryable_5xx_and_transport_only():
    """Retry 5xx + transport errors; never retry a 401/404.

    Catches a predicate that would hammer an auth failure or hide a 404.
    """
    req = httpx.Request("GET", "https://x")
    assert is_retryable(
        httpx.HTTPStatusError(
            "x", request=req, response=httpx.Response(503, request=req)
        )
    )
    assert is_retryable(httpx.ConnectError("boom"))
    assert not is_retryable(
        httpx.HTTPStatusError(
            "x", request=req, response=httpx.Response(401, request=req)
        )
    )
    assert not is_retryable(
        httpx.HTTPStatusError(
            "x", request=req, response=httpx.Response(404, request=req)
        )
    )


def test_is_retryable_ignores_unrelated_exceptions():
    """A plain ValueError is not a transient transport fault.

    Catches an over-broad predicate that retries non-network bugs.
    """
    assert not is_retryable(ValueError("not a network error"))


def test_render_netrc_contains_host_and_creds():
    """.netrc rendering includes machine + login + password lines.

    Catches a malformed .netrc that the netCDF-C OPeNDAP stack silently ignores.
    """
    text = render_netrc("tds.aviso.altimetry.fr", "user", "secret")
    assert "machine tds.aviso.altimetry.fr" in text
    assert "login user" in text
    assert "password secret" in text
