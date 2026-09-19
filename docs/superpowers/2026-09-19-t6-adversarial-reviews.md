# T6 dual adversarial review — verdicts and defects (2026-09-19)

**Status: BOTH REVIEWS COMPLETE. The T6 decision pack as first assembled was
OVERTURNED and has been rebuilt.** Owner pin 212(b) binds pin 39's full
two-reviewer form to decision packs — *"reasoning is where errors hide, and no
artifact check stands in for review there"* — and it earned itself immediately:
the reviews did not tidy the pack, they **inverted its central cell**.

Attack surfaces were authored by the requester before dispatch, per pin 39.
Reviewer 1 took geometry/frame correctness (A, B, D); reviewer 2 took ruling
compliance and decision hygiene (C, E, F). Neither was asked to approve.

| Reviewer | Surface | Verdict |
|---|---|---|
| 1 | **A** — the ±66 edge expression vs the real `obs_bbox()` | **CONFIRMED** (exact at the poleward end; latent defect at the max end) |
| 1 | **B** — "a km-space kernel leaves the meridional halo unchanged" | **OVERTURNED** — for options 1 *and* 2 |
| 1 | **D(i)** — option 3's anchor-identity citation | **UNDER-EVIDENCED** |
| 1 | **D(ii)** — option 2's "reduces EXACTLY" | **UNDER-EVIDENCED** — true in fact, pinned by no test |
| 2 | **C** — deciding on the axis 108(b) forbids | **UNDER-EVIDENCED** |
| 2 | **E** — the f-range table is decoration | **CONFIRMED** (state its bearing; do not remove) |
| 2 | **F** — AC + pins 99(a)/108/106, item by item | **OVERTURNED** — two AC clauses not met |
| 2 | the test file | **OVERTURNED** — one assertion provably vacuous |

---

## 1. The two findings that inverted the pack

Both were raised by review, then **confirmed by executing the shipped code**
rather than by reading it. Both are now test-pinned against that code.

### F-1 — options 2 and 3 are the SAME code path

`gaussian_kernel_from_params` (`src/sverdrup/validation/run.py:41`) dispatches
**on type**: a `LatitudeField` in *either* `variance` or `lx_mult` routes
`PaciorekGaussianDegrees`; only all-scalar resolution builds the stationary
kernel. Verified live — both varied-`lx_mult` and varied-`variance` providers
return `PaciorekGaussianDegrees`.

So the first draft priced "latitude-varying degree scales" at **LOW-MEDIUM** and
"Paciorek" at **MEDIUM-HIGH** — *two cost classes for one kernel*. That is the
precise shape of error that makes an option get chosen because its row looked
simpler, and the column test could not catch it because it asserted only that
cells were non-empty.

### F-2 — the shipped latitude vehicle is CONSTANT where the decision is

`LatitudeField.at` clamps latitude to the anchor-box hull **[33, 43]** before
evaluating (`src/sverdrup/core/parameters.py:17,53` — constant continuation
off-box, the PolyCalibration convention). Measured over each diverse tile's
core with `exp-linear-mult`:

| tile | core | m(lat) across the core | varies? |
|---|---|---|---|
| kuroshio | 28…43 | 0.3679 → 2.7183 | yes (overlaps the hull) |
| **southern** | **−62…−47** | **0.3679 everywhere** | **NO** |
| equatorial | −4…+11 | 0.3679 everywhere | NO |
| quiet_gyre | −30…−15 | 0.3679 everywhere | NO |

**The vehicle for latitude variation cannot vary at the latitudes a
high-latitude kernel decision is about.** The first draft's ±66 BREACH row —
the single most consequential cell in the pack — priced a `1/cos φ` multiplier
that the shipped field **cannot express**, using a substitution that appeared
nowhere in its own text. Worse, as reviewer 2 put it: the pack ruled the
coordinate aspect out as evidence in §T6.2 and then made it the sole driver of
the breach twelve lines later.

**Corrected consequence:** *no option, as the code stands, breaches ±66.* What
costs margin is the scalar halo (F-3), not the nonstationary option.

### F-3 — the halo is a single scalar (surface B, OVERTURNED)

`TileFrame.halo_deg: float`; `obs_bbox` applies the same value to lon and lat
(`spatial_tiles.py:62,101-104`); `operative_halo_deg() -> float`. There is no
per-axis halo in the tree. So the draft's claim that a km-space kernel leaves
the meridional halo alone — and option 2's "hold the meridional scale fixed" —
were **not expressible**. `PaciorekGaussianDegrees` compounds it: one shared
multiplier scales `lx` and `ly` together, and a field-valued base is refused
outright, so there is no degree-space anisotropy to hold fixed either.

Honest arithmetic: a km-space scale has a degree footprint of 1.0° meridional ×
**1.7179°** zonal at the SO φ0, the scalar halo must cover the wider axis, and
the ±66 margin falls from **1.0000° to 0.2821°**.

---

