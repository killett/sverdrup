# README refresh — design (2026-07-22)

## §0 Context and staleness basis

`README.md` (317 lines) last changed at `b4878a0` (2026-07-18, the
phase-12 flip; flip-scoped edit only). Content staleness reaches further
back: the Phase-11 evaluator rewiring (closed 2026-07-16) never landed in
it. Everything below was verified against the current tree and the
evidence store — no from-memory numbers:

- Phase-13 close (`e1eda16` flip; acceptance at
  `phase13.miost.c2_acceptance`): five-mission lineage = structured-R
  chain-lane-D winner + refit s(x); µ 0.8588 / σ 0.0812 / λx 151.86 km /
  coverage 0.7361 / χ²_red 0.9803.
- Phase-11 retro numbers (`phase11.retro.*`): GroundTrack repeat-family
  max — regenerated OI 1.233, MIOST 0.410; phase-13 winner 0.331
  (`phase13.miost.readings.direction_row`).
- `pipeline.py:296-311`: `scores` = `{"report_rows":
  build_report_rows(...), "context_keys", "fidelity",
  "blend_transforms", "eval_point_cov"}` (single-tile variant analogous;
  rows skip VISIBLY when required context is absent).
- pyproject `[io]` extra = `xarray`, `fsspec`, `netcdf4` — no
  `requests`.
- `registry.METHODS` = `fem, gmrf, miost-point, oi, trivial`.
- Verified UNCHANGED (no edit needed): Python ≥ 3.12; `rank=20` /
  `grid_resolution_deg=1.0` defaults; the four doc links; cheatsheet
  params; troubleshooting rows; quickstart API signature.

## §1 Constraints

- Preserve the existing style: tight tables, short recorded-findings
  prose, one voice. NO new top-level sections; the two new subsections
  live inside Validation.
- Bloat budget: net README growth ≤ ~45 lines.
- Every number quoted from the evidence store or a committed artifact.
- Deliberate exclusions (recorded): solver internals (PCG
  checkpoint/resume crash-durability) — README documents no solver
  internals anywhere; `miost-point` stays out of the config `method` row
  (the "validation-track only" caveat in the methods table covers it);
  the conda-forge "PR is open" claim left as-is (external state,
  unverifiable from the tree).

## §2 The eight deltas

**D1 — Validation table + falsified lines.** Five-mission row becomes
`sverdrup MIOST (5 missions, calibration lineage, structured R)` with
**0.8588 / 0.0812 / 151.9**. Gap-accounting sentence rewritten:
six-mission re-tuning stays recorded-not-elected; structured/per-mission
R EXECUTED (Phase 13: +0.0015 µ on the five-mission lineage, transferred
validation→c2 at full size — the first recorded Δ-transfer datum); the
six-mission refresh on the R-winner deferred with a bundling rule.

**D2 — `### Structured observation error (per-mission R + error modes)`**
subsection inside Validation, after D5's subsection, ~150 words:
σ²_m = R_REF·exp(δ_m) with δ as gauge-constrained CONTRASTS (mean(δ)=0,
δ_s3a derived, never physical noise) + optional per-pass {bias, tilt}
modes via [G B] state augmentation; proven against a dense oracle (mean
AND variance) and nested to the scalar era; selected via three frozen
restriction lanes under a sealed pre-registered band protocol, the
winner-lane rule taking the simpler modes-absent lane; acceptance
numbers + refit ŝ 8.74 → 5.11; honest findings — the modes measured
real, persistent, COMPENSATING (not absorbing), window-local structure,
so the mode layer ships nowhere and a redesign note is recorded;
GroundTrack 0.410 → 0.331 back-reference (direction confirmed,
necessary-not-sufficient).

**D3 — Methods table `miost` Notes clause:** structured per-mission
obs-error at the method level (`rspec`: δ contrasts + optional per-pass
bias/tilt modes; shipped values in the registry factories). Config
`params` surface unchanged (rspec rides the constructor — the
consumption seam in `methods/miost.py`).

**D4 — Everything else untouched.** Concepts, Quickstart code,
Installation structure, TOC, Troubleshooting, Links: no changes beyond
D6 (Quickstart comment + Output), D7 (extras row), and D8 (config
`method` row).

**D5 — `### Reference-free track-signature validation`** subsection
inside Validation, before D2's subsection, ~120 words: GroundTrack =
per-mission oriented spectral probes at the mission's track
spacing/orientation (geometry-derived) vs a same-|k| isotropic baseline;
necessary-not-sufficient verbatim (a strong track signature proves a
problem; a clean map does not prove correctness); the numbers —
regenerated OI 1.233 (~17× per-mode excess at s3a spacing) vs MIOST
0.410 (~2.6×), drifting probes clean on both; SpectralFidelity
descriptive row (no verdict semantics); wired REPORT-ONLY (never gates).

**D6 — Output section + Quickstart comment.** Output paragraph
rewritten at the same length: `scores` carries `report_rows` (typed
evaluator rows — RMSE/calibration for OSSE, withheld-track RMSE for OSE,
reference-free instrument rows — with VISIBLE skip rows when a row's
required context is absent), plus `fidelity`, blend provenance, and
context keys. Quickstart `print(scores)` comment updated to match.

**D7 — Extras table:** drop `requests` from the `[io]` row.

**D8 — Config-keys `method` row:** `"oi"/"gmrf"/"fem"/"trivial"`.

## §3 Verification

- After edit: re-read the diff against this spec (every delta present,
  nothing else changed); markdown link check on any touched links; the
  two new subsections within their word budgets; net growth within the
  §1 budget.
- No test/code changes — docs-only diff.

## §4 Out of scope

Solver internals; per-pass mode-layer redesign notes beyond the one
sentence in D2; PROGRESS/spec cross-linking beyond the existing Links
section; conda-forge status refresh.
