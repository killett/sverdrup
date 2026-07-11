# Phase 6 (FEM / grid-agnosticism) — Claude Code prompts (historical record)

**Provenance.** Reconstructed verbatim on 2026-07-10 from the review-layer conversation. Unlike
phases 1–5, Phase 6 had no assistant-authored `scope_spec` file: that role is played by the
committed design spec, authored in-repo by Claude Code under the brainstorming skill. The prompts
below were sent as owner paste blocks into the Claude Code session, in the order given.

**In-repo artifacts of record:**
- Spec: `docs/superpowers/specs/2026-07-01-phase6-fem-discretization-design.md`
- Plan: `docs/superpowers/plans/2026-07-01-phase6-fem-discretization.md` (+ `.tasks.json`)

Mid-flight fork-decision blocks are not reproduced here; their outcomes are recorded in the spec's
decision content and in `PROGRESS.md`.

---

## 1. Design review — blocker + scope gut-check (c. 2026-07-01, after the design sections were presented)

```text
Phase-6 FEM design review — sections mostly land; ONE blocker + a scope gut-check + two folds before write-up.

BLOCKER (verify against pushed code before §1's thesis is written as fact):
- The "exact FEM marginal var via Takahashi, reduction inherited unchanged" claim (§1/§2/§4) rests on
  GMRFPrecisionReduction being sparsity-pattern-AGNOSTIC. That reduction was built/tested/tuned on GRID
  precision (5-point lattice stencil). FEM P1 stiffness has a DIFFERENT pattern (irregular vertex adjacency,
  variable valence, no lattice). Selective-inversion/Takahashi is "exact" only if fill-in / elimination tree
  is computed from the ACTUAL precision graph — a grid-correct implementation can silently return wrong
  off-set entries on a mesh. VERIFY: does GMRFPrecisionReduction recompute the elimination tree/fill-in from
  the precision graph, or assume grid structure? If it assumes structure, "reduction inherited unchanged" is
  FALSE and Phase 6 gains a real unbudgeted component (pattern-agnostic reduction) — and the exact-marginal-var
  test is really validating reduction.py on a new pattern, not fem.py. Resolve before writing §1.

SCOPE GUT-CHECK (not a veto — the scope was chosen fast, right after you established the payoff has no consumer):
- FEM is unblocked but UNJUSTIFIED on the rectangular 2021a box. "Full resurrection" builds a real method whose
  one differentiator (C7 boundary extension) can only be shown on a synthetic fixture you also construct — a
  self-contained loop. That's legitimate as CAPABILITY-READINESS, not value-now; the spec must say which.
- §3 multi-tile FEM inheritance is the lowest-value / highest-inherited-risk section: it proves FEM obeys a
  coherence envelope it PROVABLY already inherits (CoherenceFeasibility is discretization-agnostic), demonstrated
  only at n_tiles <= n_star_joint (a tiny regime). Consider: build fem_precision + exact-marginal test + sliver
  guard as a shelved, tested capability; DEFER multi-tile FEM until a real consumer exists. Confirm the scope.

FOLDS:
1. C7 baseline (§4): "edge_var(FEM) < edge_var(grid)" depends entirely on the GRID boundary treatment compared
   against (masked cells / nearest-node extrapolation / padded rectangle). Compare against the DEFENSIBLE grid
   baseline the framework actually ships — not a naive one — and STATE the grid boundary handling in the test,
   or the demo proves nothing.
2. Stationary kappa only for Phase 6 (§2): per-node/nonstationary kappa has no consumer in the synthetic demo
   (stationary suffices to show boundary extension). Move per-node kappa to §5 deferred (assembly seam supports
   it later). Keeps the swap genuinely near-pure and trims assembly + test burden.

HONEST FRAMING (§4 C7 wording): "demonstrates the boundary-extension MECHANISM on a controlled synthetic
fixture" — NOT "demonstrates the payoff." Real-coastal payoff (mesh quality, coastal data density, MDT) is
only shown against real data, which §5 correctly defers.

CORRECT AS-IS (well-verified): inheriting the live GmrfTreeKrigingSolve (not the dead joint driver); coherence
envelope inherited verbatim via the discretization-agnostic predicate; new milestone name killing the Stage-C
collision; sliver guard + C5 genuine-swap guard + C6 shared-node tests. After the blocker is resolved and the
scope confirmed, write the spec + self-review + hand over.
```

---

## 2. The consolidated Phase-6 prompt — goal re-oriented to grid-agnosticism (c. 2026-07-01; the prompt that drove the spec)

Context: the owner set the goal — "prove that sverdrup is truly grid agnostic, and that it doesn't
secretly depend on some feature of the regular grids" — with full FEM scope retained.

