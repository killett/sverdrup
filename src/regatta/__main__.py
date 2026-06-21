"""Runnable entry point: ``python -m regatta <config.json>``."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from regatta.adapters.executor_dask import ExecutorConfig
from regatta.adapters.odc.fixtures import FixtureSource
from regatta.application.pipeline import PipelineInputs, run_pipeline


def main(argv: list[str]) -> int:
    """Run a config-driven pipeline, or print usage when no config is given.

    Args:
        argv: The process argv (``argv[1]`` is the config path).

    Returns:
        Process exit code (0 on success).
    """
    if len(argv) < 2:
        print("usage: python -m regatta <config.json>")
        return 0
    cfg = json.loads(Path(argv[1]).read_text())
    src = FixtureSource(cfg["obs_path"], cfg.get("ref_path"))
    inp = PipelineInputs(
        mode=cfg["mode"],
        method_name=cfg["method"],
        source=src,
        out_url=cfg["out_url"],
        lon_range=tuple(cfg["lon_range"]),
        lat_range=tuple(cfg["lat_range"]),
        time_range=tuple(cfg["time_range"]),
        output_times=cfg["output_times"],
        params=cfg["params"],
        grid_resolution_deg=cfg.get("grid_resolution_deg", 1.0),
        executor=ExecutorConfig(**cfg.get("executor", {})),
        rank=cfg.get("rank", 20),
    )
    product, scores = run_pipeline(inp)
    reported = {k: v for k, v in scores.items() if k != "context_keys"}
    print(f"wrote {len(product.per_time)} time(s); scores={reported}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
