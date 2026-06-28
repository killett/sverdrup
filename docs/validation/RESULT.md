# OI Validation Result — vs 2021a SSH-mapping OSE BASELINE

## Leaderboard comparison (their eval is ground truth)

| Method | µ(RMSE) | σ(RMSE) | λx (km) |
|---|---|---|---|
| **ours (OI)** | 0.853 | 0.090 | 140.9 |
| BASELINE (published) | 0.850 | 0.090 | 140.0 |
| DUACS (published) | 0.880 | 0.070 | 152.0 |

## Sanity anchor (λx is the sensitive number)

Their eval reproduces the published **DUACS** row: reproduced 0.877 / 0.065 / 152.3 km. λx is the most sensitive metric and is reported explicitly.

## Parallel cross-check (our eval vs theirs, same map)

Our `area_weighted_rmse` µ on our map: **0.858** vs their µ on our map **0.853** (Δ = 0.005).

## Decomposed read (design §6)

- Tolerance applied (µ): **±0.03** (stated and applied as recorded; never loosened to manufacture a pass).
- **Verdict: PASS** — Reproduces the BASELINE row; sanity anchor + parallel eval agree.
