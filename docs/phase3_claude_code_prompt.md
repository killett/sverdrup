You are building **Phase 3** of `sverdrup`: adding a genuinely-different method — a regular-grid Matérn **GMRF (sparse precision)** — to validate that the method-agnostic blend is truly representation-agnostic, and generalizing the representation/coherence/persistence layer so a sparse-precision representation is first-class alongside OI's low-rank, without re-baking OI's shape into the spine.

**The complete, settled specification is in `phase3_scope_spec.md` in this repo. Read it in full before doing anything else. It is the source of truth. This prompt foregrounds the parts that must not be missed; on any conflict, the spec governs, and if you believe the spec itself is wrong, raise it as a question rather than diverging.**

The requirements are settled — both brainstorm checkpoints are closed. **Do not re-gather requirements or re-open scope.** Use the **brainstorming skill (from superpowers)** to turn the settled spec into a concrete *implementation plan and architecture* — aimed at *how to refactor and extend this codebase*, not *what to build*.

## The single most important sequencing rule

**Generalize under green, then extend.** Do the architecture generalization (relocate the coherence seam, representation-tag the persisted form, generalize the reduction boundary) by refactoring the *existing OI/low-rank path* onto it **first**, keeping the **full Phase-2 suite (129 passed / 2 skipped) green at every step** as the regression oracle — OI through the new seam must reproduce Phase-2 results exactly. **Only after that gate is green do you add the GMRF method.** Do not build GMRF and the generalization simultaneously; that is how the working system gets silently broken.

## Workflow — follow in order

1. **Read `phase3_scope_spec.md` in full**, then **read the real source** you will refactor: `core/method.py`, `core/distribution.py` (the `Method` / `PredictiveDistribution` / `CovarianceOperator` protocols — all already representation-agnostic), `distributions/coherent.py` (the bypassed `StructuredNoiseSource` / `MemberSeededZr` and the free function `coherent_structured_field`), `distributions/blend.py` (`_coherent_member`, `BlendInput`, the cheap-path moment crossfade), `distributions/persisted.py` (`PersistedFields` / `PersistedDistribution` / `PersistedPoints`, `sampler_spec`, `reduce_with_basis`, `eval_rows_in_grid_basis`), `application/solve.py` (the hardcoded reduction), and `methods/oi.py` (the plug-in pattern GMRF mirrors). If the spec is not present, stop and ask for it.
2. **Brainstorm and produce an implementation plan. Write no implementation code in this step.** Cover, in order: (Stage A) the OI-first refactor onto the relocated `CoherentMemberDriver` seam, the representation-tagged persisted form, and the per-operator `to_persisted` reduction, with the Phase-2 suite as the regression gate; then (Stage B) the GMRF method core (regular-grid Matérn precision, sparse Cholesky, exact selective-inversion marginal variance, provider-driven κ, off-grid eval-point predictives via the W interpolation operator); then (Stage C) the degradation-path wiring and the nonstationary-κ demo. Identify exactly which existing tests pin the OI behavior you must preserve, and which new tests prove each invariant.
3. **Present the plan and STOP. Await explicit approval before implementing.**
4. **On approval, implement incrementally and test-first.** Keep the Phase-2 suite green through the entire Stage-A refactor. Small reviewable commits. Do not start Stage B until Stage A's regression gate is green; do not start Stage C until Stage B passes.
5. **Validate against the definition of done** (§7): Stage A (Phase-2 suite green through the refactor), Stage B (GMRF validates the blend; genuine-first-class test passes), Stage C (degradation exercised; nonstationary demo).

## Non-negotiable invariants (spec §3 — Phase-1 invariants 1–10 and Phase-2 invariants 1–12 still bind; these add the Phase-3 specifics)

1. **Protocols stay representation-agnostic.** Do not modify `Method` / `PredictiveDistribution` / `CovarianceOperator` to accommodate GMRF; GMRF implements them as they stand.
2. **Coherence driver selected by representation tag (`sampler_spec`), never method identity.**
3. **Persisted form is representation-tagged**; sparse-precision is first-class beside low-rank+diagonal; `BlendInput.distribution` widens to the abstract `PredictiveDistribution`.
4. **Reduction is a per-operator strategy** (`to_persisted`) for both the gridded block and the on-worker eval-point predictives; no method special-casing in `application/solve.py`.
5. **GMRF coherence is native via shared global white noise**: `mean + L⁻ᵀ w` with `w` the existing `diagonal_noise` global-lattice field; no QR-basis trick; the only residual is the `Q_i ≠ Q_j` halo-agreement term (conservative, recorded).
6. **Exact GMRF marginal variance via Takahashi selective inversion** (not sampled); operator `fidelity = EXACT`; keeps calibration honest; one sparse Cholesky `L` serves sampling, marginal variance, and `cov`.
7. **OI path preserved under the generalization** — the green Phase-2 suite is the regression oracle; generalize under green, then extend.
8. **Degradation path exercised end-to-end** through the tiled blend, coherence loss recorded in provenance (Phase-2 invariant 8) — closing the Phase-2 gap.
9. **Homogeneous representation per blend** (Phase-3 scope); mixing is structurally allowed but takes the degradation path; cross-representation coherent maps are out of scope.
10. **Nonstationary-capable κ via the `ParameterProvider`** (`LatitudeVaryingProvider` precedent); stationary-first, then a latitude-varying demo; ν fixed to an integer α (clean stencil).
11. **Determinism preserved**: global-lattice white noise (order-independent), deterministic fill-reducing permutation and recorded.

