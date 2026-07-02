# Tuner Debt Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close two carried Task-14 follow-ups — make `BayesianOptimization` genuinely multi-round by threading `rounds` through the stage runners, and turn the Stage-B gate test's smoke ERROR into an honest skip.

**Architecture:** `tune()` already loops `range(rounds)` and warm-starts the TPE surrogate from accumulated `history`; only `_run_stage` hardcodes `rounds=1`. Thread `rounds: int = 1` through `_run_stage`/`run_stage_a`/`run_stage_b` and forward it to `tune`. Equal-total budget is a call-site convention (Sobol: 1 round of N; BO: R rounds of N/R). The gate test gains a rounds knob and a `StageANoAdmissible → pytest.skip` guard.

**Tech Stack:** Python, numpy, pytest, optuna (existing `application/tuning/` seams).

**User decisions (already made):**
- "equal total, split into rounds" — `n_trials` stays the per-batch size; the equal-budget Sobol-vs-BO comparison is enforced at the call site (Sobol 1×N, BO R×(N/R)). `rounds` defaults to 1 (production unchanged). No `SobolSearch` change.
- "skip with diagnostic" — when the gate is opted-in but the scope yields no admissible GMRF trial, catch `StageANoAdmissible` and `pytest.skip` with the best-mu diagnostic; a full-year scope still runs the real λx asserts.

**Source of truth:** `docs/superpowers/specs/2026-07-01-tuner-debt-cleanup-design.md`.

---

## Task 1: Thread `rounds` through the stage runners (+ multi-round behavior test)

**Goal:** Give `_run_stage`/`run_stage_a`/`run_stage_b` a `rounds: int = 1` parameter forwarded to `tune`, and prove at the loop level that multi-round feeds accumulated history forward (the mechanism that makes BO guided).

**Files:**
- Modify: `src/sverdrup/application/tuning/stage_a.py` (`_run_stage` signature + the `rounds=1` call at ~line 179; `run_stage_a` signature + delegation)
- Modify: `src/sverdrup/application/tuning/stage_b.py` (`run_stage_b` signature + delegation)
- Create: `tests/test_tuning_rounds.py`

**Acceptance Criteria:**
- [ ] `_run_stage`, `run_stage_a`, `run_stage_b` each accept `rounds: int = 1`; `_run_stage` passes `rounds=rounds` to `tune` (no longer hardcoded `1`).
- [ ] `run_stage_a`/`run_stage_b` expose `rounds` in their signature with default `1` (back-compat: existing callers unaffected).
- [ ] A loop-level test proves `tune(..., rounds=3)` calls `strategy.propose` 3× with a **non-decreasing** history length that grows by the batch size each round (`[0, n, 2n]`).

**Verify:** `pixi run test tests/test_tuning_rounds.py -v && pixi run typecheck` → pass / clean.

**Steps:**

- [ ] **Step 1: Write the failing test**

