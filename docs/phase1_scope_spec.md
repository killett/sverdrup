# Phase-1 Scope Specification
### Global gridded SSHA framework with rigorous per-gridpoint uncertainty

**Status:** Settled. No open architectural questions remain for Phase 1.
**Purpose:** Single authoritative reference for the Phase-1 build. This document supersedes the scoping conversation; it is self-contained and is the basis from which the Phase-1 Claude Code prompt will be written.
**Governing discipline:** Decide the abstractions now — they must be global-ready. Defer the implementations behind them. Do not pre-engineer later phases.

---

## 1. Project north star (context for Phase-1 decisions)

A Python framework that applies any of several SSHA gridding algorithms — individually, sequentially, or in parallel — to a heterogeneous set of nadir satellite altimeters (reference-orbit missions such as Sentinel-6; high-latitude drifting-orbit missions such as CryoSat-2) and produces a **global** regular-gridded sea-surface-height-anomaly (SSHA) product **with a rigorously estimated per-gridpoint uncertainty**, plus a layer for **rigorously comparing** the resulting grids and their uncertainties. The eventual system also supports independent-data evaluation (data withholding) and an autonomous parameter-tuning loop. None of those eventual capabilities are built in Phase 1, but Phase-1 abstractions must not preclude them.

Two standing principles that shape everything:

- **Global is reached by orchestration, not by a globally-scalable method.** Global coverage is achieved later by a *method-agnostic, framework-level* tiling/blending layer: decompose the globe into overlapping tiles, run any method per tile, blend across halos. The per-tile solve can therefore stay simple (dense OI is tractable inside one tile). Framework-level tiling is kept strictly distinct from any *method-internal* tiling (e.g., GPSat local-expert patching), so a method-specific scaling trick never leaks into the framework spine.
- **The Ocean Data Challenges (ODC) are a resource, not a foundation.** Use ODC for (a) reference data (NATL60 OSSE simulations, OSE along-track, the SWOT challenge data), (b) reference metric *definitions* (so our numbers are literature-comparable), (c) reference baselines, and (d) a correctness oracle (reproducing ODC leaderboard numbers validates our framework). Do **not** build structurally on top of the ODC notebooks; wrap ODC behind our own interfaces.

---

## 2. Phase-1 objective and build philosophy

**Phase-1 objective:** Build the core abstractions plus a single regional tile and a basic accuracy + calibration evaluation, running locally on one 64-CPU Linux machine.

**Regional-first as tile-zero.** The regional run is *tile-zero* of the global system, not a throwaway prototype. The same solve, run over one window, is what later runs over many windows. Nothing in the regional path may assume regional-only conditions.

**Real vs stubbed.** Phase 1 commits the *interfaces, capability declarations, and seams* in full. It leaves the *machinery* behind them minimal or stubbed wherever its consumers (tiling, per-method ensembles, the tuner) do not yet exist. Where a seam can only be proven real by exercising it, Phase 1 implements the minimum needed to prove it (see §5.4).

---

## 3. Hard constraints (global-readiness invariants)

These are load-bearing. Baking in their negation forces a later rewrite, so they hold from the first commit even though their consumers arrive later. **Do not "optimize away" any of these for regional convenience.**

1. **Projection-aware grid.** The grid spec does not assume a flat regular lon/lat grid.
2. **Lazy/chunked observation access.** No code path assumes all observations fit in memory.
3. **Windowable solve.** The regional run is one window; global is many. The solve operates on a window.
4. **Rich uncertainty representation.** The uncertainty output is a first-class *predictive distribution over the SSHA field*, never a grid-plus-error-bar. Covariance and coherent samples are available, not just marginal variance.
5. **Execution behind a port.** Compute runs behind a swappable Executor port whose unit of work is a single windowed solve.
6. **Field-capable parameters.** Method parameters are accessed through a provider that can return scalars *or spatial fields*. Provenance records the parameter field actually used, never a scalar shortcut.
7. **Distribution-correct regridding.** A predictive distribution is regridded by regridding its samples or by applying the regridding operator to its covariance — never by naively interpolating a marginal-variance map.
8. **Typed-chain provenance.** Uncertainty provenance is a typed chain of transformations (native → synthesized[type] → recalibrated[…]), not a boolean; synthesized uncertainty is never presented as native.
9. **Reference-agnostic evaluation.** The evaluator interface does not assume a reference (withheld data) exists; intrinsic, reference-free metrics are first-class. The tuning objective is vector-valued (multi-objective), never a single baked-in scalar.
10. **Closed derived quantities.** Derived quantities are `Distribution → Distribution` and propagate uncertainty using the grid's CRS metric.

