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


class _FixedZr:
    """An injected structured source returning a hand-chosen latent."""

    def __init__(self, z: list[float]) -> None:
        self.z = np.asarray(z, dtype=float)
        self.calls: list[tuple[int, int]] = []

    def draw_one(
        self, member_index: int, rank: int, noise_spec: NoiseSpec
    ) -> np.ndarray:
        self.calls.append((member_index, rank))
        return self.z[:rank]

    def draw(self, member_index, parts, support, noise_spec):  # protocol conformance
        return [self.z for _ in parts]


def test_realize_one_uses_the_injected_structured_source():
    # Behavior: the latent z_r comes from the sampler's OWN structured source.
    # Bug caught (hygiene P1-#4): realize_one hardcoded MemberSeededZr().draw_one,
    # ignoring self.structured — the design-5c/8 swap seam was dead on this path,
    # latent only while the default equalled the hardcoded source.
    B = np.array([[1.0, 0.0], [0.0, 2.0], [1.0, 1.0]])
    src = _FixedZr([3.0, -1.0])
    sampler = CoherentSampler(structured=src)
    spec = NoiseSpec(method="oi", params_key="p", lattice_step=1.0)
    pts = np.array([[0.5, 0.5, 0.0], [1.5, 0.5, 0.0], [2.5, 0.5, 0.0]])
    field = sampler.realize_one(
        mean=np.zeros(3),
        factor=B,
        residual=np.zeros(3),  # isolate the structured term
        points=pts,
        member_index=4,
        noise_spec=spec,
    )
    # by hand: B @ [3, -1] = [3, -2, 2]
    np.testing.assert_allclose(field, [3.0, -2.0, 2.0], rtol=0, atol=1e-15)
    assert src.calls == [(4, 2)]
