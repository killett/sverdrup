# Stage-C redesign — capability-scoped, tile-count-keyed coherence feasibility

**Status:** Design, awaiting owner review. Supersedes the `core/range ≥ 25` framing of Stage C in
`phase5_scope_spec.md` §5.2/§7 and `docs/superpowers/specs/2026-06-28-phase5-autotune-loop-design.md`
§4/§11, and the Stage-C plan Tasks 15–18.
**Builds on:** the Phase-5 autotune loop at HEAD. Phase-5 Stages A–B are unchanged. This redesign only
touches Stage C: the feasibility predicate, the frontier artifact, and the Stage-C DoD.
**Governing discipline:** the coarse-correction / decomposition-redesign stays **owner-deferred**
(`phase5_scope_spec.md` §6) — this design does NOT build it. Stage C still only *respects* the boundary,
*quantifies* its cost, and hands the owner the redesign input. Coherence is gated **worst-case-localized**
(invariant 6); feasibility is a **hard barrier** (invariant 3); the predicate is **capability-conditional**
(invariant 4) and **pluggable** (invariant 5).

---

## 1. Why Stage C is redesigned

The original Stage C keyed feasibility on `core/range ≥ 25` (`CoherenceFeasibility.CORE_OVER_RANGE_MIN`),
a bound measured in Phase 4 on a GMRF prior that carried a **marginal-variance bug** (`matern_precision`
omitted the SPDE `1/(4πκ²·A_cell)` normalisation → prior σ² ~10³× too large). Fixing it (`6cce45b`) and
re-measuring dissolved the two things the bound rested on — the conditioning collapse (global `Q_post`
eigmin 2.5e-7 → 2.2, cond 4.4e8 → 73) and the seam **marginal** collapse (strict-min 1.9e-7 → 0.45). The
default `GmrfTreeKrigingSolve` now holds the marginal seam contract. `core/range ≥ 25` was a bug artifact.

The real, non-artifact question — *does the JOINT cross-seam covariance stay valid as tiles → global?* —
was then measured directly (§2). The answer redefines the boundary: it is keyed on **tile count**, not
`core/range`, and it is **capability-conditional**.

## 2. The measurement (the evidence this design rests on)

Tooling: `scripts/diag_crossseam.py` + `tests/unit/_tree_gate.py::GateFixture` helpers. Constant-core
sweep: a large synthetic obs fixture (obs-value-independent, since `Q_post = Q_prior + HᵀR⁻¹H`) windowed
into a growing centered box so the per-tile core span is held at **4°** while tile count grows — the true
"tiles → global" scaling, with the fixed-domain confound (core/range shrinking toward degenerate cores)
removed. Metrics on the DEFAULT tree-kriging driver vs a dense-global reference:

**SAMPLES/COVARIANCE — joint cross-seam correlation (`edge_seam_corr_err`,** the robust metric: per
grid-adjacent seam node pair, `|emp_cov − ref_cov| / √(σ_a σ_b)` — a correlation-unit error, immune to
the near-zero-denominator artifact of the block rel-err). Denoised at **M=8000** with a
**selection-controlled worst-of-K** (K=418 = smallest tiling's node-pair pool, mean over 400 seeded
subsamples), so "worst grew" means seams degraded, not that more pairs were sampled:

| tiles | marg strict-min | corr_med | corr_p95 | corr worst-of-K (± estimator std) |
|-------|-----------------|----------|----------|-----------------------------------|
| 4     | 0.498           | 0.015    | 0.232    | **1.105 ± 0.000** (K = full pool) |
| 9     | 0.512           | 0.023    | 0.270    | **0.506 ± 0.079** (thin: ≈ tol)   |
| 16    | 0.434           | 0.031    | 0.344    | 0.823 ± 0.135                     |
| 25    | 0.380           | 0.052    | 0.798    | 2.033                            |
| 36    | 0.342           | 0.070    | 0.427    | 2.108                            |

- **Worst-case (the invariant-6 gate) exceeds `joint_tol = 0.5` at every tested tiling, NON-monotonically**:
  1.105 @2×2, 0.506 @3×3, 0.823 @4×4, ~2.0 @5×5, ~2.1 @6×6 (2×2 is worse than 3×3–4×4 — the worst-of-K is
  not monotone in N). The `± std` column is the worst-of-K estimator uncertainty (subsample-selection
  dispersion; it does NOT include the per-pair M=8000 sampling floor, ~0.01). **Read it honestly: 2×2
  (1.105), 4×4 (0.823), 5×5, 6×6 exceed tol by ≫ 1 std — robust; 3×3 (0.506 ± 0.079) clears tol by only
  0.006, i.e. it is statistically indistinguishable from 0.5.** So "every tiling exceeds tol" holds at the
  point estimate, but the 3×3 margin is within noise — no tested multi-tile geometry is *clearly* feasible,
  and 3×3 is the sole ambiguous cell.
