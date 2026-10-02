# Phase 14 Stage-2 draft — FRAME REVIEW (§7-17 / pin 241), reviewer B

> **Ordered by owner pin 276(c)**, ruling PART 63. Conducted 2026-09-28 against the draft
> at `119acce` (`docs/superpowers/specs/2026-09-21-phase14-stage2-temporal-design.md`,
> §§0–20, D1–D17 + P1–P4).
>
> ⛔ **NOTHING IS FIXED HERE.** 276 stops at the draft plus this review; the spec gate is
> the owner's. No finding below has been acted on, and the draft is unchanged.
>
> **Brief:** reviewer B was briefed on **the owner's two targets only** — the **unit of
> account** and the **stage boundary** (276c) — and was given **none** of the author's
> attack surfaces, per §7-17: *"The requester does NOT author B's targets, because the
> requester is the one who chose the frame."*

## Verdicts

| target | verdict |
|---|---|
| **Unit of account** | ⛔ **FRAME DEFECT — CONFIRMED** (three instances) |
| **Stage boundary** | ⛔ **FRAME DEFECT — CONFIRMED** (three instances) |

⭐ **THE DEFECTS ARE THE AUTHOR'S, NOT THE OWNER'S.** Every one sits in a decision the
executor drafted or in a sentence the executor wrote; none is in the pins.

> ⚖ **FORWARD POINTER — THIS ATTRIBUTION IS CORRECTED BY OWNER PIN 278 (PART 64): FOUR of
> the six are the OWNER's, one is SHARED, one is the draft's.** The claim above is left as
> written, with this pointer beside it, so the correction is visible rather than silent —
> see **§5.1**. ⛔ **Read §5.1 before quoting this line.**

---

## 1. Unit of account — CONFIRMED

### 1a. The tier decision is priced in RAM; the binding axis is WALL

**At fault — §11.4 (D10):** *"Price that costliest era-fit … against **Tier 1: RAM by the
2× launch rule under `tier1_eligible`**"*, with the table *"it CLEARS Tier 1 → era-fits
**never need Tier 2**, and **S2 does not bind them**."*

**Verified by the author on relay:**

- `tier1_eligible(predicted_peak_mib, meminfo)` (`src/sverdrup/application/ladder.py:215`)
  is a **RAM predicate and nothing else** — *"True iff the predicted peak fits under
  `TIER1_HEADROOM_FRACTION × MemAvailable`"*. ⛔ **Tier 1 has no wall bar, so wall cannot
  make "clears Tier 1" fail.**
- ⭐ **The refutation is inside the node the draft cites twice** (§11.3 for "31.0 h", §16 P2
  for "3.44 h"). `phase14.stage1.tier2_probe_kuroshio_m100`, field `headline`: *"Measured,
  CONVERGED: 3.440 h for ONE window at m=100 on kuroshio. Per tile (×9 windows) 31.0 h;
  four tiles 123.8 h. **The binding axis is WALL, not RAM — the reverse of what the model
  implied.**"*

