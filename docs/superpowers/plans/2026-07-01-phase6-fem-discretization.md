# Phase 6 — FEM/triangulation SPDE (grid-agnosticism falsification) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a finite-element (P1 triangulation) SPDE method as the vehicle to *falsify* any hidden regular-grid dependency in sverdrup — running the full pipeline on a maximally-irregular mesh and checking every inherited quantity against dense linear-algebra ground truth.

**Architecture:** FEM is a near-pure discretization swap onto the shipped GMRF machinery. Two new mesh-carrying units — `fem_precision` (P1 lumped-mass + stiffness assembly) and `FEMBasisProjection` (P1 basis read-off, a `core/projection.py::Projection`) — feed the *unchanged* `GMRFCovarianceOperator`, `GMRFFactor` (CHOLMOD + Takahashi selective inverse), `GMRFPrecisionReduction`, `GmrfTreeKrigingSolve`, and `BlendOperator`. The one grid-shaped guard (`assert_adjacency_in_pattern`) is swapped for a mesh-edge-in-pattern guard, dispatched through the projection. The agnosticism tier (exact marginal variance on an adversarial mesh + a whole-path grid-shortcut audit) is the primary deliverable; C7 boundary demo and multi-tile inheritance are secondary completeness.

**Tech Stack:** Python, numpy, scipy (`spatial.Delaunay`, `sparse` — already core), sksparse/CHOLMOD (inherited), pytest.

**User decisions (already made):**
- "Full resurrection" — build the whole FEM method (mesh + assembly + projection + solve + register + multi-tile inheritance), not a thin demo.
- "Synthetic mesh + boundary-ring demo" — C7 payoff is validated on a synthetic irregular-boundary fixture against the shipped grid baseline; real OSSE/OSE eval is deferred (ODC THREDDS dead).
- Agnosticism is the GOAL; FEM is the vehicle. The reduction-path claim rests on the mechanistic argument (spec §0.1); the *number* is produced-and-locked by the §3 #1 shipped test.
- Stationary scalar κ only for Phase 6; per-node/nonstationary κ deferred (orthogonal to agnosticism — scales entries, not the sparsity pattern).
- "measured fact must be in version control" — the committed reproducer `scripts/probe_fem_reduction_exactness.py` previews §3 #1; the CI test is the authority.

**Source of truth:** `docs/superpowers/specs/2026-07-01-phase6-fem-discretization-design.md`.

---

## Task 1: `fem_mesh.py` — Mesh value object + Delaunay builder + sliver guard

**Goal:** A `Mesh` value object (PointSet-like `.points()`), a `build_mesh` Delaunay constructor, and `assert_mesh_quality` (the sliver guard, FEM analogue of `_assert_separates`).

**Files:**
- Create: `src/sverdrup/methods/fem_mesh.py`
- Test: `tests/test_fem_mesh.py`

**Acceptance Criteria:**
- [ ] `build_mesh(points)` triangulates a 2-D point set and returns a `Mesh` with `points_xy (n,2)`, `triangles (n_tri,3)`, and `.points()` returning `(n,3)` `(lon,lat,time)`.
- [ ] `build_mesh(points, boundary_ring=ring)` includes the ring nodes (mesh has `n + len(ring)` nodes).
- [ ] `assert_mesh_quality` raises `AssertionError` on a sliver triangle (min angle below threshold) and passes on a well-shaped mesh.

**Verify:** `pixi run test tests/test_fem_mesh.py -v && pixi run typecheck` → pass / clean.

**Steps:**

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fem_mesh.py
"""Mesh construction, boundary-ring inclusion, and the sliver quality guard."""

from __future__ import annotations

import numpy as np
import pytest

from sverdrup.methods.fem_mesh import Mesh, assert_mesh_quality, build_mesh


def _square_points() -> np.ndarray:
    # a 4x4 lattice of points -> a well-conditioned triangulation
    xs, ys = np.meshgrid(np.linspace(0.0, 3.0, 4), np.linspace(0.0, 3.0, 4))
    return np.column_stack([xs.ravel(), ys.ravel()])


def test_build_mesh_produces_pointset_like_mesh() -> None:
    # Behavior: build_mesh triangulates and exposes (n,3) points() for the blend's _support_points.
    # Bug it catches: a Mesh that does not carry the (lon,lat,time) contract the blend consumes.
    mesh = build_mesh(_square_points(), time_days=2.0)
    assert isinstance(mesh, Mesh)
    assert mesh.points_xy.shape == (16, 2)
    assert mesh.triangles.shape[1] == 3 and mesh.triangles.shape[0] > 0
    p = mesh.points()
    assert p.shape == (16, 3)
    assert np.allclose(p[:, 2], 2.0)  # time column carried


def test_boundary_ring_adds_nodes() -> None:
    # Behavior: an extended boundary ring drives boundary extension by adding ring nodes.
    # Bug it catches: build_mesh silently dropping the ring so no boundary extension happens.
    ring = np.array([[-1.0, -1.0], [4.0, -1.0], [4.0, 4.0], [-1.0, 4.0]])
    mesh = build_mesh(_square_points(), boundary_ring=ring)
    assert mesh.points_xy.shape[0] == 16 + 4


def test_sliver_guard_raises_on_degenerate_triangle() -> None:
    # Behavior: assert_mesh_quality is a loud red on a near-collinear (sliver) triangle.
    # Bug it catches: a meshing artifact inflating G / denting Q conditioning passing silently.
    slivers = np.array([[0.0, 0.0], [1.0, 0.0], [2.0, 1e-4], [0.5, 1.0]])
    mesh = build_mesh(slivers)
    with pytest.raises(AssertionError, match="sliver|degenerate"):
        assert_mesh_quality(mesh, min_angle=5.0)


def test_sliver_guard_passes_on_good_mesh() -> None:
    # Behavior: a well-shaped mesh clears the guard.
    # Bug it catches: an over-strict guard that reddens valid triangulations.
    assert_mesh_quality(build_mesh(_square_points()), min_angle=5.0)  # no raise
