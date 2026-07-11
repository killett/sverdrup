# Scope spec — OI validation against the 2021a SSH-mapping OSE challenge (BASELINE row)

**Status:** scope, pre-implementation. The unblocked return to the project's original
inspiration. No dependency on the autotuner (Phase 5), the GMRF coherent sampler, or anything
from the Stage-B saga.

## The claim (one falsifiable sentence)
*Our OI engine, configured from the challenge's own `baseline_oi` covariance parameters, on the
2021a Gulf Stream box (lon 285–315°E, lat 23–53°N, evaluation year 2017), mapping the
five-mission input constellation, scored by the challenge's own `src` / `example_data_eval`
code against the withheld independent Cryosat-2 along-track data, reproduces the published
leaderboard **BASELINE (OI)** row: µ(RMSE) ≈ 0.85, σ(RMSE) ≈ 0.09, λx ≈ 140 km.*

DUACS (0.88 / 0.07 / 152), MIOST (0.89), and the rest of the leaderboard sit alongside as
secondary reference points, but BASELINE is the **primary success criterion** because it is the
one whose recipe is OPEN (the `baseline_oi.ipynb` notebook, with parameters in the code). We are
reproducing an open-recipe reference implementation of the identical method — the sharpest,
most diagnostic test available.

## Grounded repo facts (verified against the live 2021a repo — do not re-derive from memory)
- Repo: github.com/ocean-data-challenges/2021a_SSH_mapping_OSE (branch `master`). Zenodo DOI
  10.5281/zenodo.5511905; data DOI 10.24400/527896/a01-2021.005. MIT licensed.
- **Domain** (from the data filenames `..._285-315_23-53.nc`): lon 285–315°E (−75 to −45°W),
  lat 23–53°N — the Gulf Stream box. This is the single-tile domain.
- **Period:** evaluation 2017-01-01 → 2017-12-31. Spin-up observations allowed from 2016-12-01
  (31 days), NOT included in evaluation.
- **Input constellation:** SARAL/AltiKa, Jason-2, Jason-3, Sentinel-3A, Haiyang-2A, Cryosat-2.
- **Withholding is DEFINED BY THE CHALLENGE:** Cryosat-2 is NOT used in the mapping; it is the
  independent evaluation track. So we map from the OTHER FIVE missions and score against the
  withheld Cryosat-2 `dt_global_c2_phy_l3_...` track. (Our own blocked-withholding machinery is
  NOT needed for this score — the held-out mission is given.)
- **Baseline is OI:** "the baseline mapping method is optimal interpolation (OI), in the spirit
  of the present-day standard for DUACS products," implemented in `notebooks/baseline_oi.ipynb`.
  Its covariance parameters are in that notebook — this is the config we read and reproduce.
- **DUACS row uses "Covariances DUACS DT2018"** — the operational AVISO production covariances,
  NOT the same as `baseline_oi`, and NOT published as a readable config. This is exactly why the
  target is BASELINE, not DUACS.
- **Comparison maps are SHIPPED** in `dc_maps/`: `OSE_ssh_mapping_BASELINE.nc`, `..._DUACS.nc`,
  `..._MIOST.nc`, etc., plus `mdt.nc`. We do not reconstruct baselines; they are provided.
- **Evaluation is two scores:** RMSE-based (µ, σ) and Fourier-wavenumber-spectrum-based (λx,
  the minimum resolved spatial scale), against the independent Cryosat-2 track. Implemented in
  `src/` and the `example_data_eval` notebook. The challenge's own `results/` dir is gitignored.

## Resolved decisions (pinned to repo facts, not open questions)
1. **Challenge:** 2021a Gulf Stream OSE (mature, frozen, leaderboard published, ~small regional
   data). NOT 2023a global (in-progress, 33GB).
2. **Deliverable:** a SINGLE OI reconstruction over 2017, scored by the challenge's own code,
   with µ(RMSE)/σ(RMSE)/λx placed beside the BASELINE and DUACS leaderboard rows.
3. **Evaluation = THEIR code is ground truth.** Their `src`/eval functions produce the REPORTED
   number, guaranteeing apples-to-apples by construction. Do NOT reimplement their metric as the
   source of truth (that reintroduces the "is my metric the same as theirs" risk this project
   has been burned by).
4. **OUR eval runs IN PARALLEL as a cross-check, not as the reported number.** Run our `eval/`
   area-weighted RMSE on the SAME map. If ours agrees with theirs → our eval layer is validated
   against the canonical one (a free, valuable side-benefit before we ever trust it for tuning).
   If it disagrees → we've learned our eval differs from canonical, which we must know. Report
   both; theirs is the headline, ours is the cross-check with the delta stated.
5. **Parameters:** read from `baseline_oi.ipynb` (open recipe) and translate into our OI
   `ParameterProvider`. The claim is a pure implementation check: same parameters, our engine.
