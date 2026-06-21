# Regatta Phase-1 — Implementation Architecture & Plan

**Date:** 2026-06-21
**Status:** Approved (brainstorm). Basis for the implementation plan.
**Source of truth for *what*:** `phase1_scope_spec.md`. This document settles *how*.
**Governing discipline:** decide the abstractions now (global-ready); defer the
machinery behind them. Implement only the minimum needed to *prove* each seam.

This doc records architecture decisions reached in a brainstorm directed at
*how to build* the settled Phase-1 spec. On any conflict, `phase1_scope_spec.md`
governs. Section numbers below referencing `§N` point at that spec.

---

## 1. Two pivotal realization decisions

### Decision A — Method 1 (GP/OI) is a hand-rolled dense GP behind seams

Method 1 must *natively* expose queryable covariance **and** coherent whole-field
samples (invariant 4), not a marginal error-variance map. `pyinterp` objective
analysis returns marginal variance only; GPSat is a local-expert (method-internal
tiling) framework that would leak a scaling trick into the spine (spec §1). We
therefore hand-roll a dense Gaussian-process / kriging posterior, built so dense
linear algebra is the Phase-1 *implementation*, not a baked-in assumption:

- One cached Cholesky `L` of `K_dd + R`, reused everywhere.
- `cov(A,B) = K_AB − Vᵀ_A V_B` with `V_X = L⁻¹ K_dX` (triangular solves, no explicit
  inverse) — truly on-demand for any `A,B`; never materialize grid×grid.
- `marginal_var(A) = diag(K_AA) − colwise‖V_A‖²`.
- Sampler: `μ_S + chol(K_SS − Vᵀ_S V_S + jitter)·z`, `z∼N(0,I)`, deterministic seed;
  whole-field ⇒ `S` = tile grid.
- `R` is a **matrix/operator** (diagonal for nadir now; structured-ready for swath),
  honoring the first-class observation-error-model decision (§5.1).
- **The covariance is space-time** (see §1.3): a spatial length scale **and** a temporal
  correlation scale, both resolved through the `ParameterProvider` (the temporal scale
  joins the param seam too). `K_dd`, `K_dg`, etc. evaluate the space-time kernel over
  `(space, time)` coordinates, so kernel variance / spatial length / temporal scale all
  go through the provider (invariant 6).
- The **kernel family is pinned** to a stationary **Matérn-3/2** (variance + spatial
  length + temporal scale; Gaussian/squared-exponential as a config option), kept behind
  a small `methods/kernel.py::Kernel` interface so the operator never hard-codes the form
  — that is what lets the kernel go nonstationary / spatially-varying later without
  touching `GPCovarianceOperator`.
- The linear solve sits behind an internal `LinearSolver` seam (dense Cholesky now;
  low-rank / iterative later) **within the kernel formulation**.

### Decision B — real data adapter + scoped oracle + committed fixtures

The three are complementary, not exclusive (network is available):

- **Real `DataSource`** against ODC THREDDS, on-disk cache `./data/cache/`. dodsC
  OPeNDAP subsetting where exposed (OSE along-track / grid); whole-file fetch where
  not (NATL60 OSSE tar.gz). Cache only what's needed; access lazily/chunked.
- **Scoped footprint:** OSSE nadir obs (~285 MB) grabbed whole. The 11 GB *hourly*
  reference is **never** pulled — use a **daily** NATL60-CJM165 reference clipped to
  the official **42-day window 2012-10-22 → 2012-12-02** (21 days of pre-window
  spin-up obs available). Net footprint a few hundred MB.
- **Committed tiny clipped-NetCDF fixtures** (`tests/fixtures/`, a few MB) → fast,
  deterministic, network-free CI for the adapter and the full vertical slice.
- **Correctness oracle** = a separate, opt-in test
  (`@pytest.mark.skipif(no_data or no_network)`) reproducing ODC OI **sanity-level**
  RMSE parity on the cached 42-day window (the challenge has no observation error, so
  `R` ≈ a nugget). Nightly / dev box, not fast CI. Exact leaderboard-parameter
  replication is a documented, runnable-once target, out of routine CI.
