# Phase 14 Stage 1 — THE ASSEMBLED VIEW

> ⛔ **THIS IS NOT THE GATE-1 PACK, IS NOT WRITTEN AS THE PACK, AND IS NOT AN EVIDENCE
> NODE** (owner pins 198, 197b). It is **material for the owner's walk**, assembled
> read-only from what is already recorded, so the whole can be read in one place before T9
> opens. **T9 remains unopened.**
>
> **Rule of construction (198g): if something is not in a pin or a recorded row, it does not
> appear here.** No number is re-derived, no solve or diagnostic was run, and where a number
> needs a caveat to be read correctly **the caveat travels with it**.
>
> **Sources.** `S` = the evidence store,
> `data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json`, under `phase14.stage1`.
> `R` = the ruling doc, `docs/superpowers/2026-07-27-owner-ruling-crn-sigma-rule0.md`.
> `P` = `PROGRESS.md`. Store state as read at commit `d64f49c`; mirror at **42 nodes**.
>
> ⚠ **Section 8 (what I expected to find and could not) is the part to read first.** Per
> 198(h) it is the more useful half, and one item in it bears on the launch gate.

---

## 1. The four tiles side by side (198a)

All four: `m = 100`, **9 windows** of `w_days = 60.0`, `days_stride = 1`,
`resolution_deg = 0.2`, `overlap_deg = 2.0`, `halo_deg = 1.0`, `missing_neighbors = []`,
source **cmems_my**, super-obs `challenge-coarsen n=5`. All four `CONVERGED` with
`capped_measurement = false` at `rtol = 1e-6`, `maxiter = 1200`. [S `tiles.<tile>`]

| | kuroshio | southern | equatorial | quiet_gyre |
|---|---|---|---|---|
| core `[lon0, lon1, lat0, lat1]` | 132–147, +28…+43 | 215–230, −62…−47 | 200–215, −4…+11 | 255–270, −30…−15 |
| solve bbox | 130–149, +26…+45 | 213–232, −64…−45 | 198–217, −6…+13 | 253–272, −32…−13 |
| recorded date | 2026-09-02 | 2026-09-04 | 2026-09-10 | 2026-09-08 |
| **λx [km]** | **232.5339** | **141.9472** | **RECORDED ABSENT** | **RECORDED ABSENT** |
| µ [m] | +0.28595412 | −0.61762861 | +0.76578991 | +0.84793330 |
| σ [m] | 0.21861301 | 0.13772269 | 0.05942276 | 0.06257645 |
| coverage_1σ | 0.00977815 | 0.00258066 | 0.03263243 | 0.16666988 |
| χ² (`chi2_j3_validation`) | 416.6777 | 1637.4844 | 40.3115 | 11.6379 |
| n scored points | 89,383 | 137,174 | 100,299 | 103,786 |
| n_obs (framed) | 138,518 | 175,059 | 167,579 | 168,755 |
| raw σ | 0.03818712 | 0.03496572 | 0.03798931 | 0.03772121 |
| s\* (`scalar_s_star`) | 416.6777 | 1637.4844 | 40.3115 | 11.6379 |
| leg wall [s] | 70,811.32 | 98,929.75 | 91,945.0 | 93,712.97 |
| leg wall [h] | 19.67 | 27.48 | 25.54 | 26.03 |
| peak RSS [MiB] | **7,389.34** | 4,951.16 | 4,817.0 | 4,986.42 |
| headroom min in the ROW | **absent** | **absent** | 3,468 (BACKFILLED) | **absent** |
| PCG worst iterations | 505 | **626** | 579 | 611 |
| PCG legs recorded | 18 | 18 | 18 | 18 |
| converged / capped | CONVERGED / false | CONVERGED / false | CONVERGED / false | CONVERGED / false |

