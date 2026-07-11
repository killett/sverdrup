# Phase 8 — Spatially Varying Uncertainty Calibration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the shipped global scalar s\* = 10.062847634082484 with a low-dof
spatial field s(x) applied to MIOST member anomalies at query time, so 1σ coverage
is right regionally — zero re-solves, mean maps bit-unchanged.

**Architecture:** A `CalibrationField` layer inside `MiostEnsembleDistribution`
(one `_sqrt_s(lon, lat)`, consumed at the two row-scaling sites `_anoms_at` /
`_grid_eval`), fit on j3 only by floored Gaussian MLE in log s over two lanes
(piecewise true-partition, ≤6-dof poly) + lane-0 scalar control, selected by a
pre-registered T+S fold protocol, gated per-region, closed by one owner-authorized
c2 touch and a capability-flip commit.

**Tech Stack:** numpy, scipy (optimize, sparse, stats), xarray (map artifacts),
pytest; existing sverdrup modules (`miost_ensemble`, `miost`, `calibration`,
`provenance_guard`).

**Spec (governs on conflict):**
`docs/superpowers/specs/2026-07-10-phase8-spatial-calibration-design.md`

**User decisions (already made):**
- Forks (a)–(e) + all riders per spec §1 (two fit lanes + lane-0; floored MLE;
  spatial-only; T+S folds pool-then-max lexicographic; clamp+clip edges).
- No constant-field fast path — one general eval-time path (spec §2).
- Raw-anoms one-convention persistence; factory supplies the calibration (spec §8).
- Owner gates at spec §7 step 4 (j3-evidence review) and step 5 (single c2 touch,
  fresh authorization, pre-registered reading verbatim); flip commit its own task.
- Negative-result branch (no lane beats lane-0 → ship scalar, record, NO touch)
  representable in the task flow.
- Seam lands test-first (identity/magnitude/byte-compat) before fit-lane code.
- Plan pins (owner order 2026-07-10): T-fold rotations + seeded S-fold layout;
  ρ̂ procedure + min-n_eff + merge rule; 2°-cell grid; jet-core mask build script;
  promotion statistic = Pearson r on per-cell log chi2 (primary; deficit version
  reported alongside); lane-A Newton + lane-B optimizer/tolerance constants named.
- RECORDED NARROWING (owner plan review, 2026-07-10): `rescaled(s)` RAISES on
  field-calibrated products — scalar-on-scalar composes ×√(st) as tested; field
  composition must go explicitly through `with_calibration`. Accepted narrowing
  of spec §8's "composes multiplicatively", chosen so a stray scalar rescale
  cannot silently corrupt a field product. Decision, not drift (spec carries the
  matching postscript).

---

## Pinned constants (single source of truth: `src/sverdrup/application/calibration/constants.py`, created in Task 2)

```python
"""Phase-8 pre-registered constants (spec 2026-07-10; plan-pinned values)."""

SIGMA_OBS2 = 0.03**2  # m^2 — obs-noise floor; anchor: Phase-7 spec §2.2 R_ref
S_STAR = 10.062847634082484  # shipped scalar (methods/miost.py STAGE_B_INFLATION_S)
COVERAGE_TARGET = 0.6827
COVERAGE_TOL = 0.10
TIE_BAND = 0.01  # ±1% tie band on the selection statistic
CLIP_PAD = 1.25  # log-s clip pad factor (spec §9), applied as ±log(1.25)

# 2°-cell grid == S-fold block grid (one definition, spec plan-obligation 3):
# lon edges 295,297,...,305; lat edges 33,35,...,43 → 5×5 = 25 cells.
CELL_DEG = 2.0

# T-folds (plan-obligation 1): 6 rotations, verify-2 contiguous months of 2017.
T_FOLDS = (("01", "02"), ("03", "04"), ("05", "06"),
           ("07", "08"), ("09", "10"), ("11", "12"))

# S-folds (plan-obligation 1): 4 folds over the 25 blocks, sizes (7, 6, 6, 6),
# seeded permutation; salt increments deterministically if the ≥50%-per-fit-region
# constraint fails (recorded).
S_FOLD_COUNT = 4
S_FOLD_SEED_ARGS = ("miost", "phase8", "s-folds")  # + salt as member_index
GUARD_RING_DEG = 0.5

# n_eff (plan-obligation 2): n_eff = n / (1 + 2 * sum(rho_k, k=1..K)),
# K = first k with rho_k < RHO_CUTOFF, capped at RHO_MAX_LAG.
RHO_CUTOFF = 0.05
RHO_MAX_LAG = 20
MIN_N_EFF = 200.0  # per held-out block; below → merge with nearest-centroid
                   # block in the SAME fold (deterministic, recorded)

# Promotion (plan-obligation 5): PRIMARY = Pearson r(per-cell log chi2_red,
# per-cell log proxy); |r| >= 0.6 promotes. Deficit variant reported alongside.
PROMOTION_R = 0.6

# Optimizers (plan-obligation 6):
NEWTON_MAX_ITER = 50
NEWTON_TOL = 1e-10        # |step| in log s
LBFGSB_GTOL = 1e-8        # scipy L-BFGS-B gtol; method name serialized in fit_id
POLY_MAX_DOF = 6
JET_CORE_QUANTILE = 0.75  # spec §6 mask threshold
```

Normalized poly coordinates (used everywhere the poly appears):
`u = (lon − 300)/5`, `v = (lat − 38)/5` — both in [−1, 1] over the box.

## File structure

| File | Responsibility |
|---|---|
| `src/sverdrup/distributions/miost_ensemble.py` (modify) | `CalibrationField` hierarchy (spec §8 places it here) + eval-time seam + persistence keys |
| `src/sverdrup/core/provenance.py` (modify) | `TransformKind.FIELD_INFLATION` |
| `src/sverdrup/methods/miost.py` (modify) | `calibration` argument; params_key fold; factory |
| `src/sverdrup/application/calibration/__init__.py` (create) | package |
| `src/sverdrup/application/calibration/constants.py` (create) | pinned constants above |
| `src/sverdrup/application/calibration/regions.py` (create) | quadrants, jet-core mask I/O, fit partition, 2°-cells/blocks |
| `src/sverdrup/application/calibration/likelihood.py` (create) | floored NLL + grad, lane-A Newton, lane-B L-BFGS-B, tail diagnostic, safeguard |
| `src/sverdrup/application/calibration/folds.py` (create) | T/S folds, guard ring, ρ̂/n_eff, merge rule, pool-then-max, lexicographic selection |
| `scripts/diag_phase8_covariate_alignment.py` (create) | Task 1 step-0 diagnostic |
| `scripts/build_phase8_jet_core_mask.py` (create) | deterministic mask build |
| `scripts/phase8_fit_run.py` (create) | fold fits, selection, winner refit, evidence JSON |
| `scripts/phase8_gate_run.py` (create) | owner-gate evidence presentation + env-gated single c2 touch |
| `tests/test_calibration_field.py`, `tests/test_calibration_likelihood.py`, `tests/test_calibration_folds.py`, `tests/test_calibration_regions.py`, `tests/test_phase8_identity_regression.py` (create); `tests/test_miost_ensemble.py`, `tests/test_miost_inflation.py` (modify) | tests |

