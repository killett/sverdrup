"""Refresh-election record tests (owner pins 255-259) — CI-local.

The six-mission production refresh is **ELECTED** (pin 255), and pin 259(b)
puts that outcome in the evidence store at the pre-registered node
``phase14.stage1.refresh_election``.

⛔ The failure mode these tests guard is **the C-11 defect itself**: a
successor reading a *presented question* as an *answered one*. Pin 136 created
task 23 because T9 could only post the presumptive rule with the decision cell
EMPTY. A test that merely checks the node parses would let that state return
under a different spelling. These pin the OUTCOME, the two Stage-2 obligations
that ride with it, and the 258 firewall — and they fail if the node ever
implies the election spent a touch or remedied the weak-signal finding.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.helpers import load_script

_mod = load_script("phase14_refresh_election")

# The Phase-13 close recorded the honest tally in those words: "{miost5: 3,
# miost6: 1} c2 touches". Pinned here as a LITERAL from that record, not read
# back from the same store the record under test reads — so a tally that moves
# fails this test instead of agreeing with itself.
_TALLY_AT_PHASE13_CLOSE = {"miost5": 3, "miost6": 1}


def _block() -> dict[str, Any]:
    return _mod.election_record()


def test_the_outcome_is_elected_with_its_scope_and_authority() -> None:
    """The node records the ruled OUTCOME, not the presented question.

    Bug caught: the C-11 defect returning — a node that carries the
    presumptive rule with an empty decision cell (the exact state T9 left,
    pin 136b) and is then read as the election's answer. If ``outcome``
    were ever written back to None/EMPTY, or the scope dropped, this fails.
    """
    b = _block()
    assert b["outcome"] == "ELECTED"
    assert b["scope"] == "Stage-2G assembly runs onward, as the spec named it (1-8)"
    assert "pin 255" in b["outcome_authority"]
    assert "PART 59" in b["outcome_authority"]

    # The states this node must never be in again.
    assert b.get("decision_cell") != "EMPTY"
    assert b["outcome"] is not None
    assert b["presented_rule_is_not_the_decision"]


def test_no_touch_is_spent_and_the_tally_is_the_phase13_close_tally() -> None:
    """BUNDLED means the c2 tally does not move (pin 255c).

    Bug caught: recording the election as having spent a c2 touch. The
    Phase-13 deferral said the refresh runs with its OWN chain + touch, so
    the natural (and wrong) reading of "elected" is that a touch was just
    consumed. The owner ruled the opposite: it rides 2G's chain and shares
    its touch. A drifted or hand-pasted tally fails the literal below.
    """
    ct = _block()["chain_and_touch"]
    assert ct["mode"] == "BUNDLED"
    assert ct["touch_spent_now"] is False
    assert ct["c2_touch_tally_observed"] == _TALLY_AT_PHASE13_CLOSE
    assert ct["tally_untouched_by_this_ruling"] is True
    assert "global-domain transition" in ct["bundling_rule_verbatim"]


def test_the_tally_is_read_from_the_store_not_from_the_script() -> None:
    """The recorded tally is the store's own, by node path.

    Bug caught: the tally being frozen into the script as a constant, so a
    later Phase-13 correction to the store leaves the witnessed node quietly
    disagreeing with the evidence it claims to observe.
    """
    b = _block()
    path = b["chain_and_touch"]["c2_touch_tally_source"]
    assert path == "phase13.miost.c2_acceptance.c2_touch_tally"

    store = json.loads(_mod.EVIDENCE.read_text())
    node: Any = store
    for key in path.split("."):
        node = node[key]
    assert b["chain_and_touch"]["c2_touch_tally_observed"] == node


def test_it_reunifies_and_is_not_a_mission_count_change() -> None:
    """What the election joins, in the ruling's own terms (pin 255d).

    Bug caught: a successor reading the election as adding a sixth mission
    to SHIPPED. SHIPPED has been six-mission since the Phase-12 flip; what
    it lacks is structured R. Losing that sentence turns a reunification
    into an apparent scope increase nobody authorised.
    """
    r = _block()["what_it_reunifies"]
    assert r["shipped_is_already_six_mission"] is True
    assert r["shipped_factory"] == "shipped_miost6"
    assert r["shipped_flip"] == "b4878a0"
    assert r["structured_r_winner_is_five_mission"] is True
    assert r["is_a_mission_count_change"] is False


def test_delta_j3_is_provisional_and_is_not_a_condition_of_the_election() -> None:
    """δ_j3 := δ_j2n is inherited, never fitted (pin 256).

    Bug caught: the inherited value being read as a fitted one. j3 was the
    validation holdout, so no five-mission contrast ever fit it. The second
    half matters as much: if a successor treated δ_j3 as a *condition*, a
    Stage-2 refit would look like it reopens the election, which 256(b)
    rules it does not.
    """
    d = _block()["delta_j3"]
    assert d["rule"] == "δ_j3 := δ_j2n"
    assert d["status"] == "PROVISIONAL"
    assert d["fitted"] is False
    assert d["is_a_condition_of_the_election"] is False
    assert "E7" in d["governed_by"]
    assert "election stands unchanged" in d["if_stage2_fits_it"]


def test_e10_needs_a_replacement_holdout_before_2g_runs() -> None:
    """The holdout consequence is a precondition, unresolved (pin 257).

    Bug caught: 2G running on the elected config while j3 — the holdout
    every Stage-1 transfer reading is validated against — has been
    assimilated, leaving e10 with no holdout at all. Recording this as a
    note rather than a precondition is how that happens quietly.
    """
    e = _block()["e10_holdout_consequence"]
    assert e["is_a_precondition_on_2g"] is True
    assert e["resolved"] is False
    assert "fork C" in e["selection_criteria"]
    assert "does not run" in e["statement"]


def test_the_election_claims_nothing_about_the_transfer_result() -> None:
    """The 258 firewall is in the record, and nothing breaches it.

    Bug caught — the specific way this node would regress: a helpful
    sentence saying the sixth mission raises observation density and should
    therefore help the two tiles whose λx is absent. Nothing recorded
    supports that, and 258 forbids any record from implying it. The scan
    below is over every field except the firewall's own wording, which must
    say the forbidden thing in order to forbid it.
    """
    b = _block()
    firewall = b["makes_no_claim_about_the_transfer_result"]
    assert "firewalled and open" in firewall
    assert "must not be cited as a remedy" in firewall

    # Quoted material is excluded, at any depth: a `*_verbatim` field is the
    # owner's words, not this record's claim, and the owner's own bundling
    # rule contains the word "improvement". What is scanned is everything
    # this node says in its OWN voice.
    def strip_quotes(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {
                k: strip_quotes(v)
                for k, v in obj.items()
                if not k.endswith("_verbatim")
            }
        if isinstance(obj, list):
            return [strip_quotes(v) for v in obj]
        return obj

    scanned = strip_quotes(b)
    scanned.pop("makes_no_claim_about_the_transfer_result")
    text = json.dumps(scanned, ensure_ascii=False).lower()
    for banned in ("remed", "improve", "recover", "resolve the absence", "helps"):
        assert banned not in text, banned


def test_pins_255_to_258_are_carried_verbatim_and_259_is_not() -> None:
    """The node quotes the landed ruling, and only the outcome pins.

    Bug caught: the node paraphrasing the ruling, so the witnessed record
    and the ruling document drift apart — the failure the whole verbatim
    discipline (pins 41/48) exists to prevent. The 259 half catches the
    opposite error: recording the MECHANICS pin (how to mark tasks) as if
    it were part of the outcome Stage 2 inherits.
    """
    v = _block()["ruling_verbatim"]
    assert set(v) == {"255", "256", "257", "258"}

    # Sentences taken by hand from the owner's ruling, not from the parser.
    assert (
        "NO TOUCH IS SPENT NOW. The c2 tally is untouched by this ruling." in v["255"]
    )
    assert "OUTCOME: ELECTED." in v["255"]
    assert "supplies an inherited value, not a fitted one" in v["256"]
    assert "e10's replacement holdout is chosen and sealed" in v["257"]
    assert "It must not be cited as a remedy for the weak-signal finding" in v["258"]

    # 259 is the mechanics pin. It rules how tasks 23/24 are marked; it is
    # not part of what Stage 2 inherits.
    assert "Mark it completed with this pin" not in json.dumps(v, ensure_ascii=False)


def test_an_unlanded_ruling_refuses_to_record_instead_of_writing_an_empty_quote(
    tmp_path: Path,
) -> None:
    """Missing PART 59 raises; it does not yield a blank verbatim block.

    Bug caught: writing the witnessed node from a tree where the ruling is
    NOT landed — a node citing a ruling that is not at HEAD, with an empty
    or partial quote nobody notices (pins 41/48). Silent degradation here
    is worse than a crash, so the crash is the contract.
    """
    stub = tmp_path / "ruling.md"
    stub.write_text("# a ruling with no PART 59 in it\n")
    with pytest.raises(RuntimeError, match="PART 59"):
        _mod.pins_verbatim(ruling_path=stub)

    truncated = tmp_path / "truncated.md"
    truncated.write_text(
        "## PART 59 — x (verbatim), pins 255–259, 2026-09-21\n\n"
        "> **255. THE SIX-MISSION-REFRESH ELECTION: ELECTED, BUNDLED.**\n"
    )
    with pytest.raises(RuntimeError, match="256"):
        _mod.pins_verbatim(ruling_path=truncated)
