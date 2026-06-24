# Phase-2 architecture & implementation design — tiling, blending, coherent uncertainty

**Status:** Approved (brainstorm). Source of truth for the build: `phase2_scope_spec.md` (settled
scope/invariants). This document is the *implementation* plan — how to build Phase 2 on the real
Phase-1 `sverdrup` codebase. On any conflict the scope spec governs.

**Governing discipline:** decide the global-ready abstractions now; prove the blend regionally
(Stage A gate) before any global execution (Stage B, opt-in). Reuse the Phase-1 seams; do not
reinvent them.

---

## 0. Two settled HOW-decisions (brainstorm checkpoints)

1. **Placement.** The blend operator and coherent sampler are *representation-math on
   distributions* → they live in `distributions/` (`blend.py`, `coherent.py`), beside
   `persisted.py` / `gaussian.py` / `ensemble.py` whose sampling logic and moment helpers they
   share and generalize. The spec's "`domain/`, beside the derived-quantity operators" is a
   placement *principle* (rep-math, free of orchestration and I/O), not a literal directory; this
   repo expresses that principle as a split across `core/` (protocols), `distributions/` (concrete
   reps), `derived/` (Distribution→Distribution functionals). The blend is `[Distribution] →
   Distribution over a spatial partition` — a different signature from a derived functional, so it
   is **not** filed under `derived/`. Tiling is orchestration → `application/`.

   **Dependency arrow (load-bearing):** `application/ → distributions/`, never the reverse.
   `blend.py` / `coherent.py` import `core/` protocols and `distributions/` internals only — never
   `application/`. `Tile` / `HaloExtent` / `Window` are `core/`-level value objects that the
   coordinator populates and passes *down* into the blend. If the blend ever reaches into
   `application/` for tile geometry, the value objects are mis-placed — not the blend.

2. **Cross-tile coherence for the OI low-rank rep.** Default = **member-only `z_r` for the
   structured part + global-cell white noise for the diagonal part** (Option 1, bound-and-record),
   built behind a `structured_noise_source` seam so the exact **spatial-square-root** driver
   (Option 2) is a drop-in swap without touching `blend.py` or `application/`. Rationale and the
   distinct residual it introduces are in §5.

---

## 1. Module map

```
core/
  grid.py          + PointSet value object (k×3 points + crs); unified-support sibling of GridSpec
  geometry.py  NEW  Window, Tile, HaloExtent  — frozen value objects, no math, no I/O
  types.py         + CovFidelity.BLENDED
  provenance.py    + TransformKind.BLEND ; KnownBias.CONSERVATIVE_HALO_RESIDUAL,
                     KnownBias.STRUCTURED_BASIS_ORIENTATION ; blend_transform() helper
  product.py       * EvalPointPredictions widened to carry structured eval rows (Phase-1 contract
                     change — flagged §6)
distributions/
  blend.py     NEW  BlendOperator, BlendInput, BlendedDistribution
  coherent.py  NEW  CoherentSampler, StructuredNoiseSource seam, global-lattice diagonal driver
  persisted.py     * implement regrid() (was NotImplemented) ; add PersistedPoints
                     (Persisted-over-PointSet)
application/
  tiling.py     NEW  TilingCoordinator, TilePartition (LonLat + ProjectionMixed), HaloPolicy
  withholding.py NEW WithholdingStrategy Protocol + 2 exemplars (splits.py refactored behind it)
  pipeline.py      * run_tiled_pipeline (Stage A driver) + area-weighted aggregation hook
core/parameters.py + LatitudeVaryingProvider (correlation_length as a function of latitude)
eval/
  aggregate.py  NEW  area-weighted global aggregation (GridSpec.cell_area)
```

`*` = a Phase-1 file/contract extended (visible, deliberate); `NEW` = added.

## 2. Core value objects (`core/geometry.py`)

```python
@dataclass(frozen=True)
class Window:                       # space-time box; the spec's "Window" (repo had only tuples)
    lon_range: Range; lat_range: Range; time_range: Range

@dataclass(frozen=True)
class HaloExtent:                   # projection-neutral, specified in KM (see §D)
    radius_km: float                # = k * correlation_length(lat); >= stencil radius
    # degree/grid-cell conversion happens in HaloPolicy/partition where the CRS is known —
    # NEVER store a degree pad here (a degree of longitude shrinks as cos(lat); a degree pad is
    # not a constant-km halo and won't compose with the projection-mixed partition).

@dataclass(frozen=True)
class Tile:
    core_window: Window            # the region this tile is AUTHORITATIVE for
    extended_window: Window        # core + halo; the region it ingests obs over and solves on
    grid: GridSpec                 # extended-window sub-grid = GridSpec.window(target, ...)
```

