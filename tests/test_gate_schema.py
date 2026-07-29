"""Gate-schema refusals: reachable verdicts AND validated ranges.

Pin 42 made reachability of each VERDICT a required schema field, after
prose caught none of five instances. Pin 78 extends it to VALIDATION
RANGES after a third instance of the same family:

> The 3x factor could not pass; the +/-4 sd acceptance could not fail;
> this sweep could not disagree where disagreement matters. ...
> Extrapolation beyond the validated span is declared at the point of use
> or the gate refuses.

Expected values are hand-constructed from the ruling's own examples —
the sweep validated over [0, 0.2523] and applied at r ~ 0.9, the +/-4 sd
acceptance at P(reject) ~ 1.3e-4 — never taken from the implementation.
"""

from __future__ import annotations

from typing import Any

from sverdrup.validation.gate_schema import validate_gate_schema

REACHABLE_GATE: dict[str, Any] = {
    "kind": "gate",
    "pass_condition": "the lattice is unmoved; all four routes bit-identical",
    "fail_condition": "the lattice moves; member sha-equality breaks",
    "both_outcomes_reachable": True,
}


def test_a_reachable_gate_with_no_model_passes() -> None:
    """The ordinary case returns no violations.

    Catches a validator that refuses everything — which would be
    indistinguishable from a broken seal check and would be switched off
    within a day.
    """
    assert validate_gate_schema(REACHABLE_GATE) == []


def test_an_unreachable_outcome_is_refused() -> None:
    """A gate that cannot reach one of its verdicts is not a gate.

    The ruling's own instance: the +/-4 sd acceptance at
    ``P(reject) ~ 1.3e-4`` under both null and alternative. Catches the
    pin-42 hole that let the 3x factor (no reachable CLEAN) and that
    acceptance (could not fail) through five times as prose.
    """
    block = {
        "kind": "gate",
        "threshold": "+/-4 sd",
        "p_reject_under_null": 1.3e-4,
        "p_reject_under_alternative": 1.5e-4,
        "both_outcomes_reachable": False,
    }

    violations = validate_gate_schema(block)

    assert len(violations) == 1
    assert "reachable" in violations[0]


def test_application_outside_the_validated_range_is_refused() -> None:
    """Pin 78's case: validated low, applied high, nothing declared.

    The rho model is validated over ``[0, 0.2523]`` — where sqrt(1-rho)
    is flat — and destined for ``r ~ 0.9``, where a 23% error costs
    7.17x in the floor. Catches precisely the failure that survived two
    prior rounds of review.
    """
    block = {
        "kind": "validation",
        "model": "rho = r^2",
        "validated_range": [0.0, 0.2523],
        "application_range": [0.0, 0.9],
    }

    violations = validate_gate_schema(block)

    assert len(violations) == 1
    assert "outside" in violations[0]
    assert "0.9" in violations[0]


def test_declared_extrapolation_is_allowed() -> None:
    """A declared extrapolation is permitted — the rule is disclosure.

    Pin 78 says extrapolation is "declared at the point of use or the
    gate refuses", so declaration must actually work. Catches a rule so
    strict that the only way past it is to disable it, which is how
    disciplines die.
    """
    block = {
        "kind": "validation",
        "model": "rho = r^2",
        "validated_range": [0.0, 0.2523],
        "application_range": [0.0, 0.9],
        "extrapolation_declared": (
            "applied beyond the validated span; the floor is parameterized "
            "by measured rho per pair until high-r points exist"
        ),
    }

    assert validate_gate_schema(block) == []


def test_a_missing_validated_range_is_refused() -> None:
    """Silence is not compliance.

    A validation that never states its span is exactly what the previous
    three instances looked like at authorship time. Catches treating an
    absent field as "fine", which is how all three passed review.
    """
    block = {
        "kind": "validation",
        "model": "rho = r^2",
        "application_range": [0.0, 0.9],
    }

    violations = validate_gate_schema(block)

    assert len(violations) == 1
    assert "validated_range" in violations[0]


def test_non_gate_blocks_are_ignored() -> None:
    """Ordinary recorded content is not a gate and must pass untouched.

    Catches a validator that would refuse the EXISTING sealed content —
    the seal is unspent and `check` must stay green, so the refusal has
    to key on blocks that declare themselves gates or validations.
    """
    assert validate_gate_schema({"label": "MEASUREMENT", "value": 1.0}) == []
    assert validate_gate_schema({"mu": 0.769, "sigma": 0.284}) == []
