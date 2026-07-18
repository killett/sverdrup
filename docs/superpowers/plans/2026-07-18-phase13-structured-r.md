# Phase 13 — Structured Observation Error Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Per-mission noise variances + per-pass {bias, tilt} correlated error
modes for flagship MIOST via state augmentation, at box scale, five-mission
lineage, judged µ→λx under a sealed phase13 band protocol.

**Architecture:** Augmented state z = [η; c]: G_aug = [G B], Q_aug = diag(Q, Λ);
field-block marginal ≡ solve under R_eff = diag(σ²_m) + BΛBᵀ (extended duality
oracle proves mean AND variance). One 7-dim parameterization (δ×4 + ρ + Λ×2,
gauge mean(δ)=0, δ_s3a = −Σ); lanes as frozen restrictions {lane-0 signed /
lane-D 5-dim / lane-C 7-dim / modes-only probe-conditional}; sealed phase13
bands; winner chain = members → s(x) refit → diagnostics/readings → owner gate
→ ONE c2 touch → three-branch ruling.

**Tech Stack:** numpy/scipy sparse (existing `MiostSolver` untouched), existing
CRN (`miost_crn`), existing lane apparatus (`lane_compare`), Phase-9 harness,
Phase-11 geometry artifact.

**Spec:** `docs/superpowers/specs/2026-07-18-phase13-structured-r-design.md`
(governs on conflict). Kickoff riders: TDD red/green per behavior; dual review
per task; push as you go; zero c2 before T13; no source edits during gate
suites; behavioral pins inviolable.

**User decisions (already made):**
- Mechanism = state augmentation; riders 1–5 (spec §2). Alternatives rejected
  with arithmetic.
- Basis = {bias, tilt}/pass in s-units, shared Λ; segmentation = Phase-11
  geometry artifact's; class-agnostic; P2 excluded (spec §3).
- σ²_m = R_REF·exp(δ_m), mean(δ)=0, sweep δ_{alg,h2g,j2g,j2n}, δ_s3a = −Σ;
  ρ REOPENED; α/q_slope/L_t frozen at signed values (spec §4).
- Lanes each swept fresh; PRIMARY = lane-C vs lane-0; D-vs-0 secondary;
  modes-only lane probe-conditional, never claim-bearing; winner-lane rule =
  simpler lane on tie (spec §4, §7, §10).
- New CRN axis "err"; oracle covers mean+variance; teeth companion test-local
  only; pass identity time-based (spec §5).
- Identity target = signed miost5 artifacts, rtol 1e-12, four routes,
  column-absent semantics (spec §6).
- Pre-registration one-commit bundle before any sweep; 12 h owner-amendable
  wall default; both degradation criteria explicit (spec §7).
- SIGMA_OBS2 untouched; SHIPPED["miost"] unchanged this phase; six-mission
  refresh = recorded election (spec §10, §14).
- **Probe split (recorded deviation, forced by dependency):** the kickoff's
  "Task-0 probe (t_trial both configs)" splits into leg A (Task 0: scalar
  baseline + real pass counts — no augmented code exists yet) and leg B
  (Task 5: augmented t_trial + delta + PCG iters, after Tasks 1–4). Phase-10
  precedent (Task 0 signed probe / Task 5 factory-path probe). The §7 budget
  arithmetic consumes both legs; the bundle (Task 6) still lands BEFORE any
  sweep.

**Spec §19 obligations fixed in this plan:** (1) Λ→0 continuity tolerance →
Task 2 (rtol 1e-9 on the mean map at Λ = 1e-12 m²; derivation in task).
(2) Λ/δ boxes + source table → Task 6 bundle. (3) Real pass counts → Task 0.
(4) MC tolerance at m=100 → Task 4 (derivation in task). (5) Band-width rule
value → Task 6 (Phase-10 protocol family value carried; recorded in artifact).
(6) Five-mission lineage entry point → Task 11 step 1 (verify
`src/sverdrup/methods/registry.py` miost5 entry; migration noted if its form
surprises).

**Evidence namespace:** `phase13.miost.*` in
`data/2021a_ssh_mapping_ose/ours/` evidence store (gitignored; numbers quoted
into PROGRESS/commits verbatim).

---

## File structure

- Create `src/sverdrup/methods/miost_error_basis.py` — pass segmentation
  consumption, PassTable, `build_b`, pass identity ints, Λ diagonal expansion.
  One responsibility: the B block and its identities.
- Create `src/sverdrup/methods/miost_rspec.py` — `RSpec` dataclass (structure
  kind, δ dict, Λ pair, key() fragment, `r_for(missions)`), gauge arithmetic
  (δ_s3a = −Σ). One responsibility: the R parameterization.
- Modify `src/sverdrup/methods/miost.py` — `_solve_window` + `sample_members`
  augmented assembly, field-block slicing, params_key extension, retention
  slicing, parameter_space extension (new dims), ensemble kind version.
