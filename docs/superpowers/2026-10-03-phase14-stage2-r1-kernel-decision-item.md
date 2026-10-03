# R1 — THE KERNEL DECISION ITEM (owner pin 279), **SPLIT into R1a + R1b**

> **Prepared under owner ruling PART 64, pins 279 / 286-R1**, 2026-10-03, against
> `origin/main` at `9d16b17`. ⚖ **AMENDED IN PLACE the same day** on the owner's R1
> directive, which (i) **verified** the first draft's arithmetic by re-derivation,
> (ii) ordered a **FOURTH shape** priced, (iii) **SPLIT R1**, and (iv) **RULED** the
> two-constant question. **Rewritten, not layered over** (pin 154).
>
> ⛔ **NOTHING RAN.** No producer, no map, no solve, no store write, no mirror `sync`
> (276d). `operative_halo_deg()` is **UNTOUCHED** (219d, 263.1). The per-run tally guard
> is unfixed; the closure record is frozen; seal v1 is untouched and its v2 is UNSPENT.
> Nothing in Stage 2 opens here; tasks 14-21 stay halted. The Stage-2 draft is not edited.
>
> ⚖ **TWO DECISION CELLS AT §9, BOTH EMPTY** — *priced, owner to decide*, the pin-235(e)
> form. No shape below is recommended as elected.
>
> **Every number is DERIVED** at this commit, from the store, the frame and the source —
> never recalled. Each row names its derivation.

### What the amendment changed, recorded so it is not re-derived

⭐ **The first draft treated fork-e pin 2(i)'s LAST CLAUSE as fixed, and that clause is
the whole collision.** It reported pin 2(i) as *"unsatisfiable at `southern` under every
exit"*. ⛔ **That finding is now CORRECTED: pin 2(i)'s two conditions are jointly
satisfiable at 226.274 km.** What collides them with ±66 is only the clause binding the
covariate's scale to the solver's obs halo. The superseded sentence is named here rather
than deleted, the frame review's §5.1 precedent. **The §1 arithmetic and the §6
two-constant finding are unaffected and were re-derived by the owner.**

---

## 1. The binding constraint is a 2.0° halo budget at `southern` — derived

| quantity | value | derivation |
|---|---|---|
| `southern` core | `[215, 230, −62, −47]` | `phase14.stage1.tiles.southern.frame.core` |
| `southern` solve_bbox | `[213, 232, −64, −45]` | same node, `.solve_bbox` (core ± 2.0° overlap) |
| obs framing | solve **GRID NODE** extent ± halo | `spatial_tiles.py:85-105` (`obs_bbox`) |
| poleward grid node | **−64.0** exactly | `np.arange(−64, −45+res, res)`; the overshoot quirk is at the *max* end |
| ⭐ **halo budget** | **2.0000°** | `66 + solve_bbox.lat_min` (`phase14_kernel_pack.py:380`) |
| boundary convention | halo **== 2.0°** → obs edge exactly −66.0, **recorded CLEAR** | `phase14_kernel_pack.py:388-391` — breach is STRICT |
| **today** | halo **1.0°** → obs edge **−65.0**, margin **1.0000°** | agrees with draft §2 and Gate-1 pack §1.11 as corrected by pin 215 |

**Pin 219(a) reproduces exactly from this frame** (computed, not quoted) — the footprint of
a km scale is `L/111.195` meridional × `(L/111.195)/cos φ` zonal:

| halo set at | latitude | halo = 1/cos φ | obs edge | margin to ±66 |
|---|---|---|---|---|
| φ0 — the tile's middle | −54.400 | 1.7179° | −65.7179 | **+0.2821°** |
| core poleward edge | −62.000 | 2.1301° | **−66.1301** | **−0.1301° BREACH** |
| solve-bbox poleward edge | −64.000 | 2.2812° | **−66.2812** | **−0.2812° BREACH** |

⭐ **217(c)'s ambiguity resolves the way the owner feared.** *"The km-space row spends
0.7179° of the 1.0° available"* means the halo **becomes 1.7179°**, **consuming** 0.7179°
of the 1.0° margin and leaving **0.2821°** — *less* margin. And that is the φ0 row, which
219(a) ruled is the wrong latitude to price at.

