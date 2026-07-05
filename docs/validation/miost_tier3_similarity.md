# MIOST Tier-3 similarity vs the pinned CLS maps

**DIAGNOSTIC — never a gate (Tier 3; similarity is context, not a criterion)**

- Ours: `data/2021a_ssh_mapping_ose/ours/diag_local_windowed.nc`; theirs: `data/2021a_ssh_mapping_ose/dc_maps/OSE_ssh_mapping_MIOST.nc` (SHA256-pinned in the 2021a manifest).
- Common days: 365; ours regridded to their 0.1-deg grid: True.

## RMS difference [m]

- mean over all days: **0.1130** (their field std 0.431)
- per-day: median 0.1046, p95 0.1649, max 0.2335 (day index 95)

## Along-lon spectral coherence (lat 37.0-39.0, 1281 sampled rows)

| wavelength [km] | coherence |
|---|---|
| 100 | 0.598 |
| 150 | 0.677 |
| 200 | 0.797 |
| 300 | 0.910 |
| 500 | 0.940 |

Coherence-0.5 crossing: ~18 km.
