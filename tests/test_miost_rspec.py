"""Tests for ``miost_rspec`` (plan Task 2 — the R parameterization).

Each test names the concrete bug it catches; expected values hand-computed.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from sverdrup.core.grid import GridSpec
from sverdrup.core.parameters import ConstantProvider
from sverdrup.methods.miost import Miost
from sverdrup.methods.miost_basis import R_REF
from sverdrup.methods.miost_error_basis import mission_hash_ints
from sverdrup.methods.miost_rspec import RSpec

_FOUR = {"alg": 0.1, "h2g": 0.2, "j2g": -0.3, "j2n": 0.4}
_GRID = GridSpec.lonlat(np.linspace(296.0, 304.0, 9), np.linspace(34.0, 42.0, 9))
_PARAMS = ConstantProvider(
    {"spacing_alpha": 1.5, "log10_rho": 1.3, "q_slope": 2.0, "l_t_days": 10.0}
)


def test_delta_s3a_is_derived_negative_sum() -> None:
    # Hand: -(0.1 + 0.2 - 0.3 + 0.4) = -0.4 exactly (gauge mean(delta)=0).
    # Bug caught: sign flip, or s3a treated as an independent zero.
    r = RSpec(deltas=_FOUR)
    assert r.delta_s3a == -0.4
    assert r.all_deltas["s3a"] == -0.4
    assert math.isclose(sum(r.all_deltas.values()), 0.0, abs_tol=1e-15)


def test_s3a_as_input_is_refused() -> None:
    # Bug caught: accepting delta_s3a re-injects the flat direction the
    # contrast chart exists to remove (spec §4: s3a NEVER an input).
    with pytest.raises(ValueError, match="s3a"):
        RSpec(deltas={**_FOUR, "s3a": 0.0})


def test_partial_delta_keys_are_refused() -> None:
    # Bug caught: a missing mission silently defaulting to delta=0 — a
    # 3-dim sweep masquerading as the pre-registered 4-dim one.
    with pytest.raises(ValueError, match="j2n"):
        RSpec(deltas={"alg": 0.1, "h2g": 0.2, "j2g": -0.3})


def test_lambda_half_set_is_refused() -> None:
    # Bug caught: one Lambda set and one None slipping through as a
    # half-configured mode block (neither column-absent nor active).
    with pytest.raises(ValueError, match="log_lam"):
        RSpec(deltas=_FOUR, log_lam_bias=-3.5, log_lam_tilt=None)


def test_sigma2_lookup_is_value_keyed_not_positional() -> None:
    # sigma2_m = R_REF * exp(delta_m), looked up by MISSION HASH: querying
    # [s3a, alg] (an order unlike any construction order) must return
    # [R_REF*e^-0.4, R_REF*e^0.1] (hand).
    # Bug caught: positional lookup into a list instead of identity lookup.
    r = RSpec(deltas=_FOUR)
    got = r.sigma2_for(mission_hash_ints(np.asarray(["s3a", "alg"])))
    expected = [R_REF * math.exp(-0.4), R_REF * math.exp(0.1)]
    np.testing.assert_allclose(got, expected, rtol=1e-15)


def test_sigma2_unknown_mission_hash_refused() -> None:
    # Bug caught: an unknown mission (the j3-leak class) silently getting
    # R_REF instead of refusing.
    r = RSpec(deltas=_FOUR)
    with pytest.raises(ValueError, match="hash"):
        r.sigma2_for(mission_hash_ints(np.asarray(["j3"])))


def test_scalar_config_sigma2_is_exactly_r_ref() -> None:
    # exp(0.0) == 1.0 exactly in IEEE754: the scalar restriction must be
    # BIT-equal to the scalar era, not merely close.
    # Bug caught: a rescaling detour (log/exp round trip) perturbing R.
    r = RSpec(deltas={k: 0.0 for k in _FOUR})
    got = r.sigma2_for(mission_hash_ints(np.asarray(["alg", "s3a"])))
    assert got.tolist() == [R_REF, R_REF]


def test_scalar_params_key_backward_identical() -> None:
    # The scalar config's params_key must EQUAL the documented scalar-era
    # format (seam f) — assembled here from its public components.
    # Bug caught: the rspec extension leaking text into scalar keys, which
    # would orphan every cached scalar-era window solve (cache lineage).
    m = Miost()
    spec = m._spec_from(_PARAMS, _GRID)
    rho = 10.0 ** float(_PARAMS.resolve("log10_rho", _GRID))
    q_slope = float(_PARAMS.resolve("q_slope", _GRID))
    expected = (
        f"{spec.key()};rho={rho!r};q_slope={q_slope!r};"
        f"pcg_rtol={m.pcg_rtol!r};pcg_maxiter={m.pcg_maxiter};"
        f"cal={m._calibration.key()}"
    )
    assert m._params_key(_PARAMS, _GRID) == expected
    assert Miost(rspec=RSpec())._params_key(_PARAMS, _GRID) == expected


def test_augmented_params_key_distinct_and_complete() -> None:
    # Augmented configs get NEW keys carrying kind, ALL FIVE deltas
    # (including the derived s3a), both Lambda values, the basis id and
    # the segmentation version (spec §11).
    # Bug caught: rspec missing from the key -> a cached scalar-era eta
    # reused for an augmented solve (the Phase-8 stale-pin class).
    scalar_key = Miost()._params_key(_PARAMS, _GRID)
    aug = Miost(rspec=RSpec(deltas=_FOUR, log_lam_bias=-3.5, log_lam_tilt=-4.0))
    key = aug._params_key(_PARAMS, _GRID)
    assert key != scalar_key
    for frag in ("per-mission+modes", "s3a=-0.4", "-3.5", "-4.0", "seg=", "P0P1-s"):
        assert frag in key, frag


def test_structure_kind_strings() -> None:
    # Provenance kind must reflect the structure (spec §11 enum).
    # Bug caught: a modes config recorded as plain "per-mission" — the
    # provenance record would lie about what solved the window.
    assert RSpec().structure_kind == "scalar"
    assert RSpec(deltas=_FOUR).structure_kind == "per-mission"
    assert (
        RSpec(deltas=_FOUR, log_lam_bias=-3.5, log_lam_tilt=-4.0).structure_kind
        == "per-mission+modes"
    )


def test_parameter_space_gains_phase13_dims() -> None:
    # Method-level WIDE bounds (plan Task 2): delta in (-3,3), log10 Lambda
    # in (-8,-1); the four signed dims unchanged. Sweep boxes are Task-6's.
    # Bug caught: sweep dims missing from the declared space (the tuner
    # would refuse or silently ignore them), or signed boxes drifting.
    space = Miost().parameter_space()
    assert space.bounds["spacing_alpha"] == (0.5, 1.5)
    assert space.bounds["log10_rho"] == (-2.0, 3.0)
    for d in ("delta_alg", "delta_h2g", "delta_j2g", "delta_j2n"):
        assert space.bounds[d] == (-3.0, 3.0)
    for lam in ("log_lam_bias", "log_lam_tilt"):
        assert space.bounds[lam] == (-8.0, -1.0)
