# Phase-4 Scope Specification
### FEM/triangulation SPDE and the non-chain coherent sampler (`sverdrup`)

**Status:** Settled. Both brainstorm checkpoints are closed; no open Phase-4 architectural questions remain.
**Purpose:** Single authoritative reference for the Phase-4 build. Supersedes the Phase-4 scoping conversation; self-contained; the basis from which the Phase-4 Claude Code prompt is written. Mirrors `phase1`/`phase2`/`phase3_scope_spec.md`.
**Builds on:** the real `sverdrup` codebase at the current Phase-3 HEAD (`31a58c6`), verified by source read. Phase 4 extends and refactors it; it does not start over. This spec references real symbols (`GMRFCovarianceOperator`, `GridIdentityProjection`/`BilinearProjection`, `GmrfKrigingSolve`, `_assert_separates`, `PrecisionDistribution`, `GMRFPrecisionReduction`, `select_driver`, `GMRFFactor`, `bilinear_weights`, `matern_precision`).
**Governing discipline:** Generalize under the green Phase-3 suite *before* extending. Separate the two hard problems (2-D tile topology vs unstructured mesh). Decide the abstractions to stay discretization-agnostic. Do not pre-engineer Phase 5 (autotune).

---

## 1. Project north star (context)

The framework ingests heterogeneous nadir altimetry and produces a global gridded SSHA product with rigorous per-gridpoint uncertainty, a method-comparison layer, and (eventually) an autotune loop. Phase 1 built the abstractions + a regional tile; Phase 2 the method-agnostic tiling/blend → global; Phase 3 added a sparse-precision GMRF and proved the spine is representation-agnostic. **Phase 4 extends the GMRF from a regular-grid discretization to the canonical Lindgren–Rue–Lindström finite-element (FEM/triangulation) SPDE**, and replaces the chain-only cross-tile coherent sampler with a topology-agnostic one — because 2-D and mesh tiling break the tree assumption the chain sweep relies on. Autotune is Phase 5.

---

## 2. Phase-4 objective, scope, and build philosophy

**Objective.** Make the GMRF discretization-agnostic in practice — a FEM mesh discretization validated through the method-agnostic blend, proving "discretization is a projection/assembly swap, not a rewrite" — and replace the chain-only coherent sampler with one that is correct for 2-D and mesh tile topologies, certified by a positive control on genuinely-distinct tiles.

**Scope — exactly what Phase 4 does, in three stages (and nothing else):**
- **Stage A — generalize under green.** Wire the GMRF operator and the persisted form onto a *real* Projection seam they consume (today `GMRFCovarianceOperator` and `PrecisionDistribution` hardcode `bilinear_weights(self.grid, …)`; `GridIdentityProjection`/`BilinearProjection` exist but are consumed nowhere), and de-grid the persisted form (carry a node-space/projection, not a `GridSpec`; flat-node fields, not `(ny,nx)` arrays). The green Phase-3 suite is the regression oracle. This folds in the three source-grounded corrections from scoping.
- **Stage B — the non-chain coherent sampler, on the *grid* first.** Replace `GmrfKrigingSolve`'s 1-D lon-chain sweep with a topology-agnostic coherent sampler, developed and validated on **2-D grid GMRF tiling** (coincident nodes; the topology problem isolated from the mesh problem), with a positive control on genuinely-distinct tiles.
- **Stage C — FEM.** Add the FEM discretization: a global/shared-node triangulation, FEM precision assembly (mass + stiffness → `Q`), and a FEM-basis Projection — inheriting the now-2-D-capable sampler — and demonstrate one FEM-specific payoff (boundary extension / data-adaptive refinement) that the regular grid cannot deliver.

**Why this is the order.** The chain-only limitation is *not* FEM-specific: `GmrfKrigingSolve` sorts tiles by core-lon and `_assert_separates` checks lon columns, so the grid GMRF already cannot tile in 2-D. Phase 4 therefore contains two *separable* hard problems — (i) 2-D tile topology for the coherent sampler, and (ii) unstructured mesh. Combining them in one step means debugging both at once, the exact confounding the Phase-3 meta-lesson warns against. So the topology problem is solved and certified on the grid (Stage B) before the mesh problem is added (Stage C), which makes Stage C a near-pure discretization swap *because* the seam is wired and the sampler is already topology-agnostic.

