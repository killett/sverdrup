"""SPEC §10 gate 2, loader-identity half (phase-14 Task 2 — RUNS in Stage 0).

The new ``Dc2021aSource`` must reproduce the current box input path's arrays
BYTE-identically: per mission, over the full file span AND restricted to
2017, for the mapping set and the j3 validation track. c2 is never loadable
through the mapping call.

Dtype note (recorded interpretation): numeric arrays (lon, lat, t, value)
assert dtype equality too (guards silent float32 drift). Mission labels are
compared by VALUE — numpy promotes fixed-width str dtypes on concatenation
(a j3-only load is ``<U2`` while the j3 subset of a six-file concat is
``<U3``), so label dtype equality would test numpy's promotion rules, not
the loader.

On the gate's single execution with data present, the result is recorded at
``phase14.stage0.gate2_loader_identity`` in the standing evidence JSON.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from sverdrup.adapters.altimetry import BBox
from sverdrup.adapters.altimetry.dc2021a import DC_OBS_DIR, Dc2021aSource
from sverdrup.core.observations import ObsWindow

_DATA_PRESENT = DC_OBS_DIR.is_dir() and any(DC_OBS_DIR.glob("*.nc"))

pytestmark = pytest.mark.skipif(
    not _DATA_PRESENT,
    reason=f"challenge obs directory {DC_OBS_DIR} absent on this host",
)

_EVIDENCE = Path("data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json")
_GLOBE = BBox(lon_min=0.0, lon_max=360.0, lat_min=-90.0, lat_max=90.0)
# Full file span (files cover 2016-12-01..2018-01-31) and the 2017 frame.
_SPAN = (np.datetime64("2016-11-01"), np.datetime64("2018-03-01"))
_YEAR = (np.datetime64("2017-01-01"), np.datetime64("2018-01-01"))
_MAPPING_FIVE = ("alg", "h2g", "j2g", "j2n", "s3a")  # signed mapping set
_VALIDATION = "j3"


@pytest.fixture(scope="module")
def legacy() -> ObsWindow:
    """The legacy input path's six-file load — the identity target."""
    from sverdrup.core.parameters import ConstantProvider
    from sverdrup.validation.input_adapter import load_mapping_obs

    paths = sorted(p for p in DC_OBS_DIR.glob("*.nc") if "_c2_" not in p.name)
    assert len(paths) == 6, "expected the six challenge mapping+j3 files"
    return load_mapping_obs(paths, ConstantProvider({}))


def _split(obs: ObsWindow) -> dict[str, dict[str, np.ndarray]]:
    """Per-mission arrays of a window, order preserved."""
    c = obs.coords()
    v = obs.values()
    mission = obs.mission
    assert mission is not None
    out: dict[str, dict[str, np.ndarray]] = {}
    for m in np.unique(mission):
        keep = mission == m
        out[str(m)] = {
            "lon": c[keep, 0],
            "lat": c[keep, 1],
            "t": c[keep, 2],
            "value": v[keep],
        }
    return out


def _assert_mission_identical(
    ours: dict[str, np.ndarray], theirs: dict[str, np.ndarray]
) -> None:
    for k in ("lon", "lat", "t", "value"):
        assert np.array_equal(ours[k], theirs[k]), f"{k} arrays differ"
        assert ours[k].dtype == theirs[k].dtype == np.float64


@pytest.mark.parametrize("mission", (*_MAPPING_FIVE, _VALIDATION))
def test_per_mission_byte_identity_full_span(legacy: ObsWindow, mission: str) -> None:
    """Each mission's arrays via the new loader == the legacy path's, exactly."""
    ours = Dc2021aSource().load(_GLOBE, *_SPAN, missions=[mission])
    ours_m = _split(ours)
    assert set(ours_m) == {mission}
    _assert_mission_identical(ours_m[mission], _split(legacy)[mission])


def test_mapping_set_identity_2017_frame(legacy: ObsWindow) -> None:
    """Five-mission mapping load over 2017 == the time-masked legacy subset."""
    ours = Dc2021aSource().load(_GLOBE, *_YEAR, missions=_MAPPING_FIVE)
    ours_m = _split(ours)
    assert set(ours_m) == set(_MAPPING_FIVE)
    legacy_m = _split(legacy)
    t1_days = float((_YEAR[1] - np.datetime64("2017-01-01")) / np.timedelta64(1, "D"))
    any_cut = False
    for m in _MAPPING_FIVE:
        keep = (legacy_m[m]["t"] >= 0.0) & (legacy_m[m]["t"] < t1_days)
        masked = {k: a[keep] for k, a in legacy_m[m].items()}
        assert keep.any(), f"2017 frame left no {m} obs"
        any_cut = any_cut or not keep.all()
        _assert_mission_identical(ours_m[m], masked)
    assert any_cut, "2017 frame must cut spin-up obs somewhere (anti-vacuity)"


def test_j3_validation_track_identity(legacy: ObsWindow) -> None:
    """The j3 validation track via the new loader == the legacy j3 subset."""
    ours = Dc2021aSource().load(_GLOBE, *_SPAN, missions=[_VALIDATION])
    _assert_mission_identical(_split(ours)[_VALIDATION], _split(legacy)[_VALIDATION])


def test_c2_refused_through_mapping_call() -> None:
    """c2 NEVER loadable through the mapping call (exclusion preserved)."""
    with pytest.raises(ValueError, match="c2"):
        Dc2021aSource().load(_GLOBE, *_SPAN, missions=["c2"])


def test_record_gate2_evidence(legacy: ObsWindow) -> None:
    """Record the gate result (runs last: pass bool + n_obs + manifest sha)."""
    src = Dc2021aSource()
    ours = src.load(_GLOBE, *_SPAN)
    ours_m = _split(ours)
    legacy_m = _split(legacy)
    assert set(ours_m) == set(legacy_m)
    for m in ours_m:
        _assert_mission_identical(ours_m[m], legacy_m[m])

    if not _EVIDENCE.exists():  # pragma: no cover - evidence store is host-local
        pytest.skip("standing evidence JSON absent; gate arrays verified above")
    from datetime import UTC, datetime

    from sverdrup.application.calibration.harness import atomic_write_json

    results: dict[str, Any] = json.loads(_EVIDENCE.read_text())
    node = results
    for k in ("phase14", "stage0"):
        node = node.setdefault(k, {})
    if "gate2_loader_identity" in node:
        return  # write-once: the recorded gate execution stands (misfire ethic)
    node["gate2_loader_identity"] = {
        "pass": True,  # the key exists only because the assertions above held
        "per_mission_n_obs": {m: int(a["lon"].size) for m, a in ours_m.items()},
        "manifest_sha": src.descriptor().manifest_sha(),
        "date": datetime.now(UTC).date().isoformat(),
    }
    atomic_write_json(_EVIDENCE, results)
