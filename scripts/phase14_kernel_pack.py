"""T6 — the high-latitude kernel DECISION pack (spec 1-4).

Assembles the owner's Gate-1 kernel decision material: the f-range and cos-φ
arithmetic, the Southern-Ocean tile's recorded anisotropy inputs beside it,
the three options with their halo and ±66 consequences — and an **EMPTY
decision cell**. T6 assembles and STOPs; the election is the owner's.

Two disciplines are structural here rather than editorial:

**Owner pin 108 — the anisotropy axis is UNEVIDENCED.** The recorded grid
aspect at the SO tile (1.7179) is *exactly* ``1/cos(54.4°)``: a coordinate
property that perfectly isotropic sampling would also produce. The ring
spectrum is isotropic by construction. Neither can speak to directional
sampling, and per-direction track diagnostics need the orbit-geometry
provider, which is challenge-box scoped (pin 106). So the axis is marked
**UNEVIDENCED** — never "limited", which would invite a reader to weigh it —
any option whose case rests on directional sampling is marked **UNSUPPORTED
BY STAGE-1 EVIDENCE**, and **the decision may not be made on this axis**: an
option set that cannot be separated without it is a **WAIT to the owner**.

**Review pin 16 / owner pin 99(a) — the ±66 arithmetic is COMPUTED.** The
breach threshold is ``66 + southern.frame.solve_bbox.lat_min`` read off the
ruled frame, never a typed constant, and the "isolated" branch pin 99(a)
collapsed is absent rather than carried as dead arithmetic.

Usage::

    pixi run python scripts/phase14_kernel_pack.py            # print
    pixi run python scripts/phase14_kernel_pack.py --record   # + evidence block
"""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer

EVIDENCE = Path("data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json")
KERNEL_PACK_NODE = "kernel_pack"
ERA = "2017"

# Earth's rotation rate [rad/s] — f = 2 Ω sin φ.
OMEGA = 7.2921e-5
# The anchor box's core latitudes and its φ0, and the SO tile's core edges.
BOX_LAT_MIN, BOX_LAT_MAX, BOX_PHI0 = 33.0, 43.0, 38.1
# The SO core edges are READ from the ruled frame (review pin 16) — see
# `_so_core_edges`. These names are the fallback for a frame that omits `core`.
SO_CORE_EQUATORWARD, SO_CORE_POLEWARD = 47.0, 62.0
# The shipped latitude-varying vehicle's hull: `LatitudeField.at` clamps to
# [33, 43] (core.parameters._LAT_HULL) — the ANCHOR BOX. Off-hull the field is
# a constant, which is the whole of every diverse tile except kuroshio.
LAT_HULL = (33.0, 43.0)
# The shipped scale: Lx = Ly = 1.0° (validation.params.SPATIAL_CORR_DEG), whose
# km analog is 1.0 × 111.195. The operative halo is 1.0° today
# (application.spatial_tiles.operative_halo_deg).
SHIPPED_SCALE_DEG = 1.0
KM_PER_DEG = 111.195
LAT_BREACH_ABS = 66.0

BOX_SCALE_SENTENCE = (
    "**the box-scale negative (Phase 10) is NOT cited as transferring** to the "
    "tile scale this decision is about (standing discipline 7)"
)

app = typer.Typer(add_completion=False, help=__doc__)


def _stage1(evidence_path: Path) -> dict[str, Any]:
    """The ``phase14.stage1`` node.

    Args:
        evidence_path: The evidence store.

    Returns:
        The node.
    """
    doc = json.loads(evidence_path.read_text())
    stage1: dict[str, Any] = doc["phase14"]["stage1"]
    return stage1


def _so_inputs(evidence_path: Path) -> dict[str, Any]:
    """The SO tile's recorded anisotropy inputs — or a refusal.

    Args:
        evidence_path: The evidence store.

    Returns:
        ``anisotropy_inputs.southern.<era>``.

    Raises:
        RuntimeError: The row is absent. The pack is arithmetic PLUS a
            measurement; without the measurement the table would look
            complete while resting on nothing measured.
    """
    row = _stage1(evidence_path).get("anisotropy_inputs", {}).get("southern", {})
    block: dict[str, Any] | None = row.get(ERA)
    if block and "grid_anisotropy" not in block:
        raise RuntimeError(
            "REFUSING to render the kernel pack: "
            f"anisotropy_inputs.southern.{ERA} carries no `grid_anisotropy` — the "
            "measured block is present but not the measurement."
        )
    if not block:
        raise RuntimeError(
            "REFUSING to render the kernel pack: "
            f"phase14.stage1.anisotropy_inputs.southern.{ERA} is absent. The pack "
            "presents measured SO inputs beside the arithmetic (T6 AC); without "
            "them the option table would rest on arithmetic alone."
        )
    return block


