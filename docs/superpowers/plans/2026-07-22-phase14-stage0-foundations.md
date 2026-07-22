# Phase 14 Stage 0 — Foundations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stage 0 of the Phase-14 scaling program: the sealed global evaluation
set, the compute ladder with measured probes and the determinism contract, the
dual-source input layer, and the tiling substrate — everything Gate 0 needs,
with zero evaluation-bearing maps, zero locked opens, zero c2.

**Architecture:** Four workstreams (0a evaluation re-foundation / 0b compute /
0c input layer / 0d tiling substrate) per spec §5 of
`docs/superpowers/specs/2026-07-21-phase14-scaling-program-design.md` (SPEC —
governs on conflict). 0a-6 (the SEAL) closes workstream 0a consuming
0a-2/0a-3/0a-5 + 0c-1; Gate 0 is the owner user-gate consuming everything;
0a-7 (P0-2) is Task 0, before anything touching the evidence-rerun path.

**Tech Stack:** existing spine untouched (MiostSolver, CRN, Phase-9 harness,
Phase-11 geometry provider, provenance guard, Registry). New: along-track
source adapters (`adapters/altimetry/`), in-situ family (`adapters/insitu/`,
`eval/insitu.py`), epoch machinery (`application/epochs.py`), spatial tile
frames + blend (`application/spatial_tiles.py`), per-tile scorer
(`validation/pertile_scoring.py`), seal (`validation/phase14_seal.py`),
ladder (`application/ladder.py`).

**User decisions (already made — SPEC §4 records all pins; quotable here):**
- Fork A: dual-source loader; synthetic third adapter in CI; content-addressed
  descriptor (per-file shas ALWAYS); golden-tile TABLES-never-blocks; DT2021
  pinned; version migration reruns golden-tile machinery.
- Fork C/E/F: role-split validation; epoch table = ONE registry (validation +
  locked + fit-vs-transferred columns, net-of-locked); locked gauges =
  universal spine + c2 2010→; seeded stratified split; sealed nulls;
  structural locked-gauge refusal (the c2 pattern); seal immutable, amendment
  = new version + supersession pointer.
- Fork D: 15°×15°/2° default probe-ratified; ONE frame helper (core/overlap/
  halo); partition-of-unity unit tests in Stage 0; halo follows the operative
  kernel scale.
- Fork G: tiers 0–3; spend tables with storage/egress; executor-set spend
  never; Tier-1 eligibility = measured MemAvailable; two determinism
  tolerances priced apart; CRN bit-exact asserted separately; data-governance
  line.
- Owner plan ruling (2026-07-22): task groups per workstream; 0a-6 last in 0a;
  Gate 0 = userGate; 0a-7 first; gate scheduling (gates 2 + CRN-half-of-4 RUN
  in Stage 0; 1/5 + solve-half-of-4 run in Stage 1; 3 runs in Stage 2; test
  CODE lands at earliest consumer); owner inputs pre-registered or WAIT.

**Recorded interpretation — OWNER-ACCEPTED at plan review 2026-07-22 (SPEC
§14 postscript):** gate 2 decomposes into **loader-identity** (byte-comparable,
dc2021a-wrapped source, runs Stage 0) + **lineage-sensitivity** (the first
golden-tile comparison, dc2021a vs CMEMS-MY, anchor box × 2017 × frozen signed
config — "what would the signed numbers have been on CMEMS-MY directly").
Divergence TABLES, never blocks Stage 1. The dc2021a wrapper is a REAL adapter
(conformance-covered, content-manifested descriptor — never a test-only
bypass). **Stage-1 source map (recorded now):** anchor + seam-pair run dc2021a
lineage (signed-comparable); non-box tiles necessarily run CMEMS-MY (dc2021a
is box-scoped); per-tile source in provenance; the golden-tile delta is the
recorded BRIDGE for any cross-lineage reading.

**Owner-input pre-registered defaults (the monied standing rule — tasks WAIT
if these do not cover reality):**
- Tier-2 probe ceiling (Task 18): ≤ US$25 total; single VM ≤ 8 vCPU / 64 GB;
  ≤ 6 h wall; one provider+region; delete on completion. Exceeding any bound →
  the task WAITS for the owner.
- Stage-0 storage budget (Task 16 table): CMEMS downloads ≤ 50 GB local
  (catalog metadata + probe-tile subset + box-region multi-year subset);
  public-data egress $0. Exceeding → WAIT.
- All other Stage-0 compute: Tier 0/1 only, $0.

**Standing discipline (every task):** TDD red/green per behavior; dual review
per task (spec + adversarial); `pixi run pre-commit run --files …` before every
commit; push after every task; zero evaluation-bearing maps (all solve outputs
labeled PROBE, never scored against validation or locked tiers); zero locked
opens; zero c2; tally untouched. No source edits during any timed probe run.

---

## File structure

```
src/sverdrup/adapters/altimetry/__init__.py     # contract exports
src/sverdrup/adapters/altimetry/contract.py     # SourceDescriptor, AlongTrackSource, conformance helpers
src/sverdrup/adapters/altimetry/synthetic.py    # synthetic CI adapter
src/sverdrup/adapters/altimetry/dc2021a.py      # wraps existing challenge files
src/sverdrup/adapters/altimetry/cmems_my.py     # DT2021 multi-year adapter
src/sverdrup/adapters/altimetry/jpl_ssha.py     # JPL adapter (code public, data-gated)
src/sverdrup/adapters/insitu/gauges.py          # PSMSL/UHSLC loaders + locked refusal
src/sverdrup/adapters/insitu/screening.py       # criteria pipeline + stratified split
src/sverdrup/eval/insitu.py                     # InSituGauges evaluator (reference-based)
src/sverdrup/application/epochs.py              # census artifact, partition, epoch table
src/sverdrup/application/spatial_tiles.py       # TileFrame helper + spatial blend
src/sverdrup/application/ladder.py              # tiers, spend table, Tier-1 RAM predicate
src/sverdrup/validation/pertile_scoring.py      # per-tile validation scorer
src/sverdrup/validation/locked_tier.py          # generalized touch ceremony + tally ledger
src/sverdrup/validation/phase14_seal.py         # seal build/verify/supersede
scripts/phase14_probe.py                        # 0b-1 tile probe + 0b-3 Tier-2 legs
scripts/phase14_crossenv.py                     # gate-4 machinery (CRN + solve halves)
scripts/phase14_golden_tile.py                  # 0c-5 cross-source comparison
scripts/phase14_seal.py                         # seal assembly CLI
docs/validation/phase14_seam_rubric.md          # Task-18-pattern spatial rubric
```

Evidence namespace: `phase14.stage0.*` in the standing evidence JSON
(gitignored), single-writer discipline. PROBE artifacts under
`data/2021a_ssh_mapping_ose/ours/phase14_probe/` (gitignored).

---

### Task 0: P0-2 blocking precondition (0a-7)

