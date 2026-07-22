"""dc2021a adapter tests (phase-14 Task 2): conformance + c2 exclusion + shas.

Data-gated: the conformance and file-backed legs skip when the challenge
obs directory is absent (CI shows SKIPPED with the path named; the gate-2
identity suite lives in ``tests/test_phase14_gate2_loader_identity.py``).
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest

from sverdrup.adapters.altimetry import AlongTrackSource, BBox
from sverdrup.adapters.altimetry.dc2021a import DC_OBS_DIR, Dc2021aSource
from tests.adapters.test_altimetry_contract import AltimetryConformance

_DATA_PRESENT = DC_OBS_DIR.is_dir() and any(DC_OBS_DIR.glob("*.nc"))

pytestmark = pytest.mark.skipif(
    not _DATA_PRESENT,
    reason=f"challenge obs directory {DC_OBS_DIR} absent on this host",
)


class TestDc2021aConformance(AltimetryConformance):
    """The dc2021a wrapper is a REAL adapter: full conformance on local data."""

    @pytest.fixture
    def source_factory(self) -> Callable[[], AlongTrackSource]:
        return Dc2021aSource

    @pytest.fixture
    def query(self) -> tuple[BBox, np.datetime64, np.datetime64]:
        return (
            BBox(lon_min=285.0, lon_max=315.0, lat_min=23.0, lat_max=53.0),
            np.datetime64("2017-01-05"),
            np.datetime64("2017-01-09"),
        )


def test_c2_never_loadable_and_not_in_manifest() -> None:
    """The withheld c2 mission is structurally absent from this source."""
    src = Dc2021aSource()
    assert "c2" not in src.missions()
    assert not any("_c2_" in rel for rel, _ in src.descriptor().content_manifest)
    with pytest.raises(ValueError, match="c2"):
        src.load(
            BBox(0.0, 360.0, -90.0, 90.0),
            np.datetime64("2017-01-01"),
            np.datetime64("2017-01-02"),
            missions=["c2"],
        )


def test_manifest_tracks_actual_file_bytes(tmp_path: Path) -> None:
    """Flipping ONE byte of one file moves the manifest sha (no cached shas).

    Two tmp source dirs: hardlinks of the real files, and the same with the
    smallest file byte-flipped. A wrapper that hardcodes or caches shas
    instead of hashing the bytes it serves passes everything else but fails
    here.
    """
    src_paths = sorted(p for p in DC_OBS_DIR.glob("*.nc") if "_c2_" not in p.name)
    smallest = min(src_paths, key=lambda p: p.stat().st_size)
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    dir_a.mkdir()
    dir_b.mkdir()

    def link_or_copy(src: Path, dst: Path) -> None:
        try:
            os.link(src, dst)
        except OSError:  # tmp on another filesystem — fall back to a copy
            shutil.copyfile(src, dst)

    for p in src_paths:
        link_or_copy(p, dir_a / p.name)
        if p == smallest:
            shutil.copyfile(p, dir_b / p.name)
        else:
            link_or_copy(p, dir_b / p.name)
    mutated = dir_b / smallest.name
    data = bytearray(mutated.read_bytes())
    data[len(data) // 2] ^= 0xFF
    mutated.write_bytes(data)

    desc_real = Dc2021aSource().descriptor()
    desc_a = Dc2021aSource(obs_dir=dir_a).descriptor()
    desc_b = Dc2021aSource(obs_dir=dir_b).descriptor()
    assert desc_a.manifest_sha() == desc_real.manifest_sha()
    assert desc_b.manifest_sha() != desc_a.manifest_sha()