```

- [ ] **Step 2: Run — confirm fail**

Run: `pixi run test tests/test_fem_mesh.py -v`
Expected: FAIL — `ModuleNotFoundError: sverdrup.methods.fem_mesh`.

- [ ] **Step 3: Implement `fem_mesh.py`**

```python
# src/sverdrup/methods/fem_mesh.py
"""FEM triangulation: Mesh value object + Delaunay builder + sliver quality guard (Phase 6).

The Mesh is the FEM ``Projection.node_space``. It is PointSet-like — ``.points()`` returns
``(n_nodes, 3)`` ``(lon, lat, time)`` so the blend's ``_support_points`` / ``_nearest`` work
unchanged. ``assert_mesh_quality`` is the sliver guard, the FEM analogue of ``_assert_separates``:
a loud red on a degenerate triangulation so a meshing artifact never masquerades as a method failure.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.spatial import Delaunay  # type: ignore[import-untyped]

from sverdrup.core.types import Points


@dataclass(frozen=True)
class Mesh:
    """A 2-D P1 triangulation: node coordinates + triangle vertex indices.

    Attributes:
        points_xy: ``(n_nodes, 2)`` node coordinates ``(lon, lat)``.
        triangles: ``(n_tri, 3)`` integer vertex indices into ``points_xy``.
        time_days: The output time carried in the ``(n,3)`` ``points()`` third column.
    """

    points_xy: np.ndarray
    triangles: np.ndarray
    time_days: float = 0.0

    def points(self) -> Points:
        """Return ``(n_nodes, 3)`` ``(lon, lat, time)`` — the PointSet contract the blend consumes."""
        n = self.points_xy.shape[0]
        return np.column_stack([self.points_xy, np.full(n, self.time_days)]).astype(float)

    @property
    def n_nodes(self) -> int:
        """Return the number of mesh nodes."""
        return int(self.points_xy.shape[0])


def build_mesh(
    points: np.ndarray,
    boundary_ring: np.ndarray | None = None,
    refine_points: np.ndarray | None = None,
    time_days: float = 0.0,
) -> Mesh:
    """Delaunay-triangulate an arbitrary 2-D point set (+ optional boundary ring / refinement).

    Args:
        points: ``(n, >=2)`` input node coordinates (only the first 2 columns are used).
        boundary_ring: Optional ``(m, >=2)`` extended-boundary nodes that drive boundary extension.
        refine_points: Optional ``(r, >=2)`` locally-densified nodes for data-adaptive refinement.
        time_days: Output time carried by the resulting ``Mesh``.

    Returns:
        A ``Mesh`` over the stacked input/ring/refine node set.
    """
    stack = [np.asarray(points, float)[:, :2]]
    if boundary_ring is not None:
        stack.append(np.asarray(boundary_ring, float)[:, :2])
    if refine_points is not None:
        stack.append(np.asarray(refine_points, float)[:, :2])
    all_pts = np.vstack(stack)
    tri = Delaunay(all_pts)
    return Mesh(all_pts, tri.simplices.astype(int), time_days)


def assert_mesh_quality(mesh: Mesh, min_angle: float = 5.0) -> None:
    """Raise if any triangle's minimum interior angle is below ``min_angle`` degrees (sliver guard).

    Args:
        mesh: The triangulation to check.
        min_angle: The minimum acceptable interior angle in degrees.

    Raises:
        AssertionError: On a zero-area (degenerate) or sub-threshold (sliver) triangle.
    """
    p = mesh.points_xy
    worst = 180.0
    for t in mesh.triangles:
        tri = p[t]
        for a in range(3):
            v1 = tri[(a + 1) % 3] - tri[a]
            v2 = tri[(a + 2) % 3] - tri[a]
            denom = float(np.linalg.norm(v1) * np.linalg.norm(v2))
            if denom == 0.0:
                raise AssertionError("degenerate triangle: zero-length edge")
            ang = np.degrees(np.arccos(np.clip(np.dot(v1, v2) / denom, -1.0, 1.0)))
            worst = min(worst, float(ang))
    if worst < min_angle:
        raise AssertionError(f"sliver triangle: min angle {worst:.2f} deg < {min_angle} deg")
```

- [ ] **Step 4: Run — confirm pass** — `pixi run test tests/test_fem_mesh.py -v` → 4 passed; `pixi run typecheck` → clean.

- [ ] **Step 5: Commit**

```bash
git add src/sverdrup/methods/fem_mesh.py tests/test_fem_mesh.py
git commit -m "feat(fem): Mesh value object + Delaunay build_mesh + sliver guard"
```

---

## Task 2: `fem_precision` + agnosticism #1 — exact selective-inverse on an adversarial mesh (HEADLINE)

**Goal:** The P1 SPDE α=2 precision assembly, plus the PRIMARY agnosticism test: `diag(Q⁻¹)` via the inherited `GMRFFactor.selective_inverse_diag` equals a dense `Q⁻¹` diagonal to `rtol=1e-9` on a maximally-adversarial mesh, and every mesh edge is present-and-exact in the selective-inverse pattern (the assembly-pattern sub-claim).

**Files:**
- Create: `src/sverdrup/methods/fem.py` (the `fem_precision` function only in this task)
- Test: `tests/test_fem_precision.py`

**Acceptance Criteria:**
- [ ] `fem_precision(mesh, kappa, tau)` returns a symmetric SPD CSC precision `Q = (1/τ)(κ²C + G) C⁻¹ (κ²C + G)` (P1 lumped-mass `C`, stiffness `G`).
- [ ] On a maximally-adversarial mesh (variable valence, non-uniform spacing, a near-threshold sliver, jagged boundary), `GMRFFactor(Q).selective_inverse_diag()` matches `diag(dense Q⁻¹)` to `rtol=1e-9`.
- [ ] Every mesh edge `(i,j)`: `Σ_ij` is present in the selective-inverse pattern (0 absent) and equals the dense value.

**Verify:** `pixi run test tests/test_fem_precision.py -v && pixi run typecheck` → pass / clean.

**Steps:**

- [ ] **Step 1: Write the failing test** (hardens the committed `scripts/probe_fem_reduction_exactness.py`)

```python
# tests/test_fem_precision.py
"""AGNOSTICISM TIER #1 (headline): the inherited selective inverse is EXACT on FEM's irregular pattern.