**The numbers (reviewer's, arithmetic re-checked by the author):**

| quantity | value |
|---|---|
| RAM: measured peak 4364.5 MiB; 2× rule ~8729 MiB; headroom observed 11 248 MiB | **clears by 22%** |
| one era-fit (a tile-year, 9 windows) | **30.96 h** |
| 12 era-fits (D1's fit set) | **371.5 h ≈ 15.5 d** |
| × pin-53's m = 137 (§8.5's "×1.37 wall") | **509 h ≈ 21.2 d** |
| × pin-28's host ×1.70 | **865 h ≈ 36.0 d** |
| one era-fit vs the only authorised Tier-2 row's ceiling (`max_wall_h = 6.0`) | ⛔ **5.16× over** |

**Downstream, per the reviewer:** §11.4's second row is unreachable, so §11.5's
required-evidence mechanism and precondition **§19.2-C11** are built for a consumer the tier
arithmetic declares will never exist — **unrun in discipline 11's sense**. §11.4's own escape
clause concedes throughput (wall) is what will move Stage 2 to Tier 2, so a section titled
*"ARITHMETIC, not an election"* resolves the arithmetic in RAM and relocates the decision to
an election. §5.4's "costliest admissible selection" is then priced in the axis that does
**not** govern, against §7-16.

⚠ **(f2) — the defect propagated into the prose it generated:** §18.2 reason 5 declines the
revisit because it *"competes with Stage 2's box-bound critical path"*, and §18.3 prices the
revisit in wall-days — so the draft **prices what it declines in wall and what it buys in
RAM**, and never computes the critical path it invokes as a reason.

⚠ **(f3) — the corroboration was unconsulted while being quoted**: not merely in the tree,
but in the very node the draft cites, in the field named `headline`.

### 1b. `n_eff` is the unit everything is denominated in, and the draft never defines it

`n_eff` is the regressor (§3), the selection objective (§5.3), the hull (§5.3 step 1), the
tolerance's denominator (§6.5), the era no-op's normaliser (§15.2), the census (§12.2) and
the tier price (§11.4). It is defined only up to **L**, **L_t**, **n_eff₀** and the
window aggregation.

**Verified counts in the draft:** `L_t` **1** (inside the quoted formula); `n_eff₀` **1**
(inside quoted program text); **"mid-ladder" 0**; **"NAMED scale" 0**.

Consequences, per the reviewer:

- ⛔ **Not one numeric threshold exists in the document.** Every bar names where its number
  will come from (§3, §6.3, §6.4, §6.5, §10.2, §14.3, §19.3's *"'large' is a NUMBER, STATED
  NOW"* — with no number following). ⭐ **§19.1's own test applies to the draft's own
  thresholds: a bar with no number cannot fail, and is UNRUN.**
- ⛔ **§5.3's "MECHANICAL" rule is not mechanical**: both steps rank-order as functions of
  **L**, so with L unchosen the census operator chooses L and the epoch selection follows —
  relocating Stage 2's most consequential choice to an unpinned executor parameter, which
  §3 promises the opposite of ("neither is left to the executor").
- ⛔ **Fork-e pin 2(i) sources K's scale from "a NAMED mid-ladder spatial scale in the λx
  neighborhood"** — and §6.3 establishes, from the store, that λx is `recorded_absent` at
  `equatorial` and `quiet_gyre`. The draft applies that absence **only** to resampling block
  sizes and does not notice it voids fork E's stated source for the regressor's own scale at
  the same two tiles.

### 1c. The evidence unit: 3 shared era realisations counted as 12 rotations

**At fault — §2:** *"Gate-2's leave-one-reference-out rotation set is **3 rotations × 4
tiles**"*, attributed to fork-e pin 4.

**Fork-e pin 4's own words:** *"ALL leave-one-reference-out rotations run and reported
(**three epochs → three**)."* **Verified counts in the draft:** `"3 rotations × 4 tiles"`
**1**; `"three epochs → three"` **0**.

⭐ **The rotation unit in the program spec is the EPOCH; the draft silently redefines it as
the (tile, epoch) cell and multiplies the claim-bearing set by 4.** The three reference
epochs are the *same three* at all four tiles, so independent era realisations number **3**
and cannot be raised by adding tiles.

The two readings fail in opposite directions:

- **12 cells** → §6.4's *"the ONLY instrument that touches the era-level component"* is false
  for the claim-bearing object: D2 fits **one pooled (a, b)**, so dropping one cell leaves
  that era in the pooled fit through the other three tiles. ⛔ **The falsifier cannot fail in
  the axis it exists to test** — discipline 11's family, inside §6.4.
- **3 epoch-rotations** → §2 over-counts 4×, and §19.3's "bar ON THE SET" is a bar on 3
  held-out predictions, not 12.

⚠ **And with 3 eras a per-tile LORO fit has ZERO residual dof in the era dimension** —
leaving one out leaves two, which fit the era-mean contrast exactly. §6.4's *"can falsify a
too-narrow se; cannot estimate the era variance"* understates it in the same direction.

---

## 2. Stage boundary — CONFIRMED

⭐ **THE ROOT CAUSE: the draft's boundary is TWO-STATE.** §1 declares it *"SETTLES Stage 2's
items and RECORDS 2G's as named C2→2G carry-forwards"*, and §20.1 offers exactly **SETTLED /
CARRIED TO C2→2G / PLACED**. ⛔ **There is no disposition for "Stage-2 work, at plan time,
not settled by this spec"** — although §4.3, §5.4, §6.6, §7.2, §9.4, §11.5, §12.7 and §13 all
defer design to the plan. The missing cell produces over-claiming one way and mis-homing the
other.

### 2a. The kernel exits are mis-homed to 2G — and Stage 2's regressor rides the constant they set

**At fault — §2 and §20.1 row 263.1:** *"the kernel exits are 2G's (274b)"* / *"CARRIED TO
C2→2G"*.

**Three records say otherwise. Verified verbatim by the author on relay:**

| record | words |
|---|---|
| **ruling 219(c)** | *"Two resolutions exist — a smaller km scale, or a latitude-aware halo (a code change under fork-d pin 4's single point of change). **Both are Stage 2; neither is T6's to choose.**"* |
| **closure record §5, obligation 1** | *"`operative_halo_deg()` stays untouched **until a Stage-2 ruling**."* |
| **274(b) itself** | *"pole handling and the kernel exits (219; **§7 decides poles** 'with the kernel decision in hand')"* |

⭐ **274(b) is a statement about what THIS SPEC settles, not a re-homing of the WORK**, and it
leaves 219(c) and the closure obligation standing. The draft read "not settled here" as
"belongs to the next stage".

⚠ **The misreading is legible in the draft's own sentence (the (f2) shape).** 274(b) attaches
*"with the kernel decision in hand"* to **poles** (program spec §7). §20.1's cell drops
"poles" and attaches it to *"poles **and the kernel exits**"*, producing a circle: **the
kernel exits are 2G's, decided with the kernel decision in hand.** The kernel decision
becomes its own precondition.

**Why it is load-bearing — the coupling, verified in code:**

- **fork-d pin 4**: the halo derives from the operative kernel scale, auto-following.
  `operative_halo_deg()` (`src/sverdrup/application/spatial_tiles.py:41`): *"When the
  constraint-3 decision ties the halo to the operative kernel scale, **THIS function changes
  — nothing else**."*
- **fork-e pin 2(i)**: K's scale is the named mid-ladder scale, and *"the fork-d pin-4
  auto-follow linkage binds to the NAMED scale"* — ⭐ **so `n_eff`'s kernel length is bound to
  the constant the kernel decision sets.**
- ⭐ **`halo={HALO_DEG}` is inside `BasisSpec.key()`** (`src/sverdrup/methods/miost_basis.py:80`)
  — a component of every `params_key`.
- The halo **is the obs frame**, so changing it changes the maps, `n_obs` and `n_eff` at once
  — and it lands on **`southern`**, a fit tile whose ±66 margin §2 attests at exactly **1.0°**,
  the halo itself.

⛔ **Under the draft's OWN §7.3 test** — *"they must not sit on a lattice 2G abandons"* — the
draft freezes the **pavement** in Stage 2 and leaves the **halo and kernel scale**, in the
same `params_key`, to the stage it just sent them to. The 12 era-fits, the hull, the pooled
law, the extrapolation audit, seal v2 (§10.5) and precondition **§19.2-A7** would all be
produced against a scale 2G may change. And 2G *cannot* decide poles without the kernel
decision in hand — so the draft hands 2G a required input it also handed 2G.

### 2b. The scope boundary is drawn by the inheritance list, not by the contract

276(b) specifies the coverage map's rows, and the draft builds exactly those 23 and
reconciles them two ways (§20.3) — treating that as its completeness instrument. ⛔ **But
274(a) defines Stage 2's scope as program spec §8's scope, and §8 / C2→2G contain
deliverables in NO row of §20.1 and NO decision D1–D17:**

- ⛔ **per-era δ_m assignments (E7)** beyond δ_j3. **Verified: `E7` appears 3× in the draft,
  all about δ_j3 (§9.6) or the Sentinel-6 class-map bug (§5.5).** E7's actual subject —
  per-era δ for every other mission and era — is designed nowhere.
- ⛔ **C2→2G's per-era R assignments** — appear once, in §18.6, only to classify R as an
  *input* the OSSE does not test.
- ⛔ **There is no C2→2G line table at all** — 15 scattered mentions, no enumeration, against
  the closure record's own §4 pattern (14 C1→2 lines, each with its witnessed carrier and
  digest).

⭐ **So the accounting is against what Stage 1 handed the stage, never against what the stage
owes 2G — and a 23-row reconciliation that closes "exactly" cannot show a hole in a row set
it does not contain.**

**Same cause, corroborating.** Fork C's **sparse-era honest sentence, required verbatim
in-spec by ruling** — *"calibration is transferred, not fit, here; its validation is thin and
stated; gauges carry the independence burden"* — is **absent**. **Verified:** `"transferred,
not fit"` **0**, `"thin and stated"` **0**, `"independence burden"` **1** (paraphrased inside
§19.3). Program spec §11's Stage-2 expectation-setters are likewise absent.