**Caveats that travel with every cell above** — see §5 for the verbatim text:
`reference_row = {raw-sigma + scalar-s* transfer, REFERENCE-ONLY, NOT CALIBRATED}` on all
four; `bridge_caveat` (cmems_my source) on all four; `sigma_caveat` on all four; every
`mu`/`sigma`/`coverage_1sigma`/`lambda_x`/`raw_sigma`/`scalar_s_star` carries
`report_only: true` with pin 95's note; **χ² records and does not gate** (pins 95 + 98);
**s\* and χ² are the same number twice** (pin 100b), not two witnesses.

**Headroom minima — the single headroom record** is
[S `headroom_minima_recovered`], **RECOVERED FROM LOGS, not produced by the legs' own
recording path** (pin 188a). It is **not** the rows:

| leg | in-run tracker min [MiB] | 5-min heartbeat min [MiB] | 1-min external sampler min [MiB] | n heartbeats |
|---|---|---|---|---|
| kuroshio | **none — predates 151(b)** | 3,660 | none | 235 |
| southern | 1,382 | 1,382 | 1,526 | 328 |
| equatorial | 3,468 | 3,828 | 3,601 | 306 |
| quiet_gyre | 2,762 | 2,778 | 2,704 | 312 |

⚠ **Leg 1's floor is UNRECOVERABLE and 3,660 MiB is an UPPER BOUND on it, not the value**
— [S `headroom_leg1_floor_unrecoverable`], which also corrects an arithmetic statement in
the ruling that cited it (the supporting per-leg gaps are **0 / 360 / 74 MiB**, median 74,
not "306–328 MiB" — those three are heartbeat *counts*). **That node is neither mirrored
nor reachable from the amendment index — see §8, item 3.**

---

## 2. Per-band spectra (198b) — ⛔ NOT RECORDED AS TABLES

**The per-band `study/ref` and `diff/ref` tables for all four tiles do not exist as a
recorded artifact.** `scripts/diag_stage1_coherence.py` and
`scripts/diag_stage1_hypothesis_tests.py` write no file; their output survives only as the
**selected rows quoted in the rulings**. Assembling the full four-tile × all-bands table
would require re-running them, which is a measurement, not a read — so it is **not done
here** (198g) and is flagged in §8, item 1.

**Everything that IS recorded, verbatim in scope:**

| tile | band | study/ref | diff/ref | source |
|---|---|---|---|---|
| kuroshio | 70–95 km | 3.823 | 4.697 | R pin 181 / P |
| equatorial | 250–400 km | 4.291 | 5.169 | R pin 181 / P |
| southern | 50–70 km (opposite sign) | 0.017 | 1.009 | R pin 181 / P |
| southern | **500–1000 km** | **0.084** | **0.988** | R pin 196b / P |
| southern | 150–300 km | — | **0.355–0.405** | R pin 196a |
| equatorial | 12.8–996.3 km | — | median `psd_diff/psd_ref` **1.0005** | S row + R pin 160 |

**Within-tile latitude gradients (sign check, pin 177a):** equatorial and kuroshio improve
polewards; **southern WORSENS** — `diff/ref` **0.482** at |lat| 50 against **0.716** at 58.

**Common-floor test (pin 181c), the one all-four comparison that is recorded:** all four
turn upward at **35–50 km** — ratios **1.07 / 1.03 / 1.41 / 1.58** (kuroshio / southern /
equatorial / quiet_gyre) — and again below 25 km — **1.88 / 1.93 / 2.38 / 2.52**. Recorded
reading: the rise is **not** a weak-tile property, it occurs at the same wavelength in all
four rather than where each signal drops through a fixed level, and the levels differ
~3.6× between clusters, so **a single common absolute floor does not account for it**.

**Cross-tile correlations (pin 181a, n=21, three tiles):** `corr(log10 absolute band
variance, diff/ref)` = **−0.464**; `corr(log10 |f|, diff/ref)` = **−0.322**.
**With the fourth tile (pin 186b, n=28) BOTH WEAKENED: −0.254 and −0.121.** Recorded
consequence: **the effect is at TILE level, not band level.**

