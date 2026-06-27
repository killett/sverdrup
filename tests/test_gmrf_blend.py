"""GMRF blend: kriging-conditioning coherence driver + (Task 9) seam-free blended product.

The Stage-B user-gate (Task 9) is ``test_gmrf_blend_cross_seam_firstdifference_parity``: the
contracted assertion is that the blended product's cross-seam gradient (``firstdifference``)
variance is NOT under-dispersed vs the single-tile reference — the property the disproven
native-shared-w driver failed at −0.51 (≈0.49 ratio). A red here is spec-§8 escalation, not a
tolerance to loosen.
"""

from __future__ import annotations

from typing import Any, cast

import numpy as np
import pytest

pytest.importorskip("sksparse")  # noqa: E402

from sverdrup.core.geometry import Tile, Window  # noqa: E402
from sverdrup.core.grid import GridSpec  # noqa: E402
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow  # noqa: E402
from sverdrup.core.parameters import ConstantProvider  # noqa: E402
from sverdrup.core.seeding import derive_seed  # noqa: E402
from sverdrup.distributions.blend import BlendInput, partition_weights  # noqa: E402
from sverdrup.distributions.coherent import (  # noqa: E402
    GmrfKrigingSolve,
    NoiseSpec,
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
    # Stage B (redesign): the sparse-precision driver is the spanning-tree hand-forward one.
    # Chain behaviour stays pinned by the kept GmrfKrigingSolve tests (kriging_driver/oracle).
    from sverdrup.distributions.coherent import GmrfTreeKrigingSolve

    assert isinstance(select_driver("sparse-precision"), GmrfTreeKrigingSolve)


def test_single_tile_member_is_native_draw():
    # Behavior: one GMRF tile's coherent member == mean + L^-T w (kriging is a no-op with no
    #   shared boundary), with w the per-tile white keyed by sweep position x member.
    # Bug caught: a QR-basis trick (low-rank emulation) instead of native precision sampling.
    grid = GridSpec.lonlat(np.linspace(0.0, 6.0, 7), np.linspace(0.0, 6.0, 7))
    pd = _gmrf_pd(grid)
    tile = Tile(Window((0, 6), (0, 6), (0, 0)), Window((0, 6), (0, 6), (0, 0)), grid)
    parts = [BlendInput(pd, tile)]
    pts = grid.points(2.0)
    noise = NoiseSpec(method="gmrf", params_key="p", lattice_step=0.5)
    w = partition_weights([tile], pts)
    got = GmrfKrigingSolve().crossfaded_member(parts, pts, w, 4, noise)
    seed = derive_seed(noise.method, noise.params_key, "gmrf-tile:0", 4)
    white = np.random.default_rng(seed).standard_normal(pts.shape[0])
    expected = pd.fields.mean.ravel() + pd._factor_obj().sample(white)
    np.testing.assert_allclose(got, expected, rtol=1e-9)


def _gmrf_region_inputs(tmp_path_factory, mode="OSSE"):
    # NOTE (numerical headroom): this tiny data-poor fixture's GMRF prior is near-degenerate —
    # the oscillatory mode of the (κ²−Δ)² stencil on a small grid drives adjacent nodes to
    # ~ −0.998 correlation (present IDENTICALLY in the single-tile reference, not a seam artifact).
    # The joint-covariance gates compare blend-vs-reference structure, so they are robust to it;
    # but if a joint check ever flakes, suspect this grid degeneracy FIRST, not the kriging sampler.
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


def _adjacent_lon_fdvar(samples, shape):
    """Per adjacent lon pair, the empirical firstdifference variance ``Var(x_a − x_b)``.

    ``samples`` is ``(M, ny*nx)`` row-major coherent draws; adjacent lon pairs straddle the
    tile seams. Sample-based (M draws) rather than the 256-member ``covariance()`` so the gate
    ratio is tight and reproducible (deterministic given the draw seed).
    """
    ny, nx = shape
    out = {}
    for j in range(ny):
        for i in range(nx - 1):
            a = j * nx + i
            out[(j, i)] = float(np.var(samples[:, a] - samples[:, a + 1]))
    return out


def test_gmrf_blend_cross_seam_firstdifference_parity(tmp_path_factory):
    # STAGE-B USER GATE (Task 9). Behavior: the 3-tile blended product's cross-seam gradient
    #   (firstdifference) variance is NOT under-dispersed vs the single-tile reference — the
    #   coherence the kriging-conditioning sampler delivers across distinct tiles.
    # Bug caught: the disproven native-shared-w driver left overlapping tiles ~independent, so
    #   cross-seam gradient variance collapsed to ~0.49 of the reference (§5.3.1 measured −0.51).
    #   A red is spec-§8 escalation (a real coherence defect), never a tolerance to loosen.
    from sverdrup.application.pipeline import run_tiled_pipeline

    ref = run_tiled_pipeline(_gmrf_region_inputs(tmp_path_factory), _partition(1))[0][0]
    multi = run_tiled_pipeline(_gmrf_region_inputs(tmp_path_factory), _partition(3))[0][
        0
    ]
    sr = ref.sample(3000, seed=1).reshape(3000, -1)
    sm = multi.sample(3000, seed=1).reshape(3000, -1)
    fr = _adjacent_lon_fdvar(sr, ref.grid.shape)
    fm = _adjacent_lon_fdvar(sm, multi.grid.shape)
    ratios = np.array([fm[k] / fr[k] for k in fr if fr[k] > 0])
    # conservative direction: no adjacent-pair gradient variance is under-dispersed. The old
    # driver bottomed out near 0.49 at the seams; 0.8 sits far above that and below MC slack.
    assert ratios.min() >= 0.8, (
        f"cross-seam gradient under-dispersed: min ratio {ratios.min()}"
    )
    # parity holds (coherent, not grossly inflated — finite-halo seams add mild conservatism).
    assert ratios.max() <= 2.5, (
        f"cross-seam gradient grossly inflated: max ratio {ratios.max()}"
    )


def test_gmrf_blend_reproduces_reference_correlation_structure(tmp_path_factory):
    # Supporting check (member-correlation, demoted from the old contract): the 3-tile blend
    #   reproduces the single-tile reference's adjacent-node correlation everywhere — no seam
    #   decorrelation. (Direct positive-corr probing is uninformative here: this tiny data-poor
    #   fixture's GMRF prior is itself oscillatory, so the reference has strong ± adjacent
    #   correlations the blend must match, not blanket positivity.)
    # Bug caught: the native-shared-w driver decorrelated overlapping tiles, so blend corr would
    #   drop toward 0 at seams while the reference keeps the field's ±0.5–1.0 dependence.
    from sverdrup.application.pipeline import run_tiled_pipeline

    ref = run_tiled_pipeline(_gmrf_region_inputs(tmp_path_factory), _partition(1))[0][0]
    multi = run_tiled_pipeline(_gmrf_region_inputs(tmp_path_factory), _partition(3))[0][
        0
    ]
    sr = ref.sample(3000, seed=1).reshape(3000, -1)
    sm = multi.sample(3000, seed=1).reshape(3000, -1)
    ny, nx = multi.grid.shape
    devs = [
        abs(
            np.corrcoef(sm[:, j * nx + i], sm[:, j * nx + i + 1])[0, 1]
            - np.corrcoef(sr[:, j * nx + i], sr[:, j * nx + i + 1])[0, 1]
        )
        for j in range(ny)
        for i in range(nx - 1)
    ]
    assert max(devs) <= 0.25, (
        f"blend departs from reference correlation structure: {max(devs)}"
    )


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
