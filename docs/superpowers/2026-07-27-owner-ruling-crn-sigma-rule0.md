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

---

## PART 7 — EVIDENCE-WITNESS RULING (verbatim), pins 56–57

**Status: RECEIVED AND RECORDED VERBATIM 2026-07-28**, at the start of the session
that folds pin 56. Pin 56 makes the provenance-bearing evidence externally visible;
pin 57 records the m=137 pricing against pin 53 and leaves the deferral unchanged.

> FRESH SESSION — FIRST ACTIONS. Ruling lands verbatim before anything cites it (41/48).
>
> 56. MIRROR THE PROVENANCE-BEARING EVIDENCE INTO THE TREE. The evidence store is
>     gitignored and absent from a fresh clone, so every write-once surface in Stage 1 —
>     gate-5 constants, seal-chain records, the locked-instrument tally, correction and
>     withdrawal records, and now the settling measurement with its pin_53/pin_54 blocks —
>     exists on one machine and has never been externally visible.
>     (a) The issue is WITNESS, not backup. Write-once enforced by a file only its author
>         can see is a convention; nothing can demonstrate it was not rewritten. That is
>         the one guarantee this program cannot hold on trust.
>     (b) Mirror the provenance-bearing subset into version control — small, append-only,
>         the nodes whose value is tamper-evidence. Bulk data and derived artifacts stay
>         ignored; do not un-ignore the store wholesale.
>     (c) Prose in a write-up is not a substitute. A number in a document is re-typeable;
>         that is the difference the mirror closes. Keep the write-ups as they are — they
>         have been carrying this stage — but stop them being the only record.
>     (d) Report which nodes fall inside the mirror and which stay out, as with pin 46.
>         Do not assume the line; I want to see where you drew it.
> 57. m=137 PRICING NOTED, DEFERRAL UNCHANGED. That ~512 was the RAM knee and m=137 sits
>     at 27% of it (+0.5% RAM, ×1.37 wall, inside the box's own ×1.70 drift) makes the
>     option live rather than nominal. Record it against pin 53. The decision still
>     belongs after T14/T15 with Rule 0.b — T14 collapses F_ens, which is the quantity the
>     choice turns on.
>
> SEQUENCE: land 56-57 verbatim; fold 56; then T18 comes to me — it is the userGate that
> blocks T14, and T14 is the anchor-identity risk, so it does not open without my walk.
>
> STOP CONDITION: unchanged. T14 not started. No factor adopted. Nothing sealed.

### Pin 57 — recorded against pin 53

Pin 53 reopened the m question and ordered m=137 PRICED, not chosen. The pricing
(`docs/superpowers/2026-07-27-phase14-m137-price.md`) returned:

- **~512 is exactly the RAM knee.** The sizing model's phase-max only begins
  tracking `m` at m ≈ 512 (9.0893 MiB per member against a 4650.1 MiB m-free
  assembly phase), so the original rejection was priced precisely where memory
  starts to bite — it was not an arbitrary figure.
- **m=137 sits at 27% of the knee:** +23.4 MiB predicted peak (+0.5%), wall bound
  ×1.37 — **smaller than the ×1.70 throughput drift pin 28 measured inside a single
  run on this host.** It is not the binding constraint on either axis and does not
  change T5's blocked status.

**Pin 57's disposition: this makes the option LIVE RATHER THAN NOMINAL.** The
deferral is UNCHANGED — the decision belongs after T14/T15 with Rule 0.b, because
T14 collapses `F_ens`, the quantity the choice turns on.

---

## PART 8 — MIRROR-BOUNDARY CORRECTION (verbatim), pins 58–59

**Status: RECEIVED AND RECORDED VERBATIM 2026-07-28**, after the pin-56 mirror was
reported. Pin 58 CORRECTS pin 56's boundary — the test is CITATION, not stage — and
supersedes the three exclusions the executor had flagged as judgement calls. Pin 59
makes the demonstrated tamper defence a regression test.

> 58. PIN 56'S BOUNDARY CORRECTED — citation, not stage. A node is IN if a standing claim
>     cites it, wherever it lives. The nine-node list plus the seal is ratified as far as
>     it goes; three additions:
>     (a) phase14.stage0 gate records — IN. Anchor-gate checks 2 and 4 are discharged by
>         CITATION to stage-0 gate2 and the golden-tile row, so two of five checks in the
>         identity chain rest on evidence that is currently unwitnessed. This is not a
>         wider ruling than 56; it is 56 with my own mis-drawn boundary removed.
>     (b) phase14.stage1.seam_pair — IN. The m=137 pricing quotes its wall and RSS, that
>         pricing is a standing claim recorded against pin 53, and it feeds T17.
>     (c) phase8-phase13 — NOT wholesale. Enumerate the nodes carrying standing Stage-1
>         claims and include exactly those; report the list as with 56(d).
>     (d) CHECK THE ARTIFACT SHAS. The anchor gate's sha-equality against the phase-13
>         acceptance artifacts witnesses those artifacts only if their shas were recorded,
>         not merely the comparison outcome. If only the outcome was recorded, a later
>         substitution of the compared artifact would re-pass. Confirm which; if the shas
>         are absent, capture them — that closes the loop far more cheaply than mirroring
>         a prior phase.
> 59. TEST-PIN THE TAMPER DEMONSTRATION. Editing gate5.mu made check fail naming the node
>     and made sync refuse — demonstrated, not asserted, which is the right standard. Make
>     it a regression test, per the pin-47 precedent: a demonstrated defence with no test
>     is a one-time observation, and this one guards every write-once claim in the stage.
>     Cover both gates and the byte-identical restore.
>
> SEQUENCE: land 58-59 verbatim; fold; suite, pre-commit, commit, PUSH, verify origin.
> THEN T18 comes to me — it is the userGate blocking T14, and T14 is the anchor-identity
> risk, so it opens on my walk and not before.
>
> STOP CONDITION: unchanged. T14 not started. No factor adopted. Nothing sealed.

### Pin 58 — supersession note against pin 56(d)

Pin 56(d) asked where the line was drawn and the executor reported three exclusions
as flagged judgement calls: `phase14.stage0`, `phase14.stage1.seam_pair`, and
phases 8–13. **Pin 58 overturns the first two outright and narrows the third**, and
replaces the boundary test itself:

- **OLD (pin 56, as executed):** in if the node is a Stage-1 write-once surface.
- **NEW (pin 58):** **in if a standing claim CITES it, wherever it lives.**

The reason is load-bearing and is recorded here rather than summarized: **two of the
five anchor-gate checks are discharged by CITATION** to stage-0 evidence, so under
the old boundary the identity chain that T14 threatens rested, in part, on records
that were never witnessed.

---

## PART 9 — PROSPECTIVE-GUARANTEE RULING (verbatim), pins 60–63

**Status: RECEIVED AND RECORDED VERBATIM 2026-07-28**, after the pin-58 boundary
correction landed. Pin 60 makes the mirror's guarantee explicit and prospective;
pin 61 routes 58(d)'s finding into the Gate-1 pack; pin 62 discharges pin 42 for
T14's check-1 acceptance EXACTLY rather than probabilistically; pin 63 ratifies the
58(c) enumeration and the pin-59 test plan as reported.

> 60. THE MIRROR'S GUARANTEE IS PROSPECTIVE — state it once, at the top of the mirror.
>     All 22 nodes were witnessed on 2026-07-28; every record written before that date is
>     closed against FUTURE alteration and cannot speak to the interval between its
>     writing and its mirroring. The per-node caveat on the three artifact shas is correct
>     and belongs there too, but the property is general and a reader will otherwise take
>     "witnessed" to mean "proven unaltered since creation."
>     (a) ONE PLACE LEFT TO CLOSE THE INTERVAL: if phase-13's own gate records sha'd its
>         acceptance artifacts at the time, reconcile the 2026-07-28 capture against them
>         and the interval closes for those three. Check; if nothing is there, record that
>         the check was made and came back empty — a searched-and-absent is worth more
>         than an unexamined caveat.
> 61. 58(d)'s RESULT GOES IN THE GATE-1 PACK, not only the fix log. Three of four check-1
>     routes — mean_vs_acceptance, variance, and gamma_route — would have re-passed
>     against a substituted reference; gamma_route recorded neither path nor sha. Check 1
>     is this stage's foundation and checks 2 and 4 are cited on top of it. Record the gap,
>     the two fixes, and the capture caveat together. A reader who learns this from a
>     remediation commit learns it in the wrong order.
> 62. T14's CHECK-1 ACCEPTANCE NEEDS ITS PIN-42 FIELDS, and it has a clean answer: under
>     pin 31(a) the global lattice origin must reproduce the anchor's lattice exactly, so
>     check 1 fails if and only if the lattice moves. State that as the reachability
>     condition — both outcomes reachable, the failing one precisely characterised. It is
>     the first gate in the stage where pin 42 can be discharged exactly rather than
>     probabilistically, and it is the gate guarding the highest-risk change.
>     The inline reference_sha256 write is what makes that re-run self-witnessing. Good.
> 63. 58(c) ENUMERATION AND PIN 59's PLAN — both ratified as reported. Land the seven
>     gates as specified.
>
> SEQUENCE: land 60-63 verbatim; fold; suite, pre-commit, commit, PUSH, verify origin.
> THEN T18 to me.
>
> STOP CONDITION: unchanged. T14 not started, no factor adopted, nothing sealed.

---

## PART 10 — AMENDMENT-INDEX RULING (verbatim), pins 64–66

**Status: RECEIVED AND RECORDED VERBATIM 2026-07-28.** Pin 64 adds a forward-pointer
index so witnessed-but-amended nodes stay reachable from the node itself; pin 65
moves the forward-only-witness caveat from the artifact onto the CLAIMS that rest on
it; pin 66 specifies what T18's pack must contain, before it is built.

> 64. APPEND-ONLY NEEDS FORWARD POINTERS. The new-node choice was right — the shas were
>     unchanged, so a supersede would have misstated the event, and tripping the
>     append-only gate was the gate working. But a witnessed node whose claim is later
>     amended must be reachable FROM that node, or the store accumulates entries that are
>     individually accurate and collectively stale.
>     (a) Add an amendment index to the mirror manifest — append-only itself — mapping
>         node → the nodes that later amend or reconcile its claims. Reading path: manifest
>         first, always.
>     (b) Do NOT edit the witnessed node to add the pointer. The index exists precisely so
>         that stays true.
>     (c) State the convention once in the mirror README beside pin 60's prospective-
>         guarantee heading: a node's caveats are current as of its own writing; the index
>         is what tells you whether they still stand.
> 65. CAVEATS ATTACH TO CLAIMS, NOT ONLY TO ARTIFACTS. phase13_lane0_mean.nc's interval
>     stays open, and the claim resting on it is the Gate-0 pack's "signed lane0 maps score
>     0.76953" — one of the three µ values pin 29 requires disambiguating. Readers meet
>     that number in the pack. Carry the forward-only witness statement into the pin-29
>     scope note itself, not only into the artifact's mirror entry. Same for any other
>     standing claim whose supporting artifact is witnessed forward-only; enumerate them
>     rather than assuming this is the only one.
> 66. WHAT T18 MUST CONTAIN — named now so it is built once rather than retrofitted.
>     (a) The construction: how the global lattice origin is chosen, and why it reproduces
>         the anchor's lattice EXACTLY BY CONSTRUCTION rather than by subsequent check.
>         Pin 31(a) asked for identity preserved by design; I want to see the design.
>     (b) ACCEPTANCE IS TWO-SIDED AND CHECK 1 IS ONLY HALF. Check 1 passing means the
>         anchor's lattice did not move. The POINT of T14 is that other tiles' lattices DO
>         move, into global alignment. Nothing currently accepts that half. T14 needs a
>         second acceptance demonstrating the intended change actually occurred — a
>         measured rise in coincident element centres between adjacent tiles, against the
>         pre-T14 baseline. Necessary and sufficient, stated separately.
>     (c) Blast radius: which frames, tiles and stored artifacts change, and which are
>         provably untouched.
>     (d) The failure path: if check 1 fails, what state the tree is in and how it returns.
>         T14 sits under the gate-5 constants and the identity chain; a half-applied
>         lattice change is the worst outcome available and must be impossible, not merely
>         unlikely.
>     (e) Confirmation that pin 58(a)'s pre-T14 witnessing is complete — the identity chain
>         must be witnessed BEFORE the change that puts it at risk, and the mirror now
>         does that. Say so explicitly in the pack.
>     (f) What T14 supersedes downstream: pin 31(d) already rules the Stage-1 σ rows
>         superseded by the CRN change. List everything else that inherits that status.
>
> SEQUENCE: land 64-66 verbatim; fold; suite, pre-commit, commit, PUSH, verify origin.
> THEN T18, built to 66, comes to me.
>
> STOP CONDITION: unchanged. T14 not started, no factor adopted, nothing sealed.

---

## PART 11 — WITNESS-CLASS AND SECOND-CHANNEL RULING (verbatim), pins 67–68

**Status: RECEIVED AND RECORDED VERBATIM 2026-07-28.** Pin 67 refuses to flatten
three epistemic states into one "no sha" label; pin 68 names a SECOND correlation
channel — shared observations — that CRN pairing cannot address, and orders it
measured before T14 runs.

> 67. FOURTH WITNESS CLASS — split "no sha" by whether anything constrains the artifact.
>     (a) CONSTRAINED BY REPRODUCTION: artifacts whose content is pinned by a previously
>         COMMITTED result that a later run reproduced. Pin 43's member stores qualify —
>         the replay reproduced the T4 half-split readings (2.2e-16 / 0.0) that were in the
>         tree before it ran, and only those stores could have produced them. Record the
>         constraining result and its commit alongside each. Weaker than a sha, far
>         stronger than nothing, and it is what keeps the factor derivation standing.
>     (b) VERIFIED BY RE-DERIVATION: the seal file re-derives from instrument_configs()
>         and check is green, so its integrity rests on reproducibility, not on a digest.
>         Record it as such rather than as an artifact missing a sha.
>     (c) UNCONSTRAINED: whatever remains after (a) and (b). That is the class that should
>         alarm a reader, and it is smaller than ten. Report the final split.
>     (d) The forward-only capture stands for all of them regardless; 60's guarantee is
>         unchanged. This is about not flattening three different epistemic states into one
>         label — the same reason NOT_ESTABLISHED and CLEAN are different cells.
>
> 68. ⛔ ZERO COINCIDENCE, MEASURABLE CORRELATION — a second channel, and pin 45(c) needs it.
>     seam_n/seam_s share 0 coincident element centres, so their CRN draws are independent
>     by construction, yet result 5 puts T_cross ~4.2 sd BELOW the independence null. CRN
>     cannot explain that. Their obs regions overlap across lat 35-41 — 6°, 67% of each
>     tile's obs extent — and the evaluation strip at 36-40 lies entirely within it, so both
>     tiles solve the strip from substantially shared observations and their σ sampling
>     errors correlate through the data rather than through the draws.
>     (a) MEASURE IT, do not assume it: the shared-observation fraction on the strip for the
>         recorded pair, and whether it accounts for the 4.2 sd. If it does, Rule 0.b's
>         independence premise was never correct for the pair route on any lattice.
>     (b) CONSEQUENCE FOR T14: pairing the CRN addresses one channel. If a second exists,
>         T14 does not by itself restore the σ instrument, and the post-T14 expectation
>         should be stated BEFORE T14 runs so the result cannot be read as success or
>         failure after the fact.
>     (c) CONSEQUENCE FOR 45(c): this is the strongest evidence yet that the floor must be
>         parameterized by MEASURED correlation rather than by lattice geometry — here the
>         geometry predicts independence and the measurement refuses it.
>     (d) Add to T18 under 66(b): the coincidence baseline is necessary for the second
>         acceptance but is not sufficient to predict σ behaviour, and the pack should say
>         so rather than let a coincidence rise stand in for an instrument repair.
>
> SEQUENCE: land 67-68 verbatim; fold; suite, pre-commit, commit, PUSH, verify origin.
> THEN T18 built to 66 + 68(d).
>
> STOP CONDITION: unchanged. T14 not started, no factor adopted, nothing sealed.

---

## PART 12 — PREMISE AND MECHANISM RULING (verbatim), pins 69–72

**Status: RECEIVED AND RECORDED VERBATIM 2026-07-28.** Pin 69 makes Rule 0.b's
correlated-estimate derivation structural rather than a correction; pin 70 orders the
MECHANISM behind ρ named, not just the number; pin 71 authorises the DT re-score
narrowly as its own task before T14; pin 72 ratifies the prior round.

> 69. RULE 0.b IS DERIVED FOR CORRELATED ESTIMATES — the premise problem is structural.
>     The rubric evaluates the pair route at overlap points; measurement shows Jaccard
>     1.0000 there. So the independence premise contradicts the rubric's own evaluation
>     domain for ANY tiling, not merely this one. T17 does not derive an independent floor
>     and correct it; it derives the floor with ρ as a measured input. Record this against
>     Rule 0.b as the reason, so a future reader does not "simplify" it back.
> 70. NAME THE MECHANISM BEHIND ρ = 5.17%. Identical data with independent draws should
>     give ρ ≈ 0; it does not. Check first whether observation perturbations are CRN-keyed
>     on observation identity rather than on element — identical obs sets would then mean
>     identical noise realisations and explain the figure directly. Whatever the answer:
>     (a) It determines how ρ scales with overlap width and obs density, which is the
>         parameterisation 45(c) requires. A measured ρ for one pair is a number; a
>         mechanism is a model.
>     (b) It sharpens 68(b): if a pairing channel already exists, T14 stacks a second one,
>         and the predicted fall in T_cross has a magnitude, not just a direction.
>     (c) Record it before T14 either way, alongside the pre-registration.
> 71. DT SCORING TRACK — RE-SCORE AUTHORISED, narrowly, as its own task before T14.
>     Declining to run it inside a witness sweep was correct; leaving gate-5's write-once
>     constants resting on an unconstrained input is not. Constraints:
>     (a) READ-ONLY against existing artifacts. Writes exactly one witness node. The
>         gate-5 node, the tally and the seal are untouched — assert this, do not intend it.
>     (b) A MISMATCH IS A STOP, not a correction. If the re-score does not reproduce the
>         pinned constants, nothing is adjusted and it comes to me. The value of this task
>         is entirely in its ability to fail.
>     (c) Before T14, per 58(a)'s logic: gate-5 sits on the substrate T14 disturbs, and
>         witnessing after the disturbance proves less.
>     (d) Carries pin 42's fields: both outcomes reachable, the failing one characterised.
> 72. RATIFIED as reported: the 7/1/2 split, the array-level witness on the anchor member
>     store, 68(b)'s pre-registration and falsifier, and the amendment-index ordering fix.
>     A gate refusing its own author on first use is the outcome that was wanted.
>
> SEQUENCE: land 69-72 verbatim; fold; suite, pre-commit, commit, PUSH, verify origin.
> THEN pin 71's re-score, then T18 built to 66 + 68(d).
>
> STOP CONDITION: unchanged. T14 not started, no factor adopted, nothing sealed. Pin 71
> stops immediately on any mismatch.

---

## PART 13 — MODEL-VALIDATION RULING (verbatim), pins 73–76

**Status: RECEIVED AND RECORDED VERBATIM 2026-07-28.** Pin 73 refuses to let
`ρ = r²` parameterize the floor on a single low-r datum; pin 74 orders the 23%
residual named rather than absorbed; pin 75 corrects the reported separation's
construction; pin 76 ratifies the prior round.

> 73. VALIDATE THE ρ MODEL ACROSS r BEFORE IT PARAMETERIZES THE FLOOR.
>     ρ = r² is validated at r = 0.25, where √(1−ρ) is flat, and is destined for r ≈ 0.9,
>     where it is not. Re-derived: the 23% ρ error costs 1.01× in the floor at r = 0.25,
>     1.13× at r = 0.70, and 7.17× at r = 0.90. The agreement to −0.63% on T_cross is not
>     evidence the model is good; it is evidence T_cross cannot see the error.
>     (a) SWEEP IT with pin 43's exact replay — paired fraction of the obs draws from 0 to
>         1, r and ρ measured at each step, ρ = r² tested across the range. Pure arithmetic
>         over the stored acc, no solves, the same construction that collapsed 21 h to
>         22 min.
>     (b) The sweep must precede T14. T14 produces the high-r datum the model is meant to
>         PREDICT; a model calibrated on that datum has predicted nothing.
>     (c) If ρ = r² fails at high r, the floor is parameterized by the measured curve, not
>         by the closed form. That is an acceptable outcome and should be pre-registered as
>         one so it is not read as failure.
> 74. NAME THE 23% RESIDUAL, do not absorb it. ρ ≈ r² is the right form for correlated
>     Gaussian ensembles, so a 23% coefficient gap is higher-order terms, non-Gaussianity,
>     or a third channel. The 73(a) sweep distinguishes them — a third channel shows as
>     curvature, the others as a stable offset. Record which before Rule 0.b consumes it.
> 75. STATE THE SEPARATION'S CONSTRUCTION. 155.6 sd does not reproduce from the quoted
>     ±0.01511 / ±0.01638 treated as standard errors; it does reproduce if those are sample
>     sds and the separation uses standard errors over the member and pair counts. The
>     finding is unambiguous either way — even the most conservative reading is >11 sd —
>     but the number will be cited, so record N and the SE construction beside it.
> 76. RATIFIED: the mechanism identification, the member-aligned test design, 69's fold
>     with the independent form surviving only as a limit, 70(b)'s magnitude prediction and
>     falsifier, and task 19 with T14 now behind it.
>
> SEQUENCE: land 73-76 verbatim; fold; suite, pre-commit, commit, PUSH, verify origin.
> THEN pin 73's sweep, then task 19's re-score, then T18 built to 66 + 68(d).
>
> STOP CONDITION: unchanged. T14 not started, no factor adopted, nothing sealed. Pin 73's
> sweep result comes to me before T14 opens — it now bears on what T18 must predict.

---

## PART 14 — VALIDATION-RANGE RULING (verbatim), pins 77–79

**Status: RECEIVED AND RECORDED VERBATIM 2026-07-28.** Pin 77 finds that task 20's
pre-registered sweep CANNOT reach the r range the model is destined for, and names the
structural cause; pin 78 generalises the reachability discipline from VERDICTS to
VALIDATION RANGES after a third instance of the same family; pin 79 ratifies.

> 77. THE SWEEP'S RANGE IS THE REQUIREMENT — as pre-registered it cannot meet it.
>     B'_k = α·B_k + √(1−α²)·B_perm(k) with B_perm independent of tile A gives
>     corr(A_k, B'_k) = α·r0, so r spans [0, 0.2523]. A 23% ρ error costs 1.01× in the
>     floor there and 7.17× at r ≈ 0.9. Validating across [0, 0.2523] is pin 73's own
>     failure mode wearing a sweep.
>     THE CAUSE IS STRUCTURAL: acc is post-solve, so the replay reweights members but
>     cannot re-pair ELEMENT draws — and the element channel, which currently contributes
>     nothing to r, is the one T14 pairs and the one that carries r toward 0.9.
>     (a) KEEP THE CHEAP SWEEP, narrow its claim. Over [0, 0.2523] it tests ρ = r² as a
>         statistical identity and runs 74's curvature-versus-offset discriminator. Record
>         it as validating the FORM, explicitly not the coefficient at applied r.
>     (b) HIGH-r POINTS REQUIRE SOLVES. At least two, at partial element pairing — which
>         is also what T15's alignment survey says the production grid will actually
>         contain, so these are not throwaway diagnostics. Price them against Tier-1 and
>         bring the price to me; do not launch on this ruling.
>     (c) IF HIGH-r VALIDATION IS UNAFFORDABLE, that is a finding and it decides Rule 0.b's
>         form: the floor is parameterized by MEASURED ρ per pair, never by ρ = r²
>         extrapolated from low-r calibration. Pre-register that branch now so the
>         affordability answer cannot quietly select the convenient form.
>     (d) Whatever is run, state the reachable r range beside the result. A sweep that
>         reports agreement without reporting its span invites exactly the reading we have
>         twice now had to unwind.
> 78. GENERALISE THE CHECK, because this is the third time. The 3× factor could not pass;
>     the ±4 sd acceptance could not fail; this sweep could not disagree where disagreement
>     matters. Pin 42 asks for reachability of each VERDICT; extend it: a validation must
>     also state the range of the parameter over which it is validated, and whether the
>     application range lies inside it. Extrapolation beyond the validated span is declared
>     at the point of use or the gate refuses. Add to §7 and to seal_run's refusal set.
> 79. RATIFIED: pin 75's correction and its handling, the cost-arithmetic reproduction, the
>     73(c)/74 pre-registration, task 20, and T14 behind it.
>
> SEQUENCE: land 77-79 verbatim; fold; suite, pre-commit, commit, PUSH, verify origin.
> THEN the narrowed sweep; the high-r price to me; task 19's re-score; T18.
>
> STOP CONDITION: unchanged, plus: no high-r solve launches without my ruling on its price.
> T14 not started, no factor adopted, nothing sealed.

---

## PART 15 — CLOSURE-MAP RULING (verbatim), pins 80–82

**Status: RECEIVED AND RECORDED VERBATIM 2026-07-28.** Pin 80 makes T14's dependency
on task 21 explicit rather than accidental; pin 81 turns pin 78's rule on the artifact
that motivated it; **pin 82 HALTS the creation of new hardening tasks** until a
closure map is in front of the owner, and asks for a specific alternative to be
priced.

> 80. T14 BEHIND 21, EXPLICITLY. T18 is currently an accidental backstop; state the
>     dependency. If 21's price leads to high-r points, T14 goes behind those too —
>     pin 73(b) holds: T14 produces the datum the model is meant to predict, so anything
>     validating that model must precede it.
> 81. PIN 78 APPLIES TO T18's PACK. Its 70(b) magnitude prediction uses ρ = r², validated
>     over [0, 0.2523], applied at r ≈ 0.9. The pack declares that extrapolation at the
>     point of use or seal_run refuses it. The rule's second subject is the artifact that
>     motivated the rule.
> 82. CLOSURE MAP — bring me this before any further hardening task is created.
>     Open work is now 5 deliverable against 9 hardening, and no deliverable task has moved
>     since T4. The findings justified themselves; the trajectory needs a stated endpoint.
>     (a) What must be TRUE for Stage 1 to close — the minimum set, task by task, from here
>         to the Gate-1 pack.
>     (b) Which open threads are REQUIRED for the C1→2 contract, and which are honestly
>         deferrable to Stage 2 with a recorded deferral. Rule 0.b, the ρ model, the high-r
>         validation and T5's Tier-2 crossing each get an explicit answer.
>     (c) Total remaining spend against Tier-1, including T5, which has been WAITing since
>         before this chain began and has not been revisited since pin 57 priced m=137 at
>         +0.5% RAM and ×1.37 wall.
>     (d) THE OPTION I WANT COSTED ALONGSIDE: declare the σ route NOT ESTABLISHED for
>         Stage 1 and move Rule 0.b, the ρ model and high-r validation wholesale to Stage 2.
>         The mean route's two CLEAN verdicts stand; the σ question is recorded open with
>         the mechanism, the correlation channels and the reachability finding all already
>         documented — which is a real deliverable, not a gap. If that path closes Stage 1
>         materially sooner, it is probably the right one, and I would rather see it priced
>         than arrive at it by exhaustion.
>     (e) No new hardening task is created until (a)-(d) are in front of me. Findings still
>         get recorded; they do not automatically become tasks.
>
> SEQUENCE: land 80-82 verbatim; fold; suite, pre-commit, commit, PUSH, verify origin.
> THEN the closure map, before anything else.
>
> STOP CONDITION: unchanged. T14 not started, no factor adopted, nothing sealed, no high-r
> solve without my ruling.

### PART 15 addendum — pin 82 CLARIFIED (verbatim). **Explicitly NOT a new pin.**

**Status: RECEIVED AND RECORDED VERBATIM 2026-07-28**, after the executor reported the
dependency-graph finding. The owner verified that finding independently on origin
`38aa56c` and sharpened the map's central question. It is recorded verbatim because it
changes what the map must answer, and because pin 82(e) binds the owner too — this
creates no task.

> STRUCTURAL CLAIM VERIFIED independently on origin (38aa56c): T5←14 is the ONLY edge from
> the σ chain into the deliverable path. T6, T7, T8, T9, T12 carry none. T9 is
> blockedBy [3,4,5,6,7,8,10,11,12] — all closed or on the deliverable path itself. T5's own
> text: 3 mentions of per-tile, 0 of cross-tile, 0 of shared, 0 of seam.
>
> 82 CLARIFIED — the map's central question, sharpened. Not a new pin.
>
> The question is NOT "does the C1→2 contract need σ output." That conflates two different
> deferrals hiding under one edge:
>   - The σ MEASUREMENT — seam route, Rule 0.b, the ρ model. Deferrable if nothing
>     downstream reads a σ seam verdict, and the graph says nothing does.
>   - The FIX — T14 is the CRN origin correction, not an instrument. Deferring it means
>     Stage 1 executes on per-tile lattice origins, carrying the manufactured σ gradient at
>     tile boundaries that pin 31(c) describes.
> These separate if and only if no Stage-1 deliverable depends on CROSS-TILE σ behaviour.
> Within a tile the CRN guarantee holds; the defect appears at seams and in assembly.
>
> REQUIRED IN THE MAP:
> (a) Enumerate every Stage-1 output and mark each per-tile or cross-tile. Check
>     specifically: T5's χ², the raw-σ + scalar-s* reference rows, T6's SO diagnostics, and
>     T8's pricing inputs. Those are the σ-bearing quantities most likely to carry a
>     cross-tile component nobody labelled as one.
> (b) If all per-tile: dropping T5←14 costs the deliverables nothing, and the CRN defect
>     becomes a documented open item inherited by Stage 2G, where the seams are actually
>     assembled. Price that branch against the alternative.
> (c) If ANY output is cross-tile: name it. T14 then stays ahead of T5 regardless of what
>     happens to the σ measurement, and (d) of pin 82 is off the table.
> (d) Either way the CRN record travels forward COMPLETE — mechanism, both correlation
>     channels, the reachability finding, pin 31(b)'s latitude non-uniformity, the ρ model
>     and its validated span. A deferral is not a gap if the successor inherits everything
>     needed to act on it.
> (e) Note in the map that the insulation, if it holds, is a property of the fork-d pin-6
>     sub-design — per-tile lanes chosen over a shared cross-tile field at plan review, for
>     an unrelated reason, long before any of this surfaced. That distinction matters: a
>     pre-registered design decision protecting the deliverable path is a different thing
>     from a convenient reading of the dependency graph, and only the first is evidence.
>
> No new pins from me. 82(e) binds me too.
>
> SEQUENCE: suite → pre-commit → commit → push → verify origin → report sha. Then the
> closure map, before anything else.
>
> STOP CONDITION: unchanged. T14 not started, no factor adopted, nothing sealed, no high-r
> solve without my ruling.

**THE DISTINCTION THAT GOVERNS THE MAP, restated so it cannot be lost:** the σ
MEASUREMENT and the CRN FIX are two different deferrals hiding under the single edge
`T5←14`. They separate **if and only if** no Stage-1 deliverable depends on CROSS-TILE
σ behaviour. Within a tile the CRN guarantee holds; the defect appears at seams and in
assembly.

---

## PART 16 — WORKFLOW-ORDER RULING (verbatim), pin 83

**Status: RECEIVED AND RECORDED VERBATIM 2026-07-29.** Pin 83 fixes a structural
defect in the standing gate sequence: pre-commit REWRITES files, so
suite → pre-commit → commit always produced gate evidence from a pre-format tree.

> 83. RUN FORMATTERS BEFORE THE SUITE, NOT AFTER. The standing sequence is
>     suite → pre-commit → commit, but pre-commit rewrites files, so the gate evidence is
>     structurally always from a pre-format tree. Reorder: ruff-format and any other
>     rewriting hook run FIRST, then the suite, then commit with no further edits.
>     (a) Make it mechanical rather than remembered: record the tree hash at suite start
>         and assert it is unchanged at commit. A mismatch names the changed paths and
>         refuses, the way the mirror gates do.
>     (b) This round's disclosure stands as recorded and needs no re-run. Whitespace in two
>         test files, both re-run green, and the qualification is in the commit message
>         where a reader will find it.
>     (c) The reason this is worth a pin at all: you killed a 70-minute suite this round on
>         exactly this principle, correctly, and then met a smaller instance of it four
>         steps later. The principle was sound and the workflow defeated it.

**Folded WITHOUT creating a tracker task**, per pin 82(e)'s halt: this is tooling and a
sequence change, not a hardening task. The new order is
**format → stamp → suite → verify → commit**, enforced by
`scripts/phase14_gate_suite.py`.

---

## PART 17 — BRANCH B RULING (verbatim), pins 84–88

**Status: RECEIVED AND RECORDED VERBATIM 2026-07-29.** Pin 84 rules Branch B and
frees T5 from the σ chain; **pin 85 requires T5's Tier-2 block be reinstalled IN THE
SAME EDIT**, because removing T14 would otherwise leave T5 ready against an unresolved
owner ceiling — the fourth instance of that pattern; pins 86–87 fix how the discharge
and the defect are worded; pin 88 lifts pin 82(e)'s halt for the deliverable path only.

> 84. BRANCH B RULED. "Measured seam behaviour — oracle+rubric verdicts" DISCHARGES on two
>     attributable CLEAN mean verdicts plus two σ cells NOT_ESTABLISHED with the mechanism
>     documented. The rubric was pre-registered with a withholding cell so that "looked and
>     could not attribute" is a result; this is that cell used as designed, not a blank.
>     Remove T14 from T5's blockers. T5 → {T6,T7,T8} → T9 is the remaining path.
> 85. ⛔ AND IN THE SAME EDIT — REINSTALL T5's TIER-2 BLOCK. T5's WAIT is currently
>     mechanical ONLY through T14 (blockedBy [3,4,14] → T14 → T18). Removing 14 removes the
>     entire chain and T5 goes ready with an unresolved owner ceiling decision. Fourth
>     instance of this pattern. Create a userGate task for the Tier-2 crossing and put T5
>     behind it, description opening with the ceiling and the figure it crossed. Do this in
>     the same commit as 84, not after.
> 86. THE DISCHARGE IS ON REPORTING, NOT ON ANSWERING — write it that way.
>     (a) The C1→2 contract records the σ seam question OPEN, with the inheritance package
>         named explicitly: mechanism (obs_noise on observation identity, coef_noise on
>         element identity, shared root), both channels quantified (ρ = 5.17%, r = 0.2523,
>         ρ ≈ r² with its 23% residual), the reachability condition and its m requirement,
>         pin 31(b)'s latitude non-uniformity, and the ρ model with its validated span
>         declared per pin 78.
>     (b) Reaffirm pin 37(c) as a CONTRACT LINE rather than a note: Stage 2/2G may not
>         assume σ seams are clean.
>     (c) T14-T21 are not deleted. They move to Stage 2 with their pins, tasks and
>         pre-registrations intact, including 68(b)'s falsifier and 73(c)'s branch.
> 87. THE CRN DEFECT IS A PRODUCTION DEFECT, recorded as one. Pin 31(c)'s manufactured σ
>     gradient at tile boundaries is a property of the shipped system, not of an
>     instrument. Deferring T14 defers a known defect with a product consequence, and the
>     record must say that in those words — not "deferred instrument work." Stage 2G cannot
>     close while it stands. It is also the reason Branch B is honest rather than merely
>     faster: the defect travels forward named and costed, and the only Stage-1 surface it
>     touches is the one adjacency, which T4 already measured and reported.
> 88. RECOMMENDATION CELL: filled with 84-87 by this ruling. Pin 82(e)'s halt LIFTS for the
>     deliverable path only — T5 through T9 — and stays in force for the σ chain, which is
>     now Stage 2's.
>
> SEQUENCE: land 84-88 verbatim; apply 84 and 85 together; fold 86, 87; commit, PUSH.
> THEN T5's Tier-2 ceiling comes to me as its own decision — it is the last thing standing
> between here and the stage's output, and it was owner-held before any of this began.
>
> STOP CONDITION: T5 does not dispatch on this ruling. Nothing sealed. No σ-chain task runs.

---

## PART 18 — TIER-2 PROBE RULING (verbatim), pin 89

**Status: RECEIVED AND RECORDED VERBATIM 2026-07-29.** Pin 89 refuses to bring a
4× bracket to a ceiling decision and orders the binding number MEASURED. **It runs on
this ruling** — it is a PROBE, not evaluation-bearing execution.

> 89. TASK 22 ARRIVES WITH A MEASUREMENT, NOT A 4× BRACKET.
>     23.8-94.2 h/tile spans a factor of four, and the spread is an unmeasured scaling
>     exponent, not an observation. From the two existing anchors: linear gives 21.8 h/tile
>     (87 h for four), nodes^1.25 gives 29.8, nodes^1.5 gives 40.9. Your low end is the
>     linear point; the high end needs an exponent nothing measured supports.
>     (a) RUN ONE WINDOW OF ONE DIVERSE TILE AT m=100, labelled PROBE, through T2's existing
>         machinery. ~2.4 h by the linear estimate. Report per-window wall, peak RAM, and
>         iteration counts with the CONVERGED/CAPPED flag.
>     (b) Kuroshio, per the plan's own ordering — riskiest path, fail fast.
>     (c) RAM IS THE BINDING AXIS AND IS CURRENTLY MODELLED, NOT MEASURED. The ≥9,431 MiB
>         against 5,261 live is a model figure. Peak RAM from this probe is the number the
>         ceiling decision actually turns on, and pin 57 already showed the model's phase-max
>         behaves unexpectedly around m — it only begins tracking m near 512.
>     (d) Re-derive the bracket from the probe, state the residual span, and bring THAT to
>         me. If the probe lands near linear, the four-tile figure is ~87 h against a 6.0 h
>         ceiling and the decision is a clean Tier-2 grant question. If it lands high, that
>         is worth knowing before I authorise anything.
>     (e) This is a probe, not evaluation-bearing execution: PROBE label, no
>         STAGE1-EVIDENCE row, tally untouched. It runs on this ruling.
>     Precedent for why: pin 23's ratio moved 0.570 → 0.734 the moment it was measured, and
>     the m=137 pricing found the RAM knee at ~512. Neither was visible from the model.
>
> STOP CONDITION: T5 does not dispatch. The probe runs; the ceiling decision waits for its
> number. Nothing sealed, no σ-chain task runs.

---

## PART 19 — TIER-2 CEILING CLEARED (verbatim), 2026-07-30

**Status: RECEIVED AND RECORDED VERBATIM 2026-07-30.** This clears **task 22**, the
userGate that has been the sole blocker on T5 and therefore on the whole remaining
deliverable path.

> what should i do?

*(the executor's five-point recommendation followed — reproduced below as E-16, and
NOT numbered into the owner's series)*

> do all of it. but in next session. get ready to clear, then start that after resume

### What "all of it" is — recorded as **E-16, EXECUTOR-AUTHORED, OWNER-ADOPTED**

**Pin 40 governs how this is recorded.** The operating plan below was authored by the
executor, not by the owner. The owner ADOPTED it in full ("do all of it"), which
authorises the work — but adoption does not make the text owner-authored, and **a pin
number asserts owner authorship**. It is therefore filed as **E-16** and stays E-16
until the owner renumbers it into his own series, **by him, not by this document**
(pin 40). Cite it as adopted, never as a pin.

1. **A Stage-1 Tier-2 row with `max_wall_h ≈ 40 PER TILE`** — 31.0 h measured plus the
   ×1.3 residual span. **Not 124 h for the stage.** T5 is already structured as four
   INDEPENDENT per-tile legs with per-tile commits (its own Steps: kuroshio first —
   "riskiest path, fail fast" — then southern, equatorial, quiet gyre). A leg exceeding
   40 h STOPS and reports rather than running on.
2. **Launch gate per leg: `MemAvailable ≥ 2 × 4365 MiB` (~8.7 GiB)** — twice the
   MEASURED peak, not the model's 5154. Headroom on this box cycles ~4 → ~11.2 GiB, so
   legs start at the top of the cycle. This is the existing `seam_ram_gate` rule,
   unchanged.
3. **Kuroshio FIRST**, per the plan's own ordering, and now the de-risked one: pin 89's
   probe converged on it with the land-mask path intact.
4. **⛔ RE-ASSESS AFTER LEG 1.** The 31.0 h figure is one measured window × 9. **The
   first production leg is the test of that extrapolation.** Near 31 h → the remaining
   three are predictable. High → that is known after ~31 h instead of after 5 days.
5. **Raise the PCG cap for production.** The probe's member batch used **486 of 500**;
   a tighter production rtol will hit that cap, and **a capped leg can only
   under-report**.

**Explicitly NOT adopted:** trimming tiles to fit Tier-1. The four are pre-registered
for regime diversity, southern feeds T6, and T7's lanes run on all four — trimming
weakens the transfer claim rather than the bill.

### Sequencing instruction, verbatim: **"in next session"**

The owner authorised the work and deferred its START. **T5 does not dispatch in the
session that received this ruling.** Task 22 is cleared so the next session finds T5
READY with the operating procedure in its description — that is the intent, not an
accident of blocker removal.

---

## PART 20 — STALE-CRITERIA RULING (verbatim), pins 90–93, 2026-08-01

**Status: RECEIVED AND RECORDED VERBATIM 2026-08-01.** Raised on resume, before any T5
build work, when the executor found that T5's acceptance criterion 8 (the pin-12
`box_election_pending` refusal on the programmatic path) had been written while the
election was open and outlived its own premise.

> 4 — DISCHARGED BY RULING, WITH THE EXISTING TEST NAMED AS THE EVIDENCE.
>
> Option 1 is right and I am ruling it, with one correction to how it is recorded and one
> addition. Option 2 is barred: pin 42 refuses a gate that cannot fire, and building a
> permanently-False flag is that exact object. Option 3 defers a question that is already
> answered and would arrive at Gate 1 as noise.
>
> 90. CRITERION 8 IS DISCHARGED BY THE PIN-12 RULING. The criterion was written while the
>     election was open; it asks the programmatic path to refuse while box_election_pending.
>     The election closed 2026-07-25 (box KEPT, -4..11N), no such state exists in the code,
>     and NO NEW STATE IS TO BE CREATED.
>     (a) THE EVIDENCE ALREADY EXISTS. tests/test_phase14_stage1_run.py:244,
>         test_run_equatorial_reaches_gated_stub_after_pin12_ruling, pins that the
>         equatorial path no longer refuses and dies at the solve stub — and its docstring
>         names the stale-flag bug as what it catches. Cite that test as the discharge, not
>         the ruling alone. A criterion discharged by a citation to prose is weaker than one
>         discharged by a citation to a test that fails if the fact stops holding.
>     (b) ADD THE POSITIVE PIN, as Option 1 proposes: the equatorial frame IS the ruled
>         (200.0, 215.0, -4.0, 11.0) box. Today's test proves the gate is gone; it does not
>         prove the box that survived is the one I ruled. Those are different facts and both
>         are load-bearing — the whole point of keeping -4..11N was in-band coverage, and a
>         later frame edit would pass 244 silently.
>     (c) When _solve_leg lands, extend 244 to the programmatic path (record_evidence_row
>         for "equatorial") so the criterion's actual breadth concern — CLI-only coverage —
>         is met on the real path rather than at the stub. That is the part of criterion 8
>         that is still live; the refusal is not.
>     (d) Record the criterion as DISCHARGED BY RULING with the two test citations, not as
>         met and not as dropped. Same treatment as check 3 of the anchor gate: a criterion
>         whose specified mechanism became unrunnable is recorded honestly, with what was
>         run in its place named.
>
> 91. STALE PRE-REGISTERED CRITERIA — sweep once, now, rather than one at a time. This is
>     the second stale artifact this session (the plan's "the run command from Task 1 should
>     already do these" was the first, and it understated T5 by an entire build). Both were
>     written before rulings that changed them.
>     (a) Walk T5-T9's acceptance criteria against the rulings landed since 3264524 and
>         report every criterion whose premise a later ruling changed. Report only — no
>         edits, no new tasks; pin 88's halt lifted for the deliverable path, not for
>         scope growth.
>     (b) I want that list BEFORE leg 1 launches, not discovered mid-stage. A 31 h leg run
>         against a stale criterion is 31 h spent measuring the wrong thing.
>     (c) This is cheap and it is the T11 coverage-walk method pointed at criteria instead
>         of at rubric clauses. It found four unassigned clauses then; expect it to find
>         more than one now.
>
> 92. THE T5 BUILD FINDING IS RATIFIED AND WELL RAISED. The plan's Files line was wrong,
>     _solve_leg is NotImplementedError, and T5 is a substantial build before any leg
>     starts. The authorisation covers the run; the build is ordinary Stage-1 work under it.
>     Build against Task 4's _seam_pair_real_leg as the working analog, per your reading.
>     The E-16 preflight reconciliation (replacing tier1_eligible with the ~8730 MiB
>     measured-peak gate and the 40 h per-leg ceiling) is authorised work, correctly
>     identified as such.
>     CONFIRMED NON-ISSUES, ratified: pin 12 ruled; PCG cap needs no change (production
>     default 1200 against the probe's measured 486 at identical rtol 1e-6 — tolerance
>     consistency verified, which is the right check).
>
> 93. E-16 STAYS AT E-16. Filing an executor-authored plan I adopted in full as E-16 rather
>     than as a pin is exactly pin 40 working. Adoption authorises the work; it does not
>     make the words mine. Do not renumber it.
>
> SEQUENCE: land 90-93 verbatim; discharge criterion 8 per 90; run 91(a) and report; THEN
> build T5; THEN launch leg 1 at the top of a RAM cycle under E-16's gate.
>
> STOP CONDITION: leg 1 does not launch until 91(a)'s stale-criteria report is in front of
> me. After leg 1: the mandatory re-assess, per E-16 step 4. Nothing sealed; no [STAGE 2]
> task runs — READY is not RUNNABLE for 18, 19, 20.

### Consequences for the executor

- **Criterion 8 is DISCHARGED BY RULING**, recorded with two test citations — never as
  "met", never as "dropped" (90d). The **refusal** half is dead; the **breadth** half
  (90c) is live and lands with `_solve_leg`.

---

## PART 21 — SWEEP-CONSEQUENCE RULING (verbatim), pins 94–96, 2026-08-01

**Status: RECEIVED AND RECORDED VERBATIM 2026-08-01.** Rules the three sweep findings
that land inside the T5 build itself (report items 4, 5, 6), so the build is written
against the ruling rather than against the stale criteria.

> 94. OPTION 1 — VERBATIM PIN-87 CAVEAT ON EVERY σ ROW, structurally attached.
>     (a) SIGMA_CAVEAT as a constant, attached the way BRIDGE_CAVEAT already is at
>         build_evidence_row (line 456) — a schema field the row cannot be built without,
>         not prose added at write time. An unqualified σ number must not be able to reach
>         the pack.
>     (b) It cites phase14.stage1.crn_production_defect_deferred and states the defect in
>         pin 87's terms: a property of the SHIPPED SYSTEM, not of an instrument.
>     (c) OPTION 2 IS BARRED BY THE RECORD. Review pin 17 divides where FREE PROSE lives,
>         not where facts about the data live — and the bridge caveat is itself the
>         precedent: a per-row provenance fact, attached at the row, on the mean side. The
>         σ defect is the same kind of fact. Pack-level attachment also fails the pin-8
>         test: T5's rows travel independently of T9's prose, and a row that must be paired
>         with a document to be read correctly will eventually be read alone.
>     (d) OPTION 3 IS BARRED: fork-d pin 6 pre-registered the raw-σ row and pin 86 records
>         the σ question OPEN, not unmeasured. Dropping the row would delete the per-tile
>         σ levels Stage 2G needs to parameterize the correlation channels — the
>         inheritance package pin 86(a) enumerates.
>     (e) The caveat is a FACT, not an interpretation: the CRN origin defect is measured,
>         mechanism named, both channels quantified. The rider forbids interpreting the
>         numbers, not disclosing what produced them.
>     (f) SCOPE IT HONESTLY. Per pin 68, the σ defect's visible consequence is at tile
>         boundaries, and only seam_n/seam_s are adjacent — the four diverse tiles are
>         pairwise disjoint. The caveat therefore states that these are per-tile σ levels
>         under per-tile CRN origins, that cross-tile σ comparison is not supported, and
>         that the boundary gradient is deferred and named. Do not let it imply the
>         within-tile level is compromised; it is not.
>
> 95. OPTION 3 — SPLIT. Report-only rows; pin-42 fields on the j3-validation χ² only.
>     (a) Your Option 1 reasoning is right for MOST of the row: no threshold, no verdict,
>         no gate for pin 42 to attach to, and test-pinning report-only status so the
>         judgment is recorded rather than assumed is the correct instinct. Keep that.
>     (b) But the χ² j3-validation row COMPARES AGAINST AN EXPECTATION, and that is what
>         makes a gate — not whether the word "verdict" appears. Your own Option 3 names it
>         as the genuinely gate-shaped element; I agree, and that is decisive. Pin 42's
>         five prior instances were all things nobody called gates at authorship time.
>     (c) So: pin-42 fields on the χ² row (each outcome's condition under null and under
>         the alternative it is meant to detect), pin-78's validated range where a model is
>         involved, and report-only status test-pinned for everything else.
>     (d) Extend _PINNED_KEYS accordingly. A widened schema is the cost; the alternative is
>         a comparison-against-expectation with no stated failure condition, which is the
>         exact object pin 42 refuses.
>     (e) If the χ² row turns out to carry no expectation at all in the shipped
>         implementation — check before building — then Option 1 is right in full and the
>         split collapses. Verify rather than assume; report which.
>
> 96. OPTION 1 — MIRROR IT, classified under pin 67.
>     (a) Pin 58's boundary is citation, not stage or artifact type. Fork-b pin 1 makes the
>         bundle the substrate for the future wave-increment comparison, and pin 12's ruling
>         turns on in-band coverage — the bundle IS that claim's evidence. It is cited.
>     (b) OPTION 3 IS BARRED BY THE PROPERTY THAT MAKES MIRRORING WORTH ANYTHING. Pin 60:
>         the guarantee is PROSPECTIVE. Witnessing at T9 witnesses from T9, leaving the
>         interval from creation open for exactly the artifact whose value is being frozen
>         at a known configuration. Witness at creation and the interval never opens. This
>         is 58(a)'s logic — witness before the risk, not after.
>     (c) OPTION 2 IS INSUFFICIENT: a local manifest is self-witnessing. Both the manifest
>         and the file it describes sit on one box under one process's control; nothing
>         external can show either is unaltered. That is the gap pin 56(a) named.
>     (d) Assign the pin-67 class explicitly. This one is WITNESSED AT CREATION — the
>         strongest class available and the first artifact in the stage that can claim it,
>         because it is being made now rather than reconciled after the fact.
>     (e) Mirror the manifest with per-file shas, not the maps. The manifest is small and
>         append-only; the maps are bulk and stay out per pin 56(b). The shas are the
>         witness.

### Consequences for the executor (PART 21)

- **`SIGMA_CAVEAT` is a REQUIRED schema field**, attached at `build_evidence_row` exactly
  as `BRIDGE_CAVEAT` is — a row the σ side cannot be built without. Not prose at write
  time (94a).
- **Its scope is bounded** (94f): per-tile σ levels under per-tile CRN origins;
  **cross-tile σ comparison NOT supported**; boundary gradient deferred and named. It must
  **not** imply the within-tile level is compromised — it is not. The four diverse tiles
  are pairwise disjoint; only `seam_n`/`seam_s` are adjacent (pin 68).
- **The σ row is NOT dropped** (94d): fork-d pin 6 pre-registered it, and Stage 2G needs
  the per-tile σ levels to parameterize the correlation channels (pin 86a's inheritance
  package).
- **Pin 42 applies to the χ² j3-validation row ONLY** (95c); everything else is
  **report-only, test-pinned as such**. Extend `_PINNED_KEYS` (95d).
- **⛔ 95(e) IS A VERIFY-BEFORE-BUILD**: check whether the shipped χ² row carries an
  expectation at all. If it does not, the split collapses and report-only is right in
  full. **Report which** — do not assume.
- **The lane-0 MANIFEST is mirrored, the maps are not** (96e). Pin-67 class:
  **WITNESSED AT CREATION** (96d) — the first artifact in the stage that can claim it.
  Witness at creation, not at T9, so the interval never opens (96b, pin 60).

---

## PART 22 — T9 OUTPUT-SHAPE RULING (verbatim), pins 97–99 + reboot addendum, 2026-08-01

**Status: RECEIVED AND RECORDED VERBATIM 2026-08-01.** Rules the T9 output-shape items and
the remaining sweep items, explicitly **before T5b hardens the row shapes that feed the
pack**. Carries an owner addendum R1–R6 for an imminent host reboot.

> 97. T9 OUTPUT SHAPE — ruled now, before T5b hardens the rows.
>     (a) "SIX TRANSFER READINGS" → FOUR. The store settles it: seam_n/seam_s carry no
>         scores, no reference_row, no bridge_caveat — solve records, not readings — and
>         SEAM_NON_TRANSFER_NOTE says so in the artifact itself. The anchor is the identity
>         subject, not a transfer reading. Stage 1 delivers FOUR transfer readings, one per
>         diverse tile. Correct the criterion and test-pin the count against the store so it
>         cannot drift back.
>     (b) "ANCHOR FIVE-GATE BLOCK" → the honest accounting already ruled 2026-07-26 and
>         already written into phase14_anchor_gate.py:164-177: TWO run and passed (1, 5),
>         TWO cited and pre-ratified at Gate 0 (2, 4), ONE proxy-passed with the specified
>         era no-op DEFERRED. The code says "five green" does not survive careful reading in
>         Stage 2; the pack must say the same. Cite the code as the discharge.
>     (c) "SEAM VERDICT" SINGULAR → the pack reports TWO attributable mean CLEAN verdicts
>         and TWO σ cells NOT_ESTABLISHED, and states that Stage 1 has NO attributable
>         σ-route seam verdict. Per pin 37(b), the σ seam question is UNANSWERED, not
>         answered clean. Keep the pin-37(b) firewall: the diagnosis-derived bound must not
>         sit adjacent to the UNMEASURED rows in any form a reader could take as a verdict.
>     (d) PACK CONTENTS (1)-(10) GAIN THE REQUIRED SECTIONS: pin 61 (58(d)'s result — three
>         of four check-1 routes would have re-passed against a substituted reference, both
>         fixes, the capture caveat and its reconciliation, including the searched-and-
>         absent one), pin 86 (the σ question OPEN with the full inheritance package
>         enumerated), pin 87 (the CRN production defect in its own words — a property of
>         the shipped system, and Stage 2G cannot close while it stands).
>     (e) Report the corrected criteria set before building T5b, so the row shapes are cut
>         to a pack whose shape is settled.
>
> 98. χ² PIN-42 FIELD RECORDS, IT DOES NOT GATE. Your reading is right and is now the
>     ruling. reduced_chi2 compares against an expectation of 1.0, and harness.py:1145
>     deliberately made it non-gating with coverage as the only bar. That was a decision,
>     not an oversight, and pin 42 does not reverse it.
>     (a) The pin-42 field STATES the outcome conditions under null and alternative and
>         RECORDS the non-gating status with its citation. It must not be implemented as a
>         threshold, a refusal, or anything that changes what ships.
>     (b) Test-pin the non-gating status explicitly — a later reader must not be able to
>         "complete" the gate by adding the bar that was deliberately left out.
>     (c) This is pin 42's purpose working correctly: the object was always an
>         expectation-comparison with no stated failure condition, and now it says so.
>
> 99. THE REMAINING SIX SWEEP ITEMS — ruled together, briefly, since each has one answer.
>     (a) T6's ±66 branch: pin 2 ruled production-representative 2026-07-25, so only
>         halo ≤ 2.0 is live. Collapse the branch; keep the derivation from the frame per
>         pin 16 so the arithmetic stays computed, not typed.
>     (b) T7's "no new ceilings exist": false since task 22 and E-16. Rewrite against the
>         live ceiling — a lane affordable under the 40 h per-leg ceiling is not a WAIT.
>     (c) T8's pricing basis: pin 23(a) ruled the T2 probe CAPPED and unusable for absolute
>         claims. Price from the CONVERGED numbers instead — pin 89's probe (3.440 h/window,
>         4365 MiB peak, 441/486 iters) and the anchor gate. State the basis in-row.
>     (d) Any sweep item not covered by 97-99: report it, do not fix it. 91(a)'s report-only
>         constraint still holds for anything I have not ruled.
>
> SEQUENCE: land 97-99 verbatim; fold; report the corrected criteria set; THEN build T5b;
> THEN launch leg 1 at the top of a RAM cycle under E-16's gate.
>
> STOP CONDITION: unchanged. Leg 1 does not launch until the corrected criteria set is in
> front of me. After leg 1, the mandatory re-assess per E-16 step 4. Nothing sealed; 18, 19,
> 20 remain READY-not-RUNNABLE.
>
> ADDENDUM — OWNER REBOOTING SOON. Read before executing 97-99.
>
> R1. ⛔ LEG 1 DOES NOT LAUNCH BEFORE THE REBOOT. Regardless of RAM headroom, regardless
>     of whether T5b finishes. A 31-40 h leg started now dies partway. Build only; the
>     launch waits until the owner says the box is back and stable.
> R2. INVENTORY WHAT IS ACTUALLY IN FLIGHT, and report it as a list. Do not assume either
>     direction: this session has produced three false completion reports from pgrep
>     returning wrappers, and a set of watcher shells that turned out to be stale with
>     nothing behind them. Use the pids captured at launch (logs/gate.pid and equivalents),
>     not a scrape. For each live process: what it is, what it writes, and whether losing it
>     costs anything.
> R3. ANYTHING OF VALUE ONTO ORIGIN FIRST. If a suite is mid-run it dies with the box — let
>     it die rather than racing it, and re-run after. Do not commit on a stamp whose suite
>     did not complete; the pin-83 fix now refuses that, and it should be allowed to.
> R4. setsid DOES NOT SURVIVE A REBOOT. It protects against the terminal or session closing,
>     not against the machine going down. The standing detach discipline gives no protection
>     here, and any note implying otherwise should be corrected where it stands.
> R5. BEFORE THE LEGS EVER RUN, ESTABLISH WHETHER RESUME ACTUALLY WORKS. Per-window PCG
>     checkpointing exists (b71dc7f, efd515a) and the anchor gate used a leg-level crash
>     resume. Whether a T5 diverse leg can resume from checkpoint after a hard kill is
>     UNVERIFIED. Verify it cheaply — kill a short run mid-window and resume it — before
>     committing 31 h to a path whose recovery is assumed. If resume does not work, that is
>     worth knowing before leg 1, not after a power event during leg 3.
> R6. BANNER BEFORE THE REBOOT: what was in flight, what was killed, what needs re-running,
>     and the standing state (T5b in build, leg 1 unlaunched and NOT to be launched without
>     the owner). Write it for a reader who returns to a cold box.
>
> Then stop. Do not start anything long-running until the owner confirms the box is back.

### R2 inventory as executed, 2026-08-01 — NOTHING OF VALUE WAS IN FLIGHT

Resolved from the pids captured at launch, not a scrape, per R2:

| Handle | Captured pid | Reality |
|---|---|---|
| `logs/gate.pid` | 1795155 | **not alive** |
| `logs/phase14_settling.pid` | 532474 / 532537 / 532886 | **not alive** |
| any real `gate_suite` / `pytest` / phase14 worker | — | **none exists** |
| 8 watcher shells | alive `Ss` | **stale — nothing behind them** |

The eight live processes were watcher shells spinning `sleep`. Watcher `1695408` watches
pid `1692440`, which is **itself a watcher shell** — so it would spin forever on a shell
and never on the gate. That is R2's named failure mode, confirmed by resolution rather
than assumed. **The reboot cost nothing**; no suite was mid-run, so R3 had nothing to race.

### Consequences for the executor (PART 22)

- **T9 delivers FOUR transfer readings**, test-pinned against the store (97a).
- **The pack carries the ruled anchor accounting**, citing `phase14_anchor_gate.py:164-177`
  as the discharge — never "five green" (97b).
- **The pack reports two mean CLEAN + two σ NOT_ESTABLISHED** and states plainly that
  Stage 1 has **no attributable σ-route seam verdict**; pin 37(b)'s firewall holds — the
  diagnosis-derived bound must not sit adjacent to the UNMEASURED rows (97c).
- **Pack sections gain pins 61, 86, 87** (97d).
- **The χ² pin-42 field RECORDS, never gates** (98) — and the non-gating status is itself
  test-pinned so nobody can "complete" the bar that was deliberately left out (98b).
- **T6 collapses to `halo ≤ 2.0`, computed from the frame, never typed** (99a).
- **T7 rewrites against the live 40 h per-leg ceiling** (99b).
- **T8 prices from the CONVERGED numbers** — pin 89's probe and the anchor gate, basis
  stated in-row; the CAPPED T2 probe is unusable for absolute claims (99c).
- **Report-only still binds anything 97–99 did not rule** (99d).
- **⛔ R1: leg 1 does not launch before the reboot**, regardless of headroom or build state.
- **R4 correction owed:** `setsid` protects against terminal/session close, **NOT** against
  the machine going down. Any standing note implying reboot protection is wrong and is
  corrected where it stands.
- **⛔ R5 is a NEW PRECONDITION ON LEG 1:** resume-after-hard-kill is **UNVERIFIED**. Verify
  it cheaply (kill a short run mid-window, resume) **before** committing 31 h to a recovery
  path that is currently assumed.
- **No `box_election_pending` state is to be created** — pin 42 bars a gate that cannot
  fire (90).
- **A positive frame pin is added** (90b): the equatorial frame IS `(200.0, 215.0, -4.0,
  11.0)`. Test 244 proves the gate is gone, not that the ruled box survived.
- **91(a) is a HARD STOP CONDITION on leg 1**, not a nicety. Report only — no edits, no
  new tasks; pin 88's halt lifted for the deliverable path, not for scope growth.
- **PCG cap: no change.** Ratified at 92.
- **E-16 is not renumbered** (93).

---

## PART 23 — s*/χ² IDENTITY + GUARD + PUSH-HOOK RULING (verbatim), pins 100–102, 2026-08-29

**Status: RECEIVED AND RECORDED VERBATIM 2026-08-29.** Rules the s*/χ² identity surfaced
during T5b, ratifies the provenance-guard broadening with one confirmation owed, and names
the silent push hook as the standing hazard it is.

> 100. s* / χ² IDENTITY — MAKE IT STRUCTURAL, DO NOT SPLIT THE SUPPORTS.
>      Verified: calibration.py:15 returns mean((truth-mean)**2/var), and s* on the same
>      points is the same expression. The docstring is right; the docstring is not what
>      travels.
>      (a) DISJOINT SUPPORTS REFUSED. s*'s support is set by what Stage 2G needs to inherit,
>          not by the wish to make a comparison meaningful. Manufacturing independence
>          degrades one number to decorate another.
>      (b) ATTACH THE IDENTITY TO THE ROW as a schema field — the shared expression named,
>          and same_by_construction asserted — so no consumer can read agreement as
>          corroboration. Same construction as SIGMA_CAVEAT under pin 94.
>      (c) TEST-PIN THE IDENTITY AS AN INVARIANT, not as documentation: assert equality
>          where the supports coincide, so a future change that makes them diverge fires
>          loudly instead of quietly producing two different numbers under names that imply
>          they should match. Divergence may be legitimate; it must never be silent.
>      (d) Sixth instance of the unfailable-check family (T11 vacuous pin, T0 source scan,
>          the 1.3× bracket, pin 32's 3×, the ±4 sd acceptance, this). Record it as such in
>          the §7 discipline's instance list — the list is the argument for why the rule
>          is mechanical.
> 101. PROVENANCE GUARD — RATIFIED, with one confirmation owed.
>      Broadening mission_from_track_path to the token before _phy_l3 is correct, and
>      refusing the filename workaround was the right call: a Pacific track named
>      "gulfstream" would have been undetectable forever and would have poisoned every
>      downstream mission attribution.
>      (a) CONFIRM THE ORIGINAL NARROWNESS WAS INCIDENTAL, not a deliberate whitelist. It
>          matched exactly one scheme; if that was load-bearing somewhere, broadening it
>          widens what the guard accepts. You retained and test-pinned loud failure on
>          non-scheme names, which is the right protection — say explicitly that nothing
>          previously refused is now accepted.
> 102. THE PUSH HOOK DID NOT FIRE, and that is the standing hazard itself. Remote sat at
>      ba35d80 while local had moved. You caught it with git ls-remote; it would otherwise
>      have surfaced as my walking a stale tree and ruling on it.
>      (a) MAKE THE HOOK'S FAILURE LOUD. A silent no-op in the mechanism that keeps origin
>          and local in step is worse than having no hook, because it is trusted.
>      (b) VERIFY AGAINST THE REMOTE, not the local ref, in the report line — you did this
>          round; make it the standing form.
>      (c) No archaeology needed: I have verified origin every round, so nothing shipped
>          unpushed before this.
>
> SEQUENCE: land 100-102 verbatim; fold 100 and 101(a); THEN T5c.
>
> STOP CONDITION: unchanged. Leg 1 does not launch — R1 stands until you declare the box
> back and stable, and the 91(a) sweep items outside 97-99 remain report-only. Build only.

### What PART 23 changes

- **The s*/χ² identity becomes a row field, not a docstring** (100b) — the shared
  expression named in the record, `same_by_construction` asserted, so agreement can never
  be read as corroboration.
- **Supports stay coincident** (100a) — splitting them to manufacture independence is
  REFUSED; s*'s support is Stage 2G's inheritance requirement, nothing else.
- **The identity is an INVARIANT with teeth** (100c) — equality asserted where the
  supports coincide; divergence must fire loudly, never appear silently.
- **§7's instance list grows to six** (100d) — the list is the argument for the rule.
- **The guard broadening is RATIFIED** (101), with the incidental-not-whitelist
  confirmation owed and answered below.
- **The push hook is the hazard** (102) — its silence is worse than its absence, because
  it is trusted. Loud failure required; remote-verified reporting is now the standing form.

---

## PART 24 — CHECK-PLACEMENT + HOOK-PROTOCOL RULING (verbatim), pins 103–105, 2026-08-30

**Status: RECEIVED AND RECORDED VERBATIM 2026-08-30.** Moves the s*/χ² invariant's first
firing into preflight, promotes hook installation from a gotcha into the resume protocol,
and ratifies the guard-widening sweep as the standard for that class of change.

> 103. THE s*/χ² INVARIANT FIRES TOO LATE — move the first firing into preflight.
>      Verified at calibration_readings (phase14_stage1_run.py:3608-3613): chi2 is computed
>      once and returned as both reduced_chi2 and scalar_s_star — the same object. They
>      cannot differ for any input on the current path. So the raise in build_scores_block
>      can only fire on a future caller wiring them from separate paths, which is a
>      CONSTRUCTION error: present from the first line, discoverable in seconds, and under
>      the current placement first discovered at the end of a leg.
>      (a) EXERCISE build_scores_block IN PREFLIGHT on cheap synthetic inputs, before any
>          solve. A construction error then costs seconds. Your own fixture demonstrated
>          this: s*=2.14 vs χ²=1.83 fired on first contact, which is where it belongs.
>      (b) KEEP THE ROW-BUILD RAISE. Do not downgrade it to a recorded warning — if the two
>          diverge at row build the row is wrong and must not be written. With (a) in place
>          the only path to it is a genuine mid-leg change, which is worth losing a leg over.
>      (c) TEST-PIN THAT THEY COME FROM ONE CALL, not merely that they are equal. Equality
>          is guaranteed by aliasing today, so an equality test passes even if a future
>          refactor computes them twice from drifting inputs. The invariant worth pinning is
>          single-source, not agreement.
>      (d) GENERAL FORM, for §7 alongside the six instances: a check earns its placement by
>          where the error it catches ORIGINATES, not by where the value is consumed. An
>          invariant guarding a construction error belongs where construction happens. This
>          is pin 83's lesson (formatter before the suite) and pin 89's (measure before the
>          5-day decision) in a third costume.
>
> 104. HOOK INSTALLATION BELONGS IN THE RESUME PROTOCOL, not in a gotcha.
>      .git/hooks is unversioned, so every clone and every box rebuild starts with no hook —
>      and this session has already had one box reset. A note in PROGRESS is prose a fresh
>      session may read after it has already committed.
>      (a) Add scripts/install_git_hooks.sh to docs/project-context.md §10's resume
>          checklist as an explicit early step, alongside the mirror check.
>      (b) Better still, make its absence self-announcing: have the resume checks REPORT
>          whether the post-commit hook is installed, so "no hook" is a visible state rather
>          than a silent one. That there was never a hook — not one that failed — is the
>          finding, and it went unnoticed for the whole stage precisely because absence
>          looked like success.
>
> 105. RATIFIED: 101(a)'s both-directions sweep (2665 names, zero resolved-then-unresolved,
>      zero changed tokens, 1900 newly resolved, one corner stricter with no such file) is
>      the standard for a guard widening — it establishes what was gained and, more
>      importantly, that nothing previously refused is now accepted. The provenance argument
>      that a leak cannot be downgraded is sound: detection needs mission ∈ assimilated and
>      the token is identical wherever both patterns resolve. 100(a)-(d) and 102 as folded.
>
> SEQUENCE: commit the pending folds when the suite is green; land 103-105 verbatim; fold
> 103 and 104; THEN T5c.
>
> STOP CONDITION: unchanged. Build only. Leg 1 does not launch — R1 stands until you declare
> the box back and stable, and the sweep items outside 97-99 remain report-only.

### What PART 24 changes

- **The identity check gets a SECOND, EARLIER firing site** (103a) — the row-build raise
  stays exactly as it is (103b), but the construction is exercised on synthetic inputs
  before any solve, so a mis-wiring costs seconds instead of a leg.
- **The pinned invariant becomes SINGLE-SOURCE, not agreement** (103c) — equality is
  guaranteed by aliasing today, so an equality test would survive a refactor that computed
  the two values twice from drifting inputs.
- **§7 gains the placement rule** (103d): a check earns its placement by where the error it
  catches ORIGINATES, not by where the value is consumed — pins 83 and 89 in a third costume.
- **Hook installation moves from a gotcha into the resume protocol** (104a), and its
  absence becomes self-announcing (104b): "no hook" must be a REPORTED state, because
  absence looked like success for an entire stage.
- **The both-directions sweep is now the STANDARD for widening a guard** (105).

---

## PART 25 — GROUNDTRACK-ABSENCE RULING (verbatim), pins 106–107, 2026-08-30

**Status: RECEIVED AND RECORDED VERBATIM 2026-08-30.** Accepts the GroundTrack absence at
the four diverse tiles as a NAMED GAP, orders the spec tension recorded as a design
conflict rather than an execution gap, and clears T5d to proceed.

> 106. GROUNDTRACK ABSENCE — ACCEPTED FOR STAGE 1, RECORDED AS A NAMED GAP.
>      Verified cause: groundtrack requires ORBIT_GEOMETRY, the Phase-11 provider is
>      challenge-box scoped, so Registry.applicable correctly returns false at the diverse
>      tiles. Absence recorded as absence is fork F working.
>      (a) NO PRODUCER IN STAGE 1. A per-tile geometry derivation is a new surface, which
>          the spec forbids for this wiring, and pin 82's constraint holds.
>      (b) NAME THE SPEC TENSION, because Stage 2 inherits it: the spec asks for GroundTrack
>          per tile×era AND zero new surfaces, and those are incompatible while the geometry
>          provider is challenge-box scoped. That is a design conflict, not an execution
>          gap, and it should be recorded as one so the successor stage does not rediscover
>          it as a bug.
>      (c) THE GATE-1 PACK STATES THE COMPOSITION IS INCOMPLETE at the four diverse tiles —
>          in the transfer-readings section where a reader meets the numbers, not only in an
>          absence row they may never open. Policy (b) pins the composition; the pack must
>          not present four readings as if that composition were satisfied.
>      (d) C1→2 CARRIES PER-TILE ORBIT GEOMETRY as named Stage-2 work, with the founding-
>          metric context: this is the 0.410→0.331 lineage, the spec's own standing
>          instrument, absent at exactly the tiles the stage was built to measure. Cheap to
>          record now, expensive to reconstruct later.
>      (e) This is a REAL WEAKENING of the deliverable and the record says so plainly. It is
>          accepted because absence honestly recorded beats geometry that does not belong to
>          the tile, not because the gap is small.
>
> 107. T5d PROCEEDS. State the lane-0 coupling before building rather than after: my reading
>      is the equatorial bundle serves fork-b pin 1's wave-increment substrate and has no
>      dependency on orbit geometry, so a future per-tile geometry decision does not touch
>      it. If any part of the bundle would be shaped differently under 106(d)'s Stage-2 work,
>      say so now — that is the only thing that would justify settling geometry first.

### What PART 25 changes

- **The absence is ACCEPTED, and named** (106) — fork F worked; no Stage-1 producer (106a).
- **The tension is a DESIGN CONFLICT, recorded as one** (106b): "GroundTrack per tile×era"
  and "zero new surfaces" cannot both hold while the geometry provider is challenge-box
  scoped. Recorded so Stage 2 inherits a known conflict, not a fresh bug report.
- **T9's pack states the incomplete composition WHERE THE NUMBERS ARE** (106c) — not only
  in an absence row a reader may never open.
- **C1→2 carries per-tile orbit geometry as named Stage-2 work** (106d), with the
  0.410→0.331 founding-metric context attached.
- **The record calls this a real weakening** (106e) — accepted on honesty grounds, not
  because it is small.

### Answer to 107 (the lane-0 coupling, stated BEFORE building)

**Nothing in the bundle would be shaped differently by 106(d)'s Stage-2 work, so geometry
does not need settling first.** Checked against what the bundle actually is: maps, the
FROZEN fold/eval frame, the evidence pack and `lane0_manifest.json`. The frame is a
fold/eval partition, the maps are the solve output, and pin 12's in-band-coverage claim —
the thing pin 96(a) says the bundle is evidence FOR — turns on the box, not on orbit
geometry. `groundtrack` reads ORBIT_GEOMETRY at evaluation time; it contributes nothing to
what is persisted.

**One genuine coupling, folded into T5d now rather than discovered later:** the persisted
pack embeds TODAY's instrument composition, in which GroundTrack is a recorded absence. A
future wave-increment run under per-tile geometry would carry a DIFFERENT composition, and
a blind pack-to-pack comparison would then be comparing different instrument sets while
looking like a like-for-like increment. The manifest therefore records the composition
(standing rows + recorded absences with their reasons) as a first-class field, so the
later comparison is composition-aware by construction. This changes nothing about the
bundle's shape — it makes the frozen baseline self-describing.

---

## PART 26 — ANISOTROPY-AXIS + 106-SURFACE-SWEEP RULING (verbatim), pins 108–109, 2026-08-30

**Status: RECEIVED AND RECORDED VERBATIM 2026-08-30.** Sharpens where the T6 anisotropy
line sits (UNEVIDENCED, not "limited"), and orders a report-only sweep of every Stage-1
consumer of an ORBIT_GEOMETRY-derived quantity across T6–T9.

> 108. T6's ANISOTROPY AXIS IS UNEVIDENCED — say so, do not weaken it to "limited".
>      Verified: the reported 1.72 is exactly 1/cos(54.5°), a coordinate-grid property that
>      would read 1.72 under perfectly isotropic sampling. The ring spectrum is isotropic by
>      construction. Neither can speak to directional sampling.
>      (a) T6 records the anisotropy axis as UNEVIDENCED at Stage 1, with the cause cited to
>          106. Any kernel option whose case rests on directional sampling is marked
>          UNSUPPORTED BY STAGE-1 EVIDENCE — not "weakly supported", which invites a reader
>          to weigh it.
>      (b) THE DECISION MAY NOT BE MADE ON THIS AXIS. If the option set cannot be separated
>          without it, that is a WAIT and it comes to me as one. A kernel election is not
>          improved by being made from a cosine.
>      (c) STATE THE PROPAGATION. The kernel election drives operative_halo_deg() (fork-d
>          pin 4), which sets the SO obs-frame edge and the ±66 margin (pin 10). An
>          under-evidenced kernel choice becomes a geometry fact. The option table already
>          carries the halo column; add the sentence that says why it matters here.
>      (d) Your handling — absence recorded with the consequence written into the block,
>          T6 forbidden from presenting grid arithmetic as measured sampling — is ratified
>          and is the correct shape. 108 sharpens where the line sits, it does not reverse
>          you.
>
> 109. SWEEP THE 106 SURFACE ONCE — third time this method is called for.
>      106's conflict has now bitten twice (T5's GroundTrack rows, T6's per-direction
>      diagnostics), both discovered by building into them. T7 and T8 are next and will
>      discover theirs the same way unless swept.
>      (a) Enumerate every Stage-1 consumer of an ORBIT_GEOMETRY-derived quantity across
>          T6-T9 and report which are satisfied, which are absent, and what each absence
>          costs its consumer. Report only — no fixes, no producers, no new tasks.
>      (b) The grep already suggests the radius may be narrow: fidelity.py:130 records that
>          fidelity deliberately does not read ORBIT_GEOMETRY, and resolution.py:42 records
>          it as over-declared there and never read. Someone pruned this surface before.
>          Confirm that holds rather than assuming it.
>      (c) Fold the result into 106(d)'s Stage-2 handoff, so per-tile orbit geometry arrives
>          at Stage 2 with its full consumer list rather than as one missing row.
>      (d) Same method as T11's coverage table and 91(a)'s criteria sweep, and it has found
>          something every time. This is the last surface I expect it to be needed on in
>          this stage; if it finds a third class, that is worth knowing before T6 opens.
>
> SEQUENCE: commit T5d when the suite is green; land 108-109; run 109(a) and report; THEN
> T5e.
>
> STOP CONDITION: unchanged. Build only. Leg 1 does not launch until you declare the box
> back and stable. 109 is report-only.

### What PART 26 changes

- **T6's anisotropy axis is UNEVIDENCED, not "limited"** (108a) — 1.72 is exactly
  1/cos(54.5°), a coordinate property that would read the same under perfectly isotropic
  sampling. Any kernel option resting on directional sampling is **UNSUPPORTED BY STAGE-1
  EVIDENCE**, a phrasing that cannot be weighed.
- **The kernel decision may not be made on that axis** (108b) — if the options cannot be
  separated without it, that is a WAIT that comes to the owner.
- **The propagation is stated** (108c): the election drives `operative_halo_deg()`
  (fork-d pin 4), which sets the SO obs-frame edge and the ±66 margin (pin 10) — an
  under-evidenced kernel choice becomes a GEOMETRY FACT.
- **The 106 surface is swept ONCE, report-only** (109), and the result folds into 106(d)'s
  Stage-2 handoff so per-tile orbit geometry arrives with its full consumer list (109c).

---

## PART 27 — STRAY-ARTIFACT, ATTRS-BUG AND LOOKUP RULING (verbatim), pins 110–113, 2026-08-30

**Status: RECEIVED AND RECORDED VERBATIM 2026-08-30.** Authorises deletion of the two test
strays with a recorded trace, orders the production-path attrs bug fixed FIRST, amends
106's scope to exclude the box tiles, and ratifies the 109 sweep.

> 110. DELETE BOTH STRAYS — authorised. Record the deletion, do not just do it: what they
>      were, when written, by which test, and the sha of the .nc before removal. A deletion
>      from the evidence directory that leaves no trace is its own provenance gap.
>      (a) ROOT CAUSE IS TEST ISOLATION. Tests reaching the production data directory is the
>          defect; the two artifacts are symptoms. Sandbox the Stage-1 test paths so this
>          cannot recur, and test-pin that a test run writes nothing under data/.
>      (b) THE REUSE PATTERN IS THE SEVENTH INSTANCE of the unfailable-check family
>          (phase14_stage1_run.py:4875, `if not track.exists()`). A bare existence check
>          cannot distinguish a legitimately built artifact from a test leftover, so it
>          silently adopts whatever is there. Gate reuse on the artifact's own provenance —
>          at minimum a recorded sha and a build record — not on the filename existing.
>          Add to §7's instance list.
> 111. ⛔ THE ATTRS BUG IS IN THE PRODUCTION PATH — fix before leg 1, ahead of everything
>      else here. build_tile_validation_track inherits the first daily file's global attrs,
>      so every T5 leg would write evidence claiming 2016-12-31 to 2017-01-01 coverage for a
>      year concatenated from ~365 files. combine_attrs="drop" plus our own provenance is
>      the right fix. Test-pin the coverage span against the actual concatenated range, so
>      the assertion is about the data rather than about the setting.
> 112. FIX THE LOOKUP, NOT THE PLACEMENT — and 106 is amended.
>      (a) RESOLVE THE GEOMETRY ARTIFACT FROM ITS CANONICAL LOCATION in ours/, as
>          phase13_probe.py:51 and phase13_refit_readings.py:47 already do. Do NOT copy it
>          into the evidence directory: a duplicate raises the witness question you
>          correctly flagged, and the canonical artifact should stay canonical.
>      (b) 106 IS AMENDED IN SCOPE. It stands for the four diverse tiles — genuine design
>          conflict, h2ag ≠ h2g, box-and-φ₀ scoped, absence honestly recorded. It does NOT
>          cover anchor, seam_n, seam_s, where the absence was a lookup path and is fixable
>          with no new producer. Record the amendment against 106 with the sweep as its
>          cause; do not silently widen the fix.
>      (c) WEDGE EXCLUSION: expect restoration at anchor and the seam pair only. The four
>          diverse tiles stay outside the derivation's scope, so the southern tile's slope
>          remains a degraded estimand and 108 stands for T6 unchanged. State which tiles
>          recovered and which did not, in-row — wedge_exclusion:false must never appear
>          without saying whether it is 106's conflict or a fixable gap.
>      (d) The seam and anchor readings are already recorded. Say plainly whether restoring
>          GroundTrack there changes any recorded value or only adds rows; if it changes a
>          recorded value, that is a supersession and comes to me before it lands.
> 113. 109 RATIFIED, including its correction of my own 106. One direct consumer, one
>      indirect through track_wedge_masks, one correctly pruned; T7 and T8 verified clear
>      rather than assumed. The prune was real and the radius was wider than the key —
>      that distinction is the sweep earning its cost for the third time.
>
> SEQUENCE: 111 first, it is in the production path. Then 110 with its record, then 112.
> Land 110-113 verbatim alongside. THEN T5e.
>
> STOP CONDITION: unchanged. Leg 1 does not launch until you declare the box back and
> stable. If 112(d) turns out to change a recorded value, stop and bring it to me.

### 112(d) ANSWERED BEFORE ANY FIX LANDS — additive only, NO supersession

**Restoring GroundTrack at anchor / seam_n / seam_s changes NO recorded value. It can only
ADD rows, and today it does not even do that.** Verified against the live store rather than
reasoned from the code:

- `phase14.stage1` currently holds no `report_rows` node at all (store keys read
  2026-08-30; `tiles`, `report_rows`, `anisotropy_inputs`, `land_mask_exercise` and
  `equatorial_lane0_manifest` are all absent). The T5c wiring writes report blocks from
  `_solve_leg`, and the anchor (T3) and seam-pair (T4) legs ran BEFORE that wiring existed.
- The recorded anchor and seam values — `anchor_gate` (five checks), `gate5` (µ/σ/λx) and
  `seam_rows` (the rubric verdicts) — are produced by `score_tile` / `their_eval` and the
  seam metrics. **No instrument row feeds any of them**, so no geometry-derived quantity
  enters a recorded number.
- Consequence: the lookup fix is **purely additive and prospective**. It makes GroundTrack
  and the wedge exclusion available to any FUTURE block built for those tiles; it rewrites
  nothing. **No supersession, and nothing to bring back under the 112(d) condition.**

---

## PART 28 — POST-HOC RECOVERY + BEHAVIOURAL SCOPE PIN (verbatim), pins 114–116, 2026-08-30

**Status: RECEIVED AND RECORDED VERBATIM 2026-08-30.** Authorises a bounded, additive
post-hoc recovery of the box tiles' report rows, replaces the fragile source-scan scope
test with behavioural ones, and ratifies the 110–112 folds.

> 114. POST-HOC RECOVERY AUTHORISED — bounded, additive, its own task.
>      Verified from the signature: build_tile_report_block takes mean_map: Path and
>      computes from a persisted artifact. No solve. The anchor and seam maps exist.
>      (a) Compute the report rows for anchor, seam_n, seam_s against the stored maps under
>          the fixed lookup, and APPEND them. Read-only inputs; no closed leg re-runs; no
>          recorded value changes — you have already established there is no report_rows
>          node to conflict with.
>      (b) Appending to closed tasks' evidence goes through the append-only path with a
>          forward pointer from the T3/T4 nodes, per pin 64. A reader arriving at the anchor
>          gate node must be able to reach rows that did not exist when it was written.
>      (c) Same shape as pin 71's re-score: scoring existing artifacts is not the
>          evaluation-bearing execution the stop condition guards. If it turns out to
>          require a solve, stop and tell me — that changes the ruling.
>      (d) If any row comes back with a value that contradicts something recorded rather
>          than merely adding to it, stop. That would be a supersession and it comes to me.
>      (e) The diverse tiles are untouched: still 106, still DESIGN CONFLICT, and 108 stands
>          for T6.
> 115. MAKE THE SCOPE PIN BEHAVIOURAL. Asserting 295 and 38.1 appear nowhere in the source
>      is the T0 source-scan construction I already replaced once — "295" is a substring of
>      1295, and 2.95e2 passes it vacuously. The catch it encodes is the best find in this
>      round and must not rest on a fragile test.
>      (a) Feed the function an artifact carrying a DIFFERENT box_lon and phi0 and assert
>          the scope follows the artifact. That fails on any hardcoding, including forms a
>          string scan cannot see.
>      (b) Add the adversarial case directly: an artifact whose mission families match a
>          tile outside its box, asserting the tile is refused rather than handed geometry
>          that does not belong to it. Four of five CMEMS codes matching is precisely why a
>          mission-keyed lookup would have succeeded silently, and that is the bug worth a
>          permanent test.
> 116. RATIFIED: 111's decoy-first red/green with the span pinned against the data rather
>      than the setting; the deletion record with pre-deletion sha, producing test, and why
>      the leg reached that point; the default-argument diagnosis — that an autouse sandbox
>      cannot help when `evidence_path: Path = EVIDENCE` binds at import — which is a real
>      find and the reason threading paths explicitly was the correct fix rather than a
>      heavier one; provenance-gated reuse; and the wedge flag carrying IN SCOPE versus
>      DESIGN CONFLICT in-row.
>
> SEQUENCE: commit the current folds when green; land 114-116; do 115 then 114; THEN T5e.
>
> STOP CONDITION: unchanged. Leg 1 does not launch until you declare the box back and
> stable. 114 stops on any contradiction rather than resolving it.

### What PART 28 changes

- **The box tiles' report rows are recovered post-hoc** (114) — computed from the STORED
  maps under the fixed lookup, appended, no solve and no closed leg re-run. It stops on
  any contradiction (114d) rather than resolving it.
- **The forward pointer goes in the mirror's amendment index, NOT in the witnessed node**
  — pin 64(b) is explicit ("Do NOT edit the witnessed node to add the pointer"), and 114(b)
  cites 64, so reachability is satisfied by the index.
- **The scope pin becomes behavioural** (115) — a synthetic artifact with a different
  `box_lon`/`phi0`, plus the adversarial mission-match-outside-the-box case, replacing a
  string scan that `1295` or `2.95e2` would defeat.

---

## PART 29 — R5 RESUME TEST + RESIDUAL SWEEP RULING (verbatim), pins 117–120, 2026-08-30

**Status: RECEIVED AND RECORDED VERBATIM 2026-08-30.** Rules R5 into an executable test
with bit-identity as its bar, orders the residual sweep items enumerated for a single
ruling, corrects how the 0.331 reproduction is labelled, and ratifies the T5e-adjacent
finds.

> 117. R5 RULED — RUN IT, and its acceptance is bit-identity, not survival.
>      Resume-after-hard-kill has never been tested and four legs at ~31 h is ~5 days of
>      exposure during which setsid protects nothing (R4).
>      (a) Kill a short diverse-tile run mid-window, resume, and compare the resumed output
>          against an uninterrupted run of the same configuration. The bar is BIT-IDENTICAL
>          output. "Resume completed without error" is not the test — a resume that produces
>          subtly different results is worse than no resume, because the difference is
>          invisible and would silently enter a leg's evidence.
>      (b) Kill it hard (SIGKILL), not gracefully. A clean shutdown path is not what a power
>          event exercises.
>      (c) Test resume from a MID-WINDOW checkpoint, not a window boundary. Boundaries are
>          the easy case and are not what costs 30 hours.
>      (d) IF RESUME IS NOT BIT-IDENTICAL, that is a finding and it comes to me before leg 1
>          — it would mean the four legs must each complete uninterrupted, which changes the
>          risk profile of the whole authorisation and possibly its shape.
>      (e) Cheap by construction: short run, small window count. Do not scale it up.
> 118. THE RESIDUAL SWEEP ITEMS — bring me the list. 97, 99 and 94-96 ruled eleven of the
>      thirteen; enumerate exactly what remains unruled, one line each with its criterion and
>      what changed underneath it. I will rule them together. They should not be discovered
>      one at a time by building into them, which is the failure mode 91 was created to end.
> 119. THE 0.331 REPRODUCTION IS A DETERMINISM CHECK — label it as one. The anchor maps were
>      already bit-identical to the phase-13 winner (check 1, max|Δ| = 0), so an identical
>      score follows from identical inputs. It is a genuine end-to-end wiring test and it
>      could have failed; it is not independent confirmation of the founding metric. State
>      which kind it is wherever it appears, including the Gate-1 pack. Same distinction as
>      s*/χ² under pin 100.
> 120. RATIFIED: the NaN canonical-text fix (a guard that would have raised a false
>      supersession on its own second run is the seventh-and-a-half instance of the family,
>      and catching it before it fired is the point); PENDING for registered-but-unwritten
>      mirror paths, which correctly makes absence a named state rather than a silent one;
>      114's recovery as executed; 115's mutation-checked behavioural pins; and the
>      stall-watcher gotcha with its do-not-tune instruction.
>
> SEQUENCE: land 117-120; run 118's enumeration and report; run 117; THEN hold at the launch
> gate.
>
> STOP CONDITION: leg 1 does not launch on this ruling. It needs 117 green, 118 ruled, and
> the owner's declaration that the box is back and stable — all three.

### What PART 29 changes

- **R5 becomes an executable test with a hard bar** (117): SIGKILL, mid-window, and
  **bit-identical** output against an uninterrupted run — survival is explicitly not the
  test. A non-identical resume is a FINDING that comes to the owner before leg 1 (117d).
- **The residual sweep items are enumerated once and ruled together** (118), rather than
  discovered by building into them — the failure mode 91 exists to end.
- **The 0.331 reproduction is relabelled a DETERMINISM CHECK** (119) — the anchor maps
  were already bit-identical to the phase-13 winner, so an identical score follows from
  identical inputs. A genuine end-to-end wiring test that could have failed; NOT
  independent confirmation of the founding metric. Same distinction as s*/χ² under pin 100.

---

## PART 30 — PER-WINDOW PERSISTENCE + DURABILITY RULING (verbatim), pins 121–126, 2026-08-31

**Status: RECEIVED AND RECORDED VERBATIM 2026-08-31.** Orders per-window persistence and
an atomic checkpoint write before leg 1, rules the two residual sweep items, and requires
the relabel interpretation to travel with the bridge caveat.

> 121. PER-WINDOW PERSISTENCE BEFORE LEG 1 — bounded, acceptance is bit-identity.
>      R5 was raised to decide whether 31 h legs are safe to launch. Bit-identity answers a
>      narrower question, as you said. Re-derived: per-solve checkpointing caps loss at ~31 h;
>      per-window persistence caps it at ~3.44 h, a 9× reduction over ~124 h of compute.
>      (a) Persist each window's members as it completes, so a crash costs one window.
>      (b) ACCEPTANCE IS BIT-IDENTITY of the assembled member store against the current
>          monolithic path. R5 just built the harness for exactly this comparison; reuse it.
>      (c) Bounded: persistence and reassembly only. No change to the solve, the scoring, or
>          the evidence schema.
>      (d) If bit-identity fails, stop and bring it to me. A cheaper recovery path that
>          perturbs the output is not cheaper.
> 122. FIX THE NON-ATOMIC CHECKPOINT WRITE. np.savez straight to the final path, ~23 MB, no
>      temp-and-rename, with the vulnerable window recurring every 50 iterations across
>      ~124 h. Write to a temp path and rename — atomic on POSIX same-filesystem, no change
>      to checkpoint content, no numerical consequence. This kill landed clean; that is luck
>      and not a property. Test-pin that a truncated checkpoint is DETECTED rather than
>      silently half-loaded.
> 123. h2ag → h2g IS AN INTERPRETATION AND TRAVELS WITH THE BRIDGE CAVEAT.
>      Applying the golden tile's recorded relabel rather than inventing one is right, and
>      refusing loudly on codes with no counterpart is the correct guard. But the anchor uses
>      h2g natively while the diverse tiles use relabelled h2ag, so the two sides differ in a
>      component of the frozen config.
>      (a) The golden-tile bridge delta was measured WITH the relabel in place, so it already
>          absorbs whatever the relabel costs — AT THE ANCHOR BOX. Per pin 7 that does not
>          transfer per-tile, so the relabel's cost at the diverse tiles is unmeasured, with
>          exactly the structure of the bridge caveat itself.
>      (b) Name it in the same breath as the bridge caveat, not in a separate note. The
>          mission_relabel row field is the right mechanism; the pack must say what it means.
>      (c) Record the alternatives that were refused and why: dropping h2ag changes the
>          constellation and breaks like-for-like; deriving an R for it unfreezes the config.
>          Relabelling is the least-bad option, not a free one.
> 124. RESIDUAL SWEEP ITEMS RULED.
>      (a) #14 — adopt your honest form verbatim: "zero locked opens, one deferred production
>          defect named at crn_production_defect_deferred". As phrased it read as a clean
>          bill, and pin 87 makes it not one.
>      (b) #15 — T9's verifyCommand becomes the gate suite in pin 83's order. T5e has run it
>          for real, so the correct command is established rather than hypothetical.
>      (c) RULED-BUT-UNFOLDED NEEDS A TRACKER STATE. You are right that it is indistinguishable
>          from unruled on a checklist, and rows 7-9 sit in it. Mark them explicitly so a
>          fresh session cannot read a ruled item as an open question or an unfolded one as
>          done. Same defect class as READY-not-RUNNABLE.
> 125. STATE THE PROBE/PRODUCTION PATH COMPARISON. Pin 89's probe omitted the frozen rspec;
>      R5's baseline includes it. Mean-leg iterations 441 → 437, under one percent. Record
>      that against the probe's numbers as the evidence they transfer, replacing the
>      size-dominated assertion. Also record that the probe path and production path differ
>      at all — a future reader must not assume a probe exercises production.
> 126. RATIFIED: the invalid-R5 retraction and its cause; attempt 2's construction
>      (process-group kill, survivor check, no-completed-record check, checkpoint readability,
>      distinct exit codes so a failure names itself); the h2ag fix and its three tests,
>      including that relabelled codes satisfy RSpec.sigma2_for while h2ag still raises; and
>      119's relabelling of the 0.331 reproduction.
>
> SEQUENCE: commit the relabel fix when green; land 121-126; do 122, then 121; fold 123-125.
> THEN hold at the launch gate.
>
> STOP CONDITION: leg 1 needs 121 bit-identical, 122 landed, 124 folded, and the owner's
> declaration. 117 is green; 118 is now ruled.

### What PART 30 changes

- **Per-window persistence lands BEFORE leg 1** (121), with **bit-identity of the assembled
  member store** as its acceptance — reusing R5's comparison harness. Loss per crash drops
  from ~31 h to ~3.44 h across ~124 h of compute. Bounded to persistence and reassembly
  (121c); a bit-identity failure STOPS and comes to the owner (121d).
- **The checkpoint write becomes atomic** (122) — temp-and-rename — and a truncated
  checkpoint must be DETECTED, not half-loaded.
- **The relabel travels with the bridge caveat** (123): its cost is absorbed at the anchor
  box and is UNMEASURED per-tile, with the bridge caveat's exact structure. The refused
  alternatives are recorded — dropping `h2ag` breaks like-for-like, deriving an R for it
  unfreezes the config. **Least-bad, not free.**
- **Both residual sweep items are RULED** (124a/b), and **"ruled but unfolded" becomes an
  explicit tracker state** (124c) — the same defect class as READY-not-RUNNABLE.
- **The probe/production divergence is recorded** (125) with the measured transfer: mean
  leg 441 → 437, under one percent.

---

## PART 31 — CHECK-AUTHORITY RULING + HANDOFF (verbatim), pins 127–129, 2026-08-31

**Status: RECEIVED AND RECORDED VERBATIM 2026-08-31.** Fixes 121's acceptance to ≥2
windows, ratifies 128's finding, rules that a narrower check may not override a broader one
that has already spoken, and records the owner's handoff.

> 127. 121's ACCEPTANCE NEEDS ≥2 WINDOWS. A single-window bit-identity test cannot fail on
>      the thing 121 changes — with one window, assembly is the identity operation. Run the
>      comparison at two windows minimum, so ordering, concatenation axis, dtype and
>      member-axis alignment are actually exercised.
>      (a) Precedent: pin 43's replay failed its own check at 4.2e-17 because the member axis
>          must be fastest-varying. That bug is invisible at n=1 and is precisely what
>          per-window assembly can reintroduce.
>      (b) Keep m small. The question is assembly correctness, not cost; m=2 across two
>          windows is enough and stays cheap.
>      (c) Compare against a fresh monolithic run at the SAME configuration, not against a
>          stored digest from a different window count.
> 128. CONFIRM THE GATE SUITE'S mypy SCOPE matches the commit hook's. Your narrow pre-check
>      over one file passed where the hook over 419 refused. The hook did its job here; the
>      concern is whether phase14_gate_suite.py's own mypy step has the same scope. If it is
>      narrower, the same divergence recurs inside the gate, where it costs a suite run
>      instead of a commit attempt. One line to check, and it is pin 83's own territory.
> 129. A NARROWER CHECK MAY NOT OVERRIDE A BROADER ONE THAT HAS ALREADY SPOKEN.
>      Distinct from pin 42's family: these checks worked. The mypy hook reported Failed over
>      419 files and was answered with Success over 1; R5's survivor warning was correct and
>      was read past to a green two lines below. In both cases the authoritative signal came
>      first and a weaker one was run afterward and believed.
>      (a) §7 rule: once a gate has reported a failure, only a rerun of THAT gate at THAT
>          scope clears it. A narrower or different check is evidence about something else.
>      (b) Where a check emits a warning alongside a verdict, the warning is part of the
>          verdict. A test whose green line can be read without its warnings is mis-designed
>          — make the warning fail the exit code, as R5's attempt 2 did with distinct codes.
>      (c) 128's finding is ratified: both hook and gate suite run `mypy .` over the whole
>          tree, `pass_filenames: false`, scopes match. No divergence in the tooling.
>      (d) 127 accepted as revised — two windows, m=2, fresh two-window baseline, and the
>          old single-window digest correctly retired rather than quietly reused.
>
> HANDOFF, whenever the owner clears. Nothing here is new work.
>
> H1. Land 127-129 verbatim FIRST, before building anything. 127's design rationale is the
>     thing that does not survive a clear: a fresh session told "test bit-identity" writes
>     the one-window test, because it is the obvious one, and it cannot fail.
> H2. The two-window monolithic baseline digests go in the tree when measured, with the
>     window plan and m recorded beside them, and an explicit line retiring
>     logs/r5/baseline.json as the reference.
> H3. Banner states the leg-1 gate as four items, all of which must be true:
>     121 bit-identical at ≥2 windows / 122 landed / 124 folded / owner declares the box back
>     and stable. Three are executor work; the fourth is not, and has been open across
>     several sessions.
> H4. READY ≠ RUNNABLE, restated at the top: READY is [5, 12, 18, 19, 20]; 18, 19 and 20 are
>     the [STAGE 2] σ chain under pin 88's halt and must not be started. Only 5 and 12 are
>     Stage-1 work.
> H5. Rows 7-9 of the stale-criteria sweep are RULED BUT UNFOLDED, their folds landing inside
>     T6/T7/T8 which have not opened. Per 124(c) that state must be visible in the tracker,
>     not inferable — a fresh session reading a checklist cannot distinguish it from unruled.
> H6. Carry pin 108 forward: T6's anisotropy axis is UNEVIDENCED, and 106's design conflict
>     means the southern tile's slope stays degraded regardless of 112's lookup fix.

### What PART 31 changes

- **121's acceptance moves to ≥2 windows** (127) — at one window assembly is the identity
  operation and the test cannot fail on what 121 changes. Pin 43's 4.2e-17 member-axis
  ordering bug is the named precedent for what hides at n=1.
- **The single-window R5 baseline is RETIRED as 121's reference** (127c/H2) — a fresh
  two-window monolithic run is the only valid comparison.
- **§7 gains the check-authority rule** (129a/b): once a gate reports a failure, only a
  rerun of THAT gate at THAT scope clears it, and a warning emitted beside a verdict is
  PART of the verdict — make it fail the exit code rather than trusting it to be read.
- **The tooling is exonerated** (129c): hook and gate suite both run `mypy .` whole-tree.
  The divergence was an executor error, not a scope gap.

---

## PART 32 — LEG-1 GATE RATIFICATION (verbatim), pins 130–132, 2026-09-01

**Status: RECEIVED AND RECORDED VERBATIM 2026-09-01.** Closes executor items 1–3 of the
leg-1 gate, makes the format-before-suite ordering the standing form, and carries the three
unresolved items forward explicitly.

> 130. LEG-1 GATE — ITEMS 1-3 RATIFIED AND CLOSED.
>      121: bit-identical at two windows, CI and production path, with window 1 proven
>      LOADED by the convergence log (two PCG rows against the monolithic four) rather than
>      inferred from wall time. That is the right evidence and the timing argument would not
>      have settled it.
>      122: mutation-checked against a direct-write mutant, with the truncated-checkpoint
>      refusal naming itself instead of surfacing as a bare BadZipFile.
>      124: both residual items folded, attestation form verbatim, verifyCommand corrected.
>      Item 4 is the owner's and remains open.
> 131. RUN ruff format . BEFORE ANY SUITE INTENDED FOR A COMMIT, not only inside the gate
>      suite. You identified this correctly: pin 83 fixed the ordering where it was
>      mechanised and left it broken everywhere else, so the defect recurred structurally on
>      ordinary commits. Make it the standing form, and prefer running phase14_gate_suite.py
>      for any commit whose evidence will be cited — a second ordering discipline maintained
>      by memory will drift from the mechanised one.
> 132. CARRIED FORWARD, unresolved and not resolvable by executor work: the four diverse
>      tiles carry no GroundTrack row (106's design conflict — transfer readings presented
>      with their composition stated INCOMPLETE, per 106(c)); T6's anisotropy axis is
>      UNEVIDENCED (108), so any kernel option resting on directional sampling is a WAIT
>      that comes to me, not a decision T6 makes; and a power event still costs the window
>      in flight (~3.44 h), which is the residual R5 could not remove.

### What PART 32 changes

- **Leg-1 gate items 1–3 are CLOSED** (130). Item 4 — the owner's declaration that the box
  is back and stable — is the only remaining precondition.
- **Format-before-suite becomes the standing form** (131), and the *mechanised* path
  (`phase14_gate_suite.py`) is preferred for any commit whose evidence will be cited,
  because a second ordering discipline maintained by memory drifts from the mechanised one.
- **Three items are carried forward as unresolved** (132), none of them executor-fixable:
  GroundTrack absent at the four diverse tiles, T6's anisotropy axis unevidenced, and the
  ~3.44 h in-flight window a power event still costs.

---

## PART 33 — R1 DISCHARGED: THE BOX DECLARATION (verbatim), 2026-08-31

**Status: RECEIVED AND RECORDED VERBATIM 2026-08-31.** This is leg-1 gate **item 4** —
the one precondition pin 130 left open, and the one that is not executor work.

> box is stable

### What PART 33 changes

- **The leg-1 gate is now FOUR-FOR-FOUR.** Items 1–3 were ratified and closed at pin 130
  (121 bit-identical at two windows; 122 atomic checkpoint write; 124 both residual sweep
  items folded). Item 4 is discharged by the declaration above. **R1's standing block —
  "LEG 1 DOES NOT LAUNCH WITHOUT THE OWNER SAYING THE BOX IS BACK AND STABLE" — is
  LIFTED.**
- **Leg 1 launches under E-16 unchanged** (ruling PART 19, owner-adopted). Nothing in this
  declaration alters the operating procedure: per-leg ceiling ~40 h with a leg over it
  STOPPING and reporting; per-leg launch gate `MemAvailable ≥ ~8730 MiB` (2 × the MEASURED
  4365 MiB peak); order **kuroshio → southern → equatorial → quiet_gyre**, commit per tile;
  **re-assess after leg 1 before leg 2**; PCG cap raised (`STAGE1_PCG_MAXITER = 1200`, pin
  26b — already the CLI default); `setsid`-detached with completion AND stall watchers on
  the PID captured at launch.
- **What the declaration does NOT cover, stated so it is not read wider than it is:**
  pin 132's third carried item still holds — a power event costs the window in flight
  (~3.44 h). Pin 121 capped that loss at ONE window; it did not remove it. A stable box
  lowers the probability of that event; it does not change the cost when it happens.
- **Unchanged by this declaration:** T12's Findings 1 and 5 (the Gate-1 shipped-config
  election OUTCOME has no producing AC; this table has no slot in the Gate-1 pack) are
  **still owed a ruling**. They bind T9, not T5, so they do not hold leg 1 — but they are
  not discharged by it either.