def _southern_frame(evidence_path: Path) -> dict[str, Any]:
    """The southern tile's ruled frame.

    Args:
        evidence_path: The evidence store.

    Returns:
        ``tiles.southern.frame``.
    """
    tiles = _stage1(evidence_path).get("tiles", {})
    frame: dict[str, Any] | None = tiles.get("southern", {}).get("frame")
    if not frame or "solve_bbox" not in frame:
        raise RuntimeError(
            "REFUSING to render the kernel pack: the ruled southern frame "
            "(phase14.stage1.tiles.southern.frame.solve_bbox) is absent. The ±66 "
            "column derives from it (review pin 16); without it the arithmetic "
            "would have to be typed, which is the defect the column exists against."
        )
    return frame


def _so_core_edges(evidence_path: Path = EVIDENCE) -> tuple[float, float]:
    """The SO core's equatorward and poleward |latitudes|, READ from the frame.

    Review pin 16: the arithmetic derives from the ruled frame rather than
    from typed latitudes, so moving the tile moves the table with it.

    Args:
        evidence_path: The evidence store.

    Returns:
        ``(|equatorward|, |poleward|)`` in degrees.
    """
    core = _southern_frame(evidence_path).get("core")
    if not core:
        return SO_CORE_EQUATORWARD, SO_CORE_POLEWARD
    lats = (abs(float(core[2])), abs(float(core[3])))
    return min(lats), max(lats)


def _abs_f(phi_deg: float) -> float:
    """``|f| = 2 Ω sin|φ|`` [s⁻¹].

    Args:
        phi_deg: Latitude [degrees].

    Returns:
        The Coriolis parameter's magnitude.
    """
    return 2.0 * OMEGA * math.sin(math.radians(abs(phi_deg)))


def _aspect(phi_deg: float) -> float:
    """``1/cos|φ|`` — the coordinate-grid aspect at that latitude.

    Args:
        phi_deg: Latitude [degrees].

    Returns:
        The aspect ratio.
    """
    return 1.0 / math.cos(math.radians(abs(phi_deg)))


def arithmetic(evidence_path: Path = EVIDENCE) -> dict[str, Any]:
    """The f-range and cos-φ arithmetic, with the recorded SO aspect beside it.

    Args:
        evidence_path: The evidence store.

    Returns:
        The arithmetic block.
    """
    so = _so_inputs(evidence_path)
    grid = so["grid_anisotropy"]
    phi0 = float(grid["phi0_deg"])
    lats = [BOX_LAT_MIN, BOX_PHI0, BOX_LAT_MAX, SO_CORE_EQUATORWARD, abs(phi0)]
    return {
        "cos_phi": {f"{lat:g}": math.cos(math.radians(lat)) for lat in lats},
        "aspect": {
            f"{lat:g}": _aspect(lat)
            for lat in (BOX_PHI0, SO_CORE_EQUATORWARD, abs(phi0), SO_CORE_POLEWARD)
        },
        "in_box_cos_decrease": 1.0
        - math.cos(math.radians(BOX_LAT_MAX)) / math.cos(math.radians(BOX_LAT_MIN)),
        "so_within_tile_cos_decrease": 1.0
        - math.cos(math.radians(SO_CORE_POLEWARD))
        / math.cos(math.radians(SO_CORE_EQUATORWARD)),
        "abs_f": {
            "38.1": _abs_f(BOX_PHI0),
            "55": _abs_f(55.0),
            "66": _abs_f(LAT_BREACH_ABS),
            "pole": 2.0 * OMEGA,
        },
        "f_ratio_55S_over_box": _abs_f(55.0) / _abs_f(BOX_PHI0),
        "measured_grid_aspect": {
            "value": float(grid["aspect_dy_over_dx"]),
            "phi0_deg": phi0,
            "one_over_cos_phi0": _aspect(phi0),
            "is_a_coordinate_property": True,
            "pin_108": (
                "the recorded aspect IS 1/cos(phi0) — a coordinate-grid property "
                "that perfectly isotropic sampling would also produce. It is NOT "
                "measured directional sampling"
            ),
            "cited_from": f"phase14.stage1.anisotropy_inputs.southern.{ERA}",
        },
        "isotropic_row": {
            "spec_slope": so["spectral_fidelity"]["metrics"]["spec_slope"],
            "note": "the RING spectrum — isotropic BY CONSTRUCTION (pin 108)",
        },
        "per_direction_sampling": so["per_direction_track_diagnostics"]["status"],
    }


