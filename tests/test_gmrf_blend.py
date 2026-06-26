"""GMRF blend: native shared-w coherence driver + (Task 9) seam-free blended product."""

from __future__ import annotations

from typing import cast

import numpy as np
import pytest

pytest.importorskip("sksparse")  # noqa: E402

from sverdrup.core.geometry import Tile, Window  # noqa: E402
from sverdrup.core.grid import GridSpec  # noqa: E402
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow  # noqa: E402
from sverdrup.core.parameters import ConstantProvider  # noqa: E402
from sverdrup.distributions.blend import BlendInput, partition_weights  # noqa: E402
from sverdrup.distributions.coherent import (  # noqa: E402
    GmrfPrecisionSolve,
    NoiseSpec,
    diagonal_noise,
    select_driver,
)
from sverdrup.distributions.persisted import (  # noqa: E402
    PrecisionDistribution,
    PrecisionFields,
)
from sverdrup.distributions.reduction import GMRFPrecisionReduction  # noqa: E402
from sverdrup.methods.gmrf import MaternGMRF  # noqa: E402

_P = ConstantProvider({"range": 300.0, "variance": 0.05, "temporal_taper_scale": 5.0})


def _gmrf_pd(grid, value=1.0):
    obs = ObsWindow.from_arrays(
        np.array([grid.x.mean()]),
        np.array([grid.y.mean()]),
        np.array([2.0]),
        np.array([value]),
        DiagonalErrorModel(np.array([1e-3])),
    )
    dist = MaternGMRF().solve(obs, grid, _P, 2.0)
    unit = GMRFPrecisionReduction().reduce(dist, grid.points(2.0), None, rank=0, seed=3)
    return PrecisionDistribution(
        grid, cast(PrecisionFields, unit.base_fields), dist.provenance, 2.0
    )


def test_select_driver_sparse_precision():
    assert isinstance(select_driver("sparse-precision"), GmrfPrecisionSolve)


def test_single_tile_member_is_native_shared_w():
    # Behavior: one GMRF tile's coherent member == mean + L^-T w with w the global cell noise.
    # Bug caught: a QR-basis trick (low-rank emulation) instead of native precision sampling.
    grid = GridSpec.lonlat(np.linspace(0.0, 6.0, 7), np.linspace(0.0, 6.0, 7))
    pd = _gmrf_pd(grid)
    tile = Tile(Window((0, 6), (0, 6), (0, 0)), Window((0, 6), (0, 6), (0, 0)), grid)
    parts = [BlendInput(pd, tile)]
    pts = grid.points(2.0)
    noise = NoiseSpec(method="gmrf", params_key="p", lattice_step=0.5)
    w = partition_weights([tile], pts)
    got = GmrfPrecisionSolve().crossfaded_member(parts, pts, w, 4, noise)
    white = diagonal_noise(pts, 4, noise)
    expected = pd.fields.mean.ravel() + pd._factor_obj().sample(white)
    np.testing.assert_allclose(got, expected, rtol=1e-9)
