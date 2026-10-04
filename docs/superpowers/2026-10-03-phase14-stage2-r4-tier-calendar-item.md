# R4 — THE TIER / CALENDAR ITEM (owner pin 282). ⚖ DECISION CELL EMPTY.

> **Prepared under ruling PART 64, pins 282 / 286-R4**, 2026-10-03, against `origin/main` at
> `cc9034e`. ⛔ **NOTHING RAN** (276d): the chain below is arithmetic over the witnessed
> probe node `phase14.stage1.tier2_probe_kuroshio_m100` and two ruled multipliers, plus one
> live read of this box's `/proc/meminfo`. `operative_halo_deg()` untouched; nothing opens.
>
> ⚖ **The decision cell at §4 is EMPTY** — *priced, owner to decide* (pin 235(e) form).
> 282's words: *"Present the owner a calendar decision: accept ~36 days of box time on the
> critical path, OR elect Tier 2 for throughput."*

## 1. The chain, DERIVED from the store (never recalled)

| step | value | derivation |
|---|---|---|
| one window, m = 100, kuroshio, **CONVERGED** (441/486 of a 500 cap) | **3.4399 h** | `measured_one_window.wall_h` |
| one era-fit = one tile-year = **9 windows** (`WindowPlan()`) | **30.96 h** | × 9 |
| D1's fit set = 12 era-fits | **371.5 h = 15.5 d** | × 12 |
| at **m = 137** (pin 53 reopened pin 31; pin 57: *"+0.5% RAM, ×1.37 wall"*) | **509.0 h = 21.2 d** | × 1.37 |
| under the box's measured **×1.70** throughput drift (pin 28) | ⭐ **865.2 h = 36.1 d** | × 1.70 |

⭐ **~36 days of box time**, serial. It reproduces 282's 30.96 / 371.5 / 509 / ~865 h exactly.
⚠ The probe node's own span caveat travels with it: *"31.0 h/tile is a central estimate with
a residual span of roughly ×1.3 either way"* (`residual_span_stated_pin_89d`).

## 2. Why Tier 1 cannot refuse this, and why it is a CALENDAR question

- `tier1_eligible(predicted_peak_mib, meminfo)` is **RAM-only**: `peak ≤ TIER1_HEADROOM_FRACTION
  × MemAvailable`, `TIER1_HEADROOM_FRACTION = 0.5` (`ladder.py:28, :215-233`). **Tier 1
  has no wall ceiling**, so §11.4's *"does not clear"* row is **unreachable** and §11.5 / §19.2-C11
  as framed are unrun (282). ⛔ **`tier1_eligible` is NOT given a wall term** — that would invent
  a ceiling nobody set.
- **RAM, by the rule:** peak **4364.5 MiB** → the 2× rule needs **MemAvailable ≥ 8729 MiB** at
  launch. The probe node recorded **11 248 MiB observed** at probe time (frame review §1a quotes
  it from the node) → clears by 22% **when the box is that free**.
- ⚠ **LIVE SNAPSHOT ON THIS BOX, 2026-10-03:** `MemTotal` **15 770 MiB**, `MemAvailable`
  **1 649 MiB**, swap 2 048 MiB; processes visible inside this container total ~360 MiB RSS, so
  **~13 GiB is held outside this container's view** — the owner's own work, or other
  containers. ⛔ **At this instant `tier1_eligible` would REFUSE an era-fit launch** (1 649 <
  8 729). This is a snapshot, not a verdict — but it makes the calendar point concrete: **the
  36 d is box time the era-fits must have to themselves**, and Tier 1's headroom on a shared box
  is whatever the owner leaves it.
- ⭐ **The RAM rule itself SERIALISES the era-fits on Tier 1:** at 11 248 MiB available and
  8 729 MiB required per fit, **⌊11 248 / 8 729⌋ = 1** era-fit may launch at a time. The 36 d
  is not a choice to run serially; it is what Tier 1's own rule permits on this box.

## 3. The two branches

| | **(A) ACCEPT ~36 d on the critical path** | **(B) ELECT Tier 2 for throughput** |
|---|---|---|
| what it costs | **~36 days of box wall**, serial, on Stage 2's critical path — *before* the census, the bars and Gate 2 can be evaluated. The ×1.3 residual span puts it at **28–47 d** | a **NEW spend row** — the only row, `tier2_probe`, caps wall at **6 h** (`ladder.py:83`), and **one era-fit exceeds it 5.16×**. `authorize()` WAITs on any class without a row: *"executor-set spend never happens"* (§11.5) |
| what it triggers | nothing new; `stage0:T18` stays blocked and untriggered | ⛔ **`stage0:T18`** — the cloud leg: CRN cross-host bit-exactness, cross-host single-thread delta, same-host multi-thread spread (US$25 / 8 vCPU / 64 GiB / 6 h; *"runs when owner supplies credentials"*). D10(e): the election triggers it, and §11.5's plan work makes `authorize()` **REFUSE** Tier-2 production while T18's witnessed node is absent |
| RAM | clears (§2) | clears; the 64 GiB node also lifts the serialisation of §2 |
| what the spec must then say | §11.4 rewritten as **calendar**: the serial chain, the ×1.3 span, and the RAM-rule serialisation stated; §11.5 / §19.2-C11 marked **not reached in Stage 2** | §11.4 rewritten around the **election**: the new row's ceiling (wall ≥ 31 h per fit, or per-window granularity at 3.44 h), its required-evidence field naming `stage0:T18`, and C11 **live** |
| interaction with R1b | none — the shipped kernel runs either way | none |
| interaction with the m question | m = 137 is **priced, not chosen** (53/57), settled in T17 before the era-fits; both branches carry the ×1.37 | same |

⚠ **What this item does NOT decide:** m (T17's), the kernel (288), the pavement (D6), or
whether any era-fit runs — nothing runs until the Stage-2 PLAN is approved (276d).

## 4. ⚖ DECISION CELL — **EMPTY**

Priced, owner to decide: **(A) accept ~36 d of serial box time**, or **(B) elect Tier 2** with
a new spend row and `stage0:T18` triggered. ⛔ Until it is ruled, §11.4 stands as written and
marked unrun.
