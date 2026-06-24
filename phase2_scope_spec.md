# Phase-2 Scope Specification
### Tiling, blending, and coherent uncertainty for the global SSHA framework (`sverdrup`)

**Status:** Settled. Both brainstorm checkpoints are closed; no open Phase-2 architectural questions remain.
**Purpose:** Single authoritative reference for the Phase-2 build. Supersedes the Phase-2 scoping conversation; self-contained; the basis from which the Phase-2 Claude Code prompt is written. Mirrors `phase1_scope_spec.md`.
**Builds on:** the real `sverdrup` codebase delivered in Phase 1 (22 tasks, red→green TDD, vertical slice green on OSSE + OSE, accuracy/calibration/ground-track evaluators, opt-in oracle). Phase 2 extends that codebase; it does not start over.
**Governing discipline:** Decide the abstractions now — they must be global-ready. Prove the blend regionally before going global. Do not pre-engineer beyond the committed seams.

---

## 1. Project north star (context)

The framework ingests heterogeneous nadir altimetry and produces a **global** gridded SSHA product with rigorous per-gridpoint uncertainty, plus a method-comparison layer. Phase 1 built the core abstractions and a single regional tile. **Phase 2 makes it global** — via a method-agnostic tiling/blending layer that decomposes the globe into overlapping tiles, runs any method per tile through the existing executor, and stitches the per-tile predictive distributions (estimate *and* uncertainty) into one seam-free global product. The framework needs globally-scalable orchestration, not a globally-scalable method.

---

## 2. Phase-2 objective, scope, and build philosophy

**Objective.** Stitch per-tile predictive distributions into a global product whose mean, per-gridpoint uncertainty, and whole-field ensemble samples are seam-free, with rigorous treatment of the overlap, and evaluate it honestly — proven first on a handful of overlapping regional tiles, then run truly global.

**Scope — what Phase 2 lifts from the Phase-1 non-goals.** Exactly the three named lifts, plus two coupled items the project owner added during Phase-2 finalization (called out here so scope expansion is explicit, not silent):

- Lift 1 — **the tiling / stitching / blend layer**.
- Lift 2 — **cross-tile-coherent sampling**.
- Lift 3 — **global area-weighted metric aggregation**.
- Coupled addition A — **a pluggable withholding strategy**. A generalization of the Phase-1 blocked three-way split, coupled to Phase-2 blend-evaluation at withheld points (§5.6). Not a new subsystem.
- Coupled addition B — **a latitude-varying correlation-length provider**, used for scale-aware halo sizing (§5.1). This is not new architecture: it exercises the Phase-1 `ParameterProvider` seam (which already supports "scalar / function of latitude / field") with a non-constant configuration. Full 2-D *learned* parameter fields remain deferred to the autotune phase.

**Build philosophy — prove regionally first (tile-zero discipline, continued).** The Phase-2 proving milestone runs a handful of overlapping *regional* tiles against the same OSSE truth and OSE withheld data used in Phase 1, and requires the multi-tile blended map to match a single-tile reference solve within tolerance, with no seam in mean or uncertainty. Only after the blend is proven does Phase 2 run truly global (real poles, projection-mixed tiles, global data — see §7). Decide the global-ready abstractions now; defer true-global *execution* until the blend is proven.

**Data discipline (carried from Phase-1 "Decision B").** Real ODC adapter (no mocks for data), scoped data footprint during development (do not pull the full global dataset — 2023a OSE is ≈ 33 GB — into the dev/test loop), committed small fixtures for the blend tests, opt-in oracle and opt-in global runs.

---

## 3. Hard constraints (Phase-2 invariants)

Load-bearing; do not optimize away. Phase-1 invariants 1–10 all still bind; these add the blend-specific ones.

