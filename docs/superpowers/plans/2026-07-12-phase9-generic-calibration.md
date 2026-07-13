# Phase 9 — Method-Generic Calibration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lift Phase 8's MIOST-internal s(x) calibration to a method-agnostic
`CalibratedDistribution` wrapper + generalized per-product fit harness; migrate
the shipped MIOST product identity-proven; demonstrate on OI j3-side; deliver
the Phase-10 interface contract (G_pre anchor). **ZERO c2 TOUCHES — phase
invariant; no task in this plan is capable of touching c2.**

**Architecture:** New `distributions/calibration.py` holds the moved
CalibrationField classes + the capability-aware wrapper (one general path,
pins A–E). `application/calibration/harness.py` runs the pre-registered fit
sequence over a ProductDescriptor. MIOST factory wraps instead of scaling
internally; identity suite is the migration gate.

**Tech Stack:** numpy, scipy, xarray, pytest; existing sverdrup modules
(distributions, application/calibration, validation).

**Spec (governs on conflict):**
`docs/superpowers/specs/2026-07-12-phase9-generic-calibration-design.md`

**User decisions (already made):**
- P9 = generic layer; P10 = lat-varying method params (owner-committed; §0).
- Wrapper = capability-aware, one general path, protocol-implementing (§2);
  pins A (no-raw-leak, enumerated surface, no `__getattr__`), B (explicit
  capability + required `grid`), C (cal_key byte-stability across the move),
  D (provenance single-append + sequence-equality test), E (op-reorder note:
  variance routes rtol 1e-12 by design, mean routes bit).
- MIOST migrates onto the wrapper THIS phase; identity suite = migration
  gate; no re-fit, no c2, no dual mechanisms (§3).
- Harness: ProductDescriptor with fold_seed_tuple field; MIOST descriptor
  carries the FROZEN Phase-8 tuple; leaf-identical regression with a PINNED
  key map (§4).
- Regions: per-product gate frame + `jet_core_ref_p8` report row + Jaccard
  drift (fork 1, spec §11.1).
- Flattening instrument: held-out selection gap G, pinned frame/folds,
  shrinkage vs G_pre anchor at `phase9.g_pre_anchor`, companions + demoted
  NLL gap (fork 2, spec §7c).
- OI demo: j3-only, signed-config-derived means (baseline_config, never
  re-tuned), wrapper-integration test, ŝ_OI≈1 = informative finding, no ship
  (§5, batch-2 items 1–4).
- Acceptance template with generalized one-loader window tripwire + standing
  touch mechanics recorded in spec §6 (batch-3 folds 1–2) — TEMPLATE ONLY,
  nothing executes it this phase.
- Plan-structure obligations 1–7 (owner, plan review request) — each is
  pinned in the tasks below and cross-referenced in the self-review.

---

## File structure

| File | Responsibility |
|---|---|
| `src/sverdrup/distributions/calibration.py` (create) | moved CalibrationField classes + ClipSpec + calibration_from_json + `CalibratedDistribution` wrapper |
| `src/sverdrup/distributions/miost_ensemble.py` (modify) | drop internal seam + calibration persistence (moves to wrapper); raw class keeps S-path internals |
| `src/sverdrup/methods/miost.py` (modify) | ensemble branch wraps; σ-semantics mechanism pointer |
| `src/sverdrup/application/calibration/harness.py` (create) | ProductDescriptor + generalized fit sequence (glue only) |
| `scripts/phase9_fit_run.py` (create) | thin CLI (dev/full) over harness |
| `scripts/build_jet_core_mask.py` (create, generalizes phase8 script) | per-product mask build (product paths as args); phase8 script retained |
| `scripts/phase9_g_pre_anchor.py` (create) | G_pre recomputation → `phase9.g_pre_anchor` |
| `scripts/generate_oi_maps.py` (create) | OI mean/var maps at signed config (run_mean_var_maps) |
| `tests/test_calibrated_distribution.py` (create) | wrapper unit tests (stub + MIOST fixture) |
| `tests/test_calibration_field.py`, `tests/test_phase8_identity_regression.py`, `tests/test_miost_ensemble.py`, `tests/test_miost_inflation.py`, `tests/test_phase8_gate_run.py` (modify imports only) | migration gate — assertions unchanged |
| `tests/test_calibration_harness.py` (create) | descriptor validation + harness regression |
| `PROGRESS.md` (modify, Tasks 6/8) | §0 deferred-to-P10 record; phase close |

