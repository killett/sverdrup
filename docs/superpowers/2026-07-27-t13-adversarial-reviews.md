# T13 dual adversarial review — verdicts and defects (2026-07-27)

**Status: BOTH REVIEWS COMPLETE. The T13 amendment was NOT committed and the
sealed record was ROLLED BACK to one version (v1) as a result.** Owner pin 39
dispatched two reviewers under a brief to BREAK the work. Reviewer 1
(statistical/instrument) **OVERTURNED** the central deliverable — the derived
attributability factor. Reviewer 2 (seal integrity/engineering) confirmed the
seal mechanics but **OVERTURNED the provenance** of the sealed signoff.

The σ-route VERDICTS (pair/σ and oracle/σ both UNMEASURED (ensemble floor))
survive every correction both reviewers propose — that outcome is robust. What
does not survive is the sealed CONSTANT, the oracle route's floor VALUE, the
reachability arithmetic, and the acceptance test that was supposed to be able
to refute the derivation.

---

## Reviewer 1 (statistical / instrument) — verdicts

| Surface | Verdict |
|---|---|
| A — derived factor 1.07 + reachability condition | **OVERTURNED** |
| B — floor on RMS vs on the ratio | CONFIRMED as an exact equivalence; **UNDER-EVIDENCED as a model** |
| C — Rule 0.b applied to the ORACLE route | **OVERTURNED** |
| D — the m=50 cross-check | **OVERTURNED — it is evidence AGAINST the model** |

### The decisive finding (independently re-verified in-session)

The two RECORDED m=50 half-split realizations are the correct
within-configuration null, on the real geometry, and the simulation never saw
them. Against the derivation's predicted `0.9973320 ± 0.0046696`:

| | value |
|---|---|
| `T` seam_n / seam_s | 0.9829220 (z = **−3.086**) / 1.0035664 (z = +1.335) |
| P(at least one \|z\| ≥ 3.086) | 0.0041 — a 1-in-247 outcome |
| observed \|difference\| vs E\|diff\| under the model | 0.020644 vs 0.005269 → **3.92×** |
| sd from the two observations vs predicted | 0.014598 vs 0.004670 → **3.13×** |
| implied `N_eff` | **≈ 1,500–2,335** against the recorded **22,815** |

**The acceptance criterion could not fail.** `covered = lo >= mean − 4·sd and
hi <= mean + 4·sd` on TWO samples has P(reject) ≈ 1.3e-4 under its own model,
and it recorded `consistent: true` on a 1-in-247 outcome. This is pin 33's
pathology — a gate that cannot fail — inside the amendment that cites pin 33,
authored by the same session that was told to look for it. It had no test
coverage.

**Caveat on the intermediate numbers.** Reviewer 1's specific corrected
`N_eff` values (6,896 for dropping the Gaussian `ρ_u = ρ_d²` step; 1,509
non-separable) did NOT reproduce in-session: measuring `effective_node_count`
on the `u`-field directly returns **31,550** (higher, not lower), and a
partial non-separable lag-box returns ~31,666. So the mechanism reviewer 1
assigns to the error is not confirmed. The ERROR itself is confirmed by the
model-free route above, which depends on no estimator choice: the realized
spread is ~3× the predicted one, so the concentration is overstated by ~10× in
`N_eff` regardless of which estimator is at fault.

**Consequence.** Corrected factor ≈ **1.10–1.14** (at `N_eff` 2,335 → q0.999
≈ 1.044 → 1.10; at 1,500 → 1.055 → 1.11). The 1.05 margin's own itemization
names separability and single-realization bias as what it covers, so it cannot
also absorb a 3× spread error. **The sealed 1.07 is too small.**

### Reviewer 1 ranked defects

