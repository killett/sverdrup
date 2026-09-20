"""T8 OSSE pricing tests, v3 (owner pins 232-249) — CI-local.

Two rounds of two-reviewer review overturned v1 and v2, both on the UNIT OF
ACCOUNT. The suites passed both times. What they pinned was the model that
happened to be in the producer, never the *application* of it — so a mutant
that rescaled every headline hour stayed green.

v3's headline is a BAND ACROSS MODELS with no exponent in it, so these tests
pin the band, the axes declared open, the per-class ceiling verdicts, and —
most importantly — **the claims that were WITHDRAWN**, so they cannot creep
back in.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.helpers import load_script

_mod = load_script("phase14_osse_pricing")

_WALL_S = {
    "kuroshio": 70811.32452932594,
    "equatorial": 91945.0,
    "quiet_gyre": 93712.97317277198,
    "southern": 98929.75216705899,
}
_N_OBS = {
    "kuroshio": 138518,
    "equatorial": 167579,
    "quiet_gyre": 168755,
    "southern": 175059,
}
_MISSION_COUNTS = [3, 3, 4, 4, 4, 4, 4, 4, 5, 7, 6, 7, 7, 8, 9]


def _block() -> dict[str, Any]:
    return _mod.price()


# ---------------------------------------------------------------------------
# The withdrawals — the claims that must not come back.
# ---------------------------------------------------------------------------


def test_no_subset_ordering_is_asserted_anywhere() -> None:
    """§9 carries NO ordering, and the withdrawal is recorded.

    Bug caught — THE ONE THAT OVERTURNED v2, and the reason 244(a) says do
    not re-derive it: cost is sum f(m_i), post-lift has FEWER and LARGER
    classes (6/44) than pre-lift (9/35), so the ordering needs f CONVEX and
    reverses below p ~ 0.638. Any re-derivation would need the conditioning
    term, which has never been measured. A future edit that "restores the
    finding" with a new exponent would repeat the defect exactly.
    """
    subs = _mod.scope_subsets()
    assert subs["ordering"] is None

    w = subs["ordering_is_WITHDRAWN"]
    assert "ANY cost monotone" in w["withdrawn_claim"]
    assert "CONVEX" in w["why_it_is_false"]
    assert "0.638" in w["why_it_is_false"]
    assert "NO ordering is re-derived" in w["not_re_derived"]

    # No row may carry an hours figure — an hours column is an ordering.
    for row in subs["rows"]:
        assert not [k for k in row if "_h" in k or "hour" in k.lower()], row


def test_the_convexity_arithmetic_is_recorded_with_its_coincidence() -> None:
    """The aggregate-vs-sum error is recorded, and so is why it hid.

    Bug caught (owner pin 244c): recording "the arithmetic was wrong"
    without recording that p=1 is the ONLY point where sum(m^p) and
    (sum m)^p agree. The ratification checked several exponents and the one
    that matched was the one that could not disagree. Without that, the next
    reader takes the lesson as "check your arithmetic" instead of "a lone
    agreeing figure is not verification".
    """
    w = _mod.scope_subsets()["ordering_is_WITHDRAWN"]
    err = w["the_arithmetic_error_beneath_it"]
    assert "AGGREGATE" in err
    assert "sum(m_i**p) is not (sum m_i)**p unless p == 1" in err
    assert "ONLY POINT WHERE" in err

    # And the claim is genuinely false at a monotone exponent.
    pre = [3, 3, 4, 4, 4, 4, 4, 4, 5]
    post = [7, 6, 7, 7, 8, 9]
    assert sum(m**0.5 for m in post) < sum(m**0.5 for m in pre)
    assert sum(m**1.0 for m in post) > sum(m**1.0 for m in pre)


def test_the_controlled_experiment_premise_is_struck() -> None:
    """The collinearity caveat is present and the premise is not asserted.

    Bug caught (245f): v2 called the four legs a controlled experiment in
    which "n_obs is the only varying input". With n=4 and one point per
    tile, n_obs is perfectly collinear with tile identity — the regression
    measures which tile. Restoring that sentence would restore a causal
    claim the data cannot support.
    """
    d = _mod.wall_diagnostic()
    assert "PERFECTLY COLLINEAR" in d["collinearity_caveat"]
    assert "WHICH TILE" in d["collinearity_caveat"]
    assert "STRUCK" in d["collinearity_caveat"]


def test_unreproducible_reviewer_figures_are_not_restated() -> None:
    """n_coef per tile is recorded as searched-and-absent, not quoted.

    Bug caught (owner pin 247): a reviewer reported per-tile n_coef values
    that do not exist in the store or the logs. Restating them would be the
    same failure as the "424-554" iteration range that went into v2 lifted
    from a reviewer report unverified — agent output is a claim to check.
    """
    note = _mod.wall_diagnostic()["domain_confound_searched_and_absent"]
    assert "SEARCHED AND ABSENT" in note
    assert "297600" in note
    assert "not restated" in note


def test_the_node_exponent_corroboration_is_withdrawn() -> None:
    """1.28 is an exponent on NODES and is no longer cited as support.

    Bug caught: v2 offered implied_exponent 1.28 as "independent
    corroboration" of an exponent on OBSERVATIONS. They are exponents of
    different variables, and the four legs hold nodes fixed — so it could
    not corroborate even in principle.
    """
    note = _mod.probe_cross_check()["note_on_1_28"]
    assert "GRID NODES" in note
    assert "WITHDRAWN" in note


# ---------------------------------------------------------------------------
# The v3 headline: a band, with every axis open.
# ---------------------------------------------------------------------------


def test_headline_is_a_band_across_models_with_no_single_exponent() -> None:
    """295-470 h, spanning flat through the CI ceiling.

    Bug caught: a headline that quotes one model's number. Two rounds of
    review were spent moving this band by ~11%, less than the tile axis's
    1.40x. Collapsing back to one exponent would re-inherit an authority
    the evidence does not carry.
    """
    survey = _mod.model_survey()
    assert survey["band_low_h"] == pytest.approx(295.0, abs=0.5)
    assert survey["band_high_h"] == pytest.approx(470.4, abs=0.5)

    names = [r["model"] for r in survey["rows"]]
    assert any("flat" in n for n in names)
    assert any("linear" in n for n in names)
    assert any("CI" in n for n in names)
    assert len(survey["rows"]) >= 4


def test_band_follows_the_models_not_a_constant(tmp_path: Path) -> None:
    """The band recomputes from the store.

    Bug caught — REVIEWER MUTANTS B1 and B3, which both survived v2: the
    applied exponent rescaled every headline hour while the reported fit
    stayed put, and the suite never noticed because it pinned the fit and
    not its application. Halving every leg wall must halve the band.
    """
    store = json.loads(_mod.EVIDENCE.read_text())
    for t in _mod.PRICED_TILES:
        store["phase14"]["stage1"]["tiles"][t]["wall_s"] /= 2.0
    p = tmp_path / "store.json"
    p.write_text(json.dumps(store))

    out = _mod.model_survey(p)
    assert out["band_low_h"] == pytest.approx(295.0 / 2, abs=0.5)
    assert out["band_high_h"] == pytest.approx(470.4 / 2, abs=0.5)


def test_leg_equivalents_follow_the_sealed_mission_counts(tmp_path: Path) -> None:
    """The per-model leg-equivalents recompute from the seal.

    Bug caught (B1's shape): the baseline or the class list typed, so every
    obs-scaled hour is rescaled without any test failing. A seal with three
    3-mission classes must give a smaller sweep than the real fifteen.
    """
    seal = tmp_path / "seal.json"
    seal.write_text(
        json.dumps(
            {
                "content": {
                    "epoch_table": [
                        {"epoch_id": f"e{i}", "missions": ["a", "b", "c"]}
                        for i in range(3)
                    ]
                }
            }
        )
    )
    out = _mod.model_survey(seal_path=seal)
    linear = next(r for r in out["rows"] if "linear" in r["model"])
    # 3 classes x (3/5) = 1.8 leg-equivalents.
    assert linear["leg_equivalents"] == pytest.approx(1.8, abs=1e-9)


def test_every_axis_is_declared_open_including_ram_and_platforms() -> None:
    """Four axes, none collapsed (owner pin 245b).

    Bug caught: declaring the tile axis open — as v1 and v2 both did — while
    silently fixing the larger ones. The platform convention alone moves the
    price ~1.28x and neither version disclosed which convention it used.
    """
    axes = {a["axis"]: a for a in _mod.open_axes()}
    assert len(axes) == 4
    for name, a in axes.items():
        assert a["not_a_default"] is True, name
    assert "which tile" in axes
    assert "constellation size" in axes
    assert any("platform" in k for k in axes)
    assert "RAM" in axes
    assert axes["RAM"]["spread"] == "UNMODELLED"


def test_platform_convention_is_disclosed_with_its_basis() -> None:
    """j2g/j2n are one platform, and the note says so.

    Bug caught: counting mission LABELS as platforms without disclosure.
    The legs ran four platforms under five labels; the same over-count sits
    in four of the fifteen epochs. A price that silently picks a convention
    is ~1.28x from the one that picks the other.
    """
    assert _mod.LEG_PLATFORMS == 4
    assert len(_mod.LEG_MISSIONS) == 5
    note = _mod.LABEL_VS_PLATFORM_NOTE
    assert "j2g and j2n" in note
    assert "ONE Jason-2" in note
    assert "1.28x" in note


# ---------------------------------------------------------------------------
# Per-class walls and the ceiling that v2 left as dead code.
# ---------------------------------------------------------------------------


def test_per_class_walls_are_judged_against_the_40h_ceiling() -> None:
    """TIER_CEILING_H is WIRED, and classes breach it.

    Bug caught (245c) — the decision-relevant fact v2 omitted entirely:
    TIER_CEILING_H = 40.0 sat in the producer UNREFERENCED while the same
    constant was used correctly one task over. Pin 99(b)'s rule is PER LEG;
    v2 reported only sums, so a breach — which is a WAIT — was invisible.
    """
    pcw = _mod.per_class_walls()
    assert pcw["ceiling_h"] == 40.0
    assert pcw["classes_breaching_at_dearest_tile"] > 0

    rows = {r["n_missions"]: r for r in pcw["rows"]}
    assert rows[9]["verdict_at_southern"] == "WAIT"
    assert rows[3]["verdict_at_southern"] == "RUN"
    assert sum(r["n_classes_at_this_size"] for r in pcw["rows"]) == 15


def test_ceiling_verdicts_move_when_the_ceiling_moves(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The verdicts are derived from the constant, not typed.

    Bug caught: "WAIT"/"RUN" written as literals, so the ceiling could be
    changed — or the rule retired — with every verdict frozen. That is the
    same defect as v2's typed "FEASIBLE", which no budget change could flip.
    """
    monkeypatch.setattr(_mod, "TIER_CEILING_H", 1.0)
    assert all(
        r["verdict_at_southern"] == "WAIT" for r in _mod.per_class_walls()["rows"]
    )
    monkeypatch.setattr(_mod, "TIER_CEILING_H", 10_000.0)
    assert all(
        r["verdict_at_southern"] == "RUN" for r in _mod.per_class_walls()["rows"]
    )


def test_ram_is_a_named_axis_carrying_an_explicit_refusal() -> None:
    """RAM is UNMODELLED by declaration, with the incidents recorded.

    Bug caught (245d): RAM as one clause in a NOT-costed list, on the axis
    that actually stops work here — it refused the equatorial leg by 11 MiB
    and nearly lost leg 2 at 1382 MiB with swap exhausted. This project has
    pinned the same asymmetry once before: wall 0.63x, RAM 1.69x, the RAM
    projection never written down. A silent omission would be the second
    instance; an explicit refusal is not.
    """
    ram = _mod.ram_axis()
    assert ram["modelled"] is False
    assert "UNMODELLED" in ram["declaration"]
    assert ram["launch_gate_mib"] == pytest.approx(9902.33)
    assert len(ram["recorded_incidents"]) >= 2
    assert any("11 MiB" in i for i in ram["recorded_incidents"])
    assert "1.69x" in ram["why_it_is_not_estimated"]
    assert set(ram["measured_peaks_mib"]) == set(_WALL_S)


# ---------------------------------------------------------------------------
# Diagnostic, truth field, and the surfaces that must keep holding.
# ---------------------------------------------------------------------------


def test_per_iteration_cost_is_near_constant_across_the_legs() -> None:
    """wall/(n_obs x iterations) is flat to ~4.5%.

    Bug caught: treating the raw wall-vs-n_obs exponent as a physical law.
    The per-iteration cost being constant is what shows most of the apparent
    superlinearity is the ITERATION term — which runs opposite to the
    observation term for sparse constellations, and therefore cannot be
    folded into an observation exponent without changing sign somewhere.
    """
    d = _mod.wall_diagnostic()
    lo, hi = d["microseconds_per_obs_iteration_span"]
    assert lo == pytest.approx(57.9, abs=0.2)
    assert hi == pytest.approx(63.3, abs=0.2)
    assert d["spread_pct"] < 6.0
    assert "DIAGNOSTIC" in d["is_a_diagnostic_not_a_basis"]


def test_anchor_gate_is_recorded_as_a_measured_point_below_the_legs() -> None:
    """The refit exists and the "below anything measured" claim is retired.

    Bug caught: v2's pin-139 block declared the small classes "below
    anything measured" while a measured m=100, 9-window, CONVERGED solve at
    54,345 observations sat in the same store. Including it moves the
    exponent materially, so the omission was not harmless.
    """
    d = _mod.wall_diagnostic()
    assert d["refit_with_anchor_gate"] == pytest.approx(1.2627, abs=0.01)
    assert d["refit_with_anchor_gate"] < d["raw_wall_vs_nobs_exponent"]
    assert "was false" in d["anchor_gate_was_not_below_anything_measured"]


def test_epoch_classes_and_the_above_leg_size_count_are_derived() -> None:
    """15 classes, no deduplication, and SIX classes above 5 missions.

    Bug caught: v2 typed "7 of the 15 classes are above 5 missions". The
    sealed counts are [3,3,4,4,4,4,4,4,5,7,6,7,7,8,9] — six are above five;
    seven are at-or-above, and the one at exactly five is the leg
    constellation, which every model prices correctly by construction.
    """
    c = _mod.epoch_classes()
    assert c["n_classes"] == 15
    assert c["n_classes_without_locked"] == 15
    assert c["deduplication_available"] is False
    assert c["mission_counts"] == _MISSION_COUNTS
    assert c["classes_above_leg_size"] == 6


def test_truth_field_volume_and_non_scaling(tmp_path: Path) -> None:
    """40.01 MiB per tile, 160.04 for four, and it recomputes.

    Bug caught: the span hardcoded so the window plan is never read, which
    survived v1's suite while the basis table claimed the value MEASURED.
    """
    tf = _mod.truth_field_cost()
    assert tf["grid_nodes_per_side"] == 229
    assert tf["mib_per_tile_per_span"] == pytest.approx(40.01, abs=0.01)
    assert tf["mib_all_four_tiles"] == pytest.approx(160.04, abs=0.05)
    assert "ONCE PER TILE" in tf["does_not_scale_with_classes"]
    assert tf["feasibility"]["verdict"] == "FEASIBLE"

    store = json.loads(_mod.EVIDENCE.read_text())
    store["phase14"]["stage1"]["tiles"]["quiet_gyre"]["window_plan"]["starts"] = [
        0.0,
        45.0,
    ]
    p = tmp_path / "store.json"
    p.write_text(json.dumps(store))
    assert _mod.truth_field_cost(p)["window_plan_span_days"] == 105.0


def test_window_plan_stride_is_described_as_non_uniform() -> None:
    """The stride is not uniform, and the text says so.

    Bug caught: v2 said "a 45-d stride". The strides are [25, 45] distinct —
    a uniform 45-d stride over 9 x 60 d windows spans 420 days, which
    contradicts the document's own 400-day union by 20 days.
    """
    shape = _mod.truth_field_cost()["window_plan_shape"]
    assert "NON-UNIFORM" in shape
    assert "OVERLAPPING" in shape
    assert "25.0" in shape or "25" in shape


def test_epoch_span_reading_is_flagged_as_unstated() -> None:
    """The common-span vs per-era ambiguity is raised, not resolved silently.

    Bug caught: pricing one 400-day truth span against 15 date-ranged epochs
    without saying which reading the design takes. Common-span means
    historical ground tracks must be synthesised (uncosted); per-era means
    15x the download and the truth is no longer "FIXED", which is the value
    case's own word.
    """
    note = _mod.truth_field_cost()["epoch_span_reading_is_unstated"]
    assert "SYNTHESISED" in note
    assert "no longer 'FIXED'" in note


def test_lower_bound_names_replication_and_the_twin_problem() -> None:
    """The uncosted list carries the items a spend decision actually needs.

    Bug caught: a lower-bound list that names only engineering. Replication
    is absent from v1 and v2 entirely — 15 classes x 1 tile x 1 realisation
    cannot separate "this constellation is worse" from "these tracks over
    this tile were unlucky". And GLORYS assimilates the very constellations
    being simulated, which is first-order for an OSSE whose value case is
    "against truth".
    """
    lb = _block()["lower_bound"]
    joined = " ".join(lb["what_is_not_costed"]).upper()
    for owed in ("DORMANT", "REPLICATION", "FRATERNAL-TWIN", "375-626"):
        assert owed in joined, owed


def test_decision_cell_is_empty_and_cannot_read_as_not_priced() -> None:
    """EMPTY means "priced, owner to decide" — and says so.

    Bug caught (235e): an empty cell read as "T8 was never priced", which is
    how the posted Gate-1 pack's own OSSE slot still reads.
    """
    b = _block()
    assert b["decision"] is None
    assert b["decision_cell"] == "EMPTY"
    assert "NOT 'not priced'" in b["decision_is_the_owners"]


def test_value_case_is_the_spec_string_verbatim() -> None:
    """The value case is quoted, not paraphrased.

    Bug caught (235c): a paraphrase that strengthens the claim by dropping
    the parenthetical about what fork-e level 1 validates against.
    """
    assert _mod.VALUE_CASE == (
        "constellation varied over FIXED model truth is the only "
        "ground-truth test of the era-transfer claim (fork-e level 1 "
        "validates against fitted s; OSSE against truth)"
    )
    assert _block()["value_case_verbatim"] == _mod.VALUE_CASE


def test_leg_constellation_matches_the_runner() -> None:
    """LEG_MISSIONS equals the runner's PROBE_MISSIONS.

    Bug caught: the baseline constellation drifting from the one the legs
    ran. Every per-class scaling divides by this count.
    """
    runner = load_script("phase14_stage1_run")
    assert _mod.LEG_MISSIONS == runner.PROBE_MISSIONS
