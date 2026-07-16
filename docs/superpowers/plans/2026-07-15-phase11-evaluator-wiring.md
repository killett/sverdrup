# Phase 11 — Evaluator Wiring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Exercise the reference-free evaluator family (rebuilt GroundTrack + new SpectralFidelity) through one general Registry wiring path, record retroactive numbers on the shipped MIOST and regenerated OI mean maps, and extract the triplicated lexicographic selection into one Policy seam — all report-only, zero c2, no product bit changes.

**Architecture:** Spec `docs/superpowers/specs/2026-07-15-phase11-evaluator-wiring-design.md` governs on any conflict. Two independent early tracks (orbit-geometry provider; map-spectrum prep) feed the two evaluators; the integrity test locks declared⇒consumed; a shared context-builder + row builder wire three surfaces (retro script, Phase-9 harness future packs, pipeline migration); the Policy seam is an independent track with three identity-gated site migrations; a user-gated phase-close review ends the phase.

**Tech Stack:** numpy 2-D FFT (no new deps), xarray for map reads, pytest, the existing `atomic_write_json` evidence store at `data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json`.

**User decisions (already made):** Forks a–e + 4 batch-1 pins + 3 batch-2 pins, all recorded in the spec §1 decision register; owner task-graph + 7 plan-detail obligations from the plan-approval message (fixed in the "Pinned constants" section below); hold plan for owner review before execution.

---

## Pinned constants and measured values (plan-detail obligations 1–7)

All Phase-11 constants live in ONE module: `src/sverdrup/eval/phase11_constants.py` (obligation 1, 2, 5 values; imported by geometry, evaluators, and tests — no magic numbers at call sites).

**Measured on the real artifacts this session (2026-07-15):**