No UQ math, no executor, no I/O. Populated by the coordinator, consumed by the blend.

## 3. Tiling layer (`application/tiling.py`) — orchestration only

```python
class HaloPolicy(Protocol):
    def halo_for(self, core: Window, grid: GridSpec,
                 correlation_length: ParameterProvider, stencil_radius_km: float) -> HaloExtent
    # rule: radius_km = max(k * correlation_length(lat), stencil_radius_km); k user-configurable.
    # correlation_length varies by latitude (~100 km high-lat → ~800 km equator) => non-uniform
    # tiles; equatorial tiles get the widest halos. The km→degree/grid conversion lives HERE.

class TilePartition(Protocol):
    def tiles(self, target: GridSpec) -> Sequence[Tile]   # MUST NOT assume a single projection

class TilingCoordinator:            # reuses the Phase-1 seams; reinvents none
    def run(self, target: GridSpec, partition: TilePartition,
            method, params, split, seed, output_times) -> Product:
        # 1. tiles = partition.tiles(target)                         # core + scale-aware halo
        # 2. per tile: window obs over extended_window; build UnitOfWork(grid=tile.grid,
        #    eval_locations = withheld points inside the tile); emit via the EXISTING
        #    Executor.submit (a loop over tiles — the port already submits many units,
        #    no re-granularization; scale-out is address-only)
        # 3. gather per-tile Product -> [BlendInput(persisted, tile)] per output time
        # 4. return blend over the grid support AND over the eval PointSet support
```

`LonLatPartition` (Stage A) and `ProjectionMixedPartition` (Stage B: polar-stereographic caps +
lon/lat mid-latitudes) — same coordinator, swappable partition. The coordinator owns the
global-driving-noise spec (lattice origin/step + base seed) and hands it to the blend; samples are
regenerated coherently on demand from the `Persisted` reps (never a dense global covariance).

**Stage-A node co-registration (load-bearing — stated, not assumed).** `LonLatPartition` builds
every tile grid as `GridSpec.window(target, ...)`. Overlap nodes are therefore *identical subsets
of the one target grid* — co-registered by construction — so the Stage-A blend crossfades values
at shared nodes and does **not** invoke `Persisted.regrid`. Cross-projection regridding (§7) is a
Stage-B concern. If a future Stage-A partition ever produced non-shared overlap nodes,
`Persisted.regrid` would move earlier than its Stage-B slot.

## 4. Blend operator (`distributions/blend.py`) — the heart

```python
@dataclass
class BlendInput:
    distribution: Persisted        # mean + σ² + B + d + seed + sampler_spec, LOW_RANK
    tile: Tile                     # core/halo geometry → partition-of-unity weights

class BlendOperator:
    def blend(self, parts: Sequence[BlendInput],
              support: GridSpec | PointSet) -> PredictiveDistribution
```

**Mechanism (spec §4): partition-of-unity crossfade of coherent samples.**

- **Weights `w_i(x)`** — 1 in tile *i*'s core, fall smoothly to 0 across the overlap toward the
  neighbor's core, `Σ_i w_i(x) = 1` everywhere. One routine, evaluated on `GridSpec` nodes or
  `PointSet` points (invariant 7 — the seam math lives in exactly one place).
  **Ramp = smootherstep (quintic), not smoothstep.** Smoothstep is only C¹ at the
  core/overlap endpoints; the structured-coherence gate (step 5) differentiates across the seam,
  and `∂(Σ wᵢXᵢ)` picks up `(∂wᵢ)Xᵢ` terms whose curvature jump (from smoothstep) injects a faint
  narrow artifact into exactly the velocity field the gate inspects. Quintic smootherstep makes the
  weights' first derivative itself continuous across both boundaries. Because the constituents agree
  in the overlap (invariant 5), `Σ ∂wᵢ = 0` and the `Xᵢ` are nearly equal, so the `(∂wᵢ)Xᵢ` terms
  nearly cancel — the residual artifact is third-order in the constituent disagreement. Weight tests
  (step 2) assert `Σw=1` **and** first-derivative continuity across both boundaries.
- **Cheap path** (mean, marginal variance): analytic crossfade of the constituents' moments via
  `w_i` (valid under coherence, corr ≈ 1). Mirrors the Phase-1 propagation dispatch.
