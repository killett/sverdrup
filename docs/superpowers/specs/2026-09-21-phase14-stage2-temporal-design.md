# Phase 14 — Stage 2 design: temporal scaling at fixed domain

> ⛔ **DRAFT — NOT A SPEC UNTIL THE OWNER'S SPEC GATE.** Opened by owner pins 274–276,
> ruling PART 63 of `docs/superpowers/2026-07-27-owner-ruling-crn-sigma-rule0.md`, landed
> verbatim at `248a169`, 2026-09-21.
>
> ⛔ **NOTHING RUNS** (276d). No evaluation-bearing maps until the Stage-2 PLAN is approved
> (§7-1). Tasks 14–21 stay halted under pin 88 until that plan opens or re-homes them. The
> per-run tally guard stays unfixed (262d); the Gate-1 closure record stays frozen at
> `31e7569`; no seal, no supersession, no locked open.
>
> **Inputs read, in order:** the Gate-1 closure record
> (`docs/superpowers/2026-09-21-phase14-gate1-closure.md`, §4 contract and §5 obligations
> incl. S1–S6 and A-1); the program spec
> (`docs/superpowers/specs/2026-07-21-phase14-scaling-program-design.md` §3.1–3.3, forks C
> and E, §7, §8, §9); `docs/project-context.md` §5.3–5.4 and §7; ruling PARTs 59–63.

---

## 0. Status of this draft

Sections are appended **as each is validated with the owner**, per CLAUDE.md's "persist the
brainstorm as it forms". A section present here has been agreed; a section absent has not
been reached. The coverage map required by 276(b) is built last and its counts are
**derived by script, never recalled** (146b).

> ⚖ **REVISION IN PROGRESS — ruling PART 64 (pins 277–286) returned this draft NOT APPROVED;
> D1–D17 stand except as amended.** The ordered list is R1–R7 (pin 286). **R1 is DECIDED at
> PART 65 (pins 287–291, 2026-10-03)** and is folded in at §3.1 (R1a), §7.3a (R1b) and §20.1's
> 263.1 row. R2–R7 follow in order. Amendments are marked ⚖ with their pin; nothing is
> silently rewritten.

| section | content | state |
|---|---|---|
| §1 | The frame: what Stage 2 is, and what it is not | VALIDATED |
| §2 | Identification scope — the fit set | VALIDATED (D1) |
| §3 | The density law: pooled, with a pre-registered regime test | VALIDATED (D2) |
| §4 | The anchor reference epoch: e10, pure and seasonally balanced | VALIDATED (D3) |
| §5 | The +2 reference epochs: a pre-registered rule on measured n_eff | VALIDATED (D4) |
| §6 | Tolerance and power: se(b_i), the LORO falsifier, and a three-outcome test | VALIDATED (D5) |
| §7 | The pavement: measured before it is placed; tasks 14-17 split by step | VALIDATED (D6) |
| §8 | Ordering: the geometry step and the cheap sigma work; one packet | VALIDATED (D7) |
| §9 | e10's replacement holdout, the seal-budget map, and delta_j3 | VALIDATED (D8) |
| §10 | The amended rubric: simulated null, real-data falsifier, reachability, v2 | VALIDATED (D9) |
| §11 | Tier 2, S2's cloud leg, and the stage0:T18 correction | VALIDATED (D10) |
| §12 | Data availability by (mission, day); the census's acquisition; CRN's discharge | VALIDATED (D11) |
| §13 | One new surface, authorised by name: the geometry provider and GroundTrack | VALIDATED (D12) |
| §14 | The seasonal axis: a report-only diagnostic on covariate residuals | VALIDATED (D13) |
| §15 | The era no-op: a plumbing identity that CAN fail | VALIDATED (D14) |
| §16 | Four EXECUTOR placements (P1-P4): attribution, power, S5, S6 | PLACED — executor-authored, awaiting owner correction |
| §17 | Transferred-vs-refit per era: eligibility is not a schedule | VALIDATED (D15) |
| §18 | The revisit (225) declined and travelling; the OSSE exit (251(3)) answered | VALIDATED (D16) |
| §19 | Gate 2: every item has a bar; what a failure DOES separates them | VALIDATED (D17) |
| §20 | The coverage map (276b), counts DERIVED | COMPLETE — awaiting the §7-17 frame review (276c) |

⚠ **Numbering note:** ⭐ **This table is the index, and forward references cite number AND
name** — sections are appended as they are validated, so a bare number drifts. Earlier drafts
pointed §3's forward references at §4 and then §5; they are updated in place (pin 154), not
layered, and now read **§6 (tolerance and power)**.

---

## 1. The frame: Stage 2 is not Stage 2G (pin 274)

The boot agenda for this session asked "the Stage-2 spec" to settle everything Stage 1
inherited. That was the wrong unit. **The program spec gives each stage its own spec**, and
the two stages consume different contracts:

- **Stage 2 (§8)** — temporal scaling **at fixed domain**: multi-year on the tile roster,
  consuming **C1→2** plus forks c and e. Gate 2 accepts **no shipped product**, so
  **locked instruments do NOT open at Gate 2** (§3.3).
- **Stage 2G (§7)** — global assembly at one year, consuming **C2→2G**. Its accepted
  product is the program's **first** accepted product, and the locked set opens for the
  first time at **its** acceptance touch.

So this spec **SETTLES** Stage 2's items and **RECORDS** 2G's as named C2→2G
carry-forwards. It does not settle 2G's (274).

### 1.1 Two derivations that narrow the work before any decision is taken

**(a) §7 already bounds Stage 2's tile scope.** 2G ships "per-tile reference-epoch (2017)
s-fits **produced by Stage-2 machinery**". Stage 2 therefore owes the **machinery and an
identified covariate**, not a fleet-wide set of fits — 2G applies the machinery per tile at
2017, and every fleet tile has 2017 data. Stage 2's tile count is set by **what identifies
the covariate**, not by fleet coverage. This is why §2 is a question about identification
rather than about coverage.

**(b) The store schema already anticipates era.** `scripts/phase14_stage1_run.py:2612-2614`,
in the executor's own words: *"Era is DEGENERATE at Stage 1 (2017 only) and resolution is
single — that is a ROW COUNT, not a schema excuse: both keys ride every row so Stage 2 is a
row addition, not a migration."* Era and resolution keys already ride every Stage-1 row.
**Stage 2 adds rows; it does not migrate the store.** Any part of this design that would
require a schema migration is a finding to report, not a step to take.

### 1.2 What 275 corrected, recorded so it is not re-derived

- **The test-infra defects gate nothing** (275a). The four `seam_pair` CLI tests that fail
  only in combined runs (`tier1_eligible` reading live `/proc/meminfo`) and **A-1**'s
  trickling `@external` download produce **false FAILURES and STALLS, not false passes**.
  They cannot make a suite's evidence untrustworthy. They are **early housekeeping** in the
  plan, and they are **not a precondition on this spec**.
- **The ledger question is 2G's, and there are THREE ledgers** (275b): `phase14.locked_tally`,
  `phase13.miost.c2_acceptance.c2_touch_tally`, and the legacy top-level list. At 2G the
  opens cover c1 (locked gauges) and c2. ⭐ **Because Gate 2 opens nothing (§3.3), the
  Gate-1 closure tripwire stays GREEN through the whole of Stage 2 — a trip during Stage 2
  is a VIOLATION, not the tripwire's expiry.**

---

## 2. Identification scope — the fit set (D1)

**DECISION D1 (owner, 2026-09-21): the fit set is the four diverse tiles × three reference
epochs = 12 era-fits.**

Tiles: `equatorial`, `southern`, `quiet_gyre`, `kuroshio` — the four
production-representative boxes of `TILES` in `scripts/phase14_stage1_run.py:193-220`,
built under the `production-representative` frame convention (2° overlap on all sides).
`anchor` and the `seam_n|seam_s` pair are instruments, not regime samples, and do not carry
era-fits.

Reference epochs: **2017 (e10) by construction, plus two**, per fork E's recorded criteria
— constellation ≥4 net of locked exclusions, maximum joint density-support spread,
instrument-class coverage of the record's mission families. **The +2 are not yet chosen**;
that selection is **§5**'s business and is constrained by the sealed epoch table
(`sealed/phase14_evaluation_seal_v1.json` → `content.epoch_table`, 15 epochs, mirrored).

Consequences that follow from D1 and are therefore settled here:

- **Gate-2's leave-one-reference-out rotation set is 3 rotations × 4 tiles** (fork-e pin 4:
  ALL rotations run and reported — the covariate's claim-bearing test is the set, never a
  chosen rotation).
- The four regimes — western-boundary jet, equatorial, subtropical-quiet, Southern Ocean —
  all enter identification, so the regime spread in §3 is **measured, not assumed**.
- The southern tile enters with its framed geometry, and ⭐ **±66 is NOT breached by
  Stage 2's southern tile as framed.** From `S tiles.southern.frame`, with halo **1.0°** on
  all four tiles, the obs edges are **−65.0 / −43.8**; the poleward edge is **−65.0** and
  the **margin to ±66 is 1.0°** (Gate-1 pack §1.11, as corrected by owner pin 215).
  ⚠ **−66.13 is a different quantity**: it is kernel **OPTION 1**'s breach under a km-scale
  halo, and option 1 **was not elected** (219). It reaches Stage 2 only if a kernel exit
  widens the halo — **and the kernel exits are 2G's** (274b), not settled here. ⚖ **FORWARD
  POINTER: that homing was CORRECTED by pin 278(a) — the kernel exits are STAGE 2's — and
  Stage 2 then RULED them at pin 288: a WAIT with its exit named, Stage 2 running on the
  shipped kernel at halo 1.0°, so the margin above stands as written (§7.3a).** Fork-c
  pin 3's latitude-band validity mask still governs sparse-era readings; it bites on the
  **band**, not on a breach.

---

## 3. The density law: pooled, with a pre-registered regime test (D2)

**DECISION D2 (owner, 2026-09-21): fit (a, b) POOLED across the fit set, then test each
tile's own (a_i, b_i) against the pooled law as a PRE-REGISTERED reading, with the
tolerance stated before the numbers arrive.**

The model is fork E's, unchanged:

```
s(x, era) = s_spatial(x) · exp(a + b · log n_eff(x, era))
n_eff(x, window, era) = Σ_obs K(|x − x_obs|/L) · K(|t_c − t_obs|/L_t)
```

### 3.1 n_eff's kernel scale L — RULED (owner pin 287, R1a, 2026-10-03)

⚖ **AMENDMENT TO FORK-E PIN 2(i), recorded verbatim here per 287; the program spec's text is
not edited.** Pin 2(i)'s last clause — *"the fork-d pin-4 auto-follow linkage binds to the
NAMED scale"* — is **STRUCK for Stage 2 onward**. The halo follows the **SOLVER's**
operative kernel scale under fork-d pin 4, which **stands unchanged** (1.0° shipped practice
until a solver ruling moves it); it **never** follows the covariate's scale. Why the clause
had to go: with it, the only rung satisfying pin 2(i)'s two conditions (226.274 km) demands a
2.0349° halo and breaches `southern`'s 2.0° budget by 0.0349°; without it the two conditions
are jointly satisfiable, and fork E's own record — which **rejected** a covariate for being
*"config-dependent"* through the solver — argues for the decoupling (R1 item §§3–4).

⭐ **L = 226.274 km — a CONSTANT.** By the rule (287a): *the ladder rung inside the closed
interval of RECORDED λx across the fit set and the anchor, and among those the mid-ladder
one; tiles whose λx is `recorded_absent` contribute no endpoint and are never imputed.*
Derived once on Stage 1's recorded values — interval [141.9472, 232.5339] km (southern,
kuroshio; the anchor's 174.5211 interior), rungs inside {160.000, 226.274}, mid-ladder
{226.274, 320.000}, intersection **{226.274}**. ⛔ **The rule is NOT re-evaluated as Stage 2
records λx per era** — the scale would otherwise drift with the fits it conditions. Both of
pin 2(i)'s conditions are kept as written: rung 4 of 8, inside the recorded λx range.

⛔ **REQUIRED CLAUSE (287b): n_eff's obs support is each tile's FRAMED obs** — `obs_bbox` at
the operative halo — **never the global daily file** §12.2 acquires. That support is n_eff's
**sole** coupling to the solver: a later halo change re-runs the geometry step (D6/D7); it
**never redefines L**. So density near a frame edge falls exactly as the solver's information
does, because the same truncation is applied to both.

**Consequences for the key and the frame (R1 item §5, derived):** the pavement key is
**unchanged** — L is a choice of rung, not a `BasisSpec` field, and `halo=` no longer follows
it; `southern`'s frame is **unchanged** at obs edge −65.0, margin 1.0000°; ±66 is **not
engaged** by this choice at all.

▶ **L_t, n_eff₀ and the window aggregation are pin 280's (R2)** and are fixed in §3.2, which
follows. 287(c): R1a unblocks pin 280 on its own.

**Identification.** (a, b) are identified by **cross-era contrast at matched locations**
(fork-e pin 1(ii)): `s_spatial` absorbs era-invariant spatial structure, the covariate
absorbs what changes with constellation, and the fit is **constructed to enforce that
split, not hoped into it**. ⭐ **The contrast is per matched LOCATION, not per tile** — fork
E's own answer to the extrapolation objection records that density varies enormously
*within* one epoch (crossover diamonds vs mid-diamond voids, latitude convergence, per-window
mission dropouts). Each tile therefore contributes **more than three points; how much more is
DERIVED in §6 (tolerance and power)**, beside the tolerance and before any numbers arrive.

⛔ **The raw location count is NOT that figure.** Per-location contrasts are **not
independent**: mapping errors correlate in space, and every location in a tile shares the
same three era realisations. The quantity that sets the regime test's power is an
**effective sample size under spatial correlation**, derived in §6 (tolerance and power) —
never the location count, which would overstate it exactly as "three points per tile"
understated it.

**The regime test, pre-registered.** After the pooled fit, each tile's own (a_i, b_i) is
fitted separately and compared to the pooled law. A spread beyond a **stated tolerance** is
a **RECORDED FINDING that tables an owner decision — never a silent pool.** This is fork
E's own instrument for the extrapolation fraction ("a large extrapolation fraction is a
recorded finding TABLING an owner decision, never a silent clip") applied to the pooling
assumption, and it satisfies discipline **§7-11**: the condition under which the test could
fail is named at design time, beside the threshold, before the measurement.

⛔ **The tolerance is stated before the numbers arrive and is never loosened to manufacture
a pass** (§7-10). Its value is set in **§6 (tolerance and power)**, together with the effective-sample-size
derivation that gives it meaning, and neither is left to the executor.

