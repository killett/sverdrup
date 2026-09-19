"""T6 — the high-latitude kernel DECISION pack (spec 1-4, owner pins 99a/108).

The pack is arithmetic plus an option table with an EMPTY decision cell. Two
things it must never do, and both are pinned here: present the coordinate-grid
aspect as measured directional sampling (owner pin 108 — the recorded 1.7179
is exactly 1/cos(54.4°), which perfectly isotropic sampling would also
produce), and let the ±66 threshold become a typed constant instead of an
expression over the ruled frame (review pin 16).
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from tests.helpers import load_script

_pack = load_script("phase14_kernel_pack")
runner = CliRunner()

# Hand values, computed from cos/sin tables independently of the module:
# f = 2*OMEGA*sin(phi) with OMEGA = 7.2921e-5 rad/s.
_COS = {33: 0.838671, 38.1: 0.786935, 43: 0.731354, 47: 0.681998, 54.4: 0.582123}
_ASPECT_62 = 2.130054  # 1/cos(62 deg)
_F_38_1N = 8.998975e-05
_F_55S = 1.1946677e-04
# The southern tile's recorded solve_bbox.lat_min, and the halo it admits.
_SO_LAT_MIN = -64.0
_SO_ASPECT_RECORDED = 1.7178500957106504  # S anisotropy_inputs.southern.2017


def _evidence(tmp_path: Path, *, with_so_row: bool = True) -> Path:
    """A store carrying the southern frame and (optionally) its T5 evidence row."""
    stage1: dict[str, Any] = {
        "tiles": {
            "southern": {
                "frame": {
                    "core": [215.0, 230.0, -62.0, -47.0],
                    "solve_bbox": [213.0, 232.0, _SO_LAT_MIN, -45.0],
                    "halo_deg": 1.0,
                    "overlap_deg": 2.0,
                }
            }
        }
    }
    if with_so_row:
        stage1["anisotropy_inputs"] = {
            "southern": {
                "2017": {
                    "grid_anisotropy": {
                        "aspect_dy_over_dx": _SO_ASPECT_RECORDED,
                        "phi0_deg": -54.399999999999864,
                        "dx_km": 12.960385807581197,
                        "dy_km": 22.264000000000316,
                    },
                    "spectral_fidelity": {
                        "metrics": {"spec_slope": -4.157496757622111},
                        "note": "the RING (isotropic) spectrum",
                    },
                    "per_direction_track_diagnostics": {
                        "status": "NOT AVAILABLE — RECORDED ABSENCE",
                        "missing_context": ["ORBIT_GEOMETRY"],
                    },
                }
            }
        }
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps({"phase14": {"stage1": stage1}}))
    return path


def test_the_cos_phi_arithmetic_matches_hand_values(tmp_path: Path) -> None:
    """The cos-φ table and the two spread figures the spec sentence names.

    Bug caught: a degrees/radians slip or a cos/sin swap. Either rescales
    the entire anisotropy argument while still producing a plausible
    table, and the sentence "~13% in-box becomes ~2-3x poleward" would be
    made numeric from the wrong numbers.
    """
    block = _pack.arithmetic(evidence_path=_evidence(tmp_path))

    for phi, expected in _COS.items():
        assert block["cos_phi"][str(phi)] == pytest.approx(expected, abs=5e-7)
    # "~13% in-box": cos falls 12.8% across the anchor core, 33N -> 43N.
    assert block["in_box_cos_decrease"] == pytest.approx(0.127961, abs=5e-7)
    # "~2-3x poleward": the aspect 1/cos reaches 2.13 at the SO core's pole edge.
    assert block["aspect"]["62"] == pytest.approx(_ASPECT_62, abs=5e-7)
    assert 2.0 <= block["aspect"]["62"] <= 3.0


def test_the_coriolis_row_matches_hand_values(tmp_path: Path) -> None:
    """|f| at the box, at 55S, and their ratio.

    Bug caught: cos for sin in the Coriolis expression — |f| would be
    MAXIMAL at the equator, the inverse of the physics the whole
    high-latitude question rests on, and the ratio would invert.
    """
    block = _pack.arithmetic(evidence_path=_evidence(tmp_path))

    assert block["abs_f"]["38.1"] == pytest.approx(_F_38_1N, rel=1e-6)
    assert block["abs_f"]["55"] == pytest.approx(_F_55S, rel=1e-6)
    assert block["f_ratio_55S_over_box"] == pytest.approx(1.32756, abs=5e-6)
    assert block["abs_f"]["55"] > block["abs_f"]["38.1"]


def test_the_measured_aspect_is_EXACTLY_one_over_cos_phi0(tmp_path: Path) -> None:
    """Owner pin 108: this identity is why the axis is UNEVIDENCED.

    Bug caught: the pack presenting the recorded 1.7179 as measured
    directional sampling. It is 1/cos(54.4 deg) — a coordinate-grid
    property that perfectly isotropic sampling would also produce — and
    the test asserts the coincidence to 1e-9 so the claim cannot be
    softened without this failing.
    """
    block = _pack.arithmetic(evidence_path=_evidence(tmp_path))
    recorded = block["measured_grid_aspect"]

    assert recorded["value"] == pytest.approx(_SO_ASPECT_RECORDED)
    assert recorded["one_over_cos_phi0"] == pytest.approx(
        1.0 / math.cos(math.radians(54.399999999999864)), abs=1e-12
    )
    assert abs(recorded["value"] - recorded["one_over_cos_phi0"]) < 1e-9
    assert recorded["is_a_coordinate_property"] is True


def test_the_breach_threshold_is_COMPUTED_from_the_frame_not_typed(
    tmp_path: Path,
) -> None:
    """Review pin 16 / owner pin 99(a): computed, never a constant.

    Bug caught: `2.0` typed into the pack. The branch collapse at 99(a)
    removed the dead "isolated" arithmetic and explicitly warned that
    collapsing must not turn the threshold into a constant — so a frame
    edit has to move the threshold, and here it does.
    """
    rows = _pack.breach_table(evidence_path=_evidence(tmp_path))

    assert rows["halo_breach_deg"] == pytest.approx(66.0 + _SO_LAT_MIN)
    assert rows["derivation"] == "66 + southern.frame.solve_bbox.lat_min"

    # Move the frame: the threshold must move with it.
    moved = tmp_path / "moved.json"
    doc = json.loads(_evidence(tmp_path).read_text())
    doc["phase14"]["stage1"]["tiles"]["southern"]["frame"]["solve_bbox"][2] = -60.0
    moved.write_text(json.dumps(doc))

    assert _pack.breach_table(evidence_path=moved)["halo_breach_deg"] == pytest.approx(
        6.0
    )


def test_a_breaching_halo_is_FLAGGED_and_a_clearing_one_is_not(
    tmp_path: Path,
) -> None:
    """The column exists to make one number impossible to miss.

    Bug caught: a breaching option rendered as an ordinary row. The
    nonstationary option breaches or clears depending only on where its
    multiplier is evaluated — at phi0 the margin is 0.28 deg, at the
    core's pole edge it is negative — so the flag is the difference
    between a decision and an accident.
    """
    rows = _pack.breach_table(evidence_path=_evidence(tmp_path))
    by_label = {r["label"]: r for r in rows["rows"]}
    km = next(r for label, r in by_label.items() if label.startswith("km-space"))
    hypothetical = next(
        r for label, r in by_label.items() if label.startswith("hypothetical")
    )

    # The km-space row spends margin but clears...
    assert km["halo_deg"] == pytest.approx(1.717850, abs=5e-7)
    assert km["so_obs_south_edge"] == pytest.approx(-65.717850, abs=5e-7)
    assert km["breach"] is False
    assert "BREACH" not in km["flag"]

    # ...and the only breaching row is the one the shipped code cannot express,
    # which is exactly why the row carries that column (finding F-2).
    assert hypothetical["halo_deg"] == pytest.approx(_ASPECT_62, abs=5e-7)
    assert hypothetical["so_obs_south_edge"] == pytest.approx(-66.130054, abs=5e-7)
    assert hypothetical["breach"] is True
    assert hypothetical["flag"] == "±66 BREACH — owner ruling required"
    assert hypothetical["expressible_with_shipped_code"].startswith("NO")
    assert all(
        r["expressible_with_shipped_code"].startswith("YES")
        for r in rows["rows"]
        if not r["breach"]
    )


def test_the_dead_isolated_branch_appears_nowhere(tmp_path: Path) -> None:
    """Owner pin 99(a): the branch is COLLAPSED, not carried as dead arithmetic.

    Bug caught: the "isolated" branch (edge = -(62 + halo), breach above
    halo 4.0) surviving in the rendered pack, where a reader could act on
    arithmetic the owner removed.
    """
    text = _pack.render(evidence_path=_evidence(tmp_path))

    # The dead arithmetic is the pair (breach above 4.0, edge = -(62 + halo)).
    assert "4.0" not in text
    assert "-(62" not in text and "62 + halo" not in text
    # The WORD may appear only in a sentence saying the branch was collapsed.
    for line in text.lower().splitlines():
        if "isolated" in line:
            assert "collaps" in line, f"'isolated' outside a collapse statement: {line}"
    # The live bound is the computed threshold, not a restated number.
    assert "halo ≤ 2° only — the bound IS the computed threshold" in text


def test_the_box_scale_negative_sentence_is_present(tmp_path: Path) -> None:
    """Standing discipline 7, and an explicit AC line.

    Bug caught: the sentence dropped. It is the only thing in the pack
    stopping the Phase-10 box-scale negative from being read as
    transferring to the tile scale this decision is about.
    """
    text = _pack.render(evidence_path=_evidence(tmp_path))

    assert "the box-scale negative (Phase 10) is NOT cited as transferring" in text


def test_the_axis_is_UNEVIDENCED_and_never_softened(tmp_path: Path) -> None:
    """Owner pin 108(a): UNEVIDENCED, not "limited" or "weakly supported".

    Bug caught: the softer word. "Limited" invites a reader to weigh the
    axis; the ruling is that it cannot be weighed at all, and any option
    whose case rests on directional sampling is marked UNSUPPORTED BY
    STAGE-1 EVIDENCE.
    """
    text = _pack.render(evidence_path=_evidence(tmp_path))
    lowered = text.lower()

    assert "UNEVIDENCED" in text
    assert "UNSUPPORTED BY STAGE-1 EVIDENCE" in text
    assert "weakly supported" not in lowered
    # Pin 108(a) names the bare word — "do not weaken it to 'limited'" — so the
    # pack must carry the NEGATION and must not use the word any other way.
    assert 'not "limited"' in text
    assert lowered.count("limited") == 1
    # 108(b): the decision may not be made on this axis.
    assert "may not be made on this axis" in lowered
    # 108(c): the propagation, named at its single point of change.
    assert "operative_halo_deg" in text


def test_every_option_carries_every_required_column(tmp_path: Path) -> None:
    """Three options, four columns each, none empty.

    Bug caught: an option shipped with a blank cell — the way a decision
    pack becomes unreadable at the gate, and the way an option gets
    chosen because its row looked simpler.
    """
    block = _pack.options(evidence_path=_evidence(tmp_path))

    assert len(block) == 3
    for option in block:
        for column in (
            "what_changes",
            "what_stays_identical",
            "halo_consequence",
            "cost_class",
            "anchor_identity",
        ):
            assert len(option[column].split()) >= 8, (
                f"{option['name']}: {column} is empty or a stub"
            )
        assert isinstance(option["rests_on_directional_sampling"], bool)


def test_the_decision_cell_is_EMPTY_and_no_option_is_recommended(
    tmp_path: Path,
) -> None:
    """The decision is the owner's at Gate 1; the pack prices, never picks.

    Bug caught: a recommendation reaching the pack — by a "preferred"
    column, or by prose. T6 assembles and STOPs.
    """
    text = _pack.render(evidence_path=_evidence(tmp_path))
    block = _pack.build_block(evidence_path=_evidence(tmp_path))

    assert block["decision"] is None
    assert block["decided_by"] == "owner, at Gate 1"
    for word in ("recommend", "preferred", "we suggest", "best option"):
        assert word not in text.lower(), word


def test_it_REFUSES_without_the_SO_evidence_row(tmp_path: Path) -> None:
    """No measurement, no pack.

    Bug caught: rendering the kernel pack from arithmetic alone on a host
    where T5's diagnostics never ran — the table would look complete
    while resting on nothing measured at all.
    """
    with pytest.raises(RuntimeError, match="anisotropy_inputs"):
        _pack.render(evidence_path=_evidence(tmp_path, with_so_row=False))


def test_the_command_prints_the_section_and_records_nothing_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Printing is safe; writing evidence is opt-in.

    Bug caught: the command writing `phase14.stage1.kernel_pack` on every
    invocation, so a dry read of the pack mutates the store.
    """
    evid = _evidence(tmp_path)
    monkeypatch.setattr(_pack, "EVIDENCE", evid)
    before = evid.read_text()

    result = runner.invoke(_pack.app, [])

    assert result.exit_code == 0, result.output
    assert result.output == _pack.render(evidence_path=evid)
    assert evid.read_text() == before