- **General path** (samples, covariance, cross-seam derived quantities): coherent-sample crossfade
  `X_blend^m(x) = Σ_i w_i(x)·X_i^m(x)`, samples regenerated on demand from the `Persisted` reps via
  the `CoherentSampler`. Never materialize a dense global covariance.

**Output `BlendedDistribution`** (a `PredictiveDistribution`): holds parts + weights + noise-spec;
`marginal_variance()` cheap path; `sample()` / `covariance()` general path; fidelity `BLENDED`;
provenance carries the `BlendTransform`. `blend` asserts every input fidelity ≤ `LOW_RANK` and
stamps `BLENDED` — never claims to beat the constituents.

Method-agnostic: consumes any `Persisted` / `PredictiveDistribution` regardless of producing method
(OI now; MIOST / SPDE / 4DVarNet later). It blends representations, not methods.

## 5. Coherent sampler (`distributions/coherent.py`)

Realizes `cross_tile_coherent_sampling` via **white-noise conditioning**.

```python
class StructuredNoiseSource(Protocol):           # the Option-1/Option-2 swap seam
    def draw(self, member_index, parts, support, noise_spec) -> Sequence[np.ndarray]  # z_r per tile

class MemberSeededZr:        # impl #1 (DEFAULT): z_r seeded by member_index only, tile-independent
class SpatialSqrtStructured: # impl #2 (RESERVE): spatial square-root from B over the overlap → exact

class CoherentSampler:
    def realize(self, member_index, noise_spec, parts, support) -> Field
    # diagonal part : white noise indexed by the GLOBAL spatial lattice cell (derive_seed extended
    #                 with cell_id) → coherent by construction across tiles
    # structured part: structured_noise_source.draw(...) ; default = member-only z_r
    # per tile i:  sample_i = mean_i + B_i·z_r + sqrt(d_i)·z_diag(global_cell)
```

- Global driving noise is indexed by a **tile-independent global spatial lattice × member_index**,
  derived deterministically via the Phase-1 `derive_seed` (extended: diagonal noise keyed by
  `(method, params_key, global_cell_id, member)` — the same global cell yields the same white noise
  regardless of which tile is solving). Phase-1's "members seed from caller-seed + index" is the
  basis Phase 2 extends.
- **Why coherence is approximate for the structured part, and why its residual is its own thing.**
  An SVD factorization is unique only up to rotation within equal-singular-value subspaces and up to
  sign, so two tiles can produce the same posterior covariance in the overlap yet factor it with
  different `B` orientations. Member-only `z_r` means tile A draws `B_A·z_r` and tile B draws
  `B_B·z_r` with the same `z_r` but `B_A ≠ B_B` even when `B_A B_Aᵀ ≈ B_B B_Bᵀ`. The two structured
  fields share a seed yet realize *different functions of it* — samples from nearly the same law,
  not the same realization. This **basis-orientation residual** persists even where the posteriors
  agree exactly and widening `k` may not fully kill it. It is therefore recorded in provenance as a
  **distinct** entry (`STRUCTURED_BASIS_ORIENTATION`), separate from the finite-halo mean residual
  (`CONSERVATIVE_HALO_RESIDUAL`), so a faint sample seam can be diagnosed to its true cause.
- Graceful degradation (invariant 8): `requirements()` declares what the sampler needs of the
  `Persisted` reps; when a constituent cannot support white-noise conditioning, the blend degrades
  and records the lost coherence in provenance — never a hidden seam.

The basis-orientation residual is invisible to the marginal-variance no-dip test but shows up as
sample-path discontinuity (a faint seam in individual realizations and in cross-seam derived
quantities). Hence the **sample-continuity / cross-seam-derivative gate** (step 5) is the real gate
for this decision; the no-dip variance test is necessary but not sufficient here.

## 6. Unit-of-work extension — eval points become blendable (Phase-1 contract change)

`UnitResult` is the existing `Product`, which already carries the gridded `Persisted` plus the
on-worker `EvalPointPredictions` (invariant 6 — computed while the EXACT operator lives, never
reconstructed from the gridded blend). Gap: `EvalPointPredictions` carries mean/var only and cannot
crossfade coherently. Fix → a `PersistedPoints` (Persisted-over-PointSet) extracted on-worker, so
`BlendOperator.blend(parts, support=PointSet)` runs the identical crossfade on withheld points
(invariants 6 + 7).

