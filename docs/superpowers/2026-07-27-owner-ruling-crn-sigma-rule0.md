# Owner ruling — CRN origin defect, σ instrument at m=100, Rule-0 text (2026-07-27)

**Status: RECEIVED AND RECORDED VERBATIM. Not yet implemented.** Steps 1–5 of the
ruling's sequence are for a FRESH session (the owner cleared the session in which
the ruling was given; only docs + tracker work was done here).

This document exists **verbatim rather than as folded acceptance criteria** by the
owner's explicit instruction, and the reason matters: pin 31(a)'s identity
constraint — *global origin congruent to the anchor's own `(x0_km, y0_km)` modulo
the rung spacing, so check-1 sha-equality survives BY CONSTRUCTION* — is the
reasoning behind the highest-risk change in the stage. A fresh session
implementing that from a one-line AC, without the reason, is how the identity
chain and the write-once gate-5 pins get broken by someone being locally sensible.

Tracker tasks created from this ruling: **T13** (rubric amendment), **T14** (global
lattice origin; check-1 re-run is its acceptance), **T15** (alignment-residual
survey + recordings), **T16** (pins 33/35 + process minors). **T5 is now
mechanically blocked** on T14 in addition to its standing Tier-2 WAIT.

---

## PART 1 — THE RULING (verbatim)

