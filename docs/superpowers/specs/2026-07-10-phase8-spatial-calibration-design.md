# Phase 8 — Spatially varying uncertainty calibration for the MIOST ensemble product

Owner-approved design, brainstorm 2026-07-10. Status: **awaiting owner file review
before writing-plans.**

Prerequisite verified at session start: Phase 7 CLOSED (c2 touch 3 signed off
2026-07-07; capability-flip commit `696e26f` landed; branch even with `origin/main`).

Governing inputs (verified against source this session): Phase-7 spec §6 (D6
s-rescale + σ-semantics), Task-19 gate evidence + localized-calibration table
(`stage_miost_gate_results.json:stage_b`), PROGRESS Phase-7 close entries,
`distributions/miost_ensemble.py`, `methods/miost.py` (shipped factory),
`validation/provenance_guard.py`, `eval/calibration.py`,
`scripts/diag_stage_b_localized_calibration.py`.

## 0. Shape of the phase

Replace the shipped global scalar s\* = 10.062847634082484 with a low-dof spatial
field s(x) applied to member anomalies at query time, so 1σ coverage is right
**regionally**, not just on average. Zero re-solves; mean maps bit-unchanged;
distribution-layer only.

Motivating evidence (measured, Task-19 localized-calibration table at frozen s\*;
n = 46,780 j3 validation points, aggregate coverage 0.7481, CRPS 0.0475 m):

| class | n | coverage_1σ | chi2_red |
|---|---|---|---|
| quadrant_NW | 12,144 | 0.6946 | 1.320 |
| quadrant_NE | 11,447 | 0.6851 | 1.292 |
| quadrant_SW | 11,713 | 0.7881 | 0.777 |
| quadrant_SE | 11,476 | 0.8267 | 0.598 |
| blend / interior | 17,906 / 28,874 | 0.7423 / 0.7516 | 1.101 / 0.938 |
| worst month (Aug) | 3,765 | 0.6632 | 1.491 |
| best month (Nov) | 3,897 | 0.8160 | 0.638 |

The pattern is dominantly latitudinal (both north quadrants ≈ 0.69 under-covered,
both south over-covered) with a secondary longitude signal in the south
(SE 0.8267 vs SW 0.7881). Quadrant split: 300°E / 38°N
(`diag_stage_b_localized_calibration.py:28`).

Settled constraints (from the phase prompt; not re-decided): zero re-solves /
mean bit-unchanged; post-hoc multiplicative anomaly field a′_i(x) = √s(x)·a_i(x);
fit on j3 only, c2 locked until one owner-authorized touch; worst-case-localized
gate with rubric-before-numbers; dof ≪ data (46,780 points; raw per-cell fits
forbidden; positivity via log s); one layer through all query paths; protocols and
evaluators untouched.

## 1. Decision register (forks a–e, owner-decided 2026-07-10)

**(a) Parameterization** — two FIT lanes + one gated diagnostic:

- Lane A (baseline): piecewise-constant log s on a TRUE PARTITION derived from the
  pre-registered regions — the jet-core mask carved out of the quadrants it
  intersects (fit regions must partition; EVALUATION regions may overlap).
  Per-region closed form at σ_obs = 0; 1-d Newton with the noise floor (§4).
- Lane B (smooth): low-order polynomial in log s — quadratic in lat + linear in
  lon, optionally one lat·lon interaction; hard cap ≤ 6 dof.
- Covariate lane: NOT a fit lane yet. The ensemble-σ variant is KILLED on the
  theorem: posterior covariance = (GᵀR⁻¹G + Q⁻¹)⁻¹ is independent of obs VALUES;
  with geography-constant Q and scalar R (the shipped Stage-A config), raw
  ensemble σ tracks SAMPLING GEOMETRY, not the jet — mechanically misaligned with
  signal-driven representation error. The SIGNAL-VARIANCE proxy (per-cell temporal
  std of the shipped Stage-B mean maps — deterministic from signed artifacts,
  hence pinnable) gets a mandatory, near-free ALIGNMENT DIAGNOSTIC (§7 step 0)
  with a pre-registered promotion rule: correlate per-~2°-cell miscalibration
  (log chi2 / coverage deficit) against the proxy; |r| ≥ 0.6 → promote to a third
  fit lane (log s affine in the proxy, 2 dof, covariate definition serialized into
  the calibration key); else → future work WITH the measured correlation recorded.
