# Phase-5 Scope Specification
### The autotune loop: a method-agnostic constrained tuner against the real challenge objective (`sverdrup`)

**Status:** Settled. Both brainstorm checkpoints are closed; no open Phase-5 architectural questions remain.
**Purpose:** Single authoritative reference for the Phase-5 build. Supersedes the Phase-5 scoping conversation; self-contained; the basis from which the Phase-5 Claude Code prompt is written. Mirrors `phase1`–`phase4_scope_spec.md`.
**Builds on:** the real `sverdrup` codebase at the current HEAD (`35befdd`), verified by source read. Phase 5 adds an orchestration layer; it does not start over, and it does not modify the methods, distributions, or protocols beyond adding evaluator tags. References real symbols: `validation/run.py`, `validation/their_eval.py` (`score`), the vendored `vendor/2021a_SSH_mapping_OSE` submodule, `ParameterSpace`/`parameter_space()`, the `eval/` registry, `LeaveOneMissionOut`/`PerMissionTemporalFraction`, the UoW `(window, method, params, split, seed)`.
**Governing discipline:** Prove the clean case first (OI against the challenge, no feasibility constraint). Keep the feasibility boundary a hard barrier, never a tradeable term. Don't build Bayesian optimization, parameter fields, or the decomposition-redesign before the loop is green. Owner owns the redesign milestone.

---

## 1. Project north star (context)

The framework ingests heterogeneous nadir altimetry and produces a global gridded SSHA product with rigorous per-gridpoint uncertainty, a method-comparison layer, and an autotune loop. Phases 1–4 built the abstractions, the method-agnostic tiling/blend, a sparse-precision GMRF, and (Stage-A-only) the FEM-readiness refactor — and proved a hard validity boundary on GMRF cross-tile coherent sampling. **Phase 5 is the autotune loop**: a method-agnostic tuner that searches each method's parameter space against a real, published external objective (the 2021a SSH-mapping OSE challenge), respecting the coherence feasibility boundary as a hard constraint. Tuning is the surface that tests whether the framework's seams are genuinely method-general.

---

## 2. Phase-5 objective, scope, and build philosophy

**Objective.** A tuner that searches a method's `parameter_space()`, scores trials with a vector-valued multi-objective evaluator on a blocked validation split, navigates the objectives as a *constrained* problem (resolution primary; RMSE and calibration as hard bars), respects the cross-seam coherence boundary as a *hard feasibility barrier* in the global-coherent mode, and is accepted against the real challenge leaderboard — proven OI-first against the challenge, then extended to grid-GMRF, then to the global-coherent mode where the boundary binds.

**The mode separation (the grounding fact that shapes everything).** The 2021a challenge objective is **single-tile** (`validation/run.py` runs one OI solve per day over the Gulf Stream box; `their_eval.score` returns `(µ_RMSE, σ_RMSE, λx)` vs the leaderboard). A single tile has no seams, so **the coherence feasibility constraint does not bind for the challenge objective.** It binds only when the tuner produces a *global, multi-tile* GMRF product whose whole-field coherent sampling must be valid. So the OI and grid-GMRF stages are free of the constraint; only the global-coherent stage triggers it.

**Scope — exactly what Phase 5 does, in three stages (and nothing else):**
- **Stage A — the tuner core loop on OI against the challenge** (single-tile, no feasibility constraint): the `SearchStrategy` seam, per-trial internal `eval/` scoring on a blocked validation split, the constrained objective, acceptance via `their_eval` on the CryoSat-2 locked test. Gate: tuned OI lands DUACS-class.
- **Stage B — grid-GMRF per-gridpoint against the challenge** (single-tile, no constraint; GMRF means/variances are clean): method-generality on a different `parameter_space()`; BO added as a strategy once Stage A is green.
- **Stage C — global GMRF coherent**: the `FeasibilityPredicate` binds. Gate: the tuner provably respects the boundary (never scores an infeasible trial), the global product is valid wherever it claims coherence (gated worst-case-localized), and the feasibility-vs-resolution tradeoff is surfaced as the input to the owner's redesign decision.

