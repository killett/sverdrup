"""The real structured-coherence gate: cross-seam derivative shows no variance inflation."""

from __future__ import annotations

import numpy as np

from sverdrup.distributions.blend import BlendInput, BlendOperator
from tests.test_blend_general_path import _persisted_struct, _tiles


def _xdiff(field2d):
    return np.diff(field2d, axis=1)


def test_cross_seam_derivative_no_variance_inflation():
    # Behavior: ensemble first-difference variance across the seam ~ interior variance.
    # Bug caught: member-only z_r basis-orientation mismatch inflates the velocity field
    #   exactly at the seam, invisible to the marginal no-dip test.
    target, left, right = _tiles()
    parts = [
        BlendInput(_persisted_struct(left.grid, 1), left),
        BlendInput(_persisted_struct(right.grid, 2), right),
    ]
    out = BlendOperator().blend(parts, support=target, lattice_step=0.25)
    s = out.sample(m=256, seed=5)[:, 0, :]  # (m, nx)
    dvar = _xdiff(s).var(axis=0)  # variance of x-difference per column
    seam_col = np.argmin(np.abs(target.x - (-2.0)))
    interior = np.median(dvar[5:15])
    seam = dvar[seam_col]
    assert seam <= 2.0 * interior + 1e-9, (
        "cross-seam derivative variance inflated -> structured-coherence failure; "
        "swap MemberSeededZr -> SpatialSqrtStructured and escalate to owner (design 5c/8)."
    )