```python
# tests/test_tuning_rounds.py
"""Multi-round tuning feeds accumulated history forward — the mechanism BO relies on."""

from __future__ import annotations

import inspect

from sverdrup.application.tuning.feasibility import CoherenceFeasibility, TileGeometry
from sverdrup.application.tuning.loop import tune
from sverdrup.application.tuning.objective import ConstrainedObjective
from sverdrup.application.tuning.stage_a import run_stage_a
from sverdrup.application.tuning.stage_b import run_stage_b
from sverdrup.core.parameters import ParameterSpace
from sverdrup.core.types import UncertaintyCapability as UC
from sverdrup.methods.gmrf import MaternGMRF


class _HistoryRecordingStrategy:
    """Fake SearchStrategy: records history size at each propose call, returns a fixed point."""

    def __init__(self, n: int) -> None:
        self.n = n
        self.history_lengths: list[int] = []

    def propose(self, space: ParameterSpace, history: object) -> list[dict[str, float]]:
        self.history_lengths.append(len(history.records))  # type: ignore[attr-defined]
        mid = {k: (lo + hi) / 2 for k, (lo, hi) in space.bounds.items()}
        return [dict(mid) for _ in range(self.n)]


class _AdmissibleScorer:
    def score(self, method_name, params, split, seed, window):  # noqa: ANN001, ANN201
        return {"lambda_x": 120.0, "mu_score": 0.86, "coverage_1sigma": 0.68}


class _FakeSplit:
    id = "s"


class _FakeWindow:
    id = "w"


def _space() -> ParameterSpace:
    return MaternGMRF().parameter_space()


def test_multi_round_feeds_accumulated_history() -> None:
    # Behavior: rounds=R runs propose R times, each seeing the prior rounds' recorded trials.
    # Bug it catches: a regression that breaks the range(rounds) loop or stops passing the
    # growing history into propose -> BO silently reverts to random density (rounds=1 behavior).
    strat = _HistoryRecordingStrategy(n=2)
    tune(
        method_name="gmrf",
        space=_space(),
        strategy=strat,
        predicate=CoherenceFeasibility(),
        objective=ConstrainedObjective(),
        scorer=_AdmissibleScorer(),
        split=_FakeSplit(),
        seed=1,
        window=_FakeWindow(),
        tile_geometry=TileGeometry(1e9, 1.0, "single"),
        required_capabilities=frozenset({UC.POINT}),
        rounds=3,
        on_empty="return_history",
    )
    assert strat.history_lengths == [0, 2, 4]  # 3 rounds; history grows by n=2 each round


def test_stage_runners_expose_rounds_default_one() -> None:
    # Contract: the stage runners accept `rounds` and default it to 1 (production unchanged).
    # Bug it catches: dropping the parameter so BO can never be driven multi-round.
    for fn in (run_stage_a, run_stage_b):
        p = inspect.signature(fn).parameters
        assert "rounds" in p, fn.__name__
        assert p["rounds"].default == 1, fn.__name__
```

- [ ] **Step 2: Run — confirm fail**

Run: `pixi run test tests/test_tuning_rounds.py -v`
Expected: `test_stage_runners_expose_rounds_default_one` FAILS (`rounds` not in signature). `test_multi_round_feeds_accumulated_history` should already PASS (tune already loops rounds) — that is fine; it is the regression guard, not the red.

- [ ] **Step 3: Thread `rounds` through `_run_stage` + `run_stage_a`**

In `src/sverdrup/application/tuning/stage_a.py`, add `rounds` to `_run_stage`'s keyword-only signature (after `strategy`):

Find:
```python
def _run_stage(
    *,
    method_name: str,
    space: ParameterSpace,
    scope: Path,
    n_trials: int = 16,
    seed: int = 1,
    strategy: SearchStrategy | None = None,
) -> StageAReport:
```
Replace with:
```python
def _run_stage(
    *,
    method_name: str,
    space: ParameterSpace,
    scope: Path,
    n_trials: int = 16,
    seed: int = 1,
    strategy: SearchStrategy | None = None,
    rounds: int = 1,
) -> StageAReport:
```

Find the `tune(...)` call's hardcoded rounds:
```python
        required_capabilities=frozenset({UncertaintyCapability.POINT}),
        rounds=1,
        on_empty="return_history",
```
Replace with:
```python
        required_capabilities=frozenset({UncertaintyCapability.POINT}),
        rounds=rounds,
        on_empty="return_history",
```

Add `rounds` to `run_stage_a` and forward it. Find:
```python
def run_stage_a(
    *,
    scope: Path,
    n_trials: int = 16,
    seed: int = 1,
    strategy: SearchStrategy | None = None,
) -> StageAReport:
    """Run the single-tile stage on OI (delegates to the shared ``_run_stage``)."""
    return _run_stage(
        method_name="oi",
        space=OptimalInterpolation().parameter_space(),
        scope=scope,
        n_trials=n_trials,
        seed=seed,
        strategy=strategy,
    )
```
Replace with:
```python
def run_stage_a(
    *,
    scope: Path,
    n_trials: int = 16,
    seed: int = 1,
    strategy: SearchStrategy | None = None,
    rounds: int = 1,
) -> StageAReport:
    """Run the single-tile stage on OI (delegates to the shared ``_run_stage``)."""
    return _run_stage(
        method_name="oi",
        space=OptimalInterpolation().parameter_space(),
        scope=scope,
        n_trials=n_trials,
        seed=seed,
        strategy=strategy,
        rounds=rounds,
    )
```

- [ ] **Step 4: Thread `rounds` through `run_stage_b`**