**Build philosophy.** The precision representation is genuinely discretization-agnostic and reused untouched: `GMRFFactor`, `selective_inverse()`, `posterior_cov_columns()`, `sample(white)` operate on any sparse SPD `Q`. The `ReductionStrategy` seam (`GMRFPrecisionReduction` via `select_reduction`) and the `CoherentMemberDriver` seam (`select_driver` by `sampler_spec`) are real and reused. Same Phase-1 "Decision B" data discipline (real ODC adapter, scoped footprint, committed fixtures, opt-in oracle/global). Prove regionally, then opt-in global.

---

## 3. Hard constraints (Phase-4 invariants)

Load-bearing; do not optimize away. Phase-1 invariants 1–10, Phase-2 invariants 1–12, and Phase-3 invariants 1–11 all still bind. These add the FEM and coherent-sampler specifics.

1. **Generalize under green before extending.** Stage A (Projection-seam wiring + de-grid persistence) and Stage B (non-chain sampler on the grid) keep the full Phase-3 suite green at every step — the existing OI and grid-GMRF behavior must be reproduced exactly. A red means the generalization changed behavior; surface it, do not loosen the test.
2. **The operator and persisted form consume a Projection seam; nothing hardcodes the read-off.** `W` (node→query) is produced by a `Projection` the operator/persisted form hold — `GridIdentity`/`Bilinear` for grids, `FEMBasis` for meshes. The conditioning operator `A` (node→obs) is the same `Projection` evaluated at obs points. No `bilinear_weights(self.grid, …)` call sites, no `grid.shape` reshapes, remain in the operator or persisted form.
3. **The persisted form is node-space-described, not grid-described.** It carries the node space / projection (grid *or* mesh), stores fields as flat node vectors where the node space is unstructured, and never assumes `(ny,nx)`.
4. **Coherence comes from conditioning; per-tile white noise is independent, not shared.** Each tile's unconditional draw uses independent per-tile white (keyed by tile/member), because the kriging correction requires the unconditional draw independent of the conditioning targets. Proven by the per-tile full-covariance oracle (corrected ensemble covariance == exact `(Qⁱ)⁻¹`), not asserted. (Phase-3 lesson, preserved.)
5. **The coherent sampler is topology-agnostic; the tree/separator requirement is removed, not assumed-away.** The replacement (pre-drawn-joint, §5.3) does not depend on tile-adjacency being a chain/tree. Any remaining precondition is asserted with a negative control (e.g. a too-narrow-overlap red), mirroring `_assert_separates`.
6. **The coherent sampler is certified by a positive control measuring the contracted property, on genuinely-distinct tiles.** The control measures cross-seam derived-quantity parity and joint covariance — never an incidental property (member correlation, marginal variance, blanket positivity), and never on a degenerate fixture where tiles collapse to identical precisions. (The Phase-3 meta-lesson, made a standing gate.)
7. **Correct-or-honestly-bounded, never silently wrong.** If the pre-drawn-joint construction approximates the auxiliary joint-strip draw at scale, the residual is measured and recorded (conservative direction, `known_bias`), exactly like the halo residual — not hidden. The Phase-3 saga was about *silent* under-dispersion, not inexactness.
8. **GMRF coherence remains representation-native and projection-agnostic.** The sampler operates in node space through the same `GMRFFactor`/`posterior_cov_columns` hooks; it does not assume a grid or a particular projection, so FEM inherits it once the seam is wired.
9. **FEM is a global/shared-node mesh in Phase 4.** One triangulation over the domain; tiles are node subsets of it, so overlaps share mesh nodes and the coincident-node conditioning mechanism continues to work — keeping Stage C a discretization swap rather than also a non-coincident-bases problem. Per-tile independent meshes are deferred (§6).
10. **Exact marginal variance via Takahashi selective inversion** — unchanged; the FEM `Q` is just another sparse SPD precision; off-mesh evaluation uses `diag(W Σ Wᵀ)` with the FEM-basis `W`, never an interpolated variance map.
11. **Determinism preserved.** Independent per-tile white, the pre-drawn joint-strip field, and any new randomness are deterministic (global-lattice / tile-keyed seeds), order-independent, and recorded.