Track-side predictive variance CONVENTION (all Phase-8 coverage/chi2/CRPS):
`var_track(x) = s(x)·v(x) + SIGMA_OBS2` (spec §2/§10 — the floor enters only on
track validation; map σ² = s(x)·v(x)). The delta vs Task-19's `s*·v` (floor
absorbed) is quantified in Task 9's reconciliation block.

---

### Task 1: Covariate alignment diagnostic (spec §7 step 0 — EARLY, existing artifacts only)

**Goal:** Measure proxy/miscalibration alignment and record the pre-registered
promotion decision BEFORE any fit-lane work.

**Files:**
- Create: `scripts/diag_phase8_covariate_alignment.py`
- Modify: `data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json` (adds
  `phase8.covariate_alignment` block — script writes it)

**Acceptance Criteria:**
- [ ] Proxy = per-cell temporal std of `stage_b_mean_maps.nc` on the 25-cell grid
- [ ] Per-cell chi2_red of track residuals at frozen s\* (UN-floored, matching the
      Task-19 convention it diagnoses) on the same 25 cells
- [ ] PRIMARY statistic = Pearson r(log chi2_red_cell, log proxy_cell); deficit
      variant r(|coverage_cell − 0.6827|, log proxy_cell) reported alongside
- [ ] Decision recorded verbatim: `"promoted": true` iff |r_primary| ≥ 0.6
- [ ] c2 untouched; no fit performed; existing artifacts only

**Verify:** `pixi run python scripts/diag_phase8_covariate_alignment.py` →
prints the two r values + decision; JSON block written with
`{"r_primary", "r_deficit", "n_cells", "promoted", "semantics"}`.

**Steps:**

- [ ] **Step 1: Write the script** (reuses the load pattern of
  `scripts/diag_stage_b_localized_calibration.py:main` — same maps, same track
  interp, same scope fixture):

```python
"""Phase-8 step-0 covariate alignment diagnostic (spec §1(a), §7 step 0).

Existing artifacts only; runs BEFORE any fit lane. Pre-registered promotion
rule: |Pearson r(per-cell log chi2_red at frozen s*, per-cell log proxy)| >= 0.6
promotes the signal-variance covariate to a third fit lane.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import xarray as xr
from scipy.stats import pearsonr

from sverdrup.application.calibration.constants import (
    CELL_DEG, COVERAGE_TARGET, PROMOTION_R, S_STAR,
)

RESULTS = Path("data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json")
MEAN_NC = Path("data/2021a_ssh_mapping_ose/ours/stage_b_mean_maps.nc")
VAR_NC = Path("data/2021a_ssh_mapping_ose/ours/stage_b_var_maps.nc")
LON_EDGES = np.arange(295.0, 305.0 + CELL_DEG, CELL_DEG)
LAT_EDGES = np.arange(33.0, 43.0 + CELL_DEG, CELL_DEG)


def cell_index(lon: np.ndarray, lat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (row, col) 2°-cell indices, clipped to the 5x5 grid."""
    col = np.clip(np.searchsorted(LON_EDGES, lon, side="right") - 1, 0, 4)
    row = np.clip(np.searchsorted(LAT_EDGES, lat, side="right") - 1, 0, 4)
    return row, col


def proxy_cells(mean_ds: xr.Dataset) -> np.ndarray:
    """(5,5) per-cell mean of the per-node temporal std of the mean maps."""
    std_map = mean_ds["ssh"].std(dim="time")  # (lat, lon) — signed artifact
    out = np.full((5, 5), np.nan)
    lon2d, lat2d = np.meshgrid(std_map["lon"].values, std_map["lat"].values)
    row, col = cell_index(lon2d.ravel(), lat2d.ravel())
    vals = std_map.values.ravel()
    for r in range(5):
        for c in range(5):
            m = (row == r) & (col == c)
            out[r, c] = float(np.nanmean(vals[m]))
    return out
```

  Then `main()`: interp mean/var maps on the j3 track exactly as
  `diag_stage_b_localized_calibration.py` does (same helper calls), compute
  per-cell `chi2 = mean(resid**2 / (S_STAR * var))` and per-cell coverage,
  assemble the two Pearson statistics over cells with ≥ 200 track points,
  write the JSON block, print the decision line.

- [ ] **Step 2: Run it.** `pixi run python scripts/diag_phase8_covariate_alignment.py`
  Expected: decision line `promoted: True|False` with both r values.

- [ ] **Step 3: Record.** The JSON block is the pre-registration record. If
  `promoted: true`, Tasks 2/7/9 include the covariate-lane code they carry
  conditionally (marked below); else that code is NOT written (record the
  measured r in the commit message).

- [ ] **Step 4: Commit** `feat(phase8): step-0 covariate alignment diagnostic + recorded promotion decision`

---

### Task 2: CalibrationField hierarchy + constants package

**Goal:** The field abstraction (scalar / piecewise / poly [+ covariate if
promoted]) with clamp+clip edge behavior and deterministic keys — pure functions,
no distribution wiring yet.

**Files:**
- Create: `src/sverdrup/application/calibration/__init__.py`,
  `src/sverdrup/application/calibration/constants.py` (content pinned above)
- Modify: `src/sverdrup/distributions/miost_ensemble.py` (hierarchy lives here, spec §8)
- Test: `tests/test_calibration_field.py`

**Acceptance Criteria:**
- [ ] `ScalarCalibration(s)`, `PiecewiseCalibration`, `PolyCalibration` frozen
      dataclasses with `sqrt_s_at(lon, lat)`, `log_s_at(lon, lat)`, `key()`,
      `to_json()` / `from_json()`
- [ ] Coordinate clamp to box hull + log-s clip to `[lo, hi]` inside `log_s_at`
      (spec §9); `ScalarCalibration` clip-free
- [ ] `PolyCalibration` reduces exactly to scalar at coeffs `(log s*, 0, 0, 0, 0)`;
      `PiecewiseCalibration` at all-regions-log-s\*
- [ ] `key()` deterministic, includes kind + params + clip + `fit_id`
- [ ] Piecewise values within `[lo, hi]` by construction → clip provably inert
      on that lane (validated in `__post_init__`, raises otherwise)