1. **Blend combines `Persisted` distributions, not live operators.** This is the single biggest constraint. The unit of work returns a `Persisted` distribution (mean + exact marginal variance + low-rank factor `B` + clipped diagonal residual `d` + seed + sampler-spec, fidelity `LOW_RANK`). The live operator carrying the full Cholesky exists only on-worker, before persistence. After the gather, only `Persisted` reps exist; the blend operates on them.
2. **Hand-off, never fuse.** In each tile's core the blend uses that tile's answer directly; in the overlap it crossfades smoothly from one tile's answer to the neighbor's via a partition-of-unity weight. It never combines two tiles' information into a sharper estimate. This is what makes double-counting structurally impossible (you cannot double-count evidence you never add together).
3. **Coherence makes the hand-off valid.** The crossfade is applied to *coherent* sample fields (invariant 8). Because white-noise conditioning makes the two tiles' realizations agree in the overlap (correlation ≈ 1), the crossfaded variance stays correct across the whole overlap with no mid-overlap dip. Without coherence, a variance crossfade would dip below the true variance at mid-overlap — spurious overconfidence. Q1 (hand-off) and Q2 (coherence) are therefore not independent: coherence is a precondition for the hand-off's uncertainty to be honest.
4. **Distribution-correct blending.** The output is a valid `PredictiveDistribution` exposing all three capabilities on the union support. Phase-1 invariant 7 still binds — never interpolate a marginal-variance map — now both in the overlap and across projections.
5. **Scale-aware halos.** Halo width is a user-configurable multiple `k` of the *local* correlation length, which varies by position (primarily latitude: ~100 km at high latitude to ~800 km at the equator), and is never a single global value; and it is at least the derived-quantity stencil radius. The correlation field is read through the Phase-1 `ParameterProvider`.
6. **Eval-point predictives computed on-worker.** Predictions and uncertainty at withheld points that fall in overlaps are computed while the live operator still exists, then persisted and blended — never reconstructed from the gridded blend (invariant 4 forbids it).
7. **Unified blend over support.** One blend operator handles a `GridSpec` *or* a `PointSet` as support, so the gridded blend and the eval-point blend are the same code path; the seam math lives in exactly one place.
8. **Coherent samples via shared global driving noise.** Whole-field samples across tiles are driven by a globally-indexed white-noise field, deterministically seeded, so realizations agree in overlaps. When a constituent method's sampler cannot support white-noise conditioning, the blend degrades gracefully and records the lost coherence in provenance — it never emits a hidden seam.
9. **Blend is a provenance transform with honest fidelity.** The blended product's typed uncertainty chain gains a `BlendTransform` carrying its conservative `known_bias`; the blended fidelity is a distinct marker (`BLENDED`) that never claims to be better than the constituents' `LOW_RANK`.
10. **Conservative residual, bounded and recorded.** Because halos are finite, each tile misses a thin far tail of data, so the two answers are *almost* identical. The residual errs slightly conservative (error bars a hair too large), never overconfident, shrinks as `k` grows, and is bounded-and-recorded — never silently dropped.
11. **Area-weighted global aggregation.** Global metrics aggregate per-cell scores with true spherical `cell_area` weighting (the Phase-1 first-class grid property); no unweighted global means.
12. **Pluggable, blocked withholding.** Withholding is a swappable strategy producing train / validation / (optional buffer-discard) / test from grouped or blocked structure. Random point holdout is forbidden (along-track SLA is highly autocorrelated, so a withheld point between two training points leaks).

---

## 4. The blend mechanism (how invariants 1–3, 8–10 cohere)

Stated once, because it is the heart of Phase 2 and unifies the settled decisions:

The blend is a **partition-of-unity crossfade of coherent samples**. For each tile *i* define a weight field `w_i(x)` that is 1 in tile *i*'s core, falls smoothly to 0 across the overlap toward the neighbor's core, with `Σ_i w_i(x) = 1` everywhere. Then:

- In a core (one tile only): use that tile's answer directly.
- In an overlap: for each ensemble member *m*, realize the constituents' *coherent* sample fields (driven by the shared global white noise, invariant 8) and crossfade them, `X_blend^m(x) = Σ_i w_i(x)·X_i^m(x)`. The blended distribution's samples are `{X_blend^m}`; its mean is the crossfade of the means; its marginal variance and covariance follow consistently.
- Because the constituents agree in the overlap (wide halo, invariant 5) and their realizations are coherent (invariant 8, correlation ≈ 1), the crossfade is between near-identical fields, so the result is nearly seamless and the variance does not dip (invariant 3).
- The residual (finite halo) is conservative and recorded (invariants 9, 10).

Cheap path vs general path (mirrors the Phase-1 propagation dispatch): the blended marginal **mean** and **variance** may be computed analytically from the constituents' moments via the same partition-of-unity weights (valid because coherence gives correlation ≈ 1); the full distribution needed for **samples**, **covariance**, and **cross-seam derived quantities** uses the coherent-sample crossfade. The `Persisted` reps regenerate the coherent samples deterministically on demand, so the general path is exact and reproducible.

