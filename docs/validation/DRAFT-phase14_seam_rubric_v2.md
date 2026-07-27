# Pre-registered verdict rubric — phase-14 spatial seam dispersion (VERSION 2)

**Status: PRE-REGISTERED (Task-18 pattern, spatialized), AMENDED ONCE.**
Committed in Stage 0, BEFORE any tile exists and before any seam number
can be computed. Stage-1 sessions apply these rules mechanically;
deviations require an explicit owner decision recorded at the consuming
gate.

> **VERSION 2, 2026-07-27 — supersedes version 1
> (`docs/validation/phase14_seam_rubric_v1.md`, sealed under seal v1
> `a17ea419…b725c5d2`; that file carries the v1 text unedited).**
> The amendment is the explicit owner decision this document's own
> deviation clause requires, recorded at the consuming gate:
> **`docs/superpowers/2026-07-27-owner-ruling-crn-sigma-rule0.md`, pins
> 32 and 34** (Stage-1 T4 is the consuming gate; the ruling is quoted
> verbatim there). Two changes, both to Rule 0 and to nothing else:
> **(1)** a SECOND, ensemble floor for σ-route verdicts; **(2)** the
> solver floor `F` defined by accuracy target rather than iteration
> budget. The verdict cells, the thresholds, the σ denominator and the
> ORACLE clause are UNCHANGED — the owner explicitly refused raising `m`,
> changing the σ denominator, and retiring the σ instrument.
> Amending a pre-registered instrument has a procedural cost (pin 35):
> this version invalidates the R-01..R-24 coverage segmentation of the
> sealed-instrument table, and the coverage walk is re-run against THIS
> text (Stage-1 T12).

<!-- thresholds: clean_max=1.0 elevated_max=2.5 -->
<!-- amendment_v2: ens_floor_factor=1.07 floor_decades=3 -->

## Definitions

- Adjacent tile pair `(A, B)`: two `TileFrame`s sharing a core boundary;
  their shared blend-overlap region is the 2·overlap strip centred on it.
- `delta(x)` — the MEAN-map disagreement `field_A(x) − field_B(x)`
  evaluated at overlap points `x` (each tile's own solve, before blending;
  the blend hides exactly what this measures).
- `sigma_delta(x)` — the same for member-std maps (σ dispersion).
- **Interior reference dispersion** `D_int` — computable definition:
  `RMS( field(x + s·ê_perp) − field(x) )` over all grid nodes `x` in the
  POOLED core interiors of both tiles (every node ≥ overlap-width from any
  core boundary), where `s` = ONE grid step of the tile solve resolution
  and `ê_perp` = the axis perpendicular to the shared boundary. One
  number per (pair, field kind, era), recorded beside the verdict.
  `delta(x)` itself is co-located (separation zero — two solves, one
  point); `D_int` anchors it against the field's own one-grid-step
  increment, the smallest resolved natural variation. Resolution is part
  of the recorded row, so ratios are comparable only at equal resolution
  (all Stage-1 tiles solve at one resolution — recorded).
- `D_int_sigma` — the same construction applied to the member-std maps.
- **Seam ratio** `R_seam = RMS(delta) / D_int` (mean maps) and
  `R_seam_sigma = RMS(sigma_delta) / D_int_sigma` (σ maps). Ratios are the
  verdict-bearing numbers; the raw RMS values are recorded beside.

## Rule 0 — validity gate (the Task-18 pattern, inherited)

Rule 0 carries TWO floors. A verdict must clear **both** floors that
apply to its route: every route clears the SOLVER floor (0.a); σ-route
verdicts additionally clear the ENSEMBLE floor (0.b). Below either, the
number is still recorded, the row is marked UNMEASURED with the floor
that caught it named, and it is NOT interpreted — never CLEAN.

### Rule 0.a — solver floor `F` (v2: defined by ACCURACY TARGET, pin 34)

A seam verdict is attributable ONLY if `RMS(delta)` exceeds `3 ×` the
recorded solver floor for that pair: floor `F` = max|field shift| on the
overlap when both tiles are re-solved at deeper tolerance. Below that,
report the number, mark the pair **UNMEASURED (solver floor)**, and do
NOT interpret it.