**Verify:** `pixi run pytest tests/test_calibration_field.py -v` → all pass.

**Steps:**

- [ ] **Step 1: Failing tests first** (`tests/test_calibration_field.py`) —
  each names the bug it would catch:

```python
def test_poly_scalar_reduction_exact() -> None:
    """Coeffs (log s*, 0,...) must equal ScalarCalibration(s*) everywhere.

    Bug caught: wrong normalization of (u, v) or a stray offset term.
    """
    poly = PolyCalibration(
        coeffs=(math.log(S_STAR), 0.0, 0.0, 0.0, 0.0),
        clip=ClipSpec(lo_log_s=math.log(S_STAR) - 1, hi_log_s=math.log(S_STAR) + 1),
        fit_id="test",
    )
    lon = np.array([295.0, 300.0, 305.0, 299.3])
    lat = np.array([33.0, 38.0, 43.0, 41.7])
    np.testing.assert_allclose(
        poly.sqrt_s_at(lon, lat), np.sqrt(S_STAR), rtol=1e-15
    )
    # rtol=1e-15, not 0: exp(0.5*log(s)) vs sqrt(s) is a transcendental
    # roundtrip — ulp-fragile at exact equality (owner review fix, 2026-07-10).
    # The load-bearing pin stays the distribution-level s*-identity at
    # rtol 1e-12 (Task 5).

def test_clamp_constant_continuation_outside_hull() -> None:
    """s at (294, 32) must equal s at the clamped corner (295, 33).

    Bug caught: raw extrapolation of the quadratic outside the box.
    """

def test_clip_engages_and_is_recorded() -> None:
    """A poly whose raw value exceeds hi must return exactly hi.

    Bug caught: clip applied to s instead of log s, or not at all.
    """

def test_piecewise_lookup_and_out_of_range_raises() -> None:
    """Region values outside [lo, hi] must raise at construction.

    Bug caught: silently clipping evidence-side values (spec §9 assert).
    """

def test_key_changes_with_every_param() -> None:
    """Perturbing any coeff, clip bound, or fit_id changes key().

    Bug caught: cache collisions between distinct calibrations.
    """

def test_json_roundtrip_bitexact() -> None:
    """from_json(to_json(f)) reproduces sqrt_s_at bit-identically on a grid."""
```

- [ ] **Step 2: Run tests, confirm FAIL** (`ImportError` / `NameError`).

- [ ] **Step 3: Implement** in `miost_ensemble.py` (after `KIND`):

```python
@dataclass(frozen=True)
class ClipSpec:
    """Pre-registered log-s clip bounds (spec §9; evidence-anchored)."""
    lo_log_s: float
    hi_log_s: float

@dataclass(frozen=True)
class ScalarCalibration:
    """Constant s — the shipped-scalar limit of the field layer."""
    s: float
    def log_s_at(self, lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
        return np.full(np.broadcast(lon, lat).shape, math.log(self.s))
    def sqrt_s_at(self, lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
        return np.full(np.broadcast(lon, lat).shape, math.sqrt(self.s))
    def key(self) -> str:
        return f"cal:scalar;s={self.s!r}"

def _clamp_hull(lon: np.ndarray, lat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Coordinate clamp to the box hull (spec §9 constant continuation)."""
    return (np.clip(np.asarray(lon, float), *BOX_LON),
            np.clip(np.asarray(lat, float), *BOX_LAT))

@dataclass(frozen=True)
class PolyCalibration:
    """log s = a0 + a1·v + a2·v² + a3·u + a4·u·v, u=(lon−300)/5, v=(lat−38)/5."""
    coeffs: tuple[float, float, float, float, float]
    clip: ClipSpec
    fit_id: str
    def log_s_at(self, lon, lat):
        lo, la = _clamp_hull(lon, lat)
        u, v = (lo - 300.0) / 5.0, (la - 38.0) / 5.0
        a0, a1, a2, a3, a4 = self.coeffs
        raw = a0 + a1 * v + a2 * v * v + a3 * u + a4 * u * v
        return np.clip(raw, self.clip.lo_log_s, self.clip.hi_log_s)
    def sqrt_s_at(self, lon, lat):
        return np.exp(0.5 * self.log_s_at(lon, lat))
    def key(self) -> str:
        return (f"cal:poly;coeffs={self.coeffs!r};"
                f"clip=({self.clip.lo_log_s!r},{self.clip.hi_log_s!r});"
                f"fit={self.fit_id}")
```

  `PiecewiseCalibration`: fields `lon_mid`, `lat_mid`, `mask` (bool `(5, 5)`
  jet-core cell mask on the 2°-cell grid), `log_s_by_region`
  (`dict[str, float]`, keys `SW/SE/NW/NE/JET`), `clip`, `fit_id`;
  `log_s_at` clamps to hull, resolves cell via the Task-1 `cell_index` rule,
  region = `JET` where mask true else quadrant by `lon_mid/lat_mid`;
  `__post_init__` raises if any value outside `[lo, hi]`. `to_json`/`from_json`
  for all three (mask as nested list). Union type alias:
  `CalibrationField = ScalarCalibration | PiecewiseCalibration | PolyCalibration`.
  If Task 1 recorded PROMOTED, add `CovariateCalibration(proxy_cells: tuple,
  a: float, b: float, clip, fit_id)` — log s = a + b·log proxy(cell(x)), same
  clamp/clip; else omit the class.

- [ ] **Step 4: Run tests → PASS.**
- [ ] **Step 5: Commit** `feat(phase8): CalibrationField hierarchy + pinned constants (tests first)`

---

### Task 3: Eval-time seam in MiostEnsembleDistribution (fast path deleted)

**Goal:** One general query-time √s(x) application at the two row-scaling sites;
`rescaled()` becomes a composition through the same layer.

**Files:**
- Modify: `src/sverdrup/distributions/miost_ensemble.py`
  (`_anoms_at`, `_grid_eval` call sites, `rescaled`, new `calibration` field +
  `_sqrt_s` + per-grid cache), `src/sverdrup/methods/miost.py:473` (construction
  no longer pre-scales — passes the calibration through)
- Test: `tests/test_calibration_field.py` (seam section), modify
  `tests/test_miost_ensemble.py`, `tests/test_miost_inflation.py`

**Acceptance Criteria:**
- [ ] `MiostEnsembleDistribution.calibration: CalibrationField` (default
      `ScalarCalibration(1.0)`); anomalies stored RAW always
- [ ] `_anoms_at(pts)` returns `sqrt_s[:, None] * eval`; grid path scales node
      rows via a per-grid √s cached ONCE (immutable calibration ⇒ cache safe)
