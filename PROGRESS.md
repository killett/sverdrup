# Sverdrup — Progress notebook

> **▶ RESUME (if the user says "resume"):** active work is **Phase 5 — autotune loop**, **Stage-C
> REDESIGN IMPLEMENTED — awaiting owner sign-off on the Task-6 USER GATE.** Plan
> `docs/superpowers/plans/2026-07-01-stagec-redesign.md` Tasks 1–5 `completed` + committed
> (`45bb41f`, `a4a940f`, `ae9020b`, `299d268`, `52ed96e`); Task 6 (DoD user gate) code + evidence
> DONE; owner signed off with one condition — FIX the offline-skip gap first — which is now DONE.
> **Tuner-debt-cleanup plan (the two carried Task-14 follow-ups) COMPLETE 2026-07-01** — BO now
> genuinely multi-round (`rounds` threaded through the stage runners, `6e418fa`) + Stage-B gate skips
> instead of ERRORing on no-admissible (`d7376b8`). See the follow-ups block below.
> **▶ ACTIVE PLAN (2026-07-01) — Phase 6: FEM/triangulation SPDE (grid-agnosticism falsification).**
> Brainstormed + spec approved-with-fix + plan written. Design
> `docs/superpowers/specs/2026-07-01-phase6-fem-discretization-design.md`; plan + tracker
> `docs/superpowers/plans/2026-07-01-phase6-fem-discretization.md(.tasks.json)` (6 tasks, all `pending`).
> **The point is agnosticism, not FEM** — prove no hidden grid dependency by running the full pipeline on
> a maximally-irregular mesh vs dense linear-algebra ground truth. Headline probe already PASSED
> (`scripts/probe_fem_reduction_exactness.py`, committed): inherited Takahashi selective-inverse exact on
> FEM's irregular P1 pattern (diag rel-err 4.4e-10, 40/40 mesh-edge cov). The reduction-path claim rests on
> a mechanistic argument (`gmrf_linalg.py:27/96/135`); §3 #1 shipped test locks the number. Stationary κ only
> (per-node deferred); real OSSE/OSE deferred (ODC dead); C7 = mechanism demo vs the Neumann-edge grid
> baseline. **Next action = execute Phase 6 Task 1.** NOTE: commits `aa5812e`/`8ca6e03` are LOCAL-only —
> `git push origin main` blocked on SSH host-key verification (owner must `ssh-keyscan github.com >>
> ~/.ssh/known_hosts` then push).
> **Prior next action (Phase 5, still open) = owner reviews the both-tiers frontier
> (`docs/validation/phase5_feasibility_resolution_frontier.md`) for the deferred redesign decision.**
> What shipped: capability-conditional tile-count `CoherenceFeasibility`
> (`feasibility.py`, retires core/range≥25); Stage-C loop wiring `stage_c.py` (multi-tile joint
> barrier hard — scorer never called at n_tiles≥2); worst-case-localized reduction `coherence_gate.py`
> (strict-max adjacent-seam corr-err); both-tiers frontier `tuning/tradeoff.py` (joint region EMPTY,
> marginal SHIPS); concrete strict-xfail `test_acceptance_multi_tile_joint_feasible`; frontier doc.
> **Gate evidence:** full suite (no deselect) 296 passed / 9 skipped / 1 xfailed / 0 failed;
> typecheck+lint+pre-commit(--all-files) clean. **External-skip gap FIXED:** the 2 `@external`
> download tests (`test_download_dc2021a/dc2023`) used to fail on `httpx.ConnectTimeout` OFFLINE;
> new `tests/validation/_net.py::skip_if_unreachable` (short-timeout HEAD probe → `pytest.skip` on
> `httpx.TransportError`) now makes them SKIP offline per the marker's "skipped offline" contract,
> while still running + verifying when the mirror is reachable. **Coarse-correction / default-sampler stay
> owner-deferred** (§6), decoupled via `RelaxedCoherenceFeasibility`. Source of truth:
> `docs/superpowers/specs/2026-07-01-stagec-redesign-design.md`.
>
> **[superseded — kept for trail]** Next action WAS `writing-plans` to REWRITE Stage-C plan Tasks 15–18
> against the approved design; that plan was written (`docs/superpowers/plans/2026-07-01-stagec-redesign.md`,
> Tasks 1–6) and is now executed. The OLD Tasks 15–18 in the phase5 plan remain SUPERSEDED. Read, in
> order: (1) **`docs/superpowers/specs/2026-07-01-stagec-redesign-design.md`** (the approved design);
> (2) the **DECISION 1–5** blocks below (owner decisions + measurements); (3) `phase5_scope_spec.md`
> §5.2/§7 + the phase5 design doc §4/§11 (already amended to match).
> **Task 14 (Stage-B gate) SIGNED OFF ON SMOKE** — GMRF prior bug fixed (`6cce45b`), method-agnostic
> loop drives GMRF end-to-end, c2 acceptance `(µ,σ,λx)=(0.835,0.054,308)` via BO (BASELINE-µ-ish, ~2×
> coarser λx than OI). The conda item further below is a passive watch item, NOT the active task.

## STAGE-C REDESIGN BRIEF (read first — the consolidated handoff, 2026-06-30)

**Why Stage C is being redesigned.** Stage C (Tasks 15–18: global coherent sampler + `core/range≥25`
feasibility predicate + feasibility-vs-resolution frontier + a DoD that documents *"no operational-range
DUACS-class global coherent until redesign"*) was designed around a **phase boundary that turned out to be
mostly a GMRF prior-variance BUG** (`matern_precision` omitted the SPDE marginal-variance normalisation →
prior σ² ~10³× too large). Fixing it (`6cce45b`) and re-measuring on the operational `make_natl60` band
(`scripts/diag_crossseam.py`, buggy `6cce45b~1` vs fixed) showed the two things that motivated the whole
Phase-4 Stage-B saga are **bug artifacts, now gone**: conditioning collapse (eigmin 2.5e-7→2.19, cond
4.36e8→73) and the decisive **seam marginal collapse (tree-driver strict-min 1.9e-7→0.45 @2×2, 0.74 @3×3)**.
The default `GmrfTreeKrigingSolve` now HOLDS the marginal seam contract in the operational regime.

**What is now FALSE / SUSPECT — do not carry into the redesign without re-deriving:**
- the `core/range ≥ 25` tile-sizing constraint (`CoherenceFeasibility` in `application/tuning/feasibility.py`,
  Task 7) — it was the bug's artifact; the real constraint is different (below);
- the "conditioning floor monotone in eigmin" law, "deflation is dead", the "two antagonists are the same
  object" claim, and the "no operational-range coherent sampler until redesign" verdict;
- ALL Phase-4 Stage-B blocks further down titled "THE STRUCTURAL ANTAGONIST / THE SECOND ANTAGONIST /
  DEFLATION IS DEAD / THE PHASE BOUNDARY" — treat as BUG-CONTAMINATED (kept for trail; do not act on their
  conditioning/eigmin/deflation claims).

**The ONE real, non-artifact question the redesign must answer:** the *aggregate* joint cross-seam covariance
rel-err (tree driver vs dense reference) is **scale-INVARIANT under the fix** (0.20 @2×2 → 0.47 @3×3, same
before/after) and **worsens with tile count**. That is recovery-not-collapse (~80%/53%), a genuine tiling
effect. Stage-C-at-scale feasibility hinges on whether this aggregate error stays bounded as tiles → global,
NOT on conditioning. Quantify it: run `scripts/diag_crossseam.py` at larger tilings (4×4, 5×5, …) and see if
median/max rel-err plateaus or grows unbounded. THAT curve is the new feasibility frontier.

**Concretely for the next session:**
1. `/superpowers-extended-cc:brainstorm` a Stage-C redesign: reframe feasibility as "aggregate cross-seam cov
   rel-err ≤ tol at global tile-count", drop/replace `core/range≥25`, decide if the default tree driver is
   simply *good enough* (strict-min holds; aggregate ~0.2 at small counts) vs needs the overlapping-Schwarz /
   coarse-correction idea for large counts.
2. Amend `phase5_scope_spec.md` + the Phase-5 design doc + rewrite Tasks 15–18 in
   `docs/superpowers/plans/2026-06-28-phase5-autotune-loop.md` (+ its `.tasks.json`) against the new premise.
3. Re-derive whether `CoherenceFeasibility` should exist at all, or become a cross-seam-cov-rel-err predicate.
4. Tools on disk: `scripts/diag_crossseam.py` (cross-seam probe, buggy-vs-fixed via `git checkout 6cce45b~1
   -- src/sverdrup/methods/gmrf_grid.py`), `scripts/stage_b_gate_run.py` (`SVERDRUP_STAGE_B_SCOPE=dev|full`).

