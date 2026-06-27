# Phase 4 — FEM/triangulation SPDE + non-chain coherent sampler — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the GMRF from a regular-grid discretization to a finite-element (FEM/triangulation) SPDE and replace the chain-only cross-tile coherent sampler with a topology-agnostic one, in three generalize-under-green stages.

**Architecture:** Stage A wires a consumed `Projection` seam onto the operator and the persisted form and de-grids persistence (Phase-3 suite is the regression oracle). Stage B replaces `GmrfKrigingSolve`'s lon-chain sweep with `GmrfJointKrigingSolve` (kriging toward ONE pre-drawn joint field over the overlap-strip network), validated on 2-D grid tiling. Stage C adds FEM (scipy.spatial.Delaunay mesh + hand-rolled P1 assembly + `FEMBasisProjection`) inheriting the now-topology-agnostic sampler, with a boundary-extension payoff demo.

**Tech Stack:** Python 3.12+, numpy, scipy (incl. `scipy.spatial.Delaunay` — no new dep), scikit-sparse/CHOLMOD (existing), pytest. Earth-science plotting via the `plotting-colormaps` skill (cmocean).

**User decisions (already made):**
- FEM mesh + assembly: "scipy.spatial.Delaunay + hand-rolled P1 (lumped-mass C + stiffness G)"; demos driven by the input point set (boundary ring / densified points); Shewchuk meshing is the noted upgrade behind the same seam.
- A sliver-quality guard in `fem_precision` is the FEM analogue of `_assert_separates` (loud red).
- Stage-B joint field: "spec-literal, global-prior-over-strips, gated" — residual measured-vs-single-tile-reference and recorded (`known_bias`); junction-tree fallback ONLY on out-of-tolerance residual, never because the construction is approximate.
- Five pinned correctness contracts C1–C5 + two confirmations C6–C7 (see design doc §0) are tested, not assumed.
- Hold at this plan for owner approval before any implementation code; three stage gates (A green → B; B positive-control passes → C) are user-thrown gates.

**Source of truth:** `phase4_scope_spec.md` (settled + amended, HEAD `00519b1`). **Design:** `docs/superpowers/specs/2026-06-26-phase4-fem-and-nonchain-sampler-design.md` (`f7960f8`). **Builds on:** Phase-3 HEAD `31a58c6` (suite 178 passed / 2 skipped).

---

## Conventions used throughout

- Run tools via pixi: `pixi run test`, `pixi run typecheck`, `pixi run lint`, `pixi run pre-commit run --files <paths>`.
- mypy runs `mypy .` (tests included) — keep test files type-clean (assert `x is not None` before use; wrap numpy returns in `np.asarray`).
- Commit after every task with Conventional Commits; never commit failing pre-commit.
- "Phase-3 suite green" = `pixi run test` reports **178 passed / 2 skipped** (or more, with new tests), zero failures, zero pre-existing tests modified except the single Stage-B wiring assertion called out in Task 7.

---

# STAGE A — generalize under green

## Task 1: The `Projection` seam + refactor the grid dataclasses into it

**Goal:** Introduce the `core/projection.py` `Projection` Protocol and make the (currently dead) `GridIdentityProjection`/`BilinearProjection` conform to it — additively, keeping their existing `.matrix` property so `test_gmrf_grid` stays green.

**Files:**
- Create: `src/sverdrup/core/projection.py`
- Modify: `src/sverdrup/methods/gmrf_grid.py` (add protocol methods to the two dataclasses; keep `.matrix`)
- Test: `tests/unit/test_projection.py` (new)

**Acceptance Criteria:**
- [ ] `Projection` is a `runtime_checkable` Protocol with `node_space`, `weights(pts)`, `field_shape()`, `node_points(t)`, `assert_adjacency(q)`.
- [ ] `GridIdentityProjection(grid)` and `BilinearProjection(grid, pts)` are `isinstance(..., Projection)` True, keep `.matrix`, and `weights()` equals `bilinear_weights` for the off-grid case / a unit selector on nodes.
- [ ] `GridIdentityProjection(grid).field_shape() == grid.shape`; `BilinearProjection(grid, pts).field_shape() == (len(pts),)`.
- [ ] Existing `tests/unit/test_gmrf_grid.py::test_projection_identity_and_bilinear` still passes unchanged.

**Verify:** `pixi run test tests/unit/test_projection.py tests/unit/test_gmrf_grid.py -v` → all pass.

**Steps:**

- [ ] **Step 1: Write the failing test** — `tests/unit/test_projection.py`:

```python
"""The Projection seam: grid dataclasses conform; weights/field_shape are load-bearing."""

from __future__ import annotations

import numpy as np
from scipy import sparse

from sverdrup.core.grid import GridSpec
from sverdrup.core.projection import Projection
from sverdrup.methods.gmrf_grid import (
    BilinearProjection,
    GridIdentityProjection,
    bilinear_weights,
)


def _grid() -> GridSpec:
    return GridSpec(x=np.arange(10.0), y=np.arange(10.0), crs="EPSG:4326")


def test_grid_projections_are_projections():
    # Behavior: both grid dataclasses structurally satisfy the Projection protocol.
    # Bug caught: a projection missing weights/field_shape/node_points would be
    #   silently un-consumable by the operator, reverting to the hardcoded read-off.
    g = _grid()
    assert isinstance(GridIdentityProjection(g), Projection)
    assert isinstance(BilinearProjection(g, g.points(0.0)), Projection)


def test_identity_weights_match_bilinear_and_shape():
    # Behavior: GridIdentity.weights routes through bilinear_weights; field_shape is (ny,nx).
    # Bug caught: a weights() that diverges from bilinear_weights would make the
    #   refactored operator disagree with the Phase-3 hardcoded path.
    g = _grid()
    proj = GridIdentityProjection(g)
    pts = np.array([[2.5, 3.5, 0.0], [4.0, 4.0, 0.0]])
    assert (proj.weights(pts) - bilinear_weights(g, pts)).nnz == 0
    assert proj.field_shape() == g.shape
    assert proj.node_points(0.0).shape[0] == g.shape[0] * g.shape[1]


def test_bilinear_projection_field_shape_is_query_count():
    # Behavior: an off-grid projection's field_shape is the number of query points.
    g = _grid()
    pts = np.array([[1.1, 2.2, 0.0], [3.3, 4.4, 0.0], [5.5, 6.6, 0.0]])
    assert BilinearProjection(g, pts).field_shape() == (3,)


def test_assert_adjacency_delegates_to_grid_check():
    # Behavior: the grid projection's adjacency precondition is the 5-point pattern check.
    # Bug caught: an operator that skipped this would let a too-narrow Q stencil silently
    #   break eval-variance / first-difference cancellation.
    import pytest

    g = _grid()
    bad = sparse.identity(g.shape[0] * g.shape[1], format="csc")  # no neighbour edges
    with pytest.raises(AssertionError):
        GridIdentityProjection(g).assert_adjacency(bad)
```

- [ ] **Step 2: Run to verify it fails** — `pixi run test tests/unit/test_projection.py -v` → FAIL (`cannot import name 'Projection'`).

- [ ] **Step 3: Create `src/sverdrup/core/projection.py`:**

```python
"""The Projection seam: read any field/covariance off a precision (spec §5.1, Phase-4).

A Projection abstracts the linear map ``W`` (node space -> query points) and the
node-space description, so the GMRF operator and the persisted form are
discretization-agnostic: the same hooks serve a regular grid (GridIdentity/Bilinear)
and, in Stage C, an FEM mesh (FEMBasis). ``A`` (node -> obs) is the same projection
evaluated at obs points.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from scipy import sparse  # type: ignore[import-untyped]

from sverdrup.core.types import Points


@runtime_checkable
class Projection(Protocol):
    """Node space + the ``W`` map to query points, plus the read-off precondition."""

    node_space: object

    def weights(self, pts: Points) -> sparse.csr_matrix:
        """Return the sparse ``(k, n_nodes)`` map from precision nodes to ``pts``."""
        ...

    def field_shape(self) -> tuple[int, ...]:
        """Return the field shape: ``(ny, nx)`` for a grid, ``(n_nodes,)`` for a mesh."""
        ...

    def node_points(self, time_days: float) -> Points:
        """Return the ``(n_nodes, 3)`` coordinates of the precision nodes."""
        ...

    def assert_adjacency(self, q: sparse.spmatrix) -> None:
        """Raise if ``q``'s pattern lacks the entries the read-off/derived ops need."""
        ...
```

- [ ] **Step 4: Add protocol methods to the dataclasses** in `src/sverdrup/methods/gmrf_grid.py` (keep `.matrix`). Replace the two dataclass bodies (lines ~142-166):

```python
@dataclass(frozen=True)
class GridIdentityProjection:
    """The gridded node projection: ``W = bilinear`` (identity on nodes); ``(ny,nx)`` fields."""

    grid: GridSpec

    @property
    def node_space(self) -> GridSpec:
        """Return the node layout (the grid)."""
        return self.grid

    @property
    def matrix(self) -> sparse.csr_matrix:
        """Return the ``(n, n)`` identity projection over the grid nodes (legacy hook)."""
        n = self.grid.shape[0] * self.grid.shape[1]
        return sparse.identity(n, format="csr")

    def weights(self, pts: Points) -> sparse.csr_matrix:
        """Return the bilinear ``W`` to ``pts`` (a unit selector on nodes ⇒ identity there)."""
        return bilinear_weights(self.grid, pts)

    def field_shape(self) -> tuple[int, ...]:
        """Return ``(ny, nx)``."""
        return self.grid.shape

    def node_points(self, time_days: float) -> Points:
        """Return the grid node coordinates at ``time_days``."""
        return self.grid.points(time_days)

    def assert_adjacency(self, q: sparse.spmatrix) -> None:
        """Delegate to the 5-point-pattern precondition for the grid."""
        from sverdrup.methods.gmrf_linalg import assert_adjacency_in_pattern

        assert_adjacency_in_pattern(q.tocsc(), self.grid.shape)


@dataclass(frozen=True)
class BilinearProjection:
    """The off-grid read-off: bilinear ``W`` from grid nodes to fixed query points."""

    grid: GridSpec
    pts: Points

    @property
    def node_space(self) -> GridSpec:
        """Return the node layout (the grid)."""
        return self.grid

    @property
    def matrix(self) -> sparse.csr_matrix:
        """Return the ``(k, n)`` bilinear projection to ``pts`` (legacy hook)."""
        return bilinear_weights(self.grid, self.pts)

    def weights(self, pts: Points) -> sparse.csr_matrix:
        """Return the bilinear ``W`` to ``pts`` (ignores the stored ``self.pts``)."""
        return bilinear_weights(self.grid, pts)

    def field_shape(self) -> tuple[int, ...]:
        """Return ``(k,)`` — the number of fixed query points."""
        return (self.pts.shape[0],)

    def node_points(self, time_days: float) -> Points:
        """Return the grid node coordinates at ``time_days``."""
        return self.grid.points(time_days)

    def assert_adjacency(self, q: sparse.spmatrix) -> None:
        """Delegate to the 5-point-pattern precondition for the grid."""
        from sverdrup.methods.gmrf_linalg import assert_adjacency_in_pattern

        assert_adjacency_in_pattern(q.tocsc(), self.grid.shape)
```

- [ ] **Step 5: Run** — `pixi run test tests/unit/test_projection.py tests/unit/test_gmrf_grid.py -v` → PASS.

- [ ] **Step 6: Typecheck + commit**

```bash
pixi run typecheck && pixi run pre-commit run --files src/sverdrup/core/projection.py src/sverdrup/methods/gmrf_grid.py tests/unit/test_projection.py
git add src/sverdrup/core/projection.py src/sverdrup/methods/gmrf_grid.py tests/unit/test_projection.py
git commit -m "feat(phase4): Projection seam + grid dataclasses conform (Stage A)"
```

---

## Task 2: Operator consumes the Projection; carries `q_prior`; `_diag` equivalence pinned (C3)

**Goal:** Make `GMRFCovarianceOperator` route every read-off through a held `Projection` (no `bilinear_weights(self.grid,…)`, no `grid.shape`), accept either a `grid` (legacy) or a projection, carry the prior precision `q_prior` for the Stage-B strip draw, and pin the `_diag` fast-path equal to the slow path (C3).

**Files:**
- Modify: `src/sverdrup/methods/gmrf.py` (`GMRFCovarianceOperator`, `MaternGMRF.solve`)
- Test: `tests/unit/test_gmrf_method.py` (add C3 test; existing tests must stay green)

