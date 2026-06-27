# Stage-B core-authoritative coherent sampler — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **SUPERSEDED 2026-06-27 — PHASE BOUNDARY (read PROGRESS "RESUME HERE (2026-06-27)" first).** The
> range-sweep certification (Task 5) was executed early and PROVED **case (b)**: overwrite zeroes the
> cross-seam covariance at operational range (its carrier is the near-improper global mode; near-null
> deflation killed by measurement). Disposition: overwrite landed as a **non-default reference**
> (`GmrfCoreAuthoritativeSolve`); the `sparse-precision` default STAYS `GmrfTreeKrigingSolve`; the
> default choice + the decomposition redesign are a **Phase-5 milestone**. Executed reality = Task 1
> (`d173561`) + Disp-A (`64a2b32`) + Disp-B (`006aa7a`) + Disp-C. **Tasks 2, 4, 5, 6 below are
> superseded** (no registry repoint; no tree-machinery retirement; the cert gate became the
> boundary-characterization + strict-xfail acceptance gate in `tests/test_core_authoritative_gate.py`).

**Goal:** Replace the variance-collapsing spanning-tree hand-forward coherent sampler with a per-node **core-authoritative two-pass (overwrite)** sampler, and certify it across a `range` sweep on a production-representative fixture.

**Architecture:** Each output node belongs to exactly one tile's disjoint core; the coherent draw at that node is that owning core's unconditional posterior draw (Pass 1), and every tile's halo nodes are **overwritten** with the owning neighbour's authoritative value (Pass 2) — no `Σ_ss` solve. The spanning-tree machinery dissolves. Coherence is exact at shared nodes by construction; the marginal contract is honored because each node carries its authoritative core variance.

**Tech Stack:** Python, numpy, scipy.sparse, scikit-sparse (CHOLMOD), pytest, pixi.

**User decisions (already made):**
- "per-node core-ownership, two-pass" — authority is per-node (disjoint cores), flips node-by-node; no per-edge orientation.
- "OVERWRITE leads" — halo ← owning core's actual draw, no `Σ_ss` solve (measured: marginal strict-min 0.881 vs the MST's 1.76e-7).
- "certify across a RANGE SWEEP on the production fixture, NOT a single pass" — distinguishes case (a) overwrite-sufficient from (b) core-mode-disagreement.
- "ASSERT the two tiles compute the same cross-seam derived quantity" — overwrite cleanliness gate.
- "ownership tie-break IDENTICAL to partition_weights" — assert `owner == argmax(partition_weights)`.
- "eigmin-machinery retirement deferred until the sweep rules out case (b)."
- "rule (i): strict-min over physical seam pairs — no median/percentile/aggregate."
- Reconciliation (case b) is NOT cheap (no spectral gap) and NOT built now — possible phase-boundary; stop-and-surface.

Design doc: `docs/superpowers/specs/2026-06-27-stageb-seam-overpinning-fix-design.md` (committed `27030b1`).

---

## File Structure

- `src/sverdrup/distributions/coherent.py` — add `_core_owner_of_keys`, `_core_owner_of_points`, class `GmrfCoreAuthoritativeSolve`; repoint `_DRIVERS["sparse-precision"]`. (Spanning-tree symbols stay until Task 6.)
- `tests/unit/_tree_gate.py` — replace the median `edge_dir_ratio` with **strict-min**; add `marginal_contract_ratios` (sample vs `(Σwσ)²`); add `make_grid_diagonal(...)` production-representative fixture builder with a tunable `range`.
- `tests/test_core_authoritative_gate.py` (new) — the strict-min certification gate: marginal + direction across a `range` sweep on the production fixture; the overwrite cleanliness assertion.
- `tests/unit/_tree_gate.py` import surface is currently broken by the spanning-tree revert (imports removed `_min_eccentricity_spanning_tree`/`_condition_root_scores`); Task 1 repairs it.

---

## Task 1: Core-ownership map + ownership==weights agreement

**Goal:** A per-node map from each support node to the index of the tile whose disjoint **core** owns it, with the tie-break asserted identical to `partition_weights`, and the broken `_tree_gate.py` imports repaired.

