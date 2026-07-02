# Stage-C Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite Phase-5 Stage C so the coherence feasibility barrier is capability-conditional and keyed on tile count (not the refuted `core/range ≥ 25`), quantifying the measured joint cross-seam boundary and shipping the marginal product.

**Architecture:** `CoherenceFeasibility` becomes capability-conditional + tile-count-keyed: `SAMPLES/COVARIANCE` gated at `n_star_joint=1` (empty region — measured), `MARGINAL_VARIANCE` gated at a flat marginal-error tolerance (ships), `POINT` free. The hard-barrier loop and worst-case-localized reduction are kept, re-pointed at the validated adjacent-seam correlation-error metric. The heavy measurement stays in `scripts/diag_crossseam.py`; a thin `tuning/tradeoff.py` consumer bakes the measured curve into a both-tiers owner-facing frontier doc. The coarse-correction fix stays owner-deferred.

**Tech Stack:** Python, numpy, pytest, the existing `application/tuning/` seams (`loop.tune`, `FeasibilityPredicate`, `TrialScorer`), `sverdrup.core.types.UncertaintyCapability`.

**User decisions (already made):**
- "coherent = joint cross-seam covariance, capability-scoped" — SAMPLES/COVARIANCE gated on joint worst-case; MARGINAL_VARIANCE a separate looser tier; POINT free.
- "key on TILE COUNT, not core/range" — cores don't rescue it (measured).
- "ship a DEFAULT, swappable: tol=0.5" — joint region empty regardless (tolerance-invariant headline).
- "empty region under invariant-6 worst-case" — `n_star_joint=1`; the `feasible iff N≤n_star_joint` form is the tol=0.5 empty-region shorthand only (worst-of-K is non-monotone in N).
- "MARGINAL_VARIANCE ships conditional on ~15% flat marginal error" — named swappable `marg_tol` (default 0.20), measured `marg_worst_case≈0.15`.
- "measurement stays in scripts/diag_crossseam.py; tradeoff.py is the thin consumer" — predicate stays cheap (baked constants); no measurement in the loop.
- "coarse-correction stays owner-deferred (§6)" — this plan does NOT build it; it surfaces the input.
- "concrete strict-xfail" — a SAMPLES/COVARIANCE N≥2 product asserted feasible, xfail until the deferred fix widens `n_star_joint`.

**Supersedes:** Tasks 15–18 of `docs/superpowers/plans/2026-06-28-phase5-autotune-loop.md` (their `core/range ≥ 25` premise is refuted). Source of truth: `docs/superpowers/specs/2026-07-01-stagec-redesign-design.md`.

**Non-breaking note:** `TileGeometry` gains `n_tiles` as an **appended, defaulted** field (`n_tiles: int = 1`, last position), so the ~11 existing positional `TileGeometry(core, range, id)` call sites keep working. `stage_a.py`/`stage_b.py` pass no `SAMPLES/COVARIANCE` capability, so the rewritten predicate returns `True` for them unchanged.

---

## Task 1: Capability-conditional, tile-count-keyed `CoherenceFeasibility`

**Goal:** Replace the `core/range ≥ 25` predicate with a capability-conditional, tile-count-keyed one; add `n_tiles` to `TileGeometry`; rekey `RelaxedCoherenceFeasibility`.

**Files:**
- Modify: `src/sverdrup/application/tuning/feasibility.py`
- Modify: `tests/test_tuning_feasibility.py`

**Acceptance Criteria:**
- [ ] `TileGeometry` has an appended `n_tiles: int = 1` field; existing positional `TileGeometry(core, range, id)` construction still works.
- [ ] `CoherenceFeasibility().feasible(...)` returns `False` for `{SAMPLES}` or `{COVARIANCE}` when `n_tiles ≥ 2` (default `n_star_joint=1`), `True` when `n_tiles == 1`.
- [ ] For `{MARGINAL_VARIANCE}`: `True` iff `marg_worst_case ≤ marg_tol` (default `0.15 ≤ 0.20` → `True`); flipping `marg_tol=0.10` → `False`, independent of `n_tiles`.
- [ ] For `{POINT}` (or empty joint requirement): always `True` regardless of `n_tiles`.
- [ ] `RelaxedCoherenceFeasibility(n_star_joint=64)` returns `True` for `{SAMPLES}` at `n_tiles=9` (widened region), with no change elsewhere.
- [ ] `KM_PER_DEG` and the `core/range` ratio arithmetic are removed from `feasibility.py`.

**Verify:** `pixi run test tests/test_tuning_feasibility.py -v` → pass; `pixi run typecheck` → clean.

**Steps:**

- [ ] **Step 1: Rewrite the failing tests** (replace the whole `core/range` test file body)

