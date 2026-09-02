# Stage-1 sealed-instrument coverage table (T11 — hard precondition on T4)

> **⛔ STOP CONDITION TRIGGERED — ONE UNASSIGNED NORMATIVE CLAUSE FOUND.**
> The sealed rubric's PRIMARY pair reading — `R_seam` from the PRE-BLEND
> tile-A-vs-tile-B disagreement (`delta(x) = field_A(x) − field_B(x)` on the
> shared overlap; the rubric's own words: *"the blend hides exactly what this
> measures"*) — is assigned to **no task AC in the Stage-1 plan**. T4's only
> pinned seam construction is the ORACLE read (blended field vs seamless
> anchor). See **Finding 1**. Per the standing stop condition (plan T11 AC;
> execution notes), the stage HALTS on this and it surfaces to the owner
> before T4 dispatches. Findings 2–3 are same-neighborhood defects that the
> same T4 amendment should resolve in one ruling.

**Status:** the walk is COMPLETE — both directions, every normative rubric
clause, every `instrument_configs()` family and key. This document is the
review-pin-22 method fix: the third-in-a-pattern check after Rule 0 and the
σ field kind reached shipped-and-approved state assigned to no task.

**Sources walked (verbatim, this tree):**
- `docs/validation/phase14_seam_rubric.md` (sealed rubric; Gate-0 seal v1
  `a17ea419…b725c5d2`)
- `src/sverdrup/validation/phase14_instruments.py` — `instrument_configs()`
- `docs/superpowers/plans/2026-07-23-phase14-stage1-spatial-2017.md` (T0–T11)
- `docs/superpowers/specs/2026-07-21-phase14-scaling-program-design.md`
  (§3.1 stage map, §3.3 locked schedule, §4 forks C/E/F, §6 Stage-1 scope)

**Task-number convention.** `T0`–`T11` below are THIS plan's tasks. Stage-0
deliverables are written `Stage-0 (shipped)` with the artifact named — note
that the plan's T5 phrase "GroundTrack/SpectralFidelity instrument families
from T11 configs" refers to **Stage-0's** task numbering
(`phase14_instruments.py`, 0a-5), not this table's T11.

---

## 1. FORWARD — rubric clause → discharging task+AC (or explicit deferral)

Clause IDs (R-xx) segment the rubric doc in order; every normative sentence
is inside exactly one row.

| ID | Rubric clause (section) | Discharged by | Status |
|---|---|---|---|
| R-01 | Status: pre-registered; Stage-1 sessions apply rules mechanically; deviations require explicit owner decision at the consuming gate | Plan-wide (frozen-config policy; "User decisions" block); T9 AC-1 Gate-1 pack presents verdicts to the owner | COVERED |
| R-02 | Status: machine-readable threshold comment is the parsed source for the doc↔code pin | Stage-0 (shipped): `tests/test_phase14_instrument_configs.py::test_doc_code_threshold_equality` parses the comment AND pins the prose cells | COVERED |
| R-03 | Definitions: adjacent pair `(A,B)` = shared core boundary; shared blend-overlap region = 2·overlap strip | T4 AC-1 (registry frames verbatim, pin-3 frozensets; solve bboxes test-pinned) — Stage-1 roster has exactly one adjacent pair (`seam_n`/`seam_s`) | COVERED (evaluation-domain note under Finding 1) |
| R-04 | Definitions: `delta(x)` = MEAN-map disagreement `field_A − field_B` at overlap points, **each tile's own solve, before blending** ("the blend hides exactly what this measures") | Machinery: T0 AC-2 (`seam_delta`, hand-value pinned). **Production of the pair read: NO TASK AC** — T4's only construction AC is blend-vs-seamless | **UNASSIGNED → FINDING 1 (STOP)** |
| R-05 | Definitions: `sigma_delta(x)` — same for member-std maps | T10 AC-1/AC-2 (σ route machinery, same pure functions); T3 pin-19 + T4 pin-19 ACs (member-std map persistence). *Worked row — the σ-field-kind catch, previously unassigned, now T10/T4.* Production inherits Finding 1 (the σ pair read rides the same unassigned read) | COVERED (machinery) / F1 (production) |
| R-06 | Definitions: `D_int` construction — pooled core interiors of both tiles, one grid step, axis perpendicular to the boundary | T0 AC-1 (`interior_increment_rms`, perpendicular-axis + interior-only, hand-value pinned) | COVERED |
| R-07 | Definitions: `D_int` = one number per (pair, field kind, era), recorded beside the verdict; **resolution part of the recorded row**; ratios comparable only at equal resolution | T4 evidence AC records `D_int` beside verdict; per-field-kind via T4 σ AC. Era + resolution keys pinned by NO AC | PARTIAL → FINDING 3 |
| R-08 | Definitions: `D_int_sigma` — same construction on member-std maps | T10 AC-2 (same pure functions applied to member-std fields; distinct hand values) | COVERED |
| R-09 | Definitions: `R_seam` / `R_seam_sigma` are THE verdict-bearing numbers; raw RMS recorded beside | T0 AC-3 (verdict from R); T10 AC-1 (σ pair beside mean pair); T4 evidence AC (`delta`, `D_int` recorded beside `R`, verdict) | COVERED |
| R-10 | Rule 0: floor probe construction — floor `F` = max\|field shift\| on the overlap under maxiter+1000 re-solve, run once per pair roster | T4 Rule-0 AC + T4 pin-20 AC (m=1, ONE seam window, sizing stated before run, reuse of `diag_miost_seam_dispersion.py` by import). *Worked row — the Rule-0 catch, previously unassigned, now T4.* | COVERED |
| R-11 | Rule 0: verdict attributable ONLY if `RMS(delta) > 3×F`; below → report the number, mark **UNMEASURED (solver floor)**, do NOT interpret | T4 Rule-0 AC (floor F, the 3×F check, and the marking all in the evidence row; marking logic test-pinned); WAIT-row path in pin-20 (b) | COVERED |
| R-12 | Rule 0: one-sided rubric — no under-dispersion failure cell; smallness is success, recorded not flagged; an unattributable CLEAN is forbidden | T4 Rule-0 AC ("never CLEAN … the rubric is one-sided" verbatim in the AC); T0 AC-3's three-cell mapping has no under-dispersion cell | COVERED |
| R-13 | Verdict scope: applied per adjacent pair, per field kind, **per era** | Per pair: T4 (roster's one pair). Per field kind: T10 AC-1 + T4 σ AC (both routes per pair). Per era: **not consumed in Stage 1 — deferred to Stage 2** (spec §3.1: Stage 1 = "spatial scaling at one year (2017, the proven constellation)"; Stage 2 = "temporal scaling at fixed domain (multi-year on the tile roster)"; §6 is single-epoch by construction). Stage-1 rows carry the degenerate era key (see Finding 3) | COVERED + DEFERRED (era axis → Stage 2) |
| R-14 | CLEAN cell: `R_seam ≤ 1.0`, boundary inclusive; report-only | T0 AC-3 (exact boundary semantics test: 1.0 CLEAN, 1.0000001 ELEVATED); thresholds read from `instrument_configs()["seam"]` at call time (sentinel-config behavioural pin) | COVERED |
| R-15 | ELEVATED-RECORDED cell: `1.0 < R ≤ 2.5`; recorded in standing seam rows, carried to consuming gate; pair NOT rerun or tuned on this signal (skill-selection firewall analog) | T0 AC-3 (cell + boundary); T4 evidence AC (report-only, carried); T9 AC-1 item (2) (seam verdicts in the Gate-1 pack); no-rerun/no-tune = the plan-wide frozen-config/zero-touch discipline | COVERED |
| R-16 | ELEVATED provenance: 2.5 is an a-priori pre-registered factor (phase-4 `C ∈ [2,3]` midpoint, different metric class); owner may re-pin at Gate 0 before any number exists | Discharged PRE-Stage-1: Gate 0 CLOSED/APPROVED 2026-07-23 with no re-pin (plan "User decisions" block); the window is closed, thresholds stand at 1.0/2.5 | COVERED (closed at Gate 0) |
| R-17 | STRUCTURAL-STOP cell: `R > 2.5`; owner STOP with the three recorded options; never a silent acceptance | T0 AC-3 (cell); T4 evidence AC (verdict never blocks mechanically — STRUCTURAL_STOP surfaces to the owner, Gate-1's item); T9 AC-1 item (2) | COVERED |
| R-18 | ORACLE: the seam-pair tile carries an oracle — pair region solved seamlessly as one frame; blended field vs seamless truth, RMS difference on the overlap | T4 ORACLE AC (`seam_delta` between blended and seamless-anchor fields; seamless truth = T3's maps, like-for-like AC) | COVERED |
| R-19 | ORACLE: same ratio construction **with `D_int` from the seamless solve** | T4 ORACLE AC pins `interior_increment_rms` **pooled from both tile interiors** — the pair-route denominator, not the seamless-solve `D_int` the clause names | **MISMATCH → FINDING 2** |
| R-20 | ORACLE: thresholds = the SAME cells, applied to the blend-vs-seamless ratio | T4 ORACLE AC ("R and verdict cell recorded") via T0 AC-3 cells | COVERED |
| R-21 | ORACLE: no published precedent — recorded in the gap register | T4 evidence AC: `oracle_note: "no published precedent — gap-register (T11)"` (that citation = Stage-0's gap-register task) | COVERED |
| R-22 | Recording: every evaluated pair emits a row `{pair, era, field_kind, rms_delta, d_int, r_seam, verdict}` under `phase14.<stage>.seam_rows` | T4 evidence AC pins `phase14.stage1.seam` = {R, verdict, D_int, delta, pcg maxima, oracle_note} + σ keys + both floor checks + geometry caveat. Namespace differs (`seam` vs `seam_rows`); `pair`/`era` keys unpinned; `field_kind` covered structurally by the σ AC's per-field-kind shape | PARTIAL → FINDING 3 |
| R-23 | Recording: CLEAN and ELEVATED-RECORDED are report-only; STRUCTURAL-STOP halts the consuming run | T4 evidence AC (STOP surfaces to owner; other tiles may continue — they don't consume seams; the consuming item is Gate 1's); T9 AC-1 | COVERED |
| R-24 | Recording: thresholds mirrored as constants in `phase14_instruments.py`; unit test pins doc↔code equality on the numbers | Stage-0 (shipped): `SEAM_CLEAN_MAX`/`SEAM_ELEVATED_MAX` + `test_doc_code_threshold_equality`; consumed at call time by T0 AC-3 / T10 AC-3 (never re-typed) | COVERED |

## 2. FORWARD — instrument family/config key → consumption

Every key `instrument_configs()` carries, walked one by one.

| Family.key (sealed value) | Stage-1 consumption | Status |
|---|---|---|
| `schema_version` (1) | Seal substrate (Stage-0 0a-6, shipped); Stage-1 consumes via `verify_current_seal()` refusals — T1 evidence AC (seal sha quoted, refuses if unverifiable), T3 (seal read-only), T9 AC-1 item (9) (`seal check` PASS) | COVERED |
| `groundtrack.per_tile` (true) | T5 southern AC — per-direction spectral/track diagnostics for the kernel pack, "reuse GroundTrack/SpectralFidelity instrument families … per-tile×era parameterization"; consumed by T6 AC-2. Roster breadth (the other five tiles) pinned by NO AC — see Finding 4 | COVERED at T5 (southern) / F4 (breadth) |
| `groundtrack.per_era` (true) | Degenerate in Stage 1 (single era, 2017): rows key era=2017 trivially at T5. Non-degenerate (multi-era) consumption **deferred to Stage 2** — spec §3.1 (Stage 2 = temporal scaling), §4 fork F ("GroundTrack per tile×era" standing rows keyed (tile, era)) | COVERED (degenerate) + DEFERRED (Stage 2) |
| `groundtrack.geometry_artifact_keyed` (true) | T5 southern AC (the diagnostics ride the Phase-11 geometry provider's per-era artifacts — spec §2 line: "Phase-11 geometry provider (per-era artifacts)"); pipeline behavior is absence-means-absence (`eval_context.py`) | COVERED |
| `groundtrack.constellation_aware` (true) | Stage 1 holds the constellation FIXED (frozen five-mission workhorse on every tile — plan pin 2c; spec §6 policy (c)), so the key is exercised at its fixed value at T5. Varying-constellation consumption **deferred**: Stage 2 (per-era δ_m are constellation-dependent — spec fork C/E, §8) and the OSSE option (T8 prices it; fork-f pin 5's value case IS constellation variation; owner decides at Gate 1) | COVERED (fixed) + DEFERRED (Stage 2 / OSSE election) |
| `spectral_fidelity.per_tile` (true) | Per-tile λx in every scores block via `score_tile`'s shared spectral helper: T1 evidence AC (µ/**λx**/coverage/χ² per policy (b)), T3 check 5 (λx identity at the anchor), T5 AC-1 (four diverse-tile rows). The sealed docstring itself names Stage 1 the first non-anchor consumer of the parameterization | COVERED |
| `spectral_fidelity.band` ("tile-extent") | Same rows — the band generalizes the box convention to each tile's extent; T5 southern additionally consumes per-direction spectral diagnostics (T6 input) | COVERED |
| `spectral_fidelity.convention` ("box-generalized") | Same rows (the convention is the parameterization the above consume); T3 check 5 pins it degenerates correctly to the signed box at the anchor | COVERED |
| `seam.metric` ("cross-seam dispersion ratio vs interior reference") | T0 AC-1/2/3 (machinery); T4 (production — subject to Finding 1: only the oracle construction is pinned) | COVERED (machinery) / F1 (production) |
| `seam.clean_max` (1.0), `seam.elevated_max` (2.5) | T0 AC-3 (read at call time; sentinel-config behavioural pin), T10 AC-3 (sentinel pin covers BOTH routes); Stage-0 doc↔code test (R-24) | COVERED |
| `seam.oracle` ("seam-pair blend vs seamless signed truth") | T4 ORACLE AC (R-18/R-20), with the R-19 denominator mismatch → Finding 2 | COVERED / F2 |
| `seam.rubric_doc` (path) | Stage-0 doc↔code test resolves and parses the pointed-at doc (R-02/R-24) | COVERED |
| `insitu_nulls.climo_smooth_days` (15), `insitu_nulls.persist_lag_days` (1) | **Not consumed in Stage 1 — deferred.** Stage-1 transfer-reading composition is pinned by spec §6 policy (b) (µ/λx/coverage/χ² + reference rows + seam verdicts) and contains no gauge rows. First consumers: Stage 2 — Gate-2 "DEV-pool gauge era rows" (spec §3.1); first LOCKED consumption: Stage 2G acceptance touch (spec §3.3 — "Stage 1: never opened"). The values are sealed per fork-F pin 4 ("nulls are sealed config — never chosen at scoring time"); value-identity with the Task-9 sealed objects is pinned by Stage-0 `test_config_carries_all_four_instrument_families` | DEFERRED (Stage 2 / Stage 2G), sealed-identity pinned now |

## 3. REVERSE — every rubric/instrument claim in a task AC → its clause

| Task AC claim | Clause discharged | Note |
|---|---|---|
| T0 AC-1 `interior_increment_rms` (perpendicular axis, interior-only) | R-06 | |
| T0 AC-2 `seam_delta` co-located RMS | R-04 (machinery) | Landed helper evaluates "seam line" nodes; the clause's domain is the 2·overlap strip — carried inside Finding 1 |
| T0 AC-3 verdict cells, exact boundaries, thresholds from `instrument_configs()` at call time | R-14/R-15/R-17, R-24 | |
| T0 AC-4 solve-validity residual guard (`seam_read` refuses on bad PCG residuals) | **No rubric clause** | Deliberate extra-rubric guard; the plan itself disclaims it ("NOT the rubric's Rule 0", pin 21) — benign orphan, Finding 5 |
| T0 AC-5 NaN/land exclusion; all-NaN refusal | **No rubric clause** | Rubric is silent on land; conservative addition — benign orphan, Finding 5 |
| T1 evidence AC (seal sha quoted; refuses unsealed; scores block per policy (b) incl. λx) | R-01 (mechanical application); `schema_version`; `spectral_fidelity.*` | |
| T3 check 5 (score-level identity incl. λx) + pin-19 member-std persistence | `spectral_fidelity.*`; R-05 (σ substrate) | Std-map write = T1 follow-on, named in its commit |
| T4 AC-1 registry frames verbatim (pin-3 frozensets, pinned bboxes) | R-03 | |
| T4 AC-2 like-for-like (both dc2021a, frozen config, m=100, anchor roots) | R-18 (oracle compares like against like) | |
| T4 AC-3 blend via `assemble` | R-18 (the blended field the oracle consumes) | |
| T4 ORACLE AC (blend vs seamless + pooled-interiors D_int; R + verdict; `seam_read` gate) | R-18/R-20; **R-19 mismatch** (Finding 2) | The guard citation is the T0 solve-validity guard, correctly not called Rule 0 |
| T4 Rule-0 AC (floor F, 3×F, UNMEASURED-marking, never-CLEAN, one-sidedness) | R-10/R-11/R-12 | Worked row 1 (the Rule-0 catch) |
| T4 pin-20 AC (floor probe m=1, sized before run, WAIT path, reuse by import) | R-10 ("once per pair roster" made cheap and honest) | |
| T4 σ AC pin-19 (std maps persisted; both routes per pair per field kind; both floor checks) | R-05/R-13 (field-kind axis); R-11 (σ floor check) | Worked row 2 (the σ-route catch) |
| T4 evidence AC (`phase14.stage1.seam` keys; STOP surfaces to owner; oracle_note) | R-22 (partial — Finding 3), R-23, R-21 | |
| T4 geometry-caveat AC (pin 13 — 10×5 non-production geometry sentence) | **No rubric clause** | Discipline-7 addition, honest-scope; benign orphan, Finding 5 |
| T5 southern AC (GroundTrack/SpectralFidelity per-tile×era diagnostics) | `groundtrack.*`, `spectral_fidelity.*` | "T11 configs" there = Stage-0 numbering |
| T5 AC-1 four rows µ/λx/coverage/χ² | `spectral_fidelity.*`; R-01 | |
| T6 AC-2 (SO measured anisotropy from T5's diagnostics) | `groundtrack.*` (consumer) | |
| T8 (OSSE priced; constellation-varied value case verbatim) | `groundtrack.constellation_aware` (the deferred axis' priced unlock) | Decision cell empty — owner at Gate 1 |
| T9 AC-1 items (2)/(9)/(10) (seam verdicts + oracle numbers; seal check PASS; this table) | R-15/R-17/R-23; `schema_version`; T11 closure | Pack vocabulary pin: "Rule 0" names only R-10..R-12 |
| T10 AC-1..4 (σ pair beside mean; same pure functions; sentinel covers both routes; guard on both) | R-05/R-08/R-13 (field kinds)/R-24 | |
| T11 (this table) | Review pin 22 (plan-level, not a rubric clause) | |

No task AC claims a rubric clause that does not exist. The three extra-rubric
ACs above are deliberate additions, each explicitly disclaimed in the plan —
recorded as Finding 5 (LOW, no action) for completeness.

## 4. FINDINGS

**Finding 1 — CRITICAL (STOP-condition trigger): the rubric's primary pair
read is assigned to no task.**
Clauses R-04 + R-09 + R-22: the verdict-bearing `R_seam` is defined on
`delta(x) = field_A(x) − field_B(x)` at overlap points, **each tile's own
solve, before blending** — the rubric explicitly says the blend hides exactly
what this measures, and the Recording clause keys the row per PAIR on that
quantity. T4's only pinned seam construction is the ORACLE read (blended
field vs seamless anchor). T0's `seam_delta` machinery is field-agnostic and
the two per-tile solves exist inside T4, but **no AC requires computing or
recording the A-vs-B pre-blend route** (mean or σ — the σ route rides the
same read). Without it, Stage 1 ships `phase14.stage1.seam` with no pair row,
and the C1→2 contract item "measured seam behavior (oracle + rubric
verdicts)" is half-discharged. Sub-note: when assigned, the evaluation domain
needs one sentence — the rubric says overlap points across the 2·overlap
strip; the landed T0 helper and T4's AC say "seam line"/"seam band".
*Remedy shape (owner/planner ruling, not executor's): amend T4 with a pair-read
AC (A-vs-B pre-blend, both field kinds, Rule-0 floor check applied) before T4
dispatches — T4 is already blockedBy T11, so the gate holds.*

**Finding 2 — HIGH: ORACLE denominator diverges from the clause.**
Clause R-19 requires the oracle ratio use "`D_int` from the seamless solve";
T4's ORACLE AC pins `interior_increment_rms` **pooled from both tile
interiors** (the pair-route denominator). As written, the AC discharges the
oracle clause with the wrong denominator — a wrong-denominator verdict cell
at the stage's flagship comparison. One-line AC fix; same ruling as Finding 1.

**Finding 3 — MEDIUM: recording-schema conformance unpinned.**
Clause R-22 (+ R-07): rows `{pair, era, field_kind, rms_delta, d_int, r_seam,
verdict}` under `phase14.<stage>.seam_rows`, with resolution "part of the
recorded row". T4's evidence AC pins `phase14.stage1.seam` with no
`pair`/`era`/resolution keys and a different terminal key name (`seam` vs
`seam_rows`). Era is degenerate (2017) and resolution single (0.2°) in
Stage 1 — which is exactly why the keys are cheap to record now and expensive
to retrofit at Stage 2 when both axes go live. Fold into the T4 amendment.

**Finding 4 — LOW-MEDIUM (ambiguity, needs one owner/planner sentence):
GroundTrack standing-row breadth in Stage 1.**
Fork F declares GroundTrack "per tile×era" standing default rows
(registry-applicability-gated: absence means absence), and §6 policy (b)'s
"reference-free rows" term is ambiguous between the policy-(a) σ-reference
rows and the reference-free evaluator family. The Stage-1 plan pins
GroundTrack consumption only at T5-southern (kernel-pack diagnostics). If
policy (b) means the evaluator family, five tiles have no assigned
GroundTrack-row producer; if standing rows remain applicability-gated
defaults, coverage is complete as assigned. Not a stop — but the sentence
should be ruled before T5 so the answer is a decision, not an accident.

**Finding 5 — LOW (no action): three benign extra-rubric ACs.**
The T0 solve-validity guard, T0/T4 NaN handling, and the T4 geometry caveat
(pin 13) discharge no rubric clause. All three are deliberate conservative
additions and each is explicitly disclaimed as such in the plan (the guard is
by name NOT Rule 0, per pin 21). Recorded here so the reverse walk is
exhaustive; they claim no rubric authority and require none.

## 5. Honest-scope note — what this table does NOT cover

- **Only the sealed instruments.** Rows cover the seam rubric's normative
  clauses and `instrument_configs()` keys. Non-instrument spec constraints —
  the spend ladder, ±66° discipline, locked-tally/zero-touch rules, source
  map, frame conventions (pins 2/12), bridge-caveat wording, interpretation
  withholding — are plan/spec obligations tracked by their own ACs and are
  NOT re-audited here.
- **Assignment, not execution.** A COVERED cell means a task AC exists whose
  acceptance discharges the clause — it does not certify the AC has run green.
  Execution evidence lives in the per-task close records and the Gate-1 pack.
- **Stage-1 scope only.** DEFERRED cells assert non-consumption in Stage 1
  with a spec citation; they do not audit the consuming stage's future plan —
  each deferral must reappear in that stage's own coverage walk.
- **The rubric prose is the unit.** Clause segmentation (R-01..R-24) is this
  table's reading; it is exhaustive over the doc's sentences, but a future
  rubric amendment (new sealed version) invalidates the segmentation and
  requires a re-walk.

## 6. Verify

- `rg -c 'T[0-9]+' docs/superpowers/2026-07-25-phase14-stage1-instrument-coverage.md`
  → nonzero (task citations present).
- **[CORRECTED 2026-09-01 by owner pin 138]** The spot-check below read `### Task N:`
  headings in the plan prose. **That method is wrong**: the plan prose stops at Task 12,
  so every task added by a later owner ruling — T13–T23 — reads as a phantom, and a
  verification tool blind to a third of the recent tasks misleads whoever trusts it next.
  The check now reads the **tracker**, which is the source of truth for task existence:
  `pixi run python scripts/check_task_citations.py docs/superpowers/2026-07-25-phase14-stage1-instrument-coverage.md`
  → `PASS every cited task exists in the tracker` (10 citations, exit 0). Plan/tracker
  drift is reported as INFO, never as a refusal.
- *[superseded — kept for the trail]* Spot-check: every task number cited here (T0–T11)
  exists as a `### Task N:` heading in
  `docs/superpowers/plans/2026-07-23-phase14-stage1-spatial-2017.md`.
