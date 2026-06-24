"""End-to-end pipeline wiring: source -> executor.solve -> evaluate -> sink (spec 7)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

import numpy as np

from sverdrup.adapters.executor_dask import DaskExecutor, ExecutorConfig
from sverdrup.adapters.storage_fsspec import FsspecResultSink
from sverdrup.application.splits import make_splits
from sverdrup.application.tiling import TilePartition, TilingCoordinator
from sverdrup.application.uow import UnitOfWork
from sverdrup.core.evaluation import ContextKey, EvalContext, Registry
from sverdrup.core.geometry import Tile, Window
from sverdrup.core.grid import GridSpec, PointSet
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
from sverdrup.core.parameters import ConstantProvider
from sverdrup.core.product import Product
from sverdrup.core.seeding import derive_seed
from sverdrup.distributions.blend import BlendedDistribution, BlendInput, BlendOperator
from sverdrup.distributions.persisted import PersistedPoints
from sverdrup.eval.accuracy import Accuracy
from sverdrup.eval.calibration import Calibration
from sverdrup.eval.groundtrack import GroundTrack

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


def run_tiled_pipeline(
    inp: PipelineInputs, partition: TilePartition
) -> tuple[list[BlendedDistribution], dict[str, Any]]:
    """Run the tiled blend: source -> partition -> per-tile dask solve -> blend -> evaluate.

    Reuses the Phase-1 ``_prepare``/evaluator spine. Each tile solves its windowed obs
    through the existing ``Executor`` (no new ports); the per-tile ``Persisted`` bases are
    crossfaded over the target grid, and (OSE) the withheld eval-point predictives are
    crossfaded over a ``PointSet`` — scored, never reconstructed from the grid.

    Args:
        inp: The pipeline inputs (OSSE or OSE).
        partition: The tile partition over the target grid.

    Returns:
        ``(blended_by_time, scores)`` — one ``BlendedDistribution`` per output time and
        the merged evaluator score dictionary.
    """
    grid = _grid(inp)
    src = cast(Any, inp.source)
    obs = src.window(
        lon_range=inp.lon_range, lat_range=inp.lat_range, time_range=inp.time_range
    )
    train_obs, eval_locs, withheld_vals = _prepare(inp, obs)
    params = ConstantProvider(inp.params)
    seed = derive_seed(inp.method_name, params.params_key(), "tiled", 0)
    coord = TilingCoordinator()

    def obs_for_tile(tile: Tile) -> ObsWindow:
        return _obs_in_window(train_obs, tile.extended_window)

    def eval_for_tile(tile: Tile) -> np.ndarray | None:
        if eval_locs is None:
            return None
        sub = eval_locs[_in_box(eval_locs, tile.extended_window)]
        return sub if sub.shape[0] > 0 else None

    with DaskExecutor(inp.executor) as ex:
        products = coord.gather(
            grid,
            partition,
            inp.method_name,
            params,
            None,
            seed,
            inp.output_times,
            ex,
            obs_for_tile=obs_for_tile,
            eval_for_tile=eval_for_tile,
        )
    grid_blends = coord.blend_grid(
        products,
        grid,
        inp.output_times,
        method=inp.method_name,
        params_key=params.params_key(),
    )
    eval_mean, eval_var = _blend_eval_points(
        products, eval_locs, grid, inp, params.params_key()
    )
    scores = _evaluate_blended(
        inp, grid_blends[0], grid, eval_locs, withheld_vals, eval_mean, eval_var
    )
    return grid_blends, scores


def _in_box(pts: np.ndarray, win: Window) -> np.ndarray:
    """Return a boolean mask of points inside ``win``'s lon/lat box."""
    return np.asarray(
        (pts[:, 0] >= win.lon_range[0])
        & (pts[:, 0] <= win.lon_range[1])
        & (pts[:, 1] >= win.lat_range[0])
        & (pts[:, 1] <= win.lat_range[1])
    )


def _obs_in_window(obs: ObsWindow, win: Window) -> ObsWindow:
    """Return the sub-window of ``obs`` inside ``win``'s lon/lat box (time unrestricted)."""
    idx = np.where(_in_box(obs.coords(), win))[0]
    return _subset_obs(obs, idx)


def _blend_eval_points(
    products: list[tuple[Any, Product]],
    eval_locs: np.ndarray | None,
    grid: GridSpec,
    inp: PipelineInputs,
    params_key: str,
) -> tuple[np.ndarray | None, np.ndarray | None]:
    """Crossfade per-tile withheld eval-point predictives over the full eval ``PointSet``.

    Returns ``(None, None)`` when there are no eval points (OSSE) or no tile produced
    shared-basis eval rows. Non-covering tiles contribute zero weight, so each point mixes
    only the tiles whose halo reaches it.
    """
    if eval_locs is None:
        return None, None
    parts: list[BlendInput] = []
    for tile, prod in products:
        ep = prod.per_time[0].eval_points
        if ep is None or ep.factor is None or ep.locations.shape[0] == 0:
            continue
        residual = (
            ep.residual if ep.residual is not None else np.zeros(ep.locations.shape[0])
        )
        pp = PersistedPoints(
            PointSet(ep.locations, grid.crs),
            mean=ep.mean,
            factor=ep.factor,
            residual=residual,
            provenance=prod.per_time[0].base.provenance,
            time_days=inp.output_times[0],
        )
        parts.append(BlendInput(pp, tile))
    if not parts:
        return None, None
    eb = BlendOperator().blend(
        parts,
        support=PointSet(eval_locs, grid.crs),
        method=inp.method_name,
        params_key=params_key,
    )
    return eb.mean.ravel(), eb.marginal_variance().ravel()


def _evaluate_blended(
    inp: PipelineInputs,
    gb: BlendedDistribution,
    grid: GridSpec,
    eval_locs: np.ndarray | None,
    withheld_vals: np.ndarray | None,
    eval_mean: np.ndarray | None,
    eval_var: np.ndarray | None,
) -> dict[str, Any]:
    """Assemble the eval context from the blended product and run every applicable evaluator.

    OSSE scores the blended grid against the gridded truth; OSE scores the blended
    eval-point predictives against the withheld CryoSat-2 along-track. Same evaluator spine
    as Phase-1 ``_evaluate``; only the source of the eval mean/var differs.
    """
    items: dict[ContextKey, object] = {
        ContextKey.ORBIT_GEOMETRY: {"track_spacing_nodes": 4}
    }
    result: dict[str, np.ndarray] = {"field": gb.mean, "grid_mean": gb.mean}
    if inp.mode == "OSSE":
        truth = np.asarray(cast(Any, inp.source).truth(inp.output_times[0], grid))
        items[ContextKey.TRUTH] = {"field": truth}
        items[ContextKey.WITHHELD_OBS] = {"values": truth.ravel()}
        result["eval_mean"] = gb.mean.ravel()
        result["eval_var"] = gb.marginal_variance().ravel()
    elif eval_locs is not None and eval_mean is not None and withheld_vals is not None:
        items[ContextKey.WITHHELD_OBS] = {"values": withheld_vals}
        result["eval_mean"] = eval_mean
        result["eval_var"] = cast(np.ndarray, eval_var)
    ctx = EvalContext(items)
    reg = Registry([Accuracy(), Calibration(), GroundTrack(track_wavenumber=4)])
    scores: dict[str, Any] = dict(reg.run(result, ctx))
    scores["context_keys"] = {k.name for k in ctx.keys()}
    scores["fidelity"] = gb.fidelity.name
    scores["blend_transforms"] = [t.kind.name for t in gb.provenance.transformations]
    return scores


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