- **OSE evaluation** uses the challenge's deliberately-withheld **CryoSat-2**
  along-track as the independent signal — which also exercises our withholding /
  evaluator design and keeps numbers literature-aligned.
- **Oracle pass tolerance (concrete):** our OI lands **within 10% of the ODC OI
  leaderboard RMSE** on the 42-day window (and does not exceed it by more than that).
  This pairs with the pinned kernel family/params (Decision A); a looser bar (≤25%)
  applies to the tiny-fixture smoke run, whose purpose is path-correctness, not parity.

### 1.3 Space-time structure (load-bearing)

SSH OI is fundamentally **space-time**: the deliverable is a *series of grids*, and the
ODC OI baseline (the oracle target) maps each output time using a space-time covariance
with a temporal correlation scale. The architecture reflects this explicitly:

- **Space-time GP covariance** — spatial length scale × temporal correlation scale, both
  via the `ParameterProvider` (Decision A). Without the temporal term the OI cannot match
  the baseline.
- **The unit-of-work window is space-time** — a spatial tile × a *temporal window* of
  observations around the target output time(s). This is why the 42-day eval window ships
  21 days of pre-window spin-up obs: early output times need temporal neighbors. The
  temporal window also **bounds `N_obs` per solve**, keeping the dense Cholesky tractable.
- **Time is carried on the output, not on `GridSpec`** — `GridSpec` stays purely spatial
  (`cell_area` / projection logic is inherently 2-D). The `Product` carries the output
  **time(s) as a series of per-time persisted fields**; `K_dd / K_dg / …` evaluate the
  space-time kernel over `(space, time)` coordinates. One solve can produce several output
  times sharing the same factored `K_dd + R`.

---

## 2. Hexagonal package layout

Three concentric rings enforced by package boundaries. `core` imports nothing from
methods/adapters. Methods/distributions/eval are plugin rings. Adapters are the
outer I/O + compute ring. `application` wires them. No method detail reaches `core`
or `application`; no framework concern leaks into a method.