**Coherence maxima, measured on the persisted maps, read-only (R, 2026-09-06):**
kuroshio **0.894** · southern **0.659** · equatorial **0.003** · quiet_gyre **0.0026**.

**Track variance (pin 176c), the confound-breaking measurement, no solve:**

| tile | lat span | n | track std [m] | variance [m²] | vs kuroshio |
|---|---|---|---|---|---|
| kuroshio | +28…+43 | 95,883 | 0.4793 | 2.297e-01 | 1.0× |
| southern | −62…−47 | 147,276 | 0.6570 | 4.317e-01 | 0.5× |
| equatorial | −4…+11 | 107,706 | 0.0884 | 7.813e-03 | 29.4× |
| quiet_gyre | −30…−15 | 111,812 | **0.0695** | **4.828e-03** | **47.6×** |

⚠ **NAMING HAZARD, recorded and deliberately NOT fixed (pin 178):** the vendored quantity
called `coherence` is `1 − psd_diff/psd_ref` = `2√r·Re(γ) − r`, which ranges to **−4.17**
(equatorial) and **−18.21** (quiet_gyre). **It is not a coherence.** Do **not** rename it —
it is the published leaderboard definition and comparability depends on it. Do record what
it is at every consumer, together with equatorial's true **Re(γ) max of 0.482**, which
also never reaches 0.5.

---

## 3. The two absences, with their full recorded evidence (198c)

Both are `recorded_absent: true` with `value: null` under pins **160(a)/161** — *a RECORDED
ABSENCE, not a scoring failure and not a value of zero.* Both carry the row's `not_zero`
statement: *"a zero would claim the map resolves every scale, the inverse of what was
measured."* [S `tiles.<tile>.scores.lambda_x.absence`]

| | equatorial | quiet_gyre |
|---|---|---|
| reason | `UnresolvedScaleError` | `UnresolvedScaleError` |
| message | map resolves no scale; λx undefined (no 0.5 coherence crossing) | same |
| crossing sought | 0.5 | 0.5 |
| **coherence max** | **0.0030273113** | **0.0026272919** |
| **coherence min** | **−4.169038** | **−18.210680** |
| `psd_diff/psd_ref` median | **1.00046557** | **1.00053869** |
| wavelength band [km] | 12.773636 – 996.343608 | 12.773636 – 996.343608 |
| **n wavenumbers** | **79** | **79** |

Recorded reading carried in both rows: *the residual PSD is compared against the reference
at every wavenumber; a median ratio at or above 1.0 means the map removes no variance at
any resolved scale.*

**Equatorial only:** the original leg **died in scoring at 25.5 h (91,945 s)** with all
nine windows solved and persisted; pin 161 landed, and the re-score from the store recorded
it in **21 s** [P]. Its row's `wall_s`/`peak_rss_mib` are the **ORIGINAL run's**, restored,
with the re-score's replaced values preserved at `headroom.restored_run_facts`
(57.31626431 s / 3,803.79296875 MiB). That hazard is now **prevented in code** — pin
190(a)/(b) at `7fa106d`, ratified 194.

---

## 4. Instrument rows, their four absences, and wedge exclusion (198d)

[S `report_rows.<tile>.2017`] — **this node is DERIVED and re-derivable, so it is
deliberately NOT mirrored** (pin 56b); the mirror's amendment index points at it as
reachability, *not* as a witness claim.

**Rows present at each of the four diverse tiles: 2** — `accuracy` (metrics `{}`, flag
`no_usable_context`, `context_keys_available: []`) and `spectral_fidelity`.

**The four recorded absences, identical at all four diverse tiles**, each
`status: "NOT APPLICABLE — RECORDED ABSENCE"` with *"absence, not omission: the instrument
was evaluated for applicability and could not run here (fork F)"*:

| evaluator | missing context |
|---|---|
| calibration | `WITHHELD_OBS` |
| skill | `WITHHELD_OBS` |
| **groundtrack** | `ORBIT_GEOMETRY` |
| insitu_gauges | `INSITU_GAUGES` |