In `src/sverdrup/application/tuning/stage_b.py`, find:
```python
def run_stage_b(
    *,
    scope: Path,
    n_trials: int = 16,
    seed: int = 1,
    strategy: SearchStrategy | None = None,
) -> StageAReport:
```
Replace with:
```python
def run_stage_b(
    *,
    scope: Path,
    n_trials: int = 16,
    seed: int = 1,
    strategy: SearchStrategy | None = None,
    rounds: int = 1,
) -> StageAReport:
```
And the delegation. Find:
```python
    return _run_stage(
        method_name="gmrf",
        space=MaternGMRF().parameter_space(),
        scope=scope,
        n_trials=n_trials,
        seed=seed,
        strategy=strategy,
    )
```
Replace with:
```python
    return _run_stage(
        method_name="gmrf",
        space=MaternGMRF().parameter_space(),
        scope=scope,
        n_trials=n_trials,
        seed=seed,
        strategy=strategy,
        rounds=rounds,
    )
```

- [ ] **Step 5: Run — confirm pass**

Run: `pixi run test tests/test_tuning_rounds.py -v` → both tests PASS.
Run: `pixi run typecheck` → clean.

- [ ] **Step 6: Regression — the existing tuning suite is unaffected (default rounds=1)**

Run: `pixi run test tests/test_tuning_loop.py tests/test_tuning_method_agnostic.py tests/test_tuning_bayesopt.py -v` → all pass.

- [ ] **Step 7: Commit**

```bash
git add src/sverdrup/application/tuning/stage_a.py src/sverdrup/application/tuning/stage_b.py tests/test_tuning_rounds.py
git commit -m "feat(tuning): thread rounds through stage runners (BO genuinely multi-round)"
```

---

## Task 2: Stage-B gate — multi-round BO call + no-admissible skip

**Goal:** Drive the gate's BO run multi-round at equal total budget, and turn the expected smoke `StageANoAdmissible` into an honest `pytest.skip` with a diagnostic (a full-year scope still exercises the real λx asserts).

**Files:**
- Modify: `tests/test_stage_b_gate.py`

**Acceptance Criteria:**
- [ ] The BO run uses `BayesianOptimization(seed=1, n=max(1, n // R))` with `rounds=R`, where `R = int(os.environ.get("SVERDRUP_STAGE_B_ROUNDS", "4"))`; the Sobol baseline is unchanged (1 round of `n`). Both total ≈ `n`.
- [ ] Both `run_stage_b` calls are wrapped so a raised `StageANoAdmissible` becomes `pytest.skip(...)` with an actionable message (not an ERROR).
- [ ] `StageANoAdmissible` is imported from `sverdrup.application.tuning.stage_a`.
- [ ] The λx finite/positive + `≤ 1.25× Sobol` asserts are retained for the admissible (full-year) path.

**Verify:** `pixi run test tests/test_stage_b_gate.py -v` → the gate test SKIPS (opt-in not set); `pixi run typecheck` → clean. (The full behavior runs only under `SVERDRUP_STAGE_B_GATE=1` with challenge data.)

**Steps:**