---

## 4. The eventual cross-cutting consequences these invariants serve (informative)

Recorded so later phases inherit the rationale, not as Phase-1 work:

- **Tiling vs uncertainty.** The blend must stitch *uncertainty*, not just the mean field, so it needs covariance and coherent samples (invariants 4, 7). Halo width must track the spatially-varying correlation scale (~100 km at high latitude to ~800 km at the equator); sized at a few correlation lengths it makes both estimate and variance seam-free, with the equatorial band as the tractability stress case.
- **Science depends on inter-point correlation.** Geostrophic currents (differences of neighbors), EKE, transports, and area-averages have uncertainties that depend on covariance; marginal variance alone cannot propagate to them (invariants 4, 10).
- **Spatially-varying parameters become fields.** No single global covariance scale is valid, so the tuner eventually produces parameter *fields*, not scalars (invariant 6).
- **Honest comparison/calibration needs whole-field samples** (invariant 4).

---

## 5. Committed interfaces and abstractions

Signatures below are **illustrative** — they pin down contracts and capability shapes, not internals. Implementation choices (concrete classes, libraries, data structures) are left open unless named as a constraint.

### 5.1 Observation data model (along-track in)

**Contract.** Heterogeneous nadir along-track Level-3 SLA from multiple missions, each observation carrying at minimum: mission/source id, time, longitude, latitude, SLA value, and an **observation error model** — *not* merely a scalar noise σ.

- The error model must be able to express **correlated** errors, not only white noise. This is required for unbiasedness (the long-wavelength along-track correlated-error problem) and is the same hook that later absorbs SWOT's 2-D correlated KaRIn errors.
- **Lazy/chunked access** (invariant 2): the data-source interface yields observations for a requested window without materializing the global set.
- **Swath-ready (deferred).** The geometry abstraction must be general enough to later carry 2-D swath samples and their cross-swath correlated error. Phase 1 implements point (nadir) observations only.
- **Anomaly semantics.** The framework ingests SLA *anomalies*. Mean-surface / MDT / MSS handling is upstream and out of scope.

**OSSE vs OSE (both in Phase 1).**
- **OSSE:** a reference truth field is *present*; observations are sampled from truth along realistic orbits. Phase 1 uses **ODC NATL60** pre-simulated nadir observations and its truth field — **no custom observation simulator is built in Phase 1**.
- **OSE:** truth is *absent*; real along-track data is ingested; withheld observations are the only evaluation signal.
- The presence/absence of a truth field is a property of the configured dataset, surfaced to the evaluation layer via an optional truth provider (§5.6).

### 5.2 Method interface (the mapping algorithm contract)

**Contract.** A method consumes windowed observations + a grid spec + resolved parameters and produces a **predictive distribution over the SSHA field** (§5.3) — never a bare grid-plus-error-bar.

**Capability declaration.** Each method declares its *native* uncertainty capability, mirroring a small enum: `POINT` / `MARGINAL_VARIANCE` / `COVARIANCE` / `SAMPLES`. The framework uses this to decide whether to consume the method natively or lift it via an adapter (§5.3).

```python
class UncertaintyCapability(Enum):
    POINT = auto()              # estimate only, no spread
    MARGINAL_VARIANCE = auto()  # per-gridpoint variance, no cross-covariance
    COVARIANCE = auto()         # full/queryable covariance
    SAMPLES = auto()            # can draw whole-field realizations

class Method(Protocol):
    native_capability: UncertaintyCapability
    def solve(self, obs: ObsWindow, grid: GridSpec,
              params: ResolvedParams) -> PredictiveDistribution: ...
    def parameter_space(self) -> ParameterSpace: ...   # declarative; consumed later by the tuner
```