Scope caveat (spec 0.2/7): this is strong falsifying evidence on the paths this adversarial fixture
exercises (selective-inverse diagonal + mesh-edge cov), proportional to fixture adversarial-ness — not
an unconditional proof of grid-agnosticism.
"""

from __future__ import annotations

import numpy as np

from sverdrup.methods.fem import fem_precision
from sverdrup.methods.fem_mesh import build_mesh
from sverdrup.methods.gmrf_linalg import GMRFFactor


def _adversarial_mesh(seed: int = 7):
    # MAXIMALLY ADVERSARIAL (spec 3 #1): variable valence, non-uniform spacing, a near-threshold
    # sliver, a jagged boundary ring, small enough for a dense Q^-1 ground truth.
    rng = np.random.default_rng(seed)
    cluster = rng.normal(0.3, 0.05, size=(18, 2))          # dense cluster -> high valence
    scatter = rng.uniform(0.0, 1.0, size=(22, 2))          # sparse scatter -> low valence
    theta = np.linspace(0.0, 2 * np.pi, 13, endpoint=False)
    r = 0.9 + 0.25 * rng.uniform(size=theta.size)          # irregular radius -> jagged boundary
    ring = np.c_[0.5 + r * np.cos(theta), 0.5 + r * np.sin(theta)]
    slivers = np.array([[0.501, 0.5], [0.503, 0.5005], [0.505, 0.501]])  # near-collinear sliver
    return build_mesh(np.vstack([cluster, scatter, ring, slivers]))


def _q_post(mesh) -> "object":
    q_prior = fem_precision(mesh, kappa=3.0, tau=0.05)
    n = mesh.n_nodes
    rng = np.random.default_rng(1)
    obs = rng.choice(n, size=8, replace=False)
    from scipy import sparse  # local import: test-only

    a = sparse.csc_matrix((np.ones(obs.size), (np.arange(obs.size), obs)), shape=(obs.size, n))
    return (q_prior + (a.T @ a) / 0.01).tocsc()


def test_selective_inverse_diag_exact_on_adversarial_mesh() -> None:
    # Behavior: the INHERITED Takahashi selective-inverse diagonal equals dense diag(Q^-1) on FEM's
    # irregular P1 pattern -> no hidden lattice assumption in the reduction path.
    # Bug it catches: any latent grid/lattice assumption in factorization or the selective inverse
    # (would produce plausible-but-wrong marginal variance on a non-grid pattern).
    mesh = _adversarial_mesh()
    assert mesh.points_xy.shape[0] >= 40  # dense-invertible but non-trivial
    q = _q_post(mesh)
    factor = GMRFFactor(q)
    sinv_diag = factor.selective_inverse_diag()
    dense = np.linalg.inv(q.toarray())
    rel = np.abs(sinv_diag - np.diag(dense)) / np.abs(np.diag(dense))
    assert rel.max() < 1e-9, f"selective-inverse diag not exact: max rel {rel.max():.2e}"


def test_every_mesh_edge_in_pattern_and_exact() -> None:
    # Behavior: every 1-hop mesh edge's Sigma_ij is IN the selective-inverse pattern (0 absent) and
    # exact vs dense -> the alpha=2 assembly (k^2 C + G) C^-1 (k^2 C + G) carries the 2-hop neighborhood.
    # Bug it catches: an assembly that drops mesh edges from Q's pattern so cov/firstdifference reads 0
    # (NOT implied by Takahashi-exactness alone; this is the assembly-pattern sub-claim, spec 0.1).
    mesh = _adversarial_mesh()
    q = _q_post(mesh)
    factor = GMRFFactor(q)
    sinv = factor.selective_inverse()
    dense = np.linalg.inv(q.toarray())
    edges = {
        tuple(sorted((int(t[a]), int(t[(a + 1) % 3]))))
        for t in mesh.triangles
        for a in range(3)
    }
    absent, checked = 0, 0
    for i, j in edges:
        checked += 1
        val = sinv[i, j]
        if val == 0.0 and sinv[j, i] == 0.0:
            absent += 1
            continue
        assert abs(val - dense[i, j]) / (abs(dense[i, j]) + 1e-30) < 1e-8
    assert absent == 0, f"{absent}/{checked} mesh edges absent from the selective-inverse pattern"
```

- [ ] **Step 2: Run — confirm fail** — `pixi run test tests/test_fem_precision.py -v` → FAIL (`ImportError: cannot import name 'fem_precision'`).

- [ ] **Step 3: Implement `fem_precision` in `fem.py`** (assembly proven by the committed probe)

```python
# src/sverdrup/methods/fem.py
"""FEM P1 SPDE method: precision assembly + basis read-off + solve (Phase 6).

