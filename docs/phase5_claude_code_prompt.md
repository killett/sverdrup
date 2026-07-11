You are building **Phase 5** of `sverdrup`: the **autotune loop** — a method-agnostic tuner that searches a method's parameter space against the real, published 2021a SSH-mapping OSE challenge objective, navigates the objectives as a *constrained* problem (resolution primary; RMSE and calibration as hard bars), and respects the cross-tile coherence feasibility boundary as a *hard barrier* in the global-coherent mode.

**The complete, settled specification is in `phase5_scope_spec.md` in this repo. Read it in full before doing anything else. It is the source of truth. This prompt foregrounds the parts that must not be missed; on any conflict, the spec governs, and if you believe the spec itself is wrong, raise it as a question rather than diverging.**

The requirements are settled — both brainstorm checkpoints are closed. **Do not re-gather requirements or re-open scope.** Use the **brainstorming skill (from superpowers)** to turn the settled spec into a concrete *implementation plan and architecture* — aimed at *how to build this orchestration layer on the existing seams*, not *what to build*.

## The two most important rules

1. **Prove the clean case first, in three stages.** **(A)** the tuner core loop on **OI against the challenge** — single-tile, so the feasibility constraint does *not* bind; prove the whole loop here. **(B)** **grid-GMRF per-gridpoint** against the challenge — still single-tile, still unconstrained; method-generality on a different `parameter_space()`; add Bayesian optimization as a strategy only once A is green. **(C)** **global GMRF coherent** — the only mode where the `FeasibilityPredicate` binds. Do not let the constraint complicate Stages A–B (it is `True` there by construction); do not add BO before A is green; do not start C until B is green.
2. **Three disciplines are mechanical, not aspirational.** The feasibility constraint is a **hard barrier** (infeasible trials excluded before any solve/score — never a soft penalty that lets the optimizer trade into the broken region). Coherence is a **`JOINT`-tagged feasibility constraint, never an objective term**, and wherever measured is reduced **worst-case-localized, never aggregate/median**. The challenge **CryoSat-2 locked test is touched exactly once**, at acceptance — the search scores only a blocked non-CryoSat-2 validation split.

## Workflow — follow in order

1. **Read `phase5_scope_spec.md` in full**, then **read the real source** you will build on: `validation/run.py` (the single-tile OI challenge driver — extend it to the tuned method and add a GMRF variant), `validation/their_eval.py` (`their_eval.score → (µ, σ, λx)` — the acceptance gate; the vendored `vendor/2021a_SSH_mapping_OSE` submodule it wraps), `methods/oi.py` and `methods/gmrf.py` (`parameter_space()` — scalar boxes), `eval/` (the evaluator registry — you will add a `property_kind` tag), `application/withholding.py` (`LeaveOneMissionOut`, `PerMissionTemporalFraction`) and `splits.py` (the three-way split), `application/uow.py`/`solve.py`/`pipeline.py` (the UoW trial granularity and the executor), `tests/test_core_authoritative_gate.py` (the measured `core/range ≳ 25` bound). If the spec is not present, stop and ask for it.
2. **Brainstorm and produce an implementation plan. Write no implementation code in this step.** Cover: the `application/tuning/` package (the `SearchStrategy` seam + a simple Sobol/random instance; the `FeasibilityPredicate` seam + the `CoherenceFeasibility` default; the constrained-objective ranking); the `property_kind` tag added across `eval/`; how trials are emitted as existing UoW through the executor; how the split maps onto the challenge (blocked validation via internal `eval/`, CryoSat-2 locked test via `their_eval`); how acceptance reuses `validation/`; and exactly how Stage A wires end-to-end. Name where BO will slot in (Stage B) without building it yet.
3. **Present the plan and STOP. Await explicit approval before implementing.**
4. **On approval, implement incrementally and test-first.** Small reviewable commits. Honor the stage gates above.
5. **Validate against the definition of done** (§7): Stage A (tuned OI lands DUACS-class; the loop is proven), Stage B (GMRF through the identical loop; method-agnostic), Stage C (the tuner provably respects the boundary; the feasibility-vs-resolution tradeoff is surfaced).