## 2. Surface-by-surface

**A — CONFIRMED, with a latent defect recorded.** `solve_bbox.lat_min − halo`
**is** `obs_bbox().lat_min` identically, because `np.arange`'s first element is
the start value bit-exactly; the documented overshoot can only appear at the
**max** end. For a southern-hemisphere tile the poleward end is the min end, so
the ±66 column is computed off the right quantity — and a test now proves that
rather than assuming it.
⚠ **But the max end is wrong by one grid cell, and it is in the POSTED Gate-1
pack:** kuroshio's real obs north edge is **+46.2** (margin 19.8°), not the
+46.0 / 20.0° recorded at §1.11. Not material at 20° of margin; it is the same
class of error pin 210 corrected, on the other side. **Reported, not
retro-edited — 209(c) reserves that to the owner.**

**C — UNDER-EVIDENCED.** Pin 108 forbids deciding on **directional sampling**,
which the grid aspect and the ring spectrum cannot speak to; a coordinate cos-φ
argument is a different quantity. The draft asserted the options were separable
without it and then listed the cosine-driven halo column among its own grounds.
The claim was rescuable but unshown. **Fixed by showing it:** option 1 parts
from the other two on metric and anchor identity; options 2 and 3 do not part
from each other at all (F-1). Strike the cosine column and the separation
stands — so no WAIT is owed under 108(b), and the pack now says why.
Two sentences that ran the cosine in the *evidence* direction — a 31.2%
"the tile is more distorted than the box" comparative, and a breach remark
sitting in option 3's **cost** cell — are removed.

**E — CONFIRMED.** No `|f|` value enters any option row, any halo consequence
or the ±66 arithmetic; the threshold's 66 is a **latitude**, not `|f|` at it.
The table is AC-required, so the fix is the one the surface named: the pack now
**states what it bears on** — the spec's scale-setting context, and nothing in
the option separation.

**F — OVERTURNED, four clauses.** (F-1) `-64.0` was **typed** into option 3's
halo cell while the ±66 table derived the same edge from the frame; moving the
frame produced a self-contradicting document. (F-2) "halo ≤ 2.0 only" was a
typed string beside a computed threshold. (F-3) the evidence block
`phase14.stage1.kernel_pack` did not exist and `--record` was untested.
(F-4) `rests_on_directional_sampling` was a **dead field** — nothing read it,
the render hardcoded "no", and flipping it changed nothing. All four fixed; all
four now test-pinned.

**D — UNDER-EVIDENCED, both parts.** The Paciorek citation proves **kernel-matrix**
identity at sampled pairs (it does hold bit-exactly), **not** that the anchor
*solve* stays bit-identical — which is what check 1 compares. The condition is
also narrower than "constant scales": bit-identity holds at **L0 = 1 and
variance = 1**; off those values the forms differ at ~1e-16, enough to move a
sha. Option 2 has **no** such test at all; its claim is verified-in-session and
pinned by nothing. Both rows now say exactly that.

---

## 3. The test file, and the instance it earned

⛔ **A provably vacuous assertion, in the test file enforcing pin 42's own
discipline.** `assert "4.0" not in text.split("## ")[0]` — `render()` begins
with `"## T6 …"`, so that expression is the **empty string** and the assertion
**could not fail under any input**. The clause it claimed to cover (the
collapsed branch's `halo > 4.0` never reaching a reader) was **unrun**.

Both reviewers found it independently. It was written in the same session that
catalogued §7 discipline 11 instance **(i9)** — an attestation that could not
fail — which is the strongest available argument for 212(b) binding review to
decision packs.

Also fixed: the softening guard banned "weakly supported" but not the bare word
pin 108(a) actually names; the column test asserted truthiness (a single space
passed); the no-advocacy guard was a four-word blacklist that the draft's own
advocacy sentence walked through.

**Tests added, each pinned against live code rather than a fixture:** the
dispatch fact (F-1), the hull clamp (F-2), the flag→render wiring (F-4), the
edge expression against a real `TileFrame.obs_bbox()` (A), and `--record`.
17 tests, all green.

---

## 4. What the reviews did NOT overturn

The arithmetic. Every f and cos-φ figure reproduces by hand — `|f|` 8.998975e-05
at the box φ0, 1.194668e-04 at 55°S, ratio 1.32756; `1 − cos43/cos33` = 12.796%;
`1/cos 62` = 2.1301; `1/cos 66` = 2.4586; `KM_PER_DEG` matches `_DEG2KM` exactly.
The 1/cos(φ0) identity behind pin 108 holds to 1.16e-13. The decision cell was
empty and stayed empty. The refusal without the SO evidence row worked. Southern
is genuinely the binding tile — under the widest candidate halo kuroshio still
has 18.7° of margin.

**Outstanding for the owner:** the Gate-1 pack's +46.0 (surface A.2), and
whether F-2's hull — a shipped, signed component — is a Stage-2 producer
question or a Gate-1 one.