Verified source facts used below: `GaussianPredictiveDistribution` attrs
`grid/mean/cov_op/provenance/time_days`, methods `marginal_variance:25,
covariance:30, sample:34, regrid:41`, NO mean_at/member_at/to_grid_ensemble
(gaussian.py:16–41). MIOST calibration surface: calibration:83, _sqrt_s:90,
_grid_sqrt_s_nodes:102, mean_at:146, _anoms_at:150 (scale at :160),
member_at:163, to_grid_ensemble:230, _prov_with:247, with_calibration:288,
rescaled:308, save_state:344 (cal keys :372–374), load_state:384. OI signed
config: `validation/params.py::baseline_config():47` + `baseline_kernel():70`
(audit-trailed, phase-4b). Map producer: `validation/run.py::run_mean_var_maps:180`.
their_eval scorer: `validation/their_eval.py::score:155` — NOT imported by
any Phase-9 task (c2 invariant).

---

### Task 1: Move CalibrationField classes to the shared module (cal_key byte-stable)

**Goal:** `distributions/calibration.py` owns ScalarCalibration /
PolyCalibration / PiecewiseCalibration / CovariateCalibration / ClipSpec /
calibration_from_json + the helpers `_clamp_hull` / `_cell_index` / box
constants; clean break — every caller imports from the new home; behavior and
keys byte-identical.

**Files:**
- Create: `src/sverdrup/distributions/calibration.py`
- Modify: `src/sverdrup/distributions/miost_ensemble.py` (delete moved code;
  import from new module), `scripts/phase8_gate_run.py`,
  `scripts/phase8_fit_run.py`, `tests/test_calibration_field.py`,
  `tests/test_phase8_identity_regression.py`, `tests/test_phase8_gate_run.py`,
  `tests/test_miost_ensemble.py` (import paths only), any other
  `rg -l 'from sverdrup.distributions.miost_ensemble import' src/ scripts/ tests/`
  hits that import moved names
- Test: `tests/test_calibration_field.py` (+ new PIN-C test)

**Acceptance Criteria:**
- [ ] Moved code is TEXTUALLY IDENTICAL (cut-paste; no "improvements") — the
      pre-registered classes must not drift in transit
- [ ] PIN C test: the moved code reproduces the shipped `phase8_field.json`
      `cal_key` byte-identically
- [ ] `rg 'class PolyCalibration' src/` → exactly one hit (new module); no
      import-compat shim left in miost_ensemble.py
- [ ] Full suite green, unchanged counts (imports only)

**Verify:** `pixi run pytest tests/test_calibration_field.py -q` then full
`pixi run test` → green.

**Steps:**

- [ ] **Step 1: PIN-C failing-first test** (add to test_calibration_field.py;
  red only until the module exists — it imports from the NEW path):

```python
def test_moved_code_reproduces_shipped_cal_key_bytes() -> None:
    """The module move must not change key() output for the SHIPPED field.

    Bug caught: key() accidentally hashing module paths/reprs that change
    with the move (PIN C) — the gate runner asserts this exact key.
    """
    import json
    from pathlib import Path
    from sverdrup.distributions.calibration import calibration_from_json

    art = Path("data/2021a_ssh_mapping_ose/ours/phase8_field.json")
    if not art.exists():
        pytest.skip("shipped field artifact absent")
    d = json.loads(art.read_text())
    assert calibration_from_json(d["to_json"]).key() == d["cal_key"]
```

- [ ] **Step 2: Run → FAIL** (`ModuleNotFoundError:
  sverdrup.distributions.calibration`). Paste the line.