```
src/regatta/
  __init__.py
  __main__.py                 # python -m regatta <config> -> runs the vertical slice

  core/                       # THE SPINE: protocols + value objects only
    types.py                  # Field, Seed, CovBlock, ScalarOrField, CovFidelity
    grid.py                   # GridSpec (CRS-aware pyproj/CF), cell_area, window()
    observations.py           # ObsWindow, ObservationErrorModel (R as operator), Observation
    distribution.py           # PredictiveDistribution Protocol + CovarianceOperator Protocol
    parameters.py             # ParameterProvider Protocol, ScalarOrField, ResolvedParams, ParameterSpace
    method.py                 # Method Protocol, UncertaintyCapability enum
    derived.py                # DerivedQuantity Protocol, Linearity, propagation dispatch
    evaluation.py             # Evaluator Protocol, EvalContext, ContextKey, Registry, Score, Objective
    provenance.py             # UncertaintyProvenance (typed chain), UncertaintyTransform, ProductProvenance
    ports.py                  # DataSource, ResultSink, Executor Protocols
    seeding.py                # derive_seed(method, params, window, member_index) -> Seed
    product.py                # Product bundle (base + derived + eval-point predictions + provenance)

  distributions/             # concrete PredictiveDistribution impls + lifting adapters
    gaussian.py               # GaussianPredictiveDistribution(mean, cov: CovarianceOperator)
    ensemble.py               # EnsemblePredictiveDistribution (M sample maps; canonical compute-time rep)
    persisted.py              # PersistedDistribution (mean + marginal-var + low-rank B + d + seed + spec)
    adapters.py               # perturb_and_ensemble (POINT->dist), diagonal_gaussian (MARGINAL_VARIANCE->dist)

  methods/                   # the ONLY place method math lives
    registry.py
    trivial.py                # Method 0 (POINT): naive interpolation
    oi.py                     # Method 1 (SAMPLES+COVARIANCE): dense GP/OI; builds GPCovarianceOperator
    kernel.py                 # Kernel interface + space-time Matern-3/2 (variance, spatial len, temporal scale)
    solver.py                 # LinearSolver seam (DenseCholeskySolver now; sparse/iterative later)

  derived/                   # concrete derived-quantity operators (parallel to eval/)
    firstdifference.py        # REAL, CRS-aware (exercises exact covariance path)
    velocity.py eke.py transport.py area_average.py   # STUBS: committed signatures, no bodies

  adapters/
    odc/
      download.py             # ODCCache: THREDDS fetch + dodsC subset + ./data/cache
      natl60.py               # OSSE: nadir obs + daily reference; TruthProvider
      ose.py                  # OSE: real along-track inputs + withheld CryoSat-2
    storage_fsspec.py         # ResultSink: local fsspec, persisted bundle + provenance
    executor_dask.py          # Executor: dask LocalCluster + processes×threads BLAS/OpenMP knob

  application/
    config.py                 # run config dataclasses (grid, window, method, params, executor, split)
    splits.py                 # three-way split + blocked/grouped withholding (no random point holdout)
    solve.py                  # unit of work: (window, method, params, split, seed) -> Product
    pipeline.py               # source -> executor.solve -> evaluate(registry) -> sink

  eval/
    accuracy.py               # vs truth (OSSE) / vs withheld obs (OSE)
    calibration.py            # coverage(±σ), reduced χ², PIT, CRPS, polar-void assertion
    groundtrack.py            # intrinsic track-artifact metric (reference-free)

tests/{unit,integration,fixtures}/
```

---

## 3. The abstraction spine (`core`)

- **`GridSpec` (grid.py)** — wraps a `pyproj.CRS` + axis definition. Projection
  awareness lives in the type, never in branching. `cell_area` is a computed property:
  true spherical area on lon/lat (`cos(lat)` metric), projected area on stereographic.
  `window()` returns a sub-grid of the same type, so "regional = one window" and
  "global = many windows" are the same code path. Instantiable lon/lat (default) or
  polar-stereographic. **`GridSpec` is purely spatial (2-D)** — time is carried on the
  `Product`'s output series, not here (§1.3). (invariants 1, 3; spec §5.5)

- **Space-time window (observations.py)** — the unit-of-work window is a spatial tile ×
  a temporal observation window around the target output time(s); `ObsWindow` carries the
  `(lon, lat, time)` coordinates the space-time kernel is evaluated over. The temporal
  window bounds `N_obs` per solve. (§1.3)

- **`PredictiveDistribution` (distribution.py)** — `marginal_variance() · covariance(A,B)
  · sample(m, seed) · regrid(target)`. Three concrete impls (ring `distributions/`).
  `covariance` is queried on demand and **must not** materialize a dense grid×grid
  matrix. (invariant 4; spec §5.3)

- **`CovarianceOperator` (distribution.py)** — the seam separating the covariance
  *representation* from the distribution: `cov(A,B) · marginal_var(A) ·
  posterior_sample(S, seed)`, plus a declared **`fidelity: CovFidelity ∈
  {EXACT, LOW_RANK, SAMPLE}`**. This is the abstraction both `distributions/` and
  `methods/` depend on; it carries the kernel→precision *formulation* jump (a future
  SPDE/GMRF operator is a different `CovarianceOperator`, not a `LinearSolver` swap).
  No implementation in `core`.

- **`UncertaintyProvenance` (provenance.py)** — ordered `UncertaintyTransform` chain;
  head records true `native_capability`; each transform carries `kind` (INPUT_PERTURBATION
  / DIAGONAL_INFLATION / POSTERIOR_RECALIBRATED / …) and a `known_bias` hint (e.g.
  perturb-and-ensemble = `UNDER_DISPERSED_IN_VOIDS`). Synthesized is never reportable as
  native. (invariant 8; spec §5.3)

