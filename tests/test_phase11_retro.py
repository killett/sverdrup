"""Unit tests for scripts/phase11_retro_run.py (plan Task 7).

All on tmp files — the real one-shot runs once, manually. The script module
is loaded by path (scripts/ is not a package), mirroring the
build_jet_core_mask pattern in test_calibration_harness.py.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np
import pytest
import xarray as xr

from tests.helpers import load_script

_rr: ModuleType = load_script("phase11_retro_run")


def _fam(heading: float) -> dict[str, Any]:
    return {
        "heading_north_deg": heading,
        "n_passes": 24,
        "n_crossings": 24,
        "orbit_class": "repeat",
        "s_lon_km": 300.0,
        "d_perp_km": 280.0,
        "spacing_quantiles_km": None,
    }


def _write_geometry(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "derivation_version": 1,
                "key": "test",
                "phi0": 38.1,
                "missions": {"alg": {"asc": _fam(12.0), "desc": None}},
                "provenance": {"obs_sha256": {}},
            }
        )
    )


def _write_maps(path: Path, n_days: int = 3, seed: int = 0) -> None:
    rng = np.random.default_rng(seed)
    lon = np.arange(295, 305.01, 0.2)
    lat = np.arange(33, 43.21, 0.2)
    ssh = rng.standard_normal((n_days, lat.size, lon.size))
    ds = xr.Dataset(
        {"ssh": (("time", "lat", "lon"), ssh)},
        coords={"time": np.arange(n_days), "lat": lat, "lon": lon},
        attrs={"assimilated_missions": "alg h2g j2g j2n s3a"},
    )
    ds.to_netcdf(path)


def test_refuses_on_recorded_sha_mismatch(tmp_path: Path) -> None:
    """Bug caught: scoring a swapped input file — a recorded sha that no
    longer matches must refuse BEFORE any scoring happens."""
    maps = tmp_path / "maps.nc"
    _write_maps(maps)
    evidence = {
        "phase11": {"retro": {"provenance": {"input_sha256": {"maps": "deadbeef" * 8}}}}
    }
    with pytest.raises(ValueError, match="mismatch"):
        _rr.verify_or_anchor_inputs(evidence, {"maps": maps})


def test_absent_sha_records_first_anchor_note(tmp_path: Path) -> None:
    """Bug caught: refusing (or silently recording nothing) on the FIRST run
    — an absent recorded sha anchors with an explicit note."""
    maps = tmp_path / "maps.nc"
    _write_maps(maps)
    shas, notes = _rr.verify_or_anchor_inputs({}, {"maps": maps})
    assert len(shas["maps"]) == 64
    assert "first anchor" in notes["maps"]


def test_write_evidence_preserves_unrelated_keys(tmp_path: Path) -> None:
    """Bug caught: the nested-key write clobbering standing evidence — the
    phase10/phase8 blocks must be byte-identical before and after."""
    results = tmp_path / "results.json"
    unrelated = {
        "phase10": {"oi": {"lanes": {"verdict": {"branch": "within-band"}}}},
        "phase8": {"fit_run": {"selection": [1, 2, 3]}},
    }
    results.write_text(json.dumps(unrelated))
    before = {k: json.dumps(v, sort_keys=True) for k, v in unrelated.items()}
    _rr.write_evidence(results, "phase11.retro.miost.groundtrack", {"x": 1.0})
    after_full = json.loads(results.read_text())
    for key, blob in before.items():
        assert json.dumps(after_full[key], sort_keys=True) == blob
    assert after_full["phase11"]["retro"]["miost"]["groundtrack"] == {"x": 1.0}


def test_product_block_schema_and_ring_table(tmp_path: Path) -> None:
    """Bug caught: retro blocks missing an instrument row or the script-side
    per-ring n_modes table (the evidence contract of the retro record)."""
    maps = tmp_path / "maps.nc"
    geom = tmp_path / "phase11_orbit_geometry.json"
    _write_maps(maps)
    _write_geometry(geom)
    block = _rr.build_product_block(maps, geom)
    assert set(block) >= {"groundtrack", "spectral_fidelity", "n_modes_per_ring"}
    for name in ("groundtrack", "spectral_fidelity"):
        row = block[name]
        assert row["evaluator"] == name
        assert row["metrics"]
        assert row["params"]["wedge_masks_sha"]
    table = block["n_modes_per_ring"]
    assert len(table["ring"]) == len(table["n_modes"]) >= 4
    assert all(n >= 0 for n in table["n_modes"])


def test_c2_never_in_mission_union() -> None:
    """Bug caught: the withheld mission leaking into the geometry union."""
    union = _rr.mission_union(["alg h2g", "h2g s3a"])
    assert union == ["alg", "h2g", "s3a"]
    with pytest.raises(ValueError, match="c2"):
        _rr.mission_union(["alg c2"])