Carry-forward invariants unchanged: the protocols (`Method`/`PredictiveDistribution`/`CovarianceOperator`) stay representation-agnostic and untouched; the dependency rule (`application → distributions`, one-way; the `ReductionStrategy` lives in `distributions/`, not on a core Protocol); conservative-direction-and-record; calibration first-class; never interpolate a variance map; OSSE and OSE both; the cheap blend path is representation-agnostic.

---

## 4. The two generalizations (how invariants 1–9 cohere)

**(a) The Projection seam, made load-bearing (Stage A).** Today the read-off is hardcoded: `GMRFCovarianceOperator.marginal_var/cov/posterior_sample` and `PrecisionDistribution.covariance/sample` call `bilinear_weights(self.grid, …)` and reshape to `grid.shape`; the `Projection` dataclasses are dead. Phase 4 introduces a `Projection` the operator and persisted form *hold and call* — abstracting both the linear map `W` and the node-space description — with `GridIdentity`/`Bilinear` (grid) refactored onto it under green, and `FEMBasis` (mesh) added in Stage C. This is the precursor the "just a projection swap" framing omitted.

**(b) The non-chain coherent sampler (Stage B).** `GmrfKrigingSolve` is exact only for a tree-structured tile chain: it orders tiles by core-lon, conditions each on the single already-processed neighbour's overlap, hands the corrected overlap forward, and `_assert_separates` requires the overlap to Q-separate processed/unprocessed interiors. 2-D tiling breaks this (a tile has multiple processed neighbours; the adjacency is not a tree). The replacement is **conditioning-by-kriging toward ONE pre-drawn joint field over the union of all overlap strips**: draw a single auxiliary sample over the strip-network up front, then each tile kriges its *independent* unconditional draw toward its overlap values read from that one field. Correctness no longer depends on tile-adjacency topology (no tree/separator requirement) because every tile conditions toward one globally-consistent field on all overlaps simultaneously. The auxiliary field is drawn from the global prior restricted to the strips (a thin sub-GMRF, far lower-dimensional than the full field); if that draw is approximated at scale, the residual is bounded-and-recorded (invariant 7). **Junction-tree is the noted exact fallback** if the positive control reveals the pre-drawn-joint residual is unacceptable — not built unless needed (mirrors Phase-2's hand-off-primary / full-correction-fallback).

---

## 5. Committed interfaces and abstractions

Signatures are **illustrative** — contracts and seams, not prescribed internals — and reference real symbols. Map names onto the actual layout; correct where it differs.

### 5.1 The Projection seam — consumed by the operator and persisted form

```python
@runtime_checkable
class Projection(Protocol):
    """Reads any field/covariance off the precision: node space + the W map to queries."""
    node_space: object                 # GridSpec OR Mesh (the node layout the precision lives on)
    def weights(self, pts: Points) -> "sparse (k, n_nodes)": ...   # W; A is this at obs points
    def field_shape(self) -> tuple[int, ...]: ...                  # (ny,nx) for a grid; (n_nodes,) for a mesh

# Instances:
#   GridIdentityProjection / BilinearProjection  — grid (refactor the existing dataclasses INTO use)
#   FEMBasisProjection                            — mesh: W_{ki} = psi_i(s_k), the FEM basis at queries
```

`GMRFCovarianceOperator` and `PrecisionDistribution` **hold a `Projection`** and route `marginal_var`/`cov`/`posterior_sample`/`sample`/`covariance` through it (`W = projection.weights(pts)`, `diag(W Σ Wᵀ)` off-node), instead of calling `bilinear_weights(self.grid, …)` or reshaping to `grid.shape`. Under green, the grid path produces byte-for-byte the Phase-3 result (invariant 1).

### 5.2 The de-gridded persisted form — `distributions/persisted.py`

`PrecisionFields`/`PrecisionDistribution` carry the **projection / node space** (not a bare `GridSpec`) and store `mean`/`marginal_variance` in the projection's `field_shape` (flat node vectors for a mesh). `posterior_cov_columns`, `_factor_obj`, the `GMRFFactor`, and Takahashi are unchanged. `regrid` (still `NotImplementedError` in the source) remains out of Phase-4 scope unless Stage C needs it for the payoff demo, in which case it goes via samples/covariance-operator (never the variance map).

### 5.3 The non-chain coherent sampler — `distributions/coherent.py`

A new `CoherentMemberDriver` instance for `sampler_spec="sparse-precision"`, replacing `GmrfKrigingSolve`'s chain sweep (the registry `_DRIVERS["sparse-precision"]` is repointed):

