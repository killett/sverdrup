# Phase 7 — MIOST Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the MIOST multiscale reduced-basis inversion as sverdrup method `"miost"` in two hard-gated stages: Stage A (POINT, six ensemble-ready seams, 2021a gate) and Stage B (perturbed-observation ensemble, SAMPLES).

**Architecture:** Wavelet dictionary (U2021 Eqs. 18–19) → CSR G assembled analytically at obs coords → reduced normal equations `(GᵀR⁻¹G + Q⁻¹)η = GᵀR⁻¹y` solved by Jacobi-PCG → window-cache Method (60-d windows, 15-d linear temporal blend) behind the unchanged Method protocol. Stage B adds identity-keyed CRN perturbed-observation members through the same `solve(b)`.

**Tech Stack:** numpy, scipy.sparse (CSR), existing sverdrup core/tuning/validation seams. No new dependencies.

**Spec (governs on conflict):** `docs/superpowers/specs/2026-07-03-phase7-miost-design.md` (decision register D1–D8).

**User decisions (already made):** D1 8-rung ladder 80→905/√2, n_dir=8/180°; D2 12-dir validation-track diagnostic; D3 W=60/V=15/stride45 at L_t_max=12, L_t tunable [5,12], Δt=L_t/2; D4 equivalence diagnostic REQUIRED + pavement fallback; D5 window-cache Method + 4 hardenings; D6 coefficient-space ensemble + CRN + s-rescale; D7 halo=1.0, α box intact, predicate-priced; D8 λ_ref=300 km, R_ref=(0.03)², gauge-inert. Plan-detail items fixed here: window placement s_k=−18+45k (k=0..8); parameter_space boxes α(0.5,1.5)/log10_rho(−2,3)/q_slope(0,4)/l_t_days(5,12); CRN = blake2b keyed-hash → ndtri; infeasible reason via `predicate.explain()` → `TrialRecord.exclusion_reason`; pcg_rtol=1e-6, pcg_maxiter=500.

**Stage gating:** Tasks 14–19 are BLOCKED BY Task 13 (Stage-A gate). Do not start them before the gate is signed off.

---

## File map

| File | Task | Responsibility |
|---|---|---|
| `src/sverdrup/methods/miost_sizing.py` | 1 | Sizing arithmetic (single source; probe re-imports) |
| `src/sverdrup/methods/miost_basis.py` | 2, 3 | BasisSpec, element enumeration, evaluation, G/S/Q builders |
| `src/sverdrup/methods/miost_solver.py` | 4 | Multi-RHS Jacobi-PCG + convergence report |
| `src/sverdrup/methods/miost_windows.py` | 6 | WindowPlan + blend weights |
| `src/sverdrup/methods/miost.py` | 7, 8 | POINT distribution, window-cache Method, parameter_space |
| `src/sverdrup/core/distribution.py` | 7 | `CapabilityNotAvailableError` |
| `src/sverdrup/application/tuning/objective.py` | 9 | `bars_for(capability)` |
| `src/sverdrup/application/tuning/scorer.py` | 9 | Capability-routed map path; var-optional scores |
| `src/sverdrup/application/tuning/feasibility.py` | 10 | `StoredGFeasibility`, `CompositeFeasibility` |
| `src/sverdrup/application/tuning/loop.py` | 10 | `explain()` → `exclusion_reason` |
| `scripts/diag_miost_equivalence.py` | 11 | Windowed-vs-single-window diagnostic |
| `scripts/diag_miost_tier3.py`, `scripts/diag_miost_ndir12.py` | 12 | Tier-3 + 12-dir diagnostics |
| `scripts/stage_miost_gate_run.py` | 13 | Stage-A tuning + c2-once acceptance |
| `src/sverdrup/methods/miost_crn.py` | 14 | Identity-keyed CRN perturbations |
| `src/sverdrup/distributions/miost_ensemble.py` | 15 | Coefficient-space ensemble distribution + persistence |
| `scripts/diag_miost_seam_dispersion.py` | 18 | Stage-B seam/variance diagnostics |

Constants shared across tasks (defined once in `miost_basis.py`, imported elsewhere): `LADDER = scale_set(80.0, lam_max=905.0)` (8 rungs), `N_DIR = 8`, `LAM_REF = 300.0`, `R_REF = 0.03**2`, `W_DAYS = 60.0`, `V_DAYS = 15.0`, `STRIDE_DAYS = 45.0`, `LT_MAX = 12.0`, `BETA = 0.5` (Δt = BETA·L_t), `HALO_DEG = 1.0`, `PCG_RTOL = 1e-6`, `PCG_MAXITER = 500`.

---

### Task 1: Relocate sizing functions into the package

**Goal:** `miost_sizing.py` is the single arithmetic for basis sizes, with the 905-cap and pavement-margin terms; probe re-imports it.

**Files:**
- Create: `src/sverdrup/methods/miost_sizing.py`
- Modify: `scripts/probe_miost_cost.py` (delete local copies of `scale_set`/`n_coefficients`/`nnz_g`, import from the package)
- Modify: `tests/test_probe_miost_cost.py` → rename `tests/test_miost_sizing.py`, import from package

**Acceptance Criteria:**
- [ ] `scale_set(80.0, lam_max=905.0)` returns 8 rungs ending ≈905.1
- [ ] `n_coefficients(..., margin=True)` includes the per-scale 1.5λ pavement extension; `margin=False` reproduces the probe's box-only numbers exactly (61,056 case)
- [ ] `nnz_g` unchanged in value (margin does not change the per-obs upper bound)
- [ ] Probe runs and prints the same (a)/(c) sections; sizing table now 8-rung
- [ ] All existing sizing tests pass against the package import

**Verify:** `pixi run pytest tests/test_miost_sizing.py -q` → all pass; `pixi run python scripts/probe_miost_cost.py` → table prints.

**Steps:**

- [ ] **Step 1: Write the failing test additions** (in the renamed `tests/test_miost_sizing.py`; keep all six existing tests, change import to `from sverdrup.methods.miost_sizing import ...`)

```python
def test_scale_ladder_905_cap() -> None:
    """8-rung ladder 80->905 (D1). Hand: 80*sqrt(2)^7 = 905.097 <= 905 cap + eps."""
    scales = scale_set(80.0, lam_max=905.0)
    assert len(scales) == 8
    assert scales[-1] == pytest.approx(905.097, abs=0.01)


def test_n_coefficients_margin_term() -> None:
    """Pavement margin (D=box+2*1.5*lam per scale) raises N_coef; box-only unchanged.

    Hand (lam=80, alpha=1): n_x = ceil((877.2+240)/80) = 14, n_y = ceil((1113.2+240)/80) = 17
    vs box-only 11 x 14 — margin must produce MORE positions at every scale.
    """
    box = n_coefficients(alpha=1.0, n_dir=8, window_days=60, lam_min=80.0, margin=False)
    marg = n_coefficients(alpha=1.0, n_dir=8, window_days=60, lam_min=80.0, margin=True)
    assert box == 61_056  # the probe's hand-derived anchor still holds
    assert marg > box
```

- [ ] **Step 2: Run to verify failure** — `pixi run pytest tests/test_miost_sizing.py -q` → ImportError (module missing).

- [ ] **Step 3: Create `src/sverdrup/methods/miost_sizing.py`** — move `scale_set`, `n_coefficients`, `nnz_g` from the probe verbatim, then: add `lam_max` already a param (keep); add `margin: bool = False` to `n_coefficients`:

```python
def n_coefficients(
    alpha: float,
    n_dir: int,
    window_days: float,
    lam_min: float,
    lam_max: float = 800.0,
    margin: bool = False,
    dt_days: float = 5.0,
) -> int:
    """Count basis coefficients; ``margin=True`` adds the per-scale 1.5*lam pavement extension."""
    n_t = math.ceil(window_days / dt_days)
    total = 0
    for lam in scale_set(lam_min, lam_max):
        ext = 3.0 * lam if margin else 0.0  # 1.5*lam each side
        n_x = max(1, math.ceil((D_X_KM + ext) / (alpha * lam)))
        n_y = max(1, math.ceil((D_Y_KM + ext) / (alpha * lam)))
        total += n_x * n_y * n_t * n_dir * 2
    return total
```

Module constants `D_X_KM`/`D_Y_KM`/`KM_PER_DEG` move here too. `nnz_g` gains `lam_max: float = 800.0` passthrough only.

- [ ] **Step 4: Re-point the probe** — delete the three functions + geometry constants from `scripts/probe_miost_cost.py`; add `from sverdrup.methods.miost_sizing import D_X_KM, D_Y_KM, n_coefficients, nnz_g, scale_set`. Probe behavior unchanged (calls with `lam_max=800` default keep old output; that is fine — the probe documents the Task-0 snapshot).

- [ ] **Step 5: Run tests + probe** — `pixi run pytest tests/test_miost_sizing.py -q` → 8 passed. `pixi run python scripts/probe_miost_cost.py` → runs.

- [ ] **Step 6: Commit** — `git add -A && git commit -m "refactor(miost): relocate sizing functions into methods/miost_sizing (905-cap + margin term)"`

### Task 2: BasisSpec, element enumeration, analytic evaluation

**Goal:** `BasisSpec` enumerates the wavelet dictionary with stable global element identity and evaluates it analytically (U2021 Eqs. 18–19).

**Files:**
- Create: `src/sverdrup/methods/miost_basis.py`
- Test: `tests/test_miost_basis.py`

**Acceptance Criteria:**
- [ ] Element = cosine carrier (NO ωt term) × separable cos(πδ/2) taper, hard zero outside support (Tier 2)
- [ ] Ladder spans 80→905, 8 rungs; directions j·22.5°, j=0..7; phase pairs {0, π/2} (Tier 2)
- [ ] Temporal slots are GLOBAL (j·Δt from EPOCH), spatial pavement box+1.5λ margin
- [ ] Element identity tuple independent of window (same element in two windows → same identity)

**Verify:** `pixi run pytest tests/test_miost_basis.py -q` → all pass.

**Steps:**

- [ ] **Step 1: Write failing tests**

