"""Linear-solver seam: dense Cholesky now, sparse/iterative later (same kernel formulation)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np
from scipy.linalg import cho_solve, solve_triangular  # type: ignore[import-untyped]


@runtime_checkable
class LinearSolver(Protocol):
    """Factor-once / solve-many linear solver for the obs-obs system."""

    def factor(self, a: np.ndarray) -> None:
        """Factor the SPD matrix ``a``."""
        ...

    def solve(self, b: np.ndarray) -> np.ndarray:
        """Solve ``a x = b`` using the cached factor."""
        ...

    def solve_triangular_lower(self, b: np.ndarray) -> np.ndarray:
        """Return ``L^-1 b`` using the cached lower Cholesky factor."""
        ...


class DenseCholeskySolver:
    """Caches one Cholesky factor of ``K_dd + R`` and reuses it everywhere."""

    def __init__(self) -> None:
        """Initialise with no cached factor."""
        self._cho: tuple[np.ndarray, bool] | None = None
        self.lower: np.ndarray | None = None

    def factor(self, a: np.ndarray) -> None:
        """Compute and cache the lower Cholesky factor of SPD ``a``.

        Args:
            a: A symmetric positive-definite matrix.
        """
        self.lower = np.linalg.cholesky(a)
        self._cho = (self.lower, True)

    def solve(self, b: np.ndarray) -> np.ndarray:
        """Solve ``a x = b`` via the cached Cholesky factor.

        Args:
            b: The right-hand side.

        Returns:
            The solution ``x``.
        """
        if self._cho is None:
            raise RuntimeError("factor() must be called before solve().")
        return np.asarray(cho_solve(self._cho, b))

    def solve_triangular_lower(self, b: np.ndarray) -> np.ndarray:
        """Return ``L^-1 b`` via a forward triangular solve.

        Args:
            b: The right-hand side.

        Returns:
            ``L^-1 b`` where ``L`` is the cached lower Cholesky factor.
        """
        if self.lower is None:
            raise RuntimeError(
                "factor() must be called before solve_triangular_lower()."
            )
        return np.asarray(solve_triangular(self.lower, b, lower=True))
