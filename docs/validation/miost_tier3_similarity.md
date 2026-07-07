# MIOST Tier-3 similarity vs the pinned CLS maps

**DIAGNOSTIC — never a gate (Tier 3; similarity is context, not a criterion)**

- Theirs: `data/2021a_ssh_mapping_ose/dc_maps/OSE_ssh_mapping_MIOST.nc`
  (SHA256-pinned in the 2021a manifest); their field std 0.431 m.
- Common days: 365; ours regridded to their 0.1-deg grid.
- **CORRECTED 2026-07-07 (owner-ordered): two labeled rows.** The CLS
  product assimilates all six missions; our SHIPPED product holds j3 out
  for validation — a known mission-set mismatch. Row (a) is the shipped
  product as-is; row (b) matches inputs (j3 assimilated) to isolate METHOD
  similarity, Tier-3's intent.

## RMS difference / spectral coherence, both rows

| row | map | mean RMS [m] | coh@100 km | coh@150 | coh@200 | coh@300 | coh@500 |
|---|---|---|---|---|---|---|---|
| (a) SHIPPED-PRODUCT (train-only, j3 held out) | `stage_miost_acceptance.nc` (provenance-tagged) | **0.0635** | 0.673 | 0.771 | 0.883 | 0.965 | 0.975 |
| (b) MATCHED-INPUT (j3 assimilated) | attribution variant | **0.0472** | 0.761 | 0.856 | 0.930 | 0.980 | 0.984 |

Per-day detail: (a) median 0.0606, p95 0.0902, max 0.1367 (day 267);
(b) median 0.0444, p95 0.0702, max 0.0920 (day 213). Coherence-0.5
crossing ~18 km in both rows.

## Record correction

The gate-pack Tier-3 numbers previously cited (mean RMS 0.0471 m,
coherence 0.76@100 km / 0.93@200 km) were DE FACTO row (b) mislabeled as
the acceptance map: the on-disk `stage_miost_acceptance.nc` had been
overwritten by a post-hoc, j3-assimilating Tier-3 regeneration (now
renamed `stage_miost_acceptance_tier3_regen.nc`, annotated; offset vs the
true acceptance map RMS 0.036 m / max 0.512 m, attributed to j3
assimilation — it sits max 0.020 m from a purpose-built j3 variant, ~25x
closer than to the train-only map). The true acceptance map was
regenerated deterministically at the signed winner (2026-07-07) and now
carries provenance attrs; row (a) is its number.

## Anchor caveat (recorded once, where the MIOST row is cited)

The leaderboard MIOST anchor row (0.89/0.08/139) follows the leaderboard
convention of assimilating six missions; our accepted product assimilates
FIVE (j3 held out for validation). The 0.8573-vs-0.89 comparison is
therefore conservative by construction. Caveat only — no action, no
reopening; the anchor remains aspirational, never a gate.