- [ ] Mean paths untouched (no diff in `mean_at` / mean part of
      `to_grid_ensemble`)
- [ ] `rescaled(s)` composes multiplicatively through the layer:
      `rescaled(s).rescaled(t)` ≡ ×√(st); returns a FRESH instance
- [ ] `Miost.solve` ensemble branch returns
      `ens.with_calibration(self._calibration)` — no anomaly mutation
- [ ] Correlation-preservation, magnitude, composition, no-stale-cache, and
      inertness tests green; existing suite green (existing inflation tests
      updated to the layer semantics, assertions preserved)

**Verify:** `pixi run pytest tests/test_calibration_field.py tests/test_miost_ensemble.py tests/test_miost_inflation.py -v` → all pass; then full `pixi run test`.

**Steps:**

- [ ] **Step 1: Failing tests.** Key ones (small synthetic dist fixture already
  exists in `tests/test_miost_ensemble.py` — reuse it):

```python
def test_correlation_preserved_under_nonconstant_field(dist) -> None:
    """Corr' == Corr exactly under a non-constant positive field.

    Bug caught: scaling applied after centering, or one covariance side only.
    """
    field = PolyCalibration(coeffs=(0.5, 0.8, 0.0, 0.3, 0.0), clip=WIDE, fit_id="t")
    a = np.array([[296.0, 34.0, 5.0], [303.0, 42.0, 5.0], [300.0, 38.0, 5.0]])
    c0 = dist.covariance(a, a)
    c1 = dist.with_calibration(field).covariance(a, a)
    d0, d1 = np.sqrt(np.diag(c0)), np.sqrt(np.diag(c1))
    np.testing.assert_allclose(c1 / np.outer(d1, d1), c0 / np.outer(d0, d0),
                               rtol=1e-12)

def test_magnitude_marginal_variance_scales_pointwise(dist) -> None:
    """var'(x) == s(x) · var(x) node-by-node on the grid, analytic.

    Bug caught: any positive-but-wrong power of s (s, s², √s) — the
    correlation test is blind to this by design (spec §2 note).
    """
    field = PolyCalibration(coeffs=(0.2, 0.6, -0.3, 0.1, 0.0), clip=WIDE, fit_id="t")
    v0 = dist.marginal_variance()
    v1 = dist.with_calibration(field).marginal_variance()
    lon2d, lat2d = np.meshgrid(dist.grid.x, dist.grid.y)
    s = np.exp(field.log_s_at(lon2d.ravel(), lat2d.ravel())).reshape(v0.shape)
    np.testing.assert_allclose(v1, s * v0, rtol=1e-12)

def test_rescaled_composition_multiplicative(dist) -> None:
    """rescaled(4).rescaled(9) variance == 36 × base variance (rtol 1e-12)."""

def test_no_stale_sqrt_s_cache(dist) -> None:
    """with_calibration returns a fresh instance; the original's grid
    queries are unchanged after the derived instance is queried.

    Bug caught: per-grid √s cache shared across calibrations.
    """

def test_field_inert_beyond_box_halo(dist) -> None:
    """Beyond box+halo, calibrated marginal stats equal uncalibrated to
    machine precision (anomalies ~0 there; spec §9 inertness pin)."""

def test_mean_untouched_by_field(dist) -> None:
    """mean_at under any field is the SAME ARRAY VALUES as uncalibrated
    (bitwise equal) — the D6 property the whole phase leans on."""
```

- [ ] **Step 2: Run → FAIL** (`with_calibration` missing).

- [ ] **Step 3: Implement.**

```python
# field on the dataclass:
calibration: CalibrationField = field(default_factory=lambda: ScalarCalibration(1.0))
_grid_sqrt_s: np.ndarray | None = field(default=None, repr=False, compare=False)

def _sqrt_s(self, lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    return self.calibration.sqrt_s_at(lon, lat)

def with_calibration(self, cal: CalibrationField) -> MiostEnsembleDistribution:
    """Fresh instance with cal REPLACING the current calibration."""
    return replace(self, calibration=cal, _grid_sqrt_s=None,
                   provenance=self._prov_with(cal))

def rescaled(self, s: float) -> MiostEnsembleDistribution:
    """Exact s-inflation THROUGH the layer; composes multiplicatively."""
    if isinstance(self.calibration, ScalarCalibration):
        return self.with_calibration(ScalarCalibration(self.calibration.s * s))
    raise ValueError("rescaled(scalar) on a field-calibrated product is "
                     "ambiguous — compose explicitly via with_calibration")
```

  In `_anoms_at`: after the existing `_eval`, multiply
  `out * self._sqrt_s(pts[:, 0], pts[:, 1])[:, None]`. In the grid path:
  compute `self._sqrt_s(lon2d.ravel(), lat2d.ravel())` once, memoize on the
  instance (`object.__setattr__` if frozen — the dataclass is NOT frozen, plain
  attribute is fine), apply to anomaly columns ONLY (never the `_etas_a` mean
  columns — apply inside `marginal_variance` / the `fields` anomaly term of
  `to_grid_ensemble`, NOT inside `_grid_eval` itself, so the mean path
  provably cannot pick it up). `miost.py:473` becomes:

```python
ens = self.sample_members(...)
return ens.with_calibration(self._calibration)  # Task 4 defines _calibration
```

  (until Task 4 lands, keep `ScalarCalibration(self.inflation_s)` inline).
  Update `test_ensemble_mode_inflation_exact_and_recorded` +
  `tests/test_miost_inflation.py` to the layer semantics — the numeric
  assertions (variance ×s, mean bit-identical) stay, tolerance on variance
  moves from exact to rtol 1e-12 (float re-ordering, spec identity (ii)).

- [ ] **Step 4: Run seam tests → PASS; full suite → green.**
- [ ] **Step 5: Commit** `feat(phase8): eval-time calibration seam — one general path, fast path deleted (tests first)`

---

### Task 4: Persistence, provenance, factory + params_key (one-convention)

**Goal:** Field serialization into the persisted kind + calibration key;
`FIELD_INFLATION` provenance; factory supplies the calibration at the boundary.

**Files:**
- Modify: `src/sverdrup/distributions/miost_ensemble.py` (`save_state` /
  `load_state`), `src/sverdrup/core/provenance.py` (enum member),
  `src/sverdrup/methods/miost.py` (`calibration` arg, `_params_key`,
  `shipped_miost`)
- Test: `tests/test_calibration_field.py` (persistence section),
  `tests/test_miost_ensemble.py`

**Acceptance Criteria:**
- [ ] `save_state` writes RAW anomalies always + `cal_kind`, `cal_params`
      (json), `cal_key`; `load_state` reconstructs the field; files WITHOUT cal
      keys load with `ScalarCalibration(1.0)` (raw-anoms one-convention — the
      FACTORY supplies s\*, spec §8)