**`F` is defined by the ACCURACY the probe reaches, not by the iteration
budget it is given.** The probe drives the solve a pre-registered number
of decades below the production rtol — **three decades** (the executed
construction, `1e-9` against a production `1e-6`) — with `maxiter` sized
to REACH that tolerance, and the ACHIEVED relative residual recorded
beside the target. The Task-18 "`maxiter +1000`" construction is a floor
ONLY where the reference solve exited at the iteration cap; where the
reference solve converged, more headroom returns the identical answer and
`F` comes out exactly `0`, licensing every verdict vacuously. **A probe
that does not attain the tighter tolerance is a STOP for the owner —
never a fallback to a looser `F`** (a gap between two truncation points
is not a floor, and `3 × F` has no meaning; owner PIN 23).

*The executed Stage-1 T4 probes already conformed to this construction:*
they ran at rtol `1e-9` — three decades below the production `1e-6` —
and CONVERGED (635 / 629 / 678 iterations, 29–31% of the cap), so `F`
was nonzero and measured. **The four T4 verdicts stand UNRECOMPUTED
under this amendment**: pin 34 corrected defective TEXT, not a defective
implementation. (The σ-route cells among those four are re-read under
Rule 0.b below, which is a different amendment with a different reason.)

### Rule 0.b — ensemble floor `F_ens`, σ-route verdicts only (v2, pin 32)

A σ-route verdict is attributable ONLY if
`RMS(sigma_delta) > 1.07 × F_ens`, where

    F_ens = sigma / sqrt(m - 1)

for that pair — `sigma` the σ field's own RMS level over the evaluation
domain, pooled across the two σ fields being differenced, and `m` the
member count behind each. Below that, the row reads
**UNMEASURED (ensemble floor)** and is NOT interpreted.

*Derivation (so the constant is checkable):* a sample standard deviation
from `m` members has relative standard error `1/sqrt(2(m-1))`; the
difference of two INDEPENDENT such estimates therefore has standard
deviation `sqrt(2) · sigma/sqrt(2(m-1))` = `sigma/sqrt(m-1)`. This is
Monte-Carlo noise in the ensemble, present in a perfectly seamless
solve; it is not a property of the tiling.

*Why the σ level is POOLED as an RMS over both fields:* when the two
levels differ, the variance of the difference is
`(sigma_a² + sigma_b²)/(2(m-1))`, i.e. `F_ens` built from
`sqrt((sigma_a² + sigma_b²)/2)` — the pooled RMS, not the arithmetic
mean of the two levels. **Why this matters despite agreeing to 4e-8 on
the T4 numbers:** the two constructions coincide exactly when
`sigma_a ≈ sigma_b`, which is the NULL — and they diverge as the levels
separate, which is the SIGNAL regime. A construction validated only on
the null is not validated where it has to work. (The T4 diagnosis block
used the arithmetic mean, so its `1.1356` is reproduced under either
form but its construction is SUPERSEDED by this one.)

### The attributability factor 1.07 — DERIVED, not chosen

The factor is a QUANTILE of the measured null distribution of
`T = RMS(sigma_delta) / F_ens`, not a margin picked by analogy with Rule
0.a. **The solver floor's `3 ×` does not transfer:** `F` bounds a
DETERMINISTIC quantity, where a 3× margin is a sensible allowance, while
`F_ens` is the EXPECTATION of a sampling statistic whose null is tightly
concentrated. A 3× threshold on `F_ens` would discard any true artifact
below ~2.8× the floor — and at the T4 geometry it left the σ instrument
with no reachable CLEAN or ELEVATED cell at all (see the reachability
condition below).

Derivation (`scripts/phase14_ensemble_floor_factor.py`, recorded at
`phase14.stage1.ensemble_floor_factor_derivation`, no solves):

- **The null is exactly scale-free.** For Gaussian members
  `s = F_ens · sqrt(chi2_{m-1})`, so under the null of no seam
  `T` is the σ²-weighted RMS over effectively-independent nodes of
  `sqrt(chi2_a) − sqrt(chi2_b)` — a function of `m`, `N_eff` and the
  σ-level weights only, never of `sigma`.
