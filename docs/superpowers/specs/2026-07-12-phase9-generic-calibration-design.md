# Phase 9 — Method-Generic Spatially Varying Uncertainty Calibration (design)

Owner-approved brainstorm, 2026-07-12 (two scope forks + three design batches,
each ruled with pins; all rulings folded below verbatim-intent). Governs the
Phase-9 implementation plan on conflict.

**Goal:** Lift Phase 8's distribution-layer calibration field s(x) from a
MIOST-internal seam to a method-agnostic layer: a capability-aware
`CalibratedDistribution` wrapper any `PredictiveDistribution` can carry, a
generalized per-product fit harness, the migrated (identity-proven) MIOST
product, and one OI j3-side demonstration — delivering the measurement layer
and interface contract Phase 10 (lat-varying METHOD parameters) is judged by.

**Zero c2 touches in this phase.**

---

## §0 Owner-committed scope basis (first fork ruling, 2026-07-12)

1. **PHASE 9 = the generic calibration layer (A). PHASE 10 = lat-varying
   METHOD parameters (the invariant-12 item, B) — OWNER-COMMITTED scope, not
   a decision aid.** Recorded here and in PROGRESS: B is "deferred TO
   Phase 10", with the A/B boundary carried forward: A = post-hoc s(x) on the
   distribution's uncertainty, zero re-solves, means untouched; B = solver
   input fields (e.g. correlation_length(lat) via a LatitudeVaryingProvider
   shape), changes means AND uncertainties, re-solves, per-method tuning
   gates.
2. **Sequencing rationale (recorded):** (i) instrument-before-experiment — B
   changes means and uncertainties via re-solves, so it must be judged by the
   spatially-resolved calibration/skill harness A generalizes; don't debug
   the measurement layer in the phase that changes what it measures; (ii) A's
   per-product fitted s(x) fields are B's TARGETING EVIDENCE (where priors
   are spatially misspecified) and the basis of B's acceptance instrument;
   (iii) A is permanent, not scaffolding — s* ≈ 10 is dominated by
   representation error + unresolved signal, which no solver-parameter field
   erases; post-B products still carry a (smaller, flatter) field.
3. **Invariant-12 resolution shape (recorded now):** the tuner remains
   scalar-box; Phase 10 parameterizes fields as low-dof scalar-coefficient
   providers (the Phase-8 pattern one layer down — e.g. correlation_length(lat)
   as a named 2–3-coefficient form). No tuner rewrite.
4. **Expectation-setter (recorded):** f varies only ~25% across this box
   (sin 43° / sin 33°), so Phase-10 gains HERE are expected modest; the
   payoff scales with domain — tie Phase-10 bars to the global ambition.

## §1 Scope & deliverables

