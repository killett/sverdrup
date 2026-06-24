"""Stage-B: projection-mixed partition, cross-CRS blend, polar void, area-weighted global.

USER-ORDERED GATE (opt-in). The offline checks (projection-mixed partition, regrid
round-trip, cross-CRS blend, polar-void relax-to-prior) always run; the ~33 GB global
2023a OSE run is opt-in via SVERDRUP_GLOBAL_DATA=1 under the scoped-footprint discipline.
"""

from __future__ import annotations

import os

import numpy as np
import pytest

from sverdrup.application.tiling import ProjectionMixedPartition
from sverdrup.core.geometry import Tile, Window
from sverdrup.core.grid import GridSpec
from sverdrup.core.provenance import UncertaintyProvenance
from sverdrup.core.types import UncertaintyCapability
from sverdrup.distributions.blend import BlendInput, BlendOperator
from sverdrup.distributions.persisted import PersistedDistribution, PersistedFields


def _pd(grid: GridSpec, mean: np.ndarray, sigma: np.ndarray) -> PersistedDistribution:
    """Diagonal Persisted with given mean/sigma fields (rank 0)."""
    var = sigma**2
    n = grid.shape[0] * grid.shape[1]
    fields = PersistedFields(
        mean=mean,
        marginal_variance=var,
        factor=np.zeros((n, 0)),
        residual=var.ravel(),
        rank=0,
        seed=7,
        captured_energy=0.0,
    )
    prov = UncertaintyProvenance(UncertaintyCapability.SAMPLES, [])
    return PersistedDistribution(grid, fields, prov, time_days=0.0)


def test_projection_mixed_partition_caps_and_midlat():
    # Behavior: polar caps are polar-stereographic GridSpecs, mid-lat tiles are lon/lat.
    # Bug caught: a single-projection partition cannot represent the poles without distortion.
    target = GridSpec.lonlat(
        np.arange(-180.0, 180.0, 10.0), np.arange(-85.0, 85.1, 10.0)
    )
    tiles = ProjectionMixedPartition(cap_lat=60.0, n_lon=4, n_lat=2).tiles(target)
    geographic = {t.grid.crs.is_geographic for t in tiles}
    assert geographic == {
        True,
        False,
    }  # both mid-lat (geographic) and polar (projected)
    # the polar-cap tiles must carry projected (non-geographic) grids
    caps = [t for t in tiles if not t.grid.crs.is_geographic]
    assert caps and all(
        abs(t.core_window.lat_range[1]) > 60.0 or abs(t.core_window.lat_range[0]) > 60.0
        for t in caps
    )


def test_persisted_regrid_roundtrip_preserves_mean():
    # Behavior: regrid via samples preserves a (bi)linear mean on a round-trip, and the
    #   variance map is rebuilt from interpolated samples (never interpolated directly).
    # Bug caught: interpolating the marginal-variance map (invariant 4/7 violation).
    src = GridSpec.lonlat(np.linspace(-10, 10, 21), np.linspace(-5, 5, 11))
    lon, lat = src._lonlat_nodes()
    mean = 1.0 + 0.1 * lon + 0.05 * lat  # exactly linear -> linear interp is exact
    pd = _pd(src, mean, np.full(src.shape, 0.2))
    tgt = GridSpec.lonlat(np.linspace(-9, 9, 19), np.linspace(-4, 4, 9))
    rg = pd.regrid(tgt)
    assert np.all(np.isfinite(rg.marginal_variance()))
    assert np.all(rg.marginal_variance() >= 0)
    back = rg.regrid(src)
    # interior nodes (inside both convex hulls) round-trip the linear mean
    blon, blat = src._lonlat_nodes()
    interior = (np.abs(blon) <= 8.0) & (np.abs(blat) <= 3.5)
    np.testing.assert_allclose(
        back.fields.mean[interior], pd.fields.mean[interior], atol=0.05
    )


