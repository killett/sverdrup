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


def test_pin2_ruling_pinned_production_representative() -> None:
    """DIVERSE_FRAME_CONVENTION carries the ruled value (ONE constant).

    Bug caught: a drive-by revert to None (or a flip to "isolated") would
    silently re-gate or reshape the four diverse frames after the
    2026-07-25 owner ruling.
    """
    assert _mod.DIVERSE_FRAME_CONVENTION == "production-representative"


@pytest.mark.parametrize("tile", _DIVERSE)
def test_diverse_frames_build_production_representative(tile: str) -> None:
    """Diverse frames build with EMPTY missing_neighbors (ruled pin 2).

    Bug caught: an "isolated" (all-sides-missing) frame would clip the
    solve bbox to the bare core, voiding the Stage-2/2G-representative
    geometry (and its accepted 1.59x node cost) the ruling bought.
    """
    from sverdrup.application.spatial_tiles import operative_halo_deg

    frame = _mod.registry_frame(tile)
    assert frame.missing_neighbors == frozenset()
    assert frame.overlap_deg == 2.0
    assert frame.halo_deg == operative_halo_deg()


def test_southern_solve_bbox_and_node_count_pinned() -> None:
    """Southern solve bbox = core extended 2 deg ALL sides; 96x97 nodes.

    Bug caught: a one-side-only (or missing) extension — e.g. lat_min
    staying -62.0 — would drop the blend margin whose southern obs edge
    (solve lat_min - halo = -65.0) the +/-66 headroom pin protects.
    Expected bbox computed by hand (core +/- 2); node counts measured
    independently with np.arange before pinning (the lat axis carries the
    fp-overshoot extra node, the recorded 43.2N-quirk behavior).
    """
    from sverdrup.application.spatial_tiles import frame_grid

    frame = _mod.registry_frame("southern")
    s = frame.solve_bbox
    assert (s.lon_min, s.lon_max, s.lat_min, s.lat_max) == (
        213.0,
        232.0,
        -64.0,
        -45.0,
    )
    grid = frame_grid(frame, 0.2)
    assert (grid.x.size, grid.y.size) == (96, 97)


def test_pin2_refusal_mechanism_survives_unruled_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With the constant forced back to None the refusal still fires.

    Bug caught: landing the ruling by DELETING the refusal branch instead
    of setting the constant — a future un-ruling (or a new pending
    convention) would then build frames silently.
    """
    monkeypatch.setattr(_mod, "DIVERSE_FRAME_CONVENTION", None)
    with pytest.raises(RuntimeError, match="(?i)owner election"):
        _mod.registry_frame("southern")


def test_run_refuses_unknown_tile() -> None:
    """CLI run refuses a tile not in the registry.

    Bug caught: a typo'd tile name silently sizing (and later solving) an
    unplanned box instead of refusing loudly.
    """
    res = runner.invoke(_mod.app, ["run", "nope"])
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
    res = runner.invoke(_mod.app, ["run", "anchor", "--source", "cmems_my"])
    assert res.exit_code != 0


def test_run_equatorial_reaches_gated_stub_after_pin12_ruling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Equatorial run no longer refuses pin 12; it dies at the solve stub.

    Bug caught: a stale box_election_pending flag (or leftover refusal)
    still blocking the KEPT box after the 2026-07-25 ruling; the stub's
    NotImplementedError (with the seal verifier untouched) also proves no
    solve or evidence write sneaks in behind the ruling.
    """
    from sverdrup.application import ladder

    monkeypatch.setattr(ladder, "tier1_eligible", lambda peak_mib: True)
    with pytest.raises(NotImplementedError, match="Task"):
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


# ---------------------------------------------------------------------------
# Task 2 — measured-first probe (quiet_gyre, one window, m=1)
# ---------------------------------------------------------------------------

