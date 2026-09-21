"""T8 WAIT-record tests (owner pins 250-252) — CI-local.

T8 is no longer priced. Three pricing rounds were overturned on the unit of
account, and owner pin 250 ruled the task a WAIT because **validity is prior
to price**.

⛔ The failure mode these tests guard is **a successor re-opening the price**.
Every round's suite passed while its document was overturned, so a test that
merely checks the record parses would repeat that. These pin the WAIT, the
exit, and the facts that survived — and they fail if a price returns.
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


def _block() -> dict[str, Any]:
    return _mod.wait_record()


def test_t8_is_a_wait_with_pricing_explicitly_withdrawn() -> None:
    """The verdict is WAIT and the record says pricing is withdrawn.

    Bug caught: a successor reading the node as "priced, decision pending"
    and electing a run from it. Three rounds of hours sit in this task's
    history; without an explicit withdrawal the most recent numbers look
    like the answer. Pin 250 is that validity is PRIOR to price.
    """
    b = _block()
    assert b["verdict"] == "WAIT"
    assert "pin 250" in b["verdict_authority"]
    assert "NOT PRICED AND WILL NOT BE PRICED" in b["pricing_is_withdrawn"]
    assert "VALIDITY IS PRIOR TO PRICE" in b["pricing_is_withdrawn"]
    assert b["decision"] is None
    assert b["decision_cell"] == "EMPTY"


def test_no_price_figure_survives_anywhere_in_the_record() -> None:
    """No hours, no band, no leg-equivalents.

    Bug caught — the specific way this task would regress: a price left in
    the record "for reference". The overturned bands (295-470 h and the rest)
    were each defensible-looking and each wrong about what they measured. A
    number left behind is a number a successor will use.
    """
    text = json.dumps(_block())
    for banned in ("295", "470", "leg_equivalents", "full_sweep", "band_"):
        assert banned not in text, banned

    # No key may announce a PROJECTED cost. `wall_h` on a leg is allowed and
    # deliberately kept: it is a MEASUREMENT of a leg that ran, and it is one
    # of the surviving facts. What is forbidden is a figure projected onto
    # classes or subsets — which is what every overturned round produced.
    # NB not "price": keys like `why_wait_and_not_a_price` and
    # `pricing_is_withdrawn` are prose about the withdrawal, which is
    # exactly what the record is for. The markers below are the shapes a
    # projected COST takes.
    projected = ("_h_at_", "flat_", "obs_scaled", "sweep", "equivalents")

    def walk(o: Any, path: str = "") -> None:
        if isinstance(o, dict):
            for k, v in o.items():
                assert not any(m in k for m in projected), f"{path}.{k}"
                walk(v, f"{path}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{path}[{i}]")

    walk(_block())


def test_all_three_overturns_are_recorded_with_their_defects() -> None:
    """Each round names its DEFECT, not its fix.

    Bug caught: recording "v1 and v2 were superseded" without what went
    wrong. The three defects are one pattern — the unit of account — and a
    successor who sees only "superseded" learns nothing and is free to
    repeat it. v3's entry is the sharpest: the headline was fixed and the
    defect left in the only section that produced a verdict.
    """
    ov = _block()["overturns"]
    assert len(ov) == 3
    assert [o["version"] for o in ov] == ["v1", "v2", "v3"]
    for o in ov:
        assert o["defect"] and o["why_wrong"] and o["found_by"]

    assert "one epoch class = one tile solve" in ov[0]["defect"]
    assert "OBSERVATIONS" in ov[1]["defect"] and "MISSION COUNTS" in ov[1]["defect"]
    assert "ONLY SECTION THAT PRODUCES A VERDICT" in ov[2]["defect"]
    # v1's entry must keep the fact that the authored surfaces all passed.
    assert "CONFIRMED" in ov[0]["found_by"]


def test_the_exit_names_a_nature_run_and_why_glorys_fails() -> None:
    """Pin 251's exit is recorded with its reason and its consequences.

    Bug caught: recording "use different truth" without the mechanism. The
    reason GLORYS12 fails is that it ASSIMILATES altimetry — it has already
    seen the observations the OSSE would test. Without that, a successor
    could pick another reanalysis and reproduce the defect exactly.
    """
    e = _block()["exit"]
    assert "NATURE RUN" in e["headline"]
    assert "ASSIMILATES ALTIMETRY" in e["why"]
    assert "FREE-RUNNING" in e["why"]
    assert e["owner"] == "Stage 2"
    assert "~14 months" in e["llc4320_span_forces_the_common_span_design"]
    assert "OPEN DESIGN QUESTION" in e["the_open_design_question"]
    assert "NOT resolved here" in e["the_open_design_question"]
    assert "UNPRICED" in e["replication_is_required_and_unpriced"]


def test_the_237_measurement_is_marked_as_the_wrong_object() -> None:
    """The truth volume was measured correctly, of the wrong thing.

    Bug caught: a successor reusing the 40.01 MiB figure for a nature run.
    The measurement is sound and its arithmetic exact — it is GLORYS12's
    size, and pin 251 rules GLORYS12 out. Correct measurement, wrong object,
    and the record has to say which.
    """
    note = _block()["exit"]["the_237_query_measured_the_wrong_kind_of_truth"]
    assert "WRONG KIND OF TRUTH" in note
    assert "The measurement was correct; the object was not." in note


def test_value_case_is_recorded_as_what_is_at_risk() -> None:
    """The value case is quoted, and the threat to it is stated.

    Bug caught: keeping the value case as a justification when it is the
    thing in doubt. Neither epoch-span reading preserves "FIXED truth" —
    common-span means synthesised ground tracks, per-era means truth that
    is not fixed. That is why the task waits.
    """
    b = _block()
    assert b["value_case_verbatim"] == _mod.VALUE_CASE
    risk = b["value_case_is_what_is_at_risk"]
    assert "neither epoch-span reading" in risk
    assert "SYNTHESISING" in risk
    assert "no longer FIXED" in risk


def test_surviving_facts_are_derived_not_typed(tmp_path: Path) -> None:
    """The census and decomposition recompute from the store and seal.

    Bug caught: the surviving facts frozen as literals as the task closed.
    They exist so Stage 2 inherits them rather than re-deriving them, which
    is only safe if they still track their sources. Halving the walls must
    halve the per-iteration cost.
    """
    real = _mod.surviving_facts()
    assert real["epoch_classes"]["n_classes"] == 15
    assert real["epoch_classes"]["deduplication_available"] is False
    assert real["convexity_crossover_p"] == pytest.approx(0.638, abs=0.002)

    store = json.loads(_mod.EVIDENCE.read_text())
    for t in _mod.PRICED_TILES:
        store["phase14"]["stage1"]["tiles"][t]["wall_s"] /= 2.0
    p = tmp_path / "store.json"
    p.write_text(json.dumps(store))

    out = _mod.surviving_facts(p)
    lo_r, hi_r = real["per_iteration_decomposition"]["microseconds_span"]
    lo_o, hi_o = out["per_iteration_decomposition"]["microseconds_span"]
    assert lo_o == pytest.approx(lo_r / 2)
    assert hi_o == pytest.approx(hi_r / 2)


def test_decomposition_and_iteration_span_match_the_store() -> None:
    """57.9-63.3 us, and 375-626 PCG iterations.

    Bug caught: the conditioning exposure being lost. The per-iteration cost
    being flat is what makes the iteration term first-order, and the 375-626
    span against maxiter 1200 is the concrete headroom a sparse class would
    eat. Both are the evidence behind "validity is prior to price".
    """
    d = _mod.surviving_facts()["per_iteration_decomposition"]
    lo, hi = d["microseconds_span"]
    assert lo == pytest.approx(57.9, abs=0.2)
    assert hi == pytest.approx(63.3, abs=0.2)
    assert d["spread_pct"] < 6.0
    assert d["pcg_iterations_span"] == [375, 626]
    assert set(leg["tile"] for leg in d["legs"]) == set(_WALL_S)


def test_convexity_crossover_is_solved_not_asserted(tmp_path: Path) -> None:
    """The 0.638 crossover is computed from the sealed counts.

    Bug caught: the crossover typed. It is the number that showed the
    withdrawn ordering claim was false, so it has to follow the seal — a
    different epoch table must move it.
    """
    seal = tmp_path / "seal.json"
    seal.write_text(
        json.dumps(
            {
                "content": {
                    "epoch_table": [
                        {"epoch_id": "a", "missions": ["m"] * 2, "mask_66": True},
                        {"epoch_id": "b", "missions": ["m"] * 2, "mask_66": True},
                        {"epoch_id": "c", "missions": ["m"] * 5, "mask_66": False},
                    ]
                }
            }
        )
    )
    out = _mod.surviving_facts(seal_path=seal)
    # pre = [2,2], post = [5]: 5^p = 2*2^p has a root near p = 0.7565.
    assert out["convexity_crossover_p"] == pytest.approx(0.7565, abs=0.01)
    assert out["convexity_crossover_p"] != pytest.approx(0.638, abs=0.001)


def test_platform_convention_and_99c_attestation_are_kept() -> None:
    """Both survived every round and are carried forward.

    Bug caught: dropping the facts that held along with the ones that
    failed. The platform convention (~1.28x, four platforms under five
    labels) was never disclosed by any pricing round and is a live trap for
    the next one; the 99(c) attestation is the one thing three reviews
    confirmed unanimously.
    """
    sf = _mod.surviving_facts()
    pc = sf["platform_convention"]
    assert (pc["leg_labels"], pc["leg_platforms"]) == (5, 4)
    assert "1.28x" in pc["note"]
    assert "CAPPED T2 probe" in sf["pin_99c_attestation"]


def test_the_withdrawn_document_is_preserved_not_deleted() -> None:
    """The v3 document is kept as the record of why.

    Bug caught: deleting the overturned document, which would leave the WAIT
    without its reasoning. It is withdrawn as a DELIVERABLE and preserved as
    the record — and the file it names must exist.
    """
    doc = _block()["the_v3_document"]
    assert "WITHDRAWN as a pricing deliverable" in doc["status"]
    assert "PRESERVED" in doc["status"]
    assert Path(doc["path"]).exists()


def test_leg_constellation_matches_the_runner() -> None:
    """LEG_MISSIONS equals the runner's PROBE_MISSIONS.

    Bug caught: the platform-convention finding drifting from the legs it
    describes. The rows carry no mission list, so this is the only check.
    """
    runner = load_script("phase14_stage1_run")
    assert _mod.LEG_MISSIONS == runner.PROBE_MISSIONS