- Modify `src/sverdrup/methods/miost_crn.py` — add `err_noise`.
- Create `src/sverdrup/validation/phase13_lanes.py` — boxes, lane
  restrictions, shared-Sobol masking, anchors, bars.
- Create `scripts/phase13_probe.py`, `scripts/phase13_prereg.py`,
  `scripts/phase13_lane_run.py`, `scripts/phase13_compare.py`,
  `scripts/phase13_diagnostics.py` — mirroring the phase10 script family.
- Tests: `tests/test_miost_error_basis.py`, `tests/test_miost_rspec.py`,
  `tests/test_miost_augmented_oracle.py`, `tests/test_phase13_identity.py`,
  `tests/test_miost_ensemble_augmented.py`, `tests/test_phase13_lanes.py`,
  `tests/test_phase13_diagnostics.py`, `tests/test_phase13_prereg.py`.

Standing commands: `pixi run test`, `pixi run lint`, `pixi run typecheck`,
`pixi run pre-commit run --files <paths>`. Full suite in background (~20–35
min). Use the test-design skill for every test (behavior + concrete bug named).

---

### Task 0: Probe leg A — scalar baseline + real pass counts

**Goal:** Measure the scalar-config baseline (t_trial, peak RSS, PCG
iterations) and extract REAL per-window pass counts from the Phase-11 geometry
artifact, writing `phase13.probe.scalar` + `phase13.probe.passes`.

**Files:**
- Create: `scripts/phase13_probe.py` (leg A path)
- Test: `tests/test_phase13_probe.py` (arithmetic units only; the run is a
  script execution)

**Acceptance Criteria:**
- [ ] `phase13.probe.scalar` records wall seconds, peak RSS MiB, per-window
      PCG iteration counts (baseline expected ≈302 at cap 500 — the signed
      run's figure; assert recorded, don't assert the value), host cpu/mem.
- [ ] `phase13.probe.passes` records, per 60-day window (9 windows) × mission:
      pass count, median pass length (n_obs), chord-length stats — derived
      from the SAME segmentation the geometry artifact v3 pins (consume
      `src/sverdrup/application/orbit_geometry.py`; artifact sha recorded).
- [ ] Analytic estimate ~240 passes/window (spec §12) compared against
      measured; delta recorded (no bar — this replaces the estimate).
- [ ] Task-22 ledger quoted in the probe record (model conservatism ratio +
      retained-store term BY NAME); model NOT retuned.
- [ ] Zero c2: probe consumes the five-mission obs set only (j3/c2 absent
      from inputs; assert in-script on file list).

**Verify:** `pixi run test -- tests/test_phase13_probe.py -v` → PASS;
`pixi run python scripts/phase13_probe.py --leg scalar` completes; evidence
keys present via `jq '.phase13.probe | keys' <evidence.json>`.

**Steps:**
- [ ] Write failing unit tests for the pass-count aggregation helper (given a
      synthetic PassTable-like frame, counts per mission/window are exact) and
      the file-list guard (j3/c2 path in input list → `ValueError`). Run,
      confirm FAIL.
