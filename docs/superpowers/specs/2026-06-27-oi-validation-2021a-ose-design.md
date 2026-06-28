# Design — OI validation against the 2021a SSH-mapping OSE challenge (BASELINE row)

**Status:** approved design, pre-plan. Scope source of truth: `validation_scope_spec.md`
(the falsifiable claim, the pinned decisions, the grounded repo facts). This document is the
*how*; the scope spec is the *what* and *why*. Read both before planning.

**The claim under test (unchanged, falsifiable):** our OI engine, configured from the
challenge's own `baseline_oi` covariance parameters, on the 2021a Gulf Stream box
(lon 285–315°E, lat 23–53°N, eval year 2017), mapping the FIVE-mission constellation
(SARAL/AltiKa, Jason-2, Jason-3, Sentinel-3A, Haiyang-2A — Cryosat-2 WITHHELD), scored by the
challenge's own `src`/`example_data_eval` against the withheld Cryosat-2 track, reproduces the
published leaderboard **BASELINE (OI)** row: µ(RMSE) ≈ 0.85, σ ≈ 0.09, λx ≈ 140 km.

---

## 0. The load-bearing premise (the throughline of this whole design)

The riskiest assumption of the entire validation is **"their eval code is ground truth and we
can drive it."** Everything downstream — adapters, OI config, the result table — is plumbing we
know how to do. So the design front-loads the proof of that premise into **Task 0**: before any
adapter is built, import their scoring function, run it on *their own* shipped BASELINE map, and
reproduce *all three* published numbers (µ, σ, λx) at the pinned commit. If that passes, the
risky part of the project is de-risked on day one. If it fails, we've found the real shape of the
work — a version mismatch, an import wall, or a configuration skew — before building on a false
floor. This is the project's standing instinct (prove the load-bearing assumption with a
measurement before building on it) applied to the one assumption this run rests on.

---

## 1. Architecture

New package `src/sverdrup/validation/` (importable, under full test-design / mypy / ruff
discipline — chosen over a top-level harness dir for clean reuse of internal types). Eight
focused modules, each one clear purpose, well-bounded interface.

| Module | Purpose | Reuse / net-new |
|---|---|---|
| `config.py` | `.env` load (python-dotenv) → pydantic `ValidationConfig` (AVISO creds, `AVISO_ACCESS_METHOD`, paths). **Fail loud** with a clear message if `AVISO_USERNAME`/`AVISO_PASSWORD` are empty when an authenticated path (`thredds`/`ftp`) is selected. | net-new |
| `access.py` | THREDDS OPeNDAP/FileServer fetch over HTTPS; `httpx` Basic Auth; generate `~/.netrc` + `~/.dodsrc` if the netCDF-C OPeNDAP stack requires it; `meom_mirror` + `ftp` fallbacks. **First action: verify the live catalog URL + the exact auth mechanism (Task 0).** `stamina` retry on transient faults — reuse the `_is_retryable` predicate pattern from `adapters/odc/download.py`. | net-new, follows odc pattern |
| `input_adapter.py` | The five-mission L3 along-track NetCDF → our `ObsWindow` (`core/observations.py`). Cryosat-2 loaded into a **separate eval-only** structure that the mapping path cannot read. Spin-up window (obs from 2016-12-01) included in input, excluded from eval. Reference-frame handling (SLA vs SSH, MDT) explicit per the Task-1 audit trail — see §5. | reuses `core/observations` |
| `output_adapter.py` | Our gridded OI map → `xarray.Dataset` → NetCDF matching `OSE_ssh_mapping_BASELINE.nc` **field-for-field**: dimensions, coordinate names/order, the SSH variable name + units, the time axis, fill/mask conventions. Their eval must ingest our file unchanged. Schema captured from the shipped file in Task 0. | net-new (no xarray NetCDF writer exists today — current output is `.npy` + JSON manifest) |
| `params.py` | `baseline_oi.ipynb` parameters → our OI `ParameterProvider` + `GridSpec` + temporal window (`methods/oi.py`, `methods/kernel.py::Matern32SpaceTime`). Emits the **PARAMETER AUDIT TRAIL** (committed markdown: each extracted value → its notebook cell/line → our setting). | reuses `methods/oi`, `kernel`, `core/parameters` |
| `run.py` | Drive 2017 over the single tile: sliding temporal-window batches over `OptimalInterpolation.solve` → daily maps → `output_adapter`. Cadence + window length finalized in Task 1 from the extracted params. | reuses `application/pipeline`, `solve` |
| `their_eval.py` | Import the vendored challenge `src` scoring functions; run on (a) our map and (b) the shipped BASELINE map → (µ, σ, λx). **This is the ground-truth scorer.** Highest-risk integration point — proven first in Task 0 (§0, §4). | imports vendored `src` |
| `report.py` | Our `eval/aggregate.py::area_weighted_rmse` on the same map (parallel cross-check); assemble the result table + the decomposed read (§6). | reuses `eval/aggregate` |

