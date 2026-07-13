# Phase 10 — Latitude-Varying OI Parameters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve invariant-12 option B for OI: latitude-varying signal_variance
and length_scale as low-dof tuned provider fields, judged by the Phase-9
measurement layer, shipping (on success) a calibrated flagship OI product.

**Architecture:** One core parameterization {c0, log_L0, Lt} with lanes as
restrictions; Paciorek–Schervish nonstationary Gaussian degree-space kernel;
Phase-5 tuner reused unmodified under a lexicographic selection layer with
measured bands; Phase-9 harness reused for the acceptance fit (new frame) and
the flattening readings (frozen pre-B frame); registry role-split
(METHODS/SHIPPED).

**Tech Stack:** numpy/scipy/xarray; existing sverdrup tuning + calibration
modules; pixi/pytest/ruff/mypy; pre-commit.

**Spec (governs on conflict):**
`docs/superpowers/specs/2026-07-13-phase10-latvarying-params-design.md`

**User decisions (already made):** forks a–e + eleven batch folds, recorded in
spec §12; owner plan-structure expectations (task graph, plan-detail
obligations) from the file-review message, folded here verbatim-intent.

**Standing discipline (every task):** dual review (spec + quality) per task;
commit + push after every task; ZERO c2 touches before Task 13 (no task other
than 13 imports or reads c2 paths); PROGRESS edits are explicit steps, not
afterthoughts. Suite green at every close: `pixi run test`, `pixi run lint`,
`pixi run typecheck`.

**Ordering deviation, recorded:** the spec's Task-0 probe measures BOTH the
signed config and the Paciorek path. The Paciorek kernel does not exist until
Task 4, so Task 0 measures the signed config and writes the budget TEMPLATE;
Task 5 (pre-registration) re-runs the probe through the Paciorek path and
finalizes the budget arithmetic. Both numbers land at `phase10.oi.probe`
before any trial runs — the spec's requirement (budgets from measurement,
recorded before trials) is satisfied; only the measurement is split.

**Band-source pin (plan-level resolution of a spec obligation):** §9's refusal
demands the band artifact predate lane-winner records, and the per-lane winner
selection itself uses the bands (lexicographic read). Bands therefore cannot
come from lane products. They are computed from the two Task-0/Task-5 PROBE
map pairs (signed config vs pinned Paciorek probe config) — a pre-registered
config pair that exists before any trial, at a typical config separation.
Recorded inside the band artifact as `source_pair`.

---

## File structure (locked here)

- `src/sverdrup/core/parameters.py` — MODIFY: add `LatitudeField`; replace
  `LatitudeVaryingProvider` body (superseded in place).
- `src/sverdrup/methods/kernel.py` — MODIFY: add `PaciorekGaussianDegrees`.
- `src/sverdrup/methods/oi.py` — MODIFY (Task 14 only): `shipped_oi()` +
  `ConfiguredOI`.
- `src/sverdrup/methods/registry.py` — MODIFY: role-split, `SHIPPED` table.
- `src/sverdrup/validation/run.py` — MODIFY: provider-aware Gaussian-degrees
  kernel builder (the `_oi_kernel_from_params` precedent, extended).
- `src/sverdrup/validation/phase10_lanes.py` — CREATE: lane core box +
  restrictions, provider/kernel construction from a scalar trial dict, anchor
  embedding (OI param names live in validation/, never application/tuning/).
- `src/sverdrup/application/tuning/lane_compare.py` — CREATE: method-agnostic
  band computation (block resampling), band artifact schema, lexicographic
  selection layer, refusal clock, comparison verdict.
- `scripts/phase10_probe.py` — CREATE: Task-0/Task-5 probe runs.
- `scripts/phase10_prereg.py` — CREATE: one-commit pre-registration artifact
  (bands + day list + k + budget arithmetic).
- `scripts/phase10_lane_run.py` — CREATE: per-lane tuning execution.
- `scripts/phase10_compare.py` — CREATE: winner selection + PRIMARY verdict.
- `scripts/phase10_acceptance.py` — CREATE: winner re-solve → maps + hashes →
  mask → acceptance fit (new tuple).
- `scripts/phase10_flatten_read.py` — CREATE: frozen-frame G_post readings +
  G_pre_oi anchor.
- `scripts/phase10_c2_touch.py` — CREATE (Task 12): the gate-2 touch runner.
- Tests: `tests/test_phase10_provider.py`, `tests/test_paciorek_kernel.py`,
  `tests/test_oi_dispatch.py`, `tests/test_registry_roles.py`,
  `tests/test_lane_compare.py`, `tests/test_phase10_lanes.py`,
  `tests/test_phase10_tripwires.py`; MODIFY the three provider-consumer test
  files (spec §2).

Evidence home: `data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json`
(same JSON as phases 8/9), keys per spec §10. Artifacts under
`data/2021a_ssh_mapping_ose/ours/` with `phase10_` prefixes.

---

### Task 0: Signed-config runtime probe + probe/budget scaffolding

**Goal:** Measure one full-year OI re-solve (mean+var maps, 365 days,
train-only obs) at the signed config; write `phase10.oi.probe.signed` and the
budget TEMPLATE (arithmetic with named slots, numbers finalized Task 5).

**Files:**
- Create: `scripts/phase10_probe.py`
- Test: `tests/test_phase10_probe.py` (budget arithmetic pure function)

**Acceptance Criteria:**
- [ ] `phase10.oi.probe.signed` recorded: wall seconds, peak RSS, n_days=365,
      obs framing note, host fingerprint (cpu count, MemAvailable).
- [ ] Budget arithmetic implemented as a pure function
      `trials_per_lane(t_trial_s, wall_budget_h, n_lanes) -> int` =
      `floor(wall_budget_h*3600 / (t_trial_s * n_lanes))`, unit-tested.
- [ ] c2 never imported (grep `their_eval|c2` over the new script → only the
      "never" comment).

**Verify:** `pixi run pytest tests/test_phase10_probe.py -v` → PASS;
`pixi run python scripts/phase10_probe.py --config signed` prints
`[probe] signed wall=<s> peak_rss=<MiB>` and writes the key.

**Steps:**

- [ ] **Step 1: Failing test for the budget function**

