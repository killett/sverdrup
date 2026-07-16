# Phase 11 — Evaluator Wiring (design)

Date: 2026-07-15. Status: owner-approved design (batches 1+2 approved with pins;
all pins folded below). REPORT-ONLY PHASE: no bar changes, no rubric changes, no
promotion of any metric to gating semantics, ZERO c2 anywhere, nothing ships,
registry METHODS/SHIPPED tables untouched, mean maps of every product
bit-unchanged (this phase only READS products). Protocols untouched; provenance
guard untouched; tuner core untouched; shipped Phase-8/9/10 artifacts and
evidence keys never overwritten.

Origin: the 2026-07-15 ARCHITECTURE-AUDIT FINDING (PROGRESS, commit `10159c4`)
— the evaluator flexibility commitment was implemented faithfully in
`core/evaluation.py` + `eval/` and Phases 4b–10 built the acceptance spine
BESIDE it. This phase makes the reference-free half produce numbers. The
PROGRESS deferred item "Evaluator-registry standalone phase" migrates INTO this
document (migrate, don't duplicate).

## 0. Prerequisites (verified) + source corrections

Verified on public HEAD (`main` == `origin/main`) at design time:

- Phase 10 CLOSED with the pre-registered NEGATIVE result (`402fd0b`).
- Four post-close owner rulings recorded (`eb6fb1f`): tuned-constant election
  DECLINED; `n_lambda_resamples=200` RATIFIED; 12 h budget RATIFIED with the
  search-scoped wording + standing rule; MIOST-B DECLINED, invariant-12 thread
  closed.
- ARCHITECTURE-AUDIT FINDING recorded in PROGRESS (`10159c4`).

Source corrections folded into this design (verify-before-assert):

- `ContextKey` has FOUR members: `TRUTH`, `WITHHELD_OBS`, `ORBIT_GEOMETRY`,
  `PHYSICAL_CONSTANTS`. The fourth is declared by no evaluator and provided by
  no runner; it stays as-is (same dormant status as `TRUTH`) and the integrity
  test (§6) enumerates it.
- Stub defect confirmed at source: `GroundTrack.evaluate` never touches
  `context`; the statistic is `power[k]/total` on an `axis=1` row-FFT; both
  pipeline sites pass `{"track_spacing_nodes": 4}` which nothing reads.
- `Registry.run()` (evaluation.py) returns a flat merged `dict[str, float]` —
  it cannot carry the §7 row schema, and merged flat dicts carry a
  name-collision hazard across evaluators. Report consumption goes through the
  row builder (§7, batch-2 pin 2), never `run()`.
- `accuracy.py` already returns `{}` when neither TRUTH nor WITHHELD_OBS is
  present — the skip-row convention (§7) formalizes this existing precedent.
- Evidence store: nested-key atomic writes into the standing results JSON
  (`atomic_write_json`, single-writer, `phase10_compare` pattern);
  `phase11.retro.*` follows it.

## 1. Decision register (owner-decided 2026-07-15)

Five forks (a–e) resolved during brainstorming, plus seven batch-review pins.
All content is folded into the sections below; this register is the index.

- **(a) ORBIT_GEOMETRY**: derive from the obs files themselves (deterministic,
  pinnable artifact) — NOT mission metadata constants (the hardcoded-k class),
  NOT a hybrid (two sources of truth). Five pins: spacing convention
  (`s_lon_km` raw + `d_perp_km` derived, formula in the artifact);
  repeat-vs-drifting classified FROM the data; headings fit in the φ0-scaled
  plane; context assembly keyed by the product's assimilated-missions
  provenance; determinism + synthetic-track recovery test. → §2.
- **(b) GroundTrack statistic**: 2-D FFT, oriented band vs same-|k| annulus
  baseline, per-day mean maps, median over days. Six pins: mode-count honesty;
  radial (not separable) window; Hermitian half-plane bookkeeping; full
  per-family evidence table with summaries as summary rows; drifting-class
  estimand flagged non-comparable; NaN-free input assert. Rejections recorded:
  Radon projection; time-mean-only (drifting artifacts phase-cancel);
  temporal-std map (conflates revisit pattern with signal variance; adjacent
  to the σ-map exclusion). → §4.
- **(c) Spectral fidelity**: descriptive-first isotropic slope over a
  pre-registered ~100–300 km band rule; zero verdict semantics this phase.
  Six pins: `optional_context` Protocol extension (additive) + two-directional
  integrity test; ring-INTEGRATED E(k) convention with the exponent relation
  recorded; band edges by rule; ONE shared spectral-prep module; WLS fit
  weighted by per-ring mode counts with per-day median/IQR as the honest
  stability context; fires on any MEAN map with the shared σ-guard. Rejections
  recorded: verdict-lite steepness flag (out of phase); truncation-wavelength
  metric (named future family member). → §3, §5.
- **(d) Wiring surface**: retro one-shot script + Phase-9 harness future
  evidence packs + migration of the two `application/pipeline.py` Registry
  sites to the shared builder + canonical registry. Historical gate-runner
  JSONs are closed records — untouched. Six pins: pipeline migration is the
  ONE deliberate non-identity-gated change; σ-guard mechanism =
  builder-set `field_kind` + evaluator entry assert; dormant-wiring test;
  retro provenance (shas asserted before scoring); schema versioning;
  `Registry.applicable` stays required-based (optional context never gates).
  → §7, §8.
- **(e) Policy seam**: pairwise-criterion chain, comparison-only — NOT a
  policy owning eligibility/audit (the framework), NOT helpers-only (leaves
  the triplication standing). Six pins: intransitivity confronted (banded
  chains are semiorders; banded `sort()` refused); bands as data (criteria
  close over computed OR loaded `BandValues`); pinned audit schema
  (branch-wording string-equality is the reproduction assert); three identity
  gates with one site-migration per commit; site ownership unchanged; no
  shared eligibility abstraction (named rejection). → §9.

Batch-1 pins: (1) GT statistic per-mode normalized both sides; (2) explicit
widening rule with hard cap + `under_floor` flag; (3) realized fidelity band
≈ [100, ~220] km on this box recorded; (4) spacing from in-domain φ0 crossings
only, doubled-angle (axial) circular mean for headings. Batch-2 pins:
(1) skip-row convention (visible skips vs loud guard raises); (2) row builder,
not `run()`; (3) retro-OI scores the Phase-9 REGENERATED daily means, both
shas recorded. All folded in place below.

## 2. ORBIT_GEOMETRY provider (fork a)

New module `application/orbit_geometry.py`: derives geometry from the
assimilated missions' along-track files. Per mission:

- **Pass segmentation** reuses the existing gap-based machinery (the
  `_PASS_GAP_SEC`-style fold/harness segmentation; no new implementation).
- **Headings** fit per pass in the locally-scaled plane x = lon·cos φ0,
  y = lat, km units; φ0 = domain-center latitude, recorded in the artifact.
  Ascending/descending families split on dlat/dt sign. Family heading =
  **doubled-angle (axial) circular mean** of per-pass headings (α ≡ α+180°
  convention) — stated in the module.
- **Spacing** from passes **crossing φ0 in-domain only** (headings use all
  passes; `n_crossings` recorded per family): raw `s_lon_km` = adjacent
  same-family crossing separation at φ0, AND derived
  `d_perp_km = s_lon·|cos α|` per family, with the formula recorded in the
  artifact. Evaluators consume `d_perp` — spectral power sits at the
  track-NORMAL wavevector, wavelength `d_perp`.
- **Orbit class from the data**: crossing-longitude multimodality at φ0
  classifies `orbit_class ∈ {repeat, drifting}`. Repeat → sharp `d_perp`;
  drifting → spacing-distribution summary (quantiles), flagged as such —
  never a fake single spacing. Headings recorded for all missions regardless
  of class. §4 consumes the class (sharp-line probe vs orientation-band
  probe).

Artifact: JSON, keyed by obs-file shas + derivation version + box + φ0;
provenance block inside (file shas, mission list, `n_passes` and
`n_crossings` per family); regeneration deterministic (same inputs → same
bytes → same sha). Context assembly (§7) selects per-mission entries by the
**product's** assimilated-missions provenance (the Phase-7 hardening's list) —
the bag describes the data this product used.

