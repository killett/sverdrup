# Phase 7 — MIOST: multiscale reduced-basis inversion as a sverdrup Method

**Date:** 2026-07-03. **Status:** owner-approved design (brainstorm 2026-07-03); awaiting
file review, then writing-plans.
**Method source of truth:** `docs/papers/2026-07-02-miost-method-brief.md` (verified
end-to-end, all four tiers). **Validation strategy + Task-0 probe:** PROGRESS.md
"MIOST Stage-A validation strategy — OWNER-DECIDED 2026-07-03". **Cost model:**
`scripts/probe_miost_cost.py` sizing functions (committed + tested; relocated by this
design, §5.1).

## 0. Shape of the milestone

ONE milestone, TWO hard-gated stages.

- **Stage A — MIOST-as-documented.** `Miost` registered as `"miost"`,
  `native_capability = POINT`, built ensemble-ready via six required seams (§3.2),
  accepted on the 2021a harness (µ hard floor 0.85 = BASELINE; MIOST leaderboard row
  0.89/0.08/139 = aspirational anchor, never a gate; calibration recorded
  N/A-for-POINT).
- **Stage B — ensemble posterior.** Perturbed-observation solves through the SAME
  `solve(b)`; capability upgrade to SAMPLES (native) + MARGINAL_VARIANCE/COVARIANCE
  (ensemble reduction); accepted on the existing Calibration evaluators; Stage-A mean
  provably unchanged (§6.3 theorem + non-regression test). Designed here, built only
  after the Stage-A gate.

**Honesty banner (spec-level):** pointwise reproduction of the distributed MIOST maps
is impossible IN PRINCIPLE (undocumented configuration, no public code — brief §8) and
is not a criterion at any tier. The product is FAMILY-FAITHFUL and tuned-in-framework.
Where this design chooses what no paper documents, the choice is named, recorded in
provenance, and flagged against the brief's gaps register (§8 of the brief).

## 1. Decision register (owner decisions, brainstorm 2026-07-03 — settled)

| # | Decision | Key content |
|---|---|---|
| D1 | Discrete knobs | n_dir=8 over 180°, λ_min=80 km, ratio √2, **8-rung ladder 80→905 km** (not 7→640: red spectrum makes an unrepresented 640–800+ band a µ risk; top rung nearly free). 8-over-180° is finer than the documented 12-over-360° (IT propagation directions, mod-360; mesoscale carriers are mod-180 — inference, flagged); support ~3λ ⇒ ~20–40° angular main lobe, so 22.5° spacing already overlaps. All three = per-run constants in provenance, gap-#1/#2 assumptions, swappable. |
| D2 | 12-dir sensitivity | Post-gate diagnostic on the BLOCKED VALIDATION track only (never c2 twice): winner params re-scored at n_dir=12, conditional on winner's α fitting the budget at 12-dir (else nearest feasible α, substitution noted, or skipped-with-reason). No mid-stage switching. |
| D3 | Windowing | W=60 d, overlap V=15 d, stride 45 d (run-constants). L_t TUNABLE in [5, 12] d with pavement spacing tied Δt=L_t/2 (β=0.5 fixed, recorded — the documented spacing-∝-extension principle applied in time, same assumption family as √2). Consequence: per-obs temporal overlap = 2L_t/Δt = 4 always ⇒ nnz and stored-G are L_t-INVARIANT; only N_coef ∝ 1/L_t. V=15 ≥ L_t_max=12 (ratio 1.25 at the ceiling — the reason the cap is 12); tuner pinning the L_t ceiling = recorded signal to raise V in an owner-decided follow-up, never a silent extension. |
| D4 | Equivalence check | Windowed-vs-single-window REQUIRED (not optional): full-year at α=1.5 (both paths probe-feasible), difference quantified WORST-CASE-LOCALIZED at blend days (never year-RMS only). Designed fallback if material: extend each window's element pavement by ±L_t (~+8–15% nnz, auto-priced by the resource predicate). |
| D5 | Protocol fit | Window-cache Method (Option 1) with four hardenings (§4.2). Window-native runner REJECTED (scorer method_name branch violates the Task-12 method-agnostic-loop invariant); dual-path REJECTED (kernel=None drift lesson). Batch-solve protocol extension = rule-of-three future note, not built. |
| D6 | Stage-B representation | Coefficient-space members + `MiostEnsembleDistribution` (Option 1) with four hardenings (§6). Grid-snap options REJECTED (nearest-node snap injects grid error into the calibration acceptance metric; violates on-demand pairwise-covariance invariant). |
| D7 | Obs halo | halo_deg=1.0 (challenge `read_obs` precedent), recorded, predicate-priced. halo=0.5 DOMINATED (α=0.5 exceeds 8 GB at both 1.0 and 0.5: ~11 vs ~9.3 GB — pays edge skill for nothing); halo=0 loses edge support c2 evaluates. α box STAYS [0.5, 1.5]; StoredGFeasibility excludes the corner visibly (infeasible-with-reason), honest if the budget ever rises. Halo-priced fine-spacing corner = α=0.75 (also clears 12-dir at ~7 GB → D2 gains feasibility). Predicate consumes HALO-INCLUSIVE obs counts. |
| D8 | Anchors | λ_ref=300 km, R_ref=(0.03 m)² — recorded anchors, NOT modeling commitments (gauge-inert, §2.3). |

