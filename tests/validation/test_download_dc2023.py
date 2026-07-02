"""Tests for the 2023 Ocean Data Challenges downloader."""

import argparse

import pytest

from sverdrup.validation import download_ocean_data_challenges_2023 as dl
from tests.validation._net import skip_if_unreachable


def test_four_challenges_with_wellformed_manifests():
    """All four 2023 challenges are present with well-formed file manifests.

    Catches a dropped challenge, an empty manifest, duplicate relpaths, or a
    malformed SHA256 before any download runs.
    """
    assert set(dl.CHALLENGES) == {"ose", "mapmed", "california", "enatl60"}
    for ch in dl.CHALLENGES.values():
        assert ch.files, ch.key
        relpaths = [f.relpath for f in ch.files]
        assert len(set(relpaths)) == len(relpaths), ch.key  # no duplicates
        assert ch.base_url.startswith("https://"), ch.key
        assert not ch.subdir.startswith("/"), ch.key  # relative subdir
        for f in ch.files:
            assert f.sha256 == "" or (
                len(f.sha256) == 64 and all(c in "0123456789abcdef" for c in f.sha256)
            ), f.relpath


def test_enatl60_uses_wasabi_others_use_meom():
    """eNATL60 comes from Wasabi; the other three from the MEOM mirror.

    Catches a host mix-up that would 404 every file in a challenge.
    """
    assert "wasabisys.com" in dl.CHALLENGES["enatl60"].base_url
    for key in ("ose", "mapmed", "california"):
        assert "meomopendap" in dl.CHALLENGES[key].base_url


def _ns(**flags):
    base = dict(all=False, ose=False, mapmed=False, california=False, enatl60=False)
    base.update(flags)
    return argparse.Namespace(**base)


def test_all_flag_selects_every_challenge():
    """--all selects all four challenges; a single flag selects exactly one.

    Catches a selector-resolution bug that would silently download the wrong set.
    """
    assert len(dl._select(_ns(all=True))) == 4
    sel = dl._select(_ns(california=True))
    assert [c.key for c in sel] == ["california"]
    assert dl._select(_ns()) == []  # nothing selected


def test_default_data_root_is_relative():
    """The default data-root is relative (not tied to /workspace).

    Catches a hard-coded absolute path that would break reproduction elsewhere.
    """
    assert not dl.DEFAULT_DATA_ROOT.is_absolute()


@pytest.mark.external
def test_mapmed_downloads_and_verifies(tmp_path):
    """The tiny MapMed challenge really downloads + size/SHA256-verifies.

    End-to-end proof of the download+verify path on a real (~5 MB) challenge,
    without the ~80 GB of the others. Extract flags are NOT exercised.
    Skips (not fails) when offline.
    """
    ch = dl.CHALLENGES["mapmed"]
    skip_if_unreachable(ch.base_url)
    results = dl.run([ch], tmp_path, extract=False, extract_existing=False)
    assert set(results.values()) <= {"downloaded", "skipped"}
    for entry in ch.files:
        got = tmp_path / ch.subdir / entry.relpath
        assert got.exists() and got.stat().st_size > 0, entry.relpath
