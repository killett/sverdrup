# Sverdrup — Progress notebook

## Current work (index — do not duplicate task state here)

- **Phase 4: FEM/triangulation SPDE + non-chain coherent sampler — IN PROGRESS.**
  - **Stage A COMPLETE (Tasks 1–4); Stage-A GATE PASSED.** Projection seam
    (`core/projection.py`) consumed by `GMRFCovarianceOperator` (carries `q_prior`, C3
    `_diag` fast==slow pinned) and de-gridded `PrecisionFields`/`PrecisionDistribution`
    (`projection` + `prior_precision`, cov/sample route through `projection.weights`/
    `field_shape`); `GMRFPrecisionReduction` threads both; `solve.py` unchanged (projection
    rides on `base_fields`). Gate evidence: **185 passed / 2 skipped** (178 + 7 new), typecheck
    + lint clean; tests diff vs `31a58c6` = 96 insertions / 0 deletions (additions only);
    invariant-2 grep clean on the GMRF path. **Scoping note (gotcha):** the Task-4 gate grep's
    sole hit is `persisted.py` `PersistedDistribution.sample` (`ny, nx = self.grid.shape`) — the
    **OI low-rank** rep, which is inherently grid-bound and NOT in Phase-4 de-grid scope. The
    GMRF precision read-off (`PrecisionDistribution` + `GMRFCovarianceOperator`) is grep-clean.
    Interpret invariant-2 as "the precision/GMRF path is projection-driven", not "persisted.py
    contains no `.shape`".
  - **Stage B Tasks 5–6 COMMITTED then SUPERSEDED by a design pivot (`_strip_network` kept,
    `_draw_joint`/`_strip_prior` to be removed).** Tasks 5 (`a619265`) and 6 (`809a570`) built the
    spec-literal **synthesized strip-field** sampler (`_draw_joint`: one auxiliary field drawn from
    the prior-induced strip sub-GMRF; tiles kriged toward it). Task 7's verification **disproved that
    construction** — see the canonical Phase-4 cross-cutting decision "Stage-B sampler = spanning-tree
    hand-forward" below. **Working tree is clean at `809a570`** (Task-7 synthesized-field code was
    written, disproved, and reverted uncommitted — nothing wrong is on disk). `_strip_network` is
    kept (it computes the tile-adjacency / shared-node sets the spanning tree needs); `_draw_joint`
    and `_strip_prior` are removed in the re-architected Task 6. **Next action: AWAIT OWNER APPROVAL
    of the re-architected Stage-B plan (Tasks 6–9 + spec §3/contracts amended), then implement the
    spanning-tree sampler.**
  - Scope (source of truth): `phase4_scope_spec.md` (settled + owner-amended, `00519b1`).
  - Design: `docs/superpowers/specs/2026-06-26-phase4-fem-and-nonchain-sampler-design.md` (`f7960f8`).
  - Plan: `docs/superpowers/plans/2026-06-26-phase4-fem-and-nonchain-sampler.md`
    (16 tasks; tracker `.tasks.json` co-located, Tasks 1–4 `completed`).
  - **Hard-gated sequencing:** Stage A (Tasks 1–4, generalize under green) → Stage B
    (Tasks 5–9, non-chain joint-kriging sampler on the grid) → Stage C (Tasks 10–16, FEM).
    Three user-gates: Task 4 (Stage-A regression — Phase-3 suite reproduces exactly), Task 9
    (Stage-B positive control — distinct-tiles cross-seam + corner-junction joint cov +
    nonstationary, residual recorded; junction-tree fallback only if out-of-tolerance), Task 16
    (Stage-C FEM DoD).
  - **Five pinned correctness contracts (tested, not assumed — see design §0):** C1 strip prior
    on the induced subgraph (corner-junction joint cov), C2 three white-noise streams, C3 `_diag`
    fast-path equivalence, C4 per-node strip-prior κ (nonstationary), C5 mechanically-enforced
    no-grid-path-for-FEM; + C6 shared mesh-node match, C7 boundary-measured payoff margin.
  - **Key decisions:** scipy.spatial.Delaunay + hand-rolled P1 assembly (no new dep, Shewchuk
    upgrade behind the same seam); strip-prior = induced submatrix of the persisted per-tile
    PRIOR precisions (so PrecisionFields gains `projection` + `prior_precision`); `GmrfKrigingSolve`
    kept intact as the 1-D chain regression oracle (registry repoints to `GmrfJointKrigingSolve`,
    one wiring assertion updated). **Next action: Task 1 (Projection seam).**