# The pinned PROBE row schema (plan Task 2 + owner PIN 23(c); stated here
# independently of the implementation). Deliberately NO "scores" and NO
# "seal_sha": a probe row carrying a µ would be an evaluation-bearing
# artifact. "convergence" is the PIN-23(c) CONVERGED/CAPPED verdict.
_PROBE_KEYS = {
    "label",
    "tile",
    "source",
    "frame",
    "window",
    "m",
    "superobs_cfg",
    "n_obs",
    "n_grid_nodes",
    "wall_s",
    "peak_rss_mib",
    "pcg",
    "convergence",
    "model",
    "measured_vs_model",
    "stop_bracket",
    "date",
}


def _probe_measurement(
    wall_s: float = 100.0,
    peak_rss_mib: float = 1000.0,
    wall_est_s: float = 200.0,
    peak_model_mib: float = 4000.0,
    maxiter: int = 500,
    iterations: int = 12,
    residual: float = 5.0e-7,
) -> dict[str, Any]:
    """Injected fake measurement (defaults: ratios 0.5 / 0.25, both green).

    Both PCG legs (member-batch + mean — the real probe's two log rows)
    share ``iterations``/``residual``; defaults converge well under the
    cap. ``maxiter`` mirrors the CLI pass-through so this helper can stand
    in for ``_probe_solve`` directly.
    """
    return {
        "frame": {"core": [255.0, 270.0, -30.0, -15.0], "overlap_deg": 2.0},
        "window": [14.0, 74.0],
        "superobs_cfg": {"kind": "challenge-coarsen", "n": 5},
        "n_obs": 3000,
        "n_grid_nodes": 9216,
        "wall_s": wall_s,
        "peak_rss_mib": peak_rss_mib,
        "pcg": [
            {
                "window": "w0",
                "kind": "member-batch",
                "iterations": iterations,
                "final_rel_residual": residual,
            },
            {
                "window": "w0",
                "iterations": iterations,
                "final_rel_residual": residual,
            },
        ],
        "pcg_rtol": 1.0e-6,
        "pcg_maxiter": maxiter,
        "model": {"wall_est_s": wall_est_s, "peak_model_mib": peak_model_mib},
    }


def test_probe_row_schema_exactly_pinned() -> None:
    """build_probe_row output keys == the pinned probe set, nothing else.

    Bug caught: a scores/µ block sneaking into the probe row (making an
    evaluation-bearing artifact out of a sizing probe), or a provenance
    key (superobs_cfg, model, stop_bracket, ...) silently dropped.
    """
    row = _mod.build_probe_row(date="2026-07-25", **_probe_measurement())
    assert set(row) == _PROBE_KEYS


def test_probe_row_pins_m1_label_and_registry_source() -> None:
    """Probe row: m == 1 pinned, PROBE label, quiet_gyre tile, cmems_my source.

    Bug caught: the probe running (or reporting) the m=100 production
    default; a STAGE1-EVIDENCE mislabel presenting the probe as a scored
    tile run; source drifting from the registry's Stage-0 pin-4 map.
    """
    row = _mod.build_probe_row(date="2026-07-25", **_probe_measurement())
    assert row["m"] == 1
    assert row["label"] == "PROBE"
    assert row["tile"] == "quiet_gyre"
    assert row["source"] == "cmems_my"
    assert row["date"] == "2026-07-25"


def test_probe_ratios_computed_measured_over_model() -> None:
    """measured_vs_model = measured/model, hand-computed: 100/200, 1000/4000.

    Bug caught: an inverted ratio (model/measured) — a FAST run would then
    read 2.0 and trip the STOP bracket while a 3x-over run would read 0.33
    and sail through, inverting the spend-decision trigger.
    """
    row = _mod.build_probe_row(date="2026-07-25", **_probe_measurement())
    assert row["measured_vs_model"] == {
        "wall_ratio": 0.5,
        "peak_ratio": 0.25,
        "capped_measurement": False,
    }