- **`Method` + `UncertaintyCapability` (method.py)** — `native_capability` +
  `solve(obs, grid, params) -> PredictiveDistribution` + `parameter_space()`. The
  framework reads the capability to decide native-consume vs adapter-lift. (spec §5.2)

- **`ParameterProvider` (parameters.py)** — `resolve(name, grid) -> ScalarOrField`.
  Phase-1 `ConstantProvider` returns scalars, but the return type is already
  scalar-*or*-field and provenance records the resolved field. (invariant 6)

- **Ports (ports.py)** — `DataSource.window(...) -> ObsWindow` (lazy),
  `ResultSink.write(product)`, `Executor.submit(uow) -> Product`. `application` depends
  only on these. (spec §5.8, §5.9)

- **`seeding.py`** — `derive_seed(method, params, window, member_index)` via stable
  hash: reproducibility now; the hook for approximate cross-tile-coherent ensembles
  later. (spec §5.9)

- **`product.py`** — the **`Product` bundle** (see §5).

---

## 4. Methods & distribution representations

**Method 1 — `methods/oi.py` (SAMPLES + COVARIANCE).** `solve()` resolves kernel params
(spatial length, temporal scale, variance) via the provider, builds a space-time
`methods/kernel.py::Kernel` (Matérn-3/2), assembles `R` from per-observation error
models, has `methods/solver.py::DenseCholeskySolver` factor `K_dd + R = L Lᵀ` **once**
over the space-time observation set, and builds a `GPCovarianceOperator` (caches `L`;
`cov`/`marginal_var`/`posterior_sample` per Decision A; `fidelity = EXACT`). Kernel
blocks `K_dd / K_dg / K_gg` are evaluated over `(space, time)` coordinates, so **one
factored `K_dd + R` serves all output times** in the window. Returns
`GaussianPredictiveDistribution(mean=μ, cov=GPCovarianceOperator)` per output time.
`regrid(target)` = evaluate the operator at target points (operator-on-covariance;
invariant 7). The GP-specific `K_AB − Vᵀ_A V_B` math lives here, not in `distributions/`.

**Method 0 — `methods/trivial.py` (POINT).** Naive interpolation (Gaussian-weighted /
inverse-distance, scipy-only), returns a bare field. Lifted by
`distributions/adapters.py::perturb_and_ensemble`: perturb obs by their `R` model,
re-interpolate `M` times with per-member derived seeds → `EnsemblePredictiveDistribution`
(`fidelity = SAMPLE`). Provenance head = `POINT`, transform = `INPUT_PERTURBATION`,
`known_bias = UNDER_DISPERSED_IN_VOIDS`.

**`GaussianPredictiveDistribution`** is method-agnostic: `(mean: Field, cov:
CovarianceOperator)`; all four `PredictiveDistribution` methods delegate to the injected
operator + mean. Any Gaussian-posterior method reuses it.

**`EnsemblePredictiveDistribution`** — the M-sample-map canonical compute-time rep;
covariance is sample covariance (carrying the catastrophic-cancellation caveat for
linear functionals — `fidelity = SAMPLE`).

**`PersistedDistribution`** — storage form; see §5.

---

## 5. The exact/persisted boundary and the `Product` bundle

**Unifying rule.** The worker extracts *everything that needs the EXACT operator* —
base reduction, declared derived quantities, **and eval-point predictions** — before
discarding the operator. Nothing exact is left to client-side reconstruction from the
LOW_RANK rep. The unit of work returns the Persisted representation, **never** a live
`GaussianPredictiveDistribution` carrying the `N_obs×N_obs` `L` (dask must not ship
that back).