---

## PART 34 — LEG-1 RE-ASSESSMENT RULING (verbatim), pins 133–138, 2026-09-01

**Status: RECEIVED AND RECORDED VERBATIM 2026-09-01.** Holds leg 2 on a diagnosis rather
than a basis change, refuses the "hold 8,730" option outright, ratifies the mirror
registration and T12's Finding 5, gives C-11 a post-gate producer, and orders the
verification tool fixed.

> 133. ⛔ DIAGNOSE THE RAM GROWTH BEFORE ANY BASIS CHANGE. Leg 2 stays held.
>      Re-derived: (7389 − 3379)/8 = 501.2 MiB per additional window, and the linear model
>      reproduces window 9 exactly. That is accumulation, not a peak. With per-window
>      persistence live, a completed window's members should be releasable.
>      (a) Determine whether the ~501 MiB/window is retained by merged_members holding
>          completed windows after persisting them, or by something else. Report the
>          mechanism, not a workaround.
>      (b) IF RELEASABLE: fix it, re-measure the peak on a SHORT multi-window run (3 windows
>          is enough — the signal is the slope, not the magnitude), and E-16 §2 stands
>          unchanged at 2 × the corrected peak. On window 1's figure that is ~6,758 MiB,
>          comfortably inside the cycle.
>      (c) IF GENUINELY UNRELEASABLE: bring me the mechanism and I will re-pin the basis.
>          Option (c) may then be right, but the multiplier must be re-derived from what the
>          2× was protecting against, not chosen because 1.3 is reachable. A margin picked
>          to fit the box is not a margin.
>      (d) OPTION (a) IS REFUSED OUTRIGHT: holding 8,730 while it means 1.18× is asserting a
>          margin that does not exist, and MemAvailable bottomed at 3,660 MiB — leg 1 was
>          closer to an OOM than the gate implied. It survived; that is not evidence the
>          gate worked.
>      (e) The fix, if there is one, is bounded and its acceptance is bit-identity of the
>          assembled store, exactly as 121's was. Reuse that harness.
> 134. PIN 78 SHOULD HAVE CAUGHT THE PROBE'S EXTRAPOLATION. The probe was validated at ONE
>      window and applied to NINE — an out-of-range application of exactly the kind 78
>      requires be declared at the point of use. Wall came back 0.63× pessimistic, RAM 1.69×
>      optimistic. Report why 78 did not fire: if seal_run's refusal set covers only sealed
>      gates, then unsealed measurements can extrapolate silently and the discipline has a
>      hole. Fix the hole rather than the instance.
> 135. MIRROR REGISTRATION OF tiles.* — RATIFIED. A reading in one gitignored place with no
>      history and no witness is the gap 56(a) exists to close, and finding it as omission-
>      by-absence rather than by a failing check is the 101(a) shape. Excluding the
>      report-only siblings with the reason recorded in-line is correct. Witnessing addition
>      only; nothing recorded changed.
> 136. T12 FINDING 1 — C-11 NEEDS A PRODUCER, AND IT SITS AFTER THE GATE.
>      The contract owes the election OUTCOME with its scope; T9 produces the question and
>      stops. An outcome cannot be written before I rule, so the producer cannot live in T9.
>      (a) Add a post-gate task, blocked behind T9, whose sole job is to record the owner's
>          election outcome AND ITS SCOPE to a witnessed node and into the C1→2 contract.
>      (b) T9's AC states explicitly that presenting the presumptive rule with an empty
>          decision cell does NOT discharge C-11. Same correction as T11's Finding 1: the
>          deliverable is the reading, not the machinery that produces it.
>      (c) Stage 1 does not close with C-11 outstanding. Record that in the contract, so a
>          successor cannot read a presented question as an answered one.
> 137. T12 FINDING 5 — RATIFIED, one AC edit: T9's pack list gains a slot for the C1→2
>      coverage table beside T11's instrument table, as T12's AC already requires.
> 138. THE HEADING-ONLY SPOT-CHECK IS BLIND TO T13 AND T22. Tracker-only tasks read as
>      phantoms to T11's verification method. Fix the check to read the tracker as the
>      source of truth rather than the plan's headings — a verification tool that cannot see
>      a third of the recent tasks will mislead the next person who trusts it.
>
> SEQUENCE: 133 first — leg 2 is held on it. Then 136/137/138; 134 when convenient.
>
> STOP CONDITION: leg 2 does not launch until 133 resolves and I have ruled the basis. Legs
> 3-4 likewise. Nothing sealed. T5's remaining legs are the only Stage-1 critical path.

