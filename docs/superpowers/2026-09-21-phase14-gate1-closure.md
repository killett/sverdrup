# Phase 14 — GATE 1 AND STAGE 1: THE CLOSURE RECORD

> **Owner pins 260–267, ruling PART 60** of
> `docs/superpowers/2026-07-27-owner-ruling-crn-sigma-rule0.md`, 2026-09-21.
>
> ⭐ **THIS RECORD SUPERSEDES THE GATE-1 PACK** (pin 209c). The pack posted the stage for
> decision; this records the decision. The pack's body is **unedited** — it gains a header
> pointer and nothing else.
>
> ⚠ **IT IS A RECORD OF A DECISION ALREADY MADE, NOT A DECISION PACK** (264c), so pin
> 212(b)'s two-reviewer requirement does not bind it. Its rows are verified against
> artifacts instead.
>
> ⛔ **CLOSING DOES NOT OPEN ANYTHING** (267). Nothing in Stage 2 opens. The Stage-2 spec
> is the next work and begins on the owner's word, not on this ruling. Tasks 14–21 stay
> halted under pin 88. No locked open, no c2 touch, no seal, no supersession.
> `operative_halo_deg()` stays untouched. The guard is not fixed.

**Read this before the Stage-2 spec is drafted.** Everything Stage 2 inherits from Stage 1
is in §4 and §5 below.

---

## 1. The accounting (pin 260), as ruled and never restated more strongly

Gate 1 closes **conditional on 262(a) reading true**. §3 records those reads; all four pass.

| # | spec item | ruled outcome |
|---|---|---|
| (a) | Anchor identity | the ruled accounting (**97b**): **TWO run and passed** (1, 5), **TWO cited and pre-ratified at Gate 0** (2, 4), **ONE proxy-passed with the era no-op DEFERRED**. ⛔ **Never "five green"** |
| (b) | Seam verdicts | mean **CLEAN** on the oracle (R=0.098103) and the pair (R=0.082738); **σ NOT_ESTABLISHED on both**; the σ question **OPEN** with its package (C-12); the 10×5 non-production-geometry sentence travels (pin 13) |
| (c) | Transfer readings | **FOUR** (97a), witnessed. Composition **INCOMPLETE**: no GroundTrack row (106). The three-class reading lives in the pack, not the store (197b) |
| (d) | Kernel decision | **WAIT**, option cell EMPTY (219) |
| (e) | Revisit verdict | **WAIT** (224). The aggregate is refused; anchors-only is priced and **not elected**, and 225(b)'s limit travels with it |
| (f) | Refresh election | **ELECTED, BUNDLED** (255). **No touch spent** |
| (g) | OSSE run decision (1-7, carried to the gate at 209b) | **WAIT** (250). Validity is prior to price; exit 251 |
| (h) | Zero locked-instrument opens / zero c2 / tally untouched | per **262** — see §3 |

## 2. Why a gate closes on three WAITs (pin 261, verbatim)

