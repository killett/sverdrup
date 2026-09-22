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

| section | content | state |
|---|---|---|
| §1 | The frame: what Stage 2 is, and what it is not | VALIDATED |
| §2 | Identification scope — the fit set | VALIDATED (D1) |
| §3 | The density law: pooled, with a pre-registered regime test | VALIDATED (D2) |
| §4 | The anchor reference epoch: e10, pure and seasonally balanced | VALIDATED (D3) |
| §5 | The +2 reference epochs: a pre-registered rule on measured n_eff | VALIDATED (D4) |
| §6 | Tolerance and power: the regime-test threshold and its effective sample size | NOT YET REACHED |
| §7+ | placements (tasks 14-17, CRN, Tier 2, GroundTrack, attribution, power, S5, S6), gate design, coverage map | NOT YET REACHED |

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
  widens the halo — **and the kernel exits are 2G's** (274b), not settled here. Fork-c
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
in e02–e04, and all three of those are **`fit`** epochs, which get their **own per-era fit**
and never lean on the covariate. So the class e10 lacks is a class the covariate is never
asked to reach.

**The reconciliation, stated in the spec so no consumer mis-reads the roles:**

> **Reference epochs identify (a, b). Every `fit` epoch gets its own per-era fit. Only
> `transferred` epochs rely on the covariate.**

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
