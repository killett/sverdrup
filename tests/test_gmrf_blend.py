"""GMRF blend: native shared-w coherence driver + (Task 9) seam-free blended product."""

from __future__ import annotations

from typing import Any, cast

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


def _gmrf_region_inputs(tmp_path_factory, mode="OSSE"):
    from sverdrup.adapters.executor_dask import ExecutorConfig
    from sverdrup.adapters.odc.fixtures import FixtureSource
    from sverdrup.application.pipeline import PipelineInputs

    if mode == "OSSE":
        src = FixtureSource(
            "tests/fixtures/natl60_tiny.nc",
            ref_path="tests/fixtures/natl60_ref_tiny.nc",
        )
    else:
        src = FixtureSource("tests/fixtures/ose_tiny.nc")
    out = tmp_path_factory.mktemp("gmrf")
    return PipelineInputs(
        mode=mode,
        method_name="gmrf",
        source=src,
        out_url=f"file://{out}",
        lon_range=(-64.0, -56.0),
        lat_range=(34.0, 42.0),
        grid_resolution_deg=1.0,
        time_range=(0.0, 5.0),
        output_times=[2.0],
        params={"range": 300.0, "variance": 0.05, "temporal_taper_scale": 10.0},
        executor=ExecutorConfig(n_processes=2, threads_per_process=1),
        rank=20,
    )


def _partition(n_lon):
    from sverdrup.application.tiling import LonLatPartition, ScaleAwareHalo
    from sverdrup.core.parameters import ConstantProvider

    return LonLatPartition(
        n_lon=n_lon,
        n_lat=1,
        halo=ScaleAwareHalo(k=1.0),
        correlation_length=ConstantProvider({"correlation_length": 300.0}),
        stencil_radius_km=10.0,
    )


def test_gmrf_blend_matches_single_tile_conservative(tmp_path_factory):
    # Behavior: 3-tile GMRF blend == 1-tile GMRF reference, sigma conservative, no seam.
    # Bug caught: native shared-w coherence broken -> seam or overconfident overlap.
    from sverdrup.application.pipeline import run_tiled_pipeline

    inp = _gmrf_region_inputs(tmp_path_factory)
    ref = run_tiled_pipeline(inp, _partition(1))[0][0]
    multi = run_tiled_pipeline(inp, _partition(3))[0][0]
    rel = np.linalg.norm(multi.mean - ref.mean) / np.linalg.norm(ref.mean)
    assert rel <= 0.05, f"GMRF blend diverged from single-tile reference: {rel}"
    dsig = np.sqrt(multi.marginal_variance()) - np.sqrt(ref.marginal_variance())
    assert np.nanmin(dsig) >= -1e-9, (
        f"GMRF blended sigma overconfident: {np.nanmin(dsig)}"
    )


# NOTE: test_gmrf_blend_no_variance_dip removed — it encoded the pre-amendment contract
# (sampled variance ~= conservative (Sum w sigma)^2). The Stage-B validation found the
# native shared-w driver leaves cross-seam derived quantities ~50% under-dispersed
# (phase3_scope_spec.md §5.3.1); the gate is reworked in Task 9 (kriging-conditioning sampler)
# as a cross-seam DERIVED-quantity parity check on a distinct-tiles-by-construction fixture.
# See docs/superpowers/plans/2026-06-25-phase3-task9-gmrf-kriging-sampler.md.


def test_gmrf_pipeline_osse_and_ose(tmp_path_factory):
    # Behavior: accuracy + calibration fire on the GMRF blended product, OSSE and OSE.
    # Bug caught: a representation that can't score (NaN), or OSE leaking truth.
    from sverdrup.application.pipeline import run_tiled_pipeline
    from sverdrup.core.evaluation import ContextKey

    osse = run_tiled_pipeline(
        _gmrf_region_inputs(tmp_path_factory, "OSSE"), _partition(3)
    )
    assert np.isfinite(osse[1]["rmse"])
    assert np.isfinite(osse[1]["reduced_chi2"])
    assert np.isfinite(osse[1]["coverage_1sigma"])
    ose = run_tiled_pipeline(
        _gmrf_region_inputs(tmp_path_factory, "OSE"), _partition(3)
    )
    assert ContextKey.TRUTH.name not in ose[1]["context_keys"]
    assert np.isfinite(ose[1]["rmse"])


def test_gmrf_blend_provenance_and_first_class(tmp_path_factory):
    # Behavior: blended GMRF is BLENDED with a BLEND transform; constituents stay sparse-precision.
    # Bug caught: GMRF silently reduced to low-rank somewhere in the pipeline.
    from sverdrup.application.pipeline import run_tiled_pipeline
    from sverdrup.core.provenance import TransformKind
    from sverdrup.core.types import CovFidelity

    inp = _gmrf_region_inputs(tmp_path_factory)
    blends, _ = run_tiled_pipeline(inp, _partition(3))
    gb = blends[0]
    assert gb.fidelity is CovFidelity.BLENDED
    assert any(t.kind is TransformKind.BLEND for t in gb.provenance.transformations)
    assert (
        cast(Any, gb._parts[0].distribution).fields.sampler_spec == "sparse-precision"
    )