```python
# tests/test_tuning_feasibility.py
"""The capability-conditional, tile-count-keyed coherence feasibility predicate."""

from __future__ import annotations

from sverdrup.application.tuning.feasibility import (
    CoherenceFeasibility,
    RelaxedCoherenceFeasibility,
    TileGeometry,
)
from sverdrup.core.types import UncertaintyCapability

SAMPLES = frozenset({UncertaintyCapability.SAMPLES})
COVARIANCE = frozenset({UncertaintyCapability.COVARIANCE})
MARGINAL = frozenset({UncertaintyCapability.MARGINAL_VARIANCE})
POINT = frozenset({UncertaintyCapability.POINT})


def _geom(n_tiles: int) -> TileGeometry:
    return TileGeometry(core_size_deg=4.0, range_km=300.0, tiling_id="g", n_tiles=n_tiles)


def test_samples_infeasible_at_multi_tile() -> None:
    # Bug it catches: a predicate that lets a multi-tile joint product through
    # (the measured empty region — joint worst-case > tol at every N>=2).
    p = CoherenceFeasibility()
    assert p.feasible({}, _geom(2), SAMPLES) is False
    assert p.feasible({}, _geom(9), COVARIANCE) is False
    assert p.feasible({}, _geom(1), SAMPLES) is True  # untiled single-tile is joint-valid


def test_marginal_ships_conditional_on_tol() -> None:
    # Bug it catches: burying the ~15% marginal-error acceptance in a constant so a
    # stricter tolerance silently still "ships".
    assert CoherenceFeasibility().feasible({}, _geom(9), MARGINAL) is True   # 0.15 <= 0.20
    strict = CoherenceFeasibility(marg_tol=0.10)
    assert strict.feasible({}, _geom(9), MARGINAL) is False                  # 0.15 > 0.10
    # flat in N: same verdict at any tile count
    assert strict.feasible({}, _geom(2), MARGINAL) is False


def test_point_unconstrained() -> None:
    p = CoherenceFeasibility()
    assert p.feasible({}, _geom(9), POINT) is True
    assert p.feasible({}, _geom(999), frozenset()) is True


def test_relaxed_widens_joint_region() -> None:
    # TEST 6 (redesign interface): a relaxed predicate widens n_star_joint, tuner unchanged.
    default = CoherenceFeasibility()
    relaxed = RelaxedCoherenceFeasibility(n_star_joint=64)
    assert default.feasible({}, _geom(9), SAMPLES) is False
    assert relaxed.feasible({}, _geom(9), SAMPLES) is True
```

- [ ] **Step 2: Run — confirm fail**

Run: `pixi run test tests/test_tuning_feasibility.py -v`
Expected: FAIL (old `CoherenceFeasibility` has no `n_tiles`/`marg_tol`; `TileGeometry` has no `n_tiles`).

- [ ] **Step 3: Rewrite `feasibility.py`**

```python
# src/sverdrup/application/tuning/feasibility.py
"""Pluggable feasibility predicate: the coherence barrier (Phase-5; Stage-C redesign 2026-07-01).

Capability-conditional (invariant 4) + tile-count-keyed. Replaces the refuted core/range >= 25
bound (a GMRF-prior-bug artifact, fixed in 6cce45b). Measured boundary + provenance:
docs/superpowers/specs/2026-07-01-stagec-redesign-design.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from sverdrup.core.types import UncertaintyCapability

_JOINT_CAPS = frozenset(
    {UncertaintyCapability.SAMPLES, UncertaintyCapability.COVARIANCE}
)


@dataclass(frozen=True)
class TileGeometry:
    """The geometry the coherence predicate keys on.

    ``n_tiles`` is the joint-tier key. ``core_size_deg``/``range_km`` are recorded context for
    the frontier artifact only — the predicate ignores them (measured: tile count, not
    core/range, drives the joint worst-case). ``n_tiles`` is appended + defaulted so the
    pre-redesign positional ``TileGeometry(core, range, id)`` call sites keep working.
    """

    core_size_deg: float
    range_km: float
    tiling_id: str
    n_tiles: int = 1


@runtime_checkable
class FeasibilityPredicate(Protocol):
    """Decide whether a trial may be solved+scored at all (hard barrier, invariant 3)."""

    def feasible(
        self,
        params: dict[str, float],
        tile_geometry: TileGeometry,
        required_capabilities: frozenset[UncertaintyCapability],
    ) -> bool:
        """Return True iff the trial is feasible to solve and score."""
        ...


@dataclass(frozen=True)
class CoherenceFeasibility:
    """Default: capability-conditional + tile-count-keyed (design 2026-07-01).

    - SAMPLES/COVARIANCE (joint): feasible iff ``n_tiles <= n_star_joint``. Default
      ``n_star_joint=1`` is the tol=0.5 EMPTY-REGION shorthand — measured worst-of-K adjacent-seam
      corr-err exceeds ``joint_tol`` at every tested N>=2 (non-monotone in N; NOT a monotone law).
    - MARGINAL_VARIANCE: feasible iff ``marg_worst_case <= marg_tol`` — FLAT in N (measured ~15%),
      so ships iff ``marg_tol >= ~0.15``, tile-count-independent.
    - POINT / no joint requirement: always feasible (no seams).

    Predicate is CHEAP (baked constants); the heavy measurement is offline in
    ``scripts/diag_crossseam.py``, preserving the gate-before-solve hard barrier (invariant 3).
    """

    joint_tol: float = 0.5
    n_star_joint: int = 1
    marg_tol: float = 0.20
    marg_worst_case: float = 0.15  # MEASURED, FLAT in tile count (design §2)

    def feasible(
        self,
        params: dict[str, float],
        tile_geometry: TileGeometry,
        required_capabilities: frozenset[UncertaintyCapability],
    ) -> bool:
        """Return the capability-scoped, tile-count-keyed feasibility verdict."""
        if required_capabilities & _JOINT_CAPS:
            return tile_geometry.n_tiles <= self.n_star_joint
        if UncertaintyCapability.MARGINAL_VARIANCE in required_capabilities:
            return self.marg_worst_case <= self.marg_tol
        return True


@dataclass(frozen=True)
class RelaxedCoherenceFeasibility:
    """The redesign's interface (invariant 5): widens the joint region, tuner untouched.

    The owner-deferred coarse-correction supplies this. ``n_star_joint`` here is ILLUSTRATIVE of
    the mechanism (a wider tile-count bound), NOT a measured value — the fix is unbuilt.
    """

    n_star_joint: int = 64
    marg_tol: float = 0.20
    marg_worst_case: float = 0.15

    def feasible(
        self,
        params: dict[str, float],
        tile_geometry: TileGeometry,
        required_capabilities: frozenset[UncertaintyCapability],
    ) -> bool:
        """Same body as the default, reading the widened bounds."""
        if required_capabilities & _JOINT_CAPS:
            return tile_geometry.n_tiles <= self.n_star_joint
        if UncertaintyCapability.MARGINAL_VARIANCE in required_capabilities:
            return self.marg_worst_case <= self.marg_tol
        return True
```

