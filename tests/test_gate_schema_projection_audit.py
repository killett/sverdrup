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