- Selector honesty (recorded): held-out regional coverage cannot separate lanes
  beyond noise (per-fold regional coverage SE ≈ ±1% at ~2k points), so the tie
  rule is pre-registered WITH its reason: statistical tie → the SMOOTH field wins
  (no artificial steps in shipped σ maps at region boundaries; continuous field;
  graceful edge behavior; same dof). Held-out CRPS + a ~2°-cell coverage table are
  non-bar tiebreak evidence.
- Both lanes reduce exactly to s\* (identity: piecewise = all regions s\*;
  poly = a₀ = log s\*, rest 0).

**(b) Fit criterion** — Gaussian MLE in log s, one criterion for all lanes, with
four riders (§4): the variance decomposition r ~ N(0, s(x)·v + σ_obs²) is
load-bearing; information weighting forces a spatially-contiguous holdout family;
a pre-registered tail diagnostic (report-only, no mid-phase estimator switch);
full determinism (fixed init, named optimizer + tolerance in the calibration key,
likelihood-vs-scalar safeguard assert).

**(c) Seasonal axis** — spatial-only s(x) this phase. Recorded deferral reasons
(the honest ones): (i) ONE YEAR of data — a seasonal climatology is
unidentifiable from 2017's specific weather (n = 1 Augusts); a fitted harmonic
risks encoding one year's anomalies as climatology; (ii) spatial/seasonal
CONFOUNDING — jet variability peaks late summer, so the post-s(x) monthly
residual is the measurement that sizes any true seasonal axis; (iii) dof +
serialization economy. Explicitly NOT recorded as a reason: "harmonics cannot be
validated by held-out-month rotation" — a low-order harmonic is interpolation at
a missing phase point and IS so validatable; only free month-dummies are not.
The monthly table (§6) is the pre-registered decision instrument. Decision aid
(no auto-scope): if post-fit worst-month held-out coverage remains below the
regional band, that TABLES a seasonal-axis proposal for owner decision, with the
note that a defensible s(x, season) wants multi-year data or a climatological
covariate, not harmonics on one year. s(x, month) = named future axis with its
epistemic cost (n = 1 years), not just its dof cost.

**(d) Fold protocol** — temporal + spatial-block families; cycle-alternating
REJECTED (j3 is an exact-repeat ~9.9-day orbit — every cycle flies the same
ground track, so cycle folds hold out zero new geography). Details §5.

**(e) Edge behavior** — coordinate-clamp to the box hull + value-clip in log s,
with evidence-anchored clip bounds, clip observability reporting, and the
inertness test. Details §9.

## 2. Mechanism and identities

**Query-time multiplicative field on member anomalies:** a′_i(x) = √s(x)·a_i(x),
applied at EVALUATION time inside `MiostEnsembleDistribution` — NOT
construction-time pre-scaling. There is NO constant-field fast path — one general
eval-time path serves everything including the scalar (owner decision, batch-1
review: a fast path makes the s\*-identity test exercise only the old code).

Two row-scaling sites carry the whole layer (both fed by one `_sqrt_s(lon, lat)`):

- `_anoms_at(pts)` — rows × √s(lon, lat): the Γ-path (arbitrary-point queries),
  `covariance()` both sides, `member_at`.
- `_grid_eval(self._anoms, t)` — node rows × √s on the grid: the S-path
  (`marginal_variance`, `to_grid_ensemble`, `sample`, down-conversion).

Mean paths are never touched → mean maps bit-unchanged BY CONSTRUCTION; the
(µ, σ, λx) triplet depends only on the mean → bit-identity provable.

**Identity (i) — correlation preservation (TESTED):**
Cov′(x, y) = √(s(x)s(y))·Cov(x, y) ⇒ Corr′ = Corr exactly (pointwise positive
scaling; falls out of `covariance()` since both sides route through `_anoms_at`).
Cross-point covariances and derived cross-point uncertainties change by
√(s(x)s(y)) — intended; folded into the σ-semantics paragraph (§10). NOTE
(recorded): correlation preservation is blind to magnitude (any positive
pointwise scaling passes), so the test inventory includes the direct MAGNITUDE
test: on a non-constant test field,
`marginal_variance(x) = s(x)·v_uncal(x)` pointwise, analytic.

**Identity (ii) — scalar reduction (TESTED):** s(x) ≡ s\* reproduces the shipped
scalar product. Tolerance-based (rtol ~1e-12 — float re-ordering only:
`S@(√s·a)` vs `√s·(S@a)`), as a regression vs the signed Stage-B artifacts on ALL
FOUR routes: grid (S-path), arbitrary-point Γ, covariance, and `sample()`
moments. The load-bearing BIT claim stays the mean maps (untouched by
construction).