- **`E[T] = sqrt(2(1 − c4²)(m−1))` exactly** = `0.99875` at m=100: the
  `sigma/sqrt(m-1)` floor already sits 0.13% ABOVE the exact expected
  RMS. This is the asymptotic-approximation gap, and it is inside the
  margin below rather than ignored.
- **`N_eff` is MEASURED, not assumed:** `22,815` of the strip's `390,915`
  finite nodes (5.84%), from the autocorrelation of a recorded null
  realization (the cross-tile σ difference, which the T4 diagnosis
  established IS pure ensemble noise). Per-axis divisors: time `3.82`,
  lat `1.93`, lon `2.32`. Time matters because the member draws are
  shared across output days; treating 365 days as independent would
  understate the null spread by ~19×.
- **Quantile:** one-sided `0.999` (at most one null σ row in a thousand
  falsely called attributable) gives `1.01322` equal-weight and
  `1.01592` weighted by the recorded σ heterogeneity (weighted effective
  count `16,316`); `1.07 = ceil(1.01592 × 1.05)`.
- **Margin `1.05`, itemized:** Gaussianity of the member perturbations;
  separability of the correlation across (time, lat, lon) in `N_eff`;
  single-realization bias in the measured autocorrelation; the exact-vs-
  asymptotic floor gap above.
- **Validation:** the quantile predictor (per-node moments + a
  Cornish–Fisher term) reproduces DIRECT simulation — 200,000
  replications at `N_eff = 2,000` — to `8.1e-5` relative, and `3.8e-4` at
  `N_eff = 8,000`. Independently, the two RECORDED half-split
  realizations at m=50 (`0.9829`, `1.0036`) fall inside the predicted
  `0.9973 ± 0.0047`, a measurement the simulation never saw.

### Reachability — a STANDING property of this instrument (pin 36c)

    CLEAN is reachable  iff  factor × F_ens  <  clean_max × D_int_sigma

**Every future threshold, factor or floor change is checked against this
condition BEFORE sealing.** A configuration that fails it has no
reachable CLEAN cell: every attributable σ verdict is ELEVATED or worse
and the only other outcome is UNMEASURED — a gate that cannot PASS,
which is the same pathology as a gate that cannot FAIL (§7 discipline 11,
two-sided). Equivalently, in members:

    CLEAN reachable  iff  m - 1  >  (factor × sigma / (clean_max × D_int_sigma))²

**Status at the T4 geometry, recorded plainly: CLEAN is NOT reachable at
m = 100.** `1.07 × F_ens = 0.0039679 m` against
`clean_max × D_int_sigma = 0.0032655 m`. CLEAN becomes reachable at
**m ≥ 148** (at the rejected 3× factor it would have taken m ≥ 1151, an
~8× inflation of a directly costed quantity — every member is a solve).
Note that the unreachability at m=100 is NOT caused by the factor: the
bare floor `F_ens` already exceeds `clean_max × D_int_sigma` by 1.136×,
so **even a factor of 1.0 leaves CLEAN unreachable at this m** — it takes
m ≥ 129. The instrument's σ route at m=100 can therefore return only
UNMEASURED or ELEVATED-and-above; that is a property of the ensemble
size, not of the amendment, and it is an owner item.

**Why this clause exists, stated plainly: at `m = 100` on the T4 seam
geometry the MC floor is `1.136 × D_int_sigma` against a sealed
`clean_max` of `1.0` — so a PERFECTLY SEAMLESS solve reads ELEVATED.**
Without Rule 0.b the σ route is a gate that cannot pass, which is the
same pathology as a gate that cannot fail (§7 discipline 11, two-sided).
The clause makes the instrument honest at every `m` instead of
structurally unable to pass, and it does so without raising `m`, without
changing the σ denominator, and without retiring the instrument — all
three explicitly refused by the owner.

`F_ens` is recorded on every σ row beside `F`, with the `m` it used, so a
future reader can re-derive the threshold from the row alone.

