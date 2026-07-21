# Phase-13 GATE-1 evidence pack (Task 12 — HELD for owner review)

Assembled 2026-07-21 on the final tree (no source edits during the gate
suite). Every number below is quoted from a captured command output or
the evidence store — none from memory. Evidence store:
`data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json`
(gitignored; jq paths given per row).

---

## 0. SOURCE TABLE (owner pin — marks RESOLVE HERE, before any touch authorization)

Quoted VERBATIM from `src/sverdrup/validation/phase13_boxes.py` module
docstring (sealed via Task 6; restated inside `phase13_band_artifact.json`
sha `79e4e486cfd83adeb963598c7b87e6ba8a3550dcf52ed57a8ead2b04a56589cf`):

> | Quantity | Basis | Source | Status |
> |---|---|---|---|
> | δ boxes ±0.7 (×2 in σ² either way) | published per-mission noise
>   levels are RELATIVE contrasts only: Ka-band AltiKa (alg) low noise
>   vs HY-2A (h2g) high noise; published values inform the boxes, the
>   tuner sets the values (σ²_m never quoted as physical noise) |
>   mission noise characterizations in the altimetry literature
>   [verify-at-review: owner confirms the alg-low / h2g-high ordering
>   and that ×2 brackets the published spread] | verify-at-review |
> | Λ boxes log10 ∈ [−6, −2.5] m² (σ_mode ≈ 1–56 mm) | challenge L3
>   inputs are CMEMS DT2021 corrected SLA INCLUDING long-wavelength-
>   error corrections (DAC / ocean tide / LWE) → the target is the
>   RESIDUAL orbit/LWE structure post-correction, cm-order |
>   ballarotta2023 extraction (brief input-SSH row); spec §17
>   [verify-at-review: owner confirms the cm-order residual reading of
>   the DT2021 correction chain] | verify-at-review |
> | R diagonal precedent | R is diagonal in all three family papers;
>   real-data R values are NOT specified in any paper — the structured
>   R extends the family's own state-augmentation pattern | U2021
>   §2.2.1/2.2.2; B2023 App. A1 (spec §17, verified from extractions)
>   | verified-in-spec |

**Two `verify-at-review` marks await owner resolution** (δ ordering/spread
bracket; Λ cm-order residual reading).

---

## 1. READINGS + DIAGNOSTICS (the owner's first read, per the execution rider)

### 1a. GroundTrack direction vs 0.410 (§9a; jq `.phase13.miost.readings.direction_row`)