## 3. Shared spectral-prep module (forks b/c, one implementation)

New `eval/map_spectrum.py` — name deliberately distant from
`eval/spectral.py`, the shared λx algorithm (Phase-5 invariant 10), which this
phase does NOT touch. Pure numpy. Owns, once:

- φ0-scaled km-plane construction from grid + φ0 (the same frame as §2 —
  pinned once so §2 headings and §4 wavevectors share units);
- detrend (mean + best-fit plane removal) BEFORE windowing;
- **radial** 2-D Hann/Tukey window on the inscribed disk, pre-registered —
  separable windows rejected: the anisotropic leakage cross inflates
  near-axis baseline directions and biases track ratios LOW
  (artifact-hiding);
- 2-D FFT power with half-plane Hermitian bookkeeping (α ≡ α+180°; bands,
  baselines, and wedge exclusions computed once on the same convention; no
  double-counting);
- oriented wedge masks (angle ± Δθ at radius ± Δk) and same-|k| annulus masks
  with wedge exclusions — ONE exclusion implementation, two consumers
  (§4 baseline, §5 rings);
- azimuthally-**INTEGRATED** ring spectrum E(k) (ring-sum, not ring-mean),
  with the exponent relation recorded in the docstring: density ∝ |k|^(−q)
  ⇒ E(k) ∝ k^(−q+1) and the along-track 1-D spectrum ∝ k^(−q+1) — the
  off-by-one trap named once, here;
