# Hygiene priorities — owner review queue

Sorted disposition of everything left open by the 2026-07-16 whole-repo
hygiene audit (full detail per item: `docs/hygiene-notes.md`; the 71
behavior-preserving FIX NOW items are already applied and pushed).
Effort: S < 1 h, M = half-day, L = multi-day. Each tier states its
trigger — when the items in it actually need a decision.

## P0 — evidence-integrity hazards. Decide BEFORE any future evidence or gate rerun

These two can destroy or silently corrupt recorded evidence on a rerun.
Nothing else in this file can.

1. **Unguarded inline c2 touch** — `scripts/stage_miost_gate_run.py:801-817`.
   The env-gated touch inside `stage_b_main` runs without
   `_assert_c2_untouched` and without the pre-registered `_c2_reading`;
   the later `--c2-touch` mode has both. A second
   `SVERDRUP_MIOST_C2=1 --stage-b` run silently re-spends the one
   owner-authorized touch and overwrites the acceptance record.
   Options: (a) backport both guards into the inline path (script edit
   on a frozen runner — disclosed deviation), or (b) standing rule
   "never rerun --stage-b with the env var set" recorded in
   PROGRESS.md. Effort S either way. Recommend (a): rules rot, guards
   don't.
2. **Stage-B evidence clobber path** — `scripts/tune_miost_inflation.py:117`.
   Superseded Task-17 script writes `stage_b_{mean,var}_maps.nc` into
   the same `OUT_DIR` the gate runner uses for Stage-B evidence maps
   (which `diag_stage_b_localized_calibration.py` reads). Any rerun
   clobbers gate evidence. Options: retire the script (it is a record —
   move aside or refuse-on-run), or retarget its OUT_DIR. Effort S.

## P1 — firm bugs in live machinery. Fix soon, red/green, before the machinery is next exercised

3. **`atomic_write_json` failure path** —
   `src/sverdrup/application/calibration/harness.py:1188`. On
   `os.replace` failure after the fd is closed, the handler re-closes
   the fd: `OSError(EBADF)` masks the original error and the `.tmp`
   leaks. Every evidence writer routes through this. Happy path
   correct. Fix in src only; the verbatim copy in
   `scripts/phase8_gate_run.py:693` is a frozen record and stays.
   Effort S.
4. **Injected noise source ignored** —
   `src/sverdrup/distributions/coherent.py:215`.
   `CoherentSampler.realize_one` hardcodes `MemberSeededZr().draw_one`
   instead of `self.structured` (stored at :189). The design-5c/8
   swap seam is non-functional; latent only because default ==
   hardcoded. Fix + a seam test that injects a non-default source.
   Effort S. (Couples to P3 item 24: whether the seam stays at all.)
5. **Silent exclusion reasons lost** —
   `src/sverdrup/application/tuning/feasibility.py:149`.
   `CompositeFeasibility.explain` docstring promises a class-name
   reason for members without `explain`; code skips them, so e.g. a
   `CoherenceFeasibility` failure records `exclusion_reason=None` in
   tuning evidence. Decide doc-fix vs code-fix (code-fix changes
   recorded evidence text on FUTURE runs — pick before the next tuning
   phase). Effort S.
6. **Correlated-R silent truncation family** —
   `src/sverdrup/methods/{oi.py:124,gmrf.py:133,fem.py:193}` do
   `np.diag(obs.error_model.as_matrix(n))`: a `BandedErrorModel`
   (the swath-ready hook) would silently lose its correlations in any
   method; a dense (n,n) is materialized just to read the diagonal.
   Related: `core/observations.py:38,58` `as_matrix(n)` ignores `n`
   despite "must match" docstrings. Decide: guard (raise on
   non-diagonal R in these paths) vs an explicit diagonal-only
   contract + a size guard. Effort M. Urgency jumps the moment any
   swath/correlated-error work starts.

