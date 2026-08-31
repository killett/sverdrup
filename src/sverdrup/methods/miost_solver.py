"""Multi-RHS Jacobi-preconditioned CG on the MIOST reduced normal equations (spec §2.4)."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

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

    def solve(
        self,
        b: np.ndarray,
        checkpoint: Path | None = None,
        checkpoint_every: int = 50,
    ) -> tuple[np.ndarray, ConvergenceReport]:
        """Blocked PCG; B is (n,) or (n, k); columns solved jointly, converged per-column.

        Optional mid-solve durability (phase-13 operational hardening): with
        ``checkpoint`` set, the full PCG state ``(x, r, p, rz, iters, it)``
        is persisted every ``checkpoint_every`` iterations and an existing
        checkpoint resumes the solve EXACTLY — the resumed iterate sequence
        is bit-identical to the uninterrupted one (z is dead state at the
        iteration boundary and is recomputed). The checkpoint binds to a
        hash of the RHS bytes; a mismatched system refuses. The file is
        removed after a completed solve.

        Args:
            b: Right-hand side(s) — arbitrary, not necessarily derived from obs.
            checkpoint: Optional path for crash-durable PCG state.
            checkpoint_every: Iterations between checkpoint writes.

        Returns:
            (solution matching ``b``'s shape, per-RHS convergence report).

        Raises:
            ValueError: If an existing checkpoint does not match this
                system's RHS (stale-checkpoint refusal).
        """
        b2 = np.atleast_2d(np.asarray(b, float).T).T  # (n, k)
        b_norm = np.maximum(np.linalg.norm(b2, axis=0), 1e-300)
        b_hash = ""
        if checkpoint is not None:
            b_hash = hashlib.blake2b(
                np.ascontiguousarray(b2).tobytes(), digest_size=16
            ).hexdigest()
        start_it = 1
        if checkpoint is not None and checkpoint.exists():
            try:
                ck_ctx = np.load(checkpoint)
            except Exception as exc:  # noqa: BLE001 - any load failure is corruption
                # Owner pin 122: a truncated checkpoint REFUSES, naming
                # itself. Resuming from a partially-loaded state would
                # produce a solve that is neither the interrupted one nor a
                # fresh one, with nothing to say so. A bare BadZipFile
                # tells an operator nothing about what to do.
                raise RuntimeError(
                    f"PCG checkpoint {checkpoint} is unreadable ({exc!r}) — it "
                    "is corrupt, most likely a crash inside its own write. "
                    "Delete it to solve fresh; do NOT resume from it"
                ) from exc
            with ck_ctx as ck:
                if str(ck["b_hash"]) != b_hash or tuple(ck["shape"]) != b2.shape:
                    raise ValueError(
                        "stale PCG checkpoint: saved state belongs to a "
                        "different system (RHS hash/shape mismatch) — delete "
                        f"{checkpoint} to solve fresh"
                    )
                x = np.asarray(ck["x"])
                r = np.asarray(ck["r"])
                p = np.asarray(ck["p"])
                rz = np.asarray(ck["rz"])
                iters = np.asarray(ck["iters"])
                start_it = int(ck["it"]) + 1
        else:
            x = np.zeros_like(b2)
            r = b2 - self.apply_a(x)
            z = self._m_inv[:, None] * r
            p = z.copy()
            rz = np.einsum("ij,ij->j", r, z)
            iters = np.zeros(b2.shape[1], dtype=int)
        for it in range(start_it, self.pcg_maxiter + 1):
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
            if checkpoint is not None and it % checkpoint_every == 0:
                # Owner pin 122: temp-and-rename, never a direct write to the
                # live path. os.replace is atomic on POSIX within a
                # filesystem, so a crash inside the write leaves the PREVIOUS
                # checkpoint intact instead of destroying the only one. The
                # content is unchanged; there is no numerical consequence.
                tmp = checkpoint.with_name(checkpoint.name + ".tmp")
                np.savez(
                    tmp,
                    x=x,
                    r=r,
                    p=p,
                    rz=rz,
                    iters=iters,
                    it=it,
                    b_hash=b_hash,
                    shape=np.asarray(b2.shape),
                )
                # np.savez appends .npz when the target has no suffix; the
                # rename must move whatever it actually wrote.
                written = tmp if tmp.exists() else tmp.with_name(tmp.name + ".npz")
                os.replace(written, checkpoint)
        if checkpoint is not None:
            checkpoint.unlink(missing_ok=True)
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
