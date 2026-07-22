# README Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the eight verified deltas (spec D1–D8) to `README.md` — phase-11/13 content + three mechanical corrections — preserving style, net growth ≤ ~45 lines.

**Architecture:** Docs-only. Two tasks on one file: (0) the Validation-section content (table, gap line, tally, two new subsections), (1) the four mechanical corrections + whole-file verification against the spec.

**Tech Stack:** Markdown; verification via git diff + grep.

**User decisions (already made):** scope = numbers + paragraph + dedicated structured-R subsection (option 2); D5 reference-free subsection added after owner's staleness catch; solver internals and conda-forge claim deliberately excluded; investigate-don't-assume sweep completed (S5–S7 found + folded in as D6–D8).

Spec: `docs/superpowers/specs/2026-07-22-readme-refresh-design.md`. Every number below is quoted from the evidence store / committed artifacts (spec §0); the exact old-string blocks below were read verbatim from the current `README.md`.

---

### Task 0: Validation-section content (D1, D5, D2)

**Goal:** Table row + gap-accounting + tally/lineage sentences corrected; two new subsections added inside Validation.

**Files:**
- Modify: `README.md` (Validation section only)

**Acceptance Criteria:**
- [ ] Five-mission table row reads `0.8588 | 0.0812 | 151.9` with the `structured R` label
- [ ] "neither elected" sentence replaced (structured R executed; re-tuning recorded-not-elected; refresh deferred with bundling rule)
- [ ] Tally reads `{miost5: 3, miost6: 1}`; lineage/refit split stated (five-mission = structured-R product with refit s(x); six-mission keeps the frozen-transferred Phase-8 field)
- [ ] `### Reference-free track-signature validation` subsection present (~120 words) with OI 1.233 / MIOST 0.410, necessary-not-sufficient verbatim, report-only
- [ ] `### Structured observation error (per-mission R + error modes)` subsection present (~150 words) with acceptance numbers, ŝ 8.74→5.11, 0.410→0.331 back-reference, the honest mode-layer finding
- [ ] No other Validation prose changed (σ-semantics paragraph, OI verdict, from-source note untouched)

**Verify:** `git diff README.md` shows only the blocks below; `rg -c '0.8588|1.233|0.331' README.md` → each present.

**Steps:**

- [ ] **Step 1: Table row (D1a).** Replace exactly:

```
| sverdrup MIOST (5 missions, calibration-lineage reference) | 0.857 | 0.080 | 156.4 |
```
with
```
| sverdrup MIOST (5 missions, calibration lineage, structured R) | 0.8588 | 0.0812 | 151.9 |
```

- [ ] **Step 2: Gap-accounting sentence (D1b).** Replace exactly:

```
Named future levers — six-mission re-tuning (the §8 decision) and
structured/per-mission R — are recorded, neither elected.
```
with
```
Of the named levers, structured/per-mission R has since been **executed**
(Phase 13, five-mission lineage: **+0.0015 µ**, transferred validation→c2 at
full size — the first recorded Δ-transfer datum); six-mission re-tuning stays
recorded-not-elected, and the six-mission refresh on the structured-R winner
is deferred with a bundling rule.
```

- [ ] **Step 3: MIOST-verdict paragraph (D1c).** Replace exactly:

```
**MIOST verdict: PASS** against its hard floor (µ ≥ 0.85, met at 0.8678 on the
shipped six-mission product; single withheld-CryoSat-2 acceptance touch per
generation, honest tally {miost5: 2, miost6: 1}). The five-mission row remains
the calibration-lineage reference: the s(x) field was fit there (Jason-3 held
out) and transferred frozen to the six-mission product.
```
with
```
**MIOST verdict: PASS** against its hard floor (µ ≥ 0.85, met at 0.8678 on the
shipped six-mission product and at 0.8588 on the five-mission lineage; every
generation pays a single withheld-CryoSat-2 acceptance touch — honest tally
{miost5: 3, miost6: 1}). The five-mission row is the calibration lineage —
since Phase 13 the structured-R product with its own refit s(x) (see below);
the six-mission product keeps the Phase-8 field it received frozen.
```

- [ ] **Step 4: Insert the two subsections (D5 then D2)** immediately after the σ-semantics paragraph's closing sentence ("…this measured one small step, not that one.") and before "The s(x) calibration layer is method-generic (Phase 9)":