---

## 5. Committed interfaces and abstractions

Signatures are **illustrative** — contracts and seams, not prescribed internals. Map names onto the real `sverdrup` layout; correct where it differs. The governing placement decision: **tiling is orchestration (lives in `application/`, owns geometry and dataflow, no uncertainty math); the blend operator and the coherent sampler are representation-math (live in `domain/` beside the derived-quantity operators, pure operations on distributions, no executor, no I/O). The tiling layer calls them.** Rationale: the blend must be unit-testable by handing it two overlapping `Persisted` distributions and asserting a seam-free union, with no cluster, data adapter, or orchestration in the way — the same reason Phase 1 put the first-difference operator in the domain, not the runner.

### 5.1 Tiling layer — `application/`

A partition-scatter-gather coordinator that reuses, not reinvents, the Phase-1 seams: `GridSpec.window()` is the tiling primitive ("regional = one window, global = many windows" is already one code path); windows are space-time (spatial tile × temporal obs window; `GridSpec` stays 2-D, time rides on the `Product` as per-time fields; the 21-day spin-up is the temporal halo); the Executor already submits many units with no re-granularization, so Phase 2 only *emits* many units through the existing port, and scaling out changes only the scheduler address.

```python
class TilingCoordinator(Protocol):  # application/
    def run(self, target: GridSpec, partition: TilePartition,
            method, params, split, seed) -> PredictiveDistribution:
        # 1. tiles = partition.tiles(target)                  # core + halo geometry
        # 2. emit (tile.extended_window, method, params, split, seed) per tile
        #    through the EXISTING Executor port  (no re-granularization)
        # 3. gather per-tile UnitResult (Persisted gridded + Persisted eval points)
        # 4. return blend_operator.blend(blend_inputs, support=target)

@dataclass(frozen=True)
class Tile:
    core_window: Window       # region this tile is AUTHORITATIVE for
    extended_window: Window   # core + halo; region it ingests obs over and solves on

class TilePartition(Protocol):
    def tiles(self, target: GridSpec) -> Sequence[Tile]: ...
    # MUST NOT assume a single projection (see 5.5)

class HaloPolicy(Protocol):
    def halo_for(self, core: Window, grid: GridSpec,
                 correlation_length: ParameterProvider,
                 stencil_radius: float) -> HaloExtent: ...
    # rule: halo = max(k * correlation_length(position), stencil_radius)
    #   k        : user-configurable multiple of the local correlation length
    #   position : correlation_length varies by latitude (~100 km -> ~800 km)
    # => halos (and tile geometry) vary with latitude; equatorial tiles get the
    #    widest halos. The partition is NOT uniform.
```

The solve runs on `extended_window`; the blend treats each tile's `core` as authoritative interior and the overlaps as the crossfade (seam) zones. The halo width `k` is the configurable knob; the conservative residual (invariant 10) shrinks as `k` grows, trading compute (widest at the equator) for tighter bounds.

### 5.2 Blend operator — `domain/`

```python
class BlendOperator(Protocol):  # domain/, beside the derived-quantity operators
    def blend(self, parts: Sequence[BlendInput],
              support: GridSpec | PointSet) -> PredictiveDistribution: ...
    # one operator, two supports (invariant 7)

@dataclass
class BlendInput:
    distribution: Persisted   # mean + sigma^2 + B + d + seed + sampler_spec, LOW_RANK
    tile: Tile                # core/halo geometry -> partition-of-unity weights
    # No heavy obs manifest: the hand-off (invariant 2) never fuses, so no
    # observation-information de-duplication is needed. The only "accounting" is
    # the conservative residual record (a function of halo width k), carried into
    # provenance (invariants 9, 10).
```

Contract requirements (mechanism in §4):
1. Output is a valid `PredictiveDistribution` on the union support — all three capabilities, never an interpolated variance map (invariant 4).
2. Hand-off crossfade, made valid by coherence; no mid-overlap variance dip (invariants 2, 3).
3. Honest fidelity: blended fidelity is `BLENDED` (≤ `LOW_RANK`, never higher).
4. Provenance: the typed chain gains a `BlendTransform` with the conservative `known_bias` (invariants 9, 10).
5. Method-agnostic: consumes any `Persisted` / `PredictiveDistribution` regardless of producing method (OI now; MIOST / SPDE / 4DVarNet later). It blends representations, not methods.

