"""Owner pin 134 — the refusal set was blind to unsealed measurements.

Pins 42 and 78 key on a SELF-DECLARED ``kind``. Swept over the live store,
``kind: gate`` appears zero times and ``kind: validation`` exactly once —
the ρ-model node that motivated pin 78. So the reachability rule has never
fired on anything, and the range rule has only ever inspected its own
instance, while twelve blocks carry projection-shaped fields with no
declared basis. The audit here SEES those blocks; whether it refuses them
is the owner's call, because they are recorded evidence.
"""

from __future__ import annotations

from sverdrup.validation.gate_schema import projection_audit, validate_gate_schema


def test_a_projection_without_a_basis_is_REPORTED() -> None:
    """The pin-89 probe's shape is caught: extrapolate, declare nothing.

    Bug caught: pin 134 itself — a one-window measurement scaled to nine
    windows in a field whose own name says `_if_linear_in_windows`, with
    the caveat in prose where no check reads it. Wall came back 0.63x and
    RAM 1.69x against that extrapolation.
    """
    block = {
        "measured_one_window": {"wall_h": 3.44, "peak_rss_mib": 4364.5},
        "per_tile_wall_h_if_linear_in_windows": 30.96,
        "caveat": "one window measured; windows are not identical in cost",
    }
    findings = projection_audit(block)
    assert findings, "a prose caveat is not a declared basis"
    assert "per_tile_wall_h_if_linear_in_windows" in findings[0]
    assert validate_gate_schema(block) == [], (
        "and the SELF-DECLARED path stays silent on it — that is the hole"
    )


def test_a_declared_projection_is_NOT_reported() -> None:
    """Declaring the basis clears it — the audit rewards the declaration.

    Bug caught: an audit that fires on everything, which trains readers to
    ignore it and is indistinguishable from no audit at all.
    """
    block = {
        "predicted_T_cross": 0.71,
        "validated_range": [0.0, 0.2523],
        "application_range": [0.0, 0.9],
        "extrapolation_declared": "pending task 21's high-r points (pin 77c)",
    }
    assert projection_audit(block) == []


def test_measured_over_counts_as_a_basis() -> None:
    """A measurement may declare its span without being a `validation`.

    Bug caught: forcing every probe to relabel itself `kind: validation`
    to say what it measured — which is how the discriminator got overloaded
    in the first place (`kind` already carries member-batch, poly and
    challenge-coarsen in this store).
    """
    block = {
        "per_tile_wall_h_if_linear_in_windows": 30.96,
        "measured_over": {"n_windows": 1},
        "extrapolation_declared": "scaled to 9 windows; across-window scaling unmeasured",
    }
    assert projection_audit(block) == []


def test_ordinary_recorded_content_is_untouched() -> None:
    """A block with no projection-shaped field reports nothing.

    Bug caught: a name-matching audit so greedy that ordinary evidence
    rows (mu, sigma, lambda_x, counts) trip it.
    """
    block = {"mu": 0.2859, "sigma": 0.2186, "lambda_x": 232.5, "n_scored_points": 89383}
    assert projection_audit(block) == []


# ---------------------------------------------------------------------------
# Owner pin 139 — the declaration must carry the SPAN, per AXIS, not a flag.
# ---------------------------------------------------------------------------


def test_a_boolean_declaration_is_REFUSED() -> None:
    """`extrapolation_declared: true` states nothing and does not clear.

    Bug caught: pin 139(c) exactly — a boolean satisfies the check while
    stating no span, which would make this fix an instance of the defect
    it closes. Third time in this stage that risk has appeared inside a
    remedy.
    """
    block = {
        "per_tile_wall_h_if_linear_in_windows": 30.96,
        "extrapolation_declared": True,
    }
    findings = projection_audit(block)
    assert findings, "a flag is not a span"
    assert "boolean" in findings[0].lower()


def test_an_empty_span_is_REFUSED() -> None:
    """`measured_over: {}` is silence with a key on it.

    Bug caught: the same defect one step subtler — a declaration present
    but empty, which passes a `in block` test and states nothing.
    """
    block = {"predicted_T_cross": 0.97, "measured_over": {}, "application_range": []}
    assert projection_audit(block)


