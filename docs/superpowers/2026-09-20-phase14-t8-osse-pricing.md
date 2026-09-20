# Phase-14 Stage-1 T8 — the OSSE run decision, PRICED (v2)

**Posted 2026-09-20. Owner pins 232 / 234 / 235 / 236 / 237 / 239.**
**Evidence node:** `phase14.stage1.osse_pricing` (mirrored and witnessed).
**Producer:** `scripts/phase14_osse_pricing.py` — every figure recomputes.

> ## ⬛ DECISION CELL — **EMPTY**
>
> **PRICED, OWNER TO DECIDE. This is NOT "not priced."**
>
> Every figure below is a measurement, or a **declared projection** from one.
> What is absent is the owner's election, **and only that**.
>
> ⛔ The posted Gate-1 pack's OSSE slot reads *"T8 is unopened; presented as
> such."* **That is out of date and this document supersedes it** — the pack is
> **NOT retro-edited** (pin 209c); a successor pack cites this.

> ## ⛔ v1 WAS OVERTURNED. THIS IS THE REBUILD (owner pin 239).
>
> A two-reviewer adversarial review under pin 212(b) **overturned the first
> version.** The defect was not an arithmetic slip — every number in v1
> recomputed exactly. **The defect was the UNIT OF ACCOUNT.**
>
> v1 priced **one class = one tile solve**, treating solve wall as independent
> of observation count. It is not, and an OSSE varies exactly that. The error
> **inverted the subset price ordering** an owner would choose a scope from.
>
> ⚖ **Reviewer A confirmed all five of the owner's authored attack surfaces.
> Reviewer B, briefed to attack the FRAME rather than the list, found this.**
> That split is recorded as §7 discipline 17.

---

## 1 — The value case, verbatim

Fork-f pin 5 (`specs/2026-07-21-phase14-scaling-program-design.md` §5), quoted
exactly:

> *constellation varied over FIXED model truth is the only ground-truth test of
> the era-transfer claim (fork-e level 1 validates against fitted s; OSSE
> against truth)*

The parenthetical is part of the claim. The assertion is **not** that nothing
else tests era-transfer — it is that fork-e level 1 validates against a
**fitted s** and an OSSE validates against **truth**. The spec's sentence
continues *"— the Stage-1 run decision must price that benefit, not just
seam/kernel checks"*; that clause is the mandate this document discharges.

## 2 — How many runs: N_epoch-classes = **15**, DERIVED

From the **sealed** epoch table (`phase14_evaluation_seal_v1.json` →
`content.epoch_table`), derived in the producer, never typed.

| quantity | value |
|---|---|
| epochs | **15** |
| **distinct mission sets (= classes)** | **15** |
| distinct after removing locked `c2`/`c2n` | **15** |
| deduplication available | **NO** |

⛔ **NO DEDUPLICATION EXISTS** (pin 234b). Every constellation is unique, before
*and* after removing the locked instruments — the reduction a reader would most
plausibly try. **The price has no cheap reduction available.**

## 3 — ⛔ TWO OPEN INPUTS, NOT ONE. The larger one is the constellation.

**v1 declared the smaller axis open while collapsing the bigger one** (pin
239d). Both are open:

