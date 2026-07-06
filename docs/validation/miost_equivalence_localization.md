# MIOST equivalence localization (Task-11 D4 probes, owner-ordered)

Solves at the Stage-A budgeted config (rtol 1e-6 target, maxiter 500 cap);
map-space depth-insensitivity measured in the equivalence doc.

## Probe 1 — blocked-validation skill (j3 track; never c2)

| map | mu | lambda_x [km] |
|---|---|---|
| windowed (product) | 0.9391 | 96.3 |
| single-window (reference) | 0.9457 | 88.3 |

**Delta-mu (windowed - single) = -0.0066**

> **PROTOCOL CAVEAT (owner-ordered addendum, 2026-07-06):** both maps in
> this probe were built from the SIX mapping missions — they ASSIMILATED
> j3 and were then scored on the j3 track. Leaked absolutes inflate both
> µ values (0.94-ish vs the winner's train-only 0.86-ish regime) and
> compress the delta. This probe's Δµ is therefore NOT same-protocol
> with the Task-13 winner-point re-measurement, whose corrected
> TRAIN-ONLY (j3-excluded) result is **Δµ = −0.0022 / Δλx = +0.57 km**
> at the tuned winner (results JSON `winner_point_windowing_cost`).
> The first winner-point measurement (2026-07-05, Δµ = −0.0652) was
> itself cross-protocol — single-window side assimilated j3, windowed
> side did not — and is preserved in the results JSON as
> `winner_point_windowing_cost_CROSS_PROTOCOL_20260705`; it is NOT a
> windowing cost.

## Probe 2 — Delta vs distance to nearest window boundary

| dist bin [d] | n days | mean max|D| | max max|D| | mean RMS |
|---|---|---|---|---|
| 0-3 | 80 | 0.704 | 2.004 | 0.095 |
| 3-6 | 95 | 0.655 | 1.706 | 0.088 |
| 6-9 | 75 | 0.689 | 1.555 | 0.088 |
| 9-12 | 45 | 0.581 | 1.067 | 0.078 |
| 12-15 | 45 | 0.560 | 0.907 | 0.080 |
| 15-18 | 15 | 0.445 | 0.753 | 0.071 |
| 18-21 | 6 | 0.593 | 0.991 | 0.067 |
| 21-max | 4 | 0.537 | 0.635 | 0.066 |

corr(dist, max|D|) = -0.223; near(<6 d) mean 0.678 vs far(>=15 d) mean 0.495 -> profile NOT flat.

## Probe 3 — scale + spatial attribution

Ladder rungs (km): ['80', '113', '160', '226', '320', '453', '640', '905']

| day | per-rung max|D_rung| | top-2-rung energy share |
|---|---|---|
| 250 (worst) | ['0.237', '0.407', '0.441', '0.334', '0.342', '0.196', '0.110', '0.202'] | 0.32 |
| 0 (far) | ['0.206', '0.239', '0.205', '0.182', '0.130', '0.086', '0.064', '0.106'] | 0.23 |

Worst-day spatial: argmax at cell (33, 27) of (52, 51), 18 cells from the nearest edge; edge-band(5) max 0.755 vs interior max 2.004.

## Probe 4 — J-identity (single-window objective)

J(eta_single) = 3.079232e+04; J(stitched windowed) = 5.963252e+05 -> OK (reference is the better minimizer)

## Pre-registered close-rule outcome

**WINDOW-EDGE MECHANISM: profile decays with distance — implement the D4 pavement extension**
