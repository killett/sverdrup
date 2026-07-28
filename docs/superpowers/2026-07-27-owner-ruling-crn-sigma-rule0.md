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

Tracker tasks created from this ruling: **T13** (landed seal-free — see PART 4 pin
45 for the restructure), **T14** (global lattice origin; check-1 re-run is its
acceptance), **T15** (alignment-residual survey + recordings), **T16** (pins 33/35 +
process minors), **T17** (the DEFERRED rubric amendment, behind T15 — pin 45d), and
**task 18** (the userGate that blocks T14 — pin 52). **T5 is mechanically blocked**
on T14 in addition to its standing Tier-2 WAIT.

Later parts amend earlier ones; read the whole document before citing any pin.
**PART 6 (pins 51–55) SUPERSEDES pin 31's "do NOT raise m"** — see the pin-53
section at the foot.

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

---

## PART 3 — FOLLOW-UP RULING (verbatim), pins 36–39

**Status: RECEIVED AND RECORDED VERBATIM 2026-07-27, after T13's first
implementation attempt.** Recorded here, in the same document as pins 31–35,
because the T13 seal signoff cites this path for pins 36–38 and the adversarial
review correctly found that citation unsupported while these pins lived only in
session prose. Pin 36 supersedes pin 32's `3×` constant.

