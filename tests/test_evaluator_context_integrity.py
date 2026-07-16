"""Declared⇒consumed integrity over the whole evaluator family (plan Task 5).

Mechanizes constraint 3: (1) every REQUIRED key is actually READ on a
non-skip evaluation; (2) every READ key is declared (required or optional).

Implementation note (the honest narrowing of the spec §6 wording): membership
checks against a ``keys()`` COPY are untrackable — READS are what consume
data, so rule 2 tracks reads (``__getitem__`` / ``.get``), not membership
probes. The same narrowing applies to whole-dict iteration
(``.items()`` / ``__iter__``): it is NOT tracked, deliberately —
``EvalContext.keys()`` itself iterates the mapping, so counting iteration as
"reading every key" would flag every evaluator that checks availability.
An evaluator consuming data via iteration instead of keyed access would slip
rule 2; none does, and keyed access is the protocol's documented contract.
With that scope, a dormant key cannot hide: all four ContextKey members are
present in every fixture's items, so an evaluator that keyed-read an
undeclared key WOULD get data and WOULD be caught.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
import pytest

from sverdrup.core.evaluation import ContextKey, EvalContext, Evaluator, MetricScope
from sverdrup.eval import ALL_EVALUATORS
from tests.test_eval_resolution import _track


class _SpyItems(dict[ContextKey, object]):
    """Items mapping that records reads (``__getitem__`` and ``.get``)."""

    def __init__(self, data: dict[ContextKey, object]) -> None:
        super().__init__(data)
        self.reads: set[ContextKey] = set()

    def __getitem__(self, key: ContextKey) -> object:
        self.reads.add(key)
        return super().__getitem__(key)

    def get(self, key: ContextKey, default: object = None) -> object:
        self.reads.add(key)
        return super().get(key, default)


def _real_axes() -> tuple[np.ndarray, np.ndarray]:
    return np.arange(295, 305.01, 0.2), np.arange(33, 43.21, 0.2)


def _maps(seed: int, n_days: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    lon, lat = _real_axes()
    ny, nx = lat.size, lon.size
    kx = np.fft.fftfreq(nx)[None, :]
    ky = np.fft.fftfreq(ny)[:, None]
    kk = np.hypot(kx, ky)
    kk[0, 0] = np.inf
    amp = kk ** (-0.75)
    days = []
    for _ in range(n_days):
        z = rng.standard_normal((ny, nx)) + 1j * rng.standard_normal((ny, nx))
        f = np.real(np.fft.ifft2(amp * z))
        days.append(f / f.std())
    return np.stack(days)


def _geometry_bag() -> dict[str, Any]:
    return {
        "synth": {
            "asc": {
                "heading_north_deg": 12.0,
                "orbit_class": "repeat",
                "d_perp_km": 248.0,
                "s_lon_km": 315.0,
                "n_crossings": 30,
            },
            "desc": None,
        }
    }


def _fixtures() -> dict[str, tuple[dict[str, Any], dict[ContextKey, object]]]:
    """(result, full-context items) per evaluator name — non-skip path each."""
    rng = np.random.default_rng(0)
    lon, lat = _real_axes()
    n = 64
    obs_vals = rng.standard_normal(n)
    pred = obs_vals + 0.1 * rng.standard_normal(n)
    var = np.full(n, 0.05)
    point_result: dict[str, Any] = {
        "eval_mean": pred,
        "eval_var": var,
        "grid_mean": np.zeros((4, 4)),
    }
    map_result: dict[str, Any] = {
        "fields": _maps(1, 2),
        "grid_lon": lon,
        "grid_lat": lat,
        "field_kind": "mean",
    }
    eval_locs, eval_times, _times, observed, mapped = _track()
    res_result: dict[str, Any] = {
        "eval_locations": eval_locs,
        "eval_times": eval_times,
        "eval_mean": mapped,
    }

    def items(withheld: dict[str, np.ndarray]) -> dict[ContextKey, object]:
        # ALL FOUR members present — a dormant undeclared read cannot hide.
        return {
            ContextKey.TRUTH: {"field": np.zeros((4, 4))},
            ContextKey.WITHHELD_OBS: withheld,
            ContextKey.ORBIT_GEOMETRY: _geometry_bag(),
            ContextKey.PHYSICAL_CONSTANTS: {},
        }

    plain_obs = {"values": obs_vals}
    return {
        "accuracy": (point_result, items(plain_obs)),
        "calibration": (point_result, items(plain_obs)),
        "skill": (point_result, items(plain_obs)),
        "groundtrack": (map_result, items(plain_obs)),
        "spectral_fidelity": (map_result, items(plain_obs)),
        "effective_resolution": (res_result, items({"values": observed})),
    }


def _check_integrity(
    ev: Evaluator, result: object, items: dict[ContextKey, object]
) -> None:
    spy = _SpyItems(items)
    out = ev.evaluate(result, EvalContext(spy))
    assert out, "fixture must exercise the non-skip path"
    assert ev.required_context <= spy.reads, (
        f"{ev.name}: declared-required keys never read "
        f"{set(ev.required_context) - spy.reads}"
    )
    assert spy.reads <= ev.required_context | ev.optional_context, (
        f"{ev.name}: undeclared reads {spy.reads - (ev.required_context | ev.optional_context)}"
    )


@pytest.mark.parametrize("factory", ALL_EVALUATORS, ids=lambda f: f().name)
def test_declared_context_is_consumed(factory: Callable[[], Evaluator]) -> None:
    """Bug caught: the old GroundTrack-stub class of defect — a declared
    required key that evaluate() never reads (or an undeclared read)."""
    ev = factory()
    result, items = _fixtures()[ev.name]
    _check_integrity(ev, result, items)


def test_all_evaluators_covers_every_fixture() -> None:
    """Bug caught: a new evaluator registered without integrity coverage."""
    assert {f().name for f in ALL_EVALUATORS} == set(_fixtures())


class _DeclaresNeverReads:
    """The old stub pattern, kept as a regression canary."""

    name = "canary"
    required_context = frozenset({ContextKey.PHYSICAL_CONSTANTS})
    optional_context: frozenset[ContextKey] = frozenset()
    metric_scope = MetricScope.POINTWISE

    def evaluate(self, result: object, context: EvalContext) -> dict[str, float]:
        return {"x": 1.0}  # non-empty, but the declared key is never read


def test_canary_declares_but_never_reads_fails_rule_1() -> None:
    """Proves the integrity test BITES: the exact historical defect class
    (GroundTrack stub, EffectiveResolution over-declaration) must fail."""
    items: dict[ContextKey, object] = {
        ContextKey.TRUTH: {},
        ContextKey.WITHHELD_OBS: {},
        ContextKey.ORBIT_GEOMETRY: {},
        ContextKey.PHYSICAL_CONSTANTS: {},
    }
    with pytest.raises(AssertionError, match="never read"):
        _check_integrity(_DeclaresNeverReads(), {}, items)