**Constraint (not new machinery): the eval rows are extracted as additional rows of the tile's
existing structured factor, in the same right-singular basis as the gridded block — never
re-factored with a separate SVD.** The structured-coherence gate (step 5) is a cross-seam
difference: a withheld point's first-difference / velocity residual couples it to its *grid
neighbours*, so it needs `Cov(eval_point, neighbour_grid_nodes)`, not just the eval points' own
marginals and mutual covariance. The shared SVD basis gives this cross-covariance for free as
`B_eval · B_grid_rowsᵀ`; an independent factorization of the eval rows would **not** be consistent
with the gridded block and would break the cross-seam coupling. So on-worker extraction yields
`B_eval (k×r)` + `d_eval` *in the gridded block's basis*, plus mean.

**Flagged contract change:** this widens `EvalPointPredictions` / `Product` (Phase-1 types) to carry
the structured eval rows — a deliberate extension of a Phase-1 structure, mirroring how the
unit-of-work extension was flagged in the scope spec. Touches `solve_unit._eval_points` and
`core/product.py`.

## 7. Cross-projection blend (Stage B) — `Persisted.regrid`

Implement the stubbed `regrid(target)` sample-based: draw coherent samples on the tile grid, regrid
the *samples* (or route through the covariance operator) to the union support — never interpolate
the variance map (invariants 4, 7). In a stereographic↔lon/lat overlap the blend regrids each
constituent onto `support`, then crossfades. The **polar-void property** becomes a real, testable
behavior on a real polar tile: uncertainty must relax toward the prior where there is no data; small
reported error in a void is broken UQ. (Stage B only — see §3 co-registration note.)

## 8. Withholding (`application/withholding.py`)

```python
class WithholdingStrategy(Protocol):
    def split(self, obs: ObsWindow) -> SplitAssignment    # TRAIN / VALIDATION / BUFFER_DISCARD / TEST

class LeaveOneMissionOut: ...            # exemplar 1 — withhold one mission entirely (existing
                                         #   by="mission" behavior, now behind the protocol)
class PerMissionTemporalFraction: ...    # exemplar 2 — e.g. first 75% of each mission → train,
                                         #   next 5% → buffer-discard (severs train/val
                                         #   autocorrelation), last 20% → validation
```

`Split` gains `buffer_discard_idx`. `random_point` holdout still rejected by construction
(invariant 12 — along-track SLA is highly autocorrelated; a withheld point between two training
points leaks). `make_splits` refactored to delegate to a strategy. Independence caveat recorded
honestly: withholding a mission gives independent *sampling*, not independent *errors* (shared tide
models, MSS, corrections, reference frames).

## 9. Area-weighted aggregation (`eval/aggregate.py`)

`global_score = Σ cell_area · score / Σ cell_area`, using `GridSpec.cell_area()` (correct under any
projection: lon/lat cells shrink as cos(lat), stereographic cells vary). No unweighted global means
(invariant 11). Correct at regional scale too → exercised already in Stage A.

## 10. Provenance

`blend_transform()` → `UncertaintyTransform(kind=BLEND, known_bias=CONSERVATIVE_HALO_RESIDUAL,
params={"k": k, "residual_bound": ...})`, plus a **distinct** `STRUCTURED_BASIS_ORIENTATION` entry
whenever impl #1 (member-only `z_r`) is the structured driver. The two residual kinds are recorded
separately (§5). `BLENDED` fidelity stamped, never greater than the constituents' `LOW_RANK`. Every
blended product reproducible from its provenance.

## 11. Build order — Stage A is the integration gate

1. `core/` value objects (`Window`, `Tile`, `HaloExtent`) + enum/provenance extensions
   (`CovFidelity.BLENDED`, `TransformKind.BLEND`, the two `KnownBias` kinds) + tests.
2. Partition-of-unity weights, isolated: assert `Σw = 1` **and** first-derivative continuity across
   both core/overlap boundaries (smootherstep), plus weight smoothness.
3. `BlendOperator` cheap path: blend two overlapping `Persisted` reps in isolation (no cluster, no
   I/O) → seam-free mean + **no mid-overlap variance dip** + **conservative σ ≥ single-tile**. The
   load-bearing isolation test.
4. `CoherentSampler` impl #1 + `StructuredNoiseSource` seam → coherent samples continuous across the
   seam.
5a. **Composition pre-check:** verify `derived/firstdifference` (and `velocity` when stubbed in)
    composes on a `BlendedDistribution`. The blend output is a `PredictiveDistribution`, but it is
    the first non-trivial distribution the operators meet — exercise the composition before relying
    on it as a gate.
