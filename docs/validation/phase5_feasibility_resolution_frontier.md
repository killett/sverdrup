# Phase-5 Stage-C feasibility frontier (owner redesign input)

**Bottom line (robust, tolerance-invariant):** global `SAMPLES/COVARIANCE` coherent sampling with the
bare tree-kriging driver is **infeasible at operational range** — the worst-case adjacent-seam joint
correlation error is ~2.0 by 25 tiles and rising, exceeding any sane tolerance at a global (thousands of
tiles) product. `MARGINAL_VARIANCE` **ships** globally, conditional on accepting a fixed ~15% worst-case
reported-marginal error. Operational-range DUACS-class global *coherent* products are out of reach until
the **owner-deferred** decomposition-redesign (coarse-correction / overlapping-Schwarz / low-rank seam
basis) widens `n_star_joint`.

## Tier 1 — SAMPLES/COVARIANCE (joint cross-seam covariance)

Worst-of-K adjacent-seam corr-err (K=418 fixed, M=8000, selection-controlled), median, ± estimator std:

| tiles | worst-of-K | ± std | median |
|-------|-----------|-------|--------|
| 4     | 1.105     | 0.000 | 0.015  |
| 9     | 0.506     | 0.079 | 0.023  |
| 16    | 0.823     | 0.135 | 0.031  |
| 25    | 2.033     | —     | 0.052  |
| 36    | 2.108     | —     | 0.070  |

- **Regional caveat (shorthand only):** at `joint_tol=0.5` every tested tiling's point estimate exceeds
  tol → `n_star_joint=1`. But the worst-of-K is **non-monotone** in N (2×2 > 3×3), and **3×3 = 0.506 ±
  0.079 is within noise of 0.5** — no multi-tile geometry is *clearly* feasible, but the small-N
  exclusion rests on a thin margin. A loosened tol (> ~0.51) makes feasibility **non-nested** (needs an
  `N → worst-case` lookup, not a threshold).
- **Deficit shape:** typical seam is excellent (median 1.5%→7%); the worst-case is a **sparse catastrophic
  tail** (~0.24% of pairs at 2×2), not uniform mediocrity — the coarse-correction must rescue a few
  catastrophic seam pairs, not fix a uniform deficit.

## Tier 2 — MARGINAL_VARIANCE (reported marginal accuracy, analytic)

| tiles | worst-case rel error |
|-------|----------------------|
| 4     | 0.069 |
| 9     | 0.140 |
| 16    | 0.130 |
| 25    | 0.149 |
| 36    | 0.132 |

Worst-case ~13–15%, **FLAT** with tile count → ships iff `marg_tol ≥ ~0.15`, tile-count-independent. This
is the honest global product, correctly labeled `MARGINAL_VARIANCE`, not "coherent."

## Provenance

Single synthetic fixture (4° core, 300 km range, 1° grid, M=8000, K-controlled;
`scripts/diag_crossseam.py`). The conclusion is physically robust (independent-core tiling destroys
cross-seam correlation, worsens with seam count, cores do not rescue it — confound killed), but exact
universality across ranges/densities is one-fixture-based. The predicate's `joint_tol` / `marg_tol` /
`n_star_joint` are named, swappable defaults that absorb regime variation.