### What PART 34 changes

- **Leg 2 is held on a DIAGNOSIS, not on a number** (133). The basis change is not
  available until the mechanism is reported, and **option (a) — hold 8,730 — is refused
  outright** (133d): a 1.18× margin asserted as 2× is a margin that does not exist, and
  `MemAvailable` bottoming at 3,660 MiB means leg 1 ran closer to an OOM than the gate
  implied. Surviving is not evidence the gate worked.
- **If the retention is releasable, E-16 §2 stands unchanged** (133b) — 2 × the corrected
  peak, ~6,758 MiB on window 1's figure. **If it is genuinely unreleasable** (133c), the
  multiplier is re-derived from what the 2× was protecting against; **a margin picked to
  fit the box is not a margin.**
- **Acceptance for any fix is bit-identity of the assembled store** (133e), reusing pin
  121's harness — the same standard per-window persistence itself had to meet.
- **Pin 78's hole is the subject, not the instance** (134): if `seal_run`'s refusal set
  covers only sealed gates, unsealed measurements can extrapolate silently.
- **C-11 gains a post-gate producer** (136) behind T9, T9's AC states that presenting the
  question does not discharge the line, and **Stage 1 does not close with C-11
  outstanding** — recorded in the contract itself.
- **T12 Finding 5 ratified** (137) and **the heading-only spot-check is fixed to read the
  tracker** (138), because a verification tool blind to a third of the recent tasks
  misleads whoever trusts it next.


