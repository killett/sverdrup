GOAL: design "Phase 12 — production configuration": the shipped MIOST product re-run
with Jason-3 ASSIMILATED (six missions: alg, h2g, j2g, j2n, s3a, j3 — the leaderboard
convention), all parameters FROZEN from the signed record, one acceptance chain, ONE c2
touch. This deletes the held-out-satellite asterisk from every comparison and produces
the apples-to-apples leaderboard number. It is a CONFIGURATION change, not a method or
tuning change — the design work is the transfer semantics, the evidence design for a
product with no validation track, and the ship shape. This is a design session:
clarifying questions one at a time, then design sections for my review, then commit the
spec to docs/superpowers/specs/2026-07-17-phase12-production-config-design.md, PUSH,
and STOP before writing-plans.

PREREQUISITE (hard): Phase 11 CLOSED and pushed (Task-12 banner + both ratifications in
PROGRESS). If not on public HEAD, stop and say so.

GOVERNING INPUTS (read first; verify every repo claim against source):
- The signed Stage-A winner (full-precision params in the Phase-7 record), the shipped
  s(x) field (phase8_field.json, cal_key), STAGE_B seed root, m=100, the shipped factory
  (SHIPPED table entry for "miost").
- validation/run.py + halo_obs (the shared framing helper) + the provenance guard
  (assert_scored_not_assimilated) — the guard is load-bearing this phase: it must
  REFUSE j3-scoring of the six-mission product.
- The Phase-9/10 acceptance TEMPLATE (spec §6 of Phase 9, incl. the Phase-10
  mean-changing adaptation: no prior triplet to reproduce — determinism via content-hash
  of the gate-reviewed maps; generalized window tripwire, one loader both blocks,
  n = 44,844 + year-span; touch mechanics verbatim; external-sweep rule at any
  shipped-semantics flip).
- Phase-11's wiring: build_eval_context + default_registry + build_report_rows; the
  orbit-geometry provider (a six-mission derivation is a NEW artifact — new obs-sha key;
  j3 gets classified and probed like every other mission).
- The challenge's own data layout: verify that j3 is distributed as a MAPPING INPUT by
  the 2021a challenge (our five-mission choice was framework-side, not data-side) and
  where the validation loader currently binds the j3 file — the same file changes ROLE
  for this product, and the config plumbing must express per-product mission roles
  without disturbing the five-mission calibration workhorse.
- Task-22's validated peak-RSS model + measured Phase-7 solve times (train obs grow
  ~20%: ~54,345 → ~65k; windowed G ~0.78 → ~0.95 GB/window — re-derive with the sizing
  arithmetic, no new machinery).

SETTLED CONSTRAINTS (design inside these):
1. EVERYTHING FROZEN; NOTHING REFIT. Solver params = the signed Stage-A winner verbatim
   (full precision); calibration = the shipped s(x) field, cal_key asserted at load;
   windows/blending/CRN identity per the shipped spec; m = 100, recorded seed root.
   There is NO validation track for this product (j3 is assimilated), therefore no
   quantity CAN be refit without a leak — the provenance guard enforces this
   structurally, and the spec states it as the design's central fact.
2. TRANSFER SEMANTICS PRE-REGISTERED: the s(x) field was fit on FIVE-mission residuals;
   six missions reduce representation error, so the transferred field is expected to
   MILDLY OVER-COVER on c2 (the conservative direction). Pre-register that reading:
   coverage bar stays 0.6827 ± 0.10 (the template bar); expected landing above the
   five-mission 0.748; ABOVE-band → HOLD, record, owner call, no refit (a refit has no
   legal substrate — say so). Record the constellation-dependence principle (from the
   Phase-9/10 record) as the reason a production recalibration is FUTURE work requiring
   a redesigned validation strategy, out of scope here.
3. THE FIVE-MISSION CONFIG REMAINS THE CALIBRATION WORKHORSE: every future fit
   (s*, s(x), fold protocols) still runs on the five-mission config with j3 held out.
   The six-mission product SHIPS; the five-mission config CALIBRATES. Both live in
   config, cleanly separated (per-product assimilated-mission lists — already the
   provenance convention); nothing about the five-mission signed record is reopened.
