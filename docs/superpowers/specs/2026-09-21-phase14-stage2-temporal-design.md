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
| §4+ | remaining scope, placements, gate design, coverage map | NOT YET REACHED |

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
that selection is §4's business and is constrained by the sealed epoch table
(`sealed/phase14_evaluation_seal_v1.json` → `content.epoch_table`, 15 epochs, mirrored).

Consequences that follow from D1 and are therefore settled here:

- **Gate-2's leave-one-reference-out rotation set is 3 rotations × 4 tiles** (fork-e pin 4:
  ALL rotations run and reported — the covariate's claim-bearing test is the set, never a
  chosen rotation).
- The four regimes — western-boundary jet, equatorial, subtropical-quiet, Southern Ocean —
  all enter identification, so the regime spread in §3 is **measured, not assumed**.
- The southern tile enters with its known poleward geometry: core `lat_min = −62.0`, and an
  obs edge at `solve_bbox.lat_min − halo ≈ −66.13`. Its **0.13° overshoot past ±66** is
  where fork-c pin 3's latitude-band validity mask bites, and it is the same edge the
  kernel WAIT (263.1) lives on. Carried into §4's mask treatment; not re-opened here.

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
mission dropouts). Each tile therefore contributes one contrast per matched location across
its three eras, not three points. This is what gives the regime test below its power, and
it is why a per-tile 2-dof fit is not the near-saturated fit a per-epoch reading would be.

**The regime test, pre-registered.** After the pooled fit, each tile's own (a_i, b_i) is
fitted separately and compared to the pooled law. A spread beyond a **stated tolerance** is
a **RECORDED FINDING that tables an owner decision — never a silent pool.** This is fork
E's own instrument for the extrapolation fraction ("a large extrapolation fraction is a
recorded finding TABLING an owner decision, never a silent clip") applied to the pooling
assumption, and it satisfies discipline **§7-11**: the condition under which the test could
fail is named at design time, beside the threshold, before the measurement.

⛔ **The tolerance is stated before the numbers arrive and is never loosened to manufacture
a pass** (§7-10). Its value is set in §4 and is not left to the executor.

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
