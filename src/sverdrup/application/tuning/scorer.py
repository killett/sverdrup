"""Real TrialScorer: faithful daily-maps -> interp-onto-validation-track scoring (Phase-5).

This is the integration seam between the (method-agnostic) tuner core and the
validation challenge machinery. Per trial it produces daily mean + variance maps
from the trial's params on the TRAINING obs, interpolates BOTH onto the raw
validation (non-c2) along-track at the track's own datetime64 times (the vendored
``interp_on_alongtrack``), and returns ``{mu_score, coverage_1sigma, lambda_x}`` via
the shared helpers. The ONLY difference from c2 acceptance is the track (j3 vs c2) —
invariant 10 at the scorer level. ``their_eval.score`` is NEVER called here (only the
import-prep ``_prepare_imports`` is reused for the vendored interp env), so the search
never touches the locked test.

For OI an explicit ``Matern32SpaceTime`` is built from the trial params and passed to
the solve, so the same params drive both search and acceptance (never ``kernel=None``,
which means opposite things across ``OI.solve`` and ``run_challenge_map``).
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from sverdrup.core.grid import GridSpec
from sverdrup.core.observations import ObsWindow
from sverdrup.core.parameters import ConstantProvider
from sverdrup.eval.calibration import coverage
from sverdrup.eval.skill_score import leaderboard_nrmse
from sverdrup.eval.spectral import effective_resolution_lambda_x
from sverdrup.validation.run import run_mean_var_maps


@dataclass
class ValidationTrackScorer:
    """Faithful per-trial scorer: daily maps -> interp onto the raw validation track."""

    train_obs: ObsWindow
    grid: GridSpec
    output_days: list[float]
    temporal_half_window_days: float
    val_track_path: Path
    lon_min: float
    lon_max: float
    lat_min: float
    lat_max: float
    time_min: str
    time_max: str
    mdt_grid: np.ndarray | None = None

    def score(
        self,
        method_name: str,
        params: dict[str, float],
        split: object,
        seed: int,
        window: object,
    ) -> dict[str, float]:
        """Solve daily maps, interp onto the validation track, return the metric vector."""
        import sverdrup.validation.their_eval as te  # import-prep only; .score untouched

        with tempfile.TemporaryDirectory() as td:
            mean_p = Path(td) / "mean.nc"
            var_p = Path(td) / "var.nc"
            run_mean_var_maps(
                method_name,
                self.train_obs,
                ConstantProvider(params),
                self.grid,
                self.temporal_half_window_days,
                self.output_days,
                mean_p,
                var_p,
                mdt_grid=self.mdt_grid,
                oi_kernel_from_params=True,  # OI tunes its Matérn from params (not Gaussian)
            )
            te._prepare_imports()
            from src.mod_inout import read_l3_dataset
            from src.mod_interp import interp_on_alongtrack

            box = dict(
                lon_min=self.lon_min,
                lon_max=self.lon_max,
                lat_min=self.lat_min,
                lat_max=self.lat_max,
                time_min=self.time_min,
                time_max=self.time_max,
            )
            ds_at = read_l3_dataset(str(self.val_track_path), **box)
            time_a, lat_a, lon_a, ssh_a, mean_interp = interp_on_alongtrack(
                str(mean_p), ds_at, is_circle=False, **box
            )
            # The variance map shares the mean map's grid/time axes, so its valid
            # along-track footprint (hence the returned index subset) is identical.
            _, _, _, _, var_interp = interp_on_alongtrack(
                str(var_p), ds_at, is_circle=False, **box
            )
        ssh_a = np.asarray(ssh_a, dtype=float)
        mean_interp = np.asarray(mean_interp, dtype=float)
        var_interp = np.asarray(var_interp, dtype=float)
        return {
            "mu_score": leaderboard_nrmse(ssh_a, mean_interp),
            "coverage_1sigma": float(coverage(mean_interp, var_interp, ssh_a, 1.0)),
            "lambda_x": effective_resolution_lambda_x(
                time_a, lat_a, lon_a, ssh_a, mean_interp
            ),
        }
