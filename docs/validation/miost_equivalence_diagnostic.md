# MIOST windowed-vs-single-window equivalence diagnostic (Task 11 / D4)

**Provenance:** CONVERGED run (rtol 1e-6 reached in every solve; no residual
warnings in the run log). A first run at the (rtol 1e-6, maxiter 500) defaults —
where every solve stalled at ~5e-4 residual — produced near-identical deltas
(worst-day max|Delta| 2.0036 vs 2.0220 m; blend medians 0.5740 vs 0.5542 m), so
the deltas are depth-insensitive in map space and attributable to windowing,
not solver noise. Solver findings (stall at 500 iters, ~5000-6000 iters to
rtol 1e-6, LSMR only ~1.3-2x) recorded in PROGRESS.md.

- Params: alpha=1.5, rho=10 (log10_rho=1), q_slope=2, L_t=10; grid 0.2 deg (52, 51); obs = 6 mapping missions, box+halo (70,857 points).
- Windowed: production WindowPlan (9 windows, W=60/V=15/stride 45, right-aligned last). Single: one 425-day window [-30, 395].
- Days solved: 0..364 (365); blend days: 148, interior days: 217.
- PCG rtol 1e-06 / maxiter 6000 on BOTH paths (identical solver settings; per-window residuals in the run log).

## Per-day max|Delta| [m] (worst-case-localized; the headline metric)

| class | median | p95 | max |
|---|---|---|---|
| blend days | 0.5542 | 1.1050 | **1.5242** |
| interior days | 0.6068 | 1.1945 | 2.0220 |

Median single-window field std (scale context): 0.245 m.
Solver-noise floor (windowed path, maxiter 6000 vs +2000, worst day): max|delta| = 0.0000 m — Delta attribution requires clearing this.
Worst day overall: day 250 (interior), max|Delta| = 2.0220 m, RMS = 0.1823 m.

## Ten worst days

| day | class | max|Delta| | RMS Delta | field std |
|---|---|---|---|---|
| 250 | interior | 2.0220 | 0.1823 | 0.268 |
| 251 | interior | 1.7778 | 0.1558 | 0.268 |
| 249 | interior | 1.7236 | 0.1483 | 0.275 |
| 200 | interior | 1.5496 | 0.1434 | 0.254 |
| 252 | blend | 1.5242 | 0.1322 | 0.266 |
| 265 | blend | 1.5135 | 0.1823 | 0.298 |
| 245 | interior | 1.4164 | 0.1262 | 0.280 |
| 264 | blend | 1.4034 | 0.1555 | 0.303 |
| 248 | interior | 1.3923 | 0.1186 | 0.280 |
| 266 | blend | 1.3596 | 0.1584 | 0.303 |

## Verdict

**FALLBACK NOT INVOKED — cost recorded (OWNER DECISION, Task-11 close 2026-07-05);
see `miost_equivalence_localization.md` + the PROGRESS close entry.**

Recorded windowing cost — POINT-MEASURED at the untuned diagnostic point
(alpha=1.5, rho=10, q_slope=2, L_t=10), NOT a universal figure: Delta-mu =
-0.0066 (windowed 0.9391 / single 0.9457, blocked j3 track), Delta-lambda_x =
+8 km (96.3 vs 88.3). Winner-point re-measurement happens at Task-13 acceptance
(validation-only, feasibility-conditional; c2 stays touched exactly once, by
the windowed winner).

Mechanism (modest wording): consistent with information-pooling differences
dominated by the mid-ladder (113-320 km) band — year-long temporal chaining
that 60-day windows cut — plus a ~0.18 m boundary-linked minority component
(weak decay, corr -0.223, over a ~0.5 m floor). The 19x J-gap in probe 4 is
expected for ANY stitched solution — it was a defect check on the reference
(passed), not a quality metric.

Superseded heuristic verdict (for the trail): the script's automated line read
"FALLBACK NEEDED: yes" from the pre-localization blend-day heuristic; the
localization probes showed the deltas are NOT the blend-seam mechanism that
heuristic assumes.