- [ ] **Step 3: Move.** Cut the block from miost_ensemble.py (BOX_LON/BOX_LAT,
  `_LON_EDGES`/`_LAT_EDGES`, `_clamp_hull`, `_cell_index`, ClipSpec, the four
  classes, `CalibrationField` alias, `calibration_from_json`; scout line
  refs: classes start after KIND machinery, `_cell_index` at :622) into the
  new module verbatim; add module docstring ("shared home, Phase-9 §2; moved
  verbatim from miost_ensemble.py — pre-registered code, do not edit in
  transit"). In miost_ensemble.py replace with
  `from sverdrup.distributions.calibration import (...)` re-exporting NOTHING
  (callers update). Update every import site found by
  `rg -n 'miost_ensemble import' src/ scripts/ tests/ | rg 'Calibration|ClipSpec|calibration_from_json'`.
- [ ] **Step 4: Run test file → PASS; full suite → green (counts unchanged).**
- [ ] **Step 5: Commit** `refactor(phase9): CalibrationField classes to shared distributions/calibration.py — verbatim move, cal_key byte-stable (PIN C)`

---

### Task 2: CalibratedDistribution wrapper (pins A + B; one general path)

**Goal:** The capability-aware wrapper implementing the protocol over any
distribution; enumerated surface only; unit-tested on a Gaussian-style stub.

**Files:**
- Create (in): `src/sverdrup/distributions/calibration.py`
- Test: `tests/test_calibrated_distribution.py`

**Acceptance Criteria:**
- [ ] Constructor `CalibratedDistribution(underlying, field, capability)` —
      capability EXPLICIT (`UncertaintyCapability`, PIN B); raises
      `CapabilityNotAvailableError` at construction for POINT; validates
      `underlying.grid` exists (named requirement, PIN B)
- [ ] Protocol trio per the spec §2 table; mean routes raw-delegated
- [ ] Enumerated forwarded routes (PIN A): `mean_at`, `member_at`,
      `to_grid_ensemble` DEFINED on the wrapper; each raises
      `CapabilityNotAvailableError("underlying does not provide …")` when the
      underlying lacks the attribute — NO `__getattr__`; leak test with a
      marker-method stub
- [ ] `with_calibration` (fresh wrapper, cache reset) + `rescaled` (scalar
      composes ×; field-calibrated raises ValueError) — Phase-8 semantics
- [ ] Provenance: appends DIAGONAL_INFLATION (incremental s) for scalar /
      FIELD_INFLATION ({calibration_key, cal_kind, dof}) for fields, onto the
      underlying's provenance (single append — raw never appends; full PIN-D
      test lands with Task 3 where the MIOST side stops appending)
- [ ] save_state/load_state on the WRAPPER: delegates array payload to the
      underlying's save/load where it exists, adds `cal_kind`/`cal_params`/
      `cal_key` (same npz keys as Phase 8; legacy rule: files without cal
      keys load scalar-1.0)
- [ ] Per-grid √s memoized once; reset by with_calibration; no-stale-cache test

**Verify:** `pixi run pytest tests/test_calibrated_distribution.py -q` → green.

**Steps:**

- [ ] **Step 1: Failing tests.** Stub:

```python
@dataclass
class _StubGaussian:
    """Minimal SAMPLES-capable stand-in mirroring gaussian.py's surface."""
    grid: GridSpec
    mean: np.ndarray
    time_days: float = 0.0
    provenance: UncertaintyProvenance = field(default_factory=_prov_empty)

    def marginal_variance(self): return np.full(self.mean.shape, 2.0)
    def covariance(self, a, b): return np.full((len(a), len(b)), 0.5)
    def sample(self, m, seed):
        rng = np.random.default_rng(seed)
        return self.mean[None] + rng.standard_normal((m, *self.mean.shape))
    def regrid(self, target): return replace(self, grid=target)
    def secret_marker(self): return "MUST NOT LEAK"
```

  Tests (each docstring names the bug): capability-table rows
  (POINT-construction raise; MARGINAL_VARIANCE-only wrapper raising on
  covariance/sample); `marginal_variance == s(x)·v` pointwise vs an analytic
  PolyCalibration; `covariance == sqrt_s(a)[:,None]*C*sqrt_s(b)[None,:]`
  (hand grid); `sample` moments: same seed ⇒ draws − mean scale by √s
  exactly; mean routes bitwise; `test_no_getattr_leak`:
  `hasattr(wrapped, "secret_marker") is False` AND
  `pytest.raises(AttributeError)` on access (PIN A); forwarded-route raises
  on the stub (`member_at` absent → CapabilityNotAvailableError);
  `regrid` returns a NEW CalibratedDistribution carrying the SAME field
  (batch-3 fold 3); composition ×√(st); rescaled-raises on field;
  no-stale-cache; save/load roundtrip incl. legacy-rule (npz without cal
  keys → scalar-1.0).
- [ ] **Step 2: Run → FAIL (ImportError CalibratedDistribution). Paste line.**
- [ ] **Step 3: Implement.** Shape:

```python
class CalibratedDistribution:
    """Capability-aware s(x) calibration over any PredictiveDistribution.

    ONE general path (spec §2; Phase-8 fast-path-deletion lesson). The
    exposed surface is ENUMERATED below — no __getattr__ passthrough (PIN A).
    """

    def __init__(self, underlying, field: CalibrationField,
                 capability: UncertaintyCapability) -> None:
        if capability is UncertaintyCapability.POINT:
            raise CapabilityNotAvailableError("nothing to calibrate on POINT")
        if not hasattr(underlying, "grid"):
            raise TypeError("CalibratedDistribution requires underlying.grid")
        self._u, self._field, self._cap = underlying, field, capability
        self._grid_sqrt_s: np.ndarray | None = None
        self.provenance = _append_cal_transform(underlying.provenance, field)

    # ---- scaled protocol trio (table rows per capability) ----
    def marginal_variance(self): ...   # s_nodes * self._u.marginal_variance()
    def covariance(self, a, b): ...    # outer sqrt_s scaling; raises if cap < COVARIANCE
    def sample(self, m, seed): ...     # mean + sqrt_s * (draws - mean); raises if cap < SAMPLES
    # ---- raw-delegated mean routes ----
    def mean_at(self, pts): ...        # delegate or CapabilityNotAvailableError
    # ---- enumerated forwarded routes ----
    def member_at(self, i, pts): ...   # mean_at + sqrt_s*(member - mean); delegate-guarded
    def to_grid_ensemble(self, t): ... # rebuild stack about its mean with grid-node sqrt_s
    def regrid(self, target): ...      # CalibratedDistribution(self._u.regrid(target), self._field, self._cap)
    # ---- composition / persistence ----
    def with_calibration(self, cal): ...
    def rescaled(self, s): ...
    def save_state(self, path): ...
    @classmethod
    def load_state(cls, path, ...): ...
```

  (Implementation fills the ellipses with the exact algebra from the spec
  table; grid √s memoized via `_grid_sqrt_s`; capability comparisons via the
  enum ordering used in core/types.py — verify and use the codebase's
  existing capability-comparison idiom.)
- [ ] **Step 4: Run → PASS; pre-commit.**
- [ ] **Step 5: Commit** `feat(phase9): CalibratedDistribution — capability-aware generic calibration wrapper (pins A/B; tests first)`

---

### Task 3: MIOST migration onto the wrapper (identity-gated; PIN D)

**Goal:** Raw MiostEnsembleDistribution loses calibration entirely;
`Miost.solve` wraps; Phase-8 identity suite green UNCHANGED; provenance
sequence equal; σ-semantics pointer updated.