- [ ] **Step 4: Run — confirm pass**

Run: `pixi run test tests/test_tuning_feasibility.py -v` → PASS.

- [ ] **Step 5: Fix the one collateral loop test** (it asserted infeasibility via the old ratio)

Open `tests/test_tuning_loop.py`. At the infeasible-trial test (~line 60) the geometry `TileGeometry(12.0, 400.0, "g")` was infeasible via `ratio ≈ 3.3 < 25`. Under the new predicate that geometry is `n_tiles=1` → feasible. Make it infeasible the new way: pass `SAMPLES` capability and `n_tiles=2`.

Find:
```python
    geom = TileGeometry(12.0, 400.0, "g")  # ratio ~3.3 < 25 -> infeasible
```
Replace with:
```python
    geom = TileGeometry(12.0, 400.0, "g", n_tiles=2)  # multi-tile joint -> infeasible
```
Then ensure that test's `required_capabilities` includes `SAMPLES` (it must, for the joint barrier to bind). If the test builds `required_capabilities=frozenset()` or a POINT set, change it to `frozenset({UncertaintyCapability.SAMPLES})` and add the import `from sverdrup.core.types import UncertaintyCapability` if absent. Run `pixi run test tests/test_tuning_loop.py -v` and adjust only the assertions that encoded the ratio semantics — the loop's gate-before-solve behavior is unchanged.

- [ ] **Step 6: Run the tuning suite + typecheck**

Run: `pixi run test tests/test_tuning_feasibility.py tests/test_tuning_loop.py tests/test_tuning_bayesopt.py tests/test_tuning_method_agnostic.py -v` → all pass (stage_a/b paths unaffected: no joint caps).
Run: `pixi run typecheck` → clean.

- [ ] **Step 7: Commit**

```bash
git add src/sverdrup/application/tuning/feasibility.py tests/test_tuning_feasibility.py tests/test_tuning_loop.py
git commit -m "feat(tuning): capability-conditional tile-count CoherenceFeasibility (retire core/range>=25)"
```

---

## Task 2: Stage-C loop wiring — hard barrier at multi-tile joint scale

**Goal:** Drive the GMRF tuner in the global multi-tile coherent mode (`required_capabilities={SAMPLES}`, `TileGeometry.n_tiles=N`) and prove a multi-tile joint trial is excluded before any solve.

**Files:**
- Create: `src/sverdrup/application/tuning/stage_c.py`
- Create: `tests/test_stage_c_hard_barrier.py`

**Acceptance Criteria:**
- [ ] `tile_geometry_for(n_tiles, params)` returns `TileGeometry(core_size_deg=…, range_km=params["range"], tiling_id=…, n_tiles=n_tiles)`.
- [ ] `run_stage_c_loop(n_tiles, strategy, predicate, objective, scorer, seed, on_empty)` runs `tune(...)` with `required_capabilities=frozenset({SAMPLES})` and the per-run `TileGeometry(n_tiles=n_tiles)`.
- [ ] **Test 4 (global):** with `n_tiles=9` and `CoherenceFeasibility()`, EVERY proposed trial is recorded `feasible=False, scores=None` and the scorer's `.score` is **never** called (spy asserts zero calls); with `n_tiles=1` the scorer IS called.

**Verify:** `pixi run test tests/test_stage_c_hard_barrier.py -v` → pass.

**Steps:**

- [ ] **Step 1: Write the failing test**

```python
# tests/test_stage_c_hard_barrier.py
"""Stage C: the joint coherence barrier binds; multi-tile joint trials are never solved."""

from __future__ import annotations

from sverdrup.application.tuning.feasibility import CoherenceFeasibility
from sverdrup.application.tuning.objective import ConstrainedObjective
from sverdrup.application.tuning.stage_c import run_stage_c_loop, tile_geometry_for
from sverdrup.application.tuning.strategy import RandomSearch


class _SpyScorer:
    def __init__(self) -> None:
        self.calls = 0

    def score(self, method_name, params, split, seed, window):
        self.calls += 1
        return {"lambda_x": 120.0, "mu_score": 0.86, "coverage_1sigma": 0.68}


def test_multi_tile_joint_trials_never_scored() -> None:
    # TEST 4 (global): n_tiles>=2 with SAMPLES -> excluded before any solve (empty region).
    scorer = _SpyScorer()
    result = run_stage_c_loop(
        n_tiles=9,
        strategy=RandomSearch(seed=1, n=24),
        predicate=CoherenceFeasibility(),
        objective=ConstrainedObjective(),
        scorer=scorer,
        seed=1,
        on_empty="return_history",
    )
    assert scorer.calls == 0  # decisive: no solve for any infeasible trial
    excluded = [rec for rec in result.history.records if not rec.feasible]
    assert excluded and all(rec.scores is None for rec in excluded)


def test_single_tile_is_scored() -> None:
    # n_tiles=1 -> joint-valid -> the scorer runs.
    scorer = _SpyScorer()
    run_stage_c_loop(
        n_tiles=1,
        strategy=RandomSearch(seed=1, n=4),
        predicate=CoherenceFeasibility(),
        objective=ConstrainedObjective(),
        scorer=scorer,
        seed=1,
        on_empty="return_history",
    )
    assert scorer.calls > 0


def test_tile_geometry_carries_n_tiles() -> None:
    geom = tile_geometry_for(n_tiles=9, params={"range": 80.0})
    assert geom.n_tiles == 9 and geom.range_km == 80.0
```