> T13 — DO NOT COMMIT. One defect, mine, must be fixed inside this seal version.
>
> 36. THE 3× FACTOR IN PIN 32 IS WRONG — the amended σ instrument has no reachable
>     CLEAN or ELEVATED cell.
>     Re-derived from the recorded numbers: attributability needs RMS > 3×F_ens =
>     0.0111248 m, hence R_seam_sigma > 3.407, against sealed clean_max 1.0 /
>     elevated_max 2.5. Every attributable σ verdict is therefore STRUCTURAL_STOP, and
>     the only other outcome is UNMEASURED. CLEAN is reachable only when
>     F_ens/D_int_sigma < 1/3 (m ≈ 1150 at this geometry). Pin 33's pathology, authored
>     by pin 32.
>     (a) The 3× does not transfer. The solver floor bounds a DETERMINISTIC quantity, where
>         3× is a margin. F_ens is the EXPECTATION of a sampling statistic whose null
>         distribution is tightly concentrated — your own half-split measured obs/pred at
>         0.983 and 1.004. A 3× threshold discards any true artifact below ~2.8× the
>         floor.
>     (b) DERIVE the factor, do not pick one. Reuse the reviewer's N=200k harness — it
>         already validated σ/√(m−1) to 0.4% — to characterise the null distribution of
>         RMS(sigma_delta)/F_ens directly, including the spatial correlation that sets
>         N_eff. Set the factor from that distribution at a stated confidence, with
>         explicit margin for the asymptotic σ²/(2(m−1)) approximation. Record the
>         derivation in the rubric beside the constant; a sealed constant with no
>         derivation is how this happened.
>     (c) STATE THE REACHABILITY CONDITION IN THE RUBRIC as a standing property:
>         CLEAN reachable iff factor × F_ens < clean_max × D_int_sigma. Any future
>         threshold or floor change is checked against it before sealing. This is pin 33
>         made mechanical for this instrument.
>     (d) HOLD THE SEAL AT ONE VERSION. Do not ship v2 and patch to v3 — pin 35 charges a
>         coverage re-walk per version, and a sealed record containing a rule known to be
>         unusable is worse than a delayed one. The suite re-run is the cheaper loss.
>     (e) Everything else in T13 stands as reported and is endorsed: the F-by-accuracy-
>         target construction, FLOOR_RTOL = production_rtol × 1e-3 with target and achieved
>         residual on every block, the RuntimeError naming pin 34, the conformance table,
>         the one-correction-only guard, and the chained mirroring of both versions.
>
> 37. ORACLE/σ → UNMEASURED: RATIFIED, and the extension was correct. Pin 32 was written
>     over σ-route verdicts; I named only the pair cell. Applying the rule against a
>     PASSING cell unprompted is finding (1d)'s discipline operating without being told,
>     and it is substantively right — that CLEAN was already shown contaminated by the
>     shared-origin mechanism (0.002078 predicted vs 0.002092 recorded).
>     (a) CONSEQUENCE TO RECORD PLAINLY: Stage 1 has NO attributable σ-route seam verdict.
>         The σ seam question is UNANSWERED, not answered clean. Two mean CLEAN cells are
>         the only standing verdicts.
>     (b) FIREWALL THE BOUND. The diagnosis-derived R ≈ 0.08-0.12 is a bound under the
>         not_established firewall, NOT a verdict. It must not appear adjacent to the
>         UNMEASURED rows in the Gate-1 pack in any form that lets a reader take it as
>         one. Label it, separate it, and state that no rubric verdict supports it. This
>         is the likeliest laundering path in the whole stage.
>     (c) The C1→2 contract carries the σ seam question forward OPEN. Stage 2/2G planning
>         may not assume σ seams are clean.
>
> 38. σ-LEVEL POOLING: RATIFIED. Var(σ_a − σ_b) = (σ_a² + σ_b²)/(2(m−1)), so the quadratic
>     mean is correct and the arithmetic mean is not. Record WHY it matters despite the
>     4e-8 agreement: the two constructions coincide when σ_a ≈ σ_b — the null — and
>     diverge as the levels separate, which is the signal regime. Pin the RMS form and
>     note that the T4 diagnosis used the arithmetic mean, so its 1.1356 is reproduced but
>     its construction is superseded.
>
> 39. DISPATCH BOTH REVIEWERS BEFORE T14 — and before the T13 commit. Named surfaces:
>     - The attributability factor (pin 36) and the reachability condition — the reviewer
>       should attempt to construct a measurement that returns CLEAN, and report if none
>       exists.
>     - Whether the ensemble floor belongs on RMS or on the ratio, and whether applying it
>       to the ORACLE route is coherent given the ORACLE compares blend against a seamless
>       solve rather than two ensembles (its noise structure is not the pair route's, and
>       pin 32 assumed it was — attack that).
>     - Seal-chain integrity: v1→v2 provenance, both versions mirrored, prior sha
>       preserved, the one-correction-only guard's failure mode on a second correction.
>     - Whether FLOOR_RTOL = production_rtol × 1e-3 is attainable across ALL geometries in
>       the roster, not just the three probed, and what happens at the 19° tiles.
>     - Verdict as CONFIRMED / OVERTURNED / UNDER-EVIDENCED with the settling measurement
>       named, as before.
>
> SEQUENCE: kill the pending commit; derive the factor (36b); fold 36-38; then both
> reviews; then commit T13 as ONE sealed version; then T14.
>
> STOP CONDITION: STOP after the T13 commit with the derivation, the reviewers' verdicts,
> and the reachability statement together. T14 does not start before that. If the derived
> factor still leaves no reachable CLEAN cell at m=100, that is a finding, not a failure —
> bring it to me rather than adjusting a sealed threshold to make room.

### Outcome of pin 39's reviews (recorded 2026-07-27)

Both reviews came back and **OVERTURNED the central deliverable**; see
`docs/superpowers/2026-07-27-t13-adversarial-reviews.md`. The amendment was NOT
committed and the sealed record was rolled back to ONE version (v1), applying
pin 36(d)'s own principle to the corrected work: a sealed record containing a
rule known to be defective is worse than a delayed one.

---

## PART 4 — RESTRUCTURING RULING (verbatim), pins 40–47

**Status: RECEIVED AND RECORDED VERBATIM 2026-07-27, after the pin-39 reviews.**
Pin 45 DEFERS the entire rubric amendment past T14/T15; pin 40 creates the
executor namespace (see `docs/validation/pin-registry.md`); pin 41 makes landing
a ruling a precondition of citing it, which is why PART 3 and PART 4 land in the
same commit as the work that cites them.

