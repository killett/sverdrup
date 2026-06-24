"""Cheap-path variance must match sampled variance in the overlap (corr=1 invariant)."""

from __future__ import annotations

import numpy as np

from sverdrup.distributions.blend import BlendInput, BlendOperator
from tests.test_blend_general_path import _persisted_struct, _tiles


def test_cheap_and_sample_variance_agree_in_overlap():
    # Behavior: analytic (sum w sigma)^2 ~ empirical sample variance in the overlap.
    # Bug caught: structured coherence weaker than assumed (corr<1) -> the cheap path
    #   silently understates variance; this localizes that failure to the variance.
    target, left, right = _tiles()
    parts = [
        BlendInput(_persisted_struct(left.grid, 1), left),
        BlendInput(_persisted_struct(right.grid, 2), right),
    ]
    out = BlendOperator().blend(parts, support=target, lattice_step=0.25)
    cheap = out.marginal_variance()[0]
    s = out.sample(m=512, seed=7)[:, 0, :]
    emp = s.var(axis=0, ddof=1)
    overlap = (target.x >= -2.0) & (target.x <= 2.0)
    rel = np.abs(cheap[overlap] - emp[overlap]) / np.clip(cheap[overlap], 1e-9, None)
    # NOTE: stop-and-escalate gate. If this fails, do NOT loosen the tolerance — the cheap
    # path overstates coherence; escalate per design sec 5c/8 (swap the structured driver).
    assert np.nanmedian(rel) <= 0.15
