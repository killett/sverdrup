# Stage-1 ORBIT_GEOMETRY consumer sweep (T6–T9) — owner pin 109(a)

**REPORT ONLY.** No fixes applied, no producers written, no tasks created. Ordered by pin
109 after the 106 conflict bit twice — T5's GroundTrack rows, then T6's per-direction
diagnostics — both discovered by building into them.

**Method:** the same both-directions walk as T11's coverage table and the 91(a) criteria
sweep. Forward: every quantity DERIVED from `ContextKey.ORBIT_GEOMETRY`, traced to the
Stage-1 consumers that read it. Reverse: every T6–T9 acceptance criterion that names a
geometry-derived quantity, traced back to whether it can be satisfied.

---

## 1. The surface, as it actually is (109b confirmed, and one correction)

`ORBIT_GEOMETRY` enters exactly one place — `build_eval_context`
(`application/eval_context.py:139-152`) — from `phase11_orbit_geometry.json` beside the
maps, **filtered by the product's own `assimilated_missions` attr**. From there it derives
**two** things, not one:

| Derived quantity | Where | Consumers |
|---|---|---|
| The geometry bag (`ContextKey.ORBIT_GEOMETRY`) | `eval_context.py:144` | `groundtrack` — **required context**, the only direct reader |
| `result["track_wedge_masks"]` (+ `wedge_masks_sha`) | `eval_context.py:145-151` | `groundtrack` (precomputed exclusions) **and `spectral_fidelity`** (wedge exclusion) |

**109(b) holds for the KEY, and is one quantity too narrow for the SURFACE.** Verified by
reading the declarations rather than assuming:

- `EffectiveResolution` (`eval/resolution.py:40-43`) — `ORBIT_GEOMETRY` **was
  over-declared here and never read; dropped 2026-07-15**. `required_context` is now
  `{WITHHELD_OBS}`. **Not a consumer.** (It is also excluded from `default_registry()`
  this phase.)
- `SpectralFidelity` (`eval/fidelity.py:129-135`) — `required_context = ∅`, and it
  genuinely **does not read** `ORBIT_GEOMETRY`. **But it consumes the geometry-DERIVED
  wedge masks**, and `_MASK_CONSUMERS` (`eval_context.py:29`) names it alongside
  `groundtrack`. Without geometry its row carries `wedge_exclusion:false` — the estimand
  is **visibly degraded, not absent** (plan-review pin 1a).
- Every other registry evaluator — `accuracy`, `calibration`, `skill`, `insitu_gauges` —
  declares no geometry, direct or derived. **Not consumers.**

So: **one direct consumer, one indirect consumer, one former consumer correctly pruned.**
The prune held; the radius is one quantity wider than the grep suggests.

---

## 2. Consumer table, T6–T9

"Satisfied" means the quantity is available at the tiles the task reads.

| # | Task | Quantity | Status | What the absence costs THAT consumer |
|---|---|---|---|---|
| 1 | **T6** kernel decision pack | per-direction track diagnostics (`track_excess_log10_<mission>_<family>`, from `groundtrack`) | **ABSENT** at all four diverse tiles | The anisotropy axis has **no directional evidence at all**. Grid aspect (1/cos φ₀) and the ring spectrum are both isotropic-blind — pin 108. Any kernel option separated by directional sampling is **UNSUPPORTED BY STAGE-1 EVIDENCE**; if the option set cannot be separated without it, T6 is a **WAIT** (108b) |
| 2 | **T6** kernel decision pack | `spectral_fidelity` slope (cited into `anisotropy_inputs.southern`) | **DEGRADED** — `wedge_exclusion:false` | The ring slope is fitted **without** excluding the track-aligned wedges, so orbit-sampling artifacts sit inside the band being fitted. Isotropic either way; now also contaminated. T6 must not treat it as a clean anisotropy input |
| 3 | **T6** option table | halo column → `operative_halo_deg()` (fork-d pin 4) | inherits 1 | 108(c): the election sets the SO obs-frame edge and the ±66 margin (pin 10). **An under-evidenced kernel choice becomes a geometry fact** — the cost of 1 does not stay inside T6 |
| 4 | **T7** Phase-10 revisit | none | **N/A — no exposure** | Lanes/bands are parameter-space boxes (`phase10_lanes.LANES/BOXES`), and the revisit's rows are per-lane per-band **score deltas** (µ / coverage convention at `phase10_lanes.py:148-160`). No geometry-derived quantity is read. Verified, not assumed |
| 5 | **T8** OSSE pricing | none | **N/A — no exposure** | Pricing arithmetic over wall/RAM actuals; no instrument rows |
| 6 | **T9** Gate-1 pack | policy (b) "reference-free rows" | **PARTIAL** | If policy (b) means the reference-free evaluator FAMILY, its founding member is missing at every diverse tile. T11 Finding 4 already flagged this term as ambiguous and asked for one ruling sentence **before T5**; pin 106(c) now supplies the pack's obligation regardless of which reading wins |
| 7 | **T9** Gate-1 pack | the composition claim in the transfer-readings section | **HANDLED** | Pin 106(c) folded into T9's criteria: the section states the composition is incomplete, as a real weakening (106e), where the numbers are |
| 8 | **T11** sealed instrument config (complete, listed for the reverse walk) | `groundtrack: {per_tile: true, per_era: true, geometry_artifact_keyed: true}` | **consistent** | The sealed config says the instrument is *geometry-artifact keyed*. Absence where no artifact applies is the config behaving as sealed — **no contradiction with the seal**, and no seal amendment is implied |