- Map grid (both products): `time=365, lat=52, lon=51`; lon 295.0→305.0 step 0.2°, lat 33.0→43.2 step 0.2°; var `ssh`; attr `assimilated_missions = "alg h2g j2g j2n s3a"` (space-separated).
- φ0 = mean(grid lat) = **38.1°**; box in the φ0 plane ≈ **876 × 1136 km** (runtime-computed from the grid; recorded in the geometry artifact).
- Grid spacing: dy = 22.26 km, dx ≈ 17.5 km → 3·max = 66.8 km → fidelity lower edge = **100 km** (floor binds).
- Radial-Hann mainlobe half-width, measured by 8×-padded FFT of the window on the real 52×51 grid: **2.25 zonal-fundamental bins** (0.002565 cyc/km). The §11 recorded-vs-measured test recomputes this and asserts within ±0.1 bin.
- Ring bin wavelengths (zonal fundamental Lx/b): b=3 → 292 km, b=4 → **219 km**, b=5 → 175 km. Fidelity upper edge = min(300, Lx/4) ≈ **219 km** (mainlobe-clearance rule binds, 300 cap never does — as the owner's batch-1 pin 3 records).

**Pinned constants (obligation 1, 2):**

```python
# src/sverdrup/eval/phase11_constants.py
"""Phase-11 pre-registered constants (spec §1 pins; owner plan-approval obligations 1, 2, 5)."""

DERIVATION_VERSION = 1  # orbit-geometry artifact schema/algorithm version

# GroundTrack probe geometry (spec §4).
DTHETA_DEG = 15.0
# Rationale: half the angular resolution element atan(2.25/4) ~= 29 deg at the
# Jason-class radius (bin ~4); covers per-pass heading spread without eating
# the baseline annulus.
DK_HALFWIDTH_BINS = 2.25
# Rationale: leakage-matched — equals the MEASURED radial-Hann mainlobe
# half-width in zonal-fundamental units (see MAINLOBE_HALFWIDTH_BINS).
MAINLOBE_HALFWIDTH_BINS = 2.25  # measured 2026-07-15; test re-measures +-0.1
N_MODES_BASELINE_FLOOR = 8
MAX_WIDENINGS = 3  # symmetric +1 bin per side per widening; beyond -> under_floor flag

# Orbit-class classifier (obligation 2).
CLUSTER_TOL_DEG = 0.05  # ~4.4 km at 38N — far below any track spacing
REPEAT_RATIO_MAX = 0.5
# Rule: cluster the family's phi0-crossing longitudes with tolerance
# CLUSTER_TOL_DEG; orbit_class = "repeat" iff n_clusters / n_crossings <= REPEAT_RATIO_MAX.
# Rationale: a repeat orbit (<= 35 d period) revisits each track >= 10x/year
# -> ratio <= 0.1; a geodetic/drifting orbit almost never repeats within
# tolerance -> ratio ~= 1.0. Threshold 0.5 sits with wide margin on both sides;
# the synthetic fixture exercises both sides (obligation 2).

# Spectral fidelity band rule (spec §5).
BAND_LO_FLOOR_KM = 100.0  # lower edge = max(100, 3 * grid dy_km)
BAND_HI_CAP_KM = 300.0    # upper edge = min(300, Lx / MIN_BIN_INDEX)
MIN_BIN_INDEX = 4

# Evidence/report schema versions (spec §7).
REPORT_SCHEMA_VERSION = 1
```

**Paths (obligation 7):**

- Geometry artifact: `data/2021a_ssh_mapping_ose/ours/phase11_orbit_geometry.json` (derived for the assimilated-mission union `{alg, h2g, j2g, j2n, s3a}`; the c2 obs file is NEVER opened — zero c2).
- Evidence: keys `phase11.retro.{miost|oi}.{groundtrack|spectral_fidelity}` + `phase11.retro.provenance` inside `data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json` (the standing store; nested-key atomic write, `phase10_compare` pattern).
- Retro inputs: `ours/stage_b_mean_maps.nc` (MIOST, shipped) and `ours/oi_mean_maps.nc` (Phase-9 regenerated; signed anchor `ours/OSE_ssh_mapping_OURS_OI.nc` sha recorded beside it — batch-2 pin 3).
- PROGRESS headline format (obligation 7), appended at phase close:

```
PHASE-11 RETRO NUMBERS (2026-07-XX, evidence phase11.retro.*, geometry sha <sha12>):
- MIOST stage-B means: track_excess_log10 max repeat=<x.xxx> (<mission>/<fam>),
  max drifting=<x.xxx> (<mission>); spec_slope=<-x.xx> (WLS SE <x.xx>, day IQR <x.xx>),
  band [100, 219] km
- OI regenerated means: <same two rows>
```

**Enumerated pin updates (obligation 4 — the ONE deliberate non-identity-gated migration, fork-d pin 1):**

| Consumer | Current pin | Deliberate update |
|---|---|---|
| `tests/unit/test_groundtrack.py` | `track_power` stripe > smooth | REWRITTEN in Task 3 (new statistic, new names) |
| `tests/test_metric_scope.py:29` | builds `Registry([..., GroundTrack(), ...])` | constructor takes geometry-free defaults; update construction, scope assertions unchanged |
| `tests/unit/test_evaluation.py` | fake evaluator returns `{"track_power": 0.0}` | name-only coincidence (own fake class); leave unchanged |
| `tests/test_eval_resolution.py::test_effective_resolution_metadata` | pins `required_context == {WITHHELD_OBS, ORBIT_GEOMETRY}` | pin updated to `{WITHHELD_OBS}` (Task 5 — declaration defect fix) |
| pipeline score-shape readers (`tests/test_phase2_stage_a.py`, `test_phase2_stage_b.py`, `test_gmrf_blend.py`, `test_degradation_path.py`, `tests/integration/test_vertical_slice.py`, `tests/oracle/test_oi_oracle.py`) | read flat `scores["rmse"]` etc. | Task 6 enumerates each at implementation; flat per-evaluator metrics move under `scores["report_rows"]`; a tiny test helper `row_metric(scores, evaluator, name)` keeps updates mechanical |
| `Registry.run()` | consumers after Task 6 = unit tests only (`tests/unit/test_evaluation.py`, `tests/test_metric_scope.py`) | KEPT (core spine, invariant 9) with a docstring note recording the flat-merge name-collision hazard; new report code never calls it (batch-2 pin 2) |

**NEW FINDING the plan must handle (verified at source, not in the spec):** `EffectiveResolution.required_context` declares `ORBIT_GEOMETRY` but `evaluate()` never reads it (the track arrives via `result` channels; only `WITHHELD_OBS` is read from context). This is a SECOND declared-but-unread defect of exactly the class constraint 3 mechanizes. Task 5 fixes the declaration (drop `ORBIT_GEOMETRY`), updates the one pinning test (enumerated above), and verifies the broadened `applicable()` surface changes nothing: no `Registry` registers `EffectiveResolution` today (verified — only direct-construction tests use it).

---

### Task 1: Orbit-geometry provider (`application/orbit_geometry.py`)

**Goal:** Derive per-mission track geometry (headings, φ0-crossing spacings, orbit class) from the assimilated missions' along-track obs files, cached as a deterministic pinnable JSON artifact.

**Files:**
- Create: `src/sverdrup/eval/phase11_constants.py` (content above, verbatim)
- Create: `src/sverdrup/application/orbit_geometry.py`
- Test: `tests/test_orbit_geometry.py`

**Acceptance Criteria:**
- [ ] Synthetic repeat mission (known heading 12° from north, s_lon 2.8°, 30 passes/family over a year) recovered: heading within ±1°, s_lon within ±5%, `orbit_class == "repeat"`, `d_perp_km == s_lon_km * abs(cos(radians(heading)))`
- [ ] Synthetic drifting mission (crossing longitudes uniform-random) classified `"drifting"` with quantile spacing summary and NO `d_perp_km`; a boundary fixture at ratio just below 0.5 classifies `"repeat"` (both threshold sides exercised)
- [ ] Artifact bytes deterministic: two derivations → identical sha256; changing one obs-file sha in the key → new artifact
- [ ] c2 file never opened (test asserts the loader refuses mission id `"c2"`)

**Verify:** `pixi run pytest tests/test_orbit_geometry.py -v` → all PASS

**Steps:**

- [ ] **Step 1: Write failing tests** — synthetic pass generator + recovery asserts:

```python
# tests/test_orbit_geometry.py (core fixtures; full file has one test per criterion)
import numpy as np
from sverdrup.application.orbit_geometry import (
    FamilyGeometry, classify_orbit, derive_family, derive_mission_geometry,
)

PHI0 = 38.1

def _synth_passes(heading_north_deg: float, s_lon_deg: float, n_tracks: int,
                  revisits: int, jitter_deg: float = 0.005, seed: int = 7):
    """Ascending-family passes: each pass = (lon, lat, time) arrays crossing phi0."""
    rng = np.random.default_rng(seed)
    lats = np.linspace(33.0, 43.2, 40)
    passes = []
    tan_h = np.tan(np.deg2rad(heading_north_deg))
    base_lons = 295.0 + s_lon_deg * np.arange(n_tracks)
    for rev in range(revisits):
        for lon0 in base_lons:
            # lon increases with lat at rate tan(heading) (heading from north)
            lon = lon0 + (lats - PHI0) * tan_h / np.cos(np.deg2rad(PHI0)) \
                  + rng.normal(0, jitter_deg)
            t0 = rev * 10.0 + lon0  # distinct pass times; > 60 s gaps
            times = t0 + np.linspace(0, 0.005, lats.size)
            passes.append((lon, lats.copy(), times))
    return passes

def test_repeat_mission_recovered():
    fams = derive_family(_synth_passes(12.0, 2.8, 4, 12), phi0=PHI0, ascending=True)
    assert fams.orbit_class == "repeat"
    assert abs(fams.heading_north_deg - 12.0) < 1.0
    assert abs(fams.s_lon_km - 2.8 * 111.32 * np.cos(np.deg2rad(PHI0))) \
        < 0.05 * fams.s_lon_km
    assert np.isclose(
        fams.d_perp_km,
        fams.s_lon_km * abs(np.cos(np.deg2rad(fams.heading_north_deg))))

def test_drifting_mission_classified():
    rng = np.random.default_rng(3)
    passes = []
    for lon0 in 295.0 + rng.uniform(0, 10, 48):
        lats = np.linspace(33.0, 43.2, 40)
        lon = lon0 + (lats - PHI0) * np.tan(np.deg2rad(6.0))
        passes.append((lon, lats, lon0 + np.linspace(0, 0.005, 40)))
    fams = derive_family(passes, phi0=PHI0, ascending=True)
    assert fams.orbit_class == "drifting"
    assert fams.d_perp_km is None
    assert fams.spacing_quantiles_km is not None  # (q10, q50, q90)
```

- [ ] **Step 2: Run — confirm FAIL** (`ModuleNotFoundError` / missing names): `pixi run pytest tests/test_orbit_geometry.py -v`

- [ ] **Step 3: Implement.** Core structure:

```python
# src/sverdrup/application/orbit_geometry.py
"""Orbit geometry derived FROM the obs files (spec §2; fork-a pins 1-5).

phi0-plane frame (pinned once, shared with eval/map_spectrum.py):
x = lon * cos(phi0) [deg -> km via 111.32], y = lat [deg -> km].
Headings are AXIAL (alpha == alpha + 180), measured from NORTH, in [0, 180).
d_perp_km = s_lon_km * |cos(heading_north)| (formula recorded in the artifact).
"""
KM_PER_DEG = 111.32

@dataclass(frozen=True)
class FamilyGeometry:
    heading_north_deg: float
    n_passes: int
    n_crossings: int          # passes crossing phi0 IN-DOMAIN (spacing uses only these)
    orbit_class: str          # "repeat" | "drifting"
    s_lon_km: float | None    # repeat only: median adjacent cluster-center gap at phi0
    d_perp_km: float | None   # repeat only: s_lon * |cos heading|
    spacing_quantiles_km: tuple[float, float, float] | None  # drifting only (q10,q50,q90)

def split_passes(lon, lat, time, gap_sec=60.0) -> list[tuple]:
    """Segment one mission's arrays into passes on time gaps > gap_sec
    (reuses the harness _PASS_GAP_SEC convention), split asc/desc on sign
    of dlat/dt within each segment."""

def _fit_heading(passes, phi0) -> float:
    """Per-pass total-least-squares direction in the phi0 km plane, then the
    doubled-angle (axial) circular mean over passes (batch-1 pin 4):
    mean_angle = 0.5 * atan2(mean(sin 2a_i), mean(cos 2a_i)); convert the
    east-referenced fit angle to from-NORTH axial [0, 180)."""

def _phi0_crossings(passes, phi0, lon_lo=295.0, lon_hi=305.0) -> np.ndarray:
    """Linear-interpolated crossing longitude of each pass at lat == phi0,
    keeping only crossings inside [lon_lo, lon_hi] (obligation 4: in-domain only)."""

def classify_orbit(crossing_lons, tol_deg=CLUSTER_TOL_DEG) -> tuple[str, np.ndarray]:
    """Sort crossings; single-linkage cluster with gap > tol; return
    ("repeat" if n_clusters / n_crossings <= REPEAT_RATIO_MAX else "drifting",
     cluster_centers)."""

def derive_family(passes, phi0, ascending) -> FamilyGeometry: ...

def derive_mission_geometry(obs_path, phi0) -> dict[str, FamilyGeometry]:
    """{"asc": ..., "desc": ...} for one mission file; refuses mission id 'c2'."""

def build_geometry_artifact(obs_dir, missions, phi0, out_path) -> str:
    """Derive all missions -> JSON artifact via atomic_write_json.
    Key: sha256 over (sorted obs-file sha256s, DERIVATION_VERSION, box, phi0).
    Provenance block inside: file shas, missions, n_passes/n_crossings per family.
    Returns artifact sha256. Loads instead of re-deriving when key matches."""
```

Spacing (repeat): gaps between adjacent CLUSTER CENTERS, median → `s_lon_km` (deg → km via `KM_PER_DEG * cos(phi0)`). Drifting: quantiles (q10, q50, q90) of adjacent gaps of all sorted crossings, flagged via `spacing_quantiles_km`.

- [ ] **Step 4: Run — confirm PASS**: `pixi run pytest tests/test_orbit_geometry.py -v`
- [ ] **Step 5: Determinism + c2-refusal tests → red → green** (same file; `build_geometry_artifact` on tmp_path synthetic NetCDFs written with xarray)
- [ ] **Step 6: Commit**

```bash
pixi run pre-commit run --files src/sverdrup/eval/phase11_constants.py src/sverdrup/application/orbit_geometry.py tests/test_orbit_geometry.py
git add -A && git commit -m "feat(phase11): orbit-geometry provider — data-derived headings/spacings/orbit-class, pinnable artifact"
```

### Task 2: Shared spectral prep (`eval/map_spectrum.py`)

**Goal:** One pure-numpy module owning φ0-plane, detrend, radial window, half-plane 2-D power, wedge/annulus masks with exclusions, ring-integrated E(k), mode counts.

**Files:**
- Create: `src/sverdrup/eval/map_spectrum.py`
- Test: `tests/test_map_spectrum.py`

**Acceptance Criteria:**
- [ ] Parseval: sum of half-plane power (Hermitian-corrected) ≈ windowed-field variance × N within 1e-6 relative
- [ ] Synthetic isotropic |k|^(−q) field (q=3): ring-integrated E(k) log-log slope ≈ −q+1 = −2 within ±0.15 over bins 3–10
- [ ] Wedge/annulus mode counts EXACT on a 16×16 grid vs brute-force enumeration; no k counted twice across the half-plane (kx=0 column halved correctly)
- [ ] Measured mainlobe half-width on the real 52×51 grid == `MAINLOBE_HALFWIDTH_BINS` ± 0.1 (the recorded-vs-measured test, obligation 5)

**Verify:** `pixi run pytest tests/test_map_spectrum.py -v` → all PASS

**Steps:**

- [ ] **Step 1: Failing tests** (Parseval, slope recovery, exact mode counts, mainlobe):

```python
def test_ring_spectrum_slope_recovers_isotropic_power_law():
    rng = np.random.default_rng(11)
    ny, nx = 128, 128
    kx = np.fft.fftfreq(nx)[None, :]; ky = np.fft.fftfreq(ny)[:, None]
    kk = np.hypot(kx, ky); kk[0, 0] = np.inf
    amp = kk ** (-3 / 2)  # power ~ k^-3
    phase = np.exp(2j * np.pi * rng.random((ny, nx)))
    field = np.real(np.fft.ifft2(amp * phase))
    g = PlaneGrid.from_km(dx_km=17.5, dy_km=22.26, ny=ny, nx=nx)
    P, KX, KY = power2d(detrend(field), radial_hann(g), g)
    k, E, n = ring_spectrum(P, KX, KY, exclude=[])
    sl = np.polyfit(np.log10(k[2:10]), np.log10(E[2:10]), 1)[0]
    assert abs(sl - (-2.0)) < 0.15   # E(k) ~ k^(-q+1), the spec §3 relation

def test_mainlobe_halfwidth_matches_recorded():
    g = PlaneGrid.from_deg(lon=np.arange(295, 305.01, .2),
                           lat=np.arange(33, 43.21, .2), phi0=38.1)
    measured = mainlobe_halfwidth_bins(radial_hann(g), g, pad=8)
    assert abs(measured - MAINLOBE_HALFWIDTH_BINS) < 0.1
```

- [ ] **Step 2: Run — FAIL.** `pixi run pytest tests/test_map_spectrum.py -v`
- [ ] **Step 3: Implement:**

```python
# src/sverdrup/eval/map_spectrum.py
"""Shared map-plane spectral prep (spec §3). NOT eval/spectral.py (the lambda_x
algorithm) — that module is untouched (Phase-5 invariant 10).

Ring convention: azimuthally-INTEGRATED E(k) (ring-sum, not ring-mean).
Exponent relation (the off-by-one trap, recorded once, here): an isotropic
2-D power DENSITY ~ |k|^(-q) gives ring-integrated E(k) ~ k^(-q+1), the SAME
exponent as a 1-D along-track spectrum of that field.
Half-plane convention: kx >= 0, with the kx == 0 column's ky < 0 half dropped
(alpha == alpha + 180 axial identification; no mode counted twice).
"""

@dataclass(frozen=True)
class PlaneGrid:
    x_km: np.ndarray; y_km: np.ndarray; phi0: float
    @classmethod
    def from_deg(cls, lon, lat, phi0=None): ...  # x = (lon-lon0)*111.32*cos(phi0)

def detrend(field):            # subtract lstsq plane fit on [1, x, y]
def radial_hann(grid):         # 0.5*(1+cos(pi*r/R)) inside inscribed disk r<=R, else 0
def power2d(field, window, grid):  # -> (P half-plane, KX, KY in cyc/km)
def wedge_mask(KX, KY, angle_east_deg, dtheta_deg, k_lo, k_hi):
    # axial: fold atan2(KY, KX) into [0, 180); |angle - probe| <= dtheta (circular)
def annulus_mask(KX, KY, k_lo, k_hi): ...
def ring_spectrum(P, KX, KY, exclude):  # -> (k_centers, E_sum, n_modes) per ring
def mainlobe_halfwidth_bins(window, grid, pad=8):  # first-null half-width / (1/Lx)
```

Ring bin width = zonal fundamental 1/Lx. Wedge exclusion set (all mission families' probe angles) passed by callers; ONE implementation.

- [ ] **Step 4: Run — PASS.** Then Hermitian/mode-count brute-force test red→green.
- [ ] **Step 5: Commit** — `feat(phase11): map_spectrum shared prep — radial window, half-plane power, ring-integrated E(k)`

### Task 3: GroundTrack rebuild

**Goal:** Replace the stub with the geometry-consuming oriented-band statistic vs same-|k| annulus baseline, per-day median, per-mode normalized.

**Files:**
- Modify: `src/sverdrup/eval/groundtrack.py` (full rewrite)
- Test: `tests/unit/test_groundtrack.py` (full rewrite — old `track_power` pins die, fork-d pin 1)

**Acceptance Criteria:**
- [ ] `required_context == frozenset({ORBIT_GEOMETRY})`; geometry bag actually read (probe angles/radii derived from `d_perp_km` + `heading_north_deg` per family)
- [ ] Planted oriented sinusoid at (heading 12°, wavelength 248 km) → `track_excess_log10_synth_asc` > 1.0; isotropic red-noise field → |statistic| < 0.15 (per-mode normalization: expectation 0 on isotropic input)
- [ ] Widening: baseline modes < 8 → Δk widens +1 bin/side, ≤ 3 times; beyond → row flagged `under_floor` (metric still reported)
- [ ] `field_kind == "sigma"` → `ValueError` mentioning the Phase-8 theorem; NaN in box → `ValueError`; drifting family → wedge-over-range statistic + `estimand == "drifting_band"` flag
- [ ] Class docstring contains verbatim: "NECESSARY-NOT-SUFFICIENT — a strong track signature proves a problem; a clean map does not prove correctness."

**Verify:** `pixi run pytest tests/unit/test_groundtrack.py -v` → all PASS

**Steps:**

- [ ] **Step 1: Failing tests** (planted stripe / isotropic null / sigma refusal):

```python
def _geometry_bag():
    return {"synth": {"asc": {"heading_north_deg": 12.0, "orbit_class": "repeat",
                              "d_perp_km": 248.0, "s_lon_km": 315.0,
                              "n_crossings": 30},
                      "desc": None}}

def test_planted_track_signature_detected():
    g = _real_grid()  # 52x51, phi0=38.1
    stripe = _oriented_sinusoid(g, heading_north_deg=12.0, wavelength_km=248.0)
    maps = stripe[None] + _rednoise(g, seed=5, n_days=8) * 0.3
    ctx = EvalContext({ContextKey.ORBIT_GEOMETRY: _geometry_bag()})
    out = GroundTrack().evaluate(
        {"fields": maps, "grid_lon": g.lon, "grid_lat": g.lat,
         "field_kind": "mean"}, ctx)
    assert out["track_excess_log10_synth_asc"] > 1.0

def test_isotropic_field_scores_near_zero():
    maps = _rednoise(_real_grid(), seed=9, n_days=8)
    ...
    assert abs(out["track_excess_log10_synth_asc"]) < 0.15

def test_sigma_field_refused_loudly():
    with pytest.raises(ValueError, match="mean"):
        GroundTrack().evaluate({"fields": maps, ..., "field_kind": "sigma"}, ctx)
```

- [ ] **Step 2: Run — FAIL.**
- [ ] **Step 3: Implement** (consumes Tasks 1+2):

```python
class GroundTrack:
    """... NECESSARY-NOT-SUFFICIENT — a strong track signature proves a problem;
    a clean map does not prove correctness.

    Mean maps ONLY (Phase-8 theorem, recorded here): posterior covariance
    (G'R^-1G + Q^-1)^-1 is independent of obs VALUES, so sigma/variance maps
    LEGITIMATELY carry sampling-geometry pattern — scoring them would "detect"
    an expected feature. field_kind != "mean" refuses loudly.
    """
    name = "groundtrack"
    required_context = frozenset({ContextKey.ORBIT_GEOMETRY})
    optional_context: frozenset[ContextKey] = frozenset()
    metric_scope = MetricScope.POINTWISE

    def evaluate(self, result, context):
        r = cast(Any, result)
        if r.get("field_kind") != "mean":
            raise ValueError("GroundTrack scores MEAN maps only ...")
        geometry = cast(dict, context.items[ContextKey.ORBIT_GEOMETRY])
        grid = PlaneGrid.from_deg(r["grid_lon"], r["grid_lat"])
        maps = np.asarray(r["fields"])          # (n_days, ny, nx)
        if np.isnan(maps).any(): raise ValueError("NaN in box ...")
        win = radial_hann(grid)
        all_wedges = _all_probe_wedges(geometry, grid)   # exclusions, both classes
        out = {}
        per_class_max = {"repeat": [], "drifting": []}
        for mission, fams in geometry.items():
            for famname, fam in fams.items():
                if fam is None: continue
                day_vals, nb, nbase, widened, under = [], 0, 0, 0, False
                for day in maps:
                    P, KX, KY = power2d(detrend(day), win, grid)
                    v, nb, nbase, widened, under = _excess_log10(
                        P, KX, KY, fam, all_wedges, grid)
                    day_vals.append(v)
                key = f"track_excess_log10_{mission}_{famname}"
                out[key] = float(np.median(day_vals))
                out[key + "_n_modes_band"] = float(nb)
                out[key + "_n_modes_baseline"] = float(nbase)
                per_class_max[fam["orbit_class"]].append(out[key])
        for cls, vals in per_class_max.items():
            if vals: out[f"track_excess_log10_max_{cls}"] = float(max(vals))
        return out
```

`_excess_log10`: repeat → band = wedge at probe angle ± DTHETA_DEG, radius 1/d_perp ± DK_HALFWIDTH_BINS·(1/Lx); drifting → wedge over [1/q90, 1/q10] radial range. Baseline = annulus same radial range minus ALL families' wedges. Widening loop per pinned rule. Statistic `log10((band/n_band) / (base/n_base))`.

- [ ] **Step 4: Run — PASS.** Widening + drifting + docstring tests red→green.
- [ ] **Step 5: Update `tests/test_metric_scope.py`** construction (`GroundTrack()` — still valid, constructor arg gone) — run: `pixi run pytest tests/test_metric_scope.py -v` → PASS.
- [ ] **Step 6: Commit** — `feat(phase11): GroundTrack rebuilt — geometry-consumed oriented probes vs local baseline; track_power dies`

### Task 4: `optional_context` extension + SpectralFidelity

**Goal:** Additive Evaluator-protocol extension; accuracy declares its optionals; new descriptive-only SpectralFidelity evaluator.

**Files:**
- Modify: `src/sverdrup/core/evaluation.py` (Protocol + docstring note: applicable() stays required-based)
- Modify: `src/sverdrup/eval/accuracy.py` (declare `optional_context`)
- Create: `src/sverdrup/eval/fidelity.py`
- Test: `tests/test_eval_fidelity.py`, additions to `tests/unit/test_accuracy.py`

**Acceptance Criteria:**
- [ ] `Evaluator` protocol carries `optional_context`; `Registry.applicable` UNCHANGED (required-based; a test proves an evaluator with unmet optionals is still applicable)
- [ ] Accuracy: `optional_context == {TRUTH, WITHHELD_OBS}`; neither present → returns `{}` (the pinned precedent, batch-2 addition)
- [ ] SpectralFidelity on synthetic |k|^(−3) field: `spec_slope` ≈ −2 ± 0.2; band edges on the real grid == [100.0, ≈219.3] km (rule of spec §5); day median/IQR present; `spec_slope_obs_1d` present iff WITHHELD_OBS given, absent otherwise
- [ ] σ/NaN guards identical to GroundTrack (shared behavior)

**Verify:** `pixi run pytest tests/test_eval_fidelity.py tests/unit/test_accuracy.py tests/unit/test_evaluation.py -v` → all PASS

**Steps:**

- [ ] **Step 1: Failing tests** — band-edge rule, slope recovery, optional-context row:

```python
def test_band_edges_follow_rule_on_real_grid():
    ev = SpectralFidelity()
    lo, hi = ev.band_km(_real_grid())
    assert lo == 100.0 and abs(hi - 219.3) < 1.0

def test_obs_row_iff_withheld_present():
    out_with = ev.evaluate(res, EvalContext({ContextKey.WITHHELD_OBS: obs_bag}))
    out_without = ev.evaluate(res, EvalContext({}))
    assert "spec_slope_obs_1d" in out_with and "spec_slope_obs_1d" not in out_without
```

- [ ] **Step 2: FAIL.** **Step 3: Implement:**

```python
# core/evaluation.py — Protocol gains:
    optional_context: frozenset[ContextKey]
# and Registry.applicable docstring gains:
#   "optional_context NEVER gates applicability (spec §5 / fork-d pin 6)."

# eval/fidelity.py
class SpectralFidelity:
    """Descriptive-only wavenumber-slope sanity (spec §5). No verdict semantics."""
    name = "spectral_fidelity"
    required_context: frozenset[ContextKey] = frozenset()
    optional_context = frozenset({ContextKey.WITHHELD_OBS})
    metric_scope = MetricScope.POINTWISE

    def band_km(self, grid):  # max(100, 3*dy) .. min(300, Lx/MIN_BIN_INDEX)
    def evaluate(self, result, context):
        # guards as GroundTrack; per-day power2d -> mean spectrum over days;
        # rings EXCLUDE all track wedges when ORBIT_GEOMETRY present (optional
        # read is fine: reads subset of required+optional... geometry NOT
        # declared -> rings exclude wedges ONLY when the result carries
        # precomputed masks from the builder. DECISION: wedge exclusion masks
        # arrive via result["track_wedge_masks"] (builder-computed, Task 6) so
        # fidelity does NOT read ORBIT_GEOMETRY at all — declaration stays
        # honest with required=∅, optional={WITHHELD_OBS}.
        # WLS fit: weights n_modes on log10 E vs log10 k within band;
        # per-day slopes -> median/IQR; obs 1-D slope via existing
        # pass-segmentation machinery over the same wavelength band when
        # WITHHELD_OBS carries (time, lat, lon, values) arrays.
```

Metrics: `spec_slope, spec_slope_wls_se, spec_slope_day_median, spec_slope_day_iqr, spec_n_modes_min` (+ `spec_slope_obs_1d`).

- [ ] **Step 4: PASS.** Accuracy `optional_context` + neither-branch `{}` test red→green.
- [ ] **Step 5: Commit** — `feat(phase11): SpectralFidelity evaluator + optional_context protocol extension (additive)`

### Task 5: Declared⇒consumed integrity test + EffectiveResolution declaration fix

**Goal:** Mechanize constraint 3 over the full evaluator family; fix the second declared-but-unread defect found at plan time.

**Files:**
- Modify: `src/sverdrup/eval/__init__.py` (new export `ALL_EVALUATORS: tuple[Callable[[], Evaluator], ...]` — factories for every registered evaluator; Task 6's `default_registry()` builds FROM this)
- Modify: `src/sverdrup/eval/resolution.py` (drop `ORBIT_GEOMETRY` from `required_context`; add `optional_context = frozenset()`)
- Modify: `tests/test_eval_resolution.py::test_effective_resolution_metadata` (pin update — enumerated in the table above)
- Create: `tests/test_evaluator_context_integrity.py`

**Acceptance Criteria:**
- [ ] Spy context records READS (`__getitem__`/`.get`); for every factory in `ALL_EVALUATORS`: (1) required ⊆ reads, (2) reads ⊆ required ∪ optional — on a fixture where the evaluator produces non-empty output
- [ ] Implementation note recorded in the test docstring: membership checks on a `keys()` COPY are untrackable; READS are what consume data, so rule 2 tracks reads (narrows the spec §6 wording honestly)
- [ ] The old GroundTrack stub pattern (declares, never reads) demonstrably fails rule 1 (regression canary: a deliberately-broken fake evaluator in the test file)
- [ ] `EffectiveResolution.required_context == {WITHHELD_OBS}`; full suite green (no Registry registers it — broadened applicability is a no-op, verified in Task-5 notes)

**Verify:** `pixi run pytest tests/test_evaluator_context_integrity.py tests/test_eval_resolution.py -v && pixi run test` → all PASS

**Steps:**

- [ ] **Step 1: Failing test:**

```python
class _SpyItems(dict):
    def __init__(self, data): super().__init__(data); self.reads: set = set()
    def __getitem__(self, k): self.reads.add(k); return super().__getitem__(k)
    def get(self, k, d=None): self.reads.add(k); return super().get(k, d)

FIXTURES = {...}  # per-evaluator (result, full-context-items) — reuses
                  # tests/test_eval_resolution._track() for EffectiveResolution,
                  # Task-3 synthetic maps for GroundTrack/SpectralFidelity.

@pytest.mark.parametrize("factory", ALL_EVALUATORS, ids=lambda f: f().name)
def test_declared_context_is_consumed(factory):
    ev = factory()
    result, items = FIXTURES[ev.name]
    spy = _SpyItems(items)
    out = ev.evaluate(result, EvalContext(spy))
    assert out, "fixture must exercise the non-skip path"
    assert ev.required_context <= spy.reads          # declared => READ
    assert spy.reads <= ev.required_context | ev.optional_context
```

All four `ContextKey` members appear in every fixture's `items` (a dormant key cannot hide).

- [ ] **Step 2: FAIL** (resolution violates rule 1 → proves the test bites). **Step 3:** fix `EffectiveResolution` declaration + the metadata-pin test; add `ALL_EVALUATORS`. **Step 4: PASS + full suite:** `pixi run test` green.
- [ ] **Step 5: Commit** — `test(phase11): declared=>consumed integrity test; fix EffectiveResolution over-declaration`

### Task 6: Context builder, `default_registry`, row builder, pipeline migration, dormant-wiring test

**Goal:** One wiring path for all surfaces (spec §7): builder sets `field_kind` + geometry + wedge masks; row builder produces schema'd rows incl. visible skip rows; pipeline sites migrate; harness gains the report block with a dev-scope test.

**Files:**
- Create: `src/sverdrup/application/eval_context.py`
- Modify: `src/sverdrup/application/pipeline.py` (both Registry sites, currently at ~285 and ~373)
- Modify: `src/sverdrup/application/calibration/harness.py` (append `report_only_instruments` block to future evidence packs)
- Modify (enumerated pins): `tests/test_phase2_stage_a.py`, `tests/test_phase2_stage_b.py`, `tests/test_gmrf_blend.py`, `tests/test_degradation_path.py`, `tests/integration/test_vertical_slice.py`, `tests/oracle/test_oi_oracle.py`
- Test: `tests/test_eval_context.py`, addition to `tests/test_calibration_harness.py`

**Acceptance Criteria:**
- [ ] `build_eval_context` sets `field_kind` (mean/sigma/other) — the σ-guard's single source; assembles ORBIT_GEOMETRY from the Task-1 artifact filtered by the product's `assimilated_missions` attr (space-separated); precomputes `track_wedge_masks` for fidelity
- [ ] `build_report_rows(registry, result, context)` returns one row per APPLICABLE evaluator with full schema (`schema_version`, `evaluator`, `evaluator_version`, `metrics`, `context_keys_available/used`, `params`, `n_modes`, `flags`, `provenance`); evaluator returning `{}` → visible skip row (`flags: ["no_usable_context"]`, `context_keys_used: []`); guard raise propagates (crashes the run)
- [ ] Pipeline: both sites use builder + `default_registry()` + row builder; scores shape = `{"report_rows": [...], "context_keys": ..., "fidelity": ..., "blend_transforms": ...}`; the six enumerated test files updated via `row_metric()` helper; `Registry.run()` docstring notes the collision hazard, unit-test consumers untouched
- [ ] Dormant-wiring test: dev-scope harness run (12-day fixture path, artifact-gated skipif) asserts `report_only_instruments` present with ≥ 2 rows and full schema

**Verify:** `pixi run test` → suite green (updated pins included)

**Steps:**

- [ ] **Step 1: Failing tests** for builder + row builder (skip row, σ routing, schema completeness):

```python
def test_skip_row_is_visible_not_silent():
    rows = build_report_rows(Registry([Accuracy()]), result_mean, EvalContext({}))
    (row,) = rows
    assert row["flags"] == ["no_usable_context"]
    assert row["context_keys_used"] == []
    assert row["metrics"] == {}

def test_default_registry_matches_all_evaluators():
    assert {type(e).__name__ for e in default_registry()._evaluators} \
        == {type(f()).__name__ for f in ALL_EVALUATORS if f().name != "effective_resolution"}
    # EffectiveResolution excluded THIS PHASE: its inputs (eval_locations/
    # eval_times) are not part of the standard result payload the builder
    # assembles; recorded decision (obligation 3) — integrity coverage comes
    # from ALL_EVALUATORS, not default_registry.
```

- [ ] **Step 2: FAIL.** **Step 3: Implement** `eval_context.py` (builder + `default_registry()` = Accuracy, Calibration, NormalizedSkillScore, GroundTrack, SpectralFidelity + row builder); `context_keys_used` from a spy-items wrap of the real context at row-build time (same `_SpyItems` mechanism, imported from a small shared helper).
- [ ] **Step 4: Migrate pipeline site 1 (~line 285)**, run its tests, then site 2 (~line 373); update the six enumerated test files with `row_metric(scores, "accuracy", "rmse")` style access. Run: `pixi run test` → green.
- [ ] **Step 5: Harness block + dormant-wiring test** (artifact-gated), red→green.
- [ ] **Step 6: Commit** — `feat(phase11): registry wiring — context builder, default_registry, report rows w/ skip rows; pipeline migrated (deliberate shape change)`

### Task 7: Retroactive one-shot (`scripts/phase11_retro_run.py`)

**Goal:** Score both shipped/regenerated mean-map products with the rebuilt evaluators; record numbers + provenance at `phase11.retro.*`; headline into PROGRESS.

**Files:**
- Create: `scripts/phase11_retro_run.py`
- Test: `tests/test_phase11_retro.py` (schema + provenance-refusal unit tests on tmp evidence files; the real run is executed once, manually)
- Modify: `PROGRESS.md` (headline block, format pinned above)

**Acceptance Criteria:**
- [ ] Script derives/loads the geometry artifact (assimilated union; **never opens the c2 file**), builds contexts via the Task-6 builder from each product's `assimilated_missions` attr, runs `build_report_rows`, writes `phase11.retro.{miost|oi}.{groundtrack|spectral_fidelity}` + `phase11.retro.provenance` via the nested-key atomic pattern
- [ ] Provenance: sha256 of `stage_b_mean_maps.nc`, `oi_mean_maps.nc`, AND the signed anchor `OSE_ssh_mapping_OURS_OI.nc` (batch-2 pin 3), + geometry artifact sha + `DERIVATION_VERSION`; when a recorded sha exists in the evidence JSON for an input, MISMATCH → refuse before scoring; absent → record as first anchor with a note
- [ ] Full per-ring `n_modes` table recorded in the retro blocks (script-side via shared prep; evaluator metrics stay flat)
- [ ] Existing evidence keys untouched (test: unrelated keys byte-identical before/after a tmp-file run)
- [ ] One-shot executed on the real artifacts; numbers land in evidence + PROGRESS headline; commit message carries the headline numbers

**Verify:** `pixi run pytest tests/test_phase11_retro.py -v` → PASS; then `pixi run python scripts/phase11_retro_run.py` → prints the headline block and writes evidence

**Steps:**

- [ ] **Step 1: Failing unit tests** (tmp evidence file: schema, refusal on sha mismatch, unrelated-keys preservation).
- [ ] **Step 2: FAIL. Step 3: Implement** (mirrors `phase10_compare.py` structure: `_read_evidence`/`_write_evidence` + `atomic_write_json`):

```python
_RESULTS = Path("data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json")
_PRODUCTS = {
    "miost": Path(".../ours/stage_b_mean_maps.nc"),
    "oi": Path(".../ours/oi_mean_maps.nc"),
}
_OI_SIGNED_ANCHOR = Path(".../ours/OSE_ssh_mapping_OURS_OI.nc")
```

- [ ] **Step 4: PASS. Step 5: Run the one-shot on the real artifacts.** Capture stdout; append the PROGRESS headline block (format pinned above).
- [ ] **Step 6: Commit** — `feat(phase11): retro one-shot — MIOST + OI mean-map numbers recorded at phase11.retro.* (<headline numbers in body>)`

### Task 8: Policy seam module (`application/policy.py`)

**Goal:** Comparison-only pairwise-criterion chain: `sort()` (unbanded-only, refuses banded) + `winner()` (sequential pinned-order reduction, always audited).

**Files:**
- Create: `src/sverdrup/application/policy.py`
- Test: `tests/test_policy.py`

**Acceptance Criteria:**
- [ ] `sort()` with any `banded=True` criterion → `ValueError`; property test (hypothesis-free, seeded-random records) documents banded intransitivity (constructs a~b, b~c, a beats c) in a comment + asserts `winner()` handles that triple deterministically in list order
- [ ] `sort()` with a single unbanded criterion is byte-identical to `sorted(key=...)` on 200 seeded-random record lists, ties included (stable order preserved) — gate (iii) property test
- [ ] `winner()` returns `(winner, [StageAudit, ...])`; audit schema per stage: `{criterion, verdict, detail}`; terminal all-TIE returns the FIRST candidate with full audit (matches folds' keep-running-winner semantics)

**Verify:** `pixi run pytest tests/test_policy.py -v` → all PASS

**Steps:**

- [ ] **Step 1: Failing tests** (cmp-vs-key identity, banded-sort refusal, reduction order). **Step 2: FAIL. Step 3: Implement:**

```python
class Verdict(Enum):
    A_WINS = auto(); B_WINS = auto(); TIE = auto()

@dataclass(frozen=True)
class Criterion:
    name: str
    compare: Callable[[Any, Any], Verdict]
    banded: bool = False
    detail: Callable[[Any, Any], dict[str, Any]] | None = None  # audit values/Δ/band

@dataclass(frozen=True)
class StageAudit:
    criterion: str
    verdict: str
    detail: dict[str, Any]

class LexicographicPolicy:
    def __init__(self, criteria: Sequence[Criterion]): ...
    def compare(self, a, b) -> tuple[Verdict, list[StageAudit]]:
        trail = []
        for c in self.criteria:
            v = c.compare(a, b)
            trail.append(StageAudit(c.name, v.name, c.detail(a, b) if c.detail else {}))
            if v is not Verdict.TIE:
                return v, trail
        return Verdict.TIE, trail
    def sort(self, candidates: list) -> list:
        if any(c.banded for c in self.criteria):
            raise ValueError("banded criteria form a semiorder — sort() is refused; use winner()")
        def _cmp(a, b):
            v, _ = self.compare(a, b)
            return {-1: -1, 1: 1}.get(-1 if v is Verdict.A_WINS else 1 if v is Verdict.B_WINS else 0, 0)
        return sorted(candidates, key=cmp_to_key(_cmp))
    def winner(self, candidates: Sequence) -> tuple[Any, list[list[StageAudit]]]:
        w, audits = candidates[0], []
        for c in candidates[1:]:
            v, trail = self.compare(c, w)
            audits.append(trail)
            if v is Verdict.A_WINS: w = c
        return w, audits
```

- [ ] **Step 4: PASS. Step 5: Commit** — `feat(phase11): lexicographic Policy seam — comparison-only criterion chain, banded sort refused`

### Task 9: Site migration 1 — `ConstrainedObjective.rank` (identity gate iii)

**Goal:** Delegate the sort to the seam; bar-filter + `NoAdmissibleTrial` stay put; byte-identical order.

**Files:**
- Modify: `src/sverdrup/application/tuning/objective.py` (`rank` body only)
- Test: additions to `tests/test_tuning_objective.py`

**Acceptance Criteria:**
- [ ] `rank()` = same filter, then `LexicographicPolicy((Criterion("lambda_x", ...),)).sort(ok)` with `A_WINS iff a.scores[primary] < b.scores[primary]`
- [ ] ALL existing objective tests pass UNCHANGED (`test_ranks_by_lambda_x_among_admissible` et al.)
- [ ] Gate (iii): new test — 200 seeded-random TrialRecord lists, `rank()` output identical (object identity per position) to the pre-migration `sorted(ok, key=...)` expression, ties included

**Verify:** `pixi run pytest tests/test_tuning_objective.py tests/test_policy.py -v && pixi run test` → green — gate green in THIS commit

**Steps:**

- [ ] **Step 1:** Write the gate-(iii) identity test against the CURRENT implementation (green), keep it. **Step 2:** Migrate `rank()`. **Step 3:** Test still green + suite green. **Step 4: Commit** — `refactor(phase11): objective.rank through the Policy seam — sort order byte-identical (gate iii)`

### Task 10: Site migration 2 — `folds.select` (identity gate i)

**Goal:** Express the S→T→smooth reduction as three banded criteria closures over the ABSOLUTE ±`TIE_BAND` helpers; eligibility + negative path stay put; behavior byte-equivalent.

**Files:**
- Modify: `src/sverdrup/application/calibration/folds.py` (`select`'s winner loop only)
- Test: `tests/test_calibration_folds.py` (existing select tests must pass unchanged)

**Acceptance Criteria:**
- [ ] Eligibility filter and `(None, lanes)` negative path byte-identical; winner loop replaced by `LexicographicPolicy((s_crit, t_crit, pref_crit)).winner(eligible)` where each criterion mirrors `_beats_beyond_band` exactly (A_WINS iff challenger beats, B_WINS iff incumbent beats, else TIE; pref: A_WINS iff strictly lower `_pref_rank`, else TIE)
- [ ] Candidate order pinned = `eligible` list order (legacy semantics — `winner()` reduction is the same loop shape)
- [ ] All six existing `test_select_*` tests pass UNCHANGED
- [ ] Gate (i) green in this commit: `SVERDRUP_PHASE9_EXTERNAL=1 pixi run pytest tests/test_calibration_harness.py::test_harness_on_miost_reproduces_phase8_evidence_leaf_identical -v` → PASS (artifacts present in this workspace)

**Verify:** the two commands above → all PASS — leaf-identical gate green in THIS commit

**Steps:**

- [ ] **Step 1:** Run the leaf-identical external test PRE-migration (baseline PASS, output captured). **Step 2:** Migrate the loop:

```python
def _s_crit(a, b):
    ca, cb = float(a["s_stat"]), float(b["s_stat"])
    if _beats_beyond_band(ca, cb): return Verdict.A_WINS
    if _beats_beyond_band(cb, ca): return Verdict.B_WINS
    return Verdict.TIE
# _t_crit analogous on t_stat; _pref_crit: A_WINS iff _pref_rank(a) < _pref_rank(b)
winner, _audit = LexicographicPolicy((
    Criterion("s_stat", _s_crit, banded=True),
    Criterion("t_stat", _t_crit, banded=True),
    Criterion("smooth_preference", _pref_crit),
)).winner(eligible)
```

- [ ] **Step 3:** Unit tests green; leaf-identical external test POST-migration PASS (same evidence). **Step 4: Commit** — `refactor(phase11): folds.select through the Policy seam — leaf-identical harness gate green (gate i)`

### Task 11: Site migration 3 — `lane_compare` (identity gate ii)

**Goal:** Route `select_lane_winner`'s top-2 adjudication and `primary_verdict`'s branch logic through the seam; bands stay read-time data; λ-degradation = drop the λ criterion; branch strings + wording emitted from the audit trail, verbatim.

**Files:**
- Modify: `src/sverdrup/application/tuning/lane_compare.py`
- Test: `tests/test_lane_compare.py` (existing tests unchanged) + `tests/test_phase10_verdict_reproduction.py` (new)

**Acceptance Criteria:**
- [ ] Sealed-protocol machinery, refusal clock, `compute_bands`, `_lambda_usable` untouched; the seam receives criteria closing over ONE `BandValues` (computed by the site, or LOADED — bands-as-data)
- [ ] Branch mapping from audit: `select_lane_winner` → {mu-clear, mu-primary-degraded, lambda-tiebreak, mu-leader-tie-held, single-admissible}; `primary_verdict` one-sided criteria → {beats-mu, beats-lambda-at-flat-mu, within-band}; wording strings byte-identical to current
- [ ] All existing `test_select_winner_*` / verdict tests pass UNCHANGED
- [ ] Gate (ii) green in this commit: new test loads `phase10.oi.lanes.verdict` from `data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json` (artifact-gated skipif), reconstructs `BandValues` from its PERSISTED fields (never recomputes), runs the seam-backed adjudication, asserts `branch == "within-band"` AND `wording == "improvements within band"` (string-equality)

**Verify:** `pixi run pytest tests/test_lane_compare.py tests/test_phase10_verdict_reproduction.py -v` → all PASS — verdict-reproduction gate green in THIS commit

**Steps:**

- [ ] **Step 1:** Extract `_adjudicate(bv, usable, ...)` accepting `BandValues` directly (the reproduction entry point), delegating branch selection to `LexicographicPolicy.winner()` over the pair with criteria:

```python
def _mu_crit_one_sided(bv):     # primary_verdict: A_WINS iff bv.delta_mu > bv.band_mu
def _lambda_crit_one_sided(bv): # A_WINS iff -bv.delta_lambda_x > bv.band_lambda_x
# select_lane_winner uses the symmetric variants (abs(delta) > band picks the side)
criteria = [mu_crit] + ([lambda_crit] if usable else [])  # degradation = DROP, seam has no conditionals
```

- [ ] **Step 2:** Existing tests green. **Step 3:** Write the gate-(ii) reproduction test, run → PASS. **Step 4: Commit** — `refactor(phase11): lane_compare through the Policy seam — Phase-10 verdict reproduced from persisted records (gate ii)`

### Task 12: Phase-close owner review (USER GATE) + PROGRESS close + push

**Goal:** Present the complete phase evidence to the owner; on approval record the close in PROGRESS and push.

> **USER-ORDERED GATE — NON-SKIPPABLE.** This task was requested by the user in the current conversation. It MUST NOT be closed by walking around it, by declaring it "verified inline", or by substituting a cheaper check. Close only after every item in `acceptanceCriteria` has been re-validated independently, with output captured.

**Files:**
- Modify: `PROGRESS.md` (phase-close banner; Current-work refresh)

**Acceptance Criteria:**
- [ ] Retro numbers present at `phase11.retro.{miost|oi}.{groundtrack|spectral_fidelity}` with provenance shas (`jq` output captured)
- [ ] Gate (i) output captured: leaf-identical harness test PASS post-migration
- [ ] Gate (ii) output captured: `tests/test_phase10_verdict_reproduction.py` PASS (branch + wording string-equal)
- [ ] Gate (iii) output captured: objective identity property test PASS
- [ ] Integrity + dormant-wiring tests PASS; full suite green: `pixi run test` output captured; `pixi run pytest --cov` run before the close commit
- [ ] Registry METHODS/SHIPPED untouched; mean-map files bit-unchanged (shas re-asserted); zero c2 (no task in this plan opens the c2 file — re-checked)
- [ ] OWNER APPROVES the evidence pack in conversation; then PROGRESS close banner committed + pushed

**Verify:** `pixi run test` → green; `jq '.phase11.retro | keys' data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json` → `["miost", "oi", "provenance"]`; owner approval message on record

**Steps:**

- [ ] **Step 1:** Assemble the evidence summary (retro numbers, three gate outputs, suite counts) in conversation. **Step 2:** STOP for owner review. **Step 3:** On approval: PROGRESS close banner + Current-work refresh, `git commit -m "docs(progress): PHASE 11 CLOSED — reference-free evaluators produced their first recorded numbers"`, push.

---

## Task dependency graph

```
Task 1 (geometry) ──┐
Task 2 (spectrum) ──┼→ Task 3 (GroundTrack) ─┐
Task 2 ─────────────┼→ Task 4 (Fidelity) ────┼→ Task 5 (integrity) → Task 6 (wiring) → Task 7 (retro)
Task 8 (policy) → Tasks 9, 10, 11 (migrations, independent of 1–7)
Tasks 7 + 9 + 10 + 11 → Task 12 (owner gate)
```

## Standing discipline (every task)

TDD red/green per behavior (test-design skill applies); `pixi run pre-commit run --all-files` before every commit; dual review per task; push after every task; behavioral pins inviolable — structural asserts may track the reviewed shape change only where this plan enumerates it (the fork-d pin-1 table). Zero c2: no task reads `dt_gulfstream_c2_*`; the geometry provider REFUSES mission id `c2` by test.
