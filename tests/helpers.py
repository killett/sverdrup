"""Shared test helpers (Phase-11)."""

from __future__ import annotations

from typing import Any


def row_metric(scores: dict[str, Any], evaluator: str, name: str) -> float:
    """Read one metric from a pipeline ``scores["report_rows"]`` block.

    Args:
        scores: The pipeline scores dict (post Phase-11 shape).
        evaluator: Evaluator row name, e.g. ``"accuracy"``.
        name: Metric name inside that row, e.g. ``"rmse"``.

    Returns:
        The metric value.
    """
    (row,) = [r for r in scores["report_rows"] if r["evaluator"] == evaluator]
    return float(row["metrics"][name])
