"""Tests for the SSH Mapping Data Challenge 2021a download reproducer."""

from pathlib import Path

import pytest

from sverdrup.validation import download_ssh_mapping_data_challenge_2021a as dl
from tests.validation._net import skip_if_unreachable

_EXISTING = Path("data/2021a_ssh_mapping_ose")


def test_manifest_shape_is_seven_obs_seven_maps():
    """The manifest is exactly the 14 MEOM files, well-formed.

    Catches a malformed/duplicated manifest entry or a dropped file before any
    download runs (e.g. the withheld c2 track silently going missing).
    """
    assert len(dl.MANIFEST) == 14
    obs = [e for e in dl.MANIFEST if e.subdir == "dc_obs"]
    maps = [e for e in dl.MANIFEST if e.subdir == "dc_maps"]
    assert len(obs) == 7 and len(maps) == 7
    names = [e.name for e in dl.MANIFEST]
    assert len(set(names)) == 14  # no duplicates
    assert any("_c2_" in n for n in names)  # withheld eval track is included
    for e in dl.MANIFEST:
        assert len(e.sha256) == 64 and all(c in "0123456789abcdef" for c in e.sha256)
        assert e.size > 0


def test_manifest_hashes_match_existing_downloads():
    """Every manifest SHA256/size matches the already-downloaded file.

    Proves the manifest is faithful to what we actually downloaded — without
    any network. Skips on a machine that has not fetched the data yet.
    """
    missing = [e for e in dl.MANIFEST if not (_EXISTING / e.subdir / e.name).exists()]
    if missing:
        pytest.skip(f"challenge data not present under {_EXISTING}; run the downloader")
    for e in dl.MANIFEST:
        path = _EXISTING / e.subdir / e.name
        assert path.stat().st_size == e.size, e.name
        assert dl.sha256_of(path) == e.sha256, e.name


def test_default_data_root_is_relative():
    """The default data-root is relative (not tied to /workspace).

    Catches a hard-coded absolute path that would break reproduction elsewhere.
    """
    assert not dl.DEFAULT_DATA_ROOT.is_absolute()


@pytest.mark.external
def test_download_reproduces_structure_and_contents(tmp_path):
    """A fresh download into a temp dir reproduces the exact tree + contents.

    The end-to-end reproduction guarantee: structure (dc_obs/+dc_maps/, 14 files)
    and byte-exact contents (SHA256) matching both the manifest and the existing
    download. Re-downloads ~1 GB; marked external (on-demand). Skips (not fails) when offline.
    """
    skip_if_unreachable(dl.MEOM_BASE)
    results = dl.download_all(tmp_path)
    assert len(results) == 14
    assert len(list((tmp_path / "dc_obs").glob("*.nc"))) == 7
    assert len(list((tmp_path / "dc_maps").glob("*.nc"))) == 7
    for e in dl.MANIFEST:
        got = tmp_path / e.subdir / e.name
        assert got.exists(), e.name
        assert dl.sha256_of(got) == e.sha256, e.name
        existing = _EXISTING / e.subdir / e.name
        if existing.exists():
            assert dl.sha256_of(got) == dl.sha256_of(existing), e.name