> T13 RESTRUCTURED. The rubric amendment DEFERS PAST T14/T15 — one seal, against the
> configuration that will actually exist. Pins 40-47.
>
> VERIFIED: origin 1e8e4ef, nothing committed since. Ruling doc contains PART 1 + PART 2
> only; no PART 3. Reviewer 2's provenance finding CONFIRMED on the tree.
>
> 40. PIN NAMESPACE — owner-numbered only. A pin number asserts owner authorship; nothing
>     else may enter the sequence. Executor decisions get their own namespace (E-1, E-2,
>     …), are marked UNRATIFIED on sight, and become pins only when I rule them, at which
>     point they are renumbered into my series BY ME, not by the citing document.
>     (a) AUDIT NOW: enumerate every pin citation anywhere in the tree — docs, code,
>         commit messages, evidence keys, seal signoffs — and reconcile against the two
>         rulings I have actually issued (31-35, 36-39). Report anything else. Any
>         executor-authored item found in my series is renumbered to E-n and its citation
>         corrected.
>     (b) The withdrawn v2 signoff is inside that audit scope even though it is rolled
>         back — a rolled-back artifact still teaches a future reader the wrong convention.
>
> 41. NO PIN IS CITABLE UNTIL IT IS ON ORIGIN. Citations reference the commit sha that
>     contains the pin text, not a document name. A signoff that cites an unlanded ruling
>     fails the seal check by construction. This closes the hole that let my own words be
>     cited before they existed — and note it is the addendum's A2 rule generalized: A2
>     landed the ruling that existed at the time, with nothing making it standing.
>     Standing now: every ruling lands verbatim, on origin, before any work cites it.
>
> 42. MAKE PIN 33 MECHANICAL — it has failed five times as prose. Every quantitative gate
>     carries, as a REQUIRED SCHEMA FIELD beside its threshold: the probability (or the
>     explicit condition) of each verdict outcome under the null, and under a stated
>     alternative the gate is meant to detect. If any outcome has probability ≈ 0 or ≈ 1
>     under both, the gate is not a gate and CANNOT BE SEALED — the seal check refuses it.
>     Instances to date: T11 vacuous pin; T0 source scan; the 1.3× bracket; pin 32's 3×
>     (no reachable CLEAN); the ±4 sd acceptance at P(reject) ≈ 1.3e-4 (could not fail).
>     Prose caught none of them at authorship time. A schema key will.
>
> 43. Q1 — RUN THE SETTLING MEASUREMENT. Do not seal 1.14 on a two-sample basis with a
>     known-broken estimator; that is the pattern that has now failed twice in one task.
>     The replay is cheap, needs no solves, and is non-parametric in N_eff — it settles the
>     defect without needing the mechanism you cannot yet reproduce. Two strengthenings:
>     (a) CAVEAT TO CARRY: ~200 partitions of the SAME 100 members share draws, so the
>         between-partition spread measures combinatorial variability, not ensemble-to-
>         ensemble variability, and will UNDERSTATE the true null spread. The derived
>         factor carries margin for that, and the caveat is recorded beside it.
>     (b) RUN AT MORE THAN ONE SPLIT SIZE (50/50 and 25/25). The factor should be
>         m-invariant because the ratio's distribution is governed by N_eff, not m — but
>         that is an assumption, it will be sealed, and it will be applied at m values not
>         yet chosen. Test it rather than inherit it.
>     Run it now: N_eff is a property of the field's spatial correlation and is unaffected
>     by the CRN pairing T14 introduces, so this result survives T14.
>
> 44. Q2 — YES to a per-route oracle floor, but SEAL THE CONSTRUCTION, NOT THE NUMBER.
>     Reviewer 1 is right that the blend-vs-seamless comparison has its own noise
>     structure and that ignoring the partition-of-unity weights overstates the floor
>     1.711×; reproducing the recorded oracle reading to 0.76% is strong corroboration,
>     and −92.7 sd below its own floor is proof of a broken model, not a pass. But 0.5845
>     is √(mean w²) for THIS pair's overlap and weight profile. Seal
>     F_oracle = √(mean w²) × σ_pooled/√(m−1) with the weights read from the actual blend
>     at evaluation time — the same discipline as the ±66 edge deriving from the frame
>     rather than being typed. Record the falsification-and-repair (−92.7 sd → 0.76%) as
>     the justification.
>
> 45. Q3 — THE PREMISE PROBLEM DECIDES THE SEQUENCE. Rule 0.b is derived for INDEPENDENT σ
>     estimates; T14 pairs the CRN BY DESIGN; T15 measures the alignment distribution that
>     would parameterize any CRN-conditional form. Sealing now means sealing against a
>     configuration we are about to replace, and pin 36(d) allows one version.
>     RULING: DEFER THE ENTIRE RUBRIC AMENDMENT — 0.a and 0.b together — to ONE sealed
>     version authored after T14 and T15, against the configuration that will exist.
>     (a) Rule 0.a defers safely: its defect is in the TEXT, and the implementation already
>         conforms (FLOOR_RTOL, achieved residual recorded, RuntimeError on non-attainment,
>         three probes at 1e-9). Keep enforcing the behaviour; seal the words later.
>     (b) THE σ ROWS DO NOT NEED A SEAL. Decouple them. The committed, dual-reviewed,
>         CONFIRMED diagnosis already establishes that BOTH σ cells are artifacts of the
>         shared basis origin. Mark both NOT_ESTABLISHED citing the diagnosis, under the
>         firewall that already exists. This is what was actually urgent, and it never
>         required amending a sealed instrument. Restoring rows we know are artifacts was
>         the correct consequence of the rollback; leaving them that way is not.
>     (c) The deferred amendment must be CRN-STATE-CONDITIONAL by construction so one
>         version survives T14 — the floor parameterized by the measured pairing, reducing
>         to the independent case in the unpaired limit. Do not derive that now; derive it
>         when T15 has measured what parameterizes it. Candidate worth evaluating: build
>         the null by splitting members while PRESERVING whatever pairing exists, so the
>         measured spread reflects the true correlation structure whatever it is.
>     (d) Enter the deferred seal as its own task blocked behind T15, with pin 42's
>         reachability and probability fields as acceptance criteria.
>
> 46. CODE AND SEAL MOVE TOGETHER. `seal_run` currently fails by construction because the
>     code carries an amendment the seal does not — the tripwire working, and it must not
>     be silenced. With 45 ruled, the Rule 0.b code comes out alongside the seal rollback.
>     Whatever the tripwire says requires a seal change moves to the deferred task with it.
>     Report which pieces fall on which side rather than assuming the line.
>
> 47. THE GUARD DEFECTS, fixed independent of any seal: the one-correction guard is
>     defeatable by deleting the per-row correction key (demonstrated live), and the
>     write-once correction reason has stale 3×F_ens baked in. A write-once surface
>     defeated by deleting its own witness is not write-once. Fix, and test-pin the
>     deletion attack specifically — a demonstrated exploit with no regression test is an
>     invitation.
>
> STANDING, from this round: pin 39's named attack surfaces produced three of reviewer 1's
> four findings. Reviews of sealed-instrument work carry a NAMED SURFACE LIST as a
> required input, authored by the requester, never improvised by the reviewer.
>
> SEQUENCE:
> 1. Pin 45(b) — mark both σ rows NOT_ESTABLISHED by diagnosis. No seal touched.
> 2. Pins 46, 47, 40(a), 41. Clean ruff/mypy, full suite to completion, seal_run green.
>    Commit, PUSH. This is the T13 that lands.
> 3. Pin 43's settling measurement — result recorded, not sealed.
> 4. THEN T14.
>
> STOP CONDITION: STOP after step 2 with the pin-40 audit result — I need to know what
> else was numbered in my series before anything downstream cites anything. STOP again
> before T14 with the settling measurement in hand. Nothing seals until after T15.

