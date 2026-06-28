# Phase 4 — FEM/triangulation SPDE + non-chain coherent sampler

**Design doc.** Source of truth = `phase4_scope_spec.md` (settled + owner-amended, HEAD `00519b1`).
On any conflict the spec governs; this doc is the *implementation architecture* derived from it.

**Builds on:** `sverdrup` Phase-3 HEAD `31a58c6` (suite 178 passed / 2 skipped). Refactor, don't rewrite.

**Governing discipline:** Generalize under the green Phase-3 suite *before* extending. Separate the two
hard problems (2-D tile topology vs unstructured mesh). Three stages, three gates: A green → B;
B positive-control passes → C.

---

## 0. The owner-pinned correctness contracts (read first)

Phase-after-phase the failures have been *a correctness assumption riding inside a step that looks
like plumbing*. These are pinned here so each is a **test**, not a discovery. They are
referenced inline at the stage they bind; collected here so none is lost.

> **AMENDMENT (Stage-B design pivot, owner-confirmed).** Contracts **C1, C2, C4 below are RETIRED.**
> They pinned the spec-literal *synthesized strip-field* sampler (`_draw_joint`/`_strip_prior`), which
> was **disproved by measurement** (376× cross-seam, joint-cov rel-err 1.617; jitter is a cover-up;
> no low-dimensional coarse space; `cond(Σ_ss)≈4e8` intrinsic to the near-singular posterior). The
> Stage-B sampler is now **hand-forward conditioning along a max-overlap spanning tree of the tile
> adjacency** — non-tree edges carry a **bounded, recorded** coherence residual; junction-tree (§6) is
> the exact escalation only if a measured residual exceeds tolerance. Full trail + the three-assertion
> gate: PROGRESS.md "Cross-cutting decisions (canonical — Phase 4)". The replacement contracts are
> **C1′/C2′/C4′** stated immediately under each retired one. C3, C5, C6, C7 stand unchanged.

- **C1 — RETIRED (synthesized strip-prior on the induced subgraph).** Replaced by **C1′ — the
  spanning-tree sampler is correct on tree edges and bounded on dropped edges.** Build the tile-adjacency
  graph (edge weight = shared-node count), take its **max-overlap spanning tree**, hand-forward-condition
  each tile on its parent's already-drawn overlap **values** (the proven chain mechanism, which never
  excites the 4e8 `Σ_ss` because the residual `x_s − x_u|_S` is consistent). **Test (Stage-B gate):**
  on a 2×2 partition, tree-edge joint covariance vs a dense reference is **≤ the measured chain
  baseline** (~0.30, the halo-truncation residual already shipped green); the **dropped-edge** (the
  non-tree cycle edge) joint-cov residual is **≤ C·(tree-edge residual), C∈[2,3]** — a bounded
  transitive-coherence residual, NOT discontinuity. Marginal-variance checks do not catch this; the
  per-edge joint-covariance-vs-reference check does.

- **C2 — RETIRED (three white streams incl. joint-white).** Replaced by **C2′ — two white streams,
  reverting to the Phase-3 contract.** There is no synthesized joint field, hence no joint-white. The
  only streams are per-tile unconditional white, which must be pairwise independent (tile-white ⟂
  tile-white) so a child's unconditional draw is independent of the parent values it is conditioned
  toward (invariant 4). **Test:** distinct per-tile seeds; empirical cross-correlation between two
  tiles' unconditional draws ≈ 0 at the MC floor.

- **C4 — RETIRED (strip-prior per-node κ).** Replaced by **C4′ — nonstationary κ rides on the per-tile
  posteriors, no separate strip prior.** Each tile's `Q_post` already carries its provider-resolved
  per-node κ (Stage A / Task 2–3); the spanning-tree sweep conditions on those posteriors directly, so
  the nonstationary case needs no special strip-prior handling. **Test:** repeat the Stage-B gate
  (C1′ tree/dropped residuals + conservative direction) with a latitude-varying κ field; still
  conservative and within tolerance.

- **C3 — the `_diag` fast-path equivalence is a green, not a comment.** The cached `_diag`
  (native-node marginal variance) is "documented equivalent" to the projection slow path — exactly
  the thing that silently drifts when the projection layer changes underneath it. **Test:** on the
  native-node case, `operator._diag == diag(W Σ Wᵀ)` computed through `projection.weights(node_points)`
  + the selective inverse, tight rtol. Cheap; catches plausible-but-wrong marginal variance.