```python
# tests/test_phase10_probe.py
"""Bug caught: budget arithmetic drifting from the recorded formula."""
from scripts.phase10_probe import trials_per_lane

def test_trials_per_lane_floor() -> None:
    # 6 h budget, 20-min trial, 3 lanes -> floor(21600 / (1200*3)) = 6
    assert trials_per_lane(t_trial_s=1200.0, wall_budget_h=6.0, n_lanes=3) == 6

def test_trials_per_lane_never_negative() -> None:
    assert trials_per_lane(t_trial_s=1e9, wall_budget_h=1.0, n_lanes=3) == 0
```

- [ ] **Step 2: Run; confirm FAIL (module missing).**
      `pixi run pytest tests/test_phase10_probe.py -v` → ImportError.

- [ ] **Step 3: Write `scripts/phase10_probe.py`** — thin driver over
      `run_mean_var_maps` at `baseline_config()` + `baseline_kernel()`
      (train-only obs, the `generate_oi_maps.py` obs-loading pattern), timing
      via `time.monotonic()`, RSS via `resource.getrusage`, output to a temp
      dir (probe maps for the SIGNED side are the phase-9
      `oi_{mean,var}_maps.nc` regenerated — write to
      `data/.../phase10_probe_signed_{mean,var}.nc`, kept: they are the band
      source pair's side A). `--config {signed,paciorek}`; the paciorek branch
      raises SystemExit("paciorek path lands Task 4") until then. Atomic
      evidence write to `phase10.oi.probe.<config>` (reuse the
      `phase9_fit_run.py` nested-key writer pattern).

```python
def trials_per_lane(t_trial_s: float, wall_budget_h: float, n_lanes: int) -> int:
    """Trials per lane from measured trial cost (spec §4 budget arithmetic)."""
    if t_trial_s <= 0:
        raise ValueError("t_trial_s must be positive")
    return max(0, int(wall_budget_h * 3600.0 // (t_trial_s * n_lanes)))
```

- [ ] **Step 4: Tests pass; run the signed probe (full year, detached,
      controller-owned per the standing background-job discipline:
      `nohup ... > log 2>&1 &` + `scripts/watch_pid.sh`).**

- [ ] **Step 5: Record evidence, commit, push.**
      `git commit -m "feat(phase10): Task 0 — signed-config runtime probe + budget arithmetic"`

---

### Task 1: Registry role-split + miost SHIPPED migration

**Goal:** `SHIPPED` table lands; `"miost"` migrates out of `METHODS`; caveat
comment retired; consumers migrated; disjointness + absence tests green.

**Files:**
- Modify: `src/sverdrup/methods/registry.py`
- Modify: `scripts/diag_miost_ndir12.py` (the METHODS["miost"] mutation)
- Modify: every shipped-side consumer found by the census step
- Create: `tests/test_registry_roles.py`

**Acceptance Criteria:**
- [ ] `SHIPPED = {"miost": shipped_miost}`; `"miost"` ABSENT from `METHODS`;
      `"miost-point"` remains; caveat comment deleted.
- [ ] Census executed and recorded in the commit message:
      `rg -n 'METHODS\[|method_name="miost"|method_name=.miost.' src scripts tests`
      + README grep; every shipped-side hit migrated to `SHIPPED` lookups; the
      8 bare-method test files + tuning paths untouched.
- [ ] Tests: `set(METHODS) & set(SHIPPED) == set()`; `"miost" not in METHODS`;
      `SHIPPED["miost"] is shipped_miost`.
- [ ] Full suite green (product identical — factory moved tables, not
      semantics; external sweep NOT required, rationale recorded: no
      shipped-product semantics change).

**Verify:** `pixi run pytest tests/test_registry_roles.py -v` → 3 PASS;
`pixi run test` green.

**Steps:**

- [ ] **Step 1: Failing tests**

```python
# tests/test_registry_roles.py
"""Bugs caught: double registration; miost left in METHODS; SHIPPED drift."""
from sverdrup.methods.miost import shipped_miost
from sverdrup.methods.registry import METHODS, SHIPPED

def test_tables_disjoint() -> None:
    assert set(METHODS) & set(SHIPPED) == set()

def test_miost_migrated() -> None:
    assert "miost" not in METHODS
    assert SHIPPED["miost"] is shipped_miost

def test_search_entry_remains() -> None:
    assert "miost-point" in METHODS
```

- [ ] **Step 2: FAIL (no SHIPPED).** **Step 3: Edit registry.py** (SHIPPED
      table + docstring stating the one-table/no-fallback rule verbatim from
      spec §8). **Step 4: Census + migrate consumers** — expected hits:
      `diag_miost_ndir12.py:88/98` (mutate/restore `SHIPPED["miost"]`
      instead), gate-runner scripts invoking `run_challenge_map`/scorers with
      `method_name="miost"` (these call paths resolve via `METHODS` inside
      `run.py:148/220`, `solve.py:43`, `scorer.py:127`, `stage_a.py:76` — for
      the shipped product, the CALLER passes the factory product; add a
      `shipped: bool = False` escape ONLY if a census hit genuinely needs the
      registry to resolve the shipped miost through those functions; prefer
      migrating the call site). README examples. **Step 5: Suite + dual
      review + commit + push.**

---

### Task 2: `LatitudeField` + `LatitudeVaryingProvider` superseded in place

**Goal:** The invariant-12 provider vehicle made real: typed field values,
named forms, exp links, params_key serialization; the three consumer test
files migrated.

**Files:**
- Modify: `src/sverdrup/core/parameters.py`
- Create: `tests/test_phase10_provider.py`
- Modify: `tests/test_latitude_varying_provider.py`,
  `tests/test_tiling_partition.py`, `tests/test_tiling_coordinator.py`

**Acceptance Criteria:**
- [ ] `LatitudeField(form, coeffs)` frozen dataclass: `.at(lat: ndarray) ->
      ndarray`, `.key() -> str`; forms `"exp-quad"` (exp(c0+c1·v+c2·v²)) and
      `"exp-linear-mult"` (exp(l1·v), multiplier); v = (lat−38)/5 clamped to
      the box hull (constant continuation — the PolyCalibration convention).
- [ ] `LatitudeVaryingProvider(core: dict[str, float], varied: dict[str,
      LatitudeField])` — `resolve` returns float for core names,
      `LatitudeField` for varied; `params_key` serializes form + coeffs
      (repr-stable, order-independent).
- [ ] Constant limit: `LatitudeField("exp-quad", (c0, 0, 0)).at(lat)` ==
      `exp(c0)` exactly, all lats.
- [ ] The three legacy test files migrated (cos-blend assertions replaced by
      named-form assertions; tiling tests just need a provider — construct
      with empty `varied`).

**Verify:** `pixi run pytest tests/test_phase10_provider.py tests/test_latitude_varying_provider.py tests/test_tiling_partition.py tests/test_tiling_coordinator.py -v` → PASS.

**Steps:**

- [ ] **Step 1: Failing tests**

```python
# tests/test_phase10_provider.py
"""Bugs caught: wrong v normalization; link applied twice; params_key collisions."""
import numpy as np
from sverdrup.core.parameters import LatitudeField, LatitudeVaryingProvider

def test_exp_quad_hand_computed() -> None:
    f = LatitudeField("exp-quad", (0.1, 0.5, -0.3))
    lat = np.array([33.0, 38.0, 43.0])  # v = -1, 0, +1
    expected = np.exp(np.array([0.1 - 0.5 - 0.3, 0.1, 0.1 + 0.5 - 0.3]))
    np.testing.assert_allclose(f.at(lat), expected, rtol=1e-15)

def test_exp_linear_mult_hand_computed() -> None:
    f = LatitudeField("exp-linear-mult", (-0.2,))
    np.testing.assert_allclose(
        f.at(np.array([33.0, 43.0])), np.exp(np.array([0.2, -0.2])), rtol=1e-15
    )

def test_constant_limit_exact() -> None:
    f = LatitudeField("exp-quad", (0.7, 0.0, 0.0))
    lat = np.linspace(33, 43, 51)
    assert np.all(f.at(lat) == np.exp(0.7))

def test_hull_clamp_constant_continuation() -> None:
    f = LatitudeField("exp-quad", (0.0, 1.0, 0.0))
    assert f.at(np.array([20.0]))[0] == f.at(np.array([33.0]))[0]

def test_resolve_types_and_key() -> None:
    p = LatitudeVaryingProvider(
        core={"time_scale": 7.0},
        varied={"variance": LatitudeField("exp-quad", (0.0, 0.1, 0.2))},
    )
    assert p.resolve("time_scale", None) == 7.0
    assert isinstance(p.resolve("variance", None), LatitudeField)
    q = LatitudeVaryingProvider(
        core={"time_scale": 7.0},
        varied={"variance": LatitudeField("exp-quad", (0.0, 0.1, 0.3))},
    )
    assert p.params_key() != q.params_key()
```

(`resolve(name, grid)` keeps the Protocol signature; grid unused by this
provider — latitudes come from the field consumer. Pass `None` in unit tests.)

- [ ] **Step 2: FAIL.** **Step 3: Implement** —

```python
_V_CENTER, _V_SCALE = 38.0, 5.0
_LAT_HULL = (33.0, 43.0)

@dataclass(frozen=True)
class LatitudeField:
    """Named low-dof latitude form (invariant-12 vehicle; spec §2)."""

    form: str  # "exp-quad" | "exp-linear-mult"
    coeffs: tuple[float, ...]

    def at(self, lat: np.ndarray) -> np.ndarray:
        v = (np.clip(np.asarray(lat, float), *_LAT_HULL) - _V_CENTER) / _V_SCALE
        if self.form == "exp-quad":
            c0, c1, c2 = self.coeffs
            return np.asarray(np.exp(c0 + c1 * v + c2 * v**2))
        if self.form == "exp-linear-mult":
            (l1,) = self.coeffs
            return np.asarray(np.exp(l1 * v))
        raise ValueError(f"unknown form {self.form!r}")

    def key(self) -> str:
        return f"{self.form}({','.join(repr(c) for c in self.coeffs)})"
```

Provider: frozen dataclass, `resolve` per AC, `params_key` =
`"latvary[" + ";".join(sorted core reprs + sorted varied keys) + "]"`.
Docstring carries the archaeology sentence (spec §2, batch-1 fold 1).

- [ ] **Step 4: Migrate the three legacy test files** (replace cos-blend
      construction; assert new forms; keep the tiling tests' provider role).
      **Step 5: Suite + reviews + commit + push.**

---

### Task 3: OI dispatch seam (byte-identical baseline gate)

**Goal:** Type-dispatching Gaussian-degrees kernel factory in `validation/`
consumed at solve entry; ConstantProvider path proven byte-identical.

**Files:**
- Modify: `src/sverdrup/validation/run.py` (factory + `run_mean_var_maps`
  wiring), `src/sverdrup/validation/params.py` (param-name doc note only)
- Create: `tests/test_oi_dispatch.py`

**Acceptance Criteria:**
- [ ] `gaussian_kernel_from_params(params, grid) -> Kernel` in
      `validation/run.py`: resolves `variance`, `lx_deg` (shared ly), and
      `time_scale`; ALL floats → `GaussianSpaceTimeDegrees` (the stationary
      class, same instance semantics as `baseline_kernel()` at the signed
      values); ANY `LatitudeField` → `PaciorekGaussianDegrees` (Task 4;
      until then the branch raises `NotImplementedError` — test marks the
      contract).
- [ ] Byte-identity: signed values through the factory produce a kernel whose
      `evaluate` returns bit-identical arrays vs `baseline_kernel()` on a
      pinned point set, AND a 3-day dev-scope `run_mean_var_maps` through the
      factory path is bit-identical to the `kernel=baseline_kernel()` path.
- [ ] `run_mean_var_maps`/`run_challenge_map` gain
      `oi_gaussian_kernel_from_params: bool = False` (parallel to the existing
      Matérn flag; default False — every existing caller unchanged).

**Verify:** `pixi run pytest tests/test_oi_dispatch.py -v` → PASS;
`pixi run test` green (no existing test touched).

**Steps:**

- [ ] **Step 1: Failing tests**

```python
# tests/test_oi_dispatch.py
"""Bugs caught: factory drifts from baseline_kernel; field silently coerced to float."""
import numpy as np
import pytest
from sverdrup.core.parameters import ConstantProvider, LatitudeField, LatitudeVaryingProvider
from sverdrup.validation.params import baseline_kernel
from sverdrup.validation.run import gaussian_kernel_from_params

def _pts() -> np.ndarray:
    rng = np.random.default_rng(7)
    lon = 295 + 10 * rng.random(40); lat = 33 + 10 * rng.random(40)
    t = 30 * rng.random(40)
    return np.column_stack([lon, lat, t])

def test_scalar_path_bit_identical_to_baseline() -> None:
    p = ConstantProvider({"variance": 1.0, "lx_deg": 1.0, "time_scale": 7.0})
    k = gaussian_kernel_from_params(p, None)
    a = _pts(); b = _pts()[:17]
    assert np.array_equal(k.evaluate(a, b), baseline_kernel().evaluate(a, b))

def test_field_path_routes_nonstationary() -> None:
    p = LatitudeVaryingProvider(
        core={"variance": 1.0, "time_scale": 7.0},
        varied={"lx_deg": LatitudeField("exp-linear-mult", (-0.2,))},
    )
    with pytest.raises(NotImplementedError):  # replaced by type check in Task 4
        gaussian_kernel_from_params(p, None)
```

- [ ] **Step 2: FAIL.** **Step 3: Implement the factory** (isinstance
      dispatch; the scalar branch constructs
      `GaussianSpaceTimeDegrees(variance=v, lx_deg=lx, ly_deg=lx,
      time_scale=lt)`; shared lx=ly per spec §2). Wire the boolean into
      `run_mean_var_maps` beside the Matérn flag. **Step 4: PASS; 3-day
      dev-scope map bit-comparison (in-test, tiny grid fixture per the
      existing run.py test patterns).** **Step 5: Suite + reviews + commit +
      push.**

---

### Task 4: `PaciorekGaussianDegrees` + PD/reduction/prior-diag tests

**Goal:** The PD-safe nonstationary kernel; the load-bearing math proven.
Green here UNBLOCKS stage-2 tasks (enforced by task dependency).

**Files:**
- Modify: `src/sverdrup/methods/kernel.py`
- Modify: `src/sverdrup/validation/run.py` (factory field branch)
- Create: `tests/test_paciorek_kernel.py`

**Acceptance Criteria:**
- [ ] `PaciorekGaussianDegrees(variance_field, lx_deg_base, l_mult_field,
      time_scale)` implements the Kernel Protocol; closed form per spec §3:
      per pair, `L(x) = lx_deg_base·m(lat_x)`, `L̄² = (L(x)²+L(y)²)/2`,
      spatial factor = `[L(x)·L(y)/L̄²] · exp(−Δlon²/L̄² − Δlat²/L̄²)`,
      times stationary `exp(−Δt²/Lt²)`, times `σ(x)·σ(y)` outer scaling
      (σ² = variance field; σ ≥ 0 by exp link). Scalar σ / unit multiplier
      accepted (constant limits).
- [ ] PD test at pinned geometry (spec §3): points = 20 at lat 33.0–33.4 +
      20 at lat 42.6–43.0 (max-L-contrast) + 40 dense mid-box cluster around
      (300, 38) ± 0.3°, times ∈ {0, 3, 7} d; strongly varying fields
      (c=(0.5, 1.0, −1.0), l1 = −0.5); assert
      `min(eigvalsh(K)) >= -1e-10 * norm(K, 2)`.
- [ ] Constant-reduction identity vs the SHIPPED `baseline_kernel()` at
      c1=c2=l1=0, c0=0, L0=1.0, Lt=7.0: `np.array_equal` if achievable, else
      `rtol=1e-15` — full space-time kernel (spec §3 pin 3).
- [ ] Pointwise prior variance: `prior_var_at(pts) == variance_field(lat)`
      exactly (prefactor 1 at x=y), cross-checked vs `np.diag(evaluate(a,a))`
      brute force at rtol 1e-14. `_stationary()` (oi.py:84-86) returns False
      for the class (marginal_var routes the diag branch; test asserts).
- [ ] Factory field branch (Task 3's NotImplementedError) replaced; routing
      test updated.

**Verify:** `pixi run pytest tests/test_paciorek_kernel.py tests/test_oi_dispatch.py -v` → PASS.

**Steps:**

- [ ] **Step 1: Failing tests** (PD, reduction, prior-diag, routing — each
      test docstring names its bug: "naive L(x) substitution is not PD";
      "prefactor/exponent convention mismatch vs shipped kernel"; "diag path
      O(n²) or wrong at clip boundary"; "factory still raises").

```python
# tests/test_paciorek_kernel.py (core assertions; full file per AC)
def test_pd_at_pinned_geometry() -> None:
    k = _paciorek(c=(0.5, 1.0, -1.0), l1=-0.5)
    pts = _pinned_geometry()  # spec §3 geometry, exactly as in AC
    K = k.evaluate(pts, pts)
    w = np.linalg.eigvalsh(0.5 * (K + K.T))
    assert w.min() >= -1e-10 * np.linalg.norm(K, 2)

def test_constant_reduction_identity_full_spacetime() -> None:
    k = _paciorek(c=(0.0, 0.0, 0.0), l1=0.0)  # exact constant limit
    a, b = _pts(), _pts()[:23]
    ref = baseline_kernel().evaluate(a, b)
    got = k.evaluate(a, b)
    assert np.array_equal(got, ref) or np.allclose(got, ref, rtol=1e-15, atol=0)
```

- [ ] **Step 2: FAIL.** **Step 3: Implement** — broadcast implementation
      mirroring `GaussianSpaceTimeDegrees.evaluate` (absolute columns), with
      `Lx = base * mult.at(a[:, 1])[:, None]`, `Ly = base *
      mult.at(b[:, 1])[None, :]`, `L2 = 0.5 * (Lx**2 + Ly**2)`, prefactor
      `Lx * Ly / L2`, exponent `-(dlon**2 + dlat**2) / L2 - dt**2 / lt**2`,
      outer `sig_a[:, None] * sig_b[None, :]`. `prior_var_at(pts)` returns
      `variance_field.at(pts[:, 1])` (scalar → full). Guard: if the constant
      limit cannot reach bit-identity because of the prefactor float path,
      short-circuit `l_mult_field is None or coeffs == (0.0,)` to the exact
      stationary arithmetic — the identity test decides whether the
      short-circuit is needed; if used, it is COMMENTED as the constant-limit
      exactness guarantee, and the PD/generic path is still exercised by the
      non-constant tests.
- [ ] **Step 4: PASS all.** **Step 5: Update factory branch + routing test.
      Suite + reviews + commit + push. Paciorek gate now GREEN — stage-2
      dependency satisfied.**

---

### Task 5: Pre-registration artifact — Paciorek probe + bands + day list + k + budget (ONE commit)

**Goal:** Everything the spec demands recorded BEFORE any trial: the Paciorek
probe measurement, finalized budget arithmetic, the screening day list + k,
and both bands (seeded, timestamped) from the probe pair.

**Files:**
- Create: `scripts/phase10_prereg.py`,
  `src/sverdrup/application/tuning/lane_compare.py` (band computation + schema
  + refusal clock), `tests/test_lane_compare.py`
- Modify: `scripts/phase10_probe.py` (paciorek branch live)

**Acceptance Criteria:**
- [ ] Paciorek probe: full-year `run_mean_var_maps` through the factory at the
      PINNED probe config (c=(0.0, 0.3, −0.6), l1=−0.25, L0=1.0, Lt=7.0 — a
      mid-box-bump + Rossby-sign point at roughly half the box excursions;
      recorded as the probe config, no tuning meaning) →
      `phase10.oi.probe.paciorek` (wall, RSS) + maps kept as band side B.
- [ ] `phase10.oi.probe.budget`: `t_trial` = measured (or subset-scaled),
      `wall_budget_h` (owner-supplied at execution; the evidence block records
      the number + who set it), `n_sobol_per_lane = trials_per_lane(...)`,
      minimum floor: if `n_sobol_per_lane < 8` → screening contingency ACTIVE.
- [ ] Contingency constants (ONE artifact with the bands, spec §4):
      `screening_days` = every 4th day of 2017 starting day 1 (91 days,
      stratified across the year, pinned list serialized) and `k = 3`
      (full-year re-scores per lane). Recorded whether ACTIVE or NOT.
- [ ] Band artifact `phase10_band_artifact.json` (schema pinned):

```json
{
  "created_utc": "<ISO8601, written by the script>",
  "resample_seed": 271828,
  "block_unit": "contiguous day/pass segments",
  "n_resamples": 2000,
  "source_pair": {"a": "<sha256 signed probe mean nc>", "b": "<sha256 paciorek probe mean nc>"},
  "band_mu": 0.0,
  "se_mu": 0.0,
  "band_lambda_x": 0.0,
  "se_lambda_x": 0.0,
  "lambda_informative": true
}
```

      `band_mu = 2*se_mu` from block resampling of per-point squared-error
      differences between the two probe products on the validation track
      (blocks = contiguous day/pass segments per the existing rho/n_eff
      machinery); `band_lambda_x = 2*se_lambda_x` of the SNR-crossing estimate
      over the same resamples; `lambda_informative` set by the pre-registered
      rule `band_lambda_x < 0.5 * |lambda_x_a - lambda_x_b|_probe` is NOT the
      rule — the rule is: informative iff `band_lambda_x <= 25 km` (2×SE at or
      under the λx grid resolution scale; recorded rationale: coarser than
      that cannot separate physically plausible gains).
- [ ] `lane_compare.compute_bands(errs_a, errs_b, meta) -> BandArtifact`
      deterministic under the recorded seed (reproducibility test).
- [ ] Refusal clock implemented: `assert_band_predates(band, records)`
      compares `created_utc` INSIDE artifacts, never mtimes (spec §9,
      batch-3 fold 3); unit test: winner record with earlier internal
      timestamp → `PreRegistrationError`.
- [ ] All of the above lands in ONE commit (batch-2 fold 3).

**Verify:** `pixi run pytest tests/test_lane_compare.py -v` → PASS (incl.
band determinism + refusal tests); `phase10_band_artifact.json` +
`phase10.oi.probe.{paciorek,budget}` + contingency block present.

**Steps:**

- [ ] **Step 1: Failing tests** for `compute_bands` (seeded determinism: two
      calls same seed → identical artifact dict; different seed → different
      resample draws), `assert_band_predates` (both orders), schema
      round-trip.
- [ ] **Step 2: FAIL.** **Step 3: Implement `lane_compare.py`** — block
      bootstrap: segment per (day, pass) contiguity (reuse
      `application/calibration/folds` rho machinery for the segment
      boundaries); Δµ per resample from resampled per-point squared-error
      differences; λx per resample via the existing SNR-crossing estimator in
      the scorer path (import the vendored `interp_on_alongtrack` outputs the
      scorer already produces — the band script consumes the probe products'
      per-point along-track arrays persisted by `phase10_probe.py`).
- [ ] **Step 4: PASS.** **Step 5: Run the Paciorek probe (detached +
      watcher); run `phase10_prereg.py`; ONE commit; push.**

---

### Task 6: Lane machinery — restrictions, paired seeds, anchors, bars, selection layer

**Goal:** Everything between "boxes" and "verdict" implemented + unit-tested;
no tuner-core edits.

**Files:**
- Create: `src/sverdrup/validation/phase10_lanes.py`,
  `tests/test_phase10_lanes.py`
- Modify: `src/sverdrup/application/tuning/lane_compare.py` (selection layer +
  verdict), `tests/test_lane_compare.py`

**Acceptance Criteria:**
- [ ] Boxes (spec §2 principles → endpoints, rationale strings recorded in
      code next to each):
      `c0 ∈ [−1.5, 1.5]` (brackets 0 ↔ variance 1.0; covers the measured
      log-s span 1.93), `c1 ∈ [−1.0, 1.0]`, `c2 ∈ [−1.5, 1.5]` (max swing
      |c1|+|c2| ≤ 2.5 log units over v∈[−1,1], bounded and recorded vs the
      [−1.5414, 0.3928] artifact span), `log_L0 ∈ [ln 0.5, ln 2.0]` (brackets
      1.0°), `l1 ∈ [−0.5, +0.3]` (includes 0 + both signs; asymmetric toward
      the Rossby sign, swing e^{2·l1} ∈ [0.37, 1.82]), `Lt ∈ [3.0, 14.0]`
      (brackets 7 d).
- [ ] `LANES = {"lane0": frozenset(), "V": {"c1","c2"}, "VL": {"c1","c2","l1"}}`
      — released names; every lane's ParameterSpace = core ∪ released; frozen
      coords pinned AT 0.0 in trial dicts (restriction bookkeeping test).
- [ ] `provider_for_trial(trial: dict[str, float]) -> LatitudeVaryingProvider`
      + kernel factory glue: c-coeffs → variance field; l1 → multiplier;
      all-zero released → ConstantProvider-equivalent scalars (dispatch test:
      lane-0 trials route the STATIONARY class).
- [ ] Paired Sobol: per-lane engine seeded from
      `derive_seed("oi", "phase10-lanes", lane_name, 0)`; SHARED-dim draws:
      the sequence is drawn in the FULL 6-dim unit cube with ONE engine seed
      common to all lanes (`derive_seed("oi", "phase10-lanes", "sobol", 0)`),
      each lane MASKS its frozen dims to the restriction value — same trial
      index → identical shared-dim draws across lanes, differing only on
      released coords (batch-3 fold 2a test).
- [ ] Anchor embedding: `anchors_for(lane, winners) -> list[dict]` — lane-0
      winner into V and VL (released at 0), V winner into VL (l1=0);
      pre-registered, tested.
- [ ] Bars: `bars_for(UncertaintyCapability.SAMPLES)` wired into the lane
      run config (µ floor + coverage); coverage convention = raw posterior
      variance + SIGMA_OBS2 (one convention with acceptance at s≡1); the
      ≈0.78 expectation recorded as a comment beside the bar wiring
      (ŝ_OI=0.6621 → raw coverage at the band top edge; bar LIVE, trips =
      design working).
- [ ] Selection layer in `lane_compare.py`:
      `select_lane_winner(records, band) -> record` — lexicographic (µ then
      λx per the §5 rule) over bar-passing validation records; degradation
      branch (band.lambda_informative False → µ-primary + recorded note);
      refusal clock called FIRST.
      `primary_verdict(w_vl, w_lane0, band) -> Verdict` — beats/tie per §5;
      wording pin enforced in the Verdict text ("improvements within band",
      never "worse").
- [ ] Trial scoring: `ValidationTrackScorer` reused as-is with
      `oi_gaussian_kernel_from_params=True` maps production (scorer's
      `_produce_maps` gains the flag pass-through — the ONLY tuner-adjacent
      edit, additive, default False).

**Verify:** `pixi run pytest tests/test_phase10_lanes.py tests/test_lane_compare.py -v` → PASS; `pixi run test` green.

**Steps:**

- [ ] **Step 1: Failing tests** — restriction bookkeeping (lane-0 trial dict
      has c1=c2=l1=0.0 exactly); paired-seed identity (same index, shared dims
      equal across lanes); anchor presence; lexicographic winner (crafted
      records: µ-clear win; µ-tie λx win; both-tie); degradation branch;
      dispatch routing (lane-0 → stationary class).
- [ ] **Step 2: FAIL.** **Step 3: Implement.** **Step 4: PASS.**
      **Step 5: Suite + reviews + commit + push.**

---

### Task 7: Stage-1 execution — lane-0 + V runs, winners, stage-1 flattening reading

**Goal:** Machinery proven on real runs; the V-vs-s(x) adjudication measured.

**Files:**
- Create: `scripts/phase10_lane_run.py`, `scripts/phase10_flatten_read.py`
- Modify: PROGRESS.md (stage-1 close block)

**Acceptance Criteria:**
- [ ] `phase10_lane_run.py --lane {lane0,V,VL}`: Sobol trials per the recorded
      budget (screening subset if ACTIVE), bars enforced, records appended
      under `phase10.oi.lanes.<lane>` (each record carries `created_utc`,
      trial dict, scores, bar outcomes, admissibility); anchors evaluated;
      dev smoke (`SVERDRUP_PHASE10_SCOPE=dev`, 12-day) run FIRST both lanes.
- [ ] Winners selected via `select_lane_winner` (band artifact refusal clock
      passes by construction — bands predate all records); stage-1 SECONDARY
      row V-vs-lane0 computed + recorded (attribution, never claim-bearing).
- [ ] `phase10_flatten_read.py`: (a) recomputes **G_pre_oi** canonically from
      `phase9.oi.fit_run` via the §7 definition → `phase10.g_pre_oi_anchor`
      (expected 0.27086964275496783; assert match to 1e-12, STOP otherwise);
      pre-B companions (std log s, range, clip engagement from
      `phase9_field_oi.json`) recorded beside it; (b) G_post reading for a
      given product's maps under the FROZEN pre-B OI frame: asserts mask
      sha256 == `0deefcb961a3092279ca5de30852d65fffcbade304b19de0cb9e6a5d35ef0058`,
      fold tuple ("oi","phase9","s-folds"), expects s_salt 4 with redraws
      [0,1,2,3] (records any difference), covariate proxy from the product's
      own means → `phase10.oi.flattening_stage1` for the V winner's re-solved
      maps.
- [ ] Stage-1 close block in PROGRESS states WHICH outcome occurred
      (structure moved into the prior vs product materially improved) — the
      fork-a mod-1 sentence, with G_pre_oi vs stage-1 G_post + the secondary
      row numbers.
- [ ] c2 untouched (grep gate in both scripts' review).

**Verify:** dev smoke both lanes → records present, winner selected; full runs
detached + watcher; `phase10.oi.flattening_stage1` + `phase10.g_pre_oi_anchor`
written; PROGRESS committed.

**Steps:**

- [ ] **Step 1:** `phase10_lane_run.py` — glue over `tune()` +
      `ValidationTrackScorer` + `phase10_lanes` (lane space, provider glue,
      anchors, bars); the loop's TrialScorer seam unchanged. Unit test only
      the record-shape pure function (execution scripts follow the
      phase9_fit_run.py dev/full discipline).
- [ ] **Step 2:** `phase10_flatten_read.py` — reuses the harness with a
      FROZEN-FRAME descriptor (evidence key `phase10.oi.flattening_stage1`,
      mask = the phase-9 OI mask artifact, fold tuple ("oi","phase9",
      "s-folds")) — never the acceptance descriptor (two-runs-never-conflated
      test from Task 10 covers both directions).
- [ ] **Step 3:** dev smokes → full runs (detached, controller-owned,
      watcher). **Step 4:** V-winner re-solve full-year maps (the reading
      needs product maps; run via `run_mean_var_maps` with the factory) →
      reading → evidence. **Step 5:** PROGRESS stage-1 close + reviews +
      commit + push.

---

### Task 8: Stage-2 execution — VL-joint (+ conditional L-only) + PRIMARY comparison

**Goal:** The claim-bearing measurement.

**Files:**
- Create: `scripts/phase10_compare.py`
- Modify: PROGRESS.md (verdict block)

**Acceptance Criteria:**
- [ ] VL lane run (warm-start anchors: stage-1 V winner + l1=0, lane-0
      winner); L-only lane iff the probe's budget block shows
      `n_sobol_per_lane ≥ 8` at four lanes (recorded either way with the
      probe number as the reason).
- [ ] `phase10_compare.py`: refusal clock → per-lane winners → **PRIMARY
      verdict = VL winner vs lane-0 winner** under the §5 rule; secondary
      rows (V vs lane-0, L-only if run); full verdict block at
      `phase10.oi.lanes.verdict` (bands quoted, deltas, rule branch taken,
      wording pin respected).
- [ ] BRANCH RECORDED: verdict POSITIVE → Tasks 10–15 proceed; NEGATIVE →
      Task 9 executes, Tasks 10–15 close as superseded (the Phase-8 Task-13
      branch-semantics precedent).
- [ ] PROGRESS verdict block committed.

**Verify:** `phase10.oi.lanes.verdict` present with the PRIMARY row; PROGRESS
updated; suite green.

**Steps:** dev smoke VL → full VL run (detached + watcher) → conditional
L-only decision from the recorded budget → `phase10_compare.py` → PROGRESS →
reviews → commit → push.

---

### Task 9: NEGATIVE-RESULT branch close (only if verdict negative)

**Goal:** The pre-registered honest outcome, closed cleanly.

**Files:** Modify: PROGRESS.md

**Acceptance Criteria:**
- [ ] Record in PROGRESS + evidence: "improvements within band" wording; NO c2
      touch spent (tally untouched); stage readings + verdict cross-linked.
- [ ] Tuned-constant election flagged as a SEPARATE owner item (lane-0 winner
      numbers quoted; no recommendation).
- [ ] Tasks 10–15 closed as superseded in the tracker; phase close banner;
      push.

**Verify:** PROGRESS close block; `git log` shows the close commit pushed.

---

### Task 10: Winner re-solve → maps + content hashes → mask → acceptance fit → stage-2 reading

**Goal:** The B-product's evidence chain, new frame, plus the frozen-frame
stage-2 reading. (Positive branch.)

**Files:**
- Create: `scripts/phase10_acceptance.py`, `tests/test_phase10_tripwires.py`
  (descriptor-separation tests)
- Modify: PROGRESS.md

**Acceptance Criteria:**
- [ ] Winner config re-solved: full-year `phase10_oi_{mean,var}_maps.nc` with
      provenance attrs (params_key incl. named forms + coefficients);
      **sha256 of both files recorded at `phase10.oi.maps_sha256`** (the
      determinism tripwire's reference).
- [ ] NEW mask from the winner means (pre-registered rule verbatim:
      75th-percentile temporal std → largest 4-connected component) →
      `phase10_jet_core_mask_oi.json` committed with provenance;
      `jet_core_ref_p8` + Jaccard vs p8 AND vs the phase-9 OI mask
      (0deefcb9…) recorded.
- [ ] Acceptance fit via the harness, NEW descriptor:
      `product_id="oi-p10"`, evidence key `phase10.oi.fit_run`,
      `fold_seed_tuple=("oi", "phase10", "s-folds")`, mask/field artifacts
      `phase10_*`; ordering pinned (means → mask committed → fit).
- [ ] Stage-2 flattening reading → `phase10.oi.flattening_stage2` (frozen
      frame, same assertions as stage 1).
- [ ] Two-runs-never-conflated tests: acceptance descriptor vs frozen-frame
      descriptor differ in evidence key, seed tuple, mask path, field path;
      frozen-frame runner REFUSES a descriptor whose mask sha ≠ 0deefcb9…;
      acceptance runner REFUSES the phase-9 mask path.
- [ ] c2 untouched.

**Verify:** `pixi run pytest tests/test_phase10_tripwires.py -v` → descriptor
tests PASS; evidence keys + artifacts present; PROGRESS updated; push.

---

### Task 11: OWNER GATE 1 — j3-evidence review

**Goal:** Owner reads the complete j3-side evidence and rules
PROCEED / NEGATIVE-CLOSE / REWORK.

**USER-ORDERED GATE — NON-SKIPPABLE.** This task was requested by the user in
the current conversation. It MUST NOT be closed by walking around it, by
declaring it "verified inline", or by substituting a cheaper check. Close only
after every item in acceptance criteria has been re-validated independently,
with output captured.

**Files:** none (evidence assembly + STOP).

**Acceptance Criteria:**
- [ ] Evidence pack presented verbatim from artifacts: `phase10.oi.lanes.verdict`
      (PRIMARY + secondary rows + bands), `phase10.oi.fit_run` (bars, tables,
      Jaccard rows), `phase10.oi.flattening_stage1/2` vs
      `phase10.g_pre_oi_anchor` (G shrinkage + companions incl.
      clip-engagement), maps hashes.
- [ ] Owner ruling recorded in PROGRESS verbatim-intent; PROCEED does NOT
      pre-authorize the touch (gate 2 = fresh authorization).

**Verify:** owner ruling text in PROGRESS, committed + pushed. Evidence axes:
both comparison sides (lane-0/tuned-constant AND vl/lat-varying) and both
instrument sides (g-pre AND g-post) must appear in the close evidence.

---

### Task 12: c2 touch runner (built + tested BEFORE gate 2; c2 never read)

**Goal:** `scripts/phase10_c2_touch.py` with both tripwires + touch mechanics;
tested entirely on fixtures.

**Files:**
- Create: `scripts/phase10_c2_touch.py`
- Modify: `tests/test_phase10_tripwires.py`

**Acceptance Criteria:**
- [ ] DETERMINISM TRIPWIRE: at entry, sha256 of the persisted
      `phase10_oi_{mean,var}_maps.nc` asserted == `phase10.oi.maps_sha256`
      (the gate-1-reviewed hashes); mismatch → defect-STOP exit nonzero,
      NOTHING written. NEVER re-solves (no method import in the script).
- [ ] WINDOW TRIPWIRE: ONE loader feeds the triplet block AND the calibration
      block; n_points + date-span asserted equal between blocks + spanning
      2017; n_points == 44,844 asserted (recorded count).
- [ ] Reading (pre-registered, §6): acceptance = the NEW (µ, σ, λx) recorded;
      aggregate c2 coverage at s(x)·v + SIGMA_OBS2 ∈ 0.6827±0.10 → SIGN-OFF;
      outside → HOLD, record, no refit. Regional + chi2_red + CRPS
      report-only.
- [ ] TOUCH MECHANICS: writes `phase10.oi.c2_acceptance` once; corrected run
      requires `SVERDRUP_PHASE10_CORRECTED_TOUCH=1`, valid only while a dated
      defect key exists and acceptance absent; third invocation refuses.
- [ ] Tests prove: hash-mismatch → SystemExit ≠ 0 before any scoring;
      two-loaders defect class impossible (single loader object identity);
      refusal ladder (fixture JSON states). ALL against synthetic fixtures —
      the test suite NEVER touches c2 data.

**Verify:** `pixi run pytest tests/test_phase10_tripwires.py -v` → PASS;
`rg -n "their_eval|c2" scripts/phase10_c2_touch.py` shows imports guarded to
the touch entrypoint only.

---

### Task 13: OWNER GATE 2 — fresh-auth SINGLE c2 touch

**Goal:** The one touch, mechanically read.

**USER-ORDERED GATE — NON-SKIPPABLE.** This task was requested by the user in
the current conversation. It MUST NOT be closed by walking around it, by
declaring it "verified inline", or by substituting a cheaper check. Close only
after every item in acceptance criteria has been re-validated independently,
with output captured.

**Files:** none (authorized invocation + record).

**Acceptance Criteria:**
- [ ] Fresh owner authorization quoted at request time (reading verbatim from
      Task 12's pre-registration); no standing pre-authorization.
- [ ] ONE invocation of `phase10_c2_touch.py`; tripwires both PASSED in the
      output; verdict per the pre-registered reading; honest per-product
      tally recorded (this product: touch 1).
- [ ] Outcome recorded in PROGRESS (SIGN-OFF → Task 14; HOLD → STOP, owner).

**Verify:** `phase10.oi.c2_acceptance` present with tripwire fields green;
PROGRESS updated + pushed. Evidence axes: persisted-map hashes (pre-touch)
AND c2 verdict fields (post-touch) both quoted in the close.

---

### Task 14: FLIP COMMIT — shipped_oi + SHIPPED update + σ-semantics + FULL external sweep

**Goal:** The flagship supersedes; the external-sweep standing rule's first
application.

**Files:**
- Modify: `src/sverdrup/methods/oi.py` (shipped_oi + ConfiguredOI),
  `src/sverdrup/methods/registry.py` (SHIPPED["oi"]), README.md
- Create: `tests/test_shipped_oi.py`

**Acceptance Criteria:**
- [ ] `ConfiguredOI` (frozen: provider, kernel factory config, calibration
      field) with `solve(obs, grid, time_days)` delegating to
      `OptimalInterpolation.solve(kernel=<factory>)` and wrapping in
      `CalibratedDistribution(dist, field)`; `shipped_oi() -> ConfiguredOI`
      builds it from the SIGNED phase-10 artifacts (winner coefficients +
      `phase10_field_oi.json`), constants asserted against
      `phase10.oi.fit_run` at construction.
- [ ] `SHIPPED["oi"] = shipped_oi`; disjointness test still green; the
      σ-semantics paragraph in the docstring — TEMPLATE (measured numbers
      filled from evidence at this commit): "Shipped σ = calibrated predictive
      uncertainty: a latitude-varying prior (variance(lat)=exp(c0+c1·v+c2·v²),
      L(lat)=L0·exp(l1·v); coefficients <from phase10.oi.fit_run>) plus a
      residual post-hoc calibration field s(x) fitted per Phase-9 (<field
      summary>). NOT raw posterior spread. Correlation structure preserved
      (outer √s scaling). Evidence: c2 coverage <value> ∈ 0.6827±0.10,
      (µ,σ,λx) = <triplet>; flattening G_pre 0.27086964 → G_post <value>,
      clip engagement <pre>→<post>. Two-layer story per spec §8."
- [ ] README updated (flagship product + baseline-faithful config's oracle
      role); honest touch tally in the commit message.
- [ ] **FULL EXTERNAL SWEEP** (`SVERDRUP_PHASE8_EXTERNAL=1` + all
      artifact-gated suites) run at the flip commit and GREEN — counts quoted
      in the commit message; externals are part of green (standing rule,
      first application, cited).
- [ ] Baseline oracle comparison test intact post-flip (the
      `baseline_config()` path unchanged, test still green).

**Verify:** `pixi run pytest tests/test_shipped_oi.py tests/test_registry_roles.py -v` → PASS; full suite + external sweep green; push.

---

### Task 15: Phase close — PROGRESS + push

**Goal:** Close banner with the full evidence trail.

**Files:** Modify: PROGRESS.md

**Acceptance Criteria:**
- [ ] Close banner: verdict + bands, acceptance triplet, coverage, G_pre→G_post
      + companions, touch tally, external sweep counts, deliverables list,
      MIOST-B next-decision pointer (owner item, with the
      representation-dominated note).
- [ ] Deferred-items hygiene: the invariant-12 deferral entry retired
      (migrated, not duplicated).
- [ ] Everything pushed; `git status` clean.

**Verify:** PROGRESS close block; `git log --oneline -5` shows the trail;
clean tree.

---

## Self-review record (writing-plans checklist)

**Spec coverage:** §0 scope/anchor guard → Tasks 7 (anchor STOP-assert), 12
(no-c2 grep gates), header discipline; §1 evidence/expectation → Task 7 close
wording + §4 bar expectation comment (Task 6); §2 provider/dispatch → Tasks
2–3; §3 kernel → Task 4; §4 tuning → Tasks 0, 5, 6, 7, 8; §5 comparison →
Tasks 5 (bands), 6 (selection layer), 8 (verdict); §6 pipeline/template →
Tasks 10, 12, 13; §7 instrument → Tasks 5 (n/a), 7, 10 (readings + anchor);
§8 ship → Tasks 1, 14; §9 tests → distributed, each named; §10 evidence keys →
Tasks 0, 5, 7, 8, 10, 12, 13; §11 out-of-scope → no task builds any of it;
§12/§13 → this plan's User-decisions header. Gaps: none found.
**Placeholder scan:** the σ-semantics paragraph and budget block contain
named slots filled from measured evidence at execution — explicitly marked as
such (measurement-dependent, not deferred design). No TBD/TODO remain.
**Type consistency:** `LatitudeField` (Tasks 2→3→4→6), `gaussian_kernel_from_params`
(3→4→6→7), `compute_bands`/`select_lane_winner`/`primary_verdict` (5→6→7→8),
`trials_per_lane` (0→5), descriptor fields match `ProductDescriptor`
(harness.py:65) — checked.
**Branch representability:** Task 9 vs Tasks 10–15 mutually exclusive;
tracker semantics = the Phase-8 Task-13 precedent (close-as-superseded).
