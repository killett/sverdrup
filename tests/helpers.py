"""Shared test helpers (Phase-11)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"


def load_script(name: str, module_name: str | None = None) -> ModuleType:
    """Import a repo script by path (``scripts/`` is not a package).

    The module is registered in ``sys.modules`` before execution (the
    sys.modules-correct variant from ``test_provenance_guard``) so machinery
    that resolves the module by name (dataclasses, pickling, typing) works.
    The entry is left registered; callers that need unload-after-use
    semantics (e.g. module-scoped fixtures) pop it themselves on teardown.

    Args:
        name: Script filename stem under ``scripts/``.
        module_name: Optional ``sys.modules`` key (defaults to ``name``).

    Returns:
        The executed module.
    """
    mod_name = module_name or name
    spec = importlib.util.spec_from_file_location(mod_name, _SCRIPTS_DIR / f"{name}.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


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
