# Phase-14 Stage-1 T8 — the OSSE run decision (v3) — ⛔ **WITHDRAWN AS A PRICING DELIVERABLE**

> # ⛔⛔ THIS DOCUMENT IS WITHDRAWN. **DO NOT PRICE AN OSSE FROM IT.**
>
> **Owner pins 250–252, 2026-09-20. T8 IS A RULED WAIT.**
>
> **v3 was OVERTURNED**, like v1 and v2 before it, by two-reviewer adversarial
> review under pin 212(b) — all three on the **unit of account**. v3's §3, the
> only section that produced a verdict, still applied an **observation-fitted
> exponent to mission counts**: v2's exact defect, in the one place a number
> changed a decision. Its breach count runs **0 to 5 across this document's own
> band**, driven by **model**, not by tile as §3 claims.
>
> ⭐ **AND VALIDITY IS PRIOR TO PRICE (pin 250).** The experiment may not answer
> its own value case: **no replication**; a truth field (**GLORYS12**) that
> **assimilates the constellations under test**; and an epoch-span question that
> preserves "**FIXED** truth" under **neither** reading.
>
> ⛔ **EVERY HOUR FIGURE BELOW IS WITHDRAWN** — the 295–470 h band, the per-class
> walls, the WAIT verdicts, all of it. They are left in place only so the WAIT
> carries its reasoning.
>
> ✅ **THE RULED RECORD IS `phase14.stage1.osse_pricing`** (witnessed), which
> carries the WAIT, the three overturns, pin 251's exit and the facts that
> survived. **Read that, not this.**
>
> **THE EXIT (pin 251):** the truth must be a **free-running NATURE RUN**
> (LLC4320-class), not a reanalysis. LLC4320's ~14-month span forces the
> common-span design, and whether flying each era's orbit geometry over one
> fixed nature-run period preserves "constellation varied over fixed truth" is
> the **OPEN DESIGN QUESTION, owned by Stage 2**. Replication is **required and
> unpriced**.
>
> ⚠ The pin-237 truth measurement below is **sound arithmetic about the wrong
> object**: it sized GLORYS12, which pin 251 rules out.

---

## [WITHDRAWN — preserved as the record of why] The v3 document as posted


**Posted 2026-09-20. Owner pins 232 / 234 / 235 / 236 / 237 / 244–249.**
**Evidence node:** `phase14.stage1.osse_pricing` (mirrored and witnessed).
**Producer:** `scripts/phase14_osse_pricing.py` — every figure recomputes.

> ## ⬛ DECISION CELL — **EMPTY**
>
> **PRICED, OWNER TO DECIDE. This is NOT "not priced."**
>
> Every figure below is a measurement, a **declared diagnostic**, or an
> **explicit refusal to estimate**. What is absent is the owner's election.
>
> ⛔ The posted Gate-1 pack's OSSE slot still reads *"T8 is unopened."* That is
> out of date and this supersedes it; the pack is **NOT retro-edited** (209c).

> ## ⛔ v1 AND v2 WERE BOTH OVERTURNED. v3 IS **SIMPLER THAN v1**.
>
> Two rounds of two-reviewer review, both overturning on the **unit of
> account** — v1 priced *one class = one tile solve*; v2 fitted on
> **observations** and applied on **missions**.
>
> ⭐ **The decisive point (pin 245): every defensible model puts the sweep in
> 295–470 h, and that band was always sufficient for a go/no-go.** Two rounds
> were spent moving the *smallest* term in the price. So the headline is the
> **band across models, with no exponent in it**. The fit is a **diagnostic**.

---

## 1 — The headline: a BAND, not a number

| model | leg-equivalents | at kuroshio | at southern |
|---|---|---|---|
| flat — one class = one leg (v1) | 15.00 | 295.0 h | 412.2 h |
| linear in missions | 15.80 | 310.8 h | 434.2 h |
| 5-point refit (legs + `anchor_gate`) | 16.33 | 321.3 h | 448.9 h |
| raw wall-vs-n_obs fit *(diagnostic)* | 16.71 | 328.7 h | 459.2 h |
| upper 95% CI on the 4-leg fit | 17.12 | 336.7 h | 470.4 h |

