"""Method 0: trivial POINT baseline (inverse-distance naive interpolation; spec 5.2)."""

from __future__ import annotations

import numpy as np

from regatta.core.grid import GridSpec
from regatta.core.observations import ObsWindow
from regatta.core.parameters import ParameterProvider, ParameterSpace
from regatta.core.seeding import derive_seed
from regatta.core.types import Field, UncertaintyCapability
from regatta.distributions.adapters import perturb_and_ensemble
from regatta.distributions.ensemble import EnsemblePredictiveDistribution


class TrivialInterpolation:
    """Inverse-distance-weighted point estimate; lifted to a distribution via perturbation."""

    native_capability = UncertaintyCapability.POINT

    def point_estimate(self, obs: ObsWindow, grid: GridSpec, time_days: float) -> Field:
        """Return an inverse-distance-weighted field estimate, shape ``(ny, nx)``.

        Args:
            obs: The observation window.
            grid: The output grid.
            time_days: The output time in days.

        Returns:
            The point-estimate field.
        """
        nodes = grid.points(time_days)[:, :2]
        op = obs.coords()[:, :2]
        vals = obs.values()
        d2 = np.sum((nodes[:, None, :] - op[None, :, :]) ** 2, axis=2) + 1e-9
        w = 1.0 / d2
        est = (w @ vals) / w.sum(axis=1)
        return np.asarray(est.reshape(grid.shape))

    def solve(
        self,
        obs: ObsWindow,
        grid: GridSpec,
        params: ParameterProvider,
        time_days: float,
    ) -> EnsemblePredictiveDistribution:
        """Solve by lifting the point estimate via perturb-and-ensemble.

        Args:
            obs: The observation window.
            grid: The output grid.
            params: The parameter provider (used only for the seed key).
            time_days: The output time in days.

        Returns:
            A synthesized ensemble predictive distribution.
        """
        seed = derive_seed("trivial", params.params_key(), f"t{time_days}", 0)
        return perturb_and_ensemble(
            self.point_estimate, obs, grid, m=50, seed=seed, time_days=time_days
        )

    def parameter_space(self) -> ParameterSpace:
        """Return the (empty) tunable parameter space."""
        return ParameterSpace({})