### Vendoring the challenge repo
Git submodule `vendor/2021a_SSH_mapping_OSE` (MIT), **pinned to the commit/release that
corresponds to the published leaderboard** — not bare master HEAD. See §3 (version skew). The
pinned SHA is recorded in this repo (submodule gitlink + a one-line note in the audit trail).
`their_eval.py` imports their scoring functions from that path.

### Data discipline
Bulk challenge data gitignored under `data/2021a_ssh_mapping_ose/` (per
`gitignore_additions.txt`). Commit **one small real fixture** (a short subset NetCDF — a few days
of one mapping mission's L3 plus a Cryosat-2 slice, and a small/clipped BASELINE-schema sample)
for offline tests. The shipped `dc_maps/OSE_ssh_mapping_BASELINE.nc` and `mdt.nc` are the
challenge's own provided references.

---

## 2. Data flow

```
.env ── config ──> access ──> fetch: 5-mission L3, Cryosat-2 (separate), shipped BASELINE.nc, mdt.nc
                                 │
                input_adapter ──> ObsWindow (5 missions; spin-up included)   Cryosat-2 ──> eval-only track
                                 │
                  run.py: OI over 2017, single tile ──> daily maps ──> output_adapter ──> our NetCDF
                                 │
        their_eval ──> run THEIR scorer on { our map, shipped BASELINE map } ──> (µ, σ, λx) × 2
                                 │
              report ──> our area_weighted_rmse on the same map (cross-check delta)
                                 │
            result table: ours ∥ BASELINE 0.85/0.09/140 ∥ DUACS 0.88/0.07/152
                          + reproduced-published-BASELINE sanity anchor (µ, σ, λx)
                          + parallel-eval delta + parameter audit trail
```

---

## 3. Version skew — the eval code must match the leaderboard's

Their `src` scoring functions are imported as ground truth, but the published numbers
(0.85/0.09/140) were produced by their eval code **at the version that generated the
leaderboard** — not necessarily master HEAD. If we pin to a drifted HEAD whose eval differs, the
"reproduce the published BASELINE number from their map" sanity anchor can fail *not* because we
drive their eval wrong, but because their current eval produces a different number than the
leaderboard was computed with. That corrupts the decomposition: case (ii) "harness bug" would
fire when there is no bug, only version skew.

**Decision:** pin the submodule to the release/commit that matches the published leaderboard
(candidate: the repo's tagged release "Material for SSH mapping OSE data challenge", ~Sep 2021 —
**VERIFY against the live repo; the source wins**). Record which commit was pinned. Make
*"the pinned eval code reproduces the published BASELINE numbers (µ, σ, λx) from the shipped
BASELINE map"* an explicit **Task 0** check, not just a Task 3 one. If it does not reproduce at
the pinned commit, the fix is choosing a different commit — and we must know that before building
anything. This is the same "verify the reference is what you think it is" move the whole project
runs on, applied to the eval code's version.

---

## 4. `their_eval.py` is the highest-risk integration point — spike it in Task 0

"Import their `src`, run on our map" hides real risk: 2021-era code carries its own dependency
expectations (specific xarray/numpy/pyinterp versions, its own NetCDF-reader assumptions) and its
scoring functions may expect input shapes/conventions that aren't documented.

**Task-0 feasibility spike (the single most important Task-0 deliverable):** actually import one
of their scoring functions and run it **end to end on their own shipped BASELINE map**, before
any adapter exists. One check validates four things at once — the submodule, the import path, the
version pin (§3), and the ground-truth premise (§0):

> *Their scoring function imports, runs on their own BASELINE map, and reproduces the published
> BASELINE numbers (µ, σ, λx).*

If it passes, the risky part of the project is de-risked. If it fails (won't import / won't run in
our env), we've learned the real shape of the work on day one — the fallback is a meaningfully
different build (extract and vendor just the scoring math), and we'd want to know before sinking
effort into adapters. Add to our pixi env only the deps their functions need (e.g. xarray,
pyinterp, scipy); do **not** stand up their full 2021 conda env.

### λx is the sensitive number — the sanity anchor is three numbers, not one
λx (effective resolution) is computed from a Fourier wavenumber spectrum of the error along the
Cryosat-2 track. It is far more sensitive to harness details than RMSE: along-track interpolation
of the map onto the Cryosat-2 points, spectrum detrending/windowing, segment length, the
noise-floor crossing threshold — none of these live in our OI engine; they all live in their eval
code. That is itself an argument for letting their code do it (the design's choice), but it raises
the stakes on the anchor:

**The reproduce-published-BASELINE sanity anchor must reproduce all three numbers (µ, σ, λx ≈ 140),
not just µ.** A passing µ with a silently-wrong λx is exactly the "looks fine, isn't" failure this
project distrusts. If we can reproduce their µ but not their λx from their own map, the spectral
pipeline is configured differently than the leaderboard's, and our OI's λx is uninterpretable —
flag λx as the number most likely to expose a harness mismatch.

---

## 5. Reference frame (SLA vs SSH / MDT) — Task 1 must resolve it explicitly

The L3 along-track products are typically **SLA** (sea level anomaly, relative to a mean profile);
the gridded maps and the **MDT** (`mdt.nc`, mean dynamic topography) relate SLA to absolute SSH.
Whether the evaluation compares our map to the Cryosat-2 track in SLA space or SSH space, and
whether the MDT is added/subtracted anywhere, is a `baseline_oi.ipynb`-and-eval-code question.

If our OI produces SLA and their eval expects SSH (or vice versa), the result is a constant
offset that inflates RMSE in a way that **looks like a parameter problem but is a reference-frame
problem** — the single most likely source of a wasted debugging cycle. **Task 1's audit trail
must state, explicitly, which quantity (SLA or SSH) flows at each stage and where the MDT enters.**
"MDT handling per notebook" is not allowed to stay vague in `input_adapter.py` / `params.py`; it
is resolved and recorded in the audit trail before any run.

---

## 6. Reading the result (decompose, don't pass/fail)

- **PASS:** our OI reproduces the BASELINE row within tolerance, AND we reproduced the published
  BASELINE numbers (µ, σ, λx) from *their* map, AND our `eval/` agrees with theirs on the same map.
- **INFORMATIVE MISS (diagnose, never fudge):**
  - (i) we reproduce their published BASELINE from THEIR map but our OI map scores differently →
    parameter/grid/masking/reference-frame mismatch → check the audit trail (§5 is the prime suspect).
  - (ii) we can't reproduce their published numbers from their OWN map → we're driving their eval
    wrong, OR version skew (§3) → harness/version bug, caught at Task 0 not Task 3.
  - (iii) our `eval/` disagrees with theirs on the SAME map → our eval layer differs from canonical
    → fix our eval (a real finding regardless of the headline).
- **Do NOT loosen a tolerance to manufacture a pass.** The PASS tolerance is set *after* seeing the
  spread (scope spec), recorded, and never used as a fudge knob. A miss is decomposable and
  informative — that is the point of the dual eval + three-number sanity anchor.

---

## 7. Tests (test-design discipline — each names the bug it catches)

- Withheld Cryosat-2 never appears in the mapping input set (catches a withheld-mission leak).
- Spin-up obs are present in input but excluded from eval (catches an eval-window boundary error).
- Our output NetCDF round-trips through their reader AND matches the BASELINE schema
  field-for-field (catches a silent number-shifter).
- Coordinate names/order, SSH var name/units, and fill/mask match the shipped BASELINE map
  (catches sign/units/mask drift).
- `.env` loader fails loud on empty creds under an authenticated access path (catches a silent
  no-auth fallthrough).
- Reference-frame invariant: the quantity our pipeline emits (SLA or SSH, per the Task-1 audit
  trail) is the quantity their eval consumes (catches the §5 constant-offset error).

(New logic gets unit tests even though this is a harness — consistent with project memory
`test-significant-new-code` and the prompt's own discipline.)

---

## 8. HOLD-gated sequencing (four user-gates = scope spec Tasks 0–3)

- **Task 0 — Recon + de-risk (HOLD).** Clone/read the live challenge repo; confirm the grounded
  facts (domain box, 2017 period, five mapping missions + withheld Cryosat-2, `baseline_oi.ipynb`,
  shipped `dc_maps/`, `src` eval modules) against the source, noting any discrepancy. Wire `.env`
  loading + the `.gitignore` additions (verify `git check-ignore -v .env .env.example`;
  `!.env.example` AFTER `.env.*`). Verify the live THREDDS catalog URL + auth mechanism; access
  smoke test (read one remote NetCDF). **Pin the submodule to the leaderboard-matching commit and
  run the §4 spike: their scoring function imports, runs on their own BASELINE map, and reproduces
  the published (µ, σ, λx).** Report verified facts, the working access path, and the spike result.
- **Task 1 — Parameter extraction (HOLD, load-bearing).** Read `baseline_oi.ipynb` in full;
  extract every OI parameter; produce the audit trail (value → notebook cell → our config) **and
  resolve the SLA-vs-SSH / MDT reference frame explicitly (§5)**. Translate into our OI config. Do
  not run.
- **Task 2 — Data adapters under green tests (HOLD).** Input + output adapters; the §7 tests green;
  the schema-match evidence against the shipped BASELINE map; the small real fixture committed.
- **Task 3 — Run OI + dual evaluation (HOLD — the result).** Run OI over 2017; their eval on our
  map and on the shipped BASELINE map (the three-number sanity anchor re-confirmed); our `eval/`
  cross-check on the same map; the result table + the decomposed read (§6).

---

## 9. Non-goals (locked)

Beating the leaderboard; the currents/drifter evaluation; GMRF or any precision method; parameter
tuning or the autotuner; multi-tile / coherent sampling. Single OI, single tile, SSH scores
(µ/σ RMSE + λx via their code), reproduce BASELINE. Everything else is a later, separate
conversation.
