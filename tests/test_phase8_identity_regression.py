"""Phase-8 Task 5: s*-identity four-route regression + mean-unchanged extension.

Pins the four spec identities (§2 (i)/(ii)) against ScalarCalibration(S_STAR)
and extends the mean-unchanged non-regression to field-calibrated products.

All tests should pass IMMEDIATELY if Tasks 3–4 are correct.  A failure here
means a Task-3/4 defect — do not fix distribution code here.

External tests (``@pytest.mark.external``) reconstruct the SHIPPED product at
one map day (time index 0 = 2017-01-01, covered by exactly one solve window)
through the same code path the Stage-B gate runner used
(``scripts/stage_miost_gate_run.py::stage_b_main``), and compare against the
SIGNED on-disk artifacts in ``data/2021a_ssh_mapping_ose/ours/``.  Two-level
gating: skipped when the artifacts are absent, AND opt-in via
``SVERDRUP_PHASE8_EXTERNAL=1`` (the reconstruction is a full-obs m=100 member
solve — minutes to tens of minutes).
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest

from sverdrup.application.calibration.constants import S_STAR
from sverdrup.core.grid import GridSpec
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
from sverdrup.core.parameters import ConstantProvider
from sverdrup.distributions.calibration import (
    ClipSpec,
    PolyCalibration,
    ScalarCalibration,
)
from sverdrup.distributions.miost_ensemble import MiostEnsembleDistribution
from sverdrup.methods.miost import Miost
from sverdrup.methods.miost_windows import WindowPlan

# ---------------------------------------------------------------------------
# Shared fixture (same pattern as test_calibration_field.py seam section)
# ---------------------------------------------------------------------------

_M = 6
_DAY = 50.0  # inside the [45, 60] blend zone of the two-window plan
_ROOT = 12345
_PARAMS = ConstantProvider(
    {"spacing_alpha": 1.5, "log10_rho": 1.3, "q_slope": 2.0, "l_t_days": 10.0}
)
_GRID = GridSpec.lonlat(np.linspace(296.0, 304.0, 7), np.linspace(34.0, 42.0, 7))

# A clip wide enough that no positive s value in this test ever engages it.
_WIDE = ClipSpec(lo_log_s=-100.0, hi_log_s=100.0)

_ARTIFACTS = Path("data/2021a_ssh_mapping_ose/ours")
_VAR_MAPS = _ARTIFACTS / "stage_b_var_maps.nc"
_MEAN_MAPS = _ARTIFACTS / "stage_b_mean_maps.nc"
_ACCEPTANCE = _ARTIFACTS / "stage_miost_acceptance.nc"


def _obs(n: int = 80) -> ObsWindow:
    rng = np.random.default_rng(7)
    t = rng.uniform(-12.0, 117.0, n)
    err = DiagonalErrorModel(np.full(n, 0.01))
    mission = np.asarray(["alg", "s3a", "h2g", "j2n"])[rng.integers(0, 4, n)]
    return ObsWindow.from_arrays(
        rng.uniform(296, 304, n),
        rng.uniform(34, 42, n),
        t,
        rng.standard_normal(n) * 0.1,
        err,
        mission,
    )


def _method() -> Miost:
    return Miost(plan=WindowPlan(starts=(0.0, 45.0)))


@pytest.fixture(scope="module")
def raw_dist() -> MiostEnsembleDistribution:
    """Uncalibrated (ScalarCalibration(1.0)) distribution on the small fixture."""
    return _method().sample_members(_obs(), _GRID, _PARAMS, _DAY, m=_M, root=_ROOT)


@pytest.fixture(scope="module")
def star_dist(raw_dist: MiostEnsembleDistribution) -> MiostEnsembleDistribution:
    """Distribution calibrated with the shipped scalar s*."""
    return raw_dist.with_calibration(ScalarCalibration(S_STAR))


# ---------------------------------------------------------------------------
# Criterion 1a — grid marginal_variance (S-path) scales by S_STAR
# ---------------------------------------------------------------------------


def test_identity_grid_marginal_variance(
    raw_dist: MiostEnsembleDistribution,
    star_dist: MiostEnsembleDistribution,
) -> None:
    """marginal_variance() with ScalarCalibration(S_STAR) == S_STAR × raw, rtol 1e-12.

    Bug caught: wrong power of s in the S-path (s², √s, 1) — the grid sparse
    path could double-apply or miss the sqrt_s factor.  This is identity (ii)
    on the S-path.
    """
    v_raw = np.asarray(raw_dist.marginal_variance())
    v_star = np.asarray(star_dist.marginal_variance())
    np.testing.assert_allclose(v_star, S_STAR * v_raw, rtol=1e-12)


# ---------------------------------------------------------------------------
# Criterion 1b — arbitrary-point covariance diagonal (Γ) scales by S_STAR
# ---------------------------------------------------------------------------


def test_identity_covariance_diagonal_arb_points(
    raw_dist: MiostEnsembleDistribution,
    star_dist: MiostEnsembleDistribution,
) -> None:
    """Diagonal of covariance(pts, pts) with ScalarCalibration(S_STAR) == S_STAR × raw.

    Points are track-like off-grid positions; queries route through the dense
    _anoms_at path.  Bug caught: sqrt_s applied once to only one side of the
    covariance (one-sided scaling would give factor S_STAR, not S_STAR for the
    diagonal — but the correlation test is blind to this, so we pin the
    magnitude here per spec §2 identity (ii)).
    """
    pts = np.array(
        [
            [297.3, 35.7, _DAY],
            [300.1, 38.9, _DAY],
            [302.8, 41.3, _DAY],
            [298.5, 37.2, _DAY],
        ]
    )
    c_raw = np.asarray(raw_dist.covariance(pts, pts))
    c_star = np.asarray(star_dist.covariance(pts, pts))
    np.testing.assert_allclose(np.diag(c_star), S_STAR * np.diag(c_raw), rtol=1e-12)


# ---------------------------------------------------------------------------
# Criterion 1c — full cross-point covariance block scales by S_STAR
# ---------------------------------------------------------------------------


def test_identity_covariance_full_block(
    raw_dist: MiostEnsembleDistribution,
    star_dist: MiostEnsembleDistribution,
) -> None:
    """Full covariance(a, b) block with ScalarCalibration(S_STAR) == S_STAR × raw.

    Uses two distinct point sets (a ≠ b) so the off-diagonal entries are also
    checked.  Bug caught: sqrt_s applied to only one of the two anomaly
    matrices (the block would scale by √S_STAR instead of S_STAR — invisible
    to a correlation test but wrong by a factor of √S_STAR on every off-diagonal
    entry).
    """
    a = np.array([[297.0, 35.0, _DAY], [301.0, 39.0, _DAY], [303.5, 41.5, _DAY]])
    b = np.array([[299.0, 37.0, _DAY], [302.0, 40.0, _DAY]])
    c_raw = np.asarray(raw_dist.covariance(a, b))
    c_star = np.asarray(star_dist.covariance(a, b))
    np.testing.assert_allclose(c_star, S_STAR * c_raw, rtol=1e-12)


# ---------------------------------------------------------------------------
# Criterion 1d — sample() moment ratio
# ---------------------------------------------------------------------------


def test_identity_sample_variance_ratio(
    raw_dist: MiostEnsembleDistribution,
    star_dist: MiostEnsembleDistribution,
) -> None:
    """sample() with fixed seed: calibrated sample variance / raw sample variance == S_STAR.

    Both distributions draw the SAME member indices (identical without-replacement
    subselection at seed=99) and the calibrated member fields are sqrt(S_STAR) times
    the raw anomalies about the same mean, so the sample variance ratio is exactly
    S_STAR at rtol 1e-12 (same underlying draws, same arithmetic, only the sqrt_s
    factor differs).

    Bug caught: sample() ignoring the calibration (returning raw fields regardless)
    — the ratio would be 1.0 instead of S_STAR.  Also catches a wrong power of s
    in the to_grid_ensemble path (s², √s, 1 would give ratios S_STAR², √S_STAR, 1).
    """
    seed = 99
    k = _M  # draw all members so variance is well-defined
    s_raw = np.asarray(raw_dist.sample(k, seed=seed))  # (k, ny, nx)
    s_star = np.asarray(star_dist.sample(k, seed=seed))

    # Per-node sample variance (ddof=1) over the k drawn members.
    var_raw = np.var(s_raw, axis=0, ddof=1)
    var_star = np.var(s_star, axis=0, ddof=1)

    # Nodes where raw variance is effectively zero should also be zero calibrated.
    nonzero = var_raw > 1e-30
    np.testing.assert_allclose(
        var_star[nonzero] / var_raw[nonzero],
        S_STAR,
        rtol=1e-12,
        err_msg="Calibrated sample variance does not equal S_STAR × raw",
    )


# ---------------------------------------------------------------------------
# External: day-0 shipped-product reconstruction vs the SIGNED artifacts
# ---------------------------------------------------------------------------

_SCOPE = Path("tests/validation/fixtures/stage_a_scope.json")
_EXTERNAL_ENV = "SVERDRUP_PHASE8_EXTERNAL"

_external_optin = pytest.mark.skipif(
    os.environ.get(_EXTERNAL_ENV) != "1",
    reason=(
        "opt-in: requires a full-obs member solve (m=100) at the accepted "
        f"Stage-B config, ~minutes-tens-of-minutes; set {_EXTERNAL_ENV}=1"
    ),
)


@pytest.fixture(scope="module")
def day0_shipped() -> tuple[MiostEnsembleDistribution, np.ndarray, GridSpec]:
    """Day-0 shipped-config reconstruction via the Stage-B runner's exact recipe.

    Mirrors ``scripts/stage_miost_gate_run.py::stage_b_main``: load the six
    mapping missions (``load_mapping_obs``), apply the production halo cut
    (``halo_obs`` at ``HALO_DEG``), split by mission (c2 locked, j3
    validation), train subset (``_subset``), then solve at the SIGNED winner
    params through ``shipped_miost()`` (m=100, STAGE_B_ROOT, factory
    ScalarCalibration(s*), default PCG budget rtol 1e-6 / maxiter 500 — the
    exact budget the gate converged at, per the gate evidence JSON).

    Day 0 (2017-01-01) is covered by exactly ONE window (w-18: [-18, 42]) and
    ``sample_members`` solves only covering windows with identity-keyed CRN,
    so this reproduces the gate's w-18 member batch without solving the year.

    Returns:
        (shipped ensemble distribution at day 0, gridded MDT, output grid).
    """
    import json

    import xarray as xr

    from sverdrup.application.splits import make_splits
    from sverdrup.application.tuning.stage_a import _subset
    from sverdrup.methods.miost import shipped_miost
    from sverdrup.methods.miost_basis import HALO_DEG
    from sverdrup.validation.input_adapter import load_mapping_obs, load_mdt_grid
    from sverdrup.validation.params import baseline_config
    from sverdrup.validation.run import halo_obs

    cfg = json.loads(_SCOPE.read_text())
    with xr.open_dataset(_ACCEPTANCE) as ds:
        if "winner_params" not in ds.attrs:
            pytest.skip(
                "acceptance map lacks the winner_params provenance attr; "
                "cannot reconstruct at the signed winner."
            )
        winner = json.loads(str(ds.attrs["winner_params"]))
        t0 = np.asarray(ds.time.values)[0]
    assert t0 == np.datetime64("2017-01-01"), f"unexpected first map day {t0!r}"

    provider, grid, _ = baseline_config()
    obs = load_mapping_obs([Path(p) for p in cfg["mapping_obs_paths"]], provider)
    obs = halo_obs(obs, grid, HALO_DEG)
    split = make_splits(
        obs,
        by="mission",
        locked_missions=["c2"],
        validation_missions=[str(cfg["validation_mission"])],
    )
    train = _subset(obs, split.train_idx)

    dist = shipped_miost().solve(train, grid, ConstantProvider(winner), 0.0)
    assert isinstance(dist, MiostEnsembleDistribution)
    mdt = load_mdt_grid([Path(p) for p in cfg["mdt_paths"]], grid)
    return dist, np.asarray(mdt), grid


@pytest.mark.external
@_external_optin
@pytest.mark.skipif(
    not (_VAR_MAPS.exists() and _ACCEPTANCE.exists() and _SCOPE.exists()),
    reason=(
        f"Signed Stage-B artifacts absent ({_VAR_MAPS} / {_ACCEPTANCE} / "
        f"{_SCOPE}); run with the challenge data present for the regression."
    ),
)
def test_external_var_maps_pin_s_star_identity(
    day0_shipped: tuple[MiostEnsembleDistribution, np.ndarray, GridSpec],
) -> None:
    """Shipped-config variance vs the SIGNED var maps at day 0 (rtol 1e-9).

    ARTIFACT SEMANTICS (verified against the producing code,
    ``stage_b_main``: ``var_stack = std_fields(raw anoms)**2``, and the gate
    evidence JSON: ``validation_calibration.reduced_chi2 == 1.0`` at
    ``s = s*`` applied ON TOP of these maps): the on-disk var maps are the
    RAW member variance — s* was DERIVED from them, not baked into them.
    The plan text's "written AT s*" describes the shipped SIGMA semantics,
    not the artifact bytes.  Therefore the pins are:

    - raw (calibration-1.0) variance == signed maps      (identity of the
      reconstruction: same solver, seeds, budget — rtol 1e-9)
    - factory (s*) marginal_variance == S_STAR × signed  (identity (ii)
      against the SIGNED artifact — rtol 1e-9)

    Bug caught: legacy-load inversion shipping ~3.2x under-dispersed sigma
    (a raw-vs-calibrated sign flip would yield signed/s* instead of
    S_STAR × signed — a factor-101 error, unmissable); the factory
    ScalarCalibration(s*) silently dropped at solve() time (ratio 1.0, not
    S_STAR); or any wrong power of s on the grid S-path.
    """
    import xarray as xr

    dist, _, _ = day0_shipped
    with xr.open_dataset(_VAR_MAPS) as ds:
        signed = np.asarray(ds["ssh"].isel(time=0).values)  # (lat, lon), RAW

    v_raw = np.asarray(
        dist.with_calibration(ScalarCalibration(1.0)).marginal_variance()
    )
    v_factory = np.asarray(dist.marginal_variance())

    np.testing.assert_allclose(
        v_raw,
        signed,
        rtol=1e-9,
        err_msg=(
            "Raw reconstruction variance does not match the signed var maps — "
            "the reconstruction (obs cut / seeds / budget) deviates from the "
            "gate run."
        ),
    )
    np.testing.assert_allclose(
        v_factory,
        S_STAR * signed,
        rtol=1e-9,
        err_msg=(
            "Factory marginal_variance != S_STAR × signed var maps — the "
            "factory ScalarCalibration(s*) was dropped or a wrong power of s "
            "is applied on the S-path."
        ),
    )


# ---------------------------------------------------------------------------
# Criterion 3 — mean-unchanged under ScalarCalibration(S_STAR), small fixture
# ---------------------------------------------------------------------------


def test_mean_unchanged_scalar_star_small_fixture(
    raw_dist: MiostEnsembleDistribution,
    star_dist: MiostEnsembleDistribution,
) -> None:
    """mean_at under ScalarCalibration(S_STAR) is BIT-IDENTICAL to uncalibrated.

    Checks arbitrary off-grid points (not the grid nodes), so the dense
    mean_at path is exercised.

    Bug caught: mean contamination — any code path that accidentally routes
    the mean through the √s scaling would produce a wrong mean after
    calibration and corrupt every downstream forecast.
    """
    pts = np.array(
        [
            [297.5, 35.5, _DAY],
            [300.0, 38.0, _DAY],
            [303.0, 41.0, _DAY],
            [298.8, 36.9, _DAY],
            [301.7, 39.6, _DAY],
        ]
    )
    m_raw = np.asarray(raw_dist.mean_at(pts))
    m_star = np.asarray(star_dist.mean_at(pts))
    assert np.array_equal(m_raw, m_star), (
        "mean_at is NOT bit-identical after ScalarCalibration(S_STAR); "
        "max abs diff = "
        f"{np.max(np.abs(m_raw - m_star)):.3e}"
    )


# ---------------------------------------------------------------------------
# Criterion 3 (extended) — mean-unchanged under a NON-CONSTANT field
# ---------------------------------------------------------------------------


def test_mean_unchanged_nonconstant_field_small_fixture(
    raw_dist: MiostEnsembleDistribution,
) -> None:
    """mean_at is BIT-IDENTICAL under a non-constant PolyCalibration field.

    A spatially-varying field is used to ensure the test catches contamination
    that might accidentally cancel for a uniform scaling.

    Bug caught: √s(x) accidentally applied to the mean term in mean_at or
    in to_grid_ensemble — would produce a spatially-varying mean shift
    proportional to the field, invisible in the scalar test.
    """
    field = PolyCalibration(coeffs=(0.5, 0.8, 0.0, 0.3, 0.0), clip=_WIDE, fit_id="t5")
    pts = np.array(
        [
            [297.0, 35.0, _DAY],
            [301.0, 39.0, _DAY],
            [303.5, 41.5, _DAY],
            [299.0, 37.5, _DAY],
        ]
    )
    m0 = np.asarray(raw_dist.mean_at(pts))
    m1 = np.asarray(raw_dist.with_calibration(field).mean_at(pts))
    assert np.array_equal(m0, m1), (
        "mean_at is NOT bit-identical after PolyCalibration; "
        f"max abs diff = {np.max(np.abs(m0 - m1)):.3e}"
    )

    # Grid mean nodes too (uses the S-path via to_grid_ensemble).
    lon2d, lat2d = np.meshgrid(raw_dist.grid.x, raw_dist.grid.y)
    day_arr = np.full(lon2d.size, _DAY)
    gpts = np.column_stack([lon2d.ravel(), lat2d.ravel(), day_arr])
    gm0 = np.asarray(raw_dist.mean_at(gpts))
    gm1 = np.asarray(raw_dist.with_calibration(field).mean_at(gpts))
    assert np.array_equal(gm0, gm1), (
        "Grid mean_at is NOT bit-identical after PolyCalibration; "
        f"max abs diff = {np.max(np.abs(gm0 - gm1)):.3e}"
    )


# ---------------------------------------------------------------------------
# Criterion 3 (external) — mean-unchanged vs signed acceptance map
# ---------------------------------------------------------------------------


@pytest.mark.external
@_external_optin
@pytest.mark.skipif(
    not (_ACCEPTANCE.exists() and _SCOPE.exists()),
    reason=(
        f"Signed acceptance map absent ({_ACCEPTANCE} / {_SCOPE}); run with "
        "the challenge data present for the regression."
    ),
)
def test_external_mean_unchanged_vs_acceptance_map(
    day0_shipped: tuple[MiostEnsembleDistribution, np.ndarray, GridSpec],
) -> None:
    """Shipped-config mean map at day 0 == the signed acceptance map, BITWISE.

    The regenerated acceptance map (``stage_miost_acceptance.nc``, provenance
    attrs) holds the TRUE Stage-A SSH mean (SLA mean + MDT) at the signed
    winner; the gate proved the Stage-B mean maps bit-identical to it
    (``acceptance_map_bit_identical: true`` in the gate evidence JSON).  The
    shipped ensemble's mean (+ the same gridded MDT) must reproduce it
    bit-identically, both as shipped (factory ScalarCalibration(s*)) and
    under a NON-CONSTANT field calibration.

    Bug caught: mean contamination by the Task-3 eval-time √s seam — any
    spurious routing of eta^a through the √s multiplication (scalar OR
    spatially-varying) would shift the mean vs the signed map.
    """
    import xarray as xr

    dist, mdt, _ = day0_shipped
    with xr.open_dataset(_ACCEPTANCE) as ds:
        expected = np.asarray(ds["ssh"].isel(time=0).values)  # (lat, lon)

    # As shipped (factory scalar-s* calibration riding the anomaly layer).
    got = np.asarray(dist.mean) + mdt
    assert np.array_equal(got, expected), (
        "Shipped mean map does NOT bit-match the signed acceptance map; "
        f"max abs diff = {np.max(np.abs(got - expected)):.3e}.  Possible "
        "cause: mean path contaminated by the Task-3 sqrt_s seam."
    )

    # Under a NON-constant field: the mean array must be the SAME bytes.
    field = PolyCalibration(coeffs=(0.5, 0.8, 0.0, 0.3, 0.0), clip=_WIDE, fit_id="t5")
    got_field = np.asarray(dist.with_calibration(field).mean) + mdt
    assert np.array_equal(got_field, expected), (
        "Field-calibrated mean map deviates from the signed acceptance map; "
        f"max abs diff = {np.max(np.abs(got_field - expected)):.3e}."
    )