**What C2→2G then carries:** one density law that reaches any fleet tile, **plus a measured
regime-spread row stating where it was tested** — the four regimes named, with the tested
density-support range and the extrapolation fraction beside it. A consumer must not be able
to read the pooled law as tested everywhere.

**Why not the alternatives**, recorded so they are not re-litigated: a bare pooled law
assumes regime-invariance across four regimes deliberately chosen to differ, and records
nothing about it — spending the roster's design and measuring none of it. Four per-tile
laws make no pooling assumption but do not reach fleet tiles Stage 2 never fit, forcing
C2→2G to state that the covariate does not transfer and leaving Stage 3 four laws with no
selection rule.

---

## 4. The anchor reference epoch: e10, pure and seasonally balanced (D3)

**DECISION D3 (owner, 2026-09-21): the anchor is e10, fitted on e10-PURE, SEASONALLY
BALANCED windows.** Not Stage 1's calendar-2017 set, not the six e10-keyed windows of that
set, and not a declared straddling set.

### 4.1 Purity — a reference fit is held to a stricter rule than D6

A reference-epoch fit is **fork E's ground truth**, so it is held to a stricter rule than
production keying: ⭐ **every window's full EXTENT lies inside the epoch, not merely its
centre.**

**D6 is not amended and is not extended.** Fork D6's accepted approximation — *"a
straddling window's map is mixed-constellation while its calibration key is
window-center-epoch — immaterial at one-mission deltas over 60-day windows"* — remains
exactly what it was: **a keying rule for PRODUCTION windows.** It does not reach reference
fits, where the straddle would put mixed-constellation observations into the very quantity
the covariate is identified against.

### 4.2 Seasonal balance — and the rule that binds the +2 epochs

The fit spans **whole years of pure windows inside the epoch**, so that **season cannot
alias into the era contrast**. e10 (2017-05-18 → 2018-11-27) holds one.

⭐ **The same rule binds the +2 reference epochs: an epoch that cannot hold a whole year of
pure windows cannot be a reference epoch.** This joins fork E's recorded criteria
(constellation ≥4 net of locked; maximum joint density-support spread; instrument-class
coverage of the record's mission families) as a **hard admissibility test**, applied before
the others rank anything.

**Derived from the sealed table** (`content.epoch_table`, 15 epochs), against the
production window geometry — `WindowPlan()` = 9 windows × 60 d at stride 45, full extent
**400 d** (Stage-1 placement −18 → 382; the minimum to cover 365 consecutive days at that
stride is 375 d):

| epoch | span (d) | net of locked | holds a pure year? |
|---|---|---|---|
| e00 | 944 | 3 | yes |
| e01 | 1698 | 3 | yes |
| e02 | 859 | 4 | yes |
| e03 | 1238 | 4 | yes |
| e04 | 1225 | 4 | yes |
| e05 | 623 | 3 | yes |
| e06 | 531 | 3 | yes |
| e07 | 733 | 3 | yes |
| e08 | 704 | 4 | yes |
| **e09** | **428** | 6 | yes — **28 d slack** |
| **e10** | 558 | 5 | yes — the anchor |
| e11 | 613 | 6 | yes |
| e12 | 632 | 6 | yes |
| **e13** | **452** | 7 | yes — **52 d slack** |
| e14 | 911 | 8 | yes |

⚠ **On this census the test eliminates nobody** — every epoch clears 400 d. That is a
**derived finding, not a formality**: the rule earns its place because **e09 (28 d slack)
and e13 (52 d slack) admit essentially one placement** of the production window set, so
their window grids are effectively forced; and because the test **binds immediately** if
the plan's window geometry grows. It is recorded as a criterion precisely so that a later
change of window plan cannot silently admit an epoch that can no longer hold a pure year.

### 4.3 Reuse is the PLAN's business, not the spec's

**The spec states the rule; it does not state a reuse list.** A Stage-1 window may be
reused **only if** (i) its full extent lies inside e10, **and** (ii) it sits on the e10
plan's own window grid. Which windows satisfy both is a plan-time determination against the
e10 grid, and this document deliberately does not enumerate it.

### 4.4 What Stage 1's 2017 run actually was — recorded, so no successor mis-reads it

Stage 1 applied **e10's role split — j3 held out, s3a assimilated — to all of calendar
2017**, with the constellation frozen across the year
(`PROBE_MISSIONS = ("alg","h2ag","j2g","j2n","s3a")`).

⛔ **The three e09-keyed windows are therefore NOT e09-valid fits.** They assimilated
**s3a**, which the sealed census makes **e09's holdout**. A window that assimilates an
epoch's holdout cannot be a fit for that epoch under fork C's role split.

**This is not a Stage-1 defect.** Fork C's execution belongs to Stage 2; Stage 1 ran a
frozen single-era configuration exactly as specified, and era was degenerate there by
design (S1). What the record above bounds is **any future claim that treats those windows
as e09** — that claim is refused here, in advance, with its reason.

### 4.5 The C2→2G line this creates

⭐ **§7's "2017" reference epoch means e10 under this rule.** But **2G's calendar-2017
product spans e09 and e10**, so the anchor label alone cannot carry calibration across that
boundary.

**C2→2G line (named, not settled here):** *the COVARIATE, not the anchor label, carries s
across the e09/e10 boundary in 2G's calendar-2017 product.* Recorded as a carry-forward
under 274(b); 2G's spec settles how it is applied.

### 4.6 Correction recorded — the reasoning that produced the rejected options

The question that led to D3 asserted that the e09/e10 boundary brought **"no constellation
change, only sampling"**. ⛔ **That is wrong for this covariate.** The boundary is **Jason-2
leaving its interleaved orbit (`j2n`) for the geodetic one (`j2g`)** — a **sampling-geometry
change, which is precisely what `n_eff` measures.**

The three e09-keyed windows are not a free era contrast, but **not for the reason given**:
they fail on the **season confound** (§4.2) and on the **role-split violation** (§4.4). The
corrected reason is recorded because the wrong one would have made a future reader think
the covariate is blind to an orbit change, which would be the opposite of its design.

---

## 5. The +2 reference epochs: a pre-registered rule on measured n_eff (D4)

**DECISION D4 (owner, 2026-09-21): the +2 are chosen by a PRE-REGISTERED RULE applied to
MEASURED n_eff. Class coverage does not force an early epoch.**

### 5.1 Coverage is by INSTRUMENT CLASS, not by mission — and it is already met

Fork E says **"instrument-class coverage"**, and the map is
`sverdrup.application.epoch_table.INSTRUMENT_CLASS`. Every claim below is **derived from
the sealed table and that map**, not asserted:

| derivation | result |
|---|---|
| e10's classes, net of locked | `alg`→ers-line, `h2ag`→hy2, `j2g`→poseidon, `j3`→poseidon, `s3a`→sentinel3 ⇒ **{ers-line, hy2, poseidon, sentinel3}** |
| e10's locked | `c2` ⇒ **cryosat** (present but **never assimilated**) |
| all classes in the map | {cryosat, ers-line, gfo, hy2, poseidon, sentinel3} |
| classes e10 lacks | {cryosat, **gfo**} — and **cryosat is locked**, so ⭐ **`gfo` is the only genuine gap** |
| epochs carrying class `gfo` (`g2`) | **e02, e03, e04 — and no others** |
| their sealed `fit_or_transferred` | **`fit` in all three** (fork-c pin 2) |
| the covariate's transfer targets = sealed `transferred` epochs | **e00, e01, e05, e06, e07** |
| classes those five carry, net of locked | **{ers-line, poseidon}** — and **both are covered by e10** |

⭐ **THE PURPOSIVE READING, AND WHY NO EARLY EPOCH IS FORCED.** The covariate exists to
carry `s` to the epochs that cannot be fit. Those are the sealed **`transferred`** epochs,
and they carry only ers-line and poseidon — **both already in the anchor**. `gfo` flies only
in e02–e04, and all three of those are sealed **`fit`** epochs, **eligible to carry their own
per-era fit** rather than leaning on the covariate. So the class e10 lacks is a class the
covariate is never asked to reach.

**The reconciliation — REWRITTEN by the owner (D15a), whose sentence the earlier version
was:**

> **Reference epochs identify (a, b). A `fit` epoch CAN carry its own per-era fit, and
> WHICH STAGE PRODUCES IT is recorded per era. Only `transferred` epochs rely on the
> covariate BY DESIGN.**

⚠ **The superseded wording said "Every `fit` epoch gets its own per-era fit."** That
**overstated**: ⭐ **the sealed role records ELIGIBILITY — at least four missions net of
locked, `fit+validate` — and NO ruling schedules a fit for all ten.** (Derived: `role ==
fit+validate` ⟺ net-of-locked ≥ 4, on all 15 rows.)

⛔ **AND THIS MAKES THE COVERAGE ARGUMENT ABOVE CONDITIONAL** (D15b). *"No early epoch is
forced"* holds **only while e02–e04 are REFIT when their calibration is produced.** ⭐ **If
Stage 3 TRANSFERS to any `gfo` epoch instead, the covariate meets a class it never saw, and
the `gfo` coverage gap REOPENS as a Stage-3 obligation.** Carried as a **C2→3 line**, not
only as a note here.

### 5.2 Correction — the unit error in the question that produced this

The question that led to D4 asserted: *"TOPEX, ERS, Envisat and GFO appear in no admissible
epoch except e02/e03/e04."* ⛔ **That is true of MISSIONS, and the criterion's unit is
CLASS.** TOPEX and Envisat are not classes — they are missions inside `poseidon` and
`ers-line` respectively, both of which e10 already covers.

⚠ **This is the same unit error the preview itself had just named** — mission count standing
in for density (§7-18). Naming a unit trap in one paragraph and committing it in the next is
recorded here rather than quietly fixed, because that is the failure mode discipline 18
exists to catch.

### 5.3 The rule, pre-registered

Applied to the **D3-admissible** epochs (whole pure year, `fit+validate`, ≥4 net of locked),
in this order:

1. **Minimise the transferred epochs' extrapolation fraction** against the **joint hull of
   the three reference epochs**, taken at the **WORST tile** (§7-16), **never the mean**.
2. Then **maximise log n_eff spread** — the leverage available to identify **b**.
3. Tie-breaks, in order: **sibling-having over sibling-less** (fork-c pin 4 weakens a
   ground truth by convolving map error with a prior-set holdout-error model; **e08 is the
   sibling-having four-net candidate**), then **lower cost**.

⭐ **AMENDED BY D8(f) — a CONSTRAINT, applied BEFORE the n_eff objective:** at least one of
the +2 epochs must **assimilate j3 by MISSION ID**. Derived from the census, the admissible
epochs that qualify are **e09, e11 and e12** (e13 carries `j3n`, e14 carries `j3g`/`j3n` —
different mission IDs; e02/e03/e04/e08 have no j3-family mission at all). This is what lets
E7 fit δ_j3 without touching e10 — see §9.6. ⚠ **The n_eff objective's value is recorded
BOTH with and without the constraint, so the constraint's cost is visible** rather than
absorbed.

⭐ **Using the transferred epochs' GEOMETRY in selection is legal.** `n_eff` is geometry
only — positions and times, **never values** — so step 1 consults where and when those
epochs were sampled, not what they measured. **Fork-c pin 1 forbids their READINGS in
selection and in model fitting, not their geometry.** The distinction is stated here so a
later reader cannot mistake step 1 for a sparse reading leaking into selection.

⛔ **AND THE AUDIT IS CONDITIONED ON ITS OWN OBJECTIVE.** The pre-registered
support-overlap audit will report an extrapolation fraction **under a selection chosen to
minimise exactly that fraction**. It is therefore **not an independent check of the
selection**, and no record may cite it as one. It remains a valid report of *how far out of
hull the transferred epochs sit under the chosen reference set* — which is what fork E asks
it for — and a large fraction still **tables an owner decision** rather than being clipped
silently.

### 5.4 Where it runs, and how the envelope is priced

**The n_eff census is the Stage-2 PLAN's first task**, not spec work — **nothing runs at
spec time** (276d). It runs on **sampled windows per epoch**, and the choice that follows is
**mechanical from §5.3** and **recorded before any era-fit dispatches**.

**The spec prices the fit envelope at the COSTLIEST admissible selection** (§7-16) — the
consequence is priced at the extreme that governs it, not at the midpoint of the candidate
set, so the authorised envelope cannot be exceeded by the rule's own outcome.

### 5.5 FINDING (Stage 2) — the Sentinel-6 class lookup returns None

⛔ **The sealed epoch table spells Sentinel-6 `s6a_lr`; `INSTRUMENT_CLASS` keys it
`s6a-lr`.** The sealed spelling is **absent from the map**, so
`INSTRUMENT_CLASS.get("s6a_lr")` returns **`None`** — Sentinel-6 is **classless** to every
class computation over e12–e14.

**Re-derived mechanically, and the sealed holdouts are UNAFFECTED:**

- The as-built selector reproduces **all 15 sealed holdouts and their criterion strings,
  zero mismatches**.
- Counterfactual with `s6a_lr → poseidon`: **no sealed holdout changes**.
- In **e12, e13 and e14** alike, `s6a_lr` **survives the climate-line step** (its class is
  `None`, and `None != "poseidon"`) and then **leaves at the sibling step**
  (`has_sibling` is False — it is the only classless mission in each of those epochs).
  Had it been classed `poseidon`, it would have left one step earlier, **at the climate-line
  step**. Either way it never reaches step 3, and the sealed holdout stays `s3a`.

⚠ **What IS affected:** **E7's class-match δ assignment** (the δ_j3 := δ_j2n precedent is a
class-match rule) and **any class computation over e12–e14** would see Sentinel-6 as
classless.

**The fix, and it is PLAN work, not now:** key the class map by the **sealed IDs**. ⛔ **The
seal is not touched**, and the fix **must reproduce the sealed table byte for byte before it
lands** — the re-derivation above is the test it has to pass.

---

## 6. Tolerance and power: se(b_i), the LORO falsifier, and a three-outcome test (D5)

**DECISION D5 (owner, 2026-09-21): se(b_i) comes from TWO-WAY BLOCK RESAMPLING,
CONDITIONAL ON THE ERAS; LORO is the PRE-REGISTERED FALSIFIER; and the regime test has
THREE outcomes, not two.**

### 6.1 The analytic route is rejected

⛔ **E-6's 3.1–3.9× does not travel here.** It was measured **for a different estimator on
a different quantity** — the realized **half-split spread** — and carrying the factor into
cross-era regression residuals would **move a number from where it held to where it does
not** (§7-18, the (u2) shape exactly).

⭐ **E-6's lesson is the METHOD, not its factor: a realized spread beats an analytic
`N_eff`.** That is what is inherited; the number is not.