⚖ **The budget is PER TILE: `budget = 66 + solve_bbox.lat_min`.** It reaches **zero** at
`solve_bbox.lat_min = −66` and is negative beyond. On D1's 15°/2° lattice continued
poleward, `southern` (**+2.0°**) is the poleward-most tile with any budget at all; the next
row's solve box begins at −79 (**−13.0°**), which is D4's pole region and 2G's. **So the
±66 question is settled at `southern` and does not recur until the poles.**

---

## 2. The four shapes

| # | shape | source |
|---|---|---|
| **(a)** | a **smaller km scale** | 219(c) |
| **(b)** | a **latitude-aware halo** — a code change under fork-d pin 4's single point of change | 219(c) |
| **(c)** | **F-2 hull widening** — widen the shipped `[33, 43]` latitude hull so options 2/3 stop being inert at `southern` | 216 |
| ⭐ **(d)** | **DECOUPLE** — n_eff's K takes the named scale; the halo follows the **solver's own** operative kernel scale (fork-d pin 4), never the covariate's | **owner, this directive** — an amendment of a program-spec pin, so the owner's to elect |

---

## 3. ⭐ THE COLLISION IS THE LINKAGE, NOT PIN 2(i)

**Fork-e pin 2(i), verbatim** (program spec `2026-07-21-phase14-scaling-program-design.md:425-428`):

> *"MIOST has a LADDER, not 'the' solve scale — K is parameterized by a **NAMED mid-ladder
> spatial scale in the λx neighborhood** + the shipped L_t, rationale recorded; **the
> fork-d pin-4 auto-follow linkage binds to the NAMED scale**."*

**Fork-d pin 4, verbatim** (same spec, `:365-367`):

> *"**Halo derives from the OPERATIVE kernel scale per tile** (constant 1.0° today ⇒
> current practice exactly; if **the constraint-3 high-latitude decision** changes scales,
> the halo follows automatically — no second constant to rot)."*

⭐ **Fork-d pin 4 never mentions the covariate.** It names *the operative kernel scale* and
makes *the constraint-3 high-latitude decision* — **the solver's** — its trigger. The
identification of that scale with the covariate's NAMED scale is made in **one place
only**: pin 2(i)'s last clause. ⛔ **So shape (d) amends ONE CLAUSE of fork-e pin 2(i) and
NOTHING in fork-d pin 4.**

**Without the clause, pin 2(i)'s two conditions are jointly satisfiable** — §5's rule
lands on **226.274 km**, rung 4 of 8 (mid-ladder) and inside the recorded λx range. **With
it, that same rung demands a 2.0349° halo and breaches by 0.0349°.** The collision is the
clause's alone.

### 3.1 Every citation of the linkage, and what relies on it