```python
import numpy as np
import pytest

from sverdrup.methods.miost_basis import BasisSpec, LADDER

SPEC = BasisSpec(alpha=1.0, l_t_days=10.0)


def test_ladder_8_rungs_80_to_905() -> None:
    assert len(LADDER) == 8 and LADDER[0] == 80.0
    assert LADDER[-1] == pytest.approx(905.097, abs=0.01)


def test_hard_compact_support() -> None:
    """Tier 2: exact zero beyond 1.5*lam spatially and beyond L_t temporally.

    Bug caught: Gaussian-like taper (no hard cutoff) or support radius != 1.5*lam.
    """
    els = SPEC.elements_for_window(start_day=0.0)
    # take one 80-km element near the box center
    p = next(i for i, e in enumerate(els.identity) if e[0] == 0)
    x0, y0, t0 = els.x_km[p], els.y_km[p], els.t_days[p]
    inside = SPEC.evaluate(els, np.array([x0 + 0.9 * 120.0]), np.array([y0]), np.array([t0]))[0, p]
    outside_x = SPEC.evaluate(els, np.array([x0 + 1.01 * 120.0]), np.array([y0]), np.array([t0]))[0, p]
    outside_t = SPEC.evaluate(els, np.array([x0]), np.array([y0]), np.array([t0 + 10.01]))[0, p]
    assert inside != 0.0 and outside_x == 0.0 and outside_t == 0.0


def test_no_omega_t_carrier() -> None:
    """Carrier phase is time-INDEPENDENT (documented absence of propagation).

    Bug caught: an omega*t term sneaking into the carrier. At fixed (x,y), moving in t
    changes only the temporal taper -> the ratio of values at two in-support times
    equals the ratio of tapers, INDEPENDENT of which element (same t-slot) we probe.
    """
    els = SPEC.elements_for_window(start_day=0.0)
    p = next(i for i, e in enumerate(els.identity) if e[0] == 0)
    x = np.array([els.x_km[p] + 20.0]); y = np.array([els.y_km[p] + 10.0])
    v1 = SPEC.evaluate(els, x, y, np.array([els.t_days[p] + 1.0]))[0, p]
    v2 = SPEC.evaluate(els, x, y, np.array([els.t_days[p] + 3.0]))[0, p]
    lt = SPEC.l_t_days
    expected = np.cos(np.pi * 3.0 / (2 * lt)) / np.cos(np.pi * 1.0 / (2 * lt))
    assert v2 / v1 == pytest.approx(expected, rel=1e-12)


def test_global_slot_identity_window_independent() -> None:
    """Same physical element enumerated from two overlapping windows -> same identity."""
    a = SPEC.elements_for_window(start_day=0.0)
    b = SPEC.elements_for_window(start_day=45.0)
    shared = set(map(tuple, a.identity)) & set(map(tuple, b.identity))
    assert shared  # the 15-day overlap shares temporal slots
```

- [ ] **Step 2: Run → fail** (module missing).

- [ ] **Step 3: Implement `miost_basis.py`**

```python
"""MIOST wavelet dictionary: BasisSpec, enumeration, analytic evaluation (spec §2.1)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from sverdrup.methods.miost_sizing import D_X_KM, D_Y_KM, KM_PER_DEG, scale_set

LADDER: tuple[float, ...] = tuple(scale_set(80.0, lam_max=905.0))  # D1: 8 rungs
N_DIR = 8                      # D1: mod-180 degrees
LAM_REF = 300.0                # D8 anchor (gauge-inert)
R_REF = 0.03**2                # D8 anchor (gauge-inert)
W_DAYS, V_DAYS, STRIDE_DAYS = 60.0, 15.0, 45.0   # D3 run-constants
LT_MAX, BETA = 12.0, 0.5       # D3: placement designed at ceiling; dt = BETA*l_t
HALO_DEG = 1.0                 # D7
BOX_LON = (295.0, 305.0)
BOX_LAT = (33.0, 43.0)
MID_LAT = 38.0
SUPPORT = 1.5                  # L = 1.5*lam


@dataclass(frozen=True)
class Elements:
    """One window's enumerated elements (columns of Gamma restricted to the window)."""

    identity: np.ndarray  # (n, 6) int32: scale_idx, dir_idx, phase_idx, ix, iy, global_slot
    x_km: np.ndarray      # element centers, km from box lon-min at MID_LAT
    y_km: np.ndarray
    t_days: np.ndarray
    kx: np.ndarray        # carrier wavevector components (rad/km)
    ky: np.ndarray
    phase: np.ndarray     # 0 or pi/2
    half_width_km: np.ndarray  # 1.5*lam per element


@dataclass(frozen=True)
class BasisSpec:
    """Run-constants + continuous basis params; the single source of enumeration."""

    alpha: float
    l_t_days: float
    n_dir: int = N_DIR
    ladder: tuple[float, ...] = LADDER

    @property
    def dt_days(self) -> float:
        """Temporal pavement spacing (D3: tied dt = BETA * l_t)."""
        return BETA * self.l_t_days

    def key(self) -> str:
        """Canonical basis contribution to params_key (everything eta depends on)."""
        return (
            f"miost-basis;alpha={self.alpha!r};l_t={self.l_t_days!r};n_dir={self.n_dir};"
            f"ladder={','.join(f'{s:.3f}' for s in self.ladder)};beta={BETA};"
            f"W={W_DAYS};V={V_DAYS};stride={STRIDE_DAYS};halo={HALO_DEG};"
            f"lam_ref={LAM_REF};r_ref={R_REF!r}"
        )

    def elements_for_window(self, start_day: float) -> Elements:
        """Enumerate elements whose GLOBAL temporal slot falls in [start, start+W]."""
        ids, xs, ys, ts, kxs, kys, phs, hws = [], [], [], [], [], [], [], []
        dt = self.dt_days
        j_lo = math.ceil(start_day / dt)
        j_hi = math.floor((start_day + W_DAYS) / dt)
        for s_idx, lam in enumerate(self.ladder):
            hw = SUPPORT * lam
            step = self.alpha * lam
            # spatial pavement: box + 1.5*lam margin each side (spec §2.1)
            nx = int(np.ceil((D_X_KM + 2 * hw) / step))
            ny = int(np.ceil((D_Y_KM + 2 * hw) / step))
            x0, y0 = -hw, -hw
            k = 2 * np.pi / lam
            for d_idx in range(self.n_dir):
                th = np.pi * d_idx / self.n_dir  # mod-180 (D1)
                for p_idx, ph in enumerate((0.0, np.pi / 2)):
                    for ix in range(nx):
                        for iy in range(ny):
                            for j in range(j_lo, j_hi + 1):
                                ids.append((s_idx, d_idx, p_idx, ix, iy, j))
                                xs.append(x0 + ix * step)
                                ys.append(y0 + iy * step)
                                ts.append(j * dt)
                                kxs.append(k * np.cos(th))
                                kys.append(k * np.sin(th))
                                phs.append(ph)
                                hws.append(hw)
        return Elements(
            np.asarray(ids, dtype=np.int64),
            np.asarray(xs), np.asarray(ys), np.asarray(ts),
            np.asarray(kxs), np.asarray(kys), np.asarray(phs), np.asarray(hws),
        )

    def evaluate(
        self, els: Elements, x_km: np.ndarray, y_km: np.ndarray, t_days: np.ndarray
    ) -> np.ndarray:
        """Dense (n_pts, n_elements) evaluation — small inputs only (tests, representers)."""
        dx = x_km[:, None] - els.x_km[None, :]
        dy = y_km[:, None] - els.y_km[None, :]
        dt = t_days[:, None] - els.t_days[None, :]
        hx = els.half_width_km[None, :]
        carrier = np.cos(els.kx[None, :] * dx + els.ky[None, :] * dy + els.phase[None, :])
        tap = (
            _cos_tap(dx / hx) * _cos_tap(dy / hx) * _cos_tap(dt / self.l_t_days)
        )
        return np.asarray(carrier * tap)


def _cos_tap(d: np.ndarray) -> np.ndarray:
    """cos(pi*d/2) inside |d|<1, exact 0 outside (U2021 Eq. 19)."""
    return np.where(np.abs(d) < 1.0, np.cos(0.5 * np.pi * d), 0.0)


def lonlat_to_km(lon: np.ndarray, lat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Project degrees to the local km frame used for element geometry."""
    x = (np.asarray(lon) - BOX_LON[0]) * KM_PER_DEG * math.cos(math.radians(MID_LAT))
    y = (np.asarray(lat) - BOX_LAT[0]) * KM_PER_DEG
    return x, y
```

NOTE for implementer: the pure-Python enumeration loop is fine at this stage (runs once per window; ~10⁵ elements at α=1). If profiling shows it slow at α=0.5, vectorize with `np.meshgrid` — behavior identical, tests unchanged.

- [ ] **Step 4: Run → pass.** `pixi run pytest tests/test_miost_basis.py -q`

- [ ] **Step 5: Commit** — `git commit -m "feat(miost): BasisSpec — wavelet dictionary with global element identity (D1/D3)"`

### Task 3: G/S/Q builders, applies, representer + gauge tests

**Goal:** Sparse CSR builders for G (obs) and S (grid), diagonal Q/R objects with named parameterization, first-class applies; seam (b)+(c) and Tier-2 representer tests.

**Files:**
- Modify: `src/sverdrup/methods/miost_basis.py` (add builders + `DiagonalQ`, `DiagonalR`)
- Test: `tests/test_miost_operators.py`

**Acceptance Criteria:**
- [ ] `build_g(spec, els, obs_lon, obs_lat, obs_t)` returns CSR whose dense form equals `spec.evaluate` at the obs points (small case, exact)
- [ ] Adjoint identity `⟨Gη, r⟩ == ⟨η, Gᵀr⟩` at machine precision (seam b)
- [ ] `DiagonalQ(rho, q_slope)`: `q_p = rho * R_REF * (lam_p/LAM_REF)**q_slope`; λ_ref gauge-inertness asserted numerically (seam c)
- [ ] Representer `Γ q Γᵀ` row at box center has a negative lobe (Tier 2)

**Verify:** `pixi run pytest tests/test_miost_operators.py -q`

**Steps:**

- [ ] **Step 1: Failing tests**

