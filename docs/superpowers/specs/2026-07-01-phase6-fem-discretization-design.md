# Phase 6 — FEM/triangulation SPDE: a grid-agnosticism falsification via maximally-irregular discretization

**Design doc.** Supersedes Phase-4 Stage C (the FEM tasks T10–16 in
`docs/superpowers/plans/2026-06-26-phase4-fem-and-nonchain-sampler.md`, which are stale: they name the
dead `GmrfJointKrigingSolve` and predate the capability-scoped feasibility framework). New milestone name
kills the Phase-4-StageC / Phase-5-StageC collision.

**Builds on shipped state:** the Phase-3/4 `Projection` seam (`core/projection.py`), the CHOLMOD factor +
Takahashi selective inverse (`methods/gmrf_linalg.py`), `GMRFPrecisionReduction` (`distributions/reduction.py`),
the live `GmrfTreeKrigingSolve` `sparse-precision` driver (`distributions/coherent.py`), and the
discretization-agnostic `CoherenceFeasibility` predicate (`application/tuning/feasibility.py`).

---

## 0. PRIMARY GOAL — what Phase 6 is *for*

Phase 6 exists to **falsify the claim that sverdrup secretly depends on a regular-grid feature.** The proof
strategy: run the full pipeline on a **maximally-irregular finite-element mesh** and check every inherited
quantity against **linear-algebra ground truth** (a dense `Q⁻¹`). If the pipeline is truly grid-agnostic,
the irregular mesh produces exact results through the same reduction / sampler / blend code the grid uses,
with only the discretization (assembly + basis read-off) swapped.

**The FEM method is the VEHICLE for that proof, not the point.** C7 (boundary-extension mechanism) and
multi-tile inheritance are secondary completeness — kept, but not the headline.

### 0.1 The headline experiment — the claim, and where it is produced-and-locked

The blocker ("does the inherited machinery secretly assume a grid?") and the agnosticism proof are the
**same experiment.** The load-bearing inherited component is `GMRFPrecisionReduction`, which persists exact
marginal variance via `op.marginal_var → GMRFFactor.selective_inverse_diag → _takahashi(L)`. That reduction
was built and tested on **grid** precision (5-point lattice). FEM P1 stiffness has irregular vertex adjacency,
variable valence, and no lattice — so the selective inverse is exact **only if** fill-in / elimination tree is
computed from the *actual* precision graph, not a lattice assumption.

**The CLAIM rests on three inspection-verifiable code facts** (why the reduction is pattern-agnostic — no
running required to check these):
1. `gmrf_linalg.py:27` — `GMRFFactor` factors `Q[P][:,P]` in **AMD order**; the permutation `P` comes from the
   *actual matrix graph*, with no lattice assumption.
2. `gmrf_linalg.py:96-101` — `_takahashi` / `selective_inverse_diag` is the Erisman–Tinney selective inverse,
   **exact on the factor's fill pattern for any SPD `Q`** (the Takahashi diagonal is always in-pattern).
3. `gmrf_linalg.py:135` — `assert_adjacency_in_pattern(q, shape=(ny,nx))` is the **sole** grid-shaped symbol,
   and it is a **precondition GUARD, not a numerical step**. The FEM path does not call it; it substitutes a
   **mesh-edge-in-pattern** guard (§2.2). A swap of a known guard, not a latent dependency in the numerics.

So reduction-path agnosticism is defensible **mechanistically, by reading the code** — that is the basis for
§1 treating "reduction inherited unchanged" as sound, and for multi-tile (§4.3) / C7 (§4.2) inheriting it.

