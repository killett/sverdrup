You are building **Phase 1** of a Python framework that ingests a heterogeneous set of nadir satellite altimeters (reference-orbit missions such as Sentinel-6; high-latitude drifting-orbit missions such as CryoSat-2) and produces a global regular-gridded sea-surface-height-anomaly (SSHA) product with a rigorously estimated per-gridpoint uncertainty, plus a layer for rigorously comparing methods and their uncertainties.

**The complete, settled specification is in `phase1_scope_spec.md` in this repo. Read it in full before doing anything else. It is the source of truth. This prompt foregrounds the parts that must not be missed; on any conflict, the spec governs, and if you believe the spec itself is wrong, raise it as a question rather than diverging.**

The requirements are already settled — they were worked out in detail before you were invoked. **Do not re-gather requirements or re-open scope.** Use the **brainstorming skill (from superpowers)** to turn the settled spec into a concrete *implementation plan and architecture* — i.e., direct the brainstorming at *how to build this*, not *what to build*.

## Workflow — follow in order

1. **Read `phase1_scope_spec.md` in full.** If it is not present in the repo, stop and ask for it; do not proceed from this prompt alone.
2. **Brainstorm and produce an implementation plan. Write no implementation code in this step.** The plan must cover: the package/module layout; the concrete realization of each interface in the spec (§5 — the `Protocol`/`dataclass` sketches are illustrative contracts, not prescribed internals); the build order (which seams first); the test strategy; exactly how the Phase-1 vertical slice (spec §7) wires together; and the ODC data-access plan. The plan must respect "decide the abstractions now, defer the implementations" — make the seams concrete, do not plan the deferred machinery (spec §6).
3. **Present the plan and STOP. Await explicit approval before implementing.** Do not begin implementation on your own initiative.
4. **On approval, implement incrementally and test-first**, in small reviewable commits, with the vertical slice (§7) as the integration target you build toward. Keep the "real vs stubbed" boundary exact (§5.4, §6).
5. **Validate against the definition of done** (§7), including the correctness oracle and the calibration sanity check.

## Non-negotiable invariants (spec §3 — do not optimize away for regional convenience)

1. **Projection-aware grid** — no flat regular lon/lat assumption.
2. **Lazy/chunked observation access** — no code path assumes all observations fit in memory.
3. **Windowable solve** — the regional run is one window; global is many.
4. **Rich uncertainty representation** — uncertainty is a first-class *predictive distribution over the SSHA field*, never a grid-plus-error-bar; covariance and coherent samples are available, not just marginal variance.
5. **Execution behind a port** — compute runs behind a swappable Executor port whose unit of work is a single windowed solve `(tile/window, method, params, split, seed)`.
6. **Field-capable parameters** — parameters are read through a provider that can return scalars *or spatial fields*; provenance records the field used, never a scalar shortcut.
7. **Distribution-correct regridding** — regrid by regridding samples or applying the regridding operator to the covariance; never by interpolating a marginal-variance map.
8. **Typed-chain provenance** — uncertainty provenance is a typed chain (`native → synthesized[type] → recalibrated[…]`), not a boolean; synthesized uncertainty is never presented as native.
9. **Reference-agnostic evaluation** — the evaluator interface does not assume a reference (withheld data) exists; intrinsic, reference-free metrics are first-class; the tuning-objective *type* is vector-valued (multi-objective), never a baked-in scalar.
10. **Closed derived quantities** — derived quantities are `Distribution → Distribution` and propagate uncertainty using the grid's CRS metric.

Two refinements that are decisions, not options (spec §5.3): **prefer native covariance for linear functionals, use samples for nonlinear ones** (sample-derived covariance suffers catastrophic cancellation for differences/gradients); and the **perturb-and-ensemble adapter under-disperses in data voids** — record that known bias in provenance, and do not present its spread as a full posterior.

## Out of scope — do NOT build (spec §6)

The tiling/stitching/blend layer; cloud/multi-node/SkyPilot/Slurm execution adapters; the autoresearch tuning loop, any optimizer, or the scalarization policy; SWOT/2-D swath ingestion; any method beyond the two below; a custom OSSE observation simulator (use ODC NATL60 pre-simulated observations); spatially-varying parameter *fields* in practice (the provider seam exists; a constant provider is fine); global area-weighted metric aggregation (the `cell_area` hook exists); the scientifically meaningful derived-quantity *bodies*; MDT/MSS/mean-surface handling; recalibration machinery.

**If any of these appears necessary to make Phase 1 work, stop and ask — do not build it.** The interfaces and seams must *accommodate* these without being implemented.

## Settled decisions — do NOT silently change (spec §8)

If, during implementation, a settled decision appears wrong, **surface it as a question and pause; do not silently re-architect.**

## The two starting methods (spec §5.2)

- **Method 0 — trivial baseline (`POINT`)**: a point estimate with no uncertainty (e.g., the ODC naive interpolation). Forces the interface to handle UQ-absent. Lifted to the distribution interface by the perturb-and-ensemble adapter, flagged synthesized in provenance.
- **Method 1 — GP/OI (`SAMPLES` and `COVARIANCE`)**: the reference baseline (objective analysis ≡ optimal interpolation ≡ kriging ≡ GP regression). Emits a Gaussian posterior exposing native closed-form covariance *and* whole-field sampling, so one implementation exercises two representations. Mature public Python exists (pyinterp; GPSat; ODC `baseline_oi`) — reuse/adapt rather than reinvent where sensible, behind our own interface.

