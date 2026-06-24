"""General path: coherent-sample crossfade is continuous across the seam."""

from __future__ import annotations

import numpy as np

from sverdrup.core.geometry import Tile, Window
from sverdrup.core.grid import GridSpec
from sverdrup.core.provenance import UncertaintyProvenance
from sverdrup.core.types import UncertaintyCapability
from sverdrup.distributions.blend import BlendInput, BlendOperator
from sverdrup.distributions.persisted import PersistedDistribution, PersistedFields


def _persisted_struct(grid, seed):
    ny, nx = grid.shape
    n = ny * nx
    # smooth low-rank structure shared in form across tiles (wide-halo agreement)
    lon = grid.points(0.0)[:, 0]
    B = np.column_stack([np.cos(lon * 0.3), np.sin(lon * 0.2)]) * 0.2
    d = np.full(n, 0.01)
    fields = PersistedFields(
        mean=np.zeros((ny, nx)),
        marginal_variance=(np.sum(B**2, axis=1) + d).reshape(ny, nx),
        factor=B,
        residual=d,
        rank=2,
        seed=seed,
        captured_energy=1.0,
    )
    prov = UncertaintyProvenance(UncertaintyCapability.SAMPLES, [])
    return PersistedDistribution(grid, fields, prov, 0.0)


def _tiles():
    target = GridSpec.lonlat(np.linspace(-10, 10, 81), np.array([0.0]))
    lg = target.window(lon_range=(-10, 2), lat_range=(-1, 1))
    rg = target.window(lon_range=(-2, 10), lat_range=(-1, 1))
    left = Tile(
        Window((-10, -2), (-1, 1), (0, 0)), Window((-10, 2), (-1, 1), (0, 0)), lg
    )
    right = Tile(
        Window((2, 10), (-1, 1), (0, 0)), Window((-2, 10), (-1, 1), (0, 0)), rg
    )
    return target, left, right


def test_coherent_samples_continuous_across_seam():
    # Behavior: crossfaded coherent draws have no jump at the core boundary.
    # Bug caught: independent per-tile noise makes member fields disagree -> sample seam.
    target, left, right = _tiles()
    parts = [
        BlendInput(_persisted_struct(left.grid, 1), left),
        BlendInput(_persisted_struct(right.grid, 2), right),
    ]
    out = BlendOperator().blend(parts, support=target, lattice_step=0.25)
    s = out.sample(m=64, seed=99)  # (64, 1, 81)
    field = s[:, 0, :]
    seam_col = np.argmin(np.abs(target.x - (-2.0)))  # left core boundary
    jump_seam = (field[:, seam_col + 1] - field[:, seam_col]).std()
    jump_interior = (field[:, 10] - field[:, 9]).std()
    assert jump_seam < 3.0 * jump_interior + 1e-6


def test_blend_stores_noise_spec_and_sample_shape():
    # Behavior: blend stores a NoiseSpec and sample() returns (m, ny, nx).
    # Bug caught: a missing NoiseSpec makes coherent sampling impossible downstream.
    target, left, right = _tiles()
    parts = [
        BlendInput(_persisted_struct(left.grid, 1), left),
        BlendInput(_persisted_struct(right.grid, 2), right),
    ]
    out = BlendOperator().blend(parts, support=target, lattice_step=0.25)
    s = out.sample(m=8, seed=1)
    assert s.shape == (8, 1, 81)


def test_covariance_returns_crossfaded_sample_covariance():
    # Behavior: covariance(a, b) returns a finite, symmetric-on-diagonal sample cov.
    # Bug caught: a NotImplementedError here breaks every derived-quantity read.
    target, left, right = _tiles()
    parts = [
        BlendInput(_persisted_struct(left.grid, 1), left),
        BlendInput(_persisted_struct(right.grid, 2), right),
    ]
    out = BlendOperator().blend(parts, support=target, lattice_step=0.25)
    a = np.array([[-3.0, 0.0, 0.0], [3.0, 0.0, 0.0]])
    cov = out.covariance(a, a)
    assert cov.shape == (2, 2)
    assert np.all(np.isfinite(cov))
    assert np.all(np.diag(cov) > 0)
