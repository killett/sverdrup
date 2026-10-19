# Hygiene notes

Running log of hygiene audits and smells we are intentionally keeping.
Future passes: read this before re-flagging anything.

> Prioritized owner-review queue for everything left open here:
> `docs/hygiene-priorities.md` (P0-P4, effort + trigger per item).
>
> The commit SHAs cited in the 2026-07-16 section predate an unrecorded
> history rewrite and are not on main — read them through the map in the
> 2026-10-18 ERRATUM below.

## 2026-07-16 — whole-repo audit (AUDIT-ONLY, no mutations)

Baseline: HEAD `14f59d9` (Phase 11 closed), tree clean, canonical gate
(`pixi run pre-commit run --all-files`) green. Five parallel read-only
audits: core+libs, application, adapters+validation, tests, scripts.
Totals: **71 FIX NOW** (strictly behavior-preserving, low risk),
**81 NEEDS DISCUSSION**, ~**94 LEAVE**, **11 bugs** (2 firm, rest
latent/suspected/test-tautology). Nothing was changed — the whole-repo
scope defaulted to audit-only.

Orchestrator spot-verified at source: harness `atomic_write_json`
double-close, stage-B inline c2-touch guard gap, coherent
`realize_one` hardcoded noise source.

### Bugs (recorded separately from hygiene; NOT fixed in this pass)

FIRM:

- `src/sverdrup/application/calibration/harness.py:1188`
  `atomic_write_json` failure path: `os.close(fd)` succeeds inside
  `try`, then if `os.replace` raises, the `except` re-closes the fd →
  `OSError(EBADF)` masks the original error and the `.tmp` file leaks
  (the unlink is skipped). Happy path correct. Same defect verbatim in
  the frozen script copy `scripts/phase8_gate_run.py:693` (that copy is
  a sealed evidence record — fix only the src home).
- `src/sverdrup/distributions/coherent.py:215`
  `CoherentSampler.realize_one` hardcodes `MemberSeededZr().draw_one`
  instead of the injected `self.structured` — the StructuredNoiseSource
  swap seam (design 5c/8) is non-functional on this path. Latent today
  (default == hardcoded); real the moment the seam is exercised.
- Test tautologies (can never fail):
  `tests/test_phase8_gate_run.py:568` (asserts absence of a file
  nothing creates); `tests/test_phase10_lanes.py:76` (assert after
  loop checks only `c2` via loop-var leakage);
  `tests/test_miost_inflation.py:72` ("original untouched" check is
  `allclose(v*0+v, v)` — algebraic identity, needs a pre-`rescaled()`
  snapshot).

GOVERNANCE-GRADE (owner escalation):

- `scripts/stage_miost_gate_run.py:801-817` — the inline env-gated c2
  touch inside `stage_b_main` performs the acceptance touch WITHOUT
  `_assert_c2_untouched` (:821) or the pre-registered `_c2_reading`
  (:834); the later `--c2-touch` mode has both. A second
  `SVERDRUP_MIOST_C2=1 --stage-b` run would silently re-spend the one
  owner-authorized touch and overwrite the acceptance record.
- `scripts/tune_miost_inflation.py:117` — superseded Task-17 script
  writes `stage_b_{mean,var}_maps.nc` to the SAME `OUT_DIR` as the
  gate runner's Stage-B evidence maps; a rerun clobbers gate evidence
  that `diag_stage_b_localized_calibration.py` reads. Retire or
  retarget.

LATENT / SUSPECTED (owner look, no code change proposed):

- `src/sverdrup/methods/{oi.py:124,gmrf.py:133,fem.py:193}` —
  `np.diag(obs.error_model.as_matrix(n))` silently truncates a
  correlated R to its diagonal; a `BandedErrorModel` would lose its
  correlations in any method with no guard. Guard vs explicit
  diagonal-only contract = owner decision. Related:
  `observations.py:38,58` `as_matrix(n)` ignores `n` despite
  "must match" docstrings.
- `src/sverdrup/methods/miost_solver.py:112` — `ConvergenceReport`
  iteration count off-by-one (telemetry only; residuals correct).
  Fix changes logged numbers → not behavior-preserving.
- `src/sverdrup/distributions/persisted.py:245` — `regrid` sets
  `captured_energy=1.0` unconditionally even for rank-truncated
  factors (and placeholder `seed=0` at :383). May be an intentional
  total-variance claim — confirm before touching.
- `src/sverdrup/eval/fidelity.py:86` — `_obs_slope_1d` pass
  re-alignment via `searchsorted` assumes strictly increasing unique
  timestamps; duplicates at a pass boundary would misalign silently.
- `scripts/generate_oi_maps.py:313,350` — "all 5 mapping missions"
  while listing six; the miscount is stamped into produced nc attrs
  (source-vs-recorded-artifact divergence — comment fix is safe, the
  stamped-text sites need an owner call).
- `scripts/phase9_g_pre_anchor.py:344` — claims a "byte-identical"
  regression check but compares parsed JSON (weaker than stated).
- `scripts/phase10_probe.py:293` — clobber guard tests a key nothing
  fills; always-true condition (benign; comment fix).
- `scripts/diag_miost_localization.py:308` — `weight_sum` accumulated,
  never read; looks like a dropped normalization assert for probe-4.
- `src/sverdrup/validation/report.py:121` — RESULT.md renders
  "area_weighted_rmse µ" for a value computed as global unweighted
  `1 - rmse/rms`; user-facing text, not behavior-preserving.
- `src/sverdrup/validation/download_ocean_data_challenges_2023.py` —
  docstring promises SHA256 verification but all manifest hashes are
  empty → "skipped" branch unreachable (every rerun re-downloads);
  `extract_existing` reports "extracted" for non-archives.

### FIX NOW backlog — APPLIED 2026-07-16 (owner-approved mutation pass)