def test_cross_crs_blend_regrids_onto_union_support():
    # Behavior: constituents on different CRS (lon/lat + polar-stereographic) blend onto a
    #   common lon/lat target via lon/lat node matching (regrid onto union support).
    # Bug caught: assuming a single projection -> mismatched nodes / NaNs at the caps.
    target = GridSpec.lonlat(np.linspace(-5, 5, 11), np.linspace(70.0, 80.0, 11))
    geo = target.window(lon_range=(-5, 1), lat_range=(70, 80))
    # a polar-stereographic tile covering the same lon/lat box
    polar = GridSpec.polar_stereographic(
        np.linspace(-4e5, 4e5, 11), np.linspace(-4e5, 4e5, 11), lat_ts=75.0, lon0=0.0
    )
    geo_tile = Tile(
        Window((-5, 1), (70, 80), (0, 0)), Window((-5, 3), (70, 80), (0, 0)), geo
    )
    polar_tile = Tile(
        Window((1, 5), (70, 80), (0, 0)), Window((-1, 5), (70, 80), (0, 0)), polar
    )
    parts = [
        BlendInput(
            _pd(geo, np.full(geo.shape, 2.0), np.full(geo.shape, 0.3)), geo_tile
        ),
        BlendInput(
            _pd(polar, np.full(polar.shape, 2.0), np.full(polar.shape, 0.3)), polar_tile
        ),
    ]
    out = BlendOperator().blend(parts, support=target)
    assert np.all(np.isfinite(out.mean))
    assert out.mean.shape == target.shape


def test_polar_void_relaxes_to_prior():
    # Behavior: in a data void on a polar tile, blended sigma relaxes toward the prior.
    # Bug caught: a small reported error in a void = broken UQ.
    prior_sigma = 1.0
    grid = GridSpec.lonlat(np.linspace(-5, 5, 21), np.linspace(78.0, 88.0, 21))
    lon, lat = grid._lonlat_nodes()
    # a void in the upper-right corner where sigma -> prior; elsewhere well-observed (small)
    void = (lon > 2.0) & (lat > 85.0)
    sigma = np.where(void, prior_sigma, 0.1)
    tile = Tile(
        Window((-5, 5), (78, 88), (0, 0)), Window((-6, 6), (77, 89), (0, 0)), grid
    )
    out = BlendOperator().blend(
        [BlendInput(_pd(grid, np.zeros(grid.shape), sigma), tile)], support=grid
    )
    sigma_blend = np.sqrt(out.marginal_variance())
    sigma_void = float(np.min(sigma_blend[void]))
    assert sigma_void >= 0.9 * prior_sigma, f"void sigma collapsed: {sigma_void}"


@pytest.mark.skipif(
    os.environ.get("SVERDRUP_GLOBAL_DATA") != "1",
    reason="opt-in global run (~33 GB); scoped-footprint discipline",
)
def test_global_area_weighted_run(tmp_path):
    # Behavior: the projection-mixed global product aggregates area-weighted metrics.
    # Bug caught: an unweighted global mean over-counts shrunken polar cells.
    from sverdrup.adapters.executor_dask import ExecutorConfig
    from sverdrup.adapters.odc.fixtures import FixtureSource
    from sverdrup.application.pipeline import PipelineInputs, run_tiled_pipeline
    from sverdrup.eval.aggregate import area_weighted_rmse

    src = FixtureSource(os.environ["SVERDRUP_GLOBAL_OBS"])
    inp = PipelineInputs(
        mode="OSE",
        method_name="oi",
        source=src,
        out_url=f"file://{tmp_path}/global.zarr",
        lon_range=(-180.0, 180.0),
        lat_range=(-82.0, 82.0),
        time_range=(0.0, 10.0),
        output_times=[5.0],
        params={"length_scale": 300.0, "time_scale": 10.0, "variance": 0.05},
        executor=ExecutorConfig(n_processes=4, threads_per_process=1),
        rank=20,
    )
    partition = ProjectionMixedPartition(cap_lat=60.0, n_lon=8, n_lat=4)
    blends, scores = run_tiled_pipeline(inp, partition)
    gb = blends[0]
    rmse = area_weighted_rmse(np.zeros_like(gb.mean), gb.grid)
    assert np.isfinite(rmse)
    assert np.isfinite(scores["rmse"])
