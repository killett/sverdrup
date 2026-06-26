You are building **Phase 2** of `sverdrup`: the tiling/blending layer that makes the framework global. It decomposes the globe into overlapping tiles, runs any mapping method per tile through the existing executor, and stitches the per-tile predictive distributions — estimate *and* uncertainty *and* ensemble samples — into one seam-free global product, then evaluates it honestly.

**The complete, settled specification is in `phase2_scope_spec.md` in this repo. Read it in full before doing anything else. It is the source of truth. This prompt foregrounds the parts that must not be missed; on any conflict, the spec governs, and if you believe the spec itself is wrong, raise it as a question rather than diverging.**

The requirements are settled — both brainstorm checkpoints are closed. **Do not re-gather requirements or re-open scope.** Use the **brainstorming skill (from superpowers)** to turn the settled spec into a concrete *implementation plan and architecture* — aim the brainstorming at *how to build this on the existing codebase*, not *what to build*.

## Workflow — follow in order

1. **Read `phase2_scope_spec.md` in full**, then **read the existing `sverdrup` codebase** to ground the plan in the real Phase-1 seams (`GridSpec.window()`, the Executor port, the `Persisted` distribution, the `ParameterProvider`, the derived-quantity operators, the evaluator registry, the three-way split). If the spec is not present in the repo, stop and ask for it.
2. **Brainstorm and produce an implementation plan. Write no implementation code in this step.** Cover: where each new piece lives (tiling in `application/`; blend operator and coherent sampler in `domain/` beside the derived-quantity operators); the concrete realization of each interface in the spec (§5 — illustrative contracts, not prescribed internals); how you reuse the Phase-1 seams rather than reinvent them; the build order; the test strategy (especially the seam-free and no-variance-dip tests); exactly how Stage A (the regional proving milestone) wires together; and the scoped-footprint data plan. The plan must respect "decide the abstractions now, prove regionally first, defer true-global execution."
3. **Present the plan and STOP. Await explicit approval before implementing.**
4. **On approval, implement incrementally and test-first**, in small reviewable commits, building toward Stage A as the integration gate. Do not begin Stage B (true global) until Stage A passes.
5. **Validate against the definition of done** (§7): Stage A (regional blend matches single-tile within tolerance, no seam, conservative direction, withheld-point eval in overlaps, provenance, both withholding exemplars), then Stage B (global, projection-mixed, area-weighted, opt-in).

## Non-negotiable invariants (spec §3 — Phase-1 invariants 1–10 still bind; these add the blend-specific ones)

1. **Blend combines `Persisted` distributions, not live operators.** The live Cholesky exists only on-worker, before persistence; after the gather, only `Persisted` reps exist. (Biggest single constraint.)
2. **Hand-off, never fuse.** In a core, use that tile's answer; in an overlap, crossfade via a partition-of-unity weight from one tile to the neighbor. Never combine two tiles' information into a sharper estimate — that is what makes double-counting impossible.
3. **Coherence makes the hand-off valid.** Crossfade *coherent* sample fields; because white-noise conditioning makes the constituents agree in the overlap (correlation ≈ 1), the crossfaded variance does not dip at mid-overlap. Q1 (hand-off) and Q2 (coherence) are coupled — coherence is a precondition for honest hand-off uncertainty.
4. **Distribution-correct blending.** Output is a valid `PredictiveDistribution` on the union support; never interpolate a marginal-variance map (Phase-1 invariant 7), now in the overlap and across projections.
5. **Scale-aware halos.** Halo = a user-configurable multiple `k` of the *local*, latitude-varying correlation length (~100 km high-latitude to ~800 km equatorial), at least the derived-quantity stencil radius; never a single global value. Read the correlation field through the Phase-1 `ParameterProvider`.
6. **Eval-point predictives computed on-worker** at withheld points in overlaps, carried forward; never reconstructed from the gridded blend.
7. **Unified blend over support.** One blend operator handles a `GridSpec` or a `PointSet`; the seam math lives in one place.
8. **Coherent samples via shared global driving noise.** A globally-indexed, deterministically-seeded white-noise field drives every tile's sampler so realizations agree in overlaps; when a method can't support it, degrade and record the lost coherence — never emit a hidden seam.
9. **Blend is a provenance transform with honest fidelity.** The typed chain gains a `BlendTransform` with its conservative `known_bias`; blended fidelity is `BLENDED` and never claims to beat the constituents' `LOW_RANK`.
10. **Conservative residual, bounded and recorded.** Finite halos miss a thin far tail, so answers are *almost* identical; the residual errs conservative (never overconfident), shrinks with `k`, and is recorded — never silently dropped.
11. **Area-weighted global aggregation** using true spherical `cell_area`; no unweighted global means.
12. **Pluggable, blocked withholding** producing train / validation / (optional buffer-discard) / test from grouped or blocked structure. Random point holdout is forbidden.

The blend mechanism that ties these together (spec §4): a partition-of-unity crossfade of coherent samples — analytic moment crossfade for the cheap marginal mean/variance path, coherent-sample crossfade for samples, covariance, and cross-seam derived quantities.

## Out of scope — do NOT build (spec §6)

