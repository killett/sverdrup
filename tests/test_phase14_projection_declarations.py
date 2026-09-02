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
