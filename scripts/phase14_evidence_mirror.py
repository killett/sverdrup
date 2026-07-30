"""Mirror the provenance-bearing evidence into the tree (owner pin 56).

The evidence store is gitignored and absent from a fresh clone, so every
write-once surface in Stage 1 has lived on one machine and has never been
externally visible. Pin 56(a): *the issue is WITNESS, not backup.*

This script mirrors the SUBSET whose value is tamper-evidence — small and
append-only — into version control. Bulk data and derived artifacts stay
ignored; the store is NOT un-ignored wholesale (pin 56b).

**The append-only gate is the point.** ``sync`` REFUSES to rewrite a node
it has already witnessed. A changed node is a STOP naming the node, not a
silent overwrite, because that event is exactly what write-once forbids
and exactly what a private file cannot rule out. Superseding a mirrored
record is possible but must be deliberate and reasoned:
``--supersede <path> --reason <text>`` appends the prior digest and body
to a supersession log rather than dropping them — the same discipline the
seam rubric uses for its own versions.

Where the tamper-evidence actually comes from: once the mirror is pushed,
its digests sit in history the author cannot silently rewrite. This script
makes drift DETECTABLE; the push makes it WITNESSED.

Commands:
    sync    extract, gate against the existing mirror, write
    check   verify the mirror against the store and its own digests
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer

from sverdrup.validation.evidence_mirror import (
    detect_changes,
    detect_index_regressions,
    digest_node,
    select_nodes,
)

app = typer.Typer(add_completion=False)

STORE = Path("data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json")
SEAL = Path("data/2021a_ssh_mapping_ose/ours/phase14_evaluation_seal_v1.json")
MIRROR_DIR = Path("docs/validation/evidence-mirror")
MIRROR = MIRROR_DIR / "phase14-stage1-provenance.json"
SEAL_MIRROR = MIRROR_DIR / "phase14_evaluation_seal_v1.json"
SUPERSESSIONS = MIRROR_DIR / "supersessions.json"

# ---------------------------------------------------------------------------
# THE LINE (owner pin 58, correcting pin 56d).
#
# THE TEST IS CITATION, NOT STAGE: a node is IN if a standing claim CITES
# it, wherever it lives. Pin 58 overturned the stage-scoped boundary the
# first cut used — two of the five anchor-gate checks are discharged by
# CITATION to Stage-0 evidence, so under the old rule the identity chain
# T14 threatens rested, in part, on unwitnessed records.
#
# A node is still NOT mirrored if nothing cites it: bulk search history,
# tuning traces, re-derivable operational config. Prior phases come in
# ENUMERATED, never wholesale (pin 58c). Exclusions are recorded BY NAME
# below, so the line stays visible rather than implied.
# ---------------------------------------------------------------------------

MIRRORED: dict[str, str] = {
    "phase14.stage1.gate5": (
        "WRITE-ONCE gate-5 constants (mu, sigma, lambda_x) pinned from the "
        "anchor run, with the scored-map sha — owner-named in pin 56"
    ),
    "phase14.stage1.anchor_gate": (
        "the five-gate anchor record: member sha-equality, surface identity "
        "and the score-identity assertions. This is the identity chain T14 "
        "puts at risk, so it must be witnessed BEFORE T14, not after"
    ),
    "phase14.stage1.seam_rows": (
        "the rubric's verdict rows — write-once through the one-shot guard "
        "whose deletion attack was fixed and test-pinned under pin 47"
    ),
    "phase14.stage1.seam_sigma_diagnosis": (
        "the establishing diagnosis the sigma withholding CITES. If it can "
        "be rewritten unobserved, the citation is hollow"
    ),
    "phase14.stage1.sigma_rows_not_established": (
        "the pin-45(b) withholding record, incl. the preserved prior "
        "verdicts — a correction record, owner-named in pin 56"
    ),
    "phase14.stage1.rubric_v2_amendment_withdrawn": (
        "the pin-40(b) withdrawal record. Its whole purpose is to keep a "
        "rolled-back artifact from teaching a future reader the wrong "
        "convention — worthless if it can be quietly edited"
    ),
    "phase14.stage1.ensemble_settling_measurement": (
        "pin 43's settling measurement INCLUDING the pin_53_m_requirement "
        "and pin_54_condition blocks — owner-named in pin 56. The 400 "
        "ratios per split size are mirrored in full, not digested: pin "
        "56(c) is that a re-typeable number in prose is not the record"
    ),
    "c2_touch_tally": (
        "the LOCKED-INSTRUMENT tally (see src/sverdrup/validation/"
        "locked_tier.py) — owner-named in pin 56. 'Tally byte-identical' is "
        "standing discipline and cannot be self-witnessed"
    ),
    "acceptance_artifact_correction": (
        "a standing correction record: which acceptance map was the "
        "artifact and how it differed from the true map"
    ),
    # ---- pin 58(d): the sha capture that closes the substitution hole ----
    "phase14.stage1.anchor_gate_artifact_shas": (
        "pin 58(d). Check-1's mean, Gamma and variance routes recorded the "
        "comparison OUTCOME but no sha of the artifact compared against, so "
        "a later substitution would have re-passed. This node captures those "
        "shas. Witnessing it is the whole point — an unwitnessed sha record "
        "closes nothing"
    ),
    "phase14.stage1.gate5_mu_witness_scope": (
        "pin 65. The CLAIM-level witness scope for the pin-29 mu values: one "
        "of the three rests on phase13_lane0_mean.nc, witnessed forward-only"
    ),
    "phase14.stage1.artifact_witness_classes": (
        "pin 67. Splits the 'no sha' bucket by what ELSE constrains each "
        "artifact: 7 constrained by reproduction, 1 verified by "
        "re-derivation, 2 unconstrained. The class assignment is a standing "
        "claim, so it is witnessed"
    ),
    "phase14.stage1.seam_crn_mechanism_separation_construction": (
        "pin 75. Records N and the SE construction beside the cited "
        "separation, and supersedes the 155.6 figure with 167.6 — the "
        "number will be cited, so its construction is witnessed with it"
    ),
    "phase14.stage1.rho_model_range_limitation": (
        "pin 77. The sweep's REACHABLE span [0, 0.2523] against the applied "
        "r ~ 0.9, the structural cause, and 77(c)'s pre-registered branch. It "
        "declares its own extrapolation, so it is the first block to pass "
        "pin 78's refusal on disclosure rather than on silence"
    ),
    "phase14.stage1.rho_model_validation_preregistration": (
        "pins 73/74. The sweep's design, its must-precede-T14 condition and "
        "73(c)'s acceptable-failure outcome. A pre-registration witnessed "
        "only after the fact is not a pre-registration"
    ),
    "phase14.stage1.tier2_probe_kuroshio_m100": (
        "pin 89. The MEASURED Tier-2 probe that retires the 4x bracket: one "
        "window, kuroshio, m=100, CONVERGED. It is the number the ceiling "
        "decision turns on, so it is witnessed before that decision is taken"
    ),
    "phase14.stage1.crn_production_defect_deferred": (
        "pin 87. The CRN defect recorded as a PRODUCTION defect with a product "
        "consequence, deferred to Stage 2 by pin 84 and NOT closed. Stage 2G "
        "cannot close while it stands — a deferral that can be quietly edited "
        "is how a known defect becomes a forgotten one"
    ),
    "phase14.stage1.seam_crn_channel_mechanism": (
        "pin 70. The MECHANISM behind rho, named and measured: obs "
        "perturbations are CRN-keyed on observation identity at a shared "
        "root, so identical strip observations get identical eps' draws. "
        "Carries the sharpened T14 prediction with a MAGNITUDE, which must be "
        "witnessed before T14 to be a pre-registration at all"
    ),
    "phase14.stage1.seam_shared_observation_channel": (
        "pin 68(a). The measured second correlation channel — identical "
        "observation sets on the evaluation strip — and the PRE-REGISTERED "
        "T14 expectation, which must be witnessed BEFORE T14 runs or it is "
        "not a pre-registration"
    ),
    "phase14.stage1.artifact_witness_inventory": (
        "pin 65's enumeration. Classifies every data/ artifact cited under "
        "phase14 as witnessed-at-creation, forward-only, or previously "
        "unwitnessed-and-captured-here. It is the map of what the mirror's "
        "guarantee reaches, so it is witnessed like the rest"
    ),
    "phase14.stage1.anchor_gate_artifact_sha_reconciliation": (
        "pin 60(a). Reconciles the 2026-07-28 capture against phase-13's own "
        "contemporaneous shas: 2 of 3 intervals CLOSED by exact match, 1 "
        "recorded SEARCHED AND ABSENT. It is a standing claim, so it is "
        "witnessed like the rest"
    ),
    "phase13.miost.provenance": (
        "pin 58's citation rule, triggered by pin 60(a): the reconciliation "
        "above CITES this node's mean_maps_sha256 / var_maps_sha256 / "
        "member_store_sha256 / field_artifact_sha256 as the contemporaneous "
        "witness. A reconciliation against an unwitnessed record closes "
        "nothing, so the record it leans on comes in too"
    ),
    # ---- pin 58(a): Stage-0, IN because Stage-1 checks CITE it ----
    "phase14.stage0.gate2_loader_identity": (
        "pin 58(a). Anchor-gate check 2 is discharged BY CITATION to this "
        "node (with its manifest_sha) — an identity-chain check resting on "
        "evidence that was unwitnessed until now"
    ),
    "phase14.stage0.golden_tile": (
        "pin 58(a). The other half of check 2's citation, and the "
        "mu_scale_check the gate-5 scope note leans on"
    ),
    "phase14.stage0.seal": "pin 58(a). Stage-0's seal record — part of the seal chain",
    "phase14.stage0.probe_tile": (
        "pin 58(a). The Stage-0 sizing record the Stage-1 probe path is "
        "measured against"
    ),
    "phase14.stage0.storage_ledger": "pin 58(a). Stage-0 ledger row",
    "phase14.stage0.cmems_census_raw_sha": "pin 58(a). Input-census sha — a content witness",
    "phase14.stage0.census_sha": "pin 58(a). Census sha — a content witness",
    "phase14.stage0.epoch_table_draft_sha": "pin 58(a). Epoch-table sha — a content witness",
    "phase14.stage0.gauges": "pin 58(a). Gauge inventory behind the Stage-0 gate",
    "phase14.stage0.n_epochs": "pin 58(a). Completes the Stage-0 gate record",
    # ---- pin 58(b): seam_pair, IN because the m=137 pricing cites it ----
    "phase14.stage1.seam_pair": (
        "pin 58(b). OVERTURNS the first cut's exclusion. The m=137 pricing "
        "quotes this node's wall and peak-RSS figures; that pricing is a "
        "standing claim recorded against pin 53 and it feeds T17"
    ),
    # ---- pin 58(c): prior phases ENUMERATED, not wholesale ----
    "phase13.miost.members": (
        "pin 58(c). The ONLY prior-phase evidence node a standing Stage-1 "
        "claim cites: anchor_gate's root-deviation note cites "
        "phase13.miost.members.root_int to explain why check 1 runs at the "
        "phase-13 acceptance root rather than the plan-text root. 0.8 KiB"
    ),
}

# Named exclusions, with the reason. Pin 56(d): do not assume the line.
NOT_MIRRORED: dict[str, str] = {
    "sobol / bo / calibration / winner*": (
        "search history and tuning traces. Bulk, derived, and no standing "
        "claim rests on their byte content"
    ),
    "replay_cache / solver_budget": "operational configuration, re-derivable",
    "stage_b* / phase8 / phase9 / phase10 / phase11 / phase13 (except phase13.miost.members)": (
        "pin 58(c): prior phases come in ENUMERATED, not wholesale. A full "
        "sweep of every prior-phase reference inside the phase14 evidence "
        "found exactly ONE cited evidence node — phase13.miost.members, now "
        "mirrored. The other prior-phase references are FILE artifacts, not "
        "nodes, and those are closed by sha under pin 58(d) rather than by "
        "mirroring a phase: phase13_winner_mean.nc and phase13_winner_var.nc "
        "(captured now), phase13_winner_members.npz (already sha'd in "
        "reference_store), phase13_field_miost.json (already sha'd in "
        "era_noop) and phase13_lane0_mean.nc (captured now)"
    ),
    "phase14.stage1.probe / probe_converged / seam_convergence_probe": (
        "sizing and convergence probes. Operational, re-runnable"
    ),
}


# ---------------------------------------------------------------------------
# AMENDMENT INDEX (owner pin 64). A witnessed node is never edited to point
# at what later amends it — pin 64(b) — so the forward pointers live here.
# READING PATH: manifest first, always. A node's caveats are current AS OF
# ITS OWN WRITING; this index is what tells you whether they still stand.
#
# Append-only itself: entries may be added, never removed or rewritten.
# ---------------------------------------------------------------------------

AMENDMENTS: dict[str, list[dict[str, str]]] = {
    "phase14.stage1.anchor_gate_artifact_shas": [
        {
            "amended_by": "phase14.stage1.anchor_gate_artifact_sha_reconciliation",
            "date": "2026-07-28",
            "what": (
                "That node's caveat says the 2026-07-28 capture cannot speak "
                "to the interval before it. Pin 60(a) then CLOSED that "
                "interval for phase13_winner_mean.nc and phase13_winner_var.nc "
                "by exact match against phase 13's own contemporaneous shas. "
                "The caveat still stands for phase13_lane0_mean.nc, which is "
                "recorded SEARCHED AND ABSENT. Read the reconciliation before "
                "relying on the caveat as written."
            ),
        }
    ],
    "phase14.stage1.anchor_gate": [
        {
            "amended_by": "phase14.stage1.anchor_gate_artifact_shas",
            "date": "2026-07-28",
            "what": (
                "Pin 58(d): check-1's mean_vs_acceptance, variance and "
                "gamma_route routes recorded the comparison OUTCOME but no "
                "sha of what they compared against. The shas are captured "
                "there; the gate script now writes reference_sha256 inline so "
                "future runs are self-witnessing."
            ),
        },
        {
            "amended_by": "phase14.stage1.gate5_mu_witness_scope",
            "date": "2026-07-28",
            "what": (
                "Pin 65: the gate-5 scope note's pin-29 mu disambiguation "
                "leans on phase13_lane0_mean.nc, whose witness is "
                "FORWARD-ONLY. The scope statement is recorded separately "
                "rather than edited into this witnessed node."
            ),
        },
    ],
    "phase14.stage1.gate5": [
        {
            "amended_by": "phase14.stage1.gate5_mu_witness_scope",
            "date": "2026-07-28",
            "what": (
                "Pin 65: caveats attach to CLAIMS, not only to artifacts. The "
                "scope_note's related-values row for the signed lane0 maps "
                "rests on an artifact witnessed forward-only from 2026-07-28."
            ),
        }
    ],
    "phase14.stage1.artifact_witness_inventory": [
        {
            "amended_by": "phase14.stage1.artifact_witness_classes",
            "date": "2026-07-28",
            "what": (
                "Pin 67: the inventory's 'no sha' bucket of 10 is SPLIT — 7 "
                "constrained by reproduction, 1 verified by re-derivation, 2 "
                "unconstrained. Do not read the bucket as one epistemic state."
            ),
        }
    ],
    "phase14.stage1.ensemble_settling_measurement": [
        {
            "amended_by": "phase14.stage1.artifact_witness_inventory",
            "date": "2026-07-28",
            "what": (
                "Pin 65 sweep: the seam member STORES this measurement "
                "replays had NO recorded sha until 2026-07-28. The "
                "measurement's internal identity checks are unaffected "
                "(exact 0.0 against the lineage evaluator and the persisted "
                "maps), but the artifacts it read are witnessed forward-only."
            ),
        },
        {
            "amended_by": "phase14.stage1.seam_shared_observation_channel",
            "date": "2026-07-28",
            "what": (
                "Pin 68: result 5's ~4.2 sd deficit is explained by a SECOND "
                "channel — the two tiles' observation sets on the evaluation "
                "strip are IDENTICAL (Jaccard 1.0000), implying rho ~ 5.2%. "
                "Rule 0.b's independence premise was never correct for the "
                "pair route on any lattice."
            ),
        },
        {
            "amended_by": "phase14.stage1.seam_crn_channel_mechanism",
            "date": "2026-07-28",
            "what": (
                "Pin 70: the mechanism is named — obs perturbations are "
                "CRN-keyed on OBSERVATION identity at a shared root, so the "
                "pair is ALREADY partly paired (matched-member field "
                "correlation +0.2523 vs -0.0026 mismatched, 155 sd apart). "
                "rho ~ r^2 turns the number into a model."
            ),
        },
    ],
    "phase14.stage1.seam_crn_channel_mechanism": [
        {
            "amended_by": ("phase14.stage1.seam_crn_mechanism_separation_construction"),
            "date": "2026-07-28",
            "what": (
                "Pin 75: the separation reported there as '+155.6 sd' used "
                "N=100 for a 9900-sample set. Correct SE gives 167.6; the "
                "most conservative reading is 12.8 and the two distributions "
                "do not overlap. The mechanism conclusion is unchanged."
            ),
        },
        {
            "amended_by": "phase14.stage1.rho_model_validation_preregistration",
            "date": "2026-07-28",
            "what": (
                "Pins 73/74: rho = r^2 there is validated only at r = 0.2523, "
                "where sqrt(1-rho) is flat. It must NOT parameterize the floor "
                "until task 20 sweeps r across the range and names the 23% "
                "residual."
            ),
        },
    ],
    "phase14.stage1.rho_model_validation_preregistration": [
        {
            "amended_by": "phase14.stage1.rho_model_range_limitation",
            "date": "2026-07-28",
            "what": (
                "Pin 77: the sweep design pre-registered there spans only "
                "[0, 0.2523] — it can REDUCE correlation, never raise it, "
                "because acc is post-solve and cannot re-pair element draws. "
                "Its claim is narrowed to the FORM; high-r needs solves "
                "(task 21, priced not launched)."
            ),
        }
    ],
    "phase14.stage1.seam_shared_observation_channel": [
        {
            "amended_by": "phase14.stage1.seam_crn_channel_mechanism",
            "date": "2026-07-28",
            "what": (
                "Pin 70 supplies the MECHANISM behind that node's rho and a "
                "sharpened T14 prediction with a magnitude: "
                "T_cross ~ E[T](m) * sqrt(1 - r^2). The direction-only "
                "pre-registration there still stands; this adds the size."
            ),
        }
    ],
    "phase14.stage1.seam_rows": [
        {
            "amended_by": "phase14.stage1.sigma_rows_not_established",
            "date": "2026-07-27",
            "what": (
                "Pin 45(b): both sigma rows are WITHHELD as "
                "NOT_ESTABLISHED (ensemble MC artifact). The prior verdicts "
                "in this node are preserved but are NOT the current reading."
            ),
        },
        {
            "amended_by": "phase14.stage1.ensemble_settling_measurement",
            "date": "2026-07-27",
            "what": (
                "Pin 43's settling measurement bears on how any future sigma "
                "verdict is set. RECORDED, NOT SEALED — no factor is adopted "
                "and no verdict here changes because of it."
            ),
        },
    ],
}


def _load(path: Path) -> Any:  # noqa: ANN401 - arbitrary JSON
    """Read and parse a JSON file.

    Args:
        path: File to read.

    Returns:
        The parsed document.

    Raises:
        FileNotFoundError: If the file is absent.
    """
    if not path.exists():
        raise FileNotFoundError(f"missing: {path}")
    return json.loads(path.read_text())


def _extract() -> tuple[dict[str, Any], dict[str, Any]]:
    """Pull the mirrored subset from the store and the seal.

    Returns:
        ``(nodes, seal)``.
    """
    store = _load(STORE)
    nodes = select_nodes(store, list(MIRRORED))
    seal = _load(SEAL)
    return nodes, seal


def _write_json(path: Path, payload: Any) -> None:  # noqa: ANN401
    """Write pretty, newline-terminated JSON.

    Args:
        path: Destination.
        payload: JSON-serializable document.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


