"""T8 OSSE pricing tests (owner pins 232-239) — CI-local.

This document exists to be ACTED ON: the owner elects or declines a run from
it. The failure that matters is not a crash but a number that quietly
misprices the decision, or a caveat that quietly goes missing.

⛔ **v1's suite passed while the document was OVERTURNED**, and a two-reviewer
review found 10 surviving mutants between them. Every one of those gaps has a
test below, named against the mutant that exposed it. The lesson recorded in
this docstring: **v1 built a `tmp_path` recompute test for `epoch_classes()`
and did not apply the same discipline one function over**, so
`truth_field_cost` could ignore the window plan entirely and stay green while
§9 claimed that value was MEASURED from the store.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.helpers import load_script

_mod = load_script("phase14_osse_pricing")

# Hand-read measured legs (phase14.stage1.tiles.<tile>), kept as literals so
# the expectations are not re-derived from the source under test.
_WALL_S = {
    "kuroshio": 70811.32452932594,
    "southern": 98929.75216705899,
    "equatorial": 91945.0,
    "quiet_gyre": 93712.97317277198,
}
_N_OBS = {
    "kuroshio": 138518,
    "southern": 175059,
    "equatorial": 167579,
    "quiet_gyre": 168755,
}


def _fake_store(span_starts: list[float] | None = None) -> dict[str, Any]:
    """A minimal store the producer can price from."""
    return {
        "phase14": {
            "stage1": {
                "tiles": {
                    t: {
                        "wall_s": _WALL_S[t],
                        "peak_rss_mib": 5000.0,
                        "n_obs": _N_OBS[t],
                        "window_plan": {
                            "starts": span_starts
                            or [
                                -18.0,
                                27.0,
                                72.0,
                                117.0,
                                162.0,
                                207.0,
                                252.0,
                                297.0,
                                322.0,
                            ],
                            "w_days": 60.0,
                            "n_windows": 9,
                            "days_stride": 1,
                        },
                    }
                    for t in _WALL_S
                },
                "tier2_probe_kuroshio_m100": {
                    "derived_pin_89d": {
                        "wall": {
                            "one_window_h": 3.4398840666791592,
                            "per_tile_h": 30.958956600112433,
                            "four_tiles_h": 123.83582640044973,
                        }
                    }
                },
            }
        }
    }


def _write(tmp_path: Path, obj: Any, name: str) -> Path:
    p = tmp_path / name
    p.write_text(json.dumps(obj))
    return p


def _seal(tmp_path: Path, rows: list[dict[str, Any]]) -> Path:
    return _write(tmp_path, {"content": {"epoch_table": rows}}, "seal.json")


def _block() -> dict[str, Any]:
    return _mod.price()


# ---------------------------------------------------------------------------
# The overturning defect: the unit of account (owner pin 239).
# ---------------------------------------------------------------------------


def test_obs_scaling_exponent_is_fitted_from_the_legs_not_typed() -> None:
    """Wall is fitted against n_obs, and the fit is superlinear.

    Bug caught — THE ONE THAT OVERTURNED v1: pricing every epoch class at a
    flat leg wall, as if solve cost were independent of observation count.
    The four legs are a controlled experiment (identical bbox, m, window
    plan and constellation; only n_obs varies) and give an exponent near
    1.41. A flat model is not merely imprecise, it is flatter than LINEAR,
    which this project's own probe node had already rejected at 1.28.
    """
    sc = _mod.obs_scaling()
    assert sc["exponent"] == pytest.approx(1.4146, abs=0.001)
    assert sc["r_squared"] > 0.99
    assert sc["exponent"] > 1.0, "a flat or sublinear fit would restore v1's defect"
    assert [leg["tile"] for leg in sc["legs"]] == list(_mod.PRICED_TILES)


def test_obs_scaling_recomputes_from_the_store(tmp_path: Path) -> None:
    """The exponent follows the store, not a constant in the producer.

    Bug caught: the exponent typed after being fitted once. Feeding legs
    whose wall is exactly proportional to n_obs must yield 1.0; a producer
    returning 1.4146 regardless is asserting a fit it did not perform —
    the same false-provenance class as a typed class count.
    """
    store = _fake_store()
    for t in _WALL_S:
        store["phase14"]["stage1"]["tiles"][t]["wall_s"] = _N_OBS[t] * 0.5

    out = _mod.obs_scaling(_write(tmp_path, store, "store.json"))

    assert out["exponent"] == pytest.approx(1.0, abs=1e-9)


def test_the_fit_is_declared_a_projection_outside_its_measured_span() -> None:
    """The exponent carries a pin-139 declaration naming where it fails.

    Bug caught: swapping one point estimate for another (owner pin 239b).
    The fit rests on n=4 legs at a single 5-mission constellation, while
    the classes run 3 to 9 missions — so the sparse classes are priced
    outside anything measured. Presenting obs-scaled hours as measurement
    would repeat v1's error one level up, with better arithmetic.
    """
    decl = _mod.obs_scaling()["projection_declaration"]
    assert decl["pin"] == 139
    assert decl["within_measured_span"] is False
    assert decl["measured_over"]["n_legs"] == 4
    assert decl["measured_over"]["n_missions"] == 5
    assert decl["application_range"]["n_missions"] == [3, 9]
    assert "MAGNITUDES ONLY" in decl["what_it_may_be_used_for"]


def test_subset_ordering_is_a_counting_fact_not_a_fitted_one() -> None:
    """Post-lift is dearer than pre-lift, on mission counts alone.

    Bug caught — THE DECISION-CHANGING ONE: v1's table priced post-lift at
    118 h and pre-lift at 177 h, so an owner electing the cheap modern
    scope would have budgeted ~5 days and received ~8.5. The direction is
    settled by counting: post-lift carries 44 missions across 6 classes,
    pre-lift 35 across 9. Fewer classes, more observations. It therefore
    holds under ANY cost monotone in observations, and only the flat model
    reverses it — which is why the claim must not be stated as resting on
    the fitted exponent.
    """
    cf = _mod.scope_subsets()["ordering_is_a_counting_fact"]
    assert cf["pre_lift"] == {"n_classes": 9, "total_missions": 35}
    assert cf["post_lift"] == {"n_classes": 6, "total_missions": 44}
    assert cf["post_lift"]["n_classes"] < cf["pre_lift"]["n_classes"]
    assert cf["post_lift"]["total_missions"] > cf["pre_lift"]["total_missions"]

    rows = {r["subset"]: r for r in _mod.scope_subsets()["rows"]}
    post, pre = rows["post_lift_mask66"], rows["pre_lift_mask66"]
    # Flat model inverts it; obs-scaled does not.
    assert post["flat_h_at_kuroshio"] < pre["flat_h_at_kuroshio"]
    assert post["obs_scaled_h_at_kuroshio"] > pre["obs_scaled_h_at_kuroshio"]


def test_v1_editorial_is_withdrawn_and_not_replaced_with_its_opposite() -> None:
    """The withdrawal is recorded; no opposite claim is asserted.

    Bug caught (owner pin 239c): replacing "cost and evidential value move
    together" with "they move apart". Both are editorials resting on a cost
    model; asserting the inverse would be the same mistake with a different
    sign. The record must carry the withdrawal and the inversion as a
    finding, and stop there.
    """
    w = _mod.scope_subsets()["v1_editorial_WITHDRAWN"]
    assert "move together" in w["withdrawn_text"]
    assert "ARTEFACT OF THE FLAT MODEL" in w["why"].upper()
    assert "NOT replaced" in w["not_replaced"]
    assert "different sign" in w["not_replaced"]


def test_constellation_size_is_declared_the_larger_open_input() -> None:
    """The bigger axis is declared open, in the tile axis's own form.

    Bug caught (owner pin 239d): v1 declared WHICH TILE an open input — a
    1.40x axis — while silently collapsing WHICH CONSTELLATION, a ~4.7x
    axis, to a single value. Declaring the smaller axis while fixing the
    larger one reads as rigour and is the opposite.
    """
    blk = _block()["constellation_size_is_an_open_input"]
    assert blk["not_a_default"] is True
    assert "NOT A DEFAULT" in blk["statement"]
    assert "LARGER axis" in blk["statement"]
    assert blk["class_mission_counts"] == [3, 3, 4, 4, 4, 4, 4, 4, 5, 7, 6, 7, 7, 8, 9]
    assert blk["leg_missions"] == 5


def test_leg_constellation_matches_the_runner() -> None:
    """LEG_MISSIONS equals the runner's PROBE_MISSIONS.

    Bug caught: the baseline constellation drifting from the one the legs
    actually ran. Every obs-scaled figure divides by this count, so a wrong
    baseline rescales the entire sweep silently. The leg rows carry no
    mission list, so this is the only place the claim can be checked.
    """
    runner = load_script("phase14_stage1_run")
    assert _mod.LEG_MISSIONS == runner.PROBE_MISSIONS
    assert len(_mod.LEG_MISSIONS) == 5


# ---------------------------------------------------------------------------
# Gaps the reviewers found in v1's own suite.
# ---------------------------------------------------------------------------


def test_truth_volume_recomputes_from_the_window_plan(tmp_path: Path) -> None:
    """The span is read from the store, not assumed to be 400 days.

    Bug caught — REVIEWER MUTANT M2, which survived v1's entire suite:
    replacing the window-plan arithmetic with a literal 400.0. §9's basis
    table claims `window-plan span | ...window_plan | MEASURED`; under M2
    that provenance claim is false and the suite is green. v1 built exactly
    this recompute discipline for `epoch_classes()` and failed to apply it
    one function over.
    """
    store = _fake_store(span_starts=[0.0, 45.0])  # union = 0 -> 105 days
    out = _mod.truth_field_cost(_write(tmp_path, store, "store.json"))

    assert out["window_plan_span_days"] == 105.0
    per_day = out["bytes_per_tile_per_day"]
    assert out["bytes_per_tile_per_span"] == int(105.0 * per_day)
    # And the real store still gives the 400-day figure.
    assert _mod.truth_field_cost()["window_plan_span_days"] == 400.0


def test_feasibility_verdict_is_derived_from_the_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Shrinking the budget flips FEASIBLE.

    Bug caught — REVIEWER MUTANT M7: the budget dropped to 0.001 GiB while
    the verdict still read "FEASIBLE", green across v1's suite. That one
    word is what the owner leans on to approve the download; a typed
    literal cannot ever say otherwise, so it carries no information.
    """
    assert _mod.truth_field_cost()["feasibility"]["verdict"] == "FEASIBLE"

    monkeypatch.setattr(_mod, "CMEMS_BUDGET_GIB", 0.001)
    assert _mod.truth_field_cost()["feasibility"]["verdict"] == "REFUSED"