FEM is a near-pure discretization swap: ``fem_precision`` and ``FEMBasisProjection`` are the only
mesh-carrying units; everything downstream (operator, CHOLMOD factor + Takahashi selective inverse,
reduction, coherent driver, blend) is inherited unchanged. Stationary scalar kappa only (per-node
kappa deferred — it scales entries, not the sparsity pattern).
"""

from __future__ import annotations

import numpy as np
from scipy import sparse  # type: ignore[import-untyped]

from sverdrup.methods.fem_mesh import Mesh, assert_mesh_quality


def fem_precision(mesh: Mesh, kappa: float, tau: float) -> sparse.csc_matrix:
    """Assemble the P1 SPDE alpha=2 precision ``Q = (1/tau)(k^2 C + G) C^-1 (k^2 C + G)``.

    ``C`` is the P1 lumped mass (diagonal, area/3 per node); ``G`` is the P1 stiffness (gradient
    inner products). The congruence ``(k^2 C + G) C^-1 (k^2 C + G)`` is SPD and carries the 2-hop
    neighborhood, so every 1-hop mesh edge is in ``Q``'s pattern.

    Args:
        mesh: The triangulation the precision lives on.
        kappa: Scalar SPDE inverse-range parameter (stationary; per-node deferred).
        tau: Variance scale (``diag(Q^-1)`` grows with ``tau``).

    Returns:
        A symmetric SPD ``(n_nodes, n_nodes)`` CSC precision.
    """
    assert_mesh_quality(mesh)
    p = mesh.points_xy
    n = mesh.n_nodes
    c_diag = np.zeros(n)
    g = sparse.lil_matrix((n, n))
    for t in mesh.triangles:
        tri = p[t]
        area = 0.5 * abs(
            (tri[1, 0] - tri[0, 0]) * (tri[2, 1] - tri[0, 1])
            - (tri[2, 0] - tri[0, 0]) * (tri[1, 1] - tri[0, 1])
        )
        if area <= 0:
            continue
        c_diag[t] += area / 3.0  # P1 lumped mass
        x, y = tri[:, 0], tri[:, 1]
        b = np.array([y[1] - y[2], y[2] - y[0], y[0] - y[1]])
        cc = np.array([x[2] - x[1], x[0] - x[2], x[1] - x[0]])
        ke = (np.outer(b, b) + np.outer(cc, cc)) / (4.0 * area)  # P1 stiffness
        for a in range(3):
            for bb in range(3):
                g[t[a], t[bb]] += ke[a, bb]
    c = sparse.diags(c_diag)
    c_inv = sparse.diags(1.0 / c_diag)
    k = (kappa**2) * c + g.tocsc()  # (k^2 C + G), SPD
    q = (k @ c_inv @ k) / tau  # (k^2 C + G) C^-1 (k^2 C + G) / tau
    return sparse.csc_matrix(0.5 * (q + q.T))  # symmetrize against round-off
```

- [ ] **Step 4: Run — confirm pass** — `pixi run test tests/test_fem_precision.py -v` → 2 passed; `pixi run typecheck` → clean.

- [ ] **Step 5: Commit**

```bash
git add src/sverdrup/methods/fem.py tests/test_fem_precision.py
git commit -m "feat(fem): P1 fem_precision + AGNOSTICISM #1 exact selective-inverse on adversarial mesh"
```

---

## Task 3: `FEMBasisProjection` — P1 basis read-off conforming to `Projection`

**Goal:** The mesh analogue of `bilinear_weights`: a P1 basis projection `W` via `Delaunay.find_simplex` + barycentric coordinates, conforming to `core/projection.py::Projection`, with a mesh-edge-in-pattern `assert_adjacency` (NOT the grid 5-point guard).

**Files:**
- Modify: `src/sverdrup/methods/fem.py` (add `FEMBasisProjection`)
- Test: `tests/test_fem_projection.py`

**Acceptance Criteria:**
- [ ] `FEMBasisProjection(mesh)` satisfies `isinstance(proj, Projection)` (runtime_checkable).
- [ ] `weights(pts)` returns a sparse `(k, n_nodes)` map whose rows sum to 1 (partition of unity); a point on a node is a unit selector.
- [ ] `field_shape() == (n_nodes,)`; `node_points(t)` returns `(n_nodes, 3)` matching `mesh.points()` in `(lon,lat)`.
- [ ] `assert_adjacency(Q)` passes when every mesh edge is in `Q`'s pattern and raises when an edge is absent.

**Verify:** `pixi run test tests/test_fem_projection.py -v && pixi run typecheck` → pass / clean.

**Steps:**

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fem_projection.py
"""FEMBasisProjection: P1 basis read-off conforming to the Projection seam."""

from __future__ import annotations

import numpy as np
import pytest
from scipy import sparse  # type: ignore[import-untyped]

from sverdrup.core.projection import Projection
from sverdrup.methods.fem import FEMBasisProjection, fem_precision
from sverdrup.methods.fem_mesh import build_mesh


def _mesh():
    xs, ys = np.meshgrid(np.linspace(0.0, 3.0, 5), np.linspace(0.0, 3.0, 5))
    return build_mesh(np.column_stack([xs.ravel(), ys.ravel()]), time_days=1.0)


def test_conforms_to_projection_protocol() -> None:
    # Behavior: FEMBasisProjection is a structural Projection (the seam the operator routes through).
    # Bug it catches: a missing/renamed hook that would break the discretization-agnostic operator.
    assert isinstance(FEMBasisProjection(_mesh()), Projection)


def test_weights_partition_of_unity_and_node_selector() -> None:
    # Behavior: P1 basis rows sum to 1; a query on a node is a unit selector on that node.
    # Bug it catches: barycentric weights that don't interpolate (biased A/W read-off).
    mesh = _mesh()
    proj = FEMBasisProjection(mesh)
    interior = np.array([[1.3, 1.7, 1.0], [2.1, 0.4, 1.0]])
    w = proj.weights(interior)
    assert w.shape == (2, mesh.n_nodes)
    assert np.allclose(np.asarray(w.sum(axis=1)).ravel(), 1.0)
    node = mesh.points()[3:4]  # exactly on node 3
    wn = proj.weights(node)
    assert wn[0, 3] > 0.999 and abs(wn.sum() - 1.0) < 1e-9


def test_field_shape_and_node_points() -> None:
    # Behavior: mesh field is flat (n_nodes,); node_points echoes the mesh coords with a time column.
    # Bug it catches: a (ny,nx) leak on the FEM path.
    mesh = _mesh()
    proj = FEMBasisProjection(mesh)
    assert proj.field_shape() == (mesh.n_nodes,)
    np_pts = proj.node_points(1.0)
    assert np_pts.shape == (mesh.n_nodes, 3)
    assert np.allclose(np_pts[:, :2], mesh.points_xy)


def test_assert_adjacency_mesh_edge_guard() -> None:
    # Behavior: the FEM adjacency guard passes on the real Q (edges in pattern) and raises when an
    # edge is missing -> the mesh analogue of the grid 5-point precondition, NOT the grid guard.
    # Bug it catches: routing FEM through assert_adjacency_in_pattern(shape=(ny,nx)) (grid-shaped).
    mesh = _mesh()
    proj = FEMBasisProjection(mesh)
    q = fem_precision(mesh, kappa=3.0, tau=0.05)
    proj.assert_adjacency(q)  # no raise: alpha=2 carries every mesh edge
    # a precision missing an edge -> loud red
    empty = sparse.identity(mesh.n_nodes, format="csc")
    with pytest.raises(AssertionError, match="edge|pattern"):
        proj.assert_adjacency(empty)
```

- [ ] **Step 2: Run — confirm fail** — FAIL (`cannot import name 'FEMBasisProjection'`).

- [ ] **Step 3: Add `FEMBasisProjection` to `fem.py`**

```python
# append to src/sverdrup/methods/fem.py

from dataclasses import dataclass

from scipy.spatial import Delaunay  # type: ignore[import-untyped]

from sverdrup.core.types import Points


@dataclass(frozen=True)
class FEMBasisProjection:
    """P1 basis read-off ``W`` (mesh analogue of ``bilinear_weights``); a ``Projection``.

    ``weights(pts)`` locates each query point's triangle via ``Delaunay.find_simplex`` and evaluates
    the three P1 barycentric basis functions -> a sparse ``(k, n_nodes)`` map. ``A`` (node -> obs) is
    this at obs points. ``assert_adjacency`` is the mesh-edge-in-pattern precondition (NOT the grid
    5-point guard): every triangulation edge must be present in the precision's sparsity pattern.
    """

    mesh: Mesh

    @property
    def node_space(self) -> Mesh:
        """Return the node layout (the mesh)."""
        return self.mesh

    def _delaunay(self) -> Delaunay:
        return Delaunay(self.mesh.points_xy)

    def weights(self, pts: Points) -> sparse.csr_matrix:
        """Return the sparse ``(k, n_nodes)`` P1-basis map from mesh nodes to ``pts``."""
        tri = self._delaunay()
        query = np.asarray(pts, float)[:, :2]
        simplex = tri.find_simplex(query)
        k = query.shape[0]
        rows, cols, vals = [], [], []
        transforms = tri.transform
        for r in range(k):
            s = int(simplex[r])
            if s < 0:  # outside the hull -> nearest node (unit selector), keeps rows summing to 1
                nearest = int(np.argmin(np.linalg.norm(self.mesh.points_xy - query[r], axis=1)))
                rows.append(r)
                cols.append(nearest)
                vals.append(1.0)
                continue
            b = transforms[s, :2] @ (query[r] - transforms[s, 2])
            bary = np.array([b[0], b[1], 1.0 - b[0] - b[1]])
            for vtx, wgt in zip(tri.simplices[s], bary, strict=False):
                if wgt != 0.0:
                    rows.append(r)
                    cols.append(int(vtx))
                    vals.append(float(wgt))
        w = sparse.csr_matrix((vals, (rows, cols)), shape=(k, self.mesh.n_nodes))
        rs = np.asarray(w.sum(axis=1)).ravel()
        rs[rs == 0] = 1.0
        return sparse.diags(1.0 / rs) @ w

    def field_shape(self) -> tuple[int, ...]:
        """Return ``(n_nodes,)`` — the FEM field is flat over mesh nodes."""
        return (self.mesh.n_nodes,)

    def node_points(self, time_days: float) -> Points:
        """Return the ``(n_nodes, 3)`` mesh node coordinates at ``time_days``."""
        n = self.mesh.n_nodes
        return np.column_stack([self.mesh.points_xy, np.full(n, time_days)]).astype(float)

    def assert_adjacency(self, q: sparse.spmatrix) -> None:
        """Raise if any mesh edge ``(i,j)`` is absent from ``q``'s pattern (mesh analogue of 5-point)."""
        qcoo = q.tocoo()
        present = set(zip(qcoo.row.tolist(), qcoo.col.tolist(), strict=False))
        for t in self.mesh.triangles:
            for a in range(3):
                i, j = int(t[a]), int(t[(a + 1) % 3])
                if (i, j) not in present or (j, i) not in present:
                    raise AssertionError(
                        f"mesh edge ({i},{j}) absent from Q pattern — FEM read-off/cov would break"
                    )
