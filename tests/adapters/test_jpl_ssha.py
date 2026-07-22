"""JPL SSHA adapter tests (phase-14 Task 6, 0c-4).

CI legs: parsing against a synthetic fixture matching the DOCUMENTED
layout (no private data in the repo) + the read-only governance pin.
The conformance leg is artifact-gated on ``SVERDRUP_JPL_SSHA_DIR`` and
shows SKIPPED in CI — never green-by-vacuity.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from sverdrup.adapters.altimetry import AlongTrackSource, BBox
from sverdrup.adapters.altimetry.jpl_ssha import JPL_DIR_ENV, JplSshaSource
from tests.adapters.test_altimetry_contract import AltimetryConformance

_JPL_DIR = os.environ.get(JPL_DIR_ENV, "")
_JPL_PRESENT = bool(_JPL_DIR) and Path(_JPL_DIR).is_dir()


def _fixture_dir(root: Path) -> Path:
    """A two-mission synthetic tree in the DOCUMENTED layout."""
    for mission, lon0 in (("tp", 100.0), ("j1", 200.0)):
        d = root / mission
        d.mkdir(parents=True, exist_ok=True)
        n = 50
        t0 = np.datetime64("2001-05-01T00:00:00")
        time = t0 + np.arange(n) * np.timedelta64(60, "s")
        ds = xr.Dataset(
            {
                "latitude": ("time", np.linspace(-60.0, 60.0, n)),
                "longitude": ("time", (lon0 + np.linspace(0.0, 20.0, n)) % 360.0),
                "ssha": ("time", np.linspace(-0.2, 0.2, n)),
            },
            coords={"time": time},
        )
        ds.to_netcdf(d / f"{mission}_cycle001.nc")
    return root


def test_parses_documented_layout(tmp_path: Path) -> None:
    """The documented layout parses: missions found, values in meters kept."""
    src = JplSshaSource(_fixture_dir(tmp_path))
    assert set(src.missions()) == {"j1", "tp"}
    obs = src.load(
        BBox(0.0, 360.0, -90.0, 90.0),
        np.datetime64("2001-05-01"),
        np.datetime64("2001-05-02"),
    )
    assert len(obs) == 100
    v = obs.values()
    assert v.min() == pytest.approx(-0.2) and v.max() == pytest.approx(0.2)
    mission = obs.mission
    assert mission is not None
    assert set(np.unique(mission)) == {"j1", "tp"}


def test_manifest_shas_computed_at_ingest(tmp_path: Path) -> None:
    """Per-file sha256 AT INGEST: a byte flip moves the manifest sha."""
    src = JplSshaSource(_fixture_dir(tmp_path))
    before = src.descriptor().manifest_sha()
    target = next((tmp_path / "tp").glob("*.nc"))
    data = bytearray(target.read_bytes())
    data[len(data) // 2] ^= 0xFF
    target.write_bytes(data)
    after = JplSshaSource(tmp_path).descriptor().manifest_sha()
    assert before != after


def test_read_only_no_network_capability() -> None:
    """Data-governance: the adapter is read-only local — its module imports
    no network/upload machinery (httpx, urllib, requests, subprocess)."""
    import sverdrup.adapters.altimetry.jpl_ssha as mod

    source = Path(mod.__file__).read_text()
    for banned in ("httpx", "urllib", "requests", "subprocess", "socket"):
        assert banned not in source, f"network-capable import {banned!r}"
    assert "never leaves owner-controlled hosts" in source


@pytest.mark.skipif(
    not _JPL_PRESENT,
    reason=(
        f"JPL SSHA artifact dir not present: set {JPL_DIR_ENV} to the "
        "local data root to run the conformance leg"
    ),
)
class TestJplConformance(AltimetryConformance):
    """Artifact-gated conformance — SKIPPED in CI, never green-by-vacuity."""

    @pytest.fixture
    def source_factory(self) -> Callable[[], AlongTrackSource]:
        return lambda: JplSshaSource(Path(_JPL_DIR))

    @pytest.fixture
    def query(self) -> tuple[BBox, np.datetime64, np.datetime64]:
        return (
            BBox(0.0, 360.0, -90.0, 90.0),
            np.datetime64("2001-05-01"),
            np.datetime64("2001-05-08"),
        )