### 2c. A free fleet-side measurement the boundary hides (lower materiality)

§1.1(a) sets Stage 2's scope by *"what identifies the covariate, not fleet coverage"*, and
§5.3 step 1 scopes the objective to the **transferred** epochs — Stage 3's consumers. But
§4.5 identifies **2G's** consumer: the covariate carries `s` across the **e09/e10** boundary
in 2G's calendar-2017 product. ⛔ **e09 is a `fit` epoch, so it is in no objective and enters
selection only by accident of D8(f)'s j3 constraint** — and the extrapolation fraction 2G
will actually face (fleet tiles, e09 vs e10) is in no audit.

⚠ **And it is obtainable for nothing:** `n_eff` is pure geometry (no solve, no map, and §7.2
establishes geometry-only steps do not bite §7-1), and §12.2's own basis is that the
acquisition unit is the **native daily file** which is **global** — so the days the anchor's
pure year already requires deliver the whole globe.

---

## 3. Checked and SOUND — not findings

The reviewer recomputed and confirmed, independently:

- ⭐ **§7.1's pavement arithmetic: all 64 (tile, axis, rung) cells reproduce exactly**, both
  the km table and the miss/step table, from `LADDER`, `lonlat_to_km` and the signed
  `alpha = 1.0656719505786896` at `/winner/params` — including the owner-figure
  reconciliation via the rounded 85.254 step.
