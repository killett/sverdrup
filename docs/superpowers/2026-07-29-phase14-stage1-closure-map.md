# Stage-1 closure map (owner pin 82, and its clarification)

> ## ✅ RULED 2026-07-29 — **BRANCH B**, owner pins 84–88 (ruling doc PART 17)
>
> **The recommendation cell below is FILLED by that ruling.** "Measured seam
> behaviour — oracle+rubric verdicts" **DISCHARGES** on two attributable CLEAN mean
> verdicts plus two σ cells NOT_ESTABLISHED with the mechanism documented — *"the
> rubric was pre-registered with a withholding cell so that 'looked and could not
> attribute' is a result; this is that cell used as designed, not a blank."*
>
> - **T14 removed from T5's blockers** (pin 84). Remaining path: **T5 → {T6,T7,T8} →
>   T9**, with T12 ready.
> - **⛔ T5's Tier-2 block REINSTALLED IN THE SAME EDIT** as a userGate, **task 22**
>   (pin 85) — T5 is `blockedBy [3,4,22]` and was never ready in between. Fourth
>   instance of that pattern; this time the replacement blocker was created *before*
>   the old one was removed.
> - **T14–T21 move to Stage 2 intact** (86c) — not deleted, not descoped, pins and
>   pre-registrations preserved including 68(b)'s falsifier and 73(c)'s branch.
> - **The CRN defect is recorded as a PRODUCTION DEFECT** (87), at
>   `phase14.stage1.crn_production_defect_deferred`. **Stage 2G cannot close while it
>   stands.**
> - **Pin 82(e)'s halt LIFTS for the deliverable path only** (T5–T9) and **stays in
>   force for the σ chain**, which is now Stage 2's.
>
> **The last thing standing between here and the stage's output is T5's Tier-2
> ceiling — owner-held before any of this began, and now the sole content of task 22.**

**Status: RULED — Branch B adopted (pins 84–88).** The body below is preserved AS
DELIVERED, so the reasoning the ruling acted on stays readable; the ruling's effects
are in the block above. **One task was created — task 22, the Tier-2 userGate,
mandated by pin 85 in the same edit that freed T5 from T14.** No factor adopted,
nothing sealed, T14 not started. Pin 82(e)'s halt has lifted for the deliverable path
(T5–T9) and remains in force for the σ chain.

Pin 82 asked for a stated endpoint after observing that open work stood at **5
deliverable against 9 hardening, with no deliverable task moved since T4**. The
clarification then sharpened the central question, and that sharpening turned out to
be the whole map:

> The question is NOT "does the C1→2 contract need σ output." That conflates two
> different deferrals hiding under one edge: the σ **MEASUREMENT** … and the **FIX** …
> These separate if and only if no Stage-1 deliverable depends on CROSS-TILE σ
> behaviour.

**Answer up front: they separate.** One Stage-1 deliverable is cross-tile, it is
already produced, and it does not require T14. The detail is below, including the one
place the answer is a judgement rather than a fact.

---

## 1. Every Stage-1 output, marked per-tile or cross-tile — clarification (a)

The registry decides most of this mechanically. Of the six tiles in
`scripts/phase14_stage1_run.py`, an overlap test across all fifteen pairs returns
**exactly one adjacency: `seam_n`/`seam_s`** — the seam subject itself.

| tile | core bbox (lon, lat) |
|---|---|
| equatorial | 200–215, −4–11 |
| southern | 215–230, −62–−47 |
| quiet_gyre | 255–270, −30–−15 |
| kuroshio | 132–147, 28–43 |
| seam_n / seam_s | 295–305, 38–43 / 33–38 |

**The four diverse tiles are pairwise disjoint, separated by tens of degrees in both
axes. They share no boundary with each other or with the seam pair.** A per-tile CRN
origin produces a manufactured σ gradient *at a boundary between tiles*; where no
boundary exists, there is no gradient to manufacture.

| output | task | per-tile or cross-tile | basis |
|---|---|---|---|
| µ / λx / coverage / **χ²** j3-validation rows | T5 | **per-tile** | scored per tile against the j3 track on that tile's own domain; the four tiles never touch |
| **raw-σ row** | T5 | **per-tile** | each tile's own σ field on its own core; no differencing across tiles |
| **LABELED scalar-s\* reference row** | T5 | **per-tile** | a per-tile reference scalar, labelled as such |
| bridge_caveat, seal sha, manifests | T5 | per-tile | bookkeeping per run |
| **SO anisotropy / spectral / track diagnostics** | T5→T6 | **per-tile** | recorded from the `southern` tile alone, "per-tile×era parameterization" in T5's own AC |
| kernel decision + arithmetic | T6 | per-tile | consumes the SO diagnostics above |
| revisit lane × band deltas vs lane-0 | T7 | **per-tile** | see §2 — pre-registered as per-tile |
| **OSSE pricing inputs** | T8 | **per-tile** | prices from "N_epoch-classes × tile solve wall from Task 2/5 actuals" — wall-clock and compute-hours, carrying no σ and no cross-tile term |
| **measured seam behaviour: oracle + rubric verdicts** | T4 → T12 | **⛔ CROSS-TILE** | the one genuinely cross-tile deliverable — see §3 |
| C1→2 coverage table | T12 | mixed | a bookkeeping walk over the items above |
| Gate-1 pack | T9 | assembly | presents the above |

