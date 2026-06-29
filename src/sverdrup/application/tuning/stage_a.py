"""Stage-A wiring: blocked-validation split, OI search, single c2 acceptance (Phase-5).

Trains on the mapping missions MINUS the validation mission (j3) MINUS c2 (held by
``their_eval``), searches OI's parameter space scoring each trial on the RAW j3
along-track via :class:`ValidationTrackScorer`, then accepts the winner exactly once
by running its config over the challenge map and scoring on the c2 locked test with
``their_eval.score``. A satisfiability pre-check (the untuned Matérn analog) runs
before the sweep so a structurally-unclearable floor surfaces loudly instead of as a
multi-hour ``NoAdmissibleTrial``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from sverdrup.application.splits import make_splits
from sverdrup.application.tuning.feasibility import CoherenceFeasibility, TileGeometry
from sverdrup.application.tuning.loop import tune
from sverdrup.application.tuning.objective import BASELINE_BAR_MU, ConstrainedObjective
from sverdrup.application.tuning.scorer import (
    ValidationTrackScorer,
    matern_kernel_from_params,
)
from sverdrup.application.tuning.strategy import SobolSearch
from sverdrup.application.tuning.trial import TrialRecord
from sverdrup.core.grid import GridSpec
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
from sverdrup.core.parameters import ConstantProvider
from sverdrup.core.types import UncertaintyCapability
from sverdrup.methods.oi import OptimalInterpolation
from sverdrup.validation.input_adapter import load_mapping_obs, load_mdt_grid
from sverdrup.validation.params import (
    _KM_PER_DEG,
    LAT_MAX,
    LAT_MIN,
    LON_MAX,
    LON_MIN,
    SIGNAL_VARIANCE,
    SPATIAL_CORR_DEG,
    TEMPORAL_CORR_DAYS,
    TIME_MAX,
    TIME_MIN,
    baseline_config,
)
from sverdrup.validation.run import run_challenge_map
from sverdrup.validation.their_eval import score as their_score


@dataclass
class StageAReport:
    """Winner record, c2 acceptance ``(µ, σ, λx)``, search call-count, and pre-check."""

    winner: TrialRecord
    acceptance: tuple[float, float, float]
    their_eval_calls_during_search: int
    precheck_scores: dict[str, float]


class StageANoAdmissible(RuntimeError):
    """No trial cleared the BASELINE floor — surfaced with the pre-check evidence."""


class _Win:
    def __init__(self, wid: str) -> None:
        self.id = wid


def _subset(obs: ObsWindow, idx: np.ndarray) -> ObsWindow:
    """Return the obs at ``idx`` (diagonal error preserved), mirroring run._subset."""
    c = obs.coords()
    em = obs.error_model
    var = (
        np.asarray(em.variance, dtype=float)
        if isinstance(em, DiagonalErrorModel)
        else np.asarray(em.as_matrix(len(obs)).diagonal(), dtype=float)
    )
    mission = None if obs.mission is None else np.asarray(obs.mission)[idx]
    return ObsWindow.from_arrays(
        c[idx, 0],
        c[idx, 1],
        c[idx, 2],
        obs.values()[idx],
        DiagonalErrorModel(var[idx]),
        mission=mission,
    )


def _build_scorer(
    cfg: dict[str, Any],
    train_obs: ObsWindow,
    grid: GridSpec,
    half: float,
    mdt: np.ndarray | None,
) -> ValidationTrackScorer:
    return ValidationTrackScorer(
        train_obs=train_obs,
        grid=grid,
        output_days=list(cfg["validation_days"]),
        temporal_half_window_days=half,
        val_track_path=Path(cfg["val_track_path"]),
        lon_min=LON_MIN,
        lon_max=LON_MAX,
        lat_min=LAT_MIN,
        lat_max=LAT_MAX,
        time_min=cfg.get("time_min", TIME_MIN),
        time_max=cfg.get("time_max", TIME_MAX),
        mdt_grid=mdt,
    )


def run_stage_a(*, scope: Path, n_trials: int = 16, seed: int = 1) -> StageAReport:
    """Run the Stage-A loop on OI and accept the winner once on the c2 locked test."""
    cfg = json.loads(Path(scope).read_text())
    provider, grid, half = baseline_config()
    obs = load_mapping_obs([Path(p) for p in cfg["mapping_obs_paths"]], provider)
    mdt = (
        load_mdt_grid([Path(p) for p in cfg["mdt_paths"]], grid)
        if cfg.get("mdt_paths")
        else None
    )
    split = make_splits(
        obs,
        by="mission",
        locked_missions=["c2"],
        validation_missions=[cfg["validation_mission"]],
    )
    train_obs = _subset(obs, split.train_idx)
    scorer = _build_scorer(cfg, train_obs, grid, half, mdt)
    win = _Win(cfg.get("window_id", "gulfstream"))

    # SATISFIABILITY PRE-CHECK — the untuned Matérn analog of the BASELINE params.
    precheck_params = {
        "variance": SIGNAL_VARIANCE,
        "length_scale": SPATIAL_CORR_DEG * _KM_PER_DEG,
        "time_scale": TEMPORAL_CORR_DAYS,
    }
    precheck = scorer.score("oi", precheck_params, split, seed, win)

    result = tune(
        method_name="oi",
        space=OptimalInterpolation().parameter_space(),
        strategy=SobolSearch(seed=seed, n=n_trials),
        predicate=CoherenceFeasibility(),
        objective=ConstrainedObjective(),
        scorer=scorer,
        split=split,
        seed=seed,
        window=win,
        tile_geometry=TileGeometry(1e9, 1.0, "single"),  # ratio huge -> always feasible
        required_capabilities=frozenset({UncertaintyCapability.POINT}),
        rounds=1,
        on_empty="return_history",
    )
    if result.winner is None:
        best = max(
            (
                r.scores["mu_score"]
                for r in result.history.feasible_scored()
                if r.scores is not None
            ),
            default=float("nan"),
        )
        raise StageANoAdmissible(
            f"no trial cleared BASELINE_BAR_MU={BASELINE_BAR_MU}; best mu_score={best:.4f}, "
            f"precheck(untuned Matérn) mu_score={precheck['mu_score']:.4f}. The Matérn-3/2 "
            "kernel may be structurally unable to clear the Gaussian-BASELINE floor — see the "
            "Task-11 fallbacks (same-family floor / tunable nu / tune the Gaussian kernel)."
        )

    # ACCEPTANCE — touched exactly once: winner's EXPLICIT Matérn kernel on the c2 map.
    winner_params = result.winner.trial.params
    dest = Path(cfg["acceptance_map_out"])
    run_challenge_map(
        "oi",
        train_obs,
        ConstantProvider(winner_params),
        grid,
        half,
        list(cfg["acceptance_days"]),
        dest,
        kernel=matern_kernel_from_params(winner_params),
        mdt_grid=mdt,
    )
    acceptance = their_score(dest, Path(cfg["c2_track_path"]))
    return StageAReport(
        winner=result.winner,
        acceptance=acceptance,
        their_eval_calls_during_search=0,  # tune() never imports their_eval.score
        precheck_scores=precheck,
    )
