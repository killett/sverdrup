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

## Task 2 — Access adapter + live smoke read (gate 2)

- **Verified live source:** the MEOM mirror catalog resolves and serves files,
  e.g. `…/thredds/fileServer/meomopendap/extract/MEOM/OCEAN_DATA_CHALLENGES/`
  `2021a-SSH-mapping-OSE/{dc_obs,dc_maps}/`. **Auth mechanism: none**
  (`access_method == "meom_mirror"`, unauthenticated).
- **Spec discrepancy from recon (important):** the plan/notebooks assume AVISO
  THREDDS (`tds.aviso.altimetry.fr`, HTTP Basic) — that host is **dead**
  (unresolvable everywhere). `access.fetch` therefore sends auth only for the
  `thredds`/`ftp` methods and none for `meom_mirror`. AVISO **SFTP**
  (`ftp-access.aviso.altimetry.fr:2221`, paramiko, AVISO creds) is alive but
  carries only operational products, not the challenge maps.
- **Captured live smoke read:** `access.fetch` downloaded
  `dc_maps/OSE_ssh_mapping_DUACS.nc` (4,684,262 bytes) and `xarray.open_dataset`
  succeeded — dims `time=365, lat=40, lon=40`, var `ssh`, coords `lat/lon/time`.
- **Retry:** `is_retryable` retries transport errors + 5xx only; 401/404 raise
  (unit-tested in `tests/validation/test_access.py`).

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

---

## Task 3 — baseline_oi parameter extraction (gate 1)

Source: `vendor/2021a_SSH_mapping_OSE/notebooks/baseline_oi.ipynb` (v1.0),
read end-to-end. The OI kernel itself is `src/mod_oi.py::oi_core`.

### Parameter mapping (value → notebook → our setting)

| Quantity | Notebook (cell) | Value | Our setting (`params.py`) |
|---|---|---|---|
| Domain lon | cell 7 `lon_min/lon_max` | 295–305 | `LON_MIN/LON_MAX` → `GridSpec` |
| Domain lat | cell 7 `lat_min/lat_max` | 33–43 | `LAT_MIN/LAT_MAX` → `GridSpec` |
| Grid step | cell 7 `dx`,`dy` | 0.2° | `GRID_RES_DEG` |
| Grid time | cell 7 `time_min/max`,`dt` | 2017-01-01…12-31, 1 day | `TIME_MIN/MAX` |
| Zonal decorrelation | cell 7 `Lx` | 1.0° | `SPATIAL_CORR_DEG` → `length_scale` (km, analog) |
| Merid. decorrelation | cell 7 `Ly` | 1.0° | `SPATIAL_CORR_DEG` (Lx==Ly) |
| Temporal decorrelation | cell 7 `Lt` | 7 days | `TEMPORAL_CORR_DAYS` → `time_scale` |
| Noise level | cell 7 `noise` | 0.05 (5%) | `OBS_NOISE_STD`; `OBS_NOISE_VARIANCE = 0.0025` → `DiagonalErrorModel` (Task 4) |
| Signal variance | implicit (`oi_core`) | 1.0 (B is a correlation) | `SIGNAL_VARIANCE` → `variance` |
| Obs influence window | `oi_core` `< 2*Lt` | ±14 days | `TEMPORAL_HALF_WINDOW_DAYS` |
| Obs time-coarsening | cell 14 `coarsening` | mean every 5 | `COARSEN_TIME` (applied in Task 4) |
| Mapping inputs | cell 11 | alg, j3, s3a, h2g, j2g, j2n (NOT c2) | Task 4 |

`baseline_config()` returns `(ConstantProvider, GridSpec, 14.0)` and is accepted
by `OptimalInterpolation.solve` (smoke: output mean shape (52,51) == grid.shape).

### Reference frame (SLA / SSH / MDT) — RESOLVED

- **Mapping space = SLA.** `oi_core` maps the obs variable **`sla_unfiltered`**
  (NB: unfiltered, not `sla_filtered`). The OI output field `gssh` is SLA.
