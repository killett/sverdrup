# Stage-1 stale-criteria sweep (T5–T9) — owner pin 91(a)

**REPORT ONLY.** No edits, no new tasks, no scope growth — pin 88's halt lifted for the
deliverable path, not for scope growth (pin 91a). This document is the hard stop
condition on leg 1: **leg 1 does not launch until this is in front of the owner**
(pin 91b).

**Method (pin 91c):** the T11 coverage-walk pointed at acceptance criteria instead of
rubric clauses. Each of T5–T9's acceptance criteria was walked against every ruling
landed since `3264524` (the Stage-1 plan commit) — ruling doc PARTs 1–20, pins 31–93,
plus the plan-level pins ruled 2026-07-25 (pin 2 frame convention, pin 12 box election)
and the anchor-gate ruling of 2026-07-26.

**Result: 11 stale criteria across 4 of the 5 tasks.** Pin 91c predicted "more than
one"; the count is 11. Two were already known entering the sweep (marked ✓ KNOWN).
Severity is the executor's reading and is offered for triage, not as a ruling.

---

## Summary table

| # | Task | Criterion | What changed the premise | Severity |
|---|------|-----------|--------------------------|----------|
| 1 | T5 | criterion 8 — pin-12 refusal | pin 12 ruled 2026-07-25; pin 90 | ✓ KNOWN — discharged |
| 2 | T5 | Files line ("run already does these") | `_solve_leg` is a stub; pin 92 | ✓ KNOWN — ratified |
| 3 | T5 | "RAM predicate before each" | E-16 §2 replaced the Tier-1 predicate | HIGH — blocks launch |
| 4 | T5 | "raw-σ" row, uncaveated | pins 45(b), 84, 86, 87 | HIGH |
| 5 | T5 | `build_evidence_row` "EXACTLY the schema set" | pin 42 required schema fields; pin 78 | MEDIUM |
| 6 | T5 | equatorial `lane0_manifest.json` shas | pins 56, 58, 64, 67 (mirror + witnesses) | MEDIUM |
| 7 | T6 | ±66 breach "either ruling" branch | pin 2 ruled production-representative | MEDIUM |
| 8 | T7 | "no new ceilings exist" / Tier-1-only | task 22 cleared; E-16 created a Tier-2 ceiling | HIGH |
| 9 | T8 | "price from Task 2/5 actuals … on Tier 1" | pin 23(a) re-run; pin 89 measurement; task 22 | HIGH |
| 10 | T9 | "anchor **five-gate** block" | anchor ruling 2026-07-26 — NOT "five green" | HIGH |
| 11 | T9 | "seam **verdict**" (singular) | pins 45(b), 84, 86 — Branch B discharge shape | HIGH |
| 12 | T9 | "**six** transfer readings" | T4 recorded the seam pair as NON-transfer | HIGH |
| 13 | T9 | pack contents (1)–(10) incomplete | pins 61, 86, 87 add required pack content | HIGH |
| 14 | T9 | "zero locked opens" attestation | pin 87 — CRN defect is an open production defect | MEDIUM |
| 15 | T9 | `verifyCommand` is bare pytest | pin 83 gate sequence + `phase14_gate_suite.py` | LOW |

Rows 1–2 are the two already known. The live count is **13**.

---

## T5 — Diverse-tile runs

### 3. "Each run detached + stall-watched; **RAM predicate** before each" — HIGH
The criterion inherits `preflight`'s Tier-1 ladder predicate
(`scripts/phase14_stage1_run.py:327`, `RuntimeError` on `not tier1_eligible`). Task 22's
clearance and **E-16 §2** replace it for T5: `MemAvailable ≥ 2 × 4365 MiB` (~8730), twice
the **measured** peak, not the model's 5154. Pin 89 further found the model
**over-predicts by 18%** and that **wall, not RAM, is the binding axis** — the reverse of
what the criterion's Tier-1 framing assumes. E-16 §1 adds a per-leg **40 h wall ceiling**
that the criterion does not mention at all.
**Consequence if unfixed:** every leg refuses at preflight, or runs with no wall ceiling.
Already scheduled as T5a; recorded here for completeness. Ratified at pin 92.

