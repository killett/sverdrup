You are building **Phase 4** of `sverdrup`: extending the GMRF method from a regular-grid discretization to a **finite-element (FEM/triangulation) SPDE** (the canonical Lindgren–Rue–Lindström construction), and replacing the chain-only cross-tile coherent sampler with a **topology-agnostic** one — because 2-D and mesh tiling break the tree assumption the current sweep relies on.

**The complete, settled specification is in `phase4_scope_spec.md` in this repo. Read it in full before doing anything else. It is the source of truth. This prompt foregrounds the parts that must not be missed; on any conflict, the spec governs, and if you believe the spec itself is wrong, raise it as a question rather than diverging.**

The requirements are settled — both brainstorm checkpoints are closed. **Do not re-gather requirements or re-open scope.** Use the **brainstorming skill (from superpowers)** to turn the settled spec into a concrete *implementation plan and architecture* — aimed at *how to refactor and extend this codebase in three stages*, not *what to build*.

## The two most important rules

1. **Generalize under green, then extend — and separate the two hard problems.** Phase 4 is three stages: **(A)** wire the GMRF operator and persisted form onto a *consumed* Projection seam and de-grid the persisted form, with the full Phase-3 suite green at every step as the regression oracle; **(B)** replace the chain-only coherent sampler, developed and validated on **2-D grid** GMRF tiling first (coincident nodes — the topology problem isolated from the mesh problem); **(C)** add FEM (mesh + projection), inheriting the now-topology-agnostic sampler. Do not combine FEM with the topology fix; debugging both at once is the confounding the Phase-3 meta-lesson warns against. Do not start B until A's regression gate is green; do not start C until B's positive control passes.
2. **Three source-grounded corrections are explicit Stage-A work, not "untouched."** Verified against the current code: `GMRFCovarianceOperator` and `PrecisionDistribution` hardcode `bilinear_weights(self.grid, …)` and reshape to `grid.shape`; the `GridIdentityProjection`/`BilinearProjection` dataclasses are consumed nowhere; `GmrfKrigingSolve` conditions on coincident nodes via a lon-chain sweep with `_assert_separates` checking lon columns. So FEM is **not** "just a projection swap" — Stage A must wire the read-off onto a real Projection seam and de-grid persistence first.

## Workflow — follow in order

1. **Read `phase4_scope_spec.md` in full**, then **read the real source** you will refactor: `methods/gmrf.py` (`GMRFCovarianceOperator`, `MaternGMRF`), `methods/gmrf_grid.py` (`matern_precision`, `bilinear_weights`, the dead `GridIdentityProjection`/`BilinearProjection`), `distributions/coherent.py` (`GmrfKrigingSolve`, `_assert_separates`, `select_driver`, `_DRIVERS`), `distributions/persisted.py` (`PrecisionFields`/`PrecisionDistribution`, `posterior_cov_columns`), `distributions/reduction.py` (`GMRFPrecisionReduction`, `select_reduction`), and `methods/gmrf_linalg.py` (`GMRFFactor`, selective inverse). If the spec is not present, stop and ask for it.
2. **Brainstorm and produce an implementation plan. Write no implementation code in this step.** Cover, in order: (A) the `Projection` seam the operator and persisted form will consume (abstracting `W` + node-space/field-shape), how the grid dataclasses are refactored *into* use, how persistence de-grids, and which existing tests pin the behavior to preserve; (B) the `GmrfJointKrigingSolve` replacement (pre-drawn joint field over the overlap-strip network, independent per-tile white, weight-crossfade), the 2-D grid tiling it is validated on, and the positive/negative controls; (C) the FEM method (`fem_precision` mass+stiffness assembly, `FEMBasisProjection`, global/shared-node boundary-extended mesh), the genuine-discretization-swap test, and the payoff demo. Name the FEM dependency (a triangulation/Delaunay library) explicitly.
3. **Present the plan and STOP. Await explicit approval before implementing.**
4. **On approval, implement incrementally and test-first.** Keep the Phase-3 suite green through all of Stage A. Small reviewable commits. Honor the stage gates above.
5. **Validate against the definition of done** (§7): Stage A (Phase-3 suite green through the refactor), Stage B (2-D grid GMRF coherent, controls pass), Stage C (FEM validates through the blend, genuine-swap test + payoff demo).