5b. **Cheap-vs-sample variance-agreement test (overlap):** the analytic moment crossfade (cheap
    path) and the coherent-sample crossfade (general path) must agree on marginal variance in the
    overlap to within Monte-Carlo tolerance. That agreement is the invariant that justifies using
    the cheap path at all; divergence means coherence is weaker than assumed (corr meaningfully
    below 1) and localizes the failure to the variance, separately from the derivative gate —
    making the §8/owner escalation diagnosis fast.
5c. **Sample-continuity / cross-seam-derivative gate:** `firstdifference` (velocity when stubbed)
    across the seam on the coherent ensemble shows **no variance inflation** vs the single-tile
    reference. *This is the real structured-coherence gate; if it fails, escalate to the owner per
    scope-spec §8 (bound-and-record vs swapping in the Option-2 spatial-square-root structured
    driver) — swap the driver, not the architecture.*
6. Eval-point `PersistedPoints` on-worker (shared-basis eval rows, §6) + blend over `PointSet` →
   withheld-point eval in overlaps, OSSE (vs truth) and OSE (vs withheld obs).
7. `TilingCoordinator` + `LonLatPartition` + `HaloPolicy` + `LatitudeVaryingProvider`; wire
   `run_tiled_pipeline`.
8. Withholding protocol + both exemplars; area-weighted aggregation.
9. **Stage-A integration gate:** a handful of overlapping regional tiles through the existing
   `LocalCluster` Executor; blended map matches a single-tile reference within tolerance, no seam in
   mean or uncertainty, conservative σ; coherent samples seam-free, no mid-overlap dip; withheld
   eval in overlaps fires (OSSE + OSE); provenance carries the `BlendTransform`
   (`CONSERVATIVE_HALO_RESIDUAL`, `BLENDED`); both withholding exemplars exercised; random point
   holdout rejected by construction.
10. **Stage B (opt-in, only after A passes):** `ProjectionMixedPartition`, `Persisted.regrid`, real
    polar tile + polar-void test, area-weighted global aggregation, on global 2023a OSE (~33 GB)
    under the scoped-footprint discipline.

## 12. Test strategy (TDD — each test states behavior + a concrete bug that fails it)

Load-bearing, in isolation (two `Persisted` reps, no cluster/I/O unless noted):

- Seam-free union mean (bug: naive concatenation leaves a discontinuity at the core boundary).
- No mid-overlap marginal-variance dip (bug: variance crossfade without coherence dips below true σ²).
- Conservative direction: blended σ ≥ single-tile reference σ (bug: fusion sharpens the estimate).
- `Σw = 1` partition of unity **and** weight first-derivative continuity (bug: smoothstep curvature
  jump → derivative artifact).
- Coherent samples continuous across the seam (bug: independent per-tile noise → sample seam).
- Cheap-vs-sample variance agreement in overlap within MC tolerance (bug: corr < 1 unnoticed).
- Cross-seam derived (`firstdifference`/velocity) no variance inflation vs single-tile (bug:
  basis-orientation residual → faint velocity seam the no-dip test misses).
- `firstdifference` composes on a `BlendedDistribution` (bug: blend output not a true
  `PredictiveDistribution`).
- Withheld-point eval in overlaps fires, scored from blended eval-point predictives (bug:
  reconstruct-from-grid path used instead of on-worker predictives).
- Eval rows share the gridded SVD basis → correct `Cov(eval, neighbour grid)` (bug: independent
  re-factorization breaks cross-seam coupling).
- Random point holdout rejected (bug: autocorrelation leak silently allowed).
- Area-weighting ≠ unweighted under cos(lat) (bug: unweighted global mean).

test-design skill applied per test. Stage-A milestone = integration gate; Stage B gated on it.

## 13. Data plan (Phase-1 "Decision B")

Real ODC adapter (no data mocks); scoped footprint. Committed tiny NetCDF fixtures = two small
overlapping tiles for the isolation blend tests. Stage A on the same NATL60 OSSE truth + OSE
(CryoSat-2 withheld) paths as Phase 1, daily reference (never the 11 GB hourly). Oracle parity and
the global 2023a (~33 GB) run are opt-in only; the full global set never enters the dev/test loop.

## 14. Out-of-scope guardrails (scope-spec §6, held)

No global execution before Stage A passes; no additional mapping methods (OI + Method 0 only); no
cloud/multi-node adapters (LocalCluster, address-only scale-out); no autotune / learned 2-D fields
(latitude-varying correlation length is a *configured* provider); no SWOT/2-D swath; no recalibration
machinery; no full shared-observation double-count correction (bound-and-record / hand-off; leave
room to add correction later only if Stage A shows the residual is unacceptable). If any appears
necessary, stop and ask.
