# Phase 14 — GATE 0 pack (Stage-0 foundations complete)

**Date:** 2026-07-23. **Seal:** `phase14_evaluation_seal_v1.json`, sha
`a17ea419f1d1ca119792e7a0ed0bf3d36ac6f48bc04bef2e82e1dd73b725c5d2`
(evidence pointer `phase14.stage0.seal`, write-once;
`verify_current_seal` PASS; mechanically re-derivable via
`pixi run python scripts/phase14_seal_run.py check` — PASSES today).

**Program state:** all Stage-0 tasks T0–T17, T19 complete with real-data
legs run and dual-reviewed. T18's cloud leg is the ONE open item (blocked
on input only the owner can provide — see item 5). Zero
evaluation-bearing maps, zero locked opens (`phase14.locked_tally`
absent; `c2_touch_tally` untouched at {miost5: 3, miost6: 1}). This gate
is a **userGate**: Stage-1 plan writing starts only on owner approval
(no-plans-on-unmeasured-constants rule — the constants are now
measured).

---

## 1 · Owner attention items (in the rider's order)

### 1.1 Consumed pre-registered defaults + actuals

| Ceiling (owner-set) | Registered | Actual consumed |
|---|---|---|
| Tier-2 probe | ≤ US$25 / 8 vCPU / 64 GiB / 6 h / 1 region | **$0 — never launched** (T18 waits, item 5) |
| CMEMS storage | ≤ 50 GiB, egress 0 | **0.824 GiB**, egress 0 |
| Gauge/catalog storage | (ledgered under the same discipline) | 0.083 GiB (PSMSL 0.017 + UHSLC hourly-all 0.065 + meta) |
| Probe ephemeral disk / cloud storage / cloud egress | ≤ 50 GiB / 0 / ≤ 1 GiB (ruling) | 0 / 0 / 0 |

Total ledgered: **0.907 GiB** across 5 rows, single-writer, all named.
No WAIT was ever triggered by an actual; the T16 review's zero-ceiling
rows (probe storage/egress) were superseded by the owner ruling before
any use.

### 1.2 dc2021a gate-2 substrate interpretation (recorded, reviewer-walked)

SPEC §10 gate 2 ran on a **dc2021a-wrapped source** — the current box
input path's actual files, byte-comparable today. PASSED per-mission,
full-span AND 2017-frame (six missions, n_obs table in evidence
`gate2_loader_identity`, manifest sha c688b0d8…). The
dc2021a-vs-CMEMS-MY lineage question was split out to the golden tile
(item 1.3) per the approved pin 1. Standing interpretation: the
papers-lineage claim attaches to dc2021a (DT2021-era); CMEMS `_202411`
results carry the vintage caveat.

### 1.3 Golden-tile first comparison — **TABLED (as designed)**

The pre-registered cross-DT bridge (anchor box × 2017 × frozen signed;
CMEMS missions relabeled h2ag→h2g; both sides score the same j3 track):

| Quantity | Value | Threshold | Factor |
|---|---|---|---|
| µ delta (their_eval scale) | −0.012457 | 0.002 | 6.2× |
| map RMS | 4.10 cm | 1 cm | 4.1× |
| map max-abs | 83.7 cm | (recorded) | — |
| worst-day RMS | 8.58 cm | (recorded) | — |

`tabled_for_owner: true` — the instrument records and tables, it never
blocks Stage 1. Facts the owner needs beside the table:

- **µ-scale protocol note** (review catch, resolved by measurement,
  recorded as `mu_scale_check` in the node): the µ rows are on the
  `their_eval.score` scale, NOT the phase-13 `leaderboard_nrmse` scale.
  The signed lane0 maps score **0.76953** through the identical scorer
  vs mu_a **0.76941** — side A ≡ the signed solution (1.43 cm rms from
  lane0); **no solver drift**. The A-vs-B delta is internally fair
  (same scorer both sides). Caveat carried honestly: TABLED_MU_DELTA
  0.002 was derived from the phase-13 pair band (a different µ scale);
  the tabled outcome is robust — either leg alone tables it.
- **Max-abs 0.84 m is interior jet-band signal, not an artifact**
  (verified: day ≈ 2017-09-11, 39.0°N 296.4°E, 21+ cells from any
  edge; 0.02% of samples over 0.5 m, confined to the 36.8–41°N
  meander band; temporal edges BELOW median per-day rms).
- **j2n obs delta −1696** (−27.3% of the `_202411` count 6202;
  equivalently −37.6% of the dc2021a count 4506): the largest
  per-mission count gap — a lineage/repackaging difference, recorded
  not smoothed. [Denominator convention pinned 2026-07-25, review
  pin 14: count-delta percentages are quoted relative to the
  `_202411` (side-B) count unless a denominator is named.]
