# Hygiene priorities — owner review queue

Sorted disposition of everything left open by the 2026-07-16 whole-repo
hygiene audit (full detail per item: `docs/hygiene-notes.md`; the 71
behavior-preserving FIX NOW items are already applied and pushed).
Effort: S < 1 h, M = half-day, L = multi-day. Each tier states its
trigger — when the items in it actually need a decision.

> **2026-10-18 re-audit:** per-item status of 1–41 and the NEW items 42–55
> (a P0 evidence-store write class among them) are in § "Status at
> 2026-10-18" and § "Added 2026-10-18" at the end of this file. Detail:
> `docs/hygiene-notes.md` § 2026-10-18.

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
   **RESOLVED (Phase 12, spec §5): disarmed** — the env branch in
   `stage_b_main` now refuses, naming `--c2-touch`; test
   `tests/validation/test_stage_miost_disarm.py`.
2. **Stage-B evidence clobber path** — `scripts/tune_miost_inflation.py:117`.
   **HARDENED 2026-07-22 (`56b9f24`, phase-14 Task 0):** write path refuses
   (`RuntimeError` naming P0-2) unless `SVERDRUP_ALLOW_STAGEB_EVIDENCE="1"`
   exact-string; tests `tests/test_phase14_p02_guard.py`.
   Superseded Task-17 script writes `stage_b_{mean,var}_maps.nc` into
   the same `OUT_DIR` the gate runner uses for Stage-B evidence maps
   (which `diag_stage_b_localized_calibration.py` reads). Any rerun
   clobbers gate evidence. Options: retire the script (it is a record —
   move aside or refuse-on-run), or retarget its OUT_DIR. Effort S.
   **BLOCKING PRECONDITION (pre-registered, Phase 12, spec §5):** any
   future plan invoking `tune_miost_inflation` or writing `stage_b_*`
   canonical names fixes this first. Detection covered by the
   sha-anchored external pins (loud at the next sweep).

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

## Status at 2026-10-18 (HEAD `029071f`; lines as of that commit)

1 resolved · 33 open-unchanged · 7 open-changed (better: 2, 21; worse: 10,
12, 26, 30, 38) · 0 moot. The 07-16 test tautologies (T1-T3) are all
RESOLVED (main-line commits `da401d1`, `8a46777`, `ddc377e`).

