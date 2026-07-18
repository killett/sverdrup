# Phase 12 — SHIPPED-consumer census + pin-retarget table (flip-prep)

**Execution rule: every row in this table is executed at Task 9 ONLY on the
owner's sign-off message** (three-branch ruling, spec §3). HOLD or no-flip →
this doc stays as the record of what the flip *would* have executed.

Census taken 2026-07-17 at `ffaf423` + the Task-1 disarm edit (the ONE
deliberate legacy-script edit of the phase).

## Census commands + full output (verbatim)

### 1. SHIPPED consumers

```
$ rg -n 'SHIPPED\[|SHIPPED\.get|shipped=True|shipped_miost' src scripts tests README.md
tests/test_registry_roles.py:12:from sverdrup.methods.miost import shipped_miost
tests/test_registry_roles.py:22:    assert SHIPPED["miost"] is shipped_miost
tests/test_registry_roles.py:30:    """The ``shipped=True`` escape resolves SHIPPED, never METHODS.
tests/test_phase8_identity_regression.py:232:    params through ``shipped_miost()`` (m=100, STAGE_B_ROOT, factory
tests/test_phase8_identity_regression.py:249:    from sverdrup.methods.miost import shipped_miost
tests/test_phase8_identity_regression.py:277:    dist = shipped_miost().solve(train, grid, ConstantProvider(winner), 0.0)
tests/fixtures/capture_phase8_factory_bytecompat.py:8:``shipped_miost()`` itself bakes in members=100 / STAGE_B_ROOT, too heavy for
tests/fixtures/capture_phase8_factory_bytecompat.py:97:    # THROUGH THE FACTORY-equivalent config: shipped_miost() bakes in
tests/test_miost_ensemble.py:293:def test_shipped_miost_solve_records_field_inflation_provenance() -> None:
tests/test_miost_ensemble.py:296:    A solve from ``shipped_miost()`` must (a) be SAMPLES-native and (b) carry a
tests/test_miost_ensemble.py:307:    from sverdrup.methods.miost import shipped_miost
tests/test_miost_ensemble.py:313:        calibration=shipped_miost()._calibration,
tests/test_miost_ensemble.py:471:def test_shipped_miost_uses_phase8_poly_field() -> None:
tests/test_miost_ensemble.py:472:    """shipped_miost() carries the Phase-8 clipped-poly PolyCalibration.
tests/test_miost_ensemble.py:490:        shipped_miost,
tests/test_miost_ensemble.py:498:    cal = shipped_miost()._calibration
src/sverdrup/application/tuning/stage_miost.py:50:        # method — the shipped SAMPLES product lives in SHIPPED["miost"]
src/sverdrup/methods/registry.py:16:from sverdrup.methods.miost import Miost, shipped_miost
src/sverdrup/methods/registry.py:36:    "miost": shipped_miost,
src/sverdrup/methods/miost.py:743:def shipped_miost() -> Miost:
scripts/stage_miost_gate_run.py:969:    # SHIPPED; this regeneration wants the shipped product -> shipped=True.
scripts/stage_miost_gate_run.py:979:        shipped=True,
scripts/stage_miost_gate_run.py:1005:        shipped=True,
tests/test_miost_method.py:58:    shipped = SHIPPED["miost"]()
tests/test_miost_method.py:82:    shipped = SHIPPED["miost"]()
scripts/capture_phase9_provenance_fixture.py:79:    # Build the shipped product (same calibration as shipped_miost() but
```

### 2. External pin env gates

```
$ rg -n 'SVERDRUP_.*EXTERNAL' tests
tests/test_phase8_identity_regression.py:15:``SVERDRUP_PHASE8_EXTERNAL=1`` (the reconstruction is a full-obs m=100 member
tests/test_phase8_identity_regression.py:213:_EXTERNAL_ENV = "SVERDRUP_PHASE8_EXTERNAL"
tests/test_calibration_harness.py:8:    (env-gated: set SVERDRUP_PHASE9_EXTERNAL=1 to opt in; ~2.5 min runtime)
tests/test_calibration_harness.py:369:# Opt-in gate: SVERDRUP_PHASE9_EXTERNAL=1 (runtime ~2.5 min)
tests/test_calibration_harness.py:392:    os.environ.get("SVERDRUP_PHASE9_EXTERNAL", "") != "1",
tests/test_calibration_harness.py:394:        "leaf-identical harness regression; set SVERDRUP_PHASE9_EXTERNAL=1 to run "
tests/test_calibration_harness.py:454:    os.environ.get("SVERDRUP_PHASE9_EXTERNAL", "") != "1",
tests/test_calibration_harness.py:456:        "field byte-exact gate; set SVERDRUP_PHASE9_EXTERNAL=1 to run "
```

### 3. README / PROGRESS product claims

```
$ rg -n -i 'miost' README.md   (product-claim hits only, full list retained)
12:- `miost` — multiscale reduced-basis **MIOST-family ensemble** (calibrated per-gridpoint σ;
101:  - `miost` — multiscale wavelet reduced-basis ensemble (see the Validation section)
105:  - marginal variance (**exact** for `oi`/`gmrf`/`fem`; ensemble-calibrated for `miost`)
113:  `miost` is single-tile by design (its temporal windows blend within the one tile).
198:| `miost`    | `spacing_alpha`, `log10_rho`, `q_slope`, `l_t_days` (tuned values ship in the registry) | validation-track only: geometry is fixed to the 2021a Gulf-Stream box — run from a clone via the challenge harness (see Validation) |
237:BASELINE leaderboard row, and its MIOST-family method is tuned and accepted
246:| **sverdrup MIOST** (5 missions) | **0.857** | **0.080** | **156.4** |
247:| MIOST (published, 6 missions) | 0.89 | 0.08 | 139 |
250:independently trusted — it reproduces the published DUACS, MIOST, and BFN rows to
257:**MIOST verdict: PASS** against its hard floor (BASELINE µ ≥ 0.85, met at 0.857
258:on a single withheld-CryoSat-2 acceptance touch). The published MIOST row is an
273:identity-preserving on MIOST and demonstrated end-to-end on OI.
275:> **`sverdrup.validation` — and the MIOST tuning/gate harness and its
295:- [`docs/validation/`](docs/validation/) MIOST records — method brief, windowed-equivalence + seam-dispersion diagnostics, Tier-3 similarity (two-row), calibration evidence

$ rg -c 'miost' PROGRESS.md README.md
README.md:5      (case-insensitive product-claim hits above: 14)
PROGRESS.md:57   (historical record — never rewritten; close banner ADDS, spec §10)
```