## Non-negotiable invariants (spec §3 — all prior-phase invariants still bind; these add the tuner specifics)

1. **The tuner never sees truth or the locked test during search.** Per-trial scoring on a blocked validation split (internal `eval/`); the CryoSat-2 locked test via `their_eval.score` is touched once at acceptance. Random point holdout forbidden.
2. **The objective vector is `MARGINAL` metrics only** (RMSE, calibration coverage/χ²/CRPS, λx); `JOINT` properties (coherence) never enter it.
3. **Feasibility is a hard barrier, not a soft penalty** — infeasible trials excluded before any solve/score.
4. **The feasibility constraint is mode-specific and capability-conditional** — binds only for sparse-precision when `SAMPLES`/`COVARIANCE` is required (global-coherent mode); single-tile and per-gridpoint modes are unconstrained.
5. **The feasibility predicate is pluggable**, keyed on the tiling infrastructure; the decomposition-redesign relaxes it without touching the tuner.
6. **Coherence is reduced worst-case-localized, never aggregate/median**, wherever measured.
7. **The `SearchStrategy` is pluggable and objective-agnostic**, emitting existing UoW trials through the executor (address-only scale-out); simple-first, then BO.
8. **Navigation is constrained, not scalarized** — configurable primary (default λx) + interpretable thresholds (`µ_RMSE`, calibration coverage); calibration is a hard bar, never traded.
9. **Acceptance is the real challenge harness**, every stage (`their_eval.score` vs the leaderboard).
10. **Metrics are contract-grounded** — calibration against the posterior's own contract; a reference-dependent metric value is a flagged smell.
11. **Determinism** — trials reproducible from `(window, method, params, split, seed)`; search randomness seeded and recorded.
12. **The tuner is method-agnostic** — consumes `parameter_space()` per method; scalar parameters only (fields deferred).

The formulation (spec §4): per trial, **feasibility gate → solve+score (marginal evaluators only, on the validation split) → constrained ranking**; coherence is the gate, never a score; the locked test is untouched until the single acceptance run.

## Out of scope — do NOT build (spec §6)

Latitude-varying parameter fields (named later extension); the decomposition-redesign (owner-owned; the tuner consumes a relaxed predicate, it does not build one); FEM as a tuner target (inherits the boundary); BO as the *initial* strategy (added after the simple loop is green); scalarized/weighted-sum objectives; soft feasibility penalties; joint/coherence metrics in the objective vector; additional methods beyond OI + grid-GMRF (+ the un-tunable trivial method); cloud/multi-node; SWOT; recalibration.

**If any of these appears necessary to make Phase 5 work, stop and ask — do not build it.**

## Settled decisions — do NOT silently change (spec §8)

If a settled decision appears wrong during implementation, **surface it as a question and pause; do not silently re-architect.** In particular: the three-stage sequencing (OI-against-challenge clean first); constrained-not-scalarized navigation with λx primary and calibration/RMSE as hard bars; the hard-barrier mode-specific pluggable `FeasibilityPredicate`; the `property_kind` tag making coherence a constraint not an objective; the CryoSat-2 locked test touched once via `their_eval`; simple-strategy-then-BO; scalar-only.

## Engineering standards (carried from Phases 1–4)

