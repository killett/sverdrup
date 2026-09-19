# Phase 14 — GATE 1 pack (Stage 1: spatial transfer, 2017) — HELD for the owner's walk

**Posted 2026-09-18 by T9 and STOPPED (owner pin 208).** Gate 1 is the owner's. **This pack
presents Stage 1; it does not close it** — the C1→2 line **C-11 is OUTSTANDING** and its
producer is **task 23**, behind this gate (208d, pin 136c). Nothing is sealed; the single
authorised supersession is unspent; `phase14.stage1.refresh_election` is registered and
unwritten by design (pin 193); tasks 18–20 are halted under pin 88; **T6, T7 and T8 are
UNOPENED**, and items (4)–(6) below present them as such, which is the honest state.

**How every number here is read.**
- Every figure quotes **the populated store field by name** (pin 202c). The χ² everywhere
  is `scores.chi2_j3_validation`; `scores.reduced_chi2` is null in all four tile rows.
- Store = `data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json` under
  `phase14.stage1` (`S`); mirror `docs/validation/evidence-mirror/phase14-stage1-provenance.json`
  at **45 witnessed nodes**; ruling doc `docs/superpowers/2026-07-27-owner-ruling-crn-sigma-rule0.md`
  (`R`); assembled view `docs/validation/phase14-stage1-assembled-view.md` (pin 198).
- **Vocabulary (review pin 21):** "Rule 0" names ONLY the floor-probe attributability rule;
  the T0 residual check is always "the solve-validity guard".
- **The attribution readout has not ruled.** The transfer-reading section carries numbers,
  caveats and the ruled three-class structure — and **no cross-lineage interpretation**
  (208a). It is ASSEMBLED from recorded row fields by `phase14_stage1_run.py
  render-transfer-readings`, which has no free-text parameter, and the absence check ran
  over this rendered file before posting (review pin 17; output in §2.4).

---

## 1 · Owner attention items

### 1.1 — (1) The anchor gate's RULED ACCOUNTING — never "five green" (pin 97b)

`S anchor_gate.accounting.statement`, verbatim: *"TWO checks run and passed (1, 5), TWO
cited and pre-ratified at Gate 0 (2, 4), ONE proxy-passed with the specified check deferred
(3). This accounting survives careful reading in Stage 2; 'five green' does not."*

| check | disposition | field |
|---|---|---|
| 1 tiling_identity | **run and passed** | `checks.tiling_identity.pass = true` |
| 2 loader_identity | cited and pre-ratified at Gate 0 | `checks.loader_identity.pass = true` |
| 3 surface_identity / era_noop | surface **proxy-passed**; **era no-op DEFERRED** to the stage that introduces era-keyed code (Stage 2, spec §3.1 fork E) | `checks.surface_identity.pass = true`; `checks.era_noop.pass = null`, `status = "deferred"` |
| 4 cross_env | cited and pre-ratified at Gate 0; **cross-host slot `pending-T18`** — and **T18 is a Stage-2 task (pin 86c)** | `checks.cross_env.cross_host = "pending-T18"`, same-host CRN-EQUAL recomputed |
| 5 score_identity | **run and passed** | `checks.score_identity.pass = true` |

The discharge is the code, not this table: `scripts/phase14_anchor_gate.py`, the `ACCOUNTING`
block (lines 166–178 at this commit), whose own words are that *"'five green' does not"*
survive careful reading in Stage 2. `anchor_gate.pass = true` is the machine field; the
accounting above is how the owner ruled it read (2026-07-26).

Anchor identity subject (not a transfer reading — pin 97a): `S gate5` µ **0.769459**, σ
**0.284818**, λx **174.521 km**, n **46,780**, lineage *compute_stats (vendored area-binned;
gate-0 deviation note)*, map sha `6955afb8…`. Leg: n_obs 54,345, wall 22,352 s, peak 3,512 MiB.

### 1.2 — (11) CHECK-1 PROVENANCE (pin 61 — 58(d)'s result, in the pack, in this order)

1. **THE GAP.** Three of check-1's four routes recorded the comparison OUTCOME but not what
   they compared against: `mean_vs_acceptance` and `variance` recorded the reference PATH
   and `bit_identical: true` but **no sha**; `gamma_route` recorded **neither path nor sha**
   while comparing against the same `phase13_winner_mean.nc`. **A substituted reference
   would have re-passed.** `member_sha` (both sides, 9/9 windows), `obs_identity` and
   `reference_store` were already sound. Why it is a gate-level item: **check 1 is the
   stage's foundation and checks 2 and 4 are discharged by citation on top of it.**
   [S `anchor_gate_artifact_shas.finding`, witnessed]
2. **THE TWO FIXES.** Shas captured at `S anchor_gate_artifact_shas` (`phase13_winner_mean.nc`
   `8f7068c3…`, `phase13_winner_var.nc` `17fa8561…`, `phase13_lane0_mean.nc` `cdf9076d…`);
   `phase14_anchor_gate.py` now writes `reference_sha256` inline on the mean, Gamma and
   variance routes, so T14's check-1 re-run is self-witnessing.