**Base reduction (on worker).** Reduce the posterior to sufficient statistics:
- `mean` field; `marginal_variance` field (**exact**, from the operator);
- a **low-rank factor `B` (N_grid×r)** from a **matrix-free, seeded randomized SVD** of
  the grid posterior covariance `P` (forming `P @ Ω` on the fly via `K_gg` and the
  resident `V_g` machinery — never materializing `P`); seeded from `derive_seed`;
- a **diagonal residual `d = clip(diag(P) − rowsum(B²), 0, None)`** (clipped because the
  randomized factor is approximate and may overshoot a diagonal entry; `d ≥ 0` so
  `BBᵀ + diag(d)` is PSD and marginal variance is exact);
- `seed`, `sampler_spec`, configurable **rank `r`**, and a **captured-energy
  diagnostic** (fraction of `trace(P)` captured by `BBᵀ`) so LOW_RANK quality is
  monitorable per product.

`PersistedDistribution` regenerates samples as `μ + B z_r + √d ⊙ z_full` (deterministic)
and answers `covariance` from `BBᵀ + diag(d)`, declaring `fidelity = LOW_RANK` (the
honest tag for dropped fine-scale cross-correlation).

**Derived quantities (on worker).** Declared derived quantities are applied against the
live EXACT operator and returned as their own Persisted products (§6).

**Eval-point predictions (on worker).** The gridded Persisted rep cannot answer the
predictive distribution at off-grid along-track locations (withheld CryoSat-2 in OSE;
truth/obs points generally), and interpolating its marginal-variance field to obs points
would both violate invariant 7 and be statistically wrong. So the worker, while the
operator is live, also emits predictions at the evaluation/withheld locations: `mean +
marginal variance` (and samples only for non-Gaussian reps). Then client-side:
calibration runs on those exact eval-point predictives (coverage/χ²/CRPS/PIT closed-form
from `(mean, var)` for the Gaussian case, sample-based for Ensemble); accuracy uses the
exact eval-point mean rather than interpolating the gridded mean.

**`Product` bundle (core/product.py).** An explicit bundle, **carrying the output as a
series of per-time persisted fields** (§1.3): for each output time, a base SSHA Persisted
product + derived Persisted products + eval-point predictions, with provenance linking the
derived and eval products to the base (route + `CovFidelity` stamped on each) and recording
the output time(s). `ResultSink` writes the whole bundle (the series-of-grids deliverable).

---

## 6. Derived-quantity seam & dispatch quality

`core/derived.py` holds the `DerivedQuantity` Protocol, `Linearity`, and the **dispatch**
— a function of **linearity × representation × `CovFidelity`**:

- **linear + EXACT** → covariance path, exact (cancellation-safe);
- **linear + LOW_RANK / SAMPLE** → covariance path, result provenance stamped
  `covariance_fidelity = LOW_RANK|SAMPLE`;
- **nonlinear** → sample path.

Each application appends a `DerivedTransform` (route + fidelity) to provenance.

**Real operator:** `derived/firstdifference.py` — CRS-aware (uses the grid metric, never
index-space), applied **on the worker against the live EXACT `GPCovarianceOperator`**, its
result returned as a Persisted product in the bundle. The same operator applied
client-side on a Persisted rep is permitted but stamps `LOW_RANK`; on an Ensemble it stamps
`SAMPLE`. This makes "exact covariance avoids the Monte-Carlo blowup" a demonstrated,
provenance-visible property. **Stubs** (`velocity.py` — CRS metric + Coriolis; `eke.py` —
the nonlinear sample-path exemplar; `transport.py`; `area_average.py`) carry committed
signatures, no bodies. (spec §5.4)

**On-worker rationale (recorded):** shipping the material for client-side exact neighbor
covariance (`V_g`, `N_obs×N_grid`) is as heavy as or heavier than `L`; on-worker also
generalizes to non-local derived quantities (transport, area-average) that a
banded-cross-covariance shortcut could not cover.

---

## 7. Executor port

