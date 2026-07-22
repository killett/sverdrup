# Phase 14 — Scaling program design: global domain, multi-decade record, era-aware calibration

**Date:** 2026-07-21 (live-args date; owner-accepted at fork a)
**Status:** owner-approved in-session (seven forks a–g ruled with pins; two design
batches approved with pins). Committed for owner FILE review before writing-plans.
**Kind:** PROGRAM design — architecture + stage gates + interface contracts + the
fully-designed first executable stages (0 and 1). Stages 2, 2G, 3 get their own
specs consuming this document's contracts. The monolith is refused.

---

## 0. Program identity and named destination

**Named destination, shaping every stage:** per-gridpoint SEA-LEVEL-TREND ERROR
BARS from calibrated ensembles propagated through the 25+ year altimetry record —
honest regional sea-level-rise uncertainties, the climate deliverable the JPL SSHA
product exists for.

**Program-level honest sentence (verbatim, standing):** a trend product on today's
machinery would ship overconfident bars — the current ensemble carries zero
inter-annual error correlation while trend uncertainty is dominated by long-memory
systematic errors; this program exists to refuse that, and Stage 3 does not run
until the C2G→3 contract's requirements (a)–(c) exist.

Program shape: five stages (0, 1, 2, 2G, 3), owner gates between, interface
contracts at each boundary — the Phase-9→10 contract pattern at program scale.
One new risk per stage is the architecture's own rule; the stage map obeys it.

---

## 1. Prerequisites and consumed-phase statuses (recorded, never assumed)

- **Phase 11 CLOSED** 2026-07-16, pushed (hard prerequisite satisfied). Evaluator
  wiring: reference-free family + registry surfaces + geometry provider v3 +
  Policy seam. GroundTrack 0.410 five-mission standing baseline.
- **Phase 12 CLOSED** 2026-07-18, flip `b4878a0`. Six-mission production
  convention (`shipped_miost6`); five-mission calibration-lineage reference
  retained. Consumed by: the Gate-1 refresh election's scope (§6) and Stage-2G
  shipped-config semantics.
- **Phase 13 CLOSED** 2026-07-21, flip `8b6f5d4`. Structured observation error:
  per-mission R (δ contrasts), state augmentation [G B] with Q_aug, extended
  duality oracle (mean AND variance), err CRN axis, m=100 aug1 ensemble. **The
  augmentation machinery the trend stage REQUIRES exists and is signed.** The
  six-mission refresh election was deferred with a bundling rule that fires "at
  the global-domain transition" — THIS program triggers it; the exact firing
  point is named: the Gate-1 shipped-config election (§6, task 1-8).

---

## 2. Governing inputs — verification record

Every claim below was verified against source in-session (2026-07-22).

**Papers brief** (`docs/papers/2026-07-02-miost-method-brief.md`, owner-accepted
2026-07-02):

- Global tiling is documented ONLY in U2022 §3.2.3 p.7: 15°×15° tiles, 2°
  overlap, "linearly interpolating the solution in the overlapping zones, with a
  weight ratio proportional to the boundary relative distances." ~10⁹ mesoscale
  elements global/25-yr; 2 TB RAM / 200 threads. **Per-tile problem sizes,
  wall-clock, per-tile Q/R adjustments: NOT SPECIFIED (brief gaps register §8).**
- U2021 regional = single window, no tiling — the box-scale record is
  paper-faithful as-is.
- B2023 equatorial components (brief §4.3): TIW + Poincaré, 10°S–10°N SSH-only,
  propagating carrier cos(ωt − kx), dispersion-prescribed frequencies; impact
  **~3% average, >10–20% locally** (supersedes the kickoff's ">10%"; brief is
  more precise). Q values NOT SPECIFIED.
- **Kickoff correction (recorded at fork b):** no separate barotropic/HF
  component exists in the altimetry-only lineage — input SLA arrives DAC/
  tide-corrected (B2023 Eq. 1); the component menu was always
  {mesoscale, equatorial pair}.
- Input lineages: U2022 global run = CMEMS L3 all missions 1993-01→2017-08 with
  3:1 super-obs; B2023 = CMEMS DT2021 L3 (`SEALEVEL_GLO_PHY_L3_MY_008_062`),
  unfiltered SLA. B2023 "MIOST allsat-1" (Table 3) = altimetry-only,
  geostrophy-only — the Stage-1 configuration's documented analog.