4. PRE-TOUCH EVIDENCE = REFERENCE-FREE + TELEMETRY + DELTAS (no j3-side instruments
   exist for this product — the Phase-11 wiring is now load-bearing, its first
   production consumer):
   (a) GroundTrack + SpectralFidelity report rows on the six-mission mean maps via
       build_report_rows (six-mission geometry artifact; j3's family joins the probes —
       expect repeat-class, the classic Jason track);
   (b) mean-map deltas vs the shipped five-mission product (RMS/max/map, report-only —
       the direct measurement of what j3 buys in map space);
   (c) member-solve telemetry (convergence at the standing caps; the §6.5-style budget
       check re-run cheaply);
   (d) the five-mission product's recorded numbers quoted beside as context.
   The c2 regional/monthly breakdown remains the ONLY localized calibration read —
   report-only at the touch, per the standing pattern.
5. THE ONE c2 TOUCH, template verbatim with the Phase-10 adaptation: fresh owner
   authorization in-task; determinism tripwire = content-hash of the gate-reviewed
   mean+var maps asserted at touch entry (never a re-solve at touch time); window
   tripwire (one loader both blocks, n = 44,844 + year-span); touch mechanics (one
   invocation writes acceptance; corrected runs need the owner flag + dated defect key;
   third refuses); honest per-product tally. The reading: µ ≥ 0.85 hard floor (the only
   µ bar — no promised number; the MEASURED value at matched convention is the
   deliverable, and an honest shortfall vs 0.89 is a more informative record than the
   current asterisked comparison); coverage per constraint 2; (µ, σ, λx) + chi2/CRPS +
   regional rows recorded.
6. SHIP SHAPE per the flagship-supersedes precedent, brought as a fork (my leaning
   recorded): on sign-off, SHIPPED "miost" repoints to the six-mission product (flip
   commit: SHIPPED update + σ-semantics update — transferred-field provenance stated —
   + README/leaderboard-claims update + honest tally + FULL EXTERNAL SWEEP, the standing
   rule's second application); the five-mission product's numbers remain the
   calibration-lineage record, quoted wherever the six-mission headline appears until a
   recalibrated product exists. Artifacts under NEW names/keys (phase12.miost6.*);
   never overwrite the signed five-mission artifacts.
7. EXPECTATION-SETTER recorded: the frozen winner was tuned at five-mission obs
   density; a denser network at frozen ρ may under-exploit the added data — a
   disappointing µ at frozen params MOTIVATES but does not authorize a re-tuning phase
   (which needs a redesigned validation strategy: leave-one-out, or a different held-out
   mission — recorded as the named future decision, with its costs).
8. Untouched: protocols, tuner core, provenance guard, METHODS table, all Phase-8/9/10/11
   artifacts and evidence keys, the five-mission signed record. Zero j3-side evaluation
   of the six-mission product anywhere (guard-enforced + grep-verified at close).

GENUINE OPEN QUESTIONS (bring as forks, one at a time, with a recommendation each):
a. SHIP SHAPE: repoint SHIPPED "miost" (my leaning, constraint 6) vs a parallel
   "miost-prod" entry with the five-mission product retained as shipped. Weigh: which
   product should downstream consumers get by default, and what does the σ-semantics
   paragraph honestly say about a transferred calibration?
b. MISSION-ROLE PLUMBING: the cleanest config expression of per-product roles (train
   set vs validation binding) given the current loader layout — verified against
   source; the five-mission workhorse must be untouched byte-wise.
c. EVIDENCE PACK COMPOSITION: exactly which report-only instruments run pre-touch
   (constraint 4's list is the floor — is anything else cheap and informative, e.g.
   the Tier-3 matched-input similarity row now that inputs actually match CLS's?
   That comparison becomes cleanly interpretable for the first time — my leaning:
   include it).
d. COST + SCHEDULE: derive the run budget from the sizing arithmetic + measured
   Phase-7 times at +20% obs; decide dev-smoke scope (the 12-day pattern) and whether
   the evidence run and the touch re-solve fold into one authorized execution or stay
   two (the Phase-7 precedent kept them separate; weigh against the ~doubled wall
   cost and the determinism tripwire's guarantees).

REQUIRED EVIDENCE DESIGN (in the spec): the pre-registered coverage reading with the
expected direction; the pre-touch pack composition; the touch protocol verbatim with
both tripwires; the flip-commit contents incl. the external sweep; the honest
leaderboard-claims wording (six-mission number as headline, five-mission number as the
calibration-lineage reference, the 0.89 comparison at matched convention).

OUT OF SCOPE (state, don't build): any refit of any parameter or calibration (no legal
substrate — the central fact); re-tuning at six-mission density (named future decision);
structured/per-mission R (the next capability phase); global domain; changes to the
five-mission record; GMRF/OI/FEM.

PROCESS: superpowers brainstorming flow; verify against source before asserting; design
sections in batches for my review; self-review against this prompt; commit the spec;
PUSH; STOP for owner file review before writing-plans.