### 4. "raw-σ" recorded per tile, uncaveated — HIGH
Written before the σ arc. Since then: pin 45(b) withheld both σ rows as
`NOT_ESTABLISHED`; pin 84 discharged Branch B on two CLEAN mean cells **plus two σ cells
not established**; pin 86 made **pin 37(c) a contract line — "Stage 2/2G MAY NOT ASSUME σ
SEAMS ARE CLEAN"**; pin 87 recorded the **CRN production defect** in those words at
`phase14.stage1.crn_production_defect_deferred`, a manufactured σ gradient at tile
boundaries that is *a property of the shipped system*, and **Stage 2G cannot close while
it stands**.
A per-tile `raw-σ` row that travels to Gate 1 with no attached defect caveat is an
unqualified σ number in the pack — the exact shape pin 86 says must be reported as OPEN.
**Question for the owner:** should the T5 σ row carry a verbatim pin-87 caveat, as the
mean rows carry `BRIDGE_CAVEAT`?

### 5. `build_evidence_row` keys pinned as "EXACTLY the schema set" — MEDIUM
**Pin 42** requires *every quantitative gate* to carry, **as a required schema field
beside its threshold**, the probability or explicit condition of each verdict outcome
under the null and under a stated alternative — "a schema key will" catch what prose
did not. **Pin 78** extends it: a validation must also state the **range over which it is
validated** and whether the application range lies inside it.
If any T5 row is verdict-bearing, "exactly the schema set" now names a *larger* set than
when the criterion was written. The current pinned set (`_PINNED_KEYS` in the test module)
carries no pin-42 field.
**Question:** are T5's transfer readings verdict-bearing (pin 42 applies) or purely
report-only rows (it does not)? The criterion's own "no interpretation prose" rider
suggests report-only, which would leave this INTACT — but it is not stated anywhere, and
pin 42 exists precisely because that judgment was made wrong five times in prose.

### 6. Equatorial `lane0_manifest.json` with per-file shas — MEDIUM
Written before the evidence-mirror arc. **Pin 56** mirrors provenance-bearing evidence
into the tree; **pin 58** corrected the boundary to *citation, not stage* — "a node is IN
if a standing claim cites it"; **pin 64** requires forward pointers for append-only
amendment; **pin 67** added a fourth witness class splitting "no sha" by whether anything
constrains the artifact.
The lane-0 bundle is a frozen, sha-bearing, provenance-carrying artifact that a Gate-1
claim will cite — i.e. squarely inside pin 58's boundary. The criterion predates all of
it and specifies only a local manifest.
**Question:** does the lane-0 bundle enter the evidence mirror, and under which pin-67
witness class?

---

## T6 — High-latitude kernel decision pack

### 7. ±66 breach column, "either ruling yields correct pinned arithmetic" — MEDIUM
The criterion is written with the pin-2 frame convention **open**, and pins both branches:
production-representative → `edge = −(64 + halo)`, breach at `halo > 2.0`; isolated →
`edge = −(62 + halo)`, breach at `halo > 4.0`.
**Pin 2 was ruled 2026-07-25: production-representative** (`DIVERSE_FRAME_CONVENTION`,
`scripts/phase14_stage1_run.py:189-197`), and the ruling's own recorded rationale already
states the consequence: *"SO ±66 headroom tightens to halo ≤ 2.0 deg (Gate-1 kernel
decision inherits)"*.
This is **criterion 8's exact shape** — a criterion written while an election was open,
carrying a branch for an option that lost. The isolated branch is now dead arithmetic.
Not harmful (both branches were correct), but it is the same class of artifact pin 90 just
ruled on, and the live half is: only `halo ≤ 2.0` is the operative breach threshold.

---

## T7 — Phase-10 revisit

