"""Shared test helpers (Phase-11)."""

from __future__ import annotations

import importlib.util
import json
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


def install_valid_production_seal(tmp_path: Path, monkeypatch: Any) -> Path:  # noqa: ANN401
    """Point the DEFAULT seal store at a tmp store carrying a VALID seal.

    The seal-path tests (hygiene item 45) need the production pointer to
    verify cleanly while the caller's own ``evidence_path`` carries no seal
    at all: a writer that verifies the default store instead of the store it
    writes then passes, and only a writer that honours its argument refuses.
    Independent of whether this host has a real store.

    Args:
        tmp_path: Pytest temporary directory.
        monkeypatch: Pytest monkeypatch fixture (redirects ``EVIDENCE``).

    Returns:
        The substitute "production" store path.
    """
    from sverdrup.validation import phase14_seal

    seal_path = tmp_path / "production_seal_v1.json"
    sha = phase14_seal.build_seal({"sealed": "for the test"}, seal_path)
    production = tmp_path / "production_store.json"
    production.write_text(
        json.dumps(
            {"phase14": {"stage0": {"seal": {"path": str(seal_path), "sha": sha}}}}
        )
    )
    monkeypatch.setattr(phase14_seal, "EVIDENCE", production)
    phase14_seal.verify_current_seal()  # the precondition: default verifies
    return production
