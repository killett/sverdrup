# MIOST Stage-B seam-dispersion + variance-equivalence diagnostic (Task 18)

- Params: D4 diagnostic point alpha=1.5, rho=10 (log10_rho=1), q_slope=2, L_t=10; grid 0.2 deg (52, 51); obs TRAIN-ONLY box+halo (53,583 points; c2 locked, j3 validation — neither assimilated).
- Members: m=50, CRN root=1 — SAME root on BOTH sides (identity-keyed CRN; the comparison isolates windowing).
- Solver: budgeted rtol 1e-06 / maxiter 2000 on BOTH sides; achieved residuals below (budgeted-solve honesty).
- Days: 0..364 (365); blend 148, interior 217. Exactly one batched member solve per window (9 windowed + 1 single); member fields via the sparse S-path.

## (a) Seam dispersion — per-day spatial MAX of member std [m]

| class | median | p95 | max |
|---|---|---|---|
| blend days | 0.3313 | 0.3844 | **0.4257** |
| interior days | 0.3262 | 0.3980 | 0.4353 |

**HEADLINE ratio (blend worst / interior median) = 1.305** (0.4257 / 0.3262).

## (b) Variance equivalence — per-day max|Delta member-std| windowed vs single [m]

| class | median | p95 | max |
|---|---|---|---|
| blend days | 0.0907 | 0.1578 | **0.2066** |
| interior days | 0.0590 | 0.0973 | 0.1218 |

Scale context: median per-day spatial-max single-window member std = 0.3499 m. Worst day: 80.
Windowed solver-floor probe (worst blend day, maxiter +1000): max|std shift| = 0.00305 m.

## Member-batch achieved residuals (budgeted solve)

| window | iterations | final rel residual |
|---|---|---|
| w-00018.0+60 | 2000 | 3.19e-04 |
| w+00027.0+60 | 2000 | 2.92e-04 |
| w+00072.0+60 | 2000 | 3.10e-04 |
| w+00117.0+60 | 2000 | 2.65e-04 |
| w+00162.0+60 | 2000 | 2.33e-04 |
| w+00207.0+60 | 2000 | 2.03e-04 |
| w+00252.0+60 | 2000 | 2.31e-04 |
| w+00297.0+60 | 2000 | 2.80e-04 |
| w+00322.0+60 | 2000 | 2.79e-04 |
| w-00030.0+425 | 2000 | 2.97e-04 |

## Verdict

TASK-19 GATE VERDICT: seam-dispersion ratio (blend worst / interior median, spatial-max) = 1.305 (FLAGGED — outside [0.9, 1.1]); variance equivalence: worst-day max|Delta std| = 0.2066 m blend / 0.1218 m interior vs std scale 0.3499 m (FLAGGED — exceeds 10% of scale); windowed solver-floor probe 0.00305 m — deltas clear the floor.

Run footprint: RSS 0.94 GB / peak 4.15 GB.

## Rubric applied (pre-registered 2026-07-06, `miost_seam_dispersion_rubric.md`)

- **Rule 0 (validity):** rel_F = 0.00305/0.3262 = 0.0094. Metric (a)
  deviation |R−1| = 0.305 > 3×rel_F = 0.028; metric (b) D = 0.2066 m >
  3×F = 0.0092 m. **Both metrics MEASURED** (solver floor cleared by >10×;
  the 2000-iter budget's ~3e-4 residuals move the std fields only 0.003 m).
- **Rule 1 (seam dispersion): FLAG over-dispersion** — R = 1.305 > 1.10.
  Partition-of-unity + blend tests green at the run's commit (suite
  420/9/1 at `06b03ea`). *Post-hoc context (labeled as such, not a rubric
  rule):* the class distributions nearly coincide — medians 0.3313 (blend)
  vs 0.3262 (interior), p95 0.3844 vs 0.3980, and the worst blend day
  (0.4257) is BELOW the worst interior day (0.4353); blend-max/interior-max
  = 0.978. The flag reflects ~±30% day-to-day variability of the spatial
  max in BOTH classes (track-sampling geometry) hitting a max-vs-median
  ratio, not a blend-day dispersion excess. Owner reads flag + context at
  the Task-19 gate.
- **Rule 2 (variance equivalence): EXCEEDED** — D = 0.2066 m > 0.10×S =
  0.035 m; recorded as the VARIANCE windowing cost at the D4 point.
  Mechanism split: blend max (0.2066) ≈ 1.7× interior max (0.1218), but
  interior Δ is itself large (median 0.0590 = 17% of scale) — a substantial
  uniform information-pooling component (the year-pooling single window
  yields a different σ field) plus a blend-localized extra, matching the
  D4 mean-field reading (mid-ladder pooling floor + boundary-linked
  minority). Per the rubric this does NOT reopen Task 20 (windowed ships;
  the single window is a reference); gate evidence only.
- **Rule 3 (budget note for Task 19):** member batches capped at 2000
  iters with achieved residuals 2.0–3.2e-4 on BOTH sides at this
  deliberately ill-conditioned D4 point (ρ=10); the floor probe shows the
  member std fields are solver-stable to 0.003 m. Task 19 re-decides the
  budget at the WINNER point (ρ≈10^-1.6, converged ≤286 iters in Stage A)
  and must not copy these residuals forward.
- **Rule 4: Task 18 CLOSED** — measurement complete; both FLAG outcomes
  and their context transfer to the Task-19 gate evidence.

Run telemetry (Task-22 peak-model validation datapoint): windowed leg
peak RSS 1.12 GB (model 1.24 GB, ratio 1.11); single-425d leg peak
4.15 GB (model 4.48 GB, ratio 1.08) — both inside the pre-registered
[1x, 2x] conservative band; byte constants stand, no recalibration. Wall:
windowed 6h14, single 3h54, floor probe 1h25 (11h34 total; first two
windows ran under CPU contention).