**Acceptance Criteria:**
- [ ] `GMRFCovarianceOperator(projection_or_grid, q_post, time_days, q_prior=None)` — a `GridSpec` first arg is wrapped in `GridIdentityProjection` internally.
- [ ] No `bilinear_weights(self.grid` and no `self.grid.shape` reshape remain in `gmrf.py` (grep-clean).
- [ ] `op.q_post`, `op._factor`, `op.marginal_var/cov/posterior_sample/node_sample` unchanged in behaviour; `op.q_prior` is the prior precision (or None).
- [ ] New C3 test: native-node `op._diag` equals slow-path `diag(W Σ Wᵀ)` through `projection.weights(node_points)`.
- [ ] All existing `tests/unit/test_gmrf_method.py` + `tests/unit/test_gmrf_grid.py` pass.

**Verify:** `pixi run test tests/unit/test_gmrf_method.py tests/unit/test_gmrf_grid.py -v && rg -n "bilinear_weights\(self\.grid|self\.grid\.shape" src/sverdrup/methods/gmrf.py` → tests pass; grep empty.

**Steps:**

- [ ] **Step 1: Write the failing C3 test** — append to `tests/unit/test_gmrf_method.py`:

```python
def test_diag_fastpath_equals_slowpath_on_native_nodes():
    # Behavior (C3): the cached _diag equals diag(W Σ W^T) computed through the
    #   projection's weights() on the native node points — the fast path is the slow path.
    # Bug caught: the projection layer drifting from the cached diagonal, producing a
    #   plausible-but-wrong marginal variance that no other test would notice.
    import numpy as np

    dist = _dist()  # existing helper in this file
    op = dist.cov_op
    nodes = op.projection.node_points(op.time_days)
    w = op.projection.weights(nodes)
    slow = np.asarray((w @ op._sinv @ w.T).diagonal())
    np.testing.assert_allclose(op._diag, slow, rtol=1e-9, atol=1e-12)
```

(If `_dist()` is not already at module scope in this file, reuse the existing fixture helper the other tests call — check the top of `test_gmrf_method.py` and use the same constructor.)

- [ ] **Step 2: Run to verify it fails** — `pixi run test tests/unit/test_gmrf_method.py::test_diag_fastpath_equals_slowpath_on_native_nodes -v` → FAIL (`op` has no attribute `projection`).

- [ ] **Step 3: Refactor `GMRFCovarianceOperator`** in `src/sverdrup/methods/gmrf.py`:

```python
class GMRFCovarianceOperator:
    """EXACT posterior covariance of a GMRF, backed by one sparse factor; projection-driven."""

    fidelity = CovFidelity.EXACT
    representation = "sparse-precision"

    def __init__(
        self,
        projection_or_grid: object,
        q_post: sparse.csc_matrix,
        time_days: float,
        q_prior: sparse.csc_matrix | None = None,
    ) -> None:
        """Cache the posterior precision + factor; hold a Projection; verify adjacency.

        Args:
            projection_or_grid: A ``Projection`` the read-off routes through, OR a
                legacy ``GridSpec`` (wrapped in ``GridIdentityProjection``).
            q_post: Posterior precision (CSC).
            time_days: Output time.
            q_prior: Prior precision (CSC), persisted for the Stage-B strip-prior draw.
        """
        from sverdrup.core.grid import GridSpec
        from sverdrup.methods.gmrf_grid import GridIdentityProjection

        proj = (
            GridIdentityProjection(projection_or_grid)
            if isinstance(projection_or_grid, GridSpec)
            else projection_or_grid
        )
        self.projection = cast("Projection", proj)
        self.projection.assert_adjacency(q_post)
        self.grid = getattr(self.projection, "grid", self.projection.node_space)
        self.q_post = q_post
        self.q_prior = q_prior
        self.time_days = time_days
        self._factor = GMRFFactor(q_post)
        self._sinv = self._factor.selective_inverse()
        self._diag = np.asarray(self._sinv.diagonal())

    def _is_native_nodes(self, a: Points) -> bool:
        """True if ``a`` matches the precision node points (the identity fast path)."""
        nodes = self.projection.node_points(self.time_days)
        return a.shape[0] == nodes.shape[0] and np.allclose(a[:, :2], nodes[:, :2])

    def marginal_var(self, a: Points) -> np.ndarray:
        """Return exact marginal variance: cached ``diag`` on native nodes, else ``diag(W Σ Wᵀ)``."""
        if self._is_native_nodes(a):
            return self._diag
        w = self.projection.weights(a)
        return np.asarray((w @ self._sinv @ w.T).diagonal())

    def cov(self, a: Points, b: Points) -> np.ndarray:
        """Return ``W_a Σ W_b^T`` using selective-inverse entries."""
        wa = self.projection.weights(a)
        wb = self.projection.weights(b)
        return np.asarray((wa @ self._sinv @ wb.T).toarray())

    def posterior_sample(self, s: Points, seed: Seed, m: int) -> np.ndarray:
        """Return ``m`` zero-mean draws ``W (L^-T w)`` at ``s`` (node draw, projected)."""
        rng = np.random.default_rng(seed)
        n = self.q_post.shape[0]
        node_draws = np.stack(
            [self._factor.sample(rng.standard_normal(n)) for _ in range(m)]
        )
        if self._is_native_nodes(s):
            return node_draws
        w = self.projection.weights(s)
        return np.asarray((w @ node_draws.T).T)

    def node_sample(self, w_white: np.ndarray) -> np.ndarray:
        """Return one node-space draw ``L^-T w`` from external white noise."""
        return self._factor.sample(w_white)
```

Add to the imports at the top of `gmrf.py`: `from typing import TYPE_CHECKING, cast` and, under `if TYPE_CHECKING:`, `from sverdrup.core.projection import Projection`. Remove the now-unused `bilinear_weights` import only if no longer referenced in this file *after* Step 4 (it is still used in `MaternGMRF.solve` for `A`, so keep it but route it through the projection per Step 4).

- [ ] **Step 4: Update `MaternGMRF.solve`** to build the projection, route `A` through it, pass `q_prior`, and reshape via `field_shape`. Change these lines:

```python
        q_prior = matern_precision(grid, kappa, tau)

        from sverdrup.methods.gmrf_grid import GridIdentityProjection

        projection = GridIdentityProjection(grid)
        a_op = projection.weights(obs.coords())  # (n_obs, n_nodes): node -> obs
        r_diag = np.diag(obs.error_model.as_matrix(len(obs))).astype(float)
        dt = np.abs(obs.coords()[:, 2] - time_days)
        r_inflated = r_diag * np.exp(dt / max(taper, 1e-9))
        r_inv = sparse.diags(1.0 / r_inflated)

        q_post = (q_prior + a_op.T @ r_inv @ a_op).tocsc()
        op = GMRFCovarianceOperator(projection, q_post, time_days, q_prior=q_prior)
        rhs = a_op.T @ (r_inv @ obs.values())
        mean = op._factor.solve(np.asarray(rhs)).reshape(projection.field_shape())
```

- [ ] **Step 5: Run** — `pixi run test tests/unit/test_gmrf_method.py tests/unit/test_gmrf_grid.py tests/unit/test_nonstationary_kappa.py -v` → PASS; then `rg -n "bilinear_weights\(self\.grid|self\.grid\.shape" src/sverdrup/methods/gmrf.py` → empty.

- [ ] **Step 6: Typecheck + commit**

```bash
pixi run typecheck && pixi run pre-commit run --files src/sverdrup/methods/gmrf.py tests/unit/test_gmrf_method.py
git add src/sverdrup/methods/gmrf.py tests/unit/test_gmrf_method.py
git commit -m "feat(phase4): operator consumes Projection, carries q_prior; pin _diag equivalence (C3)"
```

---

## Task 3: De-grid the persisted form + reduction + solve threading

**Goal:** Make `PrecisionFields`/`PrecisionDistribution` carry a `Projection` and the prior precision, route `covariance`/`sample` through `projection.weights`/`field_shape` (no `bilinear_weights(self.grid,…)`, no `(ny,nx)`), keep the `grid`-first positional constructor (so Phase-3 tests stay green), and thread the projection through `GMRFPrecisionReduction` and `solve.py`.

**Files:**
- Modify: `src/sverdrup/distributions/persisted.py` (`PrecisionFields`, `PrecisionDistribution`)
- Modify: `src/sverdrup/distributions/reduction.py` (`GMRFPrecisionReduction.reduce`)
- Modify: `src/sverdrup/application/solve.py` (thread projection if needed)
- Test: `tests/unit/test_precision_distribution.py` (add de-grid test; existing green)

**Acceptance Criteria:**
- [ ] `PrecisionFields` gains `projection: object | None = None` and `prior_precision: object | None = None` (both defaulted last → positional/kwarg Phase-3 constructions unaffected).
- [ ] `PrecisionDistribution.__post_init__` resolves `self._projection = fields.projection or GridIdentityProjection(self.grid)`; `covariance`/`sample` route through it; no `bilinear_weights(self.grid` and no `self.grid.shape` reshape remain in `PrecisionDistribution`.
- [ ] `GMRFPrecisionReduction.reduce` stores `projection=op.projection`, `prior_precision=op.q_prior`, and uses `op.projection.weights(eval_points)` for the eval mean.
- [ ] `pd.fields.prior_precision is dist.cov_op.q_prior` after reduction.
- [ ] All of `tests/unit/test_precision_distribution.py`, `test_reduction.py`, `test_gmrf_blend.py`, `test_gmrf_kriging_{driver,oracle}.py` pass.

**Verify:** `pixi run test tests/unit/test_precision_distribution.py tests/unit/test_reduction.py tests/test_gmrf_blend.py tests/unit/test_gmrf_kriging_driver.py tests/unit/test_gmrf_kriging_oracle.py -v && rg -n "bilinear_weights\(self\.grid|self\.grid\.shape" src/sverdrup/distributions/persisted.py` → tests pass; grep empty.

**Steps:**

- [ ] **Step 1: Write the failing de-grid test** — append to `tests/unit/test_precision_distribution.py`:

```python
def test_precision_distribution_routes_cov_through_projection_and_carries_prior():
    # Behavior: covariance goes through the held projection (not bilinear_weights(self.grid)),
    #   and the persisted form carries the prior precision for the Stage-B strip draw.
    # Bug caught: a grid-hardcoded read-off (invariant 2) or a dropped prior (Stage B can't
    #   assemble the strip sub-GMRF).
    import numpy as np

    dist = _dist()
    pts = _grid().points(2.0)
    unit = GMRFPrecisionReduction().reduce(dist, pts, None, rank=0, seed=1)
    pd = PrecisionDistribution(
        _grid(), cast(PrecisionFields, unit.base_fields), dist.provenance, 2.0
    )
    assert pd.fields.prior_precision is dist.cov_op.q_prior
    a = np.array([[2.5, 3.5, 2.0]])
    cov_proj = pd._projection.weights(a) @ pd._factor_obj().selective_inverse() @ pd._projection.weights(a).T
    np.testing.assert_allclose(pd.covariance(a, a), cov_proj.toarray(), rtol=1e-9)
```

- [ ] **Step 2: Run to verify it fails** — FAIL (`prior_precision` / `_projection` absent).

- [ ] **Step 3: Update `PrecisionFields`** (`persisted.py`) — append two defaulted fields:

```python
@dataclass(frozen=True)
class PrecisionFields:
    """Storable sufficient stats for a sparse-precision (GMRF) generator — first-class."""

    mean: Field
    precision: object  # scipy.sparse CSC posterior precision over the nodes
    permutation: np.ndarray
    marginal_variance: Field  # exact, from selective inversion
    seed: Seed
    sampler_spec: str = "sparse-precision"
    projection: object | None = None  # Projection over the node space (None -> grid identity)
    prior_precision: object | None = None  # CSC prior Q, for the Stage-B strip-prior draw
```

- [ ] **Step 4: Update `PrecisionDistribution`** (`persisted.py`) — resolve the projection and route through it:

```python
    def __post_init__(self) -> None:
        """Cache a factor lazily; resolve the held projection (grid identity by default)."""
        self._factor: object | None = None
        proj = self.fields.projection
        if proj is None:
            from sverdrup.methods.gmrf_grid import GridIdentityProjection

            proj = GridIdentityProjection(cast(Any, self.grid))
        self._projection = cast("Projection", proj)

    def marginal_variance(self) -> Field:
        """Return the stored exact marginal-variance field."""
        return self.fields.marginal_variance

    def covariance(self, a: Points, b: Points) -> np.ndarray:
        """Return ``W_a Σ W_b^T`` from the cached factor's selective inverse (via the projection)."""
        sinv = self._factor_obj().selective_inverse()
        wa = self._projection.weights(a)
        wb = self._projection.weights(b)
        return np.asarray((wa @ sinv @ wb.T).toarray())

    def sample(self, m: int, seed: Seed) -> np.ndarray:
        """Return ``m`` field draws ``mean + L^-T w`` in the projection's field shape."""
        rng = np.random.default_rng(seed)
        fac = self._factor_obj()
        n = cast(Any, self.fields.precision).shape[0]
        draws = np.stack([fac.sample(rng.standard_normal(n)) for _ in range(m)])
        shape = self._projection.field_shape()
        return np.asarray(self.fields.mean[None, ...] + draws.reshape(m, *shape))
```