```markdown
### Reference-free track-signature validation

Beside the challenge scores, sverdrup carries a report-only instrument family
that needs no reference field. **GroundTrack** probes each mission's imprint
directly: oriented spectral probes at that mission's inter-track spacing and
ascending/descending orientations (derived from the data's own orbit
geometry), scored against a same-|k| isotropic baseline. The reading is
necessary-not-sufficient — a strong track signature proves a problem; a clean
map does not prove correctness. First exercised retroactively (Phase 11), it
discriminates in the physically expected direction: repeat-family max excess
(log10, s3a/desc) — regenerated OI **1.233** (~17× per-mode excess), lineage
MIOST **0.410** (~2.6×); drifting-mission probes are clean on both.
**SpectralFidelity** adds a descriptive in-band wavenumber-slope row (no
verdict semantics). These rows ride the evidence packs and never gate.

### Structured observation error (per-mission R + error modes)

Phase 13 replaced MIOST's scalar observation-error variance with a structured
R: per-mission variances σ²ₘ = R_REF·exp(δₘ) with the five δ identified as
CONTRASTS under a mean-zero gauge (δ_s3a is derived; σ²ₘ is never quoted as
physical noise), plus optional per-pass {bias, tilt} error modes via [G B]
state augmentation — proven against a dense-solve oracle (mean AND variance)
and nested to the scalar era bit-for-bit. Three frozen restriction lanes swept
under a sealed pre-registered band protocol; the per-mission-only lane ships
(the full lane was indistinguishable — simpler lane on tie). Acceptance on the
five-mission lineage: µ 0.8588 (+0.0015, transferred to the withheld track at
full size), λx 151.9 km, coverage 0.7361 with the refit s(x) (ŝ 8.74 → 5.11),
χ²_red 0.980. GroundTrack dropped 0.410 → **0.331** (the pre-registered
direction). Measured honestly: the per-pass modes see real, persistent
track-correlated structure, but its attribution seesaws with the field and is
window-local — the mode layer ships nowhere; a redesign note is recorded.
```

- [ ] **Step 5: Verify + commit**

Run: `git diff README.md | head -120` → only the four blocks above.
```bash
git add README.md
git commit -m "docs(readme): validation section — phase-11 instruments + phase-13 structured R"
```

---

### Task 1: Mechanical corrections (D3, D6, D7, D8) + whole-file verification

**Goal:** Methods-table clause, Output/Quickstart score shape, extras row, config method row; then verify the full diff against the spec budgets.

**Files:**
- Modify: `README.md` (four spots outside Validation)

**Acceptance Criteria:**
- [ ] `miost` methods row names `rspec` (δ contrasts + optional per-pass bias/tilt modes; registry factories)
- [ ] Output section describes `report_rows` + visible skip rows + fidelity/provenance/context keys; Quickstart comment matches
- [ ] `[io]` extras row = `xarray`, `fsspec`, `netcdf4` (no `requests`)
- [ ] Config `method` row = `"oi"/"gmrf"/"fem"/"trivial"`
- [ ] Whole-file: net growth ≤ ~45 lines (`git diff --stat`); every spec delta present; nothing else changed

**Verify:** `git diff b4878a0..HEAD --stat -- README.md` → single file, net ≤ ~45 added; `rg -n 'requests' README.md` → no hit in the extras table.

**Steps:**

- [ ] **Step 1: Methods table clause (D3).** In the `miost` row, replace the Notes cell text:

```
validation-track only: geometry is fixed to the 2021a Gulf-Stream box — run from a clone via the challenge harness (see Validation)
```
with
```
validation-track only (2021a Gulf-Stream box; run from a clone — see Validation); carries structured per-mission obs-error at the method level (`rspec`: δ contrasts + optional per-pass bias/tilt modes; shipped values in the registry factories)
```

- [ ] **Step 2: Quickstart comment (D6a).** Replace:

```
print(scores)  # RMSE vs truth, calibration (reduced chi^2, coverage), ground-track power
```
with
```
print(scores)  # report_rows: RMSE vs truth + calibration (chi^2, coverage) + instrument rows
```

- [ ] **Step 3: Output section (D6b).** Replace:

```
**provenance** (every transform + any `KnownBias`). `scores` is the merged evaluator dictionary:

- RMSE vs truth + calibration (reduced χ², 1σ coverage) for OSSE
- withheld-track RMSE for OSE
- ground-track power (both modes)
```
with
```
**provenance** (every transform + any `KnownBias`). `scores` carries typed
evaluator rows plus product provenance:

- `report_rows` — one row per evaluator: RMSE vs truth + calibration (reduced
  χ², 1σ coverage) for OSSE, withheld-track RMSE for OSE, and the
  reference-free instrument rows — with a **visible skip row** when an
  evaluator's required context is absent (a missing instrument never
  disappears silently)
- `fidelity`, the blend's provenance transforms, and the context keys the
  evaluators consumed
```

- [ ] **Step 4: Extras row (D7).** Replace:

```
| `[io]`    | `xarray`, `fsspec`, `netcdf4`, `requests`, …   | reading NetCDF obs + writing the zarr product |
```
with
```
| `[io]`    | `xarray`, `fsspec`, `netcdf4`                  | reading NetCDF obs + writing the zarr product |
```

- [ ] **Step 5: Config method row (D8).** Replace:

```
| `method`             | `"oi"`/`"gmrf"`/`"trivial"` | reconstruction method |
```
with
```
| `method`             | `"oi"`/`"gmrf"`/`"fem"`/`"trivial"` | reconstruction method |
```

- [ ] **Step 6: Whole-file verification (spec §3)**

Run: `git diff b4878a0..HEAD --stat -- README.md` → net added ≤ ~45.
Run: `rg -n 'neither elected|miost5: 2|0\.857 \||requests' README.md` → NO hits.
Run: `rg -c '0.8588' README.md` → ≥ 2 (table + subsection).
Re-read the full diff once against spec §2: all eight deltas present, nothing else.

- [ ] **Step 7: Commit**

```bash
git add README.md
git commit -m "docs(readme): report-rows output shape, rspec clause, extras + config rows"
```
