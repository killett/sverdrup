# Pre-registered verdict rubric — phase-14 spatial seam dispersion

**Status: PRE-REGISTERED (Task-18 pattern, spatialized).** Committed in
Stage 0, BEFORE any tile exists and before any seam number can be
computed. Stage-1 sessions apply these rules mechanically; deviations
require an explicit owner decision recorded at the consuming gate.

<!-- thresholds: clean_max=1.0 elevated_max=2.5 -->

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

A seam verdict is attributable ONLY if `RMS(delta)` exceeds `3 ×` the
recorded solver floor for that pair: floor `F` = max|field shift| on the
overlap when both tiles are re-solved at deeper tolerance (maxiter +1000
— the Task-18 floor-probe construction, run once per pair roster).
Below that, report the number, mark the pair **UNMEASURED (solver
floor)**, and do NOT interpret it. This rubric is ONE-SIDED by design:
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

## Recording

Every evaluated pair emits a row
`{pair, era, field_kind, rms_delta, d_int, r_seam, verdict}` under
`phase14.<stage>.seam_rows` — verdicts CLEAN and ELEVATED-RECORDED are
report-only; STRUCTURAL-STOP halts the consuming run. The thresholds in
this document are mirrored as constants in
`sverdrup/validation/phase14_instruments.py`; a unit test pins doc↔code
equality on the numbers (the machine-readable comment near the top is the
parsed source).