```

- [ ] **Step 4: Run — confirm pass** — `pixi run test tests/test_fem_projection.py -v` → 4 passed; `pixi run typecheck` → clean.

- [ ] **Step 5: Commit**

```bash
git add src/sverdrup/methods/fem.py tests/test_fem_projection.py
git commit -m "feat(fem): FEMBasisProjection P1 read-off + mesh-edge adjacency guard"
```

---

## Task 4: `FEMMatern.solve` + register `"fem"` + agnosticism #2 (whole-path grid-shortcut audit)

**Goal:** `FEMMatern.solve` (mirror of `MaternGMRF.solve`, mesh-injected), registered `"fem"`, plus the second primary agnosticism test: a full `solve → reduce → project` run on an injected adversarial mesh with `bilinear_weights` and `(ny,nx)` reshape **guarded to raise if hit**, and end-to-end exact marginal variance through the inherited `GMRFPrecisionReduction` vs dense `Q⁻¹`.

**Files:**
- Modify: `src/sverdrup/methods/fem.py` (add `FEMMatern`)
- Modify: `src/sverdrup/methods/registry.py` (register `"fem"`)
- Test: `tests/test_fem_agnosticism_path.py`

**Acceptance Criteria:**
- [ ] `FEMMatern(mesh=None)` is constructible with no args (registry contract); `.solve(obs, grid, params, time_days)` builds `Q_prior = fem_precision`, `A = FEMBasisProjection.weights(obs)`, `Q_post = Q_prior + AᵀR⁻¹A` with the same temporal taper as `MaternGMRF`, wraps the same `GMRFCovarianceOperator`, returns a distribution with a flat `(n_nodes,)` mean.
- [ ] `"fem"` resolves in `registry.METHODS`.
- [ ] Whole-path audit: a full FEM `solve → GMRFPrecisionReduction.reduce → eval-point project` runs with `bilinear_weights` monkeypatched to raise and never triggers it; `field_shape()` is `(n_nodes,)`.
- [ ] End-to-end: `reduce(...).base_fields.marginal_variance` (via the inherited reduction) matches `diag(dense Q_post⁻¹)` to `rtol=1e-9`.

**Verify:** `pixi run test tests/test_fem_agnosticism_path.py -v && pixi run typecheck` → pass / clean.

**Steps:**

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fem_agnosticism_path.py
"""AGNOSTICISM TIER #2: the whole solve->reduce->project path takes no grid shortcut on FEM.

Scope caveat (spec 0.2/7): falsifying evidence on the exercised path only.
"""

from __future__ import annotations

import numpy as np

from sverdrup.core.grid import GridSpec
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
from sverdrup.core.parameters import ConstantProvider
from sverdrup.distributions.reduction import GMRFPrecisionReduction
from sverdrup.methods import gmrf_grid
from sverdrup.methods.fem import FEMMatern
from sverdrup.methods.fem_mesh import build_mesh
from sverdrup.methods.registry import METHODS


def _irregular_mesh():
    rng = np.random.default_rng(3)
    pts = np.vstack([rng.uniform(0.0, 4.0, size=(40, 2)), rng.normal(2.0, 0.3, size=(15, 2))])
    return build_mesh(pts, time_days=2.0)


def _obs() -> ObsWindow:
    rng = np.random.default_rng(0)
    lon = rng.uniform(0.5, 3.5, size=10)
    lat = rng.uniform(0.5, 3.5, size=10)
    return ObsWindow.from_arrays(
        lon, lat, np.full(10, 2.0), rng.normal(0.0, 0.1, size=10),
        DiagonalErrorModel(np.full(10, 1e-3)),
    )


def test_fem_registered() -> None:
    # Behavior: "fem" is a registered method. Bug it catches: forgetting the registry wiring.
    assert "fem" in METHODS


def test_whole_path_takes_no_grid_shortcut(monkeypatch) -> None:  # noqa: ANN001
    # Behavior: a full FEM solve->reduce->project never calls bilinear_weights (the grid read-off);
    # the FEM path holds field_shape (n_nodes,). Bug it catches: any grid shortcut on the FEM path.
    def _boom(*a, **k):  # noqa: ANN002, ANN003
        raise AssertionError("bilinear_weights called on the FEM path — grid shortcut detected")

    monkeypatch.setattr(gmrf_grid, "bilinear_weights", _boom)
    mesh = _irregular_mesh()
    grid = GridSpec.lonlat(np.arange(0.0, 4.0), np.arange(0.0, 4.0))
    params = ConstantProvider({"range": 150.0, "variance": 0.05, "temporal_taper_scale": 5.0})
    dist = FEMMatern(mesh=mesh).solve(_obs(), grid, params, 2.0)
    assert dist.cov_op.projection.field_shape() == (mesh.n_nodes,)
    eval_pts = np.array([[1.5, 1.5, 2.0], [2.5, 2.5, 2.0]])
    unit = GMRFPrecisionReduction().reduce(dist, mesh.points(), eval_pts, rank=0, seed=1)
    assert unit.base_fields.marginal_variance.shape == (mesh.n_nodes,)


def test_end_to_end_marginal_var_exact_vs_dense() -> None:
    # Behavior: reported marginal variance through the INHERITED reduction equals dense diag(Q_post^-1).
    # Bug it catches: the operator/reduction wrapping introducing a grid-shaped error on the mesh path.
    mesh = _irregular_mesh()
    grid = GridSpec.lonlat(np.arange(0.0, 4.0), np.arange(0.0, 4.0))
    params = ConstantProvider({"range": 150.0, "variance": 0.05, "temporal_taper_scale": 5.0})
    dist = FEMMatern(mesh=mesh).solve(_obs(), grid, params, 2.0)
    unit = GMRFPrecisionReduction().reduce(dist, mesh.points(), None, rank=0, seed=1)
    dense = np.diag(np.linalg.inv(dist.cov_op.q_post.toarray()))
    rel = np.abs(unit.base_fields.marginal_variance - dense) / np.abs(dense)
    assert rel.max() < 1e-9
```

- [ ] **Step 2: Run — confirm fail** — FAIL (`cannot import name 'FEMMatern'`).

- [ ] **Step 3: Add `FEMMatern` to `fem.py`** (mirror of `MaternGMRF.solve`, mesh-injected)