---

## PART 35 — PROJECTION-DECLARATION RULING (verbatim), pins 139–142, 2026-09-02

**Status: RECEIVED AND RECORDED VERBATIM 2026-09-02.** Turns the pin-134 audit into a
refusal, orders the eleven declared by forward-pointer amendment with spans per axis,
re-keys pin 42 on shape as instance seven, and sets two conditions on the re-measure.

> 139. PIN 134 — REFUSE NOW, DECLARE THE ELEVEN BY FORWARD-POINTER AMENDMENT.
>      (a) Option (a). The declaring is the point, not the refusal: eleven blocks make
>          projections whose spans nobody has stated, and the pin-89 probe proves what that
>          costs — a caveat on the wall axis, nothing on the RAM axis, and the RAM axis is
>          what broke. Expect to find that asymmetry again.
>      (b) NEVER A REWRITE. Forward-pointer amendments through the pin-64 index; no
>          witnessed node is edited.
>      (c) ⛔ THE DECLARATION MUST CARRY THE SPAN, NOT A FLAG. Refuse an
>          `extrapolation_declared: true` with no values. `measured_over` must state the
>          actual range and `application_range` the actual use. A boolean satisfies the
>          check without stating anything, which would make the fix an instance of the
>          defect it closes — the third time in this stage that risk has appeared inside a
>          remedy.
>      (d) Each of the eleven states its span PER AXIS. The pin-89 blocks are the model
>          case: one axis caveated, one silent, both extrapolated 1→9.
> 140. PIN 42 HAS NEVER FIRED — record it as instance seven and correct it the same way.
>      Zero blocks declare `kind: gate`; the reachability refusal has inspected nothing since
>      it was written. `kind` is additionally overloaded with domain vocabulary
>      (member-batch, poly, challenge-coarsen, free prose), so the discriminator collides
>      with the data.
>      (a) Re-key pin 42 on shape as 134 does — a block carrying threshold-like or
>          verdict-like fields is inspected whether or not it volunteers.
>      (b) Add to §7's instance list, authored by me, with the mechanism named: a schema
>          field that only inspects volunteers inspects nothing. That correction belongs in
>          the list precisely because I wrote the rule it breaks.
>      (c) Sweep what the re-keyed check catches and report before wiring any refusal — same
>          sequence as 134, and for the same reason.
> 141. THE 3-WINDOW RE-MEASURE IS THE GATE BASIS, and holding it at the same 8,730 MiB a leg
>      would is right — a measurement sneaking in under the gate to establish the gate is the
>      mistake one level down, and you saw it. Two conditions on the result:
>      (a) It must be the SOLVE path's peak, not the reassembly path's. The 1,235 MiB
>          reassembly figure is 133(e)'s acceptance and is not the gate basis.
>      (b) Report the per-window slope, not only the peak. A flat slope is the evidence the
>          retention is gone; a peak alone cannot distinguish "fixed" from "three windows
>          is not enough to show it."
> 142. RATIFIED: 133's mechanism and fix, including the streamed leg-store write — catching
>      that np.savez(**payload) would have restored the peak at the end while producing a
>      correct file is exactly the kind of thing that passes every test and defeats the
>      purpose. 135-138 as folded, and 138's eleven tracker-only tasks rather than two.
>
> SEQUENCE: 139, then 140(a)-(c). The re-measure runs when the box allows; leg 2 waits on it
> and on my basis ruling.
>
> STOP CONDITION: leg 2 held. Nothing sealed. If the re-measured slope is not flat, that is a
> finding and it comes to me before any basis ruling.

