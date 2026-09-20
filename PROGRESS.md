# Sverdrup — Progress notebook

> # ⬛ CURRENT STATE — 2026-09-19. THIS IS THE ONLY BLOCK DESCRIBING NOW.
>
> T8 OPEN (OSSE pricing). Deliverable is a STANDALONE doc + witnessed node (pin 232) — the
> posted Gate-1 pack is NOT retro-edited (209c). N_epoch-classes = 15, DERIVED from the sealed
> epoch table, all distinct so no deduplication exists (pin 234). Truth-field cost is part of
> the price, not an omission (234e). Pin 212(b)'s review binds with surfaces at 235. Decision
> cell stays EMPTY — the OSSE run decision is the owner's. Next stop: the price table.
>
> T7 CLOSED as a ruled WAIT (pins 224/230). The refusal is IN THE EVIDENCE STORE at
> phase14.stage1.revisit.<tile>, witnessed — four rows carrying the sizing, the per-lane RUN
> verdicts, the refused aggregate (68 solves / 69.9 days; 252 / 259.1 on the screening path),
> and the anchors-only option at 12.3 days with its weaker-claim limit. Gate 1 carries TWO
> ruled WAITs (kernel 219, revisit 224) and does not close. NEXT: T8 (OSSE pricing) on the
> owner's word — it opens on nothing else.
>
> T6 POSTED AND RULED. Kernel decision = WAIT, cell EMPTY (pin 219). No option electable as
> the code stands: options 2/3 inert at the SO tile (hull-clamped latitude field, pin 216);
> option 1 breaches ±66 at the tile's poleward reach (−66.13 at the core edge). Two named
> resolutions, both Stage 2: a smaller km scale, or a latitude-aware halo.
> operative_halo_deg() UNTOUCHED.
>
> **T7's config pins and per-lane tier guard LANDED; no lane command, no legs (224b/224d).**
> `revisit_tier_verdict` stays exactly as built — it passes every solve and has no opinion
> on the total, which is pin 222(c) demonstrated rather than asserted. Sweep row 8 is FOLDED
> (pin 227): the tracker carried the dead "no new ceilings exist" premise verbatim while the
> ruling was only a header note. Pins 221–229 landed as ruling PART 52, with the sizing
> table beside 224 as its basis.
>
> ⛔ **TASK 23 IS BEHIND TASK 24** (pin 221c) — a userGate wall for the election ruling,
> which *"does not yet exist"*. Fifth instance of that trap; it is an EDGE IN THE GRAPH with
> a machine-readable `userGate` fence, not prose. ⚠ But the blocker hook guards only
> `in_progress` and reads the TRANSCRIPT, not `.tasks.json`, so the edge is **declarative,
> not enforced** (pins 221d/229) — ratified as a plugin change, outside this repo.
>
> ✅ **SWEEP ROWS 7-9 ARE NOW ALL FOLDED** (pins 227/233). Row 9 folded at task 8 with its
> Files/Verify/verifyCommand retargeted off the posted pack. ⚠ **Row 7 was NOT folded when
> 233 was written** — task 6 still carried *'RULED BUT UNFOLDED ... inside a task that has
> not opened'* **after T6 had opened, delivered and closed**. The ruling was never lost (pin
> 108 is in `phase14_kernel_pack.py` and the witnessed node); **only the header was stale**,
> the same laxer-copy defect. Header corrected; **T6's status and ruling untouched**.
>
> **Everything below this block is TRAIL.** Owner pin 154: rewrite what went stale rather
> than layering over it.
>
> ## ⭐ T5 IS COMPLETE — ALL FOUR LEGS RECORDED
>
> | tile | λx | µ | coverage_1σ | χ² | leg wall |
> |---|---|---|---|---|---|
> | kuroshio | **232.53 km** | +0.285954 | 0.009778 | 416.678 | 19.67 h |
> | southern | **141.95 km** | −0.617629 | 0.002581 | 1637.484 | 27.48 h |
> | equatorial | **RECORDED ABSENT** | +0.765790 | 0.032632 | 40.311 | 25.54 h |
> | quiet_gyre | **RECORDED ABSENT** | +0.847933 | 0.166670 | 11.638 | 26.03 h |
>
> **⭐ THIS IS A TRANSFER FINDING, NOT FOUR READINGS OF WHICH TWO FAILED** (pin 186a).
> State it that way in the Gate-1 pack and in C1→2: **box-scale behaviour TRANSFERS to
> strong-signal regimes and does NOT transfer to weak-signal ones, at this configuration.**
>
> **⭐⭐ AND STATE IT IN THREE CLASSES, NOT TWO (pin 196b/196e).** *"Resolves versus does
> not" is TOO COARSE a summary of what Stage 1 measured* — the pack and C1→2 both carry:
>
> | class | tiles | what the spectrum does | verdict |
> |---|---|---|---|
> | **well-matched** | kuroshio | matched across the band | resolves |
> | **UNDER-powered** | southern | `study/ref` **0.084** at 500–1000 km, `diff/ref` **0.988** — correctly PHASED, real skill at 150–300 km | resolves |
> | **OVER-powered** | equatorial · quiet_gyre | over-powered at long scales, **phase collapsing** | absences recorded |
>
> **Southern is under-powered exactly where the two absences are over-powered.** That is
> **the sharpest structural contrast the stage produced**, and it **argues against one
> mechanism sliding along a single axis**. ⚖ **It is evidence about the MECHANISM, not a
> caveat on a row.** Stage 2G assembles tiles across all three regimes, which is why the
> coarse summary will not do.
>
> | | failing tiles | resolving tiles |
> |---|---|---|
> | *f* vs kuroshio | 0.11× · 0.66× | 1.00× · 1.40× |
> | track variance vs kuroshio | 0.034× · 0.021× | 1.000× · 1.879× |
>
> **It sorts on signal strength, INDEPENDENTLY OF LATITUDE** — quiet gyre has healthy *f*
> (0.66×) and failed; southern has the strongest *f* and resolved. **The spec did not
> anticipate this.** The reading stands because **180(b) pre-registered it before the run**
> (186c) — that is what distinguishes it from a fitted story.
>
> **⛔ THE DEFECT BRANCH IS CLOSED ON EVIDENCE, NOT EXHAUSTION** (185), for four reasons,
> recorded so it is not silently reopened: the pattern is **universal in kind and orderly in
> degree**; **coefficients are ordinary at every rung**; **PCG converged `capped=False` on
> all four**; and **the split sorts on signal strength across a 6.3× spread in *f***.
> *Misalignment, sign or reference errors do not sort by regime.*
>
> **MECHANISM OPEN AND FIREWALLED** (186b). Long-scale dominance + weak signal is the
> surviving account and is **NOT established**: both predictors **weakened** with the fourth
> tile (absolute variance −0.464 → −0.254, |f| −0.322 → −0.121, n=28), so **the effect is at
> TILE level, not band level** — which is where Stage 2 should look.
>
> **⛔ THE GEOSTROPHIC ACCOUNT IS REFUTED, and the record says so** (187a). An inference was
> named at 160(c) — that equatorial's failure bears on fork-b pin 1's wave-increment
> business case — and deliberately not written. **Quiet gyre kills it: healthy *f*, same
> failure.** Considered, firewalled, now **REFUTED**. *Had the firewall not held, Stage 1
> would be carrying a wrong conclusion about why the increment is needed.*
>
> ## ✅ PIN NUMBERING — RESOLVED. THE SERIES IS LANDED.
>
> - **The FORKED advisory series 184–189 is AUTHORITATIVE** — `origin/main` carries
>   **`5ce66e3` citing pin 188(a)**, so the numbering could not be rewritten.
> - **✅ PART 44 (pins 184–189) and PART 45 (pins 190–191) are LANDED VERBATIM.** The
>   **pin-41 hole is CLOSED**: 188(a)'s work had been committed without its ruling text.
> - A PART 44 drafted in-session for pins 184–186 was **VOID and was discarded** before the
>   authoritative one landed.
> - ⛔ **THREE ITEMS OF 188 ARE DISCHARGED OR STALE — do not re-execute:** **188(a) DONE**
>   at `5ce66e3`; **188(c) STALE** (quiet gyre IS mirrored — re-recording its row recreates
>   the drift the recovery cleared); **188(d) DONE** by the same commit.
> - ✅ **190(a)/(b) ARE IMPLEMENTED AND RATIFIED (pin 194, 2026-09-10).** The
>   resume-re-score refusal and its row-reading test landed at `7fa106d` — see *The
>   resume-rescore hazard is PREVENTED* below. **191's protocol half is landed too**:
>   CLAUDE.md step **0b** now makes `git log` / `git ls-remote` a **pre-write** check, not
>   only a session-start one.
> - ⛔ **THERE IS NO E-17 — `source` IS PART OF PIN 190** (194c). The owner renumbered it
>   into the series under pin 40. Cite it as **190(a)**; it carries no unratified-executor
>   status. **A restored cost with no stated origin is unauditable**: 190 stops a row
>   restating a leg's cost *silently*, `source` stops it restating one *anonymously*.
> - ✅ **PINS 194–195 LANDED VERBATIM as ruling doc PART 46; PIN 196 as PART 47; PIN 197 as
>   PART 48; PINS 199–205 as PART 49 PINS 206–208 fold into PART 49's
>   successor; **PINS 209–214 as PART 50.**
>
> ## ✅ 202(b) DISPOSED (pin 206, `2530bb2`) — forward-pointer node `equatorial_sampler_log_scope`; row untouched; re-scores now log to their own directory. THE BLOCK BELOW IS THE FINDING AS ESTABLISHED (2026-09-16)
>
> **Established exactly, not inferred.** The equatorial re-score (2026-09-10T06:05Z) wrote
> into **the leg's own log files**, `logs/leg_equatorial/{leg,vmhwm}.log`. The node
> `headroom_minima_recovered` hashed them **before** that; the equatorial ROW hashed them
> **after**. Proof: the node's shas equal the shas of today's files **truncated to 418 of 427
> and 1,533 of 1,535 lines**. **The node describes the LEG; the row describes leg +
> re-score.**
>
> | | leg only (node) | row `headroom.sampler_log` |
> |---|---|---|
> | samples | **1,533** | 1,535 |
> | min MemAvailable | 3,601 | 3,601 |
> | **max** MemAvailable | **9,953** | **10,379** — a re-score sample |
> | sha256 | `dd036ba9…` | `255ad285…` |
>
> **Minima and the whole heartbeat block are unaffected** (306 beats, 3,828 / 9,051 either
> way), so nothing the pack would cite about headroom *minima* changes. But the row's
> `sampler_log` sha, count and max **include the re-score**. **This is pin 190's hazard by a
> SECOND ROUTE — a shared log file — which 190's code fix does not cover**: a re-score still
> appends to the leg's logs. **The row is witnessed, so it is not edited.** Proposed remedy,
> **awaiting the owner**: a forward-pointer node (pin 64, as at 200) stating the leg-only
> figures and the truncation proof; and, separately, a re-score writing to its **own** log
> directory so the leg's logs close when the leg does.
>
> ## ✅ 199–205, AS DONE
>
> - **199(b)** — kuroshio's 7,389 MiB is labelled **PRE-133** wherever it appears beside the
>   post-fix peaks. Owner's arithmetic: **4,259 + 8 × 391.2 = 7,389**, the retention slope
>   reproducing the peak exactly.
> - **199(c)/204 CLOSED** — row `peak_rss_mib` equals the leg log's max heartbeat `peak_rss`
>   on all four legs; `TIER2_MEASURED_PEAK_MIB` is exactly southern's row value; the gate is
>   **1.986×** the worst post-fix peak. ⭐ **The first single-instrument measurement this stage
>   ACCEPTED as sufficient, and the grounds are the record:** `ru_maxrss` and `VmHWM` are
>   **one kernel high-water mark through two interfaces** — agreement is
>   **self-consistency, NOT corroboration** — and corroboration is unnecessary because a
>   high-water mark is not derived, is **monotone non-decreasing**, and so **errs
>   conservatively for a launch threshold**.
> - **200** (`37b2d95`), **201/205** (`d00f4e6`) — see ruling doc PART 49. **All eight
>   ruling-quoted band figures reproduce exactly.**
> - **202(a)** done inside 200. **202(c)/(d)/(e)** folded into this block and the assembled
>   view.
> - Also landed, as plain owner instructions: the offline guard now covers the **transfer**
>   (`f982b88`); the owner's PDF dependencies are in, **docling in its own `pdf`
>   environment** (`f3c7aa0`). **The default environment's C libraries moved** (libcurl
>   8.20 → 8.22, libtiff 4.7.1 → 4.7.2, and others) — the gate suite was re-run on it:
>   **1626 passed**.
>
> ## ⚠ THE OWNER MAY WORK THIS REPO CONCURRENTLY
>
> `5ce66e3` was authored by the owner mid-session and was not visible to a session that ran
> `resume_checks.sh` at hour zero. **`resume_checks.sh` at session start cannot see a commit
> that lands at hour six.** Re-check `git log` / `git ls-remote` **before writing to shared
> state after any long gap**, not only at session start.
>
> ## ⭐ HEADROOM: ONE RECORD, AND IT IS NOT THE ROWS
>
> **`phase14.stage1.headroom_minima_recovered` (`5ce66e3`) is the SINGLE headroom record** —
> a separate **witnessed** node with the tile rows left untouched. That shape is correct and
> required: the rows are witnessed, so they are never edited. A duplicate node and row-level
> `headroom` keys written in-session were **discarded**; they were the store-vs-mirror drift.
> ⚠ **The 151(b) drop is still LIVE for every FUTURE leg** — `record_tile_leg` accepted
> `headroom` and never passed it on. **This recovery commit fixes that** and test-pins it by
> reading the row back OUT of the store.
>
> ## Where the stage is
>
> | | state |
> |---|---|
> | **Leg 1 — kuroshio** | ✅ **DONE.** 9/9 windows CONVERGED, `capped=False`, solve 19.57 h, leg 19.67 h. Recorded at `phase14.stage1.tiles.kuroshio` and **witnessed in the mirror**. µ 0.285954 · σ 0.218613 · λx 232.53 km · **coverage_1σ 0.009778** · peak RSS 7,389 MiB **PRE-133 — not comparable to the post-fix basis** (pin 199) · χ² 416.678 (the s\*/χ² identity, non-gating) · raw-σ 0.038187 and s\* 416.678 both `REFERENCE-ONLY, NOT CALIBRATED` |
> | **Leg 2 — southern** | ✅ **DONE 2026-09-04.** 9/9 windows CONVERGED, `capped=False`, solve 27.37 h, leg 27.48 h — inside the 40 h ceiling, no trip. Recorded at `phase14.stage1.tiles.southern` and **witnessed in the mirror**. µ −0.617629 · σ 0.137723 · λx 141.95 km · **coverage_1σ 0.0025807** · χ² 1637.484 (the s\*/χ² identity, non-gating) · raw-σ 0.0349657 and s\* 1637.484 both `REFERENCE-ONLY, NOT CALIBRATED`. **It CLOSED the 3→9 projection — see below** |
> | **Leg 3 — equatorial** | ✅ **DONE 2026-09-10.** 9/9 CONVERGED, `capped=False`, solve 25.42 h, leg 25.54 h. **λx RECORDED ABSENT** (fork F, pins 160a/161) — coherence max **0.003**, `psd_diff/psd_ref` **1.00047**, 12.77–996.34 km. µ +0.765790 · σ 0.059423 · **coverage_1σ 0.032632** · χ² 40.311 · n 100,299. The original leg DIED in scoring at 25.5 h; 161 landed, and the re-score from the store recorded it in **21 s** |
> | **Leg 4 — quiet_gyre** | ✅ **DONE 2026-09-08.** 9/9 CONVERGED, `capped=False`, solve 25.93 h, leg 26.03 h. **λx RECORDED ABSENT** — coherence max **0.0026**, `psd_diff/psd_ref` **1.00054**. µ +0.847933 · σ 0.062576 · **coverage_1σ 0.166670** · χ² 11.638 · n 103,786. **It was the confound-breaking experiment** (pin 180) and its reading was **pre-registered before launch** at `b7fe656` |
> | **⭐ THE T5 RESULT** | **A TRANSFER FINDING IN THREE CLASSES** (pins 186a, 196b) — not four readings of which two failed, and not a two-way resolves/does-not split. The frozen config **resolves λx in the two STRONG-signal regimes and not in the two WEAK ones** — and ***f* is NOT the discriminator**: quiet gyre has healthy *f* (0.66× kuroshio) and failed; southern has the strongest *f* and resolved. **The spec did not anticipate this.** Mechanism **FIREWALLED** — long-scale dominance + weak signal is the leading candidate and is **NOT established** |
> | **T6 / T7 / T8 → T9** | Behind T5. **T12 is CLOSED**; **task 23** (post-gate C-11 producer) is `blockedBy [9]` |
> | **T6 / T7 / T8 → T9** | Behind T5. **T12 is CLOSED**; **task 23** (post-gate C-11 producer) is `blockedBy [9]` |
>
> ## What holds the legs
>
> - **The launch gate is `MemAvailable ≥ 9,902.33 MiB`** = 2 × the **measured 4,951.16 MiB**
>   (owner pin 155, leg 2's DIRECT nine-window measurement — no projection). Both prior
>   bases are **preserved** as a chain at `TIER2_MEASURED_PEAK_SUPERSEDED`: 4,365 → 4,573 →
>   4,951. **Neither 8,730 nor 9,146 admits** — 1.909× and 1.847× are the "close enough"
>   that produced the 1.18× and survived two rounds.
> - **⛔ THE GATE IS LAUNCH-TIME ONLY AND DOES NOT PROTECT THE LEG** (owner pin 156). The
>   box **shed 9,389 MiB during leg 2** against a 4,951 MiB leg peak; no launch threshold
>   covers that. **What protects the leg is the in-run watchdog** — below a floor of
>   **2,048 MiB**, or on the leg's own `VmSwap` reaching 64 MiB with headroom under 4,096,
>   the leg **STOPS CLEANLY at the next window boundary**. The boundary is where it is
>   clean: `on_window` fires *after* `_save_window`, so the halt costs nothing already
>   solved and pin 121's store carries the rest. A halt is **not a completion and not a
>   crash** — `kind: HEADROOM_HALT`, exit code **75**, and **no evidence row**.
>   `scripts/stage1_leg_launcher.sh` parks and relaunches on 75, and **stops and reports on
>   any other non-zero** rather than relaunching a crash blind.
> - **The per-leg wall ceiling is 40 h.** A leg over it **STOPS and reports**.
>   ⚠ **The check is POST-HOC and cannot lose work.** `tier2_wall_ceiling` is
>   evaluated at `phase14_stage1_run.py:5701`, *after* the leg has solved and been
>   recorded; it never interrupts the process. Its whole effect is the
>   `WALL CEILING EXCEEDED` line plus **the NEXT leg not launching until the owner
>   re-prices**. Read as a mid-run kill it invites a false trade — this session
>   reported "a ceiling trip costs the window in flight" and that was wrong. What
>   costs the window in flight is an OOM or a crash (pin 132), not the ceiling.
>   Owner ruling 2026-09-03: a proposed raise to 50 h was **SKIPPED once the
>   mechanism was established** — it would buy nothing, and `TIER2_MAX_LEG_WALL_H`
>   carries test pins (`test_phase14_stage1_run.py:4195-4197`) plus a declared
>   projection block (`TIER2_CEILING_BASIS_SPAN`) under pin 139.
> - **An exclusion lock is held for the whole leg** (pin 151a): a second Stage-1 solve is
>   refused by name. A dead holder's lock is taken over and **the takeover is recorded**.
> - **Headroom is sampled DURING the run** (151b) at **60 s, the external sampler's
>   cadence** (156c), and — **since 2026-09-10 and not before** — `headroom` reaches the
>   row. ⚠ **This block previously claimed it already did. That was FALSE for every leg**:
>   `record_tile_leg` accepted the record, documented it as satisfying 151(b), and never
>   passed it to `build_evidence_row`, so **no row carried it until the recovery commit closed the
>   drop**. Test-pinned now by reading the row back OUT of the store — the only angle that
>   could catch it. ⚠ **Corrected 2026-09-16 (pin 202d): this line used to name a node
>   `phase14.stage1.headroom_backfill`. NO SUCH NODE EXISTS.** The minima for the legs
>   whose rows lack them live in **`phase14.stage1.headroom_minima_recovered`** (mirrored,
>   pin 188a), qualified by **`headroom_leg1_floor_unrecoverable`** (mirrored and indexed at
>   pin 200: kuroshio's 3,660 MiB is an **upper bound**, not a measurement). **Kuroshio's,
>   southern's and quiet gyre's ROWS CARRY NO `headroom` KEY AT ALL** — expected, because
>   186(a) fixed the drop forward and the witnessed rows are **not edited** (pin 60); the
>   separate node carries them. **Only equatorial's row has one** (BACKFILLED — and see
>   202(b) below for what its `sampler_log` block contains). A **resumed** leg carries its halt inside
>   `headroom` (156a-ii) — which the same drop would have hidden, so it is now test-pinned
>   too. The row's top-level key set is pinned exactly; `headroom` is optional, so
>   nothing was added to the schema (156d).
> - **⭐ THE RESUME-RESCORE HAZARD IS PREVENTED (pin 190a/b, 2026-09-10) — it was
>   RECORDED-not-prevented until then.** Found on equatorial: the re-score took 57 s and
>   would have recorded **57.3 s / 3,804 MiB** for a leg that cost **91,945 s / 4,817 MiB**
>   — a ~1,600× understatement on the two fields E-16 and T7/T8 price legs from. That row
>   was restored by hand, with the replaced values kept at `headroom.restored_run_facts`.
>   **Now the code refuses instead of recording.** `build_evidence_row` takes
>   `resumed_rescore` + `original_run_facts` and raises **`ResumeRescoreRefusal`** unless
>   the ORIGINAL run's `wall_s`, `peak_rss_mib`, `headroom` (explicitly `None` if never
>   recorded) **and** `source` are supplied — `source` **required** under 194(a):
>   **provenance travels with a restored fact, or the fact is not restored, only asserted.**
>   Supplied facts **without** a resume are refused too (ratified 194d) — the block
>   restores, it is **not a general override**, and that is what keeps it from becoming the
>   hand-edit path it replaces. The refusal is
>   **satisfiable at a named path**: `<STAGE1_DIR>/<tile>_original_run_facts.json`, read by
>   `load_original_run_facts` and echoed at the top of the resume, not only at the refusal
>   57 s later. Which run each field describes is recorded **inside `headroom`**
>   (`headroom.resume_rescore`) — the row's top-level key set is pinned exactly, so no
>   schema edit (same bounded shape as 156d), and it is emitted **even when the original
>   headroom is unavailable**, which is when the reader most needs telling. **Test-pinned
>   by READING THE ROW out of the store** (190b), the angle that found it.
> - **Order: kuroshio → southern → equatorial → quiet_gyre**, commit per tile.
>
> ## What is measured and settled
>
> - **Pin 133 is RESOLVED.** `merged_members` retained every completed window after
>   persisting it (377.5 MiB/window at production shape). Fixed by a store-backed reader
>   plus a streamed leg-store write; acceptance was 121's — leg 1's store reassembled
>   **bit-identically, all 31 members**.
> - **147(a), m=25 × 4 windows: SLOPE FLAT** — boundary deltas +0/+97/+0, mean 32.3 against
>   93.4 MiB/window if broken.
> - **147(b), m=100 × 3 windows: PEAK 4,573 MiB, FLAT** — deltas +0/+147, against 373.8
>   MiB/window if broken; the one step sits **inside** window 3's solve, not at a boundary.
> - **⭐ THE 3→9 PROJECTION IS CLOSED (pin 150c, leg 2, 2026-09-04).** Nine windows at
>   production scale, measured directly, no extrapolation left on the window-count axis.
>   **Boundary peaks: 4,575 then 4,951 ×8** — deltas **+376 then +0 ×7**, mean increment
>   **47.0 MiB/window** against pin 133's 377.5 retention signature. The one +376 landed
>   *inside* window 2's solve, the same shape 147(b) saw at +147. **Nine-window peak
>   4,951.16 MiB**, against the three-window 4,573 → the extrapolation was good to
>   **1.083×**, and against the declaration's "consistent with ~4,809" it is 142 MiB high.
>   ⚖ **What this does to the gate is the OWNER's, not the executor's:** 9,146 / 4,951 =
>   **1.847×, not the 2× the gate names** — the same shape as the 1.18× pin 150 corrected,
>   one step smaller and in the safe direction. A true 2× on the measured peak is
>   **9,902 MiB**. That arithmetic is the E-16 §4 input; **it is recorded here, NOT adopted.**
> - **Wall, leg 2:** per-window 3.193 / 3.268 / 3.026 / 2.744 / 3.203 / 3.793 / 2.903 /
>   2.846 / 2.404 h, mean 3.042, **slope −0.060 h per window index** — decreasing, not
>   growing. 1.40× leg 1's 19.67 h. PCG worst 626 iterations (`w+00207` member-batch),
>   over the 500 default a smaller cap would impose and under the 1200 — pin 143's third
>   subject exercised for real a second time.
> - **⚠ The leg-2 launch gate measured a box that did not stay measured.** Launch cleared
>   at 10,771 MiB; the run bottomed at **1,382 MiB** (tracker) / 1,526 (1-min sampler),
>   far below leg 1's 3,660. Swap hit **zero**, the leg swapped ~100 MiB, and **both the
>   in-process heartbeat and the external sampler stalled ~10 min together** around
>   2026-09-04T07:29Z — a whole-box stall, from an unrelated tenant growing ~3 GiB.
>   It survived only because the owner freed memory twice, the second time ~35 min before
>   window 8's checkpoint. **A launch-time gate does not hold the box for the leg.**
> - **⭐ WALL IS SETTLED (owner pin 157a).** 19.67 h and 27.48 h against the probe's 31.0 h
>   prediction, mean 23.58 h, both well inside the 40 h ceiling. The extrapolation that made
>   per-leg re-assessment necessary is **validated twice over**, which is why legs 3 and 4
>   run back to back with no re-assessment between them. Southern took **1.40×** kuroshio;
>   the ceiling stands for the case where a remaining tile is worse (157c).
> - **Ratified (pin 158):** leg 2 as recorded, the completion procedure run in full, and
>   PROGRESS rewritten rather than layered. **The finding of the round was that the gate
>   measured a box that did not stay measured** — surfaced rather than reported as a clean
>   leg. Pin 26(b)'s raised PCG cap earned itself again at **626 iterations** on
>   `w+00207`'s member batch, over the 500 a smaller cap would have imposed.
> - **Declarations:** 12 projection blocks / 27 axes and 24 reachability blocks recorded by
>   **forward-pointer amendment — no witnessed node edited**. `seal_run check` REFUSES an
>   undeclared projection (pin 139) or verdict block (pin 152); the **9 uncited prior-phase
>   gates print every run** as recorded-as-found and are not fatal.
>
> ## ⛔⛔ LEG 3 (equatorial) CRASHED IN SCORING — OWNER RULING OWED (2026-09-06)
>
> **All nine windows SOLVED and persisted; no solve work is lost.** The leg died AFTER the
> solve, in `score_tile`, at 25.5 h (91,945 s):
> `UnresolvedScaleError: map resolves no scale; λx undefined (no 0.5 coherence crossing)`
> (`pertile_scoring.py:151`). Lock released. **The launcher correctly REFUSED to relaunch**
> — `rc=1` is a crash, not a halt (pin 156b), on its first real firing.
>
> **This is a DEFINED SIGNAL, not a fault.** `_coherence_guard` raises it deliberately in
> place of a cryptic vendored `interp1d` out-of-range error. `lane_compare` catches it and
> records NaN; `score_tile` does not, so a T5 leg dies on it.
>
> **Measured on the persisted maps (read-only, no re-solve):**
>
> | tile | lat span | trk std | map std | bias | res std | res/trk | **coh max** | λx |
> |---|---|---|---|---|---|---|---|---|
> | kuroshio | +28.3..+42.7 | 0.4780 | 0.4130 | −0.619 | 0.2315 | 0.48 | **0.894** | resolved 232.53 |
> | southern | −61.7..−47.3 | 0.6490 | 0.0875 | +0.990 | 0.6484 | 1.00 | **0.659** | resolved 141.95 |
> | equatorial | −3.7..+10.7 | 0.0889 | 0.0958 | −0.201 | 0.1005 | 1.13 | **0.003** | **UNRESOLVED** |
>
> Equatorial: median `psd_diff/psd_ref` = **1.0005** across 12.8–996.3 km — the residual PSD
> equals the reference at essentially every wavelength. Pointwise corr 0.409 and µ +0.7658,
> σ 0.0594, so LARGE-scale structure is captured and MESOSCALE skill is absent.
>
> ⚖ **What the comparison does NOT support:** "residual ≈ signal" is not the discriminator —
> **southern has res/trk = 1.00 and still resolved.** The discriminator is coherence max:
> 0.894 / 0.659 / **0.003**. A hypothesis CONSISTENT with the numbers, and **NOT
> established**: the core straddles the equator (−4..+11) and MIOST is a geostrophic-kernel
> method, which degenerates as f → 0. The −0.201 m bias does NOT explain it (a constant
> offset lives at zero wavenumber and is removed by per-segment detrending).
>
> ⚠ **A second thing the table surfaced, on an ALREADY-RECORDED leg:** southern's map std is
> **0.0875 against a track std of 0.649** — 7.4× smaller — with a +0.990 m bias, where
> kuroshio's map std tracks its own (0.413 vs 0.478). That row is committed.
> ✅ **DISPOSED at owner pin 196 (2026-09-11): it is the THIRD FAILURE CLASS, not a defect
> and not a caveat** — under-powered at long scales, correctly phased, verdict unaffected.
> The row stands **UNAMENDED**. See the three-class table at the top.
>
> **The equatorial row CANNOT be built as-is** — `build_scores_block` requires a λx.
> Options, none taken: (1) record the ABSENCE per fork F, with the coherence evidence;
> (2) treat it as a defect and diagnose the map first; (3) revisit the box — but it is
> **pin-12 elected (KEPT, −4..+11N, 2026-07-25)**, so that reopens a closed election.
>
> **LEG 4 (quiet_gyre) NOT STARTED.** 157(a) removed the re-assessment between legs 3 and 4,
> but that assumed leg 3 produced a reading. It did not.
>
> ## ⚖ EQUATORIAL — MECHANISM OPEN, TWO HYPOTHESES RETRACTED (2026-09-06)
>
> **The verdict stands; the mechanism does not.** λx is UNRESOLVED under BOTH definitions —
> the vendored skill array (max 0.003) AND true Re(γ) (max **0.482**, never reaching 0.5).
> That is what keeps the reading standing while the cause is open (pin 178).
>
> **⚠ NAMING HAZARD, recorded NOT fixed (pin 178).** The vendored quantity called
> `coherence` is `1 - psd_diff/psd_ref` = **2√r·Re(γ) − r**, which ranges to **−4.17**. It is
> NOT a coherence. **Do not rename it** — it is the published leaderboard definition and
> comparability depends on it. **Do** record what it actually is at every consumer and in the
> Gate-1 pack, together with the Re(γ) max of 0.482.
>
> **Two mechanisms proposed and RETRACTED, both on evidence:**
> 1. **Executor's "defect — structure that does not match" (166b): WITHDRAWN.** It rested on
>    a dichotomy that read over-power as evidence against degeneracy (owner pin 170).
> 2. **Owner's "f → 0 amplitude blow-up" (170): WITHDRAWN by the owner at pin 175**, refuted
>    by the coefficients themselves. 171(c), no track involved: equatorial's per-rung RMS is
>    **below kuroshio's at six of eight rungs**, total RMS 1.56e-3 against kuroshio 1.41e-3
>    and southern 1.90e-3. **No blow-up exists.**
>
> **What the solution actually shows (pin 175):** LONG-SCALE DOMINANCE at ordinary magnitude
> — **75.5% of coefficient power in the single 905 km rung**, against kuroshio's 40.3% and
> southern's 68.7%. The apparent "over-power" is that dominance leaking into 200–300 km,
> where equatorial's track carries little variance (std 0.0889 m vs kuroshio's 0.478).
>
> **⚠ f AND SNR ARE CONFOUNDED and neither simple hypothesis fits (pin 177):**
> - **Sign check:** within-tile gradients DISAGREE. Equatorial and kuroshio improve
>   polewards; **southern WORSENS** — `diff/ref` 0.482 at |lat| 50 against 0.716 at 58. A
>   controlling *f* should not produce opposite signs.
> - **Magnitude check:** equatorial's track variance is **28.9× below** kuroshio's, but
>   `study/ref` differs by only 3–5×. A constant-injected-noise model predicts ~29×, so
>   **pure SNR does not fit either.**
> - **A THIRD hypothesis is live (175/177c):** does the 905 km share predict skill loss
>   across tiles and bands better than *f* or SNR? To be tested, NOT assumed.
>
> ## ⭐ LEG 4 IS THE CONFOUND-BREAKING EXPERIMENT — READING PRE-REGISTERED (pin 180)
>
> **⛔ THIS BLOCK WAS WRITTEN AND COMMITTED BEFORE THE LEG LAUNCHED (pin 180b).** Its whole
> value is that it cannot be edited after the result is seen. Commit order is the proof.
>
> **Why quiet gyre and not a read-only test:** it is the ONLY tile in the moderate-*f*,
> weakest-signal cell — *f* 0.66× kuroshio and 6.3× equatorial, variance 0.021× kuroshio and
> 0.62× equatorial. The other three tiles confound *f* with signal strength; **no read-only
> test on them can occupy that cell** (180a).
>
> | leg-4 outcome | what it establishes |
> |---|---|
> | **λx RESOLVES** | ***f* is controlling.** Equatorial's failure is geostrophic degeneracy; **160 applies to equatorial** and quiet gyre is a normal reading |
> | **λx UNRESOLVED** | ***f* is NOT controlling.** The discriminator is signal against an **absolute noise floor**; **BOTH weak-signal tiles record absence**, and the transfer claim becomes **regime-conditional in a way the spec did not anticipate** |
> | **RESOLVES, λx DEGRADED** | Partial — **177 arbitrates** |
>
> **⛔ 180(c) — THE DEFECT BRANCH IS NOT CLOSED AND STOPS EVERYTHING.** If quiet gyre shows
> equatorial's *specific* signature — **`study/ref` above 1 with Re(γ) collapsing below
> ~350 km — at healthy f**, that is evidence for a code defect after all.
>
> Precondition met (180d): **161 is landed**, so an unresolved λx now records with its
> evidence instead of crashing after the solve — which is exactly how leg 3 was lost.
>
> ## [SUPERSEDED by pin 180 — the hold is REVERSED; kept for the trail] LEG 4 HELD ON A MEASUREMENT (pin 176)
>
> Quiet gyre's validation track was built and measured **with no solve** (minutes). Result:
> **176(c) — it sits BELOW equatorial, not near kuroshio.**
>
> | tile | lat span | n | track std m | variance m² | vs kuroshio |
> |---|---|---|---|---|---|
> | kuroshio | +28..+43 | 95,883 | 0.4793 | 2.297e-01 | 1.0× |
> | southern | −62..−47 | 147,276 | 0.6570 | 4.317e-01 | 0.5× |
> | equatorial | −4..+11 | 107,706 | 0.0884 | 7.813e-03 | **29.4×** |
> | **quiet_gyre** | −30..−15 | 111,812 | **0.0695** | **4.828e-03** | **47.6×** |
>
> **Quiet gyre has the WEAKEST signal of all four tiles** — 47.6× below kuroshio and 1.62×
> below equatorial — and is lower than equatorial in every wavelength band except 20–60 km.
> Under the SNR branch, leg 4 would spend **27 h to produce a second unresolved reading**.
> **HELD until the confound is settled** (176c).
>
> ⚖ Also visible: both low-EKE tiles have a **rising** spectrum below ~60 km (quiet_gyre
> 2.161e-02 at 20–60 against 6.856e-03 at 60–100; equatorial 1.944e-02 against 9.073e-03) —
> a noise floor comparable to their signal, which kuroshio and southern's stronger fields
> bury. That is a THIRD reading of the same numbers and is recorded, not adopted.
>
> ## ⚖ 177/181 RESULTS — AND 180(c) IS WEAKENED AS A STOP CRITERION (2026-09-06)
>
> **⛔ THE MOST IMPORTANT FINDING: KUROSHIO CARRIES EQUATORIAL'S "DEFECT" SIGNATURE.**
> 180(c) names `study/ref` above 1 with Re(γ) collapsing as evidence for a code defect.
> **Kuroshio — healthy *f*, λx resolved at 232.53 km — has exactly that**, at 70–95 km:
> `study/ref` **3.823**, `diff/ref` **4.697**. Equatorial's identical signature sits at
> 250–400 km (`study/ref` 4.291, `diff/ref` 5.169).
>
> | tile | pathological band | study/ref | diff/ref | λx |
> |---|---|---|---|---|
> | kuroshio | **70–95 km** | 3.823 | 4.697 | resolved 232.53 |
> | equatorial | **250–400 km** | 4.291 | 5.169 | UNRESOLVED |
> | southern | 50–70 km (opposite sign) | 0.017 | 1.009 | resolved 141.95 |
>
> **The candidate mechanism this suggests, recorded NOT adopted:** every tile over-powers and
> loses phase at its own effective resolution limit; whether λx resolves depends only on
> whether that limit falls above or below the 0.5 crossing. Kuroshio's pathology at 70–95 km
> sits far below its 232 km crossing and never touches the verdict; equatorial's lands on top
> of where its crossing would be. The band ratio (~3.5×) is near the deformation-radius ratio
> (138/24 ≈ 5.8×), and **kuroshio's band coincides with the basis ladder's shortest rung,
> 80 km**.
> ⚠ **Consequence for 180(c): as written in absolute km it is not equatorial-specific and
> quiet gyre will very likely trip it.** If it is to stay a defect trigger it needs the band
> pinned RELATIVE to each tile's own resolution limit. **Owner's call — not adjusted here.**
>
> **181(c) common-floor test — universal rise, but not one common level.** All four tiles turn
> upward at **35–50 km** (ratios 1.07 / 1.03 / 1.41 / 1.58 for kuroshio / southern /
> equatorial / quiet_gyre) and again below 25 km (1.88 / 1.93 / 2.38 / 2.52). So the rise is
> NOT a weak-tile property. But it occurs at the SAME wavelength in all four rather than where
> each signal drops through a fixed level, and the levels differ ~3.6× between clusters — a
> single common absolute floor predicts convergence to ONE level. A substantial common
> component exists (3.6× spread against 28.9× in total variance); it is not the whole story.
>
> **181(a) correlations (n=21):** `corr(log10 absolute band variance, diff/ref)` = **−0.464**;
> `corr(log10 |f|, diff/ref)` = **−0.322**. Absolute variance predicts skill loss better than
> *f* — but neither is strong, so neither hypothesis is established.
>
> ## ⚖ Carried forward — unresolved, and NOT resolvable by executor work
>
> 1. **The four diverse tiles carry NO GroundTrack row** (pin 106). The transfer readings
>    ship with their composition stated **INCOMPLETE**, in the section where the numbers
>    are, as a **real weakening**.
> 2. **T6's anisotropy axis is UNEVIDENCED** (pin 108) — not "limited". Any kernel option
>    resting on directional sampling is a **WAIT that comes to the owner**.
> 3. **A power event still costs the window in flight (~3.44 h)** (pin 132). Pin 121 capped
>    the loss at one window; it did not remove it.
> 4. **The CRN production defect** stands at `phase14.stage1.crn_production_defect_deferred`
>    — a property of the shipped system, and **Stage 2G cannot close while it stands**.
> 5. **Stage 1 does not close while C-11 is outstanding** (pin 136c) — task 23 is its
>    producer and sits after the Gate-1 walk.
>
> ## ⚖ Standing practice — ruled, not preference
>
> - **⛔ THE STORE HOLDS MEASUREMENTS AND FIREWALLED HYPOTHESES. INTERPRETATION LIVES IN
>   THE PACK** (owner pin 197b — **ruled against a node, not deferred**, so there is nothing
>   here to reopen). An interpretation placed beside measurements **acquires their standing
>   by adjacency**, which is the path **pin 37(b)** closes. The three-class reading is the
>   worked example: it is in PROGRESS and the ruling doc, and **NOT** in the evidence store.
> - **AN OBLIGATION ON A FUTURE WALK IS NOT A RETROACTIVE EDIT** (197a). T12's C1→2 doc is
>   CLOSED and stays untouched; 196(e) binds the **pack walk**, and **naming it in PROGRESS
>   is the correct instrument**.
> - **A COMMIT BODY STATES THE SCOPE OF ITS OWN EVIDENCE** (197c), *including when no suite
>   was run and why*. Now a **durability rule in CLAUDE.md** rather than a habit held by
>   memory — the same correction pin 131 applied to the format/suite ordering. **Evidence
>   that states its own scope is pins 78, 83 and 134 in one line.**
>
> - **⭐ `SKILL_BANDS` IS THE CANONICAL BAND GRID** (pin 205c). A band figure is quoted
>   **from that grid**, or it **states its own cut explicitly in the same artifact**
>   (`docs/validation/phase14-stage1-band-tables.json` / `phase14.stage1.band_spectra`).
>   *A number quoted from a cut nobody can reproduce is the prose-only failure wearing a
>   decimal point* — southern's 500–1000 km figures were exactly that until 205.
> - **A DIAGNOSTIC WHOSE NUMBERS REACH A RULING WRITES AN ARTIFACT** (pin 201b). Printing
>   and exiting is the defect; re-running without fixing it repeats it.
> - **The χ² every ruling quotes is `scores.chi2_j3_validation`.** `scores.reduced_chi2` is
>   **null in all four tile rows** (202c) — quote the populated field and name it.
>
> ## ⛔ Standing stops
>
> - **`[STAGE 2]` tasks 14–21 are under pin 88's halt.** They show READY when blockers
>   clear; **that is not permission.**
> - **Nothing is sealed.** The one sanctioned seal change is UNSPENT.
> - **Gate 1 (T9) is the owner's walk.** T9 STOPs after posting.
>
> ## Next action
>
> **In order:**
> 1. **✅ DONE — pins 184–189 landed as PART 44, pins 190–191 as PART 45.** The pin-41 hole
>    is closed. **190(a)/(b) are now IMPLEMENTED** (refusal + row-reading test), and 191's
>    protocol half is in CLAUDE.md step 0b.
> 2. **✅ DONE AND RATIFIED (pin 195) 2026-09-10 — the completion procedure for T5 ran in
>    full, and ⭐ THE LANE-0 `WITNESS NOW` IS DISCHARGED, outstanding since T5d.** `seal_run check`
>    PASS (seal sha `a17ea419…` re-derived), mirror **sync + push** landed at `5ec3171` and
>    verified on origin by `ls-remote` — that push **is** the lane-0 bundle's
>    `⛔ WITNESS NOW` (96b/96c), so `equatorial_lane0_manifest` now witnesses something.
>    The two pending nodes — `tiles.equatorial` and `equatorial_lane0_manifest` — are
>    **witnessed**; the mirror carries **42 nodes**, up from 40, with **zero digest changes
>    on the 40 already there** and **no supersession spent** (owner ruling 192a: the other
>    three tiles were NOT re-committed).
>    ⚠ **`phase14.stage1.refresh_election` stays PENDING by owner ruling 193** — it is task
>    23's node and cannot be written until the shipped-config election is ruled at Gate 1
>    (pin 136). **Do not resolve it**; it is meant to keep printing.
> 3. **✅ 172 IS DISPOSED (owner pin 196, 2026-09-11). SOUTHERN'S ROW STANDS UNAMENDED.**
>    **NO AMENDMENT, NO SUPERSESSION** (196d) — *the row is accurate; what was missing was
>    the READING of it*, and a reading goes in the pack. **Amending a witnessed row to add
>    an interpretation would be the wrong instrument**; the single authorised supersession
>    stays UNSPENT. The verdict is untouched (196a): λx is set by the **0.5 crossing at
>    141.95 km**, inside a band where `diff/ref` runs **0.355–0.405** — real skill — so
>    **the long-wavelength deficit sits ABOVE where the verdict is determined**. It is
>    recorded instead as the **third failure class** above.
>    ⚖ **THE BIAS HYPOTHESIS STAYS FIREWALLED (196c):** +0.990 m with the strongest MDT
>    gradient of the four, and the bias ordering across tiles tracking gradient strength,
>    is **CONSISTENT WITH** a reference offset; per-segment detrending removes constants
>    before the verdict. **Consistent, NOT established** — the same discipline that held on
>    the geostrophic account until quiet gyre refuted it.
> 4. **⛔ GATE 1 IS NOT CLOSED — and that is the honest state (owner pin 209).**
>    The pack is POSTED and **ACCEPTED AS A PRESENTATION**:
>    `docs/superpowers/2026-09-18-phase14-gate1-pack.md`. **Three of the spec's six Gate-1
>    items do not exist** (T6/T7/T8 unopened) and **C-11 is outstanding** — a gate cannot
>    close on items that were never produced.
>    **✅ RATIFIED AND STANDING (209a):** the anchor accounting as ruled · the seam result in
>    its ruled shape · the four transfer readings as recorded · the three-class reading ·
>    the σ question open with its package · the CRN defect as a production defect.
>    **⏳ REMAINING FOR GATE 1 (209b):** T6's kernel decision · T7's revisit verdict · T8's
>    OSSE decision · the refresh election, with **task 23** recording its outcome.
>    ⛔ **The pack is SUPERSEDED, NOT REWRITTEN, when those land (209c)** — 197(a) applies to
>    it as to T12's table. The 210–212 corrections are folded in; nothing else is retro-edited.
>
> 5. **⛔ T6 IS RULED — KERNEL DECISION = WAIT, CELL EMPTY (pins 219/220).** The pack is
>    `scripts/phase14_kernel_pack.py` → `phase14.stage1.kernel_pack` (mirrored); the review
>    is `docs/superpowers/2026-09-19-t6-adversarial-reviews.md`.
>    **NO OPTION IS ELECTABLE AS THE CODE STANDS** — *a measured result about the machinery,
>    not a failure of T6* (219b):
>    - **Options 2/3 are INERT at the SO tile** — `LatitudeField.at` hull-clamps to
>      [33, 43], so the multiplier is CONSTANT across that core. Deferred to Stage 2 with
>      its reason at `phase14.stage1.kernel_hull_deferred` (pin 216). **Inert ≠ refused on
>      merit; re-openable if the hull widens** (217b).
>    - **Option 1 BREACHES ±66** carrying the box-equivalent 111.195 km scale: obs
>      **−66.1301** at the core edge, **−66.2812** at the solve-bbox edge. The pack priced
>      it at φ0 (+0.2821° margin) — the tile's *middle*, not its poleward reach.
>    - ⭐ **STRUCTURAL, FOR STAGE 2 (219b): a single scalar halo cannot express a km-space
>      kernel.** The degree footprint varies with latitude, so the scalar must be set at the
>      poleward reach — and there it breaches.
>    - **THE WAY OUT IS NAMED (219c), which is why this is a WAIT and not a refusal:** the
>      breach belongs to the 111.195 km scale, not to km-space kernels. **Two resolutions,
>      both Stage 2 — a smaller km scale, or a latitude-aware halo** under fork-d pin 4's
>      single point of change.
>    - **`operative_halo_deg()` IS UNTOUCHED** (219d). **D4 inherits this; Stage 2G cannot
>      decide pole handling without it** (217e).
>
> 6. **✅ 215/216 FOLDED.** The ±66 attestation now reads the poleward edge from
>    **`TileFrame.obs_bbox` itself** — `max(|grid.min − halo|, |grid.max + halo|)`, signed —
>    and refuses a frame that cannot rebuild its own `solve_bbox`. Test-pinned on a
>    **synthetic northern tile whose overshoot flips the verdict** (215b), which the four
>    real tiles could not expose. **§1.11 of the posted pack is corrected, and only §1.11**
>    (215d): kuroshio **+46.0 → +46.2**, margin **20.0° → 19.8°**.
>    ⚖ **Measured while applying it: the `np.arange` overshoot is FLOATING-POINT DEPENDENT,
>    not a uniform rule** — present at southern (−43.8) and kuroshio (+46.2), absent at
>    quiet_gyre (−12.0) and equatorial (+14.0). That is the argument for reading the edge
>    from the framing code rather than from any expression.
>
> 7. **⛔ T7 IS RULED — THE AGGREGATE IS REFUSED (pin 224). A WAIT WITH A MEASUREMENT.**
>    Band provenance IS pinned to `phase10_lanes` (pin 9) — three ways: hand-read literals,
>    equality to the module, and **asserted unequal to `phase13_lanes`**, because the two
>    export `BOXES`/`LANES`/`ALL_DIMS` with **no shared dimension name and no error on a
>    swap** (ratified 226). The per-tile config is pinned **non-aliased**, which is how the
>    fork-d pin 6 confound would actually arrive.
>    **⭐ A PHASE-10 LANE IS NOT ONE LEG** — it is `n_sobol_per_lane` trials plus anchors,
>    and at tile scale each trial is a full leg. **68 solves / 1,678.2 h / 69.9 days**
>    full-scope; **252 / 6,219.4 h / 259.1 days** screening. Table and basis: ruling PART 52.
>    **⭐ THE PER-LANE GUARD AND THE AGGREGATE ARE DEMONSTRABLY SEPARATE QUESTIONS (224b).**
>    Every solve is **RUN** — 26.03 h against 40 h, 14 h of margin — so **99(b) marks NOT
>    ONE LANE a WAIT**, and the total is refused anyway. The guard was not wrong and was not
>    overridden; **it has no opinion on the total, by design**. That is **pin 222(c)
>    demonstrated, not asserted**, and why `revisit_tier_verdict` stays as built.
>    **ANCHORS-ONLY IS PRICED AND NOT ELECTED (225): 12 solves / 296.2 h / 12.3 d, 5.7×
>    cheaper — STAGE 2's entry point.** ⛔ **Its claim is STRICTLY WEAKER and the limit
>    travels with it:** it can say *"the lane's designated configuration does not beat lane-0
>    in this regime"*; it **cannot** say *"no configuration in the lane does"*. **A negative
>    result needs the second, and the Sobol search is what buys it.**
>    ⚖ **The screening lever is NAMED and DELIBERATELY UNPRICED** (226): phase-10 screens
>    91/365 days, but the Stage-1 leg is a **9-window solve, not a 365-day score**, so that
>    ratio has no valid basis here. **If it is ever wanted, it is a MEASUREMENT.**
>    ✅ **T7 IS CLOSED (pin 230f), AS A REFUSAL AND NOT AS DELIVERED LANES.** The AC's
>    Verify clause reads *"real rows present for all four tiles OR WAIT ROWS WITH SIZING
>    NUMBERS"*, and four WAIT rows with sizing numbers are what landed:
>    **`phase14.stage1.revisit.<tile>`**, mirrored and **witnessed** — `sync` a clean
>    APPEND, `check` PASS at 51 nodes **without a re-sync**, and **no supersession spent**
>    (230e). Producer `scripts/phase14_revisit_wait_rows.py`, test-pinned; the rows are
>    DERIVED from the measured legs and the sealed budget, never hand-pasted.
>    ⛔ **EACH ROW STATES WHY IT IS A WAIT DESPITE EVERY LANE PASSING** (230b) — a row
>    showing only RUN cells would read as an unexplained non-run, and one showing WAIT cells
>    would invert the finding by claiming the lanes were unaffordable. **225(b)'s limit
>    travels IN the row, verbatim**, so the cheap option cannot be pulled from the store
>    without its weaker claim.
>    **▶ NEXT — T8, on the owner's word, and not before** (priced from the CONVERGED
>    numbers, never the capped T2 probe, basis in-row — 99c). Then **task 23** (C-11),
>    which sits **behind task 24**. **Gate 1 carries TWO ruled WAITs (219, 224) and does not
>    close until they resolve or the owner rules without them.**