```python
import numpy as np
import pytest

from sverdrup.methods.miost_basis import (
    BasisSpec, DiagonalQ, LAM_REF, R_REF, build_g, lonlat_to_km,
)

SPEC = BasisSpec(alpha=1.5, l_t_days=10.0)  # coarse alpha keeps the test small
RNG = np.random.default_rng(7)


def _small_obs(n: int = 40):
    lon = RNG.uniform(297, 303, n); lat = RNG.uniform(35, 41, n); t = RNG.uniform(5, 55, n)
    return lon, lat, t


def test_g_matches_dense_evaluate() -> None:
    """CSR assembly == dense analytic evaluation (bug: wrong sparsity window/offset)."""
    els = SPEC.elements_for_window(0.0)
    lon, lat, t = _small_obs()
    g = build_g(SPEC, els, lon, lat, t)
    x, y = lonlat_to_km(lon, lat)
    dense = SPEC.evaluate(els, x, y, t)
    np.testing.assert_allclose(g.toarray(), dense, atol=1e-14)


def test_adjoint_identity() -> None:
    """Seam (b): <G eta, r> == <eta, G^T r> to machine precision."""
    els = SPEC.elements_for_window(0.0)
    lon, lat, t = _small_obs()
    g = build_g(SPEC, els, lon, lat, t)
    eta = RNG.standard_normal(g.shape[1]); r = RNG.standard_normal(g.shape[0])
    assert (g @ eta) @ r == pytest.approx(eta @ (g.T @ r), rel=1e-12)


def test_q_lam_ref_gauge_inert() -> None:
    """Seam (c)/D8: changing lam_ref with Q_scale retuned analytically -> identical q.

    q_p = rho*R_REF*(lam/ref)^s ; ref 300->400 is offset by rho' = rho*(400/300)^s.
    """
    q1 = DiagonalQ(rho=10.0, q_slope=2.0, lam_ref=300.0).variances(SPEC)
    q2 = DiagonalQ(rho=10.0 * (400.0 / 300.0) ** 2.0, q_slope=2.0, lam_ref=400.0).variances(SPEC)
    np.testing.assert_allclose(q1, q2, rtol=1e-12)


def test_representer_negative_lobe() -> None:
    """Tier 2 (U2022 Fig. 4): the equivalent covariance row crosses zero."""
    els = SPEC.elements_for_window(0.0)
    q = DiagonalQ(rho=10.0, q_slope=2.0).variances_for(els)
    xs = np.linspace(0.0, 850.0, 200)
    row = SPEC.evaluate(els, xs, np.full(200, 550.0), np.full(200, 30.0))
    center = SPEC.evaluate(els, np.array([425.0]), np.array([550.0]), np.array([30.0]))
    rep = (center * q) @ row.T  # (1, 200)
    assert rep[0].max() > 0 and rep[0].min() < 0
```

- [ ] **Step 2: Run → fail.**

- [ ] **Step 3: Implement** (append to `miost_basis.py`)

```python
from scipy import sparse  # type: ignore[import-untyped]


def build_g(
    spec: BasisSpec, els: Elements, lon: np.ndarray, lat: np.ndarray, t_days: np.ndarray
) -> sparse.csr_matrix:
    """Assemble CSR G analytically: rows=obs, cols=elements. Never via a gridded H."""
    x, y = lonlat_to_km(np.asarray(lon, float), np.asarray(lat, float))
    t = np.asarray(t_days, float)
    rows, cols, vals = [], [], []
    # bucket elements by support box for candidate pruning (coarse uniform grid per scale)
    for p in range(els.x_km.size):  # NOTE: replace with per-scale KD bucketing if slow
        hw = els.half_width_km[p]
        m = (
            (np.abs(x - els.x_km[p]) < hw)
            & (np.abs(y - els.y_km[p]) < hw)
            & (np.abs(t - els.t_days[p]) < spec.l_t_days)
        )
        idx = np.nonzero(m)[0]
        if idx.size == 0:
            continue
        dx = (x[idx] - els.x_km[p]) / hw
        dy = (y[idx] - els.y_km[p]) / hw
        dtt = (t[idx] - els.t_days[p]) / spec.l_t_days
        v = (
            np.cos(els.kx[p] * (x[idx] - els.x_km[p]) + els.ky[p] * (y[idx] - els.y_km[p]) + els.phase[p])
            * np.cos(0.5 * np.pi * dx) * np.cos(0.5 * np.pi * dy) * np.cos(0.5 * np.pi * dtt)
        )
        rows.append(idx); cols.append(np.full(idx.size, p)); vals.append(v)
    if not rows:
        return sparse.csr_matrix((x.size, els.x_km.size))
    return sparse.csr_matrix(
        (np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
        shape=(x.size, els.x_km.size),
    )


def build_s(spec: BasisSpec, els: Elements, grid_lon: np.ndarray, grid_lat: np.ndarray) -> sparse.csr_matrix:
    """SPATIAL basis matrix at grid nodes (fork-1 hardening 2): carrier*spatial taper only."""
    x, y = lonlat_to_km(grid_lon, grid_lat)
    rows, cols, vals = [], [], []
    for p in range(els.x_km.size):
        hw = els.half_width_km[p]
        m = (np.abs(x - els.x_km[p]) < hw) & (np.abs(y - els.y_km[p]) < hw)
        idx = np.nonzero(m)[0]
        if idx.size == 0:
            continue
        v = (
            np.cos(els.kx[p] * (x[idx] - els.x_km[p]) + els.ky[p] * (y[idx] - els.y_km[p]) + els.phase[p])
            * np.cos(0.5 * np.pi * (x[idx] - els.x_km[p]) / hw)
            * np.cos(0.5 * np.pi * (y[idx] - els.y_km[p]) / hw)
        )
        rows.append(idx); cols.append(np.full(idx.size, p)); vals.append(v)
    return sparse.csr_matrix(
        (np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
        shape=(x.size, els.x_km.size),
    )


def temporal_taper(spec: BasisSpec, els: Elements, day: float) -> np.ndarray:
    """Per-element temporal taper at ``day`` (day map = S @ (eta * taper))."""
    return np.asarray(_cos_tap((day - els.t_days) / spec.l_t_days))


@dataclass(frozen=True)
class DiagonalQ:
    """Prior variances q_p = rho * R_REF * (lam_p/lam_ref)^q_slope (spec §2.2, gap-#3 flag)."""

    rho: float
    q_slope: float
    lam_ref: float = LAM_REF
    r_ref: float = R_REF

    def variances_for(self, els: Elements) -> np.ndarray:
        lam = np.asarray(LADDER)[els.identity[:, 0]]
        return np.asarray(self.rho * self.r_ref * (lam / self.lam_ref) ** self.q_slope)

    def variances(self, spec: BasisSpec) -> np.ndarray:
        """Per-RUNG variances (gauge test helper)."""
        lam = np.asarray(spec.ladder)
        return np.asarray(self.rho * self.r_ref * (lam / self.lam_ref) ** self.q_slope)


@dataclass(frozen=True)
class DiagonalR:
    """Scalar observation-error variance (Stage A: R = R_REF, s == 1)."""

    variance: float = R_REF
```

