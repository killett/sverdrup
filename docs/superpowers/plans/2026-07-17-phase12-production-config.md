# Phase 12 — Production Configuration (six-mission MIOST) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-run the shipped MIOST product with j3 assimilated (six missions), everything
frozen from the signed record, one acceptance chain, ONE c2 touch; on owner sign-off,
repoint SHIPPED["miost"].

**Architecture:** Configuration change only. New phase12 scope cfg (declared-null
validation role) + new runner script (`smoke` / `run` / `c2-touch` modes) + shared
evidence-schema module (writer and touch-asserter import the same field names).
Everything frozen: winner params verbatim, s(x) field cal_key-asserted, m=100,
seed root 4836134738817689931 (exact int), caps [500,2000,8000], pcg_rtol 1e-6.

**Spec:** `docs/superpowers/specs/2026-07-17-phase12-production-config-design.md`
— **the spec governs on any conflict with this plan.**

**Tech Stack:** Python (existing sverdrup src/ + scripts/ layout), pytest, pixi.

**User decisions (already made):**
- Fork a: repoint SHIPPED["miost"] ON SIGN-OFF only; three-branch owner ruling; miost5/miost6 two-generation naming.
- Fork b: declared-null cfg (`val_track_path: null` + `no_validation_reason`), refusal tests, same train loader, derived roles.
- Fork c: evidence floor + Tier-3 (anchor 0.0472 m / 0.761@100 / 0.930@200) + σ-map delta as pre-registered structural signature (STOP on absent j3-track imprint).
- Fork d: one solve, two authorized steps; closed-input-set hash tripwire incl. MEMBER STORE; smoke measures budget before launch; CRN shared-mission assert.
- Coverage baseline referent: 0.7350 (0.7350370172152351, field-calibrated c2 aggregate); 0.7481 quoted beside as scalar-era.
- P0-1: DISARM in-phase before the evidence run. P0-2: leave-on-queue, hardened to blocking precondition.
- T9 executes ONLY on the owner's sign-off message (not on the mechanical verdict).
- Geometry derives ONCE (T4); smoke asserts presence + classification outcome.
- Hold this plan for owner review before execution. Zero c2 before T8's authorization.

**Standing gotchas (from PROGRESS):** pre-commit-check-tasks hook blocks commits while a
native task is in_progress (mark completed → commit → re-open if needed). NEVER edit
source while the gate suite or a long solve runs. `rg`/`fd`, never grep/find. `pixi run`
for all tools.

---

## File structure

- Create `src/sverdrup/validation/phase12_config.py` — scope-cfg schema + loader +
  pinned refusal texts (obligation 1). One responsibility: declare and validate the
  six-mission product's mission roles.
- Create `src/sverdrup/validation/phase12_evidence.py` — evidence-key layout under
  `phase12.miost6.*`, provenance hash FIELD NAMES, hash helpers, pack-writer merge +
  touch-time assert (obligation 5: shared by construction — both sides import this).
- Create `scripts/phase12_miost6_run.py` — the ONE new runner: `--smoke`, `--run`,
  `--c2-touch` (obligation 8). Never imports from `stage_miost_gate_run.py`.
- Create `tests/validation/fixtures/phase12_miost6_scope.json` — the phase12 scope cfg
  (12-day dev days; `--run` derives full-year the same way `_scope()` does).
- Modify `scripts/stage_miost_gate_run.py` (ONE deliberate legacy edit: P0-1 disarm).
- Modify `docs/hygiene-priorities.md` (P0-1 resolution note + P0-2 blocking-precondition
  wording).
- Create `docs/validation/phase12_flip_census.md` — census artifact (obligation 2).
- Tests: `tests/test_phase12_config.py`, `tests/test_phase12_evidence.py`,
  `tests/validation/test_stage_miost_disarm.py`.
- Evidence file (gitignored, NEW — never the phase-8 RESULTS):
  `data/2021a_ssh_mapping_ose/ours/phase12_miost6_results.json`.
- Artifacts (gitignored, NEW names): `phase12_orbit_geometry_miost6.json`,
  `phase12_miost6_mean_maps.nc`, `phase12_miost6_var_maps.nc`,
  `phase12_miost6_members.npz`, dev-smoke maps under `phase12_dev_smoke_*`.

## Pinned strings (obligation 1 — testable, verbatim)

```python
# phase12_config.py
NO_VALIDATION_REFUSAL = (
    "REFUSED: this product has no validation track "
    "(no_validation_reason='j3-assimilated') — j3 is assimilated; no quantity "
    "can be refit without a leak"
)
# stage_miost_gate_run.py disarm
INLINE_TOUCH_DISARMED = (
    "REFUSED: the inline stage-b c2 touch is DISARMED (hygiene P0-1) — use "
    "--c2-touch, which carries _assert_c2_untouched and the pre-registered "
    "_c2_reading (template mechanics; fresh owner authorization required)"
)
```

---

### Task 1: P0-1 disarm + P0-2 queue hardening