## Non-negotiable invariants (spec §3 — Phase-1 invariants 1–10, Phase-2 1–12, Phase-3 1–11 all still bind; these add the Phase-4 specifics)

1. **Generalize under green before extending**; a red in Stage A/B means behavior changed — surface it, do not loosen the test.
2. **The operator and persisted form consume a `Projection` seam**; no `bilinear_weights(self.grid, …)` or `grid.shape` reshape remains in either; `A` (node→obs) is the same projection at obs points.
3. **The persisted form is node-space-described, not grid-described** (carries the projection/node space; flat-node fields; never assumes `(ny,nx)`).
4. **Coherence comes from conditioning; per-tile white is independent, not shared** (proven by the per-tile full-covariance oracle).
5. **The coherent sampler is topology-agnostic**; the tree/separator requirement is removed; any remaining precondition asserted with a negative control.
6. **Certified by a positive control measuring the contracted property** (cross-seam derived-quantity parity + joint covariance) on **genuinely-distinct** tiles — never an incidental property, never a degenerate fixture.
7. **Correct-or-honestly-bounded, never silently wrong**: if the pre-drawn-joint draw is approximated at scale, the residual is measured and recorded (conservative `known_bias`).
8. **GMRF coherence stays representation-native and projection-agnostic** (same `GMRFFactor`/`posterior_cov_columns` hooks; no grid/projection assumption), so FEM inherits it.
9. **FEM is a global/shared-node mesh** (tiles are node subsets sharing overlap nodes; coincident-node conditioning survives); per-tile meshes deferred.
10. **Exact marginal variance via Takahashi selective inversion**; off-node read-off via `diag(W Σ Wᵀ)` with the FEM-basis `W`, never an interpolated variance map.
11. **Determinism preserved** (independent per-tile white, the joint-strip field, any new randomness are deterministic, order-independent, recorded).

The two generalizations (spec §4): the Projection seam made load-bearing (operator + persisted form consume it); and the non-chain sampler = conditioning-by-kriging toward ONE pre-drawn joint field over the overlap-strip network (topology-agnostic; junction-tree noted as the exact fallback, built only if the positive control demands it).

## Out of scope — do NOT build (spec §6)

Per-tile independent meshes (global/shared-node only); the junction-tree sampler (fallback only, unless the positive control demands it); full coastline/irregular-domain production (the boundary-extension/adaptive demo is in scope, a production system is not); the autotune loop and any optimizer (Phase 5); additional methods beyond OI + grid-GMRF + FEM-GMRF (+ the trivial degradation method); continuous/tunable ν (fixed α=2); cloud/multi-node; SWOT/2-D swath; recalibration; full-correction double-counting.

**If any of these appears necessary to make Phase 4 work, stop and ask — do not build it.**

## Settled decisions — do NOT silently change (spec §8)

If a settled decision appears wrong during implementation, **surface it as a question and pause; do not silently re-architect.** In particular: the three-stage generalize-under-green sequencing; global/shared-node mesh; the Projection seam consumed by the operator and persisted form; the pre-drawn-joint coherent sampler (junction-tree fallback only); FEM payoff demonstrated, not productionized; topology fix validated on the grid before FEM.

## Engineering standards (carried from Phases 1–3)