## P2 — silent-drift and honesty hazards. Batch opportunistically; each is small

Numeric-drift closures (the pin holds only while duplicates stay equal):

7. **Scoring numerics re-paste** — `scripts/phase8_gate_run.py:440`
   duplicates `harness.py:226-245` (`_coverage_count`/`_gaussian_crps`/
   `_var_track`). The script is frozen; the fix is a standing rule:
   future gate runners IMPORT from harness, never re-paste. Record the
   rule; no edit. Effort S.
8. **`draw_s_layout` reimplements `folds.s_fold_layout`** —
   `harness.py:546,569`. Frozen Phase-8 bit-repro machinery; only
   consolidate behind the leaf-identical harness gate. Effort M.
9. **Inline eligibility recompute** — `harness.py:1026` duplicates
   `folds._beats_beyond_band`/`_no_worse_than` semantics; band-rule
   drift would desynchronize evidence from selection. Call the helpers.
   Effort S-M.
10. **deg→km constant families** — one definition per family
    (111.195 GP/Matérn: kernel.py, gmrf_grid.py, validation/params.py,
    firstdifference.py; 111.32 MIOST/orbit/spectral: orbit_geometry.py,
    map_spectrum.py, miost_sizing.py). Dual-family split stays (it is
    intentional and test-pinned); this only closes the within-family
    drift hole. Needs a layering call on which module owns each.
    Effort S-M.
11. **`_PASS_GAP_SEC = 60.0` ×3** — harness.py:173, lane_compare.py:49,
    orbit_geometry.py:35. One pass-splitting decision, one constant.
    Effort S.
12. **Third `EPOCH` duplicate** — `harness.py:171` (found during the
    fix pass; validation copies already single-sourced in
    `validation/params.py`). Effort S.

Coverage and metadata honesty:

13. **Nonstationary-blend coverage gap** — dead C4 fixtures
    (`tests/unit/_strip_fixtures.py:137`, `_tree_gate.py:407`,
    `make_natl60(nonstationary=True)`) hide that NO blend/tree-driver
    test runs a nonstationary provider (method-level coverage exists).
    Recommend: write one blend-level nonstationary test, then delete
    the dead fixtures. Deleting without the test = knowingly ratifying
    the gap. Effort M.
14. **`captured_energy=1.0` unconditional** —
    `distributions/persisted.py:245` (+ placeholder `seed=0` at :383)
    misreports reduction quality in persisted metadata for
    rank-truncated factors. Confirm intent, then fix or document.
    Effort S.
15. **`ConvergenceReport` off-by-one** — `methods/miost_solver.py:112`.
    Telemetry only (residuals correct); fixing changes logged numbers —
    disclose when done. Effort S.
16. **`_obs_slope_1d` timestamp assumption** — `eval/fidelity.py:86`.
    Duplicate timestamps at a pass boundary would silently misalign;
    evaluator is now live (Phase 11). Index-returning `split_passes`
    variant removes the assumption. Effort S.
17. **Anchor-guard overstatement** — `scripts/phase9_g_pre_anchor.py:344`
    claims byte-identical regression check, compares parsed JSON.
    Reword the claim or strengthen the check (anchor writer — choose
    deliberately). Effort S.
18. **Stamped "all 5 mapping missions" (six listed)** —
    `scripts/generate_oi_maps.py:320,350`. Printed AND stamped into nc
    attrs; recorded artifacts stand as-is, fix the script for future
    runs and note the divergence. Effort S.
19. **RESULT.md metric misdescription** — `validation/report.py:121`
    renders "area_weighted_rmse µ" for a global unweighted
    `1 - rmse/rms`. User-facing text fix. Effort S.
20. **Three weak test escapes** —
    `test_calibrated_distribution.py:39` `_OI_MASK_ARTIFACT` gates two
    tests that never read it (spurious skips vs deliberate
    full-run signal — confirm intent);
    `test_miost_basis.py:68` overlap assert insensitive to the bug its
    docstring implies (epoch property separately pinned at :88);
    `test_tree_kriging_oracle.py:67` seed-independence test never
    invokes the driver (reword docstring or strengthen to a 2-tile
    driver assertion). Effort S each.

