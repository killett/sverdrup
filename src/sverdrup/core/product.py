"""The Product bundle: a series of per-time persisted fields + derived + eval points (spec 5)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class EvalPointPredictions:
    """Exact off-grid predictive at evaluation/withheld locations (computed on-worker)."""

    locations: np.ndarray  # (k, 3) lon, lat, time
    mean: np.ndarray  # (k,)
    variance: np.ndarray  # (k,)
    samples: np.ndarray | None  # (m, k) for non-Gaussian reps, else None


@dataclass(frozen=True)
class PerTimeProduct:
    """All products for one output time, provenance-linked to the base."""

    time_days: float
    base: Any  # PersistedDistribution
    derived: dict[str, Any]  # name -> PersistedDistribution
    eval_points: EvalPointPredictions | None
    provenance: Any  # ProductProvenance


@dataclass(frozen=True)
class Product:
    """The full series-of-grids deliverable for one window/method/split."""

    per_time: list[PerTimeProduct]
    run_manifest: dict[str, Any]

    def times(self) -> list[float]:
        """Return the ordered output times across the per-time series."""
        return sorted(p.time_days for p in self.per_time)