## 2. Method core

### 2.1 Basis (documented; brief §2.2)

Element p of the SSH dictionary (U2021 Eqs. 18–19 exactly; B2023 Eqs. A16–A17):

```
Γ_h[i,p] = cos( k_xp(x_i−x_p) + k_yp(y_i−y_p) + Φ_p )
         · f_tap( (x_i−x_p)/L_xp, (y_i−y_p)/L_yp, (t_i−t_p)/L_tp )
f_tap(δx,δy,δt) = cos(πδx/2)·cos(πδy/2)·cos(πδt/2)  for (|δx|,|δy|,|δt|) < 1, else 0
```

- Cosine plane-wave carrier, **NO ωt term** (no propagation in the mesoscale basis —
  documented absence, brief §2.3); hard compact support; **L_x = L_y = 1.5λ**;
  sine/cosine phase pairs Φ ∈ {0, π/2}.
- Wavelength ladder: geometric, ratio √2, **8 rungs 80 → 905 km** (D1). Slight
  overshoot of the documented 800 top preferred to undershoot; recorded as part of the
  flagged gap-#1 assumption.
- Directions: θ_j = j·22.5°, j = 0..7 (mod-180°, D1 rationale recorded).
- Temporal: half-width L_t (tunable [5,12] d), pavement spacing Δt = L_t/2, slots
  indexed from the GLOBAL origin (EPOCH 2017-01-01) — element identity
  (scale, dir, phase, x_p, y_p, global_slot) is windowing-independent (Stage-B CRN
  prerequisite, §6.2; also cleaner for the D4 diagnostic).
- Spatial pavement: spacing αλ per scale over the box EXTENDED by 1.5λ per scale
  (edge support margin). Honesty (approved fold): the margin raises N_coef ~1.5×
  overall (small scales dominate; top-rung relative blowup absolutely trivial) — the
  factor is carried in the sizing note and the margin term is INCLUDED in the
  relocated `miost_sizing` functions so predicate and probe stay one arithmetic. The
  per-obs nnz upper bound is unchanged (overlap count is support-driven).

### 2.2 Q and R (parameterized; flagged against brief gaps #3/#4)

- **Q** diagonal: `q_p = Q_scale · (λ_p/λ_ref)^q_slope`, isotropic, geography-constant
  in Stage A. Papers document only "spectrum-following" (AltiKa PSD database, U2022
  §3.2.1) with no functional form — a two-parameter power law is the minimal tunable
  stand-in, named and flagged. Same q within a phase pair (spectrum→variance pair
  split absorbed into Q_scale — stated, not hidden).