**Variance decomposition (load-bearing, rider b1):** the fit likelihood is

    r_i ~ N(0, s(x_i)·v_i + σ_obs²)

with v_i = UN-inflated ensemble variance at the track point and σ_obs² the
obs-noise floor (anchor: R_ref = (0.03 m)², Phase-7 spec §2.2). s scales the
ENSEMBLE-ANOMALY variance only — representation error lives in the map,
instrument noise in the track. A naive s×(total variance) fit inflates s(x) most
where ensemble variance is smallest (on-track) — a sampling artifact aliased into
the field. The spec's implementation plan must derive the piecewise estimator and
the poly gradient WITH the noise term.

**Fit inputs named (simplification bought by the raw-anoms convention, §8):**
v_i comes directly from the persisted RAW artifacts — `save_state` writes
anomalies as generated; s\* is applied by the METHOD at construction
(`miost.py:473`, factory `inflation_s` at line 713). No un-scaling step exists.
Source artifacts: the signed Stage-B mean/var maps + the persisted coefficient
ensemble at the accepted config (m = 100, root 4836134738817689931).

**Reconciliation with Task-19 (recorded comparison):** the scalar s\* was
computed as `reduced_chi2(mu, var, ssh)` with no noise term — s\* ABSORBED the
floor. Phase 8's constant-field fit ŝ (with the floor) will differ from s\*; the
gap is quantified and recorded in the evidence, and the semantics delta is
carried into §10.

## 3. Parameterization lanes

As registered in §1(a). Additional normative points:

- Lane 0 (control): constant s\*, evaluated on the identical folds and
  statistics as the fit lanes. Pre-registered ELIGIBILITY rule: a fit lane must
  beat lane 0 on the PRIMARY statistic beyond the ±1% band AND be no worse than
  lane 0 (within band) on the SECONDARY. If no lane qualifies → pre-registered
  negative-result path: ship the scalar, record the finding, NO c2 touch spent
  (owner confirms the close).
- The covariate alignment diagnostic runs BEFORE any fit lane (§7 step 0), from
  existing artifacts only.
- All lanes fit in log s (positivity); clip per §9.

## 4. Fit criterion

Gaussian MLE in log s under r ~ N(0, s(x)·v + σ_obs²), all lanes:

- **Lane A:** per-region 1-d NEWTON on the exact MLE (deterministic; keeps
  one-criterion-all-lanes literally true under the floor). The σ_obs = 0 limit
  `s_R = mean(r²/v)` (= per-region chi2_red = 1, the D6-consistent closed form)
  is recorded and used as the Newton init.
- **Lane B:** Newton/BFGS over ≤ 6 coefficients; fixed init a₀ = log s\*
  (rest 0); named optimizer + tolerance serialized into the calibration key.
- **Safeguard assert (loud):** converged lane-B likelihood ≥ the s\*-constant
  solution's — catches optimizer failure; never ship a silently-worse-than-scalar
  field.
- **Tail diagnostic (pre-registered, report-only), floored form:** per region,
  compare the mean-based fit against the median-consistency of
  r²/(ŝ·v + σ_obs²) vs its χ²₁ expectation (median 0.4549) — stated in the
  floored model so quiet regions do not flag phantom heavy tails that are just
  the floor. Divergence ≥ 1.5× = recorded heavy-tail evidence, interpreted at the
  gate (coverage/CRPS); NO estimator switch mid-phase.
- CRPS reported on every fold and at the gate; never optimized. Coverage stays
  the gate metric.

## 5. Fold protocol and lane selection

**T-folds:** 6 rotations of fit-10 / verify-2 CONTIGUOUS months; month rotations
recorded in the spec/plan (deterministic).

**S-folds:** contiguous ~2° lon×lat blocks; 4 folds partitioning the blocks at
~25% of track points held out per fold; deterministic, committed fold assignments
(seeded block layout; seed recorded). Leakage control (load-bearing — residuals
are correlated along-track and over ~L_t): (i) a ±0.5° spatial GUARD RING around
each held-out block, excluded from BOTH fit and scoring; (ii) per-block EFFECTIVE
sample size reported — n_eff = n / (1 + 2·Σρ̂), with the along-track residual
autocorrelation ρ̂ measured once and recorded; minimum n_eff per block with a
pre-registered merge rule for blocks below it. Constraint: every lane-A fit
region keeps ≥ 50% of its points in every fold. Held-out coverage is never
quoted at nominal n.

