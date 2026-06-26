# Task 9 (reworked) — GMRF cross-tile coherence via conditioning-by-kriging

> **Status: PLAN — awaiting approval. No sampler code written.** Implements spec
> `phase3_scope_spec.md §5.3.1` (amendment 2026-06-25). Gated by the owner on three
> points: (1) cross-covariance block method + cost scaling, (2) a joint-covariance oracle
> (not marginals), (3) global-realization handoff stated as values-not-seeds.

**Goal:** Replace the native-shared-`w` `GmrfPrecisionSolve` (which leaves cross-seam derived
quantities ~50% under-dispersed — `phase3_scope_spec.md §5.3.1`) with a conditioning-by-kriging
driver that makes overlapping tiles agree on shared nodes by conditioning each tile's exact
posterior draw toward **one globally-consistent realization**, and re-gate Task 9 on the
promoted contract (distinct-tiles-by-construction + cross-seam derived-quantity parity).

---

## The three gated points (answered before any code)

### (1) Cross-covariance blocks — method and cost scaling

The kriging correction for tile `i` is

```
x_c^i = x_u^i + Σ^i_{I,S} · (Σ^i_{S,S})⁻¹ · (x_S − x_u^i|_S)
```

where `I` = the tile's interior nodes, `S` = its shared (overlap) nodes with the already-fixed
neighbour, `Σ^i = (Q^i)⁻¹` is the **tile's posterior covariance**, and `x_S` are fixed target
**values**.

`Σ^i_{·,S}` are **full columns of `(Q^i)⁻¹` for the shared nodes** — a tall off-diagonal block.
**These are generally outside the `L+Lᵀ` selective-inverse pattern, so Takahashi (B2) does NOT
give them.** The amendment's "read off the precision via the selective inverse / factor — never
densely" is satisfied by the **factor**, not Takahashi:

- **Chosen method — per-shared-node back-solves.** For each `j ∈ S`, solve `Q^i z_j = e_j` with
  the cached CHOLMOD factor (`cf.solve`); `z_j = (Q^i)⁻¹ e_j` is a full column. Stack
  `C = [z_j]_{j∈S}` → `Σ^i_{·,S} = C` (shape `n_i × |S|`); `Σ^i_{S,S} = C[S, :]` (dense
  `|S|×|S|`, inverted directly since `|S|` is small).
- **Cost scaling.** Per tile per member: `|S|` sparse back-solves (each `≈ O(nnz(L_i))`) +
  one `|S|×|S|` dense solve `O(|S|³)`. Total per member `≈ Σ_i |S_i| · solve_cost(n_i)`. For the
  Phase-3 `n_lon×1` chain, `|S_i|` is one thin overlap strip (≈ `n_lat × halo_width_nodes`), so
  the added cost is **linear in tile count and overlap width**, dwarfed by the per-tile factor
  itself. `C` depends only on `Q^i` (not the member), so it is **computed once per tile and
  reused across all `M` members** — the per-member cost collapses to one `|S|×|S|` apply.
- **Fallback noted, not built:** if a future wider overlap makes `|S|` large, replace the dense
  `|S|×|S|` inverse with a low-rank handling of the overlap coupling — same correction, cheaper
  apply. Out of scope now; flagged so the cost is legible.

`Σ^i_{·,S}` reuse motivates exposing the columns on the factor/distribution:
`PrecisionDistribution.posterior_cov_columns(shared_idx) -> ndarray (n_i, |S|)` via
`GMRFFactor.solve` per column (cached on the instance).

### (2) The validity oracle checks JOINT covariance, not marginals

Marginal checks (mean, marginal variance) are **exactly the blind spot** that passed the broken
sampler — the same lesson the positive control just taught. On a small grid where `Q⁻¹` is
dense-formable, the oracle (`tests/unit/test_gmrf_kriging_oracle.py`) asserts **joint structure**:

- **Per-tile validity (the kriging theorem).** The corrected ensemble for tile `i` must be an
  **exact sample of tile `i`'s posterior**: empirical **full covariance** `Cov(x_c^i)` matches the
  dense `(Q^i)⁻¹` (whole matrix, not just the diagonal) to MC tolerance. This catches a
  correction that matches the overlap while distorting the interior law.
- **Cross-seam joint coherence.** On a 2-tile and a **3-tile** distinct-tiles setup, the blended
  field's **cross-node covariance across the seam** (and the derived `firstdifference` gradient
  variance) matches the single-tile dense reference, in the **conservative direction**. This is
  the property `§5.3.1 D1` measured at −0.51 for the old driver; the oracle pins it.
- **3-tile transitivity (the seam-of-the-seam).** The L–C and C–R overlaps must be mutually
  consistent: assert the centre tile's corrected draw agrees with **both** neighbours on their
  respective shared nodes within MC tolerance — the check that "passes a 2-tile test and fails a
  3-tile one" is meant to fail on pairwise schemes.

