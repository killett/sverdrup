# Pin 43 — the σ-route settling measurement (2026-07-27)

**STATUS: RECORDED, NOT SEALED.** Evidence node
`phase14.stage1.ensemble_settling_measurement`. Nothing here licenses a σ
verdict (owner pin 49); the whole rubric amendment is T17's, behind T15.
The seal is untouched and `seal_run check` is GREEN at v1.

Owner pin 43 ordered this instead of sealing `1.14` on a two-sample basis
with a known-broken `N_eff` estimator: ~200 disjoint random member
partitions per tile, replayed from the persisted member stores, no
solves, at two split sizes to TEST the assumed m-invariance rather than
inherit it.

## What was run

`scripts/phase14_settling_measurement.py`, both seam tiles, 200
partitions per tile per split size, split sizes 50/50 and 25/25, base
seed 20260727. Wall ~22 min, no solves.

The quantity is the same `T` the deferred Rule 0.b is about:

    T = RMS(σ_A − σ_B) / F_ens ,   F_ens = σ_pooled / √(size−1)

with the **pin-38 POOLED (quadratic-mean) σ level**. Both sides come from
the SAME tile's SAME solve, so they differ only by which members were
drawn: no seam, no lattice difference, no CRN difference.

### Why it was cheap, and why that is not a shortcut

The lineage evaluator `std_fields` builds, per day, the per-member
blended field `acc` of shape `(n_nodes, m)` and returns
`acc.std(axis=1, ddof=1)`. This run captures `acc` on the strip ONCE per
tile and takes the σ of any member subset from it directly — the same
arithmetic on the same numbers. Replaying each partition through the
evaluator instead would have cost ~21 h of CPU for an identical answer.

The identity is **checked, not asserted**, on every run at full `m`, to
an exact-zero tolerance, against BOTH the lineage evaluator and the map
T4 persisted. Both came back **0.0** on both tiles. The ordered
`[0:50]` vs `[50:100]` split — one specific partition — reproduces the
committed T4 half-split readings to `2.2e-16` (`seam_n`) and `0.0`
(`seam_s`).

One implementation fact worth keeping, because the first attempt failed
its own check at `4.2e-17`: the member axis must be the **fastest-varying**
one. With members on axis 0 the same values reduce in a different
summation order and land a few ULP away. Member-last reproduces the
persisted map bit-for-bit. Selecting members by index array still costs
~1.1e-15 relative (floating-point associativity), which is reported
beside the measurement rather than asserted away.

## Results

Pooled over both tiles, n = 400 partitions per split size:

| split | mean T | sd | q95 | q99 | max |
|---|---|---|---|---|---|
| 50/50 | 0.99755 | 0.0063 | 1.00777 | 1.01237 | 1.01535 |
| 25/25 | 0.99397 | 0.0061 | 1.00389 | 1.00952 | 1.01705 |

Per tile the two are consistent (`seam_n` 0.99832 / 0.99466, `seam_s`
0.99677 / 0.99327; sd 0.0057–0.0065 throughout).

### 1. The null is tight, and centred just below 1

The realized null spread is **sd ≈ 0.006**, and no draw out of 400 at
50/50 exceeded **1.016**.

### 2. m-invariance is REJECTED — and the departure has a closed form

Pin 43(b) asked whether the distribution is m-invariant. It is not: the
50/50 and 25/25 means differ by **+0.0037 (+5.7 naive SE)** on `seam_n`
and **+0.0035 (+5.8 SE)** on `seam_s` — same sign, nearly the same size,
on two independent tiles.

The departure is **not** an `N_eff` effect. It is the exact-vs-asymptotic
gap in the floor's own definition. For an m-member Gaussian σ,
`E[T] = √(2(m−1)(1−c4(m)²))`:

| m | predicted E[T] | measured mean T |
|---|---|---|
| 25 | 0.994672 | 0.99397 |
| 50 | 0.997420 | 0.99755 |
| 100 | 0.998730 | — (not splittable at m=100) |

Agreement to `7e-4` and `1e-4`. **So the m-dependence is exactly
predictable and T17 can handle it in closed form rather than by margin.**
The assumption pin 43(b) told us to test is false; the correction is
known.

### 3. The factor is settled far below both prior candidates

Against a null whose 400 realizations top out at 1.016:

- the withdrawn **1.07** (E-3) sits ~11 sd above the null mean;
- pin 32's carried-over **3.0** sits ~320 sd above it.

A factor near **1.02–1.03** already exceeds every realized null draw.
**Pin 43(a)'s caveat applies to all of this and travels with the number:**
200 partitions of the SAME 100 recorded members share draws, so this
spread is COMBINATORIAL variability, not ensemble-to-ensemble
variability, and UNDERSTATES the true null spread. A factor derived from
it must carry margin for that. Separately, n = 200 supports quantiles to
about q95–q99; **a 0.999 quantile is NOT estimable from this sample and
must not be read off it.**

### 4. ⛔ A small factor does NOT restore a reachable CLEAN cell

This is the finding that outlives the factor. At m=100 on the T4
geometry:

    F_ens = 0.00370828 m ,  D_int_σ = 0.00326550 m ,  F_ens/D_int_σ = 1.1356

The pin-36(c) reachability condition is `factor × F_ens < clean_max ×
D_int_σ` with sealed `clean_max = 1.0`. Since the floor ALONE is already
1.136× the reference dispersion, the condition fails for **every factor
≥ 1.00**:

