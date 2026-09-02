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

**Owner pin 134 — that is also the hole.** Swept over the live store,
``kind: gate`` appears ZERO times and ``kind: validation`` exactly ONCE
(``phase14.stage1.rho_model_range_limitation``, the ρ-model node that
motivated pin 78). The reachability rule has therefore never fired on any
block, and the range rule has only ever inspected the instance that
produced it, while ``kind`` itself is overloaded in this store with
``member-batch``, ``poly``, ``challenge-coarsen`` and free prose. An
unsealed measurement extrapolates silently because nothing makes it
declare anything: the pin-89 probe scaled ONE window to nine in
``per_tile_wall_h_if_linear_in_windows`` with its caveat in prose, and
came back 0.63× on wall and 1.69× on RAM.

:func:`projection_audit` closes the blindness by keying on the SHAPE of a
block rather than on what it calls itself. It REPORTS; it does not refuse.
Twelve pre-existing blocks are caught, and retro-refusing recorded
evidence is the owner's decision, not this module's.
"""

from __future__ import annotations

import re
from typing import Any

__all__ = ["projection_audit", "validate_gate_schema"]

# Field names that assert something beyond what was measured. Matched on
# the block's OWN keys; the evidence walker visits nested blocks itself.
_PROJECTION = re.compile(
    r"if_linear|extrapolat|projected|predicted|implied|forecast|scaled_to",
    re.IGNORECASE,
)
# Any ONE of these makes the basis machine-readable. `measured_over` is
# accepted so a probe can state its span without relabelling itself a
# `validation` — the overload that made `kind` useless here.
_BASIS_KEYS = (
    "validated_range",
    "measured_over",
    "application_range",
    "extrapolation_declared",
)


def projection_audit(block: dict[str, Any]) -> list[str]:
    """Report projection-shaped fields carrying no declared basis (pin 134).

    Args:
        block: One recorded block. Only its own keys are examined.

    Returns:
        One message naming the offending fields, or empty when the block
        either projects nothing or declares its basis. Reporting only —
        the caller decides whether an audit finding is fatal.
    """
    projected = sorted(k for k in block if _PROJECTION.search(k))
    if not projected or any(k in block for k in _BASIS_KEYS):
        return []
    return [
        "pin 134: projected fields with no declared basis "
        f"({', '.join(projected)}) — state `measured_over` (or "
        "`validated_range`) and, where it is applied beyond that span, "
        "`extrapolation_declared`. A caveat in prose is not read by any "
        "check, which is how a one-window probe set a nine-window budget"
    ]


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