> ---
> ## 📦 TRAIL ARCHIVED — `docs/progress-archive/phase14-stage1-trail.md`
>
> The `[TRAIL — superseded by CURRENT STATE above; kept, not deleted]` blocks that used to
> follow this line (leg-1 gate, pins 139–153 landings, 147(b), leg 1, leg 2's hold, T12,
> the T5 authorisation and everything under it, ~325 KB) were **moved verbatim** to that
> file on 2026-09-18 when PROGRESS.md crossed the repo's 500 KB large-file hook. They are
> history, not current state (pin 154). The older, unquoted phase sections below (MIOST
> brief, Stage-C, the RESUME HERE blocks) were **not** moved.

## 📦 OLDER TRAIL ARCHIVED — `docs/progress-archive/pre-phase14-trail.md`

The MIOST method brief, Stage-A/B/C sections, the 2026-06-30/07-01 measurements, the conda
feedstock watch item and every superseded `RESUME HERE` block (Phase 5, Stage B) that used to
sit here were **moved verbatim** to that file on 2026-09-18 (owner pin 207). They are history.
The canonical sections below — Current work, Cross-cutting decisions, Gotchas, Deferred
items — were not moved.

---

## Current work (index — do not duplicate task state here)

- **Phase 11: evaluator wiring (report-only) — DESIGN APPROVED 2026-07-15, awaiting
  owner file review of the spec before writing-plans.**
  - Design: `docs/superpowers/specs/2026-07-15-phase11-evaluator-wiring-design.md`
    (forks a–e + 7 batch pins owner-decided; prerequisites verified on public HEAD).
  - Plan: `docs/superpowers/plans/2026-07-15-phase11-evaluator-wiring.md`
    (12 tasks; tracker `.tasks.json` co-located with ids AND names; native ids 5–16).
  - Next action: owner reviews the PLAN (spec approved 2026-07-15) → on sign-off,
    execute via subagent-driven-development or executing-plans. Task 12 is the
    phase-close owner gate.