def code_findings() -> list[dict[str, Any]]:
    """What the SHIPPED code can and cannot express — verified, not assumed.

    Both findings came out of T6's two-reviewer adversarial review (owner pin
    212b) and were then confirmed by direct execution. Each changes what
    electing an option MEANS, so they sit ahead of the option table rather
    than under it.

    Returns:
        One dict per finding.
    """
    return [
        {
            "id": "F-1",
            "headline": (
                "options 2 and 3 are the SAME shipped code path — the option set "
                "is two, not three"
            ),
            "evidence": (
                "`gaussian_kernel_from_params` (src/sverdrup/validation/run.py:41) "
                "dispatches ON TYPE: a LatitudeField in EITHER `variance` or "
                "`lx_mult` routes `PaciorekGaussianDegrees`; only all-scalar "
                "resolution builds the stationary kernel. Confirmed live — both a "
                "varied `lx_mult` and a varied `variance` return "
                "PaciorekGaussianDegrees. Pinned already at "
                "tests/test_oi_dispatch.py:47-77 and test_phase10_lanes.py:89-99"
            ),
            "consequence": (
                'electing "latitude-varying degree scales" IS electing the '
                "Paciorek kernel, with its Paciorek–Schervish prefactor and its PD "
                "argument. They cannot carry different cost classes, and a reader "
                "choosing 2 over 3 because its row looked simpler would be choosing "
                "the same thing"
            ),
        },
        {
            "id": "F-2",
            "headline": (
                "the shipped latitude-varying vehicle is CONSTANT over the tile "
                "this decision is about"
            ),
            "evidence": (
                "`LatitudeField.at` clamps latitude to the anchor-box hull "
                f"[{LAT_HULL[0]:g}, {LAT_HULL[1]:g}] before evaluating "
                "(src/sverdrup/core/parameters.py:17, 53 — constant continuation "
                "off-box, the PolyCalibration convention). Measured over each "
                "diverse tile's core: constant at southern, equatorial and "
                "quiet_gyre; varying only at kuroshio, which overlaps the hull"
            ),
            "consequence": (
                "at the SO tile the multiplier m(lat) is a single number — the "
                "field's value at the hull's southern edge — so the shipped vehicle "
                "delivers NO latitude variation where the high-latitude decision "
                "needs it. A 1/cos φ multiplier is not expressible: widening the "
                "hull changes a shipped, signed component, which is an owner "
                "question and a new-producer question, not a T6 decision"
            ),
        },
        {
            "id": "F-3",
            "headline": "the obs halo is a single SCALAR, applied to both axes",
            "evidence": (
                "`TileFrame.halo_deg: float` and `obs_bbox` apply the same value to "
                "lon and lat (src/sverdrup/application/spatial_tiles.py:62, 101-104); "
                "`operative_halo_deg() -> float` (:41-48). There is no per-axis halo "
                "anywhere in the tree"
            ),
            "consequence": (
                "no option can widen its ZONAL footprint while leaving the "
                "MERIDIONAL halo alone: the scalar halo must cover the wider axis, "
                "so any zonal widening moves the SO obs south edge and eats ±66 "
                "margin. Every halo row below is computed that way"
            ),
        },
    ]


