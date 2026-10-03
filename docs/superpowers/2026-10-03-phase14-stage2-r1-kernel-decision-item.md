# R1 — THE KERNEL DECISION ITEM (owner pin 279). ⚖ DECISION CELL EMPTY.

> **Prepared under owner ruling PART 64, pins 279 / 286-R1**, 2026-10-03, against
> `origin/main` at `9d16b17` (the PART-64 commit; `ls-remote` in step, tree clean).
>
> ⛔ **NOTHING RAN.** No producer, no map, no solve, no store write, no mirror `sync`
> (276d). `operative_halo_deg()` is **UNTOUCHED** (219d, 263.1). The per-run tally guard
> is unfixed; the closure record is frozen; seal v1 is untouched and its v2 is UNSPENT.
> Nothing in Stage 2 opens here; tasks 14-21 stay halted.
>
> ⚖ **THE DECISION CELL AT §8 IS EMPTY.** This document is *priced, owner to decide* —
> the pin-235(e) form. It is **not** an election, and no exit below is recommended as
> elected. The three exits are 219(c)'s two plus 216's, presented as pin 279 directs:
> each with its consequence for **the pavement key**, **n_eff's L**, and **southern's
> obs frame**.
>
> **Every number below is DERIVED** from the store, the frame and the source at this
> commit — never recalled. Each row names its derivation.

---

## 1. The binding constraint is a 2.0° halo budget at `southern` — derived

| quantity | value | derivation |
|---|---|---|
| `southern` core | `[215, 230, −62, −47]` | `phase14.stage1.tiles.southern.frame.core` |
| `southern` solve_bbox | `[213, 232, −64, −45]` | same node, `.solve_bbox` (core ± 2.0° overlap) |
| obs framing | solve **GRID NODE** extent ± halo | `spatial_tiles.py:85-105` (`obs_bbox`) |
| poleward grid node | **−64.0** exactly | `np.arange(−64, −45+res, res)`; the overshoot quirk is at the *max* end |
| ⭐ **halo budget** | **2.0000°** | `66 + solve_bbox.lat_min`, the pack's own derivation (`phase14_kernel_pack.py:380`) |
| boundary convention | halo **== 2.0°** puts the obs edge at exactly −66.0 and is **recorded CLEAR** | `phase14_kernel_pack.py:388-391` — breach is STRICT |
| **today** | halo **1.0°** → obs edge **−65.0**, margin **1.0000°** | agrees with draft §2 and Gate-1 pack §1.11 as corrected by pin 215 |

⭐ **So the halo has exactly 1.0° of unspent room at `southern`, and `southern` is a fit
tile carrying era-fits under D1.** Every exit below is scored against that 2.0° budget.

**Pin 219(a) reproduces exactly** from this frame (computed, not quoted):

| halo set at | latitude | halo = 1/cos φ | obs edge | margin to ±66 |
|---|---|---|---|---|
| φ0 — the tile's middle | −54.400 | 1.7179° | −65.7179 | **+0.2821°** |
| core poleward edge | −62.000 | 2.1301° | **−66.1301** | **−0.1301° BREACH** |
| solve-bbox poleward edge | −64.000 | 2.2812° | **−66.2812** | **−0.2812° BREACH** |

⭐ **217(c)'s ambiguity, resolved in the direction the owner feared.** *"The km-space row
spends 0.7179° of the 1.0° available"* means the operative halo **becomes 1.7179°**,
**consuming** 0.7179° of the 1.0° margin and leaving **0.2821°** — *less* margin, not
more. And that is the φ0 row, which 219(a) ruled is **the wrong latitude to price at**.

---

## 2. The three exits

| # | exit | source |
|---|---|---|
| **(a)** | a **smaller km scale** | 219(c) |
| **(b)** | a **latitude-aware halo** — a code change under fork-d pin 4's single point of change | 219(c) |
| **(c)** | **F-2 hull widening** — widening the shipped `[33, 43]` latitude hull so options 2/3 stop being inert at `southern` | 216 |

⛔ **(a) and (b) are not alternatives to the same end.** (a) changes *what the scale is*
and leaves the halo machinery as it stands; (b) changes *the machinery* and leaves the
scale free. 219(b)'s structural finding — *"a SINGLE SCALAR halo cannot express a km-space
kernel"* — is a statement about (b)'s absence, so (a) alone **inherits** it.

---

