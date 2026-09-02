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

__all__ = [
    "projection_audit",
    "verdict_audit",
    "validate_gate_schema",
    "validate_projection_declarations",
]

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


def _has_values(value: object) -> bool:
    """True when a declaration states something (owner pin 139c).

    A boolean is the case the pin names: it satisfies a membership test
    while stating no span at all. An empty dict/list/string is the same
    silence with a key on it.
    """
    if isinstance(value, bool) or value is None:
        return False
    if isinstance(value, (dict, list, tuple, str)):
        return len(value) > 0
    return True


def projection_audit(
    block: dict[str, Any], declared_axes: frozenset[str] = frozenset()
) -> list[str]:
    """Report projected fields carrying no declared span (pins 134, 139).

    Args:
        block: One recorded block. Only its own keys are examined.
        declared_axes: Field names already declared for this block
            ELSEWHERE — a pin-64 forward-pointer amendment (pin 139b), so
            a witnessed node is never edited to satisfy this check.

    Returns:
        One message per unsatisfied requirement, or empty when every
        projected field has a span stated with VALUES.
    """
    # The basis keys are excluded from the vocabulary they license:
    # `extrapolation_declared` matches "extrapolat", and counting a
    # declaration as a projection makes every declared block a two-axis
    # block that can never be cleared.
    projected = sorted(
        k for k in block if _PROJECTION.search(k) and k not in _BASIS_KEYS
    )
    if not projected:
        return []

    if isinstance(block.get("extrapolation_declared"), bool):
        return [
            "pin 139(c): `extrapolation_declared` is a boolean — a flag satisfies "
            "this check while stating nothing. State `measured_over` (the actual "
            "range measured) and the actual range applied. Fields: "
            f"{', '.join(projected)}"
        ]

    undeclared = [k for k in projected if k not in declared_axes]
    if not undeclared:
        return []

    block_basis = [k for k in _BASIS_KEYS if _has_values(block.get(k))]
    if block_basis and len(projected) > 1:
        return [
            "pin 139(d): a block-level span cannot speak for "
            f"{len(projected)} axes ({', '.join(projected)}) — state the span PER "
            "AXIS. One axis caveated and one silent is the shape that cost the "
            "RAM basis at the pin-89 probe"
        ]
    if block_basis:
        return []
    stated_but_empty = [k for k in _BASIS_KEYS if k in block]
    detail = (
        f" (`{'`, `'.join(stated_but_empty)}` present but empty — silence with a "
        "key on it)"
        if stated_but_empty
        else ""
    )
    return [
        "pin 134: projected fields with no declared basis "
        f"({', '.join(undeclared)}){detail} — state `measured_over` (or "
        "`validated_range`) with VALUES and, where it is applied beyond that "
        "span, `extrapolation_declared`. A caveat in prose is not read by any "
        "check, which is how a one-window probe set a nine-window budget"
    ]


# Pin 140(a): pin 42, re-keyed on SHAPE. A block that records a VERDICT or
# carries a THRESHOLD is a gate whether or not it says so. Deliberately
# narrow: `rtol` appears on all 68 pcg rows and is not a verdict.
_VERDICT = re.compile(
    r"^(verdict|verdicts|outcome|passed|pass_fail)(_[a-z0-9]+)?$", re.I
)
_THRESHOLD = re.compile(r"threshold|clean_max|elevated_max|ceiling|criterion", re.I)


def verdict_audit(block: dict[str, Any], declared: bool = False) -> list[str]:
    """Report verdict/threshold blocks that state no reachability (pin 140a).

    Pin 42 requires every quantitative gate to name the conditions under
    which each verdict could occur. Its enforcement keyed on a
    self-declared ``kind: "gate"`` that appears ZERO times in this store,
    so it has never inspected a block. This keys on shape instead.

    ``gates: false`` exempts a block: pin 98 settled that RECORDING is a
    legitimate state distinct from gating, and demanding reachability
    from report-only rows would push authors to mislabel non-gates.

    Args:
        block: One recorded block. Only its own keys are examined.
        declared: True when a forward-pointer reachability declaration
            covers this block (pins 148, 139b) — the declaration states
            the two conditions, so the block itself is not rewritten.

    Returns:
        One message when the block gates without stating reachability.
    """
    if declared or block.get("gates") is False:
        return []
    marks = sorted(k for k in block if _VERDICT.match(k) or _THRESHOLD.search(k))
    if not marks:
        return []
    if block.get("both_outcomes_reachable") is True or _has_values(block.get("pin42")):
        return []
    return [
        f"pin 42 (re-keyed on shape, pin 140a): gates on {', '.join(marks)} with "
        "neither `both_outcomes_reachable` nor a `pin42` block, and no "
        "`gates: false` marking it report-only. A verdict whose failing case "
        "could not occur under the measurement taken is not a verdict"
    ]


def validate_projection_declarations(node: dict[str, Any]) -> list[str]:
    """Hold the DECLARATIONS to the rule they enforce (owner pin 139c).

    The declarations node is exempt from :func:`projection_audit` — it
    quotes projected field names as keys, so auditing it for spans is a
    category error and would refuse the remedy for being about the
    defect. That exemption is only safe because this validator is
    stricter: every axis must carry ``measured_over`` and ``applied_to``
    WITH VALUES, and say explicitly whether it stays inside that span.
    Without it the exemption would be a hole big enough to hide anything
    in — the remedy becoming an instance of the defect, which is the risk
    pin 139(c) names.

    Args:
        node: The recorded ``projection_declarations`` node.

    Returns:
        One message per malformed axis; empty when the table is sound.
    """
    bad: list[str] = []
    declarations = node.get("declarations") or {}
    if not declarations:
        return ["pin 139: the declarations node carries no declarations"]
    for path, entry in declarations.items():
        if not entry.get("amends"):
            bad.append(f"{path}: no `amends` — the forward pointer has no source")
        axes = entry.get("axes") or {}
        if not axes:
            bad.append(f"{path}: declares no axes")
        for field, axis in axes.items():
            where = f"{path}.{field}"
            for key in ("measured_over", "applied_to"):
                if not _has_values(axis.get(key)):
                    bad.append(f"{where}: `{key}` states no values (pin 139c)")
            declared = axis.get("extrapolation_declared")
            if isinstance(declared, bool):
                bad.append(f"{where}: `extrapolation_declared` is a boolean (pin 139c)")
            elif declared is None and axis.get("within_measured_span") is not True:
                bad.append(
                    f"{where}: neither `within_measured_span: true` nor an "
                    "`extrapolation_declared` text — say which it is"
                )
            elif declared is not None and not _has_values(declared):
                bad.append(f"{where}: `extrapolation_declared` is empty (pin 139c)")
    return bad


def validate_gate_schema(block: dict[str, Any]) -> list[str]:
    """Refusals for one gate or validation block.

    Args:
        block: A recorded block. Examined only if its ``kind`` is
            ``gate`` or ``validation`` — the self-declaration pin 134
            found to be the hole, kept here because the sealed content's
            seal is unspent. :func:`projection_audit` is the shape-keyed
            check that does not wait to be volunteered for.

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