@app.command()
def sync(
    supersede: Annotated[
        list[str] | None,
        typer.Option(help="Dotted path whose mirrored record may be replaced"),
    ] = None,
    reason: Annotated[str, typer.Option(help="Why the supersession is warranted")] = "",
) -> None:
    """Extract, gate against the existing mirror, and write.

    Raises:
        RuntimeError: If an already-mirrored node changed and was not
            explicitly superseded — the append-only STOP.
    """
    nodes, seal = _extract()
    allowed = set(supersede or [])
    if allowed and not reason:
        raise RuntimeError(
            "--supersede requires --reason: a silent replacement is the thing this gate exists to prevent"
        )

    prior_bodies: dict[str, Any] = {}
    if MIRROR.exists():
        existing_doc = _load(MIRROR)
        regressed = detect_index_regressions(
            existing_doc.get("amendment_index", {}), AMENDMENTS
        )
        if regressed:
            raise RuntimeError(
                "AMENDMENT-INDEX REGRESSION — a forward pointer was removed or "
                f"rewritten for: {regressed}. The index is append-only (pin 64): "
                "a dropped pointer leaves a witnessed node looking current while "
                "the record that amends it is unreachable from it."
            )
        existing = {k: v["value"] for k, v in existing_doc["nodes"].items()}
        changed = detect_changes(existing, nodes)
        unauthorized = [c for c in changed if c not in allowed]
        if unauthorized:
            raise RuntimeError(
                "APPEND-ONLY VIOLATION — these nodes are already witnessed in "
                f"the mirror and their content has CHANGED: {unauthorized}. "
                "This is the event write-once forbids. If the change is "
                "legitimate, re-run with --supersede <path> --reason <text>; "
                "the prior digest and body are then preserved, never dropped."
            )
        for path in changed:
            prior_bodies[path] = {
                "superseded_utc": datetime.now(UTC).isoformat(),
                "reason": reason,
                "prior_digest": digest_node(existing[path]),
                "prior_value": existing[path],
            }

    doc = {
        "WHAT THIS MIRROR DOES AND DOES NOT PROVE": {
            "pin": "60 — the guarantee is PROSPECTIVE; state it once, at the top",
            "guarantee": (
                "Every node below was WITNESSED on the date it first entered "
                "this mirror. From that moment it is closed against FUTURE "
                "alteration: changing it is detected by `check` and refused by "
                "`sync`, and once pushed the digest sits in history the author "
                "cannot silently rewrite."
            ),
            "what_it_does_NOT_mean": (
                "'Witnessed' does NOT mean 'proven unaltered since creation'. "
                "Every record written BEFORE the date it was mirrored is "
                "unwitnessed for the interval between its writing and its "
                "mirroring. A reader will otherwise take the stronger reading, "
                "so it is stated here rather than left to inference."
            ),
            "first_witnessed": "2026-07-28 (all nodes in the initial two syncs)",
            "where_the_interval_HAS_been_closed": (
                "phase14.stage1.anchor_gate_artifact_sha_reconciliation — pin "
                "60(a). Two of the three captured artifacts reconcile EXACTLY "
                "against shas phase 13 recorded at the time, so for those the "
                "interval is closed from creation, not merely bounded going "
                "forward. The third is recorded as SEARCHED AND ABSENT."
            ),
        },
        "what_this_is": (
            "Mirror of the PROVENANCE-BEARING subset of the gitignored "
            "evidence store (owner pin 56). The issue is WITNESS, not "
            "backup: write-once enforced by a file only its author can see "
            "is a convention. Once pushed, these digests sit in history the "
            "author cannot silently rewrite."
        ),
        "ruling": "docs/superpowers/2026-07-27-owner-ruling-crn-sigma-rule0.md",
        "pin": "56 — mirror the provenance-bearing evidence into the tree",
        "source_store": str(STORE),
        "source_store_note": (
            "gitignored (.gitignore:42) and NOT un-ignored wholesale, per "
            "pin 56(b). Only the nodes below are mirrored."
        ),
        "the_line_mirrored": MIRRORED,
        "the_line_not_mirrored": NOT_MIRRORED,
        "READ_THIS_FIRST": (
            "A node's caveats are current AS OF ITS OWN WRITING. "
            "`amendment_index` below is what tells you whether they still "
            "stand — read the manifest first, always (pin 64). Witnessed "
            "nodes are never edited to point at what amends them; that is "
            "why the index exists (pin 64b)."
        ),
        "amendment_index": AMENDMENTS,
        "generated_utc": datetime.now(UTC).isoformat(),
        "nodes": {
            path: {"digest_sha256": digest_node(value), "value": value}
            for path, value in sorted(nodes.items())
        },
    }
    _write_json(MIRROR, doc)
    _write_json(SEAL_MIRROR, seal)

    if prior_bodies:
        log = _load(SUPERSESSIONS) if SUPERSESSIONS.exists() else {"supersessions": []}
        for path, record in prior_bodies.items():
            log["supersessions"].append({"path": path, **record})
        _write_json(SUPERSESSIONS, log)
        typer.echo(f"superseded (prior bodies preserved): {sorted(prior_bodies)}")

    total = sum(len(json.dumps(v)) for v in nodes.values())
    typer.echo(f"mirrored {len(nodes)} nodes ({total / 1024:.1f} KiB) -> {MIRROR}")
    typer.echo(f"mirrored seal -> {SEAL_MIRROR} (sha {digest_node(seal)[:16]}…)")
    typer.echo(
        f"excluded by name: {len(NOT_MIRRORED)} groups (see the_line_not_mirrored)"
    )