**Method spread (corrected from the Phase-4 spec's assumption).** OI (clean, fully working, unconstrained) and grid-GMRF (means/variances clean; coherent JOINT sampling infeasible at operational multi-tile scale — the tile-count boundary, `docs/superpowers/specs/2026-07-01-stagec-redesign-design.md`). **FEM is deferred and is not a tuner target** — it inherits the same near-improper-mode boundary (the boundary is a property of the SPDE *prior* + sparse obs + tiling, not the grid discretization), so it adds assembly variety but not feasibility variety; it becomes interesting only after the decomposition-redesign lifts the boundary. The two-method spread (OI unconstrained vs GMRF boundary-constrained) is the right generality surface.

**Build philosophy.** Prove the loop on the clean case (OI, no constraint, real external target) before the constraint enters; add BO only once the simple-strategy loop is green; scalar parameters only. Same Phase-1 "Decision B" data discipline (real ODC adapter / vendored challenge submodule, scoped footprint, committed fixtures, opt-in oracle/global). The tuner pipeline is OSE/OSSE-agnostic (identical machinery); the primary external objective is the OSE challenge; OSSE truth remains an oracle diagnostic, never a tuning signal.

---

## 3. Hard constraints (Phase-5 invariants)

Load-bearing; do not optimize away. All prior-phase invariants still bind. These add the tuner specifics.

1. **The tuner never sees truth or the locked test during search.** Per-trial scoring is on a *blocked* validation split (internal `eval/`). The locked test is the challenge's own CryoSat-2 holdout via `their_eval.score`, touched **once** at acceptance. Random point holdout is forbidden (along-track SLA is autocorrelated).
2. **The objective vector is *marginal* metrics only.** RMSE, calibration coverage/χ²/CRPS, λx (effective resolution) — per-gridpoint / spectral properties, aggregated normally. *Joint* properties (cross-seam coherence) never enter the objective.
3. **Feasibility is a hard barrier, not a soft penalty.** Infeasible trials are excluded before any scoring. A penalty would let the optimizer trade into the broken region — exactly the failure the boundary forbids.
4. **The feasibility constraint is mode-specific and capability-conditional.** It binds only for the sparse-precision method when the product requires `SAMPLES`/`COVARIANCE` (the global-coherent mode); per-gridpoint `POINT`/`MARGINAL_VARIANCE` and the single-tile challenge are unconstrained.
5. **The feasibility predicate is pluggable, keyed on the tiling infrastructure.** The decomposition-redesign (owner-owned, §6) relaxes the predicate; the tuner is neither rebuilt nor blocked on it.
6. **Coherence, wherever measured, uses worst-case-localized reduction — never aggregate or median.** It is a constraint gated on strict-min / worst-case localized seam behavior. (The Phase-4 anti-false-green meta-lesson, made mechanical.)
7. **The search strategy is pluggable and objective-agnostic.** It emits UoW `(window, method, params, split, seed)` trials through the existing executor; scale-out is address-only. A simple strategy (Sobol/random over the feasible box) proves the loop; BO is added as a strategy afterward.
8. **Navigation is constrained, not scalarized.** A configurable primary objective + interpretable constraint thresholds — default: maximize resolution (minimize λx) subject to `µ_RMSE ≤` a DUACS-class bar, calibration coverage within tolerance, and (global mode) the feasibility predicate. Calibration is a hard bar, never a term traded against resolution. No opaque weighted-sum scalarization.
9. **Acceptance is the real challenge harness, every stage.** The winning config runs the full challenge map → `their_eval.score` → `(µ, σ, λx)` against the published leaderboard.
10. **Metrics are contract-grounded.** Calibration coverage/χ²/CRPS are defined against the posterior's own promised contract; a metric whose value moves with an externally chosen reference is a flagged smell (the Phase-4 phantom-chasing lesson — the reference is the bug).
11. **Determinism.** Trials are reproducible from `(window, method, params, split, seed)`; any search-internal randomness (Sobol/random/BO) is seeded and recorded.
12. **The tuner is method-agnostic.** It consumes `parameter_space()` per method; nothing about OI's or GMRF's parameter shape is baked in. Scalar parameters only in Phase 5; latitude-varying fields are a named extension (§6).

Carry-forward invariants unchanged: conservative-direction-and-record; never interpolate a variance map; the dependency rule (`application → eval`/`distributions`/`methods`, one-way); Decision-B data discipline; the protocols stay untouched.

---

## 4. The formulation (how invariants 2–10 cohere)

Stated once, because it is the heart of Phase 5:

A trial is `(method, params)` evaluated on a window/split through the existing UoW. The tuner processes each trial in a fixed order: **(1) feasibility gate** — `FeasibilityPredicate(params, tile_geometry, required_capabilities)`; if infeasible, the trial is excluded *before any solve or score* (invariant 3); **(2) solve + score** — run the method, score with the `eval/` registry restricted to `property_kind == marginal` evaluators (invariant 2), on the blocked validation split (invariant 1); **(3) constrained ranking** — the `SearchStrategy` ranks feasible trials by the configured primary objective subject to the constraint thresholds (invariant 8). Coherence is never a score — it is the feasibility gate (invariant 4), and any direct coherence measurement (e.g. the Phase-4 acceptance test) is worst-case-localized (invariant 6). The locked test (`their_eval` on CryoSat-2) is untouched until the single acceptance run (invariants 1, 9).

The mode separation falls out cleanly: in the single-tile challenge mode the feasibility gate is `True` for all trials (no seams), so Stages A–B are an unconstrained constrained-objective search; in the global-coherent mode the gate binds for the sparse-precision method, and the feasible region — a function of `(range, tile_geometry)` and of whether the redesign is built — is what Stage C surfaces.

---

## 5. Committed interfaces and abstractions

Signatures are **illustrative** — contracts and seams, not prescribed internals — and reference real symbols. The tuner is **orchestration**: it lives in `application/` (a new `application/tuning/`), drives trials through the existing executor, consumes the `eval/` registry and `validation/` harness, and does no uncertainty math. Dependency rule holds.

### 5.1 The search strategy seam — `application/tuning/`

```python
@runtime_checkable
class SearchStrategy(Protocol):
    """Pluggable, objective-agnostic optimizer over a method's parameter_space."""
    def propose(self, space: ParameterSpace, history: TrialHistory) -> list[Params]: ...
    # emits UoW (window, method, params, split, seed) trials through the existing executor

# Instances:
#   SobolSearch / RandomSearch  — proves the loop (Stage A); no surrogate
#   BayesianOptimization        — added once the loop is green (Stage B onward)
```

The strategy never sees truth or the locked test; it ranks only the feasible, marginally-scored trials it is handed.

### 5.2 The feasibility predicate seam — `application/tuning/`

```python
@runtime_checkable
class FeasibilityPredicate(Protocol):
    def feasible(self, params: Params, tile_geometry: TileGeometry,
                 required_capabilities: frozenset[UncertaintyCapability]) -> bool: ...

class CoherenceFeasibility:           # the default, capability-conditional + tile-count-keyed
    # Capability-scoped (invariant 4), keyed on TILE COUNT N (NOT core/range):
    #   {SAMPLES|COVARIANCE} -> joint cross-seam covariance barrier: feasible iff N <= n_star_joint.
    #     Measured EMPTY at the shipped joint_tol=0.5 (worst-of-K > tol at every tested N>=2) -> n_star_joint=1.
    #   {MARGINAL_VARIANCE}  -> reported-marginal accuracy: feasible iff marg_worst_case <= marg_tol.
    #     Measured worst-case ~15% FLAT in N -> ships iff marg_tol >= ~0.15 (tile-count-independent).
    #   {POINT} / no joint requirement -> True.
    # HARD barrier (invariant 3): infeasible -> excluded before any solve/score. Predicate stays CHEAP
    #   (baked constants); the heavy measurement is offline (scripts/diag_crossseam.py).
    # Pluggable (invariant 5): the decomposition-redesign supplies a relaxed predicate
    #   (cores>>range tiling / overlapping-Schwarz-with-coarse-correction / global low-rank
    #   seam basis) that WIDENS n_star_joint — without touching the tuner.
```

**Superseded 2026-07-01:** the earlier `core/range ≳ 25` bound was a Phase-4 GMRF-prior-bug artifact
(`6cce45b` fixed the prior; the conditioning + marginal collapse dissolved). The real, measured boundary is
the **worst-case JOINT cross-seam covariance vs TILE COUNT** (see
`docs/superpowers/specs/2026-07-01-stagec-redesign-design.md`): `SAMPLES/COVARIANCE` is infeasible at any
operational multi-tile geometry (empty region; global infeasibility is the robust, tolerance-invariant
claim), while `MARGINAL_VARIANCE` ships globally conditional on accepting the measured ~15%-flat worst-case
marginal error. The tolerances (`joint_tol`, `marg_tol`) are the predicate's swappable defaults, not tuner
assumptions — swapping/widening the predicate is the owner-deferred redesign's whole interface to the tuner.

### 5.3 The evaluator `property_kind` tag — `eval/`

Every evaluator gains a tag:

```python
class Evaluator(Protocol):
    property_kind: PropertyKind        # MARGINAL or JOINT
    def score(self, result, context) -> Scores: ...
```

- `MARGINAL` (RMSE, calibration coverage/χ²/CRPS, λx, area-weighted aggregation): may enter the objective vector; aggregated normally.
- `JOINT` (cross-seam coherence / derived-quantity seam parity): **never** enters the objective; used only as the feasibility constraint, reduced worst-case-localized (invariants 2, 6).

This tag is the mechanical form of the anti-false-green rule — an aggregate coherence score cannot reach the objective by construction.

### 5.4 The three-way split, mapped onto the real challenge — `application/withholding.py` + `splits.py`

- **train** = mapping-mission obs.
- **per-trial validation** = a *blocked* split (`LeaveOneMissionOut` / `PerMissionTemporalFraction` with buffer-discard), explicitly **not** CryoSat-2, scored by the internal `eval/`.
- **locked test** = the challenge's own **CryoSat-2 holdout via `their_eval.score`**, touched **once** at acceptance.

So "beat DUACS" is measured on exactly the leaderboard's holdout, exactly once, and the search never touches it (invariant 1). The challenge defines this holdout; the tuner reuses it rather than inventing a synthetic one.

### 5.5 Acceptance harness — reuse `validation/`

The winning config drives the full challenge map (`validation/run.py`, extended to the tuned method and a GMRF variant) → `their_eval.score` → `(µ, σ, λx)` versus the published leaderboard. This is the acceptance test for whatever the tuner produces, at every stage (invariant 9). `eval/` runs in parallel as the proven cross-check.

### 5.6 Contract-grounded calibration — `eval/calibration.py`

Coverage/χ²/CRPS are defined against the posterior's own promised contract (the distribution's stated marginal law), not an external chosen quantity. A metric value that depends on the reference choice is surfaced as a smell, not silently reported (invariant 10).

