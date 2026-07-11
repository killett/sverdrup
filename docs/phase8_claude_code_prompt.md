GOAL: design "Phase 8 — spatially varying uncertainty calibration" for the MIOST ensemble product.
Motivating evidence (measured, Task-19 localized-calibration report): under the global s* = 10.0628,
1σ coverage is ~0.69 in the jet-core north (local chi2 ~1.3) vs 0.79–0.83 in the south (aggregate
0.748 — in band but spatially wrong in both directions); worst month Aug 0.663. Goal: replace the
single scalar with a low-dof spatial field s(x) so coverage is right REGIONALLY, not just on
average. This is a design session: clarifying questions one at a time, then design sections for my
review, then commit the spec and STOP before writing-plans.

PREREQUISITE (hard): Phase 7 is CLOSED — c2 touch 3 signed off, capability-flip commit landed,
pushed. If any of that is pending, stop and say so instead of starting.

GOVERNING INPUTS (read first; settled — do not redecide): the Phase-7 spec §6 (the D6 s-rescale
mechanism + σ-semantics paragraph); the Task-19 gate evidence + localized-calibration table (the
region/month numbers above); PROGRESS Phase-7 close entries incl. the c2 touch tally + one-touch
discipline; distributions/miost_ensemble.py (MiostEnsembleDistribution + the persisted
representation-tagged kind); the provenance guard; eval/calibration.py; the S-path and Γ-path query
routes. Verify every repo claim against source before building on it.

SETTLED CONSTRAINTS (build the design inside these):
1. ZERO RE-SOLVES; mean maps BIT-UNCHANGED. Extend the existing mean-unchanged non-regression test
   to the field-calibrated product.
2. MECHANISM = post-hoc multiplicative field layer on member ANOMALIES at query time:
   a'_i(x) = sqrt(s(x)) · a_i(x). State and TEST the two identities: (i) pointwise positive scaling
   preserves ensemble CORRELATIONS exactly (Cov' = sqrt(s(x)s(y))·Cov ⇒ Corr' = Corr); (ii)
   s(x) ≡ s* reproduces the shipped scalar product exactly (regression identity vs the signed
   Stage-B artifacts). Covariances/derived cross-point uncertainties change by sqrt(s(x)s(y)) —
   intended; fold into the updated σ-semantics paragraph.
3. FIT ON j3 ONLY. c2 stays locked until ONE owner-authorized acceptance touch of the newly
   calibrated product (one touch per accepted product — the standing discipline). Provenance guard
   applies throughout.
4. GATE WORST-CASE-LOCALIZED (invariant 6): the acceptance bars are per-pre-registered-region, not
   aggregate-only. Rubric-before-numbers (the Task-18 precedent): commit the region set + bars
   BEFORE any s(x) is fit.
5. DOF BUDGET ≪ DATA: j3 has 46,780 points (~12k/quadrant, ~18 per 0.2° cell). Raw per-cell fits
   are FORBIDDEN; the parameterization must be low-dof or explicitly regularized, with positivity
   (work in log s).
6. ONE LAYER, ALL PATHS: the field applies identically through S-path grid queries, arbitrary-point
   Γ queries, down-conversion, and sample()/marginal_variance()/covariance() — no per-path
   duplication. The field spec is serialized into the persisted kind + a calibration key
   (reproducible, cache-safe).
7. PROTOCOLS UNTOUCHED (Method/PredictiveDistribution); evaluators unchanged — the distribution
   applies the field internally. NOTE to prevent a confusion: this is a DISTRIBUTION-layer
   calibration field, not a solver parameter — the Phase-5 invariant-12 deferral of lat-varying
   METHOD parameters (LatitudeVaryingProvider et al.) stays intact and is not what this phase is.

GENUINE OPEN QUESTIONS (bring to me as forks, one at a time, with a recommendation each):
a. PARAMETERIZATION of s(x): piecewise-region baseline (the pre-registered quadrant/jet-core
   partition) vs smooth low-order coordinate field vs covariate-based (s as a monotone function of
   a local field the product already has — e.g. ensemble σ or local signal variance as a jet
   proxy) vs coarse grid + smoothing. Compare at least the minimal baseline and one smooth/covariate
   candidate; complexity must pay for itself in held-out-fold coverage, not in-sample chi2.
b. FIT CRITERION: per-region/method-of-moments (chi2_red = 1 locally, closed form — the D6-
   consistent choice) vs likelihood/CRPS-optimal. Report CRPS regardless of the fitter.
c. SEASONAL AXIS: spatial-only now (record Aug 0.663 as a known limitation + future axis) vs
   s(x, month). My leaning is spatial-only this phase; surface the fork with costs.
d. INTERNAL VALIDATION: design the j3 fold protocol (temporal folds — e.g. fit 10 months / verify
   2, rotated — vs spatial folds vs cycle-alternating) that guards against fitting j3's sampling
   pattern; the held-out-fold regional coverage is the design-selection metric.
e. EDGE BEHAVIOR: s(x) outside/near the fitted region (clamp? blend to s*?) and interaction with
   the box boundary — define, don't improvise.

REQUIRED EVIDENCE DESIGN (in the spec): pre-registered region set (existing quadrants + an explicit
jet-core mask definition) and bars — aggregate coverage within 0.6827±0.10 AND every pre-registered
region within a stated band AND the worst region strictly improved vs the scalar-s record (0.69) AND
no region regressing out of band; the j3 fold protocol; the single c2-touch reading, pre-registered
(expect triplet bit-identical to the signed Stage-A values — mean untouched is provable — plus
regional c2 coverage reported).

OUT OF SCOPE (state, don't build): Q(x)/R(x) or any re-solve-based recalibration (method change);
any change to mean maps; reopening Task-20/windowing; spatial multi-tile; per-mission R; seasonal
field unless fork (c) decides otherwise.

PROCESS: superpowers brainstorming flow; verify against source before asserting; design doc to
docs/superpowers/specs/<date>-phase8-spatial-calibration-design.md; self-review against this
prompt; commit; PUSH; STOP for owner file review before writing-plans.