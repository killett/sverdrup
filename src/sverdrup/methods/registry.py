"""Method registry (spec 5.2)."""

from __future__ import annotations

from sverdrup.methods.fem import FEMMatern
from sverdrup.methods.gmrf import MaternGMRF
from sverdrup.methods.oi import OptimalInterpolation
from sverdrup.methods.trivial import TrivialInterpolation

METHODS = {
    "oi": OptimalInterpolation,
    "gmrf": MaternGMRF,
    "fem": FEMMatern,
    "trivial": TrivialInterpolation,
}