| factor | CLEAN reachable at m=100 | min m for CLEAN |
|---|---|---|
| 1.00 | no | 129 |
| 1.02 | no | 134 |
| 1.03 | no | 137 |
| 1.05 | no | 142 |
| 1.07 | no | 148 |
| 3.00 | no | 1151 |

**Deriving the factor was necessary and is now done; it is not
sufficient.** The σ instrument at m=100 still has no reachable CLEAN
cell, and the remedy has to come from `m`, from the σ denominator, or
from retiring the route — not from the factor. This is an owner decision,
not an executor one.

**Superseded on the owner's reading of this section:** pin 31's *do NOT
raise m* was written against ~512 members and **pin 53 has since REOPENED
it** (not reversed it) at the settled requirement of m ≥ 137, priced at
`docs/superpowers/2026-07-27-phase14-m137-price.md`. *Do NOT change the σ
denominator* still stands. See the owner-disposition section at the foot
of this document.

### 5. T4's cross-tile reading sits BELOW the measured null

Recomputed in this same pin-38 construction at m=100:

    RMS(Δσ) = 0.00360653 m ,  F_ens = 0.00370828 m ,  T_cross = 0.97256

The measured null centre extrapolates to 0.99873 at m=100 with sd ≈
0.006, so **T_cross is ~4.2 sd BELOW the null centre**. The σ route
carries no excess whatever over pure ensemble Monte-Carlo noise — which
corroborates the committed diagnosis from a direction it did not use.

It also raises a question this measurement does not answer: a reading 4
sd *below* an independent-null centre suggests the two cross-tile σ
estimates are positively correlated, i.e. the independence premise Rule
0.b is derived under is already violated in the RECORDED pair, before
T14 pairs the CRN deliberately. Within-tile partitions land ON the
predicted independent value, so whatever couples the cross-tile pair is
not present within a tile. **Flagged, not resolved** — it is pin 45(c)'s
CRN-state-conditional problem arriving from the other side, and it
belongs to T15/T17.

## Caveats carried (all recorded in the evidence node)

1. **Pin 43(a):** partitions resample the same 100 members; the spread is
   combinatorial, not ensemble-to-ensemble, and understates the truth.
2. **Quantile reach:** n = 200 supports ~q95–q99, not q999.
3. **m-invariance is false** (finding 2) — measured, with a closed form.
4. The within-tile partition null is not identical to a cross-tile null
   (finding 5).

## What this does NOT do

No seal touched; `seal_run check` GREEN at v1. No σ verdict changed —
both σ rows remain `NOT_ESTABLISHED (ensemble MC artifact — see
diagnosis)`. No factor adopted: adopting one is T17's, after T15, with
pin 42's per-outcome probability fields and pin 44's oracle floor
construction as acceptance criteria.

**Per pin 43's stop condition, the owner stops here with this measurement
in hand, before T14.**

---

## Owner disposition — pins 51–55 (2026-07-27)

The measurement above was reported to the owner, who ruled pins 51–55
(`docs/superpowers/2026-07-27-owner-ruling-crn-sigma-rule0.md`, PART 6). What that
changed:

- **Pin 53 SUPERSEDES pin 31's "do NOT raise m"** — reopened, not reversed. The
  rejection rested on ~512 members, from a 2× owner margin over the un-derived 3×
  factor pin 36 later overturned. At the settled factor the requirement is
  **m ≥ 137**. **No remedy is chosen**: T14 collapses `F_ens` by design, so the
  decision sits with Rule 0.b in T17. m=137 is PRICED at
  `docs/superpowers/2026-07-27-phase14-m137-price.md` — and the pricing found that
  **~512 was exactly the RAM knee** (the model's phase-max starts tracking m at
  m ≈ 512), so the original rejection was priced at the knee and m=137 sits at 27%
  of it. m=137 is not the binding constraint on either RAM or wall; T5 stays
  blocked for the reasons it already was.
- **Pin 54 ENDORSED the closed form for exact use in T17**, on the standing
  condition that it be **test-pinned at the m actually used**. Implemented as
  `sverdrup.validation.ensemble_settling.expected_t` and pinned in
  `tests/test_ensemble_settling.py` against (a) the published c4 control-chart
  table with tolerance propagated from that table's own 4-decimal precision — the
  amplification is ~47× at m=25, so a naive tolerance is wrong here — (b) an
  independent Monte-Carlo simulation that uses no Gamma function at all, and
  (c) the two measured means, 0.99397 at m=25 and 0.99755 at m=50.
- **Pin 54 also binds the quantile reach, and it is recorded at
  `phase14.stage1.ensemble_settling_measurement.pin_54_condition`:** n=200 supports
  q95–q99 only; **q999 is NOT estimable from this sample and NO THRESHOLD MAY RELY
  ON A QUANTILE THE MEASUREMENT CANNOT REACH.** A factor set from an unreachable
  quantile is not derived from this measurement whatever it cites.
- **Pin 55 SHARPENS pin 45(c)** on the strength of §5: Rule 0.b's conditional form
  must be parameterized by **MEASURED correlation** between the two σ fields, not
  by a binary paired/unpaired state — **there may be no clean unpaired limit to
  reduce to**. Carried into T15's acceptance criteria as a named question:
  measure the correlation, do not infer it from lattice geometry alone.
- **Pins 51 and 52 corrected the tracker:** T13 flipped to `completed` with its
  criteria replaced by what actually landed and the withdrawn criteria pointed at
  T17 — and, in the same commit, **T14 was blocked mechanically** behind a new
  userGate task (id 18) that only an owner ruling can clear, so that flipping T13
  did not turn the stage's highest-risk change green as the session ended.
