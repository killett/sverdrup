GOAL: design "Phase 11 — evaluator wiring": exercise the reference-free half of the
evaluation architecture that has existed since the early phases but has never produced
a number in any acceptance evidence pack. Deliverables: (1) GroundTrack rebuilt to earn
its declaration; (2) a new spectral-FIDELITY evaluator; (3) evidence packs consume
Registry.applicable for report-only rows; (4) a RETROACTIVE one-shot on the shipped
MIOST and signed OI mean maps, numbers recorded; (5) the lexicographic selection logic
extracted to ONE Policy seam (rule of three is met). This is a design session:
clarifying questions one at a time, then design sections in batches for my review, then
commit the spec to docs/superpowers/specs/2026-07-15-phase11-evaluator-wiring-design.md,
PUSH, and STOP before writing-plans.

PREREQUISITE (hard): Phase 10 CLOSED with the pre-registered negative result AND the
four post-close owner rulings recorded in PROGRESS (tuned-constant election DECLINED;
n_lambda_resamples=200 ratified; 12 h budget ratified with the search-scoped wording +
standing rule; MIOST-B DECLINED, invariant-12 thread closed). If any of that is not on
public HEAD, stop and say so. If the ARCHITECTURE-AUDIT FINDING (appendix below) is not
yet in PROGRESS, record it verbatim as this phase's first commit.

GOVERNING INPUTS (read first; verify every claim against source before building on it):
- core/evaluation.py — ContextKey {TRUTH, WITHHELD_OBS, ORBIT_GEOMETRY}, EvalContext,
  Evaluator Protocol, Registry.applicable(context_keys), MetricScope. This is the
  spine; it is NOT being redesigned.
- eval/ — accuracy.py (fires on TRUTH or WITHHELD_OBS), calibration.py, skill.py,
  skill_score.py, resolution.py, groundtrack.py (the stub this phase rebuilds),
  spectral.py (NOTE: this is the shared λx algorithm — Phase-5 invariant 10, one
  algorithm two call sites — NOT a spectral-fidelity evaluator; do not confuse or
  disturb it).
- application/pipeline.py:285,373 — the ONLY Registry consumers today
  (GroundTrack(track_wavenumber=4) hardcoded there).
- The three lexicographic selection sites: application/tuning/objective.py
  (ConstrainedObjective bar-filter + primary sort), application/calibration/folds.py
  (select — lane-0 eligibility + S→T→smooth), application/tuning/lane_compare.py
  (measured-band lexicographic µ→λx with the sealed protocol). The Policy seam must
  serve all three.
- PROGRESS: the Phase-8 localized-calibration theorem record (posterior covariance is
  independent of obs VALUES; ensemble σ tracks sampling geometry) — load-bearing for
  constraint 4 below.
- The shipped artifacts the retro run consumes: the Phase-8 MIOST product's mean maps
  (stage_b mean maps at the accepted config) and the signed OI artifact
  (OSE_ssh_mapping_OURS_OI.nc, mean-only) + the regenerated OI mean maps from Phase 9.

SETTLED CONSTRAINTS (design inside these):
1. REPORT-ONLY PHASE: no bar changes, no rubric changes, no promotion of any new metric
   to gating semantics (the promotion path — report-only → pre-registered bar — exists
   and is NOT exercised here). ZERO c2 anywhere. Nothing ships; registry METHODS/SHIPPED
   tables untouched. Mean maps of every product bit-unchanged (this phase only READS
   products).
2. GROUNDTRACK REBUILD (the declared-but-unread context is an integrity defect):
   - It REQUIRES ORBIT_GEOMETRY and must CONSUME it: derive the probe wavevectors FROM
     the geometry — per-mission inter-track spacing AND ascending/descending track
     orientations (oriented 2-D spectral probes, not a single zonal wavenumber; the
     hardcoded k=4/k=8 dies).
   - The statistic contrasts power at the track wavevector(s) against a LOCAL spectral
     baseline (neighboring wavevectors), never against total power (a red ocean
     spectrum makes power[k]/total uninformative for any k).
   - The class docstring carries the standing caveat verbatim: NECESSARY-NOT-SUFFICIENT
     — a strong track signature proves a problem; a clean map does not prove
     correctness.
3. REQUIRED-CONTEXT INTEGRITY, mechanized: a test asserts every registered evaluator
   consumes every ContextKey it declares (declared ⇒ read). The GroundTrack stub is the
   motivating counterexample; the test prevents the class recurring.
4. MEAN MAPS ONLY for track-signature scoring, with the theorem recorded at the
   evaluator: σ/variance maps LEGITIMATELY carry sampling-geometry pattern (posterior
   covariance independent of obs values — the Phase-8 record); scoring σ maps with
   GroundTrack would "detect" an expected feature. The evaluator refuses or the harness
   never routes σ fields to it — design the guard, don't rely on care.
5. SPECTRAL-FIDELITY EVALUATOR (new, reference-free): wavenumber-spectrum shape sanity
   for mean maps (over-smoothing shows as a steepened/truncated cascade). Scope it
   honestly at the design forks — descriptive-first is my leaning (report fitted slope
   over a pre-registered wavelength band + the along-track obs spectrum slope as
   context when WITHHELD_OBS is present; no verdict semantics in this phase).