- **C4 — the strip-prior uses the same κ the tiles use, per-node, including nonstationary.**
  `_draw_joint` evaluates κ (and τ) **per strip node via the provider**, not a single scalar. In the
  latitude-varying-κ case the strip spans a range of κ; a scalar-κ joint draw conditions the tiles
  against a different prior than they were built from — a bias that surfaces only in the nonstationary
  case. **Test:** add the nonstationary-κ case to the **Stage-B** positive control (not only Stage C).

- **C5 — "no grid-specific path for FEM" is mechanically enforced, not eyeballed.** This is the test
  that proves the architectural claim of the whole phase. **Test:** during a FEM solve + reduce +
  blend, a guard makes `bilinear_weights` (and any `(ny,nx)` reshape) **raise if called**; the FEM
  path holds a `FEMBasisProjection` whose `field_shape` is `(n_nodes,)`. Enforced by construction +
  a raising guard, never by inspection. Fails loudly if someone later routes FEM through a grid
  shortcut.

Two smaller pinned confirmations:
- **C6 — coincident mesh nodes actually match across tiles.** `_node_keys` rounding (`decimals=6`)
  must resolve shared strip nodes at the coordinates Delaunay vertices land on. Global/shared-node
  mesh ⇒ shared vertices are exact, so it holds — but **assert** that the cross-tile shared strip
  node set is non-empty for adjacent tiles. Silent-empty-conditioning is precisely the per-tile-mesh
  failure mode being avoided; it must be a loud red, not an empty set.
- **C7 — the payoff margin is measured at the boundary, not interior-averaged.** `edge_var(FEM) <
  edge_var(grid)` is asserted **at near-boundary nodes** (the boundary-extension effect), since an
  interior-averaged comparison washes it out.

---

## 1. Dependency rule and seam placement

`application → distributions`, one-way; protocols on `core/`. The new `Projection` Protocol joins
`CovarianceOperator`/`Method`/`PredictiveDistribution` in `core/`. Concrete projections live where
their node space lives (`methods/`). No new runtime dependency (scipy.spatial.Delaunay is already
core). Reused untouched: `GMRFFactor`/`selective_inverse`/`posterior_cov_columns` (`gmrf_linalg.py`),
`GMRFPrecisionReduction` (`reduction.py`), the `CoherentMemberDriver`/`select_driver` seam
(`coherent.py`), the blend (`blend.py`).

---

## 2. Stage A — generalize under green (gate before B/C)

### 2.1 The Projection seam — `core/projection.py` (new)

```python
@runtime_checkable
class Projection(Protocol):
    """Reads any field/covariance off the precision: node space + the W map to queries."""
    node_space: object                            # GridSpec OR Mesh
    def weights(self, pts: Points) -> sparse      # W (k, n_nodes); A is this at obs points
    def field_shape(self) -> tuple[int, ...]      # (ny,nx) grid; (n_nodes,) mesh
    def node_points(self, time_days: float) -> Points
    def assert_adjacency(self, q) -> None         # node-space-specific read-off precondition
```

