/superpowers-extended-cc:brainstorming

GOAL: design "Phase 13 — structured observation error": replace the single scalar
R = (0.03 m)² with (i) PER-MISSION noise variances and (ii) ALONG-TRACK-CORRELATED
error components per pass, for the flagship MIOST method, at box scale, judged by the
existing instrument suite. Motivating evidence, all on the record: R is the last crude
approximation in the method core (one scalar, six very different instruments); the
Phase-11 retro measured MIOST's track-oriented spectral excess at 0.410 log10 (s3a) —
track-correlated residual error is EXACTLY what a scalar R cannot suppress and a
structured R is designed to absorb; and the capability is the prerequisite machinery
for SWOT swath assimilation (roll/phase/timing errors are per-pass structured
components — same algebra, different geometry). This is a design session: clarifying
questions one at a time, then design sections in batches for my review, then commit the
spec to docs/superpowers/specs/2026-07-18-phase13-structured-r-design.md, PUSH, and
STOP before writing-plans.

PREREQUISITE (hard): Phase 11 CLOSED and pushed (the instruments this phase is judged
by). Record Phase 12's status (closed / in flight / not started) — the phases are
independent (this phase fits at the FIVE-mission calibration config), but the ship-shape
fork consumes Phase 12's outcome.

GOVERNING INPUTS (read first; verify every repo claim against source):
- The Phase-7 papers brief §on observation errors: what U2021/U2022/B2023 and the DUACS
  lineage actually do about correlated/long-wavelength errors (LWE correction precedent)
  — verify from the brief + extractions, don't assert from memory; the challenge inputs
  are corrected L3, so the target here is RESIDUAL structure.
- The signed Stage-A record (α = 1.0657, log10 ρ = −1.5991, q_slope = 1.4518,
  L_t = 6.006 d) and HOW ρ enters the solve — ρ is the scalar data-vs-prior gauge, so
  per-mission variances RE-PARAMETERIZE part of ρ's role; the entanglement must be
  stated precisely before any lane is designed.
- The solve path: stored-G assembly, Jacobi-PCG, the window/blend machinery, Task-22's
  validated peak model (sizing arithmetic for G growth), the Stage-B perturbed-obs
  sampling + CRN identity (blake2b → ndtri; obs/element keying) + the exactness oracle.
- Phase-10's lane apparatus (nested lanes as frozen restrictions, paired seeds, the
  SEALED band protocol — protocol pre-registered, values computed per consulted pair —
  lexicographic µ→λx, negative-result path) — this phase REUSES it wholesale.
- Phase-11's instruments: GroundTrack (MIOST baseline 0.410, s3a/desc; the standing
  necessary-not-sufficient caveat), SpectralFidelity, the geometry artifact (passes,
  headings, per-mission structure — the SAME pass segmentation this phase's error modes
  are indexed by); the Phase-9 flattening instrument + harness (G_pre anchors; ŝ).
- The five-mission calibration-workhorse rule (Phase-12 constraint 3): fits happen with
  j3 held out; c2 locked until the single acceptance touch.

SETTLED CONSTRAINTS (design inside these):
1. MECHANISM = STATE AUGMENTATION (bring the alternatives as a fork, but this is my
   strong leaning, argue against it only with arithmetic): per-pass error coefficients
   join the coefficient state with their own diagonal prior — R_effective =
   diag(per-mission σ²_m) + B Λ B^T realized by augmenting G with the error-basis
   columns and extending the diagonal prior. Zero solver redesign (columns + diagonal
   entries); stored-G grows by n_passes-in-window × n_modes (~5–10% — re-derive with
   the sizing arithmetic + the pass counts from the Phase-11 geometry artifact); Jacobi
   preconditioner extends trivially. This is the wavelet-dictionary pattern applied to
   nuisance structure — and the SWOT-shaped algebra.
2. BOX-CHORD PHYSICS recorded (it nearly settles the basis fork): a pass chord through
   the 10° box is ~1100–1500 km; classical long-wavelength orbit/environmental error
   (once-per-rev scales) manifests in-box as ≈ CONSTANT + TILT per pass segment. The
   basis fork therefore starts at {bias, tilt} per pass with anything richer needing
   evidence, not taste.
3. NESTING, the identity discipline (Phase-10 verbatim): one parameterization; lanes as
   frozen restrictions; the constant restriction (all σ²_m = R_ref, all mode variances
   = 0) reproduces the SHIPPED product EXACTLY — the augmented columns vanish from the
   solution at zero prior variance; identity test at rtol 1e-12 on all four routes vs
   the signed artifacts, mean maps bit where achievable. Lane-0 = the SIGNED config
   (its record already exists — spend nothing re-proving it; the lane apparatus quotes
   it).
4. TUNING inside the scalar-box invariant: every new knob is a scalar (per-mission
   log-variances, mode prior log-variances — ~6–8 new dims). The frozen-vs-reopened
   core question (α, ρ, q_slope, L_t) is a FORK with honest budget arithmetic from a
   Task-0-style probe — the Phase-10 joint-stage lesson (don't freeze what the new dims
   entangle with) cuts against freezing ρ; the budget cuts against a 12-dim joint
   sweep; screening contingency machinery exists. Boxes bracket PUBLISHED per-mission
   noise levels (Ka-band AltiKa low, HY-2A high) with recorded sources — published
   values inform the boxes, the tuner sets the values.
