"""LatitudeField + superseded LatitudeVaryingProvider (Phase-10 Task 2; spec §2).

Bugs caught per test: wrong v normalization (center/scale drift from
(lat-38)/5); the exp link applied twice (or not at all); params_key
collisions between coefficient sets; hull clamp not giving constant
continuation; resolve returning the wrong type per name class.
Expected values are hand-computed from the named forms, never from the
implementation.
"""

from __future__ import annotations

import numpy as np

from sverdrup.core.parameters import LatitudeField, LatitudeVaryingProvider


def test_exp_quad_hand_computed() -> None:
    # v = (lat-38)/5 -> lat 33, 38, 43 give v = -1, 0, +1 (hand).
    # exp(c0 + c1*v + c2*v^2) at c=(0.1, 0.5, -0.3):
    #   v=-1: 0.1-0.5-0.3; v=0: 0.1; v=+1: 0.1+0.5-0.3 (hand).
    f = LatitudeField("exp-quad", (0.1, 0.5, -0.3))
    lat = np.array([33.0, 38.0, 43.0])
    expected = np.exp(np.array([0.1 - 0.5 - 0.3, 0.1, 0.1 + 0.5 - 0.3]))
    np.testing.assert_allclose(f.at(lat), expected, rtol=1e-15)


def test_exp_linear_mult_hand_computed() -> None:
    # exp(l1*v) at l1=-0.2: lat 33 (v=-1) -> exp(+0.2); lat 43 (v=+1) -> exp(-0.2).
    f = LatitudeField("exp-linear-mult", (-0.2,))
    np.testing.assert_allclose(
        f.at(np.array([33.0, 43.0])), np.exp(np.array([0.2, -0.2])), rtol=1e-15
    )


def test_constant_limit_exact() -> None:
    # coeffs (c0, 0, 0) -> exp(c0) EXACTLY at every latitude (spec §2 constant
    # limit). Bug caught: any v-dependent term leaking into the constant case.
    f = LatitudeField("exp-quad", (0.7, 0.0, 0.0))
    lat = np.linspace(33, 43, 51)
    assert np.all(f.at(lat) == np.exp(0.7))


def test_hull_clamp_constant_continuation() -> None:
    # Outside the box hull [33, 43] the field continues CONSTANT at the edge
    # value (the PolyCalibration convention). Bug caught: extrapolating the
    # form beyond the hull (exp(c1*v) explodes off-box).
    f = LatitudeField("exp-quad", (0.0, 1.0, 0.0))
    assert f.at(np.array([20.0]))[0] == f.at(np.array([33.0]))[0]
    assert f.at(np.array([60.0]))[0] == f.at(np.array([43.0]))[0]


def test_resolve_types_and_key() -> None:
    # resolve returns float for core names, LatitudeField for varied names;
    # params_key must distinguish coefficient sets (provenance collision bug).
    p = LatitudeVaryingProvider(
        core={"time_scale": 7.0},
        varied={"variance": LatitudeField("exp-quad", (0.0, 0.1, 0.2))},
    )
    assert p.resolve("time_scale", None) == 7.0
    assert isinstance(p.resolve("variance", None), LatitudeField)
    q = LatitudeVaryingProvider(
        core={"time_scale": 7.0},
        varied={"variance": LatitudeField("exp-quad", (0.0, 0.1, 0.3))},
    )
    assert p.params_key() != q.params_key()


def test_params_key_order_independent_and_stable() -> None:
    # Same contents, different insertion order -> identical key (repr-stable,
    # order-independent AC). Bug caught: dict-order-sensitive serialization.
    a = LatitudeVaryingProvider(
        core={"time_scale": 7.0, "lx_deg": 1.0},
        varied={
            "variance": LatitudeField("exp-quad", (0.0, 0.1, 0.2)),
            "lx_mult": LatitudeField("exp-linear-mult", (-0.2,)),
        },
    )
    b = LatitudeVaryingProvider(
        core={"lx_deg": 1.0, "time_scale": 7.0},
        varied={
            "lx_mult": LatitudeField("exp-linear-mult", (-0.2,)),
            "variance": LatitudeField("exp-quad", (0.0, 0.1, 0.2)),
        },
    )
    assert a.params_key() == b.params_key()


def test_unknown_form_raises() -> None:
    # Bug caught: a typo'd form silently returning garbage instead of failing.
    f = LatitudeField("exp-cubic", (0.1, 0.2))
    try:
        f.at(np.array([38.0]))
    except ValueError as e:
        assert "exp-cubic" in str(e)
    else:
        raise AssertionError("unknown form must raise ValueError")
