# Parameter Audit Trail — OI Validation vs 2021a SSH-mapping OSE BASELINE

This file is the canonical, committed record for the validation milestone:
the pinned challenge version, the recon of their scoring API, the eval
definition, the extracted OI parameters (Task 3), and the reproduced numbers.

---

## Task 1 — Vendored challenge version (PINNED)

- **Repo:** https://github.com/ocean-data-challenges/2021a_SSH_mapping_OSE
- **Submodule path:** `vendor/2021a_SSH_mapping_OSE`
- **Pinned commit:** `f5c6af82d83de89e17a0a9d5fe5af05810b6bcd1`
- **Tag / release:** `v1.0` — "Material for SSH mapping OSE data challenge",
  released 2021-09-16. This is the release the published leaderboard
  corresponds to (verified against the live repo README leaderboard table and
  the releases page; v1.0 is the later of the two releases, v1 = 2021-09-15).

### Published leaderboard (the target this milestone reproduces)

| Method   | µ(RMSE) | σ(RMSE) | λx (km) |
|----------|---------|---------|---------|
| BASELINE | 0.85    | 0.09    | 140     |
| DUACS    | 0.88    | 0.07    | 152     |

---

## Task 1 — Their scoring API (recon)

Their scoring code lives under `vendor/2021a_SSH_mapping_OSE/src/` and is
imported by the other modules as `src.mod_*` (so the **submodule root**, not
`src/`, goes on `sys.path`). The pipeline is transcribed verbatim from
`notebooks/example_eval_baseline.ipynb`:

| Step | Function | Module | Returns |
|---|---|---|---|
| Load withheld track | `read_l3_dataset(file, lon/lat/time bounds)` | `src.mod_inout` | `xarray.Dataset` |
| Interp map → track | `interp_on_alongtrack(map_path_or_[url,session], ds_track, bounds, is_circle)` | `src.mod_interp` | `(time, lat, lon, ssh_track, ssh_map_interp)` |
| RMSE scores | `compute_stats(time, lat, lon, ssh_track, ssh_map_interp, bin_lon, bin_lat, bin_time, out_nc, out_ts_nc)` | `src.mod_stats` | `(mu, sigma)` = `(leaderboard_nrmse, leaderboard_nrmse_std)` |
| PSD | `compute_spectral_scores(time, lat, lon, ssh_track, ssh_map_interp, length_scale, delta_x, delta_t, out_nc)` | `src.mod_spectral` | writes PSD NetCDF |
| λx | `find_wavelength_05_crossing(psd_nc)` | `src.mod_plot` | `lambda_x` (km, PSD-score 0.5 crossing) |

Notes:
- `interp_on_alongtrack` accepts a **local path string** (→ `read_l4_dataset`)
  or `[url, session]` (→ `read_l4_dataset_from_aviso`). Our `their_eval.score`
  uses the local-path branch.
- `mod_plot` top-imports `hvplot.xarray` purely for interactive plotting; the
  scoring function we call (`find_wavelength_05_crossing`) never touches it, so
  `their_eval._prepare_imports` stubs `hvplot` rather than installing the
  heavy holoviews stack. `pyinterp` (real dep) was added via `pixi add`.

### Eval definition (the published-leaderboard eval parameters)

Transcribed from `example_eval_baseline.ipynb` cell 5; encoded as constants in
`src/sverdrup/validation/their_eval.py`:

| Quantity | Value |
|---|---|
| Eval region box | lon **295–305**, lat **33–43** (smaller than the 285–315/23–53 map box) |
| Time window | 2017-01-01 → 2017-12-31 |
| Spatial binning | `bin_lon_step = bin_lat_step = 1.0°`, `bin_time_step = '1D'` |
| Spectral δt | `0.9434 s` (Cryosat-2 sampling) |
| Ground-track velocity | `6.77 km/s` |
| Spectral δx | `velocity · δt` km |
| Segment length scale | `1000 km` |

### Reference frame (relevant to Task 3/Task 4)

In `interp_on_alongtrack` the along-track SSH reference is reconstructed as
**`ssh = sla_unfiltered + mdt − lwe`** from the L3 track file's own
`sla_unfiltered`, `mdt`, `lwe` variables. The map (L4) carries variable `ssh`
on coords `lon`/`lat`/`time`. Full SLA/SSH/MDT resolution is Task 3.