### 8. "Budget: Tier 0/1 only … **no new ceilings exist**" / "any lane over Tier-1 → WAIT" — HIGH
The sub-design's parenthetical **"(pre-registered-or-WAIT; no new ceilings exist)"** was
true when written. It is now false: **task 22 cleared a Tier-2 crossing** and **E-16
created an explicit Tier-2 ceiling** (40 h/leg, ~8730 MiB launch gate). A ceiling exists.
Whether T7's lanes may *use* it is the owner's call and is **not** assumed here — but the
criterion's stated premise is factually stale, and a lane that would now be affordable
under the T5 ceiling would be recorded as a WAIT row on a premise that no longer holds.
**Question:** does task 22's clearance extend to T7's lanes, or is it T5-scoped?
E-16 says "per leg" of T5 only; nothing addresses T7.

---

## T8 — OSSE run decision

### 9. "Price from measured constants … **tile solve wall from Task 2/5 actuals** … on **Tier 1**" — HIGH
Two premises moved:
1. **The Task-2 actual is superseded.** Pin 23(a) found the original T2 probe ran **both
   legs into the 500 cap over rtol**, so its wall was bounded above by cap × per-iteration
   cost — "the bracket could only ever report *model conservative*"
   (`phase14_stage1_run.py:66-72`). The converged re-run is `probe_converged`; the
   production-geometry number is now **pin 89's measurement** (3.440 h/window, 31.0 h/tile
   at m=100, CONVERGED). Pricing an OSSE off the capped T2 row would price off a number
   the owner already ruled un-usable.
2. **"on Tier 1, no cloud"** — Tier 2 now exists and is cleared for T5. The pricing table's
   tier basis is stale in the same way as T7's.

Also worth noting: T8 is `blockedBy [5]` and prices from **T5 actuals**, which do not exist
yet — so this one is naturally fixed by sequencing, provided the basis cited is pin 89's
measurement and the T5 leg-1 re-assess, not Task 2's.

---

## T9 — Gate-1 pack (userGate)

### 10. Pack section (1): "anchor **five-gate** block" — HIGH
The anchor gate was ruled **2026-07-26** to be explicitly **NOT "five green"**. Its own
`ACCOUNTING` block (`scripts/phase14_anchor_gate.py:164-177`) states the ruled count:

> "TWO checks run and passed (1, 5), TWO cited and pre-ratified at Gate 0 (2, 4), ONE
> proxy-passed with the specified check deferred (3). **This accounting survives careful
> reading in Stage 2; 'five green' does not.**"

The criterion's phrase "anchor five-gate block" is the wording the ruling exists to
prevent. The pack must carry the four-way accounting, not a five-gate block.
Note the criterion's "(with cross-host slot pending-T18 explicit)" also moved: **pin 86(c)
sent T14–T21 to Stage 2**, so "pending-T18" now means pending a *Stage-2* task — a
materially weaker promise at Gate 1 than when written.

### 11. Pack section (2): "seam **verdict** + ORACLE numbers" — HIGH
Singular "verdict" predates the σ arc. The actual Stage-1 seam result (pins 45b, 84, 86)
is: **two mean-route CLEAN cells, and two σ cells NOT_ESTABLISHED with the mechanism
documented** — "the rubric was pre-registered with a withholding cell so that 'looked and
could not attribute' is a result; this is that cell used as designed, not a blank." The
consequence recorded at `phase14.stage1.sigma_rows_not_established` is explicit: **"Stage 1
has NO attributable sigma-route seam verdict."**
A pack section titled "seam verdict" invites exactly the collapse pin 86 forbids.

### 12. Pack section (3): "**six** transfer readings (numbers + bridge caveats)" — HIGH
**The count is wrong, and this one is checkable against the store today.** Only the four
diverse tiles produce transfer readings. The seam pair does not:
- `phase14.stage1.seam_pair.non_transfer_note`, verbatim: *"this verdict is **not a
  production-geometry seam reading**: it is taken on 10×5 halves inside the anchor
  footprint …"*
