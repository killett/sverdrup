# Phase-14 Stage 1 — T5 price bracket (PIN 27) + probe wall reconciliation (PIN 28)

Date: 2026-07-26
Scope: analysis only. No source file was modified. One cheap measurement was
run (a host-throughput benchmark; §2.3 explains why that one and not a probe
re-run).

Evidence read:

- `data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json`
  (`phase14.stage1.anchor_gate`, `.probe`, `.probe_converged`,
  `phase14.stage0.probe_tile`)
- `logs/stage1_anchor_gate.log`, `logs/stage1_probe_eligible.log`,
  `data/2021a_ssh_mapping_ose/ours/phase14_stage1/probe_converged_maxiter2000.log`
- `src/sverdrup/methods/miost_sizing.py` (`size_tile`, `peak_model`)
- `src/sverdrup/methods/miost_solver.py` (the PCG loop)
- `src/sverdrup/application/ladder.py` (`tier1_eligible`, `authorize`,
  `STAGE0_SPEND_TABLE`)

---

## VERDICT (lead)

**T5 WAITS for the owner. It crosses on two independent axes.**

1. **RAM — the binding constraint, and it fails first.** The T5 configuration
   (19° geometry, 9216 nodes, 9 windows, m=100) has `peak_model_mib = 4715.6`.
   The Tier-1 predicate needs `MemAvailable >= 9431 MiB`. Live MemAvailable on
   this box is **5261 MiB**; `ladder.tier1_eligible(4715.6)` evaluates **False**.
   Worse, the model is m-insensitive by construction (§1.7) and the only m=100
   measurement we have — the anchor — came in **2.128× above its model**. The
   honest expected actual peak for T5 is **6.6 – 10.0 GiB**, which has never
   fit under half of this box's MemAvailable at any point in the recorded logs
   (observed range 8590 – 11,900 MiB).
2. **Wall — crosses every pre-registered Tier-2 ceiling that exists.** The
   bracket is **23.8 – 94.2 h per tile, 95 – 377 h (4.0 – 15.7 days) for the
   four diverse tiles**. The only pre-registered Tier-2 row is `tier2_probe`
   with `max_wall_h = 6.0`. `authorize("tier2_probe", 25.0, 8, 64.0, 23.78)`
   returns **Wait** — and that is the *low* end, over by 4.0×; the high end is
   over by 15.7×. Stage 1 has **no pre-registered Tier-2 ceilings of its own**.

No diverse-tile run may dispatch on this analysis. This goes to the owner.

---

## Section 1 — PIN 27: the T5 price, as a bracket

### 1.1 The two measured anchors, verbatim from the store

**ANCHOR gate** (`phase14.stage1.anchor_gate`, date 2026-07-26):

| quantity | value |
|---|---|
| `wall_s` | 22,352.058185428963 s (6.209 h) |
| `checks.tiling_identity.own_member_store.solve_wall_s` | 22,063.884031553986 s |
| grid nodes (`checks.era_noop.n_points`) | 2,652 |
| `window_plan.n_windows` | 9 (w = 60 d) |
| `m` | 100 |
| `n_obs` (tile total) | 54,345 |
| preflight `nnz` / `n_coef` | 39,199,621 / 115,200 |
| PCG mean legs (9) | 388, 376, 383, 342, 422, 421, 409, 368, 358 → **Σ 3467** |
| PCG member-batch legs (9) | 443, 445, 432, 396, 459, 458, 443, 398, 399 → **Σ 3873** |
| `peak_rss_mib` | 3512.19140625 |
| preflight `peak_model_mib` | 1650.8 |

Derived: mean 385.2 iters/window, member 430.3 iters/window,
**member:mean iteration ratio = 3873/3467 = 1.1171** (this is the measured
m=1→m=100 iteration penalty — a 100-column block runs until the *worst* column
converges).

