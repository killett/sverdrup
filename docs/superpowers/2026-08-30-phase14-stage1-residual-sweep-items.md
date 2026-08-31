# Residual sweep items — owner pin 118

**REPORT ONLY.** Enumerates what remains UNRULED from the 91(a) stale-criteria sweep
(`docs/superpowers/2026-08-01-phase14-stage1-stale-criteria-sweep.md`, 13 live items,
numbered 3–15 there), so they can be ruled together rather than discovered one at a time
by building into them.

## 1. The count

**11 of 13 ruled. 2 remain.** Plus two adjacent items that are NOT among the 13 and are
listed separately in §3, because the same "discovered by building into it" failure mode
applies to them.

| # | Task | Ruled by | Folded? |
|---|---|---|---|
| 3 | T5 — "RAM predicate before each" | pin 92 / E-16 §2 | ✅ T5a + T5b (`run` routes the four cleared tiles through `tier2_launch_gate`) |
| 4 | T5 — raw-σ row uncaveated | **pin 94** | ✅ T5b (`SIGMA_CAVEAT`, required schema field) |
| 5 | T5 — `build_evidence_row` "EXACTLY the schema set" | **pin 95** (+98) | ✅ T5b (pin-42 fields on the χ² row only; rest report-only, test-pinned) |
| 6 | T5 — equatorial `lane0_manifest.json` shas | **pin 96** | ✅ T5d (manifest mirrored, WITNESSED_AT_CREATION, maps stay out) |
| 7 | T6 — ±66 breach "either ruling" branch | **pin 99(a)** | ⚠️ ruled, **fold owed at T6** (only `halo ≤ 2.0` is operative; the isolated branch is dead arithmetic) |
| 8 | T7 — "no new ceilings exist" / Tier-1-only | **pin 99(b)** | ⚠️ ruled, **fold owed at T7** |
| 9 | T8 — "price from Task 2/5 actuals … on Tier 1" | **pin 99(c)** | ⚠️ ruled, **fold owed at T8** |
| 10 | T9 — "anchor five-gate block" | **pin 97(b)** | ✅ folded into T9's criteria |
| 11 | T9 — "seam verdict" (singular) | **pin 97(c)** | ✅ folded into T9's criteria |
| 12 | T9 — "six transfer readings" | **pin 97(a)** | ✅ folded into T9's criteria |
| 13 | T9 — pack contents (1)–(10) incomplete | **pin 97(d)** | ✅ folded into T9's criteria |
| **14** | **T9 — "zero locked opens" attestation** | **UNRULED** | — |
| **15** | **T9 — `verifyCommand` is bare pytest** | **UNRULED** | — |

Rows 7–9 are ruled but their folds land inside tasks that have not opened yet (T6/T7/T8).
They are listed so the distinction is visible: **nothing about them is awaiting a ruling.**

## 2. THE TWO UNRULED ITEMS

### 14 — T9 discipline attestation: "zero locked opens" (MEDIUM, wording)

- **The criterion:** T9's pack must attest "zero locked opens, tally byte-identical, ±66°
  respected under the ruled convention, seal `check` PASS".
- **What changed underneath it:** **pin 87** records an open **production defect** deferred
  into Stage 2 (`phase14.stage1.crn_production_defect_deferred`) — *a property of the
  SHIPPED SYSTEM, not of an instrument*.
- **The open question, exactly:** does "locked" scope to locked *instruments* (in which
  case the attestation is true as written, and the defect belongs in a different line), or
  does the attestation as phrased read as a clean bill that pin 87 contradicts? The sweep's
  proposed honest form: *"zero locked opens, one deferred production defect named at
  `crn_production_defect_deferred`"*.
- **Status:** report-only binds it (99d) — **not fixed**. Wording, not substance.

### 15 — T9 `verifyCommand` is a bare pytest invocation (LOW, mechanical)

- **The criterion:** T9's tracker metadata records
  `verifyCommand: pixi run pytest -q -p no:cacheprovider`.
- **What changed underneath it:** **pin 83** reordered the gate sequence to
  **format → stamp → suite → verify → commit** and made it mechanical in
  `scripts/phase14_gate_suite.py`, *because the old order produced gate evidence from a
  pre-format tree structurally and every time*. A bare pytest as T9's verify command
  reproduces the exact defect pin 83 closed.
- **Note from T5e (2026-08-30):** the gate suite has now been run in that order for real —
  1543 passed, tree unchanged across the run, `verify` PASS against a stamp recording a
  COMPLETED suite. So the correct command is not hypothetical; it is the one that produced
  this stage's most recent evidence.
- **Status:** report-only binds it (99d) — **not fixed**. The criterion's *intent* ("full
  sweep on the final tree") is right; only the recorded command is stale.

## 3. ADJACENT — not among the 13, same failure mode

Listed because pin 118's reason for enumerating (do not discover these one at a time)
applies to them equally.

### A. T11 Finding 4 — "reference-free rows" is ambiguous, and was never ruled

The T11 coverage table (2026-07-25) flagged that §6 policy (b)'s *"reference-free rows"*
is ambiguous between the policy-(a) σ-reference rows and the reference-free **evaluator
family**, and asked for **one owner sentence before T5**. That sentence was never given.
It now matters more than it did: under the evaluator-family reading, policy (b)'s
composition is unmet at the four diverse tiles (pin 106) and was unmet at the three box
tiles until the pin-114 recovery. **Pin 106(c) tells the pack what to state either way**,
so nothing is blocked — but the underlying ambiguity is still open.

### B. Pin 108's folds are owed at T6, and T6 has not opened

108(a)–(c) are RULED: the anisotropy axis is **UNEVIDENCED** at Stage 1 (not "limited"),
the kernel decision **may not be made on that axis** (a WAIT comes to the owner if the
options cannot be separated without it), and the propagation is stated — the election
drives `operative_halo_deg()` (fork-d pin 4), which sets the SO obs-frame edge and the ±66
margin (pin 10). **Nothing awaits a ruling**; the fold lands when T6 opens, alongside
item 7's.

## 4. What this list does NOT contain

- Anything ruled and already folded (rows 3–6, 10–13) — recorded above for the reverse walk
  only.
- Any proposed fix for items 14 or 15. Report-only binds both (99d), and this report
  changes nothing.
