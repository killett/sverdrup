"""Unit pins for the σ-ELEVATED diagnosis script (phase-14 Stage-1 follow-on).

The heavy legs (map reads, member-store replay, the CRN demonstration) need
the persisted 1.1 GB artifacts and are exercised by running the script; what
is pinned here is the logic that would silently produce a WRONG diagnosis:
the MC-floor arithmetic, the member half-split, and the recording contract
(right namespace, seal-gated, and — load-bearing — the block must never
read as a rubric row).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

_PATH = Path(__file__).resolve().parents[1] / "scripts" / "phase14_sigma_diagnosis.py"
_SPEC = importlib.util.spec_from_file_location("phase14_sigma_diagnosis", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
_mod = importlib.util.module_from_spec(_SPEC)
sys.modules["phase14_sigma_diagnosis"] = _mod
_SPEC.loader.exec_module(_mod)


# --- the MC-floor arithmetic ----------------------------------------------


def test_mc_floor_is_sigma_over_sqrt_m_minus_one() -> None:
    """Hand value: the floor divides by sqrt(m-1), not sqrt(m) or sqrt(2(m-1)).

    Bug caught: the wrong denominator. sqrt(m) would predict 0.00369 where
    0.00371 is true at m=100 and — far more damaging — sqrt(2(m-1)) would
    predict the floor of ONE sigma estimate rather than of the DIFFERENCE
    of two, understating it by sqrt(2) and turning a matching observation
    into a 41% excess that would look like a real seam signal.
    """
    assert _mc(0.7, 50) == pytest.approx(0.1)  # 0.7 / 7
    assert _mc(0.036902, 100) == pytest.approx(0.0037088, rel=1e-4)
    assert _mc(0.036902, 50) == pytest.approx(0.0052717, rel=1e-4)
    # the half-ensemble floor is the sqrt(99/49) = 1.42x LARGER one
    assert _mc(1.0, 50) / _mc(1.0, 100) == pytest.approx(np.sqrt(99.0 / 49.0))


def _mc(sigma: float, m: int) -> float:
    return float(_mod.mc_floor(sigma, m))


def test_mc_floor_refuses_a_single_member() -> None:
    """m=1 has no member-std; the floor must refuse, not divide by zero.

    Bug caught: a silent inf/ZeroDivisionError propagating into the
    recorded block as a nonsense prediction.
    """
    with pytest.raises(ValueError, match="m >= 2"):
        _mod.mc_floor(0.03, 1)


# --- the member half-split -------------------------------------------------


def test_member_halves_are_disjoint_and_equal_and_member_aligned() -> None:
    """The two halves partition the members, identically in every window.

    Bug caught (three of them): (a) overlapping halves — `a[:, :50]` twice,
    or `[:50]`/`[49:]` — which would make the two sigma estimates share
    members, correlate them, and drive RMS(sigma_h1 - sigma_h2) BELOW the
    floor, manufacturing a false refutation; (b) splitting the element
    axis instead of the member axis; (c) taking a different member subset
    per window, which would blend members across windows and destroy the
    coherence of each 50-member sub-ensemble.
    """
    anoms = {
        "w1": np.arange(3 * 6, dtype=float).reshape(3, 6),
        "w2": np.arange(3 * 6, dtype=float).reshape(3, 6) + 100.0,
    }
    first, second = _mod.member_halves(anoms)
    assert set(first) == set(second) == {"w1", "w2"}
    for w in ("w1", "w2"):
        assert first[w].shape == second[w].shape == (3, 3)
        np.testing.assert_array_equal(first[w], anoms[w][:, :3])
        np.testing.assert_array_equal(second[w], anoms[w][:, 3:])
        # disjoint: no member column appears in both halves
        assert not set(map(tuple, first[w].T)) & set(map(tuple, second[w].T))
    # member-aligned: the SAME column indices in every window
    np.testing.assert_array_equal(first["w2"] - 100.0, first["w1"])


def test_member_halves_refuses_an_odd_or_ragged_ensemble() -> None:
    """Unequal halves would carry different noise floors; refuse instead.

    Bug caught: an m=99 store split 50/49 whose two halves have floors
    differing by 1%, silently biasing the comparison against the
    prediction; and a store whose windows disagree on m, which would
    produce halves that are not one sub-ensemble at all.
    """
    with pytest.raises(ValueError, match="odd"):
        _mod.member_halves({"w1": np.zeros((2, 5))})
    with pytest.raises(ValueError, match="disagree"):
        _mod.member_halves({"w1": np.zeros((2, 4)), "w2": np.zeros((2, 6))})
    with pytest.raises(ValueError, match="no windows"):
        _mod.member_halves({})


def test_half_split_of_independent_gaussians_lands_on_the_predicted_floor() -> None:
    """End-to-end check of the claim the diagnosis rests on.

    Draws m=100 genuinely independent members with a known sigma, splits
    them 50/50 through `member_halves`, and confirms that the RMS
    difference of the two half-ensemble stds matches `mc_floor(sigma, 50)`.

    Bug caught: the whole prediction being wrong — if `mc_floor` and the
    split did not agree with what independent members actually do, the
    recorded "observed / predicted ~ 1" would be an artifact of the
    arithmetic rather than evidence about the ensemble.
    """
    rng = np.random.default_rng(20260727)
    sigma, n_nodes = 0.037, 20000
    members = rng.normal(0.0, sigma, size=(n_nodes, 100))
    first, second = _mod.member_halves({"w": members})
    s1 = first["w"].std(axis=1, ddof=1)
    s2 = second["w"].std(axis=1, ddof=1)
    observed = float(np.sqrt(np.mean((s1 - s2) ** 2)))
    predicted = _mod.mc_floor(sigma, 50)
    assert observed == pytest.approx(predicted, rel=0.02)
    # and it is genuinely LARGER than the m=100 floor, the direction that
    # discriminates MC noise from a seam artifact
    assert observed > _mod.mc_floor(sigma, 100)


def test_rms_pools_only_finite_values_and_refuses_an_empty_pool() -> None:
    """Land NaNs are dropped, not propagated; an all-NaN pool refuses.

    Bug caught: a single NaN node poisoning every recorded number to nan,
    or an all-NaN field silently reporting nan as a "result".
    """
    assert _mod.rms(np.array([3.0, np.nan, 4.0])) == pytest.approx(3.5355339)
    with pytest.raises(ValueError, match="no finite"):
        _mod.rms(np.array([np.nan, np.nan]))


# --- the recording contract ------------------------------------------------


def _block() -> dict[str, Any]:
    return {"label": _mod.DIAGNOSIS_LABEL, "question": _mod.QUESTION, "confirmed": []}


def test_record_writes_the_diagnosis_namespace_and_merges(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The block lands at phase14.stage1.seam_sigma_diagnosis, beside the rows.

    Bug caught: recording into `seam_rows` (which would splice a diagnosis
    into the sealed rubric list the Gate-1 pack reads as verdicts), or
    clobbering the standing evidence store.
    """
    from sverdrup.validation import phase14_seal

    monkeypatch.setattr(phase14_seal, "verify_current_seal", lambda: None)
    evid = tmp_path / "evidence.json"
    evid.write_text(
        json.dumps({"phase14": {"stage1": {"seam_rows": [{"kept": True}]}}})
    )
    _mod.record_sigma_diagnosis(_block(), evidence_path=evid)
    stored = json.loads(evid.read_text())
    assert stored["phase14"]["stage1"]["seam_rows"] == [{"kept": True}]
    assert stored["phase14"]["stage1"]["seam_sigma_diagnosis"]["label"] == "DIAGNOSIS"