- **Output conversion.** `reformate_oi_output` renames `gssh`→`sla` and writes
  **`ssh = sla + mdt`**, with `mdt` interpolated from the challenge `mdt.nc`.
  The shipped map therefore carries both `sla` and `ssh`; the eval reads `ssh`.
- **Eval space = SSH.** `interp_on_alongtrack` reconstructs the track as
  `ssh = sla_unfiltered + mdt − lwe`. So: map SLA → add MDT → compare SSH.
- **Implication for us:** our OI maps `sla_unfiltered`; the output adapter
  (Task 5) must add MDT to produce `ssh`. We need `mdt.nc` — it is on the MEOM
  mirror's grid-data area (to fetch in Task 4/5).

### DECISIVE FINDING — kernel mismatch (needs an owner decision before Task 6)

Their BASELINE covariance (`oi_core`) is:

    B = exp( −(Δlon/Lx)² − (Δlat/Ly)² − (Δt/Lt)² )      # Gaussian, degrees, anisotropic
    R = diag(noise²)                                     # signal variance ≡ 1

Our `OptimalInterpolation.solve` hardcodes `Matern32SpaceTime`:

    B = variance · M32(‖Δx‖_km / length_scale) · M32(Δt / time_scale)   # Matérn-3/2, km, isotropic

These differ on **three** axes: (1) **shape** — Gaussian vs Matérn-3/2;
(2) **geometry** — degrees (no cos-lat) vs great-circle km (with cos-lat);
(3) **anisotropy** — separate Lx/Ly vs a single isotropic length. At Lx=Ly=1°
the degree-space isotropy is physical *an*isotropy (1° lon ≈ 88 km at 38°N vs
1° lat ≈ 111 km). `baseline_config` maps `length_scale = 1.0° × 111.195 km/° ≈
111 km` as an **analog only**.

**Consequence:** our current engine cannot reproduce the literal BASELINE row
(0.85/0.09/140). The two options for Task 6:

- **(a) Faithful** — add a Gaussian, anisotropic, degree-space kernel
  (`variance, Lx, Ly, Lt`) and a kernel-selection seam in `solve`. Reproduces
  BASELINE exactly; touches the core engine (the project pins Matérn-3/2, so
  this is an additive seam, not a replacement).
- **(b) Matérn analog** — run the Matérn config above and accept it scores
  *differently* from BASELINE; report it as a Matérn-OI variant, not a
  reproduction.

This is the gate-1 decision to confirm before Task 6.

**OWNER DECISION (gate 1, 2026-06-27): option (a) — add a faithful Gaussian,
anisotropic, degree-space kernel + a kernel-selection seam in
`OptimalInterpolation.solve` (Matérn-3/2 left untouched), so Task 6 reproduces
the literal BASELINE row. Parameter mapping + SLA→+MDT→SSH reference frame
CONFIRMED.** The Gaussian kernel is implemented in Task 6 (where it is used);
`baseline_config` keeps the Matérn-analog provider for back-compat, and a
`baseline_kernel()` factory will supply the faithful kernel to the run.

## Task 4 — Input adapter + test fixtures

- `load_mapping_obs` loads `sla_unfiltered` (the variable `oi_core` maps),
  time-coarsened (mean every `COARSEN_TIME=5`), labelled by mission; spin-up
  (pre-2017) obs kept. Withheld-leak guard: `_mission_code` raises on any file
  not in `MAPPING_MISSIONS` (so the Cryosat-2 `c2` file is rejected).
- `load_eval_track` returns an `EvalTrack` (not an `ObsWindow`) in SSH space
  (`sla_unfiltered + mdt - lwe`), restricted to 2017.
- **Fixture provenance** (`tests/validation/fixtures/`, committed, ~40-60 KB):
  subsets of the MEOM-mirror L3 files, box 300-304/36-39, late-2016→early-2017,
  vars `sla_unfiltered/sla_filtered/mdt/lwe` — `l3_alg_subset.nc` (mapping,
  spans the 2017 boundary) and `l3_c2_subset.nc` (withheld eval, 402 spin-up +
  503 2017 points).
