"""Provenance-enforced train/score separation (Task 21 hardening).

Maps carry the assimilated-mission list as typed file provenance; every
track-scoring path asserts the scored mission was NOT assimilated. Ordered
after the Task-13 winner-point leak (assimilate-j3-score-j3): the assert must
fire on a deliberately-leaked map, and must stay quiet for external maps that
predate the provenance (the distributed challenge products).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from sverdrup.core.grid import GridSpec
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
from sverdrup.core.parameters import ConstantProvider
from sverdrup.validation.output_adapter import write_map
from sverdrup.validation.provenance_guard import (
    ASSIMILATED_ATTR,
    TrainScoreLeakError,
    assert_scored_not_assimilated,
)
from sverdrup.validation.run import run_challenge_map
from tests.helpers import load_script

J3_TRACK = Path("dt_gulfstream_j3_phy_l3_20161201-20180131_285-315_23-53.nc")


def _map_file(tmp_path: Path, assimilated: tuple[str, ...] | None) -> Path:
    """A minimal challenge-schema map file, optionally provenance-tagged."""
    return write_map(
        times=np.array(["2017-01-01"], dtype="datetime64[ns]"),
        lats=np.array([38.0, 38.5]),
        lons=np.array([300.0, 300.5]),
        ssh=np.zeros((1, 2, 2)),
        dest=tmp_path / "map.nc",
        assimilated_missions=assimilated,
    )


def test_write_map_round_trips_assimilated_attr(tmp_path: Path) -> None:
    """The attr survives the NetCDF round trip, sorted and space-joined.

    Bug caught: attr dropped or mangled at write time — every downstream
    guard would then be blind (attr-absent means 'external map, skip').
    """
    p = _map_file(tmp_path, ("j3", "alg", "j3"))
    with xr.open_dataset(p) as ds:
        assert ds.attrs[ASSIMILATED_ATTR] == "alg j3"


def test_write_map_default_writes_no_attr(tmp_path: Path) -> None:
    """No missions given -> attr ABSENT (not empty-string).

    Bug caught: writing '' would make every untagged map claim 'nothing
    assimilated' — a false provenance instead of no provenance.
    """
    p = _map_file(tmp_path, None)
    with xr.open_dataset(p) as ds:
        assert ASSIMILATED_ATTR not in ds.attrs


def test_run_challenge_map_records_train_missions(tmp_path: Path) -> None:
    """Maps built from labeled obs carry exactly those missions.

    Bug caught: the runner forgetting to thread obs.mission into write_map —
    the enforcement chain would be severed at its source.
    """
    rng = np.random.default_rng(0)
    n = 60
    obs = ObsWindow.from_arrays(
        300.0 + rng.random(n),
        38.0 + rng.random(n),
        rng.uniform(-2, 2, n),
        rng.standard_normal(n) * 0.1,
        DiagonalErrorModel(np.full(n, 0.01)),
        mission=np.asarray(["alg", "h2g"])[rng.integers(0, 2, n)],
    )
    grid = GridSpec.lonlat(np.arange(300.0, 301.01, 0.5), np.arange(38.0, 39.01, 0.5))
    p = ConstantProvider({"length_scale": 100.0, "time_scale": 7.0, "variance": 1.0})
    out = run_challenge_map("oi", obs, p, grid, 14.0, [0.0], tmp_path / "m.nc")
    with xr.open_dataset(out) as ds:
        assert ds.attrs[ASSIMILATED_ATTR] == "alg h2g"


def test_guard_fires_on_deliberately_leaked_map(tmp_path: Path) -> None:
    """THE ordered test: scoring j3 on a map that assimilated j3 raises.

    Bug caught: membership check inverted, or the guard never reading the
    attr — the exact Task-13 leak class (assimilate-j3-score-j3) passing
    silently again.
    """
    leaked = _map_file(tmp_path, ("alg", "j3"))
    with pytest.raises(TrainScoreLeakError, match="j3"):
        assert_scored_not_assimilated(leaked, J3_TRACK)


def test_guard_passes_on_clean_map(tmp_path: Path) -> None:
    """Scoring j3 on a map that assimilated only other missions is allowed.

    Bug caught: an over-eager guard raising on ANY provenance-tagged map
    would kill every legitimate validation score.
    """
    clean = _map_file(tmp_path, ("alg", "h2g"))
    assert_scored_not_assimilated(clean, J3_TRACK)  # must not raise


def test_guard_skips_map_without_provenance(tmp_path: Path) -> None:
    """Attr-absent maps (external/legacy, e.g. distributed products) pass.

    Bug caught: a strict-raise on missing attr would break Tier-3 / spike
    scoring of the distributed challenge maps, which we cannot re-tag.
    """
    external = _map_file(tmp_path, None)
    assert_scored_not_assimilated(external, J3_TRACK)  # must not raise


def test_guard_raises_when_track_mission_unidentifiable(tmp_path: Path) -> None:
    """Provenance-tagged map + unparseable track name -> raise, never skip.

    Bug caught: silently skipping when the mission cannot be parsed would
    let a leaked map through unverified — enforcement must fail LOUD when
    it cannot prove separation for a map that carries provenance.
    """
    tagged = _map_file(tmp_path, ("alg",))
    with pytest.raises(TrainScoreLeakError, match="track"):
        assert_scored_not_assimilated(tagged, Path("track.nc"))


def test_their_eval_score_asserts_before_scoring(tmp_path: Path) -> None:
    """their_eval.score (the c2 acceptance path) is guard-wired.

    Bug caught: the guard existing but never called at this entry — the
    acceptance touch could score a leaked map. The raise must happen BEFORE
    the vendored-eval machinery runs (no track data exists here).
    """
    import sverdrup.validation.their_eval as te

    leaked = _map_file(tmp_path, ("alg", "j3"))
    with pytest.raises(TrainScoreLeakError, match="j3"):
        te.score(leaked, J3_TRACK)


def test_validation_track_scorer_asserts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The per-trial tuning scorer is guard-wired.

    Bug caught: the tuning loop scoring every trial on a leaked map for a
    whole search — the loop-scale version of the Task-13 leak.
    """
    from sverdrup.application.tuning.scorer import ValidationTrackScorer

    leaked = _map_file(tmp_path, ("alg", "j3"))
    scorer = ValidationTrackScorer(
        train_obs=None,  # type: ignore[arg-type]  # map production monkeypatched
        grid=None,  # type: ignore[arg-type]
        output_days=[0.0],
        temporal_half_window_days=425.0,
        val_track_path=tmp_path / J3_TRACK.name,
        lon_min=295.0,
        lon_max=305.0,
        lat_min=33.0,
        lat_max=43.0,
        time_min="2017-01-01",
        time_max="2017-12-31",
    )
    monkeypatch.setattr(
        ValidationTrackScorer,
        "_produce_maps",
        lambda self, method_name, params, td: (leaked, None),
    )
    with pytest.raises(TrainScoreLeakError, match="j3"):
        scorer.score("oi", {}, split=None, seed=0, window=None)


