# Sverdrup — Progress notebook

## Current work (index — do not duplicate task state here)

- **Phase 2: tiling / blend / coherent uncertainty — ACTIVE (planned, not started).**
  - Scope (source of truth): `phase2_scope_spec.md` (committed `fa93897`).
  - Design doc: `docs/superpowers/specs/2026-06-23-phase2-tiling-blend-architecture-design.md`.
  - Implementation plan: `docs/superpowers/plans/2026-06-23-phase2-tiling-blend.md`
    (17 tasks, 0–16); tracker `.tasks.json` co-located, all `pending`.
  - Two settled HOW-decisions: blend+sampler in `distributions/` (blend.py, coherent.py);
    coherence = member-only `z_r` + global-cell diagonal noise behind a `StructuredNoiseSource`
    swap seam (Option-2 spatial-square-root in reserve), basis-orientation residual recorded
    distinct from the halo residual; smootherstep weights; km-based `HaloExtent`.
  - **Gate:** Task 15 = Stage-A integration gate (regional blend == single-tile, no seam,
    conservative σ). Stage B (Task 16, global/opt-in) MUST NOT start until Stage A passes.
    Both tagged `userGate`; revalidation hook is registered.
  - **Next action:** start Task 0 (core geometry value objects) — `pixi run test -- tests/test_geometry.py -v`.
- **Milestone: rename to `sverdrup` + PyPI release — COMPLETE (Tasks 1–7).**
  - Design doc: `docs/superpowers/specs/2026-06-21-sverdrup-pypi-release-design.md` (approved).
  - Implementation plan: `docs/superpowers/plans/2026-06-21-sverdrup-pypi-release.md` (7 tasks);
    tracker `.tasks.json` all `completed`.
  - Package renamed `regatta`→`sverdrup`; hatchling + hatch-vcs tag-driven build; Apache-2.0 +
    metadata + `py.typed`; core deps + `dask`/`io`/`all` extras; Trusted-Publishing workflow
    shipped at `docs/superpowers/ci/release.yml` (Option B). User-gate (clean-venv install smoke)
    re-validated. Public repo `killett/sverdrup` created and `main` pushed.
  - **DONE end-to-end:** all three user-side steps completed by the user — workflow installed,
    PyPI Trusted Publisher configured, `v0.1.0` tagged+pushed. `sverdrup 0.1.0` is **live on
    PyPI** (wheel+sdist, Apache-2.0); `pip install sverdrup` verified in a clean venv.
- **conda-forge distribution (in progress):**
  - Recipe generated via `grayskull` (run with `pixi exec grayskull`, not added to manifest),
    polished, and committed at `conda-recipe/meta.yaml` (+ `conda-recipe/README.md`).
  - `noarch: python`; sdist sha256 verified against PyPI; confirmed the sdist builds **without
    `.git`** (hatch-vcs reads version from PKG-INFO) — so conda-forge's sdist build works.
  - **Auto-update mechanism (the goal):** after the one-time `conda-forge/staged-recipes` PR,
    the conda-forge **autotick bot** watches PyPI and opens a version-bump PR on every PyPI
    release. Steady state: push tag → PyPI Action publishes → bot opens feedstock PR → merge.
  - **staged-recipes PR OPEN:** https://github.com/conda-forge/staged-recipes/pull/33814
    (`killett:sverdrup`). Awaiting conda-forge CI + maintainer review/merge → feedstock
    auto-created → conda package ships. User responds to any reviewer feedback.
  - **Gotcha:** the autotick bot only bumps version+hash. When `pyproject.toml` runtime deps
    change, mirror them into `requirements/run` in both `conda-recipe/meta.yaml` and the
    feedstock PR.
  - **Gotcha (CI failure, fixed):** first staged-recipes build #1541860 FAILED on all platforms
    in the *test* phase: `ModuleNotFoundError: No module named 'dask'`. Cause — the recipe test
    ran `python -m sverdrup`, but `__main__.py` eagerly imports the dask executor + pipeline
    (the `dask`/`io` *optional extras*, not core run deps). The conda test env has only core
    deps. Fix: test only the core import surface (`import sverdrup`, `sverdrup.core.grid`,
    `pip check`) — never the entry point — since core deps are all that's guaranteed installed.
    Same trap will bite any feedstock test: do not add extras-dependent checks to `test:`.
- **Phase 1: COMPLETE** — 22 tasks on `main`; suite 70 passed / 1 skipped; both user-gates
  re-validated. Plan: `docs/superpowers/plans/2026-06-21-regatta-phase1.md` (historical).
  Design: `docs/superpowers/specs/2026-06-21-regatta-phase1-architecture-design.md`.

## Cross-cutting decisions (canonical — lives nowhere else)

- **Method 1 = hand-rolled dense GP/OI** (not pyinterp/GPSat). Native covariance +
  whole-field samples via cached Cholesky `L` of `K_dd+R`, `cov(A,B)=K_AB−Vᵀ_A V_B`,
  `V_X=L⁻¹K_dX`. `R` is a structured operator (diagonal for nadir). Two complementary
  seams: `LinearSolver` (methods/, backend swap *within* the kernel formulation) and
  `CovarianceOperator` Protocol (core/, carries the kernel→precision/SPDE jump).
- **`CovarianceOperator` is the seam, not the GP.** `GaussianPredictiveDistribution(mean,
  cov: CovarianceOperator)` is method-agnostic; GP math lives in `methods/oi.py`. Operator
  declares `fidelity ∈ {EXACT, LOW_RANK, SAMPLE}`.