- Every seal-derived table in §4.2, §5.1, §5.3, §5.5, §9.1: 15 epoch rows, the spans, the
  net-of-locked counts, `role == fit+validate ⟺ net ≥ 4` on all 15, transferred =
  {e00,e01,e05,e06,e07} carrying only {ers-line, poseidon}, `gfo` only in e02–e04, `s6a_lr`
  the sole mission absent from `INSTRUMENT_CLASS`, and j3-by-mission-ID = {e09, e11, e12}.
- §12.1's per-mission day counts and the `j2n` / e09-boundary coincidence.
- §8.6's no-shared-seams claim; §6.3's λx absence; §1.1(b)'s store-schema claim at
  `scripts/phase14_stage1_run.py:2612-2614`.

## 4. Provenance and limits of this record

- **Reviewer B edited, ran, sealed and committed nothing.** Read-only throughout; two files
  read from the gitignored store and the seal.
- **The author verified on relay, read-only:** `tier1_eligible`'s signature and body;
  `operative_halo_deg()`'s docstring; `halo={HALO_DEG}` in `BasisSpec.key()`; ruling 219(c)
  verbatim; and the draft occurrence counts quoted above (`L_t`, `n_eff₀`, "mid-ladder",
  "NAMED scale", `E7`, the fork-C sentence fragments, both rotation-unit phrases). The wall
  arithmetic was re-checked (30.96 × 12 = 371.5; × 1.37 = 509; × 1.70 = 865; 30.96/6 = 5.16).