- per-mask mode counts (`n_modes`) — every consumer reports them.

## 4. GroundTrack rebuild (fork b)

`eval/groundtrack.py` rewritten. `required_context = {ORBIT_GEOMETRY}` and it
CONSUMES it: probe wavevectors derived per mission family from `d_perp` +
heading. The constructor takes NO wavenumber — `track_wavenumber` dies with
the stub; both pipeline call sites migrate (§7).

Statistic, per DAILY mean map, per family:

- repeat class: power in the oriented band α ± Δθ at radius 2π/d_perp ± Δk
  (sharp-line probe);
- drifting class: wedge-over-radial-range integrated statistic spanning the
  spacing-distribution quantiles — each vs its own baseline; the schema marks
  the two kinds NON-COMPARABLE in magnitude;
- LOCAL baseline: the same radial annulus [|k| ± Δk], EXCLUDING ± Δθ wedges of
  EVERY mission family (asc + desc, all missions) — same-|k| comparison
  defeats the red ocean spectrum; excluding all track wedges keeps one
  mission's artifact out of another's baseline;
- statistic **normalized per mode, both sides** (batch-1 pin 1):
  `log10((band_power / n_modes_band) / (baseline_power / n_modes_baseline))`.
  Per-mode ≡ per-solid-angle at the shared radius (uniform k-plane mode
  density; same-|k| by construction). Interpretation: expectation 0 on an
  isotropic field; positive = oriented excess at the track wavevector.

Aggregation: MEDIAN over days per family. Rationale recorded: drifting
missions' track artifacts phase-cancel in the time-mean map — per-day scoring
sees both orbit classes.

Metric names (flat floats per the Evaluator Protocol):
`track_excess_log10_{mission}_{asc|desc}`, `…_n_modes_band`,
`…_n_modes_baseline`; summary rows `track_excess_log10_max_repeat` and
`track_excess_log10_max_drifting` — maxima over REPORTED values (Stage-C
max-statistic discipline), per class; non-comparable kinds never share a max.