> THREE ITEMS RULED. Diagnosis ACCEPTED. Adversarial review ENDORSED and its verdict
> adopted. Pins 31-35.
>
> VERIFIED THIS WALK:
> - 8cf8039 origin HEAD; fd7e518, 420c40f, 8cf8039 all present; board as reported.
> - Diagnosis arithmetic re-derived independently: obs/pred 0.983 / 1.004; half/cross
>   1.44 / 1.47 vs sqrt(99/49) = 1.4214; 333.96 mod 85.254 = 78.198 km;
>   floor/D_int_sigma = 1.1356; quadrature room at nominal floor NEGATIVE; bounded
>   artifact at 5% floor error R = 0.237. All hold.
> - Mechanism confirmed in source: per-tile `basis_domain` (x0_km, y0_km) from each
>   tile's own solve corner; CRN keys on lattice indices from that origin.
> - CORRECTION TO MY PRIOR REASONING: the three floor probes ran at rtol 1e-9 and
>   CONVERGED (635/629/678 iters, 29-31% of cap). F was nonzero. The four T4 verdicts are
>   NOT vacuously attributable and require NO recomputation. The text was defective; the
>   implementation was not.
>
> ITEM 1 — CRN ORIGIN DEFECT. Diagnosis accepted; fix the lattice, not the ensemble.
> 31. PIN THE PAVEMENT LATTICE TO A GLOBAL ORIGIN. Element identity must be a function of
>     absolute position, not of which tile is solving. Then coincident physical elements
>     draw identically by construction, adjacent-tile comparisons are PAIRED, and the
>     common ensemble noise cancels — which is the entire purpose of common random
>     numbers. Do NOT raise m (≈512 members for a 2× floor margin; unaffordable against a
>     T5 already WAITing at Tier-2), do NOT change the σ denominator, do NOT retire the
>     instrument. The reviewer's reading is right and I endorse it.
>     (a) HARD IDENTITY CONSTRAINT — this is the part that can go badly wrong. The global
>         origin MUST reproduce the anchor's existing lattice exactly. If element centres
>         move, member draws change, check-1 sha-equality against
>         `phase13_winner_members.npz` breaks, and the write-once gate-5 pins go with it.
>         Choose the global origin congruent to the anchor's own (x0_km, y0_km) modulo the
>         rung spacing; identity is then preserved BY CONSTRUCTION rather than by luck.
>         Test-pin that construction, and re-run check 1 as the acceptance for the change.
>         The same care you applied leaving `PCG_MAXITER` at 500 applies here, more so.
>     (b) SCOPE IS NON-UNIFORM, and that is the sharper problem. `basis_domain` is in km;
>         tiles are placed in degrees; the km offset for a fixed degree spacing varies with
>         latitude. So whether adjacent lattices coincide varies ACROSS THE GRID. Measure
>         the alignment residual (offset mod finest rung) for every adjacent pair in the D1
>         production tiling across the latitude range and record the distribution. A
>         uniform bias is characterisable; a latitude-varying correlation structure writes
>         artificial structure into σ that will be read as physics.
>     (c) RECORD THE PRODUCT-LEVEL CONSEQUENCE in the Gate-1 pack: under per-tile origins
>         the blend mixes one CRN-correlated and one CRN-independent tile, so ensemble
>         noise is suppressed on one side of the overlap and full on the other — a
>         manufactured gradient in the uncertainty field. That sentence is the reason this
>         is a defect and not a curiosity.
>     (d) Stage-1 σ rows become measurements of a SUPERSEDED configuration once (a) lands.
>         Mark them so; do not carry them into the C1→2 contract as σ readings.
>
> ITEM 2 — σ INSTRUMENT AT m=100. Carry the ensemble floor; the rubric is missing a rule.
> 32. AMEND RULE 0 WITH A SECOND, ENSEMBLE FLOOR for σ-route verdicts:
>     F_ens = σ/√(m−1) for that pair; a σ verdict is attributable only if
>     RMS(sigma_delta) > 3×F_ens, else the row reads UNMEASURED (ensemble floor) and is
>     NOT interpreted. This is your own record's resolution and it is the right one: it
>     makes the instrument honest at every m instead of structurally unable to pass.
>     Under it the pair/σ row reads UNMEASURED (ensemble floor), NOT ELEVATED — correct
>     that cell.
>     Record alongside: at m=100 on this geometry the MC floor is 1.136× D_int_sigma
>     against sealed clean_max 1.0, so a perfectly seamless solve reads ELEVATED. State
>     that plainly as the reason the ensemble-floor clause exists.
> 33. AMEND PIN 24 (§7 discipline) TO BE TWO-SIDED. As written it catches gates that
>     cannot fail. This is a gate that cannot PASS — same pathology, opposite sign. New
>     wording: "Every quantitative gate names, at design time, the measurement conditions
>     under which it could fail AND under which it could pass. A gate that cannot reach
>     either verdict under the measurement actually taken is not a gate." Fourth instance
>     of this family (T11 vacuous pin, T0 source-scan pin, the 1.3× bracket, this).
>
> ITEM 3 — RULE-0 TEXT. Amend as proposed, with one addition and one procedural cost.
> 34. DEFINE F BY ACCURACY TARGET, NOT ITERATION BUDGET: the floor probe drives the solve
>     to a stated number of decades below the production rtol (the executed 1e-9 against
>     1e-6 — three decades — is the right construction and becomes the pre-registered
>     one), with maxiter sized to REACH it and the achieved residual recorded. "+1000" is
>     a floor only where the reference solve exited at the cap. Non-attainment of the
>     tighter tolerance is a STOP, never a fallback to a looser F.
>     Record explicitly that the executed T4 probes already conformed and that the four
>     verdicts stand unrecomputed — otherwise a future reader finds a defective rule and
>     an amendment and reasonably assumes the verdicts under it were bad.
> 35. PROCEDURAL COST OF AMENDING A SEALED INSTRUMENT — pay it, don't absorb it. The
>     rubric is PRE-REGISTERED; deviations require an explicit owner decision recorded at
>     the consuming gate, which this ruling is. But pins 32 and 34 produce a NEW SEALED
>     VERSION, and T11's own note says a rubric amendment invalidates the R-01..R-24
>     segmentation and requires a re-walk. Re-run the coverage walk against the amended
>     text and fold it into T12 alongside the C1→2 contract walk. Both directions, same
>     STOP condition.
>
> PROCESS — the adversarial review is endorsed and becomes the norm for diagnosis code.
>     It returned two findings sharper than its brief, and the confirmation-bias note is
>     the correct epistemics: a hypothesis may predate its test, and what matters is
>     whether the test could have refuted it. The half-split could have. That is a clean
>     pre-registration and it is why the diagnosis is believable.
>     NEW STANDING DISCIPLINE for §7, from finding (1d): "A passing cell gets the same
>     scrutiny as a failing one. Contamination in the flattering direction produces no
>     alarm and is therefore the more dangerous case." The ELEVATED cell drew four
>     independent lines of attack because it looked wrong. The contaminated cell was
>     CLEAN, and it was found only because someone went looking where nothing appeared to
>     be broken.
>     MINORS, fold with the above: the banned-key test asserts against a stub rather than
>     the real tree; the split-axis and ddof couplings are verified empirically but not
>     test-pinned; the commit message's "no verdict-shaped key anywhere" is overclaimed
>     against `recomputed_t4_reads.r_seam{,_sigma}`. Same weak-test class as before —
>     pin the behaviours, correct the message.
>
> SEQUENCE:
> 1. Correct the pair/σ cell to UNMEASURED (ensemble floor). Amend the rubric (32, 34),
>    new sealed version, owner decision recorded at this gate. Commit, PUSH.
> 2. Pin 31(a) — global lattice origin with the anchor-identity construction, check 1
>    re-run as its acceptance. This is the highest-risk change in the stage; treat the
>    identity re-run as a gate, not a regression test.
> 3. Pin 31(b) alignment-residual survey across the D1 roster; 31(c)/(d) recording.
> 4. Pins 33, 35, process minors. T12 absorbs the coverage re-walk.
> 5. T5 stays WAITing on the Tier-2 crossing — unchanged by this ruling, and the CRN fix
>    does not relieve it.
>
> STOP CONDITION: STOP after step 2 with the check-1 re-run and the alignment survey
> together — if the global-origin change cannot reproduce the anchor lattice exactly, it
> does not land, and I want to see that result either way before anything else moves.
> STOP IMMEDIATELY if check 1 degrades by any margin: the identity chain and the gate-5
> pins are downstream of it. Zero locked opens, tally byte-identical, seal read-only
> except the recorded rubric amendment.

