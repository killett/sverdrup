"""Pluggable, objective-agnostic search strategies over a method's parameter_space."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np
from scipy.stats import qmc  # type: ignore[import-untyped]

from sverdrup.application.tuning.trial import TrialHistory
from sverdrup.core.parameters import ParameterSpace


@runtime_checkable
class SearchStrategy(Protocol):
    """Propose parameter dicts to evaluate next (emitted as UoW trials by the loop)."""

    def propose(
        self, space: ParameterSpace, history: TrialHistory
    ) -> list[dict[str, float]]:
        """Return a batch of in-bounds parameter dicts."""
        ...


def _scale(unit: np.ndarray, space: ParameterSpace) -> list[dict[str, float]]:
    keys = list(space.bounds)
    lo = np.array([space.bounds[k][0] for k in keys])
    hi = np.array([space.bounds[k][1] for k in keys])
    scaled = lo + unit * (hi - lo)
    return [{k: float(v) for k, v in zip(keys, row, strict=True)} for row in scaled]


class RandomSearch:
    """Uniform random proposals (seeded)."""

    def __init__(self, seed: int, n: int = 16) -> None:
        """Store the seed and batch size ``n``."""
        self.seed, self.n = seed, n

    def propose(
        self, space: ParameterSpace, history: TrialHistory
    ) -> list[dict[str, float]]:
        """Return ``n`` uniform-random in-bounds parameter dicts (seeded)."""
        rng = np.random.default_rng(self.seed)
        unit = rng.random((self.n, len(space.bounds)))
        return _scale(unit, space)


class SobolSearch:
    """Low-discrepancy Sobol proposals (seeded)."""

    def __init__(self, seed: int, n: int = 16) -> None:
        """Store the seed and batch size ``n``."""
        self.seed, self.n = seed, n

    def propose(
        self, space: ParameterSpace, history: TrialHistory
    ) -> list[dict[str, float]]:
        """Return ``n`` low-discrepancy Sobol in-bounds parameter dicts (seeded)."""
        sampler = qmc.Sobol(d=len(space.bounds), scramble=True, seed=self.seed)
        unit = sampler.random(self.n)
        return _scale(unit, space)