def breach_table(evidence_path: Path = EVIDENCE) -> dict[str, Any]:
    """The ±66 column: operative halo → SO obs south edge → breach, computed.

    Every quantity derives from the ruled frame (review pin 16): the threshold
    is ``66 + solve_bbox.lat_min``, the edge is ``solve_bbox.lat_min - halo``,
    and the live-branch bound is the threshold itself rather than a restated
    number. Pin 99(a) collapsed the "isolated" branch, which is absent rather
    than carried as dead arithmetic.

    Each row says whether the shipped code can EXPRESS the halo it prices
    (finding F-2): a row that cannot be expressed is arithmetic about a
    hypothetical form, and is labelled as one rather than read as a property
    of an option.

    Args:
        evidence_path: The evidence store.

    Returns:
        The threshold, its derivations, and one row per candidate halo.
    """
    frame = _southern_frame(evidence_path)
    lat_min = float(frame["solve_bbox"][2])
    halo_breach = LAT_BREACH_ABS + lat_min
    phi0 = float(_so_inputs(evidence_path)["grid_anisotropy"]["phi0_deg"])
    _, poleward = _so_core_edges(evidence_path)

    candidates = [
        (
            "current constant halo (operative_halo_deg)",
            float(frame["halo_deg"]),
            "YES — this is the shipped value",
        ),
        (
            "km-space kernel: scalar halo must cover the ZONAL footprint "
            "(1/cos φ0) of an isotropic-in-km scale",
            _aspect(phi0),
            "YES — but only via a change to operative_halo_deg (fork-d pin 4); "
            "the kernel itself is shipped",
        ),
        (
            "degree-space nonstationary, SHIPPED field at the SO tile "
            "(m is hull-clamped, hence constant)",
            SHIPPED_SCALE_DEG,
            "YES at m = 1 (l1 = 0). Any other l1 scales this row by a CONSTANT "
            "over the whole tile — see finding F-2",
        ),
        (
            f"hypothetical 1/cos φ multiplier at the core's pole edge ({poleward:g}°)",
            _aspect(poleward),
            "NO — NOT EXPRESSIBLE with the shipped LatitudeField (F-2). Priced "
            "because the ±66 column asks for it, not because an option offers it",
        ),
    ]
    rows = []
    for label, halo, expressible in candidates:
        edge = lat_min - halo
        breach = halo > halo_breach
        rows.append(
            {
                "label": label,
                "halo_deg": halo,
                "so_obs_south_edge": edge,
                "margin_deg": LAT_BREACH_ABS - abs(edge),
                "breach": breach,
                "expressible_with_shipped_code": expressible,
                "flag": "±66 BREACH — owner ruling required" if breach else "clear",
            }
        )
    return {
        "halo_breach_deg": halo_breach,
        "derivation": "66 + southern.frame.solve_bbox.lat_min",
        "edge_derivation": "southern.frame.solve_bbox.lat_min − halo",
        "live_branch": (
            f"halo ≤ {halo_breach:g}° only — the bound IS the computed threshold "
            "above (owner pin 99a collapsed the 'isolated' branch; pin 2 ruled the "
            "frame production-representative 2026-07-25). Rows beyond it are "
            "priced and flagged, not in scope"
        ),
        "boundary_convention": (
            f"breach is STRICT: halo == {halo_breach:g}° puts the obs edge at "
            f"exactly ∓{LAT_BREACH_ABS:g}° and is recorded clear"
        ),
        "rows": rows,
    }