```
winner max repeat track_excess_log10 = 0.331012884019381
baseline (five-mission, Phase-11)   = 0.410  ->  DOWN
six-mission beside (non-governing)  = 0.376
```
Direction matches the pre-registered expectation ("DOWN if
track-correlated error is real and absorbed"). Necessary-not-sufficient
caveat recorded verbatim in the row. Geometry artifact v3 sha
`4e1d0db12971…` (matches the Phase-11 record).

### 1b. The saturation + lag-1 + field-correlation TRIPLET (§8; jq `.phase13.miost.diagnostics.C`)

The §3-frame measurement (real / absorbed / absent) this phase exists to
make. Lane-C winner (2233 deduped passes, 9 windows); modes-only lane
recorded beside with the same shape.

- **Saturation** (share |ĉ|>2√Λ; null < 5%): bias 0.100–0.161 per
  mission (s3a 0.106, j2n 0.121, h2g 0.126, alg 0.100, j2g 0.161) —
  ABOVE null for every mission → **fires the §4 q_slope table
  trigger** (recorded, report-only). Tilt 0.012–0.040 (under/near null).
- **Lag-1 absorption discriminator** (time-ordered, family-separated;
  band ±2/√n): positive persistence BEYOND the band in 9/10
  mission×families (r1 0.17–0.49; e.g. s3a/asc +0.284 @ band 0.098,
  alg/desc +0.471 @ 0.126); j2n/desc −0.439 (beyond-band negative,
  the one exception). Median inter-pass Δt ≈ 1 day per row.
- **Field-correlation complement** (§8.4 sign logic): 6/10
  COMPENSATION (negative beyond band, r −0.11…−0.25), 4/10 clean,
  **0/10 absorption**. Reading shape: the modes carry REAL persistent
  along-track structure (persistence + saturation), the attribution
  SEESAWS with the field (over-parameterization signature), and there
  is NO positive field-leakage signature.
- **Variance-ratio table** (§8.1; shrinkage note applies — read
  CROSS-MISSION CONTRASTS, not distance from 1): bias var(ĉ)/Λ
  s3a 21.5 / j2g 18.7 / h2g 14.9 / alg 8.3 / j2n 8.0 (2.7× spread);
  tilt 0.16–0.56 (healthy shrinkage everywhere).
- **Adjacent-window ĉ agreement** (§8.5 free stability row): n=1073
  overlap passes, corr 0.041, rmse 0.0358 m — window-local ĉ, not a
  stable per-pass property.

### 1c. Flattening / ŝ refit (§9b; jq `.phase13.miost.refit.flattening_rows`)

Frozen anchor-family frame (mask sha `6c2802f57b46…`, fold tuple
`("miost","phase8","s-folds")`, scope config byte-identical; G_pre
verified EXACT against `phase9.g_pre_anchor` = 0.13510401012055406,
STOP-on-drift armed). SIGMA_OBS2 untouched.

```
s_hat refit  = 5.1059814223881155
s_hat signed = 8.737979722446696 (miost5)
delta        = -3.63199830005858   <- the pre-registered LOWER direction
G_pre  = 0.13510401012055406
G_post = 0.1895237598683136
G shrinkage = -0.05441974974775954  (NEGATIVE: s(x) structure MORE
              informative post-R-change; opposite sign to Phase-10's
              V-lane +0.0557 relocation-into-prior)
winner lane = poly (same family as the signed fit)
```

### 1d. SpectralFidelity + mean-map deltas (§9c/§9d)

- spec_slope −6.9518 (descriptive; sub-λx rolloff caveat stands, no
  verdict semantics).
- Mean-map deltas vs the signed miost5 stage-B maps: 365 days compared;
  max |Δ| 0.17405 m; rms 0.01424 m.

---

## 2. VERDICT ARITHMETIC (T9, executed once; jq `.phase13.miost.lanes.verdict`)

```
PRIMARY C-vs-lane0 (claim-bearing): beats-mu, POSITIVE
  dmu  +0.0013757178941510295  vs band 0.0009258589562811534  (1.49x)
  dlx  -3.820651031134446 km   vs band 4.590792815682484 (informative,
       n_lambda_used 178/200; never consulted - mu decided)
  n_segments 403; wording pin: "C beats lane-0 beyond the measured band (beats-mu)"
SECONDARIES (never claim-bearing):
  D-vs-0:          beats-mu, dmu +0.0012603 vs band 0.0012055 (1.046x - thin)
  modes-only-vs-0: beats-mu, dmu +0.0015140 vs band 0.0009532 (1.59x);
                   highest mu of all lanes (0.8657140); NEVER ships (sealed)
WINNER-LANE RULE (spec §10): C-vs-D dmu +0.0001154 vs band 0.0006190
  (0.19x) WITHIN BAND -> chain lane D (simpler lane on tie)
BRANCH RECORDED: "WINNER: Tasks 11-14 proceed on lane D"
protocol_sha 79e4e486... (refusal clock passed; lane-0 byte-integrity
  match; single-execution guard live)
```

Dual reviews on the verdict: spec-compliance PASS all 5 (arithmetic
recomputed exact); adversarial NO refutations (Δµ/band reproduce BITWISE
under sealed seed 271828; seal bytes unchanged since `4766db9`). Two
epistemics caveats persisted: (1) within-lane winner-selection optimism
unpriced by the pair band (mitigant in-record: all three lanes selected
the SAME paired Sobol index 24, Δµ ≈ +0.0013–0.0015 — shared-effect
signature); (2) ρ is released in every sweeping lane and gains are
near-equal — attribution (ρ vs δ vs modes) is the 2×2 cell above.

---

## 3. SAMPLING-CORRECTNESS + SUITES (final tree, captured)

- m=100 acceptance ensemble (chain lane D idx 24): root
  7742201642112487637 EXACT INT (verified `== 7742201642112487637` by
  python; jq float-rounds — string form beside), m=100, converged at
  first cap 500, retention slicing FIELD-BLOCK-ONLY verified True.
- Measured m=100 member-variance consistency row (Task-4 oracle
  comparison at the chain-lane rspec, recorded root): median rel dev
  0.0678 / max 0.1775 vs rtol 0.7107 — **PASSES (4× headroom)**.
- Identity + oracle + member-variance + teeth suites
  (`test_phase13_identity + test_miost_{augmented,duality,ensemble}_oracle
  + test_miost_ensemble_augmented`, final tree): **21 passed, 1 skipped
  in 34:55** — the skip is the expensive EXTERNAL four-route identity,
  executed and recorded at T3 (`5be6a65`: member arrays sha-bit-equal
  zeros≡scalar, mean vs acceptance, Γ-route ≤1e-12, variance 2.2e-16).
- Full suite w/ coverage (final tree, captured in
  `phase13_gate1_suite.log`): **952 passed, 14 skipped, 1 xfailed,
  3 warnings in 57:04 — coverage 93%** (6971 stmts, 515 miss).

---

## 4. BUDGET / TELEMETRY LEDGER

- Sweeps: lane D 6.06 h; lane C scoring 25802 s; modes-only scoring
  21027 s (launch rule est 11.83 h ≤ 12 h; monitor flag never tripped).
- T9 read: single execution, ~7 h wall (4 consulted pairs × 2000 µ +
  200 λ resamples each).
- Members: wall 24780.5 s (6.88 h), 9 windows, peak window solves
  38–62 min under co-tenant pressure; converged at first cap.
- Refit: 63.7 s. Readings: ~4 min. ctap runs: ~7 min/lane.
- PCG conditioning watch (§2 rider 4, report-only): winner-trial max
  iterations D 422 / C 415 vs the 302 scalar-era baseline — the
  augmented/per-mission systems condition worse at the winner Λ/δ;
  members batch converged at cap 500 (residual ≤ 1e-6).
- OPERATIONAL NOTE for the ledger: the modes-only lane initially
  HARD-FAILED on a lane-name mismatch (`modes_only` LANES key vs the
  sealed hyphen `modes-only`); owner-approved fix-then-run `ebab4ac`
  (two red tests; no sealed artifact altered; clean re-run of the
  affected lane only).

---

## 5. HYGIENE / INTEGRITY ROWS

- Registry untouched: `git diff a17d67b..HEAD -- src/sverdrup/methods/registry.py`
  → **empty (0 lines)**. `SHIPPED["miost"]` = shipped_miost6, unchanged.
- Registry AC-1 (T11): five-mission lineage entry verified =
  `shipped_miost5()` factory (`methods/miost.py`) — clean factory, no
  migration surprise; a win updates THIS entry at T14 only.
- Zero c2: phase-13 scripts' only `c2` references are the lockout
  (`locked_missions=["c2"]`, lane_run:127) and docstring notes;
  compare/diagnostics scripts have zero occurrences; validation track
  only throughout.
- Tally arithmetic unchanged ahead of T13: {miost5: 2 → 3 on the touch,
  miost6: 1}.

---

**HELD FOR OWNER REVIEW.** Gate closes only on the owner's approval
message. On approval: T13 = the ONE c2 touch under the template
tripwires verbatim (provenance tripwire recomputes all fields BEFORE the
c2 file opens; window tripwire n = 44,844 + year-span; one-invocation
mechanics; exact-string env ceremony). Then T14 owner ruling (lineage
flip + external sweep + six-mission-refresh election record + close).
