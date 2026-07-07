"""Shared obs-framing helper + cross-path parity (owner order, 2026-07-07).

Third convention divergence this phase: the production/acceptance path cut
obs at GRID NODES ± halo while the Stage-B runner cut at the nominal box ±
halo — a 762-obs sliver at 43.0–43.2°N (+halo) that broke the c2
bit-identity check. One helper, derived from the grid, used by BOTH paths;
a parity test pins them together.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from sverdrup.core.grid import GridSpec
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
from sverdrup.core.parameters import ConstantProvider
from sverdrup.validation.run import halo_obs, run_challenge_map

# A grid whose lat axis OVERSHOOTS the nominal box (the production 0.2-deg
# grid runs to 43.2N over the 33-43 box — the quirk the helper must honor).
GRID = GridSpec.lonlat(np.arange(300.0, 301.01, 0.5), np.arange(38.0, 39.21, 0.4))


def _obs(lats: list[float]) -> ObsWindow:
    n = len(lats)
    return ObsWindow.from_arrays(
        np.full(n, 300.5),
        np.asarray(lats, float),
        np.zeros(n),
        np.zeros(n),
        DiagonalErrorModel(np.full(n, 0.01)),
        np.asarray(["alg"] * n),
    )


def test_halo_obs_region_derived_from_grid_nodes() -> None:
    """The cut is GRID NODES ± halo, not the nominal box ± halo.

    Hand: lat nodes run 38.0..39.2 (the 39.2 overshoot); halo 1.0 keeps
    lat <= 40.2. Points at 40.1 (the sliver a box-derived cut at 39+1=40.0
    would DROP — the exact c2 defect) and 37.1 kept; 40.3 dropped.
    """
    obs = _obs([37.1, 40.1, 40.3])
    kept = halo_obs(obs, GRID, halo_deg=1.0)
    np.testing.assert_allclose(kept.coords()[:, 1], [37.1, 40.1])


def test_framing_parity_with_run_challenge_map(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """run_challenge_map subsets EXACTLY like halo_obs (same points).

    Bug caught: the two paths re-diverging (someone reintroducing a local
    in_region block) — the defect class that spent a c2 touch.
    """
    from sverdrup.methods import registry

    seen: list[np.ndarray] = []

    class _Stub:
        native_capability = None

        def solve(
            self, win: ObsWindow, grid: GridSpec, params: object, time_days: float
        ) -> object:
            seen.append(win.coords().copy())

            class _D:
                mean = np.zeros(grid.shape)

            return _D()

    monkeypatch.setitem(registry.METHODS, "framing-stub", _Stub)
    obs = _obs([37.1, 38.5, 40.1, 40.3])
    run_challenge_map(
        "framing-stub",
        obs,
        ConstantProvider({}),
        GRID,
        temporal_half_window_days=999.0,
        output_days=[0.0],
        dest=tmp_path / "m.nc",
    )
    expected = halo_obs(obs, GRID, halo_deg=1.0).coords()
    assert len(seen) == 1
    np.testing.assert_array_equal(seen[0], expected)