- **Build on `sverdrup`; refactor, don't rewrite.** Reuse and relocate the real symbols named above; the precision representation (`GMRFFactor`, selective inverse, `posterior_cov_columns`), the `ReductionStrategy` (`GMRFPrecisionReduction`), and the `CoherentMemberDriver` seam (`select_driver`) are reused. The dependency rule holds: `application → distributions`, one-way; the protocols are untouched.
- **Python (modern):** type hints throughout; `typing.Protocol`/ABCs for the `Projection` and `CoherentMemberDriver` seams; `dataclasses` for value objects.
- **DRY, single-responsibility.** No discretization leaks into the protocol spine; the coherence driver dispatches on `sampler_spec`, never method identity; the read-off goes through the `Projection`, never hardcoded.
- **Rigorous TDD — and tests measure the contracted property, not an incidental one (the Phase-3 meta-lesson, now a hard rule).** For each test, state the behavior under test and a concrete bug that would make it fail. The load-bearing Phase-4 tests: the Phase-3 suite stays green through Stage A (regression oracle); the non-chain sampler's distinct-tiles positive control on cross-seam derived-quantity parity + joint covariance, the per-tile full-covariance oracle, and the too-narrow-overlap negative control; the genuine-discretization-swap test (FEM takes no grid-specific path; same representation/reduction/coherence/blend as grid-GMRF); exact FEM marginal variance vs a dense `Q⁻¹` reference on a small mesh; the boundary-extension payoff (FEM removes edge variance inflation the grid shows). Do not assert positivity/marginal-variance where the contract is joint structure; do not validate coherence on a fixture where tiles collapse to identical precisions.
- **Determinism and sparse-linear-algebra discipline.** One sparse Cholesky per operator serves sampling, marginal variance, and `cov`; persist `Q` + permutation, cache the factor; never densify `Q⁻¹` except in small reference tests. Independent per-tile white; deterministic joint-strip field and permutation.
- **BLAS/OpenMP discipline** unchanged: the per-run `processes × threads` knob; the Executor port and `LocalCluster` are unchanged (scale-out address-only).

## Definition of done (spec §7)

**Stage A — generalize under green (gate):** operator + persisted form consume a `Projection` seam; grid dataclasses refactored into use; persistence de-gridded; the full Phase-3 suite and the OI + grid-GMRF blend results reproduce exactly.

**Stage B — non-chain coherent sampler (validation on the grid):** `GmrfJointKrigingSolve` replaces the lon-chain sweep; grid GMRF tiles in 2-D, seam-free, no mid-overlap variance dip, matches a single-tile reference, conservative direction; independent-white + per-tile full-covariance oracles pass; the distinct-tiles positive control passes; the too-narrow-overlap negative control fails loudly; the 1-D chain case still passes.

**Stage C — FEM (discretization swap + payoff):** `FEMMatern` at `Method.solve`; `fem_precision` mass+stiffness assembly; `FEMBasisProjection`; sparse-precision `CovarianceOperator` (`EXACT`); exact selective-inversion marginal variance; provider-driven κ; `SAMPLES + COVARIANCE`; FEM-GMRF blends globally (homogeneous) through the inherited sampler, seam-free and conservative, provenance carrying the sparse-precision tag and any recorded residual; the genuine-discretization-swap test passes (no grid-specific path for FEM); the boundary-extension/adaptive payoff demo removes edge variance inflation; accuracy + calibration fire in OSSE and OSE.

## Data and environment notes

- **Spec location:** `./phase4_scope_spec.md` (authoritative). **Codebase:** the existing `sverdrup` repo (Phases 1–3, green, HEAD `31a58c6`).
- **New dependency:** a triangulation/Delaunay mesh library for Stage C; name it in the plan and add it under the existing extras/optional-deps convention.
- **Data discipline (Phase-1 "Decision B"):** real ODC adapter (no data mocks), scoped footprint during development (do not pull the full ~33 GB global set into the dev/test loop), committed small fixtures, opt-in oracle and opt-in global runs. Same ODC NATL60 OSSE and OSE paths; FEM validation at the regional/global scopes the blend was proven at.
- **Target environment:** single Linux machine, 64 CPUs; `dask.distributed` + `LocalCluster`; scale-out address-only behind the unchanged Executor port.

## When to ask vs proceed

Ask, and pause, when: a decision is genuinely ambiguous in the spec; you hit a real blocker; something appears to require an out-of-scope item; a settled decision looks wrong; the Stage-A refactor cannot keep the Phase-3 suite green (the generalization is changing behavior — stop and surface it, do not adjust the tests to pass); the non-chain sampler's positive control cannot be met (which may mean the pre-drawn-joint residual is unacceptable and the junction-tree fallback is needed — surface it, do not ship a silently-wrong sampler); or FEM cannot meet the seam-free / conservative gate. Otherwise proceed within the plan once approved. Prefer a clarifying question over a scope-expanding assumption.
