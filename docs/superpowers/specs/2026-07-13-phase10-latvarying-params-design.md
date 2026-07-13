# Phase 10 — Latitude-Varying Method Parameters (design)

Owner-approved brainstorm, 2026-07-13 (five forks a–e + three design batches,
each ruled with pins/folds; all rulings folded below verbatim-intent). Governs
the Phase-10 implementation plan on conflict.

**Goal:** Resolve invariant-12, option B: solver-input parameter FIELDS —
signal_variance(lat) and length_scale(lat) — fed into the OI solve via a
low-dof `LatitudeVaryingProvider`. This changes means AND uncertainties,
requires re-solves, and is judged by the Phase-9 measurement layer
(harness + wrapper + flattening instrument). SCOPE = OI ONLY this phase
(Phase-9 spec §5: "Phase 10 re-solves OI and supersedes it").

**Prerequisite verified at session start:** Phase 9 CLOSED and pushed —
close banner + Task-8 owner ruling in PROGRESS; HEAD = `1438c6d`;
`origin/main` even; tree clean.

---

## §0 Scope basis + anchor disambiguation

1. **Invariant-12 resolution shape (owner-recorded, Phase-9 spec §0.3):** the
   tuner remains scalar-box — NO tuner rewrite. Fields enter as
   `LatitudeVaryingProvider`: named low-dof forms with 2–3 scalar
   coefficients per varied parameter, normalized coordinate
   v = (lat − 38)/5 (the Phase-8 convention — the same v as
   `PolyCalibration`, verified against
   `distributions/calibration.py:183-194`), positivity via exp/log links.
   The provider translates tuned scalars → fields at solve time.
2. **MIOST-B OUT OF SCOPE, recorded:** a post-reading owner decision, with
   the honest note that MIOST's ~10× under-dispersion (s* = 10.06) is
   plausibly representation-dominated — a prior-parameter fix may barely
   move its field; the flattening instrument will say.
3. **ANCHOR DISAMBIGUATION (guard, literal):** `phase9.g_pre_anchor`
   (0.13510401012055406; frame = phase8 mask sha `6c2802f5…`, fold seed
   tuple ("miost","phase8","s-folds")) is **MIOST's** anchor — NEVER this
   phase's. This phase's anchor is **G_pre_oi**, recomputed canonically
   from `phase9.oi.fit_run` (§7). Any Phase-10 artifact or task that cites
   0.13510401 as its baseline is a defect.
4. Untouched (constraint 8): protocols; the tuner core; GMRF/FEM/MIOST
   methods; the provenance guard; the one-touch-per-accepted-product
   discipline; blocked withholding.

## §1 Motivating evidence + expectation-setter

- **Contrast finding (Phase-9 close, verified against
  `phase9.oi.fit_run`):** OI's raw posterior OVER-disperses ~34%
  (ŝ_OI = 0.6621056512171348, the constant-lane MLE WITH SIGMA_OBS2 —
  construction distinct from MIOST's s*, per the recorded
  shat_reconciliation note) while spatial structure wins selection
  decisively (poly S = 0.04475391131041362 vs lane-0 0.31562355406538145;
  bars 1–4 in band; Jaccard vs p8 = 1.0). Two opposite prior pathologies
  across methods, one instrument.
- **Quad-V motivation pinned to THIS product's artifact (fork-b pin 4):**
  `phase9_field_oi.json` poly coefficients (basis
  log s = a0 + a1·v + a2·v² + a3·u + a4·u·v, u = (lon−300)/5,
  v = (lat−38)/5): [0.0204, 0.7800, **−2.2191**, −0.0525, 0.5673] —
  a2 < 0 is a downward parabola in latitude, i.e. the measured mid-box
  bump. Not inherited from MIOST's shape.
- **Physics:** the Rossby radius shrinks with latitude → constant L is a
  known misspecification. **Degree-space honesty note (fork-b pin 1,
  load-bearing for interpretation):** the signed kernel's
  constant-in-degrees zonal scale already varies ~13% in km across the box
  via cos φ (93→81 km/deg, 33→43°N). L(lat) multipliers act ON the
  degree-space scales (stays in the signed family); the implicit cos-φ
  variation is recorded and never attributed to tuned l1; the physics
  expectation is the Rossby decline BEYOND cos φ.
