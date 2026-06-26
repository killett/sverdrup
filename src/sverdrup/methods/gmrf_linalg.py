"""CHOLMOD simplicial factor + hand-rolled Takahashi selective inverse (spec §5.1).

One factor L serves sampling (L^-T w), the posterior mean (full solve), and cov blocks.
CHOLMOD has no selective inverse, so diag(Q^-1) and near-neighbour Q^-1 entries are
computed by the Takahashi recursion over the L+L^T sparsity pattern.

Backend is sksparse 0.5.x (scipy-style API): ``cho_factor(Q, order="amd", lower=True)``
returns a ``CholeskyFactor`` with ``L Lᵀ = Q[P][:,P]`` (``P = cf.perm``); when CHOLMOD picks
LDLᵀ instead we fold ``D`` into ``L`` once — ``Lc = L·D^{1/2}`` — so a single lower factor
``Lc`` with ``Lc Lcᵀ = Q[P][:,P]`` drives sampling, Takahashi, and the permutation back-map.
The factor is of the *permuted* matrix, so an original-order entry ``(P[k], P[l])`` carries
the permuted value ``(k, l)`` — hence the back-map indexes by ``P`` directly.
"""

from __future__ import annotations

import numpy as np
from scipy import sparse  # type: ignore[import-untyped]
from scipy.sparse.linalg import spsolve_triangular  # type: ignore[import-untyped]
from sksparse.cholmod import cho_factor  # type: ignore[import-untyped]


class GMRFFactor:
    """A cached CHOLMOD simplicial Cholesky of an SPD sparse precision ``Q``."""

    def __init__(self, q: sparse.csc_matrix) -> None:
        """Factor ``Lc Lcᵀ = Q[P][:,P]`` (AMD order, deterministic); record ``P``.

        Args:
            q: Symmetric positive-definite sparse precision (CSC).
        """
        self._q = q.tocsc()
        # order fixed -> deterministic permutation across factorizations.
        self._cf = cho_factor(self._q, order="amd", lower=True)
        self.permutation = np.asarray(self._cf.perm)
        lc = sparse.csc_matrix(self._cf.L)  # P Q Pᵀ = L Lᵀ (is_ll) or L D Lᵀ
        if not self._cf.is_ll:
            d = np.asarray(sparse.csc_matrix(self._cf.D).diagonal())
            lc = (lc @ sparse.diags(np.sqrt(d))).tocsc()
        self._lc = lc
        self._cov_cols: dict[int, np.ndarray] = {}

    def solve(self, b: np.ndarray) -> np.ndarray:
        """Return ``Q^-1 b`` via the cached factor (permutation handled internally)."""
        return np.asarray(self._cf.solve(np.asarray(b, float)))

    def posterior_cov_columns(self, shared_idx: np.ndarray) -> np.ndarray:
        """Return the FULL columns ``(Q^-1)[:, shared_idx]`` via per-node back-solves.

        Each column ``z_j = Q^-1 e_j`` is a dense back-solve on the cached factor — these
        are the long-range cross-covariances OUTSIDE the Takahashi/selective-inverse pattern
        that the kriging correction conditions on (spec §5.3.1, Task-9a). Columns are cached
        per node index so the per-member kriging apply reuses them across all ``M`` members.

        Args:
            shared_idx: 1-D array of node indices (original order) whose ``Q^-1`` columns
                are wanted.

        Returns:
            A dense ``(n, |shared_idx|)`` array; column ``k`` is ``(Q^-1)[:, shared_idx[k]]``.
        """
        idx = np.asarray(shared_idx).ravel()
        n = self._lc.shape[0]
        out = np.empty((n, idx.size), float)
        for k, j in enumerate(idx):
            jj = int(j)
            col = self._cov_cols.get(jj)
            if col is None:
                e = np.zeros(n)
                e[jj] = 1.0
                col = self.solve(e)
                self._cov_cols[jj] = col
            out[:, k] = col
        return out

    def sample(self, w: np.ndarray) -> np.ndarray:
        """Return one zero-mean draw ``L^-T w`` (so ``Cov = Q^-1``), in original node order.

        Solves ``Lcᵀ y = w`` in permuted order, then scatters back: ``x[P] = y``.
        """
        y = spsolve_triangular(self._lc.T.tocsr(), np.asarray(w, float), lower=False)
        x = np.empty_like(y)
        x[self.permutation] = y
        return np.asarray(x)

    def selective_inverse(self) -> sparse.csr_matrix:
        """Return the Takahashi selective inverse of ``Q`` on the ``L+Lᵀ`` pattern (orig order)."""
        sinv_p = _takahashi(self._lc).tocoo()  # permuted order
        # original index of permuted node k is P[k]: Sigma[P[k],P[l]] = Sinv_p[k,l]
        perm = self.permutation
        rows = perm[sinv_p.row]
        cols = perm[sinv_p.col]
        n = self._lc.shape[0]
        return sparse.csr_matrix((sinv_p.data, (rows, cols)), shape=(n, n))

    def selective_inverse_diag(self) -> np.ndarray:
        """Return ``diag(Q^-1)`` (exact marginal variance) in original node order."""
        return np.asarray(self.selective_inverse().diagonal())