def test_probe_figures_are_read_from_the_store(tmp_path: Path) -> None:
    """The probe comparison follows the node it cites.

    Bug caught — REVIEWER MUTANT M15: `four_tile_projected_h` typed as
    123.8 and mutated to 200.0, surviving all 16 of v1's tests. §9 named
    `tier2_probe_kuroshio_m100` as the source while nothing read it — an
    unenforced provenance claim, the same shape as a typed class count.
    """
    store = _fake_store()
    store["phase14"]["stage1"]["tier2_probe_kuroshio_m100"]["derived_pin_89d"]["wall"][
        "four_tiles_h"
    ] = 200.0
    out = _mod.probe_cross_check(_write(tmp_path, store, "store.json"))

    assert out["four_tile_projected_h"] == 200.0
    # The real node gives the recorded figures.
    real = _mod.probe_cross_check()
    assert real["four_tile_projected_h"] == pytest.approx(123.8358, abs=1e-3)
    assert real["projected_tile_h"] == pytest.approx(30.9590, abs=1e-3)
    assert real["overprediction_factor"] == pytest.approx(1.574, abs=0.001)


def test_lower_bound_states_what_it_covers_and_that_compute_is_included() -> None:
    """The covered set is pinned, and compute is named as itself a bound.

    Bug caught — REVIEWER MUTANT M7 (A's): rewriting `what_is_covered` to
    drop the truth download, unnoticed by v1's suite, which only counted
    the uncosted list. And the substantive gap owner pin 239(e) names: v1
    attributed the lower bound to uncosted ENGINEERING alone, so a reader
    concluded the compute band was sound. It is not — the flat model
    under-prices every class above 5 missions, and 7 of 15 are.
    """
    lb = _block()["lower_bound"]
    assert "truth download" in lb["what_is_covered"]
    assert "re-solves" in lb["what_is_covered"]
    assert "INCLUDING THE COMPUTE FIGURE ITSELF" in lb["statement"]
    assert "239(e)" in lb["compute_is_itself_a_lower_bound"]
    assert len(lb["what_is_not_costed"]) >= 5
    joined = " ".join(lb["what_is_not_costed"]).upper()
    for owed in ("DORMANT", "NON-CONVERGENCE", "CALENDAR TIME"):
        assert owed in joined, owed


