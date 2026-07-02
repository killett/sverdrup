# Phase-5 design: the autotune loop

**Status:** Approved architecture (2026-06-28). Implementation plan to follow via writing-plans.
**Scope source of truth:** `phase5_scope_spec.md` (settled). On any conflict, the spec governs.
**Builds on:** `sverdrup` at HEAD `35befdd`, verified by source read. Phase 5 adds an
orchestration layer in `application/tuning/`; it does **no** uncertainty math and changes no
method/distribution/protocol beyond the one sanctioned `eval/` metric tag.

This document is *how to build* the tuner on the existing seams. It does not re-open *what to
build* — that is the spec.

---

## 0. The seams this builds on (verified by source read)

| Concern | Real symbol | Signature / shape |
| --- | --- | --- |
| Method contract | `core/method.py::Method` | `native_capability`, `solve(obs, grid, params, time_days)`, `parameter_space() -> ParameterSpace` |
| Param box | `core/parameters.py::ParameterSpace` | `bounds: dict[str, tuple[float, float]]` (scalar boxes) |
| Params carrier | `core/parameters.py::ConstantProvider` | `values: dict[str, float]` (a `ParameterProvider`) |
| OI space | `methods/oi.py::parameter_space` | `{length_scale:(10,800), time_scale:(1,30), variance:(1e-3,1)}` |
| GMRF space | `methods/gmrf.py::parameter_space` | `{range:(10,800), variance:(1e-3,1), temporal_taper_scale:(1,30)}` |
| Capabilities | `core/types.py::UncertaintyCapability` | `POINT, MARGINAL_VARIANCE, COVARIANCE, SAMPLES` |
| Representation tag | `methods/*` | OI `"lowrank+diag"`, GMRF `"sparse-precision"` |
| Trial granularity | `application/uow.py::UnitOfWork` | `(window_id, method_name, params: ParameterProvider, split_id, seed, output_times, obs, grid, …)` |
| Executor port | `core/ports.py::Executor` | `submit(unit_of_work) -> Product` |
| Solve entry | `application/solve.py::solve_unit` | `(uow) -> Product` |
| Evaluator | `core/evaluation.py::Evaluator` | `name`, `required_context: frozenset[ContextKey]`, `evaluate(result, context) -> dict[str,float]` |
| Eval registry | `core/evaluation.py::Registry` | `Registry(evaluators).applicable(keys).run(result, context)` |
| Existing evaluators | `eval/accuracy.py`, `eval/calibration.py`, `eval/groundtrack.py` | `{rmse}`, `{reduced_chi2, coverage_1sigma, crps}`, `{track_power}` |
| Challenge runner | `validation/run.py::run_year` | per-day OI solve over the Gulf Stream box; **method = OI hardcoded**, kernel pluggable |
| Acceptance scorer | `validation/their_eval.py::score` | `(map_path, track_path) -> (µ_RMSE, σ_RMSE, λx)` over the c2 locked holdout |
| Blocked splits | `application/withholding.py` | `LeaveOneMissionOut`, `PerMissionTemporalFraction` → `SplitAssignment` |
| Three-way split | `application/splits.py::make_splits` | `by='mission'` with `locked_missions` / `validation_missions`; `by='random_point'` raises |
| c2 handling | `validation/input_adapter.py` | c2 guarded out of mapping obs; loaded eval-only as `EvalTrack` |
| Coherence boundary | `distributions/coherent.py`, `tests/test_core_authoritative_gate.py` | ~~`core/range ≳ 25`~~ SUPERSEDED 2026-07-01 → tile-count boundary (joint infeasible at operational scale); see `2026-07-01-stagec-redesign-design.md` |

**Gaps these reveal (resolved in this design):** no `property_kind`/metric tag exists; **no
internal (non-locked-test) λx scorer exists** — λx lives only inside `their_eval`; no
`TileGeometry` type exists; `run_year` is OI-coupled.

---

## 1. Package layout — `application/tuning/`