- **R** diagonal, scalar `R_ref = (0.03 m)²` fixed in Stage A (anchor: U2021's OSSE
  3 cm noise; real-data R undocumented = gap #4).
- **The ρ/s split (D6 hardening, load-bearing):** with scalar R the posterior mean is
  invariant to joint (Q,R) → (sQ,sR); µ/λx see only ρ = Q_scale/R. Stage A therefore
  tunes **ρ** (one knob; the flat direction never enters the search), s ≡ 1. Stage B
  tunes **s** on VALIDATION calibration only, applied to persisted members as the
  exact anomaly rescale η′ = η^a + √s(η − η^a) — zero re-solves, mean unchanged
  (theorem §6.3). Condition recorded: holds for uniform scalar R; per-mission R would
  re-enter the mean.

### 2.3 Gauge inertness of the anchors (D8)

λ_ref is absorbed exactly into Q_scale (its value affects only interpretability and
knob decorrelation; 300 km ≈ the ladder's geometric center, good for BO). R_ref is
absorbed jointly by (ρ, s): ρ′ = ρ·R_ref/R_ref′, s′ = s·R_ref/R_ref′ — pure gauge
GIVEN uniform scalar R (the recorded condition; per-mission R breaks it). Both are
recorded anchors, not modeling commitments. Seam test (c) asserts the λ_ref gauge
numerically (§7.2).

### 2.4 Estimator and solver (documented; brief §2.6–2.7)

Reduced normal equations `(GᵀR⁻¹G + Q⁻¹) η = GᵀR⁻¹y` (U2021 Eq. 15); G assembled
ANALYTICALLY — CSR columns filled from the basis formula evaluated at obs coordinates,
never through a gridded H (U2021 p.5). Solver: PCG, **stored-G CSR default path**
(measured 527 M nnz/s vs 10 M elem/s naive matrix-free — Task-0; numba matrix-free =
escalation rung 1, noted not built). **Preconditioner: Jacobi,
`diag(GᵀR⁻¹G) + Q⁻¹`** — OUR choice; the papers never name theirs (brief gap #5);
named + recorded. `pcg_rtol` (default tight, e.g. 1e-6 — plan detail) and
`pcg_maxiter` are named, recorded parameters; the convergence report (iterations,
final residual) is surfaced, never swallowed.

## 3. Module layout and the six seams

### 3.1 Files (granularity mirrors gmrf.py/gmrf_grid.py/gmrf_linalg.py)

| File | Contents |
|---|---|
| `methods/miost_basis.py` | `BasisSpec` (frozen: run-constants D1/D3/D7/D8 + α, L_t bound at construction); element enumeration with stable global identity; vectorized analytic evaluation; builders: CSR G (obs), CSR S (output grid, §4.2), diagonal Q. |
| `methods/miost_solver.py` | Multi-RHS PCG `solve(B)` on A-apply = `Gᵀ(R⁻¹(G·x)) + Q⁻¹x`; Jacobi preconditioner; convergence report. |
| `methods/miost.py` | `Miost` Method: `WindowPlan`, window cache (§4.2), `solve(obs, grid, params, time_days)`, `parameter_space()`, Stage-B member generation. |
| `methods/miost_sizing.py` | Probe sizing functions RELOCATED here (single source of truth; `scripts/probe_miost_cost.py` re-imports; tests move; `scale_set` gains the 905-cap argument; pavement-margin N_coef term added). |
| `distributions/miost_ensemble.py` | Stage B: `MiostEnsembleDistribution` (§6.4) + representation-tagged persistence kind. |
| `application/tuning/feasibility.py` | `StoredGFeasibility` + `CompositeFeasibility` (all-of) added; existing predicates untouched (invariant 5). |

Registry: `"miost": Miost` in `methods/registry.py`. `Method` /
`PredictiveDistribution` protocols UNTOUCHED (seam e). Rule-of-three note recorded: if
a second window-shaped method arrives, consider an optional batch-solve capability —
one method does not justify a protocol change.

### 3.2 The six ensemble-ready seams (each tested AS a seam in Stage A)

a. **RHS-agnostic solver:** `solve(b)` pure in the right-hand side, multi-RHS capable.
   Test: arbitrary b not derived from y. (Stage B makes this load-bearing: batched
   member RHS.)
b. **RHS construction its own unit:** `b(y) = GᵀR⁻¹y`; G-apply and Gᵀ-apply
   first-class functions. Test: adjoint identity ⟨Gη, r⟩ = ⟨η, Gᵀr⟩.
c. **Q and R explicit diagonal objects** with named, documented parameterization
   (§2.2). Test: gauge-inertness of λ_ref (§2.3) asserted numerically.
d. **Persisted state = η^a + basis spec;** grid maps and arbitrary-point queries via
   analytic Γ evaluation (on-demand-covariance invariant). Test: reload → identical
   map; arbitrary-point query matches direct evaluation.
e. **`native_capability = POINT`** behind unchanged protocols; Stage B swaps in an
   ensemble-backed PredictiveDistribution; protocols untouched. Test: protocol
   compliance + `CapabilityNotAvailableError` (§5.4).
f. **Seeding via `derive_seed`** + `pcg_rtol` as named, recorded parameters from day
   one (tolerance joins the statistical contract in Stage B, §6.5). Test: both appear
   in params_key; seed root reproducible.

## 4. Temporal windowing and the window-cache Method

### 4.1 WindowPlan (D3; our feasibility adaptation, stated honestly)

The papers' global runs use one solve over the full record (U2022); U2021's regional
precedent is a single window. Our 60-day windowing is a FEASIBILITY adaptation (RAM
budget), honestly ours; the blend is the U2022 §3.2.3 pattern (linear weight ∝
boundary distance) applied in TIME.

- Run-constants: W=60 d, V=15 d, stride 45 d. **Designed at the L_t CEILING
  (L_t_max=12 d), not the nominal 10** — W/V/stride are run-constants but L_t is
  per-trial, so the support constraint must hold for EVERY trial (approved fold A).
- Constraints (normative): (i) every output day 2017-01-01→12-31 is covered by ≥1
  window with two-sided temporal element support inside DATA, at L_t_max=12; (ii)
  blend zone = the V-day overlap, linear weight ∝ distance to window boundary,
  weights partition unity over the ≤2 covering windows; (iii) full-weight days
  (outside blend zones) have complete two-sided support; inside the blend zone each
  contributor's truncation is anti-correlated with its weight. V=15 ≥ L_t_max=12.
- Edge windows sit in the REAL margin data (obs files span 2016-12-01→2018-01-31):
  first window starts ≈2016-12-14, so first-slot support reaches ≈2016-12-02 vs obs
  start 2016-12-01 — **~1 day slack at the L_t ceiling, recorded**; shifting placement
  by a day is plan detail. Obs and pavement both use the margins there.
- `window_id` = deterministic string from (start_day, W). Temporal slots from the
  global origin (§2.1).

### 4.2 Window-cache `Miost.solve` (D5 + four hardenings, normative)

`solve(obs, grid, params, time_days=d)` solves the ≤2 windows covering d once each,
caches η, and returns the day-d POINT distribution (mean = blended S-projection).
Harness (`run_challenge_map`, `run_mean_var_maps`, scorer, stage_a) runs VERBATIM;
`temporal_half_window_days` is set wide for miost runs — an ARGUMENT, not a branch —
so every call carries the full obs; the method re-subsets per window internally.

1. **Cache key = (window_id, params_key, obs-content fingerprint).** The obs hash is
   load-bearing: keying without it + a "callers pass full obs" convention would let a
   partial-obs caller silently poison the cache — hashing (~ms) converts contract
   violations into cache misses (wrong-becomes-slow, never wrong-becomes-wrong).
   Loud assert if the passed obs do not span [window_start − L_t, window_end + L_t].
   `params_key` serializes EVERYTHING η depends on: continuous params (α, ρ, q_slope,
   L_t), run-constants (n_dir, λ_min, ratio, ladder cap, W, V, β, halo_deg, λ_ref,
   R_ref), `pcg_rtol`/`pcg_maxiter`, seed root.
2. **Separable output projection (required, not an optimization):** naive per-day Γη
   at the grid costs ~10⁸–10⁹ evals/day at fine α (hours/trial at 10 M elem/s).
   Instead: per window, precompute the SPATIAL basis matrix S at the output grid once
   (~0.1–0.4 GB CSR; ≤2 windows live, evicted on advance); day map =
   S @ (η ⊙ τ_day) — one SpMV (~0.1 s at 527 M nnz/s). Cache stores η (~MBs); G is
   FREED after each window solve.
3. **Execution contract:** per-trial map production is SERIAL over days within one
   process/instance (cache is instance state; fan-out = empty caches + redundant
   multi-GB solves). Resource accounting: `n_concurrent_solves × peak stored-G ≤
   budget` — stated in the predicate docs.
4. **Cache-correctness tests:** repeated solve for the same day, and two days within
   one window, equal a fresh-instance solve exactly; cache-on vs cache-off identical
   maps.

### 4.3 Degenerate-obs totality

Probe facts: j2g contributes ZERO obs Jan–Feb (geodetic phase), j2n ~10.8k/yr. Windows
with mission-absent or thin coverage are NORMAL. The solver is total for n_obs ≥ 0
(n_obs=0 ⇒ A = Q⁻¹, η = 0, prior-mean map, finite, logged). No mission-count
assumption anywhere in assembly. Explicit tests: mission-absent window; zero-obs
window.

### 4.4 Required equivalence diagnostic (D4)

Windowed-vs-single-window, full-year, α=1.5 (both probe-feasible); difference
quantified worst-case-localized at blend days vs interiors (invariant-6 discipline).
Fallback recorded: per-window pavement extension ±L_t (~+8–15% nnz, predicate-priced).
Stage B extends this diagnostic to variance fields (§6.2).

## 5. Tuner and harness integration

### 5.1 StoredGFeasibility (composes; invariant 5, gate-before-solve invariant 3)

- Cost model = the relocated `miost_sizing` functions (single arithmetic with the
  probe; 8-rung ladder incl. 905 cap; pavement-margin N_coef term; nnz upper bound ×
  12 B [f64 data + i32 index]).
- Constructed with: basis run-constants, **HALO-INCLUSIVE** per-window obs counts
  (max over windows), `budget_bytes` (named, default 8e9), `n_concurrent` (default 1).
- `feasible(params, tile_geometry, caps)` reads α from params; **no L_t term**
  (nnz is L_t-invariant, D3). Excludes BEFORE any solve.
- **Infeasible-with-reason recorded:** predicate exposes `predicted_bytes(params)`;
  the trial record stores predicate name + predicted vs budget (small trial-record
  extension; plan detail). α box stays [0.5, 1.5] (D7) — the α=0.5+halo corner is
  excluded VISIBLY, honest if the budget ever rises.
- `CompositeFeasibility(predicates)` = all-of; composes with `CoherenceFeasibility`,
  replaces nothing; `tune()` untouched.

### 5.2 parameter_space (scalar boxes; Phase-5 invariant 12)

| Knob | Box | Rationale (recorded) |
|---|---|---|
| `spacing_alpha` | (0.5, 1.5) | Probe grid; predicate excludes what RAM can't hold. |
| `log10_rho` | (−2, 3) | ρ = Q_scale/R_ref; magnitude knob → log box. |
| `q_slope` | (0, 4) | Red-spectrum variance-vs-λ exponent (~1–3 physical; box wider). |
| `l_t_days` | (5, 12) | D3; cap 12 keeps V/L_t ≥ 1.25; ceiling-pinning = recorded signal, never silent extension. |

Discrete knobs (n_dir=8, λ_min=80, ratio √2, ladder cap 905, W, V, β, halo_deg, λ_ref,
R_ref) are per-run constants recorded in provenance, flagged as assumptions where the
papers are silent. Exact box endpoints are plan-tunable; the names and shapes above
are normative.

### 5.3 Capability-derived bars + capability-routed scorer (folds 1 + B)

- `bars_for(capability)` in `objective.py`: µ bar (0.85 floor) always; coverage bar
  present iff capability ≥ MARGINAL_VARIANCE, else ABSENT and recorded N/A. Never
  hand-assembled per stage — Stage B cannot forget the bar; future POINT methods
  cannot inherit one they can't evaluate. Both-directions test.
- Scorer routes by `native_capability` (NOT method_name — method-agnosticism, the
  Task-12 invariant): POINT → mean-only map path (`run_challenge_map`);
  ≥ MARGINAL_VARIANCE → mean+var path (`run_mean_var_maps`). λx path unaffected.
  Both-directions test mirroring `bars_for` (fold B).

### 5.4 Named capability error (fold 2)

The POINT distribution's `marginal_variance`/`covariance`/`sample` raise a defined
`CapabilityNotAvailableError` (UnresolvedScaleError pattern) — never None/NaN. Test:
a Calibration evaluator applied to a POINT method fails LOUD.

### 5.5 TileGeometry stance (fold 3)

MIOST reports `TileGeometry.n_tiles = 1` (single spatial tile). Temporal windows are
deliberately NOT coherence-predicate tiles — their seam health is governed by the CRN
construction (§6.2) + the required worst-case-localized seam diagnostics (§4.4, §6.2).
This is why Stage-B SAMPLES does not collide with the empty joint region of
`CoherenceFeasibility` (that predicate keys on SPATIAL tiling; n_tiles=1 today; it
applies verbatim if MIOST is ever spatially tiled).

### 5.6 Stage-A acceptance procedure

Phase-5 loop (Sobol → BO) on the blocked validation track; `StoredGFeasibility`
composing in front (infeasible-with-reason visible); winner → **c2 exactly once** →
record (µ, σ, λx) + calibration-N/A. Gate: **µ ≥ 0.85**. Attached diagnostics (never
gates): **Tier 3** — RMS diff + spectral coherence vs the SHA256-pinned
`dc_maps/OSE_ssh_mapping_MIOST.nc` (e58caea7…, 29,804,673 B; 365 daily maps 2017,
0.1°, 101×101, ssh-only; same 10°×10° box — regrid ours only if the harness grid
differs); **12-dir sensitivity** (D2; feasible at α ≥ 0.75 ≈ 7 GB per D7).

## 6. Stage B — perturbed-observation ensemble (built after the Stage-A gate)

### 6.1 Sampling (standard analysis; exact for this linear-Gaussian model)

Member i: draw ε′ᵢ ~ N(0,R), η̃ᵢ ~ N(0,Q) (both diagonal — trivial); solve with the
SAME `solve(b)`:

```
A η_i = GᵀR⁻¹(y + ε′_i) + Q⁻¹ η̃_i ,   A = GᵀR⁻¹G + Q⁻¹
```

Exactness (two lines): E[η_i] = A⁻¹GᵀR⁻¹y = η^a; Cov[η_i] =
A⁻¹(GᵀR⁻¹·R·R⁻¹G + Q⁻¹·Q·Q⁻¹)A⁻¹ = A⁻¹(GᵀR⁻¹G + Q⁻¹)A⁻¹ = A⁻¹ — the exact posterior.
Marked as standard analysis; U2022's own future-work sentence ("first given in the
parameter space, but then projectable in physical space", Conclusions) cited as the
family's pointer. m members = m extra solves, embarrassingly parallel under
`n_concurrent × peak-G ≤ budget`; generated at the tuned winner ONLY, never per-trial;
batched as multi-RHS block CSR applies (seam a load-bearing). Hours-to-overnight at
the winner's α; m named parameter, **default m=100**.

### 6.2 Cross-window member coherence (D6 hardening 1 — load-bearing)

Independent per-window ensembles blended at seams give Var_blend =
(w² + (1−w)²)·Var — σ suppressed up to √2 at w=0.5: the temporal reincarnation of the
Phase-4/5 seam under-dispersion disease. REQUIRED construction:

- **Identity-keyed common random numbers:** ε′ is a pure function of (seed root,
  member index, OBS identity); η̃ of (seed root, member index, ELEMENT identity).
  Identities are window-independent (global pavement, §2.1; obs identity =
  mission/time/lon/lat), so shared obs and shared elements receive IDENTICAL
  perturbations across windows for the same member. Seed root via `derive_seed`;
  keyed-hash construction is plan detail.
- **Honest residual:** CRN removes the independent-noise √2 suppression; what remains
  (two windows' different posteriors blended) is MEASURED, not assumed:
- **Stage-B seam test (invariant 6):** worst-case-LOCALIZED member dispersion / σ at
  blend days vs window interiors; the §4.4 diagnostic extended to VARIANCE fields at
  α=1.5. Never gate on domain-average coverage alone.

### 6.3 The s-rescale theorem (D6 hardening 2)

Stage B tunes s on VALIDATION calibration only, applied to persisted members as
η′_i = η^a + √s(η_i − η^a): zero re-solves; the shipped mean Γη^a is UNTOUCHED — a
theorem (exact linear-Gaussian analog of ensemble inflation), not a hope. Condition
recorded: uniform scalar R (§2.2). Non-regression test: the Stage-A acceptance map
regenerated under Stage-B code, identical.

### 6.4 MiostEnsembleDistribution (D6 contract, normative)

- Coefficient-space members; `marginal_variance`/`covariance`/`sample` evaluate Γ on
  demand at ANY points — exact-in-members, no nearest-node snap (grid snap would
  inject grid error into the Tier-4 calibration metric at real track points).
- Moments about the MEMBER MEAN, (m−1) denominator; shipped mean map remains Γη^a
  (standard center discrepancy noted). m and MC error √(2/(m−1)) (~14% at m=100)
  recorded beside every variance product.
- `sample(k, seed)`: seeded deterministic subselection for k ≤ m; **k > m RAISES**
  (a persisted distribution carries no solver — never fabricate draws).
- Persistence: NEW representation-tagged kind (Phase-3 sampler_spec-keyed pattern):
  basis spec + η^a (f64) + member ANOMALIES (float32 option halves it). Full-year at
  m=100 ≈ 0.5 GB (α=1.0) to 2.1 GB (α=0.5) = 9 windows × m × N_coef × bytes.
- Down-conversion to the existing grid-stack `EnsemblePredictiveDistribution`
  available via the same per-window S (for evaluators wanting (m, ny, nx)).
- Capability declaration: SAMPLES native; MARGINAL_VARIANCE + COVARIANCE by ensemble
  reduction. Deferred, noted, not built: exact marginals via assembled sparse A + the
  pattern-agnostic Takahashi reduction verified in Phase 6.

### 6.5 PCG tolerance as statistical contract

An under-converged member is a BIASED draw. Same `pcg_rtol` for mean and members,
serialized in params_key (seam f). Designed test: small case, members at loose vs
tight rtol — dispersion bias demonstrated beyond MC noise; documents why the default
is tight and recorded.

### 6.6 Stage-B acceptance

Existing Calibration evaluators (reduced_chi2, coverage_1sigma, crps) on the harness;
same blocked-validation / c2-once discipline; coverage bar auto-present
(capability-derived, §5.3); PLUS the mean-unchanged non-regression (§6.3); PLUS the
seam-dispersion worst-case test (§6.2); PLUS the small-case exactness oracle (§7.3).
Spatial multi-tile stays OUT (§8).

## 7. Validation stack and test plan (owner-decided tiers, verbatim)

### 7.1 The four tiers

- **Tier 1 — exact oracles (the correctness proof):** (i) duality oracle — dense
  obs-space OI with B = ΓQΓᵀ vs the reduced normal-equations path (U2021 Eq. 2 ↔
  Eq. 15), tight rtol, small synthetic (~10² obs, 2-rung ladder); (ii) adjoint
  identity ⟨Gη, r⟩ = ⟨η, Gᵀr⟩ at machine precision; (iii) dense-solve vs PCG on a
  small A.
- **Tier 2 — documented properties:** representer with negative lobe (U2022 Fig. 4);
  hard compact support (exact zeros beyond 1.5λ); ladder spans 80→905, 8 rungs.
- **Tier 3 — similarity, NEVER a gate:** §5.6 diagnostic vs the pinned maps.
- **Tier 4 — THE GATE:** §5.6 procedure; BASELINE 0.85 hard floor; MIOST row
  aspirational; c2 once; calibration bar capability-conditional (N/A Stage A, binding
  Stage B).

### 7.2 Stage-A test inventory

Six seam tests (§3.2 a–f, incl. the λ_ref gauge assertion); cache-correctness (§4.2.4);
mission-absent + zero-obs windows (§4.3); blend partition-of-unity; obs-span assert
fires; `bars_for` + scorer-routing both-directions tests (§5.3);
`CapabilityNotAvailableError` fail-loud test (§5.4); StoredGFeasibility unit tests
(sizing agreement with `miost_sizing`, budget boundary, reason exposure, composition);
required equivalence diagnostic (§4.4) executed + recorded.

### 7.3 Stage-B test inventory

Small-case exactness oracle (ensemble moments → A⁻¹ within MC error); CRN cross-window
identity test (shared obs/element perturbations identical across windows);
mean-unchanged non-regression (§6.3); seam-dispersion worst-case bounded (§6.2);
under-convergence sensitivity test (§6.5); `sample(k>m)` raises; persistence
round-trip; down-conversion consistency (coefficient-space vs grid-stack moments
agree at nodes).

### 7.4 Acceptance criteria

**Stage A:** Tiers 1–2 green; §7.2 inventory green; tuner run with composition +
visible infeasible reasons; c2 once with µ ≥ 0.85; Tier-3 + 12-dir diagnostics
attached; calibration recorded N/A.
**Stage B:** §7.3 inventory green; calibration bars green on validation; c2 once;
mean-unchanged non-regression green; capability upgrade recorded.

## 8. Out of scope (stated, not built)

SkyPilot / remote execution (escalation ladder in PROGRESS; reopen condition is a
MEMORY question); internal tides, equatorial waves, Doppler currents, drifters (brief
§4); spatial multi-tile MIOST (n_tiles=1; Stage-C predicate applies verbatim if ever
tiled); numba matrix-free (rung 1, noted); exact-Takahashi marginals (noted, §6.4);
batch-solve protocol extension (rule-of-three note, §3.1); per-mission R (§2.2
condition recorded).

## 9. Risks (recorded honestly)

- **µ ceiling:** the no-propagation, isotropic power-law prior may cap µ below the
  CLS row (0.89 is aspirational; 0.85 is the gate).
- **Identifiability:** ρ/q_slope on one box may plateau BO — recorded, not fatal.
- **PCG conditioning:** iteration growth at fine α — convergence report surfaced;
  `pcg_maxiter` bounds runaway.
- **Blend-seam µ artifacts:** measured by the required §4.4 diagnostic; fallback
  designed (pavement extension) and predicate-priced.
- **Stage-B seam dispersion residual:** CRN removes the √2 mechanism; the remainder is
  measured worst-case-localized before acceptance (§6.2).

## 10. Provenance of this design

Owner decisions D1–D8 + folds recorded from the 2026-07-03 brainstorm (clarifying
questions → approach forks → section approvals, verbatim in the session transcript).
Method claims trace to the verified brief; measured claims to the Task-0 probe.
The PROGRESS envelope note is amended in the same commit as this spec (probe counts
were box-only; the halo-priced fine-spacing corner is α=0.75, which also clears
12-dir at ~7 GB).