**Files:**
- Modify: `src/sverdrup/distributions/coherent.py` (add `_core_owner_of_points`, `_core_owner_of_keys`)
- Modify: `tests/unit/_tree_gate.py` (remove the now-dead `_min_eccentricity_spanning_tree`/`_condition_root_scores` imports so the module imports again)
- Test: `tests/test_core_authoritative_gate.py` (new)

**Acceptance Criteria:**
- [ ] `_core_owner_of_points(parts, pts, t)` returns an int array, one owner per point, every point owned (no `-1`); raises `AssertionError` if a point lies in no core (cores don't cover).
- [ ] On a real natl60 2×2 fixture, `owner == np.argmax(partition_weights([p.tile for p in parts], pts), axis=0)` at **every** point (ownership tie-break matches the weight convention).
- [ ] `tests/unit/_tree_gate.py` imports without error (dead spanning-tree symbols removed).

**Verify:** `pixi run python -m pytest tests/test_core_authoritative_gate.py::test_core_ownership_matches_weights -v` → PASS

**Steps:**

- [ ] **Step 1: Repair `_tree_gate.py` imports.** In `tests/unit/_tree_gate.py`, delete `_condition_root_scores` and `_min_eccentricity_spanning_tree` from the `from sverdrup.distributions.coherent import (...)` block (they were removed when the min-ecc star regression was reverted). Leave the rest of the harness intact.

- [ ] **Step 2: Write the failing test** in `tests/test_core_authoritative_gate.py`:

```python
"""Stage-B core-authoritative coherent sampler gate (strict-min, rule i)."""
from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("sksparse")

from sverdrup.distributions.blend import partition_weights  # noqa: E402
from sverdrup.distributions.coherent import _core_owner_of_points  # noqa: E402
from tests.unit._tree_gate import make_natl60  # noqa: E402


def test_core_ownership_matches_weights():
    fix = make_natl60(2, 2)
    pts = fix.pts
    owner = _core_owner_of_points(fix.parts, pts, 2.0)
    assert (owner >= 0).all(), "every output node must have a core owner"
    w = partition_weights([p.tile for p in fix.parts], pts)  # (T, n)
    assert np.array_equal(owner, np.argmax(w, axis=0)), (
        "core-ownership tie-break must match partition_weights' argmax at every node"
    )
```

- [ ] **Step 3: Run — confirm it fails** (`_core_owner_of_points` undefined):
Run: `pixi run python -m pytest tests/test_core_authoritative_gate.py::test_core_ownership_matches_weights -v`
Expected: FAIL (ImportError / AttributeError).

- [ ] **Step 4: Implement** in `src/sverdrup/distributions/coherent.py` (place near `_tile_adjacency`):

```python
def _core_owner_of_points(
    parts: Sequence[Any], pts: Points, time_days: float
) -> np.ndarray:
    """Return the owning-tile index for each point, by disjoint-core membership.

    Cores partition the domain, so each point lies in exactly one core. Boundary
    points are assigned to the lowest-index core that contains them (closed lower /
    closed upper membership, first-wins) — which coincides with ``argmax`` of the
    partition-of-unity weights (asserted by the gate). A point in no core is a loud
    red: the cores do not cover the output grid.
    """
    n = pts.shape[0]
    owner = np.full(n, -1, dtype=int)
    for i, p in enumerate(parts):
        (lo_lon, hi_lon) = p.tile.core_window.lon_range
        (lo_lat, hi_lat) = p.tile.core_window.lat_range
        inside = (
            (pts[:, 0] >= lo_lon - 1e-9)
            & (pts[:, 0] <= hi_lon + 1e-9)
            & (pts[:, 1] >= lo_lat - 1e-9)
            & (pts[:, 1] <= hi_lat + 1e-9)
        )
        take = inside & (owner < 0)
        owner[take] = i
    if (owner < 0).any():
        raise AssertionError(
            f"{int((owner < 0).sum())} output node(s) lie in no tile core — the cores "
            "do not cover the output grid (would be silently unowned)"
        )
    return owner


def _core_owner_of_keys(
    parts: Sequence[Any], time_days: float
) -> dict[tuple[float, float], int]:
    """Return ``{node-key: owning-tile index}`` over the union of tile supports."""
    keys: dict[tuple[float, float], int] = {}
    pts_per_tile = [
        (_support_points(p.distribution.grid, time_days), p) for p in parts
    ]
    for i, p in enumerate(parts):
        (lo_lon, hi_lon) = p.tile.core_window.lon_range
        (lo_lat, hi_lat) = p.tile.core_window.lat_range
        for k in _node_keys(_support_points(p.distribution.grid, time_days)):
            if (
                lo_lon - 1e-9 <= k[0] <= hi_lon + 1e-9
                and lo_lat - 1e-9 <= k[1] <= hi_lat + 1e-9
                and k not in keys
            ):
                keys[k] = i
    return keys
```

- [ ] **Step 5: Run — confirm pass** (and `_tree_gate.py` imports):
Run: `pixi run python -m pytest tests/test_core_authoritative_gate.py::test_core_ownership_matches_weights -v`
Expected: PASS.

- [ ] **Step 6: Commit.**
```bash
git add src/sverdrup/distributions/coherent.py tests/unit/_tree_gate.py tests/test_core_authoritative_gate.py
git commit -m "feat(phase4): per-node core-ownership map + ownership==weights agreement (Stage B)"
```

---

## Task 2: `GmrfCoreAuthoritativeSolve` overwrite driver + registry repoint

**Goal:** The two-pass overwrite driver: independent per-tile draws (Pass 1), halo nodes overwritten with the owning core's value (Pass 2); registered as the `sparse-precision` coherent driver; and a marginal-contract regression test proving the seam collapse is gone.

**Files:**
- Modify: `src/sverdrup/distributions/coherent.py` (class `GmrfCoreAuthoritativeSolve`; repoint `_DRIVERS["sparse-precision"]`)
- Modify: `tests/unit/_tree_gate.py` (add `marginal_contract_ratios`)
- Test: `tests/test_core_authoritative_gate.py`

**Acceptance Criteria:**
- [ ] `select_driver("sparse-precision")` returns a `GmrfCoreAuthoritativeSolve`.
- [ ] On real natl60 2×2, the coherent sample's `marginal_contract_ratios` strict-min ≥ 0.5 (the MST driver gave 1.76e-7 — collapse gone; measured overwrite ≈ 0.88).
- [ ] `tests/test_gmrf_blend.py` still passes (the existing single-tile / chain coherence tests; a 1-tile blend is a no-op patchwork).

**Verify:** `pixi run python -m pytest tests/test_core_authoritative_gate.py::test_marginal_contract_honored tests/test_gmrf_blend.py -v` → PASS

**Steps:**

- [ ] **Step 1: Add the harness helper** `marginal_contract_ratios` to `tests/unit/_tree_gate.py` (inside `GateFixture`):

```python
    def sigma_contract(self) -> np.ndarray:
        """Reported marginal std field (Σ_i w_i σ_i) over output points."""
        w = partition_weights([p.tile for p in self.parts], self.pts)  # (T, n)
        sig = np.zeros((len(self.parts), self.pts.shape[0]))
        for i, p in enumerate(self.parts):
            mv = np.ravel(cast(Any, p.distribution).marginal_variance())
            for nn, k in enumerate(_node_keys(_support_points(p.distribution.grid, _T))):
                g = self.key2g.get((round(k[0], 6), round(k[1], 6)))
                if g is not None:
                    sig[i, g] = np.sqrt(max(float(mv[nn]), 0.0))
        return np.asarray((w * sig).sum(axis=0))

    def marginal_contract_ratios(self, samples: np.ndarray) -> np.ndarray:
        """sample variance / (Σwσ)² at seam nodes with non-trivial reported variance."""
        contract = self.sigma_contract() ** 2
        sv = samples.var(axis=0)
        adj = _tile_adjacency(self.parts)
        seam = sorted({int(x) for (i, j) in adj for x in self._shared_gidx(i, j)})
        return np.array([sv[g] / contract[g] for g in seam if contract[g] > 10.0])
```
(`_node_keys`, `_support_points`, `_tile_adjacency`, `partition_weights`, `cast`, `Any`, `_T` are already imported in `_tree_gate.py`.)

- [ ] **Step 2: Write the failing test** in `tests/test_core_authoritative_gate.py`:

```python
from sverdrup.distributions.coherent import (  # noqa: E402
    GmrfCoreAuthoritativeSolve, NoiseSpec, select_driver,
)

_NOISE = NoiseSpec(method="gmrf", params_key="p", lattice_step=0.5)


def _samples(fix, m=400):
    from sverdrup.distributions.blend import partition_weights
    drv = GmrfCoreAuthoritativeSolve()
    w = partition_weights([p.tile for p in fix.parts], fix.pts)
    return np.stack([drv.crossfaded_member(fix.parts, fix.pts, w, k, _NOISE) for k in range(m)])


def test_marginal_contract_honored():
    assert isinstance(select_driver("sparse-precision"), GmrfCoreAuthoritativeSolve)
    fix = make_natl60(2, 2)
    ratios = fix.marginal_contract_ratios(_samples(fix))
    smin = float(ratios.min())
    print(f"\n[core-authoritative] marginal sample/contract strict-min = {smin:.3f}")
    assert smin >= 0.5, (
        f"seam marginal collapse not fixed: strict-min {smin:.3e} < 0.5 "
        "(MST driver was 1.76e-7) — overwrite is not honoring the contract"
    )
```

- [ ] **Step 3: Run — confirm it fails** (`GmrfCoreAuthoritativeSolve` undefined / registry still points at the tree driver):
Run: `pixi run python -m pytest tests/test_core_authoritative_gate.py::test_marginal_contract_honored -v`
Expected: FAIL.

- [ ] **Step 4: Implement the driver** in `coherent.py` (reuse `_crossfade`, `derive_seed`, `_support_points`, `_node_keys`):

```python
class GmrfCoreAuthoritativeSolve:
    """GMRF coherent driver: per-node core-authoritative two-pass (overwrite), spec 2026-06-27.

    Pass 1: every tile draws its INDEPENDENT unconditional posterior ``x_u = mean + L⁻ᵀw``
    (per-tile white, C2′). Each node's authoritative value is its disjoint-core owner's Pass-1
    draw. Pass 2: every tile's nodes are OVERWRITTEN with the authoritative value (core nodes are
    already authoritative; halo nodes take the owning neighbour's value) — no ``Σ_ss`` solve, so the
    near-improper posterior is never excited. Coherence is exact at shared nodes by construction and
    the marginal contract is honored because each node carries its authoritative core variance.
    """

    def _authoritative_fields(
        self, parts: Sequence[Any], time_days: float, member_index: int, noise: NoiseSpec
    ) -> list[np.ndarray]:
        keymaps = [
            _node_keys(_support_points(p.distribution.grid, time_days)) for p in parts
        ]
        owner = _core_owner_of_keys(parts, time_days)
        # Pass 1: independent per-tile unconditional draws
        drawn: list[np.ndarray] = []
        for i, p in enumerate(parts):
            d = p.distribution
            gpts = _support_points(d.grid, time_days)
            seed = derive_seed(noise.method, noise.params_key, f"gmrf-tile:{i}", member_index)
            white = np.random.default_rng(seed).standard_normal(len(gpts))
            drawn.append(d.fields.mean.ravel() + d._factor_obj().sample(white))
        # authoritative value per key = owning tile's Pass-1 draw at that key
        auth: dict[tuple[float, float], float] = {}
        for i, km in enumerate(keymaps):
            for n, k in enumerate(km):
                if owner.get(k) == i:
                    auth[k] = float(drawn[i][n])
        # Pass 2: overwrite every node with the authoritative value
        out: list[np.ndarray] = []
        for i, km in enumerate(keymaps):
            f = drawn[i].copy()
            for n, k in enumerate(km):
                f[n] = auth[k]
            out.append(np.asarray(f))
        return out

    def crossfaded_member(
        self, parts: Sequence[Any], pts: Points, weights: np.ndarray,
        member_index: int, noise: NoiseSpec,
    ) -> np.ndarray:
        """Realize one coherent member: core-authoritative patchwork, weight-crossfaded onto pts."""
        t = cast(Any, parts[0].distribution).time_days
        fields = self._authoritative_fields(parts, t, member_index, noise)
        return GmrfTreeKrigingSolve._crossfade(parts, pts, weights, fields)
```

- [ ] **Step 5: Repoint the registry.** Find the `_DRIVERS` dict in `coherent.py` (the `select_driver` table) and set the `"sparse-precision"` entry to `GmrfCoreAuthoritativeSolve`. Leave `GmrfTreeKrigingSolve`/`GmrfKrigingSolve` classes defined (referenced by other tests until Task 6).

- [ ] **Step 6: Run — confirm pass** (and the existing blend tests):
Run: `pixi run python -m pytest tests/test_core_authoritative_gate.py::test_marginal_contract_honored tests/test_gmrf_blend.py -v`
Expected: PASS. If `test_gmrf_blend.py` asserts MST-specific behavior, inspect — a 1-tile/chain blend under overwrite is the same patchwork; only change a test if it pins a property the design intentionally replaced, and surface that in the commit message.

- [ ] **Step 7: Commit.**
```bash
git add src/sverdrup/distributions/coherent.py tests/unit/_tree_gate.py tests/test_core_authoritative_gate.py
git commit -m "feat(phase4): GmrfCoreAuthoritativeSolve overwrite driver; repoint registry (Stage B)"
```

---

## Task 3: Overwrite cleanliness gate — both-perspectives cross-seam agreement

**Goal:** Assert the overwrite makes every cross-seam derived quantity single-valued: at every shared seam node, all covering tiles' (overwritten) field values agree, so a seam firstdifference computed from either adjacent tile's perspective is identical.

**Files:**
- Test: `tests/test_core_authoritative_gate.py`

**Acceptance Criteria:**
- [ ] For a real natl60 2×2, for every pair of adjacent tiles and every shared node, the two tiles' overwritten field values at that node are equal (to float tolerance) for several members.
- [ ] Consequently every cross-seam firstdifference (shared node a − shared node b) computed from tile A's field equals the one from tile B's field.

**Verify:** `pixi run python -m pytest tests/test_core_authoritative_gate.py::test_overwrite_seam_single_valued -v` → PASS

**Steps:**

- [ ] **Step 1: Write the test** (the assertion is the design's cleanliness gate — failing it sends Pass 2 back to conditioning):

```python
def test_overwrite_seam_single_valued():
    from sverdrup.distributions.coherent import (
        _node_keys, _support_points, _tile_adjacency,
    )
    fix = make_natl60(2, 2)
    drv = GmrfCoreAuthoritativeSolve()
    adj = _tile_adjacency(fix.parts)
    keymaps = [_node_keys(_support_points(p.distribution.grid, 2.0)) for p in fix.parts]
    for m in range(4):
        fields = drv._authoritative_fields(fix.parts, 2.0, m, _NOISE)
        for (i, j) in adj:
            ki = {k: n for n, k in enumerate(keymaps[i])}
            kj = {k: n for n, k in enumerate(keymaps[j])}
            shared = set(ki) & set(kj)
            for k in shared:
                vi, vj = fields[i][ki[k]], fields[j][kj[k]]
                assert abs(vi - vj) <= 1e-9, (
                    f"member {m} seam {i}-{j} node {k}: tiles disagree {vi} != {vj} "
                    "— overwrite is not single-valued; derived quantity would be double-valued"
                )
```

- [ ] **Step 2: Run — confirm pass** (it should pass by construction of `_authoritative_fields`; if it fails, the overwrite is applying inconsistent ownership and must be fixed before proceeding):
Run: `pixi run python -m pytest tests/test_core_authoritative_gate.py::test_overwrite_seam_single_valued -v`
Expected: PASS.

- [ ] **Step 3: Commit.**
```bash
git add tests/test_core_authoritative_gate.py
git commit -m "test(phase4): overwrite cleanliness gate — cross-seam single-valued (Stage B)"
```

---

## Task 4: Production-representative fixture (grid+diagonal) + strict-min metric

**Goal:** A fixture with **grid+diagonal** tile adjacency (not the degenerate K4/K9 complete graphs), with a tunable `range`, plus the **strict-min** conservative-direction metric replacing the banned median.

**Files:**
- Modify: `tests/unit/_tree_gate.py` (`edge_dir_ratio` → strict-min; add `make_grid_diagonal(n_lon, n_lat, range_km)`)
- Test: `tests/test_core_authoritative_gate.py`

**Acceptance Criteria:**
- [ ] `edge_dir_ratio` returns `min(ratios)` (strict-min over adjacent seam pairs), not `np.median` — rule (i).
- [ ] `make_grid_diagonal(3, 3, 300.0)` yields a partition whose tile-adjacency graph has **max degree ≤ 8 and is not complete** (grid+diagonal, not K9): `len(_tile_adjacency(parts)) < n*(n-1)/2`.

**Verify:** `pixi run python -m pytest tests/test_core_authoritative_gate.py::test_production_fixture_is_grid_not_complete -v` → PASS

**Steps:**

- [ ] **Step 1: Swap the metric to strict-min** in `tests/unit/_tree_gate.py::GateFixture.edge_dir_ratio` — change the final `return float(np.median(ratios)) if ratios else 1.0` to:
```python
        return float(min(ratios)) if ratios else 1.0
```
and update its docstring to state strict-min over adjacent seam pairs (rule i; median is banned because it laundered a real seam-node collapse).

- [ ] **Step 2: Add the production-representative fixture builder** to `tests/unit/_tree_gate.py`. It reuses `_build` (the real `MaternGMRF` solve path) over a larger synthetic grid where the halo is small relative to the tile so adjacency is grid+diagonal, not complete. `range_km` is tunable for the Task-5 sweep:

```python
def make_grid_diagonal(n_lon: int, n_lat: int, range_km: float = 150.0) -> GateFixture:
    """A real-solved n_lon x n_lat partition with GRID+DIAGONAL adjacency (not K_n).

    Larger domain + short-enough range so each tile's extended window overlaps only its
    grid/diagonal neighbours (maxdeg ~5-8), unlike the 8°/K_n natl60 fixtures. ``range_km``
    is swept by the certification gate (short range -> more near-improper).
    """
    lon = np.arange(0.0, 36.0)
    lat = np.arange(30.0, 42.0)
    grid = GridSpec.lonlat(lon, lat)
    from sverdrup.application.tiling import LonLatPartition, ScaleAwareHalo

    prov = ConstantProvider(
        {"range": range_km, "variance": 0.05, "temporal_taper_scale": 10.0}
    )
    tiles = list(
        LonLatPartition(
            n_lon, n_lat, ScaleAwareHalo(1.0),
            ConstantProvider({"correlation_length": range_km}), 10.0,
        ).tiles(grid)
    )
    olon, olat, oval = _scattered_obs_over(lon, lat)
    parts = []
    for tl in tiles:
        d = MaternGMRF().solve(_obs_in(olon, olat, oval, (tl.extended_window.lon_range,
                                                          tl.extended_window.lat_range)),
                               tl.grid, prov, _T)
        u = GMRFPrecisionReduction().reduce(d, tl.grid.points(_T), None, rank=0, seed=3)
        parts.append(BlendInput(
            PrecisionDistribution(tl.grid, cast(PrecisionFields, u.base_fields), d.provenance, _T),
            tl,
        ))
    gop = MaternGMRF().solve(
        ObsWindow.from_arrays(olon, olat, np.full(olon.size, _T), oval,
                              DiagonalErrorModel(np.full(olon.size, 1e-3))),
        grid, prov, _T,
    ).cov_op
    return GateFixture(parts, grid, gop)


def _scattered_obs_over(lon: np.ndarray, lat: np.ndarray):
    """A deterministic obs lattice spanning the domain so every tile has seam data."""
    olon, olat = np.meshgrid(np.linspace(lon[0] + 1, lon[-1] - 1, 12),
                             np.linspace(lat[0] + 1, lat[-1] - 1, 6))
    olon, olat = olon.ravel(), olat.ravel()
    oval = np.sin(0.3 * olon) + np.cos(0.4 * olat)
    return olon, olat, oval
```
(`GridSpec`, `ConstantProvider`, `MaternGMRF`, `GMRFPrecisionReduction`, `PrecisionDistribution`, `PrecisionFields`, `BlendInput`, `ObsWindow`, `DiagonalErrorModel`, `_obs_in`, `_T`, `cast` are already imported in `_tree_gate.py`.)

- [ ] **Step 3: Write the test:**
```python
def test_production_fixture_is_grid_not_complete():
    from sverdrup.distributions.coherent import _tile_adjacency
    from tests.unit._tree_gate import make_grid_diagonal
    fix = make_grid_diagonal(3, 3, 300.0)
    n = len(fix.parts)
    adj = _tile_adjacency(fix.parts)
    nbr = {k: set() for k in range(n)}
    for i, j in adj:
        nbr[i].add(j); nbr[j].add(i)
    maxdeg = max(len(v) for v in nbr.values())
    print(f"\n[production fixture] n={n} edges={len(adj)} maxdeg={maxdeg}")
    assert len(adj) < n * (n - 1) // 2, "fixture is a complete graph — not production-representative"
    assert maxdeg <= 8, f"maxdeg {maxdeg} > 8 — not grid+diagonal"
```

- [ ] **Step 4: Run — confirm pass.** If the adjacency is still complete, widen the domain or shorten `range_km` (per the geometry sweep: corr_len ≲ tile size gives grid+diagonal) until `maxdeg ≤ 8` and not complete.
Run: `pixi run python -m pytest tests/test_core_authoritative_gate.py::test_production_fixture_is_grid_not_complete -v`
Expected: PASS.

- [ ] **Step 5: Commit.**
```bash
git add tests/unit/_tree_gate.py tests/test_core_authoritative_gate.py
git commit -m "test(phase4): strict-min metric + grid+diagonal production fixture (Stage B)"
```

---

## Task 5: Range-sweep certification gate (USER-GATE)

**Goal:** Certify the overwrite sampler across a `range` sweep on the production fixture: marginal contract (strict-min) AND conservative direction (strict-min) at every range; classify **case (a)** (overwrite sufficient — direction floor holds across the whole sweep) vs **case (b)** (direction degrades as range shortens — core mode-disagreement, stop-and-surface).

> **USER-ORDERED GATE — NON-SKIPPABLE.** This task was requested by the user in the current conversation. It MUST NOT be closed by walking around it, by declaring it "verified inline", or by substituting a cheaper check. Close only after every item in `acceptanceCriteria` has been re-validated independently, with output captured.

**Files:**
- Test: `tests/test_core_authoritative_gate.py`

**Acceptance Criteria:**
- [ ] Marginal strict-min `sample/(Σwσ)²` ≥ 0.5 at **every** range in the sweep `[400, 200, 100, 50]` km on the production fixture (no seam-node collapse anywhere in the regime).
- [ ] Direction strict-min (blend/ref firstdifference variance ratio over adjacent seam pairs) is recorded at every range; the gate asserts it stays **≥ 0.9** across the whole sweep → **case (a)**, overwrite sufficient.
- [ ] If direction strict-min **degrades below 0.9 as range shortens** → **case (b)**: the test fails LOUDLY with the recorded sweep, surfacing reconciliation / the phase-boundary decision (design §4). The tolerance is never loosened to pass.
- [ ] Both metrics use **strict-min** (rule i); no median/percentile anywhere.

**Verify:** `pixi run python -m pytest tests/test_core_authoritative_gate.py::test_range_sweep_certification -v` → PASS (case a) or FAIL with the recorded degradation table (case b → stop-and-surface)

**Steps:**

- [ ] **Step 1: Write the certification test:**
```python
def test_range_sweep_certification():
    from tests.unit._tree_gate import make_grid_diagonal
    ranges = [400.0, 200.0, 100.0, 50.0]
    rows = []
    for r in ranges:
        fix = make_grid_diagonal(3, 3, r)
        bs = _samples(fix, m=600)
        rs = fix.ref_samples(m=600)
        marg = float(fix.marginal_contract_ratios(bs).min())
        adj = __import__("sverdrup.distributions.coherent", fromlist=["_tile_adjacency"])._tile_adjacency(fix.parts)
        direction = min(fix.edge_dir_ratio(bs, rs, i, j) for (i, j) in adj)
        rows.append((r, marg, direction))
        print(f"[cert] range={r:.0f}: marginal_strict_min={marg:.3f} direction_strict_min={direction:.3f}")
    # (a) marginal must never collapse anywhere in the regime
    for r, marg, _d in rows:
        assert marg >= 0.5, f"range {r:.0f}: marginal collapse {marg:.3e} < 0.5 (overwrite failed)"
    # (b) direction must stay conservative ACROSS the sweep — degradation as range shortens = case (b)
    worst = min(d for _r, _m, d in rows)
    assert worst >= 0.9, (
        "DIRECTION degrades across the range sweep (case b): cores disagree about the global "
        f"mode. Recorded {[(r, round(d,3)) for r,_m,d in rows]}. STOP — reconciliation / "
        "phase-boundary decision (design §4); do NOT loosen the tolerance."
    )
```

- [ ] **Step 2: Run the certification.**
Run: `pixi run python -m pytest tests/test_core_authoritative_gate.py::test_range_sweep_certification -v -s`
Expected: PASS = **case (a)**, overwrite is sufficient → proceed to Task 6. FAIL with the degradation table = **case (b)** → STOP and surface to the owner (reconciliation is not cheap; possible phase-boundary, design §4). Do not loosen the threshold.

- [ ] **Step 3: Commit** (only the test; behavior already shipped in Task 2).
```bash
git add tests/test_core_authoritative_gate.py
git commit -m "test(phase4): range-sweep certification gate, strict-min (Stage B user-gate)"
```

---

## Task 6: Retire eigmin + spanning-tree machinery (CONDITIONAL — blocked by Task 5 case-a)

**Goal:** Once the range sweep confirms **case (a)** (overwrite-alone sufficient), remove the now-dead spanning-tree and eigmin machinery; until then it stays (reconciliation may need it).

**Files:**
- Modify: `src/sverdrup/distributions/coherent.py` (remove `_max_overlap_spanning_tree`, `GmrfTreeKrigingSolve`, and any residual `_posterior_eigmin`/`_condition_root_scores` if present)
- Modify: `tests/unit/_tree_gate.py`, `tests/test_tree_kriging_gate.py` (remove spanning-tree-specific tests superseded by `tests/test_core_authoritative_gate.py`)

**Acceptance Criteria:**
- [ ] Only run this task if Task 5 passed as **case (a)**. If Task 5 surfaced **case (b)**, SKIP — the eigmin machinery is needed for reconciliation; stop and surface instead.
- [ ] `rg "GmrfTreeKrigingSolve|_max_overlap_spanning_tree|_posterior_eigmin|_condition_root_scores" src tests` returns no live references (only the new driver remains).
- [ ] Full suite green; `mypy .` and `ruff check .` clean.

**Verify:** `pixi run python -m pytest -q && pixi run typecheck && pixi run lint` → all green

**Steps:**

- [ ] **Step 1: Confirm Task 5 was case (a).** If not, STOP — do not delete; surface case (b) to the owner.
- [ ] **Step 2: Delete** `GmrfTreeKrigingSolve` and `_max_overlap_spanning_tree` from `coherent.py` (and any leftover `_posterior_eigmin`/`_condition_root_scores`). Remove the obsolete `tests/test_tree_kriging_gate.py` (its coverage is replaced by `tests/test_core_authoritative_gate.py`).
- [ ] **Step 3: Run the full suite + typecheck + lint.**
Run: `pixi run python -m pytest -q && pixi run typecheck && pixi run lint`
Expected: all green.
- [ ] **Step 4: Commit.**
```bash
git add -A
git commit -m "refactor(phase4): retire spanning-tree + eigmin machinery (overwrite certified case a)"
```

---

## Self-Review

**Spec coverage:** §1 architecture → Tasks 1–2; §2 ownership map + ==weights → Task 1; §3 overwrite + cleanliness gate → Tasks 2–3; §4 sub-question B / range sweep → Task 5; §5 production fixture → Task 4; §6 verification strict-min → Tasks 4–5; §8 retirement deferred → Task 6 (conditional, blocked by Task 5 case-a). Sub-question A is dissolved by overwrite (no solve) — no task needed, noted in Task 2. Reconciliation (case b) is intentionally NOT a task (stop-and-surface).

**Placeholder scan:** every code step shows complete code; verify commands are exact; no TBD/TODO.

**Type consistency:** `_core_owner_of_points`/`_core_owner_of_keys`, `GmrfCoreAuthoritativeSolve._authoritative_fields`/`crossfaded_member`, `GateFixture.sigma_contract`/`marginal_contract_ratios`/`edge_dir_ratio`(strict-min)/`make_grid_diagonal` names are used consistently across tasks; `_crossfade` is reused from `GmrfTreeKrigingSolve` (still defined until Task 6).
