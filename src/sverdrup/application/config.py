"""Run configuration value objects."""

from __future__ import annotations

from dataclasses import dataclass, field

from sverdrup.adapters.executor_dask import ExecutorConfig


@dataclass(frozen=True)
class RunConfig:
    """The full specification of one pipeline run (OSSE or OSE)."""

    mode: str  # "OSSE" | "OSE"
    method_name: str
    params: dict[str, float]
    lon_range: tuple[float, float]
    lat_range: tuple[float, float]
    time_range: tuple[float, float]
    output_times: list[float]
    grid_resolution_deg: float = 0.25
    executor: ExecutorConfig = field(default_factory=ExecutorConfig)
    split_by: str = "mission"
    rank: int = 40
