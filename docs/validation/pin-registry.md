# Pin registry — owner series vs executor series (owner pins 40, 41)

**Owner pin 40: a pin number asserts OWNER AUTHORSHIP.** Nothing else may enter
the sequence. Executor decisions live in the **E-series**, are marked
UNRATIFIED on sight, and become pins only when the owner rules them — at which
point the owner renumbers them into the owner series, not the citing document.

**Owner pins 41 + 48: a pin is citable when its VERBATIM TEXT is present in the
ruling document at HEAD as of the citing commit.** No sha bookkeeping, no
self-reference: the check is "open the ruling doc at that commit — is the pin
there?", which is mechanically decidable and catches the actual failure mode
(citing a pin that does not exist). Pins 36-47 became citable the moment PART 3
and PART 4 landed. This registry maps each pin number to the ruling document and
the PART that holds it, and separates the owner's series from the executor's.

---

## Owner series — rulings actually issued

| Pins | Subject | Ruling text |
|---|---|---|
| 1–30 | Phase-14 spec forks (a–g), design batches, and per-task review pins. **Distinct sub-namespaces**, always cited with their qualifier: "fork-b pin 2", "batch-1 pin 2c", "review pin 19", "owner PIN 23", "plan pin 20(c)". A bare "pin 12" in Stage-1 context means the owner's Stage-1 election series. | `docs/superpowers/specs/2026-07-21-phase14-scaling-program-design.md` + the Stage-0/Stage-1 plan headers |
| **31–35** | CRN origin defect (31 a–d), σ instrument at m=100 (32), two-sided gate discipline (33), Rule-0 text by accuracy target (34), procedural cost of amending a sealed instrument (35) | `docs/superpowers/2026-07-27-owner-ruling-crn-sigma-rule0.md` PART 1 |
| **36–39** | The 3× factor is wrong (36 a–e), oracle/σ extension ratified (37 a–c), σ-level pooling ratified (38), dispatch both reviewers (39) | same document, **PART 3** |
| **40–47** | Pin namespace (40), no pin citable until on origin (41), pin 33 made mechanical (42), run the settling measurement (43), per-route oracle floor construction (44), DEFER the whole amendment past T14/T15 (45 a–d), code and seal move together (46), guard defects (47) | same document, **PART 4** |

Pins **48-50** (this addendum: pin 41 simplified, the non-verdict-bearing
status of the surviving arithmetic, and the disposition of the E-series) are in
**PART 5** of the same document.

## Audit of every pin citation in the tree (owner pin 40a)

Swept `docs/`, `src/`, `scripts/`, `tests/`, `PROGRESS.md`, the plan and its
`.tasks.json`, and the evidence keys. Result:

- **Numbers 1–30**: all citations carry their sub-namespace qualifier and match
  owner-issued text. No action.
- **Numbers 31–39**: every citation in code and docs attributes genuinely
  owner-authored content (verified line by line against PART 1 and PART 3).
  No executor decision was found numbered in the owner's series.
- **ONE VIOLATION, in the withdrawn artifact (pin 40b brings it in scope):**
  the superseded seal v2's `signoff` asserted that pins 36–38 were *"recorded
  verbatim at [the ruling doc]"* when that document contained only 31–35 —
  the pins existed in session prose alone. Both v2 seal files were deleted with
  the rollback, so the text survives nowhere in the tree; it is recorded here
  and in `phase14.stage1.rubric_v2_amendment_withdrawn` so the wrong convention
  cannot be learned from it. Its content was NOT executor-authored — it cited
  real owner decisions that had not yet been landed, which is precisely the
  hole pin 41 closes.
- **What the audit found MISSING** rather than misnumbered: executor decisions
  were never marked as such anywhere. They are enumerated below.

## Executor series (E-n) — UNRATIFIED unless a pin says otherwise

| E-n | Decision | Status |
|---|---|---|
| **E-1** | σ level entering `F_ens` is the POOLED RMS (quadratic mean) of the two σ fields, not the arithmetic mean the T4 diagnosis used | **RATIFIED → owner pin 38** |
| **E-2** | Apply the σ-route ensemble floor to the ORACLE row too, not only the ELEVATED pair row | **RATIFIED → owner pin 37** |
| **E-3** | Attributability factor value **1.07** (q0.999 × 1.05 margin) | **OVERTURNED** by pin-39 review; superseded by owner pin 43 (run the settling measurement) |
| **E-4** | One-sided confidence **0.999** for the attributability quantile | UNRATIFIED — carried into the deferred seal task |
| **E-5** | Model-assumption margin **1.05** | UNRATIFIED — and shown insufficient; carried into the deferred task |
| **E-6** | `N_eff` estimator: separable per-axis lag sum with the Gaussian step `ρ_u = ρ_d²` | **OVERTURNED** — the realized half-split spread is 3.1–3.9× wider than it predicts |
| **E-7** | Acceptance criterion `±4 sd on two samples` for the m=50 cross-check | **OVERTURNED** — could not fail (P(reject) ≈ 1.3e-4); named by owner pin 42 as the fifth instance |
| **E-8** | Verdict precedence WAIT → solver floor → ensemble floor, both blocks always recorded | UNRATIFIED; the ensemble branch is REMOVED with the deferral (pin 46), the WAIT/solver order LANDS |
| **E-9** | `correction` block schema, and `seal_sha` on a corrected row naming the seal that licenses the CORRECTED verdict | WITHDRAWN with the amendment |
| **E-10** | `phase14_seal_run.py supersede` command: verify-current-first, refuse without signoff, refuse on unchanged content, `_ENVELOPE_KEYS` admitted by `check` | UNRATIFIED — **LANDS** (machinery only; it changes no sealed content and is exercised only in tests until a seal actually moves) |
| **E-11** | The `NOT_ESTABLISHED (…)` verdict wording, and a one-shot guard that keys on the row's VERDICT instead of on its own annotation block | UNRATIFIED — **LANDS**; the behaviour is owner-authorized (pins 45b, 47), the wording and guard design are the executor's |
| **E-12** | Extracting `blend_strip` from the compare phase so the blend is reusable without re-solving | UNRATIFIED — **LANDS** (pure refactor, no behaviour change) |
| **E-13** | Pin 41 implemented as a REGISTRY cited by pin number (owner pin 48 then replaced the sha requirement with presence-at-HEAD, which this file records) | UNRATIFIED — **LANDS** (this file) |
| **E-14** | The two tracked-`sealed/`-v2 tests skip while no v2 exists, re-arming automatically when one is sealed | UNRATIFIED — **LANDS** |
| **E-15** | `verify_current_seal(evidence_path=None)` gains the caller's store instead of always reading the module constant | UNRATIFIED — **LANDS** (fixes a reviewer-found defect: an isolated store was verified against the production pointer) |

**Standing rule for this file:** any new executor decision that a future reader
could mistake for an owner ruling gets an E-number here, on the commit that
introduces it.

**Owner pin 50 — the disposition of the nine UNRATIFIED items.** E-4, E-5, E-8,
E-10..E-15 go to the owner on the next walk. **Until the owner rules them they
are cited as UNRATIFIED or not cited at all**, and specifically: an unratified
E-item must never acquire authority by being referenced in a commit message, a
seal signoff, or an acceptance criterion. Nothing downstream may lean on one.
