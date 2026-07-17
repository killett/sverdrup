# Hygiene notes

Running log of hygiene audits and smells we are intentionally keeping.
Future passes: read this before re-flagging anything.

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

### FIX NOW backlog (strictly behavior-preserving, low risk — NOT applied; needs explicit opt-in to a mutation pass)

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