Mode-count honesty (batch-1 pins 1–2, thin-annulus arithmetic recorded): the
φ0-plane domain is ≈ 875×1110 km, so Jason-class probes sit 3–5 bins from the
origin. Report `n_modes_band` + `n_modes_baseline` per family at the pinned
Δk. **Widening rule**: if `n_modes_baseline` < floor (8 modes after wedge
exclusions), widen symmetrically **+1 bin per side**, re-check, HARD CAP 3
widenings; beyond the cap, report the row with the `under_floor` flag — never
silently widen into a different statistic. Final Δθ/Δk land in the row params;
initial Δθ/Δk constants are pinned in the implementation plan. Never quote a
ratio without its mode counts.

Input guards (loud refusal, never silent skip): asserts
`field_kind == "mean"` (σ-guard, §7) and NaN-free over the box (open ocean
expected) at evaluator entry.

Class docstring carries, verbatim: **NECESSARY-NOT-SUFFICIENT — a strong track
signature proves a problem; a clean map does not prove correctness.** Beside
it, the Phase-8 theorem note: posterior covariance = (GᵀR⁻¹G + Q⁻¹)⁻¹ is
independent of obs VALUES, so σ/variance maps LEGITIMATELY carry
sampling-geometry pattern — scoring them here would "detect" an expected
feature; hence the mean-only guard (constraint 4).

## 5. Spectral-fidelity evaluator (fork c) + the one Protocol extension

New `eval/fidelity.py`, class `SpectralFidelity`. DESCRIPTIVE-ONLY this
phase: no verdict semantics, no flag, no margin.

**Protocol extension (additive; the spine is otherwise not redesigned):**
`Evaluator` gains `optional_context: frozenset[ContextKey]` (default ∅).
`Registry.applicable` remains **required-based only** — `optional_context`
NEVER gates applicability; stated in the code so the extension cannot mutate
semantics by accident (fork-d pin 6). `accuracy.py` migrates to declare
`optional_context = {TRUTH, WITHHELD_OBS}` (its runtime either-check is
unchanged).

`SpectralFidelity`: `required_context = ∅`,
`optional_context = {WITHHELD_OBS}`. Fires on any mean map.

Computation: shared prep (§3) per-day 2-D spectra → average power over days →
wedge-excluded ring spectrum E(k) (fidelity rings EXCLUDE all track wedges —
an artifact must not bias the slope that is supposed to be independent
evidence) → **WLS** fit of log10 E vs log10 k, weights = per-ring `n_modes`
(log-ring variance ~ 1/n), over the pre-registered band:

- lower edge = max(100 km, 3× grid spacing);
- upper edge = min(300 km, wavelength at the pinned minimum bin index ≥ 4
  given the radial window's recorded mainlobe width — the window shrinks
  effective aperture below the 875 km box);
- **realized band on this box** (batch-1 pin 3): ~875 km inscribed aperture ⇒
  bin-4 ≈ 219 km ⇒ band ≈ [100, ~220] km; the 300 km cap never binds here —
  the mainlobe-clearance rule working as designed;
- recorded: the band deliberately spans the product's λx neighborhood
  (140.9–205.3 km measured in Phase 10) — that is the sensitivity, not a bug.

Metrics (flat floats): `spec_slope`, `spec_slope_wls_se`,
`spec_slope_day_median`, `spec_slope_day_iqr` (per-day fits; the honest
stability context — only ~365/L_t effective independent days, so the IQR is
the uncertainty context, not the WLS SE alone), `spec_n_modes_min`. When
WITHHELD_OBS is present: `spec_slope_obs_1d` over the same wavelength band via
the existing pass-segmentation machinery — FLAGGED different-estimand (1-D
along-track vs ring-integrated 2-D; same exponent under isotropy by §3's
relation, still flagged) with the instrument-noise-floor caveat recorded (obs
slope biased shallow near 100 km). No differencing, no verdict.

Same σ-guard and NaN assert as GroundTrack — one guard, two consumers, one
builder (§7).

## 6. Declared⇒consumed integrity test (constraint 3)

`tests/test_evaluator_context_integrity.py`. Mechanism: a recording
`EvalContext` whose `items` mapping is a spy — `__getitem__`/`.get` record
READS, `__contains__` records REFERENCES. For every evaluator in
`default_registry()` (§7), run `evaluate` on a synthetic minimal fixture with
a full context and assert, TWO-directional (fork-c pin 1):