- [ ] **Step 2: Run — confirm fail**

Run: `pixi run test tests/test_stage_c_hard_barrier.py -v`
Expected: FAIL (`ModuleNotFoundError: ...stage_c`).

- [ ] **Step 3: Implement**

```python
# src/sverdrup/application/tuning/stage_c.py
"""Stage-C wiring: the global multi-tile coherent mode where the joint barrier binds.

The feasibility predicate keys on tile count (design 2026-07-01): at the default
n_star_joint=1 any n_tiles>=2 SAMPLES/COVARIANCE trial is excluded before solve. The loop's
gate-before-solve guarantee makes the barrier hard (test 4).
"""

from __future__ import annotations

from sverdrup.application.tuning.feasibility import FeasibilityPredicate, TileGeometry
from sverdrup.application.tuning.loop import TrialScorer, TuningResult, tune
from sverdrup.application.tuning.objective import ConstrainedObjective
from sverdrup.application.tuning.strategy import SearchStrategy
from sverdrup.core.types import UncertaintyCapability
from sverdrup.methods.gmrf import MaternGMRF

_JOINT = frozenset({UncertaintyCapability.SAMPLES})


def tile_geometry_for(n_tiles: int, params: dict[str, float]) -> TileGeometry:
    """Derive the coherence-relevant geometry from the tile count + trial range."""
    return TileGeometry(
        core_size_deg=0.0,
        range_km=float(params.get("range", 0.0)),
        tiling_id=f"global-{n_tiles}tiles",
        n_tiles=n_tiles,
    )


def run_stage_c_loop(
    *,
    n_tiles: int,
    strategy: SearchStrategy,
    predicate: FeasibilityPredicate,
    objective: ConstrainedObjective,
    scorer: TrialScorer,
    seed: int,
    on_empty: str = "raise",
) -> TuningResult:
    """Run the GMRF global-coherent loop; the predicate gates on the fixed tile count.

    A single ``TileGeometry(n_tiles=n_tiles)`` per run — the joint barrier keys on tile count,
    not per-trial range, so no per-trial predicate wrapper is needed (unlike the retired
    core/range design).
    """
    return tune(
        method_name="gmrf",
        space=MaternGMRF().parameter_space(),
        strategy=strategy,
        predicate=predicate,
        objective=objective,
        scorer=scorer,
        split=type("S", (), {"id": "global"})(),
        seed=seed,
        window=type("W", (), {"id": "global"})(),
        tile_geometry=tile_geometry_for(n_tiles, {"range": 1.0}),
        required_capabilities=_JOINT,
        rounds=1,
        on_empty=on_empty,
    )
```

- [ ] **Step 4: Run — confirm pass**

Run: `pixi run test tests/test_stage_c_hard_barrier.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/sverdrup/application/tuning/stage_c.py tests/test_stage_c_hard_barrier.py
git commit -m "feat(tuning): Stage-C loop wiring — multi-tile joint barrier hard (test 4)"
```

---

## Task 3: Worst-case-localized coherence reduction (adjacent-seam corr-err, strict max)

**Goal:** Provide the worst-case-localized reduction the boundary is measured with — the strict worst (max) adjacent-seam correlation error over seams, never an aggregate — and prove an aggregate cannot stand in for it.

**Files:**
- Create: `src/sverdrup/application/tuning/coherence_gate.py`
- Create: `tests/test_stage_c_worst_case_localized.py`

**Acceptance Criteria:**
- [ ] `worst_case_corr_err(per_pair_errs) -> float` returns the strict MAX over adjacent-seam node pairs (higher = worse; 0 good, ≥1 decorrelated); `worst_case_corr_err([]) == 0.0` (no seams → vacuously perfect).
- [ ] `corr_err_feasible(per_pair_errs, tol) -> bool` is `worst_case_corr_err(...) <= tol`.
- [ ] A fixture where the MEDIAN is healthy (≈0.02) but one pair is catastrophic (1.1) is judged infeasible at `tol=0.5` — the median (`np.median`) would have passed it.

**Verify:** `pixi run test tests/test_stage_c_worst_case_localized.py -v` → pass.

**Steps:**

- [ ] **Step 1: Write the failing test**

```python
# tests/test_stage_c_worst_case_localized.py
"""Coherence gated worst-case-localized (strict max), never aggregate — the anti-false-green rule."""

from __future__ import annotations

import numpy as np

from sverdrup.application.tuning.coherence_gate import (
    corr_err_feasible,
    worst_case_corr_err,
)


def test_strict_max_not_median() -> None:
    # Bug it catches: a median laundering one catastrophic seam pair (design §2: median 0.015,
    # worst 1.105 at 2x2 — the sparse catastrophic tail).
    errs = np.array([0.01, 0.02, 0.02, 1.105])
    assert worst_case_corr_err(errs) == 1.105          # strict max
    assert np.median(errs) < 0.5                        # the median would have passed it
    assert corr_err_feasible(errs, tol=0.5) is False    # gated on the worst, not the median


def test_empty_is_feasible_sentinel() -> None:
    assert worst_case_corr_err(np.array([])) == 0.0
    assert corr_err_feasible(np.array([]), tol=0.5) is True
```