## 3. "Latitude-aware" has two readings, and they are not close

The halo auto-follow is **1:1 with the scale's degree footprint** — today's shipped
1.0° / 111.195 km scale gives today's 1.0° halo (`phase14_kernel_pack.py:58-61`,
`options()` option-1 row). Under a **km** scale that footprint is anisotropic in degrees:
`L/111.195` meridional × `(L/111.195)/cos φ` zonal.

- **(b1) a latitude-aware SCALAR.** One halo per tile, set from the **zonal** footprint at
  the poleward reach (the single scalar must cover the wider axis — review finding F-3,
  `obs_bbox` applies `self.halo_deg` to all four edges).
- **(b2) a PER-AXIS halo.** The **latitude** edges take the **meridional** footprint; the
  longitude edges take the zonal footprint at the local latitude.

**Ceilings on the named scale L, derived at `southern`'s solve-bbox poleward edge:**

| reading | ceiling on halo | ⇒ ceiling on L |
|---|---|---|
| **(b1)** scalar, zonal footprint at −64° | 2.0000° | **L ≤ 97.489 km** (0.8767° meridional) |
| **(b2)** per-axis, meridional on the lat edges | 2.0000° | **L ≤ 222.390 km** (2.0000°) |

**Which ladder rungs survive** (`LADDER` = `scale_set(80, lam_max=905)`, 8 rungs,
`miost_basis.py:28`):

| rung (km) | merid. deg | (b1) halo @−64 | (b1) obs edge | (b1) | (b2) halo | (b2) obs edge | (b2) |
|---|---|---|---|---|---|---|---|
| **80.000** | 0.7195 | 1.6412 | −65.6412 | **CLEAR** | 0.7195 | −64.7195 | **CLEAR** |
| 113.137 | 1.0175 | 2.3210 | −66.3210 | BREACH | 1.0175 | −65.0175 | **CLEAR** |
| **160.000** | 1.4389 | 3.2824 | −67.2824 | BREACH | 1.4389 | −65.4389 | **CLEAR** |
| **226.274** | 2.0349 | 4.6420 | −68.6420 | BREACH | 2.0349 | **−66.0349** | **BREACH by 0.0349°** |
| 320.000 | 2.8778 | 6.5648 | −70.5648 | BREACH | 2.8778 | −66.8778 | BREACH |
| 452.548 | 4.0699 | 9.2841 | −73.2841 | BREACH | 4.0699 | −68.0699 | BREACH |
| 640.000 | 5.7557 | 13.1296 | −77.1296 | BREACH | 5.7557 | −69.7557 | BREACH |
| 905.097 | 8.1397 | 18.5681 | −82.5681 | BREACH | 8.1397 | −72.1397 | BREACH |

---

## 4. ⭐ THE COLLISION — fork-e pin 2(i) is UNSATISFIABLE at `southern` under every exit

**Fork-e pin 2(i), verbatim** (program spec `2026-07-21-phase14-scaling-program-design.md:425-427`):

> *"MIOST has a LADDER, not 'the' solve scale — K is parameterized by a **NAMED mid-ladder
> spatial scale in the λx neighborhood** + the shipped L_t, rationale recorded; the fork-d
> pin-4 auto-follow linkage **binds to the NAMED scale**."*

It imposes **two** conditions on one number, and the halo follows that number.

| condition | rungs satisfying it | derivation |
|---|---|---|
| **mid-ladder** (4th/5th of 8) | 226.274, 320.000 | `LADDER` positions |
| **in the λx neighborhood** | 160.000, 226.274 | λx recorded: `southern` **141.9472**, `kuroshio` **232.5339** km (draft §6.3); anchor **174.5211** (`phase14.stage1.gate5`) |
| **both** | ⭐ **226.274 — the unique rung** | intersection |
| **admissible at southern, (b2)** | 80.000, 113.137, 160.000 | §3 table |
| **admissible at southern, (b1)** | **80.000 only** | §3 table |

⛔ **226.274 km — the only rung that is both mid-ladder and in the λx neighborhood —
BREACHES by 0.0349° under the MOST GENEROUS halo reading.** Under (b1) it breaches by
2.642°. There is no exit under which pin 2(i)'s two conditions are jointly satisfiable at
`southern`.

**So the ruling must relax one of the two conditions.** The shapes:

- **Relax "mid-ladder" → keep "λx neighborhood":** the named scale is **160.000 km**
  (λx-neighbourhood, rung 3 of 8), reachable **only under (b2)**.
- **Relax "λx neighborhood" → keep "mid-ladder":** no rung is admissible under either
  reading; this shape is **empty** at `southern`.
- **Relax both → take the bottom rung:** **80.000 km**, admissible under **(b1) and (b2)**
  and under exit **(a)** as the code stands. It is two rungs below the lowest recorded λx
  (141.9472) and 0.56× the anchor's.

⚠ **And λx is `recorded_absent` at `equatorial` and `quiet_gyre`** (pins 160a/161, draft
§6.3) — half the fit set. Pin 280 already requires the scale be named *"by a rule that
needs no per-tile λx"*. The three shapes above are each such a rule; the point here is
that the **halo budget**, not λx's availability, is what eliminates two of them.

---

## 5. ⛔ NEW FINDING — there IS a second constant, and it is the one inside `params_key`

**217(d), verbatim:** *"The halo auto-follows via `operative_halo_deg()` per fork-d pin 4 —
**the single point of change, no second constant**."*

**There is a second constant, and it is not wired to the first:**

| constant | value | where | reach |
|---|---|---|---|
| `operative_halo_deg()` | `return 1.0` | `application/spatial_tiles.py:41-48` | the **obs frame** (`TileFrame.halo_deg` → `obs_bbox`) |
| `HALO_DEG` | `= 1.0  # D7` | `methods/miost_basis.py:34` | ⭐ **inside `BasisSpec.key()`** (`:80`), a token of **every `params_key`** |

**Neither references the other.** Grepped at this commit: `miost_basis` does not import
`spatial_tiles`, and `HALO_DEG`'s consumers are `stage_miost_gate_run.py:204` and three
`diag_*` scripts. **So a kernel ruling has three possible outcomes, and one of them is
silent:**

1. **Change `operative_halo_deg()` only** → the obs frame moves; maps, `n_obs` and `n_eff`
   all change; ⛔ **`params_key` does NOT change.** Byte-identity tokens then assert "same
   basis" across two different obs frames. **This is the dangerous outcome, and it is the
   one fork-d pin 4's "nothing else" wording invites.**
2. **Change both** → every `params_key` re-keys. The pavement, the 12 era-fits, the hull,
   the pooled law, the extrapolation audit, seal v2 (§10.5) and precondition §19.2-A7 are
   all keyed under the new scale — which is exactly why **279 puts the kernel decision
   UPSTREAM of the freeze**.
3. **Change neither** (exit (c), or no exit) → key and frame both unchanged.

⚖ **`BasisSpec` carries no scale field.** Its `key()` tokens are `alpha`, `l_t`, `n_dir`,
`ladder`, `beta`, `W`, `V`, `stride`, `halo`, `lam_ref`, `r_ref`, `dom`. The named scale is
a **choice of rung**, not a change to `ladder`, so **`halo=` is the ONLY token through
which the kernel decision can reach the pavement key.** That is narrower than the frame
review's framing — and it is why outcome 1 is silent rather than loud.

---

## 6. The exits, with their three consequences

### (a) a smaller km scale — halo machinery unchanged

| axis | consequence |
|---|---|
| **pavement key** | re-keys **iff `HALO_DEG` is changed with it** (§5). The scale must be ≤ **97.489 km**, so the halo *falls* from 1.0° to 0.7195° at rung 80 — a re-key in the **direction of more** margin |
| **n_eff's L** | forced to **80.000 km**, the bottom rung — the only rung admissible under the standing scalar halo. Neither mid-ladder nor λx-neighbourhood: pin 2(i) is **broken on both conditions** |
| **southern's frame** | obs edge **−64.7195**, margin **1.2805°** — *better* than today's 1.0° |
| **code surface** | `operative_halo_deg()` + `HALO_DEG`. Anchor identity **not preserved by construction** — different kernel family *and* metric; check 1's bit-identity against the Phase-13 winner must be re-established (`phase14_kernel_pack.py` option-1 row) |
| **inherits** | 219(b)'s structural finding: the scalar still cannot express a km-space kernel; it merely stops breaching because the scale shrank below the breach point |

### (b) a latitude-aware halo

