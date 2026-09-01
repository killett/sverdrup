# Stage-1 C1→2 contract coverage table (T12 — precondition on T9)

> **⛔ STOP CONDITION TRIGGERED — ONE UNASSIGNED CONTRACT ITEM FOUND.**
> The C1→2 line **"the Gate-1 shipped-config election OUTCOME with its scope"**
> is assigned to **no task AC in the Stage-1 plan**. T9 pack item (7) produces
> the *presentation* (presumptive rule, δ_j3 := δ_j2n, scope = Stage-2G assembly
> onward) with the decision cell EMPTY, and T9's last AC is **"STOP after
> posting — Gate 1 is the owner's."** Nothing records the owner's answer, or its
> scope, into the artifact Stage 2 inherits. The contract deliverable is the
> **outcome**, not the presentation of the question. See **Finding 1**. Per the
> standing stop condition (plan T11/T12 AC), this surfaces to the owner before
> T9 assembles. Findings 2–3 are same-neighbourhood defects the same ruling
> should resolve.

**Status:** the walk is COMPLETE — both directions, every C1→2 deliverable in
spec §3.2, every Stage-1 task AC that claims one. This is the T11 method applied
a second time; T11's §5 scope note is the map of what T11 did **not** cover, and
this table covers exactly that: the *contract* obligations, not the *sealed
instrument* obligations.

**Sources walked (verbatim, this tree):**
- `docs/superpowers/specs/2026-07-21-phase14-scaling-program-design.md` §3.2
  (the C1→2 line), §3.1 (stage map), §6 (Stage-1 scope + config policy a/b/c)
- `docs/superpowers/plans/2026-07-23-phase14-stage1-spatial-2017.md` and its
  `.tasks.json` (T0–T13, T22 — the ACs as they stand at HEAD, pins folded)
- `docs/superpowers/2026-07-27-owner-ruling-crn-sigma-rule0.md`
  (pins 37, 45, 84, 86, 87, 97, 106, 108, 124, 130–132)
- `docs/superpowers/2026-07-29-phase14-stage1-closure-map.md` §1, §3
  (per-tile vs cross-tile marking; the four produced seam rows)
- `docs/superpowers/2026-07-25-phase14-stage1-instrument-coverage.md` (T11 —
  the sibling table; its Findings 1–4 are ruled and their state is carried below)

**Contract-item convention.** `C-01`…`C-14` segment the C1→2 sentence in order;
`C-12`…`C-14` are the three lines **added to the contract by owner ruling**
(pins 86a, 86b/37c, 87) after the spec text was written. Every normative noun
phrase in the C1→2 sentence sits inside exactly one row.

**Assignment, not execution** (the T11 convention, restated because it decides
how every cell below reads): a COVERED cell means **a task AC exists whose
acceptance discharges the contract line**. It does not certify the AC has run.
T5 has not run — it is blocked on the leg-1 gate's item 4 (the owner declaring
the box back and stable, R1) — so C-06…C-10 are **assigned and unrun**, which is
a different state from unassigned and is marked as such.

---

## 1. FORWARD — C1→2 deliverable → discharging task+AC (or explicit deferral)