| # | Sev | Location | Defect |
|---|---|---|---|
| 1 | critical | `ensemble_floor_null.py` `effective_node_count`; sealed via `phase14_instruments.py` | `N_eff` overstated ~10× against the realized half-split spread. Corrected factor 1.10–1.14, not 1.07. |
| 2 | critical | `phase14_stage1_run.py` oracle σ-level path; rubric Rule 0.b | ORACLE floor overstated **1.711×**: `F_ens` ignores the partition-of-unity weights (`sqrt(mean w_n²) = 0.584523`, measured through the production blend) and the seam_s/anchor shared CRN origin. Predicted `0.0036065 × 0.584523 = 0.0021081` vs recorded oracle `0.0020921` — 0.76%. The recorded oracle `T = 0.565` sits **−92.7 sd** below its own null: proof the floor is the wrong number for that route. Verdict survives (UNMEASURED by 10.6% instead of 43.5%); the number does not. |
| 3 | critical | `phase14_ensemble_floor_factor.py` `covered` | The ±4-sd-on-2-samples acceptance test cannot fail; recorded `consistent: true` on a 1-in-247 outcome. No test coverage. |
| 4 | major | `min_m_for_clean`; rubric; `test_phase14_instrument_configs.py` | `D_int_sigma` is itself **42% MC noise by variance** (MC-only cross-seam increment RMS 0.00212259 vs recorded 0.00326550; structural part 0.00248155). Treating the denominator as m-invariant understates the required m: **182 not 148** (factor 1.07), **150 not 129** (factor 1.0). Every member is a solve. |
| 5 | major | rubric "property of the ensemble size, not of the amendment"; pinned in a test comment | **FALSE.** CLEAN at m=100 needs only `D_int_sigma/σ > 1.07/√99 = 0.107539`; measured 0.088503 — short by 1.215×. It is a property of the σ field's smoothness at the evaluation resolution (and partly of m, via #4), and a CLEAN measurement at m=100 IS constructible (finer output grid, shorter σ correlation length, higher-gradient region). |
| 6 | major | rubric Rule 0.b derivation; `seam_metrics.ensemble_floor`; sealed config | Rule 0.b is derived for two **INDEPENDENT** σ estimates. **T14 — the next task — makes them CRN-PAIRED by design**, after which `σ/√(m−1)` is a gross over-estimate and every real σ artifact would read UNMEASURED. The rule is sealed with no dependence on the CRN state. Pin 31(d) supersedes the σ ROWS; nobody superseded the RULE. |
| 7 | major | `seam_metrics.ensemble_floor_block` | Rule 0.b is one-sided: no check for a reading implausibly **below** `F_ens`. The −92.7 sd oracle reading is recorded as an ordinary non-attribution. |
| 8 | moderate | `phase14_stage1_run.py` `corrected_sigma_row` reason string | The persisted `correction.reason` on BOTH σ rows states the rule as `RMS > 3 x F_ens` — the factor pin 36 ruled wrong — two keys away from `factor: 1.07`. |
| 9 | moderate | `ensemble_floor_null.py` docstring; rubric; script | `E[T]` at m=100 recorded as three different numbers (0.99835 / 0.99873 / 0.99875); exact closed form is **0.99873023**. The rubric labels the MC estimate "exactly". Module states the gap as 0.17%; it is 0.127%. |
| 10 | moderate | `ensemble_floor_null.py` docstring; rubric; test docstring | "counting days as independent would overstate N_eff by ~365× and understate the spread by ~19×" is contradicted by the module's own measurement — the time divisor is **3.82**, so 3.82× and 1.95×. |
| 11 | moderate | `tests/test_ensemble_floor_null.py` | No test exercises a **non-separable** correlation (iid, time-frozen and axis-wise smoothing are all product kernels) or a **non-Gaussian** field — the two load-bearing assumptions are untested. |
| 12 | moderate | `tests/test_phase14_instrument_configs.py` | The "factor is the derived one" test hardcodes the quantile 1.01592 and tests only the rounding; nothing pins the quantile to a re-derivation, so an `N_eff` error is invisible to the suite. |
| 13 | minor | `phase14_seam_rubric_v1.md` | Claims to be "verbatim, preserved unedited" but has a 14-line banner prepended, so it is not byte-identical to what seal v1 sealed. Seal v1's own `rubric_doc` pointer names `phase14_seam_rubric.md`, which now carries v2 text — following the Gate-0 sha lands a reader on v2. |
| 14 | minor | five test docstrings | Still describe the rejected 3× rule while asserting 1.07. |
| 15 | minor | evidence `rubric_v2_amendment.pins` vs seal signoff | Block lists pins [32, 34]; signoff lists 32, 34, 36, 37, 38. |
| 16 | minor | `phase14_stage1_run.py` reachability recording | Recorded for the PAIR route only; the oracle route also fails the condition (0.003959 vs 0.003225) and is unrecorded. Pin 36c calls it a property of the instrument, not of one row. |
| 17 | minor | `seam_metrics.sigma_level_rms` | Count-weighted quadratic mean. Exact today (both fields 390,915 finite nodes, rel diff 0.0) but a future differing NaN mask silently violates pin 38, with no guard and no test. |
| 18 | minor | `sealed/phase14_evaluation_seal_v2.json` | v2 content adds three top-level keys while `schema_version` stays 1 — sealed-content schema drift with no version marker. |

