"""The unit of work: a single parametrised windowed solve (invariant 5; spec 5.9)."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from regatta.core.grid import GridSpec
from regatta.core.observations import ObsWindow
from regatta.core.parameters import ParameterProvider


@dataclass
class UnitOfWork:
    """A self-contained windowed solve: inputs, parameters, split, and what to extract."""

    window_id: str
    method_name: str
    params: ParameterProvider
    split_id: str
    seed: int
    output_times: list[float]
    obs: ObsWindow
    grid: GridSpec
    eval_locations: np.ndarray | None = None
    derived_names: list[str] = field(default_factory=list)
    rank: int = 40
