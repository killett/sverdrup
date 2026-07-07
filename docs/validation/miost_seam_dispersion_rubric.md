# Pre-registered verdict rubric — Task-18 seam-dispersion diagnostic

**Status: PRE-REGISTERED.** Committed while the full-year run
(`scripts/diag_miost_seam_dispersion.py`, m=50, root=1, rtol 1e-6,
maxiter 2000, floor probe +1000) is still solving — before any headline
number exists. The post-run session applies these rules mechanically; no
new judgment is required to close Task 18. Deviations from this rubric
require an explicit owner decision recorded at the Task-19 gate.

## Definitions (from the diagnostic doc)

- `R` — headline ratio: (worst blend-day spatial-max member std) /
  (median interior-day spatial-max member std). Metric (a).
- `D` — worst-day max|Δ member-std| windowed vs single-window; `S` — the
  std scale (median per-day spatial-max single-window member std).
  Metric (b).
- `F` — solver-floor probe: max|std shift| on the worst blend day when its
  covering windows are re-solved at maxiter +1000 (windowed side only).
- `rel_F = F / (median interior-day spatial-max member std)` — the floor
  expressed in ratio units.
- MC context at m=50: relative SE of a sample std ≈ 1/√(2(m−1)) ≈ 0.101;
  the recorded variance MC error is √(2/(m−1)) ≈ 0.202. CRN correlates the
  two sides of metric (b), so its effective MC error is smaller; the bands
  below already absorb this.

## Rule 0 — validity gate (the Task-11 lesson)

A deviation is attributable ONLY if it exceeds 3× the relevant floor:
metric (a) deviation `|R − 1|` vs `3 × rel_F`; metric (b) `D` vs `3 × F`.
A deviation that fails this is SOLVER-NOISE-DOMINATED: report the number,
mark that metric **UNMEASURED (solver floor)**, and do NOT interpret it.
Remedy (owner picks at the gate): rerun with `DIAG_MAXITER=6000`
(~3× current solve wall) or accept the metric as unmeasured with the floor
recorded. If the floor probe itself failed (floor = nan), treat as
UNMEASURED and rerun the probe alone (cheap: one deep 2-window solve).

## Rule 1 — metric (a), seam dispersion

- **PASS:** `0.90 ≤ R ≤ 1.10` → verdict line "no seam artifact"; attach to
  the Task-19 gate; nothing further.
- **FLAG under-dispersion:** `R < 0.90` and attributable (Rule 0). This is
  the §6.2 residual (blended posteriors differ). Pre-listed owner options
  at the gate: (i) accept-with-recorded-number — the calibration bars at
  Task 19 remain the binding check; (ii) order the CRN-overlap diagnostic
  (fraction of shared elements/obs between the seam's window pair) before
  deciding; (iii) rerun deeper first if Rule 0 was marginal.
- **FLAG over-dispersion:** `R > 1.10` and attributable — same options;
  additionally check the blend partition-of-unity test suite is green at
  the run's commit before believing it.
- FLAG outcomes still CLOSE Task 18 (it is a measurement task); the
  decision lives at the user-gated Task 19.

## Rule 2 — metric (b), variance equivalence

- **BOUNDED:** `D ≤ 0.10 × S` → record; consistent with the Task-20 close
  (windowing cost small; here its variance analog).
- **EXCEEDED:** `D > 0.10 × S` and attributable → record as the VARIANCE
  windowing cost at the D4 point. This does NOT reopen Task 20 (windowed
  ships; the single window is a reference, not a candidate) — it is gate
  evidence for the owner. Note in the doc whether the excess is
  blend-localized (blend max ≫ interior max ⇒ seam mechanism) or uniform
  (interior ≈ blend ⇒ information-pooling mechanism, matching the D4 mean
  result).

## Rule 3 — solver-budget note for Task 19

Whatever the member-batch achieved residuals were (recorded in the doc's
telemetry table), Task 19 re-decides the member budget at the WINNER point
per §6.5 — the D4 point (ρ=10) is deliberately ill-conditioned and its
residuals must NOT be copied forward as the winner's budget. At the winner,
Stage-A solves converged ≤286 iters; Task 19 asserts member-batch
convergence (final residual ≤ rtol) and escalates maxiter if not, rather
than accepting biased draws.

## Rule 4 — closing Task 18

Close when: doc committed with the three (a)/(b)/(c) items + telemetry +
floor; this rubric applied and the applied outcome (PASS/FLAG/UNMEASURED
per metric) appended to the doc's verdict section; PROGRESS updated;
`.tasks.json` task 18 → completed. Sign-off is NOT required to close 18 —
all flagged decisions transfer to the Task-19 gate evidence.