```python
# append to src/sverdrup/methods/fem.py

from sverdrup.core.grid import GridSpec, PointSet
from sverdrup.core.observations import ObsWindow
from sverdrup.core.parameters import ParameterProvider, ParameterSpace
from sverdrup.core.provenance import (
    KnownBias,
    TransformKind,
    UncertaintyProvenance,
    UncertaintyTransform,
)
from sverdrup.core.types import UncertaintyCapability
from sverdrup.distributions.gaussian import GaussianPredictiveDistribution
from sverdrup.methods.gmrf import GMRFCovarianceOperator
from sverdrup.methods.gmrf_grid import kappa_from_range


class FEMMatern:
    """FEM P1 Matérn GMRF: mesh SPDE precision + temporally-tapered likelihood (Phase 6).

    ``mesh=None`` (the registry path) triangulates the grid's own node points inside ``solve``;
    a supplied ``mesh`` (the agnosticism tests) drives an arbitrary irregular triangulation through
    the full registered path.
    """

    native_capability = UncertaintyCapability.SAMPLES  # also exposes COVARIANCE

    def __init__(self, mesh: Mesh | None = None) -> None:
        """Store an optional injected mesh; when ``None`` the mesh is built from the grid in ``solve``."""
        self.mesh = mesh

    def solve(
        self,
        obs: ObsWindow,
        grid: GridSpec,
        params: ParameterProvider,
        time_days: float,
    ) -> GaussianPredictiveDistribution:
        """Solve the FEM-GMRF posterior over the mesh at ``time_days`` (temporal taper into R)."""
        from sverdrup.methods.fem_mesh import build_mesh

        mesh = self.mesh if self.mesh is not None else build_mesh(
            grid.points(time_days), time_days=time_days
        )
        tau = float(params.resolve("variance", grid))
        taper = float(params.resolve("temporal_taper_scale", grid))
        kappa = float(kappa_from_range(float(params.resolve("range", grid))))
        q_prior = fem_precision(mesh, kappa, tau)

        projection = FEMBasisProjection(mesh)
        a_op = projection.weights(obs.coords())  # (n_obs, n_nodes)
        r_diag = np.diag(obs.error_model.as_matrix(len(obs))).astype(float)
        dt = np.abs(obs.coords()[:, 2] - time_days)
        r_inflated = r_diag * np.exp(dt / max(taper, 1e-9))
        r_inv = sparse.diags(1.0 / r_inflated)

        q_post = (q_prior + a_op.T @ r_inv @ a_op).tocsc()
        op = GMRFCovarianceOperator(projection, q_post, time_days, q_prior=q_prior)
        rhs = a_op.T @ (r_inv @ obs.values())
        mean = op._factor.solve(np.asarray(rhs)).reshape(projection.field_shape())

        support = PointSet(mesh.points(), grid.crs)
        prov = UncertaintyProvenance(
            native_capability=self.native_capability,
            transformations=[
                UncertaintyTransform(
                    kind=TransformKind.DIAGONAL_INFLATION,
                    known_bias=KnownBias.UNDER_DISPERSED_IN_VOIDS,
                    params={
                        "temporal_taper": "diagonal-R; FEM P1 SPDE, mesh discretization",
                        "temporal_taper_scale": taper,
                        "discretization": "fem-p1-triangulation",
                    },
                )
            ],
        )
        return GaussianPredictiveDistribution(support, mean, op, prov, time_days)

    def parameter_space(self) -> ParameterSpace:
        """Return the tunable space (same knobs as the grid GMRF; ν fixed to α=2)."""
        return ParameterSpace(
            {
                "range": (10.0, 800.0),
                "variance": (1e-3, 1.0),
                "temporal_taper_scale": (1.0, 30.0),
            }
        )
```

- [ ] **Step 4: Register `"fem"` in `registry.py`**

Find:
```python
from sverdrup.methods.gmrf import MaternGMRF
from sverdrup.methods.oi import OptimalInterpolation
from sverdrup.methods.trivial import TrivialInterpolation

METHODS = {
    "oi": OptimalInterpolation,
    "gmrf": MaternGMRF,
    "trivial": TrivialInterpolation,
}
```
Replace with:
```python
from sverdrup.methods.fem import FEMMatern
from sverdrup.methods.gmrf import MaternGMRF
from sverdrup.methods.oi import OptimalInterpolation
from sverdrup.methods.trivial import TrivialInterpolation

METHODS = {
    "oi": OptimalInterpolation,
    "gmrf": MaternGMRF,
    "fem": FEMMatern,
    "trivial": TrivialInterpolation,
}
```

- [ ] **Step 5: Run — confirm pass** — `pixi run test tests/test_fem_agnosticism_path.py -v` → 3 passed; `pixi run typecheck` → clean.

- [ ] **Step 6: Regression** — `pixi run test tests/test_gmrf_method.py tests/test_reduction.py -q` → all pass (the operator/reduction still serve the grid unchanged).

- [ ] **Step 7: Commit**

```bash
git add src/sverdrup/methods/fem.py src/sverdrup/methods/registry.py tests/test_fem_agnosticism_path.py
git commit -m "feat(fem): FEMMatern.solve + register fem + AGNOSTICISM #2 whole-path grid-shortcut audit"
```

---

## Task 5: C7 — boundary-extension MECHANISM demo vs the named grid baseline