- **Phase 4: FEM/triangulation SPDE + non-chain coherent sampler — IN PROGRESS.**
  - **Stage A COMPLETE (Tasks 1–4); Stage-A GATE PASSED.** Projection seam
    (`core/projection.py`) consumed by `GMRFCovarianceOperator` (carries `q_prior`, C3
    `_diag` fast==slow pinned) and de-gridded `PrecisionFields`/`PrecisionDistribution`
    (`projection` + `prior_precision`, cov/sample route through `projection.weights`/
    `field_shape`); `GMRFPrecisionReduction` threads both; `solve.py` unchanged (projection
    rides on `base_fields`). Gate evidence: **185 passed / 2 skipped** (178 + 7 new), typecheck
    + lint clean; tests diff vs `31a58c6` = 96 insertions / 0 deletions (additions only);
    invariant-2 grep clean on the GMRF path. **Scoping note (gotcha):** the Task-4 gate grep's
    sole hit is `persisted.py` `PersistedDistribution.sample` (`ny, nx = self.grid.shape`) — the
    **OI low-rank** rep, which is inherently grid-bound and NOT in Phase-4 de-grid scope. The
    GMRF precision read-off (`PrecisionDistribution` + `GMRFCovarianceOperator`) is grep-clean.
    Interpret invariant-2 as "the precision/GMRF path is projection-driven", not "persisted.py
    contains no `.shape`".
  - **Stage B Tasks 5–6 COMMITTED then SUPERSEDED by a design pivot (`_strip_network` kept,
    `_draw_joint`/`_strip_prior` to be removed).** Tasks 5 (`a619265`) and 6 (`809a570`) built the
    spec-literal **synthesized strip-field** sampler (`_draw_joint`: one auxiliary field drawn from
    the prior-induced strip sub-GMRF; tiles kriged toward it). Task 7's verification **disproved that
    construction** — see the canonical Phase-4 cross-cutting decision "Stage-B sampler = spanning-tree
    hand-forward" below. **Working tree is clean at `809a570`** (Task-7 synthesized-field code was
    written, disproved, and reverted uncommitted — nothing wrong is on disk). `_strip_network` is
    kept (it computes the tile-adjacency / shared-node sets the spanning tree needs); `_draw_joint`
    and `_strip_prior` are removed in the re-architected Task 6.
  - **Stage B COMPLETE (Tasks 6–9); Stage-B GATE PASSED (uncommitted at this checkpoint — awaiting
    owner gate review before Stage C).** The spanning-tree hand-forward sampler is implemented and
    the gate is GREEN on the real near-singular natl60 regime. Final construction + the four-turn
    finding are in "Cross-cutting decisions (Phase 4)" below ("Stage-B sampler …", esp. the
    **conditioning-floor law** and the **eigmin-rooting contract**). Gate evidence (real natl60 2×2):
    stationary tree-edge **0.681 ≤ matched_chain 0.706·1.15**, dropped 0.681, dir 1.012;
    nonstationary tree 0.688, dir 1.006; conditioning floor **monotone in eigmin** `[0.706,0.624,
    0.551]` with tree==chain at equal conditioning; two-tree invariance PASSED (well-conditioned
    roots agree 0.68/0.84, worst-conditioned root 31.4 is the negative control the eigmin rule
    avoids). **Next action: owner Stage-B gate review → on sign-off, commit Tasks 6–9 + Stage C
    Task 10.**
  - Scope (source of truth): `phase4_scope_spec.md` (settled + owner-amended, `00519b1`).
  - Design: `docs/superpowers/specs/2026-06-26-phase4-fem-and-nonchain-sampler-design.md` (`f7960f8`).
  - Plan: `docs/superpowers/plans/2026-06-26-phase4-fem-and-nonchain-sampler.md`
    (16 tasks; tracker `.tasks.json` co-located, Tasks 1–4 `completed`).
  - **Hard-gated sequencing:** Stage A (Tasks 1–4, generalize under green) → Stage B
    (Tasks 5–9, non-chain joint-kriging sampler on the grid) → Stage C (Tasks 10–16, FEM).
    Three user-gates: Task 4 (Stage-A regression — Phase-3 suite reproduces exactly), Task 9
    (Stage-B positive control — distinct-tiles cross-seam + corner-junction joint cov +
    nonstationary, residual recorded; junction-tree fallback only if out-of-tolerance), Task 16
    (Stage-C FEM DoD).
  - **Five pinned correctness contracts (tested, not assumed — see design §0):** C1 strip prior
    on the induced subgraph (corner-junction joint cov), C2 three white-noise streams, C3 `_diag`
    fast-path equivalence, C4 per-node strip-prior κ (nonstationary), C5 mechanically-enforced
    no-grid-path-for-FEM; + C6 shared mesh-node match, C7 boundary-measured payoff margin.
  - **Key decisions:** scipy.spatial.Delaunay + hand-rolled P1 assembly (no new dep, Shewchuk
    upgrade behind the same seam); strip-prior = induced submatrix of the persisted per-tile
    PRIOR precisions (so PrecisionFields gains `projection` + `prior_precision`); `GmrfKrigingSolve`
    kept intact as the 1-D chain regression oracle (registry repoints to `GmrfJointKrigingSolve`,
    one wiring assertion updated). **Next action: Task 1 (Projection seam).**
