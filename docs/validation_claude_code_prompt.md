# Claude Code prompt — OI validation against the 2021a SSH-mapping OSE challenge

You are validating the `sverdrup` OI engine against a published external benchmark. This is the
project's original inspiration and is fully unblocked: it has NO dependency on the autotuner
(Phase 5), the GMRF coherent sampler, or anything from the Stage-B saga. Work in the existing
`sverdrup` repo.

## Ground rules (same discipline as every prior phase)
- **Anchor to the real challenge repo and the live AVISO server — never reconstruct their
  protocol, parameters, or endpoints from memory.** Clone/read the actual repo; read the actual
  `baseline_oi.ipynb`; hit the actual THREDDS catalog. Where this prompt states a fact, VERIFY it
  against the source before relying on it. If the source disagrees with this prompt, the source
  wins — surface the discrepancy.
- **Their evaluation code is ground truth for the reported number. Our `eval/` runs in parallel
  only as a cross-check.** Do not reimplement their metric as the source of truth.
- **Nothing committed without passing tests + your review checkpoints.** Hold at each checkpoint
  below for the owner.
- Read the scope spec (`validation_scope_spec.md`) first; it has the full claim, the resolved
  decisions, and the grounded repo facts.

## The claim you are testing (must stay falsifiable)
Our OI engine, configured from the challenge's own `baseline_oi` covariance parameters, on the
2021a Gulf Stream box (lon 285–315°E, lat 23–53°N, eval year 2017), mapping the FIVE-mission
constellation (SARAL/AltiKa, Jason-2, Jason-3, Sentinel-3A, Haiyang-2A — Cryosat-2 is WITHHELD),
scored by the challenge's own `src`/`example_data_eval` against the withheld Cryosat-2 track,
reproduces the published leaderboard **BASELINE (OI)** row: µ(RMSE) ≈ 0.85, σ ≈ 0.09, λx ≈ 140 km.

## Credentials & data access (files already provided in the repo root)
- `.env.example` is committed (placeholders only). The owner will `cp .env.example .env`,
  `chmod 600 .env`, and fill in AVISO+ username/password. Your code reads `.env` (python-dotenv
  or equivalent) and FAILS LOUDLY with a clear message if `AVISO_USERNAME`/`AVISO_PASSWORD` are
  empty when an authenticated path is selected.
- Ensure `.gitignore` contains the patterns in `gitignore_additions.txt`. CHECK the existing
  `.gitignore` first (there are likely already `.env`-related patterns) and APPEND ONLY what is
  missing — do not duplicate. CRITICAL ORDERING: `!.env.example` must come AFTER `.env.*`, or the
  committed template gets ignored. Verify `.env` is ignored and `.env.example` is NOT, with
  `git check-ignore`.
- Preferred access: AVISO+ THREDDS (OPeNDAP/FileServer, HTTPS, Basic Auth). **First adapter task:
  verify the live THREDDS catalog URL for the 2021a products and the exact auth mechanism (HTTP
  Basic header vs `~/.netrc` + `~/.dodsrc` for the OPeNDAP/netCDF-C stack).** The base URL in
  `.env.example` is the standard AVISO+ root; the per-product catalog path is VERIFY-ON-CONTACT.
  Unauthenticated MEOM-Grenoble mirror and AVISO+ FTP are documented fallbacks in `.env.example`.

## Tasks (each ends at a HOLD for owner review)

### Task 0 — Repo recon + access smoke test (HOLD)
1. Clone/read the challenge repo (`master` branch). Confirm the grounded facts in the scope spec
   against the live repo: domain box from filenames, 2017 period, the five mapping missions +
   withheld Cryosat-2, the `baseline_oi.ipynb` baseline, the shipped `dc_maps/` comparison files,
   the `src` eval modules. Note any discrepancy from the spec.
2. Wire `.env` loading + the `.gitignore` check above. Verify ignore behavior with
   `git check-ignore -v .env .env.example`.
3. Access smoke test: with the owner's filled-in `.env`, fetch ONE small file (e.g. one mission's
   L3 along-track NetCDF header, or the shipped `OSE_ssh_mapping_BASELINE.nc` metadata) via the
   selected method. Confirm auth works and you can read a remote NetCDF. Report the verified
   THREDDS catalog URL + auth mechanism.
**HOLD:** report verified facts, any spec discrepancies, the working access path. Do not proceed
to bulk download or implementation until the owner confirms.

