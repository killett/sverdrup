# Phase 14 Stage 1 — Spatial-at-2017 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the six-tile Stage-1 measurement program (spec §6) against the
C0→1 contract — anchor identity first, then seam ORACLE, then four diverse
tiles at the frozen signed config — producing the Gate-1 pack (transfer
readings, seam verdicts, kernel decision pack, revisit verdict, refresh
election presentation).

**Architecture:** Everything rides Stage-0 machinery: `TileFrame`/`frame_grid`/
`tile_plan`/`blend` (0d-1/2), `score_tile` (0d-3), the dual-source loader
(dc2021a for anchor+seam-pair, CMEMS-MY `_202411` for non-box tiles, per the
§14 source map), `Miost(basis_domain=…)` + `size_tile`, the ladder. New code is
small and test-first: a seam-metric module (D_int/delta per the sealed rubric),
a per-tile run driver script, a kernel-arithmetic pack script. Measurement
policy: frozen signed config (`shipped_miost5` + PHASE13_WINNER_PARAMS), zero
new fits, zero touches, m=100 members at the signed root convention for
coverage/χ² rows.

**Tech Stack:** existing sverdrup stack (numpy/scipy sparse PCG, xarray/netCDF4,
typer, pixi). No new dependencies.

**User decisions (already made):**
- Gate 0 CLOSED/APPROVED 2026-07-23; seal v1 `a17ea419…b725c5d2` signed — every
  evidence pack quotes this sha (C0→1).
- ATTRIBUTION BEFORE ELECTION: every cross-lineage reading carries the
  golden-tile bridge caveat explicitly; **Stage-1 interpretation language
  WAITS on the owner's attribution readout** — packs record numbers + caveat,
  no cross-lineage interpretation prose until the readout.
- T18 cloud leg = ladder-enforced precondition on FIRST Tier-2 production use;
  C0→1 ships same-host tolerances + CRN-EQUAL; cross-host slot pending-T18.
- Stage 1 stays measured-first (task 1-0) regardless of probe ratios.
- Proximity = scoring-time filter, never membership change (sealed).
- Owner spend inputs: Stage 1 runs Tier 0/1 ($0) preferred; Tier 2 only per the
  pre-registered spend table — **no new ceilings pre-registered for Stage 1, so
  ANY Tier-2 need WAITs for the owner** (pre-registered-or-WAIT).
- Frozen five-mission workhorse on every tile (batch-1 pin 2c); six-mission
  refresh election is Gate 1's item with scope = Stage-2G onward.
- Standing discipline: zero evaluation-bearing maps until THIS PLAN is
  approved (they are sanctioned by its approval, PROBE/evidence-labeled);
  zero locked opens; tally untouched; ±66° not exceeded (Stage 1 caps at the
  SO tile, D4).