- **Phase 3: GMRF method + representation-agnostic generalization — COMPLETE (all 11 tasks).**
  - **Stage C COMPLETE (Tasks 10–11):** Task 10 `PerturbEnsembleDegradation` driver end-to-end
    (per-tile independent members, weight-crossfaded; `EmpiricalReduction` retagged
    `perturb-ensemble`; blend appends `degradation_transform`/`KnownBias.DEGRADED_COHERENCE`;
    asserts the OPPOSITE contract — coherence loss recorded, mean continuous, sampler honestly
    under-dispersed vs the conservative marginal, NOT held to the coherence bar). Task 11
    nonstationary-κ GMRF (`MaternGMRF.solve` resolves `range` scalar OR field → elementwise κ
    field → spatially-varying `Q`; `kappa_from_range`/`range_from_kappa` polymorphic;
    κ↔range mapping recorded). Full suite **178 passed / 2 skipped**, typecheck + lint clean.
  - All three user-gates PASSED (Task 3 Stage-A regression, Task 5 Takahashi-vs-oracle, Task 9
    Stage-B kriging coherence). Plan `.tasks.json` all `completed`.
  - **Stage A COMPLETE (Tasks 1–3).** Three seams generalized OI-first under green:
    `ReductionStrategy` (`distributions/reduction.py`, selected by live-operator
    `representation`) + `CoherentMemberDriver` (`LowRankSharedBasis`, selected by persisted
    `sampler_spec`). Stage-A user-gate PASSED with captured AC evidence — Phase-2 subset
    129/2 green and untouched (full suite 134/2 = 129 + 5 new Stage-A tests), typecheck/lint
    clean, zero Phase-2 test files modified (diffed vs pre-Phase-3 baseline `793297e`).
  - **Stage B Tasks 4–8 COMPLETE** (committed): GMRF grid topology + bilinear/Projection
    (`methods/gmrf_grid.py`); CHOLMOD factor + hand-rolled Takahashi selective inverse
    (`methods/gmrf_linalg.py`, **USER-GATE PASSED** vs dense-Q⁻¹ oracle); `MaternGMRF` EXACT
    sparse-precision operator + temporal-taper conditioning (`methods/gmrf.py`, registered);
    `PrecisionFields`/`PrecisionDistribution` + `GMRFPrecisionReduction` (genuine-first-class,
    no factor); `solve_unit` dispatches `PrecisionFields → PrecisionDistribution`.
  - **Task 9 (Stage-B gate) COMPLETE — reworked via conditioning-by-kriging; GATE PASSES.**
    The original `GmrfPrecisionSolve` "native shared-w" driver (Task 8) was DISPROVEN
    (cross-seam derived quantities ~50% under-dispersed) and is REMOVED. Replaced by
    `GmrfKrigingSolve` (9a–9d, all committed): per-tile exact posterior draw krige-corrected
    toward ONE global node-space realization (single forward sweep, values-not-seeds, Q-separator
    precondition asserted). **Gate evidence (captured):** cross-seam `firstdifference` variance
    ratio blend/ref **min 0.93** (conservative; old driver ~0.49 / −0.51), correlation-structure
    fidelity max-dev **0.10**, pointwise σ-upper-bound held, OSSE+OSE + provenance +
    first-class all green; full suite **171 passed / 2 skipped**, typecheck + lint clean. Joint-cov
    oracle (9c) pins exactness vs a dense global reference (per-tile, cross-seam, 3-tile
    transitivity) + separator negative control. **USER-GATE: awaiting owner sign-off before
    Stage C** (spec-§8 escalation was NOT triggered — gate passed).
  - **Task-9 rework 9a–9c COMPLETE (committed); 9d IS THE NEXT ACTION.**
    - 9a (`posterior_cov_columns` full `(Q⁻¹)[:,S]` via cached per-node back-solves on
      `GMRFFactor`/`PrecisionDistribution`) — pinned vs dense oracle.
    - 9b (`GmrfKrigingSolve` forward-sweep driver, values-not-seeds, **Q-separator assertion**
      overlap ≥ `STENCIL_REACH=2`) — replaced the disproven `GmrfPrecisionSolve` (class removed)
      under `sampler_spec="sparse-precision"`.
    - 9c (joint-cov oracle `tests/unit/test_gmrf_kriging_oracle.py`): per-tile full-cov ==
      exact posterior; cross-seam joint (incl. across-seam blocks) == global; 3-tile
      transitivity; separator negative control. All EXACT by construction.
  - **Next action: Phase 3 is DONE.** Phase 4 (autotune) is the next milestone (deferred,
    scoped after Phase 3 runs — spec §6). Before Phase 4 build: the GMRF cross-tile sweep is
    exact only for tree-structured tile adjacency; 2-D/FEM tilings need the pre-drawn-joint or
    junction-tree variant (spec §5.3.1 Phase-4 caveat — do NOT inherit as unconditionally true).
  - **Working-tree state at this checkpoint (committed):** `pipeline._blend_eval_points` has the
    sparse-precision no-factor **moment-crossfade** OSE path + the `eval_point_cov` provenance
    marker (Task-9 §B6, keeper); `GmrfPrecisionSolve` carries a shape-bug fix but the whole class
    is superseded by `GmrfKrigingSolve` in 9b; the obsolete `test_gmrf_blend_no_variance_dip`
    (pre-amendment contract) was removed (9d writes the derived-quantity-parity replacement).
  - Scope (source of truth): `phase3_scope_spec.md` (settled; §5.1 now records the two
    settled forks — scikit-sparse/CHOLMOD backend + temporal-taper-into-R conditioning — and
    the forward-compat Projection abstraction).
  - Design = the spec; Implementation plan: `docs/superpowers/plans/2026-06-25-phase3-gmrf-representation-generalization.md`
    (11 tasks; tracker `.tasks.json` co-located, all `pending`).
  - **Hard-gated sequencing:** Stage A (Tasks 1–3, generalize OI under green) → Stage B
    (Tasks 4–9, add GMRF) → Stage C (Tasks 10–11). Three user-gates: Task 3 (Stage-A
    regression, 129/2 must stay green — if OI changes, surface it, don't adjust tests),
    Task 5 (Takahashi vs dense-Q⁻¹ oracle — red = math bug, not a tolerance loosen),
    Task 9 (Stage-B GMRF blend validation — spec-§8 escalation on failure).
  - **Key architecture decisions (canonical — see Cross-cutting decisions Phase 3):**
    two-point dispatch split (reduction by live-operator representation pre-persistence;
    coherence driver by persisted `sampler_spec` post-persistence); `to_persisted` is a
    `ReductionStrategy` in `distributions/reduction.py`, NOT on the core Protocol
    (invariant 1 + one-way dependency rule); GMRF read off the precision via a `Projection`
    (grid=identity, off-grid=bilinear) so a later FEM phase needs only a new projection.
- **Phase 2: tiling / blend / coherent uncertainty — COMPLETE (all 17 tasks 0–16).**
  - Scope (source of truth): `phase2_scope_spec.md` (committed `fa93897`).
  - Design doc: `docs/superpowers/specs/2026-06-23-phase2-tiling-blend-architecture-design.md`.
  - Implementation plan: `docs/superpowers/plans/2026-06-23-phase2-tiling-blend.md`
    (17 tasks, 0–16); tracker `.tasks.json` co-located, all `completed`.
  - **Both user gates PASSED with captured AC evidence:** Stage A (Task 15 — regional blend
    == single-tile, no seam, conservative σ, withheld OSSE+OSE eval, provenance, both
    withholding exemplars) and Stage B (Task 16 — projection-mixed partition, sample-based
    `regrid`, cross-CRS blend, polar-void relax-to-prior, opt-in global skipped cleanly).
  - **Key §8 resolution (see Cross-cutting decisions):** the structured coherent-sample
    driver is the shared-overlap-basis (Löwdin) construction, NOT member-only `z_r`.
  - Suite: 129 passed / 2 skipped (Stage-B global run + one pre-existing skip).
  - **DEFERRED to Task 15:** `run_tiled_pipeline` in `application/pipeline.py`. The plan's Task-12 Step 3 only implements `TilingCoordinator` (which IS done + tested) and says the pipeline wiring is "exercised in Task 15". The eval impedance — `_evaluate` reads `product.per_time[].base.fields.mean`, but the coordinator returns `BlendedDistribution`s — is resolved when Task 15's integration test defines the contract. Build `run_tiled_pipeline` there.
- **Milestone: rename to `sverdrup` + PyPI release — COMPLETE (Tasks 1–7).**
  - Design doc: `docs/superpowers/specs/2026-06-21-sverdrup-pypi-release-design.md` (approved).
  - Implementation plan: `docs/superpowers/plans/2026-06-21-sverdrup-pypi-release.md` (7 tasks);
    tracker `.tasks.json` all `completed`.
  - Package renamed `regatta`→`sverdrup`; hatchling + hatch-vcs tag-driven build; Apache-2.0 +
    metadata + `py.typed`; core deps + `dask`/`io`/`all` extras; Trusted-Publishing workflow
    shipped at `docs/superpowers/ci/release.yml` (Option B). User-gate (clean-venv install smoke)
    re-validated. Public repo `killett/sverdrup` created and `main` pushed.
  - **DONE end-to-end:** all three user-side steps completed by the user — workflow installed,
    PyPI Trusted Publisher configured, `v0.1.0` tagged+pushed. `sverdrup 0.1.0` is **live on
    PyPI** (wheel+sdist, Apache-2.0); `pip install sverdrup` verified in a clean venv.
- **conda-forge distribution (in progress):**
  - Recipe generated via `grayskull` (run with `pixi exec grayskull`, not added to manifest),
    polished, and committed at `conda-recipe/meta.yaml` (+ `conda-recipe/README.md`).
  - `noarch: python`; sdist sha256 verified against PyPI; confirmed the sdist builds **without
    `.git`** (hatch-vcs reads version from PKG-INFO) — so conda-forge's sdist build works.
  - **Auto-update mechanism (the goal):** after the one-time `conda-forge/staged-recipes` PR,
    the conda-forge **autotick bot** watches PyPI and opens a version-bump PR on every PyPI
    release. Steady state: push tag → PyPI Action publishes → bot opens feedstock PR → merge.
  - **staged-recipes PR OPEN:** https://github.com/conda-forge/staged-recipes/pull/33814
    (`killett:sverdrup`). Awaiting conda-forge CI + maintainer review/merge → feedstock
    auto-created → conda package ships. User responds to any reviewer feedback.
  - **Gotcha:** the autotick bot only bumps version+hash. When `pyproject.toml` runtime deps
    change, mirror them into `requirements/run` in both `conda-recipe/meta.yaml` and the
    feedstock PR.
  - **Gotcha (CI failure, fixed):** first staged-recipes build #1541860 FAILED on all platforms
    in the *test* phase: `ModuleNotFoundError: No module named 'dask'`. Cause — the recipe test
    ran `python -m sverdrup`, but `__main__.py` eagerly imports the dask executor + pipeline
    (the `dask`/`io` *optional extras*, not core run deps). The conda test env has only core
    deps. Fix: test only the core import surface (`import sverdrup`, `sverdrup.core.grid`,
    `pip check`) — never the entry point — since core deps are all that's guaranteed installed.
    Same trap will bite any feedstock test: do not add extras-dependent checks to `test:`.
- **Phase 1: COMPLETE** — 22 tasks on `main`; suite 70 passed / 1 skipped; both user-gates
  re-validated. Plan: `docs/superpowers/plans/2026-06-21-regatta-phase1.md` (historical).
  Design: `docs/superpowers/specs/2026-06-21-regatta-phase1-architecture-design.md`.

## Cross-cutting decisions (canonical — lives nowhere else)

- **⚖ DESIGN CONFLICT, NOT AN EXECUTION GAP — "GroundTrack per tile×era" vs "zero new
  surfaces" (owner pin 106, 2026-08-30; ⚖ AMENDED IN SCOPE by pin 112(b), same day).**
  **THE AMENDMENT, recorded against 106 with the 109(a) sweep as its cause:** 106 stands
  for the **four diverse tiles** — `h2ag` ≠ `h2g`, box-and-φ₀ scoped, absence honestly
  recorded. It does **NOT** cover `anchor`, `seam_n`, `seam_s`: their GroundTrack absence
  was a **LOOKUP PATH** (the canonical artifact sits in `ours/`, the reader looked beside
  the maps one directory below) and is fixed with **no new producer** —
  `geometry_artifact_for` resolves the canonical artifact and admits a tile only when the
  DERIVATION'S OWN `box_lon`/`phi0` cover it (read from the artifact, never typed: four of
  five CMEMS codes match, so a mission-keyed lookup would have handed Gulf-Stream geometry
  to a Pacific tile). **The fix was not silently widened** (112a: no copy into the evidence
  directory — a duplicate raises its own witness question). The spec asks for both, and **they are
  incompatible while the orbit-geometry provider is CHALLENGE-BOX scoped**:
  `build_geometry_artifact` fixes `_LON_LO`/`_LON_HI` and φ0 = 38.1 and derives from the
  dc_obs L3 files, so `ContextKey.ORBIT_GEOMETRY` is unavailable at the four diverse
  tiles and `Registry.applicable` correctly excludes `groundtrack` there. Stage 1's
  wiring is CORRECT and the absences are honestly recorded (fork F) — **there is no bug
  to find here**, which is exactly why it is written down: a successor stage that meets
  four transfer readings with no GroundTrack row would otherwise open it as a defect.
  **Ruled consequences:** no Stage-1 producer (106a — a per-tile derivation is a new
  surface); the Gate-1 pack states the incomplete composition **in the transfer-readings
  section, where the numbers are** (106c, folded into T9); C1→2 carries **per-tile orbit
  geometry as named Stage-2 work** with the 0.410→0.331 founding-metric context (106d,
  folded into T12). **The record calls it what it is (106e): a REAL WEAKENING of the
  deliverable**, accepted because absence honestly recorded beats geometry that does not
  belong to the tile — not because the gap is small.

