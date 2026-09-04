"""Stage-1 per-tile run driver unit tests (phase-14 Stage-1 Task 1) — CI-local.

Covers the CI-testable core ONLY: registry shape/refusals, seam-frame pins,
evidence-row assembly with injected fakes, the seal tripwire, and the
Tier-1-before-load ordering. No data beyond the checkout is touched.
"""

from __future__ import annotations

import functools
import inspect
import json
import os
import re
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
    "convergence",
    "scores",
    "reference_row",
    "bridge_caveat",
    "sigma_caveat",
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

# Owner pin 94 — test-pinned VERBATIM (stated here independently of the
# implementation, exactly as the bridge caveat is): the raw-sigma row cannot
# be built without it, and 94(f) scopes the defect honestly.
_PINNED_SIGMA_CAVEAT = (
    "per-tile sigma level under THIS tile's own CRN origin; the deferred CRN "
    "production defect (phase14.stage1.crn_production_defect_deferred) is a "
    "property of the SHIPPED SYSTEM, not of an instrument; cross-tile sigma "
    "comparison is NOT supported and the boundary gradient is DEFERRED and "
    "unmeasured; the within-tile sigma level is NOT compromised - the four "
    "diverse tiles are pairwise disjoint and only seam_n/seam_s are adjacent"
)

_PINNED_REFERENCE_ROW = {
    "kind": "raw-sigma + scalar-s* transfer",
    "label": "REFERENCE-ONLY, NOT CALIBRATED",
}

_DIVERSE = ("equatorial", "southern", "quiet_gyre", "kuroshio")


_REAL_DATA_ROOT = Path("data/2021a_ssh_mapping_ose/ours")