| axis | consequence |
|---|---|
| **pavement key** | ⛔ **`halo={HALO_DEG}` stops being expressible as a scalar.** `key()` must carry the halo **RULE** (or the named scale), or the key stops identifying the obs frame it is supposed to identify. This is a **schema** change to `params_key`, not a value change |
| **n_eff's L** | **(b1)** → 80.000 only; pin 2(i) broken as in (a). **(b2)** → **160.000 km** becomes reachable — the λx-neighbourhood rung, with "mid-ladder" relaxed. ⭐ **(b2) is the only exit that keeps n_eff's L in the λx neighbourhood** |
| **southern's frame** | **(b1)** @80 km: edge −65.6412, margin 0.3588°. **(b2)** @160 km: lat edge **−65.4389**, margin **0.5611°**; the lon edges widen to 3.2824° at −64° |
| **code surface** | ⛔ **fork-d pin 4's "THIS function changes — nothing else" is FALSE here.** At minimum: `operative_halo_deg()`'s signature (it needs a latitude), `TileFrame.halo_deg: float`, `TileFrame.__post_init__`'s `halo_deg < 0` validation, `TileFrame.obs_bbox` (which today applies one scalar to all four edges), `BasisSpec.key()`'s `halo=` token, and the two call sites at `spatial_tiles.py:156` / `:294` plus `phase14_stage1_run.py:479` |
| **note** | (b2) is **per-axis**, which 219(c) did not name. If the owner reads 219(c)'s "latitude-aware" as (b1) only, then **no exit reaches the λx neighbourhood** and §4's third shape (80 km) is forced |

### (c) F-2 hull widening (216)

| axis | consequence |
|---|---|
| **pavement key** | **unchanged** — options 2/3 are **degree-space**; the scale stays 1.0°, the halo stays 1.0°, `params_key` and `HALO_DEG` are untouched. ⭐ **The only exit that does not disturb the pavement at all** |
| **n_eff's L** | ⛔ **does not answer pin 2(i).** The named scale drives the halo via fork-d pin 4 regardless of which kernel is elected, so §4's collision **survives (c) untouched**. (c) settles *which kernel family*, not *which scale* |
| **southern's frame** | **unchanged** — obs edge −65.0, margin 1.0000° |
| **code surface** | widening `core.parameters._LAT_HULL` from `[33, 43]` — ⛔ **a shipped, SIGNED component**, which 216 rules is *"a producer decision with its own chain and touch, not something a decision pack elects"*. Anchor identity under options 2/3 holds **only at L0 = 1 AND variance = 1 exactly**, and is ⚠ **pinned by NO test** (`phase14_kernel_pack.py` option-2 row) |
| **why it is live** | 216: options 2/3 are **INERT** at `southern` because `LatitudeField.at` clamps to the anchor box, so `m` is constant across the whole SO core. Recorded *"so Stage 2 does not rediscover it"* |

---

## 7. What the ruling has to settle

1. ⚖ **Which exit** — (a), (b), (c), or a combination. (a) and (b) are not mutually
   exclusive; (c) is orthogonal to both and settles nothing in §4.
2. ⚖ **If (b): which reading** — (b1) latitude-aware scalar, or (b2) per-axis. This single
   choice decides whether **160.000 km** exists as an option at all (§3).
3. ⚖ **Which of pin 2(i)'s two conditions is relaxed** — "mid-ladder" or "in the λx
   neighborhood". §4 shows they cannot both hold at `southern`. Keeping "mid-ladder"
   yields the **empty** set.
4. ⚖ **The named scale itself** — the number `n_eff`'s L, D4's census, D5's se, D13 and
   D17's four bars are all denominated in (pin 280 then makes every bar mechanical).
5. ⚖ **Whether `HALO_DEG` moves with `operative_halo_deg()`** (§5). Outcome 1 is a silent
   divergence between the obs frame and `params_key`; it should be ruled out explicitly
   rather than left to the executor.
6. ⚖ **Whether fork-d pin 4's "nothing else" is amended** — under (b) it is false as
   written, and the amendment is the honest record rather than a quiet widening.

---

## 8. ⚖ DECISION CELL — **EMPTY**

Priced, owner to decide. ⛔ **No exit is elected here, and `operative_halo_deg()` is not
touched.** Until this cell carries a ruling: **n_eff is undefined, so no bar has a number
(pin 280), the geometry step is not recomputed (D6/D7), the pavement is not frozen, the
census does not select (D4), and no era-fit runs** — 279's order, in reverse.