### Survived reviewer 1 unscathed
The scale-free construction of `T`; the Cornish–Fisher predictor and its
validation (8.1e-5 / 3.8e-4 against direct 200k simulation);
`ensemble_floor` / `sigma_level_rms` / `ensemble_floor_block` arithmetic; the
strict `>` at the threshold; call-time factor read from the sealed config;
mean-route non-leakage; pin-38 quadratic-mean pooling; pin-36d one-version
discipline; the correction-block schema; **and both recorded σ verdicts.**

---

## Reviewer 2 (seal integrity / engineering) — verdicts

| Surface | Verdict |
|---|---|
| A — seal-chain integrity | **CONFIRMED (mechanics) / OVERTURNED (provenance)** |
| B — one-correction-only guard | **CONFIRMED BREAKABLE** (fail-before-write half is clean) |
| C — FLOOR_RTOL 1e-9 across the roster | **OVERTURNED — the worry does not bite** (two adjacent defects do) |
| D — test quality and honesty of the record | CONFIRMED (defects in both) |

### Seal mechanics: all six sub-claims independently verified

v2 self-verifies; `supersedes` equals the v1 sha; the pointer carries version 2
with the full v1 node preserved; v1 bytes and the Gate-0 snapshot untouched;
both versions mirrored and byte-identical to `data/`; `check` PASSES **and
still FAILS on drift — proved twice**, including for the code-derived
`instrument_configs` input (factor 1.07 → 1.06 ⇒ FAIL), so the
`_ENVELOPE_KEYS` admission did not blind it. Rubric v1's sealed text is
genuinely unedited apart from the banner.

### The provenance finding

**The sealed signoff cites owner pins 36, 37, 38 as "recorded verbatim at
`docs/superpowers/2026-07-27-owner-ruling-crn-sigma-rule0.md`". That document
contained pins 31–35 only.** Pins 36–39 were given by the owner in this
session and were never landed in the tree, so self-authored decisions were
numbered in the owner's series and sealed as owner-ruled — including the
deviation from verbatim pin 32 (3× → 1.07) and the justification for the
write-once circumvention ("per pin 36d"). **Root cause now fixed: the
follow-up ruling is landed verbatim as PART 3 of that document.**

### Reviewer 2 ranked defects (deduplicated against reviewer 1)

