"""Stage-B gate-runner helpers (plan Task 19 step 1; spec 6.5/6.6).

Only the load-bearing, data-independent logic is tested here: the member
solver-budget escalation (§6.5 — under-converged members are BIASED draws
and must never be silently accepted) and the s-inflated calibration triplet.
The full --stage-b evidence assembly runs on real data at the gate.
"""

from __future__ import annotations

import sys
from typing import Any

import numpy as np
import pytest

from sverdrup.core.grid import GridSpec
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
from sverdrup.core.parameters import ConstantProvider
from sverdrup.methods.miost_windows import WindowPlan
from tests.helpers import load_script

M = 3
ROOT = 12345
# log10_rho = -1 is winner-like and well-conditioned (converges well under
# the 500 cap); the escalation test forces failure via an unreachable rtol.
PARAMS = ConstantProvider(
    {"spacing_alpha": 1.5, "log10_rho": -1.0, "q_slope": 2.0, "l_t_days": 10.0}
)
GRID = GridSpec.lonlat(np.linspace(296.0, 304.0, 5), np.linspace(34.0, 42.0, 5))


def _obs(n: int = 60) -> ObsWindow:
    rng = np.random.default_rng(7)
    err = DiagonalErrorModel(np.full(n, 0.01))
    mission = np.asarray(["alg", "s3a"])[rng.integers(0, 2, n)]
    return ObsWindow.from_arrays(
        rng.uniform(296, 304, n),
        rng.uniform(34, 42, n),
        np.concatenate([[-10.5, 70.5], rng.uniform(-12.0, 72.0, n - 2)]),
        rng.standard_normal(n) * 0.1,
        err,
        mission,
    )


@pytest.fixture(scope="module")
def runner() -> Any:
    from sverdrup.application.tuning.scorer import ValidationTrackScorer

    orig = ValidationTrackScorer.score
    mod = load_script("stage_miost_gate_run")
    yield mod
    ValidationTrackScorer.score = orig  # type: ignore[method-assign]  # script wraps at import
    sys.modules.pop("stage_miost_gate_run", None)


def test_escalated_members_converges_at_first_cap(runner: Any) -> None:
    """A convergable config returns converged=True at the first cap.

    Bug caught: the escalation loop re-solving (or escalating) even when
    the first attempt met rtol — at the gate that would triple the
    member-generation wall for nothing.
    """
    plan = WindowPlan(starts=(0.0,))
    out = runner._escalated_members(
        plan, _obs(), GRID, PARAMS, m=M, root=ROOT, rtol=1e-6, caps=(500,)
    )
    assert out["converged"] is True
    assert out["maxiter_used"] == 500
    assert len(out["member_batches"]) == 1  # one window in this plan
    assert all(b["final_rel_residual"] <= 1e-6 for b in out["member_batches"])
    assert set(out["anoms"]) == {w.id for w in plan.windows}


def test_escalated_members_never_accepts_biased_draws(runner: Any) -> None:
    """Unreachable rtol exhausts the caps and reports converged=False.

    Bug caught: silently returning the last under-converged batch as good
    (the §6.5 biased-draw class — under-dispersed members at the gate); the
    caller must see converged=False and STOP for the owner.
    """
    plan = WindowPlan(starts=(0.0,))
    out = runner._escalated_members(
        plan, _obs(), GRID, PARAMS, m=M, root=ROOT, rtol=1e-15, caps=(2, 3)
    )
    assert out["converged"] is False
    assert out["maxiter_used"] == 3  # escalated to the LAST cap before stopping
    assert all(b["final_rel_residual"] > 1e-15 for b in out["member_batches"])


def test_calibration_at_s_hand_values(runner: Any) -> None:
    """The s-inflated triplet matches hand arithmetic.

    Hand: residuals all 0.5, var all 1.0 -> chi2(1) = 0.25; at s = 0.25 the
    inflated chi2 = 0.25/0.25 = 1.0 and coverage_1sigma = 1.0 (|0.5| <=
    sqrt(0.25)); at s = 0.04, sd = 0.2 < 0.5 -> coverage 0.0.
    Bug caught: s applied to the mean, applied as 1/s, or applied to sd
    instead of var (sqrt(s) error).
    """
    n = 8
    mu = np.zeros(n)
    ssh = np.full(n, 0.5)
    var = np.ones(n)
    cal1 = runner._calibration_at(mu, var, ssh, s=0.25)
    assert cal1["reduced_chi2"] == pytest.approx(1.0)
    assert cal1["coverage_1sigma"] == pytest.approx(1.0)
    assert cal1["crps"] > 0.0
    cal2 = runner._calibration_at(mu, var, ssh, s=0.04)
    assert cal2["coverage_1sigma"] == pytest.approx(0.0)
    assert cal2["reduced_chi2"] == pytest.approx(0.25 / 0.04)


def test_c2_touch_once_guard(runner: Any) -> None:
    """A second c2 touch is refused loudly.

    Bug caught: rerunning --c2-touch silently overwriting the single
    acceptance record — the hygiene order is ONE touch, winner-only.
    """
    with pytest.raises(RuntimeError, match="already"):
        runner._assert_c2_untouched({"c2_acceptance": {"x": 1}})
    runner._assert_c2_untouched({"status": "READY"})  # first touch allowed


def test_c2_reading_pre_registered(runner: Any) -> None:
    """Owner's pre-registered reading is applied exactly.

    Hand: Stage-A ref (0.8573, 0.08, 156.4). (a) identical scores +
    coverage 0.70 (in 0.6827+-0.10) -> SIGNED OFF; (b) identical +
    coverage 0.55 -> HOLD; (c) any score deviation -> DEFECT even with
    good coverage. Bug caught: deviation tolerated (owner: bit-identical
    or defect), or the band check inverted.
    """
    ref = [0.8573, 0.08, 156.4]
    ok = runner._c2_reading(list(ref), ref, {"coverage_1sigma": 0.70})
    assert ok.startswith("SIGNED OFF")
    hold = runner._c2_reading(list(ref), ref, {"coverage_1sigma": 0.55})
    assert hold.startswith("HOLD")
    bad = runner._c2_reading([0.8574, 0.08, 156.4], ref, {"coverage_1sigma": 0.70})
    assert bad.startswith("DEFECT")