3. **THE CAPTURE CAVEAT AND ITS RECONCILIATION.** The capture was 2026-07-28, after the
   2026-07-26 gate run. Pin 60(a)'s reconciliation [S `anchor_gate_artifact_sha_reconciliation`]:
   **"2 of 3 intervals CLOSED by exact match; 1 SEARCHED AND ABSENT"** — closed for
   `phase13_winner_mean.nc` and `phase13_winner_var.nc` against phase 13's own contemporaneous
   shas; **`phase13_lane0_mean.nc` stays OPEN** (searched and absent; the 2026-07-28 capture
   closes future substitution only; materiality lower — it is cited by gate5's scope note and
   the golden-tile µ-scale check, not by check 1's bit-identity routes). All three outcomes
   stated; not only the closed ones.

### 1.3 — (2) The seam result in its RULED SHAPE (pins 97c, 37)

**Stage 1 has NO attributable σ-route seam verdict. The σ seam question is UNANSWERED, not
answered clean** (37a). The two mean-route CLEAN cells are the stage's only standing seam
verdicts. [S `seam_rows`, 4 rows; `sigma_rows_not_established.consequence`]

| route | field | `r_seam` | `d_int` | floor attributable | **verdict** |
|---|---|---|---|---|---|
| pair (A−B pre-blend, rubric) | mean | 0.082738 | 0.086491 | yes (f_m 1.64e-6, threshold 4.91e-6) | **CLEAN** |
| pair | σ | 1.104435 | 0.003265 | — | **NOT_ESTABLISHED** (ensemble MC artifact — see diagnosis) |
| ORACLE (blended vs seamless anchor) | mean | 0.098103 | 0.094466 | yes (f_m 1.37e-6, threshold 4.12e-6) | **CLEAN** |
| ORACLE | σ | 0.648763 | 0.003225 | — | **NOT_ESTABLISHED** (ensemble MC artifact — see diagnosis) |

- **Geometry sentence (every row carries it):** *10×5 halves inside the anchor footprint —
  NOT D1 production geometry (15×15).* And the row's own `non_transfer_note`: this is not a
  production-geometry seam reading; the feasibility-frontier watch item (worst-seam grew
  with TILE COUNT) sits on the far side of that gap. ORACLE: *no published precedent —
  gap-register (T11)*.
- **The diagnosis** the σ cells cite: `S seam_sigma_diagnosis`, confirmed on four lines
  (magnitude — RMS(σ_n − σ_s) = 0.003607 m matches the two-independent-estimate MC floor
  0.003708 m to 2.7%; one-sidedness; localisation; half-split). Withheld at
  `sigma_rows_not_established` (pin 45b); prior verdicts preserved there, not current.
- ⛔ **FIREWALL (37b, 208b):** the diagnosis-derived bound is a bound under the
  not_established firewall, **not a verdict**, and **it is not reproduced anywhere in this
  pack.** No rubric verdict supports it.
- Floor probe (Rule 0): pair roster re-solved deeper at rtol 1e-9, maxiter 2200 (production
  1200), converged 629/679 iterations, `capped = false`.

### 1.4 — (3) FOUR transfer readings — one per diverse tile (pin 97a), ASSEMBLED

**Count: four, test-pinned against the store** (`seam_n`/`seam_s` carry no `scores`, no
`reference_row`, no `bridge_caveat` — solve records, not readings; the anchor is the
identity subject). The section between the markers is machine-rendered from row fields.

<!-- TRANSFER-READINGS: BEGIN -->

### kuroshio — recorded 2026-09-02 (`phase14.stage1.tiles.kuroshio`, source `cmems_my`)

| field | value |
|---|---|
| `frame.core` [lon0, lon1, lat0, lat1] | [132.0, 147.0, 28.0, 43.0] |
| `n_obs` / `m` / windows | 138,518 / 100 / 9 x 60.0 d |
| `scores.lambda_x` | **232.5339 km** |
| `scores.mu.value` [m] | 0.28595412 |
| `scores.sigma.value` [m] | 0.21861301 |
| `scores.coverage_1sigma.value` (n) | 0.00977815 (89,383) |
| `scores.chi2_j3_validation.value` — `gates: false`; `scores.reduced_chi2` = null | 416.6777 |
| `scores.n_scored_points` | 89,383 |
| `scores.raw_sigma.value` — REFERENCE-ONLY, NOT CALIBRATED | 0.03818712 |
| `scores.scalar_s_star.value` — REFERENCE-ONLY, NOT CALIBRATED; `s_star_chi2_identity.same_by_construction` = true | 416.6777 |
| `reference_row` | raw-sigma + scalar-s* transfer — REFERENCE-ONLY, NOT CALIBRATED |
| `convergence` / `scores.capped_measurement` / PCG worst iterations | CONVERGED / false / 505 |
| `wall_s` | 70811.32 s (19.67 h) |
| `peak_rss_mib` | 7389.34 — **PRE-133 — recorded before pin 133's retention fix (4,259 + 8 x 391.2 = 7,389 reproduces it from the retention slope); NOT comparable to the post-fix legs (owner pin 199b)** |
| `headroom` | no `headroom` key — the record is `phase14.stage1.headroom_minima_recovered` |
| `scores.track.sha256` | `20e9c76287fbc672384a66f069746fc6d3035bde13b26fe7872db39f39dd1828` |

**`bridge_caveat` (verbatim):** cross-lineage reading; golden-tile bridge delta MEASURED ON THE ANCHOR BOX (mu -0.012457 their_eval-scale, map RMS 4.10 cm); its magnitude at THIS tile is unmeasured; interpretation WAITS on the owner attribution readout

**`sigma_caveat` (verbatim):** per-tile sigma level under THIS tile's own CRN origin; the deferred CRN production defect (phase14.stage1.crn_production_defect_deferred) is a property of the SHIPPED SYSTEM, not of an instrument; cross-tile sigma comparison is NOT supported and the boundary gradient is DEFERRED and unmeasured; the within-tile sigma level is NOT compromised - the four diverse tiles are pairwise disjoint and only seam_n/seam_s are adjacent

**Instrument composition (`report_rows.kuroshio.2017`): INCOMPLETE — the instrument composition policy (b) pins is NOT satisfied at this tile (owner pin 106c). A REAL WEAKENING of the deliverable, accepted because absence honestly recorded beats geometry that does not belong to the tile, not because the gap is small (106e).** Recorded absences: `calibration` ABSENT (missing WITHHELD_OBS); `skill` ABSENT (missing WITHHELD_OBS); `groundtrack` ABSENT (missing ORBIT_GEOMETRY); `insitu_gauges` ABSENT (missing INSITU_GAUGES). Wedge exclusion: DESIGN CONFLICT (pin 106).

### southern — recorded 2026-09-04 (`phase14.stage1.tiles.southern`, source `cmems_my`)

| field | value |
|---|---|
| `frame.core` [lon0, lon1, lat0, lat1] | [215.0, 230.0, -62.0, -47.0] |
| `n_obs` / `m` / windows | 175,059 / 100 / 9 x 60.0 d |
| `scores.lambda_x` | **141.9472 km** |
| `scores.mu.value` [m] | -0.61762861 |
| `scores.sigma.value` [m] | 0.13772269 |
| `scores.coverage_1sigma.value` (n) | 0.00258066 (137,174) |
| `scores.chi2_j3_validation.value` — `gates: false`; `scores.reduced_chi2` = null | 1637.4844 |
| `scores.n_scored_points` | 137,174 |
| `scores.raw_sigma.value` — REFERENCE-ONLY, NOT CALIBRATED | 0.03496572 |
| `scores.scalar_s_star.value` — REFERENCE-ONLY, NOT CALIBRATED; `s_star_chi2_identity.same_by_construction` = true | 1637.4844 |
| `reference_row` | raw-sigma + scalar-s* transfer — REFERENCE-ONLY, NOT CALIBRATED |
| `convergence` / `scores.capped_measurement` / PCG worst iterations | CONVERGED / false / 626 |
| `wall_s` | 98929.75 s (27.48 h) |
| `peak_rss_mib` | 4951.16 |
| `headroom` | no `headroom` key — the record is `phase14.stage1.headroom_minima_recovered` |
| `scores.track.sha256` | `76ea059873c378d2b78b709f30e46759a254f6917ffc2093af5d964431d6b171` |

**`bridge_caveat` (verbatim):** cross-lineage reading; golden-tile bridge delta MEASURED ON THE ANCHOR BOX (mu -0.012457 their_eval-scale, map RMS 4.10 cm); its magnitude at THIS tile is unmeasured; interpretation WAITS on the owner attribution readout

**`sigma_caveat` (verbatim):** per-tile sigma level under THIS tile's own CRN origin; the deferred CRN production defect (phase14.stage1.crn_production_defect_deferred) is a property of the SHIPPED SYSTEM, not of an instrument; cross-tile sigma comparison is NOT supported and the boundary gradient is DEFERRED and unmeasured; the within-tile sigma level is NOT compromised - the four diverse tiles are pairwise disjoint and only seam_n/seam_s are adjacent

**Instrument composition (`report_rows.southern.2017`): INCOMPLETE — the instrument composition policy (b) pins is NOT satisfied at this tile (owner pin 106c). A REAL WEAKENING of the deliverable, accepted because absence honestly recorded beats geometry that does not belong to the tile, not because the gap is small (106e).** Recorded absences: `calibration` ABSENT (missing WITHHELD_OBS); `skill` ABSENT (missing WITHHELD_OBS); `groundtrack` ABSENT (missing ORBIT_GEOMETRY); `insitu_gauges` ABSENT (missing INSITU_GAUGES). Wedge exclusion: DESIGN CONFLICT (pin 106).

### equatorial — recorded 2026-09-10 (`phase14.stage1.tiles.equatorial`, source `cmems_my`)

| field | value |
|---|---|
| `frame.core` [lon0, lon1, lat0, lat1] | [200.0, 215.0, -4.0, 11.0] |
| `n_obs` / `m` / windows | 167,579 / 100 / 9 x 60.0 d |
| `scores.lambda_x` | **RECORDED ABSENT** (`recorded_absent: true`, pins 160a/161 — the map resolves no scale; not a scoring failure and not a value of zero): coherence max 0.0030273, min -4.169038; `psd_diff_over_ref_median` 1.0004656; n_wavenumbers 79; band 12.77–996.34 km |
| `scores.mu.value` [m] | 0.76578991 |
| `scores.sigma.value` [m] | 0.05942276 |
| `scores.coverage_1sigma.value` (n) | 0.03263243 (100,299) |
| `scores.chi2_j3_validation.value` — `gates: false`; `scores.reduced_chi2` = null | 40.3115 |
| `scores.n_scored_points` | 100,299 |
| `scores.raw_sigma.value` — REFERENCE-ONLY, NOT CALIBRATED | 0.03798931 |
| `scores.scalar_s_star.value` — REFERENCE-ONLY, NOT CALIBRATED; `s_star_chi2_identity.same_by_construction` = true | 40.3115 |
| `reference_row` | raw-sigma + scalar-s* transfer — REFERENCE-ONLY, NOT CALIBRATED |
| `convergence` / `scores.capped_measurement` / PCG worst iterations | CONVERGED / false / 579 |
| `wall_s` | 91945.00 s (25.54 h) |
| `peak_rss_mib` | 4817.00 |
| `headroom` | present — `min_mem_available_mib` 3468.000000 (BACKFILLED) |
| `scores.track.sha256` | `987b7513f89777f2df64ea48736c2fb72e0751904dede41d8410028b1ebb4a37` |

**`bridge_caveat` (verbatim):** cross-lineage reading; golden-tile bridge delta MEASURED ON THE ANCHOR BOX (mu -0.012457 their_eval-scale, map RMS 4.10 cm); its magnitude at THIS tile is unmeasured; interpretation WAITS on the owner attribution readout

**`sigma_caveat` (verbatim):** per-tile sigma level under THIS tile's own CRN origin; the deferred CRN production defect (phase14.stage1.crn_production_defect_deferred) is a property of the SHIPPED SYSTEM, not of an instrument; cross-tile sigma comparison is NOT supported and the boundary gradient is DEFERRED and unmeasured; the within-tile sigma level is NOT compromised - the four diverse tiles are pairwise disjoint and only seam_n/seam_s are adjacent

**Instrument composition (`report_rows.equatorial.2017`): INCOMPLETE — the instrument composition policy (b) pins is NOT satisfied at this tile (owner pin 106c). A REAL WEAKENING of the deliverable, accepted because absence honestly recorded beats geometry that does not belong to the tile, not because the gap is small (106e).** Recorded absences: `calibration` ABSENT (missing WITHHELD_OBS); `skill` ABSENT (missing WITHHELD_OBS); `groundtrack` ABSENT (missing ORBIT_GEOMETRY); `insitu_gauges` ABSENT (missing INSITU_GAUGES). Wedge exclusion: DESIGN CONFLICT (pin 106).

### quiet_gyre — recorded 2026-09-08 (`phase14.stage1.tiles.quiet_gyre`, source `cmems_my`)

| field | value |
|---|---|
| `frame.core` [lon0, lon1, lat0, lat1] | [255.0, 270.0, -30.0, -15.0] |
| `n_obs` / `m` / windows | 168,755 / 100 / 9 x 60.0 d |
| `scores.lambda_x` | **RECORDED ABSENT** (`recorded_absent: true`, pins 160a/161 — the map resolves no scale; not a scoring failure and not a value of zero): coherence max 0.0026273, min -18.210680; `psd_diff_over_ref_median` 1.0005387; n_wavenumbers 79; band 12.77–996.34 km |
| `scores.mu.value` [m] | 0.84793330 |
| `scores.sigma.value` [m] | 0.06257645 |
| `scores.coverage_1sigma.value` (n) | 0.16666988 (103,786) |
| `scores.chi2_j3_validation.value` — `gates: false`; `scores.reduced_chi2` = null | 11.6379 |
| `scores.n_scored_points` | 103,786 |
| `scores.raw_sigma.value` — REFERENCE-ONLY, NOT CALIBRATED | 0.03772121 |
| `scores.scalar_s_star.value` — REFERENCE-ONLY, NOT CALIBRATED; `s_star_chi2_identity.same_by_construction` = true | 11.6379 |
| `reference_row` | raw-sigma + scalar-s* transfer — REFERENCE-ONLY, NOT CALIBRATED |
| `convergence` / `scores.capped_measurement` / PCG worst iterations | CONVERGED / false / 611 |
| `wall_s` | 93712.97 s (26.03 h) |
| `peak_rss_mib` | 4986.42 |
| `headroom` | no `headroom` key — the record is `phase14.stage1.headroom_minima_recovered` |
| `scores.track.sha256` | `721334f87340a684659ef695f1d383ee4f50cf836a3fbb2a29de4d325ef9395b` |

**`bridge_caveat` (verbatim):** cross-lineage reading; golden-tile bridge delta MEASURED ON THE ANCHOR BOX (mu -0.012457 their_eval-scale, map RMS 4.10 cm); its magnitude at THIS tile is unmeasured; interpretation WAITS on the owner attribution readout

**`sigma_caveat` (verbatim):** per-tile sigma level under THIS tile's own CRN origin; the deferred CRN production defect (phase14.stage1.crn_production_defect_deferred) is a property of the SHIPPED SYSTEM, not of an instrument; cross-tile sigma comparison is NOT supported and the boundary gradient is DEFERRED and unmeasured; the within-tile sigma level is NOT compromised - the four diverse tiles are pairwise disjoint and only seam_n/seam_s are adjacent

**Instrument composition (`report_rows.quiet_gyre.2017`): INCOMPLETE — the instrument composition policy (b) pins is NOT satisfied at this tile (owner pin 106c). A REAL WEAKENING of the deliverable, accepted because absence honestly recorded beats geometry that does not belong to the tile, not because the gap is small (106e).** Recorded absences: `calibration` ABSENT (missing WITHHELD_OBS); `skill` ABSENT (missing WITHHELD_OBS); `groundtrack` ABSENT (missing ORBIT_GEOMETRY); `insitu_gauges` ABSENT (missing INSITU_GAUGES). Wedge exclusion: DESIGN CONFLICT (pin 106).

<!-- TRANSFER-READINGS: END -->

### 1.5 — The RULED reading of (3), recorded after the numbers (pins 185, 186, 196, 199, 204, 205, 206)

- **A transfer finding, not four readings of which two failed (186a), in THREE classes
  (196b/e):** kuroshio **well-matched** (resolves, 232.53 km); southern **UNDER-powered** at
  500–1000 km (`study/ref` 0.084, `diff/ref` 0.988) yet correctly phased with real skill at
  150–300 km (resolves, 141.95 km); equatorial and quiet gyre **OVER-powered** at long
  scales, phase collapsing (absences recorded). *"Resolves versus does not" is too coarse a
  summary of what Stage 1 measured.* Southern is under-powered exactly where the two
  absences are over-powered — the sharpest structural contrast the stage produced; **evidence
  about the mechanism, not a caveat on a row.** The band tables behind this are a recorded,
  mirrored measurement: `S band_spectra` = `docs/validation/phase14-stage1-band-tables.json`
  (pins 201/205); **every ruling-quoted figure reproduces exactly**, `SKILL_BANDS` is the
  canonical grid (205c), and southern's 500–1000 figures came from an ad-hoc cut that no
  committed code produced until then (205b, recorded as a finding).
- **The defect branch is CLOSED on evidence, not exhaustion (185), for four reasons:** the
  pattern is universal in kind and orderly in degree; coefficients are ordinary at every rung;
  PCG converged `capped = false` on all four; the split sorts on signal strength across a
  6.3× spread in *f*. Misalignment, sign or reference errors do not sort by regime.
- **The mechanism is OPEN and FIREWALLED (186b).** Long-scale dominance + weak signal is the
  surviving account and is **not established**: both predictors weakened with the fourth tile
  (absolute band variance −0.464 → −0.254; |f| −0.322 → −0.121, n = 28, reproduced at 205),
  so the effect is at **tile** level, not band level. **The geostrophic account is REFUTED**
  (187a): quiet gyre has healthy *f* (0.66× kuroshio) and failed. The bias/reference-offset
  reading (196c) is **firewalled — recorded, not established**. *f* is not the discriminator.
- **Composition INCOMPLETE at all four diverse tiles (106c/e)** — stated in the assembled
  section beside the numbers, and here: `groundtrack` (the reference-free family's founding
  member, the 0.410→0.331 lineage) is ABSENT at every diverse tile because the only
  orbit-geometry provider is challenge-box scoped. **A REAL WEAKENING of the deliverable**,
  accepted because absence honestly recorded beats geometry that does not belong to the tile
  — not because the gap is small. **The design conflict (106b) Stage 2 inherits:**
  "GroundTrack per tile×era" and "zero new surfaces" are incompatible while the provider is
  challenge-box scoped. Wedge exclusion is IN SCOPE at anchor/seam_n/seam_s and a DESIGN
  CONFLICT at all four diverse tiles — **exactly as pin 112(c) predicted, and the store
  records it in-row** (202e).
- **Kuroshio's peak RSS 7,389 MiB is PRE-133 and not comparable to the post-fix basis
  (199b).** The launch gate is 1.986× the worst post-fix peak (4,986 MiB). Row `peak_rss_mib`
  and the heartbeat `peak_rss` are **one kernel high-water mark through two interfaces** —
  self-consistency, not corroboration — accepted as sufficient because a high-water mark is
  not derived, is monotone non-decreasing, and errs conservatively for a threshold (204).
- **Headroom: both routes of the re-score hazard are now CLOSED (206d).** Pin 190 guards
  the row's cost fields; pin 206(c) gives a re-score its own log directory. The equatorial
  row's `sampler_log` shas describe leg + re-score; the leg-only figures are at
  `S equatorial_sampler_log_scope` (forward-pointer from the row, pin 64) and the minima are
  unaffected. **The single headroom record is `S headroom_minima_recovered`**, qualified by
  `headroom_leg1_floor_unrecoverable` (leg 1's 3,660 MiB is an upper bound, not a value).

### 1.6 — (4) High-latitude kernel decision pack — **UNOPENED** (T6)

Decision cell: **EMPTY.** T6 is unopened; rows 7–9 of the stale-criteria sweep are
**RULED BUT UNFOLDED** and fold inside it when it opens (pin 124c). Its anisotropy axis is
**UNEVIDENCED** (pin 108) — any kernel option resting on directional sampling is a WAIT that
comes to the owner. The C1→2 lines C-04/C-05 are covered as a decision *pack*; the decision
is the owner's.

### 1.7 — (5) Revisit verdict rows — **UNOPENED** (T7)

No rows. T7 is unopened; presented as such.

### 1.8 — (6) OSSE run decision — **UNOPENED** (T8)

Decision cell: **EMPTY.** T8 is unopened; presented as such.

### 1.9 — (7) Six-mission-refresh election — PRESENTED, decision cell EMPTY

**Presumptive rule, verbatim as recorded** (spec 2026-07-21 §1-8): *instrument-class match,
δ_j3 := δ_j2n (Poseidon-series); own chain + touch if elected; scope = Stage-2G assembly runs
onward.*

| decision | scope if elected | consequence if elected |
|---|---|---|
| **(empty — the owner's)** | Stage-2G assembly runs onward | own chain + touch (never a silent fold-in) |

⚖ **This item states its own limit (136b):** presenting the rule with an empty decision cell
does **not** discharge the C1→2 line *"the Gate-1 shipped-config election OUTCOME with its
scope"*. **The outcome's producer is task 23**, after this gate; **a decline is an outcome**
and is recorded the same way. **C-11 is OUTSTANDING and Stage 1 does not close while it is
(136c).**

### 1.10 — (8) Spend actuals vs Tier-0/1

Stage 1 ran entirely on the owner's box: **$0 cloud spend**, as expected. The four Tier-2
legs (19.67 / 27.48 / 25.54 / 26.03 h) ran under the pin-155 launch gate and the pin-156
watchdog on that box; no Tier-2 cloud ceiling was reached or used. **WAIT rows:** none open
in Stage 1. The cross-host slot (`pending-T18`, credentials owner-side) is **Stage-2 work
(pin 86c)**, not a Stage-1 wait.

### 1.11 — (9) Discipline attestation (pin 124a wording, verbatim)

- **"zero locked opens, one deferred production defect named at
  `crn_production_defect_deferred`"** — `S c2_touch_tally` reads touch 1 (Stage-A winner
  acceptance, signed 2026-07-06), touch 2 (Stage-B defect run, spent, disclosed, no
  selection), touch 3 **PENDING fresh owner authorization**; Stage 1 opened none.
- **Tally byte-identical:** `c2_touch_tally` is a witnessed mirror node; `phase14_evidence_mirror.py
  check` → *store vs mirror: PASS (no witnessed node has changed)* (§2.2).
- **±66° respected under the ruled convention:** every diverse tile's solve bbox lies inside
  it — southern's is the widest at −64…−45; kuroshio 26…45; equatorial −6…13; quiet gyre
  −32…−13 (`S tiles.<tile>.frame.solve_bbox`).
- **Seal `check` PASS:** `phase14_seal_run.py check` re-derives
  `phase14_evaluation_seal_v1.json` sha `a17ea419…` (§2.2); the 9 uncited prior-phase gates
  print as NOTED (pin 145b), non-fatal, not reopened.

### 1.12 — (10) The two coverage tables, side by side (pin 137)

- **T11 — sealed-instrument coverage:** `docs/superpowers/2026-07-25-phase14-stage1-instrument-coverage.md`.
  Five findings (1 CRITICAL — the rubric's primary pair read assigned to no task, since
  remedied by T4's pair-read AC and produced above; 2 HIGH — ORACLE denominator; 3 MEDIUM —
  recording-schema conformance; 4 LOW-MEDIUM — one owner sentence; 5 LOW — no action).
- **T12 — C1→2 contract coverage:** `docs/superpowers/2026-08-31-phase14-stage1-c1to2-coverage.md`.
  Forward table status as of this pack:

| line | deliverable | status |
|---|---|---|
| C-01 | tiling machinery | COVERED |
| C-02 | seam — ORACLE | COVERED and produced: mean R = 0.098103 CLEAN; σ R = 0.648763 NOT_ESTABLISHED |
| C-03 | seam — rubric pair | COVERED and produced: mean R = 0.082738 CLEAN; σ R = 1.104435 NOT_ESTABLISHED |
| C-04 / C-05 | kernel decision + arithmetic | COVERED as a decision pack; **decision is the owner's; T6 unopened** |
| C-06 | per-tile transfer readings (coverage/χ², µ/λx) | **PRODUCED — four rows, witnessed; composition INCOMPLETE (106)** |
| C-07 | raw-σ rows | PRODUCED (per-tile, never presented as calibrated) |
| C-08 | labelled s\* reference rows | PRODUCED (s\*/χ² identity travels in the row, pin 100) |
| C-09 | equatorial lane-0 baseline | PRODUCED and WITNESSED AT CREATION (`equatorial_lane0_manifest`, push `5ec3171`) |
| C-10 | land-mask path | PRODUCED (`land_mask_exercise.kuroshio`) |
| **C-11** | **election OUTCOME with scope** | **OUTSTANDING — producer task 23, post-gate; Stage 1 does not close while it is (136c)** |
| C-12 | σ question OPEN, package named | COVERED (T12 §2; item (12) below) |
| C-13 | Stage 2/2G may not assume σ seams clean | COVERED (contract line, 37c) |
| C-14 | CRN defect travels as a PRODUCTION defect | COVERED (item (13) below) |

The T12 table's own statuses for C-06…C-10 read "ASSIGNED, UNRUN" as written on 2026-08-31;
the legs have since run and the rows are witnessed. That table is a closed deliverable and
is not retro-edited (197a); this pack carries the current state beside it.

### 1.13 — (12) The σ question OPEN, with the FULL inheritance package (pin 86) and 37(c) as a contract line

Enumerated at T12 §2, restated here so the pack carries it, not references it:
1. **Mechanism:** `obs_noise` is CRN-keyed on OBSERVATION identity and `coef_noise` on
   ELEMENT identity at a shared root, so the seam pair is already partly paired
   [S `seam_crn_channel_mechanism`: *YES — CONFIRMED, both structurally and empirically*].
2. **Both channels quantified:** on the evaluation strip the two tiles' observation sets are
   IDENTICAL (14,876 each, Jaccard 1.0000) → ρ ≈ 5.17% [S `seam_shared_observation_channel`];
   matched-member field correlation r = 0.2523 (vs −0.0026 mismatched); **ρ ≈ r² with its
   23% residual UNRESOLVED** (pin 74).
3. **Reachability and its m requirement:** F_ens / D_int_σ = 1.1356; a clean σ cell needs
   m ≥ **129 / 137 / 148** at factor 1.00 / 1.03 / 1.07 [S `ensemble_settling_measurement.pin_53_m_requirement`
   — *decision NOT MADE; priced, not chosen*].
4. **Latitude non-uniformity (pin 31b):** `basis_domain` is in km while tiles are placed in
   degrees, so whether adjacent lattices coincide varies across the grid; the alignment-
   residual survey across the D1 roster is T15, Stage 2.
5. **The ρ model with its validated span DECLARED (pin 78):** form validated over
   **[0, 0.2523] only**; application range [0, 0.9] is a **declared extrapolation**, refused
   as a floor basis until high-r points exist [S `rho_model_range_limitation`].
6. **CONTRACT LINE (37c / 86b), in these words: Stage 2 / 2G may not assume σ seams are
   clean.** T14–T21 move to Stage 2 with their pins, tasks and pre-registrations intact
   (86c), including 68(b)'s falsifier and 73(c)'s branch.

### 1.14 — (13) The CRN PRODUCTION DEFECT, in its own words (pin 87)

`S crn_production_defect_deferred`, witnessed, label *PRODUCTION DEFECT — DEFERRED, NAMED AND
COSTED*: *"Under per-tile CRN origins the blend mixes one CRN-correlated and one
CRN-independent tile, so ensemble noise is SUPPRESSED on one side of the overlap and FULL on
the other: a manufactured gradient in the delivered uncertainty field."* **A property of the
SHIPPED SYSTEM, not of an instrument. Stage 2G cannot close while it stands.** In Stage 1 its
scope is one adjacency — seam_n/seam_s, already measured by T4 (`seam_rows`); the four
diverse tiles are pairwise disjoint. Carried forward: T14–T21 as listed in the node.

### 1.15 — The 0.331 reproduction is a DETERMINISM CHECK (pin 119)

`S report_rows.anchor.2017` → groundtrack `track_excess_log10_max_repeat = 0.331012884019381`,
bit-identical to the Phase-13 Gate-1 pack's winner figure, recovered post-hoc under the
pin-112 canonical-artifact lookup (pin 114). **Which kind it is:** the anchor maps were
already bit-identical to the phase-13 winner (check 1, max|Δ| = 0), so an identical score
**follows from identical inputs**. It is an end-to-end wiring test that could have failed
(wrong map, mission filter, geometry artifact, broken lookup); **it is NOT independent
confirmation of the founding metric** — the s\*/χ² distinction under pin 100.

---

## 2 · Evidence, provenance, reviews

### 2.1 The witnessed record
45 mirrored nodes under `phase14.stage1` (`docs/validation/evidence-mirror/`), the four tile
rows among them; 24 forward pointers over 14 amended nodes; `refresh_election` registered and
unwritten (task 23's). The lane-0 bundle is WITNESSED AT CREATION. No supersession spent in
Stage 1's T5 phase.

### 2.2 Checks on the final tree (captured)
Captured 2026-09-18 on the posting tree, before the sweep:

```
$ phase14_evidence_mirror.py check
mirror self-check: PASS (45 nodes, digests match)
store vs mirror: PASS (no witnessed node has changed)
seal vs mirror: PASS
PENDING (registered, not yet written): phase14.stage1.refresh_election
amendment index: PASS (24 forward pointers over 14 nodes)

$ phase14_seal_run.py check
NOTED (pin 145b, recorded as found — uncited prior-phase gates, not reopened): 9 block(s)
  evidence.phase10.oi.lanes
  evidence.phase13.miost.c2_acceptance.window_tripwire
  evidence.phase13.miost.lanes
  evidence.phase13.miost.lanes.launch
  evidence.phase8.c2_acceptance
  evidence.phase8.c2_acceptance.window_tripwire
  evidence.phase8.c2_defect_run_20260712
  evidence.stage_b.seam_dispersion
  evidence.stage_b_defect_run_20260707.seam_dispersion
PASS: seal data/2021a_ssh_mapping_ose/ours/phase14_evaluation_seal_v1.json sha a17ea419f1d1ca119792e7a0ed0bf3d36ac6f48bc04bef2e82e1dd73b725c5d2 re-derived
```

`gate_suite verify` (the stamp against the tree, pin 124b) is captured in §2.5 beside the sweep it certifies.

### 2.3 Legs as recorded, and their reviews
| leg | recorded | ratified / reviewed |
|---|---|---|
| 1 kuroshio | 2026-09-02, `tiles.kuroshio` | leg-1 gate items 1–3 ratified (pin 130); 133's fix accepted on leg 1's store reassembling bit-identically (142); 147(a)/(b) ratified (153) |
| 2 southern | 2026-09-04, `tiles.southern` | **ratified as recorded (pin 158)**; 172 disposed — third class, row unamended (196) |
| 3 equatorial | 2026-09-10, `tiles.equatorial` | crash/halt distinction ratified (164); 160 applies with mechanism corrected (187); re-score facts restored (190/194); sampler-log scope (206) |
| 4 quiet_gyre | 2026-09-08, `tiles.quiet_gyre` | **ratified as recorded (pin 189)**; reading pre-registered before launch (180b) |

⚠ **Dual review, stated plainly:** the Stage-0 pattern was a two-reviewer adversarial
document (`2026-07-27-t13-adversarial-reviews.md`). **No such document exists for the four
Stage-1 legs.** What exists, and is cited above, is the owner's per-leg ratification in the
ruling series, each issued after a report that stated its own scope. The AC line "all
Stage-1 real legs dual-reviewed" is therefore **met in the owner-ratification form and NOT in
the two-reviewer form**; the pack does not claim otherwise.

### 2.4 The absence check over this rendered file (review pin 17)
Run over THIS file after the transfer-readings section was assembled; scope is the marked section only (review pin 17):

```
$ phase14_pack_absence_check.py docs/superpowers/2026-09-18-phase14-gate1-pack.md
absence check over docs/superpowers/2026-09-18-phase14-gate1-pack.md
  section: 110 lines between '<!-- TRANSFER-READINGS: BEGIN -->' and '<!-- TRANSFER-READINGS: END -->'
  'suggests'           0
  'consistent with'    0
  'attributable'       0
  'implies'            0
PASS: none of the banned words appears inside the assembled section
```

### 2.5 Full sweep on the final tree, skips named
**1648 passed, 21 skipped, 1 xfailed, 3 warnings in 4410.75s (1:13:30)** — on the posting tree, `pixi run pytest -q -rs -p no:cacheprovider` under `phase14_gate_suite.py run` (pin 124b: format → mypy → stamp → suite → re-verify), stall-watched, `PIXI_FROZEN=true`. Every skip named — all 21 are data- or opt-in-gated, none is a Stage-1 test:

- `tests/adapters/test_altimetry_contract.py` × 7 — JPL SSHA artifact dir not present: set SVERDRUP_JPL_SSHA_DIR to the local data root to run the conformance leg
- `tests/oracle/test_oi_oracle.py` — set SVERDRUP_ODC_DATA to the cached NATL60 window to run the oracle
- `tests/test_calibration_harness.py` — leaf-identical harness regression; set SVERDRUP_PHASE9_EXTERNAL=1 to run (runtime ~2.5 min; requires full data artifacts)
- `tests/test_calibration_harness.py` — field byte-exact gate; set SVERDRUP_PHASE9_EXTERNAL=1 to run (runtime ~2.5 min; requires full data artifacts)
- `tests/test_phase13_identity.py` — opt-in: two full-obs m=100 member solves at the signed config, ~tens of minutes; set SVERDRUP_PHASE13_EXTERNAL=1
- `tests/test_phase2_stage_b.py` — opt-in global run (~33 GB); scoped-footprint discipline
- `tests/test_phase8_identity_regression.py` × 2 — opt-in: requires a full-obs member solve (m=100) at the accepted Stage-B config, ~minutes-tens-of-minutes; set SVERDRUP_PHASE8_EXTERNAL=1
- `tests/test_sealed_copies.py` — no v2 seal tracked: T13's amendment is PREPARED but WITHDRAWN pending the owner ruling (see PROGRESS.md). This test activates the moment the
- `tests/test_sealed_copies.py` — live store not on this host: data/2021a_ssh_mapping_ose/ours/phase14_evaluation_seal_v2.json
- `tests/test_stage_a_end_to_end.py` — Stage-A end-to-end is opt-in (multi-minute, needs the 1.2GB challenge data): set SVERDRUP_STAGE_A_E2E=1 and ensure data/2021a_ssh_mapping_os
- `tests/test_stage_b_gate.py` — Stage-B gate is opt-in (multi-hour GMRF run, needs data/2021a_ssh_mapping_ose/): set SVERDRUP_STAGE_B_GATE=1 to run the real GMRF-via-BO acc
- `tests/test_stage_b_method_agnostic.py` — Stage-B end-to-end is opt-in (multi-minute, needs the 1.2GB challenge data): set SVERDRUP_STAGE_A_E2E=1 and ensure data/2021a_ssh_mapping_os
- `tests/validation/test_their_eval_lambda_x_regression.py` — small map/track fixture not present (opt-in)
- `tests/validation/test_their_eval_spike.py` — OSE_ssh_mapping_BASELINE.nc or the Cryosat-2 track not present under data/2021a_ssh_mapping_ose

`gate_suite verify`, run immediately before the commit:

```
stamp verified: 431 files unchanged since the suite ran, and the stamp records a suite that COMPLETED with exit 0
```

---

## 3 · What this gate does and does not decide
- **Decides:** the anchor accounting as read; the seam result in its ruled shape; the four
  transfer readings as recorded with their three-class reading; the election (item 7) — or
  its decline; the T6/T8 decision cells when those open.
- **Does not decide / not presented:** the kernel decision (T6 unopened), the revisit (T7),
  the OSSE run (T8), the σ seam question (OPEN by contract), the CRN defect (deferred, named),
  the attribution readout (unruled; no cross-lineage interpretation here).
- **After this gate:** task 23 records the election OUTCOME and its scope; T6/T7/T8 open on
  the owner's word; tasks 18–20 stay halted (pin 88); nothing seals.