- **Expectations:** f varies only ~25% across this box → gains expected
  MODEST; the payoff scales with domain (global ambition; this box is the
  testbed). Hard floor µ ≥ 0.85 stands; aspirational anchors are never
  hard gates.
- **V-stage reframe (fork-a mod 1, pre-registered):** a lat-only
  posterior-variance correction is largely WITHIN the post-hoc s(x)
  layer's span — V(lat)'s unique contribution is mean-side reweighting
  (Q scaled, R fixed → means move) + sublinear posterior-variance shaping.
  Stage 1 is therefore the MACHINERY stage plus one genuine measurement:
  how much of OI's post-hoc field is prior-variance-shaped. Success =
  flattening credit + no skill regression; a skill win is NOT promised and
  its absence is NOT a negative result. The stage-1 close states which
  outcome occurred (structure moved into the prior vs product materially
  improved) — never conflated.

## §2 Provider architecture + forms

- **`LatitudeVaryingProvider` superseded IN PLACE.** Archaeology (one
  honest sentence, batch-1 fold 1): the Phase-1 class resolved
  `correlation_length`, a name OI's solve never requests (oi.py:119-121) —
  the invariant-12 deferral was never runtime-load-bearing; Phase 10 makes
  the vehicle real. Consumer census (verified): THREE test files migrate —
  `tests/test_latitude_varying_provider.py`,
  `tests/test_tiling_partition.py`, `tests/test_tiling_coordinator.py`.
  No shim.
- **Forms (fork b):**
  - `variance(lat) = exp(c0 + c1·v + c2·v²)` — 3 dof, exp link. PD-SAFE by
    construction: σ(x)·σ(y)·ρ(x,y) is an outer scaling of a valid
    correlation (the √(s(x)s(y)) algebra of Phase 8/9, applied to the
    PRIOR).
  - `length(lat)`: ONE shared multiplier on lx_deg AND ly_deg =
    `L0·exp(l1·v)` — 2 dof, preserves the signed 1:1 anisotropy,
    degree-space family. NOT PD-safe by substitution — requires the
    Paciorek–Schervish construction (§3).
  - `time_scale` (Lt): constant-TUNED in all lanes; only its LAT-variation
    deferred (fork b — no measured lat-structured temporal evidence; dof +
    solve cost), reason recorded.
- **One parameterization, lanes as restrictions (batch-1 fold 2):** every
  lane tunes the single core {c0, log-L0, Lt}; lane-0 freezes
  c1 = c2 = l1 = 0; V releases (c1, c2); VL-joint releases l1. One
  provider path, one solve path; nesting BY CONSTRUCTION (the
  constant-reduction test verifies the kernel identity, not lane
  bookkeeping); paired seeds comparable on shared dims. No lane-specific
  parameterizations anywhere.
- **Boxes (principles pinned; endpoints = plan detail, recorded with
  rationale there):** log-space excursion caps on (c1, c2) so the max
  field swing over v ∈ [−1, 1] is bounded and recorded — sized against the
  measured OI log-s span [−1.5414, 0.3928] (**source: the clip [L, U] in
  `phase9_field_oi.json`, lane-A range ± log 1.25** — batch-1 fold 4);
  l1 box includes 0 AND BOTH SIGNS (the Rossby sign is a falsifiable
  prediction, not a constraint; asymmetric room with rationale is fine);
  c0/log-L0/Lt boxes bracket the signed values (c0 ≈ 0 ↔ variance 1.0;
  L0 ≈ 1.0°; Lt ≈ 7 d).
- **RESOLVE/DISPATCH CONTRACT — SPEC-LEVEL, the invariant-12 seam
  (batch-1 fold 3):** `ParameterProvider.resolve` returns
  `float | LatitudeField` (a small typed value carrying the named form +
  coefficients, evaluable at latitudes); `OptimalInterpolation.solve`
  dispatches ON TYPE: all-scalar resolution → the stationary kernel path
  UNCHANGED (`ConstantProvider` untouched, returns floats → the
  byte-identical baseline path holds BY CONSTRUCTION, regression-pinned
  anyway); any field resolution → the nonstationary kernel (§3).
  `params_key`/provenance serialize the named form + coefficients (the
  tuned config is reconstructible from provenance alone).

## §3 Nonstationary kernel (Paciorek–Schervish; fork c)