### 5.3 Coherent sampler — `domain/`

Realizes the Phase-1 `cross_tile_coherent_sampling` capability via **white-noise conditioning** (the settled Q2 choice): a globally-indexed white-noise field drives every tile's sampler, so neighbors draw consistent realizations in shared regions.

```python
class CoherentSampler(Protocol):  # domain/
    def requirements(self) -> SamplerRequirements: ...  # what it needs of the reps
    def realize(self, member_index: int, seed: Seed,
                parts: Sequence[BlendInput], support) -> Field: ...
```

- Global driving noise is indexed by a **tile-independent global spatial lattice** × `member_index` (× method, params, window-time), derived deterministically via the Phase-1 `derive_seed`. The Phase-1 deviation — members seed from caller-seed + index — is the basis; Phase 2 extends it so the same global cell yields the same white noise regardless of which tile is solving it.
- For the current OI/GP method, a sample is `mean + B·z_lowrank + sqrt(d)·z_diag` with `z` pulled from the global white-noise field restricted to the tile's support. Because the low-rank factor `B` and residual `d` are per-tile (slightly different posteriors), coherence is **approximate**, exact only in the wide-halo limit — i.e., coherence is as good as the same halo agreement that bounds the mean residual (invariants 5, 10). For future SPDE/GMRF methods (sample solves `Q·x = w`), the global driving-noise field makes coherence cleaner; the interface accommodates both.
- Graceful degradation (invariant 8): `requirements()` declares what the sampler needs of the `Persisted` reps; when a constituent cannot support white-noise conditioning, the blend degrades and records the lost coherence in provenance rather than emitting a hidden seam.

### 5.4 Unit-of-work extension and unified-over-support blend

The unit of work returns, in addition to its gridded `Persisted` distribution, the predictive distribution at any withheld points inside the tile — computed on-worker while the live operator exists (invariant 6):

```python
@dataclass
class UnitResult:
    gridded: Persisted                  # as Phase 1
    eval_point_predictives: Persisted   # NEW: at withheld points in this tile, on-worker
```

The same `BlendOperator.blend` then runs on the eval-point support (`PointSet`) exactly as on the grid (invariant 7), so withheld points that fall in overlaps are blended the same way the grid is — never reconstructed from the gridded blend.

### 5.5 Projection-mixed partition and cross-projection blend

Going global reaches the poles, so the partition yields polar-stereographic tiles at the caps and lon/lat tiles at mid-latitudes — the CRS-aware `GridSpec` branch Phase 1 only asserted on a non-polar tile now runs for real. Consequences:

- `TilePartition` must not assume a single projection.
- `BlendOperator` must accept constituents whose grids differ in CRS; in the overlap between a stereographic and a lon/lat tile it combines distributions living on different projections onto the union support, routing through the Phase-1 invariant-7 distribution-regridding machinery (regrid via samples or covariance-operator, never via the variance map).
- The **polar-void property** becomes a real, testable behavior on a real polar tile: uncertainty must relax toward the prior where there is no data; small reported error in a void is broken UQ.

### 5.6 Withholding strategy (coupled addition A)

A pluggable strategy that partitions observations into train / validation / (optional buffer-discard) / test from **grouped or blocked** structure. Random point holdout is forbidden (invariant 12).

```python
class WithholdingStrategy(Protocol):
    def split(self, obs: ObsSource) -> SplitAssignment:
        # -> per-observation assignment to TRAIN / VALIDATION / BUFFER_DISCARD / TEST
        # grouped/blocked only; never per-point random
```

Two exemplar implementations must both be expressible (these are illustrations of the required flexibility, not targets):

- **Leave-one-mission-out** — withhold one entire satellite/mission's data for validation; train on the rest.
- **Per-mission temporal fraction with buffer** — e.g., first 75% of each mission's record → train, next 5% → buffer-discard (severs train/validation autocorrelation), last 20% → validation.

The strategy feeds the three-way split discipline (train into the grid, validation drives the eventual tuner, locked test touched once) and the blend-evaluation at withheld points (§5.4). The independence caveat from Phase 1 still holds and is recorded honestly: withholding a mission gives independent *sampling*, not independent *errors* (shared tide models, MSS, corrections, reference frames).

