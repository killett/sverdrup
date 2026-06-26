"""Degradation path: perturb-ensemble driver through the tiled blend (Task 10).

The degradation driver is the DELIBERATELY-INCOHERENT one. Its contract is the OPPOSITE of the
GMRF kriging gate: per-tile members are independent, so cross-tile coherence is NOT guaranteed —
the blend must RECORD that loss in provenance and keep the mean continuous (no silent seam), and
the reported marginal stays a conservative upper bound while the sampler is honestly
under-dispersed. It must NOT be held to the coherence bar the GMRF blend meets.
"""

from __future__ import annotations

import numpy as np

from sverdrup.adapters.executor_dask import ExecutorConfig
from sverdrup.adapters.odc.fixtures import FixtureSource
from sverdrup.application.pipeline import PipelineInputs, run_tiled_pipeline
from sverdrup.application.tiling import LonLatPartition, ScaleAwareHalo
from sverdrup.core.parameters import ConstantProvider
from sverdrup.core.provenance import KnownBias
from sverdrup.distributions.coherent import PerturbEnsembleDegradation, select_driver


def _inputs(tmp_path_factory, n_lon):
    src = FixtureSource(
        "tests/fixtures/natl60_tiny.nc", ref_path="tests/fixtures/natl60_ref_tiny.nc"
    )
    out = tmp_path_factory.mktemp("degrade")
    inp = PipelineInputs(
        mode="OSSE",
        method_name="trivial",
        source=src,
        out_url=f"file://{out}",
        lon_range=(-64.0, -56.0),
        lat_range=(34.0, 42.0),
        grid_resolution_deg=1.0,
        time_range=(0.0, 5.0),
        output_times=[2.0],
        params={},
        executor=ExecutorConfig(n_processes=2, threads_per_process=1),
        rank=20,
    )
    part = LonLatPartition(
        n_lon=n_lon,
        n_lat=1,
        halo=ScaleAwareHalo(k=1.0),
        correlation_length=ConstantProvider({"correlation_length": 300.0}),
        stencil_radius_km=10.0,
    )
    return inp, part


def test_select_driver_perturb_ensemble():
    assert isinstance(select_driver("perturb-ensemble"), PerturbEnsembleDegradation)


def test_degradation_runs_and_records_coherence_loss(tmp_path_factory):
    # Behavior: the trivial method blends end-to-end through the degradation driver and the
    #   coherence LOSS is recorded in provenance (DEGRADED_COHERENCE) — the flag, not a silent
    #   pretence of coherence. This is THE degradation contract.
    # Bug caught: the degradation path stays contracted-but-unexercised (the Phase-2 gap), or a
    #   degraded blend masquerades as coherent with no provenance flag.
    inp, part = _inputs(tmp_path_factory, 3)
    blends, scores = run_tiled_pipeline(inp, part)
    gb = blends[0]
    assert any(
        t.known_bias is KnownBias.DEGRADED_COHERENCE
        for t in gb.provenance.transformations
    )
    assert np.isfinite(scores["rmse"])


def test_degradation_mean_has_no_silent_seam(tmp_path_factory):
    # Behavior: even degraded, the crossfaded MEAN is continuous (partition-of-unity) — the
    #   coherence loss lives in the uncertainty/samples, never as a hard-cut mean seam.
    # Bug caught: a silent seam in the mean masquerading as a coherent product.
    ref = run_tiled_pipeline(*_inputs(tmp_path_factory, 1))[0][0]
    multi = run_tiled_pipeline(*_inputs(tmp_path_factory, 3))[0][0]
    gref = np.nanmax(np.abs(np.diff(ref.mean, axis=1)))
    gmul = np.nanmax(np.abs(np.diff(multi.mean, axis=1)))
    assert gmul <= 1.5 * gref + 1e-9


def test_degradation_sampler_under_dispersed_vs_conservative_marginal(tmp_path_factory):
    # Behavior (honest defect, documented): the reported marginal stays a CONSERVATIVE upper
    #   bound on the sampled variance everywhere, and somewhere (the seams, where per-tile
    #   independent members add as w²σ² < (Σwσ)²) the sampler is genuinely under-dispersed.
    #   This is the opposite of the coherent contract — the degradation is real, not hidden.
    # Bug caught: a degradation driver that secretly matched the conservative marginal (claiming
    #   coherence it does not have), or one whose samples exceed the reported (dishonest) bound.
    multi = run_tiled_pipeline(*_inputs(tmp_path_factory, 3))[0][0]
    reported = multi.marginal_variance().ravel()
    sampled = multi.sample(3000, seed=1).reshape(3000, -1).var(axis=0)
    ok = reported > 0
    ratio = sampled[ok] / reported[ok]
    assert ratio.max() <= 1.1, (
        f"sampler exceeds the conservative marginal: {ratio.max()}"
    )
    assert ratio.min() < 0.9, (
        f"no under-dispersion — degradation hidden: min {ratio.min()}"
    )