5. VALIDATION + ACCEPTANCE per the standing template: fit/tune/select on the
   five-mission config against j3 (provenance guard active); lexicographic µ→λx with
   the sealed band protocol; pre-registered negative path (no R-lane beats lane-0
   beyond band → record, no touch, "measured not shipped" — the Phase-10 precedent
   verbatim). On a win: full acceptance chain (members, s*/s(x) REFIT on the new
   posterior via the Phase-9 harness — the calibration is not transferable across an
   R change and the substrate exists here, unlike Phase 12), owner gate, ONE c2 touch,
   template tripwires verbatim.
6. SAMPLING CORRECTNESS (load-bearing, easy to get silently wrong): member
   perturbations must be drawn from the SAME structured R the solve assumes —
   per-mission variances AND correlated per-pass components (draw mode coefficients
   per pass, add B·draw to the white per-point draws). The Stage-B exactness oracle
   must be RE-DERIVED for the augmented model and re-proven; the CRN identity extends
   with pass/mode keying (deterministic, collision-free, recorded). A structured solve
   fed white-noise perturbations is a WRONG ensemble that passes every mean test —
   name this hazard in the spec and design the test that catches it (member-variance
   consistency against the analytic augmented posterior on a small case).
7. INSTRUMENT READINGS pre-registered (report-only unless stated): (a) GroundTrack —
   directional expectation DOWN from the 0.410 baseline if track-correlated error is
   real and absorbed (the first pre-registered consumer of the Phase-11 number;
   necessary-not-sufficient stated — a drop is supporting evidence, not proof);
   (b) the flattening/ŝ reading — representation error partially reattributed to obs
   error should LOWER the refit ŝ and may flatten s(x); quantify both; (c) mean-map
   deltas + the c2 regional rows at the touch. µ/λx remain the verdict (bar: µ ≥ 0.85
   floor; λx via the lexicographic rule).
8. IDENTIFIABILITY stated as a design section, not an afterthought: per-pass bias/tilt
   vs long-wavelength field signal is separated by the priors, crossovers, and
   multi-mission redundancy — the mode prior variances are the control; the failure
   mode (signal absorbed into error modes → over-smoothed maps, µ drop) is exactly
   what validation-side selection measures. State the mechanism; design the report-only
   diagnostic (fitted mode-coefficient statistics per mission vs their priors).
9. PROVENANCE + PERSISTENCE: params_key carries the R-spec (structure kind, basis,
   per-mission variances, mode variances); the persisted ensemble kind versions;
   provenance records the R structure; the external-sweep rule applies at any flip.
10. SWOT CAPABILITY CONTRACT stated in the spec (the strategic deliverable): "per-pass
    low-rank structured error components with tunable variances, assimilated via state
    augmentation, sampled consistently in the ensemble" — proven on nadir passes;
    swath geometry swaps in later. SWOT itself OUT OF SCOPE.
11. SHIP SHAPE fork consumes Phase 12's status: this phase's acceptance is the
    five-mission-lineage flagship; a six-mission production refresh with structured R
    (re-running Phase 12's frozen-transfer chain on the R-winner) is a RECORDED
    follow-on election with its own touch — never folded in silently.
12. Untouched: protocols, tuner core (scalars only), provenance guard, other methods
    (OI/GMRF/FEM), all prior signed records, Phase-11 instruments' definitions
    (readings consume them; nothing redefines them).

GENUINE OPEN QUESTIONS (bring as forks, one at a time, with a recommendation each):
a. MECHANISM: state augmentation vs block-banded R^{-1} inside PCG vs diagonal-only
   this phase — with the sizing/cost arithmetic done, not asserted.
b. STAGING: D-stage (per-mission diagonal only) → C-stage (add correlated modes,
   JOINTLY reopened) mirroring Phase-10 V→L, vs one joint design — and which core
   params reopen (the ρ entanglement, constraint 4).
c. ERROR BASIS: {bias, tilt} per pass vs +quadratic vs low-order Legendre — starting
   from the box-chord argument (constraint 2); per-mission vs shared mode variances.
d. SAMPLING EXTENSION: the CRN keying scheme for pass/mode draws; the re-derived
   exactness oracle's form; the member-variance consistency test design.
e. LANE + BUDGET DESIGN: lane set, paired seeds, screening, the probe-derived budget,
   band protocol reuse — and the negative-result semantics wording.
f. IDENTIFIABILITY DIAGNOSTIC: what report-only statistic best surfaces
   signal-absorption (mode-coefficient magnitudes vs priors; crossover residuals;
   GroundTrack direction) without becoming a bar.

REQUIRED EVIDENCE DESIGN (in the spec): the pre-registered lane comparison + bands
protocol; the identity/nesting test set; the sampling-correctness test; the instrument
readings with directions stated; the acceptance-chain instantiation (refit s(x), gate,
touch, tripwires); the honest expectation-setter (box-scale gains expected modest; λx
and GroundTrack are where the physics predicts movement; a negative is a publishable
measurement of the residual-error budget's size, not a failure).

OUT OF SCOPE (state, don't build): SWOT/swath data (the contract points at it; nothing
consumes it); cross-track or inter-pass error correlation beyond per-pass modes;
per-mission R for OI/GMRF; global domain; any change to the Phase-11 instrument
definitions; re-tuning the Phase-12 six-mission product (follow-on election only).

PROCESS: superpowers brainstorming flow; verify against source before asserting; design
sections in batches for my review; self-review against this prompt; commit the spec;
PUSH; STOP for owner file review before writing-plans.