**Goal:** The inline env-gated c2 touch in `stage_b_main` becomes a refusal naming
`--c2-touch`; the READY early-return is preserved; `docs/hygiene-priorities.md` gets the
P0-1 resolution note and the P0-2 blocking-precondition wording.

**Files:**
- Modify: `scripts/stage_miost_gate_run.py` (~lines 801–817, the block after the
  seam-dispersion record in `stage_b_main`)
- Modify: `docs/hygiene-priorities.md` (P0 section, entries 1 and 2)
- Test: `tests/validation/test_stage_miost_disarm.py`

**Acceptance Criteria:**
- [ ] `rg -n 'sb\["c2_acceptance"\]' scripts/stage_miost_gate_run.py` → ZERO hits in
      `stage_b_main` (the only remaining acceptance writes live in the `--c2-touch`
      mode's functions).
- [ ] Env set (`SVERDRUP_MIOST_C2=1`) → `stage_b_main`'s tail path raises
      `SystemExit(2)` with the pinned `INLINE_TOUCH_DISARMED` text; the c2 file is
      never opened; the signed `stage_b.c2_acceptance` key in the evidence JSON is
      untouched (test uses a tmp copy of a minimal RESULTS dict).
- [ ] Env unset → READY early-return preserved (flush text still contains
      "READY: evidence assembled; c2 NOT touched").
- [ ] `docs/hygiene-priorities.md` P0-1 entry gains: "RESOLVED (Phase 12, spec §5):
      inline path disarmed — the env branch refuses, naming --c2-touch." P0-2 entry
      gains: "BLOCKING PRECONDITION (pre-registered, Phase 12): any future plan
      invoking tune_miost_inflation or writing stage_b_* canonical names fixes this
      first. Detection covered by sha-anchored external pins."

**Verify:** `pixi run pytest tests/validation/test_stage_miost_disarm.py -v` → all PASS;
`pixi run test` green.

**Steps:**

- [ ] **Step 1: Extract the refusal into a testable helper + write failing tests**

Add to `scripts/stage_miost_gate_run.py` (module level, near `_assert_c2_untouched`):

```python
INLINE_TOUCH_DISARMED = (
    "REFUSED: the inline stage-b c2 touch is DISARMED (hygiene P0-1) — use "
    "--c2-touch, which carries _assert_c2_untouched and the pre-registered "
    "_c2_reading (template mechanics; fresh owner authorization required)"
)


def refuse_inline_touch(env: dict[str, str] | None = None) -> None:
    """Disarmed inline touch (hygiene P0-1): the env flag now REFUSES here.

    The single acceptance touch lives exclusively in the --c2-touch mode,
    which carries _assert_c2_untouched + the pre-registered _c2_reading.

    Raises:
        SystemExit: code 2 with INLINE_TOUCH_DISARMED when the flag is set.
    """
    e = os.environ if env is None else env
    if e.get("SVERDRUP_MIOST_C2") == "1":
        raise SystemExit(INLINE_TOUCH_DISARMED)
```

`tests/validation/test_stage_miost_disarm.py` (use the existing
`tests/helpers.load_script` loader from the hygiene pass):

```python
"""P0-1 disarm: the inline stage-b touch refuses; --c2-touch is the only touch.

Bugs caught: the legacy env branch re-spending the one authorized touch and
overwriting the signed sb["c2_acceptance"] with scalar-era semantics; a
refusal that still opens the c2 file; loss of the READY early-return.
"""
from __future__ import annotations

import pytest

from tests.helpers import load_script

gate = load_script("stage_miost_gate_run")


def test_env_set_refuses_with_pinned_text() -> None:
    with pytest.raises(SystemExit) as exc:
        gate.refuse_inline_touch({"SVERDRUP_MIOST_C2": "1"})
    assert "--c2-touch" in str(exc.value)
    assert "DISARMED" in str(exc.value)


def test_env_unset_is_noop() -> None:
    gate.refuse_inline_touch({})  # no raise


@pytest.mark.parametrize("val", ["0", "true", "", " 1"])
def test_non_exact_values_are_noop(val: str) -> None:
    gate.refuse_inline_touch({"SVERDRUP_MIOST_C2": val})  # no raise


def test_stage_b_main_never_writes_acceptance() -> None:
    """Source-level pin: no sb["c2_acceptance"] assignment remains in stage_b_main."""
    import inspect

    src = inspect.getsource(gate.stage_b_main)
    assert 'sb["c2_acceptance"]' not in src
    assert "refuse_inline_touch" in src
```

- [ ] **Step 2: Run tests — confirm FAIL** (`refuse_inline_touch` undefined)

Run: `pixi run pytest tests/validation/test_stage_miost_disarm.py -v`
Expected: FAIL / AttributeError.

- [ ] **Step 3: Apply the disarm edit in `stage_b_main`**

Replace the current tail (env check + touch block, ~801–817) with:

```python
    refuse_inline_touch()
    _flush(
        "READY: evidence assembled; c2 NOT touched (the inline touch is "
        "disarmed — the single acceptance touch lives in --c2-touch)"
    )
    _log("stage-b READY (c2 untouched; inline touch disarmed)")
    return
```

Delete the entire `if os.environ.get("SVERDRUP_MIOST_C2") != "1": ... return` block AND
the touch block below it (`_flush("RUNNING: the single c2 touch")` through the
`sb["c2_acceptance"] = {...}` write and its `_flush`/`_log` lines).

- [ ] **Step 4: Run tests — confirm PASS**; run full suite

Run: `pixi run pytest tests/validation/test_stage_miost_disarm.py -v` → PASS.
Run: `pixi run test` → green (any test that exercised the inline touch path must be
updated to the refusal semantics — expected: none exist; verify).

- [ ] **Step 5: Edit `docs/hygiene-priorities.md`** — append to entry 1:
"**RESOLVED (Phase 12, spec §5): disarmed** — the env branch in `stage_b_main` now
refuses, naming `--c2-touch`; test `tests/validation/test_stage_miost_disarm.py`." and
to entry 2: "**BLOCKING PRECONDITION (pre-registered, Phase 12, spec §5):** any future
plan invoking `tune_miost_inflation` or writing `stage_b_*` canonical names fixes this
first. Detection covered by the sha-anchored external pins (loud at the next sweep)."

- [ ] **Step 6: Commit**

```bash
git add scripts/stage_miost_gate_run.py tests/validation/test_stage_miost_disarm.py docs/hygiene-priorities.md
git commit -m "fix: disarm inline stage-b c2 touch (P0-1) + harden P0-2 queue entry"
```

---

### Task 2: phase12 scope cfg — schema, loader, refusal tests

**Goal:** Declared-null mission-role cfg for miost6: schema-validated loader; pinned
refusal text; the named no-default grep test; five-mission files byte-untouched.

**Files:**
- Create: `src/sverdrup/validation/phase12_config.py`
- Create: `tests/validation/fixtures/phase12_miost6_scope.json`
- Test: `tests/test_phase12_config.py`

**Acceptance Criteria:**
- [ ] Required keys, exact: `mapping_obs_paths` (6 entries, all exist, mission codes ==
      {alg,h2g,j2g,j2n,j3,s3a} via `input_adapter._mission_code`; c2 refused there),
      `val_track_path` (MUST be present AND null), `validation_mission` (present AND
      null), `no_validation_reason` (== "j3-assimilated"), `c2_track_path`,
      `mdt_paths`, `time_min`, `time_max`, `smoke_days` (12-day dev list),
      `mean_map_out`, `var_map_out`, `member_store_out`, `window_id`.
- [ ] MISSING `val_track_path` key → `Phase12ConfigError` naming the key (absence ≠
      declared null). `val_track_path` non-null → error carrying
      `NO_VALIDATION_REFUSAL`.
- [ ] `require_validation_track(scope)` raises with the pinned `NO_VALIDATION_REFUSAL`
      text — the function every validation-flavored entry point can call.
- [ ] Named test `test_no_default_for_val_track_path`: scans `src/` + `scripts/` text
      for the regex `\.get\(\s*["']val_track_path["']\s*,` → zero hits.
- [ ] Refusal tests (spec §2 pin 2): the s-fit harness path
      (`application/calibration/harness.py` reads `cfg["val_track_path"]` at :325 —
      handed the phase12 cfg dict, it KeyErrors/raises, never binds j3) and a direct
      `require_validation_track` refusal — both asserted.
- [ ] Five-mission fixtures untouched: `git diff --stat tests/validation/fixtures/stage_a_scope.json src/sverdrup/validation/input_adapter.py` → empty.

**Verify:** `pixi run pytest tests/test_phase12_config.py -v` → all PASS.

**Steps:**

- [ ] **Step 1: Write failing tests** (schema happy path from the new fixture; missing-key
error; non-null error text; `require_validation_track` refusal; no-default grep test;
harness-cfg refusal). Test bodies follow the AC exactly; the grep test:

```python
def test_no_default_for_val_track_path() -> None:
    """A .get('val_track_path', default) would silently j3-bind — forbidden."""
    import re
    from pathlib import Path

    pat = re.compile(r"\.get\(\s*[\"']val_track_path[\"']\s*,")
    hits = [
        f"{p}" for root in ("src", "scripts")
        for p in Path(root).rglob("*.py") if pat.search(p.read_text())
    ]
    assert hits == []
```

- [ ] **Step 2: Run — confirm FAIL** (module absent).
- [ ] **Step 3: Implement `phase12_config.py`**

```python
"""Phase-12 scope config: declared mission roles for the six-mission product.

val_track_path is REQUIRED and must be null: this product has no validation
track (j3 assimilated). Missing key = schema error; null = the declared
production state (spec §2, kernel=None precedent).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

REQUIRED_KEYS = frozenset({
    "mapping_obs_paths", "val_track_path", "validation_mission",
    "no_validation_reason", "c2_track_path", "mdt_paths", "time_min",
    "time_max", "smoke_days", "mean_map_out", "var_map_out",
    "member_store_out", "window_id",
})
MIOST6_MISSIONS = frozenset({"alg", "h2g", "j2g", "j2n", "j3", "s3a"})
NO_VALIDATION_REFUSAL = (
    "REFUSED: this product has no validation track "
    "(no_validation_reason='j3-assimilated') — j3 is assimilated; no quantity "
    "can be refit without a leak"
)


class Phase12ConfigError(ValueError):
    """Schema violation in the phase12 scope cfg."""


@dataclass(frozen=True)
class Phase12Scope:
    """Validated six-mission scope (roles declared, validation declared absent)."""

    mapping_obs_paths: tuple[Path, ...]
    c2_track_path: Path
    mdt_paths: tuple[Path, ...]
    time_min: str
    time_max: str
    smoke_days: tuple[float, ...]
    mean_map_out: Path
    var_map_out: Path
    member_store_out: Path
    window_id: str
    no_validation_reason: str


def load_phase12_scope(path: Path | str) -> Phase12Scope:
    """Load + schema-validate; missing keys and non-null validation roles refuse."""
    from sverdrup.validation.input_adapter import _mission_code

    raw = json.loads(Path(path).read_text())
    missing = sorted(REQUIRED_KEYS - set(raw))
    if missing:
        raise Phase12ConfigError(f"phase12 scope missing required keys: {missing}")
    if raw["val_track_path"] is not None or raw["validation_mission"] is not None:
        raise Phase12ConfigError(NO_VALIDATION_REFUSAL)
    if raw["no_validation_reason"] != "j3-assimilated":
        raise Phase12ConfigError(
            "no_validation_reason must be 'j3-assimilated' (the declared state)"
        )
    paths = [Path(p) for p in raw["mapping_obs_paths"]]
    codes = {_mission_code(p) for p in paths}  # raises on c2/unknown
    if codes != MIOST6_MISSIONS:
        raise Phase12ConfigError(
            f"mapping missions {sorted(codes)} != {sorted(MIOST6_MISSIONS)}"
        )
    return Phase12Scope(
        mapping_obs_paths=tuple(paths),
        c2_track_path=Path(raw["c2_track_path"]),
        mdt_paths=tuple(Path(p) for p in raw["mdt_paths"]),
        time_min=raw["time_min"],
        time_max=raw["time_max"],
        smoke_days=tuple(float(d) for d in raw["smoke_days"]),
        mean_map_out=Path(raw["mean_map_out"]),
        var_map_out=Path(raw["var_map_out"]),
        member_store_out=Path(raw["member_store_out"]),
        window_id=str(raw["window_id"]),
        no_validation_reason=raw["no_validation_reason"],
    )


def require_validation_track(scope: Phase12Scope) -> None:
    """Every validation-flavored entry point refuses here with the declared reason."""
    raise Phase12ConfigError(NO_VALIDATION_REFUSAL)
```

Fixture `tests/validation/fixtures/phase12_miost6_scope.json`: six dc_obs paths
(alphabetical: alg, h2g, j2g, j2n, j3, s3a), `"val_track_path": null`,
`"validation_mission": null`, `"no_validation_reason": "j3-assimilated"`, c2 path,
mdt_paths as in `stage_a_scope.json`, `time_min/time_max` = the dev fixture's 12-day
window, `smoke_days` = the stage_a dev fixture's day list,
`mean_map_out/var_map_out/member_store_out` =
`data/2021a_ssh_mapping_ose/ours/phase12_miost6_{mean_maps.nc,var_maps.nc,members.npz}`,
`window_id: "phase12-miost6"`.

- [ ] **Step 4: Run — PASS**; **Step 5: Commit** `feat: phase12 declared-null scope config + refusal tests`

---

### Task 3: SHIPPED-consumer census + pin-retarget table (flip-prep)

**Goal:** The committed list the flip commit executes (obligation 2): every
`SHIPPED["miost"]` consumer + every external pin bound to the five-mission product,
with a per-pin retarget decision.

**Files:**
- Create: `docs/validation/phase12_flip_census.md`

**Acceptance Criteria:**
- [ ] Census commands recorded verbatim IN the doc with their full output:
      `rg -n 'SHIPPED\[|SHIPPED\.get|shipped=True|shipped_miost' src scripts tests README.md`
      plus `rg -n 'SVERDRUP_.*EXTERNAL' tests` and a README/PROGRESS grep for
      "miost" product claims.
- [ ] Per-hit table: file:line | role (consumer / external pin / doc claim) | flip
      action. Known rows (verify + complete during the task): `methods/registry.py:36`
      (the SHIPPED entry — repoints); `tests/test_registry_roles.py:22` (identity
      assert — retargets to `shipped_miost6`); `tests/test_miost_method.py:58,82`
      (SHIPPED consumers — behavior identical, mission-set-agnostic: no edit expected,
      confirm); `tests/test_phase8_identity_regression.py` +
      `tests/fixtures/capture_phase8_factory_bytecompat.py` +
      `tests/test_miost_ensemble.py` field/factory pins (five-mission lineage —
      retarget to the named `shipped_miost5` factory);
      `scripts/stage_miost_gate_run.py:970,996` (five-mission regeneration — pins to
      `shipped_miost5` via a `shipped_key` argument or stays byte-untouched with a
      census note, decide in-doc); `capture_phase9_provenance_fixture.py` (record
      script — note-only).
- [ ] Factory plan stated: `methods/miost.py` keeps the existing factory as
      **`shipped_miost5`** (rename with `shipped_miost = shipped_miost5` alias until
      flip; alias retired AT flip) and gains **`shipped_miost6()`** — identical frozen
      solver/calibration config, separate function for provenance/docstring; flip sets
      `SHIPPED["miost"] = shipped_miost6`.
- [ ] NEW-pin list for miost6 named (captured at flip, T9): six-mission factory pin +
      six-mission map sha pins.
- [ ] Doc states: executed at T9 ONLY on the owner's sign-off message.

**Verify:** doc committed; every census command's output embedded; no "TBD" rows.

**Steps:**
- [ ] Step 1: run the census commands, embed outputs.
- [ ] Step 2: write the per-pin table + factory plan.
- [ ] Step 3: commit `docs: phase12 flip census + pin-retarget table`.

---

### Task 4: six-mission orbit-geometry artifact (the ONE derivation)

**Goal:** Derive `phase12_orbit_geometry_miost6.json` with j3's FIRST classification;
the gap rider fires HERE and blocks here if tabled.

**Files:**
- Create: `scripts/phase12_geometry.py` (thin driver)
- Test: extend `tests/test_phase12_config.py` with an artifact-gated presence test

**Acceptance Criteria:**
- [ ] `build_geometry_artifact("data/2021a_ssh_mapping_ose/dc_obs", ["alg","h2g","j2g","j2n","j3","s3a"], 38.1, OURS/"phase12_orbit_geometry_miost6.json")`
      runs; returns sha; sha recorded under `phase12.miost6.geometry` (via the T5
      evidence module — if T5 not yet landed, the driver prints the sha and the record
      lands at T5's first write; the artifact file itself is the durable output).
- [ ] j3 classified; expected repeat-class. If `classify_orbit` raises RATIO_GAP →
      STOP, report the measured ratio verbatim, TABLE for owner (the Phase-11 rider
      working); do NOT proceed to T5/T6.
- [ ] Artifact carries per-family ratios + cluster-size medians (v3 schema, existing
      behavior); five-mission `phase11_orbit_geometry.json` byte-untouched.
- [ ] j3's measured repeat ratio + family rows quoted in the commit message.

**Verify:** `pixi run python scripts/phase12_geometry.py` → prints artifact sha + j3
family rows; artifact JSON exists; `pixi run test` green.

**Steps:**
- [ ] Step 1: driver script (mirror `phase11_retro_run.py:235` call shape, new
      out-path, six missions).
- [ ] Step 2: run; inspect j3 rows; STOP on gap-tabling.
- [ ] Step 3: presence test (skipif artifact absent, pattern of existing
      artifact-gated tests): loads JSON, asserts `"j3"` families present and
      orbit-class == "repeat".
- [ ] Step 4: commit `feat: six-mission orbit-geometry artifact (j3 first classification)`.

---

### Task 5: evidence schema + runner (solve, pack, deltas, Tier-3) — no c2 anywhere

**Goal:** `phase12_evidence.py` (shared schema) + `scripts/phase12_miost6_run.py`
`--run` mode: six-mission full-year solve at the frozen config → maps + member store +
telemetry + report rows + deltas + Tier-3 row, incrementally written to the NEW
evidence file. CRN shared-mission assert included. ZERO c2 capability in this task.

**Files:**
- Create: `src/sverdrup/validation/phase12_evidence.py`
- Create: `scripts/phase12_miost6_run.py`
- Test: `tests/test_phase12_evidence.py`

**Acceptance Criteria:**
- [ ] `phase12_evidence.py` defines the key layout + hash-field names, used by BOTH
      writer and (T8) touch-asserter:
      keys `phase12.miost6.{geometry,telemetry,budget,report_rows,deltas,tier3,provenance,c2_acceptance}` +
      `phase12_dev_smoke.*`;
      `PROVENANCE_HASH_FIELDS = ("mean_maps_sha256", "var_maps_sha256", "member_store_sha256", "cal_key", "scope_cfg_sha256", "geometry_artifact_sha256")`;
      `provenance_block(paths...) -> dict` (sha256 helpers);
      `assert_provenance_matches(recorded, recomputed)` raising on any field mismatch.
- [ ] Writer merge is incremental and sibling-preserving — **named anti-clobber test**
      (spec §5 / fork-d pin): writing `phase12.miost6.telemetry` into a dict that
      already holds `phase12.miost6.geometry` + a foreign sibling
      `phase8.c2_acceptance` leaves both intact (read-modify-write of ONE leaf key).
- [ ] Runner path-constants test: `phase12_miost6_run.py` contains
      `stage_miost_gate_results.json` NOWHERE (`rg` in test); its RESULTS constant is
      `phase12_miost6_results.json`.
- [ ] Seed-root literal test (spec §1): `derive_seed("miost", "stage-b-winner", "members", 0) == 4836134738817689931` (int equality).
- [ ] `--run` sequence (code in the script, reviewed not unit-tested end-to-end):
      load `Phase12Scope` → frozen winner params read from the signed record
      (`results["winner"]["params"]`, full precision, asserted equal to
      `stage_b.winner_params`) → `load_mapping_obs` (six paths) → `halo_obs` framing →
      member gen via `merged_members` at caps [500,2000,8000] / pcg_rtol 1e-6 / m=100 /
      root `derive_seed("miost","stage-b-winner","members",0)` → `mean_fields` /
      `std_fields` → `write_map(..., assimilated_missions=_assimilated(obs))` to
      `phase12_miost6_{mean,var}_maps.nc` → wrapper `save_state` →
      `phase12_miost6_members.npz` (cal fields included, cal_key asserted vs
      `phase8_field.json` at load) → telemetry + report rows
      (`build_eval_context(geometry_artifact=phase12_orbit_geometry_miost6.json, assimilated_missions=attr)`
      → `default_registry()` → `build_report_rows`) → mean/σ deltas vs
      `stage_miost_acceptance.nc` / `stage_b_var_maps.nc` (RMS/max/map + the
      j3-track-localization read) → Tier-3 row vs
      `dc_maps/OSE_ssh_mapping_MIOST.nc` (RMS + coherence@{100,150,200} km, the
      `diag_miost_tier3.py` method) → `provenance` block written LAST.
- [ ] σ-signature STOP wired: if the Δσ track-localization read shows NO j3-track
      imprint (localization ratio ≤ 1 — Δσ along j3 tracks not exceeding the
      off-track median), the runner writes the delta block, prints
      "STOP: sigma-signature ABSENT — attribute before any touch (spec §4b')" and
      exits nonzero.
- [ ] CRN shared-mission assert (smoke-scope duty, implemented here): function
      `crn_shared_mission_assert(scope)` replays **s3a** member draws against the
      five-mission derivation and asserts bit-equality (identity-keyed perturbations).
- [ ] Guard demo capability: `assert_scored_not_assimilated(phase12_mean_maps, j3_track_path)`
      raises — exercised in smoke (T6), function importable here.
- [ ] `--run` REFUSES to launch if `phase12.miost6.budget` is absent from the evidence
      file (obligation 4: launch blocked on the recorded derivation).

**Verify:** `pixi run pytest tests/test_phase12_evidence.py -v` → PASS; `pixi run test`
green; `rg -n 'c2' scripts/phase12_miost6_run.py` → only the `--c2-touch` stub refusing
"not implemented until T8" + `c2_track_path` passthrough (no c2 file open in this task).

**Steps:**
- [ ] Step 1: failing tests (schema fields, sibling-survival, path constants, seed
      literal). Step 2: FAIL. Step 3: implement `phase12_evidence.py` + runner
      skeleton with `--run`. Step 4: PASS + suite green. Step 5: commit
      `feat: phase12 evidence schema + miost6 runner (no c2 capability)`.

---

### Task 6: dev smoke (six jobs) + budget derivation

**Goal:** `--smoke` runs the six-job list on the 12-day scope; measurements feed the
budget template; the recorded derivation unblocks `--run`.

**Files:**
- Modify: `scripts/phase12_miost6_run.py` (`--smoke` mode)

**Acceptance Criteria (the six jobs, spec §4):**
- [ ] 1. Guard refusal demonstrated: j3-scoring of the smoke six-mission map raises
      via `assert_scored_not_assimilated`; c2-scoring path permitted (no c2 load —
      asserted by attr logic only).
- [ ] 2. Declared-null schema round-trip validated (load fixture; mutate to missing
      key → schema error; non-null → refusal text).
- [ ] 3. Geometry artifact ASSERTED present with j3 classified repeat (NO
      re-derivation — presence + stored-key check only).
- [ ] 4. CRN shared-mission assert green for **s3a**.
- [ ] 5. Per-window wall + peak RSS measured and recorded; budget derived and
      recorded under `phase12.miost6.budget` (template below).
- [ ] 6. Evidence-dest isolation: all smoke records under `phase12_dev_smoke.*`; the
      smoke never writes any `phase12.miost6.*` key EXCEPT `budget` (the one
      cross-over, recorded with `"source": "dev_smoke"`); smoke maps to
      `phase12_dev_smoke_{mean,var}_maps.nc`.

**Budget template (obligation 4, recorded verbatim with numbers filled):**

```
n_obs_smoke, n_obs_full        # halo-framed counts, measured
t_window_smoke [s], peak_rss_smoke [MiB]   # measured
G_full_per_window = 0.78 GB * (n_obs_full / 54_345)          # nnz ∝ n_obs
t_full_est = t_window_smoke * n_windows_full * (n_obs_full / n_obs_smoke)
peak_est = PeakModelPredicate.predicted_peak_bytes(winner) * 1.11   # Task-22 model
LAUNCH iff peak_est <= 0.5 * MemAvailable AND t_full_est <= 12 h
```

**Verify:** `pixi run python scripts/phase12_miost6_run.py --smoke` → "SMOKE: 6/6 jobs
PASS; budget recorded; LAUNCH criteria met" (or a named failing job); evidence file
holds `phase12_dev_smoke.*` + `phase12.miost6.budget`.

**Steps:** implement jobs → run → fix → re-run → commit
`feat: phase12 dev smoke (six jobs) + recorded budget derivation`.

---

### Task 7: authorized evidence run + pack assembly — OWNER GATE (pack review)

**Goal:** The one full-year six-mission solve; the complete pre-touch pack assembled
and reported for owner review. **USER GATE.**

> **USER-ORDERED GATE — NON-SKIPPABLE.** This task was requested by the user in the
> current conversation. It MUST NOT be closed by walking around it, by declaring it
> "verified inline", or by substituting a cheaper check. Close only after every item in
> `acceptanceCriteria` has been re-validated independently, with output captured.

**Files:** none created beyond artifacts; runner from T5.

**Acceptance Criteria (evidence axes = the pack's four legs + context):**
- [ ] Run launched only after the recorded budget derivation (T6) — launch log line
      quotes the recorded numbers.
- [ ] Solve telemetry: members converged at the standing caps; maxiter/batches
      recorded (`phase12.miost6.telemetry`).
- [ ] Report rows: GroundTrack + SpectralFidelity rows on the six-mission mean maps;
      j3-family row present; s3a-class comparison + the five-mission 0.410 standing
      baseline quoted beside (`phase12.miost6.report_rows`).
- [ ] Deltas: mean-map RMS/max/map vs the shipped five-mission product; Δσ with the
      j3-track-localization read — signature PRESENT (else the T5 STOP fired and this
      gate is not reached) (`phase12.miost6.deltas`).
- [ ] Tier-3 row vs anchor 0.0472 m / 0.761@100 / 0.930@200 — deviation attributed in
      the pack if outside tight agreement (`phase12.miost6.tier3`).
- [ ] Provenance block written LAST with all six `PROVENANCE_HASH_FIELDS`
      (`phase12.miost6.provenance`).
- [ ] Pack REPORT to owner: all rows verbatim from the evidence file (jq/python
      quoted), five-mission context numbers beside (µ 0.8572611954190728, λx 156.43,
      coverage 0.7350 / 0.7481-scalar-era, Tier-3 rows), σ-signature read, budget
      actuals vs estimate.
- [ ] NO c2 touched (grep the run log; the touch mode still refuses).

**Verify:** owner reviews the pack and answers; the touch (T8) proceeds only on the
owner's explicit pack-review approval.

---

### Task 8: the ONE c2 touch — OWNER GATE (three-branch ruling)

**Goal:** `--c2-touch`: fresh authorization, closed-input-set hash assert, window
tripwire, one-invocation mechanics, the c2 reading; report carries the three-branch
menu. **USER GATE.**

> **USER-ORDERED GATE — NON-SKIPPABLE.** This task was requested by the user in the
> current conversation. It MUST NOT be closed by walking around it, by declaring it
> "verified inline", or by substituting a cheaper check. Close only after every item in
> `acceptanceCriteria` has been re-validated independently, with output captured.

**Files:**
- Modify: `scripts/phase12_miost6_run.py` (implement `--c2-touch`)
- Test: extend `tests/test_phase12_evidence.py` (gate mechanics, pure — no data)

**Acceptance Criteria:**
- [ ] `check_authorized`: exact-string `SVERDRUP_MIOST_C2 == "1"` (phase8_gate_run
      pattern verbatim: any other value refuses, no data loaded). Unit-tested.
- [ ] Determinism tripwire at entry: recompute all six `PROVENANCE_HASH_FIELDS` from
      disk; `assert_provenance_matches(recorded, recomputed)` — any mismatch refuses
      BEFORE the c2 file is opened. Never a re-solve. Unit-tested with a tampered
      tmp copy.
- [ ] Window tripwire after load: n == 44,844 AND year-span (time bounds
      2017-01-01..2018-01-01) — else record `window_tripwire` block + exit nonzero
      (WindowTripwire semantics).
- [ ] One-invocation mechanics: first invocation writes
      `phase12.miost6.c2_acceptance`; a second requires
      `SVERDRUP_MIOST_C2_CORRECTED=1` + a dated defect key migrating the first
      (defect-preservation semantics per template); a third refuses. Unit-tested on
      dict fixtures.
- [ ] The reading recorded: (µ, σ, λx) via `their_eval.score`; coverage/chi2/CRPS on
      the calibrated σ (member store + s(x) field, cal_key asserted); regional +
      monthly tables (phase8 binning); honest tally block
      `{"miost5": 2, "miost6": 1}`.
- [ ] REPORT to owner carries the three-branch menu with the §3 reading quoted
      verbatim: bar 0.6827±0.10; baseline 0.7350 (0.7481 scalar-era beside); expected
      landing above; µ ≥ 0.85 hard floor; branches: **sign-off** (→ T9) / **HOLD**
      (above-band: SHIPPED untouched, disposition tabled) / **no-flip** (µ < 0.85:
      finding stands, frozen-ρ-at-higher-density recorded). The ruling is the OWNER'S
      message.
- [ ] Zero c2 before this task's authorization (phase invariant restated in the gate
      report).

**Verify:** mechanics unit tests PASS without data; the authorized invocation's full
output captured in the gate report; owner returns one of the three branches.

---

### Task 9: flip commit + full external sweep (executes ONLY on owner sign-off)

**Goal:** One commit: SHIPPED repoint + σ-semantics + README/leaderboard claims +
tally + pin retargeting per the T3 census + FULL external sweep green.

**Precondition (hard):** the owner's T8 message is **sign-off**. HOLD or no-flip → this
task closes as superseded per branch semantics (Phase-8 Task-13 precedent); the close
(T10) records the branch taken.

**Files:**
- Modify: `src/sverdrup/methods/miost.py` (`shipped_miost5` named factory +
  `shipped_miost6`), `src/sverdrup/methods/registry.py` (SHIPPED repoint),
  README.md (product table, headline + five-mission reference, 0.89 matched-convention
  comparison), σ-semantics doc location per census, every pin in the T3 table.
- Test: updated pins (miost5 retargets; NEW miost6 external pins captured).

**Acceptance Criteria:**
- [ ] `SHIPPED["miost"] is shipped_miost6`; `shipped_miost5` importable and
      constructible; registry disjointness tests green.
- [ ] σ-semantics paragraph per spec §3 pinned structure ("transferred-and-verified"
      verbatim; measured c2 coverage + regional rows as THIS product's record).
- [ ] README/leaderboard wording: six-mission number headline at matched convention vs
      0.89; five-mission number beside as calibration-lineage reference; honest tally.
- [ ] Every T3 census row executed; NEW miost6 external pins captured (factory +
      map shas).
- [ ] FULL external/artifact-gated sweep green (standing rule, second application) —
      counts quoted in the commit message.

**Verify:** `pixi run test` green + external sweep command(s) from the census doc green
→ counts captured; single flip commit.

---

### Task 10: phase close — checks, PROGRESS banner, tally

**Goal:** Close verification with captured output; PROGRESS close banner; honest tally.

**Files:**
- Modify: `PROGRESS.md`

**Acceptance Criteria (spec §10, all captured):**
- [ ] Zero j3-side evaluation of miost6:
      `rg -n 'val_track|their_score|score\(' scripts/phase12_miost6_run.py` reviewed —
      no j3 scoring path; plus the guard-refusal test green.
- [ ] Byte-untouched diff check, enumerated paths:
      `git diff <pre-phase-sha> -- tests/validation/fixtures/stage_a_scope.json src/sverdrup/validation/input_adapter.py src/sverdrup/application/calibration/constants.py`
      → empty. The P0-1 disarm commit named in the banner as the ONE deliberate
      legacy-script edit (`stage_miost_gate_run.py` deliberately NOT in the check's
      path list).
- [ ] Seed-root literal test green; suite green (counts recorded).
- [ ] PROGRESS close banner: branch taken (sign-off/HOLD/no-flip), measured numbers
      verbatim (µ, σ, λx, coverage vs 0.7350 referent, chi2/CRPS), tally table
      miost5: 2 / miost6: 1, flip-commit sha (if taken), external sweep counts,
      untouched list verbatim.
- [ ] Explicit PROGRESS edit steps: (1) insert close banner above the design-committed
      banner; (2) mark the design-committed banner `[closed above]`; (3) refresh the
      "next action" line.

**Verify:** `pixi run test` green; PROGRESS committed + pushed; working tree clean.

---

## Dependencies

T1, T2, T3, T4 independent (T1 must land before any evidence run — enforced by T6/T7
ordering). T5 blocked by T2 + T4. T6 blocked by T1 + T5. T7 blocked by T3 + T6.
T8 blocked by T7. T9 blocked by T8 (+ owner sign-off message). T10 blocked by T9
(or by T8's HOLD/no-flip branch — close records the branch).

## Phase invariant

**ZERO c2 before T8's authorization.** The runner's `--c2-touch` refuses until T8; no
other code path in this plan can open the c2 file (T5 AC + T1 disarm + guard tests).