## Derived-quantity seam (spec §5.4) — exact real-vs-stub boundary

Commit the type closure (`Distribution → Distribution`) and the propagation dispatch (linearity selects covariance-path vs sample-path; operators are CRS-aware). **Implement exactly one operator end-to-end: a spatial first-difference** (the cancellation-sensitive linear case; the building block of geostrophic velocity; proves the covariance propagation avoids the Monte-Carlo blowup). **Stub, with committed signatures and no bodies:** full geostrophic velocity (CRS metric + Coriolis), EKE, transport, area-average.

## Engineering standards

- **Python (modern):** type hints throughout; `typing.Protocol`/ABCs for interfaces; `dataclasses` for value objects.
- **Ports-and-adapters (hexagonal)** for the three boundaries — data-source, result-sink, executor. Phase 1 implements: local-filesystem storage via `fsspec` (plus the read path for ODC data, which may be remote/THREDDS); `dask.distributed` + `LocalCluster` as the sole Executor adapter, written so scaling to multi-node/cloud later changes only the scheduler address, not method code.
- **DRY, single-responsibility, small modules.** No method-specific detail leaks into the framework spine; no framework-level concern leaks into a method.
- **Rigorous TDD.** For each test, state the behavior under test and a concrete bug that would make it fail. Use real assertions; do not mirror the implementation; avoid over-mocking; test the invariants and the closure, not just happy paths. The vertical slice and the correctness oracle are integration tests.
- **Determinism and reproducibility.** Seeds are derived deterministically per unit of work `(method, params, tile/window, member_index)`. Every product is reproducible from its provenance.
- **BLAS/OpenMP discipline.** Expose a per-run `processes × threads` knob in the executor config that sets `OMP_NUM_THREADS` / `OPENBLAS_NUM_THREADS` / `MKL_NUM_THREADS` per worker, to prevent thread oversubscription across the 64 cores. Process-level parallelism is the unit; the knob is per-run-configurable, not global.
- **Performance honesty (invariants).** Never materialize a dense global grid×grid covariance — covariance is queried on demand. Observations are accessed lazily/chunked. The persisted uncertainty representation is sufficient statistics + generator (mean, marginal variance, low-rank covariance factor, seed, sampler spec), regenerating full samples on demand.
- **Grid:** CRS-aware via `pyproj`/CF conventions, defaulting to lon/lat for the regional tile, instantiable as polar-stereographic; expose true spherical `cell_area` as a first-class property.

## Definition of done (spec §7)

A single regional tile wired end-to-end through the full stack, in **both OSSE and OSE** modes:

1. Data-source adapter reads ODC NATL60 (OSSE, with truth field) and an OSE real-data path, yielding windowed observations with per-observation error models, lazily.
2. Grid spec: a regional lon/lat tile, projection-aware, exposing `cell_area`.
3. Windowed solve dispatched via the `dask` `LocalCluster` Executor, unit of work `(window, method, params, split, seed)`, BLAS/OpenMP knob honored.
4. Method 1 (GP/OI) emits a Gaussian `PredictiveDistribution` with native covariance + samples; Method 0 (trivial) emits a point estimate lifted by the perturb-and-ensemble adapter to a degenerate distribution, flagged synthesized.
5. Derived-quantity closure proven by the first-difference operator (distribution in → distribution out, propagated via native covariance).
6. Evaluator registry runs accuracy (vs truth in OSSE; vs withheld observations in OSE) + calibration (coverage of ±σ, reduced χ², PIT/CRPS), with the three-way split (train/validation/locked-test) and blocked/grouped withholding in force (no random point holdout).
7. Result-sink writes the product in the persisted representation with the full provenance chain, via the local `fsspec` adapter.

**Correctness oracle:** reproduce ODC leaderboard-style numbers for the OI baseline on the NATL60 challenge, confirming the framework is correct rather than merely runnable.

**Calibration sanity check:** the polar-void property — uncertainty must relax toward the prior where there is no data; small reported error in a void indicates broken UQ — is assertable by the calibration evaluator even though the regional tile is not polar.

## Data and environment notes

- **Spec location:** `./phase1_scope_spec.md` (authoritative).
- **ODC data:** NATL60 for the OSSE path (the `2020a_SSH_mapping_NATL60` challenge) and the OSE path (the `2021a_SSH_mapping_OSE` challenge); download via the documented THREDDS/wget endpoints, behind the data-source adapter. Treat ODC as a resource wrapped behind our interfaces — do not build structurally on the ODC notebooks. ODC metric *definitions* should be adopted so our numbers are literature-comparable.
- **Target environment:** a single Linux machine with 64 CPUs; design parallelism accordingly.

## When to ask vs proceed

Ask, and pause, when: a decision is genuinely ambiguous in the spec; you hit a real blocker; something appears to require a §6 non-goal; or a §8 settled decision looks wrong. Otherwise proceed within the plan once approved. Prefer a clarifying question over a scope-expanding assumption.
