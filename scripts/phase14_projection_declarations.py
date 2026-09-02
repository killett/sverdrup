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
# NOT `verdict_declarations`: `_VERDICT` matches `verdict_<suffix>`, so that
# name made the PARENT block (phase14.stage1, which merely contains the node)
# look like a verdict-bearing gate. A container key should not be able to
# forge a claim about its container.
VERDICT_NODE_PATH = "phase14.stage1.reachability_declarations"

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


# ---------------------------------------------------------------------------
# Owner pin 148 — REACHABILITY declarations, the pin-42 side of the same
# forward-pointer mechanism. These two blocks declare FIRST because anchor-gate
# check 2 is discharged by CITATION to them, and a cited gate that could never
# have fired makes the citation hollow.
# ---------------------------------------------------------------------------

# Owner pin 145(b): prior-phase gates that NO standing Stage-1 claim cites.
# Recorded as found and left alone — those gates are closed and owner-signed,
# and reopening them is scope growth into finished work. The citation test is
# recorded with them so the judgement can be re-run rather than trusted.
UNCITED_PRIOR_PHASE: dict[str, Any] = {
    "rule": (
        "pin 58's boundary: a node is in scope if a standing claim CITES it, "
        "wherever it lives. These nine are cited by nothing in phase14"
    ),
    "citation_test": (
        "every string under evidence.phase14 was searched for each block path "
        "and for its root. The anchor gate's two CITED checks resolve "
        "elsewhere: check 2 (loader_identity) cites "
        "phase14.stage0.gate2_loader_identity and phase14.stage0.golden_tile "
        "(both DECLARED, pin 148), and check 4 (cross_env) cites the Stage-0 "
        "T17 CRN manifests. The 51 'phase13' mentions inside phase14 resolve "
        "to phase13.miost.provenance.*, members.root_int, lane0_reference, "
        "refit.report_only_instruments and file artifacts — not one of the "
        "three phase13 blocks below"
    ),
    "blocks": [
        "stage_b_defect_run_20260707.seam_dispersion",
        "stage_b.seam_dispersion",
        "phase8.c2_defect_run_20260712",
        "phase8.c2_acceptance",
        "phase8.c2_acceptance.window_tripwire",
        "phase10.oi.lanes",
        "phase13.miost.lanes",
        "phase13.miost.lanes.launch",
        "phase13.miost.c2_acceptance.window_tripwire",
    ],
    "status": (
        "RECORDED AS FOUND, NOT DECLARED. They remain in the pin-140a sweep "
        "output, so they are visible every time the check runs rather than "
        "quietly exempted"
    ),
}