- **Exact/persisted boundary:** the unit of work returns the **Persisted** rep (mean +
  exact marginal var + low-rank `B` + clipped diagonal residual `d` + seed + sampler spec +
  rank `r` + captured-energy diagnostic), **never** a live operator carrying `L`. `B` from a
  matrix-free seeded randomized SVD of `P`; `d = clip(diag(P)−rowsum(B²), 0, None)`.
- **Unifying on-worker rule:** the worker extracts *everything needing the EXACT operator* —
  base reduction, declared derived quantities (first-difference), AND eval-point predictions
  at withheld/off-grid locations — before discarding the operator. Off-grid predictives are
  computed exactly, never by interpolating a marginal-variance field (invariant 7).
- **`Product` is an explicit bundle:** base + derived Persisted products + eval-point
  predictions, provenance linking each (route + `CovFidelity` stamped).
- **Derived dispatch = linearity × representation × `CovFidelity`.** Provenance stamps the
  covariance fidelity used. Only `firstdifference` is real (on-worker, EXACT); velocity/eke/
  transport/area_average are committed-signature stubs.
- **Data (Decision B):** real `DataSource` against ODC THREDDS + `./data/cache/`; daily
  NATL60-CJM165 reference (NOT the 11 GB hourly) clipped to 42-day window
  **2012-10-22→2012-12-02**; OSSE nadir obs ~285 MB whole. Committed tiny NetCDF fixtures for
  offline CI. Oracle = opt-in OI-RMSE parity **within 10% of the ODC OI baseline** (skipif no
  data/network; ≤25% for the tiny-fixture smoke run). OSE eval uses the withheld **CryoSat-2**
  along-track.
- **Space-time structure (load-bearing):** the GP covariance is space-time — spatial length
  scale × **temporal correlation scale**, both through the `ParameterProvider`. The
  unit-of-work window is space-time (spatial tile × temporal obs window around target output
  time(s); the 21-day spin-up gives early times temporal neighbors and bounds `N_obs`).
  **`GridSpec` stays purely spatial**; time is carried on the `Product` as a series of
  per-time persisted fields. One factored `K_dd+R` serves all output times in the window.
- **Kernel:** pinned to stationary **Matérn-3/2** (variance + spatial length + temporal
  scale), behind a `methods/kernel.py::Kernel` interface so it can go nonstationary later
  without touching `GPCovarianceOperator`.

## Gotchas

- **mypy runs `mypy .` (whole tree, tests included)** via the pre-commit hook — test files
  must be type-clean too (e.g. assert `x is not None` before using an `Optional`). numpy ops
  often infer `Any`; wrap returns in `np.asarray(...)` to satisfy `no-any-return`. scipy/dask/
  distributed calls need `# type: ignore[import-untyped]` / `[no-untyped-call]`.
- **Plan deviations made & verified:** (1) Task 10 perturb_and_ensemble seeds members from the
  caller seed + index, not `id(obs)` (the plan's id-based seed broke the reproducibility test).
  (2) Task 19 CRPS test: the plan's expected `0.23379` is CRPS at y=0, but the test uses y=0.5;
  correct closed-form value is `0.331404`. Implementation formula is the standard correct CRPS.
  (3) Task 19/21: evaluators take `result: object` (not `dict[...]`) so they conform to the
  `Evaluator` protocol and can go into `Registry([...])`. (4) Task 21 `_evaluate`: OSSE runs
  calibration on the gridded truth (the plan only set TRUTH, so Calibration — which needs
  WITHHELD_OBS — would never fire and the OSSE acceptance demands reduced_chi2/coverage); OSE
  withholds CryoSat-2 by mission-splitting the obs window (the test passes a plain FixtureSource
  with no `withheld()` method, so withholding must happen in the pipeline, not the source).

- **Task-1 deviation (verified):** `.gitignore` never ignored `__pycache__`/`*.pyc`, so Phase 1
  left 77 `.pyc` files tracked. The rename swept them in; untracked them (`git rm --cached`) and
  added `__pycache__/`, `*.pyc`, `.mypy_cache/` to `.gitignore` so the soon-public repo stays
  clean. `pixi.lock` (593 KB) exceeds the 500 KB hook only under `--all-files`; it is unmodified
  so the staged-only commit hook passes.
- The 11 GB NATL60 reference is hourly — never pull it; use the daily file. Footprint stays a
  few hundred MB.
- NATL60 challenge has no observation error ⇒ `R` ≈ a nugget for the oracle.
- `pyinterp` / `GPSat` are NOT installed; Method 1 needs none. `pixi add` any new dep.
- BLAS/OpenMP env vars must be set per-worker *before* numpy/BLAS loads (Nanny child env).

## Deferred items / open questions

- **Next release — relax the conda recipe Python cap.** `pyproject.toml` now declares
  `requires-python = ">=3.12"` (cap dropped, commit `e236591`; source uses only stable stdlib
  and numpy/scipy/pyproj all ship cp314 wheels). The **0.1.0** recipe deliberately keeps
  `run: python >={{ python_min }},<3.14` to match the already-published 0.1.0 wheel (building
  0.1.0 on 3.14 would fail `pip install .` — its metadata excludes 3.14). On the next release:
  when the autotick bot opens the feedstock bump PR, drop the `,<3.14` from the `run` pin
  (→ `python >={{ python_min }}`) and mirror the same in `conda-recipe/meta.yaml`. Do NOT do
  this before a `>=3.12` wheel is on PyPI.
- **Optional:** `pixi.toml` dev pin still `python = ">=3.12,<3.14"` (left capped to avoid a
  `pixi.lock` re-solve; doesn't limit the published package). Relax only if CI should exercise 3.14.
