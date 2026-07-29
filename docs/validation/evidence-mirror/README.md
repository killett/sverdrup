# Evidence mirror — the provenance-bearing subset, under version control

**Owner pin 56** (`docs/superpowers/2026-07-27-owner-ruling-crn-sigma-rule0.md`,
PART 7). The Stage-1 evidence store is gitignored (`.gitignore:42`) and absent from
a fresh clone, so every write-once surface it carries had existed on one machine and
had never been externally visible.

> The issue is WITNESS, not backup. Write-once enforced by a file only its author
> can see is a convention; nothing can demonstrate it was not rewritten. That is the
> one guarantee this program cannot hold on trust. — pin 56(a)

## What is here

| file | what it is |
|---|---|
| `phase14-stage1-provenance.json` | the mirrored nodes, each with a canonical SHA-256, plus the line itself (`the_line_mirrored` / `the_line_not_mirrored`) |
| `phase14_evaluation_seal_v1.json` | the seal, mirrored whole — it is 11 KiB and it is the seal chain |
| `supersessions.json` | appears only if a witnessed node is ever deliberately superseded; holds the prior digest AND the prior body |

## ⛔ What this proves — and what it does not (pin 60)

Every node here was **witnessed on the date it first entered the mirror**. From that
moment it is closed against **future** alteration: `check` detects a change, `sync`
refuses it, and once pushed the digest sits in git history the author cannot
silently rewrite.

**"Witnessed" does NOT mean "proven unaltered since creation."** Every record written
*before* the date it was mirrored is unwitnessed for the interval between its writing
and its mirroring. All 24 nodes were first witnessed on **2026-07-28**.

**Where that interval HAS been closed (pin 60a).** `phase14.stage1.anchor_gate_artifact_sha_reconciliation`
reconciles the 2026-07-28 artifact capture against shas **phase 13 recorded at the
time**:

| artifact | outcome |
|---|---|
| `phase13_winner_mean.nc` | **interval CLOSED** — exact match against `phase13.miost.provenance.mean_maps_sha256`, corroborated by a second independent phase-13 record |
| `phase13_winner_var.nc` | **interval CLOSED** — exact match against `phase13.miost.provenance.var_maps_sha256` |
| `phase13_lane0_mean.nc` | **SEARCHED AND ABSENT** — no contemporaneous sha exists anywhere under `phase13` (all 30 sha-shaped values checked). Interval stays open; the capture closes future substitution only |

Also confirmed double-witnessed, no action needed: `phase13_winner_members.npz` and
`phase13_field_miost.json` both match phase-13's own provenance shas exactly.

### Reading path: the manifest first, always (pin 64)

**A node's caveats are current as of its own writing.** The manifest's
`amendment_index` is what tells you whether they still stand — it maps each node to
the nodes that later amend or reconcile its claims.

A witnessed node is **never edited** to point at what amends it (pin 64b); the index
exists precisely so that stays true. The index is **append-only itself**: entries may
be added, never removed or rewritten, and `check` fails on a regression.

So a node that reads "this cannot speak to the interval" may since have had that
interval closed — `anchor_gate_artifact_shas` is exactly that case. Read the index.

### What the guarantee does not reach (pin 65)

`phase14.stage1.artifact_witness_inventory` classifies every `data/` artifact cited
under `phase14`:

- **witnessed at creation** (8) — a sha was recorded when the artifact was written
- **forward-only** (1) — `phase13_lane0_mean.nc`; searched and absent, interval open
- **previously unwitnessed, captured 2026-07-28** (10) — a class pin 65 did not
  name and the sweep found: **all six seam artifacts**, including the member stores
  the settling measurement replays, plus `anchor_gate_member_store.npz`,
  `screening_rows.json`, the DT input track, and the seal file. Their intervals
  **cannot** be closed — no contemporaneous record exists to reconcile against.

The claim-level consequence is recorded at `phase14.stage1.gate5_mu_witness_scope`:
of the three pin-29 µ values, `0.7695329827465144` rests on the forward-only
artifact, and a reader meeting that number should meet the caveat with it.

## Why this is a witness and not a copy

Two properties, both enforced by `scripts/phase14_evidence_mirror.py`:

1. **A canonical digest per node** — stable across dict key order, sensitive to
   values and to **list order** (the settling ratios are stored in partition
   order, and a reordered array must not pass).
2. **An append-only gate.** `sync` REFUSES to rewrite a node it has already
   witnessed. Adding a new record is ordinary; changing one already recorded is a
   STOP naming the node. Superseding is possible but must be deliberate —
   `--supersede <path> --reason <text>` — and the prior body is preserved, never
   dropped.

**The tamper-evidence ultimately comes from git**: once pushed, these digests sit
in history the author cannot silently rewrite. The script makes drift *detectable*;
the push makes it *witnessed*.

Both gates were demonstrated live before this landed: editing `gate5.mu` in the
store made `check` fail naming `phase14.stage1.gate5`, and made `sync` refuse.

## Usage

```
pixi run python scripts/phase14_evidence_mirror.py check
pixi run python scripts/phase14_evidence_mirror.py sync
```

`check` is the one to run on resume. It verifies the mirror against its own digests
**and** against the live store, and reports three things: self-check, store drift,
seal drift.

## The line (pin 58, correcting pin 56d)

**THE TEST IS CITATION, NOT STAGE: a node is IN if a standing claim cites it,
wherever it lives.** Pin 58 overturned the stage-scoped boundary the first cut used.
The reason is load-bearing: **two of the five anchor-gate checks are discharged by
CITATION to Stage-0 evidence**, so under the old rule the identity chain T14
threatens rested, in part, on records that were never witnessed.

**Not mirrored** only if nothing cites it — bulk search history, tuning traces,
re-derivable operational config. **Prior phases come in ENUMERATED, never
wholesale** (pin 58c).

**22 nodes, 91.9 KiB**, plus the seal. Four groups are out, each recorded **by name
with its reason** inside the JSON.

On pin 58(c): a full sweep of every prior-phase reference inside the phase14
evidence found exactly **one** cited evidence node — `phase13.miost.members`, whose
`root_int` the anchor gate cites to explain why check 1 runs at the phase-13
acceptance root. Every other prior-phase reference is a **file artifact**, and those
are closed by sha under pin 58(d) rather than by mirroring a phase.

The store is **not** un-ignored wholesale, per pin 56(b).

## Pin 58(d) — the substitution hole, confirmed and closed

The owner's suspicion was correct. Check-1's four routes split two ways:

| route | witnessed what it compared against? |
|---|---|
| `member_sha` | **yes** — both sides' eta/anom shas, 9/9 windows |
| `obs_identity` | **yes** — both sides' coords/values shas |
| `reference_store` | **yes** — `member_store_sha` |
| `mean_vs_acceptance` | **no** — reference path + outcome, no sha |
| `variance` | **no** — reference path + outcome, no sha |
| `gamma_route` | **no** — neither path nor sha (same reference as the mean route) |

So a later substitution of `phase13_winner_mean.nc` or `phase13_winner_var.nc`
would have re-passed with nothing in the record to show it. Two fixes landed:

1. **Captured now** at `phase14.stage1.anchor_gate_artifact_shas` (mirrored).
   **Caveat stated in the node, not hidden:** these shas were taken on 2026-07-28,
   after the 2026-07-26 gate run, so they witness the artifacts *as of capture* and
   cannot prove they were unchanged in between. What they close is **future**
   substitution.
2. **Durable:** `scripts/phase14_anchor_gate.py` now records `reference_sha256`
   inline on the mean, Gamma and variance routes, so T14's check-1 re-run witnesses
   what it compared against rather than only that it matched.

Already safe, and left alone: `phase13_field_miost.json` (sha in `era_noop`),
`phase13_winner_members.npz` (sha in `reference_store`), and `surface_identity`,
which records the calibration `cal_key` verbatim on both sides.

## Pin 59 — the gates are test-pinned

`tests/test_evidence_mirror_gates.py` re-runs the live demonstration on every suite
run against a synthetic store: `check` STOPs naming the rewritten node, `sync`
refuses and leaves the mirror byte-unchanged, a byte-identical restore clears the
STOP without latching, `--supersede` preserves the prior digest *and* body,
`--supersede` without `--reason` is refused, and a brand-new node syncs freely.
Verified by mutation: stubbing `detect_changes` to return `[]` kills five of them.