- **Phase 3: GMRF method + representation-agnostic generalization — COMPLETE (all 11 tasks).**
  - **Stage C COMPLETE (Tasks 10–11):** Task 10 `PerturbEnsembleDegradation` driver end-to-end
    (per-tile independent members, weight-crossfaded; `EmpiricalReduction` retagged
    `perturb-ensemble`; blend appends `degradation_transform`/`KnownBias.DEGRADED_COHERENCE`;
    asserts the OPPOSITE contract — coherence loss recorded, mean continuous, sampler honestly
    under-dispersed vs the conservative marginal, NOT held to the coherence bar). Task 11
    nonstationary-κ GMRF (`MaternGMRF.solve` resolves `range` scalar OR field → elementwise κ
    field → spatially-varying `Q`; `kappa_from_range`/`range_from_kappa` polymorphic;
    κ↔range mapping recorded). Full suite **178 passed / 2 skipped**, typecheck + lint clean.
  - All three user-gates PASSED (Task 3 Stage-A regression, Task 5 Takahashi-vs-oracle, Task 9
    Stage-B kriging coherence). Plan `.tasks.json` all `completed`.
  - **Stage A COMPLETE (Tasks 1–3).** Three seams generalized OI-first under green:
    `ReductionStrategy` (`distributions/reduction.py`, selected by live-operator
    `representation`) + `CoherentMemberDriver` (`LowRankSharedBasis`, selected by persisted
    `sampler_spec`). Stage-A user-gate PASSED with captured AC evidence — Phase-2 subset
    129/2 green and untouched (full suite 134/2 = 129 + 5 new Stage-A tests), typecheck/lint
    clean, zero Phase-2 test files modified (diffed vs pre-Phase-3 baseline `793297e`).
  - **Stage B Tasks 4–8 COMPLETE** (committed): GMRF grid topology + bilinear/Projection
    (`methods/gmrf_grid.py`); CHOLMOD factor + hand-rolled Takahashi selective inverse
    (`methods/gmrf_linalg.py`, **USER-GATE PASSED** vs dense-Q⁻¹ oracle); `MaternGMRF` EXACT
    sparse-precision operator + temporal-taper conditioning (`methods/gmrf.py`, registered);
    `PrecisionFields`/`PrecisionDistribution` + `GMRFPrecisionReduction` (genuine-first-class,
    no factor); `solve_unit` dispatches `PrecisionFields → PrecisionDistribution`.
  - **Task 9 (Stage-B gate) COMPLETE — reworked via conditioning-by-kriging; GATE PASSES.**
    The original `GmrfPrecisionSolve` "native shared-w" driver (Task 8) was DISPROVEN
    (cross-seam derived quantities ~50% under-dispersed) and is REMOVED. Replaced by
    `GmrfKrigingSolve` (9a–9d, all committed): per-tile exact posterior draw krige-corrected
    toward ONE global node-space realization (single forward sweep, values-not-seeds, Q-separator
    precondition asserted). **Gate evidence (captured):** cross-seam `firstdifference` variance
    ratio blend/ref **min 0.93** (conservative; old driver ~0.49 / −0.51), correlation-structure
    fidelity max-dev **0.10**, pointwise σ-upper-bound held, OSSE+OSE + provenance +
    first-class all green; full suite **171 passed / 2 skipped**, typecheck + lint clean. Joint-cov
    oracle (9c) pins exactness vs a dense global reference (per-tile, cross-seam, 3-tile
    transitivity) + separator negative control. **USER-GATE: awaiting owner sign-off before
    Stage C** (spec-§8 escalation was NOT triggered — gate passed).
  - **Task-9 rework 9a–9c COMPLETE (committed); 9d IS THE NEXT ACTION.**
    - 9a (`posterior_cov_columns` full `(Q⁻¹)[:,S]` via cached per-node back-solves on
      `GMRFFactor`/`PrecisionDistribution`) — pinned vs dense oracle.
    - 9b (`GmrfKrigingSolve` forward-sweep driver, values-not-seeds, **Q-separator assertion**
      overlap ≥ `STENCIL_REACH=2`) — replaced the disproven `GmrfPrecisionSolve` (class removed)
      under `sampler_spec="sparse-precision"`.
    - 9c (joint-cov oracle `tests/unit/test_gmrf_kriging_oracle.py`): per-tile full-cov ==
      exact posterior; cross-seam joint (incl. across-seam blocks) == global; 3-tile
      transitivity; separator negative control. All EXACT by construction.
  - **Next action: Phase 3 is DONE.** Phase 4 (autotune) is the next milestone (deferred,
    scoped after Phase 3 runs — spec §6). Before Phase 4 build: the GMRF cross-tile sweep is
    exact only for tree-structured tile adjacency; 2-D/FEM tilings need the pre-drawn-joint or
    junction-tree variant (spec §5.3.1 Phase-4 caveat — do NOT inherit as unconditionally true).
  - **Working-tree state at this checkpoint (committed):** `pipeline._blend_eval_points` has the
    sparse-precision no-factor **moment-crossfade** OSE path + the `eval_point_cov` provenance
    marker (Task-9 §B6, keeper); `GmrfPrecisionSolve` carries a shape-bug fix but the whole class
    is superseded by `GmrfKrigingSolve` in 9b; the obsolete `test_gmrf_blend_no_variance_dip`
    (pre-amendment contract) was removed (9d writes the derived-quantity-parity replacement).
  - Scope (source of truth): `phase3_scope_spec.md` (settled; §5.1 now records the two
    settled forks — scikit-sparse/CHOLMOD backend + temporal-taper-into-R conditioning — and
    the forward-compat Projection abstraction).
  - Design = the spec; Implementation plan: `docs/superpowers/plans/2026-06-25-phase3-gmrf-representation-generalization.md`
    (11 tasks; tracker `.tasks.json` co-located, all `pending`).
  - **Hard-gated sequencing:** Stage A (Tasks 1–3, generalize OI under green) → Stage B
    (Tasks 4–9, add GMRF) → Stage C (Tasks 10–11). Three user-gates: Task 3 (Stage-A
    regression, 129/2 must stay green — if OI changes, surface it, don't adjust tests),
    Task 5 (Takahashi vs dense-Q⁻¹ oracle — red = math bug, not a tolerance loosen),
    Task 9 (Stage-B GMRF blend validation — spec-§8 escalation on failure).
  - **Key architecture decisions (canonical — see Cross-cutting decisions Phase 3):**
    two-point dispatch split (reduction by live-operator representation pre-persistence;
    coherence driver by persisted `sampler_spec` post-persistence); `to_persisted` is a
    `ReductionStrategy` in `distributions/reduction.py`, NOT on the core Protocol
    (invariant 1 + one-way dependency rule); GMRF read off the precision via a `Projection`
    (grid=identity, off-grid=bilinear) so a later FEM phase needs only a new projection.
- **Phase 2: tiling / blend / coherent uncertainty — COMPLETE (all 17 tasks 0–16).**
  - Scope (source of truth): `phase2_scope_spec.md` (committed `fa93897`).
  - Design doc: `docs/superpowers/specs/2026-06-23-phase2-tiling-blend-architecture-design.md`.
  - Implementation plan: `docs/superpowers/plans/2026-06-23-phase2-tiling-blend.md`
    (17 tasks, 0–16); tracker `.tasks.json` co-located, all `completed`.
  - **Both user gates PASSED with captured AC evidence:** Stage A (Task 15 — regional blend
    == single-tile, no seam, conservative σ, withheld OSSE+OSE eval, provenance, both
    withholding exemplars) and Stage B (Task 16 — projection-mixed partition, sample-based
    `regrid`, cross-CRS blend, polar-void relax-to-prior, opt-in global skipped cleanly).
  - **Key §8 resolution (see Cross-cutting decisions):** the structured coherent-sample
    driver is the shared-overlap-basis (Löwdin) construction, NOT member-only `z_r`.
  - Suite: 129 passed / 2 skipped (Stage-B global run + one pre-existing skip).
  - **DEFERRED to Task 15:** `run_tiled_pipeline` in `application/pipeline.py`. The plan's Task-12 Step 3 only implements `TilingCoordinator` (which IS done + tested) and says the pipeline wiring is "exercised in Task 15". The eval impedance — `_evaluate` reads `product.per_time[].base.fields.mean`, but the coordinator returns `BlendedDistribution`s — is resolved when Task 15's integration test defines the contract. Build `run_tiled_pipeline` there.
- **Milestone: rename to `sverdrup` + PyPI release — COMPLETE (Tasks 1–7).**
  - Design doc: `docs/superpowers/specs/2026-06-21-sverdrup-pypi-release-design.md` (approved).
  - Implementation plan: `docs/superpowers/plans/2026-06-21-sverdrup-pypi-release.md` (7 tasks);
    tracker `.tasks.json` all `completed`.
  - Package renamed `regatta`→`sverdrup`; hatchling + hatch-vcs tag-driven build; Apache-2.0 +
    metadata + `py.typed`; core deps + `dask`/`io`/`all` extras; Trusted-Publishing workflow
    shipped at `docs/superpowers/ci/release.yml` (Option B). User-gate (clean-venv install smoke)
    re-validated. Public repo `killett/sverdrup` created and `main` pushed.
  - **DONE end-to-end:** all three user-side steps completed by the user — workflow installed,
    PyPI Trusted Publisher configured, `v0.1.0` tagged+pushed. `sverdrup 0.1.0` is **live on
    PyPI** (wheel+sdist, Apache-2.0); `pip install sverdrup` verified in a clean venv.
- **conda-forge distribution (in progress):**
  - Recipe generated via `grayskull` (run with `pixi exec grayskull`, not added to manifest),
    polished, and committed at `conda-recipe/meta.yaml` (+ `conda-recipe/README.md`).
  - `noarch: python`; sdist sha256 verified against PyPI; confirmed the sdist builds **without
    `.git`** (hatch-vcs reads version from PKG-INFO) — so conda-forge's sdist build works.
  - **Auto-update mechanism (the goal):** after the one-time `conda-forge/staged-recipes` PR,
    the conda-forge **autotick bot** watches PyPI and opens a version-bump PR on every PyPI
    release. Steady state: push tag → PyPI Action publishes → bot opens feedstock PR → merge.
  - **staged-recipes PR OPEN:** https://github.com/conda-forge/staged-recipes/pull/33814
    (`killett:sverdrup`). Awaiting conda-forge CI + maintainer review/merge → feedstock
    auto-created → conda package ships. User responds to any reviewer feedback.
  - **Gotcha:** the autotick bot only bumps version+hash. When `pyproject.toml` runtime deps
    change, mirror them into `requirements/run` in both `conda-recipe/meta.yaml` and the
    feedstock PR.
  - **Gotcha (CI failure, fixed):** first staged-recipes build #1541860 FAILED on all platforms
    in the *test* phase: `ModuleNotFoundError: No module named 'dask'`. Cause — the recipe test
    ran `python -m sverdrup`, but `__main__.py` eagerly imports the dask executor + pipeline
    (the `dask`/`io` *optional extras*, not core run deps). The conda test env has only core
    deps. Fix: test only the core import surface (`import sverdrup`, `sverdrup.core.grid`,
    `pip check`) — never the entry point — since core deps are all that's guaranteed installed.
    Same trap will bite any feedstock test: do not add extras-dependent checks to `test:`.
- **Phase 1: COMPLETE** — 22 tasks on `main`; suite 70 passed / 1 skipped; both user-gates
  re-validated. Plan: `docs/superpowers/plans/2026-06-21-regatta-phase1.md` (historical).
  Design: `docs/superpowers/specs/2026-06-21-regatta-phase1-architecture-design.md`.

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

## Cross-cutting decisions (canonical — Phase 4)

- **Stage-B non-chain sampler = spanning-tree hand-forward (NOT a synthesized strip field).**
  The spec-literal Task-6 construction (`_draw_joint`: draw ONE auxiliary field over the
  overlap-strip sub-GMRF, krige every tile toward it) was **disproved by measurement** and replaced.
  This decision is owner-confirmed across a multi-turn adversarial review; the measurement trail is
  recorded here because it is load-bearing and lives nowhere else.
  - **Disproof (real natl60_tiny fixture, 3-tile + 2×2):** the synthesized-field driver blows the
    cross-seam first-difference variance ratio to **376×** (bound ≤2.5) and joint-cov rel-err vs the
    dense global posterior to **1.617**. On a well-conditioned synthetic corner fixture the same
    driver is fine (cross-seam 0.77–1.33) — so the construction is not trivially broken; the natl60
    fixture is the discriminator.
  - **Mechanism (measured, not guessed):**
    1. prior-vs-posterior is a **non-issue** — obs sit at tile centres, so `AᵀR⁻¹A≈0` at the strip
       nodes and `Q_post ≡ Q_prior` there to machine precision (strip submatrices byte-identical;
       `x_joint` std 613 either way). The "diffuse prior was wrong scale" hypothesis is **refuted**.
    2. the joint-cov error is **high-frequency**, **90% in the complement** of the bottom-k near-null
       subspace, and a shared global coarse-mode draw does **not** close it (1.617→1.393 at k=6).
       There is **no spectral gap** (global `Q_post` bottom eigenvalues `2.5e-7, 4.95e-7, …`, a
       continuum) — so the near-improper behaviour is an O(n) low-frequency tail, NOT a low-dimensional
       coarse space. Coarse-space deflation is **refuted**.
    3. `cond(sigma_ss) ≈ 4e8` (the value-conditioning operator `solve(Σ_ss, x_s − x_u|_S)`), **flat
       across halo width k=1,2,3 and resolution 0.5°/1.0°**, pinned by `Q_post`'s near-null eigenvalue
       2.5e-7 — i.e. **intrinsic** (sparse nadir obs leave the `(κ²−Δ)²` low-frequency mode
       under-determined), NOT a strip-resolution mismatch. A resolution precondition would not fix it.
    4. **jitter is a cover-up** (proven): adding `λI` to `Σ_ss` collapses the gradient ratio
       (324→3.2) while joint-cov rel-err **stays 0.61–0.73** — gradient parity goes green while the
       joint law is still 60–70% wrong. `pinv(rcond)` is a no-op (modes are physically huge-variance,
       not numerically tiny). **Gradient parity ≠ joint-law fidelity; gate the joint cov.**
  - **The fix:** the 4e8 singularity is *never excited* when conditioning targets are **consistent**
    (a residual `x_s − x_u|_S` that is tiny because `x_s` is an actual neighbour draw from the same
    posterior). That is exactly what the Phase-3 **chain** sweep does (`GmrfKrigingSolve._sweep`,
    still green). Generalize the line to a **max-overlap spanning tree of the tile-adjacency graph**:
    each tile is hand-forward-conditioned on its parent's already-drawn overlap values (the proven
    chain mechanism), non-tree edges carry a **bounded, recorded** transitive-coherence residual.
  - **Validation (2×2 natl60):** spanning-tree sweep drops overall joint-cov rel-err **1.617 → 0.313**
    (no 4e8 excitation). Tree edges **0.18–0.24**, dropped edges **0.19–0.43**. The plain **chain
    baseline** on the green 3-tile natl60 case is **0.298 overall, edges 0.294/0.313** — i.e. the
    ~0.30 halo-truncation residual already accepted & shipped green. Tree edges are **no worse than
    that baseline**; the dropped-edge max (0.43, a BFS-star artifact that kept a low-overlap diagonal
    and dropped a high-overlap side) is **1.4× the baseline** and improves under max-overlap MST.
  - **Task-9 gate = three coupled assertions (thresholds derived from the 0.30 chain baseline, not
    guessed):** (1) **tree-edge parity** — `max_tree_edge_residual ≤ chain_baseline·(1+slack)`,
    chain_baseline measured on the 1-D natl60 case; (2) **dropped-edge relative bound** —
    `max_dropped_edge_residual ≤ C · max_tree_edge_residual`, `C ∈ [2,3]`; (3) **conservative
    direction** — cross-seam derived-quantity variance ratio (blend/ref) on dropped edges `≥ 1−ε`,
    never under-dispersed (the real protection; magnitude-bounded-but-overconfident must fail).
    Plus a **two-tree invariance property test**: the shipped blend is within tolerance under the MST
    AND one alternative spanning tree (correctness is tree-invariant; only the residual distribution
    moves — if correctness depends on the tree, topology-fragility has returned → loud red).
  - **Per-tree-edge separation assert:** the MST is built from existing `extended_window` overlap
    strengths; every selected tree edge must have overlap ≥ the stencil-separation requirement
    (`_assert_separates` content, now per-tree-edge not per-chain-link) — a too-thin tree edge cannot
    hand forward and is a loud red per edge.
  - **Spec amendment (replaces two wrong sentences):** §5.3/§4 becomes *"hand-forward conditioning
    along a max-overlap spanning tree of the tile adjacency; non-tree edges carry a bounded, recorded
    coherence residual; junction-tree is the exact escalation if a measured residual exceeds
    tolerance."* **Product-facing disclosure (load-bearing, honest):** the shipped global SSHA
    uncertainty carries a bounded, recorded cross-seam coherence residual on **non-tree** tile
    adjacencies — coherence there is **transitive, not direct**; a downstream consumer computing a
    transport across a non-tree seam is entitled to know this. Junction-tree (a) is the documented
    **exact escalation** if the Phase-5 tuner wanders to short range and pushes a measured residual
    past the gate; it is NOT adopted now because it re-introduces tile-topology dependence and
    √(#tiles) treewidth — the very costs Stage B exists to avoid.
  - **Contracts C1/C2/C4 (synthesized-field) are RETIRED** and replaced by the spanning-tree
    contracts above. C3, C5, C6, C7 stand. Obsolete on-disk code to remove in the re-architected
    Task 6: `_draw_joint`, `_strip_prior`, `_interiorness` (`distributions/coherent.py`) and their
    tests (`tests/unit/test_draw_joint.py`). `_strip_network` is **kept** (adjacency + shared-node
    sets). Stage-A (Tasks 1–4) is **unaffected** — the Projection seam / de-grid generalization is
    orthogonal and already gated green.

## Cross-cutting decisions (canonical — Phase 3)

- **Two-point dispatch split (load-bearing).** Reduction strategy is selected by the LIVE
  operator's `representation` (pre-persistence): `select_reduction(dist)` in
  `distributions/reduction.py` reads `getattr(dist.cov_op, "representation", "lowrank+diag")`
  → `LowRankReduction` ("lowrank+diag") / `GMRFPrecisionReduction` ("sparse-precision"), or
  `EmpiricalReduction` when there is no operator. The coherence driver is selected by the
  PERSISTED `sampler_spec` (post-persistence): `select_driver(sampler_spec)` in `coherent.py`
  → `LowRankSharedBasis` / `GmrfPrecisionSolve` / `PerturbEnsembleDegradation`. Never dispatch
  on method identity.
- **`to_persisted` is NOT on the core Protocol.** §5.4's illustrative on-`CovarianceOperator`
  signature was self-inconsistent (it returns a `distributions/` type from `core/`, breaking
  the one-way `application/→distributions/` rule, and modifies the Protocol, violating
  invariant 1). Realized as the `ReductionStrategy` Protocol in `distributions/reduction.py`,
  selected by representation. Operators carry a `representation` class attr only (not on the
  Protocol). Spec §5 permits this ("signatures illustrative; correct where it differs").
- **GMRF reads off the precision via a `Projection`.** Precision-node space and output-grid
  space kept distinct even though they coincide on a regular grid. `mean→W·mean`,
  `cov→W Σ Wᵀ` (Σ = selective-inverse entries in W's stencil, never dense). Grid block =
  `GridIdentityProjection` (W=identity-on-nodes); off-grid = `BilinearProjection`; `A`
  (grid→obs conditioning) is itself a projection into node space. A later FEM phase supplies
  a new `Projection` + mesh-assembly only — precision rep, coherence driver, persistence, and
  blend untouched. (Recorded in `phase3_scope_spec.md` §5.1.)
- **GMRF time = temporal taper into R (not a temporal SPDE axis).** `Q_post = Q_prior +
  AᵀR⁻¹A`; R per-obs variance inflated by `exp(|t_obs−t_out|/temporal_taper_scale)`; the
  taper scale is a tunable in `parameter_space()` resolved via the provider. Conservative
  diagonal-R approximation (under-uses temporal structure) recorded as a `known_bias`. The
  OI-vs-GMRF asymmetry (OI = full space-time kernel; GMRF = spatial cov + tapered likelihood)
  is deliberate and read into the Stage-B comparison.
- **One sparse factor serves all three (invariant 6).** `GMRFFactor` (CHOLMOD simplicial)
  serves `sample` (L⁻ᵀw), `solve` (posterior mean), and the hand-rolled Takahashi selective
  inverse (`diag(Q⁻¹)` + adjacent entries on the L+Lᵀ pattern). Dense `Q⁻¹` exists ONLY as a
  small-grid test oracle. Adjacency precondition (W's 4-node stencil + firstdifference's
  adjacent-node cov inside the selective-inverse pattern) is asserted — guards a future wider
  κ-stencil from silently breaking eval var / cancellation.
- **GMRF eval-point OSE blend = moment crossfade.** GMRF has no low-rank eval factor; cross-
  tile eval-point scoring uses `mean=Σwμ`, `var=(Σwσ)²` (exact per-tile var from Takahashi).
  Cross-eval-point covariance in overlaps is NOT represented (not consumed by per-point OSE
  accuracy/calibration) — recorded in provenance (`eval_point_cov` marker), a flag not a
  hidden assumption. Full coherent eval-point GMRF sampling is out of Phase-3 scope.
- **α = 2 (ν = 1)** fixed integer smoothness — the canonical `(κ²I−Δ)` 5-point stencil
  squared. Continuous ν deferred to Phase 4.
- **GMRF cross-tile coherence = conditioning-by-kriging, NOT native shared-w (amendment, spec
  §5.3.1).** The Checkpoint-2 "GmrfPrecisionSolve: mean + L⁻ᵀw, native shared-w" line was wrong
  for non-identical Q — `L⁻ᵀ` is a global map, so shared factor-space white noise yields
  decorrelated physical fields across distinct tiles (proven by a distinct-tiles positive
  control: overlap corr ≈0 at all halos; cross-seam derived-quantity error −0.51). Fix:
  **conditioning-by-kriging** `x_c = x_u + Σ_cross Σ_shared⁻¹ (x_shared − x_u|S)`, each tile
  conditioned toward ONE global node-space realization via a single forward sweep
  (values-handed-forward, NOT seed-shared; transitive by construction for a tile chain).
  Cross-cov blocks `Σ_{·,S}` = full `Q⁻¹` columns via **factor back-solves** (outside Takahashi's
  pattern; computed once per tile, reused across members). **Validity invariant:** corrected
  draws are exact posterior samples (kriging-preserves-conditional-law theorem), verified by a
  **joint-covariance** oracle on a dense small grid — marginal checks are the blind spot.
  **Separator precondition (asserted, checked):** the handed-forward overlap must Q-graph-separate
  processed/unprocessed interiors (overlap ≥ stencil reach = 2 for α=2; the `k·corr_len` halo
  policy satisfies it); a negative control proves the joint law breaks when it doesn't. **Exact
  only for tree-structured tile adjacency** — 2-D/FEM (Phase 4) needs the documented
  pre-drawn-joint or junction-tree variant. The marginal `σ=Σwσ` bound is unchanged
  (pointwise-conservative; only the *sampler* changes). Plan:
  `docs/superpowers/plans/2026-06-25-phase3-task9-gmrf-kriging-sampler.md`.

## Cross-cutting decisions (canonical — Phase 2)

- **Coherent-sample structured driver = shared-overlap-basis (Löwdin), NOT member-only z_r.**
  The design's default Option-1 (member-only `z_r` applied to each tile's own factor) was
  escalated and rejected at the Stage-A gate (design §8). Diagnostics proved it was NOT a
  sampler bug (diagonal exact; core/aligned ≈ MC floor) but a genuine, *large, k-independent*
  basis-orientation residual: each tile builds an independent rank-20 randomized-SVD basis, so
  the structured factors are ~orthogonal across tiles (structured ratio ≈ 0.39) and member-only
  `z_r` makes them add as if independent → coherent samples underdispersed ~40–67% vs the
  reported cheap-path variance, *growing* with k. Fix (`coherent_structured_field` in
  `distributions/coherent.py`, used by `BlendedDistribution._coherent_member`): project every
  tile factor into ONE common orthonormal basis `Q` (QR of the stacked factors over the
  support), take the symmetric square root `Aᵢ=(QᵀFᵢ Fᵢᵀ Q)^½` to strip the SVD rotational
  ambiguity, and drive `G=Σ wᵢ Q Aᵢ` with ONE shared member-seeded latent `g`. Result: cheap≈
  sampled rel 0.45→0.03 and k-direction flipped growing→flat; cross-seam derivative recovers.
  The reported marginal (`BlendOperator.blend`'s `(Σwσ)²`) is UNCHANGED (still conservative;
  Task-3 cheap path untouched) — only the *sampler* changed. `MemberSeededZr`/`realize_one`
  remain for single-tile use. If Stage B's larger overlaps degrade `Q` conditioning, the next
  lever is the retained per-tile rank, NOT the driver (owner directive).
- **`run_tiled_pipeline`** (`application/pipeline.py`) reuses Phase-1 `_prepare`/evaluators:
  per-tile obs windowed to `extended_window`, eval locations windowed per tile, one submit per
  tile via the existing `Executor`, grid blend + OSE eval-point `PointSet` blend, then the
  Phase-1 `Registry`. OSSE scores the blended grid vs truth; OSE scores blended eval-point
  predictives vs withheld CryoSat-2. `UnitOfWork.obs` relaxed to `ObsWindow | None` (None only
  for obs-less coordinator probes in tests; real solves always set it).

## Gotchas

- **mypy runs `mypy .` (whole tree, tests included)** via the pre-commit hook — test files
  must be type-clean too (e.g. assert `x is not None` before using an `Optional`). numpy ops
  often infer `Any`; wrap returns in `np.asarray(...)` to satisfy `no-any-return`. scipy/dask/
  distributed calls need `# type: ignore[import-untyped]` / `[no-untyped-call]`.
- **Plan deviations made & verified:** (1) Task 10 perturb_and_ensemble seeds members from the
  caller seed + index, not `id(obs)` (the plan's id-based seed broke the reproducibility test).
  (2) Task 19 CRPS test: the plan's expected `0.23379` is CRPS at y=0, but the test uses y=0.5;
  correct closed-form value is `0.331404`. Implementation formula is the standard correct CRPS.
  (3) Task 19/21: evaluators take `result: object` (not `dict[...]`) so they conform to the
  `Evaluator` protocol and can go into `Registry([...])`. (4) Task 21 `_evaluate`: OSSE runs
  calibration on the gridded truth (the plan only set TRUTH, so Calibration — which needs
  WITHHELD_OBS — would never fire and the OSSE acceptance demands reduced_chi2/coverage); OSE
  withholds CryoSat-2 by mission-splitting the obs window (the test passes a plain FixtureSource
  with no `withheld()` method, so withholding must happen in the pipeline, not the source).

- **Task-1 deviation (verified):** `.gitignore` never ignored `__pycache__`/`*.pyc`, so Phase 1
  left 77 `.pyc` files tracked. The rename swept them in; untracked them (`git rm --cached`) and
  added `__pycache__/`, `*.pyc`, `.mypy_cache/` to `.gitignore` so the soon-public repo stays
  clean. `pixi.lock` (593 KB) exceeds the 500 KB hook only under `--all-files`; it is unmodified
  so the staged-only commit hook passes.
- The 11 GB NATL60 reference is hourly — never pull it; use the daily file. Footprint stays a
  few hundred MB.
- NATL60 challenge has no observation error ⇒ `R` ≈ a nugget for the oracle.
- `pyinterp` / `GPSat` are NOT installed; Method 1 needs none. `pixi add` any new dep.
- BLAS/OpenMP env vars must be set per-worker *before* numpy/BLAS loads (Nanny child env).
- **Phase-2 Task 11 deviation (verified):** `ScaleAwareHalo.halo_for` evaluates the
  correlation length at the band's *equatorward-most* latitude (`clamp(0, lat_lo, lat_hi)`),
  not at the band's lat nodes as the plan literal showed. The plan test asserts the halo for
  band (-5,5) equals `k*800` (equator cl), which the node-based version (cl at ±5 ≈ 797)
  would miss. Correlation length is monotone-decreasing in |lat|, so the widest over a band
  is at min|lat| — this is the correct "widest over the core band".
- **Phase-2 Task 6 deviation (verified):** `FirstDifference._diff_var` calls
  `dist.covariance(a,a/b,b/a,b)` node-by-node; the naive general-path covariance
  (regenerate 256 members per query point) made the composition test take 67s. Fix:
  `BlendedDistribution.covariance` now snaps query points to nearest grid nodes and reads
  from one cached `_grid_sample_batch(256)` realization (lazily computed, memoized on the
  instance). 67s → ~4s. Snapping is consistent with `PersistedDistribution.covariance`
  (which also snaps via `_idx`); fine for grid-node derived ops. The plan explicitly
  allowed this fast path (Task 6 Step 3).

- **Phase-3 Task-7 addition (verified):** `solve_unit` (`application/solve.py`) now dispatches the
  base distribution on `unit.base_fields` type — `PrecisionFields → PrecisionDistribution`, else
  `PersistedDistribution`. The plan's Task-7 file list omitted solve.py, but widening
  `ReducedUnit.base_fields` to `PersistedFields | PrecisionFields` forced it (and it is *required*
  for genuine-first-class GMRF to flow through the executor into the Task-9 blend as a
  `PrecisionDistribution`, not silently wrapped in `PersistedDistribution`). `PerTimeProduct.base`
  is typed `Any`, so no product-type churn. `PrecisionDistribution._factor_obj` is annotated via a
  `TYPE_CHECKING` import of `GMRFFactor` (ANN401 forbids `-> Any`); the runtime import stays lazy so
  `persisted.py` does not hard-require sksparse.
- **Phase-3 Task-5 deviation (verified) — sksparse 0.5.0 has a NEW scipy-style API.**
  `pixi add scikit-sparse` installed **scikit-sparse 0.5.0**, a rewrite — NOT the classic
  0.4.x `Factor` object the plan assumed. The plan's `cholesky(Q, ordering_method=..., mode=
  "simplicial")` + `factor.L_D()`/`.P()`/`.solve_Lt()`/`.apply_Pt()` DO NOT EXIST. Real API:
  `from sksparse.cholmod import cho_factor`; `cf = cho_factor(Q, order="amd", lower=True)`
  returns a `CholeskyFactor` with `cf.L` (sparse lower, `L Lᵀ = Q[P][:,P]`, `is_ll=True` for
  SPD), `cf.D`, `cf.perm` (the permutation P, factor is of the *permuted* matrix
  `Q[perm][:,perm]`), `cf.solve(b)` solves `Q x = b` (perm internal), `cf.is_ll`.
  `GMRFFactor` (`methods/gmrf_linalg.py`) wraps this: deterministic perm via `order="amd"`;
  one lower `Lc` (`cf.L`, or `cf.L·√diag(D)` if a future matrix factors LDLᵀ) drives sample
  (`spsolve_triangular(Lcᵀ, w)` then scatter `x[perm]=y`), Takahashi, and the back-map.
  **Permutation back-map indexes by `perm` directly** (NOT `argsort(perm)` as the plan's snippet
  did): original entry `(perm[k], perm[l])` carries permuted value `(k,l)`. Pinned correct by
  the dense-Q⁻¹ oracle (diag + adjacent rtol 1e-9). Takahashi recursion math is verbatim plan.
- **Phase-3 Task-2 deviation (verified):** widening `BlendInput.distribution` to the abstract
  `PredictiveDistribution` protocol (which declares only `grid`/`provenance`/`marginal_variance`/
  `covariance`/`sample`/`regrid`) means the duck-typed `.fields`/`.time_days` reads in `blend.py`
  (`_constituent_moments`, `_coherent_member`, `BlendOperator.blend`) need `cast(Any, dist)` to
  pass `mypy .`; the `PersistedPoints` eval-point constituent in `pipeline.py` is `cast(
  PredictiveDistribution, pp)` at the `BlendInput(...)` call (it exposes the fields by duck
  typing but isn't a structural match). The Stage-A seam test imports `_nearest` from
  `distributions.coherent` (where it now lives) not `distributions.blend` — mypy's
  `--no-implicit-reexport` rejects the re-exported name. The plan literal said import from blend;
  importing from coherent is equivalent (same function) and the only change vs the plan text.

- **Phase-3 Task-9b finding (load-bearing) — GMRF kriging sweep uses INDEPENDENT per-tile
  white, NOT the shared-lattice `diagonal_noise`.** The kriging theorem requires each tile's
  *unconditional* draw to be independent of the handed-forward target values. The old
  native-shared-w mechanism shared white across tiles by global cell, which correlated each
  tile's draw with the targets and **biased** the correction (spurious long-range correlation;
  the per-tile-validity oracle caught it). `GmrfKrigingSolve._sweep` now seeds white per tile via
  `derive_seed(method, params, f"gmrf-tile:{pos}", member)`. The single-tile coherent-member
  tests assert against this per-tile white (NOT `diagonal_noise`). `diagonal_noise` is still used
  by `LowRankSharedBasis` (OI), unchanged.
- **Phase-3 Task-9c finding — negative-control fixture limitation (recorded so 9d/Phase-4 don't
  re-derive it).** The separator assertion (`overlap ≥ reach=2`) is a STRUCTURAL *sufficient*
  condition for joint exactness at all κ — correctly conservative. Demonstrating "1-col overlap →
  wrong joint" with the exact-marginal fixture is regime-dependent: at well-conditioned κ (≈0.7)
  a 1-col overlap is *benign* (short correlation ⇒ the distance-2 precision edge barely affects
  the joint), and the long-correlation regime where it genuinely breaks makes the
  `inv(Σ_global[tile,tile])` construction ill-conditioned (double-inverse of a near-singular Σ).
  So `test_separator_negative_control` proves wrongness via the **weighted-blend seam-column
  collapse** (a 1-col overlap leaves no room for the partition-of-unity crossfade → seam variance
  collapses; joint Frobenius ≫ MC) **plus** the assertion firing — both real reasons the
  `≥reach` policy holds. The positive joint-cov oracles (≥2-col) match global EXACTLY; the chain
  construction is sound.

## Deferred items / open questions

- **Next release — relax the conda recipe Python cap.** `pyproject.toml` now declares
  `requires-python = ">=3.12"` (cap dropped, commit `e236591`; source uses only stable stdlib
  and numpy/scipy/pyproj all ship cp314 wheels). The **0.1.0** recipe deliberately keeps
  `run: python >={{ python_min }},<3.14` to match the already-published 0.1.0 wheel (building
  0.1.0 on 3.14 would fail `pip install .` — its metadata excludes 3.14). On the next release:
  when the autotick bot opens the feedstock bump PR, drop the `,<3.14` from the `run` pin
  (→ `python >={{ python_min }}`) and mirror the same in `conda-recipe/meta.yaml`. Do NOT do
  this before a `>=3.12` wheel is on PyPI.
- **Optional:** `pixi.toml` dev pin still `python = ">=3.12,<3.14"` (left capped to avoid a
  `pixi.lock` re-solve; doesn't limit the published package). Relax only if CI should exercise 3.14.