def test_every_subset_row_pins_its_class_and_mission_counts() -> None:
    """All five subsets are constrained, not just the headline ones.

    Bug caught — REVIEWER MUTANTS M6 and N5: the `fit+validate` filter
    widened to all 15 epochs, and `pre_lift` switched to a role filter
    (9 -> 10), both green. Two of the five rows in the table the owner
    picks a scope from were entirely unasserted.
    """
    rows = {r["subset"]: r for r in _mod.scope_subsets()["rows"]}
    expected = {
        "full_sweep": (15, 79),
        "fit+validate": (10, 61),
        "pre_lift_mask66": (9, 35),
        "post_lift_mask66": (6, 44),
        "validate_only": (5, 18),
    }
    assert set(rows) == set(expected)
    for name, (n, missions) in expected.items():
        assert rows[name]["n_classes"] == n, name
        assert rows[name]["total_missions"] == missions, name
        assert rows[name]["elected"] is False, name


def test_grid_geometry_is_node_inclusive() -> None:
    """229 nodes across 19 degrees, not 228.

    Bug caught — the reviewer's defect 4: `round(19/step)` counts
    INTERVALS. The STAC grid the producer cites is node-inclusive (2041 lat
    nodes over 170 deg = 2040 intervals + 1), so the tile is 229 nodes and
    the volume is 40.01 MiB, not 39.66. Small, but v1 called that figure
    "exact ... a measurement, not an estimate", and it was neither.
    """
    tf = _mod.truth_field_cost()
    assert tf["grid_nodes_per_side"] == 229
    assert tf["mib_per_tile_per_span"] == pytest.approx(40.01, abs=0.01)
    assert tf["mib_all_four_tiles"] == pytest.approx(160.04, abs=0.05)