- [ ] `TransformKind.FIELD_INFLATION` added; provenance transform carries
      `{calibration_key, cal_kind, dof}`; scalar keeps `DIAGONAL_INFLATION`
- [ ] `Miost(calibration=...)` accepted; `inflation_s` still accepted and maps
      to `ScalarCalibration(inflation_s)` (compat); both → `self._calibration`;
      `_params_key` gains `;cal={calibration.key()}`
- [ ] Factory byte-compat THROUGH THE FACTORY: `shipped_miost()` product's σ at
      probe points matches the pre-refactor recorded values (snapshot fixture
      captured on the commit BEFORE Task 3 merges — step 1 below)
- [ ] `load_state` kind-tag refusal unchanged; roundtrip bit-exact for all
      field kinds

**Verify:** `pixi run pytest tests/test_calibration_field.py tests/test_miost_ensemble.py -v && pixi run test` → green.

**Steps:**

- [ ] **Step 1: Capture the byte-compat snapshot FIRST** (before any of this
  task's code): a tiny script run at the PRE-Task-3 commit
  (`git worktree add ../pre-seam <sha>` — never checkout in-tree) evaluates the
  existing small-fixture ensemble at fixed probe points with `inflation_s=s*`,
  saves `tests/fixtures/phase8_factory_bytecompat.npz` (probe points, mean,
  marginal std, one covariance block). Commit the fixture with the script.
- [ ] **Step 2: Failing tests** — roundtrip per field kind, legacy-load
  (delete cal keys from an npz, expect `ScalarCalibration(1.0)`),
  `test_factory_bytecompat` (rtol 1e-12 vs fixture — catches the inverted-
  premise regression the spec §8 correction is about: a wrong legacy rule
  ships ~3.2× under-dispersed σ), provenance transform present with the right
  params, params_key changes when calibration changes.
- [ ] **Step 3: Implement** (enum member; npz keys; `Miost.__init__`:

```python
calibration: CalibrationField | None = None,
...
if calibration is not None and inflation_s != 1.0:
    raise ValueError("pass calibration OR inflation_s, not both")
self._calibration = calibration or ScalarCalibration(inflation_s)
```

  `_params_key` += `f";cal={self._calibration.key()}"`; `shipped_miost()`
  passes `calibration=ScalarCalibration(STAGE_B_INFLATION_S)` — flip to the
  field happens ONLY in Task 12).
- [ ] **Step 4: Run → PASS; full suite green.**
- [ ] **Step 5: Commit** `feat(phase8): field persistence + FIELD_INFLATION provenance + factory calibration boundary`

---

### Task 5: s\*-identity four-route regression + mean-unchanged extension

**Goal:** Pin spec identities (i)/(ii) against the SIGNED artifacts and extend
the mean-unchanged non-regression to the field-calibrated product.

**Files:**
- Create: `tests/test_phase8_identity_regression.py`
- Test command extends the existing mean-unchanged machinery in
  `scripts/stage_miost_gate_run.py` (no script change needed — the test drives
  the library path)

**Acceptance Criteria:**
- [ ] With `ScalarCalibration(S_STAR)`, all four routes match ×s\* of the raw
      product at rtol 1e-12: grid `marginal_variance` (S-path), arbitrary-point
      Γ (`covariance` diag at track-like points), cross-point `covariance`,
      `sample()` moments (fixed seed, ddof=1 over full m)
- [ ] Where the signed on-disk artifacts apply (`stage_b_var_maps.nc` at the
      accepted config): field-calibrated variance at the map days matches the
      signed var maps × 1.0 (they were written at s\*) at rtol 1e-9 —
      marked `@external`, skipped when artifacts absent
- [ ] Mean-unchanged: the field-calibrated distribution's mean map is
      BIT-IDENTICAL (`np.array_equal` on float64) to the uncalibrated one for a
      NON-constant field, on the small fixture AND (external) vs the
      regenerated acceptance map
- [ ] Full suite green

**Verify:** `pixi run pytest tests/test_phase8_identity_regression.py -v` →
pass (external tests skip cleanly offline/without artifacts).

**Steps:**
- [ ] **Step 1: Write the tests** (small-fixture versions complete in code;
  external versions load the artifacts under
  `data/2021a_ssh_mapping_ose/ours/` with `pytest.mark.external` +
  existence-skip, the standing repo pattern).
- [ ] **Step 2: Run → PASS** (these should pass immediately if Tasks 3–4 are
  correct — this task is the regression NET; a failure here is a Task-3/4
  defect, fix there).
- [ ] **Step 3: Commit** `test(phase8): s*-identity four-route regression + mean-unchanged extension to field product`

---

### Task 6: Jet-core mask + regions module

**Goal:** Deterministic pre-registered region machinery: mask build script,
quadrants, lane-A fit partition, cell/block helpers.

**Files:**
- Create: `src/sverdrup/application/calibration/regions.py`,
  `scripts/build_phase8_jet_core_mask.py`
- Test: `tests/test_calibration_regions.py`
- Artifact: `data/2021a_ssh_mapping_ose/ours/phase8_jet_core_mask.json`
  (25-cell bool mask + provenance: source file hash, quantile, component rule)

**Acceptance Criteria:**
- [ ] Mask rule exactly spec §6: per-cell temporal std of the shipped Stage-B
      mean maps ≥ its 75th percentile over the 25 cells → largest 4-connected
      component; NO manual edits; reproducible (re-run → identical file)
- [ ] `regions.py`: `cell_index` (shared with Task 1 — move it here, Task-1
      script imports it), `quadrant_of(lon, lat)`, `evaluation_masks(lon, lat,
      mask)` → dict of the 6 evaluation classes (4 quadrants + jet_core +
      aggregate), `fit_partition(lon, lat, mask)` → array of 5 labels
      (`SW,SE,NW,NE` minus mask + `JET`) — a TRUE partition (each point exactly
      one label; asserted)
- [ ] 4-connected-component labeling implemented with
      `scipy.ndimage.label(structure=[[0,1,0],[1,1,1],[0,1,0]])`

**Verify:** `pixi run pytest tests/test_calibration_regions.py -v`; then
`pixi run python scripts/build_phase8_jet_core_mask.py` twice → identical JSON.

**Steps:**
- [ ] **Step 1: Failing tests** — partition-is-partition (every point exactly
  one label, synthetic mask), quadrant boundary points (lon==300 → E,
  lat==38 → N, matching the shipped `>=` convention at
  `diag_stage_b_localized_calibration.py:62-65`), mask determinism (same input
  → same mask), largest-component selection (two components fixture).
- [ ] **Step 2: Implement + run script.**
- [ ] **Step 3: Commit** `feat(phase8): jet-core mask build + pre-registered region machinery`

---

### Task 7: Floored MLE fitters + tail diagnostic + safeguard

**Goal:** The one criterion, all lanes: NLL/grad under
r ~ N(0, s(x)·v + σ_obs²); lane-A per-region Newton; lane-B L-BFGS-B; tail
diagnostic; likelihood safeguard.

**Files:**
- Create: `src/sverdrup/application/calibration/likelihood.py`
- Test: `tests/test_calibration_likelihood.py`

**Acceptance Criteria:**
- [ ] `nll(theta, X, r2, v)` and `grad(theta, X, r2, v)` for log s = X @ theta
      with the SIGMA_OBS2 floor (exact formulas below)
- [ ] `fit_region_newton(r2, v)`: 1-d Newton in log s, init
      `log(mean(r2 / v))` (the σ=0 closed form, recorded), NEWTON_MAX_ITER/
      NEWTON_TOL; converges on synthetic data to the known truth
- [ ] `fit_poly_lbfgsb(X, r2, v)`: `scipy.optimize.minimize(method="L-BFGS-B",
      jac=grad, options={"gtol": LBFGSB_GTOL})`, init `(log S_STAR, 0, ...)`;
      optimizer name + gtol returned in `fit_id`
- [ ] At `SIGMA_OBS2 = 0` monkeypatched, `fit_region_newton` returns
      `mean(r2/v)` to 1e-12 (the D6-consistent closed form — the identity the
      spec §4 records)
- [ ] `tail_diagnostic(r2, v, s_hat)`: mean-fit ŝ vs median-consistent
      `median(r2 / (s_hat*v + SIGMA_OBS2))` compared to the χ²₁ median 0.4549;
      returns the ratio; ≥ 1.5 flags (report-only)
- [ ] `assert_beats_scalar(nll_fit, nll_s_star)` raises `RuntimeError` when the
      fitted NLL exceeds the s\*-constant NLL (loud safeguard, spec §4)

**Verify:** `pixi run pytest tests/test_calibration_likelihood.py -v`.

**Steps:**

- [ ] **Step 1: Failing tests by hand arithmetic** (test-design skill:
  each asserts a value derivable independently):

```python
def test_nll_matches_hand_arithmetic() -> None:
    """n=2 case computed by hand: r2=(1,4), v=(1,2), theta=(0,), X=ones.

    tot_i = 1*v_i + SIGMA_OBS2; nll = 0.5*sum(log tot_i + r2_i/tot_i).
    Bug caught: dropped 0.5, missing floor, log of s*v alone.
    """

def test_grad_matches_finite_difference() -> None:
    """Analytic grad vs central difference at a random-but-fixed theta,
    rtol 1e-6. Bug caught: sign or missing (1 - r2/tot) factor."""

def test_newton_recovers_truth_sigma0() -> None:
    """With floor monkeypatched to 0, Newton == mean(r2/v) exactly."""

def test_newton_recovers_planted_s_with_floor() -> None:
    """Synthetic r ~ N(0, s_true*v + floor), n=200_000, seeded: ŝ within
    1% of s_true=10. Bug caught: fitting total variance (aliases the
    floor into s — the spec §2 sampling artifact)."""

def test_poly_recovers_planted_latitudinal_field() -> None:
    """Plant log s = 2.0 + 0.5*v on synthetic points; L-BFGS-B recovers
    (a0, a1) within 2%, other coeffs ~0."""

def test_safeguard_fires_on_worse_than_scalar() -> None:
    """assert_beats_scalar raises when nll_fit > nll_s_star."""
```

- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement:**

```python
def nll(theta: np.ndarray, x: np.ndarray, r2: np.ndarray, v: np.ndarray) -> float:
    """Floored Gaussian NLL for log s = x @ theta (spec §4)."""
    s = np.exp(x @ theta)
    tot = s * v + SIGMA_OBS2
    return float(0.5 * np.sum(np.log(tot) + r2 / tot))

def grad(theta: np.ndarray, x: np.ndarray, r2: np.ndarray, v: np.ndarray) -> np.ndarray:
    s = np.exp(x @ theta)
    tot = s * v + SIGMA_OBS2
    w = 0.5 * (s * v / tot) * (1.0 - r2 / tot)
    return np.asarray(x.T @ w)
```

  Newton: scalar theta, second derivative analytic or damped step
  `theta -= g / h` with `h = max(h, 1e-12)`, iterate to NEWTON_TOL.
- [ ] **Step 4: Run → PASS.**
- [ ] **Step 5: Commit** `feat(phase8): floored MLE fitters (Newton + L-BFGS-B) + tail diagnostic + safeguard (tests first)`

---

### Task 8: Fold machinery + selection

**Goal:** T/S folds, guard rings, ρ̂/n_eff, merge rule, pool-then-max
statistics, lane-0 eligibility, lexicographic selection.

**Files:**
- Create: `src/sverdrup/application/calibration/folds.py`
- Test: `tests/test_calibration_folds.py`

**Acceptance Criteria:**
- [ ] `t_folds(month)` yields the 6 pinned rotations (verify-months per
      T_FOLDS; fit = complement)
- [ ] `s_fold_layout(salt=0)`: seeded permutation of the 25 blocks via
      `default_rng(derive_seed("miost", "phase8", "s-folds", salt))`, split
      (7, 6, 6, 6); `s_folds(lon, lat, day, labels, layout)` yields per-fold
      (fit_mask, score_mask) with the ±0.5° guard ring excluded from BOTH;
      constraint check: every fit-partition label keeps ≥ 50% of its points in
      every fold, else the caller re-draws at salt+1 (salt recorded in the
      evidence JSON)
- [ ] `rho_hat(z, day, pass_id)`: lag-k autocorrelation of normalized residuals
      along each pass (points sorted along-track within a pass; pass = same
      day, gaps < 30 s equivalent — use the track's native ordering + day
      grouping), averaged over passes, k = 1..RHO_MAX_LAG, truncated at first
      ρ_k < RHO_CUTOFF; `n_eff = n / (1 + 2 * sum(rho))`
- [ ] `merge_small_blocks(layout, n_eff_per_block)`: blocks with
      n_eff < MIN_N_EFF merge into the nearest-centroid block of the SAME fold
      (deterministic tie-break: lowest block index); recorded
- [ ] `pooled_worst_region(cov_by_region)`: per region pool held-out points
      across the family's folds → |coverage − 0.6827| → max over regions
- [ ] `select(lanes)`: lane-0 eligibility (beat lane-0 on PRIMARY beyond
      TIE_BAND AND no worse than lane-0 within TIE_BAND on SECONDARY), then
      lexicographic: S-fold statistic → T-fold statistic → smooth-lane
      preference order (`poly` > `covariate` > `piecewise` at final tie);
      returns `(winner | None, table)` — `None` = negative result

**Verify:** `pixi run pytest tests/test_calibration_folds.py -v`.

**Steps:**
- [ ] **Step 1: Failing tests** — rotation coverage (each month verified
  exactly once across T_FOLDS); layout determinism (same salt → same layout;
  salt+1 → different); guard-ring exclusion (points within 0.5° of a held-out
  block edge appear in NEITHER mask); n_eff hand case (AR(1) synthetic with
  known ρ → n_eff within 10% of theory); eligibility (lane worse than lane-0
  → None; lane better only on secondary → None); lexicographic split case
  (lane A wins T, lane B wins S beyond band → B selected).
- [ ] **Step 2–4: red/green/commit** `feat(phase8): fold machinery + pool-then-max lexicographic selection (tests first)`

---

### Task 9: Fit run + evidence assembly (`phase8_fit_run.py`)

**Goal:** Execute spec §7 steps 1–3: fold fits, selection, winner refit on full
j3, clip bounds, field artifact + the complete evidence JSON.

**Files:**
- Create: `scripts/phase8_fit_run.py`
- Artifacts: `data/2021a_ssh_mapping_ose/ours/phase8_field.json` (winning
  calibration `to_json` + `cal_key`),
  `stage_miost_gate_results.json` gains `phase8` block

**Acceptance Criteria:**
- [ ] Track inputs: j3 points, `resid = ssh − mean_interp`, `v = var_interp`
      (UN-inflated, from the RAW-convention artifacts), day/lon/lat — same
      loaders as `diag_stage_b_localized_calibration.py`
- [ ] Lanes fit per fold (lane 0 = constant s\* evaluated, never fit; lane A
      Newton per fit-partition region; lane B L-BFGS-B; covariate lane iff
      Task 1 promoted); coverage on held-out points at
      `s(x)·v + SIGMA_OBS2`
- [ ] ρ̂ measured ONCE on full j3 at frozen s\* (normalized residuals), recorded;
      n_eff + merge rule applied to S-fold blocks
- [ ] Selection via `folds.select`; NEGATIVE RESULT (`winner is None`) writes
      `phase8.selection.negative_result: true` + the full table, creates NO
      field artifact, and the runner EXITS 0 with the STOP banner for the
      owner — Tasks 11–12 are then NOT executed (Task 13 closes instead)
- [ ] Winner refit on ALL of j3; clip bounds `[L, U]` = lane-A per-region
      log-s range ± log(CLIP_PAD) (evidence-anchored, spec §9); safeguard
      assert runs on the refit
- [ ] Evidence JSON blocks (all pre-registered, spec §6): bars 1–4 (band
      0.6827±0.10, deficit statistic for bar 3 with the SE-0.8267/0.1440
      scalar record), regional table (fitted vs s\* side-by-side), monthly
      table (held-out, fitted vs s\* columns + delta + residual), per-region
      chi2 table with jet-core named, tail diagnostic, clip observability
      (fraction of box+halo nodes engaged + max excursion), off-track bound
      (max|∇log s| analytic from coeffs + max inter-track excursion),
      ŝ-vs-s\* reconciliation (constant-lane fit WITH floor vs 10.0628),
      2°-cell coverage table, held-out CRPS per lane, fold salt, n_eff table
- [ ] c2 UNTOUCHED (no c2 path imported); provenance guard asserted on every
      map→track scoring call

**Verify:** dev smoke first:
`SVERDRUP_PHASE8_SCOPE=dev pixi run python scripts/phase8_fit_run.py` (12-day
scope fixture, minutes) → JSON written, STOP banner printed; then full run.
`pixi run test` stays green (script imports are covered by the module tests).

**Steps:**
- [ ] **Step 1: Write the runner** — thin orchestration over Tasks 6–8 modules
  (no math in the script; everything testable lives in the package). Structure:
  `load_track() → measure_rho() → run_family(t_folds) → run_family(s_folds) →
  select() → refit_or_negative() → evidence() → write + STOP banner`.
- [ ] **Step 2: Dev smoke** (expected: runs end-to-end, evidence JSON present,
  numbers meaningless at dev scope — NOT evidence, never written to the gate
  key; dev scope writes `phase8_dev_smoke.json`, mirroring the Stage-B runner
  discipline).
- [ ] **Step 3: Full run** (j3 full year; CPU-bound fitting is seconds — the
  cost is map interpolation, minutes). Review the printed table.
- [ ] **Step 4: Commit** `feat(phase8): fit run — folds, selection, winner refit, evidence JSON (c2 untouched)`

---

### Task 10: OWNER GATE — j3-evidence review (spec §7 step 4)

**Goal:** **USER-ORDERED GATE — NON-SKIPPABLE.** Owner reviews the j3-side
evidence and rules: proceed to the c2 touch (Task 11), or take the
negative-result close (Task 13), or order rework.

**Files:** none (evidence = `phase8` block in the gate results JSON + the plan's
printed table).

**Acceptance Criteria:**
- [ ] Evidence presented verbatim from the JSON: selection table (all lanes +
      lane-0, both family statistics), bars 1–4 outcomes, all report-only
      instruments (§6 list), fold salt + n_eff table, safeguard result
- [ ] Explicit owner ruling captured in PROGRESS.md: PROCEED-TO-TOUCH /
      NEGATIVE-CLOSE / REWORK (with reasons)
- [ ] NO c2 access of any kind before the ruling

**Verify:** PROGRESS.md contains the dated owner ruling block; git log shows it
committed before any Task-11 activity.

**Steps:**
- [ ] **Step 1:** Present the evidence tables (from the JSON, no re-derivation).
- [ ] **Step 2:** STOP. Wait for the owner ruling. Record it in PROGRESS.md,
  commit `docs(progress): phase-8 j3-evidence ruling — <RULING>`.

---

### Task 11: OWNER GATE — the single c2 touch (spec §7 step 5)

**Goal:** **USER-ORDERED GATE — NON-SKIPPABLE.** One owner-authorized c2
evaluation of the FROZEN field; pre-registered reading applied verbatim.

**Files:**
- Create: `scripts/phase8_gate_run.py` (c2 scoring at the frozen field;
  `SVERDRUP_MIOST_C2=1` REQUIRED, mirroring `stage_miost_gate_run.py`
  discipline; reads `phase8_field.json`, refuses to run if absent or if
  `negative_result` is recorded)
- Modify: `stage_miost_gate_results.json` (`phase8.c2_acceptance`)

**Acceptance Criteria:**
- [ ] Fresh owner authorization obtained IN THIS TASK (Task-10 PROCEED ruling
      does not pre-authorize the touch — standing one-touch discipline)
- [ ] Field loaded from `phase8_field.json` byte-exact (cal_key match asserted);
      NOTHING refit on c2
- [ ] Pre-registered reading, verbatim: (µ, σ, λx) triplet BIT-IDENTICAL to the
      signed Stage-A values (0.8572612, 0.0799886, 156.42997) — ANY deviation =
      defect → STOP; aggregate c2 coverage at `s(x)·v + SIGMA_OBS2` ∈
      0.6827±0.10 → SIGN OFF; outside → HOLD, record, no refit, owner call
- [ ] Regional c2 coverage breakdown (6 evaluation classes) reported
      (report-only); chi2_red + CRPS recorded as the honest generalization
      numbers
- [ ] Provenance guard active on the scoring path; exactly ONE touch executed

**Verify:** `phase8.c2_acceptance` block present with
`reproduces_stage_a: true` and the coverage verdict; CONVERGENCE/scoring logs
show a single c2 evaluation.

**Steps:**
- [ ] **Step 1:** Write `phase8_gate_run.py` (reuse the c2-touch scaffolding
  pattern of `stage_miost_gate_run.py` — their_eval triplet + calibration
  block + localized breakdown via `regions.evaluation_masks`).
- [ ] **Step 2:** STOP — request owner authorization, quoting the
  pre-registered reading.
- [ ] **Step 3 (post-authorization):** `SVERDRUP_MIOST_C2=1 pixi run python
  scripts/phase8_gate_run.py` → apply the reading mechanically → record
  outcome in PROGRESS.md, commit
  `docs(progress): phase-8 c2 touch — <OUTCOME> (pre-registered reading)`.

---

### Task 12: Capability-flip commit + σ-semantics + phase close

**Goal:** On sign-off: registry `"miost"` ships the field-calibrated product;
σ-semantics paragraph replaced; PROGRESS close entry.

**Files:**
- Modify: `src/sverdrup/methods/miost.py` (`shipped_miost` →
  `calibration=<winning field from phase8_field.json, inlined as constants>`;
  docstring = spec §10 paragraph instantiated with the measured numbers),
  `tests/test_miost_ensemble.py` (flip test asserts the field calibration +
  FIELD_INFLATION provenance on the shipped product), `PROGRESS.md`, `README.md`
  (calibrated-σ story sentence)

**Acceptance Criteria:**
- [ ] `shipped_miost()` returns the field-calibrated config; the winning
      field's params inlined as named module constants (same pattern as
      `STAGE_B_INFLATION_S`); scalar constant retained for the record
