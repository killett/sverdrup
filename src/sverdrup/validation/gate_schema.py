"""Schema refusals for gates and validations (owner pins 42 and 78).

Pin 42 made the reachability of each VERDICT a required schema field,
after prose failed to catch five instances at authorship time. Pin 78
extended the same discipline to VALIDATION RANGES, on the third instance
of the family:

> The 3x factor could not pass; the +/-4 sd acceptance could not fail;
> this sweep could not disagree where disagreement matters. ...
> a validation must also state the range of the parameter over which it
> is validated, and whether the application range lies inside it.
> Extrapolation beyond the validated span is declared at the point of use
> or the gate refuses.

The two rules share a shape: a claim is refused when the thing that would
falsify it is out of reach. A gate whose failing verdict cannot occur is
not a gate; a validation applied outside the span it was validated over
is not validated there.

**Keys on self-declaration.** Only blocks carrying ``kind`` of ``gate``
or ``validation`` are examined, so ordinary recorded content — and the
existing sealed content, whose seal is unspent — passes untouched.
"""

from __future__ import annotations

from typing import Any

__all__ = ["validate_gate_schema"]


def validate_gate_schema(block: dict[str, Any]) -> list[str]:
    """Refusals for one gate or validation block.

    Args:
        block: A recorded block. Examined only if its ``kind`` is
            ``gate`` or ``validation``.

    Returns:
        Human-readable violations; empty means the block may be sealed.
    """
    kind = block.get("kind")
    if kind == "gate":
        return _gate_violations(block)
    if kind == "validation":
        return _validation_violations(block)
    return []


def _gate_violations(block: dict[str, Any]) -> list[str]:
    """Pin 42: every verdict must be reachable.

    Args:
        block: A block whose ``kind`` is ``gate``.

    Returns:
        Violations found.
    """
    if block.get("both_outcomes_reachable") is True:
        return []
    return [
        "pin 42: gate does not declare both outcomes reachable — a verdict "
        "that cannot occur under the measurement actually taken is not a "
        f"verdict, and this gate cannot be sealed. Block: {sorted(block)}"
    ]


def _validation_violations(block: dict[str, Any]) -> list[str]:
    """Pin 78: the validated span must cover the application span.

    Args:
        block: A block whose ``kind`` is ``validation``.

    Returns:
        Violations found.
    """
    validated = block.get("validated_range")
    applied = block.get("application_range")
    if validated is None:
        return [
            "pin 78: validation states no `validated_range` — silence is not "
            "compliance, and an unstated span is what the prior instances "
            "looked like at authorship time"
        ]
    if applied is None or block.get("extrapolation_declared"):
        return []
    lo_v, hi_v = float(validated[0]), float(validated[1])
    lo_a, hi_a = float(applied[0]), float(applied[1])
    if lo_a < lo_v or hi_a > hi_v:
        return [
            f"pin 78: application range [{lo_a}, {hi_a}] falls outside the "
            f"validated range [{lo_v}, {hi_v}] with no "
            "`extrapolation_declared` — declare the extrapolation at the "
            "point of use or the gate refuses"
        ]
    return []
