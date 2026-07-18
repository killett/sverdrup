# Phase 12 — Production configuration: the six-mission MIOST product

**Date:** 2026-07-17
**Status:** Design approved in-session (four forks ruled + three review batches);
awaiting owner file review before writing-plans.
**Prerequisite (verified):** Phase 11 CLOSED and pushed — Task-12 banner + both
ratifications in PROGRESS.md; HEAD `86bdf07` == `origin/main` at session start.

---

## 0. Goal and the central fact

Phase 12 re-runs the shipped MIOST product with Jason-3 **assimilated** — six
missions `alg h2g j2g j2n s3a j3`, the leaderboard convention. This is a
**configuration change**: no method work, no tuning, no refit. One acceptance
chain, ONE c2 touch. It deletes the held-out-satellite asterisk from every
comparison and produces the apples-to-apples leaderboard number.

**The central fact the whole design hangs on:** this product has NO validation
track. j3 — the project's only validation instrument — is assimilated.
Therefore no parameter or calibration quantity CAN be refit without a leak;
`assert_scored_not_assimilated` (`src/sverdrup/validation/provenance_guard.py`)
enforces this structurally: the product's derived six-mission
`assimilated_missions` attr makes every j3-scoring attempt refuse at the interp
site. Freezing everything is not discipline layered on top of the design — it
is the only legal configuration.