Deliverables: (1) the generic wrapper + shared CalibrationField home (§2);
(2) the migrated MIOST product, identity-proven, no dual mechanisms (§3);
(3) the generalized per-product fit harness (§4); (4) exactly ONE non-MIOST
demonstration: OI, j3-side only, no ship, no touch (§5); (5) the per-product
acceptance TEMPLATE as the standing pattern (§6); (6) the Phase-10 interface
contract incl. the pinned field-flattening instrument and the recomputed
**G_pre anchor** (§7). GMRF explicitly deferred (its product sits below the
BASELINE floor, µ = 0.835 — calibrate it when it's worth shipping). Each
future product = its own fit + its own gate + its own single c2 touch; never
batched.

## §2 Architecture — `CalibratedDistribution` (one general path)

New shared module `src/sverdrup/distributions/calibration.py`:
- The four `CalibrationField` classes (`ScalarCalibration`, `PolyCalibration`,
  `PiecewiseCalibration`, `CovariateCalibration`) + `ClipSpec` +
  `calibration_from_json` MOVE here from `miost_ensemble.py` — clean break,
  callers updated, no import-compat shim. Constants stay in
  `application/calibration/constants.py`.
- `CalibratedDistribution`: wraps any `PredictiveDistribution`, implements the
  protocol, capability-aware, ONE general path (the Phase-8 fast-path-deletion
  lesson):

| underlying capability | wrapper behavior |
|---|---|
| POINT | construction RAISES `CapabilityNotAvailableError` (nothing to calibrate) |
| MARGINAL_VARIANCE | `marginal_variance()` → s(x)·v(x); covariance/sample delegate-raise per underlying |
| COVARIANCE | + `covariance(a, b)` → √s(a)·C·√s(b) (outer scaling; correlations preserved exactly) |
| SAMPLES | + `sample(m, seed)` → mean + √s(x)·(draws − mean), pure protocol delegation |

Mean routes: raw delegation — bit-identity by construction, still TESTED per
product. `with_calibration` composition and `rescaled` scalar-only semantics
(RAISES on a field-calibrated instance — the Phase-8 owner narrowing) carry
over unchanged. Per-grid √s memoized once per instance (immutable fields ⇒
cache safe; reset on with_calibration).

**PIN A — NO-RAW-LEAK CONTRACT (batch-1 ruling).** The wrapper's full exposed
surface is enumerated and classified; nothing else is exposed:
- protocol trio (`marginal_variance` / `covariance` / `sample`): scaled per
  the table;
- `mean_at`: raw delegation;
- `member_at` (where underlying provides it): mean + √s·(member − mean);
- `to_grid_ensemble` (where provided): rebuild the returned stack about its
  mean with grid-node √s;
- Gaussian `regrid`: `CalibratedDistribution(underlying.regrid(target),
  same field)` — re-wrap carrying the same field;
- `save_state` / `load_state`: WRAPPER-OWNED (raw arrays + cal keys —
  calibration lives on the wrapper now; persistence follows it).
Blind `__getattr__` passthrough is FORBIDDEN; a leak test pins it (a marker
method on a stub underlying must NOT surface on the wrapper). Module helpers
(`std_fields`, `merged_members`, diagnostics) consume public routes only — no
`._anoms` reach-ins; the migration suite passing against the wrapper is the
proof.

**PIN B — REQUIRED-SURFACE.** The wrapper requires `underlying.grid` (+
`time_days` where applicable) for grid-valued scaling — named, verified on
both shipping classes (`distributions/gaussian.py` grid attribute;
`MiostEnsembleDistribution.grid`). The underlying's capability is passed
EXPLICITLY at construction (no introspectable attribute exists on the
distribution classes); the POINT raise keys off it.

**PIN C — CAL_KEY STABILITY.** A test asserts the MOVED CalibrationField code
reproduces the shipped `phase8_field.json` `cal_key` BYTE-identically —
`key()` must not hash module paths or reprs that change with the move (the
gate runner asserts this key).

**PIN D — PROVENANCE SINGLE-APPEND.** The raw ensemble stops appending
inflation transforms; the wrapper appends (FIELD_INFLATION for fields,
DIAGONAL_INFLATION with incremental s for scalars — semantics unchanged).
The identity suite gains transform-SEQUENCE equality vs the shipped product
(npz byte-compat does not cover provenance).

**PIN E — OP-REORDER NOTE (recorded).** Old seam = √s-scaled anomalies then
squared; wrapper = s-scaled variance — same algebra, different float order;
the rtol-1e-12 identity suite covers it BY DESIGN (the fast-path-deletion
decision). NO byte claims on variance routes; mean routes stay bit.

## §3 MIOST migration (no re-fit, no c2, no dual mechanisms)

`MiostEnsembleDistribution` drops its internal √s application (raw anomalies
always, no calibration field on the class); `Miost.solve`'s ensemble branch
returns `CalibratedDistribution(raw_ens, self._calibration)`. Factory API
(`Miost(calibration=...)`, `inflation_s` shim, registry, `shipped_miost()`)
unchanged — the shipped product is constructed identically from the caller's
view. Persistence moves WITH the calibration to the wrapper (PIN A): same npz
keys, same legacy rule (files without cal keys load scalar-1.0; the factory
supplies the field), roundtrip tests preserved. MIOST-internal efficiency
paths (S-path grid queries) stay in the raw class; the wrapper's scaling
composes on top exactly as the internal seam did.

**Migration gate:** the Phase-8 identity suite passes UNCHANGED against the
wrapper-built product — four routes at rtol 1e-12, mean bit-identity
(fixture + external acceptance-map pin), factory byte-compat fixture, PLUS
the PIN-D transform-sequence equality. NO re-fit; NO c2; product unchanged,
mechanism relocated. The shipped σ-semantics paragraph's MECHANISM pointer is
updated (CalibratedDistribution, with an explicit no-semantic-change note) —
batch-3 fold 4.

## §4 Generalized fit harness

`phase8_fit_run.py`'s orchestration is promoted into
`src/sverdrup/application/calibration/harness.py`, parameterized by a
**ProductDescriptor**:

```
product_id; mean_maps_path; var_maps_path; track source (j3 + scope config);
mask_artifact_path; proxy_source; evidence_key; field_artifact_path;
fold_seed_tuple  # ← SEED SCOPING (batch-2 item 1)
```

**Seed scoping (batch-2 item 1):** the fold-seed derivation tuple is a
descriptor FIELD. MIOST's descriptor carries the FROZEN Phase-8 tuple
("miost", "phase8", "s-folds", salt — salt path reproduced by the
deterministic constraint check), else the leaf-identical harness regression
is unsatisfiable. New products get product-scoped tuples (e.g. "oi",
"phase9", "s-folds", salt), recorded in evidence.

Method-agnostic by construction: the harness consumes track-interpolated
mean/var from the product's MAPS (the Phase-5 tuner precedent) — it never
sees method internals. All math stays in the tested modules
(folds/likelihood/regions); the harness is glue running the pre-registered
sequence: step-0 covariate alignment (per-product promotion decision,
standing |r| ≥ 0.6 rule) → mask build from the product's signed-config-derived
means (ORDERING PINNED: signed-config-derived means, committed before any
fit — calibration never touches means, so the mask is fixed before any s(x)
exists; batch-2 item 4 wording) → ρ̂/n_eff/merge → T+S families over lanes
0/A/B (+covariate iff promoted) → `select` (ABSOLUTE ±0.01 band, owner
ruling) → winner refit + evidence-anchored clip → per-product evidence block
(`phase9.<product>.fit_run`) + field artifact (`phase9_field_<product>.json`),
atomic writes, c2 never imported. Regions per the fork-1 ruling (§11.1):
per-product mask gate frame + `jet_core_ref_p8` report row + Jaccard drift
row.

**Harness regression (load-bearing):** harness on the MIOST descriptor must
reproduce the Phase-8 `fit_run` evidence LEAF-IDENTICALLY (modulo key naming)
and the shipped field byte-exactly. Then the **G_pre anchor** is recomputed
by the harness under the §7 pinned definition and recorded at the named home
`phase9.g_pre_anchor` (+ PROGRESS close entry) — the Phase-10 brainstorm
consumes it by reference (batch-3 fold 4).

`scripts/phase9_fit_run.py` = thin CLI over the module (dev/full scope
discipline + {dev,full} validation, atomic writes — the Phase-8 pattern).

## §5 OI demonstration (j3-side only; no ship, no touch)

Verified: the signed OI artifact (`OSE_ssh_mapping_OURS_OI.nc`) is MEAN-only.
The demo therefore generates full-year daily OI mean+variance maps at the
**signed OI config** from the oi-validation phase — winner params verified
against the phase-4b results JSON at implementation, NEVER re-tuned (batch-2
item 4). Obs = train-only under the standing split (c2-locked /
j3-validation, grid-node halo framing). Maps written with
assimilated-missions provenance (untracked artifacts, `oi_{mean,var}_maps.nc`).
Runtime measured at dev smoke (12-day scope) before the full-year run.

Then the harness runs the OI descriptor end-to-end: step-0 alignment (OI's
own proxy + promotion decision), OI mask (pre-registered rule on
signed-config-derived OI means, committed before any fit), lanes/folds/
selection, bars 1–4 + all report-only instruments, `jet_core_ref_p8` +
Jaccard rows. Output: OI evidence pack + `phase9_field_oi.json`, explicitly
marked DEMONSTRATION-ONLY: no registry change, no c2 access, no shipped
calibrated-OI (Phase 10 re-solves OI and supersedes it; shipping later is a
separate owner election, default no).

**Wrapper integration on OI (batch-2 item 2 — closes the Gaussian-path gap;
migration proves only the ensemble branch):** after the fit, construct
`CalibratedDistribution(regenerated OI product, fitted field)` and require
(a) held-out coverage recomputed THROUGH THE WRAPPER == the harness's
map-side number (tight rtol); (b) pointwise `marginal_variance` == s(x)·v
against the maps. "What the harness fit is what the wrapper ships," as a
test.

**OI interpretation note (batch-2 item 3, pre-registered):** OI's posterior
passed the Phase-5 calibration bars, so a constant-lane ŝ_OI near 1 is a
plausible and INFORMATIVE outcome (GP-posterior calibration under the
floored convention) — ŝ_OI is recorded either way; a near-flat field or a
lane-0 win is a finding, not a failed demonstration. The negative-result
branch is live: the demonstration goal is the harness, not the field.

## §6 Per-product acceptance TEMPLATE (standing pattern for all future
products, including Phase 10's)

1. Signed-config-derived means committed → mask (pre-registered rule) →
   step-0 alignment + promotion decision → j3 fit/folds/bars via the harness
   (per-product seed tuple, per-product regions + `jet_core_ref_p8` row).
2. OWNER GATE 1: j3-evidence review → PROCEED / NEGATIVE-CLOSE / REWORK.
3. OWNER GATE 2 (fresh authorization, never pre-authorized): ONE c2 touch —
   the product's own signed (µ, σ, λx) BIT-IDENTITY tripwire + the
   **generalized WINDOW TRIPWIRE (batch-3 fold 1)**: the calibration block
   and the triplet block consume the IDENTICAL track from ONE loader —
   n_points + date-span asserted EQUAL between blocks and spanning the full
   challenge year (forbids the two-loaders-one-runner defect class itself;
   needs no historical constant; portable to first-time products; where a
   recorded count exists, assert it too) — + aggregate coverage at
   s(x)·v + SIGMA_OBS2 ∈ 0.6827±0.10 → SIGN-OFF; outside → HOLD, record, no
   refit. Regional breakdown + chi2_red + CRPS report-only.
4. **TOUCH MECHANICS (batch-3 fold 2, standing per the Phase-8 precedent):**
   one invocation writes acceptance; corrected runs require an explicit owner
   flag, valid only while a dated defect key exists and acceptance is absent;
   a third invocation refuses. Defects spend touches; disclose, never
   launder; honest per-product tally.
5. Capability-flip commit with σ-semantics carrying the product's measured
   numbers.
6. **EXTERNAL-SWEEP RULE (owner, Task-8 ruling 2026-07-13, standing):** any
   commit that changes shipped-product semantics — capability flips above
   all — re-runs the FULL external/artifact-gated suite before close;
   externals are part of "green". (Origin: the Phase-8 flip left its T5
   external factory pin scalar-era and unexercised; surfaced at the Phase-9
   migration gate, fixed in `b5b44a1`.)

Phase 9 itself spends ZERO touches (MIOST migration identity-proven; OI
demonstration j3-side).

## §7 Interface contract delivered to Phase 10

(a) Per-product fitted s(x) field artifacts + evidence packs (MIOST shipped
field; OI demonstration field).
(b) The method-agnostic harness (§4) + wrapper (§2) as the measurement layer
Phase 10 is judged by.
(c) The **FIELD-FLATTENING INSTRUMENT** (second fork ruling, pinned):
1. STATISTIC: G = lane-0 S-stat − winner S-stat (pooled worst-region deficit
   units), computed by the standard fold/selection machinery verbatim
   (absolute ±0.01 band, lexicographic rule, eligibility incl. lane-0).
   ENTIRELY j3-side — the instrument never touches c2 (touches belong to
   product acceptance, not to this comparison).
2. FRAME + FOLDS PINNED for pre/post-B comparability: frozen pre-B product
   mask on BOTH sides AND identical fold layout (same T_FOLDS; same S-fold
   salt expected from same track + frozen regions — assert, record if a
   redraw differs). Same fit constants (SIGMA_OBS2, lanes, promotion rule;
   covariate proxy re-derived from the post-B product's own signed means per
   the standing rules).
3. READING = SHRINKAGE against a recorded anchor, not a binary: Phase 9
   delivers **G_pre** by ONE recomputation under this pinned definition from
   existing Phase-8 arrays (raw numbers imply 0.1790 − 0.0439 = 0.1351; the
   pinned recomputation is the canonical anchor), stored at
   `phase9.g_pre_anchor`. Phase 10 sets its bar on gap REDUCTION (expected
   modest here — the ~25% f-variation note, §0.4). FULL-FLAT semantics: the
   harness's negative-result firing (no lane eligible) = "no detectable
   residual spatial structure at ±0.01 ≈ 2 SE" — with the recorded bias
   note: three lanes give structure-detection multiple chances, so the
   instrument is CONSERVATIVE for flatness claims.
4. COMPANIONS (report-only): area-weighted std of log s of the SHIPPED
   (clipped) field on a fixed grid (std primary, max−min secondary), PLUS
   clip-engagement fraction (a flattening field stops hitting its rails;
   37.2% is the pre-B anchor). The raw NLL gap is DEMOTED: reported with dof
   and n_eff attached, NO threshold semantics — AIC's 2·dof penalty assumes
   independent samples and under-penalizes ~10× at the measured
   autocorrelation (n_eff ≈ n/10.27); as defined it cannot return its null
   verdict.
(d) FROZEN-FRAME RIDER (fork-1 ruling item 4): pre/post-B regional
comparisons for a method use the PRE-B product's mask frozen as the reference
frame for BOTH sides (B changes means, hence masks; a moving frame confounds
"coverage improved" with "region moved"). The flattening statistic is
region-frame-pinned per (c)2 and unaffected.
(e) Invariant-12 resolution shape + (f) expectation-setter: §0.3–0.4.

## §8 Testing plan

- **Identity/migration suite (the migration gate):** Phase-8 four-route
  regression (rtol 1e-12) + mean-bit (fixture + external acceptance-map pin)
  + factory byte-compat + external var-map double pin pass UNCHANGED against
  the wrapper-built product; NEW: PIN-D transform-sequence equality; PIN-C
  cal_key byte-stability across the move; PIN-A no-raw-leak stub test; PIN-B
  required-surface checks.
- **Wrapper unit tests** on BOTH a Gaussian stub and the MIOST fixture:
  capability table row by row incl. POINT raise at construction,
  √(s(x)s(y)) covariance, sample-moment scaling, memoization/no-stale-cache,
  mean bitwise, composition + rescaled-raises. **FORWARDED-ROUTE tests by
  name (batch-3 fold 3):** `member_at` scaling; `to_grid_ensemble`
  stack-rebuild about its mean; Gaussian `regrid` re-wrap carrying the SAME
  field.
- **Harness regression:** harness-on-MIOST leaf-identical to the Phase-8
  evidence + byte-exact field artifact.
- **OI integration (batch-2 item 2):** wrapper-recomputed held-out coverage
  == harness map-side number (tight rtol); pointwise marginal_variance ==
  s(x)·v.
- PIN-E recorded: variance routes rtol 1e-12 by design; mean routes bit.
- Full suite green throughout; red/green TDD per task; test-design skill
  standards (each test names the bug it catches).

## §9 Phase gates & sequence

wrapper + move (identity-gated) → harness generalization (regression-gated)
→ G_pre anchor recomputation → OI map generation (dev smoke first) → OI
demonstration run → PHASE-CLOSE OWNER REVIEW (single gate: OI evidence pack
+ G_pre anchor + migration identity report + the §7 contract; no c2
anywhere) → PROGRESS close + push. Negative/flat OI outcomes are findings
(§5 interpretation note).

## §10 Out of scope (state, don't build)

Phase-10 solver work (any lat-varying method parameter, re-solves); shipping
calibrated OI (separate election, default no); GMRF calibration (below the
BASELINE floor, µ = 0.835); seasonal axis (Phase-8 fork (c) stands);
Q(x)/R(x) or any re-solve recalibration; any mean-map change; per-mission R;
c2 access of any kind.

## §11 Fork rulings record (owner, 2026-07-12, verbatim-intent)

### §11.1 Regions (fork 1) — per-product gate frame; frozen mask compares
1. FIT + GATE frame = PER-PRODUCT: the jet-core mask derives from EACH
   product's own signed(-config-derived) means by the pre-registered rule
   (75th-percentile temporal std → largest 4-connected component, no manual
   edits). ORDERING PINNED (the no-selection-channel argument): signed means
   → mask derived + committed → fit → bars. Calibration never touches means,
   so the mask is fixed before any s(x) exists. Lane-A fit partition + gated
   evaluation regions (quadrants ± mask carve-out) live in this frame.
   Per-product mask artifacts committed with provenance (source-map hash,
   rule constants) — the Phase-8 pattern verbatim.
2. COMPARISON frame = FROZEN, REPORT-ONLY: every product's evidence pack also
   reports coverage on the Phase-8 MIOST mask as a shared cross-product row.
   NAMING pinned: `jet_core` = the product's own gated region;
   `jet_core_ref_p8` = the frozen shared row. Never a bar.
3. DRIFT VISIBILITY: report the Jaccard overlap of the product's mask vs the
   Phase-8 reference (and, for successive products of the same method, vs
   the predecessor's mask). A surprising mask is a recorded finding the
   owner sees at the gate — visibility, not discretionary override.
4. PHASE-10 RIDER: folded into §7(d).

### §11.2 Flattening instrument (fork 2)
Folded into §7(c) verbatim.

## §12 Spec self-review record

Checked: no placeholders/TBD; §2 table consistent with §8 row-by-row tests;
§4 seed scoping consistent with the §4 harness regression; §6 tripwire
wording (fold 1) supersedes any historical-constant-only phrasing — the
44,844 assertion survives as the "where a recorded count exists" clause;
G_pre named home consistent between §4 and §7(c)3; scope §10 consistent with
§0 (B fully out); single-implementation-plan sized (wrapper+move, harness,
OI demo ≈ Phase-8 task granularity). Verified against source during
brainstorm: one Gaussian class serves OI/GMRF/FEM (methods/oi.py:92,
gmrf.py:110, fem.py:173 → distributions/gaussian.py:16);
CapabilityNotAvailableError exists (core/distribution.py:16); Gaussian class
has NO persistence; signed OI artifact is mean-only.