- **Method 1 = hand-rolled dense GP/OI** (not pyinterp/GPSat). Native covariance +
  whole-field samples via cached Cholesky `L` of `K_dd+R`, `cov(A,B)=K_AB−Vᵀ_A V_B`,
  `V_X=L⁻¹K_dX`. `R` is a structured operator (diagonal for nadir). Two complementary
  seams: `LinearSolver` (methods/, backend swap *within* the kernel formulation) and
  `CovarianceOperator` Protocol (core/, carries the kernel→precision/SPDE jump).
- **`CovarianceOperator` is the seam, not the GP.** `GaussianPredictiveDistribution(mean,
  cov: CovarianceOperator)` is method-agnostic; GP math lives in `methods/oi.py`. Operator
  declares `fidelity ∈ {EXACT, LOW_RANK, SAMPLE}`.
- **Exact/persisted boundary:** the unit of work returns the **Persisted** rep (mean +
  exact marginal var + low-rank `B` + clipped diagonal residual `d` + seed + sampler spec +
  rank `r` + captured-energy diagnostic), **never** a live operator carrying `L`. `B` from a
  matrix-free seeded randomized SVD of `P`; `d = clip(diag(P)−rowsum(B²), 0, None)`.
- **Unifying on-worker rule:** the worker extracts *everything needing the EXACT operator* —
  base reduction, declared derived quantities (first-difference), AND eval-point predictions
  at withheld/off-grid locations — before discarding the operator. Off-grid predictives are
  computed exactly, never by interpolating a marginal-variance field (invariant 7).