1. every `required_context` key is **READ** (getitem — membership checks do
   NOT count for required keys);
2. every referenced key (read or membership) ⊆ required ∪ optional.

The GroundTrack stub is the motivating counterexample (fails rule 1); the
accuracy either-check is legal only via its migrated `optional_context`
(rule 2). The test enumerates all four `ContextKey`s so a future dormant key
cannot hide. Skip-row note (batch-2 pin 1): required-key reads are still
enforced on skipping evaluators' fixtures wherever `required ≠ ∅` — a skip on
absent optionals never excuses an unread required key.

## 7. Wiring: builder, canonical registry, row builder, guards (fork d)

New `application/eval_context.py`:

- `build_eval_context(...)` — assembles `EvalContext` from what a runner
  already has: mean map(s) + grid + φ0 → result payload with
  `field_kind ∈ {mean, sigma, other}` set BY THE BUILDER (the σ-guard's
  single source; evaluators assert `field_kind == "mean"` at entry, §4/§5);
  the product's assimilated-missions provenance → per-mission ORBIT_GEOMETRY
  entries from the §2 artifact; withheld obs (validation side) →
  WITHHELD_OBS. TRUTH / PHYSICAL_CONSTANTS: never fabricated, included only
  if a caller genuinely holds them (none does today).
- `default_registry()` — the ONE canonical evaluator list (Accuracy,
  Calibration, GroundTrack, SpectralFidelity, + the existing skill/resolution
  evaluators exactly as currently registered where applicable — enumerated at
  implementation from the `eval/` exports, no new hand-picking). Per-runner
  evaluator lists die.
- `build_report_rows(registry, result, context) -> list[Row]` (batch-2
  pin 2) — THE consumption path for all three surfaces: per-evaluator
  iteration over `registry.applicable(...)`, producing full rows including
  skip rows. `Registry.run()` returns a flat merged `dict[str, float]` that
  cannot carry the row schema and has a cross-evaluator name-collision hazard
  (noted here); its disposition is decided at implementation with its
  consumers enumerated; NEW report code never uses it.

**Skip-row convention** (batch-2 pin 1; formalizes accuracy.py's existing
`return {}` precedent, verified at source): evaluators MAY return `{}` when
needed optionals are absent; the row layer renders that as a VISIBLE skip row
(`flags: no_usable_context`, `context_keys_used: []`). Distinction pinned:
absent optionals → recorded skip; INVALID input (`field_kind ≠ "mean"`, NaN)
→ the guard RAISES and crashes the run.

Row schema (per evaluator run): `{schema_version (block-level),
evaluator, evaluator_version (row-level), metrics{name: value},
context_keys_available, context_keys_used (consumed optionals distinguished),
params (Δθ/Δk initial + final-after-widening, band edges, φ0), n_modes,
flags (estimand kind, under_floor, different-estimand obs row, skip),
provenance {map_sha, geometry_artifact_sha}}`. Params come from the pinned
constants + geometry artifact (builder/runner side); evaluator metrics stay
flat floats.

Three surfaces this phase:

1. **`scripts/phase11_retro_run.py`** (§8) — the one-shot deliverable.
2. **Phase-9 harness**: FUTURE evidence packs gain a
   `report_only_instruments` block built via builder + row builder.
   Historical JSONs are closed records — untouched (the
   no-edits-during-gate lesson generalizes). **Dormant-wiring test**
   (fork-d pin 3): a dev-scope (12-day fixture) harness test asserts block
   presence + full schema — the wiring never ships in the
   built-but-never-run state this phase exists to eliminate.
3. **`application/pipeline.py` (both Registry sites)**: migrate to builder +
   `default_registry()` + row builder. This is the phase's ONE deliberate
   non-identity-gated migration (fork-d pin 1), recorded: `track_power` dies
   with the stub (new statistic, new names, no compat shim);
   spectral-fidelity rows appear; pipeline-output consumers enumerated at
   implementation and their pins DELIBERATELY updated (reviewed-shape-change
   principle cited). Pipeline report values are diagnostics, not gates.

