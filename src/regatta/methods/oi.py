"""Method 1: dense space-time GP / optimal interpolation (Decision A; spec 5.2)."""

from __future__ import annotations

import numpy as np

from regatta.core.grid import GridSpec
from regatta.core.observations import ObsWindow
from regatta.core.parameters import ParameterProvider, ParameterSpace
from regatta.core.provenance import UncertaintyProvenance
from regatta.core.types import CovFidelity, Points, Seed, UncertaintyCapability
from regatta.distributions.gaussian import GaussianPredictiveDistribution
from regatta.methods.kernel import Kernel, Matern32SpaceTime
from regatta.methods.solver import DenseCholeskySolver, LinearSolver


class GPCovarianceOperator:
    """Exact GP posterior covariance via a cached Cholesky of ``K_dd + R``."""

    fidelity = CovFidelity.EXACT

    def __init__(
        self,
        kernel: Kernel,
        obs_pts: Points,
        y: np.ndarray,
        noise_diag: np.ndarray,
        solver: LinearSolver | None = None,
    ) -> None:
        """Factor ``K_dd + R`` and precompute ``alpha = (K_dd + R)^-1 y``.

        Args:
            kernel: The space-time covariance kernel.
            obs_pts: The ``(n, 3)`` observation points.
            y: The ``(n,)`` observation values.
            noise_diag: The ``(n,)`` per-obs error variances (R diagonal).
            solver: The linear-solver seam (defaults to dense Cholesky).
        """
        self.kernel = kernel
        self.obs_pts = obs_pts
        self.solver = solver or DenseCholeskySolver()
        kdd = kernel.evaluate(obs_pts, obs_pts)
        kdd[np.diag_indices_from(kdd)] += noise_diag
        self.solver.factor(kdd)
        self._alpha = self.solver.solve(y)  # (K_dd+R)^-1 y

    def _v(self, pts: Points) -> np.ndarray:
        """Return ``V_X = L^-1 K_dX`` for query points ``pts``."""
        return self.solver.solve_triangular_lower(
            self.kernel.evaluate(self.obs_pts, pts)
        )

    def posterior_mean(self, pts: Points) -> np.ndarray:
        """Return the posterior mean ``K_Xd alpha`` at ``pts``."""
        return np.asarray(self.kernel.evaluate(pts, self.obs_pts) @ self._alpha)

    def cov(self, a: Points, b: Points) -> np.ndarray:
        """Return the posterior covariance ``K_AB - V_A^T V_B`` (exact)."""
        return np.asarray(self.kernel.evaluate(a, b) - self._v(a).T @ self._v(b))

    def marginal_var(self, a: Points) -> np.ndarray:
        """Return the posterior marginal variance at ``a`` (exact, void-aware)."""
        if _stationary(self.kernel):
            kaa = np.full(a.shape[0], self.kernel.evaluate(a[:1], a[:1])[0, 0])
        else:
            kaa = np.diag(self.kernel.evaluate(a, a))
        va = self._v(a)
        return np.asarray(kaa - np.sum(va**2, axis=0))

    def posterior_sample(self, s: Points, seed: Seed, m: int) -> np.ndarray:
        """Return ``m`` zero-mean posterior draws at ``s``, shape ``(m, len(s))``."""
        cov = self.cov(s, s)
        cov[np.diag_indices_from(cov)] += 1e-9
        chol = np.linalg.cholesky(cov)
        z = np.random.default_rng(seed).standard_normal((m, s.shape[0]))
        return np.asarray(z @ chol.T)


def _stationary(kernel: Kernel) -> bool:
    """Return True if the kernel is stationary (constant prior variance)."""
    return isinstance(kernel, Matern32SpaceTime)


class OptimalInterpolation:
    """GP/OI method emitting a native Gaussian predictive distribution."""

    native_capability = UncertaintyCapability.SAMPLES

    def solve(
        self,
        obs: ObsWindow,
        grid: GridSpec,
        params: ParameterProvider,
        time_days: float,
    ) -> GaussianPredictiveDistribution:
        """Solve the GP posterior over ``grid`` at ``time_days``.

        Args:
            obs: The observation window.
            grid: The output grid.
            params: The parameter provider (variance, length_scale, time_scale).
            time_days: The output time in days.

        Returns:
            A native Gaussian predictive distribution (EXACT operator).
        """
        kernel = Matern32SpaceTime(
            variance=float(params.resolve("variance", grid)),
            length_scale=float(params.resolve("length_scale", grid)),
            time_scale=float(params.resolve("time_scale", grid)),
        )
        obs_pts = obs.coords()
        noise = np.diag(obs.error_model.as_matrix(len(obs)))
        op = GPCovarianceOperator(kernel, obs_pts, obs.values(), noise_diag=noise)
        mean = op.posterior_mean(grid.points(time_days)).reshape(grid.shape)
        prov = UncertaintyProvenance(
            native_capability=self.native_capability, transformations=[]
        )
        return GaussianPredictiveDistribution(grid, mean, op, prov, time_days)

    def parameter_space(self) -> ParameterSpace:
        """Return the tunable parameter space for OI."""
        return ParameterSpace(
            {
                "length_scale": (10.0, 800.0),
                "time_scale": (1.0, 30.0),
                "variance": (1e-3, 1.0),
            }
        )