The preflight `wall_est_s` is exactly 253.4, which is `BOX_WALL_BASIS_S`; since
`wall_est_s = 253.4 · nnz/nnz_box`, the anchor preflight was evaluated at
`n_obs = 11,041` (the pinned box w0 obs count). So 39,199,621 is a **per-window**
nnz, and 54,345 is the tile total across the record.

**CONVERGED PROBE** (`phase14.stage1.probe_converged`, date 2026-07-25):

| quantity | value |
|---|---|
| `wall_s` | 603.0559034490725 s |
| grid nodes | 9,216 (19°, 0.2°, `solve_bbox` 253–272 E / −32 – −13 N → 96×96 — **verified**) |
| windows / `m` | 1 / 1 |
| PCG | 524 (mean) + 554 (member-batch), both `final_rel_residual` < 1e-6, `maxiter` 2000, `convergence: CONVERGED` |
| `n_obs` (in-window) | 35,802 |
| `model.nnz` / `n_coef` | 127,110,299 / 288,192 |
| `peak_rss_mib` | 3662.1796875 |
| `model.peak_model_mib` / `wall_est_s` | 4652.343578338623 / 821.6852343189747 |
| `measured_vs_model` | wall 0.7339256910815666, peak 0.7871687947878914 |

Two further rows are used as supporting m=1 samples:
`phase14.stage1.probe` (**capped**: 467.9715878770221 s, 500+500) and
`phase14.stage0.probe_tile` (383.5406500339741 s, 461+500, nnz 115,678,112,
n_coef 288,192).

### 1.2 The third input: what the sizing model actually prices

`size_tile` (`src/sverdrup/methods/miost_sizing.py`) returns:

```
wall_est_s = BOX_WALL_BASIS_S * nnz / nnz_box     # 253.4 s basis
```

**There is no `n_windows` factor and no `m_members` factor in `wall_est_s`.**
The parameters are accepted and used only for `retained_member_store_mib` and
`peak_model_mib`. So `wall_est_s` prices **one window at m=1** and nothing else.

Consequences, stated plainly:

- The model cannot price T5 as-is. Naively multiplying by 9 windows gives
  821.685 × 9 = 7,395 s = 2.05 h per tile — which **ignores m=100 entirely**,
  i.e. it omits 99.1% of the work. It is off by roughly two orders of magnitude
  and must not be quoted.
- The recorded `measured_vs_model.wall_ratio` is only like-for-like on the
  1-window/m=1 probes. Applied to the anchor it would read
  22,352/253.4 = 88.2 — which is why the anchor row correctly carries **no**
  `stop_bracket`. Nobody may apply the 1.3× bracket to a T5 row without first
  fixing this.
- What the model *does* give us is a **calibrated nnz-linear ratio at m=1**:
  0.5129 (stage-0 probe_tile), 0.5695 (capped probe), 0.7339 (converged probe).
  The model over-predicts single-window m=1 wall by 1.36 – 1.95×.

So the model's contribution to the T5 price is: a validated statement that
per-window cost scales with nnz, plus a measured m=1 calibration. It contributes
**nothing** about m or windows. Those must come from the anchor.

### 1.3 Normalising both anchors onto one work unit

Per PCG iteration, `apply_a` performs `G @ x` then `Gᵀ @ (...)` — two SpMVs, so
cost per iteration per RHS column ∝ nnz, plus coefficient-shaped vector work
∝ n_coef. Since nnz/n_coef ≈ 340 (anchor) and ≈ 441 (19° tile), the
coefficient-shaped term is under 1% and the nnz term is the whole story.

Define the work unit **U = (iterations × RHS columns) × nnz**.

```
ANCHOR   U = (3467×1 + 3873×100) × 39,199,621
           = 390,767 × 39,199,621 = 1.53178e13
         rate = 22,063.884 / 1.53178e13          = 1.4404e-9 s/U   (m=100)

PROBE (converged, m=1)
         U = 1078 × 1 × 127,110,299 = 1.37025e11
         rate = 603.056 / 1.37025e11             = 4.4011e-9 s/U

PROBE (capped, m=1)
         U = 1000 × 127,110,299 = 1.27110e11
         rate = 467.972 / 1.27110e11             = 3.6816e-9 s/U

STAGE-0 probe_tile (m=1)
         U = 961 × 115,678,112 = 1.11167e11
         rate = 383.541 / 1.11167e11             = 3.4501e-9 s/U
```