### What PART 35 changes

- **The pin-134 audit becomes a REFUSAL** (139a), and the eleven caught blocks are declared
  through the **pin-64 forward-pointer index — no witnessed node is edited** (139b).
- **A declaration must carry VALUES** (139c): `extrapolation_declared: true` with no span is
  refused, because a boolean satisfies a check without stating anything — the remedy
  becoming an instance of the defect, named as the third such risk in this stage.
- **Spans are stated PER AXIS** (139d). The pin-89 probe is the model case: wall caveated,
  RAM silent, both extrapolated 1→9, and RAM is the axis that broke.
- **Pin 42 is re-keyed on shape and recorded as instance SEVEN** (140), with the mechanism
  named by the owner: *a schema field that only inspects volunteers inspects nothing.*
  **Sweep and report before wiring any refusal** (140c).
- **The re-measure must report the SOLVE path's peak and the per-window SLOPE** (141) —
  1,235 MiB is 133(e)'s reassembly acceptance and is **not** the gate basis, and a peak
  alone cannot separate "fixed" from "three windows is too few to show it".
- **If the slope is not flat, that is a finding and it comes to the owner BEFORE any basis
  ruling.**


---

## PART 36 — CONSUMER-SIDE, INDEX-INTEGRITY AND TRIAGE RULING (verbatim), pins 143–149, 2026-09-02