```python
class GmrfJointKrigingSolve:   # topology-agnostic; replaces the lon-chain GmrfKrigingSolve
    # 1. Build the strip-network: the union of all tile overlap node sets.
    # 2. Draw ONE auxiliary joint field over the strip-network (global prior restricted to
    #    strips; a thin sub-GMRF). Deterministic seed; if approximated at scale, residual recorded.
    # 3. Per tile: independent per-tile white -> unconditional x_u = mean + L^-T w;
    #    krige-correct toward this tile's overlap values READ FROM the one joint field
    #    (cols = posterior_cov_columns(shared_idx); x_c = x_u + cols @ solve(sigma_ss, x_joint - x_u|_S)).
    # 4. Weight-crossfade the corrected per-tile fields (partition-of-unity), as today.
    # No tree/separator requirement; any residual precondition asserted with a negative control.
```

Independent per-tile white (invariant 4) is preserved; the only change from `GmrfKrigingSolve` is that conditioning targets come from one pre-drawn joint field over *all* overlaps rather than handed forward along a chain. Validated on **2-D grid** tiling first (coincident nodes), with the distinct-tiles positive control (invariant 6) and a too-narrow-overlap negative control. The positive control **measures the residual against the single-tile reference and records it** (conservative known_bias); it is not pass/fail in isolation. A red means the construction is **inadequate**, not merely approximate; the junction-tree fallback (§6) is triggered **only if the recorded residual exceeds tolerance**, never because the construction is approximate.

### 5.4 FEM discretization — `methods/fem.py` (new), registered in `methods/registry.py`

```python
def fem_precision(mesh, kappa, tau) -> "sparse Q":
    # Lindgren-Rue-Lindstrom: mass C (lumped -> diagonal for sparsity) and stiffness G on the
    # triangulation; alpha=2 (nu=1): Q = (1/tau) (kappa^2 C + G) C^-1 (kappa^2 C + G).
    # kappa from the ParameterProvider (scalar OR field; nonstationary -> spatially-varying coeffs).

class FEMMatern(MaternGMRF-shaped):   # same Method contract; produces a GMRFCovarianceOperator
    # solve(): build the global/shared-node mesh (boundary-extended, optionally data-adaptive),
    # assemble Q via fem_precision, condition with A = FEMBasisProjection at obs points,
    # wrap in a GMRFCovarianceOperator holding the FEMBasisProjection. SAMPLES + COVARIANCE.
```

The mesh is **global/shared-node** (invariant 9): one triangulation; tiles are node subsets sharing overlap nodes. Mesh generation uses **scipy.spatial.Delaunay** (no new dependency) over an arbitrary input point set, with **hand-rolled P1 assembly** (lumped-mass diagonal C + stiffness G), matching the hand-rolled GMRFFactor/Takahashi approach. Both Stage-C payoff demos are driven by the input point set — an extended **boundary ring** → boundary extension that removes edge variance inflation; **locally-densified points** → data-adaptive refinement — the things the regular grid cannot do, demonstrated, not productionized.

**Mesh-quality guard (the FEM analogue of _assert_separates).** fem_precision asserts a minimum triangle quality (minimum angle / aspect ratio) on the assembled mesh and fails loudly on a sliver triangulation, rather than letting a degenerate triangle inflate G and dent Q's conditioning. This is a checked precondition with a loud red (mirroring invariant 5), so a meshing artifact never masquerades as a bad method and never falsely reddens the genuine-discretization-swap test.

---

## 6. Non-goals (Phase 4 does NOT do these)

- **Per-tile independent meshes** (non-coincident nodes; conditioning on shared physical points across differing bases). Phase 4 uses a global/shared-node mesh; per-tile meshes are deferred.
- **Junction-tree coherent sampler** — noted as the exact fallback only; built only if the pre-drawn-joint positive control shows an unacceptable residual.
- **Full irregular-domain / coastline-following production** — the boundary-extension / adaptive-refinement *demonstration* is in scope; a production coastline system is not.
- **Production-quality meshing** (Shewchuk triangle/meshpy: min-angle/max-area constraints, Steiner points) — the demo uses scipy.spatial.Delaunay; a quality mesher is the clean upgrade **behind the same fem_precision / FEMBasisProjection seam, with no change to the representation**, if a production irregular-domain capability is ever needed.
- **The autotune loop and any optimizer** (Phase 5); `parameter_space()` exists, no tuning.
- **Additional methods** beyond OI + grid-GMRF + FEM-GMRF (+ the trivial degradation method). MIOST / DYMOST / BFN-QG / 4DVarNet remain future.
- **Continuous/tunable ν** — fixed integer α=2 (clean assembly), as in Phase 3.
- **Cloud / multi-node execution** (still `LocalCluster`, address-only); **SWOT / 2-D swath**; **recalibration machinery**; **full-correction double-counting** — all still deferred.