@pytest.fixture(autouse=True)
def _sandbox_stage1_paths(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Owner pin 110(a): no test in this module may reach the real data tree.

    The two strays (a STAGE1-EVIDENCE-labeled track and a pcg checkpoint
    directory) were written into the production evidence directory by a test
    that reached ``_solve_leg`` with the real module paths live. Redirecting
    here makes that structurally impossible rather than a thing every future
    test must remember.
    """
    root = tmp_path_factory.mktemp("stage1_sandbox")
    monkeypatch.setattr(_mod, "STAGE1_DIR", root / "phase14_stage1")
    monkeypatch.setattr(_mod, "EVIDENCE", root / "evidence.json")
    monkeypatch.setattr(_mod, "LANE0_DIR", root / "phase14_stage1" / "equatorial_lane0")


def _data_tree_inventory() -> set[str]:
    """Every path under the real Stage-1 data directory (names + mtimes)."""
    root = _REAL_DATA_ROOT / "phase14_stage1"
    if not root.exists():
        return set()
    return {f"{p.relative_to(root)}:{p.stat().st_mtime_ns}" for p in root.rglob("*")}


class _SolveStopped(Exception):
    """Sentinel: the leg reached the point under test and went no further."""


class _FakeLoad:
    """Stand-in for the data loader (the one true external boundary here)."""

    @staticmethod
    def for_tile(tile: str) -> tuple[Any, Any, Any, dict[str, Any] | None]:
        """The (frame, grid, framed, superobs_cfg) tuple _solve_leg expects."""
        from types import SimpleNamespace

        grid = SimpleNamespace(x=np.zeros(3), y=np.zeros(4), shape=(4, 3))
        framed = SimpleNamespace(
            values=lambda: np.zeros(5), mission=np.array(["alg"] * 5)
        )
        return _mod.registry_frame(tile), grid, framed, None


def _row_kwargs(
    tile: str,
    *,
    iterations: int = 443,
    residual: float = 9.94e-7,
    maxiter: int = 1200,
) -> dict[str, Any]:
    """Injected fakes for one evidence row (values arbitrary but distinct).

    The two pcg legs mirror the real per-window CONVERGENCE_LOG shape (the
    mean leg plus the ``kind="member-batch"`` leg); the defaults are the
    anchor gate's measured w-00018.0 member leg, comfortably converged.
    """
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
        "pcg": [
            {
                "window": "w-00018.0+60",
                "iterations": iterations,
                "final_rel_residual": residual,
            },
            {
                "window": "w-00018.0+60",
                "kind": "member-batch",
                "iterations": iterations,
                "final_rel_residual": residual,
            },
        ],
        "pcg_rtol": 1.0e-6,
        "pcg_maxiter": maxiter,
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
    """Equatorial run no longer refuses pin 12; it reaches the Tier-2 gate.

    Bug caught: a stale box_election_pending flag (or leftover refusal)
    still blocking the KEPT box after the 2026-07-25 ruling. The refusal
    it DOES hit is the headroom gate (forced short here), which also
    proves no solve or evidence write sneaks in behind the ruling.
    """
    from sverdrup.application import ladder

    monkeypatch.setattr(ladder, "tier1_eligible", lambda peak_mib: True)
    monkeypatch.setattr(_mod, "_mem_available_mib", lambda: 100.0)
    with pytest.raises(RuntimeError, match="Tier-2") as excinfo:
        _mod.run("equatorial")
    assert "box_election" not in str(excinfo.value)


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


# The pinned Stage-1 scores schema (plan T5 criterion 1: mu / lambda_x /
# coverage / chi2 j3-validation rows + raw sigma + LABELED scalar-s*).
_PINNED_SCORE_KEYS = {
    "mu",
    "sigma",
    "lambda_x",
    "n_scored_points",
    "coverage_1sigma",
    "chi2_j3_validation",
    "raw_sigma",
    "scalar_s_star",
    "s_star_chi2_identity",
    "track",
}

_SCORE_KWARGS: dict[str, Any] = {
    "mu": -0.0131,
    "sigma": 0.0402,
    "lambda_x": 141.5,
    "n_scored_points": 20431,
    "coverage_1sigma": 0.591,
    "reduced_chi2": 1.83,
    "raw_sigma": 0.0217,
    # 100(a): the supports are NOT split, so s* IS the pre-scaling chi2.
    "scalar_s_star": 1.83,
    "calibration_n": 19004,
    "track": "data/j3.nc",
    "track_sha256": "beef" * 16,
}


def test_scores_block_keys_are_exactly_the_pinned_set() -> None:
    """build_scores_block output keys == the pinned scores set, nothing else.

    Bug caught: a free-prose scores field (the one place an interpretation
    could be written) sneaking in, or a required row silently dropped.
    """
    scores = _mod.build_scores_block(**_SCORE_KWARGS)
    assert set(scores) == _PINNED_SCORE_KEYS


def test_pin42_fields_sit_on_the_chi2_row_only() -> None:
    """Pin 95: only the chi2 j3-validation row carries pin-42 fields.

    Bug caught: pin-42 blocks sprayed across every row, which would dress
    the report-only mu/lambda_x/coverage readings as verdict-bearing — or
    omitted from chi2, the one row compared against an expectation.
    """
    scores = _mod.build_scores_block(**_SCORE_KWARGS)
    assert "pin42" in scores["chi2_j3_validation"]
    assert "report_only" not in scores["chi2_j3_validation"]
    for key in ("mu", "sigma", "lambda_x", "coverage_1sigma", "raw_sigma"):
        assert scores[key]["report_only"] is True, key
        assert "pin42" not in scores[key], key


def test_chi2_pin42_records_the_outcome_and_does_not_gate() -> None:
    """Pin 98: the chi2 pin-42 field RECORDS; the non-gating status is pinned.

    Bug caught: a later reader "completing" the bar that harness.py:1145
    deliberately left out — a threshold or pass/fail condition here would
    re-gate chi2 behind the earlier ruling's back (98b).
    """
    row = _mod.build_scores_block(**_SCORE_KWARGS)["chi2_j3_validation"]
    assert row["value"] == 1.83
    # The support the reading rests on, which is NOT n_scored_points
    # (20431): the member-std map is masked at some scored points.
    assert row["n"] == 19004
    assert row["gates"] is False
    assert row["pin42"]["null"] == "E[chi2_red] = 1 (calibrated)"
    assert row["pin42"]["pass_condition"] is None
    assert row["pin42"]["fail_condition"] is None
    assert "coverage remains the only bar" in row["pin42"]["why_not_gating"]


def test_scores_block_carries_the_s_star_chi2_identity_field() -> None:
    """Pin 100(b): the identity travels IN the row, naming the expression.

    Bug caught: the identity living only in a docstring. A consumer reading
    the stored row sees chi2 and s* agreeing and counts two independent
    witnesses, when it is one number recorded twice — the docstring is not
    what travels.
    """
    ident = _mod.build_scores_block(**_SCORE_KWARGS)["s_star_chi2_identity"]
    assert ident["same_by_construction"] is True
    assert ident["supports_coincide"] is True
    assert ident["shared_expression"] == "mean((truth - mean)**2 / var)"
    assert set(ident["fields"]) == {
        "scores.chi2_j3_validation.value",
        "scores.scalar_s_star.value",
    }
    assert "not independent confirmation" in ident["not_corroboration"]


def test_scores_block_refuses_a_silent_divergence() -> None:
    """Pin 100(c): unequal values on coincident supports fire LOUDLY.

    Bug caught: a future change to how s* is computed producing a number
    different from the pre-scaling chi2 while both keep names that imply
    they must match — recorded silently, and read as agreement-or-not by
    whoever finds them. Divergence may be legitimate; silence never is.
    """
    kwargs = dict(_SCORE_KWARGS)
    kwargs["scalar_s_star"] = kwargs["reduced_chi2"] + 0.01
    with pytest.raises(ValueError, match="same_by_construction"):
        _mod.build_scores_block(**kwargs)


def test_identity_holds_on_readings_taken_from_one_call() -> None:
    """The production path feeds both fields from ONE calibration call.

    Bug caught: 100(a) violated by splitting the supports — computing s*
    on a different point set to manufacture independence, which degrades
    one number to decorate the other. Here the readings come from a single
    hand-built call, and the block must accept them unchanged.
    """
    readings = _mod.calibration_readings(
        mean=np.zeros(3), std=np.ones(3), truth=np.array([0.5, -0.5, 2.0])
    )
    scores = _mod.build_scores_block(
        mu=0.0,
        sigma=0.04,
        lambda_x=140.0,
        n_scored_points=3,
        coverage_1sigma=readings["coverage_1sigma"],
        reduced_chi2=readings["reduced_chi2"],
        raw_sigma=readings["raw_sigma"],
        scalar_s_star=readings["scalar_s_star"],
        calibration_n=readings["n_used"],
        track="data/j3.nc",
        track_sha256="beef" * 16,
    )
    assert scores["scalar_s_star"]["value"] == scores["chi2_j3_validation"]["value"]
    assert scores["s_star_chi2_identity"]["same_by_construction"] is True


def test_readings_carry_chi2_and_s_star_as_ONE_value() -> None:
    """Pin 103(c): single-source, not agreement — the same object twice.

    Bug caught: a refactor that computes s* on its own from inputs that
    later drift. Equality is guaranteed by aliasing TODAY, so an equality
    assertion would pass right through such a refactor and only start
    failing once the two inputs actually diverged — in a recorded row.
    """
    readings = _mod.calibration_readings(
        mean=np.zeros(3), std=np.ones(3), truth=np.array([0.5, -0.5, 2.0])
    )
    assert readings["reduced_chi2"] is readings["scalar_s_star"]


def test_scores_from_readings_wires_both_fields_from_the_one_mapping() -> None:
    """The wiring hop is single-source too, not just the computation hop.

    Bug caught: a future caller assembling the block by hand and feeding
    scalar_s_star from a separate path — the exact construction error the
    row-build raise exists for. A sentinel value proves both fields were
    READ from the readings mapping rather than recomputed.
    """
    sentinel = 4.2424
    readings = {
        "coverage_1sigma": 0.61,
        "reduced_chi2": sentinel,
        "scalar_s_star": sentinel,
        "raw_sigma": 0.02,
        "n_used": 11,
    }
    scores = _mod.scores_from_readings(
        readings,
        mu=0.0,
        sigma=0.04,
        lambda_x=140.0,
        n_scored_points=12,
        track="data/j3.nc",
        track_sha256="beef" * 16,
    )
    assert scores["chi2_j3_validation"]["value"] == sentinel
    assert scores["scalar_s_star"]["value"] == sentinel
    assert scores["chi2_j3_validation"]["n"] == 11


@pytest.mark.parametrize("tile", ["kuroshio", "seam_n"])
def test_run_exercises_row_construction_before_any_load(
    tile: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pin 103(a): the construction smoke runs BEFORE the leg, both branches.

    Bug caught: a construction error (the two fields wired from separate
    paths) first discovered at the END of a 31 h leg, because the only
    check sat at row build. Placement is the whole point -- the error is
    present from the first line and costs seconds to find.
    """
    from sverdrup.application import ladder

    loaded: list[str] = []
    monkeypatch.setattr(ladder, "tier1_eligible", lambda peak_mib: True)
    monkeypatch.setattr(_mod, "_mem_available_mib", lambda: 12000.0)
    monkeypatch.setattr(_mod, "_solve_leg", lambda *a, **k: loaded.append("solved"))

    def _broken(**kwargs: Any) -> dict[str, Any]:
        raise ValueError("SENTINEL-CONSTRUCTION-BROKEN")

    monkeypatch.setattr(_mod, "build_scores_block", _broken)
    with pytest.raises(ValueError, match="SENTINEL-CONSTRUCTION-BROKEN"):
        _mod.run(tile)
    assert loaded == []


def test_solve_leg_exercises_row_construction_before_any_load(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Direct callers of the leg get the same early firing.

    Bug caught: the smoke living only in the CLI entry, so a leg launched
    programmatically (or from a future runner) keeps the old placement and
    the old cost.
    """
    evid = tmp_path / "evidence.json"
    evid.write_text(json.dumps({"phase14": {"stage0": {"seal": {"sha": "ab" * 32}}}}))
    monkeypatch.setattr(_mod, "EVIDENCE", evid)
    loaded: list[str] = []
    monkeypatch.setattr(_mod, "_tile_framed_obs", lambda tile: loaded.append(tile))

    def _broken(**kwargs: Any) -> dict[str, Any]:
        raise ValueError("SENTINEL-CONSTRUCTION-BROKEN")

    monkeypatch.setattr(_mod, "build_scores_block", _broken)
    with pytest.raises(ValueError, match="SENTINEL-CONSTRUCTION-BROKEN"):
        _mod._solve_leg("kuroshio", m=3, days_stride=1, maxiter=1200)
    assert loaded == []


def test_preflight_construction_smoke_records_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The smoke is synthetic and MUST NOT touch the evidence store.

    Bug caught: a pre-launch self-check that writes -- a synthetic row
    landing at phase14.stage1.tiles.<tile>, or a seal-verified write path
    being exercised for real, would make the cheap check expensive and the
    store untrustworthy.
    """
    evid = tmp_path / "evidence.json"
    monkeypatch.setattr(_mod, "EVIDENCE", evid)
    written: list[str] = []
    monkeypatch.setattr(
        _mod, "record_evidence_row", lambda *a, **k: written.append("w")
    )
    _mod.preflight_scores_construction()
    assert written == []
    assert not evid.exists()


def test_scalar_s_star_row_is_labeled_reference_only() -> None:
    """The scalar-s* transfer reading is LABELED where its number is read.

    Bug caught: an unlabeled s* row read as a calibrated scaling rather
    than the uncalibrated transfer reference it is.
    """
    row = _mod.build_scores_block(**_SCORE_KWARGS)["scalar_s_star"]
    assert row["value"] == 1.83
    assert row["label"] == "REFERENCE-ONLY, NOT CALIBRATED"


def test_scores_block_raw_sigma_drives_the_pin94_caveat() -> None:
    """A row built from build_scores_block carries the pin-94 sigma caveat.

    Bug caught: renaming the scores builder's raw-sigma key — the caveat
    attachment keys off it, so the rename would silently produce an
    uncaveated sigma row while every other test still passed.
    """
    kwargs = _row_kwargs("kuroshio")
    kwargs["scores"] = _mod.build_scores_block(**_SCORE_KWARGS)
    row = _mod.build_evidence_row(**kwargs)
    assert row["sigma_caveat"] == _PINNED_SIGMA_CAVEAT


@pytest.mark.parametrize("tile", _DIVERSE)
def test_evidence_row_raw_sigma_carries_pinned_sigma_caveat(tile: str) -> None:
    """A scores block carrying raw_sigma yields the VERBATIM pin-94 caveat.

    Bug caught: the caveat written as prose at pack/write time (pin 94c)
    instead of attached in the builder — a transfer row could then be built,
    recorded and read with its raw sigma uncaveated.
    """
    kwargs = _row_kwargs(tile)
    kwargs["scores"] = {"mu": 0.9, "raw_sigma": 0.0431}
    row = _mod.build_evidence_row(**kwargs)
    assert row["sigma_caveat"] == _PINNED_SIGMA_CAVEAT


def test_evidence_row_without_raw_sigma_has_no_sigma_caveat() -> None:
    """No raw sigma in scores -> sigma_caveat is None (the anchor row).

    Bug caught: attaching the caveat unconditionally would stamp a
    withheld-sigma disclaimer on the one tile whose scores ARE calibrated,
    inverting what the caveat means.
    """
    row = _mod.build_evidence_row(**_row_kwargs("anchor"))
    assert row["scores"]["mu"] == 0.9  # the fixture carries no raw_sigma
    assert row["sigma_caveat"] is None


def test_sigma_caveat_scopes_the_deferred_defect_honestly() -> None:
    """Pin 94(f): the caveat names the scope limit AND clears the level.

    Bug caught: a rewrite that drops "cross-tile ... NOT supported" (making
    the per-tile levels look inter-comparable) or one that implies the
    within-tile level is compromised — pin 94(f) says it is not.
    """
    caveat = _mod.SIGMA_CAVEAT
    assert "phase14.stage1.crn_production_defect_deferred" in caveat
    assert "SHIPPED SYSTEM, not of an instrument" in caveat
    assert "cross-tile sigma comparison is NOT supported" in caveat
    assert "boundary gradient is DEFERRED" in caveat
    assert "within-tile sigma level is NOT compromised" in caveat


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


@pytest.mark.parametrize(
    "word", ["suggests", "consistent with", "attributable", "implies"]
)
def test_recording_a_row_carrying_interpretation_prose_refuses(
    word: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The four-word serialization tripwire fires on the tile-row path.

    Bug caught: an interpretation smuggled into a value (not a key) of an
    otherwise schema-clean row -- the structural control pins the KEY set,
    so a caveat or label rewritten into "consistent with the anchor" would
    otherwise serialize straight into the evidence store.
    """
    from sverdrup.validation import phase14_seal

    monkeypatch.setattr(phase14_seal, "verify_current_seal", lambda: None)
    evid = tmp_path / "evidence.json"
    kwargs = _row_kwargs("kuroshio")
    kwargs["scores"] = {"mu": 0.9, "note": f"the transfer is {word} the anchor"}
    row = _mod.build_evidence_row(**kwargs)
    with pytest.raises(ValueError, match=word.split()[0]):
        _mod.record_evidence_row(row, evidence_path=evid)
    assert not evid.exists()


def test_the_pinned_caveats_themselves_pass_the_tripwire(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A normal row -- caveats, labels and all -- records without tripping.

    Bug caught: a tripwire so broad it fires on the pin-7 bridge caveat's
    "attribution readout" or on the pin-94 sigma caveat, which would block
    every legitimate cmems row and invite someone to delete the check.
    """
    from sverdrup.validation import phase14_seal

    monkeypatch.setattr(phase14_seal, "verify_current_seal", lambda: None)
    evid = tmp_path / "evidence.json"
    kwargs = _row_kwargs("kuroshio")
    kwargs["scores"] = _mod.build_scores_block(**_SCORE_KWARGS)
    row = _mod.build_evidence_row(**kwargs)
    _mod.record_evidence_row(row, evidence_path=evid)
    stored = json.loads(evid.read_text())
    assert stored["phase14"]["stage1"]["tiles"]["kuroshio"]["sigma_caveat"]


# ---------------------------------------------------------------------------
# T5c — GroundTrack wiring (T5 criterion 2). The EXISTING Phase-11 machinery
# (Registry.applicable + build_report_rows, via report_only_instruments_block)
# evaluated per tile x era; NO new producers; absence RECORDED as absence.
# ---------------------------------------------------------------------------


def _stage1_mean_map(tmp_path: Path, *, geometry: bool) -> Path:
    """A small challenge-schema mean map, optionally beside a geometry artifact."""
    from sverdrup.validation.output_adapter import write_map

    lon = np.arange(295, 305.01, 0.2)
    lat = np.arange(33, 43.21, 0.2)
    rng = np.random.default_rng(0)
    dest = write_map(
        times=np.array(["2017-01-01", "2017-01-02"], dtype="datetime64[ns]"),
        lats=lat,
        lons=lon,
        ssh=rng.standard_normal((2, lat.size, lon.size)),
        dest=tmp_path / "kuroshio_signed_maps.nc",
        assimilated_missions=("alg", "s3a"),
    )
    if geometry:
        fam = {
            "heading_north_deg": 12.0,
            "n_passes": 24,
            "n_crossings": 24,
            "orbit_class": "repeat",
            "s_lon_km": 300.0,
            "d_perp_km": 280.0,
            "spacing_quantiles_km": None,
        }
        (tmp_path / "phase11_orbit_geometry.json").write_text(
            json.dumps(
                {
                    "derivation_version": 1,
                    "key": "test",
                    "phi0": 38.1,
                    "missions": {
                        "alg": {
                            "asc": fam,
                            "desc": {**fam, "heading_north_deg": 168.0},
                        },
                        "s3a": {"asc": fam, "desc": None},
                    },
                    "provenance": {"obs_sha256": {}},
                }
            )
        )
    return dest


def test_tile_report_block_uses_only_registry_evaluators(tmp_path: Path) -> None:
    """Every row comes from the EXISTING registry — no new producers.

    Bug caught: a Stage-1-local GroundTrack (or any other) producer added
    to make the criterion pass. The criterion is a WIRING requirement:
    zero new surfaces, evaluated through Registry.applicable.
    """
    from sverdrup.application.eval_context import default_registry, evaluator_names

    maps = _stage1_mean_map(tmp_path, geometry=True)
    block = _mod.build_tile_report_block(tile="kuroshio", era="2017", mean_map=maps)
    known = set(evaluator_names(default_registry()))
    got = {r["evaluator"] for r in block["rows"]}
    assert got <= known
    assert {a["evaluator"] for a in block["recorded_absences"]} <= known
    # Every registry evaluator is accounted for: standing row OR absence.
    assert got | {a["evaluator"] for a in block["recorded_absences"]} == known


def test_tile_report_block_records_absence_as_absence(tmp_path: Path) -> None:
    """No geometry artifact -> GroundTrack absent AND RECORDED (fork F).

    Bug caught: an inapplicable evaluator simply missing from the rows. A
    reader then cannot distinguish "not applicable here" from "we forgot to
    run it" — which is the whole point of recording absence.
    """
    maps = _stage1_mean_map(tmp_path, geometry=False)
    block = _mod.build_tile_report_block(tile="kuroshio", era="2017", mean_map=maps)
    absent = {a["evaluator"]: a for a in block["recorded_absences"]}
    assert "groundtrack" in absent
    assert "groundtrack" not in {r["evaluator"] for r in block["rows"]}
    assert "ORBIT_GEOMETRY" in absent["groundtrack"]["missing_context"]
    assert block["geometry_artifact_sha256"] is None
    # The absence is CHECKABLE: the record says where it looked.
    assert block["geometry_artifact_present"] is False
    assert block["geometry_artifact_expected_at"].endswith(
        "phase11_orbit_geometry.json"
    )
    assert str(tmp_path) in block["geometry_artifact_expected_at"]


def test_tile_report_block_yields_a_standing_groundtrack_row(tmp_path: Path) -> None:
    """Geometry present -> GroundTrack is applicable and yields a row.

    Bug caught: wiring that never supplies the geometry artifact path, so
    the instrument is permanently "absent" and the whole wiring is inert —
    a criterion met on paper by a path that can never fire.
    """
    maps = _stage1_mean_map(tmp_path, geometry=True)
    block = _mod.build_tile_report_block(tile="kuroshio", era="2017", mean_map=maps)
    assert "groundtrack" in {r["evaluator"] for r in block["rows"]}
    assert "groundtrack" not in {a["evaluator"] for a in block["recorded_absences"]}
    assert block["geometry_artifact_sha256"] is not None


def test_tile_report_block_is_labeled_report_only_and_keyed(tmp_path: Path) -> None:
    """The block carries tile, era and the REPORT-ONLY label.

    Bug caught: a report-only block read as gate-bearing at T9, or rows
    that cannot be attributed to the tile x era they describe (Stage 1's
    era is degenerate, which is a ROW COUNT, not a schema excuse).
    """
    maps = _stage1_mean_map(tmp_path, geometry=True)
    block = _mod.build_tile_report_block(tile="kuroshio", era="2017", mean_map=maps)
    assert block["tile"] == "kuroshio"
    assert block["era"] == "2017"
    assert block["label"] == "REPORT-ONLY"
    assert block["gates"] is False


def test_record_tile_report_block_writes_beside_the_tiles_node(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Report rows land at phase14.stage1.report_rows.<tile>.<era>, seal-gated.

    Bug caught: report-only rows written INTO the gate-bearing tiles node
    (where T9 reads verdict-bearing evidence), or a write that clobbers the
    standing store, or one that skips the seal ceremony.
    """
    from sverdrup.validation import phase14_seal

    calls: list[str] = []
    monkeypatch.setattr(
        phase14_seal, "verify_current_seal", lambda: calls.append("verified")
    )
    evid = tmp_path / "evidence.json"
    evid.write_text(json.dumps({"phase13": {"kept": True}}))
    maps = _stage1_mean_map(tmp_path, geometry=True)
    block = _mod.build_tile_report_block(tile="kuroshio", era="2017", mean_map=maps)
    _mod.record_tile_report_block(block, evidence_path=evid)
    stored = json.loads(evid.read_text())
    assert stored["phase13"] == {"kept": True}
    assert stored["phase14"]["stage1"]["report_rows"]["kuroshio"]["2017"] == block
    assert "tiles" not in stored["phase14"]["stage1"]
    assert calls == ["verified"]


def test_solve_leg_records_the_tile_report_block(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The leg records report rows for the tile x era it just solved.

    Bug caught: the wiring built but never called from the leg — the exact
    drift the Phase-11 architecture audit found for track_power, where an
    instrument existed and no evidence pack carried it. Pinned on the leg's
    own path: the block must be recorded for the tile, with its maps.
    """
    from sverdrup.validation import phase14_seal

    monkeypatch.setattr(phase14_seal, "verify_current_seal", lambda: None)
    evid = tmp_path / "evidence.json"
    evid.write_text(json.dumps({"phase13": {"kept": True}}))
    maps = _stage1_mean_map(tmp_path, geometry=True)
    kwargs = _row_kwargs("kuroshio")
    kwargs["scores"] = _mod.build_scores_block(**_SCORE_KWARGS)
    _mod.record_leg_evidence(mean_map=maps, evidence_path=evid, **kwargs)
    stage1 = json.loads(evid.read_text())["phase14"]["stage1"]
    # BOTH sides of the leg's recording, in their own nodes.
    assert stage1["tiles"]["kuroshio"]["scores"]["mu"]["value"] == -0.0131
    block = stage1["report_rows"]["kuroshio"][_mod.STAGE1_ERA]
    assert block["label"] == "REPORT-ONLY"
    assert "groundtrack" in {r["evaluator"] for r in block["rows"]}


# ---------------------------------------------------------------------------
# T5d part A — the equatorial lane-0 persistence bundle (fork-b pins 1/2,
# owner pin 96: mirror the MANIFEST, witnessed AT CREATION).
# ---------------------------------------------------------------------------

# Fork-B.2 verbatim (spec 2026-07-21 §4-B.2), stated here independently of
# the implementation: it is the control on the future increment comparison.
_PINNED_FORK_B_PIN2 = (
    "the equatorial baseline is recorded UNDER Stage 1's config policy "
    "(frozen signed config, §6), and the future increment comparison HOLDS "
    "THAT POLICY FIXED — a wave-component gain must never be confounded "
    "with a config change (the tuned-constant control lesson, Phase 10)"
)


def _lane0_inputs(tmp_path: Path) -> dict[str, Any]:
    """Maps, an evidence row, a report block and a frozen frame for the bundle."""
    mean_map = _stage1_mean_map(tmp_path, geometry=False)
    std_map = tmp_path / "equatorial_member_std_maps.nc"
    std_map.write_bytes(mean_map.read_bytes())
    kwargs = _row_kwargs("equatorial")
    kwargs["scores"] = _mod.build_scores_block(**_SCORE_KWARGS)
    return {
        "mean_map": mean_map,
        "std_map": std_map,
        "row": _mod.build_evidence_row(**kwargs),
        "report_block": _mod.build_tile_report_block(
            tile="equatorial", era="2017", mean_map=mean_map
        ),
        "fold_eval_frame": _mod.build_fold_eval_frame(
            tile="equatorial",
            frame={"core": [200.0, 215.0, -4.0, 11.0], "overlap_deg": 2.0},
            window_plan={"n_windows": 9, "w_days": 60.0},
            root=12345,
            pcg_rtol=1e-6,
            pcg_maxiter=1200,
            track="data/j3.nc",
            track_sha256="beef" * 16,
        ),
    }


def test_lane0_manifest_carries_fork_b_pin2_verbatim(tmp_path: Path) -> None:
    """The frozen-config policy sentence rides the manifest, word for word.

    Bug caught: a paraphrase. This sentence is the CONTROL on the future
    wave-increment comparison — it is what forbids reading a config change
    as a wave-component gain. A summarized version cannot be checked
    against the policy it claims to hold fixed.
    """
    bundle = _mod.persist_lane0_bundle(
        dest=tmp_path / "lane0", **_lane0_inputs(tmp_path)
    )
    assert bundle["frozen_config_policy"] == _PINNED_FORK_B_PIN2


def test_lane0_manifest_shas_every_persisted_file(tmp_path: Path) -> None:
    """Every file in the bundle has a sha in the manifest, matching its bytes.

    Bug caught: a stale or wrong sha (the witness is then worth nothing),
    or a file persisted but omitted from the manifest — the manifest IS
    the mirrored object, so anything it omits is unwitnessed.
    """
    import hashlib

    dest = tmp_path / "lane0"
    bundle = _mod.persist_lane0_bundle(dest=dest, **_lane0_inputs(tmp_path))
    listed = {f["name"]: f["sha256"] for f in bundle["files"]}
    on_disk = {p.name for p in dest.iterdir() if p.name != "lane0_manifest.json"}
    assert set(listed) == on_disk
    for name, sha in listed.items():
        assert hashlib.sha256((dest / name).read_bytes()).hexdigest() == sha


def test_lane0_bundle_holds_maps_pack_and_frozen_frame(tmp_path: Path) -> None:
    """The substrate the increment comparison needs is all there.

    Bug caught: a bundle missing the frozen fold/eval frame or the pack —
    the future pre/post comparison then has maps it cannot interpret, and
    the frame it was supposed to hold fixed is gone.
    """
    dest = tmp_path / "lane0"
    _mod.persist_lane0_bundle(dest=dest, **_lane0_inputs(tmp_path))
    names = {p.name for p in dest.iterdir()}
    assert "equatorial_signed_maps.nc" in names
    assert "equatorial_member_std_maps.nc" in names
    assert "evidence_pack.json" in names
    assert "fold_eval_frame.json" in names
    assert "lane0_manifest.json" in names
    frame = json.loads((dest / "fold_eval_frame.json").read_text())
    assert frame["validation_mission"] == "j3"
    assert frame["assimilated_missions"] == list(_mod.PROBE_MISSIONS)
    assert frame["frozen"] is True


def test_lane0_manifest_records_the_instrument_composition(tmp_path: Path) -> None:
    """The baseline is self-describing about WHICH instruments stood.

    Bug caught: the pin-107 coupling. A future wave-increment run under
    per-tile orbit geometry carries a DIFFERENT composition; a blind
    pack-to-pack comparison would then read an instrument-set change as an
    increment effect.
    """
    bundle = _mod.persist_lane0_bundle(
        dest=tmp_path / "lane0", **_lane0_inputs(tmp_path)
    )
    comp = bundle["instrument_composition"]
    assert "groundtrack" in comp["absent"]
    assert comp["standing"]  # the instruments that DID run are named too
    assert "composition" in comp["compare_note"]


def test_lane0_manifest_is_witnessed_at_creation_and_mirrored(tmp_path: Path) -> None:
    """Pin 96: the manifest declares its class AND is in the mirror's set.

    Bug caught: a local manifest that is never mirrored — self-witnessing
    (pin 56a/96c), since manifest and files sit on one box under one
    process's control. Also catches the class being asserted in prose while
    the mirror config knows nothing about the node.
    """
    from tests.helpers import load_script

    bundle = _mod.persist_lane0_bundle(
        dest=tmp_path / "lane0", **_lane0_inputs(tmp_path)
    )
    assert bundle["witness_class"] == "WITNESSED_AT_CREATION"
    mirror = load_script("phase14_evidence_mirror")
    assert bundle["mirror_node"] in mirror.MIRRORED


def test_lane0_maps_are_not_mirrored(tmp_path: Path) -> None:
    """Pin 96(e)/56(b): the manifest is mirrored, the maps are not.

    Bug caught: bulk NetCDF paths creeping into the mirrored subset, which
    the mirror deliberately excludes — the shas ARE the witness.
    """
    from tests.helpers import load_script

    mirror = load_script("phase14_evidence_mirror")
    assert not [k for k in mirror.MIRRORED if k.endswith("maps")]
    bundle = _mod.persist_lane0_bundle(
        dest=tmp_path / "lane0", **_lane0_inputs(tmp_path)
    )
    # The manifest names the bulk files and digests them; it never carries
    # their contents, so mirroring it stays small and append-only.
    assert any(str(f["name"]).endswith(".nc") for f in bundle["files"])
    for entry in bundle["files"]:
        assert set(entry) == {"name", "sha256", "bytes"}
        assert isinstance(entry["bytes"], int)  # a SIZE, not a payload


def test_record_lane0_manifest_lands_at_its_own_node(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The manifest is recorded under its own node, seal-gated, store intact.

    Bug caught: the manifest recorded into the tiles node (where T9 reads
    evidence rows), or a write that clobbers the standing store, or one
    that skips the seal ceremony.
    """
    from sverdrup.validation import phase14_seal

    calls: list[str] = []
    monkeypatch.setattr(
        phase14_seal, "verify_current_seal", lambda: calls.append("verified")
    )
    evid = tmp_path / "evidence.json"
    evid.write_text(json.dumps({"phase13": {"kept": True}}))
    bundle = _mod.persist_lane0_bundle(
        dest=tmp_path / "lane0", **_lane0_inputs(tmp_path)
    )
    _mod.record_lane0_manifest(bundle, evidence_path=evid)
    stored = json.loads(evid.read_text())
    assert stored["phase13"] == {"kept": True}
    assert stored["phase14"]["stage1"]["equatorial_lane0_manifest"] == bundle
    assert calls == ["verified"]


@pytest.mark.parametrize("tile", ["equatorial", "kuroshio"])
def test_lane0_bundle_is_persisted_for_the_elected_tile_only(
    tile: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only the equatorial leg lays down a lane-0 bundle.

    Bug caught: every tile writing into the shared lane-0 directory — the
    frozen equatorial baseline would be silently overwritten by whichever
    leg ran last, destroying the pre-increment substrate fork-b pin 1
    exists to preserve.
    """
    from sverdrup.validation import phase14_seal

    monkeypatch.setattr(phase14_seal, "verify_current_seal", lambda: None)
    evid = tmp_path / "evidence.json"
    inputs = _lane0_inputs(tmp_path)
    dest = tmp_path / "lane0"
    kwargs = _row_kwargs(tile)
    kwargs["scores"] = _mod.build_scores_block(**_SCORE_KWARGS)
    manifest = _mod.persist_lane0_if_elected(
        tile=tile,
        row=_mod.build_evidence_row(**kwargs),
        report_block=inputs["report_block"],
        mean_map=inputs["mean_map"],
        std_map=inputs["std_map"],
        fold_eval_frame=inputs["fold_eval_frame"],
        evidence_path=evid,
        dest=dest,
    )
    if tile == "equatorial":
        assert manifest is not None
        assert (dest / "lane0_manifest.json").exists()
        stored = json.loads(evid.read_text())["phase14"]["stage1"]
        assert stored["equatorial_lane0_manifest"]["tile"] == "equatorial"
    else:
        assert manifest is None
        assert not dest.exists()
        assert not evid.exists()


# ---------------------------------------------------------------------------
# T5d part B — southern anisotropy inputs for T6 (existing families only).
# ---------------------------------------------------------------------------


def test_anisotropy_grid_aspect_is_computed_from_the_tile_axes(
    tmp_path: Path,
) -> None:
    """The grid aspect is the cos(lat) projection at the tile's OWN latitude.

    Bug caught: computing dx without the cos(lat) projection (the aspect
    collapses to 1.0 and the high-latitude anisotropy the kernel decision
    turns on disappears), or projecting at the wrong latitude. Expected
    value is hand-derived: the southern core spans -62..-47, so phi0 is
    about -54.5 and dy/dx = 1/cos(54.5 deg) ~ 1.72 -- nowhere near 1.
    """
    maps = _stage1_mean_map(tmp_path, geometry=False)
    block = _mod.build_tile_report_block(tile="southern", era="2017", mean_map=maps)
    got = _mod.build_anisotropy_inputs(tile="southern", era="2017", report_block=block)
    grid = got["grid_anisotropy"]
    assert grid["dx_km"] < grid["dy_km"]
    assert grid["aspect_dy_over_dx"] == pytest.approx(1.72, abs=0.05)
    # The frame, not a typed constant: the southern core's own span.
    assert grid["phi0_deg"] == pytest.approx(-54.5, abs=1.5)


def test_anisotropy_cites_the_recorded_spectral_row(tmp_path: Path) -> None:
    """The spectral input is CITED from the report block, never recomputed.

    Bug caught: a second computation of an instrument that already ran --
    two producers for one number, which is exactly what the zero-new-surface
    rule forbids and how the two copies drift apart.
    """
    maps = _stage1_mean_map(tmp_path, geometry=False)
    block = _mod.build_tile_report_block(tile="southern", era="2017", mean_map=maps)
    got = _mod.build_anisotropy_inputs(tile="southern", era="2017", report_block=block)
    row = next(r for r in block["rows"] if r["evaluator"] == "spectral_fidelity")
    assert got["spectral_fidelity"]["metrics"] == row["metrics"]
    assert got["spectral_fidelity"]["cited_from"] == (
        "phase14.stage1.report_rows.southern.2017"
    )


def test_anisotropy_records_the_missing_per_direction_diagnostics(
    tmp_path: Path,
) -> None:
    """Per-direction TRACK diagnostics are absent, and say so with the reason.

    Bug caught: T6 inheriting silence. The kernel pack's criterion expects
    per-direction track diagnostics; pin 106 says the geometry provider is
    challenge-box scoped, so they do not exist here. An input block that
    simply omits them lets T6 assume they were never needed.
    """
    maps = _stage1_mean_map(tmp_path, geometry=False)
    block = _mod.build_tile_report_block(tile="southern", era="2017", mean_map=maps)
    got = _mod.build_anisotropy_inputs(tile="southern", era="2017", report_block=block)
    absent = got["per_direction_track_diagnostics"]
    assert absent["status"] == "NOT AVAILABLE — RECORDED ABSENCE"
    assert "ORBIT_GEOMETRY" in absent["missing_context"]
    assert "106" in absent["ruling_pin"]


@pytest.mark.parametrize("tile", ["southern", "quiet_gyre"])
def test_anisotropy_inputs_recorded_for_the_southern_tile_only(
    tile: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only the southern leg records T6's anisotropy inputs.

    Bug caught: another tile's numbers landing at the node T6 reads --
    the kernel decision is about the high-latitude regime, and quiet_gyre's
    subtropical grid would quietly answer a question it was never asked.
    """
    from sverdrup.validation import phase14_seal

    monkeypatch.setattr(phase14_seal, "verify_current_seal", lambda: None)
    evid = tmp_path / "evidence.json"
    maps = _stage1_mean_map(tmp_path, geometry=False)
    block = _mod.build_tile_report_block(tile=tile, era="2017", mean_map=maps)
    out = _mod.record_anisotropy_if_elected(
        tile=tile, era="2017", report_block=block, evidence_path=evid
    )
    if tile == "southern":
        assert out is not None
        stored = json.loads(evid.read_text())["phase14"]["stage1"]
        assert stored["anisotropy_inputs"]["southern"]["2017"]["tile"] == "southern"
    else:
        assert out is None
        assert not evid.exists()


# ---------------------------------------------------------------------------
# T5d part C — the kuroshio land-mask path exercise.
# ---------------------------------------------------------------------------


def test_land_mask_exercise_records_all_three_counts() -> None:
    """n_obs, n_scored_points and the calibration n, with their gap.

    Bug caught: one count standing in for the others. coverage and chi2
    rest on the calibration n (19004 here), NOT on n_scored_points (20431)
    -- the member-std map is masked at some scored points, and a reader who
    sees a single number reads more support than exists.
    """
    scores = _mod.build_scores_block(**_SCORE_KWARGS)
    got = _mod.build_land_mask_exercise(
        tile="kuroshio", era="2017", n_obs=12345, scores=scores
    )
    counts = got["counts"]
    assert counts["n_obs_framed"] == 12345
    assert counts["n_scored_points"] == 20431
    assert counts["n_calibration_points"] == 19004
    assert counts["scored_minus_calibration"] == 1427


def test_land_mask_exercise_states_there_is_no_explicit_mask() -> None:
    """The mechanism is named honestly: land is ABSENT OBS, not a mask.

    Bug caught: a record implying a land mask was applied. Nothing in this
    pipeline masks land — altimetry simply has no observations there, and
    the coastal editing happens upstream. Claiming a mask would invent a
    control that does not exist.
    """
    scores = _mod.build_scores_block(**_SCORE_KWARGS)
    got = _mod.build_land_mask_exercise(
        tile="kuroshio", era="2017", n_obs=12345, scores=scores
    )
    assert "no explicit land mask" in got["mechanism"].lower()
    assert "absent" in got["mechanism"].lower()


def test_scoring_leg_does_not_swallow_an_all_land_core_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An empty-core refusal propagates out of the scoring leg.

    Bug caught: an except that turns score_tile's refusal into a NaN or
    masked triple. Its own docstring says an empty tile 'must be handled by
    the caller, never scored to a masked/NaN triple' -- swallowing it would
    record a transfer reading for a tile that scored nothing.
    """
    from sverdrup.validation import pertile_scoring

    def _refuse(*a: object, **k: object) -> None:
        raise ValueError("no validation track points survive in tile core")

    monkeypatch.setattr(pertile_scoring, "score_tile", _refuse)
    with pytest.raises(ValueError, match="no validation track points survive"):
        _mod._score_tile_leg(
            "kuroshio",
            frame=_mod.registry_frame("kuroshio"),
            mean_map=tmp_path / "m.nc",
            std_map=tmp_path / "s.nc",
            track=tmp_path / "dt_kuroshio_j3_phy_l3_2017_stage1.nc",
        )


@pytest.mark.parametrize("tile", ["kuroshio", "southern"])
def test_land_mask_exercise_recorded_for_kuroshio_only(
    tile: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only the kuroshio leg records the coastal exercise.

    Bug caught: an open-ocean tile's counts recorded as the land-mask
    exercise -- the criterion asks for the RISKIEST path to be exercised,
    and a tile with no coastline cannot exercise it.
    """
    from sverdrup.validation import phase14_seal

    monkeypatch.setattr(phase14_seal, "verify_current_seal", lambda: None)
    evid = tmp_path / "evidence.json"
    scores = _mod.build_scores_block(**_SCORE_KWARGS)
    out = _mod.record_land_mask_if_elected(
        tile=tile, era="2017", n_obs=1000, scores=scores, evidence_path=evid
    )
    if tile == "kuroshio":
        assert out is not None
        stored = json.loads(evid.read_text())["phase14"]["stage1"]
        assert stored["land_mask_exercise"]["kuroshio"]["2017"]["tile"] == "kuroshio"
    else:
        assert out is None
        assert not evid.exists()


# ---------------------------------------------------------------------------
# Owner pin 111 — the validation track's provenance describes ITSELF, not the
# first daily file it was concatenated from.
# ---------------------------------------------------------------------------


def _fake_cmems_j3_day(path: Path, day: str, *, decoy: str) -> None:
    """One CMEMS-shaped daily j3 file carrying misleading global attrs."""
    import xarray as xr

    t = np.array([f"{day}T00:30", f"{day}T12:30"], dtype="datetime64[ns]")
    ds = xr.Dataset(
        {
            "sla_unfiltered": ("time", np.array([0.01, 0.02])),
            "mdt": ("time", np.array([0.5, 0.5])),
            "lwe": ("time", np.array([0.0, 0.0])),
            "latitude": ("time", np.array([30.0, 31.0])),
            "longitude": ("time", np.array([140.0, 141.0])),
        },
        coords={"time": t},
        attrs={
            "time_coverage_start": decoy,
            "time_coverage_end": decoy,
            "platform": "Jason-3",
            "title": "DT Jason-3 Global Ocean Along track",
        },
    )
    ds.to_netcdf(path)


def test_validation_track_attrs_describe_the_concatenated_range(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The written track's coverage span is ITS OWN, not the first file's.

    Bug caught: the live one (pin 111). xarray.concat keeps the first
    dataset's global attrs, so a year concatenated from ~365 daily files
    was written claiming the FIRST DAY's coverage span -- evidence-labeled
    provenance describing 1/365th of the artifact. The assertion is against
    the data (the actual min/max times) so it cannot pass by someone
    setting a flag and moving on.
    """
    import xarray as xr

    from sverdrup.adapters.altimetry import cmems_my

    src = tmp_path / "cmems" / "j3"
    src.mkdir(parents=True)
    for day, decoy in (
        ("2017-03-05", "1999-01-01T00:00:00Z"),
        ("2017-09-20", "1999-01-01T00:00:00Z"),
    ):
        _fake_cmems_j3_day(src / f"dt_global_j3_{day}.nc", day, decoy=decoy)
    monkeypatch.setattr(cmems_my, "CMEMS_DATA_DIR", tmp_path / "cmems")

    out = _mod.build_tile_validation_track("kuroshio", dest=tmp_path / "track.nc")
    with xr.open_dataset(out) as ds:
        times = np.asarray(ds["time"].values)
        attrs = dict(ds.attrs)
    assert str(np.min(times))[:10] == "2017-03-05"
    assert str(np.max(times))[:10] == "2017-09-20"
    # The span the file CLAIMS equals the span it HOLDS.
    assert attrs["time_coverage_start"][:10] == "2017-03-05"
    assert attrs["time_coverage_end"][:10] == "2017-09-20"
    # And the inherited decoys are gone, not merely overwritten in two keys.
    assert "1999" not in " ".join(f"{k}={v}" for k, v in attrs.items())
    assert "platform" not in attrs
    assert attrs["n_points"] == 4
    assert attrs["source_files"] == 2


def test_no_test_write_reaches_the_real_data_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pin 110(a): exercising the risky entry points leaves data/ untouched.

    Bug caught: the live one. A test that reaches _solve_leg with the module
    paths live creates a pcg checkpoint directory and can write an
    evidence-LABELED validation track into the production evidence
    directory. The inventory is taken over the real tree, so this fails if
    the sandbox is ever removed or bypassed.
    """
    before = _data_tree_inventory()
    monkeypatch.setattr(_mod, "_tile_framed_obs", lambda tile: _FakeLoad.for_tile(tile))

    def _stop(*a: object, **k: object) -> None:
        raise _SolveStopped

    monkeypatch.setattr(_mod, "_seam_miost", _stop)
    evid = _mod.EVIDENCE
    evid.parent.mkdir(parents=True, exist_ok=True)
    evid.write_text(json.dumps({"phase14": {"stage0": {"seal": {"sha": "ab" * 32}}}}))
    with pytest.raises(_SolveStopped):
        _mod._solve_leg("kuroshio", m=3, days_stride=1, maxiter=1200)
    # The checkpoint dir WAS created -- inside the sandbox, where it belongs.
    assert (_mod.STAGE1_DIR / "kuroshio_pcg_ckpt").exists()
    assert _data_tree_inventory() == before


def test_track_reuse_is_gated_on_provenance_not_existence(tmp_path: Path) -> None:
    """Pin 110(b): a file with no build record is REFUSED, not adopted.

    Bug caught: the seventh instance of the unfailable-check family. A bare
    `if not track.exists()` cannot tell a legitimately built track from a
    test leftover, so it silently adopts whatever is on disk -- which is
    exactly how a test-written artifact came to sit in the evidence
    directory wearing a STAGE1-EVIDENCE label.
    """
    track = tmp_path / "dt_kuroshio_j3_phy_l3_2017_stage1.nc"
    track.write_bytes(b"not a real track")
    with pytest.raises(RuntimeError, match="no build record"):
        _mod.assert_track_reusable(track, tile="kuroshio")


def test_track_reuse_refuses_a_tampered_file(tmp_path: Path) -> None:
    """A build record whose sha no longer matches the bytes is REFUSED.

    Bug caught: a build record treated as a permission slip rather than a
    digest -- the file is replaced or truncated after the record was
    written, and reuse proceeds against different bytes.
    """
    track = tmp_path / "dt_kuroshio_j3_phy_l3_2017_stage1.nc"
    track.write_bytes(b"original bytes")
    _mod.write_track_build_record(track, tile="kuroshio", n_points=4, source_files=2)
    track.write_bytes(b"different bytes now")
    with pytest.raises(RuntimeError, match="sha256 mismatch"):
        _mod.assert_track_reusable(track, tile="kuroshio")


def test_track_reuse_refuses_another_tiles_track(tmp_path: Path) -> None:
    """A build record for a DIFFERENT tile is refused.

    Bug caught: a track built for seam_n being reused for kuroshio because
    a path was constructed wrong -- the scores would then be computed
    against another region's holdout and nothing would say so.
    """
    track = tmp_path / "dt_kuroshio_j3_phy_l3_2017_stage1.nc"
    track.write_bytes(b"bytes")
    _mod.write_track_build_record(track, tile="seam_n", n_points=4, source_files=2)
    with pytest.raises(RuntimeError, match="built for tile"):
        _mod.assert_track_reusable(track, tile="kuroshio")


def test_track_reuse_accepts_its_own_build_record(tmp_path: Path) -> None:
    """The happy path: same file, same tile, matching digest -> reuse.

    Bug caught: a gate so strict it refuses the artifact it just wrote,
    which would make crash-resume impossible and invite someone to delete
    the check.
    """
    track = tmp_path / "dt_kuroshio_j3_phy_l3_2017_stage1.nc"
    track.write_bytes(b"bytes")
    rec = _mod.write_track_build_record(
        track, tile="kuroshio", n_points=4, source_files=2
    )
    assert _mod.assert_track_reusable(track, tile="kuroshio") == rec


# ---------------------------------------------------------------------------
# Owner pin 112 — resolve the geometry artifact from its CANONICAL location,
# and only where the derivation's own scope covers the tile.
# ---------------------------------------------------------------------------


_HAS_GEOMETRY = _mod.CANONICAL_GEOMETRY_ARTIFACT.exists()


@pytest.mark.skipif(not _HAS_GEOMETRY, reason="canonical geometry artifact absent")
@pytest.mark.parametrize("tile", ["anchor", "seam_n", "seam_s"])
def test_geometry_applies_to_the_in_box_tiles(tile: str) -> None:
    """The canonical artifact is offered to the tiles it actually covers.

    Bug caught: leaving the box tiles on the beside-the-maps lookup, where
    the artifact does not sit -- their GroundTrack absence was a LOOKUP
    PATH, not the 106 design conflict, and pin 112(b) says 106 does not
    cover them.
    """
    path, reason = _mod.geometry_artifact_for(tile)
    assert path == _mod.CANONICAL_GEOMETRY_ARTIFACT
    assert "in scope" in reason


@pytest.mark.skipif(not _HAS_GEOMETRY, reason="canonical geometry artifact absent")
@pytest.mark.parametrize("tile", _DIVERSE)
def test_geometry_refused_for_the_diverse_tiles(tile: str) -> None:
    """The challenge-box artifact is NOT offered to the diverse tiles.

    Bug caught: the fix widening past its warrant. Four of the five
    families' codes match (alg/j2g/j2n/s3a), so a naive lookup would hand
    Gulf-Stream geometry to a Pacific tile and produce rows that look
    standing -- 'geometry that does not belong to the tile', which pin 106
    refused. The scope test must key on the DERIVATION's box, not on the
    mission codes alone.
    """
    path, reason = _mod.geometry_artifact_for(tile)
    assert path is None
    assert "106" in reason
    assert "box" in reason.lower()


def _synthetic_geometry_artifact(
    path: Path, *, box_lon: tuple[float, float], phi0: float, missions: tuple[str, ...]
) -> Path:
    """A geometry artifact with a chosen box, phi0 and mission set."""
    fam = {
        "heading_north_deg": 12.0,
        "n_passes": 24,
        "n_crossings": 24,
        "orbit_class": "repeat",
        "s_lon_km": 300.0,
        "d_perp_km": 280.0,
        "spacing_quantiles_km": None,
    }
    path.write_text(
        json.dumps(
            {
                "derivation_version": 3,
                "key": "synthetic",
                "phi0": phi0,
                "box_lon": list(box_lon),
                "missions": {m: {"asc": fam, "desc": None} for m in missions},
                "provenance": {"obs_sha256": {}},
            }
        )
    )
    return path


def test_geometry_scope_follows_the_artifacts_own_box(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pin 115(a): a DIFFERENT box_lon moves which tiles are in scope.

    Bug caught: the box hard-coded in the driver, in ANY form -- including
    ones a string scan cannot see (1295 contains "295"; 2.95e2 is the same
    number spelled differently). Here the artifact says the Pacific
    equatorial box, so `equatorial` must become in-scope and `anchor` --
    in-scope under the real artifact -- must drop out. Only a function
    reading box_lon can produce that inversion.
    """
    art = _synthetic_geometry_artifact(
        tmp_path / "geom.json",
        box_lon=(195.0, 220.0),
        phi0=3.5,
        missions=("alg", "j2g"),
    )
    monkeypatch.setattr(_mod, "CANONICAL_GEOMETRY_ARTIFACT", art)
    eq_path, eq_reason = _mod.geometry_artifact_for("equatorial")
    anchor_path, anchor_reason = _mod.geometry_artifact_for("anchor")
    assert eq_path == art, eq_reason
    assert "3.5" in eq_reason  # the artifact's phi0, not a typed 38.1
    assert anchor_path is None
    assert "195.0, 220.0" in anchor_reason


def test_geometry_refused_when_missions_match_but_box_does_not(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pin 115(b): mission overlap must NOT buy a tile geometry.

    Bug caught: the silent one. Four of the five CMEMS codes (alg, j2g,
    j2n, s3a) match the challenge artifact's families, so a lookup keyed on
    missions would hand Gulf-Stream geometry to a Pacific tile and emit
    rows that LOOK standing. This artifact's mission set covers kuroshio
    exactly, and its box does not -- the tile must still be refused.
    """
    art = _synthetic_geometry_artifact(
        tmp_path / "geom.json",
        box_lon=(295.0, 305.0),
        phi0=38.1,
        missions=("alg", "h2ag", "j2g", "j2n", "s3a"),
    )
    monkeypatch.setattr(_mod, "CANONICAL_GEOMETRY_ARTIFACT", art)
    path, reason = _mod.geometry_artifact_for("kuroshio")
    assert path is None
    assert "OUTSIDE" in reason
    assert "106" in reason


def test_geometry_refused_when_the_artifact_is_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No artifact at all -> refusal naming the path, never a crash.

    Bug caught: a missing artifact raising FileNotFoundError mid-leg
    instead of yielding the recorded-absence path the wiring is built
    around -- a fresh clone has no data/ at all.
    """
    monkeypatch.setattr(_mod, "CANONICAL_GEOMETRY_ARTIFACT", tmp_path / "absent.json")
    path, reason = _mod.geometry_artifact_for("anchor")
    assert path is None
    assert "no geometry artifact" in reason


@pytest.mark.skipif(not _HAS_GEOMETRY, reason="canonical geometry artifact absent")
def test_report_block_states_why_wedge_exclusion_is_false(tmp_path: Path) -> None:
    """Pin 112(c): a false wedge flag says WHICH kind of absence it is.

    Bug caught: `wedge_exclusion:false` appearing bare. A reader cannot
    tell 106's design conflict (diverse tiles, unfixable in Stage 1) from a
    fixable gap -- and the two carry completely different consequences.
    """
    maps = _stage1_mean_map(tmp_path, geometry=False)
    block = _mod.build_tile_report_block(tile="quiet_gyre", era="2017", mean_map=maps)
    scope = block["geometry_scope"]
    assert scope["applies"] is False
    assert "106" in scope["reason"]
    assert block["wedge_exclusion_status"]["kind"] == "DESIGN CONFLICT (pin 106)"


# ---------------------------------------------------------------------------
# Owner pin 114 — post-hoc recovery of the box tiles' report rows: computed
# from STORED maps, appended, no solve, stops on any contradiction.
# ---------------------------------------------------------------------------


def test_stored_mean_map_resolves_each_tiles_own_artifact() -> None:
    """Each tile resolves to the map its own leg actually wrote.

    Bug caught: the recovery scoring the anchor's map for a seam tile (or
    vice versa) because one path template was applied to every tile -- the
    rows would be real, attributed to the wrong region, and nothing in the
    block would say so.
    """
    assert _mod.stored_mean_map("anchor") == _mod.ANCHOR_MEAN_MAPS
    assert _mod.stored_mean_map("seam_n") == _mod.SEAM_MEAN_MAPS["seam_n"]
    assert _mod.stored_mean_map("seam_s") == _mod.SEAM_MEAN_MAPS["seam_s"]
    assert _mod.stored_mean_map("kuroshio") == _mod.tile_mean_map("kuroshio")


def test_recovery_computes_from_stored_maps_without_loader_or_solver(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pin 114(c): the recovery touches neither the obs loader nor the solver.

    Bug caught: a recovery that quietly re-runs a leg. The stop condition
    guards evaluation-bearing EXECUTION; scoring an existing artifact is
    not that, and this pin is what keeps the distinction true -- both the
    loader and the solver raise if called.
    """
    from sverdrup.validation import phase14_seal

    monkeypatch.setattr(phase14_seal, "verify_current_seal", lambda: None)

    def _boom(*a: object, **k: object) -> None:
        raise AssertionError("the recovery must not load obs or solve")

    monkeypatch.setattr(_mod, "_tile_framed_obs", _boom)
    monkeypatch.setattr(_mod, "_seam_miost", _boom)
    maps = _stage1_mean_map(tmp_path, geometry=False)
    monkeypatch.setattr(_mod, "stored_mean_map", lambda tile: maps)
    evid = tmp_path / "evidence.json"
    blocks = _mod.recover_report_rows(tiles=("seam_n",), era="2017", evidence_path=evid)
    assert list(blocks) == ["seam_n"]
    stored = json.loads(evid.read_text())["phase14"]["stage1"]
    assert stored["report_rows"]["seam_n"]["2017"]["label"] == "REPORT-ONLY"


def test_recovery_refuses_when_the_stored_map_is_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing map is named and refused, never silently skipped.

    Bug caught: a recovery that reports success having produced nothing,
    because the artifact it was supposed to score is not on this box.
    """
    monkeypatch.setattr(_mod, "stored_mean_map", lambda tile: tmp_path / "absent.nc")
    with pytest.raises(RuntimeError, match="absent.nc"):
        _mod.recover_report_rows(
            tiles=("anchor",), era="2017", evidence_path=tmp_path / "e.json"
        )


def test_recovery_stops_on_a_contradiction_instead_of_overwriting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pin 114(d): a differing existing block is a STOP, not an overwrite.

    Bug caught: the recovery silently replacing a recorded block with a
    different one -- that is a supersession, and it goes to the owner
    rather than landing inside an append-only store.
    """
    from sverdrup.validation import phase14_seal

    monkeypatch.setattr(phase14_seal, "verify_current_seal", lambda: None)
    maps = _stage1_mean_map(tmp_path, geometry=False)
    monkeypatch.setattr(_mod, "stored_mean_map", lambda tile: maps)
    evid = tmp_path / "evidence.json"
    evid.write_text(
        json.dumps(
            {
                "phase14": {
                    "stage1": {
                        "report_rows": {
                            "seam_n": {"2017": {"label": "REPORT-ONLY", "rows": []}}
                        }
                    }
                }
            }
        )
    )
    with pytest.raises(RuntimeError, match="SUPERSESSION, not an append"):
        _mod.recover_report_rows(tiles=("seam_n",), era="2017", evidence_path=evid)
    # The recorded block is untouched by the refusal.
    stored = json.loads(evid.read_text())["phase14"]["stage1"]
    assert stored["report_rows"]["seam_n"]["2017"]["rows"] == []


def test_recovery_is_idempotent_on_an_identical_block(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Re-running with the same inputs is a no-op, not a contradiction.

    Bug caught: a guard so blunt that the second run of a recovery -- the
    ordinary case after an interrupted one -- reports a supersession that
    is not one.
    """
    from sverdrup.validation import phase14_seal

    monkeypatch.setattr(phase14_seal, "verify_current_seal", lambda: None)
    maps = _stage1_mean_map(tmp_path, geometry=False)
    monkeypatch.setattr(_mod, "stored_mean_map", lambda tile: maps)
    evid = tmp_path / "evidence.json"
    first = _mod.recover_report_rows(tiles=("seam_n",), era="2017", evidence_path=evid)
    second = _mod.recover_report_rows(tiles=("seam_n",), era="2017", evidence_path=evid)
    # Canonical TEXT, not object equality: groundtrack legitimately reports
    # NaN for families beyond the grid's Nyquist, and nan != nan would make
    # an identical block look like a contradiction.
    dump = functools.partial(json.dumps, sort_keys=True, default=str)
    assert dump(first["seam_n"]["rows"]) == dump(second["seam_n"]["rows"])


def test_amendment_index_points_the_closed_nodes_at_the_new_rows() -> None:
    """Pin 114(b)/64: reachability lives in the mirror's amendment index.

    Bug caught: a forward pointer written INTO the witnessed anchor-gate
    node, which pin 64(b) forbids in as many words -- the index exists so
    the witnessed node stays exactly as witnessed. Also catches the
    pointer being omitted entirely, which leaves a reader at a node whose
    claims are individually accurate and collectively stale.
    """
    from tests.helpers import load_script

    mirror = load_script("phase14_evidence_mirror")
    for node in ("phase14.stage1.anchor_gate", "phase14.stage1.seam_pair"):
        entries = mirror.AMENDMENTS.get(node, [])
        assert any(e["amended_by"] == "phase14.stage1.report_rows" for e in entries), (
            node
        )


# ---------------------------------------------------------------------------
# The R5 dry run's finding: CMEMS mission codes reach the frozen config's
# mission-keyed R, which REFUSES anything outside the five challenge codes.
# ---------------------------------------------------------------------------


def test_cmems_missions_are_relabelled_to_challenge_codes() -> None:
    """h2ag -> h2g before the solve; every other code passes through.

    Bug caught: the live one, found by the R5 dry run. RSpec refuses any
    mission outside FIT_MISSIONS ('alg','h2g','j2g','j2n','s3a') -- that
    refusal is the j3/c2 leak guard and is correct -- while CMEMS-MY labels
    the same HY-2A geodetic stream 'h2ag'. Unrelabelled, EVERY diverse leg
    dies at window 0 with 'unknown mission hash'.
    """
    import numpy as np

    from sverdrup.methods.miost_rspec import FIT_MISSIONS

    got = _mod.relabel_missions_to_challenge(
        np.array(["alg", "h2ag", "j2g", "j2n", "s3a"])
    )
    assert list(got) == ["alg", "h2g", "j2g", "j2n", "s3a"]
    assert set(got) <= set(FIT_MISSIONS)


def test_relabelling_refuses_an_unknown_code() -> None:
    """A code with no challenge counterpart is refused, not passed through.

    Bug caught: a silent pass-through that would defer the failure to the
    solver's own refusal deep inside window 0 -- or worse, to a mission
    that happens to hash into the table.
    """
    import numpy as np

    with pytest.raises(RuntimeError, match="no challenge code"):
        _mod.relabel_missions_to_challenge(np.array(["alg", "c2n"]))


def test_relabelled_obs_survive_the_frozen_configs_r(tmp_path: Path) -> None:
    """The relabelled codes actually satisfy the frozen config's R lookup.

    Bug caught: a relabelling that looks right but still fails the check
    that matters. This asserts against RSpec itself -- the component that
    refused -- rather than against a list of strings.
    """
    import numpy as np

    from sverdrup.methods.miost import PHASE13_DELTAS
    from sverdrup.methods.miost_error_basis import mission_hash_ints
    from sverdrup.methods.miost_rspec import RSpec

    rspec = RSpec(deltas=dict(PHASE13_DELTAS))
    relabelled = _mod.relabel_missions_to_challenge(
        np.array(["alg", "h2ag", "j2g", "j2n", "s3a"])
    )
    r = rspec.sigma2_for(mission_hash_ints(np.asarray(relabelled)))
    assert r.shape == (5,)
    assert np.all(r > 0.0)
    # And the unrelabelled form is exactly what refuses.
    with pytest.raises(ValueError, match="unknown mission hash"):
        rspec.sigma2_for(mission_hash_ints(np.asarray(["h2ag"])))


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


def test_calibration_readings_are_the_stated_arithmetic() -> None:
    """The four track readings, against hand-computed values.

    Bug caught: coverage taken at 2 sigma instead of 1; a chi2 that is not
    REDUCED (no /n); s* built from sigma instead of sigma^2; or the raw
    sigma level reported as mean(std) = 1.5 rather than the level
    sqrt(mean(var)) = 1.5811 the transfer reading needs.
    """
    std = np.array([1.0, 1.0, 2.0, 2.0])
    z = np.array([0.5, -0.5, 2.0, -3.0])
    mean = np.zeros(4)
    truth = mean + z * std  # residual/std is exactly z, by construction
    got = _mod.calibration_readings(mean=mean, std=std, truth=truth)
    assert got["coverage_1sigma"] == 0.5  # |z| <= 1 for 2 of 4 points
    assert got["reduced_chi2"] == pytest.approx(3.375)  # mean(z^2) = 13.5/4
    assert got["scalar_s_star"] == pytest.approx(3.375)  # closed form = mean(z^2)
    assert got["raw_sigma"] == pytest.approx(1.5811388, abs=1e-6)  # sqrt(2.5)
    assert got["n_used"] == 4


def test_calibration_readings_drop_unusable_points_and_say_how_many() -> None:
    """NaN truth and non-positive variance are dropped; n_used is honest.

    Bug caught: land-masked / un-interpolable track points propagating a
    NaN into chi2 (recorded as a number nobody can read), or being counted
    in the support the readings claim to rest on -- the kuroshio land-mask
    path is exactly where this bites.
    """
    std = np.array([1.0, 1.0, 0.0, 2.0])
    truth = np.array([0.5, -0.5, 1.0, np.nan])
    mean = np.zeros(4)
    got = _mod.calibration_readings(mean=mean, std=std, truth=truth)
    assert got["n_used"] == 2  # zero-variance point and NaN point dropped
    assert got["reduced_chi2"] == pytest.approx(0.25)  # mean(0.5^2, 0.5^2)
    assert got["coverage_1sigma"] == 1.0


def test_calibration_readings_refuse_when_nothing_survives() -> None:
    """No usable point -> a refusal, never a masked/NaN reading.

    Bug caught: an all-land core silently scoring to NaN and being
    recorded as a transfer reading (T5 criterion 6: an all-land core
    refusal must be surfaced, not swallowed).
    """
    with pytest.raises(ValueError, match="no usable"):
        _mod.calibration_readings(
            mean=np.zeros(2), std=np.zeros(2), truth=np.array([1.0, 2.0])
        )


def test_run_diverse_tile_waits_when_tier2_headroom_is_short(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A T5 leg REFUSES below 2 x the measured peak, before any load.

    Bug caught: launching a 31 h leg over headroom (the exit-137 OOM
    class) because the Tier-2 gate was computed and then ignored.
    """
    called: list[str] = []
    monkeypatch.setattr(_mod, "_mem_available_mib", lambda: 8729.9)
    monkeypatch.setattr(_mod, "_solve_leg", lambda *a, **k: called.append("solved"))
    with pytest.raises(RuntimeError, match="Tier-2"):
        _mod.run("kuroshio")
    assert called == []


def test_run_diverse_tile_does_not_consult_the_tier1_predicate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T5 legs are gated by E-16 s2, NOT by ladder.tier1_eligible.

    Bug caught: the live sweep item -- preflight's Tier-1 refusal firing on
    a Tier-2-CLEARED leg, so task 22's clearance is inert and every diverse
    tile refuses before it loads anything.
    """
    from sverdrup.application import ladder

    seen: list[float] = []

    def _spy(peak_mib: float, *a: object, **k: object) -> bool:
        seen.append(peak_mib)
        return False

    solved: list[tuple[str, int]] = []
    monkeypatch.setattr(ladder, "tier1_eligible", _spy)
    monkeypatch.setattr(_mod, "_mem_available_mib", lambda: 12000.0)
    monkeypatch.setattr(
        _mod, "_solve_leg", lambda tile, m, ds, mi: solved.append((tile, m))
    )
    _mod.run("southern", m=100)
    assert seen == []
    assert solved == [("southern", 100)]


def test_run_seam_tile_still_routes_through_the_tier1_preflight(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tiles that were never Tier-2-cleared keep the Tier-1 refusal.

    Bug caught: "fixing" the diverse-tile gate by routing EVERY tile past
    preflight, silently disarming the launch guard for the seam tiles and
    the anchor gate. The Tier-2 authorisation is T5-scoped.
    """
    from sverdrup.application import ladder

    monkeypatch.setattr(ladder, "tier1_eligible", lambda peak_mib: False)
    monkeypatch.setattr(_mod, "_mem_available_mib", lambda: 12000.0)
    with pytest.raises(RuntimeError, match="Tier-1"):
        _mod.run("seam_n")


def test_record_tile_leg_records_equatorial_on_the_programmatic_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pin 90(c) live half: the REAL leg's write path, tile "equatorial".

    Bug caught: criterion 8's breadth concern left CLI-only -- a wiring
    change that recorded the row at the wrong node, or dropped the pin-94
    sigma caveat / pin-7 bridge caveat on the path production actually
    uses, would pass every CLI-level test in this file.
    """
    from sverdrup.validation import phase14_seal

    monkeypatch.setattr(phase14_seal, "verify_current_seal", lambda: None)
    evid = tmp_path / "evidence.json"
    evid.write_text(json.dumps({"phase13": {"kept": True}}))
    kwargs = _row_kwargs("equatorial")
    kwargs["scores"] = _mod.build_scores_block(**_SCORE_KWARGS)
    row = _mod.record_tile_leg(evidence_path=evid, **kwargs)
    stored = json.loads(evid.read_text())
    assert stored["phase14"]["stage1"]["tiles"]["equatorial"] == row
    assert stored["phase13"] == {"kept": True}
    assert row["sigma_caveat"] == _PINNED_SIGMA_CAVEAT
    assert row["bridge_caveat"] == _PINNED_CAVEAT
    assert set(row["scores"]) == _PINNED_SCORE_KEYS | {"capped_measurement"}


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
    """An eligible run threads tile/m/stride/maxiter into the solve leg.

    Bug caught: a CLI option accepted at the signature and dropped on the
    floor — a leg silently running at the library's 500 cap (which leaves
    every 19-degree leg un-converged, PIN 26(b)) instead of the cap the
    operator asked for.
    """
    from sverdrup.application import ladder

    seen: list[tuple[str, int, int, int]] = []
    monkeypatch.setattr(ladder, "tier1_eligible", lambda peak_mib: True)
    monkeypatch.setattr(
        _mod,
        "_solve_leg",
        lambda tile, m, ds, mi: seen.append((tile, m, ds, mi)),
    )
    _mod.run("seam_n", m=7, days_stride=5, maxiter=1900)
    assert seen == [("seam_n", 7, 5, 1900)]


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


# ---------------------------------------------------------------------------
# Owner ruling PIN 26(a)+(b) — the PRODUCTION path carries maxiter and its
# own convergence verdict; the Stage-1 cap is set FROM MEASUREMENT
# ---------------------------------------------------------------------------

# The PIN-23(a) converged 19-degree probe, read off
# phase14.stage1.probe_converged (NOT restated from the implementation):
# mean leg 524 iters, member-batch leg 554 iters, both ~9.9e-07 at rtol
# 1e-06. 554 is the measured worst leg and the sole basis of the cap.
_MEASURED_WORST_ITERS_19DEG = 554


def test_stage1_production_cap_is_at_least_twice_the_measured_worst_leg() -> None:
    """STAGE1_PCG_MAXITER >= 2 x 554, the owner's measured-margin rule.

    Bug caught: the T5 defect the pin exists to close — a production cap at
    (or near) the 500 library default, under which EVERY 19-degree leg
    would cap un-converged. 554 is the measured worst leg of the converged
    19-degree probe; anything below 1108 fails the owner's ">= 2x measured"
    ruling, and anything at/below 554 caps outright.
    """
    assert _mod.STAGE1_PCG_MAXITER >= 2 * _MEASURED_WORST_ITERS_19DEG


def test_stage1_cap_comment_carries_derivation_and_wall_consequence() -> None:
    """The constant's comment states 554, the 2x floor, and the s/iter cost.

    Bug caught: an unexplained magic number — the owner's ruling is that
    the cap is derived FROM MEASUREMENT with the wall consequence stated in
    the same breath, so a cap whose derivation lives only in a commit
    message cannot be audited or re-derived when the geometry changes.
    """
    src = Path(str(_mod.__file__)).read_text()
    head, _, tail = src.partition("STAGE1_PCG_MAXITER")
    comment = head[-2500:] + tail[:400]
    assert "554" in comment
    assert str(2 * _MEASURED_WORST_ITERS_19DEG) in comment
    assert "0.56" in comment  # 603.1 s / 1078 iters, the measured s/iter
    assert "member-batch" in comment  # PIN 26(d): the margin-setting leg


def test_library_pcg_maxiter_default_left_untouched() -> None:
    """The library default stays 500 — the driver passes an EXPLICIT cap.

    Bug caught: "fixing" the cap by raising miost_solver.PCG_MAXITER, which
    silently changes solver behavior under every signed-identity path (the
    anchor gate re-solves at the SIGNED cap read from the member store) —
    the owner ruled that unproven change out of scope for pin 26.
    """
    from sverdrup.methods.miost_solver import PCG_MAXITER

    assert PCG_MAXITER == 500
    assert _mod.STAGE1_PCG_MAXITER != PCG_MAXITER


@pytest.mark.parametrize(
    ("iterations", "residual", "maxiter", "want_capped"),
    [
        (500, 2.84e-6, 500, True),  # the real T2 defect leg
        (500, 1.0e-6, 500, False),  # at the cap, residual EXACTLY rtol
        (554, 9.95e-7, 2000, False),  # the converged 19-deg member leg
        (2000, 1.1e-6, 2000, True),  # capped even at the raised cap
    ],
)
def test_classify_pcg_legs_truth_table(
    iterations: int, residual: float, maxiter: int, want_capped: bool
) -> None:
    """capped iff a leg sits AT/above the cap with residual STRICTLY > rtol.

    Bug caught: keying the verdict on iterations alone (mislabeling a leg
    that legitimately converged at the cap) or a >= residual drift
    (flagging a leg that stopped exactly at rtol). Cases are the measured
    T2/converged-probe legs, classified by hand against rtol 1e-6.
    """
    legs = [{"window": "w0", "iterations": iterations, "final_rel_residual": residual}]
    rows, capped = _mod.classify_pcg_legs(legs, rtol=1.0e-6, maxiter=maxiter)
    assert capped is want_capped
    assert rows == [{**legs[0], "rtol": 1.0e-6, "maxiter": maxiter}]


def test_classify_pcg_legs_flags_a_row_on_any_one_capped_leg() -> None:
    """ONE capped leg among converged legs caps the WHOLE row.

    Bug caught: computing the verdict from only the first (or last) leg —
    the member-batch leg is the worst-converging leg in every measurement
    taken (554 vs 524 at 19 deg; 396-459 vs 342-422 at the anchor), so a
    first-leg-only verdict would systematically miss the leg that caps.
    """
    legs = [
        {"window": "w0", "iterations": 300, "final_rel_residual": 9.0e-7},
        {
            "window": "w0",
            "kind": "member-batch",
            "iterations": 500,
            "final_rel_residual": 2.84e-6,
        },
        {"window": "w1", "iterations": 310, "final_rel_residual": 9.1e-7},
    ]
    rows, capped = _mod.classify_pcg_legs(legs, rtol=1.0e-6, maxiter=500)
    assert capped is True
    assert len(rows) == 3


def test_classify_pcg_legs_stamps_copies_never_the_caller_legs() -> None:
    """Stamping happens on COPIES; the caller's leg dicts stay untouched.

    Bug caught: in-place stamping — the real caller's legs ARE the
    module-global miost CONVERGENCE_LOG entries, so mutating them corrupts
    the shared diagnostic log for every later solve in the process.
    """
    legs = [{"window": "w0", "iterations": 12, "final_rel_residual": 5.0e-7}]
    before = [dict(leg) for leg in legs]
    _mod.classify_pcg_legs(legs, rtol=1.0e-6, maxiter=1200)
    assert legs == before


def test_both_row_builders_route_through_the_one_classifier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """probe AND tile rows are BUILT from classify_pcg_legs' return value.

    Bug caught: the pin-26 defect class — a second, duplicated copy of the
    classification logic on the production path, free to drift from the
    probe's (which is exactly how a capped measurement closed a task). A
    duplicated implementation ignores this stub and fails on the sentinel.
    """
    seen: list[tuple[int, float, int]] = []

    def _fake(
        pcg: Any, *, rtol: float, maxiter: int
    ) -> tuple[list[dict[str, Any]], bool]:
        seen.append((len(list(pcg)), rtol, maxiter))
        return ([{"SENTINEL": "classified"}], True)

    monkeypatch.setattr(_mod, "classify_pcg_legs", _fake)
    probe = _mod.build_probe_row(date="2026-07-25", **_probe_measurement())
    tile = _mod.build_evidence_row(**_row_kwargs("anchor"))
    assert probe["pcg"] == [{"SENTINEL": "classified"}]
    assert probe["convergence"] == "CAPPED"
    assert probe["measured_vs_model"]["capped_measurement"] is True
    assert tile["pcg"] == [{"SENTINEL": "classified"}]
    assert tile["convergence"] == "CAPPED"
    assert seen == [(2, 1.0e-6, 500), (2, 1.0e-6, 1200)]


@pytest.mark.parametrize(
    ("iterations", "residual", "maxiter", "want"),
    [
        (1200, 1.3e-6, 1200, "CAPPED"),  # a T5 leg capped at the Stage-1 cap
        (554, 9.95e-7, 1200, "CONVERGED"),  # the measured 19-deg worst leg
        (500, 2.84e-6, 500, "CAPPED"),  # the T2 defect leg, on the tile path
    ],
)
def test_evidence_row_carries_its_own_convergence_verdict(
    iterations: int, residual: float, maxiter: int, want: str
) -> None:
    """A tile evidence row reports CONVERGED/CAPPED for its own solve legs.

    Bug caught: THE pin-26 gap — a production row that cannot report its
    own convergence, so a capped T5 leg (every 19-degree leg at the 500
    default) closes a task while looking exactly like a converged one.
    """
    row = _mod.build_evidence_row(
        **_row_kwargs(
            "seam_n", iterations=iterations, residual=residual, maxiter=maxiter
        )
    )
    assert row["convergence"] == want


def test_evidence_row_mirrors_capped_measurement_into_the_scores_block() -> None:
    """capped_measurement rides ALONGSIDE the numbers it qualifies.

    Bug caught: a capped verdict recorded only at row top level while the
    scores block (the part a rubric/ratio reader consumes) looks clean —
    the "labeled wherever it appears" rule the probe's measured_vs_model
    already follows, unenforced on the production path.
    """
    capped = _mod.build_evidence_row(
        **_row_kwargs("seam_n", iterations=1200, residual=1.3e-6, maxiter=1200)
    )
    clean = _mod.build_evidence_row(**_row_kwargs("seam_n"))
    assert capped["scores"]["capped_measurement"] is True
    assert clean["scores"]["capped_measurement"] is False
    assert clean["scores"]["mu"] == 0.9  # the caller's numbers survive


def test_evidence_row_pcg_legs_carry_rtol_maxiter_iterations_residual() -> None:
    """EVERY tile pcg leg records rtol + maxiter + iterations + residual.

    Bug caught: legs recorded without the cap they ran under, so a reader
    cannot tell a CAPPED leg from a CONVERGED one without out-of-band
    solver-config archaeology (the PIN-23(c) defect, on the tile path).
    """
    row = _mod.build_evidence_row(
        **_row_kwargs("anchor", iterations=1108, residual=9.9e-7, maxiter=1200)
    )
    assert len(row["pcg"]) == 2
    for leg in row["pcg"]:
        assert leg["rtol"] == 1.0e-6
        assert leg["maxiter"] == 1200
        assert leg["iterations"] == 1108
        assert leg["final_rel_residual"] == 9.9e-7


def test_evidence_row_never_mutates_caller_pcg_or_scores() -> None:
    """Building a row leaves the caller's pcg legs and scores dict untouched.

    Bug caught: in-place stamping of the live CONVERGENCE_LOG legs, or an
    in-place capped_measurement write into a scores dict the caller also
    hands to the scorer/rubric path.
    """
    kwargs = _row_kwargs("kuroshio")
    legs_before = [dict(leg) for leg in kwargs["pcg"]]
    _mod.build_evidence_row(**kwargs)
    assert kwargs["pcg"] == legs_before
    assert all("maxiter" not in leg for leg in kwargs["pcg"])
    assert kwargs["scores"] == {"mu": 0.9}


def test_run_default_maxiter_is_the_stage1_production_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A default `run` hands _solve_leg the measured Stage-1 cap, not 500.

    Bug caught: the pin-26 finding itself — the production path defaulting
    to the library PCG_MAXITER (500), under which every 19-degree T5 leg
    caps un-converged.
    """
    from sverdrup.application import ladder

    seen: list[int] = []
    monkeypatch.setattr(ladder, "tier1_eligible", lambda peak_mib: True)
    monkeypatch.setattr(
        _mod,
        "_solve_leg",
        lambda tile, m, days_stride, maxiter: seen.append(maxiter),
    )
    res = runner.invoke(_mod.app, ["run", "seam_n"])
    assert res.exit_code == 0, res.output
    assert seen == [_mod.STAGE1_PCG_MAXITER]


def test_run_maxiter_option_flows_through_to_the_solve_leg(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """--maxiter 777 reaches _solve_leg unchanged.

    Bug caught: --maxiter parsed but never passed through (the PIN-23(a)
    defect class) — the solve would run at one cap while the row records
    another, and "the maxiter used must be what the row records".
    """
    from sverdrup.application import ladder

    seen: list[int] = []
    monkeypatch.setattr(ladder, "tier1_eligible", lambda peak_mib: True)
    monkeypatch.setattr(
        _mod,
        "_solve_leg",
        lambda tile, m, days_stride, maxiter: seen.append(maxiter),
    )
    res = runner.invoke(_mod.app, ["run", "seam_n", "--maxiter", "777"])
    assert res.exit_code == 0, res.output
    assert seen == [777]


def test_solve_leg_hands_the_cap_to_the_solver(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_solve_leg builds its method at the maxiter it was handed.

    Bug caught: the leg constructing Miost at the library default while
    the row records the requested cap — every window would silently exit
    un-converged at 500 and the recorded convergence verdict would be
    about a cap the solve never ran under.
    """
    evid = tmp_path / "evidence.json"
    evid.write_text(json.dumps({"phase14": {"stage0": {"seal": {"sha": "ab" * 32}}}}))
    monkeypatch.setattr(_mod, "EVIDENCE", evid)
    monkeypatch.setattr(_mod, "_tile_framed_obs", lambda tile: _FakeLoad.for_tile(tile))
    seen: dict[str, Any] = {}

    def _miost(frame: Any, **kwargs: Any) -> Any:
        seen.update(kwargs)
        raise _SolveStopped

    monkeypatch.setattr(_mod, "_seam_miost", _miost)
    with pytest.raises(_SolveStopped):
        _mod._solve_leg("kuroshio", m=3, days_stride=1, maxiter=1900)
    assert seen["maxiter"] == 1900


def test_solve_leg_refuses_without_a_seal_sha_to_quote(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No stage-0 seal sha in the store -> refuse BEFORE loading anything.

    Bug caught: a 31 h leg running to completion and then failing to
    record, or recording a row that quotes an empty seal — the row's whole
    claim is that it was measured under a named seal.
    """
    evid = tmp_path / "evidence.json"
    evid.write_text(json.dumps({"phase14": {"stage1": {}}}))
    loaded: list[str] = []
    monkeypatch.setattr(_mod, "EVIDENCE", evid)
    monkeypatch.setattr(_mod, "_tile_framed_obs", lambda tile: loaded.append(tile))
    with pytest.raises(RuntimeError, match="seal"):
        _mod._solve_leg("kuroshio", m=3, days_stride=1, maxiter=1200)
    assert loaded == []


# ---------------------------------------------------------------------------
# Owner ruling PIN 26(c) — the seam-frame convergence probe (measure the
# frames T4 will actually solve, BEFORE spending T4)
# ---------------------------------------------------------------------------

# Pinned seam-probe row schema. As with the sizing probe: NO scores, NO
# seal_sha — a probe row carrying a µ would be evaluation-bearing.
_SEAM_KEYS = {
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
    "config",
    "model",
    "ram_gate",
    "date",
}


def _seam_measurement(
    iterations: int = 210,
    residual: float = 9.4e-7,
    maxiter: int = 2000,
) -> dict[str, Any]:
    """Injected fake seam measurement (defaults: both legs converged)."""
    return {
        "tile": "seam_n",
        "frame": {
            "core": [295.0, 305.0, 38.0, 43.0],
            "solve_bbox": [295.0, 305.0, 36.0, 43.0],
        },
        "window": [-18.0, 42.0],
        "superobs_cfg": None,
        "n_obs": 4200,
        "n_grid_nodes": 1887,
        "wall_s": 61.5,
        "peak_rss_mib": 900.0,
        "pcg": [
            {
                "window": "w-00018.0+60",
                "iterations": iterations,
                "final_rel_residual": residual,
            },
            {
                "window": "w-00018.0+60",
                "kind": "member-batch",
                "iterations": iterations + 30,
                "final_rel_residual": residual,
            },
        ],
        "pcg_rtol": 1.0e-6,
        "pcg_maxiter": maxiter,
        "config": {"missions": ["alg"], "rspec": "phase13-deltas"},
        "model": {"wall_est_s": 90.0, "peak_model_mib": 1000.0},
    }


_RAM_GATE_OK = {
    "mem_available_mib": 8000.0,
    "threshold_mib": 2000.0,
    "passed": True,
}


def test_seam_probe_row_schema_exactly_pinned() -> None:
    """build_seam_probe_row keys == the pinned seam-probe set, nothing else.

    Bug caught: a scores/µ block making an evaluation-bearing artifact out
    of a convergence probe, or the ram_gate / model provenance silently
    dropped so the recorded numbers cannot be re-grounded.
    """
    row = _mod.build_seam_probe_row(
        date="2026-07-26", ram_gate=_RAM_GATE_OK, **_seam_measurement()
    )
    assert set(row) == _SEAM_KEYS
    assert row["ram_gate"] == _RAM_GATE_OK


def test_seam_probe_row_pins_probe_label_m1_and_dc2021a_source() -> None:
    """Seam probe row: PROBE label, m == 1, registry dc2021a source.

    Bug caught: a STAGE1-EVIDENCE mislabel presenting a scoreless probe as
    a scored tile run, an m=100 production run billed as a cheap probe, or
    the source drifting off the registry's Stage-0 pin-4 map (the seam
    frames are dc2021a, NOT cmems_my — a cmems seam probe would measure
    the wrong obs density entirely).
    """
    row = _mod.build_seam_probe_row(
        date="2026-07-26", ram_gate=_RAM_GATE_OK, **_seam_measurement()
    )
    assert row["label"] == "PROBE"
    assert row["m"] == 1
    assert row["tile"] == "seam_n"
    assert row["source"] == "dc2021a"
    assert row["date"] == "2026-07-26"


@pytest.mark.parametrize(
    ("iterations", "residual", "want"),
    [
        (1970, 1.4e-6, "CAPPED"),  # member leg lands at 2000 over rtol
        (210, 9.4e-7, "CONVERGED"),
    ],
)
def test_seam_probe_row_convergence_verdict(
    iterations: int, residual: float, want: str
) -> None:
    """The seam row reports CAPPED when a leg hits the probe cap over rtol.

    Bug caught: a seam probe that cannot say it capped — the whole point of
    running it before T4 is that seam_read REFUSES on residual > rtol, so
    an unreported cap costs the entire T4 spend after the fact. (The
    member-batch leg carries +30 iters in the fake: at 1970 it is the leg
    that reaches 2000, exactly as in every measurement to date.)
    """
    row = _mod.build_seam_probe_row(
        date="2026-07-26",
        ram_gate=_RAM_GATE_OK,
        **_seam_measurement(iterations=iterations, residual=residual),
    )
    assert row["convergence"] == want


def test_seam_probe_row_pcg_legs_carry_rtol_and_maxiter() -> None:
    """Both seam legs record the rtol/cap they ran under.

    Bug caught: legs recorded bare, so a future reader of the seam evidence
    cannot tell whether 210 iterations was a converged solve or a cap.
    """
    row = _mod.build_seam_probe_row(
        date="2026-07-26", ram_gate=_RAM_GATE_OK, **_seam_measurement()
    )
    assert len(row["pcg"]) == 2
    for leg in row["pcg"]:
        assert leg["rtol"] == 1.0e-6
        assert leg["maxiter"] == 2000
    assert [leg["iterations"] for leg in row["pcg"]] == [210, 240]


def test_seam_ram_gate_admits_at_exactly_twice_the_predicted_peak() -> None:
    """RAM gate: pass iff MemAvailable >= 2 x predicted peak (>=, not >).

    Bug caught: a strict > drift refusing a launch that exactly meets the
    2x convention, or an inverted comparison admitting a launch with LESS
    headroom than the predicted peak (the exit-137 class). Boundary values
    hand-computed: 2 x 1000 = 2000.
    """
    exact = _mod.seam_ram_gate(peak_model_mib=1000.0, mem_available_mib=2000.0)
    assert exact == {
        "mem_available_mib": 2000.0,
        "threshold_mib": 2000.0,
        "passed": True,
    }
    short = _mod.seam_ram_gate(peak_model_mib=1000.0, mem_available_mib=1999.0)
    assert short["passed"] is False


def test_seam_probe_cli_refuses_launch_when_ram_gate_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failing RAM gate refuses BEFORE the solve; nothing is loaded.

    Bug caught: launching the seam solve over headroom — the OOM/silent
    kill class the fork-g pin-4 ordering exists to prevent; the refusal
    must fire before any obs load, not after.
    """
    solved: list[int] = []
    monkeypatch.setattr(_mod, "_mem_available_mib", lambda: 100.0)
    monkeypatch.setattr(
        _mod, "_seam_probe_solve", lambda maxiter: solved.append(maxiter)
    )
    res = runner.invoke(_mod.app, ["seam-probe"])
    assert res.exit_code != 0
    assert solved == []
    assert "MemAvailable" in res.output


def test_seam_probe_cli_records_at_the_pinned_node_and_exits_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A converged seam probe lands at phase14.stage1.seam_convergence_probe.

    Bug caught: recording at the wrong node (T4's gate reads this exact
    key), or clobbering the standing evidence store (the P0-2 class).
    """
    from sverdrup.validation import phase14_seal

    monkeypatch.setattr(phase14_seal, "verify_current_seal", lambda: None)
    monkeypatch.setattr(_mod, "_mem_available_mib", lambda: 1.0e6)
    evid = tmp_path / "evidence.json"
    evid.write_text(json.dumps({"phase13": {"kept": True}}))
    monkeypatch.setattr(_mod, "EVIDENCE", evid)
    monkeypatch.setattr(
        _mod, "_seam_probe_solve", lambda maxiter: _seam_measurement(maxiter=maxiter)
    )
    res = runner.invoke(_mod.app, ["seam-probe"])
    assert res.exit_code == 0, res.output
    stored = json.loads(evid.read_text())
    assert stored["phase13"] == {"kept": True}
    row = stored["phase14"]["stage1"]["seam_convergence_probe"]
    assert row["convergence"] == "CONVERGED"
    assert row["label"] == "PROBE"
    assert all(leg["maxiter"] == 2000 for leg in row["pcg"])


def test_seam_probe_cli_records_then_stops_when_a_leg_caps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A capped seam leg is RECORDED, then exits nonzero (owner surface).

    Bug caught: stop-before-record (the evidence lost exactly when the
    owner needs it) or a capped seam probe exiting 0 and letting T4 launch
    against frames whose solves cannot meet the rtol seam_read demands.
    """
    from sverdrup.validation import phase14_seal

    monkeypatch.setattr(phase14_seal, "verify_current_seal", lambda: None)
    monkeypatch.setattr(_mod, "_mem_available_mib", lambda: 1.0e6)
    evid = tmp_path / "evidence.json"
    monkeypatch.setattr(_mod, "EVIDENCE", evid)
    monkeypatch.setattr(
        _mod,
        "_seam_probe_solve",
        lambda maxiter: _seam_measurement(iterations=1970, residual=1.4e-6),
    )
    res = runner.invoke(_mod.app, ["seam-probe"])
    assert res.exit_code != 0
    stored = json.loads(evid.read_text())
    assert stored["phase14"]["stage1"]["seam_convergence_probe"]["convergence"] == (
        "CAPPED"
    )
    assert "STOP" in res.output


def test_seam_probe_cli_default_maxiter_is_2000(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The seam probe defaults to the owner's 2000 headroom cap.

    Bug caught: probing at the Stage-1 production cap (or the 500 library
    default) — a probe that caps tells you nothing except that it capped,
    which is exactly the measurement failure pin 26 was raised about.
    """
    from sverdrup.validation import phase14_seal

    monkeypatch.setattr(phase14_seal, "verify_current_seal", lambda: None)
    monkeypatch.setattr(_mod, "_mem_available_mib", lambda: 1.0e6)
    monkeypatch.setattr(_mod, "EVIDENCE", tmp_path / "evidence.json")
    seen: list[int] = []

    def _spy(maxiter: int) -> dict[str, Any]:
        seen.append(maxiter)
        return _seam_measurement(maxiter=maxiter)

    monkeypatch.setattr(_mod, "_seam_probe_solve", _spy)
    res = runner.invoke(_mod.app, ["seam-probe"])
    assert res.exit_code == 0, res.output
    assert seen == [2000]
    assert _mod.SEAM_PROBE_MAXITER == 2000


def test_seam_probe_geometry_is_the_registry_seam_frame() -> None:
    """The probe measures the frame T4 solves: seam_n, 51 x 37 nodes.

    Bug caught: probing a different (e.g. anchor-sized or core-only) box —
    the convergence number would not transfer to T4 at all. Node counts
    measured independently with the frame grid before pinning: the solve
    bbox [295,305]x[36,43] at 0.2 deg gives 51 lon nodes and 37 lat nodes
    (36 by arithmetic + the recorded fp-overshoot extra node), 1887 total —
    well under the anchor's 51x52 = 2652.
    """
    from sverdrup.application.spatial_tiles import frame_grid

    assert _mod.SEAM_PROBE_TILE == "seam_n"
    grid = frame_grid(_mod.registry_frame(_mod.SEAM_PROBE_TILE), _mod.RESOLUTION_DEG)
    assert (grid.x.size, grid.y.size) == (51, 37)
    assert grid.x.size * grid.y.size < 2652


# ---------------------------------------------------------------------------
# Task 4 — seam pair: the PRIMARY PAIR READ + the secondary ORACLE READ
# (owner-ruled two-route shape; the rubric's Rule-0 floor attaches to the
# PAIR first, the ORACLE carries its OWN floor, never shared)
# ---------------------------------------------------------------------------


# Hand-built fields whose one-grid-step LATITUDE increments are exactly the
# given step. Built independently of the module under test (a plain outer
# product), so every D_int expectation below is a hand value.
def _interior(step: float, rows: int = 3, cols: int = 3) -> np.ndarray:
    """Field with constant one-step latitude increments (axis -2)."""
    return np.outer(np.arange(rows, dtype=float) * step, np.ones(cols))


# rms_delta hand values: constant seams differing by 0.02 m (mean) and
# 0.003 m (sigma) — DISTINCT per field kind so a route swap is caught.
_SEAM_A = np.full(3, 0.05)
_SEAM_B = np.full(3, 0.03)
_SIG_A = np.full(3, 0.011)
_SIG_B = np.full(3, 0.008)

# Pooled-interior hand values (both tiles pooled, equal node counts):
#   mean : sqrt((6*2^2 + 6*4^2)/12) = sqrt(10)  = 3.1622776601683795
#   sigma: sqrt((6*1^2 + 6*3^2)/12) = sqrt(5)   = 2.23606797749979
_D_INT_PAIR_MEAN = 10.0**0.5
_D_INT_PAIR_SIGMA = 5.0**0.5
# The SEAMLESS solve's own interior (never pooled with the tiles').
_D_INT_ORACLE_MEAN = 4.0
_D_INT_ORACLE_SIGMA = 3.0


def _pair_read_kwargs(**over: Any) -> dict[str, Any]:
    """Injected fakes for the PAIR read (both tiles' own solves)."""
    kw: dict[str, Any] = {
        "mean_a": _SEAM_A,
        "mean_b": _SEAM_B,
        "sigma_a": _SIG_A,
        "sigma_b": _SIG_B,
        "interior_mean_a": _interior(2.0),
        "interior_mean_b": _interior(4.0),
        "interior_sigma_a": _interior(1.0),
        "interior_sigma_b": _interior(3.0),
        "residual_a": 9.3e-7,
        "rtol_a": 1.0e-6,
        "residual_b": 9.5e-7,
        "rtol_b": 1.0e-6,
    }
    kw.update(over)
    return kw


def _oracle_read_kwargs(**over: Any) -> dict[str, Any]:
    """Injected fakes for the ORACLE read (blend vs seamless truth)."""
    kw: dict[str, Any] = {
        "blended_mean": _SEAM_A,
        "seamless_mean": _SEAM_B,
        "blended_sigma": _SIG_A,
        "seamless_sigma": _SIG_B,
        "seamless_interior_mean": _interior(4.0),
        "seamless_interior_sigma": _interior(3.0),
        "residual_blend": 9.5e-7,
        "rtol_blend": 1.0e-6,
        "residual_seamless": 9.9e-7,
        "rtol_seamless": 1.0e-6,
    }
    kw.update(over)
    return kw


def _floor_probe(converged: bool = True) -> dict[str, Any]:
    """A recorded deeper-tolerance probe block (pin 23's five fields)."""
    return {
        "rtol": 1.0e-9,
        "maxiter": 2200,
        "iterations": 611,
        "final_rel_residual": 9.1e-10,
        "converged": converged,
        "m": 100,
        "window": "w-00018.0+60",
        "scope": "seam pair roster (seam_n + seam_s), deeper tolerance",
    }


def _floor(f: float = 0.005, converged: bool = True) -> dict[str, Any]:
    """An attributability block at floor F (default: 3F = 0.015 < 0.02)."""
    return _mod.floor_attributability(
        rms_delta=0.02, floor_f=f, probe=_floor_probe(converged)
    )


def _row(**over: Any) -> dict[str, Any]:
    """One assembled seam row with injected numbers."""
    kw: dict[str, Any] = {
        "route": "pair",
        "field_kind": "mean",
        "rms_delta": 0.02,
        "d_int": _D_INT_PAIR_MEAN,
        "r_seam": 0.02 / _D_INT_PAIR_MEAN,
        "rubric_cell": "CLEAN",
        "floor": _floor(),
        "seal_sha": "cafe" * 16,
        "date": "2026-07-26",
    }
    kw.update(over)
    return _mod.build_seam_row(**kw)


# --- the ONE evaluation domain: "the 2·overlap strip" ----------------------


def test_seam_strip_is_two_overlap_wide_centred_on_the_shared_core_boundary() -> None:
    """The strip is DERIVED from the two registry frames, not typed.

    Bug caught: a hand-typed strip constant that silently desyncs when a
    seam frame moves, or a HALF-width strip (one overlap instead of two) —
    either reads a different region than the rubric's "2·overlap strip
    centred on the shared core boundary". Hand values from the registry:
    the shared core boundary is 38.0N, overlap 2.0 deg, so the strip is
    lat 36-40 across the shared lon span 295-305.
    """
    strip = _mod.seam_strip_bbox()
    assert (strip.lon_min, strip.lon_max) == (295.0, 305.0)
    assert (strip.lat_min, strip.lat_max) == (36.0, 40.0)
    # 2 x overlap wide, centred on the boundary — stated independently.
    assert strip.lat_max - strip.lat_min == 2 * 2.0
    assert 0.5 * (strip.lat_min + strip.lat_max) == 38.0


def test_seam_strip_lies_inside_both_tiles_own_solves() -> None:
    """Both tiles SOLVE the whole strip — the pair read needs both.

    Bug caught: a strip reaching past seam_n's southern solve edge (36.0N)
    or seam_s's northern edge (40.0N), where one tile has no solution at
    all — delta(x) would then be taken against extrapolated or NaN values
    and the whole PRIMARY route would be measuring nothing.
    """
    strip = _mod.seam_strip_bbox()
    for tile in _mod.SEAM_PAIR_TILES:
        solve = _mod.registry_frame(tile).solve_bbox
        assert solve.lat_min <= strip.lat_min
        assert solve.lat_max >= strip.lat_max
        assert solve.lon_min <= strip.lon_min
        assert solve.lon_max >= strip.lon_max


def test_strip_nodes_are_co_located_across_both_tiles_and_the_anchor() -> None:
    """The selected strip nodes are the SAME points on all three grids.

    Bug caught: off-by-one index slicing (a shifted difference would
    manufacture a seam signal out of the field's own gradient) or a
    resolution/lattice mismatch between the tile grids and the seamless
    anchor grid, which would silently make the ORACLE compare unlike
    points. Independently: all three frames share the 0.2 deg lattice
    anchored at 295.0/33.0, so the strip must select identical values.
    """
    from sverdrup.application.spatial_tiles import frame_grid

    picks = []
    for tile in (*_mod.SEAM_PAIR_TILES, "anchor"):
        grid = frame_grid(_mod.registry_frame(tile), _mod.RESOLUTION_DEG)
        lat_m, lon_m = _mod.strip_mask(grid, _mod.seam_strip_bbox())
        picks.append((grid.y[lat_m], grid.x[lon_m]))
    for lats, lons in picks[1:]:
        assert np.allclose(lats, picks[0][0])
        assert np.allclose(lons, picks[0][1])
    # 36.0..40.0 at 0.2 deg = 21 rows; 295..305 = 51 columns (hand count).
    assert picks[0][0].size == 21
    assert picks[0][1].size == 51


def test_core_interior_trims_the_overlap_width_from_every_core_boundary() -> None:
    """Interiors are the rubric's "every node >= overlap-width from any core
    boundary" — hand-checked bounds.

    Bug caught: an untrimmed interior reaching the seam itself, so D_int
    would be contaminated by the very cross-tile disagreement it is there
    to normalize (R_seam would then be self-referential and always small).
    seam_n core is lat 38-43 / lon 295-305; trimming 2.0 deg leaves lat
    40-41 and lon 297-303.
    """
    from sverdrup.application.spatial_tiles import frame_grid

    grid = frame_grid(_mod.registry_frame("seam_n"), _mod.RESOLUTION_DEG)
    lat_m, lon_m = _mod.core_interior_mask(_mod.registry_frame("seam_n"), grid)
    lats, lons = grid.y[lat_m], grid.x[lon_m]
    assert lats.min() >= 40.0 - 1e-9
    assert lats.max() <= 41.0 + 1e-9
    assert lons.min() >= 297.0 - 1e-9
    assert lons.max() <= 303.0 + 1e-9
    assert lats.size == 6  # 40.0..41.0 at 0.2 deg
    assert lons.size == 31  # 297.0..303.0 at 0.2 deg


def test_seam_perpendicular_axis_is_latitude_in_the_map_convention() -> None:
    """D_int pools along LATITUDE (the seam at 38N runs east-west).

    Bug caught: pooling along the seam-PARALLEL axis. On this fixture the
    latitude increments are 4.0 and the longitude increments 1.0, so a
    wrong-axis D_int reads 1.0 where 4.0 is true — a 4x wrong denominator
    on every verdict. Axis -2 is pinned because maps are (time, lat, lon).
    """
    from sverdrup.validation.seam_metrics import interior_increment_rms

    stack = np.stack([np.arange(16.0).reshape(4, 4) * 4.0] * 2)  # rows differ by 16
    field = np.stack([np.outer(np.arange(4.0) * 4.0, np.ones(4)) + np.arange(4.0)] * 2)
    assert _mod.SEAM_PERP_AXIS == -2
    assert interior_increment_rms(field, _mod.SEAM_PERP_AXIS) == pytest.approx(4.0)
    assert interior_increment_rms(field, -1) == pytest.approx(1.0)
    assert stack.ndim == 3  # the (time, lat, lon) shape the real leg passes


# --- the TWO D_int denominators (different by design) ---------------------


def test_pair_read_pools_both_tile_interiors_per_rubric_r06_r07() -> None:
    """PAIR D_int = pooled core interiors of BOTH tiles.

    Bug caught: normalizing by ONE tile's interior. Hand value:
    sqrt((6*2^2 + 6*4^2)/12) = sqrt(10) = 3.16228, which is neither
    2.0 nor 4.0 — a single-tile denominator cannot produce it.
    """
    read = _mod.pair_read(**_pair_read_kwargs())
    assert read.d_int == pytest.approx(_D_INT_PAIR_MEAN)
    assert read.d_int_sigma == pytest.approx(_D_INT_PAIR_SIGMA)
    assert read.rms_delta == pytest.approx(0.02)
    assert read.rms_sigma_delta == pytest.approx(0.003)
    assert read.r_seam == pytest.approx(0.02 / _D_INT_PAIR_MEAN)
    assert read.r_seam_sigma == pytest.approx(0.003 / _D_INT_PAIR_SIGMA)


def test_oracle_read_d_int_is_the_seamless_interior_alone_per_rubric_r19() -> None:
    """ORACLE D_int = the SEAMLESS solve's interior, never the tiles'.

    Bug caught: a future reader "fixing the inconsistency" by pooling the
    two tile interiors into the ORACLE denominator — the flagship
    blend-vs-truth ratio would silently change scale. Hand value: the
    seamless interior's own increments are 4.0, so D_int is exactly 4.0
    (pooling a set with itself is the identity on RMS).
    """
    read = _mod.oracle_read(**_oracle_read_kwargs())
    assert read.d_int == pytest.approx(_D_INT_ORACLE_MEAN)
    assert read.d_int_sigma == pytest.approx(_D_INT_ORACLE_SIGMA)
    assert read.r_seam == pytest.approx(0.005)
    assert read.r_seam_sigma == pytest.approx(0.001)


def test_the_two_denominators_differ_on_the_same_seam_fields() -> None:
    """Same seam fields, DIFFERENT denominators — the invariant, behaviourally.

    Bug caught: unifying the two denominators (either direction). With
    identical seam inputs the pair ratio is 0.02/sqrt(10) and the oracle
    ratio 0.02/4 — if either read adopted the other's interior these two
    numbers would collide.
    """
    pair = _mod.pair_read(**_pair_read_kwargs())
    oracle = _mod.oracle_read(**_oracle_read_kwargs())
    assert pair.d_int != pytest.approx(oracle.d_int)
    assert _mod.PAIR_D_INT_SOURCE != _mod.ORACLE_D_INT_SOURCE
    assert "both" in _mod.PAIR_D_INT_SOURCE
    assert "seamless" in _mod.ORACLE_D_INT_SOURCE


def test_rows_record_which_denominator_they_used() -> None:
    """Each row names its own D_int source verbatim.

    Bug caught: rows that record the number but not which interior it came
    from — the pair/oracle comparison becomes unreadable a stage later,
    which is exactly how the inconsistency gets "fixed" by mistake.
    """
    assert _row(route="pair")["d_int_source"] == _mod.PAIR_D_INT_SOURCE
    assert _row(route="oracle")["d_int_source"] == _mod.ORACLE_D_INT_SOURCE
    with pytest.raises(ValueError, match="route"):
        _row(route="blend")


# --- Rule 0: floor-probe attributability (pin 23) -------------------------


@pytest.mark.parametrize(
    ("floor_f", "want_attributable", "want_verdict"),
    [
        (0.005, True, "CLEAN"),  # 3F = 0.015 < 0.02
        (0.02 / 3.0, False, "UNMEASURED (solver floor)"),  # 3F == 0.02 exactly
        (0.01, False, "UNMEASURED (solver floor)"),  # 3F = 0.03 > 0.02
    ],
)
def test_attributability_needs_rms_strictly_above_three_times_the_floor(
    floor_f: float, want_attributable: bool, want_verdict: str
) -> None:
    """RMS(delta) must EXCEED 3xF; equality is not attributable.

    Bug caught: a >= comparison admitting a verdict exactly at the floor
    bound, where the measured disagreement is indistinguishable from
    solver noise. Boundary hand-computed: 3 x (0.02/3) = 0.02 == RMS.
    """
    row = _row(floor=_floor(f=floor_f))
    assert row["attributable"] is want_attributable
    assert row["verdict"] == want_verdict
    assert row["floor"]["threshold_m"] == pytest.approx(3.0 * floor_f)


def test_unmeasured_row_is_never_clean_but_still_records_the_number() -> None:
    """Below the floor: the number is recorded, the verdict is UNMEASURED.

    Bug caught: recording a floor-failing pair as CLEAN — the precise
    failure Rule 0 exists to prevent (a solver-noise-sized disagreement
    presented as "no seam artifact"). The raw rubric cell is kept beside
    it so nothing is hidden.
    """
    row = _row(floor=_floor(f=0.01))
    assert row["verdict"] == "UNMEASURED (solver floor)"
    assert row["verdict"] != "CLEAN"
    assert row["rubric_cell"] == "CLEAN"
    assert row["rms_delta"] == pytest.approx(0.02)
    assert row["r_seam"] == pytest.approx(0.02 / _D_INT_PAIR_MEAN)


def test_floor_refuses_outright_when_the_deeper_solve_did_not_converge() -> None:
    """Pin 23: a non-converged deeper solve is a STOP, not an UNMEASURED row.

    Bug caught: treating the gap between two TRUNCATION points as a floor —
    3xF then has no meaning, and the pair would be quietly filed as
    "unmeasured" instead of surfaced to the owner.
    """
    with pytest.raises(RuntimeError, match="STOP"):
        _mod.floor_attributability(
            rms_delta=0.02, floor_f=0.005, probe=_floor_probe(converged=False)
        )


@pytest.mark.parametrize(
    "missing", ["rtol", "maxiter", "iterations", "final_rel_residual", "converged"]
)
def test_floor_probe_must_record_all_five_convergence_fields(missing: str) -> None:
    """Pin 23's recording clause: F without its convergence evidence refuses.

    Bug caught: a floor recorded as a bare number — a later reader cannot
    tell whether it came from a converged solve, and the 3xF gate becomes
    unverifiable.
    """
    probe = _floor_probe()
    probe.pop(missing)
    with pytest.raises(ValueError, match=missing):
        _mod.floor_attributability(rms_delta=0.02, floor_f=0.005, probe=probe)


def test_floor_block_carries_the_probe_evidence_into_the_row() -> None:
    """The row carries rtol/maxiter/iterations/residual/CONVERGED.

    Bug caught: the attributability decision recorded without the evidence
    that licenses it (pin 23 requires the row to RECORD that the deeper
    solve reached rtol).
    """
    probe = _row()["floor"]["probe"]
    assert probe["converged"] is True
    assert probe["rtol"] == 1.0e-9
    assert probe["maxiter"] == 2200
    assert probe["iterations"] == 611
    assert probe["final_rel_residual"] == 9.1e-10


def test_oracle_floor_is_its_own_and_never_the_pairs() -> None:
    """The ORACLE's floor block is separate from the PAIR's.

    Bug caught: reusing the pair's floor for the oracle — the oracle's
    seamless side would never be probed at all, so its attributability
    claim would rest on a measurement of two different solves.
    """
    pair = _row(route="pair", floor=_floor(f=0.005))
    oracle_probe = dict(_floor_probe(), scope="ORACLE: blend + seamless anchor")
    oracle = _row(
        route="oracle",
        floor=_mod.floor_attributability(
            rms_delta=0.02, floor_f=0.001, probe=oracle_probe
        ),
    )
    assert pair["floor"]["f_m"] == 0.005
    assert oracle["floor"]["f_m"] == 0.001
    assert oracle["floor"]["probe"]["scope"] != pair["floor"]["probe"]["scope"]


def test_tier1_wait_marks_the_pair_unmeasured_pending_owner_not_skipped() -> None:
    """A refused floor leg records a WAIT and withholds the verdict.

    Bug caught: silently skipping the floor probe when the ladder refuses
    it and then reporting CLEAN anyway — an unfloored verdict presented as
    a floored one.
    """
    row = _row(floor=_mod.floor_wait_block(reason="tier1_eligible refused"))
    assert row["verdict"] == "UNMEASURED (pending owner — floor-probe WAIT)"
    assert row["floor"]["status"] == "WAIT"
    assert row["attributable"] is False
    assert row["rms_delta"] == pytest.approx(0.02)


# --- row schema, namespace, caveats ---------------------------------------

_SEAM_ROW_KEYS = {
    "route",
    "pair",
    "era",
    "field_kind",
    "resolution_deg",
    "domain",
    "rms_delta",
    "d_int",
    "d_int_source",
    "r_seam",
    "rubric_cell",
    "verdict",
    "attributable",
    "floor",
    "geometry",
    "non_transfer_note",
    "oracle_note",
    "seal_sha",
    "label",
    "date",
}


def test_seam_row_schema_exactly_pinned() -> None:
    """The row key set is EXACTLY the schema — no free-prose field exists.

    Bug caught: an "interpretation"/"notes" field appearing on a row whose
    whole point is numbers-plus-caveat (review pin 8's structural control).
    """
    assert set(_row()) == _SEAM_ROW_KEYS


def test_row_carries_the_rubric_row_shape_with_era_and_resolution() -> None:
    """{pair, era, field_kind, rms_delta, d_int, r_seam, verdict} + resolution.

    Bug caught: dropping `era` (or `resolution_deg`) because Stage 1 has
    exactly one of each — a ROW COUNT is not a schema excuse, and the keys
    cost nothing now against a migration at Stage 2.
    """
    row = _row()
    for key in ("pair", "era", "field_kind", "rms_delta", "d_int", "r_seam"):
        assert key in row
    assert row["pair"] == "seam_n|seam_s"
    assert row["era"] == "2017"
    assert row["resolution_deg"] == 0.2
    assert row["field_kind"] == "mean"
    assert row["domain"]["name"] == "the 2·overlap strip"
    assert row["domain"]["bbox"] == [295.0, 305.0, 36.0, 40.0]


def test_geometry_caveat_and_non_transfer_sentence_are_pinned_verbatim() -> None:
    """Review pin 13: the geometry caveat rides every row, verbatim.

    Bug caught: a positive seam verdict read three documents later as a
    production-geometry result. The strings are stated here independently
    of the module, so any drift fails.
    """
    row = _row()
    assert row["geometry"] == (
        "10x5 halves inside the anchor footprint — NOT D1 production geometry (15x15)"
    )
    note = row["non_transfer_note"]
    assert "not a production-geometry seam reading" in note
    assert "TILE COUNT" in note
    assert "feasibility-frontier" in note


def test_oracle_rows_carry_the_gap_register_note_and_pair_rows_do_not() -> None:
    """oracle_note on the ORACLE route only.

    Bug caught: dropping the no-published-precedent disclaimer from the
    oracle (it is our own clause, T11 gap-register), or pasting it onto
    the pair route where it is simply false — the pair read IS the
    pre-registered rubric route.
    """
    assert _row(route="oracle")["oracle_note"] == (
        "no published precedent — gap-register (T11)"
    )
    assert _row(route="pair")["oracle_note"] is None


# --- pin 34: F defined by ACCURACY TARGET, not iteration budget ------------


def test_floor_probe_rtol_is_the_pre_registered_accuracy_target() -> None:
    """FLOOR_RTOL is production rtol / 10^decades, with decades pinned at 3.

    Hand values from the ruling: three decades below a production 1e-6 is
    1e-9 — the construction the executed T4 probes ran under and which
    pin 34 pre-registers.

    Bug caught: someone loosening the probe tolerance (the tempting fix
    when a probe is slow to converge) — F would then be measured against
    a looser accuracy target and would silently become a smaller floor,
    licensing verdicts the rubric does not license. Pin 34: non-attainment
    is a STOP, never a fallback to a looser F.
    """
    assert _mod.FLOOR_DECADES == 3
    assert _mod.SEAM_PRODUCTION_RTOL == 1.0e-6
    assert _mod.FLOOR_RTOL == pytest.approx(1.0e-9, rel=1e-12)
    assert _mod.FLOOR_RTOL == pytest.approx(
        _mod.SEAM_PRODUCTION_RTOL * 10.0**-_mod.FLOOR_DECADES, rel=1e-12
    )


def test_floor_block_records_the_accuracy_target_and_what_was_achieved() -> None:
    """The block states the target AND the residual actually reached.

    Bug caught: a row recording only F. Pin 34 requires the achieved
    residual beside the stated target, because that pairing is the only
    way a later reader can check the probe met its accuracy target rather
    than merely reporting a converged flag.
    """
    block = _mod.floor_attributability(
        rms_delta=0.02, floor_f=0.005, probe=_floor_probe()
    )
    assert block["decades_below_production_rtol"] == 3
    assert block["production_rtol"] == 1.0e-6
    assert block["target_rtol"] == pytest.approx(1.0e-9, rel=1e-12)
    assert block["achieved_rel_residual"] == 9.1e-10
    assert block["f_m"] == 0.005
    assert block["threshold_m"] == pytest.approx(0.015, rel=1e-12)


def test_floor_attributability_refuses_a_probe_that_missed_its_target() -> None:
    """A probe whose achieved residual misses the target is a STOP.

    The probe here reports converged=True but its final relative residual
    (5e-8) is above the pre-registered 1e-9 target — i.e. it converged
    against a LOOSER tolerance than the rubric pre-registers.

    Bug caught: accepting such a probe as F. That is precisely the
    "fallback to a looser F" pin 34 forbids: the floor would be measured
    at an accuracy the rubric does not sanction, and every verdict above
    it would inherit the error while looking fully floored.
    """
    probe = _floor_probe()
    probe["final_rel_residual"] = 5.0e-8
    with pytest.raises(RuntimeError, match="accuracy target"):
        _mod.floor_attributability(rms_delta=0.02, floor_f=0.005, probe=probe)


def test_seam_rows_from_read_cover_both_routes_and_both_field_kinds() -> None:
    """Four rows: {pair, oracle} x {mean, sigma}.

    Bug caught: the sigma route silently dropped — a mean-only seam
    reading would pass as a complete one, which is exactly the T10 gap
    the rubric's second ratio exists to close.
    """
    rows = _mod.seam_rows_from_read(
        route="pair",
        read=_mod.pair_read(**_pair_read_kwargs()),
        floor_mean=_floor(),
        floor_sigma=_floor(f=0.0005),
        seal_sha="cafe" * 16,
        date="2026-07-26",
    ) + _mod.seam_rows_from_read(
        route="oracle",
        read=_mod.oracle_read(**_oracle_read_kwargs()),
        floor_mean=_floor(f=0.001),
        floor_sigma=_floor(f=0.0002),
        seal_sha="cafe" * 16,
        date="2026-07-26",
    )
    assert [(r["route"], r["field_kind"]) for r in rows] == [
        ("pair", "mean"),
        ("pair", "sigma"),
        ("oracle", "mean"),
        ("oracle", "sigma"),
    ]
    # The sigma rows carry the SIGMA numbers, not the mean ones.
    assert rows[1]["rms_delta"] == pytest.approx(0.003)
    assert rows[1]["d_int"] == pytest.approx(_D_INT_PAIR_SIGMA)
    assert rows[3]["d_int"] == pytest.approx(_D_INT_ORACLE_SIGMA)


def test_record_seam_rows_writes_the_rubric_namespace_and_merges(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rows land at phase14.stage1.seam_rows; the store is merged, not clobbered.

    Bug caught: recording under a private key (the rubric names this
    namespace, and the Gate-1 pack reads it) or overwriting the standing
    evidence store (the P0-2 class).
    """
    from sverdrup.validation import phase14_seal

    monkeypatch.setattr(phase14_seal, "verify_current_seal", lambda: None)
    evid = tmp_path / "evidence.json"
    evid.write_text(json.dumps({"phase14": {"stage1": {"probe": {"kept": True}}}}))
    _mod.record_seam_rows([_row()], evidence_path=evid)
    stored = json.loads(evid.read_text())
    assert stored["phase14"]["stage1"]["probe"] == {"kept": True}
    assert len(stored["phase14"]["stage1"]["seam_rows"]) == 1
    assert stored["phase14"]["stage1"]["seam_rows"][0]["pair"] == "seam_n|seam_s"


def test_record_seam_rows_is_seal_gated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No verified seal -> nothing is written (the Task-10 tripwire).

    Bug caught: a seam row written into the evidence store while the
    evaluation seal cannot be verified — an unsealed evaluation-bearing
    artifact.
    """
    from sverdrup.validation import phase14_seal

    def _boom() -> None:
        raise phase14_seal.SealError("no seal")

    monkeypatch.setattr(phase14_seal, "verify_current_seal", _boom)
    evid = tmp_path / "evidence.json"
    with pytest.raises(phase14_seal.SealError):
        _mod.record_seam_rows([_row()], evidence_path=evid)
    assert not evid.exists()


# --- the floor probe's own sizing + lineage reuse --------------------------


def test_floor_probe_plan_states_the_tier1_arithmetic_before_it_runs() -> None:
    """Pin 20(b): the extra leg is sized and laddered BEFORE it is spent.

    Bug caught: an unpriced extra solve launched over headroom (the
    exit-137 class), or a floor leg whose cost never appears in the
    evidence at all.
    """
    plan = _mod.floor_probe_plan()
    assert plan["m"] == _mod.SEAM_PAIR_M  # see the m-justification below
    assert plan["window_index"] == 0
    assert plan["n_windows"] == 1
    assert plan["maxiter"] == _mod.STAGE1_PCG_MAXITER + 1000
    assert plan["rtol"] < 1.0e-6  # DEEPER tolerance, not just more iterations
    assert set(plan["models"]) == set(_mod.SEAM_PAIR_TILES) | {"anchor"}
    for model in plan["models"].values():
        assert model["peak_model_mib"] > 0.0
    assert isinstance(plan["tier1_eligible"], bool)
    assert "m=100" in plan["m_justification"]


def test_floor_probe_deeper_solve_is_deeper_on_both_axes() -> None:
    """The probe raises the cap AND tightens rtol.

    Bug caught: re-solving at the SAME rtol with maxiter+1000. The
    production seam solve converges at ~407 iterations against a 1200 cap,
    so more iterations alone changes nothing — F would come out exactly 0
    and 3xF would license every verdict vacuously.
    """
    plan = _mod.floor_probe_plan()
    assert plan["maxiter"] > _mod.STAGE1_PCG_MAXITER
    assert plan["rtol"] < _mod.SEAM_PRODUCTION_RTOL


def test_floor_machinery_reuses_the_task18_lineage_by_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The floor path calls the Task-18 diagnostic's own std/mean helpers.

    Bug caught: a reimplemented member-std evaluation drifting from the
    Task-18-lineage construction the rubric's Rule 0 is defined against.
    Behavioural (never a source scan): a sentinel installed on the
    diagnostic module is what the driver picks up.
    """
    lineage = _mod._diag_lineage()
    sentinel = object()
    monkeypatch.setattr(lineage, "std_fields", sentinel)
    assert _mod._lineage_std_fields() is sentinel
    monkeypatch.setattr(lineage, "exclusive_days", sentinel)
    assert _mod._lineage_exclusive_days() is sentinel


# --- the CLI: gates, stops, and never blocking mechanically ---------------


def test_seam_pair_cli_refuses_launch_when_the_ram_gate_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MemAvailable < 2x predicted peak -> nothing is solved.

    Bug caught: launching two m=100 legs over headroom — the silent-OOM
    class that already cost this stage one anchor launch.
    """
    ran: list[Any] = []
    monkeypatch.setattr(_mod, "_mem_available_mib", lambda: 10.0)
    monkeypatch.setattr(_mod, "_seam_pair_real_leg", lambda **kw: ran.append(kw))
    res = runner.invoke(_mod.app, ["seam-pair"])
    assert res.exit_code != 0
    assert ran == []
    assert "MemAvailable" in res.output


def test_seam_pair_cli_records_rows_then_surfaces_structural_stop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """STRUCTURAL_STOP is RECORDED first, then surfaced to the owner.

    Bug caught: stopping before the write (the evidence lost exactly when
    the owner needs it), or a mechanical block — other tiles do not
    consume seams and must be able to continue.
    """
    from sverdrup.validation import phase14_seal

    monkeypatch.setattr(phase14_seal, "verify_current_seal", lambda: None)
    monkeypatch.setattr(_mod, "_mem_available_mib", lambda: 1.0e6)
    evid = tmp_path / "evidence.json"
    monkeypatch.setattr(_mod, "EVIDENCE", evid)
    stop_row = _row(rubric_cell="STRUCTURAL_STOP", floor=_floor(f=0.001))
    monkeypatch.setattr(
        _mod,
        "_seam_pair_real_leg",
        lambda **kw: {
            "rows": [stop_row],
            "block": {"label": "SEAM-PAIR"},
            "stop": None,
        },
    )
    res = runner.invoke(_mod.app, ["seam-pair"])
    stored = json.loads(evid.read_text())
    assert stored["phase14"]["stage1"]["seam_rows"][0]["verdict"] == "STRUCTURAL_STOP"
    assert res.exit_code != 0
    assert "STRUCTURAL_STOP" in res.output
    assert "other tiles" in res.output.lower()


def test_seam_pair_cli_stops_immediately_when_a_seam_solve_caps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A capped seam solve stops BEFORE any verdict is claimed (pin 23).

    Bug caught: computing and recording a verdict on a solve seam_read
    would refuse anyway — the whole T4 spend reported as a reading.
    """
    from sverdrup.validation import phase14_seal

    monkeypatch.setattr(phase14_seal, "verify_current_seal", lambda: None)
    monkeypatch.setattr(_mod, "_mem_available_mib", lambda: 1.0e6)
    evid = tmp_path / "evidence.json"
    monkeypatch.setattr(_mod, "EVIDENCE", evid)
    monkeypatch.setattr(
        _mod,
        "_seam_pair_real_leg",
        lambda **kw: {
            "rows": [],
            "block": {"label": "SEAM-PAIR", "convergence": "CAPPED"},
            "stop": "PIN23",
        },
    )
    res = runner.invoke(_mod.app, ["seam-pair"])
    assert res.exit_code != 0
    assert "CAPPED" in res.output
    stored = json.loads(evid.read_text())
    assert stored["phase14"]["stage1"]["seam_pair"]["convergence"] == "CAPPED"
    assert stored["phase14"]["stage1"].get("seam_rows", []) == []


def test_seam_pair_cli_stops_when_the_floor_probe_does_not_converge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A non-converged floor probe is RECORDED, then STOPPED on (pin 23).

    Bug caught: losing the probe rows to an uncaught refusal — the owner
    is asked to rule on a non-converging deeper solve and needs exactly
    those numbers; and the stop must not be dressed up as an UNMEASURED
    verdict.
    """
    from sverdrup.validation import phase14_seal

    monkeypatch.setattr(phase14_seal, "verify_current_seal", lambda: None)
    monkeypatch.setattr(_mod, "_mem_available_mib", lambda: 1.0e6)
    evid = tmp_path / "evidence.json"
    monkeypatch.setattr(_mod, "EVIDENCE", evid)
    monkeypatch.setattr(
        _mod,
        "_seam_pair_real_leg",
        lambda **kw: {
            "rows": [],
            "block": {
                "label": "SEAM-PAIR",
                "floor_probe": {"status": "NOT_CONVERGED"},
            },
            "stop": "FLOOR_NOT_CONVERGED",
        },
    )
    res = runner.invoke(_mod.app, ["seam-pair"])
    assert res.exit_code == 2
    assert "did NOT" in res.output
    stored = json.loads(evid.read_text())
    block = stored["phase14"]["stage1"]["seam_pair"]
    assert block["floor_probe"]["status"] == "NOT_CONVERGED"
    assert stored["phase14"]["stage1"].get("seam_rows", []) == []


def test_blend_on_the_strip_is_a_partition_of_unity_and_nan_safe() -> None:
    """The ORACLE's blended field: weights sum to 1, crossfade centred on 38N.

    Bug caught: (a) a blend that does not renormalize would dent the
    field across the strip, and the oracle would then measure the dent
    instead of the tiling; (b) the two tiles swapped in the assemble call
    would pull each tile's solution across the seam — at 36N (deep inside
    seam_s's core) the blended value must be seam_s's, not seam_n's;
    (c) a NaN outside a tile's support poisoning the sum. Expected values
    are geometric, not computed from the blend code: constant 1 blends to
    1 everywhere; a 0/1 pair reads 1 at 36N, 0.5 at the 38N boundary (by
    symmetry of the linear ramps) and 0 at 40N.
    """
    from sverdrup.application.spatial_tiles import assemble, frame_grid

    frames = [_mod.registry_frame(t) for t in _mod.SEAM_PAIR_TILES]
    grid = frame_grid(frames[0], _mod.RESOLUTION_DEG)
    lat_m, lon_m = _mod.strip_mask(grid, _mod.seam_strip_bbox())
    lon2d, lat2d = np.meshgrid(grid.x[lon_m], grid.y[lat_m])
    lon, lat = lon2d.ravel(), lat2d.ravel()

    unity = assemble(frames, [np.ones(lon.size), np.ones(lon.size)], lon, lat)
    assert np.allclose(unity, 1.0)

    south_only = assemble(frames, [np.zeros(lon.size), np.ones(lon.size)], lon, lat)
    at = {round(float(v), 1): south_only[lat == v] for v in np.unique(lat)}
    keys = sorted(at)
    assert at[keys[0]] == pytest.approx(1.0)  # 36N: seam_s alone
    assert at[keys[-1]] == pytest.approx(0.0)  # 40N: seam_n alone
    mid = at[round(0.5 * (keys[0] + keys[-1]), 1)]
    assert mid == pytest.approx(0.5)  # 38N: the shared core boundary

    poisoned = np.ones(lon.size)
    poisoned[lat == np.unique(lat)[0]] = np.nan  # NaN where seam_n has no weight
    blended = assemble(frames, [poisoned, np.ones(lon.size)], lon, lat)
    assert np.isfinite(blended[lat == np.unique(lat)[0]]).all()


# --- owner pin 45(b): mark a σ row NOT_ESTABLISHED by diagnosis ------------
# No seal is touched: the diagnosis is committed, dual-reviewed and CONFIRMED,
# and the firewall label already exists. Owner pin 47: the one-shot guard must
# survive deletion of its own witness.

_DIAGNOSIS_REF = "phase14.stage1.seam_sigma_diagnosis"


def _sigma_row_as_recorded(verdict: str = "ELEVATED") -> dict[str, Any]:
    """A σ row exactly as recorded under seal v1 (verbatim numbers)."""
    return {
        "route": "pair",
        "field_kind": "sigma",
        "rms_delta": 0.0036065320446369846,
        "d_int": 0.003265498166677423,
        "r_seam": 1.1044354829041465,
        "rubric_cell": verdict,
        "verdict": verdict,
        "attributable": True,
        "floor": {"attributable": True, "f_m": 9.539364309585352e-08},
        "seal_sha": "a17ea419" + "0" * 56,
    }


def test_not_established_marking_replaces_the_verdict_and_keeps_the_numbers() -> None:
    """The σ cell reads NOT_ESTABLISHED, citing the diagnosis; numbers stand.

    Owner pin 45(b): the committed, dual-reviewed, CONFIRMED diagnosis already
    establishes that this σ reading is an artifact of the shared basis origin,
    so the cell is marked under the EXISTING not-established firewall — no
    sealed instrument is amended to do it.

    Bug caught: a marking that rewrites the measurement (rms_delta, d_int,
    r_seam) or erases the pre-registered rubric_cell. The reading is the only
    record of this configuration and must survive its own re-labelling.
    """
    row = _mod.mark_not_established(
        row=_sigma_row_as_recorded(),
        diagnosis_ref=_DIAGNOSIS_REF,
        date="2026-07-27",
    )
    assert row["verdict"] == "NOT_ESTABLISHED (ensemble MC artifact — see diagnosis)"
    assert row["attributable"] is False
    assert row["rubric_cell"] == "ELEVATED"
    assert row["rms_delta"] == 0.0036065320446369846
    assert row["d_int"] == 0.003265498166677423
    assert row["r_seam"] == 1.1044354829041465
    block = row["not_established"]
    assert block["prior_verdict"] == "ELEVATED"
    assert block["diagnosis"] == _DIAGNOSIS_REF
    assert block["date"] == "2026-07-27"
    assert "no rubric verdict supports" in block["firewall"]


def test_not_established_marking_refuses_a_row_already_marked() -> None:
    """One marking per row — the ordinary double-run refusal.

    Bug caught: a re-run overwriting `prior_verdict` with the already-marked
    label, erasing the ELEVATED reading the diagnosis is about.
    """
    once = _mod.mark_not_established(
        row=_sigma_row_as_recorded(), diagnosis_ref=_DIAGNOSIS_REF, date="2026-07-27"
    )
    with pytest.raises(ValueError, match="already"):
        _mod.mark_not_established(
            row=once, diagnosis_ref=_DIAGNOSIS_REF, date="2026-07-28"
        )


def test_not_established_guard_survives_deletion_of_its_own_witness() -> None:
    """OWNER PIN 47, the demonstrated exploit: delete the block, retry, refuse.

    The predecessor guard keyed on the presence of the annotation block, so
    deleting that block — exactly what a manual reset does — let a second
    marking through and overwrote `prior_verdict` with the already-marked
    value. This guard keys on the VERDICT, which is the thing being
    protected and cannot be deleted without destroying the row.

    Bug caught: the regression of that exploit. A write-once surface
    defeated by deleting its own witness is not write-once, and a
    demonstrated exploit with no regression test is an invitation.
    """
    marked = _mod.mark_not_established(
        row=_sigma_row_as_recorded(), diagnosis_ref=_DIAGNOSIS_REF, date="2026-07-27"
    )
    stripped = {k: v for k, v in marked.items() if k != "not_established"}
    assert "not_established" not in stripped
    assert stripped["verdict"].startswith("NOT_ESTABLISHED")
    with pytest.raises(ValueError, match="verdict is already"):
        _mod.mark_not_established(
            row=stripped, diagnosis_ref=_DIAGNOSIS_REF, date="2026-07-28"
        )


def test_not_established_marking_refuses_a_non_rubric_prior_verdict() -> None:
    """The prior verdict must be one of the pre-registered cells.

    Bug caught: marking a row whose verdict is already an UNMEASURED_* or
    pending-owner label — those are withholdings, not readings, and
    relabelling them as a diagnosis-established artifact would assert
    something the diagnosis does not say.
    """
    withheld = _sigma_row_as_recorded()
    withheld["verdict"] = _mod.UNMEASURED_SOLVER_FLOOR
    with pytest.raises(ValueError, match="verdict is already"):
        _mod.mark_not_established(
            row=withheld, diagnosis_ref=_DIAGNOSIS_REF, date="2026-07-27"
        )


def test_not_established_marking_refuses_a_mean_row() -> None:
    """Only the σ route is marked — the diagnosis is about σ only.

    Bug caught: sweeping all four rows through the marking, which would
    retract the two mean CLEAN verdicts. They are the stage's only standing
    seam verdicts and the diagnosis says nothing against them.
    """
    mean_row = _sigma_row_as_recorded("CLEAN") | {"field_kind": "mean"}
    with pytest.raises(ValueError, match="sigma"):
        _mod.mark_not_established(
            row=mean_row, diagnosis_ref=_DIAGNOSIS_REF, date="2026-07-27"
        )


# ---------------------------------------------------------------------------
# Owner pin 90 (ruling doc PART 20) — T5 acceptance criterion 8 is DISCHARGED
# BY THE PIN-12 RULING. The criterion was written while the equatorial box
# election was open and asks the programmatic path to refuse while
# box_election_pending; the election closed 2026-07-25 (box KEPT) and no such
# state exists. These four tests are the discharge's evidence.
# ---------------------------------------------------------------------------

# The box the owner RULED on 2026-07-25 (pin 12: "box KEPT"), stated here from
# the ruling rather than read off the implementation. Order is BBox's:
# (lon_min, lon_max, lat_min, lat_max).
_PIN12_RULED_EQUATORIAL_BOX = (200.0, 215.0, -4.0, 11.0)


def test_equatorial_frame_is_the_pin12_ruled_box() -> None:
    """The equatorial frame IS the ruled -4..11N x 200..215E box (pin 90b).

    Bug caught: a later frame edit shifting the box to the REJECTED
    -2..13N option (or any other span). test_run_equatorial_reaches_
    gated_stub_after_pin12_ruling passes straight through such an edit --
    it only proves the pin-12 gate no longer refuses, never that the box
    which survived is the one the owner kept. Asserted through
    registry_frame so a frame-constructor bug is caught as well as a
    registry edit.
    """
    core = _mod.registry_frame("equatorial").core
    assert (core.lon_min, core.lon_max, core.lat_min, core.lat_max) == (
        _PIN12_RULED_EQUATORIAL_BOX
    )


def test_no_box_election_pending_state_exists() -> None:
    """No box_election_pending state exists anywhere (pin 90, pin 42).

    Bug caught: someone "restores" criterion 8 literally by adding a
    permanently-False box_election_pending flag and a refusal keyed to
    it. Pin 42 bars a gate that cannot fire, and that flag is exactly
    that object; the election closed 2026-07-25.
    """
    assert not [n for n in dir(_mod) if "box_election" in n.lower()]
    # The NAME may appear in prose (the discharge record describes the state
    # it refuses to create); what must not appear is the state itself -- an
    # assignment binding it, or a refusal branching on it.
    source = Path(str(_mod.__file__)).read_text()
    assert not re.search(r"^\s*box_election_pending\s*[:=]", source, re.MULTILINE)
    assert not re.search(r"\bif\s+.*\bbox_election_pending\b", source)


def test_criterion8_discharge_cites_live_tests() -> None:
    """Every test the discharge record cites actually exists (pin 90a).

    Bug caught: test_run_equatorial_reaches_gated_stub_after_pin12_ruling
    is renamed or deleted in a later refactor and the discharge record
    goes on claiming test-backed evidence while pointing at nothing. The
    owner's point is that a criterion discharged by a citation to a test
    that fails if the fact stops holding beats one discharged by prose --
    this test is what makes the citation load-bearing.
    """
    cited = _mod.CRITERION_8_DISCHARGE["evidence_tests"]
    assert cited, "the discharge must cite at least one test"
    here = globals()
    for name in cited:
        assert name in here, f"discharge cites {name!r}, which no longer exists"
        assert callable(here[name])


def test_criterion8_discharge_record_contract() -> None:
    """The record says DISCHARGED_BY_RULING and names both halves (pin 90d).

    Bug caught: the record is quietly upgraded to "met" once _solve_leg
    lands, erasing that the refusal half was never run -- the "check 3
    passed" failure three documents downstream that the anchor-gate split
    exists to prevent. Also catches the opposite erasure: dropping the
    live breadth half (90c) so nothing carries it to _solve_leg.
    """
    rec = _mod.CRITERION_8_DISCHARGE
    assert rec["status"] == "DISCHARGED_BY_RULING"
    assert rec["status"] not in {"met", "dropped", "PASS"}
    assert rec["dead_half"]
    assert "refus" in rec["dead_half"].lower()
    assert rec["live_half_deferred_to"] == "_solve_leg (T5b)"
    assert "record_evidence_row" in rec["live_half"]


def test_criterion8_live_half_is_discharged_on_the_real_path() -> None:
    """T5b landed the leg, so the breadth half names the test that covers it.

    Bug caught: _solve_leg lands and the discharge record still says the
    breadth half is DEFERRED -- the criterion would then be carried
    forward as open work forever, which is the mirror of the "quietly
    upgraded to met" failure the record contract already guards.
    """
    rec = _mod.CRITERION_8_DISCHARGE
    covered = rec["live_half_discharged_by"]
    assert covered == "test_record_tile_leg_records_equatorial_on_the_programmatic_path"
    assert covered in rec["evidence_tests"]  # so pin 90a's citation check binds it


# ---------------------------------------------------------------------------
# E-16 §1-§2 (ruling doc PART 19), ratified owner pin 92 — the TIER-2
# production launch gate. Task 22 cleared the crossing; these pin the shape
# the clearance actually authorised.
# ---------------------------------------------------------------------------


def test_tier2_launch_threshold_is_twice_the_MEASURED_peak() -> None:
    """Threshold = 2 x 4951.16 MiB, leg 2's DIRECT measurement (pin 155).

    Bug caught: wiring the gate to a predicted, a stale, or a PROJECTED
    peak. It has been all three. The model's 5154 over-predicts by 18%;
    pin 89's 4365 was ONE window taken as a leg peak, wrong by 1.69x once
    nine windows ran, leaving the gate asserting 2x while holding 1.18x;
    and pin 147(b)'s 4573 was THREE windows applied to nine, which held
    1.847x against what nine windows actually peaked at. The basis is now
    leg 2's nine-window production measurement with no projection left on
    the window-count axis. Hand-computed: 2 x 4951.1640625.
    """
    gate = _mod.tier2_launch_gate(mem_available_mib=99999.0)
    assert gate["threshold_mib"] == 9902.328125
    assert _mod.TIER2_MEASURED_PEAK_MIB == 4951.1640625


def test_tier2_superseded_bases_are_preserved_not_overwritten() -> None:
    """BOTH prior bases stay readable: 4365 and 4573 (pin 155).

    Bug caught: overwriting the superseded entry when re-pinning a second
    time, which silently drops 4365 and leaves a reader believing the
    basis has been corrected once rather than twice. A superseded basis a
    reader cannot see is a basis they cannot check -- and the 4365 -> 4573
    -> 4951 chain is the whole record of how the 1.18x survived two
    rounds. Pins the chain by value, not by length alone.
    """
    chain = _mod.TIER2_MEASURED_PEAK_SUPERSEDED
    assert [entry["prior_value_mib"] for entry in chain] == [4365.0, 4573.0]
    # The 4573 entry must name what unseated it: nine windows measured.
    assert "155" in chain[1]["superseded_by"]


def test_tier2_extrapolation_accuracy_is_recorded_as_method_evidence() -> None:
    """The 3->9 projection came in at 1.083x, and that is KEPT (pin 155).

    Bug caught: discarding the projection's accuracy once the direct
    measurement lands. Pin 155 keeps it deliberately -- it is evidence
    about the METHOD, for the next time a short run has to stand in for a
    long one. Dropping it leaves the next executor with no basis for
    trusting or distrusting a short-run stand-in. Hand-computed:
    4951.1640625 / 4573 = 1.0827.
    """
    span = _mod.TIER2_GATE_BASIS_SPAN["closed_by_leg2_pin_155"]
    assert span["n_windows_measured"] == 9
    assert span["measured_peak_mib"] == 4951.1640625
    assert round(span["extrapolation_accuracy_ratio"], 3) == 1.083
    assert span["projection_remaining"] is None


def test_tier2_launch_gate_boundary_admits_exactly_the_threshold() -> None:
    """>= at the threshold: 9902.33 launches, 9902.3 refuses.

    Bug caught: a strict > comparison, which refuses a leg at exactly the
    authorised headroom. On a box that cycles to ~11.2 GiB roughly every
    4 h, refusing at the boundary costs a whole cycle per occurrence.
    Also pins that BOTH superseded thresholds no longer admit: 8730 held
    1.909x and 9146 held 1.847x against the measured peak, and pin 155
    refuses "close enough" for the same reason pin 150(d) did.
    """
    assert _mod.tier2_launch_gate(mem_available_mib=9902.328125)["passed"] is True
    assert _mod.tier2_launch_gate(mem_available_mib=9902.3)["passed"] is False
    assert _mod.tier2_launch_gate(mem_available_mib=9146.0)["passed"] is False
    assert _mod.tier2_launch_gate(mem_available_mib=8730.0)["passed"] is False


def test_tier2_wall_ceiling_is_per_leg_not_per_stage() -> None:
    """A leg over 40 h STOPS; 124 h (the stage figure) is not the ceiling.

    Bug caught: applying E-16's ceiling to the STAGE (4 tiles ~ 124 h)
    instead of per leg. E-16 §1 is explicit -- "CEILING IS PER LEG:
    ~40 h per tile, NOT 124 h for the stage" -- and a stage-scoped ceiling
    lets a runaway first leg burn 3 extra days before anything trips.
    Values from E-16 §1: 31.0 h measured x 1.3 residual span.
    """
    assert _mod.TIER2_MAX_LEG_WALL_H == 40.0
    assert _mod.tier2_wall_ceiling(elapsed_h=40.1)["stop"] is True
    assert _mod.tier2_wall_ceiling(elapsed_h=39.9)["stop"] is False
    # The recorded block must say which scope it is, so a reader cannot
    # mistake it for the stage figure.
    assert "LEG" in _mod.tier2_wall_ceiling(elapsed_h=1.0)["scope"].upper()


# ---------------------------------------------------------------------------
# Owner pin 156 — the IN-RUN headroom watchdog. The launch gate is not what
# protects the leg: leg 2 cleared at 10,771 MiB and the box then shed 9,389
# MiB against a 4,951 MiB leg peak. A gate prevents starting into a bad box;
# it cannot prevent the box going bad.
# ---------------------------------------------------------------------------


def test_headroom_watchdog_holds_through_leg2s_healthy_band() -> None:
    """The band leg 2 ran in for 24 h must NOT trip the watchdog.

    Bug caught: a floor set high enough to be safe on paper and useless in
    practice. Leg 2 sat at 5,500-6,200 MiB for almost the whole run with
    swap already exhausted by a co-tenant; a watchdog that halts there
    halts every leg on this box forever and the four-tile roster never
    finishes. Values are leg 2's own trace, not invented.
    """
    for avail in (5526.0, 5896.0, 6165.0, 8016.0):
        block = _mod.headroom_watchdog(mem_available_mib=avail, proc_vm_swap_mib=0.0)
        assert block["stop"] is False, f"{avail} MiB is leg 2's healthy band"


def test_headroom_watchdog_halts_in_the_region_leg2_was_failing_in() -> None:
    """Below the floor it STOPS. Leg 2 bottomed at 1,382 with both clocks
    stalling ~10 min -- that is the region, and the floor sits above it.

    Bug caught: a floor set at or below the observed bottom, which only
    fires once the leg is already thrashing. By 1,382 MiB leg 2's
    heartbeat had gone from 5-minute to 11.75-minute cadence and its
    external sampler had skipped 10 minutes entirely; halting there is
    halting after the damage. Hand-computed: floor 2048 > 1526 (the
    1-minute sampler's true bottom) > 1382 (the 5-minute tracker's).
    """
    block = _mod.headroom_watchdog(mem_available_mib=1382.0, proc_vm_swap_mib=98.0)
    assert block["stop"] is True
    assert block["floor_mib"] == 2048.0
    assert "MEM_AVAILABLE_BELOW_FLOOR" in block["reason"]


def test_headroom_watchdog_keys_on_swap_onset_not_only_the_absolute_number() -> None:
    """The leg's OWN pages being evicted is a stop signal (pin 156a-i).

    Bug caught: watching MemAvailable alone. Owner pin 156(a)(i) is
    explicit that swap onset is a signal "as much as the absolute
    number" -- when the solve's own resident set starts going to disk the
    leg is already degrading, and on leg 2 that showed as VmSwap climbing
    to ~100 MiB while MemAvailable was still reading above the floor.
    """
    block = _mod.headroom_watchdog(mem_available_mib=2600.0, proc_vm_swap_mib=98.0)
    assert block["stop"] is True
    assert "SWAP_ONSET" in block["reason"]


def test_headroom_watchdog_ignores_swap_while_headroom_is_healthy() -> None:
    """Swap alone does not halt a leg on a box whose swap is a co-tenant's.

    Bug caught: keying on swap unconditionally. This box ran leg 2 with
    SwapFree at 0-2 MiB for hours while MemAvailable sat near 6 GiB and
    the leg was entirely healthy -- swap was exhausted by another tenant
    before leg 2 even launched. An unconditional swap trip halts on a
    condition that says nothing about this leg, so the signal is gated on
    headroom also being degraded.
    """
    block = _mod.headroom_watchdog(mem_available_mib=6000.0, proc_vm_swap_mib=98.0)
    assert block["stop"] is False


def test_headroom_floor_declares_the_trace_it_came_from() -> None:
    """The floor cites leg 2's numbers, per 156(a)(i) "not invented".

    Bug caught: a magic constant. Every RAM number in this project that
    was not traceable to a measurement has been wrong -- 5154 modelled,
    4365 one window, 4573 three windows -- and each cost a round to
    unwind. The floor must carry its derivation where it is defined.
    """
    basis = _mod.STAGE1_HEADROOM_FLOOR_BASIS
    assert basis["observed_bottom_mib"] == 1382.0
    assert basis["observed_bottom_sampler_mib"] == 1526.0
    assert basis["tile"] == "southern"
    assert str(basis["margin_over_observed_bottom"]).startswith("1.4")
    # The honest limit: VmSwap was read at two instants, not sampled.
    assert "not sampled" in basis["swap_observation_limit"]


def test_headroom_tracker_reconciles_the_two_samplers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The recorded minimum is the REAL one (pin 156c).

    Bug caught: the live one. Leg 2's in-run tracker sampled every 300 s
    and recorded 1,382 MiB while the external 1-minute sampler caught
    1,526 -- two clocks disagreeing about the same run, with the row
    carrying whichever happened to land on a dip. The tracker must sample
    at the external cadence so the two cannot diverge.
    """
    assert _mod.STAGE1_HEADROOM_SAMPLE_S == 60.0
    tracker = _mod.HeadroomTracker(10771.0)
    for mib in (6000.0, 1526.0, 5000.0):
        tracker.sample(mib)
    rec = tracker.record()
    assert rec["min_mem_available_mib"] == 1526.0
    assert rec["sample_interval_s"] == 60.0
    assert rec["reconciled_with"] == "the external 1-minute vmhwm sampler"


def test_headroom_halt_is_recorded_and_distinguishable(tmp_path: Path) -> None:
    """A halt is neither a completion nor a crash (pin 156a-ii).

    Bug caught: a clean stop that looks like either of the other two. A
    halt read as a completion produces a nine-window reading from six
    windows; a halt read as a crash sends someone diagnosing a fault that
    did not happen. The record must name itself, carry why it stopped and
    how far it got, and survive the process that wrote it -- the parked
    launcher reads it to decide whether to relaunch.
    """
    block = _mod.headroom_watchdog(mem_available_mib=1382.0, proc_vm_swap_mib=98.0)
    dest = tmp_path / "southern_headroom_halt.json"
    rec = _mod.record_headroom_halt(
        dest, tile="southern", watchdog=block, windows_done=6, window_id="w+00252.0+60"
    )
    assert rec["kind"] == "HEADROOM_HALT"
    assert rec["kind"] != "CONVERGED"
    assert rec["clean"] is True
    assert rec["windows_completed"] == 6
    assert rec["halted_after_window"] == "w+00252.0+60"
    assert rec["resume"] == "automatic — the window store carries the completed windows"
    assert json.loads(dest.read_text())["kind"] == "HEADROOM_HALT"


def test_headroom_halt_raises_only_at_a_window_boundary() -> None:
    """The stop is CLEAN because it lands where the window is on disk.

    Bug caught: stopping mid-solve. `on_window` fires AFTER `_save_window`
    in merged_members, so raising there costs nothing already solved --
    but a watchdog wired into the beat thread, or into the solver's
    iteration loop, would kill the window in flight and lose ~3 h. This
    pins the boundary contract by driving the real callback shape: a
    tripped watchdog raises, an untripped one returns None.
    """
    tripped = _mod.headroom_watchdog(mem_available_mib=1000.0, proc_vm_swap_mib=0.0)
    healthy = _mod.headroom_watchdog(mem_available_mib=8000.0, proc_vm_swap_mib=0.0)
    assert tripped["stop"] is True and healthy["stop"] is False

    halt = _mod.Stage1HeadroomHalt(tripped, "w+00252.0+60")
    assert halt.window_id == "w+00252.0+60"
    assert "MEM_AVAILABLE_BELOW_FLOOR" in str(halt)
    # It must be catchable as the specific halt, never swallowed as a
    # generic solver failure.
    assert isinstance(halt, RuntimeError)


def test_a_resumed_leg_says_so_in_its_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A leg that halted and resumed carries the halt in its row (156a-ii).

    Bug caught: silent recovery. A halted-then-resumed leg produces the
    same nine windows as a clean one, so its row is indistinguishable --
    but its wall_s spans a pause that was not solve time. Pricing legs 3
    and 4 from an unexplained wall is how the 31.0 h projection got its
    authority in the first place. Also pins that the block goes INSIDE
    `headroom`: the row's top-level key set is pinned exactly and pin
    156(d) forbids a schema change.
    """
    monkeypatch.setattr(_mod, "STAGE1_DIR", tmp_path)
    assert _mod._prior_halts_block("equatorial") == {}

    _mod.record_headroom_halt(
        tmp_path / "equatorial_headroom_halt.json",
        tile="equatorial",
        watchdog=_mod.headroom_watchdog(
            mem_available_mib=1382.0, proc_vm_swap_mib=98.0
        ),
        windows_done=4,
        window_id="w+00117.0+60",
    )
    block = _mod._prior_halts_block("equatorial")
    assert block["prior_headroom_halt"]["windows_completed"] == 4
    assert "not solve time" in block["wall_includes_a_halt"]


def test_the_launcher_script_cannot_drift_from_the_pinned_constants() -> None:
    """The shell launcher's gate and halt code track the Python ones.

    Bug caught: the live shape of every RAM defect in this project --
    a threshold in one place and its basis in another, drifting apart
    silently. The launcher duplicates two constants it cannot import, so
    a re-pin that updates Python and not the shell would park legs on the
    OLD gate while the row claims the new basis, and a changed halt code
    would make the launcher read a clean halt as a crash and refuse to
    relaunch (pin 156b), or read a crash as a halt and relaunch it blind.
    """
    launcher = (
        Path(__file__).resolve().parents[1] / "scripts/stage1_leg_launcher.sh"
    ).read_text()
    gate_m = re.search(r"^GATE=(\d+)", launcher, re.MULTILINE)
    halt_m = re.search(r"^HALT_EXIT=(\d+)", launcher, re.MULTILINE)
    assert gate_m is not None, "the launcher must define GATE"
    assert halt_m is not None, "the launcher must define HALT_EXIT"
    gate = int(gate_m.group(1))
    halt = int(halt_m.group(1))

    threshold = _mod.tier2_launch_gate(mem_available_mib=0.0)["threshold_mib"]
    # Integer shell arithmetic: the gate must never admit BELOW the real
    # threshold, so it rounds up rather than down.
    assert gate >= threshold
    assert gate < threshold + 1.0
    assert halt == _mod.STAGE1_HEADROOM_HALT_EXIT


def test_tier2_launch_gate_does_not_consult_the_tier1_predicate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Tier-2 gate never calls ladder.tier1_eligible.

    Bug caught: the live one. preflight raises RuntimeError on
    `not tier1_eligible(...)`, so a Tier-2-cleared leg refuses before it
    loads anything -- task 22's clearance would be inert. tier2_probe
    already set the precedent (it bypasses the predicate with a live
    headroom guard and says why); this pins that the production gate does
    the same rather than inheriting the Tier-1 refusal.
    """
    from sverdrup.application import ladder

    called = False

    def _spy(peak_mib: float, *a: object, **k: object) -> bool:
        nonlocal called
        called = True
        return False

    monkeypatch.setattr(ladder, "tier1_eligible", _spy)
    # Above the pin-155 threshold (9902.33), so `passed` isolates the
    # predicate question rather than the headroom one.
    gate = _mod.tier2_launch_gate(mem_available_mib=10500.0)
    assert gate["passed"] is True
    assert called is False


def test_preflight_tier1_refusal_still_bites_for_other_callers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """preflight keeps refusing on the Tier-1 predicate (seam_pair depends on it).

    Bug caught: "fixing" the Tier-2 problem by deleting the Tier-1 check
    from preflight, which silently disarms the launch guard for seam_pair
    and the anchor gate -- callers that were never Tier-2-cleared. The
    Tier-2 authorisation is T5-scoped; preflight is shared.
    """
    from sverdrup.application import ladder

    monkeypatch.setattr(ladder, "tier1_eligible", lambda peak_mib: False)
    with pytest.raises(RuntimeError, match="Tier-1"):
        _mod.preflight("seam_n", 100)


# ---------------------------------------------------------------------------
# Owner pin 133 — the leg store must be written WITHOUT re-materialising the
# windows the window store just released.
# ---------------------------------------------------------------------------


def test_leg_store_streams_and_matches_savez(tmp_path: Path) -> None:
    """Streamed leg store == np.savez output, one window resident at a time.

    Bug caught: writing the leg store with ``np.savez(**payload)`` over a
    released mapping, which pulls every window back into memory at the end
    of the leg and restores exactly the O(n_windows) peak pin 133 removes
    — while looking correct, because the file it produces is right.
    """
    import numpy as np

    from sverdrup.distributions.miost_ensemble import WindowBackedAnoms, _save_window

    store = tmp_path / "windows"
    ids = [f"w+{d:08.1f}+60" for d in (0.0, 45.0, 90.0)]
    rng = np.random.default_rng(3)
    eager_eta, eager_anom, starts = {}, {}, {}
    for i, wid in enumerate(ids):
        eta = rng.standard_normal(97)
        anom = rng.standard_normal((97, 4))
        eager_eta[wid], eager_anom[wid], starts[wid] = eta, anom, float(i * 45)
        _save_window(store, wid, eta=eta, anom=anom, start=float(i * 45), m=4, root=99)

    released = WindowBackedAnoms(store, ids, m=4, root=99)
    rows = [{"window": ids[0], "iterations": 7}]

    streamed = tmp_path / "streamed.npz"
    _mod._savez_leg_store(
        streamed,
        window_ids=ids,
        etas_a=eager_eta,
        anoms=released,
        starts=starts,
        pcg_rows=rows,
        wall_s=12.5,
        label="test leg store",
    )
    assert len(released.resident_window_ids()) <= 2, (
        "the writer materialised the whole mapping — the defect this pins"
    )

    reference = tmp_path / "savez.npz"
    np.savez(
        reference,
        **_mod._store_payload(
            eager_eta, eager_anom, starts, rows, 12.5, "test leg store"
        ),
    )
    with (
        np.load(streamed, allow_pickle=False) as a,
        np.load(reference, allow_pickle=False) as b,
    ):
        assert sorted(a.files) == sorted(b.files)
        for key in sorted(b.files):
            assert np.array_equal(a[key], b[key]), key
            assert a[key].dtype == b[key].dtype, key


def test_leg_store_stream_is_atomic(tmp_path: Path) -> None:
    """A crash inside the write leaves no half-file for a later leg to read.

    Bug caught: the pin-122 failure one level up — the leg store is the
    crash-resume substrate, so a truncated one is worse than none.
    """
    import numpy as np

    dest = tmp_path / "leg.npz"
    dest.write_bytes(b"previous good store")

    class _Boom(dict[str, "np.ndarray"]):
        def __getitem__(self, key: str) -> np.ndarray:
            raise RuntimeError("solve died mid-write")

    with pytest.raises(RuntimeError, match="died mid-write"):
        _mod._savez_leg_store(
            dest,
            window_ids=["w+00000.0+60"],
            etas_a={"w+00000.0+60": np.zeros(3)},
            anoms=_Boom(),
            starts={"w+00000.0+60": 0.0},
            pcg_rows=[],
            wall_s=1.0,
            label="x",
        )
    assert dest.read_bytes() == b"previous good store"
    assert not list(tmp_path.glob("*.tmp*")), "the temp file was left behind"


# ---------------------------------------------------------------------------
# Owner pin 143 — the CONSUMER declares the span of the measurement it cites.
# ---------------------------------------------------------------------------


def test_the_launch_gate_declares_its_basis_span() -> None:
    """The gate record states what was measured and where it is applied.

    Bug caught: pin 143's own subject — a one-window peak became the basis
    for a nine-window leg's gate, and no field name at the RECORDING site
    could catch it because the projection was made where the measurement
    was USED. A reader of the gate record must meet the span there, not
    three documents away.

    After pin 155 the window-count axis is CLOSED: measured_over and
    application_range agree at 9, so the span must no longer claim an
    extrapolation it is not making. The bug this now catches is the
    opposite one — leaving a stale "3 -> 9" declaration standing after the
    measurement landed, which tells a reader the basis is weaker than it
    is and invites re-litigating a closed axis.
    """
    gate = _mod.tier2_launch_gate(mem_available_mib=9000.0)
    span = gate["basis_span"]

    assert span["measured_over"]["n_windows"] == 9
    assert span["application_range"]["n_windows"] == 9
    assert isinstance(span["extrapolation_declared"], str)
    assert span["measured_outcome_2026_09_01"]["ratio_measured_over_projected"] > 1.6
    # The TILE axis is still open and must stay declared — measured on
    # kuroshio and southern, applied to equatorial and quiet_gyre.
    assert span["tile_axis_still_projected"].strip()


def test_every_declared_basis_span_states_VALUES_not_flags() -> None:
    """No consumer-side declaration satisfies itself with a boolean.

    Bug caught: pin 139(c) reappearing on the consumer side — an
    `extrapolation_declared: true` that passes a check while stating no
    span. All three subjects (RAM basis, wall ceiling, PCG cap) are held
    to the same rule.
    """
    from sverdrup.validation.gate_schema import projection_audit

    for span in (
        _mod.TIER2_GATE_BASIS_SPAN,
        _mod.TIER2_CEILING_BASIS_SPAN,
        _mod.STAGE1_PCG_MAXITER_BASIS_SPAN,
    ):
        assert isinstance(span["extrapolation_declared"], str)
        assert span["extrapolation_declared"].strip()
        assert span["measured_over"] and span["application_range"]
        assert projection_audit(span) == [], "a declaration must satisfy the audit"


# ---------------------------------------------------------------------------
# Owner pin 151 — a gate that admits one job and then another has not gated
# anything, and the headroom it measured must keep being measured.
# ---------------------------------------------------------------------------


def test_a_second_stage1_solve_is_REFUSED_while_the_lock_is_held(
    tmp_path: Path,
) -> None:
    """Two production-shaped solves cannot hold the box at once.

    Bug caught: pin 151's subject — 147(b) passed the launch gate and then
    shared the box with 147(a) for 34 minutes, because nothing prevented a
    second job from ARRIVING after the check. The gate measured the box,
    not the box's future.
    """
    lock = tmp_path / "solve.lock"
    with _mod.stage1_solve_lock("leg:kuroshio", path=lock) as held:
        assert held["pid"] == os.getpid()
        with pytest.raises(RuntimeError, match="already holds the Stage-1 solve lock"):
            with _mod.stage1_solve_lock("leg:southern", path=lock):
                pass
    assert not lock.exists(), "the lock is released when the run ends"


def test_a_STALE_lock_is_taken_over_and_the_takeover_is_recorded(
    tmp_path: Path,
) -> None:
    """A lock left by a dead process does not block the box forever.

    Bug caught: the mirror image of the defect — a leg killed by a power
    event leaves its lock behind, and a refusal that cannot distinguish a
    live holder from a corpse would stop every future leg. The takeover is
    RECORDED rather than silent, because a lock that vanishes without a
    trace teaches nothing.
    """
    lock = tmp_path / "solve.lock"
    lock.write_text(json.dumps({"pid": 2**22, "label": "leg:ghost", "started": "then"}))

    with _mod.stage1_solve_lock("leg:kuroshio", path=lock) as held:
        assert held["took_over_stale"]["label"] == "leg:ghost"
        assert held["pid"] == os.getpid()


def test_the_lock_is_released_even_when_the_leg_RAISES(tmp_path: Path) -> None:
    """A failed leg does not leave the box locked.

    Bug caught: a leg that dies inside the solve leaving a live-looking
    lock, so the next attempt refuses on a holder that is gone — turning
    one failure into a permanent one.
    """
    lock = tmp_path / "solve.lock"
    with (
        pytest.raises(ValueError, match="solve blew up"),
        _mod.stage1_solve_lock("leg:kuroshio", path=lock),
    ):
        raise ValueError("solve blew up")
    assert not lock.exists()


def test_headroom_is_sampled_DURING_the_run_not_only_at_launch() -> None:
    """The minimum MemAvailable seen during a leg is a recorded field.

    Bug caught: pin 151(b) — leg 1 bottomed at 3,660 MiB and we learned it
    afterward by reading a log. A launch-time reading says what the box
    had before the work started, which is the one moment it is guaranteed
    not to be under pressure.
    """
    tracker = _mod.HeadroomTracker(initial_mib=8000.0)
    tracker.sample(6100.0)
    tracker.sample(3660.0)
    tracker.sample(7200.0)

    block = tracker.record()
    assert block["min_mem_available_mib"] == 3660.0
    assert block["at_launch_mem_available_mib"] == 8000.0
    assert block["n_samples"] == 4


def test_the_recorded_row_CARRIES_the_headroom_block(tmp_path: Path) -> None:
    """A leg's row carries the minimum headroom it actually saw.

    Bug caught: the tracker existing but never reaching the row, so the
    in-run measurement lives in a log again — which is exactly how leg 1's
    3,660 MiB floor was learned after the fact rather than from the record
    (pin 151b).
    """
    tracker = _mod.HeadroomTracker(initial_mib=9200.0)
    tracker.sample(4100.0)

    row = _mod.build_evidence_row(
        **{k: v for k, v in _row_kwargs("kuroshio").items() if k != "scores"},
        scores=_mod.build_scores_block(**_SCORE_KWARGS),
        headroom=tracker.record(),
    )

    assert row["headroom"]["min_mem_available_mib"] == 4100.0
    assert row["headroom"]["at_launch_mem_available_mib"] == 9200.0