## P3 — design and API decisions. Park until a phase touches the area; decide in batches

Flagged first because it is owner-ordered work left dormant:

21. **`PeakFeasibility` wired nowhere** — Task-22 owner-ordered
    replacement for StoredG@8e9 pricing exists only in tests, while
    `stage_miost.py:38` docstring still recommends the superseded
    StoredG. Wire it or retire it; either way un-contradict the
    docstring. Effort S-M.

API/layering (one decision each, mechanical after):

22. `GridSpec._lonlat_nodes` — private name, 16+ external consumers
    across layers; bless as public in one repo-wide decision. (M)
23. **Phase-1 never-wired scaffolding sweep** — delete-or-keep in one
    pass: `adapters/odc/ose.py OseSource`, `download.py open_dodsC`,
    `natl60.py WINDOW/OBS_URL/REF_DAILY_URL` + unread `ODCCache`
    attribute whose constructor mkdirs on every `Natl60Source`
    build, `application/config.py RunConfig`,
    `core/observations.py Observation`,
    `core/parameters.py ResolvedParams`,
    `core/evaluation.py Objective`, `eval/calibration.py pit()`
    (likely spec-5.6-committed — check the founding spec first),
    `eval_context.py evaluator_names`, `__version__` re-export
    question. (M, mostly deletions)
24. `StructuredNoiseSource`/`MemberSeededZr.draw` seam set never
    called — wire or drop (decide together with P1 item 4). (S-M)
25. `blend.py` — `sampler_spec` from `parts[0]` with no homogeneity
    check (silent first-tile-wins vs loud-red convention) + dead
    `_sampler` field. (S-M)
26. `miost.py` `solve`/`sample_members` duplicated G/Q/R construction
    + drifted telemetry blocks; root cause `_window_obs` not returning
    mission. SIGNED SHIPPED NUMERIC PATH — only with a byte-identity
    gate. (M-L)
27. `methods gmrf/fem` — `op._factor.solve` private reach needs a
    deliberate accessor; duplicated temporal-taper-into-R block
    (extract only with leaf-identity check). (M)
28. `validation/run.py` — `run_challenge_map` vs `run_mean_var_maps`
    duplicated solve spine (byte-identical-maps gate required). (M)
29. `pipeline.py` — `_evaluate` vs `_evaluate_blended` shared spine;
    third `_subset_obs` copy materializes dense R where stage_a's
    takes the diagonal fast path (also minor perf). (M)
30. `atomic_write_json` home — generic util inside the 1232-line
    harness forces orbit_geometry→harness import + a documented cycle
    workaround; move to a util module (import churn only). (S-M)
31. Nearest-node lookup convention ×4 (`ensemble.py:54`,
    `persisted.py:250`, `coherent.py:24`, `gaussian.py:63`) — one
    convention, four copies. (M)
32. `reduction.py:175` silent `representation` default — guard or
    intent comment. (S)
33. `gmrf_grid` `.matrix` legacy hooks (test-only) — retire or bless;
    `miost_basis` never-wired seam set (`build_s`/`temporal_taper`
    factorization oracle choice, `DiagonalR` zero refs);
    `gmrf.py node_sample` docstring claims to be the coherence hook
    but coherent.py drives via `_factor_obj().sample` — wire or drop.
    (S-M each)
34. `distributions/calibration.py:750` `@dataclass` with hand-written
    `__init__` (`dataclasses.replace` would raise); `coherent.py
    _strip_network` no production caller since d960f15 —
    Stage-B-reserved or removable. (S each)
35. `derived/firstdifference.py` — protocol-undeclared `time_days`
    dependency (declare or document the narrowing); `metric_scale_x`
    carries the y-scale when `axis="y"` (consumed only by one pinned
    test). (S each)