Two facts fall out, and they are the two ends of the bracket:

- **m=1 rate spread across three same-host runs: 4.4011/3.4501 = 1.2756×.**
  Same code family, identical `n_coef` = 288,192. This is measurement noise,
  not physics — see §2.
- **Batching bound.** `rate_anchor / rate_probe = 1.4404/4.4011 = 0.3273`, i.e.
  the m=100 batched path costs **at most 1/3.06 per column** of the m=1 path.
  Against the capped probe the bound is 1/2.556. Both estimates are biased
  *optimistic* for batching — the m=1 rate is inflated by per-run fixed
  overhead (assembly, preconditioner, S build, map write, all charged to 1078
  iterations), while the anchor amortises its own fixed overhead across 387,167
  column-iterations. So the true batching benefit is **≤ ~3×, possibly much
  less**.

**This is the single unmeasured quantity that sets the width of the bracket.**
There is no m=100 measurement at 19° geometry anywhere in the evidence store.

### 1.4 The T5 work count

A diverse tile: 96×96 = 9,216 nodes (**verified** against `probe_converged`),
9 windows, m=100, ×4 tiles (equatorial, southern, quiet_gyre, kuroshio).
nnz per window = 127,110,299 (the one measured 19° window; other tiles will
differ with track density — flagged as an unmeasured input).

Mean-leg iterations at 19° geometry, **measured, both converged**:
461 (stage-0 probe_tile, resid 9.9e-7) and 524 (stage-1 converged probe).
Band [461, 524].

Member-leg iterations at m=100: apply the anchor-measured member:mean ratio
1.1171 → [515, 585].

```
per window, iteration-columns = mean×1 + member×100
   LO: 461 + 515×100  =  51,960
   HI: 524 + 585×100  =  59,060
per tile (×9 windows)
   LO: 467,636        HI: 531,542
per tile, work units (× nnz 127,110,299)
   LO: 5.9440e13      HI: 6.7564e13
```

### 1.5 THE BRACKET

