GOAL: design "Phase 14 — scaling": global domain, multi-decade record, era-aware
calibration — the conversion of a one-box/one-year demonstration into a product
candidate. NAMED DESTINATION, stated in the spec and shaping every stage: per-gridpoint
SEA-LEVEL-TREND ERROR BARS from calibrated ensembles propagated through the 25+ year
altimetry record — honest regional sea-level-rise uncertainties, the climate
deliverable the JPL SSHA product exists for. This is a PROGRAM design, not a capability
design: the deliverable of THIS phase is (1) the program architecture with staged
scope, owner gates, and interface contracts between stages (the Phase-9→10 contract
pattern, at program scale), plus (2) the fully-designed FIRST executable stage.
Later stages get their own specs consuming this phase's contracts. Refuse the monolith.
This is a design session: clarifying questions one at a time, then design sections in
batches for my review, then commit the spec to
docs/superpowers/specs/2026-07-21-phase14-scaling-program-design.md, PUSH, and STOP
before writing-plans.

PREREQUISITE (hard): Phase 11 CLOSED and pushed. Record Phase 12 and Phase 13 statuses
— stages of this program consume their outputs (12: the six-mission production
convention; 13: the structured-error augmentation machinery, which the trend stage
REQUIRES — see constraint 8); neither blocks the program DESIGN, but every dependency
is recorded, never assumed.