**Selection statistic (pool-then-max, per family):** per evaluation region, pool
held-out points across that family's folds (n ≈ 10k+, coverage SE ≈ 0.5%),
compute |coverage − 0.6827| on the pooled set, take the worst region.
Max-of-small-samples averaged over folds is rejected (the Stage-C worst-of-pairs
pathology).

**Combination rule (lexicographic; stated generically so a promoted covariate
lane slots in):** lane-0 eligibility (§3) applies first; then PRIMARY = S-fold
pooled worst-region deficit; ties (±1% band) → T-fold statistic; ties again →
the smooth lane wins (§1(a) reason recorded). Winner refit on ALL of j3 (final
coefficients from the full track); fold machinery retained as recorded evidence.

**Off-track blind spot — bounded, not just declared (both report-only,
pre-registered):** (i) max|∇log s| over the box + the implied max inter-track
excursion of s for the winning field (analytic bound; ≤ 6 dof smoothness between
tracks 1–3° apart); (ii) stated explicitly: the c2 acceptance touch IS the
off-track test — CryoSat-2 is a non-repeat orbit filling the inter-j3-track
gaps — which is why the pre-registered c2 reading includes the REGIONAL coverage
breakdown, not aggregate only. No j3 fold protocol can test off-track behavior;
that limit is recorded.

## 6. Pre-registered regions and bars (rubric-before-numbers)

Committed in this spec BEFORE any s(x) is fit (Task-18 precedent).

**Evaluation regions:** quadrant_{SW, SE, NW, NE} (300°E / 38°N split, as shipped
in `diag_stage_b_localized_calibration.py`) + jet_core + aggregate. Evaluation
regions may overlap (jet_core straddles the north quadrants).

**Jet-core mask (explicit, deterministic from SIGNED artifacts):** grid cells
where the per-cell temporal std of the shipped Stage-B mean maps ≥ its 75th
percentile over the box, reduced to the largest 4-connected component; no manual
edits. Threshold + component rule pre-registered here. The same proxy field is
the §1(a) covariate-diagnostic input.

**Lane-A fit partition:** the 4 quadrants each minus the mask, plus the mask
= 5 regions (true partition).

**Bars at final coefficients (on j3):**

1. Aggregate coverage ∈ 0.6827 ± 0.10.
2. EVERY evaluation region ∈ 0.6827 ± 0.10. This is a real tightening: under
   scalar s\*, SW 0.7881 and SE 0.8267 sit OUTSIDE the band (top edge 0.7827) —
   the south side fails today, not just the north.
3. Worst region strictly improved vs the scalar record, stated on the DEFICIT
   statistic |coverage − 0.6827| (the §5 selection metric): the scalar record's
   worst region is SE 0.8267, deficit 0.1440 (NE 0.6851 has deficit 0.0024 — the
   BEST region; min-coverage is the wrong statistic under over-coverage). The
   phase prompt's 0.69 round number is also recorded for continuity. Bar (3) is
   subsumed by (2) once corrected (0.10 < 0.144); kept for continuity with the
   phase prompt, NOT independently binding.
4. No region regressing out of band — subsumed by (2); stated for continuity.

DISCLOSED: bars (1)–(4) are computed on j3, which the final field was fit on.
The guards are the held-out-fold selection (§5) and the independent c2 regional
reading (§7).

**Report-only instruments (pre-registered):**

- Monthly table (the fork-(c) decision instrument): held-out-fold monthly
  coverage + chi2 for the fitted s(x), side-by-side with the frozen-s\* baseline
  column (Aug 0.663/1.49, Sep 0.693, Nov 0.816, …); the delta column measures how
  much seasonal signal was spatially collocated; the residual column is the
  honestly-sized known limitation. Never a bar.
- Per-region chi2 table, fitted vs s\*, with jet-core's post-fit chi2 named as a
  recorded outcome (the chi2 ~1.3-at-nominal-coverage signal motivated this
  phase; coverage remains the only bar — no rubric change).
- Tail diagnostic (§4), clip observability (§9), off-track bound (§5),
  ŝ-vs-s\* reconciliation (§2), 2°-cell coverage table + held-out CRPS (§1(a)).

## 7. Evidence design and the one c2 touch

Execution order (pinned):

0. Covariate alignment diagnostic FIRST, from existing artifacts only
   (localized-calibration arrays + shipped mean maps) — before any fit lane runs;
   promotion rule §1(a).
