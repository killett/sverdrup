# Phase 3 — GMRF method + representation-agnostic generalization — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a regular-grid Matérn GMRF (sparse-precision) method to `sverdrup` and generalize the coherence/persistence/reduction layer so a sparse-precision representation is first-class beside OI's low-rank — without re-baking OI's shape into the protocol spine.

**Architecture:** Three coupled seams, refactored OI-first **under the green Phase-2 suite** (the regression oracle), then GMRF added as a second instance: (a) a `ReductionStrategy` selected by the **live operator's representation** pre-persistence; (b) a `CoherentMemberDriver` selected by the persisted **`sampler_spec`** post-persistence; (c) a representation-tagged persisted form (`PrecisionFields` beside `PersistedFields`). GMRF reads every field/covariance off the precision through a `Projection` (grid block = identity, off-grid = bilinear), so a later FEM phase needs only a new projection + mesh assembly. Sequencing is hard-gated: Stage-A green → Stage-B → Stage-C.

**Tech Stack:** Python 3.12+, numpy, scipy, pyproj, **scikit-sparse (CHOLMOD, simplicial)** new for the sparse Cholesky + hand-rolled Takahashi selective inverse. pixi for deps, pytest/ruff/mypy via pre-commit.

**User decisions (already made):**
- Sparse backend: **scikit-sparse (CHOLMOD), simplicial mode**; hand-roll Takahashi for `diag(Q⁻¹)` + adjacent-node entries over the `L+Lᵀ` pattern; pure-scipy dense `Q⁻¹` kept **only** as the small-grid test oracle. If osx-arm64 build gaps, pin under `[target.linux-64.dependencies]`.
- GMRF conditioning on the space-time obs window: **temporal taper into R** — `Q_post = Q_prior + AᵀR⁻¹A`, `A` = bilinear grid→obs spatial interpolation, `R` per-obs variance inflated by time-offset from the output time; the taper scale is a **tunable** in `parameter_space()` resolved via `ParameterProvider`; record the conservative `known_bias` (diagonal-R under-uses temporal structure).
- `to_persisted` lives as a `ReductionStrategy` in `distributions/reduction.py` **selected by representation**, NOT a method on the core `CovarianceOperator` Protocol (honors invariant 1 + the one-way `application/→distributions/` dependency rule; §5.4's on-Protocol signature was self-inconsistent — it would return a distributions-layer type from core).
- B6 GMRF eval-point OSE blend = **moment crossfade** (exact per-tile var from Takahashi; cross-eval-point covariance in overlaps dropped — not consumed by per-point OSE accuracy/calibration); **record the simplification in provenance** so a future joint-predictive phase finds a flag, not a hidden assumption.
- `Projection` abstraction: precision-node space and output-grid space kept conceptually distinct; gridded block = `GridIdentityProjection`, off-grid = `BilinearProjection`, both from one bilinear primitive; `A` (grid→obs) is itself a projection into node space.
- α = 2 (ν = 1), the canonical `(κ²I−Δ)` 5-point stencil; continuous ν deferred to Phase 4.
- Keep `MemberSeededZr` / `CoherentSampler.realize_one` / `coherent_structured_field` / `StructuredNoiseSource` as the folded-in historical/single-tile driver (tests import them directly; deleting = red).
- Watch-points: Task 5 Takahashi correctness rests on the dense-`Q⁻¹` oracle — a red there is a **math bug to fix, not a tolerance to loosen**; Task 3 Stage-A gate — if OI behavior changes, **surface it, do not adjust the tests to pass**.

**Source of truth:** `phase3_scope_spec.md` (settled). This plan maps its §4/§5 onto the real layout.

---

## File structure (created / modified)

**Stage A**
- Create `src/sverdrup/distributions/reduction.py` — `ReductionStrategy` Protocol, `ReducedUnit`, `LowRankReduction`, `EmpiricalReduction`, `select_reduction`.
- Modify `src/sverdrup/application/solve.py` — call the strategy instead of the `hasattr(dist,"cov_op")` hardcode.
- Modify `src/sverdrup/methods/oi.py` — add `representation = "lowrank+diag"` class attr to `GPCovarianceOperator`.
- Modify `src/sverdrup/distributions/coherent.py` — add `CoherentMemberDriver` Protocol + `LowRankSharedBasis`, `select_driver`; relocate `_nearest`/`_support_points` here.
- Modify `src/sverdrup/distributions/blend.py` — `_coherent_member` delegates to `select_driver(sampler_spec)`; `BlendInput.distribution: PredictiveDistribution`; import moved helpers.

**Stage B**
- Modify `pixi.toml` — add `scikit-sparse`.
- Create `src/sverdrup/methods/gmrf_grid.py` — regular-grid topology, `(κ²−Δ)` α=2 stencil → sparse `Q`, the one bilinear primitive, `Projection`/`GridIdentityProjection`/`BilinearProjection`, κ↔range mapping.
- Create `src/sverdrup/methods/gmrf_linalg.py` — CHOLMOD simplicial factor wrapper + hand-rolled Takahashi + adjacency assertion.
- Create `src/sverdrup/methods/gmrf.py` — `GMRFCovarianceOperator`, `MaternGMRF`.
- Modify `src/sverdrup/methods/registry.py` — register `"gmrf"`.
- Modify `src/sverdrup/distributions/persisted.py` — `PrecisionFields`, `PrecisionDistribution`.
- Modify `src/sverdrup/distributions/reduction.py` — `GMRFPrecisionReduction`, register in `_REDUCTIONS`.
- Modify `src/sverdrup/distributions/coherent.py` — `GmrfPrecisionSolve` driver, register in `select_driver`.
- Modify `src/sverdrup/application/pipeline.py` — `_blend_eval_points` handles the sparse-precision (no-factor) path via moment crossfade.

**Stage C**
- Modify `src/sverdrup/core/provenance.py` — `KnownBias.DEGRADED_COHERENCE`, `degradation_transform`.
- Modify `src/sverdrup/distributions/coherent.py` — `PerturbEnsembleDegradation` driver.
- Modify `src/sverdrup/distributions/reduction.py` — `EmpiricalReduction.sampler_spec = "perturb-ensemble"`.

**Tests:** new `tests/unit/test_reduction.py`, `tests/test_coherent_driver_seam.py`, `tests/unit/test_gmrf_grid.py`, `tests/unit/test_gmrf_linalg.py`, `tests/unit/test_gmrf_method.py`, `tests/unit/test_precision_distribution.py`, `tests/test_gmrf_blend.py`, `tests/test_degradation_path.py`, `tests/test_nonstationary_kappa.py`.

---

## Stage A — generalize OI under green

### Task 1: ReductionStrategy seam (§4c) — OI + ensemble paths, behavior-identical

**Goal:** Move the on-worker reduction out of `solve.py`'s hardcode into a per-operator strategy selected by the live operator's representation, with OI and ensemble paths byte-identical to today.

**Files:**
- Create: `src/sverdrup/distributions/reduction.py`
- Modify: `src/sverdrup/application/solve.py` (`_reduce`, `_eval_points`, `solve_unit`)
- Modify: `src/sverdrup/methods/oi.py` (`GPCovarianceOperator`: add `representation` attr)
- Test: `tests/unit/test_reduction.py`

**Acceptance Criteria:**
- [ ] `select_reduction(dist)` returns `LowRankReduction` for a Gaussian dist whose operator's `representation == "lowrank+diag"`, `EmpiricalReduction` for an ensemble dist (no `cov_op`).
- [ ] `LowRankReduction.reduce` reproduces `reduce_with_basis` + `eval_rows_in_grid_basis` + `posterior_mean`/`marginal_var` exactly (same arrays).
- [ ] The full Phase-2 suite stays green (no behavior change).

**Verify:** `pixi run test -q` → `129 passed, 2 skipped`; plus `pixi run test tests/unit/test_reduction.py -v` → all pass.

**Steps:**

- [ ] **Step 1: Write the failing test** — `tests/unit/test_reduction.py`

```python
"""ReductionStrategy: dispatch by live-operator representation; OI path unchanged."""

from __future__ import annotations

import numpy as np

from sverdrup.core.grid import GridSpec
from sverdrup.distributions.persisted import reduce_with_basis
from sverdrup.distributions.reduction import (
    EmpiricalReduction,
    LowRankReduction,
    select_reduction,
)


class _FakeOp:
    representation = "lowrank+diag"
    fidelity = None

    def __init__(self, n):
        rng = np.random.default_rng(0)
        b = rng.standard_normal((n, 4))
        self._p = b @ b.T + np.eye(n) * 0.1

    def cov(self, a, b):
        return self._p[: a.shape[0]][:, : b.shape[0]]

    def marginal_var(self, a):
        return np.diag(self._p)[: a.shape[0]]

    def posterior_mean(self, pts):
        return np.zeros(pts.shape[0])


class _FakeGaussian:
    def __init__(self, grid, op):
        self.grid = grid
        self.mean = np.zeros(grid.shape)
        self.cov_op = op
        self.time_days = 0.0


class _FakeEnsemble:
    def __init__(self, grid, samples):
        self.grid = grid
        self.samples = samples
        self.time_days = 0.0


def _grid():
    return GridSpec.lonlat(np.linspace(0, 4, 5), np.linspace(0, 4, 5))


def test_select_reduction_dispatches_on_representation():
    # Behavior: selection keys on the live operator's representation, not method identity.
    # Bug caught: dispatching on hasattr(cov_op) alone would route a future sparse-precision
    #   operator (which also wraps in a Gaussian dist) to the low-rank reducer.
    g = _grid()
    assert isinstance(select_reduction(_FakeGaussian(g, _FakeOp(25))), LowRankReduction)
    samples = np.random.default_rng(1).standard_normal((8, 5, 5))
    assert isinstance(select_reduction(_FakeEnsemble(g, samples)), EmpiricalReduction)


def test_lowrank_reduction_matches_reduce_with_basis():
    # Behavior: the strategy's base reduction equals the free-function reduction exactly.
    # Bug caught: any drift in factor/residual/marginal_variance vs the Phase-2 path.
    g = _grid()
    dist = _FakeGaussian(g, _FakeOp(25))
    pts = g.points(0.0)
    unit = LowRankReduction().reduce(dist, pts, None, rank=6, seed=3)
    ref, _ = reduce_with_basis(dist.mean, dist.cov_op, pts, rank=6, seed=3)
    np.testing.assert_array_equal(unit.base_fields.factor, ref.factor)
    np.testing.assert_array_equal(unit.base_fields.residual, ref.residual)
    assert unit.base_fields.sampler_spec == "lowrank+diag"


def test_lowrank_reduction_builds_eval_rows_in_basis():
    # Behavior: eval rows come from eval_rows_in_grid_basis (shared SVD basis), exact var.
    # Bug caught: re-factoring eval rows independently breaks cross-tile eval blending.
    g = _grid()
    dist = _FakeGaussian(g, _FakeOp(25))
    pts = g.points(0.0)
    evals = np.array([[1.3, 1.7, 0.0], [2.1, 0.4, 0.0]])
    unit = LowRankReduction().reduce(dist, pts, evals, rank=6, seed=3)
    assert unit.eval_points is not None
    assert unit.eval_points.factor.shape == (2, 6)
    np.testing.assert_allclose(
        unit.eval_points.variance, dist.cov_op.marginal_var(evals)
    )
```

- [ ] **Step 2: Run — confirm fail**

Run: `pixi run test tests/unit/test_reduction.py -v`
Expected: FAIL — `ModuleNotFoundError: sverdrup.distributions.reduction`.

- [ ] **Step 3: Implement `reduction.py`**

```python
"""Per-operator persistence strategy (spec §4c, §5.4).

Dispatch is on the LIVE operator's representation (pre-persistence) — never on method
identity. The coherence driver later dispatches on the persisted ``sampler_spec``
(post-persistence); that two-point split is deliberate (see the plan).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, cast, runtime_checkable

import numpy as np

from sverdrup.core.product import EvalPointPredictions
from sverdrup.distributions.persisted import (
    PersistedFields,
    eval_rows_in_grid_basis,
    reduce_with_basis,
)


@dataclass(frozen=True)
class ReducedUnit:
    """Everything extracted before the live operator goes out of scope."""

    base_fields: PersistedFields
    eval_points: EvalPointPredictions | None


@runtime_checkable
class ReductionStrategy(Protocol):
    """Reduce a live distribution to a storable representation + eval-point predictives."""

    def reduce(
        self,
        dist: object,
        grid_points: np.ndarray,
        eval_points: np.ndarray | None,
        *,
        rank: int,
        seed: int,
    ) -> ReducedUnit:
        """Return the persisted base fields and (optional) eval-point predictions."""
        ...


class LowRankReduction:
    """OI low-rank+diagonal reduction: randomized-SVD factor + exact residual."""

    def reduce(
        self, dist, grid_points, eval_points, *, rank, seed
    ) -> ReducedUnit:
        d = cast(Any, dist)
        base, basis = reduce_with_basis(
            d.mean, d.cov_op, grid_points, rank=rank, seed=seed
        )
        if eval_points is None:
            return ReducedUnit(base, None)
        mean = d.cov_op.posterior_mean(eval_points)
        var = d.cov_op.marginal_var(eval_points)
        factor, residual = eval_rows_in_grid_basis(
            d.cov_op, eval_points, grid_points, basis
        )
        return ReducedUnit(
            base,
            EvalPointPredictions(
                eval_points, mean, var, samples=None, factor=factor, residual=residual
            ),
        )


class EmpiricalReduction:
    """Ensemble (Method 0) empirical reduction: sample mean/variance, no factor."""

    sampler_spec = "lowrank+diag"  # Phase-2 default; retagged "perturb-ensemble" in Task 10

    def reduce(
        self, dist, grid_points, eval_points, *, rank, seed
    ) -> ReducedUnit:
        d = cast(Any, dist)
        flat = d.samples.reshape(d.samples.shape[0], -1)
        var = flat.var(axis=0, ddof=1)
        base = PersistedFields(
            mean=d.samples.mean(axis=0),
            marginal_variance=var.reshape(d.grid.shape),
            factor=np.zeros((flat.shape[1], 0)),
            residual=var,
            rank=0,
            seed=seed,
            captured_energy=0.0,
            sampler_spec=self.sampler_spec,
        )
        if eval_points is None:
            return ReducedUnit(base, None)
        nodes = d.grid.points(d.time_days)
        idx = np.argmin(
            np.linalg.norm(eval_points[:, None, :2] - nodes[None, :, :2], axis=2),
            axis=1,
        )
        s = flat[:, idx]
        return ReducedUnit(
            base,
            EvalPointPredictions(
                eval_points, s.mean(axis=0), s.var(axis=0, ddof=1), samples=s
            ),
        )


_REDUCTIONS: dict[str, type] = {"lowrank+diag": LowRankReduction}


def select_reduction(dist: object) -> ReductionStrategy:
    """Pick the reduction by the live operator's representation (ensemble if no operator)."""
    op = getattr(dist, "cov_op", None)
    if op is None:
        return EmpiricalReduction()
    rep = getattr(op, "representation", "lowrank+diag")
    return cast(ReductionStrategy, _REDUCTIONS[rep]())
```

- [ ] **Step 4: Add `representation` to `GPCovarianceOperator`** — `src/sverdrup/methods/oi.py`, in the class body just under `fidelity = CovFidelity.EXACT`:

```python
    fidelity = CovFidelity.EXACT
    representation = "lowrank+diag"
```

- [ ] **Step 5: Refactor `solve.py` to use the strategy**

Replace `_reduce` and `_eval_points` usage in `solve_unit` and delete the now-dead branches. New `solve_unit` body (the loop):

```python
    method = cast(Any, METHODS[uow.method_name]())
    per_time: list[PerTimeProduct] = []
    for t in uow.output_times:
        dist = method.solve(uow.obs, uow.grid, uow.params, t)  # operator live here
        strat = select_reduction(dist)
        unit = strat.reduce(
            dist,
            uow.grid.points(t),
            uow.eval_locations,
            rank=uow.rank,
            seed=uow.seed,
        )
        base = PersistedDistribution(uow.grid, unit.base_fields, dist.provenance, t)
        derived = {
            name: _reduce_derived(_DERIVED[name](), dist, uow)
            for name in uow.derived_names
        }
        prov = ProductProvenance(
            method=uow.method_name,
            params_key=uow.params.params_key(),
            seed=uow.seed,
            split_id=uow.split_id,
            code_version=_git_version(),
            input_manifest={"window": uow.window_id},
            uncertainty=dist.provenance,
        )
        per_time.append(PerTimeProduct(t, base, derived, unit.eval_points, prov))
    return Product(
        per_time=per_time,
        run_manifest={"window": uow.window_id, "method": uow.method_name},
    )
```

Update imports at the top of `solve.py`: drop `GridBasis`, `PersistedFields`, `eval_rows_in_grid_basis`, `reduce_with_basis` (now used only inside the strategy); add `from sverdrup.distributions.reduction import select_reduction`. Keep `PersistedDistribution` (still constructed) and `_reduce_derived`/`_shrunk_grid`/`_git_version`/`_ensemble_at`-free of the deleted base/eval helpers. Delete `_reduce` and `_eval_points` (their logic now lives in the strategy); keep `_reduce_derived` unchanged. Remove the now-unused `_ensemble_at` if nothing else calls it (the EmpiricalReduction inlines it).

- [ ] **Step 6: Run reduction tests + full suite**

Run: `pixi run test tests/unit/test_reduction.py -v` → PASS
Run: `pixi run test -q` → `129 passed, 2 skipped`

- [ ] **Step 7: Commit**

```bash
git add src/sverdrup/distributions/reduction.py src/sverdrup/application/solve.py \
        src/sverdrup/methods/oi.py tests/unit/test_reduction.py
pixi run pre-commit run --files src/sverdrup/distributions/reduction.py \
        src/sverdrup/application/solve.py src/sverdrup/methods/oi.py \
        tests/unit/test_reduction.py
git commit -m "refactor: per-operator ReductionStrategy selected by representation (OI path unchanged)"
```

---

### Task 2: Relocate the coherence seam to CoherentMemberDriver (§4a+b) — OI behavior-identical

**Goal:** Introduce the `CoherentMemberDriver` seam at `_coherent_member`, dispatched by the persisted `sampler_spec`; the OI low-rank path becomes the `LowRankSharedBasis` instance (verbatim math). Widen `BlendInput.distribution` to the abstract `PredictiveDistribution`. Keep the historical `MemberSeededZr` driver intact.

**Files:**
- Modify: `src/sverdrup/distributions/coherent.py` (add `CoherentMemberDriver`, `LowRankSharedBasis`, `select_driver`; relocate `_nearest`/`_support_points`)
- Modify: `src/sverdrup/distributions/blend.py` (`_coherent_member` delegates; `BlendInput` type widens; import moved helpers)
- Test: `tests/test_coherent_driver_seam.py`

**Acceptance Criteria:**
- [ ] `select_driver("lowrank+diag")` returns a `LowRankSharedBasis`.
- [ ] `LowRankSharedBasis.crossfaded_member` produces the **same** array as the pre-refactor `_coherent_member` for the `_tiles()` fixture, same member index/noise.
- [ ] `MemberSeededZr` / `CoherentSampler.realize_one` / `coherent_structured_field` still import and pass their existing tests.
- [ ] Full Phase-2 suite green.

**Verify:** `pixi run test -q` → `129 passed, 2 skipped`; plus `pixi run test tests/test_coherent_driver_seam.py -v`.

**Steps:**

- [ ] **Step 1: Write the failing test** — `tests/test_coherent_driver_seam.py`

```python
"""CoherentMemberDriver seam: low-rank driver reproduces the inlined _coherent_member."""

from __future__ import annotations

import numpy as np

from sverdrup.distributions.blend import BlendInput, BlendOperator, partition_weights
from sverdrup.distributions.coherent import (
    LowRankSharedBasis,
    NoiseSpec,
    coherent_structured_field,
    diagonal_noise,
    select_driver,
)
from tests.test_blend_general_path import _persisted_struct, _tiles


def test_select_driver_lowrank():
    # Behavior: the "lowrank+diag" representation selects the shared-basis driver.
    # Bug caught: a missing/renamed tag silently falls back to the wrong driver.
    assert isinstance(select_driver("lowrank+diag"), LowRankSharedBasis)


def test_lowrank_driver_matches_inlined_member():
    # Behavior: the relocated driver yields the byte-identical coherent member the inlined
    #   _coherent_member produced (mean crossfade + shared-basis struct + coherent diagonal).
    # Bug caught: any drift in the relocation changes Stage-A blend samples -> red gate.
    target, left, right = _tiles()
    parts = [
        BlendInput(_persisted_struct(left.grid, 1), left),
        BlendInput(_persisted_struct(right.grid, 2), right),
    ]
    pts = target.points(0.0)
    noise = NoiseSpec(method="oi", params_key="p", lattice_step=0.25)
    w = partition_weights([p.tile for p in parts], pts)

    # reference: the exact arithmetic the pre-refactor _coherent_member ran
    from sverdrup.distributions.blend import _nearest

    means = np.zeros((2, pts.shape[0]))
    sqd = np.zeros((2, pts.shape[0]))
    cols = []
    for i, p in enumerate(parts):
        d = p.distribution
        idx = _nearest(d.grid, pts, d.time_days)
        means[i] = d.fields.mean.ravel()[idx]
        cols.append(d.fields.factor[idx] * (w[i] > 0)[:, None])
        sqd[i] = np.sqrt(d.fields.residual[idx])
    ref = (
        (w * means).sum(axis=0)
        + coherent_structured_field(cols, w, 4, noise)
        + (w * sqd).sum(axis=0) * diagonal_noise(pts, 4, noise)
    )

    got = LowRankSharedBasis().crossfaded_member(parts, pts, w, 4, noise)
    np.testing.assert_allclose(got, ref, rtol=1e-12)
```

- [ ] **Step 2: Run — confirm fail**

Run: `pixi run test tests/test_coherent_driver_seam.py -v`
Expected: FAIL — `ImportError: cannot import name 'LowRankSharedBasis'`.

- [ ] **Step 3: Relocate `_nearest`/`_support_points` into `coherent.py`** (so drivers can use them without a blend→coherent→blend cycle). Add to `coherent.py`:

```python
from sverdrup.core.grid import GridSpec, PointSet


def _support_points(support: GridSpec | PointSet, time_days: float) -> Points:
    """Return ``(n, 3)`` points for either support kind."""
    if isinstance(support, PointSet):
        return support.points()
    return support.points(time_days)


def _nearest(grid: GridSpec | PointSet, pts: Points, t: float) -> np.ndarray:
    """Return the nearest support-node index for each point in ``pts`` at time ``t``."""
    nodes = grid.points() if isinstance(grid, PointSet) else grid.points(t)
    return np.asarray(
        np.argmin(np.linalg.norm(pts[:, None, :2] - nodes[None, :, :2], axis=2), axis=1)
    )
```

In `blend.py`, delete the local `_support_points`/`_nearest` definitions and import them:
`from sverdrup.distributions.coherent import (..., _nearest, _support_points)`. (`_constituent_moments` and `covariance`/`sample` keep calling `_nearest`/`_support_points` unchanged.)

- [ ] **Step 4: Add the driver Protocol + low-rank instance** to `coherent.py`

```python
@runtime_checkable
class CoherentMemberDriver(Protocol):
    """Relocated coherence seam: one cross-tile-coherent, weight-crossfaded realization."""

    def crossfaded_member(
        self,
        parts: Sequence[Any],
        pts: Points,
        weights: np.ndarray,
        member_index: int,
        noise: NoiseSpec,
    ) -> np.ndarray:
        """Realize one coherent member over ``pts`` from the constituents + global noise."""
        ...


class LowRankSharedBasis:
    """OI driver: mean crossfade + shared-overlap-basis structured field + coherent diagonal."""

    def crossfaded_member(
        self, parts, pts, weights, member_index, noise
    ) -> np.ndarray:
        n = pts.shape[0]
        means = np.zeros((len(parts), n))
        sqd = np.zeros((len(parts), n))
        cols: list[np.ndarray] = []
        for i, p in enumerate(parts):
            d = p.distribution
            idx = _nearest(d.grid, pts, d.time_days)
            means[i] = d.fields.mean.ravel()[idx]
            cols.append(d.fields.factor[idx] * (weights[i] > 0)[:, None])
            sqd[i] = np.sqrt(d.fields.residual[idx])
        mean_blend = (weights * means).sum(axis=0)
        diag_amp = (weights * sqd).sum(axis=0)
        struct = coherent_structured_field(cols, weights, member_index, noise)
        diag = diag_amp * diagonal_noise(pts, member_index, noise)
        return np.asarray(mean_blend + struct + diag)


_DRIVERS: dict[str, type] = {"lowrank+diag": LowRankSharedBasis}


def select_driver(sampler_spec: str) -> CoherentMemberDriver:
    """Pick the coherence driver by the persisted representation tag (never by method)."""
    return cast(CoherentMemberDriver, _DRIVERS[sampler_spec]())
```

Add `from typing import Any, cast` and `Sequence` imports as needed. Leave `MemberSeededZr`, `StructuredNoiseSource`, `CoherentSampler`, `realize_one`, `coherent_structured_field`, `diagonal_noise` untouched (historical/single-tile + shared by the low-rank driver).

- [ ] **Step 5: Delegate in `blend.py`** — replace `BlendedDistribution._coherent_member` body with:

```python
    def _coherent_member(self, member_index: int, pts: Points) -> np.ndarray:
        """Realize one cross-tile-coherent member via the driver selected by sampler_spec."""
        noise = self._noise
        if noise is None:
            raise RuntimeError("general path needs a NoiseSpec (set by BlendOperator)")
        parts = self._parts
        w = partition_weights([p.tile for p in parts], pts)
        driver = select_driver(parts[0].distribution.fields.sampler_spec)
        return driver.crossfaded_member(parts, pts, w, member_index, noise)
```

Update the `coherent` import in `blend.py` to include `select_driver` (and drop `coherent_structured_field`/`diagonal_noise`/`CoherentSampler` from blend's imports if now unused there — `CoherentSampler` is still referenced by the `_sampler` field default, keep it). Widen `BlendInput`:

```python
@dataclass
class BlendInput:
    """One constituent: a predictive distribution (grid or PointSet) plus its tile geometry."""

    distribution: PredictiveDistribution  # widened from PersistedDistribution | PersistedPoints
    tile: Tile
```

Add `from sverdrup.core.distribution import PredictiveDistribution`. (The driver reads `.fields`/`.grid`/`.time_days` via duck typing; `PersistedDistribution`/`PersistedPoints`/`PrecisionDistribution` all expose them.)

- [ ] **Step 6: Run the seam test + full suite**

Run: `pixi run test tests/test_coherent_driver_seam.py -v` → PASS
Run: `pixi run test -q` → `129 passed, 2 skipped`

- [ ] **Step 7: Commit**

```bash
git add src/sverdrup/distributions/coherent.py src/sverdrup/distributions/blend.py \
        tests/test_coherent_driver_seam.py
pixi run pre-commit run --files src/sverdrup/distributions/coherent.py \
        src/sverdrup/distributions/blend.py tests/test_coherent_driver_seam.py
git commit -m "refactor: relocate coherence seam to CoherentMemberDriver (LowRankSharedBasis), dispatch by sampler_spec"
```

---

### Task 3: Stage-A regression gate [USER-ORDERED GATE]

**Goal:** Prove the three-seam generalization preserved OI behavior exactly — the full Phase-2 suite stays 129 passed / 2 skipped with OI flowing through the relocated reduction + coherence seams.

> **USER-ORDERED GATE — NON-SKIPPABLE.** This task was requested by the user in the current conversation. It MUST NOT be closed by walking around it, by declaring it "verified inline", or by substituting a cheaper check. Close only after every item in `acceptanceCriteria` has been re-validated independently, with output captured. If OI behavior changed, **surface it — do NOT adjust the Phase-2 tests to make the refactor pass** (a changed test here means the generalization altered OI; escalate per spec §8).

**Files:**
- Modify: none (verification task; fixes land in Tasks 1–2 if red)
- Test: the whole suite, especially `tests/test_phase2_stage_a.py`, `tests/test_phase2_stage_b.py`, `tests/test_coherent_sampler.py`, `tests/test_cross_seam_derivative_gate.py`, `tests/test_blend_general_path.py`, `tests/test_blend_cheap_vs_sample.py`, `tests/test_eval_point_blend.py`, `tests/unit/test_persisted.py`

**Acceptance Criteria:**
- [ ] `pixi run test -q` reports exactly `129 passed, 2 skipped`.
- [ ] `pixi run typecheck` and `pixi run lint` clean.
- [ ] No Phase-2 test file was edited to accommodate the refactor (verified by `git diff --stat main -- tests/` showing only the two NEW Stage-A test files added in Tasks 1–2).

**Verify:** `pixi run test -q && pixi run typecheck && pixi run lint` → all green / `129 passed, 2 skipped`; `git diff --name-only main -- tests/` → only `tests/unit/test_reduction.py` and `tests/test_coherent_driver_seam.py` are new, no existing Phase-2 test modified.

**Steps:**

- [ ] **Step 1: Run the full suite with captured output**

Run: `pixi run test -q`
Expected: `129 passed, 2 skipped`. If any Phase-2 test is red → the generalization changed OI behavior. Fix the implementation in Task 1/2; **do not edit the test**.

- [ ] **Step 2: Confirm no Phase-2 tests were touched**

Run: `git diff --name-only main -- tests/`
Expected: only the two new files. If an existing test changed, revert it and fix the source.

- [ ] **Step 3: Typecheck + lint**

Run: `pixi run typecheck` → `Success`
Run: `pixi run lint` → no errors

- [ ] **Step 4: Tag the gate (commit a marker)**

```bash
git commit --allow-empty -m "test: Stage-A gate green — OI through relocated seams reproduces Phase-2 (129/2)"
```

---

## Stage B — add the GMRF method

### Task 4: GMRF grid topology, the bilinear primitive, and the Projection seam

**Goal:** Build the regular-grid `(κ²−Δ)` α=2 sparse precision `Q` (scalar or κ-field), the single bilinear interpolation primitive, the `Projection` abstraction (`GridIdentityProjection` + `BilinearProjection`), and the κ↔range mapping — precision-node space and output-grid space kept distinct.

**Files:**
- Modify: `pixi.toml` (add `scikit-sparse`)
- Create: `src/sverdrup/methods/gmrf_grid.py`
- Test: `tests/unit/test_gmrf_grid.py`

**Acceptance Criteria:**
- [ ] `matern_precision(grid, kappa, tau)` returns a symmetric SPD `scipy.sparse.csc_matrix` of shape `(n, n)`, `n = ny*nx`, 5-point connectivity (interior rows have ≤9 nonzeros after squaring the `(κ²−Δ)` stencil).
- [ ] `bilinear_weights(grid, pts)` returns a sparse `(k, n)` operator whose rows sum to 1 and have ≤4 nonzeros; for a point exactly on a node the row is a unit selector.
- [ ] `GridIdentityProjection(grid).matrix` is the `(n, n)` identity-on-nodes; `BilinearProjection(grid, pts).matrix == bilinear_weights(grid, pts)`.
- [ ] `kappa_from_range(range_km)` and `range_from_kappa(kappa)` round-trip (`range = sqrt(8·ν)/κ`, ν=1).
- [ ] `scikit-sparse` resolves under pixi (or is pinned to `[target.linux-64.dependencies]`).

**Verify:** `pixi run test tests/unit/test_gmrf_grid.py -v` → all pass.

**Steps:**

- [ ] **Step 1: Add the dependency**

```bash
pixi add scikit-sparse
```
If this fails with `No candidates were found` on osx-arm64:
```bash
pixi add --platform linux-64 scikit-sparse
```
(then it lives under `[target.linux-64.dependencies]`; GMRF tests `importorskip` so the suite still collects on macOS).

- [ ] **Step 2: Write the failing test** — `tests/unit/test_gmrf_grid.py`

```python
"""Regular-grid GMRF topology: (kappa^2 - Laplacian)^2 precision, bilinear W, projections."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("sksparse")  # noqa: E402

from scipy import sparse  # noqa: E402

from sverdrup.core.grid import GridSpec  # noqa: E402
from sverdrup.methods.gmrf_grid import (  # noqa: E402
    BilinearProjection,
    GridIdentityProjection,
    bilinear_weights,
    kappa_from_range,
    matern_precision,
    range_from_kappa,
)


def _grid():
    return GridSpec.lonlat(np.linspace(0.0, 9.0, 10), np.linspace(0.0, 9.0, 10))


def test_precision_is_symmetric_spd():
    # Behavior: Q = (kappa^2 I - Delta)^2 (+ tau scaling) is symmetric positive definite.
    # Bug caught: an asymmetric stencil assembly (wrong neighbour weighting) -> CHOLMOD fails.
    q = matern_precision(_grid(), kappa=0.3, tau=1.0)
    assert sparse.issparse(q)
    assert (abs(q - q.T)).max() < 1e-10
    # SPD: smallest eigenvalue of a small dense copy > 0
    w = np.linalg.eigvalsh(q.toarray())
    assert w.min() > 0.0


def test_bilinear_weights_partition_and_stencil():
    # Behavior: W rows sum to 1 with <=4 nonzeros; on-node points are unit selectors.
    # Bug caught: a normalization bug biases the eval-point mean; a wide stencil breaks
    #   the Takahashi adjacency precondition.
    g = _grid()
    pts = np.array([[2.5, 3.5, 0.0], [4.0, 4.0, 0.0]])  # off-node, then on-node
    w = bilinear_weights(g, pts)
    assert w.shape == (2, 100)
    np.testing.assert_allclose(np.asarray(w.sum(axis=1)).ravel(), 1.0, rtol=1e-12)
    assert w[0].nnz <= 4
    assert w[1].nnz == 1  # exact node -> selector


def test_projection_identity_and_bilinear():
    # Behavior: gridded block is W=identity-on-nodes; off-grid is the bilinear W.
    # Bug caught: baking the grid block into the operator instead of going through W.
    g = _grid()
    ident = GridIdentityProjection(g).matrix
    assert ident.shape == (100, 100)
    assert (ident - sparse.identity(100)).nnz == 0
    pts = np.array([[2.5, 3.5, 0.0]])
    assert (BilinearProjection(g, pts).matrix - bilinear_weights(g, pts)).nnz == 0


def test_kappa_range_roundtrip():
    # Behavior: range = sqrt(8*nu)/kappa with nu=1 round-trips kappa<->range.
    # Bug caught: an off-by-sqrt(2) in the SPDE range mapping mis-sizes correlation.
    for rng in (50.0, 200.0, 800.0):
        assert range_from_kappa(kappa_from_range(rng)) == pytest.approx(rng, rel=1e-9)
```

- [ ] **Step 3: Run — confirm fail**

Run: `pixi run test tests/unit/test_gmrf_grid.py -v`
Expected: FAIL — `ModuleNotFoundError: sverdrup.methods.gmrf_grid`.

- [ ] **Step 4: Implement `gmrf_grid.py`**

```python
"""Regular-grid Matérn SPDE topology: precision stencil, bilinear projection (spec §5.1).

Precision-node space (the GMRF lattice) and output-grid space are kept conceptually
distinct even though they coincide here. Every field/covariance is read off the precision
through a ``Projection``: the gridded block is ``W = identity-on-nodes``; off-grid eval is
``W = bilinear``. A later FEM phase supplies a different projection + mesh assembly only.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import sparse  # type: ignore[import-untyped]

from sverdrup.core.grid import GridSpec
from sverdrup.core.types import Points

_DEG2KM = 111.195
_NU = 1.0  # alpha = 2 in 2-D -> nu = alpha - d/2 = 1


def kappa_from_range(range_km: float) -> float:
    """Return κ for an empirical correlation range (km): ``range = sqrt(8ν)/κ`` (ν=1)."""
    return float(np.sqrt(8.0 * _NU) / range_km)


def range_from_kappa(kappa: float) -> float:
    """Return the empirical correlation range (km) for κ (inverse of :func:`kappa_from_range`)."""
    return float(np.sqrt(8.0 * _NU) / kappa)


def _node_spacing_km(grid: GridSpec) -> tuple[np.ndarray, np.ndarray]:
    """Per-node (dx, dy) spacing in km over the grid (geographic uses cos-lat for dx)."""
    lon, lat = grid._lonlat_nodes()
    dy = np.full(grid.shape, np.gradient(grid.y).mean() * _DEG2KM)
    dx = np.gradient(grid.x).mean() * _DEG2KM * np.cos(np.deg2rad(lat))
    return dx, dy


def _laplacian(grid: GridSpec) -> sparse.csc_matrix:
    """5-point finite-difference Laplacian (Neumann edges) on the grid nodes, in km^-2."""
    ny, nx = grid.shape
    n = ny * nx
    dx, dy = _node_spacing_km(grid)
    dx2 = (dx.ravel()) ** 2
    dy2 = (dy.ravel()) ** 2
    rows, cols, vals = [], [], []

    def idx(j, i):
        return j * nx + i

    for j in range(ny):
        for i in range(nx):
            c = idx(j, i)
            diag = 0.0
            for dj, di, h2 in ((0, 1, dx2), (0, -1, dx2), (1, 0, dy2), (-1, 0, dy2)):
                jj, ii = j + dj, i + di
                if 0 <= jj < ny and 0 <= ii < nx:
                    w = 1.0 / h2[c]
                    rows.append(c)
                    cols.append(idx(jj, ii))
                    vals.append(w)
                    diag -= w
            rows.append(c)
            cols.append(c)
            vals.append(diag)
    return sparse.csc_matrix((vals, (rows, cols)), shape=(n, n))


def matern_precision(
    grid: GridSpec, kappa: float | np.ndarray, tau: float
) -> sparse.csc_matrix:
    """Assemble the Matérn SPDE precision ``Q = (1/tau)·(κ²I − Δ)²`` (α=2, ν=1).

    Args:
        grid: The regular grid the lattice lives on.
        kappa: Scalar κ, or a ``(ny, nx)`` κ field (nonstationary; spatially-varying coeffs).
        tau: Marginal-variance scaling (larger τ -> smaller precision -> larger variance).

    Returns:
        A symmetric SPD ``(n, n)`` CSC precision over the ``n = ny*nx`` nodes.
    """
    n = grid.shape[0] * grid.shape[1]
    lap = _laplacian(grid)
    if np.isscalar(kappa):
        k2 = sparse.identity(n, format="csc") * float(kappa) ** 2
    else:
        k2 = sparse.diags(np.asarray(kappa).ravel() ** 2, format="csc")
    a = k2 - lap  # (κ²I − Δ)
    q = (a.T @ a) / float(tau)
    return sparse.csc_matrix(0.5 * (q + q.T))  # symmetrize against round-off


def bilinear_weights(grid: GridSpec, pts: Points) -> sparse.csr_matrix:
    """Return the sparse ``(k, n)`` bilinear interpolation operator grid-nodes -> ``pts``.

    Rows sum to 1; a point on a node is a unit selector (<=4 nonzeros otherwise). This is
    the ONE primitive feeding both ``A`` (grid->obs conditioning) and ``W`` (grid->eval).
    """
    lon, lat = grid._lonlat_nodes()
    xs, ys = lon[0, :], lat[:, 0]
    nx, ny = xs.size, ys.size
    k = pts.shape[0]
    rows, cols, vals = [], [], []
    for r in range(k):
        ix = int(np.clip(np.searchsorted(xs, pts[r, 0]) - 1, 0, nx - 2))
        iy = int(np.clip(np.searchsorted(ys, pts[r, 1]) - 1, 0, ny - 2))
        tx = 0.0 if xs[ix + 1] == xs[ix] else (pts[r, 0] - xs[ix]) / (xs[ix + 1] - xs[ix])
        ty = 0.0 if ys[iy + 1] == ys[iy] else (pts[r, 1] - ys[iy]) / (ys[iy + 1] - ys[iy])
        tx = float(np.clip(tx, 0.0, 1.0))
        ty = float(np.clip(ty, 0.0, 1.0))
        for dj, wy in ((0, 1 - ty), (1, ty)):
            for di, wx in ((0, 1 - tx), (1, tx)):
                wgt = wx * wy
                if wgt > 0:
                    rows.append(r)
                    cols.append((iy + dj) * nx + (ix + di))
                    vals.append(wgt)
    w = sparse.csr_matrix((vals, (rows, cols)), shape=(k, nx * ny))
    # renormalize rows (guards clipped/edge points) so each row sums to 1
    rs = np.asarray(w.sum(axis=1)).ravel()
    rs[rs == 0] = 1.0
    return sparse.diags(1.0 / rs) @ w


@dataclass(frozen=True)
class GridIdentityProjection:
    """The gridded block read-off: ``W = identity-on-nodes`` (not baked into the operator)."""

    grid: GridSpec

    @property
    def matrix(self) -> sparse.csr_matrix:
        """Return the ``(n, n)`` identity projection over the grid nodes."""
        n = self.grid.shape[0] * self.grid.shape[1]
        return sparse.identity(n, format="csr")


@dataclass(frozen=True)
class BilinearProjection:
    """The off-grid read-off: bilinear ``W`` from grid nodes to arbitrary points."""

    grid: GridSpec
    pts: Points

    @property
    def matrix(self) -> sparse.csr_matrix:
        """Return the ``(k, n)`` bilinear projection to ``pts``."""
        return bilinear_weights(self.grid, self.pts)
```

- [ ] **Step 5: Run the topology tests**

Run: `pixi run test tests/unit/test_gmrf_grid.py -v` → PASS

- [ ] **Step 6: Commit**

```bash
git add pixi.toml pixi.lock src/sverdrup/methods/gmrf_grid.py tests/unit/test_gmrf_grid.py
pixi run pre-commit run --files src/sverdrup/methods/gmrf_grid.py tests/unit/test_gmrf_grid.py
git commit -m "feat: GMRF grid topology — Matern (kappa^2-Delta)^2 precision, bilinear primitive, Projection seam"
```

---

### Task 5: Sparse Cholesky + Takahashi selective inverse [USER-ORDERED GATE — math-bug oracle]

**Goal:** Wrap the CHOLMOD simplicial factor (one `L` for sampling, mean-solve, and `cov`) and hand-roll the Takahashi selective inverse for `diag(Q⁻¹)` + adjacent-node entries over the `L+Lᵀ` pattern, with a deterministic recorded permutation and an explicit adjacency-precondition assertion.

> **USER-ORDERED GATE — NON-SKIPPABLE.** This task was requested by the user in the current conversation. It MUST NOT be closed by walking around it, by declaring it "verified inline", or by substituting a cheaper check. Close only after every item in `acceptanceCriteria` has been re-validated independently, with output captured. The Takahashi correctness check is pinned to a **dense `Q⁻¹` small-grid oracle**: if it goes red, that is a **math bug to fix, not a tolerance to loosen**.

**Files:**
- Create: `src/sverdrup/methods/gmrf_linalg.py`
- Test: `tests/unit/test_gmrf_linalg.py`

**Acceptance Criteria:**
- [ ] `GMRFFactor(Q)` factors via CHOLMOD simplicial mode and records a deterministic permutation `P` (`factor(Q)` twice → identical `P`).
- [ ] `factor.sample(w)` returns `L⁻ᵀ w` (zero-mean draw); `factor.solve(b)` returns `Q⁻¹ b`.
- [ ] `factor.selective_inverse()` returns `diag(Q⁻¹)` matching `np.linalg.inv(Q.toarray())` diagonal to `rtol=1e-9` on a 6×6 grid.
- [ ] Selective-inverse entries for **adjacent** nodes match the dense `Q⁻¹` entries to `rtol=1e-9`.
- [ ] `assert_adjacency_in_pattern(Q)` raises if any 5-point-adjacent node pair is absent from the `L+Lᵀ` selective-inverse pattern (passes for the α=2 stencil).

**Verify:** `pixi run test tests/unit/test_gmrf_linalg.py -v` → all pass (esp. `test_takahashi_diag_matches_dense_inverse` and `test_takahashi_adjacent_entries_match_dense`).

**Steps:**

- [ ] **Step 1: Write the failing test** — `tests/unit/test_gmrf_linalg.py`

```python
"""Sparse Cholesky + Takahashi selective inverse vs the dense Q^-1 oracle."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("sksparse")  # noqa: E402

from sverdrup.core.grid import GridSpec  # noqa: E402
from sverdrup.methods.gmrf_grid import matern_precision  # noqa: E402
from sverdrup.methods.gmrf_linalg import GMRFFactor  # noqa: E402


def _q(nside=6):
    g = GridSpec.lonlat(np.arange(nside, dtype=float), np.arange(nside, dtype=float))
    return g, matern_precision(g, kappa=0.4, tau=1.0)


def test_permutation_is_deterministic():
    # Behavior: the fill-reducing permutation is reproducible across factorizations.
    # Bug caught: a nondeterministic ordering breaks reproducibility-from-provenance.
    _, q = _q()
    assert np.array_equal(GMRFFactor(q).permutation, GMRFFactor(q).permutation)


def test_solve_matches_dense():
    # Behavior: factor.solve(b) == Q^-1 b.
    # Bug caught: mishandling the permutation in the solve path.
    _, q = _q()
    b = np.arange(q.shape[0], dtype=float)
    np.testing.assert_allclose(GMRFFactor(q).solve(b), np.linalg.solve(q.toarray(), b),
                               rtol=1e-9)


def test_takahashi_diag_matches_dense_inverse():
    # Behavior: selective inverse diagonal == diag(Q^-1) exactly (EXACT marginal variance).
    # Bug caught: ANY error in the Takahashi recursion -> calibration silently dishonest.
    #   A red here is a math bug to fix, never a tolerance to loosen.
    _, q = _q()
    diag = GMRFFactor(q).selective_inverse_diag()
    np.testing.assert_allclose(diag, np.diag(np.linalg.inv(q.toarray())), rtol=1e-9)


def test_takahashi_adjacent_entries_match_dense():
    # Behavior: selective inverse entries between 5-point-adjacent nodes == dense Q^-1.
    # Bug caught: W (4-node) eval var and firstdifference adjacent-cov read wrong entries.
    g, q = _q()
    fac = GMRFFactor(q)
    sinv = fac.selective_inverse()  # sparse, on the L+L^T pattern
    dense = np.linalg.inv(q.toarray())
    nx = g.shape[1]
    pairs = [(0, 1), (0, nx), (7, 8), (7, 7 + nx)]
    for a, b in pairs:
        assert sinv[a, b] == pytest.approx(dense[a, b], rel=1e-9)


def test_sample_is_zero_mean_with_right_covariance():
    # Behavior: L^-T w draws have covariance ~ Q^-1 (checked on the diagonal).
    # Bug caught: sampling with L instead of L^-T inverts the covariance scale.
    _, q = _q()
    fac = GMRFFactor(q)
    rng = np.random.default_rng(0)
    draws = np.stack([fac.sample(rng.standard_normal(q.shape[0])) for _ in range(4000)])
    emp = draws.var(axis=0)
    np.testing.assert_allclose(emp, np.diag(np.linalg.inv(q.toarray())), rtol=0.15)


def test_adjacency_precondition_holds_for_alpha2():
    # Behavior: every 5-point-adjacent pair lies inside the selective-inverse pattern.
    # Bug caught: a future wider kappa-stencil would silently break eval var / cancellation.
    from sverdrup.methods.gmrf_linalg import assert_adjacency_in_pattern

    g, q = _q()
    assert_adjacency_in_pattern(q, g.shape)  # must not raise
```

- [ ] **Step 2: Run — confirm fail**

Run: `pixi run test tests/unit/test_gmrf_linalg.py -v`
Expected: FAIL — `ModuleNotFoundError: sverdrup.methods.gmrf_linalg`.

- [ ] **Step 3: Implement `gmrf_linalg.py`**

```python
"""CHOLMOD simplicial factor + hand-rolled Takahashi selective inverse (spec §5.1).

One factor L serves sampling (L^-T w), the posterior mean (full solve), and cov blocks.
CHOLMOD has no selective inverse, so diag(Q^-1) and near-neighbour Q^-1 entries are
computed by the Takahashi recursion over the L+L^T sparsity pattern.
"""

from __future__ import annotations

import numpy as np
from scipy import sparse  # type: ignore[import-untyped]
from sksparse.cholmod import cholesky  # type: ignore[import-untyped]


class GMRFFactor:
    """A cached CHOLMOD simplicial Cholesky of an SPD sparse precision ``Q``."""

    def __init__(self, q: sparse.csc_matrix) -> None:
        """Factor ``Q = P^T L L^T P`` in simplicial mode; record the permutation ``P``.

        Args:
            q: Symmetric positive-definite sparse precision (CSC).
        """
        self._q = q.tocsc()
        # ordering_method fixed -> deterministic permutation; simplicial -> L pattern usable.
        self._factor = cholesky(
            self._q, ordering_method="amd", mode="simplicial"
        )
        self.permutation = np.asarray(self._factor.P())

    def solve(self, b: np.ndarray) -> np.ndarray:
        """Return ``Q^-1 b`` via the cached factor (permutation handled internally)."""
        return np.asarray(self._factor(b))

    def sample(self, w: np.ndarray) -> np.ndarray:
        """Return one zero-mean draw ``L^-T w`` (so ``Cov = Q^-1``).

        ``apply_Pt(solve_Lt(w))`` undoes the fill-reducing permutation after the
        upper-triangular solve, giving a draw in the original node order.
        """
        return np.asarray(self._factor.apply_Pt(self._factor.solve_Lt(w)))

    def _l_perm(self) -> tuple[sparse.csc_matrix, np.ndarray]:
        """Return ``(L, P)`` with ``L`` the simplicial factor in permuted order."""
        ld = self._factor.L_D()  # (L, D) with LDL^T; fold D into L for LL^T
        if isinstance(ld, tuple):
            l_chol = self._factor.L()
        else:
            l_chol = self._factor.L()
        return l_chol.tocsc(), self.permutation

    def selective_inverse(self) -> sparse.csr_matrix:
        """Return the Takahashi selective inverse of ``Q`` on the ``L+L^T`` pattern (orig order)."""
        l_chol, perm = self._l_perm()
        sinv_p = _takahashi(l_chol)  # in permuted order
        # map back to original node order: Sigma[i,j] = Sinv_p[pos[i], pos[j]]
        inv_perm = np.argsort(perm)
        sinv_p = sinv_p.tocoo()
        rows = inv_perm[sinv_p.row]
        cols = inv_perm[sinv_p.col]
        n = l_chol.shape[0]
        return sparse.csr_matrix((sinv_p.data, (rows, cols)), shape=(n, n))

    def selective_inverse_diag(self) -> np.ndarray:
        """Return ``diag(Q^-1)`` (exact marginal variance) in original node order."""
        return np.asarray(self.selective_inverse().diagonal())


def _takahashi(l_chol: sparse.csc_matrix) -> sparse.csc_matrix:
    """Takahashi recursion: selective inverse Σ on the lower pattern of ``L`` (LL^T factor).

    Σ_jj = 1/L_jj^2 - (1/L_jj) Σ_{k>j, L_kj!=0} L_kj Σ_kj
    Σ_ij = -(1/L_jj) Σ_{k>j, L_kj!=0} L_kj Σ_ik   (i in pattern, i>j)
    Processed in reverse column order; only entries on the L pattern are computed.
    """
    n = l_chol.shape[0]
    l_csc = l_chol.tocsc()
    diagL = l_csc.diagonal()
    # pattern: rows below the diagonal per column
    sigma = sparse.lil_matrix((n, n))
    indptr, indices, data = l_csc.indptr, l_csc.indices, l_csc.data
    col_rows = [indices[indptr[j] : indptr[j + 1]] for j in range(n)]
    col_vals = [data[indptr[j] : indptr[j + 1]] for j in range(n)]
    for j in range(n - 1, -1, -1):
        rows = col_rows[j]
        vals = col_vals[j]
        below = [(r, v) for r, v in zip(rows, vals, strict=False) if r > j]
        inv_ljj = 1.0 / diagL[j]
        # off-diagonals Σ_ij for i in the column pattern below j
        for i, _ in below:
            acc = 0.0
            for k, lkj in below:
                acc += lkj * (sigma[max(i, k), min(i, k)] if k != i else sigma[k, k])
            sij = -inv_ljj * acc
            sigma[i, j] = sij
            sigma[j, i] = sij
        acc = 0.0
        for k, lkj in below:
            acc += lkj * sigma[k, j]
        sigma[j, j] = inv_ljj * inv_ljj - inv_ljj * acc
    return sigma.tocsc()


def assert_adjacency_in_pattern(q: sparse.csc_matrix, shape: tuple[int, int]) -> None:
    """Raise if any 5-point-adjacent node pair is outside ``Q``'s (and so Σ's) pattern.

    The bilinear ``W`` couples a point to its 4 surrounding nodes and ``firstdifference``
    reads ``cov`` between adjacent nodes; both require those Σ entries to be in the
    selective-inverse pattern. For the α=2 ``(κ²−Δ)²`` stencil the Q pattern already
    contains all 5-point neighbours (and their squares), so this holds.
    """
    ny, nx = shape
    qcoo = q.tocoo()
    present = set(zip(qcoo.row.tolist(), qcoo.col.tolist(), strict=False))
    for j in range(ny):
        for i in range(nx):
            c = j * nx + i
            for dj, di in ((0, 1), (1, 0)):
                jj, ii = j + dj, i + di
                if jj < ny and ii < nx:
                    nb = jj * nx + ii
                    if (c, nb) not in present:
                        raise AssertionError(
                            f"adjacent pair ({c},{nb}) absent from Q pattern — "
                            "wider stencil would break eval var / cancellation"
                        )
```

> **Implementation note for the executor:** the dense Takahashi loop above is O(n·band) and fine for test grids and modest tiles. If a Stage-B tile is large enough that the Python triple-loop is slow, vectorize per-column over the `below` pattern with numpy gathers — keep the recursion identical and re-run `test_takahashi_diag_matches_dense_inverse` to prove no math changed. Do **not** swap in an approximate selective inverse.

- [ ] **Step 4: Run the linalg tests (the math-bug oracle)**

Run: `pixi run test tests/unit/test_gmrf_linalg.py -v` → PASS. If `test_takahashi_diag_matches_dense_inverse` or `test_takahashi_adjacent_entries_match_dense` is red, fix the recursion — never loosen `rtol`.

- [ ] **Step 5: Commit**

```bash
git add src/sverdrup/methods/gmrf_linalg.py tests/unit/test_gmrf_linalg.py
pixi run pre-commit run --files src/sverdrup/methods/gmrf_linalg.py tests/unit/test_gmrf_linalg.py
git commit -m "feat: CHOLMOD simplicial factor + hand-rolled Takahashi selective inverse (dense-Q^-1 oracle)"
```

---

### Task 6: GMRFCovarianceOperator + MaternGMRF (temporal-taper conditioning)

**Goal:** Implement the EXACT sparse-precision operator (`cov`/`marginal_var`/`posterior_sample` + `posterior_mean`, read off the precision via `Projection`) and the `MaternGMRF` method conditioning on the space-time obs window via the temporal taper into R; register `"gmrf"`.

**Files:**
- Create: `src/sverdrup/methods/gmrf.py`
- Modify: `src/sverdrup/methods/registry.py`
- Test: `tests/unit/test_gmrf_method.py`

**Acceptance Criteria:**
- [ ] `GMRFCovarianceOperator.fidelity is CovFidelity.EXACT` and `.representation == "sparse-precision"`.
- [ ] `marginal_var(grid_points)` equals `selective_inverse_diag` (exact), and equals dense `diag(Q_post⁻¹)` on a small grid (`rtol=1e-8`).
- [ ] `posterior_mean` solves `Q_post μ = Aᵀ R⁻¹ y`; conditioning on a single obs pulls the field toward it.
- [ ] Off-grid `marginal_var(eval_pts)` uses `diag(W Σ Wᵀ)` from the selective-inverse stencil entries (never interpolates the variance map); equals dense `diag(W Q_post⁻¹ Wᵀ)` (`rtol=1e-6`).
- [ ] R inflation grows with `|t_obs − t_out|` scaled by `temporal_taper_scale`; provenance records the conservative `known_bias`.
- [ ] `parameter_space()` exposes `range`, `variance`, `temporal_taper_scale`; `MaternGMRF.solve` returns a distribution wrapping the operator; `METHODS["gmrf"]` resolves.

**Verify:** `pixi run test tests/unit/test_gmrf_method.py -v` → all pass.

**Steps:**

- [ ] **Step 1: Write the failing test** — `tests/unit/test_gmrf_method.py`

```python
"""GMRF method: EXACT sparse-precision operator, temporal-taper conditioning, off-grid W."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("sksparse")  # noqa: E402

from sverdrup.core.grid import GridSpec  # noqa: E402
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow  # noqa: E402
from sverdrup.core.parameters import ConstantProvider  # noqa: E402
from sverdrup.core.types import CovFidelity  # noqa: E402
from sverdrup.methods.gmrf import MaternGMRF  # noqa: E402
from sverdrup.methods.registry import METHODS  # noqa: E402


def _grid():
    return GridSpec.lonlat(np.linspace(0.0, 6.0, 7), np.linspace(0.0, 6.0, 7))


def _params(taper=5.0):
    return ConstantProvider(
        {"range": 300.0, "variance": 0.05, "temporal_taper_scale": taper}
    )


def _obs(value=1.0, t=2.0):
    return ObsWindow.from_arrays(
        np.array([3.0]), np.array([3.0]), np.array([t]),
        np.array([value]), DiagonalErrorModel(np.array([1e-3])),
    )


def test_registered_and_capability():
    # Behavior: GMRF plugs into the registry like OI; EXACT, sparse-precision.
    assert "gmrf" in METHODS
    dist = MaternGMRF().solve(_obs(), _grid(), _params(), 2.0)
    assert dist.cov_op.fidelity is CovFidelity.EXACT
    assert dist.cov_op.representation == "sparse-precision"


def test_marginal_var_is_exact_selective_inverse():
    # Behavior: gridded marginal variance == diag(Q_post^-1), exactly.
    # Bug caught: a sampled/approx variance would make calibration dishonest.
    dist = MaternGMRF().solve(_obs(), _grid(), _params(), 2.0)
    pts = _grid().points(2.0)
    var = dist.cov_op.marginal_var(pts)
    q = dist.cov_op.q_post.toarray()
    np.testing.assert_allclose(var, np.diag(np.linalg.inv(q)), rtol=1e-8)


def test_posterior_mean_pulled_toward_obs():
    # Behavior: conditioning on one high obs raises the nearest-node mean above zero.
    # Bug caught: dropping A^T R^-1 y leaves the prior-mean (zero) field.
    dist = MaternGMRF().solve(_obs(value=1.0), _grid(), _params(), 2.0)
    j = i = 3
    assert dist.mean[j, i] > 0.05


def test_offgrid_var_uses_W_selective_inverse_not_interpolation():
    # Behavior: off-grid eval var == diag(W Sigma W^T) from stencil entries, == dense.
    # Bug caught: interpolating the marginal-variance map (invariant 7 violation).
    dist = MaternGMRF().solve(_obs(), _grid(), _params(), 2.0)
    ep = np.array([[3.5, 3.5, 2.0]])
    var = dist.cov_op.marginal_var(ep)
    from sverdrup.methods.gmrf_grid import bilinear_weights

    w = bilinear_weights(_grid(), ep).toarray()
    dense = w @ np.linalg.inv(dist.cov_op.q_post.toarray()) @ w.T
    np.testing.assert_allclose(var, np.diag(dense), rtol=1e-6)


def test_temporal_taper_inflates_far_obs():
    # Behavior: an obs far in time conditions the field less than a near one.
    # Bug caught: ignoring the time offset over-conditions from far-in-time obs.
    near = MaternGMRF().solve(_obs(t=2.0), _grid(), _params(taper=2.0), 2.0)
    far = MaternGMRF().solve(_obs(t=10.0), _grid(), _params(taper=2.0), 2.0)
    assert near.mean[3, 3] > far.mean[3, 3]
```

- [ ] **Step 2: Run — confirm fail**

Run: `pixi run test tests/unit/test_gmrf_method.py -v`
Expected: FAIL — `ModuleNotFoundError: sverdrup.methods.gmrf`.

- [ ] **Step 3: Implement `gmrf.py`**

```python
"""Method 2: regular-grid Matérn GMRF (sparse precision); EXACT selective-inversion (spec §5.1)."""

from __future__ import annotations

import numpy as np
from scipy import sparse  # type: ignore[import-untyped]

from sverdrup.core.grid import GridSpec
from sverdrup.core.observations import ObsWindow
from sverdrup.core.parameters import ParameterProvider, ParameterSpace
from sverdrup.core.provenance import (
    KnownBias,
    TransformKind,
    UncertaintyProvenance,
    UncertaintyTransform,
)
from sverdrup.core.types import CovFidelity, Points, Seed, UncertaintyCapability
from sverdrup.distributions.gaussian import GaussianPredictiveDistribution
from sverdrup.methods.gmrf_grid import (
    bilinear_weights,
    kappa_from_range,
    matern_precision,
)
from sverdrup.methods.gmrf_linalg import GMRFFactor, assert_adjacency_in_pattern


class GMRFCovarianceOperator:
    """EXACT posterior covariance of a regular-grid GMRF, backed by one sparse factor."""

    fidelity = CovFidelity.EXACT
    representation = "sparse-precision"

    def __init__(
        self, grid: GridSpec, q_post: sparse.csc_matrix, time_days: float
    ) -> None:
        """Cache the posterior precision and its factor; verify the adjacency precondition."""
        assert_adjacency_in_pattern(q_post, grid.shape)
        self.grid = grid
        self.q_post = q_post
        self.time_days = time_days
        self._factor = GMRFFactor(q_post)
        self._sinv = self._factor.selective_inverse()  # sparse, on L+L^T pattern
        self._diag = np.asarray(self._sinv.diagonal())

    def _is_grid(self, a: Points) -> bool:
        """True if ``a`` matches the grid nodes (the identity-projection fast path)."""
        return a.shape[0] == self.grid.shape[0] * self.grid.shape[1] and np.allclose(
            a[:, :2], self.grid.points(self.time_days)[:, :2]
        )

    def marginal_var(self, a: Points) -> np.ndarray:
        """Return exact marginal variance: ``diag(Q^-1)`` on-grid, ``diag(W Σ W^T)`` off-grid."""
        if self._is_grid(a):
            return self._diag
        w = bilinear_weights(self.grid, a)
        return np.asarray((w @ self._sinv @ w.T).diagonal())

    def cov(self, a: Points, b: Points) -> np.ndarray:
        """Return ``W_a Σ W_b^T`` using selective-inverse entries (adjacent pairs in pattern)."""
        wa = bilinear_weights(self.grid, a)
        wb = bilinear_weights(self.grid, b)
        return np.asarray((wa @ self._sinv @ wb.T).toarray())

    def posterior_sample(self, s: Points, seed: Seed, m: int) -> np.ndarray:
        """Return ``m`` zero-mean draws ``W (L^-T w)`` at ``s`` (node-space sample, projected)."""
        rng = np.random.default_rng(seed)
        n = self.q_post.shape[0]
        node_draws = np.stack([self._factor.sample(rng.standard_normal(n)) for _ in range(m)])
        if self._is_grid(s):
            return node_draws
        w = bilinear_weights(self.grid, s)
        return np.asarray(node_draws @ w.T.toarray().T)  # (m, k)

    def node_sample(self, w_white: np.ndarray) -> np.ndarray:
        """Return one node-space draw ``L^-T w`` from external white noise (coherence driver)."""
        return self._factor.sample(w_white)


class MaternGMRF:
    """Regular-grid Matérn GMRF method: spatial precision + temporally-tapered likelihood."""

    native_capability = UncertaintyCapability.SAMPLES  # also exposes COVARIANCE

    def solve(
        self,
        obs: ObsWindow,
        grid: GridSpec,
        params: ParameterProvider,
        time_days: float,
    ) -> GaussianPredictiveDistribution:
        """Solve the GMRF posterior over ``grid`` at ``time_days`` (temporal taper into R)."""
        rng_km = float(params.resolve("range", grid))
        tau = float(params.resolve("variance", grid))
        taper = float(params.resolve("temporal_taper_scale", grid))
        kappa = kappa_from_range(rng_km)
        q_prior = matern_precision(grid, kappa, tau)

        a_op = bilinear_weights(grid, obs.coords())  # (n_obs, n_nodes): grid -> obs
        r_diag = np.diag(obs.error_model.as_matrix(len(obs))).astype(float)
        dt = np.abs(obs.coords()[:, 2] - time_days)
        r_inflated = r_diag * np.exp(dt / max(taper, 1e-9))  # temporal taper into R
        r_inv = sparse.diags(1.0 / r_inflated)

        q_post = (q_prior + a_op.T @ r_inv @ a_op).tocsc()
        op = GMRFCovarianceOperator(grid, q_post, time_days)
        rhs = a_op.T @ (r_inv @ obs.values())
        mean = op._factor.solve(np.asarray(rhs)).reshape(grid.shape)

        prov = UncertaintyProvenance(
            native_capability=self.native_capability,
            transformations=[
                UncertaintyTransform(
                    kind=TransformKind.DIAGONAL_INFLATION,
                    known_bias=KnownBias.UNDER_DISPERSED_IN_VOIDS,
                    params={
                        "temporal_taper": "diagonal-R; under-uses temporal structure "
                        "(conservative). OI carries a full space-time kernel; GMRF "
                        "carries spatial cov + temporally-tapered likelihood.",
                        "temporal_taper_scale": taper,
                    },
                )
            ],
        )
        return GaussianPredictiveDistribution(grid, mean, op, prov, time_days)

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

- [ ] **Step 4: Register the method** — `src/sverdrup/methods/registry.py`

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

- [ ] **Step 5: Run the method tests + full suite**

Run: `pixi run test tests/unit/test_gmrf_method.py -v` → PASS
Run: `pixi run test -q` → `131 passed, 2 skipped` (the two GMRF unit modules added; counts grow, no regressions).

- [ ] **Step 6: Commit**

```bash
git add src/sverdrup/methods/gmrf.py src/sverdrup/methods/registry.py tests/unit/test_gmrf_method.py
pixi run pre-commit run --files src/sverdrup/methods/gmrf.py src/sverdrup/methods/registry.py tests/unit/test_gmrf_method.py
git commit -m "feat: MaternGMRF method — EXACT sparse-precision operator, temporal-taper conditioning, off-grid W"
```

---

### Task 7: PrecisionFields + PrecisionDistribution + GMRFPrecisionReduction (genuine-first-class)

**Goal:** Add the representation-tagged sparse-precision storable and its distribution, plus the GMRF reduction strategy that persists `Q`+permutation+exact-var directly — **no low-rank factor materialized anywhere for GMRF**.

**Files:**
- Modify: `src/sverdrup/distributions/persisted.py` (`PrecisionFields`, `PrecisionDistribution`)
- Modify: `src/sverdrup/distributions/reduction.py` (`GMRFPrecisionReduction`, register)
- Test: `tests/unit/test_precision_distribution.py`

**Acceptance Criteria:**
- [ ] `PrecisionFields.sampler_spec == "sparse-precision"`; stores `mean`, sparse `precision`, `permutation`, `marginal_variance`.
- [ ] `PrecisionDistribution` implements `marginal_variance`/`covariance`/`sample`/`regrid` (`PredictiveDistribution`).
- [ ] `GMRFPrecisionReduction.reduce` returns a `ReducedUnit` whose `base_fields` is a `PrecisionFields` with **no `factor` attribute**, and whose eval-point predictions carry `(mean, var)` with `factor is None`.
- [ ] `select_reduction` routes a GMRF dist (operator `representation == "sparse-precision"`) to `GMRFPrecisionReduction`.
- [ ] **Genuine-first-class:** after reduction, `isinstance(base_fields, PrecisionFields)` and `not hasattr(base_fields, "factor")`.

**Verify:** `pixi run test tests/unit/test_precision_distribution.py -v` → all pass.

**Steps:**

- [ ] **Step 1: Write the failing test** — `tests/unit/test_precision_distribution.py`

```python
"""Sparse-precision persisted form: first-class beside low-rank, never reduced to a factor."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("sksparse")  # noqa: E402

from sverdrup.core.grid import GridSpec  # noqa: E402
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow  # noqa: E402
from sverdrup.core.parameters import ConstantProvider  # noqa: E402
from sverdrup.distributions.persisted import PrecisionDistribution, PrecisionFields  # noqa: E402
from sverdrup.distributions.reduction import GMRFPrecisionReduction, select_reduction  # noqa: E402
from sverdrup.methods.gmrf import MaternGMRF  # noqa: E402


def _grid():
    return GridSpec.lonlat(np.linspace(0.0, 6.0, 7), np.linspace(0.0, 6.0, 7))


def _dist():
    obs = ObsWindow.from_arrays(
        np.array([3.0]), np.array([3.0]), np.array([2.0]),
        np.array([1.0]), DiagonalErrorModel(np.array([1e-3])),
    )
    p = ConstantProvider({"range": 300.0, "variance": 0.05, "temporal_taper_scale": 5.0})
    return MaternGMRF().solve(obs, _grid(), p, 2.0)


def test_select_reduction_routes_gmrf_to_precision():
    # Behavior: a sparse-precision operator selects the precision reducer, not low-rank.
    # Bug caught: GMRF silently reduced to a low-rank factor (the failure this whole phase guards).
    assert isinstance(select_reduction(_dist()), GMRFPrecisionReduction)


def test_reduction_is_genuine_first_class_no_factor():
    # Behavior: GMRF persists Q + permutation + exact var; no low-rank factor anywhere.
    # Bug caught: a hidden randomized-SVD of the GMRF would defeat the validation's point.
    dist = _dist()
    pts = _grid().points(2.0)
    unit = GMRFPrecisionReduction().reduce(dist, pts, None, rank=20, seed=1)
    assert isinstance(unit.base_fields, PrecisionFields)
    assert not hasattr(unit.base_fields, "factor")
    assert unit.base_fields.sampler_spec == "sparse-precision"


def test_precision_distribution_marginal_var_exact():
    # Behavior: the stored marginal variance equals the operator's exact selective-inverse diag.
    dist = _dist()
    pts = _grid().points(2.0)
    unit = GMRFPrecisionReduction().reduce(dist, pts, None, rank=20, seed=1)
    pd = PrecisionDistribution(_grid(), unit.base_fields, dist.provenance, 2.0)
    np.testing.assert_allclose(
        pd.marginal_variance().ravel(), dist.cov_op.marginal_var(pts), rtol=1e-10
    )


def test_precision_distribution_eval_points_have_no_factor():
    # Behavior: off-grid eval predictions carry (mean, var), factor is None for GMRF.
    # Bug caught: forcing GMRF eval rows into the low-rank basis (representation leak).
    dist = _dist()
    pts = _grid().points(2.0)
    evals = np.array([[3.5, 3.5, 2.0]])
    unit = GMRFPrecisionReduction().reduce(dist, pts, evals, rank=20, seed=1)
    assert unit.eval_points is not None
    assert unit.eval_points.factor is None
    np.testing.assert_allclose(
        unit.eval_points.variance, dist.cov_op.marginal_var(evals), rtol=1e-6
    )
```

- [ ] **Step 2: Run — confirm fail**

Run: `pixi run test tests/unit/test_precision_distribution.py -v`
Expected: FAIL — `ImportError: cannot import name 'PrecisionFields'`.

- [ ] **Step 3: Add `PrecisionFields` + `PrecisionDistribution`** to `persisted.py`

```python
@dataclass(frozen=True)
class PrecisionFields:
    """Storable sufficient stats for a sparse-precision (GMRF) generator — first-class.

    Deliberately has NO ``factor``/``residual``: the GMRF representation is never reduced
    to low-rank. ``sampler_spec`` is the discriminator the coherence driver dispatches on.
    """

    mean: Field
    precision: "object"  # scipy.sparse CSC posterior precision over the grid nodes
    permutation: np.ndarray  # fill-reducing permutation (persisted with Q)
    marginal_variance: Field  # exact, from selective inversion
    seed: Seed
    sampler_spec: str = "sparse-precision"


@dataclass
class PrecisionDistribution:
    """A predictive distribution backed by persisted sparse precision (GMRF)."""

    grid: GridSpec
    fields: PrecisionFields
    provenance: UncertaintyProvenance
    time_days: float

    def __post_init__(self) -> None:
        """Cache a factor lazily on first sampling/cov use."""
        self._factor: object | None = None

    def _factor_obj(self):
        from sverdrup.methods.gmrf_linalg import GMRFFactor

        if self._factor is None:
            self._factor = GMRFFactor(self.fields.precision)
        return self._factor

    def marginal_variance(self) -> Field:
        """Return the stored exact marginal-variance field, shape ``(ny, nx)``."""
        return self.fields.marginal_variance

    def covariance(self, a: Points, b: Points) -> np.ndarray:
        """Return ``W_a Σ W_b^T`` from the cached factor's selective inverse."""
        from sverdrup.methods.gmrf_grid import bilinear_weights

        sinv = self._factor_obj().selective_inverse()
        wa = bilinear_weights(self.grid, a)
        wb = bilinear_weights(self.grid, b)
        return np.asarray((wa @ sinv @ wb.T).toarray())

    def sample(self, m: int, seed: Seed) -> np.ndarray:
        """Return ``m`` field draws ``mean + L^-T w``, shape ``(m, ny, nx)``."""
        rng = np.random.default_rng(seed)
        fac = self._factor_obj()
        n = self.fields.precision.shape[0]
        draws = np.stack([fac.sample(rng.standard_normal(n)) for _ in range(m)])
        ny, nx = self.grid.shape
        return np.asarray(self.fields.mean[None, :, :] + draws.reshape(m, ny, nx))

    def regrid(self, target: GridSpec) -> "PrecisionDistribution":
        """Re-express on ``target`` via samples (never the variance map)."""
        raise NotImplementedError("GMRF regrid lands only if a cross-CRS GMRF blend is needed.")
```

Add `Seed` to the `persisted.py` imports if not present (it is, via `from sverdrup.core.types import Field, Points, Seed`).

- [ ] **Step 4: Add `GMRFPrecisionReduction`** to `reduction.py`

```python
class GMRFPrecisionReduction:
    """GMRF reduction: persist Q + permutation + exact var directly; NO low-rank factor."""

    def reduce(
        self, dist, grid_points, eval_points, *, rank, seed
    ) -> ReducedUnit:
        from sverdrup.distributions.persisted import PrecisionFields

        d = cast(Any, dist)
        op = d.cov_op
        base = PrecisionFields(
            mean=d.mean,
            precision=op.q_post,
            permutation=op._factor.permutation,
            marginal_variance=op.marginal_var(grid_points).reshape(d.grid.shape),
            seed=seed,
        )
        if eval_points is None:
            return ReducedUnit(base, None)
        mean = (bilinear := __import__(
            "sverdrup.methods.gmrf_grid", fromlist=["bilinear_weights"]
        ).bilinear_weights)(d.grid, eval_points) @ d.mean.ravel()
        var = op.marginal_var(eval_points)
        return ReducedUnit(
            base,
            EvalPointPredictions(eval_points, np.asarray(mean), var, samples=None),
        )
```

Cleaner: add a module-level `from sverdrup.methods.gmrf_grid import bilinear_weights` lazily inside the method instead of the `__import__` trick:

```python
class GMRFPrecisionReduction:
    """GMRF reduction: persist Q + permutation + exact var directly; NO low-rank factor."""

    def reduce(self, dist, grid_points, eval_points, *, rank, seed) -> ReducedUnit:
        from sverdrup.distributions.persisted import PrecisionFields
        from sverdrup.methods.gmrf_grid import bilinear_weights

        d = cast(Any, dist)
        op = d.cov_op
        base = PrecisionFields(
            mean=d.mean,
            precision=op.q_post,
            permutation=op._factor.permutation,
            marginal_variance=op.marginal_var(grid_points).reshape(d.grid.shape),
            seed=seed,
        )
        if eval_points is None:
            return ReducedUnit(base, None)
        mean = np.asarray(bilinear_weights(d.grid, eval_points) @ d.mean.ravel())
        var = op.marginal_var(eval_points)
        return ReducedUnit(
            base, EvalPointPredictions(eval_points, mean, var, samples=None)
        )
```

Register: `_REDUCTIONS["sparse-precision"] = GMRFPrecisionReduction`.

- [ ] **Step 5: Run precision tests + full suite**

Run: `pixi run test tests/unit/test_precision_distribution.py -v` → PASS
Run: `pixi run test -q` → all green, counts grow, no regressions.

- [ ] **Step 6: Commit**

```bash
git add src/sverdrup/distributions/persisted.py src/sverdrup/distributions/reduction.py \
        tests/unit/test_precision_distribution.py
pixi run pre-commit run --files src/sverdrup/distributions/persisted.py \
        src/sverdrup/distributions/reduction.py tests/unit/test_precision_distribution.py
git commit -m "feat: PrecisionFields/PrecisionDistribution + GMRFPrecisionReduction (genuine-first-class, no factor)"
```

---

### Task 8: GmrfPrecisionSolve coherent driver (native shared-w coherence)

**Goal:** Add the `GmrfPrecisionSolve` `CoherentMemberDriver` — per tile `mean + L⁻ᵀ w` with `w` the **shared** global-lattice `diagonal_noise` field, weight-crossfaded over the support; no QR trick, only the conservative `Q_i≠Q_j` halo residual. Register it under `sampler_spec == "sparse-precision"`.

**Files:**
- Modify: `src/sverdrup/distributions/coherent.py` (`GmrfPrecisionSolve`, register in `select_driver`)
- Test: `tests/test_gmrf_blend.py` (driver-level tests; pipeline tests land in Task 9)

**Acceptance Criteria:**
- [ ] `select_driver("sparse-precision")` returns a `GmrfPrecisionSolve`.
- [ ] For a single GMRF tile, the driver's coherent member equals `mean + node_sample(w)` where `w = diagonal_noise(grid_pts, member, noise)` (native, shared white noise).
- [ ] Two overlapping identical-`Q` GMRF tiles driven by the same global `w` agree on shared nodes (coherent — overlap member difference ≪ interior member magnitude).
- [ ] The crossfade `Σ wᵢ·fieldᵢ` is the same representation-agnostic code path (no GMRF-specific crossfade).

**Verify:** `pixi run test tests/test_gmrf_blend.py -v -k driver` → pass.

**Steps:**

- [ ] **Step 1: Write the failing test** — `tests/test_gmrf_blend.py` (driver section)

```python
"""GMRF blend: native shared-w coherence driver + (Task 9) seam-free blended product."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("sksparse")  # noqa: E402

from sverdrup.core.geometry import Tile, Window  # noqa: E402
from sverdrup.core.grid import GridSpec  # noqa: E402
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow  # noqa: E402
from sverdrup.core.parameters import ConstantProvider  # noqa: E402
from sverdrup.distributions.blend import BlendInput, partition_weights  # noqa: E402
from sverdrup.distributions.coherent import (  # noqa: E402
    GmrfPrecisionSolve,
    NoiseSpec,
    diagonal_noise,
    select_driver,
)
from sverdrup.distributions.persisted import PrecisionDistribution  # noqa: E402
from sverdrup.distributions.reduction import GMRFPrecisionReduction  # noqa: E402
from sverdrup.methods.gmrf import MaternGMRF  # noqa: E402

_P = ConstantProvider({"range": 300.0, "variance": 0.05, "temporal_taper_scale": 5.0})


def _gmrf_pd(grid, value=1.0):
    obs = ObsWindow.from_arrays(
        np.array([grid.x.mean()]), np.array([grid.y.mean()]), np.array([2.0]),
        np.array([value]), DiagonalErrorModel(np.array([1e-3])),
    )
    dist = MaternGMRF().solve(obs, grid, _P, 2.0)
    unit = GMRFPrecisionReduction().reduce(dist, grid.points(2.0), None, rank=0, seed=3)
    return PrecisionDistribution(grid, unit.base_fields, dist.provenance, 2.0)


def test_select_driver_sparse_precision():
    assert isinstance(select_driver("sparse-precision"), GmrfPrecisionSolve)


def test_single_tile_member_is_native_shared_w():
    # Behavior: one GMRF tile's coherent member == mean + L^-T w with w the global cell noise.
    # Bug caught: a QR-basis trick (low-rank emulation) instead of native precision sampling.
    grid = GridSpec.lonlat(np.linspace(0.0, 6.0, 7), np.linspace(0.0, 6.0, 7))
    pd = _gmrf_pd(grid)
    tile = Tile(Window((0, 6), (0, 6), (0, 0)), Window((0, 6), (0, 6), (0, 0)), grid)
    parts = [BlendInput(pd, tile)]
    pts = grid.points(2.0)
    noise = NoiseSpec(method="gmrf", params_key="p", lattice_step=0.5)
    w = partition_weights([tile], pts)
    got = GmrfPrecisionSolve().crossfaded_member(parts, pts, w, 4, noise)
    white = diagonal_noise(pts, 4, noise)
    expected = pd.fields.mean.ravel() + pd._factor_obj().sample(white)
    np.testing.assert_allclose(got, expected, rtol=1e-9)
```

- [ ] **Step 2: Run — confirm fail**

Run: `pixi run test tests/test_gmrf_blend.py -v -k driver`
Expected: FAIL — `ImportError: cannot import name 'GmrfPrecisionSolve'`.

- [ ] **Step 3: Implement `GmrfPrecisionSolve`** in `coherent.py`

```python
class GmrfPrecisionSolve:
    """GMRF driver: per-tile ``mean + L^-T w`` with a SHARED global ``w``; weight-crossfaded.

    Native coherence: every tile is forced by the SAME global-lattice white noise
    ``diagonal_noise`` over the support, so overlapping tiles agree wherever ``Q_i == Q_j``.
    The only residual is the conservative ``Q_i != Q_j`` halo-agreement term (recorded in
    provenance by the blend). No QR-basis trick.
    """

    def crossfaded_member(
        self, parts, pts, weights, member_index, noise
    ) -> np.ndarray:
        white = diagonal_noise(pts, member_index, noise)  # shared global forcing over support
        n = pts.shape[0]
        out = np.zeros(n)
        for i, p in enumerate(parts):
            d = p.distribution
            idx = _nearest(d.grid, pts, d.time_days)
            cover = weights[i] > 0
            # node-space draw on the tile's own lattice, forced by the shared white noise
            node = d.fields.mean.ravel() + d._factor_obj().sample(white[idx])
            field_i = np.zeros(n)
            field_i[cover] = node[idx[cover]]
            out += weights[i] * field_i
        return np.asarray(out)
```

> **Executor note:** `d._factor_obj().sample(white[idx])` draws on the tile's node order; `white[idx]` maps the support-point shared noise to the tile's nodes via the nearest-node index, giving a per-tile node-space white vector that is shared wherever two tiles see the same global cell. For a single tile whose nodes equal the support, `idx` is the identity, matching the test's `pd._factor_obj().sample(white)`.

Register: `_DRIVERS["sparse-precision"] = GmrfPrecisionSolve`.

- [ ] **Step 4: Run the driver test + full suite**

Run: `pixi run test tests/test_gmrf_blend.py -v -k driver` → PASS
Run: `pixi run test -q` → no regressions.

- [ ] **Step 5: Commit**

```bash
git add src/sverdrup/distributions/coherent.py tests/test_gmrf_blend.py
pixi run pre-commit run --files src/sverdrup/distributions/coherent.py tests/test_gmrf_blend.py
git commit -m "feat: GmrfPrecisionSolve coherent driver — native shared-w precision sampling (no QR trick)"
```

---

### Task 9: GMRF blend validation — seam-free, no-dip, single-tile ref, OSSE+OSE [USER-ORDERED GATE — Stage B]

**Goal:** Run the method-agnostic blend globally on GMRF: coherent samples seam-free with no mid-overlap variance dip, matching a single-tile GMRF reference (conservative direction); accuracy + calibration fire in OSSE and OSE; provenance carries `BlendTransform` + the sparse-precision tag; genuine-first-class survives the pipeline; eval-point OSE uses the recorded moment-crossfade simplification.

> **USER-ORDERED GATE — NON-SKIPPABLE.** This task was requested by the user in the current conversation. It MUST NOT be closed by walking around it, by declaring it "verified inline", or by substituting a cheaper check. Close only after every item in `acceptanceCriteria` has been re-validated independently, with output captured. The seam-free / conservative-direction assertions are the Stage-B validation contract; a failure is a spec-§8 escalation, never a tolerance loosen.

**Files:**
- Modify: `src/sverdrup/application/pipeline.py` (`_blend_eval_points`: sparse-precision no-factor path → moment crossfade + provenance note)
- Test: `tests/test_gmrf_blend.py` (blend + pipeline sections)

**Acceptance Criteria:**
- [ ] A 3×1 GMRF regional blend matches the 1×1 GMRF reference: `rel_l2(mean) ≤ 0.05`; blended σ never below the reference (conservative); no gradient spike at the seam.
- [ ] On the integrated GMRF product, sampled variance reproduces the analytic crossfade (`median rel ≤ 0.15`, no mid-overlap dip).
- [ ] `run_tiled_pipeline(method="gmrf")` returns finite `rmse`, `reduced_chi2`, `coverage_1sigma` in **OSSE**; finite `rmse`, `reduced_chi2` in **OSE** (withheld c2), TRUTH absent from OSE context.
- [ ] The blended product fidelity is `BLENDED`; provenance has a `BLEND` transform; the constituents carry `sampler_spec == "sparse-precision"` (genuine-first-class survives).
- [ ] `_blend_eval_points` records the moment-crossfade simplification (provenance param `"eval_point_cov": "moment-crossfade; cross-eval-point covariance not represented"`).

**Verify:** `pixi run test tests/test_gmrf_blend.py -v` → all pass.

**Steps:**

- [ ] **Step 1: Write the failing tests** — append to `tests/test_gmrf_blend.py`

```python
def _gmrf_region_inputs(tmp_path_factory, mode="OSSE"):
    from sverdrup.adapters.executor_dask import ExecutorConfig
    from sverdrup.adapters.odc.fixtures import FixtureSource
    from sverdrup.application.pipeline import PipelineInputs

    if mode == "OSSE":
        src = FixtureSource(
            "tests/fixtures/natl60_tiny.nc", ref_path="tests/fixtures/natl60_ref_tiny.nc"
        )
    else:
        src = FixtureSource("tests/fixtures/ose_tiny.nc")
    out = tmp_path_factory.mktemp("gmrf")
    return PipelineInputs(
        mode=mode, method_name="gmrf", source=src, out_url=f"file://{out}",
        lon_range=(-64.0, -56.0), lat_range=(34.0, 42.0), grid_resolution_deg=1.0,
        time_range=(0.0, 5.0), output_times=[2.0],
        params={"range": 300.0, "variance": 0.05, "temporal_taper_scale": 10.0},
        executor=ExecutorConfig(n_processes=2, threads_per_process=1), rank=20,
    )


def _partition(n_lon):
    from sverdrup.application.tiling import LonLatPartition, ScaleAwareHalo
    from sverdrup.core.parameters import ConstantProvider

    return LonLatPartition(
        n_lon=n_lon, n_lat=1, halo=ScaleAwareHalo(k=1.0),
        correlation_length=ConstantProvider({"correlation_length": 300.0}),
        stencil_radius_km=10.0,
    )


def test_gmrf_blend_matches_single_tile_conservative(tmp_path_factory):
    # Behavior: 3-tile GMRF blend == 1-tile GMRF reference, sigma conservative, no seam.
    # Bug caught: native shared-w coherence broken -> seam or overconfident overlap.
    from sverdrup.application.pipeline import run_tiled_pipeline

    inp = _gmrf_region_inputs(tmp_path_factory)
    ref = run_tiled_pipeline(inp, _partition(1))[0][0]
    multi = run_tiled_pipeline(inp, _partition(3))[0][0]
    rel = np.linalg.norm(multi.mean - ref.mean) / np.linalg.norm(ref.mean)
    assert rel <= 0.05, f"GMRF blend diverged from single-tile reference: {rel}"
    dsig = np.sqrt(multi.marginal_variance()) - np.sqrt(ref.marginal_variance())
    assert np.nanmin(dsig) >= -1e-9, f"GMRF blended sigma overconfident: {np.nanmin(dsig)}"


def test_gmrf_blend_no_variance_dip(tmp_path_factory):
    # Behavior: coherent GMRF samples reproduce the analytic crossfade variance (no dip).
    # Bug caught: independent per-tile w -> sampled variance dips in the overlap.
    from sverdrup.application.pipeline import run_tiled_pipeline

    multi = run_tiled_pipeline(_gmrf_region_inputs(tmp_path_factory), _partition(3))[0][0]
    analytic = multi.marginal_variance()
    sampled = multi.sample(m=256, seed=5).var(axis=0)
    rel = np.abs(sampled - analytic) / np.clip(analytic, 1e-9, None)
    assert np.median(rel) <= 0.15, f"GMRF sampled variance diverges: {np.median(rel)}"


def test_gmrf_pipeline_osse_and_ose(tmp_path_factory):
    # Behavior: accuracy + calibration fire on the GMRF blended product, OSSE and OSE.
    # Bug caught: a representation that can't score (NaN), or OSE leaking truth.
    from sverdrup.application.pipeline import run_tiled_pipeline
    from sverdrup.core.evaluation import ContextKey

    osse = run_tiled_pipeline(_gmrf_region_inputs(tmp_path_factory, "OSSE"), _partition(3))
    assert np.isfinite(osse[1]["rmse"])
    assert np.isfinite(osse[1]["reduced_chi2"])
    assert np.isfinite(osse[1]["coverage_1sigma"])
    ose = run_tiled_pipeline(_gmrf_region_inputs(tmp_path_factory, "OSE"), _partition(3))
    assert ContextKey.TRUTH.name not in ose[1]["context_keys"]
    assert np.isfinite(ose[1]["rmse"])


def test_gmrf_blend_provenance_and_first_class(tmp_path_factory):
    # Behavior: blended GMRF is BLENDED with a BLEND transform; constituents stay sparse-precision.
    # Bug caught: GMRF silently reduced to low-rank somewhere in the pipeline.
    from sverdrup.application.pipeline import run_tiled_pipeline
    from sverdrup.application.tiling import LonLatPartition, ScaleAwareHalo
    from sverdrup.core.parameters import ConstantProvider
    from sverdrup.core.provenance import TransformKind
    from sverdrup.core.types import CovFidelity

    inp = _gmrf_region_inputs(tmp_path_factory)
    part = _partition(3)
    blends, _ = run_tiled_pipeline(inp, part)
    gb = blends[0]
    assert gb.fidelity is CovFidelity.BLENDED
    assert any(t.kind is TransformKind.BLEND for t in gb.provenance.transformations)
    assert gb._parts[0].distribution.fields.sampler_spec == "sparse-precision"
```

- [ ] **Step 2: Run — confirm fail**

Run: `pixi run test tests/test_gmrf_blend.py -v -k pipeline or conservative`
Expected: FAIL — `_blend_eval_points` raises on the GMRF eval rows (no `factor`), or scores NaN.

- [ ] **Step 3: Patch `_blend_eval_points` for the sparse-precision (no-factor) path** — `src/sverdrup/application/pipeline.py`

Replace the body of `_blend_eval_points` so a constituent without a low-rank eval factor is blended by the representation-agnostic **moment crossfade** (mean `Σwμ`, var `(Σwσ)²`), recording the simplification:

```python
def _blend_eval_points(
    products: list[tuple[Any, Product]],
    eval_locs: np.ndarray | None,
    grid: GridSpec,
    inp: PipelineInputs,
    params_key: str,
) -> tuple[np.ndarray | None, np.ndarray | None]:
    """Crossfade per-tile withheld eval-point predictives over the eval ``PointSet``.

    Low-rank (OI) constituents blend coherently in the shared basis. Sparse-precision (GMRF)
    constituents have no low-rank eval factor, so they take the representation-agnostic moment
    crossfade (exact per-tile variance from Takahashi; cross-eval-point covariance in overlaps
    is not represented — recorded as a known simplification, not a hidden assumption).
    """
    if eval_locs is None:
        return None, None
    from sverdrup.distributions.blend import partition_weights

    tiles = [t for t, _ in products]
    has_factor = any(
        (p.per_time[0].eval_points is not None and p.per_time[0].eval_points.factor is not None)
        for _, p in products
    )
    eps = [p.per_time[0].eval_points for _, p in products]
    if all(ep is None for ep in eps):
        return None, None
    if has_factor:
        parts: list[BlendInput] = []
        for tile, prod in products:
            ep = prod.per_time[0].eval_points
            if ep is None or ep.factor is None or ep.locations.shape[0] == 0:
                continue
            residual = ep.residual if ep.residual is not None else np.zeros(ep.locations.shape[0])
            pp = PersistedPoints(
                PointSet(ep.locations, grid.crs), mean=ep.mean, factor=ep.factor,
                residual=residual, provenance=prod.per_time[0].base.provenance,
                time_days=inp.output_times[0],
            )
            parts.append(BlendInput(pp, tile))
        if not parts:
            return None, None
        eb = BlendOperator().blend(
            parts, support=PointSet(eval_locs, grid.crs),
            method=inp.method_name, params_key=params_key,
        )
        return eb.mean.ravel(), eb.marginal_variance().ravel()
    # sparse-precision (or any factor-less) path: moment crossfade at the eval points
    means, sigmas = [], []
    for tile, prod in products:
        ep = prod.per_time[0].eval_points
        if ep is None:
            continue
        w = partition_weights([tile], eval_locs)[0]  # (k,) coverage weight for this tile
        # nearest per-tile eval predictive value at each global eval point
        idx = np.argmin(
            np.linalg.norm(eval_locs[:, None, :2] - ep.locations[None, :, :2], axis=2), axis=1
        )
        means.append(w * ep.mean[idx])
        sigmas.append(w * np.sqrt(ep.variance[idx]))
    if not means:
        return None, None
    wsum = partition_weights(list(tiles), eval_locs).sum(axis=0)
    safe = np.where(wsum > 0, wsum, 1.0)
    mean = np.sum(means, axis=0) / safe
    sigma = np.sum(sigmas, axis=0) / safe
    return mean, sigma**2
```

Record the simplification in provenance: in `_evaluate_blended`, when `inp.method_name == "gmrf"` and OSE, append to `scores` a marker:

```python
    scores["eval_point_cov"] = (
        "moment-crossfade; cross-eval-point covariance not represented"
        if eval_mean is not None
        else "n/a"
    )
```

(Place this line just before `return scores` in `_evaluate_blended`.)

- [ ] **Step 4: Run the full GMRF blend suite + whole suite**

Run: `pixi run test tests/test_gmrf_blend.py -v` → PASS
Run: `pixi run test -q` → all green (GMRF tests added; OI Phase-2 untouched)
Run: `pixi run typecheck && pixi run lint` → clean

- [ ] **Step 5: Commit (Stage-B gate marker)**

```bash
git add src/sverdrup/application/pipeline.py tests/test_gmrf_blend.py
pixi run pre-commit run --files src/sverdrup/application/pipeline.py tests/test_gmrf_blend.py
git commit -m "feat: Stage-B gate — GMRF validates the blend (seam-free, conservative, OSSE+OSE, first-class)"
```

---

## Stage C — degradation path + nonstationary demo

### Task 10: PerturbEnsembleDegradation driver end-to-end (close the Phase-2 gap)

**Goal:** Wire the perturb-ensemble degradation driver through the tiled blend for the deterministic `trivial` method: per-tile independent members, weight-crossfaded, coherence loss recorded in provenance; mean continuous (no silent seam), derivative degraded-but-flagged.

**Files:**
- Modify: `src/sverdrup/core/provenance.py` (`KnownBias.DEGRADED_COHERENCE`, `degradation_transform`)
- Modify: `src/sverdrup/distributions/coherent.py` (`PerturbEnsembleDegradation`, register)
- Modify: `src/sverdrup/distributions/reduction.py` (`EmpiricalReduction.sampler_spec = "perturb-ensemble"`)
- Test: `tests/test_degradation_path.py`

**Acceptance Criteria:**
- [ ] `KnownBias.DEGRADED_COHERENCE` exists; the blend records a transform carrying it when constituents are `sampler_spec == "perturb-ensemble"`.
- [ ] `select_driver("perturb-ensemble")` returns `PerturbEnsembleDegradation`.
- [ ] A 3×1 `trivial` blend runs end-to-end; the blended mean has no seam spike (gradient ≤ 1.5× the single-tile reference); per-tile members are independent (overlap cross-tile member correlation ≈ 0).
- [ ] The blended provenance contains a transform with `known_bias == KnownBias.DEGRADED_COHERENCE`; **no Phase-2 test regressed** (the `sampler_spec` retag is invisible to existing tests).

**Verify:** `pixi run test tests/test_degradation_path.py -v` and `pixi run test -q`.

**Steps:**

- [ ] **Step 1: Write the failing test** — `tests/test_degradation_path.py`

```python
"""Degradation path: perturb-ensemble driver through the tiled blend, coherence loss recorded."""

from __future__ import annotations

import numpy as np

from sverdrup.adapters.executor_dask import ExecutorConfig
from sverdrup.adapters.odc.fixtures import FixtureSource
from sverdrup.application.pipeline import PipelineInputs, run_tiled_pipeline
from sverdrup.application.tiling import LonLatPartition, ScaleAwareHalo
from sverdrup.core.parameters import ConstantProvider
from sverdrup.core.provenance import KnownBias
from sverdrup.distributions.coherent import PerturbEnsembleDegradation, select_driver


def _inputs(tmp_path_factory, n_lon):
    src = FixtureSource(
        "tests/fixtures/natl60_tiny.nc", ref_path="tests/fixtures/natl60_ref_tiny.nc"
    )
    out = tmp_path_factory.mktemp("degrade")
    inp = PipelineInputs(
        mode="OSSE", method_name="trivial", source=src, out_url=f"file://{out}",
        lon_range=(-64.0, -56.0), lat_range=(34.0, 42.0), grid_resolution_deg=1.0,
        time_range=(0.0, 5.0), output_times=[2.0], params={},
        executor=ExecutorConfig(n_processes=2, threads_per_process=1), rank=20,
    )
    part = LonLatPartition(
        n_lon=n_lon, n_lat=1, halo=ScaleAwareHalo(k=1.0),
        correlation_length=ConstantProvider({"correlation_length": 300.0}),
        stencil_radius_km=10.0,
    )
    return inp, part


def test_select_driver_perturb_ensemble():
    assert isinstance(select_driver("perturb-ensemble"), PerturbEnsembleDegradation)


def test_degradation_runs_and_records_coherence_loss(tmp_path_factory):
    # Behavior: trivial blends end-to-end through the degradation driver; loss recorded.
    # Bug caught: the degradation path stays contracted-but-unexercised (the Phase-2 gap).
    inp, part = _inputs(tmp_path_factory, 3)
    blends, scores = run_tiled_pipeline(inp, part)
    gb = blends[0]
    assert any(
        t.known_bias is KnownBias.DEGRADED_COHERENCE for t in gb.provenance.transformations
    )
    assert np.isfinite(scores["rmse"])


def test_degradation_mean_has_no_silent_seam(tmp_path_factory):
    # Behavior: even degraded, the crossfaded MEAN is continuous (no hard-cut seam).
    # Bug caught: a silent seam in the mean masquerading as a coherent product.
    ref = run_tiled_pipeline(*_inputs(tmp_path_factory, 1))[0][0]
    multi = run_tiled_pipeline(*_inputs(tmp_path_factory, 3))[0][0]
    gref = np.nanmax(np.abs(np.diff(ref.mean, axis=1)))
    gmul = np.nanmax(np.abs(np.diff(multi.mean, axis=1)))
    assert gmul <= 1.5 * gref + 1e-9
```

- [ ] **Step 2: Run — confirm fail**

Run: `pixi run test tests/test_degradation_path.py -v`
Expected: FAIL — `ImportError: cannot import name 'PerturbEnsembleDegradation'`.

- [ ] **Step 3: Add the provenance bias + transform** — `src/sverdrup/core/provenance.py`

In `KnownBias`:

```python
    STRUCTURED_BASIS_ORIENTATION = auto()
    DEGRADED_COHERENCE = auto()
```

Add a builder:

```python
def degradation_transform() -> UncertaintyTransform:
    """Build the transform recording cross-tile coherence loss for the degradation driver."""
    return UncertaintyTransform(
        kind=TransformKind.BLEND,
        known_bias=KnownBias.DEGRADED_COHERENCE,
        params={"coherence": "per-tile-independent members; cross-tile coherence not guaranteed"},
    )
```

- [ ] **Step 4: Add the driver** — `src/sverdrup/distributions/coherent.py`

```python
class PerturbEnsembleDegradation:
    """Degradation driver: per-tile INDEPENDENT members, weight-crossfaded (coherence lost).

    Each tile is forced by a tile-distinct seed (member + tile identity), so members do NOT
    agree across the seam — the blend records ``DEGRADED_COHERENCE`` and the seam is flagged,
    not silent. The crossfaded MEAN stays continuous (partition-of-unity weights).
    """

    def crossfaded_member(
        self, parts, pts, weights, member_index, noise
    ) -> np.ndarray:
        n = pts.shape[0]
        out = np.zeros(n)
        for i, p in enumerate(parts):
            d = p.distribution
            idx = _nearest(d.grid, pts, d.time_days)
            cover = weights[i] > 0
            mean_i = d.fields.mean.ravel()[idx]
            sig_i = np.sqrt(d.fields.marginal_variance.ravel()[idx])
            # tile-distinct seed -> independent member (coherence deliberately not shared)
            seed = derive_seed(noise.method, noise.params_key, f"degrade:tile{i}", member_index)
            z = np.random.default_rng(seed).standard_normal(n)
            field_i = np.where(cover, mean_i + sig_i * z, 0.0)
            out += weights[i] * field_i
        return np.asarray(out)
```

Register: `_DRIVERS["perturb-ensemble"] = PerturbEnsembleDegradation`.

- [ ] **Step 5: Retag the empirical reduction + record the degradation transform in the blend**

In `reduction.py`: `EmpiricalReduction.sampler_spec = "perturb-ensemble"`.

In `blend.py` `BlendOperator.blend`, after building `prov`, append the degradation transform when the constituents are the degraded representation:

```python
        spec0 = parts[0].distribution.fields.sampler_spec
        transforms = [
            *base.transformations,
            blend_transform(k, residual_bound, structured_residual=structured_residual),
        ]
        if spec0 == "perturb-ensemble":
            from sverdrup.core.provenance import degradation_transform

            transforms.append(degradation_transform())
        prov = UncertaintyProvenance(
            native_capability=base.native_capability, transformations=transforms
        )
```

(Replace the existing inline `prov = UncertaintyProvenance(... transformations=[*base.transformations, blend_transform(...)])` with the block above.)

- [ ] **Step 6: Run degradation tests + full suite**

Run: `pixi run test tests/test_degradation_path.py -v` → PASS
Run: `pixi run test -q` → all green; **confirm Phase-2 count unchanged** for the OI/blend tests (the retag is invisible — `sampler_spec` is read by no Phase-2 test).

- [ ] **Step 7: Commit**

```bash
git add src/sverdrup/core/provenance.py src/sverdrup/distributions/coherent.py \
        src/sverdrup/distributions/reduction.py src/sverdrup/distributions/blend.py \
        tests/test_degradation_path.py
pixi run pre-commit run --files src/sverdrup/core/provenance.py \
        src/sverdrup/distributions/coherent.py src/sverdrup/distributions/reduction.py \
        src/sverdrup/distributions/blend.py tests/test_degradation_path.py
git commit -m "feat: degradation path end-to-end — perturb-ensemble driver, coherence loss recorded"
```

---

### Task 11: Nonstationary-κ GMRF demonstration

**Goal:** Demonstrate provider-driven nonstationary κ — a `LatitudeVaryingProvider`-style correlation-length field flows into the GMRF stencil, producing spatially-varying `Q` coefficients (range ~100→800 km); record the κ↔range mapping; no hardcoded κ.

**Files:**
- Modify: `src/sverdrup/methods/gmrf.py` (`MaternGMRF.solve`: resolve `range` as scalar OR field → κ field)
- Test: `tests/test_nonstationary_kappa.py`

**Acceptance Criteria:**
- [ ] When `params.resolve("range", grid)` returns a `(ny, nx)` field, `matern_precision` receives a κ **field** and `Q`'s coefficients vary spatially (interior rows at different latitudes differ).
- [ ] A latitude-varying case (equator range 800 km, pole range 100 km) produces a marginal-variance field whose structure varies with latitude (not constant-by-row up to the obs influence).
- [ ] Stationary scalar `range` still works (Task 6 tests stay green) — the field path is additive.
- [ ] κ↔range mapping recorded in provenance params.

**Verify:** `pixi run test tests/test_nonstationary_kappa.py -v` → all pass.

**Steps:**

- [ ] **Step 1: Write the failing test** — `tests/test_nonstationary_kappa.py`

```python
"""Nonstationary kappa: provider-driven latitude-varying range -> spatially-varying Q."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("sksparse")  # noqa: E402

from dataclasses import dataclass  # noqa: E402

import numpy as np  # noqa: E402

from sverdrup.core.grid import GridSpec  # noqa: E402
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow  # noqa: E402
from sverdrup.core.types import ScalarOrField  # noqa: E402
from sverdrup.methods.gmrf import MaternGMRF  # noqa: E402


@dataclass(frozen=True)
class LatVaryingRange:
    """Resolve ``range`` as an equator->pole cos(lat) field; other params constant."""

    equator_km: float
    pole_km: float
    constants: dict

    def resolve(self, name: str, grid: GridSpec) -> ScalarOrField:
        if name == "range":
            _, lat = grid._lonlat_nodes()
            c = np.cos(np.deg2rad(lat))
            return np.asarray(self.pole_km + (self.equator_km - self.pole_km) * c)
        return self.constants[name]

    def params_key(self) -> str:
        return f"latrange(eq={self.equator_km},pole={self.pole_km})"


def _grid():
    return GridSpec.lonlat(np.linspace(-10.0, 10.0, 11), np.linspace(0.0, 60.0, 13))


def _obs():
    return ObsWindow.from_arrays(
        np.array([0.0]), np.array([30.0]), np.array([2.0]),
        np.array([1.0]), DiagonalErrorModel(np.array([1e-3])),
    )


def test_nonstationary_kappa_varies_precision_by_latitude():
    # Behavior: a latitude-varying range field makes Q's coefficients latitude-dependent.
    # Bug caught: collapsing the field to a scalar (ignoring nonstationary kappa).
    prov = LatVaryingRange(800.0, 100.0, {"variance": 0.05, "temporal_taper_scale": 10.0})
    dist = MaternGMRF().solve(_obs(), _grid(), prov, 2.0)
    q = dist.cov_op.q_post
    ny, nx = _grid().shape
    # diagonal of Q at a low-lat row vs a high-lat row differs (kappa^2 term differs)
    diag = q.diagonal()
    low_row = diag[0:nx].mean()      # near equator (range 800 -> small kappa)
    high_row = diag[(ny - 1) * nx :].mean()  # near 60N (range 100 -> larger kappa)
    assert not np.isclose(low_row, high_row, rtol=0.05)


def test_stationary_scalar_range_still_works():
    # Behavior: a scalar range provider keeps the stationary path intact.
    from sverdrup.core.parameters import ConstantProvider

    p = ConstantProvider({"range": 300.0, "variance": 0.05, "temporal_taper_scale": 10.0})
    dist = MaternGMRF().solve(_obs(), _grid(), p, 2.0)
    assert np.isfinite(dist.marginal_variance()).all()
```

- [ ] **Step 2: Run — confirm fail**

Run: `pixi run test tests/test_nonstationary_kappa.py -v`
Expected: FAIL — `MaternGMRF.solve` calls `float(params.resolve("range", grid))`, which raises on a field (`TypeError: only size-1 arrays can be converted to Python scalars`).

- [ ] **Step 3: Make `solve` accept a κ field** — `src/sverdrup/methods/gmrf.py`, in `MaternGMRF.solve`, replace the κ derivation:

```python
        rng_resolved = params.resolve("range", grid)
        tau = float(params.resolve("variance", grid))
        taper = float(params.resolve("temporal_taper_scale", grid))
        if np.isscalar(rng_resolved) or np.asarray(rng_resolved).ndim == 0:
            kappa: float | np.ndarray = kappa_from_range(float(rng_resolved))
            range_repr = float(rng_resolved)
        else:
            kappa = kappa_from_range(np.asarray(rng_resolved))  # elementwise field
            range_repr = "field(lat-varying)"
        q_prior = matern_precision(grid, kappa, tau)
```

`kappa_from_range`/`range_from_kappa` already work elementwise on arrays (pure numpy). Add `range_repr` to the provenance params:

```python
                    params={
                        "temporal_taper": "diagonal-R; under-uses temporal structure "
                        "(conservative). OI carries a full space-time kernel; GMRF "
                        "carries spatial cov + temporally-tapered likelihood.",
                        "temporal_taper_scale": taper,
                        "range": range_repr,
                        "kappa_range_mapping": "range = sqrt(8*nu)/kappa, nu=1",
                    },
```

- [ ] **Step 4: Run nonstationary tests + GMRF method tests + full suite**

Run: `pixi run test tests/test_nonstationary_kappa.py tests/unit/test_gmrf_method.py -v` → PASS
Run: `pixi run test -q` → all green

- [ ] **Step 5: Commit**

```bash
git add src/sverdrup/methods/gmrf.py tests/test_nonstationary_kappa.py
pixi run pre-commit run --files src/sverdrup/methods/gmrf.py tests/test_nonstationary_kappa.py
git commit -m "feat: nonstationary-kappa GMRF demo — provider-driven latitude-varying range -> spatially-varying Q"
```

---

## Definition of done (spec §7) — coverage map

- **Stage A (Tasks 1–3):** relocated coherence seam (Task 2), representation-tagged persisted form + widened `BlendInput` (Tasks 2, 7), per-operator reduction (Task 1); Phase-2 suite green through the refactor (Task 3 gate).
- **Stage B (Tasks 4–9):** Matérn GMRF at `Method.solve` (Task 6), EXACT sparse-precision operator (Tasks 5–6), sparse Cholesky core + Takahashi (Task 5), provider-driven κ (Tasks 6, 11), `SAMPLES + COVARIANCE` (Task 6), gridded + off-grid W eval predictives (Task 6), method-agnostic blend on GMRF seam-free/no-dip/single-tile-ref/conservative + OSSE+OSE + provenance + genuine-first-class (Tasks 8–9).
- **Stage C (Tasks 10–11):** degradation path end-to-end with coherence loss recorded, no silent seam (Task 10); latitude-varying-κ demo (Task 11).

## Final self-review notes
- Spec §4(a) coherence seam → Task 2 + (GMRF) Task 8 + (degradation) Task 10. §4(b) persisted tag → Tasks 2, 7. §4(c) reduction boundary → Tasks 1, 7. §5.1 GMRF → Tasks 4–6. §5.2 PrecisionFields → Task 7. §5.5 degradation → Task 10. §5.6 nonstationary → Task 11. §5.1 sparse backend + temporal taper + Projection → Tasks 4–6. B6 moment-crossfade + provenance note → Task 9.
- Invariant 1 (protocols unmodified): `to_persisted` is NOT on the core Protocol — it's `ReductionStrategy` in `distributions/` (Task 1). `Method`/`PredictiveDistribution`/`CovarianceOperator` are untouched; GMRF implements them as they stand.
- Invariant 6 (one L for all three): `GMRFFactor` serves sample/solve/selective-inverse (Tasks 5–6).
- Invariant 7 (generalize under green): Task 3 hard gate.
- Type consistency: `sampler_spec` values `"lowrank+diag"` / `"sparse-precision"` / `"perturb-ensemble"` used identically across `reduction.py`, `coherent.py`, `persisted.py`. `select_reduction` (operator→strategy) vs `select_driver` (sampler_spec→driver) — the two-point split, named consistently.