### ⭐ **FULL SWEEP: 295 – 470 h under every defensible model.**

The models disagree by less than the **tile** axis does (1.40×). No exponent
appears in this headline.

## 2 — ⛔ FOUR OPEN INPUTS. None is defaulted.

| axis | spread | status |
|---|---|---|
| which **tile** | 1.40× (19.67 → 27.48 h) | ⛔ NOT A DEFAULT |
| **constellation size** | ~4.7× (3–9 missions vs the legs' 5) | ⛔ NOT A DEFAULT |
| **platform convention** | ~1.28× | ⛔ NOT A DEFAULT — *newly disclosed* |
| **RAM** | **UNMODELLED** | ⛔ NOT A DEFAULT — an explicit refusal |

**The platform convention was never disclosed by v1 or v2.** `j2g` and `j2n`
are **time-disjoint orbit phases of one Jason-2**, so the legs ran **four
platforms under five labels**. The same over-count sits in epochs 0 (`e1`+`e1g`),
8 (`al`+`alg`), 9 (`j2`+`j2n`) and 14 (`j3g`+`j3n`). Which convention a price
uses moves it ~1.28× — larger than the correction v2 was built to make.

## 3 — ⛔ PER-CLASS WALLS AGAINST THE 40 h CEILING — the fact v2 omitted

v2 reported **only sums**. Pin 99(b)'s ceiling is a **per-leg** rule, and a
breach is a **WAIT**, not a line in a total. `TIER_CEILING_H = 40.0` sat in the
v2 producer **unreferenced** — pin 99(b)'s own rule as dead code, while the
same constant is used correctly one task over in the revisit rows.

| missions | classes | at kuroshio | at southern | verdict (southern) |
|---|---|---|---|---|
| 3 | 2 | 9.5 h | 13.3 h | RUN |
| 4 | 6 | 14.3 h | 20.0 h | RUN |
| 5 | 1 | 19.7 h | 27.5 h | RUN |
| 6 | 1 | 25.5 h | 35.6 h | RUN |
| 7 | 3 | 31.7 h | **44.2 h** | **WAIT** |
| 8 | 1 | 38.2 h | **53.4 h** | **WAIT** |
| 9 | 1 | **45.2 h** | **63.1 h** | **WAIT** |

**Between 1 and 5 of the 15 classes breach the 40 h per-leg ceiling**,
depending on the tile. ⚠ These per-class figures use the **diagnostic**
exponent — the ceiling question needs *some* per-class number — and inherit
every caveat in §4. They are not measurements.

## 4 — The wall diagnostic, and why it is not the pricing basis

| tile | n_obs | Σ PCG iters | wall | µs per obs-iteration |
|---|---|---|---|---|
| kuroshio | 138,518 | 8,075 | 19.67 h | 63.3 |
| equatorial | 167,579 | 9,178 | 25.54 h | 59.8 |
| quiet_gyre | 168,755 | 9,592 | 26.03 h | 57.9 |
| southern | 175,059 | 9,452 | 27.48 h | 59.8 |

**The per-iteration cost is constant to ±4.5%.** So the wall is essentially
**linear in (observations × iterations)** — and roughly **60% of the apparent
superlinearity** in a raw wall-vs-n_obs fit is the **iteration term wearing an
observation exponent**. ⚠ The iteration term runs **opposite** to the
observation term for sparse constellations, which are worse-conditioned.

### ⛔ The "controlled experiment" premise is STRUCK (pin 245f)

v2 called these four legs a controlled experiment *"in which n_obs is the only
varying input"*. With **n = 4 and one point per tile, observation count is
perfectly collinear with tile identity** — the regression measures **which
tile**, not how many observations. **There is no measurement in this repository
where n_obs varies at a fixed domain**, which is the only contrast an OSSE
produces.

⚠ **A domain confound is plausible and UNQUANTIFIED.** `n_coef` varies with
latitude through `miost_sizing.n_coefficients`. Only kuroshio's is recorded
anywhere (297,600); the other three are **SEARCHED AND ABSENT** from the store
and the logs. A reviewer reported per-tile values; they could not be
reproduced, so they are **not restated here** (pin 247).

⚠ **`anchor_gate` is a measured m=100, 9-window, CONVERGED solve at 54,345
observations — below the legs.** v2's declaration claimed the small classes sat
"below anything measured"; that was **false**. Including it drops the exponent
to **1.2627**. Excluding it is defensible (smaller domain, `dc2021a` source) —
but *the reason for excluding it is the same confound that disqualifies the
four-leg fit as a clean observation contrast.* It cannot be had both ways,
which is why the fit is a diagnostic only.

## 5 — ⛔ RAM: a NAMED axis carrying an explicit refusal

v2 gave RAM one clause in a list. It is the axis that has actually stopped work
here:

- The **equatorial leg was REFUSED** by the launch gate at 9,891.58 MiB against
  a 9,902.33 MiB gate — **a margin of 11 MiB** — and relaunched at 9,907.33,
  clearing by 5.
- **Leg 2 bottomed at 1,382 MiB mid-run with swap exhausted** and survived by
  owner intervention, which is not a property the remaining legs can rely on.

**RAM IS UNMODELLED at any constellation size but the legs' five, by
declaration.** The one recorded RAM projection in this project **missed by
1.69× while its wall projection was 0.63×** — the asymmetry pin 139(a)
predicted. Estimating here would repeat it.

**What would settle it:** predicted peak RSS at 9 missions against the
9,902.33 MiB gate. A go/no-go, not a magnitude.

## 6 — Scope subsets: limits only. **NO ORDERING.**

| subset | classes | total missions | CANNOT establish |
|---|---|---|---|
| full sweep | 15 | 79 | — |
| `fit+validate` | 10 | 61 | transfer into the 5 validate-only epochs, where transfer is actually claimed |
| pre-lift (`mask_66`) | 9 | 35 | anything about the 6 modern post-lift constellations |
| post-lift | 6 | 44 | era-transfer across the 1992–2009 boundary — the era gap the claim is weakest at |
| validate-only | 5 | 18 | anything fitted; it tests only the transferred epochs |

**No hours column, and no ordering.** That is deliberate.

### ⛔ v2's DIRECTION CLAIM IS WITHDRAWN AND NOT RE-DERIVED (pin 244)

> ~~*"Post-lift is dearer than pre-lift, and this holds under **any** cost
> monotone in observation count."*~~

**It is false.** Cost is `Σ f(mᵢ)`. Post-lift has **fewer and larger** classes
(6 / 44) than pre-lift (9 / 35), so the ordering requires **f CONVEX**, not
merely monotone — and it **reverses below p ≈ 0.638**. At p = 0.5, pre-lift
costs 17.70 and post-lift 16.22 leg-equivalents.

⭐ **The arithmetic error beneath it, and the finding that matters more.** The
ratios that ratified the claim were `(Σm_post / Σm_pre)^p` — the exponent
applied to the **aggregate**. But `Σ(mᵢ^p) ≠ (Σmᵢ)^p` unless **p = 1**.
**p = 1 is the only point where the two formulas coincide, and that lone
agreeing figure was read as verification.** *That is the finding, not the
slip* (pin 244c).

⛔ **No ordering is re-derived.** Convexity needs the conditioning term, which
needs a measurement that does not exist. This is pin 239(c)'s own discipline —
*do not replace a withdrawn claim with its opposite* — applied here to the
owner's claim as it was applied to the executor's.

**What would settle it:** one solve, one tile, one window, at a 3-mission
subset of `PROBE_MISSIONS`, recording n_obs and PCG iterations. Roughly 1–2 h.

## 7 — The truth field

Metadata-only STAC query (pin 237a), HTTP 200, `stac.marine.copernicus.eu` ·
`GLOBAL_MULTIYEAR_PHY_001_030` (GLORYS12V1), **2026-09-20T06:58:29Z**.

| quantity | value |
|---|---|
| `zos` itemSize / grid | 2 bytes · 2041 × 4320 @ 0.0833° |
| tile bbox 19°, **node-inclusive** | **229** × 229 |
| window-plan span | **400 days** |
| **per tile** | **40.01 MiB** |
| **all four tiles** | **160.04 MiB** |
| global `zos`, full record | 0.20 TiB |

⭐ **Bought ONCE PER TILE, not once per class** — an OSSE varies the
constellation over fixed truth. ⚠ **It does scale with tiles.**

**FEASIBLE** (derived): 160.04 MiB against the 50 GiB `cmems_downloads` budget
(`ladder.STAGE0_SPEND_TABLE`, `Tier.BOX_PRODUCTION`) — 0.31%.

⚠ **Declared limits:** it is the **solve** box (the obs footprint adds the 1.0°
halo, 1.22× larger); it is the **uncompressed** array, so a **bound** on wire
volume, not a wire measurement; and it is **`zos` only**.

⚠ The window plan is **overlapping and non-uniform** — 9 × 60 d on strides of
{25, 45} d; 540 window-days over a 400-day union. *(v2 said "a 45-d stride";
a uniform 45 would span 420 days, contradicting its own 400.)*

⚠ **OPEN — which epoch-span reading the design takes.** The 15 classes are
date-ranged (1992–2026) while this volume assumes **one common 400-day span**.
Common-span means historical ground tracks must be **synthesised** (uncosted
engineering); per-era means **15× the download** (2.34 GiB for four tiles,
still feasible) **and the truth is no longer "FIXED"**, which is the value
case's own word.

## 8 — The value case, verbatim

> *constellation varied over FIXED model truth is the only ground-truth test of
> the era-transfer claim (fork-e level 1 validates against fitted s; OSSE
> against truth)*

The assertion is **not** that nothing else tests era-transfer — it is that
fork-e level 1 validates against a **fitted s** and an OSSE against **truth**.
The spec continues *"— the Stage-1 run decision must price that benefit, not
just seam/kernel checks"*, which is the mandate this document discharges.

## 9 — ⛔ LOWER BOUND, and what carries no number at all

**Covered:** the re-solves and the truth download, at declared assumptions.

**NOT costed:**

1. **Truth-provider wiring** — `TRUTH` is **DORMANT since 4b**. Called the
   largest open item, and it **carries no number at all**, while a 160 MiB
   download is priced to four figures.
2. Per-class observation simulation.
3. Scoring and analysis of 15 outputs.
4. **REPLICATION.** 15 classes × 1 tile × 1 truth realisation cannot separate
   *"this constellation is worse"* from *"these track positions over this tile
   were unlucky"*. §7's once-per-tile truth forecloses repeats by construction.
5. Non-convergence retries — the legs ran **375–626** PCG iterations per window
   at 5 missions.
6. Calendar time and box occupancy — serial single-host hours.
7. **Truth-field independence.** GLORYS12V1 is a **data-assimilative reanalysis
   that ingests along-track SLA from the very constellations being simulated** —
   the fraternal-twin problem, first-order for an OSSE whose whole value case is
   "against truth". §7's limits are all about volume; none is about validity.

## 10 — Recommendation: both options, neither elected

| option | cost | CAN establish | CANNOT establish |
|---|---|---|---|
| **run at Stage-2 entry** | same compute | the era-transfer claim against truth where it becomes load-bearing | anything for Gate 1 |
| **run now** | 295–470 h across all models, + 160.04 MiB truth | the same thing, earlier | any Gate-1 item; Gate 1 already carries two ruled WAITs |

> ## ⬛ DECISION CELL — **EMPTY.** The OSSE run decision is the owner's.

## 11 — Basis, stated in-row (pin 99c)

| figure | source | status |
|---|---|---|
| leg walls, n_obs, PCG iterations | `phase14.stage1.tiles.<tile>` | MEASURED, 9/9 CONVERGED |
| N_epoch-classes, mission counts | sealed `content.epoch_table` | DERIVED from sealed evidence |
| model band 295–470 h | the five models above | DERIVED; no single exponent |
| wall-vs-n_obs exponent | fitted from four legs | **DIAGNOSTIC** — declared at `projection_declarations`, collinear with tile identity |
| per-class walls / ceiling verdicts | diagnostic exponent × measured legs | PROJECTED; inherits §4's caveats |
| RAM at other constellation sizes | — | **UNMODELLED by declaration** |
| per-tile `n_coef` (3 of 4) | — | **SEARCHED AND ABSENT** |
| truth volume | STAC query 2026-09-20T06:58:29Z | DERIVED; a bound on wire volume |
| capped T2 probe | — | **NEVER USED** (99c / pin 23a) |