A red in any of these is a **math bug, not a tolerance** (Takahashi/Stage-A discipline).

### (3) Global realization = values handed to tiles, NOT seeds shared across tiles

The failure mode to avoid: "every tile uses the same RNG seed for its shared-node draw" reads
like one realization but, because each tile generates those values through its **own** local map
(`L_i⁻ᵀ`), reproduces the factor-space decorrelation we just diagnosed — same seed, different
map, decorrelated result.

**Construction — single forward sweep, fixed values handed forward.** Per member `m`, inside one
`crossfaded_member(parts, …, member=m, …)` call (the driver already receives all tiles):

1. Order `parts` spatially along the chain (by tile core lon).
2. `targets`: a node-keyed store of **fixed values** on shared nodes, initially empty.
3. For each tile `i` in order:
   a. Draw its **unconditional exact posterior** sample `x_u^i = mean_i + L_i⁻ᵀ w` (`w` an iid
      white vector; `diagonal_noise` keyed on global cell × member for reproducibility — the
      white choice is irrelevant to coherence now, conditioning enforces it).
   b. `S_fixed` = this tile's nodes that already have fixed `targets` (its overlap with the
      already-processed neighbour). If non-empty, **krige-correct** `x_u^i` toward those target
      **values** → `x_c^i` (exact posterior sample agreeing with the fixed boundary). Else
      `x_c^i = x_u^i`.
   c. Write `x_c^i`'s values at this tile's overlap **with the next tile** into `targets` (values,
      not seeds).
   d. Project `x_c^i` to the support and weight-crossfade as today.

The union of corrected tile fields is **one globally-consistent realization**: each tile is
conditioned on the running boundary, so tile 3 inherits tile 2's corrected values which were
conditioned on tile 1 — **transitive by construction**, generated once per member, values handed
forward. It is sequential *single-pass*, not pairwise-independent negotiation. The tile graph for
Phase-3 (`n_lon×1`) is a **chain (a tree)**, for which single-pass sequential conditioning is
exact; the 2-D / spanning-tree generalization is explicitly out of Phase-3 scope and flagged in
the driver docstring.

---

## Task breakdown

- **9a — cross-cov columns on the precision rep.** `GMRFFactor` / `PrecisionDistribution`:
  `posterior_cov_columns(shared_idx)` (per-column back-solves, cached). Unit test vs dense
  `(Q⁻¹)[:, S]` on a small grid, `rtol=1e-9` (oracle discipline).
- **9b — `GmrfKrigingSolve` driver** in `distributions/coherent.py`: the forward-sweep
  conditioning above; replaces `GmrfPrecisionSolve` under `sampler_spec="sparse-precision"` in
  `_DRIVERS` (keep the old class importable only if a test references it — otherwise remove, it
  is the disproven mechanism). Spatial ordering + shared-node detection from tile geometry +
  nearest-node value handoff.
- **9c — validity oracle** `tests/unit/test_gmrf_kriging_oracle.py`: the three joint-covariance
  checks in (2), on 2-tile and 3-tile dense-formable grids.
- **9d — promoted Task-9 gate** (rewrite `tests/test_gmrf_blend.py` Stage-B section):
  distinct-tiles-by-construction fixture (`nL,nR<nFull`, `Q_L≠Q_R`, region/halo chosen so
  `k≥2` cannot collapse tiles to identical); **cross-seam `firstdifference` variance parity**
  vs single-tile reference (conservative direction) as the contracted assertion; pointwise
  `σ`-upper-bound retained; member-correlation demoted to a supporting check. Keep the passing
  OSSE+OSE / provenance / genuine-first-class tests.
- **9e — keep** the already-applied coherence-neutral working-tree edits (OSE no-factor
  moment-crossfade in `_blend_eval_points`; the driver shape-bug fix) — they are orthogonal to
  the coherence mechanism and let the pipeline run.

**Verify (per task, TDD red→green):** `9a` unit oracle; `9c` joint oracle; full
`tests/test_gmrf_blend.py`; `pixi run test -q` (no Phase-2 regression); `pixi run typecheck && lint`.

## Open sub-question surfaced for the review (does not block the plan)

The forward sweep conditions tile `i` only on its **already-processed** boundary (with tile
`i−1`). Tile `i`'s draw on its overlap with tile `i+1` is then handed forward as the target for
`i+1`. This is exact for a chain. If the owner later wants every tile conditioned on a *pre-drawn*
global field on the **entire** union shared-node set (rather than swept), that is an alternative
generator for `targets` (one auxiliary joint draw over the union strips) with the same downstream
correction — heavier, and unnecessary for a chain. Plan assumes the sweep; flag if you want the
pre-drawn variant instead.