**Status: RECEIVED AND RECORDED VERBATIM 2026-09-02.** Moves the projection question from
producers to CONSUMERS, orders an index-integrity audit of the amendment history, triages
the pin-140 sweep by citation, splits the re-measure into a slope test and a gate basis,
and ratifies the reconstruction and triage.

> 143. AUDIT THE CONSUMERS, NOT ONLY THE PRODUCERS — the blind spot is mine.
>      A projection is created where a measurement is USED, not where it is written. The
>      probe recorded a one-window peak honestly; the projection appeared when I ruled the
>      gate at 2× it for a nine-window leg. No field name at the recording site could have
>      caught that.
>      (a) Any THRESHOLD, GATE or BASIS field that cites a measurement must state, machine-
>          readably, the measurement's span and its own application span. E-16 §2's launch
>          gate is the first subject: basis, measured_over = 1 window, application_range = 9
>          windows, and leg 1's outcome beside it.
>      (b) Sweep for other thresholds derived from measurements and declare them the same
>          way. The 40 h per-leg ceiling is the obvious second (derived from 31.0 h, itself
>          a 1→9 extrapolation).
>      (c) Record in the audit node that a shape-keyed check reads what was written down and
>          cannot see a projection made in a ruling — you have already done this; keep it,
>          because it is the honest statement of the tool's reach.
> 144. ⛔ AUDIT WHETHER EARLIER POINTERS WERE LOST THE SAME WAY. A dict literal with
>      duplicate keys silently kept the later value, and the index's own regression check
>      could not see it. That failure mode has existed for as long as AMENDMENTS has been a
>      dict literal, so today's three may not be the first.
>      (a) Reconstruct the full pointer history from the AST across the index's git history
>          and compare against what each node's amendments should be. Report any earlier
>          collapse.
>      (b) If any is found, restore by appending — never by rewriting a witnessed node.
>      (c) This is the mechanism that makes append-only honest. A silent loss here is worse
>          than a wrong value, because a wrong value can be noticed.
> 145. 140's 33 BLOCKS — TRIAGE BY CITATION, not by branch.
>      (a) The 24 phase14 blocks: declare, as the eleven were.
>      (b) The 9 prior-phase blocks: triage by pin 58's boundary — does a standing Stage-1
>          claim cite it? The anchor gate's checks 2 and 4 are discharged by CITATION to
>          stage-0 and phase-13 records; if a cited gate could never have fired, that
>          citation is hollow and the block must be declared. Uncited prior-phase blocks are
>          recorded as found and left alone: those gates are closed and owner-signed, and
>          reopening them is scope growth into finished work.
>      (c) Report the triage before declaring anything, as with 140(c). I want to see which
>          of the nine are load-bearing.
> 146. EXEMPTIONS AND BOOKKEEPING.
>      (a) The declarations node's audit exemption is acceptable ONLY with the stricter rule
>          test-pinned, not described. An exemption plus a prose rule is how exemptions
>          become holes; you said as much, so make it mechanical.
>      (b) §7 discipline 11 states "Six instances to date" and enumerates seven, naming the
>          seventh inline. Fix the count, and derive it from the list rather than restating
>          it — a stated count that drifts from its own enumeration is a small instance of
>          the family the list exists to catalogue.
> 147. SPLIT 141's TWO QUESTIONS.
>      (a) SLOPE TEST, runs now: ≥4 windows at reduced m (m=25 is ample — a failed fix shows
>          ~283 MiB of accumulation against flat). This answers whether the retention is
>          gone, which is the scientific question and the one currently blocked on RAM for
>          no good reason.
>      (b) GATE BASIS, runs when the box opens: 3 windows at m=100, solve path, unchanged.
>          Production scale is required here because the number IS the basis — 143(a) will
>          make it declare its own span, so it must be measured over the span it is applied
>          to as nearly as affordable.
>      (c) Keep holding (b) at the same gate a leg would. Your reasoning stands: a
>          measurement admitted under a relaxed gate to establish that gate is the mistake
>          one level down.
>      (d) If (a) shows the slope is NOT flat, stop — (b) is pointless and the fix is
>          incomplete.
> 148. THE TWO GOLDEN-TILE BLOCKS DECLARE FIRST, ahead of the other 22. They are what anchor-
>      gate check 2 is discharged by citation to, and check 2 is one of the two CITED checks
>      holding up the identity chain. Expect reachability by outcome — the gates fired, 6.2×
>      and 4.1× over tolerance, which is why the bridge caveat exists. Record that as the
>      declaration's substance. If either turns out to be unfailable, that is a finding about
>      check 2 and it stops.
> 149. RATIFIED: 144's AST reconstruction and the repo-wide duplicate-key sweep; 145(c)'s
>      triage, including its correction of my branch-based framing — the boundary is
>      citation, as it has been every time it has been tested.
>
> SEQUENCE: commit the in-flight 139/140 work; land PART 36; run 147(a) immediately; then
> 148, then 145(a)/(b) for the remaining 22, then 146.
>
> STOP CONDITION: leg 2 held on 147(b) and my basis ruling. 147(d) and 148 each stop on
> their own.