- **`Product` is an explicit bundle:** base + derived Persisted products + eval-point
  predictions, provenance linking each (route + `CovFidelity` stamped).
- **Derived dispatch = linearity × representation × `CovFidelity`.** Provenance stamps the
  covariance fidelity used. Only `firstdifference` is real (on-worker, EXACT); velocity/eke/
  transport/area_average are committed-signature stubs.
- **Data (Decision B):** real `DataSource` against ODC THREDDS + `./data/cache/`; daily
  NATL60-CJM165 reference (NOT the 11 GB hourly) clipped to 42-day window
  **2012-10-22→2012-12-02**; OSSE nadir obs ~285 MB whole. Committed tiny NetCDF fixtures for
  offline CI. Oracle = opt-in OI-RMSE parity **within 10% of the ODC OI baseline** (skipif no
  data/network; ≤25% for the tiny-fixture smoke run). OSE eval uses the withheld **CryoSat-2**
  along-track.
- **Space-time structure (load-bearing):** the GP covariance is space-time — spatial length
  scale × **temporal correlation scale**, both through the `ParameterProvider`. The
  unit-of-work window is space-time (spatial tile × temporal obs window around target output
  time(s); the 21-day spin-up gives early times temporal neighbors and bounds `N_obs`).
  **`GridSpec` stays purely spatial**; time is carried on the `Product` as a series of
  per-time persisted fields. One factored `K_dd+R` serves all output times in the window.
- **Kernel:** pinned to stationary **Matérn-3/2** (variance + spatial length + temporal
  scale), behind a `methods/kernel.py::Kernel` interface so it can go nonstationary later
  without touching `GPCovarianceOperator`.

## Cross-cutting decisions (canonical — Phase 4)

