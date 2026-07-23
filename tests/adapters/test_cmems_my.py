"""CMEMS multi-year adapter tests (phase-14 Task 3, 0c-2).

CI legs: synthetic-netCDF fixture parsing (documented DUACS L3 layout),
census arithmetic on an injected listing (no network), storage-budget WAIT
semantics, locked-c2 exclusion. Conformance runs data-gated on a real
downloaded subset.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from sverdrup.adapters.altimetry import AlongTrackSource, BBox
from sverdrup.adapters.altimetry.cmems_my import (
    CMEMS_DATA_DIR,
    DATASET_VERSION,
    PRODUCT_ID,
    CmemsMySource,
    catalog_from_listing,
)
from tests.adapters.test_altimetry_contract import AltimetryConformance

_SUBSET_PRESENT = CMEMS_DATA_DIR.is_dir() and any(CMEMS_DATA_DIR.rglob("*.nc"))


def _fixture_tree(root: Path) -> Path:
    """Two-mission synthetic tree in the DOCUMENTED native layout."""
    for mission, lon0 in (("alg", 100.0), ("j3", 200.0)):
        d = root / mission
        d.mkdir(parents=True, exist_ok=True)
        for day in ("20170105", "20170106"):
            n = 40
            t0 = np.datetime64(f"{day[:4]}-{day[4:6]}-{day[6:]}T00:00:00")
            time = t0 + np.arange(n) * np.timedelta64(600, "s")
            ds = xr.Dataset(
                {
                    "latitude": ("time", np.linspace(-50.0, 50.0, n)),
                    "longitude": (
                        "time",
                        (lon0 + np.linspace(0.0, 30.0, n)) % 360.0,
                    ),
                    "sla_unfiltered": ("time", np.linspace(-0.3, 0.3, n)),
                },
                coords={"time": time},
            )
            ds.to_netcdf(d / f"dt_global_{mission}_phy_l3_1hz_{day}_20240205.nc")
    (root / "manifest.json").write_text(
        json.dumps(
            {
                f"{m}/dt_global_{m}_phy_l3_1hz_{d}_20240205.nc": "0" * 64
                for m in ("alg", "j3")
                for d in ("20170105", "20170106")
            }
        )
    )
    return root


def test_product_and_version_pins() -> None:
    """The ratified vintage is IN the identity (DT-vintage ruling item 3)."""
    assert PRODUCT_ID == "SEALEVEL_GLO_PHY_L3_MY_008_062"
    assert "202411" in DATASET_VERSION
    assert PRODUCT_ID in DATASET_VERSION


def test_parses_documented_layout(tmp_path: Path) -> None:
    """Fixture files parse: values kept raw, mission-tagged, day-scoped."""
    src = CmemsMySource(_fixture_tree(tmp_path))
    assert set(src.missions()) == {"alg", "j3"}
    obs = src.load(
        BBox(0.0, 360.0, -90.0, 90.0),
        np.datetime64("2017-01-05"),
        np.datetime64("2017-01-06"),
    )
    assert len(obs) == 80  # one day, two missions
    v = obs.values()
    assert v.min() == pytest.approx(-0.3) and v.max() == pytest.approx(0.3)


def test_locked_c2_family_never_served(tmp_path: Path) -> None:
    """c2-family missions are structurally absent (the locked tier).

    Even with c2 files ON DISK the adapter refuses to serve them through
    the plain load call — the locked-instrument pattern, adapter level.
    """
    root = _fixture_tree(tmp_path)
    d = root / "c2"
    d.mkdir()
    (d / "dt_global_c2_phy_l3_1hz_20170105_20240205.nc").write_bytes(b"x")
    src = CmemsMySource(root)
    assert "c2" not in src.missions()
    with pytest.raises(ValueError, match="c2"):
        src.load(
            BBox(0.0, 360.0, -90.0, 90.0),
            np.datetime64("2017-01-05"),
            np.datetime64("2017-01-06"),
            missions=["c2"],
        )


def test_census_from_injected_listing() -> None:
    """Census arithmetic on an injected listing — no network, hand values."""

    def fake_listing(dataset_id: str) -> list[str]:
        code = dataset_id.split("_my_")[1].split("-l3")[0]
        return [
            f"native/x/{dataset_id}/1993/01/dt_global_{code}_phy_l3_1hz_19930103_20240205.nc",
            f"native/x/{dataset_id}/2001/12/dt_global_{code}_phy_l3_1hz_20011231_20240205.nc",
            f"native/x/{dataset_id}/1997/06/dt_global_{code}_phy_l3_1hz_19970615_20240205.nc",
        ]

    cat = catalog_from_listing(
        ["cmems_obs-sl_glo_phy-ssh_my_tp-l3-duacs_PT1S_202411"], fake_listing
    )
    assert cat == {
        "tp": {
            "first_date": "1993-01-03",
            "last_date": "2001-12-31",
            "n_files": 3,
            "dataset_id": "cmems_obs-sl_glo_phy-ssh_my_tp-l3-duacs_PT1S_202411",
            "dates": ["1993-01-03", "1997-06-15", "2001-12-31"],
        }
    }


def test_download_budget_wait_semantics(tmp_path: Path) -> None:
    """A pull whose estimate exceeds the remaining budget REFUSES (WAIT)."""
    from tests.helpers import load_script

    dl = load_script("download_cmems_my")
    with pytest.raises(RuntimeError, match="WAIT"):
        dl.check_budget(est_gib=10.0, already_gib=45.0)  # 55 > 50 ceiling
    dl.check_budget(est_gib=1.0, already_gib=45.0)  # inside: no raise


def test_ledger_absent_store_waits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing evidence store is a WAIT, never an unledgered pull.

    Bug caught: on a host without the evidence file, the budget check
    read 0.0 ledgered GiB and the pull completed with no ledger row
    (silent "ledger skip") — unledgered spend.
    """
    from tests.helpers import load_script

    dl = load_script("download_cmems_my")
    monkeypatch.setattr(dl, "EVIDENCE", tmp_path / "absent.json")
    with pytest.raises(RuntimeError, match="WAIT"):
        dl._ledgered_cmems_gib()
    with pytest.raises(RuntimeError, match="WAIT"):
        dl._ledger_append("cmems-x", 0.1)


@pytest.mark.skipif(
    not _SUBSET_PRESENT,
    reason=f"CMEMS subset not downloaded under {CMEMS_DATA_DIR}",
)
class TestCmemsConformance(AltimetryConformance):
    """Full conformance on the real downloaded subset (data-gated)."""

    @pytest.fixture
    def source_factory(self) -> Callable[[], AlongTrackSource]:
        return CmemsMySource

    @pytest.fixture
    def query(self) -> tuple[BBox, np.datetime64, np.datetime64]:
        return (
            BBox(lon_min=285.0, lon_max=315.0, lat_min=23.0, lat_max=53.0),
            np.datetime64("2017-01-05"),
            np.datetime64("2017-01-09"),
        )
