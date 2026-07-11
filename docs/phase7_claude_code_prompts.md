# Phase 7 (MIOST) — Claude Code prompts (historical record)

**Provenance.** Reconstructed verbatim on 2026-07-10 from the review-layer conversation. Unlike
phases 1–5, Phase 7 had no assistant-authored `scope_spec` file: the method source of truth is the
committed, owner-verified method brief, and the design spec was authored in-repo by Claude Code
under the brainstorming skill. The prompts below were sent as owner paste blocks, in the order
given. Phase 7 was deliberately split into sessions: comprehension (brief) → validation-strategy
decision + cost probe → design → plan → execution.

**In-repo artifacts of record:**
- Method brief: `docs/papers/2026-07-02-miost-method-brief.md` (verified end-to-end: reviewer
  tiers + owner PDF spot-check, ALL PASS)
- Spec: `docs/superpowers/specs/2026-07-03-phase7-miost-design.md`
- Plan: `docs/superpowers/plans/2026-07-03-phase7-miost.md` (+ `.tasks.json`)
- Validation strategy + probe results: `PROGRESS.md` "MIOST Stage-A validation strategy —
  OWNER-DECIDED 2026-07-03"; `scripts/probe_miost_cost.py`

Numerous mid-flight fork-decision and gate-decision blocks (discrete knobs, temporal windowing,
harness fit, Stage-B representation, section approvals, Task-11/13/19/20 gates) are not reproduced
here; their outcomes are recorded in the spec's decision register (D1–D8), the plan, and
`PROGRESS.md`.

---

## 1. Comprehension-session prompt — the method brief (sent c. 2026-07-02; plain session, no skill)

Context: sent as a plain session (not brainstorming — deliberately, since no design was wanted).
An earlier draft of this prompt mis-stated Ballarotta 2023 as "the maps the validation is
benchmarked against" and assumed one paper was primary; this final version corrected both.

```text
GOAL OF THIS SESSION: build a FAITHFUL, VERIFIABLE understanding of the MIOST method family — NOT a design,
NOT a sverdrup integration. (The eventual goal — NOT this session's — is implementing MIOST as a sverdrup
method scored on the same 2021a harness as OI/GMRF.) This session produces only the understanding that a
later design session will rest on. Do not propose code or sverdrup changes.

DELIVERABLE: a method brief COMMITTED to docs/papers/2026-07-02-miost-method-brief.md. An uncommitted brief
is not a deliverable — authoritative artifacts are versioned, and since the PDFs themselves are not pushed,
this brief will be the only versioned account of what they say. I will review it against the PDFs before any
design session happens.

SOURCES: the three local PDFs in docs/papers (Ubelmann 2021; Ubelmann 2022; Ballarotta 2023). Work from these;
the sandbox blocks most external fetches. If something load-bearing isn't in them, FLAG the gap explicitly —
do not fill it from memory or by guessing.

SCOPING (ask me before going deep — do not skip): these papers are stages of ONE evolving method family, not
three methods — a multiscale-inversion core plus components accreted over time (Doppler/current reconstruction
in U2021; coherent internal tides in U2022; the operational multi-component product with drifter ingestion in
B2023). The scoping question is therefore WHICH COMPONENT SUBSET is the implementation target, not "which
paper." My working intent: the minimal mesoscale, altimetry-only SSH configuration — the core that matches
sverdrup's 2021a Gulf Stream target — with internal tides, equatorial waves, Doppler currents, and drifters
out of scope initially. Confirm or correct that with me first. Then IDENTIFY, with citations, where each piece
of the core machinery is actually documented across the three papers (do not assume one paper is primary).

THE BRIEF must:
1. Characterize the core method with SPECIFIC citations (paper + section/equation/figure) for every
   load-bearing claim: the state decomposition (components; the wavelet-like basis — scales, spacing, support;
   and HOW TIME IS HANDLED / how space-time covariance is encoded per component), the observation operator,
   the cost function / estimator, the solver (+ preconditioning), and the computational shape (basis size,
   problem sizes, how it scales to global — any domain decomposition).
2. Extract the operational configuration the papers report for the challenge-relevant setup: scales,
   covariance/variance parameters, obs-error treatment, input missions + preprocessing/corrections — marked
   per-paper.
3. Map MIOST's OUTPUT onto sverdrup's capability taxonomy (you may read core/method.py::UncertaintyCapability
   and core/distribution.py for the contract names — no broader codebase survey): what do the papers DOCUMENT
   it producing — POINT only? any formal-error / MARGINAL_VARIANCE product? anything like COVARIANCE/SAMPLES?
   Be honest if it is mean-only as documented. You may add ONE clearly-marked-INFERENCE paragraph on what the
   linear-Gaussian reduced-basis structure implies in principle (a posterior exists in coefficient space) —
   but do NOT design how to expose it; "mean-only as shipped" is an acceptable honest answer and would reframe
   MIOST as a baseline/comparison target rather than a Method peer. That decision is mine, later.
4. Relate the estimator to classical OI (clearly marked as analysis, not paper claim): is MIOST a reduced-rank
   formulation of the same linear-Gaussian problem sverdrup's OI solves, with the covariance implied by the
   basis? This positioning feeds the later Method-peer-vs-baseline decision.
5. Record the validation anchor: what the papers report on 2021a-class metrics, and the MIOST row already in
   the vendored leaderboard (vendor/2021a_SSH_mapping_OSE README: MIOST mu=0.89, sigma=0.08, lambda_x=139 km,
   with example_eval_miost.ipynb) as the eventual acceptance reference for any sverdrup MIOST.
6. SEPARATE throughout: what the papers DOCUMENT vs what YOU INFER about details they leave open. Mark
   inference as inference; mark uncertainty instead of smoothing it.

Do not read the wider sverdrup codebase beyond the two files named in (3). The design-fit session is separate
and comes only after I've reviewed the committed brief against the papers. Stop at the brief and hand it to me.
```