---

## PART 5 — ADDENDUM (verbatim), pins 48–50

**Status: RECEIVED AND RECORDED VERBATIM 2026-07-27, immediately before the T13
push.** Pin 48 replaces pin 41's landing-sha requirement with a check that has no
bootstrap problem.

> ADDENDUM — one change, then push, then the owner clears. No new work.
>
> 48. PIN 41 SIMPLIFIED — the bootstrap wrinkle is removed, not managed. Replace the
>     landing-sha requirement with: a pin is citable when its verbatim text is present in
>     the ruling doc at HEAD as of the citing commit. That is mechanically checkable
>     without self-reference and catches the actual failure (citing a pin that does not
>     exist). Delete the two "this commit" placeholder rows; no follow-up sha-filling
>     commit is needed. Pins 36-47 become citable the moment PART 3 and PART 4 land.
>
> 49. `ensemble_floor` / `sigma_level_rms` land on the non-seal side correctly, but nothing
>     licenses them for verdicts until T17 seals Rule 0.b. Give both a docstring stating
>     they are NOT verdict-bearing until then, and confirm no verdict path imports them.
>     The Rule-0.b row wiring is on the seal side, so this should already hold — say so
>     explicitly rather than leaving it inferred.
>
> 50. The nine UNRATIFIED E-items come to me on the next walk. Until I rule them they are
>     cited as unratified or not cited at all. Do not let an unratified E-item acquire
>     authority by being referenced in a commit message or a signoff.
>
> BEFORE THE OWNER CLEARS:
> 1. Fold 48-50.
> 2. Suite to completion, pre-commit, ruff/mypy clean, seal_run green at v1.
> 3. Commit, PUSH, and VERIFY origin has it — the tree is the only thing that survives.
> 4. Banner: state where T13 stopped, that pin 43's measurement is the next action and has
>    NOT run, that T14 has not started, and that T17 is blocked behind T15. Write it for a
>    reader with no memory of this session.
> 5. Report the origin sha, then stop.
>
> STOP CONDITION: stop at the push. Pin 43's measurement is the fresh session's first
> action, not this one's — it is a measurement whose result I have to see, and a dying
> context is the wrong place to produce a number that will be sealed against later.