@app.command()
def check() -> None:
    """Verify the mirror against the store and its own digests.

    Raises:
        RuntimeError: If the mirror is absent, its internal digests do
            not match its bodies, or the store has drifted from it.
    """
    if not MIRROR.exists():
        raise RuntimeError(f"no mirror at {MIRROR} — run `sync` first")
    doc = _load(MIRROR)

    bad = [
        path
        for path, entry in doc["nodes"].items()
        if digest_node(entry["value"]) != entry["digest_sha256"]
    ]
    if bad:
        raise RuntimeError(f"MIRROR SELF-CHECK FAILED — digest mismatch: {bad}")

    nodes, seal = _extract()
    existing = {k: v["value"] for k, v in doc["nodes"].items()}
    drift = detect_changes(existing, nodes)
    added = sorted(set(nodes) - set(existing))
    seal_drift = digest_node(seal) != digest_node(_load(SEAL_MIRROR))

    typer.echo(f"mirror self-check: PASS ({len(doc['nodes'])} nodes, digests match)")
    if drift:
        raise RuntimeError(
            f"STORE HAS DRIFTED from the witnessed mirror: {drift}. Either the "
            "store was rewritten or the mirror is stale — resolve deliberately, "
            "do not re-sync reflexively."
        )
    typer.echo("store vs mirror: PASS (no witnessed node has changed)")
    typer.echo(f"seal vs mirror: {'DRIFTED' if seal_drift else 'PASS'}")
    idx_regressed = detect_index_regressions(doc.get("amendment_index", {}), AMENDMENTS)
    if idx_regressed:
        raise RuntimeError(f"AMENDMENT-INDEX REGRESSION: {idx_regressed}")
    n_ptr = sum(len(v) for v in doc.get("amendment_index", {}).values())
    typer.echo(
        f"amendment index: PASS ({n_ptr} forward pointers over "
        f"{len(doc.get('amendment_index', {}))} nodes)"
    )
    if added:
        typer.echo(f"not yet witnessed (additions pending sync): {added}")


if __name__ == "__main__":
    app()