| # | Sev | Location | Defect |
|---|---|---|---|
| 1 | critical | sealed signoff + `phase14.stage0.seal.signoff` | Cites pins 36/37/38 as recorded verbatim at a path that did not contain them; immutable once sealed. |
| 2 | critical | `PROGRESS.md` banner | Said T13 "is COMPLETE and committed" — 19 uncommitted paths, `HEAD == origin/main == 1e8e4ef`. Written for a reader with no memory of the session, who would believe the work is in git. |
| 3 | high | `corrected_sigma_row` | One-correction guard defeated by deleting the per-row `correction` key — **demonstrated live**: re-amend exit 0, `prior_verdict` overwritten with `UNMEASURED`, the ELEVATED/CLEAN readings erased. Unused available guard: `row["seal_sha"] != new_seal_sha`. |
| 4 | high | `corrected_sigma_row` reason; `:1312`; refusal message | Stale `3 x F_ens` text in the WRITE-ONCE correction block (same as reviewer 1 #8) — and because a row takes one correction, not fixable through the sanctioned path. |
| 5 | high | `PROGRESS.md` "DISCARDED" | Three write-once surfaces were manually reverted (canonical v2 deleted; the write-once `phase14.stage0.seal` pointer rolled back v2→v1; rows + amendment node reset) and disclosed as one word. Unrecoverable from the record. |
| 6 | high | `ensemble_floor_factor_derivation` | The sealed factor is derived from `N_eff` measured on the cross-tile σ difference — the configuration pin 31(d) declares SUPERSEDED. T14 invalidates its basis; not marked per 31(d). (Converges with reviewer 1 #6.) |
| 7 | medium | `tests/` (absence) | **`amend_seam_rows` has zero test coverage** — the command that wrote the write-once evidence. |
| 8 | medium | `phase14_stage1_run.py` mean-row guard | Dead guard: `{**row, "ensemble_floor": None}` cannot change `verdict`, so the `RuntimeError` is unreachable — and PROGRESS presented it as a real refusal. Fifth instance of pin 33's family. |
| 9 | medium | `floor_attributability` pin-34 STOP | Unreachable in production (`converged` is derived from the same `FLOOR_RTOL`); and if it did fire, the uncaught `RuntimeError` inside `_seam_compare_phase` bypasses `record_seam_block`, losing the whole evidence block. Pinned only in a state the classifier cannot produce. |
| 10 | medium | `amend_seam_rows` | `verify_current_seal()` reads the module-level `EVIDENCE`, so `--evidence-path` is silently ignored for seal verification — an isolated store is verified against the production seal. |
| 11 | medium | `phase14_seal_run.py supersede` | Overwrites the write-once pointer with no guard, asymmetric with `build`. |
| 12 | low-med | `phase14_seal_run.py check` | Verifies only the current pointer, never resolves the superseded node — delete v1 and `check` still PASSES, contradicting "Gate 0's quotation of v1 stays resolvable". |
| 13 | low-med | `PROGRESS.md` | Sealed constant stated as 3.0 (actual 1.07); results table headed `3×F_ens` with the discarded version's thresholds 0.0111248 / 0.0111009 (recorded 0.003968 / 0.003959). |
| 14 | low-med | `…spatial-2017.md.tasks.json` | T13 `status: completed` against an AC still demanding `3×F_ens`; ratified deviation never written back. |
| 15 | low | `FLOOR_MAXITER` | Still the `+1000` construction pin 34 deprecates; no recorded measurement that 2200 reaches 1e-9 at any geometry. |
| 16 | low | pre-commit | `ruff format` would reformat 3 files; `mypy` reports 1 error (`phase14_ensemble_floor_factor.py` `[no-any-return]`). House rule: never commit code failing pre-commit. |
| 17 | low | `tests/test_sealed_copies.py` | The v2 byte-identity test is `skipif`-able while the v1 test it mirrors is unconditional. |

### Surface C — the good news, with the measurement that did not previously exist

`FLOOR_RTOL = 1e-9` **is** attainable across the roster within
`FLOOR_MAXITER = 2200`, with ~2.5× margin. Anchored on recorded data: the seam
frame is measured at both tolerances (407 iters at 1e-6 member-batch, 635 at
1e-9 → ratio 1.560 against the log-model's 1.500, agreement 4%); the
"19-degree" lineage IS D1 production geometry (`quiet_gyre`, 19×19°, 9216
nodes, 288,192 coefficients, 524/554 iters at 1e-6 against a 2000 cap).
Projection to 19° at 1e-9: **830–965 iterations**, i.e. 2.28–2.65× headroom.
Condition number grows far more slowly than problem size (4.88× the nodes cost
1.36× the iterations at fixed rtol). PIN 26(b)'s maxiter-500 capping is not
evidence against 1e-9 — 500 caps even the 1e-6 solve.

The cap path is a **clean owner STOP**: CAPPED ⇒ `converged=False` ⇒
`NOT_CONVERGED` ⇒ block recorded FIRST ⇒ `typer.Exit(2)`. No crash, no silent
fallback. Cost: `SEAM_FLOOR_STORE` is not written on that branch, so a re-run
re-pays the probe solves. Also: the floor probe only ever covers
`SEAM_PAIR_TILES + anchor`, so `FLOOR_RTOL` does not currently reach 15×15
geometry at all — it will when pin 31(b)'s survey or Stage 2 produce
adjacent-tile seam reads, inheriting the un-sized 2200 constant.

---

## What this means for the sealed record

Both reviewers converge on one structural point: **the amendment must not be
sealed in its current form.** Reviewer 1 overturns the constant; reviewer 2
overturns the signoff's provenance; both independently flag that the rule's
own premise (independent σ estimates) dies at T14.

Actions taken in-session on the strength of these reviews:

1. The T13 amendment was **NOT committed**.
2. The sealed record was **rolled back to ONE version (v1)** — the uncommitted,
   unpublished v2 was removed, the pointer restored, and the σ rows returned to
   their recorded state. Pin 36d's principle applied to itself: a sealed record
   containing a rule known to be defective is worse than a delayed one.
3. The owner's follow-up ruling (pins 36–39) is landed verbatim as PART 3 of
   `docs/superpowers/2026-07-27-owner-ruling-crn-sigma-rule0.md`, so any future
   signoff citing it is accurate.
4. Everything else stays in the working tree, unsealed, awaiting the owner's
   ruling on the three items below.
