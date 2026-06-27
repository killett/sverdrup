"""Method 2: regular-grid Matérn GMRF (sparse precision); EXACT selective-inversion (spec §5.1)."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

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
    kappa_from_range,
    matern_precision,
)
from sverdrup.methods.gmrf_linalg import GMRFFactor

if TYPE_CHECKING:
    from sverdrup.core.projection import Projection


class GMRFCovarianceOperator:
    """EXACT posterior covariance of a GMRF, backed by one sparse factor; projection-driven."""

    fidelity = CovFidelity.EXACT
    representation = "sparse-precision"

    def __init__(
        self,
        projection_or_grid: object,
        q_post: sparse.csc_matrix,
        time_days: float,
        q_prior: sparse.csc_matrix | None = None,
    ) -> None:
        """Cache the posterior precision + factor; hold a Projection; verify adjacency.

        Args:
            projection_or_grid: A ``Projection`` the read-off routes through, OR a
                legacy ``GridSpec`` (wrapped in ``GridIdentityProjection``).
            q_post: Posterior precision (CSC).
            time_days: Output time.
            q_prior: Prior precision (CSC), persisted for the Stage-B strip-prior draw.
        """
        from sverdrup.methods.gmrf_grid import GridIdentityProjection

        proj = (
            GridIdentityProjection(projection_or_grid)
            if isinstance(projection_or_grid, GridSpec)
            else projection_or_grid
        )
        self.projection = cast("Projection", proj)
        self.projection.assert_adjacency(q_post)
        self.grid = getattr(self.projection, "grid", self.projection.node_space)
        self.q_post = q_post
        self.q_prior = q_prior
        self.time_days = time_days
        self._factor = GMRFFactor(q_post)
        self._sinv = self._factor.selective_inverse()  # sparse, on L+L^T pattern
        self._diag = np.asarray(self._sinv.diagonal())

    def _is_native_nodes(self, a: Points) -> bool:
        """True if ``a`` matches the precision node points (the identity fast path)."""
        nodes = self.projection.node_points(self.time_days)
        return a.shape[0] == nodes.shape[0] and np.allclose(a[:, :2], nodes[:, :2])

    def marginal_var(self, a: Points) -> np.ndarray:
        """Return exact marginal variance: cached ``diag`` on native nodes, else ``diag(W Σ Wᵀ)``."""
        if self._is_native_nodes(a):
            return self._diag
        w = self.projection.weights(a)
        return np.asarray((w @ self._sinv @ w.T).diagonal())

    def cov(self, a: Points, b: Points) -> np.ndarray:
        """Return ``W_a Σ W_b^T`` using selective-inverse entries (adjacent pairs in pattern)."""
        wa = self.projection.weights(a)
        wb = self.projection.weights(b)
        return np.asarray((wa @ self._sinv @ wb.T).toarray())

    def posterior_sample(self, s: Points, seed: Seed, m: int) -> np.ndarray:
        """Return ``m`` zero-mean draws ``W (L^-T w)`` at ``s`` (node-space sample, projected)."""
        rng = np.random.default_rng(seed)
        n = self.q_post.shape[0]
        node_draws = np.stack(
            [self._factor.sample(rng.standard_normal(n)) for _ in range(m)]
        )  # (m, n)
        if self._is_native_nodes(s):
            return node_draws
        w = self.projection.weights(s)  # (k, n)
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
        rng_resolved = params.resolve("range", grid)
        tau = float(params.resolve("variance", grid))
        taper = float(params.resolve("temporal_taper_scale", grid))
        if np.isscalar(rng_resolved) or np.asarray(rng_resolved).ndim == 0:
            kappa: float | np.ndarray = kappa_from_range(float(rng_resolved))
            range_repr: float | str = float(rng_resolved)
        else:
            kappa = kappa_from_range(np.asarray(rng_resolved))  # elementwise κ field
            range_repr = "field(lat-varying)"
        q_prior = matern_precision(grid, kappa, tau)

        from sverdrup.methods.gmrf_grid import GridIdentityProjection

        projection = GridIdentityProjection(grid)
        a_op = projection.weights(obs.coords())  # (n_obs, n_nodes): node -> obs
        r_diag = np.diag(obs.error_model.as_matrix(len(obs))).astype(float)
        dt = np.abs(obs.coords()[:, 2] - time_days)
        r_inflated = r_diag * np.exp(dt / max(taper, 1e-9))  # temporal taper into R
        r_inv = sparse.diags(1.0 / r_inflated)

        q_post = (q_prior + a_op.T @ r_inv @ a_op).tocsc()
        op = GMRFCovarianceOperator(projection, q_post, time_days, q_prior=q_prior)
        rhs = a_op.T @ (r_inv @ obs.values())
        mean = op._factor.solve(np.asarray(rhs)).reshape(projection.field_shape())

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
                        "range": range_repr,
                        "kappa_range_mapping": "range = sqrt(8*nu)/kappa, nu=1",
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