def test_multi_axis_blocks_need_PER_AXIS_declarations() -> None:
    """Two projected fields are not cleared by one block-level span.

    Bug caught: pin 139(d) — the pin-89 probe projected on wall AND on
    tile count, and a single block-level range would declare one while
    silently covering the other. One axis caveated and one silent is the
    exact shape that cost us the RAM basis.
    """
    two_axes = {
        "per_tile_wall_h_if_linear_in_windows": 30.96,
        "four_tile_wall_h_if_linear_in_windows": 123.8,
        "validated_range": [1, 1],
        "application_range": [1, 9],
        "extrapolation_declared": "scaled across windows",
    }
    findings = projection_audit(two_axes)
    assert findings, "a single block-level span cannot speak for two axes"

    one_axis = {
        "per_tile_wall_h_if_linear_in_windows": 30.96,
        "validated_range": [1, 1],
        "application_range": [1, 9],
        "extrapolation_declared": "scaled across windows; across-window scaling unmeasured",
    }
    assert projection_audit(one_axis) == [], (
        "a single-axis block IS per-axis, and must not be made to invent structure"
    )


def test_declared_axes_from_a_forward_pointer_clear_the_block() -> None:
    """A block declared elsewhere passes without being edited.

    Bug caught: pin 139(b) — requiring the declaration to live inside the
    recorded block would mean rewriting witnessed evidence to satisfy a
    check. The amendment index points forward; the audit follows it.
    """
    block = {"per_tile_wall_h_if_linear_in_windows": 30.96}
    assert projection_audit(block)
    assert (
        projection_audit(
            block, declared_axes=frozenset({"per_tile_wall_h_if_linear_in_windows"})
        )
        == []
    )


# ---------------------------------------------------------------------------
# Owner pin 140(a) — pin 42 re-keyed on SHAPE. Reporting only until the
# sweep has been ruled on (140c).
# ---------------------------------------------------------------------------


def test_a_verdict_block_that_never_volunteered_is_SEEN() -> None:
    """A block recording a verdict is inspected without declaring itself.

    Bug caught: pin 140 itself — `kind: gate` appears zero times in the
    live store, so the reachability rule has never inspected a single
    block since it was written. A schema field that only inspects
    volunteers inspects nothing.
    """
    from sverdrup.validation.gate_schema import verdict_audit

    block = {"pair": "seam_n/seam_s", "r_seam": 0.0827, "verdict": "CLEAN"}
    assert verdict_audit(block), "a recorded verdict with no reachability statement"
    assert "pin 42" in verdict_audit(block)[0]


def test_report_only_blocks_are_EXEMPT() -> None:
    """`gates: false` is the established marker and clears the audit.

    Bug caught: an audit that demands reachability from report-only rows.
    Pin 98 settled that recording is a legitimate state distinct from
    gating, and re-litigating it here would push authors to label
    non-gates as gates just to quiet a check.
    """
    from sverdrup.validation.gate_schema import verdict_audit

    assert verdict_audit({"verdict": "CLEAN", "gates": False}) == []


def test_declared_reachability_clears_it() -> None:
    """Either pin-42 form satisfies the re-keyed check.

    Bug caught: recognising only `both_outcomes_reachable` and ignoring
    the richer `pin42` block the anchor gate and chi2 rows already use —
    which would refuse the blocks that got it RIGHT.
    """
    from sverdrup.validation.gate_schema import verdict_audit

    assert verdict_audit({"verdict": "PASS", "both_outcomes_reachable": True}) == []
    assert (
        verdict_audit(
            {
                "verdict": "PASS",
                "pin42": {
                    "pass_condition": "sha equal",
                    "fail_condition": "sha differs",
                },
            }
        )
        == []
    )


def test_ordinary_rows_do_not_trip_the_verdict_audit() -> None:
    """A measurement row without a verdict or threshold is not a gate.

    Bug caught: a vocabulary so wide that every pcg row (they all carry
    `rtol`) becomes a gate needing a reachability statement — 68 of them
    in this store, which would drown the signal the audit exists to give.
    """
    from sverdrup.validation.gate_schema import verdict_audit

    assert (
        verdict_audit({"window": "w+00027.0+60", "iterations": 424, "rtol": 1e-06})
        == []
    )