- **Transform semantic recorded**: CMEMS side clipped to grid-node
  extent ±1° BEFORE challenge-coarsen (clip-then-coarsen — the probe's
  recorded semantic and the signed convention's regional inputs;
  `load_region_note` in the node; commit 6984e26).
- **⚖ OWNER-ELECTABLE, NOW MATERIAL:** the AVISO DT2021 (authed)
  decomposition source — the ruling said "elected ONLY if the measured
  bridge delta is material to a Stage-1 reading". The bridge delta is
  over threshold on both legs. Election remains the owner's;
  repackaging and DT-generation deltas stay inseparable without it.
- Conflation note (ruling item 1) carried verbatim in the node.

### 1.4 Probe ratios vs the Phase-12 precedent

Measured at the pinned production-geometry tile ([292,307]×[30,45],
one 60-day window, m=1, five missions, super-obs n=5):

- wall 383.5 s vs model 747.8 s → **ratio 0.513**
- peak RSS 3344.6 MiB vs model 4259.7 MiB → **ratio 0.785**

Model conservative on both axes; constants NOT retuned in-code
(Phase-12 precedent; `git diff 249a08d..HEAD -- miost_sizing.py` empty
— reviewer-verified). **PCG note:** the member-batch leg exited at the
500-iter cap at residual 1.02e-06 vs rtol 1e-06 (surfaced in-log,
recorded in the evidence pcg rows) — `wall_s` is therefore a mild
lower bound; the mean solve converged free at 461 iters. Tier-1
launch predicate ran FIRST and refused once at MemAvailable 5.4 GiB
before the eventual run (the predicate works).

### 1.5 T18 cloud leg — WAITING on credentials (owner input)

No cloud credentials exist on this host (no ~/.aws, ~/.config/gcloud,
~/.azure, no env). The Tier-2 probe (cost + cross-host determinism
measurements, `sky/phase14_probe.yaml`, pinned to the owner ceilings,
teardown required) cannot launch. Machinery complete and same-host
leg DONE (two CRN manifests EQUAL; golden synthetic-stream sha pinned
db0e6423… so a rebased randomness layer cannot silently agree
cross-host). The m=1 ZeroDivisionError that would have killed the
cloud solve leg was found and fixed this session (`61c586c`) — the
cloud leg launches clean when credentials arrive.

### 1.6 Proximity-deferral interpretation (screening criterion 4)

No program grid exists in Stage 0, so gauge proximity binds AT
CONSUMPTION against each stage's actual product grid (the evaluator's
wet-node interpolation already self-excludes unreachable gauges). All
563 rows carry the deferral VISIBLY; the interpretation is recorded
identically in module docstring, per-row detail, evidence node, and
the sealed screening config. Owner sign-off on this interpretation is
part of this gate.

### 1.7 Gate-5 µ-lineage deferral

The T14 adversarial catch stands: the near-pinned 0.8642 constant is
`leaderboard_nrmse` lineage, a different quantity from `compute_stats`
µ. Gate 5 asserts machinery identity (score_tile ≡ their_eval.score,
rtol 1e-12); the value constants pin AT the Stage-1 anchor run. The
golden-tile µ-scale note (1.3) is the same lineage class measured in
the wild — consistent story, both recorded.

### 1.8 Additional owner lines surfaced by review

- **Stage-0 real artifacts live on this disk only** (all gitignored:
  seal, evidence store, locked_split, screening_rows, epoch table,
  census). The integrity chain is git → PROGRESS sha → seal content;
  disk loss makes Gate-0 evidence depend on deterministic re-derivation
  from re-downloads (splits/tables rebuild byte-equal —
  reviewer-verified). Consider an out-of-repo copy of the seal +
  evidence store.
- **Evidence-store silent-skip (latent):** `phase14_probe.py` /
  `phase14_golden_tile.py` skip their evidence write if the store is
  absent (`if EVIDENCE.exists()`). Non-triggered (store present), but
  a long solve on a fresh host would complete unrecorded. The
  downloader got the WAIT fix (`a41d92e`); the two probe scripts are a
  cheap follow-up if desired.
- **Seam rubric 2.5 anchor:** recorded honestly as a-priori (midpoint
  of the phase-4 C∈[2,3] range, different metric class); owner may
  re-pin at this gate.
- **Mission-code naming split across nodes** (`probe_tile` uses CMEMS
  codes, `golden_tile` challenge codes) — each internally consistent,
  mapping documented; cosmetic.