6. **Tiling: SINGLE TILE.** The Gulf Stream box is regional; run it as one tile. No seams, no
   coherent sampler, the entire GMRF saga untouched. This is a deliberate scoping choice to keep
   the validation on the method's accuracy, not the tiling machinery.

## The work — three pieces (all harness-matching / plumbing, NOT method)
1. **Parameter extraction.** Read `baseline_oi.ipynb`: the covariance model (spatial correlation
   length scale(s), temporal correlation window, signal/noise variance, any anisotropy/lat
   dependence), the output grid spec (resolution, the 285–315 / 23–53 box, time stepping), and
   the OI neighbourhood/influence-radius settings. Translate EXACTLY into our OI config. Record
   each parameter and its source line — this is the audit trail for "same recipe."
2. **Two data adapters.**
   - INPUT: their L3 along-track NetCDF for the five mapping missions (+ the withheld Cryosat-2,
     loaded separately for evaluation) → our observation format. We have an ODC adapter pattern;
     reuse it. Honour the spin-up window (obs from 2016-12-01, not evaluated).
   - OUTPUT: our gridded OI map → their map NetCDF schema (match `OSE_ssh_mapping_BASELINE.nc`'s
     dimensions, coordinate names, variable name/units, time axis) so their eval code ingests it
     unchanged. Match their grid and land/mask conventions exactly (silent number-shifter if not).
3. **Run both evaluations.** (a) Their `src`/`example_data_eval` on our map AND on the shipped
   `OSE_ssh_mapping_BASELINE.nc` (re-derive their published number ourselves as a sanity check
   that we're driving their eval correctly) → our µ/σ/λx beside BASELINE/DUACS. (b) Our `eval/`
   area-weighted RMSE on our same map → the cross-check delta.

## Data access (see .env.example — committed; .env — gitignored)
- Preferred: AVISO+ THREDDS (OPeNDAP/FileServer over HTTPS, HTTP Basic Auth with AVISO+
  username/password). User has an AVISO+ account. THREDDS-not-FTP per request.
- Fallback A: unauthenticated MEOM-Grenoble opendap mirror (challenge README points there;
  "temporary"). Fallback B: AVISO+ FTP/SFTP.
- **FIRST TASK of the data adapter: verify the live THREDDS catalog URL and the exact auth
  mechanism (HTTP Basic header vs .netrc/.dodsrc for the OPeNDAP stack).** The base URL in
  .env.example is the standard AVISO+ THREDDS root but the per-product catalog path and auth
  detail are VERIFY-ON-CONTACT — do not trust a deep path that hasn't been confirmed to resolve.

## Success / failure criteria (falsifiable, stated up front)
- **PASS:** our OI, driven by `baseline_oi` parameters, scored by their code, lands at
  µ(RMSE) ≈ 0.85 (± a small tolerance to be set once we see the spread), σ ≈ 0.09, λx ≈ 140 km
  — i.e. reproduces the BASELINE row. AND we reproduce the published BASELINE number by running
  their eval on their shipped BASELINE map (proves we're driving their eval correctly). AND our
  parallel `eval/` agrees with theirs on the same map within a stated delta.
- **INFORMATIVE MISS (not failure of the project, a diagnosis):** if we miss, the gap is
  decomposable — (i) we reproduce their published BASELINE number from their map but our OI map
  scores differently → parameter/grid/masking mismatch (most likely, diagnosable against the
  audit trail); (ii) we can't even reproduce their published number from their own map → we're
  driving their eval wrong (harness bug); (iii) our `eval/` disagrees with theirs on the same
  map → our eval layer differs from canonical. Each points at a specific fix.
- **NON-GOAL:** beating the leaderboard, the currents/drifter score, GMRF, parameter tuning,
  multi-tile. All explicitly deferred.

## Risks (harness, not method)
- AVISO data access (account/THREDDS auth/catalog URL) — the long pole; handle FIRST.
- Their 2021-era conda env (`environment.yml`) may fight our stack → likely call their SCORING
  FUNCTIONS extracted from `src` rather than standing up their full notebook environment; our
  `eval/` can import their functions.
- Exact grid/mask/coordinate conventions must match theirs (they ship masks/aux files) or the
  number shifts silently — re-deriving their published BASELINE number from their map is the
  guard against this.
- The MEOM mirror is "temporary" — prefer authenticated AVISO+ THREDDS for durability.

## Definition of done
A committed report (and the supporting adapters/config) showing: our OI µ/σ/λx beside BASELINE
and DUACS, scored by the challenge's own code; the reproduced-published-BASELINE sanity number;
the parallel `eval/` cross-check delta; and the parameter audit trail mapping each OI setting to
its `baseline_oi.ipynb` source. PASS if we reproduce the BASELINE row; otherwise the decomposed
diagnosis above.
