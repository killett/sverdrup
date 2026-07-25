"""Stage-1 per-tile run driver unit tests (phase-14 Stage-1 Task 1) — CI-local.

Covers the CI-testable core ONLY: registry shape/refusals, seam-frame pins,
evidence-row assembly with injected fakes, the seal tripwire, and the
Tier-1-before-load ordering. No data beyond the checkout is touched.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from typer.testing import CliRunner

from tests.helpers import load_script

_mod = load_script("phase14_stage1_run")
runner = CliRunner()

# The pinned evidence-row schema (plan Task 1; no free-prose field).
_PINNED_KEYS = {
    "seal_sha",
    "tile",
    "source",
    "frame",
    "window_plan",
    "m",
    "superobs_cfg",
    "n_obs",
    "wall_s",
    "peak_rss_mib",
    "pcg",
    "scores",
    "reference_row",
    "bridge_caveat",
    "label",
    "date",
}

# Review pin 7 — test-pinned VERBATIM (stated here independently of the
# implementation; any drift in the script's constant fails this file).
_PINNED_CAVEAT = (
    "cross-lineage reading; golden-tile bridge delta MEASURED ON THE ANCHOR "
    "BOX (mu -0.012457 their_eval-scale, map RMS 4.10 cm); its magnitude at "
    "THIS tile is unmeasured; interpretation WAITS on the owner attribution "
    "readout"
)

_PINNED_REFERENCE_ROW = {
    "kind": "raw-sigma + scalar-s* transfer",
    "label": "REFERENCE-ONLY, NOT CALIBRATED",
}

_DIVERSE = ("equatorial", "southern", "quiet_gyre", "kuroshio")


def _row_kwargs(tile: str) -> dict[str, Any]:
    """Injected fakes for one evidence row (values arbitrary but distinct)."""
    return {
        "seal_sha": "cafe" * 16,
        "tile": tile,
        "frame": {"core": [295.0, 305.0, 33.0, 43.0], "overlap_deg": 2.0},
        "window_plan": {"n_windows": 9, "w_days": 60.0},
        "m": 3,
        "superobs_cfg": None,
        "n_obs": 12345,
        "wall_s": 1.5,
        "peak_rss_mib": 100.25,
        "pcg": [{"window": "w0", "iters": 10}],
        "scores": {"mu": 0.9},
        "date": "2026-07-25",
    }


def test_registry_anchor_frame_is_the_existing_anchor_frame() -> None:
    """registry_frame("anchor") node arrays == anchor_frame() at 0.2 deg.

    Bug caught: reconstructing TileFrame(core, overlap_deg=2.0, ...) instead
    of CONSUMING anchor_frame() widens the solve bbox by the overlap and
    yields 71x72 nodes instead of the signed 51x52 gate-5 substrate.
    """
    from sverdrup.application.spatial_tiles import anchor_frame, frame_grid

    got = frame_grid(_mod.registry_frame("anchor"), 0.2)
    want = frame_grid(anchor_frame(), 0.2)
    assert np.array_equal(got.x, want.x)
    assert np.array_equal(got.y, want.y)
    # Independent pin from the plan text: the signed grid is 51x52 nodes.
    assert got.x.size == 51
    assert got.y.size == 52


def test_seam_frames_pinned_sides_and_solve_bboxes() -> None:
    """Seam frames: pinned missing_neighbors and 2-deg-to-the-seam bboxes.

    Bug caught: a flipped seam side (e.g. seam_n missing "S" instead of
    "N") extends the solve bbox AWAY from the 38N seam, destroying the
    seam ORACLE's blend overlap at the seam.
    """
    from sverdrup.application.spatial_tiles import operative_halo_deg

    n = _mod.registry_frame("seam_n")
    s = _mod.registry_frame("seam_s")
    assert n.missing_neighbors == frozenset({"W", "E", "N"})
    assert s.missing_neighbors == frozenset({"W", "E", "S"})
    nb = n.solve_bbox
    sb = s.solve_bbox
    assert (nb.lon_min, nb.lon_max, nb.lat_min, nb.lat_max) == (
        295.0,
        305.0,
        36.0,
        43.0,
    )
    assert (sb.lon_min, sb.lon_max, sb.lat_min, sb.lat_max) == (
        295.0,
        305.0,
        33.0,
        40.0,
    )
    assert n.overlap_deg == 2.0
    assert s.overlap_deg == 2.0
    assert n.halo_deg == operative_halo_deg()
    assert s.halo_deg == operative_halo_deg()


@pytest.mark.parametrize("tile", _DIVERSE)
def test_diverse_frames_refuse_while_election_pending(tile: str) -> None:
    """Diverse-tile frames REFUSE while DIVERSE_FRAME_CONVENTION is None.

    Bug caught: silently defaulting missing_neighbors would build the four
    diverse frames under a convention the owner never ruled (plan pin 2).
    """
    assert _mod.DIVERSE_FRAME_CONVENTION is None  # the unruled state pinned
    with pytest.raises(RuntimeError, match="(?i)owner election"):
        _mod.registry_frame(tile)


def test_run_refuses_unknown_tile() -> None:
    """CLI run refuses a tile not in the registry.

    Bug caught: a typo'd tile name silently sizing (and later solving) an
    unplanned box instead of refusing loudly.
    """
    res = runner.invoke(_mod.app, ["nope"])
    assert res.exit_code != 0
    assert "unknown tile" in res.output


def test_run_has_no_source_option() -> None:
    """The run command has NO --source option — the source map is pinned.

    Bug caught: a --source escape hatch running e.g. the anchor on cmems_my
    and silently voiding the dc2021a-lineage identity gate (source map is
    registry-pinned provenance, never a CLI choice).
    """
    params = inspect.signature(_mod.run).parameters
    assert not any("source" in name for name in params)
    res = runner.invoke(_mod.app, ["anchor", "--source", "cmems_my"])
    assert res.exit_code != 0


def test_run_equatorial_refuses_on_pin12_before_any_frame_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """run("equatorial") refuses on pin 12 BEFORE any frame/preflight work.

    Bug caught: sizing or loading the unelected equatorial box first would
    do (and record) work under a box the owner may re-rule; the booby-trapped
    frame/preflight hooks prove the refusal fires first.
    """

    def _boom(*args: object, **kwargs: object) -> object:
        raise AssertionError("frame/load work ran before the pin-12 check")

    monkeypatch.setattr(_mod, "registry_frame", _boom)
    monkeypatch.setattr(_mod, "preflight", _boom)
    with pytest.raises(RuntimeError, match="pin 12"):
        _mod.run("equatorial")


def test_evidence_row_schema_is_exactly_the_pinned_set() -> None:
    """build_evidence_row output keys == the pinned schema set, nothing else.

    Bug caught: a free-prose field sneaking into the evidence store, or a
    provenance key (seal_sha, superobs_cfg, ...) silently dropped.
    """
    row = _mod.build_evidence_row(**_row_kwargs("anchor"))
    assert set(row) == _PINNED_KEYS


def test_evidence_row_anchor_semantics() -> None:
    """Anchor row: dc2021a source, NO caveat, NO reference row, quoted sha.

    Bug caught: the anchor (the calibrated identity gate) getting the
    REFERENCE-ONLY transfer row or the cross-lineage caveat would
    misrepresent the one tile whose scores ARE calibrated.
    """
    row = _mod.build_evidence_row(**_row_kwargs("anchor"))
    assert row["seal_sha"] == "cafe" * 16
    assert row["source"] == "dc2021a"
    assert row["bridge_caveat"] is None
    assert row["reference_row"] is None
    assert row["label"] == "STAGE1-EVIDENCE"
    assert row["date"] == "2026-07-25"


@pytest.mark.parametrize("tile", _DIVERSE)
def test_evidence_row_cmems_tiles_carry_pinned_bridge_caveat(tile: str) -> None:
    """cmems_my tiles carry the VERBATIM bridge caveat + transfer reference.

    Bug caught: a paraphrased caveat (review pin 7 pins the string — the
    bridge delta carries its own provenance and disclaims transfer) or a
    caveat keyed off the wrong source.
    """
    row = _mod.build_evidence_row(**_row_kwargs(tile))
    assert row["source"] == "cmems_my"
    assert row["bridge_caveat"] == _PINNED_CAVEAT
    assert row["reference_row"] == _PINNED_REFERENCE_ROW


def test_evidence_row_seam_reference_only_no_caveat() -> None:
    """dc2021a non-anchor tiles: transfer reference row, NO bridge caveat.

    Bug caught: keying the caveat off "non-anchor" instead of the source
    would stamp the cross-lineage disclaimer on same-lineage seam tiles.
    """
    for tile in ("seam_n", "seam_s"):
        row = _mod.build_evidence_row(**_row_kwargs(tile))
        assert row["source"] == "dc2021a"
        assert row["bridge_caveat"] is None
        assert row["reference_row"] == _PINNED_REFERENCE_ROW


def test_build_evidence_row_pure_and_unaliased() -> None:
    """Same inputs -> equal rows; mutating one row never leaks into the next.

    Bug caught: returning a shared module-level reference_row dict — a
    caller mutation would corrupt every subsequent tile's evidence row.
    """
    a = _mod.build_evidence_row(**_row_kwargs("seam_n"))
    b = _mod.build_evidence_row(**_row_kwargs("seam_n"))
    assert a == b
    a["reference_row"]["label"] = "TAMPERED"
    # Independent expectation, NOT a fresh-vs-b comparison: under the
    # shared-dict bug b would be tampered too and tampered-vs-tampered
    # would still compare equal.
    fresh = _mod.build_evidence_row(**_row_kwargs("seam_n"))
    assert fresh["reference_row"] == _PINNED_REFERENCE_ROW
    assert b["reference_row"] == _PINNED_REFERENCE_ROW


def test_record_refuses_when_seal_unverified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """record_evidence_row calls verify_current_seal; its raise propagates.

    Bug caught: Stage-1 evidence recorded into an unsealed context (the
    Task-10 ceremony tripwire skipped) — nothing may be written when no
    verified seal exists.
    """
    from sverdrup.validation import phase14_seal

    def _raise() -> None:
        raise phase14_seal.SealError("SENTINEL-NO-SEAL")

    monkeypatch.setattr(phase14_seal, "verify_current_seal", _raise)
    evid = tmp_path / "evidence.json"
    row = _mod.build_evidence_row(**_row_kwargs("anchor"))
    with pytest.raises(phase14_seal.SealError, match="SENTINEL-NO-SEAL"):
        _mod.record_evidence_row(row, evidence_path=evid)
    assert not evid.exists()


def test_record_writes_row_under_stage1_tiles_preserving_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The row lands at phase14.stage1.tiles.<tile>; the store survives.

    Bug caught: clobbering the standing evidence store (the P0-2 class) or
    writing the row at the wrong node so Gate 1 cannot find it.
    """
    from sverdrup.validation import phase14_seal

    calls: list[str] = []
    monkeypatch.setattr(
        phase14_seal, "verify_current_seal", lambda: calls.append("verified")
    )
    evid = tmp_path / "evidence.json"
    evid.write_text(json.dumps({"phase13": {"kept": True}}))
    row = _mod.build_evidence_row(**_row_kwargs("seam_s"))
    _mod.record_evidence_row(row, evidence_path=evid)
    stored = json.loads(evid.read_text())
    assert stored["phase13"] == {"kept": True}
    assert stored["phase14"]["stage1"]["tiles"]["seam_s"] == row
    assert calls == ["verified"]