The generalization mechanism (spec §4): relocate the coherence decision from the bypassed `StructuredNoiseSource` to a `CoherentMemberDriver` at the `_coherent_member` level with three instances (low-rank-shared-basis = repackaged `coherent_structured_field` + diagonal; gmrf-precision-solve; perturb-ensemble-degradation), retiring the naive `MemberSeededZr`; the cheap-path moment crossfade is already representation-agnostic and unchanged.

## Out of scope — do NOT build (spec §6)

The autotune loop and any optimizer (Phase 4; `parameter_space()` exists, no tuning); additional methods beyond OI + GMRF (+ the existing trivial for degradation); FEM meshing / coastline-following; cross-representation coherent blending; tunable/continuous ν (fixed integer α); cloud/multi-node; SWOT/2-D swath; recalibration; full-correction double-counting.

**If any of these appears necessary to make Phase 3 work, stop and ask — do not build it.**

## Settled decisions — do NOT silently change (spec §8)

If a settled decision appears wrong during implementation, **surface it as a question and pause; do not silently re-architect.** In particular: regular-grid GMRF (not FEM); exact selective-inversion σ; provider-driven nonstationary-capable κ (stationary-first + demo); homogeneous-per-blend; the relocated `CoherentMemberDriver` seam dispatched by representation tag; representation-tagged persistence; per-operator reduction; generalize-under-green sequencing.

## Engineering standards (carried from Phases 1–2)

- **Build on `sverdrup`; refactor, don't rewrite.** Reuse and relocate the real symbols named above. The dependency rule holds: `application/ → distributions/`, one-way; the protocols are untouched.
- **Python (modern):** type hints throughout; `typing.Protocol`/ABCs for interfaces (`CoherentMemberDriver`, the extended `CovarianceOperator`); `dataclasses` for value objects (`PrecisionFields`).
- **DRY, single-responsibility.** No representation leaks into the protocol spine; the coherence driver dispatches on `sampler_spec`, never on method identity; the crossfade stays representation-agnostic.
- **Rigorous TDD.** For each test, state the behavior under test and a concrete bug that would make it fail. The load-bearing Phase-3 tests: the Phase-2 suite stays green through the Stage-A refactor (regression oracle); GMRF blended map seam-free with no mid-overlap variance dip and matching a single-tile GMRF reference (conservative direction); the genuine-first-class test (`sampler_spec="sparse-precision"` survives end-to-end, no low-rank factor materialized for GMRF); exact GMRF marginal variance vs a dense `Q⁻¹` reference on a small grid; the degradation path records coherence loss with no silent seam; calibration fires on GMRF in OSSE and OSE. Use real assertions; avoid over-mocking.
- **Determinism and reproducibility.** GMRF sampling uses the global-lattice white noise; the fill-reducing permutation is deterministic; every product reproducible from its provenance.
- **Sparse-linear-algebra discipline.** One sparse Cholesky `L` per operator serves sampling (`L⁻ᵀ w`), marginal variance (Takahashi selective inverse), and `cov` blocks; persist `Q` + permutation, cache the factor on use; never densify `Q⁻¹` except in small-grid test references.
- **BLAS/OpenMP discipline** unchanged: the per-run `processes × threads` knob; process-level parallelism; the Executor port and `LocalCluster` are unchanged (scale-out remains address-only).

## Definition of done (spec §7)

**Stage A — generalize under green (gate before GMRF):** relocate the coherence seam, representation-tag the persisted form, generalize the reduction boundary, refactor the existing OI path onto all three; the full Phase-2 suite (129 passed / 2 skipped) stays green — OI through the new seam reproduces Phase-2 exactly.

**Stage B — add the GMRF method (validation):** regular-grid Matérn GMRF at `Method.solve`; sparse-precision `CovarianceOperator` (`EXACT`); sparse Cholesky core; exact selective-inversion marginal variance; provider-driven κ; `SAMPLES + COVARIANCE`; gridded + on-worker eval-point predictives (W-interpolation off-grid). The method-agnostic blend runs GMRF globally through the gmrf-precision-solve driver: seam-free coherent samples (native shared-`w`, no QR trick), no mid-overlap variance dip, matches a single-tile GMRF reference within tolerance, conservative direction, provenance carries `BlendTransform` + the sparse-precision tag; accuracy + calibration fire in OSSE and OSE; the genuine-first-class test passes (no low-rank reduction of GMRF anywhere).

**Stage C — degradation path + nonstationary demo:** the perturb-ensemble degradation driver runs end-to-end through the tiled blend (deterministic method) with coherence loss recorded and no silent seam; a latitude-varying-κ GMRF case is demonstrated.

## Data and environment notes

- **Spec location:** `./phase3_scope_spec.md` (authoritative). **Codebase:** the existing `sverdrup` repo (Phases 1–2, green).
- **Data discipline (Phase-1 "Decision B"):** real ODC adapter (no data mocks), scoped footprint during development (do not pull the full ~33 GB global set into the dev/test loop), committed small fixtures, opt-in oracle and opt-in global runs. Use the same ODC NATL60 OSSE and OSE paths as before; GMRF validation runs at the same regional/global scopes the blend was proven at.
- **Target environment:** single Linux machine, 64 CPUs; `dask.distributed` + `LocalCluster`; scale-out remains address-only behind the unchanged Executor port.

## When to ask vs proceed

Ask, and pause, when: a decision is genuinely ambiguous in the spec; you hit a real blocker; something appears to require an out-of-scope item; a settled decision looks wrong; the Stage-A refactor cannot keep the Phase-2 suite green (which means the generalization is changing OI behavior — stop and surface it, do not adjust the tests to pass); or GMRF cannot meet the seam-free / conservative-direction gate. Otherwise proceed within the plan once approved. Prefer a clarifying question over a scope-expanding assumption.
