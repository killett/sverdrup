# Pre-Phase-14 PROGRESS trail archive (MIOST brief, Stage-A/B/C, autotune, OI validation)

**What this is.** The older, unquoted sections that sat in PROGRESS.md between the Phase-14
CURRENT STATE block (and its archived trail pointer) and the canonical `Current work` index —
the MIOST method brief (2026-07-02), the Stage-A validation strategy, the Stage-C redesign
brief and locked decisions, the 2026-06-30/07-01 measurements, the conda feedstock watch item,
and the successive `RESUME HERE` blocks from Phase 5 and Stage B — **moved here verbatim on
2026-09-18** (owner pin 207) from PROGRESS.md as of commit `2530bb2`, lines 544–1599.
Moved, not rewritten: the byte content below is exactly what PROGRESS.md carried. Every
`RESUME HERE` block here is SUPERSEDED — do not act on any of them; PROGRESS.md's CURRENT
STATE block is the only block describing now (pin 154).

**Why moved.** Same reason as `phase14-stage1-trail.md`: PROGRESS.md is an index plus
canonical sections (CLAUDE.md durability rules), and superseded resume blocks are neither.
Migrate, don't duplicate: nothing here is repeated in PROGRESS.md.

---

## MIOST method brief COMMITTED (2026-07-02) — awaiting owner review before any design session

