"""Tests for the five-mission input adapter (Cryosat-2 held out)."""

import numpy as np
import pytest

from sverdrup.core.observations import ObsWindow
from sverdrup.validation.input_adapter import (
    MAPPING_MISSIONS,
    EvalTrack,
    load_eval_track,
    load_mapping_obs,
)


def test_withheld_cryosat2_never_in_mapping_set(
    mapping_fixture_paths, baseline_provider
):
    """The mapping ObsWindow contains only mapping missions, never Cryosat-2.

    Catches a withheld-mission leak that would invalidate the OSE score.
    """
    obs = load_mapping_obs(mapping_fixture_paths, baseline_provider)
    assert isinstance(obs, ObsWindow)
    assert obs.mission is not None
    missions = set(np.unique(obs.mission).tolist())
    assert "c2" not in missions
    assert missions <= MAPPING_MISSIONS


def test_cryosat2_file_rejected_from_mapping(cryosat2_fixture_path, baseline_provider):
    """Feeding the Cryosat-2 file to the mapping loader must raise, not silently load.

    Catches the worst failure mode: the withheld eval mission leaking into the
    mapping inputs because the loader accepted an unknown/forbidden mission code.
    """
    with pytest.raises(ValueError, match="c2|mission"):
        load_mapping_obs([cryosat2_fixture_path], baseline_provider)


def test_spinup_obs_included_in_mapping_input(mapping_fixture_paths, baseline_provider):
    """Obs from before 2017-01-01 are present in the mapping input (spin-up).

    Catches an eval-window boundary error that would starve early-2017 maps of
    their temporal neighbours (day 0 == 2017-01-01; spin-up is negative days).
    """
    obs = load_mapping_obs(mapping_fixture_paths, baseline_provider)
    times = obs.coords()[:, 2]
    assert times.min() < 0.0


def test_eval_track_is_2017_only_and_not_an_obswindow(cryosat2_fixture_path):
    """The eval track is a separate EvalTrack, restricted to 2017, never OI-feedable.

    Catches (a) returning something an OI run could ingest, and (b) leaking
    spin-up obs into the eval window (eval is 2017 only, day >= 0).
    """
    track = load_eval_track(cryosat2_fixture_path)
    assert isinstance(track, EvalTrack)
    assert not isinstance(track, ObsWindow)
    assert track.time_days.size > 0
    assert track.time_days.min() >= 0.0


def test_mapping_values_are_sla_unfiltered(mapping_fixture_paths, baseline_provider):
    """Mapping obs carry sla_unfiltered (the variable their oi_core maps).

    Catches a reference-frame slip (loading sla_filtered or an SSH that already
    includes MDT) that would silently shift every mapped value.
    """
    import xarray as xr

    obs = load_mapping_obs(mapping_fixture_paths, baseline_provider)
    ds = xr.open_dataset(mapping_fixture_paths[0])
    # values must lie within the sla_unfiltered range, not sla_filtered/ssh range
    raw = np.asarray(ds["sla_unfiltered"]).astype(float)
    assert np.nanmin(raw) - 1e-6 <= obs.values().min()
    assert obs.values().max() <= np.nanmax(raw) + 1e-6
