"""EffectiveResolution scores λx on the validation track via the SHARED helper only."""

from __future__ import annotations

import inspect

import numpy as np

from sverdrup.core.evaluation import ContextKey, EvalContext, MetricScope
from sverdrup.eval.resolution import EffectiveResolution
from sverdrup.eval.spectral import effective_resolution_lambda_x
from sverdrup.validation.input_adapter import EPOCH


def _track(
    n: int = 6000, seg: int = 600
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(1)
    s = np.cumsum(rng.standard_normal(n)) * 0.01
    m = np.convolve(s, np.ones(50) / 50.0, mode="same")
    # Varying datetime64 along-track time with >4s pass gaps (the vendored λx needs
    # both: datetime64, and >=1 gap to segment on). Carried to the evaluator as the
    # pipeline-native float days-since-EPOCH in a dedicated eval_times channel.
    step = np.timedelta64(943400, "us")  # 0.9434 s
    gap = np.timedelta64(1, "D")
    idx = np.arange(n)
    times = EPOCH.astype("datetime64[us]") + idx * step + (idx // seg) * gap
    lat = np.full(n, 38.0)
    lon = 300.0 + np.cumsum(np.full(n, 6.39 / 111.0))
    eval_locs = np.column_stack([lon, lat, np.zeros(n)])  # (lon, lat, unused time col)
    eval_times = (times - EPOCH) / np.timedelta64(1, "D")  # float days
    return eval_locs, eval_times, times, s, m


def test_effective_resolution_metadata() -> None:
    ev = EffectiveResolution()
    assert ev.name == "effective_resolution"
    assert ev.metric_scope is MetricScope.POINTWISE
    assert ev.required_context == frozenset(
        {ContextKey.WITHHELD_OBS, ContextKey.ORBIT_GEOMETRY}
    )


def test_does_not_import_locked_test_harness() -> None:
    # Bug it catches: the per-trial λx path reaching into the locked-test harness.
    src = inspect.getsource(__import__("sverdrup.eval.resolution", fromlist=["x"]))
    assert "their_eval" not in src


def test_shared_path_lambda_x_identical() -> None:
    # TEST 7 (load-bearing): a real track end-to-end through BOTH call sites is identical.
    # Bug it catches: the two paths preparing residuals/time differently (false invariant-10).
    eval_locs, eval_times, times, observed, mapped = _track()
    ctx = EvalContext(
        {
            ContextKey.WITHHELD_OBS: {"values": observed},
            ContextKey.ORBIT_GEOMETRY: {"track_spacing_nodes": 4},
        }
    )
    result = {
        "eval_locations": eval_locs,
        "eval_times": eval_times,
        "eval_mean": mapped,
    }
    via_evaluator = EffectiveResolution().evaluate(result, ctx)["lambda_x"]
    via_helper = effective_resolution_lambda_x(
        times, eval_locs[:, 1], eval_locs[:, 0], observed, mapped
    )
    assert via_evaluator == via_helper