| ID | C1→2 deliverable (spec §3.2) | Discharged by | Status |
|---|---|---|---|
| C-01 | **Tiling machinery** | T1 AC-1/2/3 (registry with per-tile `source`; anchor frame CONSUMED not reconstructed — `frame_grid(registry_frame("anchor"),0.2) == frame_grid(anchor_frame(),0.2)`; seam frames pinned as pin-3 frozensets with solve bboxes test-pinned); T4 AC-3 (blend via `assemble`, partition-of-unity, zero-overlap refusal); **identity underwritten by** T3 check 1 (the signed box through the generalized path, four routes) and check 5 (score-level) | COVERED (machinery RUN and green: T1, T3, T4 complete) |
| C-02 | **Measured seam behaviour — ORACLE verdict** | T4 ORACLE AC (blended field vs seamless-anchor truth on the 2·overlap strip; `seam_read` validity guard; D_int from the SEAMLESS solve per rubric R-19 — T11 Finding 2, owner-adopted) | COVERED **and produced**: mean `R=0.098103` **CLEAN**; σ `R=0.648763` **NOT_ESTABLISHED**. Ships with the 10×5 non-production-geometry sentence (pin 13) |
| C-03 | **Measured seam behaviour — RUBRIC (pair) verdicts** | T4 PRIMARY PAIR READ AC (`delta = field_A − field_B`, each tile's own solve, BEFORE blending; 2·overlap strip, owner-ruled domain — T11 Finding 1, owner-adopted); Rule-0 floor attributability attaches to the pair read FIRST; machinery T0 AC-1/2/3 + T10 (σ route, same pure functions); T13 pin-45b (both σ rows WITHHELD by diagnosis, not verdicted) | COVERED **and produced**: mean `R=0.082738` **CLEAN**; σ `R=1.104435` **NOT_ESTABLISHED**. **Discharge is on REPORTING, not on answering (pin 84)** — see C-12 and Finding 4 |
| C-04 | **High-latitude kernel DECISION** | T6 AC (three options — km-space kernels / lat-varying degree scales / Paciorek — each with what changes, what stays identical, halo auto-follow, ±66° breach column); **decision cell EMPTY, owner decides at Gate 1**; presented via T9 pack item (4) | COVERED as a decision *pack*; the decision itself is the owner's at Gate 1 (contract-legal: the line names the decision, and Gate 1 is where Stage 1 makes it) |
| C-05 | **…and its arithmetic** | T6 AC (f-range table: \|f\| at 38°N vs 55°S vs global; cos-φ ratios hand-value-pinned; the "~13% in-box → ~2–3× poleward" sentence made numeric); T6 AC (box-scale negative NOT cited as transferring — test-pinned string absence) | COVERED (arithmetic), **but its measured-anisotropy INPUT is degraded** — see **Finding 3** (pin 108: the anisotropy axis is UNEVIDENCED, not "limited") |
| C-06 | **Per-tile frozen-config transfer readings — j3-side coverage/χ² (the measurement that motivates Stage-2 calibration)** + µ/λx | T5 AC-1 (four rows under `phase14.stage1.tiles.{equatorial,southern,quiet_gyre,kuroshio}`: µ/λx/coverage/χ² j3-validation, seal sha, `bridge_caveat` verbatim); machinery T1 evidence AC (scores block per spec §6 policy (b)); **count test-pinned at FOUR against the store (pin 97a)** — `seam_n`/`seam_s` are solve records, the anchor is the identity subject | ASSIGNED, **UNRUN** (T5 blocked on owner R1). **Composition ships INCOMPLETE** — no GroundTrack row at any of the four tiles (pin 106) — see **Finding 2** |
| C-07 | **…raw-σ rows** | T5 AC-1 (per-tile raw posterior σ row; spec §6 policy (a): never presented as calibrated). Per-tile by construction — no cross-tile differencing (closure map §1) | ASSIGNED, UNRUN |
| C-08 | **…LABELED scalar-s\* reference rows** | T5 AC-1 (labelled reference row per tile); T1 evidence AC pins the label and the `bridge_caveat` exact string; **`S_STAR_CHI2_IDENTITY` schema field (pin 100)** states the shared expression, `same_by_construction`, and `not_corroboration` in-row, and `build_scores_block` RAISES on divergence (pin 100c) with `preflight_scores_construction()` exercising the construction before either gate (pin 103a) | ASSIGNED, UNRUN (schema + invariant landed and test-pinned) |
| C-09 | **Equatorial lane-0 baseline persisted under the frozen fold/eval frame** | T5 equatorial-persistence AC (fork-b pin 1: maps + `evidence_pack.json` + `fold_eval_frame.json` + `lane0_manifest.json` with per-file sha+size, recorded at `phase14.stage1.equatorial_lane0_manifest`); machinery LANDED at T5d — `persist_lane0_bundle` / `record_lane0_manifest`, manifest node in the evidence mirror's `MIRRORED` set (96c), fork-b pin 2 verbatim, pin-67 class `WITNESSED_AT_CREATION`, and the **instrument composition** recorded (pin 107) so a later wave-increment run cannot be compared blind | ASSIGNED, UNRUN (mirror shows the node `PENDING (registered, not yet written)` — correct pre-run state) |
| C-10 | **Land-mask path exercised** | T5 kuroshio AC (dropped-land handling in framing/scoring; `n_scored_points` honest; all-land core refusal surfaced not swallowed); machinery LANDED at T5d — `land_mask_exercise.kuroshio.<era>` records all three counts (framed obs / scored points / calibration points) **with their gap** | ASSIGNED, UNRUN. Partially de-risked already: pin 89's kuroshio probe converged **with the land-mask path intact** |
| C-11 | **The Gate-1 shipped-config election OUTCOME with its scope** | T9 pack item (7) produces the **presentation** (presumptive rule verbatim: instrument-class match, δ_j3 := δ_j2n (Poseidon-series); own chain + touch if elected; scope = Stage-2G assembly runs onward). **No AC records the OUTCOME** — T9's terminal AC is "STOP after posting" | **UNASSIGNED → FINDING 1 (STOP)** |
| C-12 | **(pin 86a — added to the contract) The σ seam question is recorded OPEN, with the inheritance package NAMED** | This table, §2 below (the package enumerated, not referenced); T9 pack item (12); T13 pin-45b (the withholding cells as produced); the closure map §3 (the branch-B reading the owner adopted at pin 84) | COVERED — §2 is the discharge |
| C-13 | **(pin 86b / pin 37c — added to the contract) STAGE 2 / 2G MAY NOT ASSUME σ SEAMS ARE CLEAN** | This table, §2.6 — **carried as a contract line item in those words**; T9 pack item (12) | COVERED |
| C-14 | **(pin 87 — added to the contract) The CRN defect travels forward as a PRODUCTION DEFECT** | `phase14.stage1.crn_production_defect_deferred` (recorded in those words); T9 pack item (13); pin 124(a)'s attestation wording — "zero locked opens, **one deferred production defect named at `crn_production_defect_deferred`**" — so the attestation cannot read as a clean bill | COVERED |

**Deferred-to-Stage-2 cells:** none in this table. Every C1→2 line is a Stage-1
obligation by construction — a deliverable the contract hands **forward**, so
deferring one would be deferring the handoff itself. Where a Stage-1 line is
weaker than its Stage-2 consumer would like (C-03's σ half, C-05's anisotropy
input, C-06's composition), that is recorded as a **stated weakening carried
into the contract**, never as a deferral.

---

## 2. The inheritance package, ENUMERATED (pin 86a — the C-12 discharge)

Named here, not referenced. This is the σ seam question as Stage 2 inherits it.

**2.1 Mechanism.** `obs_noise` is keyed on **OBSERVATION identity**; `coef_noise`
on **ELEMENT identity**; both draw from a **shared root**. Identical strip
observations therefore receive identical ε′ realisations — the two tiles'
ensembles are positively correlated exactly where the seam metric differences
them.

**2.2 Both channels quantified.**
- ρ = **5.17 %** (`phase14.stage1.seam_shared_observation_channel`: on the
  evaluation strip the two tiles' observation sets are IDENTICAL — 14,876 each,
  Jaccard 1.0000; whole-frame overlap 68 %).
- matched-member field correlation **r = 0.2523**.
- **ρ ≈ r², with its 23 % residual UNRESOLVED** (pin 74): curvature would imply a
  third channel; a stable offset implies higher-order terms or non-Gaussianity.
  The residual is carried as open, not rounded away.

**2.3 Reachability condition and its m requirement.** `F_ens / D_int_σ = 1.1356`
at m = 100, so `factor × F_ens < clean_max × D_int_σ` **fails for EVERY factor
≥ 1.00**. Minimum m for a CLEAN cell is **129 / 137 / 148** at factor
1.00 / 1.03 / 1.07. *A σ CLEAN verdict was not reachable at Stage-1's m — which
is why "looked and could not attribute" is a result, not a blank.*

**2.4 Latitude non-uniformity (pin 31b).** `basis_domain` is in **km** while
tiles are placed in **degrees**, so the km offset for a fixed degree spacing
varies with latitude: **whether adjacent lattices coincide varies ACROSS THE
GRID.** A uniform bias would be characterisable; a latitude-varying correlation
structure writes artificial structure into σ that a reader will take as physics.

**2.5 The ρ model with its validated span DECLARED (pin 78).**
`kind: validation`; `validated_range: [0.0, 0.2523]`;
`application_range: [0.0, 0.9]`; **`extrapolation_declared`** — the magnitude
prediction `T_cross ≈ E[T](m)·√(1−r²)` is an **extrapolation** pending Stage-2
task 21's high-r points or pin 77(c)'s measured-ρ branch. The **direction**
prediction (pin 68b) is **not** an extrapolation and is labelled separately, so
the declaration does not weaken the part that stands on its own.

**2.6 CONTRACT LINE (pin 37c, in these words):**
> **Stage 2 / 2G MAY NOT ASSUME σ SEAMS ARE CLEAN.**

Stage 1 delivers **two attributable CLEAN mean verdicts and two σ cells
NOT_ESTABLISHED with the mechanism documented**. The rubric was pre-registered
with a withholding cell **so that "looked and could not attribute" is a RESULT**;
this is that cell used as designed, **not a blank**. Pin 37(b)'s firewall holds:
the diagnosis-derived bound must **not** sit adjacent to the UNMEASURED rows in
any form a reader could take as a verdict.

**2.7 CONTRACT LINE (pin 87, in these words):** the manufactured σ gradient at
tile boundaries is **a property of the shipped system, not of an instrument** —
a **PRODUCTION DEFECT**, recorded at
`phase14.stage1.crn_production_defect_deferred`, and **Stage 2G CANNOT CLOSE
while it stands.** Deferral is honest because the defect travels forward named
and costed; the only Stage-1 surface it touches is the single registry
adjacency, which T4 already measured.

---

## 3. REVERSE — every Stage-1 AC claiming a contract item → its contract line

| Task AC claim | Contract line | Note |
|---|---|---|
| T1 AC-1 registry + per-tile source map; unknown-tile and `--source` refusals | C-01 | The source map is pinned, not an option |
| T1 AC-2 anchor frame CONSUMED (`frame_grid` equality) | C-01 | The gate-5 substrate; a reconstructed frame would break identity |
| T1 AC-3 seam frames pinned (pin-3 frozensets; bboxes test-pinned) | C-01, C-02, C-03 | The pair the seam lines are measured on |
| T1 evidence AC (seal sha quoted; refuses unsealed; scores block per policy (b) incl. λx) | C-06, C-07, C-08 | Machinery for the readings |
| T1 `bridge_caveat` verbatim for cross-lineage tiles | C-06 | The delta carries its own provenance and disclaims transfer (review pin 7) |
| T2 probe (quiet_gyre, m=1, one window, PROBE-labelled, never scored) + `measured_vs_model` | **No C1→2 line** | Sizing belongs to **C0→1** ("validated tile-scale sizing model + spend table"). Benign orphan — Finding 6 |
| T3 checks 1–5 + `phase14.stage1.gate5` constants | C-01 (supporting) | The anchor gate is a **Gate-1 item**, not a C1→2 deliverable; it underwrites C-01's identity claim. Presented as the **RULED ACCOUNTING**, never "five green" (pin 97b) |
| T4 AC-2 like-for-like (both dc2021a, frozen config, m=100, anchor roots) | C-02 | The oracle compares like against like |
| T4 AC-3 blend via `assemble` | C-01, C-02 | |
| T4 PRIMARY PAIR READ AC (pre-blend A−B, 2·overlap strip) | C-03 | T11 Finding 1, owner-adopted |
| T4 ORACLE AC (blend vs seamless; seamless-solve D_int) | C-02 | T11 Finding 2, owner-adopted — the two D_int denominators are pinned adjacent and are **different by design** |
| T4 Rule-0 AC (floor F, 3×F, UNMEASURED marking, never-CLEAN, one-sidedness) | C-02, C-03 | Attaches to the PAIR read first (Finding 1c) |
| T4 σ AC + recording AC (`phase14.stage1.seam_rows`, `{pair, era, field_kind, rms_delta, d_int, r_seam, verdict}` + resolution in-row) | C-03, C-12 | T11 Finding 3, owner-adopted in full incl. namespace |
| T4 geometry-caveat AC (pin 13 — 10×5, NOT D1 production geometry) | C-02, C-03 | A scope statement **on** the contract line, not a separate deliverable |
| T5 AC-1 four rows (µ/λx/coverage/χ² + raw-σ + labelled s\* + caveat + seal sha) | C-06, C-07, C-08 | Count test-pinned at FOUR against the store (pin 97a) |
| T5 GroundTrack-wiring AC (`Registry.applicable` + `build_report_rows`, zero new surfaces) | C-06 (composition) | Landed at T5c; **produces recorded ABSENCES at all four tiles** — Finding 2 |
| T5 equatorial-persistence AC (maps + pack + frozen fold/eval frame + manifest) | C-09 | |
| T5 southern AC (per-direction spectral/track diagnostics for T6) | C-05 (input) | The per-direction **track** half is a recorded absence — Finding 3 |
| T5 kuroshio AC (land-mask assertions, honest `n_scored_points`) | C-10 | |
| T5 interpretation-withholding AC (row keys test-pinned as EXACTLY the schema set) | C-06, C-07, C-08 | Structural: no free-prose field exists to interpret in (review pins 8/17) |
| T6 AC f-range table + cos-φ hand-values | C-05 | |
| T6 AC three options + halo auto-follow + ±66° breach column | C-04 | Decision cell empty — owner at Gate 1 |
| T6 AC "box-scale negative NOT cited as transferring" (test-pinned) | C-04, C-05 | |
| T7 revisit lanes (per-tile, two bands, report-only, promotion sentence verbatim) | **No C1→2 line** | A **Gate-1 item** and a Stage-2/fork input; the contract sentence names no revisit deliverable. Benign orphan — Finding 6 |
| T8 OSSE pricing + strongest value case; decision cell empty | **No C1→2 line** | Gate-1 item; the OSSE election is fork-f's, not C1→2's. Benign orphan — Finding 6 |
| T9 pack item (3) FOUR transfer readings | C-06, C-07, C-08 | **Corrected orphan:** the AC formerly said "six", which claimed more than the contract line yields; pin 97(a) fixed it to FOUR and test-pinned the count |
| T9 pack item (7) refresh-election presentation | C-11 (presentation half only) | **The outcome half is unassigned — Finding 1** |
| T9 pack item (10) the T11 sealed-instrument coverage table | T11 closure | **No slot names THIS table — Finding 5** |
| T9 pack items (12)/(13) | C-12, C-13, C-14 | |
| T10 AC-1..4 (σ pair beside mean; same pure functions; sentinel covers both routes; guard on both) | C-03 | The σ field kind of the rubric verdict |
| T11 (sealed-instrument coverage table) | **No C1→2 line** | A plan-level precondition (review pin 22), not a contract deliverable. Its output is a Gate-1 pack item |
| T12 (this table) | **No C1→2 line** | Review pin 25; a precondition on T9 |
| T13 pin-45b (both σ rows WITHHELD, mechanism recorded) | C-03, C-12 | The withholding cell used as designed |
| T13 pin-49 (`ensemble_floor` / `sigma_level_rms` marked not-verdict-bearing) | C-12 | Keeps the diagnosis-derived bound off the verdict surface (pin 37b) |

No task AC claims a C1→2 deliverable that does not exist in the contract
sentence. The four extra-contract ACs above (T2, T7, T8, T11) are Gate-1 or
sibling-contract obligations, each traceable to its own line — recorded as
Finding 6 (LOW, no action) so the reverse walk is exhaustive.

---

## 4. FINDINGS

**Finding 1 — CRITICAL (STOP-condition trigger): the shipped-config election
OUTCOME has no producer.**
C-11 names *"the Gate-1 shipped-config election **outcome** with its scope"*.
The plan produces the **question**: T9 pack item (7) presents the presumptive
rule verbatim (instrument-class match, δ_j3 := δ_j2n, own chain + touch if
elected, scope = Stage-2G assembly onward) with the decision cell empty, and
T9's terminal AC is **"STOP after posting — Gate 1 is the owner's."** After the
owner rules, **no AC writes the outcome or its scope anywhere** — not to an
evidence node, not into the contract handoff. Stage 2 would inherit a contract
line discharged by a presentation of an undecided question. This is the same
shape as T11's Finding 1: the deliverable is the *reading*, and only the
*machinery around it* was assigned.
*Remedy shape (owner/planner ruling, not executor's): give T9 a post-gate
recording AC — the ruled outcome + its scope recorded at, e.g.,
`phase14.stage1.refresh_election` with the ruling cited by sha/section — or
open a one-AC closing task that runs after the Gate-1 walk. T12 is `blockedBy
[]` and upstream of T9 in the plan order, so the gate holds if this is ruled
before T9 assembles.*

**Finding 2 — HIGH (carried, already ruled): C-06's reading composition ships
INCOMPLETE.**
Spec §6 policy (b) pins the transfer-reading composition as *"per-tile
j3-validation µ/λx/coverage/χ² at frozen config + **reference-free rows** + seam
rubric verdicts."* The reference-free evaluator family is GroundTrack, and
**none of the four diverse tiles carries a GroundTrack row**: the only
orbit-geometry artifact that exists is derived over the CHALLENGE box, and
deriving per-tile geometry from the CMEMS dailies is a NEW PRODUCER, which
criterion 2 forbids (pin 106a). T5c wires the applicability evaluation through
the existing `Registry.applicable` + `build_report_rows` path and records a
**checkable absence** (`geometry_artifact_expected_at` / `_present`) instead of
a row. This is **ruled and accepted for Stage 1 as a named gap**, but the
consequences bind the contract:
- T9 states the incomplete composition **in the transfer-readings section where
  the numbers are** (pin 106c), and the record calls it what it is: **a real
  weakening** (pin 106e).
- Per-tile orbit geometry is carried in this table's C1→2 handoff as **named
  Stage-2 work** with the 0.410→0.331 context (pin 106d).
- The southern tile's spectral slope remains a **degraded estimand** regardless
  of pin 112's lookup fix — that fix recovered the anchor and the seam pair only.
*This closes T11's Finding 4 (GroundTrack standing-row breadth): the ambiguous
sentence was ruled, and the answer is a decision, not an accident.*

**Finding 3 — MEDIUM (carried, already ruled): C-05's measured-anisotropy input
is UNEVIDENCED on the directional axis.**
T6's arithmetic (C-05) is fully assigned, but its *measured* input is not what
the spec's risk line anticipated. T5d records
`anisotropy_inputs.southern.<era>` as **grid anisotropy computed from the tile's
own axes (`dy/dx ≈ 1.72` at ~54.5°S) + a CITED SpectralFidelity row**; the
**per-direction TRACK half is a recorded absence**, because it needs
ORBIT_GEOMETRY, which pin 106 establishes is challenge-box scoped. Pin 108 rules
the axis **UNEVIDENCED — not "limited"**. Contract consequence, carried
explicitly: **any kernel option whose case rests on directional sampling is
UNSUPPORTED BY STAGE-1 EVIDENCE**, and if the option set cannot be separated
without it, that is a **WAIT that comes to the owner**, not a decision T6 makes.
T6 must not present its arithmetic as though per-direction sampling were
measured.

**Finding 4 — MEDIUM (ruled, recorded here so the contract reads correctly):
C-03 discharges on REPORTING, not on answering.**
The contract line "measured seam behavior (oracle + rubric verdicts)" is
discharged by **two attributable CLEAN mean verdicts plus two σ cells
NOT_ESTABLISHED with the mechanism documented** (pin 84, branch B). A reader who
takes "verdicts" to mean "four established verdicts" would read Stage 1 as
having answered the σ question. It has not: **Stage 1 has NO attributable
σ-route seam verdict** (pin 97c). §2 above is the mechanism documentation the
discharge depends on; §2.6 and §2.7 are the contract lines that keep the
unanswered half from being inherited as answered.

**Finding 5 — MEDIUM: this table has no slot in the Gate-1 pack.**
T12's own AC requires it *"posted in the Gate-1 pack BESIDE the instrument
table"*, but T9's pack list (items 1–13) names only **item (10) the T11
sealed-instrument coverage table**. A required deliverable with no receiving
slot is how the T11 table itself nearly went unposted.
*Remedy shape (one AC edit, same ruling as Finding 1): T9 pack item (10) becomes
"the T11 sealed-instrument coverage table **and the T12 C1→2 contract coverage
table**", or a new item (14) is added.*

**Finding 6 — LOW (no action): four extra-contract Stage-1 obligations.**
T2 (sizing probe — belongs to C0→1's sizing model), T7 (Phase-10 revisit — a
Gate-1 item and a fork input), T8 (OSSE pricing — fork-f's election) and T11
(sealed-instrument coverage — review pin 22) discharge **no C1→2 line**. All
four are real obligations under other headings, and none claims contract
authority. Recorded so the reverse walk is exhaustive. T3 (anchor identity gate)
is likewise a Gate-1 item rather than a contract deliverable, but it is *not* an
orphan: it underwrites C-01.

---

## 5. Honest-scope note — what this table does NOT cover, and what it adds to T11

**What it adds (the T11 §5 map, answered):** T11 covered the **sealed
instruments** — the seam rubric's normative clauses (R-01…R-24) and every
`instrument_configs()` key. It explicitly excluded *"non-instrument spec
constraints … the spend ladder, ±66° discipline, locked-tally/zero-touch rules,
source map, frame conventions, bridge-caveat wording, interpretation
withholding"*, calling them plan/spec obligations tracked by their own ACs. This
table covers the **C1→2 contract obligations** — what Stage 1 owes Stage 2 —
including several of those excluded items where they appear as contract content
(source map and frame conventions under C-01; bridge-caveat wording and
interpretation withholding under C-06…C-08).

**What it still does NOT cover:**
- **The other three contracts.** C0→1 (Stage-0's handoff, already consumed),
  C2→2G and C2G→3 are not walked here. Each needs its own walk in its own stage
  — including the deliverables this table hands **forward** as named Stage-2
  work (Finding 2's per-tile orbit geometry; §2's whole inheritance package).
- **Assignment, not execution.** As in T11: a COVERED cell means an AC exists.
  C-06…C-10 are assigned to a task (T5) that has not run. Execution evidence
  lives in the per-task close records and the Gate-1 pack.
- **The Gate-1 pack's own completeness.** This table checks that every contract
  line has a producer, not that the pack's thirteen items are individually
  well-formed. Finding 5 is the one pack-shape defect that surfaced *because* a
  contract-side deliverable pointed at it.
- **The contract sentence is the unit.** Segmentation C-01…C-11 is this table's
  reading of spec §3.2's C1→2 sentence, exhaustive over its noun phrases;
  C-12…C-14 are owner-added lines. A future amendment to §3.2 — or a further
  owner-added line — invalidates the segmentation and requires a re-walk.
- **Stage-2 σ chain excluded by design.** T14–T21 are `[STAGE 2]` under pin 88's
  halt; they appear here only as the destination of §2's inheritance package,
  never as producers of a Stage-1 contract line.

## 6. Verify

- `rg -c 'T[0-9]+' docs/superpowers/2026-08-31-phase14-stage1-c1to2-coverage.md`
  → nonzero (task citations present).
- Spot-check, **run**: every task number cited here exists. T0–T12 exist as
  `### Task N:` headings in
  `docs/superpowers/plans/2026-07-23-phase14-stage1-spatial-2017.md`. **T13 and
  T22 exist only in the co-located tracker**
  (`…spatial-2017.md.tasks.json`, ids 13 and 22) — both were created by owner
  ruling after the plan prose was written (T13 by pin 45's restructure, T22 by
  pin 85's Tier-2 gate), and the tracker is the source of task state. Stated
  here so a later reader running T11's heading-only spot-check does not read
  two live tasks as phantom citations.
- The four seam numbers in C-02/C-03 reproduce
  `docs/superpowers/2026-07-29-phase14-stage1-closure-map.md` §3 exactly.
