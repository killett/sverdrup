# Tuner debt cleanup — multi-round BO + Stage-B gate skip

**Date:** 2026-07-01
**Status:** Approved (owner, brainstorm 2026-07-01)
**Scope:** Two carried Task-14 follow-ups in `src/sverdrup/application/tuning/`, closed together.

## Problem

Two items were explicitly deferred at the Task-14 (Stage-B gate) sign-off (see `PROGRESS.md`):

1. **BO is not actually multi-round.** `_run_stage` hardcodes `rounds=1`, so
   `BayesianOptimization` runs a single seeded-TPE batch. Within one `propose` call the study
   `tell`s a `0.0` placeholder for each ask, so the surrogate does not learn intra-batch — guidance
   only materialises **across rounds**, when the loop scores the batch and the next `propose`
   rebuilds the study from real `history` values. At `rounds=1` BO is therefore effectively random
   density, not guided TPE. The gate found its admissible corner by luck, and the "BO ≤ 1.25× Sobol
   λx" criterion was vacuous.

2. **The Stage-B gate test ERRORs on smoke.** `test_gmrf_bo_lands_sensible_score` is opt-in
   (`SVERDRUP_STAGE_B_GATE=1`). When opted-in on the 12-day dev fixture, `run_stage_b` raises
   `StageANoAdmissible` (no GMRF trial clears the BASELINE µ bar — expected and documented), so the
   test ERRORs instead of resolving cleanly.

## Non-goals (YAGNI)

- No change to `SobolSearch`/`RandomSearch`. They are stateless + seeded (ignore `history`,
  regenerate identical points), so `rounds>1` does not help them; multi-round is a
  history-aware-strategy (BO) concept only. Making Sobol sequence-advancing was considered and
  rejected as unneeded for this goal.
- No change to `tune`, `loop.py`, or `bayesopt.py` — the multi-round loop and the surrogate
  warm-start already exist; only the callers hardcode `rounds=1`.
- `stage_c.run_stage_c_loop` stays `rounds=1` (all-excluded hard-barrier loop; rounds irrelevant).
- Production Stage-A/B paths keep `rounds=1` by default — behaviour unchanged unless a caller opts in.

## Design

### Part 1 — thread `rounds`

Add `rounds: int = 1` to `_run_stage` (stage_a.py), `run_stage_a`, and `run_stage_b`, forwarded to
`tune(rounds=rounds)` (replacing the hardcoded `rounds=1` at stage_a.py:179).

**Budget semantics — equal total, split into rounds (owner decision).** `n_trials` remains the
strategy's per-batch size. The equal-total-budget comparison is enforced at the **call site**, not
inside `_run_stage`:

- Sobol baseline: default strategy, `n_trials=N`, `rounds=1` → 1 round of N.
- BO: `strategy=BayesianOptimization(seed, n=N//R)`, `rounds=R` → R guided rounds of N/R.

Both total N evaluations; BO re-fits its surrogate from accumulated `history` between rounds. Sobol
gains nothing from rounds (hence `rounds=1` for it), and is never silently duplicated.

### Part 2 — Stage-B gate test

`tests/test_stage_b_gate.py::test_gmrf_bo_lands_sensible_score`:

- New env knob `SVERDRUP_STAGE_B_ROUNDS` (default `4`) → `R`. Total budget `n` from the existing
  `SVERDRUP_STAGE_B_N` (default `8`).
- Sobol call unchanged: `run_stage_b(scope, n_trials=n, seed=1)` (1 round of n).
- BO call: `run_stage_b(scope, n_trials=n, seed=1, strategy=BayesianOptimization(seed=1, n=max(1, n // R)), rounds=R)`.
- Wrap both `run_stage_b` calls in `try/except StageANoAdmissible` → `pytest.skip(...)` with the
  diagnostic (best mu_score if available + "scope has no admissible GMRF trial; use the full-2017
  window in stage_a_scope.json"). Turns the expected smoke no-admissible into an honest skip
  (not-a-failure, not-a-false-pass); a full-year scope still lands an admissible winner and exercises
  the finite-`(µ,λx)` and `≤1.25× Sobol λx` asserts.
- Import `StageANoAdmissible` from `sverdrup.application.tuning.objective`.

## Testing (TDD, red/green)

1. **Multi-round accumulation (the load-bearing behavior), no data required.** A history-recording
   fake `SearchStrategy` whose `propose` appends `len(history.records)` to a list and returns a fixed
   in-bounds point; run `tune(..., rounds=3)` with a fake admissible scorer; assert `propose` was
   called 3× with **non-decreasing** recorded history lengths (`0`, then `n`, then `2n`). This proves
   the round loop feeds accumulated history forward — the exact mechanism that makes BO guided.
   Bug it catches: a regression that breaks the `range(rounds)` loop or stops passing `history` into
   `propose` (silently reverting BO to random density).
2. **`rounds` forwarding.** Assert `run_stage_b`/`run_stage_a` accept a `rounds` kwarg and forward it
   to `tune` — spy on `tune` at the `stage_a` import site (monkeypatch) so no challenge data is
   touched; assert the spy received `rounds=<R>`.
3. The gate-test skip path runs only under opt-in and is test-harness control flow, so it is not
   separately unit-tested.

## Files

- Modify: `src/sverdrup/application/tuning/stage_a.py` (`_run_stage`, `run_stage_a` gain `rounds`)
- Modify: `src/sverdrup/application/tuning/stage_b.py` (`run_stage_b` gains `rounds`)
- Modify: `tests/test_stage_b_gate.py` (rounds env + BO multi-round call + no-admissible skip)
- Create/modify test for multi-round accumulation + rounds forwarding (`tests/test_tuning_loop.py`
  or a new `tests/test_tuning_rounds.py`)

## Provenance

Both items are documented Task-14 follow-ups in `PROGRESS.md` ("make BO genuinely multi-round" and
"`test_stage_b_gate.py` ERRORS on smoke"). The multi-round diagnosis (placeholder `tell`, guidance
only across rounds) is confirmed by reading `bayesopt.py::propose` and `loop.py::tune`.
