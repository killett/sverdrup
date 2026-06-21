# Correctness Oracle Runbook

This runbook documents how to reproduce the ODC (Ocean Data Challenge) optimal-interpolation
(OI) leaderboard numbers with `regatta`, and how the opt-in oracle test is wired so it stays out
of routine CI.

## What runs by default vs. on demand

| Test | When it runs | Asserts |
| --- | --- | --- |
| `test_fixture_smoke_rmse_finite_and_sane` | **Always** (`pixi run test`) | Pipeline RMSE on the committed **tiny** **fixture** is finite and within a loose ≤25% sanity band of a trivial all-zero prediction. |
| `test_oi_matches_odc_baseline_within_10pct` | **Only** when `REGATTA_ODC_DATA` is set (marked `@pytest.mark.oracle`, `skipif` otherwise) | OI RMSE on the **cached** 42-day NATL60 window is within **10%** of the recorded ODC OI baseline. |

The always-on **fixture** **smoke** guards against a pipeline that "runs" but produces a
degenerate map. The opt-in **oracle** guards numerical correctness against an external reference.

## Data endpoints (ODC THREDDS)

The 2020a SSH mapping NATL60 challenge serves its inputs over THREDDS. Pull these into the local
cache (`./data/cache/`, git-ignored):

- **OSSE nadir observations** — `2020a_SSH_mapping_NATL60` `dc_obs` tarball (`*.tar.gz`,
  ≈ 285 MB whole). Contains the simulated along-track nadir SLA used as the OI inputs.
- **Daily NATL60-CJM165 reference** — the **daily** CJM165 SSH reference file, clipped to the
  42-day evaluation window **2012-10-22 → 2012-12-02**.

> ⚠️ **Do NOT pull the 11 GB hourly NATL60 archive.** Use the daily reference only; the cached
> footprint stays a few hundred MB. The NATL60 challenge has no observation error, so `R` is
> effectively a small nugget for the oracle.

`src/regatta/adapters/odc/download.py::ODCCache` fetches whole files and OPeNDAP-subsets into the
cache; `path_for(url)` is deterministic and a re-download is skipped when the cache file exists.

## Cache layout

```
data/cache/                 # git-ignored
  natl60_obs.nc             # nadir observations (subset/clipped)
  natl60_ref_daily.nc       # daily CJM165 reference, clipped to the 42-day window
```

`tests/oracle/conftest.py::cached_natl60_source()` reads `REGATTA_ODC_DATA` and builds a
`Natl60Source` from `${REGATTA_ODC_DATA}/natl60_obs.nc` and `${REGATTA_ODC_DATA}/natl60_ref_daily.nc`.

## Enabling the oracle

Point `REGATTA_ODC_DATA` at the directory holding the cached files, then run only the oracle
marker:

```
export REGATTA_ODC_DATA=/abs/path/to/data/cache
pixi run test -m oracle
```

Without `REGATTA_ODC_DATA`, the oracle case is **skipped** cleanly and `pixi run test` (default)
never touches the network.

## One-shot full-challenge reproduction (out of routine CI)

Run once to regenerate the full leaderboard-scale product over the 0.25° / 42-day window
(`tests/oracle/conftest.py::full_window_config`); this is an 8-process × 4-thread job, not a CI step:

```
export REGATTA_ODC_DATA=/abs/path/to/data/cache
pixi run test -m oracle -v
```

## Baseline provenance

- `ODC_OI_BASELINE_RMSE = 0.0907` m — the recorded NATL60 2020a OI leaderboard RMSE, stored as a
  constant in `tests/oracle/test_oi_oracle.py`.
- Source: the 2020a SSH mapping NATL60 challenge OI baseline scoreboard.
- When refreshing this constant, record the retrieval date and the scoreboard revision alongside
  the value so the 10% tolerance stays anchored to a known reference.