6. WIRING = Registry.applicable, one general path: evidence-pack report sections
   (gate runners, the Phase-9 harness) build an EvalContext from what they already have
   (maps, grid, obs geometry; withheld obs on validation side) and run the applicable
   set — no per-runner hand-picked evaluator lists for report rows. Bars and the
   acceptance spine are UNTOUCHED.
7. RETROACTIVE ONE-SHOT (a deliverable, not an afterthought): run the rebuilt
   GroundTrack + spectral-fidelity on (a) the shipped MIOST mean maps and (b) the
   signed/regenerated OI mean maps; record the numbers at a named evidence key
   (phase11.retro.*) with provenance (map shas). These numbers inform the product
   conversation; they gate nothing.
8. POLICY SEAM (behavior-preserving refactor, identity-gated like the Phase-9
   migration): one lexicographic-selection Policy consumed by all three sites.
   HARD GATES: the Phase-8/9 harness-on-MIOST leaf-identical regression must pass
   UNCHANGED (folds.select behavior byte-equivalent); the Phase-10 verdict must be
   reproducible from its persisted records through the new seam; ConstrainedObjective's
   sort order pinned by existing tests. Behavioral pins inviolable; structural asserts
   may track the reviewed shape change (the Phase-9 close principle).
9. Protocols untouched; provenance guard untouched; tuner core untouched; shipped
   Phase-8/9/10 artifacts and evidence keys never overwritten.

GENUINE OPEN QUESTIONS (bring as forks, one at a time, with a recommendation each):
a. ORBIT_GEOMETRY content + provider: what goes in the bag — track headings/spacings
   DERIVED from the obs files themselves (deterministic, pinnable artifact) vs mission
   metadata constants? Per-mission vs constellation-aggregate probes? Where does the
   derivation live and how is it cached/keyed?
b. GroundTrack statistic design: 2-D FFT oriented-wavevector band vs Radon/projection
   along track headings; per-day maps vs the time-mean map vs the temporal-std map
   (each answers a different question — pick and justify); the local-baseline
   definition (annulus? neighboring band?); one number per mission vs one aggregate.
c. Spectral-fidelity scope: wavelength band; slope estimator; descriptive-only vs a
   context-comparison row (along-track obs slope when available); per-day vs
   time-averaged spectra.
d. Wiring surface: which runners gain the report section this phase (my leaning: the
   retro one-shot script + the Phase-9 harness evidence blocks; the historical gate
   runners are closed records — do NOT retrofit their JSONs), and the report-row schema.
e. Policy seam shape: the protocol signature that covers plain sort (objective),
   eligibility + lexicographic (folds.select), and measured-band lexicographic
   (lane_compare) without becoming a framework — smallest interface that serves three
   real call sites.

REQUIRED EVIDENCE DESIGN (in the spec): the retro numbers' key + schema + provenance;
the declared⇒consumed integrity test; the three identity/regression gates for the
Policy refactor (leaf-identical harness, Phase-10 verdict reproduction, objective sort
pins); suite green throughout.

OUT OF SCOPE (state, don't build): promoting any new metric to a bar; OSSE/TRUTH
harness work (dormant until the global ambition; the TRUTH ContextKey stays as-is);
geostrophic-balance/conservation evaluators (recorded as future family members); any
method or product change; c2 access of any kind.

PROCESS: superpowers brainstorming flow; verify against source before asserting;
design sections in batches for my review; self-review against this prompt; commit the
spec; PUSH; STOP for owner file review before writing-plans.

---

## APPENDIX — architecture-audit finding (record in PROGRESS if not already present, dated 2026-07-15)

> ARCHITECTURE-AUDIT FINDING: the evaluator flexibility commitment
> (evaluate(result, context), required_context, Registry.applicable, reference-based +
> reference-free families, vector scores + bars-as-data) was implemented faithfully in
> core/evaluation.py + eval/ — and then Phases 4b–10 built the acceptance spine BESIDE
> it: no gate or tuning path consults the registry; GroundTrack has produced zero
> numbers in any evidence pack; the reference-free family is unexercised. Withheld-data
> became the only OPERATIVE test by wiring drift, not by design. Secondary: GroundTrack
> declares ORBIT_GEOMETRY and never reads it (k hardcoded; total-power normalization
> uninformative on a red spectrum; necessary-not-sufficient caveat undocumented);
> eval/spectral.py is λx infrastructure, not a spectral-fidelity evaluator (none
> exists); lexicographic selection is triplicated (objective sort, folds.select,
> lane_compare) — rule of three met for a Policy seam. Damage: none shipped (accuracy +
> calibration were policed by the full c2/j3 discipline); the debt is an unexercised
> safety net — nobody has measured whether the shipped mean maps carry track-sampling
> signature. Reviewer's note: six phases of gate reviews checked rubric compliance and
> never asked why track_power was absent — pre-registered-rubric auditing catches
> deviations from the plan, not omissions from the vision; periodic audits against
> founding commitments are the countermeasure, and this was the first.