Understanding-only session (no code, no design): produced
`docs/papers/2026-07-02-miost-method-brief.md` — a citation-pinned account of the
MIOST family (Ubelmann 2021 / Ubelmann 2022 / Ballarotta 2023, PDFs local in
`docs/papers/`, NOT committed). Owner-confirmed scope: minimal mesoscale
altimetry-only SSH core (tides/eq-waves/Doppler/drifters out of scope, half-page
inventories each). Load-bearing outcomes: MIOST-as-documented is POINT-only (no
uncertainty product in any paper; U2022 names it future work) → baseline-vs-Method-peer
decision is the owner's, later; core = reduced-rank OI (B=ΓQΓᵀ wavelets, matrix-free
PCG on GᵀR⁻¹G+Q⁻¹); §8 gaps register lists what NO paper specifies (element spacing,
direction count, Q calibration, R values, preconditioner, the 2021a-submission
config). Acceptance anchor: vendored leaderboard MIOST row μ=0.89/σ=0.08/λx=139.
Working artifacts (`docs/papers/`): `*.extraction.md` per paper + `*.pdftext.txt` raw
dumps — **INTENTIONALLY uncommitted + gitignored** (public repo; full-text
transcriptions = republishing; U2021 license unverified). Do NOT "fix" by committing.
**REVIEWED AND ACCEPTED (owner, 2026-07-02) at every reachable tier** — quotes
faithful, repo contract refs verified (`core/types.py:15`, `core/method.py:20`),
leaderboard row verified; recorded in brief §10. Amended same day: §8 gap-closure
status (NO public MIOST implementation exists — products only on Zenodo/AVISO; GitHub
negative on method/author/ODC org; closure = authors/AVISO handbook OR tune-as-
parameter_space via Phase-5 loop, owner's call at design time) + §7 honesty
consequence (sverdrup MIOST = family-faithful tuned-in-framework, NOT a CLS
reproduction; leaderboard row = aspirational target, not hard gate).
**Owner PDF spot-check COMPLETE (2026-07-02): ALL PASS** (U2021 MIOST-absent /
Eqs. 18–20 / spacing-negative / mean-only / Eq. 25 erratum REAL; U2022 future-work
verbatim / tiling-compute paragraph / AltiKa-Q; B2023 six-variables / 80–900 /
Table 3 allsat-1 / Eqs. A2+A17 errata REAL — full list in brief §10). **Brief
VERIFIED END-TO-END (all four tiers) and CLEARED as the design-session input.**

## MIOST Stage-A validation strategy — OWNER-DECIDED 2026-07-03 (design-session input)

**Validation tiers (decided, not draft):**
- **Tier 1 (exact oracles — the correctness proof):** duality oracle — dense obs-space
  OI with B = ΓQΓᵀ vs matrix-free reduced normal equations (U2021 Eq.2 ↔ Eq.15) agree
  to tight rtol on a small synthetic; adjoint identity ⟨Gη,r⟩ = ⟨η,Gᵀr⟩; dense-vs-PCG
  on small A.
- **Tier 2 (documented properties):** representer with negative lobe (U2022 Fig.4);
  hard compact support; 80–800 km span.
- **Tier 3 (similarity, NEVER a gate):** compare our maps to distributed
  `dc_maps/OSE_ssh_mapping_MIOST.nc` (RMS diff, spectral coherence), reported as
  diagnostic only. Provenance: file is SHA256-pinned in the committed 2021a manifest
  (e58caea7…, 29,804,673 bytes) — comparison target exact + reproducible.
- **Tier 4 (THE GATE):** the existing 2021a harness, identical to OI/GMRF. Gaps #1–5
  become the `parameter_space` (spacing α, n_dir, Q scale/slope, R, λ_min) closed by
  the Phase-5 loop on the blocked validation track; c2 once at acceptance; HARD FLOOR
  = BASELINE 0.85; MIOST row (0.89/0.08/139) = ASPIRATIONAL anchor, never hard gate.
  Calibration bar recorded N/A-for-POINT (capability-conditional).
- **Explicit:** pointwise reproduction of the MIOST maps is impossible IN PRINCIPLE
  (undocumented config, no public code) and is NOT a criterion at any tier.

**Execution (decided):** SkyPilot NOT a Stage-A prerequisite; validation runs locally.
Escalation ladder if tuning throughput demands: numba/stored-G optimization → shorter
temporal windows → existing dask address-only seam to a bigger box → SkyPilot as its
own milestone. Reopen ONLY if Task-0 probe + early tuning show ONLY the expensive
corner (α≤0.5, 12-dir, full-year single window) clears the BASELINE floor.

**MIOST maps file (verified 2026-07-03):** downloader re-run — 14/14 `[skipped]` =
present + SHA256-verified, 0 downloaded; `dc_maps/OSE_ssh_mapping_MIOST.nc` confirmed.
Tier-3 output-config facts (metadata only): 365 daily maps 2017-01-01→2017-12-31;
lat 33–43°N, lon 295–305°E, 0.1° (101×101); single variable `ssh` float64 — **no
error/uncertainty variable** (consistent with brief §5 POINT-only).

**Task-0 cost probe (committed `scripts/probe_miost_cost.py` + tests — the FEM
uncommitted-probe lesson):** measured on this box (4 cores, ~15 GB RAM, ~4 GB avail):
- In-box obs (10°×10°, c2 excluded): 60 d = 39,666; 365 d = 208,542. Per-mission
  quirks: j2g = 0 in Jan–Feb (geodetic phase starts later in 2017; 9,780 full-year);
  j2n only 10,841 full-year.
- Micro-benchmarks: numpy cos-product basis eval **10 M elem/s**; CSR stored-G matvec
  **527 M nnz/s** (~50× faster ⇒ matrix-free-in-numpy is the wrong plan; stored-G or
  numba is rung 1).
- Feasibility (budgets: stored-G ≤ 8 GB, ≤ 60 min/solve, 100 CG iters): **18/32
  configs clear.** All 60-d windows clear stored-G except α=0.5+12-dir (11.5 GB);
  full-year clears ONLY at α=1.5 today. **RAM is the binding constraint, NOT
  compute** — even the worst config (α=0.5, 12-dir, 365 d, λmin=80: N_coef=2.18M,
  nnz=5.0e9, G=60.5 GB) would solve in ~32 min if G fit. The expensive corner is
  memory-bound ⇒ the SkyPilot-reopen criterion is a RAM/blocking question, and rung 1
  (numba matrix-free at stored-G-like throughput, or G-block streaming) flips most of
  the TOO-SLOW rows without leaving the box.
- Recommended local operating envelope (probe output): 60-d windows at any probed
  (α, n_dir) except α=0.5+12-dir; full-year only at α=1.5. Largest clearing config:
  α=0.5, 8-dir, 60 d, λmin=80 (nnz=6.4e8, G=7.7 GB, ~4 min/solve).
  **AMENDED 2026-07-03 (Phase-7 design, halo pricing):** probe counts were BOX-ONLY;
  production uses halo_deg=1.0 (obs ~×1.44) → the halo-priced fine-spacing corner is
  **α=0.75** (which also clears n_dir=12 at ~7 GB → the 12-dir sensitivity diagnostic
  gains feasibility); α=0.5 exceeds the 8 GB budget at any halo ∈ {0.5, 1.0} (~9.3–11
  GB) and is excluded VISIBLY by StoredGFeasibility (α box stays [0.5,1.5]). See
  design D7.
- Probe assumption flagged in-script: geometric scale ratio √2 (implied by λ_min ∈
  {80,113} being consecutive √2 steps); NOT from the papers (brief §8 gap #1 stands).

**Phase-7 MIOST DESIGN COMPLETE (2026-07-03):** brainstorm run (2 clarifying
questions + 2 architecture forks + section approvals, all owner-decided); spec
committed at `docs/superpowers/specs/2026-07-03-phase7-miost-design.md` (decision
register D1–D8: 8-rung 80→905/√2 ladder, n_dir=8/180°, W=60/V=15/stride45 designed
at L_t_max=12, L_t tunable [5,12] with Δt=L_t/2, window-cache Method + 4 hardenings,
coefficient-space Stage-B ensemble + CRN + s-rescale theorem, halo=1.0
predicate-priced, λ_ref/R_ref gauge-inert anchors). GIT PUSH still blocked — host
key fixed this session but the container has NO SSH key at all (`Permission denied
(publickey)`); owner must install a deploy key/credentials before the external
review can verify against the public repo. Spec APPROVED on file review (owner,
2026-07-03, no changes). **PLAN WRITTEN + committed (`02f7055`):**
`docs/superpowers/plans/2026-07-03-phase7-miost.md` (+ `.tasks.json`, 19 tasks,
native tasks #7–#25) — Stage A Tasks 1–13 (gate = c2 once, µ≥0.85, diagnostics
attached, calibration N/A), Stage B Tasks 14–19 all blocked by the Stage-A gate;
user-gates on Tasks 11/13/19. **Plan APPROVED (owner review 2026-07-03) after ONE
required correction, now FOLDED + committed: Task 6 right-edge placement — original
window 8 [342,402] demanded obs to day 414 vs data end 395 (span assert
unsatisfiable → every full-year run crashes); fixed to k=0..7 stride + RIGHT-ALIGNED
last window [322,382] (1-day slack both sides), blend denominator generalized to the
ACTUAL pairwise overlap (35 d on the last pair; partition-of-unity test must fail
pre-fix), escape hatches removed from the support test. Secondary confirms: BO
`rounds` threading VERIFIED landed (`6e418fa`); Task-13 smoke must record-and-skip
on StageANoAdmissible (d7376b8 pattern), never ERROR. **EXECUTION GREEN-LIT: fresh
`/superpowers-extended-cc:executing-plans docs/superpowers/plans/2026-07-03-phase7-miost.md`
session (owner-chosen mode). Gates at Tasks 11/13/19 stop for owner sign-off.
PUSH STILL BLOCKED (no GitHub credentials in container — chore task #6): origin at
`13a1731`; spec/plan commits local-only.**

**Phase-7 EXECUTION deviations (running list):**
- **Task 6 (2026-07-03): the plan's per-day support test was geometrically
  impossible; spec governs.** Plan Task-6 AC demanded a SINGLE covering window
  with span ⊇ [d±12] for EVERY output day — impossible at stride 45/W=60: a
  window's full-support day range is [s+12, s+48], so every blend zone leaves a
  9-day gap (days 31–38, 76–83, … 56 days total fail). Spec §4.1(iii) (which the
  plan header says GOVERNS on conflict) requires the single-window form only for
  FULL-WEIGHT days; blend-zone days get union-support + truncation
  anti-correlated with weight. Tests implemented spec-faithfully:
  union-support ∀ days (UNCONDITIONAL, catches the 402-crash), single-window
  support ∀ full-weight days (UNCONDITIONAL), blend-zone anti-correlation
  (weight hits 0 exactly where truncation peaks). Owner should confirm at the
  Task-11 gate.
- **Task 5 (2026-07-03): DiagonalQ.variances_for latent bug fixed** — it indexed
  the module-default LADDER by scale_idx, mispricing q for ANY custom ladder
  (the 2-rung oracle ladder got 80/113-km variances). Now derives the element's
  actual wavelength from half_width/1.5. Caught by the duality-oracle work;
  regression test in test_miost_operators.py.
- **Task 11 (2026-07-03) MEASURED: Jacobi-PCG at (rtol 1e-6, maxiter 500) does
  NOT converge on real windows** — every production-window solve stalls at
  ~5e-4 relative residual at the iteration cap, and 500→1000 iters moves the
  solution by 49% relmax (probe on window w5, α=1.5, ρ=10). Residual falls only
  ~3.4×/500 iters ⇒ ~3000+ iters for 1e-6. CONSEQUENCES: (a) the first
  equivalence run's deltas (max|Δ| up to 2.0 m, NOT blend-localized) were
  solver noise, not windowing — rerun at converged settings before any owner
  verdict; (b) U2022's "typically 100 iterations" does not transfer to plain
  Jacobi (their preconditioner is unspecified — brief §8 gap #4 bites);
  (c) Task-13 per-trial cost is dominated by iters — either raise maxiter
  (correct, slower) or improve the preconditioner (later, measured). Miost now
  takes pcg_rtol/pcg_maxiter constructor overrides, recorded in params_key.
  **LSMR MEASURED (same window): no √κ rescue** — column-scaled LSMR on the
  stacked LS system reaches normal-eq rres 2.4e-5 in 1073 iters (94 s; ~2× PCG)
  and 6e-7 in 4448 iters (382 s; ~1.3×). Ill-conditioning is intrinsic
  (overlapping multiscale elements), not a normal-equations artifact. PCG@8000
  still only 1.4e-7.
  **OWNER DECISIONS (Task-11 gate, 2026-07-04):**
  - **PCG budget = BUDGETED SOLVE, STAGE-A-SCOPED ONLY** (rtol target 1e-6,
    maxiter cap 500): map-space depth-insensitivity MEASURED (worst-day
    max|Δ| 2.0036 @500 vs 2.0220 m @6000-converged; blend medians 0.5740 vs
    0.5542), µ/λx are map functionals, U2022 ~100-iteration family precedent.
    Acceptance configs must state (target, cap, ACHIEVED per-window residual)
    — implemented: `miost.CONVERGENCE_LOG` telemetry + the gate runner's
    `solver_budget` / `winner_achieved_residuals` JSON blocks. NEVER claim
    "identical", always the quantitative insensitivity numbers.
  - **Stage B re-decides the budget at Tasks 15/16** via the spec-§6.5
    under-convergence test: PCG's slow modes are prior-dominated,
    HIGHEST-posterior-variance directions ⇒ member under-convergence
    plausibly under-disperses exactly where σ matters most. Member generation
    MUST NOT inherit the 500 cap silently (winner-only ⇒ converged members
    affordable if the test demands them).
  - **Preconditioner follow-up RECORDED, not built:** per-rung column
    equilibration / block-Jacobi if Stage B requires tight solves (5000–6000
    Jacobi iters on a multiscale dictionary = cross-rung scaling imbalance).
  - **D4 = time-boxed localization first** (`scripts/diag_miost_localization.py`,
    ~1–2 h) with PRE-REGISTERED close rules: (i) |Δµ|≤0.005 on the blocked
    validation track AND flat boundary-distance profile AND top-rung
    attribution → CLOSE fallback-NOT-invoked + update the doc headline;
    (ii) profile decays with boundary distance → implement the pavement ±L_t
    extension + re-run; (iii) Δµ ≤ −0.01 (single wins) → STOP, owner call;
    (iv) J-identity violated or small-scale signature → defect hunt.
    0.005<|Δµ|<0.01 → report and hold. Note for the record: the ten worst days
    cluster near the w5/6 seam (245–252, 264–266) + w4/5 blend (200) —
    "interior" days within ~L_t of a boundary are consistent with a
    window-edge mechanism whose footprint exceeds the blend zone.
  - **D4 LOCALIZATION MEASURED (2026-07-04,
    `docs/validation/miost_equivalence_localization.md`) → REPORT-AND-HOLD:**
    Δµ = **−0.0066** (windowed 0.9391 / single 0.9457 on the blocked j3 track;
    λx 96.3 vs 88.3 km) — inside the explicit owner-judgment band
    (0.005<|Δµ|<0.01). Profile: WEAK decay with boundary distance
    (corr −0.223; near<6d mean 0.678 vs far≥15d 0.495 m) on top of a
    distance-independent ~0.5 m floor. Attribution: NOT top-rung — mid-ladder
    113–320 km dominates (top-2-rung share 0.32 worst / 0.23 far day);
    worst-day argmax 18 cells from the nearest edge (interior). J-identity OK
    (J_single 3.08e4 ≪ J_stitched 5.96e5 — reference is the joint minimizer;
    no defect signature; Tier-1 oracles green). READING: a real
    information-pooling difference in the mesoscale band (year-long temporal
    chaining) + a modest boundary-linked component; the pavement ±L_t
    extension would plausibly shave only the decaying component, not the
    floor. Numbers big-picture: UNTUNED (α=1.5, ρ=10) windowed µ already
    0.9391 ≫ the 0.85 floor.
  - **CLOSED (OWNER DECISION 2026-07-05): accept-with-recorded-cost; fallback
    NOT invoked.** Conditions of the close:
    (1) cost is POINT-MEASURED at the untuned diagnostic point — never state a
    universal "windowing cost";
    (2) WINNER-POINT RE-MEASUREMENT at Task-13 acceptance: if a single-window
    solve fits the RAM budget at the winner's α (~α≥1.2), one full-year
    single-window solve at winner params, (Δµ, Δλx) on the VALIDATION track
    only — never c2 (c2 = exactly once, windowed winner); if infeasible,
    record "cost not measurable at winner's alpha". Implemented in
    `scripts/stage_miost_gate_run.py` (`winner_point_windowing_cost`).
    (3) mechanism wording stays modest (information-pooling, mid-ladder
    113–320 km, ~0.18 m boundary-linked minority over ~0.5 m floor; the 19×
    J-gap is expected for ANY stitch — defect check only);
    (4) doc headline updated to FALLBACK NOT INVOKED.
    REJECTED with reasons: pavement extension (targets the minority component,
    cannot restore year-long chaining; shelved as post-gate polish IF the
    tuned winner shows boundary artifacts); W=90/stride 60 (spends the binding
    RAM resource — kills α=0.75 at halo counts ~10.5 GB — to shrink, not
    remove, the floor; dominated trade like 12-dir);
    single-window-as-product (KNOWN NOT-TAKEN CONTINGENCY: locks α≥~1.2
    permanently, reprices Stage-B member generation, abandons owner-decided
    D3/D5 — revisit only as an owner re-scope if the tuned windowed winner
    disappoints at the gate).
- **Task 11 (2026-07-03) perf/memory rewrites forced by measurement:** the
  plan's per-element O(n_el × n_obs) assembly masking was ~13 min per 425-d
  window (probe: 1137 el/s) → vectorized analytic-index bucketing (20 s, 40×);
  the t-slot-tiled S matrix OOM-killed the single-window run (~255M triplets)
  → day map factored as S_spatial @ time_contract(η, day) (85× smaller S).
  Both exactness-pinned by dense-equality tests.
- **Task 16 (2026-07-06): the plan's exactness bound was statistically
  invalid — replaced by a whitened-identity oracle (spec governs).** The
  plan demanded m=4000 member covariance match dense A⁻¹ at Frobenius
  rel err < 3·√(2/(m−1)) ≈ 0.067 — but the rel Frobenius error of an
  n×n sample covariance from m draws scales as √(n/m) (measured 0.90 at
  n_el=3696), a SCALAR-variance bound misapplied matrix-wide;
  unsatisfiable for any realistic basis (n=200 already gives 0.22).
  Exactness is instead proven on whitened anomalies Z = L⁻¹(members−mean),
  A⁻¹ = LLᵀ (exact sampling ⇒ Z ~ N(0,I)) — a TIGHTER test:
  trace/n = 0.99959 (5σ tol ±0.0018), worst whitened variance dev
  0.087 < 0.112, offdiag mean-square 2.50e-04 = 1/m exactly. Same
  failure modes covered (missing Q⁻¹η̃ collapses whitened prior
  directions; wrong ε scale blows the trace; m-vs-(m−1) exceeds 5σ).
  Under-convergence AC met: rtol=0.5 members deviate 64× the tight solve
  (0.0261 vs 0.0004, >3× demanded). The CONSTRUCTION was exact all
  along; only the yardstick changed. Bonus hardening: member RHS
  construction factored to `member_rhs_matrix` so the oracle tests the
  PRODUCTION path sample_members uses.

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

