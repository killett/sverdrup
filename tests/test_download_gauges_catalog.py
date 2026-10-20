"""Hygiene: the UHSLC roster pull cannot report "done" on a failed catalog.

``download_gauges stations-all`` fetched the catalog page with a bare
``httpx.get(...).text`` — no ``raise_for_status``, no retry. A 5xx error
page parsed to ZERO file names, the loop did nothing, and the command
printed "stations-all done: 0 new". The network is stubbed; stamina's
testing mode removes retry sleeps.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
import stamina

from tests.helpers import load_script


@pytest.fixture(autouse=True)
def _no_retry_sleep() -> Iterator[None]:
    with stamina.set_testing(True, attempts=2):
        yield


def _stub_get(monkeypatch: pytest.MonkeyPatch, status: int, text: str) -> list[str]:
    calls: list[str] = []

    def _get(url: str, **_k: Any) -> httpx.Response:  # noqa: ANN401
        calls.append(url)
        return httpx.Response(status, text=text, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", _get)
    return calls


def test_a_server_error_on_the_catalog_raises_and_is_retried(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bug caught: a 503 catalog page treated as an empty roster ("done")."""
    dl = load_script("download_gauges")
    monkeypatch.setattr(dl, "DATA_DIR", tmp_path)
    monkeypatch.setattr(dl, "MANIFEST", tmp_path / "manifest.json")
    calls = _stub_get(monkeypatch, 503, "Service Unavailable")
    with pytest.raises(httpx.HTTPStatusError):
        dl.stations_all()
    assert len(calls) == 2  # a transient 5xx is retried (testing attempts=2)


def test_a_catalog_listing_no_files_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bug caught: a 200 page with no hNNN.nc links (a moved or reworded
    listing) reported as a successful pull of nothing."""
    dl = load_script("download_gauges")
    monkeypatch.setattr(dl, "DATA_DIR", tmp_path)
    monkeypatch.setattr(dl, "MANIFEST", tmp_path / "manifest.json")
    _stub_get(monkeypatch, 200, "<html>maintenance</html>")
    with pytest.raises(RuntimeError, match="no rqds hourly files"):
        dl.stations_all()


def test_a_bulk_rerun_skip_is_an_existence_check_and_says_so(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """stations-all skips present + manifested files WITHOUT re-hashing, and
    its report does not call them verified.

    Fixture: h001.nc is on disk with bytes that do NOT match its manifest
    sha. Bug caught: "verified-skipped" printed for a file nothing verified
    (only the single-file ``_get`` path re-hashes before skipping).
    """
    dl = load_script("download_gauges")
    monkeypatch.setattr(dl, "DATA_DIR", tmp_path)
    monkeypatch.setattr(dl, "MANIFEST", tmp_path / "manifest.json")
    monkeypatch.setattr(dl, "EVIDENCE", tmp_path / "absent.json")
    (tmp_path / "uhslc").mkdir()
    (tmp_path / "uhslc" / "h001.nc").write_bytes(b"corrupt")
    (tmp_path / "manifest.json").write_text('{"uhslc/h001.nc": "' + "0" * 64 + '"}')
    _stub_get(monkeypatch, 200, '<a href="h001.nc">h001.nc</a>')

    def _no_fetch(*_a: Any) -> None:
        raise AssertionError("a present + manifested file was re-fetched")

    monkeypatch.setattr(dl, "_fetch", _no_fetch)
    dl.stations_all()
    out = capsys.readouterr().out
    assert "verified" not in out
    assert "1 skipped (present + manifested, not re-hashed)" in out
