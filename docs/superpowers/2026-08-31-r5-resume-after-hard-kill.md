# R5 — resume-after-hard-kill, measured to bit-identity (owner pin 117)

**RESULT: PASS on the ruled bar — the resumed run is BIT-IDENTICAL to the uninterrupted
one.** Two findings ride alongside it, both about SCOPE rather than correctness, and one
methodological failure of my own is recorded in §4 because its green line was nearly
believed.

## 1. Configuration (cheap by construction, pin 117e)

Production path — `_tile_framed_obs` → `_seam_miost` → `merged_members` — at
deliberately small scale via `scripts/phase14_r5_resume_probe.py`:

| | |
|---|---|
| tile | `kuroshio` (a diverse tile, 117a; the leg-1 subject) |
| members | **m = 2** |
| windows | **1** (`w+00000.0+60`, the production 60-day length) |
| framed obs | 138 518 |
| solve grid | 96 × 97 |
| PCG cap | 1200 (the production `STAGE1_PCG_MAXITER`) |
| CRN root | 436225428909570549 (`derive_seed`, production convention) |

## 2. What was run

1. **Baseline, uninterrupted** — 876 s. η `baa019b3c9bff619…`, anomaly
   `e2848ffebed76764…`, PCG **[mean 437, member-batch 474]**, both converged.
2. **Hard kill, mid-window** — same configuration, fresh checkpoint directory. Launched
   under `setsid`; killed with `kill -9` on the **process group** once the per-window PCG
   checkpoint existed plus 45 s. The checkpoint is written every 50 iterations *inside the
   member-batch solve*, so its existence is what makes this mid-window and not a boundary
   (117c). Process group at kill time: `pixi` (654469) + `python` (654518).
   - **survivor check: no solver process survived the kill**
   - **the killed run's log contains no completed-record line** — it never finished
   - **checkpoint readable after the hard kill: `it = 50`**
3. **Resume** — same checkpoint directory, 653 s, completed.
4. **Compare** — `eta IDENTICAL`, `anom IDENTICAL`, PCG iterations `[437, 474]` on both
   sides.

**Bar met: BIT-IDENTICAL, not merely "resume completed" (117a).**

## 3. Two findings about SCOPE — the mechanism is sound, its reach is small

### 3a. The checkpoint covers ONE SOLVE, not the leg — measured

`MiostSolver.solve` checkpoints the PCG state of the solve in flight, and
`merged_members` holds each completed window's coefficients **in memory** until the leg
writes its own member store after *all* windows. So a hard kill recovers only the current
solve's iterations:

- This kill landed at member-batch iteration **50 of 474** → the resume recovered ~10 % of
  that solve.
- The **mean leg (437 iterations) was already complete in memory and was re-solved from
  scratch** — visible in the timings: 653 s resumed vs 876 s uninterrupted, a saving of
  223 s where the checkpoint's own contribution was 50 iterations.
- **Completed windows are not checkpointed at all.**

**Consequence for a 9-window production leg** (~3.44 h/window measured at m=100, pin 89):
a hard kill at window *k* re-solves windows 1…*k*−1 in full. **A power event at hour 30 of
a 31 h leg costs ~30 h, not ~0.** Resume protects against losing the *tail* of one solve;
it does not protect a leg. Stated plainly because R5 was raised to decide whether 31 h legs
are safe to launch, and "resume works" answers a narrower question than the one asked.

### 3b. The checkpoint write is not atomic

`np.savez(checkpoint, …)` writes **directly to the final path** — no temp file, no rename.
The file is ~23 MB. A kill landing inside that write leaves the *only* checkpoint
truncated, and the resume then either refuses (RHS-hash mismatch) or fails to load. This
run's kill happened to land clean; the window in which it would not is ~the write
duration, every 50 iterations. **Not fixed here** — it is a change to shipped solver code
whose behaviour is pinned elsewhere, and it is the owner's call whether it is worth doing
before leg 1.

## 4. Attempt 1 was INVALID, and the failure is recorded because its green line was nearly believed

The first attempt used `pgrep` to find the process to kill. It returned the **pixi
wrapper**; the solver survived, ran to completion (its log carries
`record -> logs/r5/resumed.json (728s)`), and the "resume" process ran **concurrently
against the same checkpoint path**, overwriting the record 11 s later. The comparison then
printed `BIT-IDENTICAL` — from a run that had never been killed.

The script's own `WARNING: still alive` line said so two lines above the green result.
**E-16 §6 already records this exact trap** — *"watch the PID captured at launch — `pgrep`
has twice returned a wrapper rather than the long-lived process this session"* — and it was
walked into anyway.

Attempt 2 removed the ambiguity structurally rather than by care: `setsid` + a
**process-group** kill, a **survivor check** that exits non-zero if anything is still
alive, and an assertion that the killed run's log carries **no completed-record line**.
Each failure mode exits with its own code, so a broken test names itself instead of
degrading into a green line.

## 5. What this does NOT establish

- Nothing about resume across **windows** — see 3a; that path does not exist.
- Nothing at production scale: m=2, one window. The *mechanism* is the same code; the
  *cost* profile is not (117e forbade scaling it up, and correctly).
- Nothing about the checkpoint surviving a kill during its own write (3b).
