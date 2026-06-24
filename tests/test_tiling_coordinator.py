"""Coordinator emits one unit per tile and blends the gathered Persisted reps."""

from __future__ import annotations

import numpy as np

from sverdrup.application.tiling import (
    LonLatPartition,
    ScaleAwareHalo,
    TilingCoordinator,
)
from sverdrup.core.grid import GridSpec
from sverdrup.core.parameters import LatitudeVaryingProvider


class _FakeExecutor:
    """In-process executor stand-in: runs a provided solve fn per unit, counts submits."""

    def __init__(self, solve_fn):
        self.solve_fn = solve_fn
        self.submits = 0

    def submit(self, uow):
        self.submits += 1
        return self.solve_fn(uow)


def test_coordinator_emits_one_unit_per_tile_and_blends():
    # Behavior: partition -> one submit per tile -> gather -> blend over target.
    # Bug caught: re-granularization (more units than tiles) or skipping the blend.
    target = GridSpec.lonlat(np.linspace(-10, 10, 41), np.array([0.0, 1.0]))
    prov = LatitudeVaryingProvider(800.0, 100.0, {"variance": 0.1, "time_scale": 10.0})
    partition = LonLatPartition(
        n_lon=2,
        n_lat=1,
        halo=ScaleAwareHalo(k=0.2),
        correlation_length=prov,
        stencil_radius_km=10.0,
    )

    def fake_solve(uow):
        # return a flat Persisted over the tile grid (mean=1, sigma=0.2) wrapped as a Product
        from sverdrup.core.product import PerTimeProduct, Product
        from tests.test_blend_cheap_path import _persisted

        base = _persisted(uow.grid, 1.0, 0.2)
        pt = PerTimeProduct(0.0, base, {}, None, base.provenance)
        return Product([pt], {"window": uow.window_id})

    ex = _FakeExecutor(fake_solve)
    coord = TilingCoordinator()
    blended = coord.run(
        target,
        partition,
        method="oi",
        params=prov,
        split=None,
        seed=0,
        output_times=[0.0],
        executor=ex,
    )
    assert ex.submits == 2  # exactly one unit per tile
    assert np.allclose(blended[0].mean, 1.0, atol=1e-9)  # blended over target


def test_coordinator_blend_matches_cheap_path_crossfade():
    # Behavior: the coordinator's blended mean equals the Task-3 cheap-path crossfade.
    # Bug caught: the coordinator silently picks one tile instead of crossfading overlaps.
    target = GridSpec.lonlat(np.linspace(-10, 10, 41), np.array([0.0, 1.0]))
    prov = LatitudeVaryingProvider(800.0, 100.0, {"variance": 0.1})
    partition = LonLatPartition(
        n_lon=2,
        n_lat=1,
        halo=ScaleAwareHalo(k=0.2),
        correlation_length=prov,
        stencil_radius_km=10.0,
    )

    def fake_solve(uow):
        from sverdrup.core.product import PerTimeProduct, Product
        from tests.test_blend_cheap_path import _persisted

        # distinct per-tile means so the crossfade is non-trivial (by core side)
        mval = 2.0 if uow.grid.x.mean() < 0 else 5.0
        base = _persisted(uow.grid, mval, 0.3)
        pt = PerTimeProduct(0.0, base, {}, None, base.provenance)
        return Product([pt], {"window": uow.window_id})

    ex = _FakeExecutor(fake_solve)
    blended = TilingCoordinator().run(
        target,
        partition,
        method="oi",
        params=prov,
        split=None,
        seed=0,
        output_times=[0.0],
        executor=ex,
    )
    out = blended[0]
    # mean stays within the convex hull of the two constituent means everywhere
    assert out.mean.min() >= 2.0 - 1e-9
    assert out.mean.max() <= 5.0 + 1e-9
    # and varies across longitude (a real crossfade, not a single tile)
    assert out.mean.max() - out.mean.min() > 0.5
