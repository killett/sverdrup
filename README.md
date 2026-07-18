# sverdrup

**sverdrup** reconstructs regional sea-surface-height anomaly (SSHA) fields from sparse
satellite altimetry, with *first-class, rigorous per-gridpoint uncertainty* — every output is a
predictive distribution (mean + marginal variance + coherent whole-field samples + a typed
provenance chain), not just a point estimate. It ships five interchangeable methods behind one
method-agnostic spine:

- `oi` — dense space-time Gaussian-process / **optimal interpolation**
- `gmrf` — sparse-precision **Matérn GMRF** (incl. latitude-varying correlation length)
- `fem` — mesh-based **FEM Matérn SPDE** (grid-agnostic by construction)
- `miost` — multiscale reduced-basis **MIOST-family ensemble** (calibrated per-gridpoint σ;
  validation-track)
- `trivial` — inverse-distance baseline

Overlapping tiles blend into one seam-free regional product with coherent cross-tile
uncertainty. Reconstructions are scored two ways: **OSSE** (against gridded truth) and
**OSE** (against withheld along-track data).

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
- **Method.**
  - `oi` — exact dense GP, full space-time kernel
  - `gmrf` — sparse-precision Matérn SPDE, fast + nonstationary-capable
  - `fem` — the same Matérn prior assembled on a Delaunay mesh; grid-agnostic by construction
  - `miost` — multiscale wavelet reduced-basis ensemble (see the Validation section)
  - `trivial` — inverse-distance baseline / degradation path
- **The `Product`.** Each output time carries a *Persisted* predictive distribution:
  - mean
  - marginal variance (**exact** for `oi`/`gmrf`/`fem`; ensemble-calibrated for `miost`)
  - coherent whole-field samples
  - off-grid eval-point predictions
  - a typed **provenance** chain recording every uncertainty transform and any known bias
    (e.g. a conservative halo residual, or `DEGRADED_COHERENCE` on the trivial path)
- **Tiling and blend.** A region is split into overlapping tiles, each solved independently, then
  crossfaded into one seam-free product. `oi`/`gmrf`/`fem` keep cross-tile uncertainty
  **coherent**; the `trivial` path is **degraded** and flags the coherence loss in provenance;
  `miost` is single-tile by design (its temporal windows blend within the one tile).

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
| `fem`      | `range` (km), `variance`, `temporal_taper_scale` (days)   | the same Matérn SPDE on a Delaunay mesh built from the grid; grid-agnostic |
| `miost`    | `spacing_alpha`, `log10_rho`, `q_slope`, `l_t_days` (tuned values ship in the registry) | validation-track only: geometry is fixed to the 2021a Gulf-Stream box — run from a clone via the challenge harness (see Validation) |
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
#   fem     -> {"range": 300.0, "variance": 0.05, "temporal_taper_scale": 10.0}
#   trivial -> {}

# OSE (withheld along-track) instead of OSSE: set "mode": "OSE" and drop ref_path
```

## Output

`run_pipeline` returns `(product, scores)`; `run_tiled_pipeline` returns
`(blends, scores)`. The product is written to `out_url` as zarr (via fsspec, so local
`file://`, `s3://`, `gcs://`, … all work). Each per-time entry carries the mean, marginal
variance, coherent samples, off-grid eval-point predictions, and the typed uncertainty
**provenance** (every transform + any `KnownBias`). `scores` is the merged evaluator dictionary:

- RMSE vs truth + calibration (reduced χ², 1σ coverage) for OSSE
- withheld-track RMSE for OSE
- ground-track power (both modes)

## Validation — scored by the 2021a SSH-mapping OSE challenge

Sverdrup's OI engine reproduces the published **2021a SSH Mapping Data Challenge**
BASELINE leaderboard row, and its MIOST-family method is tuned and accepted
through the same harness — everything scored by the challenge's *own* evaluation
code (vendored as a submodule and driven through `sverdrup.validation`):