---

## 2 · The sealed evaluation set (the founding artifact)

Content (all byte-verified by reviewer + `seal_run check`):

- **Epoch table** (Task-5 bytes, sha ba1050be… as evidence): 15 epochs
  1992-10-13 → 2026-01-17; anchor e10_2017-05-18 holdout j3
  signed-workhorse-by-construction; role split
  fit+validate/validate-only per net-of-locked ≥ 4; ±66° mask on
  ERS-line rows; handicap columns present.
- **Locked gauges** 39 / **dev** 96 (from 563 candidates → 135
  screened; 30%/stratum round-half-up over 12 populated strata —
  per-stratum audit exact), split seed 2278306912366042270 =
  `derive_seed("insitu","phase14-seal","locked-split",0)`; split
  rebuild from raw survivor data is **byte-equal**
  (reviewer-executed). `locked_split.json` is now write-once
  (`41a40fa`).
- **Screening config** — derived FROM the operative constants
  (`screening_config_record()`, drift-proof): 5 criteria in order,
  12 h/day, 70%/epoch + 3 y, RLR 0.05°, prox 150 km (deferred),
  7 excluded basins, 8-box strata.
- **Instrument configs** (Tasks 9/11): four families + sealed nulls
  (15-day circular-boxcar doy climatology + lag-1 persistence,
  signature pinned) + seam verdict cells CLEAN ≤1.0 / ELEVATED ≤2.5 /
  STRUCTURAL-STOP >2.5; byte-deterministic serialization.
- **c2 era windows**: e05..e14 (c2 e05–e11, c2n e12–e14, per table).
- **Descriptor schema v1** binding.

Locked-tier state: tally untouched, zero opens, the T10 ceremony
tripwire now verifies against this real seal (default verifier refuses
without it).

## 3 · Evidence axes (node `phase14.stage0`, single store)

| Node | Content |
|---|---|
| `gate2_loader_identity` | PASS; per-mission n_obs (alg 80812 / h2g 71293 / j2g 14639 / j2n 22504 / j3 87460 / s3a 82014); manifest c688b0d8… |
| `cmems_census_raw_sha` | 17ec736a… (schema v2, 29 missions) |
| `census_sha` / `n_epochs` | ea82b953… / 15 |
| `epoch_table_draft_sha` | ba1050be… |
| `gauges` | series-leg-complete; 563/135/39/96; catalog manifest shas; pending → dated RESOLVED |
| `probe_tile` | ratios 0.513 / 0.785; superobs cfg; pcg rows; "NOT retuned" note |
| `golden_tile.dc2021a_vs_cmems_my` | full comparison + `mu_scale_check` + `load_region_note`; tabled TRUE |
| `storage_ledger` | 5 rows, 0.907 GiB total |
| `seal` | path + sha a17ea419… + v1 |

## 4 · Session fix record (all TDD, dual-reviewed, pushed)

| Commit | Fix |
|---|---|
| `a41d92e` | superobs cfg into golden-tile record (pre-mint); downloader ledger WAIT on absent store |
| `61c586c` | ensemble_provenance m=1 ZeroDivisionError → mc_error None (would have killed the T18 cloud solve) |
| `6984e26` | golden-tile CMEMS side loads halo region, not globe (OOM exit 137 root cause; clip-then-coarsen recorded) |
| `dbff89f` | PROBE label INSIDE the nc maps |
| `41a40fa` | seal runner build/check; locked-split write-once; screening config single-source |

Dual reviews: T3/T4/T5 real legs CLEAN; T15+T7 runs ACCEPT (µ-scale
major resolved by measurement); T8+T19 ACCEPT (split rebuild
byte-equal; seal chain verified; minors actioned in `41a40fa`).

## 5 · Final test sweep (the flip-tree rule)

**1167 passed / 22 skipped / 1 xfailed (41:16), exit 0** — on the final
tree (`7ef555a`), the standing rule's application. Every skip reason
named: 7 × JPL conformance (data-gated on `SVERDRUP_JPL_SSHA_DIR`),
1 × gate-5 (Stage-1 anchor artifact `anchor_signed_maps.nc` not
present, by design), remainder = standing data-gated legs. Note: the
CMEMS conformance legs no longer skip — they run on the real subset
(12 passed).

One test fixed between sweeps (sweep 1: 1166/1167):
`test_refuses_on_missing_seal` exercised the default verifier against
the LIVE evidence store and was time-dependent by design ("pre-Task-19")
— building the real seal made it pass-through. Now hermetic against a
sealless tmp store (`7ef555a`); the behavior under test (refuse while no
seal recorded) is unchanged and still pinned.