```
application/tuning/
  __init__.py
  trial.py        # Trial, TrialRecord, TrialHistory  (value objects)
  strategy.py     # SearchStrategy Protocol; RandomSearch, SobolSearch; BayesianOptimization (Stage B)
  feasibility.py  # FeasibilityPredicate Protocol; CoherenceFeasibility; RelaxedCoherenceFeasibility; TileGeometry
  objective.py    # ConstrainedObjective (primary + hard bars; constrained, not scalarized)
  loop.py         # tune(...) — the orchestration loop (gate -> solve+score -> rank)
```

Dependency rule (one-way, enforced): `application/tuning → eval / methods / distributions`. The
tuner does no uncertainty math; it drives existing UoW through the unchanged executor port.

---

## 2. Value objects — `trial.py`

```python
@dataclass(frozen=True)
class Trial:
    method_name: str
    params: dict[str, float]       # materialized as ConstantProvider(params) for the UoW
    split_id: str
    seed: int
    window_id: str

@dataclass(frozen=True)
class TrialRecord:
    trial: Trial
    scores: dict[str, float] | None  # None iff excluded by the feasibility gate (PROVES no solve ran)
    feasible: bool

@dataclass
class TrialHistory:
    seed: int
    records: list[TrialRecord]
    def feasible_scored(self) -> list[TrialRecord]: ...  # feasible and scores is not None
```

`scores is None` is the on-disk evidence that an infeasible trial was excluded **before any solve
or score** (invariant 3). The hard-barrier test asserts on exactly this plus a `submit` spy.

---

## 3. The search-strategy seam — `strategy.py`

```python
@runtime_checkable
class SearchStrategy(Protocol):
    def propose(self, space: ParameterSpace, history: TrialHistory) -> list[dict[str, float]]: ...
```

- `RandomSearch(seed)`, `SobolSearch(seed)` — prove the loop (Stage A); no surrogate. Seeded and
  recorded (invariant 11).
- `BayesianOptimization` — **named seam, built in Stage B, never before** (premature-complexity
  discipline, spec §6). It slots in as a drop-in `SearchStrategy` instance; the loop, objective,
  and acceptance do not change when it is added. This is the same property the method-agnosticism
  test pins from the other axis.

The strategy is objective-agnostic and never sees truth or the locked test; it ranks only the
feasible, marginally-scored trials the loop hands back through `history`.

---

## 4. The feasibility seam — `feasibility.py`

```python
@dataclass(frozen=True)
class TileGeometry:
    n_tiles: int                 # the predicate's key (tile count)
    core_size_deg: float         # recorded context for the artifact; predicate ignores
    range_km: float              # recorded context for the artifact; predicate ignores
    tiling_id: str

@runtime_checkable
class FeasibilityPredicate(Protocol):
    def feasible(self, params: dict[str, float], tile_geometry: TileGeometry,
                 required_capabilities: frozenset[UncertaintyCapability]) -> bool: ...

class CoherenceFeasibility:
    """Default: capability-conditional + TILE-COUNT-keyed (spec §5.2; redesign 2026-07-01)."""
    joint_tol: float = 0.5        # worst adjacent-seam corr-err bound (swappable)
    n_star_joint: int = 1         # tol=0.5 EMPTY-REGION SHORTHAND (worst-of-K > tol at all tested N>=2,
                                  #   non-monotone; NOT a monotone law). Only untiled N=1 is joint-valid.
    marg_tol: float = 0.20        # accepted worst-case reported-marginal rel error (swappable)
    marg_worst_case: float = 0.15 # MEASURED, FLAT in N (~13-15% up to 36 tiles) — characterized constant
    def feasible(self, params, tile_geometry, required_capabilities) -> bool:
        caps = required_capabilities
        if caps & {SAMPLES, COVARIANCE}:  return tile_geometry.n_tiles <= self.n_star_joint
        if MARGINAL_VARIANCE in caps:     return self.marg_worst_case <= self.marg_tol  # flat -> N-indep.
        return True                        # POINT / no joint requirement -> no seams

class RelaxedCoherenceFeasibility:
    """Redesign interface (invariant 5): widens n_star_joint without touching the tuner.
    The owner-deferred coarse-correction supplies this; its n_star_joint is ILLUSTRATIVE, not measured."""
```