**Files:**
- Modify: `src/sverdrup/distributions/miost_ensemble.py` (delete
  calibration:83, _sqrt_s:90, _grid_sqrt_s_nodes:102, scaling at
  _anoms_at:160, with_calibration:288, rescaled:308, cal parts of
  _prov_with:247 and save/load :372–374/:404–408 — raw class saves raw arrays
  only), `src/sverdrup/methods/miost.py` (ensemble branch returns
  `CalibratedDistribution(raw_ens, self._calibration,
  UncertaintyCapability.SAMPLES)`; shipped σ-semantics docstring gains the
  mechanism pointer: "Mechanism (Phase 9): the field rides the shared
  CalibratedDistribution wrapper (distributions/calibration.py) — relocated
  from the class-internal seam with NO semantic change; identity-proven at
  rtol 1e-12 / mean-bit." — obligation 6)
- Test: `tests/test_miost_ensemble.py`, `tests/test_miost_inflation.py`
  (route through the wrapper; assertions preserved),
  `tests/test_phase8_identity_regression.py` (UNCHANGED — the gate),
  new PIN-D test in `tests/test_calibrated_distribution.py`
- MIOST module helpers (`mean_fields:520`, `std_fields:552`,
  `merged_members:458`) + `scripts/phase8_gate_run.py` /
  `scripts/phase8_fit_run.py`: verify they consume public routes only; adjust
  construction sites, never reach into `._anoms`

**Acceptance Criteria:**
- [ ] `rg '_sqrt_s|with_calibration|rescaled' src/sverdrup/distributions/miost_ensemble.py`
      → no hits (no dual mechanisms)
- [ ] Migration gate: `pixi run pytest tests/test_phase8_identity_regression.py -q`
      → 6 passed 2 skipped with ZERO edits to that file; then
      `SVERDRUP_PHASE8_EXTERNAL=1 ... -m external` → 2 passed (run once,
      detached, ~40 min — the external pins are part of the gate)
- [ ] PIN D: transform-sequence equality test — wrapper-built shipped product
      provenance transforms == the recorded pre-migration sequence (capture
      the expected sequence as a small fixture BEFORE migrating, same
      side-worktree discipline as Phase 8's byte-compat snapshot)
- [ ] Factory byte-compat fixture test green unchanged
- [ ] Full suite green; σ-semantics pointer text present

**Verify:** identity file + external run + full suite (detached, watch via
`bash scripts/watch_pid.sh <pid> 60`).

**Steps:**
- [ ] **Step 1: Capture the provenance-sequence fixture at HEAD~0 (pre-migration)** —
  tiny script writes `tests/fixtures/phase9_provenance_sequence.json`:
  `[{"kind": t.kind.name, "params_keys": sorted(t.params)} for t in shipped_product.provenance.transforms]`
  on the small test fixture config; commit with the script.
- [ ] **Step 2: PIN-D failing test** (compares wrapper-built product's
  sequence to the fixture — red because the wrapper double-appends or the raw
  class still appends until Step 3 lands cleanly).
- [ ] **Step 3: Migrate** (deletions + wrap site + docstring pointer + helper
  construction-site updates).
- [ ] **Step 4: Identity gate**: run the UNCHANGED identity file, the
  in-process suites, the external opt-in run (detached), full suite.
- [ ] **Step 5: Commit** `refactor(phase9): MIOST calibration onto CalibratedDistribution — identity-proven, provenance sequence pinned (PIN D), no dual mechanisms`

---

### Task 4: Generalized harness + ProductDescriptor + per-product mask build

**Goal:** Extract `phase8_fit_run.py`'s sequence into
`application/calibration/harness.py` over a validated ProductDescriptor;
generalize the mask build; thin phase9 CLI; leaf-identical MIOST regression.

**Files:**
- Create: `src/sverdrup/application/calibration/harness.py`,
  `scripts/phase9_fit_run.py`, `scripts/build_jet_core_mask.py`
- Modify: `scripts/phase8_fit_run.py` (becomes a thin shim calling the
  harness with the MIOST descriptor — or is retired with its CLI preserved;
  choose the option that keeps `tests/test_phase8_gate_run.py` +
  provenance-of-record intact and document)
- Test: `tests/test_calibration_harness.py`

**Acceptance Criteria (obligations 1 + 2 pinned):**
- [ ] `ProductDescriptor` frozen dataclass:

```python
@dataclass(frozen=True)
class ProductDescriptor:
    product_id: str            # "miost" | "oi" | ...
    mean_maps: Path
    var_maps: Path
    scope_config: Path         # track source (j3) + time bounds
    mask_artifact: Path
    evidence_key: str          # "phase9.<product_id>.fit_run" (MIOST regression: compared against phase8.fit_run)
    field_artifact: Path
    fold_seed_tuple: tuple[str, str, str]   # + salt appended at draw time
    def __post_init__(self):   # validation: paths typed, product_id nonempty,
        ...                    # seed tuple len 3 of str; evidence_key startswith "phase"
```

- [ ] MIOST descriptor (module constant `MIOST_DESCRIPTOR`) carries the
      FROZEN Phase-8 tuple `("miost", "phase8", "s-folds")` and Phase-8
      paths; OI descriptor constant `OI_DESCRIPTOR` carries
      `("oi", "phase9", "s-folds")` + `oi_{mean,var}_maps.nc` +
      `phase9_jet_core_mask_oi.json` + `phase9_field_oi.json` +
      `phase9.oi.fit_run`
- [ ] Harness = the exact Phase-8 sequence (step-0 alignment consuming the
      product's proxy; ρ̂/n_eff/merge; T+S families lanes 0/A/B+covariate-iff-
      promoted; select ABSOLUTE band; winner refit + clip; evidence blocks
      incl. `jet_core_ref_p8` row + `jaccard_vs_p8` (computed against the
      recorded artifact path with provenance,
      `data/2021a_ssh_mapping_ose/ours/phase8_jet_core_mask.json` —
      data/ours/ is untracked by design, consistent with PIN-C's skip guard)
      + per-product promotion record); NO math in the harness beyond what
      phase8_fit_run.py already inlined (functions move, don't fork)
- [ ] `build_jet_core_mask.py --mean-maps <nc> --out <json>` generalizes the
      phase8 build (same rule constants from the constants package; provenance
      sha256/quantile/rule; byte-identical re-runs); phase8 artifact untouched
- [ ] **LEAF-IDENTICAL regression (obligation 2):** pinned key map is EXACTLY
      `{"phase8.fit_run" → "phase9.miost.fit_run"}` — leaf PATHS below the
      prefix identical, VALUES exactly equal (floats ==, deterministic rerun;
      the two new report-only leaves `jet_core_ref_p8` and `jaccard_vs_p8`
      are EXCLUDED from the comparison by name — for MIOST they are
      self-referential [Jaccard 1.0] and recorded but not compared). The test
      walks both JSON trees:

```python
def _leaves(d, prefix=()):
    if isinstance(d, dict):
        for k, v in d.items(): yield from _leaves(v, (*prefix, k))
    elif isinstance(d, list):
        for i, v in enumerate(d): yield from _leaves(v, (*prefix, str(i)))
    else: yield prefix, d

# EXCLUDED is belt-and-suspenders under the superset assertion below
# (l9.keys() >= l8.keys() already tolerates NEW p9-only leaves; the explicit
# set documents WHICH new rows are expected). Do NOT "simplify" it away —
# it guards against a future rename colliding with a phase8 leaf name.
EXCLUDED = {("regional_table_ref",), ("jet_core_ref_p8",), ("jaccard_vs_p8",)}

def test_harness_on_miost_reproduces_phase8_evidence_leaf_identical():
    """Bug caught: ANY behavioral drift in the extraction — seed scoping,
    lane math, selection, evidence assembly."""
    p8 = load(...)["phase8"]["fit_run"]
    p9 = run_harness(MIOST_DESCRIPTOR, scope="full")  # in-process, ~2.5 min
    l8 = {p: v for p, v in _leaves(p8)}
    l9 = {p: v for p, v in _leaves(p9) if p[:1] not in EXCLUDED and p not in EXCLUDED}
    assert l9.keys() >= l8.keys() and all(l9[p] == v for p, v in l8.items())
```

      (marked `@pytest.mark.external`-style opt-in if runtime >60 s in CI
      terms — same env-gate idiom as Phase 8; run it ONCE in this task and
      record the outcome)
- [ ] Field artifact byte-exact vs `phase8_field.json` for the MIOST run
- [ ] CLI: `SVERDRUP_PHASE9_SCOPE={dev,full}` validation, atomic writes,
      dev writes `phase9_dev_smoke.json` only
- [ ] c2 untouched: `rg 'c2' src/sverdrup/application/calibration/harness.py`
      → docstring/comment hits only; their_eval never imported

**Verify:** `pixi run pytest tests/test_calibration_harness.py -q`; the
leaf-identical run once (paste summary); full suite green.

**Steps:** descriptor tests → red → implement descriptor → harness extraction
(move functions from phase8_fit_run.py; keep names) → mask-build
generalization (+ determinism test: two runs byte-identical on the MIOST
maps → reproduces the phase8 mask cells [(2,1),(2,2),(3,0),(3,1),(3,2),(3,3),(3,4)])
→ leaf-identical run → commit
`feat(phase9): ProductDescriptor + generalized fit harness — harness-on-MIOST leaf-identical to Phase-8 evidence`

---

### Task 5: G_pre anchor recomputation (obligation 5)

**Goal:** One recomputation of the pinned flattening statistic from the
harness's MIOST run; recorded at the named home.

**Files:**
- Create: `scripts/phase9_g_pre_anchor.py`
- Modify: `data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json`
  (script writes `phase9.g_pre_anchor` — atomic)
- Test: `tests/test_calibration_harness.py` (anchor-block assembly unit test
  on synthetic selection tables)

**Acceptance Criteria:**
- [ ] `G_pre = lane0_s_stat − winner_s_stat` from the harness MIOST selection
      block (expected ≈ 0.1790 − 0.0439 = 0.1351; the recomputation is
      canonical, not the arithmetic)
- [ ] Block: `{"g_pre": float, "definition": "<spec §7c1 verbatim>",
      "frame": {"mask": "phase8_jet_core_mask.json", "sha256": ...,
      "fold_seed_tuple": ["miost","phase8","s-folds"], "salt": 1},
      "companions": {"area_weighted_std_log_s": ..., "log_s_range": ...,
      "clip_engagement_fraction": 0.371807..., "nll_gap_demoted":
      {"value": ..., "dof": 5, "n_eff_note": "AIC under-penalizes ~10x at
      n_eff≈n/10.27 — no threshold semantics"}}}` — companions computed from
      the shipped field on the fixed challenge grid
- [ ] Deterministic (two runs byte-identical block); c2 untouched
- [ ] PROGRESS.md gains the §0 record: "Phase-10 = lat-varying METHOD
      parameters (invariant-12) — deferred TO Phase 10, owner-committed;
      A/B boundary per spec §0; G_pre anchor at phase9.g_pre_anchor"
      (obligation 7, first half)

**Verify:** `pixi run python scripts/phase9_g_pre_anchor.py` twice →
identical block; printed G_pre line.

**Steps:** unit test on synthetic tables → script (reads the phase9.miost
evidence, computes companions from `phase9_field_miost.json`≡phase8 field) →
run twice → PROGRESS edit → commit
`feat(phase9): G_pre anchor recorded at phase9.g_pre_anchor (pinned definition; companions attached)`

---

### Task 6: OI map generation at the signed config (obligation 3)

**Goal:** Full-year daily OI mean/variance maps at the signed baseline
config; dev smoke FIRST with runtime/RAM recorded.

**Files:**
- Create: `scripts/generate_oi_maps.py`
- Artifacts (untracked): `data/2021a_ssh_mapping_ose/ours/oi_mean_maps.nc`,
  `oi_var_maps.nc`

**Acceptance Criteria:**
- [ ] Signed config consumed from `sverdrup.validation.params.baseline_config()`
      (variance=1.0, length_scale=SPATIAL_CORR_DEG·km/deg analog,
      time_scale=TEMPORAL_CORR_DAYS=7 d window per params.py:47) +
      `baseline_kernel()` (params.py:70 — the faithful challenge Gaussian
      degree-space kernel passed to `OptimalInterpolation.solve(kernel=...)`);
      NEVER re-tuned; the script asserts the resolved values match the
      audit-trail constants and records them in the nc attrs
- [ ] Obs: train-only under the standing split — `load_mapping_obs` →
      `halo_obs(obs, grid, 1.0)` (grid-node framing) → `make_splits(by=
      "mission", locked_missions=["c2"], validation_missions=["j3"])` →
      `_subset(train_idx)`; c2 rows never scored, j3 never assimilated
- [ ] Generation via `validation/run.py::run_mean_var_maps:180` (reuse; only
      extend if it cannot take the OI method+kernel — document any extension)
- [ ] Provenance attrs on both nc files: assimilated_missions, framing
      ("grid-node halo 1.0 deg"), params_key/audit constants, kernel name
- [ ] Dev smoke FIRST: 12-day scope; record wall + peak RSS in the report;
      full year detached (nohup + `scripts/watch_pid.sh`); full-year wall +
      RSS recorded in the commit body
- [ ] Grid/cadence: challenge grid, daily, 2017-01-01..2017-12-31 — matching
      harness track-interp expectations (same shape as stage_b maps:
      time 365 × lat 52 × lon 51)
- [ ] **MAP-LEVEL CONFIG AUDIT (owner plan-review addition, 2026-07-12):**
      after generation, compare the regenerated OI MEANS against the SIGNED
      `OSE_ssh_mapping_OURS_OI.nc` on matched days — tight rtol (BIT-identical
      if the producer path is shared with the artifact's; determine which and
      record); comparison result recorded in the nc attrs AND the commit
      body. PASS = the code constants are PROVEN to be the signed config (the
      only zero-c2 verification available; the constants-level assert alone
      is not proof). MISMATCH = **STOP and attribute BEFORE the demonstration
      runs** — the Phase-7 0.16 m lesson: a regenerated map that differs from
      the signed artifact is a finding, never a shrug. The dev smoke carries
      the matched-day comparison on its 12-day scope BEFORE the full year
      commits.

**Verify:** dev smoke exit 0 + both nc written; full-year run exit 0;
`ncdump -h`-equivalent attrs check via python one-liner.

**Steps:** script (thin over run_mean_var_maps) → dev smoke → full detached →
verify attrs/shapes → commit
`feat(phase9): OI mean/var map generation at the signed baseline config (train-only obs, provenance attrs)`

---

### Task 7: OI demonstration run + wrapper integration (j3-only)

**Goal:** The harness end-to-end on the OI descriptor; wrapper-integration
tests close the Gaussian-path gap; evidence pack marked demonstration-only.

**Files:**
- Artifacts: `data/2021a_ssh_mapping_ose/ours/phase9_jet_core_mask_oi.json` —
  recorded artifact path with provenance (data/ours/ is untracked by design,
  consistent with PIN-C's skip guard; the phase8 pattern), plus
  `phase9_field_oi.json` (or negative-result), evidence block
  `phase9.oi.fit_run`
- Test: `tests/test_calibrated_distribution.py` (OI integration section,
  external-gated on artifact presence)

**Acceptance Criteria:**
- [ ] Sequence per spec §5: OI mask build (`build_jet_core_mask.py` on the
      OI means; committed-before-fit ordering: mask JSON written + sha
      recorded in evidence BEFORE any lane fit — the harness asserts the mask
      artifact predates the fit stage), step-0 alignment (OI proxy from OI
      means; promotion decision recorded), full lanes/folds/selection with
      the OI seed tuple, bars 1–4 + all report-only instruments +
      `jet_core_ref_p8` + `jaccard_vs_p8` rows
- [ ] **Wrapper integration (batch-2 item 2):**
      `CalibratedDistribution(OI product at one day, fitted field, SAMPLES)`:
      (a) held-out coverage recomputed THROUGH the wrapper == harness
      map-side number (rtol 1e-9 — same interp, same floor); (b) pointwise
      `marginal_variance == s(x)·v` vs the maps (rtol 1e-12)
- [ ] **Interpretation note (batch-2 item 3)** recorded in the evidence:
      ŝ_OI (constant-lane floored MLE) either way; near-1 or lane-0 win =
      informative finding, negative branch live, demonstration-only marker in
      the block (`"demonstration_only": true, "shipping": "not elected;
      Phase 10 supersedes"`)
- [ ] No registry change; no c2; full suite green

**Verify:** `SVERDRUP_PHASE9_SCOPE=dev` smoke → then full run (~minutes;
detached if >5 min); wrapper-integration tests green; evidence block complete.

**Steps:** mask build → dev smoke → full run → wrapper-integration tests
(red-first against a deliberately mis-scaled stub) → commit
`feat(phase9): OI j3-side demonstration — harness method-agnostic on a second product; wrapper integration proven (no ship, no c2)`

---

### Task 8: PHASE-CLOSE OWNER GATE + phase close

**Goal:** **USER-ORDERED GATE — NON-SKIPPABLE.** Single owner review of the
whole phase; then close records.

> **USER-ORDERED GATE — NON-SKIPPABLE.** This task was requested by the user
> in the current conversation. It MUST NOT be closed by walking around it, by
> declaring it "verified inline", or by substituting a cheaper check. Close
> only after every item in acceptanceCriteria has been re-validated
> independently, with output captured.

**Files:** `PROGRESS.md` (close banner — obligation 7 second half),
`README.md` (one-sentence generic-calibration note), plan tracker sync.

**Acceptance Criteria:**
- [ ] Evidence presented verbatim from artifacts: OI evidence pack (selection
      table, bars, promotion decision, ŝ_OI + interpretation, Jaccard),
      G_pre anchor block, migration identity report (suite counts + external
      pins + PIN-D sequence equality + byte-compat), §7 contract section
      quoted
- [ ] Owner ruling captured in PROGRESS.md, dated, committed; NO c2 access
      occurred anywhere in the phase (grep evidence: no new c2 keys; tally
      unchanged at 2)
- [ ] PROGRESS close banner: deliverables, OI finding (whatever it is),
      G_pre value, pointer to spec §7 for Phase 10; push

**Verify:** `rg -n 'phase-9 close' PROGRESS.md`; owner ruling line present;
`git log` shows ruling committed before close.

**Steps:** assemble presentation → STOP for owner → record ruling → close
banner + README + tracker → commit
`docs(progress): PHASE 9 CLOSED — <ruling>` → push.

---

## Execution order & dependencies

```
Task 1 (move, PIN C) → Task 2 (wrapper, pins A/B) → Task 3 (MIOST migration, PIN D; identity gate)
                                                        → Task 4 (harness; leaf-identical gate)
                                                            → Task 5 (G_pre anchor)
Task 6 (OI maps; needs Task 4's descriptor definition only for paths — may run after Task 4)
Task 4 + 6 → Task 7 (OI demonstration + wrapper integration)
Task 5 + 7 → Task 8 (OWNER GATE + close)
```

Identity suite green against the wrapper (Task 3) BEFORE the harness task
starts — owner ordering. Zero c2 anywhere: no task imports their_eval/c2
paths; Task 8's criteria re-verify.

## Self-review record

Obligation 1 → Task 4 descriptor + both tuples spelled. Obligation 2 →
Task 4 pinned map + walker test. Obligation 3 → Task 6 (baseline_config:47 +
baseline_kernel:70, run_mean_var_maps:180, dev smoke, provenance attrs).
Obligation 4 → Task 2 constructor/leak-test/npz schema. Obligation 5 →
Task 5 script + named home + Jaccard in Task 4/7 rows vs the committed p8
mask path. Obligation 6 → Task 3 docstring pointer text. Obligation 7 →
Task 5 (§0 record) + Task 8 (close). Spec coverage: §2→T1/T2, §3→T3,
§4→T4, §5→T6/T7, §6→template recorded in spec (no executable task — by
design, zero touches), §7→T5+T8, §8 suites land inside T1–T4/T7, §11
honored. Placeholder scan: none — every code step has real content or names
the exact source lines to move. Type consistency: ProductDescriptor
field names used identically in T4–T7; CalibratedDistribution signature
consistent T2/T3/T7. Gate tagging: Task 8 = userGate (phase-close review;
evidence axes declared). No task can touch c2: verified — no c2 path, no
their_eval import anywhere in the plan.
