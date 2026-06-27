# Phase 4 — FEM/triangulation SPDE + non-chain coherent sampler

**Design doc.** Source of truth = `phase4_scope_spec.md` (settled + owner-amended, HEAD `00519b1`).
On any conflict the spec governs; this doc is the *implementation architecture* derived from it.

**Builds on:** `sverdrup` Phase-3 HEAD `31a58c6` (suite 178 passed / 2 skipped). Refactor, don't rewrite.

**Governing discipline:** Generalize under the green Phase-3 suite *before* extending. Separate the two
hard problems (2-D tile topology vs unstructured mesh). Three stages, three gates: A green → B;
B positive-control passes → C.

---

## 0. The five owner-pinned correctness contracts (read first)

Phase-after-phase the failures have been *a correctness assumption riding inside a step that looks
like plumbing*. These five are pinned here so each is a **test**, not a discovery. They are
referenced inline at the stage they bind; collected here so none is lost.

- **C1 — the strip-network is a graph; its prior is assembled on the induced subgraph of Q.**
  Overlap strips intersect (a corner where ≥3 tiles meet shares nodes across multiple strips; two
  crossing strips share their crossing nodes). `_draw_joint` must assemble `(κ²I−Δ)²` over the strip
  node set honoring **every Q edge with both endpoints in the strip set** (corner nodes included) —
  NOT as a union of independent ribbons. Dropping inter-strip edges makes the auxiliary field
  discontinuous exactly at the junctions, where 2-D coherence is hardest and where the chain sweep
  died. **Test (Stage B positive control):** joint covariance **across a strip junction** (an
  interior corner, ≥3 tiles) vs a dense reference — a 2×2 partition has exactly one interior corner
  and is the minimal fixture. A right-marginal-variance check does NOT catch this; the corner-junction
  joint-covariance check does.

- **C2 — three white-noise streams, three pairwise-independence checks.** Phase 3 had two streams
  (tile draw ⟂ handed-forward target). The joint construction adds a third: the auxiliary field's
  white. The kriging correction is unbiased only if each tile's unconditional white is independent of
  the joint field's white (shared noise between a draw and the target it is conditioned toward
  re-biases the correction — invariant 4 / the Phase-3 lesson). **Test (independent-white oracle):**
  assert all three pairwise independences — tile-white ⟂ tile-white, tile-white ⟂ joint-white,
  (and the joint draw is a single shared field across tiles). The pairing not tested is the one that
  regresses.

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

### 3.1 `GmrfJointKrigingSolve` — `distributions/coherent.py`

Repoint `_DRIVERS["sparse-precision"]` to the new driver. Reuse `posterior_cov_columns`,
`_node_keys`, `_nearest`, the weight-crossfade. Drop tile ordering, hand-forward, and the lon-column
`_assert_separates`. Steps:

1. **`_strip_network(parts)` → (strip nodes, induced Q-subgraph).** Strip nodes = nodes of tile *i*
   falling in any other tile's `extended_window`, matched across tiles by `_node_keys`. Returns the
   strip node set **and the induced subgraph of Q** over them — every Q edge with both endpoints in
   the set, corner/junction nodes included (**C1**). Topology-agnostic: no chain/tree assumption.
   Asserts the cross-tile shared strip node set is non-empty for adjacent tiles (**C6**).

2. **`_draw_joint(strip_nodes, induced_graph, provider, seed)` → x_joint.** Assemble the **prior**
   SPDE sub-precision `(κ²I−Δ)²` over the strip node set honoring the full induced connectivity
   (**C1**), with κ (and τ) evaluated **per strip node via the provider** — the same field the tiles
   use, including nonstationary (**C4**). Draw `x_joint = mean + L_strip⁻ᵀ w_joint` with its **own
   independent** white (**C2**). This is spec-literal "global prior restricted to strips" (a thin
   sub-GMRF). Boundary truncation + the prior↔posterior strip mismatch **is** the residual, measured
   and recorded (invariant 7).

3. **Per tile.** Independent per-tile white (`gmrf-tile:pos × member`, unchanged) → `x_u = mean +
   L⁻ᵀ w`; krige toward this tile's strip values read from the **one** joint field:
   `x_c = x_u + cols @ solve(Σ_ss, x_joint|_S − x_u|_S)`, `cols = posterior_cov_columns(s_idx)`.

4. **Weight-crossfade** onto output pts (unchanged).

The only change from `GmrfKrigingSolve`: conditioning targets come from one pre-drawn joint field over
*all* strips (assembled on the strip graph) rather than handed forward along a chain. No
tree/separator requirement.

### 3.2 Negative control (replaces the lon-column separator check)

Too-narrow overlap → the strip cannot separate interiors → the measured residual blows up / the
partition-of-unity crossfade has no room and seam variance collapses → **loud red**,
topology-agnostic. Mirrors `_assert_separates` without assuming a sweep direction.

### 3.3 Validation on 2-D grid (topology isolated from mesh)

Minimal fixture: a **2×2 partition of one global grid** (exactly one interior corner — the minimal
strip-junction exerciser), genuinely-distinct tiles (distinct obs ⇒ distinct posteriors; never a
fixture where tiles collapse to identical Q — invariant 6). Tests (each states behavior + the bug it
catches, per test-design):

- **Positive control (the standing gate).** (a) cross-seam (two-tile edge) `firstdifference`
  variance parity blend-vs-single-tile reference, min ratio ≥ tol, conservative direction; (b)
  **corner-junction joint covariance vs a dense reference** (**C1**) — the load-bearing case;
  (c) the **nonstationary-κ** case (**C4**). The control **measures the residual against the
  single-tile reference and records it** (conservative `known_bias`); it is not pass/fail in
  isolation. *Bug it catches:* dropped inter-strip Q edges (discontinuous joint at the corner);
  scalar-κ joint draw in the nonstationary case.
- **Per-tile full-covariance oracle.** Corrected ensemble cov == exact `(Qⁱ)⁻¹`. *Bug:* the
  correction distorts the per-tile posterior.
- **Independent-white oracle (C2).** Three pairwise independences: tile-white ⟂ tile-white,
  tile-white ⟂ joint-white, and the joint field is a single shared draw across tiles. *Bug:* shared
  noise between a tile draw and the joint target re-biases the correction (spurious long-range corr).
- **1-D chain regression.** The existing chain tests stay green under the joint driver (it subsumes
  the chain: full strip separation ⇒ residual → 0).

### 3.4 Escalation (spec §5.3 / §8)

If the positive control shows the **recorded residual exceeds tolerance**, the construction is
*inadequate* (not merely approximate) → **stop and surface**; the junction-tree fallback is built
only then. Do not ship a silently-wrong sampler; do not loosen the tolerance to pass.

### 3.5 Stage-B gate (definition of done)

`GmrfJointKrigingSolve` replaces the lon-chain sweep; grid GMRF tiles in 2-D, seam-free, no
mid-overlap variance dip, matches the single-tile reference within tol, conservative; per-tile-full-cov
and three-stream independent-white oracles pass; the distinct-tiles positive control (cross-seam +
corner-junction + nonstationary) passes with recorded residual; the too-narrow-overlap negative
control fails loudly; the 1-D chain case still passes.

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
