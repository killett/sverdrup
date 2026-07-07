# MIOST Stage-B seam-dispersion + variance-equivalence diagnostic (Task 18)

- Params: D4 diagnostic point alpha=1.5, rho=10 (log10_rho=1), q_slope=2, L_t=10; grid 0.2 deg (52, 51); obs TRAIN-ONLY box+halo (53,583 points; c2 locked, j3 validation — neither assimilated).
- Members: m=4, CRN root=1 — SAME root on BOTH sides (identity-keyed CRN; the comparison isolates windowing).
- Solver: budgeted rtol 1e-06 / maxiter 50 on BOTH sides; achieved residuals below (budgeted-solve honesty).
- Days: 0..30 (31); blend 4, interior 27. Exactly one batched member solve per window (9 windowed + 1 single); member fields via the sparse S-path.

## (a) Seam dispersion — per-day spatial MAX of member std [m]

| class | median | p95 | max |
|---|---|---|---|
| blend days | 0.2836 | 0.2852 | **0.2853** |
| interior days | 0.2771 | 0.3649 | 0.3685 |

**HEADLINE ratio (blend worst / interior median) = 1.030** (0.2853 / 0.2771).

## (b) Variance equivalence — per-day max|Delta member-std| windowed vs single [m]

| class | median | p95 | max |
|---|---|---|---|
| blend days | 0.0498 | 0.0525 | **0.0528** |
| interior days | 0.0409 | 0.0727 | 0.0738 |

Scale context: median per-day spatial-max single-window member std = 0.2589 m. Worst day: 2.
Windowed solver-floor probe (worst blend day, maxiter +1000): max|std shift| = 0.27607 m.

## Member-batch achieved residuals (budgeted solve)

| window | iterations | final rel residual |
|---|---|---|
| w-00018.0+60 | 50 | 1.83e-02 |
| w+00027.0+60 | 50 | 1.82e-02 |
| w+00072.0+60 | 50 | 2.18e-02 |
| w+00117.0+60 | 50 | 1.84e-02 |
| w+00162.0+60 | 50 | 1.59e-02 |
| w+00207.0+60 | 50 | 1.49e-02 |
| w+00252.0+60 | 50 | 1.62e-02 |
| w+00297.0+60 | 50 | 1.96e-02 |
| w+00322.0+60 | 50 | 1.81e-02 |
| w-00030.0+425 | 50 | 1.59e-02 |

## Verdict

TASK-19 GATE VERDICT: seam-dispersion ratio (blend worst / interior median, spatial-max) = 1.030 (no seam artifact at the 10% heuristic); variance equivalence: worst-day max|Delta std| = 0.0528 m blend / 0.0738 m interior vs std scale 0.2589 m (FLAGGED — exceeds 10% of scale); windowed solver-floor probe 0.27607 m — deltas do NOT clearly exceed the floor (solver-noise caveat).

Run footprint: RSS 0.62 GB / peak 3.85 GB.
