"""Multi-RHS Jacobi-preconditioned CG on the MIOST reduced normal equations (spec §2.4)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import sparse  # type: ignore[import-untyped]

PCG_RTOL = 1e-6
PCG_MAXITER = 500


@dataclass(frozen=True)
class ConvergenceReport:
    """Per-RHS iteration counts + final relative residuals (surfaced, never swallowed)."""

    iterations: np.ndarray
    final_rel_residual: np.ndarray


class MiostSolver:
    """Solve (G^T R^-1 G + Q^-1) X = B with stored CSR G; RHS-agnostic (seam a)."""

    def __init__(
        self,
        g: sparse.csr_matrix,
        r_diag: np.ndarray,
        q_diag: np.ndarray,
        pcg_rtol: float = PCG_RTOL,
        pcg_maxiter: int = PCG_MAXITER,
    ) -> None:
        """Store operators and precompute the Jacobi preconditioner.

        Args:
            g: CSR observation basis matrix (n_obs, n_coef).
            r_diag: Observation-error variances (n_obs,).
            q_diag: Prior coefficient variances (n_coef,).
            pcg_rtol: Relative-residual convergence tolerance.
            pcg_maxiter: Iteration cap.
        """
        self.g = g
        self.r_inv = 1.0 / np.asarray(r_diag, float) if r_diag.size else r_diag
        self.q_inv = 1.0 / np.asarray(q_diag, float)
        self.pcg_rtol = pcg_rtol
        self.pcg_maxiter = pcg_maxiter
        # Jacobi preconditioner: diag(G^T R^-1 G) + Q^-1 = sum_i g_ip^2 / r_i + 1/q_p
        if g.shape[0] == 0:
            self._m_inv = 1.0 / self.q_inv
        elif sparse.issparse(g) and g.format == "csc":
            # Column-blocked, no G copy: the huge single-window G (~6.5 GB)
            # cannot afford the g.copy() temporary.
            self._m_inv = 1.0 / (self._csc_col_sq_sums(g) + self.q_inv)
        else:
            g2 = g.copy()
            g2.data = g2.data**2
            self._m_inv = 1.0 / (g2.T @ self.r_inv + self.q_inv)

    def _csc_col_sq_sums(self, g: sparse.csc_matrix) -> np.ndarray:
        """Per-column sum of g_ip^2 / r_i over CSC segments, in bounded blocks."""
        n_col = g.shape[1]
        out = np.empty(n_col)
        indptr = g.indptr
        block = 65_536
        for c0 in range(0, n_col, block):
            c1 = min(c0 + block, n_col)
            lo, hi = int(indptr[c0]), int(indptr[c1])
            w = g.data[lo:hi] ** 2 * self.r_inv[g.indices[lo:hi]]
            c = np.concatenate([[0.0], np.cumsum(w)])
            out[c0:c1] = c[indptr[c0 + 1 : c1 + 1] - lo] - c[indptr[c0:c1] - lo]
        return out

    def apply_a(self, x: np.ndarray) -> np.ndarray:
        """A-apply in two SpMVs (G then G^T) + diagonal.

        Args:
            x: Vector (n_coef,) or block (n_coef, k).

        Returns:
            A @ x with the same shape as ``x``.
        """
        if self.g.shape[0] == 0:
            return np.asarray((self.q_inv * x.T).T if x.ndim > 1 else self.q_inv * x)
        gx = self.g @ x
        gtx = self.g.T @ (self.r_inv[:, None] * gx if gx.ndim > 1 else self.r_inv * gx)
        return np.asarray(
            gtx + (self.q_inv[:, None] * x if x.ndim > 1 else self.q_inv * x)
        )

    def solve(self, b: np.ndarray) -> tuple[np.ndarray, ConvergenceReport]:
        """Blocked PCG; B is (n,) or (n, k); columns solved jointly, converged per-column.

        Args:
            b: Right-hand side(s) — arbitrary, not necessarily derived from obs.

        Returns:
            (solution matching ``b``'s shape, per-RHS convergence report).
        """
        b2 = np.atleast_2d(np.asarray(b, float).T).T  # (n, k)
        x = np.zeros_like(b2)
        r = b2 - self.apply_a(x)
        z = self._m_inv[:, None] * r
        p = z.copy()
        rz = np.einsum("ij,ij->j", r, z)
        b_norm = np.maximum(np.linalg.norm(b2, axis=0), 1e-300)
        iters = np.zeros(b2.shape[1], dtype=int)
        for it in range(1, self.pcg_maxiter + 1):
            ap = self.apply_a(p)
            alpha = rz / np.maximum(np.einsum("ij,ij->j", p, ap), 1e-300)
            x += alpha * p
            r -= alpha * ap
            rel = np.linalg.norm(r, axis=0) / b_norm
            active = rel > self.pcg_rtol
            iters[active] = it
            if not active.any():
                break
            z = self._m_inv[:, None] * r
            rz_new = np.einsum("ij,ij->j", r, z)
            p = z + (rz_new / np.maximum(rz, 1e-300)) * p
            rz = rz_new
        report = ConvergenceReport(iters, np.linalg.norm(r, axis=0) / b_norm)
        return (x[:, 0], report) if np.asarray(b).ndim == 1 else (x, report)


def rhs_from_obs(g: sparse.csr_matrix, r_diag: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Seam (b): b(y) = G^T R^-1 y as its own first-class unit.

    Args:
        g: CSR observation basis matrix.
        r_diag: Observation-error variances.
        y: Observation values.

    Returns:
        Reduced-space right-hand side.
    """
    return np.asarray(g.T @ (y / r_diag))