**Goal:** Demonstrate the boundary-extension mechanism on a synthetic fixture with an extended boundary ring: `edge_var(FEM) < edge_var(grid)` at near-boundary nodes, against the honestly-named shipped baseline (the grid GMRF's 5-point Neumann-edge Laplacian, `_laplacian`, `gmrf_grid.py:48`). NOT a "FEM better on real coasts" value claim; not rigged to make FEM win.

**Files:**
- Test: `tests/test_fem_boundary_payoff.py`

**Acceptance Criteria:**
- [ ] On a domain with a boundary-ring-extended FEM mesh vs a same-footprint regular grid (identical κ, τ, obs), the FEM near-boundary marginal variance is lower than the grid's at the domain-edge nodes (mechanism demo).
- [ ] The comparison is at near-boundary nodes specifically (not interior-averaged); the baseline is documented in the test as the Neumann-edge grid Laplacian.

**Verify:** `pixi run test tests/test_fem_boundary_payoff.py -v && pixi run typecheck` → pass / clean.

**Steps:**

- [ ] **Step 1: Write the test** (this task is a measurement, so the first run confirms the mechanism, not a red)

```python
# tests/test_fem_boundary_payoff.py
"""C7 (secondary): the boundary-extension MECHANISM reduces near-edge variance vs the shipped grid.

Honest baseline (spec 4.2): the grid GMRF prior uses a 5-point finite-difference Laplacian with
NEUMANN (zero-flux) edges (_laplacian, gmrf_grid.py:48) — edge nodes lack outward neighbour support,
inflating their variance. FEM's boundary ring supplies that support. This demonstrates that mechanism
on a controlled fixture; it is NOT a value claim about real coasts (real data deferred, ODC dead).
"""

from __future__ import annotations

import numpy as np

from sverdrup.core.grid import GridSpec
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
from sverdrup.core.parameters import ConstantProvider
from sverdrup.methods.fem import FEMMatern
from sverdrup.methods.fem_mesh import build_mesh
from sverdrup.methods.gmrf import MaternGMRF


def _obs(seed: int = 0) -> ObsWindow:
    rng = np.random.default_rng(seed)
    lon = rng.uniform(0.5, 3.5, size=12)
    lat = rng.uniform(0.5, 3.5, size=12)
    return ObsWindow.from_arrays(
        lon, lat, np.full(12, 1.0), rng.normal(0.0, 0.1, size=12),
        DiagonalErrorModel(np.full(12, 1e-3)),
    )


def test_boundary_ring_reduces_near_edge_variance() -> None:
    # Behavior: a boundary-extended FEM mesh has lower marginal variance at domain-edge nodes than the
    # Neumann-edge grid at the same edge locations (the boundary-extension mechanism).
    # Bug it catches: the boundary ring not actually supplying edge support -> no mechanism.
    params = ConstantProvider({"range": 200.0, "variance": 0.05, "temporal_taper_scale": 5.0})
    obs = _obs()

    grid = GridSpec.lonlat(np.arange(0.0, 4.0), np.arange(0.0, 4.0))
    gdist = MaternGMRF().solve(obs, grid, params, 1.0)
    gnodes = grid.points(1.0)
    gvar = gdist.cov_op.marginal_var(gnodes)

    # FEM mesh on the SAME core node set, extended by a boundary ring one cell out.
    core = grid.points(1.0)[:, :2]
    ring = np.array([[x, y] for x in (-1.0, 4.0) for y in np.linspace(-1.0, 4.0, 6)]
                    + [[x, y] for y in (-1.0, 4.0) for x in np.linspace(-1.0, 4.0, 6)])
    mesh = build_mesh(core, boundary_ring=ring, time_days=1.0)
    fdist = FEMMatern(mesh=mesh).solve(obs, grid, params, 1.0)
    fvar = fdist.cov_op.marginal_var(mesh.points())

    # near-boundary = domain-edge core nodes (x or y at 0 or 3)
    edge = (np.isclose(gnodes[:, 0], 0.0) | np.isclose(gnodes[:, 0], 3.0)
            | np.isclose(gnodes[:, 1], 0.0) | np.isclose(gnodes[:, 1], 3.0))
    # map each edge core node to its FEM node (coincident, since core points are shared)
    fem_xy = mesh.points_xy
    fem_edge_var = []
    for gp in gnodes[edge]:
        idx = int(np.argmin(np.linalg.norm(fem_xy - gp[:2], axis=1)))
        fem_edge_var.append(fvar[idx])
    assert np.median(fem_edge_var) < np.median(gvar[edge]), (
        "boundary ring did not reduce near-edge variance vs the Neumann-edge grid baseline"
    )
```

- [ ] **Step 2: Run — confirm the mechanism** — `pixi run test tests/test_fem_boundary_payoff.py -v` → pass. If it fails, the boundary ring is not supplying edge support: STOP and surface (per spec, do not loosen or rig the comparison — investigate the mechanism).

- [ ] **Step 3: Typecheck** — `pixi run typecheck` → clean.

- [ ] **Step 4: Commit**

```bash
git add tests/test_fem_boundary_payoff.py
git commit -m "test(fem): C7 boundary-extension mechanism demo vs Neumann-edge grid baseline"
```

---

## Task 6: Multi-tile FEM inheritance + C6 shared-node (secondary, lowest-information)

**Goal:** Confirm FEM tiles (node subsets of overlapping meshes sharing coincident nodes) blend through the *live* `GmrfTreeKrigingSolve` unchanged, and that the discretization-agnostic `CoherenceFeasibility` envelope applies verbatim (MARGINAL_VARIANCE ships; SAMPLES/COVARIANCE only at `n_tiles ≤ n_star_joint`). Per the spec this re-confirms an envelope already proven agnostic at the predicate level — completeness, not an agnosticism test.

**Files:**
- Test: `tests/test_fem_multitile.py`

**Acceptance Criteria:**
- [ ] Two overlapping FEM tiles built via `FEMMatern.solve → GMRFPrecisionReduction.reduce → PrecisionDistribution` share a non-empty coincident-node set (`_tile_adjacency` non-empty) — C6.
- [ ] `GmrfTreeKrigingSolve().crossfaded_member(...)` returns a finite coherent field over the two FEM tiles (the inherited driver works on mesh supports).
- [ ] `CoherenceFeasibility().feasible(params, TileGeometry(core, range, "mesh", n_tiles=N), {SAMPLES})` returns the SAME verdict as for a grid: feasible at `N=1`, infeasible at `N=2` (discretization-agnostic envelope).

**Verify:** `pixi run test tests/test_fem_multitile.py -v && pixi run typecheck` → pass / clean.

**Steps:**

- [ ] **Step 1: Write the test** (mirrors `tests/unit/_tree_gate.py` parts construction with FEM tiles)

```python
# tests/test_fem_multitile.py
"""Multi-tile FEM inheritance (secondary, lowest-information): the live tree driver + agnostic envelope.

The coherence envelope is already discretization-agnostic at the predicate level (CoherenceFeasibility
keys on n_tiles + capability, no grid/mesh); this re-confirms the FEM swap doesn't break the inherited
driver and inherits that envelope verbatim.
"""

from __future__ import annotations

import numpy as np

from sverdrup.application.tuning.feasibility import CoherenceFeasibility, TileGeometry
from sverdrup.core.geometry import Tile, Window
from sverdrup.core.grid import GridSpec
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
from sverdrup.core.parameters import ConstantProvider
from sverdrup.core.types import UncertaintyCapability as UC
from sverdrup.distributions.blend import BlendInput, partition_weights
from sverdrup.distributions.coherent import (
    GmrfTreeKrigingSolve,
    NoiseSpec,
    _tile_adjacency,
)
from sverdrup.distributions.persisted import PrecisionDistribution
from sverdrup.distributions.reduction import GMRFPrecisionReduction
from sverdrup.methods.fem import FEMMatern
from sverdrup.methods.fem_mesh import build_mesh

_T = 2.0
_PROV = ConstantProvider({"range": 200.0, "variance": 0.05, "temporal_taper_scale": 5.0})


def _obs() -> ObsWindow:
    rng = np.random.default_rng(0)
    lon = rng.uniform(0.0, 10.0, size=12)
    lat = rng.uniform(0.0, 6.0, size=12)
    return ObsWindow.from_arrays(
        lon, lat, np.full(12, _T), rng.normal(0.0, 0.1, size=12),
        DiagonalErrorModel(np.full(12, 1e-3)),
    )


def _fem_part(x_lo: float, x_hi: float, core: tuple[float, float], ext: tuple[float, float]) -> BlendInput:
    # a mesh whose nodes lie on an integer lattice in [x_lo,x_hi] x [0,5] -> adjacent tiles share
    # coincident integer nodes in their overlap (so _node_keys matches them).
    xs, ys = np.meshgrid(np.arange(x_lo, x_hi + 1.0), np.arange(0.0, 6.0))
    mesh = build_mesh(np.column_stack([xs.ravel(), ys.ravel()]), time_days=_T)
    grid = GridSpec.lonlat(np.arange(x_lo, x_hi + 1.0), np.arange(0.0, 6.0))
    dist = FEMMatern(mesh=mesh).solve(_obs(), grid, _PROV, _T)
    unit = GMRFPrecisionReduction().reduce(dist, mesh.points(), None, rank=0, seed=3)
    pd = PrecisionDistribution(dist.grid, unit.base_fields, dist.provenance, _T)
    tile = Tile(Window(core, (0.0, 5.0), (0.0, 0.0)), Window(ext, (0.0, 5.0), (0.0, 0.0)), dist.grid)
    return BlendInput(pd, tile)


def test_fem_tiles_share_nodes_and_blend_through_live_driver() -> None:
    # Behavior: two overlapping FEM tiles share coincident nodes (C6) and the LIVE GmrfTreeKrigingSolve
    # produces a finite coherent field over them (the mesh swap doesn't break the inherited driver).
    # Bug it catches: a mesh-node-index/key mismatch that empties the shared set or NaNs the sweep.
    parts = [
        _fem_part(0.0, 6.0, (0.0, 6.0), (0.0, 7.0)),
        _fem_part(4.0, 10.0, (4.0, 10.0), (3.0, 10.0)),
    ]
    adj = _tile_adjacency(parts)
    assert (0, 1) in adj and len(adj[(0, 1)]) > 0  # C6: coincident-node set non-empty

    out_pts = np.column_stack([np.arange(0.0, 10.0), np.full(10, 2.0), np.full(10, _T)]).astype(float)
    weights = partition_weights([p.tile for p in parts], out_pts)
    noise = NoiseSpec(method="fem", params_key="p", lattice_step=1.0)
    field = GmrfTreeKrigingSolve().crossfaded_member(parts, out_pts, weights, member_index=0, noise=noise)
    assert field.shape == (10,) and np.all(np.isfinite(field))


def test_fem_inherits_coherence_envelope_verbatim() -> None:
    # Behavior: the feasibility verdict is discretization-agnostic — a mesh TileGeometry gets the same
    # SAMPLES verdict as a grid: feasible at n_tiles=1, infeasible at n_tiles=2 (n_star_joint=1).
    # Bug it catches: FEM smuggling a different coherence envelope than the shipped predicate.
    pred = CoherenceFeasibility()
    params = {"range": 200.0}
    assert pred.feasible(params, TileGeometry(4.0, 200.0, "mesh", n_tiles=1), frozenset({UC.SAMPLES}))
    assert not pred.feasible(params, TileGeometry(4.0, 200.0, "mesh", n_tiles=2), frozenset({UC.SAMPLES}))
    # MARGINAL_VARIANCE ships regardless of tile count (worst-case flat, within marg_tol)
    assert pred.feasible(params, TileGeometry(4.0, 200.0, "mesh", n_tiles=9), frozenset({UC.MARGINAL_VARIANCE}))
```

- [ ] **Step 2: Run — confirm** — `pixi run test tests/test_fem_multitile.py -v` → 2 passed. If the coherent sweep NaNs or the shared set is empty, the mesh-node keys aren't matching across tiles (C6 failure): STOP and surface — do not weaken the assertion.

- [ ] **Step 3: Typecheck** — `pixi run typecheck` → clean.

- [ ] **Step 4: Full regression** — `pixi run test tests/test_fem_mesh.py tests/test_fem_precision.py tests/test_fem_projection.py tests/test_fem_agnosticism_path.py tests/test_fem_boundary_payoff.py tests/test_fem_multitile.py tests/test_gmrf_method.py tests/test_reduction.py tests/test_stage_c_hard_barrier.py -q` → all pass.

- [ ] **Step 5: Commit**

```bash
git add tests/test_fem_multitile.py
git commit -m "test(fem): multi-tile FEM inheritance via live tree driver + agnostic envelope (C6)"
```

---

## Self-review

**Spec coverage** (spec § → task):
- §0.1 headline / §3 #1 exact-marginal-var on adversarial mesh → **Task 2** (assembly-level, matches the committed probe) + **Task 4** end-to-end through the reduction.
- §3 #2 whole-path grid-shortcut audit → **Task 4** (`bilinear_weights` raise-guard + `field_shape (n_nodes,)`).
- §2.1 Mesh + build_mesh + sliver guard → **Task 1**. §2.2 `fem_precision` → **Task 2**; `FEMBasisProjection` (mesh-edge `assert_adjacency`) → **Task 3**; `FEMMatern.solve` → **Task 4**. §2.3 register `"fem"` → **Task 4**.
- §4.1 sliver guard → Task 1; C6 shared-node → **Task 6**. §4.2 C7 boundary mechanism vs Neumann baseline → **Task 5**. §4.3 multi-tile via live `GmrfTreeKrigingSolve` + agnostic envelope → **Task 6**.
- §0.2/§7 honest-scope caveat → carried in the Task 2 / Task 4 test docstrings.
- §5 deferred (nonstationary κ, real OSSE/OSE, production meshing, coarse-correction) → out of scope, not tasked (correct).

**Placeholder scan:** none — every step carries full code + exact commands.

**Type/name consistency:** `Mesh(points_xy, triangles, time_days)` / `.points()` / `.n_nodes` used identically in Tasks 1–6; `fem_precision(mesh, kappa, tau)` signature consistent (Tasks 2,3,4); `FEMBasisProjection(mesh)` hooks (`weights`/`field_shape`/`node_points`/`assert_adjacency`) match the `Projection` protocol (verified against `core/projection.py`); `FEMMatern(mesh=None).solve(obs, grid, params, time_days)` mirrors `MaternGMRF.solve` (verified against `gmrf.py:110`); `GMRFCovarianceOperator(projection, q_post, time_days, q_prior=)` matches `gmrf.py:37`; multi-tile parts (`BlendInput(PrecisionDistribution, Tile)`, `GMRFPrecisionReduction().reduce`, `GmrfTreeKrigingSolve().crossfaded_member`, `_tile_adjacency`, `NoiseSpec`, `partition_weights`) verified against `_tree_gate.py` + `coherent.py`; `CoherenceFeasibility().feasible(params, TileGeometry(...), caps)` + `TileGeometry(core, range, id, n_tiles=)` verified against `feasibility.py`.

**Note on Task 4 support type:** FEM's distribution support is `PointSet(mesh.points(), grid.crs)` (concrete `core/grid.py:137`), so the coherent driver's `_support_points` (`isinstance(support, PointSet)`) and `_node_keys` (reads `[:, :2]`) work unchanged on FEM tiles.

**Note on Tasks 5/6 red:** these are measurement/inheritance confirmations, not red/green — the spec calls them secondary completeness. Their first run confirms the mechanism; a failure is a STOP-and-surface signal, not a threshold to loosen.