| # | site | what it cites | survives (d)? |
|---|---|---|---|
| 1 | program spec `:427` | ⭐ **THE CLAUSE ITSELF** | ⛔ **amended — this is the election** |
| 2 | program spec `:365-367` (fork-d pin 4) | solver scale → halo, **per tile** | ✅ untouched |
| 3 | program spec `:702` (deliverable 1-4) | *"the decision binds the halo auto-follow (fork-d pin 4)"* — **the kernel decision** | ✅ untouched |
| 4 | ruling **217(c)** | *"The election binds the halo auto-follow … the halo sets the ±66 margin"* — the kernel election | ✅ untouched |
| 5 | ruling **217(d)** | *"the single point of change, no second constant"* | ✅ untouched as to the link; ⛔ **already FALSE as to "no second constant"** — §6 |
| 6 | ruling **219(c)/(d)** | the two exits; `operative_halo_deg()` untouched | ✅ untouched — **becomes R1b** |
| 7 | `docs/project-context.md:55` | the kernel decision binds the auto-follow | ✅ untouched |
| 8 | T6 plan AC + `.tasks.json` + C1→2 **C-04** + `phase14_kernel_pack.py:697` | per-option *"halo auto-follow consequence"* | ✅ untouched — all solver-side |
| 9 | frame review **§2a** | *"n_eff's kernel length is bound to the constant the kernel decision sets"* | ⛔ the **COUPLING** sub-claim dissolves. ⭐ **The HOMING finding STANDS** — it rests on 219(c), closure obligation 1 and 274(b)'s own words, not on the linkage. **(d) does NOT rehabilitate 274(b)'s mis-homing** |
| 10 | **pin 279** + `PROGRESS.md:18` | the re-sequence, *"the kernel scale is upstream"* | ⚖ **SPLITS rather than falls** — §5's re-sequence row |
| 11 | **the DRAFT** | **nothing.** Verified counts at `9d16b17`: `"NAMED scale"` **0**, `"named scale"` **0**, `"mid-ladder"` **0**, `"auto-follow"` **0**, `"fork-d pin 4"` **0**, `"pin 2(i)"` **0**, `HALO_DEG` **0**; `operative_halo_deg` **1** (only §20.1's 263.1 row) | ✅ **nothing to rewrite** |
| 12 | **the CODE** | **nothing.** `operative_halo_deg()` returns a literal; no code derives a halo from a ladder rung. **The linkage is a pin, never a wiring** | ✅ **nothing to unwire** |

⭐ **Exactly two sites rely on the clause** — the frame review's coupling sub-claim and pin
279's re-sequence. **Neither the draft nor the code does.** So (d) is an amendment with no
rewrite and no unwiring behind it.

---

## 4. Does (d)'s coherence argument hold? — TESTED, and it holds affirmatively

**Fork E, verbatim** (program spec `:386-392`):

> *"— **pure geometry functional** (positions + times, never values; legal per the Phase-8
> theorem distinction), **computed by the geometry-provider layer, never through the
> solver**. **Rejected alternatives recorded: geometry-determined posterior σ (theorem-legal
> information-wise but routes through the solver — circular pinning, config-dependent**;
> the ensemble-σ theorem's spirit honored beyond its letter); raw counts-in-radius …"*

⭐ **IT HOLDS, AND MORE STRONGLY THAN PERMISSIVELY.** Fork E did not merely place n_eff
outside the solver — it **rejected a candidate covariate** *because* it was
**config-dependent through the solver**. The obs halo **is** a solver configuration. So
binding n_eff's kernel length to the halo-driving scale reintroduces, by the back door,
the very property fork E rejected by the front. ⛔ **Decoupling restores fork E's stated
intent; it does not depart from it.**

**The one argument FOR coupling, tested:** *n_eff should count only data the solver uses.*

- ✅ **MET — but by the obs SET, not the kernel LENGTH.** Length is a weighting scale;
  the frame is a support restriction. They are separate knobs, and only the second
  carries the argument.
- ⛔ **AND IT NEEDS A SPEC CLAUSE TO ACTUALLY HOLD.** §12.2 establishes the acquisition
  unit as the **native daily file, which is GLOBAL**. An unrestricted sum would count obs
  the solver never sees. **REQUIRED CLAUSE (d):** *n_eff's obs support is each tile's
  FRAMED obs — `obs_bbox` at the operative halo — never the global file.* With it, density
  near a frame edge falls exactly as the solver's information does, because **the same
  truncation is applied to both**.
- ⚠ **HONEST LIMIT: (d) decouples n_eff's LENGTH from the halo, not its SUPPORT.** A later
  R1b halo change still moves n_eff, through the frame. **So R1b keeps an n_eff
  consequence — re-running the geometry step — but no longer a pin-2(i) collision, and no
  longer a DEFINITIONAL block on R2.** That asymmetry is what makes the split work.

---

## 5. (d) priced on the three axes — DERIVED, not taken from the expectation

| axis | (d) DECOUPLE | derivation |
|---|---|---|
| **pavement key** | ⭐ **UNCHANGED** — confirms the expectation | The named scale is no `BasisSpec` field. `key()`'s tokens are `alpha, l_t, n_dir, ladder, beta, W, V, stride, halo, lam_ref, r_ref, dom`. The named scale is a **choice of rung**, so `ladder=` is unchanged; and under (d) `halo=` does not follow it. **`halo=` is the ONLY token the kernel question can reach, and (d) severs its tie to the covariate** |
| **n_eff's L** | ⭐ **226.274 km** — both pin-2(i) conditions **KEPT** — confirms the expectation | Rung **4 of 8** (mid-ladder) and inside the recorded λx range. Ratios: **1.594×** southern's λx, **0.973×** kuroshio's, **1.297×** the anchor's |
| **southern's frame** | ⭐ **UNCHANGED** — obs edge **−65.0**, margin **1.0000°** — confirms the expectation | The frame depends on `operative_halo_deg()`, which (d) leaves at 1.0 and which stays untouched |
| **±66** | **not engaged by R1a at all** | 226.274 km would demand a 2.0349° halo **only if the halo followed it** — precisely the clause (d) strikes |
| **re-sequence (279)** | ⚖ **SPLITS, does not fall** | **R1a** → n_eff defined (280) → every bar gets its number → census (D4). **R1b** → *if* it moves the kernel or halo → geometry step (D6/D7) → freeze. ⭐ **R1a no longer waits on a signed-component touch or on 2G's poleward fleet, so pin 280 unblocks on R1a alone** |
| **cost** | an amendment to a program-spec pin, recorded verbatim as one | **no code change** |

### 5.1 "λx neighbourhood" as an explicit RULE (pin 280)

λx is `recorded_absent` at `equatorial` and `quiet_gyre` (pins 160a/161), so the rule must
need **no per-tile λx**:

> ⭐ **RULE (R1a):** the named scale is the ladder rung lying inside the closed interval
> spanned by the **RECORDED** λx values across the fit set and the anchor, and — among
> those — the one that is **mid-ladder**. Tiles whose λx is `recorded_absent` contribute no
> endpoint and are **never imputed**.

**Derived:** recorded interval **[141.9472, 232.5339]** km (southern, kuroshio; the
anchor's 174.5211 is interior and moves no endpoint). Rungs inside: **{160.000,
226.274}**. Mid-ladder rungs (4th, 5th of 8): **{226.274, 320.000}**. Intersection:
⭐ **{226.274} — unique.**

✅ The rule needs λx at **some** tile, never at **every** tile; it is stated **before** the
number (§7-10); and it is reproducible from the store rather than chosen.

---

## 6. ⚖ RULED — the two constants are BOUND (owner, this directive)

**217(d), verbatim:** *"The halo auto-follows via `operative_halo_deg()` per fork-d pin 4 —
**the single point of change, no second constant**."* **Fork-d pin 4** adds: *"no second
constant to rot."*

⛔ **There is a second constant, and it is the one inside `params_key`:**

| constant | value | where | reach |
|---|---|---|---|
| `operative_halo_deg()` | `return 1.0` | `application/spatial_tiles.py:41-48` | the **obs frame** (`TileFrame.halo_deg` → `obs_bbox`) |
| `HALO_DEG` | `= 1.0  # D7` | `methods/miost_basis.py:34` | ⭐ **inside `BasisSpec.key()`** (`:80`), a token of **every `params_key`** |

**Neither references the other** — `miost_basis` imports only `miost_sizing`; `HALO_DEG`'s
consumers are `stage_miost_gate_run.py:204` and three `diag_*` scripts.

⚖ **THE RULING: THE TWO CONSTANTS ARE BOUND. Any halo change moves both, and changing
`operative_halo_deg()` alone is REFUSED.** The outcome it forecloses is the silent one —
the obs frame moves while `params_key` does not, so byte-identity tokens assert "same
basis" across two different obs frames.

⭐ **This is the THIRD instance of F1/262c's family** — *"a check that reads one key while
the world writes another, producing a result that looks like evidence and is not"* (draft
§7.7), after the tally-guard key mismatch and the mixed-pavement comparison.