**⚖ OWNER ELECTIONS PENDING (plan-review pins 2 and 12 — HELD, not the
executor's to decide; the affected tasks REFUSE to run until ruled):**
- **Pin 2 — missing_neighbors convention for the four diverse tiles.**
  Isolated (all four sides missing) = 76×77 nodes; production-representative
  (2° overlap extension, no sides flagged missing) = 96×97 — a 1.59× node
  ratio that swamps T2's 1.3× STOP bracket if unstated, and on a stage where
  any Tier-2 need WAITs, the frame convention IS the spend decision. Owner's
  noted reading (not yet a ruling): production-representative — D1's 15/2
  default is what Stage 2G flies; the transfer measurement should be of
  production geometry. DECISION CELL EMPTY. **T2 (probe) and T5 refuse to
  dispatch until this is ruled and test-pinned in the registry.**
- **Pin 12 — equatorial box.** Proposed −4…11°N leaves 1° of core (5 grid
  rows at 0.2°) above the 10°N component edge — satisfies fork-b pin 4's
  letter, thin for "taper boundary becomes measurable". Options: keep
  (maximum in-band coverage; equator + TIW band well inside the core) or
  shift to −2…13°N (3° out-of-band; equator at the core edge). DECISION
  CELL EMPTY. **The equatorial run in T5 refuses until ruled.**

---

## File structure

| Path | Responsibility |
|---|---|
| `src/sverdrup/validation/seam_metrics.py` (create) | D_int, co-located delta, R ratio, verdict cell per the sealed rubric — pure functions |
| `tests/test_seam_metrics.py` (create) | hand-value + refusal tests |
| `scripts/phase14_stage1_run.py` (create) | per-tile run driver: frame → source-mapped load → frozen solve (m configurable) → score → evidence pack row (seal sha quoted) |
| `tests/test_phase14_stage1_run.py` (create) | CI-safe legs: tile registry, source map, refusals, evidence-pack shape |
| `scripts/phase14_kernel_pack.py` (create) | 1-4 arithmetic: measured SO anisotropy + f-range table + three options — pack assembly, no decision |
| `docs/superpowers/2026-XX-phase14-gate1-pack.md` (create at T9) | Gate-1 pack |
| `data/2021a_ssh_mapping_ose/ours/phase14_stage1/` | run artifacts (maps labeled per policy, evidence-pack JSONs) |

Tile registry (in `phase14_stage1_run.py`, exact frames):

```python
# D3 roster. ANCHOR IS NEVER RECONSTRUCTED: the registry CONSUMES the
# existing anchor_frame() (src/sverdrup/application/spatial_tiles.py:146
# — signed 10x10 core, overlap 0.0, all four sides missing, operative
# halo), the gate-5 substrate the skip-guarded identity test already
# scores against. Others: 15x15 cores (D1); frames built per the
# OWNER-RULED missing_neighbors convention (pin 2 — REFUSES until ruled).
TILES = {
    "anchor":     {"frame": "anchor_frame()", "source": "dc2021a",
                   "job": "identity gate (degenerate single tile)"},
    "seam_n":     {"core": (295.0, 305.0, 38.0, 43.0), "source": "dc2021a",
                   "missing_neighbors": frozenset({"W", "E", "N"}),
                   "job": "seam ORACLE north half (seam at 38.0N)"},
    "seam_s":     {"core": (295.0, 305.0, 33.0, 38.0), "source": "dc2021a",
                   "missing_neighbors": frozenset({"W", "E", "S"}),
                   "job": "seam ORACLE south half (seam at 38.0N)"},
    "equatorial": {"core": (200.0, 215.0, -4.0, 11.0), "source": "cmems_my",
                   "job": "in-band core crossing the 10N component edge "
                          "(fork-b pin 4) — BOX UNDER OWNER ELECTION "
                          "(pin 12); run REFUSES until ruled"},
    "southern":   {"core": (215.0, 230.0, -62.0, -47.0), "source": "cmems_my",
                   "job": "high-latitude honesty instrument (~54.5S center; "
                          "obs frame reaches -65.0S at halo 1.0 - 1.0 deg "
                          "margin to the +/-66 cap)"},
    "quiet_gyre": {"core": (255.0, 270.0, -30.0, -15.0), "source": "cmems_my",
                   "job": "low-signal regime (SE Pacific subtropics)"},
    "kuroshio":   {"core": (132.0, 147.0, 28.0, 43.0), "source": "cmems_my",
                   "job": "coastal/island-dense WBJ - exercises land mask"},
}
```

(Owner review 2026-07-25: southern/quiet_gyre/kuroshio boxes + the 38.0°N
seam split ENDORSED — the executor does not re-litigate them; equatorial
box + diverse-tile frame convention are HELD owner elections (pins 2/12
above). If an endorsed box turns out data-empty at load, STOP and surface.)

---

### Task 0: Seam-metric module (rubric → code, sealed thresholds)

**Goal:** `seam_metrics.py` computing D_int, co-located seam delta, R = delta/D_int, and the verdict cell (CLEAN ≤1.0 / ELEVATED ≤2.5 / STRUCTURAL-STOP >2.5) exactly per `docs/validation/phase14_seam_rubric.md`, consuming thresholds from `instrument_configs()` (never re-typed constants).

**Files:**
- Create: `src/sverdrup/validation/seam_metrics.py`
- Test: `tests/test_seam_metrics.py`

**Acceptance Criteria:**
- [ ] `interior_increment_rms(field, axis)` = pooled one-grid-step increment RMS along the axis PERPENDICULAR to the seam, interior points only (both cells inside one tile's core) — hand-value pinned on a 4×4 array
- [ ] `seam_delta(field_a, field_b, seam_nodes)` = RMS of co-located differences on the seam line — hand-value pinned
- [ ] `seam_verdict(r)` maps R to the three cells with EXACT boundary semantics (≤1.0 CLEAN, ≤2.5 ELEVATED, else STRUCTURAL_STOP); thresholds read from `instrument_configs()["seam"]` (keys `clean_max`/`elevated_max`) AT CALL TIME — pinned BEHAVIOURALLY via sentinel-config monkeypatch (0.3/0.5 → 0.4 is ELEVATED), never a source-string scan (the T11 vacuous-pin lesson)
- [ ] Rule-0 solver-floor validity gate inherited: `seam_read(...)` REFUSES (ValueError) when the underlying solves' PCG final residuals exceed rtol — an invalid solve never produces a verdict
- [ ] NaN handling: NaN nodes (land) excluded from both pools; all-NaN seam refuses

**Verify:** `pixi run pytest tests/test_seam_metrics.py -q` → all pass, no skips

**Steps:**

- [ ] **Step 1: failing tests** — hand-computed values:

```python
"""Seam-metric tests (Stage-1 T0; sealed rubric -> code)."""
import numpy as np
import pytest

from sverdrup.validation.phase14_instruments import instrument_configs
from sverdrup.validation.seam_metrics import (
    interior_increment_rms,
    seam_delta,
    seam_verdict,
)


def test_interior_increment_rms_hand_value() -> None:
    """4x4 arange ramp: axis-0 increments are all 4.0, axis-1 all 1.0.

    Bug caught: wrong-axis pooling (a seam-perpendicular D_int computed
    along the seam-parallel axis would read 1.0 where 4.0 is true) or
    off-by-one dropping the interior edge rows.
    """
    f = np.arange(16, dtype=float).reshape(4, 4)  # rows differ by 4, cols by 1
    assert interior_increment_rms(f, axis=0) == pytest.approx(4.0)
    assert interior_increment_rms(f, axis=1) == pytest.approx(1.0)


def test_seam_delta_hand_value() -> None:
    """Two constant fields differing by 2 cm on a 3-node seam -> 0.02."""
    a = np.full(3, 0.05)
    b = np.full(3, 0.03)
    assert seam_delta(a, b) == pytest.approx(0.02)


def test_verdict_cells_exact_boundaries() -> None:
    """Boundary semantics: <=1.0 CLEAN, <=2.5 ELEVATED, else STOP.

    Bug caught: strict-vs-inclusive boundary flip at either threshold.
    """
    assert seam_verdict(1.0) == "CLEAN"          # boundary inclusive
    assert seam_verdict(1.0000001) == "ELEVATED"
    assert seam_verdict(2.5) == "ELEVATED"
    assert seam_verdict(2.5000001) == "STRUCTURAL_STOP"


def test_verdict_thresholds_read_from_sealed_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """BEHAVIOURAL pin: sentinel thresholds change the verdict.

    Bug caught: re-typed literal thresholds in seam_metrics — a module
    ignoring instrument_configs would still say CLEAN at 0.4 under the
    sentinel. (Replaces a string no-literal scan: the Stage-0 T11
    vacuous-pin lesson — source scans trip on unrelated literals and
    pass vacuously on reformatted ones. Requires seam_verdict to read
    the config AT CALL TIME, which is also the sealed-config contract.)
    """
    import sverdrup.validation.seam_metrics as sm

    def sentinel_configs() -> dict:
        cfg = instrument_configs()
        cfg["seam"] = dict(cfg["seam"], clean_max=0.3, elevated_max=0.5)
        return cfg

    monkeypatch.setattr(sm, "instrument_configs", sentinel_configs)
    assert sm.seam_verdict(0.4) == "ELEVATED"
    assert sm.seam_verdict(0.6) == "STRUCTURAL_STOP"


def test_nan_exclusion_and_all_nan_refusal() -> None:
    a = np.array([0.05, np.nan, 0.05])
    b = np.array([0.03, np.nan, 0.03])
    assert seam_delta(a, b) == pytest.approx(0.02)
    with pytest.raises(ValueError, match="all-NaN"):
        seam_delta(np.array([np.nan]), np.array([np.nan]))
```

(Key names CONFIRMED against `phase14_instruments.py`: `clean_max` /
`elevated_max` at 1.0 / 2.5 — SEAM_CLEAN_MAX/SEAM_ELEVATED_MAX.)

- [ ] **Step 2:** run → confirm FAIL (module absent)
- [ ] **Step 3:** implement `seam_metrics.py` — pure numpy, docstrings citing the rubric doc + Rule-0; `seam_read` takes the two per-tile PCG residual maxima and rtol, refuses before computing
- [ ] **Step 4:** run → PASS; `pixi run pre-commit run --files …`
- [ ] **Step 5:** commit `feat: stage1 seam metrics per sealed rubric (D_int/delta/verdict)`

---

### Task 1: Per-tile run driver (CI-testable core)

**Goal:** `scripts/phase14_stage1_run.py` — one command runs one tile: frame from the registry, source-mapped load (source recorded in provenance), frozen-config solve (m option), per-tile scoring via `score_tile`, evidence-pack row written under `phase14.stage1.tiles.<tile>` quoting the seal sha.

**Files:**
- Create: `scripts/phase14_stage1_run.py`
- Test: `tests/test_phase14_stage1_run.py`

**Acceptance Criteria:**
- [ ] Registry carries the tiles above with per-tile `source`; CLI refuses an unknown tile and refuses `--source` override (source map is pinned, not an option)
- [ ] **Anchor frame CONSUMED, never reconstructed (review pin 1):** the registry's anchor entry resolves to the existing `anchor_frame()` — test-pins `frame_grid(registry_frame("anchor"), 0.2)` node arrays `==` `frame_grid(anchor_frame(), 0.2)` (the gate-5 substrate; a reconstructed TileFrame(core, 2.0, halo) would yield 71×72 nodes vs the signed 51×52)
- [ ] **Seam frames pinned (review pin 3):** `seam_n` missing_neighbors == `frozenset({"W","E","N"})`, `seam_s` == `frozenset({"W","E","S"})`; resulting solve bboxes test-pinned ([295,305]×[36,43] north / [295,305]×[33,40] south at 2° overlap toward the seam only)
- [ ] **Diverse-tile frame convention REFUSES until owner-ruled (⚖ pin 2):** building a frame for equatorial/southern/quiet_gyre/kuroshio raises RuntimeError naming the pending election while the convention constant is `None`; the ruled value lands as ONE registry constant + test-pin, never per-call-site
- [ ] Tier-1 predicate (`tier1_eligible(size_tile(...)["peak_model_mib"])`) runs BEFORE any load/solve; refusal exits nonzero naming the ladder (fork-g pin 4)
- [ ] Evidence row contains: `seal_sha` (read from `phase14.stage0.seal`, REFUSES if absent/unverifiable via `verify_current_seal()`), tile, source, frame, window plan, m, superobs cfg (cmems side only), n_obs, wall/peak, pcg rows, and the scores block per policy (b): j3-validation µ/λx/coverage/χ² + `reference_row: {"kind": "raw-sigma + scalar-s* transfer", "label": "REFERENCE-ONLY, NOT CALIBRATED"}` for non-anchor tiles
- [ ] Cross-lineage tiles (source=cmems_my) get `bridge_caveat` verbatim (review pin 7 — the delta carries ITS OWN provenance and disclaims transfer): "cross-lineage reading; golden-tile bridge delta MEASURED ON THE ANCHOR BOX (mu −0.012457 their_eval-scale, map RMS 4.10 cm); its magnitude at THIS tile is unmeasured; interpretation WAITS on the owner attribution readout" — test-pinned string
- [ ] Maps written under `phase14_stage1/` carry internal `label` attr: `"STAGE1-EVIDENCE"` (sanctioned by plan approval; the golden-tile PROBE lesson)
- [ ] CI tests run WITHOUT data: registry shape, refusals, evidence-row assembly with injected fakes; solve legs are data-gated skips with named reasons

**Verify:** `pixi run pytest tests/test_phase14_stage1_run.py -q` → pass (CI legs), skips named

**Steps:**

- [ ] **Step 1: failing tests** — registry pins (six tiles, sources match the §14 map: anchor+seam dc2021a, four others cmems_my), unknown-tile refusal, `--source` rejection, `build_evidence_row(...)` pure-function test with fakes asserting seal-sha presence + bridge-caveat exact string + reference-row label; seal-absent refusal via monkeypatched `verify_current_seal` raising
- [ ] **Step 2:** run → FAIL
- [ ] **Step 3:** implement. Skeleton (pattern: `phase14_golden_tile.py` — lazy imports, typer, atomic evidence writes; loads clipped to frame obs_bbox — the OOM lesson, commit 6984e26):

```python
@app.command()
def run(tile: str, m: int = 100, days_stride: int = 1) -> None:
    spec = TILES.get(tile) or _refuse_unknown(tile)
    frame = TileFrame(core=BBox(*spec["core"]), overlap_deg=2.0, halo_deg=operative_halo_deg())
    grid = frame_grid(frame, resolution_deg=0.2)
    model = size_tile(...)                      # from frame + window plan + m
    if not tier1_eligible(model["peak_model_mib"]):
        raise typer.Exit(code=1)                # ladder WAIT, printed
    verify_current_seal()                       # refuses unsealed context
    obs = _load_source(spec["source"], frame)   # clipped load; superobs on cmems
    ...  # merged_members(m) -> mean_fields over 2017 days -> write_map
    row = build_evidence_row(...)               # pure, unit-tested
    _record(row)                                # atomic, phase14.stage1.tiles.<tile>
```

- [ ] **Step 4:** CI tests PASS; pre-commit clean
- [ ] **Step 5:** commit `feat: stage1 per-tile run driver (source map pinned, seal-sha quoted)`

---

### Task 2: Stage Task 1-0 — measured-first probe (first non-anchor tile, reduced days)

**Goal:** The stage's sizing re-check before any full run: quiet-gyre tile, full 15°×15° geometry, reduced days (one window, m=1), measured vs `size_tile` model; ratios recorded next to the Stage-0 ratios.

**Files:**
- Modify: `scripts/phase14_stage1_run.py` (add `probe` command: one window, m=1, `label="PROBE"` map, evidence under `phase14.stage1.probe`)
- Modify: `tests/test_phase14_stage1_run.py` (probe row shape; PROBE label pin)

**⚖ GATED ON PIN 2:** this task DOES NOT DISPATCH until the owner rules the
diverse-tile missing_neighbors convention — the probe's measured-vs-model
ratio against the 1.3× STOP bracket is meaningless under an unstated 1.59×
node-count convention, and the frame convention IS the spend decision.

**Acceptance Criteria:**
- [ ] Probe runs quiet_gyre (CMEMS source — also the first real CMEMS-side solve at 15° geometry), ONE 60-day window, m=1, single mid-window day map, PROBE-labeled npz+evidence (never scored)
- [ ] `measured_vs_model` ratios recorded; model NOT retuned (constants diff-clean vs HEAD)
- [ ] If measured peak or wall exceeds model by >1.3× (the honest-bracket convention), STOP: record and surface to owner BEFORE full runs — a mis-sized model at 6 tiles × 9 windows is a spend decision, not an executor call
- [ ] RAM predicate refusal path exercised once in CI via fake meminfo (existing `tier1_eligible` test pattern)

**Verify:** `pixi run python scripts/phase14_stage1_run.py probe` → ratios printed; `pixi run pytest tests/test_phase14_stage1_run.py -q` green

**Steps:**
- [ ] **Step 1:** failing CI test for probe row shape (m=1 pinned, label PROBE, no scores block — a probe row with a µ would be an evaluation-bearing artifact)
- [ ] **Step 2:** FAIL → implement probe command (reuses run()'s internals with window subset) → PASS
- [ ] **Step 3:** REAL leg: run detached with log + stall watch (nohup + `python -u`; the OOM/silent-death lesson); verify evidence row
- [ ] **Step 4:** commit `feat: stage1 task-1-0 probe run + ratios recorded`

---

### Task 3: Anchor identity gate — five checks, NOTHING else runs until green

**Goal:** The signed box through the generalized tiling path reproduces the signed records: the §10 gate set with the Stage-0-completed halves cross-referenced, the rest run now.

**Files:**
- Create: `scripts/phase14_anchor_gate.py` (orchestrates checks 1/3/5 + assembles the five-gate evidence block; checks 2 and 4's Stage-0 halves referenced by evidence pointer)
- Test: `tests/test_phase14_anchor_gate.py` (assembly logic, refusals; the heavy legs data-gated)
- Modify: `tests/test_phase14_gate5_score_identity.py` — its skip guard flips ON when `phase14_stage1/anchor_signed_maps.nc` lands

**Acceptance Criteria:**
- [ ] **Check 1 (tiling identity):** anchor tile via the generalized path (TileFrame degenerate single tile → `frame_obs` → `Miost(basis_domain=solve bbox)` → m=100 at the signed root `derive_seed("miost","stage-b-winner","members",0)`) vs the signed acceptance records — four routes: member coefficient arrays sha-equal; mean maps vs acceptance rtol 1e-12; Γ-route; variance route (the Phase-13 T3 four-route pattern, reuse its comparators)
- [ ] **Check 2 (loader identity):** RECORDED as Stage-0 complete (evidence `gate2_loader_identity` PASS) + lineage-sensitivity = golden tile TABLED row — the gate block cites both, runs nothing
- [ ] **Check 3 (era no-op):** era-keyed calibration evaluated at the reference epoch ≡ signed s(x) EXACTLY — identity by construction at n_eff₀; asserted `==` (not approx) on the calibration surface values
- [ ] **Check 4 (cross-env):** same-host halves cited (T17 CRN-EQUAL manifests + solve manifests); cross-host slot recorded `pending-T18` per the Gate-0 ruling — the gate is GREEN with this slot explicitly pending, never silently
- [ ] **Check 5 (score-level):** `score_tile` on the anchor maps reproduces signed (µ, σ, λx) — AND the gate-5 constants (deferred at T14/Gate-0) PIN NOW into `phase14.stage1.gate5` from this run; the skip-guarded test goes live and passes
- [ ] Evidence block `phase14.stage1.anchor_gate` = five sub-blocks each pass/fail + artifact shas; ANY fail → the script exits nonzero and the plan STOPS (no downstream task starts)
- [ ] Zero touches: locked tally byte-identical before/after (asserted in the script)

**Verify:** `pixi run python scripts/phase14_anchor_gate.py` → "five gates GREEN" + evidence block; `pixi run pytest tests/test_phase14_gate5_score_identity.py -q` → 1 passed (no longer skipped)

**Steps:**
- [ ] **Step 1:** failing CI tests: gate-block assembly (five keys, fail-any-fail), tally-guard logic, check-3 exact-equality assertion with a fake calibration surface
- [ ] **Step 2:** implement orchestration; reuse Phase-13 T3 comparator functions (find via `rg "four-route" src/ scripts/` — do NOT reimplement sha/rtol comparators)
- [ ] **Step 3:** REAL leg (detached + stall watch, ~40–90 min Tier 1): m=100 full-2017 anchor solve through the tiling path; the four routes + score identity; gate-5 constants pinned write-once
- [ ] **Step 4:** dual review THIS TASK before any other tile runs (the gate is the stage's foundation)
- [ ] **Step 5:** commit `feat: stage1 anchor identity gate — five checks green, gate-5 constants pinned`

---

### Task 4: Seam-pair run + seam ORACLE read

**Goal:** Two standard tiles splitting the anchor footprint across the jet (seam at 38°N), blended via `assemble`; seam dispersion scored against the seamless anchor truth (Task 3's maps) under the sealed rubric — rubric before numbers.

**Files:**
- Modify: `scripts/phase14_stage1_run.py` (add `seam-pair` command: runs the registry's `seam_n`/`seam_s` tiles; `assemble`; seam read via `seam_metrics`)
- Modify: `tests/test_phase14_stage1_run.py` (frame pins: the two registry frames' missing_neighbors frozensets + solve bboxes; oracle-read wiring with fake fields)

**Acceptance Criteria:**
- [ ] Registry frames used verbatim (pin 3 frozensets: north {W,E,N}, south {W,E,S}); solve bboxes test-pinned ([295,305]×[36,43] / [295,305]×[33,40])
- [ ] Both tiles dc2021a source, frozen config, m=100, same roots convention as the anchor run — the ORACLE compares like against like
- [ ] Blended field via `assemble` (partition-of-unity machinery, zero-overlap refusal active); NaN never poisons
- [ ] ORACLE read: `seam_delta` between blended and seamless-anchor fields on the seam band + `interior_increment_rms` pooled from both tile interiors; R and verdict cell recorded; Rule-0 residual gate enforced
- [ ] Evidence `phase14.stage1.seam` = {R, verdict, D_int, delta, per-tile pcg maxima, oracle_note: "no published precedent — gap-register (T11)"}; verdict NEVER blocks the plan mechanically — STRUCTURAL_STOP surfaces to the owner (it is Gate-1's item, but work on OTHER tiles may continue: they don't consume seams)
- [ ] **Geometry caveat recorded (review pin 13):** the evidence row carries `geometry: "10x5 halves inside the anchor footprint — NOT D1 production geometry (15x15)"` + the explicit non-transfer sentence: the verdict is not a production-geometry seam reading, and the feasibility-frontier watch item (worst-seam grew with TILE COUNT, PROGRESS 2026-07-01) sits on the far side of that gap — discipline 7 applied to a positive result; test-pinned strings
- [ ] Zero touches; maps labeled STAGE1-EVIDENCE

**Verify:** `pixi run python scripts/phase14_stage1_run.py seam-pair` → verdict printed + evidence; CI: `pixi run pytest tests/test_phase14_stage1_run.py -q`

**Steps:** (same TDD shape as Task 2: frame-derivation + wiring tests red → implement → real leg detached → commit `feat: stage1 seam-pair + ORACLE read under sealed rubric`)

---

### Task 5: Diverse-tile runs (equatorial, Southern Ocean, quiet gyre, Kuroshio)

**Goal:** Four transfer measurements at frozen config, five-mission, CMEMS-MY source, per-tile evidence packs per policy (b) — including the equatorial lane-0 persistence bundle (fork-b pin 1) and the Kuroshio land-mask exercise.

**Files:**
- Modify: `scripts/phase14_stage1_run.py` (only if gaps surface; the `run` command from Task 1 should already do these)
- Modify: `tests/test_phase14_stage1_run.py` (data-gated legs + the absence pin below)

**⚖ PARTIALLY GATED:** the equatorial run REFUSES until the owner rules
pin 12 (box election); the other three tiles run once pin 2's convention
is ruled (they share T2's gate transitively).

**Acceptance Criteria:**
- [ ] Four runs recorded under `phase14.stage1.tiles.{equatorial,southern,quiet_gyre,kuroshio}` — each: µ/λx/coverage/χ² j3-validation rows + raw-σ + LABELED scalar-s* reference row + bridge_caveat verbatim + seal sha
- [ ] **Interpretation withholding is STRUCTURAL (review pin 8, the T7 absence-pin shape):** `build_evidence_row` output keys test-pinned as EXACTLY the schema set (no free-prose field exists to interpret in); plus a row-serialization absence pin — the strings "suggests", "consistent with", "attributable", "implies" appear NOWHERE in any tile row (test iterates the recorded rows)
- [ ] **Equatorial persistence (1-6):** beyond the pack row, persist maps + evidence pack + FROZEN fold/eval frame to `phase14_stage1/equatorial_lane0/` — the future wave-increment comparison substrate; a `lane0_manifest.json` with per-file shas; recorded under the frozen-config policy sentence (fork-b pin 2 verbatim in the manifest)
- [ ] **Southern Ocean:** additionally records measured anisotropy inputs for Task 6 (per-direction spectral/track diagnostics the kernel pack consumes — reuse `GroundTrack`/`SpectralFidelity` instrument families from T11 configs, per-tile×era parameterization)
- [ ] **Kuroshio:** land-mask path assertions — dropped-land handling in framing/scoring exercised; `n_scored_points` honest; any all-land core refusal surfaced not swallowed
- [ ] No interpretation prose anywhere — numbers + caveat only (owner rider; enforced by the structural pin above, not by intent)
- [ ] Each run detached + stall-watched; RAM predicate before each; zero touches throughout

**Verify:** four evidence rows present + `pixi run python scripts/phase14_seal_run.py check` still PASS (seal untouched) + tally byte-identical

**Steps:** run tiles SEQUENTIALLY (single-writer evidence; RAM); after each: verify row, commit evidence-side artifacts that are committable (manifests), `docs(progress)` note. Kuroshio FIRST among the four (it exercises the riskiest path — fail fast), then southern (feeds Task 6), then equatorial (persistence bundle), then quiet gyre. Commit per tile: `feat: stage1 <tile> transfer reading recorded`.

---

### Task 6: High-latitude kernel decision pack (1-4)

**Goal:** Assemble the owner's Gate-1 decision pack: SO-tile measured anisotropy + f-range arithmetic + the three options (km-space kernels / lat-varying degree scales / Paciorek — `PaciorekGaussianDegrees` exists, PD-proven, Phase 10) — arithmetic recorded, NO recommendation beyond the priced table, never inherited from the box-scale negative.

**Files:**
- Create: `scripts/phase14_kernel_pack.py`
- Test: `tests/test_phase14_kernel_pack.py` (arithmetic pins: cos-φ table hand-values; option-table shape; refusal without the SO evidence row)

**Acceptance Criteria:**
- [ ] f-range table: |f| at 38°N (box) vs 55°S vs the global range — the "~13% in-box cos-φ anisotropy becomes ~2–3× poleward" sentence made numeric (cos-φ ratios hand-value-pinned in tests)
- [ ] SO measured anisotropy from Task 5's diagnostics, presented next to the arithmetic
- [ ] Three options each with: what changes, what stays identical (anchor identity preserved — any option must keep gate-1 semantics at the box), halo auto-follow consequence (fork-d pin 4: halo derives from the operative kernel scale — each option's halo stated), implementation cost class
- [ ] **±66 breach column (review pin 10):** per option, the operative halo AND the resulting SO obs southern edge (edge = −(62 + 2 + halo)°; today −65.0 at halo 1.0); any option with halo > 2.0° is FLAGGED "±66 BREACH — owner ruling required" — arithmetic test-pinned so a Gate-1 kernel election can never move the frame past the cap silently
- [ ] Explicit sentence: "the box-scale negative (Phase 10) is NOT cited as transferring" — test-pinned
- [ ] Output = a markdown pack section + evidence block `phase14.stage1.kernel_pack`; DECISION CELL EMPTY (owner decides at Gate 1)

**Verify:** `pixi run pytest tests/test_phase14_kernel_pack.py -q`; `pixi run python scripts/phase14_kernel_pack.py` → pack section printed

**Steps:** TDD the arithmetic (red: cos-φ hand values) → implement → run on real SO row → commit `feat: stage1 kernel decision pack (arithmetic recorded, decision cell empty)`.

---

### Task 7: Phase-10 revisit — forked sub-design + run

**Goal:** The pre-registered revisit (D5/D6 sub-design, decided IN THIS PLAN): **per-tile lanes** (not a cross-tile shared field), TWO bands (the Phase-10 bands unchanged), budget = Tier-1 only, frozen config = lane-0, diverse tiles, real f range, zero touches.

**Sub-design (locked here, the fork-d pin-6 deferral resolved):**
- Per-tile lanes, NOT a shared cross-tile field: the Stage-1 question is "does the box-scale negative transfer per-regime?", which is a per-tile contrast; a shared field couples tiles through a global fit nobody pre-registered and pollutes the per-regime read. (Cross-tile sharing is Stage-2 calibration's business, fork E.)
- Bands: the exact Phase-10 band definitions, unchanged — a band change would confound the revisit with a re-design.
- Budget: Tier 0/1 only; if any lane's sizing demands Tier 2 → that lane WAITS (pre-registered-or-WAIT; no new ceilings exist).
- Lanes run on the four diverse tiles only (anchor is the identity subject, seam-pair is the seam subject — adding lanes there measures nothing new and spends).

**Files:**
- Modify: `scripts/phase14_stage1_run.py` (add `revisit` command; lane RUNNER machinery may be imported from the phase-13 runner, but lanes/bands come from phase-10 — see the AC below; NEVER copied)
- Modify: `tests/test_phase14_stage1_run.py` (lane-config pins: per-tile, band VALUES, tier guard)

**Acceptance Criteria:**
- [ ] **Band provenance pinned (review pin 9 — live confound):** lanes and dims from `sverdrup.validation.phase10_lanes` (`LANES` / `BOXES` / `ALL_DIMS`) and the PHASE-10 band protocol — NOT `phase13_lanes` and NOT the phase-13 band protocol (`phase13_band_artifact.json`), which the phase-13 runner pulls by default; the test pins the band VALUES (the `BOXES` numeric tuples) against `phase10_lanes.BOXES`, never "names verbatim" — a band change arriving through an import is exactly the confound the sub-design forbids
- [ ] Lane config test-pinned: 4 tiles × lanes {lane-0 frozen, + the phase-10 `LANES` set}, per-tile independent
- [ ] Evidence `phase14.stage1.revisit.<tile>` rows: per-lane per-band deltas vs lane-0, report-only, promotion sentence (fork-f pin 6) verbatim in each row
- [ ] Tier guard: any lane predicted over Tier-1 → recorded WAIT row, not run
- [ ] Zero touches; the box-scale negative never cited (string absent, test-pinned)

**Verify:** CI green; real rows present for all four tiles (or WAIT rows with sizing numbers)

**Steps:** TDD config pins → implement lane command → real legs (sequential, detached) → commit `feat: stage1 phase-10 revisit lanes (per-tile sub-design, report-only)`.

---

### Task 8: OSSE run decision (1-7) — priced, presented, DECIDED BY OWNER at Gate 1

**Goal:** Price the OSSE option from Stage-0/1 measured numbers and present fork-f pin 5's strongest value case; NO run in this plan unless the owner elects it at Gate 1. (Review pin 6: blocked on Task 5 — it prices from Task 5 actuals and must never dispatch while the anchor barrier is red.)

**Files:**
- Modify: the Gate-1 pack (Task 9) carries the priced section; no code

**Acceptance Criteria:**
- [ ] Price from measured constants: one OSSE = (truth-provider generation, existing dormant interface) + (constellation-varied re-solves ≈ N_epoch-classes × tile solve wall from Task 2/5 actuals) — a table in compute-hours on Tier 1, no cloud
- [ ] The strongest value case verbatim: "constellation varied over FIXED model truth is the only ground-truth test of the era-transfer claim (fork-e level 1 validates against fitted s; OSSE against truth)"
- [ ] Recommendation cell: PRESENT both "run at Stage-2 entry (when era-transfer is the live question)" and "run now" with their costs; decision cell EMPTY (⚖ owner, per the deferred-thread ledger)

**Verify:** section present in the Gate-1 pack with real measured numbers

---

### Task 9: Gate-1 pack + refresh-election presentation (userGate)

**Goal:** Assemble `docs/superpowers/2026-XX-phase14-gate1-pack.md` — owner attention items first — and STOP.

**USER-ORDERED GATE — NON-SKIPPABLE.** This task was requested by the user in the current conversation. It MUST NOT be closed by walking around it, by declaring it "verified inline", or by substituting a cheaper check. Close only after every item in `acceptanceCriteria` has been re-validated independently, with output captured.

**Files:**
- Create: `docs/superpowers/2026-XX-phase14-gate1-pack.md` (XX = actual date)
- Modify: `PROGRESS.md` (STOP block), `.tasks.json`

**Acceptance Criteria:**
- [ ] Pack contains, owner-items first: (1) anchor five-gate block (with cross-host slot pending-T18 explicit); (2) seam verdict + ORACLE numbers; (3) six transfer readings (numbers + bridge caveats, NO cross-lineage interpretation if the attribution readout hasn't ruled); (4) kernel decision pack (decision cell empty); (5) revisit verdict rows; (6) OSSE priced section (decision cell empty); (7) **six-mission-refresh election presentation** — presumptive rule verbatim: instrument-class match, δ_j3 := δ_j2n (Poseidon-series); own chain + touch if elected; scope = Stage-2G assembly onward; (8) spend actuals vs Tier-0/1 ($0 expected; any WAIT rows); (9) discipline attestation: zero locked opens, tally byte-identical, ±66° respected, seal `check` PASS
- [ ] Full sweep on the final tree recorded in the pack (with stall watch; every skip named)
- [ ] All Stage-1 real legs dual-reviewed before the pack posts (the Stage-0 pattern: reviews may batch, but the pack cites each verdict)
- [ ] PROGRESS.md STOP block + next-action; everything committed + pushed
- [ ] STOP after posting — Gate 1 is the owner's

**Verify:** pack file exists; `git status` clean; sweep green; STOP posted

```json:metadata
{"userGate": true, "tags": ["user-gate"], "files": ["docs/superpowers/2026-XX-phase14-gate1-pack.md"], "verifyCommand": "pixi run pytest -q -p no:cacheprovider", "acceptanceCriteria": ["pack posted with the nine sections", "full sweep green on final tree, skips named", "dual reviews cited", "STOP posted"], "requireEvidenceTokens": [["anchor", "five-gate", "identity"], ["seam", "verdict"], ["transfer", "tiles"]]}
```

---

## Execution notes (for the executor)

- **Order:** T0 ∥ T1 (file-disjoint) → T2 (probe; ⚖ gated on pin 2) → T3 (anchor gate — HARD BARRIER) → T4 → T5 → {T6, T7, T8} → T9. **T4/T5/T7 are SERIALIZED on the shared `phase14_stage1_run.py` + its test file (review pin 4)** — no interleaving; evidence writes single-writer; solves sequential (RAM).
- **Every long run:** nohup + `python -u` + log + completion AND stall watchers (the 10-hour-stall lesson + the OOM-silent-death gotcha, both in PROGRESS/memory).
- **Dual review per task** (owner's standing rider); no source edits during the final sweep.
- **The seal is read-only context:** `seal_run check` must PASS unchanged at T9. Any epoch/gauge/config drift discovered mid-stage is a STOP-for-owner, not a reseal.
- **Spend:** everything here is Tier 0/1 ($0). There are NO Stage-1 Tier-2 ceilings pre-registered: any Tier-2 need = WAIT row + owner surface.