`adapters/executor_dask.py`: `dask.distributed` `LocalCluster`. `ExecutorConfig(n_processes,
threads_per_process)` sets `OMP_NUM_THREADS / OPENBLAS_NUM_THREADS / MKL_NUM_THREADS` per
worker via the Nanny child-process `env` (before BLAS loads), per-run-configurable (not
global). `submit(uow)` runs `application/solve.py::solve_unit(uow) -> Product`, `uow =
(window, method, params, split, seed)`. Phase 1 submits one unit; the global loop submits
many with no re-granularization. Seeds from `derive_seed`. Scaling to multi-node/cloud later
changes only the scheduler address — no method-code changes. (invariant 5; spec §5.9)

---

## 8. Data access, splits, fixtures

`adapters/odc/download.py::ODCCache` — `fetch_file(url)` (requests + `tenacity` retry +
`tqdm`) for tar.gz; `open_dodsC(url).sel(...)` for lazy OPeNDAP subsetting; cache `./data/cache/`
(gitignored). `natl60.py` (OSSE: ~285 MB nadir obs whole; daily CJM165 reference clipped to
2012-10-22→2012-12-02; exposes `TruthProvider`). `ose.py` (OSE: real along-track inputs;
withheld CryoSat-2 surfaced as independent eval signal). `ObsWindow` is dask-chunked xarray —
lazy throughout (invariant 2).

`application/splits.py`: three-way **train / validation / locked-test** via **blocked/grouped**
holdout (by mission / crossover / space-time block). **No random point holdout** (it leaks
through spatial autocorrelation). Tune against withheld observations in both modes; truth in
OSSE is an oracle diagnostic only. Independence caveat recorded honestly. (spec §5.7)

Committed tiny clipped-NetCDF fixtures under `tests/fixtures/` drive offline CI for the adapter
and the full slice.

---

## 9. Evaluator registry

`core/evaluation.py` registry runs evaluators whose `required_context` is satisfied by the
`EvalContext` keys present (mirrors the method-capability pattern):

- `eval/accuracy.py` — requires `TRUTH` (OSSE) **or** `WITHHELD_OBS` (OSE); ODC metric
  definitions for literature comparability; uses **exact eval-point mean**.
- `eval/calibration.py` — coverage(±σ), reduced χ², PIT / rank histogram, CRPS on **exact
  eval-point predictives**; plus the **polar-void assertion** (synthetic void ⇒ variance must
  relax toward prior; small error in a void = fail), assertable on the non-polar tile.
- `eval/groundtrack.py` — intrinsic, reference-free; requires `ORBIT_GEOMETRY`; spectral power
  at the **track-spacing wavenumber**; fires in both modes.

Truth-based evaluators fire in OSSE, skip in OSE — proving reference-agnosticism (invariant 9).
The tuning objective is the **vector-valued `Objective` type** (no scalarization baked in);
optimizer deferred. (spec §5.6)

---

## 10. Storage & provenance

`adapters/storage_fsspec.py` writes the Persisted `Product` bundle (NetCDF/Zarr via local
fsspec) with `ProductProvenance` (method, **resolved parameter field** not scalar, input
manifest + hashes, git code version, split definition, seed, and the uncertainty typed-chain),
plus the derived/eval sub-products linked to the base. Every product reproducible from its
provenance. (invariant 8; spec §5.8)

---

## 11. Build order (seams first)

Pure/cheap-to-test seams first; data + dask last; vertical slice as the integration target.

1. `core/types`, `GridSpec` (+ `cell_area`), `seeding` — pure.
2. `core` Protocols (distribution, `CovarianceOperator`, method, parameters, ports,
   provenance, evaluation, derived, product).
3. `distributions/` — `Ensemble`, `Gaussian(mean, cov)`, `Persisted`, adapters — tested
   against a **toy analytic `CovarianceOperator`** (no GP yet).
4. `methods/solver` + `methods/oi` (`GPCovarianceOperator`) — validated against a **1-D
   analytic GP posterior** (closed form).
