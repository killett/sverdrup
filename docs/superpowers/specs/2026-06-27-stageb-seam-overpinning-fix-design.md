# Stage-B seam over-pinning fix — core-authoritative coherent sampler (design)

**Date:** 2026-06-27
**Status:** design, pre-implementation. Supersedes the spanning-tree hand-forward construction
(`GmrfTreeKrigingSolve`, spec `2026-06-26-…-design.md` §3.1/§3.1b/§3.1c) as the Stage-B coherent
sampler. Nothing implemented; this document is the approved-with-changes design from the 2026-06-27
diagnosis. The verification fixture and the construction certification are the **same measurement**.

## 0. The defect (measured, this session)

The shipped coherent sampler (max-overlap MST hand-forward) produces draws whose **marginal variance
collapses up to 7 orders of magnitude below its own reported `(Σwσ)²` marginal contract at ~16% of
2-D inter-tile seam nodes** — a real conservative-contract violation (sample ≪ reported σ), localized
to the seam, invisible to median/p25, caught only by **strict-min over physical seam pairs** (rule i).

**Mechanism (measured, not guessed).** Per-tile unconditional samplers are individually healthy (each
matches its own exact marginal: uncond/exact median ~0.99, min ~0.84). The crossfade weights are sound
(sum to 1). The collapse comes from the **hand-forward conditioning**: at a shared node the
*authoritative* (core-owning, high-weight) tiles are the **near-improper** ones (σ~280); the
well-determined σ~0.11 tiles see the node only in their **halo**. The conditioning chain pins the
authoritative near-improper tiles to an **over-confident halo tile's draw**, collapsing seam
dispersion below the (correct) reported marginal. Removing the correction restores the contract
(measured: blend seam variance without correction = 0.91× contract; with = 2.3e-6×).

**Root cause / the structural antagonist.** The near-improper global SPDE mode (sparse nadir obs leave
the `(κ²−Δ)²` low-frequency mode under-determined ⇒ global `Q_post` eigmin ~1e-7) is a *domain-spanning*
mode with **no local representation**, so every per-tile operation misjudges it. Small halo tiles
cannot support it ⇒ spuriously confident ⇒ the hand-forward propagates that into authoritative tiles.
This same mode produced the synthesized-strip-field blow-up and the conditioning floor; **tiling and a
near-null global mode are in fundamental tension** (a method boundary-of-validity constraint; Phase 5
drives `range` down → mode more improper → tension worse).

## 1. Architecture — per-node core-authoritative two-pass

