"""Method registry (spec 5.2)."""

from __future__ import annotations

from sverdrup.methods.fem import FEMMatern
from sverdrup.methods.gmrf import MaternGMRF
from sverdrup.methods.miost import Miost, shipped_miost
from sverdrup.methods.oi import OptimalInterpolation
from sverdrup.methods.trivial import TrivialInterpolation

METHODS = {
    "oi": OptimalInterpolation,
    "gmrf": MaternGMRF,
    "fem": FEMMatern,
    # CAPABILITY FLIP (Task-19 gate, signed off 2026-07-07): the registered
    # miost is the SHIPPED SAMPLES-native ensemble product; tuning sweeps
    # must search with a POINT-configured Miost() (see shipped_miost docs).
    "miost": shipped_miost,
    # The SEARCH entry: parameter sweeps price and score the POINT method
    # (members are generated at tuned winners only, spec 6.1 — never
    # per-trial). run_stage_miost searches this entry.
    "miost-point": Miost,
    "trivial": TrivialInterpolation,
}
