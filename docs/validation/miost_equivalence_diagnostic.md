# MIOST windowed-vs-single-window equivalence diagnostic (Task 11 / D4)

- Params: alpha=1.5, rho=10 (log10_rho=1), q_slope=2, L_t=10; grid 0.2 deg (52, 51); obs = 6 mapping missions, box+halo (70,857 points).
- Windowed: production WindowPlan (9 windows, W=60/V=15/stride 45, right-aligned last). Single: one 425-day window [-30, 395].
- Days solved: 0..364 (365); blend days: 148, interior days: 217.
- PCG rtol 1e-6 / maxiter 500 on BOTH paths (identical solver settings; any residual truncation is common-mode).

## Per-day max|Delta| [m] (worst-case-localized; the headline metric)

| class | median | p95 | max |
|---|---|---|---|
| blend days | 0.5740 | 1.0622 | **1.4804** |
| interior days | 0.6051 | 1.1853 | 2.0036 |

Median single-window field std (scale context): 0.245 m.
Worst day overall: day 250 (interior), max|Delta| = 2.0036 m, RMS = 0.1827 m.

## Ten worst days

| day | class | max|Delta| | RMS Delta | field std |
|---|---|---|---|---|
| 250 | interior | 2.0036 | 0.1827 | 0.267 |
| 251 | interior | 1.7426 | 0.1552 | 0.267 |
| 249 | interior | 1.7064 | 0.1487 | 0.275 |
| 200 | interior | 1.5549 | 0.1442 | 0.254 |
| 252 | blend | 1.4804 | 0.1308 | 0.266 |
| 265 | blend | 1.4725 | 0.1807 | 0.296 |
| 245 | interior | 1.3945 | 0.1247 | 0.280 |
| 248 | interior | 1.3713 | 0.1187 | 0.280 |
| 264 | blend | 1.3640 | 0.1536 | 0.302 |
| 95 | interior | 1.3293 | 0.1909 | 0.239 |

## Verdict

FALLBACK NEEDED: yes — worst blend-day max|Delta| = 1.4804 m (603.9% of the median field std 0.245 m); interior worst = 2.0036 m; ratio blend/interior = 0.74

**Owner checkpoint:** the pavement +-L_t temporal-slot extension (D4 fallback) is NOT implemented; decide invoke / not-needed from the numbers above before Task 13.
