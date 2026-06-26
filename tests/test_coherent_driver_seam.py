"""CoherentMemberDriver seam: low-rank driver reproduces the inlined _coherent_member."""

from __future__ import annotations

from typing import Any, cast

import numpy as np

from sverdrup.distributions.blend import BlendInput, partition_weights
from sverdrup.distributions.coherent import (
    LowRankSharedBasis,
    NoiseSpec,
    coherent_structured_field,
    diagonal_noise,
    select_driver,
)
from tests.test_blend_general_path import _persisted_struct, _tiles


def test_select_driver_lowrank():
    # Behavior: the "lowrank+diag" representation selects the shared-basis driver.
    # Bug caught: a missing/renamed tag silently falls back to the wrong driver.
    assert isinstance(select_driver("lowrank+diag"), LowRankSharedBasis)


def test_lowrank_driver_matches_inlined_member():
    # Behavior: the relocated driver yields the byte-identical coherent member the inlined
    #   _coherent_member produced (mean crossfade + shared-basis struct + coherent diagonal).
    # Bug caught: any drift in the relocation changes Stage-A blend samples -> red gate.
    target, left, right = _tiles()
    parts = [
        BlendInput(_persisted_struct(left.grid, 1), left),
        BlendInput(_persisted_struct(right.grid, 2), right),
    ]
    pts = target.points(0.0)
    noise = NoiseSpec(method="oi", params_key="p", lattice_step=0.25)
    w = partition_weights([p.tile for p in parts], pts)

    # reference: the exact arithmetic the pre-refactor _coherent_member ran
    from sverdrup.distributions.coherent import _nearest

    means = np.zeros((2, pts.shape[0]))
    sqd = np.zeros((2, pts.shape[0]))
    cols = []
    for i, p in enumerate(parts):
        d = cast(Any, p.distribution)
        idx = _nearest(d.grid, pts, d.time_days)
        means[i] = d.fields.mean.ravel()[idx]
        cols.append(d.fields.factor[idx] * (w[i] > 0)[:, None])
        sqd[i] = np.sqrt(d.fields.residual[idx])
    ref = (
        (w * means).sum(axis=0)
        + coherent_structured_field(cols, w, 4, noise)
        + (w * sqd).sum(axis=0) * diagonal_noise(pts, 4, noise)
    )

    got = LowRankSharedBasis().crossfaded_member(parts, pts, w, 4, noise)
    np.testing.assert_allclose(got, ref, rtol=1e-12)