36. Vestigial delegates and split decisions:
    `their_eval._prepare_imports` (live caller `scorer.py:198` —
    contrast with the owner-deleted harness shim);
    transient-fault predicate defined in two layers
    (`adapters/odc/download.py _is_retryable` vs
    `validation/access.py is_retryable`); stale xref
    `eval/spectral.py:56` → `their_eval._prepare_imports`. (S each)
37. `stage_a.py:137 _run_stage` — private name, cross-module API for
    stage_b/stage_miost; rename-to-public decision. (S)
38. **Cross-script extraction families** (value = future phases, ran
    runners stay frozen): F1 `_write_evidence` ×~10 (extract beside
    `harness.atomic_write_json`; carry lane_run's single-writer
    discipline note), F2 validation-track interp/scoring protocol ×8+,
    F3 atomic-JSON copies, F5 gate-runner twin helpers
    (`_stamp`/`_log`/`_counting_score`/`_scope`), F7
    `build_jet_core_mask.py` vs `build_phase8_jet_core_mask.py`
    byte-identical twin (phase8 sibling = frozen provenance record —
    retention call). (M as a batch, when the NEXT phase writes
    scripts)
39. `tests/unit/_tree_gate.py` doc-anchored dead helpers —
    `matched_chain_edge_baseline` (cited 4× in PROGRESS.md),
    `edge_seam_corr_err` (named in Stage-C design docs): keep as
    methodology record or delete with a pointer note. (S)
40. Test fixture consolidations needing care: three near-identical
    persisted-precision builders (sksparse import ordering); the
    byte-duplicated Stage-B two-window `_obs` fixture
    (`test_miost_ensemble` vs `test_diag_miost_seam_dispersion`);
    third grid-adjacency variant in `test_core_authoritative_gate`
    (subtly different semantics — not mechanically unifiable). (S-M)
41. **2023 download script contract** —
    `validation/download_ocean_data_challenges_2023.py`: all-empty
    `sha256` fields make the "skipped" branch unreachable (every rerun
    re-downloads multi-GB) and `extract_existing` reports "extracted"
    for non-archives; docstring promises SHA256 verification. Fill
    hashes (behavior change: enables skip/verify) or fix the claim.
    (S-M)

## P4 — flagged only. No action wanted; recorded so nobody re-audits them

- `ensemble.py:38` dense `np.cov` scalability landmine;
  `firstdifference.py` O(ny·nx) exact-covariance loop — correct as
  designed, will matter at the global domain.
- Frozen-script latents (owner awareness only):
  `phase8_gate_run.py:889` refusal message printed twice; :780
  tripwire-record → corrected-touch-matrix manual-surgery deadlock
  (never triggered); `phase10_probe.py:293` always-true clobber guard
  (comment names protection the code doesn't provide);
  `diag_miost_localization.py:308` `weight_sum` accumulated never
  read (dropped normalization assert — reading caveat for probe-4);
  `diag_miost_seam_dispersion.py` zero-blend-day crash + NaN-floor
  verdict on kill-switch reruns; `stage_miost_gate_run.py:1020`
  membership-based argv parsing ignores unknown flags;
  `probe_fem_reduction_exactness.py:9` "NOT committed" docstring on a
  committed file; `capture_phase9_provenance_fixture.py` one-shot
  retention.
- Everything in the "Intentional smells KEPT" section of
  `docs/hygiene-notes.md` — verified deliberate, do not re-flag.

## Suggested consumption order

P0 now (two S-effort decisions). P1 as one small TDD batch (items 3-5;
item 6 when swath work nears). P2 as a half-day drift-closure batch
before the next evidence-producing phase. P3 batched into whichever
next phase touches each area (item 21 first — it is owner-ordered work
left dangling). P4 never, unless the trigger named in the item fires.