@pytest.mark.parametrize(
    ("wall_s", "peak_rss_mib", "want_tripped"),
    [
        # model bases: wall_est_s=200, peak_model_mib=4000 (fake above)
        (280.0, 1000.0, True),  # wall 1.4 > 1.3, peak 0.25 — EITHER trips
        (100.0, 5600.0, True),  # wall 0.5, peak 1.4 > 1.3 — EITHER trips
        (100.0, 1000.0, False),  # both under
        (260.0, 5200.0, False),  # both exactly 1.3 — strict >, not >=
    ],
)
def test_probe_stop_bracket_trips_on_either_ratio(
    wall_s: float, peak_rss_mib: float, want_tripped: bool
) -> None:
    """stop_bracket: threshold 1.3, tripped iff EITHER ratio > 1.3 (strict).

    Bug caught: an AND instead of OR (a peak-only blowout undetected — the
    exit-137 class at 6 tiles), or a >= drift tripping exactly-at-bracket
    runs the 1.3x honest-bracket convention accepts.
    """
    row = _mod.build_probe_row(
        date="2026-07-25",
        **_probe_measurement(wall_s=wall_s, peak_rss_mib=peak_rss_mib),
    )
    assert row["stop_bracket"] == {"threshold": 1.3, "tripped": want_tripped}