**▶ PLAN WORK (R2's plan, not this ruling):** `HALO_DEG` **derives from**
`operative_halo_deg()` — **one origin** (§7-12: the key has one origin) — with

1. a test that **today's `params_key` bytes are UNCHANGED** at halo 1.0 (the identity
   guard), and
2. a ⭐ **NEGATIVE CONTROL that a halo change RE-KEYS** — so the binding can fail, and is
   not merely asserted.

⚖ **This repairs a pin that was asserted and never wired; it does not amend fork-d pin 4.**

⛔ **Under (b) the scalar token cannot express the rule at all** — a latitude-aware or
per-axis halo is not a number. **That schema change is R1b's to price, not this plan
task's.**

⚠ **A latent second facet, FLAGGED not fixed:** fork-d pin 4 promises a halo *"per tile"*,
and `TileFrame.halo_deg` is per-instance — but `key()` reads the **module-global**
`HALO_DEG` and can record only **one** number. The key is accidentally correct today
because `make_tiles` gives every tile `operative_halo_deg()`. **R1b prices this if a
per-tile or per-axis halo is elected.**

---

## 7. R1b — the SOLVER kernel exit, priced on the SOLVER's merits

⛔ **Priced here on the solver's merits only. n_eff's L is R1a's and does not appear.**