Executed same day as the audit: 71 commits on main (one per item,
`52023a9`..`6ec1d03`), per-file pre-commit before every commit,
all-files gate green after each area, full suite green after the last
commit: **808 passed / 13 skipped / 1 xfailed** (the +1 vs the
recorded 807 predates the pass — both HEAD and the baseline commit
`14f59d9` collect exactly 822 nodes; collection is env/artifact-
conditional, not a behavior change from this pass).

TWO AUDIT ERRATA (items skipped — premises false at source):

- `pipeline.py:196` — the function-local `partition_weights` import is
  the ONLY import of that name; line 27 imports other names from
  `blend`. Not a duplicate; deleting it would NameError.
- `distributions/blend.py:232` — same shape: module-top import brings
  `UncertaintyProvenance, blend_transform`, NOT
  `degradation_transform`; the local import is the only one.

DISCLOSED DEVIATIONS (all behavior-preserving, in-commit):

- EPOCH single-sourcing repointed two importers
  (`eval/resolution.py`, `tests/test_eval_resolution.py`) to
  `validation.params` — mypy `no_implicit_reexport`. FOLLOW-UP
  CANDIDATE: `calibration/harness.py:171` defines its own same-value
  `EPOCH` (out of that item's scope, still duplicated).
- Crossfade dedup found a THIRD verbatim consumer
  (`GmrfCoreAuthoritativeSolve.crossfaded_member`); all three now call
  one `_weight_crossfade` helper; oracle/gate tests green.
- `_tree_gate._Quad` dead third slot removed from the type entirely
  (file-private, rg-verified no external constructor).
- `miost_basis` domain-box constants use the explicit
  `BOX_LAT as BOX_LAT` re-export form so `scripts/diag_miost_*.py`
  importers stay untouched.
- Script-loader consolidation: `tests/helpers.load_script` (sys.modules
  -registering variant); the five formerly module-level loaders now
  also register in sys.modules (the mandated-correct variant);
  `test_calibration_harness._load_anchor_module` deliberately NOT
  migrated (avoids sys.modules by design).
- `unit/test_accuracy.py` item was an assert INSIDE a test, not a
  standalone test; only the vacuous disjunct was deleted.
- Old test names `test_clip_engages_and_is_recorded` /
  `test_piecewise_lookup_and_out_of_range_raises` still appear in the
  frozen Phase-8 plan doc — historical record, left as-is.

Original backlog as audited (line numbers refer to pre-pass tree):

src core/libs (22): duplicate function-local imports shadowing
module-top imports (`distributions/blend.py:232`,
`distributions/reduction.py:140`, `methods/gmrf.py:53,129`,
`methods/miost.py:350` — NB the miost.py `distributions.calibration`
/`miost_ensemble` local imports are genuine cycles and must stay);
same-value constant dedup (`distributions/calibration.py:44`
`_LON_EDGES/_LAT_EDGES` from `BOX_LON/BOX_LAT`; `methods/miost_basis.py:20`
re-declares `miost_sizing` constants); coherent-batch 256 → module
constant (`blend.py:134,153`); `WindowPlan` rebuild → `_plan()` helper
(`miost_ensemble.py:109,157`); crossfade duplicate hoist
(`coherent.py:362 vs 750`); docstring/comment corrections
(`core/observations.py:14` diagonal-contract wording,
`core/grid.py:137` PointSet attributes, `coherent.py:406` deleted
`_draw_joint` ref, `coherent.py:847` seed-keying claim,
`persisted.py:57` "never materialises dense P" claim,
`calibration.py:1091` stale side-car comment); missing docstrings
(`methods/fem.py:100 _delaunay`, `gmrf_grid.py:57 idx`,
`miost_basis.py:174 n_t`, `methods/__init__.py`); intent comments
protecting load-bearing local imports (`gmrf_grid.py:191,227` cholmod
deferral, `eval/fidelity.py:74` cycle-avoidance); rename `kernel.py:129`
`lx/ly` → `l_a/l_b`.

application (9): `application/__init__.py` docstring;
`eval_context.py:43` double factory instantiation;
`pipeline.py:196` duplicate local import; `orbit_geometry.py:162`
loop-var overwrite rename; `likelihood.py:203` missing Raises section;
`folds.py:79` hardcoded `2.0` ×5 → `constants.CELL_DEG` (identical
float, byte-identical numerics); `harness.py:827` unused `cal` param
on `_bars`; `loop.py:98` double `expl(params)` call;
`stage_a.py:207` stale retired-predicate comment.

adapters/validation (6): `their_eval.py:35` dead `_DELTA_*` constants
+ stale docstring phrase; `run.py:23`+`input_adapter.py:31` duplicate
`EPOCH` decision → single source; `input_adapter.py:144` double
`_lonlat_nodes()` call; `report.py:196` triple `xr.open_dataset`;
`sha256_of` byte-identical in both download scripts → shared helper;
`src/sverdrup/__init__.py` docstring (docstring only — `__version__`
re-export is a surface decision, ND).

tests (27): script-loader importlib boilerplate ×11 files → one helper
modeled on `test_provenance_guard._load_script`; dead symbols
(`test_calibration_regions.py:15`, `test_lane_compare.py:40` unusable
`n` param, `test_orbit_geometry.py:25`, `test_eval_context.py:128`,
`test_calibration_field.py:1005` del-without-assert,
`_tree_gate.py:319` unused `_val`); duplicate fixture/track
construction (`test_lane_compare.py:47 vs 218`,
`_tree_gate.py:211 vs 304`); `pytest.raises` instead of hand-rolled
try/except (`test_phase10_provider.py:92`); delete superseded vacuous
disjunction (`unit/test_accuracy.py:9`); tautology deletions/
strengthenings (3 BUGS above); stale docstrings/comments ×~10
(`test_calibration_field.py` ×5, `test_calibration_folds.py:314`,
`test_calibration_regions.py:267`, `test_calibration_likelihood.py:248`,
`test_phase8_identity_regression.py:127,303,476`, `_tree_gate.py:1`,
`capture_phase8_factory_bytecompat.py:6`); two test renames
(`test_calibration_field.py:164,333`);
`test_calibration_harness.py:440` redundant tautological keys assert.

scripts (7, all comment/docstring/name-only): stale mirror pointers
(`phase8_gate_run.py:108,121`); `phase9_fit_run.py:8` dev-scope
filename claim; `phase9_g_pre_anchor.py:368` step mislabel;
`generate_oi_maps.py:313` six-vs-five comment, `:155`
`_AUDIT_RTOL_THRESHOLD_M` misnomer (it is max-abs metres), `:289`
docstring return keys.

Scheduling constraint (repo memory): NO source edits while any gate
suite or chain runs; batch fixes outside evidence runs; getsource-
sensitive tree-gate tests exist.

### NEEDS DISCUSSION register (owner/maintainer decisions)

Cross-cutting:

- **deg→km constant families.** Two deliberate frames: 111.195
  (GP/Matérn: `methods/kernel.py:13`, `methods/gmrf_grid.py:20`,
  `validation/params.py:50`, `derived/firstdifference.py` `_DEG2M`)
  and 111.32 (MIOST/orbit/spectral: `application/orbit_geometry.py:34`,
  `eval/map_spectrum.py:29`, `methods/miost_sizing.py:23`). Dual-family
  split is intentional and test-pinned; each family has multiple
  definition sites. One definition per family = behavior-preserving,
  closes silent-drift hole. Which module owns each = layering decision.
- **`_PASS_GAP_SEC = 60.0` ×3** (`harness.py:173`,
  `lane_compare.py:49`, `orbit_geometry.py:35` `_GAP_SEC`) — one
  pass-splitting decision, rule of three reached; each host is
  pinned/sealed machinery.
- **`GridSpec._lonlat_nodes`** — private name, 16+ external consumer
  sites across layers. De-facto public API; bless (rename/公开) in one
  decision covering all sites.
- **Phase-1 scaffolding never wired** (delete-or-keep sweep, all
  exported surfaces): `adapters/odc/ose.py OseSource`,
  `download.py open_dodsC`, `natl60.py WINDOW/OBS_URL/REF_DAILY_URL`
  (+ unread `self.cache` whose ctor mkdirs as a side effect),
  `application/config.py RunConfig`, `core/observations.py Observation`,
  `core/parameters.py ResolvedParams`, `core/evaluation.py Objective`,
  `eval/calibration.py pit()` (likely spec-5.6-committed metric).
- **Cross-script redundancy families** (extract for FUTURE scripts;
  ran runners stay frozen): F1 `_write_evidence` ×~10; F2
  validation-track interp/scoring protocol ×8+; F3 atomic-JSON copies;
  F4 scoring numerics re-paste (`phase8_gate_run.py:440` vs
  `harness.py:226` — bit-drift hazard); F5 gate-runner twin helpers;
  F7 `build_jet_core_mask.py` vs `build_phase8_jet_core_mask.py`
  byte-identical pair (phase8 sibling = frozen provenance record).
- **Test coverage gap ratified-or-revived:** dead C4 fixtures
  (`_strip_fixtures.py:137`, `_tree_gate.py:407`,
  `make_natl60(nonstationary=True)`) mean NO blend/tree-driver test
  runs a nonstationary provider (method-level coverage exists).
  Delete = ratify gap; revive = one blend-level nonstationary test.

Selected module-level items (full details in the audit transcripts):
`run.py run_challenge_map` vs `run_mean_var_maps` duplicated solve
spine (byte-identical-maps gate risk); `pipeline.py` `_evaluate` vs
`_evaluate_blended` shared spine + third `_subset_obs` copy
materializing dense R; `harness.py draw_s_layout` reimplements
`folds.s_fold_layout` (frozen Phase-8 bit-repro); `harness.py:1026`
inline eligibility recompute duplicating `folds._beats_beyond_band`
semantics; `atomic_write_json` home (generic util living in the
1232-line harness forces an import cycle workaround);
`feasibility.py CompositeFeasibility.explain` doc-vs-code gap (skipped
members record `exclusion_reason=None`); `stage_miost.py` docstring
recommends StoredG@8e9 while `PeakFeasibility` (Task-22,
owner-ordered) is wired nowhere; `stage_a.py:137 _run_stage`
private-named cross-module API; `blend.py` `_sampler` dead field +
`parts[0]` sampler_spec first-tile-wins without homogeneity check;
`distributions/calibration.py:750` dataclass with hand-written
`__init__` (`dataclasses.replace` would raise); `coherent.py
_strip_network` no production caller since d960f15;
`StructuredNoiseSource.draw`/`MemberSeededZr.draw` never called
(seam undercut by the `realize_one` bug); nearest-node lookup
convention ×4 (`ensemble.py:54`, `persisted.py:250`, `coherent.py:24`,
`gaussian.py:63`); `reduction.py:175` silent representation default;
`methods gmrf/fem` `op._factor.solve` private reach + duplicated
temporal-taper-into-R block (leaf-identity check required);
`gmrf_grid.py .matrix` legacy hooks; `miost_basis.py build_s/
temporal_taper/DiagonalR` never-wired seam set (test-oracle-in-prod
choice); `gmrf.py node_sample` claims to be the coherence hook but
`coherent.py` drives via `_factor_obj().sample`; `miost.py`
solve/sample_members duplicated G/Q/R construction + telemetry drift
(signed shipped numeric path — high care);
`derived/firstdifference.py` protocol-undeclared `time_days` +
`metric_scale_x` carrying y-scale; `their_eval._prepare_imports`
delegate shim (has a live caller in `scorer.py:198`, unlike the
deleted harness shim); `_is_retryable` vs `is_retryable` transient-
fault predicate defined in two layers; `evaluator_names`
(`eval_context.py:258`) zero callers; `__version__` re-export;
`report.py` metric-name text; 2023 download-script sha/skip
resolution; `_tree_gate.py` doc-anchored dead helpers
(`matched_chain_edge_baseline` cited 4× in PROGRESS.md,
`edge_seam_corr_err` named in Stage-C design docs);
`test_calibrated_distribution.py` `_OI_MASK_ARTIFACT` gates two tests
that never read it; three persisted-precision builder near-copies;
`test_miost_basis.py:68` overlap assert insensitive to its docstring's
bug; `test_tree_kriging_oracle.py:67` seed-independence test never
invokes the driver.

### Intentional smells KEPT (verified deliberate — do not re-flag)

- All pinned numerics, SHAs, seeds, wording strings, sealed constants:
  identity gates and provenance pins (incl. the −2.44 windowed-slope
  test pin — recorded owner decision, never "fix" toward −2.0).
- Refusal guards by AssertionError/ValueError; `LatitudeField.__float__`
  raises per dispatch contract; `classify_orbit` RATIO_GAP refusal.
- Protocol-conformance unused params (scorer/strategy/lane_compare
  closures, `ScaleAwareHalo.halo_for grid`,
  `derive_family(ascending)`, `input_adapter params` "provenance/
  symmetry").
- `likelihood.py` `import X as X` re-export monkeypatch seam
  (documented); `folds.select` C901 and `harness.build_evidence`
  PLR0915 (gated leaf-identical / evidence assembly);
  `folds.py:577` `_audit` discard (plan-verbatim).
- `RelaxedCoherenceFeasibility` illustrative duplicate;
  `feasibility.joint_tol` shorthand record; `DUACS_TARGET_MU`
  aspirational; `coherence_gate` production-unused evidence machinery
  (anti-false-green rule).
- Pinned magic mirrors: `_norm_uv` 300/38/5, load box 295/305/33/43,
  regions 5×5 literals, `stage_b_gate_run.py:155` 1.25 gate bar,
  `tune_miost_inflation.py:104` CRN seed pin (must match
  `stage_miost:654` by design).
- `STAGE_B_INFLATION_S` retained as the signed Stage-B record;
  `GmrfCoreAuthoritativeSolve` non-registration; chain driver kept as
  pinned reference; regrid `NotImplementedError` stubs pinned to plan
  tasks; `derived` NotImplementedError stubs = committed signatures
  (spec 6); `Registry.run` flat-merge collision hazard documented
  "KEPT as the core spine"; `_cell_index` documented output-identical
  cross-layer twin; `params.py _KM_PER_DEG` coupling documented;
  eval-box constants deliberate verbatim notebook transcriptions;
  `access.py render_netrc/write_dap_auth` documented retention;
  `report.py:216` documented substitution; `run.py run_year` legacy
  wrapper with live callers; `solve.py _git_version` broad except
  (documented fallback).
- Scripts house idioms: import-time env-scope parse + SystemExit ×7
  (fail-fast before heavy import); `phase10_prereg` importlib reuse of
  a sibling's `_write_evidence` (deliberate per 99880c9→bce678b);
  white-box diag scripts reaching privates; `NamedTemporaryFile(
  delete=False)` handoff in gate runners; `np.vectorize(math.erf)` in
  phase8_gate_run (bit-drift on recorded CRPS if "fixed" — LEAVE);
  frozen evidence-runner scripts are RECORDS — value is
  reproducibility, not cleanliness.
- Tests: determinism self-compares re-execute both sides (valid);
  five documented no-raise gate-path tests; isinstance-only
  protocol/dispatch tests; skipif reasons all checked accurate;
  `test_miost_operators.py:109` `0.03**2` explained by adjacent
  docstring; `test_calibration_folds.py:229` literals are
  constant-drift pins; mypy relaxed for tests (recorded config
  decision).
- `timeout=120` in both download paths — two sites, low value to name.
- `ensemble.py:38` dense `np.cov` scalability landmine and
  `firstdifference.py` O(ny·nx) exact-covariance double loop —
  flagged, correct as designed.

## 2026-10-18 — whole-repo audit (AUDIT-ONLY, no code mutations)

Baseline: HEAD `029071f`, origin in step (`ls-remote`), tree clean, canonical
gate (`pixi run pre-commit run --all-files`) green in 21.5 s with the tree
unchanged after it. No pytest run (audit-only; the gate does not include it).
Scope: everything changed since the 07-16 pass (774 commits, ~49k inserted
lines, 136 new files under src/tests/scripts) plus the status of every open
P0-P4 item. Nine parallel read-only auditors: src new adapters/app/eval · src
MIOST family · src new validation · `phase14_stage1_run.py` + shell tooling ·
other phase-14 scripts · phase-12/13 + misc scripts · phase-14 tests · other
new/changed tests · queue status + docs/config. Line numbers are as of
`029071f`.

Totals (auditor-reported): ~95 bug findings (~24 P0-class evidence-integrity
hazards; ~20 new tests that cannot fail), 71 FIX NOW, 77 NEEDS DISCUSSION,
84 LEAVE. Prior queue: 1 resolved (P0-1), 33 open-unchanged, 7 open-changed;
the three 07-16 test tautologies are FIXED. Per-item status table:
`docs/hygiene-priorities.md` § "Status at 2026-10-18".

Re-read at source by the orchestrator (✔ below): `size_tile` peak pricing;
the spectral empty-PSD regression; the `provenance_guard` regex; the mirror
deletion blind spot; the `seam_rows` overwrite and seal-path defect; the
settling node's wholesale replace; the `tier2_probe` overwrite; the
`--stage-b` first flush before the disarm; the `stage_miost_gate_run`
whole-store overwrite; the `locked_tier` non-atomic tally write;
`test_miost_ensemble.py:705`; the packaging deps; the SHA map. Everything
else is auditor-verified at source and NOT re-checked by the orchestrator.

Operational mitigation taken (owner-approved 2026-10-19): a dated copy of the
evidence store at
`data/2021a_ssh_mapping_ose/evidence-backups/stage_miost_gate_results.2026-10-19.json`
(gitignored; mode 600; sha256 `f67392ae…e8cd` sidecar alongside, equal to the
live store at the time of copy; store last written 2026-09-21).

### ERRATUM — SHAs cited here and in PROGRESS/archive are not on main

History was rewritten at or after 2026-07-21 21:05, and nothing records it.
~119 of ~211 SHAs cited in tracked markdown (auditor count) are unreachable
from main. Each has a same-date, same-subject twin with an IDENTICAL tree.
✔ Verified: `14f59d9`→`8892120`, `52023a9`→`d0d956d`, `6ec1d03`→`724177a`,
`d960f15`→`bd6a351`. So the 07-16 applied pass is `d0d956d..724177a` on
main, and its baseline is `8892120`. The records are left as written.

### THE HEADLINE — one CLASS, not an instance: evidence-store writes are unguarded

The shared store `data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json`
(1 MB, mode 600) is gitignored, untracked and single-copy ✔. The only
backstop is `docs/validation/evidence-mirror/`, which covers the phase-14
subset only. These compose into one hazard:

1. **Whole-store wipe on a flagless or typo'd run** ✔ —
   `scripts/stage_miost_gate_run.py:463`: `main()` builds a fresh dict and
   `RESULTS.write_text(...)`s it over the store. `main()` is the `else` of a
   membership-based argv dispatch (:1029-1041), so no flag, `--stageb`,
   `--c2-touch=1`, or `SVERDRUP_MIOST_SCOPE=dev` all reach it. The phase 8-13
   evidence is not mirrored. **Re-prices the P4 "argv parsing ignores unknown
   flags" item to P0.**
2. **Mirror blind to deletion** ✔ (found independently by two auditors) —
   `scripts/phase14_evidence_mirror.py:719-757` pre-filters unresolved
   registered paths as PENDING, so `select_nodes`' "deliberately fatal"
   KeyError (`src/sverdrup/validation/evidence_mirror.py:82-84`) cannot
   fire, and `detect_changes` compares only nodes present on both sides. A
   deleted witnessed node makes `check` print PENDING and pass, and `sync`
   drops it silently. The gate-1 closure tripwire inherits this blind spot.
3. **Mirror does not enforce seal drift** — `check` prints `seal vs mirror:
   DRIFTED` and exits 0. `sync` overwrites `SEAL_MIRROR` with no append-only
   gate. `SEAL` is hard-coded to v1 (also `phase14_osse_pricing.py:37`).
4. **Overwrite-on-rerun with no write-once guard.** Detected only after the
   fact by the mirror, or never for `NOT_MIRRORED` nodes:
   - ✔ `phase14_stage1_run.py:3286-3333` `record_seam_rows` /
     `record_seam_block` — a cheap rerun (all resume stores exist) erases the
     pin-45(b) NOT_ESTABLISHED marks. `withhold-sigma-rows` then refuses at
     :6809 because the marker node exists, so the firewall cannot be
     restored.
   - ✔ `phase14_stage1_run.py:1373-1375` `tier2_probe` — the defaults
     overwrite `tier2_probe_kuroshio_m100`, the node R4's pending 36-d chain
     derives from. It writes the module-global `EVIDENCE` with no seal check.
   - `phase14_stage1_run.py` `probe` / `probe --maxiter` / `seam-probe`
     (:1389, :1045, :2506) are "never rewritten" per the comment and CLI
     help, but nothing enforces it, and they are NOT_MIRRORED. Also the
     lane-0 "FROZEN" bundle (:5761-5931) and `report_rows` (:5009).
   - ✔ `phase14_settling_measurement.py:488-539` defaults to `record=True`
     and replaces the node wholesale. That destroys the owner-added
     `pin_53_m_requirement` / `pin_54_condition` blocks, which no code
     produces and which `phase14_projection_declarations.py:137` cites.
   - `phase14_golden_tile.py:284-292` destroys the hand-added
     `mu_scale_check`. `phase14_ensemble_floor_factor.py:251-338` re-creates
     a WITHDRAWN node carrying the "cannot fail" ±4-sd test. Also
     `phase14_sigma_diagnosis.py:713-764`, `phase14_kernel_pack.py:771`,
     `phase14_projection_declarations.py:969`, `phase14_probe.py:196`,
     `phase14_anchor_gate.py:729`, `phase14_gauge_run.py:148`.
   - ✔ `stage_miost_gate_run.py:666-684` — a `--stage-b` rerun's first
     `_flush("RUNNING…")` replaces `stage_b`, erasing the signed
     `c2_acceptance` and so re-arming `--c2-touch`. This happens BEFORE
     `refuse_inline_touch()` at :800. **P0-1's "RESOLVED" overstates.** The
     rerun also rewrites the canonical `stage_b_*` maps that P0-2 protects.
   - `phase13_prereg.py:182-271` re-dates the sealed band protocol.
     `phase13_lane_run.py:597-615` also leaks dev scope into the full-scope
     key. `phase12_miost6_run.py:810` destroys the owner's T7 launch
     adjudication; see also its `:545-627` and `phase13_c2_touch.py:103-136`.
   - `phase14_seal_run.py:306-358` — `supersede` has no version cap (pin
     36(d): "hold the seal at one version"), and `build` writes the seal
     before the pointer refusal.
5. **The seal tripwire checks the wrong store** — `verify_current_seal()` is
   called with no `evidence_path` in 8 `phase14_stage1_run.py` writers
   (:942, 1071, 3303, 3327, 5001, 5881, 6066, 6174) ✔ (3303, 3327), plus
   `phase14_anchor_gate.py:696`, `phase14_sigma_diagnosis.py:703` and
   `locked_tier.py:39-57`. The contract is at `phase14_seal.py:175-179`;
   only `stage1_run:6798` complies. The tests stub it with zero-arg lambdas
   ×29, which locks the defect in.
6. **Non-atomic or lossy writes** — ✔ `locked_tier.py:151` and
   `phase14_seal.py:92-102` `write_text` the whole store.
   `atomic_write_json` (P1-#3) still double-closes, AND never checks
   `os.write`'s return, so a short write installs truncated JSON atomically.
   The corrected-touch defect migration is not persisted
   (`phase12_miost6_run.py:1130`, `phase13_c2_touch.py:265`) — a regression
   from phase8, which writes the whole dict.
7. **Locked tier** (`validation/locked_tier.py`; no production caller yet,
   so decide before Stage 2 wires it):
   - The tally counts clean completion only. That is intended per the
     comment at :139, but a raise after the locked open is uncounted, unlike
     the misfire ruling's "dated defect key, never a silent re-execution".
   - A second corrected re-touch overwrites `{era}_corrected_by`.
   - `corrected_by=""` bypasses the one-touch refusal.
   - The module-global flag cannot see a second process.

Recommended single decision: one src store-node recorder that every future
writer imports. It is seal-gated with the caller's path, write-once by
default, uses `--supersede --reason` to preserve the prior body, and writes
atomically with a checked write. Alongside it: mirror deletion detection and
seal drift as a hard fail. `phase14_refresh_election.py:279-285` is the
existing model. Frozen runners stay records; guard them only by
refusal-on-rerun.

### Other bugs in live src (P1-class)

- ✔ `methods/miost_sizing.py:321-331` — `size_tile` computes the tile's
  `n_coef`, then calls `peak_model`, which recomputes it at signed-box dims
  (`peak_model` takes no domain). `peak_model_mib` gates `tier1_eligible`,
  `seam_ram_gate` and `peak_ratio`, so RHS and workspace are priced at box
  size. A fix changes recorded numbers (e.g. 4715.6 MiB), so it is an owner
  call.
- ✔ `eval/spectral.py:150` — `_coherence_evidence` (pin 160a) runs
  `np.nanmin` on an empty PSD BEFORE `_coherence_guard`, raising a bare
  ValueError instead of ShortTrackError. The four tuning catch sites
  (`loop.py:109`, `stage_a.py:187`, `lane_compare.py:293,311`) no longer
  catch it. Untested.
- ✔ `validation/provenance_guard.py:25` — `_([a-z0-9]+)_phy_l3` returns the
  token before `_phy_l3` even when the mission is missing
  (`dt_gulfstream_phy_l3_…` → "gulfstream"), so the train/score leak guard
  passes silently. The comment at :23-24 claims such names still fail loud.
- ✔ Packaging — none of these are declared in pyproject, any extra, or the
  conda recipe:
  - `sksparse` (`methods/gmrf_linalg.py:20`), reached via
    `methods.registry` → `gmrf`. This chain already shipped in v0.2.0.
  - `pydantic` + `python-dotenv` (`validation/config.py:8-9`), reached via
    `eval.resolution` → `validation/__init__`.

  So `pip install 'sverdrup[all]'` cannot run the pipeline, and
  `release.yml` never install-smokes the wheel.
- `distributions/miost_ensemble.py:432-658` — the window store binds only
  `(wid, m, root)`, so a store from different params/rspec/basis is adopted
  silently (the docstring at :392 claims refusal). Latent.
- `miost_ensemble.py:281-322` / `miost.py:183-216` — `save_state` omits the
  basis domain, so reloading a `basis_domain=` result crashes or silently
  evaluates at the wrong positions. Latent (no saver/loader today).
- `application/epoch_table.py:48` — `"s6a-lr"` vs the data's `s6a_lr`.
  Already plan work (stage-2 design §5.5).
- Also latent:
  - `adapters/altimetry/contract.py:185`: empty-window IndexError.
  - `adapters/insitu/gauges.py:33`: a cwd-relative locked split fails OPEN.
  - `eval/insitu.py:162,206`: order-dependent alignment (new P2-#16
    instance); `:232`: ZeroDivisionError.
  - `cmems_my.py:133`: an empty manifest gives a constant sha.
  - `jpl_ssha.py:54`: no locked-c2 exclusion (suspected).
- Validation edge cases:
  - `gate_schema.py:296` accepts a boolean `extrapolation_declared`.
  - `seam_metrics.py:233` / `ensemble_settling.py:221`: zero σ raises
    ZeroDivisionError.
  - `ensemble_floor_null.py:193`: unchecked weights give a silent NaN.
- `miost_solver.py:130-156`, `miost_ensemble.py:423-487` — npz is lazy, so a
  member CRC error surfaces as a bare BadZipFile, the outcome pin 122
  forbids.
- Scripts (non-P0):
  - `phase13_diagnostics.py:201`: a lexical sort drops 167 overlap pairs
    from the recorded §8.5 check (a wrong recorded number).
  - `diag_stage1_hypothesis_tests.py:552` writes the tracked artifact before
    its STOP.
  - `download_cmems_my.py:279` writes the ledger row only on full
    completion.
  - `download_gauges.py:127`: an unretried catalog fetch, where a 5xx
    reports "done".
  - `phase14_probe.py:229`: the T18 `tolerance_threading` is mis-measured
    (live if R4 elects B).
  - `phase14_stage1_run.py:1882`: an unreadable lock becomes pid −1, and
    `os.kill(-1,0)` succeeds, so it is treated as held; `:3706`: resume
    ignores the stored m/maxiter/root.
- Tooling:
  - `resume_checks.sh:57-63`: a dirty tree never sets a non-zero exit,
    although CLAUDE.md step 0 says it does.
  - BEHIND/DIVERGED cannot distinguish origin-ahead (pin 191).
  - An `ls-remote` failure is reported as ABSENT.
  - The hooks and scripts use `--git-dir`, which is wrong in linked
    worktrees.
  - `stage1_leg_launcher.sh:90`: `kill -0` liveness spins forever on an
    unreaped zombie (PID 1 does not reap).
  - `phase14_gate_suite.py` stamps only `*.py` + pyproject, and `verify`
    does not echo the command, so a `--suite` subset attests like the full
    suite (the pin-197c scope class).

### Tests that cannot fail (new; the 07-16 three are all FIXED)

- ✔ `test_miost_ensemble.py:705`: a ≤2 bound on a 2-window fixture, so pin
  133's leg-1 accumulation test cannot catch a cache-everything mapping.
- `test_miost_ensemble.py:627`: `assert first` on a non-empty str.
- `test_evidence_mirror_gates.py:163`.
- `test_ensemble_floor_null.py:351`.
- `adapters/test_jpl_ssha.py:92`.
- `test_phase12_config.py:167` (`git diff --stat` sees uncommitted edits
  only) and `:93` (a bare ValueError parent).
- `test_phase13_c2_touch.py:69` — it also reads a 1.4 GB npz on every unit
  run.
- `test_phase13_diagnostics.py:66,76`.
- `test_phase14_locked_tier.py:68`.
- `test_phase14_gauge_screening.py:179` (`or True`), `:120`, `:196`.
- `test_phase14_gate1_closure.py:195` (seal drift passes) and `:207` (digest
  compared to the script's own constant).
- `test_phase14_stage1_run.py:3320`, `:4027`, `:5582`, `:4382`, `:4793`.

Structural:
- The stage-1 test sandbox monkeypatches module globals, but 17 script
  defaults were bound at import (`evidence_path: Path = EVIDENCE`), and its
  tripwire does not watch the store. One forgotten kwarg writes the live
  store.
- Three test modules (refresh_election, osse_pricing, gate1_closure) plus
  four phase-13 modules read the gitignored store with no skipif, so they
  ERROR on a clean clone.

### Docs / config

- PROGRESS.md "Current work" (:268-450) stops at Phase 11 "awaiting
  review" / Phase 4 "IN PROGRESS". It has no Phase 5-10/12-14 entry, and the
  CURRENT STATE banner has become the de facto index. Owner-governed, so ND.
- README: no project-structure section (global CLAUDE.md rule); the ToC
  misses Validation; last edited 07-21.
- CLAUDE.md:109 claims trailing-whitespace / end-of-file-fixer hooks that
  `.pre-commit-config.yaml` does not have.
- `docs/project-context.md:170` says "data/ ~1 GB" (it is ≈37 GB, with one
  file force-tracked).
- `pyproject.toml:108-114`: the "Claude Opus 4.7 says" comment; the
  per-module `strict = false` is likely ignored by mypy (verify).
- Classifiers claim 3.13/3.14; the recipe and pixi cap `<3.14`.
- `hygiene-priorities.md` item 38's F7 premise was wrong: the pair is not
  byte-identical (161 vs 120 lines).

### FIX NOW backlog (strictly behavior-preserving, low risk; NOT applied)

src (~21):
- Delete the dead `miost_ensemble._load_window` (:412-439, zero refs since
  the pin-133 change) and fix its sibling's docstring (:464).
- Docstring fixes:
  - `miost_crn.py:39`.
  - `miost_solver.py:196` (the npz suffix rule).
  - `miost.py:626`.
  - `eval/spectral.py:55,198`.
  - `synthetic.py:107`.
  - `phase14_seal.py:106-129` (byte-verify overstatement; a new P2-#17
    instance).
  - `gate_schema.py:36` (the stale "reports, does not refuse").
  - `phase12_config.py:109`.
  - `pertile_scoring.py:185` (Raises).
  - `ensemble_floor_null.py:210` ("inverse erf" is a bisection).
- Public-API Args/Returns: `phase13_lanes.py:179-197`, `phase14_seal.py:39`,
  `locked_tier.py:60`.
- Redundant local imports: `contract.py:208`, `screening.py:330`,
  `ensemble_settling.py:129`, `ensemble_floor_null.py:212`.
- One constant each for:
  - the proximity-deferral string (`screening.py:216/340`);
  - the "net ≥ 4" reference-epoch rule (`epoch_table.py:162` /
    `epochs.py:229`);
  - `MIN_TOTAL_YEARS` in `screening.py:156`;
  - `SWEPT_MISSIONS` in `phase13_lanes.py:117`.
- Naming: `eval/insitu.py:266`.
- Dead `.rstrip(";")`: `gauges.py:174`.

scripts (~9, live tools only — frozen runners stay records):
- `resume_checks.sh:9-13` header (it performs four checks).
- `phase14_seal_run.py:280`: parse the store once.
- `phase14_evidence_mirror.py:772`: Args.
- `phase14_sigma_diagnosis.py:124`: docstring.
- `phase14_crossenv.py:123/252`: mission tuple ×2.
- `phase14_crossenv.py:293` / `phase14_probe.py:270`: `np.load` without `with`.
- Docstring overstatements in `download_cmems_my.py:4` and
  `download_gauges.py:8`.
- `check_task_citations.py:95` (red/green).

tests (~34). Strengthening a tautology changes assertions, so do it
red/green, not as hygiene:
- Make the eviction bound bite (3+ windows or `max_resident=1`).
- Tmp-path the c2-touch provenance test.
- Add `set(items) == set(ContextKey)` (`test_evaluator_context_integrity.py:119`).
- Make the module-level RNG per-test (`test_miost_solver_checkpoint.py:23`).
- One named seal-bypass fixture for the 29 `lambda: None` stubs.
- `test_phase14_sigma_diagnosis.py:13`: a hand-rolled loader, which
  re-introduces the pattern `load_script` consolidated.
- Duplicated `_dates` / mission-catalog fixtures
  (`test_phase14_epochs.py` / `test_phase14_epoch_table.py`).
- Stale docstrings:
  - `capture_phase8_factory_bytecompat.py:8,97` (REGRESSED: `shipped_miost5`
    became the phase-13 factory).
  - `test_phase13_identity.py:230`.
  - `test_phase13_diagnostics.py:89-92`.
  - `test_phase14_epochs.py:152`.
  - `test_phase14_gate5_score_identity.py:13`.
  - `test_phase14_stage1_run.py:2080`.
- Dead fallbacks and unused params:
  - `test_phase13_diagnostics.py:34`, `test_phase13_lanes.py:96`.
  - `test_gate_stamp.py:82,96`, `test_phase14_stage1_run.py:1837,4793`.
- `os.environ` → `monkeypatch.setenv` (`test_phase14_seal.py:107`).
- `test_phase14_anchor_gate.py:583`: the skip checks the wrong file.
- Function-local re-imports (`test_phase14_stage1_run.py:1066…4636`,
  `test_gate_schema_projection_audit.py:171…222`).
- Verbatim setup ×3 (`test_miost_augmented_oracle.py:173/210/254`).

docs (~5): README structure + ToC; CLAUDE.md:109;
`project-context.md:170`; the pyproject comment; the priorities status
(done in this commit).

### NEEDS DISCUSSION (new, beyond the headline)

- `phase14_stage1_run.py` (6940 lines, 9 commands, last touched 09-19):
  freeze it as a record and give Stage 2 a new driver that imports its pure
  builders. Its 5789-line test twin → a `tests/phase14_stage1/` package.
  Blockers: the `globals()` discharge citations and the
  `Path(__file__).parents[1]` reads.
- `miost_error_basis.py:29` is the only methods→application import. It
  pulls harness, folds, xarray and input_adapter into every
  `import sverdrup.methods.miost`, and reaches the private `_GAP_SEC`.
- MIOST duplication and conventions:
  - The blake2b mission hash is duplicated (`miost.py:315` vs
    `miost_error_basis.py:78`) and feeds CRN bytes.
  - Two pass-direction conventions: `miost.py:808` uses endpoint latitude,
    `orbit_geometry.py:105` uses the median sign.
- Altimetry adapters: four re-paste the canonical-order / concat /
  ObsWindow block, and the empty-mission dtype has already drifted
  (U6/U3/U4/U4).
- Repeated definitions:
  - Two `Epoch` dataclasses (`screening.py:80`, `epochs.py:50`).
  - File-sha256 helpers: five-plus in src and six in scripts; one
    `read_bytes()`s a 1.4 GB store.
  - The locked-c2 family `{"c2","c2n"}` ×4.
  - Frame sizing ×3 in stage1_run, with two metrics (R2's
    TRUE-local-km decision lands there).
  - The store-path literal ×13, vs `phase14_seal.EVIDENCE`.
- New cross-script families:
  - F8 c2-touch ceremony ×3 (drifted).
  - F9 member-ensemble production ×3.
  - F10 script loaders ×5 (no scripts-side `load_script`).
  - F11 sha256-of-file ×6.
  - F12 storage-ledger writer ×3 (drifted).
- `miost.py:1202`: the stale `shipped_miost6` tally text (a signed-record
  docstring).
- Retention: `phase14_gauge_run`, `phase14_settling_measurement`,
  `phase10_flatten_read`, `diag_stage1_coherence` (thin-reference records).

### Intentional smells KEPT (verified deliberate — do not re-flag)

- MIOST:
  - The pin-122 broad excepts in the checkpoint/window loaders.
  - The unbounded `_eta_cache` (bounding risks re-solves; per the pin-133
    commit).
  - Importing, not copying, `_GAP_SEC` (spec §3).
  - The structured-R dims in `parameter_space` (CONSUMPTION SEAM).
  - Empty key fragments for the default `RSpec` / `BasisSpec` (cache
    lineage, test-pinned).
  - The `[bias, tilt]` interleave (documented at all three sites).
  - `WindowBackedAnoms` (pin 133).
  - `mc_error=None` at m=1.
  - The PCG `print` (spec §2.4).
- src new:
  - `frame_grid`'s verbatim `np.arange` (gate-5 identity).
  - The ladder's `Authorization.__post_init__` re-check (defense in depth).
  - The write-once `write_locked_split`.
  - dc2021a importing `load_mapping_obs`.
  - The JPL local glob (data governance).
  - The visible DEFERRED proximity row.
  - synthetic's `_EPOCH` / noise, hashed into the descriptor (NOT a P2-#12
    duplicate).
  - The sealed `INSTRUMENT_CLASS`.
- validation:
  - The `phase10_lanes` / `phase13_lanes` confusable pair (test-pinned).
  - The sealed `phase13_boxes`.
  - Three canonical-JSON encoders with different `ensure_ascii` — recorded
    digest contracts; do not unify.
  - The kind-keyed `validate_gate_schema` ("seal unspent").
  - `member_sigma`'s axis / no-nanstd choice (load-bearing).
  - The locked tier counting clean completion only (comment at :139) — the
    misfire question is an owner decision, not a smell.
- scripts:
  - The launcher constants (drift-tested).
  - The exact-float tripwires (pin 100(c)).
  - The "do NOT fix" D_int denominators.
  - `SystemExit(75/76)`.
  - `post-commit` always exits 0 (pin 102a).
  - The osse/revisit/refresh blocks carry no `date` (idempotent), and
    refresh is write-once — **the model for the recorder**.
  - `gate1_closure --write` refuses before any I/O (tested).
  - typer rejects unknown flags in all phase-14 scripts.
  - The download scripts' `.part` + atomic replace + transient-only
    stamina.
- tests:
  - The strict-xfail tripwire (262(d)/269(d)).
  - The hand-read literal pins.
  - The named data-gated skips.
  - `network_guard` catching only TransportError.