Global execution before the regional blend is proven (do not pull the ~33 GB global dataset into the dev/test loop); additional mapping methods (still Method 0 + OI); cloud/multi-node execution adapters (still `LocalCluster`, address-only scale-out); the autotune loop and 2-D *learned* parameter fields (the latitude-varying correlation length is a configured provider, not learned); SWOT/2-D swath; recalibration machinery; full correction of shared-observation double-counting (Phase 2 uses bound-and-record / hand-off; leave room to add correction later only if Stage A shows the residual is unacceptable).

**If any of these appears necessary to make Phase 2 work, stop and ask — do not build it.**

## Settled decisions — do NOT silently change (spec §8)

If a settled decision appears wrong during implementation, **surface it as a question and pause; do not silently re-architect.** In particular: tiling=orchestration in `application/` and blend+sampler=representation-math in `domain/`; bound-and-record hand-off (never fuse); white-noise conditioning; `k`-multiple latitude-varying halos; unified blend over support; cross-projection blend via regridding; pluggable blocked withholding; area-weighted aggregation; regional proving before global.

## Engineering standards (carried from Phase 1)

- **Build on `sverdrup`, reuse the Phase-1 seams.** Reuse `GridSpec.window()`, the Executor port (emit many units, no re-granularization, scale-out is address-only), the `Persisted` distribution, the `ParameterProvider`, the derived-quantity operators, the evaluator registry, and the three-way split. Do not reinvent them. Tiling lives in `application/`; the blend operator and coherent sampler live in `domain/`.
- **Python (modern):** type hints throughout; `typing.Protocol`/ABCs for interfaces; `dataclasses` for value objects.
- **Ports-and-adapters preserved.** No new boundary work beyond what the spec names; the data-source, result-sink, and Executor ports are unchanged.
- **DRY, single-responsibility, small modules.** No method-specific detail leaks into the blend (it blends representations, not methods); no orchestration leaks into the domain-level blend/sampler.
- **Rigorous TDD.** For each test, state the behavior under test and a concrete bug that would make it fail. The load-bearing Phase-2 tests: blend two overlapping `Persisted` distributions in isolation (no cluster, no I/O) and assert a seam-free union; assert no mid-overlap variance dip; assert the conservative direction (blended σ ≥ single-tile σ); assert coherent samples are continuous across seams; assert withheld-point eval in overlaps; assert random point holdout is rejected. Use real assertions; avoid over-mocking; the Stage-A milestone is the integration gate.
- **Determinism and reproducibility.** The global white-noise field is indexed by a tile-independent global spatial lattice × member_index (via the existing `derive_seed`), so the same global cell yields the same noise regardless of which tile solves it. Every product reproducible from its provenance.
- **BLAS/OpenMP discipline** unchanged: the per-run `processes × threads` knob sets `OMP_NUM_THREADS` / `OPENBLAS_NUM_THREADS` / `MKL_NUM_THREADS` per worker; process-level parallelism is the unit.
- **Performance honesty (invariants).** Never materialize a dense global covariance; the blend operates on `Persisted` reps and regenerates coherent samples on demand; the persisted blended form is sufficient statistics + generator with `BLENDED` fidelity.

## Definition of done (spec §7)

**Stage A — prove the blend regionally (the gate), on the same OSSE truth and OSE withheld data as Phase 1:** a handful of overlapping regional tiles (core + scale-aware halo) solved through the existing `LocalCluster` Executor and blended; the blended map matches a single-tile reference within tolerance with no seam in mean or uncertainty and blended error bars never smaller than the reference; coherent samples seam-free with no mid-overlap variance dip; withheld-point evaluation in overlaps fires in both OSSE and OSE; provenance carries the `BlendTransform` (conservative `known_bias`, `BLENDED` fidelity); both withholding exemplars exercised and random point holdout rejected by construction.

**Stage B — go global (only after Stage A passes):** projection-mixed partition (polar-stereographic caps + lon/lat mid-latitudes), real polar-void behavior tested on a real polar tile, area-weighted global aggregation, on global data (2023a OSE ≈ 33 GB) as an opt-in run under the scoped-footprint data discipline.

## Data and environment notes

- **Spec location:** `./phase2_scope_spec.md` (authoritative). **Codebase:** the existing `sverdrup` repo (Phase 1).
- **Data discipline (Phase-1 "Decision B"):** real ODC adapter (no data mocks), scoped data footprint during development (do not pull the full ~33 GB global set into the dev/test loop), committed small fixtures for the blend tests, opt-in oracle and opt-in global runs.
- **Data:** the same ODC NATL60 OSSE and OSE paths as Phase 1 for Stage A; the global 2023a OSE set for the opt-in Stage-B run.
- **Target environment:** single Linux machine, 64 CPUs; `dask.distributed` + `LocalCluster`; scale-out remains address-only behind the unchanged Executor port.

## When to ask vs proceed

Ask, and pause, when: a decision is genuinely ambiguous in the spec; you hit a real blocker; something appears to require an out-of-scope item; a settled decision looks wrong; or Stage A cannot meet tolerance with no seam (which may indicate the conservative residual is unacceptable and the bound-and-record vs full-correction decision needs revisiting with the project owner). Otherwise proceed within the plan once approved. Prefer a clarifying question over a scope-expanding assumption.