def _takahashi(l_chol: sparse.csc_matrix) -> sparse.csc_matrix:
    """Takahashi recursion: selective inverse Σ on the lower pattern of ``L`` (LLᵀ factor).

    Σ_jj = 1/L_jj^2 - (1/L_jj) Σ_{k>j, L_kj!=0} L_kj Σ_kj
    Σ_ij = -(1/L_jj) Σ_{k>j, L_kj!=0} L_kj Σ_ik   (i in pattern, i>j)
    Processed in reverse column order; only entries on the L pattern are computed.
    """
    n = l_chol.shape[0]
    l_csc = l_chol.tocsc()
    diag_l = l_csc.diagonal()
    sigma = sparse.lil_matrix((n, n))
    indptr, indices, data = l_csc.indptr, l_csc.indices, l_csc.data
    col_rows = [indices[indptr[j] : indptr[j + 1]] for j in range(n)]
    col_vals = [data[indptr[j] : indptr[j + 1]] for j in range(n)]
    for j in range(n - 1, -1, -1):
        rows = col_rows[j]
        vals = col_vals[j]
        below = [(r, v) for r, v in zip(rows, vals, strict=False) if r > j]
        inv_ljj = 1.0 / diag_l[j]
        # off-diagonals Σ_ij for i in the column pattern below j
        for i, _ in below:
            acc = 0.0
            for k, lkj in below:
                acc += lkj * (sigma[max(i, k), min(i, k)] if k != i else sigma[k, k])
            sij = -inv_ljj * acc
            sigma[i, j] = sij
            sigma[j, i] = sij
        acc = 0.0
        for k, lkj in below:
            acc += lkj * sigma[k, j]
        sigma[j, j] = inv_ljj * inv_ljj - inv_ljj * acc
    return sigma.tocsc()


def assert_adjacency_in_pattern(q: sparse.csc_matrix, shape: tuple[int, int]) -> None:
    """Raise if any 5-point-adjacent node pair is outside ``Q``'s (and so Σ's) pattern.

    The bilinear ``W`` couples a point to its 4 surrounding nodes and ``firstdifference``
    reads ``cov`` between adjacent nodes; both require those Σ entries to be in the
    selective-inverse pattern. For the α=2 ``(κ²−Δ)²`` stencil the Q pattern already
    contains all 5-point neighbours (and their squares), so this holds.
    """
    ny, nx = shape
    qcoo = q.tocoo()
    present = set(zip(qcoo.row.tolist(), qcoo.col.tolist(), strict=False))
    for j in range(ny):
        for i in range(nx):
            c = j * nx + i
            for dj, di in ((0, 1), (1, 0)):
                jj, ii = j + dj, i + di
                if jj < ny and ii < nx:
                    nb = jj * nx + ii
                    if (c, nb) not in present:
                        raise AssertionError(
                            f"adjacent pair ({c},{nb}) absent from Q pattern — "
                            "wider stencil would break eval var / cancellation"
                        )