| end | rate applied | assumption it rests on | per tile | ×4 tiles |
|---|---|---|---|---|
| **LOW** | 1.4404e-9 (anchor, m=100) | **Linear in nnz + the anchor's measured m=100 batching gain carries unchanged** to a system 3.24× larger in nnz and 2.5× larger in n_coef; **low** measured iteration count (461) holds on all four tiles including kuroshio. | 85,619 s = **23.78 h** | 95.13 h = **3.96 d** |
| **MID** | 3.6816e-9 (capped probe, m=1) | **Batching gain does NOT carry**: each of the 100 columns costs a full m=1 iteration. Physical basis — the 19° RHS block is 288,192 × 100 × 8 B = 220 MiB of dense workspace against the anchor's 115,200 × 100 × 8 B = 88 MiB; on a 4-core N95 with a small shared L3 the anchor's block is far more cache-resident. **High** iteration count (524). | 248,747 s = **69.10 h** | 276.4 h = **11.52 d** |
| **HIGH** | 4.4011e-9 × 1.14 (converged probe, m=1, + pin-28 noise) | As MID, plus the **+14% upward measurement-noise excursion** established in §2 (the wall measurement's own noise floor). | 338,986 s = **94.16 h** | 376.65 h = **15.69 d** |

**THE BRACKET: 23.8 – 94.2 h per tile; 95 – 377 h (4.0 – 15.7 days) for all
four diverse tiles.**

The bracket is 4.0× wide. That width is *not* padding — it is one specific
unmeasured quantity (does the m=100 batching gain survive a 3.24× larger
system?) plus the pin-28 noise floor. For calibration: the plan's anchor
estimate was 40–90 min against 22,352 s actual, a **4.1 – 9.3× miss**. The
present bracket's own width (4.0×) is of the same order as that historical
miss, which is the honest reason not to collapse it to a number.

**The one measurement that would collapse it**: a single window, m=100, at 19°
geometry on quiet_gyre. It costs 1/9 of one tile — 2.6 h (low) to 10.5 h (high)
— and it directly measures the only unknown. **But it fails the same Tier-1 RAM
predicate as T5 itself** (`peak_model` 4659.3 MiB at 1 window/m=100 → needs
MemAvailable ≥ 9319 MiB; live is 5261 MiB). So even the bracket-collapsing
measurement WAITS. That is a decision for the owner walk.

### 1.6 Wall against the ladder

Read of `src/sverdrup/application/ladder.py`:

- `TIER1_HEADROOM_FRACTION = 0.5`; `tier1_eligible(peak)` returns
  `peak <= 0.5 × MemAvailable`, read from `/proc/meminfo` **at call time**.
- `STAGE0_SPEND_TABLE` has three rows. Only `tier2_probe`
  (`Tier.CLOUD_NODE`) carries resource ceilings: `max_vcpu=8`,
  `max_ram_gib=64.0`, `max_wall_h=6.0`, `cost_ceiling_usd=25.0`.
  `stage0_default` (`Tier.BOX_PRODUCTION`) has `max_wall_h = 0.0`, and
  `_over_ceilings` guards with `if row.max_wall_h and ...` — so an unset
  ceiling is **never** checked.

Evaluated:

```
authorize("tier2_probe",    25.0, 8, 64.0, 23.78) -> Wait  (wall 23.78 > 6.0 h)
authorize("tier2_probe",    25.0, 8, 64.0, 94.16) -> Wait  (wall 94.16 > 6.0 h)
authorize("stage0_default",  0.0, 8, 64.0, 94.16) -> Authorization  (AUTHORIZED)
```

**Verdict: CROSSES TIER-2 → WAIT.** Every end of the bracket, at per-tile
granularity, exceeds the only pre-registered Tier-2 wall ceiling in the
project — by 4.0× at the low end and 15.7× at the high end. Stage 1 has no
pre-registered Tier-2 ceilings, so there is no row that could cover it.

**Gap to surface, separately.** `stage0_default` returns AUTHORIZED for a
15.7-day box run, because its wall column is simply unpopulated. *The absence
of a ceiling is not authorization.* A 4–16 day exclusive hold on the box is a
real cost decision; the table has no way to express it. Recommend the owner
register a `stage1_tile_solve` row with an explicit `max_wall_h` before any
diverse-tile dispatch.

### 1.7 RAM — the binding constraint

`size_tile(19° geometry, n_grid_nodes=9216, n_windows=9, m_members=100,
n_obs=35802, window_days=60)`:

```
nnz                        127,110,299
stored_g_gib                     1.421
retained_member_store_mib       63.281      (= 9216 × 9 × 100 × 8 B)
peak_model_mib                4715.555
```

**The model's peak is m-insensitive by construction.** 4715.6 equals the
recorded m=1 model peak (4652.3) plus exactly the retained-store delta
(63.28 − 0.07 = 63.2 MiB). Reading `peak_model`'s phase-max: the *assembly*
phase (`triplets` 24 B/nnz = 2909 MiB + `csr_g` 12 B/nnz = 1455 MiB +
baseline 286 MiB + retained) dominates, and neither triplets nor CSR depend on
m. Going from m=1 to m=100 moves the model by **1.4%**. That is the defect.

**Reality, from the only m=100 measurement in existence:**

| | model | measured | ratio |
|---|---|---|---|
| anchor, m=100 | 1650.8 MiB | 3512.2 MiB | **2.128** (model 2.13× LOW) |
| converged probe, m=1 | 4652.3 MiB | 3662.2 MiB | 0.787 (model over-predicts) |

Honest caveat: `peak_model` prices ONE window solve, while `peak_rss_mib` is
the whole-run maximum including the merge/compare phase — the phase that OOM'd
and was fixed in commit `efd515a`. So part of the 2.128 is scope, not error.
But `peak_rss_mib` is precisely the number the Tier-1 predicate must survive in
practice, so it is the right number to carry forward.

**T5 expected actual peak (bracket, transferring the anchor's m=100 miss):**

```
additive     : 4715.6 + (3512.2 - 1650.8) = 4715.6 + 1861.4 =  6577 MiB
multiplicative: 4715.6 × 2.128                              = 10,033 MiB
```

→ **6.6 – 10.0 GiB.**

**Against the Tier-1 predicate** (`peak <= 0.5 × MemAvailable`):

| fed to the predicate | MemAvailable required | status |
|---|---|---|
| model 4715.6 MiB (what the code actually checks) | ≥ 9,431 MiB | live MemAvailable **5261 MiB** → `tier1_eligible` = **False** |
| honest actual 6,577 MiB | ≥ 13,154 MiB | never observed on this box |
| honest actual 10,033 MiB | ≥ 20,066 MiB | never observed on this box |

MemAvailable observed on this box during the anchor run: **8,590 – 11,900 MiB**
(`logs/stage1_anchor_gate.log` heartbeats). Even at the best value ever
recorded (11,900 → budget 5,950 MiB), T5 clears the *model* number by only
1.26× and fails the *honest* number by 1.1 – 1.7×.

**RAM is the binding constraint, and it fails.** T5 at 19°/m=100 is not
Tier-1 launchable on this box. It fails before the wall bracket ever matters.

---

## Section 2 — PIN 28: reconciling the 20%

### 2.1 The discrepancy, and a bound that sharpens it

```
wall        603.0559 / 467.9716 = 1.28866
iterations       1078 / 1000    = 1.07800
residual      1.28866 / 1.07800 = 1.19542   ->  19.54% unexplained
```

A sharper statement. Under **any** model `wall = F + c·N` with fixed overhead
F ≥ 0 and the *same* per-iteration cost c in both runs, the capped run bounds
`c ≤ 467.972/1000 = 0.46797 s/iter`. The 78 extra iterations can therefore buy
**at most 78 × 0.46797 = 36.50 s**. The observed increment is **135.08 s**.

So **≥ 98.58 s — 21.1% of the capped wall — cannot be iteration count under any
nonnegative fixed overhead.** Solving the two equations exactly gives
`c = 135.084/78 = 1.7318 s/iter` and `F = 467.972 − 1731.8 = −1263.8 s`. A
**negative fixed cost** is the formal statement that the two runs are
inconsistent with a single throughput. The rate changed between runs.

### 2.2 The four candidates — all falsified

**(1) Host contention: was the anchor solve running concurrently?
FALSIFIED — they did not overlap, and the anchor did not yet exist.**

```
probe_converged_maxiter2000.log
  [run] 2026-07-25T23:48:44Z launching: ... probe --maxiter 2000
  [run] 2026-07-25T23:59:14Z probe exited rc=0
logs/stage1_anchor_gate.log
  [orch] 2026-07-26T00:02:19Z start; ... MemAvailable=11900 MiB >= 6900 — launching
```

The anchor's first launch is **3 min 5 s after the probe exited**. Zero overlap.
Moreover the anchor-gate machinery commit `f201c09` is dated
2026-07-25 17:01 −0700 = **2026-07-26T00:01Z** — one minute before that launch
and *after* the probe had finished; the anchor did not exist as runnable code
during the converged probe. `rg 'SIGSTOP|SIGCONT|sigstop'` over the whole tree
returns nothing — no SIGSTOP coordination exists in this repo.

What the log *does* show is a **different, unnamed co-tenant**: the RAM gate
polled MemAvailable at 7296 → 7228 → 9716 → 9725 → 10,958 MiB over the eight
minutes before launch. Several GiB were held and released by something else on
the box immediately before the run. The gate waits on a RAM threshold only; it
never waits for CPU quiescence.

**(2) The `maxiter=2000` allocation. FALSIFIED — the solver allocates nothing
per maxiter.**

`src/sverdrup/methods/miost_solver.py:150` — `for it in range(start_it,
self.pcg_maxiter + 1)`. Every state array (`x`, `r`, `p`, `rz`, `iters`) is
sized from `b2`; none from `pcg_maxiter`. No residual history is retained.
Direct confirmation from the measurement itself:

```
peak_rss_mib  maxiter 500  : 3662.140625
peak_rss_mib  maxiter 2000 : 3662.1796875
difference                 : 0.039 MiB (40 KiB)
```

**(3) The separate output path. FALSIFIED — same artifact, same cost.**

```
probe_quiet_gyre_mean.npz            75,868 B
probe_quiet_gyre_mean_maxiter2000.npz 76,028 B
```

160 bytes apart, one write each. Contributes nothing to 135 s.

**(4) Checkpoint cadence. FALSIFIED by call site and by chronology.**

`_probe_solve` never passes `checkpoint=` — checkpointing is the anchor-gate
path only. And the crash-durable PCG checkpoint feature (commit `b71dc7f`,
2026-07-25 18:04 −0700 = **2026-07-26T01:04Z**) landed **after** the converged
probe finished at 23:59:14Z. The code did not exist when the run happened.

### 2.3 The one measurement — and why this one

A repeat of the converged probe would have produced a fourth sample of the same
aggregate. It **does not discriminate** between the candidates above, because
all four are already falsified by direct evidence (timestamps, source, peak RSS,
file sizes). What was genuinely unknown is whether this host's throughput is
even *stationary* — and no probe re-run answers that, because a single aggregate
wall cannot separate "this configuration is slower" from "this box drifts".

So the measurement run was: a **fixed-work repeated SpMV** — a 5.0e6-nnz
G-shaped CSR, `G @ x` then `Gᵀ @ y` (exactly the two SpMVs `apply_a` performs),
300 s, throughput reported per 20-second bucket. Host: **Intel N95, 4 cores,
15 W class**.

```
t_s  iters  s_per_iter_per_nnz          t_s  iters  s_per_iter_per_nnz
  20   765  2.6164e-09                  180   602  3.3247e-09
  40   778  2.5698e-09                  200   575  3.4773e-09
  60   749  2.6703e-09                  220   682  2.9392e-09
  80   774  2.5834e-09                  240   530  3.7673e-09
 100   722  2.7711e-09                  260   695  2.8777e-09
 120   739  2.7064e-09                  280   656  3.0492e-09
 140   657  3.0435e-09                  300   449  4.4558e-09
 160   632  3.1636e-09

first bucket 2.6164e-09  last bucket 4.4558e-09  slowdown 1.7030x
min 2.5698e-09  max 4.4558e-09  max/min 1.7339
mean 3.0677e-09  CV 0.1693
cumulative-average over first 78% of run vs full run: ratio 1.0590
```

### 2.4 The named cause

**Non-stationary host throughput.** Not "unexplained" — measured, with two
separable components:

**(a) A deterministic duration ramp — worth +5.9% at exactly this duration
ratio.** Identical work costs **1.70× more per unit at t = 300 s than at
t = 20 s** on this box (Intel N95, 15 W class: a sustained numeric load leaves
boost and settles into a thermally/power-limited steady state). The converged
run is 28.9% longer than the capped run, so it spends a larger fraction of
itself in the ramped-down state. Measured directly: the cumulative-average rate
over the first 78% of a run versus the full run is **1.0590**. This component
is reproducible and predicts the correct *sign* — longer runs are always
slower on average.

**(b) Uncontrolled run-to-run variance — the remainder, ≈12.9%.**
`1.19542 / 1.0590 = 1.1288`. This sits comfortably inside two independent
measurements of the same thing: the benchmark's **16.9% bucket-to-bucket CV**,
and the **1.276× spread in s/(iter·col·nnz) across the three m=1 solve runs
already in the evidence store** (3.4501e-9 stage-0 probe_tile, 3.6816e-9
capped, 4.4011e-9 converged) — three runs of the same code family, identical
`n_coef` = 288,192, same host.

**Nothing in the converged configuration is intrinsically slower.** The honest
one-liner: *the wall measurement on this host carries a ~±15% noise floor with
a systematic longer-is-slower ramp on top; 20% is inside it.*

### 2.5 Consequence for the 1.3× bracket

`PROBE_STOP_THRESHOLD = 1.3` (`scripts/phase14_stage1_run.py:58`); the bracket
trips when `wall_ratio > 1.3 or peak_ratio > 1.3`. Its entire discriminating
margin is the **0.30 excess over unity**.

- Measured noise on the wall leg is **±15%** (16.9% CV), with a **1.276×** full
  spread observed across three same-host runs.
- Near the trip point, a ±15% excursion is **±0.195 in ratio units against a
  0.30 margin — 65% of the margin**. A genuine 1.3× model miss lands anywhere
  in roughly [1.13, 1.50] on a single measurement; a genuine 1.13× miss can
  trip. The gate cannot separate the two.
- The observed full spread (1.276×) is **98% of the threshold (1.30×)**.

**Stated plainly: the 1.3× STOP bracket sits inside its own noise floor on the
wall leg. Pin 24's discipline applies to precision exactly as the owner said —
a gate whose noise reaches its threshold is not a gate.**

One honest mitigation of the alarm: the bracket has never *false-tripped*,
because the readings sit at 0.513 / 0.570 / 0.734 — 1.77× below the trip point
at the highest. That is luck of the operating point (the model over-predicts
m=1 wall), not gate design. The moment a leg reads near 1.0 the gate is
noise-limited — and the anchor's m=100 RAM leg already reads **2.128**.

**Asymmetry worth recording: only the wall leg is noise-limited.** Peak RSS is
nearly noise-free on this path — 3662.140625 vs 3662.1796875 MiB across two
runs, **0.001% apart**. The bracket's peak leg is a real gate and should be
kept at 1.3.

### 2.6 What replaces the wall leg

1. **Move the discriminator off wall onto deterministic work.** The
   reproducible content of a solve is `U = Σ_legs (iterations × columns) × nnz`.
   Iteration counts are bit-reproducible — the solver documents checkpoint
   resume as yielding a bit-identical iterate sequence
   (`miost_solver.py:101-107`) — and nnz is a deterministic function of n_obs.
   Gating measured-U against model-implied-U has **zero host noise**, and it is
   the quantity that actually tells you whether the cost model is wrong.
2. **Record wall as a bracket, never a point.** Stamp every recorded wall
   ×[0.87, 1.15] measurement uncertainty, in-row, so no downstream reader
   mistakes it for a repeatable number.
3. **If a wall STOP must remain, widen it or repeat it.** Either raise the
   threshold to **≥ 1.7×** (the measured single-run rate drift, so noise cannot
   reach it), or require the **minimum of 3 independent repeats** to exceed 1.3
   — the minimum is the throttle-robust statistic, since it samples the
   least-degraded run.
4. **Add a host-rate calibration row.** Run the 300 s fixed-work SpMV
   immediately before each timed leg and record its rate alongside; wall can
   then be normalised by measured host throughput and the residual becomes a
   real signal. Cost: 5 minutes against runs of hours.
5. **Fix the ratio's denominator before any T5 row uses it.** `wall_est_s` is
   per-window and m=1 (§1.2); comparing a 9-window m=100 wall against it is
   meaningless (the anchor's would read 88.2). Either extend the model with
   `n_windows` and an m-batching factor, or restrict the bracket to 1-window
   m=1 rows by construction.

### 2.7 Coupling back to PIN 27

The pin-28 noise floor is why the pin-27 HIGH end carries an explicit ×1.14
term, and why no single confident T5 number is defensible even after the
batching question (§1.3) is settled by measurement. A ±15% wall noise floor
means the T5 price will remain a bracket of at least ×1.3 width no matter how
much is measured — the residual uncertainty must be reported, not averaged away.
