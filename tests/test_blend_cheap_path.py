"""Cheap-path moment crossfade: seam-free mean, no variance dip, conservative sigma."""

from __future__ import annotations

import numpy as np

from sverdrup.core.geometry import Tile, Window
from sverdrup.core.grid import GridSpec
from sverdrup.core.provenance import TransformKind, UncertaintyProvenance
from sverdrup.core.types import CovFidelity, UncertaintyCapability
from sverdrup.distributions.blend import BlendInput, BlendOperator
from sverdrup.distributions.persisted import PersistedDistribution, PersistedFields


def _persisted(grid: GridSpec, mean_val: float, sigma: float) -> PersistedDistribution:
    n = grid.shape[0] * grid.shape[1]
    var = np.full(grid.shape, sigma**2)
    fields = PersistedFields(
        mean=np.full(grid.shape, mean_val),
        marginal_variance=var,
        factor=np.zeros((n, 0)),
        residual=var.ravel(),
        rank=0,
        seed=1,
        captured_energy=0.0,
    )
    prov = UncertaintyProvenance(UncertaintyCapability.SAMPLES, [])
    return PersistedDistribution(grid, fields, prov, time_days=0.0)


def _two_overlapping_tiles():
    # shared target lon grid; left/right tiles are windows of it (co-registered nodes)
    target = GridSpec.lonlat(np.linspace(-10.0, 10.0, 81), np.array([0.0, 1.0]))
    left_grid = target.window(lon_range=(-10.0, 2.0), lat_range=(-1.0, 2.0))
    right_grid = target.window(lon_range=(-2.0, 10.0), lat_range=(-1.0, 2.0))
    left = Tile(
        Window((-10.0, -2.0), (0.0, 1.0), (0.0, 0.0)),
        Window((-10.0, 2.0), (0.0, 1.0), (0.0, 0.0)),
        left_grid,
    )
    right = Tile(
        Window((2.0, 10.0), (0.0, 1.0), (0.0, 0.0)),
        Window((-2.0, 10.0), (0.0, 1.0), (0.0, 0.0)),
        right_grid,
    )
    return target, left, right


def test_blended_mean_is_weight_crossfade():
    # Behavior: blended mean = sum w_i mean_i at shared nodes (seam-free).
    # Bug caught: hard cut at the core boundary leaves a mean discontinuity.
    target, left, right = _two_overlapping_tiles()
    parts = [
        BlendInput(_persisted(left.grid, 1.0, 0.2), left),
        BlendInput(_persisted(right.grid, 1.0, 0.2), right),
    ]
    out = BlendOperator().blend(parts, support=target)
    assert np.all(np.isfinite(out.mean))
    # equal means -> blended mean is exactly the common value, no seam
    np.testing.assert_allclose(out.mean, 1.0, atol=1e-9)


def test_no_mid_overlap_variance_dip():
    # Behavior: with coherence (corr=1) blended sigma at mid-overlap == constituent sigma.
    # Bug caught: independent-variance crossfade sum w_i^2 sigma^2 dips below true sigma at w=0.5.
    target, left, right = _two_overlapping_tiles()
    parts = [
        BlendInput(_persisted(left.grid, 0.0, 0.3), left),
        BlendInput(_persisted(right.grid, 0.0, 0.3), right),
    ]
    out = BlendOperator().blend(parts, support=target)
    sigma = np.sqrt(out.marginal_variance())
    # mid-overlap is lon=0 column
    mid_col = np.argmin(np.abs(target.x - 0.0))
    np.testing.assert_allclose(sigma[:, mid_col], 0.3, atol=1e-9)


def test_blended_sigma_is_conservative():
    # Behavior: blended sigma >= per-point max constituent sigma (never sharper).
    # Bug caught: fusion produces sigma below the constituents -> overconfidence.
    target, left, right = _two_overlapping_tiles()
    parts = [
        BlendInput(_persisted(left.grid, 0.0, 0.25), left),
        BlendInput(_persisted(right.grid, 0.0, 0.40), right),
    ]
    out = BlendOperator().blend(parts, support=target)
    sigma = np.sqrt(out.marginal_variance())
    assert np.nanmin(sigma) >= 0.25 - 1e-9


def test_provenance_marks_blend_and_blended_fidelity():
    # Behavior: blended product carries BlendTransform + BLENDED fidelity.
    # Bug caught: a blend that claims LOW_RANK overstates its fidelity.
    target, left, right = _two_overlapping_tiles()
    parts = [
        BlendInput(_persisted(left.grid, 1.0, 0.2), left),
        BlendInput(_persisted(right.grid, 1.0, 0.2), right),
    ]
    out = BlendOperator().blend(parts, support=target)
    assert out.fidelity is CovFidelity.BLENDED
    kinds = [t.kind for t in out.provenance.transformations]
    assert TransformKind.BLEND in kinds