**Parameters via a provider (invariant 6).** A method never reads scalar parameters hardcoded into its solve. It reads from a `ParameterProvider` that resolves a parameter to a scalar, a function of latitude, or an interpolated field. Phase 1 may inject a constant provider, but the seam exists and provenance records the resolved field.

```python
class ParameterProvider(Protocol):
    def resolve(self, name: str, grid: GridSpec) -> ScalarOrField: ...
```

**The two starting methods.** Chosen to bracket the uncertainty space at minimal method-specific cost:

- **Method 0 — trivial baseline, `POINT`.** Produces a point estimate with *no* uncertainty (e.g., the ODC naive interpolation). Its purpose is to force the interface to handle UQ-absent from day one. It is lifted to the full distribution interface by an adapter, and that uncertainty is flagged synthesized.
- **Method 1 — GP/OI, `SAMPLES` (and `COVARIANCE`).** The reference baseline every method must beat (objective analysis ≡ optimal interpolation ≡ kriging ≡ GP regression). It emits a Gaussian posterior that natively exposes closed-form covariance *and* whole-field sampling, so a single implementation exercises two representations and stress-tests the interface. Mature public Python exists (pyinterp; GPSat; ODC `baseline_oi`).

### 5.3 Predictive-distribution object (headline abstraction)

**The uncertainty output is a first-class object, not a grid plus error bars.** One interface, three capabilities:

```python
class PredictiveDistribution(Protocol):
    grid: GridSpec
    provenance: UncertaintyProvenance              # typed chain; see below

    def marginal_variance(self) -> Field: ...       # per-gridpoint variance/std
    def covariance(self, points_a, points_b) -> CovBlock: ...
        # pairwise covariance, queryable ON DEMAND.
        # MUST NOT materialize a dense global grid x grid covariance matrix.
    def sample(self, m: int, seed: Seed) -> Iterable[Field]: ...
        # seeded, reproducible whole-field realizations.
    def regrid(self, target: GridSpec) -> "PredictiveDistribution": ...
        # via samples or covariance-operator only (invariant 7).
```

**Canonical representations.**
- **Compute-time canonical representation:** an ensemble of `M` sample maps — the default, bounded-cost representation. Marginal variance and pairwise covariance are derivable from it.
- **Gaussian-native methods** (OI/GP) may *additionally* expose closed-form covariance and closed-form sampling. **No Gaussian-only or closed-form-only assumption appears anywhere**; the interface also serves non-Gaussian posteriors.
- **Persisted representation (storage):** sufficient statistics + generator — mean, marginal variance, a low-rank covariance factor, the seed, and the sampler spec — **not** the `M` full sample maps (which is ~`M`× storage blowup at global scale). Because sampling is seed-deterministic, full samples are regenerable on demand.

**Governing asymmetry (why the contract is built around the rich representation).** Rich → poor is free: samples or covariance trivially yield marginal variance. Poor → rich is impossible without adding assumptions or computation. Building the contract around the rich representation therefore maximizes extensibility.

**Adapters (write-once, reusable) lift poorer methods to the full interface:**
- **Perturb-and-ensemble** wrapper for deterministic (`POINT`) methods.
- **Gaussian-with-diagonal-covariance** wrapper for `MARGINAL_VARIANCE`-only methods.
- Any uncertainty produced by an adapter rather than natively is **flagged synthesized in provenance and never presented as native.**

**Committed refinements (from the tensions review — these are decisions, not options):**

- **Prefer native covariance; use samples for nonlinear functionals.** Sample-derived covariance suffers catastrophic cancellation for differences/gradients — `Var(a−b) = Var(a)+Var(b)−2·Cov(a,b)` is a small difference of large, near-equal numbers, and Monte-Carlo error is amplified by ≈ `1/(1−corr)`. So linear functionals prefer native (closed-form) covariance when available; nonlinear functionals (where analytic propagation is only first-order) use samples.
- **Provenance is a typed chain** (invariant 8). Each synthesis type carries its known bias direction — e.g., the perturb-and-ensemble adapter *under-disperses in data voids* because it propagates input/observation noise but not the interpolation/representativeness error (the dominant term away from tracks). Downstream consumers must be able to read *which* synthesis and *what bias*, not merely that it is synthesized.