def options(evidence_path: Path = EVIDENCE) -> list[dict[str, Any]]:
    """The options as the plan names them, each column filled and corrected.

    The plan's AC names three. Finding F-1 is that the second and third are
    one shipped code path; they are kept under the AC's names and the shared
    dispatch is stated in both rows rather than the set being silently
    renumbered.

    Args:
        evidence_path: The evidence store.

    Returns:
        One dict per option.
    """
    phi0 = float(_so_inputs(evidence_path)["grid_anisotropy"]["phi0_deg"])
    zonal = _aspect(phi0)
    shared_path = (
        "⛔ SAME CODE PATH AS THE OTHER DEGREE-SPACE OPTION (finding F-1): any "
        "LatitudeField in `variance` or `lx_mult` dispatches "
        "`PaciorekGaussianDegrees` (validation/run.py:41). Electing either "
        "elects this kernel"
    )
    scalar_halo = (
        "the obs halo is a SINGLE SCALAR (finding F-3), so it must cover the "
        "wider axis: "
    )
    return [
        {
            "name": "1 — km-space kernels",
            "code": "sverdrup.methods.kernel.Matern32SpaceTime (exists; ONE km "
            "length_scale, cos-lat corrected separation — isotropic in km)",
            "what_changes": (
                "the distance metric becomes physical: separation in km with a "
                "cos-lat zonal correction, so one scale means the same distance at "
                "every latitude. Parameters move from degrees to km "
                f"({SHIPPED_SCALE_DEG:g}° ≈ {SHIPPED_SCALE_DEG * KM_PER_DEG:.3f} km)"
            ),
            "what_stays_identical": (
                "the solver, the windowing, the blend and the evidence-row schema. "
                "⚠ NOT the obs framing: see the halo row"
            ),
            "anchor_identity": (
                "NOT preserved by construction — a different kernel family AND a "
                "different metric from the shipped GaussianSpaceTimeDegrees, so the "
                "anchor solve changes and check 1's bit-identity against the "
                "phase-13 winner would have to be re-established"
            ),
            "halo_consequence": (
                f"{scalar_halo}an isotropic-in-km scale has a degree footprint of "
                f"{SHIPPED_SCALE_DEG:g}° meridional × {zonal:.4f}° zonal at the SO "
                f"φ0, so the operative halo is {zonal:.4f}°, the SO obs south edge "
                f"moves and the ±66 margin falls from "
                f"{LAT_BREACH_ABS - abs(-64.0 - SHIPPED_SCALE_DEG):.4f}° to "
                f"{LAT_BREACH_ABS - abs(-64.0 - zonal):.4f}°. An earlier draft of "
                "this row claimed the meridional halo was unaffected; F-3 refutes "
                "that — there is no per-axis halo to hold fixed"
            ),
            "cost_class": "MEDIUM — the class exists and is tested; the cost is "
            "re-establishing anchor identity, re-tuning scales in km, and a change "
            "to operative_halo_deg",
            "rests_on_directional_sampling": False,
        },
        {
            "name": "2 — latitude-varying degree scales",
            "code": "sverdrup.core.parameters.LatitudeVaryingProvider + LatitudeField "
            f"→ dispatches PaciorekGaussianDegrees. {shared_path}",
            "what_changes": (
                "the scale becomes L(lat) = L0·exp(l1·v) — ONE multiplier shared by "
                "lx and ly (there is no independent ly; a field-valued base is "
                "refused outright), so the kernel stays 1:1 in degrees and only its "
                "SIZE varies"
            ),
            "what_stays_identical": (
                "the solver and the blend. ⛔ NOT the kernel family or its PD "
                "argument — the dispatch routes Paciorek, whose PD rests on the "
                "Paciorek–Schervish prefactor"
            ),
            "anchor_identity": (
                "preserved in the constant limit, but the condition is NARROWER "
                "than 'constant scales': bit-identity holds at L0 = 1 AND variance "
                "= 1 exactly. Off those values the two forms differ at ~1e-16 — "
                "enough to move a sha. VERIFIED in session against baseline_kernel; "
                "⚠ pinned by NO test (option 3's citation does not cover this path)"
            ),
            "halo_consequence": (
                f"{scalar_halo}the multiplier scales BOTH axes, so any widening "
                "moves the meridional halo too. ⛔ And at this tile the shipped "
                "field is HULL-CLAMPED (F-2): m is a single constant across the "
                "whole SO core, so the vehicle cannot make the halo follow latitude "
                "here at all"
            ),
            "cost_class": "MEDIUM-HIGH — the same cost class as option 3, because "
            "it is the same kernel (F-1); plus electing a form whose hull would have "
            "to be widened to vary at this tile (F-2)",
            "rests_on_directional_sampling": False,
        },
        {
            "name": "3 — Paciorek nonstationary kernel",
            "code": "sverdrup.methods.kernel.PaciorekGaussianDegrees (exists, "
            f"PD-proven). {shared_path}",
            "what_changes": (
                "the kernel becomes nonstationary: L(x) = lx_deg_base · m(lat) with "
                "the Paciorek–Schervish normalisation that keeps it PD (a naive "
                "L(x) substitution is NOT PD), plus a σ(lat) variance field"
            ),
            "what_stays_identical": (
                "the temporal factor (stationary, spec fork b), the solver and the "
                "blend; and in the constant limit the shipped arithmetic exactly"
            ),
            "anchor_identity": (
                "preserved in the constant limit at L0 = 1 AND variance = 1. "
                "⚠ The citation — tests/test_paciorek_kernel.py::"
                "test_constant_reduction_identity_full_spacetime — proves KERNEL-"
                "MATRIX identity at sampled pairs (it does hold bit-exactly), NOT "
                "that the anchor SOLVE stays bit-identical, which is what check 1 "
                "compares. The stronger claim is unproven"
            ),
            "halo_consequence": (
                f"{scalar_halo}the halo follows L0·m(lat), and at this tile m is "
                "hull-clamped to a constant (F-2). A 1/cos φ multiplier — the form "
                "that would breach ±66 — is NOT expressible with the shipped field"
            ),
            "cost_class": "MEDIUM-HIGH — PD-proven and shipped, but it adds two "
            "fields to elect and to tune, and its constant-limit anchor identity is "
            "conditional on L0 = variance = 1",
            "rests_on_directional_sampling": False,
        },
    ]