### 5.7 Global area-weighted aggregation (Lift 3)

Global evaluation aggregates per-cell / per-region scores into global metrics using true spherical `cell_area` weighting (invariant 11), correct under any projection (lon/lat cells shrink as cos(lat); stereographic cells vary). The regional proving milestone can already area-weight (it is correct at any scale); full-globe aggregation is part of the global run (§7).

---

## 6. Non-goals (Phase 2 does NOT do these)

- **Global execution before the regional blend is proven.** The proving milestone (§7) is regional; do not attempt the global run, and do not pull the full ~33 GB global dataset into the dev/test loop, until the blend matches the single-tile reference within tolerance with no seam.
- **Additional mapping methods.** Still Method 0 (trivial) + Method 1 (OI/GP) from Phase 1. The blend is method-agnostic but is exercised only with OI in Phase 2. MIOST / DYMOST / BFN-QG / 4DVarNet / SPDE remain future.
- **Cloud / multi-node / SkyPilot / Slurm execution adapters.** Still `dask.distributed` + `LocalCluster`; the Executor port is unchanged and scaling out is address-only.
- **The autotune loop and any optimizer**, including 2-D *learned* parameter fields (the latitude-varying correlation length in §5.1 is a configured provider, not a learned field).
- **SWOT / 2-D wide-swath ingestion** (data model still able to absorb it).
- **Recalibration machinery** (provenance supports the chain; the step itself is later).
- **Full correction of shared-observation double-counting.** Phase 2 uses bound-and-record / hand-off (invariants 2, 9, 10); the architecture leaves room to add explicit correction later only if the proving step shows the conservative residual is unacceptable.

---

## 7. Definition of done

**Stage A — prove the blend regionally (the gate).** Using the same OSSE truth and OSE withheld data as Phase 1:

1. A handful of **overlapping regional tiles** are partitioned (core + scale-aware halo), solved through the existing `LocalCluster` Executor (each returning the extended `UnitResult`), and blended.
2. The multi-tile blended map **matches a single-tile reference solve** over the same region **within tolerance**, with **no seam in the mean and no seam in the uncertainty**, and the blended error bars are **never smaller** than the single-tile reference (conservative direction, invariant 10).
3. **Coherent samples are seam-free**: ensemble members are continuous across tile boundaries (white-noise conditioning), and the mid-overlap marginal variance shows **no dip** (invariant 3).
4. **Withheld-point evaluation in overlaps** works: withheld points falling in overlaps are scored from the blended eval-point predictives (§5.4), in both OSSE (vs truth) and OSE (vs withheld observations); accuracy and calibration evaluators fire on the blended product.
5. The blended product carries the full provenance chain including the `BlendTransform` with its conservative `known_bias` and `BLENDED` fidelity.
6. Pluggable withholding is exercised with both exemplar strategies (§5.6); random point holdout is rejected by construction.

**Stage B — go global (after Stage A passes).** Run truly global: projection-mixed partition (polar-stereographic caps + lon/lat mid-latitudes), the real polar-void behavior tested on a real polar tile (§5.5), area-weighted global aggregation (§5.7), on global data (2023a OSE ≈ 33 GB) as an opt-in run under the scoped-footprint data discipline.

---

## 8. Decision log

All Phase-2 forks are closed. Placement: tiling = orchestration in `application/`; blend + coherent sampler = representation-math in `domain/`. Double-counting: **bound-and-record via hand-off** (crossfade, never fuse), residual conservative and recorded. Sampler: **white-noise conditioning** (global driving noise), which is also the precondition that makes the hand-off variance honest. Halos: **configurable multiple `k` of the latitude-varying local correlation length**, at least the derived-quantity stencil radius, non-uniform tiles. Eval at overlaps: **on-worker eval-point predictives** carried forward, blended by the **support-generalized (unified)** blend operator. Projection-mixed partition with **cross-projection blend** via distribution-regridding; polar-void becomes a real test. Withholding: **pluggable, blocked strategy**, two exemplars (leave-one-mission-out; per-mission temporal fraction with buffer), random point holdout forbidden. Aggregation: **area-weighted**. Proving: **regional blend matches single-tile within tolerance, no seam**, before going global. **No open Phase-2 architectural questions remain.**