def test_global_volume_figures_follow_the_recorded_grid() -> None:
    """The global record scales with the recorded grid, not a constant.

    Bug caught — REVIEWER MUTANTS M4 and N6: `latitude_len` set to 1, and
    the global TiB figure multiplied by 1000, both green. That number is
    the document's justification for the spec's "heavy downloads" claim
    being about a different object, so it has to track the grid.
    """
    tf = _mod.truth_field_cost()
    assert tf["global_zos_per_day_mib"] == pytest.approx(16.817, abs=0.01)
    assert tf["global_zos_full_record_tib"] == pytest.approx(0.1961, abs=0.001)


def test_window_plan_shape_says_overlapping_not_contiguous() -> None:
    """The windows overlap; the union is the download basis.

    Bug caught — the reviewer's wording defect: v1 said "9 windows x 60 d,
    contiguous". The stride is 45 d against 60-d windows, so they overlap
    by 15 and 9x60 = 540 window-days sit over a 400-d union. The union is
    the right basis because each day is bought once, so the number was
    right and the word was wrong — which is the kind of error that survives
    review by being immaterial until someone re-derives from the word.
    """
    shape = _mod.truth_field_cost()["window_plan_shape"]
    assert "OVERLAPPING" in shape
    assert "contiguous" in shape  # only as "NOT contiguous"
    assert "NOT \ncontiguous" in shape or "NOT contiguous" in shape
    assert "540" in shape and "400" in shape


def test_truth_headline_keeps_the_per_tile_qualifier() -> None:
    """ "Bought once PER TILE" — the qualifier is load-bearing.

    Bug caught: v1's headline said "BOUGHT ONCE, NOT ONCE PER CLASS" while
    every table beside it was a four-tile presentation, so the natural read
    was 40 MiB total rather than 160. The producer's own docstring had the
    qualifier and the document dropped it.
    """
    tf = _mod.truth_field_cost()
    assert "ONCE PER TILE" in tf["does_not_scale_with_classes"]
    assert "DOES scale with the number of tiles" in tf["does_not_scale_with_classes"]
    assert tf["mib_all_four_tiles"] == pytest.approx(
        4 * tf["mib_per_tile_per_span"], rel=1e-9
    )


def test_solve_box_is_flagged_as_not_the_obs_footprint() -> None:
    """The bbox caveat names the halo and the 1.22x it implies.

    Bug caught: reading the solve-box volume as the observation-simulation
    volume. Simulating observations needs truth over the obs footprint
    (solve bbox + 1.0 deg halo = 21 deg), which is (21/19)^2 = 1.22x
    larger. Unstated, the figure looks like the cost of the thing an OSSE
    actually needs.
    """
    caveat = _mod.truth_field_cost()["bbox_caveat"]
    assert "SOLVE box" in caveat
    assert "halo" in caveat
    assert "1.22" in caveat


# ---------------------------------------------------------------------------
# Surfaces that held in v1 and must keep holding.
# ---------------------------------------------------------------------------


def test_n_epoch_classes_is_derived_from_the_sealed_table() -> None:
    """15 classes, no deduplication, including after locked removal.

    Bug caught: a typed 15 that cites the sealed table as its source — a
    false provenance claim rather than a stale number.
    """
    real = _mod.epoch_classes()
    assert real["n_epochs"] == 15
    assert real["n_classes"] == 15
    assert real["n_classes_without_locked"] == 15
    assert real["deduplication_available"] is False
    assert "NO CHEAP REDUCTION" in real["no_deduplication_note"].upper()
    assert real["locked_removed"] == ["c2", "c2n"]


