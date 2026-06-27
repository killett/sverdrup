"""Stage-B core-authoritative coherent sampler gate (strict-min, rule i)."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("sksparse")

from sverdrup.distributions.blend import partition_weights  # noqa: E402
from sverdrup.distributions.coherent import _core_owner_of_points  # noqa: E402
from tests.unit._tree_gate import make_natl60  # noqa: E402


def test_core_ownership_matches_weights():
    fix = make_natl60(2, 2)
    pts = fix.pts
    owner = _core_owner_of_points(fix.parts, pts, 2.0)
    assert (owner >= 0).all(), "every output node must have a core owner"
    w = partition_weights([p.tile for p in fix.parts], pts)  # (T, n)
    assert np.array_equal(owner, np.argmax(w, axis=0)), (
        "core-ownership tie-break must match partition_weights' argmax at every node"
    )