- **Global infeasibility is the robust claim:** by 25 tiles the worst-of-K is ~2.0 and rising; extrapolated
  to a global product (thousands of tiles) it exceeds any sane tol by a wide margin. This does not rest on
  the thin 3×3 margin.
- **Bulk is a sparse catastrophic tail:** typical seam is excellent (median 1.5%→7%); p95 good then crosses
  tol≈0.5 around N ~16–20 tiles. So the worst-case ≥ tol is a *handful* of catastrophic pairs (~0.24% at
  2×2), not uniform mediocrity.
- **Third symptom (same tier):** coherent SAMPLES under-disperse at seams — `marginal_contract_ratios`
  (sample-var / reported-var) strict-min drifts 0.498 → 0.342 with tile count.

**MARGINAL_VARIANCE — reported-marginal accuracy (`marginal_accuracy_errs`,** analytic / sampling-free:
relative error of the blend's reported `(Σ w_i σ_i)²` vs dense-global `diag(Σ_g)` at seams — the
MARGINAL_VARIANCE capability's own deliverable, NOT sample dispersion):

| tiles | marg_med | marg_p95 | marg_max |
|-------|----------|----------|----------|
| 4     | 0.008    | 0.055    | 0.069    |
| 9     | 0.007    | 0.063    | 0.140    |
| 16    | 0.008    | 0.069    | 0.130    |
| 25    | 0.009    | 0.083    | 0.149    |
| 36    | 0.010    | 0.070    | 0.132    |

- Worst-case **~13–15%, FLAT with tile count** (not growing) — the opposite of the joint metric. Per-tile
  reported marginals with adequate halos are locally accurate.

**Conditioning** is a dead issue throughout: global `Q_post` eigmin flat ~3.1–3.8, cond ~55–66,
tiling-independent (it is the untiled reference).

## 3. The redesigned feasibility model

**Coherence = the JOINT cross-seam contract of the SAMPLES/COVARIANCE capability** (valid cross-seam
gradients/transports — the definitional purpose of a coherent sampler). Gating on the marginal while the
joint is measured-broken is the false-green the project fought (invariant 6). The barrier is therefore the
worst-case joint cross-seam correlation error, and it is **capability-scoped** (invariant 4):

- **SAMPLES / COVARIANCE** → at the shipped `joint_tol = 0.5`, every tested multi-tile geometry's worst-case
  point estimate exceeds tol, so the feasible region is **empty** and `n_star_joint = 1` (only the untiled
  single-tile solve is joint-valid; it does not scale → the owner-deferred fix is the only path to global
  joint coherence). **Caveat (see §2):** the worst-of-K is *non-monotone in N* (2×2 = 1.105 > 3×3 = 0.506),
  so `feasible iff N ≤ n_star_joint` is valid ONLY as the **empty-region shorthand at tol = 0.5** — not a
  general monotone-in-N law. At a *loosened* tol (> ~0.51) feasibility becomes **non-nested** (3×3 would pass
  while 2×2 fails), which a tile-count threshold cannot express — it would require a lookup on the measured
  `N → worst-case` curve. The robust, tolerance-insensitive claim is **global** infeasibility; the regional
  `n_star_joint = 1` is the tol = 0.5 point-estimate shorthand, carrying the thin-3×3-margin caveat.
- **MARGINAL_VARIANCE** → feasible iff the (measured, **flat**) worst-case reported-marginal error
  ≤ `marg_tol`. Measured worst-case ~13–15%, flat in N → feasibility is **tile-count-independent**:
  `n_star_marg` is effectively unbounded **iff `marg_tol ≥ ~0.15`**, else empty. So "MARGINAL_VARIANCE ships
  globally" is conditional on *accepting ~15% worst-case marginal error* — visible in the predicate via the
  named `marg_tol`, not buried in a constant. The basis is the **flatness** (a fixed, characterized error
  that does not accumulate with tile count), not an unbounded-`N` law. Correctly labeled `MARGINAL_VARIANCE`,
  **not** "coherent."
- **POINT** → unconstrained (no seams).

The predicate keys on **tile count N** for the joint tier, never `core/range` (measured: tripling the core
barely moved the worst-case; tile count is the driver). Both tolerances (`joint_tol`, `marg_tol`) are named,
swappable parameters (the old "25 was swappable" pattern); the *global* empty-region headline is
tolerance-invariant, the *regional* boundary is tolerance-dependent (and, for the joint tier, non-nested).

### 3.1 `feasibility.py` changes

```python
@dataclass(frozen=True)
class TileGeometry:
    n_tiles: int                 # the predicate's key
    core_size_deg: float         # recorded context (artifact); predicate ignores
    range_km: float              # recorded context (artifact); predicate ignores
    tiling_id: str

class CoherenceFeasibility:
    """Capability-conditional, tile-count-keyed. Replaces core/range >= 25 (bug artifact)."""
    joint_tol: float = 0.5        # worst adjacent-seam corr-err bound (swappable)
    n_star_joint: int = 1         # tol=0.5 EMPTY-REGION SHORTHAND (worst-of-K > tol at all tested N>=2,
                                  #   non-monotone; NOT a monotone law — see design §2/§3). Only N=1 valid.
    marg_tol: float = 0.20        # accepted worst-case reported-marginal rel error (swappable)
    marg_worst_case: float = 0.15 # MEASURED, FLAT in N (~13-15% up to 36 tiles) — a characterized constant
    def feasible(self, params, tile_geometry, required_capabilities) -> bool:
        caps = required_capabilities
        if caps & {SAMPLES, COVARIANCE}:  return tile_geometry.n_tiles <= self.n_star_joint
        if MARGINAL_VARIANCE in caps:     return self.marg_worst_case <= self.marg_tol  # flat -> N-indep.
        return True                        # POINT / no joint requirement

@dataclass
class RelaxedCoherenceFeasibility:
    """The redesign's interface (invariant 5): widens the joint region without touching the tuner.

    The owner-deferred coarse-correction supplies this. n_star_joint below is ILLUSTRATIVE of the
    mechanism (a wider tile-count bound), NOT a measured value — the fix has not been built or measured.
    """
    n_star_joint: int = 64        # ILLUSTRATIVE only (unmeasured)
    joint_tol: float = 0.5
    marg_tol: float = 0.20
    marg_worst_case: float = 0.15
    # same feasible() body, reading its own bounds.
```

**Dies:** `CoherenceFeasibility.CORE_OVER_RANGE_MIN`, the `KM_PER_DEG` ratio arithmetic, and
`RelaxedCoherenceFeasibility(min_ratio)` (all `core/range`-keyed). **Kept:** the capability-conditional
`_JOINT_CAPS` gate structure, the `FeasibilityPredicate` Protocol, `TileGeometry` (gains `n_tiles`).

## 4. What is kept, what dies

- **KEEP — the hard-barrier machinery (plan T15):** the gate-before-`submit` loop that excludes an
  infeasible trial before any solve/score (`scores=None`, invariant 3). Sound; only the predicate it calls
  changes. Test 4 becomes: a `SAMPLES/COVARIANCE` trial at `N ≥ 2` is excluded before the scorer is called.
- **KEEP — worst-case-localized reduction (plan T16):** `worst_case_coherence` = strict worst over seams,
  never median/aggregate (invariant 6). Re-point it at the validated adjacent-seam corr-err (worst-of-K),
  the metric §2 established. The `edge_seam_corr_err(s)` helpers already implement it.
- **REWRITE — the frontier artifact (plan T17):** from `core/range ≥ 25` arithmetic (`feasible=ratio≥25`,
  `λx≈range`) to the measured both-tiers tile-count table.
- **REWORD — the Stage-C DoD (plan T18):** §6 below.
- **RETIRE / REWRITE — `tests/test_core_authoritative_gate.py`** strict-xfail
  `test_acceptance_operational_cross_seam_covariance_recovered` (core/range-premised). Replace it with a
  CONCRETE strict-xfail that preserves the known-unmet-target-as-xfail pattern: assert that a
  `SAMPLES/COVARIANCE` product at an operational multi-tile geometry (`N ≥ 2`) is **feasible** under the
  default `CoherenceFeasibility()` — which strict-`xfail`s today (`n_star_joint = 1` excludes it) and
  `xpass`es only once the owner-deferred coarse-correction widens `n_star_joint` above 1. The known-broken
  target is pinned in code, not prose.

## 5. The frontier artifact + measurement split

The **predicate stays cheap** (baked constants only) so invariant 3's hard-barrier-before-solve holds — no
measurement in the loop. The **heavy measurement stays in `scripts/diag_crossseam.py`** (committed,
reproducible, already carrying both sweeps + the marginal sweep). `application/tuning/tradeoff.py` becomes a
**thin consumer** that reads the recorded curve and emits the owner-facing frontier doc
`docs/validation/phase5_feasibility_resolution_frontier.md`. (Productionizing the measurement into `src/`
is deferred: the metric set is still settling and a measurement module in `tuning/` risks the loop
importing it — an invariant-3 hazard. Revisit once the metric set stabilizes.)

The artifact reports **both tiers** (Option 3's content, as artifact not predicate):
- **SAMPLES/COVARIANCE tier:** worst-case joint corr-err (empty region, `n_star_joint = 1`), plus the three
  symptoms and the sparse-tail bulk (median/p95, ~2× growth) — telling the owner the coarse-correction must
  rescue a *sparse set of catastrophic seam pairs*, not fix a uniform deficit.
- **MARGINAL_VARIANCE tier:** worst-case ~15% flat → ships at large `n_star_marg`.

The predicate gates the worst-case only (invariant 6); the median/p95 tiers are reported, never gated.

## 6. Stage-C DoD (reworded)

Stage C is closed when:
1. **Boundary respected:** the tuner provably never solves/scores a `SAMPLES/COVARIANCE` trial at `N ≥ 2`
   (hard-barrier spy test, capability-conditional).
2. **Boundary quantified worst-case-localized:** the joint deficit is measured by the adjacent-seam corr-err
   worst-case (never median), and the frontier artifact carries both tiers.
3. **Boundary relaxable (the redesign interface):** `RelaxedCoherenceFeasibility` with a larger
   `n_star_joint` widens the feasible region with no change to the tuner (invariant 5).
4. **Boundary surfaced, robust claim first:** the frontier doc leads with the **robust** finding — GLOBAL
   `SAMPLES/COVARIANCE` is infeasible (worst-of-K ~2.0 by 25 tiles and rising, extrapolating past any sane
   tol at thousands of tiles) — for the **real** reason (worst-seam joint cross-seam covariance accumulates
   with tile count), **not** the refuted conditioning collapse (the fixed GMRF prior bug). It then presents
   the **regional** `n_star_joint = 1` as the *tol = 0.5 point-estimate shorthand*, explicitly carrying:
   (a) the **worst-of-K is non-monotone in N** (2×2 > 3×3); (b) its **estimator uncertainty** (the `± std`
   column) so the thin **3×3 = 0.506 ± 0.079 vs 0.5** cell is shown to be *within noise* — no tested
   multi-tile geometry is *clearly* feasible, but the small-N exclusion rests on a thin margin. It states
   that `MARGINAL_VARIANCE` ships **conditional on accepting ~15% worst-case marginal error** (`marg_tol ≥
   ~0.15`), on the basis of the **flatness** (fixed, non-accumulating). And it states the single-fixture
   provenance (§8).

Stage C does **not** attempt DUACS-class global coherent products at operational range (the boundary forbids
it until the owner-deferred fix). It proves the tuner respects the boundary and quantifies its cost.

## 7. Doc amendments (the write-up to apply)

- **`phase5_scope_spec.md` §5.2** — replace the `core/range ≳ 25` `CoherenceFeasibility` description with the
  capability-conditional, tile-count-keyed predicate; note the measurement supersedes the Phase-4 bound.
- **`phase5_scope_spec.md` §7 Stage C** — reword the DoD per §6.
- **design `…2026-06-28-…-design.md` §4** — replace the `TileGeometry`/`CoherenceFeasibility` code block
  with §3.1; `RelaxedCoherenceFeasibility` rekeyed on tile count.
- **design §11 Stage C** — reword per §6; drop the `core/range ≥ 25` gate description.

## 8. Provenance caveat (carried into the DoD)

`n_star_joint = 1` / empty-region rests on ONE synthetic fixture (4° core, 300 km range, 1° grid, M=8000,
selection-controlled). The **conclusion is physically robust** — independent-core tiling destroys cross-seam
correlation, it worsens with seam count, and larger cores do not rescue it (the confound was killed) — but
exact universality across ranges and obs densities is one-fixture-based. The swappable predicate
(`joint_tol`, `n_star_joint` as named parameters) absorbs regime variation. State this honestly in the
frontier doc; do not imply regime-universality.

## 9. Non-goals (unchanged from `phase5_scope_spec.md` §6)

- **The coarse-correction / decomposition-redesign** (cores≫range tiling / overlapping-Schwarz-with-coarse-
  correction / global low-rank seam basis) stays **owner-owned and deferred.** This design surfaces the input
  to that decision; it does not build the fix.
- **FEM as a tuner target**, **lat-varying parameter fields**, **BO as the initial strategy**,
  **scalarized objectives / soft feasibility penalties / joint metrics in the objective** — all remain out,
  exactly as in the Phase-5 scope.

## 10. Invariants preserved

Invariant 3 (hard barrier before solve — predicate stays cheap, gate before `submit`); invariant 4
(capability-conditional — the barrier binds only for `SAMPLES/COVARIANCE`); invariant 5 (pluggable —
`RelaxedCoherenceFeasibility` is the redesign interface); invariant 6 (worst-case-localized — the predicate
gates worst-case adjacent-seam corr-err, never median/aggregate; median/p95 are reported, never gated).
