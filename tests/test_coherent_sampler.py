"""Coherent sampler: member-only z_r structured + global-cell diagonal noise."""

from __future__ import annotations

import numpy as np

from sverdrup.distributions.coherent import (
    CoherentSampler,
    MemberSeededZr,
    NoiseSpec,
    diagonal_noise,
)


def test_member_seeded_zr_is_tile_independent():
    # Behavior: z_r depends on member only, so both tiles draw the same latent prefix.
    # Bug caught: seeding z_r per tile destroys structured agreement in the overlap.
    src = MemberSeededZr()
    spec = NoiseSpec(method="oi", params_key="p", lattice_step=1.0)
    a = src.draw_one(member_index=7, rank=5, noise_spec=spec)
    b = src.draw_one(member_index=7, rank=5, noise_spec=spec)
    np.testing.assert_array_equal(a, b)
    assert a.shape == (5,)


def test_diagonal_noise_is_coherent_per_global_cell():
    # Behavior: same global cell + member -> identical diagonal white noise, any tile.
    # Bug caught: tile-local diagonal seeding yields a hidden seam in the residual part.
    spec = NoiseSpec(method="oi", params_key="p", lattice_step=1.0)
    shared = np.array([[3.0, 4.0, 0.0]])
    from_tile_a = diagonal_noise(shared, member_index=2, noise_spec=spec)
    # same physical point reached while "solving tile B" -> same value
    from_tile_b = diagonal_noise(shared.copy(), member_index=2, noise_spec=spec)
    np.testing.assert_array_equal(from_tile_a, from_tile_b)


def test_realize_single_tile_matches_lowrank_plus_diag():
    # Behavior: a one-tile realize equals mean + B z_r + sqrt(d) z_diag.
    # Bug caught: dropping the structured term collapses spatial correlation in samples.
    rng = np.random.default_rng(0)
    ngrid, r = 12, 3
    mean = rng.standard_normal(ngrid)
    B = rng.standard_normal((ngrid, r))
    d = np.abs(rng.standard_normal(ngrid))
    sampler = CoherentSampler()
    spec = NoiseSpec(method="oi", params_key="p", lattice_step=1.0)
    pts = np.column_stack([np.arange(ngrid), np.zeros(ngrid), np.zeros(ngrid)]).astype(
        float
    )
    field = sampler.realize_one(
        mean=mean,
        factor=B,
        residual=d,
        points=pts,
        member_index=1,
        noise_spec=spec,
    )
    z_r = MemberSeededZr().draw_one(1, r, spec)
    z_d = diagonal_noise(pts, 1, spec)
    np.testing.assert_allclose(field, mean + B @ z_r + np.sqrt(d) * z_d, rtol=1e-12)


def test_diagonal_noise_differs_across_cells():
    # Behavior: distinct global cells get distinct white-noise draws.
    # Bug caught: a constant diagonal draw would erase the residual texture entirely.
    spec = NoiseSpec(method="oi", params_key="p", lattice_step=1.0)
    pts = np.array([[0.5, 0.5, 0.0], [10.5, 0.5, 0.0], [0.5, 10.5, 0.0]])
    vals = diagonal_noise(pts, member_index=3, noise_spec=spec)
    assert np.unique(vals).size == 3