**Smaller carried-over follow-ups (from Task 14) — BOTH CLOSED 2026-07-01 (tuner-debt-cleanup plan,
`6e418fa`+`d7376b8`):** (a) BO is now genuinely multi-round — `rounds: int = 1` threads through
`_run_stage`/`run_stage_a`/`run_stage_b` → `tune`; the gate call site drives BO at R rounds of `n//R`
(equal total budget vs Sobol's 1×n). Loop-level test `tests/test_tuning_rounds.py` proves history
accumulates `[0,n,2n]`. (b) `tests/test_stage_b_gate.py` no longer ERRORS on smoke — `StageANoAdmissible`
is caught → `pytest.skip` with a full-year-scope diagnostic; the λx finite/≤1.25×-Sobol asserts stay for
the admissible path. Plan `docs/superpowers/plans/2026-07-01-tuner-debt-cleanup.md` (both tasks completed).

**Source docs (unchanged pointers):** scope `phase5_scope_spec.md`; design
`docs/superpowers/specs/2026-06-28-phase5-autotune-loop-design.md`; plan + tracker
`docs/superpowers/plans/2026-06-28-phase5-autotune-loop.md(.tasks.json)`.

## STAGE-C REDESIGN — owner decisions locked (2026-07-01 brainstorm, in progress)

Brainstorm running (`superpowers-extended-cc:brainstorming`). Two owner decisions locked; a metric
validation is IN FLIGHT before the DoD wording is finalized. Design doc not yet written.

**DECISION 1 — "coherent" = Option 1, CAPABILITY-SCOPED.** The Stage-C barrier is worst-seam JOINT
cross-seam covariance (the definitional purpose of the SAMPLES/COVARIANCE capability: valid cross-seam
gradients/transports). Gating on the marginal while joint is measured-broken = the false-green the
project fought (invariant 6). Capability-scope it (invariant 4):
- `SAMPLES/COVARIANCE` → feasible iff tile-count `N ≤ N*_joint(tol)` (worst-seam joint curve; small).
- `MARGINAL_VARIANCE` → SEPARATE capability, looser bound `N*_marg` (marginals hold but strict-min
  DRIFTS 0.51→0.34 with tile count — do NOT over-claim "holds everywhere"; verify N*_marg by the same
  tile-count extrapolation before shipping). THIS is the honest shippable global product — labeled
  `MARGINAL_VARIANCE`, not "coherent."
- `POINT` → unconstrained.
Reject Option 2's LABEL (marginal-only ≠ coherent). Reject Option 3 (build coarse-correction now:
violates §6, premature, AND unnecessary — the curve IS the owner's decision input for the deferred fix).

**DECISION 2 — predicate reframe + tolerance.** Replace `CoherenceFeasibility` (core/range≥25, refuted)
with a CAPABILITY-CONDITIONAL, TILE-COUNT-keyed predicate. Key on tile count N, NOT core/range (measured:
cores don't rescue it). Ship a DEFAULT `tol=0.5` → `N*_joint=9` (swappable, per the old "25 was
swappable" pattern), full curve surfaced. Reject no-default: the headline (global SAMPLES/COVARIANCE
infeasible) is TOLERANCE-INVARIANT — every candidate N*≤16 ≪ thousands of global tiles; tol is a REGIONAL
knob, not a global determinant. tol=0.5 (not 1.0) because: (a) its N*=9 sits on the CLEAN low-count curve,
robust to the metric artifact below; (b) rel-err≤1.0 admits 100%-off covariance = unusable, defeats the
capability's purpose.

**DECISION 3 — metric validation RESOLVED 2026-07-01 → Option 1 (empty region), both-tiers artifact.**
The fragile `edge_relerr = ‖emp−ref‖/‖ref block‖` block-max (0.46→2.58 with tile count) was inflated by a
NEAR-ZERO-DENOMINATOR artifact (far/thin-overlap node sets, true-cov≈0) + median-of-edge-maxes. Added a
robust metric `GateFixture.edge_seam_corr_err(s)` — per grid-ADJACENT seam node pair,
`|emp_cov−ref_cov|/√(σ_aσ_b)` (correlation-unit, never near-zero denom) — and re-ran the constant-core
sweep at **M=8000** with a **selection-controlled worst-of-K** (K=418 = smallest tiling's node-pair pool,
mean over 400 seeded subsamples), so "worst grew" means seams degraded, not that more pairs were sampled.
Result (node-pair pool, constant 4° core):

  tiles  marg   corr_med  corr_p95  corr_woK(K=418)
    4    0.498   0.015     0.232      1.105
    9    0.512   0.023     0.270      0.506
   16    0.434   0.031     0.344      0.823
   25    0.380   0.052     0.798      2.033
   36    0.342   0.070     0.427      2.108

VERDICT (matches owner's decision rule — 2×2 worst-case ≥1 → Option 1 unassailable):
- WORST-CASE (invariant-6 gate): `corr_woK` ≥ 1.0 at the SMALLEST tiling (2×2 = 1.105) AND grows ~2× to
  ~2.1 at 36 tiles. Selection-controlled + denoised → real, not a small-n fluke, not pure selection. So
  `SAMPLES/COVARIANCE` feasible region is **EMPTY** at operational range; `N*_joint` RETIRES as a number;
  predicate returns False for `SAMPLES/COVARIANCE` at any operational tiling until the owner-deferred fix.
- BULK (the redesign-input nuance, reported by the artifact, NOT gated): typical seam is EXCELLENT (median
  1.5%→7%), p95 good then crosses tol≈0.5 around N~16–20 (0.34@16 → 0.80@25). So the deficit is a SPARSE
  CATASTROPHIC TAIL (~0.24% of pairs at 2×2), not uniform mediocrity → the coarse-correction must rescue a
  few bad seam pairs, not fix a uniform ~50% deficit. Materially better input than the pre-denoise reading.
- SAMPLES/COVARIANCE has a THIRD symptom (owner-corrected mis-keying): `marginal_contract_ratios`
  (sample_var/reported_var, `_tree_gate.py:201`) strict-min drift 0.498→0.342 is coherent-SAMPLE
  UNDER-DISPERSION at seams — a SAMPLES/COVARIANCE symptom, NOT a MARGINAL_VARIANCE bound. Fold into the
  joint tier (3 symptoms: joint corr worst-case ≥1, sample under-dispersion, both grow with tile count).

**DECISION 4 — MARGINAL_VARIANCE bound MEASURED on the right quantity (2026-07-01).** Added
`GateFixture.marginal_accuracy_errs` (analytic, sampling-free): relative error of the blend's REPORTED
marginal variance `(Σwσ)²` vs dense-global `diag(Σ_g)` at seams — the MARGINAL_VARIANCE capability's actual
deliverable (NOT sample dispersion). `MARG_ONLY=1 python scripts/diag_crossseam.py`, constant 4° core:

  tiles  marg_med  marg_p95  marg_max
    4     0.008     0.055     0.069
    9     0.007     0.063     0.140
   16     0.008     0.069     0.130
   25     0.009     0.083     0.149
   36     0.010     0.070     0.132

Worst-case ~13–15%, **FLAT with tile count** (not growing) — opposite of the joint metric. So `N*_marg` is
effectively UNBOUNDED within the tested range (worst-case ~15% up to 36 tiles); MARGINAL_VARIANCE global
product genuinely ships. Confirms per-tile reported marginals with adequate halos are locally accurate.

**Frontier artifact carries BOTH tiers** (Option 3's content, as ARTIFACT not predicate): predicate gates
worst-case only (invariant 6); the owner-facing frontier reports the SAMPLES/COVARIANCE tier (worst-case
empty + 3 symptoms, ~2× growth) AND the MARGINAL_VARIANCE tier (worst-case ~15% flat → ships). Fix
owner-deferred (§6). tol=0.5 default stands but N*_joint=1 (region empty regardless of tol).

**PROVENANCE CAVEAT (carry into the DoD):** n_star_joint=1 / empty-region rests on ONE synthetic fixture
(4° core, 300 km range, 1° grid, M=8000, K-controlled). The CONCLUSION is physically robust (independent-core
tiling destroys cross-seam correlation, worsens with seams, cores don't help — confound killed), but exact
universality across ranges/densities is one-fixture-based. The swappable predicate (`joint_tol`,
`n_star_joint` named params) handles regime variation; state provenance honestly, don't imply universality.

**DECISION 5 — doc-review refinements (owner review 2026-07-01, APPROVED-after-fixes; folded into
`docs/superpowers/specs/2026-07-01-stagec-redesign-design.md`).** Added worst-of-K estimator std (script now
reports it): 2×2 **1.105±0.000** (K=full pool), 3×3 **0.506±0.079**, 4×4 **0.823±0.135** (5×5~2.03, 6×6~2.11
from the full run). Refinements:
- (1a/1c) The worst-of-K is NON-MONOTONE in N (2×2 > 3×3) and 3×3=0.506 clears tol=0.5 by only 0.006 ≪ its
  std 0.079 — **within noise**. So no tested multi-tile geometry is CLEARLY feasible, but the small-N
  exclusion is thin. LEAD the DoD with the ROBUST claim (GLOBAL infeasible: woK~2.0 by 25 tiles,
  extrapolates past any tol); present regional `n_star_joint=1` as the tol=0.5 point-estimate SHORTHAND with
  the non-monotone + thin-3×3-margin + estimator-std caveats.
- (1b) `feasible iff N≤n_star_joint` assumes monotone-in-N (data violates it) → valid ONLY as the tol=0.5
  empty-region shorthand; a loosened tol (>~0.51) makes feasibility NON-NESTED (3×3 passes, 2×2 fails) →
  needs an `N→worst-case` curve lookup, not a threshold. `RelaxedCoherenceFeasibility(n_star_joint=64)` is
  ILLUSTRATIVE of the fix mechanism, NOT measured.
- (2) MARGINAL_VARIANCE tier gets a named swappable `marg_tol` (default 0.20); `marg_worst_case≈0.15`
  MEASURED-FLAT constant. Ships iff `marg_tol ≥ ~0.15` (tile-count-independent by flatness). "Ships" is
  CONDITIONAL on accepting ~15% worst-case marginal error — visible in the predicate, not buried.
- (minor) Replace the retired core/range strict-xfail with a CONCRETE one: a SAMPLES/COVARIANCE product at
  N≥2 asserted feasible under default `CoherenceFeasibility()` — strict-xfail today, xpass once the deferred
  fix widens `n_star_joint`. Known-broken target pinned in code, not prose.
Structure/capability-scoping/measurement-split APPROVED as-is. Next: apply §7 doc amendments (scope §5.2/§7,
design §4/§11) + writing-plans for the T15–T18 rewrite.

**Stage-C rewrite scope (both decisions):** amend `phase5_scope_spec.md` §5.2/§7 + design doc §4/§11 +
rewrite plan Tasks 15–18 (+ `.tasks.json`). T15 hard-barrier MACHINERY (gate-before-solve) + T16 strict-min
reduction are SOUND — keep; only the predicate key/constant and T17 frontier artifact + T18 DoD reword.
`CoherenceFeasibility(core/range≥25)` + `RelaxedCoherenceFeasibility(min_ratio)` both DIE (core/range-keyed).
`test_core_authoritative_gate.py` strict-xfail (`test_acceptance_operational_cross_seam_covariance_recovered`)
is core/range-premised → rewrite around the tile-count frontier. Phase boundary STANDS for
SAMPLES/COVARIANCE but for the REAL reason (worst-seam joint accumulates with tile count), NOT conditioning
(that was the GMRF prior bug, fixed `6cce45b`). Drop the ★-block option-(b) "median-fidelity" framing
below — invariant-6-dirty.

## ★ MEASURED 2026-07-01 — the feasibility frontier: cross-seam covariance does NOT plateau; worst-seam grows with TILE COUNT (not core/range)

**The brief's ONE real question is now answered.** Extended `scripts/diag_crossseam.py` to two sweeps
and removed the confound the first sweep had (the `natl60_tiny` fixture domain is hardcoded 8°×8°, so
2×2→6×6 shrank tiles on a *fixed* grid — conflating tile-count with core/range collapsing toward
degenerate near-empty cores). SWEEP 2 grows the DOMAIN at a **constant 4° core** by windowing a growing
centered box out of a large synthetic obs fixture (`_write_big_obs`; obs-VALUE-independent because
`Q_post=Q_prior+HᵀR⁻¹H`, so only obs geometry/density matters — OSSE `_prepare` never touches the ref
grid, fixture is obs-only). `make_natl60` gained optional `source`/`lon_range`/`lat_range` overrides
(non-breaking). tree-kriging DEFAULT driver, dense-global reference, M=2000.

**SWEEP 2 — constant 4° core, domain grows (THE tiles→global frontier):**

| tiling | tiles | seams | marg strict-min | rel-err med | rel-err **max** |
|--------|-------|-------|-----------------|-------------|-----------------|
| 2×2    | 4     | 6     | 0.510           | 0.248       | 0.467           |
| 3×3    | 9     | 36    | 0.468           | 0.310       | 0.456           |
| 4×4    | 16    | 90    | 0.441           | 0.453       | 0.808           |
| 5×5    | 25    | 168   | 0.370           | 0.751       | **2.682**       |
| 6×6    | 36    | 273   | 0.342           | 0.429       | **2.247**       |

**VERDICT — cross-seam covariance does NOT plateau at a usable tolerance.** Median climbs 0.25→0.75 then
sits ~0.4–0.75; worst-seam **max grows past 2.0** (>200% err = worst seam fully decorrelated / wrong-sign)
for ≥25 tiles. Per the standing localized-metric rule (aggregates launder localized seam defects), MAX is
decisive → bare `GmrfTreeKrigingSolve` is **NOT good-enough at global scale** on cross-seam covariance.

**THE CONFOUND IS KILLED — and the answer holds without it.** Matched tile-count, SWEEP1 (shrunk core)
vs SWEEP2 (constant 4° core): 6×6 → max 2.177 @1.33° vs 2.247 @4.00°; 5×5 → 1.678 @1.60° vs 2.682 @4.00°.
**Tripling the core barely moved max rel-err** — worst-seam error is driven by TILE COUNT, not core/range.
So the growth is a genuine tiling breakdown, NOT a small-core artifact, and bigger cores do not rescue it.
(This also RETIRES the last hope that `core/range` sizing alone fixes Stage C — it does not.)

**Unchanged confirmations (both sweeps, both core sizes):** conditioning DEAD (eigmin flat 3.1–3.8, cond
55–66 — tiling-independent, it's the 1×1 global ref); marginal contract HOLDS (strict-min 0.34–0.74, never
collapses). **Honest caveat:** median is non-monotone (6×6 dips to 0.43) — M=2000 sampling noise + more
deep-interior seam pairs (true-cov≈0 → noisy rel-err) at high tile counts; MAX is the trustworthy metric.

**CONSEQUENCE FOR THE REDESIGN (the central fork for the brainstorm):** Stage-C operational global-coherent
needs EITHER (a) a coarse-correction / overlapping-Schwarz / global-low-rank-seam-basis path on top of the
tree driver, OR (b) a DoD that scopes "coherent" to marginal + median-fidelity (which the tree driver DOES
hold: strict-min never collapses, median bounded ~0.5) and explicitly EXCLUDES worst-seam joint covariance.
`CoherenceFeasibility` should become a cross-seam-cov-rel-err-vs-tile-count predicate, NOT `core/range≥25`.
Tooling committed: `scripts/diag_crossseam.py` (two sweeps, big-fixture generator), `make_natl60` overrides.

## ★★ RESOLVED 2026-06-30 — the GMRF prior fix (`6cce45b`) LARGELY DISSOLVES the Stage-B/C "phase boundary" (it was mostly a bug artifact)

**MEASURED both ways** (`scripts/diag_crossseam.py`, buggy=`6cce45b~1` vs fixed, `make_natl60` operational core/range<25 band):
- **Conditioning collapse = bug artifact, FIXED:** global `Q_post` eigmin **2.5e-7 → 2.19**, cond **4.36e8 → 73** (2×2).
- **Seam marginal collapse = bug artifact, FIXED (the decisive one):** tree-kriging-driver marginal-contract
  **strict-min 1.9e-7 → 0.451** (2×2) and **6.7e-7 → 0.738** (3×3). This 1e-7 collapse — seam over-pinning /
  under-dispersion — was THE core Stage-B defect that killed every prior sampler attempt and motivated the
  overwrite redesign, "deflation is dead", the conditioning-floor law, `core/range≥25`. It is a prior-scale
  BUG, not a structural boundary. (Median contract was ~1.0 in BOTH — the aggregate hid it; only strict-min
  exposed it, per the standing localized-metric rule.)
- **Aggregate cross-seam cov rel-err is scale-INVARIANT (unchanged): 0.20 (2×2) / 0.47 (3×3).** This is
  ~80%/53% recovery (recovery, not collapse) and is the SAME before/after — a real tiling effect that
  **worsens with tile count**. The DEFAULT tree driver was never as broken on the aggregate as OVERWRITE
  (which zeroes the seam by construction); the strict-min collapse was the real killer, and it's fixed.

**CONSEQUENCE — Stage-C (Task 15) premise is superseded:** "no operational-range DUACS-class global coherent
sampler until redesign" + the whole conditioning/deflation/`core/range≥25` framing were measured on the
10³×-too-weak prior. The default tree-kriging driver now HOLDS the marginal seam contract in the operational
band. **Remaining REAL (non-artifact) question for Stage-C-at-scale:** aggregate joint cross-seam covariance
accumulates error as tile count grows (0.20→0.47 for 4→9 tiles) — quantify whether that bounds global-coherent
feasibility, NOT the (now-refuted) near-singular-conditioning story. Re-plan Stage C against THIS, and treat
the Phase-4 Stage-B "THE PHASE BOUNDARY / DEFLATION IS DEAD / SECOND ANTAGONIST" blocks below as
BUG-CONTAMINATED (kept for trail; do not act on their conditioning claims).

### (original question, kept for trail) does the GMRF prior-variance fix (`6cce45b`) dissolve the Stage-B/C "phase boundary"?

**Raised + partially measured 2026-06-30.** The entire Phase-4 Stage-B saga (and the Stage-C
"no operational-range coherent sampler until redesign" phase-boundary verdict) was characterised on
the **buggy 10³×-too-weak prior**. The fix makes `Q_prior` ~2.5e5× stronger at operational range.
**MEASURED** (validation grid 52×51, 1-day nadir obs, fixed prior): `Q_post` eigmin **~1e-7 → ~10–50**,
cond **~4e8 → ~200–800** across range∈{100,200,405} km. So **antagonist #1 (the near-improper-mode
CONDITIONING collapse) is essentially an artifact of the bug** and is gone at correctly-scaled params.

**Therefore SUSPECT (all measured on the buggy prior — DO NOT trust without re-measuring):**
- the `core/range ≥ 25` tile-sizing constraint;
- the "conditioning floor is monotone in eigmin" law;
- "deflation is dead";
- the headline **"no operational-range DUACS-class global coherent sampler until redesign"** phase boundary.

**NOT YET MEASURED (the decisive next step):** does cross-seam COVARIANCE (antagonist #2) now recover
on the tiled `make_natl60` fixture with the fixed prior? PROGRESS argued the two antagonists are "the
same object" (correlation carried by the near-null mode) — if so, better conditioning relieves #2 too,
but that is a hypothesis. The clean probe: re-measure the `_tree_gate` cross-seam covariance vs a dense
reference (the third invariant) under the fixed prior, on the DEFAULT tree-kriging driver (NOT overwrite,
which zeroes the seam by construction so its strict-xfail won't flip from the prior fix alone).
**If cross-seam covariance recovers → the Phase-4/5 Stage-B/C phase boundary largely dissolves and
Stage-C global-coherent feasibility (Task 15) reopens.** This is a method-level reopening, not a Task-14
item — flag to owner before Stage C planning. Do NOT tear down the Stage-B conclusions on the eigmin
probe alone; measure the cross-seam covariance first.

- **Task-14 dev-confirm (12-day, post-fix) 2026-06-30 — GMRF NO LONGER DEGENERATE; near-admissible.**
  With `6cce45b`, GMRF scores real skill on the tuning scorer: Sobol mu up to **0.875** (was 0.0),
  real λx (129 km). BUT `StageANoAdmissible` on both Sobol+BO: no trial cleared `mu≥0.85` AND
  `coverage∈[0.583,0.783]` jointly. **Investigated the overdispersion (owner-asked): NOT a 2nd bug.**
  Coverage runs both over (idx1 τ=0.59→cov0.965; idx5 τ=0.98→cov0.969) AND under (idx8 τ=0.225,
  range101,taper27→cov0.384) with params — a variance-inflation bug can't underdisperse, so the UQ
  responds correctly. τ is the target marginal variance (signal ~0.025); high-mu trials used τ~0.6–1.0
  (20–40× signal→overdispersed). **Calibrated corner = idx2 (range618, τ0.058, taper3.3): mu 0.847,
  cov 0.719 ✓ — misses the mu bar by 0.003.** So: (a) search-density miss (more trials / BO warm-start
  near idx2 should clear), OR (b) GMRF's CALIBRATED mu tops ~0.847 = ≈BASELINE, marginally below OI's
  full-space-time-kernel 0.85+ (GMRF uses the weaker tapered-diagonal temporal likelihood — documented
  KnownBias). Legit method finding either way. Result JSON: `data/2021a_ssh_mapping_ose/ours/stage_b_gate_results.json`.
- **Task 14 (Stage-B gate) SIGNED OFF ON SMOKE by owner 2026-06-30.** The N=24 re-run: Sobol found NO
  admissible (frontier — every mu≥0.85 Sobol draw miscalibrated), but **BO (n=24) hit an admissible
  corner**: winner `range=702, variance=0.895, taper=3.47` → val mu 0.851 / cov 0.699 / λx 182.8 km →
  **c2 acceptance `(µ,σ,λx)=(0.835, 0.054, 308)`** (`their_eval` 0 in search / 1 at acceptance ✓).
  vs OI reproduced 0.853/0.090/140.9 and BASELINE 0.85/0.09/140: **GMRF µ 0.835 is BELOW BASELINE**,
  **λx 308 km ≈ 2× coarser than OI** — GMRF works but is weaker (tapered-diagonal temporal likelihood
  << OI's full space-time kernel). Note the **mu_score↔acceptance-µ gap**: winner val-mu 0.851 → c2-µ
  0.835 (internal track nrmse over-reads the vendored area-binned µ by ~0.016 on 12-day smoke).
  **KNOWN CAVEATS / FOLLOW-UPS (accepted at sign-off, not blockers):** (1) the committed pytest gate
  `tests/test_stage_b_gate.py` ERRORS on smoke because Sobol raises `StageANoAdmissible` (no admissible
  Sobol) — the gate evidence is the RUNNER, not that pytest; adjust the test (or only run it full-year)
  later. (2) BO in the runner is `rounds=1` + empty history ⇒ effectively random density, NOT guided
  TPE; it found the corner by luck. Making BO genuinely multi-round (thread `rounds` through
  `_run_stage`) is a real follow-up, and the gate's "BO ≤1.25× Sobol λx" criterion was vacuous here
  (Sobol had no admissible λx to compare).

## ⏳ PENDING ACTION — conda feedstock bump for v0.2.0 (do this when the PR appears)

**`sverdrup 0.2.0` was tagged + published to PyPI (2026-06-28).** The conda-forge
**autotick bot** watches PyPI and should open a feedstock **version-bump PR for
0.2.0** within ~a day. When that PR appears:

- **Drop `,<3.14`** from the `run:` python pin (→ `python >={{ python_min }}`) in
  the feedstock PR **and** mirror the same edit in `conda-recipe/meta.yaml`. This
  is now valid: **0.2.0 is the first `>=3.12` wheel on PyPI**, so the old `<3.14`
  cap (kept only to match the 0.1.0 wheel) is no longer needed.
- **No `requirements/run` dep changes** — the package deps
  (`numpy` / `scipy` / `pyproj`) are unchanged from 0.1.0. (The new
  `pyinterp`/`paramiko`/`httpx`/`stamina` are pixi-dev-only, not package deps.)
- Reminder (still applies): the recipe `test:` must check only the core import
  surface (`import sverdrup`, `pip check`) — never `python -m sverdrup`.

(Background detail lives in the "conda-forge distribution" section further down.)

---

## RESUME HERE (Phase 5 — autotune loop) — read this first
**Status:** Phase-5 build STARTED. Design approved + committed (`eabac5f`). Plan written + committed.
- Scope (source of truth): `phase5_scope_spec.md`.
- Design: `docs/superpowers/specs/2026-06-28-phase5-autotune-loop-design.md`.
- Plan: `docs/superpowers/plans/2026-06-28-phase5-autotune-loop.md` (tracker `.tasks.json` co-located).
- **Hard-gated sequencing:** Stage A (Tasks 1–11, OI single-tile, no constraint) →
  Stage B (Tasks 12–14, grid-GMRF + BO) → Stage C (Tasks 15–18, global coherent feasibility).
  Four user-gates: Task 11 (Stage-A DoD), Task 12 + Task 14 (Stage-B), Task 18 (Stage-C DoD).
- **STATUS (2026-06-29):** Tasks 1–13 implemented + committed. **Task 11 (Stage-A gate) SIGNED
  OFF by owner as-is (smoke).** **Task 12 (Stage-B method-agnosticism gate) CLOSED on
  method-agnosticism + degenerate-robustness** (see AC split below). **Task 13 (BayesianOptimization
  optuna-TPE SearchStrategy) DONE** (`8a5c842`: seeded, in-bounds, deterministic, drop-in into `tune()`;
  3 tests green). **Task 14 (USER GATE) code enablers DONE + committed (`516b937`); the multi-hour
  full-2017 GMRF-via-BO gate RUN is PAUSED** by owner (see the Task-14 block below). Next: the gate run.
  - **Stage-A smoke (12-day, n_trials=8):** winner `mu_score=0.869 (≥0.85)`, `coverage_1σ=0.755`,
    val `λx=143.8`; c2 acceptance `(µ,σ,λx)=(0.847,0.029,58.9)`; `their_eval` 0 search / 1
    acceptance. 12-day acceptance numbers are smoke artifacts (unstable λx 58.9; µ not the
    year-long BASELINE). Real sign-off (full-2017, multi-hour): set `validation_days`/
    `acceptance_days` to all 2017 in `tests/validation/fixtures/stage_a_scope.json`, run
    `SVERDRUP_STAGE_A_E2E=1 pixi run test tests/test_stage_a_end_to_end.py`.
  - **AC SPLIT (2026-06-29, owner-approved):** Task 12 carried "GMRF acceptance finite" which
    overlapped Task 14's "GMRF via BO winner + acceptance". Split: **Task 12 owns
    method-agnosticism (test 3 + same-loop, green) + degenerate-trial robustness**; **Task 14 owns
    the GMRF `(µ,σ,λx)` acceptance NUMBER.** Plan + tracker amended.
  - **Stage-B GMRF smoke = correctly-measured NEGATIVE result (NOT a failure):** all 8 GMRF Sobol
    trials + midpoint were degenerate (`UnresolvedScaleError` — map resolves no scale over the
    12-day box) → loud `NoAdmissibleTrial`. The robustness path (defined error → loop records
    feasible-but-unscorable → no crash → loud-at-result) is PROVEN on real data. `best mu_score=nan`
    is the empty-`feasible_scored` default, NOT a genuine GMRF nan (`leaderboard_nrmse` bounded;
    maps nan-free). Random Sobol is too weak for GMRF; BO + full-year is the path → **Task 14**.
  - **GMRF cost finding:** per-day GMRF marginal-variance selective inversion is the bottleneck
    (~56 min for the 12-day n_trials=8 smoke vs ~16 min OI). Relevant to Stage-C scaling.
  - **Carried into Task 14:** the mu_score-before-λx reorder (diagnostic) + verify GMRF µ magnitude
    finite once an admissible trial exists.
- **Phase-5 decisions folded into the design doc** (read §5.1, §6.2): (1) no `CoherenceMode` enum
  ever existed — collision test dropped; (2) λx scorer is the faithful daily-maps→interp→raw-j3-track
  path (NOT eval-point); (3) the Task-3 `eval_times` channel is SUPERSEDED on the tuner's λx path
  (raw track carries its own datetime64); (4) Stage A tunes the **Matérn** OI via `OI.parameter_space`
  with an EXPLICIT kernel built from params in BOTH search and acceptance (never `kernel=None` — it
  means opposite things in `OI.solve` vs `run_challenge_map`).
- **Task 14 (USER GATE — Stage-B GMRF-via-BO) — code enablers DONE + committed (`516b937`); gate RUN
  PAUSED by owner (2026-06-29).** Built + verified (18 passed / typecheck 189 / pre-commit clean):
  (1) drop-in `strategy: SearchStrategy | None` seam on `_run_stage`/`run_stage_a`/`run_stage_b`
  (defaults `SobolSearch`, accepts `BayesianOptimization`); (2) env-gated gate test
  `tests/test_stage_b_gate.py` (`SVERDRUP_STAGE_B_GATE=1`; asserts BO λx finite + ≤1.25× Sobol);
  (3) the carried-in **mu_score-before-λx reorder** as the pure, unit-tested `scorer._assemble_scores`
  — λx (expensive/fragile) is computed ONLY for trials with `mu_score >= mu_bar` (= objective's
  BASELINE bar), so a "GMRF maps but under-resolves" trial is recorded with its REAL µ instead of
  vanishing into `UnresolvedScaleError`. **nan-check RESOLVED:** `leaderboard_nrmse` is bounded
  `[0,1]`, so a *scored* µ is always finite — the only `nan` ever seen was the empty-`feasible_scored`
  `default=nan` (confirms the Task-12 reading; no guard needed).
- **★ GMRF PRIOR-VARIANCE BUG — found + fixed 2026-06-30 (`6cce45b`); load-bearing for all GMRF work.**
  Phase 5 was the first time GMRF ran the real challenge scorer (Phase 3/4 only validated the
  covariance *machinery* — Takahashi/selective-inverse exactness — never the physical marginal-variance
  scale). The first full-2017 Stage-B gate run showed `mu_score=0.0` on EVERY GMRF trial. Root cause
  (systematic-debugging, measured): `matern_precision` built `Q=(κ²I−Δ)²/τ` WITHOUT the SPDE
  marginal-variance normalization, so prior `σ²=τ·A_cell/(4πκ²) ∝ τ·range²` — ~10³× too large at
  operational range (O(100-1000) m² vs ~0.025 m² SLA signal). The over-loose prior couldn't regularize
  sparse-nadir interpolation: posterior mean FIT obs at observed points (in-sample resid ~0.09) but
  oscillated to **±300 m in the gaps**, where the held-out j3 track lives → zero skill, exactly 0.0.
  Fix: per-node normalization `Q=D⁻¹Q_raw D⁻¹`, `D⁻¹=√(v/τ)`, `v=A_cell/(4πκ²)` → `σ²≈τ`
  range-independent (what the docstring always claimed). **GOTCHAS for future GMRF work:** (1) the
  `sv/contract` seam ratio is scale-INVARIANT under the per-node normalization, so any test filtering
  on an ABSOLUTE variance threshold (e.g. the old `_tree_gate.py` `contract>10.0`, now scale-relative)
  will silently break — use scale-relative floors; (2) `variance`-space `[1e-3,1]` is now physically
  meaningful (σ²≈τ); pre-fix it could not reach a sane prior at any operational range; (3) GMRF mean
  field should be OI-scale (std ~0.2, ±1m) — if it's O(10) again, the normalization regressed.
  Diagnostic method that cracked it: single-day GMRF-vs-OI mean-field + IN-SAMPLE obs fit (fits obs but
  explodes in gaps ⇒ over-loose prior, not a units/assimilation bug). κ↔km units were RED-HERRING-clean.
- **Task 14 gate RUN — first attempt 2026-06-29 (owner "do it now") surfaced the bug above; KILLED + fixed.** Detached
  via `scripts/stage_b_gate_run.py` (`nohup … &`, PID in `data/2021a_ssh_mapping_ose/ours/stage_b_gate.pid`).
  Runner derives a **full-2017 scope** (days 0–364, `time 2017-01-01..2018-01-01`) IN-MEMORY from the
  12-day dev fixture (committed dev fixture left untouched), runs GMRF through the loop with **Sobol
  then BO** (n_trials=8, seed=1), and persists each `(µ,σ,λx)` row to
  `…/ours/stage_b_gate_results.json` the instant it completes (mid-run death keeps the finished
  strategy). Per-trial heartbeat → `…/ours/stage_b_gate.log`. Confirmed at launch: RSS ~41 MB
  (flat-memory analysis holds — peak RAM = single-day GMRF solve on the 52×51=2652-node grid, not the
  window; full-year adds only ~15 MB of day-stacked maps).
  - **DURABILITY CAVEAT:** detached process survives this AGENT session but NOT a container/host
    teardown. On resume, if `results.json` is absent/partial AND the PID is dead → **relaunch**:
    `nohup pixi run python scripts/stage_b_gate_run.py > data/2021a_ssh_mapping_ose/ours/stage_b_gate.log 2>&1 &`.
    The loop has NO per-trial checkpoint, so a death mid-strategy restarts THAT strategy from scratch
    (the other strategy's persisted row survives).
  - **Possible outcome = NEGATIVE:** GMRF may still be all-degenerate even at full-year (`StageANoAdmissible`
    captured into `results.json` with best-µ diagnostic, not a crash). If so, that is the real Stage-B
    finding (random/BO over this space can't clear the BASELINE µ floor on GMRF) → owner decision.
  - **On completion:** present both rows + gate verdict (`bo_finite_positive`, `bo_within_1p25x_sobol`)
    → owner sign-off → commit the runner + PROGRESS, close Task 14, proceed to Stage C (Task 15).
  - `scripts/stage_b_gate_run.py` is UNCOMMITTED (commit at gate close; the running process already
    loaded it). The pytest gate `tests/test_stage_b_gate.py` remains the formal artifact (env-gated).

---

## RESUME HERE (2026-06-27 — OI VALIDATION MILESTONE COMPLETE, gate 3 PASS) — read this first

**Status:** The "OI vs 2021a SSH-mapping OSE BASELINE" validation milestone is
**DONE — all 8 tasks committed, all 5 user-gates passed, final verdict PASS.**
Our hand-rolled OI (driven from `baseline_oi.ipynb`, faithful Gaussian
degree-space kernel + MDT reference frame) **reproduces the published BASELINE
leaderboard row**: ours **0.853 / 0.090 / 140.9** vs published **0.85 / 0.09 /
140** (µ tol ±0.03, never loosened). See `docs/validation/RESULT.md`.

- Plan: `docs/superpowers/plans/2026-06-27-oi-validation-2021a-ose.md` (tracker
  `.tasks.json` all `completed`). Canonical record: the audit trail
  `docs/validation/parameter_audit_trail.md` (every parameter, the eval recon,
  gate evidence, and the bugs found/fixed).
- New package `src/sverdrup/validation/` (config, access, their_eval, params,
  input_adapter, output_adapter, run, report). Challenge code vendored as a
  submodule `vendor/2021a_SSH_mapping_OSE` pinned to **v1.0 (`f5c6af8`)**.

### Load-bearing findings (live nowhere else — read before any follow-up)
- **Eval harness validated 3×:** their scoring (via `their_eval.score`, on
  modern pyinterp through faithful API-compat shims) reproduces DUACS/MIOST/BFN
  published rows to within tolerance. "Their eval is ground truth" is proven.
- **Data-source reality:** the ODC THREDDS (`tds.aviso.altimetry.fr`) is **dead**
  (unresolvable globally). The live unauthenticated source is the **MEOM mirror**
  (tracks + DUACS/MIOST/BFN/4dvarNet/neurost/convlstm maps, but **NOT** the
  BASELINE or DYMOST maps). AVISO **SFTP** (`ftp-access.aviso.altimetry.fr:2221`)
  has operational products + `auxiliary/mdt`, not the challenge maps. The literal
  BASELINE map is unobtainable → the sanity anchor is DUACS, and our own OI
  *generates* the BASELINE-equivalent map anyway.
- **Kernel:** the challenge BASELINE is Gaussian/anisotropic/degree-space, NOT
  our default Matérn-3/2/isotropic/km. Added `GaussianSpaceTimeDegrees` +
  a kernel-selection seam in `OptimalInterpolation.solve` (Matérn default
  untouched) — owner gate-1 decision (a).
- **MDT reference frame (the bug the decomposed read caught):** OI maps SLA;
  the eval compares SSH. `input_adapter.load_mdt_grid` grids the **mapping
  tracks' own** MDT (same CNES product as the withheld c2 track, ~1mm
  self-consistent — external CNES-CLS18 mismatched by ~5cm and was rejected);
  `run_year` adds it (`ssh = sla + mdt`). Without it µ collapsed 0.85→0.21.
- **Methods inventory** for "what to implement next" lives in
  `docs/validation/methods_and_data_inventory.md` (all 8 methods, published vs
  reproduced scores, per-method notes). Downloaded challenge data (~1GB) is
  under `data/2021a_ssh_mapping_ose/` (git-ignored).

### Next action
Milestone complete. Optional follow-ups (owner's call): implement MIOST
(multiscale OI) or a DUACS-tuned variant next (maps on disk as targets); the
Phase-4 Stage-B coherent-sampler work below is unrelated and remains where it was.

---

## RESUME HERE (2026-06-27 — STAGE-B PHASE BOUNDARY REACHED; overwrite landed non-default) — read this first

**Status:** Phase 4 Stage B is CLOSED-OUT-AT-A-PHASE-BOUNDARY, not "done" and not "blocked". The
overwrite redesign was planned, executed, and its certification probe PROVED a phase boundary: there
is **NO correct sparse-precision coherent sampler for the operational range**. Overwrite
(`GmrfCoreAuthoritativeSolve`) is correct only at core/range ≳ 25 (short range); the tree driver
collapses the marginal. Both candidate defaults are known-broken, differently. Disposition shipped:
**overwrite landed as a documented NON-DEFAULT reference; the `sparse-precision` default STAYS
`GmrfTreeKrigingSolve`; the default-sampler choice is DEFERRED to Phase 5.** The real fix
(decomposition redesign: cores≫range / overlapping-Schwarz+coarse / global low-rank seam basis) is a
**Phase-5 milestone** — it depends on the tuner's chosen range, so designing it now is designing
against an unknown (the junction-tree premature-build error again). Do NOT start it here.

### What the arc proved (full record below in "THE SECOND ANTAGONIST" + "DEFLATION IS DEAD")
- **Two antagonists pull OPPOSITE ways on the range axis.** SHORT range: near-improper mode breaks
  per-tile CONDITIONING (eigmin→0, the original Stage-B saga). LONG range: correlation length spans
  the tile boundary, so independent cores destroy cross-seam COVARIANCE (overwrite's zero). They are
  the SAME object (the near-null mode IS the cross-seam correlation carrier), so no per-tile seam
  construction fixes both ends.
- **Gate THREE invariants at the seam, not two:** (1) marginal contract, (2) direction strict-min,
  (3) cross-seam COVARIANCE vs a dense reference. (3) is decisive and was previously unmeasured —
  direction PASSES at long range while the covariance is destroyed (the masking the median once did).
- **Near-null deflation is DEAD** (probed adversarially to kill it): the cross-seam correlation is
  carried entirely by the near-improper modes; deflating them to make the solve well-posed installs
  ZERO cross-seam covariance (worst-pair ratio −0.000 across 400/200/150 km). Proven, not argued.

### Exact git state (this session)
- Task 1 committed `d173561` (ownership map + `_tree_gate` import repair; removed dead untracked
  `test_tree_kriging_gate.py`). Disp-A `64a2b32` (`GmrfCoreAuthoritativeSolve` non-default reference +
  `make_grid_diagonal` production fixture + `sigma_contract`/`marginal_contract_ratios`). Disp-B
  `006aa7a` (`tests/test_core_authoritative_gate.py`: ownership + marginal-fix + case-(b)
  boundary-characterization (green) + acceptance (strict xfail)). Disp-C = this PROGRESS/tracker
  commit. Registry default UNCHANGED from HEAD (`GmrfTreeKrigingSolve`).
- `test_gmrf_blend.py` is GREEN (it exercises the tree-driver default on the 1-D chain, the validated
  regime). It is NOT the case-(b) gate — that is the explicit overwrite-on-production test in
  `test_core_authoritative_gate.py`.

### THE PHASE-5 HANDOFF (the deliverable — do not re-derive this arc)
- **Constraint:** overwrite's zero-seam is acceptable only for core-size/range ≳ 25 (measured: true
  seam corr 0.68@400km → 0.08@50km for 12° cores). The Phase-5 tuner must treat cross-seam coherence
  as a CONSTRAINT on tile-size-vs-range, not a free variable.
- **Acceptance test already on disk:** `test_core_authoritative_gate.py::
  test_acceptance_operational_cross_seam_covariance_recovered` (strict xfail). The Phase-5
  decomposition fix must make it xpass (recover operational cross-seam covariance at the worst pair).
- **Open decision parked for Phase 5:** which `sparse-precision` default sampler to register, and the
  decomposition redesign scope (separate milestone conversation when Phase 5 starts).

### The original plan's Tasks 2–6 are SUPERSEDED by this disposition
`docs/superpowers/plans/2026-06-27-stageb-core-authoritative-sampler.md` Tasks 2 (repoint registry),
4 (range-sweep cert as a pass/fail user-gate expecting case a), 5, 6 (retire tree machinery) are
superseded: case (b) was proven, the registry default is NOT repointed, and the tree machinery STAYS
(it is the deferred default). Tasks 1 + the (rewritten) Disp-A/B/C are the executed reality.

## RESUME HERE (Stage B — CORRECTED after a 7-investigation diagnosis) — SUPERSEDED 2026-06-27 by the phase-boundary block above; kept for the trail

**Status:** Phase 4 Stage B coherent sampler is BLOCKED on a CONFIRMED, LOCALIZED defect whose
mechanism is now MEASURED. `src/sverdrup/distributions/coherent.py` is reverted to the committed
max-overlap MST; nothing committed this session. The fix is NOT yet applied (fix-locus just resolved
to the sampler; owner to confirm direction). **The prior-session RESUME block further down is
SUPERSEDED** — its causal model (sibling-seams / min-ecc star / depth) was refuted by measurement;
do not act on it.

### Exact git state
- HEAD = `eb3d15c`. `coherent.py` RESTORED to committed MST (the dirty min-ecc→star change was
  discarded — it was a measured regression, see §1).
- Working tree dirty (uncommitted): `PROGRESS.md`, the spec doc, `tests/unit/_tree_gate.py`
  (import-broken — still imports `_min_eccentricity_spanning_tree`/`_condition_root_scores`, now
  removed from coherent.py; to be reworked), untracked `tests/test_tree_kriging_gate.py`.

### 1. CONSTRUCTION — star reverted, MST restored, UNCERTIFIED
- The dirty `_min_eccentricity_spanning_tree` (star) was a measured REGRESSION: it manufactured the
  0.565/0.605 "sibling collapse" on the 1-D 3-tile (the star's dropped SIBLING edge; median 1.000
  laundered it). The committed max-overlap MST builds a sibling-free PATH on 1-D (that edge = 0.905).
  Reverted to MST.
- Construction is UNCERTIFIED, NOT "Stage-B done". The gate fixtures `make_natl60(2,2)/(3,3)` are
  DEGENERATE COMPLETE GRAPHS (K4/K9): every tile shares a reach-spanning overlap with every other
  (8° domain, ~3° halo). Measured: a 2×2 is structurally K4 (even at 12° tiles); the production
  regime at corr_len=300 is grid+DIAGONALS (maxdeg ~5–8), NOT grid-4-neighbour — clean grid adjacency
  appears only at corr_len ≲ 100 km. The prior "BFS-adjacency / L-path / no-sibling" reasoning
  silently assumed grid-4-neighbour and is a no-op on a complete graph (BFS = star). Certification
  needs a PRODUCTION-REPRESENTATIVE fixture (more tiles, large-vs-halo → grid+diagonal adjacency).

### 2. RULE (i) / strict-min — survived an adversarial multi-turn test
- median, p25, AND a physical near-null exclusion were each proposed and each shown by measurement to
  LAUNDER a real seam-node contract violation that strict-min catches. STANDING RULE (sharp form):
  coherence conservative-direction is gated by STRICT-MIN over physical seam pairs — no median, no
  percentile, no aggregate — because the defects are localized and every aggregate tested laundered a
  real one.
- The gate's median direction metric (`_tree_gate.py::edge_dir_ratio` returns `np.median`) is a
  CONFIRMED BUG → must become strict-min. The recorded Stage-B gate evidence **"dir 1.012 PASSED" is
  ANTI-EVIDENCE** (the median laundered the collapse) — struck; do not trust it.

### 3. METHOD LESSON — the analysis oscillation (load-bearing for future sessions)
- The defect's apparent magnitude swung "1e6× sampler collapse" → "no defect, reference artifact" →
  "real contract violation" across turns, because intermediate measurements compared the blend
  against a CHOSEN reference (max-over-tiles exact variance) that was misattributed — it picked a
  low-weight HALO tile's near-improper variance as the node's "exact" variance. STANDING METHOD RULE:
  **when a defect's magnitude depends on which reference you pick, the reference is the bug in the
  analysis** — measure against the INVARIANT the artifact promises about itself (here: the blend's
  OWN reported `(Σwσ)²` marginal contract), not an external quantity. That test resolved the
  three-turn oscillation in one shot.

### 4. CONFIRMED PHENOMENON + fix locus (mechanism measured; fix NOT yet applied)
- At ~16% of 2-D seam nodes, the coherent blend SAMPLE variance falls up to 7 orders BELOW its own
  reported `(Σwσ)²` marginal — a real conservative-contract violation (sample ≪ reported σ),
  localized to the seam, invisible to median/p25, caught by strict-min.
- Per-tile unconditional samplers are individually HEALTHY (each matches its own exact marginal:
  uncond/exact median ~0.99, min ~0.84, zero nodes <0.5). Crossfade weights are sound (sum to 1).
- **FIX LOCUS = THE SAMPLER (hand-forward over-pins).** PROBE B (decisive): blend seam variance
  WITHOUT the kriging correction = 0.91× contract (fine); WITH correction = 2.3e-6× contract
  (collapsed) — the hand-forward conditioning IS the collapse. PROBE A: at the collapsed nodes the
  AUTHORITATIVE (core, high-weight) tiles are the NEAR-IMPROPER ones (σ~280); the well-determined
  σ~0.11 tiles see the node only in their HALO. The conditioning chain pins the authoritative
  near-improper tiles to an over-confident HALO tile's draw → seam dispersion collapses below the
  (correct) reported marginal. Reported `Σwσ` is CORRECT (matches authoritative core tiles + global).
  NOT malformed weights, NOT mis-reported marginal, NOT junction-tree (per-tile-disagreement +
  pinning, not cycle-exactness).
- ROOT CAUSE (physical): small halo tiles cannot support the domain-spanning near-null mode → they
  are artificially confident at seam nodes the core/global find near-improper; the hand-forward
  propagates that halo over-confidence into the authoritative tiles.

### Exact next action
**Design APPROVED + committed:** `docs/superpowers/specs/2026-06-27-stageb-seam-overpinning-fix-design.md`
— per-node **core-authoritative two-pass** coherent sampler (`GmrfCoreAuthoritativeSolve`), **OVERWRITE
leading** (halo node ← owning core's actual draw; no `Σ_ss` solve; measured: marginal strict-min 0.881
vs the MST's 1.76e-7). The spanning-tree machinery dissolves. Certification is a **`range` sweep on a
production-representative (grid+diagonal) fixture** under strict-min (NOT a single pass) — distinguishes
case (a) overwrite-sufficient from case (b) core-mode-disagreement/reconciliation (which is not cheap;
possible phase-boundary). Overwrite cleanliness gate = compute every cross-seam derived quantity from
BOTH adjacent tiles and assert agreement. eigmin machinery retirement DEFERRED until the sweep rules
out (b). **Next: writing-plans → implementation plan (holds for owner approval before any code).**
**IN-PROGRESS, not a closed gate.**

### THE STRUCTURAL ANTAGONIST (organizing fact of the whole Stage-B arc — first-class method constraint)
The **near-improper global SPDE mode** (sparse nadir obs leave the `(κ²−Δ)²` low-frequency mode
under-determined ⇒ global `Q_post` eigmin ~1e-7) is the **structural antagonist of the tiled-GMRF
approach**: it is a *domain-spanning* mode with **no local representation**, so **every per-tile
operation misjudges it.** It has now produced **three distinct failures**, one disease:
1. the **synthesized strip-field sampler** (376×) — the strip sub-GMRF couldn't represent the global
   mode (error 90% in the complement of the near-null subspace);
2. the **conditioning floor** (residual monotone in eigmin) — conditioning a tile with eigmin~2.5e-7
   onto anything is ill-posed;
3. the **halo over-confidence / seam collapse** (this turn) — small halo tiles can't support the
   mode ⇒ spuriously confident ⇒ the hand-forward propagates that into authoritative tiles.

**Tiling and a near-null global mode are in fundamental tension.** This is a **boundary-of-validity
constraint on the method**, not a Stage-B closeout note. **Phase 5 drives `range` DOWN → the mode is
MORE improper → the tension is WORSE**; the autotuner must treat cross-seam coherence residual as a
CONSTRAINT, not a free variable. Any future per-tile coherent-sampler work must enter expecting this
mode to be the adversary and gate the joint/contract behavior at the seam (strict-min), never an
aggregate.

### THE SECOND ANTAGONIST — long-range cross-seam covariance (measured 2026-06-27; reframes the phase)
The overwrite sampler probe surfaced a SECOND structural antagonist that pulls OPPOSITE to the first
across the range axis. The two together mean **no single per-tile construction is correct across the
operational range band.** This is a method-level finding, not a Stage-B detail.

- **Antagonist 1 (SHORT range): near-improper global mode breaks per-tile CONDITIONING.** eigmin→0,
  `cond(Σ_ss)`→4e8, the whole Stage-B saga above. Worse as range ↓.
- **Antagonist 2 (LONG range): correlation length spans the tile boundary, so INDEPENDENT cores
  destroy real cross-seam COVARIANCE.** Overwrite makes adjacent cross-core-boundary nodes
  independent BY CONSTRUCTION (per-tile Pass-1 draws), so it reports cross-seam correlation as ZERO
  regardless of the truth. Worse as range ↑.

**Measured (production grid+diagonal 3×3 fixture, dense-global reference, overwrite driver):**
Overwrite fixes the MARGINAL (strict-min 0.63–0.84 across [400,200,100,50] km, collapse gone) but
zeroes the seam correlation at every range (blend corr ≈ 0). True seam corr is range-dependent:
+0.684 @ 400, +0.515 @ 200, +0.247 @ 100, +0.080 @ 50 km. So overwrite is CORRECT only at short
range (true corr ≈ 0 ⇒ a-real); at operational 200–400 km it destroys 0.5–0.68 real correlation
(case b). **DIRECTION-strict-min ALONE MISSES THIS** — it PASSES at 400/200 (0.967/0.920 ≥ 0.9)
because zero-correlation is conservative for the GRADIENT; only the third invariant (cross-seam
COVARIANCE vs dense ref) sees the destruction. **Gate THREE invariants at the seam, not two:**
(1) marginal contract, (2) direction strict-min, (3) cross-seam covariance/correlation vs a dense
reference. (3) is decisive and was previously unmeasured.

**Decisive local-vs-global probe (is the deficit the global mode or a local property?):**
- (a) **The cross-seam correlation deficit is LOCAL/high-frequency, NOT the global mode.** True
  cross-seam corr decays below 1/e within **1°** of the boundary and is **exactly 0.000** for deep
  interiors (measured at 400 & 200 km). A boundary strip ~1–2 nodes wide carries essentially all of
  it. §4's "expensive global, no spectral gap" pessimism was about the WRONG object.
- (b) **But the strip `Σ_ss` solve is globally contaminated → ill-posed at LONG range.**
  `cond(Σ_ss)` of the per-tile shared-strip block = 4.8e9 @ 400, 6.3e8 @ 200, well-posed (~2.7) by
  100 km; at 50 km the strips VANISH (halo < 2 nodes). The near-null low-frequency mode leaks into
  even a 2-node strip block, so naive strip value-conditioning reignites the 4e8 collapse exactly
  where the deficit is largest.

**[PRE-KILL HYPOTHESIS — this "deflation could work" opening was KILLED by the DEFLATION IS DEAD block
immediately below; kept for the trail of what was tried and why it failed. Do NOT act on it.]**
**The refined bind (for whoever designs the seam fix):** the thing to install is LOCAL (a), but the
obvious operator to install it (`Σ_ss` solve) is GLOBALLY contaminated (b). The opening: the target
lives in the near-null COMPLEMENT (deficit is high-frequency per (a); §4 measured 90% of the
joint-cov error in the complement of the bottom-k near-null subspace). A coupling that installs the
seam correlation in the high-frequency band only — **deflating the near-null mode out of `Σ_ss`
before conditioning** — could carry the local correlation while never exciting the 4.8e9 direction.
That is a bounded, range-adaptive construction, far cheaper than global reconciliation. The geometry
hands off cleanly: short range → overwrite (correct, strips vanish anyway); long range →
near-null-deflated local strip coupling. The plan's overwrite Task 3–5 as written cannot certify
this (they gate ≤ 2 invariants). Tiny-fixture cross-seam reds in `test_gmrf_blend.py` are CORRECT —
they are the small-core / long-corr-length = case-b regime, now explained.

**DEFLATION IS DEAD — and the kill PROVES the phase boundary (measured 2026-06-27, adversarial probe).**
The elegant "deflate the near-null mode out of `Σ_ss`, condition in the complement" reconciliation was
probed to KILL it (elegant-and-reconciling has been the signature of wrong all arc). Two measurements:
- **(1) `Σ_ss` spectrum.** A ×3e7 gap exists, but it is the OBS-vs-PRIOR gap: ~k tiny obs-pinned modes
  (λ≈1e-3 = obs noise floor) | gap | a high-variance near-improper CONTINUUM (λ 8e4→4.8e6, ratios
  ~1.0–1.5, the near-null global mode is its top, NO internal gap). "Deflate k near-null" leaves the
  continuum behind; to reach well-posed you must project out the ENTIRE high-variance bulk and keep
  only the ~8 obs-pinned modes.
- **(2) correctness — DECISIVE.** Strip S is a Markov separator (anchor: FULL inverse reconstructs the
  true cross-seam cov to ~1e-9). But conditioning in the well-determined complement (deflating the
  high-variance bulk) installs `cov_defl/true` strict-min = **−0.000 at 400/200/150 km, −0.141 at
  100 km** (true ≈ +88…+721 → defl ≈ 0). The cross-seam correlation is carried ENTIRELY by the
  near-improper modes deflation removes. Fails across the WHOLE operational band; (3)/handoff moot.

**The two antagonists are the SAME object.** The cross-seam correlation is LOCAL in space but
LOW-FREQUENCY in spectrum — adjacent nodes correlate because they share the smooth large-scale
(near-null) modes, so the correlation's CARRIER *is* the near-null mode. The mode that breaks per-tile
CONDITIONING at short range IS the cross-seam CORRELATION CARRIER at long range. You cannot deflate it
to stabilize the solve without deleting the correlation; full inversion installs it but is the 4e8
ill-posed solve that collapses the sampler on inconsistent residuals. **No separation exists.**

**THE GENUINE PHASE BOUNDARY (proven, not argued).** Tiling a field whose cross-seam correlation is
carried by the near-improper global mode is the WRONG DECOMPOSITION. Overwrite's zero-seam is correct
ONLY where the true boundary correlation is genuinely ~0 — i.e. core-size/range large enough (measured:
true seam corr 0.68@400 → 0.08@50 km for 12° cores ⇒ core/range ≳ ~25). This is a **Phase-5
tile-sizing-vs-range constraint, NOT a seam patch.** No per-tile seam construction recovers the
correlation in the operational band; the fix is the tiling geometry (cores ≫ range) or a different
(non-tiled / overlapping-Schwarz-with-coarse-correction / global-low-rank-seam-basis) decomposition.
**OWNER DECISION — MADE + SHIPPED 2026-06-27 (commits `d173561`, `64a2b32`, `006aa7a`, `ea96f08`):**
overwrite landed as a documented NON-DEFAULT short-range reference; the `sparse-precision` default
STAYS `GmrfTreeKrigingSolve`; the default-sampler choice + the decomposition redesign are a Phase-5
milestone (designing it now = designing against the tuner's unknown range — the junction-tree
premature-build error). The case-(b) finding is pinned on disk by
`test_core_authoritative_gate.py::test_case_b_boundary_characterization` (green characterization) and
`::test_acceptance_operational_cross_seam_covariance_recovered` (strict xfail the Phase-5 fix must
flip to xpass). **Correction to the mid-investigation note above:** the `test_gmrf_blend.py`
cross-seam tests are NOT red in the shipped state — they exercise the tree-driver DEFAULT on the 1-D
chain (the validated regime) and are GREEN; the case-(b) acceptance lives in the explicit
overwrite-on-production test, not there.

---

## SUPERSEDED — prior-session RESUME block (kept for the trail; DO NOT act on it). Its sibling-seam / min-ecc-star / depth causal model was refuted by measurement — see the CORRECTED block above.

## RESUME HERE (Stage B, mid-diagnosis) — read this first

**Status:** Phase 4 Stage A DONE + gated. Stage B sampler redesign (spanning-tree hand-forward) is
implemented and ~90% validated, but **blocked on ONE measured defect with a known fix not yet
applied**. Do NOT resurrect any prior approach; do NOT re-run the whole diagnosis — the decision is
made, only the final tree-construction tweak + its measurement remain.

### Exact git state (verify before touching anything)
- **HEAD = `eb3d15c`** (`test(phase4): Stage-B spanning-tree oracles …`). **Tasks 1–8 are committed
  and green** at this commit. The committed driver `GmrfTreeKrigingSolve` uses the **max-overlap
  Kruskal MST** (`_max_overlap_spanning_tree`) — that committed state passes `tests/test_gmrf_blend.py`.
- **Working tree is DIRTY** (uncommitted Stage-B-gate work — the live diagnosis):
  - `M src/sverdrup/distributions/coherent.py` — added `_min_eccentricity_spanning_tree`,
    `_posterior_eigmin`, `_condition_root_scores`; driver `_sweep_tree` switched to
    **min-eccentricity + eigmin-rooting**. (This is what regresses the 1-D chain — see defect below.)
  - `M tests/unit/_tree_gate.py` — Stage-B gate harness: `GateFixture(parts, grid, gop)`,
    `make_2x2/make_chain/make_natl60` (real pipeline tiles), `matched_chain_edge_baseline`,
    sample-based `edge_dir_ratio`.
  - `?? tests/test_tree_kriging_gate.py` — the Stage-B gate (4 tests): stationary, nonstationary,
    conditioning-floor-monotone, two-tree-invariance. All 4 PASS as written (but see the metric caveat).
  - `M PROGRESS.md`, `M docs/superpowers/specs/2026-06-26-…-design.md` — canonical record + spec
    amendments (eigmin-rooting + conditioning floor; §3.1/§3.1b/§3.1c/§3.4a).
- **DISPROVED + REMOVED — do NOT resurrect:** the synthesized strip-field sampler
  `_draw_joint`/`_strip_prior`/`_interiorness` + `GmrfJointKrigingSolve` (376× cross-seam blow-up;
  deleted in commit `d960f15`). `_strip_network` is KEPT (shared-node sets). The Kruskal
  `_max_overlap_spanning_tree` is kept ONLY for the Task-6 unit tests — the SHIPPED selection is the
  min-eccentricity tree.

### Dirty-diff KEEP / REPLACE inventory (what survives the fix)
- **KEEP** (correct, settled — do not touch):
  - `_posterior_eigmin`, `_condition_root_scores`, and the **eigmin-rooting** logic in the driver
    (root at max-eigmin tile; the 31× worst-root negative control is permanent).
  - the whole `tests/unit/_tree_gate.py` harness (`GateFixture`, `make_2x2/make_chain/make_natl60`,
    `matched_chain_edge_baseline`, the conditioning-floor monotonicity machinery).
  - `tests/test_tree_kriging_gate.py` structure (4 tests) — but its direction metric gets swapped
    (see REPLACE).
- **REPLACE:**
  - `_min_eccentricity_spanning_tree` → a **BFS / shortest-path tree over the adjacency graph**
    (every tree edge ∈ `_tile_adjacency`; eigmin-rooted). The min-ecc tree IS the star that regressed
    the 1-D chain — it is the thing to remove. (Keep the function only if Task-6 tests reference it;
    the DRIVER must call the new BFS-adjacency tree.)
  - the **median** conservative-direction metric → **strict-min over adjacent seam pairs**,
    **everywhere** (both the gate `tests/test_tree_kriging_gate.py` and the harness
    `_tree_gate.py::edge_dir_ratio`). The median is banned (rule i).
- **KEEP-as-is:** Kruskal `_max_overlap_spanning_tree` — ONLY for the Task-6 unit tests, never the driver.

### The live decision — stated as the FIX, not the symptom
The Stage-B coherent sampler must root its hand-forward tree as a **BFS/shortest-path spanning tree
over the tile-ADJACENCY graph where every tree edge is a real adjacency (a seam), rooted at the
max-eigmin (best-conditioned) tile.** Why:
- The **star** (what min-eccentricity produced on the 2×2 / 3-tile line) FAILED: it forces two real
  seams into **sibling** pairs — both leaves conditioned on a common parent → seam **over-correlation
  → under-dispersion** (strict-min cross-seam ratio **0.605** on the 1-D 3-tile case; overconfident
  at the seam columns).
- **Depth was NOT the cause; SIBLING-SEAMS are.** A line / BFS-adjacency tree has **zero sibling
  seams** because every seam is a parent→child tree edge.
- **eigmin-rooting** (avoids the 31× deep-conditioning blow-up at the worst-conditioned root) and
  **seam-alignment** (every tree edge is an adjacency; no sibling-seams) are **two SEPARATE
  constraints, both required.** On a 2×2 the proper BFS adjacency tree is the **L-path**, not the star
  (the star illegally uses the diagonal/corner edge as a tree edge, orphaning the two side seams into
  sibling/dropped edges).

### Exact next action (the measurement that unblocks Stage B)
1. Build the tree as a **BFS/shortest-path tree over the adjacency graph**, eigmin-rooted; **assert no
   tree edge is a non-adjacency edge** (every tree edge ∈ `_tile_adjacency`). On the 2×2 this yields
   the L-path; verify it has no sibling-seams.
2. **Measure strict-min conservative-direction** (min over adjacent cross-seam node pairs of the
   blend/single-tile-ref firstdifference variance ratio) on the **1-D 3-tile** case AND the **2×2**
   (and **3×3** if cheap).
3. **Pass condition — DISAMBIGUATED BY SEAM TYPE:**
   - **Tree-edge seams** (directly conditioned parent→child): **strict-min cross-seam variance ratio
     ≥ 0.9** at the worst tree-edge seam, on BOTH the 1-D 3-tile case and the 2×2 (3×3 if cheap).
     These must be conservative — they are the seams the hand-forward directly stitches.
   - **Dropped-edge seams** (non-tree cycle edges, transitive coherence): NOT governed by the 0.9
     tree-edge strict-min. Governed by the existing assertions — **(2)** `max_dropped_edge_residual ≤
     C·max_tree_edge` (`C ∈ [2,3]`, with the per-tile conditioning-matched chain-baseline floor) AND
     **(3)** cross-seam variance ratio `≥ 1−ε` (never under-dispersed). A **2×2 L-path tree has
     exactly ONE dropped edge** (the 4-cycle minus the 3 L-path edges); that single dropped seam is
     bounded by assertion (2) + the non-under-dispersion of (3), NOT by the 0.9 tree-edge floor.
   - If tree-edge seams clear strict-min ≥ 0.9 in BOTH cases → Stage B is DONE (commit Tasks 6–9, run
     full suite, hold for gate review). If even seam-aligned (BFS-adjacency) trees can't clear it →
     **junction-tree (spec §6) is earned** (the real escalation, now justified by measurement).

### Three LOCKED rules (do not relitigate)
- **(i) Conservative-direction is gated by STRICT-MIN over adjacent seam pairs, permanently — never
  median/aggregate.** The median laundered exactly this 0.605 failure (my gate's median-direction
  passed while the strict-min Phase-3 test caught it). Revert any median direction metric to strict-min.
  - **EXPECTED RED (do not "fix" it the wrong way):** applying strict-min (reverting the median) WILL
    turn the 4 currently-green gate tests **RED on the stationary case** (strict-min **0.605 < 0.9**).
    **That red is CORRECT and EXPECTED** — it is the known sibling-seam defect surfacing, NOT a new
    regression. The gate returns to green **only** after the BFS-adjacency-tree fix removes the
    sibling-seams. A fresh session must **not** make this red go away by any means other than the
    BFS-adjacency-tree construction (no threshold change, no metric swap-back, no fixture tweak).
- **(ii) The rooting contract is TWO-PART, both with permanent negative-control tests:** max-eigmin
  root (neg control: rooting at worst-conditioned tile → **31×** blow-up) AND seam-aligned tree edges
  / no sibling-seams (neg control: the star's **0.605** sibling-seam under-dispersion).
- **(iii) The conditioning floor is a MONOTONE LAW in eigmin**, with `tree_edge == chain_edge` at
  equal conditioning (measured `0.644 == 0.644`), gated against a **per-tile conditioning-matched
  chain baseline** (`matched_chain_edge_baseline`), recorded as a characterized `known_bias`. This is
  settled and in the spec.

### Standing meta-lesson (canonical — for Phase 5 too)
Every Stage-B failure was a **localized joint-law property invisible to whatever AGGREGATE statistic
was certifying it** (marginal variance → gradient ratio → median direction). **Coherence is gated on
worst-case LOCALIZED seam behavior, never aggregate anything.** Phase 5's tuner searches `range` →
drives `eigmin` down → raises the conditioning floor; **cross-seam coherence residual is a CONSTRAINT,
not a free variable**, and junction-tree is the documented short-range escalation.

### Spec lag (must fix when the measurement confirms)
The spec (§3.1/§3.1b/§3.1c/§3.4a) **already** reflects **eigmin-rooting** and the **conditioning-floor
law**. It does **NOT yet** contain the **BFS-adjacency-tree / no-sibling-seams** refinement or the
**strict-min (not median)** conservative-direction rule — **add both to §3.1b/§3.3 once step (2)–(3)
above confirm them**, so the spec stops lagging the decision.

---

## Current work (index — do not duplicate task state here)

- **Phase 4: FEM/triangulation SPDE + non-chain coherent sampler — IN PROGRESS.**
  - **Stage A COMPLETE (Tasks 1–4); Stage-A GATE PASSED.** Projection seam
    (`core/projection.py`) consumed by `GMRFCovarianceOperator` (carries `q_prior`, C3
    `_diag` fast==slow pinned) and de-gridded `PrecisionFields`/`PrecisionDistribution`
    (`projection` + `prior_precision`, cov/sample route through `projection.weights`/
    `field_shape`); `GMRFPrecisionReduction` threads both; `solve.py` unchanged (projection
    rides on `base_fields`). Gate evidence: **185 passed / 2 skipped** (178 + 7 new), typecheck
    + lint clean; tests diff vs `31a58c6` = 96 insertions / 0 deletions (additions only);
    invariant-2 grep clean on the GMRF path. **Scoping note (gotcha):** the Task-4 gate grep's
    sole hit is `persisted.py` `PersistedDistribution.sample` (`ny, nx = self.grid.shape`) — the
    **OI low-rank** rep, which is inherently grid-bound and NOT in Phase-4 de-grid scope. The
    GMRF precision read-off (`PrecisionDistribution` + `GMRFCovarianceOperator`) is grep-clean.
    Interpret invariant-2 as "the precision/GMRF path is projection-driven", not "persisted.py
    contains no `.shape`".
  - **Stage B Tasks 5–6 COMMITTED then SUPERSEDED by a design pivot (`_strip_network` kept,
    `_draw_joint`/`_strip_prior` to be removed).** Tasks 5 (`a619265`) and 6 (`809a570`) built the
    spec-literal **synthesized strip-field** sampler (`_draw_joint`: one auxiliary field drawn from
    the prior-induced strip sub-GMRF; tiles kriged toward it). Task 7's verification **disproved that
    construction** — see the canonical Phase-4 cross-cutting decision "Stage-B sampler = spanning-tree
    hand-forward" below. **Working tree is clean at `809a570`** (Task-7 synthesized-field code was
    written, disproved, and reverted uncommitted — nothing wrong is on disk). `_strip_network` is
    kept (it computes the tile-adjacency / shared-node sets the spanning tree needs); `_draw_joint`
    and `_strip_prior` are removed in the re-architected Task 6.
  - **Stage B COMPLETE (Tasks 6–9); Stage-B GATE PASSED (uncommitted at this checkpoint — awaiting
    owner gate review before Stage C).** The spanning-tree hand-forward sampler is implemented and
    the gate is GREEN on the real near-singular natl60 regime. Final construction + the four-turn
    finding are in "Cross-cutting decisions (Phase 4)" below ("Stage-B sampler …", esp. the
    **conditioning-floor law** and the **eigmin-rooting contract**). Gate evidence (real natl60 2×2):
    stationary tree-edge **0.681 ≤ matched_chain 0.706·1.15**, dropped 0.681, dir 1.012;
    nonstationary tree 0.688, dir 1.006; conditioning floor **monotone in eigmin** `[0.706,0.624,
    0.551]` with tree==chain at equal conditioning; two-tree invariance PASSED (well-conditioned
    roots agree 0.68/0.84, worst-conditioned root 31.4 is the negative control the eigmin rule
    avoids). **Next action: owner Stage-B gate review → on sign-off, commit Tasks 6–9 + Stage C
    Task 10.**
  - Scope (source of truth): `phase4_scope_spec.md` (settled + owner-amended, `00519b1`).
  - Design: `docs/superpowers/specs/2026-06-26-phase4-fem-and-nonchain-sampler-design.md` (`f7960f8`).
  - Plan: `docs/superpowers/plans/2026-06-26-phase4-fem-and-nonchain-sampler.md`
    (16 tasks; tracker `.tasks.json` co-located, Tasks 1–4 `completed`).
  - **Hard-gated sequencing:** Stage A (Tasks 1–4, generalize under green) → Stage B
    (Tasks 5–9, non-chain joint-kriging sampler on the grid) → Stage C (Tasks 10–16, FEM).
    Three user-gates: Task 4 (Stage-A regression — Phase-3 suite reproduces exactly), Task 9
    (Stage-B positive control — distinct-tiles cross-seam + corner-junction joint cov +
    nonstationary, residual recorded; junction-tree fallback only if out-of-tolerance), Task 16
    (Stage-C FEM DoD).
  - **Five pinned correctness contracts (tested, not assumed — see design §0):** C1 strip prior
    on the induced subgraph (corner-junction joint cov), C2 three white-noise streams, C3 `_diag`
    fast-path equivalence, C4 per-node strip-prior κ (nonstationary), C5 mechanically-enforced
    no-grid-path-for-FEM; + C6 shared mesh-node match, C7 boundary-measured payoff margin.
  - **Key decisions:** scipy.spatial.Delaunay + hand-rolled P1 assembly (no new dep, Shewchuk
    upgrade behind the same seam); strip-prior = induced submatrix of the persisted per-tile
    PRIOR precisions (so PrecisionFields gains `projection` + `prior_precision`); `GmrfKrigingSolve`
    kept intact as the 1-D chain regression oracle (registry repoints to `GmrfJointKrigingSolve`,
    one wiring assertion updated). **Next action: Task 1 (Projection seam).**
- **Phase 3: GMRF method + representation-agnostic generalization — COMPLETE (all 11 tasks).**
  - **Stage C COMPLETE (Tasks 10–11):** Task 10 `PerturbEnsembleDegradation` driver end-to-end
    (per-tile independent members, weight-crossfaded; `EmpiricalReduction` retagged
    `perturb-ensemble`; blend appends `degradation_transform`/`KnownBias.DEGRADED_COHERENCE`;
    asserts the OPPOSITE contract — coherence loss recorded, mean continuous, sampler honestly
    under-dispersed vs the conservative marginal, NOT held to the coherence bar). Task 11
    nonstationary-κ GMRF (`MaternGMRF.solve` resolves `range` scalar OR field → elementwise κ
    field → spatially-varying `Q`; `kappa_from_range`/`range_from_kappa` polymorphic;
    κ↔range mapping recorded). Full suite **178 passed / 2 skipped**, typecheck + lint clean.
  - All three user-gates PASSED (Task 3 Stage-A regression, Task 5 Takahashi-vs-oracle, Task 9
    Stage-B kriging coherence). Plan `.tasks.json` all `completed`.
  - **Stage A COMPLETE (Tasks 1–3).** Three seams generalized OI-first under green:
    `ReductionStrategy` (`distributions/reduction.py`, selected by live-operator
    `representation`) + `CoherentMemberDriver` (`LowRankSharedBasis`, selected by persisted
    `sampler_spec`). Stage-A user-gate PASSED with captured AC evidence — Phase-2 subset
    129/2 green and untouched (full suite 134/2 = 129 + 5 new Stage-A tests), typecheck/lint
    clean, zero Phase-2 test files modified (diffed vs pre-Phase-3 baseline `793297e`).
  - **Stage B Tasks 4–8 COMPLETE** (committed): GMRF grid topology + bilinear/Projection
    (`methods/gmrf_grid.py`); CHOLMOD factor + hand-rolled Takahashi selective inverse
    (`methods/gmrf_linalg.py`, **USER-GATE PASSED** vs dense-Q⁻¹ oracle); `MaternGMRF` EXACT
    sparse-precision operator + temporal-taper conditioning (`methods/gmrf.py`, registered);
    `PrecisionFields`/`PrecisionDistribution` + `GMRFPrecisionReduction` (genuine-first-class,
    no factor); `solve_unit` dispatches `PrecisionFields → PrecisionDistribution`.
  - **Task 9 (Stage-B gate) COMPLETE — reworked via conditioning-by-kriging; GATE PASSES.**
    The original `GmrfPrecisionSolve` "native shared-w" driver (Task 8) was DISPROVEN
    (cross-seam derived quantities ~50% under-dispersed) and is REMOVED. Replaced by
    `GmrfKrigingSolve` (9a–9d, all committed): per-tile exact posterior draw krige-corrected
    toward ONE global node-space realization (single forward sweep, values-not-seeds, Q-separator
    precondition asserted). **Gate evidence (captured):** cross-seam `firstdifference` variance
    ratio blend/ref **min 0.93** (conservative; old driver ~0.49 / −0.51), correlation-structure
    fidelity max-dev **0.10**, pointwise σ-upper-bound held, OSSE+OSE + provenance +
    first-class all green; full suite **171 passed / 2 skipped**, typecheck + lint clean. Joint-cov
    oracle (9c) pins exactness vs a dense global reference (per-tile, cross-seam, 3-tile
    transitivity) + separator negative control. **USER-GATE: awaiting owner sign-off before
    Stage C** (spec-§8 escalation was NOT triggered — gate passed).
  - **Task-9 rework 9a–9c COMPLETE (committed); 9d IS THE NEXT ACTION.**
    - 9a (`posterior_cov_columns` full `(Q⁻¹)[:,S]` via cached per-node back-solves on
      `GMRFFactor`/`PrecisionDistribution`) — pinned vs dense oracle.
    - 9b (`GmrfKrigingSolve` forward-sweep driver, values-not-seeds, **Q-separator assertion**
      overlap ≥ `STENCIL_REACH=2`) — replaced the disproven `GmrfPrecisionSolve` (class removed)
      under `sampler_spec="sparse-precision"`.
    - 9c (joint-cov oracle `tests/unit/test_gmrf_kriging_oracle.py`): per-tile full-cov ==
      exact posterior; cross-seam joint (incl. across-seam blocks) == global; 3-tile
      transitivity; separator negative control. All EXACT by construction.
  - **Next action: Phase 3 is DONE.** Phase 4 (autotune) is the next milestone (deferred,
    scoped after Phase 3 runs — spec §6). Before Phase 4 build: the GMRF cross-tile sweep is
    exact only for tree-structured tile adjacency; 2-D/FEM tilings need the pre-drawn-joint or
    junction-tree variant (spec §5.3.1 Phase-4 caveat — do NOT inherit as unconditionally true).
  - **Working-tree state at this checkpoint (committed):** `pipeline._blend_eval_points` has the
    sparse-precision no-factor **moment-crossfade** OSE path + the `eval_point_cov` provenance
    marker (Task-9 §B6, keeper); `GmrfPrecisionSolve` carries a shape-bug fix but the whole class
    is superseded by `GmrfKrigingSolve` in 9b; the obsolete `test_gmrf_blend_no_variance_dip`
    (pre-amendment contract) was removed (9d writes the derived-quantity-parity replacement).
  - Scope (source of truth): `phase3_scope_spec.md` (settled; §5.1 now records the two
    settled forks — scikit-sparse/CHOLMOD backend + temporal-taper-into-R conditioning — and
    the forward-compat Projection abstraction).
  - Design = the spec; Implementation plan: `docs/superpowers/plans/2026-06-25-phase3-gmrf-representation-generalization.md`
    (11 tasks; tracker `.tasks.json` co-located, all `pending`).
  - **Hard-gated sequencing:** Stage A (Tasks 1–3, generalize OI under green) → Stage B
    (Tasks 4–9, add GMRF) → Stage C (Tasks 10–11). Three user-gates: Task 3 (Stage-A
    regression, 129/2 must stay green — if OI changes, surface it, don't adjust tests),
    Task 5 (Takahashi vs dense-Q⁻¹ oracle — red = math bug, not a tolerance loosen),
    Task 9 (Stage-B GMRF blend validation — spec-§8 escalation on failure).
  - **Key architecture decisions (canonical — see Cross-cutting decisions Phase 3):**
    two-point dispatch split (reduction by live-operator representation pre-persistence;
    coherence driver by persisted `sampler_spec` post-persistence); `to_persisted` is a
    `ReductionStrategy` in `distributions/reduction.py`, NOT on the core Protocol
    (invariant 1 + one-way dependency rule); GMRF read off the precision via a `Projection`
    (grid=identity, off-grid=bilinear) so a later FEM phase needs only a new projection.
- **Phase 2: tiling / blend / coherent uncertainty — COMPLETE (all 17 tasks 0–16).**
  - Scope (source of truth): `phase2_scope_spec.md` (committed `fa93897`).
  - Design doc: `docs/superpowers/specs/2026-06-23-phase2-tiling-blend-architecture-design.md`.
  - Implementation plan: `docs/superpowers/plans/2026-06-23-phase2-tiling-blend.md`
    (17 tasks, 0–16); tracker `.tasks.json` co-located, all `completed`.
  - **Both user gates PASSED with captured AC evidence:** Stage A (Task 15 — regional blend
    == single-tile, no seam, conservative σ, withheld OSSE+OSE eval, provenance, both
    withholding exemplars) and Stage B (Task 16 — projection-mixed partition, sample-based
    `regrid`, cross-CRS blend, polar-void relax-to-prior, opt-in global skipped cleanly).
  - **Key §8 resolution (see Cross-cutting decisions):** the structured coherent-sample
    driver is the shared-overlap-basis (Löwdin) construction, NOT member-only `z_r`.
  - Suite: 129 passed / 2 skipped (Stage-B global run + one pre-existing skip).
  - **DEFERRED to Task 15:** `run_tiled_pipeline` in `application/pipeline.py`. The plan's Task-12 Step 3 only implements `TilingCoordinator` (which IS done + tested) and says the pipeline wiring is "exercised in Task 15". The eval impedance — `_evaluate` reads `product.per_time[].base.fields.mean`, but the coordinator returns `BlendedDistribution`s — is resolved when Task 15's integration test defines the contract. Build `run_tiled_pipeline` there.
- **Milestone: rename to `sverdrup` + PyPI release — COMPLETE (Tasks 1–7).**
  - Design doc: `docs/superpowers/specs/2026-06-21-sverdrup-pypi-release-design.md` (approved).
  - Implementation plan: `docs/superpowers/plans/2026-06-21-sverdrup-pypi-release.md` (7 tasks);
    tracker `.tasks.json` all `completed`.
  - Package renamed `regatta`→`sverdrup`; hatchling + hatch-vcs tag-driven build; Apache-2.0 +
    metadata + `py.typed`; core deps + `dask`/`io`/`all` extras; Trusted-Publishing workflow
    shipped at `docs/superpowers/ci/release.yml` (Option B). User-gate (clean-venv install smoke)
    re-validated. Public repo `killett/sverdrup` created and `main` pushed.
  - **DONE end-to-end:** all three user-side steps completed by the user — workflow installed,
    PyPI Trusted Publisher configured, `v0.1.0` tagged+pushed. `sverdrup 0.1.0` is **live on
    PyPI** (wheel+sdist, Apache-2.0); `pip install sverdrup` verified in a clean venv.
- **conda-forge distribution (in progress):**
  - Recipe generated via `grayskull` (run with `pixi exec grayskull`, not added to manifest),
    polished, and committed at `conda-recipe/meta.yaml` (+ `conda-recipe/README.md`).
  - `noarch: python`; sdist sha256 verified against PyPI; confirmed the sdist builds **without
    `.git`** (hatch-vcs reads version from PKG-INFO) — so conda-forge's sdist build works.
  - **Auto-update mechanism (the goal):** after the one-time `conda-forge/staged-recipes` PR,
    the conda-forge **autotick bot** watches PyPI and opens a version-bump PR on every PyPI
    release. Steady state: push tag → PyPI Action publishes → bot opens feedstock PR → merge.
  - **staged-recipes PR OPEN:** https://github.com/conda-forge/staged-recipes/pull/33814
    (`killett:sverdrup`). Awaiting conda-forge CI + maintainer review/merge → feedstock
    auto-created → conda package ships. User responds to any reviewer feedback.
  - **Gotcha:** the autotick bot only bumps version+hash. When `pyproject.toml` runtime deps
    change, mirror them into `requirements/run` in both `conda-recipe/meta.yaml` and the
    feedstock PR.
  - **Gotcha (CI failure, fixed):** first staged-recipes build #1541860 FAILED on all platforms
    in the *test* phase: `ModuleNotFoundError: No module named 'dask'`. Cause — the recipe test
    ran `python -m sverdrup`, but `__main__.py` eagerly imports the dask executor + pipeline
    (the `dask`/`io` *optional extras*, not core run deps). The conda test env has only core
    deps. Fix: test only the core import surface (`import sverdrup`, `sverdrup.core.grid`,
    `pip check`) — never the entry point — since core deps are all that's guaranteed installed.
    Same trap will bite any feedstock test: do not add extras-dependent checks to `test:`.
- **Phase 1: COMPLETE** — 22 tasks on `main`; suite 70 passed / 1 skipped; both user-gates
  re-validated. Plan: `docs/superpowers/plans/2026-06-21-regatta-phase1.md` (historical).
  Design: `docs/superpowers/specs/2026-06-21-regatta-phase1-architecture-design.md`.

## Cross-cutting decisions (canonical — lives nowhere else)

- **Method 1 = hand-rolled dense GP/OI** (not pyinterp/GPSat). Native covariance +
  whole-field samples via cached Cholesky `L` of `K_dd+R`, `cov(A,B)=K_AB−Vᵀ_A V_B`,
  `V_X=L⁻¹K_dX`. `R` is a structured operator (diagonal for nadir). Two complementary
  seams: `LinearSolver` (methods/, backend swap *within* the kernel formulation) and
  `CovarianceOperator` Protocol (core/, carries the kernel→precision/SPDE jump).
- **`CovarianceOperator` is the seam, not the GP.** `GaussianPredictiveDistribution(mean,
  cov: CovarianceOperator)` is method-agnostic; GP math lives in `methods/oi.py`. Operator
  declares `fidelity ∈ {EXACT, LOW_RANK, SAMPLE}`.
- **Exact/persisted boundary:** the unit of work returns the **Persisted** rep (mean +
  exact marginal var + low-rank `B` + clipped diagonal residual `d` + seed + sampler spec +
  rank `r` + captured-energy diagnostic), **never** a live operator carrying `L`. `B` from a
  matrix-free seeded randomized SVD of `P`; `d = clip(diag(P)−rowsum(B²), 0, None)`.
- **Unifying on-worker rule:** the worker extracts *everything needing the EXACT operator* —
  base reduction, declared derived quantities (first-difference), AND eval-point predictions
  at withheld/off-grid locations — before discarding the operator. Off-grid predictives are
  computed exactly, never by interpolating a marginal-variance field (invariant 7).
- **`Product` is an explicit bundle:** base + derived Persisted products + eval-point
  predictions, provenance linking each (route + `CovFidelity` stamped).
- **Derived dispatch = linearity × representation × `CovFidelity`.** Provenance stamps the
  covariance fidelity used. Only `firstdifference` is real (on-worker, EXACT); velocity/eke/
  transport/area_average are committed-signature stubs.
- **Data (Decision B):** real `DataSource` against ODC THREDDS + `./data/cache/`; daily
  NATL60-CJM165 reference (NOT the 11 GB hourly) clipped to 42-day window
  **2012-10-22→2012-12-02**; OSSE nadir obs ~285 MB whole. Committed tiny NetCDF fixtures for
  offline CI. Oracle = opt-in OI-RMSE parity **within 10% of the ODC OI baseline** (skipif no
  data/network; ≤25% for the tiny-fixture smoke run). OSE eval uses the withheld **CryoSat-2**
  along-track.
- **Space-time structure (load-bearing):** the GP covariance is space-time — spatial length
  scale × **temporal correlation scale**, both through the `ParameterProvider`. The
  unit-of-work window is space-time (spatial tile × temporal obs window around target output
  time(s); the 21-day spin-up gives early times temporal neighbors and bounds `N_obs`).
  **`GridSpec` stays purely spatial**; time is carried on the `Product` as a series of
  per-time persisted fields. One factored `K_dd+R` serves all output times in the window.
- **Kernel:** pinned to stationary **Matérn-3/2** (variance + spatial length + temporal
  scale), behind a `methods/kernel.py::Kernel` interface so it can go nonstationary later
  without touching `GPCovarianceOperator`.

## Cross-cutting decisions (canonical — Phase 4)

- **Stage-B non-chain sampler = spanning-tree hand-forward (NOT a synthesized strip field).**
  The spec-literal Task-6 construction (`_draw_joint`: draw ONE auxiliary field over the
  overlap-strip sub-GMRF, krige every tile toward it) was **disproved by measurement** and replaced.
  This decision is owner-confirmed across a multi-turn adversarial review; the measurement trail is
  recorded here because it is load-bearing and lives nowhere else.
  - **Disproof (real natl60_tiny fixture, 3-tile + 2×2):** the synthesized-field driver blows the
    cross-seam first-difference variance ratio to **376×** (bound ≤2.5) and joint-cov rel-err vs the
    dense global posterior to **1.617**. On a well-conditioned synthetic corner fixture the same
    driver is fine (cross-seam 0.77–1.33) — so the construction is not trivially broken; the natl60
    fixture is the discriminator.
  - **Mechanism (measured, not guessed):**
    1. prior-vs-posterior is a **non-issue** — obs sit at tile centres, so `AᵀR⁻¹A≈0` at the strip
       nodes and `Q_post ≡ Q_prior` there to machine precision (strip submatrices byte-identical;
       `x_joint` std 613 either way). The "diffuse prior was wrong scale" hypothesis is **refuted**.
    2. the joint-cov error is **high-frequency**, **90% in the complement** of the bottom-k near-null
       subspace, and a shared global coarse-mode draw does **not** close it (1.617→1.393 at k=6).
       There is **no spectral gap** (global `Q_post` bottom eigenvalues `2.5e-7, 4.95e-7, …`, a
       continuum) — so the near-improper behaviour is an O(n) low-frequency tail, NOT a low-dimensional
       coarse space. Coarse-space deflation is **refuted**.
    3. `cond(sigma_ss) ≈ 4e8` (the value-conditioning operator `solve(Σ_ss, x_s − x_u|_S)`), **flat
       across halo width k=1,2,3 and resolution 0.5°/1.0°**, pinned by `Q_post`'s near-null eigenvalue
       2.5e-7 — i.e. **intrinsic** (sparse nadir obs leave the `(κ²−Δ)²` low-frequency mode
       under-determined), NOT a strip-resolution mismatch. A resolution precondition would not fix it.
    4. **jitter is a cover-up** (proven): adding `λI` to `Σ_ss` collapses the gradient ratio
       (324→3.2) while joint-cov rel-err **stays 0.61–0.73** — gradient parity goes green while the
       joint law is still 60–70% wrong. `pinv(rcond)` is a no-op (modes are physically huge-variance,
       not numerically tiny). **Gradient parity ≠ joint-law fidelity; gate the joint cov.**
  - **The fix:** the 4e8 singularity is *never excited* when conditioning targets are **consistent**
    (a residual `x_s − x_u|_S` that is tiny because `x_s` is an actual neighbour draw from the same
    posterior). That is exactly what the Phase-3 **chain** sweep does (`GmrfKrigingSolve._sweep`,
    still green). Generalize the line to a **max-overlap spanning tree of the tile-adjacency graph**:
    each tile is hand-forward-conditioned on its parent's already-drawn overlap values (the proven
    chain mechanism), non-tree edges carry a **bounded, recorded** transitive-coherence residual.
  - **Validation (2×2 natl60):** spanning-tree sweep drops overall joint-cov rel-err **1.617 → 0.313**
    (no 4e8 excitation). Tree edges **0.18–0.24**, dropped edges **0.19–0.43**. The plain **chain
    baseline** on the green 3-tile natl60 case is **0.298 overall, edges 0.294/0.313** — i.e. the
    ~0.30 halo-truncation residual already accepted & shipped green. Tree edges are **no worse than
    that baseline**; the dropped-edge max (0.43, a BFS-star artifact that kept a low-overlap diagonal
    and dropped a high-overlap side) is **1.4× the baseline** and improves under max-overlap MST.
  - **Task-9 gate = three coupled assertions (thresholds derived from the 0.30 chain baseline, not
    guessed):** (1) **tree-edge parity** — `max_tree_edge_residual ≤ chain_baseline·(1+slack)`,
    chain_baseline measured on the 1-D natl60 case; (2) **dropped-edge relative bound** —
    `max_dropped_edge_residual ≤ C · max_tree_edge_residual`, `C ∈ [2,3]`; (3) **conservative
    direction** — cross-seam derived-quantity variance ratio (blend/ref) on dropped edges `≥ 1−ε`,
    never under-dispersed (the real protection; magnitude-bounded-but-overconfident must fail).
    Plus a **two-tree invariance property test**: the shipped blend is within tolerance under the MST
    AND one alternative spanning tree (correctness is tree-invariant; only the residual distribution
    moves — if correctness depends on the tree, topology-fragility has returned → loud red).
  - **Per-tree-edge separation assert:** the MST is built from existing `extended_window` overlap
    strengths; every selected tree edge must have overlap ≥ the stencil-separation requirement
    (`_assert_separates` content, now per-tree-edge not per-chain-link) — a too-thin tree edge cannot
    hand forward and is a loud red per edge.
  - **Spec amendment (replaces two wrong sentences):** §5.3/§4 becomes *"hand-forward conditioning
    along a max-overlap spanning tree of the tile adjacency; non-tree edges carry a bounded, recorded
    coherence residual; junction-tree is the exact escalation if a measured residual exceeds
    tolerance."* **Product-facing disclosure (load-bearing, honest):** the shipped global SSHA
    uncertainty carries a bounded, recorded cross-seam coherence residual on **non-tree** tile
    adjacencies — coherence there is **transitive, not direct**; a downstream consumer computing a
    transport across a non-tree seam is entitled to know this. Junction-tree (a) is the documented
    **exact escalation** if the Phase-5 tuner wanders to short range and pushes a measured residual
    past the gate; it is NOT adopted now because it re-introduces tile-topology dependence and
    √(#tiles) treewidth — the very costs Stage B exists to avoid.
  - **Contracts C1/C2/C4 (synthesized-field) are RETIRED** and replaced by the spanning-tree
    contracts above. C3, C5, C6, C7 stand. Obsolete on-disk code to remove in the re-architected
    Task 6: `_draw_joint`, `_strip_prior`, `_interiorness` (`distributions/coherent.py`) and their
    tests (`tests/unit/test_draw_joint.py`). `_strip_network` is **kept** (adjacency + shared-node
    sets). Stage-A (Tasks 1–4) is **unaffected** — the Projection seam / de-grid generalization is
    orthogonal and already gated green.
  - **STANDING STAGE-B CAUTION (read before touching the GMRF coherent sampler, esp. in Phase 5).**
    Across four consecutive review turns the failure (or the fix) lived in a **joint-law property
    invisible to a magnitude/gradient-only gate**: (1) the value-conditioning singularity
    `cond(Σ_ss)≈4e8`, (2) coarse-mode mislocalization (error in the complement, not the near-null),
    (3) jitter laundering (gradient green / joint-cov 0.6+ wrong), (4) the relative-bound degeneracy
    (a near-zero tree-edge residual would spuriously red a bounded dropped edge — hence the
    chain-baseline floor on assertion 2). **The GMRF coherent sampler's failure modes are joint-law
    properties; gate the joint covariance vs a dense reference and the conservative DIRECTION at the
    seam, never just magnitude/gradient.** The **near-singular short-range posterior** (sparse obs +
    near-improper `(κ²−Δ)²` ⇒ `Q_post` eigmin ~1e-7) is the regime that excites all four — and
    **Phase 5's autotuner searches `range`, which drives the posterior straight into it.** Re-enter
    this regime with this context, not from scratch.

- **Stage-B sampler — FINAL construction (supersedes the spanning-tree decision above with the
  selection rule + the intrinsic floor; all measured on real natl60).** The non-chain sampler is
  `GmrfTreeKrigingSolve`: hand-forward conditioning along a **minimum-eccentricity, max-overlap
  spanning tree, rooted at the BEST-CONDITIONED tile**, with the dropped (non-tree) edges carrying a
  bounded, recorded transitive-coherence residual. Four findings, each measured, each a contract:
  - **Depth governs stability, not overlap.** Hand-forward kriging accumulates drift per hop; a deep
    tree routes the conditioning through the near-singular `Σ_ss` (`cond≈4e8`) in an order that
    amplifies (measured 10× at a depth-3 edge vs ~1.4× at depth 1; the max-overlap Kruskal MST can be
    deep → unstable). Fix: **minimum-eccentricity** root + shortest-hop BFS tree → shallow (a star,
    depth 1, on the `k·corr_len` heavy-overlap regime); rel stays bounded (0.40–0.45) as the domain
    scales to 3×2 / 3×3 where the naive MST reaches depth 3–4 and risks blow-up.
  - **EIGMIN-ROOTING CONTRACT (load-bearing, pinned with a negative control).** The blow-up root is
    the **most near-singular tile** (smallest `eigmin(Q_post)`): drawn unconditionally, its huge
    near-null draw is a toxic anchor (measured **31×** rel rooting there, vs 0.36–0.84 at any
    better-conditioned root). `_condition_root_scores` = `-eigmin(Q_post)` per tile; the tree roots
    at max-eigmin. **Negative control (must stay in the gate):** rooting at the worst-conditioned
    tile blows up >1.5× the well-conditioned roots — a future refactor that roots arbitrarily
    reintroduces the 31× and fails loudly. `eigmin` ≠ accuracy-rank among the *non-toxic* roots, but
    it cleanly avoids the toxic one.
  - **THE CONDITIONING FLOOR (the central finding; a characterized `known_bias`).** With every
    topology issue fixed, an elevated cross-seam residual remains around a near-singular tile and
    **no tree removes it** — it is not topology, it is that conditioning a tile with `eigmin≈2.5e-7`
    onto anything is ill-posed, and hand-forward inherits that. Measured: the residual is **MONOTONE
    in `eigmin(Q_post)`** (`[0.706, 0.624, 0.551]` as eigmin rises) and **`tree_edge == chain_edge`
    EXACTLY at equal conditioning** — i.e. the tree sweep is NOT worse than the plain chain on a
    near-singular tile; the chain pays the identical floor. The gate therefore compares each tree
    edge to the **per-tile conditioning-matched chain baseline** (`matched_chain_edge_baseline`,
    same tile, same eigmin), not to an easier well-conditioned chain — like-for-like, so the floor is
    not mistaken for a defect, while a multi-hop tree degrading past the fresh chain conditioning
    still fails.
  - **Gate (Task 9, three coupled assertions, PASSED):** (1) `max_tree_edge ≤ matched_chain·1.15`
    (hand-forward no worse than chain at equal conditioning); (2) `max_dropped ≤ max(2.5·max_tree,
    matched_chain)`; (3) conservative direction (median seam firstdifference variance ratio vs the
    single-tile reference) `≥ 0.9` — never under-dispersed. Plus two-tree invariance (well-conditioned
    roots agree + worst-root 31× negative control) and the nonstationary-κ case. Conservative
    everywhere, bounded under eigmin-rooting, chain-quality where conditioning allows.
  - **PHASE-5 OPERATIONAL WARNING (the bridge — do not let the tuner re-derive this arc).** The
    coherent sampler's accuracy floor is a **function of `eigmin(Q_post)`, which the `range`
    parameter controls**: short range → near-improper posterior → eigmin↓ → the cross-seam residual
    rises toward the 2.2 / 31 seen when unguarded. **The Phase-5 autotuner MUST treat cross-seam
    coherence residual as a CONSTRAINT, not a free variable** — searching `range` down drives the
    posterior into the regime this whole arc characterized. **Junction-tree (spec §6) is the
    documented exact escalation** for the short-range regime where the floor exceeds tolerance; it
    was deliberately NOT built now (measured proof it is unneeded at tested conditioning: 3 of 4
    trees nail 0.30 with zero cycle correction, and tree==chain at equal conditioning — cycle
    exactness is not what is broken; the floor is intrinsic).
  - **Obsolete (removed):** `_draw_joint`/`_strip_prior`/`_interiorness` (synthesized strip field,
    disproved 376×); the Kruskal `_max_overlap_spanning_tree` is retained only for the Task-6 unit
    tests — the SHIPPED selection is `_min_eccentricity_spanning_tree(adjacency, n, root_score)`.

## Cross-cutting decisions (canonical — Phase 3)

- **Two-point dispatch split (load-bearing).** Reduction strategy is selected by the LIVE
  operator's `representation` (pre-persistence): `select_reduction(dist)` in
  `distributions/reduction.py` reads `getattr(dist.cov_op, "representation", "lowrank+diag")`
  → `LowRankReduction` ("lowrank+diag") / `GMRFPrecisionReduction` ("sparse-precision"), or
  `EmpiricalReduction` when there is no operator. The coherence driver is selected by the
  PERSISTED `sampler_spec` (post-persistence): `select_driver(sampler_spec)` in `coherent.py`
  → `LowRankSharedBasis` / `GmrfPrecisionSolve` / `PerturbEnsembleDegradation`. Never dispatch
  on method identity.
- **`to_persisted` is NOT on the core Protocol.** §5.4's illustrative on-`CovarianceOperator`
  signature was self-inconsistent (it returns a `distributions/` type from `core/`, breaking
  the one-way `application/→distributions/` rule, and modifies the Protocol, violating
  invariant 1). Realized as the `ReductionStrategy` Protocol in `distributions/reduction.py`,
  selected by representation. Operators carry a `representation` class attr only (not on the
  Protocol). Spec §5 permits this ("signatures illustrative; correct where it differs").
- **GMRF reads off the precision via a `Projection`.** Precision-node space and output-grid
  space kept distinct even though they coincide on a regular grid. `mean→W·mean`,
  `cov→W Σ Wᵀ` (Σ = selective-inverse entries in W's stencil, never dense). Grid block =
  `GridIdentityProjection` (W=identity-on-nodes); off-grid = `BilinearProjection`; `A`
  (grid→obs conditioning) is itself a projection into node space. A later FEM phase supplies
  a new `Projection` + mesh-assembly only — precision rep, coherence driver, persistence, and
  blend untouched. (Recorded in `phase3_scope_spec.md` §5.1.)
- **GMRF time = temporal taper into R (not a temporal SPDE axis).** `Q_post = Q_prior +
  AᵀR⁻¹A`; R per-obs variance inflated by `exp(|t_obs−t_out|/temporal_taper_scale)`; the
  taper scale is a tunable in `parameter_space()` resolved via the provider. Conservative
  diagonal-R approximation (under-uses temporal structure) recorded as a `known_bias`. The
  OI-vs-GMRF asymmetry (OI = full space-time kernel; GMRF = spatial cov + tapered likelihood)
  is deliberate and read into the Stage-B comparison.
- **One sparse factor serves all three (invariant 6).** `GMRFFactor` (CHOLMOD simplicial)
  serves `sample` (L⁻ᵀw), `solve` (posterior mean), and the hand-rolled Takahashi selective
  inverse (`diag(Q⁻¹)` + adjacent entries on the L+Lᵀ pattern). Dense `Q⁻¹` exists ONLY as a
  small-grid test oracle. Adjacency precondition (W's 4-node stencil + firstdifference's
  adjacent-node cov inside the selective-inverse pattern) is asserted — guards a future wider
  κ-stencil from silently breaking eval var / cancellation.
- **GMRF eval-point OSE blend = moment crossfade.** GMRF has no low-rank eval factor; cross-
  tile eval-point scoring uses `mean=Σwμ`, `var=(Σwσ)²` (exact per-tile var from Takahashi).
  Cross-eval-point covariance in overlaps is NOT represented (not consumed by per-point OSE
  accuracy/calibration) — recorded in provenance (`eval_point_cov` marker), a flag not a
  hidden assumption. Full coherent eval-point GMRF sampling is out of Phase-3 scope.
- **α = 2 (ν = 1)** fixed integer smoothness — the canonical `(κ²I−Δ)` 5-point stencil
  squared. Continuous ν deferred to Phase 4.
- **GMRF cross-tile coherence = conditioning-by-kriging, NOT native shared-w (amendment, spec
  §5.3.1).** The Checkpoint-2 "GmrfPrecisionSolve: mean + L⁻ᵀw, native shared-w" line was wrong
  for non-identical Q — `L⁻ᵀ` is a global map, so shared factor-space white noise yields
  decorrelated physical fields across distinct tiles (proven by a distinct-tiles positive
  control: overlap corr ≈0 at all halos; cross-seam derived-quantity error −0.51). Fix:
  **conditioning-by-kriging** `x_c = x_u + Σ_cross Σ_shared⁻¹ (x_shared − x_u|S)`, each tile
  conditioned toward ONE global node-space realization via a single forward sweep
  (values-handed-forward, NOT seed-shared; transitive by construction for a tile chain).
  Cross-cov blocks `Σ_{·,S}` = full `Q⁻¹` columns via **factor back-solves** (outside Takahashi's
  pattern; computed once per tile, reused across members). **Validity invariant:** corrected
  draws are exact posterior samples (kriging-preserves-conditional-law theorem), verified by a
  **joint-covariance** oracle on a dense small grid — marginal checks are the blind spot.
  **Separator precondition (asserted, checked):** the handed-forward overlap must Q-graph-separate
  processed/unprocessed interiors (overlap ≥ stencil reach = 2 for α=2; the `k·corr_len` halo
  policy satisfies it); a negative control proves the joint law breaks when it doesn't. **Exact
  only for tree-structured tile adjacency** — 2-D/FEM (Phase 4) needs the documented
  pre-drawn-joint or junction-tree variant. The marginal `σ=Σwσ` bound is unchanged
  (pointwise-conservative; only the *sampler* changes). Plan:
  `docs/superpowers/plans/2026-06-25-phase3-task9-gmrf-kriging-sampler.md`.

## Cross-cutting decisions (canonical — Phase 2)

- **Coherent-sample structured driver = shared-overlap-basis (Löwdin), NOT member-only z_r.**
  The design's default Option-1 (member-only `z_r` applied to each tile's own factor) was
  escalated and rejected at the Stage-A gate (design §8). Diagnostics proved it was NOT a
  sampler bug (diagonal exact; core/aligned ≈ MC floor) but a genuine, *large, k-independent*
  basis-orientation residual: each tile builds an independent rank-20 randomized-SVD basis, so
  the structured factors are ~orthogonal across tiles (structured ratio ≈ 0.39) and member-only
  `z_r` makes them add as if independent → coherent samples underdispersed ~40–67% vs the
  reported cheap-path variance, *growing* with k. Fix (`coherent_structured_field` in
  `distributions/coherent.py`, used by `BlendedDistribution._coherent_member`): project every
  tile factor into ONE common orthonormal basis `Q` (QR of the stacked factors over the
  support), take the symmetric square root `Aᵢ=(QᵀFᵢ Fᵢᵀ Q)^½` to strip the SVD rotational
  ambiguity, and drive `G=Σ wᵢ Q Aᵢ` with ONE shared member-seeded latent `g`. Result: cheap≈
  sampled rel 0.45→0.03 and k-direction flipped growing→flat; cross-seam derivative recovers.
  The reported marginal (`BlendOperator.blend`'s `(Σwσ)²`) is UNCHANGED (still conservative;
  Task-3 cheap path untouched) — only the *sampler* changed. `MemberSeededZr`/`realize_one`
  remain for single-tile use. If Stage B's larger overlaps degrade `Q` conditioning, the next
  lever is the retained per-tile rank, NOT the driver (owner directive).
- **`run_tiled_pipeline`** (`application/pipeline.py`) reuses Phase-1 `_prepare`/evaluators:
  per-tile obs windowed to `extended_window`, eval locations windowed per tile, one submit per
  tile via the existing `Executor`, grid blend + OSE eval-point `PointSet` blend, then the
  Phase-1 `Registry`. OSSE scores the blended grid vs truth; OSE scores blended eval-point
  predictives vs withheld CryoSat-2. `UnitOfWork.obs` relaxed to `ObsWindow | None` (None only
  for obs-less coordinator probes in tests; real solves always set it).

## Gotchas

- **mypy runs `mypy .` (whole tree, tests included)** via the pre-commit hook — test files
  must be type-clean too (e.g. assert `x is not None` before using an `Optional`). numpy ops
  often infer `Any`; wrap returns in `np.asarray(...)` to satisfy `no-any-return`. scipy/dask/
  distributed calls need `# type: ignore[import-untyped]` / `[no-untyped-call]`.
- **Plan deviations made & verified:** (1) Task 10 perturb_and_ensemble seeds members from the
  caller seed + index, not `id(obs)` (the plan's id-based seed broke the reproducibility test).
  (2) Task 19 CRPS test: the plan's expected `0.23379` is CRPS at y=0, but the test uses y=0.5;
  correct closed-form value is `0.331404`. Implementation formula is the standard correct CRPS.
  (3) Task 19/21: evaluators take `result: object` (not `dict[...]`) so they conform to the
  `Evaluator` protocol and can go into `Registry([...])`. (4) Task 21 `_evaluate`: OSSE runs
  calibration on the gridded truth (the plan only set TRUTH, so Calibration — which needs
  WITHHELD_OBS — would never fire and the OSSE acceptance demands reduced_chi2/coverage); OSE
  withholds CryoSat-2 by mission-splitting the obs window (the test passes a plain FixtureSource
  with no `withheld()` method, so withholding must happen in the pipeline, not the source).

- **Task-1 deviation (verified):** `.gitignore` never ignored `__pycache__`/`*.pyc`, so Phase 1
  left 77 `.pyc` files tracked. The rename swept them in; untracked them (`git rm --cached`) and
  added `__pycache__/`, `*.pyc`, `.mypy_cache/` to `.gitignore` so the soon-public repo stays
  clean. `pixi.lock` (593 KB) exceeds the 500 KB hook only under `--all-files`; it is unmodified
  so the staged-only commit hook passes.
- The 11 GB NATL60 reference is hourly — never pull it; use the daily file. Footprint stays a
  few hundred MB.
- NATL60 challenge has no observation error ⇒ `R` ≈ a nugget for the oracle.
- `pyinterp` / `GPSat` are NOT installed; Method 1 needs none. `pixi add` any new dep.
- BLAS/OpenMP env vars must be set per-worker *before* numpy/BLAS loads (Nanny child env).
- **Phase-2 Task 11 deviation (verified):** `ScaleAwareHalo.halo_for` evaluates the
  correlation length at the band's *equatorward-most* latitude (`clamp(0, lat_lo, lat_hi)`),
  not at the band's lat nodes as the plan literal showed. The plan test asserts the halo for
  band (-5,5) equals `k*800` (equator cl), which the node-based version (cl at ±5 ≈ 797)
  would miss. Correlation length is monotone-decreasing in |lat|, so the widest over a band
  is at min|lat| — this is the correct "widest over the core band".
- **Phase-2 Task 6 deviation (verified):** `FirstDifference._diff_var` calls
  `dist.covariance(a,a/b,b/a,b)` node-by-node; the naive general-path covariance
  (regenerate 256 members per query point) made the composition test take 67s. Fix:
  `BlendedDistribution.covariance` now snaps query points to nearest grid nodes and reads
  from one cached `_grid_sample_batch(256)` realization (lazily computed, memoized on the
  instance). 67s → ~4s. Snapping is consistent with `PersistedDistribution.covariance`
  (which also snaps via `_idx`); fine for grid-node derived ops. The plan explicitly
  allowed this fast path (Task 6 Step 3).

- **Phase-3 Task-7 addition (verified):** `solve_unit` (`application/solve.py`) now dispatches the
  base distribution on `unit.base_fields` type — `PrecisionFields → PrecisionDistribution`, else
  `PersistedDistribution`. The plan's Task-7 file list omitted solve.py, but widening
  `ReducedUnit.base_fields` to `PersistedFields | PrecisionFields` forced it (and it is *required*
  for genuine-first-class GMRF to flow through the executor into the Task-9 blend as a
  `PrecisionDistribution`, not silently wrapped in `PersistedDistribution`). `PerTimeProduct.base`
  is typed `Any`, so no product-type churn. `PrecisionDistribution._factor_obj` is annotated via a
  `TYPE_CHECKING` import of `GMRFFactor` (ANN401 forbids `-> Any`); the runtime import stays lazy so
  `persisted.py` does not hard-require sksparse.
- **Phase-3 Task-5 deviation (verified) — sksparse 0.5.0 has a NEW scipy-style API.**
  `pixi add scikit-sparse` installed **scikit-sparse 0.5.0**, a rewrite — NOT the classic
  0.4.x `Factor` object the plan assumed. The plan's `cholesky(Q, ordering_method=..., mode=
  "simplicial")` + `factor.L_D()`/`.P()`/`.solve_Lt()`/`.apply_Pt()` DO NOT EXIST. Real API:
  `from sksparse.cholmod import cho_factor`; `cf = cho_factor(Q, order="amd", lower=True)`
  returns a `CholeskyFactor` with `cf.L` (sparse lower, `L Lᵀ = Q[P][:,P]`, `is_ll=True` for
  SPD), `cf.D`, `cf.perm` (the permutation P, factor is of the *permuted* matrix
  `Q[perm][:,perm]`), `cf.solve(b)` solves `Q x = b` (perm internal), `cf.is_ll`.
  `GMRFFactor` (`methods/gmrf_linalg.py`) wraps this: deterministic perm via `order="amd"`;
  one lower `Lc` (`cf.L`, or `cf.L·√diag(D)` if a future matrix factors LDLᵀ) drives sample
  (`spsolve_triangular(Lcᵀ, w)` then scatter `x[perm]=y`), Takahashi, and the back-map.
  **Permutation back-map indexes by `perm` directly** (NOT `argsort(perm)` as the plan's snippet
  did): original entry `(perm[k], perm[l])` carries permuted value `(k,l)`. Pinned correct by
  the dense-Q⁻¹ oracle (diag + adjacent rtol 1e-9). Takahashi recursion math is verbatim plan.
- **Phase-3 Task-2 deviation (verified):** widening `BlendInput.distribution` to the abstract
  `PredictiveDistribution` protocol (which declares only `grid`/`provenance`/`marginal_variance`/
  `covariance`/`sample`/`regrid`) means the duck-typed `.fields`/`.time_days` reads in `blend.py`
  (`_constituent_moments`, `_coherent_member`, `BlendOperator.blend`) need `cast(Any, dist)` to
  pass `mypy .`; the `PersistedPoints` eval-point constituent in `pipeline.py` is `cast(
  PredictiveDistribution, pp)` at the `BlendInput(...)` call (it exposes the fields by duck
  typing but isn't a structural match). The Stage-A seam test imports `_nearest` from
  `distributions.coherent` (where it now lives) not `distributions.blend` — mypy's
  `--no-implicit-reexport` rejects the re-exported name. The plan literal said import from blend;
  importing from coherent is equivalent (same function) and the only change vs the plan text.

- **Phase-3 Task-9b finding (load-bearing) — GMRF kriging sweep uses INDEPENDENT per-tile
  white, NOT the shared-lattice `diagonal_noise`.** The kriging theorem requires each tile's
  *unconditional* draw to be independent of the handed-forward target values. The old
  native-shared-w mechanism shared white across tiles by global cell, which correlated each
  tile's draw with the targets and **biased** the correction (spurious long-range correlation;
  the per-tile-validity oracle caught it). `GmrfKrigingSolve._sweep` now seeds white per tile via
  `derive_seed(method, params, f"gmrf-tile:{pos}", member)`. The single-tile coherent-member
  tests assert against this per-tile white (NOT `diagonal_noise`). `diagonal_noise` is still used
  by `LowRankSharedBasis` (OI), unchanged.
- **Phase-3 Task-9c finding — negative-control fixture limitation (recorded so 9d/Phase-4 don't
  re-derive it).** The separator assertion (`overlap ≥ reach=2`) is a STRUCTURAL *sufficient*
  condition for joint exactness at all κ — correctly conservative. Demonstrating "1-col overlap →
  wrong joint" with the exact-marginal fixture is regime-dependent: at well-conditioned κ (≈0.7)
  a 1-col overlap is *benign* (short correlation ⇒ the distance-2 precision edge barely affects
  the joint), and the long-correlation regime where it genuinely breaks makes the
  `inv(Σ_global[tile,tile])` construction ill-conditioned (double-inverse of a near-singular Σ).
  So `test_separator_negative_control` proves wrongness via the **weighted-blend seam-column
  collapse** (a 1-col overlap leaves no room for the partition-of-unity crossfade → seam variance
  collapses; joint Frobenius ≫ MC) **plus** the assertion firing — both real reasons the
  `≥reach` policy holds. The positive joint-cov oracles (≥2-col) match global EXACTLY; the chain
  construction is sound.

## Deferred items / open questions

- **Next release — relax the conda recipe Python cap.** `pyproject.toml` now declares
  `requires-python = ">=3.12"` (cap dropped, commit `e236591`; source uses only stable stdlib
  and numpy/scipy/pyproj all ship cp314 wheels). The **0.1.0** recipe deliberately keeps
  `run: python >={{ python_min }},<3.14` to match the already-published 0.1.0 wheel (building
  0.1.0 on 3.14 would fail `pip install .` — its metadata excludes 3.14). On the next release:
  when the autotick bot opens the feedstock bump PR, drop the `,<3.14` from the `run` pin
  (→ `python >={{ python_min }}`) and mirror the same in `conda-recipe/meta.yaml`. Do NOT do
  this before a `>=3.12` wheel is on PyPI.
- **Optional:** `pixi.toml` dev pin still `python = ">=3.12,<3.14"` (left capped to avoid a
  `pixi.lock` re-solve; doesn't limit the published package). Relax only if CI should exercise 3.14.
