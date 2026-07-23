"""Stage-B member generation + MiostEnsembleDistribution (plan Task 15, D6)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from sverdrup.core.grid import GridSpec
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
from sverdrup.core.parameters import ConstantProvider
from sverdrup.core.provenance import TransformKind
from sverdrup.core.types import UncertaintyCapability
from sverdrup.distributions.ensemble import EnsemblePredictiveDistribution
from sverdrup.distributions.miost_ensemble import MiostEnsembleDistribution
from sverdrup.methods.miost import Miost
from sverdrup.methods.miost_solver import MiostSolver
from sverdrup.methods.miost_windows import WindowPlan

M = 6
DAY = 50.0  # inside the [45, 60] blend zone of the two-window plan
ROOT = 12345
PARAMS = ConstantProvider(
    {"spacing_alpha": 1.5, "log10_rho": 1.3, "q_slope": 2.0, "l_t_days": 10.0}
)
GRID = GridSpec.lonlat(np.linspace(296.0, 304.0, 7), np.linspace(34.0, 42.0, 7))


def _obs(n: int = 80) -> ObsWindow:
    rng = np.random.default_rng(7)
    t = rng.uniform(-12.0, 117.0, n)  # spans both windows' +-L_t support
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
def dist() -> MiostEnsembleDistribution:
    # These tests pin the RAW coefficient-ensemble representation; Phase-9 §3
    # sample_members returns the CalibratedDistribution wrapper -> .underlying.
    raw = _method().sample_members(_obs(), GRID, PARAMS, DAY, m=M, root=ROOT).underlying
    assert isinstance(raw, MiostEnsembleDistribution)
    return raw


def test_one_batched_solve_per_window(monkeypatch: pytest.MonkeyPatch) -> None:
    """Members come from ONE (n, m) batched solve per window.

    Catches: a per-member solve loop — m separate PCG launches per window,
    the exact cost blow-up the batched-RHS design exists to avoid.
    """
    shapes: list[tuple[int, ...]] = []
    orig = MiostSolver.solve

    def spy(self: MiostSolver, b: np.ndarray, **kwargs: object) -> object:
        shapes.append(np.atleast_2d(np.asarray(b).T).T.shape)
        return orig(self, b, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(MiostSolver, "solve", spy)
    _method().sample_members(_obs(), GRID, PARAMS, DAY, m=M, root=ROOT)
    member_calls = [s for s in shapes if s[1] == M]
    single_calls = [s for s in shapes if s[1] == 1]
    assert len(member_calls) == 2  # one per covering window, exactly
    assert len(single_calls) == 2  # the unperturbed eta^a path, untouched
    assert len(shapes) == 4


def test_mean_is_unperturbed_eta_a(dist: MiostEnsembleDistribution) -> None:
    """Ensemble mean field == Miost.solve mean at identical params (D6).

    Catches: mean drifting to the MEMBER mean — Stage B must not touch the
    signed Stage-A mean.
    """
    point = _method().solve(_obs(), GRID, PARAMS, DAY)
    np.testing.assert_array_equal(np.asarray(dist.mean), np.asarray(point.mean))


def test_moments_member_mean_centered(dist: MiostEnsembleDistribution) -> None:
    """Variance is about the MEMBER MEAN with (m-1), matching np.var(ddof=1)
    of independently evaluated member fields.

    Catches: centering on eta^a (inflates variance by the member-mean offset,
    Steiner) or an m denominator.
    """
    fields = dist.to_grid_ensemble(DAY).samples.reshape(M, -1)
    expected = np.var(fields, axis=0, ddof=1).reshape(GRID.shape)
    np.testing.assert_allclose(dist.marginal_variance(), expected, rtol=1e-6)
    # Strict inequality vs eta^a-centered second moment on at least one node
    # (member mean != eta^a almost surely) proves the centering choice.
    mean_flat = np.asarray(dist.mean).ravel()
    about_eta = ((fields - mean_flat) ** 2).sum(axis=0) / (M - 1)
    assert (about_eta > expected.ravel()).any()


def test_covariance_matches_anomaly_outer(dist: MiostEnsembleDistribution) -> None:
    """covariance(a, b) == member-mean-centered anomaly outer product / (m-1).

    Catches: mismatched centering between marginal_variance and covariance,
    or transposed anomaly matrices.
    """
    a = np.array([[298.0, 36.0, DAY], [301.0, 40.0, DAY]])
    got = dist.covariance(a, a)
    fields = np.stack([dist.member_at(i, a) for i in range(M)])  # (M, 2)
    c = fields - fields.mean(axis=0)
    np.testing.assert_allclose(got, (c.T @ c) / (M - 1), rtol=1e-6)
    np.testing.assert_allclose(np.diag(got), np.var(fields, axis=0, ddof=1), rtol=1e-6)


def test_sample_contract(dist: MiostEnsembleDistribution) -> None:
    """sample(k<=m, seed) = deterministic without-replacement member subselect;
    sample(k>m) raises ValueError.

    Catches: with-replacement selection (duplicate members shrink spread),
    unseeded RNG, or silent truncation at k>m.
    """
    with pytest.raises(ValueError):
        dist.sample(M + 1, seed=0)
    s1 = dist.sample(3, seed=42)
    s2 = dist.sample(3, seed=42)
    np.testing.assert_array_equal(s1, s2)
    assert s1.shape == (3, *GRID.shape)
    member_fields = dist.to_grid_ensemble(DAY).samples
    for row in s1:  # every draw is an actual member field, no duplicates
        assert any(np.array_equal(row, mf) for mf in member_fields)
    flat = s1.reshape(3, -1)
    assert len({f.tobytes() for f in flat}) == 3


def test_provenance_m_and_mc_error(dist: MiostEnsembleDistribution) -> None:
    """Provenance carries m and MC error sqrt(2/(m-1)) on an
    INPUT_PERTURBATION transform over native SAMPLES.

    Catches: missing/incorrect MC-error formula (e.g. 1/sqrt(m)).
    """
    assert dist.provenance.native_capability is UncertaintyCapability.SAMPLES
    (tr,) = dist.provenance.transformations
    assert tr.kind is TransformKind.INPUT_PERTURBATION
    assert tr.params["m"] == M
    assert tr.params["mc_error"] == pytest.approx(np.sqrt(2.0 / (M - 1)))


def test_provenance_single_member_probe() -> None:
    """m=1 (probe/crossenv single-member solve) records mc_error None.

    Sample variance has m-1 dof: at m=1 the MC error is UNDEFINED, not a
    number — recording None is the honest value. Catches: the
    ZeroDivisionError that killed the phase-14 tile probe (sqrt(2/(m-1))
    evaluated unconditionally), and any future finite fake (e.g. 0.0,
    which would claim perfect MC precision from one member).
    """
    from sverdrup.distributions.miost_ensemble import ensemble_provenance

    (tr,) = ensemble_provenance(1).transformations
    assert tr.params["m"] == 1
    assert tr.params["mc_error"] is None
    with pytest.raises(ValueError, match="m must be >= 1"):
        ensemble_provenance(0)


def test_persistence_roundtrip_exact(
    dist: MiostEnsembleDistribution, tmp_path: Path
) -> None:
    """Default save/load round-trips moments exactly; kind tag present.

    Catches: silent f32 downcast in the default path, or reload rebuilding
    a different blend (wrong starts/w_days).
    """
    p = tmp_path / "ens.npz"
    dist.save_state(p)
    with np.load(p) as z:
        assert str(z["kind"]) == "miost-coeff-ensemble"
    back = MiostEnsembleDistribution.load_state(p)
    np.testing.assert_array_equal(np.asarray(back.mean), np.asarray(dist.mean))
    np.testing.assert_array_equal(back.marginal_variance(), dist.marginal_variance())


def test_persistence_f32_option(
    dist: MiostEnsembleDistribution, tmp_path: Path
) -> None:
    """anomalies_f32=True round-trips moments to f32 precision (rtol 1e-6).

    Catches: the compression option corrupting moments beyond precision loss
    (e.g. truncating eta^a too, which must stay f64).
    """
    p = tmp_path / "ens32.npz"
    dist.save_state(p, anomalies_f32=True)
    back = MiostEnsembleDistribution.load_state(p)
    np.testing.assert_array_equal(np.asarray(back.mean), np.asarray(dist.mean))
    np.testing.assert_allclose(
        back.marginal_variance(), dist.marginal_variance(), rtol=1e-5
    )


def test_load_rejects_wrong_kind(tmp_path: Path) -> None:
    """load_state refuses an npz without the ensemble kind tag.

    Catches: silently interpreting a POINT-state npz as an ensemble.
    """
    p = tmp_path / "point.npz"
    np.savez(p, kind="something-else")
    with pytest.raises(ValueError, match="miost-coeff-ensemble"):
        MiostEnsembleDistribution.load_state(p)


def test_to_grid_ensemble_type_and_moments(dist: MiostEnsembleDistribution) -> None:
    """Down-conversion returns the existing EnsemblePredictiveDistribution and
    node moments agree with coefficient-space values (rtol 1e-6).

    Catches: down-conversion evaluating a different blend than the
    coefficient-space queries.
    """
    ens = dist.to_grid_ensemble(DAY)
    assert isinstance(ens, EnsemblePredictiveDistribution)
    assert ens.samples.shape == (M, *GRID.shape)
    np.testing.assert_allclose(
        ens.marginal_variance(), dist.marginal_variance(), rtol=1e-6
    )


def test_crn_root_threading() -> None:
    """Same root -> bit-identical members; different root -> different.

    Catches: root not threaded into obs_noise/coef_noise (members would be
    irreproducible across sessions or shared across experiments).
    """
    a = _method().sample_members(_obs(), GRID, PARAMS, DAY, m=3, root=ROOT)
    b = _method().sample_members(_obs(), GRID, PARAMS, DAY, m=3, root=ROOT)
    c = _method().sample_members(_obs(), GRID, PARAMS, DAY, m=3, root=ROOT + 1)
    np.testing.assert_array_equal(
        a.to_grid_ensemble(DAY).samples, b.to_grid_ensemble(DAY).samples
    )
    assert not np.array_equal(
        a.to_grid_ensemble(DAY).samples, c.to_grid_ensemble(DAY).samples
    )


def test_member_batch_residuals_logged() -> None:
    """sample_members surfaces the member-batch solve report in CONVERGENCE_LOG.

    Catches: the batched member solve dropping its ConvergenceReport (a capped
    under-converged member batch would silently under-disperse sigma — the
    spec-6.5 failure class — with no telemetry for the acceptance record).
    """
    from sverdrup.methods.miost import CONVERGENCE_LOG

    CONVERGENCE_LOG.clear()
    _method().sample_members(_obs(), GRID, PARAMS, DAY, m=3, root=ROOT)
    batches = [e for e in CONVERGENCE_LOG if e.get("kind") == "member-batch"]
    plan = WindowPlan(starts=(0.0, 45.0))
    assert {e["window"] for e in batches} == {w.id for w in plan.windows}
    for e in batches:
        assert int(e["iterations"]) >= 1  # type: ignore[call-overload]
        res = float(e["final_rel_residual"])  # type: ignore[arg-type]
        assert np.isfinite(res) and 0.0 <= res < 1.0


def test_grid_queries_never_dense_evaluate(
    dist: MiostEnsembleDistribution, monkeypatch: pytest.MonkeyPatch
) -> None:
    """marginal_variance / to_grid_ensemble use the SPARSE S-path on grids.

    Catches: the OOM-#3 trap resurrected — dense BasisSpec.evaluate on a
    production grid is a ~8 GB/window gamma; grid-shaped queries must route
    through build_s_spatial + time_contract (arbitrary-POINT queries like
    mean_at/covariance may stay dense — track point sets are small).
    """
    from sverdrup.methods.miost_basis import BasisSpec

    def _boom(*a: object, **k: object) -> None:
        raise AssertionError("dense BasisSpec.evaluate called on a grid query")

    monkeypatch.setattr(BasisSpec, "evaluate", _boom)
    v = dist.marginal_variance()
    ens = dist.to_grid_ensemble(DAY)
    assert np.asarray(v).shape == GRID.shape
    assert ens.samples.shape == (M, *GRID.shape)


def test_ensemble_mode_capability_and_routing() -> None:
    """Miost(members=m, member_root=r) is SAMPLES-native and solve() routes.

    Catches: the capability flip leaving native_capability POINT (bars_for
    would silently omit the coverage bar at the Stage-B gate — false-green),
    or solve() returning the wrong distribution type in ensemble mode.
    """
    from sverdrup.core.types import UncertaintyCapability
    from sverdrup.distributions.calibration import CalibratedDistribution

    assert _method().native_capability is UncertaintyCapability.POINT
    ens_method = Miost(plan=WindowPlan(starts=(0.0, 45.0)), members=3, member_root=ROOT)
    assert ens_method.native_capability is UncertaintyCapability.SAMPLES
    d = ens_method.solve(_obs(), GRID, PARAMS, DAY)
    # Phase-9 §3: solve() now returns CalibratedDistribution wrapping the raw ensemble.
    assert isinstance(d, CalibratedDistribution)
    assert isinstance(d.underlying, MiostEnsembleDistribution)
    assert d.underlying.m == 3


def test_shipped_miost_solve_records_field_inflation_provenance() -> None:
    """The shipped product routes to SAMPLES and stamps FIELD_INFLATION provenance.

    A solve from the signed scalar-era config must be SAMPLES-native and carry a
    FIELD_INFLATION transform recording the Phase-8 poly field's ``cal_kind``
    ('poly'), ``dof`` (5), and the byte-exact artifact ``calibration_key`` —
    the auditable proof the production σ is the clipped-poly field, not the
    retired scalar.

    Catches: the flip leaving the shipped product on the scalar (which would
    stamp DIAGONAL_INFLATION instead), or dropping the field provenance so the
    shipped σ becomes unauditable.
    """
    from sverdrup.distributions.calibration import CalibratedDistribution
    from sverdrup.methods.miost import shipped_miost5_scalar_phase8

    ship = Miost(
        plan=WindowPlan(starts=(0.0, 45.0)),
        members=3,
        member_root=ROOT,
        calibration=shipped_miost5_scalar_phase8()._calibration,
    )
    assert ship.native_capability is UncertaintyCapability.SAMPLES
    d = ship.solve(_obs(), GRID, PARAMS, DAY)
    # Phase-9 §3: solve() returns CalibratedDistribution wrapping the raw ensemble.
    assert isinstance(d, CalibratedDistribution)
    field_transforms = [
        t
        for t in d.provenance.transformations
        if t.kind is TransformKind.FIELD_INFLATION
    ]
    assert len(field_transforms) == 1
    params = field_transforms[0].params
    assert params["cal_kind"] == "poly"
    assert params["dof"] == 5
    assert params["calibration_key"] == (
        "cal:poly;coeffs=(2.628363705995422, 0.6473150127828258, "
        "-2.2371390187292186, -0.1485348137468948, 0.5330366783275191);"
        "clip=(1.1731020392124571,2.9290288130316813);fit=L-BFGS-B;gtol=1e-08"
    )


def test_ensemble_mode_mean_bit_identical_to_point() -> None:
    """Ensemble-mode solve ships the UNTOUCHED Stage-A mean (D6).

    Catches: the routing (or a non-unit inflation default) perturbing the
    mean — the mean-unchanged non-regression at method level.
    """
    point = _method().solve(_obs(), GRID, PARAMS, DAY)
    ens = Miost(plan=WindowPlan(starts=(0.0, 45.0)), members=3, member_root=ROOT).solve(
        _obs(), GRID, PARAMS, DAY
    )
    np.testing.assert_array_equal(np.asarray(ens.mean), np.asarray(point.mean))


def test_ensemble_mode_inflation_exact_and_recorded() -> None:
    """inflation_s scales variance EXACTLY s-fold and is in provenance.

    Catches: s applied to the mean, applied twice, or dropped from the
    transform chain (the gate's s* would then be unauditable).
    Hand: var(sqrt(2) * anoms) = 2 * var(anoms), exactly, per node.
    """

    def _mk(s: float) -> Miost:
        return Miost(
            plan=WindowPlan(starts=(0.0, 45.0)),
            members=3,
            member_root=ROOT,
            inflation_s=s,
        )

    d1 = _mk(1.0).solve(_obs(), GRID, PARAMS, DAY)
    d2 = _mk(2.0).solve(_obs(), GRID, PARAMS, DAY)
    np.testing.assert_allclose(
        np.asarray(d2.marginal_variance()),
        2.0 * np.asarray(d1.marginal_variance()),
        rtol=1e-12,
    )
    infl = [
        t
        for t in d2.provenance.transformations
        if t.kind is TransformKind.DIAGONAL_INFLATION
    ]
    assert len(infl) == 1 and infl[0].params["s"] == 2.0
    np.testing.assert_array_equal(np.asarray(d2.mean), np.asarray(d1.mean))


def test_ensemble_mode_requires_root() -> None:
    """members > 0 without member_root raises — never a silent default seed.

    Catches: irreproducible members (a hidden default root would make the
    gate's ensemble unrecoverable across sessions and break CRN identity).
    """
    with pytest.raises(ValueError, match="member_root"):
        Miost(members=3)


# ---------------------------------------------------------------------------
# Task 4: Miost calibration boundary + params_key + factory
# ---------------------------------------------------------------------------


def test_miost_calibration_arg_routes_to_product() -> None:
    """Miost(calibration=ScalarCalibration(2.0)) inflates variance exactly 2×.

    Catches: the new ``calibration`` constructor arg being ignored (solve
    would return an uncalibrated product — the gate's s* silently dropped).
    """
    from sverdrup.distributions.calibration import ScalarCalibration

    base = Miost(
        plan=WindowPlan(starts=(0.0, 45.0)), members=3, member_root=ROOT
    ).solve(_obs(), GRID, PARAMS, DAY)
    cal = Miost(
        plan=WindowPlan(starts=(0.0, 45.0)),
        members=3,
        member_root=ROOT,
        calibration=ScalarCalibration(2.0),
    ).solve(_obs(), GRID, PARAMS, DAY)
    np.testing.assert_allclose(
        np.asarray(cal.marginal_variance()),
        2.0 * np.asarray(base.marginal_variance()),
        rtol=1e-12,
    )
    infl = [
        t
        for t in cal.provenance.transformations
        if t.kind is TransformKind.DIAGONAL_INFLATION
    ]
    assert len(infl) == 1 and infl[0].params["s"] == 2.0


def test_miost_both_calibration_and_inflation_raises() -> None:
    """Passing calibration AND inflation_s != 1.0 raises ValueError.

    Catches: a silent precedence rule where one arg wins and the other is
    dropped — the caller would not learn their s* was ignored.
    """
    from sverdrup.distributions.calibration import ScalarCalibration

    with pytest.raises(ValueError, match="calibration"):
        Miost(
            members=3,
            member_root=ROOT,
            inflation_s=2.0,
            calibration=ScalarCalibration(3.0),
        )


def test_miost_inflation_s_still_maps_to_scalar_calibration() -> None:
    """inflation_s=2.0 (no calibration) lands in self._calibration as a scalar.

    Catches: the compat mapping being lost — a caller relying on inflation_s
    would get an uncalibrated product.
    """
    from sverdrup.distributions.calibration import ScalarCalibration

    m = Miost(members=3, member_root=ROOT, inflation_s=2.0)
    assert m._calibration == ScalarCalibration(2.0)


def test_params_key_includes_calibration() -> None:
    """_params_key carries ;cal=<key> and differs across distinct calibrations.

    Catches: two products with different calibrations deriving the SAME CRN
    seed (silent member-stream collision across calibrations).
    """
    from sverdrup.distributions.calibration import ScalarCalibration

    m1 = Miost(members=3, member_root=ROOT, calibration=ScalarCalibration(1.0))
    m2 = Miost(members=3, member_root=ROOT, calibration=ScalarCalibration(2.0))
    k1 = m1._params_key(PARAMS, GRID)
    k2 = m2._params_key(PARAMS, GRID)
    assert ";cal=" in k1
    assert k1.endswith(ScalarCalibration(1.0).key())
    assert k1 != k2


def test_shipped_miost_uses_phase8_poly_field() -> None:
    """shipped_miost5_scalar_phase8() carries the Phase-8 clipped-poly field.

    (T14 flip 2026-07-21: shipped_miost5() now carries the phase-13 refit
    field — pinned in test_phase13_flip.py; the Phase-8 pin lives HERE on
    the preserved factory.)

    The winning field from the signed evidence (phase8_field.json /
    stage_miost_gate_results.json ``phase8`` block): the exact 5-dof poly
    coeffs, evidence-anchored log-s clip, and fit_id — assembled from the
    inlined module constants and byte-identical to the artifact ``cal_key``.

    Catches: the registry still shipping the scalar s* after the capability
    flip (Task 12), or any drift in the inlined poly constants / clip / fit_id
    away from the signed field (a wrong shipped calibration would silently
    mis-scale every production σ).
    """
    from sverdrup.distributions.calibration import ClipSpec, PolyCalibration
    from sverdrup.methods.miost import (
        PHASE8_CLIP_HI,
        PHASE8_CLIP_LO,
        PHASE8_FIT_ID,
        PHASE8_POLY_COEFFS,
        shipped_miost5_scalar_phase8,
    )

    expected = PolyCalibration(
        coeffs=PHASE8_POLY_COEFFS,
        clip=ClipSpec(lo_log_s=PHASE8_CLIP_LO, hi_log_s=PHASE8_CLIP_HI),
        fit_id=PHASE8_FIT_ID,
    )
    cal = shipped_miost5_scalar_phase8()._calibration
    assert cal == expected
    # byte-exact against the signed artifact cal_key
    assert cal.key() == (
        "cal:poly;coeffs=(2.628363705995422, 0.6473150127828258, "
        "-2.2371390187292186, -0.1485348137468948, 0.5330366783275191);"
        "clip=(1.1731020392124571,2.9290288130316813);fit=L-BFGS-B;gtol=1e-08"
    )


def test_shipped_miost6_carries_the_same_phase8_field() -> None:
    """The six-mission flagship ships the IDENTICAL frozen s(x) field.

    Phase-12 flip census row: shipped_miost6 is a provenance-only twin of
    the SIGNED scalar-era config (the T14 flip moved shipped_miost5 to the
    structured-R winner; the frozen-transfer claim pins the preserved
    factory) — a calibration divergence would silently break the
    transferred-and-verified σ-semantics claim.
    """
    from sverdrup.methods.miost import shipped_miost5_scalar_phase8, shipped_miost6

    m5, m6 = shipped_miost5_scalar_phase8(), shipped_miost6()
    assert m6._calibration == m5._calibration
    assert m6._calibration.key() == m5._calibration.key()
    assert m6.members == m5.members == 100
    assert m6.member_root == m5.member_root