def test_class_count_recomputes_when_the_sealed_table_changes(
    tmp_path: Path,
) -> None:
    """A different sealed table yields a different count.

    Bug caught: the same hardcoding from the other side — this fails if the
    function ignores its input.
    """
    seal = _seal(
        tmp_path,
        [
            {"epoch_id": "e0", "missions": ["a", "b"]},
            {"epoch_id": "e1", "missions": ["a", "b"]},
            {"epoch_id": "e2", "missions": ["c"]},
        ],
    )
    out = _mod.epoch_classes(seal)
    assert out["n_epochs"] == 3
    assert out["n_classes"] == 2
    assert out["deduplication_available"] is True


def test_every_priced_tile_cites_a_measured_converged_leg() -> None:
    """Basis purity: each price traces to a direct measurement.

    Bug caught (pin 235a): a figure sourced from the CAPPED T2 probe, which
    pin 23(a) ruled unusable for absolute claims.
    """
    per_tile = _block()["per_tile_price"]
    assert set(per_tile) == set(_WALL_S)
    for tile, row in per_tile.items():
        assert row["basis"] == f"phase14.stage1.tiles.{tile} — MEASURED, 9/9 CONVERGED"
        assert row["measured_leg_wall_h"] == pytest.approx(_WALL_S[tile] / 3600.0)


def test_the_probe_is_a_cross_check_never_a_price() -> None:
    """The probe is declared a projection and never becomes the sweep.

    Bug caught (pin 236b): the probe used AS THE PRICE. It is CONVERGED, so
    99(c) admits it, but it is a one-window projection of the very quantity
    the legs measured and it over-predicted its own tile by 1.574x. Pricing
    from it would inflate the flat sweep to 464 h.
    """
    block = _block()
    pc = block["probe_cross_check"]
    assert "NOT A PRICE" in pc["role"]
    assert pc["projection_declaration"]["within_measured_span"] is False

    probe_sweep = 15 * pc["projected_tile_h"]
    rng = block["full_sweep_range"]
    for value in (
        rng["flat_low_h"],
        rng["flat_high_h"],
        rng["obs_scaled_low_h"],
        rng["obs_scaled_high_h"],
    ):
        assert value != pytest.approx(probe_sweep, abs=1.0)


def test_price_names_both_ends_of_the_tile_spread() -> None:
    """The sweep carries both tiles and the measured spread.

    Bug caught (pin 235d): collapsing to a single "tile solve". The legs
    span 1.40x, so one number lets an owner budget kuroshio and receive
    southern.
    """
    rng = _block()["full_sweep_range"]
    assert rng["low_tile"] == "kuroshio"
    assert rng["high_tile"] == "southern"
    lo, hi = rng["measured_leg_spread_h"]
    assert lo == pytest.approx(19.67, abs=0.01)
    assert hi == pytest.approx(27.48, abs=0.01)
    assert rng["flat_high_h"] / rng["flat_low_h"] == pytest.approx(1.40, abs=0.01)


def test_decision_cell_is_empty_and_cannot_read_as_not_priced() -> None:
    """EMPTY means "priced, owner to decide" — and says so.

    Bug caught (pin 235e): an empty cell read as "T8 was never priced",
    which is exactly how the posted Gate-1 pack's OSSE slot reads today.
    """
    block = _block()
    assert block["decision"] is None
    assert block["decision_cell"] == "EMPTY"
    assert "NOT 'not priced'" in block["decision_is_the_owners"]
    assert block["report_only"] is True


def test_both_recommendation_options_carry_can_and_cannot() -> None:
    """Both options presented, neither elected, each with its limits.

    Bug caught: a document that recommends, or an option shown without what
    it cannot establish — the 225(b) failure one task over.
    """
    opts = _block()["recommendation_options"]
    assert len(opts) == 2
    for o in opts:
        assert o["can_establish"] and o["cannot_establish"]


def test_value_case_is_the_spec_string_verbatim() -> None:
    """The value case is quoted, not paraphrased.

    Bug caught (pin 235c): a paraphrase that strengthens the claim by
    dropping the parenthetical about what fork-e level 1 validates against.
    """
    assert _mod.VALUE_CASE == (
        "constellation varied over FIXED model truth is the only "
        "ground-truth test of the era-transfer claim (fork-e level 1 "
        "validates against fitted s; OSSE against truth)"
    )
    assert _block()["value_case_verbatim"] == _mod.VALUE_CASE