- [ ] **Step 2: Run — confirm fail**

Run: `pixi run test tests/test_stage_c_worst_case_localized.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement** (the reduction only — no new uncertainty math; mirrors the metric in `tests/unit/_tree_gate.py::GateFixture.edge_seam_corr_err`)

```python
# src/sverdrup/application/tuning/coherence_gate.py
"""Worst-case-localized coherence reduction (invariant 6): strict MAX adjacent-seam corr-err.

The joint cross-seam coherence deficit is measured per grid-adjacent seam node pair as a
correlation-unit error (|emp_cov - ref_cov| / sqrt(sigma_a sigma_b); design §2). This reduces
those per-pair errors worst-case-localized — the strict maximum, never a median/mean, because the
deficit is a SPARSE catastrophic tail an aggregate launders (the Phase-4 anti-false-green lesson).
This is gate EVIDENCE (the feasibility predicate keys on the baked n_star_joint), never a score.
"""

from __future__ import annotations

import numpy as np


def worst_case_corr_err(per_pair_errs: np.ndarray | list[float]) -> float:
    """Return the strict MAX adjacent-seam correlation error (0.0 if there are no seams)."""
    a = np.asarray(per_pair_errs, dtype=float)
    return float(a.max()) if a.size else 0.0


def corr_err_feasible(per_pair_errs: np.ndarray | list[float], tol: float) -> bool:
    """Return True iff the worst-case adjacent-seam corr-err is within ``tol``."""
    return worst_case_corr_err(per_pair_errs) <= tol
```

- [ ] **Step 4: Run — confirm pass**

Run: `pixi run test tests/test_stage_c_worst_case_localized.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/sverdrup/application/tuning/coherence_gate.py tests/test_stage_c_worst_case_localized.py
git commit -m "feat(tuning): worst-case-localized coherence reduction (strict-max adjacent-seam corr-err)"
```

---

## Task 4: Both-tiers feasibility frontier consumer (`tuning/tradeoff.py`)

**Goal:** A thin consumer that bakes the measured curve (from `scripts/diag_crossseam.py`) into a both-tiers frontier: the SAMPLES/COVARIANCE joint tier (worst-of-K, empty region) and the MARGINAL_VARIANCE tier (flat worst-case), with feasibility under a supplied predicate. No measurement in this module.

**Files:**
- Create: `src/sverdrup/application/tuning/tradeoff.py`
- Create: `tests/test_stage_c_tradeoff.py`

**Acceptance Criteria:**
- [ ] `MEASURED_FRONTIER` is a module constant: the committed rows `[{n_tiles, joint_worst_of_k, joint_wok_std, joint_median, marg_worst_case}, …]` for `n_tiles ∈ {4,9,16,25,36}` from the design §2 tables, with a provenance comment citing `scripts/diag_crossseam.py`.
- [ ] `feasibility_frontier(predicate)` returns rows `{n_tiles, joint_worst_of_k, joint_feasible, marg_worst_case, marg_feasible}` where `*_feasible` is the predicate's verdict for `{SAMPLES}` / `{MARGINAL_VARIANCE}` at that `n_tiles`.
- [ ] Under `CoherenceFeasibility()`: **zero** rows are `joint_feasible` (empty region); **every** row is `marg_feasible` (ships). Under `RelaxedCoherenceFeasibility(n_star_joint=64)`: the count of `joint_feasible` rows increases (region widened) with **no change to `tradeoff.py`**.

**Verify:** `pixi run test tests/test_stage_c_tradeoff.py -v` → pass.

**Steps:**

- [ ] **Step 1: Write the failing test**

```python
# tests/test_stage_c_tradeoff.py
"""The both-tiers frontier; a relaxed predicate widens the joint region without touching tradeoff.py."""

from __future__ import annotations

from sverdrup.application.tuning.feasibility import (
    CoherenceFeasibility,
    RelaxedCoherenceFeasibility,
)
from sverdrup.application.tuning.tradeoff import feasibility_frontier


def test_default_is_joint_empty_marg_ships() -> None:
    rows = feasibility_frontier(CoherenceFeasibility())
    assert rows and all(not r["joint_feasible"] for r in rows)   # empty joint region
    assert all(r["marg_feasible"] for r in rows)                 # marginal ships at every N


def test_relaxed_widens_joint_region() -> None:
    # TEST 6 (Stage C): relaxation widens the joint region; tradeoff.py unchanged.
    n_default = sum(r["joint_feasible"] for r in feasibility_frontier(CoherenceFeasibility()))
    n_relaxed = sum(
        r["joint_feasible"]
        for r in feasibility_frontier(RelaxedCoherenceFeasibility(n_star_joint=64))
    )
    assert n_relaxed > n_default
```

- [ ] **Step 2: Run — confirm fail**

Run: `pixi run test tests/test_stage_c_tradeoff.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement**