**Goal:** The Stage-B evidence clobber path cannot fire during this program:
`tune_miost_inflation.py`'s unconditional evidence write becomes a refusal
unless an explicit opt-in env is set, per the hygiene P0-2 adjudication
("leave-on-queue, hardened to a blocking precondition", Phase-12 spec §5).

**Files:**
- Modify: `scripts/tune_miost_inflation.py` (the write path at ~line 117)
- Test: `tests/test_phase14_p02_guard.py`

**Acceptance Criteria:**
- [ ] Running the script's evidence-write path without
      `SVERDRUP_ALLOW_STAGEB_EVIDENCE="1"` (exact string) raises
      `RuntimeError` naming the P0-2 hygiene item BEFORE any file is opened
      for writing; with the env set, behavior unchanged.
- [ ] Test proves refusal fires before write (tmp evidence file mtime/content
      unchanged after the refused call).
- [ ] PROGRESS hygiene register updated: P0-2 hardened, date + commit.

**Verify:** `pixi run test -- tests/test_phase14_p02_guard.py -v` → PASS.

**Steps:**
- [ ] Failing test: import the guarded function (extract the write into
      `_write_evidence_guarded()` if needed), call without env → expect
      RuntimeError; with env → writes.
- [ ] Implement guard (few lines, before file open):

```python
if os.environ.get("SVERDRUP_ALLOW_STAGEB_EVIDENCE") != "1":
    raise RuntimeError(
        "P0-2 blocking precondition: stage-B evidence write refused. "
        "Set SVERDRUP_ALLOW_STAGEB_EVIDENCE=1 only after owner adjudication "
        "(docs/hygiene-priorities.md P0-2)."
    )
```

- [ ] Run → PASS; pre-commit; commit `fix: P0-2 stage-B evidence clobber path
      hardened to blocking precondition`; push.

---

### Task 1: Along-track loader contract + synthetic adapter (0c-1 + 0c-3)

**Goal:** The dual-source contract: `SourceDescriptor` (uniform,
content-addressed), `AlongTrackSource` protocol, a conformance suite any
adapter must pass, and the synthetic adapter that runs it in public CI.

**Files:**
- Create: `src/sverdrup/adapters/altimetry/__init__.py`,
  `src/sverdrup/adapters/altimetry/contract.py`,
  `src/sverdrup/adapters/altimetry/synthetic.py`
- Test: `tests/adapters/test_altimetry_contract.py`

**Acceptance Criteria:**
- [ ] `SourceDescriptor` frozen dataclass: `source_id: str`,
      `dataset_version: str`,
      `content_manifest: tuple[tuple[str, str], ...]` (relpath, sha256),
      sorted, and `manifest_sha() -> str` = sha256 over the canonical
      JSON serialization. NO alternative to per-file shas exists in the type
      (fork-a pin 3 — kill the "OR").
- [ ] `AlongTrackSource` Protocol: `missions() -> tuple[str, ...]`;
      `load(bbox, t0, t1, missions=None) -> ObsWindow` (existing
      `core/observations.py` type; obs mission-tagged); `descriptor() ->
      SourceDescriptor`. Loading NEVER mutates values — any transform
      (super-obs later) is a separate parameterized loader-layer step
      recorded in provenance (fork-a pin 4; the hook is a documented no-op
      `apply_superobs(obs, cfg=None)` that returns obs unchanged when
      cfg is None, with its cfg serialized into provenance when set).
- [ ] Conformance suite = parametrizable test class
      (`AltimetryConformance`): region clipping exact; time clipping exact;
      mission filter exact; descriptor stable across two instantiations;
      manifest_sha changes when any file byte changes; load is deterministic
      (two calls byte-equal arrays).
- [ ] Synthetic adapter: two fake missions (`synA` 10-day repeat, `synB`
      drifting), analytic deterministic ground tracks (seeded from
      `derive_seed("altimetry","synthetic-v1",mission,0)`), ~500 obs/day,
      values = analytic SSH (sum of two Gaussians advected slowly); passes
      the full conformance suite in CI with no external data.

**Verify:** `pixi run test -- tests/adapters/test_altimetry_contract.py -v`
→ all PASS (no skips — this is the public-CI leg).

**Steps:**
- [ ] Failing conformance tests against a stub adapter → FAIL.
- [ ] Implement contract.py + synthetic.py; wire conformance suite so future
      adapters subclass the test class with a fixture override only.
- [ ] Run → PASS; pre-commit; commit `feat: phase14 along-track source
      contract + synthetic CI adapter`; push.

---

### Task 2: dc2021a source adapter + LOADER IDENTITY GATE (0c-6, SPEC gate 2 — RUNS in Stage 0)

**Goal:** The existing challenge input path wrapped as an `AlongTrackSource`,
and the byte-comparable identity gate proving the new loader reproduces the
current 2017 box input path exactly.

**Files:**
- Create: `src/sverdrup/adapters/altimetry/dc2021a.py`
- Test: `tests/adapters/test_dc2021a_source.py`,
  `tests/test_phase14_gate2_loader_identity.py`

**Acceptance Criteria:**
- [ ] `Dc2021aSource` wraps the existing per-mission challenge files (reuses
      `validation/input_adapter.py` reading logic — imported, not copied);
      `source_id="dc2021a"`; manifest = the challenge files' shas; passes the
      Task-1 conformance suite (skip-guarded on local data presence). A REAL
      adapter through the contract — uniform content-manifested descriptor,
      never a test-only bypass (owner pin 2, plan review 2026-07-22; adapter
      census = synthetic + CMEMS-MY + dc2021a + JPL-code).
- [ ] GATE 2 test: for the signed box frame and full 2017, obs arrays
      (lon, lat, t, value, mission) via `Dc2021aSource.load(...)` are
      **byte-identical** (`np.array_equal` + dtype equality) to the legacy
      `input_adapter` path's arrays, per mission, mapping set AND j3
      validation track; c2 NEVER loadable through the mapping call (the
      existing exclusion preserved — test asserts refusal/absence).
- [ ] Gate result recorded at `phase14.stage0.gate2_loader_identity`
      (pass bool + per-mission n_obs + manifest_sha).

**Verify:** `pixi run test -- tests/test_phase14_gate2_loader_identity.py -v`
→ PASS on this box (data present).

**Steps:**
- [ ] Failing tests (conformance subclass + gate 2) → FAIL/ERROR.
- [ ] Implement dc2021a.py delegating to input_adapter internals.
- [ ] Run gate; record evidence; pre-commit; commit `feat: phase14 dc2021a
      source + gate-2 loader identity (byte-comparable)`; push.

---

### Task 3: CMEMS DT2021 multi-year adapter (0c-2)

**Goal:** The public multi-year source: pinned DT2021 L3 product, reproducible
scoped downloads (catalog metadata for the census; probe-tile and box-region
subsets for Stage-0 runs), content-manifested.