### Addendum (given with the ruling — governed THIS session only)

> ADDENDUM — DO THIS FIRST, THEN STOP. The owner is clearing this session.
> Docs and tracker only: no code, no runs, no rubric amendment. Steps 1-5 of the ruling
> above are for the FRESH session, not this one.
>
> A1. MAKE THE T5 WAIT MECHANICAL. T5 is blockedBy [3,4], both completed — it is READY to
>     dispatch and its Tier-2 WAIT lives only in banner prose. The house resume protocol
>     resumes at the first unchecked task. Left as is, a fresh session dispatches the
>     stage's largest spend past a ceiling crossing while doing exactly what it was told.
>     Enter the ruling's work as REAL TRACKER TASKS with real edges:
>       T13 — rubric amendment (pins 32, 34): ensemble floor clause + F-by-accuracy-target;
>             new sealed version; correct the pair/σ cell to UNMEASURED (ensemble floor).
>       T14 — global lattice origin (pin 31a) with the anchor-identity construction;
>             check-1 re-run is its acceptance, not a regression test. blockedBy [13].
>       T15 — alignment-residual survey across the D1 roster (31b) + recordings (31c/d).
>             blockedBy [14].
>       T16 — pins 33, 35, process minors; T12 absorbs the coverage re-walk.
>     Then: T5 blockedBy [3, 4, 14] AND its description opens with the WAIT and the
>     ceiling it crossed. A WAIT that only a careful reader can see is not a WAIT.
>     Do the same for anything else WAITing that the DAG currently shows as ready.
>
> A2. LAND THE RULING IN THE TREE, VERBATIM. [this document]
>
> A3. BANNER: current halt state, this ruling received and where it lives, the four new
>     tasks, T5's mechanical block, and the STOP after T14. Write it for a reader with no
>     memory of this conversation, because that is exactly who reads it next.
>
> A4. FLUSH SESSION-ONLY STATE. [Part 2 below]
>
> A5. Commit, PUSH, verify origin has it, STOP. Do not begin step 1 of the ruling.
>     Amending a sealed instrument on a nearly-full context is how the amendment ends up
>     needing its own review round.

---

## PART 2 — SESSION NOTES, NOT OWNER-RULED

**Everything below is unratified working knowledge from the session that received the
ruling.** It is recorded so it is not rediscovered at cost, and labelled so it cannot
pass as ruled. A fresh session should verify every claim here against the tree before
relying on it — these are pointers and hypotheses, not decisions.

### 2.1 Where the CRN origin change must touch (candidate call sites, unverified as complete)

- `src/sverdrup/methods/miost_crn.py` — `coef_noise` derives its stream from
  `blake2b(f"{root}|{member}|elem")` where the element key includes
  `(scale_idx, dir_idx, phase_idx, ix, iy, global_slot)`. **`ix, iy` are the
  pavement-lattice indices measured from the BasisSpec origin — this is the binding
  site.** Its docstring promises draws are "never of array position"; that promise
  holds across windows and breaks across tiles with different origins.
- `BasisSpec` pavement fields `(x0_km, y0_km, d_x, d_y)` — added in Stage-0 T15
  ("BasisSpec DOMAIN GENERALIZATION", commit `249a08d`), defaults byte-identical, and
  **`key()` gains a suffix only when the fields are non-default**. That suffix feeds
  `params_key_hash`, which appears in recorded PCG rows — a fresh session should check
  whether any write-once evidence or identity assertion keys off that hash before
  changing origins.
- `scripts/phase14_stage1_run.py` — sets `basis_domain=(x0, y0, …)` from each tile's own
  `solve_bbox` lower-left corner (the reviewer cited ~line 1075; verify). Helpers
  `_seam_miost` / `_spec_from` build the production specs.
- `scripts/phase14_anchor_gate.py` — the anchor's own path; the T3 block records
  `basis_domain_km = [0, 0, 877.2135709, 1113.2]`, i.e. **the anchor's origin is
  (0, 0)**. Any global origin must be congruent to (0, 0) modulo the rung spacing for
  pin 31(a) to hold by construction.