---

## 6. Non-goals (Phase 5 does NOT do these)

- **Latitude-varying parameter *fields*.** Generalizing `ParameterSpace` beyond scalar `(min,max)` boxes to a lat-varying `range` field — and the *spatial* feasibility constraint it induces (a tile-count / range-dependent coherence bound, hardest at the equator where range ~800 km; the old `core/range ≳ 25` framing is superseded per the 2026-07-01 redesign) — is a **named later extension**, deferred entirely from Phase 5.
- **The decomposition-redesign** (cores≫range tiling / overlapping-Schwarz-with-coarse-correction / global low-rank seam basis). It is an **owner-owned milestone**, decoupled from the tuner via the pluggable `FeasibilityPredicate`, opened when Phase 5 is underway. The tuner is built to consume a relaxed predicate; it does not build one.
- **FEM as a tuner target** — deferred; it inherits the boundary (interesting only post-redesign).
- **Bayesian optimization as the *initial* strategy** — BO *is* built, but added after the simple-strategy loop is green, never before (premature-complexity discipline).
- **Scalarized / weighted-sum objectives** (rejected; constrained formulation) and **soft feasibility penalties** (rejected; hard barrier) and **joint/coherence metrics in the objective vector** (rejected; feasibility constraint only).
- **Additional mapping methods** beyond OI + grid-GMRF (+ the trivial method, which has an empty `parameter_space()` and is not a tuner target). MIOST / DYMOST / BFN-QG / 4DVarNet remain future.
- **Cloud / multi-node execution** (still `LocalCluster`, address-only); **SWOT / 2-D swath**; **recalibration machinery** — all still deferred.