### 6.2 b_i's uncertainty has THREE sources, and they are named

| source | scope | resampleable? |
|---|---|---|
| **SPATIAL** | within a tile | **yes** — by space blocks |
| **TEMPORAL** | within an era | **yes** — by **contiguous window blocks** |
| **ERA-LEVEL** | shared by **every location in the tile** | ⛔ **NO** — only three per tile, not resampleable within a tile |

⛔ **Spatial-only resampling measures the first source and SILENTLY DROPS the other two.**
That is why it is not the method, and the omission is recorded here so the rejected option
cannot return as an apparently-adequate shortcut.

⚠ **Windows overlap 15 days** (width **60 d**, stride **45 d** — derived from
`WindowPlan()`), so ⛔ **single windows are NEVER the resampling unit**: adjacent windows
share a quarter of their span. The unit is a **contiguous block of windows**.

### 6.3 Method — two-way block resampling, with block sizes pre-registered

**Space blocks × window blocks** gives **se(b_i | eras sampled)**, and ⭐ **the spec says
"conditional on the eras" every time it quotes that figure** — the conditioning is part of
the number, not a caveat attached to it.

Block sizes are **pre-registered**, not tuned:

- **Space blocks come from each tile's MEASURED residual correlation length.**
  ⛔ **NOT from λx.** Two reasons, both binding: λx is **RECORDED ABSENT at `equatorial`
  and `quiet_gyre`** (`recorded_absent: true`, pins 160a/161 — the map resolves no scale;
  not a scoring failure and not a value of zero), so it does not exist for half the fit
  set; and λx is a **RESOLVED scale, not an error correlation length** — the wrong quantity
  even where it is present (kuroshio 232.5339 km, southern 141.9472 km).
- **Sweep block size upward and take the LARGEST se on the plateau** (§7-16 — priced at the
  extreme that governs it, never the midpoint). ⛔ **The rule is stated before any numbers
  arrive** (§7-10), so the sweep cannot be stopped where the answer is convenient.

### 6.4 LORO is the FALSIFIER, not a free cross-check

⭐ **The leave-one-reference-out rotation set is the ONLY instrument that touches the
era-level component.** It is therefore not a bonus corroboration; it is the test of whether
§6.3's figure is honest.

**Pre-registered:** if LORO's held-out prediction errors **exceed what se(b_i | eras)
implies by a stated factor**, then **the era component dominates**, and the regime test is
reported as **CONDITIONAL ON THE ERAS SAMPLED, with its se UNDERSTATED**.

⛔ **Three rotations per tile can FALSIFY a too-narrow se; they cannot ESTIMATE the era
variance.** The spec says so in those words, so no successor reads three rotations as an
era-variance estimate.

### 6.5 The tolerance is the CONSEQUENCE threshold — and the test has three outcomes

⭐ **The tolerance is the `s` error a Δb causes at the WORST transferred epoch's hull
distance** (§7-16). ⛔ **The noise floor does NOT become the tolerance.** The noise floor
decides something different: **whether the test can speak at all.**

Three **pre-registered** outcomes:

| outcome | condition | what it means |
|---|---|---|
| **CONSISTENT** | spread within tolerance **AND** noise floor below the threshold | the pooled law stands, tested at the scale that matters |
| **DIVERGENT** | spread beyond tolerance | a **recorded finding that TABLES an owner decision** (D2's rule, never a silent pool) |
| **UNDERPOWERED** | noise floor **above** the threshold | ⛔ **regime-invariance is UNTESTED at the scale that matters** |

⛔ **UNDERPOWERED IS NEVER READ AS A PASS** (§7-10, §7-11). A test that could not have
detected a consequential spread has not found its absence — it is discipline 11's family
arriving in the regime test, and it is recorded under its own name precisely so the
green-looking reading cannot be quoted as consistency.

### 6.6 Reuse

Existing resampling machinery is reused **where it fits**. ⚠ **The resampling unit and the
estimator here are NEW**, so reuse is partial by construction, and **which pieces are reused
is PLAN business** — this document does not name them, and a claim that it "reuses the
existing bootstrap" would overstate what has been checked.

---

## 7. The pavement: measured before it is placed (D6)

**DECISION D6 (owner, 2026-09-21): SPLIT BY STEP, NOT BY TASK — and the pavement is
MEASURED before it is PLACED.**

### 7.1 The inference is now arithmetic

The earlier draft reasoned that the diverse tiles' element centres "should" move under a
global origin. ⭐ **That is no longer an inference. It is arithmetic, derived from the
witnessed frames through the repo's own code.**

**Chain of derivation, every link from the store or the layout code, nothing typed:**

- `basis_domain` is the per-tile pavement override (`Miost._spec_from`): `None` = the
  signed anchor box; otherwise `x0_km, y0_km` come from the tile. The Stage-1 runner sets
  it as `lonlat_to_km(solve_bbox.lon_min, solve_bbox.lat_min)`
  (`phase14_stage1_run.py:2448-2454`, `:3542-3550`). ⭐ **So element identity today IS a
  function of which tile is solving — pin 31's premise, confirmed in code.**
- `lonlat_to_km` (`miost_basis.py:168-179`): `x = (lon − BOX_LON[0])·KM_PER_DEG·cos(MID_LAT)`,
  `y = (lat − BOX_LAT[0])·KM_PER_DEG`, with `BOX_LON=(295.0,305.0)`, `BOX_LAT=(33.0,43.0)`,
  `MID_LAT=38.0`, `KM_PER_DEG=111.32`.
- Node positions are `x0_km − hw_j + i·step_j` with `step_j = alpha·lam_j`, `hw_j =
  SUPPORT·lam_j` (`miost_basis.py:106-121`, `_layouts`). The `hw` term is common to both
  lattices and cancels, so **congruence is `x0` modulo `step_j`**.
- `alpha` is the **signed** `spacing_alpha = 1.0656719505786896`, read from the store at
  `/winner/params` (also `/sobol/winner_params`, `/stage_b/winner_params`).
- `LADDER` is D1's **8 rungs**: 80, 113.137, 160, 226.274, 320, 452.548, 640, 905.097 km.

**Per-scale steps (km):** 85.254, 120.567, 170.508, 241.134, 341.015, 482.268, 682.030,
964.536. **Max possible miss is step/2.**

**Tile origins in the km plane:** kuroshio `(−14474.024, −779.240)`; southern
`(−7193.151, −10798.040)`; equatorial `(−8508.972, −4341.480)`; quiet_gyre
`(−3684.297, −7235.800)`.

**MISS FROM THE NEAREST ANCHOR-CONGRUENT NODE, PER SCALE (km):**

| tile | axis | λ=80 | 113.1 | 160 | 226.3 | 320 | 452.5 | 640 | 905.1 |
|---|---|---|---|---|---|---|---|---|---|
| kuroshio | x | 19.115 | 5.982 | 19.115 | 5.982 | 151.393 | 5.982 | 151.393 | 5.982 |
| kuroshio | y | 11.956 | 55.838 | 73.298 | 55.838 | 97.210 | 185.296 | 97.210 | 185.296 |
| southern | x | 31.836 | 40.870 | 31.836 | 40.870 | 31.836 | 40.870 | 309.179 | 441.398 |
| southern | y | 29.187 | 52.992 | 56.067 | 52.992 | 114.441 | 188.142 | 114.441 | 188.142 |
| equatorial | x | 16.404 | 51.287 | 16.404 | 69.280 | 16.404 | 171.854 | 324.611 | 171.854 |
| equatorial | y | 6.462 | 1.067 | 78.792 | 1.067 | 91.715 | 1.067 | 249.300 | 481.201 |
| quiet_gyre | x | 18.385 | 53.281 | 66.868 | 67.286 | 66.868 | 173.848 | 274.147 | 173.848 |
| quiet_gyre | y | 10.769 | 1.779 | 74.484 | 1.779 | 74.484 | 1.779 | 266.531 | 480.489 |

⭐ **NO TILE IS CONGRUENT AT ANY RUNG, ON EITHER AXIS.**

⚠ **AND THE KILOMETRE COLUMN IS THE WRONG UNIT FOR COMPARING RUNGS** (§7-18). The solve
responds to a miss as a **FRACTION of that rung's own step**, and the steps differ by 11×
across the ladder, so kilometres make coarse rungs look worse merely by being coarser. The
same misses **as miss/step** (max possible **0.5**):

| tile | axis | λ=80 | 113.1 | 160 | 226.3 | 320 | 452.5 | 640 | 905.1 |
|---|---|---|---|---|---|---|---|---|---|
| kuroshio | x | 0.224 | 0.050 | 0.112 | 0.025 | **0.444** | 0.012 | 0.222 | 0.006 |
| kuroshio | y | 0.140 | **0.463** | 0.430 | 0.232 | 0.285 | 0.384 | 0.143 | 0.192 |
| southern | x | 0.373 | 0.339 | 0.187 | 0.169 | 0.093 | 0.085 | **0.453** | **0.458** |
| southern | y | 0.342 | 0.440 | 0.329 | 0.220 | 0.336 | 0.390 | 0.168 | 0.195 |
| equatorial | x | 0.192 | 0.425 | 0.096 | 0.287 | 0.048 | 0.356 | **0.476** | 0.178 |
| equatorial | y | 0.076 | 0.009 | 0.462 | 0.004 | 0.269 | 0.002 | 0.366 | **0.499** |
| quiet_gyre | x | 0.216 | 0.442 | 0.392 | 0.279 | 0.196 | 0.360 | 0.402 | 0.180 |
| quiet_gyre | y | 0.126 | 0.015 | 0.437 | 0.007 | 0.218 | 0.004 | 0.391 | **0.498** |

⭐ **RESTATED IN THE RIGHT UNIT:** across all 64 (tile, axis, rung) cells the fraction runs
**min 0.002, median 0.223, max 0.499** against a worst possible **0.500**. The finest rung
(0.076–0.373) is **comparable to** the coarse rungs, **not** an order of magnitude below
them, and coarse rungs are **not systematically worse** — some are nearly aligned
(kuroshio x at λ=905.1 is 0.006; equatorial y at λ=452.5 is 0.002) while others sit at
essentially the maximum half-step (equatorial y at λ=905.1 is **0.499**). ⛔ **Deriving per
SCALE was still necessary** — the finest rung alone would have missed both the near-aligned
rungs and the half-step extremes — **but the reason is coverage of the ladder, not a
monotone worsening with scale.**

⚠ **Reconciliation with the owner's figures, per the owner's own rule.** The owner's
finest-rung numbers (kuroshio 19.156/11.954, southern 31.815/29.218, equatorial
16.428/6.474, quiet_gyre 18.375/10.790) are reproduced **exactly** by using the rounded
step **85.254** in place of the signed **85.25375604629517** (`alpha·80`). Each tile origin
lies **~170–200 steps** from the box origin, so the **0.244 m** step difference accumulates
to the 10–41 m gap — kuroshio: 170 × 0.000244 km = 41.5 m, matching its −0.041. **The
figures above are from the store and the layout code, and they stand.**

⛔ **AND THE EXPOSURE IS BROADER THAN CRN.** Moving element centres changes **the SOLVE**,
not only the draws: the basis elements are the solve's degrees of freedom. A record that
frames the pavement move as "a CRN re-key" understates it.

### 7.2 Split T14 itself — by step, not by task

| step | cost | when |
|---|---|---|
| **T14 geometry half** — choose the anchor-congruent global origin; compute per-tile, per-scale displacement | ⭐ **FREE**: no solver, no values, no maps | **Stage 2, FIRST** |
| **T15 survey** — alignment residual over every adjacent pair in the D1 production tiling | ⭐ **FREE**: geometry | **Stage 2, FIRST** |
| **T14 acceptance half** — the check-1 anchor re-solve for sha-equality against `phase13_winner_members.npz` | **~7 h, RAM-gated** | **only after the fork below** |

⭐ **THE FREE STEPS COME FIRST, IN STAGE 2, BEFORE ANY ERA-FIT.** They are geometry, so
§7-1's "no evaluation-bearing maps" does not bite, and they cost nothing to learn from.

### 7.3 Then the fork — and it is the OWNER's, not the executor's

- **Survey CLEAN** (one global origin serves the whole roster) → **freeze the pavement**
  (T14's acceptance re-solve), and **every Stage-2 era-fit runs on the frozen pavement.**
  Twelve era-fits over four tiles is the expensive product, and **2G's shipped calibration
  is made of them** (§7 of the program spec), so ⛔ **they must not sit on a lattice 2G
  abandons.**
- **Survey shows a LATITUDE-VARYING residual** (the ruling doc's open question 1: 31(a) is
  then **necessary but not sufficient**) → ⛔ **STOP at the survey and bring it to the
  owner. Stage 2 does not choose a pavement for the program.**

### 7.3a The kernel under the freeze — RULED WAIT (owner pin 288, R1b, 2026-10-03)

⚖ **The freeze proceeds on the SHIPPED kernel: halo 1.0°, `HALO_DEG` bound to
`operative_halo_deg()`, and `operative_halo_deg()` untouched** (288e). The high-latitude
kernel exit (219's cos-φ anisotropy) is a **RULED WAIT with its exit named** (261) — the
kernel question's **second** (219, now 288), and pin 290's §7-19 watch records that a
**third** deferral at 2G would indict the deliverable, not the exit.

**Why Stage 2 can afford it (288a):** the kernel is **era-invariant** (D5's frozen config), so
the shipped kernel's anisotropy — true-km zonal/meridional **0.74** at `southern`'s centre,
**0.60** at its core edge, **1.27** `equatorial`, **1.17** `quiet_gyre`, **1.03** `kuroshio`,
each derived from `lonlat_to_km`'s fixed `cos(MID_LAT)` as `cos φ / cos 38°` — is **the same
in every era and absorbed by `s_spatial(x)`** under fork-e pin 1(ii). Stage 2's
identification of (a, b) is not compromised.

**Why no active exit is Stage 2's to take (288b):** anchor identity is **MEMBER-LEVEL
equality** against the signed Phase-13 winner, and under a new metric the elements move, so it
**cannot be "re-established"**. A new kernel needs a **NEW signed baseline**, which only an
acceptance touch grants — and **Stage 2 opens nothing** (program spec §3.3). That blocker is
shared by every active exit, 216's hull widening included.

**The exit (288c):** 2G's spec decides **the kernel and pole handling TOGETHER**, as program
spec §7 wrote it, with a new kernel accepted on 2G's acceptance chain if elected. 2G starts
from the **per-axis halo reading** — the only reading that leaves halo room poleward of
`southern`, where the per-tile budget `66 + solve_bbox.lat_min` reaches zero at −66. The
±66 budget at each fleet tile's **solve-bbox poleward edge** is the constraint any 2G kernel
must satisfy (§7-16).

⭐ **Consequence for this section:** the pavement frozen here sits on the shipped kernel, so
§7.3's *"must not sit on a lattice 2G abandons"* now carries 288(d)'s explicit C2→2G line
(§20.1, 263.1 row) rather than an assumption of kernel continuity.

▶ **PLAN WORK (R1 item §6, ruled bound):** `HALO_DEG` derives from `operative_halo_deg()` —
one origin (§7-12) — with an identity guard (today's `params_key` bytes unchanged at 1.0)
**and a negative control that a halo change re-keys**. Changing `operative_halo_deg()`
alone is **REFUSED**.

### 7.4 T17 follows the freeze, wherever the freeze lands

T17 is **CRN-state-conditional** and gets **ONE sealed version** (pin 45/45d). ⛔ **Spending
it before the pavement is frozen wastes it.** It is therefore ordered behind the freeze,
not behind a stage label — which also answers **S3**, whose substance (one sealed version,
CRN-state-conditional) the closure record recorded as unnamed by obligations 1–12.

### 7.5 T16 → Stage 2

**T16 is doc-only** (pin 33's two-sided discipline 11, pin 35's procedural cost, the
process minors) and goes to **Stage 2**. ⚠ **Its tracker edge `blockedBy [15]` is
RE-DERIVED on re-homing, never carried across** — an inherited dependency edge is not
evidence that the dependency exists.

### 7.6 The inventory comes BEFORE the move

⛔ **Pin 31(d)'s "superseded configuration" list is built BEFORE the pavement moves, or
nobody can say what the move invalidated.** At minimum: **T4's `seam_rows` σ entries** and
**`seam_sigma_diagnosis`**; and **check** the T3 anchor std maps and any σ the C1→2
contract cites.

⛔ **THE SPEC MUST STATE WHETHER THAT MARKING SPENDS THE SINGLE AUTHORISED SUPERSESSION.**
If it does, **that is an owner decision at the time, never an executor's.** (The
supersession is currently **UNSPENT**, and nothing in this draft spends it.)

### 7.7 The durable fix, whichever branch runs

⭐ **Every Stage-2 product records its element-identity mode and lattice origin in its own
descriptor or row, from ONE origin in the code** (§7-12: the key has one origin). **A
comparison across two pavements is REFUSED BY CONSTRUCTION, not reported.**

⚠ **A silent mixed-pavement comparison is the same failure family as the tally-guard key
mismatch** (F1/262c): a check that reads one key while the world writes another, producing
a result that looks like evidence and is not.

---

## 8. Ordering: the geometry step and the cheap σ work run together (D7)

**DECISION D7 (owner, 2026-09-21): the geometry step and the cheap σ work run TOGETHER; T21
prices at the MEASURED r; ONE packet reaches the owner.**

### 8.1 r is the element-pairing fraction — fact, not inference

⭐ **CONFIRMED from the tracker, and recorded as fact rather than inference.** T20's
acceptance criterion reads **"(73a) SWEEP the paired fraction from 0 to 1"**, by pure
arithmetic over the stored per-member `acc` with **NO SOLVES**. T21 prices **"at least TWO
points at PARTIAL element pairing"**. So the `r` in the ρ model **is** the element-pairing
fraction, and **T14 is what drives it** — pin 31's stated purpose being that coincident
elements draw identically and adjacent-tile comparisons become PAIRED.

### 8.2 A LATENT CYCLE in the tracker, and how D6's split dissolves it

⛔ **The tracker contains a dependency cycle that its own edges cannot show.** T21's
acceptance criterion takes its partial-pairing points from *"what T15's alignment survey
says the production grid will actually contain"* — **in prose**. The edges read:

```
15 ← [14]          14 ← [1,2,3,4,13,18,19,20,21]          21 ← [20]
T21 ──prose──▶ T15 ──edge──▶ T14 ──edge──▶ T21        (closed, and invisible to the graph)
```

⭐ **D6's split-by-step dissolves it.** The geometry halves of **T14** (choose the
anchor-congruent origin) and **T15** (the survey) form **ONE geometry-only step that runs
first**. **T21 gains an EXPLICIT EDGE to that step**, replacing the prose dependence.

⛔ **T18's wall and the `[19, 20, 21]` edges stay on T14's IMPLEMENTATION + ACCEPTANCE —
the freeze — and NEVER on the geometry.**

⚠ **A dependency carried in prose is not a dependency the graph can enforce.** This is the
same family as §7.5's inherited edge: the tracker is only as truthful as its edges, and a
plan that reads the prose while the scheduler reads the edges will dispatch in an order
nobody authorised.

### 8.3 Concurrent, as PLAN tasks

⛔ **Nothing runs at spec time** (276d). As plan tasks:

| lane | contents | cost |
|---|---|---|
| **[A]** | the **geometry step**: T14's anchor-congruent origin + T15's survey | geometry only — no solver, no values, no maps |
| **[B]** | **T19** (DT scoring-track re-score) and **T20** (ρ(r) sweep over the reachable span) | T20 is pure arithmetic over stored `acc`, **no solves** |

**T21 runs after [A] AND T20.** ⭐ **It prices at the MEASURED post-freeze pairing fractions
from [A] — not the assumed r ≈ 0.9 — taken at the HIGHEST r any production seam will
carry** (§7-16: the extreme that governs it, never the middle).

### 8.4 T19 failing is NOT packet material

⛔ **Pin 19(b): a mismatch is a STOP.** T19's failure **goes to the owner the moment it
happens**, not bundled into the packet. A stop condition held back to travel with other
findings is no longer a stop condition.

### 8.5 ONE packet to the owner

| # | contents |
|---|---|
| 1 | **the survey** — clean, or latitude-varying (D6 §7.3's fork) |
| 2 | **the measured post-freeze r per seam** |
| 3 | **T20's result** — the closed form holds, **or** the measured curve replaces it (**73c pre-registers BOTH as acceptable**) |
| 4 | **T19's PASS** (its failure having already gone up alone, §8.4) |
| 5 | **T21's price** |
| 6 | **the m question** — pin 53 reopened pin 31's m-rejection and ordered **m=137 PRICED, not chosen**: m ≥ 137 (129 at factor 1.00, **137 at 1.03**, 148 at 1.07), and pin 57 put it at **27% of the RAM knee — +0.5% predicted peak, ×1.37 wall, inside the box's own ×1.70 drift**. Pin 53 placed the remedy **after T14/T15, with Rule 0.b, in T17**. ⭐ **Era-fits are ensemble products at a fixed m, so m is settled BEFORE them.** |

**The owner decides:** whether to buy the high-r validation, **and whether it must precede
the freeze**; the **freeze** itself (T14's acceptance re-solve); and **m**.

### 8.6 Scope separation — the era-fits do NOT wait on σ validation

⭐ **Stage 2's four diverse tiles share NO seams**, so **r never enters their era-fits.**

The σ chain serves **the seam instruments and 2G's fleet.** It gates **the FREEZE** —
through T19, T20, and the owner's ruling on T21's price — and reaches the era-fits **only
transitively, through the freeze.**

⛔ **The spec states this explicitly so that nobody reads the era-fits as waiting on σ
validation itself.** They wait on a **pavement decision**; they do not wait on the ρ model.

---

## 9. e10's replacement holdout, the seal-budget map, and δ_j3 (D8)

**DECISION D8 (owner, 2026-09-21): the replacement holdout is an ADDITION, not a
supersession; δ_j3 is fitted ELSEWHERE; and the BUDGET MAP comes first.**

### 9.1 The chain, confirmed — and two facts recorded

Running fork C's own `_select_holdout` on e10's sealed mission set:

- ⭐ **e10 → `alg`**, criterion **`non-climate-line+min-geometry-distortion`**.
- The **sibling step is SKIPPED**: none of `alg` (ers-line), `h2ag` (hy2), `s3a` (sentinel3)
  has an assimilated sibling at e10. So the replacement is **sibling-less**, and **fork-c
  pin 4's caveat travels with it** — its structured-error parameters come from PUBLISHED
  budget priors, and the reading convolves map error with a prior-set holdout-error model.
- ⭐ **The chain returns `alg` EVEN WITH j3 IN THE POOL.** Candidates net of locked are
  `['alg','h2ag','j2g','j3','s3a']`; j3 is removed at the climate-line step as `poseidon`.
  **So the sealed `j3` is the `signed-workhorse-by-construction` OVERRIDE, not the chain's
  answer** — e10 is the only row in the table whose criterion is that override.

### 9.2 It is an ADDITION, not a supersession

⛔ **Seal v1's e10 row (holdout `j3`) is CORRECT** — for the **five-mission workhorse**,
which is exactly the role split D3's anchor inherits (§4.4). The replacement serves a
**DIFFERENT configuration**: the **elected** one, 2G onward.

⭐ **So it is ADDED, keyed by CONFIGURATION. Seal v1 is NOT modified.** A **new sealed
record** plus a **new mirror node** — and brand-new nodes sync freely — **spends no
budget**.

⛔ **Replacing the row would break D3**, whose anchor is defined on the five-mission role
split. The two configurations coexist; neither overwrites the other.

### 9.3 ONE registry — logical, from one origin

Fork-c pin 2 makes the census **the single registry**, so the addition enters it as a
**CONFIGURATION key**: ⭐ **one reader resolves `(epoch, config) → holdout` from ONE origin
in the code** (§7-12).

⚠ **Reconciliation, stated so no reader trips on it:** "one registry" is **logical, not
one file**. The resolver is single-origin; it spans **seal v1** and the **new sealed
record**. ⛔ **A side file that some reader can miss is the tally-guard failure again**
(F1/262c) — one writer, another reader, two keys.

### 9.4 Stage 2 chooses AND seals the addition

⛔ **Stage 2 both chooses and seals it**, as a precondition it **discharges before C2→2G**.
257's words: *"Stage 2 must resolve it before 2G runs."* ⚠ **"2G seals" contradicts 257**,
and the earlier draft option that said so is withdrawn. **The seal EVENT is an owner act,
authorised at the time.**

### 9.5 THE BUDGET MAP — derived, because it existed nowhere

The record names limited instruments in near-identical words. **Derived:**

| instrument | source pin | wording | allocation |
|---|---|---|---|
| **the seal's one sanctioned change** | ⭐ **pin 36(d)**, verbatim: *"HOLD THE SEAL AT ONE VERSION. Do not ship v2 and patch to v3 — pin 35 charges a coverage re-walk per version, and a sealed record containing a rule known to be unusable is worse than a delayed one."* | one further sealed version | ⭐ **ALREADY ALLOCATED**: pin 45 defers the whole rubric amendment (0.a + 0.b) to **ONE sealed version after T14 and T15** — **T17 spends it, once** |
| **"the single authorised supersession"** (pin 264e, closure §6, pin 196d context) | ⛔ **no defining source pin exists** | — | — |

⭐ **THE FINDING: THESE ARE ONE BUDGET, NOT TWO.** The seam rubric's thresholds live
**inside the evaluation seal** — `clean_max = 1.0` and `elevated_max = 2.5` at
`content/instruments/seam` of `sealed/phase14_evaluation_seal_v1.json` (which is also what
pin 36 reads when it says "against sealed clean_max 1.0 / elevated_max 2.5"). `sealed/`
holds only that file and the Gate-0 snapshot. So **T17's one sealed rubric version IS a v2
of that file, produced through `supersede`** — and "the single authorised supersession" and
"the one sanctioned seal change" name **the same thing**, already allocated to T17.

⛔ **A TERMINOLOGY HAZARD, recorded.** The record uses "supersession" for **two different
mechanisms**, and only one is budgeted:

- **Store-node supersessions** — `supersessions.json` already records **FOUR spent**:
  `reachability_declarations` (pins 148/145), `osse_pricing` and
  `projection_declarations` (pin 246), `osse_pricing` again (pins 250–252). **These are
  routine and unbudgeted.**
- **The SEAL supersession** — the single budgeted one, allocated to T17.

⭐ **So D6(f)'s question is now answerable in principle:** pin 31(d)'s
superseded-configuration marking is a **store-node** operation, of the kind already spent
four times, and **does not claim the seal budget** — provided it marks nodes rather than
amending seal content. ⛔ **Anything that would claim the SEAL budget is an owner decision,
never the executor's**, and nothing in this draft claims it.

⚠ **Also derived:** `_ENVELOPE_KEYS = ("supersedes", "signoff", "date")` — envelope
metadata only. **`epoch_table.holdout` is CONTENT**, so changing it in place would require
`supersede`. §9.2's addition is precisely what avoids that.

⭐ **THE PHRASE IS SETTLED HERE, BECAUSE IT HAS BEEN USED LOOSELY** (D9g). **"The single
authorised supersession" MEANS THE SEAL's v2** — and it has been used loosely in mirror
contexts, **including the Gate-1 closure ruling's own 264(e) and 267**. The mirror's
**store-node supersessions are a SEPARATE instrument with NO numeric cap**: four spent, each
deliberate and each with its recorded reason. ⛔ **A reader who counts the four against "the
single authorised supersession" concludes the budget is overspent three times over. It is
not: they are different instruments.**

⭐ **PIN 31(d) DOES NOT COMPETE FOR v2 — confirmed by reading it.** Verbatim: *"Stage-1 σ
rows become measurements of a SUPERSEDED configuration once (a) lands. Mark them so; do not
carry them into the C1→2 contract as σ readings."* It concerns **σ rows in the store**, not
seal content, so it is a store-node operation of the uncapped kind. **D6(f)'s question is
answered: the marking spends no seal budget.**

### 9.6 δ_j3 without touching e10

**D4's rule gains the §5.3 constraint**, applied **before** the n_eff objective: at least
one +2 epoch **assimilates j3 by mission ID**. Qualifying admissible epochs, derived from
the census: **e09, e11, e12**. **E7 fits δ_j3 there.**

⭐ **That can discharge 256's provisional inheritance under ONE STATED ASSUMPTION: a given
mission's δ is ERA-INVARIANT — an instrument property, not a constellation property.**

**Why the assumption is reasonable, stated rather than assumed silently:** the mission-ID
granularity **already separates orbit phases** (`j3`, `j3n`, `j3g` are distinct IDs, as are
`j2`/`j2n`/`j2g`), so what an era changes is the **constellation context**, not the
instrument.

⛔ **WHAT WOULD FALSIFY IT, named at design time** (§7-11): δ_j3 fitted at **two** epochs
that both assimilate j3 disagreeing **beyond se**. If the +2 include two of
{e09, e11, e12}, that test is **free and it runs**; if they include only one, ⚠ **the
assumption is carried UNTESTED and the spec says so** — δ_j3 is then fitted but its
era-invariance is unverified, which is not the same as verified.

---

## 10. The amended rubric: simulated null, real-data falsifier, reachability, v2 (D9)

**DECISION D9 (owner, 2026-09-21): the null is SIMULATED THROUGH THE REAL BASIS; the
falsifier is a REAL-DATA NULL; reachability is CHECKED BEFORE SEALING; and v2 is COMPLETE
OR NOTHING.**

### 10.1 The order

```
freeze (T14 acceptance, survey CLEAN)
  → null harness            (§10.2)
  → falsifier               (§10.3)
  → reachability            (§10.4)
  → T17 authors and SEALS v2 (§10.5)
```

⛔ **Deriving the constants from the run they will score is REFUSED.** That is discipline
11's **(i6)** family — the s*/χ² shape, one number read twice, where agreement is an
identity rather than corroboration.

### 10.2 SIMULATE, don't estimate

⭐ **Pin 36(b)'s N=200k harness draws through the FROZEN pavement's ACTUAL BASIS at the
production geometry**, with **pairing taken element by element from D7's geometry step**, so
**spatial correlation and ρ EMERGE rather than being parameterised.**

The factor is read as **a stated quantile of the simulated `RMS(σ_delta)/F_ens`
distribution at a stated confidence**, with **36(b)'s explicit margin for the asymptotic
`σ²/(2(m−1))` approximation**.

⭐ **NO `N_eff` IS ESTIMATED AT ALL.** D5's lesson is *realised* spread; here the spread is
**simulated directly**, which is the same lesson taken one step further — and it is why
E-6's overturned estimator is not needed in this path either.

⚠ **FALLBACK, only if element-level simulation is infeasible:** parameterise by the **ρ(r)
the owner rules in D7's packet** (closed form or measured curve), and ⛔ **the SEALED rubric
states its VALIDITY RANGE IN r.** Beyond T20's validated span, with the high-r validation
not bought, **the factor carries that exposure IN WRITING** — pin 73's **7.166× at r = 0.9**
named in the sealed record itself, not in a commit message.

### 10.3 The falsifier is a REAL-DATA null with no seam by construction

**The within-tile half-split at the frozen pavement** — the diagnosis's own discriminator,
*"a seam artifact cannot appear inside a single tile"* — ⭐ **on a region DISJOINT from the
seam strip the rubric will score.**

**Pre-registered tolerance:** the real-data statistic **must fall inside the simulated
null's stated band.**

⛔ **If it does not, the synthetic null misses real structure: NOTHING SEALS, and it goes to
the owner.** It **runs before sealing** and is **read once**.

⚠ Why this is the right falsifier rather than a second simulation: a simulated null can only
be wrong in ways the simulation does not model. **A real-data null with no seam by
construction can.**

### 10.4 Reachability BEFORE sealing (36c)

Compute **CLEAN and ELEVATED reachability** at the **production geometry** and at **the m
the owner rules** (pin 53).

⛔ **If CLEAN is unreachable, DO NOT SEAL.** Pin 36(d) in its own words: *"a sealed record
containing a rule known to be unusable is worse than a delayed one."* **The owner decides m
or geometry.**

⚠ This is pin 36's reachability condition used as a **precondition on sealing** rather than
as a property recorded after it — which is the difference between a rule that can fail and
one that merely describes.

### 10.5 v2 IS THE LAST VERSION — so inventory v1 first

Because pin 36(d) holds the seal at **one further version**, ⭐ **v2 is COMPLETE OR
NOTHING**: anything Stage 2 knows must change and leaves out has **no second chance.**

**Before T17 authors v2, every field of `sealed/phase14_evaluation_seal_v1.json` is marked
RIDES IN v2 or STAYS AT v1, with its reason.** First pass, derived from the file:

| field | disposition | reason |
|---|---|---|
| `instruments.seam.clean_max` (1.0), `.elevated_max` (2.5) | **RIDES IN v2** | these **are** the rubric amendment |
| `instruments.seam.metric`, `.oracle`, `.rubric_doc` | **RIDES IN v2 if** the amendment changes the metric or its document | decided at authoring, **recorded either way** |
| `instruments.schema_version`, `schema_version`, `descriptor_schema_version` | **TBD at authoring** | rides only if the amendment changes shape; the decision is recorded, not left implicit |
| `epoch_table` (15 rows) | **STAYS AT v1** | D8: the replacement holdout is a **configuration-keyed ADDITION** in a separate record; replacing the row would break D3 |
| `c2_era_windows` (10) | **STAYS AT v1** | 2G's acceptance touch reads them; Stage 2 changes nothing |
| `dev_gauges` (96), `locked_gauges` (39), `split_seed`, `screening` | **STAYS AT v1** | the pre-registered sealed split; changing it would void the independence the locked tier rests on |
| `instruments.groundtrack`, `.insitu_nulls`, `.spectral_fidelity` | **STAYS AT v1** unless obligation 7 (GroundTrack, 106) requires otherwise — ⚠ **flagged, not settled here** | `groundtrack` already declares `per_era: true` |

⭐ **Pin 31(d) does NOT compete for v2 — confirmed** (see §9.5): it marks **store σ rows**,
not seal content.

### 10.6 D8(b)'s holdout addition stays OUT of v2

⛔ **It changes no v1 content**, so it does not need v2. And ⭐ **coupling a mechanical,
already-derived holdout to the stage's hardest open derivation would let a rubric failure
block 2G's precondition** — 257's requirement would then hostage itself to §10.4's
"do not seal".

Two instruments, two artifacts, **no shared failure mode**.

---

## 11. Tier 2, S2's cloud leg, and the `stage0:T18` correction (D10)

**DECISION D10 (owner, 2026-09-21): the cross-host slot waits on `stage0:T18`; STAGE 2's
TIER IS ARITHMETIC; and the precondition MOVES INTO THE LADDER.**

### 11.1 `pending-T18` is the STAGE-0 tracker's Task 18 — and the wall DOES know

⛔ **A FINDING I ASSERTED IS WITHDRAWN.** I reported that the wall "does not know what it is
waiting for", having searched **`stage1:T18`**'s body. **I read the wrong tracker.**

**Verified** in `docs/superpowers/plans/2026-07-22-phase14-stage0-foundations.md.tasks.json`:

- **`stage0:T18` = "Task 18: Tier-2 probe — cost + BOTH determinism measurements (0b-3)"**,
  status **`blocked`**, `blockedBy [15, 16, 17]`.
- ⭐ **It IS the cloud leg**: a SkyPilot task (`sky/phase14_probe.yaml`, pinned image),
  **CRN cross-host bit-exactness** (the Stage-0 half of gate 4), **cross-host single-thread
  solve delta**, same-host multi-thread spread → the two recorded tolerances; ceiling
  **US$25 / 8 vCPU / 64 GiB / 6 h**; **"Runs when owner supplies credentials."**
- ⭐ **Its own body carries the slot verbatim:** *"restructured as a ladder-enforced
  precondition on FIRST TIER-2 PRODUCTION USE. Cross-host tolerance slot = pending-T18.
  Runs when owner supplies credentials."*

⭐ **So the wall knows exactly what it waits for.** `stage1:T18`'s body never mentions
cross-host because **the slot was never its business.**

### 11.2 The collision is OLD — and neither record is edited

Two existing records read `pending-T18` against the **wrong tracker**:

| record | what it says | status |
|---|---|---|
| the posted **Gate-1 pack**, row 4 | *"cross-host slot `pending-T18` — and **T18 is a Stage-2 task (pin 86c)**"*; §1.11 repeats it: the slot *"is Stage-2 work (pin 86c), not a Stage-1 wait"* | ⛔ **SUPERSEDED** by the closure record — **not edited** |
| the **2026-08-01 stale-criteria sweep**, lines 160–162 | *"**pin 86(c) sent T14–T21 to Stage 2**, so 'pending-T18' now means pending a *Stage-2* task — a materially weaker promise at Gate 1 than when written"* | ⛔ **HISTORY** — **not edited** |

**Pin 86(c) moved `stage1:`T14–T21.** `pending-T18` names **`stage0:`T18**, which pin 86(c)
never touched — so the sweep's "materially weaker promise" worry **dissolves under the
correction**: the slot still waits on a blocked Gate-0 cloud probe, exactly as written.

⭐ **THE STAGE-2 SPEC RECORDS THE CORRECTION, and from here on EVERY task reference in the
spec is TRACKER-QUALIFIED** — `stage0:T18`, `stage1:T18`. A bare "T18" is ambiguous across
two trackers and has already misled two records.

**A plan-stage item adds a FORWARD POINTER to the witnessed `cross_env` node under pin 64,
naming the namespace.** ⛔ **No node is edited.**

### 11.3 Stage 1 never made Tier-2 production use

**Confirmed from the rows.** `phase14.stage1.tier2_probe_kuroshio_m100` is a **Tier-1 sizing
probe on the box**:

- *"Measured, CONVERGED: **3.440 h for ONE window** at m=100 on kuroshio. Per tile (×9
  windows) **31.0 h**; four tiles **123.8 h**."* ⭐ **31.0 h per tile against the
  `tier2_probe` row's 6 h ceiling** — the work could never have run under that ceiling.
- Its RAM finding is stated against **Tier 1**: *"the ≥9431 MiB **Tier-1** requirement was a
  MODEL figure (2 × 4715.6). Measured peak is 4365 MiB, so the **2× launch rule** needs
  ~8730 MiB."*
- The pack's own §1.11: the four legs *"ran under the pin-155 launch gate and the pin-156
  watchdog on that box; **no Tier-2 cloud ceiling was reached or used**."*

⚠ **Where the ambiguity came from:** the pack calls them *"the four Tier-2 legs (19.67 /
27.48 / 25.54 / 26.03 h)"*, in the **local memory-class** sense of E-16 / `stage1:T22`'s
"Tier-2 crossing" — **not** the ladder's `Tier.CLOUD_NODE` sense that S2's precondition keys
on. ⛔ **Two meanings of "Tier 2" in one program; the spec uses the LADDER's.**

### 11.4 Stage 2's tier is ARITHMETIC, not an election

D4(d) already prices the fit envelope at the **costliest admissible selection**. ⭐ **Price
that costliest era-fit — the densest admissible epoch at the highest-`n_obs` tile — against
Tier 1: RAM by the 2× launch rule under `tier1_eligible`, and wall with the ×1.70 margin
(pin 28).**

| outcome | consequence |
|---|---|
| **it CLEARS Tier 1** | era-fits **never need Tier 2**, and **S2 does not bind them**. ⚠ If the owner later **ELECTS** Tier 2 for throughput, **that election triggers S2** |
| **it does NOT clear** | **S2 binds before the first Tier-2 fit**, and **`stage0:T18` must discharge first** |

⭐ **The same verdict is applied to EVERY other Stage-2 compute consumer when it is priced:**
the anchors-only revisit, `stage1:T21`'s high-r validation, the OSSE.

### 11.5 Make "ladder-enforced" MECHANICAL (plan work)

**Verified as built:** `authorize()` (`src/sverdrup/application/ladder.py`) already **WAITs
on any task class without a spend row** — *"no pre-registered spend row for {task_class}:
the owner must register one before any spend (executor-set spend never happens)"* — and
`STAGE0_SPEND_TABLE` holds only `tier2_probe` (CLOUD_NODE, $25 / 8 vCPU / 64 GiB / 6 h),
`cmems_downloads` and `stage0_default`. ⭐ **So Tier-2 production needs an owner-added row.**

⛔ **BUT NOTHING CHECKS `stage0:T18`'s EVIDENCE WHEN THAT ROW IS ADDED** — `SpendRow` has no
evidence field at all.

**The fix (plan work):** a Tier-2 **production** row carries a **required-evidence field
naming `stage0:T18`'s witnessed node**, and ⭐ **`authorize()` REFUSES while that node is
absent** — so the precondition lives **in the code path that grants the spend, from ONE
origin** (§7-12), rather than in a sentence someone must remember.

**Tests:** a row with the evidence **absent** refuses; with it **present**, it authorises.

⚠ This is the same correction shape as §7.7 and §8.2: a rule enforced by the mechanism that
acts, not by a note beside it.

---

## 12. Availability by (mission, day); the census's acquisition; CRN's discharge (D11)

**DECISION D11 (owner, 2026-09-21): availability is by (MISSION, DAY); the census fetches
only its SAMPLED windows; CMEMS throughput is MEASURED, not inherited.**

### 12.1 The availability check used the WRONG UNIT — corrected

⛔ **My check asked which mission DIRECTORIES exist.** The census needs coverage by
**(mission, date range)** (§7-18: the unit must be the thing that varies). Re-derived from
the per-day files in `data/cmems_my/<mission>/`:

| mission | local days | first → last | span | missing days in span |
|---|---|---|---|---|
| `alg` | 427 | 2016-12-01 → 2018-01-31 | 427 d | 0 |
| `h2ag` | 398 | 2016-12-01 → 2018-01-31 | 427 d | **29** |
| `j2n` | 154 | 2016-12-01 → **2017-05-17** | 168 d | 14 |
| `j2g` | **66** | 2017-07-11 → 2017-09-14 | 66 d | 0 |
| `j3` | 427 | 2016-12-01 → 2018-01-31 | 427 d | 0 |
| `s3a` | 427 | 2016-12-01 → 2018-01-31 | 427 d | 0 |

⭐ **`j2n` ends 2017-05-17 — the day before the e09/e10 boundary (2017-05-18).** The sealed
boundary *is* the Jason-2 orbit change, confirmed to the day. (This also vindicates D3(e):
the boundary is a real sampling-geometry change, which is what `n_eff` measures.)

⛔ **AND e10 IS NOT FULLY LOCAL EITHER — the owner's suspicion is confirmed.** e10 spans
2017-05-18 → 2018-11-27 (558 d); D3's pure year needs the 400 d `WindowPlan` extent, i.e.
data through **2018-06-22**, but local data ends **2018-01-31**. Coverage *inside* e10:

| mission | local days inside e10 | of ~400 needed |
|---|---|---|
| `alg`, `j3`, `s3a` | 259 | ~65% |
| `h2ag` | 250 | ~63% |
| ⭐ **`j2g`** | **66** | ⛔ **~17% — THE BINDING CONSTRAINT** |

⚠ **So even the ANCHOR needs acquisition, and `j2g` needs the most of it.** A corollary
worth recording: Stage 1's own frozen five-mission config had `j2g` present for only 66 days
of calendar 2017 locally — an **acquisition** limit, not a mission-lifetime one (Jason-2 flew
its geodetic orbit from 2017-07 to 2019-10).

### 12.2 It is NOT circular — the census fetches only its sampled windows

D4(d) already puts the census on **sampled windows**, and `n_eff` is **geometry only**, so
⭐ **the census fetches only the days its sampled windows cover** — never a candidate epoch
in full.

**Pre-registered sampling, stated before any fetch:** per candidate epoch, **K windows spread
across the seasons**, inside **D3-admissible spans**, **per tile** — with **K and the
placement rule fixed in advance**.

**Pricing basis, MEASURED from the local files and never by mission count:**

- ⭐ **0.444 MiB per (mission, day)** (1899 files, 843.5 MiB; per-mission medians 0.429–0.500
  MiB).
- A 400-day pure year for **one** mission ≈ **0.17 GiB**; an e10-like era-fit at five
  missions ≈ **0.87 GiB**.
- Acquisition is therefore priced as `Σ over (mission, day)` — **the unit that varies** —
  not as a mission count.

⚠ **THE SUBSETTING QUESTION IS ANSWERED FROM THE SERVICE'S OWN BEHAVIOUR, NOT ASSUMED.** If
the service supports variable or region subsetting for this product, **fetch coordinates
only**. If it does not, ⛔ **the native daily file is the unit, and "coordinates only" saves
DISK, not BANDWIDTH.** The spec says which applies **after checking**, and my option 1
overstated the saving by assuming the former.

### 12.3 Selection by acquisition cost is REFUSED

⛔ Acquisition cost must not shape **which epochs identify the covariate** — that is outside
D4's pre-registered objective. ⭐ **Cost enters ONLY as D4's last tie-break, where it already
sits** (§5.3 step 3).

### 12.4 Acquiring every candidate in full is UNNECESSARY

Full data is needed only for the **three SELECTED** epochs, **acquired after selection**.
The candidates are only ever sampled.

### 12.5 A-1 does NOT transfer — but its MECHANISM does

⛔ **The 16 KB/s was measured on the MEOM mirror serving dc2021a/dc2023, NOT on Copernicus
Marine.** Carrying that number to this path would be the same unit error §7-18 catches.

⭐ **Measure CMEMS throughput for this path on its own** — one day-file per candidate mission,
timed — **before pricing any wall.**

⭐ **What DOES transfer is A-1's MECHANISM: a trickle defeats a transport-failure guard.** The
acquisition code therefore carries a **throughput floor with a stall watcher**, not error
handling alone. ⚠ **A-1 itself stays test-infra work, as the closure record has it** — my
earlier reclassification of it onto the acquisition critical path is withdrawn.

### 12.6 Pin 87 — the CRN defect is discharged by MEASUREMENT, not by construction

⭐ **T14's freeze removes the MECHANISM** of the CRN production defect — pin 31(c)'s
manufactured σ gradient at tile boundaries, which pin 87 calls "a property of the shipped
system, not of an instrument".

⛔ **BUT THE DEFECT IS DISCHARGED ONLY BY A POST-FREEZE MEASUREMENT showing the manufactured
σ gradient GONE at the seams — a FAILABLE check (§7-11), never by construction.** The spec
**names that measurement and its trip condition**.

⛔ **Until it passes, pin 87's "Stage 2G cannot close while it stands" STILL HOLDS.** A
mechanism removed by design is not a defect measured absent.

### 12.7 All of this is PLAN work

⛔ **Nothing runs at spec time** (276d). The spec records **the acquisition design, the
sampling rule, the pricing basis, and the throughput measurement** — not their results.

---

## 13. One new surface, authorised by name (D12)

**DECISION D12 (owner, 2026-09-21): ONE new surface, AUTHORISED BY NAME; identity
PRESERVED; rows REPORT-ONLY.**

### 13.1 Pin 106(a) cited TWO blockers, not one

I found the first and missed the second.

| blocker | scope | status |
|---|---|---|
| **pin 82** — "bring me this before any further hardening task is created… what must be TRUE for **Stage 1** to close" | ⭐ **Stage-1 scoped** | **does NOT bind Stage 2** |
| ⛔ **the PROGRAM spec's standing-instruments clause** (fork F), verbatim: *"Standing instruments, default rows (report-only; keyed (tile, era) via `Registry.applicable` + `report_rows` — Phase-11 machinery, **zero new surfaces**)"* | ⛔ **NOT stage-scoped** | ⭐ **this is why 106(b) named a design conflict Stage 2 inherits** |

⭐ **THIS DECISION LIFTS THE SECOND BLOCKER FOR EXACTLY ONE NAMED SURFACE:** a
**source-agnostic obs locator** plus **explicit per-tile window parameters** for the
geometry provider.

⛔ **IT IS NOT A GENERAL LICENCE.** It is recorded in the spec as an **amendment of that
clause, citing this decision** — so a successor reads the clause and the exception together.

### 13.2 Why lifting it is right, recorded

⭐ **Fork E already requires it.** It puts `n_eff` in *"the geometry-provider layer, never
through the solver"* — so **the program spec already demands a geometry provider that
reaches cmems_my tiles.** The surface is **mandated by fork E**; GroundTrack **rides on it**.

**One reader, two consumers, ONE origin** (§7-12). ⛔ **The derivation stays Phase-11's,
unchanged** — `split_passes`, `_fit_heading`, `classify_orbit`, `derive_family` are
box-agnostic already; only the file lookup and the longitude window are scoped:

- `_find_obs` globs `dt_gulfstream_{mission}_phy_l3_*.nc` and demands **exactly one file per
  mission**. cmems_my is `dt_global_{mission}_phy_l3_1hz_{date}_{vintage}.nc`, **427 files
  per mission**.
- `_LON_LO, _LON_HI = 295.0, 305.0` sit at **module level** and are baked into the artifact
  key (`box_lon`).

### 13.3 IDENTITY — the pin-31(a) pattern, reused

`_LON_LO`/`_LON_HI` **leave module level and become explicit inputs**, and ⭐ **the
challenge-box call site passes today's constants.**

⛔ **ACCEPTANCE: given the challenge box (295–305) and the dc2021a locator, the generalised
provider reproduces the existing artifact's KEY AND BYTES exactly.** ⛔ **A mismatch is a
STOP, not a re-baseline.**

⚠ This is the same instrument as pin 31(a)'s hard identity constraint: a generalisation is
accepted only when it reproduces the specialisation byte for byte.

### 13.4 Rows are REPORT-ONLY — and the program spec already refused the alternative

⭐ **Report-only is the program spec's OWN classification for standing instruments**, not a
caution added here.

⛔ **Claim-bearing groundtrack rows are REFUSED.** GroundTrack's **0.410** is a
**challenge-box baseline** (the `0.410→0.331` lineage, fork F), and a claim-bearing threshold
carried to other tiles is **a box-scale result cited as transferring** — §7-7 exactly.

⭐ **And fork F pin 6 had already refused it, in its own words:** *"every standing row is
report-only; promotion to a bar anywhere in this program goes through the pre-registration
mechanism with owner sign-off — the box-scale rule, said once here so no tile/era table
drifts into gating."*

**So promoting ANY standing instrument to claim-bearing is a SEPARATE owner decision, with
pre-registered tolerances.** Nothing here promotes one.

### 13.5 Stage 1's composition stays INCOMPLETE

⛔ **Stage 1's transfer composition stays INCOMPLETE as recorded (106), and the closure
record stays FROZEN.** ⭐ **Stage 2's rows complete the composition for STAGE 2's readings
going forward** — and the spec says exactly that, so no reader takes Stage-2 rows as
retroactively completing Stage 1's.

### 13.6 D11 binds the reader

- **Availability by (mission, day)** — §12.1's unit, not directory presence.
- **A throughput floor with a stall watcher** — A-1's mechanism, not its number (§12.5).
- ⭐ **The locator handles the many-day-file layout WITHOUT the one-file-per-mission
  assumption** — the concrete defect §13.2 names.

---

## 14. The seasonal axis: a report-only diagnostic on covariate residuals (D13)

**DECISION D13 (owner, 2026-09-21): a REPORT-ONLY seasonal diagnostic on COVARIATE
RESIDUALS; `s(x, era)` UNCHANGED; resolution STATED.**

### 14.1 The substrate is THINNER than "n>1 years"

⚠ **The unlock condition is met only in a weak sense.** D3 gives each reference epoch **ONE
balanced year**, so **within an era every season appears once.** The n>1 years exist only
**ACROSS the three reference epochs — which are different ERAS.**

⭐ **So the diagnostic runs on residuals AFTER the covariate model, where era is absorbed by
`n_eff`.** That gives ⭐ **n = 3 per (season, tile)**, ⛔ **CONDITIONAL ON THE COVARIATE
ABSORBING ERA** — D5's structure exactly, **and quoted with that qualifier every time**.

### 14.2 Resolution is set by the WINDOW STRIDE — quarters, not months

Derived from `WindowPlan()`: 9 windows, stride **45 d**, so **365/45 ≈ 8.1 windows per year**.
Season is taken **by window centre**, and the centres (days 12, 57, 102, 147, 192, 237, 282,
327, 352) fall **2 / 2 / 2 / 3** across quarters.

⭐ **THE PARTITION IS QUARTERS, NOT MONTHS, AND IT IS PRE-REGISTERED.**

⛔ **THE AUGUST 0.629 FINDING IS MONTHLY. It can be tested only at SEASONAL resolution, and
the spec says so** — so no reader takes a quarterly result as a test of the monthly claim.
(The lineage, from the archived trail's owner T14 ledger line (c): *"August 0.629 — the
seasonal limitation survives the R change: one more candidate mechanism eliminated; the axis
stays named future work with n>1-years as its substrate."*)

### 14.3 Pre-registered exactly as D5 is

| element | specification |
|---|---|
| **statistic** | per-season **`coverage_1σ`** and **χ² deviation from the all-season value** |
| **tolerance** | **stated before any number arrives** (§7-10) |
| **noise floor** | **two-way block resampling with WINDOW BLOCKS WITHIN SEASON** (§6.3's method, restricted) |
| **outcomes** | **CONSISTENT** / **DIVERGENT** / **UNDERPOWERED** |

⛔ **UNDERPOWERED IS NEVER READ AS "NO SEASONALITY."** With n = 3 per (season, tile) this is
the likely outcome, and it must be reported under its own name (§7-11).

### 14.4 `s(x, era)` stays ERA-STATIC — and a DIVERGENT result does not change it

⛔ `s(x, era)` **stays era-static** (fork-e pin 2(ii), per-location median).

⭐ **A DIVERGENT result is a RECORDED FINDING that tables an owner decision to fit the axis
in STAGE 3**, where the full record gives **many years per era**.

⛔ **IT NEVER CHANGES THE CALIBRATION MODEL INSIDE STAGE 2.** Changing `s` on the diagnostic
that measures it is **the (i6) pattern** — the same refusal as D9 §10.1.

### 14.5 The C2→2G line

⭐ **2G's calibrated σ is ERA-STATIC, and the seasonal row travels with it as a STATED
LIMITATION** — continuing the August 0.629 lineage rather than closing it.

### 14.6 No extra solves

D3's windows already carry the substrate. The diagnostic adds **no solves**.

### 14.7 CORRECTION APPLIED to `docs/project-context.md` (owner's, D13g)

**Line 64 read:** *"extrapolation-fraction audit; **locked-gauge era rows (DEV pool)**."*

⛔ **That contradicts itself** — the locked c1 set is 39 gauges, **disjoint from the 96-gauge
DEV pool by pre-registered sealed split** — **and it contradicts program spec §3.3 and the
same file's own §5.4**, both of which read *"DEV-pool gauge era rows."*

**Replaced with:** *"extrapolation-fraction audit; **DEV-pool gauge era rows (no locked opens
at Gate 2, §3.3)**."* ⛔ **Nothing else in that file changes.**

⭐ **RECORDED, because the consequence was not cosmetic: a successor reading the old line
could have spent the program's FIRST LOCKED OPEN at the wrong gate** — Gate 2, where §3.3
says the locked set is *never opened*, instead of at 2G's acceptance touch.

---

## 15. The era no-op: a plumbing identity that CAN fail (D14)

**DECISION D14 (owner, 2026-09-21): the era no-op is a PLUMBING IDENTITY THAT CAN FAIL;
§10 check 3's "BY CONSTRUCTION" wording is REPLACED for Stage 2.**

### 15.1 The trap is in the SPEC

⛔ **Program spec §10 check 3, verbatim:** *"**Era-machinery no-op:** era-keyed calibration
evaluated at the reference epoch = signed s(x) EXACTLY, **BY CONSTRUCTION** (fork-e pin 1's
gauge: density factor ≡ 1 at n_eff₀) — an identity, not a tolerance."*

⛔ **A CHECK TRUE BY CONSTRUCTION CANNOT FAIL** (§7-11) — and this one sits **inside the
five-gate anchor identity set**, which is the last place it belongs.

⭐ **The gauge-identity reading is REFUSED.** This decision **replaces check 3's CONTENT for
Stage 2**, recorded here. ⛔ **The program spec's text is NOT edited.**

### 15.2 What it asserts

- ⭐ **The FULL era-keyed path runs, with NO branch on `era == reference`.** A path that
  short-circuits at the reference epoch tests nothing.
- Evaluated at **the anchor's reference epoch**, surface values **`==` the signed phase13
  field** (`phase13_field_miost.json`, sha `a4d3b4a0…`, **2652 values**, exact `==`, never a
  tolerance).
- ⭐ **The factor is built NORMALISED BY THE REFERENCE ERA'S OWN FACTOR**, so the reference
  epoch **cancels exactly in IEEE** (`x/x = 1.0` for finite nonzero `x`) **while the whole
  path still executes.**
- **Assert that the covariate path RAN**: `n_eff` computed, descriptor fields populated.

### 15.3 The descriptor is a STRUCTURED DIFF, not `cal_key` byte-equality

⚠ **Byte-equality is the wrong instrument here.** Fork E **serialises the covariate
definition into the calibration descriptor**, while Stage 1's `cal_key` is the **bare
polynomial string**
(`cal:poly;coeffs=(…);clip=(…);fit=L-BFGS-B;gtol=1e-08`) — so ⛔ **`cal_key` byte-equality is
reachable only by a BYPASS**, which is the opposite of what the check wants.

**Assert instead:** every **Stage-1 `cal_key` field unchanged**, **plus EXACTLY the era and
covariate fields on an ALLOWLIST written before the run.** ⛔ **Any other difference fails.**

### 15.4 BOTH outcomes reachable (pin 42)

⭐ **A declared MIS-WIRING must FAIL** — the other era's geometry on one side of the
normalisation, or a wrong era key. ⭐ **The negative control's FAIL is recorded BESIDE the
PASS.**

⛔ **NAMED TRIP CONDITION:** a **zero or infinite density reaching the normalisation**
(`n_eff = 0` not caught by hull/clip) yields a **non-1.0 factor and trips**. ⭐ **That is a
real defect the check exists to catch** — not a hypothetical.

### 15.5 Scope, stated BESIDE the PASS

⭐ **This proves the era machinery is TRANSPARENT at the anchor. It CANNOT validate the
covariate.** That is **LORO's** job and the **sparse-epoch transfer reading's** job.

⚠ Stated beside the PASS, not in a footnote — a transparent-plumbing result quoted as
covariate validation would be the pack's §1.11 error repeated (evidence read as covering
more than it does).

### 15.6 Discharge accounting

**On PASS:** ⭐ **anchor check 3's era no-op is RUN AND PASSED at Stage 2, with its commit
named.**

⛔ **Stage 1's proxy-pass stays as recorded**: the closure record is **frozen at 97b's
accounting**, and **the `anchor_gate` node is NOT edited**. ⭐ **A pin-64 FORWARD POINTER
names the Stage-2 discharge.**

**From then on the accounting reads:** ⭐ **THREE run and passed (1, 3, 5), TWO cited
(2, 4) — each with its date.** (Still never "five green": 260(a)'s form is preserved, with
one item moved from proxy to run.)

⚠ The narrower option — running the test but declining to discharge check 3 — **would
UNDER-record once the real check has run**, which is the mirror of over-recording and just as
wrong.

### 15.7 It runs on the code that SHIPS

⭐ **After T14's acceptance, or re-run after it.** Pin 31(a) keeps the anchor identical **by
construction** — ⛔ **and "by construction" is precisely what this decision refuses to lean
on.**

---

## 16. Four placements, with reasons (P1–P4)

⛔ **THESE ARE EXECUTOR PLACEMENTS, NOT OWNER DECISIONS.** 274(c) directs that *"THE SPEC
PLACES, WITH REASONS"*, so they are authored here and tagged **P1–P4** rather than given pin
numbers — **a pin number asserts owner authorship** (pin 40). Each is **subject to owner
correction**, and none is cited as ruled.

### P1 — ATTRIBUTION versus the bridge caveat → the CAVEAT travels; the READOUT does not

**PLACED:** Stage 2 does **NOT** land the source-delta attribution readout. It is an **owner**
readout — the golden-tile node records the AVISO DT2021 decomposition as an
**owner-electable ledger row, `tabled_for_owner: true`** — and nothing in Stage 2's scope
produces it.

**What Stage 2 does instead:** ⭐ **the bridge caveat travels as a REQUIRED SCHEMA FIELD**, the
mechanism that already exists — `BRIDGE_CAVEAT` in `phase14_stage1_run.py:233-238`, verbatim
on every cmems_my row: *"cross-lineage reading; golden-tile bridge delta MEASURED ON THE
ANCHOR BOX (mu −0.012457 their_eval-scale, map RMS 4.10 cm); its magnitude at THIS tile is
unmeasured; interpretation WAITS on the owner attribution readout."*

**Reason:** pin 94's precedent is explicit — *"a row that must be paired with a document to be
read correctly will eventually be read alone"* — so a Stage-2 cross-lineage row **cannot be
BUILT without the field**. ⚠ **Stage 2's own named exposure:** `s_spatial`'s baseline lineage
is the phase-13 anchor-derived surface while the covariate is identified on **cmems_my**
tiles, so **any reading that carries the anchor's surface onto a cmems_my tile is
cross-lineage** and carries the field.

### P2 — THE POWER WINDOW (132) → a budget line, not new work

**PLACED:** recorded in the plan's per-leg envelope as a **budget line**; **no new work**.

**Reason:** pin 132 names it *"carried forward, unresolved and **not resolvable by executor
work**… a power event still costs the window in flight (~3.44 h), which is the residual R5
could not remove."* ⭐ **And the figure is exactly ONE WINDOW-SOLVE, measured**: the
`tier2_probe_kuroshio_m100` row records **3.440 h for one window at m=100**. So the exposure
is *one window re-solve per power event*, priced in the unit that varies (§7-18).

**Standing practice already covers the mitigation** — *"persist expensive intermediate state
BEFORE any compare phase; a compare-phase death must not cost the solves"* — so Stage 2 adds
**no mechanism**, only the line in the envelope.

### P3 — S5 (the open witness interval) → binds ONLY where Stage 2 re-cites the artifact

**PLACED:** the open interval rides **`stage1:T19`**'s citation, and is otherwise **recorded,
not acted**.

**Reason, derived from the node:** exactly **one** of three intervals is open —
**`phase13_lane0_mean.nc`**, *"ABSENT — no contemporaneous sha of this artifact exists in the
record"*, so *"the 2026-07-28 capture closes **future substitution only**."* Its own recorded
materiality: *"lower than the other two: this artifact is cited by the **gate-5 `scope_note`**
and the **Stage-0 golden-tile `mu_scale_check`**, not by a bit-identical check-1 route."*

⭐ **Stage 2 touches gate-5 through `stage1:T19`** (the DT scoring-track re-score that
constrains gate-5's write-once constants), **so that is the one place the caveat must
travel.** The other two intervals are **CLOSED by exact match** and need nothing.

### P4 — S6 (gauge proximity) → it BINDS Stage 2, and is resolvable WITHOUT a seal change

⭐ **PLACED AS BINDING, not as recorded-only** — this is the one of the four that reaches into
Stage 2's own gate.

**Reason:** the **sealed** screening block carries
`"proximity": "DEFERRED to consumption grid (Stage-0 recorded interpretation; Gate-0 owner
attention item)"`, with `l_prox_km = 150.0` concrete and **`proximity` the FOURTH of five
entries in `criteria_order`**. ⭐ **Gate 2's independence evidence includes DEV-pool gauge era
rows (§3.3), so STAGE 2 IS A CONSUMPTION GRID** — the deferral's own named trigger.

⛔ **It must be resolved BEFORE those rows are read**, or the rows carry an **unresolved
screening criterion** while serving as Gate-2 independence evidence.

⭐ **AND IT IS RESOLVABLE WITHOUT TOUCHING THE SEAL** — which matters, because a seal change
would claim the one authorised v2 already allocated to T17 (§9.5). The sealed text **itself
contemplates this**: the interpretation is deferred *to the consumption grid*, so the
resolution is a **consumption-side decision recorded outside the seal**, leaving
`screening.proximity` and `l_prox_km = 150.0` byte-unchanged.

⚠ **What resolving it means is NOT settled here:** how proximity is applied when selecting
which DEV-pool gauges serve which tile and era. That is a Stage-2 design item, and being a
**Gate-0 owner attention item**, the resolution goes to the owner rather than being chosen by
the executor.

---

## 17. Transferred-vs-refit per era: eligibility is not a schedule (D15)

**DECISION D15 (owner, 2026-09-21): the SEALED ROLE IS ELIGIBILITY, NOT A SCHEDULE; the
SEVEN are NOT PRODUCED in Stage 2; STAGE 3 decides REFIT vs TRANSFER.**

### 17.1 The owner's correction, tagged as the owner's

⭐ **§5.1's "Every `fit` epoch gets its own per-era fit" is the OWNER's sentence, and it
OVERSTATED.** The sealed role records **ELIGIBILITY** — at least four missions net of locked,
`fit+validate` — and ⛔ **no ruling schedules a fit for all ten.** §5.1 now carries the
rewritten form.

⚠ Recorded as the owner's own correction rather than absorbed silently, for the same reason
§5.2 and §12.1 are: the tree should show where a sentence came from and who fixed it.

### 17.2 The per-era row: THREE FIELDS, not a category picked by eye

| field | values | note |
|---|---|---|
| **`sealed_role`** | **verbatim from seal v1** | ⛔ **never restated** — quoted, not paraphrased |
| **`stage2_status`** | **FITTED** (the three reference epochs) \| **TRANSFER-READ** (where the Gate-2 sparse-epoch reading consumes it — **once, masked**) \| **NOT PRODUCED** | what Stage 2 actually did |
| **`calibration_when_produced`** | **REFIT** \| **TRANSFER** \| **UNDECIDED**, **with the stage that decides** | the forward-looking field |

⭐ **THE SEVEN ARE: `stage2_status` = NOT PRODUCED, `calibration_when_produced` = UNDECIDED
(Stage 3).**

⛔ **Recording them as "transferred" would record a transfer THAT NEVER HAPPENS IN STAGE 2.**
Both my two-category option and my own preview's "s from the covariate in practice" made
exactly that error: Stage 2 produces **no** `s` for those eras at all — neither fitted nor
transferred.

### 17.3 Stage 3 decides, and is NOT committed to fit

⭐ **REFIT is the default the sealed role allows.** ⛔ **TRANSFER instead must CITE STAGE 2's
LORO EVIDENCE** — held-out-reference prediction error is **exactly the test of whether the
covariate can stand in for a per-era fit** — and it **triggers §5.1's `gfo` obligation where
it applies.**

⚠ So D5's LORO is doing double duty, and the spec says so: it is the era-level **falsifier**
for `se(b_i)` (§6.4) **and** the evidence any future TRANSFER decision must cite. A weak LORO
result therefore costs twice.

### 17.4 The Phase-12 pattern, era-indexed — on every row that TRANSFERS

Three elements on each transferring row, following Phase 12's own form (*"the six-mission
product SHIPS; the five-mission config CALIBRATES"*):

1. **the expected DIRECTION, with its reason**;
2. **a PRE-REGISTERED BAR**;
3. **an OWNER-RULED REFERENT**.

⛔ **AND ONE ASYMMETRY IS STATED NOW.** Phase 12 transferred toward **MORE** missions and
expected **over-coverage — the conservative direction** (its bar: coverage ∈ 0.6827 ± 0.10,
referent 0.7350). ⭐ **Stage 2's sparse-era transfer runs toward FEWER missions, and where the
hull clip binds, the bias direction is set by THE SIGN OF `b`: UNDER-coverage if `b < 0`.**

⛔ **IT CANNOT BE ASSUMED CONSERVATIVE.** ⭐ **The row states the direction ONCE `b` IS
FITTED, and BEFORE the sparse reading is consumed** — the reading is consumed **once**
(fork-c pin 1), so a direction stated after it would be stated too late to be a prediction.

---

## 18. The revisit (225) and the OSSE exit (251(3)) (D16)

**DECISION D16 (owner, 2026-09-21).** Two halves: the **revisit is NOT ELECTED at Stage 2,
by explicit decision, and TRAVELS to 2G**; the **OSSE design question is PRESERVED FOR THE
SAMPLING CLAIM, and for its FORM only, with three limits.**

### 18.1 The Phase-10 reopening condition — quoted, and my mis-citation corrected

⛔ **I CITED THE WRONG ROW.** *"Revisit only at the global domain"* is the **MIOST-B
REPRESENTATION** thread — **Phase-10 post-close ruling 4** — and *"the OI product question
re-opens at the global domain"* is **ruling 1** (the declined tuned-constant election).
**Neither is the Phase-10 revisit thread's reopening condition**, and §9's row for that
thread reads only *"per its recorded reopening condition."*

⭐ **THE CONDITION, VERBATIM — Phase-10 post-close ruling 3(a), 2026-07-15:**

> *"the negative result is SCOPED — **'no lat-varying gain beyond the measured band UNDER
> THIS SEARCH (recorded `n_sobol_per_lane`: 7 full-year equivalent / 30 screening per lane,
> 12 h wall, screening contingency active)'** — a search-scoped negative, never a physics
> disproof."*

⭐ **AND THAT SETTLES SOMETHING 225(b) ONLY IMPLIED.** The condition is about **SEARCH
BREADTH**. ⛔ **Anchors-only is NARROWER than the search that produced the negative** — 3
solves/tile against 7 full-year-equivalent sobol samples per lane — so **it can never
discharge the reopening condition at any stage.** Only a **wider** search can. The revisit
therefore travels as a **configuration comparison**, never as a reopening instrument.

### 18.2 NOT ELECTED at Stage 2 — an explicit decision, with reasons

⚠ **225 names anchors-only "Stage 2's entry point", so DECLINING IS AN EXPLICIT OWNER
DECISION**, recorded with its reasons — not a silent lapse.

**225(c)'s reasons, re-checked for Stage 2, each still holding:**

1. **12 days for a report-only result whose strong form is unreachable**, on a
   memory-constrained box;
2. **the box-scale negative is never cited as transferring** (§7-7 / discipline 7);
3. **no Gate-2 item is bought** — Gate 2's four items are the covariate rotations verdict,
   the sparse-epoch transfer reading, the extrapolation-fraction audit and the DEV-pool
   gauge era rows; the revisit is **not among them**.

**Two more, specific to Stage 2:**

4. ⭐ **It has NO TEMPORAL CONTENT** — a 2017-only configuration comparison, in the stage
   whose whole subject is era;
5. ⭐ **it competes with Stage 2's box-bound critical path** (the era-fits and the
   acquisition of §12).

### 18.3 It TRAVELS to 2G — and the price is labelled

⭐ **At 2G, fleet compute makes 12 solves cheap in WALL time, and the answer — which
configuration to ship per regime — BUYS something.**

⛔ **296.2 h / 12.3 d is a TIER-1 BOX PRICE.** It **travels as that, LABELLED**, and is
**RE-PRICED at 2G's rung**. ⛔ **It is NEVER quoted as a 2G cost** (§7-18: a figure measured
on one axis must not be applied on another).

### 18.4 225(b)'s limit travels verbatim

⛔ **Wherever the option appears:** anchors-only can say *"the lane's designated
configuration does not beat lane-0 in this regime."* It **CANNOT** say *"no configuration in
the lane does."* **A negative result needs the second, and the sobol search is what buys
it.**

### 18.5 OSSE 251(3) — PRESERVED for the sampling claim, and for its FORM only

⭐ **Flying each era's geometry over one fixed nature-run period ISOLATES SAMPLING, which is
exactly what `s = f(n_eff)` claims.** So the design **does** preserve "constellation varied
over fixed truth" — **for that claim.**

⛔ **BUT IT TESTS THE COVARIATE'S *FORM*, NOT ITS LEVEL.** It tests **`b`** — the slope,
relative across eras. ⛔ **`a` is set by the TRUTH's own variance spectrum, which a nature
run does not share with the real ocean.** ⭐ **Compare `b` between the OSSE and real data.
NEVER `a`.**

### 18.6 Three stated limits

| # | limit |
|---|---|
| 1 | ⛔ **ERROR MODELS ARE INPUTS.** The OSSE tests the covariate **GIVEN** the assumed δ_m and structured R — **not those models** |
| 2 | ⛔ **OCEAN STATE IS HELD FIXED.** Any era-dependence of `s` arising from the ocean itself (eddy energy, regime shifts) is **invisible by construction**. ⭐ *"Nothing but density varies with era"* is tested **only** by real-data **LORO** and the **sparse-epoch reading** |
| 3 | ⛔ **ABSOLUTE `s` IS TRUTH-DEPENDENT** — §18.5 |

### 18.7 The truth period, and what stays open

⭐ **The ~14-month truth holds ONE D3-balanced year, so the OSSE INHERITS D3's balance.**
Era geometry comes from **D12's reader**, with times **re-mapped to the truth period by a
PRE-REGISTERED rule**.

⛔ **Replication (251(4)) stays OPEN and UNPRICED. No pricing here.**

---

## 19. Gate 2: every item has a bar; what a failure DOES separates them (D17)

**DECISION D17 (owner, 2026-09-21): EVERY ITEM HAS A BAR; WHAT A FAILURE DOES separates
them; 212(b) BINDS THE PACK.**

### 19.1 "TABLE vs TRIP" is a FALSE DICHOTOMY

⛔ **My framing was wrong.** ⭐ **Every Gate-2 item carries a PRE-REGISTERED BAR, stated
before its numbers** (§7-10, §7-11). ⛔ **A reading with no bar that merely "tables" CANNOT
FAIL, and as a gate item it is UNRUN** — discipline 11's family, arriving in the gate design
itself.

⭐ **What separates the items is WHAT A FAILURE DOES:**

- **IDENTITIES AND REFUSALS STOP.** A trip **halts downstream work**. These are
  **PRECONDITIONS: the pack cannot be posted while any is tripped or unrun.**
- **READINGS TABLE** — each with its bar, and a failure **routes to an OWNER DECISION**,
  never an automatic action, ⛔ **never a silent pool or clip.**

### 19.2 The preconditions, DERIVED from D1–D16 (not taken)

**Derived by sweeping every decision for stop-shaped conditions. The count is 13, and it is
DERIVED, never restated beside the list** (146b). ⭐ **Grouped by WHAT THE FAILURE BLOCKS** —
a flat list would imply they all block the same thing, and they do not.

**A. Preconditions on POSTING the Gate-2 pack (8):**

| # | precondition | source |
|---|---|---|
| 1 | era no-op **PASSES** and its declared mis-wiring **FAILS** | §15 (D14) |
| 2 | `stage1:T19`'s reproduction — a mismatch is a STOP, reported the moment it happens | §8.4 (D7) |
| 3 | geometry provider reproduces the existing artifact's **KEY AND BYTES** exactly | §13.3 (D12) |
| 4 | the **Sentinel-6** class-map fix reproduces the sealed table **byte for byte** | §5.5 (D4) |
| 5 | the **CRN post-freeze σ-gradient discharge measurement** passes | §12.6 (D11) |
| 6 | the **267 closure tripwire is GREEN** — a trip in Stage 2 is a VIOLATION | §1.2 (275b) |
| 7 | `stage1:T14`'s member **sha-equality** vs `phase13_winner_members.npz` — *if the freeze ran* | §7.2 (pin 31a) |
| 8 | the **mixed-pavement comparison refusal** is active (refused by construction, not reported) | §7.7 (D6) |

**B. Preconditions on SEALING v2 (2) — these gate the SEAL, not the pack:**

| # | precondition | source |
|---|---|---|
| 9 | the **real-data null** falls inside the simulated null's stated band — else **NOTHING SEALS** | §10.3 (D9) |
| 10 | **CLEAN reachability** holds at the production geometry and the ruled m — else **do not seal** | §10.4 (D9) |

**C. Precondition on SPEND (1):**

| # | precondition | source |
|---|---|---|
| 11 | `authorize()` **REFUSES** Tier-2 production while `stage0:T18`'s witnessed node is absent | §11.5 (D10) |

**D. Selection admissibility — refusals, not halts (2):**

| # | precondition | source |
|---|---|---|
| 12 | an epoch that cannot hold a **whole year of pure windows** cannot be a reference epoch | §4.2 (D3) |
| 13 | at least one +2 epoch **assimilates j3 by mission ID** | §5.3 (D8f) |

### 19.3 The classification, CORRECTED

⛔ **My "three of four table" was wrong, item by item:**

| item | corrected classification |
|---|---|
| **LORO** | ⭐ **CLAIM-BEARING AS A SET** (fork-e pin 4) — **a pre-registered bar ON THE SET.** The claim **can fail** |
| **DEV-pool gauge era rows** | ⭐ **THE CLAIM-BEARING INDEPENDENT FAMILY IN ALL EPOCHS** (fork C), carrying the **independence burden in sparse eras**. ⛔ **They are NOT "record"** — my own Gate-2 preview said "record", and that was the error |
| **sparse-epoch reading** | consumed **ONCE**, against **D15(e)'s Phase-12-pattern bar** (direction, bar, referent) |
| **extrapolation audit** | it tables *"a large fraction"* — ⛔ **and "large" is a NUMBER, STATED NOW** |

### 19.4 212(b) binds the PACK; the identities do not need it

⭐ **212(b) BINDS THE PACK — the readings and their interpretation.** Reviewer A takes the
requester's surfaces; ⭐ **reviewer B is briefed INDEPENDENTLY on the FRAME** (§7-17).

⭐ **The IDENTITIES do not need it:** they are **verification against artifacts**, which is
exactly the case §7-15 names as admitting owner ratification — ⛔ **and each passed identity
is shown WITH ITS NEGATIVE CONTROL** (D14(d)), so the ratification rests on a check that
could have failed.

### 19.5 Organise the pack around the DECISIONS, not the four items

Stage 2 **ships no product and opens nothing** (§3.3), so ⭐ **Gate 2's decisions concern
what C2→2G CARRIES:**

1. **is the covariate FIT TO FEED 2G?**
2. **what does a DIVERGENT, UNDERPOWERED or large-fraction finding CHANGE IN 2G's DESIGN?**

⛔ **The pack is organised around those two decisions, NOT around the four items.** The items
are evidence *for* the decisions; a pack shaped like its evidence list makes the reader
assemble the decision themselves.

### 19.6 The NAME COLLISIONS — now FOUR

⛔ **This program reuses names, and each collision has already misled a record or a reader:**

| name | meanings |
|---|---|
| **"Tier 2"** | the ladder's `Tier.CLOUD_NODE` **vs** the local memory-class crossing of E-16 / `stage1:T22` (§11.3) |
| **"T18"** | `stage0:T18` (the Tier-2 cloud probe, which owns `pending-T18`) **vs** `stage1:T18` (the userGate before T14) — **this one misled two records** (§11.2) |
| **"gate 2"** | ⭐ **the STAGE gate** (Gate 2) **vs** **§10's anchor identity check 2** (loader identity), which §14's "Gate-2 decomposition" is about |
| **"S6"** | ⭐ **sweep item S6** (the gauge consumption grid, §16 P4) **vs** **Sentinel-6** (`s6a_lr`, §5.5's classless mission) — surfaced by D17's own wording |

⭐ **CONVENTION, extending §11.2's rule from tasks to gates and sweep items:** **"Gate 2"**
means the stage gate; **"anchor-check-2"** means §10's second identity; task references are
tracker-qualified; **"S6"** is written **"sweep item S6"** or **"Sentinel-6"**, never bare.

---

## 20. The coverage map (276b)

⭐ **Every closure-record item (263.1–12, S1–S6, A-1) and pins 255–258, each marked SETTLED
(§ ref), CARRIED TO C2→2G (named), or PLACED (with reason).** ⛔ **The count is DERIVED from
this table by script, never recalled** (146b) — see §20.3.

### 20.1 The map

| item | disposition | where, and why |
|---|---|---|
| **263.1 KERNEL** | ⚖ **RULED in Stage 2 (pin 288): a WAIT with its exit named; and a C2→2G LINE (288d)** | ~~274(b): poles and the kernel exits are 2G's~~ **corrected by 278(a) — the exits are Stage 2's — and RULED at 288.** Stage 2 runs on the **shipped kernel** (§7.3a); `operative_halo_deg()` untouched (288e). **C2→2G line:** *the covariate (a, b) is identified on the shipped kernel. If 2G changes the kernel, it RE-IDENTIFIES (a, b) on the new one — priced: the twelve-fit set again — or carries the caveat that b was identified under 288(a)'s anisotropy.* Exit: 2G decides kernel and poles together, starting from the per-axis halo reading (288c). ⚠ R5 (pin 283) rebuilds this map with the four-state boundary and the full C2→2G line table; this row is amended now so the ruling is not held only in the item |
| **263.2 REVISIT** | **SETTLED** | §18.1–18.4 — NOT elected at Stage 2 by explicit decision; travels to 2G labelled as a **Tier-1 box price**, with 225(b)'s limit verbatim |
| **263.3 OSSE** | **SETTLED** (in part) | §18.5–18.7 — 251(3) answered: preserved for the **sampling** claim, **form only** (`b`, never `a`), three limits stated. ⚠ **Replication (251(4)) stays OPEN and UNPRICED** |
| **263.4 REFRESH** | **CARRIED TO C2→2G** | bundled with 2G's chain and touch (255c); its two named Stage-2 obligations are SETTLED — see **256** and **257** |
| **263.5 σ SEAMS** | **SETTLED** | §10 — freeze → simulated null → real-data falsifier → reachability → v2 → score. The diagnosis's five confirmed lines stand; the verdict becomes attributable once the pavement pairs |
| **263.6 CRN** | **SETTLED** | §12.6 — the freeze removes the MECHANISM; the defect is discharged only by a **failable post-freeze measurement** (§7-11), which is precondition **§19.2-A5** |
| **263.7 GROUNDTRACK** | **SETTLED** | §13 — ONE named surface authorised; rows **REPORT-ONLY** (fork F pin 6); identity by the pin-31(a) pattern |
| **263.8 ATTRIBUTION** | **PLACED** | §16 **P1** — the caveat travels as a **required schema field** (pin 94's precedent); the **readout stays the owner's** |
| **263.9 POWER** | **PLACED** | §16 **P2** — a budget line, not new work; the ~3.44 h is **one window-solve, measured** |
| **263.10 LEDGERS** | **CARRIED TO C2→2G** | 275(b): **THREE** ledgers, and it is **2G's question**; the tripwire stays green through Stage 2 (§1.2, §9.5) |
| **263.11 TEST ISOLATION** | **PLACED** | §1.2 — 275(a): **early housekeeping**; false FAILURES, not false passes, so it **gates nothing** |
| **263.12 TASKS 14–21** | **SETTLED** | §7 (split by step), §8.2 (the latent cycle dissolved), §11; ⛔ **the PLAN opens them, not this spec** (276d) |
| **S1 era no-op** | **SETTLED** | §15 — a **plumbing identity that CAN fail**; §10 check 3's "BY CONSTRUCTION" replaced for Stage 2 |
| **S2 Gate-0 cloud leg** | **SETTLED** | §11 — it waits on **`stage0:T18`**; the precondition **moves into the ladder** (`authorize()` refuses) |
| **S3 seam-rubric amendment (substance)** | **SETTLED** | §7.4 + §10 — **T17 follows the FREEZE**, not a stage label; ONE sealed version, CRN-state-conditional |
| **S4 ensemble-settling sealing dependency** | **SETTLED** | §7.4 + §8.5 — ordered behind the freeze; **m** travels in the owner's packet (pin 53's m ≥ 137, priced not chosen) |
| **S5 witness interval** | **PLACED** | §16 **P3** — one of three intervals open (`phase13_lane0_mean.nc`); rides **`stage1:T19`**'s citation |
| **sweep item S6 (gauge consumption grid)** | **PLACED — BINDING** | §16 **P4** — Stage 2 **IS** a consumption grid; resolvable **without a seal change**; the resolution is the owner's |
| **A-1 trickling download** | **PLACED** | §12.5 — the **mechanism** transfers (throughput floor + stall watcher); ⛔ **the 16 KB/s number does NOT** (MEOM, not CMEMS). A-1 stays test-infra |
| **pin 255 refresh ELECTED, BUNDLED** | **CARRIED TO C2→2G** | 274(b) — bundled with 2G's chain and touch; **no touch spent**, and none spent here |
| **pin 256 δ_j3 PROVISIONAL** | **SETTLED** | §9.6 + §5.3 — fitted at **e09 / e11 / e12** under **one stated assumption** (δ is era-invariant, an instrument property) with a **named falsifier** |
| **pin 257 e10 replacement holdout** | **SETTLED** | §9.1–9.4 — fork C's chain gives **`alg`**; it is an **ADDITION**, not a supersession; **Stage 2 chooses AND seals** |
| **pin 258 the firewall** | **CARRIED — and landed HERE** | §20.2 — it was **not yet in this draft**; the coverage map is what found that |

### 20.2 Pin 258's firewall, in its own words — the gap this map found

⚠ **Building the map surfaced one item the draft had not carried.** Pin 258 requires the
firewall to travel **in its own words** wherever the election appears, and this draft
references the election in §1 and §9 without it. Landed now:

> **258. THE ELECTION MAKES NO CLAIM ABOUT THE TRANSFER RESULT.** A sixth mission raises
> observation density, and nothing recorded says whether that helps, hurts or leaves
> unchanged the two tiles whose lambda_x is absent. That mechanism is firewalled and open.
> The election is about reuniting the shipped product with its calibration. It must not be
> cited as a remedy for the weak-signal finding, and no record may imply it is.

⛔ **CONSEQUENCE FOR THIS SPEC, stated because §5.3's rule could otherwise imply it:** the
+2 selection maximises **log `n_eff` spread**, which raises density at some tiles. ⛔ **No
Stage-2 record may present that as remedying the weak-signal finding at `equatorial` or
`quiet_gyre`** — the two tiles whose λx is **RECORDED ABSENT** (§6.3). The mechanism stays
**firewalled and open**.

### 20.3 The count, DERIVED

Counted from §20.1's rows by script, not recalled:

```
SETTLED                12   263.2 263.3 263.5 263.6 263.7 263.12
                            S1 S2 S3 S4 256 257
CARRIED TO C2→2G        5   263.1 263.4 263.10 255 258
PLACED                  6   263.8 263.9 263.11 S5 sweep-S6 A-1
                       ---
TOTAL                  23   = 12 (263.1-12) + 6 (S1-S6) + 1 (A-1) + 4 (255-258)
```

⭐ **The enumeration reconciles exactly: 12 + 6 + 1 + 4 = 23, and 12 + 5 + 6 = 23.**

⚠ **PLAN-TIME OBLIGATION:** a test pins these counts **against the table's own rows**, the
way `tests/test_project_context_instances.py` pins discipline 11's instance tags — so ⛔ **a
count can never drift from its own enumeration** (146b's defect, which had already happened
once: "six" stated beside seven items).