**The shipped solver scale is `SPATIAL_CORR_DEG = 1.0°` = 111.195 km**
(`validation/params.py:34`) — a **continuous solver parameter, not a ladder rung**. So R1b's
ceilings bind a free scale, and the ladder is R1a's business:

| halo reading | ceiling on the solver scale | vs shipped |
|---|---|---|
| **scalar** (one halo per tile, sized from the **zonal** footprint at −64°) | **97.489 km** (0.8767°) | **0.877×** → ⛔ **requires a ≥ 12.33% reduction** |
| **per-axis** (lat edges take the **meridional** footprint) | **222.390 km** (2.0000°) | **2.000×** → ✅ **the shipped scale is inside; no reduction required** |

⭐ **(b) ALONE CHANGES NOTHING.** At a *degree* scale the footprint is isotropic in
degrees, so a per-axis halo returns 1.0° on both axes and the frame is unmoved. **(b)'s
entire value is that it raises (a)'s ceiling from 97.489 km to 222.390 km.** So the real
R1b choice is a pair, not four independent exits.

| | **R1b-1** km scale + scalar halo | **R1b-2** km scale + per-axis halo | **R1b-3** (c) hull widening | **R1b-4** ruled WAIT |
|---|---|---|---|---|
| **fixes the cos-φ anisotropy?** | ✅ **yes, by construction** — a km metric is isotropic in km at every latitude | ✅ **yes** | ⛔ **no.** Options 2/3 are **degree-space**: the scale's SIZE varies with latitude (opt 2) or the kernel becomes nonstationary (opt 3). **Never enters km space, so 219(b)'s finding is untouched** | ⛔ no — stays unfixed |
| **the frame it leaves** | ⚠ obs drawn **2.2812×** past the kernel's meridional reach on the lat axis (1/cos 64) — not a breach, an asymmetric over-draw | ✅ frame matched per axis | unchanged | unchanged |
| **±66 budget at southern** | scale ≤ **97.489 km**; at that ceiling margin **+0.0000°** (clear, strict) | scale ≤ **222.390 km**; shipped 111.195 → margin **+0.9825°** | **unchanged, +1.0000°** | **unchanged, +1.0000°** |
| **2G's poleward fleet** | the ±66 budget dies at `solve_bbox.lat_min = −66`; **a scalar halo has no room there at all** | ⭐ **the only reading that leaves room poleward** — the lat edge stops paying the 1/cos φ penalty | no change | 219's WAIT persists into 2G, which **219(d) says cannot decide poles without it** |
| **anchor identity** | ⛔ **NOT preserved by construction** — different kernel family **and** metric; check 1's bit-identity vs the Phase-13 winner must be re-established | same as R1b-1 | ⚠ bit-identical **only at L0 = 1 AND variance = 1 exactly**, and that is ⛔ **PINNED BY NO TEST** | ✅ preserved |
| **signed-component touch** | none | none | ⛔ **see the blocker below** | none |
| **key change** | `halo=` **value** moves (and §6 binds `HALO_DEG` with it) → **every `params_key` re-keys** | ⛔ `halo=` **SCHEMA** change — a scalar token cannot express a per-axis rule; §6's per-tile facet lands here too | **none** | **none** |
| **upstream of the freeze (279)?** | ✅ yes | ✅ yes | n/a — see blocker | ✅ moot |
| **Stage 2 vs 2G consistency** | ✅ both on the new kernel | ✅ both on the new kernel | ⛔ **DIVERGENT — see blocker** | ✅ both on the shipped kernel |
| **code surface** | `operative_halo_deg()` + `HALO_DEG` | + `operative_halo_deg()`'s **signature** (it needs a latitude), `TileFrame.halo_deg`, `TileFrame.obs_bbox`, `__post_init__`, call sites `spatial_tiles.py:156` / `:294`, `phase14_stage1_run.py:479`, and `key()`. ⛔ **fork-d pin 4's "THIS function changes — nothing else" is FALSE here; amend it** | widen `core/parameters.py:17` `_LAT_HULL` from `[33, 43]` | none |