5. `methods/trivial` + `perturb_and_ensemble`.
6. `derived/` dispatch + `firstdifference` (exact-vs-sample cancellation test); stubs.
7. `executor_dask` (BLAS knob; **Persisted-return**; eval-point + derived extraction
   on worker).
8. `adapters/odc` + fixtures + `splits`.
9. `eval/` (accuracy, calibration incl. polar-void, groundtrack).
10. `application/` (`solve`, `pipeline`, `config`, `__main__`) — **vertical slice OSSE then OSE**.
11. **Oracle** test (opt-in, skipif no data/network).

---

## 12. Test strategy

Per the `test-design` skill + red/green TDD. Each test states the behavior under test and a
concrete bug that would make it fail. Anchor tests:

| Behavior under test | Concrete bug it catches |
|---|---|
| `cell_area` shrinks as `cos(lat)`; varies on stereographic | flat-area assumption |
| `cov(A,B)` symmetric, PSD, matches dense reference | dropped `Vᵀ` term / wrong solve |
| 1-D GP posterior matches closed form | solve / sign error |
| space-time kernel: obs at the same point but distant times are weakly correlated; one factored `K_dd+R` serves multiple output times | spatial-only kernel; time dropped |
| oracle: OI RMSE within 10% of ODC OI baseline on cached window | wrong kernel/params; broken solve |
| sampler determinism; sample-cov → operator-cov as M→∞ | unseeded / biased draws |
| first-difference exact-path error ≪ sample-path error on `Var(a−b)` | index-space diff / sample-path on Gaussian |
| perturb-ensemble void under-dispersion recorded, not native | synthesized-as-native |
| Persisted round-trip reproduces marginal variance exactly | dropped diagonal residual |
| captured-energy diagnostic present and in [0,1] | unmonitorable LOW_RANK quality |
| polar-void calibration fails a small-error-in-void map | broken UQ |
| registry truth-evaluator fires OSSE / skips OSE | reference-always-assumed |
| executor returns Persisted, not live `L` | heavy-state shipping |
| eval-point predictive from exact operator, not interpolated variance | invariant-7 violation |

Vertical slice (fixtures, OSSE + OSE) and the oracle (cached, opt-in) are integration tests.

---

## 13. Vertical-slice wiring (definition of done, spec §7)

`application/pipeline.py`:

```
config
  → DataSource.window                      # lazy, windowed obs + per-obs error model
  → splits (train / validation / locked-test, blocked)
  → Executor.submit(uow = (window, method, params, split, seed))
       [worker, operator live:
          solve
          → base reduction (mean, marginal var, low-rank B+d, captured energy)
          → declared derived quantities (EXACT first-difference)
          → eval-point predictions (withheld / truth locations)
          → discard operator]
  → Product bundle (Persisted) returned
  → client reconstructs PersistedDistribution view
  → evaluator registry (accuracy + calibration + groundtrack)
  → ResultSink.write(bundle + provenance)
```

The **OSE run is the identical path** — only the `DataSource` and the `EvalContext` keys differ
(truth absent, withheld CryoSat-2 present), no spine change — demonstrating the reference-agnostic
registry and mode transferability in one stroke.

**Correctness oracle:** reproduce ODC OI sanity-level RMSE on the cached NATL60 window (opt-in).
**Calibration sanity check:** the polar-void property is assertable by the calibration evaluator
even though the regional tile is not polar.

---

## 14. Non-goals (unchanged from spec §6)

Tiling/stitching/blend; cloud/multi-node/SkyPilot/Slurm adapters; the tuning loop / optimizer /
scalarization policy; SWOT/2-D swath ingestion; methods beyond Method 0/1; a custom OSSE
simulator; spatially-varying parameter fields in practice; global area-weighted aggregation;
derived-quantity bodies beyond first-difference; MDT/MSS/mean-surface handling; recalibration
machinery. The interfaces accommodate these without implementing them. If any appears necessary
to make Phase 1 work — stop and ask.
