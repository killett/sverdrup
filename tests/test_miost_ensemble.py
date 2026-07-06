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
    return _method().sample_members(_obs(), GRID, PARAMS, DAY, m=M, root=ROOT)


def test_one_batched_solve_per_window(monkeypatch: pytest.MonkeyPatch) -> None:
    """Members come from ONE (n, m) batched solve per window.

    Catches: a per-member solve loop — m separate PCG launches per window,
    the exact cost blow-up the batched-RHS design exists to avoid.
    """
    shapes: list[tuple[int, ...]] = []
    orig = MiostSolver.solve

    def spy(self: MiostSolver, b: np.ndarray) -> object:
        shapes.append(np.atleast_2d(np.asarray(b).T).T.shape)
        return orig(self, b)

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