### Pin 49 — verified, not inferred (recorded here because the pin asks for it)

The only importers of `ensemble_floor` / `sigma_level_rms` are
`scripts/phase14_sigma_diagnosis.py` (the establishing diagnosis),
`scripts/phase14_ensemble_floor_factor.py` (the deferred derivation harness) and
their two test files. **`scripts/phase14_stage1_run.py` — the verdict path —
imports neither**, because the Rule-0.b row wiring left with the seal side under
pin 46. Both functions carry the not-verdict-bearing statement in their
docstrings and in the module docstring.

---

## PART 6 — POST-MEASUREMENT RULING (verbatim), pins 51–55

**Status: RECEIVED AND RECORDED VERBATIM 2026-07-27, after pin 43's settling
measurement was run and reported.** Pin 51 approves the T13 tracker correction;
pin 52 blocks T14 mechanically in the same commit; pin 53 SUPERSEDES pin 31's
m-rejection (reopened, not reversed) and orders m=137 PRICED, not chosen; pin 54
endorses the closed form with a test-pin condition; pin 55 sharpens pin 45(c) into
a named question for T15.

> APPROVED with one addition. Fold, push, then the owner clears.
>
> 51. T13 TRACKER EDIT — APPROVED AS PROPOSED. Marking completed against withdrawn
>     criteria would be a false green and pin 40 is exactly that accounting. Apply the
>     status flip, the replaced criteria, and the line pointing the withdrawn criteria at
>     T17. Leaving it in_progress rather than papering it was the right call.
> 52. ⛔ AND IN THE SAME COMMIT — BLOCK T14 MECHANICALLY. Flipping T13 makes T14
>     dispatchable (blockedBy [1,2,3,4,13], all met). This is the T5 trap one task later,
>     on the stage's highest-risk change, landing precisely as the session clears. Add an
>     explicit blocker — a gate task, or T14 blockedBy an owner-ruling item that does not
>     exist yet — and open T14's description with the STOP and why. A fresh session
>     following the resume protocol must hit a wall, not a green light.
> 53. PIN 31'S m-REJECTION IS SUPERSEDED — reopened, not reversed. I rejected raising m on
>     ~512 members, derived from a 2× margin I imposed plus the un-derived 3× factor.
>     At the settled factor the requirement is m ≥ 137 (129 at 1.00, 148 at 1.07),
>     independently re-derived. Record the correction in the ruling doc against pin 31 so
>     the tree carries the supersession, not just this thread.
>     DO NOT DECIDE THE REMEDY NOW. T14 collapses F_ens by design — the very quantity the
>     m question turns on. The decision belongs after T14/T15 with Rule 0.b, where it
>     already sits. What is needed before then: price m=137 against the Tier-2 ceiling
>     that already holds T5 at m=100, since RAM scales with m and the option may be
>     blocked in practice however cheap it looks in principle. Price it; don't choose.
> 54. CLOSED FORM ENDORSED, with the standing condition. E[T] = √(2(m−1)(1−c4²))
>     reproduces both split sizes exactly on independent re-derivation. T17 uses it
>     exactly rather than by margin. Because it will be sealed and applied at m values not
>     measured here, test-pin it at the m actually used, and record that n=200 supports
>     q95-q99 only — q999 is not estimable from this sample and no threshold may rely on
>     a quantile the measurement cannot reach.
> 55. RESULT 5 SHARPENS PIN 45(c). If T_cross sits ~4.2 sd below the null while within-tile
>     partitions land on it, the independence premise may already be violated pre-T14.
>     Rule 0.b's conditional form must therefore be parameterized by MEASURED correlation
>     between the two σ fields, not by a binary paired/unpaired state — there may be no
>     clean unpaired limit to reduce to. Carry this into T15's alignment survey as a named
>     question: measure the correlation, do not infer it from lattice geometry alone.
>
> BEFORE THE OWNER CLEARS: fold 51-55; suite to completion; pre-commit, ruff/mypy clean,
> seal_run green at v1; commit; PUSH; verify origin; banner states that pin 43 is measured
> and NOT sealed, no factor adopted, T14 blocked pending owner ruling, T17 behind T15.
> Report the origin sha and stop.
>
> STOP CONDITION: the push. T14 does not start. No factor is adopted. Nothing seals.