**Where the NUMBER is produced-and-locked: the shipped §3 #1 test** (`exact-marginal-var on the adversarial
mesh vs dense Q⁻¹`), committed and CI-run. That test *is* this measurement; it is the authoritative,
reproducible evidence — not a one-off script. **Both outcomes are a successful Phase 6:** PASS substantiates
the reduction path; a FAIL *finds* a hidden grid dependency and the fix (pattern-agnostic reduction in
`reduction.py` / `gmrf_linalg.py`) becomes a Phase-6 component. The mechanistic argument predicts PASS.

**Preview figures (reproducible, not the authority).** A committed reproducer,
`scripts/probe_fem_reduction_exactness.py` (the `diag_crossseam.py` precedent), prototypes §3 #1 on an
adversarial Delaunay mesh (valence [3, 9] vs grid's ~4; a 0.38° sliver; 31%-dense irregular `Q_post`) and
reports `diag(Q⁻¹)` max rel err **4.4e-10** (rtol 1e-9) and **40/40** mesh-edge cov entries exact. These are a
*preview* of what §3 #1 locks in CI — cited for concreteness, not as standalone "measured fact."

**Reinforcement — one sub-claim genuinely needs the §3 #1 measurement, not just the mechanistic argument.**
"Every mesh edge lands in the selective-inverse pattern (0 absent)" is **not** implied by Takahashi-exactness:
Takahashi gives `Σ_ij` only for `(i,j)` already **in** the factor fill pattern. So this asserts an
**assembly-pattern property** of `fem_precision` — the α=2 form `(κ²C+G)C⁻¹(κ²C+G)` carries the 2-hop
neighbourhood, so every 1-hop mesh edge is in `Q`'s pattern → in `L`'s fill. That can fail under degenerate
configs and is not fully nailed by inspection → §3 #1 asserts it explicitly on the adversarial fixture, where
it is locked and reproducible.

### 0.2 Honest-scope caveat (state next to every agnosticism result)

Passing establishes **"no hidden grid dependency ON THE PATHS THE ADVERSARIAL FIXTURE EXERCISES."** It is
strong *falsifying evidence*, not a universal proof: a dependency in an unexercised path stays invisible.
Strength is proportional to how adversarial the fixture is and how much of the `solve → reduce → blend →
project` path it covers — which is exactly why the agnosticism tier (§3) is the whole game, and why the
grid-shortcut audit (§3, #2) is expanded to the *entire* path rather than the obvious reshape spots. Do **not**
claim unconditional grid-agnosticism anywhere in code, docstrings, or provenance.

---

## 1. Architecture — near-pure discretization swap (reduction path: mechanistic claim, §3 #1 locks the number)

FEM adds exactly two mesh-carrying units — the precision **assembly** (`fem_precision`) and the basis
**read-off** (`FEMBasisProjection`). Everything downstream is inherited **unchanged**; the reduction path's
pattern-agnosticism is defensible by inspection (§0.1's three code facts) and its exactness is
produced-and-locked by the shipped §3 #1 test: `GMRFCovarianceOperator`, `GMRFFactor` (CHOLMOD + Takahashi),
`GMRFPrecisionReduction`, `GmrfTreeKrigingSolve`, `BlendOperator`. The `Projection` seam (shipped) is the
polymorphism point: grid holds `GridIdentityProjection`, FEM holds `FEMBasisProjection`, both satisfy
`core/projection.py::Projection`.

The single grid-shaped precondition (`assert_adjacency_in_pattern`) is dispatched *through* the projection
(`Projection.assert_adjacency`), so the read-off precondition travels with the node space — grid → 5-point
lattice check; mesh → mesh-edge-in-pattern + sliver guard.

---

## 2. Components (3 units; stationary κ only for Phase 6)

### 2.1 `methods/fem_mesh.py` (new)
- `Mesh` value object: `points (n_nodes, 2)`, `triangles (n_tri, 3)`; PointSet-like `.points(time_days)` so
  the blend's `_nearest` / `_support_points` work unchanged; serves as a `Projection.node_space`.
- `build_mesh(points, boundary_ring=None, refine_points=None) -> Mesh` via `scipy.spatial.Delaunay` over an
  arbitrary point set — an extended boundary ring drives boundary extension; densified `refine_points` drive
  data-adaptive refinement. Both demos are input-point-set driven; no refinement primitives.
- `assert_mesh_quality(mesh, min_angle)` — the **sliver guard**, FEM analogue of `_assert_separates`: raises
  loudly on a degenerate triangulation so a meshing artifact never inflates G, dents Q's conditioning, or
  falsely reddens the agnosticism test. Dep: scipy Delaunay (already core).

### 2.2 `methods/fem.py` (new), registered `"fem"` in `methods/registry.py`
- `fem_precision(mesh, kappa, tau) -> sparse Q`: hand-rolled P1 **lumped-mass** `C` (diagonal, area/3 per node)
  + **stiffness** `G` (P1 gradients); α=2 → `Q = (1/τ)(κ²C + G) C⁻¹ (κ²C + G)`. **Stationary scalar κ** for
  Phase 6 (per-node κ deferred, §5). Calls `assert_mesh_quality`. (Prototyped in the §0.1 probe.)
- `FEMBasisProjection(mesh)`: `weights(pts)` = P1 basis `ψ_i(s_k)` via `Delaunay.find_simplex` + barycentric →
  sparse `(k, n_nodes)`; `A` = this at obs points; `field_shape() = (n_nodes,)`;
  `node_points = mesh.points`; `assert_adjacency` → **mesh-edge-in-pattern + sliver guard** (NOT the grid
  5-point check).
- `FEMMatern.solve`: build the global/shared-node (optionally boundary-extended / data-adaptive) mesh;
  `Q_prior = fem_precision`; `A = FEMBasisProjection.weights(obs.coords())`; `Q_post = Q_prior + AᵀR⁻¹A` with
  the **same** temporal-taper-into-R as `MaternGMRF`; wrap in the **same** `GMRFCovarianceOperator` holding the
  FEM projection. SAMPLES + COVARIANCE; mean stored flat `(n_nodes,)`.

### 2.3 `methods/registry.py`
Register `"fem": FEMMatern` alongside `"oi"`, `"gmrf"`.

---

## 3. Agnosticism tier — the PRIMARY deliverable

Two tests carry the goal. Both run **FIRST**, before the secondary sections, because multi-tile and C7 inherit
whatever they establish.

**#1 — Exact marginal variance on a MAXIMALLY ADVERSARIAL mesh.** `diag(Q_post⁻¹)` via the inherited
`GMRFPrecisionReduction` (→ `selective_inverse_diag`) vs a **dense** `Q_post⁻¹`, tight rtol (1e-9). The shipped
test hardens the §0.1 probe into a fixture with **explicitly required adversarial properties**:
- irregular / variable vertex valence (not grid-constant);
- non-uniform node spacing (clustered + sparse regions);
- slivers near the guard threshold (stress the conditioning + the pattern);
- a jagged / irregular boundary;
- small enough that a dense `Q⁻¹` ground truth is computable.

The adversarial-ness **is** the value — a favorable/regular-ish mesh proves little. *Bug it catches:* any latent
lattice assumption in assembly, factorization, or the selective inverse → plausible-but-wrong marginal variance.

This test **also explicitly owns the edge-in-pattern sub-claim** (per §0.1 reinforcement): it asserts every
mesh edge's `Σ_ij` is present in the selective-inverse pattern (0 absent) and exact vs dense — an
**assembly-pattern property** of the α=2 `fem_precision` that Takahashi-exactness alone does not guarantee and
that can fail under degenerate configs. Locked here on the adversarial fixture, reproducibly.

**#2 — Grid-shortcut audit over the WHOLE `solve → reduce → blend → project` path.** During a full FEM solve +
reduce + blend + eval-point projection, a guard makes **any** call to `bilinear_weights`, **any** `(ny, nx)`
reshape, and **any** lattice-index assumption **raise loudly** if hit on the FEM path; FEM holds `field_shape
(n_nodes,)`. This is the literal mechanization of "prove it doesn't secretly use the grid": fail loud if the FEM
path routes through *any* grid-shaped code, not just the obvious reshape spots. *Bug it catches:* a grid
shortcut anywhere on the path — the exact failure mode Phase 6 exists to falsify.

**Both tests carry the §0.2 honest-scope caveat in-line** (docstring + any recorded provenance): they establish
no-hidden-grid-dependency *on the exercised paths*, proportional to fixture adversarial-ness — not a universal
proof.

---

## 4. Secondary completeness (kept; not agnosticism tests)

### 4.1 Sliver guard + C6 shared-node
- **Sliver guard** — a degenerate triangulation raises (loud red). *Bug:* meshing artifact masquerading as a
  method failure.
- **C6 shared-node match** — on the global shared-node mesh, the adjacent-tile shared strip-node set is
  non-empty (Delaunay vertices coincide exactly). *Bug:* silent-empty cross-tile conditioning.

### 4.2 C7 boundary-extension MECHANISM demo (honest baseline)
On a synthetic fixture with an irregular / extended boundary ring, assert `edge_var(FEM) < edge_var(grid)` **at
near-boundary nodes** (not interior-averaged). This **demonstrates the boundary-extension mechanism on a
controlled fixture against a DEFENSIBLE grid baseline** — it is a mechanism demo, NOT a "FEM is better on real
coasts" value claim (real-coastal payoff needs real data; deferred, §5). Under the agnosticism goal the demo
must **not be rigged to make FEM win**.

The honest baseline, stated: the shipped grid-GMRF uses a **5-point finite-difference Laplacian with Neumann
(zero-flux) edges** (`_laplacian`, `gmrf_grid.py:48` — the `0 <= jj < ny` bounds check is the Neumann edge),
which inflates variance at domain-edge nodes because edge nodes lack
outward neighbour support. FEM's boundary ring supplies that support. The demo measures that specific mechanism
against that specific, named baseline. Figure via the `plotting-colormaps` skill (cmocean, perceptually
uniform). *Bug:* the boundary extension not actually reducing edge inflation vs the real shipped baseline.

### 4.3 Multi-tile FEM inheritance (lowest-information section — kept for completeness)
One global shared-node mesh; tiles are node subsets sharing overlap nodes → inherits the **live
`GmrfTreeKrigingSolve`** (max-overlap spanning-tree hand-forward — NOT the dead `GmrfJointKrigingSolve` the
Phase-4 design named). FEM inherits the **discretization-agnostic `CoherenceFeasibility` envelope verbatim**:
MARGINAL_VARIANCE global ships; SAMPLES/COVARIANCE only within `n_star_joint`. Demonstrated at
`n_tiles ≤ n_star_joint`.

**Why lowest-information:** the coherence envelope is already proven discretization-agnostic *at the predicate
level* (`CoherenceFeasibility` keys on `n_tiles` + capability, with zero grid/mesh dependence). This section
re-confirms an already-established fact; it is completeness, not an agnosticism test. *Bug it catches:* the FEM
swap breaking the inherited driver's cross-tile hand-forward (a mesh-node-index mismatch), caught at small
feasible tile counts.

---

## 5. Deferred / out of scope (stated, not silent)
- **Nonstationary / per-node κ.** Orthogonal to grid-agnosticism: per-node κ scales precision *entries*, it does
  **not** change the sparsity *pattern*, so it adds zero pattern-coverage to the agnosticism proof; and it has
  no consumer. The assembly seam (`fem_precision`) supports it later as a small add behind the same seam. In
  scope only if the owner explicitly wants it despite the above.
- **Real OSSE / OSE eval.** ODC THREDDS is dead; no live coastal/irregular-domain data. The C7 payoff is a
  synthetic mechanism demo; real-data validation is deferred.
- **Production-quality meshing** (`triangle` / `meshpy`) — the clean upgrade behind the same
  `fem_precision` / `FEMBasisProjection` seam if an irregular-domain production capability is ever needed.
- **The coarse-correction that widens `n_star_joint`** — owner-deferred, horizontal (constrains grid and FEM
  identically), out of Phase 6.

---

## 6. Files, tests, sequencing

| Created | Modified |
|---|---|
| `methods/fem_mesh.py`, `methods/fem.py` | `methods/registry.py` (register `"fem"`) |

New tests (each states behavior + the concrete bug it catches, per `test-design`):
- **Agnosticism tier (PRIMARY, run first):** #1 exact-marginal-var on the adversarial mesh vs dense `Q⁻¹`;
  #2 whole-path grid-shortcut audit (bilinear/reshape/lattice-index raise-if-hit).
- **Secondary:** sliver guard; C6 shared-node; C7 boundary-extension mechanism demo vs the named Neumann-edge
  grid baseline; multi-tile FEM blend through `GmrfTreeKrigingSolve` at `n_tiles ≤ n_star_joint`.

**Sequencing:** agnosticism tier (§3) FIRST — it clears the inheritance the rest depends on (the §0.1 probe
already confirmed the reduction path; the shipped hardened tests lock it). Then secondary completeness. Small
reviewable commits, test-first, existing suite green throughout.

**Determinism:** mesh construction, per-tile white, and any new randomness are deterministic (fixed seeds via
`derive_seed`), order-independent, recorded.

---

## 7. Honest-scope statement (formal)

Phase 6 produces **strong falsifying evidence** that sverdrup has no hidden regular-grid dependency, by running
the full pipeline on a maximally-irregular mesh checked against dense linear-algebra ground truth. It does **not**
produce an unconditional proof of grid-agnosticism: dependencies in paths the adversarial fixture does not
exercise remain invisible. Every result is reported with this scope attached. The reduction-path claim is
mechanistically sound by inspection (§0.1's three code facts); the shipped §3 #1 test produces-and-locks the
number in CI (the committed `scripts/probe_fem_reduction_exactness.py` previews a pass); the agnosticism tier
hardens and path-extends that evidence across the whole solve→reduce→blend→project path.