## 8. Retroactive one-shot (constraint 7)

`scripts/phase11_retro_run.py`, run once, numbers recorded:

- **Inputs**: (a) the shipped Phase-8 MIOST stage-B mean maps at the accepted
  config; (b) the **Phase-9 REGENERATED daily OI means** (batch-2 pin 3) —
  tied to the signed artifact by the Phase-9 matched-day comparison;
  provenance records BOTH shas: regenerated (scored) + signed
  `OSE_ssh_mapping_OURS_OI.nc` (anchor). READS only; products bit-unchanged.
- **Provenance discipline** (fork-d pin 4): the script asserts map shas
  against the recorded Phase-8/9 evidence values BEFORE scoring;
  deterministic regeneration only if artifacts are absent, shas still
  asserted. Context assembled via the §7 builder from the maps'
  assimilated-missions provenance attrs — MIOST and OI get their own geometry
  bags.
- **Writes**: `phase11.retro.{miost|oi}.{groundtrack|spectral_fidelity}.*`
  via the standing nested-key atomic-write pattern (`atomic_write_json`,
  single writer); full §7 row schema per entry, PLUS the full per-ring
  `n_modes` table (the retro script records it via shared prep directly;
  evaluator metrics stay flat floats).
- **Headline numbers into PROGRESS** (per-class track-excess maxima +
  fidelity slopes, both products); the commit message carries them.
- These numbers inform the product conversation; they GATE NOTHING. No
  promotion this phase.

## 9. Policy seam (fork e, constraint 8)

New `application/policy.py`:

- `Verdict = {A_WINS, B_WINS, TIE}`; `Criterion` = a named
  `compare(a, b) -> Verdict`.
- `LexicographicPolicy(criteria)`, two entry points:
  - `sort(candidates)` — `cmp_to_key` over the chain. ASSERTS an unbanded
    (total-order) chain: banded criteria form a SEMIORDER (a~b, b~c, a beats
    c is realizable), so banded `sort()` is refused; a property test
    documents the intransitivity (fork-e pin 1).
  - `winner(candidates)` — the banded entry point: sequential pairwise
    reduction in the PINNED per-site candidate order (legacy order; the
    leaf-identical gate arbitrates), returning a winner OR terminal
    TIE-with-survivors (lane_compare's negative PRIMARY verdict is exactly
    that), ALWAYS with a per-stage audit trail.
- **Audit schema pinned** (fork-e pin 3): per stage
  `{criterion, values/Δ, band?, verdict}` — sufficient to emit lane_compare's
  recorded "rule branch taken" wording VERBATIM; string-equality is the
  reproduction assert. The sort path needs no audit; `winner()` always
  returns one.
- **Bands as data** (fork-e pin 2): criteria close over `BandValues` computed
  OR LOADED by the call site; the seam never computes bands and has NO
  conditional semantics — λ-degradation = the call site drops the λ criterion
  before the chain runs.

Site ownership unchanged (fork-e pin 5): bar-filter + `NoAdmissibleTrial`
(objective); lane-0 eligibility + the negative path (folds); sealed-protocol
machinery + read-time `compute_bands` + λ-degradation (lane_compare). The
seam owns ONLY the ordinal chain. NO shared eligibility abstraction — named
rejection (three different KINDS of eligibility; that way lies the
framework).

**Three identity gates — HARD; one site-migration per commit, gate green in
the same commit (fork-e pin 4):**

1. The Phase-8/9 harness-on-MIOST leaf-identical regression passes
   UNCHANGED — `folds.select` byte-equivalent through the seam.
2. The Phase-10 verdict is reproduced from its PERSISTED records through the
   seam — `BandValues` reconstructed from the phase-10 evidence JSON (never
   recomputed), branch + wording string-equal ("improvements within band").
3. `ConstrainedObjective`'s sort order pinned by existing tests + a new
   property test: single-criterion `cmp`-chain sort byte-identical to
   `sorted(key=…)` on generated records (stable-sort tie order included).