- **Build on `sverdrup`; the tuner is orchestration in `application/tuning/`.** It drives existing UoW trials through the executor, consumes the `eval/` registry and the `validation/` harness, and does **no** uncertainty math and **no** changes to methods/distributions/protocols beyond adding the `eval/` `property_kind` tag. Dependency rule: `application → eval`/`distributions`/`methods`, one-way.
- **Python (modern):** type hints throughout; `typing.Protocol`/ABCs for the `SearchStrategy` and `FeasibilityPredicate` seams; `dataclasses` for value objects (trial, scores, history).
- **DRY, single-responsibility.** Nothing about a method's parameter shape is baked into the search; coherence cannot reach the objective by construction (the `property_kind` tag).
- **Rigorous TDD — and tests measure the contracted property (the Phase-4 meta-lesson, still a hard rule).** For each test, state the behavior under test and a concrete bug that would make it fail. The load-bearing Phase-5 tests: Stage A end-to-end (tuned OI lands DUACS-class via `their_eval`); the locked test is touched exactly once (assert no `their_eval` call during search); method-agnosticism (the same `SearchStrategy`/objective/acceptance drive OI and GMRF unchanged); the **hard barrier** (assert no solve/score occurs for an infeasible `(range, tile_geometry)` — not merely that it scores poorly); coherence reduced worst-case-localized (a test that an aggregate coherence score cannot enter the objective); a relaxed `FeasibilityPredicate` widens the feasible region without touching the tuner. Do not let a `JOINT` metric reach the objective; do not assert feasibility via a soft score.
- **Determinism.** Seed the search (Sobol/random/BO); record the seed; trials reproducible from the UoW tuple.
- **BLAS/OpenMP + executor discipline** unchanged: the per-run `processes × threads` knob; trials are existing UoW through the unchanged executor port; `LocalCluster`; scale-out address-only.

## Definition of done (spec §7)

**Stage A — tuner core loop on OI against the challenge (single-tile, no constraint):** `SearchStrategy` (Sobol/random) emits UoW trials; per-trial blocked-validation scoring via internal `eval/` (marginal only); constrained objective (λx primary; `µ_RMSE` + calibration-coverage thresholds; feasibility `True` in single-tile mode); acceptance via `their_eval.score` on the CryoSat-2 locked test, touched once. Gate: tuned OI lands DUACS-class; the whole loop is proven.

**Stage B — grid-GMRF per-gridpoint against the challenge (single-tile, no constraint):** the identical loop with GMRF's `parameter_space()`; BO added as a `SearchStrategy` instance (Stage-A loop green first). Gate: GMRF tuned through the same loop, sensible challenge score; the method-agnosticism test passes (no OI parameter-shape baked in).

**Stage C — global GMRF coherent (the boundary binds):** `CoherenceFeasibility` (`core/range ≳ 25`) gates trials as a hard barrier. Gate: the tuner provably never scores an infeasible trial; the global product is valid wherever it claims coherence, gated worst-case-localized; a relaxed predicate widens the feasible region without touching the tuner; and the feasibility-vs-resolution tradeoff (achievable λx for a valid global coherent product as a function of the feasible `(range, tile)` region) is surfaced as the input to the owner's redesign decision. (Stage C proves the tuner *respects and quantifies* the boundary; it does not attempt DUACS-class global coherent products at operational range — the boundary forbids that until the redesign.)

## Data and environment notes

- **Spec location:** `./phase5_scope_spec.md` (authoritative). **Codebase:** the existing `sverdrup` repo (Phases 1–4; Phase 4 Stage-A-complete; HEAD `35befdd`).
- **Vendored challenge:** `vendor/2021a_SSH_mapping_OSE` (pinned submodule) — ensure it is initialized; `their_eval.score` is the published-leaderboard eval definition (read CryoSat-2 holdout → interp onto track → area-binned RMSE `(µ, σ)` → spectral `λx`).
- **Data discipline (Phase-1 "Decision B"):** real ODC adapter (no data mocks), scoped footprint during development (do not pull the full ~33 GB global set into the dev/test loop), committed small fixtures, opt-in oracle and opt-in global runs. The challenge box (Gulf Stream) is the OI/GMRF proving scope; the global-coherent stage uses the existing tiled-global scopes.
- **Target environment:** single Linux machine, 64 CPUs; `dask.distributed` + `LocalCluster`; scale-out address-only behind the unchanged executor port.

## When to ask vs proceed

Ask, and pause, when: a decision is genuinely ambiguous in the spec; you hit a real blocker; something appears to require an out-of-scope item; a settled decision looks wrong; tuned OI cannot reach DUACS-class on the challenge (which may indicate a harness or objective-definition problem worth surfacing, not silently working around); or Stage C reveals the feasible region is so narrow that global coherent products are impractical at any useful resolution (surface this as the redesign-decision input it is — do not loosen the feasibility predicate to manufacture a result). Otherwise proceed within the plan once approved. Prefer a clarifying question over a scope-expanding assumption.