**anchor, seam_n and seam_s record THREE absences** — calibration, skill, insitu_gauges.
**GroundTrack is absent only at the four diverse tiles.**

**Wedge exclusion — which tiles recovered under pin 112, and which did not:**

| tile | `wedge_exclusion_status.kind` | in-row `wedge_exclusion` | geometry artifact present |
|---|---|---|---|
| kuroshio | **DESIGN CONFLICT (pin 106)** | 0.0 | false |
| southern | **DESIGN CONFLICT (pin 106)** | 0.0 | false |
| equatorial | **DESIGN CONFLICT (pin 106)** | 0.0 | false |
| quiet_gyre | **DESIGN CONFLICT (pin 106)** | 0.0 | false |
| anchor | **IN SCOPE — wedge exclusion available** | 1.0 | true |
| seam_n | **IN SCOPE — wedge exclusion available** | 1.0 | true |
| seam_s | **IN SCOPE — wedge exclusion available** | 1.0 | true |

**This is exactly what pin 112(c) said to expect: restoration at anchor and the seam pair
only.** Each diverse tile's row carries the reason in-row, as 112(c) requires — *tile core
lies OUTSIDE the derivation's box [295.0, 305.0] (φ₀ = 38.1); this is pin 106's design
conflict, not a lookup gap: applying this geometry here would be geometry that does not
belong to the tile* — and the consequence: **the spectral slope is a DEGRADED estimand
here**, fitted without excluding the track-aligned wedges, so orbit-sampling artifacts sit
inside the fitted band. **Not fixable in Stage 1; per-tile derivation is Stage-2 work
(106d), and pin 108 stands for T6 unchanged.**