- [ ] **Step 1: Replace the test body** (the file's non-test scaffolding — module docstring, `_OPT_IN`, `skipif` — stays)

Find:
```python
def test_gmrf_bo_lands_sensible_score() -> None:
    # Behavior: the GMRF sweep, driven by BayesianOptimization through the unchanged
    # loop/objective/acceptance, produces a finite challenge acceptance (µ, σ, λx) that
    # does not regress the Sobol-baseline λx by more than 1.25x.
    # Bug it catches: a BO drop-in that silently degrades the search (e.g. proposing
    # out-of-bounds or collapsing to one point) so the GMRF winner resolves a far
    # coarser scale than the Sobol baseline — or returns a non-finite acceptance.
    from sverdrup.application.tuning.bayesopt import BayesianOptimization
    from sverdrup.application.tuning.stage_b import run_stage_b

    n = int(os.environ.get("SVERDRUP_STAGE_B_N", "8"))
    sobol = run_stage_b(scope=FIX / "stage_a_scope.json", n_trials=n, seed=1)
    bo = run_stage_b(
        scope=FIX / "stage_a_scope.json",
        n_trials=n,
        seed=1,
        strategy=BayesianOptimization(seed=1, n=n),
    )
    # Finite, positive acceptance (µ and λx) — the GMRF winner produced a real map.
    assert bo.acceptance[0] > 0.0
    assert bo.acceptance[2] > 0.0
    # BO must not badly regress λx vs the Sobol baseline (record the margin).
    assert bo.acceptance[2] <= sobol.acceptance[2] * 1.25
```
Replace with:
```python
def test_gmrf_bo_lands_sensible_score() -> None:
    # Behavior: the GMRF sweep, driven by MULTI-ROUND BayesianOptimization through the
    # unchanged loop/objective/acceptance at equal total budget, produces a finite challenge
    # acceptance (µ, σ, λx) that does not regress the Sobol-baseline λx by more than 1.25x.
    # Bug it catches: a BO drop-in that silently degrades the search (out-of-bounds, collapse
    # to one point, or losing multi-round guidance) so the GMRF winner resolves a far coarser
    # scale than the Sobol baseline — or returns a non-finite acceptance.
    from sverdrup.application.tuning.bayesopt import BayesianOptimization
    from sverdrup.application.tuning.stage_a import StageANoAdmissible
    from sverdrup.application.tuning.stage_b import run_stage_b

    n = int(os.environ.get("SVERDRUP_STAGE_B_N", "8"))
    rounds = int(os.environ.get("SVERDRUP_STAGE_B_ROUNDS", "4"))
    scope = FIX / "stage_a_scope.json"
    try:
        # Sobol baseline: 1 round of n (Sobol ignores history; rounds>1 would duplicate).
        sobol = run_stage_b(scope=scope, n_trials=n, seed=1)
        # BO: R guided rounds of n // R -> same total budget n, surrogate re-fit each round.
        bo = run_stage_b(
            scope=scope,
            n_trials=n,
            seed=1,
            strategy=BayesianOptimization(seed=1, n=max(1, n // rounds)),
            rounds=rounds,
        )
    except StageANoAdmissible as exc:
        pytest.skip(
            f"no admissible GMRF trial on this scope ({exc}); the 12-day dev fixture is too "
            "small for GMRF — set stage_a_scope.json to the full-2017 window to run the gate."
        )
    # Finite, positive acceptance (µ and λx) — the GMRF winner produced a real map.
    assert bo.acceptance[0] > 0.0
    assert bo.acceptance[2] > 0.0
    # BO must not badly regress λx vs the Sobol baseline (record the margin).
    assert bo.acceptance[2] <= sobol.acceptance[2] * 1.25
```

- [ ] **Step 2: Run — confirm the gate skips cleanly (opt-in not set)**

Run: `pixi run test tests/test_stage_b_gate.py -v`
Expected: 1 skipped (the opt-in `skipif` reason), no ERROR, no collection error.

- [ ] **Step 3: Typecheck**

Run: `pixi run typecheck` → clean.

- [ ] **Step 4: Commit**

```bash
git add tests/test_stage_b_gate.py
git commit -m "test(tuning): Stage-B gate runs BO multi-round + skips on no-admissible"
```

---

## Self-review

**Spec coverage** (design § → task): Part 1 (thread `rounds`, equal-total budget, no strategy change) → T1; Part 2 (gate rounds knob + `StageANoAdmissible → skip`) → T2; Testing §1 (multi-round accumulation) → T1 Step 1; Testing §2 (rounds forwarding) → T1 contract test (`inspect.signature`, no over-mocking — the end-to-end forward is exercised by the opt-in gate run); Testing §3 (skip path not unit-tested) → honored. Non-goals (no `SobolSearch`/`tune`/`bayesopt` change, `stage_c` untouched) → honored.

**Placeholder scan:** none — every step carries full code + exact commands.

**Type/name consistency:** `rounds: int = 1` identical across `_run_stage`/`run_stage_a`/`run_stage_b` (T1) and consumed in T2's `run_stage_b(..., rounds=rounds)`; `StageANoAdmissible` imported from `sverdrup.application.tuning.stage_a` (verified: defined there, stage_a.py:58, NOT objective); `BayesianOptimization(seed, n)` matches `bayesopt.py`; env knobs `SVERDRUP_STAGE_B_N`/`SVERDRUP_STAGE_B_ROUNDS` consistent.

**Note on T1 red:** `test_multi_round_feeds_accumulated_history` passes before the source change (tune already loops rounds) — it is the regression guard for the mechanism, not the red test. The red is `test_stage_runners_expose_rounds_default_one`. This is intentional and called out so the executor does not "fix" a passing guard.
