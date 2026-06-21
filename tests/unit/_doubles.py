import numpy as np

from regatta.core.types import CovFidelity


class ToyExpOperator:
    """Zero-mean stationary exponential covariance over (lon,lat,time) points."""

    fidelity = CovFidelity.EXACT

    def __init__(self, sigma2=1.0, length=2.0):
        self.sigma2, self.length = sigma2, length

    def _k(self, a, b):
        d = np.linalg.norm(a[:, None, :] - b[None, :, :], axis=2)
        return self.sigma2 * np.exp(-d / self.length)

    def cov(self, a, b):
        return self._k(a, b)

    def marginal_var(self, a):
        return np.full(a.shape[0], self.sigma2)

    def posterior_sample(self, s, seed, m):
        cov = self._k(s, s) + 1e-10 * np.eye(s.shape[0])
        chol = np.linalg.cholesky(cov)
        z = np.random.default_rng(seed).standard_normal((m, s.shape[0]))
        return z @ chol.T
