"""Latitude-varying provider — named-form behavior (superseded in place, spec §2).

Migrated for Phase-10 Task 2: the cos-blend assertions died with the old
class; these tests cover the named-form behaviors NOT already pinned by
tests/test_phase10_provider.py (hand-computed values live there).
"""

from __future__ import annotations

import numpy as np

from sverdrup.core.parameters import LatitudeField, LatitudeVaryingProvider


def test_negative_l1_multiplier_decreases_northward_within_hull():
    # Behavior: exp(l1*v) with l1 < 0 is strictly decreasing across the box
    # (the Rossby sign: shorter scales poleward).
    # Bug caught: a sign flip in v or l1 (poleward-INCREASING length scales).
    f = LatitudeField("exp-linear-mult", (-0.5,))
    lat = np.linspace(33.0, 43.0, 21)
    vals = f.at(lat)
    assert np.all(np.diff(vals) < 0)


def test_key_is_stable_across_constructions():
    # Behavior: identical construction -> identical params_key (provenance
    # reproducibility). Bug caught: an unstable key (id()/hash-seeded).
    def build() -> LatitudeVaryingProvider:
        return LatitudeVaryingProvider(
            core={"time_scale": 7.0},
            varied={"lx_mult": LatitudeField("exp-linear-mult", (-0.25,))},
        )

    assert build().params_key() == build().params_key()


def test_key_distinguishes_forms_and_names():
    # Behavior: the key encodes the named form AND the varied-name binding.
    # Bug caught: a key ignoring the form (exp-quad vs exp-linear-mult with
    # equal leading coefficients would collapse in provenance).
    a = LatitudeVaryingProvider(
        core={}, varied={"variance": LatitudeField("exp-quad", (0.0, 0.0, 0.0))}
    )
    b = LatitudeVaryingProvider(
        core={}, varied={"variance": LatitudeField("exp-linear-mult", (0.0,))}
    )
    c = LatitudeVaryingProvider(
        core={}, varied={"lx_mult": LatitudeField("exp-quad", (0.0, 0.0, 0.0))}
    )
    assert len({a.params_key(), b.params_key(), c.params_key()}) == 3


def test_field_never_coerces_to_float():
    # Behavior: float(LatitudeField) raises (spec §2 dispatch contract).
    # Bug caught: a scalar path silently collapsing a field to one number —
    # the exact silent-coercion failure the type dispatch exists to prevent.
    f = LatitudeField("exp-quad", (0.1, 0.2, 0.3))
    try:
        float(f)
    except TypeError as e:
        assert "dispatch on type" in str(e)
    else:
        raise AssertionError("float(LatitudeField) must raise TypeError")