- The recorded `seam_pair.tiles.{seam_n,seam_s}` sub-rows carry **no `scores`, no
  `reference_row`, no `bridge_caveat`** — keys are solve/provenance only (`convergence`,
  `frame`, `maps`, `pcg`, `worst_residual`, …). They are solve records, not transfer
  readings.
- The anchor is the identity subject, not a transfer reading.

So Stage 1 can deliver **four** transfer readings, not six. The criterion was written
against a six-tile program in which every tile yielded a reading; T4's actual execution
recorded the seam pair as explicitly non-transfer on non-production geometry.
**This is the sweep's most consequential find:** it is a deliverable-count error in the
stage's own output section, and it would have surfaced at pack-assembly time — after all
four legs had run.

### 13. Pack contents (1)–(10) are incomplete against later rulings — HIGH
Three rulings add required Gate-1 pack content that the enumerated list does not carry:
- **Pin 61 — explicit:** *"58(d)'s RESULT GOES IN THE GATE-1 PACK, not only the fix log."*
  Three of four check-1 routes would have re-passed against a substituted reference;
  `gamma_route` recorded neither path nor sha. Record the gap, the two fixes, and the
  capture caveat **together** — "a reader who learns this from a remediation commit learns
  it in the wrong order."
- **Pin 86** — T12 carries the σ question forward OPEN with the inheritance package named
  (mechanism, both channels quantified, reachability + m requirement, pin 31(b) latitude
  non-uniformity, ρ model with its validated span declared), and **pin 37(c) as a contract
  line**. The pack is where that contract is handed over.
- **Pin 87** — the CRN production defect and its consequence (**Stage 2G cannot close
  while it stands**) travels forward "named and costed".

### 14. Discipline attestation: "**zero locked opens**" — MEDIUM
Pin 87 records an open **production defect** deferred into Stage 2. Whether that counts
against "zero locked opens" depends on what "locked" means here (locked *instruments* vs
open *defects*) — but the attestation as phrased reads as a clean bill, and the honest
statement is now "zero locked opens, one deferred production defect named at
`crn_production_defect_deferred`". Flagged for wording, not for substance.

### 15. `verifyCommand` metadata is `pixi run pytest -q -p no:cacheprovider` — LOW
**Pin 83** reordered the gate sequence to **format → stamp → suite → verify → commit** and
made it mechanical in `scripts/phase14_gate_suite.py`, because the old order produced gate
evidence from a pre-format tree *structurally and every time*. A bare pytest invocation as
T9's verify command reproduces the defect pin 83 fixed. T9's "full sweep on the final tree"
criterion is right in intent; only the recorded command is stale.

---

## What the sweep did NOT find stale

Recorded so the walk is auditable rather than a list of hits only:

- **T5 GroundTrack wiring** (criterion 2) — no later ruling touches `Registry.applicable` /
  `report_rows`, and fork F's "absence means absence" survives pin 86's reporting
  discipline unchanged.
- **T5 kuroshio land-mask** (criterion 6) — pin 89's probe converged on kuroshio with the
  land-mask path intact, which *de-risks* the criterion without changing it.
- **T5 southern anisotropy inputs** (criterion 5) — feeds T6 as written.
- **T5 "no interpretation prose"** (criterion 7) — reinforced, not changed, by pin 86.
- **T7 band provenance** (`phase10_lanes` not `phase13_lanes`) — the live confound review
  pin 9 named is untouched by any later ruling.
- **T8 value-case verbatim + empty decision cell** — unchanged.
- **T9 sections (7) refresh election and (10) T11 coverage table** — unchanged.

---

## Executor's reading of the shape

Nine of the thirteen live items share one mechanism: **a criterion that named a live
option, an open election, or a current ceiling, and outlived the ruling that closed it.**
Criterion 8 (pin 90) was the first instance found; T6's ±66 branch and T7's "no new
ceilings exist" are the same object.

The remaining four are a different and more dangerous mechanism: **criteria describing an
output whose shape later evidence changed** — T9's "five-gate", "seam verdict", and
especially "**six** transfer readings", which is a count contradicted by the evidence store
as it stands today. Those would not have failed loudly. They would have been assembled.