def test_preflight_refuses_when_tier1_ineligible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """preflight raises naming the ladder when tier1_eligible says no.

    Bug caught: launching a solve whose predicted peak exceeds measured
    headroom (the exit-137 OOM class, fork-g pin 4) instead of WAITing.
    """
    from sverdrup.application import ladder

    seen: list[float] = []

    def _no(peak_mib: float) -> bool:
        seen.append(peak_mib)
        return False

    monkeypatch.setattr(ladder, "tier1_eligible", _no)
    with pytest.raises(RuntimeError, match="ladder"):
        _mod.preflight("anchor", m=1)
    # the predicate saw the sizing model's peak, a real positive MiB figure
    assert len(seen) == 1
    assert seen[0] > 0.0


def test_run_checks_ladder_before_any_load(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An ineligible run dies at the ladder, never reaching the solve leg.

    Bug caught: loading obs before the Tier-1 check (the OOM lesson) — an
    ineligible run must fail with the ladder refusal, NOT the solve-leg
    NotImplementedError that sits behind it.
    """
    from sverdrup.application import ladder

    monkeypatch.setattr(ladder, "tier1_eligible", lambda peak_mib: False)
    with pytest.raises(RuntimeError, match="ladder"):
        _mod.run("seam_n")


def test_run_reaches_gated_solve_stub_when_eligible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An eligible run hits the solve-leg stub naming its owning tasks.

    Bug caught: the CI core silently "succeeding" without a solve — the
    stub must refuse loudly and name the later gated tasks that own the
    real legs.
    """
    from sverdrup.application import ladder

    monkeypatch.setattr(ladder, "tier1_eligible", lambda peak_mib: True)
    with pytest.raises(NotImplementedError, match="Task"):
        _mod.run("seam_n")