**Files:**
- Create: `src/sverdrup/adapters/altimetry/cmems_my.py`,
  `scripts/download_cmems_my.py`
- Test: `tests/adapters/test_cmems_my.py` (fixture-driven; network tests
  data-gated)

**Acceptance Criteria:**
- [ ] Product pinned: `SEALEVEL_GLO_PHY_L3_MY_008_062` (DT2021 vintage — the
      papers' lineage), per-mission along-track SLA; `dataset_version` carries
      the product id + DT tag; version migration = a NEW source_id, never a
      mutation (fork-a pin 5 recorded in the module docstring).
- [ ] Downloader follows the dc-download reproducer pattern (httpx + stamina
      retry on `_is_retryable`, sha256 manifest written beside data, re-run =
      verify-and-skip); scope arguments (bbox, t0, t1, missions) — NEVER an
      implicit full-globe pull; downloaded layout is deterministic.
- [ ] **Census leg:** `mission_catalog()` returns per-mission
      (first_date, last_date, n_files) from catalog/manifest metadata WITHOUT
      bulk data download; result content-addressed, written to
      `data/cmems_my/census_raw.json` + sha.
- [ ] `CmemsMySource` passes the Task-1 conformance suite on a downloaded
      fixture subset (data-gated skip otherwise); parsing tested against a
      small committed synthetic-netCDF fixture in CI (no network).
- [ ] Storage accounting: every download logs GiB to
      `phase14.stage0.storage_ledger`; refuses to start a pull whose estimate
      would exceed the Task-16 storage budget remaining (WAIT semantics).

**Verify:** `pixi run test -- tests/adapters/test_cmems_my.py -v` → PASS
(CI legs green; network legs skip-guarded).

**Steps:**
- [ ] Failing parser/conformance-fixture tests → FAIL.
- [ ] Implement adapter + downloader; run census leg (metadata only) on this
      box; record `phase14.stage0.cmems_census_raw_sha`.
- [ ] Pre-commit; commit `feat: phase14 CMEMS DT2021 multi-year source +
      scoped reproducible downloads`; push.

---

### Task 4: Census artifact + epoch partition (0a-1)

**Goal:** The deterministic constellation census and epoch partition the whole
program keys on — from loader metadata, schema-versioned, content-addressed,
reference-epoch candidates computed net-of-locked.

**Files:**
- Create: `src/sverdrup/application/epochs.py`
- Test: `tests/test_phase14_epochs.py`

**Acceptance Criteria:**
- [ ] `build_census(catalog) -> CensusArtifact`: per-mission ACTIVE intervals
      = [first_obs_date, last_obs_date] split where an intra-mission gap
      > `MISSION_GAP_SPLIT_D = 90` days; day resolution; `schema_version=1`;
      `content_sha()` deterministic (two builds byte-equal).
- [ ] `partition_epochs(census) -> tuple[Epoch, ...]`: boundaries = union of
      active-interval endpoints (constellation-change dates);
      **minimum-epoch rule:** any epoch shorter than `MIN_EPOCH_DAYS = 365`
      is MERGED into the neighbor with the higher mission-set Jaccard
      similarity (tie → earlier neighbor); merge trail recorded IN the
      artifact (the pre-merge boundaries kept as `raw_boundaries`).
- [ ] Epoch naming: `e{index:02d}_{start ISO date}` (e.g. `e00_1993-01-01`) —
      index in time order, deterministic.
- [ ] `window_epoch(window_center_date, epochs)` — the WINDOW-CENTER rule
      (fork-d D6), with the accepted-approximation sentence in the docstring.
- [ ] `reference_candidates(epochs, locked_exclusions) -> list[EpochId]`:
      constellation counted NET of locked missions per epoch (fork-e pin 3);
      candidates = epochs with net count ≥ 4.
- [ ] Fixture tests: synthetic catalog reproducing the known shape (1993
      two-satellite; a mid-2000s 4-mission span; 2017 six-mission) → expected
      epochs, merges, candidates; boundary-day off-by-one pinned by test.

**Verify:** `pixi run test -- tests/test_phase14_epochs.py -v` → PASS.

**Steps:**
- [ ] Failing fixture tests (each AC row) → FAIL.
- [ ] Implement; run on the real Task-3 census leg; record artifact sha at
      `phase14.stage0.census_sha` (artifact file gitignored, sha in evidence).
- [ ] Pre-commit; commit `feat: phase14 census artifact + deterministic epoch
      partition`; push.

---

### Task 5: Epoch table draft (0a-2)

**Goal:** The single registry: epoch → missions → holdout(validation) →
locked-instrument → fit-vs-transferred, with the sparse-era handicap columns —
drafted from the census, sealed later by Task 19.

**Files:**
- Modify: `src/sverdrup/application/epochs.py` (table builder)
- Test: `tests/test_phase14_epoch_table.py`

**Acceptance Criteria:**
- [ ] `build_epoch_table(epochs, census) -> EpochTable` applies the fork-c
      holdout criteria IN ORDER, mechanically: (1) never the climate-reference
      line (`{tp, j1, j2*, j3}` family ids) where an alternative exists;
      (2) prefer a holdout with an instrument-class sibling still assimilated
      (class map recorded in the module: Poseidon-series / ERS-Envisat-AltiKa
      / HY-2 / Sentinel-3 / CryoSat); (3) prefer minimal geometry-class-mix
      distortion (repeat/drifting balance via the Phase-11 classifier
      classes); (4) one holdout per epoch, stable.
- [ ] Columns per epoch: missions; holdout + recorded criterion that selected
      it; role (`fit+validate` for reference epochs, `validate-only` sparse);
      locked instruments (`gauges` always; `c2` where c2 flies — 2010→);
      fit-vs-transferred; handicap: fit-substrate fraction, ±66° mask flag
      for ERS-line holdouts (fork-c pin 3), sibling-less flag (fork-c pin 4).
- [ ] 2017 epoch row: holdout = j3, role = reference (`fit+validate`) — the
      workhorse, by construction; test pins it.
- [ ] Table serializes deterministically (the seal consumes these bytes).

**Verify:** `pixi run test -- tests/test_phase14_epoch_table.py -v` → PASS.

**Steps:**
- [ ] Failing tests: synthetic census → expected holdout choices incl. a
      1993-shape epoch (ERS-line holdout, validate-only, mask flag, sibling-
      less flag) and the 2017 pin → FAIL.
- [ ] Implement; generate the REAL draft table; record sha at
      `phase14.stage0.epoch_table_draft_sha`.
- [ ] Pre-commit; commit `feat: phase14 epoch table — holdout/locked/role
      columns per recorded criteria`; push.

---

### Task 6: JPL adapter code + artifact-gated conformance (0c-4)

**Goal:** The production-source adapter: code public, conformance runnable
only where the data lives, ingest-time content manifest.

**Files:**
- Create: `src/sverdrup/adapters/altimetry/jpl_ssha.py`
- Test: `tests/adapters/test_jpl_ssha.py`

**Acceptance Criteria:**
- [ ] `JplSshaSource` reads a documented directory layout (per-mission
      along-track SSHA netCDF; layout + variable names in the module
      docstring as the interface contract); computes per-file sha256 AT
      INGEST for the manifest (fork-a pin 3 — no processing-tag branch).
- [ ] Conformance suite subclass behind the standing skip-guard
      (`pytest.mark.skipif` on `SVERDRUP_JPL_SSHA_DIR` unset/absent) — the
      artifact-gated pattern; CI shows SKIPPED, never green-by-vacuity
      (skip reason names the env var).
- [ ] Parsing logic unit-tested in CI against a committed synthetic fixture
      file matching the documented layout (no private data in repo).
- [ ] Data-governance line enforced in code comment + test: no code path
      uploads/copies JPL data off-host (adapter is read-only local).

**Verify:** `pixi run test -- tests/adapters/test_jpl_ssha.py -v` → CI legs
PASS, conformance leg SKIPPED here.

**Steps:**
- [ ] Failing fixture-parse tests → FAIL. Implement. PASS.
- [ ] Pre-commit; commit `feat: phase14 JPL SSHA adapter — public code,
      artifact-gated conformance`; push.

---

### Task 7: Golden-tile cross-check machinery + first public comparison (0c-5)

**Goal:** The input-lineage sensitivity instrument: same tile, same period,
same config through two sources → map deltas + track-metric deltas, recorded;
divergence TABLES. First execution: dc2021a vs CMEMS-MY on the box (public
both sides).

**Files:**
- Create: `scripts/phase14_golden_tile.py`
- Test: `tests/test_phase14_golden_tile.py`

**Acceptance Criteria:**
- [ ] `phase14_golden_tile.py --source-a dc2021a --source-b cmems_my
      --frame signed-box --period 2017` runs the FROZEN signed config through
      the existing solve path per source (PROBE-labeled artifacts) and
      records: obs-count deltas per mission, mean-map RMS/max delta per
      window, j3-track µ delta. NO verdict logic — numbers + a
      `tabled_for_owner: true` flag when any delta exceeds the recording
      threshold (all deltas recorded regardless). Pre-registration sharpened
      (owner pin 3): tile = the ANCHOR box, period = 2017, config = frozen
      signed — the comparison's meaning is "what would the signed numbers
      have been on CMEMS-MY directly"; divergence TABLES, never blocks
      Stage 1; the recorded delta is the cross-lineage BRIDGE for the Stage-1
      source map.
- [ ] Output under `phase14.stage0.golden_tile.<a>_vs_<b>` with both
      descriptors' manifest shas — the version-migration protocol reuses this
      key shape verbatim (fork-a pin 5).
- [ ] Unit tests: delta arithmetic on synthetic pairs; the tabled flag; both
      descriptors recorded; refusal to run with identical source ids.
- [ ] The dc2021a-vs-CMEMS-MY execution is RECORDED in evidence (box-region
      CMEMS subset from Task 3; a real lineage measurement, PROBE-labeled,
      never validation-scored).

**Verify:** `pixi run test -- tests/test_phase14_golden_tile.py -v` → PASS;
evidence key present after the run.

**Steps:**
- [ ] Failing unit tests → FAIL. Implement script (reuses run.py solve path
      + halo_obs; scoring via the existing j3 validation call).
- [ ] Download box-region CMEMS subset (within storage budget); run the
      comparison; record.
- [ ] Pre-commit; commit `feat: phase14 golden-tile lineage comparison +
      dc2021a-vs-CMEMS-MY first execution`; push.

---

### Task 8: Gauge data layer — sources, screening, split, LOCKED REFUSAL (0a-3a)

**Goal:** PSMSL/UHSLC loaders, the recorded screening pipeline (data-quality
only), the seeded stratified locked/dev split, and the structural refusal on
locked IDs — the c2 pattern extended to in-situ.

**Files:**
- Create: `src/sverdrup/adapters/insitu/__init__.py`,
  `src/sverdrup/adapters/insitu/gauges.py`,
  `src/sverdrup/adapters/insitu/screening.py`,
  `scripts/download_gauges.py`
- Test: `tests/adapters/test_gauges.py`, `tests/test_phase14_gauge_screening.py`

**Acceptance Criteria:**
- [ ] Sources pinned: UHSLC research-quality (rqds) hourly → daily means
      (primary series); PSMSL RLR catalog snapshot for datum-continuity
      metadata. Both content-manifested at download (per-file shas); snapshot
      date recorded — "version" = the manifest, per fork-a pin 3.
- [ ] Screening criteria implemented as recorded, IN ORDER, each emitting a
      per-gauge pass/fail row (visible, never silent): (1) RLR datum
      continuity; (2) era completeness ≥ 70% of days in each epoch the gauge
      claims + ≥ 3 years total in-record; (3) open-ocean siting — excluded
      basins list (recorded lat/lon polygons in `screening.py`: Baltic,
      Black, Mediterranean marginal cells, semi-enclosed bays) + island/
      offshore preference flag; (4) proximity ≤ `L_PROX_KM = 150.0` (≈ the
      shipped λx neighborhood; rationale in constant docstring: a gauge
      farther than the product's resolved scale from the nearest wet
      gridpoint cannot be compared) to the nearest ocean point of the target
      grid; (5) correction-consistency flag (DAC/tide handling recorded per
      gauge; B2023 Eq.-1 stack is the reference convention).
- [ ] **The firewall in code + docstring (verbatim sentence from SPEC §4-F):**
      screening consumes gauge data quality ONLY; no map, no skill number
      enters any criterion (test: screening runs with no map artifacts on
      disk).
- [ ] Stratified split: strata = basin (recorded 8-box partition) ×
      era-coverage class (pre-2000 / 2000–2010 / post-2010 / full-span);
      locked fraction 30% per stratum;
      seed = `derive_seed("insitu", "phase14-seal", "locked-split", 0)`
      (fork-f pin 3); split deterministic (test: rebuild byte-equal).
- [ ] **Structural refusal (fork-f pin 1):** `load_gauge(gauge_id)` for an id
      in the locked set raises `LockedGaugeError` BEFORE any file open unless
      `SVERDRUP_INSITU_LOCKED="1"` (exact string — the c2 ceremony pattern);
      refusal tests green; dev-pool ids load normally.

**Verify:** `pixi run test -- tests/adapters/test_gauges.py
tests/test_phase14_gauge_screening.py -v` → PASS (network legs data-gated;
parsing/screening/split/refusal legs CI-green on committed fixtures).

**Steps:**
- [ ] Failing tests per AC row (fixtures: 6 synthetic gauges spanning the
      strata + one locked) → FAIL.
- [ ] Implement loaders + screening + split + refusal. Download real
      catalogs/series scoped to candidates (storage-ledgered); run screening;
      record `phase14.stage0.gauges.{n_candidates,n_screened,n_locked,split_seed}`.
- [ ] Pre-commit; commit `feat: phase14 gauge layer — screening firewall,
      seeded split, locked structural refusal`; push.

---

### Task 9: In-situ evaluator + sealed nulls (0a-3b)

**Goal:** The founding taxonomy completed: `InSituGauges` evaluator in the
reference-based family, `required_context` gains the in-situ provider key,
metrics vs sealed null models.

**Files:**
- Create: `src/sverdrup/eval/insitu.py`
- Modify: `src/sverdrup/core/evaluation.py` (`ContextKey.INSITU_GAUGES`),
  `src/sverdrup/application/eval_context.py` (provider wiring),
  `src/sverdrup/eval/__init__.py` (default_registry row)
- Test: `tests/eval/test_insitu.py`

**Acceptance Criteria:**
- [ ] `ContextKey.INSITU_GAUGES` added; `InSituGauges.required_context =
      frozenset({ContextKey.INSITU_GAUGES})`; registered reference-based;
      `Registry.applicable` picks it up iff the provider key is present
      (declared⇒consumed integrity test extended — the Phase-11 pattern).
- [ ] Comparison operator: map SSHA at gauge location (bilinear from the
      output grid, wet-node handling per the existing mask derivation) vs
      gauge daily anomaly; per-gauge rows + aggregate.
- [ ] Metrics: correlation and RMSE **reduction vs null**, null models from
      SEALED config only (fork-f pin 4): `null_climo` = day-of-year
      climatology from the gauge's own record (15-day boxcar smoothing);
      `null_persist` = lag-1-day persistence. No scoring-time null choice
      exists in the API (nulls come from the sealed instrument config
      object).
- [ ] Report-only: emits `report_rows`; no bar semantics anywhere (fork-f
      pin 6).
- [ ] Test fixtures: synthetic gauge + synthetic map where the analytic
      answer is known; a wrong-null bug (climatology without smoothing)
      caught by value pin.

**Verify:** `pixi run test -- tests/eval/test_insitu.py -v` → PASS; the
declared⇒consumed integrity suite still green
(`pixi run test -- tests/ -k integrity -v`).

**Steps:**
- [ ] Failing tests → FAIL. Implement evaluator + context key + wiring.
- [ ] Pre-commit; commit `feat: phase14 in-situ gauge evaluator — founding
      taxonomy completed, sealed nulls`; push.

---

### Task 10: Touch mechanics generalized (0a-4)

**Goal:** The one-touch discipline at program scale: per-product-per-era tally
ledger + the generalized ceremony (tripwires recompute sealed shas before any
locked data opens), misfire protocol inherited.

**Files:**
- Create: `src/sverdrup/validation/locked_tier.py`
- Test: `tests/test_phase14_locked_tier.py`

**Acceptance Criteria:**
- [ ] `TallyLedger` in the evidence JSON at `phase14.locked_tally`:
      `{product_id: {era_id: n_touches}}`; `open_touch(product_id, eras)`
      refuses (a) without `SVERDRUP_PHASE14_TOUCH="1"` exact-string, (b) if
      any (product, era) tally would exceed 1 without an owner
      `corrected_by` dated defect key (misfire protocol — the owner
      2026-07-20 recording, applied verbatim), (c) if the seal verification
      (Task 19's `verify_seal()`) fails — tripwire BEFORE any locked data
      opens.
- [ ] The ceremony function is the ONLY code path that sets
      `SVERDRUP_INSITU_LOCKED` / future locked-instrument envs for its
      child scope (structural: refusals in Task 8 stay independent).
- [ ] 8 refusal tests (the phase-13 pre-touch pattern): no env; tally
      exceeded; seal sha mismatch; missing seal; double-open; defect-key
      path accepted; env exact-string (not "true"/"yes"); dev-pool
      unaffected.
- [ ] Docstring carries: gate approval is NOT touch authorization (the
      standing rule).

**Verify:** `pixi run test -- tests/test_phase14_locked_tier.py -v` → PASS.

**Steps:**
- [ ] 8 failing refusal tests → FAIL. Implement against a stub seal verifier
      (real one lands Task 19; interface pinned here).
- [ ] Pre-commit; commit `feat: phase14 locked-tier touch ceremony + per-era
      tally ledger`; push.

---

### Task 11: Seam rubrics + instrument configs (0a-5)

**Goal:** The Task-18 pattern, spatial: the seam-dispersion rubric written
BEFORE any tile exists, plus the sealed per-tile instrument configs
(GroundTrack, SpectralFidelity, seam, in-situ nulls) as one config object the
seal ingests.

**Files:**
- Create: `docs/validation/phase14_seam_rubric.md`,
  `src/sverdrup/validation/phase14_instruments.py`
- Test: `tests/test_phase14_instrument_configs.py`

**Acceptance Criteria:**
- [ ] Rubric doc (pattern: `docs/validation/miost_seam_dispersion_rubric.md`):
      verdict rubric BEFORE numbers — seam metric definition (cross-seam
      mean/σ dispersion on the blend overlap vs interior-reference
      dispersion), the three verdict cells (CLEAN / ELEVATED-RECORDED /
      STRUCTURAL-STOP) with pre-registered thresholds, and the seam-ORACLE
      clause (seam-pair vs seamless signed truth; no published precedent —
      recorded).
- [ ] `instrument_configs()` returns the deterministic, serializable config
      set: GroundTrack per-tile (geometry-artifact keyed, constellation-
      aware); SpectralFidelity per-tile (band = tile extent, box convention
      generalized); seam rubric thresholds (mirroring the doc — test pins
      doc↔code equality on the numbers); in-situ nulls (Task 9's objects).
- [ ] Serialization is byte-deterministic (seal substrate).

**Verify:** `pixi run test -- tests/test_phase14_instrument_configs.py -v`
→ PASS.

**Steps:**
- [ ] Write the rubric doc FIRST (dual-reviewed as prose). Failing
      config/serialization tests → FAIL → implement → PASS.
- [ ] Pre-commit; commit `feat: phase14 seam rubric (pre-registered) +
      sealed instrument configs`; push.

---

### Task 12: Tile-frame helper (0d-1)

**Goal:** ONE shared helper emitting {core, blend-overlap, halo} frames — the
halo_obs lesson; the anchor's degenerate frame reproduces the signed box
exactly.

**Files:**
- Create: `src/sverdrup/application/spatial_tiles.py`
- Test: `tests/test_phase14_tile_frames.py`

**Acceptance Criteria:**
- [ ] `TileFrame` frozen dataclass: `core: BBox`, `overlap_deg: float`,
      `halo_deg: float`, derived `solve_bbox` (core + overlap) and
      `obs_bbox` (solve + halo); `frame_grid(frame, resolution)` returns the
      solve grid; obs selection delegates to the EXISTING
      `halo_obs(obs, grid, halo_deg)` (imported — no second implementation).
- [ ] `tile_plan(domain_bbox, tile_deg=15.0, overlap_deg=2.0, halo_deg=1.0)`
      → deterministic tile list (paper defaults as named constants,
      probe-ratification note in docstring); edge tiles clipped to domain
      with missing-neighbor sides flagged (Task 13 consumes the flags).
- [ ] `halo_deg` DEFAULTS from the operative kernel scale hook
      (`operative_halo_deg()` — returns the current 1.0° practice; single
      point of change for the constraint-3 decision; fork-d pin 4).
- [ ] **Anchor degeneracy:** `anchor_frame()` returns the signed box frame —
      test pins `core == the signed 10°×10° bbox`, `overlap = 0`,
      `obs_bbox == the legacy halo_obs extent` (byte-equal grid nodes vs the
      legacy path).

**Verify:** `pixi run test -- tests/test_phase14_tile_frames.py -v` → PASS.

**Steps:**
- [ ] Failing tests (incl. anchor byte-equality vs legacy grid) → FAIL →
      implement → PASS.
- [ ] Pre-commit; commit `feat: phase14 tile-frame helper — one source for
      core/overlap/halo, anchor degenerate`; push.

---

### Task 13: Spatial blend + partition-of-unity EVERYWHERE (0d-2)

**Goal:** The paper's linear edge blend + our separable corner completion,
with partition of unity asserted numerically in every configuration —
interior, edges, corners, missing-neighbor renormalization.

**Files:**
- Modify: `src/sverdrup/application/spatial_tiles.py` (blend weights)
- Test: `tests/test_phase14_spatial_blend.py`

**Acceptance Criteria:**
- [ ] `blend_weight(frame, lon, lat)`: per-axis linear ramp over the actual
      overlap (weight ∝ boundary relative distance — U2022 verbatim on
      edges), separable product across axes (our corner completion —
      docstring cites the gap-register: papers silent on corners).
- [ ] `assemble(tiles, fields)` normalizes by the ACTUAL local weight sum
      (missing-neighbor/domain-edge renormalization — the actual-overlap
      normalization lesson, spatialized).
- [ ] **Partition-of-unity tests (fork-d pin 2), all numeric to 1e-12:**
      2×1 edge; 2×2 corner (four-tile point); domain edge (missing
      neighbor); land-adjacent clipped tile; degenerate single tile
      (weight ≡ 1 everywhere — the anchor path adds NOTHING).
- [ ] Edge-reduction test: on a pure two-tile edge the separable weight
      equals the 1-D paper rule exactly.

**Verify:** `pixi run test -- tests/test_phase14_spatial_blend.py -v` → PASS.

**Steps:**
- [ ] Five failing partition-of-unity tests + edge-reduction → FAIL →
      implement → PASS.
- [ ] Pre-commit; commit `feat: phase14 spatial blend — paper edges, separable
      corners, partition of unity everywhere`; push.

---

### Task 14: Per-tile validation scorer + gate-5 test code (0d-3)

**Goal:** The scoring path generalized to a tile frame: per-tile track
extraction, per-tile (µ, σ, λx), per-tile provenance through the guard — and
the SPEC §10 gate-5 test (score-level anchor identity) landing now, running in
Stage 1.

**Files:**
- Create: `src/sverdrup/validation/pertile_scoring.py`
- Test: `tests/test_phase14_pertile_scoring.py`,
  `tests/test_phase14_gate5_score_identity.py`

**Acceptance Criteria:**
- [ ] `score_tile(frame, maps, track_source, mission)` extracts the
      validation track WITHIN `frame.core` (core only — blend overlap never
      double-scored), runs the existing µ/σ/λx machinery unchanged
      (imported), and calls `assert_scored_not_assimilated` with the
      per-tile assimilated list (per-tile provenance rows).
- [ ] Per-tile λx uses the existing spectral machinery with the tile-extent
      band (Task 11 config).
- [ ] GATE-5 test (skip-guarded on anchor-run artifacts, which exist only in
      Stage 1): `score_tile(anchor_frame(), signed_maps, dc2021a, "j3")`
      reproduces the signed miost5 (µ, σ, λx) EXACTLY (the signed acceptance
      numbers pinned as constants in the test; rtol 1e-12) — skip reason
      names the Stage-1 artifact path.
- [ ] Unit tests run NOW on synthetic fixtures: core-only extraction (obs in
      overlap excluded — off-by-one pinned); provenance guard invoked
      (refusal fixture).

**Verify:** `pixi run test -- tests/test_phase14_pertile_scoring.py -v` →
PASS; gate-5 test SKIPPED with the named reason.

**Steps:**
- [ ] Failing unit tests → FAIL → implement → PASS; gate-5 test lands
      skip-guarded.
- [ ] Pre-commit; commit `feat: phase14 per-tile scorer + gate-5 score
      identity (runs Stage 1)`; push.

---

### Task 15: Sizing model at tile scale + Tier-0/1 probe (0b-1)

**Goal:** Task-22 arithmetic extended to tile geometry with the retained-store
term BY NAME, then re-grounded by ONE measured production-geometry tile probe
at reduced days.

**Files:**
- Modify: `src/sverdrup/methods/miost_sizing.py` (tile-scale entry +
  retained-store term)
- Create: `scripts/phase14_probe.py` (leg: `--tile-sizing`)
- Test: `tests/test_phase14_sizing.py`

**Acceptance Criteria:**
- [ ] `size_tile(frame, window_days, n_windows, m_members)` returns
      {n_coef, nnz, stored_g_gib, peak_model_mib, wall_est_s} where
      peak_model EXPLICITLY includes `retained_member_store_mib =
      n_grid · n_windows · m · 8 B` (the Phase-12 miss, carried BY NAME —
      docstring cites the ledger entry).
- [ ] Probe config PINNED: frame = 15°×15° + 2° overlap + 1.0° halo, core
      lon [292, 307]°E lat [30, 45]°N (contains the signed box; CMEMS
      box-region+tile subset from Task 3); ONE 60-day window
      (2017-01-15 → 2017-03-15); mean solve + member 0 only; PROBE-labeled
      outputs; Tier 0/1.
- [ ] Probe records at `phase14.stage0.probe_tile`: wall s, peak RSS MiB,
      n_obs, PCG iters, measured-vs-model ratios for wall and peak; model
      NOT retuned in-code (re-grounding = recorded ratios, the Phase-12
      precedent).
- [ ] Tier-1 launch check runs FIRST: measured MemAvailable at launch vs
      predicted peak (fork-g pin 4); refusal path tested.

**Verify:** `pixi run test -- tests/test_phase14_sizing.py -v` → PASS;
`phase14.stage0.probe_tile` populated after the run.

**Steps:**
- [ ] Failing sizing-arithmetic tests (incl. retained-store term present and
      scaling with m) → FAIL → implement → PASS.
- [ ] Run the probe (detached, nohup + pid + log — the standing background
      discipline; no source edits during the run); record.
- [ ] Pre-commit; commit `feat: phase14 tile-scale sizing + measured tile
      probe (retained-store term named)`; push.

---

### Task 16: Ladder + spend table (0b-2)

**Goal:** Tiers 0–3 as code + the Stage-0 spend table with storage/egress
columns, Tier-1 measured-RAM predicate, data-governance line, audit-locality
rule.

**Files:**
- Create: `src/sverdrup/application/ladder.py`
- Test: `tests/test_phase14_ladder.py`

**Acceptance Criteria:**
- [ ] `Tier` enum 0–3 with the SPEC §4-G definitions in docstrings;
      `SpendTable` rows: {task_class, tier, cost_ceiling_usd, storage_gib,
      egress_gib, basis}; the STAGE-0 table as module data: Tier-2 probe row
      (ceiling US$25 / VM ≤ 8 vCPU 64 GiB / ≤ 6 h / one region — the
      pre-registered owner default), CMEMS storage row (≤ 50 GiB, egress 0),
      everything else Tier 0/1 cost 0.
- [ ] `authorize(task_class, est) -> Authorization | Wait`: any estimate over
      its row → `Wait` with the owner-facing sentence (executor-set spend
      never happens — test pins that no code path constructs an
      Authorization above a ceiling).
- [ ] `tier1_eligible(predicted_peak_mib)` reads MemAvailable AT CALL TIME
      (fork-g pin 4; test with a fake /proc/meminfo).
- [ ] Module docstring carries verbatim: the data-governance line (private
      JPL data never leaves owner-controlled hosts absent explicit owner
      authorization) and the audit-locality rule incl. third-party Tier-0
      extension.

**Verify:** `pixi run test -- tests/test_phase14_ladder.py -v` → PASS.

**Steps:**
- [ ] Failing tests (Wait semantics; ceiling arithmetic; meminfo fake) →
      FAIL → implement → PASS.
- [ ] Pre-commit; commit `feat: phase14 compute ladder + stage-0 spend table
      (owner defaults pre-registered)`; push.

---

### Task 17: Cross-env gate machinery (0b-4; gate-4 CODE — CRN half runs Stage 0)

**Goal:** The gate-4 instrument: CRN-draw bit-exactness assertion (hash-based)
and the mean+member solve comparison with recorded FP tolerances — decomposed,
never one blended number.

**Files:**
- Create: `scripts/phase14_crossenv.py`
- Test: `tests/test_phase14_crossenv.py`

**Acceptance Criteria:**
- [ ] Pinned subject: the SIGNED BOX frame, window w0 (first 60-day window of
      2017), dc2021a source, frozen signed config; mean solve + member 0
      (seed root via the existing `derive_seed` identity — recorded in
      output).
- [ ] `--leg crn` emits sha256 of the raw CRN draw byte-streams (all axes
      consumed by the window, member 0) → `crn_manifest.json`;
      `--compare-crn a.json b.json` asserts equality (the bit-exact half —
      hash compare, no FP).
- [ ] `--leg solve` emits mean map + member map + PCG iters + the BLAS
      recipe actually in effect; `--compare-solve` reports max-abs and RMS
      deltas — REPORTS, tolerance is recorded from measurement (Task 18),
      never asserted before it exists.
- [ ] Pinned single-thread deterministic recipe documented in the script and
      exported by `--print-env`:
      `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
      PYTHONHASHSEED=0`, plus `pixi list` openblas/numpy/scipy versions and
      the container image digest captured into the output.
- [ ] Same-host smoke: two `--leg crn` runs on this box → `--compare-crn`
      EQUAL (runs in CI-local test with a tiny synthetic window).

**Verify:** `pixi run test -- tests/test_phase14_crossenv.py -v` → PASS.

**Steps:**
- [ ] Failing tests (manifest determinism; compare semantics; env recipe
      captured) → FAIL → implement → PASS.
- [ ] Pre-commit; commit `feat: phase14 cross-env gate machinery — CRN
      bit-exact half + solve-delta half, decomposed`; push.

---

### Task 18: Tier-2 probe — cost + BOTH determinism measurements (0b-3)

**Goal:** The single ceilinged cloud probe: measured cloud cost basis, CRN
cross-host bit-exactness PASSED (the Stage-0 half of gate 4), cross-host
single-thread solve delta, same-host multi-thread spread → the TWO recorded
tolerances.

**Files:**
- Modify: `scripts/phase14_probe.py` (leg: `--tier2-report`)
- Create: `sky/phase14_probe.yaml` (SkyPilot task: pinned image, the Task-17
  legs, artifact pull-back)
- Test: `tests/test_phase14_tier2_report.py`

**Acceptance Criteria:**
- [ ] Launch obeys `ladder.authorize("tier2_probe", est)` — WAIT semantics if
      the pre-registered ceiling (US$25 / 8 vCPU / 64 GiB / 6 h) does not
      cover the estimate. Owner informed via the plan's pre-registration;
      no executor-set spend.
- [ ] Cloud run executes Task-17 legs under the pinned single-thread recipe,
      PLUS 3 repeated multi-thread solve legs; artifacts pulled back;
      VM deleted (checked).
- [ ] Recorded at `phase14.stage0.determinism`: (a) CRN cross-host compare =
      EQUAL (bit-exact half of gate 4 → PASSED in Stage 0; a mismatch is a
      STOP, owner adjudication — it breaks the CRN identity assumption);
      (b) cross-host single-thread max-abs/RMS deltas (tolerance_gate);
      (c) same-host multi-thread spread over 3 runs (tolerance_threading);
      (d) measured $ cost, wall, egress GiB → the spend-table basis columns.
- [ ] The two tolerances land as SEPARATE recorded numbers (fork-g pin 2);
      the production spot-check tolerance = their envelope, computed and
      recorded beside, formula in evidence.

**Verify:** `pixi run test -- tests/test_phase14_tier2_report.py -v` → PASS
(report assembly on fixture inputs); `phase14.stage0.determinism` populated
after the cloud run.

**Steps:**
- [ ] Failing report-assembly tests → FAIL → implement → PASS.
- [ ] Estimate cost; `authorize`; launch via SkyPilot; run legs; pull back;
      compare; record; delete VM (verify deletion).
- [ ] Pre-commit; commit `feat: phase14 tier-2 probe — cost basis + two
      determinism tolerances + CRN cross-host bit-exact`; push.

---

### Task 19: THE SEAL (0a-6 — last in 0a)

**Goal:** One sha-sealed evaluation-set artifact assembled from Tasks 5, 8, 9,
11 + the Task-1 descriptor schema; immutable, amendment machinery built WITH
it, recompute + tamper tests.

**Files:**
- Create: `src/sverdrup/validation/phase14_seal.py`, `scripts/phase14_seal.py`
- Test: `tests/test_phase14_seal.py`

**Acceptance Criteria:**
- [ ] `build_seal()` assembles deterministically: epoch table bytes (Task 5);
      locked gauge IDs + split seed + screening config (Task 8); instrument
      configs incl. nulls + seam rubric thresholds (Tasks 9/11); c2 era
      windows; the descriptor SCHEMA version it binds to (Task 1). Output:
      `phase14_evaluation_seal_v1.json` + `seal_sha` (sha256 of canonical
      bytes).
- [ ] `verify_seal(path, expected_sha)` — byte recompute; a single flipped
      byte → refusal (tamper test, the phase-13 protocol_sha pattern).
- [ ] Recompute test: rebuilding from the same inputs is byte-identical.
- [ ] **Amendment machinery (fork-f pin 2), built WITH the seal:**
      `supersede_seal(old_path, new_content, owner_signoff: str)` writes
      `…_v{n+1}.json` carrying `{supersedes: old_sha, signoff, date}`;
      MUTATION of an existing seal file is impossible through the API
      (write-once check + test); `verify_seal` on a superseded version still
      passes (history stays auditable).
- [ ] Seal sha recorded in evidence AND printed for the PROGRESS entry
      (every subsequent pack quotes it).
- [ ] Task-10 ceremony wired to the REAL verifier (stub replaced; refusal
      tests still green).

**Verify:** `pixi run test -- tests/test_phase14_seal.py
tests/test_phase14_locked_tier.py -v` → PASS.

**Steps:**
- [ ] Failing tests (determinism, tamper, write-once, supersession chain) →
      FAIL → implement → PASS.
- [ ] Build the REAL seal v1 from Tasks 5/8/9/11 outputs; record sha.
- [ ] Pre-commit; commit `feat: phase14 evaluation-set SEAL v1 — immutable,
      supersession-only amendments`; push.

---

### Task 20: GATE 0 — owner review (userGate)

**Goal:** The Stage-0 owner gate: sealed set signed, spend table authorized,
gates green, tolerances recorded — Stage 1 planning unblocks on approval.

**USER-ORDERED GATE — NON-SKIPPABLE.** This task was requested by the owner in
the current conversation. It MUST NOT be closed by walking around it, by
declaring it "verified inline", or by substituting a cheaper check. Close only
after every item below has been re-validated independently, with output
captured, and the OWNER has replied with approval.

**Files:**
- Create: `docs/superpowers/2026-XX-XX-phase14-gate0-pack.md` (dated at
  assembly)
- Modify: `PROGRESS.md` (gate banner + seal sha)

**Acceptance Criteria:**
- [ ] Pack quotes, verbatim from evidence/artifacts (never re-derived):
      seal sha + contents inventory; epoch table (all columns, handicap
      rows); locked-gauge counts per stratum + c2 windows; gate-2 loader
      identity result; CRN cross-host EQUAL + the two tolerances + measured
      cloud cost; probe-tile measured-vs-model ratios; golden-tile
      dc2021a-vs-CMEMS-MY deltas (tabled flag state); refusal-test census
      (locked gauges, touch ceremony, P0-2, spend WAIT); partition-of-unity
      test census; storage ledger vs budget.
- [ ] Explicit zero-lines: zero evaluation-bearing maps (PROBE labels
      enumerated); zero locked opens; zero c2; tally untouched.
- [ ] Owner attention items listed FIRST: the two pre-registered defaults
      consumed (Tier-2 ceiling, storage budget) with actuals beside; the
      dc2021a gate-2 substrate interpretation; any golden-tile tabled
      divergence; any probe ratio outside the Phase-12 conservatism-ledger
      bracket.
- [ ] STOP after posting the pack. Owner reply = the gate ruling; Stage-1
      plan writing is authorized by that reply, never before.

**Verify:** pack committed + pushed; PROGRESS updated; owner approval message
received (captured in PROGRESS at close).

**Steps:**
- [ ] Assemble pack from evidence keys verbatim; dual review (spec-compliance
      + adversarial) BEFORE posting.
- [ ] Commit `docs: phase14 gate-0 pack — held for owner review`; push; STOP.

---

## Task dependency graph

```
T0 (P0-2)                     — first, standalone
T1 → T2 → (T7)                — contract → dc2021a+gate2 → golden-tile
T1 → T6                       — contract → JPL adapter
T1 → T3 → T4 → T5             — contract → CMEMS → census → epoch table
T3 → T7                       — CMEMS subset feeds golden-tile
T8 → T9                       — gauge layer → evaluator
T5 → T10                      — epoch ids → tally ledger keys
T11                           — standalone (rubric + configs)
T12 → T13, T14, T15           — frames → blend / scorer / probe
T3 → T15                      — probe tile needs CMEMS subset
T15, T16, T17 → T18           — sizing + ladder + gate machinery → Tier-2 probe
T5, T8, T9, T11, T1 → T19     — the SEAL (last in 0a)
ALL → T20                     — Gate 0
```

## Self-review (run before handoff)

- SPEC §5 coverage: 0a-1→T4, 0a-2→T5, 0a-3→T8+T9, 0a-4→T10, 0a-5→T11,
  0a-6→T19, 0a-7→T0; 0b-1→T15, 0b-2→T16, 0b-3→T18, 0b-4→T17; 0c-1→T1,
  0c-2→T3, 0c-3→T1, 0c-4→T6, 0c-5→T7, 0c-6→T2; 0d-1→T12, 0d-2→T13,
  0d-3→T14; Gate 0→T20. No gaps.
- Owner plan-ruling coverage: task groups per workstream ✓; 0a-6 last in 0a
  consuming 0a-2/0a-3/0a-5+0c-1 ✓ (T19 deps); Gate 0 userGate ✓; 0a-7 first ✓
  (T0); gate scheduling ✓ (gate 2 runs T2; CRN half runs T18; gates 1/5 +
  solve half = skip-guarded test code in T14/T17 for Stage 1; gate 3 = Stage-2
  machinery, no Stage-0 code — its BY-CONSTRUCTION identity is the fork-e
  gauge, built with the covariate in Stage 2); owner inputs pre-registered ✓
  (header defaults; T16/T18 WAIT semantics); census/epoch concretes ✓ (T4);
  gauge concretes ✓ (T8/T9); seal amendment + recompute ✓ (T19); probe
  configs ✓ (T15/T18 pinned); descriptor schema + synthetic fixture ✓ (T1);
  0d-3 gate-row wiring ✓ (T14).
- Placeholder scan: no TBD/TODO; every step names its code or its exact
  command.
- Type consistency: `SourceDescriptor`/`AlongTrackSource` (T1) consumed by
  T2/T3/T6/T7; `TileFrame`/`anchor_frame()` (T12) consumed by T13/T14/T15;
  `verify_seal` interface pinned in T10, implemented T19.