Behavioral pins inviolable; structural asserts may track the reviewed shape
change (the Phase-9 close principle, cited).

## 10. Evidence design summary

| Item | Where |
|---|---|
| Retro numbers | `phase11.retro.{miost\|oi}.{groundtrack\|spectral_fidelity}.*`; §7 row schema + `schema_version`/`evaluator_version`; provenance = scored-map shas + signed-artifact anchor sha (OI) + geometry-artifact sha |
| Declared⇒consumed test | `tests/test_evaluator_context_integrity.py`; spy context; two-directional; all four ContextKeys enumerated |
| Policy gate (i) | leaf-identical harness-on-MIOST regression, unchanged |
| Policy gate (ii) | Phase-10 verdict reproduction from persisted records; branch + wording string-equal |
| Policy gate (iii) | objective sort pins + `cmp`-vs-key byte-identity property test |
| Dormant-wiring test | dev-scope harness test asserts `report_only_instruments` presence + full schema |
| Suite | green throughout; `pixi run pre-commit run --all-files` before every commit |

## 11. Test plan (TDD, test-design discipline)

Red/green per behavior. Key tests beyond §10:

- **orbit_geometry**: synthetic-track recovery (known headings via
  doubled-angle axial mean, spacings, repeat structure; a synthetic drifting
  mission correctly classified; the in-domain-crossing spacing rule;
  `n_crossings` recorded); artifact determinism (same inputs → same bytes →
  same sha); cache-key sensitivity (obs sha change → new artifact).
- **map_spectrum**: Parseval sanity; ring-integrated E(k) exponent relation
  on a synthetic |k|^(−q) field; wedge/annulus mask mode counts exact on a
  small grid; Hermitian half-plane no-double-count; the radial window's
  recorded mainlobe width matches measurement.
- **GroundTrack**: planted oriented sinusoid at (α, d_perp) → large positive
  `track_excess_log10`; isotropic red-noise field → ≈ 0 (the per-mode
  normalization interpretation); widening rule fires +1 bin per side, caps at
  3, `under_floor` flag beyond; σ-field input → loud refusal; NaN input →
  refusal; drifting-class statistic flagged non-comparable.
- **SpectralFidelity**: synthetic |k|^(−q) field → E(k) slope ≈ −q+1 within
  tolerance; WLS weighting matches `n_modes`; band edges follow the rule on
  this box (≈ [100, ~220] km); the obs row appears iff WITHHELD_OBS present,
  flagged; day-median/IQR computed over per-day fits.
- **Row builder / skip rows** (batch-2 additions): skip-row rendering test
  (absent optionals → visible skip row with `no_usable_context`,
  `context_keys_used: []`); row-builder tests (schema completeness,
  per-evaluator iteration, consumed-optionals distinction);
  accuracy-neither-branch test pinning the `{}` precedent.
- **Policy**: semiorder intransitivity property test (banded `sort()`
  refused); audit-trail schema; TIE-with-survivors path.
- Existing suites (`test_eval_spectral`, harness, folds, lane_compare,
  objective) pass unchanged EXCEPT the enumerated pipeline-consumer pins
  (§7, deliberate).

## 12. Out of scope (stated, not built) + standing hard constraints

- Promoting any new metric to a bar — the promotion path (report-only →
  pre-registered bar) exists and is NOT exercised here.
- OSSE/TRUTH harness work — dormant until the global ambition; the TRUTH
  ContextKey stays as-is; PHYSICAL_CONSTANTS likewise (recorded in §0).
- Geostrophic-balance / conservation evaluators — named future family
  members. Truncation-wavelength metric — named future family member once
  slope numbers exist (fork-c record).
- Any method or product change; c2 access of any kind; registry
  METHODS/SHIPPED tables untouched; shipped Phase-8/9/10 artifacts and
  evidence keys never overwritten; `eval/spectral.py` (λx) undisturbed;
  protocols, provenance guard, tuner core untouched.
