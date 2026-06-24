"""Area-weighted global aggregation (invariant 11; design section 9)."""

from __future__ import annotations

import numpy as np

from sverdrup.core.grid import GridSpec
from sverdrup.core.types import Field


def area_weighted_mean(field: Field, grid: GridSpec) -> float:
    """Return ``sum(area * field) / sum(area)`` using true spherical cell areas.

    Args:
        field: A ``(ny, nx)`` field aligned with ``grid``.
        grid: The grid supplying ``cell_area()`` weights (cos(lat) shrinkage).

    Returns:
        The area-weighted global mean.
    """
    area = grid.cell_area()
    return float((area * field).sum() / area.sum())


def area_weighted_rmse(error_field: Field, grid: GridSpec) -> float:
    """Return the area-weighted RMS of an error field.

    Args:
        error_field: A ``(ny, nx)`` error field aligned with ``grid``.
        grid: The grid supplying ``cell_area()`` weights.

    Returns:
        The area-weighted root-mean-square error.
    """
    area = grid.cell_area()
    return float(np.sqrt((area * error_field**2).sum() / area.sum()))