```text
Phase-6 FEM design — GOAL RE-ORIENTED + one refinement to the prior review. Everything else in the prior
review stands (C7 kept, multi-tile kept, blocker-first, the two folds, the CORRECT-AS-IS items). Full FEM
scope is confirmed — nothing is being cut or deferred beyond what's already noted.

PRIMARY GOAL (restate at the top of the spec): Phase 6 exists to FALSIFY the claim that sverdrup secretly
depends on a regular-grid feature — i.e. to prove sverdrup is grid-agnostic by running the full pipeline on
a maximally-irregular mesh and checking it against linear-algebra ground truth. The FEM method is the VEHICLE
for that proof; C7 (boundary mechanism) and multi-tile inheritance are secondary completeness, not the point.

THE HEADLINE EXPERIMENT (this is the blocker and the agnosticism proof — they are the SAME thing):
- Does GMRFPrecisionReduction stay EXACT on FEM's irregular sparsity pattern? It was built/tested on GRID
  precision (5-point lattice). FEM P1 stiffness has irregular vertex adjacency / variable valence / no
  lattice. Takahashi/selective-inversion is exact only if fill-in / elimination tree is computed from the
  ACTUAL precision graph. So: exact-marginal-var test = diag(Q_post^-1) via the inherited reduction vs a
  DENSE Q_post^-1, on a SMALL adversarial mesh, tight rtol.
- REFRAME (do NOT treat as a risk to retire): this is the core grid-agnosticism experiment, and BOTH outcomes
  are a successful Phase 6. Passes -> agnosticism substantiated for the reduction path. FAILS -> you have
  FOUND a hidden grid dependency; the fix is in reduction.py (pattern-agnostic reduction), and Phase 6 gains
  that component. Either way, run it FIRST, before writing §1's "reduction inherited unchanged" as fact —
  because multi-tile and C7 both inherit a broken reduction until it's cleared.

ELEVATE TO PRIMARY DELIVERABLE (was ordinary §4 tests; now the headline, because agnosticism is the goal):
1. The exact-marginal-var test above, on a MAXIMALLY ADVERSARIAL mesh — not merely non-grid. Required fixture
   properties, stated explicitly in the spec: irregular/variable vertex valence; non-uniform node spacing;
   slivers near the guard threshold; a jagged/irregular boundary; small enough that a dense Q^-1 ground truth
   is computable. The adversarial-ness IS the value — a favorable/regular-ish mesh proves little.
2. The grid-shortcut audit, expanded to the WHOLE solve->reduce->blend->project path (not just the obvious
   reshape spots): any call to bilinear_weights, any (ny,nx) reshape, any lattice-index assumption raises
   loudly if hit on the FEM path. FEM holds field_shape (n_nodes,). This is the literal mechanization of
   "prove it doesn't secretly use the grid" — make it fail loud if the FEM path routes through ANY
   grid-shaped code.

HONEST-SCOPE CAVEAT (write this in the spec NEXT TO the result — it is the difference between honest and
oversold): passing establishes "no hidden grid dependency ON THE PATHS THE ADVERSARIAL FIXTURE EXERCISES."
It is strong falsifying evidence, not a universal proof — a dependency in an unexercised path stays invisible.
Strength is proportional to how adversarial and path-covering the fixture is (which is why #1/#2 are the whole
game). State this scope honestly; do not claim unconditional grid-agnosticism.

UNCHANGED FROM THE PRIOR REVIEW (keep exactly):
- C7 boundary demo KEPT, framed as "demonstrates the boundary-extension MECHANISM on a controlled fixture
  against a DEFENSIBLE grid baseline (the one the framework actually ships — state its boundary handling:
  masked cells / nearest-node / padded)" — NOT "proves FEM better on real coasts" (real-coastal payoff needs
  real data; deferred, ODC dead). Under the agnosticism goal C7 must NOT be rigged to make FEM win — it's a
  mechanism demo with an honest baseline, not a value claim.
- Multi-tile FEM inheritance KEPT (scope confirmed): one global shared-node mesh, tiles are node subsets,
  inherits the LIVE GmrfTreeKrigingSolve (NOT the dead GmrfJointKrigingSolve the old design named); FEM
  inherits the discretization-agnostic CoherenceFeasibility envelope verbatim (MARGINAL_VARIANCE global ships;
  SAMPLES/COVARIANCE only within n_star_joint); demonstrated at n_tiles <= n_star_joint. Note in the spec this
  is the lowest-information section (it re-confirms an envelope already proven discretization-agnostic at the
  predicate level) — kept for completeness, not as an agnosticism test.
- Stationary kappa only for Phase 6; per-node/nonstationary kappa stays deferred (§5), assembly seam supports
  it later. It is ORTHOGONAL to grid-agnosticism (per-node kappa scales entries, doesn't change the sparsity
  pattern, so it adds no pattern-coverage) and has no consumer. If "don't return later" means you want it too,
  say so — it's a small assembly add behind the same seam — but it does not serve the stated goal.
- CORRECT AS-IS: new milestone name (kills the Phase-4/Phase-5 Stage-C collision); sliver guard; C5
  genuine-swap guard; C6 shared-node (adjacent-tile shared strip non-empty on the global mesh).

After the headline experiment is run and its outcome known, write the spec to
docs/superpowers/specs/2026-07-01-phase6-fem-discretization-design.md with the goal re-oriented as above and
the agnosticism tier as the headline; self-review; hand over the file before writing-plans.
```