**If any of these appears necessary to make Phase 5 work, stop and ask — do not build it.**

---

## 7. Definition of done

**Stage A — the tuner core loop on OI against the challenge (single-tile, no constraint).** The `SearchStrategy` seam with a simple strategy (Sobol/random over the feasible box) emits UoW trials; per-trial scoring on the blocked validation split via the internal `eval/` (marginal evaluators only); the constrained objective (λx primary; `µ_RMSE` and calibration-coverage thresholds; feasibility predicate returns `True` in single-tile mode); acceptance via `their_eval.score` on the CryoSat-2 locked test, touched once. **Gate:** tuned OI lands DUACS-class on the leaderboard `(µ, σ, λx)`; the whole loop — search + constrained multi-objective + challenge scorer + the three-way split with the locked test touched exactly once — is proven.

**Stage B — grid-GMRF per-gridpoint against the challenge (single-tile, no constraint).** The same loop with GMRF's `parameter_space()` (range/variance/temporal_taper); still single-tile, still unconstrained (GMRF means/variances are clean). BO added as a `SearchStrategy` instance (Stage-A loop green first). **Gate:** GMRF tuned through the identical loop, landing a sensible challenge score; a test that the tuner is method-agnostic — no OI parameter-shape is baked in (the same `SearchStrategy`/objective/acceptance drive both methods unchanged).

