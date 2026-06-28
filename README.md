# sverdrup

**sverdrup** reconstructs regional sea-surface-height anomaly (SSHA) fields from sparse
satellite altimetry, with *first-class, rigorous per-gridpoint uncertainty* — every output is a
predictive distribution (mean + exact marginal variance + coherent whole-field samples + a typed
provenance chain), not just a point estimate. It ships three interchangeable methods behind one
method-agnostic spine — a dense space-time Gaussian-process / **optimal interpolation** (`oi`), a
sparse-precision **Matérn GMRF** (`gmrf`, incl. latitude-varying correlation length), and a
**trivial** inverse-distance baseline (`trivial`) — and blends overlapping tiles into one
seam-free regional product with coherent cross-tile uncertainty. Reconstructions are scored two
honest ways: **OSSE** (against gridded truth) and **OSE** (against withheld along-track data).

## Table of contents

- [Quickstart](#quickstart)
- [Installation](#installation)
- [Concepts in 60 seconds](#concepts-in-60-seconds)
- [Running a reconstruction](#running-a-reconstruction)
  - [CLI (config file)](#cli-config-file)
  - [Config keys](#config-keys)
  - [Programmatic API](#programmatic-api)
  - [Methods and their parameters](#methods-and-their-parameters)
- [Cheatsheet](#cheatsheet)
- [Output](#output)
- [Troubleshooting](#troubleshooting)
- [Links and license](#links-and-license)

## Quickstart

```bash
pip install 'sverdrup[all]'
```

Reconstruct an OSSE tile on the committed tiny fixtures and print the scores:

```python
from sverdrup.adapters.odc.fixtures import FixtureSource
from sverdrup.application.pipeline import PipelineInputs, run_pipeline

src = FixtureSource(
    "tests/fixtures/natl60_tiny.nc", ref_path="tests/fixtures/natl60_ref_tiny.nc"
)
product, scores = run_pipeline(PipelineInputs(
    mode="OSSE", method_name="oi", source=src, out_url="file:///tmp/osse.zarr",
    lon_range=(-64, -56), lat_range=(34, 42), time_range=(0, 5), output_times=[2.0],
    params={"length_scale": 300.0, "time_scale": 10.0, "variance": 0.05},
))
print(scores)  # RMSE vs truth, calibration (reduced chi^2, coverage), ground-track power
```

Or run the same thing from the shipped config:

```bash
python -m sverdrup tests/integration/config_osse.json
```

> The `tests/...` fixture paths are repo-relative — clone the repo to run these examples
> as-is, or point `obs_path` / `ref_path` (and the `FixtureSource` arguments) at your own
> NetCDF observations.

## Installation

Requires **Python ≥ 3.12**.

```bash
pip install sverdrup            # core library API only (lightweight)
pip install 'sverdrup[all]'     # everything needed to RUN the pipeline (recommended)
```

Extras (install only what you need):

| Extra     | Pulls in                                       | Needed for |
|-----------|------------------------------------------------|------------|
| `[dask]`  | `dask[distributed]`                            | the parallel executor (any pipeline run) |
| `[io]`    | `xarray`, `fsspec`, `netcdf4`, `requests`, …   | reading NetCDF obs + writing the zarr product |
| `[all]`   | `[dask]` + `[io]`                              | running reconstructions end-to-end |

> The bare `import sverdrup` surface (core grid/types/distributions) works with no extras. The
> pipeline (`run_pipeline`, `python -m sverdrup`) eagerly imports the dask executor and the I/O
> stack, so it needs `[all]`.

**conda-forge:** packaging is in progress (a `staged-recipes` PR is open). Once merged,
`conda install -c conda-forge sverdrup` will track every PyPI release automatically.

## Concepts in 60 seconds

- **Mode — OSSE vs OSE.** `OSSE` scores the reconstructed grid against gridded "truth" (accuracy
  + calibration). `OSE` withholds a real mission (CryoSat-2) from training and scores the
  reconstruction against that withheld along-track data — no truth leak.
- **Method.** `oi` (exact dense GP, full space-time kernel), `gmrf` (sparse-precision Matérn
  SPDE, fast + nonstationary-capable), `trivial` (inverse-distance baseline / degradation path).
- **The `Product`.** Each output time carries a *Persisted* predictive distribution: mean, **exact**
  marginal variance, coherent whole-field samples, off-grid eval-point predictions, and a typed
  **provenance** chain that records every uncertainty transform and any known bias (e.g. a
  conservative halo residual, or `DEGRADED_COHERENCE` on the trivial path).
- **Tiling and blend.** A region is split into overlapping tiles, each solved independently, then
  crossfaded into one seam-free product. `oi`/`gmrf` keep cross-tile uncertainty **coherent**; the
  `trivial` path is honestly **degraded** and flags the coherence loss in provenance.

## Running a reconstruction

### CLI (config file)

```bash
python -m sverdrup <config.json>
```

The shipped example, `tests/integration/config_osse.json`:

```json
{
  "mode": "OSSE",
  "method": "oi",
  "obs_path": "tests/fixtures/natl60_tiny.nc",
  "ref_path": "tests/fixtures/natl60_ref_tiny.nc",
  "out_url": "file:///tmp/sverdrup_osse.zarr",
  "lon_range": [-64, -56],
  "lat_range": [34, 42],
  "time_range": [0, 5],
  "output_times": [2.0],
  "params": {"length_scale": 300.0, "time_scale": 10.0, "variance": 0.05},
  "grid_resolution_deg": 1.0,
  "executor": {"n_processes": 2, "threads_per_process": 1},
  "rank": 20
}
```

### Config keys

| Key                  | Type            | Meaning |
|----------------------|-----------------|---------|
| `mode`               | `"OSSE"`/`"OSE"` | scoring mode (gridded truth vs withheld along-track) |
| `method`             | `"oi"`/`"gmrf"`/`"trivial"` | reconstruction method |
| `obs_path`           | path            | observation NetCDF |
| `ref_path`           | path (optional) | gridded-truth NetCDF (OSSE) |
| `out_url`            | fsspec URL      | where the zarr product is written (`file://`, `s3://`, …) |
| `lon_range`/`lat_range` | `[min, max]` | region bounds in degrees |
| `time_range`         | `[min, max]`    | training window in days |
| `output_times`       | `[float, …]`    | output time(s) in days |
| `params`             | object          | method parameters (see table below) |
| `grid_resolution_deg`| float (def `1.0`) | target grid spacing |
| `executor`           | object          | `{n_processes, threads_per_process}` for the dask LocalCluster |
| `rank`               | int (def `20`)  | low-rank factor rank for the persisted product |

### Programmatic API

Single tile — `run_pipeline(PipelineInputs(...)) -> (product, scores)` (see [Quickstart](#quickstart)).

Regional, multi-tile coherent blend — `run_tiled_pipeline(inputs, partition)`:

```python
from sverdrup.application.pipeline import PipelineInputs, run_tiled_pipeline
from sverdrup.application.tiling import LonLatPartition, ScaleAwareHalo
from sverdrup.adapters.executor_dask import ExecutorConfig
from sverdrup.adapters.odc.fixtures import FixtureSource
from sverdrup.core.parameters import ConstantProvider

inp = PipelineInputs(
    mode="OSSE", method_name="gmrf",
    source=FixtureSource("tests/fixtures/natl60_tiny.nc",
                         ref_path="tests/fixtures/natl60_ref_tiny.nc"),
    out_url="file:///tmp/blend.zarr",
    lon_range=(-64, -56), lat_range=(34, 42), grid_resolution_deg=1.0,
    time_range=(0, 5), output_times=[2.0],
    params={"range": 300.0, "variance": 0.05, "temporal_taper_scale": 10.0},
    executor=ExecutorConfig(n_processes=2, threads_per_process=1), rank=20,
)
partition = LonLatPartition(
    n_lon=3, n_lat=1, halo=ScaleAwareHalo(k=1.0),
    correlation_length=ConstantProvider({"correlation_length": 300.0}),
    stencil_radius_km=10.0,
)
blends, scores = run_tiled_pipeline(inp, partition)   # one BlendedDistribution per output time
```

### Methods and their parameters

| `method`   | `params`                                                  | Notes |
|------------|-----------------------------------------------------------|-------|
| `oi`       | `length_scale` (km), `time_scale` (days), `variance`      | exact dense space-time GP / OI |
| `gmrf`     | `range` (km), `variance`, `temporal_taper_scale` (days)   | sparse Matérn SPDE; `range` may be a latitude-varying field (nonstationary κ) |
| `trivial`  | `{}` (none)                                               | inverse-distance baseline; degradation path |

## Cheatsheet

```bash
# install (everything needed to run)
pip install 'sverdrup[all]'

# run a reconstruction from a config file
python -m sverdrup path/to/config.json

# minimal OSSE config: copy tests/integration/config_osse.json and edit
#   mode/method/paths/ranges/output_times/params

# methods + params
#   oi      -> {"length_scale": 300.0, "time_scale": 10.0, "variance": 0.05}
#   gmrf    -> {"range": 300.0, "variance": 0.05, "temporal_taper_scale": 10.0}
#   trivial -> {}

# OSE (withheld along-track) instead of OSSE: set "mode": "OSE" and drop ref_path
```

## Output

`run_pipeline` returns `(product, scores)`; `run_tiled_pipeline` returns
`(blends, scores)`. The product is written to `out_url` as zarr (via fsspec, so local
`file://`, `s3://`, `gcs://`, … all work). Each per-time entry carries the mean, exact marginal
variance, coherent samples, off-grid eval-point predictions, and the typed uncertainty
**provenance** (every transform + any `KnownBias`). `scores` is the merged evaluator dictionary:
RMSE vs truth, calibration (reduced χ², 1σ coverage) for OSSE; withheld-track RMSE for OSE; plus
ground-track power.

## Validation — reproduces the 2021a SSH-mapping OSE BASELINE

Sverdrup's OI engine reproduces the published **2021a SSH Mapping Data Challenge**
BASELINE leaderboard row, scored by the challenge's *own* evaluation code (vendored
as a submodule and driven through `sverdrup.validation`):

| Method | µ(RMSE) | σ(RMSE) | λx (km) |
|--------|---------|---------|---------|
| **sverdrup OI** | **0.853** | **0.090** | **140.9** |
| BASELINE (published) | 0.85 | 0.09 | 140 |
| DUACS (published) | 0.88 | 0.07 | 152 |

**Verdict: PASS** (µ tolerance ±0.03, never loosened). The challenge's eval is
independently trusted — it reproduces the published DUACS, MIOST, and BFN rows to
within tolerance — and our own parallel skill score agrees with it on our map
(Δ 0.005). The reproduction required a faithful Gaussian, anisotropic,
degree-space kernel (`GaussianSpaceTimeDegrees`) and the SLA→SSH MDT reference
frame; details, the decomposed read, and the data-source notes are in the
[`docs/validation/`](docs/validation/) records below.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ModuleNotFoundError: No module named 'dask'` (or `xarray`, `fsspec`, `netcdf4`) | Install the run extras: `pip install 'sverdrup[all]'`. The core install is deliberately light. |
| Oracle / ODC-data tests are **skipped** | Expected offline. They are opt-in: set `SVERDRUP_ODC_DATA` to a cached NATL60 window — see [`docs/oracle-runbook.md`](docs/oracle-runbook.md). |
| Want output somewhere other than local disk | `out_url` is any fsspec URL — `s3://bucket/key.zarr`, `gcs://…`, etc. (install the matching fsspec backend). |
| Reconstruction is slow / over-subscribes CPUs | Tune `executor` (`n_processes`, `threads_per_process`). One BLAS thread per worker is usually fastest; set thread env vars *before* numpy/BLAS loads. |
| macOS install fails to solve a Linux-only dependency | A few conda deps are linux-64-only; this affects the pixi dev environment, not the PyPI install. Use `pip install 'sverdrup[all]'`. |

## Links and license

- [`docs/validation/RESULT.md`](docs/validation/RESULT.md) — the 2021a BASELINE reproduction result (table + decomposed read); [`docs/validation/parameter_audit_trail.md`](docs/validation/parameter_audit_trail.md) — full parameter/eval/MDT audit trail
- [`docs/oracle-runbook.md`](docs/oracle-runbook.md) — opt-in correctness oracle (reproduce the ODC OI leaderboard number)
- [`docs/`](docs/) — architecture design + implementation plans; [`conda-recipe/`](conda-recipe/) — conda-forge packaging
- `PROGRESS.md` — running project notebook (decisions, gotchas, deviations)

Licensed under **Apache-2.0**.