- **Interface verified — no seam extension needed (fork-c pin 1 resolved):**
  `Kernel.evaluate(a, b)` receives absolute (n,3) lon/lat/time point sets
  (kernel.py:19-21; `GaussianSpaceTimeDegrees.evaluate` computes dlon from
  absolute columns). New class implementing the existing Protocol;
  `GaussianSpaceTimeDegrees` untouched → the signed baseline path is
  byte-identical trivially; the regression test pins it anyway.
- **Closed form (recorded; fork-c pin 4):** spatial factor per pair
  (x, y), L evaluated at each point's latitude:

  prefactor = L(x)·L(y) / [(L(x)² + L(y)²)/2]   (scalar-diagonal, d = 2;
  ≤ 1 by AM–GM), and the exponent uses the averaged local scales in the
  signed convention exp(−d²/L²):

  k_s(x,y) = prefactor · exp( −Δlon²/L̄² − Δlat²/L̄² ),
  L̄² = (L(x)² + L(y)²)/2

  composed with the STATIONARY temporal Gaussian factor (fork-c pin 2 —
  nonstationary construction on the SPATIAL factor only; Lt constant per
  fork b; PD by product of PD kernels) and with V's outer σ(x)·σ(y)
  scaling. Constant reduction is EXACT: prefactor → 1 and the exponent →
  the stationary form at l1 = 0 (verified by re-derivation at the fork
  ruling).
- **Convention by test (fork-c pin 3):** the exact-reduction test's
  reference is the SHIPPED `baseline_kernel()` implementation itself at
  c1 = c2 = l1 = 0 (bit where achievable, else rtol ~1e-15) — exponent/
  normalization mismatches fail loudly; no reimplemented reference.
- **REQUIRED TESTS (settled constraint 2 — load-bearing math):**
  (i) PD test — assemble K on the pinned geometry (max-L-contrast pairs at
  the extreme latitudes + a dense mid-box cluster); assert
  min eigenvalue ≥ −tol, tol scaled to the matrix norm.
  (ii) constant-reduction identity — coefficients at the constant limit
  reproduce the stationary kernel exactly, covering the FULL space-time
  kernel (Phase-8 identity-test style).
  Both land and pass BEFORE any stage-2 tuning begins (fork-a mod 4).
- **Prior variance routing:** `_stationary()` (oi.py:84-86) returns False
  for the new class → the diag branch; the Paciorek prior diagonal is
  analytically σ²(lat) (prefactor → 1 at x = y; owner-verified) — a
  pointwise prior-variance method avoids O(n²) diag assembly (plan
  detail).
- **Cost:** ~2× kernel-eval flops, assembly only; the §4 runtime probe
  measures the Paciorek path explicitly.

## §4 Tuning protocol (forks a + d)

- **Task-0 RUNTIME PROBE (hard precondition for all budget numbers):**
  measure one full-year OI re-solve (mean + var maps, 365 days, train-only
  obs) at the signed config AND one through the Paciorek path. Per-lane
  trial budget derived from the measurement, recorded with its arithmetic
  at `phase10.oi.probe`. Budgets are set from measurement, never
  assumption.
- **Screening contingency (pre-registered; constants committed TOGETHER
  before any trial runs — batch-2 fold 3):** if full-year-per-trial is
  infeasible, trial scoring runs on a FIXED stratified day subset (the
  pinned day list) with full-year re-scores of each lane's top-k before
  lane selection; the day list AND k are recorded in the same
  pre-registration artifact; the SAME subset serves all lanes (paired
  screening). The cross-lane COMPARISON always reads full-year scores.
- **Staging (fork a):** Stage 1 = the MACHINERY stage — provider seam +
  dispatch contract + lane protocol + paired seeds proven; V lane tuned;
  stage-1 flattening reading = the V-vs-s(x) adjudication (§7). Stage 2 =
  VL-JOINT: V coefficients re-opened alongside l1 (~6 dof, one problem),
  warm-started from the stage-1 V winner + l1 = 0 as an anchored evaluated
  point. Greedy/frozen staging REJECTED (ordering bias: V-under-constant-L
  absorbs structure L(lat) explains; combined lane lands off-optimum;
  attribution muddied). Stage 1 is NOT a science gate for stage 2: L
  proceeds regardless of the V lane's outcome (independent Rossby
  motivation); stage 1 gates only that the machinery works. Paciorek +
  PD + constant-reduction tests green BEFORE stage-2 tuning.
