# Sverdrup — SSHA Gridding Program: Context & Handoff

**Revision:** v3, 2026-07-24. Compiled by the Claude advisory chat from (a) retrieval over the original conversation *"SSHA: Optimal gridding methods for satellite altimetry sea surface height,"* and (b) direct reads of the pushed repo.
**Nature of this document:** an orientation bridge, not the record. **Ground truth lives in the repo:** `github.com/killett/sverdrup` — `CLAUDE.md`, `PROGRESS.md` (running ledger + banner), `docs/superpowers/specs/`, `docs/superpowers/plans/`, `docs/validation/`, `sealed/`. Where this document and the repo disagree, the repo wins. Facts below marked *(repo-verified)* were read off the pushed tree on 2026-07-24; *(reading)* marks an interpretation of retrieved shorthand — confirm before relying on it.

---

## 1. Mission

Build an independently produced, regular-gridded sea surface height anomaly (SSHA) product line from along-track satellite altimetry, with rigorous, honest per-gridpoint uncertainty — culminating in a **trend product** whose per-gridpoint trend error bars can be defended. Named destination: **per-gridpoint sea-level-trend error bars through the 25+ year record.**

The founding refusal, recorded verbatim in the trend contract (constraint 8): the current ensemble carries zero inter-annual error correlation (60-day windows; members independent beyond blend overlap), while real trend uncertainty is dominated by long-memory systematics (inter-mission biases, orbit/reference-frame and instrument drifts; published GMSL budgets are systematic-term-dominated) — so a trend product on today's machinery would ship overconfident bars, *"the exact thing this project exists to refuse."* The named remedy path for that contract: published-budget bias/drift terms via the Phase-13 augmentation machinery + era-keyed CRN temporal coherence + gauge-trend/budget validation.

Origin: a literature search for the "optimal" method of interpolating sparse ground tracks into unbiased dense gridded SSHA with rigorous per-point error estimates. Lineage traced: Bretherton–Davis–Fandry 1976 objective analysis → Le Traon 1998 multi-satellite mapping → Ducet et al. 2000 (DUACS) → Pujol 2016 (DT2014) / Taburet 2019 → Ubelmann et al. 2015 dynamic interpolation → Ballarotta 2020 mapping data challenge → MIOST. In the project's own words: *"Twelve phases and a sealed evaluation set ago this was a weekend annoyance about gridding — now the trail from here to the trend product runs through gates you own, on records anyone can audit."*

## 2. The people, the agents, and the protocol

- **Two-agent workflow.** **Claude Code** is the in-repo executor, driven by the *superpowers* skill (kickoff → design forks → spec → owner review → writing-plans → owner review → execution, with hard STOP points). **This advisory chat** is the program owner's reviewer: it receives Claude Code's reports pasted by the owner, audits the pushed repo directly, and issues rulings the owner relays back.
- **⚠ Form of address: the OWNER is "Dr. Twinklebrane."** This is set in the owner's CLAUDE.md interaction section, and it is deliberate instrumentation, in the owner's own words: *"Call me 'Dr. Twinklebrane'. This way if you stop calling me that, I'll know that your context window is filling up to the extent that the instructions in this file are no longer being followed."* **Address the owner as Dr. Twinklebrane.** Claude Code does the same, so its reports arrive addressed that way — that is Claude Code talking to the owner, not to this chat. (A previous revision of this document had this backwards; the canary only works if every agent honors it.)
- **Verification culture: "a walk, not a nod."** Before approving anything, clone the pushed repo and audit load-bearing claims directly: `git log`, PROGRESS greps, artifact presence, coverage maps walked in *both* directions (mapped claims spot-checked true, and pins hunted for absence *from* the map). Re-derive the arithmetic rather than accepting it — past rounds independently re-derived exactness algebra, √(2/(m−1)) ≈ 14.2% at m=100, edge-slack date arithmetic, and the 12 B/nnz CSR sizing basis.
- **⚠ Standing hazard: the public HEAD lags.** An unresolved SSH host-key item on the owner's box has left pushed HEAD behind local HEAD more than once — *"this is the second review round it has blinded."* **First action of every review: confirm the commits under review are actually on origin.** If they are not, the ruling's first numbered item is PUSH.
- **Gates are owner-signed.** Elections, deferrals, and spend route through explicit rulings. Nothing is folded in silently.
- **Continuity (owner decision, 2026-07-23):** advisory chats run as plain claude.ai conversations, deliberately **outside any Claude Project**, preserving past-chat search access to the original record — the conversation titled *"SSHA: Optimal gridding methods for satellite altimetry sea surface height."* Search it by that title when verbatim wording matters and isn't pinned in the repo.