### Task 1 — Parameter extraction from baseline_oi.ipynb (HOLD)
1. Read `notebooks/baseline_oi.ipynb` in full. Extract EVERY parameter of the OI baseline: spatial
   correlation length scale(s) (and any lat/anisotropy dependence), temporal correlation window,
   signal & noise variance, the OI influence radius / neighbourhood selection, the output grid
   (resolution, the 285–315 / 23–53 box, time stepping/cadence), and any preprocessing of the
   along-track input (detrending, MDT handling via `mdt.nc`, editing).
2. Produce a PARAMETER AUDIT TRAIL: a table mapping each extracted value to its source cell/line in
   the notebook, and to the corresponding setting in our OI `ParameterProvider` / config. This is
   the evidence for "same recipe" and the diagnostic key if we miss.
3. Translate into our OI config. Do NOT run yet.
**HOLD:** present the audit trail. Owner confirms the parameter mapping before any run. (A wrong
parameter reading here invalidates the whole claim — this is the load-bearing task.)

### Task 2 — Data adapters under green tests (HOLD)
1. INPUT adapter: their L3 along-track NetCDF (the five mapping missions) → our observation format,
   reusing the existing ODC adapter pattern. Load the withheld Cryosat-2 track SEPARATELY (for
   evaluation only — it must never enter the mapping). Honour the spin-up window (obs from
   2016-12-01 usable, not evaluated). Commit a small real fixture (one time slice / small subset)
   per the project's data discipline; the bulk data stays gitignored.
2. OUTPUT adapter: our gridded OI map → their map NetCDF schema. Match `OSE_ssh_mapping_BASELINE.nc`
   EXACTLY: dimensions, coordinate names/order, the SSH variable name + units, the time axis,
   fill/mask conventions. Their eval code must ingest our file unchanged.
3. Tests (test-design discipline — each states the behavior + the bug it catches): the withheld
   mission never appears in the mapping input set; the spin-up window is included in input but
   excluded from eval; our output NetCDF round-trips through their reader and matches their schema
   field-for-field; coordinate/units/mask match the shipped BASELINE map.
**HOLD:** green adapters + the schema-match evidence. Owner confirms before the full run.

### Task 3 — Run OI + dual evaluation (HOLD — the result)
1. Run our OI over 2017 on the box, five-mission input, `baseline_oi` parameters → our map in
   their schema.
2. THEIR EVAL (ground truth): run their `src`/`example_data_eval` functions on (a) OUR map and
   (b) the shipped `OSE_ssh_mapping_BASELINE.nc`. Re-deriving their PUBLISHED BASELINE number from
   their own map proves we drive their eval correctly — do this and report it as the sanity anchor.
   If their full notebook env fights our stack, extract and call their scoring FUNCTIONS from `src`
   rather than standing up their environment.
3. OUR EVAL (parallel cross-check): run our `eval/` area-weighted RMSE on OUR same map. Report the
   delta vs their RMSE on the same map.
4. Produce the result table: our µ(RMSE)/σ(RMSE)/λx beside the BASELINE (0.85/0.09/140) and DUACS
   (0.88/0.07/152) rows; the reproduced-published-BASELINE sanity number; the parallel-eval delta;
   and the parameter audit trail.
**HOLD:** present the table + the decomposed read (see below). Owner decides disposition.

## Reading the result (decompose, don't just pass/fail)
- **PASS:** our OI reproduces the BASELINE row within tolerance, AND we reproduced the published
  BASELINE number from their map, AND our `eval/` agrees with theirs on the same map.
- **INFORMATIVE MISS (diagnose, do not fudge):**
  (i) we reproduce their published BASELINE from THEIR map but our OI map scores differently →
      parameter/grid/masking mismatch → check against the audit trail.
  (ii) we can't reproduce their published number from their OWN map → we're driving their eval
      wrong → harness bug.
  (iii) our `eval/` disagrees with theirs on the SAME map → our eval layer differs from canonical
      → fix our eval (this is a real finding regardless of the headline).
- Do NOT loosen a tolerance to manufacture a pass. A miss is decomposable and informative; that is
  the point of the dual eval + sanity anchor.

## Explicit non-goals (do not scope-creep)
Beating the leaderboard; the currents/drifter evaluation; GMRF or any precision method; parameter
tuning or the autotuner; multi-tile / coherent sampling. Single OI, single tile, SSH scores,
reproduce BASELINE. Everything else is a later, separate conversation.

## Wrap-up
Commit: the adapters, the OI config + parameter audit trail, the dual-eval runner, and a short
report (the result table + decomposed read). Update PROGRESS/notebook with the outcome. Hold for
owner review at each Task HOLD; nothing forced green; if you hit the AVISO access wall, surface it
rather than working around it.