## 6 · What Gate-0 approval unlocks

Stage-1 plan writing (spatial-at-2017, six-tile roster, mesoscale-only,
frozen five-mission config, zero touches) against the C0→1 contract —
with the measured constants: tile sizing ratios, seam rubric, sealed
evaluation set, and the tabled golden-tile row as the recorded
cross-lineage context (per-tile source map: anchor + seam-pair on
dc2021a; non-box tiles on CMEMS-MY; the bridge delta is the recorded
translation). The Phase-13 six-mission-refresh election trigger sits at
Gate 1, not here.

**STOP: awaiting owner review of this pack (T20 userGate).**

---

## ADDENDUM (Gate-0 ruling item 1, 2026-07-23) — attribution readout from data in hand

**Ruling context:** GATE 0 CLOSED/APPROVED, seal v1 signed. Attribution
BEFORE election; this readout is computed read-only from the exact
framed sets the golden tile solved (same loads, same transforms; no
re-solve, no maps).

### A.1 Per-mission along-track table (A = dc2021a, B = cmems_my `_202411`)

| Mission | n_A | n_B | Δn | mean_A − mean_B | std_A − std_B | day-span note |
|---|---|---|---|---|---|---|
| alg | 15916 | 15622 | +294 (+1.9%) | −4.4 mm | +1.6 mm | B ends ~1 d later |
| h2g | 14546 | 14452 | +94 (+0.6%) | −4.5 mm | +0.2 mm | B ends ~1 d later |
| j2g | 2886 | 2818 | +68 (+2.4%) | −6.0 mm | +0.2 mm | spans equal (d191–255) |
| j2n | 4506 | 6202 | **−1696 (−27.3% of B)** | **+21.1 mm** | −1.5 mm | **A ends day 91.5; B extends to day 136.5** |
| s3a | 16491 | 16267 | +224 (+1.4%) | −2.0 mm | −1.6 mm | B ends ~1 d later |

Overall: mean_A 0.112664 m vs mean_B 0.112301 m; std_A 0.236801 m vs
std_B 0.236877 m.

### A.2 The three ordered checks

1. **Reference-surface / mean-epoch consistency: CONSISTENT.** Overall
   mean offset **+0.36 mm** — no reference-surface or mean-epoch shift
   between lineages on the box. Per-mission mean deltas are mm-level
   (−2.0 to −6.0 mm for four missions, a common-mode processing-baseline
   scale), not a surface change.
2. **Along-track variance/RMS: ESSENTIALLY IDENTICAL.** std deltas
   ≤ 1.6 mm against ~237 mm signal — the DT generations do not differ
   in along-track energy on the box. The map-level 4.1 cm RMS delta is
   therefore NOT a noise-floor or variance-scaling effect.
3. **n_obs structure: ONE STRUCTURAL DIFFERENCE + edge trims.** Four
   missions show small +0.6–2.4% A-excess consistent with coarsen
   bin-phase/daily-file chunking at the region and window edges (the
   recorded repackaging delta; B's spans run ~1 day longer at the
   window tail). **j2n is categorically different: dc2021a's j2n
   record STOPS at day 91.5 (~2017-04-01) while `_202411` carries j2n
   through day 136.5 (~2017-05-16) — ~45 extra days of a whole mission
   on the box, −27% count delta.** Its +21.1 mm mean delta co-moves
   (different span samples different seasonal state), consistent with
   check 1's verdict that this is coverage, not datum.

### A.3 Reading (candidate driver, honestly bounded)

The measured bridge delta is **not attributable to reference surface or
variance scaling** (checks 1–2). The dominant structural candidate is
the **j2n coverage-window difference** — an entire mission present for
~45 more days in CMEMS on the box — plus mm-level common-mode mean
offsets. Attribution of the 6.2×/4.1× map+µ deltas to the j2n span
specifically would require a controlled re-solve (j2n-trimmed CMEMS
side); NOT run — not ordered, and it spends a solve on a question the
owner may answer by election instead.

**What AVISO DT2021 would and would not decide:** it would tell whether
the j2n truncation is DT2021-generation behavior (j2n retired earlier in
that lineage) or dc2021a repackaging; it would NOT change checks 1–2
(already clean). If the owner prefers the cheaper instrument first: the
j2n-trimmed re-solve isolates the span effect with zero new data and no
auth, at one box-solve of compute (~7 min measured).

Stage-1 interpretation language WAITS on the owner's readout of this
addendum, per the ruling; every cross-lineage Stage-1 reading carries
the bridge caveat until then.
