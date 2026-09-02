"""Owner pin 139 — the declared spans, and the index that points at them."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.helpers import load_script

_mod = load_script("phase14_projection_declarations")
_mirror = load_script("phase14_evidence_mirror")


def test_every_declaration_is_well_formed() -> None:
    """Every axis carries measured_over and applied_to WITH VALUES.

    Bug caught: pin 139(c) — a declaration that says `extrapolation_declared:
    true` and nothing else would satisfy the audit while stating no span,
    making the remedy an instance of the defect it closes.
    """
    assert _mod.validate(_mod.DECLARATIONS) == []


def test_each_pointer_aims_at_the_node_it_declares() -> None:
    """`amends` is the recorded node the declared block lives inside.

    Bug caught: a forward pointer aimed at an unrelated node — the
    amendment index would resolve, the reader would follow it, and the
    declaration they landed on would be about something else.
    """
    for path, entry in _mod.DECLARATIONS.items():
        assert path.startswith(entry["amends"] + "."), (
            f"{path} declares itself an amendment of {entry['amends']}, "
            "which does not contain it"
        )


def test_the_probe_declares_BOTH_axes_including_the_unwritten_one() -> None:
    """Wall and RAM are both declared for the pin-89 probe.

    Bug caught: the asymmetry that cost the launch-gate basis — the wall
    projection carried a prose caveat and the RAM projection carried
    nothing at all, and was never even written as a projection, so no
    field name could catch it. If a future edit drops the hand-added RAM
    axis, the store goes back to declaring one axis of a two-axis probe.
    """
    wall = _mod.DECLARATIONS[
        "phase14.stage1.tier2_probe_kuroshio_m100.rederived_bracket_pin_89d"
    ]["axes"]
    ram = _mod.DECLARATIONS[
        "phase14.stage1.tier2_probe_kuroshio_m100.measured_one_window"
    ]["axes"]

    assert "per_tile_wall_h_if_linear_in_windows" in wall
    assert "peak_rss_mib" in ram
    for axis in (wall["per_tile_wall_h_if_linear_in_windows"], ram["peak_rss_mib"]):
        assert axis["measured_over"]["n_windows"] == 1
        assert axis["applied_to"]["n_windows"] == 9
        assert isinstance(axis["extrapolation_declared"], str)
    assert (
        ram["peak_rss_mib"]["measured_outcome_2026_09_01"][
            "ratio_measured_over_projected"
        ]
        > 1.6
    ), "leg 1 measured the RAM projection optimistic by ~1.69x"


def test_the_amendment_index_has_no_DUPLICATE_keys() -> None:
    """A repeated key in AMENDMENTS silently discards the earlier list.

    Bug caught: exactly what happened while landing pin 139 — three
    forward pointers were added under keys that already appeared later in
    the literal, and Python kept the later value. The index still passed
    its own regression check, because from its point of view the pointers
    had never existed. A dict literal cannot detect this after parsing,
    so the source is read.
    """
    assert _mirror.__file__ is not None
    source = Path(_mirror.__file__).read_text()
    tree = ast.parse(source)
    literals = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "AMENDMENTS"
    ]
    assert len(literals) == 1, "AMENDMENTS is assigned exactly once"
    literal = literals[0]
    assert isinstance(literal, ast.Dict)
    keys = [k.value for k in literal.keys if isinstance(k, ast.Constant)]
    duplicates = {k for k in keys if keys.count(k) > 1}
    assert not duplicates, (
        f"duplicate AMENDMENTS keys silently drop pointers: {duplicates}"
    )


def test_declared_axes_by_path_feeds_the_audit_the_field_names() -> None:
    """The lookup the audit consults returns field names, not axis blobs.

    Bug caught: handing the audit the axis dicts instead of their keys —
    the membership test would never match and every declared block would
    still be refused, which looks like "the declarations did not work"
    rather than a lookup bug.
    """
    node = _mod.build_node()
    by_path = _mod.declared_axes_by_path(node)
    assert by_path[
        "phase14.stage1.tier2_probe_kuroshio_m100.derived_pin_89d.wall"
    ] == frozenset({"implied_exponent"})


# ---------------------------------------------------------------------------
# Owner pin 148 — the two golden-tile blocks, and pin 146(a) — the exemption
# is mechanical, not described.
# ---------------------------------------------------------------------------


def test_the_cited_golden_tile_gates_COULD_have_failed() -> None:
    """Check 2's citation is not hollow: both legs fired, with margins.

    Bug caught: an unfailable gate discharging a cited check. Anchor-gate
    check 2 RUNS NOTHING — it is discharged by citation to these blocks —
    so if either could not have fired, the identity chain rests on a gate
    that was never a gate. Both fired: mu 6.23x and map rms 4.10x over
    their recorded tolerances.
    """
    entry = _mod.REACHABILITY["phase14.stage0.golden_tile.dc2021a_vs_cmems_my"]
    margins = entry["margins"]

    assert entry["both_outcomes_reachable"] is True
    assert margins["mu_over_by"] > 6.0
    assert margins["map_rms_over_by"] > 4.0
    assert abs(margins["mu_delta"]) > margins["mu_threshold"]
    assert margins["map_rms_m"] > margins["map_rms_threshold_m"]
    assert _mod.validate_reachability(_mod.REACHABILITY) == []


def test_a_reachability_claim_without_a_failing_condition_is_REFUSED() -> None:
    """Asserting both outcomes is not the same as naming them.

    Bug caught: pin 42's own defect inside its remedy — a declaration
    that sets `both_outcomes_reachable: true` and says nothing about what
    failure would have looked like, which is exactly the unexamined claim
    the rule exists to refuse.
    """
    bad = {
        "x.y": {
            "amends": "x",
            "both_outcomes_reachable": True,
            "pass_condition": "it passed",
            "fail_condition": "",
            "outcome_observed": "PASS",
        }
    }
    findings = _mod.validate_reachability(bad)
    assert any("fail_condition" in f for f in findings)


def test_the_declarations_node_exemption_is_MECHANICAL(tmp_path: Path) -> None:
    """A malformed declarations node fails the check that exempts it.

    Bug caught: pin 146(a) — the audit skips the declarations subtree, so
    if the stricter validator were only described rather than wired, that
    exemption would be a hole big enough to hide any projection in. This
    drives the seal-run walker directly with a broken node.
    """
    seal_run = load_script("phase14_seal_run")
    store = {
        "phase14": {
            "stage1": {
                "projection_declarations": {
                    "declarations": {
                        "phase14.stage1.somewhere": {
                            "amends": "phase14.stage1",
                            "axes": {
                                "predicted_thing": {
                                    "measured_over": {},
                                    "applied_to": {"m": 100},
                                    "extrapolation_declared": True,
                                }
                            },
                        }
                    }
                }
            }
        }
    }
    findings = seal_run._projection_findings(store)
    assert findings, "the exempt subtree must still be validated, and more strictly"
    assert any("139c" in f for f in findings)
