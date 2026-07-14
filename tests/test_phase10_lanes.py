"""Lane machinery (Phase-10 Task 6; spec §2 boxes, §4 lanes/seeds/anchors/bars).

Bugs caught per test: box endpoints drifting from the pre-registered values;
restriction bookkeeping broken (frozen coords not pinned at exactly 0.0);
per-lane Sobol engines (shared-dim draws differing across lanes at the same
trial index — kills pairing); the provider emitting a field for an all-zero
released set (lane-0 trials routed off the stationary class) or emitting the
multiplier under lx_deg (the Task-4 contract trap); anchor embedding missing
or mutating the source winners; the coverage bar dropped or the SIGMA_OBS2
convention lost.
"""

from __future__ import annotations

import math

from sverdrup.application.calibration.constants import SIGMA_OBS2
from sverdrup.application.tuning.objective import bars_for
from sverdrup.core.parameters import LatitudeField
from sverdrup.core.types import UncertaintyCapability
from sverdrup.methods.kernel import GaussianSpaceTimeDegrees, PaciorekGaussianDegrees
from sverdrup.validation.phase10_lanes import (
    ALL_DIMS,
    BOXES,
    LANES,
    anchors_for,
    lane_bars,
    lane_coverage_extra_var,
    provider_for_trial,
    sobol_trials,
)
from sverdrup.validation.run import gaussian_kernel_from_params


def test_boxes_pinned_to_preregistered_endpoints() -> None:
    assert BOXES["c0"] == (-1.5, 1.5)
    assert BOXES["c1"] == (-1.0, 1.0)
    assert BOXES["c2"] == (-1.5, 1.5)
    assert BOXES["log_L0"] == (math.log(0.5), math.log(2.0))
    assert BOXES["l1"] == (-0.5, 0.3)
    assert BOXES["Lt"] == (3.0, 14.0)


def test_lane_restrictions() -> None:
    assert LANES["lane0"] == frozenset()
    assert LANES["V"] == frozenset({"c1", "c2"})
    assert LANES["VL"] == frozenset({"c1", "c2", "l1"})


def test_restriction_bookkeeping_frozen_at_zero() -> None:
    # Every trial dict carries ALL six dims; frozen coords are EXACTLY 0.0.
    for lane, released in LANES.items():
        trials = sobol_trials(lane, 4)
        frozen = {"c1", "c2", "l1"} - released
        for t in trials:
            assert set(t) == set(ALL_DIMS)
            for dim in frozen:
                assert t[dim] == 0.0
            for dim in released | {"c0", "log_L0", "Lt"}:
                lo, hi = BOXES[dim]
                assert lo <= t[dim] <= hi


def test_paired_sobol_shared_dims_identical_across_lanes() -> None:
    # ONE engine seed for all lanes: at the same trial index, the shared
    # (core) dims are identical across lanes, and V/VL share c1/c2 draws.
    t0 = sobol_trials("lane0", 5)
    tv = sobol_trials("V", 5)
    tvl = sobol_trials("VL", 5)
    for i in range(5):
        for dim in ("c0", "log_L0", "Lt"):
            assert t0[i][dim] == tv[i][dim] == tvl[i][dim]
        for dim in ("c1", "c2"):
            assert tv[i][dim] == tvl[i][dim]
        assert tv[i][dim] != 0.0  # released draws are real draws


def test_provider_lane0_routes_stationary_class() -> None:
    trial = sobol_trials("lane0", 1)[0]
    p = provider_for_trial(trial)
    k = gaussian_kernel_from_params(p, None)
    assert isinstance(k, GaussianSpaceTimeDegrees)
    # Hand-check: lx = exp(log_L0), variance = exp(c0), Lt passes through.
    assert k.lx_deg == math.exp(trial["log_L0"])
    assert k.variance == math.exp(trial["c0"])
    assert k.time_scale == trial["Lt"]