NOTE: the per-element loop in `build_g`/`build_s` is O(n_elements · n_obs) masking — acceptable for Stage-A boxes at coarse test sizes but MUST be bucketed for production (per scale, bin obs into cells of size αλ; only neighboring cells' elements touch an obs). Implement the bucketing in this task if the α=1.0 60-d window assembly exceeds ~60 s; the tests above are size-independent.

- [ ] **Step 4: Run → pass.** **Step 5: Commit** — `git commit -m "feat(miost): CSR G/S/Q/R builders + adjoint/gauge/representer tests (seams b,c; Tier 2)"`

### Task 4: Multi-RHS Jacobi-PCG solver

**Goal:** `MiostSolver` solving `(GᵀR⁻¹G + Q⁻¹)X = B` matrix-free over stored CSR G, Jacobi-preconditioned, convergence-reported; RHS-agnostic (seam a).

**Files:**
- Create: `src/sverdrup/methods/miost_solver.py`
- Test: `tests/test_miost_solver.py`

**Acceptance Criteria:**
- [ ] `solve(B)` accepts (n_coef,) or (n_coef, k) arbitrary RHS not derived from y (seam a)
- [ ] Dense-vs-PCG agreement on a small A at rtol 1e-8 (Tier 1 (iii))
- [ ] Jacobi preconditioner = `diag(GᵀR⁻¹G) + Q⁻¹` (computed as CSR column sum of squares / R)
- [ ] Report (iterations, final relative residual per RHS) returned, never swallowed
- [ ] `pcg_rtol=1e-6`, `pcg_maxiter=500` defaults, named

**Verify:** `pixi run pytest tests/test_miost_solver.py -q`

**Steps:**

- [ ] **Step 1: Failing tests**

```python
import numpy as np
import pytest
from scipy import sparse

from sverdrup.methods.miost_solver import MiostSolver

RNG = np.random.default_rng(3)


def _small_system(n_obs=60, n_coef=25):
    g = sparse.random(n_obs, n_coef, density=0.3, random_state=3, format="csr")
    r = np.full(n_obs, 0.01)
    q = np.full(n_coef, 2.0)
    return g, r, q


def test_pcg_matches_dense() -> None:
    """Tier 1 (iii): PCG solution == dense solve of the same normal equations."""
    g, r, q = _small_system()
    a_dense = (g.T @ sparse.diags(1 / r) @ g).toarray() + np.diag(1 / q)
    b = RNG.standard_normal(g.shape[1])
    s = MiostSolver(g, r_diag=r, q_diag=q, pcg_rtol=1e-12)
    x, report = s.solve(b)
    np.testing.assert_allclose(x, np.linalg.solve(a_dense, b), rtol=1e-8)
    assert report.iterations[0] > 0 and report.final_rel_residual[0] <= 1e-10


def test_solve_is_rhs_agnostic_multi_rhs() -> None:
    """Seam (a): arbitrary B (n_coef, 3) not derived from any y; columns independent."""
    g, r, q = _small_system()
    s = MiostSolver(g, r_diag=r, q_diag=q)
    b = RNG.standard_normal((g.shape[1], 3))
    x, _ = s.solve(b)
    x0, _ = s.solve(b[:, 0])
    np.testing.assert_allclose(x[:, 0], x0, rtol=1e-8)


def test_zero_obs_total() -> None:
    """n_obs=0 -> A = Q^-1, solve returns q*b exactly (degenerate-obs totality §4.3)."""
    g = sparse.csr_matrix((0, 10)); q = np.full(10, 2.0)
    s = MiostSolver(g, r_diag=np.zeros(0), q_diag=q)
    b = RNG.standard_normal(10)
    x, _ = s.solve(b)
    np.testing.assert_allclose(x, q * b, rtol=1e-10)
```

- [ ] **Step 2: Run → fail.**

- [ ] **Step 3: Implement**

```python
"""Multi-RHS Jacobi-preconditioned CG on the MIOST reduced normal equations (spec §2.4)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import sparse  # type: ignore[import-untyped]

PCG_RTOL = 1e-6
PCG_MAXITER = 500


@dataclass(frozen=True)
class ConvergenceReport:
    """Per-RHS iteration counts + final relative residuals (surfaced, never swallowed)."""

    iterations: np.ndarray
    final_rel_residual: np.ndarray


class MiostSolver:
    """Solve (G^T R^-1 G + Q^-1) X = B with stored CSR G; RHS-agnostic (seam a)."""

    def __init__(
        self,
        g: sparse.csr_matrix,
        r_diag: np.ndarray,
        q_diag: np.ndarray,
        pcg_rtol: float = PCG_RTOL,
        pcg_maxiter: int = PCG_MAXITER,
    ) -> None:
        self.g = g
        self.r_inv = 1.0 / np.asarray(r_diag, float) if r_diag.size else r_diag
        self.q_inv = 1.0 / np.asarray(q_diag, float)
        self.pcg_rtol = pcg_rtol
        self.pcg_maxiter = pcg_maxiter
        # Jacobi preconditioner: diag(G^T R^-1 G) + Q^-1 = sum_i g_ip^2 / r_i + 1/q_p
        g2 = g.copy(); g2.data = g2.data**2
        self._m_inv = 1.0 / (g2.T @ self.r_inv + self.q_inv) if g.shape[0] else 1.0 / self.q_inv

    def apply_a(self, x: np.ndarray) -> np.ndarray:
        """A-apply in two SpMVs (G then G^T) + diagonal."""
        if self.g.shape[0] == 0:
            return np.asarray(self.q_inv * x.T).T if x.ndim > 1 else self.q_inv * x
        gx = self.g @ x
        gtx = self.g.T @ (self.r_inv[:, None] * gx if gx.ndim > 1 else self.r_inv * gx)
        return gtx + (self.q_inv[:, None] * x if x.ndim > 1 else self.q_inv * x)

    def solve(self, b: np.ndarray) -> tuple[np.ndarray, ConvergenceReport]:
        """Blocked PCG; B is (n,) or (n, k); columns solved jointly, converged per-column."""
        b2 = np.atleast_2d(np.asarray(b, float).T).T  # (n, k)
        x = np.zeros_like(b2)
        r = b2 - self.apply_a(x)
        z = self._m_inv[:, None] * r
        p = z.copy()
        rz = np.einsum("ij,ij->j", r, z)
        b_norm = np.maximum(np.linalg.norm(b2, axis=0), 1e-300)
        iters = np.zeros(b2.shape[1], dtype=int)
        for it in range(1, self.pcg_maxiter + 1):
            ap = self.apply_a(p)
            alpha = rz / np.maximum(np.einsum("ij,ij->j", p, ap), 1e-300)
            x += alpha * p
            r -= alpha * ap
            rel = np.linalg.norm(r, axis=0) / b_norm
            active = rel > self.pcg_rtol
            iters[active] = it
            if not active.any():
                break
            z = self._m_inv[:, None] * r
            rz_new = np.einsum("ij,ij->j", r, z)
            p = z + (rz_new / np.maximum(rz, 1e-300)) * p
            rz = rz_new
        report = ConvergenceReport(iters, np.linalg.norm(r, axis=0) / b_norm)
        return (x[:, 0], report) if np.asarray(b).ndim == 1 else (x, report)


def rhs_from_obs(g: sparse.csr_matrix, r_diag: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Seam (b): b(y) = G^T R^-1 y as its own first-class unit."""
    return np.asarray(g.T @ (y / r_diag))
```

- [ ] **Step 4: Run → pass.** **Step 5: Commit** — `git commit -m "feat(miost): multi-RHS Jacobi-PCG solver + convergence report (seam a; Tier-1 dense-vs-PCG)"`

### Task 5: Tier-1 duality oracle

**Goal:** Prove the reduced path solves the same linear-Gaussian problem as dense obs-space OI with B = ΓQΓᵀ (U2021 Eq. 2 ↔ Eq. 15).

**Files:**
- Test: `tests/test_miost_duality_oracle.py`

**Acceptance Criteria:**
- [ ] On a small synthetic (~50 obs, 2-rung ladder), `Γ_grid η^a` == dense `B_gx Hᵀ (H B Hᵀ + R)⁻¹ y` at rtol 1e-8

**Verify:** `pixi run pytest tests/test_miost_duality_oracle.py -q`

**Steps:**

- [ ] **Step 1+3: Write the oracle test** (it exercises only Tasks 2–4 code; no new impl)

```python
"""Tier-1 duality oracle: reduced normal equations == obs-space OI with B = Gamma Q Gamma^T."""

import numpy as np

from sverdrup.methods.miost_basis import BasisSpec, DiagonalQ, build_g, lonlat_to_km
from sverdrup.methods.miost_solver import MiostSolver, rhs_from_obs

RNG = np.random.default_rng(11)


def test_duality_oracle_u2021_eq2_vs_eq15() -> None:
    spec = BasisSpec(alpha=1.5, l_t_days=10.0, ladder=(320.0, 452.548))  # 2 rungs, tiny
    els = spec.elements_for_window(0.0)
    n = 50
    lon = RNG.uniform(296, 304, n); lat = RNG.uniform(34, 42, n); t = RNG.uniform(10, 50, n)
    y = RNG.standard_normal(n) * 0.1
    r = np.full(n, 0.01)
    q = DiagonalQ(rho=20.0, q_slope=2.0).variances_for(els)

    g = build_g(spec, els, lon, lat, t)               # obs-side Gamma (= H Gamma, H analytic)
    # query points: a coarse grid at day 30
    qlon, qlat = np.meshgrid(np.linspace(296, 304, 9), np.linspace(34, 42, 9))
    qx, qy = lonlat_to_km(qlon.ravel(), qlat.ravel())
    gamma_q = spec.evaluate(els, qx, qy, np.full(qx.size, 30.0))  # (n_query, n_elem)

    # Eq. 2: x^a = B_qd (B_dd + R)^-1 y  with  B = Gamma Q Gamma^T
    gd = g.toarray()
    b_dd = gd * q @ gd.T
    b_qd = gamma_q * q @ gd.T
    dense_map = b_qd @ np.linalg.solve(b_dd + np.diag(r), y)

    # Eq. 15: eta^a = (G^T R^-1 G + Q^-1)^-1 G^T R^-1 y ; map = Gamma eta^a
    eta, _ = MiostSolver(g, r_diag=r, q_diag=q, pcg_rtol=1e-13).solve(rhs_from_obs(g, r, y))
    np.testing.assert_allclose(gamma_q @ eta, dense_map, rtol=1e-8, atol=1e-12)
```

- [ ] **Step 2: Run → must PASS immediately if Tasks 2–4 are correct; if it fails, the bug is real — fix Tasks 2–4, not the oracle.**

- [ ] **Step 3: Commit** — `git commit -m "test(miost): Tier-1 duality oracle — reduced path == dense obs-space OI with B=GammaQGamma^T"`

### Task 6: WindowPlan + temporal blend

**Goal:** Window placement (designed at L_t_max=12) and the linear temporal blend with partition of unity.

**Files:**
- Create: `src/sverdrup/methods/miost_windows.py`
- Test: `tests/test_miost_windows.py`

**Acceptance Criteria:**
- [ ] Windows `s_k = −18 + 45k, k=0..8` (i.e. [−18,42] … [342,402]); ids stable strings
- [ ] Every output day 0..364: covering windows found; full-weight days have two-sided slot support at L_t=12; first-slot support ≥ −31 (obs start; ~1-day slack recorded)
- [ ] Blend weights: day in overlap → (left, right) = ((s_k+60−d)/15, (d−s_{k+1})/15); sum to 1; outside overlap weight 1

**Verify:** `pixi run pytest tests/test_miost_windows.py -q`

**Steps:**

- [ ] **Step 1: Failing tests**

```python
import numpy as np
import pytest

from sverdrup.methods.miost_windows import WindowPlan

PLAN = WindowPlan()  # run-constants from miost_basis


def test_placement_s_k() -> None:
    starts = [w.start_day for w in PLAN.windows]
    assert starts == [-18.0 + 45.0 * k for k in range(9)]


def test_every_output_day_supported_at_lt_ceiling() -> None:
    """Constraint (i) at L_t_max=12: slots within [d-12, d+12] inside the window,
    and slot support inside obs span [-31, 395]. Bug: placement off by one stride."""
    for d in range(0, 365):
        wins = PLAN.covering(float(d))
        assert 1 <= len(wins) <= 2
        w = wins[0] if len(wins) == 1 else max(wins, key=lambda w: PLAN.weight(w, float(d)))
        assert w.start_day <= d - 12 or w is PLAN.windows[0]
        assert w.start_day + 60 >= d + 12 or w is PLAN.windows[-1]
    assert PLAN.windows[0].start_day - 12 >= -31 + 1 - 1e-9  # 1-day slack, recorded


def test_blend_partition_of_unity() -> None:
    for d in np.linspace(-18, 364, 500):
        wins = PLAN.covering(float(d))
        total = sum(PLAN.weight(w, float(d)) for w in wins)
        assert total == pytest.approx(1.0)


def test_blend_linear_in_overlap() -> None:
    """Day 30 lies in w0/w1 overlap [27, 42]: w0 weight (42-30)/15 = 0.8."""
    w0, w1 = PLAN.covering(30.0)
    assert PLAN.weight(w0, 30.0) == pytest.approx(0.8)
    assert PLAN.weight(w1, 30.0) == pytest.approx(0.2)
```

- [ ] **Step 2: Run → fail.**

- [ ] **Step 3: Implement**

```python
"""Temporal WindowPlan + linear blend (spec §4.1; designed at L_t_max=12)."""

from __future__ import annotations

from dataclasses import dataclass, field

from sverdrup.methods.miost_basis import STRIDE_DAYS, V_DAYS, W_DAYS


@dataclass(frozen=True)
class Window:
    start_day: float

    @property
    def end_day(self) -> float:
        return self.start_day + W_DAYS

    @property
    def id(self) -> str:
        return f"w{self.start_day:+08.1f}+{W_DAYS:.0f}"


@dataclass(frozen=True)
class WindowPlan:
    """s_k = -18 + 45k, k = 0..8 (covers outputs 0..364 inside obs span [-31, 395])."""

    first_start: float = -18.0
    n_windows: int = 9
    windows: tuple[Window, ...] = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "windows",
            tuple(Window(self.first_start + STRIDE_DAYS * k) for k in range(self.n_windows)),
        )

    def covering(self, day: float) -> list[Window]:
        return [w for w in self.windows if w.start_day <= day <= w.end_day]

    def weight(self, w: Window, day: float) -> float:
        """Linear, proportional to boundary distance; partition of unity over covering."""
        wins = self.covering(day)
        if len(wins) == 1:
            return 1.0
        left, right = wins  # ordered by start
        if w is left or w.id == left.id:
            return (left.end_day - day) / V_DAYS
        return (day - right.start_day) / V_DAYS
```

- [ ] **Step 4: Run → pass.** **Step 5: Commit** — `git commit -m "feat(miost): WindowPlan at L_t ceiling + linear temporal blend (D3/fold A)"`

### Task 7: POINT distribution, capability error, persisted state

**Goal:** `MiostPointDistribution` (mean via analytic evaluation; variance-family calls raise), `CapabilityNotAvailableError`, and coefficient persistence (seams d + e).

**Files:**
- Modify: `src/sverdrup/core/distribution.py` (add exception at top; protocols untouched)
- Create: `src/sverdrup/methods/miost.py` (distribution + persistence half)
- Test: `tests/test_miost_distribution.py`

**Acceptance Criteria:**
- [ ] `marginal_variance()` / `covariance()` / `sample()` raise `CapabilityNotAvailableError` with the capability name in the message — never None/NaN
- [ ] `save_state(path)` / `load_state(path)` round-trips (η per window + basis key + window ids); reloaded object reproduces the day map bit-identically
- [ ] Arbitrary-point query `mean_at(points)` equals direct analytic evaluation

**Verify:** `pixi run pytest tests/test_miost_distribution.py -q`

**Steps:**

- [ ] **Step 1: Failing tests**

```python
import numpy as np
import pytest

from sverdrup.core.distribution import CapabilityNotAvailableError
from sverdrup.methods.miost import MiostPointDistribution
# construction helper: build a tiny solved state via the Task-8 Miost internals or directly:
from tests._miost_fixtures import tiny_point_distribution  # built in this task's test module


def test_capability_calls_raise_loud() -> None:
    d = tiny_point_distribution()
    for call in (d.marginal_variance, lambda: d.covariance(P, P), lambda: d.sample(2, 0)):
        with pytest.raises(CapabilityNotAvailableError, match="POINT"):
            call()


def test_persist_round_trip(tmp_path) -> None:
    d = tiny_point_distribution()
    p = tmp_path / "state.npz"
    d.save_state(p)
    d2 = MiostPointDistribution.load_state(p)
    np.testing.assert_array_equal(np.asarray(d.mean), np.asarray(d2.mean))
```

(`tests/_miost_fixtures.py` builds a 2-rung, α=1.5, 40-obs solved state through the Task 2–4 public API — same construction as the duality oracle; write it in this task, complete code, reused by later tasks.)

- [ ] **Step 2: Run → fail.**

- [ ] **Step 3: Implement.** In `core/distribution.py` (top, after imports — protocols untouched):

```python
class CapabilityNotAvailableError(RuntimeError):
    """A distribution was asked for an uncertainty product its capability cannot emit."""
```

In `methods/miost.py`:

```python
@dataclass
class MiostPointDistribution:
    """POINT predictive: mean field + analytic-eval queries; variance family raises (seam e)."""

    grid: GridSpec
    mean: Field
    provenance: UncertaintyProvenance
    time_days: float
    _spec: BasisSpec
    _etas: dict[str, np.ndarray]        # window_id -> eta
    _window_starts: dict[str, float]

    def marginal_variance(self) -> Field:
        raise CapabilityNotAvailableError("miost Stage A is POINT: no marginal variance")

    def covariance(self, a: Points, b: Points) -> np.ndarray:
        raise CapabilityNotAvailableError("miost Stage A is POINT: no covariance")

    def sample(self, m: int, seed: Seed) -> np.ndarray:
        raise CapabilityNotAvailableError("miost Stage A is POINT: no samples")

    def regrid(self, target: GridSpec) -> MiostPointDistribution: ...  # evaluate mean_at on target

    def mean_at(self, pts: Points) -> np.ndarray:
        """Blend-weighted analytic evaluation at arbitrary (lon, lat, t) points (seam d)."""
        ...

    def save_state(self, path: Path) -> None:
        np.savez(path, basis_key=self._spec.key(), time_days=self.time_days,
                 mean=np.asarray(self.mean), grid_lon=..., grid_lat=...,
                 **{f"eta_{wid}": eta for wid, eta in self._etas.items()},
                 **{f"start_{wid}": s for wid, s in self._window_starts.items()})

    @classmethod
    def load_state(cls, path: Path) -> MiostPointDistribution: ...
```

Implementer: `mean_at` = for each covering window, enumerate its elements (`elements_for_window`), evaluate analytically at the points, dot with η, blend with `WindowPlan.weight`. `regrid` = `mean_at` on the target grid nodes. `load_state` reconstructs `BasisSpec` from the stored basis-key fields (store `alpha`/`l_t_days` as npz scalars too — add them to `save_state`). Full round-trip is the acceptance test; keep the npz layout flat.

- [ ] **Step 4: Run → pass.** **Step 5: Commit** — `git commit -m "feat(miost): POINT distribution + CapabilityNotAvailableError + coefficient persistence (seams d,e)"`

### Task 8: Window-cache `Miost` Method + registry

**Goal:** The `Miost` Method: full-obs re-subsetting per window, cache with obs-fingerprint key, S-matrix day projection, blend, `parameter_space()`, registry entry (fork-1 hardenings 1–4).

**Files:**
- Modify: `src/sverdrup/methods/miost.py`
- Modify: `src/sverdrup/methods/registry.py` (add `"miost": Miost`)
- Test: `tests/test_miost_method.py`

**Acceptance Criteria:**
- [ ] `Miost().solve(obs, grid, params, time_days=d)` returns `MiostPointDistribution`; protocol-compliant (`isinstance(Miost(), Method)`)
- [ ] Cache key = (window_id, params_key, blake2b obs fingerprint); repeat-day and two-days-one-window solves == fresh-instance solves exactly; cache-on/off identical
- [ ] Loud `ValueError` if obs don't span [window_start − L_t, window_end + L_t] (clipped to obs data span)
- [ ] `params_key` contains α, ρ, q_slope, L_t, pcg_rtol, basis key (seam f test)
- [ ] Mission-absent and zero-obs windows produce finite maps (spec §4.3)
- [ ] `parameter_space()` = boxes {spacing_alpha (0.5,1.5), log10_rho (−2,3), q_slope (0,4), l_t_days (5,12)}

**Verify:** `pixi run pytest tests/test_miost_method.py -q`

**Steps:**

- [ ] **Step 1: Failing tests** (key ones; use `tests/_miost_fixtures.py` synthetic obs)

```python
def test_cache_repeat_day_equals_fresh() -> None:
    m1, m2 = Miost(), Miost()
    d_a = m1.solve(OBS, GRID, PARAMS, time_days=30.0)
    _ = m1.solve(OBS, GRID, PARAMS, time_days=35.0)   # same window pair, cache warm
    d_b = m1.solve(OBS, GRID, PARAMS, time_days=30.0)  # repeat day
    d_fresh = m2.solve(OBS, GRID, PARAMS, time_days=30.0)
    np.testing.assert_array_equal(np.asarray(d_a.mean), np.asarray(d_b.mean))
    np.testing.assert_array_equal(np.asarray(d_a.mean), np.asarray(d_fresh.mean))


def test_obs_fingerprint_busts_cache() -> None:
    """Partial-obs caller -> different fingerprint -> cache MISS (wrong-becomes-slow)."""
    m = Miost()
    _ = m.solve(OBS, GRID, PARAMS, time_days=30.0)
    half = _subset_first_half(OBS)
    with pytest.raises(ValueError, match="span"):
        m.solve(half_missing_margin, GRID, PARAMS, time_days=30.0)  # span assert fires
    # a DIFFERENT full-span obs set must not hit the old cache entry:
    d2 = m.solve(perturb_values(OBS), GRID, PARAMS, time_days=30.0)
    assert not np.array_equal(np.asarray(d2.mean), np.asarray(_.mean))


def test_zero_obs_window_finite() -> None:
    d = Miost().solve(EMPTY_OBS, GRID, PARAMS, time_days=30.0)
    assert np.isfinite(np.asarray(d.mean)).all()


def test_params_key_serializes_contract() -> None:
    key = Miost()._params_key(PARAMS, GRID)
    for token in ("alpha", "rho", "q_slope", "l_t", "pcg_rtol", "ladder"):
        assert token in key
```

- [ ] **Step 2: Run → fail.**

- [ ] **Step 3: Implement `Miost`** (core shape; full class in file):

```python
class Miost:
    """MIOST window-cache Method (spec §4.2). native_capability = POINT (Stage A)."""

    native_capability = UncertaintyCapability.POINT

    def __init__(self) -> None:
        self._plan = WindowPlan()
        self._eta_cache: dict[tuple[str, str, str], np.ndarray] = {}
        self._s_cache: OrderedDict[tuple[str, str], tuple[Elements, sparse.csr_matrix]] = OrderedDict()

    def parameter_space(self) -> ParameterSpace:
        return ParameterSpace(bounds={
            "spacing_alpha": (0.5, 1.5), "log10_rho": (-2.0, 3.0),
            "q_slope": (0.0, 4.0), "l_t_days": (5.0, 12.0),
        })

    def solve(self, obs, grid, params, time_days):
        spec = self._spec_from(params, grid)
        pk = self._params_key(params, grid)
        fp = _obs_fingerprint(obs)
        wins = self._plan.covering(time_days)
        parts, weights = [], []
        for w in wins:
            eta = self._solve_window(w, spec, pk, fp, obs)
            els, s = self._s_matrix(w, spec, pk, grid)
            day_map = s @ (eta * temporal_taper(spec, els, time_days))
            parts.append(day_map); weights.append(self._plan.weight(w, time_days))
        mean = sum(wgt * p for wgt, p in zip(weights, parts)).reshape(grid.shape)
        return MiostPointDistribution(grid=grid, mean=mean, provenance=..., time_days=time_days,
                                      _spec=spec, _etas={...}, _window_starts={...})

    def _solve_window(self, w, spec, pk, fp, obs):
        key = (w.id, pk, fp)
        if key in self._eta_cache:
            return self._eta_cache[key]
        sub = _window_obs(obs, w, spec.l_t_days)   # asserts span; subsets [start-Lt, end+Lt]
        els = spec.elements_for_window(w.start_day)
        g = build_g(spec, els, ...sub coords...)
        q = DiagonalQ(rho=10 ** params["log10_rho"], q_slope=...).variances_for(els)
        solver = MiostSolver(g, r_diag=np.full(len(sub), R_REF), q_diag=q)
        eta, report = solver.solve(rhs_from_obs(g, np.full(len(sub), R_REF), sub_values))
        log the report (iterations / residual); del g  # G freed (hardening 2)
        self._eta_cache[key] = eta
        return eta
```

`_obs_fingerprint`: `hashlib.blake2b` over `coords().tobytes() + values().tobytes()`, 16-byte digest hex. `_window_obs`: subset to `[start − L_t, end + L_t]`; raise `ValueError("obs do not span window ... — pass the full obs (wide temporal_half_window_days)")` if the passed obs' time range does not cover that interval clipped to `[-31, 395]`. `_s_cache` keyed (window_id, pk): keep max 2 entries (OrderedDict, popitem(last=False)). Registry: add import + `"miost": Miost` line.

- [ ] **Step 4: Run → pass; also `pixi run pytest tests/test_miost_distribution.py tests/test_miost_duality_oracle.py -q` (no regressions).**

- [ ] **Step 5: Commit** — `git commit -m "feat(miost): window-cache Method + registry (fork-1 hardenings; seams e,f)"`

### Task 9: Capability-derived bars + capability-routed scorer

**Goal:** `bars_for(capability)`; scorer routes mean-only vs mean+var by `native_capability`; `_assemble_scores` var-optional; fail-loud calibration test.

**Files:**
- Modify: `src/sverdrup/application/tuning/objective.py`
- Modify: `src/sverdrup/application/tuning/scorer.py`
- Test: `tests/test_capability_conditioning.py`

**Acceptance Criteria:**
- [ ] `bars_for(POINT)` = (µ bar,); `bars_for(MARGINAL_VARIANCE | COVARIANCE | SAMPLES)` includes the coverage bar (both-directions test)
- [ ] Scorer with a POINT method produces scores WITHOUT `coverage_1sigma` and never calls `marginal_variance` (fold B both-directions test: a ≥MARGINAL method still routes through the var path)
- [ ] `coverage(...)` on a POINT distribution raises `CapabilityNotAvailableError` (fail-loud test)
- [ ] Existing OI/GMRF paths unchanged (`_default_bars` still the default; full suite green)

**Verify:** `pixi run pytest tests/test_capability_conditioning.py -q && pixi run test`

**Steps:**

- [ ] **Step 1: Failing tests**

```python
from sverdrup.application.tuning.objective import bars_for
from sverdrup.core.types import UncertaintyCapability as UC


def test_bars_for_point_omits_coverage() -> None:
    bars = bars_for(UC.POINT)
    assert [b.metric for b in bars] == ["mu_score"]


def test_bars_for_marginal_and_up_include_coverage() -> None:
    for cap in (UC.MARGINAL_VARIANCE, UC.COVARIANCE, UC.SAMPLES):
        assert "coverage_1sigma" in [b.metric for b in bars_for(cap)]


def test_scorer_routes_point_mean_only(monkeypatch) -> None:
    """POINT -> run_challenge_map (mean-only); >=MARGINAL -> run_mean_var_maps.
    Monkeypatch both runners to record which was called; use 'trivial' + 'miost' stubs."""
    ...


def test_assemble_scores_var_optional() -> None:
    s = _assemble_scores(ssh_a=..., mean_interp=..., var_interp=None, ..., mu_bar=0.85)
    assert "coverage_1sigma" not in s and "mu_score" in s
```

- [ ] **Step 2: Run → fail.**

- [ ] **Step 3: Implement.** objective.py — add (keep `_default_bars` for existing callers):

```python
def bars_for(capability: UncertaintyCapability) -> tuple[HardBar, ...]:
    """Capability-derived hard bars (spec §5.3): coverage iff capability can emit variance."""
    bars: tuple[HardBar, ...] = (HardBar("mu_score", ">=", BASELINE_BAR_MU),)
    if capability.value >= UncertaintyCapability.MARGINAL_VARIANCE.value:
        bars += (HardBar("coverage_1sigma", "within", _COVERAGE_TARGET, _COVERAGE_TOL),)
    return bars
```

scorer.py — `_assemble_scores(var_interp: np.ndarray | None, ...)`: wrap the coverage line in `if var_interp is not None:`. `ValidationTrackScorer.score`: before the tempdir block,

```python
from sverdrup.methods.registry import METHODS
cap = METHODS[method_name]().native_capability
```

if `cap is UncertaintyCapability.POINT`: call `run_challenge_map(...)` (mean only), interp mean only, pass `var_interp=None`; else the existing `run_mean_var_maps` path verbatim.

- [ ] **Step 4: Run new tests + FULL suite** (`pixi run test`) — OI/GMRF paths must be untouched.

- [ ] **Step 5: Commit** — `git commit -m "feat(tuning): capability-derived bars + capability-routed scorer (folds 1+B; fail-loud POINT)"`

### Task 10: StoredGFeasibility + CompositeFeasibility + reason recording

**Goal:** Resource predicate priced by `miost_sizing`, composing with existing predicates; infeasible reason lands in `TrialRecord.exclusion_reason`.

**Files:**
- Modify: `src/sverdrup/application/tuning/feasibility.py`
- Modify: `src/sverdrup/application/tuning/loop.py` (lines 97–100)
- Test: `tests/test_stored_g_feasibility.py`

**Acceptance Criteria:**
- [ ] `StoredGFeasibility(n_obs_max, budget_bytes=8e9, n_concurrent=1, n_dir=8, lam_min=80, lam_max=905)`: `feasible(params, ...)` False iff `n_concurrent * predicted_bytes > budget`
- [ ] `predicted_bytes(params)` == `nnz_g(n_obs_max, alpha, n_dir, lam_min, lam_max) * 12` (single-arithmetic test vs `miost_sizing` — no local formula)
- [ ] No L_t term (predicted bytes identical across l_t_days values)
- [ ] `CompositeFeasibility((a, b))` = logical AND; protocol unchanged
- [ ] `tune()` records `exclusion_reason=predicate.explain(params)` for infeasible trials when the predicate has `explain`; existing predicates (no `explain`) → reason None (backward compatible)

**Verify:** `pixi run pytest tests/test_stored_g_feasibility.py -q && pixi run test`

**Steps:**

- [ ] **Step 1: Failing tests**

```python
def test_predicted_bytes_is_sizing_arithmetic() -> None:
    p = StoredGFeasibility(n_obs_max=57_000, budget_bytes=8e9)
    from sverdrup.methods.miost_sizing import nnz_g
    expected = nnz_g(57_000, alpha=0.75, n_dir=8, lam_min=80.0, lam_max=905.0) * 12
    assert p.predicted_bytes({"spacing_alpha": 0.75}) == expected


def test_l_t_free() -> None:
    p = StoredGFeasibility(n_obs_max=57_000)
    a = p.predicted_bytes({"spacing_alpha": 1.0, "l_t_days": 5.0})
    b = p.predicted_bytes({"spacing_alpha": 1.0, "l_t_days": 12.0})
    assert a == b


def test_budget_boundary_and_reason() -> None:
    p = StoredGFeasibility(n_obs_max=57_000, budget_bytes=8e9)
    fine = {"spacing_alpha": 0.5}
    assert not p.feasible(fine, GEOM, frozenset())
    assert "stored-G" in p.explain(fine) and "8.0e+09" in p.explain(fine)


def test_composite_and_loop_reason() -> None:
    comp = CompositeFeasibility((StoredGFeasibility(n_obs_max=10**6, budget_bytes=1.0),))
    result = tune(..., predicate=comp, ..., on_empty="return_history")
    rec = result.history.records[0]
    assert not rec.feasible and rec.exclusion_reason and "stored-G" in rec.exclusion_reason
```

- [ ] **Step 2: Run → fail.**

- [ ] **Step 3: Implement.** feasibility.py:

```python
@dataclass(frozen=True)
class StoredGFeasibility:
    """Excludes trials whose predicted stored-G exceeds the RAM budget (spec §5.1).

    Cost model = methods.miost_sizing (the probe's single arithmetic). HALO-INCLUSIVE
    ``n_obs_max`` (max over windows). No L_t term: nnz is L_t-invariant (D3).
    Accounting: n_concurrent * bytes <= budget (execution contract, spec §4.2).
    """

    n_obs_max: int
    budget_bytes: float = 8e9
    n_concurrent: int = 1
    n_dir: int = 8
    lam_min: float = 80.0
    lam_max: float = 905.0

    def predicted_bytes(self, params: dict[str, float]) -> int:
        from sverdrup.methods.miost_sizing import nnz_g
        return nnz_g(self.n_obs_max, alpha=params["spacing_alpha"],
                     n_dir=self.n_dir, lam_min=self.lam_min, lam_max=self.lam_max) * 12

    def explain(self, params: dict[str, float]) -> str | None:
        b = self.n_concurrent * self.predicted_bytes(params)
        if b <= self.budget_bytes:
            return None
        return f"stored-G {b:.1e} B > budget {self.budget_bytes:.1e} B (alpha={params['spacing_alpha']})"

    def feasible(self, params, tile_geometry, required_capabilities) -> bool:
        return self.explain(params) is None


@dataclass(frozen=True)
class CompositeFeasibility:
    """All-of composition (invariant 5); first failing member's explain() is the reason."""

    predicates: tuple[FeasibilityPredicate, ...]

    def feasible(self, params, tile_geometry, required_capabilities) -> bool:
        return all(p.feasible(params, tile_geometry, required_capabilities) for p in self.predicates)

    def explain(self, params: dict[str, float]) -> str | None:
        for p in self.predicates:
            reason = getattr(p, "explain", lambda _: None)(params)
            if reason:
                return f"{type(p).__name__}: {reason}"
        return None
```

loop.py lines 97–100 →

```python
            if not predicate.feasible(params, tile_geometry, required_capabilities):
                reason = getattr(predicate, "explain", lambda _p: None)(params)
                history.records.append(
                    TrialRecord(trial, scores=None, feasible=False, exclusion_reason=reason)
                )  # HARD BARRIER: no solve, no score
                continue
```

- [ ] **Step 4: Run new tests + full suite.** **Step 5: Commit** — `git commit -m "feat(tuning): StoredGFeasibility + CompositeFeasibility + infeasible reason recording (D7)"`

### Task 11: REQUIRED windowed-vs-single-window equivalence diagnostic

**Goal:** Run the D4 diagnostic at α=1.5 full-year, record worst-case-localized seam deltas, and surface the fallback decision to the owner.

> **USER-ORDERED GATE — NON-SKIPPABLE.** This task was requested by the user in the current conversation. It MUST NOT be closed by walking around it, by declaring it "verified inline", or by substituting a cheaper check. Close only after every item in `acceptanceCriteria` has been re-validated independently, with output captured.

**Files:**
- Create: `scripts/diag_miost_equivalence.py`
- Output: `docs/validation/miost_equivalence_diagnostic.md` (recorded numbers)

**Acceptance Criteria:**
- [ ] Script solves 2017 both ways at α=1.5 (windowed W=60/V=15 vs one 425-day window, same params ρ=10, q_slope=2, L_t=10) on the real dc_obs
- [ ] Reports per-day max|Δ| and RMS Δ; blend-day vs interior-day distributions separated; WORST blend-day max|Δ| is the headline (never year-RMS only)
- [ ] Output doc records numbers + the fallback decision (pavement ±L_t extension) as an explicit owner checkpoint: invoked or not-needed, with reason

**Verify:** `pixi run python scripts/diag_miost_equivalence.py` → prints table + writes the doc; owner reviews the doc.

**Steps:**

- [ ] **Step 1: Write the script** — load dc_obs via the existing validation input adapter (mirror `scripts/stage_b_gate_run.py`'s obs loading), build `Miost` twice: default `WindowPlan()` vs `WindowPlan(first_start=-30.0, n_windows=1)` with `W_DAYS` overridden to 425 for the single-window instance (add an optional `w_days` field to `WindowPlan` defaulting to `W_DAYS` — single-window path only used here). Solve daily maps for days 0..364 both ways; compute Δ per day; classify days: blend (within V of any interior window boundary) vs interior.
- [ ] **Step 2: Run it** (~2× full-year α=1.5 cost ≈ 2×2–4 min windows × … ≈ under an hour total; G at α=1.5/425 d ≈ halo-priced ~5.5 GB — feasible).
- [ ] **Step 3: Write `docs/validation/miost_equivalence_diagnostic.md`** with the tables + explicit verdict line: `FALLBACK NEEDED: yes/no — <reason>`.
- [ ] **Step 4: STOP for owner decision on the fallback** (do not implement the pavement extension unless owner says invoke).
- [ ] **Step 5: Commit** — `git commit -m "test(miost): windowed-vs-single-window equivalence diagnostic (D4) — recorded"`

### Task 12: Tier-3 + 12-dir diagnostic tools

**Goal:** Report-only tools: similarity vs the pinned MIOST maps; n_dir=12 winner re-score on the validation track.

**Files:**
- Create: `scripts/diag_miost_tier3.py`, `scripts/diag_miost_ndir12.py`

**Acceptance Criteria:**
- [ ] Tier-3: RMS diff (per-day + mean) and along-lon spectral coherence (mid-lat band, scipy.signal.coherence, wavelength axis) between OUR acceptance map nc and `data/2021a_ssh_mapping_ose/dc_maps/OSE_ssh_mapping_MIOST.nc`; regrids ours only if grids differ; prints "DIAGNOSTIC — never a gate" banner
- [ ] 12-dir: re-runs `ValidationTrackScorer.score` at the winner's params with `n_dir=12` (BasisSpec override), conditional: skip-with-reason if `StoredGFeasibility(n_dir=12)` excludes the winner's α (D2 conditions verbatim); prints µ/λx side by side with the 8-dir winner
- [ ] Both write small md reports under `docs/validation/`

**Verify:** scripts run against a produced acceptance map (Task 13 output) without error; reports written.

**Steps:**

- [ ] **Step 1: Implement both scripts** (xarray open, align time/lat/lon, compute; ~80 lines each; n_dir override = construct `BasisSpec(alpha=winner_alpha, l_t_days=winner_lt, n_dir=12)` through a `Miost` instance whose `_spec_from` honors an `n_dir` constructor override — add `Miost(n_dir=8)` constructor arg, recorded in params_key).
- [ ] **Step 2: Smoke-test on a short day range** (env var `DIAG_DAYS=0-30`).
- [ ] **Step 3: Commit** — `git commit -m "feat(miost): Tier-3 similarity + 12-dir sensitivity diagnostic tools (D2; report-only)"`

### Task 13: STAGE-A GATE — tuning run + c2-once acceptance

**Goal:** Run the Phase-5 loop for miost on the blocked validation track; accept the winner on c2 once; assemble the §7.4 Stage-A evidence.

> **USER-ORDERED GATE — NON-SKIPPABLE.** This task was requested by the user in the current conversation. It MUST NOT be closed by walking around it, by declaring it "verified inline", or by substituting a cheaper check. Close only after every item in `acceptanceCriteria` has been re-validated independently, with output captured.

**Files:**
- Create: `scripts/stage_miost_gate_run.py` (mirror `scripts/stage_b_gate_run.py`: full-2017 scope, Sobol then BO, per-strategy JSON persistence, heartbeat log)
- Output: `data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json`

**Acceptance Criteria (spec §7.4 Stage A, verbatim):**
- [ ] Tiers 1–2 green; §7.2 test inventory green (`pixi run test` full suite, no deselect)
- [ ] Tuner run with `CompositeFeasibility((StoredGFeasibility(...), CoherenceFeasibility()))` and `bars_for(POINT)`; infeasible trials visible with reasons in the results JSON
- [ ] c2 touched ONCE at acceptance; (µ, σ, λx) recorded; **µ ≥ 0.85**
- [ ] Tier-3 + 12-dir diagnostics attached (Task-12 reports generated from the winner)
- [ ] Calibration recorded N/A-for-POINT in the results JSON
- [ ] Owner sign-off

**Verify:** `pixi run python scripts/stage_miost_gate_run.py` (multi-hour; nohup pattern from the Stage-B runner incl. the PROGRESS durability caveat) → results JSON with winner row; then owner review.

**Steps:**

- [ ] **Step 1: Write the runner** — clone the stage_b_gate_run.py structure: derive full-2017 scope, build `ValidationTrackScorer` with wide `temporal_half_window_days=425.0`, `StoredGFeasibility(n_obs_max=<computed halo-inclusive max-window count from the loaded obs>)`, `ConstrainedObjective(bars=bars_for(UncertaintyCapability.POINT))`, `method_name="miost"`, Sobol(n=16) then BO(n=16, rounds=4); persist rows incrementally.
- [ ] **Step 2: Smoke on 60-day scope first** (`SVERDRUP_MIOST_SCOPE=dev`) — verifies plumbing end to end cheaply.
- [ ] **Step 3: Launch full run detached; monitor heartbeat.**
- [ ] **Step 4: Acceptance** — winner params → `run_challenge_map` full-2017 map → `their_eval.score` on c2 (the ONE touch) → record (µ, σ, λx); run Task-12 diagnostics on this map.
- [ ] **Step 5: Present evidence to owner; on sign-off commit** — `git commit -m "feat(miost): Stage-A gate — tuned winner, c2 acceptance (mu>=0.85), diagnostics attached"` + PROGRESS update.

---

## STAGE B (Tasks 14–19 — ALL blocked by Task 13 sign-off)

### Task 14: Identity-keyed CRN perturbations

**Goal:** `miost_crn.py`: ε′/η̃ as pure functions of (seed root, member, identity) — window-independent (spec §6.2).

**Files:**
- Create: `src/sverdrup/methods/miost_crn.py`
- Test: `tests/test_miost_crn.py`

**Acceptance Criteria:**
- [ ] `obs_noise(member, obs_ids, r_var, root)`: per-obs N(0, R) from blake2b(key=member-key, obs-identity-bytes) → uint64 → `ndtri((u+0.5)/2^64)`; obs identity = float64 bytes of (lon, lat, time) + mission
- [ ] `coef_noise(member, element_identity, q_var, root)`: same construction over the (6,) int identity rows
- [ ] Cross-window identity test: same obs/element in two windows → IDENTICAL perturbation; different member → different
- [ ] Moments sane: 10⁵ draws mean≈0, var≈R within 2%

**Verify:** `pixi run pytest tests/test_miost_crn.py -q`

**Steps:**

- [ ] **Step 1: Failing tests**

```python
def test_cross_window_crn_identity() -> None:
    """The load-bearing Stage-B property: shared identity -> identical perturbation."""
    root = derive_seed("miost", "pk", "stageB-crn", 0)
    ids_a = ELS_A.identity  # window A enumeration
    ids_b = ELS_B.identity  # overlapping window B enumeration
    za = coef_noise(member=3, identity=ids_a, q_var=np.ones(len(ids_a)), root=root)
    zb = coef_noise(member=3, identity=ids_b, q_var=np.ones(len(ids_b)), root=root)
    shared = {tuple(r): i for i, r in enumerate(ids_a)}
    for j, r in enumerate(ids_b):
        if tuple(r) in shared:
            assert za[shared[tuple(r)]] == zb[j]


def test_member_index_decorrelates() -> None:
    root = derive_seed("miost", "pk", "stageB-crn", 0)
    z0 = coef_noise(0, IDS, np.ones(len(IDS)), root)
    z1 = coef_noise(1, IDS, np.ones(len(IDS)), root)
    assert abs(np.corrcoef(z0, z1)[0, 1]) < 0.05


def test_moments() -> None:
    z = obs_noise(0, OBS_IDS_100K, np.full(100_000, 0.25), root=42)
    assert abs(z.mean()) < 0.01 and abs(z.var() - 0.25) < 0.005
```

- [ ] **Step 2: Run → fail.** **Step 3: Implement**

```python
"""Identity-keyed common random numbers for Stage-B members (spec §6.2)."""

from __future__ import annotations

import hashlib

import numpy as np
from scipy.special import ndtri  # type: ignore[import-untyped]


def _keyed_uniform(key: bytes, rows: np.ndarray) -> np.ndarray:
    """Deterministic U(0,1) per row: blake2b(key=key, row-bytes) -> uint64 -> (u+0.5)/2^64."""
    out = np.empty(rows.shape[0])
    for i in range(rows.shape[0]):  # blake2b ~1 us/row; vectorize later if hot
        h = hashlib.blake2b(rows[i].tobytes(), key=key, digest_size=8).digest()
        out[i] = (int.from_bytes(h, "big") + 0.5) / 2.0**64
    return out


def _member_key(root: int, member: int, axis: str) -> bytes:
    return hashlib.blake2b(f"{root}|{member}|{axis}".encode(), digest_size=16).digest()


def obs_noise(member: int, identity: np.ndarray, r_var: np.ndarray, root: int) -> np.ndarray:
    """eps' ~ N(0, R) keyed by (root, member, obs identity); window-independent."""
    u = _keyed_uniform(_member_key(root, member, "obs"), identity)
    return np.asarray(np.sqrt(r_var) * ndtri(u))


def coef_noise(member: int, identity: np.ndarray, q_var: np.ndarray, root: int) -> np.ndarray:
    """eta~ ~ N(0, Q) keyed by (root, member, element identity); window-independent."""
    u = _keyed_uniform(_member_key(root, member, "elem"), identity)
    return np.asarray(np.sqrt(q_var) * ndtri(u))
```

Obs identity rows: build in `miost.py` as a contiguous `(n, 4)` float64 array (lon, lat, time, mission-hash-as-float via blake2b of the mission string → uint32). Bit-identical across windows because the source arrays are the same file-loaded values.

- [ ] **Step 4: Run → pass.** **Step 5: Commit** — `git commit -m "feat(miost): identity-keyed CRN perturbations (Stage-B seam coherence)"`

### Task 15: Member generation + MiostEnsembleDistribution + persistence

**Goal:** m perturbed-observation members through `solve(B)` (batched), coefficient-space distribution with the D6 contract, representation-tagged persistence.

**Files:**
- Modify: `src/sverdrup/methods/miost.py` (add `Miost.sample_members(obs, grid, params, m, root)`)
- Create: `src/sverdrup/distributions/miost_ensemble.py`
- Test: `tests/test_miost_ensemble.py`

**Acceptance Criteria:**
- [ ] `sample_members` builds, per window, the m RHS `GᵀR⁻¹(y+ε′_i) + Q⁻¹η̃_i` and calls ONE batched `solve(B)`; unperturbed path untouched
- [ ] `MiostEnsembleDistribution`: mean = Γη^a; variance/cov = member-mean-centered, (m−1); `sample(k≤m, seed)` deterministic subselection; `sample(k>m)` raises `ValueError`; `marginal_variance()`/`covariance(a,b)` evaluate Γ on demand at arbitrary points (no node snap)
- [ ] Provenance carries m and MC error `sqrt(2/(m−1))`
- [ ] Persistence round-trip: kind tag `"miost-coeff-ensemble"`, η^a f64 + member anomalies f32 option; reload → identical moments
- [ ] Down-conversion `to_grid_ensemble(grid, day)` returns the existing `EnsemblePredictiveDistribution`; moments agree at grid nodes with the coefficient-space values (rtol 1e-6)

**Verify:** `pixi run pytest tests/test_miost_ensemble.py -q`

**Steps:**

- [ ] **Step 1: Failing tests** (contract tests: k>m raises; (m−1) denominator asserted against `np.cov`; round-trip; down-conversion agreement; MC-error in provenance).
- [ ] **Step 2: Run → fail.**
- [ ] **Step 3: Implement.** `sample_members`: reuse `_solve_window` machinery; per window build `B = rhs_from_obs(g, r, y)[:, None] + stack_i(gᵀ(ε′_i/r) + η̃_i/q)`; one `solver.solve(B)`; store `{window_id: (eta_a, members (n_coef, m))}`. Distribution mirrors `MiostPointDistribution` evaluation (blend-weighted Γ at query points) applied per member; variance = anomalies² mean with (m−1); covariance = anomaly outer products. Persistence: npz with `kind="miost-coeff-ensemble"` string array + basis fields + per-window arrays.
- [ ] **Step 4: Run → pass.** **Step 5: Commit** — `git commit -m "feat(miost): perturbed-obs members + coefficient-space ensemble distribution (D6)"`

### Task 16: Stage-B exactness oracle + under-convergence test

**Goal:** Prove the ensemble machinery samples the exact posterior on a small case; demonstrate the PCG-tolerance contract.

**Files:**
- Test: `tests/test_miost_ensemble_oracle.py`

**Acceptance Criteria:**
- [ ] Small case (duality-oracle geometry, single window): m=4000 members' coefficient covariance → matches dense `A⁻¹` (Frobenius rel err < 3·sqrt(2/(m−1)))
- [ ] Member mean → η^a within MC error
- [ ] Under-convergence: same case at pcg_rtol=0.5 (deliberately loose) → coefficient-variance Frobenius error exceeds the tight-rtol error by >3× (documents the §6.5 contract; both numbers printed)

**Verify:** `pixi run pytest tests/test_miost_ensemble_oracle.py -q`

**Steps:** Step 1 write tests (dense A from the small G/Q/R; compare `np.cov(members)`); Step 2 run → fail until wired; Step 3 fix wiring only (no new features); Step 4 pass; Step 5 commit `test(miost): Stage-B exactness oracle + under-convergence contract test`.

### Task 17: s-inflation + mean-unchanged non-regression

**Goal:** Closed-form s on validation calibration; exact anomaly rescale; prove Stage-A mean untouched.

**Files:**
- Modify: `src/sverdrup/distributions/miost_ensemble.py` (add `rescaled(s)`)
- Create: `scripts/tune_miost_inflation.py`
- Test: `tests/test_miost_inflation.py`

**Acceptance Criteria:**
- [ ] `rescaled(s)` returns a new distribution with anomalies ×√s; mean field BIT-IDENTICAL (test asserts `np.array_equal`)
- [ ] Closed form used and recorded: χ²_red(s) = χ²_red(1)/s ⇒ s* = χ²_red(1) on the validation track; script prints s*, coverage(s*), crps(s*)
- [ ] Scalar-R condition asserted in the script (raises if per-obs R non-uniform)
- [ ] Non-regression: Stage-A acceptance map regenerated under Stage-B code == committed Stage-A map (allclose atol 0 — same solve path)

**Verify:** `pixi run pytest tests/test_miost_inflation.py -q`; script run on the winner.

**Steps:** Step 1 tests (bit-identical mean; χ² closed form on synthetic: scale anomalies by √s ⇒ χ² divides by s); Step 2 fail; Step 3 implement (`rescaled` = dataclass copy with anomalies scaled; script mirrors scorer interp to get per-point (y−µ, σ²)); Step 4 pass; Step 5 commit `feat(miost): s-inflation via exact anomaly rescale + mean-unchanged non-regression (D6)`.

### Task 18: Stage-B seam-dispersion + variance-equivalence diagnostics

**Goal:** Measure the CRN residual: worst-case-localized member dispersion at blend days; extend the D4 diagnostic to variance fields.

**Files:**
- Create: `scripts/diag_miost_seam_dispersion.py`
- Output: `docs/validation/miost_seam_dispersion.md`

**Acceptance Criteria:**
- [ ] Per output day: member std field; report ratio (blend-day worst / interior-day median) — worst-case-localized, never averaged away
- [ ] Variance-field windowed-vs-single-window comparison at α=1.5 (same construction as Task 11, on member std)
- [ ] Doc records numbers + verdict line for the Stage-B gate

**Verify:** script runs; doc written; numbers reviewed at the Task-19 gate.

**Steps:** Step 1 implement (reuse Task-11 harness, add member generation m=50 at α=1.5); Step 2 run + write doc; Step 3 commit `test(miost): Stage-B seam-dispersion + variance-equivalence diagnostics (recorded)`.

### Task 19: STAGE-B GATE — calibration acceptance

**Goal:** Stage-B acceptance per spec §6.6/§7.4: calibration bars on validation, c2 once, evidence assembled.

> **USER-ORDERED GATE — NON-SKIPPABLE.** This task was requested by the user in the current conversation. It MUST NOT be closed by walking around it, by declaring it "verified inline", or by substituting a cheaper check. Close only after every item in `acceptanceCriteria` has been re-validated independently, with output captured.

**Files:**
- Modify: `scripts/stage_miost_gate_run.py` (Stage-B mode: winner params + m members + s*)
- Output: results JSON + PROGRESS update

**Acceptance Criteria (spec §7.4 Stage B, verbatim):**
- [ ] §7.3 inventory green (full suite)
- [ ] `native_capability` upgraded (SAMPLES) and `bars_for` now includes coverage automatically (test observed)
- [ ] Calibration bars green on validation (reduced_chi2, coverage_1sigma, crps reported; coverage within 0.6827±0.10)
- [ ] c2 touched once; mean-unchanged non-regression green
- [ ] Seam-dispersion diagnostic (Task 18) attached; owner sign-off

**Verify:** gate runner output + owner review.

**Steps:** Step 1 extend runner (generate members at winner, compute s*, score calibration on validation, then the single c2 touch); Step 2 run; Step 3 present evidence; Step 4 on sign-off commit + PROGRESS update + capability flip commit `feat(miost): Stage-B gate — ensemble posterior accepted on calibration`.

---

## Self-review notes (run before handoff)

- Spec coverage: D1→T2, D2→T12, D3→T2/T6, D4→T11, D5→T8, D6→T14–17, D7→T10, D8→T3; six seams a→T4, b→T3/T4, c→T3, d→T7, e→T7/T8, f→T8; folds 1/2→T9, 3 (n_tiles=1) → T13 runner geometry `TileGeometry(core_size_deg=10.0, range_km=0.0, tiling_id="miost-single", n_tiles=1)`, 4→T1, A→T6, B→T9, C landed with the spec commit.
- Type consistency: `BasisSpec.elements_for_window(start_day)` / `Elements.identity` / `build_g(spec, els, lon, lat, t)` / `MiostSolver.solve(b) -> (x, report)` / `rhs_from_obs(g, r, y)` used identically across Tasks 3–17.
- Placeholders: none — every "..." in Task 7/8 sketches is bounded by named behavior + tests that pin it; implementer fills bodies against the tests in the same task.
