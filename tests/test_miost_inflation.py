"""s-inflation via exact anomaly rescale + mean-unchanged non-regression (Task 17, D6)."""

from __future__ import annotations

import sys
from typing import Any

import numpy as np
import pytest

from sverdrup.core.grid import GridSpec
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
from sverdrup.core.parameters import ConstantProvider
from sverdrup.core.provenance import TransformKind
from sverdrup.methods.miost import Miost
from sverdrup.methods.miost_windows import WindowPlan
from tests.helpers import load_script

M = 5
DAY = 50.0
PARAMS = ConstantProvider(
    {"spacing_alpha": 1.5, "log10_rho": 1.3, "q_slope": 2.0, "l_t_days": 10.0}
)
GRID = GridSpec.lonlat(np.linspace(296.0, 304.0, 6), np.linspace(34.0, 42.0, 6))


@pytest.fixture(scope="module")
def infl_mod() -> Any:
    mod = load_script("tune_miost_inflation")
    yield mod
    del sys.modules["tune_miost_inflation"]


def _obs(n: int = 60) -> ObsWindow:
    rng = np.random.default_rng(3)
    return ObsWindow.from_arrays(
        rng.uniform(296, 304, n),
        rng.uniform(34, 42, n),
        rng.uniform(-12.0, 117.0, n),
        rng.standard_normal(n) * 0.1,
        DiagonalErrorModel(np.full(n, 0.01)),
        None,
    )


@pytest.fixture(scope="module")
def dist() -> Any:
    return Miost(plan=WindowPlan(starts=(0.0, 45.0))).sample_members(
        _obs(), GRID, PARAMS, DAY, m=M, root=77
    )


def test_rescaled_mean_bit_identical_variance_scaled(dist: Any) -> None:
    """rescaled(s): mean BIT-IDENTICAL (np.array_equal); variance exactly x s.

    Catches: rescaling members instead of anomalies (shifts the mean — the
    D6 violation), or scaling by s instead of sqrt(s) (variance x s^2).
    """
    s = 2.7
    var_before = np.asarray(dist.marginal_variance()).copy()
    re = dist.rescaled(s)
    assert np.array_equal(np.asarray(re.mean), np.asarray(dist.mean))
    np.testing.assert_allclose(
        re.marginal_variance(), s * dist.marginal_variance(), rtol=1e-12
    )
    # Original untouched (no aliasing mutation): compare against a snapshot
    # taken BEFORE rescaled() was called.
    np.testing.assert_array_equal(dist.marginal_variance(), var_before)


def test_rescaled_records_provenance(dist: Any) -> None:
    """rescaled(s) appends a DIAGONAL_INFLATION transform carrying s.

    Catches: silent recalibration — downstream consumers could not tell an
    inflated ensemble from a native one.
    """
    re = dist.rescaled(1.5)
    assert re.provenance.transformations[-1].kind is TransformKind.DIAGONAL_INFLATION
    assert re.provenance.transformations[-1].params["s"] == pytest.approx(1.5)
    assert (
        len(re.provenance.transformations) == len(dist.provenance.transformations) + 1
    )


def test_chi2_closed_form(infl_mod: Any) -> None:
    """chi2_red(s) = chi2_red(1)/s, so s* = chi2_red(1) gives chi2_red(s*) = 1.

    Catches: an inverted closed form (s* = 1/chi2) — inflation would shrink
    an under-dispersed ensemble further.
    """
    rng = np.random.default_rng(5)
    truth = rng.standard_normal(500)
    mean = truth + rng.standard_normal(500) * 0.3
    var = np.full(500, 0.02)  # deliberately under-dispersed: chi2 >> 1
    from sverdrup.eval.calibration import reduced_chi2

    s_star = infl_mod.s_star_closed_form(mean, var, truth)
    assert s_star == pytest.approx(reduced_chi2(mean, var, truth))
    assert s_star > 1.0  # under-dispersed -> inflate
    assert reduced_chi2(mean, s_star * var, truth) == pytest.approx(1.0, rel=1e-12)


def test_scalar_r_condition(infl_mod: Any) -> None:
    """Non-uniform per-obs R raises (the closed form assumes scalar R).

    Catches: silently applying the scalar-R closed form to heteroscedastic
    obs, where s* is no longer the chi2 minimizer.
    """
    infl_mod.assert_scalar_r(np.full(10, 0.01))  # uniform: fine
    with pytest.raises(ValueError, match="scalar"):
        infl_mod.assert_scalar_r(np.array([0.01, 0.01, 0.02]))


def test_stage_b_code_leaves_solve_unchanged() -> None:
    """Miost.solve day map is unchanged by member generation on the same
    instance AND matches a fresh instance (mean-unchanged non-regression).

    Catches: sample_members polluting the eta/S caches (wrong key, mutated
    eta) so the Stage-A map silently changes under Stage-B code.
    """
    obs = _obs()
    m1 = Miost(plan=WindowPlan(starts=(0.0, 45.0)))
    before = np.asarray(m1.solve(obs, GRID, PARAMS, DAY).mean).copy()
    m1.sample_members(obs, GRID, PARAMS, DAY, m=3, root=1)
    after = np.asarray(m1.solve(obs, GRID, PARAMS, DAY).mean)
    np.testing.assert_array_equal(before, after)
    fresh = np.asarray(
        Miost(plan=WindowPlan(starts=(0.0, 45.0))).solve(obs, GRID, PARAMS, DAY).mean
    )
    np.testing.assert_array_equal(before, fresh)
