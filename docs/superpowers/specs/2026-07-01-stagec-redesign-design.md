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

| tiles | marg strict-min | corr_med | corr_p95 | corr worst-of-K |
|-------|-----------------|----------|----------|-----------------|
| 4     | 0.498           | 0.015    | 0.232    | **1.105**       |
| 9     | 0.512           | 0.023    | 0.270    | 0.506           |
| 16    | 0.434           | 0.031    | 0.344    | 0.823           |
| 25    | 0.380           | 0.052    | 0.798    | 2.033           |
| 36    | 0.342           | 0.070    | 0.427    | 2.108           |

- **Worst-case (the invariant-6 gate): ≥ 1.0 from the smallest tiling** (2×2 worst-of-K = 1.105) and grows
  ~2× to ~2.1 at 36 tiles. Selection-controlled + denoised → real, not small-n noise, not pure selection.
- **Bulk is a sparse catastrophic tail:** typical seam is excellent (median 1.5%→7%); p95 good then crosses
  tol≈0.5 around N ~16–20 tiles. So the worst-case ≥1 is a *handful* of catastrophic pairs (~0.24% at 2×2),
  not uniform mediocrity.
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

- **SAMPLES / COVARIANCE** → feasible iff `N ≤ n_star_joint`. Measured: worst-case ≥ tol from the smallest
  tiling → the feasible region is **empty** at any operational multi-tile geometry. Mechanically
  `n_star_joint = 1` (only the untiled single-tile solve is joint-valid; that does not scale → the
  owner-deferred fix is the only path to global joint coherence).
- **MARGINAL_VARIANCE** → feasible iff `N ≤ n_star_marg`. Measured worst-case ~15%, flat → `n_star_marg`
  is effectively unbounded within the tested range; the marginal global product genuinely ships. This is
  the honest global offering, correctly labeled `MARGINAL_VARIANCE` — **not** "coherent."
- **POINT** → unconstrained (no seams).

The predicate keys on **tile count N**, never `core/range` (measured: tripling the core barely moved the
worst-case; tile count is the driver). Tolerances are named, swappable parameters (the old "25 was
swappable" pattern); the empty-region headline is tolerance-invariant.

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
    joint_tol: float = 0.5       # worst adjacent-seam corr-err bound (swappable; region empty regardless)
    n_star_joint: int = 1        # MEASURED empty region: only untiled N=1 is joint-valid at op. range
    n_star_marg: int = 1_000_000 # MEASURED ~flat 15% worst-case -> effectively unbounded in tested range
    def feasible(self, params, tile_geometry, required_capabilities) -> bool:
        caps = required_capabilities
        if caps & {SAMPLES, COVARIANCE}:  return tile_geometry.n_tiles <= self.n_star_joint
        if MARGINAL_VARIANCE in caps:     return tile_geometry.n_tiles <= self.n_star_marg
        return True                        # POINT / no joint requirement

@dataclass
class RelaxedCoherenceFeasibility:
    """The redesign's interface (invariant 5): widens the tile-count bounds without touching the tuner."""
    n_star_joint: int = 64
    n_star_marg: int = 1_000_000
    # same feasible() body, reading its own bounds — the owner-deferred coarse-correction supplies this.
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
  `test_acceptance_operational_cross_seam_covariance_recovered` (core/range-premised). Its replacement:
  the deferred fix must move `n_star_joint` above 1 (a non-empty `SAMPLES/COVARIANCE` region) at an
  operational tiling — i.e. `RelaxedCoherenceFeasibility` widening the region is the redesign's success
  signal, not a core/range xpass.

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
4. **Boundary surfaced:** the frontier doc states — for the **real** reason (worst-seam joint cross-seam
   covariance accumulates unbounded with tile count), **not** the refuted conditioning collapse (the fixed
   GMRF prior bug) — that global `SAMPLES/COVARIANCE` is infeasible at operational range; that
   `MARGINAL_VARIANCE` ships within its (measured, flat) bound; and the single-fixture provenance (§8).

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
