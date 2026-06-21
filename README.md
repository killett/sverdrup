# regatta

A regional SSHA (sea-surface-height anomaly) reconstruction framework with first-class,
rigorous predictive-distribution uncertainty. Phase 1 wires a single space-time tile
end-to-end (OSSE + OSE) through a hexagonal stack: a hand-rolled dense space-time GP / optimal
interpolation exposes native covariance and whole-field samples behind a `CovarianceOperator`
seam, and each unit of work returns a *Persisted* `Product` bundle (mean + exact marginal
variance + low-rank factor + clipped diagonal residual + eval-point predictions) reduced
on-worker while the exact operator is still live.

## Installation

Dependencies are managed with [pixi](https://pixi.sh):

```
pixi install
```

## Quick usage

Run a config-driven pipeline over a regional tile (OSSE on the committed fixtures):

```
pixi run python -m regatta tests/integration/config_osse.json
```

This windows the observations, dispatches the solve through a `dask.distributed` LocalCluster,
writes the persisted `Product` to an fsspec URL, and prints evaluator scores (RMSE vs truth,
calibration, ground-track power).

Programmatically:

```python
from regatta.adapters.odc.fixtures import FixtureSource
from regatta.application.pipeline import PipelineInputs, run_pipeline

src = FixtureSource("tests/fixtures/natl60_tiny.nc", ref_path="tests/fixtures/natl60_ref_tiny.nc")
product, scores = run_pipeline(PipelineInputs(
    mode="OSSE", method_name="oi", source=src, out_url="file:///tmp/osse.zarr",
    lon_range=(-64, -56), lat_range=(34, 42), time_range=(0, 5), output_times=[2.0],
    params={"length_scale": 300.0, "time_scale": 10.0, "variance": 0.05},
))
```

## Common tasks

```
pixi run test        # pytest (the opt-in oracle is skipped without REGATTA_ODC_DATA)
pixi run lint        # ruff check
pixi run format      # ruff format
pixi run typecheck   # mypy
```

The correctness oracle (reproducing the ODC OI leaderboard number) is opt-in — see
[`docs/oracle-runbook.md`](docs/oracle-runbook.md).

## Project structure

```
src/regatta/
  core/          # pure protocols + value objects (grid, types, distribution, product, ports, ...)
  distributions/ # Gaussian / Ensemble / Persisted distributions + lifting adapters
  methods/       # space-time Matern-3/2 kernel, Cholesky solver, GP/OI (Method 1), trivial (Method 0)
  derived/       # CRS-aware first-difference (real) + committed stubs
  eval/          # accuracy, calibration (+ polar-void), ground-track evaluators
  adapters/      # dask executor, fsspec result sink, ODC data sources + fixtures
  application/   # unit of work, solve_unit, splits, run config, end-to-end pipeline
tests/           # unit, integration, oracle; tiny committed NetCDF fixtures
docs/            # architecture design, implementation plan, oracle runbook
```

See `PROGRESS.md` for the running project notebook (decisions, gotchas, deviations).