1. Fold fits + lane selection (§5), lane-0 eligibility (§3).
2. Winner refit on full j3; field FROZEN here.
3. Bars §6 + all report-only instruments.
4. STOP — owner reviews the j3-side evidence.
5. Owner-authorized SINGLE c2 touch at the frozen field (nothing refit on c2).
   Pre-registered reading: (µ, σ, λx) triplet BIT-IDENTICAL to the signed
   Stage-A values (mean untouched is provable; ANY deviation = defect → STOP);
   aggregate c2 coverage ∈ 0.6827 ± 0.10 → sign-off; PLUS the regional c2
   coverage breakdown reported (report-only; severe deviation = recorded, owner
   call, no refit); chi2_red + CRPS recorded as the honest generalization
   numbers. One touch per accepted product (standing discipline); provenance
   guard active throughout; negative-result path (§3) spends NO touch.
6. On sign-off: capability-flip commit (registry `"miost"` → field-calibrated
   factory) carrying the updated σ-semantics paragraph (§10). Until then the
   field is opt-in (flip discipline unchanged from Phase 7).

**Test inventory (new):**

- Correlation preservation: non-constant field, Corr′ == Corr (tight rtol).
- Magnitude: `marginal_variance(x) = s(x)·v_uncal(x)` pointwise, analytic,
  non-constant field.
- s\*-identity regression at rtol ~1e-12 vs signed Stage-B artifacts on all four
  routes: grid (S-path), arbitrary-point Γ, covariance, `sample()` moments.
- Mean-unchanged non-regression EXTENDED to the field-calibrated product: the
  Stage-A acceptance map regenerated under field-calibrated code, bit-identical.
- Byte-compat THROUGH THE FACTORY: shipped σ values pre/post-refactor at the
  default config (a save/load roundtrip test can pass against a wrong premise;
  the factory-boundary comparison cannot).
- Inertness beyond box+halo: calibrated `marginal_variance` == uncalibrated to
  machine precision (§9).
- Piecewise clip-inert assert (§9); composition test for `rescaled()` (§8);
  no-stale-cache test for the per-grid √s cache (§8); save/load roundtrip with
  field spec; kind-tag refusal unchanged; lane-B likelihood safeguard assert.
- Full suite green; pre-commit clean; framing-parity + provenance-guard tests
  untouched and passing.

## 8. One-layer seam and serialization

**CalibrationField hierarchy** (in `distributions/miost_ensemble.py`):
`ScalarCalibration(s)`, `PiecewiseCalibration(partition_def, log_s per region,
clip)`, `PolyCalibration(coeffs, hull, clip)`; a promoted covariate lane adds
`CovariateCalibration(proxy_ref, affine, clip)`. Common interface:
`sqrt_s_at(lon, lat)` + `key()` — a deterministic calibration key hashing kind +
all params + clip bounds + fit-provenance ids (optimizer, tolerance,
fold-protocol id).

**Single application point:** one private `_sqrt_s(lon, lat)` on the
distribution, consumed at exactly the two row-scaling sites of §2. Per-grid √s
cached once, keyed by grid id — safe because the calibration is IMMUTABLE per
instance: `rescaled()`/new-calibration returns a fresh instance (no-stale-cache
test). `rescaled(s)` is reimplemented THROUGH the same layer (API kept, one
mechanism) and COMPOSES multiplicatively — today
`rescaled(s).rescaled(t)` = anoms × √(st); preserved and tested.

**ONE-CONVENTION persistence (corrected on verified source facts):** persisted
anomalies are RAW — `save_state` writes them as generated; s\* is applied by the
METHOD at construction (`miost.py:473`:
`ens if self.inflation_s == 1.0 else ens.rescaled(self.inflation_s)`; the
shipped factory passes `STAGE_B_INFLATION_S`), and s\* was fit FROM the raw
members' variance, so the signed artifacts are necessarily un-inflated. The rule
for legacy AND new files alike: raw anoms on disk; calibration applied at eval by
the layer. Legacy files (no cal keys) load with NO baked field, and the FACTORY
supplies `ScalarCalibration(STAGE_B_INFLATION_S)` exactly where it supplies
`inflation_s` today — shipped behavior preserved at the factory boundary (pinned
by the factory byte-compat test, §7). This also buys the §2 simplification: the
fit's v_i comes straight from the persisted raw artifacts; no un-scaling step
exists.

**Persistence keys:** `KIND` stays `"miost-coeff-ensemble"`; npz gains
`cal_kind` + `cal_params` (json) + `cal_key`.

