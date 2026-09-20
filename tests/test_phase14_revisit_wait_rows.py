"""T7 revisit WAIT-row builder tests (owner pin 230) — CI-local.

The rows record a REFUSAL. The failure mode that matters is not a crash: it
is a row that records the refusal in a shape which misrepresents WHY, and
which a later reader then acts on. Each test below names the misreading it
prevents.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.helpers import load_script

_mod = load_script("phase14_revisit_wait_rows")

# Measured T5 legs, hand-read from phase14.stage1.tiles.<tile> in the store.
# Kept as literals so the tests do not re-derive expectations from the same
# source the builder reads.
_MEASURED_WALL_S: dict[str, float] = {
    "kuroshio": 70811.32452932594,
    "southern": 98929.75216705899,
    "equatorial": 91945.0,
    "quiet_gyre": 93712.97317277198,
}
_MEASURED_PEAK: dict[str, float] = {
    "kuroshio": 7389.3359375,
    "southern": 4951.1640625,
    "equatorial": 4817.0,
    "quiet_gyre": 4986.41796875,
}
# The sealed phase-10 budget (phase10.oi.probe.budget).
_N_SOBOL = 7
_SCREENING_N = 30


def _store() -> dict[str, Any]:
    return {
        "phase14": {
            "stage1": {
                "tiles": {
                    tile: {
                        "wall_s": _MEASURED_WALL_S[tile],
                        "peak_rss_mib": _MEASURED_PEAK[tile],
                    }
                    for tile in _MEASURED_WALL_S
                }
            }
        },
        "phase10": {
            "oi": {
                "probe": {
                    "budget": {
                        "n_sobol_per_lane": _N_SOBOL,
                        "screening": {"n_sobol_per_lane": _SCREENING_N},
                    }
                }
            }
        },
    }


def _row(tile: str = "quiet_gyre") -> dict[str, Any]:
    return _mod.build_revisit_wait_row(
        tile, _store(), n_sobol=_N_SOBOL, screening_n=_SCREENING_N
    )


def test_row_is_a_wait_carrying_the_ruling_that_made_it_one() -> None:
    """The verdict is WAIT and names the pin that ruled it.

    Bug caught: a row recording the sizing without the verdict, or the
    verdict without its authority. Either leaves a successor unable to tell
    a ruled refusal from an unfinished task — which is exactly the state
    pin 224(c) wrote this row to prevent ("a measured WAIT with its cost
    and its exits named, not an empty row").
    """
    row = _row()
    assert row["verdict"] == "WAIT"
    assert "pin 224" in row["verdict_authority"]
    assert row["report_only"] is True


def test_every_lane_passes_the_guard_and_the_row_still_says_wait() -> None:
    """The WAIT/RUN asymmetry is present and explained in the row itself.

    Bug caught — and this is the one that matters (pin 230b): a builder
    that produced the WAIT by marking lanes WAIT would invert the finding.
    Pin 224(b) is that every solve is RUN with 14 h of margin AND the
    aggregate is refused anyway. A row whose per-lane cells read WAIT would
    claim the lanes were unaffordable, which is false and would send a
    reader looking for a cheaper per-lane configuration that already fits.

    A row showing only RUN cells with no explanation fails the other way:
    it reads as an unexplained non-run.
    """
    row = _row()

    assert [e["tier_verdict_per_solve"] for e in row["per_lane"]] == ["RUN", "RUN"]
    assert row["verdict"] == "WAIT"

    why = row["why_wait_despite_all_lanes_run"]
    assert "NOT ONE LANE a WAIT" in why
    assert "does not authorise the aggregate" in why
    # The mechanism, not just the outcome.
    assert "LANE IS NOT ONE LEG" in why


def test_solve_counts_carry_the_anchors_and_exclude_lane_zero() -> None:
    """V = n+1, VL = n+2; lane-0 is not re-solved.

    Bug caught: dropping the anchors (V=n, VL=n) understates the tile by
    3 solves — 14 instead of 17 — and the four-tile total by 12, which is
    an entire anchors-only run's worth of work. The opposite bug, folding
    lane-0 back in, would add 7 more and price a re-solve of the frozen
    config that pin 226 ruled measures the solver, not the lane.

    Anchor counts are `anchors_for`'s: the lane-0 winner goes into V and
    VL, the V winner into VL.
    """
    row = _row()
    by_lane = {e["lane"]: e for e in row["per_lane"]}

    assert set(by_lane) == {"V", "VL"}
    assert (by_lane["V"]["anchors"], by_lane["VL"]["anchors"]) == (1, 2)
    assert by_lane["V"]["solves"] == _N_SOBOL + 1
    assert by_lane["VL"]["solves"] == _N_SOBOL + 2
    assert row["tile_totals"]["solves"] == 17
    assert row["aggregate_refused"]["full_scope"]["solves"] == 68
    assert row["lane_set"]["lanes"]["lane0"] == []
    assert "measure the solver" in row["lane_set"]["lane0_excluded_reason"]


def test_each_tile_is_priced_from_its_own_measured_leg() -> None:
    """Predicted cost uses THAT tile's leg, never a shared basis.

    Bug caught: pricing all four tiles at the quoted 26.03 h basis leg.
    Kuroshio measured 19.67 h, so it would be overstated by 6.36 h on every
    one of its 17 solves — 108 h, on the one tile whose cost is lowest.
    The four-tile total would stop being the sum of four measurements and
    become one measurement multiplied by four.
    """
    kuroshio = _row("kuroshio")
    quiet = _row("quiet_gyre")

    assert kuroshio["measured_leg"]["wall_h"] == pytest.approx(19.6698, abs=1e-3)
    assert quiet["measured_leg"]["wall_h"] == pytest.approx(26.0314, abs=1e-3)
    assert kuroshio["tile_totals"]["wall_h"] == pytest.approx(
        17 * _MEASURED_WALL_S["kuroshio"] / 3600.0
    )
    # The two tiles must not price the same.
    assert kuroshio["tile_totals"]["wall_h"] != quiet["tile_totals"]["wall_h"]


def test_anchors_only_option_carries_its_weaker_claim_verbatim() -> None:
    """Pin 225(b)'s limit travels inside every row.

    Bug caught: the limit living only in the ruling document. A reader who
    pulls this row from the store sees a 12.3-day option that is 5.7x
    cheaper than the refused one and elects it — believing it delivers the
    negative result. It cannot: it speaks only to the lane's DESIGNATED
    configuration. Recording the price without the limit is how the cheap
    option gets adopted for the expensive one's purpose.
    """
    row = _row()
    opt = row["anchors_only_option"]

    assert opt["elected"] is False
    assert opt["solves_per_tile"] == 3
    assert opt["solves_total"] == 12
    assert "STRICTLY WEAKER" in opt["limit"]
    assert "does not beat lane-0 in this regime" in opt["limit"]
    assert 'CANNOT say "no configuration in the lane does."' in opt["limit"]


def test_kuroshio_peak_carries_the_pre_133_caveat() -> None:
    """A non-comparable peak says so, in the row.

    Bug caught: kuroshio's 7,389 MiB presented beside three post-fix peaks
    as though the four were one column. Pin 199 closed that question once;
    a row citing the number bare re-raises it, and the next reader computes
    a spurious ratio against the 4,986 MiB basis.
    """
    kuroshio = _row("kuroshio")["measured_leg"]
    southern = _row("southern")["measured_leg"]

    assert "PRE-133" in kuroshio["peak_caveat"]
    assert "peak_caveat" not in southern


def test_a_tile_with_no_measured_leg_is_refused_not_priced() -> None:
    """An unmeasured tile raises rather than producing a row.

    Bug caught: a missing or renamed tile yielding a row with a null or
    zero wall. It would look complete, price the tile at nothing, and pull
    the four-tile aggregate down by a quarter — the number the owner's
    refusal rests on.
    """
    store = _store()
    del store["phase14"]["stage1"]["tiles"]["southern"]

    with pytest.raises(KeyError, match="no measured leg"):
        _mod.build_revisit_wait_row(
            "southern", store, n_sobol=_N_SOBOL, screening_n=_SCREENING_N
        )


def test_rows_are_built_for_exactly_the_four_diverse_tiles() -> None:
    """Never the anchor, never the seam pair.

    Bug caught: a revisit row appearing at `anchor`, `seam_n` or `seam_s`.
    Those are the identity and seam subjects; a revisit verdict recorded
    against them would assert a per-regime reading the stage never made.
    """
    assert set(_mod.REVISIT_TILES) == {
        "kuroshio",
        "southern",
        "equatorial",
        "quiet_gyre",
    }
    assert {"anchor", "seam_n", "seam_s"}.isdisjoint(_mod.REVISIT_TILES)


def test_build_rows_reads_the_sealed_budget_from_the_store(tmp_path: Path) -> None:
    """Trial counts come from the sealed budget, not from a constant here.

    Bug caught: `n_sobol_per_lane` hardcoded in the script. The budget is
    sealed evidence; if it were ever re-sealed at a different n, a
    hardcoded copy would keep pricing the refusal at the old number while
    citing `phase10.oi.probe.budget` as its source.
    """
    store = _store()
    store["phase10"]["oi"]["probe"]["budget"]["n_sobol_per_lane"] = 9
    path = tmp_path / "store.json"
    path.write_text(json.dumps(store))

    rows = _mod.build_rows(evidence_path=path)

    assert set(rows) == set(_mod.REVISIT_TILES)
    # 9 + 1 and 9 + 2 -> 21 per tile, not 17.
    assert rows["southern"]["tile_totals"]["solves"] == 21
    assert rows["southern"]["aggregate_refused"]["full_scope"]["solves"] == 84
