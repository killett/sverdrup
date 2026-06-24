"""Stage-A gate: regional multi-tile blend == single-tile reference, no seam, conservative.

USER-ORDERED GATE. The assertions here (rel-L2, conservative sigma, no-seam, no-dip,
cross-seam derivative, withheld-eval scores, provenance) are the contract. A failure is a
spec-section-8 escalation (bound-and-record residual unacceptable), never a tolerance loosen.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from sverdrup.adapters.executor_dask import ExecutorConfig
from sverdrup.adapters.odc.fixtures import FixtureSource
from sverdrup.application.pipeline import PipelineInputs, run_tiled_pipeline
from sverdrup.application.splits import make_splits
from sverdrup.application.tiling import LonLatPartition, ScaleAwareHalo
from sverdrup.application.withholding import (
    Assignment,
    LeaveOneMissionOut,
    PerMissionTemporalFraction,
)
from sverdrup.core.evaluation import ContextKey
from sverdrup.core.parameters import ConstantProvider
from sverdrup.core.provenance import KnownBias, TransformKind
from sverdrup.core.types import CovFidelity

_REGION: dict[str, Any] = dict(
    lon_range=(-64.0, -56.0),
    lat_range=(34.0, 42.0),
    grid_resolution_deg=1.0,
    time_range=(0.0, 5.0),
    output_times=[2.0],
    params={"length_scale": 300.0, "time_scale": 10.0, "variance": 0.05},
    executor=ExecutorConfig(n_processes=2, threads_per_process=1),
    rank=20,
)
# Wide (300 km) halos via a constant correlation-length provider for the partition geometry.
_HALO_PROV = ConstantProvider({"correlation_length": 300.0})


def _partition(n_lon: int) -> LonLatPartition:
    return LonLatPartition(
        n_lon=n_lon,
        n_lat=1,
        halo=ScaleAwareHalo(k=1.0),
        correlation_length=_HALO_PROV,
        stencil_radius_km=10.0,
    )


def _osse_inputs(tmp_path_factory):
    src = FixtureSource(
        "tests/fixtures/natl60_tiny.nc", ref_path="tests/fixtures/natl60_ref_tiny.nc"
    )
    out = tmp_path_factory.mktemp("stage_a")
    return PipelineInputs(
        mode="OSSE", method_name="oi", source=src, out_url=f"file://{out}", **_REGION
    )


def _ose_inputs(tmp_path_factory):
    src = FixtureSource("tests/fixtures/ose_tiny.nc")
    out = tmp_path_factory.mktemp("stage_a_ose")
    return PipelineInputs(
        mode="OSE", method_name="oi", source=src, out_url=f"file://{out}", **_REGION
    )


@pytest.fixture(scope="module")
def osse_ref(tmp_path_factory):
    """Single-tile (1x1) OSSE blend over the whole region — the reference."""
    return run_tiled_pipeline(_osse_inputs(tmp_path_factory), _partition(1))


@pytest.fixture(scope="module")
def osse_multi(tmp_path_factory):
    """Three overlapping regional tiles (3x1) OSSE blend."""
    return run_tiled_pipeline(_osse_inputs(tmp_path_factory), _partition(3))


@pytest.fixture(scope="module")
def ose_multi(tmp_path_factory):
    """Three overlapping regional tiles (3x1) OSE blend (withheld CryoSat-2)."""
    return run_tiled_pipeline(_ose_inputs(tmp_path_factory), _partition(3))


def test_stage_a_blend_matches_single_tile_no_seam_conservative(osse_ref, osse_multi):
    # Behavior: 3 overlapping regional tiles blended == 1-tile reference, no seam, sigma>=ref.
    # Bug caught: any fuse/double-count (sharper sigma), or a hard cut leaving a seam.
    ref = osse_ref[0][0]
    multi = osse_multi[0][0]
    rel_l2 = np.linalg.norm(multi.mean - ref.mean) / np.linalg.norm(ref.mean)
    assert rel_l2 <= 0.05, (
        f"multi-tile mean diverged from single-tile reference: {rel_l2}"
    )
    # conservative: blended sigma never sharper than the all-data single-tile reference
    dsig = np.sqrt(multi.marginal_variance()) - np.sqrt(ref.marginal_variance())
    assert np.nanmin(dsig) >= -1e-9, (
        f"blended sigma below reference (overconfident): {np.nanmin(dsig)}"
    )
    # no seam in the mean: the blend introduces no gradient steeper than the all-data
    # reference already has (a hand-cut would spike the gradient at a core boundary).
    # Compared to the reference, so genuine SLA fronts (present in both) do not trip it.
    gref = np.abs(np.diff(ref.mean, axis=1))
    gmul = np.abs(np.diff(multi.mean, axis=1))
    assert np.nanmax(gmul) <= 1.5 * np.nanmax(gref) + 1e-9, (
        "seam: blend steepened the gradient"
    )


def test_stage_a_integrated_no_dip_and_cross_seam(osse_multi):
    # Behavior: on the integrated product the coherent samples reproduce the analytic
    #   (cheap-path) marginal variance everywhere (Task-7 invariant), and the cross-seam
    #   derivative is not inflated at the core boundaries (Task-8 invariant).
    # Bug caught: independent per-tile noise -> sampled variance dips below the analytic
    #   corr=1 crossfade in the overlap, and the d/dx variance spikes at the seam.
    multi = osse_multi[0][0]
    analytic = multi.marginal_variance()
    s = multi.sample(m=512, seed=5)
    sampled = s.var(axis=0)
    # Task-7 on the integrated product, TWO-SIDED: |sampled - analytic|/analytic within the
    # Monte-Carlo tolerance bounds BOTH overconfidence (sampled > analytic) and under-
    # dispersion (the basis-orientation dip). The shared-overlap-basis (Lowdin) structured
    # driver makes the coherent samples reproduce the cheap-path variance (rel ~0.03 here);
    # the pre-fix member-only-z_r driver gave rel ~0.45 and growing with k.
    rel = np.abs(sampled - analytic) / np.clip(analytic, 1e-9, None)
    assert np.median(rel) <= 0.15, (
        f"sampled variance diverges from analytic: {np.median(rel)}"
    )
    # Task-8 on the integrated product: x-difference variance at the true seam columns
    #   is not inflated vs the interior.
    dvar = np.diff(s, axis=2).var(axis=0)  # (ny, nx-1)
    xcols = 0.5 * (multi.grid.x[:-1] + multi.grid.x[1:])
    seam_idx = [int(np.argmin(np.abs(xcols - sl))) for sl in (-61.333, -58.667)]
    seam = float(np.median(np.stack([dvar[:, i] for i in seam_idx])))
    interior = float(np.median(dvar))
    assert seam <= 3.0 * interior, (
        f"cross-seam derivative inflated: {seam} vs {interior}"
    )


def test_stage_a_withheld_eval_osse_and_ose(osse_multi, ose_multi):
    # Behavior: withheld points scored in OSSE (vs truth) and OSE (vs withheld c2);
    #   OSE scores come from the blended eval-point predictives, not the gridded blend.
    # Bug caught: reconstructing eval from the grid (invariant 4/6 violation), or NaN scores.
    osse_scores = osse_multi[1]
    assert np.isfinite(osse_scores["rmse"])
    assert np.isfinite(osse_scores["reduced_chi2"])
    assert np.isfinite(osse_scores["coverage_1sigma"])

    ose_scores = ose_multi[1]
    # OSE used withheld CryoSat-2, never the gridded truth
    assert ContextKey.TRUTH.name not in ose_scores["context_keys"]
    assert ContextKey.WITHHELD_OBS.name in ose_scores["context_keys"]
    assert np.isfinite(ose_scores["rmse"])
    assert np.isfinite(ose_scores["reduced_chi2"])


def test_stage_a_provenance_and_withholding_exemplars(osse_multi):
    # Behavior: BlendTransform (conservative halo residual, BLENDED fidelity) present;
    #   both withholding exemplars run; random point holdout rejected.
    # Bug caught: a blend that overstates fidelity, or an autocorrelation-leaking split.
    multi = osse_multi[0][0]
    assert multi.fidelity is CovFidelity.BLENDED
    assert multi.provenance.transformations[-1].kind is TransformKind.BLEND
    assert (
        multi.provenance.transformations[-1].known_bias
        is KnownBias.CONSERVATIVE_HALO_RESIDUAL
    )

    obs = FixtureSource("tests/fixtures/ose_tiny.nc").window(
        lon_range=_REGION["lon_range"],
        lat_range=_REGION["lat_range"],
        time_range=_REGION["time_range"],
    )
    loo = LeaveOneMissionOut(validation_missions=["c2"]).split(obs)
    assert (loo.assignment == Assignment.VALIDATION).any()
    # buffer fraction sized for the tiny fixture (few obs/mission) so the band is non-empty;
    # the disjoint-buffer invariant itself is proven at n=100 in tests/test_withholding.py
    pmtf = PerMissionTemporalFraction(train=0.6, buffer=0.2, validation=0.2).split(obs)
    assert (pmtf.assignment == Assignment.BUFFER_DISCARD).any()

    with pytest.raises(ValueError, match="[Rr]andom point holdout"):
        make_splits(obs, by="random_point")
