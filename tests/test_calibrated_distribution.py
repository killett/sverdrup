"""Tests for CalibratedDistribution — capability-aware generic calibration wrapper.

All tests follow the test-design skill: each docstring names the behaviour under
test AND a concrete bug that would make the test fail.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np
import pytest

from sverdrup.core.distribution import CapabilityNotAvailableError
from sverdrup.core.grid import GridSpec
from sverdrup.core.provenance import (
    TransformKind,
    UncertaintyProvenance,
)
from sverdrup.core.types import UncertaintyCapability as UC
from sverdrup.distributions.calibration import (
    CalibratedDistribution,
    ClipSpec,
    PolyCalibration,
    ScalarCalibration,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_WIDE = ClipSpec(lo_log_s=-10.0, hi_log_s=10.0)


def _prov_empty() -> UncertaintyProvenance:
    return UncertaintyProvenance(
        native_capability=UC.SAMPLES,
        transformations=[],
    )


def _grid_3x4() -> GridSpec:
    """3-lon × 4-lat lonlat grid inside the calibration box."""
    return GridSpec.lonlat(
        lons=np.array([297.0, 300.0, 303.0]),
        lats=np.array([34.0, 37.0, 40.0, 43.0]),
    )


# ---------------------------------------------------------------------------
# Stub underlying — SAMPLES-capable
# ---------------------------------------------------------------------------


@dataclass
class _StubGaussian:
    """Minimal SAMPLES-capable stand-in mirroring gaussian.py's surface."""

    grid: GridSpec
    mean: np.ndarray
    time_days: float = 0.0
    provenance: UncertaintyProvenance = field(default_factory=_prov_empty)

    def marginal_variance(self) -> np.ndarray:
        """Return uniform variance 2.0 everywhere."""
        return np.full(self.mean.shape, 2.0)

    def covariance(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Return uniform 0.5 cross-covariance."""
        return np.full((len(a), len(b)), 0.5)

    def sample(self, m: int, seed: int) -> np.ndarray:
        """Return draws: mean + standard_normal."""
        rng = np.random.default_rng(seed)
        return self.mean[None] + rng.standard_normal((m, *self.mean.shape))

    def regrid(self, target: GridSpec) -> _StubGaussian:
        """Return a regridded stub."""
        return replace(self, grid=target)

    def secret_marker(self) -> str:
        """Must NOT be accessible on the wrapper (PIN A leak test)."""
        return "MUST NOT LEAK"


# ---------------------------------------------------------------------------
# Stub underlying — MARGINAL_VARIANCE-only (no covariance/sample)
# ---------------------------------------------------------------------------


@dataclass
class _StubMarginalOnly:
    """Variance-only underlying; covariance/sample raise as required."""

    grid: GridSpec
    mean: np.ndarray
    time_days: float = 0.0
    provenance: UncertaintyProvenance = field(default_factory=_prov_empty)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "provenance",
            UncertaintyProvenance(
                native_capability=UC.MARGINAL_VARIANCE,
                transformations=[],
            ),
        )

    def marginal_variance(self) -> np.ndarray:
        """Return uniform variance 3.0."""
        return np.full(self.mean.shape, 3.0)

    def covariance(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Raise — this capability is unavailable."""
        raise CapabilityNotAvailableError("stub: no covariance")

    def sample(self, m: int, seed: int) -> np.ndarray:
        """Raise — this capability is unavailable."""
        raise CapabilityNotAvailableError("stub: no sample")

    def regrid(self, target: GridSpec) -> _StubMarginalOnly:
        """Return a regridded stub."""
        return replace(self, grid=target)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def grid() -> GridSpec:
    """3 × 4 lonlat grid inside the calibration box."""
    return _grid_3x4()


@pytest.fixture()
def scalar_field() -> ScalarCalibration:
    """Uniform scale factor s = 4.0."""
    return ScalarCalibration(s=4.0)


@pytest.fixture()
def poly_field() -> PolyCalibration:
    """Spatially-varying PolyCalibration with analytically predictable values."""
    # log s = 1.0 everywhere (a0=1, rest 0) → s = e, sqrt_s = exp(0.5)
    return PolyCalibration(
        coeffs=(1.0, 0.0, 0.0, 0.0, 0.0),
        clip=_WIDE,
        fit_id="test-const-1",
    )


@pytest.fixture()
def stub(grid: GridSpec) -> _StubGaussian:
    """SAMPLES-capable stub on the 3×4 grid."""
    mean = np.arange(12, dtype=float).reshape(4, 3)
    return _StubGaussian(grid=grid, mean=mean)


# ===========================================================================
# 1 — Capability-table: POINT raises at construction
# ===========================================================================


def test_point_capability_raises_at_construction(grid: GridSpec) -> None:
    """Construction with POINT capability raises CapabilityNotAvailableError.

    Bug caught: wrapper allows POINT underlyings and silently produces
    a distribution that cannot provide any uncertainty output.
    """
    mean = np.zeros((4, 3))
    underlying = _StubGaussian(grid=grid, mean=mean)
    with pytest.raises(CapabilityNotAvailableError):
        CalibratedDistribution(underlying, ScalarCalibration(1.0), UC.POINT)


# ===========================================================================
# 2 — Capability-table: MARGINAL_VARIANCE wrapper raises on covariance/sample
# ===========================================================================


def test_marginal_variance_capability_covariance_raises(grid: GridSpec) -> None:
    """MARGINAL_VARIANCE wrapper delegates covariance raise from underlying.

    Bug caught: wrapper ignores capability and provides covariance by itself
    rather than letting the underlying's raise propagate.
    """
    mean = np.zeros((4, 3))
    underlying = _StubMarginalOnly(grid=grid, mean=mean)
    wrapped = CalibratedDistribution(
        underlying, ScalarCalibration(2.0), UC.MARGINAL_VARIANCE
    )
    pts = np.array([[297.0, 34.0, 0.0], [300.0, 37.0, 0.0]])
    with pytest.raises(CapabilityNotAvailableError):
        wrapped.covariance(pts, pts)


def test_marginal_variance_capability_sample_raises(grid: GridSpec) -> None:
    """MARGINAL_VARIANCE wrapper delegates sample raise from underlying.

    Bug caught: wrapper ignores capability and generates samples itself
    despite having no valid underlying sample method.
    """
    mean = np.zeros((4, 3))
    underlying = _StubMarginalOnly(grid=grid, mean=mean)
    wrapped = CalibratedDistribution(
        underlying, ScalarCalibration(2.0), UC.MARGINAL_VARIANCE
    )
    with pytest.raises(CapabilityNotAvailableError):
        wrapped.sample(3, 0)


# ===========================================================================
# 3 — marginal_variance = s(x) · v(x) pointwise
# ===========================================================================


def test_marginal_variance_scales_pointwise(
    stub: _StubGaussian, poly_field: PolyCalibration
) -> None:
    """marginal_variance returns s(x)·v(x) pointwise.

    Bug caught: wrapper uses a scalar s instead of the spatially-varying
    field, or applies sqrt(s) instead of s.
    """
    wrapped = CalibratedDistribution(stub, poly_field, UC.SAMPLES)
    mv = wrapped.marginal_variance()

    # Compute expected: s(x) = exp(log_s_at) for every grid node
    lon2d, lat2d = np.meshgrid(stub.grid.x, stub.grid.y)  # (ny, nx)
    s_field = np.exp(poly_field.log_s_at(lon2d, lat2d))
    expected = s_field * stub.marginal_variance()

    np.testing.assert_allclose(mv, expected, rtol=1e-12)


# ===========================================================================
# 4 — covariance = sqrt_s(a)[:,None] * C * sqrt_s(b)[None,:]
# ===========================================================================


def test_covariance_outer_scaled(
    stub: _StubGaussian, poly_field: PolyCalibration
) -> None:
    """covariance is sqrt_s(a)[:,None] * C_raw * sqrt_s(b)[None,:].

    Bug caught: wrapper applies s instead of sqrt(s), or applies the same
    s value to both rows and columns without using the per-point coords.
    """
    wrapped = CalibratedDistribution(stub, poly_field, UC.SAMPLES)
    pts_a = np.array([[297.0, 34.0, 0.0], [300.0, 37.0, 0.0]])
    pts_b = np.array([[303.0, 40.0, 0.0]])

    cov = wrapped.covariance(pts_a, pts_b)

    sqrt_s_a = poly_field.sqrt_s_at(pts_a[:, 0], pts_a[:, 1])  # (2,)
    sqrt_s_b = poly_field.sqrt_s_at(pts_b[:, 0], pts_b[:, 1])  # (1,)
    raw_cov = stub.covariance(pts_a, pts_b)  # (2,1) = 0.5
    expected = sqrt_s_a[:, None] * raw_cov * sqrt_s_b[None, :]

    np.testing.assert_allclose(cov, expected, rtol=1e-12)


# ===========================================================================
# 5 — sample: same seed ⇒ draws − mean scale by √s exactly
# ===========================================================================


def test_sample_scaled_anomalies(
    stub: _StubGaussian, poly_field: PolyCalibration
) -> None:
    """sample returns mean + sqrt_s(x) * (raw_draw - mean).

    Bug caught: wrapper returns raw draws unscaled, or applies the full
    scalar s rather than sqrt(s) per location.
    """
    seed = 42
    wrapped = CalibratedDistribution(stub, poly_field, UC.SAMPLES)

    draws = wrapped.sample(5, seed)

    # Re-draw with same seed from stub to get the raw anomalies
    raw = stub.sample(5, seed)  # (5, 4, 3) = mean + standard_normal
    anoms = raw - stub.mean[None]  # (5, 4, 3)

    lon2d, lat2d = np.meshgrid(stub.grid.x, stub.grid.y)
    sqrt_s = poly_field.sqrt_s_at(lon2d, lat2d)  # (4, 3)

    expected = stub.mean[None] + sqrt_s[None] * anoms

    np.testing.assert_allclose(draws, expected, rtol=1e-12)


# ===========================================================================
# 6 — mean routes bitwise
# ===========================================================================


def test_mean_routes_bitwise(
    stub: _StubGaussian,
    poly_field: PolyCalibration,
) -> None:
    """mean attribute is the SAME object as the underlying's mean (bitwise identity).

    Bug caught: wrapper returns a copy or applies sqrt_s to mean, breaking
    the PIN-B bit-identity guarantee.
    """
    wrapped = CalibratedDistribution(stub, poly_field, UC.SAMPLES)
    assert wrapped.mean is stub.mean


# ===========================================================================
# 7 — PIN A: no __getattr__ leak
# ===========================================================================


def test_no_getattr_leak(stub: _StubGaussian, scalar_field: ScalarCalibration) -> None:
    """secret_marker on underlying is NOT accessible on the wrapper (PIN A).

    Bug caught: wrapper has __getattr__ passthrough that exposes all
    underlying attributes, violating the enumerated-surface contract.
    """
    wrapped = CalibratedDistribution(stub, scalar_field, UC.SAMPLES)
    assert hasattr(stub, "secret_marker"), "stub must have secret_marker for this test"
    assert not hasattr(wrapped, "secret_marker")
    with pytest.raises(AttributeError):
        _ = wrapped.secret_marker  # type: ignore[attr-defined]


# ===========================================================================
# 8 — forwarded route raises when underlying lacks the attribute
# ===========================================================================


def test_member_at_raises_when_underlying_lacks_it(
    stub: _StubGaussian, scalar_field: ScalarCalibration
) -> None:
    """member_at raises CapabilityNotAvailableError when underlying has no member_at.

    Bug caught: wrapper silently raises AttributeError or returns garbage
    instead of the required CapabilityNotAvailableError.
    """
    wrapped = CalibratedDistribution(stub, scalar_field, UC.SAMPLES)
    # _StubGaussian has no member_at → should raise
    pts = np.array([[297.0, 34.0, 0.0]])
    with pytest.raises(
        CapabilityNotAvailableError, match="underlying does not provide"
    ):
        wrapped.member_at(0, pts)


def test_member_at_scales_about_mean(
    grid: GridSpec, poly_field: PolyCalibration
) -> None:
    """member_at returns mean + √s(x)·(member − mean) at the query points.

    Bug caught: wrapper delegates member_at raw (uncalibrated member leaks
    through the forwarded route), or scales the member INCLUDING its mean.
    """

    @dataclass
    class _StubWithMembers(_StubGaussian):
        def mean_at(self, pts: np.ndarray) -> np.ndarray:
            return np.full(len(pts), 3.0)

        def member_at(self, member_idx: int, pts: np.ndarray) -> np.ndarray:
            return np.full(len(pts), 3.0) + (member_idx + 1.0)

    stub = _StubWithMembers(grid=grid, mean=np.zeros((4, 3)))
    wrapped = CalibratedDistribution(stub, poly_field, UC.SAMPLES)
    pts = np.array([[297.0, 34.0, 0.0], [303.0, 40.0, 0.0]])

    got = wrapped.member_at(1, pts)

    sqrt_s = poly_field.sqrt_s_at(pts[:, 0], pts[:, 1])
    # member anomaly is exactly 2.0 (member_idx 1) about the mean 3.0
    expected = 3.0 + sqrt_s * 2.0
    np.testing.assert_allclose(got, expected, rtol=1e-12)


def test_to_grid_ensemble_rebuilds_stack_about_its_mean(
    grid: GridSpec, poly_field: PolyCalibration
) -> None:
    """to_grid_ensemble rebuilds the returned stack: mean + √s(x)·(members − mean).

    PIN A: "rebuild the returned stack about its mean with grid-node √s".

    Bug caught: wrapper delegates to_grid_ensemble raw — after the Task-3
    migration (raw class stops scaling internally) the ensemble route would
    silently return UNCALIBRATED samples.
    """

    @dataclass
    class _Ens:
        grid: GridSpec
        samples: np.ndarray
        provenance: UncertaintyProvenance
        time_days: float

    @dataclass
    class _StubWithEnsemble(_StubGaussian):
        def to_grid_ensemble(self, time_days: float) -> _Ens:
            rng = np.random.default_rng(7)
            samples = self.mean[None] + rng.standard_normal((6, *self.mean.shape))
            return _Ens(self.grid, samples, self.provenance, time_days)

    stub = _StubWithEnsemble(grid=grid, mean=np.arange(12, dtype=float).reshape(4, 3))
    wrapped = CalibratedDistribution(stub, poly_field, UC.SAMPLES)

    ens = wrapped.to_grid_ensemble(0.0)
    raw = stub.to_grid_ensemble(0.0)

    stack_mean = raw.samples.mean(axis=0)
    lon2d, lat2d = np.meshgrid(grid.x, grid.y)
    sqrt_s = poly_field.sqrt_s_at(lon2d, lat2d)
    expected = stack_mean[None] + sqrt_s[None] * (raw.samples - stack_mean[None])

    np.testing.assert_allclose(ens.samples, expected, rtol=1e-12)
    # The rebuilt ensemble carries the WRAPPER's (calibrated) provenance.
    assert ens.provenance is wrapped.provenance


def test_to_grid_ensemble_raises_when_underlying_lacks_it(
    stub: _StubGaussian, scalar_field: ScalarCalibration
) -> None:
    """to_grid_ensemble raises CapabilityNotAvailableError when underlying has no to_grid_ensemble.

    Bug caught: wrapper exposes to_grid_ensemble unconditionally and calls a
    missing method on the underlying, raising the wrong error type.
    """
    wrapped = CalibratedDistribution(stub, scalar_field, UC.SAMPLES)
    with pytest.raises(
        CapabilityNotAvailableError, match="underlying does not provide"
    ):
        wrapped.to_grid_ensemble(0.0)


# ===========================================================================
# 9 — regrid returns a new CalibratedDistribution carrying the SAME field
# ===========================================================================


def test_regrid_rewraps_with_same_field(
    stub: _StubGaussian, poly_field: PolyCalibration
) -> None:
    """regrid returns a CalibratedDistribution on target with the same calibration field.

    Bug caught: regrid returns the raw underlying's regrid result without
    re-wrapping it, exposing the unwrapped distribution to callers.
    """
    wrapped = CalibratedDistribution(stub, poly_field, UC.SAMPLES)
    target = GridSpec.lonlat(
        lons=np.array([298.0, 302.0]),
        lats=np.array([35.0, 39.0]),
    )
    rw = wrapped.regrid(target)

    assert isinstance(rw, CalibratedDistribution)
    assert rw.calibration is poly_field
    assert rw.grid is target


# ===========================================================================
# 10 — with_calibration: fresh wrapper, cache reset; composition × √(st)
# ===========================================================================


def test_rescaled_composes_multiplicatively(
    stub: _StubGaussian, scalar_field: ScalarCalibration
) -> None:
    """rescaled(s).rescaled(t) produces variance s·t × original.

    Bug caught: rescaled(t) replaces s rather than composing, or applies
    sqrt(s*t) twice instead of producing variance s·t × base.
    """
    wrapped = CalibratedDistribution(stub, scalar_field, UC.SAMPLES)  # s=4
    re1 = wrapped.rescaled(9.0)  # composed s = 4*9 = 36
    mv = re1.marginal_variance()
    base_mv = stub.marginal_variance()  # 2.0 everywhere
    # variance should be 36 × 2.0 = 72.0
    np.testing.assert_allclose(mv, base_mv * 36.0, rtol=1e-12)


def test_rescaled_raises_on_field_calibrated(
    stub: _StubGaussian, poly_field: PolyCalibration
) -> None:
    """rescaled raises ValueError on a field-calibrated instance.

    Bug caught: wrapper allows scalar rescale on a field-calibrated product,
    silently composing in an ambiguous way.
    """
    wrapped = CalibratedDistribution(stub, poly_field, UC.SAMPLES)
    with pytest.raises(ValueError):
        wrapped.rescaled(2.0)


def test_with_calibration_resets_cache(
    stub: _StubGaussian, scalar_field: ScalarCalibration
) -> None:
    """with_calibration returns a fresh wrapper with cleared per-grid √s cache.

    Bug caught: with_calibration returns the same instance or carries over
    the stale cached √s from the old field, producing wrong output for the
    new calibration field.
    """
    wrapped = CalibratedDistribution(stub, scalar_field, UC.SAMPLES)
    # Force cache population
    _ = wrapped.marginal_variance()

    new_field = ScalarCalibration(s=9.0)
    refreshed = wrapped.with_calibration(new_field)

    assert refreshed is not wrapped
    assert refreshed.calibration is new_field
    # Cache must NOT carry over the old s=4 computation
    mv = refreshed.marginal_variance()
    np.testing.assert_allclose(mv, stub.marginal_variance() * 9.0, rtol=1e-12)


# ===========================================================================
# 11 — no-stale-cache: marginal_variance from memoized cache is correct
# ===========================================================================


def test_no_stale_cache(stub: _StubGaussian, poly_field: PolyCalibration) -> None:
    """Per-grid √s cache returns correct result on repeated calls (no staleness).

    Bug caught: cache is keyed by grid identity but the field's per-grid
    computation is wrong on the second call (e.g. cache stores the raw
    array then mutates it).
    """
    wrapped = CalibratedDistribution(stub, poly_field, UC.SAMPLES)
    mv1 = wrapped.marginal_variance()
    mv2 = wrapped.marginal_variance()
    np.testing.assert_array_equal(mv1, mv2)
    # And the value is correct (not garbage from a stale key)
    lon2d, lat2d = np.meshgrid(stub.grid.x, stub.grid.y)
    expected = np.exp(poly_field.log_s_at(lon2d, lat2d)) * stub.marginal_variance()
    np.testing.assert_allclose(mv1, expected, rtol=1e-12)


# ===========================================================================
# 12 — Provenance: DIAGONAL_INFLATION for scalar, FIELD_INFLATION for fields
# ===========================================================================


def test_provenance_diagonal_inflation_for_scalar(
    stub: _StubGaussian, scalar_field: ScalarCalibration
) -> None:
    """CalibratedDistribution(scalar) appends DIAGONAL_INFLATION to provenance.

    Bug caught: wrapper does not record any provenance transform, or records
    FIELD_INFLATION for a scalar calibration (wrong kind).
    """
    wrapped = CalibratedDistribution(stub, scalar_field, UC.SAMPLES)
    transforms = wrapped.provenance.transformations
    assert len(transforms) == len(stub.provenance.transformations) + 1
    last = transforms[-1]
    assert last.kind is TransformKind.DIAGONAL_INFLATION
    assert last.params["s"] == scalar_field.s


def test_provenance_field_inflation_for_poly(
    stub: _StubGaussian, poly_field: PolyCalibration
) -> None:
    """CalibratedDistribution(poly) appends FIELD_INFLATION to provenance.

    Bug caught: wrapper records DIAGONAL_INFLATION for a field calibration,
    losing the spatial calibration metadata in the provenance chain.
    """
    wrapped = CalibratedDistribution(stub, poly_field, UC.SAMPLES)
    transforms = wrapped.provenance.transformations
    assert len(transforms) == len(stub.provenance.transformations) + 1
    last = transforms[-1]
    assert last.kind is TransformKind.FIELD_INFLATION
    assert last.params["calibration_key"] == poly_field.key()
    assert last.params["cal_kind"] == "poly"
    assert "dof" in last.params


# ===========================================================================
# 13 — save_state / load_state roundtrip including legacy rule
# ===========================================================================


def test_save_load_roundtrip(
    stub: _StubGaussian,
    poly_field: PolyCalibration,
    tmp_path: Path,
) -> None:
    """save_state/load_state roundtrip preserves calibration field exactly.

    Bug caught: load_state ignores cal_params and reloads scalar-1.0, or
    mean values are corrupted during the npz round-trip.
    """
    wrapped = CalibratedDistribution(stub, poly_field, UC.SAMPLES)
    path = tmp_path / "dist.npz"
    wrapped.save_state(path)
    loaded = CalibratedDistribution.load_state(path, stub)

    assert isinstance(loaded, CalibratedDistribution)
    assert loaded.calibration.key() == poly_field.key()
    np.testing.assert_array_equal(loaded.mean, stub.mean)


def test_load_state_legacy_rule_scalar_1(
    stub: _StubGaussian,
    tmp_path: Path,
) -> None:
    """load_state on file WITHOUT cal keys reloads with ScalarCalibration(1.0).

    Bug caught: legacy files missing cal_params cause load_state to crash
    rather than applying the identity calibration per spec.
    """
    # Save WITHOUT cal keys (simulate pre-calibration file)
    path = tmp_path / "legacy.npz"
    np.savez(path, mean=stub.mean)  # bare file with no cal keys

    loaded = CalibratedDistribution.load_state(path, stub)
    assert isinstance(loaded.calibration, ScalarCalibration)
    assert loaded.calibration.s == pytest.approx(1.0)


# ===========================================================================
# 14 — underlying.grid is required (PIN B)
# ===========================================================================


def test_requires_grid_attribute() -> None:
    """Constructor raises TypeError if underlying has no .grid attribute.

    Bug caught: wrapper proceeds without a grid and then crashes later
    with an opaque AttributeError deep in the scaling logic.
    """

    @dataclass
    class _NoGrid:
        mean: np.ndarray
        provenance: UncertaintyProvenance = field(default_factory=_prov_empty)

        def marginal_variance(self) -> np.ndarray:
            return np.ones(self.mean.shape)

        def covariance(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
            return np.zeros((len(a), len(b)))

        def sample(self, m: int, seed: int) -> np.ndarray:
            return np.zeros((m, *self.mean.shape))

    underlying = _NoGrid(mean=np.zeros((4, 3)))
    with pytest.raises(TypeError, match="grid"):
        CalibratedDistribution(underlying, ScalarCalibration(1.0), UC.SAMPLES)


# ===========================================================================
# PIN D — MIOST wrapper provenance-sequence equality
# ===========================================================================


def test_pin_d_miost_wrapper_provenance_sequence_matches_fixture() -> None:
    """PIN D: wrapper-built shipped product provenance transforms == pre-migration fixture.

    The fixture was captured at the PRE-Task-3 commit by
    scripts/capture_phase9_provenance_fixture.py. After migration the
    CalibratedDistribution wrapper must produce the exact same transform
    chain (kind names + sorted param key sets, same order) — proving no
    double-append or dropped append.

    Bug caught: raw class still appends a transform (double-append, extra
    transform), or wrapper forgets to append (missing transform), or the
    transform kinds are swapped — any of which would change the sequence
    from the pre-migration baseline.
    """
    import json
    from pathlib import Path

    from sverdrup.core.grid import GridSpec
    from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
    from sverdrup.core.parameters import ConstantProvider
    from sverdrup.distributions.calibration import ClipSpec, PolyCalibration
    from sverdrup.methods.miost import (
        PHASE8_CLIP_HI,
        PHASE8_CLIP_LO,
        PHASE8_FIT_ID,
        PHASE8_POLY_COEFFS,
        STAGE_B_ROOT,
        Miost,
    )
    from sverdrup.methods.miost_windows import WindowPlan

    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "fixtures"
        / "phase9_provenance_sequence.json"
    )
    expected = json.loads(fixture_path.read_text())

    # Same fixture config as test_phase8_identity_regression.py
    _M = 6
    _DAY = 50.0
    _PARAMS = ConstantProvider(
        {"spacing_alpha": 1.5, "log10_rho": 1.3, "q_slope": 2.0, "l_t_days": 10.0}
    )
    _GRID = GridSpec.lonlat(np.linspace(296.0, 304.0, 7), np.linspace(34.0, 42.0, 7))

    rng = np.random.default_rng(7)
    n = 80
    t = rng.uniform(-12.0, 117.0, n)
    err = DiagonalErrorModel(np.full(n, 0.01))
    mission = np.asarray(["alg", "s3a", "h2g", "j2n"])[rng.integers(0, 4, n)]
    obs = ObsWindow.from_arrays(
        rng.uniform(296, 304, n),
        rng.uniform(34, 42, n),
        t,
        rng.standard_normal(n) * 0.1,
        err,
        mission,
    )

    ship = Miost(
        plan=WindowPlan(starts=(0.0, 45.0)),
        members=_M,
        member_root=STAGE_B_ROOT,
        calibration=PolyCalibration(
            coeffs=PHASE8_POLY_COEFFS,
            clip=ClipSpec(lo_log_s=PHASE8_CLIP_LO, hi_log_s=PHASE8_CLIP_HI),
            fit_id=PHASE8_FIT_ID,
        ),
    )
    product = ship.solve(obs, _GRID, _PARAMS, _DAY)

    actual = [
        {"kind": tr.kind.name, "params_keys": sorted(tr.params.keys())}
        for tr in product.provenance.transformations
    ]
    assert actual == expected, (
        f"PIN D FAIL: provenance sequence mismatch.\n"
        f"  expected: {expected}\n"
        f"  actual:   {actual}\n"
        "This means the migration changed the number or order of "
        "transforms (double-append or missing append)."
    )