| Method | µ(RMSE) | σ(RMSE) | λx (km) |
|--------|---------|---------|---------|
| **sverdrup OI** | **0.853** | **0.090** | **140.9** |
| BASELINE (published) | 0.85 | 0.09 | 140 |
| DUACS (published) | 0.88 | 0.07 | 152 |
| **sverdrup MIOST (6 missions, shipped)** | **0.8678** | **0.0823** | **151.2** |
| MIOST (published, 6 missions) | 0.89 | 0.08 | 139 |
| sverdrup MIOST (5 missions, calibration-lineage reference) | 0.857 | 0.080 | 156.4 |

The shipped six-mission row is the matched-convention comparison against the
published 0.89 (both assimilate six missions; DUACS 0.88 sits at DUACS-class
resolution 152 km, beside our 151.2). **Gap accounting** (recorded at the
Phase-12 flip): assimilating j3 closed **+0.0105 of the 0.0327 gap** to the
published MIOST row; the remainder is settings/tuning at matched inputs.
Named future levers — six-mission re-tuning (the §8 decision) and
structured/per-mission R — are recorded, neither elected.

**OI verdict: PASS** (µ tolerance ±0.03, never loosened). The challenge's eval is
independently trusted — it reproduces the published DUACS, MIOST, and BFN rows to
within tolerance — and our own parallel skill score agrees with it on our map
(Δ 0.005). The reproduction required a faithful Gaussian, anisotropic,
degree-space kernel (`GaussianSpaceTimeDegrees`) and the SLA→SSH MDT reference
frame; details, the decomposed read, and the data-source notes are in the
[`docs/validation/`](docs/validation/) records below.

**MIOST verdict: PASS** against its hard floor (µ ≥ 0.85, met at 0.8678 on the
shipped six-mission product; single withheld-CryoSat-2 acceptance touch per
generation, honest tally {miost5: 2, miost6: 1}). The five-mission row remains
the calibration-lineage reference: the s(x) field was fit there (Jason-3 held
out) and transferred frozen to the six-mission product.

**σ-semantics (transferred-and-verified):** the uncertainty is a 100-member
perturbed-observation ensemble rescaled by the spatially-varying,
regionally-calibrated field s(x) — a clipped low-order polynomial — fit on the
five-mission configuration (j3 held out) and transferred frozen; the
pre-registered expectation was mild over-coverage; MEASURED Δcoverage = −0.0043
vs the 0.7350 referent ≈ 0.6·SE (n_eff ≈ n/10.27, SE ≈ 0.0067) — transfer
NEUTRAL within noise; χ²_red 0.991; regional structure reproduces
region-by-region (max |Δ| 0.011; SW 0.775 → jet-core 0.678, still the weakest
region; August 0.636 remains the recorded seasonal trough, in band). It is a
*predictive* σ that includes representation error and unresolved scales, with
correlation structure from the exact posterior; the calibration touches σ only,
leaving the mean maps bit-identical (proven on the c2 acceptance touch). The
constellation-dependence caveat for LARGE constellation changes (the 1993-era
case) stands unchanged — this measured one small step, not that one.

The s(x) calibration layer is method-generic (Phase 9): any method's predictive
distribution can be wrapped in `CalibratedDistribution` and fitted per-product
by the shared harness (`sverdrup.application.calibration.harness`) — proven
identity-preserving on MIOST and demonstrated end-to-end on OI.

> **`sverdrup.validation` — and the MIOST tuning/gate harness and its
> diagnostics — are from-source tools, not part of the PyPI/conda package.**
> They need the vendored challenge submodule (`git submodule update --init`),
> the downloaded challenge data, and extra deps (`httpx`, `stamina`,
> `paramiko`, `pyinterp`) that ship only in the pixi dev environment — so they
> are not exercised by a bare `pip install sverdrup`. Run them from a clone.

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
- [`docs/validation/`](docs/validation/) MIOST records — method brief, windowed-equivalence + seam-dispersion diagnostics, Tier-3 similarity (two-row), calibration evidence
- [`docs/oracle-runbook.md`](docs/oracle-runbook.md) — opt-in correctness oracle (reproduce the ODC OI leaderboard number)
- [`docs/`](docs/) — architecture design + implementation plans; [`conda-recipe/`](conda-recipe/) — conda-forge packaging
- `PROGRESS.md` — running project notebook (decisions, gotchas, deviations)

Licensed under **Apache-2.0**.