This rubric is ONE-SIDED by design:
`R_seam → 0` means the two solves agree — there is no under-dispersion
failure cell (unlike the Task-18 blend-day ratio, whose expectation was
1); smallness is success here, recorded not flagged.

## Verdict cells (pre-registered thresholds)

Applied to each adjacent pair, each field kind, per era:

- **CLEAN:** `R_seam ≤ 1.0` — cross-tile disagreement is within the
  field's own variability at seam scale. Verdict line "no seam artifact";
  recorded, nothing further.
- **ELEVATED-RECORDED:** `1.0 < R_seam ≤ 2.5` — a visible seam signature,
  bounded. The number is RECORDED in the standing seam rows (report-only)
  and carried to the consuming gate; the pair is NOT rerun or tuned on
  this signal (skill-selection firewall analog). Provenance of 2.5,
  honestly: an A-PRIORI pre-registered factor — the midpoint of the
  phase-4 dropped-edge bound range `C ∈ [2, 3]`, which bounded a
  DIFFERENT metric class (solver-approximation residual ratios); adopted
  here as a pre-registration anchor, not a derived threshold. Owner may
  re-pin it at Gate 0 before any number exists.
- **STRUCTURAL-STOP:** `R_seam > 2.5` — the seam disagrees with the field
  beyond bounded-residual reading. STOP for the owner: the recorded
  options are (i) junction/exact escalation on that pair, (ii) overlap
  widening probe, (iii) accept-with-recorded-number ONLY by explicit owner
  ruling. Never a silent acceptance.

## The seam-ORACLE clause (recorded; no published precedent)

The Stage-1 roster's **seam-pair tile** carries an ORACLE: the same pair
region solved SEAMLESSLY as one frame (the signed-config truth for that
region). The pair's blended field is compared against that seamless truth
(RMS difference on the overlap, and the same ratio construction with
`D_int` from the seamless solve). Published tiling papers do not report a
seam-oracle comparison — this clause is our addition, recorded in the
gap register; its thresholds are the SAME cells above, applied to the
blend-vs-seamless ratio.

## The σ seam question is OPEN, not answered (owner pin 37)

Under Rule 0.b both Stage-1 σ rows — pair AND oracle — read
**UNMEASURED (ensemble floor)**. **Stage 1 therefore has NO attributable
σ-route seam verdict. The σ seam question is UNANSWERED, not answered
clean.** The two mean-route CLEAN cells are the stage's only standing seam
verdicts. Three standing consequences:

- **The oracle/σ cell was CLEAN and is corrected anyway.** Rule 0.b is a
  rule over σ-route verdicts, not a patch for one cell; applying it to a
  PASSING cell is §7's flattering-contamination discipline. That CLEAN was
  in any case already shown contaminated by the shared-origin mechanism
  (predicted `0.002078` against recorded `0.002092`).
- **FIREWALL THE BOUND.** The diagnosis-derived `R ≈ 0.08–0.12` is a
  BOUND under the not-established firewall, **NOT a verdict**. It must not
  appear adjacent to the UNMEASURED σ rows in the Gate-1 pack in any form
  a reader could take as one: label it, separate it, and state explicitly
  that no rubric verdict supports it. This is the likeliest laundering
  path in the stage.
- **The C1→2 contract carries the σ seam question forward OPEN.** Stage
  2 / 2G planning may NOT assume σ seams are clean.

## Recording

Every evaluated pair emits a row
`{pair, era, field_kind, rms_delta, d_int, r_seam, verdict}` under
`phase14.<stage>.seam_rows` — verdicts CLEAN and ELEVATED-RECORDED are
report-only; STRUCTURAL-STOP halts the consuming run. **σ rows
additionally carry the Rule-0.b block** `{sigma_level, m, f_ens, factor,
threshold, attributable}`, so the ensemble floor is re-derivable from the
row alone. **A row corrected under an amendment carries its own
`correction` block** naming the prior verdict, the seal version it was
taken under, and the ruling that corrected it — a verdict is never
silently overwritten. The thresholds in
this document are mirrored as constants in
`sverdrup/validation/phase14_instruments.py`; a unit test pins doc↔code
equality on the numbers (the machine-readable comment near the top is the
parsed source).
