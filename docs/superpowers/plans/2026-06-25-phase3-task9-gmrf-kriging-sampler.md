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
  nearest-node value handoff. **Separator precondition (asserted, not assumed):** the
  handed-forward overlap strip must be a **graph-separator in `Q`** between the already-processed
  interior and the not-yet-processed interior — otherwise the sweep is exact for the per-tile
  *marginal* but **wrong for the joint law** (the "passes per-tile marginals, wrong joint" bug).
  For the α=2 `(κ²−Δ)²` stencil the precision couples nodes within **grid-distance 2** (reach =
  2), so the overlap must be **≥ 2 grid columns thick** in the sweep direction. The driver checks
  it cheaply (no `Q` edge bridges from a pre-overlap-interior node to a post-overlap-interior node
  / overlap strip width ≥ `stencil_reach`) and **fails loudly** if violated. **Halo-policy
  confirmation:** `ScaleAwareHalo(k·corr_len)` with `corr_len`≈300 km on a ~111 km/1° grid gives
  a halo of ≈2.7 nodes even at `k=1` (many stencil-widths at the policy default `k≥1`), so the
  overlap comfortably separates — confirm this in the gate fixture and state the
  `overlap ≥ stencil_reach` implication in the docstring.
- **9c — validity oracle** `tests/unit/test_gmrf_kriging_oracle.py`: the three joint-covariance
  checks in (2), on 2-tile and 3-tile dense-formable grids, **plus a fourth — the separator
  negative control:** a deliberately **too-narrow overlap (1 column, < reach)** must produce a
  **wrong joint covariance** (cross-seam cov departs from the dense reference) and trip the 9b
  separator assertion. This tests the **boundary of validity** — proving the separator property
  is the real precondition, not folklore, rather than assuming "exact for a chain."
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

## Resolved: sweep, with separation as a checked-and-bounded property (owner decision)

The forward sweep is exact for the **joint law** only when each handed-forward overlap is a
**`Q`-separator** between the already-processed and not-yet-processed interiors (the Markov
factorization a GMRF on a tree-structured tile chain provides *iff* the separator is a full cut).
For a chain of tiles with halos sized by the existing policy (a multiple of the local correlation
length — many stencil-widths for a Matérn field), the overlap separates comfortably, so the sweep
is exact and far cheaper than the alternative. We keep the sweep, but convert "exact for a chain"
from an **assumption** into a **checked-and-bounded property**: 9b asserts separation and fails
loudly; 9c's negative control proves the joint law goes wrong exactly when separation is violated.
Standing rule: if the separator assertion or the negative control reds in a way that says the
**chain construction** is wrong (not the fixture), **stop and surface before** reaching for the
pre-drawn variant.

**The pre-drawn-joint variant — documented unconditional fallback (not built now).** Draw ONE
auxiliary joint sample over the *entire* union of shared strips up front, hand every tile its
overlap values from that single pre-drawn field; correctness then **does not depend on the
overlaps being separators** — every tile conditions on values already mutually consistent by
construction, regardless of `Q`'s cross-strip connectivity. Heavier (one joint draw over all
strips). It is explicitly the variant a **2-D / FEM tiling needs** (see the Phase-4 note below):
when the tile-adjacency graph stops being a chain (tiles meeting at corners and along multiple
edges), single-pass sequential conditioning is no longer exact, and the pre-drawn-joint (or a
junction-tree generalization) is required. Phase 3 inherits the known alternative rather than
rediscovering it.

**Phase-4 caveat (mirrored into `phase3_scope_spec.md §5.3.1`):** GMRF cross-tile coherence via
the single-pass sweep is exact **only for tree-structured tile adjacency**; 2-D / FEM tilings
require the pre-drawn-joint or junction-tree variant. Written down now so the conditionally-true
property is not inherited as unconditionally true.
