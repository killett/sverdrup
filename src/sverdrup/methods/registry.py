"""Method registry (spec 5.2) — role-split into METHODS and SHIPPED (Phase-10 §8).

Lookup rule (spec-level): a name lives in exactly ONE table; lookups are
explicit per call site; NO fallback-chaining helper (a resolve-either helper
silently re-creates the ambiguity the split kills). Product-scoring/shipping
paths read ``SHIPPED``; tuning/search paths read ``METHODS``.
``METHODS ∩ SHIPPED == ∅`` is CI-enforced (tests/test_registry_roles.py).
"""

from __future__ import annotations

from collections.abc import Callable

from sverdrup.methods.fem import FEMMatern
from sverdrup.methods.gmrf import MaternGMRF
from sverdrup.methods.miost import Miost, shipped_miost6
from sverdrup.methods.oi import OptimalInterpolation
from sverdrup.methods.trivial import TrivialInterpolation

# Tunable-method table: bare classes only — what parameter sweeps search.
# (Typed as zero-arg factories: diagnostics may temp-register configured
# lambdas, e.g. diag_miost_ndir12.py.)
METHODS: dict[str, Callable[[], object]] = {
    "oi": OptimalInterpolation,
    "gmrf": MaternGMRF,
    "fem": FEMMatern,
    # The SEARCH entry: parameter sweeps price and score the POINT method
    # (members are generated at tuned winners only, spec 6.1 — never
    # per-trial). run_stage_miost searches this entry.
    "miost-point": Miost,
    "trivial": TrivialInterpolation,
}

# Flagship product factories: the signed, calibrated, shipping configurations.
# Phase-12 flip (owner sign-off 2026-07-18): miost6 = the six-mission
# flagship; shipped_miost5 stays importable as the five-mission
# calibration-lineage reference (its signed artifacts pin that name).
SHIPPED: dict[str, Callable[[], object]] = {
    "miost": shipped_miost6,
}