> **261. A RULED WAIT CLOSES A GATE ITEM; AN EMPTY QUESTION DOES NOT.** This does not relax
> 136(b).
> (a) 136(b) refused a question PRESENTED with an empty decision cell. Each WAIT here is
> an ANSWER ("no option is electable as the code stands", "the aggregate is
> refused", "validity is prior to price"), with its reason recorded and its exits
> named. The kernel's EMPTY cell is the OPTION cell; the DECISION cell reads WAIT.
> (b) The test for any future gate: a line discharges on a ruling with a reason AND a
> named exit. A WAIT with no named exit discharges nothing and closes nothing.
> (c) No WAIT here can discharge inside Stage 1, because every exit is Stage-2 work.
> Holding the gate open would not bring one closer; it would only halt Stage 2's
> spec.

## 3. The quantitative criterion, READ AT CLOSURE (pin 262, verbatim)

> **262. THE SPEC'S GATE-1 CRITERION IS READ AT CLOSURE. THE PER-RUN GUARD IS NOT ITS
> EVIDENCE.**
> (a) Discharge by direct reads. Each is failable and records the value that would
> have tripped it:
> (i)   the ceremony's ledger, phase14.locked_tally, keyed from
> locked_tier._TALLY_KEYS and not retyped: ABSENT or EMPTY. Any entry trips.
> (ii)  phase13.miost.c2_acceptance.c2_touch_tally == {"miost5": 3, "miost6": 1},
> the value witnessed in phase14.stage1.refresh_election and written by
> scripts/phase13_c2_touch.py. Any other value trips.
> (iii) mirror `check` PASS without re-sync: the legacy list unchanged at digest
> 9ea71b85…d806. A digest change trips.
> (iv)  The residual, stated and not hidden: the ceremony increments on clean
> completion only, so an open that crashed would leave no entry. Record by
> grep that no Stage-1 producer references SVERDRUP_PHASE14_TOUCH or
> SVERDRUP_INSITU_LOCKED. The grep and its hits (the owner saw none in
> scripts/) go in the record.
> (b) If ANY read trips, Gate 1 does NOT close. STOP after landing these pins verbatim
> and report the read. Nothing else in this ruling lands.
> (c) Under §7-11 the guard's Phase-14 half was UNRUN, not passed: it could not have
> tripped on a ceremony open. The guard and the pack's §1.11 are evidence for the
> legacy list only, and any record citing either for more says so from here on.
> No witnessed row is amended. The rows recorded what the guard said, accurately.
> (d) The guard is NOT fixed at closure. Changing its keys changes the byte-identity
> token, and re-scoring a witnessed row compares against its recorded token
> (phase14_stage1_run.py:4456-4458). A hasty fix could refuse re-scores of rows
> already witnessed. Land ONE strict-xfail test now: a store whose
> phase14.locked_tally moves between snapshot and assert must be refused, with the
> key taken from locked_tier's own constant (§7-12: the key has one origin). It
> flips when Stage 2 fixes the guard.
> (e) The F2 label is NOT amended at closure. Which ledger is authoritative is the
> open question, and relabelling before deciding it is guessing. Stage 2 obligation
> (263.10).

### 3.1 The reads

<!-- BEGIN DERIVED: reads -->
✅ **ALL FOUR READS PASS. NONE TRIPS.** Gate 1's one quantitative criterion is discharged by direct
read at closure, not by the per-run guard (262).

| read | what is read | value AT CLOSURE | what would have tripped it | verdict |
|---|---|---|---|---|
| **(i)** the ceremony's ledger | `phase14.locked_tally`, keyed from `locked_tier._TALLY_KEYS` and not retyped | `ABSENT (no such node in the store)` | any entry trips | ✅ passes |
| **(ii)** the c2 ledger | `phase13.miost.c2_acceptance.c2_touch_tally`, the value witnessed in `phase14.stage1.refresh_election` and written by `scripts/phase13_c2_touch.py` | `{"miost5": 3, "miost6": 1}` | any value other than {"miost5": 3, "miost6": 1} trips | ✅ passes |
| **(iii)** the legacy list, unchanged | `phase14_evidence_mirror.py check` PASS **without a re-sync**, and the mirrored digest of `c2_touch_tally` | `9ea71b8587f4031ecf8fabe9bdc8c08f3e761babf6206a75e88cd974fe69d806` | a digest not matching `9ea71b85…d806` trips | ✅ passes |
| **(iv)** the residual — no producer can open a ceremony | `rg -n 'SVERDRUP_PHASE14_TOUCH|SVERDRUP_INSITU_LOCKED' scripts/` | `NO HITS` | any hit in a Stage-1 producer trips | ✅ passes |
<!-- END DERIVED: reads -->

⚠ **WHAT THE GUARD DID AND DID NOT WITNESS** (262c, finding F1). The per-run zero-touch
guard snapshots `phase14.locked_n`; the ceremony writes `phase14.locked_tally`; **nothing
writes `locked_n` except the guard's own test fixture.** Mismatched from birth — ceremony
`9623b0f` (07-22), guard `f201c09` (07-25). So the guard's Phase-14 half was **UNRUN, not
passed**: it could not have tripped on a ceremony open. ⛔ **The guard and the pack's §1.11
are evidence for the LEGACY LIST ONLY**, and any record citing either for more says so from
here on. **No witnessed row is amended** — the rows recorded what the guard said,
accurately.

⛔ **THE GUARD IS NOT FIXED HERE** (262d). Changing its keys changes the byte-identity
token, and a re-score of a witnessed row compares against the token that row recorded
(`scripts/phase14_stage1_run.py:4456-4458`) — a hasty fix could **refuse re-scores of rows
already witnessed**. The defect is pinned instead by a **strict xfail**
(`tests/test_phase14_anchor_gate.py::test_tally_guard_detects_ceremony_ledger_mutation`),
whose key comes from `locked_tier._TALLY_KEYS`. It **XPASSes and therefore FAILS** the day
Stage 2 repoints the guard, which is what forces the marker off. The fix is obligation
**263.10**.

⛔ **THE F2 MIRROR LABEL IS NOT AMENDED HERE EITHER** (262e). The mirror calls the
top-level `c2_touch_tally` "the LOCKED-INSTRUMENT tally (see locked_tier.py)"; it is the
Phase-7 list, and the ledger `locked_tier.py` actually maintains is not mirrored at all.
Which ledger is authoritative is the open question, and **relabelling before deciding it is
guessing**.

## 4. The C1→2 contract AT CLOSURE

<!-- BEGIN DERIVED: contract -->
**14 contract lines, every one citing the witnessed node(s) that
carry it.** The status column is the owner's accounting (260), quoted. The
evidence column is RESOLVED AGAINST THE MIRROR at build time — node, field,
and what that field says today — so a line whose carrier moved cannot keep
reading as discharged.

| line | C1→2 deliverable | at-closure status (ruled) | witnessed carrier → what it says now | digest |
|---|---|---|---|---|
| **C-01** | Tiling machinery | COVERED — machinery run and green (260a's identity accounting) | `phase14.stage1.anchor_gate` → `pass`: `true`<br>`phase14.stage1.reachability_declarations` → `finding`: NOT hollow. Both golden-tile legs FIRED — mu by 6.23x and map rms by 4.10x over their recorded tolerances — and the scale check's discriminator is an… | `262bd85f755b…`<br>`c3b7b2cbd9dd…` |
| **C-02** | Measured seam behaviour — ORACLE verdict | 260(b) — mean CLEAN (R=0.098103); σ NOT_ESTABLISHED | `phase14.stage1.seam_rows` → `2.verdict`: CLEAN<br>`phase14.stage1.seam_rows` → `3.verdict`: NOT_ESTABLISHED (ensemble MC artifact — see diagnosis) | `273027937ead…`<br>`273027937ead…` |
| **C-03** | Measured seam behaviour — RUBRIC (pair) verdicts | 260(b) — mean CLEAN (R=0.082738); σ NOT_ESTABLISHED | `phase14.stage1.seam_rows` → `0.verdict`: CLEAN<br>`phase14.stage1.seam_rows` → `1.verdict`: NOT_ESTABLISHED (ensemble MC artifact — see diagnosis)<br>`phase14.stage1.sigma_rows_not_established` → `withheld.0`: *4 fields: prior_verdict, r_seam_sigma, route, verdict…* | `273027937ead…`<br>`273027937ead…`<br>`d0e8f5dd0adb…` |
| **C-04** | High-latitude kernel DECISION | 260(d) — WAIT, option cell EMPTY (219) | `phase14.stage1.kernel_pack` → `decision`: `null` (EMPTY)<br>`phase14.stage1.kernel_pack` → `decided_by`: owner, at Gate 1<br>`phase14.stage1.kernel_hull_deferred` → `label`: STAGE1-EVIDENCE | `4a26ac5dddb0…`<br>`4a26ac5dddb0…`<br>`6dbddcc3b9d3…` |
| **C-05** | …and its arithmetic | COVERED (arithmetic); the anisotropy INPUT is UNEVIDENCED (108) | `phase14.stage1.kernel_pack` → `arithmetic.in_box_cos_decrease`: `0.12796069210960692`<br>`phase14.stage1.kernel_pack` → `anisotropy_axis.status`: UNEVIDENCED at Stage 1 (owner pin 108a) | `4a26ac5dddb0…`<br>`4a26ac5dddb0…` |
| **C-06** | Per-tile frozen-config transfer readings (j3-side coverage/χ²) + µ/λx | 260(c) — FOUR, witnessed; composition INCOMPLETE, no GroundTrack row (106) | `phase14.stage1.tiles.kuroshio` → `scores.chi2_j3_validation.value`: `416.67773570223335`<br>`phase14.stage1.tiles.southern` → `scores.chi2_j3_validation.value`: `1637.4843984422607`<br>`phase14.stage1.tiles.equatorial` → `scores.chi2_j3_validation.value`: `40.31148110854822`<br>`phase14.stage1.tiles.quiet_gyre` → `scores.chi2_j3_validation.value`: `11.637874900560991` | `de6f3d946d79…`<br>`088719dceb49…`<br>`8880685fbf05…`<br>`5e296193ef8b…` |
| **C-07** | …raw-σ rows | PRODUCED — per-tile, never presented as calibrated (spec §6 policy a) | `phase14.stage1.tiles.kuroshio` → `scores.raw_sigma.label`: REFERENCE-ONLY, NOT CALIBRATED<br>`phase14.stage1.tiles.southern` → `scores.raw_sigma.label`: REFERENCE-ONLY, NOT CALIBRATED<br>`phase14.stage1.tiles.equatorial` → `scores.raw_sigma.label`: REFERENCE-ONLY, NOT CALIBRATED<br>`phase14.stage1.tiles.quiet_gyre` → `scores.raw_sigma.label`: REFERENCE-ONLY, NOT CALIBRATED | `de6f3d946d79…`<br>`088719dceb49…`<br>`8880685fbf05…`<br>`5e296193ef8b…` |
| **C-08** | …LABELLED scalar-s* reference rows | PRODUCED — labelled REFERENCE-ONLY, with the s*/χ² identity in-row (100) | `phase14.stage1.tiles.kuroshio` → `reference_row.label`: REFERENCE-ONLY, NOT CALIBRATED<br>`phase14.stage1.tiles.kuroshio` → `scores.s_star_chi2_identity.same_by_construction`: `true`<br>`phase14.stage1.tiles.kuroshio` → `scores.s_star_chi2_identity.not_corroboration`: agreement between these two fields is an IDENTITY, not independent confirmation: a consumer reading them as two witnesses is reading one number twice | `de6f3d946d79…`<br>`de6f3d946d79…`<br>`de6f3d946d79…` |
| **C-09** | Equatorial lane-0 baseline persisted under the frozen fold/eval frame | PRODUCED — manifest witnessed AT CREATION (96d) | `phase14.stage1.equatorial_lane0_manifest` → `witness_class`: WITNESSED_AT_CREATION<br>`phase14.stage1.equatorial_lane0_manifest` → `frozen_config_policy`: the equatorial baseline is recorded UNDER Stage 1's config policy (frozen signed config, §6), and the future increment comparison HOLDS THAT POLICY F… | `ca50faed7d14…`<br>`ca50faed7d14…` |
| **C-10** | Land-mask path exercised | PRODUCED — n_scored_points honest at the land-bearing tile | `phase14.stage1.tiles.kuroshio` → `scores.n_scored_points`: `89383` | `de6f3d946d79…` |
| **C-11** | The Gate-1 shipped-config election OUTCOME with its scope | 260(f) — DISCHARGED 2026-09-21: ELECTED, BUNDLED, no touch spent (255) | `phase14.stage1.refresh_election` → `outcome`: ELECTED<br>`phase14.stage1.refresh_election` → `scope`: Stage-2G assembly runs onward, as the spec named it (1-8)<br>`phase14.stage1.refresh_election` → `chain_and_touch.touch_spent_now`: `false` | `566a99fbe40a…`<br>`566a99fbe40a…`<br>`566a99fbe40a…` |
| **C-12** | The σ seam question is recorded OPEN, with the inheritance package NAMED | COVERED — OPEN, carried to Stage 2 (263.5) | `phase14.stage1.sigma_rows_not_established` → `consequence`: Stage 1 has NO attributable sigma-route seam verdict. The sigma seam question is UNANSWERED, not answered clean; the two mean-route CLEAN cells are t…<br>`phase14.stage1.seam_sigma_diagnosis` → `not_established`: *2 entries* | `d0e8f5dd0adb…`<br>`27be192e616b…` |
| **C-13** | STAGE 2 / 2G MAY NOT ASSUME σ SEAMS ARE CLEAN | COVERED — 'UNANSWERED, not answered clean' is the node's own wording | `phase14.stage1.sigma_rows_not_established` → `consequence`: Stage 1 has NO attributable sigma-route seam verdict. The sigma seam question is UNANSWERED, not answered clean; the two mean-route CLEAN cells are t…<br>`phase14.stage1.seam_sigma_diagnosis` → `question`: Is the PAIR/σ ELEVATED cell (R_seam_sigma = 1.1044) a seam artifact, or the ensemble Monte-Carlo noise floor of two independent m=100 member-std esti… | `d0e8f5dd0adb…`<br>`27be192e616b…` |
| **C-14** | The CRN defect travels forward as a PRODUCTION DEFECT | COVERED — OPEN, and Stage 2G cannot close while it stands (263.6) | `phase14.stage1.crn_production_defect_deferred` → `status`: OPEN. Deferred to Stage 2 by pin 84 (Branch B). NOT closed, NOT descoped.<br>`phase14.stage1.crn_production_defect_deferred` → `stage_2g_cannot_close_while_it_stands`: `true` | `76a0e9fbc5b4…`<br>`76a0e9fbc5b4…` |
<!-- END DERIVED: contract -->

⚠ **T12's C1→2 table is CLOSED** (197a). Its status column is as of 2026-08-31 except
C-11; this table is the at-closure status, and the two must not be merged.

## 5. What Stage 2 inherits (pin 263)

Named obligations, recorded here and **not** in T12's closed table.

| # | obligation | what it binds |
|---|---|---|
| **1** | **KERNEL** (219; 216/217b; 108) | No high-latitude option is electable **as the code stands**. Option 1 breaches ±66 (−66.13 at the core edge); options 2/3 are **inert** at the SO tile under the F-2 hull clamp. Exits: a smaller km scale, or a latitude-aware halo. ⭐ **A widened hull re-opens 2/3 — inert ≠ refused on merit.** The anisotropy axis is UNEVIDENCED. `operative_halo_deg()` stays untouched until a Stage-2 ruling |
| **2** | **REVISIT** (224-226) | Anchors-only (**12 solves / 296.2 h / 12.3 d**) is Stage 2's entry point, with 225(b)'s limit **verbatim in the row**. The screening lever is named and unpriced; if wanted, **it is a measurement** |
| **3** | **OSSE** (250/251) | Truth is a **free-running nature run**, never a reanalysis that assimilates the constellations under test. Common-span design and replication are **OPEN**. T8 v3 is **withdrawn** as a pricing deliverable |
| **4** | **REFRESH** (255-258) | BUNDLED with 2G's chain and touch. δ_j3 := δ_j2n is **PROVISIONAL** (256). e10's replacement holdout is chosen by **fork C's criteria in order** and **SEALED before 2G runs** (257). The 258 firewall travels in its own words |
| **5** | **σ SEAMS** (C-12/C-13) | **OPEN.** Stage 2/2G **may not assume σ seams are clean** |
| **6** | **CRN** (87/C-14) | A **production defect**. Stage 2G **cannot close while it stands** |
| **7** | **GROUNDTRACK** (106) | No per-tile row, so transfer composition is **INCOMPLETE** |
| **8** | **ATTRIBUTION** | The source-delta readout has not landed. The **bridge caveat stands** on every cross-lineage reading (§7-8) |
| **9** | **POWER** (132) | An interruption still costs the in-flight window (**~3.44 h**) |
| **10** | **LEDGERS** (262) | Before 2G spends the program's **first locked open** (§5.4), Stage 2 **names ONE ledger** for it, **fixes the guard** to read that ledger, **mirrors and witnesses** the ledger, and **amends the F2 label** under pin 64 |
| **11** | **TEST ISOLATION** | Four `seam_pair` CLI tests fail **only in combined runs** (`tier1_eligible` reads live `/proc/meminfo`). **Unfixed** |
| **12** | **TASKS 14-21** | Halted under pin 88. **READY ≠ RUNNABLE.** The Stage-2 spec opens or re-homes them; nothing else does |

### 5.1 FOUND-BY-SWEEP (E-SWEEP, pin 263)

The owner ordered a sweep of the ruling doc, the pack, the kernel and OSSE records, and the
store for Stage 1's own words — DEFERRED, OPEN, WAIT, PROVISIONAL, "Stage 2's", "before 2G"
— against the owner's own list, because the owner had just missed a frame (F3).

⛔ **These are RECORDED, NOT MERGED into 1–12, and NOT ACTED ON.** None of them is a
blocker on closure; each is a Stage-1 deferral whose consumer is Stage 2 and which items
1–12 do not name.

| # | found | source line | why it is not already in 1–12 |
|---|---|---|---|
| **S1** | **The era no-op is DEFERRED** to the stage that introduces era-keyed code (Stage 2, spec §3.1 fork E). Anchor check 3 is proxy-passed on surface identity only | `phase14.stage1.anchor_gate` → `checks`/`accounting`; pack row 3; ruling PART 60 260(a) | 260(a) names it **in the accounting**; no inheritance item carries it forward as Stage-2 work |
| **S2** | **Gate 0 closed WITH the cloud leg open** — restructured as a ladder-enforced precondition on **first Tier-2 production use**; C0→1 ships same-host tolerances + CRN-EQUAL | `phase14.stage1.anchor_gate` → Gate-0 ruling item 2 (in-node) | A **Gate-0** carry-forward that lands on Stage 2's first Tier-2 production use; 1–12 are Stage-1 items |
| **S3** | **The seam-rubric amendment is DEFERRED to ONE sealed version after T14/T15** (pin 45/45d), CRN-state-conditional | `phase14.stage1.seam_rows` → *"the rubric amendment is DEFERRED to one sealed version after T14/T15 (owner pin 45)"*; ruling line 18 (T17) | Item 12 halts **task 17**; the amendment's **substance** (one sealed version, CRN-state-conditional) is not named |
| **S4** | **The ensemble-settling measurement is deferred to T17**, to be sealed once against the CRN-paired configuration **T14 creates** | `phase14.stage1.ensemble_settling_measurement` (in-node) | Same shape as S3: the task is halted by 12, the measurement's **sealing dependency on T14** is not named |
| **S5** | **An artifact's witness interval stays OPEN** — the 2026-07-28 capture closes **future** substitution only | `phase14.stage1.anchor_gate_artifact_sha_reconciliation` (in-node) | A standing witness limitation on a Stage-1 artifact; no item carries it |
| **S6** | **Gauge consumption grid: DEFERRED** (a Gate-0 attention item) | `phase14.stage0.gauges` → *"DEFERRED to consumption grid (Gate-0 attention item)"* | Stage-**0** deferral still unresolved at Stage-1 close; 1–12 do not reach back to it |

**Not swept into the table, and why:** the `rho_model_*` nodes (pins 73/74/77) and the
headroom nodes are the substance of **tasks 19–21**, which item 12 halts by name — recording
them again would be duplication, not a finding.

---

## 6. What this record does not do

- **No evidence-store node** (264e). The store holds measurements and firewalled hypotheses
  (197b); **a closure is a ruling**. `refresh_election` had a node because C-11 named one;
  **no contract line names one here.** The mirror stays at **53 nodes**.
- **Nothing seals.** The single authorised supersession stays **UNSPENT**.
- **The posted pack's body and T12's table rows stay untouched** — both gain a header
  pointer only, with the body byte-identical below (264d).
- **Gate 1 closing is not Stage 2 opening** (267).