def test_record_is_seal_gated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No verified seal -> nothing is written (the Task-10 tripwire).

    Bug caught: an evaluation-bearing block written while the sealed set
    cannot be verified.
    """
    from sverdrup.validation import phase14_seal

    def _boom() -> None:
        raise phase14_seal.SealError("no seal")

    monkeypatch.setattr(phase14_seal, "verify_current_seal", _boom)
    evid = tmp_path / "evidence.json"
    with pytest.raises(phase14_seal.SealError):
        _mod.record_sigma_diagnosis(_block(), evidence_path=evid)
    assert not evid.exists()


def test_assembled_block_never_reads_as_a_rubric_row() -> None:
    """No verdict, no rubric cell, no score anywhere in the recorded block.

    Bug caught: the diagnosis acquiring verdict-shaped keys and being
    mistaken for (or mechanically consumed as) a fifth rubric row — the
    exact failure the owner ruled out. Checked over the WHOLE nested
    block, not just its top level, because a nested "verdict" would be
    read by any consumer walking the tree.
    """
    block = _mod.build_diagnosis_block(
        strip_reads={
            "line_1_magnitude": {
                "observed_rms_sigma_delta_m": 0.0036,
                "predicted_mc_floor_sigma_over_sqrt_m_minus_1_m": 0.0037,
            }
        },
        half_split={"seam_n": {"observed_rms_sigma_half1_minus_half2_m": 0.0052}},
        mechanism={"B_same_physical_element_seam_n_vs_seam_s": {}},
        seal_sha="deadbeef",
        date="2026-07-27",
    )
    banned = {
        "verdict",
        "verdict_sigma",
        "rubric_cell",
        "score",
        "pass",
        "attributable",
    }

    def keys(node: Any) -> set[str]:
        if isinstance(node, dict):
            return set(node) | set().union(*(keys(v) for v in node.values()), set())
        if isinstance(node, list):
            return set().union(*(keys(v) for v in node), set())
        return set()

    assert not keys(block) & banned
    assert block["label"] == "DIAGNOSIS"
    assert "no verdict cell is assigned" in block["not_a_rubric_row"]
    # the subject line may QUOTE the recorded row, but only as identification
    assert block["subject"]["rubric_cell_as_recorded"] == "ELEVATED"
    assert block["refuted"] and block["confirmed"]