```python
# src/sverdrup/application/tuning/tradeoff.py
"""Stage-C both-tiers feasibility frontier: the owner's redesign-decision input.

THIN CONSUMER — no measurement here. The heavy cross-seam measurement lives in
scripts/diag_crossseam.py (constant-core sweep, M=8000, selection-controlled worst-of-K; plus the
analytic MARGINAL_VARIANCE-accuracy sweep). Its results are baked below and fed to the injected
predicate, so a relaxed predicate (the redesign interface) widens the feasible region WITHOUT
touching this module (invariant 5). Provenance + tables: design §2.
"""

from __future__ import annotations

from sverdrup.application.tuning.feasibility import FeasibilityPredicate, TileGeometry
from sverdrup.core.types import UncertaintyCapability

_SAMPLES = frozenset({UncertaintyCapability.SAMPLES})
_MARGINAL = frozenset({UncertaintyCapability.MARGINAL_VARIANCE})

# MEASURED (scripts/diag_crossseam.py, constant 4 deg core; design §2). joint_* = adjacent-seam
# corr-err worst-of-K (K=418 fixed) + its estimator std + node-pair median; marg = analytic
# reported-marginal worst-case rel error (FLAT in N).
MEASURED_FRONTIER: list[dict[str, float]] = [
    {"n_tiles": 4,  "joint_worst_of_k": 1.105, "joint_wok_std": 0.000, "joint_median": 0.015, "marg_worst_case": 0.069},
    {"n_tiles": 9,  "joint_worst_of_k": 0.506, "joint_wok_std": 0.079, "joint_median": 0.023, "marg_worst_case": 0.140},
    {"n_tiles": 16, "joint_worst_of_k": 0.823, "joint_wok_std": 0.135, "joint_median": 0.031, "marg_worst_case": 0.130},
    {"n_tiles": 25, "joint_worst_of_k": 2.033, "joint_wok_std": 0.000, "joint_median": 0.052, "marg_worst_case": 0.149},
    {"n_tiles": 36, "joint_worst_of_k": 2.108, "joint_wok_std": 0.000, "joint_median": 0.070, "marg_worst_case": 0.132},
]


def _geom(n_tiles: int) -> TileGeometry:
    return TileGeometry(core_size_deg=4.0, range_km=300.0, tiling_id=f"c{n_tiles}", n_tiles=n_tiles)


def feasibility_frontier(
    predicate: FeasibilityPredicate,
) -> list[dict[str, float | bool]]:
    """Return per-tile-count rows with both tiers' worst-case + the predicate's verdict.

    ``joint_feasible`` / ``marg_feasible`` are the predicate's decisions for {SAMPLES} /
    {MARGINAL_VARIANCE} at each measured tile count. Injecting a relaxed predicate widens the
    joint region with no change here (invariant 5).
    """
    rows: list[dict[str, float | bool]] = []
    for m in MEASURED_FRONTIER:
        n = int(m["n_tiles"])
        rows.append(
            {
                "n_tiles": n,
                "joint_worst_of_k": m["joint_worst_of_k"],
                "joint_feasible": predicate.feasible({}, _geom(n), _SAMPLES),
                "marg_worst_case": m["marg_worst_case"],
                "marg_feasible": predicate.feasible({}, _geom(n), _MARGINAL),
            }
        )
    return rows
```

- [ ] **Step 4: Run — confirm pass**

Run: `pixi run test tests/test_stage_c_tradeoff.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/sverdrup/application/tuning/tradeoff.py tests/test_stage_c_tradeoff.py
git commit -m "feat(tuning): both-tiers feasibility frontier consumer (thin, predicate-injected)"
```

---

## Task 5: Concrete strict-xfail + generate the frontier doc

**Goal:** Replace the retired `core/range` strict-xfail with a concrete one (a multi-tile joint product asserted feasible, xfail until the deferred fix widens `n_star_joint`), and generate the owner-facing both-tiers frontier doc.

**Files:**
- Modify: `tests/test_core_authoritative_gate.py`
- Create: `docs/validation/phase5_feasibility_resolution_frontier.md`

**Acceptance Criteria:**
- [ ] The retired core/range strict-xfail `test_acceptance_operational_cross_seam_covariance_recovered` is replaced by `test_acceptance_multi_tile_joint_feasible` — asserts a `{SAMPLES}` product at `n_tiles=9` is feasible under `CoherenceFeasibility()`, marked `@pytest.mark.xfail(strict=True, reason="owner-deferred coarse-correction; n_star_joint=1 until then")`. It **xfails** today.
- [ ] `docs/validation/phase5_feasibility_resolution_frontier.md` exists and contains: both-tiers tables from `MEASURED_FRONTIER`; the robust-first framing (global infeasible → regional shorthand with non-monotone + thin-3×3-margin caveats); the MARGINAL_VARIANCE ~15%-flat conditional; the single-fixture provenance; and the explicit statement that operational-range DUACS-class global coherent is out of reach until the owner-deferred decomposition-redesign.

**Verify:** `pixi run test tests/test_core_authoritative_gate.py -v` → the new xfail is `xfailed` (not `xpassed`, not error); the doc exists.

**Steps:**

- [ ] **Step 1: Locate + replace the retired xfail**

Run: `rg -n "test_acceptance_operational_cross_seam_covariance_recovered|core/range|CORE_OVER_RANGE|>= 25" tests/test_core_authoritative_gate.py` to find the retired test and any core/range asserts.

Replace the retired `test_acceptance_operational_cross_seam_covariance_recovered` function (and remove any now-dangling `core/range` helper it used) with:

```python
import pytest

from sverdrup.application.tuning.feasibility import CoherenceFeasibility, TileGeometry
from sverdrup.core.types import UncertaintyCapability


@pytest.mark.xfail(
    strict=True,
    reason="owner-deferred coarse-correction; n_star_joint=1 (joint region empty) until then",
)
def test_acceptance_multi_tile_joint_feasible() -> None:
    # The known-unmet target, pinned in code: a multi-tile SAMPLES product should be feasible.
    # It is NOT today (n_star_joint=1) -> strict xfail; the deferred decomposition-redesign that
    # widens n_star_joint flips this to xpass. Replaces the retired core/range>=25 acceptance.
    geom = TileGeometry(core_size_deg=4.0, range_km=300.0, tiling_id="g", n_tiles=9)
    assert CoherenceFeasibility().feasible(
        {}, geom, frozenset({UncertaintyCapability.SAMPLES})
    )
```

If `test_core_authoritative_gate.py` has other tests that assert the `core/range` boundary directly (case-(b) characterization etc.), leave the DENSE-vs-tile covariance measurement tests intact but delete only assertions that hard-code `>= 25` / `CORE_OVER_RANGE_MIN`; run the file and adjust any import errors from the removed helpers.

- [ ] **Step 2: Run — confirm the xfail xfails**

Run: `pixi run test tests/test_core_authoritative_gate.py -v`
Expected: `test_acceptance_multi_tile_joint_feasible` reported `XFAIL` (not `XPASS`, not `ERROR`); the rest of the file green.

- [ ] **Step 3: Generate the frontier doc**

Create `docs/validation/phase5_feasibility_resolution_frontier.md`. Use the exact measured numbers from `MEASURED_FRONTIER` (Task 4) and the design §2 tables. Content (fill the tables from the constants — no placeholders):

```markdown
# Phase-5 Stage-C feasibility frontier (owner redesign input)

**Bottom line (robust, tolerance-invariant):** global `SAMPLES/COVARIANCE` coherent sampling with the
bare tree-kriging driver is **infeasible at operational range** — the worst-case adjacent-seam joint
correlation error is ~2.0 by 25 tiles and rising, exceeding any sane tolerance at a global (thousands of
tiles) product. `MARGINAL_VARIANCE` **ships** globally, conditional on accepting a fixed ~15% worst-case
reported-marginal error. Operational-range DUACS-class global *coherent* products are out of reach until
the **owner-deferred** decomposition-redesign (coarse-correction / overlapping-Schwarz / low-rank seam
basis) widens `n_star_joint`.

## Tier 1 — SAMPLES/COVARIANCE (joint cross-seam covariance)

Worst-of-K adjacent-seam corr-err (K=418 fixed, M=8000, selection-controlled), median, ± estimator std:

| tiles | worst-of-K | ± std | median |
|-------|-----------|-------|--------|
| 4     | 1.105     | 0.000 | 0.015  |
| 9     | 0.506     | 0.079 | 0.023  |
| 16    | 0.823     | 0.135 | 0.031  |
| 25    | 2.033     | —     | 0.052  |
| 36    | 2.108     | —     | 0.070  |

- **Regional caveat (shorthand only):** at `joint_tol=0.5` every tested tiling's point estimate exceeds
  tol → `n_star_joint=1`. But the worst-of-K is **non-monotone** in N (2×2 > 3×3), and **3×3 = 0.506 ±
  0.079 is within noise of 0.5** — no multi-tile geometry is *clearly* feasible, but the small-N
  exclusion rests on a thin margin. A loosened tol (> ~0.51) makes feasibility **non-nested** (needs an
  `N → worst-case` lookup, not a threshold).
- **Deficit shape:** typical seam is excellent (median 1.5%→7%); the worst-case is a **sparse catastrophic
  tail** (~0.24% of pairs at 2×2), not uniform mediocrity — the coarse-correction must rescue a few
  catastrophic seam pairs, not fix a uniform deficit.

## Tier 2 — MARGINAL_VARIANCE (reported marginal accuracy, analytic)

| tiles | worst-case rel error |
|-------|----------------------|
| 4     | 0.069 |
| 9     | 0.140 |
| 16    | 0.130 |
| 25    | 0.149 |
| 36    | 0.132 |

Worst-case ~13–15%, **FLAT** with tile count → ships iff `marg_tol ≥ ~0.15`, tile-count-independent. This
is the honest global product, correctly labeled `MARGINAL_VARIANCE`, not "coherent."

## Provenance

Single synthetic fixture (4° core, 300 km range, 1° grid, M=8000, K-controlled;
`scripts/diag_crossseam.py`). The conclusion is physically robust (independent-core tiling destroys
cross-seam correlation, worsens with seam count, cores do not rescue it — confound killed), but exact
universality across ranges/densities is one-fixture-based. The predicate's `joint_tol` / `marg_tol` /
`n_star_joint` are named, swappable defaults that absorb regime variation.
```

- [ ] **Step 4: Commit**

```bash
git add tests/test_core_authoritative_gate.py docs/validation/phase5_feasibility_resolution_frontier.md
git commit -m "feat(tuning): concrete multi-tile-joint strict-xfail + both-tiers frontier doc"
```

---

## Task 6: [USER GATE] Stage-C DoD — boundary respected, quantified, relaxable, surfaced

**Goal:** Close Stage C: assemble the gate evidence that the tuner never solves a multi-tile joint trial, coherence is worst-case-localized, a relaxed predicate widens the joint region without touching the tuner, and the both-tiers frontier is surfaced with the robust-first framing. Run the full suite + typecheck + lint.