REACHABILITY: dict[str, dict[str, Any]] = {
    "phase14.stage1.seam_rows[0]": {
        "amends": "phase14.stage1.seam_rows",
        "cited_by": "T9 pack item (2) — the seam result in its ruled shape (pin 97c)",
        "both_outcomes_reachable": True,
        "pass_condition": (
            "R_seam <= 1.0 -> CLEAN (boundary inclusive); 1.0 < R <= 2.5 -> "
            "ELEVATED-RECORDED; R > 2.5 -> STRUCTURAL_STOP to the owner. The "
            "thresholds are SEALED (instrument_configs()['seam']) and were fixed "
            "at Gate 0 before any number existed"
        ),
        "fail_condition": (
            "this pair/mean route measured R = 0.082738 against those cells, so a "
            "different dispersion would have landed in a different cell; the "
            "three-cell mapping is exhaustive and the boundaries are test-pinned "
            "at 1.0 and 1.0000001"
        ),
        "outcome_observed": "CLEAN",
        "attributability": (
            "Rule 0: a verdict is attributable ONLY if RMS(delta) > 3 x F, with "
            "F = 1.6372260422947704e-06 measured by a deeper-tolerance re-solve of the pair roster. "
            "Below that the row reads UNMEASURED (solver floor) and is not "
            "interpreted — the failing branch of the attributability test, "
            "reachable and pre-registered"
        ),
    },
    "phase14.stage1.seam_rows[0].floor": {
        "amends": "phase14.stage1.seam_rows",
        "both_outcomes_reachable": True,
        "pass_condition": "RMS(delta) > 3 x F -> the row's verdict is attributable",
        "fail_condition": (
            "RMS(delta) <= 3 x F -> the row is marked UNMEASURED (solver floor) "
            "and MUST NOT be interpreted; the rubric is one-sided, so smallness "
            "is never read as CLEAN"
        ),
        "outcome_observed": "attributable (F = 1.6372260422947704e-06)",
    },
    "phase14.stage1.seam_rows[1]": {
        "amends": "phase14.stage1.seam_rows",
        "cited_by": "T9 pack item (2) — the seam result in its ruled shape (pin 97c)",
        "both_outcomes_reachable": True,
        "pass_condition": (
            "R_seam <= 1.0 -> CLEAN (boundary inclusive); 1.0 < R <= 2.5 -> "
            "ELEVATED-RECORDED; R > 2.5 -> STRUCTURAL_STOP to the owner. The "
            "thresholds are SEALED (instrument_configs()['seam']) and were fixed "
            "at Gate 0 before any number existed"
        ),
        "fail_condition": (
            "this pair/sigma route measured R = 1.104435 against those cells, so a "
            "different dispersion would have landed in a different cell; the "
            "three-cell mapping is exhaustive and the boundaries are test-pinned "
            "at 1.0 and 1.0000001"
        ),
        "outcome_observed": "NOT_ESTABLISHED",
        "attributability": (
            "Rule 0: a verdict is attributable ONLY if RMS(delta) > 3 x F, with "
            "F = 9.539364309585352e-08 measured by a deeper-tolerance re-solve of the pair roster. "
            "Below that the row reads UNMEASURED (solver floor) and is not "
            "interpreted — the failing branch of the attributability test, "
            "reachable and pre-registered"
        ),
    },
    "phase14.stage1.seam_rows[1].floor": {
        "amends": "phase14.stage1.seam_rows",
        "both_outcomes_reachable": True,
        "pass_condition": "RMS(delta) > 3 x F -> the row's verdict is attributable",
        "fail_condition": (
            "RMS(delta) <= 3 x F -> the row is marked UNMEASURED (solver floor) "
            "and MUST NOT be interpreted; the rubric is one-sided, so smallness "
            "is never read as CLEAN"
        ),
        "outcome_observed": "attributable (F = 9.539364309585352e-08)",
    },
    "phase14.stage1.seam_rows[2]": {
        "amends": "phase14.stage1.seam_rows",
        "cited_by": "T9 pack item (2) — the seam result in its ruled shape (pin 97c)",
        "both_outcomes_reachable": True,
        "pass_condition": (
            "R_seam <= 1.0 -> CLEAN (boundary inclusive); 1.0 < R <= 2.5 -> "
            "ELEVATED-RECORDED; R > 2.5 -> STRUCTURAL_STOP to the owner. The "
            "thresholds are SEALED (instrument_configs()['seam']) and were fixed "
            "at Gate 0 before any number existed"
        ),
        "fail_condition": (
            "this oracle/mean route measured R = 0.098103 against those cells, so a "
            "different dispersion would have landed in a different cell; the "
            "three-cell mapping is exhaustive and the boundaries are test-pinned "
            "at 1.0 and 1.0000001"
        ),
        "outcome_observed": "CLEAN",
        "attributability": (
            "Rule 0: a verdict is attributable ONLY if RMS(delta) > 3 x F, with "
            "F = 1.3746386805707489e-06 measured by a deeper-tolerance re-solve of the pair roster. "
            "Below that the row reads UNMEASURED (solver floor) and is not "
            "interpreted — the failing branch of the attributability test, "
            "reachable and pre-registered"
        ),
    },
    "phase14.stage1.seam_rows[2].floor": {
        "amends": "phase14.stage1.seam_rows",
        "both_outcomes_reachable": True,
        "pass_condition": "RMS(delta) > 3 x F -> the row's verdict is attributable",
        "fail_condition": (
            "RMS(delta) <= 3 x F -> the row is marked UNMEASURED (solver floor) "
            "and MUST NOT be interpreted; the rubric is one-sided, so smallness "
            "is never read as CLEAN"
        ),
        "outcome_observed": "attributable (F = 1.3746386805707489e-06)",
    },
    "phase14.stage1.seam_rows[3]": {
        "amends": "phase14.stage1.seam_rows",
        "cited_by": "T9 pack item (2) — the seam result in its ruled shape (pin 97c)",
        "both_outcomes_reachable": True,
        "pass_condition": (
            "R_seam <= 1.0 -> CLEAN (boundary inclusive); 1.0 < R <= 2.5 -> "
            "ELEVATED-RECORDED; R > 2.5 -> STRUCTURAL_STOP to the owner. The "
            "thresholds are SEALED (instrument_configs()['seam']) and were fixed "
            "at Gate 0 before any number existed"
        ),
        "fail_condition": (
            "this oracle/sigma route measured R = 0.648763 against those cells, so a "
            "different dispersion would have landed in a different cell; the "
            "three-cell mapping is exhaustive and the boundaries are test-pinned "
            "at 1.0 and 1.0000001"
        ),
        "outcome_observed": "NOT_ESTABLISHED",
        "attributability": (
            "Rule 0: a verdict is attributable ONLY if RMS(delta) > 3 x F, with "
            "F = 8.278502339198468e-08 measured by a deeper-tolerance re-solve of the pair roster. "
            "Below that the row reads UNMEASURED (solver floor) and is not "
            "interpreted — the failing branch of the attributability test, "
            "reachable and pre-registered"
        ),
    },
    "phase14.stage1.seam_rows[3].floor": {
        "amends": "phase14.stage1.seam_rows",
        "both_outcomes_reachable": True,
        "pass_condition": "RMS(delta) > 3 x F -> the row's verdict is attributable",
        "fail_condition": (
            "RMS(delta) <= 3 x F -> the row is marked UNMEASURED (solver floor) "
            "and MUST NOT be interpreted; the rubric is one-sided, so smallness "
            "is never read as CLEAN"
        ),
        "outcome_observed": "attributable (F = 8.278502339198468e-08)",
    },
    "phase14.stage1.sigma_rows_not_established.withheld[0]": {
        "amends": "phase14.stage1.sigma_rows_not_established",
        "both_outcomes_reachable": True,
        "pass_condition": (
            "an ATTRIBUTABLE sigma verdict: the sigma-route dispersion resolves "
            "into a rubric cell that is not explained by the ensemble MC floor"
        ),
        "fail_condition": (
            "the dispersion is accounted for by the MC floor at the m actually "
            "run, so the cell reads NOT_ESTABLISHED — the pre-registered "
            "withholding cell, used as designed rather than as a blank"
        ),
        "outcome_observed": (
            "NOT_ESTABLISHED; the PRIOR verdict was ELEVATED at R_sigma 1.10443, "
            "which is the proof the other branch was reachable — it had been taken"
        ),
    },
    "phase14.stage1.sigma_rows_not_established.withheld[1]": {
        "amends": "phase14.stage1.sigma_rows_not_established",
        "both_outcomes_reachable": True,
        "pass_condition": "as withheld[0], on the oracle route",
        "fail_condition": "as withheld[0], on the oracle route",
        "outcome_observed": (
            "NOT_ESTABLISHED; PRIOR verdict CLEAN at R_sigma 0.64876 — the two "
            "withheld rows had OPPOSITE prior verdicts, so the withholding is "
            "not a one-way ratchet toward the safer answer"
        ),
    },
    "phase14.stage1.probe.stop_bracket": {
        "amends": "phase14.stage1.probe",
        "both_outcomes_reachable": True,
        "pass_condition": "measured/model ratio <= 1.3 -> the sizing model stands",
        "fail_condition": (
            "ratio > 1.3 -> STOP and surface to the owner BEFORE any full run; a "
            "mis-sized model at six tiles x nine windows is a spend decision, not "
            "an executor call"
        ),
        "outcome_observed": "not tripped",
    },
    "phase14.stage1.probe_converged.stop_bracket": {
        "amends": "phase14.stage1.probe_converged",
        "both_outcomes_reachable": True,
        "pass_condition": "as probe.stop_bracket, on the converged re-run (pin 23a)",
        "fail_condition": "as probe.stop_bracket",
        "outcome_observed": "not tripped",
    },
    "phase14.stage1.seam_convergence_probe.ram_gate": {
        "amends": "phase14.stage1.seam_convergence_probe",
        "both_outcomes_reachable": True,
        "pass_condition": "MemAvailable >= the threshold computed for this solve",
        "fail_condition": (
            "below it, the leg REFUSES rather than launching into an OOM — the "
            "same predicate E-16 section 2 uses at leg scale, and it has refused "
            "in practice (the pin-133b re-measure is parked on it right now)"
        ),
        "outcome_observed": "passed: 5189.6 MiB available against a 2457.1 MiB threshold",
    },
    "phase14.stage1.ensemble_settling_measurement.per_tile.seam_n.capture_identity_check": {
        "amends": "phase14.stage1.ensemble_settling_measurement",
        "both_outcomes_reachable": True,
        "pass_condition": (
            "the captured per-member field reduced by std(axis=0, ddof=1) "
            "reproduces BOTH the lineage evaluator and the map T4 persisted, at "
            "max_abs_diff 0.0 against a tolerance of exactly 0.0"
        ),
        "fail_condition": (
            "any nonzero difference -> the partition sigmas below are an "
            "APPROXIMATION of the production arithmetic rather than the "
            "arithmetic itself, and the settling measurement rests on nothing"
        ),
        "outcome_observed": (
            "0.0 on both comparisons. The measurement is not vacuous: the same "
            "block records a member-selection fp gap of 4.16e-17 from summation "
            "order, so the machinery CAN produce a nonzero number here"
        ),
    },
    "phase14.stage1.ensemble_settling_measurement.per_tile.seam_s.capture_identity_check": {
        "amends": "phase14.stage1.ensemble_settling_measurement",
        "both_outcomes_reachable": True,
        "pass_condition": "as seam_n's capture identity check",
        "fail_condition": "as seam_n's capture identity check",
        "outcome_observed": "0.0 on both comparisons",
    },
    "phase14.stage1.seam_shared_observation_channel.does_it_account_for_the_deficit": {
        "amends": "phase14.stage1.seam_shared_observation_channel",
        "both_outcomes_reachable": True,
        "pass_condition": (
            "the implied rho accounts for the measured T_cross deficit -> the "
            "shared observation channel explains it"
        ),
        "fail_condition": (
            "the implied rho is too small to close the 4.2 sd deficit -> a "
            "further mechanism is required and the diagnosis is incomplete"
        ),
        "outcome_observed": (
            "YES at rho = 5.17%; the deficit is fully accounted for. The "
            "arithmetic could have left a residual and did not"
        ),
    },
    "phase14.stage1.seam_crn_channel_mechanism.empirical_test": {
        "amends": "phase14.stage1.seam_crn_channel_mechanism",
        "both_outcomes_reachable": True,
        "pass_condition": (
            "member k of seam_n correlates with member k of seam_s while j != k "
            "does not -> the draws are PAIRED, which is what a shared draw "
            "predicts and a shared field does not"
        ),
        "fail_condition": (
            "matched and mismatched correlations indistinguishable -> the draws "
            "are independent and the pairing hypothesis is refuted"
        ),
        "outcome_observed": (
            "PAIRED: matched +0.2523 vs mismatched -0.0025, a separation of "
            "155.6 sd of the mismatched distribution over 390,915 strip nodes"
        ),
    },
    "phase14.stage1.rho_model_validation_preregistration"
    ".owner_arithmetic_independently_reproduced": {
        "amends": "phase14.stage1.rho_model_validation_preregistration",
        "both_outcomes_reachable": True,
        "pass_condition": (
            "an independent recomputation of sqrt(1-r^2)/sqrt(1-1.23 r^2) "
            "reproduces the owner's 1.01x / 1.13x / 7.17x to 3 significant figures"
        ),
        "fail_condition": (
            "it does not -> the owner's arithmetic, or this reproduction of it, "
            "is wrong, and the cost of a 23% rho error is not what the "
            "preregistration says"
        ),
        "outcome_observed": "REPRODUCED at all three points",
    },
    "phase14.stage1.tier2_probe_kuroshio_m100.rederived_bracket_pin_89d": {
        "amends": "phase14.stage1.tier2_probe_kuroshio_m100",
        "both_outcomes_reachable": True,
        "pass_condition": (
            "the measured per-tile wall lands inside the prior 23.8-94.2 h "
            "bracket -> the bracket stands and the sizing question is closed"
        ),
        "fail_condition": (
            "it lands outside -> the bracket was wrong and the spend question "
            "reopens. The measurement also had to be CONVERGED to count at all"
        ),
        "outcome_observed": (
            "inside, in the lower third (31.0 h/tile) — and leg 1 then measured "
            "19.67 h, so the projection itself was pessimistic by 1.58x "
            "(declared as a projection at phase14.stage1.projection_declarations)"
        ),
    },
    "phase14.stage1.tier2_probe_kuroshio_m100.derived_pin_89d.wall": {
        "amends": "phase14.stage1.tier2_probe_kuroshio_m100",
        "both_outcomes_reachable": True,
        "pass_condition": (
            "the measured wall matches the owner's LINEAR anchor (21.8 h/tile) "
            "-> scaling is linear in nodes and the high anchors were unsupported"
        ),
        "fail_condition": (
            "it exceeds the linear anchor -> scaling is superlinear, which is "
            "what happened: 31.0 h/tile, an implied exponent near 1.28, with the "
            "linear anchor optimistic by 1.42x"
        ),
        "outcome_observed": "NOT linear; between the nodes^1.25 and nodes^1.5 anchors",
    },
    "phase14.stage1.tier2_probe_kuroshio_m100.derived_pin_89d.wall.vs_ceiling": {
        "amends": "phase14.stage1.tier2_probe_kuroshio_m100",
        "both_outcomes_reachable": True,
        "pass_condition": "per-tile wall <= the 6.0 h tier2_probe ceiling",
        "fail_condition": "above it -> the Tier-2 crossing goes to the owner (task 22)",
        "outcome_observed": "over by 5.16x, and task 22 is where it went",
    },
    "phase14.stage1.tier2_probe_kuroshio_m100.derived_pin_89d.convergence": {
        "amends": "phase14.stage1.tier2_probe_kuroshio_m100",
        "both_outcomes_reachable": True,
        "pass_condition": (
            "both legs finish under rtol before the iteration cap -> CONVERGED, "
            "and the wall is a true measurement"
        ),
        "fail_condition": (
            "either leg exits AT the cap -> CAPPED, and the wall can only "
            "UNDER-report. The margin was thin and the record says so: the "
            "member batch used 486 of 500"
        ),
        "outcome_observed": "CONVERGED at 441/486 against a 500 cap",
    },
    "phase14.stage0.golden_tile.dc2021a_vs_cmems_my": {
        "amends": "phase14.stage0.golden_tile",
        "cited_by": (
            "phase14.stage1.anchor_gate.checks.loader_identity — check 2 runs "
            "nothing and is discharged by citation to this block and to "
            "phase14.stage0.gate2_loader_identity"
        ),
        "both_outcomes_reachable": True,
        "pass_condition": (
            "|mu_delta| <= 0.002 AND map rms <= 0.010 m — the recorded thresholds"
        ),
        "fail_condition": (
            "either leg over its threshold; both legs are one-sided tolerances "
            "on a measured difference, so either verdict was available before "
            "the numbers existed"
        ),
        "outcome_observed": "FAILED BOTH LEGS, which is why the bridge caveat exists",
        "margins": {
            "mu_delta": -0.012457116394516077,
            "mu_threshold": 0.002,
            "mu_over_by": 6.228558197258039,
            "map_rms_m": 0.041034469767374786,
            "map_rms_threshold_m": 0.01,
            "map_rms_over_by": 4.103446976737479,
        },
        "why_not_unfailable": (
            "the two legs are independent tolerances on measured differences "
            "between two data lineages; a repackaging-only difference would have "
            "landed inside both. They did not, by 6.2x and 4.1x, and the failure "
            "is the finding the tabled row carries forward"
        ),
    },
    "phase14.stage0.golden_tile.dc2021a_vs_cmems_my.mu_scale_check": {
        "amends": "phase14.stage0.golden_tile",
        "cited_by": (
            "the same check-2 citation; this sub-block is what rules out solver "
            "drift as the explanation of the mu delta above"
        ),
        "both_outcomes_reachable": True,
        "pass_condition": (
            "side A reproduces the SIGNED solution (mu_a 0.76941 vs lane0 "
            "0.76953 on the their_eval scale, 1.43 cm rms against "
            "phase13_lane0_mean.nc) -> the delta is a SCALE mismatch, not drift"
        ),
        "fail_condition": (
            "side A does NOT reproduce the signed solution -> solver drift, and "
            "the whole A-vs-B comparison becomes uninterpretable"
        ),
        "outcome_observed": "scale mismatch CONFIRMED, no solver drift",
        "why_not_unfailable": (
            "the discriminator is an equality against an independent recorded "
            "artifact, not a property of the comparison itself: had the "
            "generalized path drifted, mu_a would not have matched lane0 and "
            "this check would have said so"
        ),
    },
}