```python
@dataclass
class UncertaintyProvenance:
    native_capability: UncertaintyCapability
    transformations: list[UncertaintyTransform]   # ordered chain
    # each transform records: kind (e.g. INPUT_PERTURBATION, DIAGONAL_INFLATION,
    # POSTERIOR_RECALIBRATED), known_bias hint, and parameters used.
```

- **Two distinct sampling capabilities.** `reproducible_sampling` (same seed → same ensemble within a run; universal; for caching, reproducibility, comparison) is distinct from `cross_tile_coherent_sampling` (coupled draws across adjacent tiles so the future blend can stitch uncertainty member-wise; optional, method-dependent, only *approximate* under tiling, best achieved by white-noise-transform samplers such as SPDE/GMRF driven by a globally-indexed noise field). Phase 1 commits the seed-deterministic sampling that *enables* the latter; the blend itself is deferred.

### 5.4 Derived-quantity seam (closure)

**Type closure (committed).** A derived quantity of a predictive distribution is itself a predictive distribution exposing the same three capabilities:

```python
class DerivedQuantity(Protocol):
    linearity: Linearity   # LINEAR | NONLINEAR  -> selects propagation route
    def apply(self, dist: PredictiveDistribution) -> PredictiveDistribution: ...
```

**Propagation dispatch (committed).** Routed by *representation × functional-linearity*: linear functionals use the covariance path (native covariance preferred); nonlinear functionals use the sample path. Operators are **CRS-aware** (invariant 10) — spatial derivatives use the grid metric (e.g., `cos(lat)` and Earth-radius factors on lon/lat, the correct metric on a projected grid), never index-space finite differences.

**"Real closure" — one operator implemented end-to-end.** To make the closure *demonstrated*, not merely declared, Phase 1 implements exactly one reference operator: a **spatial first-difference**. It is the cancellation-sensitive linear case, the building block of geostrophic velocity, and the most failure-prone path in the interface; a working first-difference proves the covariance propagation avoids the Monte-Carlo blowup.

**Stubbed (committed signatures, no bodies):** full geostrophic velocity (CRS metric + Coriolis), eddy kinetic energy (the nonlinear functional that exercises the sample path), transport, and area-average. Their signatures are committed so the closure is verified to compose; their bodies are deferred.

### 5.5 Grid spec

- **CRS-aware via a standard** (pyproj / CF conventions). Projection-awareness is satisfied by the type itself, not by branching. Defaults to lon/lat for the regional tile; can instantiate polar-stereographic. Does **not** assume a flat regular lon/lat grid (invariant 1).
- **True spherical `cell_area` is a first-class property**, computed from the CRS, so area-weighted metrics and area-averaged derived quantities are correct under any projection (lon/lat cells shrink as `cos(lat)`; stereographic cells vary). The global area-weighting requirement consumes this; full global aggregation is a global-phase concern.
- **Windowable** (invariant 3): the regional run is one window; global is many.
- **Polar treatment is an explicit policy**, not a default — grid / mask / extrapolation are real choices. Data voids (poles often have no local data to constrain the map) must yield uncertainty that relaxes toward the prior. **The polar void is a built-in calibration sanity check**: a method reporting small error in a data void has broken UQ. This property must be assertable by the calibration evaluator even when the Phase-1 regional tile is not itself polar.

### 5.6 Evaluator / metric interface

**Reference-agnostic by construction (invariant 9).** "Compare to withheld data" must not be the only quantifiable test. Evaluators fall into two families with different needs:

- **Reference-based** — score against an external truth: vs full truth (OSSE), vs withheld observations (OSE), vs independent in-situ (tide gauges, drifters). Requires a truth/reference provider.
- **Reference-free / intrinsic** — score the output against physical or geometric priors with no truth: ground-track-artifact signature, spectral-slope sanity (is the wavenumber spectrum the expected turbulence cascade or over-smoothed?), geostrophic-balance / physical plausibility, conservation.

**Interface.** An evaluator is `(result, context) → scores`. `context` is a bag that *may* contain a truth provider, withheld observations, observation/orbit geometry, physical constants. Each evaluator **declares which context elements it requires** (mirroring the method capability pattern). The evaluation layer is a **registry** that runs whichever evaluators are applicable given available context: truth-based evaluators fire in OSSE and skip in OSE; the ground-track metric fires whenever orbit geometry is present, in both modes. New tests slot in by registering, with no changes to the spine.

