"""The unit of work: a single parametrised windowed solve (invariant 5; spec 5.9)."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from sverdrup.core.grid import GridSpec
from sverdrup.core.observations import ObsWindow
from sverdrup.core.parameters import ParameterProvider


@dataclass
class UnitOfWork:
    """A self-contained windowed solve: inputs, parameters, split, and what to extract."""

    window_id: str
    method_name: str
    params: ParameterProvider
    split_id: str
    seed: int
    output_times: list[float]
    obs: (
        ObsWindow | None
    )  # None only for obs-less coordinator probes (tests); real solves set it
    grid: GridSpec
    eval_locations: np.ndarray | None = None
    derived_names: list[str] = field(default_factory=list)
    rank: int = 40