def build_block(evidence_path: Path = EVIDENCE) -> dict[str, Any]:
    """The evidence block — arithmetic, options, ±66 table, EMPTY decision.

    Args:
        evidence_path: The evidence store.

    Returns:
        The block written to ``phase14.stage1.kernel_pack``.
    """
    return {
        "label": "STAGE1-EVIDENCE",
        "date": datetime.now(UTC).date().isoformat(),
        "consumer": "T9 / Gate 1 — the owner's kernel election",
        "pin": "spec 1-4; owner pins 99(a), 108; review pins 10/16",
        "decision": None,
        "decided_by": "owner, at Gate 1",
        "gates": False,
        "anisotropy_axis": {
            "status": "UNEVIDENCED at Stage 1 (owner pin 108a)",
            "cause": "pin 106 — per-direction track diagnostics need ORBIT_GEOMETRY, "
            "whose provider is challenge-box scoped; deriving per-tile geometry is a "
            "new producer, named Stage-2 work",
            "may_not_decide": "owner pin 108(b) — the decision may not be made on this "
            "axis; an option set that cannot be separated without it is a WAIT to the "
            "owner, not a decision T6 makes",
            "propagation": "owner pin 108(c) — the kernel election drives "
            "operative_halo_deg(), which sets the SO obs-frame edge and the ±66 margin "
            "(pin 10). An under-evidenced kernel choice becomes a geometry fact",
        },
        "code_findings": code_findings(),
        "arithmetic": arithmetic(evidence_path),
        "options": options(evidence_path),
        "breach_table": breach_table(evidence_path),
        "box_scale_negative": BOX_SCALE_SENTENCE,
    }


def _fmt(value: float, digits: int = 4) -> str:
    """Fixed-width number for the markdown tables.

    Args:
        value: The number.
        digits: Decimals.

    Returns:
        The rendered number.
    """
    return f"{value:.{digits}f}"