- **Stage-B non-chain sampler = spanning-tree hand-forward (NOT a synthesized strip field).**
  The spec-literal Task-6 construction (`_draw_joint`: draw ONE auxiliary field over the
  overlap-strip sub-GMRF, krige every tile toward it) was **disproved by measurement** and replaced.
  This decision is owner-confirmed across a multi-turn adversarial review; the measurement trail is
  recorded here because it is load-bearing and lives nowhere else.
  - **Disproof (real natl60_tiny fixture, 3-tile + 2×2):** the synthesized-field driver blows the
    cross-seam first-difference variance ratio to **376×** (bound ≤2.5) and joint-cov rel-err vs the
    dense global posterior to **1.617**. On a well-conditioned synthetic corner fixture the same
    driver is fine (cross-seam 0.77–1.33) — so the construction is not trivially broken; the natl60
    fixture is the discriminator.
  - **Mechanism (measured, not guessed):**
    1. prior-vs-posterior is a **non-issue** — obs sit at tile centres, so `AᵀR⁻¹A≈0` at the strip
       nodes and `Q_post ≡ Q_prior` there to machine precision (strip submatrices byte-identical;
       `x_joint` std 613 either way). The "diffuse prior was wrong scale" hypothesis is **refuted**.
    2. the joint-cov error is **high-frequency**, **90% in the complement** of the bottom-k near-null
       subspace, and a shared global coarse-mode draw does **not** close it (1.617→1.393 at k=6).
       There is **no spectral gap** (global `Q_post` bottom eigenvalues `2.5e-7, 4.95e-7, …`, a
       continuum) — so the near-improper behaviour is an O(n) low-frequency tail, NOT a low-dimensional
       coarse space. Coarse-space deflation is **refuted**.
    3. `cond(sigma_ss) ≈ 4e8` (the value-conditioning operator `solve(Σ_ss, x_s − x_u|_S)`), **flat
       across halo width k=1,2,3 and resolution 0.5°/1.0°**, pinned by `Q_post`'s near-null eigenvalue
       2.5e-7 — i.e. **intrinsic** (sparse nadir obs leave the `(κ²−Δ)²` low-frequency mode
       under-determined), NOT a strip-resolution mismatch. A resolution precondition would not fix it.
    4. **jitter is a cover-up** (proven): adding `λI` to `Σ_ss` collapses the gradient ratio
       (324→3.2) while joint-cov rel-err **stays 0.61–0.73** — gradient parity goes green while the
       joint law is still 60–70% wrong. `pinv(rcond)` is a no-op (modes are physically huge-variance,
       not numerically tiny). **Gradient parity ≠ joint-law fidelity; gate the joint cov.**
  - **The fix:** the 4e8 singularity is *never excited* when conditioning targets are **consistent**
    (a residual `x_s − x_u|_S` that is tiny because `x_s` is an actual neighbour draw from the same
    posterior). That is exactly what the Phase-3 **chain** sweep does (`GmrfKrigingSolve._sweep`,
    still green). Generalize the line to a **max-overlap spanning tree of the tile-adjacency graph**:
    each tile is hand-forward-conditioned on its parent's already-drawn overlap values (the proven
    chain mechanism), non-tree edges carry a **bounded, recorded** transitive-coherence residual.
  - **Validation (2×2 natl60):** spanning-tree sweep drops overall joint-cov rel-err **1.617 → 0.313**
    (no 4e8 excitation). Tree edges **0.18–0.24**, dropped edges **0.19–0.43**. The plain **chain
    baseline** on the green 3-tile natl60 case is **0.298 overall, edges 0.294/0.313** — i.e. the
    ~0.30 halo-truncation residual already accepted & shipped green. Tree edges are **no worse than
    that baseline**; the dropped-edge max (0.43, a BFS-star artifact that kept a low-overlap diagonal
    and dropped a high-overlap side) is **1.4× the baseline** and improves under max-overlap MST.
  - **Task-9 gate = three coupled assertions (thresholds derived from the 0.30 chain baseline, not
    guessed):** (1) **tree-edge parity** — `max_tree_edge_residual ≤ chain_baseline·(1+slack)`,
    chain_baseline measured on the 1-D natl60 case; (2) **dropped-edge relative bound** —
    `max_dropped_edge_residual ≤ C · max_tree_edge_residual`, `C ∈ [2,3]`; (3) **conservative
    direction** — cross-seam derived-quantity variance ratio (blend/ref) on dropped edges `≥ 1−ε`,
    never under-dispersed (the real protection; magnitude-bounded-but-overconfident must fail).
    Plus a **two-tree invariance property test**: the shipped blend is within tolerance under the MST
    AND one alternative spanning tree (correctness is tree-invariant; only the residual distribution
    moves — if correctness depends on the tree, topology-fragility has returned → loud red).
  - **Per-tree-edge separation assert:** the MST is built from existing `extended_window` overlap
    strengths; every selected tree edge must have overlap ≥ the stencil-separation requirement
    (`_assert_separates` content, now per-tree-edge not per-chain-link) — a too-thin tree edge cannot
    hand forward and is a loud red per edge.
  - **Spec amendment (replaces two wrong sentences):** §5.3/§4 becomes *"hand-forward conditioning
    along a max-overlap spanning tree of the tile adjacency; non-tree edges carry a bounded, recorded
    coherence residual; junction-tree is the exact escalation if a measured residual exceeds
    tolerance."* **Product-facing disclosure (load-bearing, honest):** the shipped global SSHA
    uncertainty carries a bounded, recorded cross-seam coherence residual on **non-tree** tile
    adjacencies — coherence there is **transitive, not direct**; a downstream consumer computing a
    transport across a non-tree seam is entitled to know this. Junction-tree (a) is the documented
    **exact escalation** if the Phase-5 tuner wanders to short range and pushes a measured residual
    past the gate; it is NOT adopted now because it re-introduces tile-topology dependence and
    √(#tiles) treewidth — the very costs Stage B exists to avoid.
  - **Contracts C1/C2/C4 (synthesized-field) are RETIRED** and replaced by the spanning-tree
    contracts above. C3, C5, C6, C7 stand. Obsolete on-disk code to remove in the re-architected
    Task 6: `_draw_joint`, `_strip_prior`, `_interiorness` (`distributions/coherent.py`) and their
    tests (`tests/unit/test_draw_joint.py`). `_strip_network` is **kept** (adjacency + shared-node
    sets). Stage-A (Tasks 1–4) is **unaffected** — the Projection seam / de-grid generalization is
    orthogonal and already gated green.
  - **STANDING STAGE-B CAUTION (read before touching the GMRF coherent sampler, esp. in Phase 5).**
    Across four consecutive review turns the failure (or the fix) lived in a **joint-law property
    invisible to a magnitude/gradient-only gate**: (1) the value-conditioning singularity
    `cond(Σ_ss)≈4e8`, (2) coarse-mode mislocalization (error in the complement, not the near-null),
    (3) jitter laundering (gradient green / joint-cov 0.6+ wrong), (4) the relative-bound degeneracy
    (a near-zero tree-edge residual would spuriously red a bounded dropped edge — hence the
    chain-baseline floor on assertion 2). **The GMRF coherent sampler's failure modes are joint-law
    properties; gate the joint covariance vs a dense reference and the conservative DIRECTION at the
    seam, never just magnitude/gradient.** The **near-singular short-range posterior** (sparse obs +
    near-improper `(κ²−Δ)²` ⇒ `Q_post` eigmin ~1e-7) is the regime that excites all four — and
    **Phase 5's autotuner searches `range`, which drives the posterior straight into it.** Re-enter
    this regime with this context, not from scratch.

- **Stage-B sampler — FINAL construction (supersedes the spanning-tree decision above with the
  selection rule + the intrinsic floor; all measured on real natl60).** The non-chain sampler is
  `GmrfTreeKrigingSolve`: hand-forward conditioning along a **minimum-eccentricity, max-overlap
  spanning tree, rooted at the BEST-CONDITIONED tile**, with the dropped (non-tree) edges carrying a
  bounded, recorded transitive-coherence residual. Four findings, each measured, each a contract:
  - **Depth governs stability, not overlap.** Hand-forward kriging accumulates drift per hop; a deep
    tree routes the conditioning through the near-singular `Σ_ss` (`cond≈4e8`) in an order that
    amplifies (measured 10× at a depth-3 edge vs ~1.4× at depth 1; the max-overlap Kruskal MST can be
    deep → unstable). Fix: **minimum-eccentricity** root + shortest-hop BFS tree → shallow (a star,
    depth 1, on the `k·corr_len` heavy-overlap regime); rel stays bounded (0.40–0.45) as the domain
    scales to 3×2 / 3×3 where the naive MST reaches depth 3–4 and risks blow-up.
  - **EIGMIN-ROOTING CONTRACT (load-bearing, pinned with a negative control).** The blow-up root is
    the **most near-singular tile** (smallest `eigmin(Q_post)`): drawn unconditionally, its huge
    near-null draw is a toxic anchor (measured **31×** rel rooting there, vs 0.36–0.84 at any
    better-conditioned root). `_condition_root_scores` = `-eigmin(Q_post)` per tile; the tree roots
    at max-eigmin. **Negative control (must stay in the gate):** rooting at the worst-conditioned
    tile blows up >1.5× the well-conditioned roots — a future refactor that roots arbitrarily
    reintroduces the 31× and fails loudly. `eigmin` ≠ accuracy-rank among the *non-toxic* roots, but
    it cleanly avoids the toxic one.
  - **THE CONDITIONING FLOOR (the central finding; a characterized `known_bias`).** With every
    topology issue fixed, an elevated cross-seam residual remains around a near-singular tile and
    **no tree removes it** — it is not topology, it is that conditioning a tile with `eigmin≈2.5e-7`
    onto anything is ill-posed, and hand-forward inherits that. Measured: the residual is **MONOTONE
    in `eigmin(Q_post)`** (`[0.706, 0.624, 0.551]` as eigmin rises) and **`tree_edge == chain_edge`
    EXACTLY at equal conditioning** — i.e. the tree sweep is NOT worse than the plain chain on a
    near-singular tile; the chain pays the identical floor. The gate therefore compares each tree
    edge to the **per-tile conditioning-matched chain baseline** (`matched_chain_edge_baseline`,
    same tile, same eigmin), not to an easier well-conditioned chain — like-for-like, so the floor is
    not mistaken for a defect, while a multi-hop tree degrading past the fresh chain conditioning
    still fails.
  - **Gate (Task 9, three coupled assertions, PASSED):** (1) `max_tree_edge ≤ matched_chain·1.15`
    (hand-forward no worse than chain at equal conditioning); (2) `max_dropped ≤ max(2.5·max_tree,
    matched_chain)`; (3) conservative direction (median seam firstdifference variance ratio vs the
    single-tile reference) `≥ 0.9` — never under-dispersed. Plus two-tree invariance (well-conditioned
    roots agree + worst-root 31× negative control) and the nonstationary-κ case. Conservative
    everywhere, bounded under eigmin-rooting, chain-quality where conditioning allows.
  - **PHASE-5 OPERATIONAL WARNING (the bridge — do not let the tuner re-derive this arc).** The
    coherent sampler's accuracy floor is a **function of `eigmin(Q_post)`, which the `range`
    parameter controls**: short range → near-improper posterior → eigmin↓ → the cross-seam residual
    rises toward the 2.2 / 31 seen when unguarded. **The Phase-5 autotuner MUST treat cross-seam
    coherence residual as a CONSTRAINT, not a free variable** — searching `range` down drives the
    posterior into the regime this whole arc characterized. **Junction-tree (spec §6) is the
    documented exact escalation** for the short-range regime where the floor exceeds tolerance; it
    was deliberately NOT built now (measured proof it is unneeded at tested conditioning: 3 of 4
    trees nail 0.30 with zero cycle correction, and tree==chain at equal conditioning — cycle
    exactness is not what is broken; the floor is intrinsic).
  - **Obsolete (removed):** `_draw_joint`/`_strip_prior`/`_interiorness` (synthesized strip field,
    disproved 376×); the Kruskal `_max_overlap_spanning_tree` is retained only for the Task-6 unit
    tests — the SHIPPED selection is `_min_eccentricity_spanning_tree(adjacency, n, root_score)`.

## Cross-cutting decisions (canonical — Phase 3)

- **Two-point dispatch split (load-bearing).** Reduction strategy is selected by the LIVE
  operator's `representation` (pre-persistence): `select_reduction(dist)` in
  `distributions/reduction.py` reads `getattr(dist.cov_op, "representation", "lowrank+diag")`
  → `LowRankReduction` ("lowrank+diag") / `GMRFPrecisionReduction` ("sparse-precision"), or
  `EmpiricalReduction` when there is no operator. The coherence driver is selected by the
  PERSISTED `sampler_spec` (post-persistence): `select_driver(sampler_spec)` in `coherent.py`
  → `LowRankSharedBasis` / `GmrfPrecisionSolve` / `PerturbEnsembleDegradation`. Never dispatch
  on method identity.
- **`to_persisted` is NOT on the core Protocol.** §5.4's illustrative on-`CovarianceOperator`
  signature was self-inconsistent (it returns a `distributions/` type from `core/`, breaking
  the one-way `application/→distributions/` rule, and modifies the Protocol, violating
  invariant 1). Realized as the `ReductionStrategy` Protocol in `distributions/reduction.py`,
  selected by representation. Operators carry a `representation` class attr only (not on the
  Protocol). Spec §5 permits this ("signatures illustrative; correct where it differs").
- **GMRF reads off the precision via a `Projection`.** Precision-node space and output-grid
  space kept distinct even though they coincide on a regular grid. `mean→W·mean`,
  `cov→W Σ Wᵀ` (Σ = selective-inverse entries in W's stencil, never dense). Grid block =
  `GridIdentityProjection` (W=identity-on-nodes); off-grid = `BilinearProjection`; `A`
  (grid→obs conditioning) is itself a projection into node space. A later FEM phase supplies
  a new `Projection` + mesh-assembly only — precision rep, coherence driver, persistence, and
  blend untouched. (Recorded in `phase3_scope_spec.md` §5.1.)
- **GMRF time = temporal taper into R (not a temporal SPDE axis).** `Q_post = Q_prior +
  AᵀR⁻¹A`; R per-obs variance inflated by `exp(|t_obs−t_out|/temporal_taper_scale)`; the
  taper scale is a tunable in `parameter_space()` resolved via the provider. Conservative
  diagonal-R approximation (under-uses temporal structure) recorded as a `known_bias`. The
  OI-vs-GMRF asymmetry (OI = full space-time kernel; GMRF = spatial cov + tapered likelihood)
  is deliberate and read into the Stage-B comparison.
- **One sparse factor serves all three (invariant 6).** `GMRFFactor` (CHOLMOD simplicial)
  serves `sample` (L⁻ᵀw), `solve` (posterior mean), and the hand-rolled Takahashi selective
  inverse (`diag(Q⁻¹)` + adjacent entries on the L+Lᵀ pattern). Dense `Q⁻¹` exists ONLY as a
  small-grid test oracle. Adjacency precondition (W's 4-node stencil + firstdifference's
  adjacent-node cov inside the selective-inverse pattern) is asserted — guards a future wider
  κ-stencil from silently breaking eval var / cancellation.
- **GMRF eval-point OSE blend = moment crossfade.** GMRF has no low-rank eval factor; cross-
  tile eval-point scoring uses `mean=Σwμ`, `var=(Σwσ)²` (exact per-tile var from Takahashi).
  Cross-eval-point covariance in overlaps is NOT represented (not consumed by per-point OSE
  accuracy/calibration) — recorded in provenance (`eval_point_cov` marker), a flag not a
  hidden assumption. Full coherent eval-point GMRF sampling is out of Phase-3 scope.
- **α = 2 (ν = 1)** fixed integer smoothness — the canonical `(κ²I−Δ)` 5-point stencil
  squared. Continuous ν deferred to Phase 4.
- **GMRF cross-tile coherence = conditioning-by-kriging, NOT native shared-w (amendment, spec
  §5.3.1).** The Checkpoint-2 "GmrfPrecisionSolve: mean + L⁻ᵀw, native shared-w" line was wrong
  for non-identical Q — `L⁻ᵀ` is a global map, so shared factor-space white noise yields
  decorrelated physical fields across distinct tiles (proven by a distinct-tiles positive
  control: overlap corr ≈0 at all halos; cross-seam derived-quantity error −0.51). Fix:
  **conditioning-by-kriging** `x_c = x_u + Σ_cross Σ_shared⁻¹ (x_shared − x_u|S)`, each tile
  conditioned toward ONE global node-space realization via a single forward sweep
  (values-handed-forward, NOT seed-shared; transitive by construction for a tile chain).
  Cross-cov blocks `Σ_{·,S}` = full `Q⁻¹` columns via **factor back-solves** (outside Takahashi's
  pattern; computed once per tile, reused across members). **Validity invariant:** corrected
  draws are exact posterior samples (kriging-preserves-conditional-law theorem), verified by a
  **joint-covariance** oracle on a dense small grid — marginal checks are the blind spot.
  **Separator precondition (asserted, checked):** the handed-forward overlap must Q-graph-separate
  processed/unprocessed interiors (overlap ≥ stencil reach = 2 for α=2; the `k·corr_len` halo
  policy satisfies it); a negative control proves the joint law breaks when it doesn't. **Exact
  only for tree-structured tile adjacency** — 2-D/FEM (Phase 4) needs the documented
  pre-drawn-joint or junction-tree variant. The marginal `σ=Σwσ` bound is unchanged
  (pointwise-conservative; only the *sampler* changes). Plan:
  `docs/superpowers/plans/2026-06-25-phase3-task9-gmrf-kriging-sampler.md`.

## Cross-cutting decisions (canonical — Phase 2)

- **Coherent-sample structured driver = shared-overlap-basis (Löwdin), NOT member-only z_r.**
  The design's default Option-1 (member-only `z_r` applied to each tile's own factor) was
  escalated and rejected at the Stage-A gate (design §8). Diagnostics proved it was NOT a
  sampler bug (diagonal exact; core/aligned ≈ MC floor) but a genuine, *large, k-independent*
  basis-orientation residual: each tile builds an independent rank-20 randomized-SVD basis, so
  the structured factors are ~orthogonal across tiles (structured ratio ≈ 0.39) and member-only
  `z_r` makes them add as if independent → coherent samples underdispersed ~40–67% vs the
  reported cheap-path variance, *growing* with k. Fix (`coherent_structured_field` in
  `distributions/coherent.py`, used by `BlendedDistribution._coherent_member`): project every
  tile factor into ONE common orthonormal basis `Q` (QR of the stacked factors over the
  support), take the symmetric square root `Aᵢ=(QᵀFᵢ Fᵢᵀ Q)^½` to strip the SVD rotational
  ambiguity, and drive `G=Σ wᵢ Q Aᵢ` with ONE shared member-seeded latent `g`. Result: cheap≈
  sampled rel 0.45→0.03 and k-direction flipped growing→flat; cross-seam derivative recovers.
  The reported marginal (`BlendOperator.blend`'s `(Σwσ)²`) is UNCHANGED (still conservative;
  Task-3 cheap path untouched) — only the *sampler* changed. `MemberSeededZr`/`realize_one`
  remain for single-tile use. If Stage B's larger overlaps degrade `Q` conditioning, the next
  lever is the retained per-tile rank, NOT the driver (owner directive).
- **`run_tiled_pipeline`** (`application/pipeline.py`) reuses Phase-1 `_prepare`/evaluators:
  per-tile obs windowed to `extended_window`, eval locations windowed per tile, one submit per
  tile via the existing `Executor`, grid blend + OSE eval-point `PointSet` blend, then the
  Phase-1 `Registry`. OSSE scores the blended grid vs truth; OSE scores blended eval-point
  predictives vs withheld CryoSat-2. `UnitOfWork.obs` relaxed to `ObsWindow | None` (None only
  for obs-less coordinator probes in tests; real solves always set it).

## Gotchas

- **A LOG-GROWTH STALL WATCHER IS BLIND TO `pytest -q` (2026-08-30).** The T5e gate suite
  ran green in 44:22, and the watcher reported **`STALL: log unchanged for ~20 min`**
  anyway: `pytest -q` under `pixi run` with output redirected is BLOCK-BUFFERED, so the
  log grows in one burst at the end. The completion signal (pid exit) was correct; the
  growth signal was a false alarm. **Do not tighten a stall threshold against this — it
  cannot be made true.** Either run the suite unbuffered (`PYTHONUNBUFFERED=1`, without
  `-q`, so per-file progress lines land as they happen) or watch pid liveness only and
  accept that a hung suite is caught by wall-clock, not by silence. The earlier lesson
  still stands for solve legs, which DO emit heartbeats.

- **`.git/hooks` IS NOT VERSIONED — the "hook pushes on commit" belief was false
  (2026-08-29, owner pins 102 + 104).** There was never a post-commit hook on this box;
  commits stayed local while every report line said "everything is on origin", and
  **absence looked exactly like success**. ⛔ **This is now a PROTOCOL step, not a
  gotcha** (pin 104: a note here is prose a fresh session may read after it has already
  committed) — `CLAUDE.md` step 0 and `docs/project-context.md` §10 both run
  `sh scripts/resume_checks.sh` first, which REPORTS hook presence, any
  `.git/UNPUSHED_COMMITS` marker, local-vs-**remote** head via `ls-remote`, and tree
  state, exiting non-zero on any of them. Kept here only as the trail: **verify against
  the REMOTE**, never `git rev-parse HEAD` alone — that is precisely the check that
  cannot see this failure.

- **A pin-42-style "required schema field" must round-trip through JSON (2026-08-29).**
  `S_STAR_CHI2_IDENTITY` first carried its `fields` entry as a TUPLE; the in-memory row
  and its stored copy then compared UNEQUAL (tuple vs list), which is how the
  programmatic-path test caught it. Any constant embedded in an evidence row uses JSON
  types only, and is copied into a fresh container per row so a caller's mutation cannot
  leak into the next tile's row.

- **The σ route's floor is the ENSEMBLE, not the solver — CRN is keyed to the basis
  ORIGIN, not to the ocean (2026-07-27, `phase14.stage1.seam_sigma_diagnosis`).**
  T4's PAIR/σ `R_seam_sigma = 1.1044` (ELEVATED) beside PAIR/mean `0.0827` (CLEAN) is
  ensemble Monte-Carlo noise, not a seam artifact — CONFIRMED on four lines, the
  decisive one being a within-tile 50/50 member half-split (no seam crossed at all)
  that disagrees **more** than the two tiles do: seam_n 0.005182 m, seam_s 0.005289 m
  against the predicted `σ/√(50−1)` ≈ 0.00527 m, vs the cross-tile 0.003607 m ≈
  `σ/√(99)` = 0.003708 m. **Mechanism (the part to remember):** `miost_crn.coef_noise`
  keys the perturbation on pavement-lattice `(ix, iy)` measured from
  `BasisSpec.(x0_km, y0_km)`, and every tile sets `basis_domain` from its OWN
  `solve_bbox` lower-left corner. So two tiles whose solve boxes start at different
  corners draw INDEPENDENT coefficient perturbations for the same physical element
  (seam_n vs seam_s: 334 km offset, not a multiple of any rung's lattice step — the
  two pavements share *zero* element centres), while two boxes sharing a corner draw
  the IDENTICAL ones (seam_s and the seamless anchor both start at lat 33 → their σ
  fields agree to 0.00025 m, 14× closer than seam_n's). Consequences: (a) any σ
  comparison between differently-origined solves carries a `σ/√(m−1)` floor —
  at m=100 that floor is comparable to `D_int_sigma`, so **`R_seam_sigma` at m=100 has
  little resolving power and a σ-route reading near 1 means "at the noise floor", not
  "seam"**; (b) an anchor-vs-tile σ agreement can be spuriously *good* purely from a
  shared origin — never read it as validation; (c) the mean route is unaffected (it
  localises correctly: a V with its minimum at the shared core boundary, 81% spread
  across the strip, vs the σ route's flat ±7%). Diagnosis only — nothing was tuned and
  the sealed rubric row stands as recorded; reproduce with
  `pixi run python scripts/phase14_sigma_diagnosis.py`.
- **mypy runs `mypy .` (whole tree, tests included)** via the pre-commit hook — test files
  must be type-clean too (e.g. assert `x is not None` before using an `Optional`). numpy ops
  often infer `Any`; wrap returns in `np.asarray(...)` to satisfy `no-any-return`. scipy/dask/
  distributed calls need `# type: ignore[import-untyped]` / `[no-untyped-call]`.
- **Plan deviations made & verified:** (1) Task 10 perturb_and_ensemble seeds members from the
  caller seed + index, not `id(obs)` (the plan's id-based seed broke the reproducibility test).
  (2) Task 19 CRPS test: the plan's expected `0.23379` is CRPS at y=0, but the test uses y=0.5;
  correct closed-form value is `0.331404`. Implementation formula is the standard correct CRPS.
  (3) Task 19/21: evaluators take `result: object` (not `dict[...]`) so they conform to the
  `Evaluator` protocol and can go into `Registry([...])`. (4) Task 21 `_evaluate`: OSSE runs
  calibration on the gridded truth (the plan only set TRUTH, so Calibration — which needs
  WITHHELD_OBS — would never fire and the OSSE acceptance demands reduced_chi2/coverage); OSE
  withholds CryoSat-2 by mission-splitting the obs window (the test passes a plain FixtureSource
  with no `withheld()` method, so withholding must happen in the pipeline, not the source).

- **Task-1 deviation (verified):** `.gitignore` never ignored `__pycache__`/`*.pyc`, so Phase 1
  left 77 `.pyc` files tracked. The rename swept them in; untracked them (`git rm --cached`) and
  added `__pycache__/`, `*.pyc`, `.mypy_cache/` to `.gitignore` so the soon-public repo stays
  clean. `pixi.lock` (593 KB) exceeds the 500 KB hook only under `--all-files`; it is unmodified
  so the staged-only commit hook passes.
- The 11 GB NATL60 reference is hourly — never pull it; use the daily file. Footprint stays a
  few hundred MB.
- NATL60 challenge has no observation error ⇒ `R` ≈ a nugget for the oracle.
- `pyinterp` / `GPSat` are NOT installed; Method 1 needs none. `pixi add` any new dep.
- BLAS/OpenMP env vars must be set per-worker *before* numpy/BLAS loads (Nanny child env).
- **Phase-2 Task 11 deviation (verified):** `ScaleAwareHalo.halo_for` evaluates the
  correlation length at the band's *equatorward-most* latitude (`clamp(0, lat_lo, lat_hi)`),
  not at the band's lat nodes as the plan literal showed. The plan test asserts the halo for
  band (-5,5) equals `k*800` (equator cl), which the node-based version (cl at ±5 ≈ 797)
  would miss. Correlation length is monotone-decreasing in |lat|, so the widest over a band
  is at min|lat| — this is the correct "widest over the core band".
- **Phase-2 Task 6 deviation (verified):** `FirstDifference._diff_var` calls
  `dist.covariance(a,a/b,b/a,b)` node-by-node; the naive general-path covariance
  (regenerate 256 members per query point) made the composition test take 67s. Fix:
  `BlendedDistribution.covariance` now snaps query points to nearest grid nodes and reads
  from one cached `_grid_sample_batch(256)` realization (lazily computed, memoized on the
  instance). 67s → ~4s. Snapping is consistent with `PersistedDistribution.covariance`
  (which also snaps via `_idx`); fine for grid-node derived ops. The plan explicitly
  allowed this fast path (Task 6 Step 3).

- **Phase-3 Task-7 addition (verified):** `solve_unit` (`application/solve.py`) now dispatches the
  base distribution on `unit.base_fields` type — `PrecisionFields → PrecisionDistribution`, else
  `PersistedDistribution`. The plan's Task-7 file list omitted solve.py, but widening
  `ReducedUnit.base_fields` to `PersistedFields | PrecisionFields` forced it (and it is *required*
  for genuine-first-class GMRF to flow through the executor into the Task-9 blend as a
  `PrecisionDistribution`, not silently wrapped in `PersistedDistribution`). `PerTimeProduct.base`
  is typed `Any`, so no product-type churn. `PrecisionDistribution._factor_obj` is annotated via a
  `TYPE_CHECKING` import of `GMRFFactor` (ANN401 forbids `-> Any`); the runtime import stays lazy so
  `persisted.py` does not hard-require sksparse.
- **Phase-3 Task-5 deviation (verified) — sksparse 0.5.0 has a NEW scipy-style API.**
  `pixi add scikit-sparse` installed **scikit-sparse 0.5.0**, a rewrite — NOT the classic
  0.4.x `Factor` object the plan assumed. The plan's `cholesky(Q, ordering_method=..., mode=
  "simplicial")` + `factor.L_D()`/`.P()`/`.solve_Lt()`/`.apply_Pt()` DO NOT EXIST. Real API:
  `from sksparse.cholmod import cho_factor`; `cf = cho_factor(Q, order="amd", lower=True)`
  returns a `CholeskyFactor` with `cf.L` (sparse lower, `L Lᵀ = Q[P][:,P]`, `is_ll=True` for
  SPD), `cf.D`, `cf.perm` (the permutation P, factor is of the *permuted* matrix
  `Q[perm][:,perm]`), `cf.solve(b)` solves `Q x = b` (perm internal), `cf.is_ll`.
  `GMRFFactor` (`methods/gmrf_linalg.py`) wraps this: deterministic perm via `order="amd"`;
  one lower `Lc` (`cf.L`, or `cf.L·√diag(D)` if a future matrix factors LDLᵀ) drives sample
  (`spsolve_triangular(Lcᵀ, w)` then scatter `x[perm]=y`), Takahashi, and the back-map.
  **Permutation back-map indexes by `perm` directly** (NOT `argsort(perm)` as the plan's snippet
  did): original entry `(perm[k], perm[l])` carries permuted value `(k,l)`. Pinned correct by
  the dense-Q⁻¹ oracle (diag + adjacent rtol 1e-9). Takahashi recursion math is verbatim plan.
- **Phase-3 Task-2 deviation (verified):** widening `BlendInput.distribution` to the abstract
  `PredictiveDistribution` protocol (which declares only `grid`/`provenance`/`marginal_variance`/
  `covariance`/`sample`/`regrid`) means the duck-typed `.fields`/`.time_days` reads in `blend.py`
  (`_constituent_moments`, `_coherent_member`, `BlendOperator.blend`) need `cast(Any, dist)` to
  pass `mypy .`; the `PersistedPoints` eval-point constituent in `pipeline.py` is `cast(
  PredictiveDistribution, pp)` at the `BlendInput(...)` call (it exposes the fields by duck
  typing but isn't a structural match). The Stage-A seam test imports `_nearest` from
  `distributions.coherent` (where it now lives) not `distributions.blend` — mypy's
  `--no-implicit-reexport` rejects the re-exported name. The plan literal said import from blend;
  importing from coherent is equivalent (same function) and the only change vs the plan text.

- **Phase-3 Task-9b finding (load-bearing) — GMRF kriging sweep uses INDEPENDENT per-tile
  white, NOT the shared-lattice `diagonal_noise`.** The kriging theorem requires each tile's
  *unconditional* draw to be independent of the handed-forward target values. The old
  native-shared-w mechanism shared white across tiles by global cell, which correlated each
  tile's draw with the targets and **biased** the correction (spurious long-range correlation;
  the per-tile-validity oracle caught it). `GmrfKrigingSolve._sweep` now seeds white per tile via
  `derive_seed(method, params, f"gmrf-tile:{pos}", member)`. The single-tile coherent-member
  tests assert against this per-tile white (NOT `diagonal_noise`). `diagonal_noise` is still used
  by `LowRankSharedBasis` (OI), unchanged.
- **Phase-3 Task-9c finding — negative-control fixture limitation (recorded so 9d/Phase-4 don't
  re-derive it).** The separator assertion (`overlap ≥ reach=2`) is a STRUCTURAL *sufficient*
  condition for joint exactness at all κ — correctly conservative. Demonstrating "1-col overlap →
  wrong joint" with the exact-marginal fixture is regime-dependent: at well-conditioned κ (≈0.7)
  a 1-col overlap is *benign* (short correlation ⇒ the distance-2 precision edge barely affects
  the joint), and the long-correlation regime where it genuinely breaks makes the
  `inv(Σ_global[tile,tile])` construction ill-conditioned (double-inverse of a near-singular Σ).
  So `test_separator_negative_control` proves wrongness via the **weighted-blend seam-column
  collapse** (a 1-col overlap leaves no room for the partition-of-unity crossfade → seam variance
  collapses; joint Frobenius ≫ MC) **plus** the assertion firing — both real reasons the
  `≥reach` policy holds. The positive joint-cov oracles (≥2-col) match global EXACTLY; the chain
  construction is sound.

## Deferred items / open questions

- **seam_metrics zero-dispersion refusal (T10 review LOW, 2026-07-25):** a
  constant interior gives `d_int == 0.0` → bare ZeroDivisionError instead of
  a named refusal, on BOTH routes (pre-existing from T0's sealed mean route;
  the σ route mirrors it deliberately — fixing under T10 would have touched
  sealed semantics). Fix as its own small task when seam code next opens:
  named refusal ("zero-dispersion interior — R undefined"), both routes,
  test-pinned.

- ~~**Phase-10 = lat-varying METHOD parameters (invariant-12) — deferred TO Phase 10,
  owner-committed.**~~ **RETIRED 2026-07-15:** executed as Phase 10 and closed with the
  pre-registered NEGATIVE result (measured, not shipped) — see the Phase-10 close banner
  at the top of this file. G-shrinkage finding recorded there; no duplicate content here.

- ~~**Evaluator-registry standalone phase (owner-electable, no method work, no c2):
  GroundTrack rebuild + spectral-fidelity evaluator + report-only registry wiring +
  retroactive one-shot on shipped/signed mean maps + selection-Policy seam extraction.**~~
  **MIGRATED 2026-07-15:** elected as Phase 11; the finding's WHAT-REMAINS content is
  migrated into `docs/superpowers/specs/2026-07-15-phase11-evaluator-wiring-design.md`
  (owner-approved design; forks a–e + batch pins decided there). The dated
  ARCHITECTURE-AUDIT FINDING block above stays as the historical record.

- **Next release — relax the conda recipe Python cap.** `pyproject.toml` now declares
  `requires-python = ">=3.12"` (cap dropped, commit `e236591`; source uses only stable stdlib
  and numpy/scipy/pyproj all ship cp314 wheels). The **0.1.0** recipe deliberately keeps
  `run: python >={{ python_min }},<3.14` to match the already-published 0.1.0 wheel (building
  0.1.0 on 3.14 would fail `pip install .` — its metadata excludes 3.14). On the next release:
  when the autotick bot opens the feedstock bump PR, drop the `,<3.14` from the `run` pin
  (→ `python >={{ python_min }}`) and mirror the same in `conda-recipe/meta.yaml`. Do NOT do
  this before a `>=3.12` wheel is on PyPI.
- **Optional:** `pixi.toml` dev pin still `python = ">=3.12,<3.14"` (left capped to avoid a
  `pixi.lock` re-solve; doesn't limit the published package). Relax only if CI should exercise 3.14.