def test_provider_vl_routes_paciorek_with_lx_mult() -> None:
    trial = dict.fromkeys(ALL_DIMS, 0.0)
    trial.update(
        {"c0": 0.1, "c1": 0.2, "c2": -0.3, "log_L0": 0.1, "l1": -0.2, "Lt": 7.0}
    )
    p = provider_for_trial(trial)
    k = gaussian_kernel_from_params(p, None)
    assert isinstance(k, PaciorekGaussianDegrees)
    assert k.variance_field == LatitudeField("exp-quad", (0.1, 0.2, -0.3))
    assert k.l_mult_field == LatitudeField("exp-linear-mult", (-0.2,))
    assert k.lx_deg_base == math.exp(0.1)


def test_provider_omits_lx_mult_at_l1_zero() -> None:
    # The Task-4 contract: l1 == 0 -> NO lx_mult entry (a zero-coefficient
    # field would route Paciorek and break lane-0/V stationary dispatch).
    trial = dict.fromkeys(ALL_DIMS, 0.0)
    trial.update({"c0": 0.0, "c1": 0.5, "c2": 0.0, "log_L0": 0.0, "l1": 0.0, "Lt": 7.0})
    p = provider_for_trial(trial)
    assert "lx_mult" not in p.varied
    k = gaussian_kernel_from_params(p, None)
    assert isinstance(k, PaciorekGaussianDegrees)  # variance field released
    assert k.l_mult_field is None


def test_anchors_pre_registered() -> None:
    lane0_w = dict.fromkeys(ALL_DIMS, 0.0)
    lane0_w.update({"c0": 0.3, "log_L0": -0.1, "Lt": 8.0})
    # Give the V winner a NONZERO l1 marker so a mutating anchors_for (setting
    # l1=0 on the source instead of a copy) is actually caught below.
    v_w = dict(lane0_w, c1=0.4, c2=-0.2, l1=0.25)
    winners = {"lane0": lane0_w, "V": v_w}
    snap_lane0, snap_v = dict(lane0_w), dict(v_w)
    assert anchors_for("lane0", winners) == []
    assert anchors_for("V", winners) == [lane0_w]
    vl_anchors = anchors_for("VL", winners)
    assert lane0_w in vl_anchors
    assert dict(v_w, l1=0.0) in vl_anchors  # V winner enters VL at l1=0
    assert winners["lane0"] == snap_lane0  # sources not mutated
    assert winners["V"] == snap_v


def test_scorer_provider_factory_seam() -> None:
    # Bug caught: the scorer silently ignoring provider_factory and wrapping
    # phase-10 trial dicts in ConstantProvider (whose names the Gaussian
    # factory cannot resolve).
    from pathlib import Path
    from typing import Any, cast

    from sverdrup.application.tuning.scorer import ValidationTrackScorer
    from sverdrup.core.parameters import ConstantProvider

    def _scorer(**overrides: Any) -> ValidationTrackScorer:
        return ValidationTrackScorer(
            train_obs=cast(Any, None),
            grid=cast(Any, None),
            output_days=[0.0],
            temporal_half_window_days=14.0,
            val_track_path=Path("x.nc"),
            lon_min=295.0,
            lon_max=305.0,
            lat_min=33.0,
            lat_max=43.0,
            time_min="2017-01-01",
            time_max="2018-01-01",
            **overrides,
        )

    default = _scorer()
    assert isinstance(default._provider({"variance": 1.0}), ConstantProvider)
    assert default.coverage_extra_var == 0.0  # raw-var default preserved
    wired = _scorer(provider_factory=provider_for_trial)
    trial = sobol_trials("VL", 1)[0]
    p = wired._provider(trial)
    assert isinstance(p, type(provider_for_trial(trial)))
    assert p == provider_for_trial(trial)


def test_bars_are_capability_derived_with_coverage() -> None:
    bars = lane_bars()
    assert bars == bars_for(UncertaintyCapability.SAMPLES)
    assert [b.metric for b in bars] == ["mu_score", "coverage_1sigma"]
    # Coverage convention: raw posterior variance + SIGMA_OBS2 (one
    # convention with acceptance at s == 1).
    assert lane_coverage_extra_var() == SIGMA_OBS2