**Provenance:** new `TransformKind.FIELD_INFLATION` carrying
{calibration_key, cal_kind, dof}; scalar products keep `DIAGONAL_INFLATION`
(backward compat). Core `Method`/`PredictiveDistribution` protocols untouched —
the provenance module is ours.

**Cache-safety:** the calibration key is folded into the Miost `params_key`
(factory gains a calibration argument), so every cached or persisted artifact
distinguishes scalar vs field product.

## 9. Edge behavior (normative)

s(x) := field evaluated at coordinates CLAMPED to the box hull (piecewise lane:
nearest-region continuation), THEN log s CLIPPED to [L, U].

- **Clip bounds from evidence, not from the poly's excursions:** [L, U] = range
  of the lane-A per-region MLE log-s values (the evidence-dense closed-form
  estimates), padded ×/÷ 1.25 — a ≤ 6-dof quadratic's extrema sit where the fit
  is least constrained; the guard rail anchors to where evidence lives.
  [L, U] + hull + pad factor serialized in the calibration key.
- **Clip observability (report-only, pre-registered):** fraction of box+halo
  grid nodes where clamp/clip engaged + the max engaged excursion
  (log s_raw − log s_clipped). A guard rail that engages on real nodes is a
  recordable fact, not a silent absorption (explain() discipline).
- **Inertness pinned by test, not prose:** beyond box+halo the basis has compact
  support — anomalies ~0, the layer multiplies zero. Unit test asserts calibrated
  `marginal_variance` == uncalibrated to machine precision out there, so a future
  basis-config change fails LOUDLY at the assumption.
- Piecewise lane: within [L, U] by construction — the clip is provably inert on
  that lane; asserted.

## 10. σ-semantics paragraph (replaces the scalar paragraph in the shipped factory docstring at flip time)

Shipped σ = calibrated predictive uncertainty via a LOW-DOF SPATIAL FIELD s(x)
(kind, dof, calibration key, fit-on-j3 recorded), fit by Gaussian MLE in log s
WITH the obs-noise floor. SEMANTICS DELTA from the scalar product, stated
explicitly: map σ² = s(x)·v(x) EXCLUDES the obs-noise floor (the scalar s\* had
absorbed it); the floor is added only when validating against along-track
residuals; the constant-field ŝ-vs-s\* reconciliation number recorded. σ still
includes representation error + unresolved scales; it is NOT raw posterior
spread. Correlation structure is preserved EXACTLY (pointwise positive scaling);
cross-point covariances and derived cross-point uncertainties scale by
√(s(x)s(y)) — intended, stated. Coverage (aggregate + per pre-registered region)
and CRPS are the evidence; the chi2 identity is per-fit-region (lane A) or
in-likelihood (lane B), not global. Edge clamp/clip behavior named. Jet-core and
monthly residual limitations recorded with numbers.

## 11. Out of scope (stated, not built)

- Q(x)/R(x) or any re-solve-based recalibration (method change).
- Any change to mean maps.
- Reopening Task-20/windowing; spatial multi-tile; per-mission R.
- s(x, month)/seasonal axis — deferred per fork (c) with the n = 1-years
  epistemic rationale + the decision-aid trigger (no auto-scope).
- Lat-varying METHOD parameters: the Phase-5 invariant-12 deferral
  (LatitudeVaryingProvider et al.) stays intact — this phase is a
  DISTRIBUTION-layer calibration field, not a solver parameter.

## 12. Provenance of this design

Owner decisions recorded from the 2026-07-10 brainstorm: forks (a)–(e) each
decided with riders (fork a: two lanes + covariate promotion rule + tie rule;
fork b: MLE + variance decomposition + fold requirement + tail diagnostic +
determinism; fork c: spatial-only with corrected rationale + monthly instrument +
demoted trigger; fork d: T+S folds + guard rings + pool-then-max + off-track
bound; fork e: clamp+clip with evidence-anchored bounds + observability +
inertness test), then three design-section review batches (batch 1: fast path
deleted, floored Newton, semantics delta, floored tail diagnostic; batch 2:
deficit-statistic bar restatement, lane-0 + negative-result path, lexicographic
rule, fold pinning; batch 3: raw-anoms persistence correction on verified source
facts, factory-boundary byte-compat test, composition/immutability pinning).
Repo claims verified against source this session: Phase-7 closure (PROGRESS
banner + git), the localized-calibration table (gate results JSON), the
query-path choke points and `rescaled` construction-time application
(`miost_ensemble.py`, `miost.py:473`), quadrant split constants
(`diag_stage_b_localized_calibration.py:28`).
