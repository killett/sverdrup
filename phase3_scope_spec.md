# Phase-3 Scope Specification
### A genuinely-different method (SPDE/GMRF) and the representation-agnostic generalization (`sverdrup`)

**Status:** Settled. Both brainstorm checkpoints are closed; no open Phase-3 architectural questions remain.
**Purpose:** Single authoritative reference for the Phase-3 build. Supersedes the Phase-3 scoping conversation; self-contained; the basis from which the Phase-3 Claude Code prompt is written. Mirrors `phase1_scope_spec.md` and `phase2_scope_spec.md`.
**Builds on:** the real `sverdrup` codebase after Phase 2 (full suite 129 passed / 2 skipped; both Phase-2 gates green). Phase 3 extends and refactors that codebase; it does not start over. This spec references real source symbols (verified against the repo).
**Governing discipline:** Generalize the abstraction under the green Phase-2 suite *before* adding the new method. Decide the abstractions to stay representation-agnostic. Do not pre-engineer Phase 4 (autotune).

---

## 1. Project north star (context)

The framework ingests heterogeneous nadir altimetry and produces a global gridded SSHA product with rigorous per-gridpoint uncertainty, plus a method-comparison layer and (eventually) an autotune loop. Phase 1 built the core abstractions and a regional tile; Phase 2 added the method-agnostic tiling/blend and went global. **Phase 3 proves "method-agnostic" is real** by adding a method whose uncertainty representation is fundamentally different from OI's — a sparse-precision GMRF — and by generalizing the representation/coherence/persistence layer so that representation is first-class alongside OI's low-rank, without re-baking OI's shape into the spine. Phase 4 (autotune) is deferred and scoped after Phase 3 runs.

---

## 2. Phase-3 objective, scope, and build philosophy

**Objective.** Add a regular-grid Matérn GMRF method (sparse precision) as a first-class second method; relocate the coherence seam and representation-tag the persistence/reduction layer so the GMRF representation is first-class alongside OI's low-rank with no method-specific special-casing; validate the method-agnostic blend on a genuinely-different representation (clean coherence via shared white noise, which cannot be faked as low-rank); and close the Phase-2 gap by exercising the degradation path (perturb-ensemble) end-to-end through the tiled blend.