def test_probe_cli_records_then_stops_on_tripped_bracket(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A tripped bracket exits nonzero AFTER the row is recorded.

    Bug caught: stop-before-record (a silent STOP — the mis-sized-model
    evidence lost exactly when the owner needs it), or a tripped bracket
    exiting 0 and letting the 6-tile full runs launch on a bad model.
    """
    from sverdrup.application import ladder
    from sverdrup.validation import phase14_seal

    monkeypatch.setattr(ladder, "tier1_eligible", lambda peak_mib: True)
    monkeypatch.setattr(phase14_seal, "verify_current_seal", lambda: None)
    evid = tmp_path / "evidence.json"
    monkeypatch.setattr(_mod, "EVIDENCE", evid)
    monkeypatch.setattr(
        _mod, "_probe_solve", lambda maxiter=500: _probe_measurement(wall_s=400.0)
    )  # wall ratio 2.0 — tripped
    res = runner.invoke(_mod.app, ["probe"])
    assert res.exit_code != 0
    stored = json.loads(evid.read_text())
    probe = stored["phase14"]["stage1"]["probe"]
    assert probe["stop_bracket"] == {"threshold": 1.3, "tripped": True}
    assert probe["measured_vs_model"]["wall_ratio"] == 2.0


def test_probe_cli_green_bracket_records_and_exits_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Under-bracket probe exits 0 with the row recorded at stage1.probe.

    Bug caught: the probe exiting nonzero unconditionally (blocking the
    stage on a healthy model), recording at the wrong evidence node, or
    clobbering the standing store (the P0-2 class).
    """
    from sverdrup.application import ladder
    from sverdrup.validation import phase14_seal

    monkeypatch.setattr(ladder, "tier1_eligible", lambda peak_mib: True)
    monkeypatch.setattr(phase14_seal, "verify_current_seal", lambda: None)
    evid = tmp_path / "evidence.json"
    evid.write_text(json.dumps({"phase13": {"kept": True}}))
    monkeypatch.setattr(_mod, "EVIDENCE", evid)
    monkeypatch.setattr(_mod, "_probe_solve", _probe_measurement)
    res = runner.invoke(_mod.app, ["probe"])
    assert res.exit_code == 0
    stored = json.loads(evid.read_text())
    assert stored["phase13"] == {"kept": True}
    probe = stored["phase14"]["stage1"]["probe"]
    assert probe["label"] == "PROBE"
    assert probe["stop_bracket"] == {"threshold": 1.3, "tripped": False}


def test_probe_record_seal_tripwire_fires_before_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """record_probe_row verifies the seal FIRST; on SealError nothing lands.

    Bug caught: probe evidence written into an unsealed context — the
    Task-10 ceremony tripwire skipped on the NEW record path (the tiles
    path being guarded does not guard this one).
    """
    from sverdrup.application import ladder
    from sverdrup.validation import phase14_seal

    def _raise() -> None:
        raise phase14_seal.SealError("SENTINEL-NO-SEAL")

    monkeypatch.setattr(ladder, "tier1_eligible", lambda peak_mib: True)
    monkeypatch.setattr(phase14_seal, "verify_current_seal", _raise)
    evid = tmp_path / "evidence.json"
    monkeypatch.setattr(_mod, "EVIDENCE", evid)
    monkeypatch.setattr(_mod, "_probe_solve", _probe_measurement)
    res = runner.invoke(_mod.app, ["probe"])
    assert res.exit_code != 0
    assert isinstance(res.exception, phase14_seal.SealError)
    assert not evid.exists()


def test_probe_checks_ladder_before_any_solve(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An ineligible probe dies at the Tier-1 ladder; the solve never runs.

    Bug caught: loading CMEMS obs (or solving) before the RAM predicate —
    the OOM/silent-death class the fork-g pin-4 ordering exists to prevent.
    """
    from sverdrup.application import ladder

    solve_calls: list[str] = []

    def _spy(maxiter: int = 500) -> dict[str, Any]:
        solve_calls.append("solved")
        return _probe_measurement(maxiter=maxiter)

    monkeypatch.setattr(ladder, "tier1_eligible", lambda peak_mib: False)
    monkeypatch.setattr(_mod, "_probe_solve", _spy)
    res = runner.invoke(_mod.app, ["probe"])
    assert res.exit_code != 0
    assert isinstance(res.exception, RuntimeError)
    assert "ladder" in str(res.exception)
    assert solve_calls == []


# ---------------------------------------------------------------------------
# Owner ruling PIN 23(a)+(c) — convergence fields in-row, --maxiter option,
# converged re-run node (phase14.stage1.probe_converged)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("iterations", "residual", "want"),
    [
        # rtol 1e-6, maxiter 500 (the fake's defaults). First case is the
        # REAL T2 defect leg: exited AT the 500 cap over rtol.
        (500, 2.84e-6, "CAPPED"),
        (500, 1.0e-6, "CONVERGED"),  # at cap, residual EXACTLY rtol: strict >
        (500, 9.9e-7, "CONVERGED"),  # converged exactly at the cap
        (140, 9.0e-7, "CONVERGED"),  # ordinary converged leg under the cap
    ],
)
def test_probe_row_convergence_verdict_truth_table(
    iterations: int, residual: float, want: str
) -> None:
    """convergence: CAPPED iff a leg sits AT maxiter with residual > rtol.

    Bug caught: the T2 defect class — a 500-cap leg at 2.84e-6 > rtol
    presented as a true measurement; also a residual >= drift (flagging a
    leg that stopped exactly AT rtol) or keying CAPPED on iterations alone
    (mislabeling a run that legitimately converged at the cap).
    """
    row = _mod.build_probe_row(
        date="2026-07-25",
        **_probe_measurement(iterations=iterations, residual=residual),
    )
    assert row["convergence"] == want
    assert row["measured_vs_model"]["capped_measurement"] is (want == "CAPPED")


def test_probe_row_capped_when_any_single_leg_capped() -> None:
    """ONE capped leg among converged legs flags the WHOLE row CAPPED.

    Bug caught: computing the verdict from only the first (or last) log
    leg — the member-batch leg's cap (the T2 member leg at 2.84e-6) would
    be missed when the mean leg happens to converge.
    """
    measurement = _probe_measurement()  # both legs converged (12 iters)
    measurement["pcg"].append(
        {"window": "w0", "iterations": 500, "final_rel_residual": 2.84e-6}
    )
    row = _mod.build_probe_row(date="2026-07-25", **measurement)
    assert row["convergence"] == "CAPPED"
    assert row["measured_vs_model"]["capped_measurement"] is True


def test_probe_pcg_rows_carry_rtol_and_maxiter_in_row() -> None:
    """EVERY recorded pcg leg carries the solver's rtol and maxiter in-row.

    Bug caught: the PIN-23(c) defect (was T2-review LOW) — legs recorded
    without rtol/maxiter, so a future reader cannot tell a CAPPED leg from
    a CONVERGED one without out-of-band solver-config archaeology.
    """
    row = _mod.build_probe_row(
        date="2026-07-25", **_probe_measurement(maxiter=2000, iterations=1740)
    )
    assert len(row["pcg"]) == 2
    for leg in row["pcg"]:
        assert leg["rtol"] == 1.0e-6
        assert leg["maxiter"] == 2000
        assert leg["iterations"] == 1740  # measured fields survive stamping


def test_probe_row_stamping_never_mutates_caller_pcg_legs() -> None:
    """Stamping rtol/maxiter happens on COPIES; caller legs stay untouched.

    Bug caught: in-place stamping — the real caller's leg dicts ARE the
    module-global miost CONVERGENCE_LOG entries, so mutating them would
    corrupt the shared diagnostic log for every later solve this process.
    """
    measurement = _probe_measurement()
    legs_before = [dict(leg) for leg in measurement["pcg"]]
    _mod.build_probe_row(date="2026-07-25", **measurement)
    assert measurement["pcg"] == legs_before
    assert all("maxiter" not in leg for leg in measurement["pcg"])


def test_probe_cli_maxiter_rerun_records_at_probe_converged_preserving_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--maxiter 2000 flows to the solver; the row lands at probe_converged.

    Bug caught: the PIN-23(a) re-run overwriting the historical T2 row at
    phase14.stage1.probe (owner: it stays as history), or --maxiter parsed
    but never passed through — the solver would run at the 500 default
    while the row records 2000 ("the maxiter used must be what the row
    records").
    """
    from sverdrup.application import ladder
    from sverdrup.validation import phase14_seal

    monkeypatch.setattr(ladder, "tier1_eligible", lambda peak_mib: True)
    monkeypatch.setattr(phase14_seal, "verify_current_seal", lambda: None)
    evid = tmp_path / "evidence.json"
    t2_history = {"label": "PROBE", "sentinel": "T2-CAPPED-HISTORY"}
    evid.write_text(json.dumps({"phase14": {"stage1": {"probe": t2_history}}}))
    monkeypatch.setattr(_mod, "EVIDENCE", evid)
    seen: list[int] = []

    def _spy(maxiter: int = 500) -> dict[str, Any]:
        seen.append(maxiter)
        return _probe_measurement(maxiter=maxiter, iterations=1740)

    monkeypatch.setattr(_mod, "_probe_solve", _spy)
    res = runner.invoke(_mod.app, ["probe", "--maxiter", "2000"])
    assert res.exit_code == 0
    assert seen == [2000]
    stored = json.loads(evid.read_text())
    assert stored["phase14"]["stage1"]["probe"] == t2_history
    rerun = stored["phase14"]["stage1"]["probe_converged"]
    assert rerun["convergence"] == "CONVERGED"
    assert rerun["label"] == "PROBE"
    assert all(leg["maxiter"] == 2000 for leg in rerun["pcg"])


def test_probe_cli_default_maxiter_is_the_production_cap_and_probe_node(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Default --maxiter == miost_solver.PCG_MAXITER; default run -> probe node.

    Bug caught: the script's local default drifting from the production
    PCG cap (rows would record a maxiter the production solver does not
    use), or the default run being rerouted to probe_converged (history
    and re-run swapping places).
    """
    from sverdrup.application import ladder
    from sverdrup.methods.miost_solver import PCG_MAXITER
    from sverdrup.validation import phase14_seal

    assert _mod.PROBE_MAXITER_DEFAULT == PCG_MAXITER
    monkeypatch.setattr(ladder, "tier1_eligible", lambda peak_mib: True)
    monkeypatch.setattr(phase14_seal, "verify_current_seal", lambda: None)
    evid = tmp_path / "evidence.json"
    monkeypatch.setattr(_mod, "EVIDENCE", evid)
    seen: list[int] = []

    def _spy(maxiter: int = 0) -> dict[str, Any]:
        seen.append(maxiter)
        return _probe_measurement(maxiter=maxiter)

    monkeypatch.setattr(_mod, "_probe_solve", _spy)
    res = runner.invoke(_mod.app, ["probe"])
    assert res.exit_code == 0
    assert seen == [PCG_MAXITER]
    stored = json.loads(evid.read_text())
    assert "probe" in stored["phase14"]["stage1"]
    assert "probe_converged" not in stored["phase14"]["stage1"]