- [ ] σ-semantics docstring carries: field kind/dof/cal_key, floor-exclusion
      delta, √(s(x)s(y)) covariance statement, per-region coverage evidence
      numbers, edge clamp/clip, jet-core/monthly residual limitations with
      numbers (spec §10 verbatim structure)
- [ ] Flip test green; full suite green; pre-commit clean
- [ ] PROGRESS.md close banner (tally: c2 touches for this product = 1)

**Verify:** `pixi run test` → green;
`pixi run python -c "from sverdrup.methods.registry import METHODS; print(METHODS['miost']().native_capability)"` → SAMPLES.

**Steps:**
- [ ] **Step 1:** Update flip test expectations (field, not scalar) → run → FAIL.
- [ ] **Step 2:** Flip the factory + docstring → run → PASS; full suite.
- [ ] **Step 3:** PROGRESS + README; commit
  `feat(miost): Phase-8 capability flip — registry miost ships the field-calibrated product`; push.

---

### Task 13: Negative-result close (ALTERNATIVE branch — executes only on a Task-10 NEGATIVE-CLOSE ruling)

**Goal:** Pre-registered negative-result path (spec §3): no lane beat lane-0 →
ship the scalar, record the finding, spend NO c2 touch.

**Files:**
- Modify: `PROGRESS.md` (close entry: measured selection table, the finding,
  scalar stays shipped), `src/sverdrup/methods/miost.py` (docstring gains one
  sentence: field investigated, did not beat scalar on held-out regional
  coverage — dated, with the table pointer), spec gets a dated postscript line.