> **USER-ORDERED GATE — NON-SKIPPABLE.** This task was requested by the user in the current conversation. It MUST NOT be closed by walking around it, by declaring it "verified inline", or by substituting a cheaper check. Close only after every item in `acceptanceCriteria` has been re-validated independently, with output captured.

**Files:**
- Create: `tests/test_stage_c_dod.py`
- Modify: `PROGRESS.md`

**Acceptance Criteria:**
- [ ] Aggregated Stage-C evidence passes: hard barrier (Task 2), worst-case-localized (Task 3), relaxed-widens-joint (Task 4), concrete strict-xfail xfails (Task 5), frontier doc exists with both tiers + the "no operational-range DUACS-class global coherent until the deferred redesign" statement.
- [ ] Full suite green: `pixi run test` → all pass/skip/xfail (no unexpected fail/xpass/error); `pixi run typecheck` clean; `pixi run lint` clean; `pixi run pre-commit run --all-files` clean.
- [ ] `PROGRESS.md` records Stage C closed, the frontier doc path, and that the coarse-correction/default-sampler remains owner-deferred (decoupled via the predicate).

**Verify:** `pixi run test -q && pixi run typecheck && pixi run lint && pixi run pre-commit run --all-files` → all green; `docs/validation/phase5_feasibility_resolution_frontier.md` exists.

**Steps:**

- [ ] **Step 1: Write the DoD aggregation test**

```python
# tests/test_stage_c_dod.py
"""Stage-C definition of done: boundary respected, quantified, relaxable, surfaced (both tiers)."""

from __future__ import annotations

from pathlib import Path

from sverdrup.application.tuning.feasibility import (
    CoherenceFeasibility,
    RelaxedCoherenceFeasibility,
)
from sverdrup.application.tuning.tradeoff import feasibility_frontier


def test_joint_region_empty_marginal_ships() -> None:
    rows = feasibility_frontier(CoherenceFeasibility())
    assert rows and all(not r["joint_feasible"] for r in rows)  # boundary real: joint empty
    assert all(r["marg_feasible"] for r in rows)                # marginal ships


def test_relaxation_is_the_redesign_interface() -> None:
    n_default = sum(r["joint_feasible"] for r in feasibility_frontier(CoherenceFeasibility()))
    n_relaxed = sum(
        r["joint_feasible"]
        for r in feasibility_frontier(RelaxedCoherenceFeasibility(n_star_joint=64))
    )
    assert n_relaxed > n_default


def test_frontier_doc_surfaced() -> None:
    p = Path("docs/validation/phase5_feasibility_resolution_frontier.md")
    assert p.exists()
    text = p.read_text()
    assert "MARGINAL_VARIANCE" in text and "owner-deferred" in text
```

- [ ] **Step 2: Run — confirm pass**

Run: `pixi run test tests/test_stage_c_dod.py -v` → PASS.

- [ ] **Step 3: Run the full gate**

Run each, capture output:
```bash
pixi run test -q
pixi run typecheck
pixi run lint
pixi run pre-commit run --all-files
```
Expected: all green (tests: pass/skip/xfail only — the Task-5 xfail is expected-xfail, not xpass).

- [ ] **Step 4: Update PROGRESS.md**

Record under the Stage-C section: Stage C CLOSED; tuner never solves a multi-tile joint trial; coherence gated worst-case-localized; both-tiers frontier at `docs/validation/phase5_feasibility_resolution_frontier.md`; the coarse-correction/default-sampler remains owner-deferred (decoupled via `RelaxedCoherenceFeasibility`). Set the resume "next action" to "Phase 5 complete; owner reviews the frontier for the redesign decision."

- [ ] **Step 5: Commit**

```bash
git add tests/test_stage_c_dod.py PROGRESS.md
git commit -m "feat(tuning): Stage-C DoD — boundary respected, quantified, relaxable, surfaced"
```

- [ ] **Step 6: STOP — user gate.** Present the full-suite result, the both-tiers frontier table, and the four Stage-C evidence points. Await owner sign-off to close Stage C / Phase 5.

---

## Self-review

**Spec coverage** (design §§ → task): §3 predicate + `TileGeometry.n_tiles` + `RelaxedCoherenceFeasibility` → T1; §4 hard-barrier machinery (kept, re-keyed) → T2; §4 worst-case-localized reduction (kept, re-pointed) → T3; §5 both-tiers frontier + measurement-in-script/thin-consumer split → T4; §4 concrete strict-xfail + §6 surfaced frontier doc → T5; §6 DoD → T6. §8 provenance caveat → T5 doc + T6. Non-goals §9 (coarse-correction deferred) → honored (no fix built; `RelaxedCoherenceFeasibility` bounds illustrative).

**Placeholder scan:** none — every code/doc step carries full content; `MEASURED_FRONTIER` numbers are the committed §2 measurements.

**Type/name consistency:** `TileGeometry(core_size_deg, range_km, tiling_id, n_tiles=1)` consistent T1/T2/T4/T5; `CoherenceFeasibility(joint_tol, n_star_joint, marg_tol, marg_worst_case)` consistent T1/T4/T5; `feasibility_frontier(predicate)` row keys (`joint_feasible`/`marg_feasible`/`joint_worst_of_k`/`marg_worst_case`) consistent T4/T6; `worst_case_corr_err`/`corr_err_feasible` T3; `run_stage_c_loop`/`tile_geometry_for` T2. `required_capabilities` uses real `UncertaintyCapability.{SAMPLES,COVARIANCE,MARGINAL_VARIANCE,POINT}` (verified in `core/types.py`).