**Recorded spectral-fidelity metrics** (degraded estimand at the four diverse tiles, per
the row's own flag `wedge_exclusion:false`):

| tile | spec_slope | WLS SE | slope day-median | day IQR | n_modes_min |
|---|---|---|---|---|---|
| kuroshio | −4.832952 | 0.020350 | −4.804925 | 0.315163 | 24 |
| southern | −4.157497 | 0.049205 | −4.191927 | 0.600223 | 29 |
| equatorial | −5.014511 | 0.030671 | −4.699387 | 1.126792 | 24 |
| quiet_gyre | −5.063102 | 0.032098 | −4.867804 | 0.850977 | 24 |
| anchor | −6.951845 | 0.108122 | −6.891741 | 1.904872 | 10 |
| seam_n | −5.830157 | 0.101534 | −5.785608 | 1.443767 | 7 |
| seam_s | −7.497447 | 0.141805 | −7.463648 | 1.065497 | 6 |

⚠ The **day IQR is 5.5× wider at equatorial than at kuroshio** (1.127 against 0.315) while
the WLS SE is of the same order — recorded as found, no reading attached.

All seven blocks record `gates: false`.

---

## 5. Caveats that attach to ROWS, not to prose (198e)

Verbatim from the store. **Every one of these is a row field; none is narration.**

**`bridge_caveat`** — on all four (source `cmems_my`; `None` on the dc2021a anchor):
> cross-lineage reading; golden-tile bridge delta MEASURED ON THE ANCHOR BOX (mu −0.012457
> their_eval-scale, map RMS 4.10 cm); its magnitude at THIS tile is unmeasured;
> interpretation WAITS on the owner attribution readout

**`sigma_caveat`** (pin 94 — a REQUIRED field wherever a raw sigma is reported):
> per-tile sigma level under THIS tile's own CRN origin; the deferred CRN production defect
> (phase14.stage1.crn_production_defect_deferred) is a property of the SHIPPED SYSTEM, not
> of an instrument; cross-tile sigma comparison is NOT supported and the boundary gradient
> is DEFERRED and unmeasured; the within-tile sigma level is NOT compromised - the four
> diverse tiles are pairwise disjoint and only seam_n/seam_s are adjacent

**The h2ag → h2g relabel** — inside `superobs_cfg.mission_relabel`, on all four:
> CMEMS-MY codes relabelled to CHALLENGE codes before the solve (h2ag -> h2g; all others
> identical), the CHALLENGE_TO_CMEMS inverse — the recorded interpretation the golden tile
> applies, so the frozen config's mission-keyed R deltas apply per instrument on both
> sources

It is also **the substantive half of pin 106's design conflict**: `h2ag ≠ h2g` is why the
orbit geometry derived on the anchor box does not belong to the diverse tiles (112b).

**`reference_row`**, on all four (`None` at the anchor alone, whose scores ARE calibrated):
`{"kind": "raw-sigma + scalar-s* transfer", "label": "REFERENCE-ONLY, NOT CALIBRATED"}`.
The same **`REFERENCE-ONLY, NOT CALIBRATED`** label is repeated inside `raw_sigma` and
`scalar_s_star` themselves.

**`report_only`** — on `mu`, `sigma`, `coverage_1sigma`, `lambda_x`, `raw_sigma` and
`scalar_s_star` in every one of the four rows:
> REPORT-ONLY: a reading with no expectation to compare against, so pin 42's gate fields do
> not apply and none are recorded here (pin 95)

**The s\*/χ² identity** (`scores.s_star_chi2_identity`, pin 100b — *the identity travels in
the row*): shared expression `mean((truth - mean)**2 / var)`, `supports_coincide: true`,
`same_by_construction: true`.
> agreement between these two fields is an IDENTITY, not independent confirmation: a
> consumer reading them as two witnesses is reading one number twice

with `support_basis`: DISJOINT supports were **REFUSED** — *independence manufactured by
splitting the point set degrades one number to decorate the other* — and `enforced_by`:
`build_scores_block` raises when the two values differ (100c), so **divergence may be
legitimate but is never silent**.

**χ² records and does not gate** (`chi2_j3_validation.pin42`, pins 95 + 98):
`gates: false`, `kind: "recorded outcome, NOT a gate"`, null `E[χ²_red] = 1 (calibrated)`,
**`pass_condition: null`, `fail_condition: null`** — and the field that forbids completing
them:
> adding a threshold here would re-gate chi2 behind that ruling's back (98b) — the absent
> failure condition is the record, not a gap

---

## 6. Pointer list for the six things the pack must state together (198f)

**Pointers, not restatements.** Where each already lives:

| # | thing | where it is recorded |
|---|---|---|
| 1 | **The readings** | S `phase14.stage1.tiles.{kuroshio,southern,equatorial,quiet_gyre}` — all four **witnessed in the mirror**; §1 above is their assembly |
| 2 | **The absences** | λx: S `tiles.{equatorial,quiet_gyre}.scores.lambda_x.absence` (pins 160a/161). Instrument rows: S `report_rows.<tile>.2017.recorded_absences` — four per diverse tile (fork F). Ruling: R PART 40 (161), PART 44 (185–186) |
| 3 | **The three classes** | R **PART 47** (pin 196b) verbatim; P CURRENT STATE three-class table. ⛔ **Deliberately NOT in the store** — owner pin 197(b): the store holds measurements and firewalled hypotheses; interpretation lives in the pack |
| 4 | **The open mechanism** | R PART 44 (186b) — long-scale dominance + weak signal, **NOT established**, and **at TILE level, not band level** (n=28 correlations weakened to −0.254 / −0.121). Retractions: 166b and 170 both **WITHDRAWN** (R PART 42, pin 175); the geostrophic account **REFUTED** by quiet gyre (187a). Firewalled hypotheses still live: the 905 km-share test (175/177c), the bias/reference-offset reading (196c), the "each tile's own resolution limit" account (181) |
| 5 | **Incomplete composition at the diverse tiles (pin 106)** | S `report_rows.<tile>.2017.wedge_exclusion_status` (kind = DESIGN CONFLICT) + `recorded_absences.groundtrack`; R pins 106, 108, 112(b)/(c). P carries it as carried-forward item 1: **the transfer readings ship with their composition stated INCOMPLETE, in the section where the numbers are, as a REAL WEAKENING** |
| 6 | **Deferred CRN production defect (pin 87)** | S `phase14.stage1.crn_production_defect_deferred` — **mirrored**. Labelled *PRODUCTION DEFECT — DEFERRED, NAMED AND COSTED*; **Stage 2G cannot close while it stands**; in Stage 1 its scope is **one adjacent pair, seam_n/seam_s**, already measured by T4 (`seam_rows`), the four diverse tiles being pairwise disjoint. Its product consequence is a **manufactured gradient in the delivered uncertainty field** |

**The lane-0 bundle**, for completeness of the pointer list: S
`equatorial_lane0_manifest` — **mirrored, WITNESSED_AT_CREATION** (pins 96b/96d/96e), four
files at `…/phase14_stage1/equatorial_lane0` (`equatorial_signed_maps.nc`,
`equatorial_member_std_maps.nc`, `evidence_pack.json`, `fold_eval_frame.json`), the maps
themselves deliberately outside the mirror (56b — the shas are the witness). Its
`frozen_config_policy` is fork-B.2 verbatim. **Its `WITNESS NOW` push landed at `5ec3171`
and was ratified at pin 195.**

---

## 7. What holds the numbers up (context the walk will want)

- **Launch gate:** `MemAvailable ≥ 9,902.33 MiB` = 2 × the measured **4,951.16 MiB**
  (pin 155, southern's direct nine-window measurement). Prior bases preserved as a chain at
  `TIER2_MEASURED_PEAK_SUPERSEDED`: 4,365 → 4,573 → 4,951. **See §8 item 9.**
- **The gate is launch-time only and does not protect the leg** (pin 156). What protects it
  is the in-run watchdog: below **2,048 MiB**, or the leg's own `VmSwap` at 64 MiB with
  headroom under 4,096, the leg **stops cleanly at a window boundary** — `HEADROOM_HALT`,
  exit **75**, **no evidence row**.
- **Per-leg wall ceiling 40 h, POST-HOC** — evaluated after the leg is recorded; it never
  interrupts. Its whole effect is the printed line plus the next leg not launching.
  All four legs came in at 19.67–27.48 h.
- **Nothing seals.** The single authorised supersession is **UNSPENT**.
- `phase14.stage1.refresh_election` is **registered and not written** — task 23's node,
  unwritable until the shipped-config election is ruled at Gate 1 (pin 136). **Left
  pending deliberately** (pin 193); it prints on every `check`.

---

## 8. ⚠ What I expected to find and could not (198h)

Ordered by how much it bears on the walk.

**1. The per-band `study/ref` / `diff/ref` tables are not recorded anywhere.** They exist
only as the selected rows quoted in rulings (§2). `diag_stage1_coherence.py` and
`diag_stage1_hypothesis_tests.py` write **no artifact** — no `json.dump`, no `write_text` —
so every band number in the record passed through prose. **198(b) cannot be satisfied from
the record as it stands.** The numbers can be regenerated read-only from the persisted maps
(that is how 177/181 were produced), but that is a measurement and was not run here.

**2. ⛔ Kuroshio's recorded peak RSS is 7,389.34 MiB — 1.49× the 4,951.16 MiB the launch
gate's 2× is computed from.** The gate is **9,902.33 MiB**, which is **1.34×** kuroshio's
recorded peak, not 2×. The basis chain (4,365 → 4,573 → 4,951) is described throughout as
window-boundary peaks from the *probe* and from *southern*; **kuroshio's row-level figure
appears in no current-state narrative and is the largest of the four by 2.4 GiB** (southern
4,951.16, equatorial 4,817.0, quiet_gyre 4,986.42). I cannot tell from the record whether
the two quantities are meant to be comparable — row `peak_rss_mib` is process `ru_maxrss`
at the end of the leg and therefore includes the scoring phase, while the basis is a
boundary trace. **If they are comparable, this is the same shape as the 1.18× and the
1.847× the owner has already corrected twice, one step further out.** Recorded here, not
adopted; it is a ruling, not an executor call.

**3. `headroom_leg1_floor_unrecoverable` is NOT mirrored and NOT reachable from the
amendment index.** It declares itself `amends: phase14.stage1.headroom_minima_recovered`,
which **is** mirrored — but the mirror's amendment index has **no pointer** from that node
to it (22 pointers over 12 nodes; `headroom_minima_recovered` is not among the 12). So a
reader arriving at the witnessed headroom record cannot reach the node that says **leg 1's
3,660 MiB is an upper bound and not a measurement**, nor its arithmetic correction. **That
is precisely the failure pin 64's index exists to prevent** — a witnessed node looking
current while the record that amends it is unreachable from it.

**4. A pin-number collision.** `headroom_leg1_floor_unrecoverable` cites **`pin: "191"`**
for the ruling *"leg 1's floor is UNRECOVERABLE"*, and quotes that pin as stating the
supporting evidence *"as '306-328 MiB'"*. **PART 45's pin 191 is the concurrent-owner
`git log` check**, and the string "306-328" appears nowhere in the ruling doc. The node
therefore cites a **191 that the authoritative series does not contain** — consistent with
it having been written under the forked advisory numbering that PART 44 resolved. Flagged,
not touched: renumbering is the owner's under pin 40, and the node is witnessed-adjacent.

**5. Three of the four rows carry no `headroom` key at all** — kuroshio, southern and
quiet_gyre. **Only equatorial's row has one**, `status: BACKFILLED`. This is the 151(b)
drop as recorded, and it is now fixed forward — but PROGRESS's phrasing ("Legs 1–2 are
witnessed, so their values are BACKFILLED … and their rows are not edited") can be read as
though the rows carry it. **They do not. The rows are silent; the single headroom record is
the separate node.**

**6. PROGRESS names a node that does not exist.** It points backfilled headroom at
`phase14.stage1.headroom_backfill`. **There is no such node.** The real ones are
`headroom_minima_recovered` (mirrored) and `headroom_leg1_floor_unrecoverable` (not).

**7. Two records of the same equatorial logs disagree.** The row's
`headroom.heartbeat_log` gives `logs/leg_equatorial/leg.log` sha `888c5ae0…` and the
sampler `255ad285…` with `n_samples 1535`; the node `headroom_minima_recovered` gives the
same two paths as `078e7da7…` and `dd036ba9…` with `external_sampler_n 1533`. Capture dates
differ (row 2026-09-10, node 2026-09-09), which would explain a growing log — **but nothing
in either record says so**, and a reader comparing shas sees two witnesses disagreeing.

**8. `scores.reduced_chi2` is `None` in all four rows.** Every χ² quoted in the record is
`scores.chi2_j3_validation`. Anyone grepping the field name the rulings use most often
finds an empty field.

**9. No GroundTrack row exists at any of the four diverse tiles, and none can.** Expected —
pin 106, recorded honestly in-row — but worth stating in the pack's own voice: of the six
instruments, **two ran and four recorded absences**, and `geometry_artifact_present` is
`false` at all four. The transfer readings' composition is **INCOMPLETE**, and that belongs
in the section where the numbers are, not in a footnote (106c).

**10. σ appears for kuroshio in the row (0.21861301) but not in PROGRESS's current-state
line for leg 1**, where the other three legs' σ are quoted. No contradiction — an omission
in the summary, filled in §1.

---

## Provenance of this document

Assembled **2026-09-11** from the store, the mirror, the ruling doc and PROGRESS at commit
`d64f49c`. **No solve, no diagnostic and no scoring path was run to produce it; nothing was
re-derived.** It is not an evidence node (197b), not the Gate-1 pack, and creates no
obligation on any recorded row. **T9 remains unopened.**