- [ ] Implement `scripts/phase13_probe.py` leg A: full-year five-mission POINT
      solve at the signed config (params verbatim from the signed record —
      same source `stage_miost_gate_results.json` reads as Phase-12), RSS via
      `resource.getrusage`, per-window `CONVERGENCE_LOG` capture; pass counts
      via the Task-1 segmentation rule applied read-only here (duplicate-free:
      import the geometry artifact's segmentation parameters, record its sha).
      Run tests → PASS.
- [ ] Execute leg A (background, `nohup` + pid + log per standing memory);
      record evidence; commit `feat: phase13 probe leg A — scalar baseline +
      measured pass counts`. Push.

---

### Task 1: Pass table + B-builder (`miost_error_basis.py`)

**Goal:** Window-independent pass segmentation + the B block in s-units with
time-based pass identities.

**Files:**
- Create: `src/sverdrup/methods/miost_error_basis.py`
- Test: `tests/test_miost_error_basis.py`

**Acceptance Criteria:**
- [ ] `PassTable` frozen dataclass: `pass_mission (n_pass,) int64`,
      `pass_start_s (n_pass,) int64` (integer seconds since epoch 2017-01-01
      of the pass's first obs — TIME-BASED identity, spec §5 rider 2),
      `obs_pass_idx (n_obs,) int32`, `s (n_obs,) float64 ∈ [−1, 1]`.
- [ ] `segment_passes(lon, lat, t_days, mission_hash)` groups obs by
      (mission, time-gap rule consistent with the Phase-11 geometry artifact's
      pass segmentation — same gap constant, imported not copied); s =
      2·(arc − arc_min)/(arc_max − arc_min) − 1 with arc = cumulative
      great-circle distance in time order; single-obs pass → s = 0.
- [ ] `build_b(pt) -> csr (n_obs, 2·n_pass)`: column 2p = 1 (bias), column
      2p+1 = s (tilt); IDENTICAL columns for a pass regardless of which
      window's obs subset built it (window-independence test: two overlapping
      synthetic windows → same per-pass column values on shared obs).
- [ ] `lam_diag(n_pass, lam_bias, lam_tilt) -> (2·n_pass,)` tiled diagonal.
- [ ] `err_identity(pt) -> (2·n_pass, 3) int64` rows
      (mission_hash, pass_start_s, mode_idx) — deterministic, collision-free
      across missions/passes (test: two missions, same start second → distinct
      rows).

**Verify:** `pixi run test -- tests/test_miost_error_basis.py -v` → all PASS.

**Steps:**
- [ ] Failing tests first (each names the bug it catches: e.g. s computed in
      time-units not arc-length → unequal-spacing fixture fails; positional
      pass ids → reordered-input fixture fails). Run → FAIL.
- [ ] Implement module (sketch):

```python
def segment_passes(lon, lat, t_days, mission_hash) -> PassTable:
    order = np.argsort(t_days, kind="stable")
    # per mission: split where dt > PASS_GAP_S (geometry-artifact constant)
    # arc-length s per pass:
    d = _great_circle_km(lon[i0:i1], lat[i0:i1])   # cumulative, km
    span = d[-1] - d[0]
    s = np.zeros_like(d) if span == 0 else 2.0 * (d - d[0]) / span - 1.0
```

- [ ] Run → PASS. `pixi run pre-commit run --files src/sverdrup/methods/miost_error_basis.py tests/test_miost_error_basis.py`.
      Commit `feat: phase13 pass table + B-builder in s-units`. Push.

---

### Task 2: RSpec + augmented assembly + extended duality oracle

**Goal:** The R parameterization, augmented `_solve_window`, column-absent
restriction, params_key/cache lineage, and the oracle proving
augmentation ≡ structured R for mean AND variance.

**Files:**
- Create: `src/sverdrup/methods/miost_rspec.py`
- Modify: `src/sverdrup/methods/miost.py` (`_solve_window`, `_params_key`,
  `parameter_space`)
- Test: `tests/test_miost_rspec.py`, `tests/test_miost_augmented_oracle.py`

**Acceptance Criteria:**
- [ ] `RSpec(deltas: dict[str, float], log_lam_bias: float | None,
      log_lam_tilt: float | None)`: `sigma2_for(mission_hashes) -> (n,)`
      via σ²_m = R_REF·exp(δ_m); δ_s3a DERIVED = −Σ(four swept) — never an
      input; `modes_active` property (both Λ set); `key()` fragment with
      structure kind + all five δ (incl. derived) + Λ + basis id + the
      segmentation-artifact version (spec §11); scalar config (`deltas` all
      zero, Λ None) → `key()` fragment EQUAL to the current scalar-era
      fragment (params_key backward-identical — cache lineage: augmented
      configs get NEW keys, scalar config keeps its key).
- [ ] `_solve_window`: `modes_active` → `g_aug = sparse.hstack([g, b],
      format="csr")`, `q_aug = concat([q, lam_diag])`, r per-mission; eta
      field-block sliced `eta_full[:n_elem]` before every downstream use;
      NOT `modes_active` → NO B columns built (structural absence, spec §2
      rider 3).
- [ ] Extended duality oracle (small case, 2 rungs, ~50 obs, 2 synthetic
      passes): augmented reduced solve vs dense obs-space OI with
      R_eff = diag(σ²_m) + BΛBᵀ — MEAN at rtol 1e-8 AND field-marginal
      posterior VARIANCE at query points at rtol 1e-8 (dense
      A = G_augᵀR⁻¹G_aug + Q_aug⁻¹; slice (A⁻¹)_ηη; Γ_q(A⁻¹)_ηηΓ_qᵀ vs
      B_qq − B_qd(B_dd + R_eff)⁻¹B_qdᵀ).
- [ ] Λ→0 continuity: Λ = 1e-12 m² solution vs column-absent solution, mean
      map rtol 1e-9 (§19.1 fixed: 1e-12/R_REF ≈ 1e-9 relative prior weight;
      PCG rtol 1e-6 dominated — tolerance 1e-9 on the map with pcg_rtol
      tightened to 1e-13 in the test, derivation in test docstring).
- [ ] Per-mission gauge test: common δ shift ≡ ρ shift for the mean
      (rtol 1e-10 small case) — the §4 exact-flat claim, executable.

**Verify:** `pixi run test -- tests/test_miost_rspec.py
tests/test_miost_augmented_oracle.py -v` → all PASS; `pixi run typecheck`
clean.

**Steps:**
- [ ] Failing oracle test first (dense side written independently from the
      spec equation, never from the implementation). Run → FAIL (no RSpec).
- [ ] Implement `miost_rspec.py`; wire `_solve_window` (sketch):

```python
if rspec.modes_active:
    pt = segment_passes(...); b = build_b(pt)
    g_use = sparse.hstack([g, b], format="csr")
    q_use = np.concatenate([q, lam_diag(pt.n_pass, lb, lt)])
else:
    g_use, q_use = g, q
r = rspec.sigma2_for(obs_mission_hash)
eta_full, report = MiostSolver(g_use, r, q_use).solve(rhs_from_obs(g_use, r, y))
eta = eta_full[: els.identity.shape[0]]
```

- [ ] Run → PASS. New params (`delta_alg, delta_h2g, delta_j2g, delta_j2n,
      log_lam_bias, log_lam_tilt`) added to `parameter_space` with WIDE
      method-level bounds (δ ∈ (−3, 3), log10 Λ ∈ (−8, −1) — the existing
      `log10_rho (−2, 3)` pattern); the SWEEP boxes are the Task-6 bundle's
      and live in `phase13_boxes.py`, sealed there. Commit `feat: phase13
      RSpec + augmented assembly + extended
      duality oracle`. Push.

---

### Task 3: Identity / nesting suite (miost5 target)

**Goal:** Prove the constant restriction reproduces the signed FIVE-MISSION
(miost5) product exactly; close the c-block leak class.

**Files:**
- Test: `tests/test_phase13_identity.py`

**Acceptance Criteria:**
- [ ] Constant restriction (all δ = 0, modes column-absent) vs the signed
      miost5 artifacts: rtol 1e-12 on all FOUR routes (S-path grid, Γ-path
      points, member route, variance route); mean maps bit-identical where
      achievable (assert bit, fall back to rtol 1e-12 with the failure mode
      printed). Target = miost5, NEVER `SHIPPED` (resolves to miost6).
- [ ] Query-route test, BOTH forms: (a) structural — product routes consume
      the η slice alone; (b) behavioral — perturb the c-slice of a solved
      state object, assert every product route output bit-unchanged.
- [ ] CRN no-perturbation regression, BOTH pre-existing axes: at δ = 0,
      obs-axis draws bit-identical to scalar-era `obs_noise` outputs AND
      elem-axis (η̃) draws bit-identical (fixture: recorded draw vectors at a
      pinned root/member/identity set).
- [ ] Lane-0 record QUOTED (µ = 0.8642 constant in the lane apparatus, Task
      7) — no re-solve here beyond the identity fixtures (dev-scope
      12-day window per `stage_a_scope.json` where full-year is not needed).

**Verify:** `pixi run test -- tests/test_phase13_identity.py -v` → all PASS.

**Steps:**
- [ ] Failing tests (behavioral c-perturb test constructed on an augmented
      small solve — catches a variance route summing over all columns). Run →
      FAIL where machinery missing; fix; PASS.
- [ ] Commit `test: phase13 identity/nesting suite vs signed miost5 — four
      routes, c-block leak class closed`. Push.

---

### Task 4: CRN "err" axis + augmented sampling + consistency tests

**Goal:** Member sampling on the augmented state with the new draw axis;
member-variance consistency vs the analytic posterior; teeth companion.

**Files:**
- Modify: `src/sverdrup/methods/miost_crn.py` (add `err_noise`),
  `src/sverdrup/methods/miost.py` (`member_rhs_matrix`, `sample_members`,
  retention slicing, ensemble kind version)
- Test: `tests/test_miost_ensemble_augmented.py`

**Acceptance Criteria:**
- [ ] `err_noise(member, identity, lam_var, root)` — axis key `"err"`,
      identity rows from `err_identity` (spec §5); draws identical across
      overlapping windows (window-independence test).
- [ ] `member_rhs_matrix` augmented: columns
      `G_augᵀR⁻¹(y+ε'_i) + Q_aug⁻¹[η̃_i; c̃_i]`; ε' via existing `obs_noise`
      with per-mission r_var (stream unchanged — bit-equal check at δ=0 lives
      in Task 3).
- [ ] Retention slicing: `anoms[w.id]` holds FIELD-BLOCK rows only
      (`[: n_elem]`) — retained member store size unchanged (spec §12).
- [ ] Persisted ensemble kind VERSIONED (new tag; `load_state` refuses
      mismatch — extend the existing kind-tag test pattern).
- [ ] Mean-vs-deterministic identity at an augmented config: ensemble mean ==
      deterministic augmented solve (rtol 1e-12, small case).
- [ ] Member-variance consistency: small case, m = 2000 in-test draws,
      empirical member variance vs analytic augmented field-marginal
      posterior; tolerance = 5·SE where SE = var·√(2/(m−1)) per node
      (χ² MC arithmetic; derivation in docstring). §19.4 fixed for m = 100
      acceptance runs: same statistic, tolerance 5·var·√(2/99) ≈ 0.71·var —
      recorded as the acceptance-run consistency row.
- [ ] TEETH companion: broken sampler (c̃ omitted via test-local injection —
      NEVER a code path/flag) FAILS the same statistic by ≫ tolerance on a
      fixture where the mode share of posterior variance is ≥ 50%
      (constructed: large Λ, few obs/pass).

**Verify:** `pixi run test -- tests/test_miost_ensemble_augmented.py -v` →
all PASS (correct sampler passes, broken sampler test asserts failure
magnitude).

**Steps:**
- [ ] Failing tests first (teeth test written BEFORE the sampler extension —
      it must fail against the unextended white-only path, demonstrating the
      hazard is real). Run → FAIL.
- [ ] Implement (sketch):

```python
def err_noise(member: int, identity: np.ndarray, lam_var: np.ndarray, root: Seed) -> np.ndarray:
    u = _keyed_uniform(_member_key(root, member, "err"), identity)
    return np.asarray(np.sqrt(lam_var) * ndtri(u))
```

- [ ] Run → PASS. Commit `feat: phase13 err CRN axis + augmented member
      sampling + variance-consistency oracle with teeth`. Push.

---

### Task 5: Probe leg B — augmented cost + budget arithmetic

**Goal:** Measure the augmented config's t_trial/peak/PCG-iterations, the
scalar delta, and derive n-per-lane + the modes-only conditional.

**Files:**
- Modify: `scripts/phase13_probe.py` (leg B)
- Test: `tests/test_phase13_probe.py` (budget arithmetic units)

**Acceptance Criteria:**
- [ ] `phase13.probe.augmented`: full-year five-mission POINT solve at the
      pinned augmented probe config (δ = 0.2·[+1,+1,−1,−1] pattern, mid-box
      Λ — pinned in-script with rationale comment); wall, peak RSS
      (retained-store term named in the record), per-window PCG iterations
      beside leg A's.
- [ ] Delta vs scalar recorded (expected ~negligible at +0.24% cols; measured
      anyway — spec §7).
- [ ] Budget arithmetic: n_full per lane = floor(wall_h·3600/t_trial_B) per
      the sealed template; floor 8; screening contingency determination;
      MODES-ONLY CONDITIONAL resolved (4th lane iff budget covers n ≥ 8
      after three committed lanes) — recorded either way with the arithmetic.
- [ ] Wall default 12 h carried as the owner-amendable pre-registered value
      (consumed by Task 6's bundle; standing rule 3b note in the record).

**Verify:** `pixi run test -- tests/test_phase13_probe.py -v` → PASS; evidence
keys `phase13.probe.augmented` + `phase13.probe.budget` present.

**Steps:**
- [ ] Failing unit tests for budget arithmetic (floor, contingency branch,
      conditional-lane rule — each with a hand-computed fixture). Run → FAIL.
- [ ] Implement leg B; run it (background, watcher on pid-exit); record.
- [ ] Run tests → PASS. Commit `feat: phase13 probe leg B — augmented cost +
      n-per-lane arithmetic + modes-only determination`. Push.

---

### Task 6: Pre-registration ONE-COMMIT bundle

**Goal:** Seal everything claim-bearing before any sweep, in one commit.

**Files:**
- Create: `scripts/phase13_prereg.py`,
  `src/sverdrup/validation/phase13_boxes.py` (box constants + source table)
- Test: `tests/test_phase13_prereg.py`
- Artifact: `phase13_band_artifact.json` (repo root, sha-sealed like
  `phase10_band_artifact.json`)

**Acceptance Criteria:**
- [ ] Sealed band artifact via `lane_compare.seal_protocol` family: seed,
      contiguous day/pass block bootstrap, λ rule, single-execution rule,
      refusal clock on created_utc, protocol_sha binding + tamper refusal;
      BOTH degradation criteria explicit (n_lambda_used ≥ 50% AND band-width
      rule ≤ 25 km — the Phase-10 family value carried, §19.5) with the
      deviation-from-Phase-10 (width-only) noted and reasoned IN the artifact.
- [ ] 91-day screening day list (days 1,5,…,361 family) + k = 3 co-sealed;
      wall default 12 h recorded owner-amendable.
- [ ] δ boxes: ±0.7 in log-variance (≈ ×2 either way in σ²) for the four
      swept contrasts, derived δ_s3a range recorded; Λ boxes: log10 Λ ∈
      [−6, −2.5] m² (σ_mode ≈ 1–56 mm — brackets cm-order post-LWE residual
      budgets); SOURCE TABLE in `phase13_boxes.py` docstring (published
      per-mission noise + residual-LWE citations; entries marked
      verify-at-review), boxes recorded in the artifact.
- [ ] Lane-0 per-point validation residual arrays REGENERATED
      deterministically at the signed config; asserted against recorded
      validation µ = 0.8642 (exact recorded precision); stored beside the
      artifact for pair-band computation.
- [ ] Primary/secondary designation + winner-lane rule + modes-only
      conditional rule + negative wording (verbatim + scope clause) restated
      in the artifact.
- [ ] Sobol dim assignment recorded: dims 1–4 = δ_{alg,h2g,j2g,j2n}, 5 = ρ,
      6–7 = {Λ_bias, Λ_tilt}; ONE shared engine
      `derive_seed("miost","phase13-lanes","sobol",0)`; per-lane MASKING;
      NO per-lane engines.
- [ ] ALL of the above lands in ONE commit.

**Verify:** `pixi run test -- tests/test_phase13_prereg.py -v` → PASS
(tamper refusal, µ assertion, box constants import); `jq .protocol_sha
phase13_band_artifact.json` non-empty.

**Steps:**
- [ ] Failing tests (tamper → `PreRegistrationError`; µ mismatch → refuse;
      derived δ_s3a range arithmetic). Run → FAIL.
- [ ] Implement + seal + regenerate arrays (background run). Tests → PASS.
- [ ] ONE commit `feat: phase13 pre-registration bundle — sealed bands, boxes
      + sources, lane-0 arrays, designations`. Push.

---

### Task 7: Lane machinery + dev smokes

**Goal:** Lanes-as-restrictions runner with shared-Sobol masking, anchors,
checkpoints, live bars — smoked on the dev scope.

**Files:**
- Create: `src/sverdrup/validation/phase13_lanes.py`,
  `scripts/phase13_lane_run.py`
- Test: `tests/test_phase13_lanes.py`

**Acceptance Criteria:**
- [ ] Lane definitions {lane-0 quoted, D, C, modes-only-conditional} as
      FROZEN RESTRICTIONS of the 7-dim space (masked dims pinned to 0/None →
      column-absent, spec §2 rider 3); one shared Sobol engine, per-lane
      masking (projection test: shared dims of paired trials equal across
      lanes at the same index).
- [ ] Anchors = evaluated extra points (lane-0 config in D and C at Λ
      box-floor; D-winner into C post-selection) — never Sobol points.
- [ ] Crash-durable per-trial checkpoints (phase10_lane_run pattern);
      launch rule reads the Task-6 bundle (wall default; refuses if absent).
- [ ] Dev smokes: both lanes on the `stage_a_scope.json` 12-day dev scope,
      live bars trip arbitrary dev points as pre-registered (Phase-10
      pattern); zero c2 (guard by test).
- [ ] PCG iteration telemetry per trial recorded (conditioning watch row).

**Verify:** `pixi run test -- tests/test_phase13_lanes.py -v` → PASS; dev
smoke exits 0 with checkpoint files written.

**Steps:**
- [ ] Failing tests (masking projection; anchor-not-Sobol bookkeeping;
      bundle-absent refusal). Run → FAIL. Implement. PASS.
- [ ] Dev smokes (foreground, minutes). Commit `feat: phase13 lane machinery +
      dev smokes`. Push.

---

### Task 8: Sweeps — lane-D, lane-C (+ conditional modes-only)

**Goal:** Execute the pre-registered sweeps under the sealed budget.

**Files:**
- Run-only (checkpoints + evidence `phase13.miost.lanes.*`); no source edits.

**Acceptance Criteria:**
- [ ] Launch rule evaluated from the Task-5 arithmetic + Task-6 bundle BEFORE
      launch (est ≤ wall default or WAIT for owner — standing rule 3b; never
      executor-amended).
- [ ] Lane-D then lane-C swept (screening contingency if armed: 91-day
      screening n=30/lane, k=3 full re-scores); modes-only lane run or
      "not run" recorded with the probe arithmetic as reason.
- [ ] Winners recorded at full precision with per-point residual arrays
      persisted (band pairs need arrays); anchors evaluated; admissibility
      patterns logged; PCG telemetry per trial.
- [ ] Zero c2 phase-wide (validation track only).
- [ ] No source edits during the runs (standing memory; runs are long — any
      fix means clean re-run of affected trials).

**Verify:** checkpoints complete for all committed lanes;
`jq '.phase13.miost.lanes | keys'` shows lane records + winners.

**Steps:**
- [ ] Launch per rule (background, nohup + pid + log, watcher on pid-exit).
- [ ] On completion: record winners + telemetry; commit evidence-quoting docs
      `feat: phase13 lane sweeps — winners + telemetry recorded`. Push.

---

### Task 9: Comparison read → BRANCH record

**Goal:** The claim-bearing read under the sealed protocol; branch recorded.

**Files:**
- Create: `scripts/phase13_compare.py`
- Test: `tests/test_phase13_compare.py` (wording pin, refusal clock order,
  single-execution rule)

**Acceptance Criteria:**
- [ ] Refusal clock FIRST; protocol_sha recomputed and matched; bands computed
      per consulted pair at read (lane-C winner vs lane-0 PRIMARY; D-vs-0 and
      modes-only rows as secondaries — same bands, never claim-bearing).
- [ ] Lexicographic µ→λx with BOTH degradation criteria; verdict wording via
      the pinned `primary_wording` branch strings.
- [ ] Winner-lane rule applied on the record: C-vs-D within band → lane-D
      takes the chain (spec §10).
- [ ] Verdict at `phase13.miost.lanes.verdict` with full-precision numbers +
      protocol_sha + timestamps; BRANCH RECORDED (negative → Task 10;
      winner → Tasks 11–14).
- [ ] Dual review per standing discipline (spec-compliance + adversarial) on
      the verdict before the branch executes.

**Verify:** `pixi run test -- tests/test_phase13_compare.py -v` → PASS;
verdict key present with `branch` field.

**Steps:**
- [ ] Failing tests (clock-first order via injected stale clock → refuse;
      wording string-equal to pin). Run → FAIL. Implement. PASS.
- [ ] Execute the read ONCE (single-execution rule). Commit `feat: phase13
      lane comparison read — verdict + branch recorded`. Push.

---

### Task 10: NEGATIVE branch close (executes only on branch=negative)

**Goal:** The pre-registered negative result, recorded honestly; no touch.

**Files:**
- Modify: `PROGRESS.md`

**Acceptance Criteria:**
- [ ] Wording verbatim: "improvements within band" + scope clause "under this
      search (recorded n/lane, wall, screening state)".
- [ ] Framed as the measurement of the box-scale residual-error budget
      (spec §16); §8 diagnostics still computed report-only for the record
      (they are part of the measurement).
- [ ] NO c2 touch; tally unchanged {miost5: 2, miost6: 1}; Tasks 11–14 closed
      as superseded (Phase-8 Task-13 branch semantics).
- [ ] PROGRESS close banner; all evidence pushed.

**Verify:** PROGRESS banner quotes verdict numbers verbatim from
`phase13.miost.lanes.verdict`; `git log origin/main..HEAD` empty after push.

**Steps:**
- [ ] Record, close, commit `docs(progress): phase-13 CLOSE — pre-registered
      negative, measured not shipped`. Push.

---

### Task 11: WINNER chain — members, s(x) refit, diagnostics, readings

**Goal:** Full acceptance substrate on the winner (executes only on
branch=winner).

**Files:**
- Create: `scripts/phase13_diagnostics.py`
- Modify: winner-run wiring in `scripts/phase13_lane_run.py` (ensemble mode)
- Test: `tests/test_phase13_diagnostics.py`

**Acceptance Criteria:**
- [ ] FIRST: verify the five-mission lineage entry point in
      `src/sverdrup/methods/registry.py` (miost5 factory/record/σ-semantics;
      §19.6) — note the migration if its current form surprises; a win
      updates THIS entry, `SHIPPED["miost"]` untouched (spec §14).
- [ ] Members m = 100 at the winner config, root = the recorded exact-int
      seed-root convention; retention slicing verified (field-block only);
      m=100 member-variance consistency row recorded (Task-4 tolerance).
- [ ] s*/s(x) REFIT via the Phase-9 harness (`refit_winner`/`run_harness`
      path) on the new posterior — five-mission/j3 discipline; SIGMA_OBS2
      untouched; ŝ delta + G_pre→G_post under the MIOST anchor family +
      s(x) shape summary recorded (spec §9b).
- [ ] §8 diagnostics computed for lane-D and lane-C winners (+ conditional
      lane if run): variance-ratio table (+ shrinkage note), saturation
      fraction, lag-1 autocorrelation per mission × family (asc/desc, median
      Δt, ±2/√n null band), field-correlation complement (sign logic per
      spec §8.4), adjacent-window ĉ agreement scatter — from the c-block
      diagnostic tap (window-tagged artifact, winner-only).
- [ ] §9 readings: GroundTrack on the winner mean maps (retro pattern;
      direction vs 0.410 recorded), SpectralFidelity descriptive row,
      mean-map deltas vs miost5.
- [ ] Zero c2 still (validation track only).

**Verify:** `pixi run test -- tests/test_phase13_diagnostics.py -v` → PASS;
evidence keys `phase13.miost.{members,refit,diagnostics,readings}` present.

**Steps:**
- [ ] Failing diagnostic unit tests (each statistic on hand-computed
      fixtures; lag-1 null band arithmetic; sign-logic fixture). Run → FAIL.
      Implement. PASS.
- [ ] Execute members + refit + diagnostics + readings (background). Commit
      `feat: phase13 winner chain — members, s(x) refit, diagnostics,
      readings`. Push.

---

### Task 12: OWNER GATE 1 — evidence pack review

**Goal:** Assemble and hold the gate-1 pack for owner review.

> **USER-ORDERED GATE — NON-SKIPPABLE.** This task was requested by the user
> in the current conversation. It MUST NOT be closed by walking around it, by
> declaring it "verified inline", or by substituting a cheaper check. Close
> only after every item in `acceptanceCriteria` has been re-validated
> independently, with output captured.

**Files:**
- Modify: `PROGRESS.md` (pack-held banner)

**Acceptance Criteria:**
- [ ] Pack re-validated on the FINAL tree with captured output: verdict +
      bands (jq), identity suite PASS, oracle + member-variance + teeth PASS,
      full suite w/ coverage, §8 diagnostics + §9 readings quoted verbatim
      from artifacts, refit rows, sizing/telemetry rows (PCG vs 302),
      registry untouched check (empty diff on `SHIPPED`), zero-c2 grep.
- [ ] Pack ORDER per template: readings/diagnostics first, then verdict
      arithmetic, then budget/telemetry ledger rows.
- [ ] HELD for owner review — the task closes on the owner's approval
      message, never on pack assembly.

**Verify:** every pack row quotes a captured command output (no
from-memory numbers); PROGRESS banner "pack held" committed + pushed.

**Steps:**
- [ ] Assemble on final tree (no source edits during the gate suite —
      standing memory). Commit `docs(progress): phase-13 gate-1 pack held for
      owner review`. Push. STOP for owner.

---

### Task 13: The ONE c2 touch

**Goal:** Execute the single acceptance touch under fresh owner
authorization; report; STOP.

> **USER-ORDERED GATE — NON-SKIPPABLE.** This task was requested by the user
> in the current conversation. It MUST NOT be closed by walking around it, by
> declaring it "verified inline", or by substituting a cheaper check. Close
> only after every item in `acceptanceCriteria` has been re-validated
> independently, with output captured.

**Files:**
- Modify: `scripts/phase13_compare.py` or a dedicated `--c2-touch` runner
  (TDD mechanics per the Phase-12 `--c2-touch` precedent, `15b09c3`)
- Test: touch-refusal tests (no-env refuse; provenance tripwire refuses
  BEFORE the c2 file opens; window tripwire n = 44,844 + year-span;
  one-invocation mechanics)

**Acceptance Criteria:**
- [ ] AUTHORIZATION IS FRESH: the touch executes only after an explicit owner
      message following Task 12 — never carried over.
- [ ] Ceremony verbatim (template): exact-string-"1" env
      (`SVERDRUP_MIOST_C2`), provenance tripwire recomputes ALL fields and
      refuses before the c2 file opens, window tripwire, one-invocation
      mechanics (third refuses).
- [ ] Reading sealed pre-touch: µ ≥ 0.85 floor; coverage 0.6827±0.10
      (field-calibrated referent); (µ,σ,λx) + chi2/CRPS + regional/monthly
      rows; mean-map deltas + c2 regional rows vs miost5 (spec §9c).
- [ ] Tally arithmetic recorded: {miost5: 2 → 3, miost6: 1}.
- [ ] Report + THREE-BRANCH menu to owner; no branch pre-committed; STOP.

**Verify:** touch log captured; refusal tests green BEFORE the touch; tally
row in the report; session STOPPED awaiting the ruling.

**Steps:**
- [ ] TDD the touch mechanics (refusals first, red/green). Commit. Execute
      the authorized touch ONCE. Report. STOP.

---

### Task 14: Owner ruling — lineage flip + sweep + election record + close

**Goal:** Execute the owner's three-branch ruling; close the phase.

> **USER-ORDERED GATE — NON-SKIPPABLE.** This task was requested by the user
> in the current conversation. It MUST NOT be closed by walking around it, by
> declaring it "verified inline", or by substituting a cheaper check. Close
> only after every item in `acceptanceCriteria` has been re-validated
> independently, with output captured.

**Files:**
- Modify: `src/sverdrup/methods/registry.py` (five-mission lineage entry
  ONLY — on sign-off branch), `PROGRESS.md`

**Acceptance Criteria:**
- [ ] Executes ONLY on the owner's sign-off message (three-branch ruling; no
      branch pre-committed).
- [ ] On sign-off: five-mission lineage entry updated (SHIPPED["miost"] =
      miost6 UNCHANGED — spec §14 pin); FULL external sweep on the flip tree
      (standing rule, third application); §14 six-mission-refresh election
      RECORDED as a named owner item (never folded in).
- [ ] PROGRESS close banner with the full task record + honest tally +
      deferred-items hygiene; everything pushed.

**Verify:** external sweep counts recorded on the flip tree;
`git log origin/main..HEAD` empty; PROGRESS close banner quotes artifacts
verbatim.

**Steps:**
- [ ] Execute per ruling; commit flip + `docs(progress): phase-13 CLOSE`;
      push.

---

## Self-review (run before handoff)

- Spec coverage: §2→T2, §3→T1, §4→T2/T6/T7, §5→T4, §6→T3, §7→T5/T6/T8,
  §8→T11, §9→T11/T13, §10→T9–T14, §11→T2/T4, §12→T0/T5, §13 (contract —
  no build), §14→T11/T14, §15 (scope guard on every task), §16→T10 wording,
  §17 (grounding — no build), §19.1–6 fixed in T2/T6/T0/T4/T6/T11.
- Both branches representable: T10 vs T11–T14 with Phase-8 branch semantics.
- No placeholders; types consistent (PassTable/RSpec names used identically
  across tasks).