def test_the_directional_sampling_FLAG_actually_drives_the_render(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Owner pin 108(a): the marking must be wired, not decorative.

    Bug caught: the live one, found by review. The render hardcoded "no",
    so an option flagged `rests_on_directional_sampling: True` still
    printed that it was not marked UNSUPPORTED BY STAGE-1 EVIDENCE. That
    is §7 discipline 11 instance (i8)'s mechanism — a field nothing reads
    — and here it read nothing at all.
    """
    evid = _evidence(tmp_path)
    assert "UNSUPPORTED BY STAGE-1 EVIDENCE** (owner pin 108a)" not in _pack.render(
        evidence_path=evid
    )

    real = _pack.options

    def _flagged(evidence_path: Path = evid) -> list[dict[str, Any]]:
        opts = real(evidence_path=evidence_path)
        opts[0]["rests_on_directional_sampling"] = True
        return opts

    monkeypatch.setattr(_pack, "options", _flagged)

    assert (
        "**YES — UNSUPPORTED BY STAGE-1 EVIDENCE** (owner pin 108a)."
        in _pack.render(evidence_path=evid)
    )


def test_the_shipped_latitude_field_is_CONSTANT_over_the_southern_tile() -> None:
    """Finding F-2, pinned against the real shipped field.

    Bug caught: the pack pricing a 1/cos-φ multiplier as though the
    vehicle could deliver it. `LatitudeField.at` clamps to the anchor-box
    hull [33, 43], so over the SO core the multiplier is a single
    constant — the vehicle for latitude variation cannot vary at the
    latitudes this decision is about.
    """
    import numpy as np

    from sverdrup.core.parameters import LatitudeField

    field = LatitudeField("exp-linear-mult", (1.0,))
    so = field.at(np.linspace(-62.0, -47.0, 7))

    assert np.allclose(so, so[0]), "the SO multiplier must be constant (hull clamp)"
    # ...and it is the hull edge's value, not the tile's own latitude's.
    assert so[0] == pytest.approx(float(field.at(np.array([_pack.LAT_HULL[0]]))[0]))
    # Kuroshio overlaps the hull, so it DOES vary there — the clamp is the cause.
    kuroshio = field.at(np.linspace(28.0, 43.0, 7))
    assert not np.allclose(kuroshio, kuroshio[0])


def test_the_two_degree_space_options_are_ONE_dispatch() -> None:
    """Finding F-1, pinned against the real factory.

    Bug caught: pricing "lat-varying degree scales" and "Paciorek" as
    separate options with different cost classes when electing either
    elects the same kernel class — the shape that makes an option get
    chosen because its row looked simpler.
    """
    from sverdrup.core.parameters import LatitudeField, LatitudeVaryingProvider
    from sverdrup.methods.kernel import PaciorekGaussianDegrees
    from sverdrup.validation.run import gaussian_kernel_from_params

    core = {"variance": 1.0, "lx_deg": 1.0, "time_scale": 7.0}
    for varied in (
        {"lx_mult": LatitudeField("exp-linear-mult", (0.3,))},
        {"variance": LatitudeField("exp-quad", (0.0, 0.1, 0.0))},
    ):
        kernel = gaussian_kernel_from_params(
            LatitudeVaryingProvider(core=core, varied=varied), None
        )
        assert isinstance(kernel, PaciorekGaussianDegrees)


def test_the_edge_expression_matches_the_REAL_obs_frame(tmp_path: Path) -> None:
    """The pack's edge must be what `obs_bbox()` actually produces.

    Bug caught: the pack deriving its ±66 edge from the nominal solve
    bbox while the obs framing derives from the grid NODE extent, which
    `np.arange` can overshoot (the recorded 43.2°N quirk). At the
    poleward (min) end of a southern tile the two coincide by
    construction — this test is what proves that rather than assuming it.
    """
    from sverdrup.adapters.altimetry import BBox
    from sverdrup.application.spatial_tiles import TileFrame

    frame_row = json.loads(_evidence(tmp_path).read_text())["phase14"]["stage1"][
        "tiles"
    ]["southern"]["frame"]
    core = frame_row["core"]
    frame = TileFrame(
        core=BBox(lon_min=core[0], lon_max=core[1], lat_min=core[2], lat_max=core[3]),
        overlap_deg=frame_row["overlap_deg"],
        halo_deg=frame_row["halo_deg"],
    )
    real = frame.obs_bbox(resolution_deg=0.2)
    pack_edge = float(frame_row["solve_bbox"][2]) - float(frame_row["halo_deg"])

    assert real.lat_min == pytest.approx(pack_edge, abs=1e-9)


def test_record_writes_the_evidence_block(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The AC's other half: a markdown section AND an evidence block.

    Bug caught: `--record` shipped untested, so the half of the output
    the AC names as an evidence block could have been broken (or absent)
    without anything saying so.
    """
    from sverdrup.validation import phase14_seal

    monkeypatch.setattr(phase14_seal, "verify_current_seal", lambda: None)
    evid = _evidence(tmp_path)
    monkeypatch.setattr(_pack, "EVIDENCE", evid)

    result = runner.invoke(_pack.app, ["--record"])

    assert result.exit_code == 0, result.output
    block = json.loads(evid.read_text())["phase14"]["stage1"][_pack.KERNEL_PACK_NODE]
    assert block["decision"] is None
    assert block["label"] == "STAGE1-EVIDENCE"
    assert len(block["options"]) == 3
    assert [f["id"] for f in block["code_findings"]] == ["F-1", "F-2", "F-3"]
    assert block["breach_table"]["halo_breach_deg"] == pytest.approx(2.0)