---

## 2. Validation-strategy decision + Task-0 cost probe (sent c. 2026-07-03; final corrected version)

Context: an earlier version of item 3 instructed a manual AVISO-credentialed download; the owner's
"read the download scripts first" check corrected it — the committed 2021a reproducer already
carried the MIOST maps file (manifest entry #11, SHA256-pinned) from the unauthenticated MEOM
mirror. This is the version as sent.

```text
MIOST Stage-A validation strategy — DECIDED (record in PROGRESS as the design-session input; design
prompt comes next, separately):

1. RECORD the validation-tier decision:
   - Tier 1 (exact oracles, the correctness proof): duality oracle — dense obs-space OI with
     B = Γ Q Γᵀ vs matrix-free reduced normal equations (U2021 Eq.2 ↔ Eq.15) must agree to tight
     rtol on a small synthetic; adjoint identity <Gη,r> = <η,Gᵀr>; dense-vs-PCG on small A.
   - Tier 2 (documented properties): representer with negative lobe (U2022 Fig.4), hard compact
     support, 80–800 km span.
   - Tier 3 (similarity, NEVER a gate): compare our maps to the distributed
     dc_maps/OSE_ssh_mapping_MIOST.nc (RMS diff, spectral coherence), reported as a diagnostic.
     Provenance note: that file is SHA256-pinned in the committed 2021a manifest
     (e58caea7..., 29,804,673 bytes), so the comparison target is exact and reproducible.
   - Tier 4 (THE GATE): the existing 2021a harness, identical to OI/GMRF. Gaps #1–5 become the
     parameter_space (spacing α, n_dir, Q scale/slope, R, λ_min) closed by the Phase-5 loop on the
     blocked validation track; c2 once at acceptance; HARD FLOOR = BASELINE 0.85; MIOST row
     (0.89/0.08/139) = ASPIRATIONAL anchor, never a hard gate. Calibration bar recorded
     N/A-for-POINT (capability-conditional).
   - State explicitly: pointwise reproduction of the MIOST maps is impossible IN PRINCIPLE
     (undocumented config, no public code) and is NOT a criterion at any tier.

2. RECORD the execution decision: SkyPilot is NOT a Stage-A prerequisite. Validation runs locally.
   Escalation ladder if tuning throughput demands it later: numba/stored-G optimization → shorter
   temporal windows → existing dask address-only seam to a bigger box → SkyPilot as its own
   milestone. Reopen only if the Task-0 probe + early tuning show ONLY the expensive corner
   (α≤0.5, 12-dir, full-year single window) clears the BASELINE floor.

3. MIOST MAPS FILE — use the EXISTING committed reproducer (no new script, no credentials; the
   AVISO THREDDS is dead per validation/access.py and the live MEOM mirror is unauthenticated;
   dc_maps/OSE_ssh_mapping_MIOST.nc is ALREADY manifest entry #11 of
   src/sverdrup/validation/download_ssh_mapping_data_challenge_2021a.py):
   a. Run: python -m sverdrup.validation.download_ssh_mapping_data_challenge_2021a
      (idempotent: verifies SHA256 of present files, fetches only what's missing).
   b. Report the per-file [skipped|downloaded] statuses; confirm dc_maps/OSE_ssh_mapping_MIOST.nc
      is present + hash-verified.
   c. Open it (xarray) and RECORD its output-config facts for the Tier-3 design input: grid extent,
      resolution, time coverage/cadence, variables. Metadata inspection only — no method inference.

4. TASK-0 COST PROBE (measure before design; COMMIT the script — the FEM uncommitted-probe lesson):
   scripts/probe_miost_cost.py that (a) counts the ACTUAL local obs per mission and per window from
   data/2021a_ssh_mapping_ose/dc_obs/*.nc (the 6 training missions; c2 excluded — eval only);
   (b) computes N_coef, nnz(G), stored-G bytes, and matrix-free flops/apply over a grid of
   (spacing α ∈ {0.5, 0.75, 1.0, 1.5}, n_dir ∈ {8, 12}, window ∈ {60 d, 365 d},
   λ_min ∈ {80, 113} km) using: positions/scale = (D/(αλ))², per-obs overlaps/scale =
   (3/α)²·n_dir·2·(2L_t/Δt), L = 1.5λ, L_t = 10 d, Δt = 5 d, scales geometric 80→800 km;
   (c) MICRO-BENCHMARKS vectorized basis evaluation (cos-product) throughput on this box to replace
   the assumed 20 GFLOP/s with a measured number; (d) prints the feasibility table + a recommended
   local operating envelope. Report the table back. No method code, no design — measurement only.

Then STOP. The design-session prompt (staged Stage A/B milestone, six ensemble-ready seams,
capability-conditional calibration bar, this validation stack baked in) is written next, after the
probe's numbers are in.
```

---

## 3. The Phase-7 design-session prompt (sent c. 2026-07-03; the Phase-7 equivalent of a `claude_code_prompt` file)

```text
/superpowers-extended-cc:brainstorming

GOAL: design "Phase 7 — MIOST" — the MIOST-family multiscale-inversion method as a sverdrup Method,
as ONE milestone with TWO hard-gated stages:
  Stage A: MIOST-as-documented (native_capability = POINT), built ensemble-ready via six required
           seams, accepted on the 2021a harness (µ/λx) with calibration recorded N/A-for-POINT.
  Stage B: ensemble posterior via perturbed-observation solves — capability upgrade to
           SAMPLES/COVARIANCE/MARGINAL_VARIANCE — accepted on calibration, with Stage-A mean
           provably unchanged.
This is a design session: clarifying questions one at a time, then design sections for my review,
then commit the spec to docs/superpowers/specs/2026-07-03-phase7-miost-design.md and STOP before
writing-plans.

GOVERNING INPUTS (read first; they are settled — do not redecide):
- docs/papers/2026-07-02-miost-method-brief.md (verified end-to-end; the method source of truth).
- PROGRESS.md "MIOST Stage-A validation strategy — OWNER-DECIDED 2026-07-03" (the four validation
  tiers + SkyPilot decision) and the Task-0 probe results section.
- scripts/probe_miost_cost.py (committed, tested sizing functions + measured benchmarks).
- The Phase-5 tuning framework (application/tuning/), core/types.py + core/method.py +
  core/distribution.py, validation/run.py + their_eval.py + the download reproducer,
  distributions/blend.py (the hand-off blend philosophy), methods/registry.py.

MEASURED CONSTRAINTS (from Task-0 — treat as requirements, not suggestions):
- Stored-G CSR is the DEFAULT solve path (527 M nnz/s measured); naive numpy matrix-free is
  excluded (10 M elem/s, 50× slower). Numba matrix-free = escalation rung 1 (noted, not built).
- RAM binds, not compute: stored-G budget ≤ 8 GB. Local operating envelope: 60-day windows across
  the (α, n_dir, λ_min) grid except α=0.5+12-dir; full-year single-window only at α=1.5.
- Obs (in-box, c2 excluded): 39,666 / 60 d; 208,542 / 365 d. j2g contributes ZERO obs Jan–Feb
  (geodetic phase) and j2n only ~10.8k/yr: windows with mission-absent or thin coverage are NORMAL
  and must be handled gracefully (explicit test).

REQUIRED DESIGN ELEMENTS:
1. The method core per the brief: wavelet dictionary (U2021 Eqs. 18–19 exactly: cosine plane-wave
   carrier, NO ωt term; separable cos(πδ/2) taper, hard compact support; L = 1.5λ; sine/cosine
   phase pairs), diagonal Q from a spectrum parameterization, diagonal R, analytic G assembly
   (columns filled from the basis formula at obs coords — never through a gridded H), reduced
   normal equations (GᵀR⁻¹G + Q⁻¹)η = GᵀR⁻¹y, PCG. Register "miost" in methods/registry.py.
2. THE SIX ENSEMBLE-READY SEAMS, each tested AS a seam in Stage A:
   a. RHS-agnostic solver: solve(b) is a pure function of the right-hand side, multi-RHS capable.
      Unit test: solve accepts an arbitrary b (not derived from y).
   b. RHS construction as its own unit: b(y) = GᵀR⁻¹y, with G-apply and Gᵀ-apply first-class.
   c. Q and R as explicit diagonal objects with named, documented parameterization.
   d. Persisted state = coefficient vector η^a + basis spec; grid maps and arbitrary-point queries
      derived via analytic Γ evaluation (fits the on-demand-covariance invariant).
   e. native_capability = POINT behind the unchanged Method/PredictiveDistribution protocols;
      Stage B swaps in an ensemble-backed PredictiveDistribution; protocols untouched.
   f. Seeding via derive_seed + PCG convergence tolerance as named, recorded parameters from day
      one (the tolerance joins the statistical contract in Stage B).
3. Temporal windowing + blend (our feasibility adaptation — state it honestly as such): window
   length W and overlap as named parameters (overlap ≥ L_t = 10 d); linear blend in the overlap
   with weight proportional to boundary distance (the U2022 §3.2.3 pattern, applied in time;
   U2021's single-window regional precedent noted). Use the dc_obs temporal margins (files span
   2016-12-01→2018-01-31) for edge windows; spatial obs margin from the 30° file extent for
   edge-element support. Candidate diagnostic (optional): windowed-vs-single-window equivalence
   on a small case. Check the probe's pavement-extent assumption (D = box only?) and extend sizing
   to per-scale support margins if needed (small effect; be honest about it).
4. RESOURCE-FEASIBILITY PREDICATE for the tuner: a pluggable FeasibilityPredicate (invariant 5)
   that excludes, BEFORE solve (invariant 3), any trial whose predicted stored-G exceeds the
   memory budget — cost model = the probe's committed, tested sizing functions. Budget a named
   parameter (default 8 GB). This composes with (does not replace) existing predicates.
5. parameter_space for Tier-4 tuning: continuous knobs {α spacing fraction, Q scale, Q slope, R,
   optionally L_t} as scalar boxes; discrete knobs (n_dir, λ_min, scale ratio) FIXED per run and
   recorded (recommend n_dir=8, λ_min=80 km, ratio √2), since ParameterSpace is scalar-box-only
   (Phase-5 invariant 12). The √2 ratio is an ASSUMPTION, not from the papers (brief gap #1) —
   name it, record it, flag it in the spec. Surface this discrete-knob decision at a checkpoint.
6. Harness integration: a run_challenge_map-style entry for method="miost" producing daily 2017
   maps on the existing harness grid (Tier 4 unchanged); regrid only for the Tier-3 comparison
   against the pinned dc_maps/OSE_ssh_mapping_MIOST.nc (0.1°, 101×101, daily, ssh-only —
   metadata recorded in PROGRESS).

STAGE-B SPECIFICATION (design now, build after Stage-A gate):
- Sampling = perturbed-observation / sample-then-optimize, EXACT for this linear-Gaussian model:
  draw ε′ ~ N(0,R), η̃ ~ N(0,Q) (both diagonal — trivial), solve A η_s = GᵀR⁻¹(y+ε′) + Q⁻¹η̃ with
  the SAME solve(b). Mean of η_s = η^a; covariance = A⁻¹ = the exact posterior (two-line check in
  the spec; mark as standard analysis, with U2022's "parameter space … projectable in physical
  space" future-work sentence cited as the family's own pointer). m members = m extra solves,
  embarrassingly parallel; field samples/queries via Γη_s.
- Capability upgrade declared: SAMPLES native; MARGINAL_VARIANCE + COVARIANCE by ensemble
  reduction. State the MC error explicitly (relative variance error ~ √(2/(m−1))); m a named
  parameter. Note (deferred, not built): exact marginals via assembled sparse A + the
  pattern-agnostic Takahashi reduction verified in Phase 6.
- PCG tolerance is part of the statistical contract: an under-converged member is a biased draw —
  design a test for it.
- Stage-B acceptance: the existing Calibration evaluators (reduced_chi2, coverage_1sigma, crps)
  on the harness, same train/validation/locked-c2 discipline; PLUS a non-regression test that
  Stage-B code leaves the Stage-A mean map unchanged (the unperturbed solve is untouched by
  construction — prove it).
- Multi-tile/global coherence questions are OUT: single-window/temporally-blended regional product
  only; the Stage-C capability-conditional predicate applies verbatim if ever tiled spatially.

VALIDATION STACK (owner-decided; bake into the test plan and acceptance criteria verbatim):
- Tier 1 exact oracles: duality oracle (dense obs-space OI with B = ΓQΓᵀ vs the reduced
  normal-equations path — U2021 Eq. 2 ↔ Eq. 15 — tight rtol on a small synthetic); adjoint
  identity ⟨Gη, r⟩ = ⟨η, Gᵀr⟩; dense-vs-PCG on a small A.
- Tier 2 documented properties: representer with negative lobe (U2022 Fig. 4), hard compact
  support, 80–800 km span.
- Tier 3 similarity vs the SHA256-pinned MIOST maps: RMS diff + spectral coherence, reported as a
  DIAGNOSTIC, never a gate.
- Tier 4 THE GATE: Phase-5 loop tunes the parameter_space on the blocked validation track;
  BASELINE 0.85 = hard floor; MIOST row (0.89/0.08/139) = aspirational anchor, never a hard gate;
  c2 touched once at acceptance; calibration bar capability-conditional (N/A-for-POINT in Stage A,
  binding in Stage B).
- State in the spec: pointwise reproduction of the distributed MIOST maps is impossible IN
  PRINCIPLE (undocumented config, no public code) and is not a criterion at any tier; the product
  is FAMILY-FAITHFUL and tuned-in-framework.

OUT OF SCOPE (state, don't build): SkyPilot / remote execution (escalation ladder recorded in
PROGRESS; reopen condition is now a MEMORY question); internal tides, equatorial waves, Doppler,
drifters (brief §4); spatial multi-tile MIOST; numba matrix-free (rung 1, noted); exact-Takahashi
marginals (noted).

PROCESS: follow the brainstorming skill — clarifying questions one at a time (the discrete-knob
decision in #5 and the window-length default are genuine ones), then present the design in
sections for my approval, then write + self-review the spec, commit it, and STOP for my review
before writing-plans. Also: resolve the blocked git push (SSH host-key) so the public repo
reflects HEAD — the external review verifies against it.
```

---

## 4. Plan review — the Task-6 right-edge correction gating execution (sent c. 2026-07-03/04)

Context: the plan review found the window placement `s_k = −18 + 45k, k=0..8` unsatisfiable at the
right data edge (window 8 demanded obs 19 days past the data end under the normative span assert);
the correction below restored the spec's own placement sketch and gated execution.

```text
Phase-7 plan review — APPROVED AFTER ONE REQUIRED CORRECTION (Task 6). Fold the correction, commit,
then execution is green-lit.

REQUIRED — Task 6 right-edge placement (as written, every full-year run crashes at window 8):
- Window 8 [342, 402] demands obs spanning [330, 414] at L_t_max=12 (the NORMATIVE §4.2 span
  assert, implemented in Task 8's _window_obs) — but obs end at day 395 (2018-01-31). Unsatisfiable.
- FIX: keep k=0..7 (s_k = −18+45k); RIGHT-ALIGN the last window: s_8 = 395 − 12 − 60 − 1 = 322 →
  [322, 382] (ends 2018-01-18, restoring the spec §4.1 sketch "≈2018-01-14"). Right slack = 1 day
  (382+12 = 394 ≤ 395), symmetric with the left.
- CONSEQUENT FIX (current code fails partition-of-unity once corrected): overlap(7,8) = 35 d, so
  generalize the blend denominator from V_DAYS to the ACTUAL pairwise overlap
  (left.end − right.start); reduces to /15 on interior pairs; constraint restated as "every
  pairwise overlap ≥ L_t_max" (15, 35 ≥ 12 ✓).
- TESTS: update test_placement_s_k to the new starts; REMOVE both escape hatches
  (`or w is windows[0]` / `windows[-1]`) — assert two-sided support unconditionally for ALL output
  days 0..364; ADD the right-slack assertion (windows[-1].end_day + 12 ≤ 395 − 1 + eps) mirroring
  the left; keep the partition test sampling through [322, 357] (it must FAIL before the denominator
  generalization and pass after).
- WindowPlan gains the data-span constants (OBS_END_DAY=395, L_T_MAX=12) beside the run-constants;
  grep the plan/tasks for any other hardcoded 342/402 and update. Verified for you: coverage of days
  358–364 holds two-sided (slots ≤ 376 ≤ 382; data support ≤ 394); no triple-cover (window 6 ends
  312 < 322); window ids derive from start_day so cache keys stay distinct.

SECONDARY (confirm during the same commit):
1. Task 13 claims BO(n=16, rounds=4) — the Phase-5 carried follow-up (a) says rounds is NOT yet
   threaded through _run_stage (BO currently rounds=1). Either verify that follow-up landed, or fix
   it as Task-13 prep, or the runner must not claim rounds=4. Also do not inherit follow-up (b)'s
   pattern (stage_b gate test ERRORS on smoke via Sobol StageANoAdmissible) into
   stage_miost_gate_run/its pytest gate — design the smoke path to skip/pass cleanly.
2. Sketch regions (Tasks 7/8 `...`): executor treats them as pinned by the SAME task's tests + prose
   — no invented behavior; mean_at/regrid must route through the analytic Γ/S path (seam-d test
   enforces; no nearest-node shortcut).

PROCESS:
- PUSH before execution (manual again if needed): origin is at 13a1731; spec + plan commits are
  local-only, and execution adds ~19 tasks of commits my review cannot see otherwise. The
  credential/host-key fix is now a real chore — schedule it.
- EXECUTION MODE: fresh executing-plans session (not subagent-in-this-session) — matches every
  prior phase, clean context budget for a 19-task build, and the committed plan+spec+PROGRESS are
  the complete handoff. Gates 11/13/19 stop for owner sign-off regardless.

After the Task-6 correction is committed (and pushed), kick off execution.
```