---

## 3. Spec file review — the keystone fix gating writing-plans (c. 2026-07-02)

Context: the review found the spec's headline exactness numbers cited an uncommitted probe script —
the "measured-fact-not-in-version-control" pattern — and required the evidence be made reproducible
before writing-plans.

```text
Phase-6 FEM spec review — APPROVED in structure/reasoning; ONE keystone fix required before writing-plans.

BLOCKER (verified against pushed repo): §0.1 presents the reduction-exactness result as "measured fact"
citing scripts/probe_fem_reduction_exactness.py (max rel err 4.4e-10, 40/40 mesh-edge cov exact). That script
is NOT in the repo — at HEAD 65719c5, scripts/ has only diag_crossseam.py + stage_b_gate_run.py; no FEM source
or probe is tracked. So the document's keystone is currently UNVERIFIABLE (not reproducible by me or a future
session) — the exact "measured-fact-not-in-version-control" pattern the project's discipline forbids, and it
undercuts the §0.2/§7 honest-scope stance the spec itself rests on.

THE CLAIM IS SOUND (verified from real code — this is a framing fix, not a teardown):
- gmrf_linalg.py:27 — GMRFFactor factors Q[P][:,P] in AMD order; the permutation is from the ACTUAL matrix
  graph, no lattice assumption.
- gmrf_linalg.py:96-101 — _takahashi / selective_inverse_diag = Erisman-Tinney selective inverse, exact on
  the factor's fill pattern for ANY SPD Q.
- gmrf_linalg.py:135 — assert_adjacency_in_pattern(q, shape=(ny,nx)) is the sole grid-shaped symbol, and it's
  a PRECONDITION GUARD, not a numerical step; the FEM path correctly substitutes a mesh-edge-in-pattern guard.
So reduction-path agnosticism is defensible mechanistically; only the evidence is missing.

FIX (do both):
1. Rest §0.1's CLAIM on the mechanistic argument above (three code facts, verifiable by inspection) — "why the
   reduction is pattern-agnostic" — instead of on an uncommitted probe's numbers labeled "measured fact."
2. Make the NUMBER come from the shipped, CI-run §3 #1 test (exact-marginal-var on the adversarial mesh vs
   dense Q^-1), which IS this measurement, committed and reproducible. Cite THAT as where exactness is
   produced-and-locked. IF you want to keep the concrete 4.4e-10 / 40/40 figures as a preview in §0.1, then
   COMMIT probe_fem_reduction_exactness.py so they are reproducible (the diag_crossseam.py precedent).

REINFORCEMENT (why CI-locking is non-optional, not hygiene): the "40/40 mesh-edges exact, 0 absent from the
selective-inverse pattern" sub-claim is NOT covered by "Takahashi is exact" — Takahashi gives Sigma_ij only for
(i,j) IN the factor fill pattern, so this asserts every mesh edge lands in Q's pattern (a property of
fem_precision's alpha=2 assembly: (k^2 C + G) C^-1 (k^2 C + G) carries the 2-hop neighborhood, so 1-hop edges
are included -> in L's fill). That's an assembly-pattern fact the mechanistic argument doesn't fully nail and
can fail under degenerate configs -> it genuinely needs the reproducible §3 #1 measurement.

SMALLER:
- Verify the C7 baseline citation (gmrf_grid.py:49 as the 5-point Neumann-edge Laplacian) — the one other
  load-bearing line-reference in the doc; confirm it before it's written as fact.
- Per-node kappa: deferral reasoning is sound (scales entries, not pattern -> zero agnosticism-coverage; no
  consumer). Stays owner's call; leaving it out is fine unless "don't return later" outweighs that.

APPROVED AS-IS otherwise: goal re-orientation; agnosticism tier as primary with adversarial-fixture properties
spelled out; whole-path grid-shortcut audit; honest-scope caveats (§0.2/§7); C7 as mechanism demo vs the named
baseline; multi-tile flagged lowest-information via the live GmrfTreeKrigingSolve; blocker-first sequencing.

Apply fix 1+2 (and confirm the two smaller items), then invoke writing-plans.
```