| # | status | current location / note |
|---|---|---|
| 1 | RESOLVED — the `--stage-b` rerun hole (first flush erasing the signed `c2_acceptance`) closed by item 42, `3bb69f0` | `stage_miost_gate_run.py:800`, `:816-827` |
| 2 | ✅ RESIDUAL FIXED `1e0068b` (2026-10-20; gate suite `a1098af`) — a full-scope `--stage-b` rerun over a finished block was already refused before any work (item 42); the live hole was a DEV-scope smoke, which item 42 lets through and which wrote its 12-day maps over the canonical `stage_b_{mean,var}_maps.nc`; it now writes `stage_b_dev_smoke_*`. `tune_miost_inflation` stays env-guarded, not retired | `tune_miost_inflation.py:50`; `stage_miost_gate_run.py` `stage_b_main` |
| 3 | ✅ FIXED `c92c1b5` (2026-10-19; full gate suite on `d9447ea`: 1832 passed / 21 skipped / 2 deselected (@external downloads) / 2 xfailed, 1:46:32, tree unchanged) — fdopen write + fsync + single close; unlink-only failure path | `harness.py` `atomic_write_json` |
| 4 | ✅ FIXED `0f1398a` (2026-10-19; gate suite `8fe55fe`) — `realize_one` draws z_r from the injected source | `coherent.py:215` |
| 5 | ✅ FIXED `02bb173` (2026-10-19; gate suite `8fe55fe`) — a no-explain member names itself (code-fix: changes recorded exclusion text on FUTURE tuning runs) | `feasibility.py:149-160` |
| 6 | ✅ FIXED `960b375` (2026-10-19; gate suite `8fe55fe`) — guard chosen: one accessor `core.observations.diagonal_variances` for all SEVEN vector reads of R (adds `pipeline`, `adapters`, `run`, `stage_a`); a correlated R raises NotImplementedError; both `as_matrix(n)` check n; source tripwire test | `observations.py` |
| 7 | ✅ RULE RECORDED `2180c4c` (2026-10-22; docs-only) — PROGRESS.md cross-cutting decisions: gate runners import scoring numerics from the harness, never re-paste; the three re-paste sites named. Scripts untouched (frozen records) | `phase8_gate_run.py:442`; `phase12_miost6_run.py:1068`; `phase13_c2_touch.py:280` |
| 8 | ✅ FIXED `38d0efd` (2026-10-22; gate suite `38d0efd`) — `draw_s_layout` draws through `folds.s_fold_layout(salt, seed_args)`; both Phase-8 external gates re-run green (leaf-identical fit_run evidence + field byte-exact, 2 passed in 3:22) | `harness.py`, `folds.py` |
| 9 | ✅ FIXED `bbbb215` (2026-10-19; gate suite `d26f2d8`) — `harness._lane_eligibility` calls `folds._beats_beyond_band`/`_no_worse_than`; leaf-identical + byte-exact Phase-8 gates re-run green | `harness.py` |
| 10 | ✅ PARTLY FIXED `6ed332e` (2026-10-22; gate suite `38d0efd`) — the 111.195 GP/Matérn family has one owner, `kernel.KM_PER_DEG` (`params`, `gmrf_grid`, `tiling` alias it; identity tripwire). OPEN, owner call: the 111.32 family's home (`orbit_geometry`, `map_spectrum`, `miost_sizing`; eval→methods would be a new import direction). Scripts' literals frozen. **Erratum:** that commit's body says "100 passed" for its targeted run; the run was 39 passed | `kernel.py:13` |
| 11 | ✅ FIXED `af3a390` (2026-10-19; gate suite `d26f2d8`) — `harness.PASS_GAP_SEC` public owner; `orbit_geometry._GAP_SEC` aliases it (importers untouched), `lane_compare` imports it; identity tripwire test | `harness.py`, `lane_compare.py`, `orbit_geometry.py` |
| 12 | ✅ FIXED `adccf62` (2026-10-22; gate suite `38d0efd`) — no layering change needed: `harness.EPOCH` was used in one function that already imports `validation` lazily, so the copy is gone and that function imports `params.EPOCH` the same way; `lane_compare._day_float` likewise. Behavior test (sentinel epoch) + re-paste tripwire. Script literals and the descriptor-hashed `_EPOCH` left | `harness.py`, `lane_compare.py` |
| 13 | ✅ FIXED `0892296` (2026-10-20; gate suite `0892296`) — a nonstationary provider (`LatLinearRange`, 100→800 km) now runs through the tree blend; the test catches every tile drawn from the root's factor (|log var ratio| 2.94 vs the in-test bound 1.17) that all nine prior tree tests passed; dead C4 fixtures deleted. **NOT caught (measured, recorded in the test):** the root's covariance in the kriging update | `test_tree_kriging_oracle.py`, `_tree_gate.py`, `_strip_fixtures.py` |
| 14 | ✅ FIXED `c7cf637` (2026-10-19; gate suite `d26f2d8`) — intent settled by the phase-1 design ("fraction of trace(P) captured by BBᵀ"); one helper `captured_energy_fraction` for all four writers (+ `solve._reduce_derived`, a third instance). **DISCLOSURE: future manifests report the true share where they said 1.0**; `seed=0` kept, documented inert | `persisted.py`, `solve.py` |
| 15 | ✅ FIXED `7f7866c` (2026-10-19; gate suite `8fe55fe`) — **DISCLOSURE: every converged window's recorded `iterations` reads one higher on future runs** (recorded values stand; capped-solve checks unaffected) | `miost_solver.py` |
| 16 | `fidelity.py`: NOT LIVE (analysed 2026-10-19) — `split_passes` cuts only on strictly positive gaps and both sides stable-sort the same array, so a pass's first timestamp cannot occur in the previous pass; the residual is a cross-module coupling (index-returning variant optional). The `eval/insitu.py` instance ✅ FIXED `e08642e` | `fidelity.py:88` |
| 17 | ✅ FIXED `5543fe5` (claim reworded, recorded check kept) + the `phase14_seal.verify_seal` instance `8fe55fe` (2026-10-19; gate suite `8fe55fe`) | `phase9_g_pre_anchor.py:344-349` |
| 18 | ✅ FIXED `87cf2e9` (2026-10-19; gate suite `8fe55fe`) — count derived from `MAPPING_MISSIONS`; recorded artifacts stand as stamped ("5") | `generate_oi_maps.py` |
| 19 | ✅ FIXED `6f4b2ef` (2026-10-19; gate suite `8fe55fe`); recorded RESULT.md files stand | `report.py:121` |
| 20 | ✅ FIXED `d663e00` (2026-10-19; gate suite `d26f2d8`) — basis identity test pins attributes + the exact overlap set; new driver-level per-tile seed test; OI tests gate on the field artifact they read | `test_calibrated_distribution.py`, `test_miost_basis.py`, `test_tree_kriging_oracle.py` |
| 21 | DOCSTRING FIXED `e2e8273` (2026-10-22) — `run_stage_miost` now names `PeakFeasibility` (Task 22) as the pricing predicate, `StoredGFeasibility` as the frozen runner's. OPEN: wiring `PeakFeasibility` into a src path (owner) | `feasibility.py:235`; `stage_miost.py:37` |
| 22 | OPEN — 25 sites / 16 files (+ `test_phase14_golden_tile.py:81`) | `grid.py:69` |
| 23 | OPEN — `evaluator_names` gained a test-only caller (`test_phase14_stage1_run.py:833`) | see item |
| 24 | OPEN | `coherent.py:81-117` |
| 25 | OPEN | `blend.py:104,133,233,255` |
| 26 | CHANGED (worse) — phase-13 structured-R block duplicated too; miost.py 817→1212 lines | `miost.py:672-701` vs `:865-877` |
| 27 | OPEN | `gmrf.py:130-138`; `fem.py:194-202` |
| 28 | OPEN | `run.py:208` vs `:292` |
| 29 | OPEN | `pipeline.py:256,349,314` |
| 30 | CHANGED (worse) — new src consumer `phase12_evidence.py:125`; 32 scripts reference it | `harness.py:1186` |
| 31 | OPEN | `ensemble.py:54`, `persisted.py:250`, `coherent.py:24`, `gaussian.py:63` |
| 32 | ✅ FIXED `fdf1a0b` (2026-10-22; gate suite `38d0efd`) — the guard: an operator with no `representation` raises `TypeError` naming its type (was a silent low-rank default). Protocol declaration NOT added: six structural test fakes + `adapters._DiagonalOperator` (which also lacks `posterior_mean`, so it never reduced; test-only caller) | `reduction.py:168` |
| 33 | OPEN — `build_s` edited (domain hook) though never wired | `gmrf_grid.py:173,212`; `miost_basis.py:367,519,569`; `gmrf.py:99` |
| 34 | ✅ PARTLY FIXED `66d0105` (2026-10-22; gate suite `38d0efd`) — `CalibratedDistribution.__init__` names the field `calibration`, so `dataclasses.replace` works (red first); no caller used the keyword. OPEN, owner call: `_strip_network` (tested, Stage-B-reserved) | `calibration.py:750`; `coherent.py:414` |
| 35 | ✅ FIXED `ebe0ff1` (2026-10-22; gate suite `38d0efd`) — `_DiffField.metric_scale` (was `metric_scale_x`, carrying the y scale for `axis="y"`); the `time_days` narrowing documented on `apply` | `firstdifference.py` |
| 36 | ✅ FIXED `3d634df` + `e2e8273` (2026-10-22; gate suite `38d0efd`) — one `is_retryable`, owned by `adapters/odc/download` (CLAUDE.md's reference), re-exported by `validation/access`; `_is_retryable` kept as an alias for the two scripts; identity tripwire. Disclosed: access's copy said False for status ≥600 (not an HTTP range). The `spectral.py` xref now names `validation.vendor.prepare_vendored_imports`; `their_eval._prepare_imports` left (live delegate) | `download.py`, `access.py`, `spectral.py` |
| 37 | OPEN | `stage_a.py:137` |
| 38 | CHANGED (worse) — `_write_evidence` 4 → 10+ copies, already drifted (root of 44/45). **Erratum:** F7 pair is NOT byte-identical (161 vs 120 lines) | scripts/* |
| 39 | OPEN | `_tree_gate.py:142,226` |
| 40 | OPEN — 4 new near-copies of the synthetic pass builder | `test_miost_ensemble.py:35` vs `test_diag_miost_seam_dispersion.py:36` |
| 41 | ✅ FIXED `e9c0103` (2026-10-19; gate suite `8fe55fe`) — the CLAIM fixed (hashes NOT filled: that needs a reference other than this disk) + `not-an-archive` status | `download_ocean_data_challenges_2023.py` |
| P4 argv | **RE-PRICED → P0 (item 42)** | `stage_miost_gate_run.py:1029-1041` |

## Added 2026-10-18

Trigger for the P0 block: **before ANY script that writes the evidence store
is run again** — today that is gated by pin 276(d) ("NOTHING RUNS" until the
Stage-2 plan), so the hazards are dormant, not absent. A dated backup of the
store exists (`docs/hygiene-notes.md` § 2026-10-18).

**P0 — evidence-integrity hazards**

42. ✅ **FIXED `3bb69f0` (2026-10-19; full gate suite on `946987d`: 1771 passed / 21 skipped / 2 deselected (@external downloads) / 2 xfailed, 1:31:08, tree unchanged).** **Whole-store wipe** — `stage_miost_gate_run.py:463`: a flagless,
    typo'd or `SCOPE=dev` run `write_text`s a fresh dict over the entire
    shared store (phase 8-13 unmirrored). Refuse unknown/no flags, or never
    write `RESULTS` from `main()`. (S)
43. ✅ **FIXED `9a13e1f` (2026-10-19; same suite).** **Mirror blind spots** — a deleted witnessed node reads as PENDING and
    passes (`phase14_evidence_mirror.py:719-757`); seal drift is printed,
    not failed; `SEAL` hard-coded to v1. Detect removal against the existing
    mirror; fail on seal drift. (S-M)
44. ✅ **FIXED in four parts (2026-10-19; same suite): `83fd90f` stage-1 commands, `6f1686f` settling/golden/floor/sigma, `ea5319d` phase-12/13 runners, `a5b37e3` seal v3 cap + build order — via the new `sverdrup.validation.write_once.refuse_if_recorded`. NOT guarded (recorded): the stage-1 leg writers (re-score gated by pin 190; recover-rows already append-only), anchor_gate ("deliberately NOT write-once"), kernel_pack/projection_declarations/probe tile-sizing/gauge_run (mirrored or idempotent).** **Overwrite-on-rerun class** — ~20 writers replace nodes with no
    write-once guard (seam rows → pin-45(b) firewall unrecoverable; tier2
    probe → R4's basis; settling → owner-added pin 53/54 blocks; `--stage-b`
    → signed c2_acceptance). Decide ONE src store-node recorder (seal-gated
    with the caller's path, write-once default, `--supersede --reason`,
    atomic + checked write), model `phase14_refresh_election.py:279`. (M)
45. ✅ **FIXED `68ba272` (2026-10-19; same suite).** **Seal check ignores `evidence_path`** — ~11 sites call
    `verify_current_seal()` bare against the contract at
    `phase14_seal.py:175`; 29 test stubs lock it in. Falls out of 44. (S)
46. ✅ **PARTLY FIXED `2c416e0` (2026-10-19; same suite): blank key refused, keys appended, atomic write, per-process docstring. OPEN for the owner: clean-completion-only tally vs the misfire ruling.** **Locked-tier semantics** — clean-completion-only tally vs the misfire
    ruling; `corrected_by` overwrite and `""` bypass; non-atomic store write;
    per-process flag. Before Stage 2 wires `locked_tier`. (S, owner call)

**P1 — firm bugs in live machinery**

47. ✅ **FIXED `d9447ea` (2026-10-19; same suite).** `miost_sizing.size_tile` prices RHS/workspace at signed-box `n_coef`
    (gates tier-1 eligibility, seam RAM gate). Changes recorded numbers —
    owner call. (S)
48. ✅ **FIXED `59bd9f7` (2026-10-19; same suite).** `eval/spectral.py:150` empty-PSD regression (ValueError escapes four
    tuning catch sites). Red/green. (S)
49. ✅ **FIXED `946987d` (2026-10-19; same suite).** `provenance_guard.py:25` regex passes mission-less names silently. (S)
50. ✅ **FIXED `181fdc6` (2026-10-19; gate suite `8fe55fe`) — deps declared, scikit-sparse an optional lazy extra. STILL OPEN: the `release.yml` install-smoke step (an untestable-here CI change; the owner picks what it covers).** Packaging: `scikit-sparse`, `pydantic`, `python-dotenv` imported on the
    pipeline path, declared nowhere; add an install-smoke step to
    `release.yml`. scikit-sparse's install story is the decision. (S-M)
51. ✅ **FIXED `5bb6473` (window store bound to params-key + obs digest) + `6a51ec3` (state files keep the domain; `basis_key` checked) (2026-10-19; gate suite `8fe55fe`). Residual: a LEGACY window file (no digest) from another configuration is still adopted on (m, root) — the recorded Stage-1 stores carry no digest.** MIOST window store binds only `(wid, m, root)`; `save_state` omits the
    basis domain. Latent. (S-M)

**P2 — honesty and tooling**

52. ✅ **FIXED (2026-10-19; gate suite `8fe55fe`): `31d9d0b`, `dba8f71`, `27b84a2` (every listed test, plus the audit's unpersisted p02_guard/kernel_pack items), `062db58` (17 import-bound store-path defaults now resolve at call time; the sandbox tripwire watches the live store), `54d2383` (29 store-reading tests skip on a clean clone). The gate1-closure seal-drift item was already fixed by `9a13e1f`.** ~20 new tests that cannot fail (list in hygiene-notes § 2026-10-18);
    the stage-1 test sandbox misses import-time path defaults. Red/green,
    S each.
53. ✅ **FIXED `9d495b6` (2026-10-19; gate suite `8fe55fe`) — plus install_git_hooks.sh and the post-commit hook (worktree-correct hooks dir and marker).** `resume_checks.sh` — dirty tree never exits non-zero (CLAUDE.md step 0
    says it does); origin-ahead mislabelled; `ls-remote` failure reads as
    ABSENT; `--git-dir` wrong in worktrees. Session-protocol tool. (S)
54. ✅ **FIXED `d837928` (2026-10-19; gate suite `8fe55fe` — the first run under the broadened stamp).** `phase14_gate_suite.py` attestation scope — stamps `*.py` + pyproject
    only; `verify` doesn't echo the command (pin 197c class). (S)
55. ✅ **PARTLY FIXED `ebd9c76` (2026-10-20; docs-only): README structure + ToC, CLAUDE.md:109, `project-context.md:170`. Archive SHA-erratum pointers added `2180c4c` (2026-10-22). OPEN: PROGRESS "Current work" (owner-governed).** Docs: PROGRESS "Current work" frozen at Phase 11/4 (owner-governed);
    README structure; CLAUDE.md:109; the SHA erratum not yet reflected in
    PROGRESS/archive pointers. (S)

## Fixed 2026-10-19 — the "Also latent" / validation / scripts / tooling lists

(hygiene-notes § 2026-10-18.) Every fix in this section and every
status row above that cites "gate suite `8fe55fe`" is gated by ONE full
gate suite on `8fe55fe` (all of these commits are its ancestors):
1934 passed / 21 skipped / 2 deselected (the two @external ~1 GB
downloads) / 2 xfailed, 1:22:24, tree unchanged across the run;
`verify` attests the 473-file stamp and the exact command.

| finding | commit | note |
|---|---|---|
| `contract.py:185` empty-window IndexError | `4cca25d` | |
| `gauges.py:33` cwd-relative locked split fails OPEN | `2a00e57` | split anchored to the checkout; `GAUGES_DIR` stays relative (recorded path string) |
| `eval/insitu.py` alignment + ZeroDivision | `e08642e` | flat gauge skipped; sorted-day results unchanged |
| `cmems_my.py:133` empty-manifest constant sha | `a2dee6c` | refuses missing/empty |
| `jpl_ssha.py:54` no locked-c2 exclusion | `7942ecf` | three `{"c2","c2n"}` literals remain (consolidation open) |
| `gate_schema.py:296` boolean `extrapolation_declared` | `4a93e2e` | every recorded declaration is text — no outcome moves |
| zero σ / flat interior x/0 (`seam_metrics`, `ensemble_settling`) | `acbe700` | |
| `ensemble_floor_null.py:193` unchecked weights | `e689967` | |
| lazy-npz bare `BadZipFile` (solver checkpoint, window store) | `4fc50a5` | preceded by `137bc82` (dead `_load_window` deleted) |
| `phase13_diagnostics.py:201` lexical window sort | `ed92a78` | the recorded §8.5 number (−167 pairs) stands as recorded |
| `diag_stage1_hypothesis_tests.py:552` write before STOP | `8f2b88d` | |
| `download_cmems_my.py:279` ledger only on completion | `b25aaf5` | `-PARTIAL` row on any exit |
| `download_gauges.py:127` unretried catalog, 5xx "done" | `3cd0c58` | |
| `phase14_probe.py:229` threading tolerance mis-measured | `a412998` | pairwise; recorded `determinism` node stands |
| `phase14_stage1_run`: lock pid −1 / non-O_EXCL, halt record non-atomic, seam resume ignoring m/maxiter/root | `fa4cb4a` | |
| `stage1_leg_launcher.sh` `kill -0` on zombies | `47e9e58` | |
| FIX NOW (src): stale docstrings ×4, redundant local imports ×4, dead `.rstrip` | `8fe55fe` | the remaining FIX NOW items (constants, Args, scripts, tests) stay open |

Evidence correction: `062db58`'s cited targeted tests ran before a
ruff-format rewrite of its committed bytes; re-run on the committed bytes:
346 passed, 1 xfailed (recorded in `54d2383`'s body).

## Fixed 2026-10-19 (batch 2) — P2 rows and the src/scripts FIX NOW backlog

All gated by one full gate suite on `d26f2d8` (all batch-2 commits are its ancestors): 1952 passed / 21 skipped / 2 deselected (@external downloads) / 2 xfailed, 1:12:19, tree unchanged across the run; `verify` attests the 474-file stamp and the exact command.

| item | commit | note |
|---|---|---|
| P2 #20 three weak test escapes | `d663e00` | each red shown by a reverted src mutation |
| P2 #14 `captured_energy` constant 1.0 | `c7cf637` | **manifest values change (disclosed)** |
| P2 #9 recorded eligibility re-pasted the rule | `bbbb215` | Phase-8 leaf-identical + field byte-exact gates re-run green |
| P2 #11 pass gap ×3 | `af3a390` | |
| FIX NOW src docstrings + Args/Returns (miost_crn, spectral ×2, synthetic, phase12_config, pertile_scoring, miost.sample_members, phase13_lanes ×2, phase14_seal, locked_tier) | `3e92e76` | AST identical to HEAD minus docstrings, file by file |
| FIX NOW constants ×4 (proximity string, "< 3 y", "net ≥ 4", `SWEPT_MISSIONS`) | `e193e24` | sealed `content.screening` == refactored code, checked |
| FIX NOW naming (`eval/insitu.py` rows) | `8150668` | |
| FIX NOW `phase14_seal_run check` parsed the store 4× | `5325d49` | one snapshot (pin 191 concurrency) |
| FIX NOW download re-run "verified-skipped" (cmems + gauges `stations-all`, the latter a new instance) | `31699de` | **stdout wording changes (disclosed)** |
| FIX NOW scripts: npz handles ×2, mapping-five tuple, `sync` Args, `mc_floor` section order | `12ce853` | compare-solve output byte-identical vs HEAD |
| FIX NOW `check_task_citations` dead/wrong plan fallback (+ test set literal) | `d26f2d8` | latent: all 22 trackers carry `planPath` |

**Owner attention (found 2026-10-19; NOT changed — evidence-store
governed):** `phase14_seal_run.py check` on the LIVE store exits 1. Pin 42
refuses `phase14.stage1.osse_pricing` and `phase14.stage1.refresh_election`
(2026-09-20 blocks that gate on a verdict/outcome with no reachability
declaration, after the pin-152 sweep). So the stage-1 pack's "seal `check`
PASS" attestation does not currently hold. HEAD's script and `5325d49`'s
print byte-identical output.

**Still open:** P2 #12 (layering call, row above), #13 (Effort M: a
blend-level nonstationary test must name a seam property a
stationary-ization bug would move), #7/#8/#10 (owner/layering calls); #50's
`release.yml` install-smoke step; #51's legacy-store residual; the three
`{"c2","c2n"}` literals; #55 docs; the test-side FIX NOW list
(hygiene-notes § 2026-10-18, ~30 items). *(Superseded by batch 3 below.)*

## Fixed 2026-10-20 (batch 3) — the test-side FIX NOW list, P2 #13, the c2 literals, #55 docs

All gated by one full gate suite on `0892296` (all batch-3 commits are
its ancestors): 1955 passed / 21 skipped / 2 deselected (@external
downloads) / 2 xfailed, 1:39:58, tree unchanged across the run; `verify`
attests the 475-file stamp and the exact command. The preceding suite,
on `ebd9c76` (every row below except #13): 1954 passed / 21 skipped / 2
deselected / 2 xfailed, 1:49:47, tree unchanged; 13 of its 16 warnings
were dask port collisions with a concurrent scratch probe, not code.

| item | commit | note |
|---|---|---|
| batch-2 record | `eef4ebf` | docs-only |
| test correctness: anchor-gate skip read the wrong file; `ContextKey` coverage; checkpoint module RNG; seal env leak | `f52dcae` | reds shown first (foreign-cwd run; an added enum member) |
| test tidy: sigma loader → `load_script`; lanes dead `hasattr` → literal −6.0; diagnostics dead `or`; unused `tmp_path` ×3; `verdict_audit` local imports ×4 | `17e3736` | behavior-preserving |
| stale test claims ×6 (stage-1 ladder, epochs hand check, diagnostics −11/14, identity `KIND_AUG`, gate-5 recorder, capture factory name) + unused `tmp_path` ×2 | `6a9a232` | ladder, epochs and diagnostics now asserted; ladder red shown under a reorder mutation |
| three `{"c2","c2n"}` literals | `ec6d2e4` | one `contract.LOCKED_MISSIONS`; seal content sha unchanged (read-only `_assemble`); `phase14_osse_pricing` (ruled-WAIT record) and `DRIFTING` (orbit class) left |
| #55 docs (partial) | `ebd9c76` | docs-only |
| P2 #13 nonstationary blend coverage | `0892296` | see row 13 |

Already closed before this batch (checked, not re-done): the eviction
bound, the c2-touch tmp-path, and every "tests that cannot fail" item
(row 52).

**Deferred, recorded (churn > value):** one named seal-bypass fixture
(after row 45 the "29 `lambda: None` stubs" are 36 `verify_current_seal`
patches in 4 files, mostly per-test recorders or refusals; only 3 are bare
no-op lambdas); `test_phase14_stage1_run` function-local re-imports;
`test_miost_augmented_oracle` verbatim setup ×3; the duplicated `_dates` /
catalog fixtures (`test_phase14_epochs` vs `test_phase14_epoch_table`).

**Still open — every one needs an owner or layering decision:** #12 (the
`EPOCH` import would load `validation/__init__` into harness); #7/#8/#10;
#46 (clean-completion-only tally vs the misfire ruling); #50's
`release.yml` install-smoke step; #51's legacy-store residual; #55's
PROGRESS "Current work" and SHA-erratum pointers; pyproject's per-module
`strict = false` and the 3.14 classifier vs pixi's `<3.14`; and the
owner-attention item above (`phase14_seal_run.py check` exits 1 on the
live store). *(Superseded by batch 5 below.)*

## Fixed 2026-10-20 (batch 4) — P0-2's residual and two siblings found by sweep

All gated by one full gate suite on `a1098af` (all batch-4 commits are its
ancestors): 1964 passed / 21 skipped / 2 deselected (@external
downloads) / 2 xfailed, 1:18:08, tree unchanged across the run; `verify`
attests the 476-file stamp and the exact command.

| item | commit | note |
|---|---|---|
| P0-2 residual: a DEV-scope `--stage-b` smoke wrote its 12-day maps over the canonical `stage_b_{mean,var}_maps.nc` (item 42's guard lets dev scope through on the premise it "never writes RESULTS") | `1e0068b` | dev maps → `stage_b_dev_smoke_*`; s* reads them; full scope pinned unchanged. Red: canonical file became HDF bytes |
| NEW: a `--regen-acceptance` rerun renamed the TRUE map onto `stage_miost_acceptance_tier3_regen.nc` (the one copy of the stale artifact), labelled it "NOT the scored map", and replaced the signed `acceptance_artifact_correction` with one measured against itself | `f4e2402` | `refuse_regen_rerun` before any work: `write_once.refuse_if_recorded` on the node, plus tier3-exists (crash after the rename). The live store holds both |
| NEW: a bare `generate_oi_maps.py` (full scope is the default) regenerated the signed Phase-9 `oi_{mean,var}_maps.nc` in place — non-atomic, and a clean rerun still breaks the sha phase-11 retro recorded | `a1098af` | `refuse_existing_maps` before any work in full scope; dev and audit modes unchanged. All four files exist live |

The sweep (read-only, every map/netCDF write site in `scripts/`):
`phase14_stage1_run` (member store, seam/tile maps, j3 track: written only
when absent), `phase13_lane_run` winner maps, `phase12_miost6_run` maps
and `phase13_prereg` lane-0 mean are all refused before any work by their
node guards. The rest are tempdir or unread diagnostics, and
`golden_tile` is labelled PROBE. Residual: if a crash lands between the
two map writes of a stage-1 pair, the rerun rewrites both. Both come from
the same member store, so the bytes match unless the code has changed.

**Recorded, not changed: owner call.** `phase14_anchor_gate.py run`
rewrites `anchor_{signed,member_std}_maps.nc` (`:1332-1340`) on every
re-walk, including after a GREEN. The gate-5 conflict check (`:1389`)
then compares only mu/sigma/lambda_x, and only after the maps have been
replaced. `stage1_run` reads those maps as the seamless reference. The
node is deliberately not write-once (`record_anchor_gate`: "a re-walk
after a RED records the latest reading"), so guarding the maps changes
the gate protocol. There are two options: refuse a re-walk after a
GREEN, or score a temp map and replace only on no conflict. Also noted,
outside the file class: `phase13_lane_run.main_winner_ensemble` records
dev scope under the full-scope key `phase13.miost.members`. The refusal
at `:478` blocks that once the full-scope node exists.

## Fixed 2026-10-22 (batch 5) — the clear-cut open items (owner's ask, 2026-10-21: fix what will not make things worse)

All gated by one full gate suite on `38d0efd` (all batch-5 commits are its ancestors): 1975 passed / 21 skipped / 2 deselected (@external downloads) / 2 xfailed, 1:21:45, tree unchanged across the run; `verify` attests the 481-file stamp and the exact command.

| item | commit | note |
|---|---|---|
| pyproject: no-op per-module `strict = false` dropped (mypy acts on the key only when true); 3.14 classifier dropped (pixi + recipe cap `<3.14`; env 3.13.14) | `cfc9d80` | config-only; `mypy .` identical before/after |
| #36 vendor xref + #21 pricing-predicate docstring | `e2e8273` | docs-only |
| #36 one `is_retryable` | `3d634df` | identity tripwire; `_is_retryable` alias for 2 scripts; CLAUDE.md pointer |
| #10 GP family 111.195 → `kernel.KM_PER_DEG` | `6ed332e` | identity tripwire. **Body erratum: "100 passed" was 39 passed** |
| #12 EPOCH: lazy imports from `validation.params` | `adccf62` | sentinel-epoch behavior test + re-paste tripwire |
| #32 `select_reduction` representation guard | `fdf1a0b` | red first; protocol declaration deferred (6 fakes + the diagonal adapter) |
| #34 dataclass `replace` on `CalibratedDistribution` | `66d0105` | red first; keyword `cal=` unused by all 35 sites |
| #35 `_DiffField.metric_scale` | `ebe0ff1` | rename on a private class + docstrings |
| #7 rule + #55 archive pointers | `2180c4c` | docs-only |
| #8 `draw_s_layout` → `folds.s_fold_layout` | `38d0efd` | Phase-8 external gates re-run green: leaf-identical + byte-exact, 2 passed in 3:22 |

Process notes, recorded so the next pass does not repeat them: the mypy
hook checks untracked tests, so a red test for a not-yet-applied item
blocks an unrelated commit (park it in the scratchpad meanwhile); the tool
shell does not honour `set -e`, chain with `&&`; a trailing `&`
backgrounds a whole `&&` chain (this launched a duplicate gate suite on
`38d0efd`, both killed; the resulting `mv` lost the raw log of the
`a1098af` suite, whose result stands as verified and recorded in batch 4);
`pkill -f` / `pgrep -f` self-match the tool shell — use `patter[n]` forms
and never put the launch line in the same call.

**Still open — one decision each (recommendations in the 2026-10-22
session report):** #10's 111.32 family owner; #30 `atomic_write_json`
home (moving it alone leaves the documented cycle: `orbit_geometry` also
imports `PASS_GAP_SEC`); #22 bless `_lonlat_nodes` public (25 sites);
#37 / #39 / #34b `_strip_network` (recommend leave); #23 and the
numeric-path refactors #24–29, #31, #33, #38, #40 (leave); #21 wiring
`PeakFeasibility`; #46, #50, #51, the anchor-gate map rewrite, the live
seal-check FAIL, PROGRESS "Current work".