**Stage C — global GMRF coherent (the feasibility boundary binds).** The `FeasibilityPredicate` (`CoherenceFeasibility`, **capability-conditional + tile-count-keyed** — see `docs/superpowers/specs/2026-07-01-stagec-redesign-design.md`) gates trials as a hard barrier. **Gate:** the tuner provably **never scores an infeasible trial** (a test asserting no solve/score occurs for a `SAMPLES/COVARIANCE` trial at `N ≥ 2`); coherence is gated **worst-case-localized** (adjacent-seam corr-err, never median); the pluggable predicate is demonstrated (a relaxed predicate widens `n_star_joint` without touching the tuner); and the **feasibility-vs-tile-count frontier is surfaced (both tiers)** — leading with the ROBUST claim that GLOBAL `SAMPLES/COVARIANCE` is infeasible (worst-of-K ~2.0 by 25 tiles, extrapolating past any tol), then the regional `n_star_joint=1` as the tol=0.5 point-estimate shorthand with its non-monotone + thin-margin (3×3=0.506±0.079 vs 0.5) + estimator-uncertainty caveats, and that `MARGINAL_VARIANCE` ships globally conditional on accepting ~15%-flat marginal error — as the input to the owner's decision on whether to open the (owner-deferred) decomposition-redesign. The known-broken target is pinned as a **concrete strict-xfail** (a `SAMPLES/COVARIANCE` `N ≥ 2` product asserted feasible, xfail until the fix widens `n_star_joint`). (Stage C proves the tuner *respects* the boundary and *quantifies its cost* for the REAL reason — worst-seam joint cross-seam covariance accumulates with tile count, NOT the refuted conditioning collapse; it does not attempt DUACS-class global coherent products at operational range, which the boundary forbids until the redesign. Single-fixture provenance is stated, not hidden.)

---

## 8. Decision log

All Phase-5 forks are closed. The tuner is a **method-agnostic, constrained multi-objective** search: a pluggable `SearchStrategy` (simple-first, then BO) emitting existing UoW trials; a pluggable, **hard-barrier**, **capability-conditional** `FeasibilityPredicate` (default **tile-count-keyed**: `SAMPLES`/`COVARIANCE` joint coherence infeasible at operational multi-tile scale, `MARGINAL_VARIANCE` ships within a flat marginal-error bound — superseding the refuted `core/range ≳ 25`; pluggable so the owner-owned decomposition-redesign relaxes it); a `property_kind` `{MARGINAL,JOINT}` tag so coherence (joint) is the feasibility constraint and never an objective term, gated **worst-case-localized**. Navigation is **constrained, not scalarized** — default λx primary, with `µ_RMSE` and calibration coverage as **hard bars**. The three-way split maps onto the **real challenge**: train = mapping missions, per-trial validation = blocked non-CryoSat-2 split via internal `eval/`, locked test = challenge **CryoSat-2 holdout via `their_eval.score`, touched once** at acceptance; acceptance = the `validation/` harness against the leaderboard. Metrics are **contract-grounded**. Sequencing: **OI-against-challenge → grid-GMRF-per-gridpoint → global-GMRF-coherent**, the constraint binding only in the third. **Scalar parameters only**; lat-varying fields deferred. **FEM is not a tuner target** (inherits the boundary). The **decomposition-redesign is owner-owned**, decoupled via the predicate. **No open Phase-5 architectural questions remain.**