**Why this method.** The method-agnostic blend was built and proven in Phase 2 but only ever exercised with OI (low-rank). SPDE/GMRF is the highest-value validation because it stresses the three coupled spots at once — the persisted form, the coherence driver, and the reduction boundary — and cannot hide in the degradation path (its coherence is clean). It also gives Phase 4 a non-trivial second method with a different, physically-interpretable parameter space, and advances the original north-star (rigorous nonstationary UQ — the literature's "optimal + rigorous error" frontier).

**Scope — exactly what Phase 3 does, and nothing else:**
- The **SPDE/GMRF method**: regular-grid Matérn, sparse precision `Q`, exact selective-inversion marginal variance, provider-driven (nonstationary-capable) κ.
- The **D2 architecture generalization**: relocated `CoherentMemberDriver` seam (three instances), representation-tagged persisted form, per-operator reduction strategy.
- **Exercising the degradation path** (perturb-ensemble driver) end-to-end through the tiled blend — closing the Phase-2 gap where it was contracted but unexercised.
- A **latitude-varying-κ demonstration** (provider-driven nonstationarity), as the SPDE differentiator and the Phase-4 parameter-field precedent.

**Build philosophy — generalize under green, then extend.** The protocols are already clean (verified: `core/method.py` `Method`, `core/distribution.py` `PredictiveDistribution` and `CovarianceOperator`), so GMRF plugs in at the same point as OI. The real work is the representation generalization plus the method core. The critical sequencing: **refactor the existing OI/low-rank path onto the relocated seam + representation-tagged persistence + per-operator reduction *first*, with the full Phase-2 suite as the regression oracle (OI through the new seam must reproduce Phase-2 results exactly), and only then add GMRF as a second instance.** This prevents the generalization from silently breaking the working system. Prove stationary-first, then the nonstationary demo. Homogeneous-representation-per-blend (one method per global run). Same Phase-1 "Decision B" data discipline (real ODC adapter, scoped footprint, committed fixtures, opt-in oracle/global).

---

## 3. Hard constraints (Phase-3 invariants)

Load-bearing; do not optimize away. Phase-1 invariants 1–10 and Phase-2 invariants 1–12 all still bind. These add the representation-generalization and GMRF specifics.

1. **Protocols stay representation-agnostic.** `Method`, `PredictiveDistribution`, and `CovarianceOperator` are not modified to accommodate GMRF; GMRF implements them as they stand. No representation leaks into the protocol spine.
2. **Coherence driver selected by representation tag, never method identity.** The `CoherentMemberDriver` dispatches on the persisted form's representation (`sampler_spec`), not on which method produced it. This is "method-agnostic" in the strict sense.
3. **Persisted form is representation-tagged.** `sampler_spec` is the load-bearing discriminator; sparse-precision is a first-class storable beside low-rank+diagonal. `BlendInput.distribution` accepts the abstract `PredictiveDistribution`, not the concrete `PersistedDistribution | PersistedPoints` union.
4. **Reduction is a per-operator strategy.** Persistence — for both the gridded block and the on-worker eval-point predictives — goes through a per-`CovarianceOperator` strategy, never application-level method special-casing (replacing the current hardcoded `reduce_with_basis` + `eval_rows_in_grid_basis` calls in `application/solve.py`).
5. **GMRF coherence is native via shared global white noise.** A GMRF member is `mean + L⁻ᵀ w`, with `w` the *existing* global-lattice `diagonal_noise` field reused as the coherent forcing. Coherence requires **no QR-basis trick**; the only residual is the `Q_i ≠ Q_j` halo-agreement term (conservative, recorded) — never the basis-orientation residual that was the ~40% killer for low-rank.
6. **Exact GMRF marginal variance via selective inversion.** `diag(Q⁻¹)` via the Takahashi recursion (exact, sparse), not sampled; the operator's `fidelity` is `EXACT`; this keeps the calibration axis (a first-class metric) honest. The same sparse Cholesky `L` serves sampling, marginal variance, and `cov(a,b)`.
7. **OI path preserved under the generalization (generalize-under-green).** Refactoring the existing OI/low-rank path onto the relocated seam, the representation-tagged persistence, and the per-operator reduction must reproduce the Phase-2 results exactly — the green Phase-2 suite (129 passed / 2 skipped) is the regression oracle. Generalize under green, then add GMRF.
8. **Degradation path exercised, not just contracted.** The perturb-ensemble driver runs end-to-end through the tiled blend with coherence loss recorded in the typed provenance chain (Phase-2 invariant 8), closing the Phase-2 gap where it was wired nowhere.
9. **Homogeneous representation per blend (Phase-3 scope).** One method per global run; every blend is homogeneous. Mixing OI and GMRF tiles is *structurally* allowed (per-constituent dispatch + field crossfade) but coherence is only guaranteed *within* a representation; a mixed blend, if it ever arises, takes the degradation path (provenance-flagged). Cross-representation coherent maps are out of scope.
10. **Nonstationary-capable κ via the provider.** κ flows through the Phase-1 `ParameterProvider` (`LatitudeVaryingProvider` is the precedent); GMRF is nonstationary-capable; Phase 3 proves stationary-first, then demonstrates latitude-varying κ. The discretization uses a fixed integer α (smoothness ν fixed) for a clean sparse stencil; continuous/tunable ν is deferred.
11. **Determinism preserved.** GMRF sampling uses the global-lattice white noise (order-independent, reproducible); the fill-reducing permutation and any new randomness are deterministic and recorded.

Carry-forward invariants that persist unchanged: the typed provenance chain with known-bias entries; honest fidelity and conservative-direction-and-record over hidden assumptions; calibration first-class, not just accuracy; never interpolate a variance map; OSSE and OSE both; and (for Phase 4) the tuner must never see truth or the locked test.

---

## 4. The representation generalization (how invariants 1–9 cohere)

Stated once, because it is the heart of Phase 3. Three coupled changes, done OI-first under green, then GMRF added:

**(a) Relocate the coherence seam.** Today the working cross-tile coherence is the free function `coherent_structured_field` (QR-common-basis + symmetric-sqrt), called directly at `blend.py:159`, *bypassing* the `StructuredNoiseSource` protocol — which holds only the naive `MemberSeededZr` (the ~40% underdisperser). Phase 3 introduces a `CoherentMemberDriver` seam at the `_coherent_member` level — *produce a cross-tile-coherent, weight-crossfaded realization over the support from the constituents + global noise* — with three instances: low-rank-shared-basis (repackage `coherent_structured_field` + diagonal), gmrf-precision-solve (`mean + L⁻ᵀ w`, native coherence), perturb-ensemble-degradation (records coherence loss). The naive `MemberSeededZr`/`StructuredNoiseSource` is retired (or folded in as the historical driver), resolving the existing seam/fix drift. The crossfade itself (`Σ wᵢ · fieldᵢ`) stays representation-agnostic.

**(b) Representation-tag the persisted form.** Add a sparse-precision storable (`mean + sparse Q + permutation + marginal_variance + sampler_spec="sparse-precision"`) beside the low-rank+diagonal `PersistedFields` (`sampler_spec="lowrank+diag"`). The currently-vestigial `sampler_spec` becomes the discriminator the driver (a) dispatches on. Widen `BlendInput.distribution` to the abstract `PredictiveDistribution`.

**(c) Generalize the reduction boundary.** Move persistence behind a per-`CovarianceOperator` strategy so OI reduces to low-rank (the existing `reduce_with_basis` + `eval_rows_in_grid_basis`) and GMRF persists its precision directly — covering both the gridded block and the on-worker eval-point predictives, with no special-casing in `application/solve.py`.

The dependency rule holds (`application/ → distributions/`, one-way); the protocols are untouched.

---

## 5. Committed interfaces and abstractions

Signatures are **illustrative** — contracts and seams, not prescribed internals — and reference real `sverdrup` symbols. Map names onto the actual layout; correct where it differs.

### 5.1 The GMRF method — `methods/gmrf.py` (new), registered in `methods/registry.py`

Plugs in at `Method.solve → PredictiveDistribution` exactly like `OptimalInterpolation`, producing a sparse-precision-backed `CovarianceOperator` (`fidelity=EXACT`) wrapped in a distribution.

```python
class GMRFCovarianceOperator:  # implements core.distribution.CovarianceOperator
    fidelity = CovFidelity.EXACT

    # Built from a regular-grid finite-difference discretization of the Matern SPDE
    # operator (kappa^2 - Laplacian) on the GridSpec nodes -> sparse precision Q.
    # kappa from the ParameterProvider (scalar OR latitude-varying field; nonstationary
    # kappa makes Q's coefficients spatially varying).
    # Core: sparse Cholesky Q = L L^T with a fill-reducing permutation, serving all three:
    def cov(self, a: Points, b: Points) -> np.ndarray: ...          # selective/partial inverse blocks
    def marginal_var(self, a: Points) -> np.ndarray: ...            # exact, Takahashi selective inverse
    def posterior_sample(self, s: Points, seed: Seed, m: int) -> np.ndarray: ...  # L^-T w draws

class MaternGMRF:  # implements core.method.Method
    native_capability = UncertaintyCapability.SAMPLES   # also exposes COVARIANCE
    def solve(self, obs, grid, params, time_days) -> PredictiveDistribution: ...
    def parameter_space(self) -> ParameterSpace: ...
        # range / correlation length (kappa<->range mapping), marginal variance (tau),
        # temporal_taper_scale (GMRF's analog of OI's time_scale; see "Conditioning" below);
        # smoothness nu exposed but fixed to an integer alpha for Phase 3 (clean stencil).
```

**Sparse backend (settled).** Use **`scikit-sparse` (CHOLMOD)** for the sparse Cholesky, in **simplicial** mode (Takahashi walks `L`'s pattern in reverse elimination order). One factor `L` serves all three: sampling (`L⁻ᵀ w`), the posterior mean (full solve `Q_post μ = Aᵀ R⁻¹ y`), and `cov` blocks. CHOLMOD supplies the fill-reducing ordering (AMD/METIS, deterministic and recorded) and triangular + full solves; it has **no** selective inverse, so **hand-roll Takahashi** for `diag(Q⁻¹)` and the near-neighbour `Q⁻¹` entries over the `L+Lᵀ` pattern. **Adjacency precondition (assert + test):** the bilinear eval-point operator `W` couples a point to its 4 surrounding nodes, and `firstdifference` reads `cov` between adjacent nodes — so the `Q⁻¹` entries between adjacent nodes must lie inside the selective-inverse (`L+Lᵀ`) pattern. For the `(κ²−Δ)` α=2 stencil they do; add an explicit assertion of that adjacency precondition so a future wider κ-stencil cannot silently break eval-point variance or the cancellation path. Dependency added via conda-forge; if osx-arm64 build gaps appear, pin under `[target.linux-64.dependencies]` (linux-64 is the compute/CI target — local-Mac build issues must not block it). Keep a **pure-scipy dense `Q⁻¹`** path **only** as the small-grid Stage-B test reference, never as the production backend.

**Conditioning on the space-time obs window (settled — temporal taper into R).** The spatial GMRF conditions via `Q_post = Q_prior + Aᵀ R⁻¹ A`, with `A` the bilinear grid→obs **spatial** interpolation and `R` the per-obs error variance **inflated by each obs's time-offset from the output time** (obs further in time get larger `R`, contribute less). Time enters through the **likelihood**, not the prior — no temporal lattice axis (3-D SPDE is out of scope). Three requirements: (1) the **temporal-taper scale is a tunable parameter** in `parameter_space()` resolved through the `ParameterProvider`, never hardcoded — GMRF's parameter space is range + marginal variance + `temporal_taper_scale` (+ fixed ν); (2) build `A` (grid→obs, conditioning) and the eval-point `W` (grid→withheld, predictives) from **one bilinear interpolation primitive**, so `Aᵀ R⁻¹ A` and `W Σ Wᵀ` stay consistent; (3) record the conservative approximation as a `known_bias` in the method's provenance/docs — a diagonal-`R` taper treats temporal decorrelation as per-obs independent inflation, not a true temporal covariance, so it **under-uses** temporal structure (conservative, never over-claiming). The OI-vs-GMRF asymmetry is deliberate (OI carries a full space-time kernel; GMRF carries spatial covariance + a temporally-tapered likelihood) and the Stage-B accuracy/calibration comparison is read with that asymmetry visible — a real method difference, not a bug.

**Off-grid eval-point predictives.** A regular-grid GMRF lives on grid nodes, so off-grid withheld points use a (bilinear) interpolation operator `W` from grid nodes to eval points: the eval-point mean is `W·mean`, the eval-point coherent member is `W·(grid coherent member)`, and the eval-point marginal variance is `diag(W Σ Wᵀ)` using the selective-inverse entries within the interpolation stencil (which lie in the Takahashi pattern). The marginal-variance map is never interpolated (invariant; consistent with Phase-1 invariant 7).

**Projection abstraction (forward-compat; do NOT expand Phase-3 scope).** Keep **precision-node space** and **output-grid space** conceptually distinct even though in the regular-grid GMRF they coincide. The node→query projection `W` is the *general* way any field/covariance is read off the precision — `mean → W·mean`, `cov → W Σ Wᵀ` (Σ = selective-inverse entries within `W`'s stencil, never dense), coherent member → `W·(node-space member)`. The **gridded block is the case `W = identity-on-grid-nodes`**, expressed as a `GridIdentityProjection`, *not* an assumption baked into the operator; off-grid eval is a `BilinearProjection`; both come from the one bilinear primitive. The conditioning operator `A` (grid→obs) is itself a projection into node space. Consequence: a later phase supplying a different projection (a finite-element basis on a mesh whose nodes are **not** the grid) needs only that projection + a mesh-assembly routine — **no change to the precision representation (`PrecisionFields` stores `Q`/permutation/mean in node space), the `CoherentMemberDriver` (`mean + L⁻ᵀ w` is node-space-native, then projected), persistence, or the blend.** Phase 3 ships only the regular-grid identity + bilinear projections; the seam is what's load-bearing.

### 5.2 The representation-tagged persisted form — `distributions/persisted.py` (+ new precision storable)

```python
@dataclass(frozen=True)
class PrecisionFields:                  # NEW, beside PersistedFields (lowrank+diag)
    mean: Field
    precision: "sparse Q"               # sparse precision on the grid nodes
    permutation: np.ndarray             # fill-reducing permutation (persisted with Q)
    marginal_variance: Field            # exact, from selective inversion
    sampler_spec: str = "sparse-precision"   # the load-bearing discriminator

class PrecisionDistribution:            # implements PredictiveDistribution
    # marginal_variance from the stored field; covariance(a,b) from the cached factor /
    # selective inverse; sample via L^-T w; regrid via samples / covariance-operator.
    ...
```

`sampler_spec` (`"lowrank+diag"` vs `"sparse-precision"`) is the discriminator the `CoherentMemberDriver` dispatches on. Storage persists `Q` + permutation; the Cholesky factor is cached on use (sparse-storage-vs-recompute is an implementation detail). `BlendInput.distribution` widens to the abstract `PredictiveDistribution`.

### 5.3 The relocated coherence seam — `distributions/coherent.py` + `distributions/blend.py`

```python
@runtime_checkable
class CoherentMemberDriver(Protocol):   # the relocated seam, at the _coherent_member level
    def crossfaded_member(
        self, parts: Sequence[BlendInput], weights: np.ndarray,
        member_index: int, support, noise: NoiseSpec,
    ) -> np.ndarray:
        """One cross-tile-coherent, weight-crossfaded realization over the support."""
        ...

# Three instances, selected per-constituent by sampler_spec (representation), never by method:
#   LowRankSharedBasis        — repackage coherent_structured_field + diagonal (the current OI behavior)
#   GmrfPrecisionSolve        — mean + L^-T w (per tile, shared global w from diagonal_noise),
#                               weight-crossfaded; NATIVE coherence, no QR-basis trick
#   PerturbEnsembleDegradation — per-tile independent members, weight-crossfaded,
#                                coherence loss recorded in provenance (invariant 8)
```

`BlendedDistribution._coherent_member` delegates to the selected driver(s); the crossfade `Σ wᵢ·fieldᵢ` is representation-agnostic. The cheap path (`BlendOperator.blend`'s mean+σ crossfade via `_constituent_moments`) is already representation-agnostic and is unchanged.

### 5.3.1 AMENDMENT (2026-06-25) — GMRF cross-tile coherence is conditioning-by-kriging toward one global realization, NOT native shared-`w`

**This amendment corrects a settled-but-wrong decision.** §5.3's `GmrfPrecisionSolve` line — "`mean + L⁻ᵀw` (per tile, shared global `w` from `diagonal_noise`), weight-crossfaded; NATIVE coherence, no QR-basis trick" — was **under-specified for non-identical `Q`** and does not deliver the contract. It is replaced by the construction below. The provenance of the change is recorded here so the FEM phase reads the *why*, not just the *what*.

**The evidence (Stage-B validation, the distinct-tiles positive control).** Native shared-`w` shares the white noise in each tile's **factor space**; `x = L⁻ᵀw`. `L⁻ᵀ` (inverse Cholesky) is a **global** map, so two tiles whose precision is *locally identical in the overlap* still have different Cholesky factors (different fill / permutation / extent) and the same `w` produces **uncorrelated physical realizations**. Measured:

- **Distinct-tiles positive control** (genuinely distinct tiles, `nL, nR < nFull`, `Q_L ≠ Q_R`): overlap member correlation stays **≈ 0 (−0.06 … +0.03) at every halo `k = 1…5`**; an identical-tiles sanity case reads **1.000**. Coherence does **not** climb with halo when tiles stay distinct.
- The earlier 3-tile halo-sweep's apparent `corr → 1.000` at `k ≥ 2` was **degenerate**: on a small region the `k ≥ 2` extended windows each swallow the whole domain, so the tiles became *identical*, not *reconciled*. A gate that can pass this way is measuring the wrong thing on a degenerate fixture.
- **Cross-seam derived-quantity error**: the `firstdifference` (x-gradient) variance across the seam is **−0.51 relative to the single-tile reference** — under-dispersed by ~50%. This is *the* failure SPDE/GMRF was chosen to prevent.
- **Direction is suppression, not inflation** (counterintuitive, mechanism is load-bearing for the fix): independent halves would *add* variance, but the partition-of-unity crossfade `w_L·field_L + w_R·field_R` **averages** two near-independent draws, which *shrinks* the realized cross-seam difference. The artifact is therefore a **smoothing seam** — a spurious band of artificially-calm water at every tile boundary in every derived field. A reviewer catches this in a velocity map; it cannot ship recorded-and-accepted.
- **The marginal σ-bound is real but structurally blind to this.** Reported `σ = Σwσ` is a valid **pointwise upper bound everywhere** (reported ≥ sampled at 81/81 nodes; max `sampled/reported = 0.97`). A conservative-direction (option-1) contract would hold for *per-point* uncertainty — but a per-point upper bound says nothing about the *joint* structure a derivative reads, so it does not rescue D1. Marginally-honest, derived-quantity-dishonest.

**(a) The mechanism, as a validity claim (not a recipe).** Conditioning-by-kriging on the GMRF: draw an unconditional per-tile sample `x_u`, then correct it to agree with a shared realization on the shared (overlap) nodes,

```text
x_corrected = x_u + Σ_cross · Σ_shared⁻¹ · (x_shared − x_u|shared)
```

where `Σ_shared`, `Σ_cross` are blocks of the tile posterior covariance (read off the precision via the selective inverse / factor — never densely). **Validity invariant (the theorem it rests on):** `x_corrected` must be an **exact sample of that tile's posterior**, because conditioning by kriging preserves the correct conditional law — *not* merely a draw that happens to match on the overlap. A correction that matched the overlap while distorting the interior law would trade a visible seam artifact for a worse, hidden one. **Oracle discipline (same as Takahashi):** corrected draws are verified to be exact posterior samples against a dense reference on a small grid; a red is a math bug, not a tolerance.

**(b) ONE global node-space realization, not pairwise overlaps.** Every tile conditions toward a **single shared global node-space realization**, so coherence is **transitive by construction**. Pairwise-negotiated overlaps re-create the original bug one level up: with three tiles in a row, the L–C and C–R overlaps share tile C, and pairwise conditioning asks C to match two different shared draws — the seam-of-the-seam. This is precisely the class of bug that **passes a 2-tile test and fails a 3-tile one** (the trap this phase already fell into once). The shared realization is generated once in node space and every tile — regular-grid now, FEM later — conditions against the same draw.

**(c) The promoted test contract (replaces the corr-proxy on a degenerate fixture).** Task-9's Stage-B gate asserts, on a fixture **constructed so tiles cannot collapse to identical**:

- **Distinct-tiles-by-construction:** `nL, nR < nFull` and `Q_L ≠ Q_R` — forbid the region/halo combinations where `k ≥ 2` tiles swallow the domain. (The old member-correlation proxy alone is insufficient and is demoted to a supporting check.)
- **Cross-seam DERIVED-quantity parity:** `firstdifference` (x-gradient) variance across the seam within tolerance of the single-tile reference, **in the conservative direction** — this, not member correlation, is the contracted property.
- **Conservative marginal direction:** reported `σ ≥ sampled σ` pointwise (retained; necessary, not sufficient).
- **Validity oracle:** corrected draws equal exact posterior samples vs a dense reference on a small grid.

**Scope honesty.** This is the **most invasive addition since Phase 2**: sampling becomes **cross-tile-coupled** — a tile's draw now depends on a shared realization, not its own solve alone. It repairs the under-specified Checkpoint-2 "native shared-`w`, no QR trick" line, which was simply wrong for non-identical `Q`; the distinct-tiles positive control is the evidence. It is **not** the QR-basis trick (that note guarded against low-rank's basis-orientation fix, which has no bearing on a precision representation). **It buys FEM for free:** conditioning-by-kriging is representation-native and **projection-agnostic** — it operates on the precision and the shared node-space realization, both of which the `Projection` abstraction already keeps in node space — so the FEM phase inherits coherent cross-tile sampling with no further work. The cost lands once, here, and the canonical case Phase 4 cares about gets it gratis.

### 5.4 The per-operator reduction strategy — `core/distribution.py` + `application/solve.py`

```python
class CovarianceOperator(Protocol):     # extended with a persistence strategy
    def to_persisted(self, grid, eval_points, *, rank, seed): ...
        # OI  -> low-rank+diagonal (reduce_with_basis + eval_rows_in_grid_basis), sampler_spec="lowrank+diag"
        # GMRF-> sparse precision direct (+ selective-inversion marginal variance),
        #        eval-point predictives via the W interpolation operator, sampler_spec="sparse-precision"
```

`application/solve.py` calls `operator.to_persisted(...)` (or an equivalent strategy object) for both the gridded block and the on-worker eval-point predictives; it no longer hardcodes the low-rank reduction.

### 5.5 The degradation driver, end-to-end — closes the Phase-2 gap

The `PerturbEnsembleDegradation` instance runs through the tiled blend for a deterministic method (the existing `trivial.py` / Method 0, or a deterministic variant): coherence loss is recorded in the typed provenance chain, and the seam is provenance-flagged rather than a silent crack. Asserts: degradation provenance present; samples per-tile-independent-but-documented; no silent seam.

### 5.6 Nonstationary κ demonstration

κ is provider-driven; a latitude-varying-κ GMRF case is demonstrated (correlation length ~100→800 km), as the SPDE differentiator and the Phase-4 parameter-field precedent. The κ↔range mapping is recorded; nonstationary κ makes `Q`'s coefficients spatially varying.

---

## 6. Non-goals (Phase 3 does NOT do these)

- **The autotune loop and any optimizer** (Phase 4). `parameter_space()` is the declarative surface; Phase 3 does no tuning.
- **Additional methods** beyond OI + GMRF (plus the existing trivial for the degradation path). MIOST / DYMOST / BFN-QG / 4DVarNet remain future. (BFN-QG was considered as a different-*science* degradation method and deferred.)
- **FEM meshing / coastline-following / irregular domains** — regular-grid GMRF only.
- **Cross-representation coherent blending** (mixing OI and GMRF tiles coherently in one blend). Homogeneous-per-blend; a mixed blend takes the degradation path.
- **Tunable/continuous smoothness ν** — ν is fixed to an integer α for a clean stencil in Phase 3; range and variance are the live tunable surface for Phase 4.
- **Cloud / multi-node execution** (still `LocalCluster`, address-only scale-out); **SWOT / 2-D swath**; **recalibration machinery**; **full-correction double-counting** — all still deferred.

**If any of these appears necessary to make Phase 3 work, stop and ask — do not build it.**

---

## 7. Definition of done

**Stage A — generalize under green (the safety refactor; the gate before GMRF).** Relocate the coherence seam to `CoherentMemberDriver`; representation-tag the persisted form; generalize the reduction boundary to a per-operator strategy. Refactor the *existing* OI/low-rank path onto all three. **The full Phase-2 suite (129 passed / 2 skipped) still passes — OI through the new seam reproduces Phase-2 results exactly.** This regression gate must be green before adding GMRF.

**Stage B — add the GMRF method (the validation).** Regular-grid Matérn GMRF plugged in at `Method.solve`; sparse-precision `CovarianceOperator` (`EXACT`); sparse Cholesky core; exact selective-inversion marginal variance; provider-driven κ; `SAMPLES + COVARIANCE`. GMRF produces gridded + on-worker eval-point predictives (W-interpolation for off-grid points). The method-agnostic blend runs GMRF globally (homogeneous) through the gmrf-precision-solve driver: coherent samples seam-free (native shared-`w` coherence, no QR trick), no mid-overlap variance dip, the blended product matches a single-tile GMRF reference within tolerance, conservative direction holds, provenance carries the `BlendTransform` and the sparse-precision tag. Accuracy + calibration evaluators fire on the GMRF blended product in OSSE and OSE; exact marginal variance keeps calibration honest. **A genuine-first-class test:** the GMRF representation is never reduced to low-rank anywhere — assert `sampler_spec="sparse-precision"` survives end-to-end and no low-rank factor is materialized for GMRF.

**Stage C — degradation path + nonstationary demo.** The perturb-ensemble degradation driver runs end-to-end through the tiled blend (deterministic method): coherence loss recorded in provenance, no silent seam — closing the Phase-2 gap. A latitude-varying-κ GMRF case is demonstrated (nonstationary, provider-driven).

---

## 8. Decision log

All Phase-3 forks are closed. Method: **regular-grid Matérn GMRF** (sparse precision), not FEM. κ: **provider-driven, nonstationary-capable, stationary-first plus a latitude-varying demo**; ν fixed to an integer α (clean stencil), continuous ν deferred. Marginal variance: **exact via Takahashi selective inversion**. Blend scope: **homogeneous-representation-per-blend** (mixing structurally allowed → degradation path). Coherence seam: **relocated to `CoherentMemberDriver`** (three instances — low-rank-shared-basis, gmrf-precision-solve, perturb-ensemble-degradation — dispatched by `sampler_spec` representation tag, never method identity), retiring the bypassed `MemberSeededZr`/`StructuredNoiseSource`. Persistence: **representation-tagged** (sparse-precision first-class beside low-rank+diagonal; `sampler_spec` load-bearing; `BlendInput.distribution` widened to abstract `PredictiveDistribution`). Reduction: **per-operator strategy** (`to_persisted`), covering gridded block + eval-point predictives. Degradation: **exercised end-to-end**. Sequencing: **generalize OI under the green Phase-2 suite, then add GMRF**. **No open Phase-3 architectural questions remain.**

**AMENDMENT 2026-06-25 (Stage-B validation finding).** GMRF cross-tile coherence: the §5.3 "native shared-`w`" line was **wrong for non-identical `Q`** and is replaced by **conditioning-by-kriging toward one global node-space realization** (see §5.3.1). Evidence: a distinct-tiles positive control showed overlap member correlation ≈ 0 at every halo (the prior `corr→1` was a degenerate identical-tiles artifact), and the cross-seam `firstdifference` variance was −0.51 vs the single-tile reference (a smoothing seam). The marginal `σ = Σwσ` bound stays pointwise-conservative but is structurally blind to the joint/derived defect, so the cheaper record-and-accept path is insufficient. Fix is **cross-tile-coupled sampling** (single global realization → transitive coherence, not pairwise overlaps), with a validity oracle (corrected draws == exact posterior samples vs a dense small-grid reference) and a promoted Task-9 gate (distinct-tiles-by-construction + cross-seam derived-quantity parity, conservative direction). Representation-native and projection-agnostic ⇒ FEM (Phase 4) inherits it for free.
