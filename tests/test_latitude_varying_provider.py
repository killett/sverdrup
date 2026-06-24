"""Latitude-varying correlation length provider (configured, not learned)."""

from __future__ import annotations

import numpy as np

from sverdrup.core.grid import GridSpec
from sverdrup.core.parameters import LatitudeVaryingProvider


def test_correlation_length_decreases_toward_poles():
    # Behavior: correlation_length(lat) ~ 800 km equator -> ~100 km high lat.
    # Bug caught: a single global value defeats scale-aware halos (invariant 5).
    grid = GridSpec.lonlat(np.array([0.0]), np.array([0.0, 30.0, 60.0, 80.0]))
    p = LatitudeVaryingProvider(
        equator_km=800.0, pole_km=100.0, constants={"variance": 0.1, "time_scale": 10.0}
    )
    cl = np.asarray(p.resolve("correlation_length", grid))  # field over the grid
    by_lat = cl.reshape(grid.shape)[:, 0]
    assert by_lat[0] > by_lat[-1]  # equator wider than high-lat
    assert np.all(np.diff(by_lat) <= 1e-9)  # monotone non-increasing with |lat|


def test_constants_pass_through_and_key_is_stable():
    # Behavior: non-latitude params resolve as scalars; key is reproducible.
    # Bug caught: an unstable key breaks provenance reproducibility.
    grid = GridSpec.lonlat(np.array([0.0]), np.array([0.0]))
    p = LatitudeVaryingProvider(800.0, 100.0, {"variance": 0.1})
    assert float(p.resolve("variance", grid)) == 0.1
    assert (
        p.params_key()
        == LatitudeVaryingProvider(800.0, 100.0, {"variance": 0.1}).params_key()
    )


def test_key_encodes_latitude_profile():
    # Behavior: the params_key distinguishes different equator/pole profiles.
    # Bug caught: a key that ignores the profile collapses distinct runs in provenance.
    a = LatitudeVaryingProvider(800.0, 100.0, {"variance": 0.1}).params_key()
    b = LatitudeVaryingProvider(600.0, 100.0, {"variance": 0.1}).params_key()
    assert a != b