### 7.1 ⛔ R1b-3's HIDDEN BLOCKER — it cannot complete inside Stage 2

**216:** widening the hull is *"a producer decision with its own chain and touch, not
something a decision pack elects."* **Program spec §3.3:** *"Stage 2: **never opened** …
**Stage 2G acceptance touch: FIRST open**."*

⛔ **Stage 2 has no touch to spend, so R1b-3 cannot complete inside Stage 2.** Bundled with
2G's chain instead — the pin-255 bundling precedent — it **puts Stage 2's era-fits on a
different kernel than 2G ships.** That is the divergence R1b-1/2/4 all avoid: 1 and 2 move
both stages to the new kernel; 4 leaves both on the shipped one.

⚠ **And R1b-3 settles WHICH KERNEL FAMILY, not WHICH SCALE** — so even elected it leaves
R1b's anisotropy question open.

### 7.2 R1b-4 is a WAIT, which is an answer — but only with its exit named

**261:** *"A ruled WAIT is an answer with a reason and a named exit; an empty question is
not."* ⚖ **A deferral is Stage 2 exercising its ownership, not a re-homing** — it does not
revive 274(b), which **278(a)** corrected. ⭐ **And under (d) it is newly affordable:** R1b
no longer blocks n_eff's definition, so deferring costs the anisotropy fix and 2G's pole
input — **not** Stage 2's bars. Gate 1 already carries three ruled WAITs (219, 224, 250);
this would make the kernel's a second-generation one, and **pin 285's §7-19 watch applies
to the revision, not to a WAIT.**

---

## 8. What each ruling settles

**R1a — the NAMED SCALE for n_eff (a covariate choice).** Elect (d) or decline it; if
elected, confirm §5.1's rule and the scale it derives (**226.274 km**), and confirm §4's
**required clause** that n_eff's obs support is each tile's framed obs. Settling R1a
unblocks **pin 280** — n_eff defined, then every bar's number.

**R1b — the SOLVER kernel exit for high latitude.** R1b-1, R1b-2, R1b-3 or R1b-4. If it
moves the kernel or the halo it stays **upstream of the freeze** (279). If R1b-2, fork-d
pin 4's *"nothing else"* is amended and `key()`'s `halo=` token becomes a rule.

⚖ **Already ruled in this directive, carried for the record:** §6's binding of the two
constants, with its plan work and its negative control.

---

## 9. ⚖ DECISION CELLS — BOTH **EMPTY**

| | cell |
|---|---|
| **R1a** — the named scale for n_eff | ⚖ **EMPTY** |
| **R1b** — the solver kernel exit | ⚖ **EMPTY** |

Priced, owner to decide. ⛔ **`operative_halo_deg()` is not touched.**

**Until R1a carries a ruling:** n_eff is undefined, so no bar has a number (pin 280), the
census does not select (D4), and no era-fit runs. **Until R1b carries one:** the geometry
step is not recomputed (D6/D7) and the pavement is not frozen. ⭐ **Under (d) those are
two chains, not one** — which is the whole point of the split.