**Capability-conditional, not method-conditional** (confirmed correct): the gate is driven by
`required_capabilities`, so the same GMRF method is unconstrained per-gridpoint and constrained only when
the product demands joint samples/covariance. **Superseded 2026-07-01:** the predicate keys on **tile count**
(not `core/range` — the `~25` bound was a GMRF-prior-bug artifact, `6cce45b`). Measured: `SAMPLES/COVARIANCE`
worst-case joint cross-seam correlation exceeds `joint_tol` at every operational multi-tile geometry → empty
region (`n_star_joint=1`); `MARGINAL_VARIANCE` reported-marginal error is ~15% flat → ships iff
`marg_tol ≥ ~0.15`. The predicate stays cheap (baked constants; the measurement is offline in
`scripts/diag_crossseam.py`), so invariant 3's gate-before-solve holds. Full rationale + provenance:
`docs/superpowers/specs/2026-07-01-stagec-redesign-design.md`.

---

## 5. The metric tag — `eval/` (the one sanctioned protocol change, spec §5.3)

### 5.1 Naming — `MetricScope`, NOT a bare `JOINT` (revision 1)

**Correction (2026-06-28):** an earlier draft claimed `distributions/blend.py` already exports
`JOINT` as a `CoherenceMode`. That premise was false — there is **no `CoherenceMode` enum** anywhere
in `src/`; the cross-tile *sampling* mode is carried by `sampler_spec` strings
(`"lowrank+diag"` / `"sparse-precision"`) dispatched via `select_driver`. The Phase-5 tag is a
different axis entirely: a **metric category** that controls whether a metric may enter the objective
vector. Metric-category and coherence-sampling-mode are simply different axes; there is nothing to
collide with.

Decision: name the metric axis with self-describing words that have zero lexical overlap with the
coherence-sampling representation, so no literal collision is possible:

```python
class MetricScope(Enum):
    POINTWISE   = "pointwise"     # per-gridpoint / spectral marginal property — MAY enter the objective
    CROSS_SEAM  = "cross_seam"    # joint cross-tile coherence — NEVER enters the objective; feasibility only
```

Add `metric_scope: MetricScope` to the `Evaluator` protocol in `core/evaluation.py`.

| Evaluator | `metric_scope` |
| --- | --- |
| `Accuracy` (rmse) | `POINTWISE` |
| `Calibration` (reduced_chi2, coverage_1sigma, crps) | `POINTWISE` |
| `GroundTrack` (track_power) | `POINTWISE` |
| `EffectiveResolution` (λx, new — §6) | `POINTWISE` |
| coherence (cross-seam parity) | `CROSS_SEAM` (reserved) |

`Registry` gains `.pointwise()` → a registry restricted to `metric_scope == POINTWISE`. The loop
scores trials through this restricted registry, so a `CROSS_SEAM` metric **cannot reach the
objective by construction** (invariant 2). Coherence is mechanically barred from the objective even
if a coherence Evaluator is added later; in Stage C coherence is the *feasibility gate*, reduced
worst-case-localized (§9), never a score.

> Note: today no coherence Evaluator exists in `eval/`; coherence is measured in the
> coherent-sampler gates. `CROSS_SEAM` is reserved now so the bar is in place before any such
> evaluator could be written. There is no `CoherenceMode`/`JOINT` enum to collide with — coherence
> mode is a `sampler_spec` string — so `MetricScope.CROSS_SEAM` is unambiguous by construction.

---

## 6. Internal λx — `eval/spectral.py` + `eval/resolution.py`

The primary objective is λx, scored per-trial on the **blocked non-c2 validation split** via
internal `eval/`. No such internal scorer exists; λx lives only inside `their_eval` on the c2
locked test. This builds it — completing the spec's "λx primary via internal `eval/`" default
(it is not new scope; the spec assumed an internal λx that did not exist).

### 6.1 One algorithm, two call sites — preparation lives in the shared helper (revision 4)

Invariant 10's real failure mode is the two paths **preparing residuals differently** (detrending,
windowing, gap-handling, segment chunking) before a shared crossing computation — λx then diverges
for reasons unrelated to the map, and a helper that only shares the final crossing math gives false
assurance. So the shared boundary is **raw track residuals**, not pre-prepared segments:

```python
# eval/spectral.py
_LENGTH_SCALE = 1000.0  # km; minimum along-track segment length for the spectral computation
def effective_resolution_lambda_x(track_residuals: AlongTrackResiduals) -> float:
    """Raw residuals -> segment preparation -> spectral score -> 0.5-crossing -> λx.
    The ONLY genuine single path: preparation AND crossing live here together."""
```

`their_eval.score` is refactored to call `effective_resolution_lambda_x` on the c2 locked track;
the new evaluator calls it on the blocked validation track. The track is the only thing that
varies between per-trial λx and acceptance λx, so "tuning on internal λx improves acceptance λx"
holds *by construction*.

### 6.2 The evaluator

```python
# eval/resolution.py
class EffectiveResolution:        # Evaluator
    name = "effective_resolution"
    required_context = frozenset({WITHHELD_OBS, ORBIT_GEOMETRY})
    metric_scope = MetricScope.POINTWISE
    def evaluate(self, result, context) -> dict[str, float]:
        # interp trial map onto the blocked NON-c2 validation track -> raw residuals
        # -> effective_resolution_lambda_x(...) -> {"lambda_x": ...}
```

- **Never touches c2 or `their_eval`** — only the validation track from the blocked split.
- **Time channel (decided 2026-06-28, implements Task 3):** the vendored λx requires *varying*
  datetime64 along-track time, but `eval_locations` is a float `(k,3)` coords array that cannot hold
  datetime64 (`column_stack` raises `DTypePromotionError`), and the OSE pipeline overwrites
  `eval_locations[:,2]` with a single scalar output time (`pipeline.py` `_prepare`), destroying the
  per-point times. Resolution: the evaluator reads lon/lat from `eval_locations[:,0:2]` and the
  *varying* per-point times from a **dedicated `result["eval_times"]` channel** carrying the
  pipeline-native float days-since-`EPOCH`; it reconstructs datetime64 via the named
  `input_adapter.EPOCH` (lossless to µs), so both call sites feed the helper an *identical* datetime64
  representation (invariant 10 preserved; segmentation is gap-based, so absolute epoch is irrelevant).
  **Deferred wiring (Task 11 + pipeline):** the validation-split scorer must populate `eval_times`
  from the blocked track's true timestamps (`coords[idx][:,2]` *before* the scalar `[:,2]` overwrite),
  and the gridded snapshot keeps its single time. `eval_locations` shape is unchanged (back-compat).
- **SUPERSEDED for the tuner's λx path (decided 2026-06-28, Task 11):** the Stage-A scorer was found
  unable to produce a meaningful per-trial λx via the single-snapshot eval-point solve (λx is a
  spectral property of the map along a *continuous track over the period*, not an eval-point
  property). The tuner's validation scoring is therefore the **faithful challenge pipeline pointed at
  the validation mission (j3)**: per trial, `run_challenge_map` builds daily maps from the trial's
  params on the *training* obs → vendored `interp_on_alongtrack` onto the **raw j3 (non-c2) track at
  its own datetime64 times** → residuals → `{mu_score, coverage_1sigma, lambda_x}` via the shared
  helpers (`effective_resolution_lambda_x`, `leaderboard_nrmse`, `calibration.coverage`). The only
  difference from c2 acceptance is the track (j3 vs c2) — invariant 10 at the scorer level;
  `their_eval.score` stays untouched (interp is a separate vendored fn). Because the raw track carries
  its own datetime64 times, the **`eval_times` float-days channel above is SUPERSEDED on the tuner's
  λx critical path** — it (and the eval-point predictive mechanism) remain only for the standard
  pipeline's OSE diagnostics. The shared `eval/spectral.py` helper (Task 2) and `EffectiveResolution`
  (Task 3) are KEPT and reused, just fed from interp-onto-raw-track residuals.