Add `from sverdrup.core.projection import Projection` under the file's `TYPE_CHECKING` block. Remove the now-dead `from sverdrup.methods.gmrf_grid import bilinear_weights` import inside `covariance` (it was a local import at line 314).

Note on `sample`: `self.fields.mean[None, ...]` + `reshape(m, *shape)` works for both `(ny,nx)` (grid) and `(n_nodes,)` (mesh, Stage C), replacing the hardcoded `ny, nx = self.grid.shape`.

- [ ] **Step 5: Update `GMRFPrecisionReduction.reduce`** (`reduction.py`) — carry projection + prior, route eval mean through the projection:

```python
    def reduce(
        self,
        dist: object,
        grid_points: np.ndarray,
        eval_points: np.ndarray | None,
        *,
        rank: int,
        seed: int,
    ) -> ReducedUnit:
        """Persist the sparse precision + permutation + projection + prior + exact var."""
        from sverdrup.distributions.persisted import PrecisionFields

        d = cast(Any, dist)
        op = d.cov_op
        base = PrecisionFields(
            mean=d.mean,
            precision=op.q_post,
            permutation=op._factor.permutation,
            marginal_variance=op.marginal_var(grid_points).reshape(
                op.projection.field_shape()
            ),
            seed=seed,
            projection=op.projection,
            prior_precision=op.q_prior,
        )
        if eval_points is None:
            return ReducedUnit(base, None)
        mean = np.asarray(op.projection.weights(eval_points) @ d.mean.ravel())
        var = op.marginal_var(eval_points)
        return ReducedUnit(
            base, EvalPointPredictions(eval_points, mean, var, samples=None)
        )
```

Remove the local `from sverdrup.methods.gmrf_grid import bilinear_weights` import in this method.

- [ ] **Step 6: Verify `solve.py` needs no change** — `solve.py:60` does `PrecisionDistribution(uow.grid, base_fields, dist.provenance, t)`; `base_fields.projection` now carries the operator's projection, so `__post_init__` picks it up. No change required (confirm by running `tests/integration/test_solve_unit.py`).

- [ ] **Step 7: Run** — `pixi run test tests/unit/test_precision_distribution.py tests/unit/test_reduction.py tests/test_gmrf_blend.py tests/unit/test_gmrf_kriging_driver.py tests/unit/test_gmrf_kriging_oracle.py tests/integration/test_solve_unit.py -v` → PASS; grep clean.

- [ ] **Step 8: Typecheck + commit**

```bash
pixi run typecheck && pixi run pre-commit run --files src/sverdrup/distributions/persisted.py src/sverdrup/distributions/reduction.py tests/unit/test_precision_distribution.py
git add src/sverdrup/distributions/persisted.py src/sverdrup/distributions/reduction.py tests/unit/test_precision_distribution.py
git commit -m "feat(phase4): de-grid persisted form; carry projection + prior precision (Stage A)"
```

---

## Task 4: STAGE-A GATE — full Phase-3 suite reproduces exactly

**Goal:** Prove the generalization changed no behavior: the entire Phase-3 suite is green, the OI + grid-GMRF blend results are byte-identical, and the operator/persisted form hold no hardcoded read-off.

> **USER-ORDERED GATE — NON-SKIPPABLE.** This task was requested by the user in the current conversation. It MUST NOT be closed by walking around it, by declaring it "verified inline", or by substituting a cheaper check. Close only after every item in `acceptanceCriteria` has been re-validated independently, with output captured.

**Files:**
- Test: none new (regression gate over the existing suite)

**Acceptance Criteria:**
- [ ] `pixi run test` reports **0 failed** (≥ 178 passed / 2 skipped — the count only grows by the new Stage-A tests).
- [ ] `pixi run typecheck` and `pixi run lint` clean.
- [ ] `rg -n "bilinear_weights\(self\.grid|self\.grid\.shape" src/sverdrup/methods/gmrf.py src/sverdrup/distributions/persisted.py` → empty (invariant 2).
- [ ] Zero Phase-3 test files modified in Stage A (Tasks 1–3 only ADDED tests). `git diff --stat 31a58c6 -- tests/` shows only new files under `tests/unit/test_projection.py` and appended tests in `test_gmrf_method.py` / `test_precision_distribution.py` — no deletions or assertion edits.
- [ ] A red anywhere = the generalization changed behavior → surface it, do NOT loosen the test (invariant 1).

**Verify:** `pixi run test 2>&1 | tail -5 && pixi run typecheck && pixi run lint` → 0 failed, clean.

**Steps:**

- [ ] **Step 1: Run the full suite, capture the tail**

```bash
pixi run test 2>&1 | tail -8
```
Expected: `... 178 passed, 2 skipped ...` (or higher passed count; 0 failed).

- [ ] **Step 2: Run typecheck + lint**

```bash
pixi run typecheck && pixi run lint
```
Expected: no errors.

- [ ] **Step 3: Grep the invariant-2 cleanliness + Phase-3 test untouchedness**

```bash
rg -n "bilinear_weights\(self\.grid|self\.grid\.shape" src/sverdrup/methods/gmrf.py src/sverdrup/distributions/persisted.py
git diff --stat 31a58c6 -- tests/
```
Expected: first command empty; the diff shows only additions (new file + appended tests), no edits to existing assertions.

- [ ] **Step 4: Record gate evidence + commit a PROGRESS note**

Update `PROGRESS.md` "next action" to "Stage B Task 5". Commit:
```bash
git add PROGRESS.md
git commit -m "chore(phase4): Stage-A gate PASSED — Phase-3 suite reproduces exactly"
```

---

# STAGE B — non-chain coherent sampler, on the grid

## Task 5: `_strip_network` — strip nodes + induced Q-subgraph (C1, C6)

**Goal:** Add a topology-agnostic builder that returns the union of all tile-overlap nodes AND the induced connectivity over them (every prior-Q edge with both endpoints in the strip set, corners included), with a loud assertion that adjacent tiles actually share strip nodes (C6).

**Files:**
- Modify: `src/sverdrup/distributions/coherent.py` (add `_strip_network`, helpers)
- Test: `tests/unit/test_strip_network.py` (new)

**Acceptance Criteria:**
- [ ] `_strip_network(parts)` returns `(global_keys, per_tile)` where `global_keys` is the ordered list of unique strip-node `(lon,lat)` keys and `per_tile[i]` maps each global strip index to tile-`i`'s local node index (or -1 if absent).
- [ ] A 2×2 partition with a shared interior corner yields ≥1 global strip node present in ≥3 tiles (the junction node).
- [ ] Adjacent tiles with a real overlap produce a non-empty shared key set; a degenerate (disjoint) pair raises `AssertionError` (C6 — silent-empty-conditioning is a loud red).

**Verify:** `pixi run test tests/unit/test_strip_network.py -v` → pass.

**Steps:**

- [ ] **Step 1: Write the failing test** — `tests/unit/test_strip_network.py`:

```python
"""The strip-network: union strip nodes + induced connectivity; corner is multiply-covered."""

from __future__ import annotations

import numpy as np
import pytest

from sverdrup.distributions.coherent import _strip_network
from tests.unit._strip_fixtures import four_tile_corner_parts, disjoint_pair_parts


def test_corner_node_is_covered_by_at_least_three_tiles():
    # Behavior (C1/C6): in a 2x2 partition the interior corner node belongs to >=3 tiles,
    #   so the induced strip graph must connect across the junction, not treat strips as
    #   independent ribbons.
    # Bug caught: assembling the strip prior per-overlap drops the corner's cross-strip edges.
    parts = four_tile_corner_parts()
    global_keys, per_tile = _strip_network(parts)
    coverage = np.array([sum(pt.get(g, -1) >= 0 for pt in per_tile) for g in range(len(global_keys))])
    assert coverage.max() >= 3  # the interior corner


def test_disjoint_tiles_raise_loudly():
    # Behavior (C6): adjacent tiles that share no node must fail loudly, never silently
    #   produce an empty conditioning set.
    parts = disjoint_pair_parts()
    with pytest.raises(AssertionError, match="share no strip node"):
        _strip_network(parts)
```

Create `tests/unit/_strip_fixtures.py` building real `BlendInput` parts (reuse the constructors from `tests/test_gmrf_blend.py` / `tests/unit/test_gmrf_kriging_driver.py` — distinct obs per tile, `Tile` with `core_window`/`extended_window`). The four-tile fixture tiles a single 10×10 global grid into four 6×6 overlapping quadrants (overlap ≥ 2 columns AND rows, so a shared interior 2×2 corner block exists). The disjoint fixture places two tiles with non-touching extended windows.

```python
"""Shared Stage-B fixtures: a 2x2 overlapping partition of one global grid + a disjoint pair."""

from __future__ import annotations

import numpy as np

from sverdrup.core.geometry import Window
from sverdrup.core.grid import GridSpec
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
from sverdrup.core.tiling import Tile  # adjust import to the real Tile location
from sverdrup.distributions.blend import BlendInput
from sverdrup.distributions.reduction import GMRFPrecisionReduction
from sverdrup.distributions.persisted import PrecisionDistribution, PrecisionFields
from sverdrup.methods.gmrf import MaternGMRF
from sverdrup.methods.parameters import ConstantProvider  # adjust to real provider import
from typing import cast


def _tile_part(x0, x1, y0, y1, obsval, core, ext):
    grid = GridSpec(x=np.arange(x0, x1), y=np.arange(y0, y1), crs="EPSG:4326")
    obs = ObsWindow.from_arrays(
        np.array([float((x0 + x1) / 2)]),
        np.array([float((y0 + y1) / 2)]),
        np.array([2.0]),
        np.array([obsval]),
        DiagonalErrorModel(np.array([1e-3])),
    )
    P = ConstantProvider({"range": 6.0, "variance": 0.2, "temporal_taper_scale": 10.0})
    dist = MaternGMRF().solve(obs, grid, P, 2.0)
    unit = GMRFPrecisionReduction().reduce(dist, grid.points(2.0), None, rank=0, seed=3)
    pd = PrecisionDistribution(grid, cast(PrecisionFields, unit.base_fields), dist.provenance, 2.0)
    tile = Tile(Window(core, (0, 1), (0, 0)), Window(ext, (0, 1), (0, 0)), grid)
    return BlendInput(pd, tile)


def four_tile_corner_parts():
    # one global 0..9 grid split into four 0..5 / 4..9 overlapping quadrants (overlap cols 4,5)
    return [
        _tile_part(0, 6, 0, 6, 1.0, (0.0, 5.0), (0.0, 5.0)),
        _tile_part(4, 10, 0, 6, 2.0, (4.0, 9.0), (0.0, 5.0)),
        _tile_part(0, 6, 4, 10, 3.0, (0.0, 5.0), (4.0, 9.0)),
        _tile_part(4, 10, 4, 10, 4.0, (4.0, 9.0), (4.0, 9.0)),
    ]


def disjoint_pair_parts():
    return [
        _tile_part(0, 4, 0, 4, 1.0, (0.0, 3.0), (0.0, 3.0)),
        _tile_part(6, 10, 6, 10, 2.0, (6.0, 9.0), (6.0, 9.0)),
    ]
```

(When implementing, confirm the real import paths for `Tile`, `Window`, and the constant provider by grepping — the design intentionally reuses the existing fixtures; adjust the three flagged imports to match.)

- [ ] **Step 2: Run to verify it fails** — FAIL (`_strip_network` undefined).

- [ ] **Step 3: Implement `_strip_network`** in `coherent.py`:

```python
def _strip_network(
    parts: Sequence[Any],
) -> tuple[list[tuple[float, float]], list[dict[int, int]]]:
    """Return the union strip-node keys and per-tile {global_idx -> local node idx}.

    A strip node of tile ``i`` is a node of tile ``i`` that falls inside ANOTHER tile's
    extended window (an overlap node). The returned ``global_keys`` is the ordered set of
    unique ``(lon,lat)`` keys over all tiles; ``per_tile[i][g]`` is tile ``i``'s local node
    index for global strip node ``g`` (absent if tile ``i`` does not contain it). Corner
    nodes shared by >=3 tiles appear once in ``global_keys`` and in every covering tile's map
    — so the induced connectivity assembled in ``_draw_joint`` spans the junction (C1).

    Raises:
        AssertionError: if any pair of tiles whose extended windows overlap shares no strip
            node (C6 — silent-empty-conditioning must be a loud red).
    """
    t = cast(Any, parts[0].distribution).time_days
    tile_keys = []
    tile_pts = []
    for p in parts:
        gpts = _support_points(p.distribution.grid, t)
        tile_pts.append(gpts)
        tile_keys.append(_node_keys(gpts))

    # strip nodes: tile-i nodes inside any other tile's extended window
    strip_local: list[set[int]] = [set() for _ in parts]
    for i, p_i in enumerate(parts):
        for j, p_j in enumerate(parts):
            if i == j:
                continue
            win_j = p_j.tile.extended_window
            for n, pt in enumerate(tile_pts[i]):
                if _in_window(pt, win_j):
                    strip_local[i].add(n)

    global_index: dict[tuple[float, float], int] = {}
    global_keys: list[tuple[float, float]] = []
    per_tile: list[dict[int, int]] = [dict() for _ in parts]
    for i in range(len(parts)):
        for n in sorted(strip_local[i]):
            key = tile_keys[i][n]
            g = global_index.get(key)
            if g is None:
                g = len(global_keys)
                global_index[key] = g
                global_keys.append(key)
            per_tile[i][g] = n

    # C6: adjacent (extended-window-overlapping) tiles must share at least one strip node
    for i in range(len(parts)):
        for j in range(i + 1, len(parts)):
            wi, wj = parts[i].tile.extended_window, parts[j].tile.extended_window
            overlap = (
                wi.lon_range[0] <= wj.lon_range[1]
                and wj.lon_range[0] <= wi.lon_range[1]
                and wi.lat_range[0] <= wj.lat_range[1]
                and wj.lat_range[0] <= wi.lat_range[1]
            )
            if overlap:
                shared = set(per_tile[i]) & set(per_tile[j])
                if not shared:
                    raise AssertionError(
                        f"tiles {i},{j} overlap but share no strip node — "
                        "conditioning set would be silently empty (C6)"
                    )
    return global_keys, per_tile
```

- [ ] **Step 4: Run** — `pixi run test tests/unit/test_strip_network.py -v` → PASS.

- [ ] **Step 5: Typecheck + commit**

```bash
pixi run typecheck && pixi run pre-commit run --files src/sverdrup/distributions/coherent.py tests/unit/test_strip_network.py tests/unit/_strip_fixtures.py
git add src/sverdrup/distributions/coherent.py tests/unit/test_strip_network.py tests/unit/_strip_fixtures.py
git commit -m "feat(phase4): topology-agnostic strip-network with induced connectivity (C1, C6)"
```

---

## Task 6: Tile-adjacency graph + max-overlap spanning tree (replaces the synthesized strip field)

**Goal:** Replace the disproved synthesized-field machinery with the topology object the spanning-tree
sampler needs: the tile-adjacency graph (edge weight = shared-node count), its max-overlap spanning
tree (parent map + sweep order), and the dropped-edge set — with a per-tree-edge separation assert.

> **DESIGN PIVOT (owner-confirmed).** The spec-literal `_draw_joint`/`_strip_prior` synthesized strip
> field was disproved by measurement (376× cross-seam, joint-cov rel-err 1.617; jitter is a cover-up;
> no coarse space; intrinsic near-singular `Σ_ss`). See PROGRESS "Cross-cutting decisions (Phase 4) —
> Stage-B sampler = spanning-tree hand-forward". `_strip_network` is **kept** (it computes shared-node
> sets); `_draw_joint`, `_strip_prior`, `_interiorness` and `tests/unit/test_draw_joint.py` are
> **removed**.

**Files:**
- Modify: `src/sverdrup/distributions/coherent.py` (remove `_draw_joint`/`_strip_prior`/`_interiorness`;
  add `_tile_adjacency`, `_max_overlap_spanning_tree`, `_assert_tree_edge_separates`)
- Remove: `tests/unit/test_draw_joint.py`
- Test: `tests/unit/test_spanning_tree.py` (new)

**Acceptance Criteria:**
- [ ] `_tile_adjacency(parts) -> dict[tuple[int,int], set[key]]` returns, for every tile pair whose
  `extended_window`s overlap, the shared strip-node key set (reusing `_strip_network`'s shared-node
  logic). Pairs sharing `< STENCIL_REACH` distinct nodes per adjacency axis are **not** edges.
- [ ] `_max_overlap_spanning_tree(adjacency, n) -> (parent: dict[int,int|None], order: list[int],
  tree_edges: set, dropped: list)`: a maximum-weight spanning tree by shared-node count (Kruskal/Prim),
  rooted, BFS order, with `dropped` = real overlap edges not in the tree.
- [ ] Disconnected adjacency (a tile reachable by no edge ≥ reach) raises `AssertionError` (C6 — a tile
  that cannot be hand-forward-conditioned is a loud red, never silently independent).
- [ ] `_assert_tree_edge_separates` raises if any **tree** edge's shared strip is thinner than
  `STENCIL_REACH` in the adjacency direction (per-tree-edge analogue of `_assert_separates`).
- [ ] On the 2×2 corner fixture: tree has exactly `n-1 = 3` edges; `dropped` is non-empty; the chosen
  tree maximizes total shared-node weight (a higher-overlap edge is never dropped in favour of a
  lower-overlap tree edge).

**Verify:** `pixi run test tests/unit/test_spanning_tree.py -v` → pass.

**Steps:**
- [ ] **Step 1: Remove** `_draw_joint`, `_strip_prior`, `_interiorness` from `coherent.py` and delete
  `tests/unit/test_draw_joint.py`. Keep `_strip_network` (it is now the shared-node primitive).
- [ ] **Step 2: Write the failing test** `tests/unit/test_spanning_tree.py`: a 2×2 fixture asserts
  3 tree edges + ≥1 dropped + max-overlap optimality; `disjoint_pair_parts` raises (disconnected);
  a deliberately thin-overlap pair as a forced tree edge raises via `_assert_tree_edge_separates`.
- [ ] **Step 3: Implement** `_tile_adjacency` (shared-node sets via `_strip_network` per pair, filtered
  by `≥ STENCIL_REACH` per axis), `_max_overlap_spanning_tree` (max-weight ST + connectivity assert),
  `_assert_tree_edge_separates`.
- [ ] **Step 4: Run → green. Step 5: typecheck + pre-commit + commit**
  `feat(phase4): tile-adjacency graph + max-overlap spanning tree (Stage B redesign)`.

---

## Task 7: `GmrfTreeKrigingSolve` — spanning-tree hand-forward; repoint the registry

**Goal:** Implement the topology-agnostic-in-correctness driver: generalize the proven chain
`GmrfKrigingSolve._sweep` (line) to a **max-overlap spanning tree** — each tile draws its independent
unconditional posterior sample and is hand-forward-conditioned on its **parent's** already-drawn
overlap **values** (consistent residual ⇒ the 4e8 `Σ_ss` singularity is never excited). Re-point
`_DRIVERS["sparse-precision"]`; keep `GmrfKrigingSolve` (chain) as the 1-D regression.

**Files:**
- Modify: `src/sverdrup/distributions/coherent.py` (`GmrfTreeKrigingSolve`, `_DRIVERS`)
- Modify: `tests/test_gmrf_blend.py` (the one wiring assertion — the only pre-existing assertion changed)
- Test: `tests/unit/test_tree_kriging_driver.py` (new)

**Acceptance Criteria:**
- [ ] `GmrfTreeKrigingSolve._sweep_tree(parts, t, member, noise) -> list[field]`: build adjacency →
  max-overlap ST → BFS order; per tile, independent white keyed `gmrf-tile:{i}×member`; root drawn
  unconditionally; each child kriged toward its parent's drawn values on the shared nodes via
  `x_c = x_u + cols @ solve(Σ_ss, x_parent|_S − x_u|_S)`, `cols = posterior_cov_columns(s_idx)`.
- [ ] Independent-white discipline: **two** streams only (tile-white ⟂ tile-white). The synthesized
  joint-white stream is gone (C2 reverts to the Phase-3 two-stream contract).
- [ ] `_DRIVERS["sparse-precision"] is GmrfTreeKrigingSolve`; on a **single tile** the member reduces
  to `mean + L⁻ᵀw` (no parent ⇒ no-op), bit-identical to the chain's single-tile result.
- [ ] `GmrfKrigingSolve` unchanged; `tests/unit/test_gmrf_kriging_{driver,oracle}.py` stay green
  untouched (they instantiate the chain directly via `._sweep`). **Note:** the 3 oracle tests that
  route through `BlendOperator().blend()` move to the new driver — addressed in Task 8 by rebuilding
  their fixtures as real solved tiles (the hand-stubbed `prior_precision=None` synthetic tiles were
  always going to rot) and treating the 2 chain-gate blend tests as the Stage-B gate that moves with
  the cross-seam number (see Task 9), not as independent repairs.
- [ ] `tests/test_gmrf_blend.py::test_select_driver_sparse_precision` asserts the new class (the ONLY
  pre-existing assertion changed in Phase 4).

**Verify:** `pixi run test tests/unit/test_tree_kriging_driver.py tests/unit/test_gmrf_kriging_driver.py
tests/unit/test_gmrf_kriging_oracle.py tests/test_gmrf_blend.py -v` → all pass (oracle/blend fixtures
rebuilt in Task 8 land here too; sequence Task 8 fixtures before re-running if needed).

**Steps:**
- [ ] **Step 1:** failing test `test_tree_kriging_driver.py` — registry points to `GmrfTreeKrigingSolve`;
  2×2 member is finite + full-length; single-tile == `mean + L⁻ᵀw`.
- [ ] **Step 2:** implement `GmrfTreeKrigingSolve` (sweep over the ST, hand-forward parent values).
- [ ] **Step 3:** repoint `_DRIVERS`; update the one wiring assertion.
- [ ] **Step 4: Run → green. Step 5: typecheck + pre-commit + commit**
  `feat(phase4): GmrfTreeKrigingSolve spanning-tree hand-forward; repoint registry (Stage B)`.

---

## Task 8: Stage-B oracles — tree-edge exactness, dropped-edge bound, conservative direction, two-tree invariance

**Goal:** Pin the construction's contracts before the gate, with thresholds derived from the **measured
chain baseline** (not constants): per-tile full-cov exactness; tree-edge ≤ chain baseline; dropped-edge
bounded relative to tree-edge; conservative-direction (non-under-dispersion); two-tree invariance;
thin-tree-edge loud red. Rebuild the 3 blend-routed oracle fixtures as **real solved tiles**.

**Files:**
- Modify: `tests/unit/test_gmrf_kriging_oracle.py` (rebuild the 3 blend-routed fixtures as real
  `MaternGMRF` solved tiles so `prior_precision`/`q_post` exist; the chain `._sweep` per-tile oracle
  stays as-is)
- Test: `tests/unit/test_tree_kriging_oracle.py` (new)
- Modify: `src/sverdrup/distributions/coherent.py` if a residual-recording hook is needed