```python
class Evaluator(Protocol):
    required_context: frozenset[ContextKey]
    def evaluate(self, result: Product, context: EvalContext) -> dict[str, Score]: ...
```

**Phase-1 concrete evaluators (minimum):**
- **Accuracy** — vs truth (OSSE) and vs withheld observations (OSE).
- **Calibration** — predicted distribution vs actual held-out errors: coverage of ±σ, reduced χ², PIT / rank histograms, CRPS. Calibration is the harder, more important axis given the "rigorous uncertainty" goal, and it is the only axis fully validatable everywhere (between tracks) — which OSSE uniquely permits.
- The **ground-track-artifact** metric is well-motivated (it is the intrinsic dual of the unbiasedness check, targeting the track-correlated error that motivated correlated-error handling). Detect the *periodic* track signature specifically — e.g., spectral power at the track-spacing wavenumber — to avoid confounding with real fronts. It is necessary-not-sufficient: a strong pattern proves a problem; a clean map does not prove correctness.

**Forward consequence (type-level now, machinery deferred):** because no single metric is baked in, the tuning objective is **vector-valued (multi-objective)** with a *pluggable* scalarization / selection policy (weighted sum, lexicographic, Pareto). A method that nails RMSE while smearing the spectrum or carrying track artifacts should be penalized. Phase 1 commits the vector-valued objective *type*; the optimizer and scalarization policy are deferred.

### 5.7 Evaluation data and split discipline (withholding)

- **Three-way split.** train (into the grid) / validation (drives the eventual tuner) / locked test (touched once for the honest final number). The tuning objective and the test set must never be the same data.
- **Withholding unit respects autocorrelation.** Grouped/blocked holdout only — hold out a mission, crossovers, or space-time blocks. **Random point holdout is not offered** (it leaks through spatial autocorrelation).
- **Independence caveat, recorded honestly.** Holding out a satellite gives independent *sampling*, not independent *errors* — held-out and training data share tide models, mean sea surface, wet-troposphere corrections, and reference frames. The framework states this rather than implying a cleaner test than exists.
- **Mode-aware, transferable tuning.** OSSE has truth (validate uncertainty everywhere); OSE has only withheld along-track (validate at withheld locations). **Tune against withheld observations in both modes** — do not let the tuner see truth in OSSE — so the pipeline is identical and transferable; truth in OSSE is used only as an oracle diagnostic. (Tuner itself deferred; the split discipline is committed.)

### 5.8 Storage / I/O ports and provenance

**Ports-and-adapters (hexagonal), three boundaries:** data-source (along-track in), result-sink (grids + uncertainty out), execution-backend (§5.9). Decoupling these is application architecture, independent of where code runs.

- **Vendor-agnostic storage via `fsspec`** (local, S3, GCS, ODC THREDDS as adapters). **Phase 1 implements the local-filesystem adapter**, plus whatever read path is needed for ODC data (which may be remote/THREDDS).
- **Provenance is first-class on every product** (and is the carrier of invariant 8): method, resolved parameters (field-capable, not scalar), input-data manifest/hashes, code version, split definition, seed, and the uncertainty-provenance chain. Every product is reproducible from its provenance.

### 5.9 Executor port (compute)

- **Swappable Executor port.** **First and only Phase-1 adapter: `dask.distributed` + `LocalCluster`** on the single 64-CPU machine. The same code scales to multi-node / cloud / SkyPilot later by changing only the scheduler address — **no method-code changes**. Slurm and cloud backends are later adapters behind the same port. (Terraform/Kubernetes are not adopted; they operate at a different layer and are not Phase-1 concerns.)
- **Unit of work = one parametrized windowed solve:** `(tile/window, method, params, split, seed)` (invariant 5). Phase 1 submits a single unit; global submits many, with no re-granularization.
- **Process-level parallelism with an explicit `processes × threads` knob, per-run-configurable** (not global). It sets `OMP_NUM_THREADS` / `OPENBLAS_NUM_THREADS` / `MKL_NUM_THREADS` per worker to prevent BLAS/OpenMP thread oversubscription across the 64 cores. Dense-OI tiles may benefit from a few BLAS threads per worker; many-small-ensemble runs want more processes and fewer threads — hence per-run configurability rather than a single global setting.
- **Seeds derived deterministically per unit of work**, enabling reproducibility now and approximate cross-tile coherent ensembles later (§5.3).