**If any of these appears necessary to make Phase 4 work, stop and ask — do not build it.**

---

## 7. Definition of done

**Stage A — generalize under green (gate before the sampler and FEM).** The operator and persisted form consume a `Projection` seam; the grid `Projection` dataclasses are refactored into use; the persisted form is de-gridded (carries the projection/node space, flat-node-capable). The full Phase-3 suite (and the OI + grid-GMRF blend results) reproduce exactly — generalization changed no behavior.

**Stage B — non-chain coherent sampler (validation on the grid).** `GmrfJointKrigingSolve` replaces the lon-chain sweep; the grid GMRF tiles in **2-D** with seam-free coherent samples, no mid-overlap variance dip, blended product matching a single-tile GMRF reference within tolerance, conservative direction; independent-white and per-tile full-covariance oracles pass; the distinct-tiles positive control (cross-seam derived-quantity parity + joint covariance) passes; the too-narrow-overlap negative control fails loudly. The 1-D chain case still passes (regression).

**Stage C — FEM (the discretization swap + payoff).** `FEMMatern` plugged in at `Method.solve`; FEM precision assembly (`fem_precision`) and `FEMBasisProjection`; sparse-precision `CovarianceOperator` (`EXACT`); exact selective-inversion marginal variance; provider-driven κ; `SAMPLES + COVARIANCE`; gridded/eval read-off via the FEM `Projection`. The method-agnostic blend runs FEM-GMRF globally (homogeneous) through the inherited `GmrfJointKrigingSolve`: seam-free, conservative, provenance carries the sparse-precision tag and any recorded coherence residual. A **genuine-discretization-swap test**: FEM uses the same precision representation, reduction strategy, coherence driver, and blend as the grid GMRF, with only the precision assembly and projection differing (assert no grid-specific code path is taken for FEM). A **payoff demonstration**: a boundary-extended (and/or data-adaptive) mesh removes edge variance inflation the regular grid exhibits. Accuracy + calibration fire on the FEM product in OSSE and OSE. The mesh-quality guard rejects sliver triangulations (loud red), so meshing artifacts cannot masquerade as method failures.

---

## 8. Decision log

All Phase-4 forks are closed. Extension: **FEM/triangulation Matérn SPDE** (Lindgren–Rue–Lindström), reusing the precision representation / reduction strategy / coherence seam / blend. Sequencing: **Stage A generalize-under-green** (wire operator + persisted form onto a consumed `Projection` seam; de-grid persistence; fold in the three corrections) → **Stage B non-chain coherent sampler on 2-D grid first** (topology isolated from mesh) → **Stage C FEM** (mesh + projection inherit the sampler). Mesh: **global/shared-node**, generated by scipy.spatial.Delaunay + hand-rolled P1 assembly with a sliver-quality guard (Shewchuk meshing noted as the upgrade behind the same seam); per-tile meshes deferred, so coincident-node conditioning survives. Projection seam: **consumed by the operator and persisted form**, abstracting `W` + node-space (grid `field_shape` `(ny,nx)`, mesh `(n_nodes,)`). Coherent sampler: **conditioning-by-kriging toward one pre-drawn joint field over the overlap-strip network** (topology-agnostic, independent per-tile white, bounded-and-recorded if approximated), certified by a **distinct-tiles positive control** on cross-seam derived-quantity parity + joint covariance; **junction-tree noted as the exact fallback**, built only if needed. FEM payoff: **boundary-extension / adaptive-refinement demonstrated** (not productionized). Three source-grounded corrections (vestigial Projection seam, grid-coupled persistence, node-coincidence conditioning) **folded into Stage A as explicit work**. **No open Phase-4 architectural questions remain.**
