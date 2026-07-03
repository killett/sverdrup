"""Shared tiny MIOST fixtures: a solved 2-rung state built through the public API."""

from __future__ import annotations

import numpy as np

from sverdrup.methods.miost import MiostPointDistribution
from sverdrup.methods.miost_basis import BasisSpec, DiagonalQ, build_g
from sverdrup.methods.miost_solver import MiostSolver, rhs_from_obs
from sverdrup.methods.miost_windows import Window

TINY_SPEC = BasisSpec(alpha=1.5, l_t_days=10.0, ladder=(320.0, 452.548))
TINY_WINDOW = Window(0.0)
TINY_GRID_LON = np.linspace(296.0, 304.0, 9)
TINY_GRID_LAT = np.linspace(34.0, 42.0, 9)
TINY_DAY = 30.0


def tiny_solved_eta(n_obs: int = 40) -> np.ndarray:
    """Solve the duality-oracle geometry once; return eta for window [0, 60]."""
    rng = np.random.default_rng(11)
    els = TINY_SPEC.elements_for_window(TINY_WINDOW.start_day)
    lon = rng.uniform(296, 304, n_obs)
    lat = rng.uniform(34, 42, n_obs)
    t = rng.uniform(10, 50, n_obs)
    y = rng.standard_normal(n_obs) * 0.1
    r = np.full(n_obs, 0.01)
    q = DiagonalQ(rho=20.0, q_slope=2.0).variances_for(els)
    g = build_g(TINY_SPEC, els, lon, lat, t)
    eta, _ = MiostSolver(g, r_diag=r, q_diag=q).solve(rhs_from_obs(g, r, y))
    return np.asarray(eta)


def tiny_point_distribution() -> MiostPointDistribution:
    """A single-window POINT distribution on a small geographic grid at day 30."""
    from sverdrup.core.grid import GridSpec

    eta = tiny_solved_eta()
    grid = GridSpec.lonlat(TINY_GRID_LON, TINY_GRID_LAT)
    return MiostPointDistribution.from_etas(
        grid=grid,
        time_days=TINY_DAY,
        spec=TINY_SPEC,
        etas={TINY_WINDOW.id: eta},
        window_starts={TINY_WINDOW.id: TINY_WINDOW.start_day},
    )