`assert_adjacency` is the node-space-dispatched precondition: the grid projection delegates to the
existing `assert_adjacency_in_pattern` (5-point neighbours in Q's pattern); the FEM projection
delegates to the mesh-edge-in-pattern + sliver guard (§4). The read-off precondition therefore
travels with the node space, not hardcoded in the operator.

### 2.2 Refactor the dead dataclasses INTO use — `methods/gmrf_grid.py`

- `GridIdentityProjection(grid)` — the node projection the operator and persisted form **hold**.
  `weights(pts) = bilinear_weights(grid, pts)` (a unit selector on nodes ⇒ identity there),
  `field_shape() = grid.shape`, `node_points(t) = grid.points(t)`, `assert_adjacency` →
  `assert_adjacency_in_pattern`. Replaces the hardcoded read-off.
- `BilinearProjection(grid, pts)` — the materialized off-grid query form; conforms to the protocol
  (`field_shape() = (len(pts),)`); consumed by the reduction eval-point path. Both dataclasses now
  load-bearing (invariant 2).

### 2.3 Operator — `methods/gmrf.py` `GMRFCovarianceOperator`

`__init__(projection, q_post, time_days)` (legacy `grid` still accepted → wrapped in
`GridIdentityProjection` internally, so Phase-3 call sites are untouched). `marginal_var` / `cov` /
`posterior_sample` route through `self.projection.weights(...)`; **no** `bilinear_weights(self.grid,…)`,
**no** `grid.shape` reshape remain (invariant 2). `_is_grid` → `_is_native_nodes` (compares against
`projection.node_points`). The cached `_diag` stays as an exactness/perf fast-path **and is pinned
equal to the slow path** by C3. `__init__` calls `projection.assert_adjacency(q_post)`.

### 2.4 De-grid persistence — `distributions/persisted.py`

`PrecisionFields` and `PrecisionDistribution` carry the **projection** (→ node space), not a bare
`GridSpec` (invariant 3). `covariance` / `sample` go through `projection.weights` + `field_shape`
(flat-node capable; never assumes `(ny,nx)`). A `.grid` property returns the node support (GridSpec,
or a mesh `PointSet` in Stage C) so the blend's existing `_nearest` / `_support_points` are unchanged.
`MaternGMRF.solve`, `GMRFPrecisionReduction.reduce` (`reduction.py:141-154`), and `solve.py:60`
thread the projection through.

### 2.5 Green strategy — zero Phase-3 test churn

Constructors accept **either** `grid` (legacy → internal `GridIdentityProjection`) **or** a
projection; internals route only through the projection. Regression oracle = the full Phase-3 suite
(178/2), specifically `test_gmrf_grid`, `test_gmrf_method`, `test_gmrf_linalg`,
`test_precision_distribution`, `test_reduction`, `test_gmrf_blend`, `test_gmrf_kriging_{driver,oracle}`,
`test_nonstationary_kappa`. **A red means the generalization changed behavior — surface it, do not
loosen the test** (invariant 1).

### 2.6 New Stage-A tests

- **C3 fast-path equivalence** (new): native-node `_diag` == slow-path `diag(W Σ Wᵀ)`. *Bug it
  catches:* projection layer drifting from the cached diagonal → plausible-but-wrong marginal var.
- Projection-conformance tests for `GridIdentityProjection` / `BilinearProjection` (weights shape,
  identity-on-nodes, `field_shape`). *Bug:* a dead dataclass silently not matching the protocol.

### 2.7 Stage-A gate (definition of done)

Operator + persisted hold no hardcoded read-off (grep-clean of `bilinear_weights(self.grid`,
`grid.shape` in those two); grid dataclasses consumed; persistence carries projection/node space,
flat-node capable; full Phase-3 suite + OI + grid-GMRF blend reproduce **exactly**.

---

## 3. Stage B — non-chain coherent sampler, validated on the grid (gate before C)

### 3.1 `GmrfTreeKrigingSolve` — `distributions/coherent.py` (spanning-tree hand-forward)

> **AMENDED — replaces the synthesized `GmrfJointKrigingSolve` (disproved; see §0 amendment +
> PROGRESS Phase-4 decisions).** The auxiliary strip field (`_draw_joint`/`_strip_prior`) is removed.

Repoint `_DRIVERS["sparse-precision"]` to `GmrfTreeKrigingSolve`. Reuse `posterior_cov_columns`,
`_node_keys`, `_nearest`, the weight-crossfade, and the proven chain solve. Steps:

1. **`_strip_network(parts)` → per-pair shared-node sets (kept).** Strip nodes = nodes of tile *i*
   falling in any other tile's `extended_window`, matched across tiles by `_node_keys`. Asserts the
   cross-tile shared node set is non-empty for adjacent tiles (**C6**).

2. **`_tile_adjacency` + `_max_overlap_spanning_tree`.** Build the tile-adjacency graph (edge weight
   = shared-node count; edges below `STENCIL_REACH` per axis are not edges), take the **maximum-weight
   spanning tree** (parent map + BFS order), and the **dropped** = real overlap edges not in the tree.
   Assert connectivity (a tile reachable by no edge ≥ reach is a loud red, **C6**) and per-tree-edge
   separation (`_assert_tree_edge_separates`, the per-edge analogue of `_assert_separates`).

3. **Per tile, in BFS order.** Independent per-tile white (`gmrf-tile:i × member`) → `x_u = mean +
   L⁻ᵀ w`. **Root:** unconditional. **Child:** krige toward its **parent's already-drawn** overlap
   **values** on the shared nodes: `x_c = x_u + cols @ solve(Σ_ss, x_parent|_S − x_u|_S)`,
   `cols = posterior_cov_columns(s_idx)`. Because `x_parent` is an actual draw from the same posterior
   family, the residual `x_parent|_S − x_u|_S` is **consistent (small)**, so the near-singular `Σ_ss`
   (`cond ≈ 4e8` on near-improper posteriors) is **never excited** — the mechanism the chain already
   relied on, now over a tree instead of a line.

4. **Weight-crossfade** onto output pts (unchanged).

The change from `GmrfKrigingSolve`: the line sweep becomes a max-overlap **spanning-tree** sweep. Exact
(chain-quality) on tree edges; **non-tree edges carry a bounded, recorded** transitive-coherence
residual. There is **no synthesized field** and **no joint-white** (C2′).

### 3.1a Why not the synthesized joint field, and why not junction-tree (recorded)

Measured on real natl60 tiles: a synthesized strip field (any precision — prior, posterior, or true
marginal — they are byte-identical at the strips) yields a draw inconsistent at strip scale with each
tile's unconditional draw; the near-singular `Σ_ss` amplifies that O(1) inconsistency into a 376×
cross-seam blowup / joint-cov rel-err 1.617. The error is **high-frequency** (90% in the complement of
the near-null subspace; a shared coarse-mode draw does not close it) and `cond(Σ_ss)≈4e8` is **flat
across halo width and resolution** (intrinsic, not a strip-resolution mismatch). **Jitter is a
cover-up** (gradient ratio 324→3.2 while joint-cov stays 0.61–0.73 wrong). **Junction-tree (§6)**
restores exactness on cycles but re-introduces tile-topology dependence and √(#tiles) treewidth — the
costs Stage B exists to remove; it is the **exact escalation**, taken only if a measured dropped-edge
residual exceeds tolerance, never by default.

### 3.1b Tree selection: minimum-eccentricity + eigmin-rooting (AMENDED — load-bearing)

> **SUPERSEDED 2026-06-27 (read PROGRESS "RESUME HERE (2026-06-27)" first).** Two corrections to the
> text below: (i) `_min_eccentricity_spanning_tree` was **reverted as a measured regression** (it
> manufactured a sibling-seam collapse; PROGRESS §1) — the live tree driver is the **max-overlap MST**
> (`_max_overlap_spanning_tree`), and the min-ecc / `_condition_root_scores` symbols are **removed from
> `coherent.py`**; (ii) the whole tree-driver sampler is now the **deferred `sparse-precision` default
> at a proven PHASE BOUNDARY** — it collapses the marginal, while the overwrite reference zeroes
> cross-seam covariance at operational range. The eigmin-rooting / conditioning-floor *reasoning* below
> is kept as Phase-5-relevant trail; the **shipped construction** is in `2026-06-27-stageb-…-design.md`
> + the phase-boundary disposition. Do NOT read §3.1b/§3.1c as live shipped design.

Two measured findings make the tree SELECTION part of the construction, not a free choice:

1. **Depth → instability.** Hand-forward kriging accumulates drift per hop; a deep tree routes the
   conditioning through the near-singular `Σ_ss` in an order that amplifies (10× at a depth-3 edge vs
   ~1.4× at depth 1). The shipped tree is therefore the **minimum-eccentricity, max-overlap** spanning
   tree (`_min_eccentricity_spanning_tree`) — a shallow star on the `k·corr_len` heavy-overlap regime;
   rel stays bounded (0.40–0.45) at 3×2/3×3 where the naive Kruskal MST reaches depth 3–4 and blows up.
2. **Eigmin-rooting (contract).** The blow-up root is the most near-singular tile (smallest
   `eigmin(Q_post)`): rooting there gives 31× rel vs 0.36–0.84 at any better-conditioned root. The tree
   roots at the **maximum-eigmin (best-conditioned) tile** (`_condition_root_scores = -eigmin`). **Test
   (negative control, in the gate):** rooting at the worst-conditioned tile blows up >1.5× the
   well-conditioned roots — a refactor that roots arbitrarily reintroduces the 31× and fails loudly.

### 3.1c The conditioning floor (the central finding — intrinsic, recorded)

With depth and rooting fixed, an elevated cross-seam residual remains around a near-singular tile and
**no tree removes it**: conditioning a tile with `eigmin≈2.5e-7` onto anything is ill-posed, and
hand-forward inherits that. Measured: the residual is **monotone in `eigmin(Q_post)`** and
**`tree_edge == chain_edge` EXACTLY at equal conditioning** — the tree sweep is not worse than the
plain chain on a near-singular tile. Therefore the construction has an **accuracy floor set by the
worst-conditioned tile's eigmin**, and the gate compares each tree edge to the **per-tile
conditioning-matched chain baseline** (same tile, same eigmin), not an easier well-conditioned chain.
The floor is a **characterized, recorded `known_bias`** (monotone in eigmin); junction-tree (§6) is the
exact escalation if a use case cannot tolerate it near near-singular tiles. **Phase-5 caveat:** the
floor is a function of `eigmin`, which `range` controls — the autotuner must treat cross-seam coherence
residual as a constraint, not a free variable (short range drives eigmin down and the floor up).

### 3.2 Negative control (per-tree-edge separation)

A **tree** edge whose shared overlap is thinner than `STENCIL_REACH` in the adjacency direction cannot
hand forward a consistent conditional → **loud red** per edge (`_assert_tree_edge_separates`). A tile
disconnected from the spanning tree (no edge ≥ reach) is also a loud red — never silently independent.

### 3.3 Validation on 2-D grid (topology isolated from mesh)

Minimal fixture: a **2×2 partition of one global grid** (exactly one interior corner — the minimal
strip-junction exerciser), genuinely-distinct tiles (distinct obs ⇒ distinct posteriors; never a
fixture where tiles collapse to identical Q — invariant 6). Tests (each states behavior + the bug it
catches, per test-design):

- **Positive control = the three coupled gate assertions, thresholds derived from the measured chain
  baseline (~0.30 on the 1-D natl60 case, the halo-truncation residual already shipped green):**
  **(1) tree-edge parity** `max_tree_edge_relerr ≤ chain_baseline·(1+slack)` (tree edges no worse than
  the validated chain); **(2) dropped-edge relative bound** `max_dropped_edge_relerr ≤ C·max_tree_edge,
  C∈[2,3]` (a bounded transitive residual at the cycle edge); **(3) conservative direction** cross-seam
  firstdifference variance ratio (blend/ref) `≥ 0.9` on tree edges and `≥ 1−ε` on dropped edges — never
  under-dispersed. Recorded as a conservative `known_bias`. *Bug it catches:* (1) a broken hand-forward
  on a shared edge; (2) a discontinuity instead of transitive agreement at a non-tree seam; (3) a
  residual that is small **but overconfident** — the Phase-3 disease wearing a small number.
- **Two-tree invariance (property test).** The shipped blend passes (1)–(3) under the MST AND one
  alternative valid spanning tree. *Bug:* correctness depends on which tree → topology-fragility has
  silently returned.
- **Nonstationary-κ (C4′).** Repeat (1)–(3) with a latitude-varying κ field — conservative, within tol.
  No special handling: κ rides on the per-tile posteriors.
- **Per-tile full-covariance oracle.** Corrected ensemble cov == exact `(Qⁱ)⁻¹`. *Bug:* the
  correction distorts the per-tile posterior.
- **Independent-white oracle (C2′).** Two pairwise independences: tile-white ⟂ tile-white (a child's
  unconditional draw is independent of the parent values it conditions toward). *Bug:* shared noise
  between a draw and its conditioning target re-biases the correction.
- **1-D chain regression.** The existing chain tests stay green; the tree sweep over a line IS the chain.

### 3.4 Escalation (spec §5.3 / §6 / §8)

If the gate shows a **recorded residual exceeds tolerance** (e.g. the Phase-5 tuner wanders to short
range and a dropped-edge residual breaks bound (2) or the conservative direction (3)), the spanning-tree
construction is *inadequate for that regime* → **stop and surface**; the **junction-tree** fallback
(§6) — exact on cycles, at the topology/treewidth cost — is built only then. Do not ship a silently
overconfident sampler; do not loosen the tolerance to pass.

### 3.4a Product-facing residual disclosure (load-bearing honesty)

The shipped global SSHA uncertainty carries a **bounded, recorded cross-seam coherence residual on
non-tree tile adjacencies** — coherence across a non-tree seam is **transitive (through a common
neighbour), not direct**. This is a permanent, measured property of the deliverable, not a fixture
artifact. A downstream consumer computing a derived quantity (e.g. transport) across a non-tree seam is
entitled to know the coherence there is transitive; the §5.3/§4 product sentence and provenance
`known_bias` must say so. Junction-tree is the documented exact escalation if that residual is ever
unacceptable for a use case.

### 3.5 Stage-B gate (definition of done)

`GmrfTreeKrigingSolve` replaces the lon-chain sweep with a max-overlap spanning-tree sweep; grid GMRF
tiles in 2-D, seam-free, conservative, tree edges ≤ the measured chain baseline and dropped edges
within `C·tree-edge`; the three coupled assertions + two-tree invariance + nonstationary all pass on
real solved tiles with the residual recorded; per-tile-full-cov and two-stream independent-white
oracles pass; the per-tree-edge separation + disconnected-tile negative controls fail loudly; the 1-D
chain case still passes.

---

## 4. Stage C — FEM (near-pure discretization swap + payoff)

### 4.1 `methods/fem_mesh.py` (new)

- `Mesh` value object: `points` (n_nodes, ≥2), `triangles` (n_tri, 3); PointSet-like `.points()` so
  the blend's `_nearest` / `_support_points` work unchanged; serves as a `Projection.node_space`.
- `build_mesh(points, boundary_ring=None, refine_points=None) -> Mesh` via `scipy.spatial.Delaunay`
  over an arbitrary input point set — an extended boundary ring drives boundary extension;
  locally-densified `refine_points` drive data-adaptive refinement (both demos are input-point-set
  driven; no refinement primitives needed).
- `assert_mesh_quality(mesh, min_angle)` — the **sliver guard**, the FEM analogue of
  `_assert_separates`: fails loudly on a degenerate triangulation so a meshing artifact never inflates
  G, never dents Q's conditioning, and never falsely reddens the swap test (spec §5.4 amendment).

### 4.2 `methods/fem.py` (new), registered `"fem"` in `methods/registry.py`

- `fem_precision(mesh, kappa, tau) -> sparse Q`: hand-rolled P1 **lumped-mass** `C` (diagonal,
  area/3 per node) + **stiffness** `G` (P1 gradients); α=2 → `Q = (1/τ)(κ²C + G) C⁻¹ (κ²C + G)`.
  κ scalar **or** per-node field (nonstationary → per-node `κ²C`). Calls `assert_mesh_quality`.
- `FEMBasisProjection(mesh)`: `weights(pts)` = P1 basis `ψ_i(s_k)` via `Delaunay.find_simplex` +
  barycentric coordinates → sparse `(k, n_nodes)` (the mesh analogue of `bilinear_weights`); `A`
  (node→obs) = this at obs points; `field_shape() = (n_nodes,)`; `node_points = mesh.points`;
  `assert_adjacency` → mesh-edge-in-pattern + sliver guard.
- `FEMMatern.solve`: build the global/shared-node boundary-extended (optionally data-adaptive) mesh;
  `Q_prior = fem_precision`; `A = FEMBasisProjection.weights(obs.coords())`;
  `Q_post = Q_prior + AᵀR⁻¹A` with the **same** temporal-taper-into-R as `MaternGMRF`; wrap in the
  **same** `GMRFCovarianceOperator` holding the FEM projection. SAMPLES + COVARIANCE; provenance
  carries the sparse-precision tag and any recorded coherence residual. Mean stored flat
  (`field_shape (n_nodes,)`).

### 4.3 Global/shared-node mesh ⇒ the sampler is inherited (invariant 9)

One triangulation; tiles are node subsets sharing overlap nodes ⇒ coincident-node conditioning works
and `GmrfJointKrigingSolve` is inherited unchanged. The strip-prior over mesh strips is
`fem_precision` restricted to the strip node set honoring the induced mesh connectivity (the C1
contract carries over to the mesh). C6 (shared nodes actually match) is especially load-bearing here
and is asserted.

### 4.4 Stage-C tests

- **Genuine-discretization-swap (C5)** — the test that proves the phase. During a FEM solve + reduce
  + blend, a guard makes `bilinear_weights` and any `(ny,nx)` reshape **raise if called**; the FEM
  path holds a `FEMBasisProjection` with `field_shape (n_nodes,)`; assert FEM flows through the same
  `GMRFCovarianceOperator`, `GMRFPrecisionReduction`, `GmrfJointKrigingSolve`, and `BlendOperator`,
  with only `fem_precision` + `FEMBasisProjection` differing. *Bug it catches:* anyone routing FEM
  through a grid shortcut.
- **Exact FEM marginal variance** — Takahashi `diag(Q⁻¹)` vs dense `Q⁻¹` on a small mesh, tight
  rtol. *Bug:* assembly or selective-inverse error on an unstructured pattern.
- **Sliver guard** — a degenerate triangulation raises (loud red). *Bug:* a meshing artifact
  masquerading as a method failure.
- **Payoff demo (C7)** — a boundary-extended (and/or data-adaptive) mesh removes the edge variance
  inflation the regular grid shows: assert `edge_var(FEM) < edge_var(grid)` by margin **at
  near-boundary nodes** (boundary-extension effect, not interior-averaged). Figure via the
  `plotting-colormaps` skill (cmocean, perceptually uniform). *Bug:* the boundary extension not
  actually reducing edge inflation.
- **Blend + eval** — FEM-GMRF blends globally (homogeneous) through the inherited driver: seam-free,
  conservative, provenance carries the sparse-precision tag + recorded residual; OSSE + OSE accuracy
  and calibration fire (real ODC NATL60 OSSE + withheld CryoSat-2 OSE, scoped footprint, opt-in
  global).

### 4.5 Dependency

None added. scipy.spatial.Delaunay is core. Shewchuk-quality meshing (`triangle`/`meshpy`) is the
clean upgrade behind the same `fem_precision` / `FEMBasisProjection` seam if a production
irregular-domain capability is ever needed (spec §6) — out of Phase-4 scope.

---

## 5. Out of scope (spec §6) — stop and ask if any appears necessary

Per-tile independent meshes; the junction-tree sampler (fallback only, built solely on an
out-of-tolerance Stage-B residual); production-quality meshing; full coastline/irregular-domain
production; the autotune loop / any optimizer (Phase 5); methods beyond OI + grid-GMRF + FEM-GMRF
(+ trivial degradation); continuous/tunable ν (fixed α=2); cloud/multi-node; SWOT/2-D swath;
recalibration; full-correction double-counting.

---

## 6. Sequencing, determinism, engineering standards

- **Gates:** A green (Phase-3 suite exact) → B (positive control passes, residual in tolerance) → C.
  Small reviewable commits, test-first, Phase-3 suite green through all of A.
- **Determinism (invariant 11):** independent per-tile white, the joint-strip white, the permutation,
  and any new randomness are deterministic (tile-/lattice-keyed seeds via `derive_seed`),
  order-independent, recorded.
- **Sparse-linear-algebra discipline:** one sparse Cholesky per operator serves sampling, marginal
  variance, and cov; persist Q + permutation, cache the factor; dense `Q⁻¹` only in small reference
  tests.
- **TDD + test-design:** every test states the behavior under test and a concrete bug that would make
  it fail; tests measure the *contracted* property (joint structure where the contract is joint
  structure), never an incidental one. New logic gets unit tests even where the spec is terse.
- **BLAS/OpenMP + Executor:** unchanged (per-run processes × threads; `LocalCluster`, address-only).

---

## 7. Files touched / created (summary)

| Stage | Created | Modified |
|---|---|---|
| A | `core/projection.py` | `methods/gmrf_grid.py` (dataclasses → protocol), `methods/gmrf.py` (operator holds projection), `distributions/persisted.py` (de-grid), `distributions/reduction.py` (projection call-site), `application/solve.py` (thread projection) |
| B | — | `distributions/coherent.py` (`GmrfJointKrigingSolve`, repoint `_DRIVERS`) |
| C | `methods/fem_mesh.py`, `methods/fem.py` | `methods/registry.py` (register `"fem"`) |

New tests: Stage A — projection conformance, C3 fast-path equivalence. Stage B — distinct-tiles
positive control (cross-seam + C1 corner-junction + C4 nonstationary), per-tile full-cov oracle, C2
three-stream independent-white oracle, negative control, C6 shared-node assertion. Stage C — C5
genuine-swap guard, exact FEM marginal var, sliver guard, C7 boundary payoff, FEM blend OSSE/OSE.
