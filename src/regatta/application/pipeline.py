"""End-to-end pipeline wiring: source -> executor.solve -> evaluate -> sink (spec 7)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

import numpy as np

from regatta.adapters.executor_dask import DaskExecutor, ExecutorConfig
from regatta.adapters.storage_fsspec import FsspecResultSink
from regatta.application.splits import make_splits
from regatta.application.uow import UnitOfWork
from regatta.core.evaluation import ContextKey, EvalContext, Registry
from regatta.core.grid import GridSpec
from regatta.core.observations import DiagonalErrorModel, ObsWindow
from regatta.core.parameters import ConstantProvider
from regatta.core.product import Product
from regatta.core.seeding import derive_seed
from regatta.eval.accuracy import Accuracy
from regatta.eval.calibration import Calibration
from regatta.eval.groundtrack import GroundTrack

Range = tuple[float, float]


@dataclass
class PipelineInputs:
    """All inputs to one end-to-end pipeline run (OSSE or OSE)."""

    mode: str
    method_name: str
    source: object
    out_url: str
    lon_range: Range
    lat_range: Range
    time_range: Range
    output_times: list[float]
    params: dict[str, float]
    grid_resolution_deg: float = 1.0
    executor: ExecutorConfig = field(default_factory=ExecutorConfig)
    rank: int = 20


def _grid(inp: PipelineInputs) -> GridSpec:
    """Build the regular lon/lat output grid for the run."""
    lons = np.arange(inp.lon_range[0], inp.lon_range[1] + 1e-9, inp.grid_resolution_deg)
    lats = np.arange(inp.lat_range[0], inp.lat_range[1] + 1e-9, inp.grid_resolution_deg)
    return GridSpec.lonlat(lons, lats)


def run_pipeline(inp: PipelineInputs) -> tuple[Product, dict[str, Any]]:
    """Run source -> dask solve -> sink -> evaluate and return ``(product, scores)``.

    Args:
        inp: The pipeline inputs.

    Returns:
        The persisted Product and the evaluator score dictionary.
    """
    grid = _grid(inp)
    src = cast(Any, inp.source)
    obs = src.window(
        lon_range=inp.lon_range, lat_range=inp.lat_range, time_range=inp.time_range
    )
    train_obs, eval_locs, withheld_vals = _prepare(inp, obs)
    params = ConstantProvider(inp.params)
    seed = derive_seed(inp.method_name, params.params_key(), "tile0", 0)
    uow = UnitOfWork(
        "tile0",
        inp.method_name,
        params,
        "train",
        seed,
        inp.output_times,
        train_obs,
        grid,
        eval_locations=eval_locs,
        derived_names=["firstdifference"],
        rank=inp.rank,
    )

    with DaskExecutor(inp.executor) as ex:
        product = ex.submit(uow)

    FsspecResultSink().write(product, inp.out_url)
    scores = _evaluate(inp, product, grid, eval_locs, withheld_vals)
    return product, scores


def _subset_obs(obs: ObsWindow, idx: np.ndarray) -> ObsWindow:
    """Return the sub-window of ``obs`` at the given indices (preserves error variances)."""
    coords = obs.coords()
    var = np.diag(obs.error_model.as_matrix(len(obs)))
    mission = obs.mission[idx] if obs.mission is not None else None
    return ObsWindow.from_arrays(
        coords[idx, 0],
        coords[idx, 1],
        coords[idx, 2],
        obs.values()[idx],
        DiagonalErrorModel(var[idx]),
        mission=mission,
    )


def _prepare(
    inp: PipelineInputs, obs: ObsWindow
) -> tuple[ObsWindow, np.ndarray | None, np.ndarray | None]:
    """Return ``(train_obs, eval_locations, withheld_values)``.

    OSSE trains on all observations (truth supplies evaluation). OSE withholds the
    CryoSat-2 mission from training and returns its locations/values for evaluation,
    so the eval signal is genuinely independent (no autocorrelation leak).
    """
    if inp.mode == "OSE" and obs.mission is not None:
        split = make_splits(obs, by="mission", locked_missions=["c2"])
        train_obs = _subset_obs(obs, split.train_idx)
        coords = obs.coords()
        eval_locs = coords[split.locked_test_idx].copy()
        eval_locs[:, 2] = inp.output_times[0]
        withheld_vals = obs.values()[split.locked_test_idx]
        return train_obs, eval_locs, withheld_vals
    return obs, None, None


def _evaluate(
    inp: PipelineInputs,
    product: Product,
    grid: GridSpec,
    eval_locs: np.ndarray | None,
    withheld_vals: np.ndarray | None,
) -> dict[str, Any]:
    """Assemble the evaluation context and run every applicable evaluator.

    OSSE calibrates/scores against the gridded truth; OSE scores against the
    withheld CryoSat-2 along-track at the exact eval-point predictions. The
    evaluator spine is identical — only the source and context differ.
    """
    pt = product.per_time[0]
    base = pt.base
    items: dict[ContextKey, object] = {
        ContextKey.ORBIT_GEOMETRY: {"track_spacing_nodes": 4}
    }
    result: dict[str, np.ndarray] = {
        "field": base.fields.mean,
        "grid_mean": base.fields.mean,
    }
    if inp.mode == "OSSE":
        truth = cast(Any, inp.source).truth(inp.output_times[0], grid)
        truth = np.asarray(truth)
        items[ContextKey.TRUTH] = {"field": truth}
        items[ContextKey.WITHHELD_OBS] = {"values": truth.ravel()}
        result["eval_mean"] = base.fields.mean.ravel()
        result["eval_var"] = base.marginal_variance().ravel()
    elif (
        eval_locs is not None
        and withheld_vals is not None
        and pt.eval_points is not None
    ):
        items[ContextKey.WITHHELD_OBS] = {"values": withheld_vals}
        result["eval_mean"] = pt.eval_points.mean
        result["eval_var"] = pt.eval_points.variance
    ctx = EvalContext(items)
    reg = Registry([Accuracy(), Calibration(), GroundTrack(track_wavenumber=4)])
    scores: dict[str, Any] = dict(reg.run(result, ctx))
    scores["context_keys"] = {k.name for k in ctx.keys()}
    return scores