**Acceptance Criteria:**
- [ ] NO c2 access occurred anywhere in the phase (grep the logs/JSON — no
      `c2_acceptance` under `phase8`)
- [ ] Registry unchanged (scalar product still shipped); suite green
- [ ] Owner confirms the close in PROGRESS.md

**Verify:** `phase8` JSON block shows `negative_result: true` and no
`c2_acceptance` key; owner close line in PROGRESS.md.

**Steps:**
- [ ] **Step 1:** Write the PROGRESS close + docstring sentence; commit
  `docs(phase8): negative-result close — scalar stands, no c2 touch spent`; push.

**Branch semantics (task-flow representation):** exactly one of
{Task 11 → Task 12} or {Task 13} executes, decided by the Task-10 owner
ruling. Task 13 is blocked by Task 10 only; Tasks 11/12 are blocked by
Task 10 (and 11) respectively. Whichever branch does not execute is closed as
superseded with a pointer to the ruling — never silently skipped.

---

## Execution order & dependencies

```
Task 1 (covariate diag)  ──────────────┐
Task 2 (field classes)  → Task 3 (seam) → Task 4 (persistence/factory) → Task 5 (identity regression)
Task 6 (mask/regions)   ───────────────┤
Task 7 (fitters)  [dep 2,6]            ├→ Task 9 (fit run) → Task 10 (GATE: j3 review)
Task 8 (folds)    [dep 6,7]            ┘         ├→ Task 11 (GATE: c2 touch) → Task 12 (flip)
                                                 └→ Task 13 (negative close)
```

Task 9 additionally depends on 1 (promotion decision), 3, 4, 5 (seam proven
before any fit-lane consumption — the test-first ordering the owner required).

## Self-review record

Spec coverage: §2 → Tasks 2–5; §3 → Tasks 7/9 (lane-0), 13 (negative path);
§4 → Task 7; §5 → Task 8 (+ 9 for ρ̂/salt recording); §6 → Tasks 6, 9;
§7 → Tasks 1, 9–13 (order pinned); §8 → Tasks 3–4; §9 → Tasks 2, 9 (bounds);
§10 → Task 12; §11 honored (no method-layer work anywhere). Plan-detail
obligations 1–6 → pinned-constants block + Tasks 8 (1, 2), 1 (3, 5), 6 (4),
7 (6). Type consistency: `CalibrationField`/`ClipSpec`/`with_calibration`/
`cell_index` names used identically across Tasks 1–9.
