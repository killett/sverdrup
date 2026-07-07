"""Report-only localized calibration splits (Task-19 owner protocol item 3)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

_SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "diag_stage_b_localized_calibration.py"
)


@pytest.fixture(scope="module")
def mod() -> Any:
    spec = importlib.util.spec_from_file_location("diag_stage_b_localized", _SCRIPT)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    sys.modules["diag_stage_b_localized"] = m
    spec.loader.exec_module(m)
    yield m
    del sys.modules["diag_stage_b_localized"]


def test_localized_coverage_hand_classes(mod: Any) -> None:
    """Every split classifies hand-placed points correctly at frozen s.

    Hand: 4 points. s=4, var=1 -> 1-sigma band = 2.0.
      p0: day 10 (interior; January; SW quadrant), resid 1.0 -> covered
      p1: day 30 (blend zone of w0/w1 [27,42]; January; NE), resid 3.0 -> NOT
      p2: day 100 (interior; April; SW), resid 1.9 -> covered
      p3: day 350 (blend zone [322,357]; December; NE), resid 2.1 -> NOT
    So: blend coverage 0/2, interior 2/2; SW 2/2, NE 0/2; Jan 1/2 (p0 in,
    p1 out), Apr 1/1, Dec 0/1. Bug caught: wrong blend-zone day
    classification (the [322,357] 35-d overlap is the trap), quadrant
    boundary on the wrong side, or s applied as sqrt(s) to the band.
    """
    day = np.array([10.0, 30.0, 100.0, 350.0])
    lon = np.array([296.0, 304.0, 296.0, 304.0])
    lat = np.array([34.0, 42.0, 34.0, 42.0])
    resid = np.array([1.0, 3.0, 1.9, 2.1])
    var = np.ones(4)
    out = mod.localized_coverage(day, lon, lat, resid, var, s=4.0)
    assert out["blend"]["coverage_1sigma"] == pytest.approx(0.0)
    assert out["blend"]["n"] == 2
    assert out["interior"]["coverage_1sigma"] == pytest.approx(1.0)
    assert out["quadrant_SW"]["coverage_1sigma"] == pytest.approx(1.0)
    assert out["quadrant_NE"]["coverage_1sigma"] == pytest.approx(0.0)
    assert out["month_01"]["coverage_1sigma"] == pytest.approx(0.5)
    assert out["month_04"]["coverage_1sigma"] == pytest.approx(1.0)
    assert out["month_12"]["coverage_1sigma"] == pytest.approx(0.0)