### What PART 36 changes

- **The projection question moves to the CONSUMER** (143): a threshold that cites a
  measurement declares the measurement's span and its own application span. E-16 §2's
  launch gate is the first subject; the 40 h ceiling the second.
- **The amendment index gets an integrity audit across its whole history** (144), because a
  silent pointer loss is worse than a wrong value — a wrong value can be noticed.
- **The pin-140 sweep triages by CITATION, not branch** (145): uncited prior-phase gates are
  recorded and left alone; a cited gate that could never have fired makes the citation
  hollow and must be declared.
- **The exemption becomes mechanical** (146a) and **§7's instance count is derived from its
  own list** (146b).
- **The re-measure splits** (147): the slope test runs now at m=25 and answers whether the
  retention is gone; the gate basis waits for production-scale headroom, still held at the
  gate a leg would face. **A non-flat slope stops (b) outright.**
- **The two golden-tile blocks declare first** (148), and an unfailable one there is a
  finding about anchor-gate check 2.


---

## PART 37 — BASIS RE-PIN, EXCLUSION LOCK AND THE 140 REFUSAL (verbatim), pins 150–153, 2026-09-02

**Status: RECEIVED AND RECORDED VERBATIM 2026-09-02.** Re-pins E-16 §2 to 9,146 MiB,
orders an exclusion lock and in-run headroom sampling, turns the re-keyed pin-42 check
into a refusal, and ratifies the two measurements and the work around them.