## Per-hit table

| file:line | role | flip action (T9) |
|---|---|---|
| `src/sverdrup/methods/registry.py:16` | SHIPPED import | Import `shipped_miost5`, `shipped_miost6` (alias `shipped_miost` retired AT flip). |
| `src/sverdrup/methods/registry.py:36` | **THE SHIPPED entry** | `"miost": shipped_miost6` — the repoint. |
| `src/sverdrup/methods/miost.py:743` | the factory | Rename to `shipped_miost5`; add `shipped_miost6()` (see factory plan). |
| `tests/test_registry_roles.py:12,22` | identity assert | Retarget: `assert SHIPPED["miost"] is shipped_miost6`. |
| `tests/test_registry_roles.py:30` | `shipped=True` escape docstring | No edit — resolution semantics unchanged. |
| `tests/test_miost_method.py:58,82` | SHIPPED consumers | No edit expected (mission-set-agnostic: they call `SHIPPED["miost"]()` and test behavior identical under the frozen config) — CONFIRM green at flip. |
| `tests/test_phase8_identity_regression.py:232,249,277` | external pins, five-mission lineage (signed maps + member reconstruction) | Retarget to the named `shipped_miost5` factory — these pin the FIVE-mission signed artifacts forever. |
| `tests/fixtures/capture_phase8_factory_bytecompat.py:8,97` | capture-script comments referencing factory config | Retarget naming to `shipped_miost5` (comment-only; the captured fixture is a record). |
| `tests/test_miost_ensemble.py:293-313` | factory provenance pin | Retarget to `shipped_miost5` (five-mission calibration-lineage pin per plan decision). |
| `tests/test_miost_ensemble.py:471-498` | phase8 poly-field pin | Retarget to `shipped_miost5`; ADD the same assert against `shipped_miost6` (identical frozen calibration — both factories must carry the phase8 field). |
| `src/sverdrup/application/tuning/stage_miost.py:50` | comment | No edit — statement stays true post-flip (the shipped SAMPLES product still lives in SHIPPED["miost"]). |
| `scripts/stage_miost_gate_run.py:969,979,1005` | five-mission regeneration via `shipped=True` | **DECISION: stays byte-untouched.** The P0-1 disarm is the phase's ONE deliberate edit to this frozen runner. Census note (blocking precondition, same shape as hygiene P0-2): any future rerun of this regeneration path post-flip must first pin it to `shipped_miost5` — otherwise it would regenerate five-mission evidence through the six-mission factory. Detection: the sha-anchored external pins go loud. |
| `scripts/capture_phase9_provenance_fixture.py:79` | record script (builds config directly, no factory import) | Note-only — no edit. |
| `README.md:246-247,257-258` (+ claim lines above) | leaderboard + verdict claims | Rewrite per spec §3: six-mission headline at matched convention vs published 0.89; five-mission 0.857 row stays beside as calibration-lineage reference; honest tally; σ-semantics paragraph ("transferred-and-verified" verbatim). |
| `tests/test_calibration_harness.py:369-456` (`SVERDRUP_PHASE9_EXTERNAL`) | harness leaf-identity + field byte-exact externals | No edit — they pin the phase8/phase9 ARTIFACTS (harness evidence + `phase8_field.json`), not the SHIPPED symbol. CONFIRM green in the T9 full external sweep. |
| `PROGRESS.md` (57 hits) | historical record | Never rewritten — the T10 close banner ADDS the miost6 record. |

## Factory plan

`src/sverdrup/methods/miost.py`:

1. Rename the existing factory `shipped_miost` → **`shipped_miost5`**
   (docstring gains: five-mission calibration-lineage reference product,
   miost5 generation).
2. Keep `shipped_miost = shipped_miost5` as an alias **until flip; the alias
   is retired AT the flip commit** (all consumers retargeted per the table
   above in the same commit).
3. Add **`shipped_miost6()`** — byte-identical frozen solver/calibration
   config (same winner params path, same `PolyCalibration` from
   `phase8_field.json`, m=100, STAGE_B_ROOT, caps, pcg_rtol); separate
   function purely for provenance/docstring (six-mission flagship, phase12
   record).
4. Flip: `SHIPPED["miost"] = shipped_miost6` in `registry.py`.

## NEW miost6 pins (captured AT flip, T9)

- Six-mission factory pin: `shipped_miost6()` member reconstruction vs the
  phase12 artifacts (external, env-gated — pattern of
  `test_phase8_identity_regression.py`).
- Six-mission map sha pins: `phase12_miost6_mean_maps.nc` +
  `phase12_miost6_var_maps.nc` sha256 anchored (values from
  `phase12.miost6.provenance`).

## Execution gate (restated)

This census is executed at **Task 9 ONLY on the owner's explicit sign-off
message** at the Task-8 three-branch ruling. The mechanical verdict does not
authorize it. HOLD/no-flip → Task 9 closes superseded; Task 10 records the
branch and this doc remains the unexecuted record.