def validate_reachability(table: dict[str, dict[str, Any]]) -> list[str]:
    """Refusals against the reachability table (owner pins 148, 42).

    Holds a reachability declaration to the rule it discharges: a
    declaration that asserts both outcomes without naming the failing
    condition is pin 42's own defect wearing the fix's clothes.

    Args:
        table: The reachability declaration table.

    Returns:
        One message per malformed entry.
    """
    from sverdrup.validation.gate_schema import _has_values  # noqa: PLC0415

    bad: list[str] = []
    for path, entry in table.items():
        if not entry.get("amends"):
            bad.append(f"{path}: no `amends` — the forward pointer has no source")
        if entry.get("both_outcomes_reachable") is not True:
            bad.append(f"{path}: does not assert `both_outcomes_reachable`")
        for key in ("pass_condition", "fail_condition", "outcome_observed"):
            if not isinstance(entry.get(key), str) or not _has_values(entry.get(key)):
                bad.append(f"{path}: `{key}` states nothing (pin 42)")
    return bad


def build_verdict_node() -> dict[str, Any]:
    """The reachability node as recorded, with its own provenance."""
    return {
        "label": "VERDICT REACHABILITY DECLARATIONS — owner pins 148, 42",
        "ruling": "docs/superpowers/2026-07-27-owner-ruling-crn-sigma-rule0.md",
        "pin": "148 — the two golden-tile blocks declare first",
        "gates": False,
        "method": (
            "Pin 42 keyed on a self-declared `kind: gate` that appears ZERO times "
            "in this store, so it never inspected anything (pin 140). These "
            "declarations state, per block, the condition under which each "
            "verdict could occur and which one did — by forward pointer, so no "
            "witnessed node is edited"
        ),
        "why_these_two_first": (
            "anchor-gate check 2 RUNS NOTHING: it is discharged by citation to "
            "phase14.stage0.gate2_loader_identity and to the golden tile. A cited "
            "gate that could never have fired makes the citation hollow, and "
            "check 2 is one of two cited checks under the identity chain"
        ),
        "finding": (
            "NOT hollow. Both golden-tile legs FIRED — mu by 6.23x and map rms by "
            "4.10x over their recorded tolerances — and the scale check's "
            "discriminator is an equality against an independent artifact "
            "(phase13_lane0_mean.nc), so its other verdict was reachable too"
        ),
        "declarations": REACHABILITY,
        "not_declared_uncited_prior_phase": UNCITED_PRIOR_PHASE,
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
    bad_reach = validate_reachability(REACHABILITY)
    for msg in bad_reach:
        typer.echo(f"FAIL: {msg}")
    if bad_reach:
        raise typer.Exit(1)
    n_axes = sum(len(e["axes"]) for e in DECLARATIONS.values())
    typer.echo(
        f"PASS: {len(DECLARATIONS)} blocks, {n_axes} axes, every axis carries "
        "measured_over + applied_to with values"
    )
    typer.echo(
        f"PASS: {len(REACHABILITY)} reachability declarations, each naming its "
        "pass condition, its fail condition and the outcome observed"
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
    bad_reach = validate_reachability(REACHABILITY)
    if bad_reach:
        for msg in bad_reach:
            typer.echo(f"FAIL: {msg}")
        raise typer.Exit(1)
    results = json.loads(evidence_path.read_text())
    node = results["phase14"]["stage1"]
    node["projection_declarations"] = build_node()
    node["reachability_declarations"] = build_verdict_node()
    atomic_write_json(evidence_path, results)
    typer.echo(f"recorded {NODE_PATH} ({len(DECLARATIONS)} blocks)")
    typer.echo(f"recorded {VERDICT_NODE_PATH} ({len(REACHABILITY)} blocks)")


if __name__ == "__main__":
    app()