**Everything the owner named specifically — T5's χ², the raw-σ and scalar-s\*
reference rows, T6's SO diagnostics, T8's pricing inputs — is per-tile.** None of
them carries an unlabelled cross-tile component, and the geometry is why: those
quantities are computed on single tiles that have no neighbours.

---

## 2. The insulation is pre-registered, not convenient — clarification (e)

This is the distinction the owner asked to be tested, and it holds. T7's sub-design,
**locked at plan review as the resolution of the fork-d pin-6 deferral**, reads
verbatim in the tracker:

> **Per-tile lanes, NOT a shared cross-tile field**: the Stage-1 question is "does the
> box-scale negative transfer per-regime?", which is a per-tile contrast; a shared
> field couples tiles through a global fit nobody pre-registered and pollutes the
> per-regime read. **(Cross-tile sharing is Stage-2 calibration's business, fork E.)**

And, separately:

> Lanes run on the four diverse tiles only (anchor is the identity subject, seam-pair
> is the seam subject — adding lanes there measures nothing new and spends).

**The reason given is a statistical-confound reason, not a CRN reason, and it was
recorded long before the CRN origin defect surfaced.** The deliverable path is
insulated from cross-tile σ behaviour by a design decision taken for an unrelated
purpose. That is evidence. Had the insulation only shown up as a shape in the
dependency graph, it would not be.

---

## 3. The one cross-tile deliverable — clarification (c), answered honestly

**Name it: T12's C1→2 contract line "tiling machinery + measured seam behavior
oracle+rubric verdicts".** It is cross-tile by construction — a seam is where two
tiles meet.

**But it is already produced.** T4 is COMPLETE and its four rows are recorded:

| route | field | R_seam | verdict |
|---|---|---|---|
| pair | mean | 0.082738 | **CLEAN** |
| oracle | mean | 0.098103 | **CLEAN** |
| pair | σ | 1.104435 | **NOT_ESTABLISHED** (ensemble MC artifact — see diagnosis) |
| oracle | σ | 0.648763 | **NOT_ESTABLISHED** (ensemble MC artifact — see diagnosis) |

So the contract line does not *require T14*. What T14 would change is the **quality
of the σ half** of an already-delivered measurement, not whether the line is
discharged at all.

**This is where the map stops being a fact and becomes an owner decision**, and it is
exactly pin 82(d): is "measured seam behaviour" discharged by **two CLEAN mean
verdicts plus two σ cells marked NOT_ESTABLISHED with the mechanism documented**, or
does the contract require the σ verdicts to be *established*? Nothing in the tracker
answers that; it is a judgement about what Stage 2 is owed. §5 prices both readings.

---

## 4. What must be TRUE for Stage 1 to close — pin 82(a)

Minimum set, task by task, to the Gate-1 pack. **T9 is `blockedBy [3,4,5,6,7,8,10,11,12]`
— none of T14–T21 appears.**

| # | must be true | task | state |
|---|---|---|---|
| 1 | four diverse-tile transfer readings recorded | T5 | **blocked on task 22 ONLY** — the Tier-2 crossing (owner-held). The T14 edge was removed by pin 84 |
| 2 | high-latitude kernel decision pack assembled | T6 | behind T5 |
| 3 | phase-10 revisit lanes run per-tile, report-only | T7 | behind T5 |
| 4 | OSSE priced from T5 actuals, decision cell empty | T8 | behind T5 |
| 5 | C1→2 coverage table walked both directions | T12 | **READY NOW** |
| 6 | Gate-1 pack assembled, owner walk | T9 | behind 1–5 |

**The critical path is T5 → {T6, T7, T8} → T9, with T12 parallel and already ready.**
Everything else open — T14, T15, T16, T17, T18, T19, T20, T21 — sat off this path
except through the single edge `T5←14`. **Pin 84 cut that edge and pin 86(c) moved
those eight tasks to Stage 2 intact**, so the only blocker on the critical path is now
**task 22**, the Tier-2 ceiling.

---

## 5. Required vs deferrable, and the two branches priced — pin 82(b), (c), (d)

### The four threads the owner named

| thread | required for C1→2? | verdict |
|---|---|---|
| **Rule 0.b** (the σ floor) | **No.** Nothing downstream reads a σ seam verdict; the contract line is discharged by the recorded rows | **deferrable** |
| **the ρ model** | **No.** It exists only to parameterize Rule 0.b | **deferrable** |
| **high-r validation** | **No.** It exists only to validate the ρ model | **deferrable** |
| **T5's Tier-2 crossing** | **YES — and it is the binding constraint.** No T5, no T6/T7/T8, no Gate-1 pack | **required; owner-held** |

### Branch A — status quo: fix first, then measure

T5 waits for T14, which waits for T18 (owner walk), T19, T20, T21 — and, if task 21's
price authorises high-r points, for those too (pin 80).

- **Work before T5 can start:** the T18 walk, T19's re-score, T20's sweep, T21's
  pricing, then the owner's ruling on that price, then T14's re-solve (~7 h, RAM-gated,
  died twice historically), then T15's survey, then Rule 0.b in T17.
- **Then** T5 still faces its unchanged Tier-2 crossing.
- **Spend:** T14's check-1 re-run alone is a ~7 h RAM-gated solve. T21 may authorise
  further solves at a price not yet known. **Rule 0.b cannot be sealed until the ρ
  model is validated, and pin 77 established that the cheap route cannot reach the
  applied range.** The path has no bounded end date that can be stated today.

### Branch B — pin 82(d): declare σ NOT ESTABLISHED for Stage 1

Drop the `T5←14` edge. Move Rule 0.b, the ρ model and high-r validation to Stage 2G,
where the seams are actually assembled.

- **Work before T5 can start:** none from the σ chain. T5 faces **only** its Tier-2
  crossing — a pre-existing, separate owner decision that predates this entire chain.
- **What Stage 1 ships:** the mean route's **two CLEAN verdicts**, the σ route
  **recorded open with its mechanism**, and the four per-tile deliverables untouched.
- **What Stage 2G inherits (pin-82 clarification (d) — the record travels COMPLETE):**
  the CRN origin defect and its mechanism; **both** correlation channels, one of them
  irremovable by any lattice fix; the reachability finding (`F_ens/D_int_σ = 1.1356`,
  CLEAN unreachable at m=100 for every factor ≥ 1.00, min m 129–148); pin 31(b)'s
  latitude non-uniformity; the ρ model with its **validated span [0, 0.2523] declared
  against an applied r ≈ 0.9**; the settling measurement with its caveats; and the
  provenance mirror witnessing all of it. **A deferral is not a gap if the successor
  inherits everything needed to act on it — and it does.**
- **Cost:** the manufactured σ gradient at tile boundaries persists through Stage 1.
  **It has no Stage-1 consumer** (§1), because the only tile pair that has a boundary
  is the seam subject, whose σ rows are already NOT_ESTABLISHED.

### Spend, both branches

Measured, not estimated: anchor gate **6.21 h / 3512 MiB**; seam pair **15.33 h /
2574 MiB**. T5 is priced at **23.8–94.2 h per tile, 95–377 h (4.0–15.7 d) for four**,
needing **MemAvailable ≥ 9431 MiB** against 5261 MiB live at pricing time —
`tier1_eligible` **False**, and `authorize("tier2_probe", …, 23.78)` returns **Wait**
at the *low* end, over the 6 h ceiling by 4.0×.

| | Branch A | Branch B |
|---|---|---|
| σ-chain work before T5 | T18 + T19 + T20 + T21 + owner ruling + T14 (~7 h solve) + T15 | **none** |
| additional solves | T14's re-run, plus whatever T21 authorises (unpriced) | none |
| T5's Tier-2 crossing | unchanged, still owner-held | unchanged, still owner-held |
| Stage-1 σ verdicts | possibly established, on a floor whose model is unvalidated at the applied range | **NOT_ESTABLISHED, with the mechanism documented** |

**Branch B closes Stage 1 materially sooner — and the difference is the entire σ
chain.** It does not resolve T5's Tier-2 crossing, which is the binding constraint
either way and is owner-held independently.

---

## 6. What I am not deciding

Three things are the owner's, and this document deliberately stops at each:

1. ~~**Whether "measured seam behaviour" is discharged…**~~ **ANSWERED: YES** (pin 84).
   The withholding cell was pre-registered precisely so that "looked and could not
   attribute" is a result rather than a blank, and **the discharge is on REPORTING, not
   on ANSWERING** (pin 86) — the σ question is recorded OPEN with a named inheritance
   package, and pin 37(c) becomes a CONTRACT LINE: **Stage 2/2G may not assume σ seams
   are clean.**
2. **T5's Tier-2 crossing**, WAITing since before this chain began and unchanged by
   pin 57's m=137 pricing (+0.5% RAM, ×1.37 wall — both inside the host's own ×1.70
   drift).
3. ~~**Which branch to take.**~~ **RULED: Branch B** (pin 84). The recommendation cell
   is no longer empty — it is filled by pins 84–88, recorded at the head of this
   document. What remains owner-held is item 2 above, and only that.

**Pin 82(e)'s halt stays in force until the owner rules.** No new hardening task has
been created, and findings recorded during this map — the disjointness of the diverse
tiles, the fork-d pin-6 provenance — became evidence here rather than tasks.