Data-side verification (this phase's kickoff requirement): the 2021a challenge
distributes `dt_gulfstream_j3_phy_l3_20161201-20180131_285-315_23-53.nc` in
`dc_obs/` beside the five assimilated missions and c2 — j3 is a **mapping
input** by the challenge's own layout. Our five-mission choice was
framework-side, not data-side. The loader agrees: `MAPPING_MISSIONS`
(`src/sverdrup/validation/input_adapter.py:33`) already admits j3; only c2 is
refused by the withheld-leak guard.

## 1. Product definition — frozen configuration

Everything frozen; nothing refit. All values verified against source this
session.

| Quantity | Frozen value | Source |
|---|---|---|
| Solver params (Stage-A winner, verbatim full precision) | `spacing_alpha` 1.0656719505786896, `log10_rho` −1.5990709075704217, `q_slope` 1.4518111273646355, `l_t_days` 6.00630128569901 | `data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json` — `winner.params` == `stage_b.winner_params` |
| Calibration | shipped s(x) field (clipped low-order polynomial), `cal_key` asserted at load | `data/2021a_ssh_mapping_ose/ours/phase8_field.json` |
| Ensemble | m = 100; seed root = `derive_seed("miost", "stage-b-winner", "members", 0)` = **4836134738817689931** (exact integer) | stage-B record |
| Solver budget | caps [500, 2000, 8000]; `pcg_rtol` 1e-6; Phase-7 record converged at maxiter 500 | stage-B record |
| Windows / blending / CRN | shipped-spec identity — 9×60-day windows, identity-keyed perturbations | Phase-7 spec |
| Train obs | six missions through the SAME train loader (`load_mapping_obs`); no special-casing of j3 | `input_adapter.py` |

**Big-int hazard (recorded incident):** the seed root printed as
…690000 when routed through jq (float round-trip). The spec carries the exact
integer; implementation adds a literal-equality test
`derive_seed("miost", "stage-b-winner", "members", 0) == 4836134738817689931`
(int `==`, no float path), and evidence tooling never routes big ints through
jq/float for comparison. Python's `json` module preserves the int — the runner
path is safe; the hazard is display/comparison tooling. The seed root is the
only big int in play.

**Artifacts and naming (fork-a pin 4, two-generation naming):** evidence keys
`phase12.miost6.*`; new artifact file names; nothing five-mission overwritten.
Stable names in prose and artifacts: **miost6** = production flagship,
**miost5** = calibration-lineage reference. The README product table names both
with their numbers.

## 2. Mission-role plumbing (fork b — ruled, with pins)

**Decision:** new phase12 scope cfg JSON following the existing per-run
scope-cfg convention, with the **declared-absence upgrade**.

1. **Explicit null, not key-absence** (the kernel=None precedent): the phase12
   cfg carries `"val_track_path": null` + `"no_validation_reason":
   "j3-assimilated"`, schema-validated. MISSING key = schema error (accidental
   omission caught as itself); NULL = the declared production state. Every
   validation-flavored refusal quotes the declared reason. `c2_track_path`
   present for the one touch. Grep-verify at implementation that NO consumer
   supplies a default for the key — a `.get(..., default)` would convert
   absence into silent j3-binding, which is the leak.
2. **Refusal tests** on the enumerated validation-flavored entry points — the
   s-fit harness descriptor (`harness.py`, `cfg["val_track_path"]` consumer),
   the localized-calibration diag, any scorer bound to a validation track:
   each, handed the phase12 cfg, refuses with the declared-reason error.
   Defense-in-depth: the phase12 runner never calls them; future misuse fails
   loudly.
3. **j3 enters through the same train loader** as the other five missions — no
   special-casing, no validation-loader reuse. Train-suitability of the
   distributed j3 file confirmed by the §0 data-layout verification.
4. **Derived roles confirmed by test:** `_assimilated(obs)`
   (`validation/run.py`) derives the provenance attr from obs actually fed —
   never a hand-written list. Tests pin: (i) the six-mission product's attr
   lists exactly the six; (ii) `assert_scored_not_assimilated` fires on
   j3-scoring of this product; (iii) c2 scoring is permitted (c2 ∉
   assimilated). Five-mission cfg files + module constants byte-untouched,
   asserted by the phase-close diff check (§10, scope enumerated there).

Rejected-for-the-record: registry-level mission lists (roles live at the run
layer; migrating them touches the workhorse's call sites); mission-list helper
mid-freeze (recorded instead as named POST-FLIP cleanup — a shared
`missions_to_paths` for future configs; five-mission files migrate only with
their own tests, never mid-freeze).

**Constraint restated:** the five-mission config remains the calibration
workhorse — every future fit (s*, s(x), fold protocols) runs on it with j3
held out. The six-mission product SHIPS; the five-mission config CALIBRATES.
Nothing about the five-mission signed record is reopened.

## 3. Transfer semantics — the pre-registered coverage reading

The s(x) field was fit on FIVE-mission residuals. Six missions reduce
representation error, so the transferred field is expected to **mildly
over-cover** on c2 — the conservative direction. Pre-registered before the run:

- **Bar:** coverage ∈ 0.6827 ± 0.10 (the template bar, unchanged).
- **Baseline referent (owner-ruled):** **0.7350** — precisely
  `phase8.c2_acceptance.aggregate_coverage_1sigma` = 0.7350370172152351, the
  Phase-8 touch-2 aggregate of the FIELD-calibrated shipped product;
  like-for-like for a transferred field. **0.7481** (0.7481045401837481,
  scalar-s* calibration bars at the Stage-B touch) is quoted beside, labeled
  scalar-era. The kickoff's "0.748" is annotated as resolving to the
  scalar-era row (kickoff error, owner-owned).
- **Expected direction:** landing ABOVE 0.7350.
- **Mechanism, stated honestly (pre-registered):** the formal posterior
  contracts modestly (prior-dominated regime, +20% obs) while true error
  shrinks by gap-filling the dominant representation term ⇒ net direction UP.
  An expectation, not a guarantee.
- **Headroom arithmetic, on record:** 0.7350 → band top 0.7827 = 4.8 points.
  The ABOVE-band HOLD branch is **live** — an ~0.79 landing is a foreseen
  outcome handled by the branch, not a shock.
- **Cross-track stability context:** the five-mission field measures
  0.7353783668234288 aggregate coverage on j3 (`phase8.fit_run.bars.
  bar1_aggregate_coverage`) vs 0.7350370172152351 on c2 — track-to-track
  transfer already demonstrated; mission-set transfer is the new step.
- **ABOVE-band branch:** HOLD, record, owner call on disposition — **no
  refit; a refit has no legal substrate** (the §0 central fact, stated in
  those words).
- **Constellation-dependence principle** (Phase-9/10 record) is the reason a
  production recalibration is FUTURE work requiring a redesigned validation
  strategy. Out of scope here.

**σ-semantics paragraph structure (fork-a pin 3, pinned):** s(x) FIT on the
five-mission configuration (j3 held out), TRANSFERRED FROZEN to this product;
expected-direction note (constellation dependence → mild over-coverage,
conservative); MEASURED c2 coverage + regional rows = THIS product's
calibration record (the five-mission table cited as methodology context, not
as this product's evidence); correlation structure preserved;
"transferred-and-verified" stated in those words.

## 4. Pre-touch evidence pack (fork c — ruled, with pins)

No j3-side instruments exist for this product; the pack is reference-free +
telemetry + deltas. **The Phase-11 wiring is the delivery vehicle — its first
production consumer.** All rows report-only, no verdict semantics.

**(a) Reference-free rows.** GroundTrack + SpectralFidelity on the six-mission
mean maps via `build_eval_context` → `default_registry` → `build_report_rows`.
NEW six-mission geometry artifact (new obs-sha key, v3 schema, classifier
evidence embedded); j3 classified and probed like every other mission.
Pre-named reading notes: the j3-family row is the new-information row (first
probe at the classic Jason wavevector; s3a's 0.410 is the comparison class;
MIOST's five-mission 0.410 is the standing baseline, quoted beside). No
cross-product j3-probe machinery is built — the builder's provenance-selection
stays clean; the five-mission product legitimately has no j3 probes.
**Gap rider:** `classify_orbit` refuses on RATIO_GAP (0.14, 0.431)
(`src/sverdrup/eval/phase11_constants.py:55-56`). Family-level provenance for
both endpoints: the lower edge is the Task-12 ruling's 0.14 verbatim — no
family measures 0.14; the v2-era geometry reading (sha 84e8a19bfe4e) showed
j2n ≈ 0.14, refined by the v3 full 10-family measurement to a repeat-side max
of 0.095238 = j2n/desc, comfortably below. The upper edge 0.431 pins just
inside the measured drifting-side min 0.431953 = alg/desc (the ruling's
rounded 0.44 would table the very missions it ratified). A j3 landing inside
the gap TABLES an owner decision — the Phase-11 rider working, not a blocker.

**(b) Mean-map deltas** vs the shipped five-mission product: RMS/max/map —
the direct measurement of what j3 buys in map space.

**(b′) σ-map delta as a pre-registered STRUCTURAL SIGNATURE (fork-c pin 1):**
expected = variance reduction concentrated along the j3 ground track (the
Phase-8 theorem as a prediction, not a hazard). Report RMS/max/map of Δσ plus
the track-localization read. **ABSENCE of the j3-track imprint = STOP and
attribute before any touch** (config-not-changed / framing class; the Phase-7
0.16 m attribution precedent cited). The over-reading worry is recorded as
resolved by pre-registration.

**(c) Member-solve telemetry:** convergence at the standing caps
[500, 2000, 8000], `pcg_rtol` 1e-6; the §6.5-style budget check re-run
cheaply — smoke-measured per-window wall + peak RSS fed into the Task-22 peak
model, arithmetic recorded in the evidence (fork-d pin 2).

**(d) Five-mission numbers quoted beside as context:** µ 0.8572611954190728,
λx 156.42996684578844 km, coverage 0.7350 (field-calibrated aggregate) with
0.7481 scalar-era beside, Tier-3 rows.

**(e) Tier-3 matched-input similarity row (fork-c pin 2):** pre-registered
anchor = the Phase-7 j3-assimilating variant, row (b) of
`docs/validation/miost_tier3_similarity.md`: mean RMS **0.0472 m**, coherence
0.761@100 / 0.856@150 / 0.930@200 km — same configuration, recorded before
this phase existed. Tight-agreement expectation, not bit (framing-era input
details differ); deviation = attributed, not shrugged. **Two-row collapse
stated:** with inputs matched, the shipped-product row ≡ the matched-input row
for THIS product; the mismatch caveat is retired here; the five-mission record
keeps its two-row form. Standing caveat restated: similarity to CLS ≠ quality
— their maps are not truth; report-only.

The c2 regional/monthly breakdown remains the ONLY localized calibration read
— report-only at the touch, per the standing pattern.

**Dev smoke (12-day pattern) — explicit job list (fork-d pins 3–4):**

1. Guard-refusal demonstration: j3-scoring of the six-mission smoke map
   refuses via `assert_scored_not_assimilated`.
2. Null-val schema validation (declared-null cfg round-trip; missing-key =
   schema error).
3. Geometry artifact ASSERTED present with j3's classification outcome — the
   artifact derives ONCE, at its own pre-run task (§10 T4), where the gap
   rider fires and blocks there if tabled. The smoke asserts presence +
   outcome; it does not re-derive. One derivation, one rider evaluation point.
4. **CRN shared-mission assert** (free config-correctness check):
   identity-keyed perturbations ⇒ the five shared missions' draws are
   bit-identical across products — the smoke replays one shared mission's
   draws against the five-mission derivation and asserts equality.
5. Per-window wall + peak RSS measured → full-run budget derived from the
   measurement + the Task-22 peak model BEFORE launch.
6. Evidence-dest isolation: `phase12_dev_smoke` key, never the gate key (the
   Phase-8 fixture-leak lesson).

## 5. The one c2 touch — template verbatim + Phase-10 adaptation

Template = Phase-9 spec §6 mechanics with the Phase-10 mean-changing
adaptation (no prior triplet to reproduce; determinism via content-hash of the
gate-reviewed artifacts).

- **Fresh owner authorization in-task:** `SVERDRUP_MIOST_C2` exact-string-"1"
  pattern; no standing authorization; smoke runs can never spend the touch.
- **Determinism tripwire — closed input set (fork-d pin 1):** the touch
  consumes mean maps + var maps + the MEMBER STORE (the calibration read
  queries members, not just gridded maps) + the cal field `cal_key`. ALL
  hashed at touch entry, asserted equal against the hashes RECORDED in the
  reviewed evidence pack's provenance rows — end-to-end "owner reviewed
  exactly this," not convention. Never a re-solve at touch time.
- **Window tripwire:** one loader both blocks; n = 44,844 + year-span
  asserted.
- **Touch mechanics verbatim:** one invocation writes acceptance; corrected
  runs need the owner flag + a dated defect key; a third refuses.
- **Honest per-product tally:** miost6 tally 0 → 1 at the touch; miost5 tally
  stays 2 (touch 1 = disclosed defect run, touch 2 = accepted), quoted beside.
- **The reading:** µ ≥ 0.85 hard floor — the ONLY µ bar; no promised number.
  The MEASURED value at matched convention is the deliverable; an honest
  shortfall vs the 0.89 comparison is a more informative record than the
  current asterisked comparison. Coverage per §3. Recorded: (µ, σ, λx) +
  chi2/CRPS + regional/monthly rows.

### P0 adjudications (the register's own trigger fires this phase)

Register: `docs/hygiene-priorities.md`, section **"P0 — evidence-integrity
hazards. Decide BEFORE any future evidence or gate rerun"** (full findings in
`docs/hygiene-notes.md`). Phase 12 is that future evidence/gate rerun; both
entries are adjudicated here, traceably.

**P0-1 (register entry 1): unguarded inline c2 touch —
`scripts/stage_miost_gate_run.py:801-817`.** Adjudication: **DISARM, in-phase,
BEFORE the evidence run** (§10 T1). Verified worse than labeled: the legacy
env-branch OVERWRITES the signed `sb["c2_acceptance"]` with scalar-era
semantics. Fix: the `== "1"` branch becomes a refusal naming `--c2-touch` +
the template mechanics; the READY early-return is preserved; guard-fires test
(env set → refusal; c2 file + signed key untouched). This disarm is the
phase's ONE deliberate edit to legacy-script territory (see §10 diff-check
scope).

**P0-2 (register entry 2): Stage-B evidence clobber path —
`scripts/tune_miost_inflation.py:117`.** Adjudication: **LEAVE-ON-QUEUE,
hardened.** The script does not run in Phase 12 (nothing is refit — no legal
substrate). The queue entry is upgraded to a pre-registered **BLOCKING
PRECONDITION**: any future plan invoking `tune_miost_inflation` or writing
`stage_b_*` canonical names fixes it first (named edit to
`docs/hygiene-priorities.md` in §10 T1). Detection is already covered by the
sha-anchored external pins (loud at the next sweep). The phase-12 runner
carries the anti-clobber discipline by construction — incremental writes,
`phase12.miost6.*` keys only, defect-key preservation semantics per template,
no shared write path with any five-mission evidence — pinned by test:
phase12-named writes only; sibling keys survive the JSON merge (named
acceptance criterion in §10 T5).

## 6. Ship shape + the flip commit (fork a — ruled, with pins)

**Decision:** on sign-off, SHIPPED `"miost"` repoints to the six-mission
product (flagship-supersedes precedent). Rejected-for-the-record: a parallel
`"miost-prod"` entry — the purity distinction is fit-lineage, not validation;
its price is permanent default-consumer ambiguity, the disease the role-split
cured.

1. **Conditionality spelled out — a branch, not a schedule.** The repoint
   happens ONLY on owner sign-off. Pre-registered branches: coverage above
   band → HOLD, SHIPPED untouched, six-mission disposition tabled for owner
   decision (ship-with-recorded-over-coverage vs not); µ < 0.85 → bar fails,
   no flip, the finding stands (frozen-ρ-at-higher-density — informative,
   recorded).
2. **External-pin + consumer migration is flip-task content** (the Phase-8
   stale-pin lesson applied in advance): enumerate every `SHIPPED["miost"]`
   consumer and every external pin bound to the five-mission product;
   five-mission pins re-target a named, still-constructible five-mission
   factory (the calibration workhorse keeps a FACTORY, not just a config);
   NEW external pins for the six-mission shipped product captured at flip;
   the FULL external sweep (standing rule, second application) runs green in
   the flip commit — planned, not discovered. The census + retargeting design
   land BEFORE the evidence-run review (fork-d pin 5; §10 T3).
3. **σ-semantics paragraph** per §3's pinned structure.
4. **Two-generation naming** per §1; README/leaderboard-claims update: the
   six-mission number is the headline at matched convention vs the 0.89; the
   five-mission number is quoted beside as the calibration-lineage reference
   wherever the headline appears, until a recalibrated product exists.

**Flip commit contents (one commit):** SHIPPED update + σ-semantics update +
README/leaderboard-claims update + honest tally + new/retargeted external
pins + FULL external sweep green.

## 7. Cost + schedule (sizing arithmetic re-derived; no new machinery)

**Memory** (Task-22 validated component-sum model; measured conservatism
1.08–1.11×): train obs 54,345 → ~65k (+20%; exact count recorded at smoke).
nnz ∝ n_obs ⇒ windowed G 0.78 → ~0.95 GB/window; N_coef unchanged (197k
windowed); X+workspace at m=100 ~1.0 GB ⇒ modeled peak **~2.2–2.4 GB** vs
measured `MemAvailable` (~10.8 GB class box). Comfortable; the single-window
variant is not needed and not designed.

**Wall:** five-mission member-gen measured ~1.5–4 h at m=100; member cost ∝
nnz×iters ⇒ **~2–5 h** member-gen; + mean/var reduction + geometry derivation
+ report-row instruments ⇒ one overnight envelope. The dev smoke measures
per-window wall + peak RSS; the full-run budget is derived from the
measurement + the peak model BEFORE launch; the arithmetic is recorded in the
evidence.

**Execution shape (fork d — ruled): one solve, two authorized steps.**
Step 1 (authorized run): dev smoke, then the full-year six-mission solve
producing mean+var maps + the whole pre-touch pack. Owner reviews the pack.
Step 2 (fresh in-task authorization): the ONE c2 touch asserts the closed
input set's hashes (§5), no re-solve, minutes. Honors the Phase-7 separation
(owner sees evidence before c2 is spent) at zero extra wall — the tripwire
makes a second solve unnecessary. Rejected-for-the-record: touch folded into
one execution (evidence review made retrospective — against fresh-auth
discipline); two solves (contradicts the determinism tripwire outright).

**Schedule (order, not calendar):** pre-run tasks (P0-1 disarm; cfg schema +
refusal tests; flip-prep census; geometry derivation) → dev smoke (six jobs)
→ authorized evidence run (overnight) → pack assembly + owner review →
authorized touch (minutes) → the owner's three-branch ruling → flip commit +
external sweep (sign-off branch only).

## 8. Expectation-setter (recorded)

The frozen winner was tuned at five-mission obs density: `log10_rho`
−1.5990709075704217, `spacing_alpha`, `q_slope` all selected against a
sparser network. A denser network at frozen ρ may under-exploit the added
data. A disappointing µ at frozen params **MOTIVATES but does not authorize**
a re-tuning phase. Re-tuning requires a redesigned validation strategy — a
named future decision with named costs: leave-one-out (≈N× tuning cost, N=6
solves per trial) or a different held-out mission (re-introduces a held-out
asterisk, losing the leaderboard convention this phase exists to reach).
Neither is elected here.

## 9. Out of scope (stated, not built)

- Any refit of any parameter or calibration — no legal substrate; the §0
  central fact.
- Re-tuning at six-mission density — the named future decision (§8).
- Structured / per-mission R — the next capability phase.
- Global domain.
- Changes to the five-mission signed record.
- GMRF / OI / FEM.

## 10. Acceptance chain, close checks, task shape

**One chain:** smoke → evidence run → owner pack review → touch → **the
owner's three-branch ruling** → flip / HOLD / no-flip. Every c2-relevant step
under the template's mechanics; both tripwires live; fresh authorization at
each of the two authorized steps.

**T9 is gated on the owner sign-off message, not on the mechanical verdict:**
the touch numbers land → report to owner → the three-branch ruling
(sign-off / HOLD / no-flip) is the owner's act, informed by the pre-registered
reading — the flip executes only on that message (every prior phase's
pattern).

**Phase-close verification (all captured-output):**

- Grep-verified ZERO j3-side evaluation of miost6 anywhere (guard-enforced +
  grep at close).
- **Byte-untouched diff check, scope enumerated:** the five-mission scope cfg
  files + the module constants (`input_adapter.py` mission set, five-mission
  `_MAPPING_OBS_PATHS` constants, calibration constants) diff empty vs
  pre-phase HEAD. The P0-1 disarm is recorded as the phase's ONE deliberate
  edit to legacy-script territory (`stage_miost_gate_run.py`) — it neither
  trips the check nor gets excluded ad hoc; the check's path list simply does
  not include the disarmed script, and the disarm commit is named in the
  close banner.
- Seed-root literal-equality test green (int path; §1).
- Suite green; FULL external sweep in the flip commit (if the flip branch is
  taken).
- PROGRESS close banner + honest per-product tally table (miost5: 2; miost6:
  1).
- Untouched list verbatim: protocols, tuner core, provenance guard, METHODS
  table, all Phase-8/9/10/11 artifacts and evidence keys, the five-mission
  signed record.

**Task-shape sketch (input to writing-plans, not binding):**

- **T1** — P0-1 disarm (red/green: env set → refusal naming `--c2-touch`;
  READY early-return preserved; c2 file + signed `sb["c2_acceptance"]` key
  untouched) **+ the P0-2 queue-entry hardening edit** (blocking-precondition
  wording into `docs/hygiene-priorities.md`).
- **T2** — phase12 cfg schema + declared-null + refusal tests + no-default
  grep.
- **T3** — SHIPPED-consumer census + external-pin retargeting design
  (flip-prep, lands before the evidence-run review).
- **T4** — six-mission geometry artifact: the ONE derivation; j3's first
  classification; the gap rider fires here and blocks here if tabled.
- **T5** — runner: solve + evidence pack, dest-isolated; CRN shared-mission
  assert; **named AC: anti-clobber sibling-survival test** (phase12-named
  writes only; sibling keys survive the JSON merge).
- **T6** — dev smoke (six-job list, §4) + budget derivation.
- **T7** — authorized evidence run + pack assembly → **OWNER GATE** (pack
  review).
- **T8** — authorized touch → numbers reported → **OWNER GATE** (three-branch
  ruling).
- **T9** — flip commit + external sweep — executes ONLY on the owner's
  sign-off message (see above).
- **T10** — phase close (checks above; PROGRESS banner).

Owner gates = user-gates with evidence axes, per standing discipline.
