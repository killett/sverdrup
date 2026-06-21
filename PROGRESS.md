# Regatta — Progress notebook

## Current work (index — do not duplicate task state here)

- **Design doc:** `docs/superpowers/specs/2026-06-21-regatta-phase1-architecture-design.md`
  (approved brainstorm; the *how* for Phase 1).
- **Scope source of truth:** `phase1_scope_spec.md` (the *what* — settled).
- **Implementation plan:** `docs/superpowers/plans/2026-06-21-regatta-phase1.md`
  (22 tasks, build order = design §11). Task tracker:
  `docs/superpowers/plans/2026-06-21-regatta-phase1.md.tasks.json`.
  Resume with `/superpowers-extended-cc:executing-plans docs/superpowers/plans/2026-06-21-regatta-phase1.md`.
- **Next action:** execute **Task 1 (GridSpec)** — the first unchecked task. Then proceed in
  DAG order (Tasks 21 and 22 are non-skippable user-gates). Task 0 done (commit 8ad9da0).

## Cross-cutting decisions (canonical — lives nowhere else)

- **Method 1 = hand-rolled dense GP/OI** (not pyinterp/GPSat). Native covariance +
  whole-field samples via cached Cholesky `L` of `K_dd+R`, `cov(A,B)=K_AB−Vᵀ_A V_B`,
  `V_X=L⁻¹K_dX`. `R` is a structured operator (diagonal for nadir). Two complementary
  seams: `LinearSolver` (methods/, backend swap *within* the kernel formulation) and
  `CovarianceOperator` Protocol (core/, carries the kernel→precision/SPDE jump).
- **`CovarianceOperator` is the seam, not the GP.** `GaussianPredictiveDistribution(mean,
  cov: CovarianceOperator)` is method-agnostic; GP math lives in `methods/oi.py`. Operator
  declares `fidelity ∈ {EXACT, LOW_RANK, SAMPLE}`.
- **Exact/persisted boundary:** the unit of work returns the **Persisted** rep (mean +
  exact marginal var + low-rank `B` + clipped diagonal residual `d` + seed + sampler spec +
  rank `r` + captured-energy diagnostic), **never** a live operator carrying `L`. `B` from a
  matrix-free seeded randomized SVD of `P`; `d = clip(diag(P)−rowsum(B²), 0, None)`.
- **Unifying on-worker rule:** the worker extracts *everything needing the EXACT operator* —
  base reduction, declared derived quantities (first-difference), AND eval-point predictions
  at withheld/off-grid locations — before discarding the operator. Off-grid predictives are
  computed exactly, never by interpolating a marginal-variance field (invariant 7).
- **`Product` is an explicit bundle:** base + derived Persisted products + eval-point
  predictions, provenance linking each (route + `CovFidelity` stamped).
- **Derived dispatch = linearity × representation × `CovFidelity`.** Provenance stamps the
  covariance fidelity used. Only `firstdifference` is real (on-worker, EXACT); velocity/eke/
  transport/area_average are committed-signature stubs.
- **Data (Decision B):** real `DataSource` against ODC THREDDS + `./data/cache/`; daily
  NATL60-CJM165 reference (NOT the 11 GB hourly) clipped to 42-day window
  **2012-10-22→2012-12-02**; OSSE nadir obs ~285 MB whole. Committed tiny NetCDF fixtures for
  offline CI. Oracle = opt-in OI-RMSE parity **within 10% of the ODC OI baseline** (skipif no
  data/network; ≤25% for the tiny-fixture smoke run). OSE eval uses the withheld **CryoSat-2**
  along-track.
- **Space-time structure (load-bearing):** the GP covariance is space-time — spatial length
  scale × **temporal correlation scale**, both through the `ParameterProvider`. The
  unit-of-work window is space-time (spatial tile × temporal obs window around target output
  time(s); the 21-day spin-up gives early times temporal neighbors and bounds `N_obs`).
  **`GridSpec` stays purely spatial**; time is carried on the `Product` as a series of
  per-time persisted fields. One factored `K_dd+R` serves all output times in the window.
- **Kernel:** pinned to stationary **Matérn-3/2** (variance + spatial length + temporal
  scale), behind a `methods/kernel.py::Kernel` interface so it can go nonstationary later
  without touching `GPCovarianceOperator`.

## Gotchas

- The 11 GB NATL60 reference is hourly — never pull it; use the daily file. Footprint stays a
  few hundred MB.
- NATL60 challenge has no observation error ⇒ `R` ≈ a nugget for the oracle.
- `pyinterp` / `GPSat` are NOT installed; Method 1 needs none. `pixi add` any new dep.
- BLAS/OpenMP env vars must be set per-worker *before* numpy/BLAS loads (Nanny child env).

## Deferred items / open questions

- (none open — Phase-1 architecture is settled in the design doc.)