- **Lane set:** {lane-0 tuned-constant, V, VL-joint}, identical protocol
  and budget, paired seeds. L-only lane CONDITIONAL on the probe showing
  sweeps cheap (records the fourth 2×2 cell); otherwise noted as not run,
  with the probe number as the reason.
- **Search:** Sobol-primary, equal trial counts per lane, product-scoped
  seed derivation (recorded in evidence); BO optional rounds only if the
  budget allows (Phase-7 record cited: BO lost to Sobol at n = 16).
  **Anchor embedding pre-registered:** the lane-0 winner is evaluated
  inside V and VL (released coords at 0); the V winner inside VL
  (l1 = 0). Nested lanes therefore tie-or-win by construction on the
  selection read — the negative result reads "improvements within band,"
  never "lat-varying worse" (batch-2 fold 1 wording pin).
- **Bars during tuning (capability-derived, Phase-5 precedent):**
  `bars_for(SAMPLES)` → µ ≥ 0.85 hard floor + raw-posterior coverage bar.
  **Coverage-bar convention pinned (batch-2 fold 2):** raw posterior
  variance + SIGMA_OBS2 floor — ONE convention with the acceptance bar at
  s ≡ 1; no tuning-vs-acceptance fork. **Recorded expectation:**
  ŝ_OI = 0.6621 → baseline raw coverage ≈ 0.78, at the band's top edge —
  the bar is LIVE for this product; variance-increasing trials tripping it
  is the design working, not a defect (pre-registered so bar-binding
  clusters aren't misread at execution). Inadmissible trials recorded,
  never selected.
- **Selection layer (fork-d pin 3; no tuner rewrite):** each lane's
  winner = the same lexicographic read (§5) over that lane's bar-passing
  VALIDATION trial records — a selection layer over tuner outputs; the
  tuner's native objective (`ConstrainedObjective`, min λx s.t. bars) is
  verified at design time and left untouched.
- All trial scoring validation-side (j3), train-only assimilation,
  `assert_scored_not_assimilated` on every map-to-track call; c2 never
  imported.

## §5 Lane-comparison protocol (pre-registered; the falsifiable claim)

- **The claim:** lat-varying beats TUNED-CONSTANT (lane-0) beyond the
  measured band on the validation track — NOT "beats the signed 0.853"
  (the signed OI is BASELINE-FAITHFUL, untuned; beating it confounds
  tuning-at-all with latitude variation).
- **PRIMARY COMPARISON (batch-2 fold 1, kills selection multiplicity):**
  the claim-bearing test is **VL-JOINT winner vs lane-0 winner** — a
  single primary. V-vs-lane-0 and the conditional L-only cell are
  SECONDARY/attribution rows: same bands, reported, never claim-bearing.
- **Rule (fork-d pin 1, lexicographic µ → λx):** a lat lane BEATS lane-0
  iff Δµ > band_µ; if |Δµ| ≤ band_µ, then Δλx > band_λx breaks the tie
  (finer resolution wins) — λx-win-at-flat-µ IS a win (the L(lat) physics
  signature), not a companion; both within bands → tie → counts toward the
  negative result.
- **BOTH BANDS MEASURED, recorded BEFORE any cross-lane read
  (rubric-before-numbers; fork-d pin 2):** band_µ = 2×SE of paired Δµ via
  block resampling of per-point squared-error differences (blocks
  respecting the measured along-track/temporal correlation — the existing
  n_eff machinery); band_λx = 2×SE of the SNR-crossing estimate via the
  same block-bootstrap unit (pre-registered unit: contiguous day/pass
  segments). SELF-CALIBRATION note recorded: if band_λx is too wide to
  inform, the tie-break cannot fire and the rule degrades to µ-primary —
  record "λx uninformative at measured band," never a noisy verdict.
- Winner vs winner; paired-seed trial clouds reported as context with the
  honest note that pairing is partial across different-dof lanes.
- **Negative result (settled constraint 7):** NO lat lane beats lane-0
  under the rule → record, spend NO c2 touch; whether the tuned-CONSTANT
  winner is worth its own acceptance is a separate owner election.

## §6 Pipeline + acceptance template instantiated for a MEAN-CHANGING product

Pipeline (ordering pinned): winning lat-lane config re-solved → full-year
mean + var maps persisted with provenance → **means committed → NEW mask**
from the winner-config-derived means (pre-registered rule verbatim:
75th-percentile temporal std → largest 4-connected component, no manual
edits; provenance = source-map hash + rule constants) → **post-hoc s(x)
fit** via the Phase-9 harness, j3-side, NEW descriptor: evidence key
`phase10.oi.fit_run`, NEW product-scoped fold-seed tuple (new lineage,
distinct from ("oi","phase9","s-folds")), `jet_core_ref_p8` row + Jaccard
vs p8 AND vs the pre-B OI mask (same-method predecessor, Phase-9 spec
§11.1 item 3) → **flattening reading** (§7, frozen pre-B frame) →
**OWNER GATE 1** (j3 evidence: lane comparison + fit evidence + reading)
→ **OWNER GATE 2** (fresh authorization, never pre-authorized: ONE c2
touch — skill + calibration-at-the-fitted-field).

**TWO HARNESS RUNS, NEVER CONFLATED (batch-2 fold 4):** the
frozen-pre-B-frame run produces G_post (comparison only; phase-9 OI frame
verbatim incl. the salt-4 fold layout); the NEW-frame acceptance fit
produces the shipped field + bars. Separate descriptors, separate evidence
keys, separate artifacts.

**Template adaptation (settled constraint 5, spelled out):** there is no
prior signed triplet to reproduce — **the acceptance IS the new
(µ, σ, λx)**. The bit-identity tripwire generalizes to **DETERMINISM**:
the c2 touch scores the exact persisted maps the gate reviewed — sha256
content-hashes of the mean + var maps asserted at touch entry against the
gate-reviewed hashes; NEVER a re-solve at touch time. **Generalized window
tripwire verbatim (Phase-9 spec §6.3):** the calibration block and the
triplet block consume the IDENTICAL track from ONE loader — n_points +
date-span asserted EQUAL between blocks and spanning the full challenge
year; the recorded count 44,844 asserted too. **Touch mechanics verbatim
(Phase-9 spec §6.4):** one invocation writes acceptance; corrected runs
require an explicit owner flag, valid only while a dated defect key exists
and acceptance is absent; a third invocation refuses; defects spend
touches; disclose, never launder; honest per-product tally. Aggregate
coverage at s(x)·v + SIGMA_OBS2 ∈ 0.6827±0.10 → SIGN-OFF; outside → HOLD,
record, no refit. Regional breakdown + chi2_red + CRPS report-only.

The shipped product carries its OWN (expected smaller/flatter) calibration
field — B does not retire the Phase-9 layer; it shrinks what the layer
must absorb.

## §7 Flattening instrument (Phase-9 spec §7c verbatim, OI frame)

- **Statistic:** G = lane-0 S-stat − winner S-stat (pooled worst-region
  deficit units), computed by the standard fold/selection machinery
  verbatim (absolute ±0.01 band, lexicographic rule, eligibility incl.
  lane-0). ENTIRELY j3-side — the instrument never touches c2.
- **Anchor:** **G_pre_oi** recomputed canonically from
  `phase9.oi.fit_run` at implementation (expected value
  0.27086964275496783 = 0.31562355406538145 − 0.04475391131041362; the
  pinned recomputation is the canonical anchor, the arithmetic here is the
  expectation), stored at `phase10.g_pre_oi_anchor` with definition +
  frame block. The §0.3 guard applies: `phase9.g_pre_anchor` is MIOST's.
- **Post-B readings under the FROZEN pre-B OI frame:** mask sha
  `0deefcb961a3092279ca5de30852d65fffcbade304b19de0cb9e6a5d35ef0058` on
  BOTH sides; fold-seed tuple ("oi","phase9","s-folds"); identical fold
  layout — pre-B record: s_salt final 4, redraws [0,1,2,3] — asserted,
  any redraw difference recorded; same fit constants (SIGMA_OBS2, lanes,
  promotion rule); covariate proxy re-derived from the post-B product's
  own signed means per the standing rules.
- **A reading after EACH stage's winner (fork a):** the stage-1 reading is
  the V-vs-s(x) adjudication measurement.
- **Companions (report-only):** area-weighted std of log s of the SHIPPED
  (clipped) field on a fixed grid (std primary, max−min secondary) +
  clip-engagement fraction; the pre-B OI companion values are computed
  from `phase9.oi.fit_run` / `phase9_field_oi.json` at implementation and
  recorded beside the anchor. The raw NLL gap stays DEMOTED (dof + n_eff
  attached, no threshold semantics).
- **Conservative-bias note verbatim:** three lanes give structure-detection
  multiple chances, so the instrument is CONSERVATIVE for flatness claims;
  the negative-result firing = "no detectable residual spatial structure
  at ±0.01 ≈ 2 SE."
- **Purpose statement (fork-a mod 1):** the instrument credits only
  structure that moves INTO the prior — that is its purpose; the
  prior-side variance(lat) vs post-hoc s(x) overlap is adjudicated here,
  not by skill.

## §8 Ship shape — registry role-split + flip discipline (fork e)

- **Role-split.** `METHODS` = tunable-method table, bare classes only;
  `"oi"` UNCHANGED (bare-method consumers undisturbed). NEW `SHIPPED`
  table in `registry.py` = flagship product factories.
  `"miost": shipped_miost` MIGRATES into SHIPPED this phase — retiring the
  registry caveat comment (the landmine dies this phase).
  `"oi": shipped_oi` enters SHIPPED **only in the post-sign-off flip
  commit**.
- **Lookup rule (spec-level):** a name lives in exactly ONE table; lookups
  are explicit per call site; NO fallback-chaining helper (a
  resolve-either helper silently re-creates the ambiguity the split
  kills). Product-scoring/shipping paths read SHIPPED; tuning/search paths
  read METHODS. **Mechanized (batch-3 fold 1):** unit tests assert
  METHODS ∩ SHIPPED = ∅ (double registration fails in CI) and `"miost"`
  absent from METHODS post-migration (`"miost-point"` remains, disposition
  accepted as ruled).
- **Consumer census (verified against source, recorded):** dynamic
  `METHODS[...]` sites — `validation/run.py:148,220`,
  `application/solve.py:43`, `tuning/scorer.py:127`,
  `tuning/stage_a.py:76`, `scripts/diag_miost_ndir12.py:88/98` (the
  diag script MUTATES `METHODS["miost"]` — migrates to a SHIPPED-side
  lookup). Shipped-side consumers (gate runners, `run_challenge_map`
  invocations with `method_name="miost"`, README examples) enumerated and
  migrated in the plan; bare-method consumers (8 test files + tuning
  paths) confirmed untouched.
- **Flip discipline verbatim:** the flip commit = SHIPPED-table update +
  σ-semantics + README/records + honest touch tally + **FULL external
  sweep — the external-sweep standing rule's FIRST APPLICATION, cited
  explicitly (the rule was born from a flip that skipped it: the Phase-8
  T5 stale pin, fixed `b5b44a1`; rule recorded in Phase-9 spec §6.6).**
- **Two-field hygiene:** `phase9_field_oi.json` is demonstration-only
  FOREVER (fitted to the baseline-config product); the shipped product
  carries the phase-10 winner's OWN post-hoc field (§6 pipeline). The
  σ-semantics paragraph tells the two-layer story: prior-side lat
  structure (named form + coefficients recorded) + residual post-hoc s(x)
  field, with the flattening numbers as evidence.
- **Records:** the signed baseline triplet (0.853 / 0.090 / 140.9,
  PROGRESS:1511) is the baseline-faithful config's permanent record; the
  B-winner gets its own acceptance triplet + artifacts under NEW
  names/keys (`phase10.oi.*`, new acceptance nc) — never overwrite the
  signed artifact or phase-9 evidence (content-hash determinism tripwire
  per §6); `baseline_config()`/`baseline_kernel()` retained verbatim as
  the harness regression oracle + config-audit path, registry-independent,
  with the oracle comparison test intact post-flip. Never deleted.
- Rejections recorded: new registry name (flagship identity forks +
  stale-"oi" silent consumers); ship-without-wrapper (constraint 4).

## §9 Testing plan (red/green per task; each test names the bug it catches)

- **Provider:** named-form field values vs hand-computed
  exp(c0 + c1·v + c2·v²) / L0·exp(l1·v) at pinned latitudes; `resolve`
  returns float for constants, the field type for varied params;
  `params_key` stability + coefficient distinctness; migration of the
  THREE consumer test files (§2).
- **Dispatch (the invariant-12 seam):** ConstantProvider path
  byte-identical — the signed config through the new solve path reproduces
  fixture-day means/vars bit-identically + the external acceptance pin
  unchanged; field path routes to the Paciorek kernel; the type-dispatch
  contract unit-pinned.
- **Kernel:** the §3 PD test (pinned geometry) + constant-reduction
  identity vs the SHIPPED `baseline_kernel()` (full space-time kernel,
  bit where achievable else rtol ~1e-15); pointwise prior-variance =
  σ²(lat) vs a brute-force diag cross-check. Both PD + reduction green
  BEFORE stage-2 tuning (enforced by plan task ordering).
- **Lane machinery:** restriction bookkeeping (lane-0 trial records carry
  c1 = c2 = l1 = 0 exactly); anchor embedding present in each lat lane's
  trial set; lexicographic selection-layer unit tests incl. the
  band-degradation branch (λx uninformative → µ-primary + recorded note);
  **rubric-before-numbers as code** — the comparison function REQUIRES the
  persisted band artifact to predate lane-winner records, else refuses.
  **REFUSAL CLOCK PINNED (batch-3 fold 3):** the refusal compares RECORDED
  timestamps inside the JSON artifacts (band-artifact write-time vs
  lane-winner-record write-time), never filesystem mtimes (which churn
  under git operations).
- **Paired seeds (batch-3 fold 2a):** same trial index yields IDENTICAL
  shared-dim draws across lanes, differing only on released coordinates.
- **Band determinism (batch-3 fold 2b):** seeded block resampling, the
  seed recorded INSIDE the band artifact, reproducibility test.
- **Bars:** `bars_for(SAMPLES)` wiring for OI (µ floor + coverage bar);
  coverage convention = raw posterior variance + SIGMA_OBS2 (batch-2
  fold 2); the ≈0.78 baseline expectation recorded next to the bar
  constant.
- **Registry (batch-3 fold 1):** METHODS ∩ SHIPPED = ∅ disjointness test;
  `"miost"` absent from METHODS post-migration.
- **Harness reuse, two runs never conflated:** descriptor-construction
  tests for BOTH runs (new-frame acceptance vs frozen-frame reading)
  asserting distinct evidence keys, seed tuples, mask paths, artifact
  paths; the frozen-frame run asserts mask sha `0deefcb9…` + the salt-4
  fold layout before fitting.
- **Tripwires:** determinism — the touch runner content-hash assert on the
  persisted maps, with a test proving hash mismatch → defect-STOP exit
  nonzero; window — one loader feeds both blocks, n_points/date-span
  equality asserted, the 44,844 count asserted.
- Full suite green throughout; test-design skill standards.

## §10 Evidence design

Evidence keys (gate results JSON, atomic writes):
- `phase10.oi.probe` — Task-0 measurements + derived budget arithmetic.
- `phase10.oi.lanes` — trial records incl. inadmissible, band artifacts
  (with recorded write-time + resampling seed), per-lane winners, the
  PRIMARY comparison verdict (VL vs lane-0) + secondary attribution rows.
- `phase10.g_pre_oi_anchor` — the §7 anchor + companions + frame.
- `phase10.oi.flattening_stage1` / `phase10.oi.flattening_stage2` —
  G_post readings, frozen frame, companions incl. clip engagement.
- `phase10.oi.fit_run` — the acceptance fit (new frame).
- `phase10.oi.c2_acceptance` — the touch, on sign-off.

Regional/monthly report-only tables per the standing pattern; pre/post-B
regional comparisons use the PRE-B OI mask frozen as the reference frame
for BOTH sides (Phase-9 spec §7(d) rider). Negative-result path: lanes +
readings recorded, NO c2 touch, the tuned-constant election flagged as a
separate owner item.

## §11 Out of scope (state, don't build)

MIOST-B (post-reading owner decision; §0.2 honest note); GMRF (below the
BASELINE floor, µ = 0.835); seasonal axes; global domain; tuner-core
changes; Q(x)/R(x); spatial multi-tile; time_scale(lat) (fork b); per-axis
L split (fork b — any future case starts from the §1 implicit-anisotropy
note); any change to shipped Phase-8/9 artifacts; protocols, provenance
guard, one-touch discipline, blocked withholding untouched.

## §12 Fork rulings + batch folds record (owner, 2026-07-13, verbatim-intent)

- **Fork (a)** — both parameters, staged V→L, FOUR MODS: (1) V-stage
  reframed as machinery + one genuine measurement (§1); (2) stage-2 tuning
  JOINT, greedy/frozen staging rejected (§4); (3) final lane set
  {lane-0, V, VL-joint} + conditional L-only (§4); (4) stage 1 gates
  machinery only, Paciorek tests before stage-2 (§3/§4). Rejected: joint
  one-lane (no attribution, Paciorek on the critical path day one); V-only
  (physics lever skipped, hollow-relocation risk); L-only (attribution
  forfeited, hardest math first).
- **Fork (b)** — V = exp(c0+c1v+c2v²), L = L0·exp(l1·v) shared lx=ly,
  degree-space family, time_scale lat-variation deferred; FOUR PINS:
  degree-space honesty note (§1); nested lanes / pinned composition (§2);
  box principles (§2); evidence citation pinned to
  `phase9_field_oi.json` (§1). Rejected: quad-L (dof without physics);
  axis-split (no evidence).
- **Fork (c)** — Paciorek–Schervish, claims verified by re-derivation;
  FOUR PINS: kernel-interface verification first (resolved: absolute
  point sets, no seam extension, §3); separability (spatial factor only,
  §3); convention by test (§3); closed form + PD-test geometry recorded
  (§3). Rejected: banding (knobs + seam machinery approximating what the
  closed form gives exactly).
- **Fork (d)** — lexicographic µ→λx with measured bands; FOUR PINS: the
  rule (§5); both bands measured before read + self-calibration (§5);
  selection consistency, no tuner rewrite (§4); companions report-only
  (§5/§7). Rejected: µ-primary alone (blind to the λx-at-flat-µ physics
  win; its band discipline adopted); λx-primary (verdict-by-noise; µ is
  the floor/leaderboard currency).
- **Fork (e)** — registry ROLE-SPLIT (§8), five items: split; flip
  discipline + external-sweep first application; two-field hygiene;
  records under new names/keys; rejections (new registry name;
  ship-without-wrapper).
- **Batch-1 folds:** (1) census correction — THREE provider test
  consumers + the name-mismatch archaeology sentence (§2); (2) one
  parameterization, lanes as restrictions (§2/§4); (3) resolve/dispatch
  contract spec-level (§2); (4) box-span provenance to
  `phase9_field_oi.json` clip (§2).
- **Batch-2 folds:** (1) PRIMARY comparison = VL-joint vs lane-0, single
  claim-bearing test + the tie-or-win wording pin (§5); (2) tuning
  coverage-bar convention pinned + the ≈0.78 live-bar expectation (§4);
  (3) contingency constants committed together (§4); (4) two harness
  runs never conflated (§6/§7).
- **Batch-3 folds:** (1) registry rule mechanized — disjointness +
  absence tests (§8/§9); (2) paired-seed test + band-computation
  determinism test (§9); (3) refusal clock = recorded JSON timestamps,
  never filesystem mtimes (§9).

## §13 Spec self-review record

Checked against the session prompt + all five fork rulings + the eleven
batch folds: no placeholders/TBD; settled constraints 1–8 each land in a
section (1→§0/§2; 2→§3/§9; 3→§5; 4→§6; 5→§6; 6→§7; 7→§1/§5; 8→§0.4);
anchor disambiguation stated twice (§0.3, §7) as demanded; the two harness
runs distinct in §6, §7, §9, §10; G_pre_oi arithmetic verified against
`phase9.oi.fit_run` (0.31562355406538145 − 0.04475391131041362); frozen
frame carries mask sha + seed tuple + salt-4 layout + redraw record;
MIOST-B out-of-scope with the representation-dominated note (§0.2, §10,
§11); negative-result semantics identical in §1, §4 (wording pin), §5,
§10. Verified against source during brainstorm: `Kernel.evaluate` absolute
point sets (kernel.py:19-21,70-75); OI float coercion (oi.py:118-122);
`_stationary` routing (oi.py:84-86); `PolyCalibration` basis + v
convention (calibration.py:183-194); registry census (13 import sites;
dynamic lookups enumerated in §8); `LatitudeVaryingProvider` three test
consumers; signed triplet (PROGRESS:1511); ŝ_OI/mask-sha/fold-salt/
selection numbers (gate results JSON); `phase9.g_pre_anchor` =
MIOST-frame confirmed. Single-implementation-plan sized: provider +
kernel + lanes/tuning + pipeline + flip ≈ Phase-8/9 task granularity.
Ambiguity check: "±0.01-equivalent" resolved to measured band_µ/band_λx
(§5); "staging" resolved to machinery-stage semantics (§1/§4); LatitudeField
dispatch shape pinned (§2).
