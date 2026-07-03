"""Tests for MiostPointDistribution: capability fail-loud, persistence, mean_at (seams d, e)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from sverdrup.core.distribution import CapabilityNotAvailableError
from sverdrup.methods.miost import MiostPointDistribution
from sverdrup.methods.miost_basis import lonlat_to_km
from tests._miost_fixtures import TINY_DAY, TINY_SPEC, tiny_point_distribution

P = np.array([[300.0, 38.0, 30.0], [301.0, 39.0, 30.0]])


def test_capability_calls_raise_loud() -> None:
    """POINT: variance-family calls raise with the capability named — never None/NaN."""
    d = tiny_point_distribution()
    for call in (
        d.marginal_variance,
        lambda: d.covariance(P, P),
        lambda: d.sample(2, 0),
    ):
        with pytest.raises(CapabilityNotAvailableError, match="POINT"):
            call()


def test_persist_round_trip(tmp_path: Path) -> None:
    """save_state/load_state: reloaded object reproduces the mean bit-identically."""
    d = tiny_point_distribution()
    p = tmp_path / "state.npz"
    d.save_state(p)
    d2 = MiostPointDistribution.load_state(p)
    np.testing.assert_array_equal(np.asarray(d.mean), np.asarray(d2.mean))
    assert d2.time_days == d.time_days


def test_mean_at_equals_direct_analytic_eval() -> None:
    """Seam (d): mean_at(points) == Gamma(points) @ eta for the single-window state."""
    d = tiny_point_distribution()
    got = d.mean_at(P)
    els = TINY_SPEC.elements_for_window(0.0)
    x, y = lonlat_to_km(P[:, 0], P[:, 1])
    gamma = TINY_SPEC.evaluate(els, x, y, P[:, 2])
    eta = next(iter(d._etas.values()))
    np.testing.assert_allclose(got, gamma @ eta, rtol=1e-12)


def test_mean_is_grid_shaped_and_matches_mean_at() -> None:
    """The stored mean field equals mean_at evaluated on the grid nodes at time_days."""
    d = tiny_point_distribution()
    assert np.asarray(d.mean).shape == d.grid.shape
    lon2d, lat2d = np.meshgrid(d.grid.x, d.grid.y)
    pts = np.column_stack([lon2d.ravel(), lat2d.ravel(), np.full(lon2d.size, TINY_DAY)])
    np.testing.assert_allclose(np.asarray(d.mean).ravel(), d.mean_at(pts), rtol=1e-12)