---

## 6. Explicit non-goals (Phase 1 does NOT build these)

- The **tiling / stitching / blend layer** — blend operator, halo logic, scale-aware tile geometry. *(Phase 2.)*
- **Cloud / multi-node / SkyPilot / Slurm** execution adapters. *(Later; the port exists.)*
- The **autoresearch parameter-tuning loop**, any optimizer (grid/random/Bayesian/LLM), and the **multi-objective scalarization policy**. *(Later; the vector-valued objective type and the declarative `parameter_space` exist.)*
- **SWOT / 2-D wide-swath ingestion** and its correlated-error handling. *(Deferred; the data model and error model can absorb it.)*
- **Additional methods** beyond Method 0 and Method 1 (MIOST, DYMOST, BFN-QG / 4DVarQG, 4DVarNet, neural-SPDE). *(Later; the method interface + adapters accommodate them.)*
- A **custom OSSE observation simulator** *(use ODC NATL60 pre-simulated observations)*.
- **Spatially-varying parameter fields in practice** *(the provider seam exists; Phase 1 may use a constant provider)*.
- **Global area-weighted metric aggregation** *(the `cell_area` hook exists; global aggregation is a global-phase concern)*.
- **Scientifically meaningful derived-quantity bodies** — geostrophic velocity, EKE, transport, area-average — *(signatures committed, bodies stubbed; only the first-difference operator is implemented)*.
- **MDT / MSS / mean-surface handling** *(framework ingests SLA anomalies)*.
- **Recalibration machinery** *(provenance supports the recalibration chain; the recalibration step itself is later)*.

---

## 7. Phase-1 vertical slice (definition of done)

A single regional tile, wired end-to-end through the full stack, in **both OSSE and OSE** modes:

1. **Data-source adapter** reads ODC NATL60 (OSSE, with truth field) and an OSE real-data path, yielding windowed observations with per-observation error models, lazily.
2. **Grid spec**: a regional lon/lat tile, projection-aware, exposing `cell_area`.
3. **Windowed solve** dispatched via the `dask` `LocalCluster` Executor, unit of work `(window, method, params, split, seed)`, with the BLAS/OpenMP thread knob honored.
4. **Methods**: Method 1 (GP/OI) emitting a Gaussian `PredictiveDistribution` with native covariance + samples; Method 0 (trivial) emitting a point estimate, lifted by the perturb-and-ensemble adapter to a (degenerate) distribution and flagged synthesized in provenance.
5. **Derived-quantity closure proven** by the first-difference operator applied to a distribution, returning a distribution, propagated via native covariance.
6. **Evaluator registry** runs accuracy (vs truth in OSSE, vs withheld observations in OSE) + calibration (coverage, reduced χ², PIT/CRPS), with the three-way split and blocked withholding in force.
7. **Result-sink** writes the product in the persisted representation (sufficient statistics + generator) with the full provenance chain, via the local `fsspec` adapter.

**Correctness oracle:** reproduce ODC leaderboard-style numbers for the OI baseline on the NATL60 challenge, confirming the framework is correct rather than merely runnable.

**Calibration sanity check:** the polar-void property (uncertainty must relax toward the prior where there is no data; small reported error in a void = broken UQ) is expressible by the calibration evaluator even though the regional tile is not polar.

---

## 8. Decision log

All architectural forks raised during scoping are closed: OSSE+OSE both (on ODC data); SWOT deferred but data-model-absorbable; global via framework-level tiling, regional-first as tile-zero; single 64-CPU box with a `dask` `LocalCluster` Executor behind a port; predictive-distribution object with marginal variance + on-demand covariance + seeded coherent sampling; CRS-aware grid; reference-agnostic evaluator registry with vector-valued tuning objective; derived-quantity seam included with real closure (one first-difference operator) and stubbed meaningful operators. **No open Phase-1 architectural questions remain.**