GOVERNING INPUTS (read first; verify every repo claim against source):
- The papers brief: what U2021/U2022/B2023 do AT GLOBAL SCALE — component structure
  (mesoscale + barotropic/high-frequency + equatorial wave modes; the recorded ">10%
  local error reduction" equatorial finding), tiling/assembly, and what they DON'T
  publish. The global design must be paper-faithful where the papers speak and
  gap-registered where they don't (the Phase-7 discipline).
- The full deferred-thread ledger this program gates (from PROGRESS; verify each):
  seasonal axis (blocked on n=1 years — unlocks at multi-year); the Phase-10
  search-scoped negative (recorded reopening condition: f varies ~100× globally vs 25%
  in-box — lat-varying parameters STOP being optional at global scale); MIOST-B
  (deferred "to the global domain" in the Phase-10 rulings); equatorial wave modes;
  the SkyPilot compute ladder; the TRUTH/OSSE context (dormant since 4b — a global
  OSSE, e.g. NATL60-class, re-arms it for tiling validation); the tide-gauge /
  in-situ evaluator family (named in the founding evaluator taxonomy, never built).
- The machinery that scales as-is vs needs generalization: halo_obs framing + the
  window/blend machinery (spatial-tiling analog); seam-dispersion instruments (Phase-7
  Task 18 — the tile-seam discipline already exists in temporal form); the Phase-9
  product-agnostic calibration harness (era-aware fits run THROUGH it — it already
  supports per-product descriptors and covariates); the Phase-11 geometry provider
  (per-era artifacts) + reference-free instruments (per-tile, trivially); Task-22
  sizing arithmetic; the provenance guard (per-era assimilated lists).
- The Phase-8 covariate theorem, restated precisely because it MATTERS here: the
  ensemble-σ covariate was killed because posterior covariance is independent of obs
  VALUES — a SAMPLING-DENSITY covariate is derived from obs GEOMETRY, not values, so
  it is LEGAL, deterministic, and pinnable. This distinction is load-bearing for
  era-aware calibration (constraint 5).

PROGRAM SHAPE (settled — design inside this staging; stage boundaries may move with
argument, the staged-with-gates structure may not):
- STAGE 0 — foundations: (a) EVALUATION RE-FOUNDATION: define what "locked test" means
  for a global multi-year product BEFORE any global map exists — pre-registered
  held-out missions per era + independent in-situ (tide gauges) + the reference-free
  suite per tile; the one-touch discipline generalized to the pre-registered global
  evaluation set; (b) COMPUTE PROBES: measured tile-scale costs → the sizing model →
  the SkyPilot ladder design with OWNER-AUTHORIZED SPEND TIERS (the budget standing
  rule, now with real money: execution-blocking spend decisions get pre-registered
  tiers or the task waits); (c) INPUT-DATA strategy (fork a).
- STAGE 1 — spatial scaling at ONE year (2017, the proven constellation): tiling +
  halo + spatial blend on 3–5 pre-registered DIVERSE tiles (the Gulf Stream box as the
  anchored regression — the signed record is the identity oracle; an equatorial tile;
  a Southern Ocean tile; a quiet-gyre tile), tile-seam instruments (the Task-18
  pattern, spatial), reference-free rows per tile, and the PHASE-10 REVISIT executed
  per its recorded reopening condition (lat-varying parameters at real f range —
  the lane apparatus reuses verbatim; the box-scale negative does not transfer and
  must not be cited as if it did). Equatorial wave modes: in-scope decision at fork b.
- STAGE 2 — temporal scaling at fixed domain: multi-year, era-aware calibration
  (constraint 5), the per-era validation-mission protocol (fork c — nontrivial: 1993
  has TWO satellites; holding one out is half the data and TOPEX is the
  climate-reference), seasonal-axis unlock decision (recorded, not automatic).
- STAGE 3 — the record + the trend product: full-record assembly, the TREND-ERROR
  machinery (constraint 8 — the crux), per-gridpoint trend bars, validation against
  tide-gauge trends + published GMSL/regional budgets. Stage 3's spec is written
  AFTER stages 0–2 report; this phase delivers its interface contract only.
Owner gates between stages; each stage's acceptance instruments named in this spec.

SETTLED CONSTRAINTS (design inside these):
1. THE GULF STREAM BOX IS THE PERMANENT REGRESSION ANCHOR: every generalization
   (tiling, era machinery, new components) must reproduce the signed box records
   through the generalized path (identity-gated, the Phase-9 migration pattern).
   Nothing re-opens the signed box results.
2. TILING = the window/blend discipline in space: derived tile frames + halos from
   ONE shared helper (the halo_obs lesson — no per-runner tile framing); pre-registered
   seam instruments with the Task-18 verdict-rubric pattern (rubric before numbers);
   blend by actual overlap, seams measured never assumed.
3. HIGH-LATITUDE HONESTY: the degree-space kernel's cos-φ anisotropy (~13% in-box)
   becomes ~2–3× poleward — the Phase-10 degree-space note scales into a real design
   question (km-space kernels vs lat-varying degree scales vs Paciorek — the
   invariant-12 machinery exists; the decision is Stage 1's, made with the f-range
   arithmetic recorded, not inherited from the box-scale negative).
4. EVALUATION BEFORE PRODUCT (Stage 0 precedes everything): no global map is produced
   before the locked evaluation set, the touch discipline, and the per-tile/per-era
   report instruments are pre-registered. The project's founding rule — the test is
   defined before the thing it tests exists — applied at program scale.
5. ERA-AWARE CALIBRATION (the named subtlety, shaping Stage 2): s(x) was fit on 2017's
   five-mission geometry; representation error is CONSTELLATION-DEPENDENT and does not
   transfer to a 1993 two-satellite era. Two legal routes, both supported by the
   Phase-9 harness today, brought as a fork with my leaning: (i) PER-ERA fits
   (assumption-free, data-hungry, ~one fit per constellation epoch); (ii) a
   SAMPLING-DENSITY COVARIATE (legal per the theorem distinction above; one fitted
   relationship generalizing across eras; the physically-right regressor). Leaning:
   HYBRID — per-era fits at 2–3 reference epochs as ground truth, the density-covariate
   model fit across them, validated on a held-out epoch; the covariate definition
   derived from the geometry artifacts (deterministic, pinnable, era-keyed).
6. VALIDATION-MISSION-PER-ERA protocol pre-registered (Stage 2): which mission is held
   out per epoch, chosen by recorded criteria (never the climate-reference mission
   where an alternative exists; the sparse-era handicap quantified and stated);
   crossover diagnostics and tide gauges as the era-spanning independent checks —
   the in-situ evaluator joins the registry as a REFERENCE-BASED family member
   (required_context gains the in-situ provider key; the founding taxonomy finally
   completed).
7. COMPUTE DISCIPLINE: measured-first (Task-0 pattern per stage); the sizing model
   extended and validated before any large run; SkyPilot ladder with owner spend
   tiers; reproducibility survives the cloud (pinned images, seeded everything,
   artifact provenance — the container-to-cloud determinism contract stated).
8. THE TREND-ERROR CRUX, named now so Stage 3's contract is honest: the CURRENT
   ensemble carries ZERO inter-annual error correlation (60-day windows; members
   independent beyond blend overlap) — and trend uncertainty is DOMINATED by
   long-memory systematic errors (inter-mission biases, orbit/reference-frame and
   instrument drifts; the published GMSL error budgets are systematic-term-dominated).
   A trend product on today's machinery would ship overconfident bars — the exact
   thing this project exists to refuse. Stage 3 therefore REQUIRES: (a) inter-mission
   bias/drift error components as structured terms with priors from PUBLISHED budgets
   — the Phase-13 augmentation machinery at climate timescale (the recorded
   dependency); (b) ensemble TEMPORAL COHERENCE for those components across
   windows/years (era-keyed CRN draws held fixed across windows — the CRN identity
   machinery extended); (c) trend-bar validation = coverage of tide-gauge trends
   (VLM-corrected gauges, caveats recorded) + consistency with published budget
   totals. The interface contract this phase writes for Stage 3 carries (a)–(c)
   verbatim.
9. CALIBRATION LINEAGE DISCIPLINE at scale: which config is the fit substrate per era
   (the five-mission-workhorse rule generalizes: per-era held-out mission), which
   products ship, and the transferred-vs-refit semantics recorded per product — the
   Phase-12 pattern, era-indexed.
10. Untouched: protocols; the tuner core (scalar-box — field parameters remain
    low-dof scalar-coefficient providers); the provenance guard (generalized, not
    weakened); all signed box-scale records; the one-touch-per-accepted-product ethic
    (generalized in Stage 0, never diluted).

GENUINE OPEN QUESTIONS (bring as forks, one at a time, with a recommendation each):
a. INPUT DATA strategy: public CMEMS/AVISO multi-year L3 vs the owner's own
   JPL-processed along-track SSHA (the actual production-integration story) — design
   the loader abstraction to serve BOTH; decide what the public repo demonstrates on
   vs what production consumes; provenance/pinning implications of each.
b. STAGE-1 COMPONENT SCOPE: global mesoscale-only first (leaderboard-faithful,
   smallest honest step) vs including barotropic/equatorial components from the start
   — with the papers' component structure and the recorded equatorial finding costed.
c. THE PER-ERA VALIDATION PROTOCOL: held-out-mission selection criteria per epoch;
   the two-satellite-era handicap handling; where crossovers and gauges substitute.
d. TILE GEOMETRY: size/overlap/blend given the correlation scales and the sizing
   model; pole handling; the 3–5 pre-registered Stage-1 tiles and why those.
e. ERA-AWARE CALIBRATION route (constraint 5's hybrid leaning) + the density-covariate
   definition (what function of the geometry artifact; pinned how).
f. EVALUATION SET (Stage 0's core): the pre-registered global locked set — held-out
   missions per era, gauge network + screening criteria, OSSE role, the generalized
   touch mechanics — and what the standing instruments (GroundTrack per tile,
   fidelity, seam rubrics, flattening per era) report by default.
g. COMPUTE LADDER: tier structure, spend-gate placement, the box-vs-cloud determinism
   contract, and what stays runnable on the mini-PC (the dev-scope discipline must
   survive scaling).

REQUIRED EVIDENCE DESIGN (in the spec): the program architecture with stage gates and
interface contracts (Stage-3's contract carrying constraint 8 verbatim); the Stage-0/1
detailed design ready for writing-plans; the deferred-thread ledger with each thread's
unlock stage named; the Gulf-Stream-anchor identity-gate set; the honest
expectation-setters per stage (Stage 1: seams and high-latitude behavior are the risks;
Stage 2: era transfer is the risk; Stage 3: temporal coherence is the risk).

OUT OF SCOPE (state, don't build): SWOT/swath (Phase-13's contract points there;
nothing here consumes it); internal tides; operational/NRT latency; any dilution of
the touch or provenance disciplines; Stage-2/3 implementation (contracts only);
reopening any signed record.

PROCESS: superpowers brainstorming flow; verify against source before asserting;
design sections in batches for my review; self-review against this prompt; commit the
spec; PUSH; STOP for owner file review before writing-plans.
