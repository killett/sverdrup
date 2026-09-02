"""Declared spans for every projecting block (owner pins 139, 134).

Eleven recorded blocks project beyond what they measured. Pin 139 rules
that they are DECLARED, and declared through the pin-64 forward-pointer
index: **no witnessed node is edited**. The declarations live here and are
recorded as one new node, ``phase14.stage1.projection_declarations``, which
the amendment index points at from each amended node.

Three rules the content obeys, from pin 139:
- **(c) values, never a flag.** ``extrapolation_declared: true`` states
  nothing; every axis carries the range MEASURED and the range APPLIED.
- **(d) per axis.** A block projecting on two axes declares two, because
  "one axis caveated and one silent" is the pin-89 shape that cost the RAM
  basis.
- **(a) the declaring is the point.** Where leg 1 has since measured the
  projected quantity, the outcome is recorded beside the declaration —
  a declaration that cannot be checked against anything is half of one.

⛔ **The audit's limit, found while declaring (pin 139a's "expect to find
that asymmetry again").** The probe's RAM projection was never WRITTEN as
a projection: ``measured_one_window.peak_rss_mib`` became the launch-gate
basis with no derived field at all, so no field name could catch it. The
wall axis at least carried a prose caveat. The RAM axis is declared here
explicitly, and the general lesson is recorded with it: a shape-keyed
audit reads what was written down, and cannot see a projection that lives
only in a reader's head.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer

app = typer.Typer(add_completion=False)

EVIDENCE = Path("data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json")
NODE_PATH = "phase14.stage1.projection_declarations"

_MC_FLOOR = "sigma_delta MC floor sigma*sqrt(2/(m-1))*c4-corrected"

DECLARATIONS: dict[str, dict[str, Any]] = {
    "phase14.stage1.seam_sigma_diagnosis.line_1_magnitude": {
        "amends": "phase14.stage1.seam_sigma_diagnosis",
        "axes": {
            "predicted_mc_floor_sigma_over_sqrt_m_minus_1_m": {
                "quantity": _MC_FLOOR,
                "measured_over": {"m": 100, "n_windows": 9, "pair": "seam_n/seam_s"},
                "applied_to": {"m": 100, "n_windows": 9, "pair": "seam_n/seam_s"},
                "within_measured_span": True,
                "note": (
                    "the floor is EVALUATED at the same m the observation was taken "
                    "at; no m axis is crossed here. The m=100 floor that splitting "
                    "cannot reach is a different claim, declared at "
                    "ensemble_settling_measurement.pin_54_condition.test_pinned_at"
                ),
            },
            "observed_over_predicted": {
                "quantity": "ratio of the observed sigma_delta RMS to the floor above",
                "measured_over": {"m": 100, "pair": "seam_n/seam_s"},
                "applied_to": {"m": 100, "pair": "seam_n/seam_s"},
                "within_measured_span": True,
                "note": (
                    "a ratio of two quantities measured under the same "
                    "configuration; it transfers to no other pair, m or geometry"
                ),
            },
        },
    },
    "phase14.stage1.seam_sigma_diagnosis.line_4_half_split.per_tile.seam_n": {
        "amends": "phase14.stage1.seam_sigma_diagnosis",
        "axes": {
            "predicted_mc_floor_m": {
                "quantity": _MC_FLOOR + ", at the HALF ensemble",
                "measured_over": {"m_half": 50, "tile": "seam_n", "n_windows": 9},
                "applied_to": {"m_half": 50, "tile": "seam_n"},
                "within_measured_span": True,
            },
            "observed_over_predicted": {
                "quantity": "half1-minus-half2 RMS over the floor above",
                "measured_over": {"m_half": 50, "tile": "seam_n"},
                "applied_to": {"m_half": 50, "tile": "seam_n"},
                "within_measured_span": True,
            },
        },
    },
    "phase14.stage1.seam_sigma_diagnosis.line_4_half_split.per_tile.seam_s": {
        "amends": "phase14.stage1.seam_sigma_diagnosis",
        "axes": {
            "predicted_mc_floor_m": {
                "quantity": _MC_FLOOR + ", at the HALF ensemble",
                "measured_over": {"m_half": 50, "tile": "seam_s", "n_windows": 9},
                "applied_to": {"m_half": 50, "tile": "seam_s"},
                "within_measured_span": True,
            },
            "observed_over_predicted": {
                "quantity": "half1-minus-half2 RMS over the floor above",
                "measured_over": {"m_half": 50, "tile": "seam_s"},
                "applied_to": {"m_half": 50, "tile": "seam_s"},
                "within_measured_span": True,
            },
        },
    },
    **{
        f"phase14.stage1.ensemble_settling_measurement.per_tile.{tile}"
        ".recorded_half_split_reproduction": {
            "amends": "phase14.stage1.ensemble_settling_measurement",
            "axes": {
                field: {
                    "quantity": "replay of the recorded half-split numbers",
                    "measured_over": {"m_half": 50, "tile": tile, "n_windows": 9},
                    "applied_to": {"m_half": 50, "tile": tile},
                    "within_measured_span": True,
                    "note": (
                        "a REPRODUCTION under the identical configuration — it "
                        "crosses no axis, and its whole content is that it matches"
                    ),
                }
                for field in (
                    "recomputed_predicted_mc_floor_m",
                    "recorded_predicted_mc_floor_m",
                    "abs_diff_predicted_m",
                    "recomputed_observed_over_predicted",
                    "recorded_observed_over_predicted",
                )
            },
        }
        for tile in ("seam_n", "seam_s")
    },
    "phase14.stage1.ensemble_settling_measurement.pin_54_condition.test_pinned_at": {
        "amends": "phase14.stage1.ensemble_settling_measurement",
        "axes": {
            "m_25_predicted": {
                "quantity": "the c4(m) settling form",
                "measured_over": {"m": 25},
                "applied_to": {"m": 25},
                "within_measured_span": True,
            },
            "m_50_predicted": {
                "quantity": "the c4(m) settling form",
                "measured_over": {"m": 50},
                "applied_to": {"m": 50},
                "within_measured_span": True,
            },
            "m_100_predicted_not_measurable_by_splitting": {
                "quantity": "the c4(m) settling form",
                "measured_over": {"m": [25, 50], "method": "half-splitting"},
                "applied_to": {"m": 100},
                "extrapolation_declared": (
                    "EXTRAPOLATION on the m axis, and the field name says so: "
                    "splitting a 100-member ensemble yields halves of 50, so m=100 "
                    "is the one value the method cannot measure. The form is "
                    "checked at m=25 and m=50 against pooled means and by an "
                    "independent Monte-Carlo route, and applied at m=100 on that "
                    "basis — a validated FORM, not a measured point"
                ),
            },
        },
    },
    "phase14.stage1.seam_shared_observation_channel.does_it_account_for_the_deficit": {
        "amends": "phase14.stage1.seam_shared_observation_channel",
        "axes": {
            "implied_correlation_rho": {
                "quantity": "rho = 1 - (T_cross/E[T])^2, inverted from the measurement",
                "measured_over": {
                    "m": 100,
                    "pair": "seam_n/seam_s",
                    "domain": "the evaluation strip",
                },
                "applied_to": {"m": 100, "pair": "seam_n/seam_s"},
                "within_measured_span": True,
                "note": (
                    "an INVERSION of a measured T_cross, not a prediction: it "
                    "restates the same measurement in rho units. It speaks for THIS "
                    "pair on THIS domain and transfers to no other pair — the "
                    "shared-observation fraction is a property of the geometry"
                ),
            }
        },
    },
    "phase14.stage1.seam_crn_channel_mechanism.the_model_pin_70a": {
        "amends": "phase14.stage1.seam_crn_channel_mechanism",
        "axes": {
            "rho_implied_by_T_cross": {
                "quantity": "the same inversion as the shared-observation channel",
                "measured_over": {"m": 100, "pair": "seam_n/seam_s"},
                "applied_to": {"m": 100, "pair": "seam_n/seam_s"},
                "within_measured_span": True,
            },
            "predicted_T_cross": {
                "quantity": "T_cross under rho = r^2 at the MEASURED r",
                "measured_over": {"r": 0.25225741093173065, "m": 100},
                "applied_to": {"r": 0.25225741093173065, "m": 100},
                "within_measured_span": True,
                "note": (
                    "evaluated AT the measured r, so this number crosses nothing. "
                    "The r ~ 0.9 application of the same model IS an extrapolation "
                    "and is declared at phase14.stage1.rho_model_range_limitation "
                    "(validated_range [0, 0.2523], application_range [0, 0.9]) — "
                    "the one block in this store that ever declared itself"
                ),
            },
        },
    },
    "phase14.stage1.seam_crn_channel_mechanism.sharpened_t14_prediction_pin_70b.now": {
        "amends": "phase14.stage1.seam_crn_channel_mechanism",
        "axes": {
            "predicted_T_cross": {
                "quantity": "T_cross under rho = r^2, as the sharpened T14 prediction",
                "measured_over": {
                    "r": 0.25225741093173065,
                    "crn_state": "per-tile pavement origins (pre-T14)",
                },
                "applied_to": {"crn_state": "global pavement origin (post-T14)"},
                "extrapolation_declared": (
                    "EXTRAPOLATION on the CRN-STATE axis, which is the axis nobody "
                    "wrote down: the number is computed at the pre-T14 measured r "
                    "and used to predict behaviour after T14 pairs the draws by "
                    "construction. r post-T14 is UNMEASURED — T14 has not run, and "
                    "it is Stage 2's under pin 88's halt. Pin 68(b) already fixes "
                    "the direction (T_cross must FALL, and a fall is NOT evidence "
                    "of repair); the magnitude is what this axis cannot supply"
                ),
            }
        },
    },
    "phase14.stage1.tier2_probe_kuroshio_m100.rederived_bracket_pin_89d": {
        "amends": "phase14.stage1.tier2_probe_kuroshio_m100",
        "axes": {
            "per_tile_wall_h_if_linear_in_windows": {
                "quantity": "per-tile wall, one window scaled to nine",
                "measured_over": {
                    "n_windows": 1,
                    "wall_h": 3.4398840666791592,
                    "tile": "kuroshio",
                    "m": 100,
                },
                "applied_to": {"n_windows": 9, "tile": "kuroshio", "m": 100},
                "extrapolation_declared": (
                    "EXTRAPOLATION on the WINDOW-COUNT axis, linear, with "
                    "across-window scaling unmeasured at the time"
                ),
                "measured_outcome_2026_09_01": {
                    "projected_h": 30.958956600112433,
                    "measured_leg_h": 19.67,
                    "ratio_measured_over_projected": 0.635,
                    "note": (
                        "leg 1 settled it: the projection was PESSIMISTIC by 1.58x. "
                        "Windows are not equal in cost and the last two are short"
                    ),
                },
            },
            "four_tile_wall_h_if_linear_in_windows": {
                "quantity": "four-tile wall, one window scaled to nine and one tile to four",
                "measured_over": {"n_windows": 1, "n_tiles": 1, "tile": "kuroshio"},
                "applied_to": {"n_windows": 9, "n_tiles": 4},
                "extrapolation_declared": (
                    "TWO axes crossed at once — window count 1->9 AND tile count "
                    "1->4 — on a single tile's measurement. Tile-to-tile variation "
                    "remains UNMEASURED: only kuroshio has run, and southern, "
                    "equatorial and quiet_gyre differ in obs density, land fraction "
                    "and latitude"
                ),
            },
        },
    },
    "phase14.stage1.tier2_probe_kuroshio_m100.derived_pin_89d.wall": {
        "amends": "phase14.stage1.tier2_probe_kuroshio_m100",
        "axes": {
            "implied_exponent": {
                "quantity": "the nodes-scaling exponent implied by the probe",
                "measured_over": {"n_geometries": 1, "tile": "kuroshio", "m": 100},
                "applied_to": {"claim": "where the scaling sits among the anchors"},
                "extrapolation_declared": (
                    "ONE point cannot determine an exponent. 1.28 is the exponent "
                    "that would place this single measurement between the nodes^1.25 "
                    "and nodes^1.5 anchors; it LOCATES the measurement, and is not a "
                    "fitted scaling law. A second geometry is what would make it one"
                ),
            }
        },
    },
    "phase14.stage1.tier2_probe_kuroshio_m100.measured_one_window": {
        "amends": "phase14.stage1.tier2_probe_kuroshio_m100",
        "added_axis_not_caught_by_the_audit": True,
        "axes": {
            "peak_rss_mib": {
                "quantity": "peak RSS, taken as the LEG peak by E-16 section 2",
                "measured_over": {"n_windows": 1, "tile": "kuroshio", "m": 100},
                "applied_to": {"n_windows": 9, "role": "the launch gate's 2x basis"},
                "extrapolation_declared": (
                    "EXTRAPOLATION on the WINDOW-COUNT axis that was NEVER WRITTEN "
                    "DOWN. The wall axis at least carried a prose caveat; this one "
                    "carried nothing, and no field name marks it as projected, so "
                    "the shape-keyed audit cannot catch it either. It is declared "
                    "here by hand (pin 139a: expect the asymmetry again)"
                ),
                "measured_outcome_2026_09_01": {
                    "projected_peak_mib": 4364.52734375,
                    "measured_leg_peak_mib": 7389.3359375,
                    "ratio_measured_over_projected": 1.693,
                    "note": (
                        "OPTIMISTIC by 1.69x, and structurally so: peak RSS grew "
                        "monotonically with window count (4259 MiB after window 1 "
                        "to 7389 at window 9, ~391 MiB/window) because completed "
                        "windows were retained. Pin 133 removed the retention; the "
                        "corrected basis is the pin-133(b) three-window re-measure"
                    ),
                },
            }
        },
    },
}


def validate(declarations: dict[str, dict[str, Any]]) -> list[str]:
    """Refusals against the declaration table (owner pin 139c).

    Delegates to the library validator so the table is held to exactly
    the rule `seal_run check` applies — a second copy of a rule drifts
    from the first, which is the defect pin 131 named one level up.

    Args:
        declarations: The declaration table.

    Returns:
        One message per malformed axis.
    """
    from sverdrup.validation.gate_schema import (  # noqa: PLC0415
        validate_projection_declarations,
    )

    return validate_projection_declarations({"declarations": declarations})


def declared_axes_by_path(node: dict[str, Any]) -> dict[str, frozenset[str]]:
    """Path -> the field names declared for it, for the audit to consult.

    Args:
        node: The recorded declarations node.

    Returns:
        A mapping the evidence walker can look each block up in.
    """
    out: dict[str, frozenset[str]] = {}
    for path, entry in (node.get("declarations") or {}).items():
        out[path] = frozenset((entry.get("axes") or {}).keys())
    return out


def build_node() -> dict[str, Any]:
    """The node as recorded, with its own provenance."""
    return {
        "label": "PROJECTION DECLARATIONS — owner pin 139",
        "ruling": "docs/superpowers/2026-07-27-owner-ruling-crn-sigma-rule0.md",
        "pin": "139 — refuse now, declare the eleven by forward-pointer amendment",
        "gates": False,
        "method": (
            "Every block the pin-134 shape audit catches is declared here PER AXIS "
            "with the range measured and the range applied (139c/d). No amended "
            "node is edited: the amendment index carries the forward pointers "
            "(139b), and the audit resolves them"
        ),
        "the_audits_limit": (
            "A shape-keyed audit reads what was WRITTEN. The pin-89 probe's RAM "
            "projection was never written as one — measured_one_window.peak_rss_mib "
            "became the launch-gate basis with no derived field — so no field name "
            "could catch it. It is declared here by hand, and the limit is recorded "
            "rather than papered over"
        ),
        "declarations": DECLARATIONS,
    }


@app.command()
def check() -> None:
    """Validate the declaration table without writing anything."""
    bad = validate(DECLARATIONS)
    for msg in bad:
        typer.echo(f"FAIL: {msg}")
    if bad:
        raise typer.Exit(1)
    n_axes = sum(len(e["axes"]) for e in DECLARATIONS.values())
    typer.echo(
        f"PASS: {len(DECLARATIONS)} blocks, {n_axes} axes, every axis carries "
        "measured_over + applied_to with values"
    )


@app.command()
def write(
    evidence_path: Annotated[Path, typer.Option(help="Evidence store")] = EVIDENCE,
) -> None:
    """Record the declarations node (atomic); refuses a malformed table."""
    from sverdrup.application.calibration.harness import (  # noqa: PLC0415
        atomic_write_json,
    )

    bad = validate(DECLARATIONS)
    if bad:
        for msg in bad:
            typer.echo(f"FAIL: {msg}")
        raise typer.Exit(1)
    results = json.loads(evidence_path.read_text())
    node = results["phase14"]["stage1"]
    node["projection_declarations"] = build_node()
    atomic_write_json(evidence_path, results)
    typer.echo(f"recorded {NODE_PATH} ({len(DECLARATIONS)} blocks)")


if __name__ == "__main__":
    app()