def test_gate_runner_scoring_asserts(tmp_path: Path) -> None:
    """stage_miost_gate_run._score_map_on_validation is guard-wired.

    Bug caught: the winner-point / acceptance scoring path — where the
    Task-13 cross-protocol leak actually happened — accepting a leaked map.
    """
    from sverdrup.application.tuning.scorer import ValidationTrackScorer

    orig = ValidationTrackScorer.score
    try:
        mod = load_script("stage_miost_gate_run")
        leaked = _map_file(tmp_path, ("alg", "j3"))
        cfg = {
            "val_track_path": str(tmp_path / J3_TRACK.name),
            "time_min": "2017-01-01",
            "time_max": "2018-01-01",
        }
        with pytest.raises(TrainScoreLeakError, match="j3"):
            mod._score_map_on_validation(leaked, cfg)
    finally:
        ValidationTrackScorer.score = orig  # type: ignore[method-assign]  # script wraps at import
        sys.modules.pop("stage_miost_gate_run", None)


def test_localization_diag_scoring_asserts(tmp_path: Path) -> None:
    """diag_miost_localization._score_on_validation is guard-wired.

    Bug caught: the D4 localization harness re-scoring a leaked map in a
    future rerun (its VAL_TRACK is the blocked j3 file).
    """
    try:
        mod = load_script("diag_miost_localization")
        leaked = _map_file(tmp_path, ("alg", "j3"))
        with pytest.raises(TrainScoreLeakError, match="j3"):
            mod._score_on_validation(leaked)
    finally:
        sys.modules.pop("diag_miost_localization", None)