### Withheld vs mapping missions

- Mapping (five): SARAL/Altika (`alg`), Jason-2 (`j2`), Jason-3 (`j3`),
  Sentinel-3A (`s3a`), Haiyang-2A (`h2g`).
- Withheld for eval (never used in mapping): **Cryosat-2 (`c2`)**, file
  `dt_gulfstream_c2_phy_l3_20161201-20180131_285-315_23-53.nc`.

---

## Task 1 — pyinterp version skew (the import/version surprise)

Their 2021 code targets a 2021-era pyinterp; our env has **pyinterp 2026.6.0**,
which is API-incompatible in several places. Rather than build a full 2021 conda
env (the user chose "import their src into our env"), `their_eval._shim_pyinterp_axis`
installs faithful, exact API-compat shims (kwarg rename / type coercion /
restored accessor — never a scoring-logic change):

| Their 2021 call | Modern break | Shim |
|---|---|---|
| `Axis(values, is_circle=True)` | kwarg renamed to `period`; needs float64 ndarray | `period=360.0`/`None`; `np.asarray(values, float64)` |
| `TemporalAxis(DataArray)` | needs datetime64 ndarray | `np.asarray(values)` |
| `z_axis.safe_cast(times)` | method removed (modern `trivariate` takes datetime64) | subclass restores `safe_cast` = cast to axis dtype |
| `Grid3D(..., var.data)` | needs materialized float64 (dask/float32 fails: `std::bad_cast`) | `np.asarray(values, float64)` |
| `Binning2D(...).variable(name)` | accessor removed; per-stat methods now | forwarding proxy maps `variable(name)` -> `getattr(b, name)()` |

The shims are **validated**: with them, their eval on the shipped DUACS map
reproduces the published DUACS leaderboard row to within tolerance (below), so
the modern pyinterp is numerically faithful through this path.

## Task 1 — Reproduced numbers

> **PREMISE PROVEN VIA DUACS. LITERAL BASELINE STILL PENDING ITS MAP.**

**Data-access reality (build sandbox):** `tds.aviso.altimetry.fr` (which hosts
`OSE_ssh_mapping_BASELINE.nc`) does **not resolve** from this environment; the
unauthenticated MEOM mirror (`ige-meom-opendap.univ-grenoble-alpes.fr`) **is**
reachable and ships the L3 tracks (incl. Cryosat-2) and the DUACS/MIOST/BFN/
4dvarNet/neurost/convlstm maps — but **not** the OI BASELINE map (404).

The gate's literal artifact (their BASELINE map) is **unobtainable** — the ODC
THREDDS is dead, the MEOM mirror lacks BASELINE, and AVISO SFTP holds only
operational products (full source recon in `methods_and_data_inventory.md`).

The de-risk **premise** ("their eval is ground truth; the pinned pipeline
reproduces a published leaderboard row from a shipped map; import + version
skew handled") is instead proven against **every classical method whose map
survives** — three independent published rows, all within tolerance:

| Method | Published µ/σ/λx | Reproduced µ/σ/λx |
|---|---|---|
| DUACS | 0.88 / 0.07 / 152 | **0.877 / 0.065 / 152.3** |
| MIOST | 0.89 / 0.08 / 139 | **0.887 / 0.085 / 139.7** |
| BFN   | 0.88 / 0.06 / 122 | **0.879 / 0.065 / 122.0** |

Three-row agreement is a stronger de-risk than the single BASELINE row the gate
named. `tests/validation/test_their_eval_spike.py` parametrizes over BASELINE +
DUACS; DUACS **passes**, BASELINE **skips** (map unobtainable). The literal
BASELINE row is moot for the milestone: `sverdrup`'s own OI run *produces* the
BASELINE-equivalent map (Task 6) — that generated map is what Task 7 scores.

| Metric | Published BASELINE | Reproduced | Note |
|---|---|---|---|
| µ(RMSE) | 0.85 | _n/a — map unobtainable_ | covered 3× by DUACS/MIOST/BFN |
| σ(RMSE) | 0.09 | _n/a_ | |
| λx (km) | 140  | _n/a_ | |