---

## 3. THE THIRD CLASS — and it runs OPPOSITE to 106 (109d)

Pin 109(d) asked whether a third class exists. It does, and it is not another instance of
the 106 conflict — it is an **artifact-placement** gap, and it costs the two Stage-1 tiles
that pin 106 does **not** apply to.

**The facts, all verified on this box:**

- `data/2021a_ssh_mapping_ose/ours/phase11_orbit_geometry.json` **EXISTS** —
  `derivation_version: 3`, `phi0: 38.1`, missions `alg h2g j2g j2n s3a`.
- `report_only_instruments_block` looks for it **beside the maps**
  (`eval_context.py:215,242`: `mean_maps.parent / "phase11_orbit_geometry.json"`). The
  Stage-1 maps live in `…/ours/phase14_stage1/`, one directory **below** the artifact.
- `anchor_signed_maps.nc` and `seam_n_signed_maps.nc` both carry
  `assimilated_missions = "alg h2g j2g j2n s3a"` — **exactly the artifact's mission set**.
- The anchor core is 295–305°E / 33–43°N and the seam cores sit inside it: **within the
  challenge box the artifact was derived over, at its own φ₀**.

**Consequence:** at `anchor`, `seam_n` and `seam_s`, GroundTrack is absent and
SpectralFidelity is wedge-degraded **not because of the 106 design conflict, but because
the artifact sits one directory up from where the reader looks.** The inputs exist, they
are in-box, and their mission set matches. Nothing new would need deriving.

**Cost:** the three tiles where the reference-free founding metric COULD stand today
carry a recorded absence instead, and their spectral rows are degraded estimands. Under
policy (b) read as the evaluator family, that is three more tiles short, on top of the four
that 106 explains.

**Not fixed here** (109a is report-only, and the fix is a placement decision, not a
mechanical one): whether the artifact should be copied/symlinked beside the Stage-1 maps,
or the reader given an explicit path, is a decision with provenance consequences — a
geometry artifact appearing in the evidence directory acquires a witness question of its
own. **Owner decision owed.**

**Why the diverse tiles are NOT in this class:** their maps carry the CMEMS codes
(`alg h2ag j2g j2n s3a` — `h2ag`, not `h2g`), the mission filter would drop the mismatched
family, and the derivation is box-and-φ₀ scoped regardless. **106 stands for all four.**

---

## 4. Stage-2 handoff (109c) — the full consumer list for per-tile orbit geometry

When per-tile orbit geometry is built as Stage-2 work (pin 106d), these are its consumers,
so it arrives as a package rather than as one missing row:

1. **`groundtrack`** — direct, required. Restores `track_excess_log10_<mission>_<family>`
   per tile×era: the 0.410→0.331 lineage, the spec's own standing reference-free
   instrument.
2. **`track_wedge_masks`** → **`spectral_fidelity`** — restores `wedge_exclusion:true`,
   i.e. upgrades every tile's spectral slope from a degraded estimand to the intended one.
   *This consumer is invisible to a search for `ORBIT_GEOMETRY` and was found only by
   tracing the derived quantity.*
3. **T6's anisotropy axis** — the only route by which the kernel decision could be made on
   measured directional sampling rather than on a cosine (108a/b).
4. **`operative_halo_deg()` / the ±66 margin** — downstream of 3, via fork-d pin 4 and
   pin 10 (108c).
5. **T9 / policy (b)'s "reference-free rows"** — the composition claim becomes satisfiable
   for the first time.
6. **The mission-code mapping** — `h2g` (dc2021a) vs `h2ag` (CMEMS-MY) must be resolved by
   the per-tile derivation, or the filter will silently drop a family at every CMEMS tile.
   Recorded here because it is the kind of detail that is cheap now and expensive later.

---

## 5. Scope note — what this sweep does NOT cover

- It does not evaluate whether per-tile geometry is *derivable* from the CMEMS dailies;
  that is Stage-2 design work, not this report's business.
- It does not price anything.
- It does not touch T0–T5 (complete or in flight) except where they feed T6–T9 — the
  T5 report rows are listed because they are the objects T6 and T9 read.
- It asserts nothing about the seal: the sealed instrument config is consistent with every
  absence recorded above (row 8).