**Acceptance Criteria:**
- [ ] **Per-tile full-cov:** a single tile's corrected-draw empirical covariance == its exact posterior
  `(Qⁱ)⁻¹` within MC tol (kriging toward the parent does not distort the tile's own law).
- [ ] **Two-stream independence (C2):** tile-white ⟂ tile-white (distinct seeds; empirical
  cross-correlation ≈ 0 at MC floor). No joint-white stream exists.
- [ ] **Tree-edge parity:** on the 2×2 fixture, `max_tree_edge_joint_cov_relerr ≤ chain_baseline·(1+slack)`
  where `chain_baseline` is **measured in-test** from the 1-D 3-tile chain on the same fixture
  (≈0.30 on natl60-scale; do not hardcode — compute it).
- [ ] **Dropped-edge relative bound:** `max_dropped_edge_relerr ≤ C · max_tree_edge_relerr`, `C ∈ [2,3]`.
- [ ] **Conservative direction:** cross-seam derived-quantity (firstdifference) variance ratio
  (blend/single-tile-reference) on dropped edges `≥ 1 − ε` (never under-dispersed; over-dispersion OK).
- [ ] **Two-tree invariance:** the shipped blend joint-cov rel-err is within tolerance under the MST AND
  one alternative valid spanning tree (correctness tree-invariant; only the residual distribution moves).
- [ ] **Thin tree edge:** forcing a sub-reach overlap as a tree edge raises loudly (`_assert_tree_edge_separates`).

**Verify:** `pixi run test tests/unit/test_tree_kriging_oracle.py tests/unit/test_gmrf_kriging_oracle.py -v` → pass.

**Steps:** Step 1 rebuild the 3 oracle fixtures as real solved tiles; Step 2 write the oracle tests
above (measure chain baseline in-test, assert the relative bounds + direction + invariance); Step 3
run → green; Step 4 typecheck + pre-commit + commit
`test(phase4): Stage-B spanning-tree oracles — tree/dropped/direction/invariance (chain-baseline-derived)`.

---

## Task 9: STAGE-B GATE — spanning-tree sampler on real tiles; three coupled assertions + invariance

**Goal:** Certify the spanning-tree sampler on genuinely-distinct real-solved tiles (2×2 + 3-tile),
with the three coupled gate assertions and the two-tree invariance test, the dropped-edge residual
**recorded** as a conservative `known_bias`; junction-tree escalation only on out-of-tolerance.

> **USER-ORDERED GATE — NON-SKIPPABLE.** Close only after every `acceptanceCriteria` item is
> re-validated independently with captured output. The thresholds are derived from the measured chain
> baseline, never loosened to pass.

**Files:**
- Test: `tests/test_tree_kriging_gate.py` (new) — real natl60-style solved tiles via the pipeline spine
- Modify: `tests/test_gmrf_blend.py` — the 2 cross-seam tests are the Stage-B gate; they move with the
  spanning-tree number (re-baseline against the chain, conservative direction), not independent repairs

**Acceptance Criteria:**
- [ ] **(1) Tree-edge parity:** `max_tree_edge_relerr ≤ chain_baseline·(1+slack)` (chain baseline
  measured in-test ≈0.30; record the actual numbers). Tree edges no worse than the validated chain.
- [ ] **(2) Dropped-edge bound:** `max_dropped_edge_relerr ≤ C·max_tree_edge_relerr`, `C ∈ [2,3]`
  (record actual; the residual is printed and stored as `KnownBias`/provenance `known_bias`).
- [ ] **(3) Conservative direction:** cross-seam firstdifference variance ratio (blend/ref) min `≥ 0.9`
  on tree edges AND `≥ 1−ε` on dropped edges — never the under-dispersed 0.45 the synthesized field gave.
- [ ] **Two-tree invariance:** the shipped blend passes (1)–(3) under MST AND one alternative tree.
- [ ] **Nonstationary-κ:** repeat (1)–(3) with a latitude-varying κ field (conservative, recorded).
- [ ] **Out-of-tolerance ⇒ STOP:** if any residual exceeds tolerance, fail LOUDLY, record the measured
  residual, surface that junction-tree escalation (spec §6) is triggered — never loosen.
- [ ] **1-D chain regression** (`GmrfKrigingSolve` direct tests) still green.

**Verify:** `pixi run test tests/test_tree_kriging_gate.py -v -s 2>&1 | tail -25` → pass with recorded
ratios/residuals; then `pixi run test 2>&1 | tail -5` whole-suite green.

**Steps:** Step 1 build the real-tile 2×2 + 3-tile fixtures via the pipeline spine; Step 2 write the
three coupled assertions + invariance + nonstationary, measuring the chain baseline in-test and
recording the dropped-edge residual as `known_bias`; Step 3 run, capture evidence; Step 4 if
out-of-tolerance STOP and surface §6 escalation; Step 5 record gate evidence in PROGRESS, update
"next action" → Stage C Task 10, commit
`test(phase4): Stage-B gate PASSED — spanning-tree sampler, residual recorded (chain-baseline gate)`.

---

# STAGE C — FEM (discretization swap + payoff)

## Task 10: `fem_mesh.py` — Mesh, Delaunay generation, sliver guard

**Goal:** Add the mesh value object, `build_mesh` (scipy.spatial.Delaunay over an arbitrary point set, supporting a boundary ring and densified points), and `assert_mesh_quality` — the loud sliver guard (FEM analogue of `_assert_separates`).

**Files:**
- Create: `src/sverdrup/methods/fem_mesh.py`
- Test: `tests/unit/test_fem_mesh.py` (new)

**Acceptance Criteria:**
- [ ] `Mesh` is a frozen dataclass with `points: np.ndarray (n,2|3)`, `triangles: np.ndarray (m,3)`, a `.points()` method returning `(n,3)` space-time points (PointSet-like, so the blend's `_nearest`/`_support_points` work), and a `time_days` field.
- [ ] `build_mesh(points, boundary_ring=None, refine_points=None) -> Mesh` triangulates the concatenated point set via `scipy.spatial.Delaunay`.
- [ ] `assert_mesh_quality(mesh, min_angle_deg=15.0)` raises `AssertionError` on a sliver triangulation (a near-degenerate triangle) and passes on a regular grid-derived mesh.

**Verify:** `pixi run test tests/unit/test_fem_mesh.py -v` → pass.

**Steps:**

- [ ] **Step 1: Write the failing test** — `tests/unit/test_fem_mesh.py`:

```python
"""FEM mesh: Delaunay build over a point set; the sliver guard fails loudly."""

from __future__ import annotations

import numpy as np
import pytest

from sverdrup.methods.fem_mesh import Mesh, assert_mesh_quality, build_mesh


def _grid_points(n=6):
    xs, ys = np.meshgrid(np.arange(float(n)), np.arange(float(n)))
    return np.column_stack([xs.ravel(), ys.ravel()])


def test_build_mesh_triangulates_point_set():
    # Behavior: a regular point set produces a valid triangulation with shared vertices.
    m = build_mesh(_grid_points(6))
    assert isinstance(m, Mesh)
    assert m.points.shape[0] == 36
    assert m.triangles.shape[1] == 3
    assert m.points().shape == (36, 3)  # PointSet-like (lon,lat,time)


def test_boundary_ring_adds_exterior_nodes():
    # Behavior: a boundary ring extends the node set (the payoff demo's mechanism).
    ring = np.array([[-2.0, -2.0], [7.0, -2.0], [7.0, 7.0], [-2.0, 7.0]])
    m = build_mesh(_grid_points(6), boundary_ring=ring)
    assert m.points.shape[0] == 40


def test_sliver_guard_rejects_degenerate_triangle():
    # Behavior: a near-collinear point set yields slivers -> loud red (FEM analogue of
    #   _assert_separates), so a meshing artifact never masquerades as a method failure.
    sliver = np.array([[0.0, 0.0], [1.0, 0.0], [2.0, 1e-4], [1.0, 1.0]])
    m = build_mesh(sliver)
    with pytest.raises(AssertionError, match="sliver|angle|quality"):
        assert_mesh_quality(m, min_angle_deg=15.0)


def test_quality_guard_passes_on_grid_mesh():
    assert_mesh_quality(build_mesh(_grid_points(6)), min_angle_deg=10.0)  # no raise
```

- [ ] **Step 2: Run to verify it fails** — FAIL (module missing).

- [ ] **Step 3: Implement `src/sverdrup/methods/fem_mesh.py`:**

```python
"""FEM mesh: scipy.spatial.Delaunay triangulation + the sliver-quality guard (spec §5.4).

Global/shared-node mesh: one triangulation over the domain; tiles are node subsets sharing
overlap nodes, so coincident-node conditioning survives. Demos are driven by the input point
set — an extended boundary ring -> boundary extension; locally-densified points -> adaptive
refinement.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.spatial import Delaunay  # type: ignore[import-untyped]


@dataclass(frozen=True)
class Mesh:
    """A 2-D triangulation: node coordinates + triangle vertex indices (a Projection node space)."""

    points_xy: np.ndarray  # (n, 2) node coordinates (lon, lat)
    triangles: np.ndarray  # (m, 3) vertex indices
    time_days: float = 0.0

    @property
    def points_arr(self) -> np.ndarray:
        """Alias for the (n, 2) node coordinates."""
        return self.points_xy

    @property
    def shape(self) -> tuple[int]:
        """Return the flat node-count shape ``(n_nodes,)`` (mesh field shape)."""
        return (self.points_xy.shape[0],)

    def points(self, time_days: float | None = None) -> np.ndarray:
        """Return ``(n, 3)`` space-time points (PointSet-like, for blend nearest access)."""
        t = self.time_days if time_days is None else time_days
        n = self.points_xy.shape[0]
        return np.column_stack([self.points_xy, np.full(n, t)])


def build_mesh(
    points: np.ndarray,
    boundary_ring: np.ndarray | None = None,
    refine_points: np.ndarray | None = None,
    time_days: float = 0.0,
) -> Mesh:
    """Delaunay-triangulate the (optionally extended/refined) point set.

    Args:
        points: ``(n, 2)`` core node coordinates.
        boundary_ring: optional ``(b, 2)`` exterior nodes (boundary extension).
        refine_points: optional ``(r, 2)`` densified interior nodes (adaptive refinement).
        time_days: the output time carried on the mesh.

    Returns:
        A :class:`Mesh` over the concatenated, de-duplicated point set.
    """
    parts = [np.asarray(points, float)]
    if boundary_ring is not None:
        parts.append(np.asarray(boundary_ring, float))
    if refine_points is not None:
        parts.append(np.asarray(refine_points, float))
    allpts = np.vstack(parts)
    allpts = np.unique(np.round(allpts, 9), axis=0)
    tri = Delaunay(allpts)
    return Mesh(points_xy=allpts, triangles=np.asarray(tri.simplices), time_days=time_days)


def _triangle_min_angle(p0: np.ndarray, p1: np.ndarray, p2: np.ndarray) -> float:
    """Return the smallest interior angle (degrees) of triangle ``(p0,p1,p2)``."""
    a = np.linalg.norm(p1 - p2)
    b = np.linalg.norm(p0 - p2)
    c = np.linalg.norm(p0 - p1)
    angs = []
    for opp, s1, s2 in ((a, b, c), (b, a, c), (c, a, b)):
        denom = 2.0 * s1 * s2
        if denom == 0.0:
            return 0.0
        cosv = np.clip((s1 * s1 + s2 * s2 - opp * opp) / denom, -1.0, 1.0)
        angs.append(np.degrees(np.arccos(cosv)))
    return float(min(angs))


def assert_mesh_quality(mesh: Mesh, min_angle_deg: float = 15.0) -> None:
    """Raise if any triangle is a sliver (min interior angle < ``min_angle_deg``).

    The FEM analogue of ``_assert_separates``: a degenerate triangle inflates the stiffness G
    and dents Q's conditioning. A loud red here means the meshing is bad — it must never be
    mistaken for a method failure (spec §5.4 / §7).
    """
    pts = mesh.points_xy
    worst = 180.0
    for tri in mesh.triangles:
        ang = _triangle_min_angle(pts[tri[0]], pts[tri[1]], pts[tri[2]])
        worst = min(worst, ang)
    if worst < min_angle_deg:
        raise AssertionError(
            f"sliver triangulation: min angle {worst:.2f}° < {min_angle_deg}° — "
            "mesh quality too low (would dent Q conditioning); refine the input point set"
        )
```

- [ ] **Step 4: Run** — `pixi run test tests/unit/test_fem_mesh.py -v` → PASS.

- [ ] **Step 5: Typecheck + commit**

```bash
pixi run typecheck && pixi run pre-commit run --files src/sverdrup/methods/fem_mesh.py tests/unit/test_fem_mesh.py
git add src/sverdrup/methods/fem_mesh.py tests/unit/test_fem_mesh.py
git commit -m "feat(phase4): FEM mesh (Delaunay) + sliver-quality guard (Stage C)"
```

---

## Task 11: `fem_precision` — P1 mass + stiffness assembly; exact marginal var vs dense Q⁻¹

**Goal:** Implement the Lindgren–Rue–Lindström FEM precision (lumped-mass C + stiffness G, α=2) and prove exact Takahashi marginal variance against a dense `Q⁻¹` on a small mesh.

**Files:**
- Create: `src/sverdrup/methods/fem.py` (start with `fem_precision` + assembly helpers)
- Test: `tests/unit/test_fem_precision.py` (new)

**Acceptance Criteria:**
- [ ] `fem_precision(mesh, kappa, tau) -> sparse.csc_matrix` returns a symmetric SPD `(n,n)` precision; `Q = (1/τ)(κ²C + G) C⁻¹ (κ²C + G)`; `C` lumped diagonal (node areas/3), `G` P1 stiffness.
- [ ] `kappa` accepts a scalar OR a per-node `(n,)` field (nonstationary → per-node `κ²C`).
- [ ] `fem_precision` calls `assert_mesh_quality` (sliver guard).
- [ ] On a small (~36-node) mesh, `GMRFFactor(Q).selective_inverse().diagonal()` matches `np.linalg.inv(Q.toarray()).diagonal()` within rtol 1e-7.

**Verify:** `pixi run test tests/unit/test_fem_precision.py -v` → pass.

**Steps:**

- [ ] **Step 1: Write the failing test** — `tests/unit/test_fem_precision.py`:

```python
"""FEM precision: SPD, nonstationary-capable, exact selective-inverse marginal variance."""

from __future__ import annotations

import numpy as np

from sverdrup.methods.fem import fem_precision
from sverdrup.methods.fem_mesh import build_mesh
from sverdrup.methods.gmrf_linalg import GMRFFactor


def _grid_mesh(n=6):
    xs, ys = np.meshgrid(np.arange(float(n)), np.arange(float(n)))
    return build_mesh(np.column_stack([xs.ravel(), ys.ravel()]))


def test_fem_precision_is_symmetric_spd():
    # Behavior: assembled Q is symmetric positive-definite (factorizable).
    q = fem_precision(_grid_mesh(6), kappa=0.5, tau=0.2)
    assert (abs(q - q.T)).nnz == 0 or float(abs(q - q.T).max()) < 1e-10
    GMRFFactor(q)  # raises if not SPD


def test_fem_marginal_var_matches_dense_inverse():
    # Behavior (spec §7): exact selective-inversion marginal variance equals dense diag(Q^-1).
    # Bug caught: an assembly or Takahashi error on the unstructured (mesh) pattern.
    q = fem_precision(_grid_mesh(6), kappa=0.5, tau=0.2)
    sel = np.asarray(GMRFFactor(q).selective_inverse().diagonal())
    dense = np.diag(np.linalg.inv(q.toarray()))
    np.testing.assert_allclose(sel, dense, rtol=1e-7)


def test_fem_precision_nonstationary_kappa():
    # Behavior: a per-node kappa field yields spatially-varying coefficients (C4 on the mesh).
    mesh = _grid_mesh(6)
    kfield = 0.3 + 0.4 * (mesh.points_xy[:, 1] / mesh.points_xy[:, 1].max())
    q = fem_precision(mesh, kappa=kfield, tau=0.2)
    d = np.asarray(q.diagonal())
    assert d.std() / d.mean() > 1e-3
```

- [ ] **Step 2: Run to verify it fails** — FAIL (module/function missing).

- [ ] **Step 3: Implement `fem_precision` (+ helpers)** in `src/sverdrup/methods/fem.py`:

```python
"""Method 3: FEM/triangulation Matérn SPDE (Lindgren-Rue-Lindstrom), α=2 (spec §5.4).

Hand-rolled P1 assembly (lumped-mass diagonal C + stiffness G), matching the hand-rolled
GMRFFactor/Takahashi approach. The precision is just another sparse SPD Q: it reuses the
GMRFCovarianceOperator, the GMRFPrecisionReduction, the GmrfJointKrigingSolve coherence driver,
and the blend unchanged — only this assembly and the FEMBasisProjection differ from grid-GMRF.
"""

from __future__ import annotations

import numpy as np
from scipy import sparse  # type: ignore[import-untyped]

from sverdrup.methods.fem_mesh import Mesh, assert_mesh_quality

_DEG2KM = 111.195


def _assemble_c_g(mesh: Mesh) -> tuple[np.ndarray, sparse.csc_matrix]:
    """Return the lumped-mass diagonal ``c`` (n,) and the P1 stiffness ``G`` (n,n), in km².

    Lumped mass: each triangle contributes area/3 to each of its 3 nodes.
    Stiffness: G_ij = sum_T ∫_T ∇φ_i·∇φ_j = sum_T (cot/area) gradient products (P1).
    Coordinates are scaled to km (cos-lat for lon) so κ has units of 1/km, matching the grid.
    """
    pts = mesh.points_xy.copy()
    lat0 = float(np.mean(pts[:, 1]))
    xy = np.column_stack(
        [pts[:, 0] * _DEG2KM * np.cos(np.deg2rad(lat0)), pts[:, 1] * _DEG2KM]
    )
    n = xy.shape[0]
    c = np.zeros(n)
    rows, cols, vals = [], [], []
    for tri in mesh.triangles:
        i, j, k = int(tri[0]), int(tri[1]), int(tri[2])
        p_i, p_j, p_k = xy[i], xy[j], xy[k]
        # signed area
        area = 0.5 * abs(
            (p_j[0] - p_i[0]) * (p_k[1] - p_i[1])
            - (p_k[0] - p_i[0]) * (p_j[1] - p_i[1])
        )
        if area <= 0.0:
            continue
        for v in (i, j, k):
            c[v] += area / 3.0
        # P1 gradients: b/c coefficients
        verts = [p_i, p_j, p_k]
        idx = [i, j, k]
        grads = []
        for a in range(3):
            b1, b2 = verts[(a + 1) % 3], verts[(a + 2) % 3]
            grad = np.array([b1[1] - b2[1], b2[0] - b1[0]]) / (2.0 * area)
            grads.append(grad)
        for a in range(3):
            for b in range(3):
                rows.append(idx[a])
                cols.append(idx[b])
                vals.append(area * float(grads[a] @ grads[b]))
    g = sparse.csc_matrix((vals, (rows, cols)), shape=(n, n))
    g = 0.5 * (g + g.T)
    return c, g.tocsc()


def fem_precision(
    mesh: Mesh, kappa: float | np.ndarray, tau: float, min_angle_deg: float = 15.0
) -> sparse.csc_matrix:
    """Assemble the FEM Matérn precision ``Q = (1/τ)(κ²C + G) C⁻¹ (κ²C + G)`` (α=2, ν=1).

    Args:
        mesh: The triangulation.
        kappa: Scalar κ, or a per-node ``(n,)`` κ field (nonstationary).
        tau: Marginal-variance scaling.
        min_angle_deg: Sliver-guard threshold.

    Returns:
        Symmetric SPD ``(n, n)`` CSC precision over the mesh nodes.
    """
    assert_mesh_quality(mesh, min_angle_deg=min_angle_deg)
    c, g = _assemble_c_g(mesh)
    n = c.shape[0]
    if np.isscalar(kappa) or np.asarray(kappa).ndim == 0:
        k2 = np.full(n, float(kappa) ** 2)
    else:
        k2 = np.asarray(kappa, float).ravel() ** 2
    k2c = sparse.diags(k2 * c)
    cmat = sparse.diags(c)
    cinv = sparse.diags(1.0 / c)
    a = (k2c + g).tocsc()  # (κ²C + G)
    q = (a.T @ cinv @ a) / float(tau)
    return sparse.csc_matrix(0.5 * (q + q.T))
```

- [ ] **Step 4: Run** — `pixi run test tests/unit/test_fem_precision.py -v` → PASS.

- [ ] **Step 5: Typecheck + commit**

```bash
pixi run typecheck && pixi run pre-commit run --files src/sverdrup/methods/fem.py tests/unit/test_fem_precision.py
git add src/sverdrup/methods/fem.py tests/unit/test_fem_precision.py
git commit -m "feat(phase4): fem_precision P1 mass+stiffness; exact selective-inverse var (Stage C)"
```

---

## Task 12: `FEMBasisProjection` — P1 basis read-off conforming to `Projection`

**Goal:** Add the mesh projection (`weights(pts)` = P1 basis `ψ_i(s_k)` via `find_simplex` + barycentric coords), conforming to the `Projection` protocol with `field_shape() == (n_nodes,)`.

**Files:**
- Modify: `src/sverdrup/methods/fem.py` (add `FEMBasisProjection`)
- Test: `tests/unit/test_fem_projection.py` (new)

**Acceptance Criteria:**
- [ ] `FEMBasisProjection(mesh)` is `isinstance(..., Projection)` True; `field_shape() == (n_nodes,)`; `node_points(t)` returns `mesh.points(t)`.
- [ ] `weights(pts)` rows sum to 1 (partition of unity) for interior points; a point at a mesh vertex is a unit selector; shape `(k, n_nodes)`.
- [ ] `assert_adjacency(q)` checks mesh-edge presence in Q's pattern (every triangle edge `(i,j)` has `Q[i,j] != 0`) and calls the sliver guard.

**Verify:** `pixi run test tests/unit/test_fem_projection.py -v` → pass.

**Steps:**

- [ ] **Step 1: Write the failing test** — `tests/unit/test_fem_projection.py`:

```python
"""FEM basis projection: P1 partition-of-unity weights; conforms to Projection."""

from __future__ import annotations

import numpy as np

from sverdrup.core.projection import Projection
from sverdrup.methods.fem import FEMBasisProjection, fem_precision
from sverdrup.methods.fem_mesh import build_mesh


def _grid_mesh(n=6):
    xs, ys = np.meshgrid(np.arange(float(n)), np.arange(float(n)))
    return build_mesh(np.column_stack([xs.ravel(), ys.ravel()]))


def test_is_a_projection_with_mesh_field_shape():
    m = _grid_mesh(6)
    proj = FEMBasisProjection(m)
    assert isinstance(proj, Projection)
    assert proj.field_shape() == (36,)
    assert proj.node_points(0.0).shape == (36, 3)


def test_weights_partition_of_unity_and_vertex_selector():
    # Behavior: interior P1 weights sum to 1; a vertex maps to a unit selector.
    # Bug caught: a basis that doesn't interpolate -> wrong off-node read-off / conditioning.
    m = _grid_mesh(6)
    proj = FEMBasisProjection(m)
    interior = np.array([[2.3, 3.7, 0.0]])
    w = proj.weights(interior)
    np.testing.assert_allclose(np.asarray(w.sum(axis=1)).ravel(), [1.0], rtol=1e-9)
    vert = np.array([[2.0, 3.0, 0.0]])
    wv = proj.weights(vert)
    assert wv.nnz == 1 and abs(wv.data[0] - 1.0) < 1e-9


def test_assert_adjacency_requires_mesh_edges_in_pattern():
    import pytest
    from scipy import sparse

    m = _grid_mesh(6)
    proj = FEMBasisProjection(m)
    proj.assert_adjacency(fem_precision(m, 0.5, 0.2))  # no raise
    with pytest.raises(AssertionError):
        proj.assert_adjacency(sparse.identity(36, format="csc"))
```

- [ ] **Step 2: Run to verify it fails** — FAIL (`FEMBasisProjection` missing).

- [ ] **Step 3: Implement `FEMBasisProjection`** in `src/sverdrup/methods/fem.py`:

```python
from dataclasses import dataclass

from scipy.spatial import Delaunay  # type: ignore[import-untyped]

from sverdrup.core.types import Points


@dataclass(frozen=True)
class FEMBasisProjection:
    """Mesh read-off: ``W_{ki} = ψ_i(s_k)`` (P1 basis at queries); ``(n_nodes,)`` fields."""

    mesh: Mesh

    @property
    def node_space(self) -> Mesh:
        """Return the node layout (the mesh)."""
        return self.mesh

    def _delaunay(self) -> Delaunay:
        """Rebuild a Delaunay locator from the stored nodes/triangles (cheap; deterministic)."""
        return Delaunay(self.mesh.points_xy)

    def weights(self, pts: Points) -> sparse.csr_matrix:
        """Return the sparse ``(k, n_nodes)`` P1 basis weights at ``pts`` (barycentric)."""
        tri = self._delaunay()
        xy = np.asarray(pts)[:, :2]
        simplex = tri.find_simplex(xy)
        rows, cols, vals = [], [], []
        for r in range(xy.shape[0]):
            s = int(simplex[r])
            if s < 0:
                # outside the hull: nearest vertex (unit selector), keeps rows summing to 1
                j = int(np.argmin(np.linalg.norm(self.mesh.points_xy - xy[r], axis=1)))
                rows.append(r)
                cols.append(j)
                vals.append(1.0)
                continue
            verts = tri.simplices[s]
            b = tri.transform[s, :2] @ (xy[r] - tri.transform[s, 2])
            bary = np.array([b[0], b[1], 1.0 - b[0] - b[1]])
            for a in range(3):
                if abs(bary[a]) > 1e-14:
                    rows.append(r)
                    cols.append(int(verts[a]))
                    vals.append(float(bary[a]))
        n = self.mesh.points_xy.shape[0]
        w = sparse.csr_matrix((vals, (rows, cols)), shape=(xy.shape[0], n))
        rs = np.asarray(w.sum(axis=1)).ravel()
        rs[rs == 0] = 1.0
        return sparse.diags(1.0 / rs) @ w

    def field_shape(self) -> tuple[int, ...]:
        """Return ``(n_nodes,)``."""
        return (self.mesh.points_xy.shape[0],)

    def node_points(self, time_days: float) -> Points:
        """Return the mesh node coordinates at ``time_days``."""
        return self.mesh.points(time_days)

    def assert_adjacency(self, q: sparse.spmatrix) -> None:
        """Raise if any mesh edge is absent from ``q``'s pattern; also run the sliver guard."""
        assert_mesh_quality(self.mesh)
        qcoo = q.tocoo()
        present = set(zip(qcoo.row.tolist(), qcoo.col.tolist(), strict=False))
        for tri in self.mesh.triangles:
            for a in range(3):
                i, j = int(tri[a]), int(tri[(a + 1) % 3])
                if i != j and (i, j) not in present:
                    raise AssertionError(
                        f"mesh edge ({i},{j}) absent from Q pattern — "
                        "read-off / first-difference would miss this covariance entry"
                    )
```

- [ ] **Step 4: Run** — `pixi run test tests/unit/test_fem_projection.py -v` → PASS.

- [ ] **Step 5: Typecheck + commit**

```bash
pixi run typecheck && pixi run pre-commit run --files src/sverdrup/methods/fem.py tests/unit/test_fem_projection.py
git add src/sverdrup/methods/fem.py tests/unit/test_fem_projection.py
git commit -m "feat(phase4): FEMBasisProjection P1 read-off conforms to Projection (Stage C)"
```

---

## Task 13: `FEMMatern.solve` + register `"fem"`; genuine-discretization-swap guard (C5)

**Goal:** Add the FEM method producing a `GMRFCovarianceOperator` over the same machinery, register it, and prove mechanically that NO grid-specific path (`bilinear_weights`, `(ny,nx)` reshape) is taken during a FEM solve+reduce (C5).

**Files:**
- Modify: `src/sverdrup/methods/fem.py` (add `FEMMatern`)
- Modify: `src/sverdrup/methods/registry.py` (register `"fem"`)
- Test: `tests/unit/test_fem_method.py` (new, incl. the C5 guard)

**Acceptance Criteria:**
- [ ] `FEMMatern().solve(obs, mesh_or_grid, params, time_days)` builds the global/shared-node mesh, assembles `Q_prior=fem_precision`, conditions with `A=FEMBasisProjection.weights(obs)`, returns a `GaussianPredictiveDistribution` carrying a `GMRFCovarianceOperator` holding the `FEMBasisProjection` and `q_prior`; `native_capability = SAMPLES` (also COVARIANCE); provenance sparse-precision tag.
- [ ] `METHODS["fem"]` resolves to `FEMMatern`.
- [ ] **C5 guard:** during a FEM solve + `GMRFPrecisionReduction.reduce`, a monkeypatched `bilinear_weights` that raises is NEVER called, and the resulting `PrecisionFields.projection` is a `FEMBasisProjection` with `field_shape() == (n_nodes,)`.
- [ ] FEM flows through the same `GMRFCovarianceOperator`/`GMRFPrecisionReduction` classes as grid-GMRF (assert type identity).

**Verify:** `pixi run test tests/unit/test_fem_method.py -v` → pass.

**Steps:**

- [ ] **Step 1: Write the failing test** — `tests/unit/test_fem_method.py`:

```python
"""FEMMatern: same operator/reduction as grid-GMRF; NO grid-specific path for FEM (C5)."""

from __future__ import annotations

import numpy as np
import pytest

import sverdrup.methods.gmrf_grid as gmrf_grid
from sverdrup.distributions.reduction import GMRFPrecisionReduction
from sverdrup.methods.fem import FEMBasisProjection, FEMMatern
from sverdrup.methods.gmrf import GMRFCovarianceOperator
from sverdrup.methods.registry import METHODS
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
from sverdrup.methods.parameters import ConstantProvider  # adjust to real import


def _mesh():
    from sverdrup.methods.fem_mesh import build_mesh
    xs, ys = np.meshgrid(np.arange(8.0), np.arange(8.0))
    return build_mesh(np.column_stack([xs.ravel(), ys.ravel()]))


def _obs():
    return ObsWindow.from_arrays(
        np.array([3.5]), np.array([3.5]), np.array([2.0]), np.array([1.0]),
        DiagonalErrorModel(np.array([1e-3])),
    )


def test_registered_and_uses_shared_operator():
    assert METHODS["fem"] is FEMMatern
    P = ConstantProvider({"range": 6.0, "variance": 0.2, "temporal_taper_scale": 10.0})
    dist = FEMMatern().solve(_obs(), _mesh(), P, 2.0)
    assert isinstance(dist.cov_op, GMRFCovarianceOperator)
    assert isinstance(dist.cov_op.projection, FEMBasisProjection)


def test_no_grid_path_for_fem(monkeypatch):
    # Behavior (C5): the FEM solve+reduce takes NO grid-specific path — bilinear_weights is
    #   never called, and the persisted projection is a mesh projection.
    # Bug caught: anyone routing FEM through a grid shortcut (the architectural claim of Phase 4).
    def _boom(*a, **k):
        raise AssertionError("bilinear_weights called during a FEM solve — grid path leaked (C5)")

    monkeypatch.setattr(gmrf_grid, "bilinear_weights", _boom)
    P = ConstantProvider({"range": 6.0, "variance": 0.2, "temporal_taper_scale": 10.0})
    mesh = _mesh()
    dist = FEMMatern().solve(_obs(), mesh, P, 2.0)
    unit = GMRFPrecisionReduction().reduce(dist, mesh.points(2.0), None, rank=0, seed=1)
    proj = unit.base_fields.projection
    assert isinstance(proj, FEMBasisProjection)
    assert proj.field_shape() == (mesh.points_xy.shape[0],)
```

- [ ] **Step 2: Run to verify it fails** — FAIL (`FEMMatern` missing / not registered).

- [ ] **Step 3: Implement `FEMMatern`** in `src/sverdrup/methods/fem.py`:

```python
from sverdrup.core.observations import ObsWindow
from sverdrup.core.parameters import ParameterProvider, ParameterSpace
from sverdrup.core.provenance import (
    KnownBias,
    TransformKind,
    UncertaintyProvenance,
    UncertaintyTransform,
)
from sverdrup.core.types import CovFidelity, UncertaintyCapability
from sverdrup.distributions.gaussian import GaussianPredictiveDistribution
from sverdrup.methods.fem_mesh import build_mesh
from sverdrup.methods.gmrf import GMRFCovarianceOperator
from sverdrup.methods.gmrf_grid import kappa_from_range


class FEMMatern:
    """FEM/triangulation Matérn GMRF: mesh precision + temporally-tapered likelihood."""

    native_capability = UncertaintyCapability.SAMPLES  # also exposes COVARIANCE

    def _mesh_for(self, support: object) -> Mesh:
        """Return a Mesh: pass-through if already a Mesh, else triangulate a grid's nodes."""
        if isinstance(support, Mesh):
            return support
        pts = support.points(0.0)[:, :2]  # GridSpec -> its nodes (global/shared-node)
        return build_mesh(pts)

    def solve(
        self,
        obs: ObsWindow,
        support: object,
        params: ParameterProvider,
        time_days: float,
    ) -> GaussianPredictiveDistribution:
        """Solve the FEM GMRF posterior over the mesh at ``time_days`` (temporal taper into R)."""
        mesh = self._mesh_for(support)
        # resolve params on the mesh node space; provider.resolve takes a GridSpec-like .points
        rng_resolved = params.resolve("range", support)  # scalar OR field over support
        tau = float(params.resolve("variance", support))
        taper = float(params.resolve("temporal_taper_scale", support))
        if np.isscalar(rng_resolved) or np.asarray(rng_resolved).ndim == 0:
            kappa: float | np.ndarray = kappa_from_range(float(rng_resolved))
            range_repr: float | str = float(rng_resolved)
        else:
            kappa = kappa_from_range(np.asarray(rng_resolved).ravel())
            range_repr = "field(varying)"
        q_prior = fem_precision(mesh, kappa, tau)

        projection = FEMBasisProjection(mesh)
        a_op = projection.weights(obs.coords())
        r_diag = np.diag(obs.error_model.as_matrix(len(obs))).astype(float)
        dt = np.abs(obs.coords()[:, 2] - time_days)
        r_inflated = r_diag * np.exp(dt / max(taper, 1e-9))
        r_inv = sparse.diags(1.0 / r_inflated)
        q_post = (q_prior + a_op.T @ r_inv @ a_op).tocsc()

        op = GMRFCovarianceOperator(projection, q_post, time_days, q_prior=q_prior)
        rhs = a_op.T @ (r_inv @ obs.values())
        mean = op._factor.solve(np.asarray(rhs)).reshape(projection.field_shape())

        prov = UncertaintyProvenance(
            native_capability=self.native_capability,
            transformations=[
                UncertaintyTransform(
                    kind=TransformKind.DIAGONAL_INFLATION,
                    known_bias=KnownBias.UNDER_DISPERSED_IN_VOIDS,
                    params={
                        "discretization": "FEM/triangulation (LRL SPDE, α=2)",
                        "temporal_taper_scale": taper,
                        "range": range_repr,
                        "kappa_range_mapping": "range = sqrt(8*nu)/kappa, nu=1",
                    },
                )
            ],
        )
        return GaussianPredictiveDistribution(mesh, mean, op, prov, time_days)

    def parameter_space(self) -> ParameterSpace:
        """Return the tunable space: range, variance, temporal taper (ν fixed to α=2)."""
        return ParameterSpace(
            {
                "range": (10.0, 800.0),
                "variance": (1e-3, 1.0),
                "temporal_taper_scale": (1.0, 30.0),
            }
        )
```

(Confirm `GaussianPredictiveDistribution` accepts a mesh as its `grid` arg — it stores it and exposes `.grid`; the mesh is PointSet-like via `.points()`. If `GaussianPredictiveDistribution.marginal_variance()` reshapes to `grid.shape`, the mesh's `.shape == (n_nodes,)` makes the reshape a no-op flat array — verify against `distributions/gaussian.py:27-28` and, if it hard-assumes 2 dims, route its reshape through `field_shape` analogously to Task 3.)

- [ ] **Step 4: Register `"fem"`** in `src/sverdrup/methods/registry.py`:

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

- [ ] **Step 5: Run** — `pixi run test tests/unit/test_fem_method.py -v` → PASS.

- [ ] **Step 6: Typecheck + commit**

```bash
pixi run typecheck && pixi run pre-commit run --files src/sverdrup/methods/fem.py src/sverdrup/methods/registry.py tests/unit/test_fem_method.py
git add src/sverdrup/methods/fem.py src/sverdrup/methods/registry.py tests/unit/test_fem_method.py
git commit -m "feat(phase4): FEMMatern method + registry; mechanical no-grid-path guard (C5)"
```

---

## Task 14: FEM blends through the inherited joint sampler (global/shared-node) + mesh shared-node match (C6)

**Goal:** Prove a FEM-GMRF tiled blend runs seam-free through `GmrfJointKrigingSolve` unchanged (global/shared-node mesh ⇒ coincident-node conditioning), and that shared strip nodes actually match across mesh tiles (C6 on the mesh).

**Files:**
- Test: `tests/test_fem_blend.py` (new)

**Acceptance Criteria:**
- [ ] Two FEM tiles that are node subsets of ONE global mesh, sharing overlap nodes, blend via the sparse-precision driver: the coherent member is finite, seam-free (no mid-overlap variance dip), and conservative vs a single-mesh reference (record the ratio).
- [ ] C6 on the mesh: `_strip_network` over the two FEM tiles yields a non-empty shared strip-node set (shared mesh vertices match at `decimals=6`); a constructed non-coincident pair raises the C6 `AssertionError`.
- [ ] Provenance carries the sparse-precision tag and any recorded coherence residual.

**Verify:** `pixi run test tests/test_fem_blend.py -v` → pass.

**Steps:**

- [ ] **Step 1: Write the test** — `tests/test_fem_blend.py`. Build one global mesh (e.g. a 10×10 grid's nodes triangulated), define two `FEMMatern` tiles as node subsets (overlapping quadrants), persist each via `GMRFPrecisionReduction`, wrap in `PrecisionDistribution(mesh_tile, fields, prov, t)`, and run the blend exactly as `tests/test_gmrf_blend.py` does — only the support is a mesh. Assert finiteness, the conservative ratio vs a single-mesh reference, and `_strip_network` non-empty shared set. Add a non-coincident pair (two independently-built meshes with offset vertices) and assert the C6 raise.

```python
"""FEM blend: tiled FEM-GMRF coherent through the inherited joint sampler; mesh nodes match (C6)."""

from __future__ import annotations

import numpy as np
import pytest

from sverdrup.distributions.coherent import GmrfJointKrigingSolve, NoiseSpec, _strip_network
# reuse the blend realization machinery from tests/test_gmrf_blend.py (import its helpers or
# replicate the minimal coherent-member realization used there)

_NOISE = NoiseSpec(method="fem", params_key="k", lattice_step=0.25)


def test_fem_tiles_share_mesh_nodes_and_blend_finite():
    # Behavior (invariant 9 / C6): FEM tiles as subsets of ONE global mesh share overlap nodes,
    #   so the joint sampler conditions on coincident nodes and the blend is finite + seam-free.
    parts = _two_fem_tiles_one_global_mesh()  # build per the description above
    gk, pt = _strip_network(parts)
    assert len(gk) > 0  # shared mesh nodes actually matched (decimals=6)
    pts = parts[0].distribution.grid.points(2.0)
    w = np.ones((len(parts), pts.shape[0])) / len(parts)
    out = GmrfJointKrigingSolve().crossfaded_member(parts, pts, w, 1, _NOISE)
    assert np.all(np.isfinite(out))


def test_noncoincident_mesh_tiles_raise_c6():
    parts = _two_noncoincident_fem_tiles()
    with pytest.raises(AssertionError, match="share no strip node|stencil reach"):
        _strip_network(parts)
```

- [ ] **Step 2: Run** — `pixi run test tests/test_fem_blend.py -v` → PASS.

- [ ] **Step 3: Typecheck + commit**

```bash
pixi run typecheck && pixi run pre-commit run --files tests/test_fem_blend.py
git add tests/test_fem_blend.py
git commit -m "test(phase4): FEM blend through inherited joint sampler; mesh shared-node match (C6)"
```

---

## Task 15: Payoff demo — boundary extension removes edge variance inflation (C7) + OSSE/OSE

**Goal:** Demonstrate the FEM-specific payoff the grid cannot deliver: a boundary-extended mesh removes the edge variance inflation the regular grid shows, measured **at near-boundary nodes** (C7); and confirm FEM accuracy + calibration fire in OSSE and OSE.

**Files:**
- Create: `tests/test_fem_payoff.py` (new)
- Create: `docs/superpowers/figures/phase4_fem_boundary_payoff.py` (figure generator; cmocean via the plotting-colormaps skill)

**Acceptance Criteria:**
- [ ] On a domain with an edge, grid-GMRF marginal variance at near-boundary nodes is inflated relative to interior; FEM with a boundary-extension ring reduces near-boundary variance toward the interior level: `edge_var(FEM) < edge_var(grid)` at near-boundary nodes by a recorded margin (assert ratio < 0.9; print both).
- [ ] The comparison is at near-boundary nodes specifically (NOT interior-averaged) — C7.
- [ ] FEM OSSE accuracy (RMSE finite, reduced-χ² + coverage computed) and OSE calibration fire on the FEM product (reuse the Phase-3 OSSE/OSE eval path; the tiny-fixture smoke run, opt-in global skipped cleanly).
- [ ] A figure is produced via the plotting-colormaps skill (cmocean perceptually-uniform; correct zero-handling) showing grid vs FEM near-boundary variance.

**Verify:** `pixi run test tests/test_fem_payoff.py -v -s 2>&1 | tail -20` → pass with recorded margins.

**Steps:**

- [ ] **Step 1: Invoke the plotting-colormaps skill** before writing the figure generator (cmocean choice for a variance/positive field; no zero-crossing).

- [ ] **Step 2: Write the payoff test** — `tests/test_fem_payoff.py`:

```python
"""FEM payoff: boundary extension removes near-boundary variance inflation the grid shows (C7)."""

from __future__ import annotations

import numpy as np

from sverdrup.methods.fem import FEMMatern, fem_precision
from sverdrup.methods.fem_mesh import build_mesh
from sverdrup.methods.gmrf import MaternGMRF
from sverdrup.methods.gmrf_linalg import GMRFFactor
# ConstantProvider, ObsWindow, GridSpec imports as in the other tests


def _near_boundary_mask(xy, lo, hi, band=1.0):
    return (
        (xy[:, 0] <= lo + band) | (xy[:, 0] >= hi - band)
        | (xy[:, 1] <= lo + band) | (xy[:, 1] >= hi - band)
    )


def test_boundary_extension_reduces_edge_variance():
    # Behavior (C7): a boundary-extended FEM mesh lowers near-boundary marginal variance toward
    #   the interior level, vs the regular grid's Neumann edge inflation. Measured AT the
    #   boundary band, not interior-averaged (which would wash the effect out).
    # Bug caught: a boundary extension that doesn't actually remove edge inflation.
    n = 12
    xs, ys = np.meshgrid(np.arange(float(n)), np.arange(float(n)))
    core = np.column_stack([xs.ravel(), ys.ravel()])
    mask = _near_boundary_mask(core, 0.0, float(n - 1), band=1.0)

    # grid-GMRF prior marginal variance (no obs -> prior; reuse matern_precision on the grid)
    from sverdrup.methods.gmrf_grid import matern_precision
    from sverdrup.core.grid import GridSpec

    g = GridSpec(x=np.arange(float(n)), y=np.arange(float(n)), crs="EPSG:4326")
    qg = matern_precision(g, kappa=0.5, tau=0.2)
    var_grid = np.asarray(GMRFFactor(qg).selective_inverse().diagonal())

    # FEM with a boundary ring ~2 deg outside the core
    ring = np.array([[-2, -2], [n + 1, -2], [n + 1, n + 1], [-2, n + 1]], float)
    # add a denser ring so the extension is effective (a frame of nodes)
    frame = []
    for t in np.linspace(-2, n + 1, 2 * n):
        frame += [[-2, t], [n + 1, t], [t, -2], [t, n + 1]]
    mesh = build_mesh(core, boundary_ring=np.array(frame, float))
    qf = fem_precision(mesh, kappa=0.5, tau=0.2)
    var_fem_all = np.asarray(GMRFFactor(qf).selective_inverse().diagonal())
    # map FEM core nodes back to the core ordering
    core_idx = [int(np.argmin(np.linalg.norm(mesh.points_xy - c, axis=1))) for c in core]
    var_fem = var_fem_all[core_idx]

    edge_grid = float(var_grid[mask].mean())
    edge_fem = float(var_fem[mask].mean())
    print(f"[stage-c] near-boundary var grid={edge_grid:.4f} fem={edge_fem:.4f} ratio={edge_fem/edge_grid:.3f}")
    assert edge_fem / edge_grid < 0.9, "boundary extension did not reduce edge variance (C7)"
```

- [ ] **Step 3: Write the FEM OSSE/OSE test** in the same file — reuse the Phase-3 eval path (`tests/test_gmrf_blend.py` / the OSSE+OSE integration test) with `METHODS["fem"]`, on the committed tiny fixture; assert RMSE finite, reduced-χ²/coverage computed (OSSE), calibration fires (OSE), opt-in global skipped cleanly.

- [ ] **Step 4: Write the figure generator** `docs/superpowers/figures/phase4_fem_boundary_payoff.py` (cmocean; saves a PNG comparing grid vs FEM near-boundary variance). Not run in CI; a `__main__` guard.

- [ ] **Step 5: Run** — `pixi run test tests/test_fem_payoff.py -v -s 2>&1 | tail -20` → PASS with the recorded ratio.

- [ ] **Step 6: Typecheck + commit**

```bash
pixi run typecheck && pixi run pre-commit run --files tests/test_fem_payoff.py docs/superpowers/figures/phase4_fem_boundary_payoff.py
git add tests/test_fem_payoff.py docs/superpowers/figures/phase4_fem_boundary_payoff.py
git commit -m "test(phase4): FEM boundary-extension payoff (C7) + OSSE/OSE; figure via cmocean"
```

---

## Task 16: STAGE-C GATE — FEM definition of done

**Goal:** Certify Stage C against spec §7: FEM plugged in at `Method.solve`, exact selective-inversion var, provider-driven κ, SAMPLES+COVARIANCE, blends globally seam-free + conservative with provenance carrying the sparse-precision tag + recorded residual, the genuine-discretization-swap test green, the boundary payoff fires, and the WHOLE suite green.

> **USER-ORDERED GATE — NON-SKIPPABLE.** This task was requested by the user in the current conversation. It MUST NOT be closed by walking around it, by declaring it "verified inline", or by substituting a cheaper check. Close only after every item in `acceptanceCriteria` has been re-validated independently, with output captured.

**Files:**
- Test: none new (gate over Stage-C tests + whole suite)

**Acceptance Criteria:**
- [ ] `pixi run test` → 0 failed (Phase-3 178/2 + all Stage A/B/C additions), `pixi run typecheck` + `pixi run lint` clean.
- [ ] Genuine-discretization-swap (C5) green: FEM uses the same `GMRFCovarianceOperator`/`GMRFPrecisionReduction`/`GmrfJointKrigingSolve`/`BlendOperator`; no grid path taken.
- [ ] Exact FEM marginal var (Task 11) green; sliver guard (Task 10) green; boundary payoff (Task 15, C7) green with recorded margin; FEM OSSE+OSE fire.
- [ ] FEM blend provenance carries the sparse-precision tag and any recorded coherence residual.
- [ ] `rg -n "bilinear_weights\(self\.grid|self\.grid\.shape" src/sverdrup/methods/gmrf.py src/sverdrup/methods/fem.py src/sverdrup/distributions/persisted.py` → empty.

**Verify:** `pixi run test 2>&1 | tail -6 && pixi run typecheck && pixi run lint` → 0 failed, clean.

**Steps:**

- [ ] **Step 1: Run the whole suite + typecheck + lint**

```bash
pixi run test 2>&1 | tail -6
pixi run typecheck && pixi run lint
```
Expected: 0 failed; clean.

- [ ] **Step 2: Re-confirm the C5 swap + invariant-2 cleanliness**

```bash
pixi run test tests/unit/test_fem_method.py::test_no_grid_path_for_fem -v
rg -n "bilinear_weights\(self\.grid|self\.grid\.shape" src/sverdrup/methods/gmrf.py src/sverdrup/methods/fem.py src/sverdrup/distributions/persisted.py
```
Expected: pass; grep empty.

- [ ] **Step 3: Update PROGRESS.md + commit**

Record Phase 4 COMPLETE (Stages A/B/C, three gates), the captured Stage-B/-C residuals/margins, and set next milestone = Phase 5 (autotune). Commit:
```bash
git add PROGRESS.md
git commit -m "chore(phase4): Stage-C gate PASSED — FEM discretization swap + payoff; Phase 4 COMPLETE"
```

---

## Self-Review (completed during authoring)

- **Spec coverage:** §4a Projection seam → Tasks 1–3; §4b non-chain sampler → Tasks 5–9; §5.1 Projection → Task 1; §5.2 de-grid persistence → Task 3; §5.3 joint sampler + gated residual → Tasks 6–9; §5.4 fem_precision/FEMBasisProjection/FEMMatern/sliver guard → Tasks 10–13; invariants 1 (gate) → Task 4; 2 (no hardcoded read-off) → Tasks 2,3,16 greps; 3 (de-grid) → Task 3; 4 (independent white) → Tasks 6,8; 5 (topology-agnostic + negative control) → Tasks 7,8; 6 (positive control) → Task 9; 7 (recorded residual) → Task 9; 8 (representation-native) → Tasks 13,14; 9 (global/shared-node) → Tasks 13,14; 10 (exact var) → Task 11; 11 (determinism) → Tasks 6,7. §7 DoD → Tasks 4,9,16. C1–C7 each mapped to a named test. No spec requirement is unticketed.
- **Placeholder scan:** the only ellipses are inside test-helper bodies explicitly flagged "fill against the real blend API" (Tasks 9, 14) where the concrete machinery to reuse already exists in `tests/test_gmrf_blend.py` — these are reuse instructions, not unwritten logic; every production function has complete code.
- **Type consistency:** `Projection.weights/field_shape/node_points/assert_adjacency` used identically in Tasks 1,2,3,12,13; `GMRFCovarianceOperator(projection_or_grid, q_post, time_days, q_prior=)` consistent across Tasks 2,13; `PrecisionFields(..., projection=, prior_precision=)` consistent across Tasks 3,6; `_strip_network`/`_strip_prior`/`_draw_joint` signatures consistent across Tasks 5,6,7,8.
- **Import paths to confirm at execution** (flagged inline): `Tile`/`Window` locations, the constant `ParameterProvider` class name, and `GaussianPredictiveDistribution`'s reshape behavior — grep before use, adjust to the real symbols (the design mandates reusing existing fixtures/paths).