def render(evidence_path: Path = EVIDENCE) -> str:
    """The markdown pack section.

    Args:
        evidence_path: The evidence store.

    Returns:
        Markdown.
    """
    block = build_block(evidence_path)
    arith = block["arithmetic"]
    breach = block["breach_table"]
    aspect = arith["aspect"]
    measured = arith["measured_grid_aspect"]
    phi0 = measured["phi0_deg"]

    out = [
        "## T6 — high-latitude kernel DECISION pack (spec 1-4)",
        "",
        "**DECISION CELL: EMPTY.** T6 assembles and STOPs; the election is the owner's "
        "at Gate 1. Nothing below advocates an option — the pack prices them and "
        "stops.",
        "",
        "### T6.1 The arithmetic — f range and cos-φ",
        "",
        "| quantity | value |",
        "|---|---|",
        f"| \\|f\\| at the box φ0 = {BOX_PHI0}°N | {arith['abs_f']['38.1']:.6e} s⁻¹ |",
        f"| \\|f\\| at 55°S | {arith['abs_f']['55']:.6e} s⁻¹ |",
        f"| ratio, 55°S / box | **{_fmt(arith['f_ratio_55S_over_box'], 5)}×** |",
        f"| \\|f\\| at ±66° (the frame limit) | {arith['abs_f']['66']:.6e} s⁻¹ |",
        f"| \\|f\\| at the pole (2Ω) | {arith['abs_f']['pole']:.6e} s⁻¹ |",
        "",
        "**The spec's sentence, made numeric.** Across the anchor core (33°N→43°N) "
        f'cos φ falls **{arith["in_box_cos_decrease"] * 100:.1f}%** — the "~13% in-box" '
        "figure. Poleward the coordinate aspect 1/cos φ reaches "
        f"**{_fmt(aspect[f'{SO_CORE_POLEWARD:g}'])}×** at the SO core's pole edge "
        f"({SO_CORE_POLEWARD:g}°S) and **{_fmt(_aspect(LAT_BREACH_ABS))}×** at ±66° — "
        'the "~2–3× poleward" figure. Within the SO core itself cos φ falls '
        f"**{arith['so_within_tile_cos_decrease'] * 100:.1f}%**, against "
        f"{arith['in_box_cos_decrease'] * 100:.1f}% in the box.",
        "",
        "| latitude | cos φ | aspect 1/cos φ |",
        "|---|---|---|",
    ]
    for lat in (BOX_LAT_MIN, BOX_PHI0, BOX_LAT_MAX, SO_CORE_EQUATORWARD, abs(phi0)):
        key = f"{lat:g}"
        out.append(
            f"| {lat:g}° | {_fmt(arith['cos_phi'][key], 6)} | "
            f"{_fmt(aspect.get(key, _aspect(lat)))} |"
        )
    out += [
        f"| {SO_CORE_POLEWARD:g}° | "
        f"{_fmt(math.cos(math.radians(SO_CORE_POLEWARD)), 6)} | "
        f"{_fmt(aspect[f'{SO_CORE_POLEWARD:g}'])} |",
        "",
        "### T6.2 The SO tile's measured inputs — and what they cannot say",
        "",
        f"Recorded at `{measured['cited_from']}` (T5, REPORT-ONLY):",
        "",
        f"- **Grid aspect dy/dx = {measured['value']:.10f}** at φ0 = {phi0:.4f}°, "
        f"computed from the tile's own solve-grid axes.",
        f"- **Isotropic ring spectrum:** `spec_slope` "
        f"{arith['isotropic_row']['spec_slope']:.6f} — {arith['isotropic_row']['note']}.",
        f"- **Per-direction track sampling: {arith['per_direction_sampling']}.**",
        "",
        '⛔ **THE ANISOTROPY AXIS IS UNEVIDENCED (owner pin 108a)** — not "limited", '
        "which would invite a reader to weigh it. The reason is arithmetic, not "
        f"judgement: **{measured['value']:.10f} is exactly 1/cos({abs(phi0):.1f}°) = "
        f"{measured['one_over_cos_phi0']:.10f}** — a coordinate-grid property that "
        "**perfectly isotropic sampling would also produce**. The ring spectrum is "
        "isotropic by construction. Neither can speak to directional sampling, and the "
        "measurement that could is a RECORDED ABSENCE (pin 106: the orbit-geometry "
        "provider is challenge-box scoped; per-tile derivation is Stage-2 work).",
        "",
        "⚖ **THE DECISION MAY NOT BE MADE ON THIS AXIS (108b).** Any option whose case "
        "rests on directional sampling is **UNSUPPORTED BY STAGE-1 EVIDENCE**. If the "
        "option set cannot be separated without it, **that is a WAIT and it goes to the "
        "owner** — a kernel election is not improved by being made from a cosine. "
        "*(No option below rests on directional sampling, and the set separates "
        "WITHOUT the cosine — shown, not asserted: option 1 parts from the other two "
        "on METRIC (km vs degrees) and on ANCHOR IDENTITY (not preserved vs preserved "
        "in the constant limit); options 2 and 3 do not part from each other at all, "
        "because they are the same dispatch — finding F-1. Strike the cosine-driven "
        "halo column entirely and that separation still stands, so no WAIT is owed "
        "under 108(b).)*",
        "",
        "⚠ **THE PROPAGATION (108c).** The kernel election drives "
        "**`operative_halo_deg()`** — today a constant 1.0° and *the single point of "
        "change* when the halo is tied to the operative kernel scale (fork-d pin 4). "
        "That function sets the SO obs-frame edge and therefore the ±66 margin (pin 10): "
        "**an under-evidenced kernel choice becomes a geometry fact.** The ±66 table "
        "below is that consequence, priced per option.",
        "",
        "### T6.3 ⛔ What the SHIPPED code can express — read before the options",
        "",
        "Both findings came out of this pack's two-reviewer adversarial review "
        "(owner pin 212b) and were then confirmed by running the code. Each changes "
        "what electing an option MEANS, so they sit ahead of the table.",
        "",
    ]
    for finding in block["code_findings"]:
        out += [
            f"**{finding['id']} — {finding['headline']}.**",
            "",
            f"- *Evidence:* {finding['evidence']}.",
            f"- *Consequence:* {finding['consequence']}.",
            "",
        ]
    out += [
        "### T6.4 The options",
        "",
    ]
    for opt in block["options"]:
        out += [
            f"#### {opt['name']}",
            "",
            f"- **Code:** {opt['code']}",
            f"- **What changes:** {opt['what_changes']}",
            f"- **What stays identical:** {opt['what_stays_identical']}",
            f"- **Anchor identity:** {opt['anchor_identity']}",
            f"- **Halo auto-follow (fork-d pin 4):** {opt['halo_consequence']}",
            f"- **Cost class:** {opt['cost_class']}",
            "- **Rests on directional sampling:** "
            + (
                "**YES — UNSUPPORTED BY STAGE-1 EVIDENCE** (owner pin 108a)."
                if opt["rests_on_directional_sampling"]
                else "no — so it is not marked UNSUPPORTED BY STAGE-1 EVIDENCE on "
                "that ground."
            ),
            "",
        ]
    out += [
        "### T6.5 The ±66 column — COMPUTED, never typed",
        "",
        f"Threshold **{_fmt(breach['halo_breach_deg'], 1)}°**, derived as "
        f"`{breach['derivation']}`; edge derived as `{breach['edge_derivation']}`. "
        f"Live branch: **{breach['live_branch']}**.",
        "",
        "| candidate operative halo | halo [°] | SO obs south edge | margin to ±66 | "
        "flag | expressible with the SHIPPED code? |",
        "|---|---|---|---|---|---|",
    ]
    for row in breach["rows"]:
        flag = f"**{row['flag']}**" if row["breach"] else row["flag"]
        out.append(
            f"| {row['label']} | {_fmt(row['halo_deg'])} | "
            f"{_fmt(row['so_obs_south_edge'])}° | {row['margin_deg']:+.4f}° | {flag} "
            f"| {row['expressible_with_shipped_code']} |"
        )
    out += [
        "",
        f"Boundary: {breach['boundary_convention']}.",
        "",
        "⚖ **The arithmetic finding, stated and not argued from.** The only row that "
        f"breaches is the hypothetical 1/cos φ multiplier "
        f"({abs(breach['rows'][3]['margin_deg']):.4f}° past the limit) — and finding "
        "**F-2** is that the shipped LatitudeField **cannot express it**: at this "
        "tile the multiplier is hull-clamped to a constant. So **no option, as the "
        "code stands, breaches ±66.** What does cost margin is the SCALAR halo "
        "(F-3): the km-space row spends "
        f"{breach['rows'][0]['margin_deg'] - breach['rows'][1]['margin_deg']:.4f}° of "
        f"the {breach['rows'][0]['margin_deg']:.4f}° available, leaving "
        f"{breach['rows'][1]['margin_deg']:+.4f}°. An earlier draft made the breach a "
        "property of the nonstationary option; that was wrong in two ways at once, "
        "and the review caught both.",
        "",
        f"### T6.6 Scope\n\nExplicitly: {BOX_SCALE_SENTENCE}.",
        "",
        "**Decision:** _(EMPTY — owner, at Gate 1)_ · **RULED A WAIT at owner pin 219:** "
        "no option is electable as the code stands. Options 2/3 are INERT at this tile "
        "(hull-clamped latitude field, pin 216); option 1 carrying the box-equivalent "
        "111.195 km scale BREACHES ±66 at the latitudes the tile solves (obs −66.1301 at "
        "the core edge, −66.2812 at the solve-bbox edge) — priced above at φ0, which is "
        "the tile's middle and not its poleward reach (§7 discipline 16, instance p2). "
        "**Two named resolutions, both Stage 2: a smaller km scale, or a latitude-aware "
        "halo under fork-d pin 4's single point of change.** `operative_halo_deg()` is "
        "UNTOUCHED (219d); D4 inherits this.",
        "",
    ]
    return "\n".join(out) + "\n"


@app.command()
def main(
    record: Annotated[
        bool, typer.Option(help="Also write phase14.stage1.kernel_pack")
    ] = False,
) -> None:
    """Print the kernel decision pack section; ``--record`` also writes evidence.

    Args:
        record: Write the block to the evidence store.
    """
    typer.echo(render(evidence_path=EVIDENCE), nl=False)
    if record:
        from sverdrup.application.calibration.harness import (  # noqa: PLC0415
            atomic_write_json,
        )
        from sverdrup.validation import phase14_seal  # noqa: PLC0415

        phase14_seal.verify_current_seal()
        doc = json.loads(EVIDENCE.read_text())
        doc.setdefault("phase14", {}).setdefault("stage1", {})[KERNEL_PACK_NODE] = (
            build_block(evidence_path=EVIDENCE)
        )
        atomic_write_json(EVIDENCE, doc)
        typer.echo(f"\nrecorded: phase14.stage1.{KERNEL_PACK_NODE}")


if __name__ == "__main__":
    app()