**Deferred threads** (each verified in PROGRESS.md): seasonal axis (August 0.629
survives the phase-13 R change; "n>1-years as its substrate"); Phase-10 negative,
scoped verbatim "no lat-varying gain beyond the measured band UNDER THIS SEARCH …
never a physics disproof", with ruling 1 "the OI product question re-opens at the
global domain" and ruling 4 "MIOST-B … Revisit only at the global domain";
SkyPilot ladder recorded with reopen criterion = RAM/blocking; TRUTH/OSSE context
dormant since 4b; tide gauges named in the founding taxonomy
(`docs/phase1_scope_spec.md:183`, reference-based family: "vs independent in-situ
(tide gauges, drifters)") — never built until Stage 0a.

**Phase-8 covariate theorem (restated because it is load-bearing for fork e):**
the ensemble-σ covariate was KILLED because posterior covariance
= (GᵀR⁻¹G + Q⁻¹)⁻¹ is independent of obs VALUES (phase-8 spec, covariate-lane
section). A SAMPLING-DENSITY covariate is derived from obs GEOMETRY, not values —
LEGAL, deterministic, pinnable. This distinction authorizes the fork-e design.

**Machinery inventory (scales as-is vs generalizes):** halo_obs framing +
window/blend machinery (spatial-tiling analog); seam-dispersion instruments +
rubric (Phase-7 Task 18 — temporal seam discipline, spatialized in Stage 1);
Phase-9 product-agnostic calibration harness (covariate lanes supported since
Phase 8); Phase-11 geometry provider (per-era artifacts) + reference-free
instruments (per-tile trivially); Task-22 sizing arithmetic (+ re-grounding queue
carrying the retained-store term BY NAME); provenance guard (per-era assimilated
lists); scalar-box tuner core untouched (settled constraint 10).

---

## 3. Program architecture

### 3.1 Stage map

**STAGE 0 — foundations.** Workstreams 0a–0d (§5). No evaluation-bearing map
exists before Gate 0: the 0b-3/0b-4 probe and cross-env solves are INSTRUMENTS
(sizing, determinism), artifacts labeled PROBE, never scored against validation
or locked tiers — constraint 4 held by precision, not weakened.
**Gate 0 (owner):** sealed evaluation-set sha signed; spend table authorized;
adapter + identity gates green; locked-refusal tests green; determinism
tolerances recorded.

**STAGE 1 — spatial scaling at one year (2017, the proven constellation).**
Six-tile roster, frozen signed config, five-mission workhorse, zero touches
(§6). **Gate 1 (owner):** anchor identity (five checks); seam oracle verdicts;
six transfer readings; high-latitude kernel decision; Phase-10 revisit verdict;
six-mission refresh election.
**Risk line (expectation-setter): seams and high-latitude behavior.** The
equatorial tile is EXPECTED weaker without wave modes — priced at B2023's ~3%
average / 10–20% local.

**STAGE 2 — temporal scaling at fixed domain (multi-year on the tile roster,
not yet global assembly).** Era-aware calibration per fork e; role-split
validation per fork c; per-era δ_m assignments (§8); seasonal-axis unlock
decision (recorded decision, not automatic). Own spec, consuming C1→2.
**Gate 2 (owner):** covariate leave-one-out rotation set; sparse-epoch transfer
reading (consumed once, masked); extrapolation-fraction audit; DEV-pool gauge
era rows. **Stage 2 accepts no shipped product → locked instruments do NOT open
at Gate 2** (§3.3).
**Risk line: era transfer.** Negative path: per-era fits at reference epochs +
stated uncertainty elsewhere — measured-not-shipped discipline.

**STAGE 2G — global assembly at one year.** Named its own gated stage (batch-1
pin 1). First global map: full tile fleet, SHIPPED config per the Gate-1
election, calibration = per-tile reference-epoch (2017) fits via Stage-2
machinery (the stated justification for Stage 2 preceding 2G). Pole handling
(fork-d D4) decided HERE with the Southern-Ocean measurement + kernel decision
in hand. Fleet compute at the fork-g rungs per its own spend table. **Its
accepted product = the program's FIRST accepted product; the locked set opens
for the first time at its acceptance touch** (§3.3). Own spec, consuming C2→2G.
**Risk line: assembly at scale** — poles, fleet compute, land-mask everywhere,
seam behavior at fleet count (the 2026-07-01 feasibility-frontier lesson:
worst-seam grew with tile COUNT — measured then, watched here).

**STAGE 3 — the record + the trend product.** Full-record assembly, trend-error
machinery, per-gridpoint trend bars, validation vs VLM-corrected gauge trends +
published GMSL/regional budgets. **Spec written only after Stages 0–2G report;
this phase delivers its interface contract (C2G→3) only.**
**Risk line: temporal coherence.**

### 3.2 Interface contracts (batch-2 pin 1 chain: C0→1, C1→2, C2→2G, C2G→3)

**C0→1:** sealed evaluation-set artifact (sha quoted by every subsequent
evidence pack); dual-source loader contract + uniform provenance descriptors;
census artifact + epoch partition; tile-frame/blend substrate with
partition-of-unity proofs; per-tile validation scorer; validated tile-scale
sizing model + spend table; the two determinism tolerances (priced apart).

**C1→2:** tiling machinery + measured seam behavior (oracle + rubric verdicts);
high-latitude kernel decision + its arithmetic; per-tile frozen-config transfer
readings (raw-σ + labeled scalar-s* reference rows; j3-side coverage/χ² — the
measurement that motivates Stage-2 calibration); the equatorial lane-0 baseline
persisted under frozen fold/eval frame; land-mask path exercised; the Gate-1
shipped-config election outcome with its scope.

**C2→2G:** era-keyed calibration artifacts (covariate model + per-era reference
fits + the two-level validation record); final epoch table; per-era R/δ
assignments; **the first global product's calibration named: per-tile
reference-epoch (2017) fits produced by Stage-2 machinery** — Stage 2G ships
calibrated σ, not raw posterior σ (§7).

**C2G→3 (the trend contract; settled constraint 8 carried VERBATIM):**
the CURRENT ensemble carries ZERO inter-annual error correlation (60-day
windows; members independent beyond blend overlap) — and trend uncertainty is
DOMINATED by long-memory systematic errors (inter-mission biases,
orbit/reference-frame and instrument drifts; the published GMSL error budgets
are systematic-term-dominated). A trend product on today's machinery would ship
overconfident bars — the exact thing this project exists to refuse. Stage 3
therefore REQUIRES: **(a)** inter-mission bias/drift error components as
structured terms with priors from PUBLISHED budgets — the Phase-13 augmentation
machinery at climate timescale (the recorded dependency); **(b)** ensemble
TEMPORAL COHERENCE for those components across windows/years (era-keyed CRN
draws held fixed across windows — the CRN identity machinery extended);
**(c)** trend-bar validation = coverage of tide-gauge trends (VLM-corrected
gauges, caveats recorded) + consistency with published budget totals.
Additionally carried into this contract: the accepted 2G global product +
assembly machinery; the Phase-13 MODE-LAYER REDESIGN note (cross-window-coherent
pass modes, one physical error per pass — a temporal-coherence design input for
(b), from the residual-structure ledger); the storage-vs-recompute decision
(fork-g pin 3: CRN determinism makes "store the recipe — config + seeds — and
regenerate members on demand" a priced alternative to storing full member
stacks; U2022's 2 TB-class number is the stakes); the trend-tier gauge column
(GPS-colocated, VLM-corrected — a stricter column in the same gauge registry).

### 3.3 Locked-instrument schedule (program-wide; batch-1 pin 3)

Stage 0: locked set sealed, structurally refused, never opened. Stage 1: never
opened — zero c2, tally untouched. Stage 2: never opened — Gate-2 independence
evidence = the sparse-epoch holdout reading (consumed once, ±66° masked) +
DEV-pool gauge era rows. **Stage 2G acceptance touch: FIRST open** — one scoring
pass of the accepted product over the sealed locked set for its era range;
tally entry named for the shipped config (e.g. `global-2017-<config>: 1`).
Stage 3: trend-tier reads under its own contract. One schedule, no drift.

---

## 4. Fork rulings record (all pins verbatim-intent; the Phase-11 §12 pattern)

### Fork A — input data: dual-source loader abstraction (option iii)

Public repo demonstrates on CMEMS for ALL program evidence; JPL SSHA is a
conformance-tested adapter; one loader interface, era-keyed provenance. Pins:

1. **Three-layer testability:** (a) a SYNTHETIC third adapter (constructed
   fixture data) exercises the loader contract in public CI — interface drift
   fails publicly; (b) the JPL adapter's CODE is public, its conformance run
   artifact-gated behind the standing skip-guard pattern, runnable where the
   data lives; (c) golden-tile cross-check RESULTS are recorded in public
   evidence even when inputs are private — the PDF-extraction precedent
   (private inputs, public verified claims) applies verbatim.
2. **Golden-tile epistemics pre-registered:** purpose = measuring the PRODUCT's
   input-lineage sensitivity — same tile, same period, same config through both
   adapters → map deltas + track-metric deltas, recorded. The sources are
   different processing lineages and WILL diverge; divergence TABLES an owner
   decision (never auto-blocks, never auto-reconciles — no scope creep into
   processing arbitration). Placement resolved (batch 2): machinery Stage 0c;
   execution artifact-gated, runs when JPL data is reachable, any stage.
3. **Descriptor schema uniform + content-addressed — no "OR":**
   (source_id, dataset_version, content_manifest) with content_manifest =
   per-file shas ALWAYS; if the JPL pipeline emits no content hash, the adapter
   computes them at ingest. A processing tag is a label; the provenance guard's
   value is content addressing — one convention, no branches.
4. **Super-obs (3:1)** = a Stage-1 MEASURED decision; it is a LOADER-LAYER,
   source-agnostic transform (applies identically through both adapters if
   adopted), parameterized and recorded in provenance — adopting it later must
   not fork the adapters.
5. **Version-migration protocol:** the CMEMS dataset version is part of the pin
   (DT2021 is the papers' vintage); any future migration (DT2024, …) is a
   RECORDED event that runs the same golden-tile comparison machinery
   cross-version — the pin-2 protocol pays twice.

### Fork B — Stage-1 component scope: mesoscale-only + pre-registered wave increment (option iii)

Stage 1 = B2023 "MIOST allsat-1" lineage. The equatorial-wave increment is its
own OWNER-ELECTABLE phase after Stage 1 reports (a capability, not a scaling
step); election inputs = the baseline pack + the priced expectation. Pins:

1. **The baseline is the future lane-0, engineered now:** the equatorial tile's
   Stage-1 run persists everything the eventual increment comparison needs —
   maps, evidence pack, fold/eval frame — so the wave increment (when elected)
   is judged by the standing pre/post pattern: FROZEN pre-increment frame, same
   tile, lane-0 = this mesoscale-only baseline. Business case = (our measured
   band baseline) + (B2023's published increment, ~3% average / 10–20% local in
   10°S–10°N, cited as the priced expectation); the increment's success metric
   is recovering an improvement of that order against OUR OWN baseline, never a
   cross-paper number-match.
2. **Config-policy control:** the equatorial baseline is recorded UNDER
   Stage 1's config policy (frozen signed config, §6), and the future increment
   comparison HOLDS THAT POLICY FIXED — a wave-component gain must never be
   confounded with a config change (the tuned-constant control lesson,
   Phase 10).
3. **Gap-register inheritance, pre-registered for the increment:** the
   equatorial Q values are NOT SPECIFIED in the papers — when the increment is
   elected, they enter as TUNABLE parameters optimized against validation per
   the Phase-7 gap discipline, never invented constants. The increment's future
   spec inherits this sentence.
4. **Forward note to fork d (executed there):** the equatorial tile's placement
   serves double duty — primarily in-band with meridional extent crossing the
   10°N component edge (the taper boundary becomes measurable when the
   increment lands).

### Fork C — per-era validation: role-split protocol (option iii)

Epoch partition derived deterministically from the census artifact. Reference
epochs (constellation ≥4 net of locked exclusions) serve both roles (fit
substrate + validation metric), 2017/five-mission first by construction. Sparse
epochs (2–3 satellites): NO per-era fit — calibration transferred via the
density covariate; holdout is validation-only, one measurement run that never
ships. Holdout selection criteria (recorded, in order): never the
climate-reference line (TOPEX→J1→J2→J3) where an alternative exists; prefer a
mission with an instrument-class sibling still assimilated (the δ_j3 := δ_j2n
precedent); prefer the holdout whose removal least distorts the assimilated
geometry-class mix; one holdout per epoch, stable across the epoch. Gauges =
claim-bearing independent family in ALL epochs; crossovers = report-only where
the mission is assimilated.

**Sparse-era honest sentence (verbatim, in-spec per ruling):** "calibration is
transferred, not fit, here; its validation is thin and stated; gauges carry the
independence burden" — true of any method on 1993 data, and we say it out loud.

Pins:

1. **Covariate fit/validate separation (hard rule, binding on fork e):** the
   density-covariate model is fit on REFERENCE epochs only; sparse-epoch holdout
   readings are consumed ONCE as the pre-registered transfer-validation
   measurement — never as fit data, never in model selection. The moment a
   sparse reading informs the covariate, it stops being validation.
2. **The epoch table gains a LOCKED column:** fork c designs the VALIDATION
   tier; the LOCKED tier is a Stage-0/fork-f deliverable, and the pre-registered
   table is the single registry of both: epoch → missions → holdout(validation)
   → locked-instrument → fit-vs-transferred. c2's never-assimilated status
   extends as the locked track for every epoch it flies (2010→); pre-2010
   locked instruments decided at fork f.
3. **Latitude-band validity mask:** the ERS-line holdout reading is
   claim-bearing ONLY within the T/P latitude band (±66°); poleward, the fit
   substrate has ZERO observations and the map is pure prior — polar validation
   in sparse eras = gauges only. The handicap table carries the mask explicitly;
   no sparse-era number is ever quoted without its band.
4. **Sibling-less holdouts:** where no instrument-class sibling remains
   assimilated (1993 ERS), the holdout's own structured-error parameters come
   from the PUBLISHED budget priors (the Phase-13 box sources), recorded as
   such — the reading's caveat names that the measurement convolves map error
   with a prior-set holdout-error model.
5. **Epoch-boundary handling** resolved at fork d (D6).

### Fork D — tile geometry (package D1–D6)

- **D1:** 15°×15° tiles + 2° overlap = the pre-registered paper-faithful
  default, ratified by PRODUCTION-TIER sizing probes; 10°×10° = the recorded
  fallback on production-tier arithmetic only. Gap-registered: papers never
  document per-tile obs halo — our machinery distinguishes core / blend-overlap
  / halo, ONE shared frame helper emits all three (the halo_obs lesson).
- **D2:** blend = the paper's linear boundary-relative-distance rule on edges;
  corners = OUR separable per-axis product completion (reduces exactly to the
  paper rule on edges; math checked, partition of unity holds), gap-registered
  as our completion.
- **D3 roster (six entries, each with a named job):** (1) Gulf Stream ANCHOR —
  the signed 10°×10° box as a degenerate single tile through the generalized
  path, identity gate; (2) Gulf Stream SEAM-PAIR — seam crosses the jet inside
  the anchor footprint; **seam ORACLE: seam dispersion measured against the
  seamless signed truth — no published precedent exists for this instrument
  (recorded)**; (3) equatorial (in-band core, crossing the 10°N edge);
  (4) Southern Ocean ~55°S (high-latitude honesty instrument); (5) quiet gyre,
  subtropical SE Pacific (low-signal regime); (6) KUROSHIO (coastal/island-dense
  western-boundary jet — exercises the land-masking path Stage 1 would otherwise
  hand to assembly unexercised; second jet for the transfer read).
- **D4:** pole handling DEFERRED with a recorded boundary — Stage 1 caps at the
  Southern-Ocean tile latitude; polar-cap geometry (meridian convergence,
  ±66°/±81.5° mission limits, B2023's 80°S–90°N precedent) is Stage 2G's
  decision, informed by tile-4's measured anisotropy. Gap + option list, not
  designed now.
- **D5:** FROZEN signed config is Stage 1's default on every tile — the transfer
  measurement; zero new fits, zero touches. The Phase-10 revisit runs as the
  pre-registered lane experiment on top.
- **D6:** epoch label attaches per window by WINDOW-CENTER rule, recorded in the
  census artifact; obs carry mission tags intrinsically. Padding/split-window
  alternatives rejected (complexity, no enabled measurement).

Pins:

1. **Kuroshio = tile 6** (folded into D3 above; no deferral argued).
2. **Blend partition-of-unity asserted numerically EVERYWHERE** — interior,
   edges, corners, AND domain-edge/missing-neighbor (land-adjacent) cases where
   weights renormalize: the actual-overlap normalization lesson, spatialized.
   Unit tests in Stage 0 regardless of whether the 2×2 corner exercise rides
   the seam-pair.
3. **Two envelopes, never conflated:** the 15°/2° default is ratified by
   PRODUCTION-TIER sizing probes; the mini-PC serves DEV-SCOPE FIXTURES (reduced
   days / single tile) at whatever tile size production uses. The 10° fallback
   triggers on production-tier arithmetic only — dev convenience never dictates
   product geometry.
4. **Halo derives from the OPERATIVE kernel scale per tile** (constant 1.0°
   today ⇒ current practice exactly; if the constraint-3 high-latitude decision
   changes scales, the halo follows automatically — no second constant to rot).
5. **D6 accepted-approximation stated:** a straddling window's map is
   mixed-constellation while its calibration key is window-center-epoch —
   immaterial at one-mission deltas over 60-day windows, RECORDED rather than
   discovered later.
6. **D5 sub-design deferral named:** the Phase-10 revisit is pre-registered here
   as EXISTING (frozen-config = lane-0, diverse tiles, real f range, zero
   touches), but its design — per-tile lanes vs one cross-tile shared field,
   its bands, its budget — is its own forked sub-design at Stage-1 plan time,
   not inherited from the box-scale apparatus unexamined.

### Fork E — era-aware calibration: hybrid route + density covariate

Route: per-era fits at 2–3 reference epochs = ground truth; density-covariate
model fit ACROSS them (reference epochs only, fork-c pin 1); two-level
validation. Covariate: kernel-weighted effective sampling density

    n_eff(x, window, era) = Σ_obs K(|x−x_obs|/L) · K(|t_c−t_obs|/L_t)

— pure geometry functional (positions + times, never values; legal per the
Phase-8 theorem distinction), computed by the geometry-provider layer, never
through the solver. Rejected alternatives recorded: geometry-determined
posterior σ (theorem-legal information-wise but routes through the solver —
circular pinning, config-dependent; the ensemble-σ theorem's spirit honored
beyond its letter); raw counts-in-radius (a degenerate special case of the
kernel form with a new arbitrary constant). Model form: the Phase-8
covariate-lane pattern verbatim — log s affine in log n_eff, 2 dof, covariate
definition serialized into the calibration descriptor, hull + clip:
`s(x, era) = s_spatial(x) · exp(a + b · log n_eff(x, era))`.

**The extrapolation objection, answered structurally (recorded verbatim per
ruling):** the regressor is per-LOCATION sampling density, and density varies
enormously WITHIN one epoch (crossover diamonds vs mid-diamond voids, latitude
convergence, per-window mission dropouts) — a 5-mission epoch already contains
locally-2-mission-sparse neighborhoods; regressor SUPPORT overlaps across eras
even when era means differ. Pre-registered **support-overlap audit**:
sparse-era density distribution vs the fit hull, extrapolation fraction
reported per era; outside-hull predictions CLIPPED (Phase-8 hull/clip
discipline); a large extrapolation fraction is a recorded finding TABLING an
owner decision, never a silent clip.

Two-level validation: (1) held-out reference epoch — predict its per-era fit,
compare vs independently-fit s; (2) the fork-c sparse-epoch transfer reading
(once, masked). Reference-epoch selection criteria pinned NOW, table finalized
in Stage 0 from the census artifact: 2017/five-mission first by construction;
+2 chosen for constellation ≥4 (net of locked), maximum joint density-support
spread, instrument-class coverage of the record's mission families.

Pins:

1. **Gauge + identification:** (i) the density factor ≡ 1 at a pinned reference
   density n_eff₀ (anchor-epoch median; the λ_ref = 300 km gauge pattern
   reused), making s_spatial interpretable as "s at reference density";
   (ii) (a, b) are identified by CROSS-ERA contrast at matched locations —
   s_spatial absorbs era-invariant spatial structure; the covariate absorbs
   what changes with constellation — and the fit is CONSTRUCTED to enforce that
   split, not hoped into it. Without both, the held-out-epoch comparison tests
   refitting, not transfer.
2. **Regressor concretes:** (i) MIOST has a LADDER, not "the" solve scale — K
   is parameterized by a NAMED mid-ladder spatial scale in the λx neighborhood
   + the shipped L_t, rationale recorded; the fork-d pin-4 auto-follow linkage
   binds to the NAMED scale. (ii) n_eff is per-window; s(x, era) is era-static —
   aggregation pinned as per-location MEDIAN over the era's windows,
   deterministic, in the artifact schema.
3. **Locked-tier collision resolved structurally:** reference-epoch
   constellations counted NET of locked exclusions; the epoch table's locked
   column and reference selection are ONE table, finalized together in Stage 0;
   no epoch is ever both reference-assimilating and locked-scoring for the same
   mission.
4. **Small-n honesty:** ALL leave-one-reference-out rotations run and reported
   (three epochs → three) — the covariate's claim-bearing test is the set,
   never a chosen rotation.

Artifact discipline (endorsed): per-era, era-keyed, schema-versioned
(geometry-v3 pattern), content-addressed sha, deterministic-recompute test,
enters the provenance guard's per-era lists.

**E7 (flagged to the Stage-2 spec, named not designed):** the Phase-13
per-mission δ_m contrasts are constellation-dependent — per-era δ assignments
needed; instrument-class-match rule (δ_j3 := δ_j2n precedent) as the
presumptive mechanism; per-era gauge mean(δ) = 0 within the era's constellation.

### Fork F — the pre-registered global evaluation set

Two tiers. **Locked tier:** locked gauge subset = the universal locked spine,
ALL eras (the only instrument spanning 1993→present uniformly); c2 = the
altimeter locked track 2010→ (never-assimilated status extended).
**c2-cost honesty sentence (verbatim):** our product line forgoes c2's
observations wherever locked — a real data sacrifice the published products
don't make (B2023 assimilates CryoSat-2); that's the price of a locked test and
we state it. **Pre-2010 gap sentence (verbatim):** pre-2010 one-touch acceptance
rests on the locked gauges alone, crossovers report-only beside — constellations
of 2–4 can't afford a third tier on top of the validation holdout.

Gauges: PSMSL RLR ∩ UHSLC research-quality daily; screening criteria (recorded,
in order): datum continuity (RLR); era completeness; open-ocean siting
(island/offshore preferred, semi-enclosed/estuarine excluded); proximity ≤
correlation scale to valid ocean gridpoints; correction-consistency with the
altimetry stack (B2023 Eq.-1 reference, convention recorded).
**Skill-selection firewall sentence (verbatim):** data-QUALITY screening may
look at gauge data; SKILL-based selection may not — screening never consults
any map. Locked/dev split drawn AFTER screening, stratified (region ×
era-coverage). VLM: irrelevant for anomaly-tier scoring; REQUIRED for the
Stage-3 trend tier (GPS-colocated subset — a stricter column in the same
registry, contract-only this phase). The in-situ evaluator joins the registry
as a reference-based family member; `required_context` gains the in-situ
provider key — **the founding taxonomy completed**. Metrics: correlation + RMSE
vs a recorded null, per-gauge rows + era aggregate.

OSSE: contract now (TRUTH provider interface, dormant since 4b, re-arms
unchanged; per-era synthetic sampling = real constellation geometry over model
truth), run decision priced at Stage-1 plan time. Never claim-bearing for the
product; instrument-validation only.

Touch mechanics: ONE touch = one scoring pass of an accepted product over the
sealed locked set for its era range; per-product-per-era tally ledger; ceremony
inherited verbatim (exact-string env, provenance tripwires recompute sealed
shas BEFORE any locked data opens, refusal tests green pre-touch, dated defect
keys, misfire protocol per the owner 2026-07-20 recording). **The Stage-0 SEAL:
one sha-sealed evaluation-set artifact** — constraint 4 discharged as a single
auditable object.

Standing instruments, default rows (report-only; keyed (tile, era) via
`Registry.applicable` + `report_rows` — Phase-11 machinery, zero new surfaces):
GroundTrack per tile×era (**the 0.410→0.331 lineage continues — the founding
metric's closed loop, now the standing instrument of this program**);
SpectralFidelity per tile (band = tile extent); seam-dispersion rows per
adjacent pair (Task-18 rubric verdicts); flattening/G-shrinkage per era;
coverage + χ²_red per tile×era; extrapolation-fraction audit rows; crossovers
report-only.

Pins:

1. **Locked-gauge structural refusal:** locked gauge IDs refuse to load without
   the touch ceremony env, enforced in the loader exactly as the c2 path is.
   Quarantine is structural, never procedural: locked series may sit in the
   same PSMSL/UHSLC download, but the code cannot open them outside a touch.
   Refusal tests green pre-seal.
2. **Seal immutability + amendment window:** census-driven table edits (incl.
   "a ≥5 epoch may add a locked track") close AT the seal; the sealed artifact
   is immutable; any post-seal change = a NEW sealed version with owner
   sign-off and dated supersession-with-pointer — never an edit. The seal's sha
   goes into PROGRESS and is QUOTED by every subsequent evidence pack.
3. **Split determinism:** the locked/dev gauge split is SEEDED (stratified
   random), seed recorded inside the seal.
4. **Nulls are sealed config:** the gauge metrics' null models (which
   climatology, which persistence lag) are pinned in the sealed instrument
   config — never chosen at scoring time.
5. **OSSE's strongest value case named in the contract:** constellation varied
   over FIXED model truth is the only ground-truth test of the era-transfer
   claim (fork-e level 1 validates against fitted s; OSSE against truth) — the
   Stage-1 run decision must price that benefit, not just seam/kernel checks.
6. **Promotion discipline restated for the global context:** every standing row
   is report-only; promotion to a bar anywhere in this program goes through the
   pre-registration mechanism with owner sign-off — the box-scale rule, said
   once here so no tile/era table drifts into gating.

### Fork G — compute ladder

Tiers: **0** mini-PC dev fixtures + CI (every capability keeps a Tier-0
fixture — the dev-scope discipline survives scaling by construction); **1**
mini-PC production-tier sequential single-tile runs where sizing clears
(OOM-priced by the existing checkpoint/resume + retry machinery); **2** single
cloud node (SkyPilot) — first spend rung; **3** multi-node fan-out (per-tile/
per-era fleet; embarrassingly parallel outside blend assembly).

Spend gates: every stage plan carries a pre-registered SPEND TABLE (rung,
measured-cost basis, authorized ceiling per task class, **storage and egress
columns**); an execution-blocking spend outside its tier WAITS for the owner —
executor-set spend never happens (the Phase-10 standing rule, monied).
Ladder-climb rule: first use of each NEW rung is a probe-sized run whose
measured cost re-grounds the sizing model before any full run. Stage 0: Tiers
0–1 + ONE ceilinged Tier-2 probe serving both cost and determinism
measurements.

Determinism contract (the honest version, endorsed verbatim): pinned image
(pixi lock → container digest per run), derive_seed discipline unchanged,
content-addressed artifacts, single-writer evidence discipline. Cross-host
bit-identity NOT assumed. **Audit-locality rule:** no acceptance instrument may
REQUIRE cloud to re-verify given artifacts — cloud produces artifacts, the box
can always audit them; **on public-lineage artifacts, ANY third party at Tier 0
can audit — the reproducibility ethic stated as compute policy.**

Pins:

1. **Cross-env gate decomposed into its two variance sources:** the
   CRN/derive_seed DRAWS are asserted BIT-exact cross-host separately
   (hash-based, no FP reduction — proving it isolates randomness from
   arithmetic); the gate's tile×window includes ONE MEMBER SOLVE alongside the
   mean solve, with FP-order deltas toleranced. "Randomness reproduces
   bit-exactly; solves differ by measured FP order" — never one blended number.
2. **Two tolerances, two measurements:** the Tier-2 probe measures BOTH
   (a) cross-host single-thread delta (the gate) and (b) same-host multi-thread
   run-to-run spread. The production spot-check tolerance = the measured
   envelope of both — threading nondeterminism and cross-host arithmetic priced
   apart.
3. **Spend table gains storage/egress columns; member-artifact RETENTION
   flagged to the architecture with the determinism-enabled alternative NAMED:**
   CRN determinism makes "store the recipe (config + seeds), regenerate members
   on demand" a priced alternative to storing full member stacks (the U2022
   2 TB-class number is the stakes) — a storage-vs-recompute tradeoff the trend
   stage's temporal-coherence design consumes. Decided there; named now
   (carried in C2G→3).
4. **Tier-1 eligibility binds to MEASURED-available RAM at launch** (the
   Phase-8 predicate re-grounding lesson) — the co-tenant box's headroom is a
   measurement, not a constant.
5. **Data governance:** private-source (JPL-adapter) data never leaves
   owner-controlled hosts absent explicit owner authorization; public-lineage
   data may use any authorized tier.

---

## 5. Stage 0 — detailed design (ready for writing-plans)

### 0a — evaluation re-foundation

- **0a-1 Census artifact + epoch partition.** Loader-derived mission start/stop
  → deterministic constellation-change partition → named epochs;
  schema-versioned, content-addressed. Reference-epoch candidates computed NET
  of locked exclusions (fork-e pin 3).
- **0a-2 Epoch table.** epoch → missions → holdout(validation; criteria in the
  fork-c order) → locked-instrument → fit-vs-transferred; sparse-era handicap
  columns (fit-substrate fraction, ±66° mask). Drafted here, sealed at Gate 0.
- **0a-3 In-situ evaluator family.** Gauge loader (PSMSL RLR ∩ UHSLC daily);
  screening pipeline (recorded criteria; data-quality-only firewall); seeded
  stratified locked/dev split (seed inside the seal); locked-ID structural
  refusal in the loader with refusal tests green pre-seal; evaluator class
  registered (reference-based family; `required_context` in-situ provider key);
  null models in sealed config. Metrics: correlation + RMSE vs sealed null,
  per-gauge rows + era aggregate.
- **0a-4 Touch mechanics generalized.** Per-product-per-era tally ledger;
  ceremony verbatim (exact-string env, tripwires recompute sealed shas before
  any locked data opens, dated defect keys, misfire protocol).
- **0a-5 Seam rubrics + instrument configs into the seal.** Task-18 spatial
  rubric written BEFORE any tile exists; GroundTrack/fidelity per-tile configs.
- **0a-6 The SEAL.** One sha-sealed evaluation-set artifact (epoch table,
  locked gauge IDs + split seed, c2 era windows, instrument configs + nulls,
  seam rubrics); immutable; amendment = new sealed version + owner sign-off +
  dated supersession pointer; sha into PROGRESS, quoted by every subsequent
  pack.
- **0a-7 P0-2 blocking-precondition check** (Stage-B evidence clobber path,
  `tune_miost_inflation.py:117`) adjudicated before any evidence rerun touches
  that path. (P0-1 already disarmed `54db3e5`, Phase 12.)

### 0b — compute

- **0b-1 Sizing model at tile scale.** Task-22 extension with the
  retained-store term BY NAME; probe = ONE production-geometry tile at reduced
  days, Tier 0/1 (Task-0 pattern).
- **0b-2 Ladder + spend table.** Rungs 0–3; storage/egress columns; Tier-1
  eligibility = MemAvailable measured at launch; data-governance line;
  audit-locality rule incl. the third-party Tier-0 extension.
- **0b-3 Tier-2 probe (ceilinged, pre-authorized in the Stage-0 plan).**
  Measures: cloud cost basis; CRN cross-host bit-exactness (asserted
  separately, hash-based); single-thread cross-host solve delta; same-host
  multi-thread spread → TWO tolerances, priced apart. Includes one member solve
  beside the mean solve.
- **0b-4 Cross-env gate** (§10 gate 4) implemented on a box tile×window.

### 0c — input layer

- **0c-1 Loader contract + uniform descriptor** (source_id, dataset_version,
  content_manifest = per-file shas ALWAYS; JPL adapter computes at ingest).
- **0c-2 CMEMS multi-year adapter.** DT2021 pinned (the papers' vintage);
  downloader-reproducer pattern (dc2021a/dc2023 precedent); 1993→ coverage;
  version-migration protocol recorded (any DT change reruns golden-tile
  machinery cross-version).
- **0c-3 Synthetic third adapter + public CI conformance suite** (interface
  drift fails publicly).
- **0c-4 JPL adapter CODE (public) + artifact-gated conformance** behind the
  standing skip-guard pattern.
- **0c-5 Golden-tile cross-check MACHINERY.** Same tile/period/config through
  both adapters → map deltas + track-metric deltas; divergence TABLES an owner
  decision. Machinery Stage 0; EXECUTION artifact-gated (runs when JPL data is
  reachable, any stage); results public per the PDF-extraction precedent.
- **0c-6 Loader identity gate** (§10 gate 2): CMEMS adapter through the new
  loader reproduces the current 2017 box input path — obs table
  byte-comparable, downstream scores identical.

### 0d — tiling substrate (machinery only; no evaluation-bearing maps)

- **0d-1 Shared tile-frame helper.** core / blend-overlap / halo derived from
  the operative (NAMED) kernel scale; the anchor's degenerate single-tile frame
  reproduces the signed box frame EXACTLY (checked).
- **0d-2 Spatial blend.** Paper-linear edges + separable corner completion;
  partition-of-unity asserted numerically EVERYWHERE — interior, edges,
  corners, domain-edge/missing-neighbor renormalization — unit tests HERE, in
  Stage 0 (fork-d pin 2).
- **0d-3 Per-tile validation-scoring generalization** (batch-2 pin 2):
  tile-frame track extraction, per-tile λx/n_eff, per-tile provenance lists
  through the guard. Consumed by the fifth anchor identity check (§10).

**Gate 0 (owner):** seal signed (sha quoted); spend table authorized; adapter +
identity gates green; locked-refusal tests green; determinism tolerances
recorded. Posture: Tiers 0–1 + the one ceilinged Tier-2 probe; **zero
evaluation-bearing maps** (probe/cross-env solves are instruments, artifacts
labeled PROBE, never scored against validation or locked tiers); zero touches.

---

## 6. Stage 1 — detailed design (ready for writing-plans)

**Config policy (batch-1 pin 2, in full):**

- **(c) Fit-vs-ship at program scale:** all Stage-1 measurement runs ride the
  FIVE-MISSION workhorse (j3 validation — j3 flies globally in 2017; the
  workhorse pattern generalizes spatially). The six-mission-refresh election at
  Gate 1 sets the SHIPPED config **for Stage-2G assembly runs onward** — the
  election's scope is named in its trigger; if elected, it runs with its own
  chain + touch per the Phase-13 bundling rule, never a silent fold-in.
- **(a) Non-anchor tiles, honest labels:** raw posterior σ + scalar-s* transfer
  as a LABELED reference row — never presented as calibrated (the spatial s(x)
  is box-fit and does not transfer spatially). Their j3-side coverage/χ² IS the
  Stage-1 measurement that motivates Stage-2 calibration.
- **(b) Transfer-reading composition pinned:** per-tile j3-validation
  µ/λx/coverage/χ² at frozen config + reference-free rows + seam rubric
  verdicts.

**Tasks:**

- **1-0 Stage Task-0 probe.** First non-anchor tile, full geometry, reduced
  days; sizing re-check before any full run (measured-first, per stage).
- **1-1 Anchor identity gate** (§10, all five checks): the signed box through
  the generalized tiling path; four array routes rtol 1e-12 + score-level
  identity. The stage's first full run; **nothing else runs until green.**
- **1-2 Seam-pair run + seam ORACLE read.** Two standard tiles across the jet
  inside the anchor footprint; seam dispersion scored against the seamless
  signed truth under the SEALED rubric (rubric before numbers; no published
  precedent — recorded).
- **1-3 Diverse-tile runs** (equatorial, Southern Ocean, quiet gyre, Kuroshio)
  at frozen config, five-mission; per-tile evidence packs per policy (b).
  Kuroshio exercises the land-mask path.
- **1-4 High-latitude kernel decision pack.** SO-tile measured anisotropy +
  f-range arithmetic + the three options (km-space kernels / lat-varying degree
  scales / Paciorek — `PaciorekGaussianDegrees` exists, PD-proven, Phase 10);
  owner decides at Gate 1; the decision binds the halo auto-follow (fork-d
  pin 4). Made with the arithmetic recorded, never inherited from the box-scale
  negative.
- **1-5 Phase-10 revisit.** Pre-registered as EXISTING: frozen config = lane-0,
  diverse tiles, real f range (~100× globally vs 25% in-box), zero touches; its
  DESIGN (per-tile lanes vs cross-tile shared field, bands, budget) is a forked
  sub-design at Stage-1 plan time. The box-scale negative is never cited as
  transferring.
- **1-6 Equatorial lane-0 persistence** (fork-b pin 1): maps + evidence pack +
  frozen fold/eval frame stored as the future wave-increment comparison
  substrate; recorded under the frozen-config policy (fork-b pin 2).
- **1-7 OSSE run decision** at plan time, priced from Stage-0 numbers, the
  strongest value case included (fork-f pin 5).
- **1-8 Six-mission-refresh election at Gate 1.** Presumptive rule presented as
  recorded: instrument-class match, δ_j3 := δ_j2n (Poseidon-series); own chain
  + touch if elected; scope = Stage-2G assembly runs onward.

**Gate 1 (owner):** anchor identity (five checks); seam verdicts; six transfer
readings; kernel decision; revisit verdict; refresh election. **Zero
locked-instrument opens, zero c2, tally untouched.** Compute: Tier 0/1
preferred; Tier 2 per the pre-registered spend table if production-tier
arithmetic demands.

**Risks (expectation-setter, verbatim):** seams and high-latitude behavior are
the risks; the equatorial tile is EXPECTED weaker without wave modes (priced
~3% average / 10–20% local); the degree-space kernel's ~13% in-box cos-φ
anisotropy becomes ~2–3× poleward — the Southern-Ocean tile measures it.

---

## 7. Stage 2G — global assembly at one year (named; own spec later)

First global map: full tile fleet, one year, SHIPPED config per the Gate-1
election. **The shipped 2017 product carries CALIBRATED σ: per-tile
reference-epoch (2017) s-fits produced by Stage-2 machinery (C2→2G) — not raw
posterior σ, not box-transferred scalar s*.** (This is also the stated
justification for Stage 2 preceding 2G.) Pole handling (fork-d D4) decided here
with the Southern-Ocean measurement + kernel decision in hand. Fleet compute at
the fork-g rungs per its own spend table. **Its accepted product = the
program's FIRST accepted product: the locked set (locked gauges + c2 2017
windows) opens for the first time at its acceptance touch; tally entry named
for the shipped config.** Risk line: **assembly at scale** — poles, fleet
compute, land-mask everywhere, seam behavior at fleet count (the
feasibility-frontier lesson: worst-seam grew with tile COUNT — measured then,
watched here).

## 8. Stage 2 — scope summary (own spec later, consuming C1→2 + forks c/e)

Multi-year on the tile roster: era-aware calibration (fork e, all pins);
role-split validation protocol executed (fork c, all pins); per-era δ_m
assignments (E7); seasonal-axis unlock decision (recorded decision, not
automatic — n>1 years finally exists as its substrate); transferred-vs-refit
semantics recorded per era (the Phase-12 pattern, era-indexed — settled
constraint 9). Gate-2 evidence per §3.1; no locked opens (§3.3).

---

## 9. Deferred-thread ledger (thread → unlock; ⚖ = owner election required)

| Thread | Unlock | ⚖ |
|---|---|---|
| Seasonal axis (August 0.629 survives R change) | Stage 2, recorded decision | |
| Phase-10 search-scoped negative | Stage 1 revisit (task 1-5), per its recorded reopening condition | |
| MIOST-B representation | After the Stage-1 reading ("revisit only at the global domain") | ⚖ |
| Equatorial wave modes | Own phase after Stage 1; baseline = equatorial lane-0 (1-6) | ⚖ |
| SkyPilot ladder | Stage 0b (executed) | |
| TRUTH/OSSE (dormant since 4b) | Contract Stage 0; run decision Stage-1 plan time (1-7) | ⚖ |
| Tide-gauge / in-situ evaluator | Stage 0a (built — founding taxonomy completed) | |
| Six-mission refresh election (bundling rule) | Gate 1 (task 1-8) — the named global-domain trigger | ⚖ |
| Tuned-constant election / OI product question | Global domain, by owner election only (Phase-10 ruling 1); no stage claims it | ⚖ |
| Task-22 re-grounding (retained-store term) | Stage 0b-1 | |
| Mode-layer redesign note | C2G→3 contract input (§3.2) | |
| Hygiene P0-2 (Stage-B evidence clobber) | Stage 0a-7 blocking-precondition check | |

## 10. Gulf-Stream-anchor identity-gate set (settled constraint 1, five gates)

1. **Tiling identity:** anchor tile through the generalized tiling path ≡
   signed box records — four-route pattern (member arrays sha-equal, mean vs
   acceptance, Γ-route, variance), rtol 1e-12 (Phase-13 T3 precedent).
2. **Loader identity:** CMEMS adapter through the dual-source loader reproduces
   the current 2017 box input path — obs table byte-comparable, downstream
   scores identical.
3. **Era-machinery no-op:** era-keyed calibration evaluated at the reference
   epoch = signed s(x) EXACTLY, BY CONSTRUCTION (fork-e pin 1's gauge: density
   factor ≡ 1 at n_eff₀) — an identity, not a tolerance.
4. **Cross-env gate** on a box tile×window (fork-g pin 1 decomposition: CRN
   bit-exact asserted separately; mean + one member solve FP-toleranced).
5. **Score-level identity:** the generalized per-tile scorer (0d-3) on the
   anchor tile reproduces the signed (µ, σ, λx) NUMBERS — beside the four array
   routes.

Nothing re-opens signed records; every gate is a refusal, not a hope.

## 11. Honest expectation-setters (the verbatim sentence set)

- Program-level: §0's overconfident-bars sentence.
- Stage 1: seams + high-latitude (§6); equatorial priced-weaker.
- Stage 2: era transfer; negative path measured-not-shipped (§3.1).
- Stage 2G: assembly at scale (§7).
- Stage 3: temporal coherence (§3.1).
- Sparse-era honest sentence (§4 fork c).
- c2-cost honesty + pre-2010 gap + skill-selection firewall (§4 fork f).
- GroundTrack 0.410→0.331 lineage: the founding metric's closed loop, now this
  program's standing instrument (§4 fork f).

## 12. Out of scope (stated, not built)

SWOT/swath (Phase-13's capability contract points there; nothing here consumes
it); internal tides; operational/NRT latency; any dilution of the touch or
provenance disciplines (settled constraint 10: protocols, tuner core
(scalar-box — field parameters remain low-dof scalar-coefficient providers),
provenance guard generalized-never-weakened, all signed box-scale records,
one-touch ethic generalized in Stage 0 and never diluted); Stage-2/2G/3
implementation (contracts only); reopening any signed record.

---

## 13. Self-review + pin-coverage map

Self-review executed against the kickoff prompt, all seven fork rulings, and
both batch approvals. Placeholder scan: none. Contradiction scan: the Gate-0
"zero maps" wording corrected to "zero evaluation-bearing maps" (batch-2
pin 3). Scope: Stages 0/1 detailed for writing-plans; 2/2G/3 contract-only —
matches the program-not-monolith mandate.

**Pin-coverage map (every pin → section):**

| Pin | Section |
|---|---|
| Fork A pin 1 (three-layer testability) | §4-A.1; 0c-3/0c-4/0c-5 |
| Fork A pin 2 (golden-tile epistemics + placement) | §4-A.2; 0c-5 |
| Fork A pin 3 (uniform content-addressed descriptor) | §4-A.3; 0c-1 |
| Fork A pin 4 (super-obs loader-layer) | §4-A.4 |
| Fork A pin 5 (version migration) | §4-A.5; 0c-2 |
| Fork A notes (live date / 10–20% / bundling-rule placement) | header; §2; §1 + 1-8 |
| Fork B pin 1 (baseline = future lane-0) | §4-B.1; 1-6 |
| Fork B pin 2 (config-policy control) | §4-B.2; §6 policy |
| Fork B pin 3 (Q gap-register inheritance) | §4-B.3 |
| Fork B pin 4 (10°N edge → fork d) | §4-B.4; §4-D3 tile 3 |
| Fork B placement (own electable phase) | §4-B header; §9 |
| Fork C pin 1 (fit/validate separation) | §4-C.1; §4-E validation |
| Fork C pin 2 (locked column, one registry) | §4-C.2; 0a-2 |
| Fork C pin 3 (±66° mask) | §4-C.3; 0a-2 |
| Fork C pin 4 (sibling-less budget priors) | §4-C.4 |
| Fork C pin 5 (epoch boundary → fork d) | §4-C.5; §4-D6 |
| Fork D pin 1 (Kuroshio) | §4-D3 tile 6; 1-3 |
| Fork D pin 2 (partition-of-unity everywhere, Stage-0 tests) | §4-D pins; 0d-2 |
| Fork D pin 3 (two envelopes) | §4-D pins; §4-G tiers |
| Fork D pin 4 (halo from named operative scale) | §4-D pins; 0d-1; §4-E pin 2i; 1-4 |
| Fork D pin 5 (D6 accepted-approximation) | §4-D pins |
| Fork D pin 6 (revisit sub-design at plan time) | §4-D pins; 1-5 |
| Fork E pin 1 (gauge + identification) | §4-E.1; §10 gate 3 |
| Fork E pin 2 (named K scales; median aggregation) | §4-E.2; 0d-1 linkage |
| Fork E pin 3 (net-of-locked, one table) | §4-E.3; 0a-1/0a-2 |
| Fork E pin 4 (all rotations) | §4-E.4; §3.1 Gate 2 |
| Fork E endorsed verbatim (E2 argument, σ-covariate rejection, audit) | §4-E body |
| Fork E E7 (per-era δ) | §4-E E7; §8 |
| Fork F pin 1 (structural refusal) | §4-F.1; 0a-3 |
| Fork F pin 2 (seal immutability) | §4-F.2; 0a-6 |
| Fork F pin 3 (seeded split) | §4-F.3; 0a-3/0a-6 |
| Fork F pin 4 (sealed nulls) | §4-F.4; 0a-3 |
| Fork F pin 5 (OSSE strongest case) | §4-F.5; 1-7 |
| Fork F pin 6 (promotion discipline) | §4-F.6 |
| Fork F verbatim sentences | §4-F body; §11 |
| Fork G pin 1 (cross-env decomposition) | §4-G.1; 0b-3/0b-4; §10 gate 4 |
| Fork G pin 2 (two tolerances) | §4-G.2; 0b-3; §3.2 C0→1 |
| Fork G pin 3 (storage/egress + retention alternative) | §4-G.3; 0b-2; §3.2 C2G→3 |
| Fork G pin 4 (measured RAM) | §4-G.4; 0b-2 |
| Fork G pin 5 (data governance) | §4-G.5; 0b-2 |
| Fork G endorsed (honest determinism, audit locality + third-party, one probe) | §4-G body; §5 Gate 0 |
| Batch-1 pin 1 (Stage 2G named, own risk) | §3.1; §7 |
| Batch-1 pin 2a (honest labels) | §6 policy (a) |
| Batch-1 pin 2b (reading composition) | §6 policy (b) |
| Batch-1 pin 2c (fit-vs-ship + election scope) | §6 policy (c); 1-8 |
| Batch-1 pin 3 (Gate-2 locked correction) | §3.1 Stage 2; §3.3 |
| Batch-1 pin 4 (election-marker column) | §9 |
| Batch-2 pin 1 (contract chain + 2G payloads + §J σ) | §3.2; §7 |
| Batch-2 pin 2 (per-tile scorer task + fifth identity check) | 0d-3; §10 gate 5 |
| Batch-2 pin 3 (zero evaluation-bearing maps wording) | §5 Gate 0; §3.1 Stage 0 |
| Batch-2 pin 4 (marker column + verbatim pin record) | §9; §4 |
| Settled constraint 8 verbatim in the Stage-3 contract | §3.2 C2G→3 |
| Kickoff evidence-design requirements | §3 (architecture+gates), §5/§6 (Stage 0/1), §9 (ledger), §10 (anchor gates), §11 (expectation-setters) |