| axis | spread | status |
|---|---|---|
| which **tile** | **1.40×** (19.67 → 27.48 h) | ⛔ OPEN INPUT, not a default |
| which **constellation** | **~4.7×** (3 → 9 missions vs the legs' 5) | ⛔ **OPEN INPUT, not a default — and it is the larger** |

Class mission counts, from the sealed table:
`[3, 3, 4, 4, 4, 4, 4, 4, 5, 7, 6, 7, 7, 8, 9]`. The four legs all ran the
**same 5-mission** constellation (`PROBE_MISSIONS`), so the legs hold
constellation fixed and vary tile — the opposite of what an OSSE does.

## 4 — Why "one class = one tile solve" is wrong

The four legs are the cleanest controlled experiment this project has:
**identical** 19°×19° solve bbox, **identical** `m=100`, **identical** 9×60 d
window plan, **identical** 5-mission constellation. The only varying input is
observation count.

| tile | n_obs | measured wall |
|---|---|---|
| kuroshio | 138,518 | 19.67 h |
| equatorial | 167,579 | 25.54 h |
| quiet_gyre | 168,755 | 26.03 h |
| southern | 175,059 | 27.48 h |

**wall ∝ n_obs^1.4146, R² = 0.9989.**

⚖ **Independently corroborated, and already on the record:**
`tier2_probe_kuroshio_m100.derived_pin_89d.wall.implied_exponent = 1.28`, whose
own verdict reads *"NOT linear. The linear point … was optimistic by 1.42×."*
**v1's flat model was flatter than LINEAR — a model this project's own pinned
evidence had already rejected once.**

### ⚖ The fit is a PROJECTION and is declared as one (pin 139)

`measured_over`: 4 legs, **5 missions**, n_obs 138,518–175,059 ·
`application_range`: **3–9 missions** · `within_measured_span`: **false** —
the 3- and 4-mission classes sit **below** anything measured.

⛔ **It may be used for MAGNITUDES ONLY.** One point estimate is not swapped
for another (pin 239b).

## 5 — The price

| tile | measured leg | flat model ×15 | **obs-scaled (projected)** |
|---|---|---|---|
| kuroshio | 19.67 h | 295.0 h | **328.7 h** |
| equatorial | 25.54 h | 383.1 h | 426.8 h |
| quiet_gyre | 26.03 h | 390.5 h | 435.0 h |
| southern | 27.48 h | 412.2 h | **459.2 h** |

**Full sweep: 295.0 – 412.2 h flat; 328.7 – 459.2 h obs-scaled (projected).**
The measured leg spread is **19.67 – 27.48 h**.

The range is stated at both ends with each tile named, because *"a tile solve"
is not one number* and a single figure hides a 1.40× spread that is a property
of the tiles, not of the OSSE (pin 236c).

## 6 — Pin 89's probe: a CROSS-CHECK, and a record of how a projection performed

All figures **derived** from `tier2_probe_kuroshio_m100.derived_pin_89d.wall`
(v1 typed them while citing the node — a provenance claim nothing enforced).

| | value |
|---|---|
| probe, kuroshio m=100 | 3.4399 h/window, CONVERGED (441/486 vs a 500 cap) |
| projected ×9 | **30.96 h** |
| **measured, same tile** | **19.67 h** |
| **over-prediction** | **1.574×** |
| four-tile projected / measured | 123.84 h / 98.72 h → **1.254×** |

⚖ **The measurement supersedes the projection** (236a). Both CONVERGED, both
admissible under 99(c) — but one is a one-window projection and the other is
the thing it was projecting. **Its value now is as a record of how a one-window
projection performed** (236b). It is not a price.

⛔ **THE CAPPED T2 PROBE IS USED NOWHERE** (99c / pin 23a).

## 7 — The truth field: MEASURED, and it scales with TILES, not classes

Pin 237(a) authorised a **metadata-only** STAC query — no download, one host,
read-only. HTTP 200.

- `stac.marine.copernicus.eu` · `GLOBAL_MULTIYEAR_PHY_001_030` (GLORYS12V1) ·
  `cmems_mod_glo_phy_my_0.083deg_P1D-m_202311` · **2026-09-20T06:58:29Z**
- The STAC document carries **no total-size field**. Volumes are **derived**
  from `itemSize` × grid geometry.

| quantity | value |
|---|---|
| `zos` itemSize / dtype | 2 bytes / `<i2` |
| grid | 2041 lat × 4320 lon, 0.0833°, 12,227 days |
| tile bbox 19°, **node-inclusive** | **229** × 229 nodes |
| window-plan span | **400 days** |
| **per tile, whole span** | **40.01 MiB** |
| **all four tiles** | **160.04 MiB** |
| global `zos`, full record | 0.20 TiB |

### ⭐ **THE TRUTH FIELD IS BOUGHT ONCE PER TILE, NOT ONCE PER CLASS.**

An OSSE varies the **CONSTELLATION** over **FIXED** truth — that is what makes
it a ground-truth test. So N_epoch-classes multiplies the **re-solves**, not
the download. ⚠ **It DOES scale with the number of tiles**: four tiles is four
buys, 160.04 MiB. *(v1's headline dropped "per tile".)*

**FEASIBLE** — derived, not asserted: 160.04 MiB against a 50 GiB
pre-registered CMEMS budget (0.31%), with 311 GiB free disk.

⚠ **Three declared limits on this figure:**

1. **It is the SOLVE box.** Simulating observations needs truth over the **obs
   footprint** (solve bbox + the 1.0° operative halo = 21°), which is
   **(21/19)² = 1.22× larger**. Not applied, because the obs-footprint choice
   belongs with the run design.
2. **It is the UNCOMPRESSED array size**, so it is a **bound** on wire volume,
   not a wire measurement. GLORYS netCDF is deflate-compressed int16.
3. **`zos` only** — no MDT, mask or ancillary. Adequate for a nadir-SLA OSSE;
   stated as a scope choice.

⚠ The window plan is **overlapping, not contiguous**: 9 × 60 d on a 45-d
stride, so 540 window-days sit over a **400-day union**. The union is the
download basis because each day is bought once.

## 8 — ⛔ THE FIGURES ARE A LOWER BOUND — **INCLUDING THE COMPUTE FIGURE**

**Widened under pin 239(e).** v1 attributed the lower bound to uncosted
*engineering* alone, so a reader concluded the compute band was sound. **It is
not:** the flat model under-prices every class above 5 missions, and **7 of the
15 classes are above it.**

**Covered:** constellation-varied re-solves and the truth download, both at
declared model assumptions.

**NOT costed:**

1. **Truth-provider wiring** — the `TRUTH` interface is **DORMANT since 4b**;
   re-arming it is unmeasured engineering time and is the **largest open item**.
2. Per-class observation simulation from the truth field.
3. Scoring and analysis of 15 outputs.
4. **Non-convergence retries** — the legs ran 424–554 PCG iterations at 5
   missions; the 3-mission classes are sparser, worse-conditioned, and outside
   anything measured.
5. **Calendar time and box occupancy** — these are serial single-host hours,
   with a launch gate of 2× predicted peak RSS per class.

**The gap is BOUNDED on the download axis and OPEN on both the engineering and
the compute-model axes.**

## 9 — Scope subsets: the ORDERING is a counting fact

⛔ **v1's ordering was WRONG.** Under the flat model post-lift looked cheaper
than pre-lift because it has fewer classes. **It has more total observations.**

| subset | classes | total missions | flat ×kuroshio | **obs-scaled ×kuroshio** | CANNOT establish |
|---|---|---|---|---|---|
| full sweep | 15 | 79 | 295.0 h | **328.7 h** | — |
| `fit+validate` | 10 | 61 | 196.7 h | **266.6 h** | transfer into the 5 validate-only epochs, where transfer is actually claimed |
| pre-lift (`mask_66`) | **9** | **35** | 177.0 h | **124.8 h** | anything about the 6 modern post-lift constellations |
| post-lift | **6** | **44** | 118.0 h | **203.9 h** | era-transfer across the 1992–2009 boundary — the era gap the claim is weakest at |
| validate-only | 5 | 18 | 98.3 h | **62.1 h** | anything fitted; it tests only the transferred epochs |

### ⭐ **POST-LIFT IS DEARER THAN PRE-LIFT. This is a COUNTING FACT.**

Post-lift has **fewer classes (6 vs 9) and more total missions (44 vs 35)**. So
it is dearer under **any** cost monotone in observation count — the direction
does **not** depend on the fitted exponent. Only the flat model reverses it,
and that model is what the review overturned.

**The magnitudes** above carry §4's pin-139 declaration. **The direction** does
not (pin 239a/b).

### ⛔ v1's §8 editorial is WITHDRAWN

> ~~*"The cheapest subsets are cheap precisely because they drop the epochs the
> era-transfer claim is weakest at. Cost and evidential value move together
> here."*~~

**It was an artefact of the flat model and inverts with it**: the sparse
historical constellations — exactly where era-transfer is weakest — carry the
**fewest** observations and are therefore the **cheapest** classes to solve.

⛔ **It is NOT replaced with the opposite editorial** (pin 239c). That would be
the same mistake with a different sign. The inversion is recorded as a
**finding**; no claim is made about cost and value moving together or apart.

## 10 — Recommendation: both options presented, neither elected

| option | cost | CAN establish | CANNOT establish |
|---|---|---|---|
| **run at Stage-2 entry** | same compute; truth download trivial either way | the era-transfer claim against truth where it becomes load-bearing | anything for Gate 1 — it closes no Stage-1 item |
| **run now** | flat 295.0–412.2 h; obs-scaled (projected) 328.7–459.2 h; + 160.04 MiB truth | the same thing, earlier | any Gate-1 item — the OSSE is not a Gate-1 deliverable, and Gate 1 already carries two ruled WAITs (219, 224) |

> ## ⬛ DECISION CELL — **EMPTY.** The OSSE run decision is the owner's.

## 11 — Basis, stated in-row (pin 99c)

| figure | source | status |
|---|---|---|
| four leg walls, n_obs | `phase14.stage1.tiles.<tile>` | MEASURED, 9/9 CONVERGED |
| N_epoch-classes, mission counts | sealed `content.epoch_table` | DERIVED from sealed evidence |
| **obs-scaling exponent 1.4146** | fitted from the four legs | **PROJECTED — pin-139 declared, outside measured span** |
| probe 3.4399 h/window, 123.84 h | `tier2_probe_kuroshio_m100` | CONVERGED; **declared projection**, cross-check only |
| truth volume | STAC metadata query 2026-09-20T06:58:29Z | DERIVED from `itemSize` × geometry; a **bound** on wire volume |
| window-plan span | `tiles.quiet_gyre.window_plan` | MEASURED |
| leg constellation | `phase14_stage1_run.PROBE_MISSIONS` | test-pinned (rows carry no mission list) |
| capped T2 probe | — | **NEVER USED** (99c / pin 23a) |