### Pin 53 — the supersession, recorded against pin 31

**Pin 31 (PART 1) ruled: "do NOT raise m".** Pin 53 SUPERSEDES that clause and
REOPENS the question. It does not reverse it — no remedy is chosen here.

- The rejection rested on **~512 members**, from a 2× owner margin over the
  **un-derived 3× factor** that pin 36 later overturned.
- The settled factor puts the requirement at **m ≥ 137** (129 at factor 1.00,
  137 at 1.03, 148 at 1.07) — see
  `docs/superpowers/2026-07-27-phase14-pin43-settling-measurement.md` §4 and
  `phase14.stage1.ensemble_settling_measurement`.
- **The remedy is NOT decided now.** T14 collapses `F_ens` by design — the very
  quantity the m question turns on — so the decision belongs after T14/T15, with
  Rule 0.b, in T17 where it already sits.
- What pin 53 requires BEFORE then: **m=137 PRICED against the Tier-2 ceiling**
  that already holds T5 at m=100. Priced at
  `docs/superpowers/2026-07-27-phase14-m137-price.md`.

Every other clause of pin 31 stands unchanged: the global-origin fix (31a), the
alignment survey (31b), the product-consequence and superseded-σ recordings
(31c/d), and the standing "do NOT change the σ denominator, do NOT retire the
instrument".
