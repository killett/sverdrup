"""Method 2: regular-grid Matérn GMRF (sparse precision); EXACT selective-inversion (spec §5.1)."""

from __future__ import annotations

import numpy as np
from scipy import sparse  # type: ignore[import-untyped]

from sverdrup.core.grid import GridSpec
from sverdrup.core.observations import ObsWindow
from sverdrup.core.parameters import ParameterProvider, ParameterSpace
from sverdrup.core.provenance import (
    KnownBias,
    TransformKind,
    UncertaintyProvenance,
    UncertaintyTransform,
)
from sverdrup.core.types import CovFidelity, Points, Seed, UncertaintyCapability
from sverdrup.distributions.gaussian import GaussianPredictiveDistribution
from sverdrup.methods.gmrf_grid import (
    bilinear_weights,
    kappa_from_range,
    matern_precision,
)
from sverdrup.methods.gmrf_linalg import GMRFFactor, assert_adjacency_in_pattern


class GMRFCovarianceOperator:
    """EXACT posterior covariance of a regular-grid GMRF, backed by one sparse factor."""

    fidelity = CovFidelity.EXACT
    representation = "sparse-precision"

    def __init__(
        self, grid: GridSpec, q_post: sparse.csc_matrix, time_days: float
    ) -> None:
        """Cache the posterior precision and its factor; verify the adjacency precondition."""
        assert_adjacency_in_pattern(q_post, grid.shape)
        self.grid = grid
        self.q_post = q_post
        self.time_days = time_days
        self._factor = GMRFFactor(q_post)
        self._sinv = self._factor.selective_inverse()  # sparse, on L+L^T pattern
        self._diag = np.asarray(self._sinv.diagonal())

    def _is_grid(self, a: Points) -> bool:
        """True if ``a`` matches the grid nodes (the identity-projection fast path)."""
        return a.shape[0] == self.grid.shape[0] * self.grid.shape[1] and np.allclose(
            a[:, :2], self.grid.points(self.time_days)[:, :2]
        )

    def marginal_var(self, a: Points) -> np.ndarray:
        """Return exact marginal variance: ``diag(Q^-1)`` on-grid, ``diag(W Σ W^T)`` off-grid."""
        if self._is_grid(a):
            return self._diag
        w = bilinear_weights(self.grid, a)
        return np.asarray((w @ self._sinv @ w.T).diagonal())

    def cov(self, a: Points, b: Points) -> np.ndarray:
        """Return ``W_a Σ W_b^T`` using selective-inverse entries (adjacent pairs in pattern)."""
        wa = bilinear_weights(self.grid, a)
        wb = bilinear_weights(self.grid, b)
        return np.asarray((wa @ self._sinv @ wb.T).toarray())

    def posterior_sample(self, s: Points, seed: Seed, m: int) -> np.ndarray:
        """Return ``m`` zero-mean draws ``W (L^-T w)`` at ``s`` (node-space sample, projected)."""
        rng = np.random.default_rng(seed)
        n = self.q_post.shape[0]
        node_draws = np.stack(
            [self._factor.sample(rng.standard_normal(n)) for _ in range(m)]
        )  # (m, n)
        if self._is_grid(s):
            return node_draws
        w = bilinear_weights(self.grid, s)  # (k, n)
        return np.asarray((w @ node_draws.T).T)  # (m, k)

    def node_sample(self, w_white: np.ndarray) -> np.ndarray:
        """Return one node-space draw ``L^-T w`` from external white noise (coherence driver)."""
        return self._factor.sample(w_white)


class MaternGMRF:
    """Regular-grid Matérn GMRF method: spatial precision + temporally-tapered likelihood."""

    native_capability = UncertaintyCapability.SAMPLES  # also exposes COVARIANCE

    def solve(
        self,
        obs: ObsWindow,
        grid: GridSpec,
        params: ParameterProvider,
        time_days: float,
    ) -> GaussianPredictiveDistribution:
        """Solve the GMRF posterior over ``grid`` at ``time_days`` (temporal taper into R)."""
        rng_km = float(params.resolve("range", grid))
        tau = float(params.resolve("variance", grid))
        taper = float(params.resolve("temporal_taper_scale", grid))
        kappa = kappa_from_range(rng_km)
        q_prior = matern_precision(grid, kappa, tau)

        a_op = bilinear_weights(grid, obs.coords())  # (n_obs, n_nodes): grid -> obs
        r_diag = np.diag(obs.error_model.as_matrix(len(obs))).astype(float)
        dt = np.abs(obs.coords()[:, 2] - time_days)
        r_inflated = r_diag * np.exp(dt / max(taper, 1e-9))  # temporal taper into R
        r_inv = sparse.diags(1.0 / r_inflated)

        q_post = (q_prior + a_op.T @ r_inv @ a_op).tocsc()
        op = GMRFCovarianceOperator(grid, q_post, time_days)
        rhs = a_op.T @ (r_inv @ obs.values())
        mean = op._factor.solve(np.asarray(rhs)).reshape(grid.shape)

        prov = UncertaintyProvenance(
            native_capability=self.native_capability,
            transformations=[
                UncertaintyTransform(
                    kind=TransformKind.DIAGONAL_INFLATION,
                    known_bias=KnownBias.UNDER_DISPERSED_IN_VOIDS,
                    params={
                        "temporal_taper": "diagonal-R; under-uses temporal structure "
                        "(conservative). OI carries a full space-time kernel; GMRF "
                        "carries spatial cov + temporally-tapered likelihood.",
                        "temporal_taper_scale": taper,
                    },
                )
            ],
        )
        return GaussianPredictiveDistribution(grid, mean, op, prov, time_days)

    def parameter_space(self) -> ParameterSpace:
        """Return the tunable space: range, variance, temporal taper (ν fixed to α=2)."""
        return ParameterSpace(
            {
                "range": (10.0, 800.0),
                "variance": (1e-3, 1.0),
                "temporal_taper_scale": (1.0, 30.0),
            }
        )
