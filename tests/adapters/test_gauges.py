"""Gauge data-layer tests (phase-14 Task 8, 0a-3a): parsing + LOCKED REFUSAL.

CI-green on synthetic fixtures; network legs live in the downloader script
and are exercised by the real catalog run (evidence-recorded), never here.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from sverdrup.adapters.insitu.gauges import (
    GaugeDaily,
    LockedGaugeError,
    load_gauge,
    load_psmsl_catalog,
    locked_ids,
    parse_uhslc_hourly,
)

ENV = "SVERDRUP_INSITU_LOCKED"


def _uhslc_fixture(path: Path, *, hours: int = 48, fill_from: int = 40) -> Path:
    """Synthetic UHSLC-rqds-hourly-layout file, documented schema.

    48 hourly samples over two days; sea_level in MILLIMETERS with the
    trailing 8 samples set to the fill value (a partial second day).
    """
    t0 = np.datetime64("2015-03-01T00:00:00")
    time = t0 + np.arange(hours) * np.timedelta64(1, "h")
    level_mm = np.linspace(1000.0, 2000.0, hours)
    level_mm[fill_from:] = np.nan
    ds = xr.Dataset(
        {"sea_level": ("time", level_mm)},
        coords={"time": time},
        attrs={"station_name": "FIXTURE", "uhslc_id": 999},
    )
    ds["lat"] = 21.3
    ds["lon"] = 202.1
    ds.to_netcdf(path)
    return path


def test_parse_uhslc_hourly_daily_means_hand_computed(tmp_path: Path) -> None:
    """Daily means: mm -> m conversion and per-day averaging, hand-derived.

    Day 1 = mean of samples 0..23 of linspace(1000, 2000, 48) mm; a
    unit-conversion slip (cm vs mm) or an off-by-one day boundary moves the
    value and fails the exact comparison.
    """
    path = _uhslc_fixture(tmp_path / "h999.nc")
    g = parse_uhslc_hourly(path, gauge_id="uh999")
    level_mm = np.linspace(1000.0, 2000.0, 48)
    expected_day1 = level_mm[:24].mean() / 1000.0
    assert g.gauge_id == "uh999"
    assert g.lon == 202.1 and g.lat == 21.3
    assert g.days[0] == np.datetime64("2015-03-01")
    np.testing.assert_allclose(g.sea_level_m[0], expected_day1, rtol=1e-12)


def test_parse_uhslc_hourly_drops_underfilled_days(tmp_path: Path) -> None:
    """A day with < 12 valid hourly samples is dropped, not averaged thin."""
    path = _uhslc_fixture(tmp_path / "h999.nc", hours=48, fill_from=30)
    g = parse_uhslc_hourly(path, gauge_id="uh999")
    # day 2 has only 6 valid samples (24..29) -> dropped
    assert list(g.days.astype(str)) == ["2015-03-01"]


def test_load_psmsl_catalog_parses_filelist(tmp_path: Path) -> None:
    """The RLR filelist columns parse into typed rows."""
    z = tmp_path / "rlr_monthly.zip"
    lines = [
        " 1; 48.382850;  -4.494838; BREST;                190; 091; N",
        " 7; 53.866667;   8.716667; CUXHAVEN 2;           140; 012; N",
        # non-numeric coastline/station codes occur in the real snapshot
        " 9;  0.000000;   0.000000; SOMEWHERE;            XXX; XXX; N",
    ]
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("rlr_monthly/filelist.txt", "\n".join(lines) + "\n")
    cat = load_psmsl_catalog(z)
    assert len(cat) == 3
    assert cat[0].psmsl_id == 1
    assert cat[0].lat == pytest.approx(48.382850)
    assert cat[0].lon == pytest.approx(-4.494838)
    assert cat[0].name == "BREST"
    assert cat[0].coastline == 190
    assert cat[2].coastline is None  # XXX code tolerated, never a crash


def _write_split(path: Path, locked: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"locked": locked, "dev": ["uh001"]}))


def test_locked_refusal_before_any_file_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A locked id raises LockedGaugeError BEFORE any file open.

    The gauge's data file does NOT exist — a refusal that only fired after
    an open attempt would surface FileNotFoundError instead.
    """
    monkeypatch.delenv(ENV, raising=False)
    split = tmp_path / "locked_split.json"
    _write_split(split, ["uh777"])
    with pytest.raises(LockedGaugeError, match="uh777"):
        load_gauge("uh777", data_dir=tmp_path, split_path=split)


@pytest.mark.parametrize("value", ["true", "yes", "", "0"])
def test_locked_refusal_exact_string(
    value: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only the exact string "1" opens locked ids (the c2 ceremony pattern)."""
    monkeypatch.setenv(ENV, value)
    split = tmp_path / "locked_split.json"
    _write_split(split, ["uh777"])
    with pytest.raises(LockedGaugeError):
        load_gauge("uh777", data_dir=tmp_path, split_path=split)


def test_locked_loads_with_ceremony_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With the exact-string env the locked gauge loads normally."""
    monkeypatch.setenv(ENV, "1")
    split = tmp_path / "locked_split.json"
    _write_split(split, ["uh777"])
    (tmp_path / "uhslc").mkdir()
    _uhslc_fixture(tmp_path / "uhslc" / "uh777.nc")
    g = load_gauge("uh777", data_dir=tmp_path, split_path=split)
    assert isinstance(g, GaugeDaily)
    assert g.gauge_id == "uh777"


def test_dev_pool_loads_without_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dev-pool ids load with no ceremony env at all."""
    monkeypatch.delenv(ENV, raising=False)
    split = tmp_path / "locked_split.json"
    _write_split(split, ["uh777"])
    (tmp_path / "uhslc").mkdir()
    _uhslc_fixture(tmp_path / "uhslc" / "uh001.nc")
    g = load_gauge("uh001", data_dir=tmp_path, split_path=split)
    assert g.gauge_id == "uh001"


def test_locked_ids_empty_when_split_absent(tmp_path: Path) -> None:
    """No split artifact yet -> empty locked set (pre-seal state), not a crash."""
    assert locked_ids(tmp_path / "nope.json") == frozenset()
