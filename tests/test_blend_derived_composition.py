"""FirstDifference must compose on a BlendedDistribution (it is a PredictiveDistribution)."""

from __future__ import annotations

import numpy as np

from sverdrup.derived.firstdifference import FirstDifference
from sverdrup.distributions.blend import BlendInput, BlendOperator
from tests.test_blend_general_path import _persisted_struct, _tiles


def test_firstdifference_composes_on_blended():
    # Behavior: the blend output is a real PredictiveDistribution the operators can consume.
    # Bug caught: a blend that omits covariance()/grid/time_days breaks derived composition.
    target, left, right = _tiles()
    parts = [
        BlendInput(_persisted_struct(left.grid, 1), left),
        BlendInput(_persisted_struct(right.grid, 2), right),
    ]
    blended = BlendOperator().blend(parts, support=target, lattice_step=0.25)
    diff = FirstDifference(axis="x").apply(blended)
    assert np.all(np.isfinite(diff.marginal_variance()))
    assert np.all(np.isfinite(diff.mean))
    # propagated difference variance is non-negative (Var(a)+Var(b)-2Cov(a,b) >= 0)
    assert np.all(diff.marginal_variance() >= -1e-9)