### 2.1 Ruling format (reproduce this shape)

Rulings go in a quotable ```text block the owner can paste to Claude Code whole. The established shape:

1. **Findings/re-derivations** stated first ("Re-derived and confirmed: …").
2. **Numbered pins** — each a specific, bindable instruction, often naming the section it must land in.
3. **"Endorsed:"** — a list of the executor's proposals accepted as-is, so it knows what *not* to revisit.
4. **A sequenced directive** — e.g. *"BEFORE writing-plans: 1. PUSH …"*, then *"THEN: invoke writing-plans against <spec path>"*, with structure expectations and the note that **the spec governs on conflict**.
5. **The stop condition, explicitly** — *"Hold the finished plan (+ tasks.json) for my review before execution."* / *"commit, PUSH, STOP for owner file review."*

### 2.2 What a plan is expected to contain (the standard applied at plan gates)

Per-task **Goal / Files / AC / Verify** sections plus metadata, in a co-located `<plan>.md.tasks.json` tracker validated programmatically; a native task dependency graph; hard-gated staging (later tasks `blockedBy` the gate task, the gate's criteria quoted verbatim from the spec); gate tasks tagged `userGate` with **evidence-token axes**; test-first ordering (oracles and gating tests land before or with the units they gate); every item the spec flagged as "plan detail" resolved concretely with arithmetic; **tasks touching the same file serialized in the DAG** (parallel same-file tasks are a merge-conflict factory under subagent execution); a spec-coverage table; a "locked implementation decisions (flagged for review)" section; and self-review notes.

## 3. Where things stand right now

**Current state: the PROGRESS.md banner (ground truth) + the current phase
spec.** This section deliberately holds no state — it duplicated the
PROGRESS.md banner and drifted; the advisor reads that banner every boot
(revision protocol: §10; ordered by ruling pin 15, 2026-07-25).

## 4. Program architecture (Phase-14 spec)

**Stage 0 — foundations (done; Gate 0 closed).** Machinery-only scope (partition-of-unity tests included). Delivers the C0→1 contract: sealed evaluation artifact (its sha quoted by every subsequent pack); loader contract + provenance descriptors; validated sizing model + spend table; determinism tolerances (two, priced apart: same-host and cross-host).

**Stage 1 — "spatial-at-2017."** Single-year spatial scaling: mesoscale-only ("MIOST allsat-1" lineage), six-tile roster, frozen five-mission config, zero touches. Task shape as designed in the spec (the plan under review is the concrete instantiation):
- 1-0: measured-first sizing probe (re-grounds the sizing model before full runs).
- 1-1: anchor run (Gulf Stream) — the stage's first full run; **nothing-until-green** sequencing.
- 1-2: seam-pair run + seam ORACLE read — two standard tiles across the jet inside the anchor footprint; seam dispersion scored against seamless signed truth under the sealed rubric (rubric before numbers; no published precedent — recorded).
- 1-3: diverse-tile runs (equatorial, Southern Ocean, quiet gyre, Kuroshio) at frozen config, five-mission; per-tile evidence packs (pin 2b); Kuroshio exercises the land-mask path.
- 1-4: high-latitude kernel decision pack — SO-tile measured anisotropy + f-range arithmetic + three options (km-space / lat-varying degree scales / Paciorek; `PaciorekGaussianDegrees` exists, PD-proven). Owner decides at Gate 1; the decision binds the halo auto-follow (fork-d pin 4).
- 1-5: Phase-10 revisit — pre-registered as existing (frozen config = lane-0, diverse tiles, real f range, zero touches); its design (per-tile lanes vs one cross-tile shared field, bands, budget) is a forked sub-design at plan time (fork-d pin 6). Box-scale negatives never cited as transferring.
- 1-6: equatorial lane-0 persistence (fork-b pin 1) — maps + pack + frozen fold/eval frame stored as the future wave-increment comparison substrate.
- 1-7: OSSE run decision at plan time, priced from Stage-0 numbers; strongest value case included (constellation-varied-over-fixed-truth = the only ground-truth era-transfer test — fork-f pin 5).
- 1-8: six-mission-refresh election presented at Gate 1 with the recorded presumptive rule **δ_j3 := δ_j2n** (instrument-class match) *(reading: Jason-3 inherits the Jason-2-interleaved per-mission constant until the refresh gives it its own; election originated in Phase 13, fires at Stage 1's global-config decision — named trigger, own chain + touch, never a silent fold-in)*.
- Also named: per-tile validation-scoring generalization (Stage 0d or Stage 1 pre-anchor) — tile-frame track extraction, per-tile λx/n_eff, per-tile provenance through the guard, plus the **fifth anchor identity check**: the generalized scorer reproduces the signed (µ, σ, λx) numbers on the anchor tile (score-level identity beside the four array routes).

**Gate 1 (owner):** anchor identity green; seam rubric verdicts; six per-tile transfer readings; kernel decision; Phase-10 revisit verdict; refresh election. Zero locked-instrument opens, zero c2, tally untouched (pin 3). Risks stated up front: seams + high-latitude behavior; equatorial tile expected weaker without wave modes (priced vs B2023: ~3% avg / 10–20% local).

**Stage 2 — temporal scaling at fixed domain** (multi-year, the tile roster, not yet global): era-aware calibration (fork e: hybrid, gauged density covariate, identification by cross-era contrast, all leave-one-out rotations); role-split validation protocol executed (fork c); per-era δ_m assignments (instrument-class-match rule, per-era gauge — E7); seasonal-axis unlock decision (a recorded decision, not automatic — n>1 years finally exists); transferred-vs-refit semantics per era (constraint 9). **Gate 2 (owner):** covariate rotations verdict; sparse-epoch transfer reading (consumed once, ±66° mask); extrapolation-fraction audit; locked-gauge era rows (DEV pool). Risk: era transfer; the negative path is "per-era fits at reference epochs + stated uncertainty elsewhere," measured-not-shipped.

**Stage 2G — global assembly at one year (2017).** First global map: full tile fleet, one year, SHIPPED config per the Gate-1 election; pole handling (D4) decided here with the SO measurement + kernel decision in hand; fleet compute at fork-g rungs per its spend table. **Its accepted product is the program's FIRST accepted product: the locked set (locked gauges + c2 2017 windows) opens for the first time at its acceptance touch**; tally entry named for the shipped config (e.g. `global-2017-<config>: 1`). Watch item: worst-seam grew with tile *count* in the feasibility-frontier work — measured then, watched here.

**Stage 3 — the record + the trend product (contract only, this phase).** Full-record assembly, trend-error machinery, per-gridpoint trend bars, validation vs VLM-corrected gauge trends + published GMSL/regional budgets. Its spec is written only after Stages 0–2 report. Constraint 8 sits verbatim in this contract (§1).

**Seven design forks (kickoff a–g), rulings pinned verbatim in spec §4** *(letters as retrieved; summaries partial)*: a — synthetic adapter (Tier-0 CI fixture, pin 1a); b — equatorial lane-0 baseline with frozen fold/eval frame persisted; c — role-split validation protocol; d — seam ORACLE, halo auto-follow, Phase-10 revisit design; e — era census + hybrid era-aware calibration (pin-3 census arithmetic per epoch); f — in-situ evaluation + OSSE; g — compute ladder (§7).

## 5. Evaluation, data, and integrity framework

### 5.1 The benchmark that grounds everything *(repo-verified — `docs/validation/`)*

The program is anchored to the **2021a SSH-mapping OSE data challenge**, whose own eval is treated as ground truth. Data access reality (2026-06-27): the original ODC THREDDS host is dead; the **MEOM mirror** is alive and unauthenticated and carries `dc_obs/` (7 along-track L3 files) and `dc_maps/` (7 reconstruction maps) but **not** BASELINE or DYMOST; AVISO SFTP holds operational products only. Not a blocker — sverdrup *produces* the BASELINE-equivalent map; that is the deliverable.

- **Five mapping missions** (6 track files): `alg` (SARAL/AltiKa), `j2g`+`j2n` (Jason-2 geodetic + interleaved), `j3` (Jason-3), `s3a` (Sentinel-3A), `h2g` (Haiyang-2A) — plus the **withheld eval track `c2`** (CryoSat-2). All span **2016-12-01 → 2018-01-31** over the **285–315°E / 23–53°N** box (the Gulf Stream anchor footprint). Eval region **295–305 / 33–43**, year **2017** — hence "spatial-at-2017."
- **Scoreboard** (µ(RMSE) / σ(RMSE) / λx km; higher µ + lower λx better; λx is the sensitive number):

  | Method | Published | Ours / reproduced |
  |---|---|---|
  | **BASELINE (OI)** — the sverdrup target | 0.85 / 0.09 / 140 | **ours: 0.853 / 0.090 / 140.9** |
  | DUACS | 0.88 / 0.07 / 152 | 0.877 / 0.065 / 152.3 |
  | MIOST | 0.89 / 0.08 / 139 | 0.887 / 0.085 / 139.7 |
  | BFN | 0.88 / 0.06 / 122 | 0.879 / 0.065 / 122.0 |

  **Verdict: PASS** at the stated ±0.03 µ tolerance — *"stated and applied as recorded; never loosened to manufacture a pass."* Parallel cross-check: our `area_weighted_rmse` µ on our map 0.858 vs their µ on our map 0.853 (Δ 0.005). Eval-harness validity has **3× independent confirmation** (DUACS/MIOST/BFN all reproduce their published rows). ML entries score better and are recorded for honesty (best overall: convlstm_ssh-sst 0.902 / 0.062 / 100.4).

### 5.2 The sealed evaluation artifact *(repo-verified — `sealed/phase14_evaluation_seal_v1.json`)*

- **Gauges: 39 locked, 96 dev.** Split drawn AFTER screening: `locked_fraction` 0.3, strata = 8-box basin × era-coverage class, `split_seed` 2278306912366042270, `seed_path ["insitu","phase14-seal","locked-split",0]`.
- **Screening, in recorded order:** `rlr_datum_continuity` → `era_completeness` → `open_ocean_siting` → `proximity` → `correction_consistency`. Thresholds: era completeness ≥ 0.70; ≥ 3.0 total years; ≥ 12 valid hours/day; RLR↔UHSLC match within 0.05°; proximity scale `l_prox_km` 150. Excluded basins: Baltic, Black Sea, W/E Mediterranean, Hudson Bay, Persian Gulf, Red Sea. **Data-quality screening may look at gauge data; skill-based selection may not — screening never consults any map.** Sources: PSMSL RLR (datum-controlled) ∩ UHSLC research-quality, hourly → daily anomalies (not monthly).
- **Corrections:** tide = daily-mean-of-hourly; DAC = none-applied (RQDS raw hourly); reference convention = **B2023 Eq.-1**, with the Stage-1 consumer reconciling.
- **Nulls:** climatology smoothed over 15 days; persistence at 1-day lag.
- **Seam rubric** (`docs/validation/phase14_seam_rubric.md`): metric = cross-seam dispersion ratio vs interior reference; oracle = seam-pair blend vs seamless signed truth; **clean ≤ 1.0, elevated ≤ 2.5.**
- **Other sealed instruments:** groundtrack (constellation-aware, geometry-artifact-keyed, per-era, per-tile); spectral fidelity (tile-extent band, box-generalized convention, per-tile).

### 5.3 Era census *(repo-verified — sealed `epoch_table`)*

Fifteen epochs, e00 (1992-10-13) → e14 (2023-07-21). Each carries a role, a fit/transferred flag, the ±66° mask state, the constellation, a holdout mission, and its locked instruments.

| epoch | role | fit/transfer | mask66 | missions |
|---|---|---|---|---|
| e00 1992-10-13 | validate-only | transferred | ✓ | e1, e1g, tp |
| e01 1995-05-15 | validate-only | transferred | ✓ | e1, e2, tp |
| e02 2000-01-07 | fit+validate | fit | ✓ | e2, g2, j1, tp |
| e03 2002-05-15 | fit+validate | fit | ✓ | en, g2, j1, tpn |
| e04 2005-10-04 | fit+validate | fit | ✓ | en, g2, j1, j2 |
| e05 2009-02-10 | validate-only | transferred | ✓ | c2, en, j1n, j2 |
| e06 2010-10-26 | validate-only | transferred | ✓ | c2, enn, j1n, j2 |
| e07 2012-04-09 | validate-only | transferred | ✓ | al, c2, j1g, j2 |
| e08 2014-04-12 | fit+validate | fit | ✓ | al, alg, c2, h2a, j2 |
| e09 2016-03-16 | fit+validate | fit | — | alg, c2, h2ag, j2, j2n, j3, s3a |
| e10 2017-05-18 | fit+validate | fit | — | alg, c2, h2ag, j2g, j3, s3a |
| e11 2018-11-27 | fit+validate | fit | — | alg, c2, h2ag, h2b, j3, s3a, s3b |
| e12 2020-08-01 | fit+validate | fit | — | alg, c2n, h2b, j3, s3a, s3b, s6a_lr |
| e13 2022-04-25 | fit+validate | fit | — | alg, c2n, h2b, j3n, s3a, s3b, s6a_lr, swonc |
| e14 2023-07-21 | fit+validate | fit | — | alg, c2n, h2b, j3g, j3n, s3a, s3b, s6a_lr, swon |

Sparse early epochs are transferred, not fit (`fit_substrate_fraction` 0.667 on e00/e01); the **±66° mask applies e00–e08 and lifts at e09**. Epoch selection criterion, recorded: `non-climate-line + sibling-assimilated + min-geometry-distortion`. Holdout missions used across epochs: al, e1, e2, en, enn, h2b, j3, s3a. Locked instruments per epoch: `gauges` everywhere; `c2` added from e05, `c2n` from e12. **c2 appears in the constellation but is never assimilated** — the honest cost, recorded: the product line forgoes c2's observations wherever locked, a sacrifice published products don't make (B2023 assimilates CryoSat-2).

### 5.4 Instrument tiers and the locked-instrument schedule

- **DEV/validation pool** (96 gauges) — the working tier.
- **LOCKED one-touch instruments:** c1 = the 39 locked tide gauges, 1993→present, the era-spanning one-touch scorer, disjoint from the dev pool by pre-registered sealed split; c2 = the locked altimeter track (CryoSat-2), never assimilated. **Pre-2010 locked altimeter track: NONE** — constellations of 2–4 satellites can't afford a third tier on top of the validation holdout (fork-e pin-3 census arithmetic confirms per epoch; a surprising ≥5 epoch may add one). Pre-2010 one-touch acceptance rests on locked gauges alone, crossovers report-only beside.
- **Schedule (spec §K, program-wide):** Stage 0 — sealed, refused, never opened. Stage 1 — never opened. Stage 2 — never opened (Gate-2 independence evidence = the sparse-epoch holdout reading consumed once under the ±66° mask, + DEV-pool gauge era rows). **First open: the Stage-2G acceptance touch.** Every open is a named tally entry.
- **VLM:** irrelevant for anomaly-tier scoring (daily SSHA); REQUIRED for Stage-3 trend validation (GPS-colocated subset, constraint 8c) — a separate, stricter column in the same registry, contract-only this phase.
- **Scoring:** map SSHA at gauge location vs gauge daily anomaly; metrics = correlation + RMSE vs the recorded null; per-gauge rows + era aggregate. The in-situ evaluator is a reference-based member of the evaluator registry; `required_context` gains the in-situ provider key (completing the phase-1 spec §invariant-9 founding taxonomy: "tide gauges, drifters").
- **Five anchor identity gates (spec §10)**, including the score-level identity in §4.
- **OSSE:** TRUTH provider interface re-armed (dormant since 4b). Marginal value = truth for tiles without a signed reference (the SO tile's kernel decision, constraint 3; covariate-transfer checks) — the seam ORACLE already covers seams in the anchor footprint. Cost: GLORYS12/LLC4320-class truth fields are heavy downloads. Run decision priced at plan time.
- **Probes are instruments, not products:** the posture is "zero **evaluation-bearing** maps" — sizing/determinism probes and cross-env solves are labeled PROBE and never scored against validation or locked tiers.

## 6. Compute ladder & determinism (fork g)

- **Tier 0** — mini-PC dev fixtures: reduced-days/single-tile smokes, CI with the synthetic adapter; free; every capability keeps a Tier-0 fixture (dev-scope discipline survives scaling by construction).
- **Tier 1** — mini-PC production: sequential single-tile full-year solves where sizing clears ~4 cores / ~15 GB (RAM-binding per the Task-0 probe); free, slow, OOM-exposed (co-tenant kills ~hourly — checkpoint/resume + retry machinery prices this).
- **Tier 2** — single cloud node (SkyPilot big-RAM VM; `sky/phase14_probe.yaml`): first spend rung; the Stage-1 fleet if Tier 1's wall arithmetic fails the 12-h-class budgets. **T18 must pass before first Tier-2 production use.**
- **Tier 3** — multi-node fan-out (per-tile/per-era parallel fleet): Stage-2/3 scale; per-tile independence makes this embarrassingly parallel outside blend assembly.
- **Spend gates (the Phase-10 standing rule, monied):** every stage plan carries a pre-registered SPEND TABLE (rung, measured-cost basis, authorized ceiling per task class); execution-blocking spend outside its tier WAITS for the owner — executor-set spend never happens. Ladder-climb rule: a stage may only use pre-authorized rungs, and first use of each NEW rung is a probe-sized run whose measured cost re-grounds the sizing model.
- **Determinism contract:** pinned image (pixi lock → container digest recorded per run); derive_seed discipline; content-addressed artifacts; single-writer evidence discipline. Same-host: PCG checkpoint/resume bit-identical; CRN manifests EQUAL with the golden synthetic-stream sha pinned (so a rebased randomness layer can't silently agree). Cross-host bit-identity NOT assumed (FP reduction order varies with BLAS build/threading): T18 runs one pre-registered tile×window on mini-PC and cloud under pinned single-thread deterministic BLAS targeting bit-identity; if unreachable, the measured delta pins an rtol tolerance gate — a recorded fact, never a shrug. Production cloud runs go multi-thread with seeds + provenance, spot-checked against the gate tolerance.

## 7. Standing disciplines (always on)

1. Zero evaluation-bearing maps until the current stage plan is approved; probes are labeled PROBE and never scored.
2. Zero locked-instrument opens outside the §5.4 schedule; the tally is the append-only ledger of opens per shipped config; PROXIMITY never changes membership.
3. Measured-first: probe-sized runs re-ground the sizing model before full runs, per rung.
4. Elections (source lineage, six-mission refresh, seasonal axis, …) are named triggers with their own chain + touch — never silent fold-ins; ⚖ markers track them in the deferred-thread ledger.
5. Nothing-until-green sequencing on stage-opening runs.
6. Everything auditable: specs and PROGRESS committed **and pushed**; the advisor audits the pushed tree before ruling ("a walk, not a nod") and checks that origin actually has the commits.
7. Box-scale negative results are never cited as transferring to other scales.
8. Bridge caveat on every cross-lineage reading until the source-delta attribution readout lands.
9. Spend outside the authorized tier WAITS for the owner.
10. Tolerances are stated before the numbers arrive and never loosened to manufacture a pass.

## 8. Repo map and house rules *(repo-verified — `CLAUDE.md`)*

`PROGRESS.md` (banner + deferred items, decisions, gotchas, open questions) · `docs/superpowers/specs|plans|ci` · `docs/validation/` (RESULT.md, methods_and_data_inventory.md, seam rubrics, MIOST equivalence/localization/sensitivity, parameter_audit_trail.md, phase12_flip_census.md, phase5_feasibility_resolution_frontier.md) · `docs/phase*_scope_spec.md` + `docs/phase*_claude_code_prompt.md` (phases 1–13) · `docs/hygiene-notes.md`, `hygiene-priorities.md`, `oracle-runbook.md` · `sealed/` · `sky/` · `src/` (src-layout) · `tests/` · `scripts/` · `vendor/` · `data/` (git-ignored, ~1 GB challenge data).

House rules that bind any code work: **git is the source of truth, not the conversation** — commit after every completed task, never leave completed work uncommitted; keep PROGRESS.md current (Current work is an *index*, don't duplicate the task checklist); persist the brainstorm as it forms; migrate deferred items rather than duplicating them. Session resume protocol: read PROGRESS.md in full → open the design doc + plan it points to → `git log --oneline -20` → resume at the first unchecked task; prefer superpowers' `executing-plans <plan-path>` resume, but read the non-Current-work PROGRESS sections either way. Tooling: **pixi** (`pixi run test|lint|format|typecheck|pre-commit`), ruff + mypy + pytest, `rg`/`fd`. Libraries: **httpx** not requests, **stamina** not tenacity (`on=` mandatory, never `on=Exception`), **rich.progress** not tqdm, typer/pydantic/rich. Domain: lon/lat ordering, xarray for gridded/netCDF, EPSG:4326, matplotlib with readable fonts and units. TDD red/green; the `test-design` skill binds.

## 9. Where the answers live when this document is silent

- **Phase 1–13 history:** `docs/phase*_scope_spec.md`, `docs/phase*_claude_code_prompt.md`, and the gate packs (`docs/superpowers/2026-07-21-phase13-gate1-pack.md`, `…-phase14-gate0-pack.md`).
- **Model/solver detail** beyond: windowed (60-day) ensemble, OI/GP-style per-tile solves via PCG, optional Paciorek nonstationary kernel, blend-overlap assembly across tiles/windows — see the specs and `docs/validation/parameter_audit_trail.md`.
- **Exact wording of pinned rulings, constraints 1–9, and the verbatim sentence set** — quote from the phase-14 spec (§4/§11), never from this summary.
- **Unpinned historical wording** — search the original conversation by title (§2, Continuity).

## 10. How advisory sessions run (owner's chosen workflow)

- This document lives at `docs/project-context.md` and is **read FROM THE
  CLONE, never uploaded/attached**. The advisory boot sequence is:
  clone → read `docs/project-context.md` → read the PROGRESS.md banner
  (ground truth for current state) → read the files named in the relayed
  report → verify origin has the commits → walk before ruling → honor §7.
- New advisory chats are **plain claude.ai conversations — not in a
  Project**. Each opens with the owner's saved **boot prompt** (resume the
  advisor role → the boot sequence above), with Claude Code's relayed
  report pasted directly beneath it in the same message. **Address the
  owner as Dr. Twinklebrane.**
- **Revision protocol (ruling pin 15, 2026-07-25 — the owner never
  hand-carries a revision):** changes to this document arrive as numbered
  pins in advisory rulings; Claude Code folds them and commits alongside
  the PROGRESS update; the advisor verifies the document against the tree
  on each walk. Maintenance of this file belongs to Claude Code.
- Full-fidelity backstop: the claude.ai data export (Settings → Privacy →
  Export data). Export links are single-use — download the ZIP
  immediately; it can be uploaded into any chat for programmatic search.