> 150. E-16 §2 BASIS RE-PINNED TO 9,146 MiB = 2 × the measured 4,573.
>      (a) TIER2_MEASURED_PEAK_MIB becomes 4,573; the 4,365 one-window figure is superseded
>          with the prior value preserved, not overwritten.
>      (b) THE EXTRAPOLATION IS DECLARED, per 143(a): measured over 3 windows, applied to 9,
>          bounded by the flat-slope evidence rather than by an assumption of linearity.
>          Record beside it that leg 1's increments minus retention give per-window
>          working-set variation of −170 to +236 MiB, so a nine-window peak near ~4,809 is
>          consistent and 9,146 still covers it at 1.90×.
>      (c) LEG 2 CLOSES THE PROJECTION. It is a nine-window run at production scale: record
>          its boundary peaks and re-pin the basis from the direct measurement afterward.
>          After leg 2 this threshold stops being derived from a shorter run.
>      (d) I am NOT holding 8,730 at 1.909×. It is within a rounding error of the rule, and
>          that is exactly the kind of "close enough" that produced the 1.18× we just spent
>          two rounds unwinding. The rule says 2×; the measurement says 4,573; the threshold
>          is 9,146.
> 151. ⛔ THE GATE MEASURES THE BOX, NOT THE BOX'S FUTURE — your finding, and it needs a fix.
>      147(b) launched on a passing gate and then shared the box with 147(a) for 34 minutes.
>      Peak RSS is per-process so the basis survives, but nothing prevented a second
>      production-shaped job from arriving after the check.
>      (a) Take an exclusion lock at launch, held for the run's duration, refusing any second
>          Stage-1 solve while it is held. A gate that admits one job and then admits
>          another has not gated anything.
>      (b) Sample MemAvailable DURING the run, not only at launch, and record the minimum
>          beside the peak. Leg 1 bottomed at 3,660 MiB and we learned that afterward; it
>          should be a recorded field.
>      (c) This is why leg 1 survived at an asserted-2×-actual-1.18× gate: it happened to
>          have the box to itself. That was luck, not the gate working.
> 152. PIN 140's REFUSAL — REFUSE NOW, same shape as 139. The 24 phase14 blocks are declared
>      with pass condition, fail condition and outcome observed; the 9 uncited prior-phase
>      blocks are recorded as found with the citation test that cleared them and remain
>      visible in every sweep run. That is the right resting state, and leaving the re-keyed
>      check reporting would make it a check that cannot fail — in the pin whose entire
>      subject is checks that cannot fail.
> 153. RATIFIED: 147(a) and (b) as measured, including the boundary-versus-mid-solve
>      discrimination that makes them conclusive; 148 — check 2's citation holds, and
>      mu_scale_check's discriminator being an equality against an independent artifact is a
>      better two-sidedness argument than the one I offered; 145's 33 → 9; 143's three
>      consumers, including STAGE1_PCG_MAXITER which the sweep found on its own; 146; and
>      the append-only gate firing on your own edit, resolved by supersession with the prior
>      body preserved rather than by re-syncing.
>
> SEQUENCE: land 150-153; fold 150 and 151(a)/(b); then 152. Leg 2 launches when the box
> clears 9,146 with the exclusion lock held.
>
> STOP CONDITION: leg 2 runs to completion or stops at 40 h. Re-assess after it, per E-16 §4
> and 150(c).  Nothing sealed.

### What PART 37 changes

- **The launch gate is 9,146 MiB** (150): 2 × the measured 4,573, with the 4,365 one-window
  figure **superseded and preserved**, never overwritten. **8,730 at 1.909× is REFUSED**
  (150d) — "close enough" is what produced the 1.18×.
- **The remaining extrapolation is declared and bounded** (150b): 3 windows measured,
  9 applied, with leg-1 working-set variation of **−170 to +236 MiB** recorded, so a
  nine-window peak near **~4,809 MiB** is consistent and 9,146 covers it at **1.90×**.
- **Leg 2 CLOSES the projection** (150c): nine windows at production scale, boundary peaks
  recorded, and the basis re-pinned from the direct measurement afterward.
- **A gate that admits one job and then another has not gated anything** (151a): an
  exclusion lock is held for the run, and **MemAvailable is sampled DURING the run with its
  minimum recorded beside the peak** (151b). Leg 1's survival was the box being free, not
  the gate working (151c).
- **The re-keyed pin-42 check REFUSES** (152) — leaving it reporting would make it a check
  that cannot fail, inside the pin whose subject is checks that cannot fail.


---

## PART 38 — BANNER-STATE RULING (verbatim), pin 154, 2026-09-02

**Status: RECEIVED AND RECORDED VERBATIM 2026-09-02.** The progress banner had become a
stack of headline blocks whose top two contradicted each other.

> 154. THE BANNER'S TOP TWO ENTRIES CONTRADICT EACH OTHER. Line 89 reads "LEG 2 LAUNCHES AT
>      9,146 MiB"; line 211 still reads "LEG 2 IS HELD ON PIN 133 — peak re-measure QUEUED."
>      Both are prefixed as headline blocks. 133 is resolved, the re-measure is done, and the
>      basis is ruled — the second entry is stale and a fresh session reading top-down meets
>      a resolved hold presented as current.
>      (a) Retire or supersede line 211's block rather than leaving it under a newer one.
>      (b) The banner's current state should be one block, not a stack a reader has to date-
>          order. Same defect the closure map had when its header outlived its body, and the
>          same fix: rewrite what went stale rather than layering over it.

### What PART 38 changes

- **The banner is ONE current-state block** (154b). Everything older is demoted below it and
  marked as trail, so a top-down reader meets the current state once rather than a stack
  they must date-order.
- **Line 211's hold is retired** (154a): pin 133 is resolved, 147(a)/(b) are measured, and
  the basis is ruled at 9,146 MiB.
- **The rule, stated generally:** rewrite what went stale rather than layering over it. A
  headline block that outlives its body is the closure-map defect in another file.

---

## PART 39 — BASIS RE-PIN, THE IN-RUN WATCHDOG AND THE E-16 §4 RE-ASSESSMENT (verbatim), pins 155–158, 2026-09-04

**Status: RECEIVED AND RECORDED VERBATIM 2026-09-04.** Leg 2 (southern) closed the 3→9
projection by direct measurement, and in doing so surfaced that the launch gate measures a
box that does not stay measured.

> 155. RE-PIN THE BASIS TO THE DIRECT MEASUREMENT — mechanical, per 150(c).
>      TIER2_MEASURED_PEAK_MIB 4,573 → 4,951.16, nine windows at production scale, no
>      projection. The 4,573 figure is superseded with the prior value preserved, as 4,365
>      already is. Record that the 3→9 extrapolation came in at 1.083× — good to 8.3%,
>      which validates the method that produced it and is worth keeping for the next time
>      a short run has to stand in for a long one.
>      Threshold becomes 2 × 4,951 = 9,902 MiB. The rule says 2×; the measurement says
>      4,951. I am not holding 9,146 at 1.847× for the same reason I would not hold 8,730 at
>      1.909× — "close enough" is how the 1.18× survived two rounds.
> 156. ⛔ BUT THE LAUNCH GATE IS NOT WHAT PROTECTS THE LEG, and 155 must not be mistaken for
>      a fix. Re-derived: the box shed 9,389 MiB during leg 2 against a leg peak of 4,951.
>      No launch threshold covers that. The gate prevents starting into a bad box; it cannot
>      prevent the box going bad. Leg 2 survived by owner intervention, and that is not a
>      property the remaining legs can rely on.
>      (a) ADD AN IN-RUN HEADROOM WATCHDOG. Below a floor, the leg STOPS CLEANLY at the next
>          window boundary — not dies, not thrashes. Pin 121 makes this cheap: at most the
>          window in flight is lost, and the store carries the rest.
>          (i) Floor set from leg 2's own trace, not invented. It bottomed at 1,382 MiB with
>              VmSwap ~100 MiB and both clocks stalling ~10 min — that is the region where
>              the leg was already failing, so the floor sits above it with margin, and the
>              swap onset is the signal to key on as much as the absolute number.
>          (ii) Stop reason recorded in the row, distinguishable from a completion and from
>               a crash.
>      (b) THE PARKED LAUNCHER RELAUNCHES IT when the box recovers, resuming from the store.
>          The pause/resume path is 121's and is already bit-identity tested; do not build a
>          second one.
>      (c) SAMPLE AT A CADENCE THAT CAN SEE THE SQUEEZE. The 1-minute sampler caught 1,526
>          MiB while the in-run tracker recorded 1,382 — the row understated the true floor.
>          Reconcile the two so the recorded minimum is the real one.
>      (d) This is what 133(e)'s bounded-change discipline was for: persistence and stop
>          logic only, no change to the solve, the scoring, or the schema.
> 157. E-16 §4 RE-ASSESSMENT — LEGS 3 AND 4 AUTHORISED TOGETHER, CONDITIONAL ON 156(a).
>      (a) Wall is settled: 19.67 h and 27.48 h against the probe's 31.0 h prediction, mean
>          23.58 h, both well inside the 40 h ceiling. Two legs remain at ~47 h. The
>          extrapolation that made per-leg re-assessment necessary is now validated twice
>          over, so I am not re-assessing between legs 3 and 4.
>      (b) CONDITIONAL: the watchdog lands first. Without it each leg is a supervised event
>          requiring manual rescue, and I will not authorise two of those. With it, run them
>          back to back.
>      (c) The 40 h ceiling stands unchanged. Southern took 1.40× kuroshio; the remaining
>          tiles are not obviously worse, but the ceiling exists for the case where they are.
>      (d) Equatorial then quiet gyre, E-16 order, unchanged.
> 158. RATIFIED: leg 2 as recorded, the completion procedure run in full, PROGRESS rewritten
>      rather than layered per 154, and the three items recorded-not-adopted — the 1.847×
>      coverage, the 9,902 figure, and the observation that the gate measured a box that did
>      not stay measured. That last one is the finding of this round and you surfaced it
>      rather than reporting a clean leg.
>      Noting also that pin 26(b)'s raised cap earned itself again: 626 iterations on
>      w+00207's member batch, over the 500 a smaller cap would have imposed.
>
> SEQUENCE: land 155-158; fold 155; build 156; then legs 3 and 4 back to back.
>
> STOP CONDITION: leg 3 does not launch until 156(a) is landed and tested. Each leg still
> stops at 40 h. Nothing sealed; 18/19/20 remain halted; T6-T9 and task 23 unopened.

### What PART 39 changes

- **The basis is the DIRECT MEASUREMENT** (155). `TIER2_MEASURED_PEAK_MIB` becomes
  **4,951.16** from nine production windows; 4,573 joins 4,365 in the preserved-superseded
  set. The threshold becomes **9,902 MiB** — the rule says 2×, and 1.847× is refused for the
  same reason 1.909× was: *"close enough" is how the 1.18× survived two rounds.*
- **The 3→9 extrapolation is RECORDED AS VALIDATED at 1.083×** (155) — kept deliberately,
  as evidence about the *method*, for the next time a short run stands in for a long one.
- **⛔ 155 IS NOT A FIX, AND MUST NOT BE READ AS ONE** (156). The box shed **9,389 MiB**
  during leg 2 against a 4,951 MiB leg peak: **no launch threshold covers that.** A gate
  prevents starting into a bad box; it cannot prevent the box going bad.
- **The protection is an IN-RUN WATCHDOG** (156a): below a floor the leg **stops cleanly at
  the next window boundary** — not dies, not thrashes — and pin 121 caps the loss at the
  window in flight. The floor comes from **leg 2's own trace**, not invention, and **swap
  onset is a signal alongside the absolute number** (156a-i).
- **A clean stop is DISTINGUISHABLE from a completion and from a crash** in the row
  (156a-ii), the parked launcher **relaunches on recovery through pin 121's existing
  pause/resume path — no second one is built** (156b), and the **two headroom samplers are
  reconciled so the recorded minimum is the real one** (156c).
- **Bounded change, per 133(e)** (156d): persistence and stop logic only — no change to the
  solve, the scoring, or the schema.
- **Legs 3 and 4 are authorised TOGETHER** (157), **conditional on 156(a) landing first**
  (157b). Wall is settled at 19.67 h and 27.48 h against a 31.0 h prediction, so **there is
  no re-assessment between legs 3 and 4** (157a). The **40 h ceiling stands unchanged**
  (157c); equatorial then quiet gyre (157d).
- **Leg 2 is RATIFIED as recorded** (158), and the finding of the round is named: *the gate
  measured a box that did not stay measured.* Pin 26(b)'s raised cap earned itself again at
  626 iterations.