- `src/sverdrup/methods/miost.py` — the `Miost(basis_domain=…)` hook that threads it.

### 2.2 Lattice arithmetic already measured (from the T4 diagnosis, `420c40f`)

- Finest rung step: **85.254 km**.
- seam_n origin `y0_km = 333.96`; seam_s and anchor both `y0_km = 0.0`; all three
  `x0_km = 0.0`.
- `333.96 mod 85.254 = 78.199 km` — the lattice is *re-placed*, not merely re-indexed;
  nearest lattice miss is `85.254 − 78.199 = 7.06 km`.
- Coincident element centres: **0** (seam_n ↔ seam_s), **148,352** (seam_s ↔ anchor).
- 3° of latitude = 333.96 km at this projection — the source of the offset.

### 2.3 Cost note the fresh session must plan for (NOT ruled — an estimate)

T14's acceptance is a **check-1 re-run**, which means re-solving the anchor's 9-window
m=100 configuration to test member sha-equality against `phase13_winner_members.npz`.
The T3 leg took **22,352 s (~6.2 h)** plus a compare phase, under a RAM gate, and died
twice before succeeding (harness process-group kill; Γ-route compare-phase OOM). The
persisted `anchor_gate_member_store.npz` cannot substitute — a lattice change must be
tested by re-solving. Budget a ~7 h RAM-gated, `setsid`-detached, checkpointed run with
completion **and** stall watchers, and expect the co-tenant RAM cycle to gate the start.

### 2.4 Open questions being carried (unresolved, not ruled)

1. **Can a single global origin satisfy pin 31(a) everywhere?** The anchor congruence
   fixes the origin modulo 85.254 km in the projected plane. Whether *adjacent D1 tiles
   at other latitudes* then coincide is exactly what pin 31(b)'s survey measures — and
   because tiles are placed in degrees while the lattice lives in km, the answer may be
   "no" at some latitudes. If the survey shows a latitude-varying residual, pin 31(a)'s
   fix is necessary but not sufficient, and the residual distribution becomes an owner
   item in its own right.
2. **Does changing `basis_domain` perturb `BasisSpec.key()` → `params_key_hash`** in any
   recorded identity assertion? See 2.1. If the anchor keeps `(0, 0)` this may be moot,
   but it should be checked rather than assumed.
3. **Which recorded σ artifacts fall under pin 31(d)'s "superseded configuration" mark?**
   At minimum: T4's `seam_rows` σ entries and `phase14.stage1.seam_sigma_diagnosis`;
   possibly also the T3 anchor `anchor_member_std_maps.nc` and any σ referenced by the
   C1→2 contract. Needs an explicit inventory when 31(d) is executed.
4. **T12 now has two inputs** — the C1→2 contract walk (pin 25) *and* the amended-rubric
   re-walk (pin 35). Its acceptance criteria currently name only the first.

### 2.5 Adversarial-review detail that did not make it into `8cf8039`

- The reviewer noted parts (A) and (C) of the mechanism demonstration are **partly
  tautological** — feeding identical identity rows to a pure function must return
  identical draws. The load-bearing content is the *centre/identity coincidence counts*
  (0 vs 148,352), not the "draws are identical" statement itself.
- FP quantization on the 1 mm centre key is **not** material: the nearest lattice miss
  (7.06 km) is ~7 million times the quantum.
- σ levels across the three solves agree within **0.2%** (0.036902 / 0.036892 /
  0.036826), so there is no level asymmetry for a geometry explanation to exploit —
  this is what closed the "seam_s is just closer to data" alternative.
- The reviewer's own corroboration of the mechanism via ORACLE/σ was **not fitted**:
  predicted `0.0035989 × √(1/3) = 0.002078` against recorded `0.002092` (0.7%).

### 2.6 Standing operational lessons this session confirmed (already in PROGRESS, repeated for the fresh reader)

- Long runs: `setsid`-detached + `python -u` + log + **completion AND stall watchers**.
  Harness task-group teardown killed one anchor launch; buffered stdout means an
  OOM-killed run leaves an empty log (exit 137 + a MemAvailable plunge is the signature).
- Persist expensive intermediate state **before** any compare phase — a compare-phase
  death must not cost the solves.
- Host throughput on this box is **non-stationary**: 1.70× drift measured within a
  single 300 s benchmark; identical-geometry windows ranged 1,656–3,480 s inside one
  run; `seam_s` ran ~30% slower than `seam_n` at identical geometry. Wall-based gates
  need ≥1.7× margins or a deterministic work unit (pin 28).