- **Segment-length guard (fail loud):** assert the validation track supports ≥ one full
  `_LENGTH_SCALE` segment; raise a clear configuration error otherwise. A too-short or too-sparse
  validation track is a config signal to surface, never a noisy λx the search would chase. (Object
  analogue: §8's empty-admissible-set rule.)

---

## 7. The split mapping onto the challenge

```python
make_splits(obs_mapping, by='mission',
            locked_missions=['c2'],                 # never in mapping obs anyway; held by their_eval
            validation_missions=[<one mapping mission>])
# -> train_idx (mapping)  |  validation_idx (blocked non-c2, internal eval/)  |  locked_test_idx (c2)
```

- **train** = mapping-mission obs.
- **per-trial validation** = a blocked `LeaveOneMissionOut` (or `PerMissionTemporalFraction` with
  buffer-discard) split over the mapping missions, explicitly **not** c2, scored by internal
  `eval/`.
- **locked test** = the challenge's own c2 holdout via `their_eval.score`, touched **once** at
  acceptance.

Random point holdout is forbidden (`make_splits(by='random_point')` already raises).

### 7.1 Validation-mission count is a known knob (revision 3)

`validation_missions=[one mapping mission]` is the minimal `LeaveOneMissionOut` proving case. It
couples per-trial λx/RMSE to **one mission's track geometry**, and λx is sensitive to that
geometry. This is recorded as a deliberate knob, not an oversight:

- **one mission** = minimal proof (Stage A default);
- **rotating / pooling a few missions** = the hardening path.

So a future "great on internal validation, mediocre on c2 at acceptance" outcome is diagnosed as
**expected-and-known** (a validation-geometry coupling to widen by rotating missions), not as a
silent bug in the loop.

---

## 8. The objective — `objective.py` (constrained, not scalarized)

```python
@dataclass(frozen=True)
class ConstrainedObjective:
    primary: str = "lambda_x"         # minimize (finer effective resolution)
    bars: tuple[HardBar, ...] = ...   # mu_score >= BASELINE, coverage_1sigma within tol
    def admissible(self, scores: dict[str, float]) -> bool: ...   # ALL bars pass
    def rank(self, records: list[TrialRecord]) -> list[TrialRecord]:
        admissible = [r for r in records if r.feasible and self.admissible(r.scores)]
        if not admissible:
            raise NoAdmissibleTrial(...)   # fail loud — see §8.2
        return sorted(admissible, key=lambda r: r.scores[self.primary])
```

### 8.1 The µ bar — BASELINE floor, DUACS aspiration (revision 2)

**Metric direction — CONFIRMED `>=` (higher is better).** Verified from source: the vendored
`compute_stats` returns `leaderboard_nrmse`, a **normalized-RMSE skill score** (1 = perfect), and
the leaderboard has DUACS 0.880 > BASELINE 0.850 with DUACS the stronger product. So the
admissibility gate is `mu_score >= bar`, not `≤`. The spec §3 invariant-8 phrasing "`µ_RMSE ≤`"
was **wrong** for this metric and is corrected here.

> **Naming guard:** the score variable is `mu_score`, **not** `mu_rmse`. A `*_rmse` name reads as
> lower-better and would tempt a future reader to reintroduce `≤`. Carry the meaning in the name:
> `mu_score` (higher-better skill score). The internal `Accuracy` evaluator emits raw `rmse`
> (lower-better); the µ **bar** is evaluated on the normalized `mu_score` — see the metric-source
> note below.

**The bar is BASELINE, not DUACS** — and DUACS is the aspiration, never a hard gate:

```
BASELINE_BAR_MU = 0.85   # hard admissibility floor — "do not regress below the published baseline"
                         # provenance: published 2021a leaderboard BASELINE row
                         # sverdrup OI scores 0.853 (RESULT.md), so it CLEARS this floor at the start
DUACS_TARGET_MU = 0.88   # aspirational ACCEPTANCE target — reported/compared via their_eval at
                         # acceptance, NEVER a hard admissibility gate
                         # provenance: README.md:224 / RESULT.md:9; harness reproduces 0.877/0.065/152.3
```

Why not DUACS as the hard bar: sverdrup OI starts at µ 0.853, **below** 0.88. A hard gate at 0.88
makes the admissible set **empty at the starting point** — the 0.853→0.88 gap is the full
BASELINE→DUACS spread, not closable by three scalar knobs — so `NoAdmissibleTrial` would fire every
run and Stage A could never go green. That collides test 1 (loop proven) with test 10 (empty →
`NoAdmissibleTrial`). The loud-empty safety net must **catch** that miscalibration, not **be** it.
With the BASELINE floor, `NoAdmissibleTrial` now guards the genuine "can't even hold BASELINE" case.

Note sverdrup OI already sits on the accuracy/resolution frontier — finer λx than DUACS (140.9 vs
152) at µ 0.853 — so scalar-tuning headroom is small, but the loop is still validly **proven**,
which is Stage A's purpose.

**Metric source for the bar (mirrors the λx shared-helper discipline).** `mu_score` is the
leaderboard-comparable normalized skill score computed **on the blocked validation track**, not raw
RMSE. As with λx (§6.1), the normalization is the *same* computation `their_eval` uses, applied to a
different track — so the per-trial validation µ and the acceptance µ are comparable by construction
(invariant 10). A thin normalized-score wrapper over `Accuracy`'s residuals supplies `mu_score`; it
never touches c2 or `their_eval`.

### 8.2 Empty admissible set fails loud (revision 2)

When zero trials are admissible, the loop **surfaces `NoAdmissibleTrial` loudly** — message:
"no admissible trial — loosen the bar or widen the search." It **never** silently returns empty and
**never** falls back to the least-bad infeasible or inadmissible point. An empty admissible set is
a configuration signal (objective-side analogue of the segment-guard-fails-loud rule), not a result
to paper over. Calibration and RMSE bars are hard — never traded against resolution (no opaque
weighted-sum scalarization, spec §6).

---

## 9. The orchestration loop — `loop.py`

The spec §4 formulation, in order: **feasibility gate → solve+score (marginal only, validation
split) → constrained ranking.**

```python
def tune(*, method_name, space, strategy, predicate, objective,
         pointwise_registry, executor, window, split, seed,
         tile_geometry, required_capabilities, rounds) -> TuningResult:
    history = TrialHistory(seed=seed, records=[])
    for _ in range(rounds):
        for p in strategy.propose(space, history):
            if not predicate.feasible(p, tile_geometry, required_capabilities):
                history.records.append(TrialRecord(Trial(method_name, p, split.id, seed, window.id),
                                                    scores=None, feasible=False))
                continue                                  # HARD BARRIER: no UoW built, no submit
            uow     = UnitOfWork(window_id=window.id, method_name=method_name,
                                 params=ConstantProvider(p), split_id=split.id, seed=seed, ...)
            product = executor.submit(uow)                 # solve via the unchanged port
            scores  = pointwise_registry.run(product, validation_context(split))  # POINTWISE only
            history.records.append(TrialRecord(Trial(...), scores=scores, feasible=True))
    ranked = objective.rank(history.feasible_scored())     # raises NoAdmissibleTrial if empty
    return TuningResult(winner=ranked[0], history=history)
```

- The feasibility gate is **before `UnitOfWork` construction and `submit`** → hard barrier
  (testable: `submit` spy is never called for an infeasible trial; the record carries
  `scores=None`).
- `pointwise_registry` is `Registry.pointwise()` — `CROSS_SEAM` metrics are structurally absent.
- `validation_context(split)` carries the **blocked non-c2 validation track** as `WITHHELD_OBS`.
  `their_eval` is not imported anywhere in `tuning/`.
- Determinism: a trial reproduces from `(window, method, params, split, seed)`; the search seed is
  recorded in `TrialHistory` (invariant 11).

---

## 10. Acceptance harness — reuse `validation/` (every stage)

`run_year` is OI-coupled. Generalize it to method-agnostic per-day solve:

```python
# validation/run.py
def run_challenge_map(method_name, params, grid, *, output_days,
                      temporal_half_window_days, mdt_grid=None, kernel=None, ...) -> Path:
    method = METHODS[method_name]
    # per day: method.solve(window, grid, ConstantProvider(params), time_days=day, **kw)
    #   OI keeps the kernel seam (kernel=kernel); GMRF variant ignores kernel and uses its own prior.
```

(`run_challenge_map` selecting `METHODS[method_name].solve` with OI keeping the kernel seam is
confirmed correct as-is.) The winning config drives the full challenge map → `their_eval.score` →
`(µ, σ, λx)` versus the published leaderboard, at **every** stage (invariant 9). `eval/` runs in
parallel as the proven cross-check.

---

## 11. Stage wiring (the hard-gated sequence)

**Stage A — tuner core loop on OI against the challenge (single-tile, no constraint).**
`method='oi'`; `space = OptimalInterpolation.parameter_space()`; `strategy = SobolSearch(seed)`;
`predicate = CoherenceFeasibility` (returns `True` — `required_capabilities` lacks
`{SAMPLES|COVARIANCE}`, single tile, no seams); `objective = ConstrainedObjective("lambda_x",
bars=[mu_score >= BASELINE_BAR_MU (0.85), coverage_1sigma within tol])`; per-trial scoring on the
blocked validation split via `pointwise_registry = {Accuracy(+normalized mu_score), Calibration,
EffectiveResolution}`; acceptance via `run_challenge_map('oi', winner) → their_eval.score` on the
c2 locked test, touched once, reported against the DUACS target.
**Gate:** the loop runs and holds `mu_score >= BASELINE` with calibration within tol, improves or
holds λx, and the acceptance run reports `(µ, σ, λx)` versus the DUACS row — the whole loop (search
+ constrained multi-objective + challenge scorer + three-way split, locked test touched once) is
proven. **Not** "achieves µ ≥ 0.88" (DUACS is the aspiration, not the gate — §8.1).

**Stage B — grid-GMRF per-gridpoint against the challenge (single-tile, no constraint).** Swap
`method='gmrf'`, `space = MaternGMRF.parameter_space()` — *nothing else changes*. The
method-agnosticism test pins that the same strategy/objective/acceptance drive both methods
unchanged (no OI param name baked into `tuning/`). Add `BayesianOptimization` as a `SearchStrategy`
instance once the Stage-A loop is green. **Gate:** GMRF tuned through the identical loop, sensible
challenge score; method-agnosticism test passes.

**Stage C — global GMRF coherent (the boundary binds).** *Redesigned 2026-07-01
(`docs/superpowers/specs/2026-07-01-stagec-redesign-design.md`) — the `core/range ≥ 25` framing below is
superseded.* `required_capabilities = {SAMPLES|COVARIANCE}` → `CoherenceFeasibility` binds; per trial
`TileGeometry(n_tiles, …)` → feasible iff `n_tiles ≤ n_star_joint` (= 1: empty region at the shipped
`joint_tol=0.5`, so any `N ≥ 2` joint trial is excluded before `submit` — hard-barrier test). Coherence is
the JOINT cross-seam covariance, reduced **strict-min worst-case-localized** (adjacent-seam corr-err, never
aggregate/median) — the gate, never a score (`CROSS_SEAM` barred from the objective).
`RelaxedCoherenceFeasibility` widens `n_star_joint` with the tuner unchanged (pluggability test); a concrete
strict-xfail (a `SAMPLES/COVARIANCE` `N ≥ 2` product asserted feasible) pins the known-broken target until
the deferred fix widens it. **Surface the feasibility-vs-tile-count frontier (both tiers)**: lead with the
ROBUST claim that GLOBAL `SAMPLES/COVARIANCE` is infeasible (worst-of-K ~2.0 by 25 tiles, extrapolating past
any tol), then the regional `n_star_joint=1` as the tol=0.5 point-estimate shorthand (non-monotone in N;
3×3=0.506±0.079 vs 0.5 is within noise), and that `MARGINAL_VARIANCE` ships globally conditional on ~15%-flat
marginal error — the input to the owner's (deferred) decomposition-redesign decision. Stage C proves the
tuner *respects and quantifies* the boundary, for the REAL reason (worst-seam joint accumulates with tile
count, NOT the refuted conditioning collapse); it does **not** attempt DUACS-class global coherent products
at operational range. Single-fixture provenance is stated. Do not loosen the predicate to manufacture a
result.

---

## 12. Load-bearing tests (TDD — each names a concrete killing bug)

| # | Behavior under test | Bug it catches |
| --- | --- | --- |
| 1 | Stage-A end-to-end: loop runs, holds `mu_score >= BASELINE` + calibration within tol, improves/holds λx; acceptance reports `(µ,σ,λx)` vs the DUACS row | The loop doesn't actually optimize toward the challenge objective (NOT "achieves µ ≥ 0.88" — DUACS is aspiration, §8.1) |
| 2 | Locked test touched **exactly once** (spy `their_eval.score`) | Search peeks at c2 — `call_count` must be 0 during search, 1 at acceptance |
| 3 | Method-agnosticism: same strategy/objective/acceptance drive OI + GMRF | An OI param name (`length_scale`) is baked into `tuning/` |
| 4 | Hard barrier: `executor.submit` spy **not called** for an infeasible `(range, tile)` | Feasibility implemented as a soft penalty that still solves/scores |
| 5 | `CROSS_SEAM` metric cannot enter the objective | An aggregate coherence value reaches `objective.rank` |
| 6 | `RelaxedCoherenceFeasibility` widens the feasible region, tuner code unchanged | The `~25` bound is hard-coded in the loop, not in the predicate |
| 7 | Shared-helper λx: a **real track** fed end-to-end through *both* call sites gives identical λx | The two paths prepare residuals differently (revision 4) — false invariant-10 assurance |
| 8 | Determinism: same `(window, method, params, split, seed)` reproduces | Unseeded search / unrecorded seed |
| 9 | Segment-length guard fails loud on a too-short validation track | A noisy λx silently emitted and chased |
| 10 | Empty admissible set raises `NoAdmissibleTrial` | Loop silently returns empty or the least-bad inadmissible point (now guards the genuine "can't hold BASELINE" case, §8.2) |

Test 7 feeds a real track end-to-end through both `their_eval.score` and `EffectiveResolution`,
asserting identical λx — **not** "identical given identical pre-prepared segments."

---

## 13. Invariant traceability

| Spec §3 invariant | Where enforced |
| --- | --- |
| 1 — never sees truth / locked test during search | §7 split; loop scores on validation only; test 2 |
| 2 — objective is marginal metrics only | §5 `MetricScope`; `pointwise_registry`; tests 5 |
| 3 — feasibility is a hard barrier | §4 + §9 gate-before-submit; `scores=None`; test 4 |
| 4 — mode-specific, capability-conditional | §4 `required_capabilities` branch |
| 5 — predicate pluggable | §4 `RelaxedCoherenceFeasibility`; test 6 |
| 6 — coherence worst-case-localized | §9/§11 Stage C strict-min reduction |
| 7 — strategy pluggable, objective-agnostic, UoW through executor | §3, §9; test 3 |
| 8 — constrained, not scalarized; calibration a hard bar | §8 `ConstrainedObjective` |
| 9 — acceptance is the real challenge harness | §10 `run_challenge_map` + `their_eval` |
| 10 — contract-grounded; reference-dependence is a smell | §6 shared raw-residual helper; test 7 |
| 11 — determinism | §9 seed recorded; test 8 |
| 12 — method-agnostic; scalar only | §1–§3 consumes `parameter_space()`; test 3 |

---

## 14. Owner-review resolutions (all closed)

1. **µ-bar direction** — RESOLVED `>=` (confirmed from source: `compute_stats` returns a
   normalized-RMSE skill score, higher-better; DUACS 0.880 > BASELINE 0.850). Spec §3 invariant-8
   "≤" was wrong; corrected. Score var named `mu_score` (not `mu_rmse`) to keep the direction
   legible (§8.1).
2. **µ-bar value** — RESOLVED to the BASELINE floor (`BASELINE_BAR_MU = 0.85`, which sverdrup OI's
   0.853 clears), with DUACS (0.88) as the aspirational acceptance target, never a hard gate. Stage-A
   gate and test 1 reframed accordingly so the loud-empty net catches miscalibration rather than
   being it (§8.1, §8.2, §11, §12).
3. **`blend.CoherenceMode.JOINT` reconciliation** — RESOLVED, **on a corrected premise**: there is
   no `CoherenceMode`/`JOINT` enum in `src/` (the original premise was wrong; coherence mode is a
   `sampler_spec` string). The metric axis is named `MetricScope.CROSS_SEAM`; a literal collision is
   therefore structurally impossible, and no `blend.py` change is made (§5). The Task-1 "distinct from
   `CoherenceMode.JOINT`" test was dropped as broken-and-vacuous (it imported a non-existent symbol);
   a one-line comment near `MetricScope` records why no collision exists.
4. **Spec versioning** — `phase5_scope_spec.md` committed alongside this doc (phases 1–4 specs
   already tracked).

Everything else in the approved architecture stands. Next step: writing-plans.