Authority is **per-node**, set by the partition's **disjoint** core windows (cores partition the
domain ⇒ every node has exactly one core owner). Authority flips node-by-node between any two tiles
(a tile owns *its* core nodes, is halo at the neighbour's), so no single per-tile-edge orientation is
correct — measured. The spanning-tree machinery (`_max_overlap_spanning_tree`,
`_min_eccentricity_spanning_tree`, eigmin-rooting, sibling-seam reasoning, tree-edge separation)
**dissolves**. New driver (working name `GmrfCoreAuthoritativeSolve`, `sampler_spec="sparse-precision"`):

- **Pass 1 (independent, parallel, unchanged):** every tile draws its unconditional posterior
  `x_u = mean + L⁻ᵀw` (per-tile white). For each global node, its **core owner's** Pass-1 draw is the
  node's **authoritative** value.
- **Pass 2 (leading approach — OVERWRITE, see §3):** the coherent field is the **per-core
  authoritative patchwork**: each node takes its owning core's Pass-1 value; every tile's halo nodes
  are **overwritten** with the owning neighbour's authoritative value (per member). No `Σ_ss` solve.
  The partition-of-unity crossfade then operates on values that already agree at every overlap, so the
  coherent member **equals the patchwork** — the crossfade no longer has a tile-disagreement to smooth.

The design stays **agnostic about variance recovery** as a derivation — it is established by
measurement (§3/§6), not asserted. (Empirically, overwrite gives each halo node *exactly* the core's
value and therefore the core's variance; §3 records the measured marginal ratio rather than claiming
it a priori.)

DAG is `Pass1 → Pass2`, no sweep order, no root selection, no sibling seams, no tree.

## 2. Core-ownership map

A `node → unique core-owner tile` map built from the disjoint core windows. **The tie-break for
boundary nodes MUST be identical to `partition_weights`' half-open convention** — not merely
"consistent with". Assert (a test, not a comment) that the ownership map and the weight map resolve to
the **same owner at every boundary node**; a one-tile disagreement is itself a seam artifact. Assert
the map is **total** (every support node resolves to exactly one owner) — a loud red if the cores do
not partition the domain.

## 3. The conditioning-vs-overwrite fork (measured) — OVERWRITE leads

Two ways to make a halo node agree with its authoritative core value:

- **OVERWRITE (leading):** set the halo node = the owning core's actual draw. No solve, no
  near-singularity, coherence exact at shared nodes by construction.
- **CONDITION (rejected as leading):** krige the halo toward the core value via `solve(Σ_ss, …)`.

**Measured (real natl60 2×2; strict-min over seam pairs/nodes):**

| metric | OVERWRITE | CONDITION (current MST) |
|---|---|---|
| marginal `sample/(Σwσ)²` strict-min | **0.881** (median 0.996) | **1.76e-7** (collapse) |
| direction fd-ratio blend/ref strict-min | **0.712** (median 1.03, p90 1.33) | **0.000** |

Overwrite **fixes the marginal collapse** (6 orders better) and **dissolves sub-question A** — there
is no `Σ_ss` solve to be ill-posed at the near-improper nodes (the antagonist of the whole arc never
enters Pass 2). **CHANGE-1 note:** "does the halo variance recover to the core's?" is the measurement,
not an assumption — under overwrite it is exact by construction and the 0.881 marginal strict-min
confirms it empirically. Conditioning is retained only as the fallback if overwrite breaks derived
quantities on the production fixture (§5); if used, sub-question A (is the solve well-posed at
near-improper nodes?) and the distinct measurement "halo conditional variance vs core variance" must
both be checked — conditioning can give the right mean and a still-collapsed variance.

**Open check carried into the plan (pre-ship), stated as the real assertion — not a hope.** A
cross-seam derived quantity (e.g. firstdifference) between core node A (owned by tile A) and neighbour
node B (owned by tile B, overwritten into A's halo) is computed by **tile A using B's value**, and the
same seam quantity is computed by **tile B using A's value**. **ASSERT THE TWO TILES COMPUTE THE SAME
CROSS-SEAM DERIVED QUANTITY:** compute every cross-seam derived quantity from **both adjacent tiles'
perspectives and assert agreement**. If A's "A−B" and B's "A−B" disagree, the derived product is
**double-valued at the seam** — a coherence failure in the DERIVED quantity even though the FIELD is
coherent. This is the overwrite cleanliness gate; failing it is what would send Pass 2 back to
conditioning.

## 4. Sub-question B — do independent cores agree about the global mode?

Pass 1 draws every core independently ⇒ adjacent cores hold **different realizations** of the
domain-spanning near-improper mode. Overwrite makes the seam *value*-coherent (halo = core value) but
adjacent cores can still **disagree about the global mode**, surfacing as residual cross-seam direction
under-dispersion. The measured **0.712 direction strict-min on the K4 2×2** is the candidate signature
(the bulk is conservative: median 1.03, p90 1.33; the 2×2 is a degenerate complete graph, so this is
not yet certification).

**The 0.712 must NOT be filed as merely "deferred to the production fixture."** It is a ~30% cross-seam
gradient under-dispersion at the worst seam pair — and seam under-dispersion is THE disease this whole
arc established. It is either **(a)** a K4-complete-graph artifact a real fixture clears, or **(b)** the
core-mode-disagreement residual overwrite cannot fix. **A single production-fixture pass cannot
distinguish them** — a production fixture is also *less* near-improper (more tiles, smaller halos), so
it could pass for the WRONG reason (milder regime) while (b) is still there, resurfacing when Phase 5
drives `range` down.

**Resolution — certify across a RANGE SWEEP on the production fixture (NOT a single pass).** Sweep
`range` from long (mode well-determined, no disagreement possible) to short (mode maximally improper),
the arc's own "watch it as the fraction varies" discipline that exposed p25:
- Direction strict-min **stays ≥ floor across the whole sweep** → **case (a)**: overwrite is genuinely
  sufficient; **ship overwrite alone.**
- Direction **degrades as `range` shortens** → **case (b)**: cores disagree about the global mode;
  **draw the shared global mode once in Pass 1** (reconciliation) so cores condition toward a
  consistent realization — and if that shared mode is high-dimensional (it has no spectral gap, §4
  below), this is the per-tile method's boundary of validity, a **phase-boundary decision, not an
  in-Stage-B patch**.

**Honesty about reconciliation cost.** Reconciliation does **NOT** mean sharing "bottom-k coarse
modes" — that failed as a strip fix (error 90% in the complement) and the global `Q_post` near-null
space has **no spectral gap** (an O(n) low-frequency tail, not a low-rank coarse space). So
reconciliation is **not cheap**. If sub-question B genuinely needs it *and* the shared mode is
high-dimensional, that is the **per-tile method hitting its boundary of validity — a phase-boundary
decision, not an in-Stage-B patch** — and must be surfaced as such (junction-tree / a different
global-coupling construction), not bolted on.

## 5. Production-representative fixture (certification)

The K4/K9 fixtures (`make_natl60(2,2)/(3,3)`) are **degenerate complete graphs** (8° domain, ~3° halo
⇒ every tile overlaps every tile) and produced half this arc's confusion; a 2×2 is *structurally* K4.
The production regime at corr_len=300 is **grid+diagonals** (maxdeg ~5–8), not grid-4-neighbour (clean
grid adjacency needs corr_len ≲ 100 km). Add a **production-representative fixture**: more tiles, large
relative to the halo, yielding grid+diagonal adjacency (built from the geometry sweep validated this
session). **The fix and the construction certification are the same measurement** — verify on this
fixture, never on K4/K9.

## 6. Verification

- **Marginal contract test (the defect's own invariant):** coherent sample variance vs the blend's own
  `(Σwσ)²`, **strict-min over physical seam nodes** ≥ floor (no node below its reported marginal).
- **Conservative direction:** cross-seam firstdifference variance ratio (blend/single-tile reference),
  **strict-min over physical adjacent seam pairs** ≥ floor — never under-dispersed (over-dispersion is
  conservative, allowed).
- Both gated by **strict-min** (rule i), **across a `range` sweep on the production fixture**
  (long→short range, §4) — NOT a single pass, which can succeed for the wrong reason in a milder
  regime. The gate's median `edge_dir_ratio` is a confirmed bug → becomes strict-min; the recorded
  "dir 1.012 PASSED" is anti-evidence and is struck.

## 7. Sequencing

1. Implement **overwrite** per-node two-pass (§1–§3) + the core-ownership map (§2).
2. **Measure** on the production fixture (§5): marginal contract + direction, strict-min (§6); confirm
   derived quantities are clean (§3 open check).
3. Direction honors the floor → **ship overwrite alone.** Else investigate sub-question B and add
   reconciliation **only if measured necessary**, surfacing the phase-boundary case if it is
   high-dimensional (§4).
4. Rework `tests/unit/_tree_gate.py` / `tests/test_tree_kriging_gate.py` to the strict-min metric and
   the production fixture.

## 8. Retired / deferred

- **Dissolved by the new architecture:** `_min_eccentricity_spanning_tree`, the spanning-tree sweep as
  the driver, sibling-seam reasoning, tree-edge separation, the median `edge_dir_ratio`.
- **Deferred, NOT preemptive:** retire `_posterior_eigmin` / `_condition_root_scores` / eigmin-rooting
  in the **implementation only after the RANGE SWEEP (§4/§6) confirms overwrite-alone is sufficient
  (case a)**. Sub-question A being moot under overwrite is **NOT** a sufficient condition — it is
  already satisfied (no solve), so it would license premature deletion; if the sweep reveals **case
  (b)**, reconciliation may NEED the eigmin machinery (which tiles are near-improper, how to weight the
  shared mode). The machinery survives until the sweep rules out (b). `_max_overlap_spanning_tree` is
  kept only if Task-6 unit tests still reference it.
- The spanning-tree decision in `2026-06-26-…-design.md` and PROGRESS is **superseded** by this
  document.
