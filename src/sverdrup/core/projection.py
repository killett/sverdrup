"""The Projection seam: read any field/covariance off a precision (spec §5.1, Phase-4).

A Projection abstracts the linear map ``W`` (node space -> query points) and the
node-space description, so the GMRF operator and the persisted form are
discretization-agnostic: the same hooks serve a regular grid (GridIdentity/Bilinear)
and, in Stage C, an FEM mesh (FEMBasis). ``A`` (node -> obs) is the same projection
evaluated at obs points.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from scipy import sparse  # type: ignore[import-untyped]

from sverdrup.core.types import Points


@runtime_checkable
class Projection(Protocol):
    """Node space + the ``W`` map to query points, plus the read-off precondition."""

    node_space: object

    def weights(self, pts: Points) -> sparse.csr_matrix:
        """Return the sparse ``(k, n_nodes)`` map from precision nodes to ``pts``."""
        ...

    def field_shape(self) -> tuple[int, ...]:
        """Return the field shape: ``(ny, nx)`` for a grid, ``(n_nodes,)`` for a mesh."""
        ...

    def node_points(self, time_days: float) -> Points:
        """Return the ``(n_nodes, 3)`` coordinates of the precision nodes."""
        ...

    def assert_adjacency(self, q: sparse.spmatrix) -> None:
        """Raise if ``q``'s pattern lacks the entries the read-off/derived ops need."""
        ...
