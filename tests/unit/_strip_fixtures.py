"""Shared Stage-B fixtures: a 2x2 overlapping partition of one global grid + degenerate pairs.

Real import paths (the plan's draft used stale ones): ``Tile``/``Window`` live in
``sverdrup.core.geometry``; ``ConstantProvider`` in ``sverdrup.core.parameters``;
``BlendInput``/``partition_weights`` in ``sverdrup.distributions.blend``.
"""

from __future__ import annotations

from typing import cast

import numpy as np

from sverdrup.core.geometry import Tile, Window
from sverdrup.core.grid import GridSpec
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
from sverdrup.core.parameters import ConstantProvider, ParameterProvider
from sverdrup.distributions.blend import BlendInput
from sverdrup.distributions.persisted import PrecisionDistribution, PrecisionFields
from sverdrup.distributions.reduction import GMRFPrecisionReduction
from sverdrup.methods.gmrf import MaternGMRF

_STATIONARY = ConstantProvider(
    {"range": 300.0, "variance": 0.05, "temporal_taper_scale": 5.0}
)


def _pd(
    lon: np.ndarray,
    lat: np.ndarray,
    obsval: float,
    provider: ParameterProvider | None = None,
) -> PrecisionDistribution:
    """Solve a GMRF tile to a persisted precision distribution (distinct obs -> distinct Q)."""
    grid = GridSpec.lonlat(lon, lat)
    obs = ObsWindow.from_arrays(
        np.array([float(lon.mean())]),
        np.array([float(lat.mean())]),
        np.array([2.0]),
        np.array([obsval]),
        DiagonalErrorModel(np.array([1e-3])),
    )
    dist = MaternGMRF().solve(obs, grid, provider or _STATIONARY, 2.0)
    unit = GMRFPrecisionReduction().reduce(dist, grid.points(2.0), None, rank=0, seed=3)
    return PrecisionDistribution(
        grid, cast(PrecisionFields, unit.base_fields), dist.provenance, 2.0
    )


def _part(
    lon: np.ndarray,
    lat: np.ndarray,
    obsval: float,
    core: tuple[tuple[float, float], tuple[float, float]],
    ext: tuple[tuple[float, float], tuple[float, float]],
    provider: ParameterProvider | None = None,
) -> BlendInput:
    """Build one BlendInput from a tile grid extent + core/extended lon-lat windows."""
    pd = _pd(lon, lat, obsval, provider)
    tile = Tile(
        Window(core[0], core[1], (0.0, 0.0)),
        Window(ext[0], ext[1], (0.0, 0.0)),
        pd.grid,
    )
    return BlendInput(pd, tile)


def four_tile_corner_parts(
    provider: ParameterProvider | None = None,
) -> list[BlendInput]:
    """One global 0..9 grid split into four overlapping 0..5 / 4..9 quadrants.

    Cores partition the domain at the lon/lat 4|5 seam; extended windows overlap by two
    nodes in each direction, so the interior 2x2 corner block is shared by all four tiles.
    """
    x_lo, x_hi = np.arange(0.0, 6.0), np.arange(4.0, 10.0)
    y_lo, y_hi = np.arange(0.0, 6.0), np.arange(4.0, 10.0)
    return [
        _part(
            x_lo,
            y_lo,
            1.0,
            ((0.0, 4.0), (0.0, 4.0)),
            ((0.0, 5.0), (0.0, 5.0)),
            provider,
        ),
        _part(
            x_hi,
            y_lo,
            2.0,
            ((5.0, 9.0), (0.0, 4.0)),
            ((4.0, 9.0), (0.0, 5.0)),
            provider,
        ),
        _part(
            x_lo,
            y_hi,
            3.0,
            ((0.0, 4.0), (5.0, 9.0)),
            ((0.0, 5.0), (4.0, 9.0)),
            provider,
        ),
        _part(
            x_hi,
            y_hi,
            4.0,
            ((5.0, 9.0), (5.0, 9.0)),
            ((4.0, 9.0), (4.0, 9.0)),
            provider,
        ),
    ]


def disjoint_pair_parts() -> list[BlendInput]:
    """Two tiles whose extended windows do not touch — the strip network is empty (C6)."""
    return [
        _part(
            np.arange(0.0, 4.0),
            np.arange(0.0, 4.0),
            1.0,
            ((0.0, 3.0), (0.0, 3.0)),
            ((0.0, 3.0), (0.0, 3.0)),
        ),
        _part(
            np.arange(6.0, 10.0),
            np.arange(6.0, 10.0),
            2.0,
            ((6.0, 9.0), (6.0, 9.0)),
            ((6.0, 9.0), (6.0, 9.0)),
        ),
    ]