- **Taken on the reviewer's word, not re-derived by the author:** the 64/64 pavement
  recomputation (the author's own §7.1 derivation is the thing it agrees with), and the RAM
  figures 4364.5 / 8729 / 11 248 MiB quoted from the probe node.
- ⛔ **No finding has been acted on.** The draft at `119acce` is unchanged, and remains the
  artifact before the owner's spec gate.

---

## 5. DISPOSITION — owner ruling PART 64, pins 277–286, 2026-09-28

⛔ **THE SPEC GATE IS *NOT APPROVED*. REVISE.** The ruling is landed verbatim as **PART 64**
of `docs/superpowers/2026-07-27-owner-ruling-crn-sigma-rule0.md`.

⭐ **The review DID ITS JOB (277):** reviewer B found **six** frame defects the requester's
list could not. ⭐ **D1–D17 STAND except as amended by 278–283.** ⚠ **P1–P4 are NOT ruled —
they are reviewed with the revision.**

### 5.1 OWNERSHIP, CORRECTED (278) — four of the six are the OWNER's

⚠ **§2 and the summary of this record attribute all six to the author. That attribution is
corrected by the ruling**, and the record keeps both so the correction is visible:

| defect | owner's or draft's | the ruling's words |
|---|---|---|
| **kernel exits mis-homed to 2G** (§2a) | ⚖ **OWNER's** | *"274(b) mis-homed the kernel exits to 2G. 219(c) verbatim: 'Both are Stage 2; neither is T6's to choose.' §7 has 2G decide POLES 'with the kernel decision in hand', so the decision PRECEDES 2G. **Pole handling is 2G's; the kernel exits are Stage 2's.**"* |
| **coverage map scoped to inherited items, three marks, no PLAN-WORK state** (§2b) | ⚖ **OWNER's** | *"276(b) scoped the coverage map to INHERITED items only, not Stage 2's own scope (§8) or its outbound contract (C2→2G), and gave it three marks with no PLAN-WORK state, although D1-D17 defer to the plan throughout."* |
| **"three rotations per tile"** (§1c, the D5 side) | ⚖ **OWNER's** | *"D5(d) wrote 'three rotations per tile'. Fork-e pin 4 says 'three epochs → three', and under D2's pooled law a rotation removes one epoch from all four tiles at once."* |
| **tier framed as "clears Tier 1"** (§1a) | ⚖ **OWNER's** | *"D10(d) framed the tier as 'clears Tier 1', pricing RAM and wall as if both were Tier-1 ceilings. `tier1_eligible` is RAM-only, correctly, and Tier 1 has no wall ceiling. **Wall binds, and it is a CALENDAR question.**"* |
| **`n_eff` never defined** (§1b) | ⭐ **SHARED** | *"the draft's … and the owner built D4/D5/D11 on the undefined n_eff without noticing: shared."* |
| **§2's rotation arithmetic** (§1c, the §2 side) | **the draft's** | *"The other two (n_eff never defined; §2's rotation arithmetic) are the draft's."* |

⭐ **All six are recorded as instances of §7-17 WORKING, with the count DERIVED** (278) — six
rows above, six findings in §§1–2.

### 5.2 The ordered revision list (286) — identical to PROGRESS's

| # | item | whose |
|---|---|---|
| **R1** | the **kernel decision item** (279): 219's exits — smaller km scale, latitude-aware halo, F-2 hull widening per 216 — each with its consequence for the **pavement key**, **n_eff's L** and **southern's frame** | ⚖ **→ OWNER** |
| **R2** | **n_eff DEFINED** (280): L, L_t, n_eff₀ and the aggregation fixed from fork-e pins 1(i)/2, the named scale by a rule needing **no per-tile λx**; then **EVERY bar gets its NUMBER** (D2, D4, D5, D13, D17's four). **A bar without a number is unrun** (§7-11). **D4 becomes mechanical only once L is fixed; the census operator must never choose the epochs by choosing L** | executor |
| **R3** | the **LORO unit** (281): three rotations, each removing one reference epoch from **all four tiles**; the four per-tile prediction errors are **NOT independent**; re-derive D5(d)'s era-level falsifier for the **pooled** law and state what **n = 3** can and cannot falsify | executor |
| **R4** | the **tier/calendar item** (282): accept **~36 d** of box time on the critical path **OR** elect Tier 2 — a **NEW spend row** (`tier2_probe` caps wall at 6 h; one era-fit exceeds it **5.16×**), triggering **`stage0:T18`**. ⛔ **`tier1_eligible` is NOT given a wall term: that would invent a ceiling nobody set** | ⚖ **→ OWNER** |
| **R5** | the **four-state boundary** (283): SETTLED (§ ref) · **PLAN WORK** (named, with the plan task that discharges it) · CARRIED TO C2→2G (named) · PLACED (with reason) — plus the **rebuilt coverage map** against (i) §8's own scope *(incl. per-era δ_m for EVERY mission, per-era R, and fork C's required-verbatim sparse-era sentence)*, (ii) the inherited items, and (iii) a **C2→2G LINE TABLE** in the C1→2 pattern. **Counts derived, never recalled** | executor |
| **R6** | **re-review** (284): reviewer A checks 278–283 were applied; ⭐ **a FRESH reviewer B** attacks the frame again, briefed independently and **NOT handed this review's findings as targets** (§7-17) | both |
| **R7** | the **spec gate** | ⚖ **→ OWNER** |

### 5.3 §7-19 WATCH (285)

⚠ **This is the draft's FIRST frame overturn.** ⛔ **If the revision is overturned again ON
THE SAME FRAME, the next ruling examines the DELIVERABLE, not the fix.**

### 5.4 What this session did and did not do (286)

**Did:** landed PART 64 verbatim; rewrote PROGRESS's CURRENT STATE (pin 154) with the R1–R7
list; appended this disposition.

⛔ **Did NOT:** edit the draft — *"The draft is NOT edited in this session"* — run anything,
open anything in Stage 2, fix the guard, regenerate or unfreeze the closure record, touch
seal v1, or spend its one v2. ⭐ **The revision begins in a FRESH SESSION.**
